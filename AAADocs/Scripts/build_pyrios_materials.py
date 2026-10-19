"""Run with UnrealEditor-Cmd -run=pythonscript -script="<this file> --exposure-weight=<0..1>" -AllowCommandletRendering.

生成 Pyrios 表面材质：
- M_Pyrois_Toon：Unlit，原程序 Custom 节点承载 nap_avatar_toon.hlsl（NapAvatarStandard
  CharacterToonDeferred 像素逻辑的逐行移植），主光由 UGGYGOCharacterRenderComponent 写入
  KeyLightDirectionWS / KeyLightColor / SceneLightStrength / KeyLightVisibility；
- MI_Pyrois_Body_1 / Body_2 / Weapon01：参数来自材质 JSON 与 Pyrios_Toon_Globals.json；
- M_Pyrois_Outline：运行时反面扩张描边；
- 把三个 MI 绑定到骨骼网格的默认槽位作为编辑器预览。
可重复运行；完整预检通过前不写资产。

--master-exposure-only --exposure-weight=<0..1> 只给既有主材质接入／配置原生曝光抵偿。
权重必须明确指定；此入口不重建旧图、不修改其它资产。0保留曝光、1全额抵偿。
--surface-pipeline 只迁移已验单Master的项目合成/场景预览图，保持现有曝光；
默认留下未保存编辑，--save-pipeline 才保存。必须在另行授权的干净 UE 窗口运行。
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
import unreal

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyrios_material_plan import (BuildJournal, EXPOSURE_INPUTS, EXPOSURE_PARAMETER,
                                 PREVIEW_LIGHT, PREVIEW_SCALARS, SLOT_INSTANCES,
                                 SUFFIXES, SURFACE_OUTPUTS, PREVIEW_DATA_NAMES, DISPLAY_PARAMETERS,
                                 COMPOSITE_CODE, PREVIEW_CODE, exposure_weight, load_plan)


ROOT = "/Game/Characters/Player/Pyrios/Materials"
OUT = ROOT + "/Generated"
JSON_DIR = Path(__file__).resolve().parents[1] / "Assets/Pyrios/Rendering/UnityMaterials"
GLOBALS_PATH = Path(__file__).resolve().parents[1] / "Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json"
HLSL_PATH = Path(__file__).resolve().with_name("nap_avatar_toon.hlsl")
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
MESH_PATH = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"
def slot_inputs(plan):
    """{贴图槽: (占位贴图名, 采样类型名)}。

    采样类型按槽内贴图的 Unity sRGB 设置决定；占位贴图取任一材质在该槽用到的贴图，
    保证与采样类型一致（不一致会编译失败）。
    """
    result = {}
    for slot in [i["name"] for i in plan["inputs"] if i["kind"] == "texture"]:
        used = [plan["textures"][s][slot] for s in SUFFIXES if plan["textures"][s][slot]]
        if not used:
            raise RuntimeError("没有任何材质使用贴图槽 " + slot)
        result[slot] = (used[0], "SAMPLERTYPE_COLOR" if plan["slot_srgb"][slot] else "SAMPLERTYPE_LINEAR_COLOR")
    return result


JOURNAL = None


def touch(obj):
    if JOURNAL is not None:
        JOURNAL.touch(obj.get_path_name().split(".")[0])


def save(obj):
    path = obj.get_path_name().split(".")[0]
    if JOURNAL is None:
        if not EAL.save_loaded_asset(obj):
            raise RuntimeError("Asset save failed: " + path)
    else:
        JOURNAL.save(path, lambda: EAL.save_loaded_asset(obj))


def check_targets_clean(paths):
    dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts = sorted(dirty.intersection(paths))
    if conflicts:
        raise RuntimeError("Refusing to overwrite/save dirty target packages: " + str(conflicts))


def preflight():
    plan = load_plan(JSON_DIR, GLOBALS_PATH)
    packed = {ROOT + "/Texture/Pyrois_" + body + "_" + suffix
              for body in ("Body_Map1", "Body_Map2", "Weapon") for suffix in ("N", "M", "A")}
    required = {ROOT + "/Texture/" + name for name in plan["texture_names"]} | packed
    for path in sorted(required):
        if not isinstance(EAL.load_asset(path), unreal.Texture2D):
            raise RuntimeError("Missing/wrong texture type: " + path)
    outputs = {OUT + "/M_Pyrois_Toon": unreal.Material, OUT + "/M_Pyrois_Outline": unreal.Material}
    outputs.update({OUT + "/MI_Pyrois_" + s: unreal.MaterialInstanceConstant for s in SUFFIXES})
    for path, cls in outputs.items():
        if EAL.does_asset_exist(path) and not isinstance(EAL.load_asset(path), cls):
            raise RuntimeError("Wrong output asset type: " + path)
    mesh = EAL.load_asset(MESH_PATH)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("Missing/wrong mesh type: " + MESH_PATH)
    slots = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("materials")]
    if any(slots.count(name) != 1 for name in SLOT_INSTANCES):
        raise RuntimeError("Expected each target mesh slot exactly once: " + str(slots))
    used = {ROOT + "/Texture/" + n for n in plan["texture_names"]}
    check_targets_clean(packed | used | set(outputs) | {MESH_PATH})
    return plan


def node(material, cls, x, y, **props):
    result = MEL.create_material_expression(material, cls, x, y)
    for name, value in props.items():
        result.set_editor_property(name, value)
    return result


def connect(a, b, name, output=""):
    if not MEL.connect_material_expressions(a, output, b, name):
        raise RuntimeError("Could not connect %s to %s" % (a, name))


def asset(name, factory, asset_class):
    path = OUT + "/" + name
    if JOURNAL is not None:
        JOURNAL.touch(path)
    result = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if result is None:
        result = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, OUT, asset_class, factory)
    if result is None:
        raise RuntimeError("Could not create " + path)
    return result


def clear_expressions(m):
    MEL.delete_all_material_expressions(m)
    for leftover in MEL.get_material_expressions(m):
        MEL.delete_material_expression(m, leftover)
    if MEL.get_material_expressions(m):
        raise RuntimeError("Old expressions remain in " + m.get_name())


def add_custom(material, x, y, code, inputs, desc, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3):
    """inputs: [(输入名, 源节点, 源输出名)]，顺序即引脚顺序。"""
    c = node(material, unreal.MaterialExpressionCustom, x, y, code=code, output_type=output_type, description=desc)
    pins = []
    for name, _, _ in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", name)
        pins.append(pin)
    c.set_editor_property("inputs", pins)
    for name, source, output in inputs:
        connect(source, c, name, output)
    return c


def vector_param(m, name, x, y, default=(0, 0, 0, 0), group=None):
    v = node(m, unreal.MaterialExpressionVectorParameter, x, y,
             parameter_name=name, default_value=unreal.LinearColor(*default))
    if group:
        v.set_editor_property("group", group)
    return v


def scalar_param(m, name, x, y, default, group=None):
    s = node(m, unreal.MaterialExpressionScalarParameter, x, y, parameter_name=name, default_value=default)
    if group:
        s.set_editor_property("group", group)
    return s


def add_exposure_output(master, custom, configured_weight):
    """用公开原生节点消费实际 GPU 曝光；不改变主光或原 Toon 运算。"""
    configured_weight = exposure_weight(configured_weight)
    inverse = node(master, unreal.MaterialExpressionEyeAdaptationInverse, 700, 0)
    weight = scalar_param(master, EXPOSURE_PARAMETER, 450, 220, configured_weight, "Display")
    weight.set_editor_property("slider_min", 0.0)
    weight.set_editor_property("slider_max", 1.0)
    if tuple(str(n) for n in MEL.get_material_expression_input_names(inverse)) != EXPOSURE_INPUTS:
        raise RuntimeError("Native exposure input contract differs")
    connect(custom, inverse, EXPOSURE_INPUTS[0])
    connect(weight, inverse, EXPOSURE_INPUTS[1])
    if not MEL.connect_material_property(inverse, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("Could not connect native exposure output")
    return inverse, weight


def compile_surface(master):
    """真实编译诊断与指令数同时有效才允许调用方保存。失败保留脏包和错误。"""
    errors = MEL.recompile_material(master)
    if errors is None or errors:
        raise RuntimeError("Surface compilation failed or returned no diagnostics: " + repr(errors))
    stats = MEL.get_statistics(master)
    if stats.num_pixel_shader_instructions <= 0 or stats.num_vertex_shader_instructions <= 0:
        raise RuntimeError("M_Pyrois_Toon has no valid compiled pixel/vertex shader")
    unreal.log("PYRIOS_TOON_STATS ps=%s vs=%s" % (stats.num_pixel_shader_instructions,
                                               stats.num_vertex_shader_instructions))


def _toon_snapshot(custom):
    """同次调用内保护原程序及全部输入的完整原生表达式连接。"""
    return (custom.get_editor_property("code"),
            tuple(p.export_text() for p in custom.get_editor_property("inputs")))


def add_project_surface(master, custom, plan):
    """只接入项目输出/瞬态场景预览；不改原185输入顺序，不创建渲染通道。"""
    outputs = []
    for name, kind in SURFACE_OUTPUTS:
        output = unreal.CustomOutput()
        output.set_editor_property("output_name", name)
        output.set_editor_property("output_type", getattr(unreal.CustomMaterialOutputType, kind))
        outputs.append(output)
    custom.set_editor_property("additional_outputs", outputs)
    cpd = [scalar_param(master, name, -2900, index * 80, 0.0, "Scene Preview")
           for index, name in enumerate(PREVIEW_DATA_NAMES)]
    for index, parameter in enumerate(cpd):
        parameter.set_editor_property("use_custom_primitive_data", True)
        parameter.set_editor_property("primitive_data_index", index)
    vectors = []
    for offset in (1, 4):
        vectors.append(add_custom(master, -2600, offset * 80, "return float3(X, Y, Z);",
            [(name, cpd[offset + index], "") for index, name in enumerate(("X", "Y", "Z"))],
            "Scene preview vector"))
    preview = dict(zip((*PREVIEW_LIGHT, *PREVIEW_SCALARS), (*vectors, cpd[7], cpd[8])))
    links = MEL.get_inputs_for_material_expression(master, custom)
    for item, source in zip(plan["inputs"], links):
        name = item["name"]
        if name not in preview:
            continue
        kind = unreal.CustomMaterialOutputType.CMOT_FLOAT3 if name in PREVIEW_LIGHT else unreal.CustomMaterialOutputType.CMOT_FLOAT1
        selector = add_custom(master, -1600, list(preview).index(name) * 200, PREVIEW_CODE,
            [("MaterialValue", source, "RGB" if name in PREVIEW_LIGHT else ""),
             ("PreviewValue", preview[name], ""), ("PreviewValid", cpd[0], "")],
            "Scene preview: " + name, kind)
        connect(selector, custom, name)
    display = [(name, scalar_param(master, name, 300, index * 160, plan["display"][name], "Display"), "")
               for index, name in enumerate(DISPLAY_PARAMETERS)]
    composite = add_custom(master, 650, 0, COMPOSITE_CODE,
        [("MainColor", custom, "return"), ("RimRaw", custom, "RimRaw")] + display,
        "Project Toon Composite")
    if not MEL.connect_material_property(composite, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("Could not connect project surface output")
    return composite


def apply_surface_pipeline(save_result=False):
    """既有单Master的精确迁移；默认只准备候选，保存必须由调用者明确授权。"""
    if unreal.EditorLevelLibrary.get_pie_worlds(True):
        raise RuntimeError("Surface migration requires non-PIE")
    dirty = list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    if dirty:
        raise RuntimeError("Surface migration refuses dirty packages")
    plan = load_plan(JSON_DIR, GLOBALS_PATH)
    master = EAL.load_asset(OUT + "/M_Pyrois_Toon")
    if not isinstance(master, unreal.Material):
        raise RuntimeError("Missing existing Toon Master")
    if master.get_path_name() != OUT + "/M_Pyrois_Toon.M_Pyrois_Toon" or master.get_editor_property("shading_model") != unreal.MaterialShadingModel.MSM_UNLIT:
        raise RuntimeError("Existing Toon Master identity/shading model differs")
    custom = MEL.get_material_property_input_node(master, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if not isinstance(custom, unreal.MaterialExpressionCustom):
        raise RuntimeError("Expected the accepted direct-output graph; exposure migration is a separate choice")
    old_code = custom.get_editor_property("code")
    if hashlib.sha256(old_code.encode("utf-8")).hexdigest() != "36ad1a7aaa6cf2ea0f6fcb75b23d4ea8ff861b23e4b065b0a4a80d80b2098543":
        raise RuntimeError("Accepted Toon code identity differs; target unchanged")
    from verify_pyrios_renderer import verify_surface_graph, verify_project_surface_graph
    verify_surface_graph(master, plan, legacy_direct=True, expected_code=old_code)
    if len(MEL.get_material_expressions(master)) != len(plan["inputs"]) + 1 or custom.get_editor_property("additional_outputs"):
        raise RuntimeError("Accepted Toon graph structure differs; target unchanged")
    original = _toon_snapshot(custom)[1]
    # 所有正式包编辑前保留精确磁盘副本；同名备份不得覆盖失败/用户历史。
    source_file = Path(unreal.Paths.project_content_dir()) / "Characters/Player/Pyrios/Materials/Generated/M_Pyrois_Toon.uasset"
    source_bytes = source_file.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != "3ed65ddfa2431f8d5210219f877636e6643932788e1875d032618608635331de":
        raise RuntimeError("Accepted saved Toon package changed; no graph mutation")
    import datetime
    backup = Path(unreal.Paths.project_saved_dir()) / "AssetBackups" / ("PyriosSurface_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source_file, backup / source_file.name)
    if (backup / source_file.name).read_bytes() != source_bytes:
        raise RuntimeError("Toon package backup verification failed; no graph mutation")
    touch(master)
    custom.set_editor_property("code", HLSL_PATH.read_text(encoding="utf-8"))
    add_project_surface(master, custom, plan)
    verify_project_surface_graph(master, plan)
    compile_surface(master)
    verify_project_surface_graph(master, plan)
    # 原图pin连接允许仅四个主光增加预览选择，其余连接逐字段保持。
    after = _toon_snapshot(custom)[1]
    if any(a != b for item, a, b in zip(plan["inputs"], original, after)
           if item["kind"] not in ("component_vector", "component_scalar")):
        raise RuntimeError("Migration changed a non-light source input")
    final_dirty = list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    if any(p.get_path_name() != OUT + "/M_Pyrois_Toon" for p in final_dirty):
        raise RuntimeError("Migration produced foreign dirty packages; no save")
    if source_file.read_bytes() != source_bytes:
        raise RuntimeError("Toon disk changed while preparing graph; no save")
    if save_result:
        save(master)
    unreal.log("PYRIOS_SURFACE_PIPELINE " + json.dumps(dict(saved=save_result, supported_light="Directional", occlusion="CharacterTrace")))
    return master


def apply_master_exposure(configured_weight):
    """只迁移／配置既有主材质，严格图核对和编译后只保存该一个包。"""
    configured_weight = exposure_weight(configured_weight)
    if unreal.EditorLevelLibrary.get_pie_worlds(True):
        raise RuntimeError("Single Master exposure update requires a non-PIE editor")
    dirty = list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    dirty += list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    if dirty:
        raise RuntimeError("Single Master exposure update requires a clean editor: " + repr([p.get_path_name() for p in dirty]))
    plan = load_plan(JSON_DIR, GLOBALS_PATH)
    master = EAL.load_asset(OUT + "/M_Pyrois_Toon")
    if not isinstance(master, unreal.Material) or master.get_path_name() != OUT + "/M_Pyrois_Toon.M_Pyrois_Toon":
        raise RuntimeError("Single Master target is missing or has the wrong identity/type")
    if (master.get_editor_property("shading_model") != unreal.MaterialShadingModel.MSM_UNLIT
            or master.get_editor_property("material_domain") != unreal.MaterialDomain.MD_SURFACE):
        raise RuntimeError("Single Master target must remain an Unlit surface")
    from verify_pyrios_renderer import verify_surface_graph, verify_project_surface_graph
    output = MEL.get_material_property_input_node(master, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    legacy = isinstance(output, unreal.MaterialExpressionCustom)
    shading_output = output if legacy else MEL.get_inputs_for_material_expression(master, output)[0]
    project = isinstance(shading_output, unreal.MaterialExpressionCustom) and shading_output.get_editor_property("code") == COMPOSITE_CODE
    verify_graph = verify_project_surface_graph if project else verify_surface_graph
    if project:
        custom = verify_graph(master, plan)
    else:
        original_code = shading_output.get_editor_property("code")
        # 已验旧图允许完成其显式曝光选择；不把新多输出源码灌进旧单输出接口。
        if hashlib.sha256(original_code.encode()).hexdigest() != "36ad1a7aaa6cf2ea0f6fcb75b23d4ea8ff861b23e4b065b0a4a80d80b2098543":
            raise RuntimeError("Legacy exposure source is not the accepted frozen program")
        custom = verify_graph(master, plan, legacy_direct=legacy, expected_code=original_code)
    before = _toon_snapshot(custom)
    expressions = tuple(MEL.get_material_expressions(master))
    expected_count = len(plan["inputs"]) + ((19 if legacy else 21) if project else (1 if legacy else 3))
    if len(expressions) != expected_count:
        raise RuntimeError("Unexpected existing surface expressions; refusing to rebuild or remove them")
    touch(master)
    if legacy:
        added = add_exposure_output(master, shading_output, configured_weight)
        expected_expressions = set(expressions) | set(added)
    else:
        weight = MEL.get_inputs_for_material_expression(master, output)[1]
        weight.set_editor_property("default_value", configured_weight)
        expected_expressions = set(expressions)
    if (_toon_snapshot(custom) != before
            or set(MEL.get_material_expressions(master)) != expected_expressions):
        raise RuntimeError("Exposure update changed the original Toon graph")
    if project:
        verify_graph(master, plan, configured_weight)
    else:
        verify_graph(master, plan, configured_weight, expected_code=original_code)
    compile_surface(master)
    # 编译可能更新图；仍需保护原185输入，并核对实际曝光输出后才能保存。
    if (_toon_snapshot(custom) != before
            or set(MEL.get_material_expressions(master)) != expected_expressions):
        raise RuntimeError("Compilation changed the original Toon graph")
    if project:
        verify_graph(master, plan, configured_weight)
    else:
        verify_graph(master, plan, configured_weight, expected_code=original_code)
    dirty_after = list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    dirty_after += list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    if any(p.get_path_name() != OUT + "/M_Pyrois_Toon" for p in dirty_after):
        raise RuntimeError("Compilation produced a non-target dirty package; preserving the editor without saving")
    save(master)
    unreal.log("PYRIOS_MASTER_EXPOSURE_SAVED %s=%s" % (EXPOSURE_PARAMETER, configured_weight))
    return master


def build_main(plan, configured_weight):
    configured_weight = exposure_weight(configured_weight)
    m = asset("M_Pyrois_Toon", unreal.MaterialFactoryNew(), unreal.Material)
    clear_expressions(m)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    m.set_editor_property("two_sided", False)
    MEL.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    MEL.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS)
    builtins = {
        "UV": (node(m, unreal.MaterialExpressionTextureCoordinate, -2400, -600), ""),
        "UV2": (node(m, unreal.MaterialExpressionTextureCoordinate, -2400, -700, coordinate_index=2), ""),
        "Time": (node(m, unreal.MaterialExpressionTime, -2400, -500), ""),
        "WorldPos": (node(m, unreal.MaterialExpressionWorldPosition, -2400, -400), ""),
        "CameraPos": (node(m, unreal.MaterialExpressionCameraPositionWS, -2400, -300), ""),
        "VCol": (node(m, unreal.MaterialExpressionVertexColor, -2400, -200), ""),
        "FaceSign": (node(m, unreal.MaterialExpressionTwoSidedSign, -2400, -100), ""),
    }
    inputs, y = [], 0
    for item in plan["inputs"]:
        name, kind = item["name"], item["kind"]
        if kind == "texture":
            tex_name, sampler = slot_inputs(plan)[name]
            src = node(m, unreal.MaterialExpressionTextureObjectParameter, -2000, y, parameter_name=name,
                       group="Textures", texture=EAL.load_asset(ROOT + "/Texture/" + tex_name),
                       sampler_type=getattr(unreal.MaterialSamplerType, sampler))
            inputs.append((name, src, ""))
        elif kind == "builtin":
            src, out = builtins[name]
            inputs.append((name, src, out))
            continue
        elif kind == "component_vector":
            inputs.append((name, vector_param(m, name, -2000, y, PREVIEW_LIGHT[name], "Light"), "RGBA"))
        elif kind == "component_scalar":
            inputs.append((name, scalar_param(m, name, -2000, y, PREVIEW_SCALARS[name], "Light"), ""))
        else:
            group = {"material": "Material", "global": "Globals", "extra": "Globals"}[kind]
            default = plan["globals"].get(name, (0.0, 0.0, 0.0, 0.0))
            inputs.append((name, vector_param(m, name, -2000, y, default, group), "RGBA"))
        y += 90
    custom = add_custom(m, -900, 0, HLSL_PATH.read_text(encoding="utf-8"), inputs,
                        "NapAvatarStandard CharacterToonDeferred")
    output = add_project_surface(m, custom, plan)
    add_exposure_output(m, output, configured_weight)
    if not all(MEL.get_inputs_for_material_expression(m, custom)):
        raise RuntimeError("Custom node has unconnected inputs")
    from verify_pyrios_renderer import verify_project_surface_graph
    verify_project_surface_graph(m, plan, configured_weight)
    compile_surface(m)
    verify_project_surface_graph(m, plan, configured_weight)
    save(m)
    return m


def build_outline():
    m = asset("M_Pyrois_Outline", unreal.MaterialFactoryNew(), unreal.Material)
    clear_expressions(m)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property("two_sided", True)
    MEL.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    MEL.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS)
    width = scalar_param(m, "OutlineWidth", -700, 0, 0.6)
    normal = node(m, unreal.MaterialExpressionVertexNormalWS, -700, -200)
    multiply = node(m, unreal.MaterialExpressionMultiply, -300, -150)
    connect(normal, multiply, "A")
    connect(width, multiply, "B")
    MEL.connect_material_property(multiply, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    sign = node(m, unreal.MaterialExpressionTwoSidedSign, -700, 250)
    enabled = scalar_param(m, "OutlineOpacity", -700, 350, 1.0)
    opacity = add_custom(m, -300, 250, "float v = (Sign < 0 ? 1.0 : 0.0) * Enabled; return float3(v, v, v);",
                         [("Sign", sign, ""), ("Enabled", enabled, "")], "Back faces only")
    MEL.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    color = vector_param(m, "OutlineColor", -950, 500, (0.025, 0.025, 0.04, 1))
    MEL.connect_material_property(color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    save(m)


def set_instance(main, suffix, plan):
    mi = asset("MI_Pyrois_" + suffix, unreal.MaterialInstanceConstantFactoryNew(), unreal.MaterialInstanceConstant)
    MEL.set_material_instance_parent(mi, main)
    MEL.clear_all_material_instance_parameters(mi)
    textures = {}
    for slot, name in plan["textures"][suffix].items():
        tex = EAL.load_asset(ROOT + "/Texture/" + (name or slot_inputs(plan)[slot][0]))
        textures[slot] = tex
        MEL.set_material_instance_texture_parameter_value(mi, slot, tex)
    vectors = dict(plan["globals"])
    vectors.update(plan["params"][suffix])
    vectors.update(PREVIEW_LIGHT)
    for name, value in vectors.items():
        MEL.set_material_instance_vector_parameter_value(mi, name, unreal.LinearColor(*value))
    for name, value in PREVIEW_SCALARS.items():
        MEL.set_material_instance_scalar_parameter_value(mi, name, value)
    MEL.update_material_instance(mi)
    # 引擎 set_* 的返回值不可靠，统一回读。
    for slot, tex in textures.items():
        got = MEL.get_material_instance_texture_parameter_value(mi, slot)
        if got != tex:
            raise RuntimeError("Readback mismatch %s.%s" % (suffix, slot))
    for name, value in vectors.items():
        got = MEL.get_material_instance_vector_parameter_value(mi, name)
        if any(abs(a - b) > 1e-4 * max(1.0, abs(b)) for a, b in zip((got.r, got.g, got.b, got.a), value)):
            raise RuntimeError("Readback mismatch %s.%s: %s != %s" % (suffix, name, got, value))
    save(mi)


def configure_textures(plan):
    # sRGB 照抄 Unity 导入设置（m_ColorSpace）。N/M/A 打包图另外用 BC7：_LightTex.B 是明暗偏移，
    # 法线贴图的 BC5 压缩会丢掉它；M/A 需要保留 alpha。
    packed = {"Pyrois_%s_%s" % (b, s) for b in ("Body_Map1", "Body_Map2", "Weapon") for s in ("N", "M", "A")}
    for name in plan["texture_names"]:
        tex = EAL.load_asset(ROOT + "/Texture/" + name)
        touch(tex)
        tex.set_editor_property("srgb", plan["texture_srgb"][name])
        if name in packed:
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_BC7)
        save(tex)


def bind_editor_preview_materials(prechecked=False):
    mesh = EAL.load_asset(MESH_PATH)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("Missing Pyrios skeletal mesh: " + MESH_PATH)
    materials = list(mesh.get_editor_property("materials"))
    if not prechecked:
        check_targets_clean({MESH_PATH})
    bound = set()
    for index, slot in enumerate(materials):
        slot_name = str(slot.get_editor_property("material_slot_name"))
        instance_name = SLOT_INSTANCES.get(slot_name)
        if instance_name is None:
            continue
        instance = EAL.load_asset(OUT + "/" + instance_name)
        if not isinstance(instance, unreal.MaterialInstanceConstant):
            raise RuntimeError("Missing Pyrios material instance: " + instance_name)
        slot.set_editor_property("material_interface", instance)
        materials[index] = slot
        bound.add(slot_name)
    if bound != set(SLOT_INSTANCES):
        raise RuntimeError("Pyrios material slots differ from expected: " + str(bound))
    touch(mesh)
    mesh.set_editor_property("materials", materials)
    save(mesh)
    unreal.log("PYRIOS_EDITOR_PREVIEW_MATERIALS " + str(sorted(bound)))


def main(configured_weight=None, master_exposure_only=False, surface_pipeline=False, save_pipeline=False):
    global JOURNAL
    if not surface_pipeline:
        configured_weight = exposure_weight(configured_weight)
    JOURNAL = BuildJournal()
    try:
        if surface_pipeline:
            if configured_weight is not None or master_exposure_only:
                raise ValueError("Surface pipeline preserves current exposure; do not specify exposure options")
            apply_surface_pipeline(save_pipeline)
            return
        if master_exposure_only:
            apply_master_exposure(configured_weight)
            unreal.log("PYRIOS_MASTER_EXPOSURE_OK " + json.dumps(JOURNAL.report("complete")))
            return
        plan = preflight()  # No writes before the complete source/asset/dirty check.
        EAL.make_directory(OUT)
        configure_textures(plan)
        m = build_main(plan, configured_weight)
        build_outline()
        for suffix in SUFFIXES:
            set_instance(m, suffix, plan)
        bind_editor_preview_materials(prechecked=True)
        unreal.log("PYRIOS_MATERIAL_BUILD_OK " + json.dumps(JOURNAL.report("complete")))
    except Exception as error:
        unreal.log_error("PYRIOS_MATERIAL_BUILD_FAILED " + json.dumps(JOURNAL.report("failed", str(error))))
        raise
    finally:
        JOURNAL = None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exposure-weight", type=float, help="明确指定曝光抵偿权重0..1，不采用隐式默认")
    parser.add_argument("--master-exposure-only", action="store_true", help="只迁移／配置既有主材质，不运行整批生成")
    parser.add_argument("--surface-pipeline", action="store_true", help="只准备既有单Master项目合成候选，保持曝光")
    parser.add_argument("--save-pipeline", action="store_true", help="显式保存上述单Master，须另有生产窗口")
    args = parser.parse_args()
    if args.save_pipeline and not args.surface_pipeline:
        parser.error("--save-pipeline requires --surface-pipeline")
    main(args.exposure_weight, args.master_exposure_only, args.surface_pipeline, args.save_pipeline)
