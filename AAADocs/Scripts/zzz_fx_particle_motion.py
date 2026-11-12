"""Birth-shape and linear velocity formulas in source Unity particle space.

This pure helper owns no clocks or runtime objects. The Niagara generator owns
coordinate conversion and ordered assignments; ParticleState owns retirement.
Unknown native kernels require an explicitly selected UE equivalence policy.
"""
import math


class MotionError(ValueError):
    pass


def finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise MotionError("%s requires a finite source number" % label)
    return float(value)


def curve_is_zero(curve):
    state = curve["minMaxState"]
    if state == 0:
        return curve["scalar"] == 0
    if state == 3:
        return curve["scalar"] == 0 and curve["minScalar"] == 0
    if state in (1, 2):
        if curve["scalar"] == 0:
            return True
        fields = ("maxCurve",) if state == 1 else ("maxCurve", "minCurve")
        return all(curve[field]["m_Curve"] and all(
            key["value"] == key["inSlope"] == key["outSlope"] == 0
            for key in curve[field]["m_Curve"]) for field in fields)
    return False


def shape_contract(source, path, project_shape=None, *, alignment_consumer=None):
    if source is None or not source["enabled"]:
        return None
    circle = source["type"] == 10 and project_shape is not None
    edge = source["type"] == 12 and project_shape is not None \
        and project_shape.get("edge_kernel") == "PositiveYEdgeDistanceSpeed"
    cone = source["type"] in (4, 8) and project_shape is not None \
        and project_shape.get("cone_kernel") == "UniformAreaAnnulusNativeBurstSpread"
    volume = source["type"] == 8 and cone \
        and project_shape.get("cone_volume_kernel") == "UniformFrustumVolumeOrLateralSurface"
    sphere_shell = source["type"] in (0, 2) and project_shape is not None \
        and project_shape.get("sphere_shell_kernel") == "UniformSolidAnglePositiveZHemisphereShell"
    donut = source["type"] == 17 and project_shape is not None \
        and project_shape.get("donut_kernel") == "ParametricDonutCrossSectionArea"
    if source["type"] not in (0, 4, 5) and not circle and not edge and not volume and not sphere_shell and not donut:
        raise MotionError("%s ShapeModule.type=%r is not implemented" % (path, source["type"]))
    for field in ("randomDirectionAmount", "sphericalDirectionAmount", "randomPositionAmount"):
        if source[field] != 0:
            raise MotionError("%s ShapeModule.%s requires its source sampling rule" % (path, field))
    if source["alignToDirection"] and (project_shape is None
            or project_shape.get("align_to_direction_kernel") != "NativeVelocityAlignedStretch"
            or alignment_consumer != "NativeVelocityAlignedStretch"):
        raise MotionError("%s ShapeModule.alignToDirection需要明确且已接的朝向消费者" % path)
    if source["m_Texture"]["m_PathID"] or source["m_Texture"]["m_FileID"]:
        raise MotionError("%s ShapeModule texture sampling is not implemented" % path)
    transform = {field: tuple(finite(source[field][axis], path + ".ShapeModule." + field)
                             for axis in "xyz") for field in ("m_Position", "m_Rotation", "m_Scale")}
    if source["alignToDirection"]:
        transform.update(source_align_to_direction=True, project_alignment_consumer=alignment_consumer,
                         source_birth_quaternion_recovered=False)
    if source["type"] == 5:
        return {"type": 5, "sampling": "IndependentUniformUnitBox", **transform}
    radius = finite(source["radius"]["value"], path + ".ShapeModule.radius")
    if edge:
        if radius < 0 or source["radius"]["mode"] not in (0, 1, 2):
            raise MotionError("%s Edge需要非负半长和Random／Loop／PingPong模式" % path)
        spread = finite(source["radius"]["spread"], path + ".ShapeModule.radius.spread")
        if not 0 <= spread <= 1:
            raise MotionError("%s Edge离散间隔必须在[0,1]" % path)
        speed = source["radius"]["speed"]
        if source["radius"]["mode"] != 0 and speed["minMaxState"] != 0:
            raise MotionError("%s Edge变速曲线需要真实相位积分，不能用当前速度乘年龄" % path)
        return {"type": 12, "radius": radius, "source_radius_mode": source["radius"]["mode"],
                "spread": spread, "speed": finite(speed["scalar"], path + ".ShapeModule.radius.speed"),
                "project_shape": dict(project_shape), **transform}
    if donut:
        tube = finite(source["donutRadius"], path + ".ShapeModule.donutRadius")
        thickness = finite(source["radiusThickness"], path + ".ShapeModule.radiusThickness")
        arc = finite(source["arc"]["value"], path + ".ShapeModule.arc")
        if radius < 0 or tube < 0 or not 0 <= thickness <= 1 or not 0 < arc <= 360:
            raise MotionError("%s Donut半径／管径／厚度／弧长无效" % path)
        modes = {}
        for field in ("radius", "arc"):
            row = source[field]
            mode, spread = row["mode"], finite(row["spread"], path + ".ShapeModule."+field+".spread")
            if mode not in (0, 1, 2) or not 0 <= spread <= 1:
                raise MotionError("%s Donut需明确Random／Loop／PingPong及有效间隔" % path)
            speed = None
            if mode != 0:
                if row["speed"]["minMaxState"] != 0:
                    raise MotionError("%s Donut变速相位需要真实积分，不能当前速度乘年龄" % path)
                speed = finite(row["speed"]["scalar"], path + ".ShapeModule."+field+".speed")
            modes[field] = {"mode": mode, "spread": spread, "speed": speed}
        return {"type": 17, "radius": radius, "tube_radius": tube, "thickness": thickness, "arc": arc,
                "source_modes": modes, "project_shape": dict(project_shape), **transform}
    thickness = finite(source["radiusThickness"], path + ".ShapeModule.radiusThickness")
    # Full volume and surface have unambiguous density. Intermediate thickness
    # needs source radial-kernel evidence, not an invented linear shell radius.
    if radius < 0 or (not 0 <= thickness <= 1 if circle or cone or sphere_shell else thickness not in (0, 1)):
        raise MotionError("%s ShapeModule requires nonnegative radius and surface/full-volume thickness" % path)
    angle = finite(source["angle"], path + ".ShapeModule.angle")
    if source["type"] in (4, 8):
        if not 0 <= angle <= 90:
            raise MotionError("%s cone angle is outside [0,90]" % path)
        for field in ("radius", "arc"):
            modes = (0, 3) if cone and field == "arc" else (0,)
            if source[field]["mode"] not in modes or source[field]["spread"] != 0:
                raise MotionError("%s cone %s requires its source distribution mode" % (path, field))
        if source["arc"]["value"] != 360 and not cone:
            raise MotionError("%s partial cone arc requires verified source start-angle convention" % path)
        if cone:
            arc = finite(source["arc"]["value"], path + ".ShapeModule.arc")
            if not 0 < arc <= 360:
                raise MotionError("%s cone arc must be in (0,360]" % path)
    if volume:
        length = finite(source["length"], path + ".ShapeModule.length")
        if length < 0 or length > 0 and angle >= 90:
            raise MotionError("%s 正长ConeVolume需要非负长度及小于90度的有限圆台" % path)
    if circle:
        if any(source[field]["mode"] != 0 or source[field]["spread"] != 0 for field in ("radius", "arc")):
            raise MotionError("%s circle requires the explicit random radius/arc mode" % path)
        arc = finite(source["arc"]["value"], path + ".ShapeModule.arc")
        if not 0 < arc <= 360:
            raise MotionError("%s circle arc must be in (0,360]" % path)
    return {"type": source["type"], "radius": radius, "thickness": thickness,
            "angle": angle, **({"arc": arc, "project_shape": dict(project_shape),
                "source_arc_mode": source["arc"]["mode"]} if circle or cone else {}),
            **({"length": length, "volume_kernel": project_shape["cone_volume_kernel"]} if volume else {}),
            **({"shell_kernel": project_shape["sphere_shell_kernel"]} if sphere_shell else {}), **transform}


