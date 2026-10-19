"""Unity ParticleSystem 预制体（.fx.json）→ Niagara 发射器方案（离线，不依赖 UE）。

一个渲染中的 ParticleSystem 节点对应一个 Niagara 发射器。粒子行为不套 Niagara 的高层模块，
而是用 Set Parameters 模块把已核实的 Unity 公式逐项写成 HLSL 表达式：

    发射器更新：Emitter State（Self、Once/Infinite、时长=lengthInSec、延迟=startDelay）
                 Spawn Burst（逐个 burst 的时刻与数量）/ Spawn Rate（rateOverTime）
    粒子生成：  Lifetime、各随机数、起始颜色/尺寸/旋转、世界空间发射器的出生位姿
    粒子更新：  Particle State（年龄、到寿命销毁）
                节点位姿 = 预制体根→节点的变换链（含 Legacy Animation 的旋转/位置曲线，按 System.Age 求值）
                Position / MeshOrientation / Scale / Color / DynamicMaterialParameter0..3

坐标约定（与网格导入一致）：Unity (x, y, z) 米 → UE (-x, z, y)×100 厘米；
四元数 (x, y, z, w) → (-x, z, y, w)；缩放 (sx, sy, sz) → (sx, sz, sy)。
所有 Unity 量先在 Unity 坐标里算好，最后一步才换到 UE。

支持 Sphere/Cone Base 出生形状、View Billboard 和 Lifetime Grid UV；
标准帧/缩放适配复用引擎时钟；未知减速/触限度量须显式选择可调UE等效，不能冒称原生一致。
"""
import math
import re
import zzz_fx_particle_renderer as PR
import zzz_fx_particle_motion as PM
import zzz_fx_particle_uv as PU

UNITY_RENDER_MODE = {0: "Billboard", 1: "Stretch", 2: "HorizontalBillboard", 3: "VerticalBillboard", 4: "Mesh", 5: "None"}
# 已实现的模块；其余模块 enabled=true 时报错
SUPPORTED_MODULES = {"InitialModule", "EmissionModule", "ColorModule", "SizeModule", "RotationModule", "CustomDataModule",
                     "ShapeModule", "UVModule", "VelocityModule", "ClampVelocityModule", "LightsModule"}


class SpecError(Exception):
    pass


def f(v):
    """HLSL 浮点字面量。"""
    if isinstance(v, bool):
        return "1.0" if v else "0.0"
    if v != v or abs(v) == float("inf"):
        raise SpecError("非有限数值 %r" % v)
    s = repr(float(v))
    return s if ("." in s or "e" in s) else s + ".0"


def f3(v):
    return "float3(%s, %s, %s)" % tuple(f(x) for x in v)


def f4(v):
    return "float4(%s, %s, %s, %s)" % tuple(f(x) for x in v)


# ---------------------------------------------------------------- 四元数（Unity 坐标，(x, y, z, w)）

def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qrot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def qeuler_zxy(rx, ry, rz):
    """Unity Quaternion.Euler（弧度）：先绕 Z、再绕 X、最后绕 Y。"""
    def axis(ax, a):
        s, c = math.sin(a / 2), math.cos(a / 2)
        return tuple(s if i == ax else 0.0 for i in range(3)) + (c,)
    return qmul(axis(1, ry), qmul(axis(0, rx), axis(2, rz)))


# 表达式版本：参数是 HLSL 字符串
QMUL_HLSL = ("float4({a}.w * {b}.xyz + {b}.w * {a}.xyz + cross({a}.xyz, {b}.xyz), "
             "{a}.w * {b}.w - dot({a}.xyz, {b}.xyz))")
QROT_HLSL = ("({v} + 2.0 * cross({q}.xyz, cross({q}.xyz, {v}) + {q}.w * {v}))")


def qmul_h(a, b):
    return QMUL_HLSL.format(a=a, b=b)


def qrot_h(q, v):
    return QROT_HLSL.format(q=q, v=v)


# Unity → UE
def ue_pos_h(p):
    return "(float3(-({p}).x, ({p}).z, ({p}).y) * 100.0)".format(p=p)


def ue_quat_h(q):
    # C=(-X,Z,Y) has determinant +1, so C*R(q)*C^-1 maps the quaternion
    # vector part by C. The old sign pattern rotated mesh axes backwards.
    return "float4(-({q}).x, ({q}).z, ({q}).y, ({q}).w)".format(q=q)


def ue_scale_h(s):
    return "float3(({s}).x, ({s}).z, ({s}).y)".format(s=s)


def srgb_to_linear_h(c):
    """Unity 的 GammaToLinearSpace（逐通道 sRGB 曲线），alpha 不变。"""
    return ("float4(select(({c}).rgb <= 0.04045, ({c}).rgb / 12.92, pow((({c}).rgb + 0.055) / 1.055, 2.4)), ({c}).a)"
            .format(c=c))


# ---------------------------------------------------------------- 曲线与渐变

class CurveProgram:
    """Ordered transient assignments for time-inverted weighted Bezier curves.

    Bisection reaches single precision in 24 steps. Values stay on the original
    cubic curve; no piecewise linear resampling or second animation clock.
    """
    def __init__(self, stage):
        self.prefix = "Transient.UWeighted" + stage
        self.entries = []

    def temp(self, kind, expr):
        name = self.prefix + str(len(self.entries))
        self.entries.append((name, kind, expr))
        return name


