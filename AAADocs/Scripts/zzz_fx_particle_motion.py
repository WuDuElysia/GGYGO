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


def shape_contract(source, path):
    if source is None or not source["enabled"]:
        return None
    if source["type"] not in (0, 4):
        raise MotionError("%s ShapeModule.type=%r is not implemented" % (path, source["type"]))
    for field in ("randomDirectionAmount", "sphericalDirectionAmount", "randomPositionAmount"):
        if source[field] != 0:
            raise MotionError("%s ShapeModule.%s requires its source sampling rule" % (path, field))
    if source["alignToDirection"]:
        raise MotionError("%s ShapeModule.alignToDirection requires a rotation adapter" % path)
    if source["m_Texture"]["m_PathID"] or source["m_Texture"]["m_FileID"]:
        raise MotionError("%s ShapeModule texture sampling is not implemented" % path)
    radius = finite(source["radius"]["value"], path + ".ShapeModule.radius")
    thickness = finite(source["radiusThickness"], path + ".ShapeModule.radiusThickness")
    # Full volume and surface have unambiguous density. Intermediate thickness
    # needs source radial-kernel evidence, not an invented linear shell radius.
    if radius < 0 or thickness not in (0, 1):
        raise MotionError("%s ShapeModule requires nonnegative radius and surface/full-volume thickness" % path)
    angle = finite(source["angle"], path + ".ShapeModule.angle")
    if source["type"] == 4:
        if not 0 <= angle <= 90:
            raise MotionError("%s cone angle is outside [0,90]" % path)
        for field in ("radius", "arc"):
            if source[field]["mode"] != 0 or source[field]["spread"] != 0:
                raise MotionError("%s cone %s requires its source distribution mode" % (path, field))
        if source["arc"]["value"] != 360:
            raise MotionError("%s partial cone arc requires verified source start-angle convention" % path)
    transform = {field: tuple(finite(source[field][axis], path + ".ShapeModule." + field)
                             for axis in "xyz") for field in ("m_Position", "m_Rotation", "m_Scale")}
    return {"type": source["type"], "radius": radius, "thickness": thickness,
            "angle": angle, **transform}


def birth_shape_h(source, path, randoms, literal):
    """Return source-local sampling assignments plus the static shape transform.

    Sphere directions have uniform solid angle and volume positions use the
    cube-root radius. Cone base points use square-root radius for uniform area;
    directions diverge in proportion to distance from the center line.
    Native random sequence identity remains a separate visual validation fact.
    """
    plan = shape_contract(source, path)
    if plan is None:
        return [], "float3(0.0, 0.0, 0.0)", "float3(0.0, 0.0, 1.0)", None
    phi = "Transient.UShapePhi"
    entries = [(phi, "Float", "(%s * %s)" % (randoms.take(), literal(2 * math.pi)))]
    if plan["type"] == 0:
        z = "Transient.UShapeZ"
        radial = "Transient.UShapeRadius"
        entries.append((z, "Float", "(2.0 * %s - 1.0)" % randoms.take()))
        direction = "float3(sqrt(max(0.0, 1.0 - {z}*{z}))*cos({phi}), sqrt(max(0.0, 1.0 - {z}*{z}))*sin({phi}), {z})".format(z=z, phi=phi)
        radial_value = "1.0" if plan["thickness"] == 0 else "pow(%s, 1.0/3.0)" % randoms.take()
        entries += [(radial, "Float", "(%s * %s)" % (literal(plan["radius"]), radial_value)),
                    ("Transient.UShapeDirection", "Vector", direction)]
        position = "(Transient.UShapeDirection * %s)" % radial
    else:
        radial = "Transient.UShapeRadiusFraction"
        entries.append((radial, "Float", "1.0" if plan["thickness"] == 0 else "sqrt(%s)" % randoms.take()))
        entries.append(("Transient.UShapeDirection", "Vector", "normalize(float3({r}*cos({phi})*{s}, {r}*sin({phi})*{s}, {c}))".format(
            r=radial, phi=phi, s=literal(math.sin(math.radians(plan["angle"]))), c=literal(math.cos(math.radians(plan["angle"]))))))
        position = "float3({r}*cos({phi})*{radius}, {r}*sin({phi})*{radius}, 0.0)".format(
            r=radial, phi=phi, radius=literal(plan["radius"]))
    return entries, position, "Transient.UShapeDirection", plan


def linear_velocity_h(source, path, randoms, curve_program, minmax_curve_h):
    if source is None or not source["enabled"]:
        return "float3(0.0, 0.0, 0.0)", False
    for field in ("orbitalX", "orbitalY", "orbitalZ", "orbitalOffsetX", "orbitalOffsetY", "orbitalOffsetZ", "radial"):
        if not curve_is_zero(source[field]):
            raise MotionError("%s VelocityModule.%s requires its orbital/radial solver" % (path, field))
    modifier = source["speedModifier"]
    if modifier["minMaxState"] != 0 or modifier["scalar"] != 1:
        raise MotionError("%s VelocityModule.speedModifier requires its full source velocity contract" % path)
    expression = "float3(%s)" % ", ".join(minmax_curve_h(source[axis], "Particles.NormalizedAge",
                                   randoms.take(), curve_program) for axis in "xyz")
    return expression, bool(source["inWorldSpace"])


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
        if source["separateAxis"] or not curve_is_zero(source["drag"]):
            raise MotionError("%s ClampVelocityModule separate-axis/drag solver is not implemented" % path)
        dampen = finite(source["dampen"], path + ".ClampVelocityModule.dampen")
        if not 0 <= dampen <= 1:
            raise MotionError("%s ClampVelocityModule.dampen is outside [0,1]" % path)


def dampen_entries(source, limit, velocity, literal):
    """One native frame: decay only excess speed, retaining its direction.

    Feedback into base velocity is performed by the simulation-frame adapter.
    Exact Unity sampling order and discrete kernel remain unverified. The
    dt-exponent preserves the chosen decay over equal elapsed frame intervals.
    """
    speed = "Transient.UEFX_Speed"
    capped = "Transient.UEFX_Limit"
    remain = "Transient.UEFX_Remain"
    return [(speed, "Float", "length(%s)" % velocity),
            (capped, "Float", "max(0.0, %s)" % limit),
            (remain, "Float", "(Engine.DeltaTime > 0.0 ? pow(1.0-saturate(%s * Emitter.UEFX_DampenStrength), Engine.DeltaTime / Emitter.UEFX_DampenReferenceSeconds) : 1.0)" % literal(source["dampen"])),
            (velocity, "Vector", "(%s > 0.0 ? %s * ((min(%s,%s) + max(0.0,%s-%s)*%s) / %s) : %s)" %
             (speed, velocity, speed, capped, speed, capped, remain, speed, velocity))]