def birth_shape_h(source, path, randoms, literal, project_shape=None, *, burst_spread_count=None, birth_seconds_h=None, alignment_consumer=None):
    """Return source-local sampling assignments plus the static shape transform.

    Sphere directions have uniform solid angle and volume positions use the
    cube-root radius. Cone base points use square-root radius for uniform area;
    directions diverge in proportion to distance from the center line.
    Native random sequence identity remains a separate visual validation fact.
    """
    plan = shape_contract(source, path, project_shape, alignment_consumer=alignment_consumer)
    if plan is None:
        return [], "float3(0.0, 0.0, 0.0)", "float3(0.0, 0.0, 1.0)", None
    if plan["type"] == 5:
        # Box是完整体积；Shape TRS由原Niagara坐标通路消费，方向保持源+Z。
        values = ["(%s-0.5)" % randoms.take() for _ in range(3)]
        return [], "float3(%s)" % ",".join(values), "float3(0.0,0.0,1.0)", plan
    if plan["type"] == 12:
        # Edge沿源X布点、向源+Y发射；TRS仍由原Shape通路唯一应用。
        radius = plan["radius"] * project_shape["radius_scale"]
        if plan["source_radius_mode"] == 0:
            fraction = randoms.take()
        elif radius == 0:
            fraction = "0.5"  # 合法零长边退化为原点，不计算除零相位。
        else:
            if birth_seconds_h is None:
                raise MotionError("%s Edge顺序采样缺原发射器出生时刻" % path)
            phase = "((%s)*%s)" % (birth_seconds_h, literal(
                plan["speed"] * project_shape["edge_speed_scale"] / (2.0 * radius)))
            fraction = "frac(%s)" % phase if plan["source_radius_mode"] == 1 else "(1.0-abs(2.0*frac((%s)*0.5)-1.0))" % phase
        if plan["spread"] > 0:
            step = literal(plan["spread"])
            fraction = "(floor((%s)/%s)*%s)" % (fraction, step, step)
        return [], "float3(((%s)*2.0-1.0)*%s,0.0,0.0)" % (fraction, literal(radius)), "float3(0.0,1.0,0.0)", plan
    if plan["type"] == 17:
        # 明确UE参数化核：原Loop速度按可调cycles/sec解释；不宣称恢复Unity原采样密度。
        phases = {}
        for field in ("radius", "arc"):
            source_mode = plan["source_modes"][field]
            if source_mode["mode"] == 0:
                value = randoms.take()
            else:
                if birth_seconds_h is None:
                    raise MotionError("%s Donut顺序采样缺同发射器出生时刻" % path)
                phase = "((%s)*%s)" % (birth_seconds_h, literal(source_mode["speed"]*project_shape["donut_speed_scale"]))
                value = "frac(%s)" % phase if source_mode["mode"] == 1 else "(1.0-abs(2.0*frac((%s)*0.5)-1.0))" % phase
            if source_mode["spread"] > 0:
                step = literal(source_mode["spread"])
                value = "(floor((%s)/%s)*%s)" % (value, step, step)
            phases[field] = value
        angle, tube_angle, tube_radius = "Transient.UShapeDonutPhi", "Transient.UShapeDonutTheta", "Transient.UShapeDonutRadius"
        outer = plan["tube_radius"]*project_shape["radius_scale"]*project_shape["donut_tube_radius_scale"]
        radial = ("1.0" if plan["thickness"] == 0 else "sqrt(lerp(%s,1.0,%s))" %
                  (literal((1.0-plan["thickness"])**2), randoms.take()))
        entries = [(angle, "Float", "(%s*%s+%s)" % (phases["arc"], literal(math.radians(plan["arc"])), literal(math.radians(project_shape["arc_start_degrees"])))),
                   (tube_angle, "Float", "(%s*%s)" % (phases["radius"], literal(2*math.pi))),
                   (tube_radius, "Float", "(%s*%s)" % (literal(outer), radial))]
        normal = "float3(cos(%s)*cos(%s),cos(%s)*sin(%s),sin(%s))" % (tube_angle, angle, tube_angle, angle, tube_angle)
        major = literal(plan["radius"]*project_shape["radius_scale"])
        point = "float3((%s+%s*cos(%s))*cos(%s),(%s+%s*cos(%s))*sin(%s),%s*sin(%s))" % (
            major,tube_radius,tube_angle,angle,major,tube_radius,tube_angle,angle,tube_radius,tube_angle)
        return entries, point, normal, plan
    phi = "Transient.UShapePhi"
    arc = math.radians(plan["arc"]) if "arc" in plan else 2*math.pi
    start = math.radians(project_shape["arc_start_degrees"]) if "arc" in plan else 0.0
    fraction = None
    if plan.get("source_arc_mode") == 3:
        if type(burst_spread_count) is not int or burst_spread_count <= 0:
            raise MotionError("%s BurstSpread requires the actual constant source burst count" % path)
        # Unity BurstSpread为均匀分布；端点/出生索引使用明确UE核，保源arc及真实burst数。
        denominator = burst_spread_count if plan["arc"] == 360 else burst_spread_count-1
        # VM 用整数除乘减保留余数，最后再转 float。
        fraction = "0.0" if denominator == 0 else "(float(Engine.ExecIndex - (Engine.ExecIndex / %d) * %d)/%s)" % (
            burst_spread_count, burst_spread_count, literal(denominator))
    entries = [(phi, "Float", "(%s * %s + %s)" % (fraction if fraction is not None else randoms.take(), literal(arc), literal(start)))]
    if plan["type"] == 10:
        radial = "Transient.UShapeRadius"
        inner = (1.0-plan["thickness"])**2
        entries += [(radial, "Float", "(%s*sqrt(lerp(%s,1.0,%s)))" % (
            literal(plan["radius"]*project_shape["radius_scale"]), literal(inner), randoms.take())),
            ("Transient.UShapeDirection", "Vector", "float3(cos(%s),sin(%s),0.0)" % (phi,phi))]
        position = "(Transient.UShapeDirection*%s)" % radial
    elif plan["type"] in (0, 2):
        z = "Transient.UShapeZ"
        radial = "Transient.UShapeRadius"
        entries.append((z, "Float", "(%s)" % randoms.take() if plan["type"] == 2 else "(2.0 * %s - 1.0)" % randoms.take()))
        direction = "float3(sqrt(max(0.0, 1.0 - {z}*{z}))*cos({phi}), sqrt(max(0.0, 1.0 - {z}*{z}))*sin({phi}), {z})".format(z=z, phi=phi)
        radial_value = "1.0" if plan["thickness"] == 0 else (
            "pow(%s, 1.0/3.0)" % randoms.take() if plan["thickness"] == 1 else
            "pow(lerp(%s,1.0,%s),1.0/3.0)" % (literal((1-plan["thickness"])**3), randoms.take()))
        radius = plan["radius"] * (project_shape["radius_scale"] if "shell_kernel" in plan else 1.0)
        entries += [(radial, "Float", "(%s * %s)" % (literal(radius), radial_value)),
                    ("Transient.UShapeDirection", "Vector", direction)]
        position = "(Transient.UShapeDirection * %s)" % radial
    else:
        radial = "Transient.UShapeRadiusFraction"
        radial_h = "1.0" if plan["thickness"] == 0 else (
            "sqrt(lerp(%s,1.0,%s))" % (literal((1-plan["thickness"])**2), randoms.take()))
        entries.append((radial, "Float", radial_h))
        entries.append(("Transient.UShapeDirection", "Vector", "normalize(float3({r}*cos({phi})*{s}, {r}*sin({phi})*{s}, {c}))".format(
            r=radial, phi=phi, s=literal(math.sin(math.radians(plan["angle"]))), c=literal(math.cos(math.radians(plan["angle"]))))))
        radius = plan["radius"] * (project_shape["radius_scale"] if "project_shape" in plan else 1.0)
        if plan["type"] == 8:
            # 圆台体积按截面积积分，零厚度按侧面积积分；零锥角合法退化为柱体。
            length = plan["length"] * project_shape["cone_volume_length_scale"]
            slope = math.tan(math.radians(plan["angle"]))
            along = randoms.take()
            z = "Transient.UShapeVolumeZ"
            if length == 0 or slope == 0:
                height = "(%s*%s)" % (along, literal(length))
            else:
                power = 2 if plan["thickness"] == 0 else 3
                end_radius = radius + length*slope
                height = "((pow(lerp(%s,%s,%s),%s)-%s)/%s)" % (
                    literal(radius**power), literal(end_radius**power), along,
                    literal(1.0/power), literal(radius), literal(slope))
            entries.append((z, "Float", height))
            position = "float3({r}*cos({phi})*({radius}+{z}*{slope}), {r}*sin({phi})*({radius}+{z}*{slope}), {z})".format(
                r=radial, phi=phi, radius=literal(radius), z=z, slope=literal(slope))
        else:
            position = "float3({r}*cos({phi})*{radius}, {r}*sin({phi})*{radius}, 0.0)".format(
                r=radial, phi=phi, radius=literal(radius))
    return entries, position, "Transient.UShapeDirection", plan