def bezier_h(points, u):
    a, b, c, d = points
    return "(((%s * (%s) + %s) * (%s) + %s) * (%s) + %s)" % (
        f(-a + 3*b - 3*c + d), u, f(3*a - 6*b + 3*c), u, f(-3*a + 3*b), u, f(a))


def weighted_segment_h(a, b, t, program):
    if program is None:
        raise SpecError("Weighted curve requires ordered transient assignments")
    dt = b["time"] - a["time"]
    w0 = a["outWeight"] if a.get("weightedMode", 0) in (2, 3) else 1/3
    w1 = b["inWeight"] if b.get("weightedMode", 0) in (1, 3) else 1/3
    if not (0 <= w0 <= 1 and 0 <= w1 <= 1):
        raise SpecError("Weighted curve time handles must be within [0, 1]")
    target = program.temp("Float", "saturate(((%s) - %s) / %s)" % (t, f(a["time"]), f(dt)))
    bounds = program.temp("Vector4", "float4(0.0, 1.0, 0.0, 0.0)")
    for _ in range(24):
        mid = "((%s.x + %s.y) * 0.5)" % (bounds, bounds)
        x = bezier_h((0, w0, 1-w1, 1), mid)
        bounds = program.temp("Vector4", "((%s) < %s ? float4(%s, %s.y, 0.0, 0.0) : "
                              "float4(%s.x, %s, 0.0, 0.0))" % (x, target, mid, bounds, bounds, mid))
    u = "((%s.x + %s.y) * 0.5)" % (bounds, bounds)
    y = bezier_h((a["value"], a["value"] + w0*dt*a["outSlope"],
                  b["value"] - w1*dt*b["inSlope"], b["value"]), u)
    return program.temp("Float", y)


def curve_h(curve, t, program=None):
    """Unity AnimationCurve → HLSL: Hermite or time-inverted weighted Bezier."""
    keys = curve["m_Curve"]
    if not keys:
        raise SpecError("空曲线")
    if len(keys) == 1:
        return f(keys[0]["value"])
    expr = f(keys[-1]["value"])
    for a, b in reversed(list(zip(keys, keys[1:]))):
        dt = b["time"] - a["time"]
        weighted = a.get("weightedMode", 0) in (2, 3) or b.get("weightedMode", 0) in (1, 3)
        if dt <= 0:
            seg = f(b["value"])
        elif abs(a["outSlope"]) == float("inf") or abs(b["inSlope"]) == float("inf"):
            seg = f(a["value"])
        elif weighted:
            seg = weighted_segment_h(a, b, t, program)
        else:
            s = "saturate(((%s) - %s) / %s)" % (t, f(a["time"]), f(dt))
            # h00 v0 + h10 dt m0 + h01 v1 + h11 dt m1，按 s 展开成多项式系数，避免重复长子式
            v0, v1, m0, m1 = a["value"], b["value"], a["outSlope"] * dt, b["inSlope"] * dt
            c3 = 2 * v0 + m0 - 2 * v1 + m1
            c2 = -3 * v0 - 2 * m0 + 3 * v1 - m1
            seg = "(((%s * {s} + %s) * {s} + %s) * {s} + %s)".format(s="S") % (f(c3), f(c2), f(m0), f(v0))
            seg = seg.replace("S", s)
        expr = "((%s) < %s ? %s : %s)" % (t, f(b["time"]), seg, expr)
    return "((%s) <= %s ? %s : %s)" % (t, f(keys[0]["time"]), f(keys[0]["value"]), expr)


def minmax_curve_h(c, t, rand_attr, program=None):
    """MinMaxCurve：0 常量、1 曲线、2 双曲线随机、3 双常量随机。rand_attr 是该粒子固定的随机数。"""
    s = c["minMaxState"]
    if s == 0:
        return f(c["scalar"])
    if s == 1:
        return "(%s * %s)" % (f(c["scalar"]), curve_h(c["maxCurve"], t, program))
    if s == 2:
        return "(%s * lerp(%s, %s, %s))" % (f(c["scalar"]), curve_h(c["minCurve"], t, program), curve_h(c["maxCurve"], t, program), rand_attr)
    if s == 3:
        return "lerp(%s, %s, %s)" % (f(c["minScalar"]), f(c["scalar"]), rand_attr)
    raise SpecError("MinMaxCurve 模式 %r" % s)


def minmax_curve_const(c):
    """只接受与时间无关、非随机的常量，用于发射器级参数。"""
    if c["minMaxState"] != 0:
        raise SpecError("发射器级参数要求常量 MinMaxCurve，实际模式 %d" % c["minMaxState"])
    return c["scalar"]


def burst_count(c, path):
    """Burst counts are integers; preserve two-constant random event counts."""
    if c["minMaxState"] not in (0, 3):
        raise SpecError("%s burst count curve mode %r is not implemented" % (path, c["minMaxState"]))
    maximum = c["scalar"]
    minimum = c["minScalar"] if c["minMaxState"] == 3 else maximum
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or v != int(v)
           for v in (minimum, maximum)) or minimum > maximum:
        raise SpecError("%s burst count requires ordered nonnegative integer endpoints" % path)
    return int(maximum) if minimum == maximum else {"min": int(minimum), "max": int(maximum)}


