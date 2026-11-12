"""按 zzz_fx_niagara 的方案，经同Editor Toolset和原生Stack批量接口制作Niagara系统。

    build_system(path, specs):
        仅创建审批清单内的新内容版本；已有系统保留，禁止删除重建
        CreateNiagaraSystem(DefaultSystem) → 删掉模板自带的 Fountain 发射器
        for spec: AddEmitter(CompletelyEmpty) → 发射器属性 → Emitter State / Spawn Burst / Spawn Rate
                  → 粒子生成 Set Parameters → Particle State + 粒子更新 Set Parameters → Mesh 渲染器
        同一 NS 按有限 Emitter 批完成数据和 Stack，RequestCompile(false) / Wait 后再继续
        最后按当前完整图补齐必要编译，不主动强制更换已完成批的 ForceRebuildId
        编译状态和原生运行就绪均通过后，才保存本批拥有的新包
    作者工具退栈后经原资源门同步回收临时对象；真实NS和DI模板由原生引用保活。
"""
import json
import hashlib
import copy
import re
import sys
import time
import math
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_fx_particle_renderer as PR

NS = "NiagaraToolsets.NiagaraToolset_System."
COMPILE = "GGYGOEditor.GGYGONiagaraCompileLibrary."
RUNTIME_FAILURE_CLASS = "/Script/GGYGO.GGYGONiagaraRuntimeFailureDataInterface"
MATH_CLASS = "/Script/GGYGO.GGYGOFXMathDataInterface"
AS = "editor_toolset.toolsets.asset.AssetTools."
TYPES = {"Bool": "/Script/Niagara.NiagaraBool", "Int": "/Script/Niagara.NiagaraInt32", "Float": "/Script/Niagara.NiagaraFloat", "Vector2": "/Script/CoreUObject.Vector2f", "Vector": "/Script/CoreUObject.Vector3f",
         "Vector4": "/Script/CoreUObject.Vector4f", "Quat": "/Script/CoreUObject.Quat4f",
         "LinearColor": "/Script/CoreUObject.LinearColor", "Position": "/Script/Niagara.NiagaraPosition", "ID": "/Script/Niagara.NiagaraID",
         "ExecutionState": "/Script/Niagara.ENiagaraExecutionState"}