def _linear_components_h(source, path, randoms, curve_program, minmax_curve_h):
    if source is None or not source["enabled"]:
        return "float3(0.0, 0.0, 0.0)", False
    modifier = source["speedModifier"]
    if modifier["minMaxState"] != 0 or modifier["scalar"] != 1:
        raise MotionError("%s VelocityModule.speedModifier requires its full source velocity contract" % path)
    expression = "float3(%s)" % ", ".join(minmax_curve_h(source[axis], "Particles.NormalizedAge",
                                   randoms.take(), curve_program) for axis in "xyz")
    return expression, bool(source["inWorldSpace"])


def linear_velocity_h(source, path, randoms, curve_program, minmax_curve_h):
    if source is not None and source["enabled"]:
        for field in ("orbitalX", "orbitalY", "orbitalZ", "orbitalOffsetX", "orbitalOffsetY", "orbitalOffsetZ", "radial"):
            if not curve_is_zero(source[field]):
                raise MotionError("%s VelocityModule.%s requires its orbital/radial solver" % (path, field))
    return _linear_components_h(source, path, randoms, curve_program, minmax_curve_h)


def force_h(source, path, randoms, curve_program, minmax_curve_h):
    """源每轴力按同一粒子Update积分；随机双值的逐帧重抽样明确拒绝。"""
    if source is None or not source["enabled"]:
        return None, False
    if type(source["inWorldSpace"]) is not bool or type(source["randomizePerFrame"]) is not bool:
        raise MotionError("%s ForceModule空间／随机策略缺真实布尔字段" % path)
    if source["randomizePerFrame"] and any(source[axis]["minMaxState"] in (2, 3) for axis in "xyz"):
        raise MotionError("%s ForceModule逐帧随机双曲线需要明确源随机消费器" % path)
    values = [minmax_curve_h(source[axis], "Particles.NormalizedAge",
              randoms.take() if source[axis]["minMaxState"] in (2, 3) else "0.0", curve_program) for axis in "xyz"]
    return "float3(%s)" % ",".join(values), source["inWorldSpace"]


