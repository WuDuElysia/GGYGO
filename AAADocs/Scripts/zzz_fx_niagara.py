"""Unity ParticleSystem 预制体（.fx.json）→ Niagara 发射器方案（离线，不依赖 UE）。

一个渲染中的 ParticleSystem 节点对应一个 Niagara 发射器。粒子行为不套 Niagara 的高层模块，
而是用 Set Parameters 模块把 Unity 的公式逐项写成 HLSL 表达式，保证数值与 Unity 一致：

    发射器更新：Emitter State（Self、Once/Infinite、时长=lengthInSec、延迟=startDelay）
                 Spawn Burst（逐个 burst 的时刻与数量）/ Spawn Rate（rateOverTime）
    粒子生成：  Lifetime、各随机数、起始颜色/尺寸/旋转、世界空间发射器的出生位姿
    粒子更新：  Particle State（年龄、到寿命销毁）
                节点位姿 = 预制体根→节点的变换链（含 Legacy Animation 的旋转/位置曲线，按 System.Age 求值）
                Position / MeshOrientation / Scale / Color / DynamicMaterialParameter0..3

坐标约定（与网格导入一致）：Unity (x, y, z) 米 → UE (-x, z, y)×100 厘米；
四元数 (x, y, z, w) → (-x, z, y, w)；缩放 (sx, sy, sz) → (sx, sz, sy)。
所有 Unity 量先在 Unity 坐标里算好，最后一步才换到 UE。

未实现的模块（形状发射、速度、噪声、碰撞、子发射器、拖尾…）一旦启用就报错，不生成近似效果。
"""
import math
import re

UNITY_RENDER_MODE = {0: "Billboard", 1: "Stretch", 2: "HorizontalBillboard", 3: "VerticalBillboard", 4: "Mesh", 5: "None"}
# 已实现的模块；其余模块 enabled=true 时报错
SUPPORTED_MODULES = {"InitialModule", "EmissionModule", "ColorModule", "SizeModule", "RotationModule", "CustomDataModule"}


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


def check_modules(ps, path):
    for name, expected in (("simulationSpeed", 1.0), ("useUnscaledTime", False),
                           ("stopAction", 0), ("ringBufferMode", 0), ("playOnAwake", True)):
        if name in ps and ps[name] != expected:
            raise SpecError("%s %s=%r requires its source runtime lifecycle/time contract" % (path, name, ps[name]))
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
    if ps.get("ShapeModule", {}).get("enabled"):
        raise SpecError("%s 启用了 ShapeModule，形状发射未实现" % path)
    em = ps.get("EmissionModule") if ps.get("EmissionModule", {}).get("enabled") else None
    if em and minmax_curve_const(em["rateOverDistance"]) != 0.0:
        raise SpecError("%s rateOverDistance≠0 未实现" % path)


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


