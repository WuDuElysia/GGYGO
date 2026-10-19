"""@file test_pyrios_ghost_fx.py
@brief 首残影静态契约、实际绘制拓扑、几何匹配与保存前失败边界。

只读既有准确源；Native/MCP 用受限假宿主记录调用，不操作用户 UE。
"""
import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import build_pyrios_ghost_fx as G
import nap_avatar_simple_material_plan as MP
import zzz_fx_niagara_ue as N
from build_nap_avatar_simple_materials import NapAvatarSimpleBuilder
from tests.test_zzz_mesh_fbx_import import array

ROOT = Path(__file__).resolve().parents[3]
SOURCES = Path("F:/AnimeStudio/Exports/ZZZ/Pyrois_SkillFX_Evidence/Prefabs")
PREFAB = SOURCES / (G.SOURCE_NAME + ".fx.json")
DEPENDENCY = SOURCES / (G.SOURCE_NAME + ".deps.v2.json")


class FakeMcp:
    """保留真实调用请求/结果形状，仅模拟必要原生读回，不连接工具。"""
    def __init__(self):
        self.calls = []
        self.emitters = {}
        self.system_data = {}
        self.system_path = None
        self.corrupt_renderer = False
        self.corrupt_bounds = False
        self.corrupt_binding = False
        self.force_compile = True

    def tool(self, full_name, **args):
        name = full_name.rsplit(".", 1)[-1]
        self.calls.append((name, copy.deepcopy(args)))
        result = None
        if name == "CreateNiagaraSystem":
            self.system_path = args["assetPath"] + "/" + args["assetName"] + "." + args["assetName"]
        elif name == "GetSystemSummary":
            result = {"emitters": [{"emitterName": "Fountain"}]}
        elif name == "AddEmitter":
            self.emitters[args["emitterName"]] = []
        elif name == "SetSystemData":
            self.system_data.update(json.loads(args["systemData"]["propertyValues"]))
        elif name == "GetSystemData":
            data = copy.deepcopy(self.system_data)
            if self.corrupt_bounds:
                data["bFixedBounds"] = False
            result = {"propertyValues": json.dumps(data)}
        elif name == "AddModule":
            result = {"moduleName": args["moduleAsset"]["refPath"].rsplit("/", 1)[-1]}
        elif name == "AddSetParametersModule":
            result = {"moduleName": "Set_" + str(len(self.calls))}
        elif name == "AddRenderer":
            renderers = self.emitters[args["newRendererLocation"]["emitterName"]]
            result = {"rendererIndex": len(renderers)}
            renderers.append({})
        elif name == "SetRendererData":
            ref = args["renderer"]
            self.emitters[ref["emitterName"]][ref["rendererIndex"]] = json.loads(args["rendererData"]["propertyValues"])
        elif name == "GetEmitterTopology":
            renderers = self.emitters[args["emitterRef"]["emitterName"]]
            result = {"renderers": [{"rendererIndex": i,
                "rendererClass": {"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"}} for i in range(len(renderers))]}
        elif name == "GetRendererData":
            ref = args["rendererRef"]
            data = copy.deepcopy(self.emitters[ref["emitterName"]][ref["rendererIndex"]])
            data.setdefault("bIsEnabled", True)
            for binding in N.EmitterMeshBuilder.BINDINGS:
                data[binding]["bBindingExistsOnSource"] = not self.corrupt_binding
                data[binding]["bIsCachedParticleValue"] = False
            if self.corrupt_renderer:
                data["SourceMode"] = "Particles"
            result = {"propertyValues": json.dumps(data)}
        elif name == "ForceCompile":
            result = {"bForceCompileRequested": self.force_compile, "error": ""}
        elif name == "ReadSystemState":
            result = {"systemPath": self.system_path, "error": "", "bCompilationPending": False,
                      "bVMAttributesEqual": True, "bSystemValid": True, "bNativeReady": True}
        elif name == "GetSystemCompileState":
            result = {"bIsCompiling": False, "bIsStale": False, "scripts": [],
                      "bHasErrors": False, "aggregateStatus": "UpToDate"}
        return {"returnValue": result}


class FakeSession:
    def __init__(self, targets):
        self.targets, self.created, self.saved = set(targets), set(), set()
        self.m = FakeMcp()
    def check_editor(self):
        pass
    def begin_create(self, path):
        if path not in self.targets or path in self.created:
            raise AssertionError("非本批准确 create-only 目标")
    def created_asset(self, path):
        self.created.add(path)
    def require_created(self, path):
        if path not in self.created:
            raise AssertionError("保存了非自有新包")
    def save(self, paths):
        for path in paths:
            self.require_created(path)
        self.saved.update(paths)