MATH_SIGNATURES = {
    "ComposeAffineStep": (
        (("ParentPosition", "Vector"), ("ParentColumn0", "Vector"), ("ParentColumn1", "Vector"),
         ("ParentColumn2", "Vector"), ("LocalPosition", "Vector"), ("LocalRotation", "Quat"), ("LocalScale", "Vector")),
        (("NextPosition", "Vector"), ("NextColumn0", "Vector"), ("NextColumn1", "Vector"), ("NextColumn2", "Vector"))),
    "EulerZXY": ((("Euler", "Vector"),), (("Quaternion", "Quat"),))}
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
    WPO_BOUNDS_PARAMETER = "User.UEFX_AdditionalWPOBoundsRadiusCM"
    # 同一原 NS 的有限制作批；数据和 Stack 都在批内完成，再等待编译退役。
    AUTHORING_EMITTER_BATCH_SIZE = 8
    # 单个实际编译包的界限；跨包的完整动作组合由调用方配置，不在此重建父图。
    MAX_SYSTEM_EMITTERS = 32
    # 原生ParticleRead按短DataSet名读取；显式保留跨发射器消费字段，防止属性裁剪丢失。
    PARTICLE_TRAIL_SOURCE_ATTRIBUTES = {"ID":"ID", "Lifetime":"Float", "NormalizedAge":"Float",
        "Color":"LinearColor", "USize":"Vector", "UEFX_TrailEmitPoint":"Bool",
        "UEFX_TrailCapturePosition":"Vector", "UEFX_TrailLastPosition":"Vector", "UEFX_TrailLastAge":"Float"}
    DEPTH_VELOCITY_BINDINGS = {"PositionBinding": ("Position", "Position"),
        "VelocityBinding": ("Velocity", "Vector"), "SpriteSizeBinding": ("SpriteSize", "Vector2"),
        "SpriteRotationBinding": ("SpriteRotation", "Float")}
    DEPTH_VELOCITY_CONSTANT_BINDINGS = {"SpriteFacingBinding": "Vector", "SpriteAlignmentBinding": "Vector",
        "CameraOffsetBinding": "Float", "PivotOffsetBinding": "Vector2"}
    COMPONENT_MESH_BINDINGS = {"PositionBinding": ("UEFX_ComponentPosition", "Position"),
        "MeshOrientationBinding": ("UEFX_ComponentOrientation", "Quat"),
        "ScaleBinding": ("UEFX_ComponentScale", "Vector"),
        "VelocityBinding": ("UEFX_ComponentVelocity", "Vector"),
        "DynamicMaterialBinding": ("UEFX_ComponentMaterial0", "Vector4")}
    def __init__(self, session, *, unreal=None):
        self.session = session
        self.m = session.m
        self.native = unreal
        self.native_sync = getattr(self.m, "run_native_sync", None)
        compile_library = getattr(unreal, COMPILE.rstrip(".").rsplit(".", 1)[1], None)
        if (unreal is None or not callable(getattr(unreal, "collect_garbage", None))
                or not callable(self.native_sync)
                or not callable(getattr(self.m, "is_niagara_authoring_batch_active", None))
                or not callable(getattr(compile_library, "apply_stack_batch", None))):
            raise ValueError("Niagara制作需要同Editor的原生Stack批量接口、公开同步回收、同步组装状态查询及原预算/资源调用边界")
        # Python UObject wrapper由原FPyReferenceCollector保活；不能只留JSON对象路径。
        self.authored_system = None
        self.projected_renderers = []
        self.generated_ribbon_renderers = []
        self.depth_velocity_renderers = []
        self.depth_velocity_native_defaults = {}
        self.actual_emitter_names = {}
        self.assignment_di_templates = []
        self.assignment_di_bindings = []
        self.particle_trail_layouts = []
        self._stack_work = None

    def ns(self, name, **kw):
        # 只为本Builder保活的新NS使用数据桥；既有资产的完整脚本拓扑仍走原工具。
        methods = {"AddEmitter":"AuthoringAddEmitter", "GetSystemSummary":"AuthoringGetSystemSummary",
            "GetEmitterTopology":"AuthoringGetRendererIdentities", "AddRenderer":"AuthoringAddRenderer",
            "SetEmitterData":"AuthoringSetEmitterData", "GetEmitterData":"AuthoringGetEmitterData",
            "SetRendererData":"AuthoringSetRendererData", "GetRendererData":"AuthoringGetRendererData"}
        if name in methods and self.authored_system is not None:
            return self._author_data(name,methods[name],kw)
        return self._author_tool(NS + name, **kw)["returnValue"]

    def _author_data(self, name, method, arguments):
        if name in ("AddEmitter","GetSystemSummary"):
            args = dict(arguments)
        else:
            reference_key = {"GetEmitterTopology":"emitterRef", "AddRenderer":"newRendererLocation",
                "SetEmitterData":"emitter", "GetEmitterData":"emitterRef",
                "SetRendererData":"renderer", "GetRendererData":"rendererRef"}[name]
            reference = arguments[reference_key]
            args = {"system":reference["system"],"emitterName":reference["emitterName"]}
            if name == "AddRenderer":
                args["rendererClass"] = arguments["rendererClass"]
            if name in ("SetRendererData","GetRendererData"):
                args["rendererIndex"] = reference["rendererIndex"]
            if name in ("SetEmitterData","SetRendererData"):
                args["propertyValues"] = arguments["emitterData" if name == "SetEmitterData" else "rendererData"]["propertyValues"]
        state = self._author_tool(COMPILE+method,**args)["returnValue"]
        if (state.get("bSucceeded") is not True or state.get("error")
                or state.get("systemPath") != args["system"]["refPath"]
                or state.get("bTransactionClosed") is not True
                or (name not in ("AddEmitter","GetSystemSummary") and (
                    state.get("emitterName") != args["emitterName"] or not state.get("emitterHandleId")))
                or ("rendererIndex" in args and (type(state.get("rendererIndex")) is not int
                    or state["rendererIndex"] != args["rendererIndex"]))):
            identity = {key:state.get(key) for key in ("systemPath","emitterName","emitterHandleId",
                "rendererIndex","rendererClass","rendererPath","error","bTransactionClosed")}
            raise RuntimeError("Niagara原生数据作者身份／操作失败: %s %r" % (name,identity))
        if name == "GetSystemSummary":
            return {"systemName":state["systemPath"].rsplit(".",1)[-1],"emitters":state["emitters"]}
        if name == "GetEmitterTopology":
            return {"emitterName":state["emitterName"],"renderers":[{
                "rendererIndex":row["rendererIndex"],"rendererClass":{"refPath":row["rendererClass"]}}
                for row in state["renderers"]]}
        if name == "AddRenderer":
            if (type(state.get("rendererIndex")) is not int or state["rendererIndex"] < 0
                    or state.get("rendererClass") != args["rendererClass"]["refPath"] or not state.get("rendererPath")):
                raise RuntimeError("新增Renderer未返回准确原生对象身份")
            return {"rendererIndex":state["rendererIndex"],"rendererClass":{"refPath":state["rendererClass"]}}
        if name == "AddEmitter":
            if not state.get("emitterName") or not state.get("emitterHandleId"):
                raise RuntimeError("新增Emitter未返回准确原生句柄身份")
            return state
        return {"propertyValues":state["propertyValues"]}

    def _author_tool(self, tool_identifier, /, **arguments):
        if self.session is not None and not self.m.is_niagara_authoring_batch_active():
            # 组装内保留原Digest缓存；旧排队图未退役，逐工具GC会使后继请求重建副本。
            # 组装外保留原Context/Stack退栈后的回收及预算边界。
            self.native_sync("niagara_retired_editor_objects", self.native.collect_garbage)
        return self.m.tool(tool_identifier, **arguments)

    def _hold_authored_system(self, path):
        self.session.require_created(path)
        system = self.native.load_object(None, self.sref["refPath"])
        if not isinstance(system, self.native.NiagaraSystem) or system.get_path_name() != self.sref["refPath"]:
            raise RuntimeError("不能保活本批创建的准确Niagara System：" + path)
        self.authored_system = system

    def configure_wpo_bounds(self, specs):
        radii = [renderer.get("additional_wpo_bounds_radius_cm", 0.0) for spec in specs
                 for renderer in [spec["renderer"], *spec.get("additional_renderers", [])]]
        if any(type(radius) not in (int, float) or not math.isfinite(radius) or radius < 0.0 for radius in radii):
            raise ValueError("WPO世界空间包围半径必须是有限非负厘米值")
        radius = max(radii, default=0.0)
        variable = {"name": self.WPO_BOUNDS_PARAMETER,
            "type": {"classStructOrEnum": {"refPath": TYPES["Float"]}},
            "defaultValue": self.num("Float", radius),
            "description": "原System各层WPO最大世界空间欧氏半径，普通FX明确为0；原Component消费至尾粒子完成"}
        current = self.ns("GetUserVariables", system=self.sref)["userVariables"]
        if any(item["name"] == self.WPO_BOUNDS_PARAMETER for item in current):
            raise ValueError("create-only System模板已含WPO边界参数，须核实际来源")
        self.ns("AddUserVariables", system=self.sref, variablesToAdd=[variable])
        self.verify_wpo_bounds(radius)
        return radius

    def verify_wpo_bounds(self, radius):
        variables = [item for item in self.ns("GetUserVariables", system=self.sref)["userVariables"]
                     if item["name"] == self.WPO_BOUNDS_PARAMETER]
        if len(variables) != 1:
            raise RuntimeError("原System WPO边界Float类型／半径读回不符")
        self.verify_properties({"type": {"classStructOrEnum": {"refPath": TYPES["Float"]}},
                                "defaultValue": self.num("Float", radius)}, variables[0], self.WPO_BOUNDS_PARAMETER)

    def loc(self, emitter="", script="", module="", inputs=None, renderer=-1):
        return {"system": self.sref, "emitterName": emitter, "scriptName": script, "moduleName": module,
                "rendererIndex": renderer, "inputNameStack": inputs or []}

    def set_input(self, emitter, script, module, name, value):
        if self._stack_work is not None:
            if not isinstance(module,dict) or module.get("kind") != "Module" \
                    or module["emitterName"] != emitter or module["scriptName"] != script:
                raise ValueError("Stack输入没有同一制作计划中的标准模块")
            module["inputs"].append({"namePath":[name],"inputData":value})
            return
        self.ns("SetStackInputData", stackInputRef=self.loc(emitter, script, module, [name]), inputData=value)

    @staticmethod
    def hlsl(expr):
        return {"struct": {"refPath": HLSL}, "value": {"hlslExpression": expr}}

    @staticmethod
    def num(kind, v):
        if kind == "Bool":
            if type(v) not in (int,bool) or v not in (0,1):
                raise ValueError("NiagaraBool 作者输入必须是布尔语义 0/1")
            # FNiagaraBool::SetValue 使用 VM/HLSL 掩码 -1/0；在作者入口编码，读回仍逐字段严格比较。
            v = -1 if v else 0
        return {"struct": {"refPath": "/Script/Niagara.Niagara%s" % kind}, "value": {"value": v}}

    @staticmethod
    def enum(asset, name, display):
        return {"struct": {"refPath": ENUM}, "value": {"enum": {"refPath": asset}, "enumName": name, "displayName": display}}

    def add_module(self, emitter, script, asset):
        if self._stack_work is not None:
            work = {"kind":"Module","emitterName":emitter,"scriptName":script,
                    "moduleAsset":{"refPath":asset},"inputs":[]}
            self._stack_work.append(work)
            return work
        return self.ns("AddModule", moduleLocationRef=self.loc(emitter, script), moduleAsset={"refPath": asset})["moduleName"]

    def set_params(self, emitter, script, entries, *, runtime_failure=None, math_calls=None):
        # 每项仍是独立ParamMap写入；批量Paste保持原序，不合并相邻赋值节点。
        # Alive的DI是真实依赖屏障：原生提交后立即接线，再制作后继赋值。
        begin = 0
        for index, (name, _, expression) in enumerate(entries):
            if math_calls and index in math_calls:
                if begin < index:
                    self._apply_assignment_batch(emitter, script, entries[begin:index])
                for call in math_calls[index]:
                    self._append_native_math_call(emitter, script, call)
                begin = index
            if runtime_failure is not None and name == "Particles.Alive":
                batch = self._apply_assignment_batch(emitter, script, entries[begin:index + 1])
                if self._stack_work is not None:
                    batch["failureSourceReference"] = self._runtime_failure_source(emitter,runtime_failure)
                    batch["originalAliveExpression"] = expression
                else:
                    self._connect_runtime_failure(emitter, script, batch[-1]["moduleName"], expression, runtime_failure)
                begin = index + 1
        if begin < len(entries):
            self._apply_assignment_batch(emitter, script, entries[begin:])

    def require_native_math_support(self, specs):
        if not any(spec.get("_native_math_calls") for spec in specs):
            return
        # 新 wire 类型的显式 ScriptName 同时挡住新 runtime / 旧 Editor DLL 混搭。
        if (self.native.load_class(None, MATH_CLASS) is None
                or getattr(self.native, "GGYGONiagaraAssignmentDIInput", None) is None
                or self._author_tool(COMPILE+"ReadAssignmentDataInterfaceSupport")["returnValue"] is not True):
            raise RuntimeError("实际加载软件缺本批 typed CPU math DI 作者接口，未开始创建资产")

    def native_math_template(self):
        for template in self.assignment_di_templates:
            if template.get_class().get_path_name() == MATH_CLASS:
                return template
        template = self.native.new_object(self.native.load_class(None, MATH_CLASS))
        if template is None or template.get_class().get_path_name() != MATH_CLASS:
            raise RuntimeError("未创建实际 CPU math DI 模板")
        self.assignment_di_templates.append(template)
        return template

    def _append_native_math_call(self, emitter, script, call):
        if self._stack_work is None:
            raise RuntimeError("CPU math DI 必须在原完整 Stack 制作作用域中接线")
        template = self.native_math_template()
        self._stack_work.append({"kind":"AssignmentDI", "emitterName":emitter, "scriptName":script,
            "interfaceTemplate":{"refPath":template.get_path_name()}, **call})

    def _apply_assignment_batch(self, emitter, script, entries):
        assignments = [{"name": name, "type": {"classStructOrEnum": {"refPath": TYPES[kind]}},
                        "hlslExpression": expression} for name, kind, expression in entries]
        if self._stack_work is not None:
            work = {"kind":"Assignments","emitterName":emitter,"scriptName":script,"assignments":assignments}
            self._stack_work.append(work)
            return work
        result = self._author_tool(COMPILE + "ApplyStackBatch", system=self.sref,
            emitterName=emitter, scriptName=script, assignments=assignments)["returnValue"]
        if (result.get("bApplied") is not True or result.get("error") != ""
                or result.get("systemPath") != self.sref["refPath"]
                or result.get("emitterName") != emitter or result.get("scriptName") != script
                or result.get("bViewModelReleased") is not True or result.get("bTransactionClosed") is not True
                or result.get("bReadyForGarbageCollection") is not True):
            raise RuntimeError("Niagara原生赋值批次或资源归还读回失败，保脏图并禁止保存：" + repr(result))
        return self._verify_assignment_modules(result.get("modules"),emitter,script,entries)

    @staticmethod
    def _verify_assignment_modules(modules, emitter, script, entries):
        if not isinstance(modules, list) or len(modules) != len(entries):
            raise RuntimeError("Niagara批量赋值未读回完整独立节点：" + emitter + ":" + script)
        names, guids = set(), set()
        for index, (module, (name, kind, expression)) in enumerate(zip(modules, entries)):
            module_name, guid = module.get("moduleName"), module.get("nodeGuid")
            guid_digits = guid.replace("-", "").lower() if isinstance(guid, str) else ""
            if (type(module.get("index")) not in (int, float) or module["index"] != index
                    or not isinstance(module_name, str) or not module_name or module_name in names
                    or not isinstance(guid, str)
                    or re.fullmatch(r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}", guid) is None
                    or int(guid_digits, 16) == 0 or guid_digits in guids
                    or module.get("target") != name or module.get("typePath") != TYPES[kind]
                    or module.get("hlslExpression") != expression):
                raise RuntimeError("Niagara批量赋值的实际节点/类型/表达式顺序不符：%s:%s[%d] %r" % (
                    emitter, script, index, module))
            names.add(module_name)
            guids.add(guid_digits)
        return modules

    def _runtime_failure_source(self, emitter, runtime_failure):
        policy = PR.validate_runtime_failure_transport(runtime_failure)
        source = (self.sref["refPath"] + "|Emitter=" + emitter + "|Transform=" + policy["source_transform"]
                  + "|Decision=" + policy["decision_reference"])
        if runtime_failure.get("kind") == "SourceMetricFrame":
            source += "|Node="+policy["source_node"]+"|Modules="+",".join(policy["modules"])
        elif runtime_failure.get("kind") == "SourceParticleTrail":
            source += "|Node="+policy["source_node"]+"|Parent="+policy["parent_emitter"]
            source += "|Checks="+",".join(policy["required_checks"])
            if runtime_failure.get("prior_failure") is not None:
                source += "|Prior="+json.dumps(runtime_failure["prior_failure"],ensure_ascii=False,separators=(",", ":"))
        return source

    def _connect_runtime_failure(self, emitter, script, module, original_alive, runtime_failure):
        source = self._runtime_failure_source(emitter,runtime_failure)
        binding = self._author_tool(COMPILE + "ConnectRuntimeFailureToAlive", system=self.sref,
            emitterName=emitter, moduleName=module, sourceReference=source, scriptName=script)["returnValue"]
        self._verify_runtime_failure_binding(binding,emitter,script,module,original_alive,source)

    def _verify_runtime_failure_binding(self, binding, emitter, script, module, original_alive, source):
        if (binding.get("bApplied") is not True or binding.get("bGraphChanged") is not True
                or binding.get("error") or binding.get("systemPath") != self.sref["refPath"]
                or binding.get("emitterName") != emitter or binding.get("moduleName") != module
                or binding.get("scriptName") != script or binding.get("originalAliveExpression") != original_alive
                or binding.get("sourceReference") != source
                or binding.get("dataInterfaceClass") != RUNTIME_FAILURE_CLASS
                or binding.get("failureAttribute") != "Particles.UEFX_RuntimeFailure"
                or not binding.get("interfaceParameter")):
            raise RuntimeError("原 Alive 的运行失败 DI 接线未通过实际读回，禁止编译保存: " + repr(binding))

    def require_particle_trail_support(self, specs):
        if not any(s.get("source_particle_trail") or s.get("particle_trail_child") for s in specs):
            return
        if self.native is None:
            raise RuntimeError("逐粒子拖尾需要原host标准Python创建并配置真实ParticleRead模板")
        value = self._author_tool(COMPILE+"ReadAssignmentDataInterfaceSupport")["returnValue"]
        if value is not True:
            raise RuntimeError("实际加载DLL未支持通用typed DI/Function多out桥，不先创建部分NS")
        library = getattr(self.native,"GGYGONiagaraCompileLibrary",None)
        if library is None or not callable(getattr(library,"read_emitter_data_set_attributes",None)):
            raise RuntimeError("旧host缺源粒子DataSet facet，不先创建部分NS")
        cls = self.native.load_class(None, "/Script/Niagara.NiagaraDataInterfaceParticleRead")
        if cls is None:
            raise RuntimeError("实际加载的ParticleRead类缺失")
        # Python 包装可能只提供 RWBase 的别名表；按实际 UClass 读取原生字段。
        data = json.loads(self._author_tool("editor_toolset.toolsets.object.ObjectTools.get_properties",
            instance={"refPath": "/Script/Niagara.Default__NiagaraDataInterfaceParticleRead"},
            properties=["EmitterBinding"])["returnValue"])
        keys = {key.lower(): key for key in data}
        binding = data.get(keys.get("emitterbinding"))
        if not isinstance(binding, dict):
            raise RuntimeError("实际ParticleRead缺可读EmitterBinding，不先创建部分NS")
        keys = {key.lower(): key for key in binding}
        if (binding.get(keys.get("bindingmode")) not in ("Self", "Other")
                or not isinstance(binding.get(keys.get("emittername")), str)):
            raise RuntimeError("实际ParticleRead缺准确BindingMode／EmitterName ABI: "+repr(binding))

    def particle_reader_template(self, source_spec_name):
        actual = self.actual_emitter_names.get(source_spec_name)
        if actual is None or not re.fullmatch(r"[A-Za-z0-9_]+", actual):
            raise RuntimeError("ParticleRead未取得原AddEmitter实际消歧名")
        data = json.loads(self.ns("GetEmitterData", emitterRef=self.loc(actual))["propertyValues"])
        self.verify_properties({"Name": actual, "SimTarget": "CPUSim", "bRequiresPersistentIDs": True},data,actual)
        cls = self.native.load_class(None, "/Script/Niagara.NiagaraDataInterfaceParticleRead")
        template = self.native.new_object(cls)
        if template is None or template.get_class().get_path_name() != "/Script/Niagara.NiagaraDataInterfaceParticleRead":
            raise RuntimeError("未创建真实非CDO ParticleRead模板")
        reference = {"refPath": template.get_path_name()}
        properties = {"EmitterBinding": {"BindingMode": "Other", "EmitterName": actual}}
        object_tools = "editor_toolset.toolsets.object.ObjectTools."
        applied = self._author_tool(object_tools+"set_properties", instance=reference,
            values=json.dumps(properties))["returnValue"]
        if applied is not True:
            raise RuntimeError("真实ParticleRead EmitterBinding配置失败: "+actual)
        actual_binding = json.loads(self._author_tool(object_tools+"get_properties", instance=reference,
            properties=["EmitterBinding"])["returnValue"])
        self.verify_properties(properties, actual_binding, "ParticleRead."+actual)
        self.assignment_di_templates.append(template)
        return template

    @staticmethod
    def particle_reader_call_outputs(body, script):
        """当前 CPU ParticleRead 先按原序求值纯查询，再由原业务守卫提交结果。"""
        # 参数数目按作者调用；隐式 InstanceData 仍由原 translator 注入。
        signatures = {"GetNumParticles": (0, ("int",)),
            "GetIDByIndex": (1, ("bool", "NiagaraID")),
            "GetParticleIndex": (1, ("int",)),
            "GetFloatByID": (1, ("bool", "float")),
            "GetColorByID": (1, ("bool", "float4")),
            "GetVectorByID": (1, ("bool", "float3")),
            "GetBoolByID": (1, ("bool", "bool"))}
        calls = re.compile(r"\{\{DI\}\}\.([A-Za-z_]\w*)(<[^;\n>]*>)?\(([^;\n()]*)\);")
        if "{{DI}}." in calls.sub("", body):
            raise ValueError("ParticleRead 作者语句含未支持的调用结构")
        call_index = 0

        def writable_outputs(match, queries=None):
            nonlocal call_index
            function, specifiers, arguments = match.groups()
            if function not in signatures:
                raise ValueError("ParticleRead 缺实际函数签名：" + function)
            input_count, types = signatures[function]
            arguments = [value.strip() for value in arguments.split(",")]
            if len(arguments) != input_count + len(types) or not all(arguments):
                raise ValueError("ParticleRead 调用参数数目与真实签名不符：" + function)
            temporaries = ["GGYGO_DIOut_%d_%d" % (call_index, index) for index in range(len(types))]
            call_index += 1
            declarations = [kind + " " + name + ";" for kind, name in zip(types, temporaries)]
            call = "{{DI}}." + function + (specifiers or "") + "(" + ", ".join(
                arguments[:input_count] + temporaries) + ");"
            writeback = [target + "=" + value + ";" for target, value in zip(arguments[input_count:], temporaries)]
            if queries is not None:
                # out 在完整路径由原生查询写入；原业务变量仍留在原提交段，保留 invalid 返回值。
                queries.append(" ".join([*declarations, call]))
                return " ".join(writeback)
            return "{ " + " ".join([*declarations, call, *writeback]) + " }"

        if script == "ParticleSpawnScript":
            parent_guard = "if(IDValid) { int ParentIndex; "
            values_guard = "if(ParentIndex>=0) { "
            if body.count(parent_guard) != 1 or body.count(values_guard) != 1 or not body.endswith("} }"):
                raise ValueError("ParticleRead spawn 语句不是原完整父查询／属性查询守卫")
            prefix, parent = body.split(parent_guard, 1)
            parent, values = parent.split(values_guard, 1)
            predicates = re.findall(r"(\{\{OUT:[^{}]+\}\})=\(ParentIndex>=0\);", parent)
            if len(predicates) != 1 or predicates[0] + "=false;" not in prefix:
                raise ValueError("ParticleRead spawn 缺原先初始化的父存活判定")
            prefix = calls.sub(writable_outputs, prefix)
            queries = []
            parent = calls.sub(lambda match: writable_outputs(match, queries), parent)
            values = calls.sub(lambda match: writable_outputs(match, queries), values[:-3])
            # VVM 的分支展开会搬出纯查询；这里显式建立完整 out，再以原判定提交业务值。
            # ParentAlive 已全路径定义，恰等于原 IDValid && ParentIndex>=0；Index 仍仅在父提交段使用。
            result = (prefix + "\n" + "\n".join(queries) + "\n" + parent_guard + parent
                      + "}\nif(" + predicates[0] + ") { " + values + "}")
        elif script == "ParticleUpdateScript":
            values_guard = "if(ParentIndex>=0) { "
            if body.count(values_guard) != 1 or not body.endswith("}"):
                raise ValueError("ParticleRead update 语句不是原完整父索引／Lifetime 查询守卫")
            prefix, values = body.split(values_guard, 1)
            prefix = calls.sub(writable_outputs, prefix)
            queries = []
            values = calls.sub(lambda match: writable_outputs(match, queries), values[:-1])
            result = prefix + "\n" + "\n".join(queries) + "\n" + values_guard + values + "}"
        elif script == "EmitterUpdateScript":
            result = calls.sub(writable_outputs, body)
        else:
            raise ValueError("ParticleRead 缺已支持的原查询 Script 角色：" + script)
        if not call_index:
            raise ValueError("ParticleRead 作者语句缺真实 DI 调用")
        return result

    def set_assignment_di(self, emitter, script, outputs, body, template):
        """先建同一准确assignment和唯一seed，再由原Native桥接Function多输出。"""
        if (not outputs or outputs[0][1] != "Bool" or len({name for name,_ in outputs}) != len(outputs)
                or any(kind not in TYPES for _,kind in outputs)
                or any("{{OUT:"+name+"}}" not in body for name,_ in outputs) or "{{DI}}" not in body):
            raise ValueError("DI assignment缺全部显式typed目标／Bool seed／准确占位符")
        body = self.particle_reader_call_outputs(body, script)
        if self._stack_work is not None:
            self._stack_work.append({"kind":"ParticleRead","emitterName":emitter,"scriptName":script,
                "interfaceTemplate":{"refPath":template.get_path_name()},"hlslBodyTemplate":body,
                "outputTargets":[{"name":name,"type":{"classStructOrEnum":{"refPath":TYPES[kind]}}}
                    for name,kind in outputs]})
            return
        params = [{"variable": {"name": name,"type": {"classStructOrEnum": {"refPath": TYPES[kind]}}}} for name,kind in outputs]
        mod = self.ns("AddSetParametersModule",moduleLocationRef=self.loc(emitter,script),parameters=params)["moduleName"]
        self.set_input(emitter,script,mod,outputs[0][0],self.hlsl("false"))
        result = self._author_tool(COMPILE+"ConnectAssignmentDataInterface",system=self.sref,emitterName=emitter,
            scriptName=script,moduleName=mod,interfaceTemplate={"refPath":template.get_path_name()},
            outputTargets=[name for name,_ in outputs],hlslBodyTemplate=body)["returnValue"]
        return self._verify_assignment_di(result,emitter,script,mod,outputs)

    def _verify_assignment_di(self, result, emitter, script, mod, outputs):
        if (result.get("bApplied") is not True or result.get("bGraphChanged") is not True or result.get("error")
                or result.get("systemPath") != self.sref["refPath"] or result.get("emitterName") != emitter
                or result.get("scriptName") != script or result.get("moduleName") != mod
                or result.get("dataInterfaceClass") != "/Script/Niagara.NiagaraDataInterfaceParticleRead"
                or result.get("bInterfaceEqualsTemplate") is not True or result.get("customUsage") != "Function"
                or not result.get("assignmentGuid") or not result.get("customGuid")
                or not result.get("interfaceParameter") or "{{" in result.get("hlslBody", "{{")):
            raise RuntimeError("原DI assignment读回失败，保脏图并禁止编译保存: "+repr(result))
        values = result.get("outputs",[])
        if ([row.get("target") for row in values] != [name for name,_ in outputs]
                or any(row.get("typePath") != TYPES[kind]
                    or not isinstance(row.get("outputPin"), str)
                    or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", row["outputPin"]) is None
                    for row,(_,kind) in zip(values,outputs))
                or len({row["outputPin"] for row in values}) != len(outputs)):
            raise RuntimeError("原DI assignment逐目标pin/类型/顺序不符，禁止编译保存")
        self.assignment_di_bindings.append(result)
        return result

    def _verify_math_assignment(self, result, emitter, script, mod, expected):
        """核本次真实 DI、正式函数签名、CPU 绑定与全部 typed 输出；不是运行验收。"""
        body = result.get("hlslBody")
        if (not mod or result.get("bApplied") is not True or result.get("bGraphChanged") is not True
                or result.get("error") or result.get("systemPath") != self.sref["refPath"]
                or result.get("emitterName") != emitter or result.get("scriptName") != script
                or result.get("moduleName") != mod or result.get("dataInterfaceClass") != MATH_CLASS
                or not result.get("dataInterfacePath") or result.get("bInterfaceEqualsTemplate") is not True
                or result.get("functionName") != expected["functionName"] or result.get("bFunctionBound") is not True
                or result.get("customUsage") != "Function" or not result.get("assignmentGuid")
                or not result.get("customGuid") or not result.get("interfaceParameter")
                or not isinstance(body, str) or not body or "{{" in body):
            raise RuntimeError("CPU math DI 实际接线／绑定读回失败，保脏图并禁止编译保存: "+repr(result))
        formal_outputs = [{"name":name, "type":{"classStructOrEnum":{"refPath":TYPES[kind]}}}
                          for name,kind in MATH_SIGNATURES[expected["functionName"]][1]]
        self.verify_properties(expected["functionInputs"], result.get("functionInputs"), "MathDI.functionInputs")
        self.verify_properties(formal_outputs, result.get("functionOutputs"), "MathDI.functionOutputs")
        values = result.get("outputs", [])
        targets = expected["outputTargets"]
        if (not isinstance(values, list) or len(values) != len(targets)
                or any(row.get("target") != target["name"]
                    or row.get("typePath") != target["type"]["classStructOrEnum"]["refPath"]
                    or not isinstance(row.get("outputPin"), str)
                    or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", row["outputPin"]) is None
                    for row,target in zip(values, targets))
                or len({row["outputPin"] for row in values}) != len(targets)):
            raise RuntimeError("CPU math DI 全部目标 pin／类型／顺序读回不符，禁止编译保存")
        self.assignment_di_bindings.append(result)

    def _apply_collected_stack_work(self, work):
        """在同一有限原生作用域应用完整有序Stack计划，不把计划模块当真实节点。"""
        result = self._author_tool(COMPILE+"ApplyAuthoringStackBatch",system=self.sref,workItems=work)["returnValue"]
        if (result.get("bApplied") is not True or result.get("bGraphChanged") is not True or result.get("error")
                or result.get("systemPath") != self.sref["refPath"]
                or result.get("bViewModelReleased") is not True or result.get("bTransactionClosed") is not True
                or result.get("bReadyForGarbageCollection") is not True):
            state = {key:result.get(key) for key in ("systemPath","bApplied","bGraphChanged","error","failedIndex",
                "bViewModelReleased","bTransactionClosed","bReadyForGarbageCollection")}
            raise RuntimeError("完整Stack制作或作用域归还失败，保脏图并禁止保存: "+repr(state))
        rows = result.get("items")
        if not isinstance(rows,list) or len(rows) != len(work):
            raise RuntimeError("完整Stack制作未返回全部有序工作项")
        type_names = {path:name for name,path in TYPES.items()}
        # 仅索引本次已核 DI 的输出来源；不跨制作批保留状态或 UObject。
        system_outputs = {}
        for index,(expected,actual) in enumerate(zip(work,rows)):
            if (type(actual.get("index")) not in (int,float) or actual["index"] != index
                    or any(actual.get(key) != expected[key] for key in ("kind","emitterName","scriptName"))
                    or actual.get("error")):
                identity = {key:actual.get(key) for key in ("index","kind","emitterName","scriptName","error")}
                raise RuntimeError("Stack实际工作项身份／顺序不符: %d %r" % (index,identity))
            emitter,script = expected["emitterName"],expected["scriptName"]
            system_script = script in ("EmitterSpawnScript", "EmitterUpdateScript")
            if expected["kind"] == "Module":
                if not actual.get("moduleName"):
                    raise RuntimeError("标准模块未读回实际节点名: "+emitter+":"+script)
                self._verify_stack_inputs(expected["inputs"],actual.get("inputs"),"Stack."+actual["moduleName"])
            elif expected["kind"] == "Assignments":
                entries = [(entry["name"],type_names[entry["type"]["classStructOrEnum"]["refPath"]],
                            entry["hlslExpression"]) for entry in expected["assignments"]]
                if system_script:
                    entries = self._verify_system_assignment_inputs(entries, actual.get("inputs"),
                        system_outputs.get((emitter,script), {}), emitter+":"+script)
                modules = self._verify_assignment_modules(actual["modules"],emitter,script,entries)
                if expected.get("failureSourceReference"):
                    self._verify_runtime_failure_binding(actual["runtimeFailureBinding"],emitter,script,
                        modules[-1]["moduleName"],expected["originalAliveExpression"],expected["failureSourceReference"])
            elif expected["kind"] == "ParticleRead":
                outputs = [(entry["name"],type_names[entry["type"]["classStructOrEnum"]["refPath"]])
                           for entry in expected["outputTargets"]]
                self._verify_assignment_di(actual["assignmentDIBinding"],emitter,script,actual["moduleName"],outputs)
            elif expected["kind"] == "AssignmentDI":
                self._verify_math_assignment(actual["assignmentDIBinding"], emitter, script, actual["moduleName"], expected)
                if system_script:
                    outputs = system_outputs.setdefault((emitter,script), {})
                    outputs.update((entry["name"],entry["type"]["classStructOrEnum"]["refPath"])
                                   for entry in expected["outputTargets"])
            else:
                raise RuntimeError("Stack计划出现未支持的制作项: "+expected["kind"])
        return {key:result[key] for key in ("bApplied","bGraphChanged","systemPath","bViewModelReleased",
            "bTransactionClosed","bReadyForGarbageCollection")} | {"workItemCount":len(rows)}

    @staticmethod
    def _system_assignment_input(kind, expression, outputs):
        """原式只作来源；按严格字面或本次已核 DI 输出构造预期原生输入。"""
        text = expression.strip()
        if text in outputs:
            if outputs[text] != TYPES[kind]:
                raise ValueError("System赋值的前序DI输出类型不符: "+text)
            return {"struct":{"refPath":"/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked"},
                    "value":{"linkedVariable":{"name":text,
                        "type":{"classStructOrEnum":{"refPath":TYPES[kind]}}}}}
        if kind == "Bool" and text in ("true", "false"):
            return NiagaraBuilder.num("Bool", text == "true")
        number = r"[+-]?(?:(?:0|[1-9][0-9]*)(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?[fF]?"
        fields = {"Float":("value",), "Vector":("x","y","z"), "Quat":("x","y","z","w")}.get(kind)
        if fields:
            tokens = [text]
            if kind != "Float":
                constructor = re.fullmatch(r"float%d\s*\((.*)\)" % len(fields), text, re.DOTALL)
                tokens = [token.strip() for token in constructor[1].split(",")] if constructor else []
            if len(tokens) == len(fields) and all(re.fullmatch(number, token) for token in tokens):
                values = []
                for token in tokens:
                    if not any(marker in token for marker in ".eEfF"):
                        integer = int(token)
                        if not -(2**31) <= integer < 2**31:
                            return NiagaraBuilder.hlsl(expression)
                        values.append(float(integer))
                    else:
                        values.append(float(token.rstrip("fF")))
                try:
                    # 先得到实际 float32 值，包含下溢所得的带符号零，再核 JSON 读回。
                    values = [struct.unpack("<f",struct.pack("<f",value))[0] for value in values]
                    if all(math.isfinite(value) for value in values):
                        return {"struct":{"refPath":TYPES[kind]}, "value":dict(zip(fields,values))}
                except OverflowError:
                    pass  # 非有限 float32 不属于 Local 候选，保留原 HLSL 表示。
        return NiagaraBuilder.hlsl(expression)

    @staticmethod
    def _verify_system_assignment_inputs(entries, actual, outputs, path):
        """同次真实 typed 读回；不将请求原式当作实际 Local／Linked 的证明。"""
        if not isinstance(actual,list) or len(actual) != len(entries):
            raise RuntimeError(path+" System赋值实际输入数量不符")
        module_entries = []
        for index,((name,kind,expression),readback) in enumerate(zip(entries,actual)):
            data = NiagaraBuilder._system_assignment_input(kind,expression,outputs)
            # Local/Linked 节点没有原 HLSL；原请求仍留在 Work 中，不冒充实际节点读回。
            module_entries.append((name,kind,expression if data["struct"]["refPath"] == HLSL else ""))
            input_path = path+"[%d]" % index
            NiagaraBuilder.verify_properties({"namePath":[name],"inputData":{"struct":data["struct"]}},
                                             readback,input_path)
            if data["struct"]["refPath"] in (HLSL, "/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked"):
                NiagaraBuilder.verify_properties({"inputData":data},readback,input_path)
                continue
            values = readback["inputData"].get("value")
            if not isinstance(values,dict):
                raise RuntimeError(input_path+" Local输入缺少实际值")
            for field,requested in data["value"].items():
                value = values.get(field)
                if type(requested) is int:
                    equal = type(value) is int and value == requested
                else:
                    # JSON 数字可能把 -0 写成整数 0；符号位由 Native 同次逐分量位核验保证。
                    equal = (type(value) in (int,float) and math.isfinite(value)
                             and ((requested == 0 and value == 0)
                                  or struct.pack("<f",requested) == struct.pack("<f",value)))
                if not equal:
                    raise RuntimeError("%s Local实际值不符: %s=%r != %r" % (input_path,field,value,requested))
        return module_entries

    @staticmethod
    def _verify_stack_inputs(expected, actual, path):
        """仅按同一 typed Enum 的成员身份兼容原生限定名，其它输入沿原校验。"""
        if not isinstance(actual,list) or len(expected) != len(actual):
            raise RuntimeError(path+" Stack输入读回数组类型或数量不符")
        comparison = copy.deepcopy(expected)
        for index,(requested,readback) in enumerate(zip(comparison,actual)):
            data = requested["inputData"]
            if data["struct"]["refPath"] != ENUM:
                continue
            input_path = path+"[%d].inputData" % index
            actual_data = readback.get("inputData") if isinstance(readback,dict) else None
            # 先核实际 UEnum 资产和 wire 类型；不能将其它枚举的同名成员当成同一个值。
            NiagaraBuilder.verify_properties({"struct":data["struct"],"value":{"enum":data["value"]["enum"]}},
                actual_data,input_path)
            enum_type = data["value"]["enum"]["refPath"].rsplit(".",1)[-1]
            prefix = enum_type+"::"
            expected_name = data["value"]["enumName"]
            member = expected_name.removeprefix(prefix)
            if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*",member) is None:
                raise RuntimeError(input_path+" 枚举请求成员缺失或不属于准确枚举类型: "+repr(expected_name))
            actual_name = actual_data["value"].get("enumName")
            # GetNameByValue 可返回限定名；仅接受准确成员或其准确 UEnum 对象名前缀，不截实际读回。
            if actual_name not in (member,prefix+member):
                raise RuntimeError("%s 枚举成员读回不符: %r != %r" % (input_path,expected_name,actual_name))
            data["value"]["enumName"] = actual_name
        # 只调整比较副本的合法枚举名；原请求、显示文本、输入路径和其它 typed 值均不改。
        NiagaraBuilder.verify_properties(comparison,actual,path)

    @staticmethod
    def validate_particle_trail_spec(spec):
        import zzz_fx_niagara as FN
        child = spec.get("particle_trail_child",{})
        rd = spec["renderer"]
        contract = child.get("contract",{})
        if (not child.get("parent_emitter") or contract.get("schema") != "GGYGO.SourceParticleTrail/v1"
                or child.get("queries") != FN.particle_trail_query_templates()
                or rd.get("generated_ribbon") != FN.generated_ribbon_context()["generated_ribbon"]
                or rd.get("source_trail_length_color") != contract.get("source_trail_length_color")
                or rd.get("source_particle_trail") != contract or rd.get("source_material_slot") != 1
                or rd.get("dynamic_parameter_components") != 0xFFFF or rd.get("field_renderer") is not None
                or spec.get("local_space") is not True or spec.get("loop") is not False
                or spec.get("rate") != 0 or spec.get("bursts") != []
                or any(row[0] == "Particles.Position" for row in spec["update"])):
            raise ValueError("逐粒子拖尾缺准确父／本地历史／两槽／同Function查询合同")
        import zzz_fx_material as FM
        FM.source_trail_length_color_contract({**FN.generated_ribbon_context(),
            "source_trail_length_color": contract["source_trail_length_color"]})
        PR.validate_runtime_failure_transport(spec.get("runtime_failure"))
        update = spec["update"]
        if (len(update)<2 or update[0][0:2] not in (("Particles.UEFX_RuntimeFailure","Float"),["Particles.UEFX_RuntimeFailure","Float"])
                or tuple(update[1]) != ("Particles.Alive","Bool","Particles.Alive")):
            raise ValueError("逐粒子拖尾必须保唯一原失败属性及后继单Alive")
        if (len(update)<3 or tuple(update[2]) != ("Particles.Lifetime","Float",
                "(Particles.UEFX_TrailParentAlive ? Particles.Lifetime : 0.0)")
                or spec.get("requirements") or spec.get("additional_renderers")
                or spec["runtime_failure"]["policy"]["parent_emitter"] != child["parent_emitter"]
                or not re.fullmatch(r"/Game/[A-Za-z0-9_/]+",rd.get("material",""))):
            raise ValueError("逐粒子拖尾缺原生父死亡到期路径／准确父身份或混入额外要求")
        if not {"Particles.Alive","Particles.UEFX_RuntimeFailure","Particles.Position","Particles.Color","Particles.Lifetime"} <= set(name for name,_,_ in spec["spawn"]):
            raise ValueError("逐粒子拖尾出生字段不完整")
        spawn = spec["spawn"]
        failure = ("Particles.UEFX_RuntimeFailure", "Float",
            "(Particles.UEFX_TrailParentAlive && !Particles.UEFX_TrailReadValid ? 22.0 : 0.0)")
        alive = ("Particles.Alive", "Bool",
            "(Particles.UEFX_TrailParentAlive && (!Particles.UEFX_TrailReadValid || Particles.UEFX_TrailParentEmitPoint))")
        names = [name for name,_,_ in spawn]
        if (len(names) != len(set(names)) or tuple(spawn[names.index(failure[0])]) != failure
                or tuple(spawn[names.index(alive[0])]) != alive or names.index(failure[0]) >= names.index(alive[0])):
            raise ValueError("逐粒子拖尾必须先写准确出生失败，再由原Alive经DI报告并筛除无效点")

    def build_particle_trail_emitter(self,s):
        """同NS有限派生采样；原父停发、child只完成所需每父历史和排空。"""
        name = s["name"]
        added = self.ns("AddEmitter",system=self.sref,templateEmitter={"refPath":EMPTY_EMITTER},emitterName=name)
        if added.get("emitterName") != name:
            raise RuntimeError("逐粒子child实际原生名与准备不同")
        self.actual_emitter_names[name] = added["emitterName"]
        self.verify_properties({"Name":name},json.loads(self.ns("GetEmitterData",emitterRef=self.loc(name))["propertyValues"]),name)
        self.ns("SetEmitterData",emitter=self.loc(name),emitterData={"propertyValues":json.dumps({
            "bLocalSpace":True,"SimTarget":"CPUSim","InterpolatedSpawnMode":"RunUpdateScript","CalculateBoundsMode":"Dynamic",
            "AttributesToPreserve":["Particles.UniqueID"]})})
        parent = s["particle_trail_child"]["parent_emitter"]
        template = self.particle_reader_template(parent)
        state = self.add_module(name,"EmitterUpdateScript","/Niagara/Modules/Emitter/EmitterState.EmitterState")
        self.set_input(name,"EmitterUpdateScript",state,"Life Cycle Mode",self.enum(
            "/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode","NewEnumerator1","Self"))
        self.set_input(name,"EmitterUpdateScript",state,"Loop Behavior",self.enum(
            "/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions","NewEnumerator0","Infinite"))
        self.set_input(name,"EmitterUpdateScript",state,"Loop Duration",self.num("Float",s["duration"]))
        # 原生循环只提供采样所需Emitter属性；实际有限状态由同Main／父存活／尾点数量在后继assignment唯一收束。
        count = s["particle_trail_child"]["queries"]["count"]
        self.set_assignment_di(name,"EmitterUpdateScript",count["outputs"],count["body"],template)
        spawn_rate = self.add_module(name,"EmitterUpdateScript","/Niagara/Modules/Emitter/SpawnRate.SpawnRate")
        self.set_input(name,"EmitterUpdateScript",spawn_rate,"SpawnRate",self.hlsl("Emitter.UEFX_TrailSpawnRate"))
        query = s["particle_trail_child"]["queries"]["spawn"]
        self.set_assignment_di(name,"ParticleSpawnScript",query["outputs"],query["body"],template)
        self.set_params(name,"ParticleSpawnScript",s["spawn"],runtime_failure=s["runtime_failure"])
        query = s["particle_trail_child"]["queries"]["update"]
        self.set_assignment_di(name,"ParticleUpdateScript",query["outputs"],query["body"],template)
        self.set_params(name,"ParticleUpdateScript",s["update"][:2],runtime_failure=s["runtime_failure"])
        # 先报告出生/本帧锁存错误，再让原生Lifetime处理正常到期，避免0寿命遮掉首错。
        self.set_params(name,"ParticleUpdateScript",s["update"][2:3])
        self.add_module(name,"ParticleUpdateScript","/Niagara/Modules/Update/Lifetime/ParticleState.ParticleState")
        self.set_params(name,"ParticleUpdateScript",s["update"][3:])
        self.build_generated_ribbon_renderer(name,s["renderer"])

    def verify_particle_trail_source_layouts(self,specs):
        parents = [s for s in specs if s.get("source_particle_trail")]
        self.particle_trail_layouts = []
        required = {name:TYPES[kind] for name,kind in self.PARTICLE_TRAIL_SOURCE_ATTRIBUTES.items()}
        for spec in parents:
            actual = self.actual_emitter_names.get(spec["name"])
            if actual is None:
                raise RuntimeError("源DataSet没有本次实际Emitter名")
            result = self._author_tool(COMPILE+"ReadEmitterDataSetAttributes",system=self.sref,emitterName=actual)["returnValue"]
            if (result.get("bReady") is not True or result.get("error") or result.get("emitterName") != actual
                    or result.get("uniqueEmitterName") != actual or not result.get("emitterHandleId")
                    or type(result.get("handleIndex")) is not int or result["handleIndex"] < 0
                    or not result.get("dataSetName") or result.get("bRequiresPersistentIds") is not True):
                identity = {key:result.get(key) for key in ("bReady", "error", "emitterName", "uniqueEmitterName",
                    "emitterHandleId", "handleIndex", "dataSetName", "bRequiresPersistentIds")}
                raise RuntimeError("源真实编译DataSet未Ready／身份／persistent ID不符: %s %r" % (actual,identity))
            rows = result.get("attributes",[])
            values = {row["name"]:row["typePath"] for row in rows}
            missing = sorted(set(required)-set(values))
            type_mismatches = {name:{"expected":kind,"actual":values[name]}
                for name,kind in required.items() if name in values and values[name] != kind}
            if len(values) != len(rows) or missing or type_mismatches:
                duplicates = sorted(name for name in values if sum(row["name"] == name for row in rows) > 1)
                raise RuntimeError("源真实DataSet字段不符: %s %s" % (actual,json.dumps({
                    "missing":missing,"type_mismatches":type_mismatches,"duplicates":duplicates},ensure_ascii=False)))
            self.particle_trail_layouts.append(result)

    def build_emitter(self, s):
        self.validate_spec(s)
        if s.get("source_mode") == "Emitter":
            self.build_component_emitter(s)
            return
        if s.get("particle_trail_child"):
            self.build_particle_trail_emitter(s)
            return
        name = s["name"]
        added = self.ns("AddEmitter", system=self.sref, templateEmitter={"refPath": EMPTY_EMITTER}, emitterName=name)
        actual = added.get("emitterName")
        if actual != name:
            raise RuntimeError("新Emitter实际名与唯一准备名不同，拒绝以猜测名继续: "+repr(added))
        self.actual_emitter_names[name] = actual
        properties = {"bLocalSpace": s["local_space"], "SimTarget": "CPUSim", "InterpolatedSpawnMode": "RunUpdateScript"}
        if "native_particle_limit" in s:
            properties.update(AllocationMode="FixedCount", PreAllocationCount=s["native_particle_limit"])
        if s.get("requires_persistent_ids"):
            properties["bRequiresPersistentIDs"] = True
        if s.get("source_particle_trail"):
            properties["AttributesToPreserve"] = ["Particles."+field for field in self.PARTICLE_TRAIL_SOURCE_ATTRIBUTES]
        if s["renderer"]["kind"] == "generated_ribbon":
            properties["AttributesToPreserve"] = ["Particles.UniqueID"]
        if s["renderer"].get("native_prop_contract") is not None:
            properties["AttributesToPreserve"] = ["Particles.UStable", "Particles.UEFX_SourceCustom1", "Particles.UEFX_SourceCustom2"]
        if s["renderer"].get("mesh_affine") is not None or s["renderer"].get("sprite_geometry") is not None \
                or s["renderer"]["kind"] in ("projected_decal", "generated_ribbon"):
            properties["CalculateBoundsMode"] = "Dynamic"
        # 同一 emitter 的属性沿原接口一次提交，避免为中间属性组合反复初始化编译上下文。
        self.ns("SetEmitterData", emitter=self.loc(name), emitterData={"propertyValues": json.dumps(properties)})
        self.verify_properties({"Name": actual, **properties}, json.loads(
            self.ns("GetEmitterData", emitterRef=self.loc(actual))["propertyValues"]), actual)
        math_calls = s.get("_native_math_calls", {})
        self.set_params(name, "EmitterSpawnScript", s.get("emitter_spawn", []), math_calls=math_calls.get("emitter_spawn"))
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
        self.set_params(name, "EmitterUpdateScript", s.get("emitter_update", []), math_calls=math_calls.get("emitter_update"))
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
        rate = s["rate"]
        if isinstance(rate, dict):
            if set(rate) != {"kind", "attribute", "source_field", "bounds"} \
                    or rate["kind"] != "EmitterSourceCurve" or rate["attribute"] != "Emitter.UEFX_SpawnRate" \
                    or len(rate["bounds"]) != 2 or any(type(value) not in (int, float) or not math.isfinite(value) for value in rate["bounds"]) \
                    or not 0 <= rate["bounds"][0] < rate["bounds"][1] \
                    or sum(row[0] == rate["attribute"] and row[1] == "Float" for row in s.get("emitter_update", [])) != 1:
                raise ValueError("Emitter SourceCurve缺有限非负值域及唯一的当次Update写入者")
            r = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/SpawnRate.SpawnRate")
            self.set_input(name, "EmitterUpdateScript", r, "SpawnRate", self.hlsl(rate["attribute"]))
        elif rate > 0:
            r = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/SpawnRate.SpawnRate")
            self.set_input(name, "EmitterUpdateScript", r, "SpawnRate", self.num("Float", rate))
        if s.get("distance_rate", 0) > 0:
            r = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/SpawnPerUnit.SpawnPerUnit")
            # Latest native version takes spacing in cm, not particles/cm.
            self.set_input(name, "EmitterUpdateScript", r, "Spawn Spacing", self.num("Float", 100.0 / s["distance_rate"]))
            self.set_input(name, "EmitterUpdateScript", r, "Velocity Vector", self.hlsl("Transient.UEFX_EmissionVelocity"))
            self.set_input(name, "EmitterUpdateScript", r, "Module.Use Movement Tolerance", self.num("Bool", 0))
            self.set_input(name, "EmitterUpdateScript", r, "Module.Use Max Movement Threshold", self.num("Bool", 0))
        self.set_params(name, "ParticleSpawnScript", s["spawn"], math_calls=math_calls.get("spawn"))
        self.add_module(name, "ParticleUpdateScript", "/Niagara/Modules/Update/Lifetime/ParticleState.ParticleState")
        alignment = (s["renderer"].get("mesh_affine") or {}).get("project_alignment")
        self.set_params(name, "ParticleUpdateScript", s["update"], runtime_failure=s.get("runtime_failure") or alignment,
                        math_calls=math_calls.get("update"))
        self.build_renderer(name, s["renderer"])
        for renderer in s.get("additional_renderers", []):
            self.build_renderer(name, renderer)

    def build_component_emitter(self, spec):
        """同 NS 的组件绘制沿系统激活；实际有来源 bounds 属于原生 Emitter。"""
        name = spec["name"]
        added = self.ns("AddEmitter", system=self.sref, templateEmitter={"refPath": EMPTY_EMITTER}, emitterName=name)
        if added.get("emitterName") != name:
            raise RuntimeError("组件Emitter实际名不符: requested=%r actual=%r" % (name,added.get("emitterName")))
        self.actual_emitter_names[name] = added["emitterName"]
        box = {"Min": dict(zip("xyz", spec["fixed_bounds"]["min"])),
               "Max": dict(zip("xyz", spec["fixed_bounds"]["max"])), "IsValid": 1}
        properties = {"bLocalSpace": True, "SimTarget": "CPUSim", "CalculateBoundsMode": "Fixed", "FixedBounds": box}
        self.ns("SetEmitterData", emitter=self.loc(name), emitterData={"propertyValues": json.dumps(properties)})
        self.verify_properties({"Name":name, **properties}, json.loads(
            self.ns("GetEmitterData", emitterRef=self.loc(name))["propertyValues"]), name)
        math_calls = spec.get("_native_math_calls", {})
        self.set_params(name, "EmitterSpawnScript", spec["emitter_spawn"], math_calls=math_calls.get("emitter_spawn"))
        state = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/EmitterState.EmitterState")
        self.set_input(name, "EmitterUpdateScript", state, "Life Cycle Mode", self.enum(
            "/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode", "NewEnumerator0", "System"))
        self.set_params(name, "EmitterUpdateScript", spec["emitter_update"], math_calls=math_calls.get("emitter_update"))
        if spec["renderer"]["kind"] == "component_mesh":
            for draw in spec["renderer"]["draws"]:
                metadata = self.ns("AddRenderer", newRendererLocation=self.loc(name),
                    rendererClass={"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"})
                self.ns("SetRendererData", renderer=self.loc(name, renderer=metadata["rendererIndex"]),
                    rendererData={"propertyValues": json.dumps(self.component_mesh_properties(name, draw))})
                path = draw["material"]
                applied = self._author_tool(COMPILE+"BindMeshUserMaterial", system=self.sref, emitterName=name,
                    rendererIndex=metadata["rendererIndex"], parameterName=draw["user_material"],
                    material={"refPath": path+"."+path.rsplit("/",1)[1]})["returnValue"]
                self.verify_properties({"bApplied": True, "error": "", "systemPath": self.sref["refPath"],
                    "emitterName": name, "rendererIndex": metadata["rendererIndex"],
                    "parameterName": draw["user_material"], "materialPath": path+"."+path.rsplit("/",1)[1]}, applied, name)
        else:
            self.build_renderer(name, spec["renderer"])

    @classmethod
    def component_mesh_properties(cls, name, draw):
        properties = EmitterMeshBuilder.renderer_properties(name, draw, bindings=cls.COMPONENT_MESH_BINDINGS)
        if draw.get("phase_visibility"):
            properties.update(RendererVisibility=0, RendererVisibilityTagBinding={
                "RootName": "UEFX_PhaseVisibility", "DataSetName": "UEFX_PhaseVisibility",
                "BindingSourceMode": "ExplicitEmitter",
                "ParamMapVariable": {"Name": name + ".UEFX_PhaseVisibility"},
                "CachedDisplayName": "Emitter.UEFX_PhaseVisibility"})
        for suffix in ("1", "2", "3"):
            properties["DynamicMaterial"+suffix+"Binding"] = cls.attribute_binding(None)
        return properties

    @classmethod
    def validate_component_mesh_spec(cls, spec):
        import zzz_fx_niagara as FN
        renderer = spec["renderer"]
        FN.component_mesh_policy(renderer["policy"])
        FN.validate_component_geometry(renderer["source_geometry"])
        if renderer.get("source_mode") != "Emitter" or not spec.get("local_space") \
                or spec.get("lifecycle") != "NativeComponentActivation" \
                or spec.get("bounds_source") != "SourceNodeHermiteConvexHullAndMeshVertices" \
                or renderer.get("dynamic_parameter_components") != 1 \
                or any(spec.get(k) for k in ("spawn", "update", "bursts", "rate", "requirements", "additional_renderers")):
            raise ValueError("MeshRenderer缺原Emitter/同NS生命周期/真实几何界限合同")
        EmitterMeshBuilder.validate_bounds(spec["fixed_bounds"])
        expected = {"Emitter."+name: kind for name,kind in cls.COMPONENT_MESH_BINDINGS.values()}
        phase = spec.get("project_phase")
        age = "System.Age"
        if phase is not None:
            start, end = phase.get("start_seconds"), phase.get("end_seconds")
            if phase.get("configuration_mode") != "ProjectConfigured" or not phase.get("purpose") \
                    or type(start) not in (int, float) or type(end) not in (int, float) \
                    or not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end:
                raise ValueError("组件阶段需要明确有限的项目显隐配置")
            age = "max(0.0, System.Age - " + format(start, '.17g') + ")"
            expected["Emitter.UEFX_PhaseVisibility"] = "Int"
            visibility = "((System.Age >= %s && System.Age < %s) ? 0 : 1)" % (format(start, '.17g'), format(end, '.17g'))
            if any(not draw.get("phase_visibility") for draw in renderer["draws"]) \
                    or any([v for n, _, v in spec[stage] if n == "Emitter.UEFX_PhaseVisibility"] != [visibility]
                           for stage in ("emitter_spawn", "emitter_update")):
                raise ValueError("组件阶段缺准确的原时钟显隐绑定")
        for stage in ("emitter_spawn", "emitter_update"):
            entries = spec[stage]
            if len({entry[0] for entry in entries}) != len(entries) or any(
                    {name: kind for name,kind,_ in entries}.get(name) != kind for name,kind in expected.items()) \
                    or [entry[2] for entry in entries if entry[0] == "Emitter.UEFX_ComponentMaterial0"] \
                        != ["float4(" + age + ",0.0,0.0,0.0)"]:
                raise ValueError("MeshRenderer缺准确类型的原姿态/材质年龄输入")
        if spec["emitter_spawn"] != spec["emitter_update"]:
            raise ValueError("MeshRenderer首帧和更新必须消费相同原System.Age姿态")
        source = renderer["source_contract"]
        kinds = renderer.get("source_material_kinds", {})
        if source.get("kind") != "static_mesh_renderer_source_contract" \
                or set(kinds) != {slot["pid"] for slot in source["materials"]} \
                or any(kind not in ("NapAvatarSimple", "NativeSourceColor") for kind in kinds.values()):
            raise ValueError("MeshRenderer缺各准确源材质的消费角色")
        expected_draws = [(slot, role) for slot in source["materials"]
                          for role in (("outline", "surface") if kinds[slot["pid"]] == "NapAvatarSimple" else ("surface",))]
        if len(renderer["draws"]) != len(expected_draws):
            raise ValueError("MeshRenderer缺全部源槽的实际角色绘制")
        slot_meshes = {}
        for index, ((slot, role), draw) in enumerate(zip(expected_draws, renderer["draws"])):
            if any(draw[k] != slot[s] for k,s in (("source_slot","slot"),("source_submesh","submesh"),("source_material_pid","pid"))) \
                    or draw["role"] != role or draw["sort"] != index \
                    or not re.fullmatch(r"User\.[A-Za-z][A-Za-z0-9_]*", draw.get("user_material", "")) \
                    or any(not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", draw.get(k,"")) for k in ("mesh","material")):
                raise ValueError("MeshRenderer改变了源材质槽/子网格/绘制顺序或缺明确UserMaterial")
            previous = slot_meshes.setdefault(slot["slot"], draw["mesh"])
            if previous != draw["mesh"]:
                raise ValueError("同源槽的角色Mesh不同")

    @staticmethod
    def validate_native_depth_velocity_spec(spec):
        """核准确Primary Sprite或原生TRS Mesh；上一帧仍由原生编译器生成。"""
        import zzz_fx_native_shader as NS
        rd = spec["renderer"]
        contract = NS.project_depth_velocity_contract(rd.get("native_depth_velocity"))
        if contract is None:
            return
        if rd.get("kind") == "mesh":
            if (rd.get("source_material_pid") != contract["material_pid"] or rd.get("source_material_slot") != 0
                    or not rd.get("mesh") or rd.get("mesh_affine") is not None
                    or rd.get("field_renderer") is not None or spec.get("source_mode") is not None):
                raise ValueError("额外Depth/Velocity缺准确单槽原生TRS Mesh")
            attributes = {name:kind for name,kind,_ in spec["spawn"]+spec["update"]}
            if any(attributes.get("Particles."+name) != kind for name,kind in (
                    ("Position", "Position"), ("Scale", "Vector"), ("MeshOrientation", "Quat"))):
                raise ValueError("Mesh额外Depth/Velocity缺当前TRS粒子属性")
            return
        source = spec.get("source_particle_trail", {})
        if (rd.get("kind") != "sprite" or spec.get("source_mode") is not None
                or spec.get("local_space") is not False or rd.get("field_renderer") is not None
                or rd.get("source_material_slot") != 0 or source.get("source_node") != spec["path"]
                or not source.get("source_materials")
                or str(source["source_materials"][0]["m_PathID"]) != contract["material_pid"]
                or source["policy"]["project_primary_geometry"] != "Billboard"
                or rd.get("facing_mode") != "FaceCameraPlane" or rd.get("alignment") != "Unaligned"
                or tuple(rd.get("pivot_uv", ())) != (0.5, 0.5)):
            raise ValueError("额外Depth/Velocity缺准确Primary Billboard／原槽／固定Native几何模式")
        attributes = {name:kind for name,kind,_ in spec["spawn"]+spec["update"]}
        if any(attributes.get("Particles."+name) != kind for name,kind in NiagaraBuilder.DEPTH_VELOCITY_BINDINGS.values()):
            raise ValueError("额外Depth/Velocity缺四个真实current粒子属性")

    @staticmethod
    def validate_spec(spec):
        rd = spec["renderer"]
        if "native_particle_limit" in spec:
            limit = spec["native_particle_limit"]
            lights = [r for r in [rd]+spec.get("additional_renderers", []) if r["kind"] == "light"]
            if (type(limit) is not int or limit <= 0 or len(lights) != 1
                    or lights[0]["contract"].get("native_particle_limit") != limit
                    or lights[0]["contract"].get("allocation_policy") != "NiagaraFixedCount"):
                raise ValueError("原生粒子上限缺准确灯模板及源数量依据")
        NiagaraBuilder.validate_native_depth_velocity_spec(spec)
        if rd["kind"] == "particle_trail_ribbon":
            NiagaraBuilder.validate_particle_trail_spec(spec)
            return
        if rd["kind"] == "generated_ribbon":
            NiagaraBuilder.validate_generated_ribbon_spec(spec)
            return
        if spec.get("source_mode") == "Emitter":
            if rd["kind"] == "component_mesh":
                NiagaraBuilder.validate_component_mesh_spec(spec)
                return
            if (rd["kind"] != "light" or rd.get("source_mode") != "Emitter" or not spec["local_space"]
                    or rd.get("field_renderer") is not None
                    or spec.get("lifecycle") != "NativeComponentActivation"
                    or spec.get("bounds_source") != "SourceNodeHermiteConvexHullAndPointRadius"
                    or any(spec.get(key) for key in ("spawn", "update", "bursts", "rate", "requirements", "additional_renderers"))):
                raise ValueError("Component Light requires its sole native Emitter/lifecycle/bounds contract")
            box = spec["fixed_bounds"]
            if set(box) != {"min", "max"} or any(not isinstance(box[k], (list, tuple)) or len(box[k]) != 3
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in box[k]) for k in box) \
                    or any(a > b for a,b in zip(box["min"], box["max"])):
                raise ValueError("Component Light bounds must retain finite source-derived XYZ")
            required = {"Emitter.UEFX_ComponentPosition": "Position", "Emitter.UEFX_ComponentColor": "LinearColor",
                        "Emitter.UEFX_ComponentRadius": "Float", "Emitter.UEFX_ComponentEnabled": "Bool",
                        "Emitter.UEFX_ComponentScattering": "Float"}
            for stage in ("emitter_spawn", "emitter_update"):
                writes = {name: kind for name,kind,_ in spec[stage]}
                if any(writes.get(name) != kind for name,kind in required.items()):
                    raise ValueError("Component Light lacks its exact typed Emitter inputs")
            import zzz_fx_niagara as FN
            FN.project_light_policy(rd["contract"]["policy"])
            return
        failure = spec.get("runtime_failure")
        if failure is not None:
            PR.validate_runtime_failure_transport(failure)
            if (rd.get("mesh_affine") or {}).get("project_alignment") is not None:
                raise ValueError("同一原 Alive 不能同时消费两份空间失败来源")
            indices = [i for i, entry in enumerate(spec["update"]) if entry[0] == "Particles.UEFX_RuntimeFailure"]
            alive = [i for i, entry in enumerate(spec["update"]) if entry[0] == "Particles.Alive"]
            if len(indices) != 1 or len(alive) != 1 or alive[0] != indices[0]+1 \
                    or spec["update"][indices[0]][1] != "Float" \
                    or tuple(spec["update"][alive[0]]) != ("Particles.Alive", "Bool", "Particles.Alive") \
                    or not {"Particles.UEFX_RuntimeFailure", "Particles.Alive"} <= {n for n,_,_ in spec["spawn"]}:
                raise ValueError("Source frame failure must feed its single original Alive/DI consumer")
        extras = spec.get("additional_renderers", [])
        lights = [renderer for renderer in [rd]+extras if renderer["kind"] == "light"]
        prop = rd.get("native_prop_contract")
        additional_meshes = [renderer for renderer in extras if renderer["kind"] == "mesh"]
        if prop is not None:
            expected_forward = {**rd, "material": additional_meshes[0]["material"] if additional_meshes else None,
                                "prop_role": "prop_forward_color", "motion_vector_setting": "Disable"}
            writes = {name: kind for name, kind, _ in spec["update"]}
            if (rd["kind"] != "mesh" or rd.get("prop_role") != "prop_surface"
                    or prop["geometry"] != "NativeTRSOnly" or prop["roles"] != ["prop_surface", "prop_forward_color"]
                    or rd.get("motion_vector_setting") != prop["motion_vector_setting"]
                    or len(additional_meshes) != 1 or additional_meshes[0] != expected_forward
                    or additional_meshes[0]["material"] == rd["material"]
                    or rd.get("mesh_affine") is not None):
                raise ValueError("Prop双角色不共用完整原生geometry／UV／motion合同")
            if (writes.get("Particles.UEFX_SourceCustom1") != "Vector4" or writes.get("Particles.UEFX_SourceCustom2") != "Vector4"
                    or not any(name == "Particles.UStable" and kind == "Vector4" for name, kind, _ in spec["spawn"])):
                raise ValueError("Prop缺原Random/CustomDataSet")
        elif additional_meshes:
            raise ValueError("额外Mesh draw缺明确同源Prop角色合同")
        for renderer in lights:
            contract = renderer.get("contract")
            writes = {name: kind for name, kind, _ in spec["update"]}
            required = {"Particles.UEFX_LightColor": "LinearColor", "Particles.UEFX_LightRadius": "Float",
                        "Particles.UEFX_LightEnabled": "Bool", "Particles.UEFX_LightScattering": "Float"}
            if renderer["kind"] != "light" or not isinstance(contract, dict) \
                    or any(writes.get(name) != kind for name,kind in required.items()) \
                    or "Particles.Position" not in writes \
                    or str(contract["source_module"]["light"]["m_PathID"]) != contract["source_identity"]["pathID"]:
                raise ValueError("Particle Light lacks exact template identity or same-instance typed native bindings")
            # 只核已声明的项目政策；不把未知光度单位、原 URP 宿主或阴影升级为已还原。
            import zzz_fx_niagara as FN
            FN.project_light_policy(contract["policy"])
        if rd["kind"] == "light":
            if spec.get("requirements") or rd.get("field_renderer") or spec.get("additional_renderers") or spec["local_space"]:
                raise ValueError("Light-only source cannot carry an undeclared colour/field renderer")
            return
        if rd["kind"] == "projected_decal":
            contract, required = rd["contract"], rd["required_source_inputs"]
            writes = {name: kind for name, kind, _ in spec["update"]}
            native = {"Position": "Position", "Orientation": "Quat", "Size": "Vector", "Color": "LinearColor",
                      "Fade": "Float", "Visible": "Bool", "SortOrder": "Int"}
            if (spec["local_space"] or spec.get("requirements") or not rd.get("source_node")
                    or not re.fullmatch(r"-?[1-9][0-9]*", rd.get("source_transform", ""))
                    or contract["renderer_class"] != "/Script/GGYGORendering.GGYGOProjectedDecalRendererProperties"
                    or contract["simulation"] != "OriginalCPUInstanceParticles"
                    or required["vector_attributes"] != contract["properties"]["ParticleVectorAttributes"]
                    or any(writes.get(name) != "Vector4" for name in required["vector_attributes"])
                    or any(writes.get("Particles.UEFX_Decal"+name) != kind for name, kind in native.items())
                    or writes.get("Particles.Position") != "Position"):
                raise ValueError("Native Decal缺完整同CPU实例world帧、类型或投影合同")
            return
        NiagaraBuilder.validate_field_renderer(rd)
        if rd["kind"] not in ("mesh", "sprite"):
            raise ValueError("Unsupported Niagara renderer: " + str(rd["kind"]))
        mesh_uv = rd.get("mesh_uv")
        if mesh_uv is not None:
            import zzz_fx_particle_uv as PU
            if rd["kind"] != "mesh" or PU.mesh_uv_adapter(mesh_uv["source_module"], spec["path"]) != mesh_uv \
                    or mesh_uv["contract"]["animated"] and not any(name == "Particles.SubImageIndex" and kind == "Float"
                                                                  for name, kind, _ in spec["update"]):
                raise ValueError("Mesh UV缺同一原模块、通道mask或原寿命帧属性")
        requirements = list(spec.get("requirements", [])) + list(rd.get("requirements", []))
        if requirements:
            raise ValueError("%s unresolved renderer requirements: %s" %
                             (spec["name"], ", ".join(requirements)))
        affine = rd.get("mesh_affine")
        native_facing = rd.get("project_native_facing")
        if native_facing is not None:
            choice = PR.mesh_alignment_policy(native_facing)
            if choice["alignment"] != "NativeCameraPlane" or rd["kind"] != "mesh" or spec["local_space"] \
                    or affine is not None or rd.get("field_renderer") is not None \
                    or not {"Particles.Position", "Particles.Scale", "Particles.MeshOrientation", "Particles.Velocity"} \
                        <= {name for name, _, _ in spec["update"]}:
                raise ValueError("Native Mesh camera plane lacks its ordinary world-space pose/size/velocity contract")
        if affine is not None and (rd["kind"] != "mesh" or not spec["local_space"]
                or affine.get("mode") != "full_affine_local_mesh_v1"
                or affine.get("bounds") != "NativeDynamicSphereWithPositiveScaleBound"
                or affine.get("pivot_consumption") != "NativeMeshOffsetPlusAffineVertexCorrection"
                or affine.get("source_pivot_cm") != rd.get("pivot_offset")
                or type(affine.get("bound_scale")) not in (float, int)
                or not math.isfinite(affine["bound_scale"]) or affine["bound_scale"] <= 0):
            raise ValueError("Incomplete affine geometry/normal/bounds contract")
        alignment = (affine or {}).get("project_alignment")
        if alignment is not None:
            PR.validate_mesh_alignment_transport(alignment)
            mask = rd.get("dynamic_parameter_components")
            required = rd["mesh_affine"]["project_alignment"]["required_components"]
            if type(mask) is not int or mask & required != required:
                raise ValueError("Mesh project basis requires its actual Euler component transport")
            field = rd.get("field_renderer")
            if field is not None and field["properties"]["FieldStreams"]["RequiredDynamicParameterComponents"] != mask:
                raise ValueError("Mesh Euler field mask does not match this actual variant")
            writes = {name for name, _, _ in spec["update"]}
            births = {name for name, _, _ in spec["spawn"]}
            if not {"Particles.MeshOrientation", "Particles.Velocity", "Particles.Scale", "Particles.Position",
                    "Particles.DynamicMaterialParameter2", "Particles.DynamicMaterialParameter3",
                    "Particles.UEFX_RuntimeFailure", "Particles.Alive"} <= writes \
                    or not {"Particles.Velocity", "Particles.Position", "Particles.Alive"} <= births:
                raise ValueError("Mesh basis lacks native identity/real velocity/Euler/rejection producers")
            failure_indices = [i for i, entry in enumerate(spec["update"]) if entry[0] == "Particles.UEFX_RuntimeFailure"]
            alive_indices = [i for i, entry in enumerate(spec["update"]) if entry[0] == "Particles.Alive"]
            if (len(failure_indices) != 1 or len(alive_indices) != 1
                    or alive_indices[0] != failure_indices[0] + 1
                    or tuple(spec["update"][alive_indices[0]]) != ("Particles.Alive", "Bool", "Particles.Alive")
                    or spec["update"][failure_indices[0]][1] != "Float"):
                raise ValueError("Mesh failure must precede its single original Alive DI consumer")
        geometry = rd.get("sprite_geometry")
        if geometry is not None:
            if rd["kind"] != "sprite" or spec["local_space"]:
                raise ValueError("Sprite geometry requires its world-space particle-center contract")
            PR.validate_sprite_geometry(geometry)
            source_pivot = rd.get("source_pivot")
            if not isinstance(source_pivot, (tuple, list)) or len(source_pivot) != 3:
                raise ValueError("Sprite geometry is missing its source pivot")
            source_z = PR.number(source_pivot[2], "source_pivot.z")
            depth = geometry.get("depth_pivot")
            if (depth is None and source_z != 0.0) or (depth is not None and depth["source_pivot_z"] != source_z):
                raise ValueError("Sprite depth transport and source pivot do not match")
            field = rd.get("field_renderer")
            if field is not None:
                streams = field["properties"]["FieldStreams"]
                required = 0x7000 if depth is not None else 0x3000
                if (streams["RequiredDynamicParameterComponents"] & required) != required \
                        or streams["BoundsReference"] != geometry["bounds"]:
                    raise ValueError("Field sprite certificate does not cover its geometry streams/bounds")

        facing = rd.get("material_facing")
        if facing is not None and (facing != "CameraPositionWithViewRoll" or rd["kind"] != "sprite"
                or rd.get("field_renderer") is not None or geometry is None
                or (rd["facing_mode"], rd["alignment"]) != ("FaceCamera", "Unaligned")
                or tuple(rd["pivot_uv"]) != (.5, .5)):
            raise ValueError("Ordinary Facing requires its single native-plane material geometry adapter")

    @staticmethod
    def require_component_mesh_support(mcp, specs):
        if any(spec["renderer"]["kind"] == "component_mesh" for spec in specs):
            if mcp.tool(COMPILE+"ReadMeshUserMaterialSupport")["returnValue"] is not True:
                raise ValueError("实际加载的Native UserMaterial桥不可用，未开始资产变更")

    @staticmethod
    def require_runtime_failure_support(mcp, specs):
        """资产变更前读取实际加载的 DI ABI；配置声明本身不是运行资格。"""
        if not any(spec.get("runtime_failure") is not None or
                   (spec["renderer"].get("mesh_affine") or {}).get("project_alignment") is not None for spec in specs):
            return
        support = mcp.tool(COMPILE + "ReadRuntimeFailureSupport")["returnValue"]
        if (support.get("bSupported") is not True or support.get("error")
                or support.get("dataInterfaceClass") != RUNTIME_FAILURE_CLASS
                or support.get("functionName") != "ReportFailure"
                or support.get("failureAttribute") != "Particles.UEFX_RuntimeFailure"
                or type(support.get("perInstanceBytes")) is not int or support["perInstanceBytes"] <= 0):
            raise RuntimeError("实际加载的 CPU 运行失败 DI 不可用，未开始资产变更: " + repr(support))

    @staticmethod
    def validate_field_renderer(rd):
        field = rd.get("field_renderer")
        if field is None:
            return
        name = "GGYGOSignedFieldMeshRendererProperties" if rd["kind"] == "mesh" else "GGYGOSignedFieldSpriteRendererProperties"
        if set(field) != {"class", "properties"} or field["class"] != "/Script/GGYGORendering." + name:
            raise ValueError("Field renderer class does not match its source geometry")
        properties = field["properties"]
        required = {"FacingMode", "FieldStreams"} if rd["kind"] == "mesh" else {"FieldBasis", "PixelCoverageMode", "FieldStreams"}
        if set(properties) != required:
            raise ValueError("Incomplete field renderer properties")
        streams = properties["FieldStreams"]
        if set(streams) != {"bConfigured", "SourceReference", "TransformOwner", "RequiredDynamicParameterComponents", "BoundsReference"} \
                or streams["bConfigured"] is not True or streams["TransformOwner"] != "MaterialWorldPositionOffset" \
                or any(not isinstance(streams[key], str) or not streams[key] for key in ("SourceReference", "BoundsReference")) \
                or type(streams["RequiredDynamicParameterComponents"]) is not int \
                or not 0 <= streams["RequiredDynamicParameterComponents"] <= 65535:
            raise ValueError("Field source/transform/component-mask/bounds contract is invalid")
        if rd["kind"] == "mesh":
            if properties["FacingMode"] != "Default":
                raise ValueError("Field mesh must retain its uncompensated native basis")
        else:
            basis = properties["FieldBasis"]
            expected = {"NativeViewPlane": ("FaceCameraPlane", "Unaligned"),
                        "NativeVelocityAligned": ("FaceCamera", "VelocityAligned"),
                        "CameraPositionWithViewRoll": ("FaceCamera", "Unaligned")}
            if basis not in expected or (rd["facing_mode"], rd["alignment"]) != expected[basis] \
                    or properties["PixelCoverageMode"] != "Disabled":
                raise ValueError("Field sprite basis/coverage would repeat or replace geometry compensation")

    @staticmethod
    def require_field_renderer_classes(mcp, specs):
        """先读真实 CDO 反射；未加载新模块不先创建任何资源。"""
        checked = set()
        for spec in specs:
            rd = spec["renderer"]
            NiagaraBuilder.validate_field_renderer(rd)
            field = rd.get("field_renderer")
            if field is None or field["class"] in checked:
                continue
            class_name = field["class"].split(".", 1)[1]
            required = ["FieldStreams", "DynamicMaterialBinding", "DynamicMaterial1Binding", "DynamicMaterial2Binding", "DynamicMaterial3Binding"]
            required += ["FacingMode"] if rd["kind"] == "mesh" else ["FieldBasis", "PixelCoverageMode", "UVScaleBinding"]
            value = json.loads(mcp.tool("editor_toolset.toolsets.object.ObjectTools.get_properties",
                instance={"refPath": "/Script/GGYGORendering.Default__" + class_name}, properties=required)["returnValue"])
            keys = {key.lower(): key for key in value}
            if not all(key.lower() in keys for key in required):
                raise ValueError("Loaded field renderer class lacks its declared properties: " + field["class"])
            streams = value[keys["fieldstreams"]]
            if not isinstance(streams, dict) or not {key.lower() for key in field["properties"]["FieldStreams"]}.issubset(
                    {key.lower() for key in streams}):
                raise ValueError("Loaded field renderer stream ABI is incomplete: " + field["class"])
            checked.add(field["class"])

    GENERATED_RIBBON_BINDINGS = {
        "PositionBinding": "Particles.Position", "VelocityBinding": "Particles.Velocity", "ColorBinding": "Particles.Color",
        "RibbonWidthBinding": "Particles.RibbonWidth", "RibbonTwistBinding": "Particles.RibbonTwist",
        "NormalizedAgeBinding": "Particles.UEFX_RawTC6Z", "MaterialRandomBinding": "Particles.UEFX_RawTC6W",
        "DynamicMaterialBinding": "Particles.DynamicMaterialParameter",
        "DynamicMaterial1Binding": "Particles.DynamicMaterialParameter1",
        "DynamicMaterial2Binding": "Particles.DynamicMaterialParameter2",
        "DynamicMaterial3Binding": "Particles.DynamicMaterialParameter3"}

    @staticmethod
    def validate_generated_ribbon_spec(spec):
        import zzz_fx_niagara as FN
        rd = spec["renderer"]
        policy = FN.generated_ribbon_policy(rd.get("generator"))
        if (rd.get("generated_ribbon") != FN.generated_ribbon_context()["generated_ribbon"]
                or rd.get("dynamic_parameter_components") != 0xFFFF or rd.get("field_renderer") is not None
                or rd.get("link_order") != "NativeUniqueID" or spec.get("local_space") is not False
                or spec.get("source_mode") == "Emitter" or spec.get("loop") is not False
                or spec.get("bounds_source") != "NativeRibbonWorldPointsAndWidth"
                or spec.get("requirements") or spec.get("additional_renderers") or spec.get("runtime_failure")):
            raise ValueError("生成拖尾缺同NS World历史／完整22流／Native序号或混入其它几何")
        g = policy["geometry"]
        if (spec.get("duration") != g["duration_seconds"] or spec.get("delay") != g["delay_seconds"]
                or spec.get("rate") != g["points_per_second"] or spec.get("bursts") != []
                or spec.get("emitter_spawn") != [] or spec.get("emitter_update") != []
                or not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", rd.get("material", ""))
                or rd.get("source_mesh", {}).get("mesh") != {"m_FileID": 0, "m_PathID": 0}
                or rd["source_mesh"].get("enabled") is not True):
            raise ValueError("生成拖尾与准确Mesh0源／显式生成时域不同")
        types = {"Particles.Position": "Position", "Particles.Velocity": "Vector", "Particles.Lifetime": "Float",
                 "Particles.Age": "Float", "Particles.NormalizedAge": "Float", "Particles.Alive": "Bool",
                 "Particles.RibbonWidth": "Float", "Particles.RibbonTwist": "Float", "Particles.Color": "LinearColor",
                 "Particles.UEFX_RawTC6Z": "Float", "Particles.UEFX_RawTC6W": "Float",
                 **{"Particles.DynamicMaterialParameter"+(str(i) if i else ""): "Vector4" for i in range(4)}}
        spawn = {name: kind for name,kind,_ in spec["spawn"]}
        update = {name: kind for name,kind,_ in spec["update"]}
        changing = {key: value for key,value in types.items() if key.startswith("Particles.DynamicMaterial")
                    or key in ("Particles.Color", "Particles.UEFX_RawTC6Z", "Particles.UEFX_RawTC6W")}
        if (any(spawn.get(name) != kind for name,kind in types.items()) or update != changing
                or any(name in update for name in ("Particles.Position", "Particles.Age", "Particles.NormalizedAge", "Particles.Lifetime"))
                or len(spawn) != len(spec["spawn"]) or len(update) != len(spec["update"])):
            raise ValueError("生成拖尾typed流不完整或Update重写World出生点／真实生命周期")

    def require_generated_ribbon_support(self, specs):
        if not any(s["renderer"]["kind"] in ("generated_ribbon","particle_trail_ribbon") for s in specs):
            return
        library = getattr(self.native,"GGYGONiagaraCompileLibrary",None) if self.native is not None else None
        methods = ("read_emitter_data_set_attributes", "read_ribbon_unique_id_support",
            "configure_ribbon_unique_id", "read_ribbon_unique_id_state")
        if library is None or any(not callable(getattr(library,method,None)) for method in methods):
            raise RuntimeError("Native Ribbon缺真实typed配置／编译UniqueID读取入口，不先创建部分NS")
        support = self._author_tool(COMPILE+"ReadRibbonUniqueIDSupport")["returnValue"]
        if (support.get("bSupported") is not True or support.get("error")
                or support.get("rendererClass") != "/Script/Niagara.NiagaraRibbonRendererProperties"
                or type(support.get("bDefaultLinkOrderUseUniqueId")) is not bool
                or support.get("defaultRibbonIdTypePath") != TYPES["ID"]):
            raise RuntimeError("实际加载Native Ribbon的UniqueID／完整父ID ABI不符，不先创建部分NS: "+repr(support))
        required = list(self.GENERATED_RIBBON_BINDINGS) + ["Material", "MaterialParameters", "RibbonLinkOrderBinding",
            "RibbonIdBinding", "RibbonFacingBinding", "FacingMode", "Shape", "TessellationMode", "bUseGPUInit",
            "SortOrderHint", "MaxNumRibbons", "UV0Settings", "UV1Settings"]
        data = json.loads(self._author_tool("editor_toolset.toolsets.object.ObjectTools.get_properties",
            instance={"refPath": "/Script/Niagara.Default__NiagaraRibbonRendererProperties"}, properties=required)["returnValue"])
        keys = {key.lower(): key for key in data}
        if not all(key.lower() in keys for key in required):
            raise RuntimeError("已加载Native Ribbon缺准确22流／MaterialParameters ABI")
        age = data[keys["normalizedagebinding"]]
        variable = age.get("ParamMapVariable", age.get("paramMapVariable"))
        if not isinstance(variable, dict) or not any(key.lower() == "typedefhandle" for key in variable):
            raise RuntimeError("Native Ribbon默认Float缺真实TypeDefHandle，不猜注册序号")

    def generated_ribbon_properties(self, rd):
        values = (rd["source_particle_trail"]["policy"]["streams"] if rd["kind"] == "particle_trail_ribbon" else rd["generator"]["streams"])
        properties = {"Material": rd["material"]+"."+rd["material"].rsplit("/", 1)[1],
            "FacingMode": "Screen", "Shape": "Plane", "TessellationMode": "Disabled", "bUseGPUInit": False,
            "SortOrderHint": rd["sort"], "MaxNumRibbons": 1,
            "RibbonFacingBinding": self.attribute_binding(None)}
        properties.update({key: self.attribute_binding(value) for key,value in self.GENERATED_RIBBON_BINDINGS.items()})
        if rd["kind"] == "particle_trail_ribbon":
            properties["MaxNumRibbons"] = 0
        for index in (0, 1):
            properties["UV%dSettings" % index] = {"DistributionMode": "ScaledUsingRibbonSegmentLength",
                "LeadingEdgeMode": "Locked", "TrailingEdgeMode": "Locked",
                "bEnablePerParticleUOverride": False, "bEnablePerParticleVRangeOverride": False,
                "Offset": dict(zip("xy", values["uv%d_offset" % index])),
                "Scale": dict(zip("xy", values["uv%d_scale" % index]))}
        return properties

    def build_generated_ribbon_renderer(self, name, rd):
        renderer = self.ns("AddRenderer", newRendererLocation=self.loc(name),
            rendererClass={"refPath": "/Script/Niagara.NiagaraRibbonRendererProperties"})
        ref = self.loc(name, renderer=renderer["rendererIndex"])
        defaults = json.loads(self.ns("GetRendererData", rendererRef=ref)["propertyValues"])
        # 新数组条目的类型必须来自当前Native Float，不能硬编码TypeDef注册序号。
        keys = {key.lower(): key for key in defaults}
        binding = defaults[keys["normalizedagebinding"]]
        var_key = next((key for key in binding if key.lower() == "parammapvariable"), None)
        if var_key is None:
            raise RuntimeError("新Native Ribbon缺真实Float绑定结构")
        variable = copy.deepcopy(binding[var_key])
        name_key = next((key for key in variable if key.lower() == "name"), None)
        if name_key is None or not any(key.lower() == "typedefhandle" for key in variable):
            raise RuntimeError("新Native Ribbon缺Float名字／TypeDefHandle")
        variable[name_key] = "System.Age"
        age_binding = {"MaterialParameterName": "UEFX_GeneratedRibbonSystemAge",
                       "NiagaraVariable": variable, "ResolvedNiagaraVariable": copy.deepcopy(variable)}
        properties = self.generated_ribbon_properties(rd)
        properties["MaterialParameters"] = {"AttributeBindings": [age_binding], "ScalarParameters": [],
            "VectorParameters": [], "TextureParameters": [], "StaticBoolParameters": []}
        self.ns("SetRendererData", renderer=ref, rendererData={"propertyValues": json.dumps(properties)})
        self.verify_properties(properties, json.loads(self.ns("GetRendererData", rendererRef=ref)["propertyValues"]), name)
        emitter = self.actual_emitter_names[name]
        id_attribute = "Particles.UEFX_TrailParentID" if rd["kind"] == "particle_trail_ribbon" else ""
        state = self._author_tool(COMPILE+"ConfigureRibbonUniqueID", system=self.sref,
            emitterName=emitter, rendererIndex=ref["rendererIndex"], ribbonIdAttribute=id_attribute)["returnValue"]
        self.verify_ribbon_unique_id(state, emitter, ref["rendererIndex"], id_attribute)
        if state.get("bApplied") is not True:
            raise RuntimeError("Native Ribbon稳定出生顺序及完整父ID未实际配置，禁止编译保存: "+repr(state))
        self.generated_ribbon_renderers.append({"name": name, "ref": ref, "properties": properties,
            "ribbon_id_attribute": id_attribute, "native_configuration": state})

    def verify_ribbon_unique_id(self, state, emitter, renderer_index, id_attribute):
        if (state.get("error") or state.get("systemPath") != self.sref["refPath"]
                or state.get("emitterName") != emitter or not state.get("emitterHandleId")
                or type(state.get("rendererIndex")) is not int or state["rendererIndex"] != renderer_index
                or not state.get("rendererPath")
                or state.get("rendererClass") != "/Script/Niagara.NiagaraRibbonRendererProperties"
                or state.get("bLinkOrderUseUniqueId") is not True
                or state.get("ribbonLinkOrderAttribute") != "None"
                or state.get("ribbonLinkOrderTypePath") != TYPES["Float"]
                or state.get("ribbonIdAttribute") != (id_attribute or "None")
                or state.get("ribbonIdDataSetAttribute") != (id_attribute.split(".",1)[1] if id_attribute else "None")
                or state.get("ribbonIdTypePath") != TYPES["ID"]):
            raise RuntimeError("Native Ribbon真实renderer／UniqueID／完整父ID绑定读回不符: "+repr(state))

    def verify_generated_ribbon_bindings(self, specs):
        selected = {s["name"]: s for s in specs if s["renderer"]["kind"] in ("generated_ribbon","particle_trail_ribbon")}
        if set(selected) != {r["name"] for r in self.generated_ribbon_renderers}:
            raise RuntimeError("生成拖尾Renderer数量或原发射器归属不符")
        for row in self.generated_ribbon_renderers:
            topology = self.ns("GetEmitterTopology", emitterRef=self.loc(row["name"]))["renderers"]
            if len(topology) != 1 or topology[0]["rendererClass"] != {"refPath": "/Script/Niagara.NiagaraRibbonRendererProperties"}:
                raise RuntimeError("生成拖尾没有唯一Native Ribbon Renderer")
            expected = copy.deepcopy(row["properties"])
            for key in self.GENERATED_RIBBON_BINDINGS:
                expected[key].update(bBindingExistsOnSource=True, bIsCachedParticleValue=True)
            actual = json.loads(self.ns("GetRendererData", rendererRef=row["ref"])["propertyValues"])
            self.verify_properties(expected, actual, row["name"])
            # UniqueID 缺失时引擎会退回 NormalizedAge；必须核真实编译字段才可采用降序头尾约定。
            emitter = self.actual_emitter_names.get(row["name"])
            if emitter is None:
                raise RuntimeError("Native Ribbon没有本次实际Emitter身份")
            layout = self._author_tool(COMPILE+"ReadEmitterDataSetAttributes",system=self.sref,emitterName=emitter)["returnValue"]
            attributes = layout.get("attributes",[])
            names = {attribute["name"]:attribute["typePath"] for attribute in attributes}
            types = {"PositionBinding": "Position", "VelocityBinding": "Vector", "ColorBinding": "LinearColor",
                "RibbonWidthBinding": "Float", "RibbonTwistBinding": "Float", "NormalizedAgeBinding": "Float",
                "MaterialRandomBinding": "Float", **{"DynamicMaterial"+(str(i) if i else "")+"Binding": "Vector4" for i in range(4)}}
            required = {attribute.split(".",1)[1]:TYPES[types[binding]]
                for binding,attribute in self.GENERATED_RIBBON_BINDINGS.items()}
            required["UniqueID"] = TYPES["Int"]
            if selected[row["name"]]["renderer"]["kind"] == "particle_trail_ribbon":
                required["UEFX_TrailParentID"] = TYPES["ID"]
            # 此处核Renderer持久输入；失败码由原Alive的DI立即锁存并筛除，不是Renderer绑定。
            if (layout.get("bReady") is not True or layout.get("error") or layout.get("emitterName") != emitter
                    or layout.get("uniqueEmitterName") != emitter or not layout.get("emitterHandleId")
                    or type(layout.get("handleIndex")) is not int or layout["handleIndex"] < 0
                    or not layout.get("dataSetName")):
                identity = {key:layout.get(key) for key in ("bReady", "error", "emitterName", "uniqueEmitterName",
                    "emitterHandleId", "handleIndex", "dataSetName")}
                raise RuntimeError("Native Ribbon真实编译DataSet未Ready／身份不符: %s %r" % (emitter,identity))
            missing = sorted(set(required)-set(names))
            type_mismatches = {name:{"expected":kind,"actual":names[name]}
                for name,kind in required.items() if name in names and names[name] != kind}
            if len(names) != len(attributes) or missing or type_mismatches:
                duplicates = sorted(name for name in names if sum(attribute["name"] == name for attribute in attributes) > 1)
                raise RuntimeError("Native Ribbon真实编译DataSet字段不符: %s %s" % (emitter,json.dumps({
                    "missing":missing,"type_mismatches":type_mismatches,"duplicates":duplicates},ensure_ascii=False)))
            state = self._author_tool(COMPILE+"ReadRibbonUniqueIDState", system=self.sref,
                emitterName=emitter, rendererIndex=row["ref"]["rendererIndex"])["returnValue"]
            self.verify_ribbon_unique_id(state, emitter, row["ref"]["rendererIndex"], row["ribbon_id_attribute"])
            if (state.get("bReady") is not True
                    or state.get("emitterHandleId") != layout["emitterHandleId"]
                    or state.get("emitterHandleId") != row["native_configuration"]["emitterHandleId"]
                    or state.get("rendererPath") != row["native_configuration"]["rendererPath"]
                    or state.get("uniqueIdTypePath") != TYPES["Int"]
                    or state.get("bInt32LinkOrderAccessorValid") is not True
                    or state.get("bFloatLinkOrderAccessorValid") is not False
                    or state.get("bInt32RibbonIdAccessorValid") is not False
                    or state.get("bFullRibbonIdAccessorValid") is not bool(row["ribbon_id_attribute"])):
                raise RuntimeError("Native Ribbon真实缓存未采用Int32 UniqueID或完整父ID，拒绝Age／单ID替代: "+repr(state))
            row["compiled_data_set"] = layout
            row["native_compiled_state"] = state
            # 这里只签图编译和真实cached绑定；实例MID的动态Age仍待统一运行窗核对。

    def build_renderer(self, name, rd):
        if rd["kind"] in ("generated_ribbon","particle_trail_ribbon"):
            self.build_generated_ribbon_renderer(name, rd)
            return
        if rd["kind"] == "projected_decal":
            self.build_projected_renderer(name, rd)
            return
        if rd["kind"] == "light":
            policy = rd["contract"]["policy"]
            renderer = self.ns("AddRenderer", newRendererLocation=self.loc(name),
                rendererClass={"refPath": "/Script/Niagara.NiagaraLightRendererProperties"})
            emitter_source = rd.get("source_mode") == "Emitter"
            def bind(particle_name, component_name):
                binding = self.attribute_binding("Emitter.UEFX_Component"+component_name if emitter_source else "Particles."+particle_name)
                if emitter_source:
                    binding["BindingSourceMode"] = "ExplicitEmitter"
                    binding["ParamMapVariable"]["Name"] = name+".UEFX_Component"+component_name
                return binding
            properties = {"SourceMode": "Emitter" if emitter_source else "Particles", "bUseInverseSquaredFalloff": True,
                "bAffectsTranslucency": policy["affect_translucency"], "bAllowMegaLights": False,
                "bMegaLightsCastShadows": False, "bAlphaScalesBrightness": False, "RadiusScale": 1.0,
                "ColorAdd": {"x": 0.0, "y": 0.0, "z": 0.0}, "RendererVisibility": 0,
                "PositionBinding": bind("Position", "Position"),
                "ColorBinding": bind("UEFX_LightColor", "Color"),
                "RadiusBinding": bind("UEFX_LightRadius", "Radius"),
                "LightRenderingEnabledBinding": bind("UEFX_LightEnabled", "Enabled"),
                "VolumetricScatteringBinding": bind("UEFX_LightScattering", "Scattering"),
                "RendererVisibilityTagBinding": self.attribute_binding(None)}
            ref = self.loc(name, renderer=renderer["rendererIndex"])
            self.ns("SetRendererData", renderer=ref, rendererData={"propertyValues": json.dumps(properties)})
            actual = json.loads(self.ns("GetRendererData", rendererRef=ref)["propertyValues"])
            self.verify_properties(properties, actual, name + ".ParticleLight")
            return
        field = rd.get("field_renderer")
        klass = "NiagaraMeshRendererProperties" if rd["kind"] == "mesh" else "NiagaraSpriteRendererProperties"
        renderer_class = field["class"] if field is not None else "/Script/Niagara." + klass
        r = self.ns("AddRenderer", newRendererLocation=self.loc(name), rendererClass={"refPath": renderer_class})
        mat = rd["material"] + "." + rd["material"].rsplit("/", 1)[1]
        properties = {"SortOrderHint": rd["sort"], "SortMode": rd["sort_mode"]}
        if rd["kind"] == "mesh":
            mesh = rd["mesh"] + "." + rd["mesh"].rsplit("/", 1)[1]
            properties.update({"Meshes": [{"Mesh": mesh,
                      "PivotOffset": dict(zip("xyz", rd["pivot_offset"])),
                      "PivotOffsetSpace": rd["pivot_space"]}],
                      "bOverrideMaterials": True, "OverrideMaterials": [{"ExplicitMat": mat}]})
            if rd.get("component_particle_lifecycle") is not None:
                properties.update(SourceMode="Particles", MotionVectorSetting="Approximate",
                    PositionBinding=self.attribute_binding("Particles.Position"),
                    MeshOrientationBinding=self.attribute_binding("Particles.MeshOrientation"),
                    ScaleBinding=self.attribute_binding("Particles.Scale"),
                    VelocityBinding=self.attribute_binding("Particles.Velocity"),
                    ColorBinding=self.attribute_binding("Particles.Color"),
                    DynamicMaterialBinding=self.attribute_binding("Particles.DynamicMaterialParameter"))
            if (rd.get("mesh_uv") or {}).get("contract", {}).get("animated") \
                    and rd["mesh_uv"]["contract"].get("uv_channel_mask", 0) != 0:
                properties.update(MaterialRandomBinding=self.attribute_binding("Particles.SubImageIndex"),
                    SubImageIndexBinding=self.attribute_binding(None), SubImageSize={"x": 1.0, "y": 1.0},
                    bSubImageBlend=False)
            if rd.get("native_prop_contract") is not None:
                properties.update(SourceMode="Particles", MotionVectorSetting=rd["motion_vector_setting"],
                    PositionBinding=self.attribute_binding("Particles.Position"),
                    MeshOrientationBinding=self.attribute_binding("Particles.MeshOrientation"),
                    ScaleBinding=self.attribute_binding("Particles.Scale"),
                    VelocityBinding=self.attribute_binding("Particles.Velocity"))
                age = rd["native_prop_contract"]["system_age_transport"]
                if rd["native_prop_contract"]["system_age_dynamic_parameter_mask"]:
                    property_name = "DynamicMaterialBinding" if age["slot"] == 0 else "DynamicMaterial%dBinding" % age["slot"]
                    attribute_name = "Particles.DynamicMaterialParameter"+(str(age["slot"]) if age["slot"] else "")
                    properties[property_name] = self.attribute_binding(attribute_name)
            if rd.get("project_native_facing") is not None:
                facing = PR.mesh_alignment_policy(rd["project_native_facing"])
                properties["Meshes"][0]["Rotation"] = facing["mesh_rotation"]
                properties.update(FacingMode="CameraPlane", bLockedAxisEnable=False,
                    MeshOrientationBinding=self.attribute_binding("Particles.MeshOrientation"),
                    VelocityBinding=self.attribute_binding("Particles.Velocity"),
                    ScaleBinding=self.attribute_binding("Particles.Scale"))
            if rd.get("mesh_affine") is not None:
                # 原组件 DynamicBounds 已纳入偏移后的 Mesh 界限及正比例球扩展。
                # 未修正的逐粒子剔除球不能代替该 affine 界限。
                properties.update(ScaleBinding=self.attribute_binding("Particles.Scale"),
                    DynamicMaterial3Binding=self.attribute_binding("Particles.DynamicMaterialParameter3"),
                    bEnableFrustumCulling=False, bEnableCameraDistanceCulling=False)
                if rd["mesh_affine"].get("project_alignment") is not None:
                    properties["Meshes"][0].update(Scale={"x": 1.0, "y": 1.0, "z": 1.0},
                        Rotation={"pitch": 0.0, "yaw": 0.0, "roll": 0.0})
                    properties.update(FacingMode="Default", bLockedAxisEnable=False, MotionVectorSetting="AutoDetect",
                        MeshOrientationBinding=self.attribute_binding("Particles.MeshOrientation"),
                        VelocityBinding=self.attribute_binding("Particles.Velocity"),
                        DynamicMaterial2Binding=self.attribute_binding("Particles.DynamicMaterialParameter2"))
            if rd.get("vertex_deformation") is not None:
                properties.update(bEnableFrustumCulling=False, bEnableCameraDistanceCulling=False)
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
            if rd.get("stretch") is not None:
                properties["VelocityBinding"] = self.attribute_binding("Particles.Velocity")
            if rd.get("project_plane") is not None:
                properties["SpriteFacingBinding"] = self.attribute_binding("Particles.SpriteFacing")
                properties["SpriteAlignmentBinding"] = self.attribute_binding("Particles.SpriteAlignment")
            if rd.get("sprite_geometry") is not None:
                properties["UVScaleBinding"] = self.attribute_binding("Particles.UVScale")
                properties["DynamicMaterial3Binding"] = self.attribute_binding("Particles.DynamicMaterialParameter3")
            if rd.get("material_facing") is not None:
                properties.update(bUseMaterialCutoutTexture=False, CutoutTexture="None")
            if rd["subuv"]["animated"]:
                properties["MaterialRandomBinding"] = self.attribute_binding("Particles.SubImageIndex")
        if field is not None:
            properties.update(field["properties"])
            mask = field["properties"]["FieldStreams"]["RequiredDynamicParameterComponents"]
            for slot in range(4):
                suffix = str(slot) if slot else ""
                attribute = "Particles.DynamicMaterialParameter" + suffix if mask & (0xF << (slot * 4)) else None
                properties["DynamicMaterial" + suffix + "Binding"] = self.attribute_binding(attribute)
        if rd["sort_attribute"] is not None:
            # UE 5.8 uses RootName/ParamMapVariable/DataSetName for live lookup;
            # BoundVariable is retained only for loading older editor assets.
            # The new mesh renderer's native Age binding already has Float type.
            attribute = rd["sort_attribute"]
            properties["CustomSortingBinding"] = self.attribute_binding(attribute)
        if rd.get("native_depth_velocity") is not None:
            properties.update(SourceMode="Particles", MotionVectorSetting=rd["native_depth_velocity"]["motion_vector_setting"],
                              bIsEnabled=True)
            if rd["kind"] == "sprite":
                properties.update({key:self.attribute_binding("Particles."+field)
                                   for key,(field,_) in self.DEPTH_VELOCITY_BINDINGS.items()})
        self.ns("SetRendererData", renderer=self.loc(name, renderer=r["rendererIndex"]), rendererData={"propertyValues": json.dumps(
            properties)})
        back = self.ns("GetRendererData", rendererRef=self.loc(name, renderer=r["rendererIndex"]))
        actual = json.loads(back["propertyValues"])
        self.verify_properties(properties, actual, name)
        if rd.get("native_depth_velocity") is not None:
            self.depth_velocity_renderers.append({"emitter":name, "renderer_index":r["rendererIndex"],
                "renderer":self.loc(name, renderer=r["rendererIndex"]), "properties":copy.deepcopy(properties),
                "contract":copy.deepcopy(rd["native_depth_velocity"])})

    def build_projected_renderer(self, name, renderer):
        """Outer持有唯一原生child；沿公开author入口绑定原NS，不猜私有参数结构。"""
        if self.native is None:
            raise ValueError("Native投影需要显式同一标准Editor unreal宿主")
        contract = renderer["contract"]
        metadata = self.ns("AddRenderer", newRendererLocation=self.loc(name),
                           rendererClass={"refPath": contract["renderer_class"]})
        location = self.loc(name, renderer=metadata["rendererIndex"])
        source = self.sref["refPath"]+"|Emitter="+name+"|Transform="+renderer["source_transform"]+"|Node="+renderer["source_node"]
        outer_properties = {**contract["properties"], "SourceReference": source}
        self.ns("SetRendererData", renderer=location, rendererData={"propertyValues": json.dumps(outer_properties)})
        actual = json.loads(self.ns("GetRendererData", rendererRef=location)["propertyValues"])
        self.verify_properties(outer_properties, actual, source)
        keys = {key.lower(): key for key in actual}
        child_ref = actual[keys[contract["native_subobject"].lower()]]
        if not isinstance(child_ref, dict) or set(child_ref) != {"refPath"}:
            raise RuntimeError("Native Decal缺真实已拥有child引用")
        child = self.native.load_object(None, child_ref["refPath"])
        if child is None:
            raise RuntimeError("Native Decal实际child未加载")
        outer = child.get_outer()
        if outer.get_class().get_path_name() != contract["renderer_class"] \
                or getattr(outer, contract["native_authoring_getter"])() != child:
            raise RuntimeError("Native Decal getter改变原child或Outer身份")
        material = self.native.load_asset(renderer["material"])
        system = self.native.load_asset(self.sref["refPath"])
        bound = outer.bind_source_user_material_for_authoring(system, "User.UEFX_DecalMaterial_"+name, material)
        # UE Python 剥离成功 bool：此入口成功仅返回空 Error 字符串，失败返回 None。
        if not isinstance(bound, str) or bound:
            raise RuntimeError("Native Decal原UserMaterial绑定失败："+source+" "+repr(bound))
        native_properties = {"SourceMode": "Particles", "RendererVisibility": 0, "DecalScreenSizeFade": 0.0,
            "PositionBinding": self.attribute_binding("Particles.UEFX_DecalPosition"),
            "DecalOrientationBinding": self.attribute_binding("Particles.UEFX_DecalOrientation"),
            "DecalSizeBinding": self.attribute_binding("Particles.UEFX_DecalSize"),
            "DecalColorBinding": self.attribute_binding("Particles.UEFX_DecalColor"),
            "DecalFadeBinding": self.attribute_binding("Particles.UEFX_DecalFade"),
            "DecalVisibleBinding": self.attribute_binding("Particles.UEFX_DecalVisible"),
            "DecalSortOrderBinding": self.attribute_binding("Particles.UEFX_DecalSortOrder"),
            "RendererVisibilityTagBinding": self.attribute_binding(None)}
        object_tools = "editor_toolset.toolsets.object.ObjectTools."
        self._author_tool(object_tools+"set_properties", instance=child_ref, values=json.dumps(native_properties))
        native_actual = json.loads(self._author_tool(object_tools+"get_properties", instance=child_ref,
                                               properties=list(native_properties))["returnValue"])
        self.verify_properties(native_properties, native_actual, source+".NativeDecal")
        self.projected_renderers.append({"location": location, "child": child_ref, "source": source,
                                         "native_properties": native_properties,
                                         "vector_attributes": contract["properties"]["ParticleVectorAttributes"]})

    def require_projected_support(self, specs):
        """新包变更前核真实已加载公共ABI；源码声明本身不代表Editor软件已包含接口。"""
        decals = any(spec["renderer"]["kind"] == "projected_decal" for spec in specs)
        props = any(spec["renderer"].get("native_prop_contract") is not None for spec in specs)
        if not decals and not props:
            return
        if self.native is None:
            raise ValueError("Native投影／Prop制作缺同Editor unreal宿主")
        klass = getattr(self.native, "GGYGOProjectedDecalRendererProperties", None)
        if klass is None:
            raise RuntimeError("实际Editor未加载Native投影／Prop公开桥")
        if props and not callable(getattr(klass, "read_native_mesh_motion_for_authoring", None)):
            raise RuntimeError("实际Editor缺Native Mesh current/previous布局只读接口")
        if decals:
            default = self.native.get_default_object(klass)
            for method in ("get_native_decal_for_authoring", "bind_source_user_material_for_authoring",
                           "read_compiled_payload_layout_for_authoring"):
                if not callable(getattr(default, method, None)):
                    raise RuntimeError("实际Editor缺Native Decal author ABI："+method)

    def verify_projected_bindings(self, specs):
        """当前NS编译已收束后读取同原Renderer布局；不证明活粒子值或可见绘制。"""
        object_tools = "editor_toolset.toolsets.object.ObjectTools."
        for item in self.projected_renderers:
            actual = json.loads(self.ns("GetRendererData", rendererRef=item["location"])["propertyValues"])
            keys = {key.lower(): key for key in actual}
            if actual[keys["nativedecal"]] != item["child"] or actual[keys["sourcereference"]] != item["source"]:
                raise RuntimeError("Native Decal编译期间原child／来源改变")
            child = self.native.load_object(None, item["child"]["refPath"])
            layout = child.get_outer().read_compiled_payload_layout_for_authoring()
            if not isinstance(layout, tuple) or len(layout) != 4:
                raise RuntimeError("Native Decal未返回实际四项payload结果："+item["source"]+" "+repr(layout))
            valid, invalid, geometry_valid, error = layout
            if ([str(name) for name in valid] != item["vector_attributes"]
                    or invalid or geometry_valid is not True or error):
                raise RuntimeError("Native Decal真实typed payload布局不完整："+repr(layout))
            expected = {name: {**value, "bBindingExistsOnSource": True, "bIsCachedParticleValue": True}
                        for name, value in item["native_properties"].items()
                        if name.endswith("Binding") and name != "RendererVisibilityTagBinding"}
            native = json.loads(self._author_tool(object_tools+"get_properties", instance=item["child"],
                                           properties=list(expected))["returnValue"])
            self.verify_properties(expected, native, item["source"])
        for spec in specs:
            if spec["renderer"].get("native_prop_contract") is None:
                continue
            renderers = [spec["renderer"]]+spec.get("additional_renderers", [])
            topology = self.ns("GetEmitterTopology", emitterRef=self.loc(spec["name"]))["renderers"]
            if len(topology) != len(renderers):
                raise RuntimeError("Prop两role及原灯Renderer数量不同")
            for metadata, renderer in zip(topology, renderers):
                if renderer.get("prop_role") is None:
                    continue
                if metadata["rendererClass"] != {"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"}:
                    raise RuntimeError("Prop没有使用原生标准Mesh Renderer")
                layout = self.native.GGYGOProjectedDecalRendererProperties.read_native_mesh_motion_for_authoring(
                    self.native.load_asset(self.sref["refPath"]), spec["name"], metadata["rendererIndex"])
                precise = renderer["motion_vector_setting"] == "Precise"
                if not isinstance(layout, tuple) or len(layout) != 6:
                    raise RuntimeError("Prop未返回实际六项motion结果："+spec["name"]+" "+repr(layout))
                needs_precise, current, previous, current_valid, previous_valid, error = layout
                if (needs_precise != precise
                        or [str(name) for name in current] != ["Particles.Position", "Particles.Scale", "Particles.MeshOrientation"]
                        or list(current_valid) != [True]*3 or error
                        or precise and ([str(name) for name in previous] != ["Particles.Previous.Position", "Particles.Previous.Scale", "Particles.Previous.MeshOrientation"]
                                        or list(previous_valid) != [True]*3)):
                    raise RuntimeError("Prop真实原生current/previous布局未通过："+repr(layout))

    def require_native_depth_velocity_support(self, specs):
        """制作前确认原生Sprite/编译布局入口；不把属性存在当作GPU深度已验。"""
        selected = [s for s in specs if s["renderer"].get("native_depth_velocity") is not None]
        if any(s["renderer"]["kind"] == "mesh" for s in selected):
            klass = getattr(self.native, "GGYGOProjectedDecalRendererProperties", None)
            if klass is None or not callable(getattr(klass, "read_native_mesh_motion_for_authoring", None)):
                raise RuntimeError("Mesh额外Depth/Velocity缺原生current/previous布局只读接口")
        if not any(s["renderer"]["kind"] == "sprite" for s in selected):
            return
        library = getattr(self.native, "GGYGONiagaraCompileLibrary", None) if self.native is not None else None
        methods = ("read_emitter_data_set_attributes", "read_sprite_motion_support", "read_sprite_motion_state")
        if library is None or any(not callable(getattr(library, method, None)) for method in methods):
            raise RuntimeError("Precise Primary缺真实编译DataSet／派生Previous只读入口，不先创建部分NS")
        support = self._author_tool(COMPILE+"ReadSpriteMotionSupport")["returnValue"]
        if (support.get("bSupported") is not True or support.get("error")
                or support.get("rendererClass") != "/Script/Niagara.NiagaraSpriteRendererProperties"):
            raise RuntimeError("Precise Primary实际Sprite current/Previous ABI缺失: "+repr(support))
        self.verify_sprite_motion_bindings(support, compiled=False)
        current = list(self.DEPTH_VELOCITY_BINDINGS)
        unused = list(self.DEPTH_VELOCITY_CONSTANT_BINDINGS)
        # Previous 是 Native 从 current 派生的 Transient 缓存，只经 typed 快照读取。
        required = current + unused + [
            "SourceMode", "MotionVectorSetting", "FacingMode", "Alignment", "PivotInUVSpace", "bIsEnabled"]
        data = json.loads(self._author_tool("editor_toolset.toolsets.object.ObjectTools.get_properties",
            instance={"refPath":"/Script/Niagara.Default__NiagaraSpriteRendererProperties"},
            properties=required)["returnValue"])
        keys = {key.lower():key for key in data}
        if any(key.lower() not in keys for key in required):
            raise RuntimeError("Precise Primary实际Sprite属性ABI缺失")
        defaults = {}
        for key in unused:
            binding = data[keys[key.lower()]]
            if not isinstance(binding, dict):
                raise RuntimeError("Precise Primary原生常量绑定ABI无效: "+key)
            identity = {name:value for name,value in binding.items() if name.lower() in (
                "rootname", "parammapvariable", "datasetname", "defaultvalueifnonexistent")}
            if not identity or not any(name.lower() == "parammapvariable" for name in identity):
                raise RuntimeError("Precise Primary原生常量缺真实变量身份: "+key)
            defaults[key] = copy.deepcopy(identity)
        self.depth_velocity_native_defaults = {"properties": defaults, "motion": support}

    def verify_sprite_motion_bindings(self, state, *, compiled):
        names = list(self.DEPTH_VELOCITY_BINDINGS) + list(self.DEPTH_VELOCITY_CONSTANT_BINDINGS)
        types = {key: kind for key, (_,kind) in self.DEPTH_VELOCITY_BINDINGS.items()}
        types.update(self.DEPTH_VELOCITY_CONSTANT_BINDINGS)
        current, previous = state.get("currentBindings"), state.get("previousBindings")
        if (not isinstance(current, list) or not isinstance(previous, list)
                or [row.get("propertyName") for row in current] != names
                or [row.get("propertyName") for row in previous] != ["Prev"+key for key in names]):
            raise RuntimeError("Precise Primary缺准确八组current／派生Previous快照: "+repr(state))
        for index, (key, now, before) in enumerate(zip(names, current, previous)):
            if compiled:
                defaults = self.depth_velocity_native_defaults["motion"]
                expected = defaults["currentBindings"][index]["attribute"]
            elif key in self.DEPTH_VELOCITY_BINDINGS:
                expected = "Particles."+self.DEPTH_VELOCITY_BINDINGS[key][0]
            else:
                expected = now.get("attribute")
            if not isinstance(expected, str) or not expected.startswith("Particles.") or len(expected) <= 10:
                raise RuntimeError("Precise Primary原生常量缺准确Particles身份: "+repr(now))
            for row, attribute in ((now, expected), (before, "Particles.Previous."+expected.split(".",1)[1])):
                if (row.get("attribute") != attribute or row.get("dataSetAttribute") != attribute.split(".",1)[1]
                        or row.get("typePath") != TYPES[types[key]]
                        or row.get("bIsCachedParticleValue") is not True
                        or type(row.get("bBindingExistsOnSource")) is not bool
                        or type(row.get("bLayoutValid")) is not bool):
                    raise RuntimeError("Precise Primary真实current／Previous身份或类型不符: "+repr(row))
            if compiled and key in self.DEPTH_VELOCITY_BINDINGS:
                # Prev 的 exists 可因引擎派生时未传 Emitter 而为 false；真实 VF 槽和 DataSet 才证明消费。
                if (now["bBindingExistsOnSource"] is not True
                        or now["bLayoutValid"] is not True or before["bLayoutValid"] is not True):
                    raise RuntimeError("Precise Primary缺真实current／Previous VF布局: "+repr((now,before)))
        return {row["propertyName"]: row for row in current+previous}

    def verify_native_depth_velocity_bindings(self, specs):
        selected = {s["name"]:s for s in specs if s["renderer"].get("native_depth_velocity") is not None}
        if set(selected) != {row["emitter"] for row in self.depth_velocity_renderers}:
            raise RuntimeError("额外Depth/Velocity Primary数量或发射器身份不符")
        for row in self.depth_velocity_renderers:
            emitter = self.actual_emitter_names.get(row["emitter"])
            if emitter is None:
                raise RuntimeError("额外Depth/Velocity缺本次实际Emitter身份")
            topology = self.ns("GetEmitterTopology", emitterRef=self.loc(emitter))["renderers"]
            index = row["renderer_index"]
            if selected[row["emitter"]]["renderer"]["kind"] == "mesh":
                if (type(index) is not int or index < 0 or index >= len(topology)
                        or topology[index]["rendererClass"] != {"refPath":"/Script/Niagara.NiagaraMeshRendererProperties"}):
                    raise RuntimeError("额外Depth/Velocity没有准确Native Mesh Renderer")
                actual = json.loads(self.ns("GetRendererData", rendererRef=row["renderer"])["propertyValues"])
                self.verify_properties(row["properties"], actual, emitter)
                layout = self.native.GGYGOProjectedDecalRendererProperties.read_native_mesh_motion_for_authoring(
                    self.native.load_asset(self.sref["refPath"]), emitter, index)
                if not isinstance(layout, tuple) or len(layout) != 6:
                    raise RuntimeError("Mesh额外Depth/Velocity未返回实际motion布局")
                precise, current, previous, current_valid, previous_valid, error = layout
                if (precise is not True or error
                        or [str(name) for name in current] != ["Particles.Position", "Particles.Scale", "Particles.MeshOrientation"]
                        or [str(name) for name in previous] != ["Particles.Previous.Position", "Particles.Previous.Scale", "Particles.Previous.MeshOrientation"]
                        or list(current_valid) != [True]*3 or list(previous_valid) != [True]*3):
                    raise RuntimeError("Mesh额外Depth/Velocity原生current/previous布局未通过: "+repr(layout))
                row["native_motion_state"] = {"precise": precise, "current": [str(name) for name in current],
                    "previous": [str(name) for name in previous], "current_valid": list(current_valid),
                    "previous_valid": list(previous_valid)}
                continue
            if (type(index) is not int or index < 0 or index >= len(topology)
                    or topology[index]["rendererClass"] != {"refPath":"/Script/Niagara.NiagaraSpriteRendererProperties"}):
                raise RuntimeError("额外Depth/Velocity没有准确Native Sprite Renderer")
            expected = copy.deepcopy(row["properties"])
            required = {}
            for key,(attribute,kind) in self.DEPTH_VELOCITY_BINDINGS.items():
                binding = self.attribute_binding("Particles."+attribute)
                binding.pop("CachedDisplayName")  # 原生重缓存可改显示标签，执行身份由真实变量及布局核实。
                expected[key] = {**binding, "bBindingExistsOnSource":True, "bIsCachedParticleValue":True}
                for field in (attribute,"Previous."+attribute):
                    required[field] = TYPES[kind]
            expected.update(copy.deepcopy(self.depth_velocity_native_defaults["properties"]))
            actual = json.loads(self.ns("GetRendererData", rendererRef=row["renderer"])["propertyValues"])
            self.verify_properties(expected, actual, emitter)
            layout = self._author_tool(COMPILE+"ReadEmitterDataSetAttributes", system=self.sref, emitterName=emitter)["returnValue"]
            attributes = layout.get("attributes", [])
            fields = {item["name"]:item["typePath"] for item in attributes}
            if (layout.get("bReady") is not True or layout.get("error") or layout.get("emitterName") != emitter
                    or layout.get("uniqueEmitterName") != emitter or not layout.get("emitterHandleId")
                    or type(layout.get("handleIndex")) is not int or layout["handleIndex"] < 0
                    or not layout.get("dataSetName") or len(fields) != len(attributes)
                    or any(fields.get(name) != kind for name,kind in required.items())):
                raise RuntimeError("Precise Primary真实编译current/Previous类型或身份不符: "+repr(layout))
            motion = self._author_tool(COMPILE+"ReadSpriteMotionState", system=self.sref,
                emitterName=emitter, rendererIndex=index)["returnValue"]
            if (motion.get("bReady") is not True or motion.get("error")
                    or motion.get("systemPath") != self.sref["refPath"] or motion.get("emitterName") != emitter
                    or motion.get("emitterHandleId") != layout["emitterHandleId"]
                    or type(motion.get("rendererIndex")) is not int or motion["rendererIndex"] != index
                    or not motion.get("rendererPath")
                    or motion.get("rendererClass") != "/Script/Niagara.NiagaraSpriteRendererProperties"
                    or motion.get("sourceMode") != "Particles" or motion.get("bNeedsPreciseMotionVectors") is not True):
                raise RuntimeError("Precise Primary实际renderer／编译快照身份不符: "+repr(motion))
            bindings = self.verify_sprite_motion_bindings(motion, compiled=True)
            unused = list(self.DEPTH_VELOCITY_CONSTANT_BINDINGS)
            row["native_constant_bindings"] = {key:copy.deepcopy(bindings[key])
                for key in unused + ["Prev"+key for key in unused]}
            row["native_motion_state"] = motion
            row["compiled_data_set"] = layout
            row["runtime_and_gpu_verified"] = False
            row["source_previous_wpo_and_same_draw_equivalence"] = False

    def verify_renderer_bindings(self, specs):
        self.verify_light_bindings(specs)
        self.verify_projected_bindings(specs)
        self.verify_generated_ribbon_bindings(specs)
        self.verify_particle_trail_source_layouts(specs)
        self.verify_native_depth_velocity_bindings(specs)

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
        # Retain the freshly constructed binding's native TypeDefHandle.
        # None explicitly disables a native stage replaced by the shader adapter.
        root = attribute.split(".", 1)[1] if attribute is not None else "None"
        return {"RootName": root, "ParamMapVariable": {"Name": attribute or "None"},
                # CachedDisplayName is FName, like the live binding names.
                "DataSetName": root, "CachedDisplayName": attribute or "None"}

    def build_system(self, path, specs):
        """既有同步入口；沿同一原生制作流程消费全部安全边界。"""
        steps = self.iter_build_system(path, specs)
        while True:
            try:
                next(steps)
            except StopIteration as completed:
                return completed.value

    @staticmethod
    def _native_math_vector_atom(expression, template, marker, path):
        """只解固定原语模板中的完整 float3 子树，并逐字符重组核对。"""
        prefix = template.split(marker,1)[0]
        if not expression.startswith(prefix):
            raise ValueError(path+" 原数学公式前缀不符")
        begin = len(prefix)
        if not expression.startswith("float3(",begin):
            raise ValueError(path+" 原数学输入不是完整 float3")
        depth = 0
        for end in range(begin+6,len(expression)):
            if expression[end] == "(":
                depth += 1
            elif expression[end] == ")":
                depth -= 1
                if depth == 0:
                    end += 1
                    break
        else:
            raise ValueError(path+" 原 float3 未完整闭合")
        atom = expression[begin:end]
        if template.replace(marker,atom) != expression:
            raise ValueError(path+" 完整公式不能由原数学模板精确重组")
        return atom

    @staticmethod
    def _native_math_recipe(function, expressions, number, rows, path):
        inputs, outputs = MATH_SIGNATURES[function]
        if len(expressions) != len(inputs):
            raise ValueError(path+" 数学原语缺正式输入")
        names = ["Transient.UEFX_Math%d_%s" % (number,name) for name,_ in outputs]
        if any(name in row[0] or name in row[2] for row in rows for name in names):
            raise ValueError(path+" 数学临时输出与原输入冲突")
        return {"functionName":function,
            "functionInputs":[{"name":name, "type":{"classStructOrEnum":{"refPath":TYPES[kind]}},
                               "hlslExpression":expression} for (name,kind),expression in zip(inputs,expressions)],
            "outputTargets":[{"name":name, "type":{"classStructOrEnum":{"refPath":TYPES[kind]}}}
                             for name,(_,kind) in zip(names,outputs)]}, names

    @staticmethod
    def _lower_native_math_spec(spec):
        """仅降低已知 AffineChain / Euler 原语；保留原赋值位置、随机流和制作前源身份。"""
        import zzz_fx_niagara as FN
        prefixes = ("Particles.UAffine", "Particles.UAffineSprite", "Transient.UEFX_GeneratedFrame",
                    "Emitter.UEFX_ComponentFrame", "Emitter.UAffine")
        affine_target = re.compile("("+"|".join(re.escape(prefix) for prefix in prefixes)+r")([0-9]+)$")
        marker = "__UEFX_ORIGINAL_MATH_VECTOR__"
        euler = FN.qeuler_h("Particles.URot")
        projected = {}
        for stage in ("emitter_spawn", "emitter_update", "spawn", "update"):
            rows = spec.get(stage, [])
            lowered, calls, number = list(rows), {}, 0
            path = spec["name"]+"."+stage
            index = 0
            while index < len(rows):
                match = affine_target.fullmatch(rows[index][0])
                if match is None:
                    index += 1
                    continue
                prefix, offset = match[1], int(match[2])
                group = [(prefix+str(offset+k), "Quat" if k == 0 else "Vector") for k in range(5)]
                if offset % 5 or [(row[0],row[1]) for row in rows[index:index+5]] != group:
                    raise ValueError(path+" AffineChain 缺原连续 Q/P/C0/C1/C2 步骤")
                if offset:
                    previous = [(prefix+str(offset-5+k), "Quat" if k == 0 else "Vector") for k in range(5)]
                    if index < 5 or [(row[0],row[1]) for row in rows[index-5:index]] != previous:
                        raise ValueError(path+" AffineChain 缺原先序父步骤")
                    parent_p = prefix+str(offset-4)
                    parent_c = [prefix+str(offset-k) for k in (3,2,1)]
                else:
                    parent_p, parent_c = "float3(0,0,0)", ["float3(1,0,0)", "float3(0,1,0)", "float3(0,0,1)"]
                q = rows[index][0]
                p_template = "("+parent_p+"+"+FN.AffineChain.vector(parent_c,marker)+")"
                local_p = NiagaraBuilder._native_math_vector_atom(rows[index+1][2],p_template,marker,path)
                scales = []
                for axis in range(3):
                    template = FN.AffineChain.vector(parent_c,FN.qrot_h(q,marker))
                    atom = NiagaraBuilder._native_math_vector_atom(rows[index+2+axis][2],template,marker,path)
                    try:
                        components = tuple(float(value) for value in atom[7:-1].split(","))
                    except ValueError as error:
                        raise ValueError(path+" AffineChain 缩放轴不是原常量") from error
                    if len(components) != 3 or not all(math.isfinite(value) for value in components) \
                            or FN.f3(tuple(components[axis] if k == axis else 0.0 for k in range(3))) != atom:
                        raise ValueError(path+" AffineChain 缩放轴与原构造不同")
                    scales.append(components[axis])
                original = [rows[index+k][2] for k in range(1,5)]
                reconstructed = ["("+parent_p+"+"+FN.AffineChain.vector(parent_c,local_p)+")"] + [
                    FN.AffineChain.vector(parent_c,FN.qrot_h(q,FN.f3(tuple(scales[k] if k == axis else 0.0
                        for k in range(3))))) for axis in range(3)]
                if reconstructed != original:
                    raise ValueError(path+" AffineChain 完整反向重组与原公式不同")
                call, outputs = NiagaraBuilder._native_math_recipe("ComposeAffineStep",
                    (parent_p,*parent_c,local_p,q,FN.f3(scales)),number,rows,path)
                calls.setdefault(index+1, []).append(call)
                number += 1
                for k,output in enumerate(outputs,1):
                    lowered[index+k] = (rows[index+k][0],rows[index+k][1],output)
                index += 5
            for index,(name,kind,expression) in enumerate(lowered):
                if euler not in expression:
                    continue
                call, outputs = NiagaraBuilder._native_math_recipe("EulerZXY",("Particles.URot",),number,rows,path)
                final = expression.replace(euler,outputs[0])
                if final.replace(outputs[0],euler) != expression:
                    raise ValueError(path+" Euler 子式反向展开与原公式不同")
                calls.setdefault(index, []).append(call)
                number += 1
                lowered[index] = (name,kind,final)
            if calls:
                if spec.get("particle_trail_child"):
                    raise ValueError(path+" 逐粒子子拖尾出现未支持的数学制作位置，未开始创建资产")
                spec[stage], projected[stage] = lowered, calls
        if projected:
            spec["_native_math_calls"] = projected

    @staticmethod
    def _lower_emitter_chain_temps(spec):
        """按距离发射的变换链仅在当前 Emitter 脚本求值，不能写入粒子属性。"""
        token = re.compile(r"(?<![A-Za-z0-9_.])(?:Particles\.UChain|Transient\.UEFX_EmitterChain)[0-9]+[PQ](?![A-Za-z0-9_])")
        for stage in ("emitter_spawn", "emitter_update"):
            rows = spec.get(stage, [])
            aliases = {}
            for name, _, _ in rows:
                match = re.fullmatch(r"Particles\.UChain([0-9]+[PQ])", name)
                if match:
                    aliases[name] = "Transient.UEFX_EmitterChain" + match[1]
            if not aliases:
                continue
            existing = {match[0] for name, _, expression in rows for text in (name, expression)
                        for match in token.finditer(text)}
            if existing & set(aliases.values()):
                raise ValueError(spec["name"]+"."+stage+" 变换链临时名与原输入冲突")
            # 只替换已声明临时量的完整标识符；保留后续 .xyz 等取分量和原求值顺序。
            spec[stage] = [(aliases.get(name, name), kind,
                            token.sub(lambda match: aliases.get(match[0], match[0]), expression))
                           for name, kind, expression in rows]

    @staticmethod
    def lower_native_emitter_specs(specs):
        """转换制作副本的 Native 命名、Emitter 临时量及纯数学调用；源计划仍保留原身份。"""
        names = [spec["name"] for spec in specs]
        if (len({name.casefold() for name in names}) != len(names)
                or any(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",name) is None for name in names)):
            raise ValueError("原计划Emitter名不唯一或不是明确合法标识符")
        # Niagara去重会忽略FName的数字索引；固定文字结尾让完整原名参与比较。
        requested = {name:name+"_UEFX" for name in names}
        authored = copy.deepcopy(specs)
        for spec in authored:
            spec["name"] = requested[spec["name"]]
            references = [spec.get("particle_trail_child")]
            if spec.get("runtime_failure",{}).get("kind") == "SourceParticleTrail":
                references.append(spec["runtime_failure"]["policy"])
            for reference in references:
                if reference is not None:
                    parent = reference["parent_emitter"]
                    if parent not in requested:
                        raise ValueError("逐粒子拖尾父引用不在同一原计划: "+parent)
                    reference["parent_emitter"] = requested[parent]
            NiagaraBuilder._lower_emitter_chain_temps(spec)
            NiagaraBuilder._lower_native_math_spec(spec)
        return authored,requested

    def iter_build_system(self, path, specs):
        """System 与 transient DI 由当前 Builder 保活；只在原生调用完整返栈后让出原帧。"""
        folder, name = path.rsplit("/", 1)
        if not specs:
            raise ValueError("Cannot build an empty FX system: " + path)
        if len(specs) > self.MAX_SYSTEM_EMITTERS:
            raise ValueError("System超过独立编译单元界限，禁止创建或累积编译父图: "+path)
        if self.m.tool(COMPILE+"AuthoringReadSupport")["returnValue"] is not True:
            raise ValueError("实际加载软件缺本批Niagara作者桥，未开始创建资产")
        library = getattr(self.native, "GGYGONiagaraCompileLibrary", None)
        if any(not callable(getattr(library, method, None)) for method in (
                "compile_authoring_batch", "get_authoring_compile_task_limit", "try_set_authoring_compile_task_limit",
                "configure_authoring_compilation", "read_authoring_compilation_settings")):
            raise ValueError("实际加载软件缺有限制作批编译／任务启动控制／参数表示入口，未开始创建资产")
        run_data_batch = getattr(self.m, "run_niagara_authoring_batch", None)
        if not callable(run_data_batch):
            raise ValueError("当前生产宿主缺受控同步 Niagara 制作窗口，未开始创建资产")
        specs, requested_names = self.lower_native_emitter_specs(specs)
        for spec in specs:
            self.validate_spec(spec)
        self.require_field_renderer_classes(self.m, specs)
        self.require_runtime_failure_support(self.m, specs)
        self.require_component_mesh_support(self.m, specs)
        self.require_projected_support(specs)
        self.require_generated_ribbon_support(specs)
        self.require_particle_trail_support(specs)
        self.require_native_depth_velocity_support(specs)
        self.require_native_math_support(specs)
        self.generated_ribbon_renderers = []
        self.depth_velocity_renderers = []
        self.actual_emitter_names = {}
        self.assignment_di_templates = []
        self.assignment_di_bindings = []
        self.particle_trail_layouts = []
        self._stack_work = []
        # 原 Factory 会等待复制源；必须在任务上限仍为1时先收束真实模板，不能在0态等它启动。
        template_system = self.native_sync("niagara_authoring_template_load",
            lambda: self.native.load_object(None, DEFAULT_SYSTEM))
        if not isinstance(template_system, self.native.NiagaraSystem) or template_system.get_path_name() != DEFAULT_SYSTEM:
            raise RuntimeError("未加载准确的只读 Niagara System 模板，未创建资产")
        template_state = self._author_tool(COMPILE+"CompletePendingCompilation",
            system={"refPath":DEFAULT_SYSTEM})["returnValue"]
        if (template_state.get("systemPath") != DEFAULT_SYSTEM or template_state.get("error")
                or any(template_state.get(key) is not False for key in (
                    "bCompilationPending", "bActiveCompilations", "bNeedsCompileRequest"))):
            raise RuntimeError("复制源模板编译尚未收束，未进入暂停启动窗口: "+repr(template_state))
        stack_result = None
        wpo_radius = None
        for begin in range(0, len(specs), self.AUTHORING_EMITTER_BATCH_SIZE):
            end = min(begin+self.AUTHORING_EMITTER_BATCH_SIZE, len(specs))
            def author_batch_data():
                nonlocal wpo_radius
                original_limit = self._author_tool(COMPILE+"GetAuthoringCompileTaskLimit")["returnValue"]
                if original_limit != 1:
                    raise RuntimeError("有限制作批需要原编译任务上限1，未修改启动控制: "+repr(original_limit))
                operation_error = None
                try:
                    if self._author_tool(COMPILE+"TrySetAuthoringCompileTaskLimit",
                            expectedLimit=original_limit, newLimit=0)["returnValue"] is not True:
                        raise RuntimeError("未能暂停本批编译任务启动，停止制作")
                    # 只在 Root 专属 Editor 的完整同步制作段暂停启动；保留原 dirty/入队通知。
                    # 首批连同创建/WPO/模板移除一起覆盖，窗口内不返回 Editor 帧。
                    if begin == 0:
                        self.session.begin_create(path)
                        self.ns("CreateNiagaraSystem", assetName=name, assetPath=folder, templateSystem={"refPath": DEFAULT_SYSTEM})
                        self.session.created_asset(path)
                        self.sref = {"refPath": "%s.%s" % (path, name)}
                        self._hold_authored_system(path)
                        # 新 NS 在任何 Emitter/Stack 制作前确定持久 RI 表示；Edit/Cook 使用同一原生配置。
                        self._verify_authoring_compilation_settings(self._author_tool(
                            COMPILE+"ConfigureAuthoringCompilation", system=self.sref,
                            bUseRapidIterationParameters=True)["returnValue"])
                        wpo_radius = self.configure_wpo_bounds(specs)
                        for e in self.ns("GetSystemSummary", system=self.sref)["emitters"]:
                            self.ns("RemoveEmitter", emitterToRemove=self.loc(e["emitterName"]))
                        if any(spec.get("source_mode") == "Emitter" for spec in specs):
                            self.ns("SetSystemData", system=self.sref, systemData={"propertyValues": json.dumps({"bFixedBounds": False})})
                    self._stack_work = []
                    for s in specs[begin:end]:
                        self.build_emitter(s)
                    work = self._stack_work
                    self._stack_work = None
                    applied = self._apply_collected_stack_work(work)
                    del work
                    # 实际 DI 克隆已归原 NS 图；本批模板和完整 Work 不跨批保留。
                    self.assignment_di_templates.clear()
                    return applied
                except BaseException as error:
                    operation_error = error
                    raise
                finally:
                    # 清理必须在资源门已经中止时仍能执行；只直接调用实际 Native 恢复原值，不能借此续作。
                    # 也覆盖 Setter 已完成、但其 after_tool 预算检查抛错的边界。
                    try:
                        current_limit = library.get_authoring_compile_task_limit()
                        if current_limit == 0:
                            if library.try_set_authoring_compile_task_limit(0, original_limit) is not True:
                                raise RuntimeError("有限制作批未能恢复原编译任务上限")
                        elif current_limit != original_limit:
                            raise RuntimeError("有限制作批编译任务上限被其它来源改变，不覆盖: "+repr(current_limit))
                    except BaseException as cleanup_error:
                        if operation_error is not None:
                            raise RuntimeError("Niagara同步制作失败（%s）: %s；编译限额恢复失败（%s）: %s" % (
                                type(operation_error).__name__, operation_error,
                                type(cleanup_error).__name__, cleanup_error)) from operation_error
                        raise
            applied = run_data_batch(author_batch_data)
            if begin == 0:
                del template_system
            compiled = self.compile_authoring_batch(path, [s["name"] for s in specs[:end]])
            if stack_result is None:
                stack_result = dict(applied, batches=[])
            else:
                stack_result["workItemCount"] += applied["workItemCount"]
            stack_result["batches"].append({"firstEmitterIndex":begin, "emitterCount":end-begin,
                "workItemCount":applied["workItemCount"], "compile":compiled})
            yield "niagara_authoring_batch_compiled:%s:%d:%d" % (path, begin, end)
        yield "niagara_stack_authored:"+path
        def verify_source_bindings():
            summary = self.ns("GetSystemSummary",system=self.sref)
            actual = [row["emitterName"] for row in summary["emitters"]]
            expected = set(requested_names.values())
            if (len(actual) != len(expected) or set(actual) != expected
                    or self.actual_emitter_names != {name:name for name in expected}):
                raise RuntimeError("完整NS实际Emitter身份不符: missing=%r unexpected=%r count=%d/%d" % (
                    sorted(expected-set(actual)),sorted(set(actual)-expected),len(actual),len(expected)))
            self.verify_renderer_bindings(specs)
            self.verify_wpo_bounds(wpo_radius)
            self._verify_authoring_compilation_settings(self._author_tool(
                COMPILE+"ReadAuthoringCompilationSettings", system=self.sref)["returnValue"])
        result = self.finish_compile(path, before_save=verify_source_bindings, force_rebuild=False,
                                     expected_emitters=[s["name"] for s in specs])
        result["stack_authoring"] = stack_result
        result["authored_emitter_names"] = {source:self.actual_emitter_names[requested]
            for source,requested in requested_names.items()}
        if self.generated_ribbon_renderers:
            result["generated_ribbon_authoring"] = {"renderers":self.generated_ribbon_renderers}
        if self.depth_velocity_renderers:
            result["native_depth_velocity_authoring"] = {"renderers":self.depth_velocity_renderers}
        particle_bindings = [binding for binding in self.assignment_di_bindings
                             if binding["dataInterfaceClass"] != MATH_CLASS]
        math_bindings = [binding for binding in self.assignment_di_bindings
                        if binding["dataInterfaceClass"] == MATH_CLASS]
        if particle_bindings or self.particle_trail_layouts:
            result["particle_trail_authoring"] = {"assignment_di_bindings":particle_bindings,
                "source_data_sets":self.particle_trail_layouts}
        if math_bindings:
            result["native_math_authoring"] = {"assignment_di_bindings":math_bindings}
        return result

    def _verify_authoring_compilation_settings(self, state):
        """核对原资产的即时编译表示；保存前只读复核，不回写掩盖差异。"""
        if (state.get("bSucceeded") is not True or state.get("error")
                or state.get("systemPath") != self.sref["refPath"]
                or state.get("bCompileForEdit") is not False
                or state.get("bUsesRapidIterationParameters") is not True):
            raise RuntimeError("Niagara原资产的持久RI编译表示不符，停止制作或保存: "+repr(state))

    def compile_authoring_batch(self, path, names, timeout=50):
        """同一累计 NS 的非 force 编译；原任务退役并核实际脚本后才允许后继制作。"""
        self.session.require_created(path)
        self.session.check_editor()
        native = self._author_tool(COMPILE+"CompileAuthoringBatch", system=self.sref)["returnValue"]
        deadline = time.monotonic()+timeout
        while True:
            self.verify_authoring_compilation(path, native, names)
            if native.get("bNativeReady") is True:
                break
            # 保留原生 PSO 等正常就绪暂态；不把未就绪当作成功或继续堆积下一批。
            if time.monotonic() >= deadline:
                raise RuntimeError("有限制作批 Native Ready 尚未完成，禁止继续制作和保存: "+repr(native))
            time.sleep(min(2, max(0, deadline-time.monotonic())))
            native = self._author_tool(COMPILE+"ReadSystemState", system=self.sref)["returnValue"]
        state = self.read_compile_state(path)
        self.verify_compile_state(path, state)
        # 原 Context/事务已退栈，编译与真实脚本均收束后，经原宿主同步边界释放临时对象。
        self.native_sync("niagara_authoring_batch_retired", self.native.collect_garbage)
        return {"cumulativeEmitterCount":len(names), "aggregateStatus":state["aggregateStatus"],
            **{key:native[key] for key in ("bForceCompileRequested", "bCompilationPending", "bActiveCompilations",
                "bNeedsCompileRequest", "bSystemValid", "bNativeReady", "bVMAttributesEqual", "compiledEmitterCount")}}

    @staticmethod
    def verify_authoring_compilation(path, native, names):
        """批间及最终的同图编译共用完整身份与任务退役门；Ready 的合法等待留在调用方。"""
        NiagaraBuilder.verify_native_compilation(path, native)
        if (native.get("bForceCompileRequested") is not False
                or any(native.get(key) is not False for key in (
                    "bCompilationPending", "bActiveCompilations", "bNeedsCompileRequest"))
                or native.get("emitterNames") != names or native.get("emitterCount") != len(names)
                or native.get("emitterEnabled") != [True]*len(names)
                or native.get("compiledEmitterCount") != len(names)):
            raise RuntimeError("制作编译未归还或完整 Emitter 身份不同，禁止继续制作和保存: "+repr(native))

    def verify_light_bindings(self, specs):
        """原生编译完成后核实际 renderer 类型及真实 typed 绑定，缺省值不算消费成功。"""
        bindings = ("PositionBinding", "ColorBinding", "RadiusBinding", "LightRenderingEnabledBinding", "VolumetricScatteringBinding")
        for spec in specs:
            if spec["renderer"]["kind"] == "component_mesh":
                topology = self.ns("GetEmitterTopology", emitterRef=self.loc(spec["name"]))["renderers"]
                draws = spec["renderer"]["draws"]
                if len(topology) != len(draws):
                    raise RuntimeError("MeshRenderer原生绘制数量与源重复槽不符")
                for metadata, draw in zip(topology, draws):
                    if metadata["rendererClass"] != {"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"}:
                        raise RuntimeError("MeshRenderer实际类型不同")
                    properties = self.component_mesh_properties(spec["name"], draw)
                    properties["OverrideMaterials"][0]["UserParamBinding"] = {"Parameter": {"Name": draw["user_material"]}}
                    for binding in self.COMPONENT_MESH_BINDINGS:
                        properties[binding].update(bBindingExistsOnSource=True, bIsCachedParticleValue=False)
                    actual = json.loads(self.ns("GetRendererData", rendererRef=self.loc(
                        spec["name"], renderer=metadata["rendererIndex"]))["propertyValues"])
                    self.verify_properties(properties, actual, spec["name"])
                continue
            expected = [spec["renderer"]]+spec.get("additional_renderers", [])
            if not any(renderer["kind"] == "light" for renderer in expected):
                continue
            topology = self.ns("GetEmitterTopology", emitterRef=self.loc(spec["name"]))["renderers"]
            if len(topology) != len(expected):
                raise RuntimeError("同一源发射器的原生 renderer 数量不同: " + spec["name"])
            for metadata, renderer in zip(topology, expected):
                if renderer["kind"] != "light":
                    continue
                if metadata["rendererClass"] != {"refPath": "/Script/Niagara.NiagaraLightRendererProperties"}:
                    raise RuntimeError("Particle/Component Light 的实际 renderer 类型不同")
                data = json.loads(self.ns("GetRendererData", rendererRef=self.loc(
                    spec["name"], renderer=metadata["rendererIndex"]))["propertyValues"])
                emitter = renderer.get("source_mode") == "Emitter"
                self.verify_properties({"SourceMode": "Emitter" if emitter else "Particles",
                    **{binding: {"bBindingExistsOnSource": True, "bIsCachedParticleValue": not emitter} for binding in bindings}}, data, spec["name"])
        if any(spec.get("source_mode") == "Emitter" for spec in specs):
            self.verify_properties({"bFixedBounds": False}, json.loads(
                self.ns("GetSystemData", system=self.sref)["propertyValues"]), self.sref["refPath"])

    def finish_compile(self, path, timeout=50, before_save=None, *, force_rebuild=True, expected_emitters=None):
        """默认完整 Force；分批制作可显式保留缓存，仍检查完整脚本、身份、布局和 Native Ready。"""
        self.session.require_created(path)
        self.session.check_editor()
        if not force_rebuild and not expected_emitters:
            raise ValueError("最终同图编译缺准确完整 Emitter 清单，未请求编译或保存")
        method = "ForceCompile" if force_rebuild else "CompileAuthoringBatch"
        native = self._author_tool(COMPILE+method, system=self.sref)["returnValue"]
        if force_rebuild and not native["bForceCompileRequested"]:
            raise RuntimeError("Niagara full compile was not requested; package was not saved: %s %s" %
                               (path, native["error"]))
        if not force_rebuild:
            self.verify_authoring_compilation(path, native, expected_emitters)
        # 同步原生编译返回后，仍给 PSO 等真实 Ready 暂态完整的等待区间。
        deadline = time.monotonic()+timeout
        while True:
            state = self.read_compile_state(path)
            native = self._author_tool(COMPILE + "ReadSystemState", system=self.sref)["returnValue"]
            if force_rebuild:
                self.verify_native_compilation(path, native)
            else:
                self.verify_authoring_compilation(path, native, expected_emitters)
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
    def compile_state_from_diagnostics(path, diagnostics):
        """完整读取的成功与编译通过分开；只消费原对象、无 Context 错误的原生返回。"""
        expected_object = path + "." + path.rsplit("/", 1)[1]
        if (diagnostics["bSucceeded"] is not True or diagnostics["systemPath"] != expected_object
                or diagnostics["error"]):
            raise RuntimeError("Niagara 完整诊断读取失败: %s %s" % (
                path, json.dumps(diagnostics, ensure_ascii=False, sort_keys=True)))
        return diagnostics["compileState"]

    def read_compile_state(self, path):
        """通过默认 Context 的 Native 薄桥读取；不创建编辑 VM 或请求编译。"""
        diagnostics = self._author_tool(COMPILE + "ReadSystemCompileDiagnostics", system=self.sref)["returnValue"]
        return self.compile_state_from_diagnostics(path, diagnostics)

    @staticmethod
    def verify_compile_state(path, state):
        """编译聚合状态不能覆盖单脚本错误或未收束结果。"""
        if state["bIsCompiling"] or state["bIsStale"]:
            reason = "Niagara compile is incomplete; package was not saved: " + path
        else:
            errors = [(x["emitterName"], x["scriptName"], ev["message"]) for x in state["scripts"]
                      for ev in x["compileEvents"] if ev["severity"] == "Error"]
            if errors:
                reason = "Niagara 编译失败：\n" + "\n".join("%s %s\n%s" % e for e in errors[:4])
            elif state["bHasErrors"] or state["aggregateStatus"] not in ("UpToDate", "UpToDateWithWarnings"):
                reason = "Niagara compile did not succeed: %s %s" % (path, state["aggregateStatus"])
            else:
                return
        # 保留两就绪旗、聚合值和全部单脚本状态／事件，不能只留路径或截取前几条错误。
        raise RuntimeError(reason + "; state=" + json.dumps(state, ensure_ascii=False, sort_keys=True))


class EmitterMeshBuilder(NiagaraBuilder):
    """@brief 原生 Emitter Mesh 资源；所有绘制归属于同一个 NS。

    不产生粒子，不从源 Clip 时长推导生命周期。资源实例由创建它的
    预览所有者显式销毁；原动作的生成、挂点、Follow、Fade 和 Stop 未准入。
    """

    BINDINGS = {"PositionBinding": ("GhostPosition", "Position"),
                "MeshOrientationBinding": ("GhostOrientation", "Quat"),
                "ScaleBinding": ("GhostScale", "Vector"),
                "VelocityBinding": ("GhostVelocity", "Vector")}
    AGE_TRANSPORT = {"DP0.x": "System.Age"}
    AGE_ENTRY = ["Emitter.GhostMaterial0", "Vector4", "float4(System.Age,0.0,0.0,0.0)"]

    @classmethod
    def renderer_bindings(cls, renderer):
        bindings = dict(cls.BINDINGS)
        if renderer.get("material_age_transport") is not None:
            if renderer["material_age_transport"] != cls.AGE_TRANSPORT:
                raise ValueError("Emitter Mesh材质年龄必须来自原System.Age的DP0.x")
            bindings["DynamicMaterialBinding"] = ("GhostMaterial0", "Vector4")
        return bindings

    def __init__(self, session=None, *, mcp=None):
        """构建使用自有 session；只读检查使用显式 mcp，二者不混用。"""
        if (session is None) == (mcp is None):
            raise ValueError("Emitter Mesh 需要唯一的构建 session 或只读工具接口")
        if session is not None:
            # 原NativeToolsets公开native即本Session的宿主；不另找Editor或借远端实例。
            super().__init__(session, unreal=session.m.native)
        else:
            self.session = None
            self.m = mcp

    @classmethod
    def validate_specs(cls, specs):
        if not specs:
            raise ValueError("Emitter Mesh 资源缺少源组件")
        names = set()
        for spec in specs:
            expected_parameters = {"Emitter." + n: t for n, t in cls.BINDINGS.values()}
            age_transport = spec.get("material_age_transport")
            if age_transport is not None:
                if age_transport != cls.AGE_TRANSPORT:
                    raise ValueError("Emitter Mesh缺准确DP0.x年龄合同")
                expected_parameters[cls.AGE_ENTRY[0]] = cls.AGE_ENTRY[1]
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
            expected_update = [cls.AGE_ENTRY] if age_transport is not None else []
            if spec.get("emitter_update", []) != expected_update or any(spec.get(k) for k in ("bursts", "rate", "spawn", "update")):
                raise ValueError("静态残影资源不生成粒子或猜动态输入")
            if age_transport is not None and [e for e in entries if e[0] == cls.AGE_ENTRY[0]] != [cls.AGE_ENTRY]:
                raise ValueError("Emitter Mesh首帧年龄缺原System.Age初始化")
            renderers = spec.get("renderers", [])
            if not renderers or len(renderers) % 2:
                raise ValueError("每个源材质槽需要独立 Outline/Surface renderer")
            for slot in range(len(renderers) // 2):
                pair = renderers[slot * 2:slot * 2 + 2]
                for role, renderer in zip(("outline", "surface"), pair):
                    if renderer.get("material_age_transport") != age_transport:
                        raise ValueError("Emitter Mesh材质与Emitter年龄合同不同")
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
    def renderer_properties(name, renderer, *, bindings=None):
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
        for property_name, (root, _) in (EmitterMeshBuilder.renderer_bindings(renderer) if bindings is None else bindings).items():
            properties[property_name] = {"RootName": root, "DataSetName": root,
                "BindingSourceMode": "ExplicitEmitter", "ParamMapVariable": {"Name": name + "." + root},
                "CachedDisplayName": "Emitter." + root}
        if renderer.get("material_age_transport") is not None:
            for suffix in ("1", "2", "3"):
                properties["DynamicMaterial" + suffix + "Binding"] = NiagaraBuilder.attribute_binding(None)
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
                for binding in self.renderer_bindings(renderer):
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
        updates = spec.get("emitter_update", [])
        if update["scriptName"] != "EmitterUpdateScript" or len(update["modules"]) != 1 + len(updates):
            raise RuntimeError("Emitter Mesh生命周期/实际材质年龄模块数量不符: " + name)
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
        for module, (parameter, kind, expression) in zip(update["modules"][1:], updates):
            self.verify_properties({"enabled": True, "bIsSetParametersModule": True,
                "inputs": [{"name": parameter, "type": {"classStructOrEnum": {"refPath": TYPES[kind]}},
                            "bIsDynamic": False}]}, module, name + ".EmitterUpdateScript")
            values = self.ns("GetModuleInputValues", moduleRef=self.loc(name, "EmitterUpdateScript", module["moduleName"]))
            self.verify_properties({"moduleName": module["moduleName"],
                "inputs": [{"name": parameter, "value": self.hlsl(expression)}]}, values, name + "." + parameter)
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
        state = self.read_compile_state(path)
        native = self._author_tool(COMPILE + "ReadSystemState", system=self.sref)["returnValue"]
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
        self._hold_authored_system(path)
        wpo_radius = self.configure_wpo_bounds(specs)
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
            self.set_params(name, "EmitterUpdateScript", spec.get("emitter_update", []))
            for renderer in spec["renderers"]:
                result = self.ns("AddRenderer", newRendererLocation=self.loc(name),
                    rendererClass={"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"})
                self.ns("SetRendererData", renderer=self.loc(name, renderer=result["rendererIndex"]),
                    rendererData={"propertyValues": json.dumps(self.renderer_properties(name, renderer))})
        def verify_resource():
            self.verify_wpo_bounds(wpo_radius)
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
        state = NiagaraBuilder.compile_state_from_diagnostics(NORMAL01_SYSTEM,
            call(COMPILE + "ReadSystemCompileDiagnostics", system=ref))
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
            state = NiagaraBuilder.compile_state_from_diagnostics(NORMAL01_SYSTEM,
                json.loads(result.get_editor_property("value"))["returnValue"])
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
        toolset, name = (COMPILE + "ReadSystemCompileDiagnostics").rsplit(".", 1)
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
            tool_name = COMPILE + "ReadSystemCompileDiagnostics"
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
                compile_state = NiagaraBuilder.compile_state_from_diagnostics(path, completed_value(result, tool_name))
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
        compile_state = NiagaraBuilder.compile_state_from_diagnostics(path,
            call(COMPILE + "ReadSystemCompileDiagnostics", system=ref))
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