def project_extensions_policy(policy):
    """明确项目选择的扇环／轨道径向／噪声；数值和原曲线另行消费。"""
    if policy is None:
        return None
    keys = {"mode", "decision_reference", "shape", "velocity", "noise"}
    if not isinstance(policy, dict) or not keys <= set(policy) or set(policy) - keys - {"drag", "gravity"} \
            or policy["mode"] != "ProjectConfiguredMotionExtensions" or not isinstance(policy["decision_reference"], str) \
            or not policy["decision_reference"]:
        raise MotionError("Motion extensions require the explicit project decision")
    contracts = {"shape": ("UniformAreaCircleSector", {"arc_start_degrees", "radius_scale"}),
                 "velocity": ("CurrentFrameAngularCrossRadial", {"orbital_scale", "radial_scale"}),
                 "noise": ("SmoothValueNoise3D", {"frequency_scale", "strength_scale", "scroll_scale"})}
    for name,(kernel,values) in contracts.items():
        row=policy[name]
        optional = {"cone_kernel", "edge_kernel", "edge_speed_scale", "cone_volume_kernel", "cone_volume_length_scale", "sphere_shell_kernel", "align_to_direction_kernel", "donut_kernel", "donut_phase_kernel", "donut_speed_scale", "donut_tube_radius_scale"} if name == "shape" else {"size_kernel", "octave_kernel"} if name == "noise" else set()
        if not isinstance(row,dict) or not {"kernel",*values} <= set(row) or set(row)-{"kernel",*values}-optional or row["kernel"] != kernel:
            raise MotionError("Missing complete project kernel/tunables: "+name)
        if name == "shape" and any(key.startswith("donut_") for key in row):
            if (row.get("donut_kernel") != "ParametricDonutCrossSectionArea"
                    or row.get("donut_phase_kernel") != "ConfiguredSourceCyclesPerSecond"
                    or "donut_speed_scale" not in row or "donut_tube_radius_scale" not in row
                    or finite(row["donut_speed_scale"], "shape.donut_speed_scale") < 0
                    or finite(row["donut_tube_radius_scale"], "shape.donut_tube_radius_scale") < 0):
                raise MotionError("Donut需要完整明确的UE相位／横截面核与非负可调倍率")
        if name == "shape" and "cone_kernel" in row and row["cone_kernel"] != "UniformAreaAnnulusNativeBurstSpread":
            raise MotionError("Cone sampler requires its explicit project annulus/burst-spread kernel")
        if name == "shape" and "align_to_direction_kernel" in row \
                and row["align_to_direction_kernel"] != "NativeVelocityAlignedStretch":
            raise MotionError("AlignToDirection需要明确Native Stretch真实速度朝向核")
        if name == "shape" and ("cone_volume_kernel" in row or "cone_volume_length_scale" in row):
            if row.get("cone_volume_kernel") != "UniformFrustumVolumeOrLateralSurface" \
                    or "cone_volume_length_scale" not in row or finite(row["cone_volume_length_scale"], "shape.cone_volume_length_scale") < 0:
                raise MotionError("ConeVolume需要明确体积／侧面密度核及非负长度倍率")
        if name == "shape" and "sphere_shell_kernel" in row \
                and row["sphere_shell_kernel"] != "UniformSolidAnglePositiveZHemisphereShell":
            raise MotionError("Sphere／Hemisphere需要明确立体角及体积壳核")
        if name == "shape" and ("edge_kernel" in row or "edge_speed_scale" in row):
            if row.get("edge_kernel") != "PositiveYEdgeDistanceSpeed" or "edge_speed_scale" not in row \
                    or finite(row["edge_speed_scale"], "shape.edge_speed_scale") < 0:
                raise MotionError("Edge需要明确+Y线段／距离速度核及非负速度倍率")
        if name == "noise" and "size_kernel" in row and row["size_kernel"] != "MultiplicativeCurrentFrameField":
            raise MotionError("Noise size requires its explicit current-frame multiplier")
        if name == "noise" and "octave_kernel" in row and row["octave_kernel"] != "SourceWeightedAmplitudeNormalized":
            raise MotionError("Noise octave需要明确源频率／权重及幅值归一化核")
        for key in values:
            value=finite(row[key],name+"."+key)
            if key != "arc_start_degrees" and value < 0 or key == "frequency_scale" and value == 0:
                raise MotionError("Invalid project motion scale: "+name+"."+key)
    if "drag" in policy:
        drag = policy["drag"]
        if not isinstance(drag, dict) or set(drag) != {"kernel", "size_metric", "strength"} \
                or drag["kernel"] != "ExponentialMetricDecayAfterLimit" \
                or drag["size_metric"] != "MaximumAbsoluteSourceSizeMetres" \
                or finite(drag["strength"], "drag.strength") < 0:
            raise MotionError("Drag requires its explicit metric/order/strength")
    if "gravity" in policy:
        gravity = policy["gravity"]
        if not isinstance(gravity, dict) or set(gravity) != {"kernel", "world_metres_per_second_squared"} \
                or gravity["kernel"] != "ConfiguredWorldAcceleration" \
                or not isinstance(gravity["world_metres_per_second_squared"], (list, tuple)) \
                or len(gravity["world_metres_per_second_squared"]) != 3:
            raise MotionError("Gravity requires an explicit project world acceleration")
        for value in gravity["world_metres_per_second_squared"]:
            finite(value, "gravity.world_metres_per_second_squared")
    return {k:dict(v) if isinstance(v,dict) else v for k,v in policy.items()}