def gradient_h(g, t):
    """Unity Gradient → float4 HLSL。颜色与 alpha 各自分段线性（mode 0）或阶跃（mode 1）。"""
    mode = g["m_Mode"]
    if mode not in (0, 1):
        raise SpecError("Gradient 模式 %r 未实现" % mode)
    nc, na = g["m_NumColorKeys"], g["m_NumAlphaKeys"]
    ck = [(g["ctime%d" % i] / 65535.0, [g["key%d" % i][c] for c in "rgb"]) for i in range(nc)]
    ak = [(g["atime%d" % i] / 65535.0, g["key%d" % i]["a"]) for i in range(na)]

    def piece(keys, conv, lerp_fn):
        expr = conv(keys[-1][1])
        for (t0, v0), (t1, v1) in reversed(list(zip(keys, keys[1:]))):
            if mode == 1 or t1 <= t0:
                seg = conv(v1 if mode == 1 else v1)
            else:
                seg = lerp_fn(conv(v0), conv(v1), "saturate(((%s) - %s) / %s)" % (t, f(t0), f(t1 - t0)))
            expr = "((%s) < %s ? %s : %s)" % (t, f(t1), seg, expr)
        return "((%s) <= %s ? %s : %s)" % (t, f(keys[0][0]), conv(keys[0][1]), expr)

    rgb = piece(ck, f3, lambda a, b, s: "lerp(%s, %s, %s)" % (a, b, s))
    a = piece(ak, f, lambda x, y, s: "lerp(%s, %s, %s)" % (x, y, s))
    return "float4(%s, %s)" % (rgb, a)


def color_of(c):
    return [c["r"], c["g"], c["b"], c["a"]]


def minmax_gradient_h(g, t, rand_attr):
    s = g["minMaxState"]
    if s == 0:
        return f4(color_of(g["maxColor"]))
    if s == 1:
        return gradient_h(g["maxGradient"], t)
    if s == 2:
        return "lerp(%s, %s, %s)" % (f4(color_of(g["minColor"])), f4(color_of(g["maxColor"])), rand_attr)
    if s == 3:
        return "lerp(%s, %s, %s)" % (gradient_h(g["minGradient"], t), gradient_h(g["maxGradient"], t), rand_attr)
    if s == 4:
        return gradient_h(g["maxGradient"], rand_attr)
    raise SpecError("MinMaxGradient 模式 %r" % s)


# ---------------------------------------------------------------- 节点变换链

def _vals(d, keys):
    return tuple(float(d[k]) for k in keys)


def anim_curve_h(keys, comp, t):
    """zzz_unity_anim 的曲线（value/in/out 为列表）→ HLSL。"""
    conv = {"m_Curve": [{"time": k["time"], "value": k["value"][comp], "inSlope": k["in"][comp],
                         "outSlope": k["out"][comp]} for k in keys]}
    return curve_h(conv, t)


class Chain:
    """预制体根 → 节点的变换，常量部分在 Python 里折叠，带动画的节点生成 HLSL。

    累积量 (P, Q, S)：世界点 = P + Q ⊗ (S ∘ 本地点)。非均匀父缩放与
    子旋转组合产生切变时，不能用三个缩放分量可靠表达，须使用矩阵路径。"""

    def __init__(self, prefix="Particles.UChain"):
        self.P, self.Q, self.S = (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0)
        self.Ph = self.Qh = None  # 一旦出现动画，转成 HLSL 字符串
        self.animated = False
        # 中间结果写成粒子属性（Set Parameters 条目按顺序求值），避免长表达式在四元数乘法里成倍展开
        self.prefix = prefix
        self.temps = []

    def temp(self, kind, expr):
        name = "%s%d%s" % (self.prefix, len(self.temps), kind)
        self.temps.append((name, "Quat" if kind == "Q" else "Vector", expr))
        return name

    def commutes(self, q):
        """父级累积缩放 S 与子节点旋转 q 可交换（不会产生切变）的条件：
        旋转只绕某根轴、且另外两根轴缩放相等；或三轴缩放相等。"""
        sx, sy, sz = self.S
        eq = lambda a, b: abs(a - b) < 1e-4
        if eq(sx, sy) and eq(sy, sz):
            return True
        ax = [abs(q[0]) > 1e-6, abs(q[1]) > 1e-6, abs(q[2]) > 1e-6]
        if not any(ax):
            return True
        if ax == [False, True, False]:
            return eq(sx, sz)
        if ax == [True, False, False]:
            return eq(sy, sz)
        if ax == [False, False, True]:
            return eq(sx, sy)
        return False

    def push(self, pos, rot, scale, anim_rot=None, anim_pos=None, t=None):
        if getattr(self, "sheared", False):
            raise SpecError("切变节点下还有子节点，lossyScale 近似不再成立，未实现")
        if anim_rot and not all(self.commutes(k["value"]) for k in anim_rot):
            raise SpecError("父节点非均匀缩放 %r 下子节点旋转动画会产生切变，未实现" % (self.S,))
        if not self.commutes(rot):
            # The leaf origin and world quaternion are still exact. No lossy
            # scale is invented here; consumers must prove they do not use it.
            if anim_pos is not None:
                raise SpecError("切变节点位置动画需要矩阵变换路径")
            local_p = tuple(self.S[i] * pos[i] for i in range(3))
            if self.animated:
                self.Ph = self.temp("P", "(%s + %s)" % (self.Ph, qrot_h(self.Qh, f3(local_p))))
                self.Qh = self.temp("Q", qmul_h(self.Qh, f4(rot)))
            else:
                off = qrot(self.Q, local_p)
                self.P = tuple(self.P[i] + off[i] for i in range(3))
                self.Q = qmul(self.Q, rot)
            self.sheared = True
            return
        if anim_pos is None:
            local_p = tuple(self.S[i] * pos[i] for i in range(3))
        else:
            local_p = None
            lp_h = "float3(%s)" % ", ".join("%s * %s" % (f(self.S[i]), anim_curve_h(anim_pos, i, t)) for i in range(3))
        if not self.animated and anim_rot is None and anim_pos is None:
            off = qrot(self.Q, local_p)
            self.P = tuple(self.P[i] + off[i] for i in range(3))
            self.Q = qmul(self.Q, rot)
        else:
            Ph = self.Ph or f3(self.P)
            Qh = self.Qh or f4(self.Q)
            lp = lp_h if local_p is None else f3(local_p)
            if local_p is None:
                lp = self.temp("P", lp)
            self.Ph = self.temp("P", "(%s + %s)" % (Ph, qrot_h(Qh, lp)))
            if anim_rot is not None:
                qa = self.temp("Q", "normalize(float4(%s))" % ", ".join(anim_curve_h(anim_rot, i, t) for i in range(4)))
                self.Qh = self.temp("Q", qmul_h(Qh, qa))
            else:
                self.Qh = self.temp("Q", qmul_h(Qh, f4(rot)))
            self.animated = True
        self.S = tuple(self.S[i] * scale[i] for i in range(3))

    def pos_h(self):
        return self.Ph or f3(self.P)

    def quat_h(self):
        return self.Qh or f4(self.Q)