class FakeReadMcp(FakeMcp):
    """已存在资源的有限只读宿主；错误值可注入，不从构建过程生成答案。"""
    def __init__(self, plan):
        super().__init__()
        self.plan, self.missing = plan, set()
        self.pie = False
        self.system_path = plan["system"] + "." + plan["system"].rsplit("/", 1)[1]
        self.system_data = {"bFixedBounds": True, "FixedBounds": {
            "min": dict(zip("xyz", plan["fixed_bounds"]["min"])),
            "max": dict(zip("xyz", plan["fixed_bounds"]["max"])), "isValid": 1}}
        self.summary = {"systemName": plan["system"].rsplit("/", 1)[1], "emitters": []}
        self.topologies, self.module_values = {}, {}
        for spec in plan["specs"]:
            name = spec["name"]
            self.summary["emitters"].append({"emitterName": name, "bEnabled": True, "simTarget": "CPUSim"})
            self.emitters[name] = [N.EmitterMeshBuilder.renderer_properties(name, r) for r in spec["renderers"]]
            modules = []
            for index, (parameter, kind, expression) in enumerate(spec["emitter_spawn"]):
                module = "Assignment_" + str(index)
                modules.append({"moduleName": module, "enabled": True, "bIsSetParametersModule": True,
                    "inputs": [{"name": parameter, "type": {"classStructOrEnum": {"refPath": N.TYPES[kind]}},
                                "bIsDynamic": False}]})
                self.module_values[(name, module)] = {"moduleName": module, "inputs": [{"name": parameter,
                    "value": {"struct": {"refPath": N.HLSL}, "value": {"hlslExpression": expression}}}]}
            # 使用真实 getter 快照，避免由写入参数拼出预期读回而掩盖序列化差异。
            state_native = json.loads((Path(__file__).parent /
                "fixtures/pyrios_emitter_state_native.json").read_text(encoding="utf-8"))
            state_inputs = copy.deepcopy(state_native["topology_inputs"])
            self.module_values[(name, "EmitterState")] = {"moduleName": "EmitterState",
                "inputs": copy.deepcopy(state_native["actual_inputs"])}
            self.topologies[name] = {"emitterName": name, "bEnabled": True, "simTarget": "CPUSim",
                "emitterSpawnScript": {"scriptName": "EmitterSpawnScript", "modules": modules},
                "emitterUpdateScript": {"scriptName": "EmitterUpdateScript", "modules": [{
                    "moduleName": "EmitterState", "enabled": True, "bIsSetParametersModule": False,
                    "moduleScript": {"refPath": "/Niagara/Modules/Emitter/EmitterState.EmitterState"}, "inputs": state_inputs}]},
                "particleSpawnScript": {"scriptName": "ParticleSpawnScript", "modules": []},
                "particleUpdateScript": {"scriptName": "ParticleUpdateScript", "modules": []},
                "renderers": [{"rendererIndex": i, "rendererClass": {
                    "refPath": "/Script/Niagara.NiagaraMeshRendererProperties"}} for i in range(len(spec["renderers"]))]}
        self.native_state = {"systemPath": self.system_path, "error": "", "bCompilationPending": False,
                             "bVMAttributesEqual": True, "bSystemValid": True, "bNativeReady": True}
        self.compile_state = {"bIsCompiling": False, "bIsStale": False, "scripts": [],
                              "bHasErrors": False, "aggregateStatus": "UpToDate"}

    def tool(self, full_name, **args):
        if full_name not in G.ReadOnlyToolsets.TOOLS:
            raise AssertionError("只读宿主收到写入工具: " + full_name)
        name = full_name.rsplit(".", 1)[-1]
        if name == "IsPIERunning":
            result = self.pie
        elif name == "exists":
            result = args["path"] not in self.missing
        elif name == "GetSystemSummary":
            result = self.summary
        elif name == "GetEmitterTopology":
            result = self.topologies[args["emitterRef"]["emitterName"]]
        elif name == "GetEmitterData":
            result = {"propertyValues": json.dumps({"bLocalSpace": True, "SimTarget": "CPUSim",
                                                   "InterpolatedSpawnMode": "RunUpdateScript"})}
        elif name == "GetModuleInputValues":
            ref = args["moduleRef"]
            result = self.module_values[(ref["emitterName"], ref["moduleName"])]
        elif name == "ReadSystemState":
            result = self.native_state
        elif name == "GetSystemCompileState":
            result = self.compile_state
        else:
            return super().tool(full_name, **args)
        self.calls.append((name, copy.deepcopy(args)))
        return {"returnValue": copy.deepcopy(result)}


class GhostReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = G.make_plan(PREFAB, DEPENDENCY, revision="pyrios_ghost_03_02_ue_r1")

    def setUp(self):
        self.m = FakeReadMcp(self.plan)
        self.native = SimpleNamespace(GeometryScript_AssetUtils=object(), GeometryScript_MeshQueries=object(),
                                      GeometryScript_Materials=object())
        # 本组隔离原生只读合同；转换文件合同由 MeshSourceTests 独立严格验证。
        source_format = patch.object(G, "verify_mesh_fbx", return_value={"source_format_verified": True})
        source_format.start()
        self.addCleanup(source_format.stop)

    def verify_niagara(self):
        return N.EmitterMeshBuilder(mcp=G.ReadOnlyToolsets(self.m)).verify_system(
            self.plan["system"], self.plan["specs"], fixed_bounds=self.plan["fixed_bounds"])

    def test_existing_resource_readback_without_creating_compiling_or_saving(self):
        material = {"material_binding_readback_verified": True, "bindings": self.plan["material_plan"]["bindings"]}
        with patch.object(G, "read_geometry", return_value={"verified": True}) as geometry, \
                patch.object(NapAvatarSimpleBuilder, "verify", return_value=material) as materials, \
                patch.object(NapAvatarSimpleBuilder, "build") as build, patch.object(G, "AssetSession") as session, \
                patch.object(N.time, "sleep", side_effect=AssertionError("只读检查不得等待")):
            result = G.verify(self.plan, mcp=self.m, unreal=self.native)
        geometry.assert_called_once()
        materials.assert_called_once_with(self.plan["material_plan"])
        build.assert_not_called()
        session.assert_not_called()
        self.assertTrue(result["resource_readback_verified"])
        self.assertTrue(result["niagara"]["emitter_stack_readback_verified"])
        for key in ("cold_read_verified", "saved_package_bytes_verified", "action_integrated", "visual_verified"):
            self.assertFalse(result[key])
        names = {name for name, _ in self.m.calls}
        self.assertIn("ReadSystemState", names)
        self.assertIn("GetModuleInputValues", names)
        self.assertFalse(names & {"ForceCompile", "save_assets", "CreateNiagaraSystem", "SetStackInputData"})

    def test_missing_batch_or_pie_blocks_geometry_and_material_reads(self):
        for kind in ("missing", "pie", "unknown_pie"):
            with self.subTest(kind=kind):
                self.m = FakeReadMcp(self.plan)
                if kind == "missing":
                    self.m.missing.add(self.plan["targets"][0])
                else:
                    self.m.pie = True if kind == "pie" else None
                with patch.object(G, "read_geometry") as geometry, patch.object(NapAvatarSimpleBuilder, "verify") as materials, \
                        self.assertRaises(RuntimeError):
                    G.verify(self.plan, mcp=self.m, unreal=self.native)
                geometry.assert_not_called()
                materials.assert_not_called()
                self.assertNotIn("GetSystemSummary", [name for name, _ in self.m.calls])

    def test_wrong_material_binding_blocks_niagara_readback(self):
        with patch.object(G, "read_geometry", return_value={"verified": True}), \
                patch.object(NapAvatarSimpleBuilder, "verify", return_value={
                    "material_binding_readback_verified": True, "bindings": {}}), self.assertRaisesRegex(RuntimeError, "源槽绑定"):
            G.verify(self.plan, mcp=self.m, unreal=self.native)
        self.assertNotIn("GetSystemSummary", [name for name, _ in self.m.calls])

    def test_stale_compile_or_pending_native_ready_fails_without_repair(self):
        for state, change in (("compile", {"bIsStale": True}), ("native", {"bCompilationPending": True}),
                              ("native", {"bNativeReady": False}), ("native", {"bVMAttributesEqual": False}),
                              ("native", {"systemPath": "/Game/Wrong.Wrong"})):
            with self.subTest(change=change):
                self.m = FakeReadMcp(self.plan)
                (self.m.compile_state if state == "compile" else self.m.native_state).update(change)
                with patch.object(N.time, "sleep", side_effect=AssertionError("只读检查不得等待")), self.assertRaises(RuntimeError):
                    self.verify_niagara()
                self.assertNotIn("ForceCompile", [name for name, _ in self.m.calls])

    def test_disabled_wrong_pose_type_expression_or_particle_module_rejected(self):
        mutations = [lambda m: m.summary["emitters"][0].update(bEnabled=False),
                     lambda m: m.topologies["GhostMesh"]["emitterSpawnScript"]["modules"][0]["inputs"][0].update(
                         type={"classStructOrEnum": {"refPath": N.TYPES["Vector"]}}),
                     lambda m: m.module_values[("GhostMesh", "Assignment_0")]["inputs"][0]["value"]["value"].update(
                         hlslExpression="float3(0,0,0)"),
                     lambda m: m.topologies["GhostMesh"]["particleSpawnScript"]["modules"].append({"moduleName": "SpawnBurst"}),
                     lambda m: m.module_values[("GhostMesh", "EmitterState")]["inputs"][1]["value"]["value"].update(
                         enumName="ENiagara_EmitterStateOptions::NewEnumerator1")]
        for change in mutations:
            self.m = FakeReadMcp(self.plan)
            change(self.m)
            with self.assertRaises(RuntimeError):
                self.verify_niagara()

    def test_emitter_state_requires_exact_native_enum_identity(self):
        fixture = Path(__file__).parent / "fixtures/pyrios_emitter_state_native.json"
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(),
            "314e0c346eed480544aa311f99aedbde234ed5126a561488ced2e18a190f17b5")
        mutations = (
            {"enumName": "NewEnumerator1"},
            {"enumName": "OtherEnum::NewEnumerator1"},
            {"enumName": "ENiagaraEmitterLifeCycleMode::NewEnumerator0"},
            {"enum": {"refPath": "/Game/Wrong.Wrong"}},
        )
        for change in mutations:
            with self.subTest(change=change):
                self.m = FakeReadMcp(self.plan)
                self.m.module_values[("GhostMesh", "EmitterState")]["inputs"][0]["value"]["value"].update(change)
                with self.assertRaisesRegex(RuntimeError, "GhostMesh.Life Cycle Mode"):
                    self.verify_niagara()

    def test_actual_bounds_renderer_mode_and_binding_fail_readback(self):
        for corruption in ("corrupt_bounds", "corrupt_renderer", "corrupt_binding"):
            with self.subTest(corruption=corruption):
                self.m = FakeReadMcp(self.plan)
                setattr(self.m, corruption, True)
                with self.assertRaises(RuntimeError):
                    self.verify_niagara()
        self.m = FakeReadMcp(self.plan)
        self.m.emitters["GhostMesh"][0]["bIsEnabled"] = False
        with self.assertRaisesRegex(RuntimeError, "bIsEnabled"):
            self.verify_niagara()

    def test_readonly_transport_rejects_mutation_before_delegation(self):
        client = G.ReadOnlyToolsets(self.m)
        for tool in (N.COMPILE + "ForceCompile", N.NS + "CreateNiagaraSystem", N.NS + "SetStackInputData", N.AS + "save_assets"):
            with self.assertRaisesRegex(ValueError, "拒绝修改"):
                client.tool(tool)
        self.assertEqual(self.m.calls, [])
        with self.assertRaisesRegex(ValueError, "自有 create-only session"):
            N.EmitterMeshBuilder(mcp=client).build_system(self.plan["system"], self.plan["specs"], fixed_bounds=self.plan["fixed_bounds"])
        self.assertEqual(self.m.calls, [])

    def test_invalid_source_and_host_identity_fail_before_tools(self):
        p = copy.deepcopy(self.plan)
        p["source_files"][next(iter(p["source_files"]))] = "0" * 64
        with self.assertRaisesRegex(ValueError, "源文件已改变"):
            G.verify(p, mcp=self.m, unreal=self.native)
        self.assertEqual(self.m.calls, [])
        with patch.object(G, "NativeToolsets") as transport, self.assertRaisesRegex(ValueError, "准确 Editor PID"):
            G.verify_in_editor(self.plan, unreal=self.native, expected_editor_pid=os.getpid() + 1)
        transport.assert_not_called()

    def test_native_pending_result_retained_for_assigned_host(self):
        calls, pending = [], SimpleNamespace(is_complete=False, error="", value="")
        def execute(*args):
            calls.append(args)
            return pending
        self.native.Paths = SimpleNamespace(project_dir=lambda: str(ROOT))
        self.native.ToolsetRegistry = SimpleNamespace(execute_tool=execute)
        with self.assertRaisesRegex(RuntimeError, "尚未同步完成") as caught:
            G.verify_in_editor(self.plan, unreal=self.native, expected_editor_pid=os.getpid())
        self.assertIs(caught.exception.ghost_client.pending, pending)
        self.assertEqual(len(calls), 1)


class GhostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = G.make_plan(PREFAB, DEPENDENCY, revision="pyrios_ghost_03_02_ue_r1")

    def plan_copy(self):
        return copy.deepcopy(self.plan)

    def emitter_build(self, session):
        return N.EmitterMeshBuilder(session).build_system(self.plan["system"], self.plan["specs"],
                                                        fixed_bounds=self.plan["fixed_bounds"])

    def test_original_duplicate_slots_are_four_physical_renderers(self):
        p = self.plan
        self.assertEqual([(m["slot"], m["submesh"], m["pid"]) for m in p["source_contract"]["materials"]],
                         [(0, 0, MP.MATERIAL_PID), (1, 0, MP.MATERIAL_PID)])
        session = FakeSession([p["system"]])
        self.emitter_build(session)
        actual = session.m.emitters["GhostMesh"]
        self.assertEqual(len(actual), 4)
        self.assertEqual([r["SortOrderHint"] for r in actual], [0, 1, 2, 3])
        binding = p["material_plan"]["bindings"][MP.MATERIAL_PID]
        self.assertEqual([r["OverrideMaterials"][0]["ExplicitMat"].split(".")[0] for r in actual],
                         [binding["outline"], binding["surface"], binding["outline"], binding["surface"]])
        self.assertTrue(all(len(r["Meshes"]) == len(r["OverrideMaterials"]) == 1 and r["SourceMode"] == "Emitter" for r in actual))

    def test_emitter_mode_has_no_particle_spawn_or_fake_lifetime(self):
        session = FakeSession([self.plan["system"]])
        self.emitter_build(session)
        calls = session.m.calls
        modules = [a["moduleAsset"]["refPath"] for n, a in calls if n == "AddModule"]
        self.assertEqual(modules, ["/Niagara/Modules/Emitter/EmitterState.EmitterState"])
        parameters = [p["variable"]["name"] for n, a in calls if n == "AddSetParametersModule" for p in a["parameters"]]
        self.assertTrue(parameters and all(n.startswith("Emitter.") for n in parameters))
        inputs = [a["stackInputRef"]["inputNameStack"][0] for n, a in calls if n == "SetStackInputData"]
        self.assertNotIn("Loop Duration", inputs)
        self.assertNotIn("Spawn Count", inputs)
        self.assertEqual(self.plan["ownership"]["source_stop"], "unresolved")
        self.assertFalse(self.plan["ownership"]["auto_finish"])

    def test_source_mode_bindings_and_bounds_are_verified_before_save(self):
        for corruption in ("corrupt_renderer", "corrupt_bounds", "corrupt_binding"):
            with self.subTest(corruption=corruption):
                session = FakeSession([self.plan["system"]])
                setattr(session.m, corruption, True)
                with self.assertRaises(RuntimeError):
                    self.emitter_build(session)
                self.assertEqual(session.saved, set())
                self.assertEqual(session.created, {self.plan["system"]})

    def test_compile_request_failure_is_not_saved_or_ready(self):
        session = FakeSession([self.plan["system"]])
        session.m.force_compile = False
        with self.assertRaisesRegex(RuntimeError, "full compile"):
            self.emitter_build(session)
        self.assertEqual(session.saved, set())

    def test_missing_pose_or_draw_resource_rejected_before_editor_mutation(self):
        mutations = [lambda s: s[0]["emitter_spawn"].pop(),
                     lambda s: s[0]["renderers"].pop(),
                     lambda s: s[0]["renderers"][2].update(source_slot=0),
                     lambda s: s[0]["renderers"][1].update(material=""),
                     lambda s: s[0].update(source_mode="Particles"),
                     lambda s: s[0].update(bursts=[[0, 1]])]
        for change in mutations:
            specs = copy.deepcopy(self.plan["specs"])
            change(specs)
            session = FakeSession([self.plan["system"]])
            with self.assertRaises(ValueError):
                N.EmitterMeshBuilder(session).build_system(self.plan["system"], specs, fixed_bounds=self.plan["fixed_bounds"])
            self.assertEqual(session.m.calls, [])

    def test_invalid_bounds_rejected_before_editor_mutation(self):
        for bounds in (None, {"min": [0, 0, 0], "max": [0, 1, 1]},
                       {"min": [float("nan"), 0, 0], "max": [1, 1, 1]}):
            session = FakeSession([self.plan["system"]])
            with self.assertRaises(ValueError):
                N.EmitterMeshBuilder(session).build_system(self.plan["system"], self.plan["specs"], fixed_bounds=bounds)
            self.assertEqual(session.m.calls, [])

    def test_resource_does_not_gain_action_or_full_prefab_permission(self):
        for key, value in (("mode", "action"), ("system", "/Game/Other/Existing")):
            p = self.plan_copy()
            p[key] = value
            session = FakeSession(p["targets"])
            with self.assertRaises(ValueError):
                G.build(p, session, unreal=object())
            self.assertEqual(session.m.calls, [])
        self.assertEqual(self.plan["limitations"]["full_prefab_preflight"], "not performed")
        self.assertEqual(self.plan["source_contract"]["transform"]["root_actor_binding"], "unresolved")
        self.assertFalse(self.plan["source_contract"]["transform"]["animated"])

    def test_source_guard_fails_before_any_native_calls(self):
        p = self.plan_copy()
        key = next(iter(p["source_files"]))
        p["source_files"][key] = "0" * 64
        session = FakeSession(p["targets"])
        with self.assertRaisesRegex(ValueError, "源文件已改变"):
            G.build(p, session, unreal=object())
        self.assertEqual(session.m.calls, [])

    def test_missing_native_or_shared_session_rejected_before_import(self):
        native = SimpleNamespace(GeometryScript_AssetUtils=object(), GeometryScript_MeshQueries=object(), GeometryScript_Materials=object())
        sessions = [FakeSession(self.plan["targets"]), FakeSession(self.plan["targets"][:-1]), FakeSession(self.plan["targets"])]
        sessions[-1].created.add(self.plan["targets"][0])
        for session, ue in zip(sessions, (None, native, native)):
            with patch.object(G.IA, "apply_imports") as imported, self.assertRaises(ValueError):
                G.build(self.plan, session, unreal=ue)
            imported.assert_not_called()
            self.assertEqual(session.m.calls, [])
        session = FakeSession(self.plan["targets"])
        with patch.object(G.IA, "apply_imports") as imported, self.assertRaisesRegex(ValueError, "接口不存在"):
            G.build(self.plan, session, unreal=object())
        imported.assert_not_called()

    def test_geometry_failure_blocks_materials_and_ns(self):
        session = FakeSession(self.plan["targets"])
        native = SimpleNamespace(GeometryScript_AssetUtils=object(), GeometryScript_MeshQueries=object(), GeometryScript_Materials=object())
        with patch.object(G, "verify_mesh_fbx", return_value={"source_format_verified": True}), \
                patch.object(G.IA, "apply_imports"), patch.object(G, "read_geometry", side_effect=RuntimeError("native corner mismatch")), \
                patch.object(NapAvatarSimpleBuilder, "build") as materials, self.assertRaisesRegex(RuntimeError, "corner mismatch"):
            G.build(self.plan, session, unreal=native)
        materials.assert_not_called()
        self.assertEqual(session.m.calls, [])

    def test_material_failure_blocks_ns(self):
        session = FakeSession(self.plan["targets"])
        native = SimpleNamespace(GeometryScript_AssetUtils=object(), GeometryScript_MeshQueries=object(), GeometryScript_Materials=object())
        with patch.object(G, "verify_mesh_fbx", return_value={"source_format_verified": True}), \
                patch.object(G.IA, "apply_imports"), patch.object(G, "read_geometry", return_value={"verified": True}), \
                patch.object(NapAvatarSimpleBuilder, "build", side_effect=RuntimeError("native compile errors")), \
                self.assertRaisesRegex(RuntimeError, "compile errors"):
            G.build(self.plan, session, unreal=native)
        self.assertEqual(session.m.calls, [])

    def test_material_hdr_exact_textures_and_depth_coverage_remain_explicit(self):
        material = self.plan["material_plan"]
        self.assertEqual(set(material["textures"]), set(G.TEXTURE_PIDS))
        specs = material["materials"]
        self.assertTrue(all(m["properties"]["BlendMode"] == "BLEND_Masked" and m["properties"]["bUsedWithNiagaraMeshParticles"] for m in specs))
        self.assertEqual(specs[0]["shader"]["coverage"], specs[1]["shader"]["coverage"])
        self.assertGreater(max(specs[0]["params"]["_ScreenColor"]["value"]), 1)
        self.assertEqual(specs[1]["shader"]["face_mask"], "back_faces_only")
        self.assertFalse(material["equivalence"]["source_runtime_certified"])
        self.assertEqual(material["equivalence"]["source_outputs"], ["SV_Target0", "SV_Target1", "SV_Target2", "SV_Target3"])

    def test_dynamic_source_inputs_are_not_public_ue_tuning(self):
        for name in ("_EntityInfo", "_DitherEffectAlpha", "Fade", "RootTRS", "Age", "Stop"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "禁止"):
                G.make_plan(PREFAB, DEPENDENCY, revision="test", ue_parameters={name: 0})

    def test_cli_rejects_legacy_source_and_has_no_apply_mode(self):
        args = [sys.executable, "-B", str(ROOT / "AAADocs/Scripts/build_pyrios_ghost_fx.py"),
                str(PREFAB), str(DEPENDENCY), "--revision", "pyrios_ghost_03_02_ue_r1"]
        result = subprocess.run(args, capture_output=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(result.returncode, 1, result.stderr.decode("utf-8"))
        failed = json.loads(result.stdout)
        self.assertFalse(failed["resource_planned"])
        self.assertIn("规范角点转换合同", failed["error"])
        refused = subprocess.run(args + ["--apply"], capture_output=True)
        self.assertEqual(refused.returncode, 2)
        self.assertIn(b"unrecognized arguments", refused.stderr)

    def test_existing_niagara_paths_unchanged_except_optional_save_gate(self):
        baseline = ROOT / "Saved/Codex/PyriosGhostResourceTools_20261010_R1/baseline/zzz_fx_niagara_ue.py"
        old = ast.parse(baseline.read_text(encoding="utf-8-sig"))
        new = ast.parse(Path(N.__file__).read_text(encoding="utf-8-sig"))
        new.body = [n for n in new.body if not isinstance(n, ast.ClassDef) or n.name != "EmitterMeshBuilder"]
        builder = next(n for n in new.body if isinstance(n, ast.ClassDef) and n.name == "NiagaraBuilder")
        finish = next(n for n in builder.body if isinstance(n, ast.FunctionDef) and n.name == "finish_compile")
        finish.args.args.pop()
        finish.args.defaults.pop()
        finish.body = [n for n in finish.body if not isinstance(n, ast.If) or not isinstance(n.test, ast.Compare)
                       or not isinstance(n.test.left, ast.Name) or n.test.left.id != "before_save"]
        self.assertEqual(ast.dump(new, include_attributes=False), ast.dump(old, include_attributes=False))


class MeshSourceTests(unittest.TestCase):
    """文件 fixture 仅是四顶点合成数据，不生成真实角色转换产物。"""
    def setUp(self):
        base = ROOT / "Saved/Codex/FXTestTemp"
        base.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.mesh = {"m_Name": "Corners", "m_VertexCount": 4,
            "m_Vertices": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "m_Indices": [0, 1, 2, 0, 2, 3], "m_SubMeshes": [{"indexCount": 6}],
            "m_Normals": [1, 0, 0, 0, 1, 0, 0, 0, 1, -1, 0, 0],
            "m_Colors": [1, 0, 0, 0, 0, 1, 0, .2, 0, 0, 1, .5, 1, 1, 1, 1],
            "m_UV0": [.1, .2, .3, .4, .5, .6, .7, .8],
            "m_UV1": [.8, .7, .6, .5, .4, .3, .2, .1],
            "m_UV2": [.9, .1, .8, .2, .7, .3, .6, .4]}
        self.json_file = self.folder / "fixture.json"
        self.fbx_file = self.folder / "fixture.fbx"
        self.json_file.write_text(json.dumps(self.mesh), encoding="utf-8")

    def plan_for(self, text):
        self.fbx_file.write_bytes(text.encode("utf-8"))
        return {"source_contract": {"mesh": {"source_json": str(self.json_file)}},
            "source_files": {str(self.json_file): G.sha(self.json_file)},
            "imports": {"entries": {G.MESH_PID: {"source": str(self.fbx_file),
                "identity": {"source_sha256": G.sha(self.fbx_file)}}}}}

    def test_canonical_all_corner_layers_accept_bom_and_crlf_without_writes(self):
        text = G.FBX.build(self.mesh)
        plan = self.plan_for("\ufeff" + text.replace("\n", "\r\n"))
        before = [(p.stat().st_mtime_ns, G.sha(p)) for p in (self.json_file, self.fbx_file)]
        result = G.verify_mesh_fbx(plan)
        self.assertTrue(result["source_format_verified"])
        self.assertFalse(result["geometry_native_verified"])
        self.assertEqual(result["canonical_text_sha256"], hashlib.sha256(text.encode("utf-8")).hexdigest())
        self.assertEqual(before, [(p.stat().st_mtime_ns, G.sha(p)) for p in (self.json_file, self.fbx_file)])

    def test_nonstandard_mapping_and_incomplete_normals_rejected(self):
        text = G.FBX.build(self.mesh)
        for broken in (text.replace('MappingInformationType: "ByPolygonVertex"',
                                    'MappingInformationType: "ByControlPoint"'),
                       text.replace("Normals: *18", "Normals: *12")):
            with self.assertRaisesRegex(ValueError, "规范角点转换合同"):
                G.verify_mesh_fbx(self.plan_for(broken))

    def test_relabelled_uv_layer_or_wrong_corner_index_rejected(self):
        text = G.FBX.build(self.mesh)
        for broken in (text.replace('Name: "UVChannel_3"', 'Name: "UVChannel_2"'),
                       text.replace("a: 2,1,0,3,2,0", "a: 0,1,2,0,2,3")):
            self.assertNotEqual(broken, text)
            with self.assertRaisesRegex(ValueError, "规范角点转换合同"):
                G.verify_mesh_fbx(self.plan_for(broken))

    def test_same_read_source_identity_must_match_before_conversion(self):
        plan = self.plan_for(G.FBX.build(self.mesh))
        for stream in ("json", "fbx"):
            broken = copy.deepcopy(plan)
            if stream == "json":
                broken["source_files"][str(self.json_file)] = "0" * 64
            else:
                broken["imports"]["entries"][G.MESH_PID]["identity"]["source_sha256"] = "0" * 64
            with patch.object(G.FBX, "build") as converted, self.assertRaisesRegex(ValueError, "已改变"):
                G.verify_mesh_fbx(broken)
            converted.assert_not_called()

    def test_explicit_winding_must_match_file_and_legacy_factory_matrix_model(self):
        self.mesh["m_SubMeshes"][0]["baseVertex"] = 0
        self.json_file.write_text(json.dumps(self.mesh), encoding="utf-8")
        channels, expected = G.geometry_corners(self.mesh)
        self.assertEqual(channels, [0, 1, 2])
        for reverse in (False, True):
            text = G.FBX.build(self.mesh, reverse_winding=reverse)
            plan = self.plan_for(text)
            plan["mesh_winding"] = "reflected" if reverse else "source"
            self.assertTrue(G.verify_mesh_fbx(plan)["source_format_verified"])
            plan["mesh_winding"] = "source" if reverse else "reflected"
            with self.assertRaisesRegex(ValueError, "规范角点转换合同"):
                G.verify_mesh_fbx(plan)
            positions, normals, colors = array(text, "Vertices"), array(text, "Normals"), array(text, "Colors")
            points = [k if k >= 0 else -k - 1 for k in array(text, "PolygonVertexIndex", int)]
            layers = re.findall(r"LayerElementUV:\s*\d+\s*\{(.*?)\n\t\t\}", text, re.S)
            uv_data = [(array(layer, "UV"), array(layer, "UVIndex", int)) for layer in layers]
            corners = []
            for corner, point in enumerate(points):
                p, n = positions[point * 3:point * 3 + 3], normals[corner * 3:corner * 3 + 3]
                # 只建模已证工厂坐标/角点消费，不声称执行了原生导入。
                corners.append({"position": [p[0], p[2], p[1]], "normal": [n[0], n[2], n[1]],
                    "color": colors[corner * 4:corner * 4 + 4],
                    "uv": [[values[indices[corner] * 2], 1 - values[indices[corner] * 2 + 1]]
                           for values, indices in uv_data]})
            triangles = [corners[i:i + 3] for i in range(0, len(corners), 3)]
            if reverse:
                with self.assertRaisesRegex(RuntimeError, "绕序"):
                    G.compare_geometry(expected, triangles)
            else:
                self.assertEqual(G.compare_geometry(expected, triangles)["triangles"], 2)
        with self.assertRaisesRegex(ValueError, "需要明确转换 FBX"):
            G.make_plan(PREFAB, DEPENDENCY, revision="winding_fixture", mesh_winding="source")

    def test_explicit_mesh_source_is_preserved_in_plan_identity_and_validation(self):
        self.fbx_file.write_text("synthetic plan input, not admitted geometry", encoding="utf-8")
        revision = "mesh_source_fixture"
        old = G.make_plan(PREFAB, DEPENDENCY, revision=revision)
        plan = G.make_plan(PREFAB, DEPENDENCY, revision=revision, mesh_source=self.fbx_file, mesh_winding="source")
        item = plan["imports"]["entries"][G.MESH_PID]
        self.assertEqual(plan["mesh_source"], str(self.fbx_file.resolve()))
        self.assertEqual(item["source"], plan["mesh_source"])
        self.assertEqual(plan["mesh_winding"], "source")
        self.assertNotEqual(item["path"], old["imports"]["entries"][G.MESH_PID]["path"])
        self.assertNotEqual(plan["system"], old["system"])
        self.assertEqual(G.validate_plan(plan), plan)
        tampered = copy.deepcopy(plan)
        tampered.pop("mesh_source")
        with self.assertRaisesRegex(ValueError, "需要明确转换 FBX"):
            G.validate_plan(tampered)
        tampered = copy.deepcopy(plan)
        tampered.pop("mesh_winding")
        with self.assertRaisesRegex(ValueError, "完整资源计划"):
            G.validate_plan(tampered)

    def test_explicit_mesh_revision_creates_disjoint_batch_without_changing_sources(self):
        old = G.make_plan(PREFAB, DEPENDENCY, revision="batch_old")
        new = G.make_plan(PREFAB, DEPENDENCY, revision="batch_new", mesh_revision="mesh_new")
        self.assertEqual(new["source_files"], old["source_files"])
        self.assertEqual(new["source_contract"], old["source_contract"])
        self.assertEqual(new["ue_parameters"], old["ue_parameters"])
        self.assertTrue(set(old["targets"]).isdisjoint(new["targets"]))
        self.assertEqual(len(new["targets"]), 9)
        self.assertNotIn("mesh_revision", old)
        self.assertEqual(G.validate_plan(old), old)
        self.assertEqual(G.validate_plan(new), new)
        tampered = copy.deepcopy(new)
        tampered.pop("mesh_revision")
        with self.assertRaisesRegex(ValueError, "完整资源计划"):
            G.validate_plan(tampered)

    def test_invalid_explicit_mesh_revision_is_rejected_before_source_access(self):
        for value in ("", " ", 42):
            with self.subTest(value=value), patch.object(G, "read") as source_read:
                with self.assertRaisesRegex(ValueError, "网格资源版本"):
                    G.make_plan(PREFAB, DEPENDENCY, revision="new", mesh_revision=value)
                source_read.assert_not_called()

    def test_real_legacy_fbx_rejected_before_import_or_readonly_native_calls(self):
        plan = G.make_plan(PREFAB, DEPENDENCY, revision="pyrios_ghost_03_02_ue_r1")
        native = SimpleNamespace(GeometryScript_AssetUtils=object(), GeometryScript_MeshQueries=object(),
                                 GeometryScript_Materials=object())
        session = FakeSession(plan["targets"])
        with patch.object(G.IA, "apply_imports") as imported, patch.object(G, "read_geometry") as geometry, \
                self.assertRaisesRegex(ValueError, "规范角点转换合同"):
            G.build(plan, session, unreal=native)
        imported.assert_not_called()
        geometry.assert_not_called()
        self.assertEqual(session.created, set())
        self.assertEqual(session.saved, set())
        self.assertEqual(session.m.calls, [])
        reader = FakeReadMcp(plan)
        with self.assertRaisesRegex(ValueError, "规范角点转换合同"):
            G.verify(plan, mcp=reader, unreal=native)
        self.assertEqual(reader.calls, [])


class EmitterBindingTests(unittest.TestCase):
    """真实原生历史快照只作校验回归夹具，不代替新宿主的资产或视觉验收。"""
    def setUp(self):
        path = Path(__file__).parent / "fixtures/pyrios_emitter_binding_native.json"
        self.actual = json.loads(path.read_text(encoding="utf-8"))["bindings"]
        renderer = {"sort": 0, "mesh": "/Game/Test/Mesh", "material": "/Game/Test/Material"}
        self.expected = {key: value for key, value in
            N.EmitterMeshBuilder.renderer_properties("GhostMesh", renderer).items()
            if key in N.EmitterMeshBuilder.BINDINGS}
        for value in self.expected.values():
            value.update(bBindingExistsOnSource=True, bIsCachedParticleValue=False)

    def test_native_display_cache_and_actual_emitter_binding_remain_distinct(self):
        N.NiagaraBuilder.verify_properties(self.expected, self.actual, "GhostMesh")

    def test_wrong_scope_dataset_or_missing_source_binding_is_rejected(self):
        changes = ({"rootName": "Wrong"}, {"dataSetName": "Wrong"},
            {"paramMapVariable": {"name": "Emitter.GhostPosition"}},
            {"cachedDisplayName": "GhostMesh.GhostPosition"},
            {"bindingSourceMode": "ImplicitFromSource"},
            {"bBindingExistsOnSource": False}, {"bIsCachedParticleValue": True})
        for change in changes:
            with self.subTest(change=change):
                actual = copy.deepcopy(self.actual)
                actual["PositionBinding"].update(change)
                with self.assertRaisesRegex(RuntimeError, "renderer value mismatch"):
                    N.NiagaraBuilder.verify_properties(self.expected, actual, "GhostMesh")


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.triangle = [{"position": p, "normal": [0, 0, 1], "color": [.5, .25, .75, 1],
                          "uv": [[0, 0], [.2, .3], [.4, .5]]} for p in ([0, 0, 0], [1, 0, 0], [0, 1, 0])]

    def test_real_corner_matching_accepts_cyclic_order_and_quantized_rgba(self):
        native = copy.deepcopy(self.triangle[1:] + self.triangle[:1])
        for corner in native:
            corner["color"][0] = 128 / 255
        result = G.compare_geometry([self.triangle], [native])
        self.assertEqual(result["corners"], 3)
        self.assertGreater(result["max_color_error"], 0)

    def test_duplicate_triangle_multiplicity_is_preserved(self):
        result = G.compare_geometry([self.triangle, self.triangle], [self.triangle, self.triangle])
        self.assertEqual(result["triangles"], 2)
        with self.assertRaisesRegex(RuntimeError, "数量"):
            G.compare_geometry([self.triangle, self.triangle], [self.triangle])

    def test_wrong_winding_or_uv2_color_normal_and_nonfinite_are_rejected(self):
        changes = [lambda t: t.reverse(), lambda t: t[0]["uv"][2].__setitem__(0, .8),
                   lambda t: t[1]["color"].__setitem__(0, 0), lambda t: t[2].update(normal=[0, 1, 0]),
                   lambda t: t[0]["position"].__setitem__(0, float("nan"))]
        for change in changes:
            native = copy.deepcopy(self.triangle)
            change(native)
            with self.assertRaises((RuntimeError, ValueError)):
                G.compare_geometry([self.triangle], [native])


class NativeTransportTests(unittest.TestCase):
    def test_same_host_registry_result_preserves_void_bool_and_out_fields(self):
        calls = []
        payload = {"returnValue": None, "rendererIndex": 3}
        def execute(toolset, method, arguments):
            calls.append((toolset, method, json.loads(arguments)))
            return SimpleNamespace(is_complete=True, error="", value=json.dumps(payload))
        native = SimpleNamespace(ToolsetRegistry=SimpleNamespace(execute_tool=execute))
        client = G.NativeToolsets(native)
        value = client.tool(N.NS + "AddRenderer", rendererClass={"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"})
        self.assertEqual(value, payload)
        self.assertEqual(calls[0][:2], ("NiagaraToolsets.NiagaraToolset_System", "AddRenderer"))
        payload["returnValue"] = False
        self.assertIs(client.tool("EditorToolset.EditorAppToolset.IsPIERunning")["returnValue"], False)

    def test_pending_result_retained_without_retry_or_blocking_wait(self):
        calls = []
        pending = SimpleNamespace(is_complete=False, error="", value="")
        def execute(*args):
            calls.append(args)
            return pending
        native = SimpleNamespace(ToolsetRegistry=SimpleNamespace(execute_tool=execute))
        client = G.NativeToolsets(native)
        with self.assertRaisesRegex(RuntimeError, "尚未同步完成"):
            client.tool(N.NS + "GetSystemSummary")
        self.assertIs(client.pending, pending)
        with self.assertRaisesRegex(RuntimeError, "不重试"):
            client.tool(N.NS + "GetSystemSummary")
        self.assertEqual(len(calls), 1)

    def test_tool_errors_and_out_of_scope_names_are_rejected(self):
        calls = []
        def execute(*args):
            calls.append(args)
            return SimpleNamespace(is_complete=True, error="real tool error", value="")
        client = G.NativeToolsets(SimpleNamespace(ToolsetRegistry=SimpleNamespace(execute_tool=execute)))
        with self.assertRaises(ValueError):
            client.tool("OtherToolset.delete_all")
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(RuntimeError, "real tool error"):
            client.tool(N.NS + "GetSystemSummary")
        self.assertEqual(len(calls), 1)

    def test_wrong_editor_pid_rejected_before_host_access(self):
        plan = G.make_plan(PREFAB, DEPENDENCY, revision="pid_guard")
        with patch.object(G, "build") as built, self.assertRaisesRegex(ValueError, "准确 Editor PID"):
            G.build_in_editor(plan, unreal=object(), approved_targets=plan["targets"], expected_editor_pid=os.getpid() + 1)
        built.assert_not_called()

    def test_build_error_keeps_real_session_for_partial_save_and_pending_handoff(self):
        plan = G.make_plan(PREFAB, DEPENDENCY, revision="failure_handoff")
        native = SimpleNamespace(Paths=SimpleNamespace(project_dir=lambda: str(ROOT)), ToolsetRegistry=object())
        session = FakeSession(plan["targets"])
        session.m.pending = SimpleNamespace(is_complete=False)
        failed = RuntimeError("real native failure")
        with patch.object(G, "AssetSession", return_value=session), patch.object(G, "build", side_effect=failed):
            with self.assertRaisesRegex(RuntimeError, "real native failure") as caught:
                G.build_in_editor(plan, unreal=native, approved_targets=plan["targets"], expected_editor_pid=os.getpid())
        self.assertIs(caught.exception, failed)
        self.assertIs(caught.exception.ghost_session, session)
        self.assertIsNotNone(caught.exception.ghost_session.m.pending)
        constructor_error = RuntimeError("native preflight pending")
        with patch.object(G, "AssetSession", side_effect=constructor_error):
            with self.assertRaisesRegex(RuntimeError, "preflight pending") as caught:
                G.build_in_editor(plan, unreal=native, approved_targets=plan["targets"], expected_editor_pid=os.getpid())
        self.assertIsInstance(caught.exception.ghost_client, G.NativeToolsets)
        self.assertFalse(hasattr(caught.exception, "ghost_session"))


if __name__ == "__main__":
    unittest.main()
