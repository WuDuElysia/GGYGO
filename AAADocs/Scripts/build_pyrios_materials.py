"""Run with UnrealEditor-Cmd -run=pythonscript -script=<this file> -AllowCommandletRendering.

生成 Pyrios 表面材质：
- M_Pyrois_Toon：Unlit，单个 Custom 节点承载 nap_avatar_toon.hlsl（NapAvatarStandard
  CharacterToonDeferred 像素逻辑的逐行移植），主光由 UGGYGOCharacterRenderComponent 写入
  KeyLightDirectionWS / KeyLightColor / SceneLightStrength / KeyLightVisibility；
- MI_Pyrois_Body_1 / Body_2 / Weapon01：参数来自材质 JSON 与 Pyrios_Toon_Globals.json；
- M_Pyrois_Outline：运行时反面扩张描边；
- 把三个 MI 绑定到骨骼网格的默认槽位作为编辑器预览。
可重复运行；完整预检通过前不写资产。
"""
import json
import sys
from pathlib import Path
import unreal

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyrios_material_plan import BuildJournal, SLOT_INSTANCES, SUFFIXES, load_plan


ROOT = "/Game/Characters/Player/Pyrios/Materials"
OUT = ROOT + "/Generated"
JSON_DIR = Path(__file__).resolve().parents[2] / "Content/Characters/Player/Pyrios/Materials"
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


# 编辑器静态预览的主光；运行时由组件覆盖。方向为 UE 世界空间指向光源。
PREVIEW_LIGHT = {"KeyLightDirectionWS": (0.35, 0.25, 0.9, 0.0), "KeyLightColor": (1.0, 1.0, 1.0, 1.0)}
PREVIEW_SCALARS = {"SceneLightStrength": 1.0, "KeyLightVisibility": 1.0}
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


def build_main(plan):
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
    if not MEL.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("Could not connect emissive output")
    if not all(MEL.get_inputs_for_material_expression(m, custom)):
        raise RuntimeError("Custom node has unconnected inputs")
    MEL.recompile_material(m)
    save(m)
    stats = MEL.get_statistics(m)
    unreal.log("PYRIOS_TOON_STATS ps=%s vs=%s" % (stats.num_pixel_shader_instructions,
                                                  stats.num_vertex_shader_instructions))
    if stats.num_pixel_shader_instructions <= 0:
        raise RuntimeError("M_Pyrois_Toon has no compiled pixel shader")
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


def main():
    global JOURNAL
    JOURNAL = BuildJournal()
    try:
        plan = preflight()  # No writes before the complete source/asset/dirty check.
        EAL.make_directory(OUT)
        configure_textures(plan)
        m = build_main(plan)
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
    main()
