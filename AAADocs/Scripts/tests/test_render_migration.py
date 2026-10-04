"""Offline migration failure/retry tests; fake Unreal and temporary files only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


class Obj:
    def __init__(self, path="", **props):
        self.path, self.props = path, props
    def get_path_name(self): return self.path
    def get_editor_property(self, name): return self.props[name]
    def set_editor_property(self, name, value): self.props[name] = value


class Color:
    def __init__(self, r, g, b, a): self.r, self.g, self.b, self.a = r, g, b, a


class Material(Obj): pass
class Blueprint(Obj): pass


class MigrationTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.events, self.logs, self.dirty = [], [], []
        self.protected = False
        self.compile_error = False
        self.path = "/Game/BP/Test"
        self.file = self.root / "Content/BP/Test.uasset"
        self.file.parent.mkdir(parents=True)
        self.file.write_bytes(b"legacy-blueprint")
        self.sha = hashlib.sha256(self.file.read_bytes()).hexdigest()
        self.component = Obj("/Game/BP/Test.Default__Test_C:StylizedRenderComponent",
            MaterialSlots=[], OutlineMaterial=None, KeyLight=None,
            KeyLightTint=Color(1, 1, 1, 1), KeyLightOutputScale=0.65,
            bAutoConfigurePyrios=True, auto_activate=True)
        self.component.get_name = lambda: "StylizedRenderComponent"
        self.component.get_class = lambda: Obj("/Script/GGYGO.GGYGOPyriosRenderComponent")
        self.component.modify = lambda: self.events.append("component.modify")
        self.bp = Blueprint(self.path, status="UP_TO_DATE")
        def modify():
            self.events.append("bp.modify")
            self.dirty[:] = [Obj(self.path)]
        self.bp.modify = modify
        self.bp.generated_class = lambda: "BPClass"
        mesh = Obj(materials=[Obj(material_slot_name="Surface")])
        self.cdo = Obj(mesh=Obj(skeletal_mesh_asset=mesh), StylizedRenderComponent=self.component)
        self.cdo.get_components_by_class = lambda cls: [self.component]
        self.native = Obj(**dict(self.component.props))
        self.body, self.outline = Material("/Game/Body.Body"), Material("/Game/Outline.Outline")
        assets = {self.path: self.bp, "/Game/Body": self.body, "/Game/Outline": self.outline}
        def probe(cls, outer):
            result = Obj()
            def setter(name, value):
                if self.protected and name == "bAutoConfigurePyrios":
                    raise RuntimeError("Property is protected and cannot be set")
                result.props[name] = value
            result.set_editor_property = setter
            return result
        def compile_bp(bp):
            self.events.append("compile")
            bp.props["status"] = "ERROR" if self.compile_error else "UP_TO_DATE"
        def save(bp):
            self.events.append("save")
            self.file.write_bytes(b"migrated-blueprint")
            self.dirty.clear()
            return True
        self.fake = types.SimpleNamespace(Object=Obj, LinearColor=Color, Blueprint=Blueprint,
            MaterialInterface=Material, GGYGOCharacterRenderSlot=Obj,
            GGYGOCharacterRenderComponent=types.SimpleNamespace(static_class=lambda: "Native"),
            GGYGOPyriosRenderComponent=object, new_object=probe,
            get_transient_package=lambda: Obj("/Engine/Transient"),
            Paths=types.SimpleNamespace(project_dir=lambda: str(self.root)),
            get_default_object=lambda cls: self.native if cls == "Native" else self.cdo,
            load_object=lambda outer, path: None,
            EditorAssetLibrary=types.SimpleNamespace(load_asset=lambda path: assets.get(path), save_loaded_asset=save),
            EditorLoadingAndSavingUtils=types.SimpleNamespace(get_dirty_content_packages=lambda: self.dirty),
            BlueprintEditorLibrary=types.SimpleNamespace(compile_blueprint=compile_bp), log=self.logs.append)
        script = Path(__file__).resolve().parents[1] / "migrate_pyrios_render_component.py"
        spec = importlib.util.spec_from_file_location("render_migration_under_test", script)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"unreal": self.fake}): spec.loader.exec_module(self.module)
        props = dict(material_slots=[], OutlineMaterial=None, KeyLight=None,
                     KeyLightTint=[1, 1, 1, 1], KeyLightOutputScale=0.65, bAutoConfigurePyrios=True)
        self.baseline = self.root / "baseline.json"
        self.baseline.write_text(json.dumps(dict(schema=1, complete=True, errors=[],
            native_default=dict(properties=props), blueprints=[dict(asset=self.path, sha256=self.sha,
                components=[dict(object=self.component.path, **{"class": self.component.get_class().path}, properties=props)])])))
        config = self.root / "config.json"
        config.write_text(json.dumps(dict(blueprint=self.path, component_name="StylizedRenderComponent",
            material_slots={"Surface": "/Game/Body"}, outline_material="/Game/Outline")))
        self.module.CONFIG = config

    def test_protected_flag_fails_before_asset_mutation_or_backup(self):
        self.protected = True
        with self.assertRaisesRegex(RuntimeError, "write contract failed for bAutoConfigurePyrios"):
            self.module.run(self.baseline, apply=True)
        self.assertEqual(self.events, [])
        self.assertEqual(self.component.props["MaterialSlots"], [])
        self.assertFalse((self.root / "Saved").exists())
        self.assertEqual(self.file.read_bytes(), b"legacy-blueprint")

    def test_preflight_probes_without_mutating_target(self):
        self.module.run(self.baseline)
        self.assertEqual(self.events, [])
        self.assertTrue(self.component.props["bAutoConfigurePyrios"])
        self.assertFalse((self.root / "Saved").exists())

    def test_saved_values_after_reload_are_idempotent(self):
        self.module.run(self.baseline, apply=True)
        self.assertEqual(self.events.count("save"), 1)
        self.assertFalse(self.component.props["bAutoConfigurePyrios"])
        backup = self.root / "Saved/Codex/RenderMigrationBackup" / (self.sha + "_BP_PC_Pyrios.uasset")
        self.assertEqual(backup.read_bytes(), b"legacy-blueprint")
        # Simulate a new loaded template with the persisted values, not the old object.
        previous = self.component
        self.component = Obj(previous.path, **dict(previous.props))
        self.component.get_name = previous.get_name
        self.component.get_class = previous.get_class
        self.cdo.props["StylizedRenderComponent"] = self.component
        self.events.clear()
        self.module.run(self.baseline, apply=True)
        self.assertEqual(self.events, [])
        self.assertIn("ALREADY_CONFIGURED", self.logs[-1])

    def test_partial_failure_requires_reload_and_never_saves(self):
        self.compile_error = True
        with self.assertRaisesRegex(RuntimeError, "compile failed"):
            self.module.run(self.baseline, apply=True)
        self.assertNotIn("save", self.events)
        self.assertEqual(self.file.read_bytes(), b"legacy-blueprint")
        count = len(self.events)
        with self.assertRaisesRegex(RuntimeError, "Blueprint is dirty"):
            self.module.run(self.baseline, apply=True)
        self.assertEqual(len(self.events), count)

    def test_dirty_even_if_all_values_match_is_not_success(self):
        self.module.run(self.baseline, apply=True)
        self.dirty[:] = [Obj(self.path)]
        with self.assertRaisesRegex(RuntimeError, "Blueprint is dirty"):
            self.module.run(self.baseline)


if __name__ == "__main__":
    unittest.main()
