"""Offline failure-path tests; no Unreal process or project asset writes.

夹具复制项目里的三份 Pyrios 材质 JSON 与全局参数文件到临时目录再修改，源文件只读。
"""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
PROJECT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
from pyrios_material_plan import (BuildJournal, EXPOSURE_PARAMETER, PREVIEW_LIGHT,
                                 PREVIEW_SCALARS, SLOT_INSTANCES, SUFFIXES,
                                 exposure_weight, load_plan, unity_gamma_to_linear)
import gen_nap_avatar_hlsl as toon_generator

SOURCE_JSON = PROJECT / "AAADocs/Assets/Pyrios/Rendering/UnityMaterials"
SOURCE_GLOBALS = PROJECT / "AAADocs/Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json"


def module(name, unreal):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"unreal": unreal}):
        spec.loader.exec_module(result)
    return result


class Texture:
    def get_editor_property(self, name):
        return True
class Properties:
    def __init__(self, path="", **properties):
        self.path, self.properties = path, properties

    def get_editor_property(self, name):
        return self.properties[name]

    def set_editor_property(self, name, value):
        self.properties[name] = value

    def export_text(self):
        return repr(self.properties)

    def get_path_name(self):
        return self.path + "." + self.path.rsplit("/", 1)[-1]


class Material(Properties):
    def __init__(self, path="", **properties):
        super().__init__(path, material_domain="surface", shading_model="unlit",
                         use_material_attributes=False)
        self.properties.update(properties)


class Instance(Properties): pass
class Custom(Properties): pass
class VectorParameter(Properties): pass
class ScalarParameter(Properties): pass
class EyeAdaptationInverse(Properties): pass
class Mesh:
    def get_editor_property(self, name):
        return [types.SimpleNamespace(get_editor_property=lambda _, s=s: "MAT_Pyrois_" + s) for s in SUFFIXES]


class ToonShadowAdapterTest(unittest.TestCase):
    def shadow_lines(self):
        # 保留源程序的两个输出及穿过该块的逆距离；采样细节不属于此适配契约。
        lines = ["  r10.w = cmp(0.5 < _is_main_light_shadows_on.x);",
                 "  if (r10.w != 0) {", "    r11.w = SourceShadow;",
                 "    r10.w = SourceShadow;", "  } else {",
                 "    r11.w = 1;", "    r10.w = 1;", "  }"]
        toon_generator.replace_main_light_shadows(lines)
        return lines

    def test_visibility_changes_shadow_without_changing_light_direction_or_attenuation(self):
        lines = self.shadow_lines()
        for distance in (1.0, 1000.0):
            for visibility, receive, entity_weight in ((1, 1, 1), (0, 1, 1), (0.35, 1, 1),
                                                       (0, 0, 1), (0.35, 0.5, 0.75), (0, 1, 0)):
                with self.subTest(distance=distance, visibility=visibility, receive=receive,
                                  entity_weight=entity_weight):
                    registers = {"r8": types.SimpleNamespace(w=0.99),
                                 "r9": types.SimpleNamespace(w=1.0 / distance),
                                 "r10": types.SimpleNamespace(w=-0.01),
                                 "r11": types.SimpleNamespace(w=1.0),
                                 "r12": types.SimpleNamespace(y=entity_weight),
                                 "_ReceiveShadows": types.SimpleNamespace(x=receive),
                                 "_AvatarMainLightColor": types.SimpleNamespace(w=1.0),
                                 "KeyLightVisibility": visibility}
                    # 仅执行生成器自产的标量赋值，不执行外部 shader 程序。
                    for line in lines:
                        exec(line.strip().rstrip(";"), {"__builtins__": {},
                             "lerp": lambda a, b, t: a + (b - a) * t,
                             "saturate": lambda v: min(1.0, max(0.0, v))}, registers)
                    self.assertAlmostEqual(distance * registers["r9"].w, 1.0)
                    self.assertEqual(registers["r8"].w, 0.99)
                    self.assertAlmostEqual(registers["r11"].w, 1 + (visibility - 1) * receive)
                    weight = min(1, max(0, 2 * entity_weight - 1))
                    self.assertAlmostEqual(registers["r10"].w, 1 + (visibility - 1) * receive * weight)

    def test_changed_source_shadow_register_contract_is_rejected(self):
        lines = ["  if (_is_main_light_shadows_on.x) {", "    r9.w = SourceShadow;",
                 "    r10.w = SourceShadow;", "    r11.w = SourceShadow;", "  }"]
        original = list(lines)
        with self.assertRaisesRegex(RuntimeError, "寄存器契约变化"):
            toon_generator.replace_main_light_shadows(lines)
        self.assertEqual(lines, original)


class ToonSkinFlagAdapterTest(unittest.TestCase):
    def source(self):
        return ('"// hash: 9225f290963128b1\n'
                '  r3.w = cmp((int)r2.w == asint(_SkinMatId.x));\n'
                '  r5.w = r3.w ? 0.000000 : 0;\n'
                '  r2.y = cmp(_AmbientGradientShape.w != 0.000000);\n')

    def test_boolean_selection_matches_native_group_comparison_and_bit_mask(self):
        code = toon_generator.restore_skin_group_flag(self.source())
        assignment = next(line for line in code.splitlines() if line.strip().startswith("r5.w ="))
        when_true, when_false = assignment.split("?", 1)[1].rstrip(";").split(":")
        # 原生 ieq 输出全位掩码；and 1 的结果只作为后续布尔选择条件。
        for group in range(5):
            for skin in range(6):
                with self.subTest(group=group, skin=skin):
                    mask = 0xFFFFFFFF if group == skin else 0
                    value = float(when_true if mask else when_false)
                    self.assertEqual(bool(value), bool(mask & 1))
                    self.assertEqual(value, 1.0 if mask else 0.0)

    def test_unrelated_zero_literal_remains_unchanged(self):
        source = self.source()
        self.assertEqual(toon_generator.restore_skin_group_flag(source),
                         source.replace("r5.w = r3.w ? 0.000000 : 0;",
                                        "r5.w = r3.w ? 1 : 0;"))

    def test_unknown_fragment_or_changed_group_contract_is_rejected(self):
        source = self.source()
        changed = (source.replace("9225f290963128b1", "1234567890abcdef"),
                   source.replace("asint(_SkinMatId.x)", "asint(_OtherGroup.x)"),
                   source.replace("r5.w = r3.w", "r5.w = r2.w"),
                   source + source,
                   source.replace("r5.w = r3.w ? 0.000000 : 0;", "r5.w = r3.w ? 1 : 0;"))
        for candidate in changed:
            with self.subTest(candidate=candidate), self.assertRaises(RuntimeError):
                toon_generator.restore_skin_group_flag(candidate)


