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


def draw_order(source, path, *, signed_field=False, project_order=None):
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
    if fudge != 0.0 and not signed_field and project_order is None:
        raise RendererError("%s SortingFudge=%s requires a scene transparency ordering contract" % (path, fudge))
    return {"sort_mode": sorts[mode], "source_sorting_fudge": fudge,
            **({"project_scene_order": {**project_order, "source_sorting_order": source["m_SortingOrder"],
                "scene_distance_equivalence": False}} if project_order is not None and not signed_field else {}),
            **({"field_ordering": "IndependentSignedRGBAAddWithImmutableDepth"} if signed_field else {}),
            "sort_attribute": "Particles.Age" if mode in (2, 3) else None}


def mesh_contract(source, path, *, signed_field=False, project_order=None):
    order = draw_order(source, path, signed_field=signed_field, project_order=project_order)
    pivot = vector(source, "m_Pivot", path)
    flips = vector(source, "m_Flip", path)
    if any(value < 0.0 or value > 1.0 for value in flips):
        raise RendererError("%s renderer flip probabilities must be within [0,1]" % path)
    return {"pivot_offset": (-pivot[0] * 100.0, pivot[2] * 100.0, pivot[1] * 100.0),
            "pivot_space": "Mesh", **order, "flip_probability": flips}


