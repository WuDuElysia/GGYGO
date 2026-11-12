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
import json
import copy
import hashlib
from pathlib import Path
import zzz_fx_particle_renderer as PR
import zzz_fx_particle_motion as PM
import zzz_fx_particle_uv as PU

UNITY_RENDER_MODE = {0: "Billboard", 1: "Stretch", 2: "HorizontalBillboard", 3: "VerticalBillboard", 4: "Mesh", 5: "None"}
# 已实现的模块；其余模块 enabled=true 时报错
SUPPORTED_MODULES = {"InitialModule", "EmissionModule", "ColorModule", "SizeModule", "RotationModule", "CustomDataModule",
                     "ShapeModule", "UVModule", "VelocityModule", "ForceModule", "ClampVelocityModule", "LightsModule"}


class SpecError(Exception):
    pass


class AffineRequired(SpecError):
    """已知 TRS 表示不足；仅由完整 affine 消费器接管，不吞掉其它来源错误。"""


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


def _finite_h(value, components):
    """CPU VM 的 binary32 有限值检查；标量比较同时拒绝 NaN 和正负 Inf。"""
    values = [value] if components == 1 else ["(%s).%s" % (value, axis) for axis in "xyzw"[:components]]
    return "("+" && ".join("(abs(%s)<=3.4028234663852886e38)" % item for item in values)+")"


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


def emitter_curve_bounds(c, path):
    """核单曲线的有限值域；Hermite／加权Bezier取导数极值，不能用键值代替整段。"""
    scalar = c["scalar"]
    if type(scalar) not in (int, float):
        raise SpecError("%s 发射器倍率缺真实数值" % path)
    f(scalar)
    if c["minMaxState"] == 0:
        return scalar, scalar
    if c["minMaxState"] != 1:
        raise SpecError("%s 发射器随机模式%d缺原生随机生命周期消费者" % (path, c["minMaxState"]))
    curve = c["maxCurve"]
    keys = curve["m_Curve"]
    if not keys:
        raise SpecError("%s 发射器曲线为空" % path)
    if curve["m_PreInfinity"] != 2 or curve["m_PostInfinity"] != 2:
        raise SpecError("%s 发射器曲线需要明确的源区间外延拓" % path)
    values = []
    for key in keys:
        f(key["time"])
        f(key["value"])
        values.append(key["value"])
    for a, b in zip(keys, keys[1:]):
        dt = b["time"]-a["time"]
        if dt < 0:
            raise SpecError("%s 发射器曲线时间未排序" % path)
        if dt == 0:
            continue
        out_slope, in_slope = a["outSlope"], b["inSlope"]
        if math.isnan(out_slope) or math.isnan(in_slope):
            raise SpecError("%s 发射器曲线切线含NaN" % path)
        if math.isinf(out_slope) or math.isinf(in_slope):
            continue  # 原步进段只取已登记的端点值。
        w0 = a["outWeight"] if a.get("weightedMode", 0) in (2, 3) else 1/3
        w1 = b["inWeight"] if b.get("weightedMode", 0) in (1, 3) else 1/3
        if not 0 <= w0 <= 1 or not 0 <= w1 <= 1:
            raise SpecError("%s 加权曲线时间柄不在[0,1]" % path)
        y0, y3 = a["value"], b["value"]
        y1, y2 = y0+w0*dt*out_slope, y3-w1*dt*in_slope
        if y0 == y1 == y2 == y3:
            continue  # 真正恒定的Bezier控制点，不由系数消去误差制造时间变化。
        c3, c2, c1 = -y0+3*y1-3*y2+y3, 3*y0-6*y1+3*y2, -3*y0+3*y1
        for value in (c3, c2, c1):
            f(value)
        qa, qb, qc = 3*c3, 2*c2, c1
        roots = []
        if qa == 0:
            if qb != 0:
                roots.append(-qc/qb)
        else:
            disc = qb*qb-4*qa*qc
            if disc >= 0:
                root = math.sqrt(disc)
                roots.extend(((-qb-root)/(2*qa), (-qb+root)/(2*qa)))
        for u in roots:
            if 0 < u < 1:
                values.append(((c3*u+c2)*u+c1)*u+y0)
    values = [scalar*value for value in values]
    for value in values:
        f(value)
    return min(values), max(values)


def minmax_curve_const(c):
    """发射器常量可来自真正恒定的单曲线；变化值和随机生命周期仍明确拒绝。"""
    low, high = emitter_curve_bounds(c, "EmitterParameter")
    if low != high:
        raise SpecError("发射器级参数需要常量；实际单曲线随时间变化")
    return low


def emission_rate(c, path, emitter_update):
    """派生当次EmitterUpdate速率；原生SpawnRate继续唯一负责分数计数和出生时序。"""
    low, high = emitter_curve_bounds(c, path)
    if low < 0:
        raise SpecError("%s 源发射率曲线含负值" % path)
    if low == high:
        return low
    program = CurveProgram("EmitterRate")
    attribute = "Emitter.UEFX_SpawnRate"
    expression = minmax_curve_h(c, "Emitter.NormalizedLoopAge", "0.0", program)
    emitter_update.extend(program.entries)
    emitter_update.append((attribute, "Float", expression))
    return {"kind": "EmitterSourceCurve", "attribute": attribute,
            "source_field": path, "bounds": [low, high]}


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


def project_gradient_policy(policy):
    """明确 UE 移植的未知 Gradient 核；保原 key、时间与最终颜色变换。"""
    if policy is None:
        return None
    keys = {"configuration_mode", "mode2_kernel", "decision_reference"}
    if (not isinstance(policy, dict) or set(policy) != keys
            or policy["configuration_mode"] != "ProjectConfigured" or policy["mode2_kernel"] != "LinearRGBAKeys"
            or not isinstance(policy["decision_reference"], str) or not policy["decision_reference"]):
        raise SpecError("Gradient2 requires explicit ProjectConfigured LinearRGBAKeys policy")
    return dict(policy)


def gradient_h(g, t, project_gradient=None):
    """Unity Gradient → float4 HLSL。颜色与 alpha 各自分段线性（mode 0）或阶跃（mode 1）。"""
    mode = g["m_Mode"]
    if mode not in (0, 1) and not (mode == 2 and project_gradient_policy(project_gradient) is not None):
        raise SpecError("Gradient 模式 %r 未实现或缺明确项目核" % mode)
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


def minmax_gradient_h(g, t, rand_attr, project_gradient=None):
    s = g["minMaxState"]
    if s == 0:
        return f4(color_of(g["maxColor"]))
    if s == 1:
        return gradient_h(g["maxGradient"], t, project_gradient)
    if s == 2:
        return "lerp(%s, %s, %s)" % (f4(color_of(g["minColor"])), f4(color_of(g["maxColor"])), rand_attr)
    if s == 3:
        return "lerp(%s, %s, %s)" % (gradient_h(g["minGradient"], t, project_gradient), gradient_h(g["maxGradient"], t, project_gradient), rand_attr)
    if s == 4:
        return gradient_h(g["maxGradient"], rand_attr, project_gradient)
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
        """直接检验 S·R=R·S，涵盖保留缩放特征子空间的复合轴半周旋转。

        容差只容纳源 float32 四元数的舍入；不分解矩阵、不修改原旋转或缩放。
        """
        columns = [qrot(q, axis) for axis in ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))]
        tolerance = 1e-7 * max(1., *(abs(value) for value in self.S))
        return all(abs((self.S[i] - self.S[j]) * columns[j][i]) <= tolerance
                   for i in range(3) for j in range(3))

    def rotation_curve_commutes(self, keys):
        """证明端值和切线共同支撑的整个四元数子空间可交换，而非采样键点。

        Hermite 曲线及归一化保持该坐标子空间。交换子对四元数是齐次二次式；
        在所有基向量及两两和上成立，才允许整段。无法证明时保留矩阵路径拒绝。
        """
        support = {i for key in keys for field in ("value", "in", "out")
                   for i, value in enumerate(key[field]) if value != 0.}
        basis = [tuple(float(i == axis) for i in range(4)) for axis in sorted(support)]
        if not all(self.commutes(vector) for vector in basis):
            return False
        return all(self.commutes(tuple((a[k] + b[k]) / math.sqrt(2.) for k in range(4)))
                   for i, a in enumerate(basis) for b in basis[i + 1:])

    def scale_after_rotation(self, q):
        """静态旋转可交换缩放轴时检验 S·R=R·S'，保持符号和原四元数。

        四分之一周旋转会交换非均匀缩放轴，并不产生切变。只在完整矩阵
        残差满足既有源 float32 容差时返回 S'；真实切变继续使用矩阵路径。
        """
        columns = [qrot(q, axis) for axis in ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))]
        lengths = [sum(v * v for v in column) for column in columns]
        if any(value == 0. for value in lengths):
            return None
        scale = tuple(sum(self.S[i] * columns[j][i] ** 2 for i in range(3)) / lengths[j]
                      for j in range(3))
        tolerance = 1e-7 * max(1., *(abs(value) for value in self.S))
        if any(abs((self.S[i] - scale[j]) * columns[j][i]) > tolerance
               for i in range(3) for j in range(3)):
            return None
        return scale

    def push(self, pos, rot, scale, anim_rot=None, anim_pos=None, t=None):
        if getattr(self, "sheared", False):
            raise AffineRequired("切变节点下还有子节点，lossyScale 近似不再成立，需要矩阵路径")
        if anim_rot and not self.rotation_curve_commutes(anim_rot):
            raise AffineRequired("父节点非均匀缩放 %r 下无法证明旋转动画整区间可交换，需要矩阵路径" % (self.S,))
        rotated_scale = self.S if self.commutes(rot) else self.scale_after_rotation(rot) if anim_rot is None else None
        if rotated_scale is None:
            # The leaf origin and world quaternion are still exact. No lossy
            # scale is invented here; consumers must prove they do not use it.
            if anim_pos is not None:
                raise AffineRequired("切变节点位置动画需要矩阵变换路径")
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
        self.S = tuple(rotated_scale[i] * scale[i] for i in range(3))

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


def rotation_chain(path_nodes, clip, time):
    """仅累积真实层级四元数；完整原点另由AffineChain求值，不从shear分解旋转。"""
    chain, names = Chain("Particles.URotationChain"), []
    for node in path_nodes:
        names.append(node["name"])
        path = "/".join(names)
        if clip and path in clip["euler"]:
            raise SpecError("节点 %s 的欧拉角动画尚无消费路径" % path)
        rotation = clip["rotation"].get(path) if clip else None
        chain.push((0.,0.,0.), _vals(node["rot"],"xyzw"), (1.,1.,1.), rotation, None, time)
    return chain


class AffineChain:
    """按原节点顺序乘完整 TRS；列向量和原点不分解为近似旋转／缩放。"""

    def __init__(self, prefix):
        self.prefix, self.temps = prefix, []
        self.columns = ["float3(1,0,0)", "float3(0,1,0)", "float3(0,0,1)"]
        self.position, self.bound_scale = "float3(0,0,0)", 1.0
        self.invertible = True

    def temp(self, kind, expression):
        name = "%s%d" % (self.prefix, len(self.temps))
        self.temps.append((name, kind, expression))
        return name

    @staticmethod
    def vector(columns, value):
        return "((%s)*(%s).x+(%s)*(%s).y+(%s)*(%s).z)" % (
            columns[0], value, columns[1], value, columns[2], value)

    def push(self, node, rotation, position, time):
        scale = _vals(node["scale"], "xyz")
        if any(not math.isfinite(v) for v in scale):
            raise SpecError("affine 节点缩放包含非法数值")
        self.invertible = self.invertible and all(v != 0 for v in scale)
        self.bound_scale *= max(abs(v) for v in scale)
        if not math.isfinite(self.bound_scale) or self.bound_scale < 0:
            raise SpecError("affine 层级界限无效")
        p = ("float3(%s)" % ",".join(anim_curve_h(position, k, time) for k in range(3))
             if position else f3(_vals(node["pos"], "xyz")))
        q = ("normalize(float4(%s))" % ",".join(anim_curve_h(rotation, k, time) for k in range(4))
             if rotation else f4(_vals(node["rot"], "xyzw")))
        q = self.temp("Quat", q)
        previous = self.columns
        self.position = self.temp("Vector", "(%s+%s)" % (self.position, self.vector(previous, p)))
        self.columns = [self.temp("Vector", self.vector(previous, qrot_h(q, f3(
            tuple(scale[i] if i == axis else 0.0 for i in range(3)))))) for axis in range(3)]

    def apply(self, value):
        return "(%s+%s)" % (self.position, self.vector(self.columns, value))

    def inverse_vector(self, value, valid_frame=None):
        if not self.invertible:
            raise SpecError("source simulation frame is singular; inverse-vector conversion is undefined")
        a, b, c = self.columns
        determinant = "dot(%s,cross(%s,%s))" % (a,b,c)
        if valid_frame is not None:
            determinant = "(%s ? %s : 1.0)" % (valid_frame,determinant)
        result = "(float3(dot(cross(%s,%s),%s),dot(cross(%s,%s),%s),dot(cross(%s,%s),%s))/%s)" % (
            b, c, value, c, a, value, a, b, value, determinant)
        return "(%s ? %s : float3(0,0,0))" % (valid_frame,result) if valid_frame is not None else result


def affine_chain(path_nodes, clip, time, prefix):
    chain, names = AffineChain(prefix), []
    for node in path_nodes:
        names.append(node["name"])
        path = "/".join(names)
        if clip and (path in clip["scale"] or path in clip["euler"]):
            raise SpecError("节点 %s 的缩放/欧拉角动画未实现" % path)
        chain.push(node, clip["rotation"].get(path) if clip else None,
                   clip["position"].get(path) if clip else None, time)
    return chain


def mesh_alignment_error(path, alignment):
    """指出缺失的源基底契约，不借 Native 朝向轴或模型外形代填。"""
    name, missing = {
        0: ("View", "source per-view XYZ basis and affine/particle-rotation multiplication order"),
        4: ("Velocity", "source forward axis, secondary-up/roll reference and affine/particle-rotation multiplication order"),
    }[alignment]
    return SpecError("%s MissingSourceMeshAlignment: %s requires %s; native mesh +X and native zero-speed direction are not source evidence" % (
        path, name, missing))


def _mesh_alignment_basis(matrix, alignment):
    """目标 T 与源参考 F_n 共同供唯一位置／normal通路；不读场景纹理。"""
    code = []
    for i, column in enumerate(matrix.columns):
        code.append("float3 FXNode%d=mul(float3(-(%s).x,(%s).z,(%s).y),FXRoot);" % (i, column, column, column))
    code += [
        "float3 FXRefFront=" + AffineChain.vector(["FXNode0", "FXNode1", "FXNode2"], f3(alignment["front_axis"])) + ";",
        "float3 FXRefUp=" + AffineChain.vector(["FXNode0", "FXNode1", "FXNode2"], f3(alignment["up_axis"])) + ";",
        "float FXRefLength=dot(FXRefFront,FXRefFront);",
        "float3 FXFnZ=FXRefLength>0.0 ? FXRefFront*rsqrt(FXRefLength) : float3(0,0,0);",
        "FXRefUp-=FXFnZ*dot(FXRefUp,FXFnZ);",
        "float FXUpLength=dot(FXRefUp,FXRefUp);",
        "float3 FXFnY=FXUpLength>0.0 ? FXRefUp*rsqrt(FXUpLength) : float3(0,0,0);",
        "float3 FXFnX=cross(FXFnY,FXFnZ);",
        "float3 FXRootLengths=float3(length(FXRoot[0]),length(FXRoot[1]),length(FXRoot[2]));",
        "float FXRootMin=min(FXRootLengths.x,min(FXRootLengths.y,FXRootLengths.z));",
        "float FXRootCondition=FXRootMin>0.0 ? max(FXRootLengths.x,max(FXRootLengths.y,FXRootLengths.z))/FXRootMin : 0.0;",
        "float4 FXParticleQ=" + qeuler_h("FXParticleEuler") + ";"]
    if alignment["alignment"] == "View":
        code += [
            "bool FXPrevious=FXPreviousView>0.5;",
            "float3 FXCameraX=FXPrevious ? ResolvedView.PrevViewToTranslatedWorld[0].xyz : ResolvedView.ViewRight;",
            "float3 FXCameraY=FXPrevious ? ResolvedView.PrevViewToTranslatedWorld[1].xyz : ResolvedView.ViewUp;",
            "float3 FXCameraZ=FXPrevious ? ResolvedView.PrevViewToTranslatedWorld[2].xyz : ResolvedView.ViewForward;"]
        for i, axis in enumerate(alignment["view_xyz"]):
            code.append("float3 FXT%d=%s;" % (i, AffineChain.vector(["FXCameraX", "FXCameraY", "FXCameraZ"], f3(axis))))
    else:
        up = "FXFnY" if alignment["velocity_up_reference"] == "NodeUp" else f3(alignment["world_up"])
        code += [
            "float3 FXTravel=mul(FXVelocity,FXRoot);",
            "float FXTravelSquared=dot(FXTravel,FXTravel);",
            "float3 FXT2=FXTravelSquared>0.0 ? FXTravel*rsqrt(FXTravelSquared) : float3(0,0,0);",
            "float3 FXT0=cross(%s,FXT2);" % up,
            "float FXCrossSquared=dot(FXT0,FXT0);",
            "FXT0*=FXCrossSquared>0.0 ? rsqrt(FXCrossSquared) : 0.0;",
            "float3 FXT1=cross(FXT2,FXT0);"]
    roll = math.radians(math.remainder(alignment["roll_offset_degrees"], 360.0))
    code += [
        "float3 FXRollX=FXT0*%s+FXT1*%s;" % (f(math.cos(roll)), f(math.sin(roll))),
        "FXT1=FXT1*%s-FXT0*%s;" % (f(math.cos(roll)), f(math.sin(roll))),
        "FXT0=FXRollX;"]
    return "\n".join(code)


