"""A single approved FX asset batch. Existing packages are never edited or saved.

The caller supplies the exact approved package list after offline planning. Every
target is checked before the first mutation; content versions keep old assets and
their references intact. Failed new packages remain available for diagnosis.
"""
import hashlib
import json
import re
from pathlib import Path

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


def verify_readonly_asset_files(records, requirements, *, initial_imports=()):
    """核本批已由宿主认证来源并冻结的包文件族，不授予写权或代签 Native。"""
    if set(records) != set(requirements):
        raise AssetConflict("只读包记录未准确覆盖本批依赖")
    project = Path(__file__).resolve().parents[2]

    def check_pin(pin):
        path = Path(pin["path"])
        sizes = [pin[key] for key in ("size", "size_bytes") if key in pin]
        if not path.is_absolute() or not sizes or len(set(sizes)) != 1 or not path.is_file():
            raise AssetConflict("只读文件 pin 无效：" + str(path))
        hashed = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1048576), b""):
                size += len(block)
                hashed.update(block)
        if size != sizes[0] or hashed.hexdigest() != pin["sha256"].lower():
            raise AssetConflict("只读文件身份改变：" + str(path))

    checked_sources = set()
    for package, expected in requirements.items():
        record = records[package]
        if record["recipe_sha256"] != expected["recipe_sha256"]:
            raise AssetConflict("只读包不是当前准确配方：" + package)
        source = record["source_return"]
        key = (source["path"], source["sha256"])
        if key not in checked_sources:
            check_pin(source)
            checked_sources.add(key)
        if "restore_archive" in record:
            check_pin(record["restore_archive"])
        elif package not in initial_imports and not isinstance(record.get("native_class"), str):
            raise AssetConflict("后继只读包缺原 Native 类核收：" + package)
        if not package.startswith(ROOTS) or not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", package):
            raise AssetConflict("只读包路径无效：" + package)
        base = project / "Content" / package[len("/Game/"):]
        family = {str(Path(str(base) + suffix).resolve()).lower()
                  for suffix in (".uasset", ".umap", ".uexp", ".ubulk", ".uptnl")}
        rows = record["files"]
        if len(rows) != 5 or {str(Path(row["path"]).resolve()).lower() for row in rows} != family:
            raise AssetConflict("只读包文件族不完整：" + package)
        for row in rows:
            path = Path(row["path"])
            if type(row["exists"]) is not bool or path.exists() != row["exists"]:
                raise AssetConflict("只读包文件存在性改变：" + str(path))
            if row["exists"]:
                if Path(row["file"]["path"]).resolve() != path.resolve():
                    raise AssetConflict("只读包文件 pin 路径不符：" + str(path))
                check_pin(row["file"])
        if not Path(str(base) + ".uasset").is_file():
            raise AssetConflict("只读包缺 uasset：" + package)


class AssetSession:
    def __init__(self, mcp, targets, approved_targets, *, readonly_targets=()):
        if mcp is None:
            raise AssetConflict("An explicitly assigned editor connection is required")
        self.m = mcp
        self.targets = set(targets)
        self.readonly_targets = frozenset(readonly_targets)
        self.created = set()
        self.saved = set()
        if (not (self.targets or self.readonly_targets)
                or not self.targets.issubset(set(approved_targets))
                or self.targets & self.readonly_targets):
            raise AssetConflict("FX batch includes packages outside the approved target list")
        for path in self.targets | self.readonly_targets:
            if not path.startswith(ROOTS) or not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", path):
                raise AssetConflict("Invalid FX package target: " + path)
        self.check_editor()
        # Finish ALL existence checks before starting this batch.
        conflicts = [p for p in sorted(self.targets)
                     if self.m.tool(AS + "exists", path=p)["returnValue"]]
        if conflicts:
            raise AssetConflict("Existing packages are protected; choose a new revision: " + ", ".join(conflicts))
        missing = [p for p in sorted(self.readonly_targets)
                   if not self.m.tool(AS + "exists", path=p)["returnValue"]]
        if missing:
            raise AssetConflict("准确只读依赖尚未存在：" + ", ".join(missing))

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