def emitter_spec(node, path_nodes, clip, ue_assets, material_paths, material_plan):
    path = "/".join(n["name"] for n in path_nodes)
    raw_ps, rd = node["particle"]["system"], node["particle"]["renderer"]
    # New source evidence preserves disabled modules as well as enabled ones.
    # Their serialized curves are inert and must never become live simulation.
    ps = {k: v for k, v in raw_ps.items() if not isinstance(v, dict) or "enabled" not in v
          or v["enabled"] or k == "InitialModule"}
    check_modules(ps, path)
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
    # 形状模块关闭时 Unity 从变换原点沿本地 +Z 以 startSpeed 发射；没有任何力，位移 = 速度 × 年龄
    spawn.append(("Particles.USpeed", "Float", minmax_curve_h(im["startSpeed"], eage, rnd.take(), spawn_curves)))
    local_pos = "(float3(0.0, 0.0, 1.0) * Particles.USpeed * Particles.Age)"

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
        if ps["scalingMode"] == 0 or not stationary:
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
    if mode != 4:
        raise SpecError("%s 渲染模式 %s 未实现（只做了 Mesh）" % (path, UNITY_RENDER_MODE.get(mode, mode)))
    align = rd["m_RenderAlignment"]
    update.append(("Particles.UPartQ", "Quat", qeuler_h("Particles.URot")))
    if align == 2:      # Local：网格随变换旋转
        q_u = qmul_h(chain.quat_h(), "Particles.UPartQ")
    elif align == 1:    # World：只用粒子自身旋转
        q_u = "Particles.UPartQ"
    else:
        raise SpecError("%s 网格对齐模式 %d 未实现" % (path, align))
    scale_u = "(Particles.USize * %s)" % f3(tscale)
    pose = list(chain.temps)
    owner_q = "Engine.Owner.Rotation"
    if align == 1:
        # World-aligned meshes keep world orientation even in local simulation.
        inverse_owner = "float4(-Engine.Owner.Rotation.xyz, Engine.Owner.Rotation.w)"
        q_local = qmul_h(inverse_owner, ue_quat_h(q_u)) if sim_local else ue_quat_h(q_u)
    else:
        q_local = ue_quat_h(q_u)
    pose_q = ("Particles.MeshOrientation", "Quat", q_local)
    # 粒子在节点本地的位移经节点变换到预制体根空间（scalingMode=Shape 时位置也按变换缩放，与 Hierarchical 同）
    pos_u = "(%s + %s)" % (chain.pos_h(), qrot_h(chain.quat_h(), "(%s * %s)" % (f3(chain.S), local_pos)))
    if sim_local:
        update += pose + [("Particles.Position", "Position", ue_pos_h(pos_u)), pose_q]
    else:
        # 世界空间：出生时把节点位置换到世界，之后沿出生时的方向直线运动；
        # Local 对齐的朝向仍按当前变换每帧更新（与 Unity 相同）
        spawn += [(n, t, e) for n, t, e in pose]
        spawn.append(("Particles.UWorldOrigin", "Position",
                      "(Engine.Owner.Position + %s)" % qrot_h("Engine.Owner.Rotation", "(Engine.Owner.Scale * %s)" % ue_pos_h(chain.pos_h()))))
        spawn.append(("Particles.UWorldDir", "Vector",
                      qrot_h("Engine.Owner.Rotation", "(Engine.Owner.Scale * %s)" % ue_pos_h(qrot_h(chain.quat_h(), "float3(0.0, 0.0, 1.0)")))))
        update += [(n, t, e) for n, t, e in pose]
        update.append(("Particles.Position", "Position",
                       "(Particles.UWorldOrigin + Particles.UWorldDir * Particles.USpeed * Particles.Age)"))
        world_q = ue_quat_h(q_u) if align == 1 else qmul_h(owner_q, ue_quat_h(q_u))
        update.append(("Particles.MeshOrientation", "Quat", world_q))
    update.append(("Particles.Scale", "Vector", ue_scale_h(scale_u)))

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
    bursts, rate = [], 0.0
    if em:
        for b in em["m_Bursts"]:
            if b.get("probability", 1.0) != 1.0:
                raise SpecError("%s burst 概率≠1 未实现" % path)
            count = minmax_curve_const(b["countCurve"])
            cycles = b["cycleCount"] if b["cycleCount"] > 0 else 1
            if b["cycleCount"] == 0:
                raise SpecError("%s burst 无限循环未实现" % path)
            for k in range(cycles):
                bursts.append((b["time"] + k * b["repeatInterval"], int(round(count))))
        rate = minmax_curve_const(em["rateOverTime"])
    mesh_pid = str(rd["m_Mesh"]["m_PathID"])
    if mesh_pid not in ue_assets:
        raise SpecError("%s 的网格 PathID %s 没有导入" % (path, mesh_pid))
    mats = [str(m["m_PathID"]) for m in rd["m_Materials"] if m["m_PathID"] != 0]
    if len(mats) != 1:
        raise SpecError("%s 有 %d 个材质，多材质网格粒子未实现" % (path, len(mats)))
    return {
        "name": re.sub(r"[^A-Za-z0-9_]", "_", path),
        "path": path, "local_space": sim_local,
        "loop": bool(ps["looping"]), "duration": ps["lengthInSec"], "delay": minmax_curve_const(ps["startDelay"]),
        "bursts": bursts, "rate": rate, "spawn": spawn, "update": update,
        "renderer": {"kind": "mesh", "mesh": ue_assets[mesh_pid], "material": material_paths[mats[0]],
                     "sort": rd["m_SortingOrder"]},
    }
