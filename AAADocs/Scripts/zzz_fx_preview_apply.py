"""Execute one explicitly approved new-only subtree preview and retain its result.

This uses the existing local MCP client. It never places actors, changes maps,
runs PIE or saves a package outside its exact approved batch.
"""
import argparse
import datetime
import hashlib
import json
import sys
import traceback
from pathlib import Path

import zzz_fx_preview as P
from zzz_fx_asset_session import AssetSession
from zzz_fx_import_assets import apply_imports
from zzz_fx_material_ue import Builder
from zzz_fx_niagara_ue import NiagaraBuilder
from ue_mcp import Mcp


class ProgressMcp(Mcp):
    def tool(self, full_name, **arguments):
        if any(full_name.endswith("." + name) for name in
               ("import_file", "create_material", "recompile", "create", "CreateNiagaraSystem", "AddEmitter")):
            print("FX preview: " + full_name.rsplit(".", 1)[1], flush=True)
        return super().tool(full_name, **arguments)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fx", type=Path)
    parser.add_argument("node")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--deps-path", type=Path)
    parser.add_argument("--native-selections-json")
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--approved-targets-json", required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.result.resolve()
    result_root = Path(__file__).resolve().parents[2] / "Saved" / "AutomationReports"
    if result_path.parent != result_root or result_path.exists():
        raise ValueError("Result must be a new file in the project AutomationReports directory")
    result_root.mkdir(parents=True, exist_ok=True)
    selection = json.loads(args.native_selections_json) if args.native_selections_json is not None else None
    batch = P.plan_preview(args.fx, args.node, args.revision, args.deps_path, selection)
    approved = json.loads(args.approved_targets_json)
    if set(batch["targets"]) != set(approved):
        raise ValueError("Current offline plan differs from the exact approved batch")
    scripts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in Path(__file__).parent.glob("zzz_fx*.py")}
    report = {"started": datetime.datetime.now().isoformat(), "targets": batch["targets"],
              "scope": batch["plans"][0]["scope"], "source_node": args.node,
              "source_prefab_restore": "incomplete", "action_integration": "outside preview scope",
              "visual_comparison": "unverified", "executed_script_sha256": scripts,
              "native_shader_selections": {mi: material["source_selection"]
                                            for mi, material in batch["plans"][0]["materials"].items()
                                            if "source_selection" in material},
              "imports": batch["imports"]["entries"], "created": [], "saved": []}
    session = None
    try:
        mcp = ProgressMcp(args.endpoint)
        session = AssetSession(mcp, batch["targets"], approved)
        apply_imports(batch["imports"], session)
        builder = Builder(session)
        plan = batch["plans"][0]
        for mi, material in plan["materials"].items():
            master = builder.build_master(material)
            builder.build_instance(material, master, mi.rsplit("/", 1)[1])
        report["material_compile"] = "passed"
        report["niagara_compile"] = NiagaraBuilder(session).build_system(plan["system"], plan["specs"])
        report["phase"] = "asset_build_passed"
        report["system"] = plan["system"]
        print("FX preview assets built; actual asset preview remains required", flush=True)
    except Exception:
        report["phase"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        if session:
            report["created"], report["saved"] = sorted(session.created), sorted(session.saved)
        report["finished"] = datetime.datetime.now().isoformat()
        result_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print("FX preview result: " + str(result_path), flush=True)


if __name__ == "__main__":
    main()
