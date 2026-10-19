"""按 zzz_fx_niagara 的发射器方案，在用户打开的 UE 编辑器里（经 MCP 的 NiagaraToolset）建 Niagara 系统。

    build_system(path, specs):
        仅创建审批清单内的新内容版本；已有系统保留，禁止删除重建
        CreateNiagaraSystem(DefaultSystem) → 删掉模板自带的 Fountain 发射器
        for spec: AddEmitter(CompletelyEmpty) → 发射器属性 → Emitter State / Spawn Burst / Spawn Rate
                  → 粒子生成 Set Parameters → Particle State + 粒子更新 Set Parameters → Mesh 渲染器
        原生 RequestCompile(true) / WaitForCompilationComplete 完整编译
        编译状态和原生运行就绪均通过后，才保存本批拥有的新包
"""
import json
import hashlib
import copy
import re
import sys
import time
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

NS = "NiagaraToolsets.NiagaraToolset_System."
COMPILE = "GGYGOEditor.GGYGONiagaraCompileLibrary."
AS = "editor_toolset.toolsets.asset.AssetTools."
TYPES = {"Float": "/Script/Niagara.NiagaraFloat", "Vector2": "/Script/CoreUObject.Vector2f", "Vector": "/Script/CoreUObject.Vector3f",
         "Vector4": "/Script/CoreUObject.Vector4f", "Quat": "/Script/CoreUObject.Quat4f",
         "LinearColor": "/Script/CoreUObject.LinearColor", "Position": "/Script/Niagara.NiagaraPosition"}
HLSL = "/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression"
EMPTY_EMITTER = "/Niagara/DefaultAssets/Templates/CascadeConversion/CompletelyEmpty.CompletelyEmpty"
DEFAULT_SYSTEM = "/Niagara/DefaultAssets/DefaultSystem.DefaultSystem"
ENUM = "/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum"
NORMAL01_SYSTEM = "/Game/Characters/Player/Pyrios/FX/Skill/NS_Eff_Pyrois_Attack_Normal_01_01_Trail"
NORMAL01_EMITTERS = tuple("root_Trail_rot_" + name for name in
                         ("HighLight", "light_edge", "Smoke_trail", "Smoke_Head", "bloom", "Shining")) + ("Smoke_Cone01__2_",)
FX_MESH_ROOT = "/Game/Characters/Shared/FX/ZZZ/Meshes/"
NORMAL01_MATERIAL_LAYERS = ("HighLight", "light_edge", "bloom", "Shining")


class NiagaraBuilder:
    def __init__(self, session):
        self.session = session
        self.m = session.m

    def ns(self, name, **kw):
        return self.m.tool(NS + name, **kw)["returnValue"]

    def loc(self, emitter="", script="", module="", inputs=None, renderer=-1):
        return {"system": self.sref, "emitterName": emitter, "scriptName": script, "moduleName": module,
                "rendererIndex": renderer, "inputNameStack": inputs or []}

    def set_input(self, emitter, script, module, name, value):
        self.ns("SetStackInputData", stackInputRef=self.loc(emitter, script, module, [name]), inputData=value)

    @staticmethod
    def hlsl(expr):
        return {"struct": {"refPath": HLSL}, "value": {"hlslExpression": expr}}

    @staticmethod
    def num(kind, v):
        return {"struct": {"refPath": "/Script/Niagara.Niagara%s" % kind}, "value": {"value": v}}

    @staticmethod
    def enum(asset, name, display):
        return {"struct": {"refPath": ENUM}, "value": {"enum": {"refPath": asset}, "enumName": name, "displayName": display}}

    def add_module(self, emitter, script, asset):
        return self.ns("AddModule", moduleLocationRef=self.loc(emitter, script), moduleAsset={"refPath": asset})["moduleName"]

    def set_params(self, emitter, script, entries):
        # A Niagara assignment node reads every input from its incoming map.
        # Chain/random/size expressions depend on preceding assignments, so each
        # ordered entry needs a distinct map write before the next input is read.
        for n, t, e in entries:
            params = [{"variable": {"name": n, "type": {"classStructOrEnum": {"refPath": TYPES[t]}}}}]
            mod = self.ns("AddSetParametersModule", moduleLocationRef=self.loc(emitter, script),
                          parameters=params)["moduleName"]
            self.set_input(emitter, script, mod, n, self.hlsl(e))

    def build_emitter(self, s):
        self.validate_spec(s)
        name = s["name"]
        self.ns("AddEmitter", system=self.sref, templateEmitter={"refPath": EMPTY_EMITTER}, emitterName=name)
        self.ns("SetEmitterData", emitter=self.loc(name), emitterData={"propertyValues": json.dumps(
            {"bLocalSpace": s["local_space"], "SimTarget": "CPUSim", "InterpolatedSpawnMode": "RunUpdateScript"})})
        self.set_params(name, "EmitterSpawnScript", s.get("emitter_spawn", []))
        es = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/EmitterState.EmitterState")
        self.set_input(name, "EmitterUpdateScript", es, "Life Cycle Mode", self.enum(
            "/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode", "NewEnumerator1", "Self"))
        self.set_input(name, "EmitterUpdateScript", es, "Loop Behavior", self.enum(
            "/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions",
            "NewEnumerator0" if s["loop"] else "NewEnumerator1", "Infinite" if s["loop"] else "Once"))
        self.set_input(name, "EmitterUpdateScript", es, "Loop Duration", self.num("Float", s["duration"]))
        if s["delay"] > 0:
            self.set_input(name, "EmitterUpdateScript", es, "UseLoopDelay", self.num("Bool", 1))
            self.set_input(name, "EmitterUpdateScript", es, "Loop Delay", self.num("Float", s["delay"]))
        self.set_params(name, "EmitterUpdateScript", s.get("emitter_update", []))
        for t, count in s["bursts"]:
            b = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/SpawnBurst_Instantaneous.SpawnBurst_Instantaneous")
            if isinstance(count, dict):
                # Burst event count is sampled by the native emission module,
                # independently from each spawned particle's stable randoms.
                value = self.hlsl("min(%d, int(floor(lerp(%s, %s, rand(1.0)))))" %
                                  (count["max"], repr(float(count["min"])), repr(float(count["max"] + 1))))
            else:
                value = self.num("Int32", count)
            self.set_input(name, "EmitterUpdateScript", b, "Spawn Count", value)
            self.set_input(name, "EmitterUpdateScript", b, "Spawn Time", self.num("Float", t))
        if s["rate"] > 0:
            r = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/SpawnRate.SpawnRate")
            self.set_input(name, "EmitterUpdateScript", r, "SpawnRate", self.num("Float", s["rate"]))
        if s.get("distance_rate", 0) > 0:
            r = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/SpawnPerUnit.SpawnPerUnit")
            # Latest native version takes spacing in cm, not particles/cm.
            self.set_input(name, "EmitterUpdateScript", r, "Spawn Spacing", self.num("Float", 100.0 / s["distance_rate"]))
            self.set_input(name, "EmitterUpdateScript", r, "Velocity Vector", self.hlsl("Transient.UEFX_EmissionVelocity"))
            self.set_input(name, "EmitterUpdateScript", r, "Module.Use Movement Tolerance", self.num("Bool", 0))
            self.set_input(name, "EmitterUpdateScript", r, "Module.Use Max Movement Threshold", self.num("Bool", 0))
        self.set_params(name, "ParticleSpawnScript", s["spawn"])
        self.add_module(name, "ParticleUpdateScript", "/Niagara/Modules/Update/Lifetime/ParticleState.ParticleState")
        self.set_params(name, "ParticleUpdateScript", s["update"])
        self.build_renderer(name, s["renderer"])

    @staticmethod
    def validate_spec(spec):
        rd = spec["renderer"]
        if rd["kind"] not in ("mesh", "sprite"):
            raise ValueError("Unsupported Niagara renderer: " + str(rd["kind"]))
        requirements = list(spec.get("requirements", [])) + list(rd.get("requirements", []))
        if requirements:
            raise ValueError("%s unresolved renderer requirements: %s" %
                             (spec["name"], ", ".join(requirements)))

    def build_renderer(self, name, rd):
        klass = "NiagaraMeshRendererProperties" if rd["kind"] == "mesh" else "NiagaraSpriteRendererProperties"
        r = self.ns("AddRenderer", newRendererLocation=self.loc(name),
                    rendererClass={"refPath": "/Script/Niagara." + klass})
        mat = rd["material"] + "." + rd["material"].rsplit("/", 1)[1]
        properties = {"SortOrderHint": rd["sort"], "SortMode": rd["sort_mode"]}
        if rd["kind"] == "mesh":
            mesh = rd["mesh"] + "." + rd["mesh"].rsplit("/", 1)[1]
            properties.update({"Meshes": [{"Mesh": mesh,
                      "PivotOffset": dict(zip("xyz", rd["pivot_offset"])),
                      "PivotOffsetSpace": rd["pivot_space"]}],
                      "bOverrideMaterials": True, "OverrideMaterials": [{"ExplicitMat": mat}]})
        else:
            # Native VF's B frame runs past the last grid row. The source shader
            # adapter builds both UVs from raw quad UV plus this float transport,
            # wrapping the next frame before UV creation even with clamp samplers.
            # Source StableRandom still uses DP2; this binding adds no new clock.
            properties.update({"Material": mat, "FacingMode": rd["facing_mode"], "Alignment": rd["alignment"],
                "PivotInUVSpace": dict(zip("xy", rd["pivot_uv"])),
                "SubImageSize": {"x": 1, "y": 1}, "bSubImageBlend": False,
                "bRemoveHMDRollInVR": False, "PixelCoverageMode": "Disabled"})
            properties["SubImageIndexBinding"] = self.attribute_binding(None)
            if rd["subuv"]["animated"]:
                properties["MaterialRandomBinding"] = self.attribute_binding("Particles.SubImageIndex")
        if rd["sort_attribute"] is not None:
            # UE 5.8 uses RootName/ParamMapVariable/DataSetName for live lookup;
            # BoundVariable is retained only for loading older editor assets.
            # The new mesh renderer's native Age binding already has Float type.
            attribute = rd["sort_attribute"]
            properties["CustomSortingBinding"] = self.attribute_binding(attribute)
        self.ns("SetRendererData", renderer=self.loc(name, renderer=r["rendererIndex"]), rendererData={"propertyValues": json.dumps(
            properties)})
        back = self.ns("GetRendererData", rendererRef=self.loc(name, renderer=r["rendererIndex"]))
        actual = json.loads(back["propertyValues"])
        self.verify_properties(properties, actual, name)

    @staticmethod
    def verify_properties(expected, actual, path):
        """Verify assigned values, including live bindings and nested geometry.

        Unreal exports nested USTRUCT member names in lower camel case and
        UObject paths as {refPath}; neither changes their assigned values.
        A cached display string alone does not prove an attribute is bound.
        """
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                raise RuntimeError("%s renderer readback type mismatch" % path)
            keys = {key.lower(): key for key in actual}
            for key, value in expected.items():
                if key.lower() not in keys:
                    raise RuntimeError("%s renderer readback missing %s" % (path, key))
                NiagaraBuilder.verify_properties(value, actual[keys[key.lower()]], path + "." + key)
        elif isinstance(expected, list):
            if not isinstance(actual, list) or len(expected) != len(actual):
                raise RuntimeError("%s renderer readback array mismatch" % path)
            for index, (left, right) in enumerate(zip(expected, actual)):
                NiagaraBuilder.verify_properties(left, right, path + "[%d]" % index)
        elif isinstance(expected, str) and isinstance(actual, dict) and set(actual) == {"refPath"}:
            NiagaraBuilder.verify_properties(expected, actual["refPath"], path)
        elif isinstance(expected, float) and isinstance(actual, (int, float)) and not isinstance(actual, bool):
            if actual != actual or abs(expected - actual) > 1e-5:
                raise RuntimeError("%s renderer value mismatch: %r != %r" % (path, expected, actual))
        elif expected != actual or isinstance(expected, bool) and not isinstance(actual, bool):
            raise RuntimeError("%s renderer value mismatch: %r != %r" % (path, expected, actual))

    @staticmethod
    def attribute_binding(attribute):
        # Retain the freshly constructed binding's native Float TypeDefHandle.
        # None explicitly disables a native stage replaced by the shader adapter.
        root = attribute.split(".", 1)[1] if attribute is not None else "None"
        return {"RootName": root, "ParamMapVariable": {"Name": attribute or "None"},
                # CachedDisplayName is FName, like the live binding names.
                "DataSetName": root, "CachedDisplayName": attribute or "None"}

    def build_system(self, path, specs):
        folder, name = path.rsplit("/", 1)
        if not specs:
            raise ValueError("Cannot build an empty FX system: " + path)
        for spec in specs:
            self.validate_spec(spec)
        self.session.begin_create(path)
        self.ns("CreateNiagaraSystem", assetName=name, assetPath=folder, templateSystem={"refPath": DEFAULT_SYSTEM})
        self.session.created_asset(path)
        self.sref = {"refPath": "%s.%s" % (path, name)}
        for e in self.ns("GetSystemSummary", system=self.sref)["emitters"]:
            self.ns("RemoveEmitter", emitterToRemove=self.loc(e["emitterName"]))
        for s in specs:
            self.build_emitter(s)
        return self.finish_compile(path)

    def finish_compile(self, path, timeout=50, before_save=None):
        """完整编译后检查真实布局及原生 Ready；失败或超时均不保存。"""
        self.session.require_created(path)
        self.session.check_editor()
        deadline = time.monotonic() + timeout
        native = self.m.tool(COMPILE + "ForceCompile", system=self.sref)["returnValue"]
        if not native["bForceCompileRequested"]:
            raise RuntimeError("Niagara full compile was not requested; package was not saved: %s %s" %
                               (path, native["error"]))
        while True:
            state = self.ns("GetSystemCompileState", system=self.sref)
            native = self.m.tool(COMPILE + "ReadSystemState", system=self.sref)["returnValue"]
            self.verify_native_compilation(path, native)
            if (not state["bIsCompiling"] and not native["bCompilationPending"]
                    and state["aggregateStatus"] != "Unknown"):
                self.verify_compile_state(path, state)
                if native["bNativeReady"]:
                    break
            if time.monotonic() >= deadline:
                raise RuntimeError("Niagara compile/native readiness is incomplete; package was not saved: %s %s" %
                                   (path, native))
            time.sleep(min(2, max(0, deadline - time.monotonic())))
        state["native"] = native
        if before_save is not None:
            before_save()
        self.session.save([path])
        return state

    @staticmethod
    def verify_native_compilation(path, native):
        expected_object = path + "." + path.rsplit("/", 1)[1]
        if native["systemPath"] != expected_object or native["error"]:
            raise RuntimeError("Niagara native compile readback failed; package was not saved: %s %s" % (path, native))
        # 在途编译的 VM 数据属于旧结果；只拒绝已收束的结构缺陷，保留原生 PSO 等待。
        if not native["bCompilationPending"]:
            if not native["bVMAttributesEqual"]:
                raise RuntimeError("Niagara System VM attributes mismatch; package was not saved: %s %s" % (path, native))
            if not native["bSystemValid"]:
                raise RuntimeError("Niagara System is invalid; package was not saved: %s %s" % (path, native))

    @staticmethod
    def verify_compile_state(path, state):
        """编译聚合状态不能覆盖单脚本错误或未收束结果。"""
        if state["bIsCompiling"] or state["bIsStale"]:
            raise RuntimeError("Niagara compile is incomplete; package was not saved: " + path)
        errors = [(x["emitterName"], x["scriptName"], ev["message"]) for x in state["scripts"]
                  for ev in x["compileEvents"] if ev["severity"] == "Error"]
        if errors:
            raise RuntimeError("Niagara 编译失败：\n" + "\n".join("%s %s\n%s" % e for e in errors[:4]))
        if state["bHasErrors"] or state["aggregateStatus"] not in ("UpToDate", "UpToDateWithWarnings"):
            raise RuntimeError("Niagara compile did not succeed: %s %s" % (path, state["aggregateStatus"]))


