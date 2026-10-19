"""@file test_pyrios_audio_import.py
@brief 离线验证来源契约、既有资产保护和原生失败传播，不冒充 UE 导入验收。
"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import wave


SCRIPT = Path(__file__).resolve().parents[1] / "import_pyrios_audio.py"
SPEC = importlib.util.spec_from_file_location("pyrios_audio_import_under_test", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeImportData:
    def __init__(self, source):
        self.source = source

    def extract_filenames(self):
        return [self.source]


class FakeWave:
    def __init__(self, record):
        self.path = record["object_path"]
        self.source = FakeImportData(record["source"])
        self.values = {"num_channels": record["channels"], "duration": record["duration_seconds"],
                       "looping": False, "volume": 1.0, "pitch": 1.0}
        self.rate = record["sample_rate"]
        self.writes = []

    def get_path_name(self):
        return self.path

    def get_editor_property(self, name):
        return self.values[name]

    def set_editor_property(self, name, value):
        self.writes.append((name, value))
        self.values[name] = value


class AudioImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pyrios_audio_test_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.audio = self.source / "Audio"
        self.project = self.root / "project"
        self.montage = self.project / "protected_montage.uasset"
        self.montage.parent.mkdir(parents=True)
        self.montage.write_bytes(b"existing-montage")
        self.manifest = {"mappedAnimations": {}, "mappedAnimationCount": 3, "mappedEventCount": 6,
                         "wavCount": 6, "unmappedDecodedEvents": [], "animationsWithoutMatchedDecodedEvents": ["unproven"]}
        self.armor = {"character": "Pyrois", "events": [], "wavCount": 2}
        self.footsteps = {"character": "Pyrois", "events": [], "wavCount": 2}
        self.mappings = {}
        for suffix in ("Attack_Normal_01", "Run_Loop", "Walk_Loop"):
            action = MODULE.ACTION_PREFIX + suffix
            folder = self.audio / action
            folder.mkdir(parents=True)
            clip = self.source / "anim" / action
            clip.parent.mkdir(exist_ok=True)
            clip.with_suffix(".fbx").write_bytes(b"source-fbx")
            clip.with_suffix(".json").write_text("{}", encoding="utf-8")
            events = []
            for index, stem in enumerate(("Skill_Attack_Normal_01", "Impact_Attack_Normal_01") if suffix == "Attack_Normal_01" else ("Armor", "Footstep")):
                wav = folder / (stem + ".wav")
                with wave.open(str(wav), "wb") as writer:
                    writer.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
                    writer.writeframes(b"\x01\x00\x02\x00" * 128)
                name = suffix + "_" + stem
                event = {"eventName": name, "eventShortId": 100 + len(self.manifest["mappedAnimations"]) * 2 + index,
                         "eventBankFiles": ["source-bank.bnk"], "mappingMethod": "event-name prefix",
                         "outputs": [action + "/" + wav.name]}
                if suffix != "Attack_Normal_01":
                    event.pop("mappingMethod")
                    event.update(characterSwitchGroupId=4203091697, characterSwitchValue=3763547777,
                                 selectionBasis="original role switch")
                    evidence = {"eventName": name, "eventShortId": event["eventShortId"],
                                "outputs": [{"file": event["outputs"][0]}]}
                    if stem == "Armor":
                        evidence.update(switchGroupId=4203091697, switchValue=3763547777, eventBankFile="source-bank.bnk")
                        self.armor["events"].append(evidence)
                    else:
                        evidence.update(pyroisSwitchValue=3763547777, pyroisNodes=[123], lycaonNodes=[123],
                                        bank="source-bank.bnk", characterSwitchRootId=321)
                        event.update(characterSwitchRootId=321, characterNodeIds=[123])
                        self.footsteps["events"].append(evidence)
                events.append(event)
            self.mappings[action] = {"animationName": action, "animationFbx": str(clip.with_suffix(".fbx")),
                                     "animationJson": str(clip.with_suffix(".json")), "events": events, "wavCount": 2}
            self.manifest["mappedAnimations"][action] = {"events": [e["eventName"] for e in events], "wavCount": 2}
        self.flush()
        for name, value in {"SOURCE": self.source, "AUDIO": self.audio, "PROJECT": self.project,
                            "MONTAGE_FILE": self.montage}.items():
            context = patch.object(MODULE, name, value)
            context.start()
            self.addCleanup(context.stop)
        legacy = MODULE.target_file(MODULE.LEGACY_TARGET)
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(b"existing-soundwave")
        for name, value in {"LEGACY_ASSET_SHA": hashlib.sha256(legacy.read_bytes()).hexdigest(),
                            "LEGACY_SOURCE_SHA": hashlib.sha256((self.audio / MODULE.LEGACY_SOURCE).read_bytes()).hexdigest()}.items():
            context = patch.object(MODULE, name, value)
            context.start()
            self.addCleanup(context.stop)
        self.plan = MODULE.build_plan()
        self.records = {a["target"]: a for a in self.plan["assets"]}
        self.new = [a for a in self.plan["assets"] if a["kind"] == "new"]
        self.plan_path = self.root / "reviewed.json"
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")

    def flush(self):
        for name, data in [("manifest.json", self.manifest), ("movement_pyrois_armor_manifest.json", self.armor),
                           ("movement_pyrois_footsteps_manifest.json", self.footsteps)]:
            (self.audio / name).write_text(json.dumps(data), encoding="utf-8")
        for action, mapping in self.mappings.items():
            (self.audio / action / "mapping.json").write_text(json.dumps(mapping), encoding="utf-8")

    def fake_unreal(self):
        legacy = FakeWave(self.records[MODULE.LEGACY_TARGET])
        errors, saves = [], []

        def save(asset, only_if_is_dirty):
            self.assertFalse(only_if_is_dirty)
            target = asset.path.rsplit(".", 1)[0]
            file = MODULE.target_file(target)
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"saved-target")
            saves.append(target)
            return True

        unreal = SimpleNamespace(SoundWave=FakeWave, AssetImportData=FakeImportData,
            Paths=SimpleNamespace(project_dir=lambda: str(self.project)),
            AssetRegistryHelpers=SimpleNamespace(create_asset_data=lambda a: a, get_tag_value=lambda a, tag: str(a.rate)),
            find_object=lambda outer, name, **kwargs: outer.source if outer is not None else None,
            EditorAssetLibrary=SimpleNamespace(does_asset_exist=lambda t: t == MODULE.LEGACY_TARGET,
                                               load_asset=lambda t: legacy, save_loaded_asset=save),
            log=lambda text: None, log_error=errors.append)
        return unreal, legacy, errors, saves

    def execute(self, unreal, mode, targets=None):
        with patch.dict(sys.modules, {"unreal": unreal}), patch.object(MODULE, "require_host"), \
                patch.object(MODULE, "dirty_packages", return_value={"content": set(), "maps": set()}):
            return MODULE.run(mode, self.plan_path, targets, "commandlet")

    def test_existing_skill_is_preserved_without_duplicate_target(self):
        self.assertEqual(sum(a["kind"] == "preserved" for a in self.plan["assets"]), 1)
        self.assertEqual(len(self.new), 5)
        self.assertEqual(self.records[MODULE.LEGACY_TARGET]["source_sha256"], MODULE.LEGACY_SOURCE_SHA)

    def test_path_escape_is_rejected(self):
        self.mappings[MODULE.NORMAL_ACTION]["events"][1]["outputs"] = [MODULE.NORMAL_ACTION + "/../escape.wav"]
        self.flush()
        with self.assertRaisesRegex(RuntimeError, "输出路径越界"):
            MODULE.build_plan()

    def test_wrong_role_switch_is_rejected(self):
        action = MODULE.ACTION_PREFIX + "Run_Loop"
        self.mappings[action]["events"][1]["characterSwitchValue"] = 2293482459
        self.flush()
        with self.assertRaisesRegex(RuntimeError, "未选中已证 Pyrois"):
            MODULE.build_plan()

    def test_wrong_footstep_node_is_rejected(self):
        action = MODULE.ACTION_PREFIX + "Run_Loop"
        self.mappings[action]["events"][1]["characterNodeIds"] = [456]
        self.flush()
        with self.assertRaisesRegex(RuntimeError, "脚步角色节点与原清单不同"):
            MODULE.build_plan()

    def test_unmapped_wav_is_rejected(self):
        original = Path(self.new[0]["source"])
        (original.parent / "unmapped.wav").write_bytes(original.read_bytes())
        with self.assertRaisesRegex(RuntimeError, "WAV／mapping 文件集合不同"):
            MODULE.build_plan()

    def test_silent_pcm_is_rejected(self):
        file = Path(self.new[0]["source"])
        with wave.open(str(file), "wb") as writer:
            writer.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
            writer.writeframes(b"\x00" * 512)
        with self.assertRaisesRegex(RuntimeError, "PCM 截断或全零"):
            MODULE.build_plan()

    def test_truncated_pcm_is_rejected(self):
        file = Path(self.new[0]["source"])
        file.write_bytes(file.read_bytes()[:-4])
        with self.assertRaisesRegex(RuntimeError, "PCM 截断或全零"):
            MODULE.build_plan()

    def test_reviewed_plan_tampering_is_rejected_before_unreal(self):
        changed = copy.deepcopy(self.plan)
        changed["assets"][0]["target"] = "/Game/Other/forbidden"
        self.plan_path.write_text(json.dumps(changed), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "机器计划与实际"):
            MODULE.run("import", self.plan_path)

    def test_existing_skill_cannot_be_selected_for_import(self):
        with self.assertRaisesRegex(RuntimeError, "目标不属于本模式"):
            MODULE.run("import", self.plan_path, [MODULE.LEGACY_TARGET])

    def test_inspection_has_no_setters_and_checks_source(self):
        unreal, _, _, _ = self.fake_unreal()
        asset = FakeWave(self.new[0])
        MODULE.inspect_asset(unreal, asset, self.new[0])
        self.assertEqual(asset.writes, [])
        asset.source.source = "wrong-source.wav"
        with self.assertRaisesRegex(RuntimeError, "原生导入来源不同"):
            MODULE.inspect_asset(unreal, asset, self.new[0])

    def test_unowned_native_object_receives_no_setters(self):
        unreal, _, _, _ = self.fake_unreal()
        record = self.new[0]
        foreign = FakeWave(record)
        foreign.path += "_foreign"
        unreal.SoundFactory = lambda: SimpleNamespace(set_editor_property=lambda key, value: None)
        unreal.AssetImportTask = lambda: SimpleNamespace(set_editor_property=lambda key, value: None,
            get_objects=lambda: [foreign], get_editor_property=lambda key: [record["object_path"]])
        unreal.AssetToolsHelpers = SimpleNamespace(get_asset_tools=lambda: SimpleNamespace(import_asset_tasks=lambda tasks: None))
        with self.assertRaisesRegex(RuntimeError, "原生返回非自有目标"):
            MODULE.import_one(unreal, record, {"content": set(), "maps": set()})
        self.assertEqual(foreign.writes, [])

    def test_readback_never_imports_sets_or_saves(self):
        unreal, legacy, _, saves = self.fake_unreal()
        record = self.new[0]
        file = MODULE.target_file(record["target"])
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"existing-readback-target")
        asset = FakeWave(record)
        unreal.EditorAssetLibrary.does_asset_exist = lambda t: t in (record["target"], MODULE.LEGACY_TARGET)
        unreal.EditorAssetLibrary.load_asset = lambda t: legacy if t == MODULE.LEGACY_TARGET else asset
        with patch.object(MODULE, "import_one") as importer:
            result = self.execute(unreal, "readback", [record["target"]])
            importer.assert_not_called()
        self.assertEqual(result["saved"], [])
        self.assertEqual(len(result["assets"]), 1)
        self.assertEqual(saves + legacy.writes + asset.writes, [])

    def test_registered_new_target_is_rejected_before_import(self):
        unreal, legacy, _, saves = self.fake_unreal()
        unreal.EditorAssetLibrary.does_asset_exist = lambda t: True
        with patch.object(MODULE, "import_one") as importer:
            with self.assertRaisesRegex(RuntimeError, "新增目标已存在"):
                self.execute(unreal, "import")
            importer.assert_not_called()
        self.assertEqual(saves, [])
        self.assertEqual(legacy.writes, [])

    def test_partial_native_failure_preserves_real_saved_set(self):
        unreal, legacy, errors, saves = self.fake_unreal()
        selected = [a["target"] for a in self.new[:2]]
        with patch.object(MODULE, "import_one", side_effect=[FakeWave(self.new[0]), RuntimeError("原生导入失败")]):
            with self.assertRaisesRegex(RuntimeError, "原生导入失败"):
                self.execute(unreal, "import", selected)
        self.assertEqual(saves, selected[:1])
        self.assertIn(repr(selected[:1]), errors[-1])
        self.assertTrue(MODULE.target_file(selected[0]).is_file())
        self.assertFalse(MODULE.target_file(selected[1]).exists())
        self.assertEqual(legacy.writes, [])

    def test_changed_protected_montage_is_rejected(self):
        self.montage.write_bytes(b"changed-existing-montage")
        with self.assertRaisesRegex(RuntimeError, "受保护既有文件变化"):
            MODULE.check_inputs(self.plan)

    def test_commandlet_cannot_use_editor_host(self):
        unreal = SimpleNamespace(SystemLibrary=SimpleNamespace(get_command_line=lambda: "-run=PythonScript"))
        with self.assertRaisesRegex(RuntimeError, "不得声明为 editor"):
            MODULE.require_host(unreal, "editor")


if __name__ == "__main__":
    unittest.main()
