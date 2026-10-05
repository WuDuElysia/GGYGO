"""Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>.

重建 Pyrios 身体 FX：
  1. 导入缺失的 FX 贴图，并把本材质用到的 FX 贴图设为线性采样；
  2. 生成通用 master 材质 M_FX_DissolveMaskLayers（三层 Custom 节点 + 预乘 over 合成）；
  3. 生成 MI_Pyrois_Body_FX，按 pyrios_fx_plan 的换算结果填参数；
  4. 绑定到骨骼网格的 MAT_Pyrois_Body_FX01 槽位（资产默认材质）。

可重复运行：每次清空 master 节点后重建，MI 参数整体覆盖。
目标包在编辑器里有未保存修改时拒绝写入。
"""
import json
import sys
from pathlib import Path
import unreal

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from pyrios_fx_plan import LAYER_COUNT, TEXTURE_SLOTS, VECTOR_PARAMS, load_plan

MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary

PYRIOS = "/Game/Characters/Player/Pyrios"
TEX_DIR = PYRIOS + "/Materials/Texture"
MI_DIR = PYRIOS + "/Materials/Generated"
MI_NAME = "MI_Pyrois_Body_FX"
MASTER_DIR = "/Game/Characters/Shared/FX/Materials"
MASTER_NAME = "M_FX_DissolveMaskLayers"
MESH_PATH = PYRIOS + "/Avatar_Male_Size03_Pyrois_Model"
FX_SLOT = "MAT_Pyrois_Body_FX01"
CHARACTER_BP = "/Game/BP/Character/Player/BP_PC_Pyrios"
MATERIAL_JSON_DIR = HERE.parent / "Assets/Pyrios/Rendering/UnityMaterials"
SOURCE_PNG_DIR = Path(r"F:\AnimeStudio\Exports\ZZZ\Avatar_Male_Size03_Pyrois_Model\FX\Player\Textures")
HLSL_PATH = HERE / "fx_dissolve_mask_layer.hlsl"


VECTOR_DEFAULTS = {name: (0.0, 0.0, 0.0, 0.0) for name in VECTOR_PARAMS}
VECTOR_DEFAULTS.update({k: (1.0, 1.0, 0.0, 0.0) for k in
                        ("MainST", "MaskST", "DissolveST", "DissolveRampST", "RampST", "DistST", "Dist2ST")})
VECTOR_DEFAULTS.update({"WrapA": (3.0, 3.0, 3.0, 3.0), "WrapB": (3.0, 3.0, 3.0, 3.0),
                        "AlphaCfg": (1.0, 1.0, 1.0, 0.0), "CustomColor": (0.0, 0.0, 0.0, 1.0)})


class Report:
    def __init__(self):
        self.saved, self.imported, self.notes = [], [], []

    def save(self, obj):
        path = obj.get_path_name().split(".")[0]
        if not EAL.save_loaded_asset(obj, only_if_is_dirty=False):
            raise RuntimeError("保存失败: " + path)
        self.saved.append(path)


REPORT = Report()


def check_clean(paths):
    dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts = sorted(dirty.intersection(paths))
    if conflicts:
        raise RuntimeError("目标包有未保存修改，拒绝覆盖: " + str(conflicts))


def preflight(plan):
    missing_png = [n for n in plan["textures"]
                   if not EAL.does_asset_exist(TEX_DIR + "/" + n) and not (SOURCE_PNG_DIR / (n + ".png")).is_file()]
    if missing_png:
        raise RuntimeError("贴图既未导入也找不到源 PNG: " + str(missing_png))
    mesh = EAL.load_asset(MESH_PATH)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("缺少骨骼网格: " + MESH_PATH)
    slots = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("materials")]
    if slots.count(FX_SLOT) != 1:
        raise RuntimeError("网格应恰好有一个 %s 槽位: %s" % (FX_SLOT, slots))
    for path, cls in ((MASTER_DIR + "/" + MASTER_NAME, unreal.Material),
                      (MI_DIR + "/" + MI_NAME, unreal.MaterialInstanceConstant)):
        if EAL.does_asset_exist(path) and not isinstance(EAL.load_asset(path), cls):
            raise RuntimeError("已有同名资产但类型不符: " + path)
    targets = {TEX_DIR + "/" + n for n in plan["textures"]}
    targets |= {MASTER_DIR + "/" + MASTER_NAME, MI_DIR + "/" + MI_NAME, MESH_PATH}
    check_clean(targets)