def needs_source_position(source):
    return source is not None and source["enabled"] and any(
        not curve_is_zero(source[field]) for field in ("orbitalX", "orbitalY", "orbitalZ", "radial"))


def project_velocity_h(source, path, randoms, curves, curve_h, position, policy, literal):
    """源寿命曲线保持；项目角速度叉乘及径向分量在同一当前模拟帧求值。"""
    linear,world=_linear_components_h(source,path,randoms,curves,curve_h)
    if source is None or not source["enabled"]:
        return linear,world
    if world:
        if any(not curve_is_zero(source[axis]) for axis in "xyz"):
            raise MotionError("%s project nonzero World linear velocity requires its inverse simulation-frame conversion" % path)
        # Space限定线性XYZ；原三轴严格为零时不需要换帧，保原角速度核和随机消费。
        world = False
    if not needs_source_position(source):
        return linear, world
    def sample(name):
        return curve_h(source[name],"Particles.NormalizedAge",randoms.take(),curves)
    omega="float3(%s)" % ",".join(sample(k) for k in ("orbitalX","orbitalY","orbitalZ"))
    offset="float3(%s)" % ",".join(sample(k) for k in ("orbitalOffsetX","orbitalOffsetY","orbitalOffsetZ"))
    radius="(%s-%s)" % (position,offset)
    direction="(dot(%s,%s)>0.0 ? %s*rsqrt(max(dot(%s,%s),1.e-30)) : float3(0,0,0))" % (radius,radius,radius,radius,radius)
    return "(%s+cross(%s,%s)*%s+%s*(%s)*%s)" % (
        linear,omega,radius,literal(policy["orbital_scale"]),direction,sample("radial"),literal(policy["radial_scale"])),False


