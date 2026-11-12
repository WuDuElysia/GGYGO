"""@file zzz_fx_material_ue.py @brief 经MCP制作材质图，以同Editor原生接口完成编译并读回。

    build_master(plan):
        新建本批次审批清单内的内容版本；仅在同一批次内复用本会话刚创建的 master
        create_material → 设 BlendMode / Unlit / TwoSided / Niagara 用途
        Custom 节点：代码 = plan.code 前面补内置输入的拼装（VCol/PCol/DPk → float4）
        每个输入一个节点：材质参数（Scalar/Vector/TextureObject）或内置节点，连到 Custom 同名输入
        Custom → Emissive；混合模式需要不透明度时再经 ComponentMask(A) → Opacity
        recompile → 等当前RHI编译完成 → 读回可渲染ShaderMap → 保存
    build_instance(plan, master): MI 设全部参数值与贴图

用法见 zzz_fx_build.py。
"""
import hashlib
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import zzz_fx_particle_renderer as PR

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
    return {"refPath": name if name.startswith("/Script/") else "/Script/Engine." + name}


def linear_color(v):
    v = list(v) + [0.0] * (4 - len(v))
    return {"r": v[0], "g": v[1], "b": v[2], "a": v[3]}


def _native_property_name(name):
    if name.startswith("b") and len(name) > 1 and name[1].isupper():
        name = name[1:]
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def _native_enum(native, enum_class, value):
    enum_type = getattr(native, enum_class)
    return value if isinstance(value, enum_type) else getattr(enum_type, _native_property_name(value).upper())


def _native_value_equal(native, key, actual, expected, float_equal):
    # Native实数属性读回为float；计划的整数表示不改变目标属性类型。
    if type(actual) is float:
        return (type(expected) in (int, float) and math.isfinite(actual) and math.isfinite(expected)
                and float_equal(actual, expected))
    if type(actual) in (bool, int) or type(expected) in (bool, int, float):
        return type(actual) is type(expected) and actual == expected
    if isinstance(expected, native.LinearColor):
        return isinstance(actual, native.LinearColor) and all(
            _native_value_equal(native, component, getattr(actual, component), getattr(expected, component), float_equal)
            for component in "rgba")
    if key in ("Inputs", "AdditionalOutputs"):
        if len(actual) != len(expected):
            return False
        fields = ("input_name",) if key == "Inputs" else ("output_name", "output_type")
        return all(all(left.get_editor_property(field) == right.get_editor_property(field) for field in fields)
                   for left, right in zip(actual, expected))
    if isinstance(expected, native.Object):
        return actual == expected and actual.get_path_name() == expected.get_path_name()
    # FName/Enum使用原生值比较，不能将Struct的诊断字符串作为相等依据。
    return actual == expected


def set_native_properties(native, obj, props, *, native_sync, float_equal=None):
    """对当前材质对象批写一次并逐值读回；调用者先核本批created包/只读权限。

    native_sync为原宿主的公开同步写入边界，不在本函数推断权限或另建资源门。
    默认数值规则沿原Simple；通用U显式传入原abs<1e-5规则。
    """
    if not callable(native_sync):
        raise ValueError("原生材质属性批写缺少明确的同步预算边界")
    if float_equal is None:
        float_equal = lambda actual, expected: math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6)
    enums = {"BlendMode": "BlendMode", "ShadingModel": "MaterialShadingModel", "MaterialDomain": "MaterialDomain",
             "TranslucencyPass": "MaterialTranslucencyPass", "TranslucencyLightingMode": "TranslucencyLightingMode",
             "SamplerType": "MaterialSamplerType", "OutputType": "CustomMaterialOutputType",
             "WorldPositionShaderOffset": "WorldPositionIncludedOffsets", "RefractionMethod": "RefractionMode",
             "TransformSourceType": "MaterialVectorCoordTransformSource", "TransformType": "MaterialVectorCoordTransform"}
    converted = {}
    for key, value in props.items():
        if key in enums:
            enum_class = enums[key]
            if key in ("TransformSourceType", "TransformType") and isinstance(obj, native.MaterialExpressionTransformPosition):
                enum_class = "MaterialPositionTransformSource"
            value = _native_enum(native, enum_class, value)
        elif key == "Texture":
            if isinstance(value, dict):
                if set(value) != {"refPath"}:
                    raise ValueError("材质纹理必须是准确的单键refPath")
                path = value["refPath"]
            else:
                path = ref(value)["refPath"]
            value = native.load_object(None, path)
            if not isinstance(value, native.Texture) or value.get_path_name() != path:
                raise ValueError("材质纹理类型或完整对象路径不符：" + path)
        elif key == "DefaultValue" and isinstance(value, dict):
            if set(value) != set("rgba"):
                raise ValueError("材质颜色需要完整RGBA，不补默认分量")
            value = native.LinearColor(value["r"], value["g"], value["b"], value["a"])
        elif isinstance(value, dict):
            raise ValueError("未声明的材质结构属性，不能猜测Native类型：" + key)
        converted[_native_property_name(key)] = value
    if not converted:
        return
    native_sync("material_properties:" + obj.get_path_name(), lambda: obj.set_editor_properties(converted))
    for key in props:
        name = _native_property_name(key)
        actual = obj.get_editor_property(name)
        if not _native_value_equal(native, key, actual, converted[name], float_equal):
            raise RuntimeError("材质原生属性读回不符：%s.%s 期望%r 实际%r" % (
                obj.get_path_name(), key, converted[name], actual))


def configure_native_custom(native, node, inputs, code, output_type, description, *,
                            native_sync, additional_outputs=None, float_equal=None):
    """首次接线前构齐独立的Custom结构数组，再与代码/类型/描述一次提交。

    additional_outputs为明确的(name, type_name)对；None不改，[]明确清空。
    不编辑隐藏FExpressionInput，不克隆/扩容附着数组，也不抑制节点PostEdit维护。
    """
    library = native.MaterialEditingLibrary
    if any(library.get_inputs_for_material_expression(node.get_outer(), node)):
        raise ValueError("不能在Custom已接线后重置输入数组：" + node.get_path_name())
    entries = []
    for name in inputs:
        item = native.CustomInput()
        item.set_editor_property("input_name", name)
        entries.append(item)
    props = {"Inputs": entries, "Code": code, "OutputType": output_type, "Description": description}
    if additional_outputs is not None:
        outputs = []
        for name, type_name in additional_outputs:
            item = native.CustomOutput()
            item.set_editor_property("output_name", name)
            item.set_editor_property("output_type", _native_enum(native, "CustomMaterialOutputType", type_name))
            outputs.append(item)
        props["AdditionalOutputs"] = outputs
    set_native_properties(native, node, props, native_sync=native_sync, float_equal=float_equal)
    if list(library.get_material_expression_input_names(node)) != inputs:
        raise RuntimeError("Custom公开输入端口读回不符：" + node.get_path_name())


def _u_float_equal(actual, expected):
    return abs(actual - expected) < 1e-5