def mesh_affine_adapter(node, path_nodes, clip, *, project_alignment=None, euler_components=None, source_components=0):
    """规划确实需要的网格 affine 通路；不能完整承载的空间／数据明确拒绝。"""
    ps, rd = node["particle"]["system"], node["particle"]["renderer"]
    alignment = PR.mesh_alignment_policy(project_alignment)
    source_alignment = rd["m_RenderAlignment"]
    if alignment is not None and alignment["alignment"] == "NativeCameraPlane":
        if rd["m_RenderMode"] != 4 or source_alignment != 0 \
                or str(node["transform"]) != alignment["source_transform"]:
            raise SpecError("原生 Mesh 相机平面选择不属于准确源 View Mesh")
        chain = node_chain(None, path_nodes, clip, "System.Age")
        if getattr(chain, "sheared", False) and ps["scalingMode"] == 0:
            raise SpecError("原生 Mesh 相机平面不能丢弃完整源 shear；需要对应 WPO 基底合同")
        return None
    if source_alignment in (0, 4) and alignment is None:
        raise mesh_alignment_error("/".join(n["name"] for n in path_nodes), source_alignment)
    if alignment is not None:
        if rd["m_RenderMode"] != 4 or source_alignment != {"View": 0, "Velocity": 4}[alignment["alignment"]] \
                or str(node["transform"]) != alignment["source_transform"] or not rd["m_AllowRoll"] \
                or rd["m_MotionVectors"] != 1:
            raise SpecError("Mesh 项目基底不属于准确源 Renderer／Transform／Object motion-vector合同")
        if any((ps.get(k) or {}).get("enabled", False) for k in ("ShapeModule", "VelocityModule", "ClampVelocityModule", "NoiseModule")):
            raise SpecError("Mesh 项目基底仅准本批无复合运动的三处真实来源")
        speed = ps["InitialModule"]["startSpeed"]
        if alignment["alignment"] == "Velocity" and (speed["minMaxState"] != 0
                or PR.number(speed["scalar"], "Mesh.startSpeed") <= 0.0):
            raise SpecError("Mesh Velocity 必须证明源初速严格正；不猜零速朝向")
    try:
        chain = node_chain(None, path_nodes, clip, "System.Age")
        needed = getattr(chain, "sheared", False) and ps["scalingMode"] == 0
    except AffineRequired:
        needed = True
    if not needed and alignment is None:
        return None
    if rd["m_RenderMode"] != 4 or ps["moveWithTransform"] != 0 or ps["scalingMode"] != 0:
        raise SpecError("affine 网格需要 Local 模拟／Hierarchy 缩放的完整消费通路")
    if rd["m_RenderAlignment"] != 2 and alignment is None:
        if rd["m_RenderAlignment"] in (0, 4):
            raise mesh_alignment_error("/".join(n["name"] for n in path_nodes), rd["m_RenderAlignment"])
        raise SpecError("affine 网格对齐模式 %r 尚无完整消费通路" % rd["m_RenderAlignment"])
    pivot = PR.vector(rd, "m_Pivot", "/".join(n["name"] for n in path_nodes))
    pivot_cm = (-pivot[0] * 100.0, pivot[2] * 100.0, pivot[1] * 100.0)
    matrix = affine_chain(path_nodes, clip, "FXAffineTransport.x", "FXA")
    if alignment is not None and not matrix.invertible:
        raise SpecError("项目 Mesh reference frame 包含零缩放，不能构造 F_n")
    # 完全坍缩时用单位原生基底表达零目标矩阵；不是替换源缩放或法线。
    bound_scale = matrix.bound_scale if matrix.bound_scale > 0.0 else 1.0
    declarations = ["%s %s = %s;" % ("float4" if kind == "Quat" else "float3", name, value)
                    for name, kind, value in matrix.temps]
    c = matrix.columns
    # UE C=(-X,Z,Y)，方向只换轴；米/厘米只在粒子位置与原 Mesh 导入链处理。
    common = "\n".join(declarations) + "\n" + "\n".join([
        "float3x3 FXRoot = DFToFloat3x3(GetPrimitiveData(Parameters).LocalToWorld);",
        "float3x3 FXRootInv = DFToFloat3x3(GetPrimitiveData(Parameters).WorldToLocal);",
        "float3x3 FXNative = DFToFloat3x3(Parameters.InstanceLocalToWorld);"])
    if alignment is not None:
        common += "\n" + _mesh_alignment_basis(matrix, alignment)
    for axis in range(3):
        v = "FXV%d" % axis
        u = "FXU%d" % axis
        native = "FXNative[%d] * FXAffineTransport.%s" % (axis, "yzw"[axis])
        common += "\nfloat3 %s = mul(%s, FXRootInv);" % (v, native)
        common += "\nfloat3 %s = float3(-%s.x,%s.z,%s.y);" % (u, v, v, v)
        if alignment is None:
            value = AffineChain.vector(c, u)
            common += "\nfloat3 FXM%d = %s;" % (axis, value)
            common += "\nfloat3 FXB%d = mul(float3(-FXM%d.x,FXM%d.z,FXM%d.y)/%s,FXRoot);" % (
                axis, axis, axis, axis, f(bound_scale))
        else:
            divisor = "(%s*FXRootCondition)" % f(bound_scale)
            common += "\n%s *= %s>0.0 ? rcp(%s) : 0.0;" % (u, divisor, divisor)
            before_h = qrot_h("FXParticleQ", u) if alignment["order"] == "THRS" else u
            common += "\nfloat3 FXWorld%d=%s;" % (axis, AffineChain.vector(["FXNode0", "FXNode1", "FXNode2"], before_h))
            common += "\nfloat3 FXH%d=float3(dot(FXFnX,FXWorld%d),dot(FXFnY,FXWorld%d),dot(FXFnZ,FXWorld%d));" % (
                axis, axis, axis, axis)
            after_h = "FXH%d" % axis
            if alignment["order"] == "TRHS":
                after_h = qrot_h("FXParticleQ", after_h)
            common += "\nfloat3 FXB%d=%s;" % (axis, AffineChain.vector(["FXT0", "FXT1", "FXT2"], after_h))
    # Native MeshOffset 先乘粒子 Scale 再旋转；完整矩阵修正同时作用于原顶点与 Pivot。
    # 平移不改法线，原逆转置通路保留。
    mesh_position = "MeshPos" if not any(pivot) else "(MeshPos+%s)" % f3(pivot_cm)
    wpo = common + "\nfloat3 FXVertex=%s;" % mesh_position + \
        "\nreturn FXVertex.x*(FXB0-FXNative[0])+FXVertex.y*(FXB1-FXNative[1])+FXVertex.z*(FXB2-FXNative[2]);"
    normal = common + "\nfloat3 c0=cross(FXB1,FXB2),c1=cross(FXB2,FXB0),c2=cross(FXB0,FXB1);" \
        "\nfloat determinant=dot(FXB0,c0);" \
        "\nfloat3 normal=MeshNormal.x*c0+MeshNormal.y*c1+MeshNormal.z*c2;" \
        "\nif(determinant!=0.0) normal/=determinant;" \
        "\nfloat lengthSquared=dot(normal,normal);" \
        "\nreturn lengthSquared>0.0 ? normal*rsqrt(lengthSquared) : float3(0,0,0);"
    return {"mode": "full_affine_local_mesh_v1", "bound_scale": bound_scale,
            "source_pivot_cm": pivot_cm, "pivot_consumption": "NativeMeshOffsetPlusAffineVertexCorrection",
            "transport": "DP3=System.Age,sign(UE ParticleSize.xyz)",
            **({"project_alignment": PR.mesh_alignment_transport(alignment, euler_components, source_components)} if alignment is not None else {}),
            "wpo_inputs": ["FXAffineTransport", "MeshPos"] + (["FXParticleEuler", "FXPreviousView"] +
                (["FXVelocity"] if alignment["alignment"] == "Velocity" else []) if alignment is not None else []),
            "wpo_code": wpo,
            "normal_inputs": ["FXAffineTransport", "MeshNormal"] + (["FXParticleEuler", "FXPreviousView"] +
                (["FXVelocity"] if alignment["alignment"] == "Velocity" else []) if alignment is not None else []),
            "normal_code": normal,
            "bounds": "NativeDynamicSphereWithPositiveScaleBound", "native_verified": False}


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


def project_light_policy(policy):
    """项目光照单位与衰减选择；源颜色、曲线及引用仍独立保留。"""
    if policy is None:
        return None
    keys = {"configuration_mode", "decision_reference", "falloff", "intensity_scale", "range_scale",
            "size_metric", "affect_translucency", "volumetric_scattering", "component_range_scale"}
    if not isinstance(policy, dict) or set(policy) != keys or policy["configuration_mode"] != "ProjectConfigured" \
            or policy["falloff"] != "InverseSquared" or policy["size_metric"] != "MaxAbsXYZ" \
            or policy["component_range_scale"] != "MinAbsOwnerScale" \
            or not isinstance(policy["decision_reference"], str) or not policy["decision_reference"] \
            or type(policy["affect_translucency"]) is not bool:
        raise SpecError("Particle lights require an explicit native point-light configuration")
    for key in ("intensity_scale", "range_scale", "volumetric_scattering"):
        if PR.number(policy[key], key) < 0:
            raise SpecError("Particle light parameter must be nonnegative: " + key)
    return dict(policy)


def point_light_contract(source, policy, path):
    """读取明确点光源的必要字段；未消费扩展字段保留在原 typed 输入。"""
    policy = project_light_policy(policy)
    if policy is None or not isinstance(source, dict) or set(source) != {"identity", "light"}:
        raise SpecError("%s bound particle Light requires its exact typed template and UE policy" % path)
    body = source["light"]
    if (body["m_Type"] != 2 or body["m_Enabled"] != 1 or body["m_UseColorTemperature"]
            or body["m_Shadows"]["m_Type"] != 0
            or any(body[k]["m_PathID"] or body[k]["m_FileID"] for k in ("m_Cookie", "m_Flare"))):
        raise SpecError("%s native particle Light only supports the declared unshadowed Point/no-cookie/no-temperature template" % path)
    color = tuple(PR.number(body["m_Color"][a], "Light.Color."+a) for a in "rgba")
    intensity, radius = (PR.number(body[k], "Light."+k) for k in ("m_Intensity", "m_Range"))
    if intensity < 0 or radius < 0:
        raise SpecError("%s source Point intensity/range must be finite and nonnegative" % path)
    consumed = {k: body[k] for k in ("m_Type", "m_Enabled", "m_UseColorTemperature", "m_Color", "m_Intensity", "m_Range",
                                   "m_Cookie", "m_Flare")}
    consumed["m_Shadows"] = {"m_Type": body["m_Shadows"]["m_Type"]}
    return {"policy": policy, "source_identity": source["identity"], "source_template_consumed": consumed,
            "source_template_unconsumed_fields": sorted(set(body)-set(consumed)),
            "source_unconsumed_shadow_fields": sorted(set(body["m_Shadows"])-{"m_Type"}),
            "source_color": color, "source_intensity": intensity, "source_range_metres": radius,
            "source_runtime_and_photometric_equivalence": False}


def particle_light_contract(ps, source, policy, path):
    """核准确本地 Light 模板；停用节点仍可能被活动 LightsModule 引用。"""
    module = ps.get("LightsModule")
    if not module or not module["enabled"] or module["light"]["m_PathID"] == 0:
        return None
    result = point_light_contract(source, policy, path)
    if module["ratio"] != 1.0 or type(module["maxLights"]) is not int or module["maxLights"] <= 0:
        raise SpecError("%s particle Light requires ratio=1 and a positive source cap" % path)
    maximum_particles = ps["InitialModule"]["maxNumParticles"]
    if type(maximum_particles) is int and 0 < maximum_particles <= module["maxLights"]:
        # 原生 FixedCount 限制同帧活粒子；不以速率总量替代活粒子上限，也不增设灯计数器。
        # 满额时的出生选择沿用 Niagara；这里只保源数量边界，不声明 Unity 的淘汰顺序等价。
        return {**result, "source_module": module, "native_particle_limit": maximum_particles,
                "allocation_policy": "NiagaraFixedCount", "source_eviction_order_verified": False}
    # 本批实际源均为一次单粒子 burst；用真实生成上界证明 cap，不添加计数器或另一调度。
    emission = ps.get("EmissionModule")
    if ps["looping"] or not emission or not emission["enabled"] \
            or minmax_curve_const(emission["rateOverTime"]) != 0 \
            or minmax_curve_const(emission["rateOverDistance"]) != 0:
        raise SpecError("%s particle Light cap needs a finite nonlooping burst bound" % path)
    maximum = 0
    for burst in emission["m_Bursts"]:
        count = burst_count(burst["countCurve"], path)
        if type(burst["cycleCount"]) is not int or burst["cycleCount"] <= 0:
            raise SpecError("%s particle Light burst must have finite positive cycles" % path)
        maximum += (count["max"] if isinstance(count, dict) else count) * burst["cycleCount"]
    if maximum > module["maxLights"]:
        raise SpecError("%s source particle Light cap requires its real per-frame selection consumer" % path)
    return {**result, "source_module": module, "proven_spawn_upper_bound": maximum}


def particle_light_entries(contract, rnd, curves):
    """原粒子的寿命／位置／颜色驱动同实例原生 LightRenderer。"""
    module, policy = contract["source_module"], contract["policy"]
    intensity = minmax_curve_h(module["intensityCurve"], "Particles.NormalizedAge", rnd.take(), curves)
    radius = minmax_curve_h(module["rangeCurve"], "Particles.NormalizedAge", rnd.take(), curves)
    color = f3(contract["source_color"][:3])
    if module["color"]:
        color = "(%s*Particles.Color.rgb)" % color
    alpha = "Particles.Color.a" if module["intensity"] else "1.0"
    size = "max(abs(Particles.USize.x),max(abs(Particles.USize.y),abs(Particles.USize.z)))" if module["range"] else "1.0"
    return [("Particles.UEFX_LightColor", "LinearColor", "float4(%s*(%s)*%s*(%s),1.0)" % (
                color, intensity, f(contract["source_intensity"]*policy["intensity_scale"]), alpha)),
            ("Particles.UEFX_LightRadius", "Float", "((%s)*%s*(%s))" % (
                radius, f(contract["source_range_metres"]*100.0*policy["range_scale"]), size)),
            ("Particles.UEFX_LightEnabled", "Bool", "true"),
            ("Particles.UEFX_LightScattering", "Float", f(policy["volumetric_scattering"]))]


def component_bounds_radius(path_nodes, clip, extent_metres, *, scale_extent):
    """由节点原位置、Hermite 控制点凸包及常量 scale 导出根内球界限。"""
    radius, inherited_scale, names = 0.0, 1.0, []
    for node in path_nodes:
        names.append(node["name"])
        curve = clip["position"].get("/".join(names)) if clip else None
        if curve:
            maxima = [max(abs(PR.number(key["value"][i], "Position.value")) for key in curve) for i in range(3)]
            for left, right in zip(curve, curve[1:]):
                dt = PR.number(right["time"], "Position.time")-PR.number(left["time"], "Position.time")
                if dt < 0:
                    raise SpecError("节点位置曲线必须按真实时间严格递增")
                if dt == 0:
                    continue  # 与现 curve_h 一致，重复时点仅取原端点值。
                for i in range(3):
                    slopes = left["out"][i], right["in"][i]
                    if any(type(v) not in (int, float) or math.isnan(v) for v in slopes):
                        raise SpecError("节点位置曲线斜率无效")
                    if any(math.isinf(v) for v in slopes):
                        continue  # 原 step 段，端点凸包已覆盖，不把合法 Infinity 斜率当 NaN。
                    controls = (left["value"][i]+PR.number(left["out"][i], "Position.out")*dt/3.0,
                                right["value"][i]-PR.number(right["in"][i], "Position.in")*dt/3.0)
                    maxima[i] = max(maxima[i], *(abs(v) for v in controls))
            position_radius = math.sqrt(sum(v*v for v in maxima))
        else:
            position_radius = math.sqrt(sum(PR.number(node["pos"][axis], "Node.position")**2 for axis in "xyz"))
        radius += inherited_scale*position_radius
        inherited_scale *= max(abs(PR.number(node["scale"][axis], "Node.scale")) for axis in "xyz")
    radius += PR.number(extent_metres, "source geometry extent")*(inherited_scale if scale_extent else 1.0)
    if not math.isfinite(radius) or radius < 0:
        raise SpecError("由真实几何／曲线计算的组件界限无效")
    return radius*100.0