def sprite_contract(source, path, *, project_geometry=None, signed_field=False):
    """Source View/Stretch billboards, with explicit remaining frame/view requirements.

    The viewport clamp cannot be replaced by Niagara pixel-coverage fading.
    Its source bounds are retained for preflight; the builder rejects this
    requirement before creating any asset until its view-stage adapter exists.
    """
    project_geometry = geometry_policy(project_geometry)
    stretched = source["m_RenderMode"] == 1 and project_geometry is not None
    plane_key = "horizontal_billboard" if source["m_RenderMode"] == 2 else (
        "local_billboard" if source["m_RenderMode"] == 0 and source["m_RenderAlignment"] == 2 else None)
    plane = (project_geometry or {}).get(plane_key)
    if plane is not None and signed_field:
        raise RendererError("%s field renderer has no declared custom-plane stream consumer" % path)
    material_facing = not stretched and source["m_RenderMode"] == 0 and source["m_RenderAlignment"] == 3 and not signed_field
    if material_facing and project_geometry is None:
        raise RendererError("%s source Facing requires its explicit ProjectConfigured material geometry adapter" % path)
    if plane is None and not stretched and (source["m_RenderMode"] != 0 or source["m_RenderAlignment"] not in (
            (0, 3) if signed_field or project_geometry is not None else (0,))):
        raise RendererError("%s only View Billboard or explicit Stretch is implemented" % path)
    if not source["m_AllowRoll"] and plane is None:
        raise RendererError("%s billboard without camera roll requires a facing adapter" % path)
    pivot = vector(source, "m_Pivot", path)
    if any(pivot) and project_geometry is None:
        raise RendererError("%s billboard pivot requires verified geometry/Center-stream mapping" % path)
    depth_pivot = None
    if pivot[2] != 0:
        if project_geometry is None or "depth_pivot_axis" not in project_geometry:
            raise RendererError("%s nonzero billboard Pivot.z needs an explicit project depth-axis decision" % path)
        depth_pivot = {"source_pivot_z": pivot[2],
                       "normal_sign": -1.0 if project_geometry["depth_pivot_axis"] == "RightCrossUp" else 1.0,
                       "decision_reference": project_geometry["depth_pivot_decision_reference"],
                       "size_source": "SignedSourceSizeZCM"}
    stretch = None
    if stretched:
        camera = number(source["m_CameraVelocityScale"], path + ".m_CameraVelocityScale")
        velocity = number(source["m_VelocityScale"], path + ".m_VelocityScale")
        length = number(source["m_LengthScale"], path + ".m_LengthScale")
        if camera != 0:
            raise RendererError("%s Stretch camera velocity requires its actual view-motion consumer" % path)
        # 已有 DP3 带符号几何链保留负 length/velocity；仅 Native bounds 取绝对值。
        stretch = {"length_scale": length, "velocity_scale": velocity, "camera_velocity_scale": camera,
                   "length_formula": "size_y_times_length_plus_world_speed_times_velocity_scale",
                   "precision": "ProjectConfiguredRequiresOriginalGameVisualCalibration"}
    flips = vector(source, "m_Flip", path)
    if any(value < 0.0 or value > 1.0 for value in flips) or flips[2] != 0:
        raise RendererError("%s invalid/unsupported billboard flip probabilities" % path)
    minimum = number(source["m_MinParticleSize"], path + ".m_MinParticleSize")
    maximum = number(source["m_MaxParticleSize"], path + ".m_MaxParticleSize")
    if minimum < 0 or maximum <= 0 or minimum > maximum:
        raise RendererError("%s invalid viewport particle-size interval" % path)
    pivot_uv = (.5 - pivot[0], .5 + pivot[1])
    bound_scale = max(1.0, max(abs(pivot_uv[0]), abs(1-pivot_uv[0]))
                      + max(abs(pivot_uv[1]), abs(1-pivot_uv[1])))
    return {**draw_order(source, path, signed_field=signed_field,
                         project_order=(project_geometry or {}).get("scene_sort")),
            # Stretch 沿 Native VelocityAligned 基底；View 保持相机平面。
            # Facing 须逐 View 朝相机位置，不用 FaceCamera 冒称已实现。
            "facing_mode": "CustomFacingVector" if plane is not None else
                "FaceCamera" if stretched or source["m_RenderAlignment"] == 3 else "FaceCameraPlane",
            **({"field_basis": "NativeVelocityAligned" if stretched else
                "CameraPositionWithViewRoll" if source["m_RenderAlignment"] == 3 else "NativeViewPlane"}
               if signed_field else {}),
            "alignment": "CustomAlignment" if plane is not None else "VelocityAligned" if stretched else "Unaligned",
            **({"project_plane": dict(plane), "source_render_alignment": source["m_RenderAlignment"],
                "source_allow_roll": source["m_AllowRoll"]} if plane is not None else {}),
            **({"material_facing": "CameraPositionWithViewRoll"} if material_facing else {}),
            # Niagara DynamicBounds 不计 Pivot，也不取负尺寸绝对值。项目图
            # 用正的保守尺寸扩界，WPO 消费真实带符号尺寸及 Pivot，原中心不变。
            "pivot_uv": (.5, .5) if project_geometry is not None else pivot_uv, "source_pivot": pivot,
            **({"sprite_geometry": {
                 "transport": "DP3=SignedDrawSizeCM.xyz,0" if depth_pivot else "DP3=SignedDrawSizeCM.xy,0,0",
                 "bound_scale": bound_scale,
                 "bounds": "NativeDynamicPositiveSpriteSizeWithDepthPivot" if depth_pivot else "NativeDynamicPositiveSpriteSize",
                 "native_uv_scale": (1.0, 1.0),
                 **({"depth_pivot": depth_pivot} if depth_pivot else {})}}
               if project_geometry is not None else {}),
            **({"stretch": stretch} if stretch is not None else {}), "flip_probability": flips,
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


def mesh_alignment_policy(policy):
    """显式项目 Mesh 基底／Euler 次序；未选择时保持缺来源拒绝。"""
    if policy is None:
        return None
    common = {"configuration_mode", "decision_reference", "source_transform", "alignment",
              "front_axis", "up_axis", "roll_offset_degrees", "order"}
    if not isinstance(policy, dict):
        raise RendererError("Mesh alignment requires an explicit ProjectConfigured object")
    mode = policy.get("alignment")
    if mode == "NativeCameraPlane":
        expected = {"configuration_mode", "decision_reference", "source_transform", "alignment", "mesh_rotation"}
        if set(policy) != expected or policy["configuration_mode"] != "ProjectConfigured" \
                or any(not isinstance(policy[k], str) or not policy[k].strip()
                       for k in ("decision_reference", "source_transform")) \
                or not isinstance(policy["mesh_rotation"], dict) \
                or set(policy["mesh_rotation"]) != {"pitch", "yaw", "roll"}:
            raise RendererError("Native Mesh camera plane requires the exact source and adjustable mesh rotation")
        return {**policy, "mesh_rotation": {k: number(v, "mesh_rotation."+k)
                                          for k,v in policy["mesh_rotation"].items()}}
    extra = {"view_xyz"} if mode == "View" else {"velocity_up_reference", "world_up"} if mode == "Velocity" else set()
    if not extra or set(policy) != common | extra or policy["configuration_mode"] != "ProjectConfigured" \
            or policy["order"] not in ("THRS", "TRHS") \
            or not isinstance(policy["decision_reference"], str) or not policy["decision_reference"].strip() \
            or not isinstance(policy["source_transform"], str) or not policy["source_transform"].strip():
        raise RendererError("Incomplete explicit Mesh frame/order/source decision")

    def unit(value, label):
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise RendererError(label + " requires XYZ")
        v = tuple(number(x, label) for x in value)
        if abs(sum(x*x for x in v)-1.0) > 1.e-5:
            raise RendererError(label + " requires a unit vector; no automatic normalization")
        return v

    def dot(a, b):
        return sum(x*y for x, y in zip(a, b))

    front, up = unit(policy["front_axis"], "front_axis"), unit(policy["up_axis"], "up_axis")
    if abs(dot(front, up)) > 1.e-5:
        raise RendererError("Mesh source front/up must be orthogonal")
    result = {**policy, "front_axis": front, "up_axis": up,
              "roll_offset_degrees": number(policy["roll_offset_degrees"], "roll_offset_degrees")}
    if mode == "View":
        xyz = policy["view_xyz"]
        if not isinstance(xyz, (list, tuple)) or len(xyz) != 3:
            raise RendererError("Mesh View requires three explicit camera-basis XYZ columns")
        x, y, z = tuple(unit(v, "view_xyz") for v in xyz)
        cross = (x[1]*y[2]-x[2]*y[1], x[2]*y[0]-x[0]*y[2], x[0]*y[1]-x[1]*y[0])
        if any(abs(dot(a, b)) > 1.e-5 for a, b in ((x, y), (x, z), (y, z))) or abs(dot(cross, z)-1.0) > 1.e-5:
            raise RendererError("Mesh View XYZ must be an orthonormal positive frame")
        result["view_xyz"] = (x, y, z)
    else:
        if policy["velocity_up_reference"] not in ("NodeUp", "WorldUp"):
            raise RendererError("Mesh Velocity requires explicit NodeUp or WorldUp")
        if policy["velocity_up_reference"] == "WorldUp":
            result["world_up"] = unit(policy["world_up"], "world_up")
        elif policy["world_up"] is not None:
            raise RendererError("NodeUp does not consume an implicit world reference")
    return result


def mesh_alignment_transport(policy, euler_components=None, source_components=0):
    """由同一项目选择派生原生单位姿态／Euler及界限运输声明。"""
    result = {"policy": mesh_alignment_policy(policy), "source_motion_vectors": 1,
            "native_orientation": "Identity", "native_facing": "Default",
            "euler_transport": "DP2.xyz=SourceEulerRadians", "required_components": 0x0700,
            "velocity_space": "LocalSimulationPositionDerivative",
            "root_bound": "OwnerScaleConditionNumber",
            "invalid_frame": "RejectParticle",
            "runtime_failure_consumer": "/Script/GGYGO.GGYGONiagaraRuntimeFailureDataInterface.ReportFailure",
            "failure_attribute": "Particles.UEFX_RuntimeFailure",
            "previous_baseline": "NativeCurrentParticleApproximationWithExplicitView",
            "verification_requirements": ["NativeShaderMapSlot2AndActualComponents",
                "FRayTracingDynamicGeometryConverterCS_ActualDispatchWithoutFallback",
                "NormalShadowBiasAndCurrentPrevious", "ConservativeBoundsUnderOwnerNonuniformScale"]}
    if euler_components is not None:
        if not isinstance(euler_components, list) or len(euler_components) != 3 \
                or any(not isinstance(pair, list) or len(pair) != 2 or type(pair[0]) is not int or type(pair[1]) is not int
                       or not 0 <= pair[0] <= 2 or not 0 <= pair[1] <= 3 for pair in euler_components) \
                or len({tuple(pair) for pair in euler_components}) != 3 \
                or type(source_components) is not int or not 0 <= source_components <= 0x0FFF:
            raise RendererError("Mesh Euler requires three distinct actual free DP components")
        mask = sum(1 << (slot*4+component) for slot,component in euler_components)
        if mask & source_components:
            raise RendererError("Mesh Euler transport would replace live original source data")
        result.update(euler_components=[list(pair) for pair in euler_components], source_dynamic_components=source_components,
            euler_transport="ExplicitFreeDPComponents=SourceEulerRadians", required_components=mask)
    return result


def validate_mesh_alignment_transport(transport):
    """资产写入前核同一 variant 的数据、几何与原生资格声明。"""
    if not isinstance(transport, dict) or not isinstance(transport.get("policy"), dict):
        raise RendererError("Incomplete project Mesh transport")
    expected = mesh_alignment_transport(transport["policy"], transport.get("euler_components"), transport.get("source_dynamic_components",0))
    if set(transport) != set(expected) or any(transport[key] != expected[key] for key in expected if key != "policy"):
        raise RendererError("Project Mesh Euler/normal/bounds transport mismatch")
    return expected["policy"]


def source_metric_failure_transport(source_transform, decision_reference, source_node, modules):
    return {"kind": "SourceMetricFrame", "policy": {"configuration_mode": "ProjectConfigured",
            "source_transform": str(source_transform), "decision_reference": decision_reference,
            "source_node": source_node, "modules": list(modules)},
            "failure_attribute": "Particles.UEFX_RuntimeFailure",
            "runtime_failure_consumer": "/Script/GGYGO.GGYGONiagaraRuntimeFailureDataInterface.ReportFailure"}



def particle_trail_failure_transport(source_transform, decision_reference, source_node, parent_emitter, prior=None):
    """原粒子拖尾的Root逆帧／父活字段失效，共用同一Alive失败属性和Native DI。"""
    return {"kind": "SourceParticleTrail", "policy": {"configuration_mode": "ProjectConfigured",
        "source_transform": str(source_transform), "decision_reference": decision_reference,
        "source_node": source_node, "parent_emitter": parent_emitter,
        "parent_dead_is_normal": True, "required_checks": ["ComponentRootInverse", "ParentAliveRequiredReadsValid"]},
        "prior_failure": prior, "failure_attribute": "Particles.UEFX_RuntimeFailure",
        "runtime_failure_consumer": "/Script/GGYGO.GGYGONiagaraRuntimeFailureDataInterface.ReportFailure"}


def validate_runtime_failure_transport(transport):
    """同一原Alive消费已声明空间／拖尾读取失败；源父死亡是正常分支。"""
    if isinstance(transport, dict) and transport.get("kind") == "SourceParticleTrail":
        policy = transport.get("policy")
        if (not isinstance(policy, dict) or set(policy) != {"configuration_mode", "source_transform", "decision_reference", "source_node", "parent_emitter", "parent_dead_is_normal", "required_checks"}
                or policy["configuration_mode"] != "ProjectConfigured" or policy["parent_dead_is_normal"] is not True
                or policy["required_checks"] != ["ComponentRootInverse", "ParentAliveRequiredReadsValid"]
                or any(not isinstance(policy[k], str) or not policy[k].strip()
                       for k in ("source_transform", "decision_reference", "source_node", "parent_emitter"))
                or transport != particle_trail_failure_transport(policy["source_transform"], policy["decision_reference"],
                     policy["source_node"], policy["parent_emitter"], transport.get("prior_failure"))):
            raise RendererError("Source Trail要求准确源／完整父ID／真实Valid及原Native失败消费者")
        prior = transport["prior_failure"]
        if prior is not None:
            if not isinstance(prior, dict) or prior.get("kind") == "SourceParticleTrail":
                raise RendererError("Source Trail不得叠第二条同源失败或递归失败状态")
            validate_runtime_failure_transport(prior)
        return policy
    if isinstance(transport, dict) and transport.get("kind") == "SourceMetricFrame":
        policy = transport.get("policy")
        if (not isinstance(policy, dict) or set(policy) != {"configuration_mode", "source_transform", "decision_reference", "source_node", "modules"}
                or policy["configuration_mode"] != "ProjectConfigured"
                or any(not isinstance(policy[k], str) or not policy[k].strip()
                       for k in ("source_transform", "decision_reference", "source_node"))
                or not isinstance(policy["modules"], list) or not policy["modules"]
                or any(not isinstance(module, str) for module in policy["modules"])
                or len(set(policy["modules"])) != len(policy["modules"])
                or set(policy["modules"])-{"ClampVelocityModule", "NoiseModule", "VelocityModule", "InitialModule.gravityModifier", "ForceModule"}
                or transport != source_metric_failure_transport(policy["source_transform"], policy["decision_reference"], policy["source_node"], policy["modules"])):
            raise RendererError("Source metric frame requires exact source/decision and the original native DI consumer")
        return policy
    return validate_mesh_alignment_transport(transport)


def geometry_policy(policy):
    """独立的项目几何选择，不借用无关的 ClampVelocity 等效参数。"""
    if policy is None:
        return None
    required = {"configuration_mode", "viewport_metric", "viewport_limit_scale"}
    depth_keys = {"depth_pivot_axis", "depth_pivot_decision_reference"}
    if not isinstance(policy, dict) or not required <= set(policy) or set(policy) - required - depth_keys - {"scene_sort", "horizontal_billboard", "local_billboard"} \
            or bool(set(policy) & depth_keys) != depth_keys.issubset(policy) \
            or policy["configuration_mode"] != "ProjectConfigured" \
            or policy["viewport_metric"] != "NativeQuadProjectedAxisFraction" \
            or number(policy["viewport_limit_scale"], "viewport_limit_scale") <= 0:
        raise RendererError("Missing explicit ProjectConfigured sprite geometry policy")
    if depth_keys.issubset(policy) and (policy["depth_pivot_axis"] not in ("RightCrossUp", "UpCrossRight")
            or not isinstance(policy["depth_pivot_decision_reference"], str)
            or not policy["depth_pivot_decision_reference"].strip()):
        raise RendererError("Sprite depth pivot requires an explicit axis and decision reference")
    if "scene_sort" in policy:
        order = policy["scene_sort"]
        if (not isinstance(order, dict) or set(order) != {"mode", "decision_reference", "priority_overrides"}
                or order["mode"] != "SourceOrderThenFudgeOrdinal"
                or not isinstance(order["decision_reference"], str) or not order["decision_reference"]
                or not isinstance(order["priority_overrides"], dict)
                or any(not isinstance(path, str) or not path or type(value) is not int
                       or not -(1 << 31) <= value < (1 << 31)
                       for path, value in order["priority_overrides"].items())):
            raise RendererError("Project renderer ordering requires explicit ordinal policy and int32 overrides")
    for name in ("horizontal_billboard", "local_billboard"):
        if name not in policy:
            continue
        plane = policy[name]
        axes_names = ("local_normal", "local_up") if name == "local_billboard" else ("world_normal", "world_up")
        mode = "NativeSourceLocalPlane" if name == "local_billboard" else "NativeWorldPlane"
        if not isinstance(plane, dict) or set(plane) != {"mode", *axes_names, "decision_reference"} \
                or plane["mode"] != mode or not isinstance(plane["decision_reference"], str) \
                or not plane["decision_reference"]:
            raise RendererError(name + " requires an explicit adjustable native world plane")
        axes = []
        for name in axes_names:
            axis = plane[name]
            if not isinstance(axis, (list, tuple)) or len(axis) != 3:
                raise RendererError("Incomplete horizontal billboard axis: " + name)
            axis = [number(v, name) for v in axis]
            if abs(sum(v*v for v in axis)-1.0) > 1.e-5:
                raise RendererError("Horizontal billboard axes must be normalized")
            axes.append(axis)
        if abs(sum(a*b for a,b in zip(*axes))) > 1.e-5:
            raise RendererError("Horizontal billboard axes must be perpendicular")
    return dict(policy)


def validate_sprite_geometry(geometry):
    """校验同一几何计划的尺寸传输、正 UV 和原生保守界限。"""
    common = {"transport", "bound_scale", "bounds", "native_uv_scale"}
    if not isinstance(geometry, dict) or set(geometry) not in (common, common | {"depth_pivot"}):
        raise RendererError("Incomplete sprite geometry transport contract")
    if number(geometry["bound_scale"], "sprite bound_scale") < 1.0:
        raise RendererError("Sprite bound_scale must cover the native centered quad")
    uv_scale = geometry["native_uv_scale"]
    if not isinstance(uv_scale, (tuple, list)) or len(uv_scale) != 2 \
            or any(number(v, "native_uv_scale") != 1.0 for v in uv_scale):
        raise RendererError("Sprite WPO requires positive unit native UVScale")
    if "depth_pivot" in geometry:
        depth = geometry["depth_pivot"]
        if not isinstance(depth, dict) or set(depth) != {"source_pivot_z", "normal_sign", "decision_reference", "size_source"} \
                or number(depth["source_pivot_z"], "source_pivot_z") == 0.0 \
                or number(depth["normal_sign"], "depth normal_sign") not in (-1.0, 1.0) \
                or depth["size_source"] != "SignedSourceSizeZCM" \
                or not isinstance(depth["decision_reference"], str) or not depth["decision_reference"].strip():
            raise RendererError("Incomplete explicit sprite depth-pivot contract")
        expected = ("DP3=SignedDrawSizeCM.xyz,0", "NativeDynamicPositiveSpriteSizeWithDepthPivot")
    else:
        expected = ("DP3=SignedDrawSizeCM.xy,0,0", "NativeDynamicPositiveSpriteSize")
    if (geometry["transport"], geometry["bounds"]) != expected:
        raise RendererError("Sprite transport and native bounds describe different geometry")


def _facing_frame_code():
    """沿原 Native 粒子近似，仅为新增 Facing 显式选择相机帧。"""
    return """float3 UEFX_OldR = Parameters.TangentToWorld[0];
float3 UEFX_OldD = Parameters.TangentToWorld[1];
float2 UEFX_Spin = float2(dot(UEFX_OldR,ResolvedView.ViewRight),dot(UEFX_OldR,-ResolvedView.ViewUp));
float UEFX_SpinSquared = dot(UEFX_Spin,UEFX_Spin);
UEFX_Spin *= UEFX_SpinSquared>0.0 ? rsqrt(UEFX_SpinSquared) : 0.0;
bool UEFX_Previous = UEFX_PreviousView>0.5;
float3 UEFX_ViewR = UEFX_Previous ? ResolvedView.PrevViewToTranslatedWorld[0].xyz : ResolvedView.ViewRight;
float3 UEFX_ViewU = UEFX_Previous ? ResolvedView.PrevViewToTranslatedWorld[1].xyz : ResolvedView.ViewUp;
float3 UEFX_ViewF = UEFX_Previous ? ResolvedView.PrevViewToTranslatedWorld[2].xyz : ResolvedView.ViewForward;
float3 UEFX_ToCamera = CamPos-PPos;
float UEFX_FacingSquared = dot(UEFX_ToCamera,UEFX_ToCamera);
float3 UEFX_Facing = UEFX_FacingSquared>0.0 ? UEFX_ToCamera*rsqrt(UEFX_FacingSquared) : -UEFX_ViewF;
float3 UEFX_R = cross(UEFX_Facing,UEFX_ViewU);
if (dot(UEFX_R,UEFX_R)<1.e-10)
    UEFX_R = UEFX_ViewR-UEFX_Facing*dot(UEFX_ViewR,UEFX_Facing);
UEFX_R = normalize(UEFX_R);
float3 UEFX_D = cross(UEFX_Facing,UEFX_R);
float3 UEFX_Right = UEFX_R*UEFX_Spin.x+UEFX_D*UEFX_Spin.y;
float3 UEFX_Down = UEFX_D*UEFX_Spin.x-UEFX_R*UEFX_Spin.y;
"""


def viewport_plan(source, policy, path, *, project_geometry=None, signed_field=False):
    """Explicit UE geometry equivalent, separate from source pixel shading.

    Measure the maximum projected axis of the rotated billboard bounding box,
    as a fraction of that viewport axis. Unity's precise width/radius metric
    is unverified. Uses the actual view projection, including orthographic W;
    no guessed camera FOV, screen aspect, alpha fade or simulation size change.
    """
    project_geometry = geometry_policy(project_geometry)
    contract = sprite_contract(source, path, project_geometry=project_geometry, signed_field=signed_field)
    if project_geometry is not None:
        minimum, maximum = contract["viewport_size"]
        if minimum != 0:
            raise RendererError("%s positive minimum viewport size requires expanded native bounds" % path)
        params = {"UEFX_MinViewportFraction": {"dim": 1, "value": minimum},
                  "UEFX_MaxViewportFraction": {"dim": 1, "value": maximum},
                  "UEFX_ViewportLimitScale": {"dim": 1, "value": project_geometry["viewport_limit_scale"]}}
        pivot = (.5 - contract["source_pivot"][0], .5 + contract["source_pivot"][1])
        geometry = contract["sprite_geometry"]
        validate_sprite_geometry(geometry)
        depth_code, depth_add = "", ""
        if "depth_pivot" in geometry:
            depth = geometry["depth_pivot"]
            depth_code = """float3 geometricNormal = cross(Parameters.TangentToWorld[0],Parameters.TangentToWorld[1]);
float normalLengthSquared = dot(geometricNormal,geometricNormal);
float3 depthDelta = (normalLengthSquared>0.0 ? geometricNormal*rsqrt(normalLengthSquared) : float3(0,0,0))*(DP3.z*%s*%s);
""" % (repr(depth["source_pivot_z"]), repr(depth["normal_sign"]))
            depth_add = "+depthDelta"
        code = """// 项目几何：实际 VF 切线、Stretch 尺寸和 Pivot 的四角投影。
float2 lo = float2(1.e30,1.e30), hi = -lo;
float2 pivot = float2(%s,%s);
float2 drawSize = DP3.xy;
%s[unroll] for (int i=0;i<4;++i) {
    float2 uv = float2(i & 1, (i >> 1) & 1);
    float3 delta = mul(drawSize * (uv-pivot), float2x3(Parameters.TangentToWorld[0],Parameters.TangentToWorld[1]))%s;
    float3 viewDelta = mul(delta,(float3x3)ResolvedView.TranslatedWorldToView);
    float4 clip = mul(float4(CenterView+viewDelta,1.0),ResolvedView.ViewToClip);
    float2 projected = clip.xy / max(abs(clip.w),1.e-6);
    lo=min(lo,projected); hi=max(hi,projected);
}
float extent=max(hi.x-lo.x,hi.y-lo.y)*0.5;
float factor=extent>0.0 ? min(1.0,UEFX_MaxViewportFraction*UEFX_ViewportLimitScale/extent) : 1.0;
float3 targetDelta = mul(drawSize*(UV0-pivot),float2x3(Parameters.TangentToWorld[0],Parameters.TangentToWorld[1]))%s;
return targetDelta*factor-(RawWorldPos-PPos);
""" % (repr(pivot[0]), repr(pivot[1]), depth_code, depth_add, depth_add)
        facing_adapter = None
        if contract.get("material_facing") is not None:
            # 仅替换原唯一几何链中的基底，不在 viewport 之后再叠 Facing WPO。
            code = code.replace("Parameters.TangentToWorld[0]", "UEFX_Right").replace(
                "Parameters.TangentToWorld[1]", "UEFX_Down").replace(
                "ResolvedView.TranslatedWorldToView", "UEFX_WorldToView").replace(
                "ResolvedView.ViewToClip", "UEFX_ViewToClip")
            code = _facing_frame_code() + """float3x3 UEFX_WorldToView = UEFX_Previous ? (float3x3)ResolvedView.PrevTranslatedWorldToView : (float3x3)ResolvedView.TranslatedWorldToView;
float4x4 UEFX_ViewToClip = UEFX_Previous ? ResolvedView.PrevViewToClip : ResolvedView.ViewToClip;
""" + code
            normal = _facing_frame_code() + """float3 UEFX_OldN = cross(UEFX_OldR,UEFX_OldD);
float UEFX_OldNSquared = dot(UEFX_OldN,UEFX_OldN);
UEFX_OldN *= UEFX_OldNSquared>0.0 ? rsqrt(UEFX_OldNSquared) : 0.0;
float3 UEFX_NewN = cross(UEFX_Right,UEFX_Down);
float3 UEFX_Normal = dot(NativeNormal,UEFX_OldR)*UEFX_Right+dot(NativeNormal,UEFX_OldD)*UEFX_Down+dot(NativeNormal,UEFX_OldN)*UEFX_NewN;
float UEFX_NormalSquared = dot(UEFX_Normal,UEFX_Normal);
return UEFX_NormalSquared>0.0 ? UEFX_Normal*rsqrt(UEFX_NormalSquared) : float3(0,0,0);
"""
            facing_adapter = {"kind": contract["material_facing"],
                "previous_baseline": "NativeParticleApproximationWithExplicitPreviousView",
                "normal_inputs": ["CamPos", "PPos", "UEFX_PreviousView", "NativeNormal"], "normal_code": normal,
                "verification_requirements": ["FRayTracingDynamicGeometryConverterCS_ActualDispatchWithoutFallback",
                    "CurrentPreviousNativeBaseline", "WorldNormalAndShadowBiasBaseline", "FullQuadAndConservativeBounds"]}
        return {"mode": "ProjectConfigured", "metric": project_geometry["viewport_metric"],
                "precision": "ProjectConfiguredRequiresOriginalGameVisualCalibration", "code": code, "params": params,
                "inputs": ["DP3", "UV0", "RawWorldPos", "PPos", "CenterView", *params]
                    + (["CamPos", "UEFX_PreviousView"] if facing_adapter is not None else []),
                "sprite_geometry": contract["sprite_geometry"], "source_pivot": contract["source_pivot"],
                **({"facing_adapter": facing_adapter} if facing_adapter is not None else {})}
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