class EmitterMeshBuilder(NiagaraBuilder):
    """@brief 原生 Emitter Mesh 资源；所有绘制归属于同一个 NS。

    不产生粒子，不从源 Clip 时长推导生命周期。资源实例由创建它的
    预览所有者显式销毁；原动作的生成、挂点、Follow、Fade 和 Stop 未准入。
    """

    BINDINGS = {"PositionBinding": ("GhostPosition", "Position"),
                "MeshOrientationBinding": ("GhostOrientation", "Quat"),
                "ScaleBinding": ("GhostScale", "Vector"),
                "VelocityBinding": ("GhostVelocity", "Vector")}

    def __init__(self, session=None, *, mcp=None):
        """构建使用自有 session；只读检查使用显式 mcp，二者不混用。"""
        if (session is None) == (mcp is None):
            raise ValueError("Emitter Mesh 需要唯一的构建 session 或只读工具接口")
        self.session = session
        self.m = session.m if session is not None else mcp

    @classmethod
    def validate_specs(cls, specs):
        if not specs:
            raise ValueError("Emitter Mesh 资源缺少源组件")
        names = set()
        expected_parameters = {"Emitter." + n: t for n, t in cls.BINDINGS.values()}
        for spec in specs:
            name = spec.get("name", "")
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) or name in names:
                raise ValueError("Emitter Mesh 名称无效或重复")
            names.add(name)
            if (spec.get("source_mode") != "Emitter" or spec.get("local_space") is not True
                    or spec.get("lifecycle") != "owner_destroy_only"):
                raise ValueError("需要显式 Emitter、根内空间和预览所有者销毁契约")
            entries = spec.get("emitter_spawn", [])
            if (any(not isinstance(e, (list, tuple)) or len(e) != 3 for e in entries)
                    or len(entries) != len(expected_parameters)
                    or {n: t for n, t, _ in entries} != expected_parameters
                    or any(not isinstance(e, str) or not e for _, _, e in entries)):
                raise ValueError("Emitter Mesh 缺少完整且准确类型的根内姿态/静态速度输入")
            if spec.get("emitter_update") or any(spec.get(k) for k in ("bursts", "rate", "spawn", "update")):
                raise ValueError("静态残影资源不生成粒子或猜动态输入")
            renderers = spec.get("renderers", [])
            if not renderers or len(renderers) % 2:
                raise ValueError("每个源材质槽需要独立 Outline/Surface renderer")
            for slot in range(len(renderers) // 2):
                pair = renderers[slot * 2:slot * 2 + 2]
                for role, renderer in zip(("outline", "surface"), pair):
                    if (renderer.get("source_slot") != slot or renderer.get("source_submesh") != 0
                            or renderer.get("role") != role or renderer.get("sort") != slot * 2 + (role == "surface")
                            or not renderer.get("source_material_pid")):
                        raise ValueError("源有序材质槽/子网格/两角色绘制身份不完整")
                    for key in ("mesh", "material"):
                        if not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", renderer.get(key, "")):
                            raise ValueError("Emitter Mesh 缺少准确资源路径: " + key)
                if any(pair[0][k] != pair[1][k] for k in ("mesh", "source_material_pid")):
                    raise ValueError("同一源槽的两角色必须绘制相同几何及源材质")

    @staticmethod
    def renderer_properties(name, renderer):
        def object_path(path):
            return path + "." + path.rsplit("/", 1)[1]
        properties = {"SourceMode": "Emitter", "FacingMode": "Default",
                      "SortMode": "None", "SortOrderHint": renderer["sort"],
                      "bLockedAxisEnable": False, "MotionVectorSetting": "Approximate",
                      "Meshes": [{"Mesh": object_path(renderer["mesh"]),
                                  "PivotOffset": {"x": 0.0, "y": 0.0, "z": 0.0},
                                  "PivotOffsetSpace": "Mesh"}],
                      "bOverrideMaterials": True,
                      "OverrideMaterials": [{"ExplicitMat": object_path(renderer["material"])}]}
        # 保留新原生 binding 的 TypeDefHandle；只写当前 Emitter 命名与来源。
        # CacheValues 先缓存通用 Emitter 显示名，再把 ParamMap 解为真实发射器名。
        # ExplicitEmitter 与真实 ParamMap 名均须读回，不能仅凭显示字符串。
        for property_name, (root, _) in EmitterMeshBuilder.BINDINGS.items():
            properties[property_name] = {"RootName": root, "DataSetName": root,
                "BindingSourceMode": "ExplicitEmitter", "ParamMapVariable": {"Name": name + "." + root},
                "CachedDisplayName": "Emitter." + root}
        return properties

    def verify_renderers(self, specs, *, topologies=None):
        for spec in specs:
            topology = (topologies[spec["name"]] if topologies is not None else
                        self.ns("GetEmitterTopology", emitterRef=self.loc(spec["name"])))
            actual = topology["renderers"]
            if len(actual) != len(spec["renderers"]):
                raise RuntimeError("Emitter Mesh 实际 renderer 数量与源槽两角色绘制不一致")
            for metadata, renderer in zip(actual, spec["renderers"]):
                if metadata["rendererClass"] != {"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"}:
                    raise RuntimeError("Emitter Mesh 实际 renderer 类型不同")
                data = self.ns("GetRendererData", rendererRef=self.loc(
                    spec["name"], renderer=metadata["rendererIndex"]))
                actual_properties = json.loads(data["propertyValues"])
                expected = self.renderer_properties(spec["name"], renderer)
                expected["bIsEnabled"] = True
                # flags 只读：编译后必须真实绑定到 Emitter host map，不能填 true
                # 或接受属性名称正确却仍在使用 native default 的渲染器。
                for binding in self.BINDINGS:
                    expected[binding].update({"bBindingExistsOnSource": True, "bIsCachedParticleValue": False})
                self.verify_properties(expected, actual_properties, spec["name"])

    def verify_emitter_stack(self, spec, topology):
        """检查实际四个 Emitter 栈及有序姿态输入，不以显示名代替类型/值。"""
        name = spec["name"]
        spawn = topology["emitterSpawnScript"]
        entries = spec["emitter_spawn"]
        if spawn["scriptName"] != "EmitterSpawnScript" or len(spawn["modules"]) != len(entries):
            raise RuntimeError("Emitter Mesh 姿态赋值模块数量或栈身份不同: " + name)
        for module, (parameter, kind, expression) in zip(spawn["modules"], entries):
            self.verify_properties({"enabled": True, "bIsSetParametersModule": True,
                "inputs": [{"name": parameter, "type": {"classStructOrEnum": {"refPath": TYPES[kind]}},
                            "bIsDynamic": False}]}, module, name + ".EmitterSpawnScript")
            values = self.ns("GetModuleInputValues", moduleRef=self.loc(
                name, "EmitterSpawnScript", module["moduleName"]))
            self.verify_properties({"moduleName": module["moduleName"],
                "inputs": [{"name": parameter, "value": self.hlsl(expression)}]}, values, name + "." + parameter)
        update = topology["emitterUpdateScript"]
        if update["scriptName"] != "EmitterUpdateScript" or len(update["modules"]) != 1:
            raise RuntimeError("Emitter Mesh 仅允许自有无限生命周期模块: " + name)
        state = update["modules"][0]
        self.verify_properties({"enabled": True, "bIsSetParametersModule": False,
            "moduleScript": {"refPath": "/Niagara/Modules/Emitter/EmitterState.EmitterState"}}, state, name)
        values = self.ns("GetModuleInputValues", moduleRef=self.loc(
            name, "EmitterUpdateScript", state["moduleName"]))
        if values["moduleName"] != state["moduleName"]:
            raise RuntimeError("Emitter Mesh 生命周期模块读回身份不同: " + name)
        for parameter, asset, enum in (
            ("Life Cycle Mode", "ENiagaraEmitterLifeCycleMode", "NewEnumerator1"),
            ("Loop Behavior", "ENiagara_EmitterStateOptions", "NewEnumerator0")):
            inputs = [i for i in state["inputs"] if i["name"] == parameter]
            actual = [i for i in values["inputs"] if i["name"] == parameter]
            if len(inputs) != 1 or len(actual) != 1 or inputs[0]["bIsDynamic"] is not False:
                raise RuntimeError("Emitter Mesh 缺少唯一原生生命周期输入: " + name + "." + parameter)
            # 原生 getter 返回包含枚举类型的完整名称，按类型与成员精确校验。
            expected = {"struct": {"refPath": ENUM}, "value": {
                "enum": {"refPath": "/Niagara/Enums/" + asset + "." + asset},
                "enumName": asset + "::" + enum}}
            self.verify_properties(expected, actual[0]["value"], name + "." + parameter)
        for key, script in (("particleSpawnScript", "ParticleSpawnScript"),
                            ("particleUpdateScript", "ParticleUpdateScript")):
            self.verify_properties({"scriptName": script, "modules": []}, topology[key], name + "." + script)

    def verify_system(self, path, specs, *, fixed_bounds):
        """只读已存在系统；编译/PSO 等待保留失败，不请求编译或泵帧。"""
        self.validate_specs(specs)
        self.validate_bounds(fixed_bounds)
        if not isinstance(path, str) or not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", path):
            raise ValueError("Emitter Mesh 只读检查需要准确包路径")
        self.sref = {"refPath": path + "." + path.rsplit("/", 1)[1]}
        summary = self.ns("GetSystemSummary", system=self.sref)
        self.verify_properties({"systemName": path.rsplit("/", 1)[1],
            "emitters": [{"emitterName": s["name"], "bEnabled": True, "simTarget": "CPUSim"}
                         for s in specs]}, summary, path)
        bounds = {"Min": dict(zip("xyz", fixed_bounds["min"])),
                  "Max": dict(zip("xyz", fixed_bounds["max"])), "IsValid": 1}
        self.verify_properties({"bFixedBounds": True, "FixedBounds": bounds},
            json.loads(self.ns("GetSystemData", system=self.sref)["propertyValues"]), path)
        topologies = {}
        for spec in specs:
            name = spec["name"]
            topology = self.ns("GetEmitterTopology", emitterRef=self.loc(name))
            self.verify_properties({"emitterName": name, "bEnabled": True, "simTarget": "CPUSim"}, topology, name)
            self.verify_properties({"bLocalSpace": True, "SimTarget": "CPUSim",
                "InterpolatedSpawnMode": "RunUpdateScript"}, json.loads(
                    self.ns("GetEmitterData", emitterRef=self.loc(name))["propertyValues"]), name)
            self.verify_emitter_stack(spec, topology)
            topologies[name] = topology
        self.verify_renderers(specs, topologies=topologies)
        state = self.ns("GetSystemCompileState", system=self.sref)
        native = self.m.tool(COMPILE + "ReadSystemState", system=self.sref)["returnValue"]
        self.verify_compile_state(path, state)
        self.verify_native_compilation(path, native)
        if native["bCompilationPending"] is not False or native["bNativeReady"] is not True:
            raise RuntimeError("Emitter Mesh 原生编译或 Ready 尚未就绪；只读检查不启动修复: " + path)
        return {"system": path, "emitter_stack_readback_verified": True,
                "renderer_binding_readback_verified": True, "fixed_bounds_verified": True,
                "compile": state, "native": native, "cold_host_verified": False,
                "system_stack_readback_verified": False, "gpu_draw_verified": False}

    @staticmethod
    def validate_bounds(bounds):
        if not isinstance(bounds, dict) or set(bounds) != {"min", "max"}:
            raise ValueError("无粒子 Emitter Mesh 需要由真实几何派生的固定 bounds")
        for key in ("min", "max"):
            if (not isinstance(bounds[key], list) or len(bounds[key]) != 3
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds[key])):
                raise ValueError("Emitter Mesh bounds 必须是有限 XYZ")
        if any(a >= b for a, b in zip(bounds["min"], bounds["max"])):
            raise ValueError("Emitter Mesh bounds 缺少有效范围")

    def build_system(self, path, specs, *, fixed_bounds):
        """@param specs 已完整验证几何/材质的静态资源计划；不播放或接动作。
        @return 原生编译结果；NS 保存前核实际有序 renderer 和 Emitter binding。
        """
        self.validate_specs(specs)
        self.validate_bounds(fixed_bounds)
        if self.session is None:
            raise ValueError("Emitter Mesh 构建需要自有 create-only session")
        folder, asset_name = path.rsplit("/", 1)
        self.session.begin_create(path)
        self.ns("CreateNiagaraSystem", assetName=asset_name, assetPath=folder,
                templateSystem={"refPath": DEFAULT_SYSTEM})
        self.session.created_asset(path)
        self.sref = {"refPath": path + "." + asset_name}
        for emitter in self.ns("GetSystemSummary", system=self.sref)["emitters"]:
            self.ns("RemoveEmitter", emitterToRemove=self.loc(emitter["emitterName"]))
        # 原生 Emitter Mesh 不创建粒子 bounds calculator；必须提供真实固定范围。
        bounds = {"Min": dict(zip("xyz", fixed_bounds["min"])),
                  "Max": dict(zip("xyz", fixed_bounds["max"])), "IsValid": 1}
        self.ns("SetSystemData", system=self.sref, systemData={"propertyValues": json.dumps({"bFixedBounds": True})})
        self.ns("SetSystemData", system=self.sref, systemData={"propertyValues": json.dumps({"FixedBounds": bounds})})
        for spec in specs:
            name = spec["name"]
            self.ns("AddEmitter", system=self.sref, templateEmitter={"refPath": EMPTY_EMITTER}, emitterName=name)
            self.ns("SetEmitterData", emitter=self.loc(name), emitterData={"propertyValues": json.dumps(
                {"bLocalSpace": True, "SimTarget": "CPUSim", "InterpolatedSpawnMode": "RunUpdateScript"})})
            self.set_params(name, "EmitterSpawnScript", spec["emitter_spawn"])
            state = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/EmitterState.EmitterState")
            self.set_input(name, "EmitterUpdateScript", state, "Life Cycle Mode", self.enum(
                "/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode", "NewEnumerator1", "Self"))
            self.set_input(name, "EmitterUpdateScript", state, "Loop Behavior", self.enum(
                "/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions", "NewEnumerator0", "Infinite"))
            for renderer in spec["renderers"]:
                result = self.ns("AddRenderer", newRendererLocation=self.loc(name),
                    rendererClass={"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"})
                self.ns("SetRendererData", renderer=self.loc(name, renderer=result["rendererIndex"]),
                    rendererData={"propertyValues": json.dumps(self.renderer_properties(name, renderer))})
        def verify_resource():
            data = self.ns("GetSystemData", system=self.sref)
            self.verify_properties({"bFixedBounds": True, "FixedBounds": bounds},
                                   json.loads(data["propertyValues"]), path)
            self.verify_renderers(specs)
        return self.finish_compile(path, before_save=verify_resource)


