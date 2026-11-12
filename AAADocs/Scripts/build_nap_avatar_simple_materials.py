"""@file build_nap_avatar_simple_materials.py
@brief 构建两个准确Simple MID的源程序与UE配置材质；仅显式 session/native 宿主可执行。

不启动编辑器、不自动连接、不保存包。FX 统一管理导入、资源实例与保存。
失败保留本批新脏包供诊断，禁止清空旧资产或使用缺失依赖替代成功。
"""
import math
import re

from nap_avatar_simple_material_plan import validate_plan
from zzz_fx_material_ue import configure_native_custom, ref, set_native_properties


class NapAvatarSimpleBuilder:
    """@param session FX 分配的 create-only AssetSession。
    只读 verify 可传 None；build 必须有本批 session。
    @param unreal 与 session 同一标准 Editor 的显式原生宿主。
    @param verified_readonly_dependencies FX 本次完整验证后的只读依赖路径；仅本实例使用，不授予写权。
    未传入时保留原 require_created 规则，不从资产存在性推导复用权限。
    材质编译与有效参数读回在本调用完成；保存权仍归 FX 批次协调者。
    """
    validate_plan = staticmethod(validate_plan)

    def __init__(self, session, *, unreal=None, verified_readonly_dependencies=None):
        self.session = session
        self.native = unreal
        self.verified_readonly_dependencies = frozenset(() if verified_readonly_dependencies is None else verified_readonly_dependencies)

    def build(self, plan):
        self.validate_plan(plan)
        self._require_native()
        self._require_build_targets(plan)
        # 全部依赖完成读回后才开始创建，避免先写 surface 再发现 outline 缺资源。
        self._verify_textures(plan)
        for spec in plan["materials"]:
            self._build_master(spec)
            self._build_instance(spec)
        return plan["bindings"]

    def _require_build_targets(self, plan):
        """原 Session 独占写权；已核只读纹理仅作为当前计划依赖，不能进入 created 集合。"""
        if self.session is None:
            raise ValueError("材质构建需要本批 create-only Session")
        if not callable(getattr(getattr(self.session, "m", None), "run_native_sync", None)):
            raise ValueError("材质构建需要原Controller的run_native_sync写入入口")
        writable = {path for spec in plan["materials"] for path in (spec["master"], spec["instance"])}
        dependencies = {item["path"] for item in plan["textures"].values()}
        if set(plan["targets"]) != writable | dependencies or writable & dependencies:
            raise ValueError("材质计划 targets 未准确闭合为独立材质写目标与纹理依赖")
        if not writable.issubset(self.session.targets):
            raise ValueError("材质写目标超出原 Session 批准范围：" + repr(sorted(writable - self.session.targets)))
        conflict = self.verified_readonly_dependencies & self.session.targets
        if conflict:
            raise ValueError("已核只读依赖不得进入本批写域：" + repr(sorted(conflict)))
        for path in sorted(dependencies):
            if path not in self.verified_readonly_dependencies:
                self.session.require_created(path)

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
        if obj.get_path_name().split(".", 1)[0] in self.verified_readonly_dependencies:
            raise ValueError("不得设置已核只读依赖的属性：" + obj.get_path_name())
        return set_native_properties(self.native, obj, props, native_sync=self.session.m.run_native_sync)

    def add(self, mat, klass, x, y, props=None):
        node = self.native.MaterialEditingLibrary.create_material_expression(mat, getattr(self.native, klass), x, y)
        if node is None:
            raise RuntimeError("材质表达式创建失败: " + klass)
        if props:
            self.set(node, props)
        return node

    def connect(self, src, out_name, dst, in_name):
        requested_input = in_name
        # GetOutputs 同时取得 DynamicParameter 的当前 ParamNames；连接 API 自身仅查询 Outputs。
        outputs = list(self.native.MaterialEditingLibrary.get_material_expression_output_names(src))
        inputs = list(self.native.MaterialEditingLibrary.get_material_expression_input_names(dst))
        if not in_name and len(inputs) == 1:
            in_name = str(inputs[0])
        pins_valid = bool(outputs) and bool(inputs) and (not out_name or out_name in outputs) \
            and (not in_name or in_name in inputs)
        if not pins_valid or not self.native.MaterialEditingLibrary.connect_material_expressions(src, out_name, dst, in_name):
            raise RuntimeError("材质表达式连接失败：source=%s class=%s output=%r available_outputs=%r "
                               "-> target=%s class=%s requested_input=%r resolved_input=%r available_inputs=%r pins_valid=%r" % (
                                   src.get_path_name(), src.get_class().get_path_name(), out_name, outputs,
                                   dst.get_path_name(), dst.get_class().get_path_name(), requested_input, in_name, inputs, pins_valid))

    def configure_custom(self, node, inputs, code, output_type, description, *, additional_outputs=None):
        if node.get_path_name().split(".", 1)[0] in self.verified_readonly_dependencies:
            raise ValueError("不得设置已核只读依赖的属性：" + node.get_path_name())
        return configure_native_custom(self.native, node, inputs, code, output_type, description,
                                       native_sync=self.session.m.run_native_sync,
                                       additional_outputs=additional_outputs)

    def sampler_type(self, path):
        tex = self.native.load_asset(path)
        return "SAMPLERTYPE_Color" if tex.get_editor_property("srgb") else "SAMPLERTYPE_LinearColor"

    def _create(self, path, asset_class, factory_class):
        if path in self.verified_readonly_dependencies:
            raise ValueError("不得创建或覆盖已核只读依赖：" + path)
        self.session.begin_create(path)
        directory, name = path.rsplit("/", 1)
        obj = self.native.AssetToolsHelpers.get_asset_tools().create_asset(
            name, directory, getattr(self.native, asset_class), getattr(self.native, factory_class)())
        if not isinstance(obj, getattr(self.native, asset_class)) or obj.get_path_name() != ref(path)["refPath"]:
            raise RuntimeError("新材质资源身份不一致: " + path)
        self.session.created_asset(path)
        return obj

    def _output(self, expression, output_name, prop):
        outputs = list(self.native.MaterialEditingLibrary.get_material_expression_output_names(expression))
        pin_valid = bool(outputs) and (not output_name or output_name in outputs)
        if not pin_valid or not self.native.MaterialEditingLibrary.connect_material_property(expression, output_name, self._enum("MaterialProperty", prop)):
            raise RuntimeError("材质输出连接失败：source=%s class=%s output=%r available_outputs=%r property=%s pin_valid=%r" % (
                expression.get_path_name(), expression.get_class().get_path_name(), output_name, outputs, prop, pin_valid))

    def _custom(self, mat, inputs, code, output_type, sources, y, *, additional_outputs=None):
        node = self.add(mat, "MaterialExpressionCustom", 0, y)
        self.configure_custom(node, inputs, code, output_type, "NapAvatarSimple：已审计算法与明确 UE 对应",
                              additional_outputs=additional_outputs)
        for name in inputs:
            self.connect(*sources[name], node, name)
        return node

    def _build_master(self, spec):
        from gen_nap_avatar_hlsl import ADDITIONAL_LIGHT_CODE
        from pyrios_material_plan import ADDITIONAL_SCALARS, ADDITIONAL_VECTORS
        mat = self._create(spec["master"], "Material", "MaterialFactoryNew")
        self.set(mat, spec["properties"])
        sources = {}
        for index, (name, parameter) in enumerate(spec["params"].items()):
            scalar = parameter["dim"] == 1
            node = self.add(mat, "MaterialExpressionScalarParameter" if scalar else "MaterialExpressionVectorParameter",
                            -1400, index * 80,
                            {"ParameterName": name, "DefaultValue": parameter["value"] if scalar
                             else dict(zip("rgba", parameter["value"]))})
            sources[name] = (node, "" if scalar else "RGBA")
        for index, (name, path) in enumerate(spec["textures"].items()):
            node = self.add(mat, "MaterialExpressionTextureObjectParameter", -1100, index * 110,
                            {"ParameterName": name, "Texture": path, "SamplerType": self.sampler_type(path)})
            sources[name] = (node, "")
        builtins = (("WorldPos", "MaterialExpressionWorldPosition", {}),
                    ("CameraPos", "MaterialExpressionCameraPositionWS", {}),
                    ("VCol", "MaterialExpressionVertexColor", {}),
                    ("FaceSign", "MaterialExpressionTwoSidedSign", {}),
                    ("VertexNormalWS", "MaterialExpressionVertexNormalWS", {}),
                    ("UV0", "MaterialExpressionTextureCoordinate", {"CoordinateIndex": 0}),
                    ("UV2", "MaterialExpressionTextureCoordinate", {"CoordinateIndex": 2}),
                    ("UV3", "MaterialExpressionTextureCoordinate", {"CoordinateIndex": 3}))
        for index, (name, klass, props) in enumerate(builtins):
            source = self.add(mat, klass, -2000, index * 100, props)
            if name == "VCol":
                # VertexColor 的 RGB 首输出未命名；空名取该 RGB，再与实际 A 拼 float4，保 PartID/alpha。
                rgba = self.add(mat, "MaterialExpressionAppendVector", -1700, index * 100)
                self.connect(source, "", rgba, "A")
                self.connect(source, "A", rgba, "B")
                source = rgba
            sources[name] = (source, "")
        screen = self.add(mat, "MaterialExpressionScreenPosition", -2000, 950)
        sources["PixelPosition"] = (screen, "PixelPosition")
        age = self.add(mat, "MaterialExpressionDynamicParameter", -2000, 1100,
                       {"ParameterIndex": 0, "DefaultValue": dict(r=0.0, g=0.0, b=0.0, a=0.0)})
        sources["EffectAge"] = (age, "")  # 原生第0输出为DP0.x；Emitter Update写System.Age。
        additional_names = ["WorldPos", *ADDITIONAL_VECTORS, *ADDITIONAL_SCALARS]
        additional = self._custom(mat, additional_names, ADDITIONAL_LIGHT_CODE,
                                  "CMOT_Float3", sources, -500)
        interpolator = self.add(mat, "MaterialExpressionVertexInterpolator", -700, -500)
        self.connect(additional, "", interpolator, "")
        sources["VertexAdditionalLight"] = (interpolator, "")
        part = self._custom(mat, ["VCol", "_PartIDOffset", "_ShowPartIDs"],
                            spec["part_code"], "CMOT_Float1", sources, -300)
        interpolator = self.add(mat, "MaterialExpressionVertexInterpolator", -700, -300)
        self.connect(part, "", interpolator, "")
        sources["VertexPartVisibility"] = (interpolator, "")
        style = self._custom(mat, ["VCol"], spec["style_code"], "CMOT_Float2", sources, -100)
        interpolator = self.add(mat, "MaterialExpressionVertexInterpolator", -700, -100)
        self.connect(style, "", interpolator, "")
        sources["VertexStyle"] = (interpolator, "")
        program = spec["shader"]
        names = list(dict.fromkeys([*program["material_params"], *program["parameters"],
                                    *program["textures"], *program["builtins"]]))
        outputs = [(name, "CMOT_Float3" if name == "RimRaw" else "CMOT_Float1") for name in program["outputs"]]
        main = self._custom(mat, names, program["code"], "CMOT_Float3", sources, 0, additional_outputs=outputs)
        if [str(x.get_editor_property("output_name")) for x in main.get_editor_property("additional_outputs")] != program["outputs"]:
            raise RuntimeError("Simple Custom输出原生读回不同")
        sources["CoverageOut"] = (main, "CoverageOut")
        sources["BaseRGB"] = (main, "")
        face = {"both": "1.0", "front": "(FaceSign>0.0?1.0:0.0)", "back": "(FaceSign<0.0?1.0:0.0)"}[spec["face_mask"]]
        mask = self._custom(mat, ["CoverageOut", "FaceSign"],
                            "return CoverageOut * " + face + ";", "CMOT_Float1", sources, 320)
        self._output(mask, "", "MP_OpacityMask")
        if spec["role"] == "surface":
            sources["RimRaw"] = (main, "RimRaw")
            emission = self._custom(mat, ["BaseRGB", "RimRaw", "UE_RimGain", "UE_RimMaxIntensity", "UE_OutputScale"],
                                    spec["display"], "CMOT_Float3", sources, 600)
        else:
            emission = self._custom(mat, ["BaseRGB", "UE_OutputScale"], "return BaseRGB*UE_OutputScale;",
                                    "CMOT_Float3", sources, 600)
            wpo = self._custom(mat, ["VertexNormalWS", "_Outline", "_OutlineWidth",
                                    "UE_OutlineWidthCm", "UE_OutlineMaxOffsetCm"],
                               spec["wpo"], "CMOT_Float3", sources, 900)
            self._output(wpo, "", "MP_WorldPositionOffset")
        inverse = self.add(mat, "MaterialExpressionEyeAdaptationInverse", 700, 600)
        self.connect(emission, "", inverse, "LightValueInput")
        self.connect(*sources["ExposureCompensationWeight"], inverse, "AlphaInput")
        self._output(inverse, "", "MP_EmissiveColor")
        errors = self.native.MaterialEditingLibrary.recompile_material(mat)
        if errors is None or errors:
            raise RuntimeError("Simple材质编译失败或没有诊断：" + spec["master"] + " " + repr(errors))
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
