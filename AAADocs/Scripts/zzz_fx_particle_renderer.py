"""Source particle renderer contracts, independent of simulation and editor calls.

Unity 2019.4 Renderer-module pivot is measured in particle-size units. Niagara's
mesh-local offset is multiplied by particle scale in NiagaraMeshParticleUtils.
Meshes are imported in centimetres; offsets use the same (-x, z, y) basis.
Sources: Unity 2019.4 Manual/PartSysRendererModule.html and the matching enums;
UE NiagaraMeshRendererMeshProperties.h / NiagaraMeshParticleUtils.ush.
"""
import math
import hashlib
import json
import zzz_fx_particle_motion as PM


class RendererError(ValueError):
    pass


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise RendererError("%s requires a finite source number: %r" % (label, value))
    return float(value)


def vector(source, field, path):
    return tuple(number(source[field][axis], path + "." + field + "." + axis) for axis in "xyz")


def draw_order(source, path):
    """Retain particle draw order; reject unsupported scene-sort bias.

    SortingFudge changes ordering between separate transparent scene objects.
    Niagara's integer SortOrderHint only orders renderers in a system, so rounding
    or copying this float would silently change the source contract.
    """
    mode = source["m_SortMode"]
    sorts = {0: "None", 1: "ViewDistance", 2: "CustomAscending", 3: "CustomDecending"}
    if type(mode) is not int or mode not in sorts:
        raise RendererError("%s unsupported source particle sort mode %r" % (path, mode))
    fudge = number(source["m_SortingFudge"], path + ".m_SortingFudge")
    if fudge != 0.0:
        raise RendererError("%s SortingFudge=%s requires a scene transparency ordering contract" % (path, fudge))
    return {"sort_mode": sorts[mode],
            "sort_attribute": "Particles.Age" if mode in (2, 3) else None}


def mesh_contract(source, path):
    order = draw_order(source, path)
    pivot = vector(source, "m_Pivot", path)
    flips = vector(source, "m_Flip", path)
    if any(value < 0.0 or value > 1.0 for value in flips):
        raise RendererError("%s renderer flip probabilities must be within [0,1]" % path)
    return {"pivot_offset": (-pivot[0] * 100.0, pivot[2] * 100.0, pivot[1] * 100.0),
            "pivot_space": "Mesh", **order, "flip_probability": flips}


def sprite_contract(source, path):
    """Source View billboards, with explicit remaining view-size requirement.

    The viewport clamp cannot be replaced by Niagara pixel-coverage fading.
    Its source bounds are retained for preflight; the builder rejects this
    requirement before creating any asset until its view-stage adapter exists.
    """
    if source["m_RenderMode"] != 0 or source["m_RenderAlignment"] != 0:
        raise RendererError("%s only View-aligned Billboard is implemented" % path)
    if not source["m_AllowRoll"]:
        raise RendererError("%s billboard without camera roll requires a facing adapter" % path)
    pivot = vector(source, "m_Pivot", path)
    if any(pivot):
        raise RendererError("%s billboard pivot requires verified geometry/Center-stream mapping" % path)
    flips = vector(source, "m_Flip", path)
    if any(value < 0.0 or value > 1.0 for value in flips) or flips[2] != 0:
        raise RendererError("%s invalid/unsupported billboard flip probabilities" % path)
    minimum = number(source["m_MinParticleSize"], path + ".m_MinParticleSize")
    maximum = number(source["m_MaxParticleSize"], path + ".m_MaxParticleSize")
    if minimum < 0 or maximum <= 0 or minimum > maximum:
        raise RendererError("%s invalid viewport particle-size interval" % path)
    return {**draw_order(source, path), "facing_mode": "FaceCameraPlane", "alignment": "Unaligned",
            "pivot_uv": (.5, .5), "flip_probability": flips,
            "viewport_size": (minimum, maximum),
            "requirements": ["source_viewport_size_limit"]}


def mesh_flip_h(probabilities, randoms):
    """Mirror renderer geometry with birth-stable random choices in Unity axes.

    This multiplier is applied after USize, so source Size/CustomData streams
    retain their simulation values and a renderer flip never changes motion.
    """
    axes = []
    for probability in probabilities:
        if probability == 0.0:
            axes.append("1.0")
        elif probability == 1.0:
            axes.append("-1.0")
        else:
            axes.append("(%s < %s ? -1.0 : 1.0)" % (randoms.take(), repr(probability)))
    return "float3(%s)" % ", ".join(axes)


def viewport_plan(source, policy, path):
    """Explicit UE geometry equivalent, separate from source pixel shading.

    Measure the maximum projected axis of the rotated billboard bounding box,
    as a fraction of that viewport axis. Unity's precise width/radius metric
    is unverified. Uses the actual view projection, including orthographic W;
    no guessed camera FOV, screen aspect, alpha fade or simulation size change.
    """
    contract = sprite_contract(source, path)
    policy = PM.equivalence_policy(policy)
    if policy is None:
        return None
    minimum, maximum = contract["viewport_size"]
    params = {"UEFX_MinViewportFraction": {"dim": 1, "value": minimum},
              "UEFX_MaxViewportFraction": {"dim": 1, "value": maximum},
              "UEFX_ViewportLimitScale": {"dim": 1, "value": policy["viewport_limit_scale"]}}
    code = """// UE equivalence: maximum projected billboard axis; calibrate against source.
float2 size = abs(PSize);
float c = abs(cos(PRot));
float s = abs(sin(PRot));
float2 span = float2(c*size.x+s*size.y, s*size.x+c*size.y);
float clipW = mul(float4(CenterView,1.0), ResolvedView.ViewToClip).w;
float2 projection = abs(float2(ResolvedView.ViewToClip[0][0], ResolvedView.ViewToClip[1][1]));
float2 fraction = span * projection / (2.0 * max(abs(clipW), 1.e-6));
float extent = max(fraction.x, fraction.y);
float factor = extent > 0.0 ? clamp(extent, UEFX_MinViewportFraction * UEFX_ViewportLimitScale,
                                  UEFX_MaxViewportFraction * UEFX_ViewportLimitScale) / extent : 1.0;
return (RawWorldPos-PPos) * (factor-1.0);
"""
    return {"mode": policy["mode"], "metric": "maximum_projected_axis_fraction",
            "precision": "UE_equivalent_requires_original_game_visual_calibration",
            "code": code, "params": params,
            "inputs": ["PSize", "PRot", "RawWorldPos", "PPos", "CenterView", *params]}


def viewport_signature(plan):
    """Machine contract joining a renderer to its generated material adapter."""
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode("utf-8")).hexdigest()