def node_chain(root, path_nodes, clip, t):
    """path_nodes：从根的子节点到目标节点（不含预制体根自身——根的位姿由生成时的组件变换决定）。"""
    ch = Chain()
    names = []
    for n in path_nodes:
        names.append(n["name"])
        rel = "/".join(names)
        ar = clip["rotation"].get(rel) if clip else None
        ap = clip["position"].get(rel) if clip else None
        if clip and (rel in clip["scale"] or rel in clip["euler"]):
            raise SpecError("节点 %s 的缩放/欧拉角动画未实现" % rel)
        ch.push(_vals(n["pos"], "xyz"), _vals(n["rot"], "xyzw"), _vals(n["scale"], "xyz"), ar, ap, t)
    return ch


def lossy_scale(path_nodes):
    s = [1.0, 1.0, 1.0]
    for n in path_nodes:
        for i, k in enumerate("xyz"):
            s[i] *= n["scale"][k]
    return tuple(s)


# ---------------------------------------------------------------- 发射器方案

def qeuler_h(v):
    """弧度欧拉角（HLSL float3）→ Unity Quaternion.Euler 顺序的四元数 HLSL：q = qy * qx * qz。"""
    qx = "float4(sin(({v}).x * 0.5), 0.0, 0.0, cos(({v}).x * 0.5))".format(v=v)
    qy = "float4(0.0, sin(({v}).y * 0.5), 0.0, cos(({v}).y * 0.5))".format(v=v)
    qz = "float4(0.0, 0.0, sin(({v}).z * 0.5), cos(({v}).z * 0.5))".format(v=v)
    return qmul_h(qy, qmul_h(qx, qz))


