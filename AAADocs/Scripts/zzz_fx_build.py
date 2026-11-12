"""Offline complete-render preflight and exact, create-only FX asset batches.

Unsupported visible branches block ALL writes. Compile, action integration and
visual comparison are separate acceptance facts; old assets are preserved.
"""
import argparse
import ast
import copy
import hashlib
import json
import re
import sys
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_fx_material as FM
import zzz_fx_niagara as FN
import zzz_fx_particle_renderer as PR
import zzz_fx_particle_uv as PU
import zzz_fx_mesh_renderer as MR
import zzz_unity_anim as UA
from zzz_fx_asset_session import AssetSession, version_name, verify_readonly_asset_files
from zzz_fx_material_ue import Builder, MASTER_DIR, MI_DIR
from zzz_fx_niagara_ue import NiagaraBuilder

SYSTEM_DIR = "/Game/Characters/Player/Pyrios/FX/Skill"
RAW_ROOT = Path(r"F:\AnimeStudio\Exports\ZZZ\Pyrois_SkillFX\Raw")
UNSUPPORTED_RENDERERS = {"TrailRenderer", "LineRenderer", "SkinnedMeshRenderer", "SpriteRenderer"}


class PreflightError(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__("FX preflight failed; no editor mutation: " +
                         "; ".join(x["node"] + ": " + x["reason"] for x in report["blocked"]))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def dependency_path(fx_path, fx=None, explicit=None):
    fx = read_json(fx_path) if fx is None else fx
    version = fx.get("schemaVersion", 1)
    if version not in (1, 2):
        raise ValueError("Unsupported FX source schema: " + str(version))
    if explicit is not None:
        return Path(explicit)
    path = Path(fx_path)
    if not path.name.endswith(".fx.json"):
        raise ValueError("FX source must have the .fx.json suffix")
    suffix = ".deps.v2.json" if version == 2 else ".deps.json"
    return path.with_name(path.name[:-len(".fx.json")] + suffix)


def walk(node, path=(), active=True, *, project_active=()):
    label = "/".join(n["name"] for n in path) or "$root"
    active = active and (bool(node["active"]) or label in project_active)
    yield node, path, active
    for child in node["children"]:
        yield from walk(child, path + (child,), active, project_active=project_active)


def source_activation_paths(fx, policy):
    """显式项目激活仅覆盖准确source-inactive节点，原数据与renderer enabled保持。"""
    if policy is None:
        return set()
    if (not isinstance(policy, dict) or set(policy) != {"mode", "nodes"}
            or policy["mode"] != "EnableExactSourceInactiveNodes"
            or not isinstance(policy["nodes"], list) or not policy["nodes"]):
        raise ValueError("项目激活缺准确inactive节点合同")
    source = {"/".join(n["name"] for n in path) or "$root": node for node, path, _ in walk(fx["root"])}
    paths = set()
    for row in policy["nodes"]:
        if not isinstance(row, dict) or set(row) != {"node", "source_transform", "source_active"}:
            raise ValueError("项目激活节点身份不完整")
        node = source.get(row["node"])
        if (node is None or row["node"] in paths or row["source_active"] is not False
                or node["active"] is not False or row["source_transform"] != str(node["transform"])):
            raise ValueError("项目激活不是准确原inactive节点: " + str(row.get("node")))
        paths.add(row["node"])
    return paths


def component_identity(item, component_type):
    components = [c for c in item.get("components", []) if c["type"] == component_type]
    if not item.get("componentListProof") or len(components) != 1:
        raise ValueError("Particle Light 需要唯一且完整的组件身份证明")
    component = components[0]
    explicit = item.get("lightSource") if component_type == "Light" else item.get("particleSource", {}).get("system")
    if explicit is not None:
        if str(explicit["pathID"]) != str(component["pathID"]):
            raise ValueError("Particle Light typed 正文和组件 PathID 不一致")
        return {"block": str(explicit["block"]), "cab": explicit["cab"], "pathID": str(explicit["pathID"]),
                "raw_sha256": explicit["rawSha256"]}
    return {"block": str(component["sourceBlock"]), "cab": component["cab"], "pathID": str(component["pathID"]),
            "raw_sha256": component["rawSha256"]}



def particle_light_source(node, rows):
    """只读同一导出中的准确本地 Light PPtr；模板不受节点 active 过滤。"""
    module = node["particle"]["system"].get("LightsModule")
    if not module or not module["enabled"] or not module["light"]["m_PathID"]:
        return None
    pointer = module["light"]
    if pointer["m_FileID"] != 0:
        raise ValueError("Particle Light 外部 CAB 引用尚无准确模板正文消费者")

    source = component_identity(node, "ParticleSystem")
    found = []
    for candidate, _, _ in rows:
        if not candidate.get("light"):
            continue
        ids = [c["pathID"] for c in candidate.get("components", []) if c["type"] == "Light"]
        if pointer["m_PathID"] not in ids:
            continue
        target = component_identity(candidate, "Light")
        if (target["block"], target["cab"]) == (source["block"], source["cab"]):
            found.append({"identity": target, "light": candidate["light"]})
    if len(found) != 1:
        raise ValueError("Particle Light 本地 PPtr 未解析到唯一同 CAB typed 模板")
    return found[0]


def dependency_file(deps, pid, extension):
    entry = deps.get(str(pid))
    if entry is None:
        raise ValueError("Missing dependency PathID " + str(pid))
    files = [Path(f) for f in entry["files"] if f.lower().endswith(extension)]
    if len(files) != 1 or not files[0].is_file():
        raise ValueError("Expected one existing %s file for PathID %s" % (extension, pid))
    return files[0]


def uv_count(deps, mesh_pid):
    mesh = read_json(dependency_file(deps, mesh_pid, ".json"))
    channels = [k for k in range(8) if mesh.get("m_UV%d" % k)]
    return max(channels) + 1 if channels else 0


def material_plan(deps, mpid, renderer, assets, native_selection=None, output_contract="color", *, project_camera=None):
    source = dependency_file(deps, mpid, ".json")
    shader_id = str(FM.material_input(read_json(source))["m_Shader"]["m_PathID"])
    shader = deps.get(shader_id)
    if shader is None or shader["type"] != "Shader":
        raise ValueError("Missing Shader dependency " + shader_id)
    if shader.get("nativeJson") and shader.get("cab"):
        if native_selection is None:
            raise FM.PlanError("Native Shader %s in %s requires exact subprogram/global keyword selection; "
                               "the legacy variant directory will not be used" % (shader_id, shader["cab"]))
        renderer = {**renderer, **({"project_camera": project_camera} if project_camera is not None else {})}
        return FM.plan(source, renderer, assets, shader_name=shader["name"], output_contract=output_contract, native_source={
            "shader_entry": shader, "material_pid": mpid, "selection": native_selection,
            "texture_entries": {pid: entry for pid, entry in deps.items() if entry.get("type") == "Texture2D"}})
    if native_selection is not None:
        raise FM.PlanError("Native preview selection requires its exact native Shader dependency")
    return FM.plan(source, renderer, assets, shader_name=shader["name"], output_contract=output_contract)


def mi_name(plan, revision=""):
    return version_name("MI_" + plan["material"], {"master": plan["master"],
                        "params": plan["params"], "textures": plan["textures"], "revision": revision})


def inspect_source_programs(fx_paths, material_audits):
    """仅审计既有 Particle Renderer 清单，不选择运行策略或认证完整 Prefab。

    保留停用 Renderer／Pass，核验启用候选的原字节及各自关键词声明。
    完整材质输入与程序声明分别报告；结果不能用作资产写入计划。
    """
    import zzz_fx_native_shader as NS
    visible, disabled, materials = [], [], {}
    for fx_path in fx_paths:
        fx = read_json(fx_path)
        deps = read_json(dependency_path(fx_path, fx))
        for node, path, active in walk(fx["root"]):
            if not active or not node.get("particle") or not node["particle"]["renderer"]:
                continue
            renderer = node["particle"]["renderer"]
            mids = [str(m["m_PathID"]) for m in renderer["m_Materials"] if m["m_PathID"]]
            label = "/".join(n["name"] for n in path) or "$root"
            row = {"prefab": fx["name"], "node": label, "materials": mids}
            if not renderer["m_Enabled"] or not mids:
                disabled.append(row)
                continue
            visible.append(row)
            for mid in mids:
                source = dependency_file(deps, mid, ".json")
                material = FM.material_input(read_json(source))
                shader_id = str(material["m_Shader"]["m_PathID"])
                shader = deps[shader_id]
                audit_path = Path(material_audits[mid])
                audit = NS.read_json(audit_path)
                native_path, serialized_keywords = NS.validate_audit_identity(shader, material, mid, audit)
                identity = (str(source.resolve()), str(native_path.resolve()), serialized_keywords)
                if mid in materials:
                    if materials[mid]["identity"] != identity:
                        raise ValueError("Conflicting source identity for material " + mid)
                    continue
                passes = []
                source_disabled = set(material.get("m_DisabledShaderPasses") or [])
                for source_pass in audit["passes"]:
                    pi = source_pass["passIndex"]
                    inactive = source_pass["passName"] in source_disabled or source_pass["lightMode"] in source_disabled
                    programs = NS.inspect_program_candidates(audit, pi, serialized_keywords,
                                                              verify_bytes=not inactive)
                    passes.append({"pass_index": pi, "name": source_pass["passName"],
                                   "disabled": inactive, **programs,
                                   "native_state": source_pass["nativeRenderState"],
                                   "resolved_state": source_pass["resolvedRenderState"]})
                materials[mid] = {"identity": identity, "source_material": str(source), "source_shader": str(native_path),
                                  "audit": str(audit_path), "serialized_material_keywords": serialized_keywords,
                                  "enabled_pass_mask": material.get("m_EnabledPassMask"), "passes": passes}
    if set(material_audits) != set(materials):
        raise ValueError("Program inventory audits must exactly match visible source materials")
    return {"scope": "source_program_inventory", "renderer_scope": "existing_particle_renderers_only",
            "render_preflight": "inspection_only",
            "visible_renderers": visible, "disabled_renderers": disabled,
            "materials": {mid: {key: value for key, value in item.items() if key != "identity"}
                          for mid, item in materials.items()}, "runtime_selection": "unverified"}


def preflight(fx_path, *, assets=None, revision="", preview_node=None, deps_path=None, native_selections=None,
              particle_equivalence=None, ue_equivalent=None, project_materials=None, project_geometry=None,
              project_motion=None, project_mesh_alignments=None, project_gradient=None, project_lights=None,
              component_material_plans=None, project_component_mesh=None, component_mesh_sources=None, project_camera=None,
              projected_material_plans=None, projected_material_errors=None, project_activation=None, project_generated_trails=None, project_particle_trails=None):
    if project_materials is not None:
        if any(v is not None for v in (preview_node, native_selections, ue_equivalent, particle_equivalence)):
            raise ValueError("ProjectConfigured cannot mix preview, smoke environment or particle overrides")
        if not isinstance(project_materials, dict) or not project_materials and not component_material_plans:
            raise ValueError("ProjectConfigured requires explicit material program selections")
    elif any(value is not None for value in (project_geometry, project_motion, project_mesh_alignments, project_gradient,
                                           project_lights, component_material_plans, project_component_mesh, component_mesh_sources, project_camera,
                                           projected_material_plans, projected_material_errors, project_activation, project_generated_trails, project_particle_trails)):
        raise ValueError("Project geometry/motion/alignment require explicit ProjectConfigured materials")
    project_geometry = PR.geometry_policy(project_geometry)
    project_motion = FN.project_motion_policy(project_motion)
    project_gradient = FN.project_gradient_policy(project_gradient)
    project_lights = FN.project_light_policy(project_lights)
    project_component_mesh = FN.component_mesh_policy(project_component_mesh)
    component_material_plans = {} if component_material_plans is None else component_material_plans
    projected_material_plans = {} if projected_material_plans is None else projected_material_plans
    projected_material_errors = {} if projected_material_errors is None else projected_material_errors
    if (not isinstance(projected_material_plans, dict) or not isinstance(projected_material_errors, dict)
            or set(projected_material_plans) & set(projected_material_errors)):
        raise ValueError("投影／Prop需要按准确原节点区分完整材质计划和真实失败")
    if projected_material_plans:
        from projected_fx_material_plan import validate_plan
        for plan in projected_material_plans.values():
            validate_plan(plan)
    if not isinstance(component_material_plans, dict):
        raise ValueError("Component materials require exact source MID plans")
    if component_material_plans:
        import nap_avatar_simple_material_plan as MP
        for pid, plan in component_material_plans.items():
            MP.validate_plan(plan)
            if plan["source_identity"]["material_pid"] != pid:
                raise ValueError("Component material plan key differs from actual source MID")
    if project_mesh_alignments is not None:
        if not isinstance(project_mesh_alignments, dict) or any(not isinstance(path, str) or not path for path in project_mesh_alignments):
            raise ValueError("Mesh alignment choices require exact source node paths")
        project_mesh_alignments = {path: PR.mesh_alignment_policy(choice) for path, choice in project_mesh_alignments.items()}
        if any(choice is None for choice in project_mesh_alignments.values()):
            raise ValueError("Unselected Mesh choices must be omitted; no implicit alignment")
    environment_data = None
    if ue_equivalent is not None:
        import zzz_fx_ue_equivalent as UE
        if native_selections is not None or preview_node is not None:
            raise ValueError("UE equivalent production cannot consume a preview selection or subtree")
        environment_data = UE.configuration(ue_equivalent)
        if particle_equivalence is not None and particle_equivalence != environment_data["particle_equivalence"]:
            raise ValueError("UE smoke particle tunables differ from the explicit environment configuration")
        particle_equivalence = environment_data["particle_equivalence"]
        revision = revision or environment_data["revision"]
    policy = FN.PM.equivalence_policy(particle_equivalence)
    if native_selections is not None and (not isinstance(native_selections, dict) or preview_node is None):
        raise ValueError("Explicit native candidate selections are restricted to a source subtree preview")
    fx = read_json(fx_path)
    deps = read_json(dependency_path(fx_path, fx, deps_path))
    assets = assets if assets is not None else read_json(Path(fx_path).with_name("ue_assets.json"))
    root = fx["root"]
    rows = list(walk(root, project_active=source_activation_paths(fx, project_activation)))
    trail_nodes = {}
    if project_particle_trails is not None:
        if project_particle_trails.get("schema") != "GGYGO.ProjectParticleTrails/v1":
            raise ValueError("逐粒子拖尾缺明确项目配置")
        trail_nodes = {r["node"]:r for r in project_particle_trails["source_nodes"]}
        active_trails = {"/".join(n["name"] for n in path) or "$root" for node,path,active in rows
                         if active and ((node.get("particle") or {}).get("system",{}).get("TrailModule") or {}).get("enabled")}
        if len(trail_nodes) != len(project_particle_trails["source_nodes"]) or set(trail_nodes) != active_trails:
            raise ValueError("逐粒子拖尾必须逐项覆盖准确活动源模块")
    generated_nodes = {}
    if project_generated_trails is not None:
        FN.generated_ribbon_policy(project_generated_trails)
        generated_nodes = {row["node"]: row for row in project_generated_trails["source_nodes"]}
        eligible = {"/".join(n["name"] for n in path) or "$root" for node, path, active in rows
                    if active and node.get("mesh", {}).get("enabled")
                    and node["mesh"]["mesh"] == {"m_FileID": 0, "m_PathID": 0}}
        if (len(generated_nodes) != len(project_generated_trails["source_nodes"])
                or set(generated_nodes) != eligible):
            raise ValueError("UE生成器必须完整匹配本根全部准确enabled Mesh0节点")
    source_paths = {"/".join(n["name"] for n in path) or "$root" for node, path, active in rows
                    if active and ((node.get("particle") or {}).get("renderer") or {}).get("m_Enabled")}
    if (set(projected_material_plans) | set(projected_material_errors)) - source_paths:
        # 明确源节点准入，不把旧计划套到同名材质的另一粒子系统。
        raise ValueError("投影／Prop计划包含非活动原粒子节点")
    frame_paths = {"/".join(n["name"] for n in path) or "$root" for node, path, active in rows
                   if active and ((node.get("particle") or {}).get("renderer") or {}).get("m_Enabled")
                   and ((node.get("particle") or {}).get("renderer") or {}).get("m_RenderMode") == 4
                   and ((node.get("particle") or {}).get("renderer") or {}).get("m_RenderAlignment") in (0, 4)}
    if project_mesh_alignments is not None and set(project_mesh_alignments) - frame_paths:
        raise ValueError("Mesh alignment choice requires an exact active View/Velocity Mesh node")
    if preview_node is not None:
        selected = [row for row in rows if "/".join(n["name"] for n in row[1]) == preview_node]
        if not preview_node or len(selected) != 1 or not selected[0][2]:
            raise ValueError("Preview requires one exact active source subtree: " + str(preview_node))
        prefix = selected[0][1]
        rows = [row for row in rows if row[1][:len(prefix)] == prefix]
    clip = None
    blocked, specs, materials, controls, mesh_contracts = [], [], {}, [], []
    used_component_materials = {}
    used_projected_materials = {}
    spec_source_transforms = []
    # Legacy extraction did not preserve all renderer component types. Read the
    # original index, or require the new description's explicit inventory.
    inventory = {}
    if fx.get("schemaVersion", 1) == 2:
        for node, path, _ in rows:
            if not node.get("components") or not node.get("componentListProof"):
                blocked.append({"node": "/".join(n["name"] for n in path) or "$root",
                                "reason": "Version 2 requires its explicit source component inventory/proof"})
    elif "block" in fx:
        index = read_json(RAW_ROOT / str(fx["block"]) / "fx_index.json")
        roots = [r for r in index["roots"] if r["transform"] == root.get("transform")]
        if len(roots) != 1:
            blocked.append({"node": "$root", "reason": "Source component inventory is ambiguous/missing"})
        else:
            for source, _, _ in walk(roots[0]):
                inventory[source["transform"]] = {c["type"] for c in source["components"]}
    animation = root.get("animation")
    animation_ready = True
    if animation:
        try:
            if not animation["playAutomatically"]:
                raise ValueError("Animation requires a source runtime playback binding")
            pid = animation["default"]["m_PathID"]
            if not pid or pid not in [p["m_PathID"] for p in animation["clips"]]:
                raise ValueError("Default AnimationClip is missing from clip list")
            clip = UA.load(dependency_file(deps, pid, ".anim"))
            if animation["wrapMode"] not in (0, 1) or clip["wrap"] not in (0, 1):
                raise ValueError("Animation wrap behavior is not implemented")
            if clip["float"]:
                raise ValueError("Animation runtime property curves are not implemented")
        except (ValueError, KeyError, OSError) as error:
            animation_ready = False
            blocked.append({"node": "$root/Animation", "reason": str(error)})
    for node, path, active in rows:
        if not active:
            continue
        label = "/".join(n["name"] for n in path) or "$root"
        types = {c["type"] for c in node.get("components", [])} or inventory.get(
            node.get("transform"), set(node.get("component_types", [])))
        if not types:
            blocked.append({"node": label, "reason": "Source renderer component inventory is missing"})
        unknown = types & UNSUPPORTED_RENDERERS
        if unknown:
            blocked.append({"node": label, "reason": "Source renderer not implemented: " + ", ".join(sorted(unknown))})
        controls.extend({"node": label, "script": s["script"],
                         "source_payload_bytes": len(s["payload_hex"]) // 2}
                        for s in node.get("scripts", []) if s["enabled"])
        if path and node.get("animation"):
            blocked.append({"node": label, "reason": "Nested Animation playback is not implemented"})
        if node.get("light", {}).get("m_Enabled"):
            try:
                if project_materials is None or project_lights is None:
                    raise FN.SpecError("组件 Light 需要显式原生 Emitter Light 项目政策")
                if animation_ready:
                    spec = FN.component_light_spec(node, list(path), clip,
                        {"identity": component_identity(node, "Light"), "light": node["light"]}, project_lights)
                    NiagaraBuilder.validate_spec(spec)
                    specs.append(spec)
                    spec_source_transforms.append(node["transform"])
            except (ValueError, FN.SpecError, KeyError, OSError) as error:
                blocked.append({"node": label, "reason": "%s: %s" % (type(error).__name__, error)})
        mesh = node.get("mesh")
        if label in generated_nodes:
            try:
                if not animation_ready or project_materials is None:
                    raise FN.SpecError("UE生成拖尾缺准确动画/ProjectConfigured材质输入")
                pointers = mesh["materials"]
                if len(pointers) != 1 or not pointers[0]["m_PathID"]:
                    raise FN.SpecError("UE生成拖尾须消费准确单槽源材质")
                pid = str(pointers[0]["m_PathID"])
                if pid not in project_materials:
                    raise FM.PlanError("UE生成拖尾缺本MID真VP/FP选择: "+pid)
                generated_material = material_plan(deps, pid, FN.generated_ribbon_context(), assets,
                    project_materials[pid], output_contract="color", project_camera=project_camera)
                if revision:
                    generated_material["master"] = version_name(generated_material["master"], revision)
                target = "%s/%s" % (MI_DIR, mi_name(generated_material, revision))
                materials[target] = generated_material
                spec = FN.generated_ribbon_spec(node, list(path), clip, project_generated_trails, generated_material, target)
                NiagaraBuilder.validate_spec(spec)
                specs.append(spec)
                spec_source_transforms.append(node["transform"])
            except (FM.PlanError, FM.T.TranslateError, ValueError, FN.SpecError, KeyError, OSError) as error:
                blocked.append({"node": label, "reason": "%s: %s" % (type(error).__name__, error)})
        elif mesh and mesh["enabled"]:
            try:
                contract = MR.inspect(node, list(path), deps, clip)
                mesh_contracts.append({"node": label, **contract})
                if project_component_mesh is None:
                    blocked.extend({"node": label, "reason": "MeshRenderer requires " + requirement}
                                   for requirement in contract["required_consumers"])
                elif animation_ready:
                    source_materials = {}
                    for slot in contract["materials"]:
                        pid = slot["pid"]
                        if pid in component_material_plans:
                            continue
                        if project_materials is None or pid not in project_materials:
                            raise FM.PlanError("静态Mesh缺准确 ProjectConfigured 材质程序：" + pid)
                        context = {"kind": "mesh", "mesh": True, "uv_count": uv_count(deps, contract["mesh"]["pid"]),
                                   "component_age_binding": project_component_mesh["material_age"]}
                        if project_component_mesh.get("native_source_mode") == "SingleParticle":
                            context["component_coverage_binding"] = {"DP0.y": "ParticleLifetimeFade"}
                        plan = material_plan(deps, pid, context, assets, project_materials[pid],
                                             output_contract=project_materials[pid].get("output_contract", "color"),
                                             project_camera=project_camera)
                        if revision:
                            plan["master"] = version_name(plan["master"], revision)
                        target = "%s/%s" % (MI_DIR, mi_name(plan, revision))
                        materials[target] = plan
                        source_materials[pid] = {"plan": plan, "target": target}
                    spec = FN.component_mesh_spec(node, list(path), clip, contract, assets,
                        component_material_plans, project_component_mesh, (component_mesh_sources or {}).get(contract["mesh"]["pid"]),
                        source_materials=source_materials)
                    NiagaraBuilder.validate_spec(spec)
                    specs.append(spec)
                    spec_source_transforms.append(node["transform"])
                    used_component_materials.update({slot["pid"]: component_material_plans[slot["pid"]]
                                                     for slot in contract["materials"] if slot["pid"] in component_material_plans})
            except (FM.PlanError, FM.T.TranslateError, ValueError, FN.SpecError, KeyError, OSError) as error:
                blocked.append({"node": label, "reason": "%s: %s" % (type(error).__name__, error)})
        elif "MeshRenderer" in types and not mesh:
            blocked.append({"node": label, "reason": "MeshRenderer source description is missing"})
        if "particle" not in node:
            continue
        particle_trail = None
        if label in trail_nodes:
            try:
                particle_trail = FN.particle_trail_contract(node,list(path),project_particle_trails)
                node = FN.particle_trail_primary_node(node,particle_trail)
            except (ValueError,FN.SpecError,KeyError) as error:
                blocked.append({"node":label,"reason":type(error).__name__+": "+str(error)})
                continue
        renderer = node["particle"]["renderer"]
        lights = node["particle"]["system"].get("LightsModule") or {}
        bound_light = lights.get("enabled") and lights.get("light", {}).get("m_PathID")
        if renderer is None:
            if bound_light:
                blocked.append({"node": label, "reason": "Light-only source needs its renderer-independent particle colour contract"})
            continue
        mids = [str(m["m_PathID"]) for m in renderer["m_Materials"] if m["m_PathID"]]
        if not renderer["m_Enabled"] and not bound_light:
            continue
        try:
            source_light = particle_light_source(node, rows)
            if not mids or not renderer["m_Enabled"]:
                if source_light is None:
                    continue
                if project_materials is None or project_lights is None:
                    raise FN.SpecError("Light-only ParticleSystem requires explicit ProjectConfigured native lighting")
                if not animation_ready:
                    continue  # 原 Clip 未就绪，不能制作静态灯冒充动画节点。
                light_plan = {"configuration_mode": "ProjectConfigured", "output_contract": "light", "dyn_params": {}}
                spec = FN.emitter_spec(node, list(path), clip, assets, {}, light_plan,
                    project_geometry=project_geometry, project_motion=project_motion, project_gradient=project_gradient,
                    project_lights=project_lights, source_light=source_light, light_only=True)
                NiagaraBuilder.validate_spec(spec)
                if not path:
                    spec["name"], spec["path"] = "PrefabRoot", "$root"
                specs.append(spec)
                spec_source_transforms.append(node["transform"])
                continue
            if len(mids) != 1:
                raise FN.SpecError("Multiple renderer materials are not implemented")
            mpid = mids[0]
            if label in projected_material_errors:
                raise FM.PlanError(projected_material_errors[label])
            source_plan = projected_material_plans.get(label)
            if source_plan is not None:
                if source_plan["source_identity"]["material_pid"] != mpid:
                    raise FM.PlanError("投影／Prop计划改变原节点材质身份")
                roles = source_plan["roles"]
                decal = roles == ["projected_decal"]
                prop = roles == ["prop_surface", "prop_forward_color"]
                if not decal and not prop:
                    raise FM.PlanError("未实现的原生材质角色")
                context = {"configuration_mode": "ProjectConfigured", "output_contract": "projected_decal" if decal else "native_prop_roles",
                           "dyn_params": {}}
                if prop:
                    affine = FN.mesh_affine_adapter(node, list(path), clip,
                        project_alignment=(project_mesh_alignments or {}).get(label))
                    if affine is not None:
                        raise FN.SpecError("Prop NativeTRSOnly不能放行真实FullAffine WPO")
                    context["mesh_uv"] = source_plan["native_renderer_contract"]["mesh_uv"]["adapter"]
                    transport = source_plan["native_renderer_contract"]
                    mask = transport["system_age_dynamic_parameter_mask"]
                    context["dynamic_parameter_components"] = mask
                    if mask:
                        context["dyn_params"] = {transport["system_age_transport"]["slot"]: "OriginalSystemAge"}
                material_path = source_plan["bindings"][mpid][roles[0]]
                if not animation_ready:
                    continue
                spec = FN.emitter_spec(node, list(path), clip, assets, {mpid: material_path}, context,
                    project_geometry=project_geometry, project_motion=project_motion,
                    project_mesh_alignment=(project_mesh_alignments or {}).get(label), project_gradient=project_gradient,
                    project_lights=project_lights, source_light=source_light,
                    projected_plan=source_plan if decal else None, prop_plan=source_plan if prop else None)
                NiagaraBuilder.validate_spec(spec)
                if not path:
                    spec["name"], spec["path"] = "PrefabRoot", "$root"
                specs.append(spec)
                spec_source_transforms.append(node["transform"])
                used_projected_materials[label] = source_plan
                continue
            if project_materials is not None:
                selection = project_materials.get(mpid)
                if not isinstance(selection, dict) or selection.get("purpose") != "project_configured_source_particles" \
                        or selection.get("configuration_mode") != "ProjectConfigured":
                    raise FM.PlanError("Missing explicit ProjectConfigured program selection for material " + mpid)
            mesh_pid = str(renderer["m_Mesh"]["m_PathID"])
            context = {"kind": "particle", "streams": renderer["m_VertexStreams"],
                       "custom_streams": renderer["m_UseCustomVertexStreams"],
                       "mesh": renderer["m_RenderMode"] == 4,
                       "sprite_subuv": renderer["m_RenderMode"] in (0, 1, 2) and
                                       bool(node["particle"]["system"].get("UVModule", {}).get("enabled")),
                       "sprite_uv_tiles": tuple(node["particle"]["system"].get("UVModule", {}).get(k)
                                                for k in ("tilesX", "tilesY")),
                       "sprite_uv_animation_type": node["particle"]["system"].get("UVModule", {}).get("animationType", 0),
                       "mesh_uv": FN.PU.mesh_uv_adapter(node["particle"]["system"].get("UVModule"), label)
                           if renderer["m_RenderMode"] == 4 and node["particle"]["system"].get("UVModule") is not None else None,
                       "sprite_normal_direction": renderer.get("m_NormalDirection"),
                       "sprite_rotation_2d": not node["particle"]["system"].get("InitialModule", {}).get("rotation3D", False)
                            and not node["particle"]["system"].get("RotationModule", {}).get("separateAxes", False),
                       "sprite_static_quad_uv": (environment_data is not None or project_materials is not None)
                           and renderer["m_RenderMode"] in (0, 1, 2)
                           and node["particle"]["system"].get("UVModule", {}).get("enabled") is False,
                       "sprite_extra_quad_uv": (environment_data is not None or project_materials is not None)
                           and renderer["m_RenderMode"] in (0, 1, 2),
                       "uv_count": uv_count(deps, mesh_pid) if renderer["m_RenderMode"] == 4 else 1}
            if renderer["m_RenderMode"] == 4 and animation_ready:
                if deps[str(mesh_pid)].get("vertex_texture_mesh") is not None:
                    context["vertex_texture_mesh"] = deps[str(mesh_pid)]["vertex_texture_mesh"]
                context["mesh_affine"] = FN.mesh_affine_adapter(node, list(path), clip,
                    project_alignment=(project_mesh_alignments or {}).get(label))
            if renderer["m_RenderMode"] in (0, 1, 2) and (policy is not None or project_geometry is not None):
                context["viewport_clamp"] = PR.viewport_plan(renderer, policy, label,
                    project_geometry=project_geometry,
                    signed_field=project_materials is not None and selection.get("output_contract") == "distortion_field_pair")
            plan = material_plan(deps, mpid, context, assets,
                                 environment_data["materials"].get(mpid) if environment_data is not None else
                                  project_materials[mpid] if project_materials is not None else
                                  native_selections.get(mpid) if native_selections is not None else None,
                                  output_contract=project_materials[mpid].get("output_contract", "color")
                                  if project_materials is not None else "color", project_camera=project_camera)
            if revision:
                plan["master"] = version_name(plan["master"], revision)
            mi = "%s/%s" % (MI_DIR, mi_name(plan, revision))
            materials[mi] = plan
            if not animation_ready:
                continue  # 已生成材质可保留；缺 Clip 不生成静态姿态冒充原节点动画。
            spec = FN.emitter_spec(node, list(path), clip, assets, {mpid: mi}, plan, policy,
                                   project_geometry=project_geometry, project_motion=project_motion,
                                   project_mesh_alignment=(project_mesh_alignments or {}).get(label), project_gradient=project_gradient,
                                   project_lights=project_lights, source_light=source_light, particle_trail=particle_trail)
            NiagaraBuilder.validate_spec(spec)
            if not path:
                spec["name"], spec["path"] = "PrefabRoot", "$root"
            specs.append(spec)
            spec_source_transforms.append(node.get("transform"))
            if particle_trail is not None:
                trail_mid = str(particle_trail["source_materials"][1]["m_PathID"])
                if project_materials is None or trail_mid not in project_materials:
                    raise FM.PlanError("逐粒子拖尾slot1缺准确源程序选择")
                trail_context = {**FN.generated_ribbon_context(),
                    "source_trail_length_color": particle_trail["source_trail_length_color"]}
                trail_material = material_plan(deps,trail_mid,trail_context,assets,
                    project_materials[trail_mid],output_contract="color",project_camera=project_camera)
                if revision:
                    trail_material["master"] = version_name(trail_material["master"],revision)
                trail_target = "%s/%s" % (MI_DIR,mi_name(trail_material,revision))
                materials[trail_target] = trail_material
                child = FN.particle_trail_child_spec(spec,particle_trail,trail_material,trail_target)
                NiagaraBuilder.validate_spec(child)
                specs.append(child)
                spec_source_transforms.append(node.get("transform"))
        except (FM.PlanError, FN.SpecError, FM.T.TranslateError, ValueError, KeyError, OSError) as error:
            blocked.append({"node": label, "reason": "%s: %s" % (type(error).__name__, error)})
    if not specs and not blocked:
        blocked.append({"node": "$root", "reason": "Prefab has no implemented visible renderer"})
    names = [s["name"] for s in specs]
    duplicates = {name for name in names if names.count(name) > 1}
    for spec, transform in zip(specs, spec_source_transforms):
        if spec["name"] not in duplicates:
            continue
        text = str(transform)
        if re.fullmatch(r"-?[1-9][0-9]*", text) is None or not -(1 << 63) <= int(text) < (1 << 63):
            blocked.append({"node": spec["path"], "reason": "Colliding emitter name requires exact source Transform Int64"})
            continue
        # Unity 名称／动画路径不改；仅以该源 Transform 身份区分 Niagara 对象名。
        spec["name"] += "_Transform_" + text.replace("-", "N")
    names = [s["name"] for s in specs]
    if len(names) != len(set(names)):
        blocked.append({"node": "$root", "reason": "Node paths collide after Niagara name normalization"})
    ordinary = [spec for spec in specs if spec["renderer"].get("project_scene_order") is not None]
    if ordinary:
        ordering = project_geometry["scene_sort"]
        overrides = ordering["priority_overrides"]
        if set(overrides) - {spec["path"] for spec in ordinary}:
            raise ValueError("Project priority override does not name an actual ordinary renderer")
        ranked = sorted(enumerate(ordinary), key=lambda item: (
            item[1]["renderer"]["project_scene_order"]["source_sorting_order"],
            -item[1]["renderer"]["source_sorting_fudge"], item[0]))
        for priority, (_, spec) in enumerate(ranked):
            spec["renderer"]["sort"] = overrides.get(spec["path"], priority)
            for extra in spec.get("additional_renderers", []):
                if extra.get("prop_role") is not None:
                    extra["sort"] = spec["renderer"]["sort"]
    source_parent_sorts = {s["name"]:s["renderer"]["sort"] for s in specs if s.get("source_particle_trail")}
    source_parents = {s["source_particle_trail"]["source_transform"]:s for s in specs if s.get("source_particle_trail")}
    if len(source_parents) != len(source_parent_sorts):
        raise ValueError("逐粒子拖尾源Transform与父Emitter不是一对一")
    for parent in source_parents.values():
        parent["runtime_failure"]["policy"]["parent_emitter"] = parent["name"]
    for child in specs:
        if child.get("particle_trail_child"):
            source_transform = child["particle_trail_child"]["contract"]["source_transform"]
            parent = source_parents.get(source_transform)
            if parent is None or parent["source_particle_trail"] != child["particle_trail_child"]["contract"]:
                raise ValueError("逐粒子拖尾缺同源完整合同的准确父Emitter")
            parent_name = parent["name"]
            child["particle_trail_child"]["parent_emitter"] = parent_name
            child["runtime_failure"]["policy"]["parent_emitter"] = parent_name
            child["renderer"]["sort"] = source_parent_sorts[parent_name]
    report = {"name": fx["name"], "blocked": blocked, "renderers": [s["path"] for s in specs if not s.get("particle_trail_child")],
              "runtime_controls": controls, "action_integration": "unverified", "visual_comparison": "unverified"}
    report["component_material_plans"] = used_component_materials
    report["projected_material_plans"] = used_projected_materials
    report["material_sources"] = {}
    for spec in specs:
        renderer = spec["renderer"]
        if renderer.get("mesh_uv") is not None:
            report["material_sources"].setdefault(renderer["material"], []).append({
                "prefab": fx["name"], "source_node": renderer["mesh_uv"]["source_node"]})
    if project_materials is not None:
        report.update(configuration_mode="ProjectConfigured", source_shader_selection="ProjectConfigured_not_source_runtime",
                      project_geometry=project_geometry, project_motion=project_motion, project_mesh_alignments=project_mesh_alignments,
                      project_gradient=project_gradient, project_lights=project_lights,
                      project_component_mesh=project_component_mesh)
    if mesh_contracts:
        report["mesh_renderer_contracts"] = mesh_contracts
    if policy is not None:
        report["particle_equivalence"] = {**policy, "precision": "explicit_UE_equivalent_not_native_identity"}
    if preview_node is not None:
        report.update({"scope": "source_subtree_preview", "source_node": preview_node,
                       "source_prefab_restore": "incomplete", "action_integration": "outside preview scope"})
    if blocked:
        # 保已能完整生成的作者输入；失败对象仍不返回可执行资产计划。
        report.update(prepared_materials=materials, prepared_specs=specs)
        raise PreflightError(report)
    if native_selections is not None:
        used = {p["source_selection"]["material_pid"] for p in materials.values() if "source_selection" in p}
        if set(native_selections) != used:
            raise ValueError("Native selections must exactly match selected source materials")
        report["source_shader_selection"] = "explicit_preview_candidates_runtime_unverified"
    if environment_data is not None:
        UE.validate_prefab(fx_path, environment_data, report["renderers"])
        report.update({"scope": "complete_source_prefab_UE_equivalent", "source_prefab_restore": "complete_structure_UE_environment",
                       "source_shader_selection": "explicit_UE_equivalent_not_source_runtime",
                       "ue_environment": {"name": UE.MODE, "configuration": str(Path(ue_equivalent).resolve()),
                                          "calibration": environment_data["calibration"]}})
    base = "NS_" + fx["name"] if preview_node is None else "NS_PREVIEW_" + fx["name"] + "_" + preview_node
    if environment_data is not None:
        base = "NS_UEEquivalent_" + fx["name"]
    system = "%s/%s" % (SYSTEM_DIR, version_name(base, {"specs": specs, "revision": revision}))
    targets = sorted({system, *materials, *(MASTER_DIR + "/" + p["master"] for p in materials.values())})
    targets = sorted(set(targets) | {target for plan in used_component_materials.values() for target in plan["targets"]})
    targets = sorted(set(targets) | {target for plan in used_projected_materials.values() for target in plan["targets"]})
    return {**report, "system": system, "targets": targets, "specs": specs, "materials": materials,
            "render_preflight": "complete"}


def compile_unit_plans(plan):
    """读取完整组合的实际编译包；原单项计划仍保持原资产身份。"""
    units = plan.get("compile_units", [plan])
    if not isinstance(units,list) or not units:
        raise ValueError("动作缺实际独立编译单元")
    if "compile_units" in plan:
        if ([spec for unit in units for spec in unit["specs"]] != plan["specs"]
                or set().union(*(set(unit["targets"]) for unit in units)) != set(plan["targets"])
                or len({unit["system"] for unit in units}) != len(units)
                or any(not unit["specs"] or len(unit["specs"]) > NiagaraBuilder.MAX_SYSTEM_EMITTERS for unit in units)):
            raise ValueError("独立编译单元改变完整层顺序／原式、准确目标或编译界限")
    return units


def independent_system_plan(plan):
    """从已核原聚合来源派生受限独立包；依赖区间同包，保原层次序和随机调用。"""
    specs = plan["specs"]
    limit = NiagaraBuilder.MAX_SYSTEM_EMITTERS
    names = {spec["name"]:index for index,spec in enumerate(specs)}
    if not specs or len(names) != len(specs):
        raise ValueError("独立编译缺完整唯一Emitter来源")
    if len(specs) <= limit:
        return {**plan, "compile_units":[plan]}
    ends = list(range(len(specs)))
    for index,spec in enumerate(specs):
        references = []
        child = spec.get("particle_trail_child")
        if child:
            references.append(child["parent_emitter"])
        failure = spec.get("runtime_failure", {})
        if failure.get("kind") == "SourceParticleTrail":
            references.append(failure["policy"]["parent_emitter"])
        for stage in ("emitter_spawn", "emitter_update", "spawn", "update"):
            for _,_,expression in spec.get(stage, []):
                references.extend(name for name in re.findall(r"\b([A-Za-z_][A-Za-z_0-9]*)\.",expression) if name in names)
        for reference in references:
            if reference not in names:
                raise ValueError("跨层依赖不属于原完整组合: "+reference)
            low,high = sorted((index,names[reference]))
            ends[low] = max(ends[low],high)
    # 区间闭包还保留依赖两端之间的原顺序，不为压包而重新排列独立层。
    groups,begin = [],0
    while begin < len(specs):
        end,index = ends[begin],begin
        while index <= end:
            end = max(end,ends[index])
            index += 1
        if end-begin+1 > limit:
            raise ValueError("真实依赖闭包超过独立System界限，不能拆断: "+repr([s["name"] for s in specs[begin:end+1]]))
        if groups and len(groups[-1])+end-begin+1 <= limit:
            groups[-1].extend(specs[begin:end+1])
        else:
            groups.append(list(specs[begin:end+1]))
        begin = end+1
    units = []
    for index,group in enumerate(groups):
        digest = _batch_recipe_sha(group)[:12]
        system = plan["system"]+"_Unit%02d_" % index+digest
        paths = {(spec["source_prefab"]+"::" if "source_prefab" in spec else "")+spec["path"] for spec in group}
        # 原材质声明及只读依赖保持完整；本包只创建当前规格的 NS，不重做共享材质。
        units.append({**plan, "name":plan["name"]+"_Unit%02d" % index, "system":system,
            "specs":group, "renderers":[path for path in plan["renderers"] if path in paths],
            "targets":sorted((set(plan["targets"])-{plan["system"]}) | {system})})
    composition = {**plan, "source_system":plan["system"], "compile_units":units,
                   "targets":sorted(set().union(*(set(unit["targets"]) for unit in units)))}
    del composition["system"]  # 原父包仅为来源，不能再成为创建或最终合图目标。
    compile_unit_plans(composition)
    return composition


def validate_batch(plans, imports=None):
    """@brief 核定完整真实plans/imports的纯数据合同；不调用MCP、不创建或保存资产。

    @return 供apply直接使用的去重材质、目标及覆盖计数；不代表Native ABI或Shader编译通过。
    """
    plans = [unit for plan in plans for unit in compile_unit_plans(plan)]
    import zzz_fx_ue_equivalent as UE
    UE.validate_batch(plans)
    component_materials = {}
    projected_materials = {}
    for plan in plans:
        if plan.get("render_preflight") != "complete" or plan.get("blocked") or not plan.get("specs"):
            raise ValueError("Cannot apply an incomplete render plan")
        for material in plan["materials"].values():
            Builder.validate_plan(material)
        for material in plan.get("component_material_plans", {}).values():
            from build_nap_avatar_simple_materials import NapAvatarSimpleBuilder
            NapAvatarSimpleBuilder.validate_plan(material)
            key = tuple(item["instance"] for item in material["materials"])
            if key in component_materials and component_materials[key] != material:
                raise ValueError("Same component material target has conflicting source plans")
            component_materials[key] = material
        for material in plan.get("projected_material_plans", {}).values():
            from projected_fx_material_plan import validate_plan
            validate_plan(material)
            key = tuple(item["instance"] for item in material["materials"])
            if key in projected_materials and projected_materials[key] != material:
                raise ValueError("同一Native投影／Prop材质目标存在不同来源")
            projected_materials[key] = material
        for spec in plan["specs"]:
            try:
                NiagaraBuilder.validate_spec(spec)
                renderer = spec["renderer"]
                depth_material = plan["materials"].get(renderer.get("material"), {})
                if depth_material.get("native_depth_velocity") != renderer.get("native_depth_velocity"):
                    raise ValueError("额外Depth/Velocity材质与真实Primary Renderer合同不一致")
                if renderer["kind"] == "projected_decal" or renderer.get("native_prop_contract") is not None:
                    material_path = spec["path"]
                    if "source_members" in plan:
                        members = [member for member in plan["source_members"]
                                   if member["prefab"] == spec.get("source_prefab")]
                        if len(members) != 1 or not spec["name"].startswith(members[0]["emitter_prefix"]):
                            raise ValueError("组合投影／Prop未绑定唯一原成员及发射器前缀")
                        # 聚合计划保留原节点路径，由明确成员身份限定材质索引。
                        material_path = spec["source_prefab"] + "::" + material_path
                    material = plan.get("projected_material_plans", {}).get(material_path)
                    if material is None:
                        raise ValueError("Native投影／Prop缺当前原节点材质计划")
                    pid = material["source_identity"]["material_pid"]
                    bindings = material["bindings"][pid]
                    if renderer["material"] != bindings[material["roles"][0]]:
                        raise ValueError("Native主role改变原材质绑定")
                    contract = renderer.get("contract") if renderer["kind"] == "projected_decal" else renderer["native_prop_contract"]
                    if contract != material["native_renderer_contract"]:
                        raise ValueError("Native材质／Renderer数据合同不相等")
                    if renderer.get("native_prop_contract") is not None:
                        forward = [row for row in spec.get("additional_renderers", []) if row.get("prop_role") == "prop_forward_color"]
                        if len(forward) != 1 or forward[0]["material"] != bindings["prop_forward_color"]:
                            raise ValueError("Prop第二role未消费自己的真Forward材质")
                    continue
                if renderer["kind"] in ("light", "component_mesh"):
                    continue  # 已由 validate_spec 核 Light-only 原生合同，不消费颜色材质。
                material = plan["materials"].get(renderer["material"])
                if renderer["kind"] in ("generated_ribbon","particle_trail_ribbon"):
                    if (material is None or material.get("renderer_kind") != "generated_ribbon"
                            or material.get("generated_ribbon") != renderer["generated_ribbon"]
                            or material.get("dynamic_parameter_components") != 0xFFFF):
                        raise ValueError("生成拖尾完整22输入与准确材质计划未配对")
                field = renderer.get("field_renderer")
                is_field = material is not None and material.get("output_contract") == "distortion_field_pair"
                if is_field != (field is not None) or is_field and field["properties"]["FieldStreams"]["RequiredDynamicParameterComponents"] != material.get("dynamic_parameter_components"):
                    raise ValueError("Field material/renderer DP component contract mismatch before editor mutation")
                if renderer["kind"] == "mesh":
                    affine = material.get("mesh_affine") if material is not None else None
                    vertex_stage = (material or {}).get("vertex_stage")
                    expected_radius = (material or {}).get("additional_wpo_bounds_radius_cm")
                    if renderer.get("vertex_deformation") != (vertex_stage or {}).get("deformation") \
                            or renderer.get("additional_wpo_bounds_radius_cm") != expected_radius:
                        raise ValueError("原VS形变／真实WPO半径未接到同一Mesh Renderer")
                    material_uv, renderer_uv = (material or {}).get("mesh_uv"), renderer.get("mesh_uv")
                    material_contract = PU.mesh_uv_material_contract(material_uv)
                    renderer_contract = PU.mesh_uv_material_contract(renderer_uv)
                    if material_contract != renderer_contract:
                        raise ValueError("Mesh UV材质／原生Frame运输不一致: material=%r renderer=%r" % (
                            material_contract, renderer_contract))
                    if material_uv != renderer_uv and {"prefab": spec.get("source_prefab", plan["name"]),
                            "source_node": renderer_uv["source_node"]} not in plan.get("material_sources", {}).get(renderer["material"], []):
                        raise ValueError("共享Mesh UV材质缺当前原节点的完整组合来源")
                    if FN.mesh_affine_transport(affine) != renderer.get("mesh_affine"):
                        raise ValueError("Mesh material/native geometry transport contract mismatch")
                    if affine is not None and affine.get("project_alignment") is not None \
                            and renderer.get("dynamic_parameter_components") != material.get("dynamic_parameter_components"):
                        raise ValueError("Mesh Euler material/native component masks differ")
                if renderer["kind"] == "sprite":
                    material = plan["materials"].get(renderer["material"])
                    viewport = material.get("viewport_clamp") if material is not None else None
                    if viewport is None or PR.viewport_signature(viewport) != renderer.get("viewport_adapter_signature"):
                        raise ValueError("%s sprite material viewport adapter contract mismatch before editor mutation" % spec["name"])
                    material_facing = (viewport.get("facing_adapter") or {}).get("kind")
                    if material_facing != renderer.get("material_facing"):
                        raise ValueError("Ordinary Facing material/native renderer contract mismatch before editor mutation")
            except Exception as error:
                raise ValueError("FX.Batch plan=%s prefab=%s node=%s renderer=%s: %s: %s" % (
                    plan["name"], spec.get("source_prefab", plan["name"]), spec["path"],
                    spec["name"], type(error).__name__, error)) from error
    if (component_materials or projected_materials) and imports is None:
        raise ValueError("Source component materials require exact prepared imports")
    targets = {path for plan in plans for path in plan["targets"]}
    if imports is not None:
        targets.update(imports["targets"])
    return {"component_materials": list(component_materials.values()),
            "projected_materials": list(projected_materials.values()), "targets": sorted(targets),
            "plan_count": len(plans), "emitter_count": sum(len(plan["specs"]) for plan in plans),
            "material_occurrence_count": sum(len(plan["materials"]) for plan in plans)}


def apply_batch(plans, mcp, approved_targets, imports=None, *, unreal=None,
                import_resume=None, import_resume_receipt=None):
    """既有同步入口；与宿主续作消费同一条制作流程。"""
    steps = iter_apply_batch(plans, mcp, approved_targets, imports, unreal=unreal,
        import_resume=import_resume, import_resume_receipt=import_resume_receipt)
    while True:
        try:
            next(steps)
        except StopIteration as completed:
            return completed.value


def iter_apply_batch(plans, mcp, approved_targets, imports=None, *, unreal=None,
                     import_resume=None, import_resume_receipt=None):
    """在工具已返栈的业务边界让出原帧；原宿主推进，完整 reports 仅正常结束时返回。"""
    plans = [unit for plan in plans for unit in compile_unit_plans(plan)]
    validated = validate_batch(plans, imports=imports)
    if import_resume is None and import_resume_receipt is not None:
        raise ValueError("无显式FX复用输入时不能提供复用回执")
    resume_validation = None
    reused = set()
    if import_resume is not None:
        if imports is None or not isinstance(import_resume_receipt, dict) or import_resume_receipt:
            raise ValueError("显式FX复用需要完整imports和本次全新空回执")
        reused = set(imports["targets"])
        if reused & set(approved_targets):
            raise ValueError("FX复用资产不能同时出现在可写批准集合")
        import_resume_receipt.update(schema="GGYGO.FX.ReadOnlyImportsReceipt/v1",
            source_receipt=dict(import_resume), expected_packages=sorted(reused), source_verified=False,
            verified_packages=[], identity_readbacks={}, property_readbacks={}, geometry_readbacks={},
            current_package=None, stage="SourceValidation", complete=False)
        from zzz_fx_import_assets import validate_import_resume
        resume_validation = validate_import_resume(imports, import_resume)
        import_resume_receipt.update(source_verified=True, stage="NativePreflight")
    component_materials = validated["component_materials"]
    projected_materials = validated["projected_materials"]
    if any(material.get("output_contract") == "distortion_field_pair"
           for plan in plans for material in plan["materials"].values()):
        Builder.require_dual_field_class(mcp, unreal=unreal)
        NiagaraBuilder.require_field_renderer_classes(mcp, [spec for plan in plans for spec in plan["specs"]])
    NiagaraBuilder.require_runtime_failure_support(mcp, [spec for plan in plans for spec in plan["specs"]])
    NiagaraBuilder.require_component_mesh_support(mcp, [spec for plan in plans for spec in plan["specs"]])
    if (component_materials or projected_materials) and (unreal is None or imports is None):
        raise ValueError("Source component materials require the explicit same standard Editor native host and exact imports")
    if resume_validation is not None:
        import_resume_receipt["stage"] = "CreateTargetPreflight"
    session = AssetSession(mcp, set(validated["targets"]) - reused, approved_targets)
    NiagaraBuilder(session, unreal=unreal).require_projected_support([spec for plan in plans for spec in plan["specs"]])
    imported_geometry_reports = {}
    if resume_validation is not None:
        from zzz_fx_import_assets import verify_import_resume
        verify_import_resume(imports, mcp, resume_validation, import_resume_receipt,
                             unreal=unreal, geometry_reports=imported_geometry_reports)
    elif imports:
        from zzz_fx_import_assets import apply_imports
        apply_imports(imports, session, unreal=unreal, geometry_reports=imported_geometry_reports)
    geometry_reports = {}
    if component_materials:
        from build_pyrios_ghost_fx import read_geometry
        for plan in plans:
            for spec in plan["specs"]:
                renderer = spec["renderer"]
                if renderer["kind"] != "component_mesh":
                    continue
                source = renderer["source_geometry"]
                item = imports["entries"].get(source["mesh_pid"])
                if item is None or Path(item["source"]).resolve() != Path(source["source_fbx"]["path"]).resolve() \
                        or item["identity"]["source_sha256"] != source["source_fbx"]["sha256"]:
                    raise ValueError("Static Mesh import does not match the exact source-winding input")
                try:
                    if item["path"] in imported_geometry_reports:
                        geometry_reports[(plan["system"], spec["name"])] = imported_geometry_reports[item["path"]]
                    else:
                        geometry_reports[(plan["system"], spec["name"])] = read_geometry(unreal, item, renderer["source_contract"],
                            vertex_color_mode=source["vertex_color_mode"])
                except (ValueError, RuntimeError) as error:
                    raise RuntimeError("FX Mesh '%s/%s' PID=%s Native SourceModel核对失败：%s" % (
                        plan["name"], spec["path"], source["mesh_pid"], error)) from error
    material_options = {"unreal": unreal}
    if resume_validation is not None:
        verified_dependencies = frozenset(import_resume_receipt["verified_packages"])
        if (import_resume_receipt.get("source_verified") is not True
                or import_resume_receipt.get("complete") is not True
                or verified_dependencies != reused
                or len(import_resume_receipt["verified_packages"]) != len(reused)):
            raise ValueError("材质只读依赖必须来自本次完整Native复用核验")
        material_options["verified_readonly_dependencies"] = verified_dependencies
    yield "imports_verified"
    if component_materials:
        from build_nap_avatar_simple_materials import NapAvatarSimpleBuilder
        builder = NapAvatarSimpleBuilder(session, **material_options)
        for material in component_materials:
            builder.build(material)
            paths = [path for spec in material["materials"] for path in (spec["master"], spec["instance"])]
            session.save(paths)
            yield "component_materials_saved:" + paths[-1]
    if projected_materials:
        from build_projected_fx_materials import ProjectedFXMaterialBuilder
        from zzz_fx_material_ue import build_source_mesh_uv
        projected_builder = ProjectedFXMaterialBuilder(session, uv_author=build_source_mesh_uv, **material_options)
        for material in projected_materials:
            projected_builder.build(material)
            paths = [path for spec in material["materials"] for path in (spec["master"], spec["instance"])]
            session.save(paths)
            yield "projected_materials_saved:" + paths[-1]
    material_builder = Builder(session, unreal=unreal)
    reports = []
    for plan in plans:
        for mi, material in plan["materials"].items():
            master = material_builder.build_master(material)
            material_builder.build_instance(material, master, mi.rsplit("/", 1)[1])
            yield "material_instance_saved:" + mi
        state = yield from NiagaraBuilder(session, unreal=unreal).iter_build_system(plan["system"], plan["specs"])
        yield "niagara_system_saved:" + plan["system"]
        reports.append({k: plan[k] for k in ("name", "system", "renderers", "runtime_controls",
                                              "action_integration", "visual_comparison", "scope", "source_node",
                                              "source_prefab_restore", "particle_equivalence", "ue_environment",
                                              "source_shader_selection", "configuration_mode", "project_geometry", "project_motion", "project_gradient", "project_lights") if k in plan})
        reports[-1]["compile"] = state
        reports[-1]["component_mesh_geometry"] = {name: report for (system,name),report in geometry_reports.items() if system == plan["system"]}
        if imported_geometry_reports:
            used_meshes = {spec["renderer"].get("mesh") for spec in plan["specs"]}
            used_meshes.update(draw["mesh"] for spec in plan["specs"]
                if spec["renderer"]["kind"] == "component_mesh" for draw in spec["renderer"]["draws"])
            reports[-1]["import_mesh_tangent_basis"] = {path: report for path,report in imported_geometry_reports.items()
                                                       if path in used_meshes}
    return reports


def _batch_recipe_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _batch_package_references(value, packages):
    if isinstance(value, dict):
        return set().union(set(value) & packages,
            *(_batch_package_references(item, packages) for item in value.values()))
    if isinstance(value, (tuple, list)):
        return set().union(*(_batch_package_references(item, packages) for item in value))
    return {value} if isinstance(value, str) and value in packages else set()


def asset_batch_catalog(plans, imports, *, profile_request):
    """从已绑定的完整组合分配实际独立包；不重做成员计划或回建父 System。"""
    if not isinstance(plans, dict) or not plans or len(set(imports["targets"])) != len(imports["targets"]):
        raise ValueError("分批目录缺准确动作映射或完整 imports")
    validated = validate_batch(list(plans.values()), imports=imports)
    imported = set(imports["targets"])
    units, assets, generic = {}, {}, {}

    def add_asset(path, recipe, asset_type, **facts):
        value = {"recipe_sha256": _batch_recipe_sha(recipe), "asset_type": asset_type, **facts}
        if path in assets and assets[path] != value:
            raise ValueError("同一分批目标有不同执行配方：" + path)
        assets[path] = value

    for plan in plans.values():
        for instance, material in plan["materials"].items():
            normalized = copy.deepcopy(material)
            if normalized.get("mesh_uv") is not None:
                normalized["mesh_uv"] = PU.mesh_uv_material_contract(normalized["mesh_uv"])
            if instance in generic and generic[instance][1] != normalized:
                raise ValueError("共享材质的完整执行配方不同：" + instance)
            generic.setdefault(instance, (material, normalized))
    for instance, (material, normalized) in sorted(generic.items()):
        master = MASTER_DIR + "/" + material["master"]
        unit = units.setdefault(master, {"kind": "material", "targets": set(), "dependencies": set(), "tasks": []})
        unit["targets"].update((master, instance))
        unit["dependencies"].update(_batch_package_references(material, imported))
        unit["tasks"].append({"plan": material, "instance": instance})
        add_asset(master, {"kind": "material_master", "plan": normalized}, "Material")
        add_asset(instance, {"kind": "material_instance", "plan": normalized, "parent": master},
                  "MaterialInstanceConstant", parent=master,
                  parameters=normalized["params"], textures=normalized["textures"])
    for kind, recipes in (("component_material", validated["component_materials"]),
                          ("projected_material", validated["projected_materials"])):
        for recipe in recipes:
            targets = {path for spec in recipe["materials"] for path in (spec["master"], spec["instance"])}
            key = min(targets)
            if key in units:
                raise ValueError("完整材质单元目标冲突：" + key)
            units[key] = {"kind": kind, "targets": targets,
                "dependencies": (set(recipe["targets"]) - targets) | _batch_package_references(recipe, imported),
                "tasks": [{"plan": recipe}]}
            for spec in recipe["materials"]:
                add_asset(spec["master"], {"kind": kind, "spec": spec}, "Material")
                add_asset(spec["instance"], {"kind": kind, "spec": spec},
                          "MaterialInstanceConstant", parent=spec["master"])
    owners = {}
    for key, unit in units.items():
        for path in unit["targets"]:
            if path in owners:
                raise ValueError("不同完整材质单元共享创建目标，须先收敛所属单元：" + path)
            owners[path] = key
        unit["targets"] = sorted(unit["targets"])
        unit["dependencies"] = sorted(unit["dependencies"])
        if not set(unit["dependencies"]) <= imported:
            raise ValueError("材质单元有未声明的只读导入依赖：" + key)
    for item in imports["entries"].values():
        recipe = {key: value for key, value in item.items()
                  if key not in {"settings_source", "source_texture_contract"}}
        add_asset(item["path"], {"kind": "import", "entry": recipe},
                  "Texture2D" if item["type"] == "Texture2D" else "StaticMesh")
    systems = {}
    for action, composition in plans.items():
        compiled = []
        for plan in compile_unit_plans(composition):
            materials = set(plan["targets"]) - {plan["system"]} - imported
            if not materials <= set(owners):
                raise ValueError("独立 NS 有未分配的材质依赖：" + action)
            dependencies = materials | (set(plan["targets"]) & imported) | _batch_package_references(plan["specs"], imported)
            for path in materials:
                dependencies.update(units[owners[path]]["dependencies"])
            add_asset(plan["system"], {"kind": "system", "plan": plan}, "NiagaraSystem")
            compiled.append({"system":plan["system"], "targets":[plan["system"]],
                             "dependencies":sorted(dependencies), "emitter_count":len(plan["specs"])})
        systems[action] = {"units":compiled, "targets":[unit["system"] for unit in compiled],
                           "dependencies":sorted(set().union(*(set(unit["dependencies"]) for unit in compiled))),
                           "emitter_count":sum(unit["emitter_count"] for unit in compiled)}
    profile = profile_request["target_path"]
    add_asset(profile, {"kind": "profile", "request": profile_request}, "GGYGODistortionProfile")
    expected = set(validated["targets"]) | {profile}
    if set(assets) != expected:
        raise ValueError("分批目录没有无损覆盖原准确目标集合")
    return {"schema": "GGYGO.FX.AssetBatchCatalog/v1", "units": units, "systems": systems,
            "profile": {"target": profile, **assets[profile]}, "assets": assets, "targets": sorted(expected)}


def _complete_batch_material_compilation(path, material, mcp, unreal, *, diagnostics):
    """每窗在原同步边界完成准确 World 的实际材质资源；持久包复用不代替派生就绪。"""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    library = getattr(unreal, "GGYGOProjectedDecalRendererProperties", None)
    complete = getattr(library, "complete_material_compilation_for_authoring", None)
    state_type = getattr(unreal, "GGYGOMaterialCompilationState", None)
    if world is None or not callable(complete) or state_type is None:
        raise RuntimeError("材质编译缺原 EditorWorld 或实际加载的 MaterialInterface 完成入口: " + path)
    expected_material = path + "." + path.rsplit("/", 1)[1]
    expected_world = world.get_path_name()
    if not isinstance(material, unreal.MaterialInterface) or material.get_path_name() != expected_material:
        raise RuntimeError("材质编译的原 MaterialInterface 身份不同: " + path)
    diagnostics["material_wait"] = {"package":path, "world":expected_world, "stage":"CompleteMaterialCompilation"}

    def complete_and_capture():
        state = complete(material, world)
        if not isinstance(state, state_type):
            diagnostics["material_wait"]["result_type"] = type(state).__name__
            raise RuntimeError("材质完成入口未返回实际 GGYGOMaterialCompilationState: " + path)
        fields = ("ready", "material_path", "world_path", "shader_platform", "resource_material_path",
                  "resource_available", "shader_map_complete", "shader_map_present", "compilation_finalized",
                  "compiled_successfully", "valid_for_rendering", "error")
        result = {name:state.get_editor_property(name) for name in fields}
        result["compile_errors"] = list(state.get_editor_property("compile_errors"))
        # 在同步执行器的返栈预算门前保全结果；预算拒绝也不丢失原 Native 失败。
        diagnostics["material_wait"]["native"] = result
        return result

    result = mcp.run_native_sync("material_compilation:" + expected_material, complete_and_capture)
    # 原资源门先核返栈 dirty／保护／预算；失败快照保留在同一回执内。
    yield "material_compilation_completed:" + path
    if (result["ready"] is not True or result["material_path"] != expected_material
            or result["world_path"] != expected_world or result["compile_errors"] or result["error"]):
        raise RuntimeError("当前 World 的实际材质 ShaderMap 尚未合格: %s %s" % (
            path, json.dumps(result, ensure_ascii=False, sort_keys=True)))
    diagnostics.pop("material_wait")


def _verify_batch_native_asset(path, expected, record, mcp, unreal, *, diagnostics):
    """核收实际依赖；我方生成材质／NS 显式完成原派生编译，不编辑或保存包。"""
    obj = unreal.load_asset(path)
    asset_type = getattr(unreal, expected["asset_type"], None)
    if asset_type is None or not isinstance(obj, asset_type) \
            or obj.get_path_name() != path + "." + path.rsplit("/", 1)[1]:
        raise RuntimeError("只读资产 Native 类型／准确对象不符：" + path)
    actual_class = obj.get_class().get_path_name()
    if record is not None and record.get("native_class") is not None and record["native_class"] != actual_class:
        raise RuntimeError("只读资产 Native 类改变：" + path)
    if expected["asset_type"] == "Material":
        yield from _complete_batch_material_compilation(path, obj, mcp, unreal, diagnostics=diagnostics)
    elif expected["asset_type"] == "MaterialInstanceConstant":
        parent = obj.get_editor_property("parent")
        if parent is None or parent.get_path_name().split(".", 1)[0] != expected["parent"]:
            raise RuntimeError("只读实例实际 Parent 与配方不符：" + path)
        from zzz_fx_material_ue import linear_color
        values = [("scalar" if row["dim"] == 1 else "vector", name,
                   row["value"] if row["dim"] == 1 else linear_color(row["value"]))
                  for name, row in expected.get("parameters", {}).items()]
        values += [("texture", name, value) for name, value in expected.get("textures", {}).items()]
        for kind, name, value in values:
            names = getattr(unreal.MaterialEditingLibrary, "get_" + kind + "_parameter_names")(obj)
            overrides = [row.get_editor_property("parameter_value")
                for row in obj.get_editor_property(kind + "_parameter_values")
                if str(row.get_editor_property("parameter_info").get_editor_property("name")) == name
                and row.get_editor_property("parameter_info").get_editor_property("association")
                    == unreal.MaterialParameterAssociation.GLOBAL_PARAMETER
                and row.get_editor_property("parameter_info").get_editor_property("index") == -1]
            actual = getattr(unreal.MaterialEditingLibrary, "get_material_instance_" + kind + "_parameter_value")(obj, name)
            if name not in {str(item) for item in names} or len(overrides) != 1:
                raise RuntimeError("只读实例缺准确 typed 本地 override：" + path + "." + name)
            for current in (overrides[0], actual):
                if kind == "texture":
                    valid = current is not None and current.get_path_name().split(".", 1)[0] == value
                elif kind == "scalar":
                    valid = float(current) == struct.unpack("<f", struct.pack("<f", value))[0]
                else:
                    valid = all(float(getattr(current, key)) == struct.unpack("<f", struct.pack("<f", value[key]))[0]
                                for key in "rgba")
                if not valid:
                    raise RuntimeError("只读实例本地 override／实际有效值改变：" + path + "." + name)
        yield from _complete_batch_material_compilation(path, obj, mcp, unreal, diagnostics=diagnostics)
    elif expected["asset_type"] == "NiagaraSystem":
        from zzz_fx_niagara_ue import COMPILE
        reference = {"refPath": obj.get_path_name()}
        last_observed = None

        def observe(action, native, *, compile_diagnostics=None):
            nonlocal last_observed
            flags = {key: native[key] for key in ("bNeedsCompileRequest", "bActiveCompilations",
                "bCompilationPending", "bNativeReady", "bSystemValid", "bVMAttributesEqual", "error")}
            current = {"package": path, "action": action, **flags}
            if current != last_observed:
                unreal.log("FX.NSCompilation " + json.dumps(current, ensure_ascii=False, sort_keys=True))
                last_observed = current
            diagnostics["readonly_wait"] = {"package": path, "action": action, "native": native}
            if compile_diagnostics is not None:
                diagnostics["readonly_wait"]["compile_diagnostics"] = compile_diagnostics

        native = mcp.tool(COMPILE + "ReadSystemState", system=reference)["returnValue"]
        observe("Inspect", native)
        if native["error"] or native["systemPath"] != reference["refPath"]:
            NiagaraBuilder.verify_native_compilation(path, native)
        if native["bNeedsCompileRequest"] or native["bCompilationPending"] or native["bActiveCompilations"]:
            # Root 对准确配方中的我方生成 NS 明确授权的编译动作，不能称为纯读取。
            observe("CompletePendingCompilation:Begin", native)
            native = mcp.tool(COMPILE + "CompletePendingCompilation", system=reference)["returnValue"]
            observe("CompletePendingCompilation:Returned", native)
            if native["error"] or native["systemPath"] != reference["refPath"]:
                NiagaraBuilder.verify_native_compilation(path, native)
            # 原边界立即核 dirty、资源与预算；不清 dirty、不保存，也不外层重试编译。
            yield "ns_compilation_completed:" + path
            native = mcp.tool(COMPILE + "ReadSystemState", system=reference)["returnValue"]
            observe("AfterCompletionBoundary", native)
        if native["error"] or native["systemPath"] != reference["refPath"]:
            NiagaraBuilder.verify_native_compilation(path, native)
        if native["bNeedsCompileRequest"] or native["bCompilationPending"] or native["bActiveCompilations"]:
            raise RuntimeError("原生完成接口后 NS 编译仍未收束，停止核收：%s %r" % (path, native))
        # 无 VM 薄桥保留全部脚本诊断；读回成功不代表编译通过。
        compile_diagnostics = mcp.tool(COMPILE + "ReadSystemCompileDiagnostics", system=reference)["returnValue"]
        diagnostics["readonly_wait"]["compile_diagnostics"] = compile_diagnostics
        state = NiagaraBuilder.compile_state_from_diagnostics(path, compile_diagnostics)
        # 把原就绪循环的首次 Native 读取移到拒绝前，保留完整诊断后的实际快照。
        native = mcp.tool(COMPILE + "ReadSystemState", system=reference)["returnValue"]
        observe("AfterCompileState", native, compile_diagnostics=compile_diagnostics)
        NiagaraBuilder.verify_compile_state(path, state)
        while True:
            if (native["bCompilationPending"] or native["bActiveCompilations"]
                    or native["bNeedsCompileRequest"]):
                raise RuntimeError("只读 NS 完整诊断后的编译快照已变化：%s %r" % (path, native))
            NiagaraBuilder.verify_native_compilation(path, native)
            if native["bNativeReady"]:
                break
            yield "readonly_ns_waiting_native_ready:" + path
            native = mcp.tool(COMPILE + "ReadSystemState", system=reference)["returnValue"]
            observe("NativeReady", native, compile_diagnostics=compile_diagnostics)
        diagnostics.pop("readonly_wait")
    elif expected["asset_type"] == "GGYGODistortionProfile":
        if not isinstance(obj.validate_configuration(), str):
            raise RuntimeError("只读 Profile Native 配置无效：" + path)
    return {"recipe_sha256": expected["recipe_sha256"], "native_class": actual_class}


def _batch_native_material_builder(session, kind, unreal, readonly):
    if kind == "component_material":
        from build_nap_avatar_simple_materials import NapAvatarSimpleBuilder
        return NapAvatarSimpleBuilder(session, unreal=unreal, verified_readonly_dependencies=readonly)
    from build_projected_fx_materials import ProjectedFXMaterialBuilder
    from zzz_fx_material_ue import build_source_mesh_uv
    return ProjectedFXMaterialBuilder(session, unreal=unreal, uv_author=build_source_mesh_uv,
                                     verified_readonly_dependencies=readonly)


def _reusable_readonly_assets(readonly, catalog, admission):
    """只沿已冻结正常回执复用静态核收；缺兼容证据时保留原完整检查。"""
    def identity(pin):
        return pin.get("size",pin.get("size_bytes")),pin.get("sha256","").lower()

    def key(path):
        return str(Path(path).resolve()).casefold()

    frozen = {key(pin["path"]):pin for pin in admission["inputs"]}
    for pin in [admission["software"],admission["modules"]["fx_build"],
                *(record["source_return"] for record in readonly.values())]:
        frozen[key(pin["path"])] = pin
    documents = {}

    def read_frozen(pin):
        admitted = frozen.get(key(pin["path"]))
        if admitted is None or identity(admitted) != identity(pin):
            return None
        raw = Path(admitted["path"]).read_bytes()
        if (len(raw),hashlib.sha256(raw).hexdigest()) != identity(admitted):
            raise ValueError("静态复用所读冻结输入身份改变: "+admitted["path"])
        return raw

    def document(pin):
        name = key(pin["path"])
        if name not in documents:
            raw = read_frozen(pin)
            documents[name] = json.loads(raw.decode("utf-8-sig")) if raw is not None else None
        return documents[name]

    def readers(raw):
        if raw is None:
            return {}
        return {node.name:ast.dump(node,include_attributes=False)
            for node in ast.parse(raw.decode("utf-8-sig")).body
            if isinstance(node,ast.FunctionDef) and node.name in (
                "_verify_batch_native_asset","_batch_native_material_builder")}

    current_software = document(admission["software"])
    current_readers = readers(read_frozen(admission["modules"]["fx_build"]))
    if current_software is None or len(current_readers) != 2:
        return set()
    sources, dependencies, unit_kinds, unit_packages = {}, {path:set() for path in readonly}, {}, {}
    for unit in catalog["units"].values():
        for path in set(unit["targets"]) & set(readonly):
            dependencies[path].update(unit["dependencies"])
            unit_kinds[path] = unit["kind"]
            if unit["kind"] != "material":
                unit_packages[path] = set(unit["targets"])
    for path in readonly:
        parent = catalog["assets"][path].get("parent")
        if parent is not None:
            dependencies[path].add(parent)

    def family(rows):
        if rows is None:
            return None
        return {key(row["path"]):(row["exists"],identity(row["file"]) if row["exists"] else None) for row in rows}

    reusable = set()
    for path,record in readonly.items():
        asset_type = catalog["assets"][path]["asset_type"]
        if asset_type == "NiagaraSystem" or "restore_archive" in record or record["native_class"] is None:
            continue
        source_key = key(record["source_return"]["path"])
        if source_key not in sources:
            source = document(record["source_return"])
            context = None
            if source is not None and all(source.get(flag) is True for flag in (
                    "success","validation_success","protection_success")):
                report = source.get("fx_batch",{})
                before = document(source["receipts"]["before.json"])
                if report.get("batch_complete") is True and before is not None:
                    previous = before["batch"]["data"]
                    software = document(previous["software"])
                    old_builder = previous["modules"]["fx_build"]
                    # 作者改动只允许复用真实旧字节中未变的Native读者；不执行旧源码。
                    snapshot = next((pin for pin in frozen.values() if identity(pin) == identity(old_builder)),None)
                    if (software is not None and previous["rhi"] == admission["rhi"]
                            and all(identity(software[name]) == identity(current_software[name])
                                for name in ("engine_image","engine_module_manifest"))
                            and snapshot is not None and readers(read_frozen(snapshot)) == current_readers):
                        context = source,previous,software
            sources[source_key] = context
        context = sources[source_key]
        if context is None:
            continue
        source,previous,software = context
        old_inputs = {key(pin["path"]):pin for pin in previous["inputs"]}
        reader_files = []
        if asset_type in ("Material","MaterialInstanceConstant"):
            reader_files.append("zzz_fx_material_ue.py")
        if asset_type in ("Texture2D","StaticMesh"):
            reader_files.append("zzz_fx_import_assets.py")
        if asset_type == "StaticMesh":
            reader_files.append("build_pyrios_ghost_fx.py")
        kind = unit_kinds.get(path)
        if kind in ("component_material","projected_material"):
            reader_files += ["build_nap_avatar_simple_materials.py","nap_avatar_simple_material_plan.py"]
            if kind == "projected_material":
                reader_files += ["build_projected_fx_materials.py","projected_fx_material_plan.py"]
        if any(key(Path(__file__).parent/name) not in old_inputs or key(Path(__file__).parent/name) not in frozen
                or identity(old_inputs[key(Path(__file__).parent/name)]) != identity(frozen[key(Path(__file__).parent/name)])
                for name in reader_files):
            continue
        native_modules = {"GGYGORendering"} if asset_type == "GGYGODistortionProfile" or kind in (
            "component_material","projected_material") else set()
        class_module = record["native_class"].split("/Script/",1)[-1].split(".",1)[0]
        if class_module in current_software["modules"]:
            native_modules.add(class_module)
        if any(name not in software["modules"] or name not in current_software["modules"]
                or identity(software["modules"][name]) != identity(current_software["modules"][name]) for name in native_modules):
            continue
        report = source["fx_batch"]
        old_readonly = previous["business"]["fx_batch"]["readonly_assets"]
        # 多role单元必须在同一正常来源中闭合，不能拼单包类型读回来替代完整单元核收。
        for dependency in {path} | dependencies[path] | unit_packages.get(path,set()):
            if dependency not in readonly or report["assets"].get(dependency) != {
                    name:readonly[dependency][name] for name in ("recipe_sha256","native_class")}:
                break
            old_family = source["target_postimages"].get(dependency) if dependency in report["saved_packages"] \
                else old_readonly.get(dependency,{}).get("files") if dependency in report["readonly_packages"] else None
            if old_family is None or family(old_family) != family(readonly[dependency]["files"]):
                break
        else:
            reusable.add(path)
    # 上游配置或其实际读者改变时，相关下游也回原完整核收路径。
    while True:
        retained = {path for path in reusable if dependencies[path] <= reusable}
        if retained == reusable:
            return retained
        reusable = retained


def iter_apply_asset_batch(plans, mcp, approved_targets, imports, *, selection, unreal,
                           receipt, profile_request, admission, import_resume=None, import_resume_receipt=None):
    """沿原宿主安全点制作一个明确子批；只读前批、仅完整 NS 进入创建流程。"""
    if unreal is None or not isinstance(receipt, dict) or receipt:
        raise ValueError("分批制作缺同一原生 Editor 或本次全新空回执")
    if selection.get("schema") != "GGYGO.FX.AssetBatchSelection/v1":
        raise ValueError("缺明确的制作子批选择")
    if not isinstance(admission,dict) or admission.get("business",{}).get("fx_batch") != selection:
        raise ValueError("静态复用缺原Leaf传入的同批admission上下文")
    catalog = asset_batch_catalog(plans, imports, profile_request=profile_request)
    kind = selection["kind"]
    readonly = selection["readonly_assets"]
    candidates = {path for path, record in readonly.items() if "restore_archive" in record}
    selected_units = []
    selected_system_plan = None
    if kind == "dependencies":
        ids = selection["unit_ids"]
        if len(ids) != len(set(ids)) or not set(ids) <= set(catalog["units"]) or not (ids or candidates):
            raise ValueError("依赖子批须选明确完整单元或非空初始只读候选")
        selected_units = [catalog["units"][key] for key in ids]
        selected = set().union(*(set(unit["targets"]) for unit in selected_units))
        required = selected | candidates
        for unit in selected_units:
            required.update(unit["dependencies"])
        for composition in catalog["systems"].values():
            for system in composition["units"]:
                if system["system"] in candidates:
                    required.update(system["dependencies"])
        for unit in catalog["units"].values():
            if set(unit["targets"]) & candidates:
                required.update(unit["dependencies"])
        for path in candidates:
            if path in catalog["assets"] and "parent" in catalog["assets"][path]:
                required.add(catalog["assets"][path]["parent"])
    elif kind == "system":
        action = selection["action"]
        if action not in plans:
            raise ValueError("完整 NS 子批动作不属于原准备")
        requested = set(approved_targets)
        chosen = [unit for unit in catalog["systems"][action]["units"] if unit["system"] in requested]
        if len(chosen) != 1 or requested != set(chosen[0]["targets"]):
            raise ValueError("System窗须由原targets精确选择一个实际独立NS，不含兄弟或父包")
        system = chosen[0]
        selected_system_plan = next(unit for unit in compile_unit_plans(plans[action]) if unit["system"] == system["system"])
        selected = set(system["targets"])
        required = selected | set(system["dependencies"])
        if candidates:
            raise ValueError("初始归档候选须先经依赖批 Native 核收")
    elif kind == "integration":
        selected = set()
        required = set(catalog["targets"])
        if candidates:
            raise ValueError("最终接线只消费已核收正常子批")
    else:
        raise ValueError("B 只接依赖／完整 NS／最终只读核收；Profile 创建仍属原 leaf")
    create = set(approved_targets)
    if not create <= selected or set(readonly) != required - create or create & set(readonly):
        raise ValueError("子批准确 create／readonly 目标与宿主授权不一致")
    if not required <= set(catalog["assets"]):
        raise ValueError("子批引用越出完整准备目录")
    for unit in selected_units:
        owned = set(unit["targets"]) & create
        if unit["kind"] != "material" and owned and owned != set(unit["targets"]):
            raise ValueError("Native 多 role 材质单元须完整创建或完整只读核收")
    legacy_imports, import_validation = set(), None
    if import_resume is not None:
        if not isinstance(import_resume_receipt, dict) or import_resume_receipt:
            raise ValueError("原导入只读来源须有本次全新空回执")
        source_path = Path(import_resume["path"]).resolve()
        legacy_imports = {path for path, record in readonly.items()
            if path in imports["targets"] and Path(record["source_return"]["path"]).resolve() == source_path
            and record["source_return"]["sha256"].lower() == import_resume["sha256"].lower()}
        if not legacy_imports:
            raise ValueError("本批没有原导入初始来源，不应继承旧归还父链")
        from zzz_fx_import_assets import validate_import_resume
        import_validation = validate_import_resume(imports, import_resume)
        import_resume_receipt.update(schema="GGYGO.FX.ReadOnlyImportsReceipt/v1",
            source_receipt=dict(import_resume), source_verified=True,
            source_validated_packages=import_validation["packages"], expected_packages=sorted(legacy_imports),
            verified_packages=[], identity_readbacks={}, property_readbacks={}, geometry_readbacks={},
            current_package=None, stage="NativeContext", complete=False)
    elif import_resume_receipt is not None:
        raise ValueError("没有原导入来源却提供只读回执")
    verify_readonly_asset_files(readonly, {path: catalog["assets"][path] for path in readonly},
                                initial_imports=legacy_imports)
    session = AssetSession(mcp, create, create, readonly_targets=readonly)
    receipt.update(schema="GGYGO.FX.AssetBatchResult/v1", kind=kind,
        batch_complete=False, production_complete=False, assets={}, saved_packages=[], readonly_packages=[], reports=[])
    if import_validation is not None:
        from zzz_fx_import_assets import verify_import_resume
        subset = {"entries": {pid: item for pid, item in imports["entries"].items() if item["path"] in legacy_imports},
                  "assets": {pid: path for pid, path in imports["assets"].items() if path in legacy_imports},
                  "targets": sorted(legacy_imports)}
        # 来源已按原完整 242 合同核过；这里只投影本批实际需要的 Native 读集。
        verify_import_resume(subset, mcp, {**import_validation, "packages": sorted(legacy_imports)},
                             import_resume_receipt, unreal=unreal, geometry_reports={})
    reusable = _reusable_readonly_assets(readonly,catalog,admission) - legacy_imports
    # 复用只覆盖持久内容；所有材质的当前 World 派生状态及已有 NS 状态仍走原 Native 入口。
    verified = {path:{name:readonly[path][name] for name in ("recipe_sha256","native_class")}
        for path in sorted(reusable) if catalog["assets"][path]["asset_type"] != "Material"}
    receipt["readonly_packages"].extend(verified)
    if verified:
        yield "readonly_assets_reused:"+str(len(verified))
    for path in sorted(readonly):
        if path in verified:
            if catalog["assets"][path]["asset_type"] == "MaterialInstanceConstant":
                material = unreal.load_asset(path)
                yield from _complete_batch_material_compilation(path, material, mcp, unreal, diagnostics=receipt)
            continue
        verified[path] = yield from _verify_batch_native_asset(
            path, catalog["assets"][path], readonly[path], mcp, unreal, diagnostics=receipt)
        receipt["readonly_packages"].append(path)
        yield "readonly_asset_verified:" + path
    for unit in catalog["units"].values():
        if (unit["kind"] != "material" and set(unit["targets"]) <= set(readonly)
                and not (set(unit["targets"]) | set(unit["dependencies"])) <= reusable):
            _batch_native_material_builder(session, unit["kind"], unreal, readonly).verify(unit["tasks"][0]["plan"])
            yield "readonly_native_material_unit_verified:" + unit["targets"][0]
    receipt["assets"].update(verified)
    for unit in selected_units:
        owned = set(unit["targets"]) & create
        if not owned:
            continue
        if unit["kind"] == "material":
            builder = Builder(session, unreal=unreal)
            for task in unit["tasks"]:
                material, instance = task["plan"], task["instance"]
                master = MASTER_DIR + "/" + material["master"]
                if master in create:
                    if material.get("output_contract") == "distortion_field_pair":
                        Builder.require_dual_field_class(mcp, unreal=unreal)
                    master = builder.build_master(material)
                if instance in create:
                    builder.build_instance(material, master, instance.rsplit("/", 1)[1])
        else:
            builder = _batch_native_material_builder(session, unit["kind"], unreal, readonly)
            builder.build(unit["tasks"][0]["plan"])
            session.save(owned)
            builder.verify(unit["tasks"][0]["plan"])
        for path in sorted(owned):
            if path not in session.saved:
                raise RuntimeError("子批依赖缺真实同步保存：" + path)
            receipt["assets"][path] = yield from _verify_batch_native_asset(
                path, catalog["assets"][path], None, mcp, unreal, diagnostics=receipt)
            yield "dependency_asset_saved:" + path
    if kind == "system" and create:
        plan = selected_system_plan
        geometry = {}
        from build_pyrios_ghost_fx import read_geometry
        for spec in plan["specs"]:
            renderer = spec["renderer"]
            if renderer["kind"] == "component_mesh":
                source = renderer["source_geometry"]
                item = imports["entries"][source["mesh_pid"]]
                if Path(item["source"]).resolve() != Path(source["source_fbx"]["path"]).resolve() \
                        or item["identity"]["source_sha256"] != source["source_fbx"]["sha256"]:
                    raise ValueError("完整 NS Mesh 不是准确原源绕序输入")
                geometry[spec["name"]] = read_geometry(unreal, item, renderer["source_contract"],
                    vertex_color_mode=source["vertex_color_mode"], verify_tangents=True)
        state = yield from NiagaraBuilder(session, unreal=unreal).iter_build_system(plan["system"], plan["specs"])
        receipt["reports"].append({"name": plan["name"], "system": plan["system"],
            "compile": state, "component_mesh_geometry": geometry})
        receipt["assets"][plan["system"]] = yield from _verify_batch_native_asset(
            plan["system"], catalog["assets"][plan["system"]], None, mcp, unreal, diagnostics=receipt)
        yield "niagara_system_saved:" + plan["system"]
    if session.created != create or session.saved != create or set(receipt["assets"]) != required:
        raise RuntimeError("当前子批创建／保存／Native 核收未完整覆盖准确集合")
    receipt.update(saved_packages=sorted(session.saved), batch_complete=True)
    return receipt


def build(fx_path, mcp, approved_targets, **options):
    return apply_batch([preflight(fx_path, **options)], mcp, approved_targets)[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fx", nargs="+")
    parser.add_argument("--assets-map", type=Path)
    parser.add_argument("--deps-path", type=Path,
                        help="Explicit dependency file for a single FX source; never falls back to legacy exports")
    parser.add_argument("--plan-imports", action="store_true")
    parser.add_argument("--revision", default="")
    parser.add_argument("--particle-equivalence", type=Path,
                         help="Explicit mode and all tunables; omitted retains strict native-kernel requirements")
    parser.add_argument("--ue-equivalent", type=Path,
                        help="Explicit complete Front/Back UE environment configuration, with source evidence retained")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--endpoint")
    parser.add_argument("--approved-targets", type=Path)
    parser.add_argument("--inspect-source-programs", action="store_true",
                        help="只读审计源 Particle Renderer 候选，不生成资产写入计划")
    parser.add_argument("--material-audits", type=Path,
                        help="JSON：准确材质 PathID 到既有程序审计文件路径的映射")
    args = parser.parse_args()
    if args.inspect_source_programs:
        if any((args.assets_map, args.deps_path, args.plan_imports, args.revision,
                args.particle_equivalence, args.ue_equivalent, args.apply, args.endpoint, args.approved_targets)):
            parser.error("--inspect-source-programs cannot be combined with production/import options")
        if not args.material_audits:
            parser.error("--inspect-source-programs requires --material-audits")
        try:
            audits = read_json(args.material_audits)
            if not isinstance(audits, dict) or any(not isinstance(k, str) or not k or
                    not isinstance(v, str) or not v for k, v in audits.items()):
                raise ValueError("--material-audits must map material PathIDs to audit file paths")
            result = inspect_source_programs(args.fx, audits)
        except (ValueError, OSError, KeyError) as error:
            print(json.dumps({"scope": "source_program_inventory", "render_preflight": "inspection_only",
                              "runtime_selection": "unverified", "status": "failed", "error": str(error)},
                             ensure_ascii=False, indent=1))
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0
    if args.material_audits:
        parser.error("--material-audits requires --inspect-source-programs")
    if args.ue_equivalent:
        import zzz_fx_ue_equivalent as UE
        args.revision = args.revision or UE.configuration(args.ue_equivalent)["revision"]
    if args.deps_path and len(args.fx) != 1:
        parser.error("--deps-path requires one FX source")
    plans, errors = [], []
    imports = None
    if args.plan_imports:
        if args.assets_map:
            parser.error("Choose --plan-imports or --assets-map")
        from zzz_fx_import_assets import plan_imports
        imports = plan_imports([dependency_path(p, explicit=args.deps_path) for p in args.fx], args.revision)
    for path in args.fx:
        try:
            plans.append(preflight(path, assets=imports["assets"] if imports else
                                   read_json(args.assets_map) if args.assets_map else None,
                                   revision=args.revision, deps_path=args.deps_path,
                                    particle_equivalence=read_json(args.particle_equivalence) if args.particle_equivalence else None,
                                    ue_equivalent=args.ue_equivalent))
        except PreflightError as error:
            errors.append(error.report)
    if errors:
        print(json.dumps({"preflight": "blocked", "errors": errors}, ensure_ascii=False, indent=1))
        return 1
    if args.ue_equivalent:
        import zzz_fx_ue_equivalent as UE
        UE.validate_batch(plans)
    if not args.apply:
        print(json.dumps({"plans": plans, "imports": imports}, ensure_ascii=False, indent=1))
        return 0
    if not args.endpoint or not args.approved_targets:
        parser.error("--apply requires the assigned --endpoint and exact --approved-targets list")
    from ue_mcp import Mcp
    print(json.dumps(apply_batch(plans, Mcp(args.endpoint), read_json(args.approved_targets), imports),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