def import_textures(plan):
    tasks = []
    for name in plan["textures"]:
        if EAL.does_asset_exist(TEX_DIR + "/" + name):
            continue
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(SOURCE_PNG_DIR / (name + ".png")))
        task.set_editor_property("destination_path", TEX_DIR)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("save", False)
        tasks.append((name, task))
    if tasks:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t for _, t in tasks])
    for name, _ in tasks:
        if not isinstance(EAL.load_asset(TEX_DIR + "/" + name), unreal.Texture2D):
            raise RuntimeError("贴图导入失败: " + name)
        REPORT.imported.append(name)


def configure_textures(plan):
    # sRGB 照抄 Unity 导入设置（m_ColorSpace）。寻址由 master 里的共享采样器决定，这里不改贴图自身的 Address 设置。
    for name in plan["textures"]:
        tex = EAL.load_asset(TEX_DIR + "/" + name)
        tex.set_editor_property("srgb", plan["srgb"][name])
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
        tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_EFFECTS)
        REPORT.save(tex)


def slot_defaults(plan):
    """未赋值槽位的占位贴图：取任一层在该槽使用的贴图，保证与槽的 sRGB 采样类型一致（不一致会编译失败）。"""
    result = {}
    for slot in TEXTURE_SLOTS:
        names = [layer["textures"][slot] for layer in plan["layers"] if layer["textures"][slot]]
        if not names:
            raise RuntimeError("没有任何层使用贴图槽 " + slot)
        result[slot] = EAL.load_asset(TEX_DIR + "/" + names[0])
    return result


def node(material, cls, x, y, **props):
    result = MEL.create_material_expression(material, cls, x, y)
    for key, value in props.items():
        result.set_editor_property(key, value)
    return result


def connect(src, src_out, dst, dst_in):
    if not MEL.connect_material_expressions(src, src_out, dst, dst_in):
        raise RuntimeError("连线失败: %s.%s -> %s" % (src.get_name(), src_out, dst_in))


