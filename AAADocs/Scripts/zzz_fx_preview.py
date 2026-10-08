"""Plan a complete source subtree preview, with only its used dependencies.

The preview is visibly named NS_PREVIEW and explicitly leaves its parent prefab
and action integration incomplete. It is an independent import/render evidence
batch, never a replacement for a partially unsupported production prefab.
"""
import argparse
import json
from pathlib import Path

import zzz_fx_build as B
from zzz_fx_import_assets import plan_imports


def plan_preview(fx_path, node_path, revision="", deps_path=None, native_selections=None):
    deps_path = B.dependency_path(fx_path, explicit=deps_path)
    deps = B.read_json(deps_path)
    # Placeholder paths keep planning offline and let us retain only shader-live
    # textures and the exact selected subtree's meshes. No old UE map is reused.
    source_assets = {pid: "/Source/" + pid for pid, value in deps.items()
                     if value["type"] in ("Texture2D", "Mesh")}
    source = B.preflight(fx_path, assets=source_assets, revision=revision,
                         preview_node=node_path, deps_path=deps_path, native_selections=native_selections)
    used = {path.rsplit("/", 1)[1] for plan in source["materials"].values() for path in plan["textures"].values()}
    used.update(spec["renderer"]["mesh"].rsplit("/", 1)[1] for spec in source["specs"]
                if spec["renderer"]["kind"] == "mesh")
    imports = plan_imports([deps_path], revision, selected_pids=used)
    plan = B.preflight(fx_path, assets=imports["assets"], revision=revision,
                       preview_node=node_path, deps_path=deps_path, native_selections=native_selections)
    return {"plans": [plan], "imports": imports, "targets": sorted(set(plan["targets"] + imports["targets"])),
            "source": str(fx_path), "source_node": node_path, "revision": revision,
            "deps_path": str(deps_path), "native_selections": native_selections}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fx", type=Path)
    parser.add_argument("node")
    parser.add_argument("--revision", default="")
    parser.add_argument("--deps-path", type=Path)
    parser.add_argument("--native-selections-json", help="Explicit material PathID to source candidate preview configuration")
    args = parser.parse_args()
    selection = json.loads(args.native_selections_json) if args.native_selections_json is not None else None
    print(json.dumps(plan_preview(args.fx, args.node, args.revision, args.deps_path, selection), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