def configuration_snapshot(call, path):
    """用既有 Niagara Toolsets 读回配置，保护重编译前后的模块、输入及渲染器。"""
    ref = {"refPath": path + "." + path.rsplit("/", 1)[1]}
    summary = call(NS + "GetSystemSummary", system=ref)
    result = {"summary": summary, "system": call(NS + "GetSystemData", system=ref), "stacks": []}
    scripts = [("", "SystemSpawnScript"), ("", "SystemUpdateScript")]
    for emitter in summary["emitters"]:
        name = emitter["emitterName"]
        loc = {"system": ref, "emitterName": name}
        topology = call(NS + "GetEmitterTopology", emitterRef=loc)
        result.setdefault("emitters", []).append({
            "topology": topology, "data": call(NS + "GetEmitterData", emitterRef=loc),
            "renderers": [call(NS + "GetRendererData", rendererRef={**loc, "rendererIndex": r["rendererIndex"]})
                          for r in topology["renderers"]]})
        scripts += [(name, s) for s in ("EmitterSpawnScript", "EmitterUpdateScript", "ParticleSpawnScript", "ParticleUpdateScript")]
    for emitter, script in scripts:
        loc = {"system": ref, "emitterName": emitter, "scriptName": script}
        topology = call(NS + "GetScriptStackTopology", scriptRef=loc)
        modules = []
        for module in topology["modules"]:
            module_ref = {**loc, "moduleName": module["moduleName"]}
            modules.append({"values": call(NS + "GetModuleInputValues", moduleRef=module_ref),
                            "dynamic": [call(NS + "GetDynamicInputChain", stackInputRef={
                                **module_ref, "inputNameStack": [i["name"]]})
                                for i in module["inputs"] if i["bIsDynamic"]]})
        result["stacks"].append({"emitterName": emitter, "topology": topology, "modules": modules})
    return parse_property_blobs(result)


def parse_property_blobs(value):
    if isinstance(value, dict):
        return {k: parse_property_blobs(json.loads(v) if k == "propertyValues" else v) for k, v in value.items()}
    if isinstance(value, list):
        return [parse_property_blobs(v) for v in value]
    return value


def snapshot_differences(before, after, path="$", before_exists=True, after_exists=True):
    """保留每个真实差异的字段路径和两侧值；缺失与 null 明确区分。"""
    if before_exists and after_exists and isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(before.keys() | after.keys()):
            yield from snapshot_differences(before.get(key), after.get(key), path + "." + key,
                                            key in before, key in after)
    elif before_exists and after_exists and isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            yield from snapshot_differences(before[index] if index < len(before) else None,
                                            after[index] if index < len(after) else None,
                                            path + "[%d]" % index, index < len(before), index < len(after))
    elif before_exists != after_exists or before != after or isinstance(before, bool) != isinstance(after, bool):
        yield {"path": path, "beforeExists": before_exists, "afterExists": after_exists,
               "before": before, "after": after}


def partition_configuration_differences(before, after, differences):
    """仅识别真实已证 Mesh 绑定的原生存在性缓存，其余差异仍阻止保存。"""
    # 这八个 Mesh 属性均声明为 FNiagaraVariableAttributeBinding；CacheValues 根据
    # 编译后的属性查询设置 bBindingExistsOnSource，不是作者配置。只接受已证 false→true。
    fields = ("ColorBinding", "PositionBinding", "ScaleBinding", "MeshOrientationBinding", "NormalizedAgeBinding",
              "DynamicMaterialBinding", "DynamicMaterial1Binding", "DynamicMaterial2Binding")
    pattern = re.compile(r"^\$\.emitters\[(\d+)\]\.renderers\[(\d+)\]\.propertyValues\.(%s)\.bBindingExistsOnSource$" %
                         "|".join(fields))
    authored, compiled = [], []
    for difference in differences:
        match = pattern.fullmatch(difference["path"])
        eligible = (match is not None and difference["beforeExists"] and difference["afterExists"]
                    and difference["before"] is False and difference["after"] is True)
        if eligible:
            emitter, renderer = map(int, match.group(1, 2))
            field = match.group(3)
            for snapshot in (before, after):
                metadata = snapshot["emitters"][emitter]["topology"]["renderers"][renderer]
                binding = snapshot["emitters"][emitter]["renderers"][renderer]["propertyValues"][field]
                eligible = (eligible and metadata["rendererIndex"] == renderer
                            and metadata["rendererClass"] == {"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"}
                            and isinstance(binding, dict) and isinstance(binding["bBindingExistsOnSource"], bool))
        (compiled if eligible else authored).append(difference)
    return authored, compiled


def normal01_orientation_expressions():
    """仅已证单系统的旧／新完整表达式；保留原四元数乘法及 Owner 变换。"""
    from zzz_fx_niagara import f4, qmul_h, ue_quat_h

    def pair(q, world=False):
        old = "float4(({q}).x, -({q}).z, -({q}).y, ({q}).w)".format(q=q)
        new = ue_quat_h(q)
        return (qmul_h("Engine.Owner.Rotation", old), qmul_h("Engine.Owner.Rotation", new)) if world else (old, new)

    local = pair(qmul_h("Particles.UChain4Q", "Particles.UPartQ"))
    # 原生读回的 Cone 根局部旋转；它是 root 的独立分支，不挂 Trail LegacyClip。
    cone = pair(qmul_h(f4((0.3779549300670624, 0.5304046273231506,
                          0.5750681757926941, -0.49509358406066895)), "Particles.UPartQ"), True)
    return dict(zip(NORMAL01_EMITTERS, [local] * 6 + [cone]))


def normal01_orientation_plan(config, path, require_current=False):
    """先完整核七 pin 和 Renderer，再返回精确七次改值；未知配置在写前拒绝。"""
    if path != NORMAL01_SYSTEM or tuple(e["emitterName"] for e in config["summary"]["emitters"]) != NORMAL01_EMITTERS:
        raise RuntimeError("朝向迁移只支持已证 Normal01 精确系统／七发射器")
    expected = copy.deepcopy(config)
    plan = []
    for index, (name, (old, new)) in enumerate(normal01_orientation_expressions().items()):
        emitter = config["summary"]["emitters"][index]
        data = config["emitters"][index]
        renderers = data["renderers"]
        topology = data["topology"]
        if (not emitter["bEnabled"] or emitter["simTarget"] != "CPUSim"
                or topology["emitterName"] != name or len(renderers) != 1
                or topology["renderers"][0]["rendererClass"] != {"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"}):
            raise RuntimeError("原 Mesh 发射器身份／Renderer 不同: " + name)
        rd = renderers[0]["propertyValues"]
        mesh_name = "Eff_Cone_01" if index == 6 else "FXMD_DAO_001"
        meshes = rd["Meshes"]
        if (len(meshes) != 1 or meshes[0]["mesh"] != {"refPath": FX_MESH_ROOT + mesh_name + "." + mesh_name}
                or meshes[0]["scale"] != dict(x=1, y=1, z=1)
                or meshes[0]["rotation"] != dict(pitch=0, yaw=0, roll=0)
                or meshes[0]["pivotOffset"] != dict(x=0, y=0, z=0)
                or meshes[0]["pivotOffsetSpace"] != "Mesh" or not rd["bIsEnabled"]
                or rd["SourceMode"] != "Particles" or rd["FacingMode"] != "Default" or rd["bLockedAxisEnable"]
                or rd["MeshOrientationBinding"]["paramMapVariable"]["name"] != "Particles.MeshOrientation"):
            raise RuntimeError("原 Mesh／Renderer 存在不同朝向或基座补偿: " + name)
        hits = []
        for si, stack in enumerate(config["stacks"]):
            if stack["emitterName"] != name or stack["topology"]["scriptName"] != "ParticleUpdateScript":
                continue
            if len(stack["topology"]["modules"]) != len(stack["modules"]):
                raise RuntimeError("模块配置与拓扑数量不同: " + name)
            for mi, module in enumerate(stack["modules"]):
                mt = stack["topology"]["modules"][mi]
                if module["values"]["moduleName"] != mt["moduleName"]:
                    raise RuntimeError("模块配置与拓扑身份不同: " + name)
                for ii, value in enumerate(module["values"]["inputs"]):
                    if value["name"] == "Particles.MeshOrientation":
                        hits.append((si, mi, ii, mt, value["value"]))
        if len(hits) != 1:
            raise RuntimeError("需要唯一原 ParticleUpdate MeshOrientation pin: " + name)
        si, mi, ii, mt, value = hits[0]
        if (not mt["enabled"] or not mt["bIsSetParametersModule"]
                or value != NiagaraBuilder.hlsl(new if require_current else old)):
            raise RuntimeError("MeshOrientation 完整表达式未知或已改变，拒绝迁移: " + name)
        ref = {"system": {"refPath": path + "." + path.rsplit("/", 1)[1]}, "emitterName": name,
               "scriptName": "ParticleUpdateScript", "moduleName": mt["moduleName"],
               "rendererIndex": -1, "inputNameStack": ["Particles.MeshOrientation"]}
        after = NiagaraBuilder.hlsl(new)
        expected["stacks"][si]["modules"][mi]["values"]["inputs"][ii]["value"] = after
        plan.append({"ref": ref, "before": value, "after": after})
    return expected, plan