def noise_contract(source,path,policy):
    if source is None or not source["enabled"]:
        return None
    if policy is None:
        raise MotionError("%s NoiseModule requires an explicit project kernel" % path)
    if source["quality"] != 2 or source["remapEnabled"]:
        raise MotionError("%s unsupported noise dimension/remap" % path)
    count = source["octaves"]
    if type(count) is not int or not 1 <= count <= 4:
        raise MotionError("%s NoiseModule源octaves不在项目支持的整数1～4范围" % path)
    layers = [(1.0, 1.0)]
    if count > 1:
        if policy.get("octave_kernel") != "SourceWeightedAmplitudeNormalized":
            raise MotionError("%s 多层Noise需要明确源频率／权重及幅值归一化核" % path)
        multiplier = finite(source["octaveMultiplier"], path+".NoiseModule.octaveMultiplier")
        scale = finite(source["octaveScale"], path+".NoiseModule.octaveScale")
        if multiplier < 0 or scale <= 0:
            raise MotionError("%s Noise octave需要非负强度倍率与正频率倍率" % path)
        for index in range(1, count):
            frequency_scale = finite(layers[-1][0]*scale, path+".NoiseModule.octaveFrequency")
            weight = finite(layers[-1][1]*multiplier, path+".NoiseModule.octaveWeight")
            if frequency_scale <= 0:
                raise MotionError("%s Noise octave频率倍率下溢为0" % path)
            layers.append((frequency_scale, weight))
        total = finite(sum(weight for _, weight in layers), path+".NoiseModule.octaveWeightSum")
        layers = [(frequency_scale, weight/total) for frequency_scale, weight in layers]
    if not curve_is_zero(source["rotationAmount"]):
        raise MotionError("%s noise rotation integration is not implemented" % path)
    if not curve_is_zero(source["sizeAmount"]) and policy.get("size_kernel") != "MultiplicativeCurrentFrameField":
        raise MotionError("%s noise size requires its declared current-frame multiplier" % path)
    frequency=finite(finite(source["frequency"],path+".NoiseModule.frequency")*policy["frequency_scale"],
                     path+".NoiseModule.configuredFrequency")
    if frequency <= 0:
        raise MotionError("%s noise frequency must be positive" % path)
    return {"frequency":frequency,"frequency_damping":bool(source["damping"]), "layers": layers}