class Randoms:
    """按需分配每粒子固定的随机数：Particles.URand<k> 的各分量，出生时一次性生成。"""

    def __init__(self):
        self.n = 0

    def take(self):
        k = self.n
        self.n += 1
        return "Particles.URand%d.%s" % (k // 4, "xyzw"[k % 4])

    def spawn_entries(self):
        return [("Particles.URand%d" % i, "Vector4", "float4(rand(1.0), rand(1.0), rand(1.0), rand(1.0))")
                for i in range((self.n + 3) // 4)]


def check_modules(ps, path, policy=None):
    for name, expected in (("simulationSpeed", 1.0), ("useUnscaledTime", False),
                           ("stopAction", 0), ("ringBufferMode", 0), ("playOnAwake", True)):
        if name in ps and ps[name] != expected:
            raise SpecError("%s %s=%r requires its source runtime lifecycle/time contract" % (path, name, ps[name]))
    PM.check_limit_velocity(ps.get("ClampVelocityModule"), path, policy)
    lights = ps.get("LightsModule")
    if lights and lights["enabled"] and any(lights["light"][k] for k in ("m_FileID", "m_PathID")):
        raise SpecError("%s LightsModule bound Light prefab requires a source light renderer" % path)
    for k, v in ps.items():
        if isinstance(v, dict) and v.get("enabled") and k not in SUPPORTED_MODULES:
            raise SpecError("%s 启用了 %s，未实现" % (path, k))
    im = ps["InitialModule"]
    if ps.get("prewarm"):
        raise SpecError("%s 开了 prewarm，未实现" % path)
    c = im["gravityModifier"]
    if not (c["minMaxState"] in (0, 1) and c["scalar"] == 0.0) and not (
            c["minMaxState"] == 3 and c["scalar"] == 0.0 and c["minScalar"] == 0.0):
        raise SpecError("%s 的 gravityModifier 不为 0，重力未实现" % path)
    if im.get("randomizeRotationDirection", 0.0) != 0.0:
        raise SpecError("%s randomizeRotationDirection≠0 未实现" % path)
    em = ps.get("EmissionModule") if ps.get("EmissionModule", {}).get("enabled") else None
    if em and minmax_curve_const(em["rateOverDistance"]) < 0.0:
        raise SpecError("%s rateOverDistance must be nonnegative" % path)


def custom_data_h(cd, idx, age, rnd, program=None):
    if cd is None:
        return "float4(0.0, 0.0, 0.0, 0.0)"
    mode = cd["mode%d" % idx]
    if mode == 0:
        return "float4(0.0, 0.0, 0.0, 0.0)"
    if mode == 1:
        n = cd["vectorComponentCount%d" % idx]
        comps = [minmax_curve_h(cd["vector%d_%d" % (idx, k)], age, rnd.take(), program) if k < n else "0.0" for k in range(4)]
        return "float4(%s)" % ", ".join(comps)
    if mode == 2:
        return minmax_gradient_h(cd["color%d" % idx], age, rnd.take())
    raise SpecError("CustomData 模式 %r" % mode)


def sprite_motion(ps, path, chain, tscale, shape_pos, shape_dir, velocity_h, sim_local, rnd, curves):
    """Single velocity owner, native dt/lifetime, source-frame displacement.

    Keep Niagara positions in world space even for Unity local simulation: the
    source displacement follows current node/owner transforms explicitly. This
    prevents Niagara bLocalSpace from reapplying parent scale in Local/Shape
    scaling modes. No inverse owner scale or second transform/time cache.
    """
    smode = ps["scalingMode"]
    clamp = ps.get("ClampVelocityModule")
    if not sim_local and clamp and smode == 0:
        raise SpecError("%s world simulation with hierarchy-scale Clamp needs its source metric-frame adapter" % path)
    if not sim_local and clamp and len(set(tscale)) != 1:
        raise SpecError("%s world simulation with nonuniform-scale Clamp needs its source metric-frame adapter" % path)
    origin = "(Engine.Owner.Position + %s)" % qrot_h("Engine.Owner.Rotation",
                                 "(Engine.Owner.Scale * %s)" % ue_pos_h(chain.pos_h()))

    def vector_world(vector, scale, owner_scale):
        value = ue_pos_h(qrot_h(chain.quat_h(), "(%s * %s)" % (f3(scale), vector)))
        if owner_scale:
            value = "(Engine.Owner.Scale * %s)" % value
        return qrot_h("Engine.Owner.Rotation", value)

    shape_world = vector_world(shape_pos, chain.S if smode == 2 else tscale, smode in (0, 2))
    birth = "(%s + %s)" % (origin, shape_world)
    spawn, update = list(chain.temps), list(chain.temps)
    base = "Particles.UEFX_BaseVelocity"
    total = "Transient.UEFX_TotalVelocity"
    linear = "Transient.UEFX_LinearVelocity"
    initial = "(%s * Particles.USpeed)" % shape_dir
    if sim_local:
        spawn += [(base, "Vector", initial), ("Particles.UEFX_Displacement", "Vector", "float3(0.0,0.0,0.0)"),
                  ("Particles.Position", "Position", birth)]
        update.append((linear, "Vector", velocity_h))
    else:
        spawn += [(base, "Vector", vector_world(initial, tscale, smode == 0)),
                  ("Particles.Position", "Position", birth)]
        update.append((linear, "Vector", vector_world(velocity_h, tscale, smode == 0)))
    update.append((total, "Vector", "(%s + %s)" % (base, linear)))
    tunables = []
    if clamp:
        limit = minmax_curve_h(clamp["magnitude"], "Particles.NormalizedAge", rnd.take(), curves)
        if not sim_local:
            limit = "(%s * %s)" % (limit, f(abs(tscale[0]) * 100.0))
        update += PM.dampen_entries(clamp, limit, total, f)
        # Retain damping feedback. Reconstructing the original start speed each
        # update would discard all earlier damping; curve velocity is additive.
        update.append((base, "Vector", "(%s - %s)" % (total, linear)))
        tunables = [("Emitter.UEFX_DampenReferenceSeconds", "Float"), ("Emitter.UEFX_DampenStrength", "Float")]
    if sim_local:
        update += [("Particles.UEFX_Displacement", "Vector", "(Particles.UEFX_Displacement + %s * Engine.DeltaTime)" % total),
                   ("Particles.Velocity", "Vector", vector_world(total, tscale, smode == 0)),
                   ("Particles.Position", "Position", "(%s + %s)" % (birth,
                        vector_world("Particles.UEFX_Displacement", tscale, smode == 0)))]
    else:
        update += [("Particles.Velocity", "Vector", total),
                   ("Particles.Position", "Position", "(Particles.Position + Particles.Velocity * Engine.DeltaTime)")]
    # Hierarchical size incorporates the owner transform once. Local ignores
    # parents; Shape does not scale size or movement. Axis lengths remain valid
    # under owner nonuniform scaling without pretending the chain is pure TRS.
    if smode == 0:
        size_scale = "float3(%s)" % ", ".join("length(Engine.Owner.Scale * %s)" % ue_pos_h(
            qrot_h(chain.quat_h(), f3(tuple(tscale[i] if i == axis else 0.0 for i in range(3)))))
            + " / 100.0" for axis in range(3))
    else:
        size_scale = f3(tscale)
    return spawn, update, size_scale, tunables


def emitter_spec(node, path_nodes, clip, ue_assets, material_paths, material_plan, particle_equivalence=None):
    path = "/".join(n["name"] for n in path_nodes)
    raw_ps, rd = node["particle"]["system"], node["particle"]["renderer"]
    # New source evidence preserves disabled modules as well as enabled ones.
    # Their serialized curves are inert and must never become live simulation.
    ps = {k: v for k, v in raw_ps.items() if not isinstance(v, dict) or "enabled" not in v
          or v["enabled"] or k == "InitialModule"}
    policy = PM.equivalence_policy(particle_equivalence)
    check_modules(ps, path, policy)
    im = ps["InitialModule"]
    rnd = Randoms()
    spawn_curves, update_curves = CurveProgram("Spawn"), CurveProgram("Update")
    age = "Particles.NormalizedAge"
    eage = "Emitter.NormalizedLoopAge"
    sim_local = ps["moveWithTransform"] == 0
    if ps["moveWithTransform"] not in (0, 1):
        raise SpecError("%s 自定义模拟空间未实现" % path)

    spawn, update = [], []
    spawn.append(("Particles.Lifetime", "Float", minmax_curve_h(im["startLifetime"], eage, rnd.take(), spawn_curves)))
    spawn.append(("Particles.UStartColor", "Vector4", minmax_gradient_h(im["startColor"], eage, rnd.take())))
    if im["size3D"]:
        sz = "float3(%s, %s, %s)" % tuple(minmax_curve_h(im[k], eage, rnd.take(), spawn_curves) for k in ("startSize", "startSizeY", "startSizeZ"))
    else:
        sz = "(%s * float3(1.0, 1.0, 1.0))" % minmax_curve_h(im["startSize"], eage, rnd.take(), spawn_curves)
    spawn.append(("Particles.UStartSize", "Vector", sz))
    if im["rotation3D"]:
        rot0 = "float3(%s, %s, %s)" % tuple(minmax_curve_h(im[k], eage, rnd.take(), spawn_curves) for k in ("startRotationX", "startRotationY", "startRotation"))
    else:
        rot0 = "float3(0.0, 0.0, %s)" % minmax_curve_h(im["startRotation"], eage, rnd.take(), spawn_curves)
    spawn.append(("Particles.URot", "Vector", rot0))
    spawn.append(("Particles.UStable", "Vector4", "float4(rand(1.0), rand(1.0), rand(1.0), rand(1.0))"))
    # Shape samples are source-local birth attributes. No shape means the
    # original origin/+Z direction; unsupported enabled shapes fail explicitly.
    shape_entries, shape_pos, shape_dir, shape = PM.birth_shape_h(ps.get("ShapeModule"), path, rnd, f)
    spawn += shape_entries
    if shape is not None:
        shape_q = f4(qeuler_zxy(*(math.radians(value) for value in shape["m_Rotation"])))
        shape_pos = "(%s + %s)" % (f3(shape["m_Position"]), qrot_h(shape_q,
                    "(%s * %s)" % (f3(shape["m_Scale"]), shape_pos)))
        shape_dir = qrot_h(shape_q, shape_dir)
        spawn += [("Particles.UShapePosition", "Vector", shape_pos),
                  ("Particles.UShapeDirection", "Vector", shape_dir)]
        shape_pos, shape_dir = "Particles.UShapePosition", "Particles.UShapeDirection"
    spawn.append(("Particles.USpeed", "Float", minmax_curve_h(im["startSpeed"], eage, rnd.take(), spawn_curves)))
    local_pos = "(%s + %s * Particles.USpeed * Particles.Age)" % (shape_pos, shape_dir)
    velocity = ps.get("VelocityModule")
    requirements = []
    if velocity and rd["m_RenderMode"] != 0:
        # The unfinished mesh candidate never passed preflight. Retire that
        # dead write chain rather than retain a speculative integrator behind
        # a permanent native-evidence requirement. This is an adapter gap.
        raise SpecError("%s mesh VelocityModule simulation-frame adapter is not implemented" % path)

    # 旋转随寿命（角速度，弧度/秒）
    rm = ps.get("RotationModule")
    if rm:
        if rm["separateAxes"]:
            w = "float3(%s, %s, %s)" % tuple(minmax_curve_h(rm[k], age, rnd.take(), update_curves) for k in ("x", "y", "curve"))
        else:
            w = "float3(0.0, 0.0, %s)" % minmax_curve_h(rm["curve"], age, rnd.take(), update_curves)
        update.append(("Particles.URot", "Vector", "(Particles.URot + %s * Engine.DeltaTime)" % w))
    # 尺寸随寿命
    sm = ps.get("SizeModule")
    if sm:
        if sm["separateAxes"]:
            mul = "float3(%s, %s, %s)" % tuple(minmax_curve_h(sm[k], age, rnd.take(), update_curves) for k in ("curve", "y", "z"))
        else:
            mul = "(%s * float3(1.0, 1.0, 1.0))" % minmax_curve_h(sm["curve"], age, rnd.take(), update_curves)
        update.append(("Particles.USize", "Vector", "(Particles.UStartSize * %s)" % mul))
    else:
        update.append(("Particles.USize", "Vector", "Particles.UStartSize"))
    # 颜色：Unity 在 gamma 空间相乘；渲染器 ApplyActiveColorSpace 时再转线性
    cm = ps.get("ColorModule")
    col = "Particles.UStartColor"
    if cm:
        col = "(Particles.UStartColor * %s)" % minmax_gradient_h(cm["gradient"], age, rnd.take())
    update.append(("Particles.Color", "LinearColor", srgb_to_linear_h(col) if rd["m_ApplyActiveColorSpace"] else col))

    # 节点位姿
    t_anim = "System.Age"
    chain = node_chain(None, path_nodes, clip, t_anim)
    if getattr(chain, "sheared", False):
        speed = im["startSpeed"]
        stationary = speed["minMaxState"] == 0 and speed["scalar"] == 0.0 or (
            speed["minMaxState"] == 3 and speed["scalar"] == 0.0 and speed["minScalar"] == 0.0)
        if ps["scalingMode"] == 0 or not stationary or shape is not None:
            raise SpecError("%s 切变影响层级尺寸或运动，需要矩阵变换路径" % path)
    if ps["scalingMode"] == 0:
        tscale = chain.S
    elif ps["scalingMode"] == 1:
        tscale = _vals(node["scale"], "xyz")
    elif ps["scalingMode"] == 2:
        tscale = (1.0, 1.0, 1.0)
    else:
        raise SpecError("%s 未知 scalingMode %r" % (path, ps["scalingMode"]))
    mode = rd["m_RenderMode"]
    if mode not in (0, 4):
        raise SpecError("%s 渲染模式 %s 未实现" % (path, UNITY_RENDER_MODE.get(mode, mode)))
    renderer_contract = PR.mesh_contract(rd, path) if mode == 4 else PR.sprite_contract(rd, path)
    viewport = PR.viewport_plan(rd, policy, path) if mode == 0 else None
    if viewport is not None:
        if material_plan.get("viewport_clamp") != viewport:
            raise SpecError("%s sprite material is missing/mismatches its explicit viewport geometry adapter" % path)
        renderer_contract["requirements"] = []
        renderer_contract["viewport_adapter"] = {k: viewport[k] for k in ("mode", "metric", "precision")}
        renderer_contract["viewport_adapter_signature"] = PR.viewport_signature(viewport)
    align = rd["m_RenderAlignment"]
    if mode == 0:
        if im["rotation3D"] or (rm and rm["separateAxes"]):
            raise SpecError("%s 3D billboard rotation requires a source plane adapter" % path)
        q_u = None
    elif align == 2:      # Local：网格随变换旋转
        q_u = qmul_h(chain.quat_h(), "Particles.UPartQ")
    elif align == 1:    # World：只用粒子自身旋转
        q_u = "Particles.UPartQ"
    else:
        raise SpecError("%s 网格对齐模式 %d 未实现" % (path, align))
    if mode == 4:
        update.append(("Particles.UPartQ", "Quat", qeuler_h("Particles.URot")))
    scale_u = "(Particles.USize * %s)" % f3(tscale)
    pose = list(chain.temps)
    owner_q = "Engine.Owner.Rotation"
    if mode == 0:
        pose_q = None
    elif align == 1:
        # World-aligned meshes keep world orientation even in local simulation.
        inverse_owner = "float4(-Engine.Owner.Rotation.xyz, Engine.Owner.Rotation.w)"
        q_local = qmul_h(inverse_owner, ue_quat_h(q_u)) if sim_local else ue_quat_h(q_u)
    else:
        q_local = ue_quat_h(q_u)
    if mode == 4:
        pose_q = ("Particles.MeshOrientation", "Quat", q_local)
    # 粒子在节点本地的位移经节点变换到预制体根空间（scalingMode=Shape 时位置也按变换缩放，与 Hierarchical 同）
    pos_u = "(%s + %s)" % (chain.pos_h(), qrot_h(chain.quat_h(), "(%s * %s)" % (f3(chain.S), local_pos)))
    emitter_update = []
    if mode == 0:
        velocity_h, velocity_world = PM.linear_velocity_h(velocity, path, rnd, update_curves, minmax_curve_h)
        if velocity_world:
            raise SpecError("%s World VelocityModule requires its inverse source simulation-frame conversion" % path)
        s_motion, u_motion, sprite_scale, tunables = sprite_motion(ps, path, chain, tscale,
                                                        shape_pos, shape_dir, velocity_h, sim_local, rnd, update_curves)
        spawn += s_motion
        update += u_motion
        scale_u = "(Particles.USize * %s)" % sprite_scale
        if tunables:
            emitter_update = [(name, kind, f(policy["dampen_reference_seconds" if name.endswith("ReferenceSeconds") else "dampen_strength"]))
                              for name, kind in tunables]
    elif ps.get("ClampVelocityModule"):
        raise SpecError("%s mesh ClampVelocityModule needs its simulation-frame adapter" % path)
    elif sim_local:
        update += pose + [("Particles.Position", "Position", ue_pos_h(pos_u))]
        if pose_q is not None:
            update.append(pose_q)
    else:
        # 世界空间：出生时把节点位置换到世界，之后沿出生时的方向直线运动；
        # Local 对齐的朝向仍按当前变换每帧更新（与 Unity 相同）
        spawn += [(n, t, e) for n, t, e in pose]
        birth_origin = "(%s + %s)" % (chain.pos_h(), qrot_h(chain.quat_h(),
                            "(%s * %s)" % (f3(chain.S), shape_pos)))
        world_origin = "(Engine.Owner.Position + %s)" % qrot_h("Engine.Owner.Rotation", "(Engine.Owner.Scale * %s)" % ue_pos_h(birth_origin))
        world_direction = qrot_h("Engine.Owner.Rotation", "(Engine.Owner.Scale * %s)" % ue_pos_h(qrot_h(chain.quat_h(), shape_dir)))
        update += [(n, t, e) for n, t, e in pose]
        spawn += [("Particles.UWorldOrigin", "Position", world_origin),
                  ("Particles.UWorldDir", "Vector", world_direction)]
        update.append(("Particles.Position", "Position",
                       "(Particles.UWorldOrigin + Particles.UWorldDir * Particles.USpeed * Particles.Age)"))
        if mode == 4:
            world_q = ue_quat_h(q_u) if align == 1 else qmul_h(owner_q, ue_quat_h(q_u))
            update.append(("Particles.MeshOrientation", "Quat", world_q))
    render_scale = "(%s * %s)" % (scale_u, PR.mesh_flip_h(renderer_contract["flip_probability"], rnd))
    if mode == 4:
        if ps.get("UVModule"):
            raise SpecError("%s Mesh UVModule requires a mesh-stream animation adapter" % path)
        update.append(("Particles.Scale", "Vector", ue_scale_h(render_scale)))
    else:
        # Sprite geometry width/height remain Unity X/Y; they are not 3D scale
        # axes. Niagara rotates the UV-down basis clockwise, hence -Unity Z.
        update += [("Particles.SpriteSize", "Vector2", "((%s).xy * 100.0)" % render_scale),
                   ("Particles.SpriteRotation", "Float", "(-Particles.URot.z * %s)" % f(180 / math.pi))]
        uv_spawn, uv_update, uv = PU.entries(ps.get("UVModule"), path, rnd,
                                      (spawn_curves, update_curves), minmax_curve_h, f)
        spawn += uv_spawn
        update += uv_update
        renderer_contract["subuv"] = uv

    # 动态材质参数（与 zzz_fx_material 的槽约定一致）
    dyn = material_plan["dyn_params"]
    cd = ps.get("CustomDataModule")
    names = {0: "Particles.DynamicMaterialParameter", 1: "Particles.DynamicMaterialParameter1",
             2: "Particles.DynamicMaterialParameter2", 3: "Particles.DynamicMaterialParameter3"}
    for slot in sorted(int(k) for k in dyn):
        if slot in (0, 1):
            expr = custom_data_h(cd, slot, age, rnd, update_curves)
        elif slot == 2:
            expr = "Particles.UStable"
        else:
            expr = "float4(Particles.USize, 1.0 / Particles.Lifetime)"
        update.append((names[slot], "Vector4", expr))

    spawn = rnd.spawn_entries() + spawn_curves.entries + spawn
    update = update_curves.entries + update

    em = ps.get("EmissionModule")
    bursts, rate, distance_rate = [], 0.0, 0.0
    if em:
        for b in em["m_Bursts"]:
            probability = b.get("probability", 1.0)
            if probability == 0.0:
                continue  # Explicit source zero probability is an inert burst.
            if probability != 1.0:
                raise SpecError("%s burst 概率≠1 未实现" % path)
            count = burst_count(b["countCurve"], path)
            if count == 0:
                continue  # Serialized inactive count is not an extra emitter.
            cycles = b["cycleCount"] if b["cycleCount"] > 0 else 1
            if b["cycleCount"] == 0:
                raise SpecError("%s burst 无限循环未实现" % path)
            for k in range(cycles):
                bursts.append((b["time"] + k * b["repeatInterval"], count))
        rate = minmax_curve_const(em["rateOverTime"])
        distance_rate = minmax_curve_const(em["rateOverDistance"])
    emitter_spawn = []
    if distance_rate > 0:
        # Only a derived previous source-emitter position is retained. Native
        # SpawnPerUnit owns fractional count, spacing and emission lifecycle.
        # Rotation of an offset child must contribute, unlike Owner.Velocity.
        emission_position = "(Engine.Owner.Position + %s)" % qrot_h(owner_q,
                                      "(Engine.Owner.Scale * %s)" % ue_pos_h(chain.pos_h()))
        emitter_spawn = list(chain.temps) + [("Emitter.UEFX_PreviousEmissionPosition", "Position", emission_position)]
        emitter_update += list(chain.temps) + [
            ("Transient.UEFX_EmissionPosition", "Position", emission_position),
            ("Transient.UEFX_EmissionVelocity", "Vector", "(Engine.DeltaTime > 0.0 ? (Transient.UEFX_EmissionPosition-Emitter.UEFX_PreviousEmissionPosition)/Engine.DeltaTime : float3(0.0,0.0,0.0))"),
            ("Emitter.UEFX_PreviousEmissionPosition", "Position", "Transient.UEFX_EmissionPosition")]
    mesh_pid = str(rd["m_Mesh"]["m_PathID"])
    if mode == 4 and mesh_pid not in ue_assets:
        raise SpecError("%s 的网格 PathID %s 没有导入" % (path, mesh_pid))
    mats = [str(m["m_PathID"]) for m in rd["m_Materials"] if m["m_PathID"] != 0]
    if len(mats) != 1:
        raise SpecError("%s 有 %d 个材质，多材质网格粒子未实现" % (path, len(mats)))
    return {
        "name": re.sub(r"[^A-Za-z0-9_]", "_", path),
        "path": path, "local_space": sim_local if mode == 4 else False,
        "source_simulation_space": "local" if sim_local else "world", "source_scaling_mode": ps["scalingMode"],
        "loop": bool(ps["looping"]), "duration": ps["lengthInSec"], "delay": minmax_curve_const(ps["startDelay"]),
        "bursts": bursts, "rate": rate, "spawn": spawn, "update": update, "requirements": requirements,
        "emitter_spawn": emitter_spawn, "emitter_update": emitter_update,
        "distance_rate": distance_rate,
        "particle_equivalence": policy,
        "source_particle_lights": "unbound_no_light_renderer" if ps.get("LightsModule") else "disabled",
        "renderer": {"kind": "mesh" if mode == 4 else "sprite",
                     **({"mesh": ue_assets[mesh_pid]} if mode == 4 else {}), "material": material_paths[mats[0]],
                     "sort": rd["m_SortingOrder"], **renderer_contract},
    }