def verify_normal01_mesh_basis(call):
    """复核两原导入设置与已证不对称本地边界；不导入或修改 Mesh。"""
    ot = "editor_toolset.toolsets.object.ObjectTools."
    sm = "editor_toolset.toolsets.static_mesh.StaticMeshTools."
    settings = dict(importTranslation=dict(x=0, y=0, z=0), importRotation=dict(pitch=0, yaw=0, roll=0),
                    importUniformScale=1, coordinateSystemPolicy="MatchUpForwardAxes", bConvertScene=True,
                    bForceFrontXAxis=False, bConvertSceneUnit=False, bUsingLUFCoordinateSysem=False,
                    bTransformVertexToAbsolute=True, bBakePivotInVertex=False)
    bounds = {"FXMD_DAO_001": ((-150.0426025390625, -150.0424041748047, -1.2862329483032227),
                              (149.95730590820312, 150.04269409179688, 2.8998489379882812)),
              "Eff_Cone_01": ((-63.54888153076172, -24.319089889526367, -63.54888153076172),
                              (63.54888153076172, 24.31909942626953, 63.54888153076172))}
    for name, (minimum, maximum) in bounds.items():
        ref = {"refPath": FX_MESH_ROOT + name + "." + name}
        asset = json.loads(call(ot + "get_properties", instance=ref,
                               properties=["assetImportData", "positiveBoundsExtension", "negativeBoundsExtension"]))
        for extension in ("positiveBoundsExtension", "negativeBoundsExtension"):
            if asset[extension] != dict(x=0, y=0, z=0):
                raise RuntimeError("Mesh 有不同边界扩展: " + name)
        imported = json.loads(call(ot + "get_properties", instance=asset["assetImportData"], properties=list(settings)))
        if imported != settings:
            raise RuntimeError("Mesh 导入坐标约定已改变: " + name)
        actual = call(sm + "get_bounds", mesh=ref)
        if not actual["isValid"] or any(not abs(actual[side][axis] - values[i]) <= 0.0001
                                      for side, values in (("min", minimum), ("max", maximum))
                                      for i, axis in enumerate("xyz")):
            raise RuntimeError("Mesh 实际本地边界已改变: " + name)


def normal01_material_readback(unreal, call, source_report, output, *, mesh_only=False, read_sections=False):
    """只读正式七层的真实材质链和 LOD0 渲染数据，保留后续指针迁移所需快照。

    只加载旧构建报告列出的七对材质；链不同即拒绝跟随未知包。
    FBX 只导出两个原 StaticMesh 的 LOD0 RenderData，不改资产或请求编译。
    """
    source = json.loads(source_report.read_text(encoding="utf-8-sig"))
    names = tuple(re.sub(r"[^a-zA-Z0-9_]", "_", n) for n in source["emitters"])
    if source["system"] != NORMAL01_SYSTEM or names != NORMAL01_EMITTERS or len(source["materials"]) != 7:
        raise RuntimeError("只读材质证据需要原 Normal01 七层报告")
    saved = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())).resolve()
    output = output.resolve()
    if not output.is_relative_to(saved) or output.suffix != ".json" or output.exists():
        raise RuntimeError("读回输出须为 Saved 下未存在的 JSON 文件")
    mesh_files = {name: output.with_name(output.stem + "_" + name + "_LOD0.fbx")
                  for name in ("FXMD_DAO_001", "Eff_Cone_01")}
    if any(f.exists() for f in mesh_files.values()):
        raise RuntimeError("拒绝覆盖已有网格证据")
    packages = {NORMAL01_SYSTEM, *(FX_MESH_ROOT + n for n in mesh_files)}
    for material in source["materials"].values():
        if (not material["master"].startswith("/Game/Characters/Shared/FX/ZZZ/Materials/M_ZZZFX_Particles_")
                or not material["mi"].startswith("/Game/Characters/Shared/FX/ZZZ/MaterialInstances/MI_Eff_")):
            raise RuntimeError("旧报告含范围外材质")
        packages.update((material["master"], material["mi"]))
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))

    def disk_hashes():
        return {p: hashlib.sha256((content / (p[6:] + ".uasset")).read_bytes()).hexdigest()
                for p in sorted(packages)}

    def dirty():
        return sorted(p.get_path_name() for p in list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
                      + list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()))

    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is not None or dirty():
        raise RuntimeError("只读材质入口需要非 PIE、无未保存包的独立 Editor")
    before_hashes = disk_hashes()
    report = {"system": NORMAL01_SYSTEM, "saved": False, "source_report": str(source_report.resolve()),
              "scope": "meshes" if mesh_only else "materials_and_meshes",
              "before_hashes": before_hashes, "materials": [], "meshes": [], "errors": []}
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        # 仅网格复核是显式只读模式，不重跑已完成的七层材质核查。
        config = None if mesh_only else configuration_snapshot(call, NORMAL01_SYSTEM)
        if not mesh_only:
            normal01_orientation_plan(config, NORMAL01_SYSTEM, require_current=True)
            report["configuration"] = config
        expected_mi = {v["mi"]: (pid, v) for pid, v in source["materials"].items()}
        seen = set()
        mel = unreal.MaterialEditingLibrary
        for name, data in zip(NORMAL01_EMITTERS, [] if mesh_only else config["emitters"]):
            rd = data["renderers"][0]["propertyValues"]
            overrides = rd["OverrideMaterials"]
            if not rd["bOverrideMaterials"] or len(overrides) != 1:
                raise RuntimeError("需要唯一原材质覆盖: " + name)
            actual = overrides[0]["explicitMat"]["refPath"]
            mi_package = actual.rsplit(".", 1)[0]
            if mi_package not in expected_mi:
                raise RuntimeError("真实 Renderer 引用了范围外材质: " + actual)
            pid, recorded = expected_mi[mi_package]
            if pid in seen:
                raise RuntimeError("原七层材质引用不唯一: " + pid)
            seen.add(pid)
            mi = unreal.EditorAssetLibrary.load_asset(mi_package)
            if not isinstance(mi, unreal.MaterialInstanceConstant) or mi.get_path_name() != actual:
                raise RuntimeError("真实 MI 身份无效: " + actual)
            master = mi.get_editor_property("parent")
            expected_master = recorded["master"] + "." + recorded["master"].rsplit("/", 1)[1]
            if not isinstance(master, unreal.Material) or master.get_path_name() != expected_master:
                raise RuntimeError("真实 MI 父材质与旧报告不同: " + actual)
            custom = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            if not isinstance(custom, unreal.MaterialExpressionCustom):
                raise RuntimeError("原 Emissive 未直接连接 Custom: " + expected_master)
            code = custom.get_editor_property("code")
            inputs = [str(i.get_editor_property("input_name")) for i in custom.get_editor_property("inputs")]
            connections = mel.get_inputs_for_material_expression(master, custom)
            if len(connections) != len(inputs):
                raise RuntimeError("Custom pin 与原生输入连线数量不同: " + expected_master)
            wiring = []
            for pin, node in zip(inputs, connections):
                row = {"pin": pin, "node": node.get_path_name() if node else None,
                       "class": node.get_class().get_path_name() if node else None}
                if isinstance(node, unreal.MaterialExpressionScalarParameter):
                    row.update(parameter=str(node.get_editor_property("parameter_name")),
                               default=float(node.get_editor_property("default_value")))
                wiring.append(row)
            scalar_names = [str(n) for n in mel.get_scalar_parameter_names(mi)]
            vector_names = [str(n) for n in mel.get_vector_parameter_names(mi)]
            texture_names = [str(n) for n in mel.get_texture_parameter_names(mi)]
            textures = {n: mel.get_material_instance_texture_parameter_value(mi, n) for n in texture_names}
            report["materials"].append({"emitter": name, "sourcePID": pid, "instance": actual,
                "master": master.get_path_name(), "custom": custom.get_path_name(), "code": code,
                "code_sha256": hashlib.sha256(code.encode()).hexdigest(), "custom_inputs": inputs,
                "wiring": wiring, "blend": str(master.get_editor_property("blend_mode")),
                "shading_model": str(master.get_editor_property("shading_model")),
                "two_sided": master.get_editor_property("two_sided"),
                "scalar_parameters": {n: mel.get_material_instance_scalar_parameter_value(mi, n) for n in scalar_names},
                "vector_parameters": {n: mel.get_material_instance_vector_parameter_value(mi, n).export_text()
                                      for n in vector_names},
                "texture_parameters": {n: t.get_path_name() if t else None for n, t in textures.items()},
                "scalar_overrides": [v.export_text() for v in mi.get_editor_property("scalar_parameter_values")]})
        smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        for name, filename in mesh_files.items():
            mesh = unreal.EditorAssetLibrary.load_asset(FX_MESH_ROOT + name)
            if not isinstance(mesh, unreal.StaticMesh) or mesh.get_path_name() != FX_MESH_ROOT + name + "." + name:
                raise RuntimeError("原 StaticMesh 身份无效: " + name)
            import_data = mesh.get_editor_property("asset_import_data")
            if not isinstance(import_data, unreal.FbxStaticMeshImportData):
                raise RuntimeError("原网格不是 FbxStaticMeshImportData: " + name)
            import_info = {"class": import_data.get_class().get_path_name(),
                "source_files": list(import_data.extract_filenames()),
                "vertex_color_import_option": str(import_data.get_editor_property("vertex_color_import_option")),
                "vertex_override_color": import_data.get_editor_property("vertex_override_color").export_text()}
            if read_sections:
                # 直接读取原 LOD0 RenderData，排除 FBX 的顶点焊接／角点映射影响。
                # 标准 Editor 保留 CPU 数据；不设置 AllowCPUAccess 或修改资产。
                if mesh.get_num_sections(0) != 1:
                    raise RuntimeError("原网格不是唯一 LOD0 Section: " + name)
                vertices, triangles, normals, uvs, tangents = (
                    unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, 0))
                if (not vertices or len(uvs) != len(vertices) or len(normals) != len(vertices)
                        or len(triangles) != mesh.get_num_triangles(0) * 3
                        or any(i < 0 or i >= len(vertices) for i in triangles)):
                    raise RuntimeError("原生 LOD0 Section 数据不完整: " + name)
                report["meshes"].append({"mesh": mesh.get_path_name(), "lod": 0, "section": 0,
                    "representation": "LOD0 RenderData; ProceduralMeshLibrary.GetSectionFromStaticMesh",
                    "allow_cpu_access": mesh.get_editor_property("allow_cpu_access"),
                    "import_data": import_info,
                    "vertices": [[v.x, v.y, v.z] for v in vertices], "triangles": list(triangles),
                    "uv0": [[v.x, v.y] for v in uvs]})
                continue
            options = unreal.FbxExportOption()
            settings = dict(fbx_export_compatibility=unreal.FbxExportCompatibility.FBX_2013,
                            ascii=False, force_front_x_axis=False, level_of_detail=False,
                            export_source_mesh=False, vertex_color=True, collision=False,
                            bake_material_inputs=unreal.FbxMaterialBakeMode.DISABLED)
            for prop, value in settings.items():
                options.set_editor_property(prop, value)
                if options.get_editor_property(prop) != value:
                    raise RuntimeError("原生 FBX 选项未生效: " + prop)
            task = unreal.AssetExportTask()
            for prop, value in dict(object=mesh, exporter=unreal.StaticMeshExporterFBX(), options=options,
                                    filename=str(filename), automated=True, prompt=False, selected=False,
                                    replace_identical=False).items():
                task.set_editor_property(prop, value)
            def export_options_readback():
                actual_options = task.get_editor_property("options")
                if (actual_options != options or task.get_editor_property("object") != mesh
                        or not task.get_editor_property("automated")):
                    raise RuntimeError("FBX Task 未绑定原网格和自动导出选项: " + name)
                actual = {prop: actual_options.get_editor_property(prop) for prop in settings}
                if actual != settings:
                    raise RuntimeError("FBX Task 的有效选项不同: " + name)
                return {prop: value if isinstance(value, bool) else str(value) for prop, value in actual.items()}
            export_before = export_options_readback()
            ok = unreal.Exporter.run_asset_export_task(task)
            errors = list(task.get_editor_property("errors"))
            if not ok or errors or not filename.is_file():
                raise RuntimeError("原生 LOD0 RenderData 导出失败: " + name + "; " + repr(errors))
            exporter = task.get_editor_property("exporter")
            if exporter.get_editor_property("export_task") != task:
                raise RuntimeError("原生 FBX Exporter 未消费指定 Task: " + name)
            report["meshes"].append({"mesh": mesh.get_path_name(), "lod": 0,
                "representation": "native StaticMesh LOD0 RenderData; bExportSourceMesh=false",
                "import_data": import_info, "exporter_class": exporter.get_class().get_path_name(),
                "exporter_task_matches": True, "export_options_before": export_before,
                "export_options_after": export_options_readback(),
                "vertex_count": smes.get_number_verts(mesh, 0), "triangle_count": mesh.get_num_triangles(0),
                "uv_channels": smes.get_num_uv_channels(mesh, 0), "fbx": str(filename),
                "uv_channels_representation": "MeshDescription; native GetNumUVChannels",
                "fbx_sha256": hashlib.sha256(filename.read_bytes()).hexdigest()})
        if not mesh_only:
            report["configuration_matches_after"] = configuration_snapshot(call, NORMAL01_SYSTEM) == config
            if not report["configuration_matches_after"]:
                raise RuntimeError("只读前后 Niagara 作者配置不同")
    except Exception as error:
        report["errors"].append(str(error))
        raise
    finally:
        report.update(after_hashes=disk_hashes(), dirty_after=dirty())
        report["asset_bytes_unchanged"] = report["after_hashes"] == before_hashes
        output.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        unreal.log("FX_MATERIAL_READBACK " + json.dumps({"file": str(output), "material_count": len(report["materials"]),
            "mesh_count": len(report["meshes"]), "errors": report["errors"], "saved": False,
            "asset_bytes_unchanged": report["asset_bytes_unchanged"], "dirty_after": report["dirty_after"]}, ensure_ascii=False))
        if not report["asset_bytes_unchanged"] or report["dirty_after"]:
            raise RuntimeError("只读入口出现资产字节变化／未保存包")


