"""@file build_nap_avatar_simple_materials.py
@brief 构建首个 Ghost 的 UE 对应材质；仅显式 session/native 宿主可执行。

不启动编辑器、不自动连接、不保存包。FX 统一管理导入、资源实例与保存。
失败保留本批新脏包供诊断，禁止清空旧资产或使用缺失依赖替代成功。
"""
import math
import re

from nap_avatar_simple_material_plan import validate_plan
from zzz_fx_material_ue import ref


class NapAvatarSimpleBuilder:
    """@param session FX 分配的 create-only AssetSession。
    只读 verify 可传 None；build 必须有本批 session。
    @param unreal 与 session 同一标准 Editor 的显式原生宿主。
    材质编译与有效参数读回在本调用完成；保存权仍归 FX 批次协调者。
    """
    validate_plan = staticmethod(validate_plan)

    def __init__(self, session, *, unreal=None):
        self.session = session
        self.native = unreal

    def build(self, plan):
        self.validate_plan(plan)
        self._require_native()
        if self.session is None:
            raise ValueError("Ghost 材质构建需要本批 create-only session")
        if not set(plan["targets"]).issubset(self.session.targets):
            raise ValueError("材质/纹理目标不在本 session 的整批批准清单内")
        # 全部依赖完成读回后才开始创建，避免先写 surface 再发现 outline 缺资源。
        for item in plan["textures"].values():
            self.session.require_created(item["path"])
        self._verify_textures(plan)
        for spec in plan["materials"]:
            self._build_master(spec)
            self._build_instance(spec)
        return plan["bindings"]

    def verify(self, plan):
        """只读已加载资产的类型、配置、编译统计及有效材质绑定。

        不要求 create-only session，不创建、修改、编译或保存资产。
        调用者证明冷宿主和已保存包 hash；本入口不认证图字节、GPU draw 或画面。
        """
        self.validate_plan(plan)
        self._require_native()
        self._verify_textures(plan)
        statistics = {}
        for spec in plan["materials"]:
            statistics[spec["role"]] = self._verify_master(spec)
            self._verify_instance(spec)
        return {"material_binding_readback_verified": True, "bindings": plan["bindings"],
                "targets": plan["targets"], "compiled_statistics": statistics,
                "cold_host_verified": False, "material_graph_bytes_verified": False,
                "gpu_draw_verified": False, "visual_verified": False}

    def _require_native(self):
        if self.native is None:
            raise ValueError("Ghost 材质入口需要显式同一标准 Editor 的 unreal 宿主")

    def _check_properties(self, obj, properties):
        for key, value in properties.items():
            actual = obj.get_editor_property(self._property_name(key))
            if not self._same_value(actual, value) and self._enum_name(actual) != self._enum_name(value):
                raise RuntimeError("实际资源设置不一致: " + obj.get_path_name() + "." + key)

    def _verify_textures(self, plan):
        for item in plan["textures"].values():
            tex = self.native.load_asset(item["path"])
            if not isinstance(tex, self.native.Texture2D) or tex.get_path_name() != ref(item["path"])["refPath"]:
                raise RuntimeError("必需纹理类型或路径不一致: " + item["path"])
            self._check_properties(tex, item["properties"])

    @staticmethod
    def _property_name(name):
        if name.startswith("b") and name[1:2].isupper():
            name = name[1:]
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    @staticmethod
    def _enum_name(value):
        text = str(value)
        match = re.search(r"\.([A-Za-z0-9_]+)", text)
        return (match.group(1) if match else text).replace("_", "").casefold()

    @staticmethod
    def _same_value(actual, expected):
        if isinstance(expected, float):
            return math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6)
        if all(hasattr(expected, k) for k in "rgba"):
            return all(math.isclose(getattr(actual, k), getattr(expected, k), rel_tol=1e-6, abs_tol=1e-6) for k in "rgba")
        return actual == expected

    def _enum(self, enum_class, name):
        return getattr(getattr(self.native, enum_class), self._property_name(name).upper())

    def set(self, obj, props):
        enums = {"BlendMode": "BlendMode", "ShadingModel": "MaterialShadingModel",
                 "TransformSourceType": "MaterialVectorCoordTransformSource", "TransformType": "MaterialVectorCoordTransform",
                 "SamplerType": "MaterialSamplerType"}
        for key, value in props.items():
            if key in enums:
                value = self._enum(enums[key], value)
            elif key == "Texture":
                value = self.native.load_asset(value)
            elif key == "DefaultValue" and isinstance(value, dict):
                value = self.native.LinearColor(value["r"], value["g"], value["b"], value["a"])
            name = self._property_name(key)
            obj.set_editor_property(name, value)
            if not self._same_value(obj.get_editor_property(name), value):
                raise RuntimeError("材质属性原生读回不一致: " + obj.get_path_name() + "." + key)

    def add(self, mat, klass, x, y, props=None):
        node = self.native.MaterialEditingLibrary.create_material_expression(mat, getattr(self.native, klass), x, y)
        if node is None:
            raise RuntimeError("材质表达式创建失败: " + klass)
        if props:
            self.set(node, props)
        return node

    def connect(self, src, out_name, dst, in_name):
        if not in_name:
            names = self.native.MaterialEditingLibrary.get_material_expression_input_names(dst)
            if len(names) == 1:
                in_name = str(names[0])
        if not self.native.MaterialEditingLibrary.connect_material_expressions(src, out_name, dst, in_name):
            raise RuntimeError("材质表达式连接失败: " + dst.get_path_name() + "." + in_name)

    def configure_custom(self, node, inputs, code, output_type, description):
        entries = []
        for name in inputs:
            item = self.native.CustomInput()
            item.set_editor_property("input_name", name)
            entries.append(item)
        node.set_editor_property("inputs", entries)
        node.set_editor_property("code", code)
        node.set_editor_property("output_type", self._enum("CustomMaterialOutputType", output_type))
        node.set_editor_property("description", description)
        if [str(x.get_editor_property("input_name")) for x in node.get_editor_property("inputs")] != inputs or node.get_editor_property("code") != code:
            raise RuntimeError("Custom 表达式原生读回不一致")

    def sampler_type(self, path):
        tex = self.native.load_asset(path)
        return "SAMPLERTYPE_Color" if tex.get_editor_property("srgb") else "SAMPLERTYPE_LinearColor"

    def _create(self, path, asset_class, factory_class):
        self.session.begin_create(path)
        directory, name = path.rsplit("/", 1)
        obj = self.native.AssetToolsHelpers.get_asset_tools().create_asset(
            name, directory, getattr(self.native, asset_class), getattr(self.native, factory_class)())
        if not isinstance(obj, getattr(self.native, asset_class)) or obj.get_path_name() != ref(path)["refPath"]:
            raise RuntimeError("新材质资源身份不一致: " + path)
        self.session.created_asset(path)
        return obj

    def _output(self, expression, output_name, prop):
        if not self.native.MaterialEditingLibrary.connect_material_property(expression, output_name, self._enum("MaterialProperty", prop)):
            raise RuntimeError("材质输出连接失败: " + prop)

    def _custom(self, mat, inputs, code, output_type, sources, y):
        node = self.add(mat, "MaterialExpressionCustom", 0, y)
        self.configure_custom(node, inputs, code, output_type, "NapAvatarSimple：已审计算法与明确 UE 对应")
        for name in inputs:
            self.connect(*sources[name], node, name)
        return node

    def _build_master(self, spec):
        mat = self._create(spec["master"], "Material", "MaterialFactoryNew")
        self.set(mat, spec["properties"])
        sources = {}
        for i, (n, p) in enumerate(spec["params"].items()):
            klass = "MaterialExpressionScalarParameter" if p["dim"] == 1 else "MaterialExpressionVectorParameter"
            props = {"ParameterName": n, "DefaultValue": p["value"] if p["dim"] == 1 else dict(zip("rgba", p["value"]))}
            e = self.add(mat, klass, -700, i * 100, props)
            sources[n] = (e, "" if p["dim"] == 1 else "RGBA")
        for i, (n, path) in enumerate(spec["textures"].items()):
            e = self.add(mat, "MaterialExpressionTextureObjectParameter", -1000, i * 150,
                         {"ParameterName": n, "Texture": ref(path)["refPath"], "SamplerType": self.sampler_type(path)})
            sources[n] = (e, "")
        screen = self.add(mat, "MaterialExpressionScreenPosition", -1000, 700)
        sources["PixelPosition"] = (screen, "PixelPosition")
        for n, klass, props in (("UV0", "MaterialExpressionTextureCoordinate", {"CoordinateIndex": 0}),
                                ("UV2", "MaterialExpressionTextureCoordinate", {"CoordinateIndex": 2}),
                                ("Time", "MaterialExpressionTime", {}),
                                ("VertexNormalWS", "MaterialExpressionVertexNormalWS", {}),
                                ("FaceSign", "MaterialExpressionTwoSidedSign", {})):
            sources[n] = (self.add(mat, klass, -1000, 900 + len(sources) * 90, props), "")
        pixel_normal = self.add(mat, "MaterialExpressionPixelNormalWS", -1000, 600)
        normal_view = self.add(mat, "MaterialExpressionTransform", -700, 600,
                               {"TransformSourceType": "TRANSFORMSOURCE_World", "TransformType": "TRANSFORM_View"})
        self.connect(pixel_normal, "", normal_view, "")
        sources["NormalView"] = (normal_view, "")
        coverage = self._custom(mat, ["PixelPosition", "_DitherAlpha", "_DitherAlpha2", "_DitherEffectAlpha"],
                                spec["shader"]["coverage"], "CMOT_Float1", sources, 0)
        if spec["role"] == "outline":
            sources["Coverage"] = (coverage, "")
            coverage = self._custom(mat, ["Coverage", "FaceSign"], "return Coverage * ((FaceSign < 0.0) ? 1.0 : 0.0);",
                                    "CMOT_Float1", sources, 120)
        self._output(coverage, "", "MP_OpacityMask")
        if spec["role"] == "surface":
            inputs = ["NormalView", "UV2", "Time", "_Color", "_ScreenColor", "_ScreenImage", "_ScreenImageUvMove",
                      "_ScreenTex", "_ScreenTex_ST", "_ScreenMask", "_ScreenMask_ST"]
        else:
            inputs = ["UV0", "UV2", "Time", "_Color", "_OutlineColor", "_OverrideOutline", "_OverrideOutlineUseUV2",
                      "_OverrideOutlineColor", "_OverrideOutlineSpeed", "_OverrideOutlineTex", "_OverrideOutlineTex_ST"]
        color = self._custom(mat, inputs, spec["shader"]["color"], "CMOT_Float3", sources, 350)
        sources["SourceRGB"] = (color, "")
        scale = "UE_SurfaceEmissionScale" if spec["role"] == "surface" else "UE_OutlineEmissionScale"
        emission = self._custom(mat, ["SourceRGB", scale], "return SourceRGB * " + scale + ";", "CMOT_Float3", sources, 650)
        self._output(emission, "", "MP_EmissiveColor")
        if spec["role"] == "surface":
            albedo = self._custom(mat, ["SourceRGB", "_ScreenColor", "UE_SurfaceLitScale"],
                "float peak = max(max(_ScreenColor.r,_ScreenColor.g),max(_ScreenColor.b,0.000001));\nreturn saturate(SourceRGB / peak) * UE_SurfaceLitScale;",
                "CMOT_Float3", sources, 800)
            self._output(albedo, "", "MP_BaseColor")
            self._output(*sources["_Metallic"], "MP_Metallic")
            self._output(*sources["_SpecIntensity"], "MP_Specular")
            rough = self._custom(mat, ["_Glossiness"], "return saturate(1.0 - _Glossiness);", "CMOT_Float1", sources, 950)
            self._output(rough, "", "MP_Roughness")
        else:
            wpo = self._custom(mat, ["VertexNormalWS", "_Outline", "_OutlineWidth", "UE_OutlineWidthCm"],
                               spec["shader"]["wpo"], "CMOT_Float3", sources, 950)
            self._output(wpo, "", "MP_WorldPositionOffset")
        actual = self.native.load_asset(spec["master"])
        errors = self.native.MaterialEditingLibrary.recompile_material(actual)
        if errors is None or errors:
            raise RuntimeError("Ghost 材质编译失败或没有诊断: " + spec["master"] + " " + repr(errors))
        self._verify_master(spec)

    def _verify_master(self, spec):
        actual = self.native.load_asset(spec["master"])
        if not isinstance(actual, self.native.Material) or actual.get_path_name() != ref(spec["master"])["refPath"]:
            raise RuntimeError("Ghost master 类型或路径不一致: " + spec["master"])
        self._check_properties(actual, spec["properties"])
        stats = self.native.MaterialEditingLibrary.get_statistics(actual)
        if stats.num_pixel_shader_instructions <= 0 or stats.num_vertex_shader_instructions <= 0:
            raise RuntimeError("Ghost 材质尚未取得有效编译统计: " + spec["master"])
        # 有效值查询对不存在的 scalar 返回 0，必须先证明参数存在。
        mel = self.native.MaterialEditingLibrary
        scalar_names = {str(n) for n in mel.get_scalar_parameter_names(actual)}
        vector_names = {str(n) for n in mel.get_vector_parameter_names(actual)}
        texture_names = {str(n) for n in mel.get_texture_parameter_names(actual)}
        for name, parameter in spec["params"].items():
            if name not in (scalar_names if parameter["dim"] == 1 else vector_names):
                raise RuntimeError("Ghost master 未注册必需参数: " + spec["master"] + "." + name)
        if set(spec["textures"]) - texture_names:
            raise RuntimeError("Ghost master 未注册必需纹理参数: " + spec["master"])
        return {"pixel_shader_instructions": stats.num_pixel_shader_instructions,
                "vertex_shader_instructions": stats.num_vertex_shader_instructions}

    def _build_instance(self, spec):
        path = spec["instance"]
        mi = self._create(path, "MaterialInstanceConstant", "MaterialInstanceConstantFactoryNew")
        mel = self.native.MaterialEditingLibrary
        mel.set_material_instance_parent(mi, self.native.load_asset(spec["master"]))
        # UE 5.8 MaterialEditingLibrary.cpp 的这三个 setter 实际执行更新，
        # 但未置 bResult，始终返回 false；以原生存在性与有效参数读回认证。
        for n, p in spec["params"].items():
            if p["dim"] == 1:
                mel.set_material_instance_scalar_parameter_value(mi, n, p["value"])
            else:
                mel.set_material_instance_vector_parameter_value(mi, n, self.native.LinearColor(*p["value"]))
        for n, tex in spec["textures"].items():
            mel.set_material_instance_texture_parameter_value(mi, n, self.native.load_asset(tex))
        self._verify_instance(spec)

    def _verify_instance(self, spec):
        path = spec["instance"]
        mi = self.native.load_asset(path)
        if not isinstance(mi, self.native.MaterialInstanceConstant) or mi.get_path_name() != ref(path)["refPath"]:
            raise RuntimeError("Ghost MIC 类型或路径不一致: " + path)
        mel = self.native.MaterialEditingLibrary
        parent = mi.get_editor_property("parent")
        if parent is None or parent.get_path_name() != ref(spec["master"])["refPath"]:
            raise RuntimeError("Ghost MIC 类型或 Parent 不一致: " + path)
        for n, p in spec["params"].items():
            actual = mel.get_material_instance_scalar_parameter_value(mi, n) if p["dim"] == 1 else mel.get_material_instance_vector_parameter_value(mi, n)
            values = [actual] if p["dim"] == 1 else [getattr(actual, k) for k in "rgba"]
            expected = [p["value"]] if p["dim"] == 1 else p["value"]
            if any(not math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-5) for a, b in zip(values, expected)):
                raise RuntimeError("Ghost MIC 有效参数不一致: " + path + "." + n)
        for n, tex in spec["textures"].items():
            actual = mel.get_material_instance_texture_parameter_value(mi, n)
            if actual is None or actual.get_path_name() != ref(tex)["refPath"]:
                raise RuntimeError("Ghost MIC 有效纹理不一致: " + path + "." + n)
