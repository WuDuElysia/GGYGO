"""按 zzz_fx_niagara 的发射器方案，在用户打开的 UE 编辑器里（经 MCP 的 NiagaraToolset）建 Niagara 系统。

    build_system(path, specs):
        已存在则删除重建（系统内容完全由方案生成，没有手工编辑需要保留）
        CreateNiagaraSystem(DefaultSystem) → 删掉模板自带的 Fountain 发射器
        for spec: AddEmitter(CompletelyEmpty) → 发射器属性 → Emitter State / Spawn Burst / Spawn Rate
                  → 粒子生成 Set Parameters → Particle State + 粒子更新 Set Parameters → Mesh 渲染器
        OpenEditorForAsset 触发首次完整编译，轮询编译状态，有错误就抛出（附 HLSL 报错原文）
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ue_mcp import Mcp  # noqa: E402

NS = "NiagaraToolsets.NiagaraToolset_System."
AS = "editor_toolset.toolsets.asset.AssetTools."
TYPES = {"Float": "/Script/Niagara.NiagaraFloat", "Vector": "/Script/CoreUObject.Vector3f",
         "Vector4": "/Script/CoreUObject.Vector4f", "Quat": "/Script/CoreUObject.Quat4f",
         "LinearColor": "/Script/CoreUObject.LinearColor", "Position": "/Script/Niagara.NiagaraPosition"}
HLSL = "/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression"
EMPTY_EMITTER = "/Niagara/DefaultAssets/Templates/CascadeConversion/CompletelyEmpty.CompletelyEmpty"
DEFAULT_SYSTEM = "/Niagara/DefaultAssets/DefaultSystem.DefaultSystem"
ENUM = "/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum"


class NiagaraBuilder:
    def __init__(self, mcp=None):
        self.m = mcp or Mcp()

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
        if not entries:
            return
        params = [{"variable": {"name": n, "type": {"classStructOrEnum": {"refPath": TYPES[t]}}}} for n, t, _ in entries]
        mod = self.ns("AddSetParametersModule", moduleLocationRef=self.loc(emitter, script), parameters=params)["moduleName"]
        for n, _, e in entries:
            self.set_input(emitter, script, mod, n, self.hlsl(e))

    def build_emitter(self, s):
        name = s["name"]
        self.ns("AddEmitter", system=self.sref, templateEmitter={"refPath": EMPTY_EMITTER}, emitterName=name)
        self.ns("SetEmitterData", emitter=self.loc(name), emitterData={"propertyValues": json.dumps(
            {"bLocalSpace": s["local_space"], "SimTarget": "CPUSim", "InterpolatedSpawnMode": "RunUpdateScript"})})
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
        for t, count in s["bursts"]:
            b = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/SpawnBurst_Instantaneous.SpawnBurst_Instantaneous")
            self.set_input(name, "EmitterUpdateScript", b, "Spawn Count", self.num("Int32", count))
            self.set_input(name, "EmitterUpdateScript", b, "Spawn Time", self.num("Float", t))
        if s["rate"] > 0:
            r = self.add_module(name, "EmitterUpdateScript", "/Niagara/Modules/Emitter/SpawnRate.SpawnRate")
            self.set_input(name, "EmitterUpdateScript", r, "SpawnRate", self.num("Float", s["rate"]))
        self.set_params(name, "ParticleSpawnScript", s["spawn"])
        self.add_module(name, "ParticleUpdateScript", "/Niagara/Modules/Update/Lifetime/ParticleState.ParticleState")
        self.set_params(name, "ParticleUpdateScript", s["update"])
        rd = s["renderer"]
        r = self.ns("AddRenderer", newRendererLocation=self.loc(name),
                    rendererClass={"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"})
        mesh = rd["mesh"] + "." + rd["mesh"].rsplit("/", 1)[1]
        mat = rd["material"] + "." + rd["material"].rsplit("/", 1)[1]
        self.ns("SetRendererData", renderer=self.loc(name, renderer=r["rendererIndex"]), rendererData={"propertyValues": json.dumps(
            {"Meshes": [{"Mesh": mesh}], "bOverrideMaterials": True, "OverrideMaterials": [{"ExplicitMat": mat}],
             "SortOrderHint": rd["sort"]})})
        back = self.ns("GetRendererData", rendererRef=self.loc(name, renderer=r["rendererIndex"]))
        text = json.dumps(back)
        if rd["mesh"].rsplit("/", 1)[1] not in text or rd["material"].rsplit("/", 1)[1] not in text:
            raise RuntimeError("%s 渲染器的网格/材质没有设上：%s" % (name, text[:600]))

    def build_system(self, path, specs):
        folder, name = path.rsplit("/", 1)
        if self.m.tool(AS + "exists", path=path)["returnValue"]:
            self.m.tool(AS + "delete", path=path)
        self.ns("CreateNiagaraSystem", assetName=name, assetPath=folder, templateSystem={"refPath": DEFAULT_SYSTEM})
        self.sref = {"refPath": "%s.%s" % (path, name)}
        for e in self.ns("GetSystemSummary", system=self.sref)["emitters"]:
            self.ns("RemoveEmitter", emitterToRemove=self.loc(e["emitterName"]))
        for s in specs:
            self.build_emitter(s)
        self.m.tool(AS + "save_assets", asset_paths=[path])
        self.m.tool("EditorToolset.EditorAppToolset.OpenEditorForAsset", assetPath=path)
        state = None
        for _ in range(120):
            time.sleep(2)
            state = self.ns("GetSystemCompileState", system=self.sref)
            if not state["bIsCompiling"] and state["aggregateStatus"] != "Unknown":
                break
        errors = [(x["emitterName"], x["scriptName"], ev["message"]) for x in state["scripts"]
                  for ev in x["compileEvents"] if ev["severity"] == "Error"]
        if errors:
            raise RuntimeError("Niagara 编译失败：\n" + "\n".join("%s %s\n%s" % e for e in errors[:4]))
        self.m.tool(AS + "save_assets", asset_paths=[path])
        return state