def normal01_reference_plan(config, material_refs, mesh_refs=None):
    """只迁移既有四个材质指针及可选七个网格指针，完整保留结构的其它字段。"""
    normal01_orientation_plan(config, NORMAL01_SYSTEM, require_current=True)
    names = tuple("root_Trail_rot_" + n for n in NORMAL01_MATERIAL_LAYERS)
    if set(material_refs) != set(names):
        raise ValueError("必须提供 Normal01 精确四个材质引用")
    if mesh_refs is not None and set(mesh_refs) != set(NORMAL01_EMITTERS):
        raise ValueError("网格迁移必须提供精确七个发射器引用")
    expected, edits = copy.deepcopy(config), []
    for index, name in enumerate(NORMAL01_EMITTERS):
        rd = expected["emitters"][index]["renderers"][0]["propertyValues"]
        props = {}
        for refs, field, member, root in (
                (material_refs, "OverrideMaterials", "explicitMat", "/Game/Characters/Shared/FX/ZZZ/MaterialInstances/"),
                (mesh_refs or {}, "Meshes", "mesh", FX_MESH_ROOT)):
            if name not in refs:
                continue
            target = refs[name]
            if (not target.startswith(root) or not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", target)
                    or len(rd[field]) != 1 or set(rd[field][0][member]) != {"refPath"}):
                raise ValueError("未知引用或 Renderer 结构: " + name + "." + field)
            value = target + "." + target.rsplit("/", 1)[1]
            if rd[field][0][member]["refPath"] == value:
                raise ValueError("迁移目标必须是新内容版本: " + name)
            rd[field][0][member]["refPath"] = value
            props[field] = copy.deepcopy(rd[field])
        if props:
            edits.append({"renderer": {"system": {"refPath": NORMAL01_SYSTEM + "." + NORMAL01_SYSTEM.rsplit("/", 1)[1]},
                          "emitterName": name, "rendererIndex": 0}, "properties": props})
    differences = list(snapshot_differences(config, expected))
    if len(differences) != 4 + (7 if mesh_refs is not None else 0):
        raise RuntimeError("指针迁移差异数不符")
    return expected, edits


def verify_normal01_configuration(expected, actual):
    differences = list(snapshot_differences(expected, actual))
    authored, derived = partition_configuration_differences(expected, actual, differences)
    if authored:
        raise RuntimeError("Normal01 出现批准指针以外配置差异: " + json.dumps(authored[:6], ensure_ascii=False))
    return derived


def normal01_material_plans(fx_path, assets_path):
    """复用当前生成器四个有效计划，不重建有未解决源契约的整八层系统。"""
    import zzz_fx_build as B
    from zzz_fx_material_ue import Builder, MASTER_DIR, MI_DIR
    fx, assets = B.read_json(fx_path), B.read_json(assets_path)
    deps = B.read_json(B.dependency_path(fx_path, fx))
    plans = {}
    for node, _, active in B.walk(fx["root"]):
        if not active or node["name"] not in NORMAL01_MATERIAL_LAYERS:
            continue
        renderer = node["particle"]["renderer"]
        pid = str(renderer["m_Materials"][0]["m_PathID"])
        context = {"kind": "particle", "streams": renderer["m_VertexStreams"],
                   "custom_streams": renderer["m_UseCustomVertexStreams"], "mesh": True,
                   "uv_count": B.uv_count(deps, renderer["m_Mesh"]["m_PathID"])}
        plan = B.material_plan(deps, pid, context, assets)
        Builder.validate_plan(plan)
        name = "root_Trail_rot_" + node["name"]
        if name in plans:
            raise ValueError("源材质层身份重复: " + name)
        plans[name] = {"plan": plan, "master": MASTER_DIR + "/" + plan["master"],
                       "instance": MI_DIR + "/" + B.mi_name(plan), "sourcePID": pid}
    if set(plans) != {"root_Trail_rot_" + n for n in NORMAL01_MATERIAL_LAYERS}:
        raise ValueError("源数据缺少四个明确材质层")
    return plans


def verify_normal01_material(unreal, row, *, instance=False):
    """保存前及保存后核真实 Custom 输入连线、代码、材质属性和有效实例参数。"""
    from zzz_fx_material_ue import BUILTIN_NODES, linear_color
    plan, mel = row["plan"], unreal.MaterialEditingLibrary
    master = unreal.EditorAssetLibrary.load_asset(row["master"])
    if not isinstance(master, unreal.Material):
        raise RuntimeError("新 Master 身份不同")
    flags = {"two_sided": plan["two_sided"], "disable_depth_test": plan["disable_depth_test"],
             "used_with_niagara_mesh_particles": True, "used_with_niagara_sprites": False,
             "automatically_set_usage_in_editor": False}
    for prop, value in flags.items():
        if master.get_editor_property(prop) != value:
            raise RuntimeError("新材质属性不同: " + prop)
    # UE Python 枚举 str 是 <类型.成员: 数值>；按原生类型和值核验，不解析显示文本。
    blend_modes = {"BLEND_AlphaComposite": unreal.BlendMode.BLEND_ALPHA_COMPOSITE,
                   "BLEND_Translucent": unreal.BlendMode.BLEND_TRANSLUCENT,
                   "BLEND_Additive": unreal.BlendMode.BLEND_ADDITIVE,
                   "BLEND_Modulate": unreal.BlendMode.BLEND_MODULATE}
    expected_blend = blend_modes.get(plan["blend"])
    if expected_blend is None:
        raise RuntimeError("未支持的源混合枚举: " + plan["blend"])
    actual_blend = master.get_editor_property("blend_mode")
    actual_shading = master.get_editor_property("shading_model")
    expected_shading = unreal.MaterialShadingModel.MSM_UNLIT
    if actual_blend != expected_blend or actual_shading != expected_shading:
        raise RuntimeError("新材质混合／光照属性不同: " + str({"material": master.get_path_name(),
            "expected_blend": str(expected_blend), "actual_blend": str(actual_blend),
            "expected_shading": str(expected_shading), "actual_shading": str(actual_shading)}))
    custom = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    code = ("float4 VCol = float4(VCol_rgb, VCol_a);\n" if "VCol" in plan["builtins"] else "") + plan["code"]
    pins = [p for b in plan["builtins"] for p in (["VCol_rgb", "VCol_a"] if b == "VCol" else [b])]
    pins += list(plan.get("pixel_params", plan["params"])) + list(plan["textures"])
    if (not isinstance(custom, unreal.MaterialExpressionCustom) or custom.get_editor_property("code") != code
            or [str(i.get_editor_property("input_name")) for i in custom.get_editor_property("inputs")] != pins):
        raise RuntimeError("新 Custom 代码／输入／Emissive 接线不同")
    connections = mel.get_inputs_for_material_expression(master, custom)
    if len(connections) != len(pins):
        raise RuntimeError("新 Custom 输入连线数不同")
    for pin, node in zip(pins, connections):
        if node is None:
            raise RuntimeError("新 Custom 输入未接线: " + pin)
        klass = BUILTIN_NODES[pin][0] if pin in BUILTIN_NODES else (
            "MaterialExpressionTextureObjectParameter" if pin in plan["textures"] else
            "MaterialExpressionScalarParameter" if plan["params"][pin]["dim"] == 1 else "MaterialExpressionVectorParameter")
        if node.get_class().get_name() != klass:
            raise RuntimeError("新 Custom 输入类型不同: " + pin)
        if pin not in BUILTIN_NODES and str(node.get_editor_property("parameter_name")) != pin:
            raise RuntimeError("新 Custom 参数连线不同: " + pin)
    opacity = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_OPACITY)
    if (not isinstance(opacity, unreal.MaterialExpressionComponentMask)
            or [opacity.get_editor_property(k) for k in ("r", "g", "b", "a")] != [False, False, False, True]
            or list(mel.get_inputs_for_material_expression(master, opacity)) != [custom]):
        raise RuntimeError("新材质 Alpha 输出接线不同")
    if instance:
        mi = unreal.EditorAssetLibrary.load_asset(row["instance"])
        if not isinstance(mi, unreal.MaterialInstanceConstant) or mi.get_editor_property("parent") != master:
            raise RuntimeError("新 MI 父材质不同")
        for name, p in plan["params"].items():
            if p["dim"] == 1:
                actual = mel.get_material_instance_scalar_parameter_value(mi, name)
                if abs(actual - float(p["value"])) > 1e-5:
                    raise RuntimeError("新 MI scalar 不同: " + name)
            else:
                actual = mel.get_material_instance_vector_parameter_value(mi, name)
                if any(abs(getattr(actual, k) - v) > 1e-5 for k, v in linear_color(p["value"]).items()):
                    raise RuntimeError("新 MI vector 不同: " + name)
        for name, path in plan["textures"].items():
            tex = mel.get_material_instance_texture_parameter_value(mi, name)
            if tex is None or tex.get_path_name() != path + "." + path.rsplit("/", 1)[1]:
                raise RuntimeError("新 MI texture 不同: " + name)
    return {"code_sha256": hashlib.sha256(code.encode()).hexdigest(), "inputs": pins, "instance": instance}


