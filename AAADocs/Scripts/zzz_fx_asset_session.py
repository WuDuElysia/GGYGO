"""A single approved FX asset batch. Existing packages are never edited or saved.

The caller supplies the exact approved package list after offline planning. Every
target is checked before the first mutation; content versions keep old assets and
their references intact. Failed new packages remain available for diagnosis.
"""
import hashlib
import json
import re

AS = "editor_toolset.toolsets.asset.AssetTools."
PIE = "EditorToolset.EditorAppToolset.IsPIERunning"
ROOTS = ("/Game/Characters/Shared/FX/ZZZ/", "/Game/Characters/Player/Pyrios/FX/Skill/")


class AssetConflict(RuntimeError):
    pass


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12]


def version_name(name, content):
    return re.sub(r"[^A-Za-z0-9_]", "_", name) + "_" + digest(content)


class AssetSession:
    def __init__(self, mcp, targets, approved_targets):
        if mcp is None:
            raise AssetConflict("An explicitly assigned editor connection is required")
        self.m = mcp
        self.targets = set(targets)
        self.created = set()
        self.saved = set()
        if not self.targets or not self.targets.issubset(set(approved_targets)):
            raise AssetConflict("FX batch includes packages outside the approved target list")
        for path in self.targets:
            if not path.startswith(ROOTS) or not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", path):
                raise AssetConflict("Invalid FX package target: " + path)
        self.check_editor()
        # Finish ALL existence checks before starting this batch.
        conflicts = [p for p in sorted(self.targets)
                     if self.m.tool(AS + "exists", path=p)["returnValue"]]
        if conflicts:
            raise AssetConflict("Existing packages are protected; choose a new revision: " + ", ".join(conflicts))

    def check_editor(self):
        if self.m.tool(PIE)["returnValue"]:
            raise AssetConflict("FX asset batch requires its assigned non-PIE editor window")

    def begin_create(self, path):
        if path not in self.targets or path in self.created:
            raise AssetConflict("Unplanned or duplicate creation: " + path)
        self.check_editor()
        # Detect a package created by another writer after batch preflight.
        if self.m.tool(AS + "exists", path=path)["returnValue"]:
            raise AssetConflict("Target appeared after preflight: " + path)

    def created_asset(self, path):
        if path not in self.targets:
            raise AssetConflict("Unplanned asset: " + path)
        self.created.add(path)

    def require_created(self, path):
        if path not in self.created:
            raise AssetConflict("Cannot modify or save an existing/unowned asset: " + path)

    def save(self, paths):
        paths = sorted(set(paths))
        for path in paths:
            self.require_created(path)
        if paths:
            self.check_editor()
            result = self.m.tool(AS + "save_assets", asset_paths=paths)
            if result.get("returnValue") is False:
                raise RuntimeError("FX package save failed: " + ", ".join(paths))
            self.saved.update(paths)