class ToonContributionTest(unittest.TestCase):
    def setUp(self):
        # import 不启动旧 commandlet、SIE 或复制资产；实际诊断由 MCP 明确调用。
        self.capture = module("capture_pyrios_toon", types.SimpleNamespace())
        self.source = (SCRIPTS / "nap_avatar_toon.hlsl").read_text(encoding="utf-8")
        # 历史诊断固定消费其原程序：逆向恢复已证的两处变化后仍必须精确匹配旧 hash。
        # 不更新旧准入值，也不把它作为新图的诊断入口。
        self.source = self.source.replace("  RimRaw = r0.xyz;", "  float3 rimOut = r0.xyz;")
        self.source = self.source.replace("  BloomWeight = 0.333299994 * r15.y;\n  return o0.xyz;",
            "  float3 c = o0.xyz + min(rimOut, 25.0);\n"
            "  return c + max(0.0, max(c.x, max(c.y, c.z)) - 1.0) * HighlightBleed.x;")
        self.source = self.source.replace("  r5.w = r3.w ? 1 : 0;", "  r5.w = r3.w ? 0.000000 : 0;")
        import hashlib
        self.assertEqual(hashlib.sha256(self.source.encode()).hexdigest(), self.capture._CONTRIBUTION_SHA)

    def test_display_rejects_unknown_stage_before_mutation(self):
        with self.assertRaisesRegex(RuntimeError, "未知显示对照阶段"):
            self.capture.display_parameters({}, "GlobalExposure")

    def test_display_accepts_native_input_names_and_rejects_changed_pin_contract(self):
        self.assertEqual(self.capture.display_input_names(["LightValueInput", "AlphaInput"]),
                         ("LightValueInput", "AlphaInput"))
        for names in (["LightValue", "Alpha"], ["AlphaInput", "LightValueInput"], ["LightValueInput"]):
            with self.subTest(names=names), self.assertRaisesRegex(RuntimeError, "输入契约不符"):
                self.capture.display_input_names(names)

    def test_display_candidate_matches_native_linear_color_readback(self):
        import struct
        original = {i: {"vector:_PostShadowTint": (1, 1, 1, 1),
                       "vector:_PostShadowFadeTint": (1, 1, 1, 1),
                       "vector:_PostShallowTint": (1, 1, 1, 1),
                       "vector:_PostShallowFadeTint": (1, 1, 1, 1)} for i in (0, 1, 3)}
        for stage, candidates in (("ShadowTints", self.capture._DISPLAY_SHADOWS),
                                  ("ShallowTintsExposure", self.capture._DISPLAY_SHALLOWS)):
            result = self.capture.display_parameters(original, stage)
            for name, value in candidates.items():
                color = types.SimpleNamespace(**dict(zip(("r", "g", "b", "a"), struct.unpack("<4f", struct.pack("<4f", *value)))))
                native = self.capture._BodyCapture._rgba(color)
                self.assertEqual(result[0]["vector:" + name], native)

    def test_display_preserves_original_lights_and_restores_baseline(self):
        original = {i: {"vector:_PostShadowTint": [1, 1, 1, 1],
            "vector:_PostShadowFadeTint": [1, 1, 1, 1],
            "vector:_PostShallowTint": [1, 1, 1, 1], "vector:_PostShallowFadeTint": [1, 1, 1, 1],
            "scalar:SceneLightStrength": 0.65,
            "vector:KeyLightColor": [0.8, 0.9, 1, 1]} for i in (0, 1, 3)}
        untouched = json.dumps(original, sort_keys=True)
        for stage in ("Exposure", "ShadowTints", "ShadowTintsExposure", "ShallowTintsExposure", "Baseline"):
            result = self.capture.display_parameters(original, stage)
            for i, parameters in original.items():
                self.assertEqual(result[i]["scalar:SceneLightStrength"], parameters["scalar:SceneLightStrength"])
                self.assertEqual(result[i]["vector:KeyLightColor"], parameters["vector:KeyLightColor"])
                if stage in ("Baseline", "Exposure"):
                    self.assertEqual({k: v for k, v in result[i].items() if k in parameters}, parameters)
        self.assertEqual(json.dumps(original, sort_keys=True), untouched)

    def test_shallow_comparison_changes_only_two_bright_inputs_from_exposure(self):
        original = {i: {"vector:_PostShadowTint": (1, 1, 1, 1),
                       "vector:_PostShadowFadeTint": (1, 1, 1, 1),
                       "vector:_PostShallowTint": (1, 1, 1, 1),
                       "vector:_PostShallowFadeTint": (1, 1, 1, 1),
                       "texture:Diffuse": "/Game/OriginalTexture"} for i in (0, 1, 3)}
        exposure = self.capture.display_parameters(original, "Exposure")
        shallow = self.capture.display_parameters(original, "ShallowTintsExposure")
        for i in original:
            self.assertEqual({k for k in exposure[i] if exposure[i][k] != shallow[i][k]},
                             {"vector:_PostShallowTint", "vector:_PostShallowFadeTint"})
            self.assertEqual(shallow[i]["scalar:" + self.capture._DISPLAY_EXPOSURE], 1.0)

    def test_display_rejects_missing_nonfinite_and_colliding_inputs(self):
        original = {i: {"vector:_PostShadowTint": [1, 1, 1, 1],
                       "vector:_PostShadowFadeTint": [1, 1, 1, 1],
                       "vector:_PostShallowTint": [1, 1, 1, 1],
                       "vector:_PostShallowFadeTint": [1, 1, 1, 1]} for i in (0, 1, 3)}
        for name in ("vector:_PostShadowTint", "vector:_PostShallowFadeTint"):
            for kind in ("missing", "nonfinite", "collision"):
                values = {i: dict(p) for i, p in original.items()}
                if kind == "missing": del values[0][name]
                if kind == "nonfinite": values[0][name] = [1, float("nan"), 1, 1]
                if kind == "collision": values[0]["scalar:" + self.capture._DISPLAY_EXPOSURE] = 0.0
                with self.subTest(name=name, kind=kind), self.assertRaises(RuntimeError):
                    self.capture.display_parameters(values, "Baseline")

    def test_unknown_source_is_rejected_before_any_output_replacement(self):
        with self.assertRaisesRegex(RuntimeError, "未知 Toon 源码"):
            self.capture.contribution_code(self.source.replace("o0.xyz = r5.xyz", "o0.xyz = r2.xyz"), "Surface")

    def test_unknown_stage_is_rejected_and_final_is_exact_original(self):
        self.assertEqual(self.capture.contribution_code(self.source, "Final"), self.source)
        with self.assertRaisesRegex(RuntimeError, "未知贡献阶段"):
            self.capture.contribution_code(self.source, "r14")

    def test_foreign_dirty_prevents_owned_cleanup(self):
        paths = self.capture._CONTRIBUTION_PATHS
        self.capture._contribution_check_owned(paths, paths)
        with self.assertRaisesRegex(RuntimeError, "非自有脏包"):
            self.capture._contribution_check_owned(list(paths) + ["/Game/Map/L_Movement_Test"], paths)

    def test_changed_register_anchor_is_rejected_even_with_new_hash(self):
        # 源 hash 与有限锚点分开校验，不能以更新 hash 接受未知阶段位置。
        source = self.source.replace("  r2.x = cmp(_CharacterMatCapEnable.x >= 0.5);", "")
        import hashlib
        with patch.object(self.capture, "_CONTRIBUTION_SHA", hashlib.sha256(source.encode()).hexdigest()):
            with self.assertRaisesRegex(RuntimeError, "寄存器锚点"):
                self.capture.contribution_code(source, "Albedo")

    def test_disk_identity_uses_the_frozen_forward_slash_package_paths(self):
        with tempfile.TemporaryDirectory(prefix="PyriosContributionTest_", dir=PROJECT / "Saved") as content:
            package = Path(content) / "Characters/Player/Pyrios/Materials/Generated/M_Pyrois_Toon.uasset"
            package.parent.mkdir(parents=True)
            package.write_bytes(b"fixture")
            with patch.object(self.capture.unreal, "Paths", types.SimpleNamespace(project_content_dir=lambda: content), create=True):
                self.assertEqual(set(self.capture.PyriosContributionCapture._disk()),
                                 {"Materials/Generated/M_Pyrois_Toon.uasset"})

    def test_partial_attach_resume_refuses_a_changed_actor_before_asset_reads(self):
        capture = self.capture
        diagnostic = object.__new__(capture.PyriosContributionCapture)
        world = object()
        diagnostic.world = world
        diagnostic.ues = types.SimpleNamespace(get_game_world=lambda: world)
        diagnostic.stage = None
        diagnostic.flags = (False, True, False, True, "Blueprint", False)
        diagnostic.overrides = ()
        diagnostic.mesh = types.SimpleNamespace(
            get_editor_property=lambda n: [] if n == "override_materials" else False,
            is_visible=lambda: True, is_component_tick_enabled=lambda: True,
            get_animation_mode=lambda: "Blueprint")
        diagnostic.pawn = types.SimpleNamespace(get_editor_property=lambda n: True)
        with patch.object(capture.unreal, "GameplayStatics", types.SimpleNamespace(is_game_paused=lambda w: False), create=True):
            with self.assertRaisesRegex(RuntimeError, "角色状态已变"):
                diagnostic.resume_prepared_attachment()

    def test_inherited_fx_with_null_override_is_valid_but_changed_effective_material_is_rejected(self):
        capture = self.capture
        diagnostic = object.__new__(capture.PyriosContributionCapture)
        world, fx = object(), object()
        diagnostic.world = world
        diagnostic.ues = types.SimpleNamespace(get_game_world=lambda: world)
        diagnostic.original_parameters = {}
        diagnostic.expected_parameters = {}
        diagnostic.overrides = (None, None, None, None)
        diagnostic.original_materials = (None, None, fx, None)
        diagnostic._protect = lambda: None
        diagnostic.mesh = types.SimpleNamespace(get_num_bones=lambda: 177, get_material=lambda i: fx,
            get_bone_name=lambda i: str(i), get_socket_transform=lambda *a: types.SimpleNamespace(export_text=lambda: "pose"))
        with patch.multiple(capture.unreal, create=True,
            GameplayStatics=types.SimpleNamespace(is_game_paused=lambda w: True),
            EditorLevelLibrary=types.SimpleNamespace(get_pie_worlds=lambda _: [world]),
            RelativeTransformSpace=types.SimpleNamespace(RTS_WORLD="World")):
            self.assertEqual(len(diagnostic.witness()), 177)
            diagnostic.mesh.get_material = lambda i: object()
            with self.assertRaisesRegex(RuntimeError, "披风材质发生变化"):
                diagnostic.witness()