def component_mesh_policy(policy):
    if policy is None:
        return None
    expected = {"configuration_mode": "ProjectConfigured", "native_source_mode": "Emitter",
        "lifecycle": "NativeComponentActivation", "material_age": {"DP0.x": "System.Age"},
        "motion_vectors": "NativeApproximateZeroLocalVelocity"}
    timing = set()
    if isinstance(policy, dict) and policy.get("native_source_mode") == "SingleParticle":
        expected.update(native_source_mode="SingleParticle", lifecycle="NativeFiniteParticle")
        timing = {"lifetime_seconds", "fade_start_seconds"}
        life = PR.number(policy.get("lifetime_seconds"), "ComponentMesh.lifetime_seconds")
        fade = PR.number(policy.get("fade_start_seconds"), "ComponentMesh.fade_start_seconds")
        if not 0 <= fade < life:
            raise SpecError("静态网格项目寿命须包含有限消退区间")
    if not isinstance(policy, dict) or set(policy) != {*expected, "decision_reference", *timing} \
            or any(policy[k] != value for k, value in expected.items()) \
            or not isinstance(policy["decision_reference"], str) or not policy["decision_reference"].strip():
        raise SpecError("静态Mesh需要明确Emitter/原系统年龄/原激活生命周期的项目合同")
    return dict(policy)


def validate_component_geometry(source):
    if not isinstance(source, dict) or source.get("winding") != "source" \
            or source.get("coordinate_conversion") != "UE C=(-X,Z,Y); Unity triangle winding; FBX Y-up reflect X, cm" \
            or source.get("requires_native_geometry_readback") is not True or source.get("native_geometry_verified") is not False:
        raise SpecError("静态Mesh缺准确source-winding/Native逐角读回合同")
    for key in ("source_json", "source_fbx"):
        pin = source[key]
        raw = Path(pin["path"]).read_bytes()
        if len(raw) != pin["size"] or hashlib.sha256(raw).hexdigest() != pin["sha256"]:
            raise SpecError("静态Mesh输入在准备后变化："+pin["path"])
    data = json.loads(Path(source["source_json"]["path"]).read_text(encoding="utf-8-sig"))
    colors = data["m_Colors"]
    if source.get("vertex_color_mode") == "SourceAbsentNativeWhite":
        if data["m_VertexCount"] <= 0 or colors is not None:
            raise SpecError("明确Native白色只允许源无颜色流")
    elif source.get("vertex_color_mode") != "SourceRGBA" or not isinstance(colors, list) \
            or len(colors) != data["m_VertexCount"]*4:
        raise SpecError("静态Mesh缺明确原RGBA/源无色NativeWhite模式")