def normal01_render_colors(geometry, source, *, vertex_color, export_source_mesh):
    """读原生 RenderData 颜色；只有完整源角点全白才能使用 UE 默认白色缓冲。"""
    if vertex_color is not True or export_source_mesh is not False:
        raise RuntimeError("颜色证据必须实际启用 vertex_color 并导出 RenderData")
    colors, indices = source.get("m_Colors"), source.get("m_Indices")
    count = source["m_VertexCount"]
    if (not isinstance(colors, list) or len(colors) != count * 4 or not indices
            or any(type(c) not in (int, float) or not math.isfinite(c) or not 0 <= c <= 1 for c in colors)
            or any(type(i) is not int or not 0 <= i < count for i in indices)):
        raise RuntimeError("源 RGBA／实际角点不完整或无效")

    def child(node, name):
        values = [c for c in node.children if c.name == name]
        if len(values) != 1:
            raise RuntimeError("原生 FBX 缺少唯一字段: " + name)
        return values[0]

    layers = [c for c in geometry.children if c.name == "LayerElementColor"]
    references = [(layer, element) for layer in geometry.children if layer.name == "Layer"
                  for element in layer.children if element.name == "LayerElement"
                  and child(element, "Type").props == [b"LayerElementColor"]]
    corners = child(geometry, "PolygonVertexIndex").props[0][3]
    if len(corners) != len(indices):
        raise RuntimeError("原生 FBX 与源实际角点数不同")
    if not layers:
        if references:
            raise RuntimeError("原生颜色层缺失但仍被引用")
        if any(colors[i * 4:i * 4 + 4] != [1, 1, 1, 1] for i in indices):
            raise RuntimeError("非白源角点缺少原生颜色层")
        # UE 非白才分配 ColorVertexBuffer；Niagara 消费 GNullColorVertexBuffer 的 opaque white。
        return [1., 1., 1., 1.], [0] * len(corners), "implicit_opaque_white"
    if (len(layers) != 1 or layers[0].props != [0] or len(references) != 1
            or references[0][0].props != [0] or child(references[0][1], "TypedIndex").props != [0]):
        raise RuntimeError("原生颜色层／引用身份不唯一或错误")
    color = layers[0]
    if (child(color, "MappingInformationType").props != [b"ByPolygonVertex"]
            or child(color, "ReferenceInformationType").props != [b"IndexToDirect"]):
        raise RuntimeError("未核实的原生颜色映射")
    rgba = child(color, "Colors").props[0][3]
    color_indices = child(color, "ColorIndex").props[0][3]
    if (not rgba or len(rgba) % 4 or len(color_indices) != len(corners)
            or any(not math.isfinite(c) or not 0 <= c <= 1 for c in rgba)
            or any(type(i) is not int or not 0 <= i < len(rgba) // 4 for i in color_indices)):
        raise RuntimeError("原生颜色 RGBA／角点索引不完整或无效")
    return rgba, color_indices, "explicit_render_color_buffer"


def normal01_mesh_validation(unreal, imports, output):
    """先核实际 LOD0 几何/UV/法线，再核原生颜色及合法全白省略。"""
    import struct
    from collections import Counter
    from fbx_bin_reader import FbxReader
    def half(value):
        return struct.unpack("e", struct.pack("e", value))[0]
    rows = []
    for pid, item in imports["entries"].items():
        source = json.loads(Path(item["source_mesh_json"]).read_text(encoding="utf-8-sig"))
        positions = [(-source["m_Vertices"][i * 3] * 100, source["m_Vertices"][i * 3 + 2] * 100,
                      source["m_Vertices"][i * 3 + 1] * 100) for i in range(source["m_VertexCount"])]
        mesh = unreal.EditorAssetLibrary.load_asset(item["path"])
        if not isinstance(mesh, unreal.StaticMesh) or mesh.get_num_sections(0) != len(source["m_SubMeshes"]):
            raise RuntimeError("新网格身份／Submesh 数不符")
        all_triangles, oriented_triangles, native_vertices, uv_errors, normal_errors = [], [], 0, 0, 0
        def cyclic(points):
            return min(tuple(points[i:] + points[:i]) for i in range(3))
        for section, submesh in enumerate(source["m_SubMeshes"]):
            vertices, triangles, normals, uvs, tangents = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(mesh, 0, section)
            if (len(uvs) != len(vertices) or len(normals) != len(vertices)
                    or len(triangles) != submesh["indexCount"] or any(i < 0 or i >= len(vertices) for i in triangles)):
                raise RuntimeError("新网格原生 LOD0 Section 数组不完整")
            keys = []
            for v, uv, normal in zip(vertices, uvs, normals):
                candidates = [i for i, p in enumerate(positions)
                              if max(abs(a - b) for a, b in zip((v.x, v.y, v.z), p)) <= .0003]
                if not candidates:
                    raise RuntimeError("新网格位置与原源不符")
                matches = [i for i in candidates if max(abs(uv.x - half(source["m_UV0"][i * 2])),
                            abs(uv.y - half(1 - source["m_UV0"][i * 2 + 1]))) <= 2e-6]
                uv_errors += not matches
                if source.get("m_Normals") and matches:
                    def normal_matches(i):
                        n = source["m_Normals"][i * 3:i * 3 + 3]
                        return max(abs(a - b) for a, b in zip((normal.x, normal.y, normal.z), (-n[0], n[2], n[1]))) <= .012
                    normal_errors += not any(normal_matches(i) for i in matches)
                keys.append(positions[candidates[0]])
            all_triangles += [tuple(sorted(keys[i] for i in triangles[t:t + 3])) for t in range(0, len(triangles), 3)]
            oriented_triangles += [cyclic([keys[i] for i in triangles[t:t + 3]]) for t in range(0, len(triangles), 3)]
            native_vertices += len(vertices)
        expected_triangles = [tuple(sorted(positions[i] for i in source["m_Indices"][t:t + 3]))
                              for t in range(0, len(source["m_Indices"]), 3)]
        if uv_errors or normal_errors or Counter(all_triangles) != Counter(expected_triangles):
            raise RuntimeError("新网格真实几何／UV／法线不符: " + str((pid, uv_errors, normal_errors)))
        reference = json.loads(Path(item["render_geometry_reference"]).read_text(encoding="utf-8-sig"))
        old_name = item["identity"]["name"]
        original = [r for r in reference["meshes"] if r["mesh"] == FX_MESH_ROOT + old_name + "." + old_name]
        if len(original) != 1 or reference["errors"] or not reference["asset_bytes_unchanged"]:
            raise RuntimeError("原 LOD0 几何参考身份不同")
        old = original[0]
        old_keys = []
        for vertex in old["vertices"]:
            candidates = [p for p in positions if max(abs(a - b) for a, b in zip(vertex, p)) <= .0003]
            if not candidates:
                raise RuntimeError("原 LOD0 几何参考不匹配源位置")
            old_keys.append(candidates[0])
        old_oriented = [cyclic([old_keys[i] for i in old["triangles"][t:t + 3]])
                        for t in range(0, len(old["triangles"]), 3)]
        if Counter(oriented_triangles) != Counter(old_oriented):
            raise RuntimeError("新网格三角形绕序与已证原 LOD0 几何不同")
        # stock StaticMeshExporterFBX 直接导出 LOD0 RenderData 的 FColorBuffer；不用源 MeshDescription 冒充。
        filename = output.with_name(output.stem + "_" + item["name"] + "_RenderData.fbx")
        if filename.exists():
            raise RuntimeError("拒绝覆盖新网格颜色证据")
        options = unreal.FbxExportOption()
        for prop, value in dict(fbx_export_compatibility=unreal.FbxExportCompatibility.FBX_2013,
                ascii=False, force_front_x_axis=False, level_of_detail=False, export_source_mesh=False,
                vertex_color=True, collision=False, bake_material_inputs=unreal.FbxMaterialBakeMode.DISABLED).items():
            options.set_editor_property(prop, value)
        vertex_color = options.get_editor_property("vertex_color")
        export_source_mesh = options.get_editor_property("export_source_mesh")
        if vertex_color is not True or export_source_mesh is not False:
            raise RuntimeError("原生 FBX 实际导出选项与 RenderData 颜色请求不同")
        task = unreal.AssetExportTask()
        for prop, value in dict(object=mesh, exporter=unreal.StaticMeshExporterFBX(), options=options,
                filename=str(filename), automated=True, prompt=False, selected=False, replace_identical=False).items():
            task.set_editor_property(prop, value)
        if not unreal.Exporter.run_asset_export_task(task):
            raise RuntimeError("新网格原生颜色导出失败")
        reader = FbxReader(str(filename), decode_arrays=True)
        try:
            roots = reader.parse()
        finally:
            reader.close()
        def child(node, name):
            values = [c for c in node.children if c.name == name]
            if len(values) != 1:
                raise RuntimeError("原生 FBX 缺少唯一字段: " + name)
            return values[0]
        objects = [r for r in roots if r.name == "Objects"]
        geometries = [g for obj in objects for g in obj.children if g.name == "Geometry"]
        if len(geometries) != 1:
            raise RuntimeError("原生 FBX 不是唯一网格")
        geometry = geometries[0]
        pv = child(geometry, "Vertices").props[0][3]
        polygons = child(geometry, "PolygonVertexIndex").props[0][3]
        rgba, color_indices, color_storage = normal01_render_colors(geometry, source,
            vertex_color=vertex_color, export_source_mesh=export_source_mesh)
        uv_layers = [n for n in geometry.children if n.name == "LayerElementUV" and n.props == [0]]
        if len(uv_layers) != 1:
            raise RuntimeError("原生 FBX 缺少唯一 UV0")
        uv_layer = uv_layers[0]
        if (child(uv_layer, "MappingInformationType").props[0] != b"ByPolygonVertex"
                or child(uv_layer, "ReferenceInformationType").props[0] != b"IndexToDirect"):
            raise RuntimeError("未核实的原生 UV0 映射")
        exported_uvs = child(uv_layer, "UV").props[0][3]
        uv_indices = child(uv_layer, "UVIndex").props[0][3]
        if (len(pv) % 3 or len(uv_indices) != len(polygons) or len(exported_uvs) % 2
                or any(not 0 <= (i if i >= 0 else -i - 1) < len(pv) // 3 for i in polygons)
                or any(not 0 <= i < len(exported_uvs) // 2 for i in uv_indices)):
            raise RuntimeError("原生 FBX 位置／UV0 角点数组不完整")
        color_errors, alphas = 0, set()
        for corner, encoded in enumerate(polygons):
            point = encoded if encoded >= 0 else -encoded - 1
            # FFbxDataConverter 的 UE→FBX 为 (X,-Y,Z)。
            p = (pv[point * 3], -pv[point * 3 + 1], pv[point * 3 + 2])
            candidates = [i for i, pos in enumerate(positions) if max(abs(a - b) for a, b in zip(p, pos)) <= .0003]
            uv = exported_uvs[uv_indices[corner] * 2:uv_indices[corner] * 2 + 2]
            candidates = [i for i in candidates if max(abs(uv[0] - half(source["m_UV0"][i * 2])),
                abs(uv[1] - (1 - half(1 - source["m_UV0"][i * 2 + 1])))) <= 2e-6]
            actual = rgba[color_indices[corner] * 4:color_indices[corner] * 4 + 4]
            alphas.add(actual[3])
            # 源色经原生 FColorBuffer 保存为8bit；这里核实际角点，不只核颜色集合。
            expected_colors = [[round(c * 255) / 255 for c in source["m_Colors"][i * 4:i * 4 + 4]] for i in candidates]
            color_errors += not any(max(abs(a - b) for a, b in zip(actual, expected)) < .005 for expected in expected_colors)
        if color_errors:
            raise RuntimeError("新网格真实源颜色角点不符: " + str((pid, color_errors)))
        rows.append({"path": item["path"], "sourcePID": pid, "vertex_count": native_vertices,
                     "triangle_count": len(all_triangles), "uv_mismatches": uv_errors,
                     "normal_mismatches": normal_errors, "color_mismatches": color_errors,
                     "color_storage": color_storage, "export_vertex_color": vertex_color,
                     "export_source_mesh": export_source_mesh,
                     "alpha_levels": sorted(alphas), "render_fbx": str(filename),
                     "render_fbx_sha256": hashlib.sha256(filename.read_bytes()).hexdigest()})
    return rows


def normal01_created_packages(manifest, report_path, expected_sha, disk):
    """仅消费完整十件已保存、旧 NS 尚未迁移的真实颜色校验失败报告。"""
    raw = report_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha.lower():
        raise RuntimeError("已创建阶段报告与冻结 SHA 不同")
    report = json.loads(raw.decode("utf-8-sig"))
    targets = set(manifest["targets"])
    owned = {r[k] for r in manifest["materials"].values() for k in ("master", "instance")}
    owned.update(r["path"] for r in manifest["imports"]["entries"].values())
    if (len(manifest["materials"]) != 4 or len(manifest["imports"]["entries"]) != 2
            or len(targets) != 10 or targets != owned or NORMAL01_SYSTEM in targets
            or report["system"] != NORMAL01_SYSTEM or report["saved"] is not False
            or report["errors"] != ["原生 FBX 缺少唯一字段: LayerElementColor"]
            or len(report["saved_new_packages"]) != 10 or set(report["saved_new_packages"]) != targets
            or set(report["new_package_hashes"]) != targets
            or report["protected_unchanged"] is not True or report["dirty_after"] != []
            or report["before_configuration"] != manifest["before_configuration"]):
        raise RuntimeError("已创建阶段不是完整十件及未迁移旧 NS 的精确失败批次")
    protected = {p: h for p, h in manifest["protected_hashes"].items() if p != NORMAL01_SYSTEM}
    if report["protected_hashes_after"] != protected:
        raise RuntimeError("已创建阶段原保护集合或身份不同")
    if hashlib.sha256(Path(report["backup"]).read_bytes()).hexdigest() != manifest["protected_hashes"][NORMAL01_SYSTEM]:
        raise RuntimeError("已创建阶段旧 NS 备份身份不同")
    for package, expected in {**manifest["protected_hashes"], **report["new_package_hashes"]}.items():
        if hashlib.sha256(disk(package).read_bytes()).hexdigest() != expected:
            raise RuntimeError("已创建阶段实际包身份不同: " + package)
    return report


def normal01_production(unreal, call, manifest_path, approved, output, *, created_report=None, created_report_sha=None):
    """复用唯一 AssetSession/Builder，既有 NS 只作批准指针迁移及原生编译。"""
    from zzz_fx_asset_session import AssetSession
    from zzz_fx_material_ue import Builder, MT
    from zzz_fx_import_assets import apply_imports
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    targets = set(manifest["targets"])
    if set(approved) != targets | {NORMAL01_SYSTEM}:
        raise RuntimeError("生产批准清单必须与完整批次精确相等")
    saved = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())).resolve()
    output = output.resolve()
    if not output.is_relative_to(saved) or output.exists():
        raise RuntimeError("生产报告必须为 Saved 下新文件")
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    def disk(path):
        return content / (path[6:] + ".uasset")
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def dirty():
        return sorted(p.get_path_name() for p in list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
                      + list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()))
    def guard():
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is not None or dirty():
            raise RuntimeError("生产入口需要非 PIE、无未保存包的独立 Editor: " + str(dirty()))
    guard()
    for filename, expected in manifest["input_hashes"].items():
        if sha(Path(filename)) != expected:
            raise RuntimeError("冻结输入已改变: " + filename)
    for path, expected in manifest["protected_hashes"].items():
        if sha(disk(path)) != expected:
            raise RuntimeError("旧包已改变: " + path)
    if bool(created_report) != bool(created_report_sha):
        raise RuntimeError("已创建阶段必须同时提供真实报告与冻结 SHA")
    created = normal01_created_packages(manifest, created_report, created_report_sha, disk) if created_report else None
    before = configuration_snapshot(call, NORMAL01_SYSTEM)
    verify_normal01_configuration(manifest["before_configuration"], before)
    expected, edits = normal01_reference_plan(before, manifest["material_refs"], manifest.get("mesh_refs"))
    backup = output.with_suffix(".NS_before.uasset")
    if backup.exists():
        raise RuntimeError("拒绝覆盖旧 NS 备份")
    backup.write_bytes(disk(NORMAL01_SYSTEM).read_bytes())
    if sha(backup) != manifest["protected_hashes"][NORMAL01_SYSTEM]:
        raise RuntimeError("旧 NS 备份身份不同")
    report = {"system": NORMAL01_SYSTEM, "saved": False, "saved_new_packages": [], "errors": [],
              "backup": str(backup), "before_configuration": before, "materials": {}, "meshes": []}
    if created is not None:
        report.update(saved_new_packages=list(created["saved_new_packages"]),
                      created_stage={"report": str(created_report), "sha256": created_report_sha.lower(),
                                     "saved_in_this_run": []})
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True,
                include_hard_package_references=True, include_searchable_names=False,
                include_soft_management_references=False, include_hard_management_references=False)
    report["old_mesh_consumers"] = {FX_MESH_ROOT + n: sorted(str(p) for p in
        registry.get_referencers(FX_MESH_ROOT + n, options)) for n in ("FXMD_DAO_001", "Eff_Cone_01")}
    by_path = {r[k]: (r, k == "instance") for r in manifest["materials"].values() for k in ("master", "instance")}

    def material_statistics(material):
        # 原生 GetStatistics 等待已有 Shader 编译；读已创建阶段时不另发 recompile。
        stats = unreal.MaterialEditingLibrary.get_statistics(material)
        values = {p: stats.get_editor_property(p) for p in (
            "num_pixel_shader_instructions", "num_vertex_shader_instructions", "num_samplers",
            "num_pixel_texture_samples", "num_vertex_texture_samples")}
        if values["num_pixel_shader_instructions"] <= 0 or values["num_vertex_shader_instructions"] <= 0:
            raise RuntimeError("新材质未形成完整有效 Shader 结果: " + str(values))
        return values

    class NativeTools:
        def tool(self, full_name, **kw):
            if full_name == MT + "recompile":
                material = unreal.EditorAssetLibrary.load_asset(kw["material_or_function"]["refPath"])
                errors = list(unreal.MaterialEditingLibrary.recompile_material(material))
                values = material_statistics(material)
                if errors:
                    raise RuntimeError("新材质原生编译失败: " + str(errors))
                report["materials"][material.get_path_name().rsplit(".", 1)[0]] = {"compile_errors": errors, "statistics": values}
                return {"returnValue": None}
            if full_name == AS + "save_assets":
                for path in kw["asset_paths"]:
                    if path in by_path:
                        row, instance = by_path[path]
                        result = verify_normal01_material(unreal, row, instance=instance)
                        report["materials"].setdefault(path, {}).update(result)
                value = call(full_name, **kw)
                if value is False:
                    raise RuntimeError("新包保存失败")
                for path in kw["asset_paths"]:
                    if not disk(path).is_file():
                        raise RuntimeError("新包未落盘: " + path)
                    if path in by_path:
                        row, instance = by_path[path]
                        verify_normal01_material(unreal, row, instance=instance)
                    report["saved_new_packages"].append(path)
                return {"returnValue": value}
            return {"returnValue": call(full_name, **kw)}

    try:
        if created is None:
            session = AssetSession(NativeTools(), targets, approved)
            builder = Builder(session)
            for row in manifest["materials"].values():
                master = builder.build_master(row["plan"])
                builder.build_instance(row["plan"], master, row["instance"].rsplit("/", 1)[1])
            if manifest.get("imports"):
                apply_imports(manifest["imports"], session, unreal=unreal)
        else:
            for path, (row, instance) in by_path.items():
                result = verify_normal01_material(unreal, row, instance=instance)
                if not instance:
                    result["statistics"] = material_statistics(unreal.EditorAssetLibrary.load_asset(path))
                report["materials"][path] = result
        if manifest.get("imports"):
            report["meshes"] = normal01_mesh_validation(unreal, manifest["imports"], output)
        guard()
        if created is not None:
            for path, expected_hash in created["new_package_hashes"].items():
                if sha(disk(path)) != expected_hash:
                    raise RuntimeError("只读复核改变了已创建包: " + path)
        for path, expected_hash in manifest["protected_hashes"].items():
            if sha(disk(path)) != expected_hash:
                raise RuntimeError("新包复核期间原保护包已改变: " + path)
        # 独立新包都成功后，复核旧 NS 仍未改变才写唯一既有包。
        verify_normal01_configuration(before, configuration_snapshot(call, NORMAL01_SYSTEM))
        if sha(disk(NORMAL01_SYSTEM)) != sha(backup):
            raise RuntimeError("新包创建期间旧 NS 已改变")
        for edit in edits:
            call(NS + "SetRendererData", renderer=edit["renderer"],
                 rendererData={"propertyValues": json.dumps(edit["properties"])})
        verify_normal01_configuration(expected, configuration_snapshot(call, NORMAL01_SYSTEM))
        ref = {"refPath": NORMAL01_SYSTEM + "." + NORMAL01_SYSTEM.rsplit("/", 1)[1]}
        native = call(COMPILE + "ForceCompile", system=ref)
        NiagaraBuilder.verify_native_compilation(NORMAL01_SYSTEM, native)
        if not native["bForceCompileRequested"] or native["bCompilationPending"] or not native["bNativeReady"]:
            raise RuntimeError("Normal01 原生完整编译／Ready 未完成")
        state = call(NS + "GetSystemCompileState", system=ref)
        NiagaraBuilder.verify_compile_state(NORMAL01_SYSTEM, state)
        actual = configuration_snapshot(call, NORMAL01_SYSTEM)
        derived = verify_normal01_configuration(expected, actual)
        native = call(COMPILE + "ReadSystemState", system=ref)
        NiagaraBuilder.verify_native_compilation(NORMAL01_SYSTEM, native)
        if native["bCompilationPending"] or not native["bNativeReady"] or set(dirty()) - {NORMAL01_SYSTEM}:
            raise RuntimeError("最终原生就绪／脏包范围不符")
        system = unreal.EditorAssetLibrary.load_asset(NORMAL01_SYSTEM)
        if not unreal.EditorAssetLibrary.save_loaded_asset(system, False):
            raise RuntimeError("唯一旧 NS 保存失败")
        verify_normal01_configuration(actual, configuration_snapshot(call, NORMAL01_SYSTEM))
        report.update(saved=True, after_configuration=actual, native=native, compile_state=state,
                      compiled_binding_differences=derived, system_hash=sha(disk(NORMAL01_SYSTEM)))
    except Exception as error:
        report["errors"].append(str(error))
        raise
    finally:
        report["protected_hashes_after"] = {p: sha(disk(p)) for p in manifest["protected_hashes"] if p != NORMAL01_SYSTEM}
        report["new_package_hashes"] = {p: sha(disk(p)) for p in report["saved_new_packages"]}
        report["protected_unchanged"] = all(h == manifest["protected_hashes"][p] for p, h in report["protected_hashes_after"].items())
        report["dirty_after"] = dirty()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        unreal.log("NORMAL01_PRODUCTION_RESULT " + str(output))
    if not report["protected_unchanged"] or report["dirty_after"]:
        raise RuntimeError("生产结束时旧包／脏包保护失败")
    return report


def normal01_cold_readback(unreal, call, manifest_path, production_path, output, on_complete):
    """独立冷宿主只读同批包；直接订阅既有原生诊断结果，不添加等待器。"""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    production = json.loads(production_path.read_text(encoding="utf-8-sig"))
    if (production["system"] != NORMAL01_SYSTEM or not production["saved"] or production["errors"]
            or not production["protected_unchanged"] or production["dirty_after"]
            or set(production["new_package_hashes"]) != set(manifest["targets"])):
        raise RuntimeError("冷读需要同批完整成功的真实生产报告")
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    saved = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())).resolve()
    output = output.resolve()
    if output.exists() or not output.is_relative_to(saved):
        raise RuntimeError("冷读输出须是 Saved 内新文件")
    def hashes():
        return {p: hashlib.sha256((content / (p[6:] + ".uasset")).read_bytes()).hexdigest() for p in expected_hashes}
    def dirty():
        return sorted(p.get_path_name() for p in list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
                      + list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()))
    expected_hashes = {**production["protected_hashes_after"], **production["new_package_hashes"],
                       NORMAL01_SYSTEM: production["system_hash"]}
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is not None or dirty():
        raise RuntimeError("冷读需要非 PIE、clean 的独立 Editor")
    if hashes() != expected_hashes:
        raise RuntimeError("冷读磁盘包与真实生产结果不同")
    report = {"system": NORMAL01_SYSTEM, "saved": False, "errors": [], "materials": {}, "meshes": [],
              "before_hashes": hashes()}
    ref = {"refPath": NORMAL01_SYSTEM + "." + NORMAL01_SYSTEM.rsplit("/", 1)[1]}
    original_system = unreal.EditorAssetLibrary.load_asset(NORMAL01_SYSTEM)
    def finish(result):
        try:
            if original_system.get_path_name() != ref["refPath"] or not result.get_editor_property("is_complete"):
                raise RuntimeError("冷读原生结果／资产身份不符")
            if result.get_editor_property("error"):
                raise RuntimeError(result.get_editor_property("error"))
            state = json.loads(result.get_editor_property("value"))["returnValue"]
            NiagaraBuilder.verify_compile_state(NORMAL01_SYSTEM, state)
            native = call(COMPILE + "ReadSystemState", system=ref)
            NiagaraBuilder.verify_native_compilation(NORMAL01_SYSTEM, native)
            if native["bCompilationPending"] or not native["bNativeReady"] or native["bForceCompileRequested"]:
                raise RuntimeError("只读冷资产尚未原生 Ready／发生强制编译请求")
            config = configuration_snapshot(call, NORMAL01_SYSTEM)
            report["compiled_binding_differences"] = verify_normal01_configuration(production["after_configuration"], config)
            report.update(configuration=config, native=native, compile_state=state)
        except Exception as error:
            report["errors"].append(str(error))
            unreal.log_error("NORMAL01_COLD_FAILED " + str(error))
        finally:
            report.update(after_hashes=hashes(), dirty_after=dirty())
            report["bytes_unchanged"] = report["before_hashes"] == report["after_hashes"]
            if not report["bytes_unchanged"] or report["dirty_after"]:
                report["errors"].append("冷读出现磁盘字节／脏包变化")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
            unreal.log("NORMAL01_COLD_RESULT " + str(output))
            if on_complete is not None:
                on_complete()
    try:
        for name, row in manifest["materials"].items():
            result = verify_normal01_material(unreal, row, instance=True)
            stats = unreal.MaterialEditingLibrary.get_statistics(unreal.EditorAssetLibrary.load_asset(row["master"]))
            result["pixel_instructions"] = stats.get_editor_property("num_pixel_shader_instructions")
            if result["pixel_instructions"] <= 0:
                raise RuntimeError("冷材质未形成完整 Shader 结果")
            report["materials"][name] = result
        if manifest.get("imports"):
            report["meshes"] = normal01_mesh_validation(unreal, manifest["imports"], output)
        toolset, name = (NS + "GetSystemCompileState").rsplit(".", 1)
        pending = unreal.ToolsetRegistry.execute_tool(toolset, name, json.dumps({"system": ref}))
    except Exception as error:
        report["errors"].append(str(error))
        report.update(after_hashes=hashes(), dirty_after=dirty())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        if on_complete is not None:
            on_complete()
        raise
    if pending.get_editor_property("is_complete"):
        finish(pending)
    else:
        pending.get_editor_property("on_completed").add_callable(finish)
        pending.broadcast_on_completed_if_complete()
    return pending