@unittest.skipUnless(SOURCE_JSON.is_dir() and SOURCE_GLOBALS.is_file(), "Pyrios source JSON not present")
class RenderToolsTest(unittest.TestCase):
    def setUp(self):
        saved = (PROJECT / "Saved").resolve()
        self.temp = tempfile.TemporaryDirectory(prefix="CharacterRenderTools_", dir=saved)
        self.root = Path(self.temp.name).resolve()
        # TemporaryDirectory 会递归清理，注册前核实实际目标只在自有 Saved 下。
        assert self.root.parent == saved and self.root.name.startswith("CharacterRenderTools_")
        self.addCleanup(self.temp.cleanup)
        for suffix in SUFFIXES:
            shutil.copy(SOURCE_JSON / ("MAT_Pyrois_" + suffix + ".json"), self.root)
        shutil.copytree(SOURCE_JSON / "TextureSettings", self.root / "TextureSettings")
        self.globals = self.root / "globals.json"
        shutil.copy(SOURCE_GLOBALS, self.globals)

    def edit(self, path, fn):
        data = json.loads(path.read_text(encoding="utf-8"))
        fn(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def builder(self, missing=None, dirty=False, wrong_type=False):
        writes = []
        def load(path):
            if missing and path.endswith(missing): return None
            if path.endswith("Avatar_Male_Size03_Pyrois_Model"): return Mesh()
            if "/Generated/" in path: return Texture() if wrong_type else None
            return Texture()
        eal = types.SimpleNamespace(load_asset=load, does_asset_exist=lambda p: wrong_type,
            make_directory=lambda *a: writes.append("mkdir"), save_loaded_asset=lambda *a: writes.append("save"))
        fake = types.SimpleNamespace(EditorAssetLibrary=eal, MaterialEditingLibrary=types.SimpleNamespace(),
            Texture2D=Texture, Material=Material, MaterialInstanceConstant=Instance, SkeletalMesh=Mesh,
            CustomMaterialOutputType=types.SimpleNamespace(CMOT_FLOAT3=0),
            EditorLoadingAndSavingUtils=types.SimpleNamespace(get_dirty_content_packages=lambda:
                [types.SimpleNamespace(get_path_name=lambda: "/Game/Characters/Player/Pyrios/Materials/Generated/M_Pyrois_Toon")] if dirty else []))
        builder = module("build_pyrios_materials", fake)
        builder.JSON_DIR, builder.GLOBALS_PATH = self.root, self.globals
        return builder, writes

    def verifier_fixture(self, configured_weight=1.0, legacy_direct=False):
        """Typed graph, exact package identities, and MI inputs for the real read-only verifier."""
        plan = load_plan(self.root, self.globals)
        root = "/Game/Characters/Player/Pyrios/Materials"
        out = root + "/Generated"
        master, outline = Material(out + "/M_Pyrois_Toon"), Material(out + "/M_Pyrois_Outline")
        code = (SCRIPTS / "nap_avatar_toon.hlsl").read_text(encoding="utf-8")
        # 此夹具是原单输出/曝光图，不伪造新图的 AdditionalOutputs 或 CPD 支持。
        code = code.replace("  RimRaw = r0.xyz;", "  float3 rimOut = r0.xyz;").replace(
            "  BloomWeight = 0.333299994 * r15.y;\n  return o0.xyz;",
            "  float3 c = o0.xyz + min(rimOut, 25.0);\n"
            "  return c + max(0.0, max(c.x, max(c.y, c.z)) - 1.0) * HighlightBleed.x;")
        custom = Custom(master.get_path_name() + ":Custom", code=code,
                        inputs=[Properties(input_name=i["name"]) for i in plan["inputs"]])
        connections = [({"component_scalar": ScalarParameter, "component_vector": VectorParameter}
                        .get(i["kind"], Properties))(master.get_path_name() + ":Input" + str(index), parameter_name=i["name"])
                       for index, i in enumerate(plan["inputs"])]
        custom.properties["_links"] = connections
        master.properties["_expressions"] = connections + [custom]
        if legacy_direct:
            master.properties["_emissive"] = custom
        else:
            weight = ScalarParameter(master.get_path_name() + ":ExposureWeight", parameter_name=EXPOSURE_PARAMETER,
                                     default_value=configured_weight, use_custom_primitive_data=False,
                                     slider_min=0.0, slider_max=1.0)
            inverse = EyeAdaptationInverse(master.get_path_name() + ":Inverse", _links=[custom, weight])
            master.properties["_expressions"] += [inverse, weight]
            master.properties["_emissive"] = inverse
        assets = {out + "/M_Pyrois_Toon": master, out + "/M_Pyrois_Outline": outline}
        for name, srgb in plan["texture_srgb"].items():
            path = root + "/Texture/" + name
            assets[path] = Properties(path, srgb=srgb)
        slots = []
        for suffix in SUFFIXES:
            path = out + "/MI_Pyrois_" + suffix
            instance = Instance(path, parent=master,
                                base_property_overrides=Properties(override_shading_model=False, shading_model="unlit"))
            instance.vectors = dict(plan["globals"], **plan["params"][suffix], **PREVIEW_LIGHT)
            instance.scalars = dict(PREVIEW_SCALARS)
            instance.textures = {}
            for name, texture in plan["textures"][suffix].items():
                default = next(plan["textures"][s][name] for s in SUFFIXES if plan["textures"][s][name])
                instance.textures[name] = assets[root + "/Texture/" + (texture or default)]
            assets[path] = instance
            slots.append(Properties(material_slot_name="MAT_Pyrois_" + suffix, material_interface=instance))
        assets["/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"] = Properties(materials=slots)
        compiled = []
        fake = types.SimpleNamespace(Material=Material, MaterialInstanceConstant=Instance,
            MaterialExpressionCustom=Custom, MaterialExpressionVectorParameter=VectorParameter,
            MaterialExpressionScalarParameter=ScalarParameter,
            MaterialExpressionEyeAdaptationInverse=EyeAdaptationInverse,
            CustomMaterialOutputType=types.SimpleNamespace(CMOT_FLOAT3=0),
            MaterialUsage=types.SimpleNamespace(MATUSAGE_SKELETAL_MESH=0),
            MaterialDomain=types.SimpleNamespace(MD_SURFACE="surface"),
            MaterialShadingModel=types.SimpleNamespace(MSM_UNLIT="unlit"),
            MaterialProperty=types.SimpleNamespace(MP_EMISSIVE_COLOR=0),
            EditorAssetLibrary=types.SimpleNamespace(does_asset_exist=lambda p: p in assets, load_asset=assets.get),
            MaterialEditingLibrary=types.SimpleNamespace(has_material_usage=lambda *a: True,
                recompile_material=lambda m: compiled.append(m) or [],
                get_statistics=lambda m: types.SimpleNamespace(num_pixel_shader_instructions=1, num_vertex_shader_instructions=1),
                get_material_property_input_node=lambda m, _: m.properties["_emissive"],
                get_material_expressions=lambda m: m.properties["_expressions"],
                get_scalar_parameter_names=lambda m: list(dict.fromkeys(n.properties["parameter_name"] for n in m.properties["_expressions"] if isinstance(n, ScalarParameter))),
                get_material_expression_input_names=lambda _: ["LightValueInput", "AlphaInput"],
                get_inputs_for_material_expression=lambda m, n: n.properties["_links"],
                get_material_instance_texture_parameter_value=lambda mi, n: mi.textures.get(n),
                get_material_instance_vector_parameter_value=lambda mi, n:
                    types.SimpleNamespace(**dict(zip(("r", "g", "b", "a"), mi.vectors[n]))),
                get_material_instance_scalar_parameter_value=lambda mi, n: mi.scalars.get(n,
                    configured_weight if n == EXPOSURE_PARAMETER else 0.0)),
            log=lambda *a: None)
        verifier = module("verify_pyrios_renderer", fake)
        verifier.JSON_DIR, verifier.GLOBALS_PATH = self.root, self.globals
        source = self.root / "accepted_single_output.hlsl"
        source.write_text(code, encoding="utf-8")
        verifier.HLSL_PATH = source
        return verifier, assets, compiled, custom, connections

    def test_complete_source_plan(self):
        plan = load_plan(self.root, self.globals)
        self.assertEqual(set(plan["materials"]), set(SUFFIXES))
        inputs = {i["name"] for i in plan["inputs"] if i["kind"] == "material"}
        for suffix in SUFFIXES:
            self.assertTrue(inputs.issubset(plan["params"][suffix]))
        self.assertIn("Eff_Matcap_125", plan["texture_names"])

    def test_color_property_is_linearized_vector_is_not(self):
        def mutate(d):
            d["m_SavedProperties"]["m_Colors"]["_ShallowColor"] = dict(r=0.5, g=0.5, b=0.5, a=0.5)
            d["m_SavedProperties"]["m_Colors"]["_RefractParam"] = dict(r=0.5, g=0.5, b=0.5, a=0.5)
        self.edit(self.root / "MAT_Pyrois_Body_1.json", mutate)
        params = load_plan(self.root, self.globals)["params"]["Body_1"]
        self.assertAlmostEqual(params["_ShallowColor"][0], unity_gamma_to_linear(0.5))
        self.assertEqual(params["_ShallowColor"][3], 0.5)
        self.assertEqual(params["MC_Refract1"], (0.5, 0.5, 0.5, 0.5))

    def test_matcap_slice_only_for_assigned_textures(self):
        plan = load_plan(self.root, self.globals)
        for suffix in SUFFIXES:
            for g in range(1, 6):
                has_tex = plan["textures"][suffix]["MatCapTex%d" % g] is not None
                self.assertEqual(plan["params"][suffix]["MC_A%d" % g][0], float(g - 1) if has_tex else 100.0)

    def test_texture_colorspace_from_settings(self):
        plan = load_plan(self.root, self.globals)
        self.assertTrue(plan["texture_srgb"]["Pyrois_Body_Map1_D"])
        self.assertFalse(plan["texture_srgb"]["Pyrois_Body_Map1_N"])
        self.assertTrue(plan["slot_srgb"]["SpecialWeaponEmissionMaskTex"])

    def test_missing_texture_settings_rejected(self):
        (self.root / "TextureSettings" / "Eff_Mask_032.json").unlink()
        with self.assertRaisesRegex(ValueError, "Eff_Mask_032"):
            load_plan(self.root, self.globals)

    def test_hdr_color_scales_gamma_base(self):
        from pyrios_material_plan import unity_color_to_linear
        r, g, b = unity_color_to_linear((2.509804, 6.5254903, 47.937256))
        self.assertAlmostEqual(b, 47.937256)
        self.assertLess(g, 1.0)

    def test_unsupported_feature_rejected(self):
        self.edit(self.root / "MAT_Pyrois_Body_2.json",
                  lambda d: d["m_SavedProperties"]["m_Floats"].__setitem__("_DoubleSided", 1.0))
        with self.assertRaisesRegex(ValueError, "_DoubleSided"):
            load_plan(self.root, self.globals)

    def test_last_material_invalid_before_writes(self):
        self.edit(self.root / "MAT_Pyrois_Weapon01.json",
                  lambda d: d["m_SavedProperties"]["m_Colors"]["_SpecularColor5"].pop("a"))
        builder, writes = self.builder()
        with self.assertRaises(ValueError): builder.preflight()
        self.assertEqual(writes, [])

    def test_unknown_global_rejected(self):
        self.edit(self.globals, lambda d: d.__setitem__("TypoGain", [1, 0, 0, 0]))
        with self.assertRaisesRegex(ValueError, "TypoGain"): load_plan(self.root, self.globals)

    def test_missing_global_rejected(self):
        self.edit(self.globals, lambda d: d.pop("_PostShadowTint"))
        with self.assertRaisesRegex(ValueError, "_PostShadowTint"): load_plan(self.root, self.globals)

    def test_nonfinite_global_rejected(self):
        self.globals.write_text(self.globals.read_text(encoding="utf-8").replace(
            '"_CharacterAmbient": [0, 0, 0, 0]', '"_CharacterAmbient": [NaN, 0, 0, 0]'), encoding="utf-8")
        with self.assertRaises(ValueError): load_plan(self.root, self.globals)

    def test_missing_texture_before_writes(self):
        builder, writes = self.builder(missing="Pyrois_Weapon_A")
        with self.assertRaisesRegex(RuntimeError, "texture type"): builder.preflight()
        self.assertEqual(writes, [])

    def test_dirty_target_before_writes(self):
        builder, writes = self.builder(dirty=True)
        with self.assertRaisesRegex(RuntimeError, "dirty target"): builder.preflight()
        self.assertEqual(writes, [])

    def test_wrong_existing_output_type_before_writes(self):
        builder, writes = self.builder(wrong_type=True)
        with self.assertRaisesRegex(RuntimeError, "output asset type"): builder.preflight()
        self.assertEqual(writes, [])

    def test_save_failure_is_not_reported_complete(self):
        journal = BuildJournal()
        journal.touch("first")
        journal.save("first", lambda: True)
        journal.touch("second")
        with self.assertRaises(RuntimeError): journal.save("second", lambda: False)
        report = journal.report("failed", "disk error")
        self.assertEqual(report["saved"], ["first"])
        self.assertEqual(report["unsaved_or_failed"], ["second"])

    def test_verifier_compile_is_opt_in(self):
        compiled = []
        fake = types.SimpleNamespace(Material=Material, MaterialInstanceConstant=Instance,
            MaterialUsage=types.SimpleNamespace(MATUSAGE_SKELETAL_MESH=0),
            MaterialDomain=types.SimpleNamespace(MD_SURFACE="surface"),
            MaterialShadingModel=types.SimpleNamespace(MSM_UNLIT="unlit"),
            EditorAssetLibrary=types.SimpleNamespace(does_asset_exist=lambda p: True,
                load_asset=lambda p: Material() if "/Generated/" in p and p.split("/")[-1].startswith("M_") else None),
            MaterialEditingLibrary=types.SimpleNamespace(has_material_usage=lambda *a: True,
                recompile_material=lambda m: compiled.append(m) or [],
                get_statistics=lambda m: types.SimpleNamespace(num_pixel_shader_instructions=1)),
            log=lambda *a: None)
        verifier = module("verify_pyrios_renderer", fake)
        # 两个 master 检查完后在第一个缺失的 MI 处停下；只读模式不重编译。
        with self.assertRaises(AssertionError): verifier.verify()
        self.assertEqual(compiled, [])
        with self.assertRaises(AssertionError): verifier.verify(recompile=True)
        self.assertEqual(len(compiled), 2)

    def test_verifier_complete_graph_and_bindings_are_read_only(self):
        verifier, _, compiled, _, _ = self.verifier_fixture()
        verifier.verify()
        self.assertEqual(compiled, [])

    def test_verifier_rejects_lit_master(self):
        verifier, assets, compiled, _, _ = self.verifier_fixture()
        assets[verifier.ROOT + "/Generated/M_Pyrois_Toon"].properties["shading_model"] = "lit"
        with self.assertRaisesRegex(AssertionError, "Unlit"): verifier.verify()
        self.assertEqual(compiled, [])

    def test_verifier_rejects_parent_from_another_package(self):
        verifier, assets, _, _, _ = self.verifier_fixture()
        mi = assets[verifier.ROOT + "/Generated/MI_Pyrois_Body_1"]
        mi.properties["parent"] = Material("/Game/Other/M_Pyrois_Toon")
        with self.assertRaisesRegex(AssertionError, "wrong parent"): verifier.verify()

    def test_verifier_rejects_lit_instance_override(self):
        verifier, assets, _, _, _ = self.verifier_fixture()
        overrides = assets[verifier.ROOT + "/Generated/MI_Pyrois_Body_1"].properties["base_property_overrides"]
        overrides.properties.update(override_shading_model=True, shading_model="lit")
        with self.assertRaisesRegex(AssertionError, "Lit instance override"): verifier.verify()

    def test_verifier_requires_each_target_slot_exactly_once(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                verifier, assets, _, _, _ = self.verifier_fixture()
                slots = assets["/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"].properties["materials"]
                if duplicate: slots.append(slots[0])
                else: slots.pop()
                with self.assertRaisesRegex(AssertionError, "missing/duplicate target mesh slot"): verifier.verify()

    def test_verifier_rejects_same_named_slot_asset_from_other_package(self):
        verifier, assets, _, _, _ = self.verifier_fixture()
        slot = assets["/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"].properties["materials"][0]
        slot.properties["material_interface"] = Instance("/Game/Other/MI_Pyrois_Body_1")
        with self.assertRaises(AssertionError): verifier.verify()

    def test_verifier_checks_preview_light_scalars(self):
        verifier, assets, _, _, _ = self.verifier_fixture()
        assets[verifier.ROOT + "/Generated/MI_Pyrois_Body_1"].scalars.pop("SceneLightStrength")
        with self.assertRaisesRegex(AssertionError, "SceneLightStrength"): verifier.verify()

    def test_verifier_rejects_changed_toon_code(self):
        verifier, _, _, custom, _ = self.verifier_fixture()
        custom.properties["code"] += "\nreturn float3(1,1,1);"
        with self.assertRaisesRegex(AssertionError, "code differs"): verifier.verify()

    def test_verifier_rejects_missing_or_wrong_typed_light_input(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                verifier, _, _, _, connections = self.verifier_fixture()
                index = next(i for i, n in enumerate(verifier.load_plan(self.root, self.globals)["inputs"])
                             if n["name"] == "SceneLightStrength")
                connections[index] = None if missing else VectorParameter(parameter_name="SceneLightStrength")
                with self.assertRaisesRegex(AssertionError, "connected|wrong light parameter type"): verifier.verify()


@unittest.skipUnless(SOURCE_JSON.is_dir() and SOURCE_GLOBALS.is_file(), "Pyrios source JSON not present")
class ExposureMaterialToolsTest(unittest.TestCase):
    """验证真实单Master调用链的写入范围、图保留、迁移和提交门禁。"""

    def fixture(self, legacy_direct=True):
        self.root, self.globals = SOURCE_JSON, SOURCE_GLOBALS
        verifier, assets, compiled, custom, _ = RenderToolsTest.verifier_fixture(self, legacy_direct=legacy_direct)
        fake = verifier.unreal
        master = assets[verifier.ROOT + "/Generated/M_Pyrois_Toon"]
        saved, events = [], []
        fake.EditorLevelLibrary = types.SimpleNamespace(get_pie_worlds=lambda _: [])
        fake.EditorLoadingAndSavingUtils = types.SimpleNamespace(
            get_dirty_content_packages=lambda: [], get_dirty_map_packages=lambda: [])
        fake.EditorAssetLibrary.save_loaded_asset = lambda m: events.append("save") or saved.append(m) or True
        mel = fake.MaterialEditingLibrary

        def create(m, cls, x, y):
            expression = cls(m.get_path_name() + ":Added" + str(len(m.properties["_expressions"])),
                             parameter_name="", default_value=0.0, use_custom_primitive_data=False,
                             slider_min=0.0, slider_max=0.0, _links=[None, None])
            m.properties["_expressions"].append(expression)
            return expression

        def connect(source, _, target, name):
            target.properties["_links"][["LightValueInput", "AlphaInput"].index(name)] = source
            return True

        mel.create_material_expression = create
        mel.connect_material_expressions = connect
        mel.connect_material_property = lambda n, _, prop: master.properties.update(_emissive=n) or True
        mel.recompile_material = lambda m: events.append("compile") or compiled.append(m) or []
        fake.log_error = lambda _: None
        builder = module("build_pyrios_materials", fake)
        builder.JSON_DIR, builder.GLOBALS_PATH = self.root, self.globals
        return builder, verifier, master, custom, assets, saved, events

    def test_configuration_is_explicit_and_invalid_values_stop_before_asset_reads(self):
        builder, _, _, _, _, _, _ = self.fixture()
        for value in (0.0, 0.5, 1.0):
            self.assertEqual(exposure_weight(value), value)
        with patch.object(builder.EAL, "load_asset", side_effect=AssertionError("unexpected asset read")):
            for value in (None, True, float("nan"), float("inf"), -0.1, 1.1):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    builder.apply_master_exposure(value)
        with self.assertRaises(TypeError):
            builder.apply_master_exposure()

    def test_single_master_migration_preserves_original_program_inputs_and_other_assets(self):
        for value in (0.0, 1.0):
            with self.subTest(value=value):
                builder, verifier, master, custom, assets, saved, events = self.fixture()
                before = builder._toon_snapshot(custom)
                nodes = tuple(master.properties["_expressions"])
                other_inputs = {p: (dict(m.vectors), dict(m.scalars), dict(m.textures))
                                for p, m in assets.items() if isinstance(m, Instance)}
                with patch.dict(sys.modules, {"verify_pyrios_renderer": verifier}):
                    self.assertIs(builder.apply_master_exposure(value), master)
                self.assertEqual(builder._toon_snapshot(custom), before)
                self.assertTrue(set(nodes).issubset(master.properties["_expressions"]))
                self.assertEqual(len(master.properties["_expressions"]), len(nodes) + 2)
                verifier.verify_surface_graph(master, load_plan(self.root, self.globals), value)
                self.assertEqual({p: (m.vectors, m.scalars, m.textures)
                                  for p, m in assets.items() if isinstance(m, Instance)}, other_inputs)
                self.assertEqual(saved, [master])
                self.assertEqual(events, ["compile", "save"])

    def test_reconfiguration_reuses_the_same_native_nodes(self):
        builder, verifier, master, custom, _, saved, _ = self.fixture()
        with patch.dict(sys.modules, {"verify_pyrios_renderer": verifier}):
            builder.apply_master_exposure(1.0)
            nodes = tuple(master.properties["_expressions"])
            before = builder._toon_snapshot(custom)
            builder.apply_master_exposure(0.0)
        self.assertEqual(tuple(master.properties["_expressions"]), nodes)
        self.assertEqual(builder._toon_snapshot(custom), before)
        verifier.verify_surface_graph(master, load_plan(self.root, self.globals), 0.0)
        self.assertEqual(saved, [master, master])

    def test_invalid_source_dirty_or_pie_refuses_before_graph_mutation(self):
        for kind in ("source", "dirty", "pie", "extra_expression", "collision"):
            with self.subTest(kind=kind):
                builder, verifier, master, custom, _, saved, events = self.fixture()
                if kind == "source": custom.properties["code"] += "\nreturn 1;"
                if kind == "dirty": builder.unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages = lambda: [Properties("/Game/UserMap")]
                if kind == "pie": builder.unreal.EditorLevelLibrary.get_pie_worlds = lambda _: [object()]
                if kind == "extra_expression": master.properties["_expressions"].append(Properties("/Game/Unidentified"))
                if kind == "collision": master.properties["_expressions"].append(ScalarParameter(parameter_name=EXPOSURE_PARAMETER))
                before = tuple(master.properties["_expressions"])
                with patch.dict(sys.modules, {"verify_pyrios_renderer": verifier}), self.assertRaises((RuntimeError, AssertionError)):
                    builder.apply_master_exposure(1.0)
                self.assertEqual(tuple(master.properties["_expressions"]), before)
                self.assertEqual(saved, [])
                self.assertEqual(events, [])

    def test_pin_connection_compile_and_postcompile_changes_do_not_save(self):
        for kind in ("pins", "connection", "errors", "unknown_diagnostics", "instructions", "postcompile_input", "postcompile_foreign_dirty"):
            with self.subTest(kind=kind):
                builder, verifier, master, custom, _, saved, events = self.fixture()
                before = builder._toon_snapshot(custom)
                mel = builder.MEL
                if kind == "pins": mel.get_material_expression_input_names = lambda _: ["LightValue", "Alpha"]
                if kind == "connection": mel.connect_material_expressions = lambda *args: False
                if kind in ("errors", "unknown_diagnostics"):
                    mel.recompile_material = lambda m: ["actual shader error"] if kind == "errors" else None
                if kind == "instructions": mel.get_statistics = lambda m: types.SimpleNamespace(num_pixel_shader_instructions=0)
                if kind == "postcompile_input":
                    def changed(m):
                        custom.properties["inputs"][0].properties["input_name"] = "Changed"
                        return []
                    mel.recompile_material = changed
                if kind == "postcompile_foreign_dirty":
                    def foreign_dirty(m):
                        builder.unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages = lambda: [Properties("/Game/UserChanged")]
                        return []
                    mel.recompile_material = foreign_dirty
                with patch.dict(sys.modules, {"verify_pyrios_renderer": verifier}), self.assertRaises((RuntimeError, AssertionError)):
                    builder.apply_master_exposure(1.0)
                self.assertEqual(saved, [])
                self.assertNotIn("save", events)
                if kind != "postcompile_input": self.assertEqual(builder._toon_snapshot(custom), before)

    def test_master_only_dispatch_does_not_run_any_batch_mutator(self):
        builder, verifier, master, _, _, saved, _ = self.fixture()
        with patch.dict(sys.modules, {"verify_pyrios_renderer": verifier}), patch.multiple(builder,
                preflight=unittest.mock.Mock(side_effect=AssertionError("batch preflight")),
                configure_textures=unittest.mock.Mock(side_effect=AssertionError("textures")),
                build_main=unittest.mock.Mock(side_effect=AssertionError("rebuild")),
                build_outline=unittest.mock.Mock(side_effect=AssertionError("outline")),
                set_instance=unittest.mock.Mock(side_effect=AssertionError("MI")),
                bind_editor_preview_materials=unittest.mock.Mock(side_effect=AssertionError("Mesh"))):
            builder.main(1.0, master_exposure_only=True)
        self.assertEqual(saved, [master])
        self.assertIsNone(builder.JOURNAL)

    def test_failed_single_master_save_does_not_publish_complete(self):
        builder, verifier, master, _, _, saved, _ = self.fixture()
        messages = []
        builder.unreal.log = messages.append
        builder.unreal.log_error = messages.append
        builder.EAL.save_loaded_asset = lambda _: False
        with patch.dict(sys.modules, {"verify_pyrios_renderer": verifier}), self.assertRaisesRegex(RuntimeError, "Asset save failed"):
            builder.main(1.0, master_exposure_only=True)
        failed = next(m for m in messages if m.startswith("PYRIOS_MATERIAL_BUILD_FAILED "))
        record = json.loads(failed.split(" ", 1)[1])
        self.assertEqual(record["saved"], [])
        self.assertEqual(record["unsaved_or_failed"], [master.path])
        self.assertFalse(any(m.startswith("PYRIOS_MASTER_EXPOSURE_OK") for m in messages))
        self.assertEqual(saved, [])
        self.assertIsNone(builder.JOURNAL)

    def test_verifier_requires_native_output_and_an_editable_unique_scalar(self):
        for kind in ("legacy", "swapped", "primitive", "name", "duplicate", "default"):
            with self.subTest(kind=kind):
                _, verifier, master, _, _, _, _ = self.fixture(legacy_direct=(kind == "legacy"))
                output = master.properties["_emissive"]
                if kind != "legacy":
                    weight = output.properties["_links"][1]
                    if kind == "swapped": output.properties["_links"].reverse()
                    if kind == "primitive": weight.properties["use_custom_primitive_data"] = True
                    if kind == "name": weight.properties["parameter_name"] = "PyriosDiagnosticExposureWeight"
                    if kind == "duplicate": master.properties["_expressions"].append(ScalarParameter(parameter_name=EXPOSURE_PARAMETER))
                    if kind == "default": weight.properties["default_value"] = float("nan")
                with self.assertRaises((AssertionError, ValueError)):
                    verifier.verify_surface_graph(master, load_plan(self.root, self.globals))


class ProjectSurfacePipelineTest(unittest.TestCase):
    """只覆盖新输出/CPD连接和真实配置拒绝；UE编译/编辑器生命周期另走原生门槛。"""
    def setUp(self):
        fixture = RenderToolsTest(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        verifier, assets, _, custom, _ = fixture.verifier_fixture(legacy_direct=True)
        self.plan = load_plan(fixture.root, fixture.globals)
        self.master = assets["/Game/Characters/Player/Pyrios/Materials/Generated/M_Pyrois_Toon"]
        self.custom, self.verifier = custom, verifier
        custom.properties["output_type"] = 0
        # 新切片使用真实新源码，不能复用历史图身份/准入。
        custom.properties["code"] = (SCRIPTS / "nap_avatar_toon.hlsl").read_text(encoding="utf-8")
        verifier.HLSL_PATH = SCRIPTS / "nap_avatar_toon.hlsl"
        fake = verifier.unreal
        fake.CustomMaterialOutputType.CMOT_FLOAT1 = 1
        class ProtectedCustomInput(Properties):
            def get_editor_property(self, name):
                if name == "input":
                    raise RuntimeError("CustomInput: Property 'Input' is protected and cannot be read")
                return super().get_editor_property(name)

            def export_text(self):
                if "export_override" in self.properties:
                    return self.properties["export_override"]
                link = self.properties["input"].properties
                source = link["expression"]
                expression = "/Script/Engine.MaterialExpressionCustom'" + source.get_path_name() + "'"
                return ('(InputName=' + json.dumps(str(self.properties["input_name"])) + ',Input=(Expression='
                        + json.dumps(expression) + ',OutputIndex=' + str(link["output_index"])
                        + ',InputName="",Mask=0,MaskR=0,MaskG=0,MaskB=0,MaskA=0))')
        fake.CustomInput = ProtectedCustomInput
        fake.CustomOutput = Properties
        fake.MaterialExpressionVectorParameter = VectorParameter
        fake.MaterialExpressionScalarParameter = ScalarParameter
        fake.MaterialExpressionCustom = Custom
        mel = fake.MaterialEditingLibrary
        def create(master, cls, x, y):
            expression = cls(master.get_path_name() + ":N" + str(len(master.properties["_expressions"])),
                             inputs=[], additional_outputs=[], use_custom_primitive_data=False, _links=[])
            master.properties["_expressions"].append(expression)
            return expression
        def connect(source, output, target, name):
            outputs = ["return"] + [str(o.get_editor_property("output_name")) for o in source.properties.get("additional_outputs", [])]
            index = outputs.index(output) if output in outputs else 0
            for pin in target.properties["inputs"]:
                if pin.get_editor_property("input_name") == name:
                    pin.set_editor_property("input", Properties(expression=source, output_index=index))
            target.properties["_links"] = [p.properties.get("input", Properties(expression=None)).get_editor_property("expression")
                                           for p in target.properties["inputs"]]
            return True
        for pin, link in zip(custom.properties["inputs"], custom.properties["_links"]):
            pin.set_editor_property("input", Properties(expression=link, output_index=0))
            link.properties["use_custom_primitive_data"] = False
        mel.create_material_expression = create
        mel.connect_material_expressions = connect
        mel.connect_material_property = lambda node, _, prop: self.master.properties.__setitem__("_emissive", node) is None
        self.builder = module("build_pyrios_materials", fake)
        self.original_links = list(custom.properties["_links"])
        self.builder.add_project_surface(self.master, custom, self.plan)

    def test_project_graph_consumes_separate_main_rim_and_exclusive_preview_values(self):
        composite = self.master.properties["_emissive"]
        with self.assertRaisesRegex(RuntimeError, "protected"):
            composite.properties["inputs"][0].get_editor_property("input")
        self.assertIs(self.verifier.verify_project_surface_graph(self.master, self.plan), self.custom)
        links = self.custom.properties["_links"]
        for item, before, after in zip(self.plan["inputs"], self.original_links, links):
            if item["kind"] not in ("component_vector", "component_scalar"):
                self.assertIs(before, after)
        # 新的预览传输只覆盖四个输入，不能动贴图/角色属性/原始UV。
        self.assertEqual(sum(a is not b for a, b in zip(self.original_links, links)), 4)

    def test_reversed_source_outputs_are_not_a_valid_surface(self):
        composite = self.master.properties["_emissive"]
        composite.properties["inputs"][0].properties["input"].set_editor_property("output_index", 1)
        with self.assertRaisesRegex(AssertionError, "output index"):
            self.verifier.verify_project_surface_graph(self.master, self.plan)

    def test_native_custom_connection_export_requires_full_identity_index_and_rgb(self):
        pin = self.master.properties["_emissive"].properties["inputs"][0]
        exported = pin.export_text()
        self.assertEqual(self.verifier.custom_input_output_index(pin, self.custom), 0)
        for bad in (exported.replace(',OutputIndex=0', ''),
                    exported.replace(self.custom.get_path_name(), self.custom.get_path_name() + '_Foreign'),
                    exported.replace('InputName="MainColor"', 'InputName="RimRaw"', 1),
                    exported.replace('Mask=0', 'Mask=1'),
                    exported + ',OutputIndex=0'):
            with self.subTest(exported=bad), self.assertRaises(AssertionError):
                pin.properties["export_override"] = bad
                self.verifier.custom_input_output_index(pin, self.custom)
        pin.properties.pop("export_override")

    def test_native_custom_connection_export_failure_propagates(self):
        pin = self.master.properties["_emissive"].properties["inputs"][0]
        def fail_export():
            raise RuntimeError("native export failed")
        pin.export_text = fail_export
        with self.assertRaisesRegex(RuntimeError, "native export failed"):
            self.verifier.verify_project_surface_graph(self.master, self.plan)

    def test_foreign_cpd_index_or_wrong_preview_channel_is_rejected(self):
        cpd = next(n for n in self.master.properties["_expressions"] if n.properties.get("parameter_name") == "ScenePreviewColorR")
        cpd.properties["primitive_data_index"] = 3
        with self.assertRaises(AssertionError):
            self.verifier.verify_project_surface_graph(self.master, self.plan)

    def test_scene_following_requires_an_explicit_nonzero_intensity_response(self):
        from pyrios_material_plan import scene_light_settings
        settings = scene_light_settings(10, 0.5, 0.65, 1)
        self.assertEqual(settings["KeyLightIntensityResponse"], 0.5)
        self.assertTrue(settings["bPreviewSceneLighting"])
        for args in ((10, 0, 0.65, 1), (0, 0.5, 0.65, 1), (10, 0.5, -1, 1), (10, float("nan"), 1, 1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                scene_light_settings(*args)

    def test_explicit_exposure_choice_preserves_the_new_surface_and_preview_transport(self):
        fake = self.builder.unreal
        mel = fake.MaterialEditingLibrary
        create = mel.create_material_expression
        def create_inverse(master, cls, x, y):
            expression = create(master, cls, x, y)
            if cls is EyeAdaptationInverse:
                expression.properties["inputs"] = [Properties(input_name=name) for name in ("LightValueInput", "AlphaInput")]
            return expression
        mel.create_material_expression = create_inverse
        mel.get_material_expression_input_names = lambda node: [p.get_editor_property("input_name") for p in node.properties["inputs"]]
        fake.EditorLevelLibrary = types.SimpleNamespace(get_pie_worlds=lambda _: [])
        fake.EditorLoadingAndSavingUtils = types.SimpleNamespace(get_dirty_content_packages=lambda: [], get_dirty_map_packages=lambda: [])
        saved = []
        fake.EditorAssetLibrary.save_loaded_asset = lambda asset: saved.append(asset) or True
        original = self.builder._toon_snapshot(self.custom)
        with patch.dict(sys.modules, {"verify_pyrios_renderer": self.verifier}):
            self.builder.apply_master_exposure(0.5)
        self.assertEqual(self.builder._toon_snapshot(self.custom), original)
        self.verifier.verify_project_surface_graph(self.master, self.plan, 0.5)
        self.assertEqual(saved, [self.master])

    def test_project_display_configuration_is_not_source_global_data(self):
        from pyrios_material_plan import load_display, load_globals
        with tempfile.TemporaryDirectory(dir=PROJECT / "Saved", prefix="RenderDisplay_") as folder:
            path = Path(folder) / "globals.json"
            original = json.loads(SOURCE_GLOBALS.read_text(encoding="utf-8"))
            original["ProjectDisplay"] = {"RimCompositeGain": -1, "RimMaxIntensity": 25}
            path.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_display(path)
            self.assertNotIn("ProjectDisplay", load_globals(path, self.plan["inputs"]))


if __name__ == "__main__":
    unittest.main()