def particle_trail_contract(node, path_nodes, policy):
    """只消费本批两槽／PerParticle源声明；未知enum6按显式UE几何政策保原值。"""
    path = "/".join(n["name"] for n in path_nodes) or "$root"
    if (not isinstance(policy, dict) or policy.get("schema") != "GGYGO.ProjectParticleTrails/v1"
            or policy.get("mode") != "NativeParticleReadPerParticleRibbon"
            or policy.get("source_render_mode_proven") is not False
            or policy.get("project_primary_geometry") != "Billboard"
            or policy.get("primary_material_slot") != 0 or policy.get("trail_material_slot") != 1
            or policy.get("sampling") != "SourceMinimumVertexDistanceInParentSimulationSpace"
            or policy.get("lifetime") != "SourceMultiplierTimesActualParentLifetime"
            or policy.get("parent_identity") != "FullNiagaraID"
            or policy.get("normal_tail") != "FiniteChildActiveWhileOriginalParentAlive"
            or not isinstance(policy.get("decision_reference"), str) or not policy["decision_reference"]
            or policy.get("source_attributes") != {"size": "Particles.USize", "emit_point": "Particles.UEFX_TrailEmitPoint"}):
        raise SpecError("逐粒子拖尾缺完整显式项目合同")
    entries = [row for row in policy["source_nodes"] if row["node"] == path]
    ps, rd = node["particle"]["system"], node["particle"]["renderer"]
    source = ps.get("TrailModule")
    if (len(entries) != 1 or source is None or entries[0]["source_transform"] != str(node["transform"])
            or (rd["m_RenderMode"] != entries[0]["source_render_mode"] or rd["m_RenderMode"] != 6)
            or rd["m_Enabled"] is not True or len(rd["m_Materials"]) != 2
            or rd["m_Materials"] != entries[0]["source_materials"]
            or any(not row["m_PathID"] for row in rd["m_Materials"])
            or hashlib.sha256(json.dumps(source,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
                != entries[0]["source_trail_sha256"]):
        raise SpecError("逐粒子拖尾不是准确源节点／两材质槽／原TrailModule")
    required = {"enabled": True, "mode": 0, "ratio": 1.0, "textureMode": 0, "ribbonCount": 1,
        "worldSpace": False, "dieWithParticles": True, "sizeAffectsWidth": True,
        "sizeAffectsLifetime": False, "inheritParticleColor": True, "generateLightingData": False,
        "splitSubEmitterRibbons": False, "attachRibbonsToTransform": False}
    if any(source[key] != value for key,value in required.items()):
        raise SpecError("逐粒子拖尾尚不支持此源生命周期／空间／宽色组合")
    lifetime = source["lifetime"]
    distance = source["minVertexDistance"]
    if (lifetime["minMaxState"] != 0 or not math.isfinite(lifetime["scalar"]) or lifetime["scalar"] <= 0
            or type(distance) not in (int,float) or not math.isfinite(distance) or distance < 0
            or source["widthOverTrail"]["minMaxState"] != 0 or source["widthOverTrail"]["scalar"] != 1.0):
        raise SpecError("逐粒子拖尾需要源常数寿命倍率／单位宽度曲线及有效最小距离")
    gradient = source["colorOverLifetime"]
    if gradient["minMaxState"] != 0 or any(gradient["maxColor"][a] != 1.0 for a in "rgba"):
        raise SpecError("逐粒子拖尾按寿命颜色曲线尚无已配置消费者")
    # 长度颜色由材质原 VS 输入消费；Native 几何 U 与粒子年龄保持独立。
    import zzz_fx_material as FM
    streams = policy["streams"]
    length_color = {"schema": "GGYGO.SourceTrailLengthColor/v1",
        "gradient": copy.deepcopy(source["colorOverTrail"]),
        "native_u_scale": streams["uv0_scale"][0], "native_u_offset": streams["uv0_offset"][0],
        "direction": policy["length_color_direction"]}
    FM.source_trail_length_color_contract({**generated_ribbon_context(), "source_trail_length_color": length_color})
    if (ps["moveWithTransform"] != 0 or ps["scalingMode"] != 1 or ps["InitialModule"]["size3D"]
            or any(_vals(n["scale"], "xyz") != (1.0,1.0,1.0) for n in path_nodes)):
        raise SpecError("本逐粒子拖尾合同只接已核Local模拟／Local scaling／单位源层级与标量宽度")
    return {"schema": "GGYGO.SourceParticleTrail/v1", "policy": copy.deepcopy(policy), "source_module": copy.deepcopy(source),
        "source_node": path, "source_transform": str(node["transform"]), "source_render_mode": rd["m_RenderMode"],
        "source_materials": copy.deepcopy(rd["m_Materials"]), "lifetime_multiplier": lifetime["scalar"],
        "minimum_vertex_distance_cm": distance*100.0, "parent_space": "World", "trail_space": "ComponentLocal",
        "width": "AbsoluteParentUSizeXMetresTimes100", "sampling_count_phase": "NativePreviousCompletedParentBuffer",
        "source_trail_length_color": length_color}


def particle_trail_primary_node(node, contract):
    """只改内存中的UE几何视图；原enum／两槽及模块正文留在准确合同中。"""
    if contract.get("source_transform") != str(node["transform"]):
        raise SpecError("逐粒子拖尾Primary视图与原节点身份不同")
    virtual = copy.deepcopy(node)
    virtual["particle"]["renderer"]["m_RenderMode"] = 0
    virtual["particle"]["renderer"]["m_Materials"] = [copy.deepcopy(contract["source_materials"][0])]
    return virtual



def configure_particle_trail_parent(spec, contract):
    """原父模拟只增派生采样状态；本地历史必要逆Root失败仍走唯一原Alive。"""
    capture = "Particles.UEFX_TrailCapturePosition"
    valid = "Transient.UEFX_TrailRootValid"
    root_ok = "(%s && %s && %s && min(abs(Engine.Owner.Scale.x),min(abs(Engine.Owner.Scale.y),abs(Engine.Owner.Scale.z)))>0.0)" % (
        _finite_h("Engine.Owner.Position", 3), _finite_h("Engine.Owner.Rotation", 4), _finite_h("Engine.Owner.Scale", 3))
    local = "(%s/(%s ? Engine.Owner.Scale : float3(1.0,1.0,1.0)))" % (
        qrot_h("float4(-Engine.Owner.Rotation.xyz,Engine.Owner.Rotation.w)", "(Particles.Position-Engine.Owner.Position)"), root_ok)
    delta = "(%s-Particles.UEFX_TrailLastPosition)" % capture
    point_distance = "sqrt(dot(%s,%s))" % (delta, delta)
    spec["spawn"] += [(capture, "Vector", local), ("Particles.UEFX_TrailLastPosition", "Vector", local),
        ("Particles.UEFX_TrailLastAge", "Float", "-1.0"), ("Particles.UEFX_TrailEmitPoint", "Bool", "true")]
    checks = [(valid, "Bool", root_ok), (capture, "Vector", local),
        ("Particles.UEFX_TrailEmitPoint", "Bool", "(Particles.UEFX_TrailLastAge<0.0 || %s>=%s)" %
             (point_distance, f(contract["minimum_vertex_distance_cm"]))),
        ("Particles.UEFX_TrailLastPosition", "Vector", "(Particles.UEFX_TrailEmitPoint ? %s : Particles.UEFX_TrailLastPosition)" % capture),
        ("Particles.UEFX_TrailLastAge", "Float", "(Particles.UEFX_TrailEmitPoint ? Particles.Age : Particles.UEFX_TrailLastAge)")]
    indices = [i for i,row in enumerate(spec["update"]) if row[0] == "Particles.UEFX_RuntimeFailure"]
    if indices:
        if len(indices) != 1:
            raise SpecError("原父粒子出现重复失败写入者")
        index = indices[0]
        old = spec["update"][index]
        spec["update"][index] = (old[0], old[1], "max((%s),(%s ? 0.0 : 21.0))" % (old[2], valid))
        spec["update"][index:index] = checks
    else:
        spec["spawn"] += [("Particles.UEFX_RuntimeFailure", "Float", "0.0"), ("Particles.Alive", "Bool", "true")]
        spec["update"] += checks + [("Particles.UEFX_RuntimeFailure", "Float", "(%s ? 0.0 : 21.0)" % valid),
                                     ("Particles.Alive", "Bool", "Particles.Alive")]
    spec["runtime_failure"] = PR.particle_trail_failure_transport(contract["source_transform"],
        contract["policy"]["decision_reference"], contract["source_node"], spec["name"], spec.get("runtime_failure"))
    # System只关闭原父的新发射；派生child另沿真实父存活与尾点排空收束。
    spec["emitter_update"].append(("Emitter.ExecutionState", "ExecutionState",
        "(System.ExecutionState==0 ? Emitter.ExecutionState : max(Emitter.ExecutionState,System.ExecutionState))"))
    return spec



def particle_trail_query_templates():
    """显式原生Function语句体；DI与每个output名由唯一作者桥替换。"""
    prefix = "Particles.UEFX_Trail"
    outputs = [[prefix+"ReadValid", "Bool"], [prefix+"ParentAlive", "Bool"], [prefix+"ParentID", "ID"],
        [prefix+"ParentLifetime", "Float"], [prefix+"ParentAge", "Float"], [prefix+"ParentColor", "LinearColor"],
        [prefix+"ParentUSize", "Vector"], [prefix+"ParentEmitPoint", "Bool"], [prefix+"ParentPosition", "Vector"]]
    def out(name):
        return "{{OUT:"+name+"}}"
    read_valid = " && ".join(["VLife", "VAge", "VColor", "VSize", "VEmit", "VPos",
        _finite_h(out(prefix+"ParentLifetime"), 1), out(prefix+"ParentLifetime")+">0.0",
        _finite_h(out(prefix+"ParentAge"), 1), _finite_h(out(prefix+"ParentPosition"), 3),
        _finite_h(out(prefix+"ParentUSize"), 3), _finite_h(out(prefix+"ParentColor"), 4)])
    body = [out(prefix+"ReadValid")+"=false;", out(prefix+"ParentAlive")+"=false;",
        out(prefix+"ParentID")+".Index=-1;",out(prefix+"ParentID")+".AcquireTag=-1;",
        out(prefix+"ParentLifetime")+"=0.0;",out(prefix+"ParentAge")+"=0.0;",
        out(prefix+"ParentColor")+"=float4(0,0,0,0);",out(prefix+"ParentUSize")+"=float3(0,0,0);",
        out(prefix+"ParentEmitPoint")+"=false;",out(prefix+"ParentPosition")+"=float3(0,0,0);",
        "bool IDValid=false; NiagaraID ParentID; ParentID.Index=-1; ParentID.AcquireTag=-1;",
        '{{DI}}.GetIDByIndex<Attribute="ID">(Engine.ExecIndex,IDValid,ParentID);',
        "if(IDValid) { int ParentIndex; {{DI}}.GetParticleIndex(ParentID,ParentIndex);",
        out(prefix+"ParentID")+"=ParentID;", out(prefix+"ParentAlive")+"=(ParentIndex>=0);",
        "if(ParentIndex>=0) { bool VLife=false; bool VAge=false; bool VColor=false; bool VSize=false; bool VEmit=false; bool VPos=false;",
        '{{DI}}.GetFloatByID<Attribute="Lifetime">(ParentID,VLife,'+out(prefix+"ParentLifetime")+');',
        '{{DI}}.GetFloatByID<Attribute="NormalizedAge">(ParentID,VAge,'+out(prefix+"ParentAge")+');',
        '{{DI}}.GetColorByID<Attribute="Color">(ParentID,VColor,'+out(prefix+"ParentColor")+');',
        '{{DI}}.GetVectorByID<Attribute="USize">(ParentID,VSize,'+out(prefix+"ParentUSize")+');',
        '{{DI}}.GetBoolByID<Attribute="UEFX_TrailEmitPoint">(ParentID,VEmit,'+out(prefix+"ParentEmitPoint")+');',
        '{{DI}}.GetVectorByID<Attribute="UEFX_TrailCapturePosition">(ParentID,VPos,'+out(prefix+"ParentPosition")+');',
        out(prefix+"ReadValid")+"=("+read_valid+");", "} }"]
    update_outputs = [[prefix+"ReadValid","Bool"],[prefix+"ParentAlive","Bool"]]
    update = [out(prefix+"ReadValid")+"=false;",out(prefix+"ParentAlive")+"=false;",
        "int ParentIndex; {{DI}}.GetParticleIndex(Particles.UEFX_TrailParentID,ParentIndex);",
        out(prefix+"ParentAlive")+"=(ParentIndex>=0);",
        "if(ParentIndex>=0) { bool VLife=false; float ParentLife=0.0;",
        '{{DI}}.GetFloatByID<Attribute="Lifetime">(Particles.UEFX_TrailParentID,VLife,ParentLife);',
        out(prefix+"ReadValid")+"=(VLife&&"+_finite_h("ParentLife", 1)+"&&ParentLife>0.0); }"]
    count_outputs = [["Emitter.UEFX_TrailCountSampled","Bool"],["Emitter.UEFX_TrailParentCount","Int"],
                     ["Emitter.UEFX_TrailSpawnRate","Float"],["Emitter.ExecutionState","ExecutionState"]]
    count = ["int ParentCount=0; {{DI}}.GetNumParticles(ParentCount);",
        out("Emitter.UEFX_TrailCountSampled")+"=(ParentCount>=0);",out("Emitter.UEFX_TrailParentCount")+"=ParentCount;",
        out("Emitter.UEFX_TrailSpawnRate")+"=(Engine.DeltaTime>0.0 ? float(ParentCount)/Engine.DeltaTime : 0.0);",
        out("Emitter.ExecutionState")+"=((System.ExecutionState==0 || ParentCount>0) ? 0 : (Engine.Emitter.NumParticles>0 ? 1 : 3));"]
    return {"spawn":{"outputs":outputs,"body":"\n".join(body)},
            "update":{"outputs":update_outputs,"body":"\n".join(update)},
            "count":{"outputs":count_outputs,"body":"\n".join(count)}}


def particle_trail_child_spec(parent, contract, material, material_target):
    """每点只在出生取原父快照；历史由同NS Native粒子持有，本地随Root且按父ID归还。"""
    if (material.get("renderer_kind") != "generated_ribbon" or material.get("generated_ribbon") != generated_ribbon_context()["generated_ribbon"]
            or material.get("source_trail_length_color") != contract["source_trail_length_color"]
            or material.get("dynamic_parameter_components") != 0xFFFF or material.get("output_contract") != "color"
            or str(material.get("source_selection",{}).get("material_pid")) != str(contract["source_materials"][1]["m_PathID"])):
        raise SpecError("源拖尾slot1材质缺完整22流／准确原MID")
    policy = contract["policy"]
    raw = policy["streams"]
    if (set(raw) != {"tc1","tc2","tc3","tc4","tc6_z_mode","tc6_w","uv0_scale","uv0_offset","uv1_scale","uv1_offset"}
            or raw["tc6_z_mode"] != "ParticleNormalizedAgeCopy"
            or type(raw["tc6_w"]) not in (int,float) or not math.isfinite(raw["tc6_w"])):
        raise SpecError("源拖尾需完整明确22输入配置")
    for key,count in {"tc1":4,"tc2":4,"tc3":4,"tc4":4,"uv0_scale":2,"uv0_offset":2,"uv1_scale":2,"uv1_offset":2}.items():
        if not isinstance(raw[key],list) or len(raw[key]) != count or any(type(v) not in (int,float) or not math.isfinite(v) for v in raw[key]):
            raise SpecError("源拖尾输入不是有限明确向量: "+key)
    prefix = "Particles.UEFX_Trail"
    valid = "(%sParentAlive && %sReadValid)" % (prefix,prefix)
    streams = [("Particles.DynamicMaterialParameter"+(str(i) if i else ""),"Vector4",f4(raw["tc"+str(i+1)])) for i in range(4)]
    streams += [("Particles.UEFX_RawTC6Z","Float","Particles.NormalizedAge"),("Particles.UEFX_RawTC6W","Float",f(raw["tc6_w"]))]
    spawn = [("Particles.Age","Float","0.0"),("Particles.NormalizedAge","Float","0.0"),
        ("Particles.Lifetime","Float","(%s ? min(%s*%sParentLifetime,max(0.0,(1.0-%sParentAge)*%sParentLifetime)) : 0.0)" %
            (valid,f(contract["lifetime_multiplier"]),prefix,prefix,prefix)),
        ("Particles.Position","Position","%sParentPosition" % prefix),
        ("Particles.Velocity","Vector","float3(0,0,0)"),
        ("Particles.RibbonWidth","Float","(%s ? abs(%sParentUSize.x)*100.0 : 0.0)" % (valid,prefix)),
        ("Particles.RibbonTwist","Float","0.0"), ("Particles.Color","LinearColor","%sParentColor" % prefix),
        # 出生失败须先送原Alive的DI；无效采样报告后由KeepAlive排除，不进入Ribbon历史。
        ("Particles.UEFX_RuntimeFailure","Float","(%sParentAlive && !%sReadValid ? 22.0 : 0.0)" % (prefix,prefix)),
        ("Particles.Alive","Bool","(%sParentAlive && (!%sReadValid || %sParentEmitPoint))" % (prefix,prefix,prefix))]+streams
    update = [("Particles.UEFX_RuntimeFailure","Float","max(Particles.UEFX_RuntimeFailure,(%sParentAlive && !%sReadValid ? 22.0 : 0.0))" % (prefix,prefix)),
              ("Particles.Alive","Bool","Particles.Alive")]
    # dieWithParticles=true：父身份退役后令原生ParticleState到期，不增加Kill模块或第二Alive消费者。
    update += [("Particles.Lifetime","Float","(%sParentAlive ? Particles.Lifetime : 0.0)" % prefix)] + streams
    return {"name":parent["name"]+"_ParticleTrail","path":parent["path"],"local_space":True,
        "loop":False,"duration":parent["duration"],"delay":parent["delay"],"rate":0,"bursts":[],
        "emitter_spawn":[],"emitter_update":[],"spawn":spawn,"update":update,"requirements":[],
        "particle_trail_child":{"parent_emitter":parent["name"],"contract":contract,"queries":particle_trail_query_templates()},
        "runtime_failure":PR.particle_trail_failure_transport(contract["source_transform"],policy["decision_reference"],contract["source_node"],parent["name"]),
        "renderer":{"kind":"particle_trail_ribbon","material":material_target,"sort":parent["renderer"]["sort"],
            "source_material_slot":1,"generated_ribbon":generated_ribbon_context()["generated_ribbon"],
            "source_trail_length_color":copy.deepcopy(contract["source_trail_length_color"]),
            "dynamic_parameter_components":0xFFFF,"source_particle_trail":contract,"field_renderer":None},
        "source_runtime_and_visual_acceptance":"pending"}


def generated_ribbon_context():
    """原材质作者公开的完整22标量布局，专用Age不占任何源TC。"""
    return {"kind": "generated_ribbon", "mesh": False, "generated_ribbon": {
        "schema": "GGYGO.GeneratedRibbonMaterial/v1", "uv_convention": "NativeUVToUnityUVDown",
        "raw_uv6": {"z_attribute": "Particles.UEFX_RawTC6Z", "w_attribute": "Particles.UEFX_RawTC6W"},
        "system_age": {"parameter": "UEFX_GeneratedRibbonSystemAge", "source": "System.Age"}}}


def generated_ribbon_policy(policy):
    """显式UE生成参数；未知源宿主不通过猜Mesh、默认材质或隐藏参数补齐。"""
    if (not isinstance(policy, dict) or set(policy) != {"mode", "space", "source_generator_recovered", "source_nodes", "geometry", "streams"}
            or policy["mode"] != "NativeRibbonParametricSweep" or policy["space"] != "PrefabRootRelativeBirthWorldHistory"
            or policy["source_generator_recovered"] is not False or not policy["source_nodes"]):
        raise SpecError("动态拖尾缺显式项目生成合同")
    geometry, streams = policy["geometry"], policy["streams"]
    vectors = {"center_metres": 3, "axis_u": 3, "axis_v": 3, "width_axis": 3}
    scalars = {"radius_metres", "width_metres", "start_angle_degrees", "end_angle_degrees", "duration_seconds",
               "delay_seconds", "lifetime_seconds", "points_per_second"}
    if set(geometry) != set(vectors) | scalars | {"facing", "sort_order"}:
        raise SpecError("动态拖尾几何参数不完整")
    stream_vectors = {"color_start": 4, "color_end": 4, "tc1": 4, "tc2": 4, "tc3": 4, "tc4": 4,
                      "uv0_scale": 2, "uv0_offset": 2, "uv1_scale": 2, "uv1_offset": 2}
    if (set(streams) != set(stream_vectors) | {"tc6_z_mode", "tc6_w"}
            or streams["tc6_z_mode"] != "ParticleNormalizedAgeCopy"
            or type(streams["tc6_w"]) not in (int, float) or not math.isfinite(streams["tc6_w"])):
        raise SpecError("动态拖尾22标量／RGBA配置不完整")
    for mapping, dimensions in ((geometry, vectors), (streams, stream_vectors)):
        for key, count in dimensions.items():
            values = mapping[key]
            if not isinstance(values, list) or len(values) != count or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
                raise SpecError("动态拖尾有限向量无效: "+key)
    if any(type(geometry[k]) not in (int, float) or not math.isfinite(geometry[k]) for k in scalars):
        raise SpecError("动态拖尾标量须有限")
    if (any(geometry[k] <= 0.0 for k in ("radius_metres", "width_metres", "duration_seconds", "lifetime_seconds", "points_per_second"))
            or geometry["delay_seconds"] < 0.0 or geometry["facing"] != "Screen" or type(geometry["sort_order"]) is not int
            or geometry["start_angle_degrees"] == geometry["end_angle_degrees"]):
        raise SpecError("动态拖尾时域／非退化几何或原生Facing无效")
    for key in ("axis_u", "axis_v", "width_axis"):
        if abs(sum(v*v for v in geometry[key])-1.0) > 1e-6:
            raise SpecError("动态拖尾生成轴须明确单位向量")
    if abs(sum(a*b for a,b in zip(geometry["axis_u"], geometry["axis_v"]))) > 1e-6:
        raise SpecError("动态拖尾扫掠平面轴不正交")
    return policy


def generated_ribbon_spec(node, path_nodes, clip, policy, material, material_target):
    """同NS CPU点出生后保World历史；仅同System.Age扫掠，无新Tick或几何缓存。"""
    policy = generated_ribbon_policy(policy)
    path = "/".join(n["name"] for n in path_nodes) or "$root"
    rows = [row for row in policy["source_nodes"] if row["node"] == path]
    mesh = node.get("mesh", {})
    if (len(rows) != 1 or rows[0]["source_transform"] != str(node["transform"])
            or rows[0]["source_mesh"] != {"m_FileID": 0, "m_PathID": 0}
            or mesh.get("mesh") != rows[0]["source_mesh"] or mesh.get("materials") != rows[0]["source_materials"]
            or mesh.get("enabled") is not True or len(mesh["materials"]) != 1):
        raise SpecError("动态拖尾不是声明的准确enabled Mesh0源节点")
    context = generated_ribbon_context()["generated_ribbon"]
    if (material.get("renderer_kind") != "generated_ribbon" or material.get("mesh") is not False
            or material.get("generated_ribbon") != context or material.get("dynamic_parameter_components") != 0xFFFF
            or material.get("output_contract") != "color" or material.get("configuration_mode") != "ProjectConfigured"
            or str(material.get("source_selection", {}).get("material_pid")) != str(mesh["materials"][0]["m_PathID"])):
        raise SpecError("动态拖尾缺准确Native源材质及完整22输入合同")
    g, values = policy["geometry"], policy["streams"]
    matrix = affine_chain(path_nodes, clip, "System.Age", "Transient.UEFX_GeneratedFrame")
    phase = "saturate((System.Age-%s)/%s)" % (f(g["delay_seconds"]), f(g["duration_seconds"]))
    theta = "lerp(%s,%s,%s)" % (f(math.radians(g["start_angle_degrees"])), f(math.radians(g["end_angle_degrees"])), phase)
    local = "(%s+%s*(cos(%s)*%s+sin(%s)*%s))" % (
        f3(g["center_metres"]), f(g["radius_metres"]), theta, f3(g["axis_u"]), theta, f3(g["axis_v"]))
    source_point = matrix.apply(local)
    world_point = "(Engine.Owner.Position+%s)" % qrot_h("Engine.Owner.Rotation", "(Engine.Owner.Scale*%s)" % ue_pos_h(source_point))
    width_axis = ue_pos_h(matrix.vector(matrix.columns, f3(g["width_axis"])))
    width = "(%s*length(Engine.Owner.Scale*%s))" % (f(g["width_metres"]), width_axis)
    spawn = list(matrix.temps)+[("Particles.Lifetime", "Float", f(g["lifetime_seconds"])),
        ("Particles.Age", "Float", "0.0"), ("Particles.NormalizedAge", "Float", "0.0"),
        ("Particles.Alive", "Bool", "true"), ("Particles.Position", "Position", world_point),
        ("Particles.Velocity", "Vector", "float3(0.0,0.0,0.0)"),
        ("Particles.RibbonWidth", "Float", width), ("Particles.RibbonTwist", "Float", "0.0")]
    streams = [("Particles.DynamicMaterialParameter"+(str(i) if i else ""), "Vector4", f4(values["tc"+str(i+1)])) for i in range(4)]
    streams += [("Particles.UEFX_RawTC6Z", "Float", "Particles.NormalizedAge"),
                ("Particles.UEFX_RawTC6W", "Float", f(values["tc6_w"]))]
    spawn += streams + [("Particles.Color", "LinearColor", f4(values["color_start"]))]
    update = streams + [("Particles.Color", "LinearColor", "lerp(%s,%s,saturate(Particles.NormalizedAge))" %
                        (f4(values["color_start"]), f4(values["color_end"])))]
    return {"name": re.sub(r"[^A-Za-z0-9_]", "_", path), "path": path, "local_space": False,
        "loop": False, "duration": g["duration_seconds"], "delay": g["delay_seconds"], "bursts": [],
        "rate": g["points_per_second"], "spawn": spawn, "update": update, "emitter_spawn": [], "emitter_update": [],
        "requirements": [], "bounds_source": "NativeRibbonWorldPointsAndWidth", "source_runtime_and_visual_acceptance": "pending",
        "renderer": {"kind": "generated_ribbon", "material": material_target, "sort": g["sort_order"],
                     "generated_ribbon": context, "dynamic_parameter_components": 0xFFFF,
                     "generator": policy, "source_mesh": mesh, "link_order": "NativeUniqueID", "field_renderer": None}}


def component_mesh_spec(node, path_nodes, clip, contract, assets, material_plans, policy, source_geometry, *, source_materials=None):
    """消费已有完整几何/槽/姿态；UE激活/停止由同NS原所有者执行，不把它声明为原Unity宿主。"""
    policy = component_mesh_policy(policy)
    if policy is None or contract.get("kind") != "static_mesh_renderer_source_contract":
        raise SpecError("MeshRenderer缺准确源合同或明确项目移植选择")
    mesh = contract["mesh"]
    validate_component_geometry(source_geometry)
    if source_geometry["mesh_pid"] != mesh["pid"] \
            or Path(source_geometry["source_json"]["path"]).resolve() != Path(mesh["source_json"]).resolve():
        raise SpecError("静态Mesh绕序输入不属于当前源几何")
    contract = {**contract, "mesh": {**mesh, "source_export_coordinate_conversion": mesh["coordinate_conversion"],
                                    "coordinate_conversion": source_geometry["coordinate_conversion"]}}
    if mesh["pid"] not in assets:
        raise SpecError("MeshRenderer缺该源Mesh的真实导入计划")
    data = json.loads(Path(mesh["source_json"]).read_text(encoding="utf-8-sig"))
    vertices = data["m_Vertices"]
    extent = max(math.sqrt(sum(value*value for value in vertices[i:i+3])) for i in range(0, len(vertices), 3))
    bound = component_bounds_radius(path_nodes, clip, extent, scale_extent=True)
    transform = contract["transform"]
    if policy["native_source_mode"] == "SingleParticle":
        # 静态源组件需要有限显隐时，使用同 NS 的单粒子及原生粒子清理。
        # SignedField 继续消费既有粒子 VF，不把 Emitter 参数冒充粒子数据。
        if len(contract["materials"]) != 1:
            raise SpecError("有限静态网格当前需要一个准确源材质槽")
        slot = contract["materials"][0]
        source = (source_materials or {}).get(slot["pid"])
        plan = source.get("plan") if isinstance(source, dict) else None
        if not isinstance(plan, dict) or plan.get("source_selection", {}).get("material_pid") != slot["pid"] \
                or plan.get("output_contract") not in ("color", "distortion_field_pair") \
                or plan.get("component_age_binding") != policy["material_age"] \
                or plan.get("component_coverage_binding") != {"DP0.y": "ParticleLifetimeFade"} \
                or plan.get("dynamic_parameter_components") != 3:
            raise SpecError("有限静态网格缺原姿态、年龄及明确消退绑定")
        life, fade = policy["lifetime_seconds"], policy["fade_start_seconds"]
        # Niagara CPU VectorVM 不支持 smoothstep；展开相同三次 Hermite 消退。
        fade_phase = "saturate((Particles.Age-%s)/%s)" % (f(fade), f(life-fade))
        coverage = "(1.0-(%s)*(%s)*(3.0-2.0*(%s)))" % (fade_phase, fade_phase, fade_phase)
        update = list(transform["temporaries"]) + [
            ("Particles.Position", "Position", ue_pos_h(transform["position_hlsl"])),
            ("Particles.MeshOrientation", "Quat", ue_quat_h(transform["rotation_hlsl"])),
            ("Particles.Scale", "Vector", ue_scale_h(f3(transform["scale"]))),
            ("Particles.Velocity", "Vector", "float3(0,0,0)"),
            ("Particles.Color", "LinearColor", "float4(1,1,1,1)"),
            ("Particles.DynamicMaterialParameter", "Vector4",
             "float4(System.Age,%s,0,0)" % coverage)]
        path = "/".join(n["name"] for n in path_nodes) or "$root"
        renderer = {"kind": "mesh", "mesh": assets[mesh["pid"]], "material": source["target"], "sort": 0,
            "pivot_offset": [0., 0., 0.], "pivot_space": "Mesh", "sort_mode": "None", "sort_attribute": None,
            "flip_probability": [0., 0., 0.], "component_particle_lifecycle": policy}
        if plan["output_contract"] == "distortion_field_pair":
            renderer["field_renderer"] = signed_field_renderer_contract(node, plan, {})
        return {"name": re.sub(r"[^A-Za-z0-9_]", "_", path), "path": path, "local_space": True,
            "loop": False, "duration": life, "delay": 0., "bursts": [[0., 1]], "rate": 0.,
            "spawn": [("Particles.Lifetime", "Float", f(life))] + update, "update": update,
            "emitter_spawn": [], "emitter_update": [], "requirements": [], "renderer": renderer,
            "fixed_bounds": {"min": [-bound] * 3, "max": [bound] * 3},
            "project_component_mesh": policy, "source_component_contract": contract,
            "source_geometry": source_geometry, "source_runtime_and_visual_acceptance": "pending"}
    entries = list(transform["temporaries"])+[
        ("Emitter.UEFX_ComponentPosition", "Position", ue_pos_h(transform["position_hlsl"])),
        ("Emitter.UEFX_ComponentOrientation", "Quat", ue_quat_h(transform["rotation_hlsl"])),
        ("Emitter.UEFX_ComponentScale", "Vector", ue_scale_h(f3(transform["scale"]))),
        ("Emitter.UEFX_ComponentVelocity", "Vector", "float3(0.0,0.0,0.0)"),
        ("Emitter.UEFX_ComponentMaterial0", "Vector4", "float4(System.Age,0.0,0.0,0.0)")]
    draws, material_kinds = [], {}
    for slot in contract["materials"]:
        plan = material_plans.get(slot["pid"])
        if plan is not None:
            if not isinstance(plan, dict) or plan.get("runtime_inputs", {}).get("effect_age") != policy["material_age"] \
                    or plan["runtime_inputs"].get("dynamic_parameter_mask") != 1 \
                    or plan.get("source_identity", {}).get("material_pid") != slot["pid"]:
                raise SpecError("MeshRenderer材质缺准确源MID/DP0.x场景灯消费合同："+slot["pid"])
            roles = plan["bindings"][slot["pid"]]
            if set(roles) != {"outline", "surface"}:
                raise SpecError("Nap材质需要完整outline/surface两个角色")
            material_kinds[slot["pid"]] = "NapAvatarSimple"
            roles = [(role, roles[role]) for role in ("outline", "surface")]
        else:
            source = (source_materials or {}).get(slot["pid"])
            plan = source.get("plan") if isinstance(source, dict) else None
            if not isinstance(plan, dict) or plan.get("source_selection", {}).get("material_pid") != slot["pid"] \
                    or plan.get("output_contract") != "color" or plan.get("renderer_kind") != "mesh" \
                    or plan.get("component_age_binding") != policy["material_age"] \
                    or plan.get("dynamic_parameter_components") != 1:
                raise SpecError("普通静态材质缺完整源程序/原DP0.x年龄/单颜色输出合同："+slot["pid"])
            material_kinds[slot["pid"]] = "NativeSourceColor"
            roles = [("surface", source["target"])]
        for role, target in roles:
            draws.append({"source_slot": slot["slot"], "source_submesh": slot["submesh"],
                "source_material_pid": slot["pid"], "role": role, "sort": len(draws), "mesh": assets[mesh["pid"]],
                "material": target, "user_material": "User.FXSceneMaterial_"+hashlib.sha256(target.encode()).hexdigest()[:20]})
    path = "/".join(n["name"] for n in path_nodes) or "$root"
    name = re.sub(r"[^A-Za-z0-9_]", "_", path) if path_nodes else "PrefabRoot"
    return {"name": name, "path": path, "source_mode": "Emitter", "local_space": True,
        "lifecycle": "NativeComponentActivation", "bounds_source": "SourceNodeHermiteConvexHullAndMeshVertices",
        "fixed_bounds": {"min": [-bound]*3, "max": [bound]*3}, "spawn": [], "update": [], "bursts": [], "rate": 0,
        "emitter_spawn": entries, "emitter_update": entries, "requirements": [],
        "renderer": {"kind": "component_mesh", "source_mode": "Emitter", "draws": draws,
            "policy": policy, "source_contract": contract, "source_geometry": source_geometry,
            "source_material_kinds": material_kinds, "dynamic_parameter_components": 1},
        "source_runtime_and_visual_acceptance": "pending"}


def component_light_spec(node, path_nodes, clip, source, policy):
    """同 NS 的原生 Emitter Light；不创建粒子或复制原有模拟。"""
    path = "/".join(n["name"] for n in path_nodes) or "$root"
    contract = point_light_contract(source, policy, path)
    policy = contract["policy"]
    matrix = affine_chain(path_nodes, clip, "System.Age", "Emitter.UEFX_ComponentFrame")
    source_radius = contract["source_range_metres"]*policy["range_scale"]
    bound = component_bounds_radius(path_nodes, clip, source_radius, scale_extent=False)
    entries = list(matrix.temps)+[
        ("Emitter.UEFX_ComponentPosition", "Position", ue_pos_h(matrix.position)),
        ("Emitter.UEFX_ComponentColor", "LinearColor", "float4(%s*%s,1.0)" % (
            f3(contract["source_color"][:3]), f(contract["source_intensity"]*policy["intensity_scale"]))),
        ("Emitter.UEFX_ComponentRadius", "Float", "(%s*min(abs(Engine.Owner.Scale.x),min(abs(Engine.Owner.Scale.y),abs(Engine.Owner.Scale.z))))" % f(source_radius*100.0)),
        ("Emitter.UEFX_ComponentEnabled", "Bool", "true"),
        ("Emitter.UEFX_ComponentScattering", "Float", f(policy["volumetric_scattering"]))]
    return {"name": re.sub(r"[^A-Za-z0-9_]", "_", path), "path": path, "source_mode": "Emitter", "local_space": True,
        "lifecycle": "NativeComponentActivation", "bounds_source": "SourceNodeHermiteConvexHullAndPointRadius",
        "fixed_bounds": {"min": [-bound]*3, "max": [bound]*3}, "spawn": [], "update": [], "bursts": [], "rate": 0,
        "emitter_spawn": entries, "emitter_update": entries, "requirements": [],
        "renderer": {"kind": "light", "contract": contract, "source_mode": "Emitter"},
        "source_runtime_and_visual_acceptance": "pending"}


def check_modules(ps, path, policy=None, extensions=None, light_consumer=None, trail_consumer=None):
    for name, expected in (("simulationSpeed", 1.0), ("useUnscaledTime", False),
                           ("stopAction", 0), ("ringBufferMode", 0), ("playOnAwake", True)):
        if name in ps and ps[name] != expected:
            raise SpecError("%s %s=%r requires its source runtime lifecycle/time contract" % (path, name, ps[name]))
    PM.check_limit_velocity(ps.get("ClampVelocityModule"), path, policy)
    lights = ps.get("LightsModule")
    if lights and lights["enabled"] and any(lights["light"][k] for k in ("m_FileID", "m_PathID")) and light_consumer is None:
        raise SpecError("%s LightsModule bound Light prefab requires a source light renderer" % path)
    for k, v in ps.items():
        if isinstance(v, dict) and v.get("enabled") and k not in SUPPORTED_MODULES:
            if k == "TrailModule" and trail_consumer is not None:
                if trail_consumer.get("schema") != "GGYGO.SourceParticleTrail/v1" or trail_consumer.get("source_module") != v:
                    raise SpecError("TrailModule没有同一准确来源的Native逐父消费者")
                continue
            if k == "SubModule":
                children = v["subEmitters"]
                if not isinstance(children, list):
                    raise SpecError("%s SubModule缺完整声明数组" % path)
                for child in children:
                    pointer = child["emitter"]
                    if any(type(pointer[field]) is not int for field in ("m_FileID", "m_PathID")):
                        raise SpecError("%s SubModule缺真实PPtr字段" % path)
                    if pointer["m_FileID"] or pointer["m_PathID"]:
                        raise SpecError("%s SubModule非空目标需要真实事件／出生继承消费者" % path)
                continue  # 原生空槽不发射任何子系统；不生成替代子效果。
            if k == "NoiseModule" and extensions is not None:
                PM.noise_contract(v, path, extensions["noise"])
                continue
            raise SpecError("%s 启用了 %s，未实现" % (path, k))
    im = ps["InitialModule"]
    if ps.get("prewarm"):
        raise SpecError("%s 开了 prewarm，未实现" % path)
    c = im["gravityModifier"]
    if not (c["minMaxState"] in (0, 1) and c["scalar"] == 0.0) and not (
            c["minMaxState"] == 3 and c["scalar"] == 0.0 and c["minScalar"] == 0.0):
        if extensions is None or "gravity" not in extensions:
            raise SpecError("%s 的 gravityModifier 需要明确项目世界加速度" % path)
    if im.get("randomizeRotationDirection", 0.0) != 0.0:
        raise SpecError("%s randomizeRotationDirection≠0 未实现" % path)
    em = ps.get("EmissionModule") if ps.get("EmissionModule", {}).get("enabled") else None
    if em and minmax_curve_const(em["rateOverDistance"]) < 0.0:
        raise SpecError("%s rateOverDistance must be nonnegative" % path)


def custom_data_h(cd, idx, age, rnd, program=None, project_gradient=None):
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
        return minmax_gradient_h(cd["color%d" % idx], age, rnd.take(), project_gradient)
    raise SpecError("CustomData 模式 %r" % mode)


def sprite_motion(ps, path, chain, tscale, shape_pos, shape_dir, velocity_h, sim_local, rnd, curves,
                  project_motion=None, matrix=None, extensions=None, prefab_local=False):
    """Single velocity owner, native dt/lifetime, source-frame displacement.

    Keep Niagara positions in world space even for Unity local simulation: the
    source displacement follows current node/owner transforms explicitly. This
    prevents Niagara bLocalSpace from reapplying parent scale in Local/Shape
    scaling modes. No inverse owner scale or second transform/time cache.
    """
    smode = ps["scalingMode"]
    if prefab_local and (not sim_local or smode != 0):
        raise SpecError("%s root-local mesh motion requires Local simulation and Hierarchy scaling" % path)
    clamp = ps.get("ClampVelocityModule")
    noise = ps.get("NoiseModule") if extensions is not None else None
    noisy = noise is not None and noise["enabled"]
    gravity_curve = ps["InitialModule"]["gravityModifier"]
    gravity = not PM.curve_is_zero(gravity_curve)
    force_h, force_world = PM.force_h(ps.get("ForceModule"), path, rnd, curves, minmax_curve_h)
    source_position_needed = extensions is not None and (noisy or PM.needs_source_position(ps.get("VelocityModule")))
    inverse_needed = project_motion is not None and (
        not sim_local and (source_position_needed or clamp is not None and not clamp["inWorldSpace"])
        or sim_local and (clamp is not None and clamp["inWorldSpace"] or gravity)) \
        or sim_local and force_h is not None and force_world
    frame = "Transient.UEFX_SourceFrameValid" if inverse_needed else None
    if not sim_local and clamp and smode == 0 and project_motion is None:
        raise SpecError("%s world simulation with hierarchy-scale Clamp needs its source metric-frame adapter" % path)
    if not sim_local and clamp and project_motion is None and len(set(tscale)) != 1:
        raise SpecError("%s world simulation with nonuniform-scale Clamp needs its source metric-frame adapter" % path)
    node_origin = ue_pos_h(matrix.position if matrix is not None else chain.pos_h())
    origin = node_origin if prefab_local else "(Engine.Owner.Position + %s)" % qrot_h("Engine.Owner.Rotation",
                                 "(Engine.Owner.Scale * %s)" % node_origin)

    def vector_world(vector, scale, owner_scale):
        value = ue_pos_h(matrix.vector(matrix.columns, vector) if matrix is not None and smode == 0 else
                         qrot_h(chain.quat_h(), "(%s * %s)" % (f3(scale), vector)))
        if prefab_local:
            return value  # 原 Mesh VF 唯一应用 component 根 R/S；CPU 不重复套根变换。
        if owner_scale:
            value = "(Engine.Owner.Scale * %s)" % value
        return qrot_h("Engine.Owner.Rotation", value)

    def vector_source(vector):
        owner_local = vector if prefab_local else qrot_h("float4(-Engine.Owner.Rotation.xyz,Engine.Owner.Rotation.w)", vector)
        if smode == 0 and not prefab_local:
            divisor = "(%s ? Engine.Owner.Scale : float3(1,1,1))" % frame if frame is not None else "Engine.Owner.Scale"
            owner_local = "(%s/%s)" % (owner_local,divisor)
        u = "(float3(-(%s).x,(%s).z,(%s).y)*0.01)" % (owner_local, owner_local, owner_local)
        if matrix is not None and smode == 0:
            return matrix.inverse_vector(u, frame)
        if any(not math.isfinite(s) or s == 0 for s in tscale):
            raise SpecError("%s source metric requires an invertible TRS" % path)
        q = chain.quat_h()
        value = "(%s/%s)" % (qrot_h("float4(-(%s).xyz,(%s).w)" % (q,q),u),f3(tscale))
        return "(%s ? %s : float3(0,0,0))" % (frame,value) if frame is not None else value

    if matrix is not None and smode == 2:
        shape_world = qrot_h("Engine.Owner.Rotation", "(Engine.Owner.Scale*%s)" % ue_pos_h(matrix.vector(matrix.columns,shape_pos)))
    else:
        shape_world = vector_world(shape_pos, chain.S if smode == 2 else tscale, smode in (0, 2))
    birth = "(%s + %s)" % (origin, shape_world)
    temporaries = list(matrix.temps if matrix is not None else chain.temps)
    if matrix is not None and chain is not None:
        temporaries += chain.temps
    spawn, update = list(temporaries), list(temporaries)
    frame_failure = None
    if inverse_needed:
        root = "(min(abs(Engine.Owner.Scale.x),min(abs(Engine.Owner.Scale.y),abs(Engine.Owner.Scale.z)))>0.0 && max(abs(Engine.Owner.Scale.x),max(abs(Engine.Owner.Scale.y),abs(Engine.Owner.Scale.z)))<3.4028234e38)" if smode == 0 else "true"
        node_metric = ("abs(dot(%s,cross(%s,%s)))" % tuple(matrix.columns) if matrix is not None and smode == 0 else
            "dot(%s,%s)" % (chain.quat_h(),chain.quat_h()))
        update += [("Transient.UEFX_RootFrameValid", "Bool", root),
                   ("Transient.UEFX_NodeFrameMetric", "Float", node_metric),
                   ("Transient.UEFX_NodeFrameValid", "Bool", "(Transient.UEFX_NodeFrameMetric>0.0 && Transient.UEFX_NodeFrameMetric<3.4028234e38)"),
                   (frame, "Bool", "(Transient.UEFX_RootFrameValid && Transient.UEFX_NodeFrameValid)")]
        modules = []
        if clamp is not None and (sim_local and clamp["inWorldSpace"] or not sim_local and not clamp["inWorldSpace"]):
            modules.append("ClampVelocityModule")
        if not sim_local and noisy:
            modules.append("NoiseModule")
        if not sim_local and extensions is not None and PM.needs_source_position(ps.get("VelocityModule")):
            modules.append("VelocityModule")
        if gravity and sim_local:
            modules.append("InitialModule.gravityModifier")
        if force_h is not None and force_world and sim_local:
            modules.append("ForceModule")
        frame_failure = {"code": "(Transient.UEFX_RootFrameValid ? (Transient.UEFX_NodeFrameValid ? 0.0 : 2.0) : 1.0)", "modules": modules}
    base = "Particles.UEFX_BaseVelocity"
    total = "Transient.UEFX_TotalVelocity"
    linear = "Transient.UEFX_LinearVelocity"
    initial = "(%s * Particles.USpeed)" % shape_dir
    motion_position = "Particles.UEFX_MotionPosition" if noisy else "Particles.Position"
    if noisy:
        spawn.append((motion_position, "Position", birth))
    if source_position_needed:
        source_point = "(%s+Particles.UEFX_Displacement)" % shape_pos if sim_local else vector_source("(%s-%s)" % (motion_position,origin))
        update.append(("Transient.UEFX_SourcePosition", "Vector", source_point))
    if sim_local:
        spawn += [(base, "Vector", initial), ("Particles.UEFX_Displacement", "Vector", "float3(0.0,0.0,0.0)"),
                  ("Particles.Position", "Position", birth),
                  ("Particles.Velocity", "Vector", vector_world(initial, tscale, smode == 0))]
        update.append((linear, "Vector", velocity_h))
    else:
        spawn += [(base, "Vector", vector_world(initial, tscale, smode == 0)),
                  ("Particles.Position", "Position", birth)]
        update.append((linear, "Vector", vector_world(velocity_h, tscale, smode == 0)))
    if gravity:
        if extensions is None or "gravity" not in extensions:
            raise SpecError("%s 重力缺明确世界加速度配置" % path)
        world_acceleration = "(%s*100.0)" % f3(extensions["gravity"]["world_metres_per_second_squared"])
        source_acceleration = world_acceleration
        if sim_local:
            if prefab_local:
                source_acceleration = "(%s/(%s ? Engine.Owner.Scale : float3(1,1,1)))" % (
                    qrot_h("float4(-Engine.Owner.Rotation.xyz,Engine.Owner.Rotation.w)", world_acceleration), frame)
            source_acceleration = vector_source(source_acceleration)
        modifier = minmax_curve_h(gravity_curve, "Particles.NormalizedAge", rnd.take(), curves)
        update.append((base, "Vector", "(%s+%s*(%s)*Engine.DeltaTime)" % (base, source_acceleration, modifier)))
    if force_h is not None:
        acceleration = force_h
        if force_world:
            acceleration = ue_pos_h(acceleration)
            if sim_local:
                if prefab_local:
                    acceleration = "(%s/(%s ? Engine.Owner.Scale : float3(1,1,1)))" % (
                        qrot_h("float4(-Engine.Owner.Rotation.xyz,Engine.Owner.Rotation.w)", acceleration), frame)
                acceleration = vector_source(acceleration)
        elif not sim_local:
            acceleration = vector_world(acceleration, tscale, smode == 0)
        # Force和重力共享原BaseVelocity，在唯一Update内先加速、再限速／阻尼和位移。
        update.append((base, "Vector", "(%s+(%s)*Engine.DeltaTime)" % (base, acceleration)))
    update.append((total, "Vector", "(%s + %s)" % (base, linear)))
    tunables = []
    if clamp:
        limit = minmax_curve_h(clamp["magnitude"], "Particles.NormalizedAge", rnd.take(), curves)
        drag = minmax_curve_h(clamp["drag"], "Particles.NormalizedAge", rnd.take(), curves) \
            if not PM.curve_is_zero(clamp["drag"]) else None
        drag_strength = extensions["drag"]["strength"] if drag is not None else 1.0
        if project_motion is not None and clamp["inWorldSpace"]:
            metric = "Transient.UEFX_MetricVelocity"
            world_total = vector_world(total, tscale, smode == 0) if sim_local else total
            if prefab_local:
                world_total = qrot_h("Engine.Owner.Rotation", "(Engine.Owner.Scale*%s)" % world_total)
            update.append((metric, "Vector", "(%s*0.01)" % world_total))
            update += PM.dampen_entries(clamp, limit, metric, f, drag=drag, drag_strength=drag_strength)
            restore = "(%s*100.0)" % metric
            if prefab_local:
                restore = "(%s/(%s ? Engine.Owner.Scale : float3(1,1,1)))" % (qrot_h(
                    "float4(-Engine.Owner.Rotation.xyz,Engine.Owner.Rotation.w)", restore), frame)
            update.append((total, "Vector", vector_source(restore) if sim_local else restore))
        elif not sim_local and project_motion is not None:
            metric = "Transient.UEFX_MetricVelocity"
            if clamp["inWorldSpace"]:
                update.append((metric, "Vector", "(%s*0.01)" % total))
                restore = "(%s*100.0)" % metric
            else:
                # 当前源帧的完整逆序：Owner R/S、换轴与单位、节点 R/S。
                # 只有显式项目衰减分支使用该度量；不把它签为 Unity 离散核。
                update.append((metric, "Vector", vector_source(total)))
                restore = vector_world(metric, tscale, smode == 0)
            update += PM.dampen_entries(clamp, limit, metric, f, drag=drag, drag_strength=drag_strength)
            update.append((total, "Vector", restore))
        elif not sim_local:
            limit = "(%s * %s)" % (limit, f(abs(tscale[0]) * 100.0))
            update += PM.dampen_entries(clamp, limit, total, f, drag=drag, drag_strength=drag_strength)
        else:
            update += PM.dampen_entries(clamp, limit, total, f, drag=drag, drag_strength=drag_strength)
        # Retain damping feedback. Reconstructing the original start speed each
        # update would discard all earlier damping; curve velocity is additive.
        update.append((base, "Vector", "(%s - %s)" % (total, linear)))
        tunables = [("Emitter.UEFX_DampenReferenceSeconds", "Float"), ("Emitter.UEFX_DampenStrength", "Float")]
    if sim_local:
        update += [("Particles.UEFX_Displacement", "Vector", "(Particles.UEFX_Displacement + %s * Engine.DeltaTime)" % total),
                   ("Particles.Velocity", "Vector", vector_world(total, tscale, smode == 0)),
                   (motion_position, "Position", "(%s + %s)" % (birth,
                        vector_world("Particles.UEFX_Displacement", tscale, smode == 0)))]
    else:
        update += [("Particles.Velocity", "Vector", total),
                   (motion_position, "Position", "(%s + Particles.Velocity * Engine.DeltaTime)" % motion_position)]
    if noisy:
        point = "(%s+Particles.UEFX_Displacement)" % shape_pos if sim_local else vector_source("(%s-%s)" % (motion_position,origin))
        update.append(("Transient.UEFX_SourcePosition", "Vector", point))
        noise_entries, offset = PM.project_noise_entries(noise,path,extensions["noise"],
            "Transient.UEFX_SourcePosition",rnd,curves,minmax_curve_h,f)
        update += noise_entries
        update += [("Transient.UEFX_FinalPosition", "Position", "(%s+%s)" % (
                        motion_position,vector_world(offset,tscale,smode == 0))),
                   ("Particles.Velocity", "Vector", "(Engine.DeltaTime>0.0 ? (Transient.UEFX_FinalPosition-Particles.Position)/Engine.DeltaTime : Particles.Velocity)"),
                   ("Particles.Position", "Position", "Transient.UEFX_FinalPosition")]
    # Hierarchical size incorporates the owner transform once. Local ignores
    # parents; Shape does not scale size or movement. Axis lengths remain valid
    # under owner nonuniform scaling without pretending the chain is pure TRS.
    if smode == 0:
        columns = matrix.columns if matrix is not None else [qrot_h(chain.quat_h(),
            f3(tuple(tscale[i] if i == axis else 0.0 for i in range(3)))) for axis in range(3)]
        size_scale = "float3(%s)" % ", ".join("length(Engine.Owner.Scale * %s) / 100.0" % ue_pos_h(c) for c in columns)
    else:
        size_scale = f3(tscale)
    return spawn, update, size_scale, tunables, frame_failure


def project_motion_policy(policy):
    """可调衰减单独选择；未知源核不借几何配置或宿主跳过自动准入。"""
    if policy is None:
        return None
    keys = {"configuration_mode", "mode", "dampen_reference_seconds", "dampen_strength", "decision_reference"}
    if not isinstance(policy, dict) or set(policy) not in (keys, keys | {"extensions"}) or policy["configuration_mode"] != "ProjectConfigured" \
            or policy["mode"] != "ExcessSpeedDecay" or not isinstance(policy["decision_reference"], str) \
            or not policy["decision_reference"]:
        raise SpecError("Project motion requires an explicit decision and complete tunables")
    for name in ("dampen_reference_seconds", "dampen_strength"):
        value = policy[name]
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise SpecError("Project motion requires positive finite " + name)
    result = dict(policy)
    if "extensions" in result:
        result["extensions"] = PM.project_extensions_policy(result["extensions"])
    return result


def signed_field_renderer_contract(node, material_plan, renderer_contract):
    """将已翻译的实际分量掩码交给公开 renderer ABI，不复制模拟或変换。"""
    if material_plan.get("output_contract") != "distortion_field_pair":
        return None
    mask = material_plan.get("dynamic_parameter_components")
    if type(mask) is not int or not 0 <= mask <= 65535:
        raise SpecError("Field material lacks its exact DP component mask")
    mesh = material_plan["mesh"]
    if mesh:
        bounds = (material_plan.get("mesh_affine") or {}).get("bounds", "NativeMeshBoundsIncludingPivot")
        properties = {"FacingMode": "Default"}
        class_name = "GGYGOSignedFieldMeshRendererProperties"
    else:
        geometry = renderer_contract.get("sprite_geometry")
        PR.validate_sprite_geometry(geometry)
        bounds = geometry["bounds"]
        basis = renderer_contract.get("field_basis")
        if basis not in ("NativeViewPlane", "NativeVelocityAligned", "CameraPositionWithViewRoll"):
            raise SpecError("Field sprite needs an explicit native/view-roll basis")
        properties = {"FieldBasis": basis, "PixelCoverageMode": "Disabled"}
        class_name = "GGYGOSignedFieldSpriteRendererProperties"
    properties["FieldStreams"] = {"bConfigured": True,
        "SourceReference": "F1|Transform=" + str(node["transform"]) + "|Material=" + material_plan["master"],
        "TransformOwner": "MaterialWorldPositionOffset", "RequiredDynamicParameterComponents": mask,
        "BoundsReference": bounds}
    return {"class": "/Script/GGYGORendering." + class_name, "properties": properties}


def mesh_affine_transport(adapter):
    """材质与原生 renderer 共享同一几何／数据／界限声明。"""
    if adapter is None:
        return None
    keys = ("mode", "bound_scale", "bounds", "transport", "source_pivot_cm", "pivot_consumption")
    if adapter.get("project_alignment") is not None:
        keys += ("project_alignment",)
    return {key: adapter[key] for key in keys}


def _mesh_alignment_update(matrix, alignment):
    """沿原 Update 写真实速度／失败码；无效帧交原 Alive 生命周期拒绝。"""
    def world(v):
        return qrot_h("Engine.Owner.Rotation", "(Engine.Owner.Scale*%s)" % v)

    front = world("float3(-(%s).x,(%s).z,(%s).y)" % ((AffineChain.vector(matrix.columns, f3(alignment["front_axis"])),) * 3))
    up = world("float3(-(%s).x,(%s).z,(%s).y)" % ((AffineChain.vector(matrix.columns, f3(alignment["up_axis"])),) * 3))
    entries = [
        ("Transient.UEFX_MeshFront", "Vector", front),
        ("Transient.UEFX_MeshUp", "Vector", up),
        ("Transient.UEFX_MeshFrameCross", "Vector", "cross(Transient.UEFX_MeshUp,Transient.UEFX_MeshFront)"),
        ("Transient.UEFX_MeshRootMin", "Float", "min(abs(Engine.Owner.Scale.x),min(abs(Engine.Owner.Scale.y),abs(Engine.Owner.Scale.z)))"),
        ("Transient.UEFX_MeshRootCondition", "Float",
         "(Transient.UEFX_MeshRootMin>0.0 ? max(abs(Engine.Owner.Scale.x),max(abs(Engine.Owner.Scale.y),abs(Engine.Owner.Scale.z)))/Transient.UEFX_MeshRootMin : 0.0)")]
    failure = "(Transient.UEFX_MeshRootMin>0.0 ? (dot(Transient.UEFX_MeshFrameCross,Transient.UEFX_MeshFrameCross)>0.0 ? 0.0 : 2.0) : 1.0)"
    if alignment["alignment"] == "Velocity":
        entries += [("Transient.UEFX_MeshTravel", "Vector", world("Particles.Velocity")),
                    ("Transient.UEFX_MeshFrontSquared", "Float", "dot(Transient.UEFX_MeshFront,Transient.UEFX_MeshFront)")]
        reference_up = (f3(alignment["world_up"]) if alignment["velocity_up_reference"] == "WorldUp" else
            "(Transient.UEFX_MeshFrontSquared>0.0 ? Transient.UEFX_MeshUp-Transient.UEFX_MeshFront*dot(Transient.UEFX_MeshUp,Transient.UEFX_MeshFront)/Transient.UEFX_MeshFrontSquared : float3(0,0,0))")
        entries.append(("Transient.UEFX_MeshTravelCross", "Vector", "cross(%s,Transient.UEFX_MeshTravel)" % reference_up))
        failure = "(%s!=0.0 ? %s : (dot(Transient.UEFX_MeshTravel,Transient.UEFX_MeshTravel)>0.0 ? (dot(Transient.UEFX_MeshTravelCross,Transient.UEFX_MeshTravelCross)>0.0 ? 0.0 : 4.0) : 3.0))" % (failure, failure)
    entries += [("Particles.UEFX_RuntimeFailure", "Float", failure),
                ("Particles.Alive", "Bool", "Particles.Alive")]
    return entries


def projected_decal_entries(ps, node, matrix, rotation, flip, custom_data, randoms, curves, gradient, plan):
    """原CPU粒子生成完整投影帧及payload；单位cube是明确UE配置，不是已恢复源Mesh。"""
    required = plan["required_source_inputs"]
    volume = required["conservative_volume"]
    if (volume["mode"] != "ConservativeSourceVolumeWithPadding" or volume["geometry"] != "NativeUnitCubeProjector"
            or volume["local_bounds"] != [-0.5, 0.5] or volume["source_builtin_mesh_recovered"] is not False
            or required["original_mpb_recovered"] is not False):
        raise SpecError("Decal需要明确Native单位cube投影配置及原MPB未证边界")
    padding = PR.number(volume["padding"], "Decal.native_enclosure_scale")
    if padding < 4.0/3.0 or ps["scalingMode"] not in (0, 1, 2):
        raise SpecError("Decal保守包围体或源scalingMode无效")
    if ps["scalingMode"] == 0:
        source_columns = matrix.columns
    else:
        if rotation is None:
            raise SpecError("Decal Local/Shape缩放缺原层级四元数链")
        scale = _vals(node["scale"], "xyz") if ps["scalingMode"] == 1 else (1.0, 1.0, 1.0)
        source_columns = [qrot_h(rotation.quat_h(), f3(tuple(scale[i] if i == axis else 0.0
                                                           for i in range(3)))) for axis in range(3)]
    entries = [("Transient.UEFX_DecalParticleQ", "Quat", qeuler_h("Particles.URot")),
               ("Transient.UEFX_DecalSignedSize", "Vector", "(Particles.USize*%s)" % flip)]
    axes = []
    for axis in range(3):
        basis = "float3(%s)" % ",".join("Transient.UEFX_DecalSignedSize."+"xyz"[axis]
                                                  if i == axis else "0.0" for i in range(3))
        source = AffineChain.vector(source_columns, qrot_h("Transient.UEFX_DecalParticleQ", basis))
        native = "float3(-(%s).x,(%s).z,(%s).y)" % (source, source, source)
        if ps["scalingMode"] == 0:
            native = "(Engine.Owner.Scale*%s)" % native
        world = qrot_h("Engine.Owner.Rotation", native)
        world_name = "Transient.UEFX_DecalAxisWS"+str(axis)
        source_name = "Transient.UEFX_DecalAxisU"+str(axis)
        entries += [(world_name, "Vector", world),
                    (source_name, "Vector", "float3(-%s.x,%s.z,%s.y)" % (world_name, world_name, world_name))]
        axes.append(source_name)
    a, b, c = axes
    determinant = "Transient.UEFX_DecalDeterminant"
    entries += [(determinant, "Float", "dot(%s,cross(%s,%s))" % (a, b, c)),
                ("Transient.UEFX_DecalInvertible", "Bool", "(%s && %s!=0.0)" % (_finite_h(determinant, 1), determinant))]
    denominator = "(Transient.UEFX_DecalInvertible ? %s : 1.0)" % determinant
    for axis, (left, right) in enumerate(((b, c), (c, a), (a, b))):
        # A已含Size；先乘diag(Size)再交材质唯一原o7，避免Size被除两遍。
        row = "(cross(%s,%s)*Particles.USize.%s/%s)" % (left, right, "xyz"[axis], denominator)
        entries += [("Particles.UEFX_ProjectionRow"+str(axis), "Vector4", "float4(%s,0.0)" % row),
                    ("Particles._ParticleDecalLocalToWorldMatrix_R"+str(axis), "Vector4", "float4(%s,0.0)" % axes[axis])]
    entries += [("Particles.UEFX_SourceColor", "Vector4", "Particles.Color"),
                ("Particles.UEFX_SourceCenter", "Vector4", "float4(0.0,0.0,0.0,0.0)"),
                ("Particles.UEFX_SourceSize", "Vector4", "float4(Particles.USize,1.0)"),
                ("Particles.UEFX_SourceStableRandom", "Vector4", "Particles.UStable"),
                ("Particles.UEFX_SourceCustom1", "Vector4", custom_data_h(custom_data, 0, "Particles.NormalizedAge", randoms, curves, gradient)),
                ("Particles.UEFX_SourceCustom2", "Vector4", custom_data_h(custom_data, 1, "Particles.NormalizedAge", randoms, curves, gradient)),
                ("Particles.UEFX_DecalPosition", "Position", "Particles.Position"),
                ("Particles.UEFX_DecalOrientation", "Quat", "float4(0.0,0.0,0.0,1.0)"),
                # Native Decal renderer内部乘.5，绑定全宽；完整A的绝对列和包住shear和mirror。
                ("Particles.UEFX_DecalSize", "Vector", "((abs(Transient.UEFX_DecalAxisWS0)+abs(Transient.UEFX_DecalAxisWS1)+abs(Transient.UEFX_DecalAxisWS2))*%s)" % f(100.0*padding)),
                ("Particles.UEFX_DecalColor", "LinearColor", "float4(1.0,1.0,1.0,1.0)"),
                ("Particles.UEFX_DecalFade", "Float", "1.0")]
    available = {name: kind for name, kind, _ in entries}
    vector_attributes = required["vector_attributes"]
    if any(available.get(name) != "Vector4" for name in vector_attributes):
        raise SpecError("Decal材质存在未实现的真实float4来源")
    # 非法必需帧仍交原Renderer首错校验；只有有限退化体积不可见，粒子寿命继续。
    finite = [_finite_h("Particles.UEFX_DecalPosition", 3), _finite_h("Particles.UEFX_DecalSize", 3),
              _finite_h(determinant, 1)] + [_finite_h(name, 4) for name in vector_attributes]
    entries.append(("Particles.UEFX_DecalVisible", "Bool", "(!(%s) || %s!=0.0)" % (" && ".join(finite), determinant)))
    return entries


def shape_alignment_consumer(ps, renderer, path, project_geometry):
    """仅消费已选择的Cone／View Stretch／零2D旋转组合，其余原朝向继续拒绝。"""
    shape = ps.get("ShapeModule")
    if not shape or not shape["enabled"] or not shape["alignToDirection"]:
        return None
    initial = ps["InitialModule"]
    rotation = ps.get("RotationModule") or {}
    z = initial["startRotation"]
    if shape["type"] != 4 or renderer["m_RenderMode"] != 1 or renderer["m_RenderAlignment"] != 0 \
            or initial["rotation3D"] or z["minMaxState"] != 0 or z["scalar"] != 0 \
            or rotation.get("enabled") or project_geometry is None:
        raise SpecError("%s Shape朝向所选UE核仅接Cone/View Stretch/零2D源旋转组合" % path)
    return "NativeVelocityAlignedStretch"


def emitter_spec(node, path_nodes, clip, ue_assets, material_paths, material_plan, particle_equivalence=None,
                 *, project_geometry=None, project_motion=None, project_mesh_alignment=None, project_gradient=None,
                 project_lights=None, source_light=None, light_only=False, projected_plan=None, prop_plan=None, particle_trail=None):
    path = "/".join(n["name"] for n in path_nodes)
    raw_ps, rd = node["particle"]["system"], node["particle"]["renderer"]
    projected = projected_plan is not None
    prop_contract = prop_plan["native_renderer_contract"] if prop_plan is not None else None
    if prop_contract is not None and (projected or prop_plan["roles"] != ["prop_surface", "prop_forward_color"]
            or prop_contract["geometry"] != "NativeTRSOnly" or rd["m_RenderMode"] != 4
            or rd["m_MotionVectors"] != prop_contract["source_motion_vectors"] or project_motion is None):
        raise SpecError("Prop需要准确双role、源MotionVectors及同CPU原生TRS运动合同")
    if projected and (projected_plan.get("roles") != ["projected_decal"]
            or material_plan.get("output_contract") != "projected_decal" or rd["m_RenderMode"] != 4
            or rd["m_RenderAlignment"] != 2 or any(PR.vector(rd, "m_Pivot", path))):
        raise SpecError("投影计划需要准确Local Mesh源、零Pivot及独立Native Decal角色")
    # New source evidence preserves disabled modules as well as enabled ones.
    # Their serialized curves are inert and must never become live simulation.
    ps = {k: v for k, v in raw_ps.items() if not isinstance(v, dict) or "enabled" not in v
          or v["enabled"] or k == "InitialModule"}
    policy = PM.equivalence_policy(particle_equivalence)
    motion = project_motion_policy(project_motion)
    gradient = project_gradient_policy(project_gradient)
    if gradient is not None and material_plan.get("configuration_mode") != "ProjectConfigured":
        raise SpecError("Project Gradient kernel requires ProjectConfigured materials")
    if motion is not None and (policy is not None or material_plan.get("configuration_mode") != "ProjectConfigured"):
        raise SpecError("Project motion cannot mix with source/other particle policies")
    motion = motion or policy
    extensions = motion.get("extensions") if motion is not None else None
    light = particle_light_contract(ps, source_light, project_lights, path)
    if light_only and (light is None or rd["m_Enabled"] and any(p["m_PathID"] for p in rd["m_Materials"])):
        raise SpecError("%s light-only renderer requires a real light consumer and no colour material" % path)
    check_modules(ps, path, motion, extensions, light, particle_trail)
    im = ps["InitialModule"]
    rnd = Randoms()
    spawn_curves, update_curves = CurveProgram("Spawn"), CurveProgram("Update")
    age = "Particles.NormalizedAge"
    eage = "Emitter.NormalizedLoopAge"
    sim_local = ps["moveWithTransform"] == 0
    alignment_choice = PR.mesh_alignment_policy(project_mesh_alignment)
    native_mesh_facing = alignment_choice is not None and alignment_choice["alignment"] == "NativeCameraPlane"
    if native_mesh_facing and project_motion is None:
        raise SpecError("%s native Mesh facing requires its explicit world-position motion consumer" % path)
    mesh_prefab_local = rd["m_RenderMode"] == 4 and sim_local and ps["scalingMode"] == 0 and alignment_choice is None
    shared_mesh_motion = projected or (project_motion is not None and (mesh_prefab_local or native_mesh_facing))
    if (ps.get("ForceModule") or {}).get("enabled") and rd["m_RenderMode"] == 4 and not shared_mesh_motion:
        raise SpecError("%s Mesh ForceModule需要原共享运动帧消费者" % path)
    if projected:
        mesh_prefab_local = False  # 原投影数据统一world模拟，根变换仅由原CPU链应用一次。
    if ps["moveWithTransform"] not in (0, 1):
        raise SpecError("%s 自定义模拟空间未实现" % path)

    spawn, update = [], []
    spawn.append(("Particles.Lifetime", "Float", minmax_curve_h(im["startLifetime"], eage, rnd.take(), spawn_curves)))
    spawn.append(("Particles.UStartColor", "Vector4", minmax_gradient_h(im["startColor"], eage, rnd.take(), gradient)))
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
    shape_source = ps.get("ShapeModule")
    shape_alignment = shape_alignment_consumer(ps, rd, path, project_geometry)
    spread_count = None
    if shape_source and shape_source["enabled"] and shape_source["type"] in (4, 8) and shape_source["arc"]["mode"] == 3:
        emission = ps.get("EmissionModule")
        if not emission or not emission["enabled"] or minmax_curve_const(emission["rateOverTime"]) != 0 \
                or minmax_curve_const(emission["rateOverDistance"]) != 0:
            raise SpecError("%s BurstSpread需要真实独立Burst计数，不能由连续发射猜分母" % path)
        counts = [burst_count(b["countCurve"], path) for b in emission["m_Bursts"] if b["probability"] > 0]
        if not counts or any(type(count) is not int or count <= 0 or count != counts[0] for count in counts):
            raise SpecError("%s BurstSpread需要本批原Burst的相同确定计数" % path)
        spread_count = counts[0]
    shape_entries, shape_pos, shape_dir, shape = PM.birth_shape_h(shape_source, path, rnd, f,
        extensions["shape"] if extensions is not None else None, burst_spread_count=spread_count,
        birth_seconds_h="(%s*%s)" % (eage, f(ps["lengthInSec"])), alignment_consumer=shape_alignment)
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
    if velocity and rd["m_RenderMode"] not in (0, 1, 2) and not shared_mesh_motion and not light_only:
        if rd["m_RenderMode"] != 4 or not sim_local or ps["scalingMode"] != 0:
            raise SpecError("%s mesh VelocityModule requires Local simulation and Hierarchy scaling" % path)
        if ps.get("ClampVelocityModule") or ps.get("NoiseModule"):
            raise SpecError("%s mesh velocity with damping/noise requires its complete motion adapter" % path)
        linear, in_world = PM.linear_velocity_h(velocity, path, rnd, update_curves, minmax_curve_h)
        if in_world:
            raise SpecError("%s world-space mesh velocity needs a source simulation-frame adapter" % path)
        # 源 Local 线性速度在同一 Niagara Update 中积分，保留原曲线与原生 dt。
        # 派生位移属于本粒子；出生置零，由原 ParticleState 结束时释放。
        displacement = "Particles.UEFX_LocalVelocityDisplacement"
        spawn.append((displacement, "Vector", "float3(0.0,0.0,0.0)"))
        update += [("Transient.UEFX_LocalLinearVelocity", "Vector", linear),
                   (displacement, "Vector", "(%s+Transient.UEFX_LocalLinearVelocity*Engine.DeltaTime)" % displacement)]
        local_pos = "(%s+%s)" % (local_pos, displacement)

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
        col = "(Particles.UStartColor * %s)" % minmax_gradient_h(cm["gradient"], age, rnd.take(), gradient)
    update.append(("Particles.Color", "LinearColor", srgb_to_linear_h(col) if rd["m_ApplyActiveColorSpace"] else col))

    # 节点位姿
    t_anim = "System.Age"
    affine = material_plan.get("mesh_affine")
    if prop_contract is not None and affine is not None:
        raise SpecError("Prop NativeTRSOnly不能丢弃真实FullAffine WPO")
    mesh_alignment = (affine or {}).get("project_alignment")
    sprite_matrix = None
    if affine is not None:
        expected = mesh_affine_adapter(node, path_nodes, clip, project_alignment=project_mesh_alignment,
            euler_components=(mesh_alignment or {}).get("euler_components"),
            source_components=(mesh_alignment or {}).get("source_dynamic_components",0))
        if affine != expected or material_plan["dyn_params"].get(3, material_plan["dyn_params"].get("3")) != "FullAffineTransport":
            raise SpecError("完整 affine 材质／粒子传输不一致")
        if mesh_alignment is not None:
            PR.validate_mesh_alignment_transport(mesh_alignment)
            required = mesh_alignment["required_components"]
            source_mask = mesh_alignment.get("source_dynamic_components",0)
            actual = material_plan["dynamic_parameter_components"]
            if actual & required != required or source_mask and actual & 0x0FFF != source_mask | required:
                raise SpecError("Mesh Euler运输缺实际分量或改变了原活跃流")
        matrix = affine_chain(path_nodes, clip, t_anim, "Particles.UAffine")
        chain = None
    elif projected or project_geometry is not None and (rd["m_RenderMode"] in (0, 1, 2) or light_only):
        matrix_required = projected
        if not matrix_required:
            try:
                chain = node_chain(None, path_nodes, clip, t_anim)
                matrix_required = getattr(chain, "sheared", False)
            except AffineRequired:
                matrix_required = True
        if matrix_required:
            sprite_matrix = affine_chain(path_nodes, clip, t_anim, "Particles.UAffineSprite")
            chain = None if ps["scalingMode"] == 0 else rotation_chain(path_nodes, clip, t_anim)
    else:
        chain = node_chain(None, path_nodes, clip, t_anim)
    if getattr(chain, "sheared", False):
        speed = im["startSpeed"]
        stationary = speed["minMaxState"] == 0 and speed["scalar"] == 0.0 or (
            speed["minMaxState"] == 3 and speed["scalar"] == 0.0 and speed["minScalar"] == 0.0)
        if ps["scalingMode"] == 0 or not stationary or shape is not None:
            raise SpecError("%s 切变影响层级尺寸或运动，需要矩阵变换路径" % path)
    if affine is not None:
        tscale = (affine["bound_scale"],) * 3
    elif sprite_matrix is not None:
        # Hierarchy全部走矩阵；Local/Shape仅原点需要全矩阵，运动/尺寸保其独立缩放语义。
        tscale = None if ps["scalingMode"] == 0 else _vals(node["scale"],"xyz") if ps["scalingMode"] == 1 else (1.,1.,1.)
    elif ps["scalingMode"] == 0:
        tscale = chain.S
    elif ps["scalingMode"] == 1:
        tscale = _vals(node["scale"], "xyz")
    elif ps["scalingMode"] == 2:
        tscale = (1.0, 1.0, 1.0)
    else:
        raise SpecError("%s 未知 scalingMode %r" % (path, ps["scalingMode"]))
    mode = rd["m_RenderMode"]
    if mode not in (0, 1, 2, 4) and not light_only:
        raise SpecError("%s 渲染模式 %s 未实现" % (path, UNITY_RENDER_MODE.get(mode, mode)))
    signed_field = material_plan.get("output_contract") == "distortion_field_pair"
    renderer_contract = {"flip_probability": (0.0, 0.0, 0.0)} if light_only else PR.mesh_contract(rd, path, signed_field=signed_field,
        project_order=(project_geometry or {}).get("scene_sort")) if mode == 4 else PR.sprite_contract(
        rd, path, project_geometry=project_geometry, signed_field=signed_field)
    if shape_alignment is not None and (renderer_contract.get("alignment") != "VelocityAligned"
            or renderer_contract.get("facing_mode") != "FaceCamera" or renderer_contract.get("stretch") is None):
        raise SpecError("%s Shape朝向没有接入真实Native Stretch速度／相机基底" % path)
    if mesh_alignment is not None:
        renderer_contract["dynamic_parameter_components"] = material_plan["dynamic_parameter_components"]
    source_local_plane = (renderer_contract.get("project_plane") or {}).get("mode") == "NativeSourceLocalPlane"
    if native_mesh_facing:
        if signed_field or affine is not None:
            raise SpecError("%s native camera-plane Mesh requires its ordinary native geometry contract" % path)
        renderer_contract["project_native_facing"] = alignment_choice
    viewport = PR.viewport_plan(rd, policy, path, project_geometry=project_geometry,
                                signed_field=signed_field) if mode in (0, 1, 2) else None
    if viewport is not None:
        if material_plan.get("viewport_clamp") != viewport:
            raise SpecError("%s sprite material is missing/mismatches its explicit viewport geometry adapter" % path)
        renderer_contract["requirements"] = []
        renderer_contract["viewport_adapter"] = {k: viewport[k] for k in ("mode", "metric", "precision")}
        renderer_contract["viewport_adapter_signature"] = PR.viewport_signature(viewport)
    align = rd["m_RenderAlignment"]
    if mode in (0, 1, 2) or light_only or projected:
        if not light_only and not projected and not source_local_plane and (im["rotation3D"] or (rm and rm["separateAxes"])):
            raise SpecError("%s 3D billboard rotation requires a source plane adapter" % path)
        q_u = None
    elif affine is not None:
        q_u = "float4(0.0,0.0,0.0,1.0)" if mesh_alignment is not None else "Particles.UPartQ"  # 唯一 WPO 消费项目 Euler／完整矩阵。
    elif native_mesh_facing:
        q_u = "Particles.UPartQ"  # 原生 CameraPlane 在此源 Euler 后应用项目相机基底。
    elif align == 2:      # Local：网格随变换旋转
        q_u = qmul_h(chain.quat_h(), "Particles.UPartQ")
    elif align == 1:    # World：只用粒子自身旋转
        q_u = "Particles.UPartQ"
    elif align in (0, 4):
        raise mesh_alignment_error(path, align)
    else:
        raise SpecError("%s 网格对齐模式 %d 未实现" % (path, align))
    if mode == 4 and mesh_alignment is None and not projected:
        update.append(("Particles.UPartQ", "Quat", qeuler_h("Particles.URot")))
    scale_u = None if sprite_matrix is not None else "(%s * %s)" % (
        "abs(Particles.USize)" if affine is not None else "Particles.USize", f3(tscale))
    pose = list(matrix.temps if affine is not None else sprite_matrix.temps if sprite_matrix is not None else chain.temps)
    if sprite_matrix is not None and chain is not None:
        pose += chain.temps
    owner_q = "Engine.Owner.Rotation"
    if mode in (0, 1, 2) or light_only or projected:
        pose_q = None
    elif align == 1:
        # World-aligned meshes keep world orientation even in local simulation.
        inverse_owner = "float4(-Engine.Owner.Rotation.xyz, Engine.Owner.Rotation.w)"
        q_local = qmul_h(inverse_owner, ue_quat_h(q_u)) if sim_local else ue_quat_h(q_u)
    else:
        q_local = "float4(0.0,0.0,0.0,1.0)" if mesh_alignment is not None else ue_quat_h(q_u)
    if mode == 4 and not projected:
        pose_q = ("Particles.MeshOrientation", "Quat", q_local)
    # 粒子在节点本地的位移经节点变换到预制体根空间（scalingMode=Shape 时位置也按变换缩放，与 Hierarchical 同）
    pos_u = (matrix.apply(local_pos) if affine is not None else None if sprite_matrix is not None else
        "(%s + %s)" % (chain.pos_h(), qrot_h(chain.quat_h(), "(%s * %s)" % (f3(chain.S), local_pos))))
    emitter_update = []
    runtime_failure = None
    if mode in (0, 1, 2) or shared_mesh_motion or light_only:
        velocity_h, velocity_world = (PM.project_velocity_h(velocity,path,rnd,update_curves,minmax_curve_h,
            "Transient.UEFX_SourcePosition",extensions["velocity"],f) if extensions is not None else
            PM.linear_velocity_h(velocity, path, rnd, update_curves, minmax_curve_h))
        if velocity_world:
            raise SpecError("%s World VelocityModule requires its inverse source simulation-frame conversion" % path)
        s_motion, u_motion, sprite_scale, tunables, frame_failure = sprite_motion(ps, path, chain, tscale,
                                                        shape_pos, shape_dir, velocity_h, sim_local, rnd, update_curves,
                                                        project_motion=project_motion,
                                                        matrix=matrix if shared_mesh_motion and affine is not None else sprite_matrix,
                                                        extensions=extensions, prefab_local=mesh_prefab_local)
        spawn += s_motion
        update += u_motion
        if frame_failure is not None:
            runtime_failure = PR.source_metric_failure_transport(node["transform"], motion["decision_reference"], path, frame_failure["modules"])
        if mode == 4:
            if pose_q is not None:
                update.append(pose_q)
        if not mesh_prefab_local:
            scale_u = "(Particles.USize * %s)" % sprite_scale
        if tunables:
            emitter_update = [(name, kind, f(motion["dampen_reference_seconds" if name.endswith("ReferenceSeconds") else "dampen_strength"]))
                              for name, kind in tunables]
    elif ps.get("ClampVelocityModule"):
        raise SpecError("%s mesh ClampVelocityModule needs its simulation-frame adapter" % path)
    elif sim_local:
        if mesh_alignment is not None:
            # 出生先给原节点位置与非零源速度，避免首帧拿默认原点生成假速度。
            spawn += pose + [("Particles.Position", "Position", ue_pos_h(matrix.apply(shape_pos))),
                ("Particles.Velocity", "Vector", ue_pos_h(AffineChain.vector(matrix.columns,
                    "(%s*Particles.USpeed)" % shape_dir))),
                ("Particles.UEFX_RuntimeFailure", "Float", "0.0"),
                ("Particles.Alive", "Bool", "true")]
            update += pose + [("Transient.UEFX_MeshNextPosition", "Position", ue_pos_h(pos_u)),
                ("Particles.Velocity", "Vector", "(Engine.DeltaTime>0.0 ? (Transient.UEFX_MeshNextPosition-Particles.Position)/Engine.DeltaTime : Particles.Velocity)"),
                ("Particles.Position", "Position", "Transient.UEFX_MeshNextPosition")]
            update += _mesh_alignment_update(matrix, mesh_alignment["policy"])
        else:
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
    if renderer_contract.get("project_plane") is not None:
        plane = renderer_contract["project_plane"]
        if plane["mode"] == "NativeSourceLocalPlane":
            orientation = rotation_chain(path_nodes, clip, t_anim)
            # 源完整Euler按qy*qx*qz进入同一当前平面；原SpriteRotation不重复旋转Z。
            source_q = qmul_h(orientation.quat_h(), qeuler_h("Particles.URot"))
            world_q = "Transient.UEFX_LocalPlaneQuaternion"
            plane_entries = list(orientation.temps) + [
                (world_q, "Quat", qmul_h("Engine.Owner.Rotation", ue_quat_h(source_q))),
                ("Particles.SpriteFacing", "Vector", qrot_h(world_q, f3(plane["local_normal"]))),
                ("Particles.SpriteAlignment", "Vector", qrot_h(world_q, f3(plane["local_up"])))]
        else:
            plane_entries = [("Particles.SpriteFacing", "Vector", f3(plane["world_normal"])),
                             ("Particles.SpriteAlignment", "Vector", f3(plane["world_up"]))]
        spawn += plane_entries
        update += plane_entries
    flip = PR.mesh_flip_h(renderer_contract["flip_probability"], rnd)
    if affine is not None:
        update.append(("Particles.UAffineSignedSize", "Vector", "(Particles.USize * %s)" % flip))
        render_scale = "(abs(Particles.UAffineSignedSize) * %s)" % f3(tscale)
        if mesh_alignment is not None:
            render_scale = "(%s*Transient.UEFX_MeshRootCondition)" % render_scale
    else:
        render_scale = "(%s * %s)" % (scale_u, flip)
    if prop_contract is not None and prop_contract["motion_vector_setting"] == "Precise":
        if not sim_local or sprite_matrix is not None or affine is not None or native_mesh_facing:
            raise SpecError("Precise Prop出生帧需要已证完整Local TRS，不猜其它几何的旧值")
        # 原编译器唯一复制Previous；Spawn先提供真实初始current，避免首帧默认原点/零Scale。
        spawn += list(pose) + [("Particles.USize", "Vector", "Particles.UStartSize"),
            ("Particles.UPartQ", "Quat", qeuler_h("Particles.URot")),
            ("Particles.MeshOrientation", "Quat", q_local),
            ("Particles.Scale", "Vector", ue_scale_h(render_scale))]
        if not any(name == "Particles.Position" for name, _, _ in spawn):
            birth = "(%s+%s)" % (chain.pos_h(), qrot_h(chain.quat_h(), "(%s*%s)" % (f3(chain.S), shape_pos)))
            spawn.append(("Particles.Position", "Position", ue_pos_h(birth)))
    if mode == 4 and not projected:
        source_uv = raw_ps.get("UVModule")
        if source_uv is not None:
            # 保留原节点的完整UV声明；disabled仅声明原Mesh UV，不激活帧动画。
            mesh_uv = PU.mesh_uv_adapter(source_uv, path)
            if material_plan.get("mesh_uv") != mesh_uv:
                raise SpecError("%s Mesh UV材质未消费同一原模块／通道mask" % path)
            renderer_contract["mesh_uv"] = mesh_uv
        if ps.get("UVModule"):
            uv_spawn, uv_update, _ = PU.entries(ps["UVModule"], path, rnd,
                (spawn_curves, update_curves), minmax_curve_h, f, mesh=True)
            spawn += uv_spawn
            update += uv_update
        update.append(("Particles.Scale", "Vector", ue_scale_h(render_scale)))
    elif not light_only and not projected:
        # Sprite geometry width/height remain Unity X/Y; they are not 3D scale
        # axes. Niagara rotates the UV-down basis clockwise, hence -Unity Z.
        sprite_size = "((%s).xy * 100.0)" % render_scale
        if mode == 1:
            stretch = renderer_contract["stretch"]
            # 源尺寸用米，Native Velocity 已是厘米/秒；只对尺寸项换算一次。
            sprite_size = "float2((%s).x*100.0,sign((%s).y)*(abs((%s).y)*100.0*%s+length(Particles.Velocity)*%s))" % (
                render_scale, render_scale, scale_u, f(stretch["length_scale"]), f(stretch["velocity_scale"]))
        geometry = renderer_contract.get("sprite_geometry")
        if geometry is not None:
            if material_plan["dyn_params"].get(3, material_plan["dyn_params"].get("3")) != "SpriteGeometryTransport":
                raise SpecError("Sprite geometry material/particle DP3 transport mismatch")
            spawn.append(("Particles.UVScale", "Vector2", "float2(1.0,1.0)"))
            update.append(("Particles.UEFX_DrawSize", "Vector2", sprite_size))
            sprite_size = "(abs(Particles.UEFX_DrawSize)*%s)" % f(geometry["bound_scale"])
            if "depth_pivot" in geometry:
                update.append(("Particles.UEFX_DrawDepthSize", "Float", "((%s).z*100.0)" % render_scale))
                sprite_size = "(%s+abs(Particles.UEFX_DrawDepthSize*%s))" % (
                    sprite_size, f(geometry["depth_pivot"]["source_pivot_z"]))
        update += [("Particles.SpriteSize", "Vector2", sprite_size),
                   ("Particles.SpriteRotation", "Float", "0.0" if source_local_plane else "(-Particles.URot.z * %s)" % f(180 / math.pi))]
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
        if prop_contract is not None and prop_contract["system_age_dynamic_parameter_mask"]:
            age_transport = prop_contract["system_age_transport"]
            if slot != age_transport["slot"] or dyn.get(slot, dyn.get(str(slot))) != "OriginalSystemAge":
                raise SpecError("Prop不能覆盖原随机或Custom字段来运输Age")
            expr = "float4(%s)" % ",".join("System.Age" if component == age_transport["component"] else "0.0"
                                                    for component in range(4))
        elif slot == 3 and affine is not None:
            expr = "float4(System.Age,sign(%s))" % ue_scale_h("Particles.UAffineSignedSize")
        elif slot == 3 and renderer_contract.get("sprite_geometry") is not None:
            expr = ("float4(Particles.UEFX_DrawSize,Particles.UEFX_DrawDepthSize,0.0)"
                    if "depth_pivot" in renderer_contract["sprite_geometry"] else "float4(Particles.UEFX_DrawSize,0.0,0.0)")
        elif dyn.get(slot,dyn.get(str(slot))) == "MeshAlignmentEuler":
            expr = "float4(0.0,0.0,0.0,0.0)"
        elif slot in (0, 1):
            expr = custom_data_h(cd, slot, age, rnd, update_curves, gradient)
        elif slot == 2:
            expr = "Particles.UStable"
        else:
            expr = "float4(Particles.USize, 1.0 / Particles.Lifetime)"
        if mesh_alignment is not None:
            layout = mesh_alignment.get("euler_components",[[2,0],[2,1],[2,2]])
            if any(mapped_slot == slot for mapped_slot,component in layout):
                values = ["(%s).%s" % (expr,c) for c in "xyzw"]
                for axis,(mapped_slot,component) in enumerate(layout):
                    if mapped_slot == slot:
                        values[component] = "Particles.URot."+"xyz"[axis]
                expr = "float4(%s)" % ",".join(values)
        update.append((names[slot], "Vector4", expr))

    if prop_contract is not None:
        update += [("Particles.UEFX_SourceCustom1", "Vector4", custom_data_h(cd, 0, age, rnd, update_curves, gradient)),
                   ("Particles.UEFX_SourceCustom2", "Vector4", custom_data_h(cd, 1, age, rnd, update_curves, gradient))]

    if projected:
        update += projected_decal_entries(ps, node, sprite_matrix, chain, flip, cd, rnd, update_curves,
                                          gradient, projected_plan)
        if type(rd["m_SortingOrder"]) is not int:
            raise SpecError("Native Decal SortOrder需要原整数排序值")
        update.append(("Particles.UEFX_DecalSortOrder", "Int", str(rd["m_SortingOrder"])))

    light_renderer = None
    if light is not None:
        update += particle_light_entries(light, rnd, update_curves)
        light_renderer = {"kind": "light", "contract": light, "sort": rd["m_SortingOrder"]}
    if runtime_failure is not None:
        spawn += [("Particles.UEFX_RuntimeFailure", "Float", "0.0"), ("Particles.Alive", "Bool", "true")]
        update += [("Particles.UEFX_RuntimeFailure", "Float", frame_failure["code"]), ("Particles.Alive", "Bool", "Particles.Alive")]

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
        rate = emission_rate(em["rateOverTime"], path + ".EmissionModule.rateOverTime", emitter_update)
        distance_rate = minmax_curve_const(em["rateOverDistance"])
    emitter_spawn = []
    if distance_rate > 0:
        # Only a derived previous source-emitter position is retained. Native
        # SpawnPerUnit owns fractional count, spacing and emission lifecycle.
        # Rotation of an offset child must contribute, unlike Owner.Velocity.
        matrix_emission = affine is not None or sprite_matrix is not None
        emission_chain = affine_chain(path_nodes, clip, t_anim, "Emitter.UAffine") if matrix_emission else chain
        emission_origin = emission_chain.position if matrix_emission else chain.pos_h()
        emission_position = "(Engine.Owner.Position + %s)" % qrot_h(owner_q,
                                      "(Engine.Owner.Scale * %s)" % ue_pos_h(emission_origin))
        emitter_spawn = list(emission_chain.temps) + [("Emitter.UEFX_PreviousEmissionPosition", "Position", emission_position)]
        emitter_update += list(emission_chain.temps) + [
            ("Transient.UEFX_EmissionPosition", "Position", emission_position),
            ("Transient.UEFX_EmissionVelocity", "Vector", "(Engine.DeltaTime > 0.0 ? (Transient.UEFX_EmissionPosition-Emitter.UEFX_PreviousEmissionPosition)/Engine.DeltaTime : float3(0.0,0.0,0.0))"),
            ("Emitter.UEFX_PreviousEmissionPosition", "Position", "Transient.UEFX_EmissionPosition")]
    mesh_pid = str(rd["m_Mesh"]["m_PathID"])
    if mode == 4 and not projected and mesh_pid not in ue_assets:
        raise SpecError("%s 的网格 PathID %s 没有导入" % (path, mesh_pid))
    mats = [str(m["m_PathID"]) for m in rd["m_Materials"] if m["m_PathID"] != 0]
    if not light_only and len(mats) != 1:
        raise SpecError("%s 有 %d 个材质，多材质网格粒子未实现" % (path, len(mats)))
    if light_only:
        renderer = light_renderer
    elif projected:
        renderer = {"kind": "projected_decal", "material": material_paths[mats[0]],
                    "source_node": path, "source_transform": str(node["transform"]),
                    "contract": projected_plan["native_renderer_contract"],
                    "required_source_inputs": projected_plan["required_source_inputs"]}
    else:
        renderer = {"kind": "mesh" if mode == 4 else "sprite",
                    **({"additional_wpo_bounds_radius_cm": material_plan["additional_wpo_bounds_radius_cm"],
                        "vertex_deformation": material_plan["vertex_stage"]["deformation"]}
                       if material_plan.get("vertex_stage") is not None else {}),
                    **({"field_renderer": signed_field_renderer_contract(node, material_plan, renderer_contract)}
                       if material_plan.get("output_contract") == "distortion_field_pair" else {}),
                    **({"mesh_affine": mesh_affine_transport(affine)} if affine is not None else {}),
                    **({"mesh": ue_assets[mesh_pid]} if mode == 4 else {}),
                    "material": material_paths[mats[0]], "sort": rd["m_SortingOrder"], **renderer_contract}
        if material_plan.get("native_depth_velocity") is not None:
            import zzz_fx_native_shader as NS
            depth_velocity = NS.project_depth_velocity_contract(material_plan["native_depth_velocity"], mats[0])
            if mode == 4:
                if renderer.get("mesh_affine") is not None or renderer.get("field_renderer") is not None:
                    raise SpecError("Mesh额外Depth/Velocity需要原生TRS几何，FullAffine／Field尚未接线")
                renderer.update(native_depth_velocity=depth_velocity, source_material_slot=0,
                                source_material_pid=mats[0])
            elif (particle_trail is None or mode != 0 or renderer["kind"] != "sprite"
                    or str(particle_trail["source_materials"][0]["m_PathID"]) != depth_velocity["material_pid"]):
                raise SpecError("额外Depth/Velocity只接准确原两槽拖尾的Primary Billboard")
            else:
                renderer.update(native_depth_velocity=depth_velocity, source_material_slot=0)
    additional_renderers = [light_renderer] if light_renderer is not None and not light_only else []
    if prop_contract is not None:
        bindings = prop_plan["bindings"][mats[0]]
        renderer.update(material=bindings["prop_surface"], prop_role="prop_surface", native_prop_contract=prop_contract,
                        motion_vector_setting=prop_contract["motion_vector_setting"])
        additional_renderers.insert(0, {**renderer, "material": bindings["prop_forward_color"],
            "prop_role": "prop_forward_color", "motion_vector_setting": "Disable"})
    spec = {
        "name": re.sub(r"[^A-Za-z0-9_]", "_", path),
        "path": path, "local_space": sim_local if mode == 4 and not native_mesh_facing and not projected else False,
        "source_simulation_space": "local" if sim_local else "world", "source_scaling_mode": ps["scalingMode"],
        **({"project_transform": "FullAffineSpriteMotionAndColumnSize"} if sprite_matrix is not None else {}),
        "loop": bool(ps["looping"]), "duration": ps["lengthInSec"], "delay": minmax_curve_const(ps["startDelay"]),
        "bursts": bursts, "rate": rate, "spawn": spawn, "update": update, "requirements": requirements,
        "emitter_spawn": emitter_spawn, "emitter_update": emitter_update,
        "distance_rate": distance_rate,
        "particle_equivalence": policy,
        **({"project_motion": project_motion_policy(project_motion)} if project_motion is not None else {}),
        **({"project_gradient": gradient} if gradient is not None else {}),
        **({"runtime_failure": runtime_failure} if runtime_failure is not None else {}),
        **({"project_motion_metric": "WorldMetres" if ps["ClampVelocityModule"]["inWorldSpace"]
            else "SourceCurrentEmitterTRS"} if project_motion is not None and ps.get("ClampVelocityModule") else {}),
        "source_particle_lights": "NativeSameParticleRenderer" if light is not None else
            "explicit_null_template" if ps.get("LightsModule") else "disabled",
        **({"native_particle_limit": light["native_particle_limit"]}
           if light is not None and "native_particle_limit" in light else {}),
        **({"additional_renderers": additional_renderers} if additional_renderers else {}),
        "renderer": renderer,
        **({"source_particle_trail": particle_trail, "requires_persistent_ids": True} if particle_trail is not None else {}),
    }
    return configure_particle_trail_parent(spec, particle_trail) if particle_trail is not None else spec
