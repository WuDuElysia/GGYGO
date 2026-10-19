"""Offline complete-render preflight and exact, create-only FX asset batches.

Unsupported visible branches block ALL writes. Compile, action integration and
visual comparison are separate acceptance facts; old assets are preserved.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_fx_material as FM
import zzz_fx_niagara as FN
import zzz_fx_particle_renderer as PR
import zzz_fx_mesh_renderer as MR
import zzz_unity_anim as UA
from zzz_fx_asset_session import AssetSession, version_name
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


def walk(node, path=(), active=True):
    active = active and bool(node["active"])
    yield node, path, active
    for child in node["children"]:
        yield from walk(child, path + (child,), active)


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


def material_plan(deps, mpid, renderer, assets, native_selection=None):
    source = dependency_file(deps, mpid, ".json")
    shader_id = str(read_json(source)["m_Shader"]["m_PathID"])
    shader = deps.get(shader_id)
    if shader is None or shader["type"] != "Shader":
        raise ValueError("Missing Shader dependency " + shader_id)
    if shader.get("nativeJson") and shader.get("cab"):
        if native_selection is None:
            raise FM.PlanError("Native Shader %s in %s requires exact subprogram/global keyword selection; "
                               "the legacy variant directory will not be used" % (shader_id, shader["cab"]))
        return FM.plan(source, renderer, assets, shader_name=shader["name"], native_source={
            "shader_entry": shader, "material_pid": mpid, "selection": native_selection})
    if native_selection is not None:
        raise FM.PlanError("Native preview selection requires its exact native Shader dependency")
    return FM.plan(source, renderer, assets, shader_name=shader["name"])


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
                material = read_json(source)
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
              particle_equivalence=None, ue_equivalent=None):
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
    rows = list(walk(root))
    if preview_node is not None:
        selected = [row for row in rows if "/".join(n["name"] for n in row[1]) == preview_node]
        if not preview_node or len(selected) != 1 or not selected[0][2]:
            raise ValueError("Preview requires one exact active source subtree: " + str(preview_node))
        prefix = selected[0][1]
        rows = [row for row in rows if row[1][:len(prefix)] == prefix]
    clip = None
    blocked, specs, materials, controls, mesh_contracts = [], [], {}, [], []
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
            blocked.append({"node": label, "reason": "Light component is not implemented"})
        mesh = node.get("mesh")
        if mesh and mesh["enabled"]:
            try:
                contract = MR.inspect(node, list(path), deps, clip)
                mesh_contracts.append({"node": label, **contract})
                blocked.extend({"node": label, "reason": "MeshRenderer requires " + requirement}
                               for requirement in contract["required_consumers"])
            except (ValueError, FN.SpecError, KeyError, OSError) as error:
                blocked.append({"node": label, "reason": "%s: %s" % (type(error).__name__, error)})
        elif "MeshRenderer" in types and not mesh:
            blocked.append({"node": label, "reason": "MeshRenderer source description is missing"})
        if "particle" not in node:
            continue
        renderer = node["particle"]["renderer"]
        if renderer is None:
            continue  # Source ParticleSystem with no renderer: simulation only.
        mids = [str(m["m_PathID"]) for m in renderer["m_Materials"] if m["m_PathID"]]
        if not renderer["m_Enabled"] or not mids:
            continue
        try:
            if len(mids) != 1:
                raise FN.SpecError("Multiple renderer materials are not implemented")
            mpid = mids[0]
            mesh_pid = str(renderer["m_Mesh"]["m_PathID"])
            context = {"kind": "particle", "streams": renderer["m_VertexStreams"],
                       "custom_streams": renderer["m_UseCustomVertexStreams"],
                       "mesh": renderer["m_RenderMode"] == 4,
                       "sprite_subuv": renderer["m_RenderMode"] == 0 and
                                       bool(node["particle"]["system"].get("UVModule", {}).get("enabled")),
                       "sprite_uv_tiles": tuple(node["particle"]["system"].get("UVModule", {}).get(k)
                                                for k in ("tilesX", "tilesY")),
                       "sprite_normal_direction": renderer.get("m_NormalDirection"),
                       "sprite_rotation_2d": not node["particle"]["system"].get("InitialModule", {}).get("rotation3D", False)
                            and not node["particle"]["system"].get("RotationModule", {}).get("separateAxes", False),
                       "sprite_static_quad_uv": environment_data is not None and renderer["m_RenderMode"] == 0
                           and node["particle"]["system"].get("UVModule", {}).get("enabled") is False,
                       "sprite_extra_quad_uv": environment_data is not None and renderer["m_RenderMode"] == 0,
                       "uv_count": uv_count(deps, mesh_pid) if renderer["m_RenderMode"] == 4 else 1}
            if renderer["m_RenderMode"] == 0 and policy is not None:
                context["viewport_clamp"] = PR.viewport_plan(renderer, policy, label)
            plan = material_plan(deps, mpid, context, assets,
                                 environment_data["materials"].get(mpid) if environment_data is not None else
                                 native_selections.get(mpid) if native_selections is not None else None)
            if revision:
                plan["master"] = version_name(plan["master"], revision)
            mi = "%s/%s" % (MI_DIR, mi_name(plan, revision))
            spec = FN.emitter_spec(node, list(path), clip, assets, {mpid: mi}, plan, policy)
            NiagaraBuilder.validate_spec(spec)
            if not path:
                spec["name"], spec["path"] = "PrefabRoot", "$root"
            specs.append(spec)
            materials[mi] = plan
        except (FM.PlanError, FN.SpecError, FM.T.TranslateError, ValueError, KeyError, OSError) as error:
            blocked.append({"node": label, "reason": "%s: %s" % (type(error).__name__, error)})
    if not specs and not blocked:
        blocked.append({"node": "$root", "reason": "Prefab has no implemented visible renderer"})
    names = [s["name"] for s in specs]
    if len(names) != len(set(names)):
        blocked.append({"node": "$root", "reason": "Node paths collide after Niagara name normalization"})
    report = {"name": fx["name"], "blocked": blocked, "renderers": [s["path"] for s in specs],
              "runtime_controls": controls, "action_integration": "unverified", "visual_comparison": "unverified"}
    if mesh_contracts:
        report["mesh_renderer_contracts"] = mesh_contracts
    if policy is not None:
        report["particle_equivalence"] = {**policy, "precision": "explicit_UE_equivalent_not_native_identity"}
    if preview_node is not None:
        report.update({"scope": "source_subtree_preview", "source_node": preview_node,
                       "source_prefab_restore": "incomplete", "action_integration": "outside preview scope"})
    if blocked:
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
    return {**report, "system": system, "targets": targets, "specs": specs, "materials": materials,
            "render_preflight": "complete"}


def apply_batch(plans, mcp, approved_targets, imports=None):
    import zzz_fx_ue_equivalent as UE
    UE.validate_batch(plans)
    for plan in plans:
        if plan.get("render_preflight") != "complete" or plan.get("blocked") or not plan.get("specs"):
            raise ValueError("Cannot apply an incomplete render plan")
        for material in plan["materials"].values():
            Builder.validate_plan(material)
        for spec in plan["specs"]:
            NiagaraBuilder.validate_spec(spec)
            renderer = spec["renderer"]
            if renderer["kind"] == "sprite":
                material = plan["materials"].get(renderer["material"])
                viewport = material.get("viewport_clamp") if material is not None else None
                if viewport is None or PR.viewport_signature(viewport) != renderer.get("viewport_adapter_signature"):
                    raise ValueError("%s sprite material viewport adapter contract mismatch before editor mutation" % spec["name"])
    targets = {path for plan in plans for path in plan["targets"]}
    if imports:
        targets.update(imports["targets"])
    session = AssetSession(mcp, targets, approved_targets)
    if imports:
        from zzz_fx_import_assets import apply_imports
        apply_imports(imports, session)
    material_builder = Builder(session)
    reports = []
    for plan in plans:
        for mi, material in plan["materials"].items():
            master = material_builder.build_master(material)
            material_builder.build_instance(material, master, mi.rsplit("/", 1)[1])
        state = NiagaraBuilder(session).build_system(plan["system"], plan["specs"])
        reports.append({k: plan[k] for k in ("name", "system", "renderers", "runtime_controls",
                                              "action_integration", "visual_comparison", "scope", "source_node",
                                              "source_prefab_restore", "particle_equivalence", "ue_environment",
                                              "source_shader_selection") if k in plan})
        reports[-1]["compile"] = state
    return reports


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