def _value_noise_3d_entries(point, prefix, literal):
    """同一无状态值噪声层；独立瞬态名隔离octave，不增加粒子历史或随机消费。"""
    cell, fraction, weight = prefix+"Cell", prefix+"Fraction", prefix+"Weight"
    entries=[(cell,"Vector","floor(%s)" % point),
             (fraction,"Vector","frac(%s)" % point),
             (weight,"Vector","(pow(%s,3.0)*(%s*(%s*6.0-15.0)+10.0))" % (fraction,fraction,fraction))]
    components=[]
    for axis in range(3):
        corners=[]
        for i in range(8):
            name=prefix+"%d_%d" % (axis,i)
            corner="(%s+float3(%d,%d,%d))" % (cell,i&1,(i>>1)&1,(i>>2)&1)
            entries.append((name,"Float","(frac(sin(dot(%s,float3(127.1,311.7,74.7))+%s)*43758.5453)*2.0-1.0)" % (corner,literal(axis*53.36))))
            corners.append(name)
        x=["lerp(%s,%s,%s.x)" % (*corners[i:i+2],weight) for i in range(0,8,2)]
        y=["lerp(%s,%s,%s.y)" % (*x[i:i+2],weight) for i in range(0,4,2)]
        components.append("lerp(%s,%s,%s.z)" % (*y,weight))
    return entries,"float3(%s)" % ",".join(components)


def project_noise_entries(source,path,policy,position,randoms,curves,curve_h,literal):
    """便携 CPU VM 的同帧三维噪声；源octave按显式UE政策归一化叠加。"""
    contract=noise_contract(source,path,policy)
    if contract is None:
        return [],"float3(0,0,0)"
    age="Particles.NormalizedAge"
    scroll=curve_h(source["scrollSpeed"],age,randoms.take(),curves)
    point="Transient.UEFX_NoisePoint"
    entries=[(point,"Vector","(%s*%s+float3(0.0,(%s)*System.Age*%s,0.0))" % (
        position,literal(contract["frequency"]),scroll,literal(policy["scroll_scale"])))]
    fields=[]
    for index,(frequency_scale,weight) in enumerate(contract["layers"]):
        prefix="Transient.UEFX_Noise" if len(contract["layers"]) == 1 else "Transient.UEFX_NoiseOctave%d_" % index
        layer_point=point
        if len(contract["layers"]) > 1:
            layer_point=prefix+"Point"
            entries.append((layer_point,"Vector","(%s*%s)" % (point,literal(frequency_scale))))
        layer_entries,vector=_value_noise_3d_entries(layer_point,prefix,literal)
        entries+=layer_entries
        if len(contract["layers"]) == 1:
            fields.append(vector)
        else:
            layer_field=prefix+"Field"
            entries.append((layer_field,"Vector",vector))
            fields.append("(%s*%s)" % (layer_field,literal(weight)))
    if source["separateAxes"]:
        strength=[curve_h(source[k],age,randoms.take(),curves) for k in ("strength","strengthY","strengthZ")]
    else:
        shared_strength=curve_h(source["strength"],age,randoms.take(),curves)
        strength=[shared_strength]*3
    amount=curve_h(source["positionAmount"],age,randoms.take(),curves)
    scale=policy["strength_scale"]/(contract["frequency"] if contract["frequency_damping"] else 1.0)
    field="Transient.UEFX_NoiseField"
    entries.append((field,"Vector","(%s*float3(%s))" % (
        fields[0] if len(fields) == 1 else "("+"+".join(fields)+")",",".join(strength))))
    if not curve_is_zero(source["sizeAmount"]):
        size=curve_h(source["sizeAmount"],age,randoms.take(),curves)
        # USize已由本帧原StartSize/SizeModule重算；不把上一帧noise乘数反馈为新基线。
        entries.append(("Particles.USize","Vector","(Particles.USize*(float3(1,1,1)+%s*(%s)*%s))" % (
            field,size,literal(policy["strength_scale"]))))
    return entries,"(%s*(%s)*%s)" % (field,amount,literal(scale))


