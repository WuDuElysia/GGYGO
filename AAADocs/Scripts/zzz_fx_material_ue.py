"""按 zzz_fx_material.plan() 的方案，在用户打开的 UE 编辑器里（经 MCP）建 master 材质与材质实例。

    build_master(plan):
        新建本批次审批清单内的内容版本；仅在同一批次内复用本会话刚创建的 master
        create_material → 设 BlendMode / Unlit / TwoSided / Niagara 用途
        Custom 节点：代码 = plan.code 前面补内置输入的拼装（VCol/PCol/DPk → float4）
        每个输入一个节点：材质参数（Scalar/Vector/TextureObject）或内置节点，连到 Custom 同名输入
        Custom → Emissive；混合模式需要不透明度时再经 ComponentMask(A) → Opacity
        recompile（编译失败直接抛错）
    build_instance(plan, master): MI 设全部参数值与贴图

用法见 zzz_fx_build.py。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

MASTER_DIR = "/Game/Characters/Shared/FX/ZZZ/Materials"
MI_DIR = "/Game/Characters/Shared/FX/ZZZ/MaterialInstances"
MT = "editor_toolset.toolsets.material.MaterialTools."
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools."
OB = "editor_toolset.toolsets.object.ObjectTools."
AS = "editor_toolset.toolsets.asset.AssetTools."

# 内置输入：Custom 输入名 → (表达式类, 属性, 输出引脚)
BUILTIN_NODES = {
    "WorldPos": ("MaterialExpressionWorldPosition", {}, ""),
    "CamPos": ("MaterialExpressionCameraPositionWS", {}, ""),
    "Time": ("MaterialExpressionTime", {}, ""),
    "PixelDepth": ("MaterialExpressionPixelDepth", {}, ""),
    "FaceSign": ("MaterialExpressionTwoSidedSign", {}, ""),
    "NrmW": ("MaterialExpressionVertexNormalWS", {}, ""),
    "PPos": ("MaterialExpressionParticlePositionWS", {}, ""),
    "PAge": ("MaterialExpressionParticleRelativeTime", {}, ""),
    "PCol": ("MaterialExpressionParticleColor", {}, "RGBA"),
    "VCol_rgb": ("MaterialExpressionVertexColor", {}, ""),
    "VCol_a": ("MaterialExpressionVertexColor", {}, "A"),
    "AtlasFrame": ("MaterialExpressionParticleRandom", {}, ""),
    "PRot": ("MaterialExpressionParticleSpriteRotation", {}, ""),
    "PSize": ("MaterialExpressionParticleSize", {}, ""),
    "RawWorldPos": ("MaterialExpressionWorldPosition", {"WorldPositionShaderOffset": "WPT_ExcludeAllShaderOffsets"}, ""),
}
for _k in range(4):
    BUILTIN_NODES["UV%d" % _k] = ("MaterialExpressionTextureCoordinate", {"CoordinateIndex": _k}, "")
    BUILTIN_NODES["DP%d" % _k] = ("MaterialExpressionDynamicParameter", {"ParameterIndex": _k}, "RGBA")


def ref(path):
    return {"refPath": path if "." in path.rsplit("/", 1)[1] else "%s.%s" % (path, path.rsplit("/", 1)[1])}


def cls(name):
    return {"refPath": "/Script/Engine." + name}


def linear_color(v):
    v = list(v) + [0.0] * (4 - len(v))
    return {"r": v[0], "g": v[1], "b": v[2], "a": v[3]}


class Builder:
    def __init__(self, session):
        self.session = session
        self.m = session.m
        self.masters = set()

    def exists(self, path):
        return self.m.tool(AS + "exists", path=path)["returnValue"]

    def add(self, mat, klass, x, y, props=None):
        e = self.m.tool(MT + "add_expression", material_or_function=mat, expression_class=cls(klass), x=x, y=y)["returnValue"]
        if props:
            self.set(e, props)
        return e

    def set(self, obj, props):
        self.m.tool(OB + "set_properties", instance=obj, values=json.dumps(props))
        back = json.loads(self.m.tool(OB + "get_properties", instance=obj, properties=list(props))["returnValue"])
        for k, v in props.items():
            if isinstance(v, (bool, int, float, str)) and back.get(k) != v and not (
                    isinstance(v, float) and isinstance(back.get(k), (int, float)) and abs(back[k] - v) < 1e-5):
                raise RuntimeError("%s.%s 设置失败：期望 %r 实际 %r" % (obj["refPath"], k, v, back.get(k)))

    def connect(self, src, out_name, dst, in_name):
        self.m.tool(MT + "connect_expressions", from_expression=src, from_output_name=out_name,
                    to_expression=dst, to_input_name=in_name)

    def configure_custom(self, expression, inputs, code, output_type, description):
        cur = json.loads(self.m.tool(OB + "get_properties", instance=expression, properties=["Inputs"])["returnValue"])["Inputs"]
        grown = cur + [dict(cur[0]) for _ in range(len(inputs) - len(cur))]
        # Native ArrayAdd requires existing elements unchanged during expansion.
        self.m.tool(OB + "set_properties", instance=expression, values=json.dumps({"Inputs": grown}))
        cur = json.loads(self.m.tool(OB + "get_properties", instance=expression, properties=["Inputs"])["returnValue"])["Inputs"]
        for i, name in enumerate(inputs):
            cur[i]["inputName"] = name
        self.set(expression, {"Inputs": cur, "Code": code, "OutputType": output_type, "Description": description})
        pins = self.m.tool(MT + "get_expression_input_names", expression=expression)["returnValue"]
        if pins != inputs:
            raise RuntimeError("%s Custom input readback mismatch: expected %s, got %s" % (expression["refPath"], inputs, pins))

    def sampler_type(self, tex_path):
        props = json.loads(self.m.tool(OB + "get_properties", instance=ref(tex_path),
                                       properties=["SRGB", "CompressionSettings"])["returnValue"])
        comp = props["CompressionSettings"]
        if comp in ("TC_Grayscale", "TC_Alpha"):
            return "SAMPLERTYPE_Grayscale" if props["SRGB"] else "SAMPLERTYPE_LinearGrayscale"
        if comp == "TC_Masks":
            return "SAMPLERTYPE_Masks"
        if comp != "TC_Default":
            raise RuntimeError("%s 压缩设置 %s 未处理" % (tex_path, comp))
        return "SAMPLERTYPE_Color" if props["SRGB"] else "SAMPLERTYPE_LinearColor"

    @staticmethod
    def validate_plan(plan):
        if plan.get("output_contract", "color") != "color":
            raise RuntimeError("Distortion fields require their dedicated buffer/composite renderer")
        if type(plan.get("disable_depth_test")) is not bool:
            raise ValueError("Material plan requires its resolved source depth-test state")
        if "ue_environment" in plan:
            import zzz_fx_ue_equivalent as UE
            UE.material_properties(plan["ue_environment"])
            if plan["blend"] != plan["ue_environment"]["blend"]:
                raise ValueError("UE smoke material blend differs from its environment")

    def build_master(self, plan):
        self.validate_plan(plan)
        path = "%s/%s" % (MASTER_DIR, plan["master"])
        if path in self.masters:
            return path
        self.session.begin_create(path)
        mat = self.m.tool(MT + "create_material", folder_path=MASTER_DIR, asset_name=plan["master"])["returnValue"]
        self.session.created_asset(path)
        # 只开实际用到的用途：每多一种顶点工厂就多编一整套排列，大 Custom 节点会把编译内存撑爆。
        # 自动补用途也关掉，误挂到别的组件上时直接显示默认材质，而不是在编辑器里临时加编。
        properties = {"BlendMode": plan["blend"], "ShadingModel": "MSM_Unlit", "TwoSided": plan["two_sided"],
                       "bDisableDepthTest": plan["disable_depth_test"],
                       "bUsedWithNiagaraMeshParticles": plan["renderer_kind"] == "particle" and plan["mesh"],
                       "bUsedWithNiagaraSprites": plan["renderer_kind"] == "particle" and not plan["mesh"],
                       "bAutomaticallySetUsageInEditor": False}
        environment = plan.get("ue_environment")
        if environment is not None:
            import zzz_fx_ue_equivalent as UE
            properties.update(UE.material_properties(environment))
        self.set(mat, properties)

        inputs = []
        prelude = []
        for b in plan["builtins"]:
            if b == "VCol":
                inputs += ["VCol_rgb", "VCol_a"]
                prelude.append("float4 VCol = float4(VCol_rgb, VCol_a);")
            else:
                inputs.append(b)
        inputs += list(plan.get("pixel_params", plan["params"])) + list(plan["textures"])

        custom = self.add(mat, "MaterialExpressionCustom", 0, 0)
        code = "\n".join(prelude) + ("\n" if prelude else "") + plan["code"]
        self.configure_custom(custom, inputs, code, "CMOT_Float4", plan["shader"])

        y = 0
        sources = {}
        for n in inputs:
            if n in BUILTIN_NODES:
                klass, props, out = BUILTIN_NODES[n]
                node = self.add(mat, klass, -600, y, props)
            elif n in plan["params"]:
                p = plan["params"][n]
                if p["dim"] == 1:
                    node = self.add(mat, "MaterialExpressionScalarParameter", -600, y,
                                    {"ParameterName": n, "DefaultValue": float(p["value"])})
                    out = ""
                else:
                    node = self.add(mat, "MaterialExpressionVectorParameter", -600, y, {"ParameterName": n})
                    self.m.tool(OB + "set_properties", instance=node,
                                values=json.dumps({"DefaultValue": linear_color(p["value"])}))
                    out = "RGBA"  # 默认引脚只有 RGB，shader 会读 .w
            else:
                tex = plan["textures"][n]
                node = self.add(mat, "MaterialExpressionTextureObjectParameter", -600, y, {"ParameterName": n})
                self.m.tool(OB + "set_properties", instance=node, values=json.dumps(
                    {"Texture": ref(tex)["refPath"], "SamplerType": self.sampler_type(tex)}))
                out = ""
            self.connect(node, out, custom, n)
            sources[n] = (node, out)
            y += 120

        viewport = plan.get("viewport_clamp")
        if viewport is not None:
            for n in viewport["inputs"]:
                if n in sources or n == "CenterView":
                    continue
                if n in BUILTIN_NODES:
                    klass, props, out = BUILTIN_NODES[n]
                    node = self.add(mat, klass, -600, y, props)
                else:
                    p = viewport["params"][n]
                    node = self.add(mat, "MaterialExpressionScalarParameter", -600, y,
                                    {"ParameterName": n, "DefaultValue": float(p["value"])})
                    out = ""
                sources[n] = (node, out)
                y += 120
            center = self.add(mat, "MaterialExpressionTransformPosition", -300, y,
                              {"TransformSourceType": "TRANSFORMPOSSOURCE_World", "TransformType": "TRANSFORMPOSSOURCE_View"})
            # UE shortens the Input property to NAME_None; MCP exposes "None".
            self.connect(*sources["PPos"], center, "None")
            sources["CenterView"] = (center, "")
            wpo = self.add(mat, "MaterialExpressionCustom", 0, y)
            self.configure_custom(wpo, viewport["inputs"], viewport["code"], "CMOT_Float3",
                                  "UE equivalence: projected billboard viewport size")
            for name in viewport["inputs"]:
                self.connect(*sources[name], wpo, name)
            self.m.tool(MT + "connect_to_output", expression=wpo, output_name="", material_property="MP_WorldPositionOffset")

        lit = environment is not None and environment["lighting"] == "ue_volumetric_nondirectional"
        self.m.tool(MT + "connect_to_output", expression=custom, output_name="",
                    material_property="MP_BaseColor" if lit else "MP_EmissiveColor")
        if lit:
            # AlphaComposite consumes the associated RGB directly. No alpha
            # division, second opacity multiplication or HDR emissive bypass.
            zero = self.add(mat, "MaterialExpressionConstant", 300, 400, {"R": 0.0})
            one = self.add(mat, "MaterialExpressionConstant", 300, 500, {"R": 1.0})
            for prop in ("MP_EmissiveColor", "MP_Metallic", "MP_Specular"):
                self.m.tool(MT + "connect_to_output", expression=zero, output_name="", material_property=prop)
            self.m.tool(MT + "connect_to_output", expression=one, output_name="", material_property="MP_Roughness")
        if plan["blend"] in ("BLEND_AlphaComposite", "BLEND_Translucent"):
            mask = self.add(mat, "MaterialExpressionComponentMask", 300, 200, {"R": False, "G": False, "B": False, "A": True})
            self.connect(custom, "", mask, "")
            self.m.tool(MT + "connect_to_output", expression=mask, output_name="", material_property="MP_Opacity")
        self.m.tool(MT + "recompile", material_or_function=mat)
        self.session.save([path])
        self.masters.add(path)
        return path

    def build_instance(self, plan, master, name):
        path = "%s/%s" % (MI_DIR, name)
        if path in self.session.created:
            return path
        self.session.begin_create(path)
        self.m.tool(MI + "create", folder_path=MI_DIR, asset_name=name, parent=ref(master))
        self.session.created_asset(path)
        mi = ref(path)
        for n, p in plan["params"].items():
            if p["dim"] == 1:
                self.m.tool(MI + "set_scalar_parameter", instance=mi, name=n, value=float(p["value"]))
            else:
                self.m.tool(MI + "set_vector_parameter", instance=mi, name=n, value=linear_color(p["value"]))
        for n, tex in plan["textures"].items():
            self.m.tool(MI + "set_texture_parameter", instance=mi, name=n, value=ref(tex))
        self.session.save([path])
        return path