def _source_varying_layout(plan):
    """消费原FP的live分量集合；按原生UV空洞打包规则核同图插值预算。"""
    layout = []
    for row in plan["vertex_stage"]["varyings"]:
        used = row.get("components")
        if (not isinstance(used, str) or not used or len(used) != len(set(used))
                or set(used) - set("xyzw")):
            raise ValueError("源varying缺准确FP分量集合：" + row["name"])
        # ComponentMask始终按RGBA输出；原集合字符串可能是wxyz。
        lanes = "".join(c for c in "xyzw" if c in used)
        payload = row.get("native_payload")
        if payload is not None:
            proof = payload.get("proof", {})
            source_program = (plan.get("source_selection") or {}).get("programs", {}).get("vp")
            if (plan["renderer_kind"] != "generated_ribbon"
                    or payload.get("schema") != "GGYGO.SourceProvenNativeVarying/v1"
                    or payload.get("components") != lanes or proof.get("components") != lanes
                    or proof.get("output_register") != row["source_register"]
                    or proof.get("source_program") != source_program
                    or proof.get("rule") != "CopyUniformSelectLiteralOne"
                    or proof.get("scalar_type") != "float32"
                    or proof.get("native_interpolation") != "default_perspective"
                    or proof.get("uniform_scope") != "MaterialParametersWithoutCustomPrimitiveData"
                    or not isinstance(payload.get("code"), str) or not payload["code"]
                    or proof.get("code_sha256") != hashlib.sha256(payload["code"].encode()).hexdigest()):
                raise ValueError("Native varying缺同一源VP的完整copy/select来源证明：" + row["name"])
            builtins = set()
            for field in proof["native_inputs"]:
                builtin, component = field["builtin"], field["component"]
                if (not re.fullmatch(r"DP[0-3]", builtin) or component not in "xyzw" or len(component) != 1
                        or not plan["dynamic_parameter_components"] & (1 << (int(builtin[2]) * 4 + "xyzw".index(component)))):
                    raise ValueError("Native varying的实际DP/validmask未提供：" + row["name"])
                builtins.add(builtin)
            parameters = proof["uniform_parameters"]
            if (any(plan["params"].get(name, {}).get("dim") != dim for name, dim in parameters.items())
                    or payload["inputs"] != sorted(builtins) + list(parameters)):
                raise ValueError("Native varying未复用原同一材质统一参数输入：" + row["name"])
        layout.append((row, "" if payload is not None else lanes, payload))
    pixel_uvs = {int(name[2:]) for name in plan["builtins"] if re.fullmatch(r"UV[0-3]", name)}
    viewport = plan.get("viewport_clamp") or {}
    other_scalars = (3 if plan.get("mesh_affine") is not None else 0)
    other_scalars += 3 if viewport.get("facing_adapter") is not None else 0
    occupied = set(pixel_uvs)
    next_uv = 0
    for _ in range((sum(len(lanes) for _, lanes, _ in layout) + other_scalars + 1) // 2):
        while next_uv in occupied:
            next_uv += 1
        occupied.add(next_uv)
    # Ribbon VF从TEXCOORD1开始，HitProxy/Velocity固定保留6；只用VS的UV不占此PS集合。
    if plan["renderer_kind"] == "generated_ribbon" and 1 + max(occupied, default=-1) // 2 >= 6:
        raise ValueError("Native Ribbon的PS UV及全部插值超出TEXCOORD1–5，不能覆盖位置/Velocity语义：" + plan["master"])
    return layout


def build_source_mesh_uv(material, plan, builder):
    """在Rendering原新Master中消费唯一PU算法；返回同一材质的真实UE UV表达式。"""
    import zzz_fx_particle_uv as PU
    uv = plan["source_identity"]["source_programs"]["mesh_uv"]
    adapter = uv["adapter"]
    if adapter != PU.mesh_uv_adapter(adapter["source_module"], adapter["source_node"]) or uv["mode"] != adapter["mode"]:
        raise ValueError("Mesh UV制作合同与原模块／唯一算法不符")
    coordinate = builder.add(material, "MaterialExpressionTextureCoordinate", -2500, 600, {"CoordinateIndex": 0})
    if adapter["mode"] == "OriginalMeshUV0":
        return coordinate, ""
    if adapter["mode"] != "FXAnimatedMeshUV0" or adapter["native_binding"] != "MaterialRandomBinding":
        raise ValueError("未实现的Mesh UV原生运输")
    frame = builder.add(material, "MaterialExpressionParticleRandom", -2500, 750)
    expression = builder.add(material, "MaterialExpressionCustom", -2200, 600)
    builder.configure_custom(expression, adapter["inputs"], adapter["code"], "CMOT_Float2", "原粒子Grid UV及稳定出生行")
    builder.connect(coordinate, "", expression, "UV0")
    builder.connect(frame, "", expression, "AtlasFrame")
    return expression, ""


class Builder:
    def __init__(self, session, *, unreal=None):
        self.session = session
        self.m = session.m
        self.native = unreal
        self.masters = set()
        self.native_sync = getattr(self.m, "run_native_sync", None)
        # 原Toolset同步返回不代表Shader已完成；必须在创建前具备实际完成及读回接口。
        if (unreal is None or not callable(self.native_sync)
                or not callable(getattr(getattr(unreal, "MaterialEditingLibrary", None), "get_statistics", None))
                or not callable(getattr(getattr(unreal, "GGYGOProjectedDecalRendererProperties", None),
                                        "read_material_compilation_for_authoring", None))):
            raise ValueError("FX材质制作需要同一Editor的受控原生属性批写、编译完成及ShaderMap读回接口")

    def _finish_master(self, material):
        """完成当前Master的既有编译并严格读回；不另排任务，不将工具返回当成完成。"""
        actual = self.native.load_object(None, material["refPath"])
        if not isinstance(actual, self.native.Material) or actual.get_path_name() != material["refPath"]:
            raise RuntimeError("待完成的FX Master类型或路径不符：" + material["refPath"])
        self.m.tool(MT + "recompile", material_or_function=material)
        # GetStatistics提交并完成当前RHI资源的原编译；统计为0不代替ShaderMap判定。
        self.native.MaterialEditingLibrary.get_statistics(actual)
        state = self.native.GGYGOProjectedDecalRendererProperties.read_material_compilation_for_authoring(actual)
        if not isinstance(state, tuple) or len(state) != 3:
            raise RuntimeError("FX Master编译读回未返回实际三项结果：%s %r" % (material["refPath"], state))
        shader_map_complete, compile_errors, error = state
        if shader_map_complete is not True or len(compile_errors) != 0 or error:
            raise RuntimeError("FX Master ShaderMap未完成或有编译诊断：%s %r" % (material["refPath"], state))

    def exists(self, path):
        return self.m.tool(AS + "exists", path=path)["returnValue"]

    def add(self, mat, klass, x, y, props=None):
        e = self.m.tool(MT + "add_expression", material_or_function=mat, expression_class=cls(klass), x=x, y=y)["returnValue"]
        if props:
            self.set(e, props)
        return e

    def set(self, obj, props):
        actual = self._owned_native_object(obj)
        set_native_properties(self.native, actual, props, native_sync=self.native_sync, float_equal=_u_float_equal)

    def _owned_native_object(self, obj):
        path = obj["refPath"]
        package = path.split(".", 1)[0]
        self.session.require_created(package)
        actual = self.native.load_object(None, path)
        if (not isinstance(actual, (self.native.Material, self.native.MaterialExpression))
                or actual.get_path_name() != path):
            raise ValueError("属性目标不是本批材质或表达式的准确对象：" + path)
        if isinstance(actual, self.native.MaterialExpression):
            owner = actual.get_outer()
            if not isinstance(owner, self.native.Material) or owner.get_path_name() != ref(package)["refPath"]:
                raise ValueError("表达式outer不是本批创建的准确Master：" + path)
        return actual

    @staticmethod
    def _verify_value(expected, actual, path):
        """核对 Native JSON 值；对象引用显式使用完整 refPath，结构和数组逐项核对。"""
        if isinstance(expected, dict):
            if not isinstance(actual, dict) or set(actual) != set(expected):
                raise RuntimeError("%s 属性字段不一致：期望 %r 实际 %r" % (path, expected, actual))
            for name, value in expected.items():
                Builder._verify_value(value, actual[name], path + "." + name)
        elif isinstance(expected, list):
            if not isinstance(actual, list) or len(actual) != len(expected):
                raise RuntimeError("%s 属性数组不一致：期望 %r 实际 %r" % (path, expected, actual))
            for index, (value, readback) in enumerate(zip(expected, actual)):
                Builder._verify_value(value, readback, "%s[%d]" % (path, index))
        elif type(expected) is float:
            if (type(actual) not in (int, float) or not math.isfinite(expected) or not math.isfinite(actual)
                    or abs(actual - expected) >= 1e-5):
                raise RuntimeError("%s 属性值不一致：期望 %r 实际 %r" % (path, expected, actual))
        elif type(actual) is not type(expected) or actual != expected:
            raise RuntimeError("%s 属性值不一致：期望 %r 实际 %r" % (path, expected, actual))

    def connect(self, src, out_name, dst, in_name):
        self.m.tool(MT + "connect_expressions", from_expression=src, from_output_name=out_name,
                    to_expression=dst, to_input_name=in_name)

    def configure_custom(self, expression, inputs, code, output_type, description, additional_outputs=None):
        actual = self._owned_native_object(expression)
        outputs = None if additional_outputs is None else [(name, "CMOT_Float4") for name in additional_outputs]
        configure_native_custom(self.native, actual, inputs, code, output_type, description,
                                native_sync=self.native_sync, additional_outputs=outputs, float_equal=_u_float_equal)

    def material_input_node(self, mat, name, plan, y):
        if name in ("RawTC6Z", "RawTC6W"):
            if plan.get("renderer_kind") != "generated_ribbon" or plan.get("generated_ribbon") is None:
                raise ValueError("Raw TC6 两条 float 仅用于明确 Generated Ribbon 输入")
            klass = "MaterialExpressionParticleRelativeTime" if name == "RawTC6Z" else "MaterialExpressionParticleRandom"
            return self.add(mat, klass, -600, y), ""
        if name in BUILTIN_NODES:
            klass, props, output = BUILTIN_NODES[name]
            return self.add(mat, klass, -600, y, props), output
        if name in plan["params"]:
            parameter = plan["params"][name]
            if parameter["dim"] == 1:
                return self.add(mat, "MaterialExpressionScalarParameter", -600, y,
                    {"ParameterName": name, "DefaultValue": float(parameter["value"]), "bUseCustomPrimitiveData": False}), ""
            node = self.add(mat, "MaterialExpressionVectorParameter", -600, y, {"ParameterName": name})
            self.set(node, {"DefaultValue": linear_color(parameter["value"]), "bUseCustomPrimitiveData": False})
            return node, "RGBA"
        texture = plan["textures"][name]
        node = self.add(mat, "MaterialExpressionTextureObjectParameter", -600, y, {"ParameterName": name})
        self.set(node, {"Texture": ref(texture), "SamplerType": self.sampler_type(texture)})
        return node, ""

    def build_source_vertex_nodes(self, material, plan, sources, y):
        stage = plan["vertex_stage"]
        layout = _source_varying_layout(plan)
        inputs, prelude = [], []
        for name in stage["builtins"]:
            if name == "VCol":
                inputs.extend(("VCol_rgb", "VCol_a"))
                prelude.append("float4 VCol = float4(VCol_rgb, VCol_a);")
            else:
                inputs.append(name)
        inputs += stage["params"] + stage["textures"]
        vertex = self.add(material, "MaterialExpressionCustom", 0, y)
        self.configure_custom(vertex, inputs, "\n".join(prelude) + "\n" + stage["code"], "CMOT_Float3",
                              "原VS顶点采样、真实外扩及插值", [row["name"] for row in stage["varyings"]])
        for name in inputs:
            source_name = {"WorldPos": "SourceVertexWorldPos", "NrmW": "SourceVertexNrmW"}.get(name, name)
            if source_name not in sources:
                sources[source_name] = self.material_input_node(material, "RawWorldPos" if name == "WorldPos" else name, plan, y)
                y += 120
            self.connect(*sources[source_name], vertex, name)
        wpo = vertex
        if stage.get("deformation", {}).get("mode") == "SourceVertexTexturePosition":
            # 原 VS 输出局部绝对顶点；引擎实例矩阵拥有粒子和组件 TRS，只在这里应用一次。
            position = self.add(material, "MaterialExpressionTransformPosition", 200, y,
                {"TransformSourceType": "TRANSFORMPOSSOURCE_Instance", "TransformType": "TRANSFORMPOSSOURCE_World"})
            self.connect(vertex, "", position, "")
            wpo = self.add(material, "MaterialExpressionSubtract", 400, y)
            self.connect(position, "", wpo, "A")
            self.connect(*sources["RawWorldPos"], wpo, "B")
        self.m.tool(MT + "connect_to_output", expression=wpo, output_name="", material_property="MP_WorldPositionOffset")
        for row, lanes, payload in layout:
            if payload is not None:
                native_value = self.add(material, "MaterialExpressionCustom", 600, y)
                self.configure_custom(native_value, payload["inputs"], payload["code"], "CMOT_Float4",
                                      "同源copy/统一选择复用Native已有插值payload")
                for name in payload["inputs"]:
                    if name not in sources:
                        sources[name] = self.material_input_node(material, name, plan, y)
                    self.connect(*sources[name], native_value, name)
                sources[row["name"]] = native_value, ""
                y += 120
                continue
            value = vertex, row["name"]
            if lanes != "xyzw":
                mask = self.add(material, "MaterialExpressionComponentMask", 200, y,
                    {channel: lane in lanes for channel, lane in zip("RGBA", "xyzw")})
                self.connect(*value, mask, "")
                value = mask, ""
            varying = self.add(material, "MaterialExpressionVertexInterpolator", 300, y)
            self.connect(*value, varying, "VS")
            if lanes == "xyzw":
                sources[row["name"]] = varying, ""
            else:
                packed = {lane: ("Packed" if len(lanes) == 1 else "Packed." + "xyzw"[index])
                          for index, lane in enumerate(lanes)}
                restored = self.add(material, "MaterialExpressionCustom", 600, y)
                code = "return float4(" + ",".join(packed.get(lane, "0.0") for lane in "xyzw") + ");"
                self.configure_custom(restored, ["Packed"], code, "CMOT_Float4", "按原lane恢复FP已用分量")
                self.connect(varying, "", restored, "Packed")
                sources[row["name"]] = restored, ""
            y += 120

    def sampler_type(self, tex_path):
        props = json.loads(self.m.tool(OB + "get_properties", instance=ref(tex_path),
                                       properties=["SRGB", "CompressionSettings"])["returnValue"])
        comp = props["CompressionSettings"]
        if comp in ("TC_Grayscale", "TC_Alpha"):
            return "SAMPLERTYPE_Grayscale" if props["SRGB"] else "SAMPLERTYPE_LinearGrayscale"
        if comp == "TC_Masks":
            return "SAMPLERTYPE_Masks"
        if comp == "TC_HDR" and props["SRGB"] is False:
            return "SAMPLERTYPE_LinearColor"
        if comp != "TC_Default":
            raise RuntimeError("%s 压缩设置 %s 未处理" % (tex_path, comp))
        return "SAMPLERTYPE_Color" if props["SRGB"] else "SAMPLERTYPE_LinearColor"

    @staticmethod
    def validate_plan(plan):
        generated_ribbon = None
        length_color = None
        if (plan.get("renderer_kind") == "generated_ribbon" or plan.get("generated_ribbon") is not None
                or plan.get("source_trail_length_color") is not None):
            from zzz_fx_material import generated_ribbon_contract, source_trail_length_color_contract
            context = {"kind": plan["renderer_kind"], "mesh": plan["mesh"], "generated_ribbon": plan.get("generated_ribbon")}
            context.update({key: plan[key] for key in ("component_age_binding", "mesh_affine", "mesh_uv", "viewport_clamp",
                                                       "source_trail_length_color") if key in plan})
            generated_ribbon = generated_ribbon_contract(context)
            length_color = source_trail_length_color_contract(context)
            if (plan.get("configuration_mode") != "ProjectConfigured" or plan.get("output_contract") != "color"
                    or plan.get("blend") != "BLEND_AlphaComposite" or plan.get("vertex_stage") is None
                    or plan.get("dynamic_parameter_components") != 0xFFFF
                    or any(plan.get("dyn_params", {}).get(slot, plan.get("dyn_params", {}).get(str(slot))) != "GeneratedTC%d" % (slot + 1)
                           for slot in range(4))):
                raise ValueError("Generated Ribbon 缺完整颜色／22 UV 原生传输合同")
        component_age = plan.get("component_age_binding")
        component_coverage = plan.get("component_coverage_binding")
        if component_coverage is not None and (component_age is None
                or component_coverage != {"DP0.y": "ParticleLifetimeFade"}):
            raise ValueError("静态材质缺明确粒子寿命消退绑定")
        if component_age is not None and (component_age != {"DP0.x": "System.Age"}
                or plan.get("renderer_kind") != "mesh" or not plan.get("mesh")
                or plan.get("dynamic_parameter_components") != (3 if component_coverage is not None else 1)
                or "DP0" not in plan.get("builtins", []) or "Time" in plan.get("builtins", [])):
            raise ValueError("普通静态材质缺准确Native Emitter System.Age传输")
        if plan.get("configuration_mode") == "ProjectConfigured" and plan.get("translucency_pass") != "MTP_BeforeDOF":
            raise ValueError("ProjectConfigured material lacks its explicit native translucency stage")
        contract = plan.get("output_contract", "color")
        if contract not in ("color", "distortion_field_pair"):
            raise RuntimeError("Distortion fields require their dedicated buffer/composite renderer")
        if contract == "distortion_field_pair" and (set(plan.get("fields", {})) != {"DefaultField", "OverlayField"}
                or plan.get("field_routing") != {"DefaultField": "source_o0", "OverlayField": "source_o1"}
                or [plan["fields"][k].get("output_register") for k in ("DefaultField", "OverlayField")] != [0, 1]):
            raise ValueError("Dual field must preserve both complete source registers")
        if contract == "distortion_field_pair":
            mask = plan.get("dynamic_parameter_components")
            fields = plan["fields"]
            masks = [fields[key].get("dynamic_parameter_components") for key in ("DefaultField", "OverlayField")]
            if type(mask) is not int or not 0 <= mask <= 65535 \
                    or any(type(value) is not int or not 0 <= value <= 65535 for value in masks) \
                    or mask != masks[0] | masks[1]:
                raise ValueError("Field output/geometry dynamic component masks are incomplete")
        if type(plan.get("disable_depth_test")) is not bool:
            raise ValueError("Material plan requires its resolved source depth-test state")
        viewport = plan.get("viewport_clamp") or {}
        facing = viewport.get("facing_adapter")
        if facing is not None and (contract != "color" or plan.get("mesh") or viewport.get("mode") != "ProjectConfigured"
                or facing.get("kind") != "CameraPositionWithViewRoll"
                or facing.get("previous_baseline") != "NativeParticleApproximationWithExplicitPreviousView"
                or facing.get("normal_inputs") != ["CamPos", "PPos", "UEFX_PreviousView", "NativeNormal"]
                or not isinstance(facing.get("normal_code"), str) or not facing["normal_code"]
                or "UEFX_PreviousView" not in viewport.get("inputs", [])
                or set(viewport.get("inputs", [])) != (
                    {"DP3", "UV0", "RawWorldPos", "PPos", "CenterView", "CamPos", "UEFX_PreviousView"} | set(viewport.get("params", {})))
                or facing.get("verification_requirements") != [
                    "FRayTracingDynamicGeometryConverterCS_ActualDispatchWithoutFallback",
                    "CurrentPreviousNativeBaseline", "WorldNormalAndShadowBiasBaseline", "FullQuadAndConservativeBounds"]):
            raise ValueError("Incomplete ordinary Facing geometry/normal/previous-view contract")
        affine = plan.get("mesh_affine")
        if affine is not None and (affine.get("mode") != "full_affine_local_mesh_v1"
                or not plan.get("mesh") or plan.get("viewport_clamp") is not None):
            raise ValueError("Complete affine mesh geometry cannot mix with a sprite viewport adapter")
        vertex = plan.get("vertex_stage")
        if (vertex or {}).get("source_trail_length_color") != length_color:
            raise ValueError("源拖尾长度色与实际源 VS 输入合同不同")
        if vertex is not None:
            radius = plan.get("additional_wpo_bounds_radius_cm")
            if generated_ribbon is not None:
                age = generated_ribbon["system_age"]["parameter"]
                geometry = vertex.get("geometry")
                expected_geometry = {"mode": "NativeGeneratedRibbon", "position_space": "WorldBakedUnityMetres",
                                     "additional_wpo_cm": 0.0, "source_uniform_constraints": {
                                         name: 0.0 for name in ("_CollideWithAvatar", "_ZOffset", "_ClampZToFar")}}
                if (vertex.get("mode") != "SourceVertexProgramWithInterpolatedOutputs" or vertex.get("deformation") is not None
                        or geometry != expected_geometry or type(radius) not in (int, float) or radius != 0.0
                        or not vertex.get("code") or not vertex.get("varyings")
                        or not {"WorldPos", "RawWorldPos", "PCol", "UV0", "UV1", "DP0", "DP1", "DP2", "DP3", "RawTC6Z", "RawTC6W"}
                            <= set(vertex["builtins"])
                        or {"Time", "PixelDepth", "FaceSign"} & set(vertex["builtins"])
                        or "Time" in plan["builtins"] or re.search(r"\bTime\b", vertex["code"]) or re.search(r"\bTime\b", plan["code"])
                        or plan["params"].get(age) != {"dim": 1, "value": 0.0}
                        or age not in vertex["params"] or age not in plan["pixel_params"]
                        or not set(vertex["params"]) <= set(plan["params"]) or not set(vertex["textures"]) <= set(plan["textures"])):
                    raise ValueError("Generated Ribbon 原 VS 插值／Native 位置／同 NS 时钟不完整")
            elif vertex.get("deformation", {}).get("mode") == "SourceVertexTexturePosition":
                deformation = vertex["deformation"]
                if contract != "color" or not plan.get("mesh") or viewport or affine \
                        or vertex.get("mode") != "SourceVertexProgramWithInterpolatedOutputs" \
                        or not vertex.get("code") or not vertex.get("varyings") or radius != 0.0 \
                        or deformation.get("bounds_owner") != "StaticMeshSourceTextureEnvelope" \
                        or deformation.get("transform_owner") != "NativeNiagaraMeshInstance" \
                        or deformation.get("mesh_import", {}).get("mode") != "SourceVertexTextureMesh" \
                        or not {"RawWorldPos", "UV1", "DP0", "PAge"} <= set(vertex["builtins"]) \
                        or {"PixelDepth", "FaceSign", "WorldPos"} & set(vertex["builtins"]) \
                        or not set(vertex["params"]) <= set(plan["params"]) \
                        or not set(vertex["textures"]) <= set(plan["textures"]):
                    raise ValueError("顶点位置贴图的局部采样、原生粒子 TRS 或网格包围范围不完整")
            elif contract != "color" or not plan.get("mesh") or viewport \
                    or vertex.get("mode") != "SourceVertexProgramWithInterpolatedOutputs" \
                    or not vertex.get("code") or not vertex.get("varyings") \
                    or type(radius) not in (int, float) or not math.isfinite(radius) or radius <= 0 \
                    or radius != vertex["deformation"]["additional_bounds_radius_cm"] \
                    or not {"RawWorldPos", "WorldPos"} <= set(vertex["builtins"]) \
                    or {"PixelDepth", "FaceSign"} & set(vertex["builtins"]) \
                    or not set(vertex["params"]) <= set(plan["params"]) \
                    or not set(vertex["textures"]) <= set(plan["textures"]):
                raise ValueError("原VS采样、插值、唯一WPO或真实包围范围合同不完整")
            names = [row["name"] for row in vertex["varyings"]]
            if len(names) != len(set(names)) or any(not name.startswith("UEFX_Varying_") for name in names):
                raise ValueError("原VS插值输出须保持唯一名称及真实stage映射")
        alignment = (affine or {}).get("project_alignment")
        if alignment is not None:
            choice = PR.validate_mesh_alignment_transport(alignment)
            extra = ["FXParticleEuler", "FXPreviousView"] + (["FXVelocity"] if choice["alignment"] == "Velocity" else [])
            dyn = plan["dyn_params"]
            if affine["wpo_inputs"] != ["FXAffineTransport", "MeshPos"] + extra \
                    or affine["normal_inputs"] != ["FXAffineTransport", "MeshNormal"] + extra \
                    or dyn.get(3, dyn.get("3")) != "FullAffineTransport" \
                    or plan["dynamic_parameter_components"] & alignment["required_components"] != alignment["required_components"]:
                raise ValueError("Mesh project basis/Euler inputs or actual component mask mismatch")
        if "ue_environment" in plan:
            import zzz_fx_ue_equivalent as UE
            UE.material_properties(plan["ue_environment"])
            if plan["blend"] != plan["ue_environment"]["blend"]:
                raise ValueError("UE smoke material blend differs from its environment")
        if plan.get("project_environment") is not None:
            from zzz_fx_native_shader import project_material_properties
            project_material_properties(plan["project_environment"])
            if plan.get("ue_environment") is not None or plan["blend"] != plan["project_environment"]["blend"]:
                raise ValueError("Project environment cannot mix with another rendering policy")
        environment = plan.get("project_environment") or {}
        if plan.get("native_depth_velocity") is not None or environment.get("name") == "project_native_depth_velocity_fullres":
            from zzz_fx_native_shader import project_depth_velocity_contract
            selection = plan["source_selection"]
            depth_velocity = project_depth_velocity_contract(plan.get("native_depth_velocity"), selection["material_pid"])
            if (depth_velocity is None or environment.get("name") != "project_native_depth_velocity_fullres"
                    or environment.get("depth_velocity_contract") != depth_velocity
                    or plan.get("configuration_mode") != "ProjectConfigured" or plan.get("output_contract") != "color"
                    or plan.get("renderer_kind") != "particle"
                    or plan.get("blend") != "BLEND_AlphaComposite" or plan.get("translucency_pass") != "MTP_BeforeDOF"
                    or plan.get("disable_depth_test") is not False):
                raise ValueError("额外Depth/Velocity缺准确源材质／Native粒子／颜色阶段配对")

    @staticmethod
    def require_dual_field_class(mcp, *, unreal=None):
        """用实际 Editor 的公开材质 pin API 核双路 float4；只读，不创建资产。

        @param mcp 同一 Editor 的原工具连接，仅读取具有编辑权限的合同标量。
        @param unreal 调用方明确提供的同一 Editor 原生 Python 上下文。
        FExpressionInput 没有通用属性读取权限，输入形状由公开 MaterialEditingLibrary 核验。
        """
        library = getattr(unreal, "MaterialEditingLibrary", None)
        if (unreal is None or not callable(getattr(unreal, "load_object", None))
                or library is None or not callable(getattr(library, "get_material_expression_input_names", None))
                or not callable(getattr(library, "get_material_expression_input_types", None))):
            raise RuntimeError("双场预检缺实际 Editor 的原生材质输入名称／类型接口")
        field_class = "/Script/GGYGORendering.Default__GGYGOMaterialExpressionDistortionField"
        expression = unreal.load_object(None, field_class)
        if (not isinstance(expression, unreal.MaterialExpression)
                or expression.get_class().get_path_name() != "/Script/GGYGORendering.GGYGOMaterialExpressionDistortionField"):
            raise RuntimeError("实际 Editor 未加载准确双场 Native 类：" + field_class)
        pins = list(library.get_material_expression_input_names(expression))
        types = list(library.get_material_expression_input_types(expression))
        # MaterialValueType.h 的 EMaterialValueType 未作 UENUM；MCT_Float4 明确定义为 1u << 3。
        if pins != ["DefaultField", "OverlayField"] or types != [1 << 3, 1 << 3] \
                or any(type(value) is not int for value in types):
            raise RuntimeError("实际双场 Native 输入须为按序 DefaultField／OverlayField float4：%r / %r" % (pins, types))
        fields = json.loads(mcp.tool(OB + "get_properties", instance={"refPath": field_class},
                                     properties=["bStreamContractConfigured", "RequiredDynamicParameterComponents"])["returnValue"])
        # CDO 的未配置 false／0 是合法初值；这里只确认实际字段类型与允许范围，不认证材质已就绪。
        if (not isinstance(fields, dict) or set(fields) != {"bStreamContractConfigured", "RequiredDynamicParameterComponents"}
                or type(fields["bStreamContractConfigured"]) is not bool
                or type(fields["RequiredDynamicParameterComponents"]) is not int
                or not 0 <= fields["RequiredDynamicParameterComponents"] <= 65535):
            raise RuntimeError("实际双场 Native 缺布尔／16位分量掩码合同")

    @staticmethod
    def require_native_depth_velocity(mcp, value):
        """在制作前核实际公开 ABI／具名 CVar，不设置全局状态或签 GPU 执行。"""
        from zzz_fx_native_shader import project_depth_velocity_contract
        contract = project_depth_velocity_contract(value)
        if contract is None:
            raise ValueError("额外Depth/Velocity制作前缺完整合同")
        names = ["bOutputTranslucentVelocity", "OpacityMaskClipValue", "bUsedWithNiagaraSprites"]
        material = json.loads(mcp.tool(OB + "get_properties", instance={"refPath": "/Script/Engine.Default__Material"},
                                      properties=names)["returnValue"])
        if (not set(names) <= material.keys() or type(material["bOutputTranslucentVelocity"]) is not bool
                or type(material["bUsedWithNiagaraSprites"]) is not bool
                or type(material["OpacityMaskClipValue"]) not in (int, float)
                or not math.isfinite(material["OpacityMaskClipValue"])):
            raise RuntimeError("当前Native Material缺实际Sprite／DepthVelocity／阈值ABI")
        for name, expected in contract["runtime_cvars"].items():
            matches = json.loads(mcp.tool("EditorToolset.EditorAppToolset.SearchCVars", name=name)["returnValue"])
            if name not in matches or "value" not in matches[name]:
                raise RuntimeError("额外Depth/Velocity缺实际具名CVar：" + name)
            actual = matches[name]["value"]
            if type(actual) not in (int, float) or not math.isfinite(actual) or actual != expected:
                raise RuntimeError("额外Depth/Velocity运行前置不符：%s=%r，要求%r" % (name, actual, expected))

    def build_master(self, plan):
        self.validate_plan(plan)
        if plan.get("output_contract") == "distortion_field_pair":
            return self.build_field_master(plan)
        path = "%s/%s" % (MASTER_DIR, plan["master"])
        if path in self.masters:
            return path
        if plan.get("native_depth_velocity") is not None:
            self.require_native_depth_velocity(self.m, plan["native_depth_velocity"])
        self.session.begin_create(path)
        mat = self.m.tool(MT + "create_material", folder_path=MASTER_DIR, asset_name=plan["master"])["returnValue"]
        self.session.created_asset(path)
        # 只开实际用到的用途：每多一种顶点工厂就多编一整套排列，大 Custom 节点会把编译内存撑爆。
        # 自动补用途也关掉，误挂到别的组件上时直接显示默认材质，而不是在编辑器里临时加编。
        properties = {"BlendMode": plan["blend"], "ShadingModel": "MSM_Unlit", "TwoSided": plan["two_sided"],
                       "bDisableDepthTest": plan["disable_depth_test"],
                       "bUsedWithNiagaraMeshParticles": plan["mesh"] and (
                           plan["renderer_kind"] == "particle" or plan.get("component_age_binding") is not None),
                       "bUsedWithNiagaraSprites": plan["renderer_kind"] == "particle" and not plan["mesh"],
                       "bAutomaticallySetUsageInEditor": False}
        if plan["renderer_kind"] == "generated_ribbon":
            properties["bUsedWithNiagaraRibbons"] = True
        if plan.get("translucency_pass") is not None:
            properties["TranslucencyPass"] = plan["translucency_pass"]
        environment = plan.get("ue_environment")
        if environment is not None:
            import zzz_fx_ue_equivalent as UE
            properties.update(UE.material_properties(environment))
        if plan.get("project_environment") is not None:
            from zzz_fx_native_shader import project_material_properties
            environment = plan["project_environment"]
            properties.update(project_material_properties(environment))
        if plan.get("mesh_affine") is not None:
            properties.update(bTangentSpaceNormal=False, MaxWorldPositionOffsetDisplacement=0.0,
                              bEnableNewHLSLGenerator=False)
        if (plan.get("viewport_clamp") or {}).get("mode") == "ProjectConfigured":
            properties.update(MaxWorldPositionOffsetDisplacement=0.0, bEnableNewHLSLGenerator=False)
        if plan.get("vertex_stage") is not None:
            properties.update(MaxWorldPositionOffsetDisplacement=0.0, bEnableNewHLSLGenerator=False)
        if (plan.get("viewport_clamp") or {}).get("facing_adapter") is not None:
            properties.update(bTangentSpaceNormal=False)
        self.set(mat, properties)

        inputs = []
        prelude = []
        for b in plan["builtins"]:
            if b == "VCol":
                inputs += ["VCol_rgb", "VCol_a"]
                prelude.append("float4 VCol = float4(VCol_rgb, VCol_a);")
            else:
                inputs.append(b)
        inputs += list(plan.get("pixel_params", plan["params"])) + list(plan.get("pixel_textures", plan["textures"]))
        if plan.get("vertex_stage") is not None:
            inputs += [row["name"] for row in plan["vertex_stage"]["varyings"]]

        custom = self.add(mat, "MaterialExpressionCustom", 0, 0)
        code = "\n".join(prelude) + ("\n" if prelude else "") + plan["code"]
        self.configure_custom(custom, inputs, code, "CMOT_Float4", plan["shader"])

        y = 0
        sources = self.build_affine_nodes(mat, plan["mesh_affine"]) if plan.get("mesh_affine") is not None else {}
        if plan.get("vertex_stage") is not None:
            self.build_source_vertex_nodes(mat, plan, sources, -2000)
        for n in inputs:
            if n in sources:
                node, out = sources[n]
            else:
                node, out = self.material_input_node(mat, n, plan, y)
            self.connect(node, out, custom, n)
            sources[n] = (node, out)
            y += 120

        self.build_viewport_nodes(mat, plan, sources, y)
        if (plan.get("viewport_clamp") or {}).get("facing_adapter") is not None and "NrmW" in inputs:
            self.connect(*sources["NrmW"], custom, "NrmW")

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
        self._finish_master(mat)
        self.session.save([path])
        self.masters.add(path)
        return path

    def build_viewport_nodes(self, mat, plan, sources, y):
        """颜色与双场共享同一原 VF 的几何限制；不修改模拟尺寸或中心流。"""
        viewport = plan.get("viewport_clamp")
        if viewport is not None:
            for n in viewport["inputs"]:
                if n in sources or n == "CenterView":
                    continue
                if n == "UEFX_PreviousView":
                    current = self.add(mat, "MaterialExpressionConstant", -900, y, {"R": 0.0})
                    previous = self.add(mat, "MaterialExpressionConstant", -900, y + 80, {"R": 1.0})
                    node = self.add(mat, "MaterialExpressionPreviousFrameSwitch", -600, y)
                    self.connect(current, "", node, "Current Frame")
                    self.connect(previous, "", node, "Previous Frame")
                    out = ""
                elif n in BUILTIN_NODES:
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
                                  "ProjectConfigured: sprite geometry and bounds" if viewport["mode"] == "ProjectConfigured"
                                  else "UE equivalence: projected billboard viewport size")
            for name in viewport["inputs"]:
                self.connect(*sources[name], wpo, name)
            self.m.tool(MT + "connect_to_output", expression=wpo, output_name="", material_property="MP_WorldPositionOffset")
            facing = viewport.get("facing_adapter")
            if facing is not None:
                native_normal = sources.get("NrmW")
                if native_normal is None:
                    native_normal = (self.add(mat, "MaterialExpressionVertexNormalWS", -600, y + 120), "")
                corrected = self.add(mat, "MaterialExpressionCustom", 0, y + 180)
                self.configure_custom(corrected, facing["normal_inputs"], facing["normal_code"], "CMOT_Float3",
                                      "Native baseline: Facing world normal")
                for name in facing["normal_inputs"]:
                    source = native_normal if name == "NativeNormal" else sources[name]
                    self.connect(*source, corrected, name)
                interpolator = self.add(mat, "MaterialExpressionVertexInterpolator", 300, y + 180)
                self.connect(corrected, "", interpolator, "VS")
                self.m.tool(MT + "connect_to_output", expression=interpolator, output_name="", material_property="MP_Normal")
                sources["NrmW"] = (interpolator, "")


    def build_affine_nodes(self, material, adapter):
        """同一原 VF：唯一 WPO／normal消费完整矩阵及显式项目 Euler。"""
        transport = self.add(material, "MaterialExpressionDynamicParameter", -900, -600, {"ParameterIndex": 3})
        position = self.add(material, "MaterialExpressionPreSkinnedPosition", -900, -450)
        normal = self.add(material, "MaterialExpressionPreSkinnedNormal", -900, -300)
        sources = {"FXAffineTransport": (transport, "RGBA"), "MeshPos": (position, ""), "MeshNormal": (normal, "")}
        result = {"DP3": (transport, "RGBA")}
        alignment = adapter.get("project_alignment")
        if alignment is not None:
            choice = PR.validate_mesh_alignment_transport(alignment)
            scalars = []
            for axis,(slot,component) in enumerate(alignment.get("euler_components",[[2,0],[2,1],[2,2]])):
                key = "DP"+str(slot)
                if key not in result:
                    node = self.add(material, "MaterialExpressionDynamicParameter", -1400, -750-axis*130, {"ParameterIndex":slot})
                    result[key] = (node,"RGBA")
                mask = self.add(material, "MaterialExpressionComponentMask", -1100, -750-axis*130,
                    {c:index == component for index,c in enumerate(("R","G","B","A"))})
                self.connect(*result[key],mask,"")
                scalars.append(mask)
            pair = self.add(material, "MaterialExpressionAppendVector", -850, -750)
            self.connect(scalars[0],"",pair,"A")
            self.connect(scalars[1],"",pair,"B")
            euler = self.add(material, "MaterialExpressionAppendVector", -650, -750)
            self.connect(pair,"",euler,"A")
            self.connect(scalars[2],"",euler,"B")
            sources["FXParticleEuler"] = (euler, "")
            current = self.add(material, "MaterialExpressionConstant", -1200, -900, {"R": 0.0})
            previous = self.add(material, "MaterialExpressionConstant", -1200, -1000, {"R": 1.0})
            selector = self.add(material, "MaterialExpressionPreviousFrameSwitch", -900, -900)
            self.connect(current, "", selector, "Current Frame")
            self.connect(previous, "", selector, "Previous Frame")
            sources["FXPreviousView"] = (selector, "")
            if choice["alignment"] == "Velocity":
                sources["FXVelocity"] = (self.add(material, "MaterialExpressionParticleDirection", -900, -1100), "")
        wpo = self.add(material, "MaterialExpressionCustom", -300, -600)
        self.configure_custom(wpo, adapter["wpo_inputs"], adapter["wpo_code"], "CMOT_Float3", "完整 affine 网格位置")
        for name in adapter["wpo_inputs"]:
            self.connect(*sources[name], wpo, name)
        self.m.tool(MT + "connect_to_output", expression=wpo, output_name="", material_property="MP_WorldPositionOffset")
        corrected_normal = self.add(material, "MaterialExpressionCustom", -300, -300)
        self.configure_custom(corrected_normal, adapter["normal_inputs"], adapter["normal_code"], "CMOT_Float3", "完整 affine 逆转置／退化面积法线")
        for name in adapter["normal_inputs"]:
            self.connect(*sources[name], corrected_normal, name)
        interpolator = self.add(material, "MaterialExpressionVertexInterpolator", 0, -300)
        self.connect(corrected_normal, "", interpolator, "VS")
        self.m.tool(MT + "connect_to_output", expression=interpolator, output_name="", material_property="MP_Normal")
        raw = self.add(material, "MaterialExpressionWorldPosition", -900, -1200,
                       {"WorldPositionShaderOffset": "WPT_ExcludeAllShaderOffsets"})
        world = self.add(material, "MaterialExpressionAdd", -300, -1200)
        self.connect(raw, "", world, "A")
        self.connect(wpo, "", world, "B")
        return {**result, "NrmW": (interpolator, ""), "SourceVertexNrmW": (corrected_normal, ""),
                "SourceVertexWorldPos": (world, ""), "RawWorldPos": (raw, "")}

    def build_field_master(self, plan):
        """同一原材质输出源 o0/o1；颜色与场资产生产入口明确分开。"""
        path = MASTER_DIR + "/" + plan["master"]
        if path in self.masters:
            return path
        # 先核真实加载类的双 pin ABI；旧单场或未加载模块不能先创建半成品冒就绪。
        self.require_dual_field_class(self.m, unreal=self.native)
        self.session.begin_create(path)
        material = self.m.tool(MT + "create_material", folder_path=MASTER_DIR, asset_name=plan["master"])["returnValue"]
        self.session.created_asset(path)
        properties = {"BlendMode": "BLEND_Translucent", "ShadingModel": "MSM_Unlit", "TwoSided": plan["two_sided"],
            "bDisableDepthTest": plan["disable_depth_test"], "bEnableNewHLSLGenerator": False,
            "bUsedWithNiagaraMeshParticles": plan["mesh"] and (
                plan["renderer_kind"] == "particle" or plan.get("component_age_binding") is not None),
            "bUsedWithNiagaraSprites": plan["renderer_kind"] == "particle" and not plan["mesh"],
            "bAutomaticallySetUsageInEditor": False, "RefractionMethod": "RM_IndexOfRefraction"}
        if plan.get("mesh_affine") is not None:
            properties.update(bTangentSpaceNormal=False, MaxWorldPositionOffsetDisplacement=0.0)
        if plan.get("viewport_clamp") is not None:
            properties.update(MaxWorldPositionOffsetDisplacement=0.0)
        self.set(material, properties)
        sources = self.build_affine_nodes(material, plan["mesh_affine"]) if plan.get("mesh_affine") is not None else {}
        field_outputs = {}
        y = 0
        for pin, field in plan["fields"].items():
            inputs, prelude = [], []
            for name in field["builtins"]:
                if name == "VCol":
                    inputs += ["VCol_rgb", "VCol_a"]
                    prelude.append("float4 VCol=float4(VCol_rgb,VCol_a);")
                else:
                    inputs.append(name)
            inputs += list(field.get("pixel_params", field["params"])) + list(field["textures"])
            custom = self.add(material, "MaterialExpressionCustom", 300, y)
            self.configure_custom(custom, inputs, "\n".join(prelude + [field["code"]]), "CMOT_Float4", pin + "完整源 RGBA")
            for name in inputs:
                if name not in sources:
                    if name in BUILTIN_NODES:
                        klass, props, output = BUILTIN_NODES[name]
                        node = self.add(material, klass, -600, y, props)
                    elif name in field["params"]:
                        parameter = field["params"][name]
                        if parameter["dim"] == 1:
                            node = self.add(material, "MaterialExpressionScalarParameter", -600, y,
                                {"ParameterName": name, "DefaultValue": float(parameter["value"])})
                            output = ""
                        else:
                            node = self.add(material, "MaterialExpressionVectorParameter", -600, y, {"ParameterName": name})
                            self.set(node, {"DefaultValue": linear_color(parameter["value"])})
                            output = "RGBA"
                    else:
                        texture = field["textures"][name]
                        node = self.add(material, "MaterialExpressionTextureObjectParameter", -600, y, {"ParameterName": name})
                        self.set(node, {"Texture": ref(texture), "SamplerType": self.sampler_type(texture)})
                        output = ""
                    sources[name] = (node, output)
                    y += 120
                self.connect(*sources[name], custom, name)
            field_outputs[pin] = custom
        self.build_viewport_nodes(material, plan, sources, y)
        zero = self.add(material, "MaterialExpressionConstant", 500, y, {"R": 0.0})
        one = self.add(material, "MaterialExpressionConstant", 500, y + 120, {"R": 1.0})
        # CustomOutput会参与每次属性通知的材质编译；完整建图后才创建并接齐两场，
        # 避免后续数组/结构字段通知反复编译缺失输入的临时sink。
        sink = self.add(material, "/Script/GGYGORendering.GGYGOMaterialExpressionDistortionField", 800, 0)
        for pin, custom in field_outputs.items():
            self.connect(custom, "", sink, pin)
        # 两输出与renderer共享同一来源掩码，设置时两场均已接齐。
        self.set(sink, {"bStreamContractConfigured": True,
                        "RequiredDynamicParameterComponents": plan["dynamic_parameter_components"]})
        for property_name, expression in (("MP_EmissiveColor", zero), ("MP_Opacity", zero), ("MP_Refraction", one)):
            self.m.tool(MT + "connect_to_output", expression=expression, output_name="", material_property=property_name)
        self._finish_master(material)
        self.session.save([path])
        self.masters.add(path)
        return path

    def _set_instance_parameter(self, instance, kind, name, value):
        """每参数沿原资源门写一次；核本实例 typed override 及实际有效值。"""
        library = self.native.MaterialEditingLibrary

        def apply():
            names = getattr(library, "get_" + kind + "_parameter_names")(instance)
            if name not in {str(item) for item in names}:
                raise ValueError("本实例不存在准确类型的参数：%s.%s (%s)" % (
                    instance.get_path_name(), name, kind))
            expected = value
            if kind == "vector":
                expected = self.native.LinearColor(*(value[key] for key in "rgba"))
            elif kind == "texture":
                path = ref(value)["refPath"]
                expected = self.native.load_object(None, path)
                if not isinstance(expected, self.native.Texture) or expected.get_path_name() != path:
                    raise ValueError("实例参数纹理不是准确原资产：" + path)
            # 原公开三类 setter 内部已 UpdateMaterialInstance，当前实现仍固定返回 false。
            # 沿其实际写入语义调用；成功依据是本实例 override 和准确值，不能用继承值替代。
            getattr(library, "set_material_instance_" + kind + "_parameter_value")(instance, name, expected)
            overrides = []
            for item in instance.get_editor_property(kind + "_parameter_values"):
                info = item.get_editor_property("parameter_info")
                if (str(info.get_editor_property("name")) == name
                        and info.get_editor_property("association") == self.native.MaterialParameterAssociation.GLOBAL_PARAMETER
                        and info.get_editor_property("index") == -1):
                    overrides.append(item.get_editor_property("parameter_value"))
            actual = getattr(library, "get_material_instance_" + kind + "_parameter_value")(instance, name)
            if (len(overrides) != 1
                    or not _native_value_equal(self.native, name, overrides[0], expected, _u_float_equal)
                    or not _native_value_equal(self.native, name, actual, expected, _u_float_equal)):
                raise RuntimeError("实例参数没有准确的本地 override／有效值：%s.%s (%s)" % (
                    instance.get_path_name(), name, kind))
            library.refresh_material_instance_editor(instance)

        self.native_sync("material_instance_parameter:" + instance.get_path_name() + ":" + name, apply)

    def build_instance(self, plan, master, name):
        path = "%s/%s" % (MI_DIR, name)
        if path in self.session.created:
            return path
        self.session.begin_create(path)
        self.m.tool(MI + "create", folder_path=MI_DIR, asset_name=name, parent=ref(master))
        self.session.created_asset(path)
        mi = ref(path)
        parent = json.loads(self.m.tool(OB + "get_properties", instance=mi, properties=["Parent"])["returnValue"])
        self._verify_value({"Parent": ref(master)}, parent, mi["refPath"])
        instance = self.native.load_object(None, mi["refPath"])
        if not isinstance(instance, self.native.MaterialInstanceConstant) or instance.get_path_name() != mi["refPath"]:
            raise RuntimeError("参数写入目标不是本批创建的准确 MaterialInstanceConstant：" + mi["refPath"])
        for n, p in plan["params"].items():
            if p["dim"] == 1:
                self._set_instance_parameter(instance, "scalar", n, float(p["value"]))
            else:
                self._set_instance_parameter(instance, "vector", n, linear_color(p["value"]))
        for n, tex in plan["textures"].items():
            self._set_instance_parameter(instance, "texture", n, tex)
            texture = self.m.tool(MI + "get_texture_parameter", instance=mi, name=n)["returnValue"]
            self._verify_value(ref(tex), texture, mi["refPath"] + ".TextureParameters." + n)
        parent = json.loads(self.m.tool(OB + "get_properties", instance=mi, properties=["Parent"])["returnValue"])
        self._verify_value({"Parent": ref(master)}, parent, mi["refPath"])
        self.session.save([path])
        return path