EQUIVALENCE_MODE = "source_particles_ue_equivalent_v1"


def equivalence_policy(policy):
    """Explicit opt-in; calibration interval is a coefficient unit, not a clock.

    Source textures, curves, emission and lifecycle remain authoritative. Only
    excess-speed damping and viewport measurement are approximated. These
    choices require original-game visual calibration, not claims of identity.
    """
    if policy is None:
        return None
    expected = {"mode", "dampen_reference_seconds", "dampen_strength", "viewport_limit_scale"}
    if not isinstance(policy, dict) or set(policy) != expected or policy["mode"] != EQUIVALENCE_MODE:
        raise MotionError("Particle equivalence requires the explicit supported mode and all tunables")
    result = {"mode": EQUIVALENCE_MODE}
    for key in expected - {"mode"}:
        result[key] = finite(policy[key], "equivalence." + key)
        if result[key] <= 0:
            raise MotionError("equivalence.%s must be positive" % key)
    return result


def check_limit_velocity(source, path, policy=None):
    if source is not None and source["enabled"]:
        if policy is None:
            raise MotionError("%s ClampVelocityModule requires verified native dampen/drag integration or explicit UE equivalence; dampen=%r" %
                              (path, source["dampen"]))
        if source["separateAxis"]:
            raise MotionError("%s ClampVelocityModule separate-axis solver is not implemented" % path)
        if not curve_is_zero(source["drag"]):
            if (policy.get("extensions") or {}).get("drag") is None:
                raise MotionError("%s drag requires its explicit metric decay kernel" % path)
            drag = source["drag"]
            values = [drag["scalar"]] if drag["minMaxState"] == 0 else [drag["minScalar"], drag["scalar"]] \
                if drag["minMaxState"] == 3 else None
            if values is None or any(finite(v, path+".drag") < 0 for v in values):
                raise MotionError("%s drag requires nonnegative source constant/range; curve extrema are unresolved" % path)
        dampen = finite(source["dampen"], path + ".ClampVelocityModule.dampen")
        if not 0 <= dampen <= 1:
            raise MotionError("%s ClampVelocityModule.dampen is outside [0,1]" % path)


def dampen_entries(source, limit, velocity, literal, *, drag=None, drag_strength=1.0):
    """One native frame: decay only excess speed, retaining its direction.

    Feedback into base velocity is performed by the simulation-frame adapter.
    Exact Unity sampling order and discrete kernel remain unverified. The
    dt-exponent preserves the chosen decay over equal elapsed frame intervals.
    """
    speed = "Transient.UEFX_Speed"
    capped = "Transient.UEFX_Limit"
    remain = "Transient.UEFX_Remain"
    result = [(speed, "Float", "length(%s)" % velocity),
            (capped, "Float", "max(0.0, %s)" % limit),
            (remain, "Float", "(Engine.DeltaTime > 0.0 ? pow(1.0-saturate(%s * Emitter.UEFX_DampenStrength), Engine.DeltaTime / Emitter.UEFX_DampenReferenceSeconds) : 1.0)" % literal(source["dampen"])),
            (velocity, "Vector", "(%s > 0.0 ? %s * ((min(%s,%s) + max(0.0,%s-%s)*%s) / %s) : %s)" %
             (speed, velocity, speed, capped, speed, capped, remain, speed, velocity))]
    if drag is not None:
        size = "max(abs(Particles.USize.x),max(abs(Particles.USize.y),abs(Particles.USize.z)))" \
            if source["multiplyDragByParticleSize"] else "1.0"
        speed_scale = "length(%s)" % velocity if source["multiplyDragByParticleVelocity"] else "1.0"
        result.append((velocity, "Vector", "(%s*exp(-(%s)*%s*%s*%s*Engine.DeltaTime))" % (
            velocity,drag,literal(drag_strength),size,speed_scale)))
    return result