def editor_main(on_complete=None):
    """独立标准 Editor 单包入口；只读冷检由原生完成事件收束。

    on_complete 供独立宿主在检查结束后正常关闭；默认不关闭 Editor。
    诊断返回异步结果时，宿主须等完成回调，不能在本函数返回时提前退出。
    """
    import argparse
    import unreal
    from zzz_fx_asset_session import ROOTS

    def completed_value(result, full_name):
        if not result.get_editor_property("is_complete"):
            raise RuntimeError("原生 tool 结果尚未收束: " + full_name)
        if result.get_editor_property("error"):
            raise RuntimeError(result.get_editor_property("error"))
        return json.loads(result.get_editor_property("value"))["returnValue"]

    def call(full_name, **kw):
        toolset, name = full_name.rsplit(".", 1)
        result = unreal.ToolsetRegistry.execute_tool(toolset, name, json.dumps(kw))
        # 写操作仍只消费已收束的同步调用，不改原完整编译／保存边界。
        return completed_value(result, full_name)

    parser = argparse.ArgumentParser(description="原生 Niagara 单包读回／完整重编译")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--inspect-system")
    modes.add_argument("--recompile-system")
    modes.add_argument("--migrate-mesh-orientation")
    modes.add_argument("--inspect-normal01-materials", action="store_true")
    modes.add_argument("--migrate-normal01", action="store_true")
    modes.add_argument("--inspect-normal01-production", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--production-report", type=Path)
    parser.add_argument("--normal01-created-report", type=Path)
    parser.add_argument("--normal01-created-report-sha")
    parser.add_argument("--approved-package", action="append", default=[])
    parser.add_argument("--material-report", type=Path)
    parser.add_argument("--readback-output", type=Path)
    parser.add_argument("--mesh-only", action="store_true", help="只复核两 Mesh，不重复已完成的材质读回")
    parser.add_argument("--read-lod0-sections", action="store_true", help="仅网格模式直接读 LOD0 Section，不重复 FBX 导出")
    parser.add_argument("--quit-editor", action="store_true")
    parser.add_argument("--approved-target")
    parser.add_argument("--expected-sha")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--expected-emitter", action="append", default=[])
    parser.add_argument("--require-ready", action="store_true", help="只读冷启动检查也要求原生 Ready")
    parser.add_argument("--require-current-mesh-orientation", action="store_true", help="只读核七 pin 已使用当前坐标换算")
    args = parser.parse_args()
    if args.normal01_created_report or args.normal01_created_report_sha:
        if not args.migrate_normal01 or not args.normal01_created_report or not args.normal01_created_report_sha:
            parser.error("已创建阶段报告和 SHA 仅成对用于 Normal01 精确生产迁移")
    if args.inspect_normal01_production:
        if not args.manifest or not args.production_report or not args.readback_output or args.approved_package:
            parser.error("只读生产冷检需要 manifest、真实 production-report 和新 readback-output")
        return normal01_cold_readback(unreal, call, args.manifest, args.production_report, args.readback_output,
                                     unreal.SystemLibrary.quit_editor if args.quit_editor else on_complete)
    if args.migrate_normal01:
        if not args.manifest or not args.readback_output or not args.approved_package:
            parser.error("Normal01 生产需 manifest、新 readback-output 和精确 approved-package 全清单")
        return normal01_production(unreal, call, args.manifest, args.approved_package, args.readback_output,
                                   created_report=args.normal01_created_report, created_report_sha=args.normal01_created_report_sha)
    if args.manifest or args.approved_package or args.production_report:
        parser.error("manifest 与 approved-package 仅用于 Normal01 生产")
    if args.inspect_normal01_materials:
        if not args.material_report or not args.readback_output or args.require_ready:
            parser.error("只读材质入口需旧 material-report 与新 readback-output，不请求编译完成")
        if args.read_lod0_sections and not args.mesh_only:
            parser.error("LOD0 Section 读回必须显式 mesh-only")
        try:
            return normal01_material_readback(unreal, call, args.material_report, args.readback_output,
                                             mesh_only=args.mesh_only, read_sections=args.read_lod0_sections)
        finally:
            if on_complete is not None:
                on_complete()
    if args.material_report or args.readback_output or args.quit_editor or args.mesh_only or args.read_lod0_sections:
        parser.error("材质读回参数与 quit-editor 只用于 inspect-normal01-materials")
    path = args.inspect_system or args.recompile_system or args.migrate_mesh_orientation
    writes = bool(args.recompile_system or args.migrate_mesh_orientation)
    if not path.startswith(ROOTS) or not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", path):
        parser.error("必须提供精确的 FX 包路径")
    if writes and (args.approved_target != path or not args.backup or not args.expected_sha or not args.expected_emitter):
        parser.error("重编译需精确 approved-target、expected-sha、既有 backup 及 expected-emitter 清单")
    if (args.migrate_mesh_orientation or args.require_current_mesh_orientation) and path != NORMAL01_SYSTEM:
        parser.error("朝向迁移／冷读仅支持已证 Normal01 系统")
    if args.require_current_mesh_orientation and not args.inspect_system:
        parser.error("require-current-mesh-orientation 仅用于只读冷读")

    def dirty_packages():
        return sorted(p.get_path_name() for p in list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
                      + list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()))

    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is not None:
        raise RuntimeError("单包编译入口需要非 PIE Editor")
    if dirty_packages():
        raise RuntimeError("拒绝覆盖 Editor 已有未保存工作: " + str(dirty_packages()))
    disk = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())) / (path[6:] + ".uasset")
    before_hash = hashlib.sha256(disk.read_bytes()).hexdigest()
    if writes:
        if before_hash != args.expected_sha.lower() or hashlib.sha256(args.backup.read_bytes()).hexdigest() != before_hash:
            raise RuntimeError("原包／备份与保护 SHA 不一致，拒绝重编译")
    ref = {"refPath": path + "." + path.rsplit("/", 1)[1]}
    before = call(COMPILE + "ReadSystemState", system=ref)
    if before["error"] or before["systemPath"] != ref["refPath"]:
        raise RuntimeError("原资产读回失败: " + str(before))
    if args.expected_emitter and (before["emitterNames"] != args.expected_emitter
                                 or before["emitterEnabled"] != [True] * len(args.expected_emitter)):
        raise RuntimeError("原发射器清单／启用状态与保护清单不符: " + str(before))
    report = {"system": path, "beforeHash": before_hash, "before": before, "saved": False}
    unreal.log("FX_COMPILE_BEGIN " + json.dumps(report, ensure_ascii=False))
    if args.require_ready and args.inspect_system:
        # 原生等待入口按需发起已有请求并提取结果；诊断工具本身只观察状态。
        # 直接接其完成事件；不新增 Python Tick、轮询或等待时钟。
        def log_inspection_failure(error):
            unreal.log_error("FX_COMPILE_FAILED " + json.dumps({"system": path, "saved": False,
                             "error": str(error), "beforeHash": before_hash,
                             "afterHash": hashlib.sha256(disk.read_bytes()).hexdigest(),
                             "dirtyAfter": dirty_packages(), "inspection": report}, ensure_ascii=False))

        try:
            original_system = unreal.EditorAssetLibrary.load_asset(path)
            if not original_system or original_system.get_path_name() != ref["refPath"]:
                raise RuntimeError("冷启动原资产身份无效")
            completed = call(COMPILE + "CompletePendingCompilation", system=ref)
            report["nativeCompletedState"] = completed
            unreal.log("FX_COMPILE_PENDING_COMPLETED " + json.dumps({"system": path, "state": completed}, ensure_ascii=False))
            if completed["error"] or completed["systemPath"] != ref["refPath"]:
                raise RuntimeError("原生编译完成入口失败: " + str(completed))
            if (completed["bCompilationPending"] or completed["bNeedsCompileRequest"]
                    or completed["bActiveCompilations"]):
                raise RuntimeError("原生编译完成入口返回后仍未收束: " + str(completed))
            if (completed["emitterNames"] != before["emitterNames"]
                    or completed["emitterEnabled"] != before["emitterEnabled"]
                    or completed["bForceCompileRequested"]):
                raise RuntimeError("原生编译完成入口改变了原发射器身份／启用或显式强制请求")
            tool_name = NS + "GetSystemCompileState"
            toolset, name = tool_name.rsplit(".", 1)
            pending = unreal.ToolsetRegistry.execute_tool(toolset, name, json.dumps({"system": ref}))
            report["nativeDiagnosticWasPending"] = not pending.get_editor_property("is_complete")
        except Exception as error:
            try:
                log_inspection_failure(error)
            finally:
                if on_complete is not None:
                    on_complete()
            raise

        def finish_inspection(result):
            try:
                # 闭包保持原资产存活；实际结果仍来自同一公开原生资产。
                if original_system.get_path_name() != ref["refPath"]:
                    raise RuntimeError("在途编译结束后原资产身份不同")
                compile_state = completed_value(result, tool_name)
                NiagaraBuilder.verify_compile_state(path, compile_state)
                after = call(COMPILE + "ReadSystemState", system=ref)
                NiagaraBuilder.verify_native_compilation(path, after)
                if after["bCompilationPending"] or not after["bNativeReady"]:
                    raise RuntimeError("在途编译收束后原资产仍未原生 Ready: " + str(after))
                if (after["emitterNames"] != before["emitterNames"]
                        or after["emitterEnabled"] != before["emitterEnabled"]
                        or after["bForceCompileRequested"]):
                    raise RuntimeError("只读检查前后原发射器身份／启用或编译请求不同")
                if args.require_current_mesh_orientation:
                    verify_normal01_mesh_basis(call)
                    _, plan = normal01_orientation_plan(configuration_snapshot(call, path), path, require_current=True)
                    report["currentOrientationInputsVerified"] = len(plan)
                final_native = call(COMPILE + "ReadSystemState", system=ref)
                NiagaraBuilder.verify_native_compilation(path, final_native)
                if final_native != after:
                    raise RuntimeError("只读配置检查后原生状态不同: " + str(final_native))
                report.update(after=final_native, compile=compile_state,
                              afterHash=hashlib.sha256(disk.read_bytes()).hexdigest(), dirtyAfter=dirty_packages())
                if report["afterHash"] != before_hash or report["dirtyAfter"]:
                    raise RuntimeError("只读检查改变了原包／存在未保存资产: " + str(report))
                unreal.log("FX_COMPILE_RESULT " + json.dumps(report, ensure_ascii=False))
            except Exception as error:
                log_inspection_failure(error)
                raise
            finally:
                if on_complete is not None:
                    on_complete()

        if pending.get_editor_property("is_complete"):
            finish_inspection(pending)
        else:
            pending.get_editor_property("on_completed").add_callable(finish_inspection)
            # 原 API 要求订阅后广播已完成状态，覆盖完成与绑定之间的竞态。
            pending.broadcast_on_completed_if_complete()
        return pending
    if args.require_current_mesh_orientation:
        verify_normal01_mesh_basis(call)
        _, plan = normal01_orientation_plan(configuration_snapshot(call, path), path, require_current=True)
        report["currentOrientationInputsVerified"] = len(plan)
    if writes:
        config = configuration_snapshot(call, path)
        original_digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        if args.migrate_mesh_orientation:
            verify_normal01_mesh_basis(call)
            config, plan = normal01_orientation_plan(config, path)
        if dirty_packages():
            raise RuntimeError("配置读回期间出现未保存包，拒绝开始编译: " + str(dirty_packages()))
        if args.migrate_mesh_orientation:
            for item in plan:
                stored = call(NS + "SetStackInputData", stackInputRef=item["ref"], inputData=item["after"])
                if stored != item["after"]:
                    raise RuntimeError("朝向 pin 原生写后读回不同，拒绝保存: " + str(item["ref"]))
            report["orientationInputsMigrated"] = [{"ref": item["ref"],
                "beforeDigest": hashlib.sha256(item["before"]["value"]["hlslExpression"].encode()).hexdigest(),
                "afterDigest": hashlib.sha256(item["after"]["value"]["hlslExpression"].encode()).hexdigest()} for item in plan]
        compiled = call(COMPILE + "ForceCompile", system=ref)
        if not compiled["bForceCompileRequested"]:
            raise RuntimeError("原生完整编译未发出: " + str(compiled))
        after = call(COMPILE + "ReadSystemState", system=ref)
        NiagaraBuilder.verify_native_compilation(path, after)
        compile_state = call(NS + "GetSystemCompileState", system=ref)
        NiagaraBuilder.verify_compile_state(path, compile_state)
        if after["bCompilationPending"] or not after["bNativeReady"]:
            raise RuntimeError("原生编译／运行就绪未收束，不保存: " + str(after))
        unreal.log("FX_COMPILE_NATIVE_STATE " + json.dumps({"system": path, "compiled": compiled, "after": after,
                   "compile": {k: compile_state[k] for k in ("aggregateStatus", "bIsCompiling", "bIsStale", "bHasErrors", "bHasWarnings")}},
                   ensure_ascii=False))
        actual_config = configuration_snapshot(call, path)
        differences = list(snapshot_differences(config, actual_config))
        authored, derived = partition_configuration_differences(config, actual_config, differences)
        native_after_snapshot = call(COMPILE + "ReadSystemState", system=ref)
        unreal.log("FX_COMPILE_CONFIG_COMPARE " + json.dumps({"system": path, "differenceCount": len(differences),
                   "authoredDifferenceCount": len(authored), "compiledBindingDifferenceCount": len(derived),
                   "nativeAfterSnapshot": native_after_snapshot}, ensure_ascii=False))
        for difference in differences:
            unreal.log("FX_COMPILE_CONFIG_DIFF " + json.dumps(difference, ensure_ascii=False))
        for difference in derived:
            unreal.log("FX_COMPILE_DERIVED_BINDING_DIFF " + json.dumps(difference, ensure_ascii=False))
        if authored:
            raise RuntimeError("原生编译前后作者配置不同，拒绝保存")
        NiagaraBuilder.verify_native_compilation(path, native_after_snapshot)
        if native_after_snapshot["bCompilationPending"] or not native_after_snapshot["bNativeReady"]:
            raise RuntimeError("配置读回后原生编译／运行就绪未收束，不保存: " + str(native_after_snapshot))
        if set(dirty_packages()) - {path}:
            raise RuntimeError("编译出现原包以外脏资产，拒绝保存: " + str(dirty_packages()))
        system = unreal.EditorAssetLibrary.load_asset(path)
        if system.get_path_name() != ref["refPath"] or not unreal.EditorAssetLibrary.save_loaded_asset(system, False):
            raise RuntimeError("原 Niagara 单包保存失败")
        report.update(after=native_after_snapshot, authoredConfigurationUnchanged=not args.migrate_mesh_orientation,
                      configurationMatchesExpected=True, saved=True,
                      derivedBindingDifferences=derived,
                      configurationDigestBefore=original_digest,
                      expectedConfigurationDigest=hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
                      configurationDigestAfter=hashlib.sha256(json.dumps(actual_config, sort_keys=True).encode()).hexdigest())
    report.update(afterHash=hashlib.sha256(disk.read_bytes()).hexdigest(), dirtyAfter=dirty_packages())
    if report["dirtyAfter"]:
        raise RuntimeError("单包操作后仍有脏资产: " + str(report["dirtyAfter"]))
    unreal.log("FX_COMPILE_RESULT " + json.dumps(report, ensure_ascii=False))
    if on_complete is not None:
        on_complete()


if __name__ == "__main__":
    try:
        editor_main()
    finally:
        if any(mode in sys.argv for mode in ("--inspect-normal01-materials", "--migrate-normal01")) and "--quit-editor" in sys.argv:
            import unreal
            unreal.SystemLibrary.quit_editor()