def custom(material, x, y, code, inputs, desc):
    """inputs: [(输入名, 源节点, 源输出名)]，顺序即 Custom 节点引脚顺序。"""
    c = node(material, unreal.MaterialExpressionCustom, x, y, code=code, description=desc,
             output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    pins = []
    for name, _, _ in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property("input_name", name)
        pins.append(pin)
    c.set_editor_property("inputs", pins)
    for name, src, out in inputs:
        connect(src, out, c, name)
    return c


def build_master(plan):
    path = MASTER_DIR + "/" + MASTER_NAME
    EAL.make_directory(MASTER_DIR)
    m = EAL.load_asset(path) if EAL.does_asset_exist(path) else \
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(MASTER_NAME, MASTER_DIR, unreal.Material,
                                                                unreal.MaterialFactoryNew())
    if m is None:
        raise RuntimeError("无法创建 " + path)
    MEL.delete_all_material_expressions(m)
    for leftover in MEL.get_material_expressions(m):
        MEL.delete_material_expression(m, leftover)
    if MEL.get_material_expressions(m):
        raise RuntimeError("master 旧节点未清空")
    m.set_editor_property("material_domain", unreal.MaterialDomain.MD_SURFACE)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ALPHA_COMPOSITE)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)
    m.set_editor_property("use_translucency_vertex_fog", False)
    MEL.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)

    defaults = slot_defaults(plan)
    code = HLSL_PATH.read_text(encoding="utf-8")
    uv = node(m, unreal.MaterialExpressionTextureCoordinate, -2600, -400)
    time = node(m, unreal.MaterialExpressionTime, -2600, -300, ignore_pause=True)
    scene_z = node(m, unreal.MaterialExpressionSceneDepth, -2600, -200)
    pixel_z = node(m, unreal.MaterialExpressionPixelDepth, -2600, -100)
    face = node(m, unreal.MaterialExpressionTwoSidedSign, -2600, 0)

    layers = []
    for i in range(1, LAYER_COUNT + 1):
        group = "Layer%d" % i
        base_y = (i - 1) * 2600
        inputs = []
        for k, slot in enumerate(TEXTURE_SLOTS):
            t = node(m, unreal.MaterialExpressionTextureObjectParameter, -2000, base_y + k * 140,
                     parameter_name="L%d_%s" % (i, slot), group=group,
                     sampler_type=(unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if plan["slot_srgb"].get(slot, False)
                                   else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
                     sampler_source=unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS,
                     texture=defaults[slot])
            inputs.append((slot, t, ""))
        for k, name in enumerate(VECTOR_PARAMS):
            v = node(m, unreal.MaterialExpressionVectorParameter, -1500, base_y + k * 90,
                     parameter_name="L%d_%s" % (i, name), group=group,
                     default_value=unreal.LinearColor(*VECTOR_DEFAULTS[name]))
            inputs.append((name, v, "RGBA"))
        inputs += [("UV", uv, ""), ("Time", time, ""), ("SceneZ", scene_z, ""),
                   ("PixelZ", pixel_z, ""), ("FaceSign", face, "")]
        layers.append(custom(m, -900, base_y, code, inputs, "FX layer %d" % i))

    comp_code = ("float4 c = L1;\n"
                 "c = L2 + c * (1.0 - L2.a);\n"
                 "c = L3 + c * (1.0 - L3.a);\n"
                 "return c;")
    comp = custom(m, -400, 0, comp_code, [("L%d" % (i + 1), layers[i], "") for i in range(LAYER_COUNT)],
                  "Premultiplied over, layer 1 drawn first")
    rgb = node(m, unreal.MaterialExpressionComponentMask, -150, -80, r=True, g=True, b=True, a=False)
    alpha = node(m, unreal.MaterialExpressionComponentMask, -150, 80, r=False, g=False, b=False, a=True)
    connect(comp, "", rgb, "")
    connect(comp, "", alpha, "")
    scale = node(m, unreal.MaterialExpressionScalarParameter, -150, -220,
                 parameter_name="EmissiveScale", group="Global", default_value=1.0)
    mul = node(m, unreal.MaterialExpressionMultiply, 50, -100)
    connect(rgb, "", mul, "A")
    connect(scale, "", mul, "B")
    if not MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("Emissive 连线失败")
    if not MEL.connect_material_property(alpha, "", unreal.MaterialProperty.MP_OPACITY):
        raise RuntimeError("Opacity 连线失败")
    customs = [e for e in MEL.get_material_expressions(m) if isinstance(e, unreal.MaterialExpressionCustom)]
    if len(customs) != LAYER_COUNT + 1:
        raise RuntimeError("master 的 Custom 节点数为 %d，应为 %d" % (len(customs), LAYER_COUNT + 1))
    for c in customs:
        if not all(MEL.get_inputs_for_material_expression(m, c)):
            raise RuntimeError("Custom 节点存在未连接输入: " + c.get_editor_property("description"))
    MEL.recompile_material(m)
    REPORT.save(m)
    stats = MEL.get_statistics(m)
    unreal.log("PYRIOS_BODY_FX_MASTER_STATS ps=%s vs=%s samplers=%s textures=%s" % (
        stats.num_pixel_shader_instructions, stats.num_vertex_shader_instructions,
        stats.num_samplers, stats.num_pixel_texture_samples))
    return m


def build_instance(master, plan):
    path = MI_DIR + "/" + MI_NAME
    mi = EAL.load_asset(path) if EAL.does_asset_exist(path) else \
        unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            MI_NAME, MI_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if mi is None:
        raise RuntimeError("无法创建 " + path)
    MEL.set_material_instance_parent(mi, master)
    MEL.clear_all_material_instance_parameters(mi)
    defaults = slot_defaults(plan)
    for i, layer in enumerate(plan["layers"], 1):
        for slot, tex_name in layer["textures"].items():
            tex = EAL.load_asset(TEX_DIR + "/" + tex_name) if tex_name else defaults[slot]
            if not isinstance(tex, unreal.Texture2D):
                raise RuntimeError("缺少贴图 " + str(tex_name))
            # 引擎的 set_* 返回值恒为 False，写入结果统一在下面回读核对。
            MEL.set_material_instance_texture_parameter_value(mi, "L%d_%s" % (i, slot), tex)
        for name, value in layer["vectors"].items():
            MEL.set_material_instance_vector_parameter_value(mi, "L%d_%s" % (i, name), unreal.LinearColor(*value))
    MEL.update_material_instance(mi)
    verify_instance(mi, plan, defaults)
    REPORT.save(mi)
    return mi


def verify_instance(mi, plan, defaults):
    for i, layer in enumerate(plan["layers"], 1):
        for slot, tex_name in layer["textures"].items():
            got = MEL.get_material_instance_texture_parameter_value(mi, "L%d_%s" % (i, slot))
            want = tex_name or defaults[slot].get_name()
            if got is None or got.get_name() != want:
                raise RuntimeError("回读不符 L%d_%s: %s != %s" % (i, slot, got and got.get_name(), want))
        for name, value in layer["vectors"].items():
            got = MEL.get_material_instance_vector_parameter_value(mi, "L%d_%s" % (i, name))
            if any(abs(a - b) > 1e-4 * max(1.0, abs(b)) for a, b in zip((got.r, got.g, got.b, got.a), value)):
                raise RuntimeError("回读不符 L%d_%s: %s != %s" % (i, name, got, value))


def bind_mesh(mi):
    mesh = EAL.load_asset(MESH_PATH)
    materials = list(mesh.get_editor_property("materials"))
    for index, slot in enumerate(materials):
        if str(slot.get_editor_property("material_slot_name")) == FX_SLOT:
            slot.set_editor_property("material_interface", mi)
            materials[index] = slot
    mesh.set_editor_property("materials", materials)
    bound = [s.get_editor_property("material_interface") for s in mesh.get_editor_property("materials")
             if str(s.get_editor_property("material_slot_name")) == FX_SLOT]
    if len(bound) != 1 or bound[0] != mi:
        raise RuntimeError("槽位 %s 回读不符" % FX_SLOT)
    REPORT.save(mesh)


def report_character_override():
    """角色蓝图若在 Mesh 组件上覆盖了 FX 槽位，资产默认材质不会生效；这里只记录，不改蓝图。"""
    bp = EAL.load_asset(CHARACTER_BP)
    if bp is None:
        REPORT.notes.append("未找到 " + CHARACTER_BP)
        return
    cdo = unreal.get_default_object(bp.generated_class())
    comp = cdo.get_editor_property("mesh")
    overrides = [m.get_path_name() if m else None for m in comp.get_editor_property("override_materials")]
    REPORT.notes.append("BP mesh override_materials=" + str(overrides))


def main():
    plan = load_plan(MATERIAL_JSON_DIR)
    try:
        preflight(plan)  # 完整检查通过前不写任何资产
        import_textures(plan)
        configure_textures(plan)
        master = build_master(plan)
        mi = build_instance(master, plan)
        bind_mesh(mi)
        report_character_override()
        unreal.log("PYRIOS_BODY_FX_BUILD_OK " + json.dumps(
            {"order": plan["order"], "imported": REPORT.imported, "saved": REPORT.saved,
             "notes": REPORT.notes}, ensure_ascii=False))
    except Exception as error:
        unreal.log_error("PYRIOS_BODY_FX_BUILD_FAILED " + json.dumps(
            {"error": str(error), "imported": REPORT.imported, "saved": REPORT.saved}, ensure_ascii=False))
        raise


if __name__ == "__main__":
    main()
