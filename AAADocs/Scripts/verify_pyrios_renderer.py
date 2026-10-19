"""核对 Pyrios 材质；--compile 重编译表面材质并标脏。

--body-fx 单独只读采样正式身体 FX 的活动输出图、MI 最终参数和纹理设置。
在独立标准 Editor 中使用 -ExecutePythonScript="<本文件> --body-fx"，
原生读回写入日志，不保存资产、不重编译、不修改参数。读不到的字段明确记为未知；
采样完成不表示源 Shader 运行变体或视觉根因已验证。
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path
import unreal

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyrios_material_plan import (EXPOSURE_INPUTS, EXPOSURE_PARAMETER, PREVIEW_LIGHT,
                                 PREVIEW_SCALARS, SLOT_INSTANCES, SUFFIXES,
                                 SURFACE_OUTPUTS, PREVIEW_DATA_NAMES, DISPLAY_PARAMETERS,
                                 COMPOSITE_CODE, PREVIEW_CODE, exposure_weight, load_plan)

ROOT = "/Game/Characters/Player/Pyrios/Materials"
JSON_DIR = Path(__file__).resolve().parents[1] / "Assets/Pyrios/Rendering/UnityMaterials"
GLOBALS_PATH = Path(__file__).resolve().parents[1] / "Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json"
HLSL_PATH = Path(__file__).resolve().with_name("nap_avatar_toon.hlsl")


def configure_scene_light_component(component, reference_intensity, intensity_response, output_scale, max_strength, *, apply=False):
    """原生字段接缝。默认只预检；写调用需实际 BP/角色窗口，且本函数不编译/保存 BP。"""
    from pyrios_material_plan import scene_light_settings
    expected = scene_light_settings(reference_intensity, intensity_response, output_scale, max_strength)
    if not isinstance(component, unreal.GGYGOCharacterRenderComponent):
        raise RuntimeError("Expected the generic character rendering component")
    before = {name: component.get_editor_property(name) for name in expected}
    if apply:
        for name, value in expected.items():
            component.set_editor_property(name, value)
        actual = {name: component.get_editor_property(name) for name in expected}
        if any(actual[name] != value if isinstance(value, bool) else not math.isfinite(actual[name]) or abs(actual[name] - value) > 1e-5 * max(1, abs(value))
               for name, value in expected.items()):
            raise RuntimeError("Scene light component readback differs; no BP save")
    return dict(object=component.get_path_name(), before=before, expected=expected, applied=apply,
                supported="Directional", occlusion="CharacterTrace", compiled=False, saved=False)


def close(color, value):
    return all(abs(a - b) <= 1e-4 * max(1.0, abs(b))
               for a, b in zip((color.r, color.g, color.b, color.a), value))


def same_asset(asset, package):
    """Compare complete object identity, including its package, not its short name."""
    return asset is not None and asset.get_path_name() == package + "." + package.rsplit("/", 1)[1]


def custom_input_output_index(pin, source):
    """从原生结构导出读连接；CustomInput.Input 的 Python 字段不可直接读取。

    GetInputNodeOutputNameForMaterialExpression 只返回相同来源的第一条连接，不能区分
    Main/Rim 两条边。这里核对完整来源身份及 RGB mask，再返回实际 OutputIndex。
    未知导出布局明确拒绝，不把缺失索引当作 0。
    """
    quoted = r'("(?:[^"\\]|\\.)*")'
    pattern = (r'\(InputName=' + quoted + r',Input=\(Expression=' + quoted
               + r',OutputIndex=(-?\d+),InputName=' + quoted
               + r',Mask=(-?\d+),MaskR=(-?\d+),MaskG=(-?\d+),MaskB=(-?\d+),MaskA=(-?\d+)\)\)')
    exported = pin.export_text()
    match = re.fullmatch(pattern, exported)
    assert match, "Unknown CustomInput connection export: " + exported
    name, expression, index, _, *mask = match.groups()
    assert json.loads(name) == str(pin.get_editor_property("input_name")), "CustomInput export name differs"
    assert json.loads(expression) == "/Script/Engine.MaterialExpressionCustom'" + source.get_path_name() + "'", "CustomInput exported source differs"
    mask = tuple(map(int, mask))
    assert all(v in (0, 1) for v in mask) and (mask[0] == 0 or mask == (1, 1, 1, 1, 0)), "CustomInput must consume full RGB"
    return int(index)


def verify_surface_graph(master, plan, expected_exposure=None, *, legacy_direct=False, expected_code=None):
    """核对原程序及曝光输出；旧直接输出只用于明确的迁移前检查，不自动接受。"""
    mel = unreal.MaterialEditingLibrary
    output = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if legacy_direct:
        assert expected_exposure is None, "Legacy graph cannot declare an exposure weight"
        assert isinstance(output, unreal.MaterialExpressionCustom), "Legacy Toon must connect directly to Emissive"
        assert EXPOSURE_PARAMETER not in [str(n) for n in mel.get_scalar_parameter_names(master)], "Exposure parameter collision"
        custom = output
    else:
        assert isinstance(output, unreal.MaterialExpressionEyeAdaptationInverse), "Native exposure output required"
        assert tuple(str(n) for n in mel.get_material_expression_input_names(output)) == EXPOSURE_INPUTS, "Exposure input contract differs"
        links = mel.get_inputs_for_material_expression(master, output)
        assert len(links) == 2, "Exposure output must have two inputs"
        custom, weight = links
        assert isinstance(custom, unreal.MaterialExpressionCustom), "Exposure must consume the original Toon Custom"
        assert isinstance(weight, unreal.MaterialExpressionScalarParameter), "Exposure alpha must use an editable scalar"
        assert str(weight.get_editor_property("parameter_name")) == EXPOSURE_PARAMETER, "Wrong exposure parameter name"
        assert not weight.get_editor_property("use_custom_primitive_data"), "Exposure must remain an MI parameter"
        actual = exposure_weight(weight.get_editor_property("default_value"))
        if expected_exposure is not None:
            assert abs(actual - exposure_weight(expected_exposure)) <= 1e-6, "Exposure default differs from explicit configuration"
        assert [str(n) for n in mel.get_scalar_parameter_names(master)].count(EXPOSURE_PARAMETER) == 1, "Exposure scalar must be unique"
        named_weights = [n for n in mel.get_material_expressions(master)
                         if isinstance(n, unreal.MaterialExpressionScalarParameter)
                         and str(n.get_editor_property("parameter_name")) == EXPOSURE_PARAMETER]
        assert named_weights == [weight], "Duplicate exposure expression"
        assert weight.get_editor_property("slider_min") == 0.0 and weight.get_editor_property("slider_max") == 1.0, "Exposure slider range differs"
        prefix = master.get_path_name() + ":"
        assert all(n.get_path_name().startswith(prefix) for n in (output, custom, weight)), "Exposure references another material graph"
    assert custom.get_editor_property("code") == (expected_code if expected_code is not None else HLSL_PATH.read_text(encoding="utf-8")), "Toon code differs from source"
    assert not master.get_editor_property("use_material_attributes"), "Material Attributes bypass the expected surface output"
    inputs = custom.get_editor_property("inputs")
    assert [str(i.get_editor_property("input_name")) for i in inputs] == [i["name"] for i in plan["inputs"]], "Toon input contract differs"
    connections = mel.get_inputs_for_material_expression(master, custom)
    assert len(connections) == len(plan["inputs"]) and all(connections), "Toon inputs must all be connected"
    for item, connection in zip(plan["inputs"], connections):
        cls = {"component_vector": unreal.MaterialExpressionVectorParameter,
               "component_scalar": unreal.MaterialExpressionScalarParameter}.get(item["kind"])
        if cls:
            assert isinstance(connection, cls), (item["name"], "wrong light parameter type")
            assert str(connection.get_editor_property("parameter_name")) == item["name"], (item["name"], "wrong light parameter name")
    return custom


def verify_project_surface_graph(master, plan, expected_exposure=None):
    """核对项目合成、源输出以及九槽非 PIE 预览；不把 Custom 输出视作原 MRT。"""
    mel = unreal.MaterialEditingLibrary
    assert master.get_editor_property("material_domain") == unreal.MaterialDomain.MD_SURFACE
    assert master.get_editor_property("shading_model") == unreal.MaterialShadingModel.MSM_UNLIT
    assert not master.get_editor_property("use_material_attributes")
    output = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    exposure_nodes = []
    if isinstance(output, unreal.MaterialExpressionEyeAdaptationInverse):
        assert tuple(str(n) for n in mel.get_material_expression_input_names(output)) == EXPOSURE_INPUTS
        composite, weight = mel.get_inputs_for_material_expression(master, output)
        assert isinstance(weight, unreal.MaterialExpressionScalarParameter)
        assert str(weight.get_editor_property("parameter_name")) == EXPOSURE_PARAMETER
        assert not weight.get_editor_property("use_custom_primitive_data")
        value = exposure_weight(weight.get_editor_property("default_value"))
        if expected_exposure is not None:
            assert abs(value - exposure_weight(expected_exposure)) <= 1e-6
        exposure_nodes = [output, weight]
    else:
        assert expected_exposure is None, "Direct project output has no exposure compensation node"
        composite = output
    assert isinstance(composite, unreal.MaterialExpressionCustom)
    assert composite.get_editor_property("output_type") == unreal.CustomMaterialOutputType.CMOT_FLOAT3
    assert composite.get_editor_property("code") == COMPOSITE_CODE
    assert [str(p.get_editor_property("input_name")) for p in composite.get_editor_property("inputs")] == ["MainColor", "RimRaw", *DISPLAY_PARAMETERS]
    links = mel.get_inputs_for_material_expression(master, composite)
    assert len(links) == 4 and links[0] == links[1], "Composite must consume two outputs of the same source program"
    custom = links[0]
    assert isinstance(custom, unreal.MaterialExpressionCustom)
    assert custom.get_editor_property("output_type") == unreal.CustomMaterialOutputType.CMOT_FLOAT3
    assert custom.get_editor_property("code") == HLSL_PATH.read_text(encoding="utf-8")
    assert [(str(o.get_editor_property("output_name")), o.get_editor_property("output_type"))
            for o in custom.get_editor_property("additional_outputs")] == [
                (name, getattr(unreal.CustomMaterialOutputType, kind)) for name, kind in SURFACE_OUTPUTS]
    for pin, index in zip(composite.get_editor_property("inputs")[:2], (0, 1)):
        assert custom_input_output_index(pin, custom) == index, "Main/Rim output index differs"
    for name, expression in zip(DISPLAY_PARAMETERS, links[2:]):
        assert isinstance(expression, unreal.MaterialExpressionScalarParameter)
        assert str(expression.get_editor_property("parameter_name")) == name
        assert not expression.get_editor_property("use_custom_primitive_data")
        value = expression.get_editor_property("default_value")
        assert value >= 0 and abs(value - plan["display"][name]) <= 1e-6
    nodes = list(mel.get_material_expressions(master))
    cpd = {}
    for node in nodes:
        if isinstance(node, (unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter)) and node.get_editor_property("use_custom_primitive_data"):
            index = node.get_editor_property("primitive_data_index")
            if index < len(PREVIEW_DATA_NAMES):
                assert isinstance(node, unreal.MaterialExpressionScalarParameter)
                assert index not in cpd, "CPD indices overlap"
                assert str(node.get_editor_property("parameter_name")) == PREVIEW_DATA_NAMES[index]
                assert node.get_editor_property("default_value") == 0
                cpd[index] = node
    assert set(cpd) == set(range(9)), "Incomplete preview CPD contract"
    inputs = custom.get_editor_property("inputs")
    assert [str(i.get_editor_property("input_name")) for i in inputs] == [i["name"] for i in plan["inputs"]]
    connections = mel.get_inputs_for_material_expression(master, custom)
    assert len(connections) == len(inputs) and all(connections)
    for item, connection in zip(plan["inputs"], connections):
        if item["kind"] not in ("component_vector", "component_scalar"):
            continue
        assert isinstance(connection, unreal.MaterialExpressionCustom) and connection.get_editor_property("code") == PREVIEW_CODE
        assert connection.get_editor_property("output_type") == (unreal.CustomMaterialOutputType.CMOT_FLOAT3
            if item["kind"] == "component_vector" else unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        assert [str(p.get_editor_property("input_name")) for p in connection.get_editor_property("inputs")] == ["MaterialValue", "PreviewValue", "PreviewValid"]
        original, preview, valid = mel.get_inputs_for_material_expression(master, connection)
        cls = unreal.MaterialExpressionVectorParameter if item["kind"] == "component_vector" else unreal.MaterialExpressionScalarParameter
        assert isinstance(original, cls) and str(original.get_editor_property("parameter_name")) == item["name"]
        assert not original.get_editor_property("use_custom_primitive_data") and valid == cpd[0]
        name = item["name"]
        if name in PREVIEW_SCALARS:
            assert preview == cpd[7 if name == "SceneLightStrength" else 8]
        else:
            assert isinstance(preview, unreal.MaterialExpressionCustom) and preview.get_editor_property("code") == "return float3(X, Y, Z);"
            start = 1 if name == "KeyLightDirectionWS" else 4
            assert list(mel.get_inputs_for_material_expression(master, preview)) == [cpd[start + i] for i in range(3)]
    assert len(nodes) == len(plan["inputs"]) + 19 + len(exposure_nodes), "Unexpected project graph nodes"
    prefix = master.get_path_name() + ":"
    assert all(n.get_path_name().startswith(prefix) for n in nodes), "Foreign graph reference"
    return custom


def verify(recompile=False, expected_exposure=None, project_pipeline=False, expected_light_scalars=None):
    # 原始导出预览默认值与项目静态 MI 的明确配置分别验证；不从 actual 值猜预期。
    light_scalars = PREVIEW_SCALARS
    if expected_light_scalars is not None:
        assert project_pipeline, "项目主光配置只适用于项目表面管线"
        assert set(expected_light_scalars) == set(PREVIEW_SCALARS), "必须提供完整主光标量契约"
        assert all(isinstance(value, (int, float)) and not isinstance(value, bool)
                   and math.isfinite(value) and value >= 0 for value in expected_light_scalars.values()), "主光标量必须有限且非负"
        assert expected_light_scalars["KeyLightVisibility"] <= 1, "可见性必须在 0..1 范围"
        light_scalars = dict(expected_light_scalars)
    mel = unreal.MaterialEditingLibrary
    eal = unreal.EditorAssetLibrary
    for name in ("M_Pyrois_Toon", "M_Pyrois_Outline", "MI_Pyrois_Body_1", "MI_Pyrois_Body_2", "MI_Pyrois_Weapon01"):
        path = ROOT + "/Generated/" + name
        assert eal.does_asset_exist(path), path
        material = eal.load_asset(path)
        assert material is not None
        expected_class = unreal.Material if name.startswith("M_") else unreal.MaterialInstanceConstant
        assert isinstance(material, expected_class), (name, "wrong asset type")
        if isinstance(material, unreal.Material):
            assert mel.has_material_usage(material, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
            assert material.get_editor_property("material_domain") == unreal.MaterialDomain.MD_SURFACE, (name, "surface domain")
            assert material.get_editor_property("shading_model") == unreal.MaterialShadingModel.MSM_UNLIT, (name, "Unlit required")
            if recompile:
                errors = mel.recompile_material(material)
                assert errors is not None and not errors, (name, "compile errors or missing diagnostics", errors)
                assert mel.get_statistics(material).num_pixel_shader_instructions > 0, name
                unreal.log("PYRIOS_VERIFY_COMPILED " + name)
        unreal.log("PYRIOS_VERIFY_ASSET " + path)

    plan = load_plan(JSON_DIR, GLOBALS_PATH)
    master = eal.load_asset(ROOT + "/Generated/M_Pyrois_Toon")
    (verify_project_surface_graph if project_pipeline else verify_surface_graph)(master, plan, expected_exposure)
    mesh = eal.load_asset("/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model")
    assert mesh is not None
    slots = mesh.get_editor_property("materials")
    names = [str(slot.get_editor_property("material_slot_name")) for slot in slots]
    assert all(names.count(name) == 1 for name in SLOT_INSTANCES), ("missing/duplicate target mesh slot", names)
    for slot in slots:
        slot_name = str(slot.get_editor_property("material_slot_name"))
        if slot_name in SLOT_INSTANCES:
            actual = slot.get_editor_property("material_interface")
            assert same_asset(actual, ROOT + "/Generated/" + SLOT_INSTANCES[slot_name]), (slot_name, actual)
    unreal.log("PYRIOS_VERIFY_EDITOR_PREVIEW_OK")

    for name, srgb in plan["texture_srgb"].items():
        tex = eal.load_asset(ROOT + "/Texture/" + name)
        assert tex.get_editor_property("srgb") == srgb, (name, srgb)

    for suffix in SUFFIXES:
        mi = eal.load_asset(ROOT + "/Generated/MI_Pyrois_" + suffix)
        assert isinstance(mi, unreal.MaterialInstanceConstant), (suffix, "material instance required")
        assert same_asset(mi.get_editor_property("parent"), ROOT + "/Generated/M_Pyrois_Toon"), (suffix, "wrong parent")
        overrides = mi.get_editor_property("base_property_overrides")
        assert not overrides.get_editor_property("override_shading_model") or overrides.get_editor_property("shading_model") == unreal.MaterialShadingModel.MSM_UNLIT, (suffix, "Lit instance override")
        for slot, name in plan["textures"][suffix].items():
            actual = mel.get_material_instance_texture_parameter_value(mi, slot)
            default = next(plan["textures"][s][slot] for s in SUFFIXES if plan["textures"][s][slot])
            assert same_asset(actual, ROOT + "/Texture/" + (name or default)), (suffix, slot, actual)
        expected = dict(plan["globals"])
        expected.update(plan["params"][suffix])
        expected.update(PREVIEW_LIGHT)
        for name, value in expected.items():
            assert close(mel.get_material_instance_vector_parameter_value(mi, name), value), (suffix, name)
        for name, value in light_scalars.items():
            actual = mel.get_material_instance_scalar_parameter_value(mi, name)
            assert abs(actual - value) <= 1e-4, (suffix, name, actual)
        actual_exposure = exposure_weight(mel.get_material_instance_scalar_parameter_value(mi, EXPOSURE_PARAMETER))
        unreal.log("PYRIOS_VERIFY_EXPOSURE %s %s" % (suffix, actual_exposure))
        unreal.log("PYRIOS_VERIFY_PARAMS %s %d" % (suffix, len(expected)))

    unreal.log("PYRIOS_VERIFY_OK")
    unreal.log("PYRIOS_VERIFY_COMPILATION " + ("CHECKED" if recompile else "NOT_RUN"))


def body_fx_emit(stage, **values):
    unreal.log("PYRIOS_BODY_FX_READBACK " + json.dumps(dict(stage=stage, **values), ensure_ascii=False))


def body_fx_property(obj, name, unknown):
    """只读反射字段；失败保留对象、字段和原生原因，不补预期值。"""
    try:
        return obj.get_editor_property(name)
    except Exception as error:
        unknown.append(dict(object=str(obj), field=name, reason=str(error)))
        return None


def body_fx_api(name, args, unknown):
    method = getattr(unreal.MaterialEditingLibrary, name, None)
    if method is None:
        unknown.append(dict(api=name, reason="当前 Python 未暴露该公开 API"))
        return None
    try:
        return method(*args)
    except Exception as error:
        unknown.append(dict(api=name, objects=[str(a) for a in args], reason=str(error)))
        return None


def body_fx_input(link, unknown):
    """读取公开反射的 FExpressionInput，保留输出索引及分量 mask。"""
    if link is None:
        return None
    source = body_fx_property(link, "expression", unknown)
    result = dict(source=source.get_path_name() if source else None)
    for name in ("output_index", "mask", "mask_r", "mask_g", "mask_b", "mask_a"):
        result[name] = body_fx_property(link, name, unknown)
    return result


def body_fx_node(master, expression, unknown):
    """记录真实节点和连接；仅输出链可达节点进入采样。"""
    names = body_fx_api("get_material_expression_input_names", (expression,), unknown)
    sources = body_fx_api("get_inputs_for_material_expression", (master, expression), unknown)
    outputs = body_fx_api("get_material_expression_output_names", (expression,), unknown)
    result = dict(object=expression.get_path_name(), type=expression.get_class().get_name(),
                  output_names=list(outputs) if outputs is not None else None, inputs=None)
    if names is not None and sources is not None:
        if len(names) != len(sources):
            unknown.append(dict(object=result["object"], reason="原生输入名与连接数组长度不一致"))
        result["inputs"] = [dict(index=i, name=names[i] if i < len(names) else None,
                                 source=s.get_path_name() if s else None) for i, s in enumerate(sources)]

    if isinstance(expression, unreal.MaterialExpressionCustom):
        for name in ("code", "description"):
            result[name] = body_fx_property(expression, name, unknown)
        result["output_type"] = str(body_fx_property(expression, "output_type", unknown))
        pins = body_fx_property(expression, "inputs", unknown)
        result["custom_inputs"] = None if pins is None else [
            dict(name=str(body_fx_property(pin, "input_name", unknown)),
                 link=body_fx_input(body_fx_property(pin, "input", unknown), unknown)) for pin in pins]
        includes = body_fx_property(expression, "include_file_paths", unknown)
        result["include_file_paths"] = list(includes) if includes is not None else None
        extra_outputs = body_fx_property(expression, "additional_outputs", unknown)
        defines = body_fx_property(expression, "additional_defines", unknown)
        result["additional_outputs"] = None if extra_outputs is None else [
            dict(name=str(body_fx_property(p, "output_name", unknown)),
                 type=str(body_fx_property(p, "output_type", unknown))) for p in extra_outputs]
        result["additional_defines"] = None if defines is None else [
            dict(name=body_fx_property(p, "define_name", unknown),
                 value=body_fx_property(p, "define_value", unknown)) for p in defines]
    elif isinstance(expression, unreal.MaterialExpressionComponentMask):
        result["mask"] = {k: body_fx_property(expression, k, unknown) for k in ("r", "g", "b", "a")}
        result["link"] = body_fx_input(body_fx_property(expression, "input", unknown), unknown)
    elif isinstance(expression, unreal.MaterialExpressionMultiply):
        result["links"] = {k: body_fx_input(body_fx_property(expression, k, unknown), unknown) for k in ("a", "b")}
        result["unconnected_constants"] = {k: body_fx_property(expression, k, unknown) for k in ("const_a", "const_b")}
    elif isinstance(expression, (unreal.MaterialExpressionVectorParameter, unreal.MaterialExpressionScalarParameter,
                                 unreal.MaterialExpressionTextureObjectParameter)):
        result["parameter_name"] = str(body_fx_property(expression, "parameter_name", unknown))
        if isinstance(expression, unreal.MaterialExpressionTextureObjectParameter):
            result["sampler_type"] = str(body_fx_property(expression, "sampler_type", unknown))
            result["sampler_source"] = str(body_fx_property(expression, "sampler_source", unknown))
    elif isinstance(expression, unreal.MaterialExpressionTextureCoordinate):
        result["uv"] = {k: body_fx_property(expression, k, unknown)
                        for k in ("coordinate_index", "u_tiling", "v_tiling", "un_mirror_u", "un_mirror_v")}
    elif isinstance(expression, unreal.MaterialExpressionTime):
        result["time"] = {k: body_fx_property(expression, k, unknown) for k in ("ignore_pause", "period")}
    return result, sources


def body_fx_parameters(instance, unknown):
    """原生枚举后读最终 GLOBAL 参数；不对缺失名字调用零值 getter。"""
    for kind in ("scalar", "vector", "texture"):
        names = body_fx_api("get_%s_parameter_names" % kind, (instance,), unknown)
        body_fx_emit("parameter_names", kind=kind, names=[str(n) for n in names] if names is not None else None)
        if names is None:
            continue
        for name in names:
            value = body_fx_api("get_material_instance_%s_parameter_value" % kind, (instance, name), unknown)
            if kind == "vector" and value is not None:
                value = [value.r, value.g, value.b, value.a]
            elif kind == "texture" and value is not None:
                texture = value
                value = dict(object=texture.get_path_name(), type=texture.get_class().get_name(),
                             srgb=body_fx_property(texture, "srgb", unknown),
                             address_x=str(body_fx_property(texture, "address_x", unknown)),
                             address_y=str(body_fx_property(texture, "address_y", unknown)))
            body_fx_emit("parameter", kind=kind, name=str(name), value=value)


def verify_body_fx():
    """有限活动图读回；不验证原游戏 variant／PropertyBlock 或当前 GPU 结果。"""
    def dirty_packages():
        packages = list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        packages += list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
        return tuple(sorted(p.get_path_name() for p in packages))

    if unreal.EditorLevelLibrary.get_pie_worlds(True):
        raise RuntimeError("BodyFX 只读采样拒绝在 PIE 中运行")
    before = dirty_packages()
    if before:
        raise RuntimeError("BodyFX 只读采样拒绝已有脏包: " + repr(before))
    unknown = []
    try:
        master_path = "/Game/Characters/Shared/FX/Materials/M_FX_DissolveMaskLayers"
        instance_path = ROOT + "/Generated/MI_Pyrois_Body_FX"
        master = unreal.EditorAssetLibrary.load_asset(master_path)
        instance = unreal.EditorAssetLibrary.load_asset(instance_path)
        if not isinstance(master, unreal.Material) or not same_asset(master, master_path):
            raise RuntimeError("BodyFX 正式 Master 缺失或身份不符: " + master_path)
        if not isinstance(instance, unreal.MaterialInstanceConstant) or not same_asset(instance, instance_path):
            raise RuntimeError("BodyFX 正式 MI 缺失或身份不符: " + instance_path)
        parent = instance.get_editor_property("parent")
        flags = {k: body_fx_property(master, k, unknown)
                 for k in ("two_sided", "use_material_attributes", "use_translucency_vertex_fog")}
        flags.update({k: str(body_fx_property(master, k, unknown))
                      for k in ("material_domain", "blend_mode", "shading_model")})
        overrides = instance.get_editor_property("base_property_overrides")
        base_overrides = {k: body_fx_property(overrides, k, unknown) for k in
                          ("override_blend_mode", "override_shading_model", "override_two_sided", "two_sided")}
        base_overrides.update({k: str(body_fx_property(overrides, k, unknown)) for k in ("blend_mode", "shading_model")})
        body_fx_emit("assets", master=master.get_path_name(), instance=instance.get_path_name(),
                     parent=parent.get_path_name() if parent else None, parent_matches=(parent == master),
                     master_flags=flags, instance_base_overrides=base_overrides)
        queue = []
        properties = [("Emissive", unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                      ("Opacity", unreal.MaterialProperty.MP_OPACITY)]
        if flags["use_material_attributes"]:
            properties.append(("MaterialAttributes", unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES))
        for name, prop in properties:
            source = body_fx_api("get_material_property_input_node", (master, prop), unknown)
            output = body_fx_api("get_material_property_input_node_output_name", (master, prop), unknown)
            body_fx_emit("output", name=name, source=source.get_path_name() if source else None,
                         source_output_name=output, use_material_attributes=flags["use_material_attributes"])
            if source is not None:
                queue.append(source)
        visited = set()
        custom_count = 0
        while queue:
            expression = queue.pop()
            path = expression.get_path_name()
            if path in visited:
                continue
            visited.add(path)
            record, sources = body_fx_node(master, expression, unknown)
            body_fx_emit("node", **record)
            if isinstance(expression, unreal.MaterialExpressionCustom):
                custom_count += 1
            if sources is not None:
                queue.extend(s for s in sources if s is not None)
        body_fx_parameters(instance, unknown)
        body_fx_emit("sampled", reachable_nodes=len(visited), reachable_custom_nodes=custom_count,
                     sampling_status="partial" if unknown else "complete", unknown=unknown,
                     limits="仅磁盘加载资产的活动图和 GLOBAL 参数；未编译、未验原游戏运行变体/PropertyBlock、未验 GPU/视觉")
    finally:
        after = dirty_packages()
        body_fx_emit("dirty", before=before, after=after, unchanged=(after == before))
        if after != before:
            raise RuntimeError("BodyFX 只读采样出现脏包变化，未保存或丢弃: " + repr(after))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--compile", action="store_true", help="显式重编译表面材质并标脏")
    mode.add_argument("--body-fx", action="store_true", help="仅原生只读采样正式身体 FX，不重编译或保存")
    parser.add_argument("--exposure-weight", type=float, help="可选核对明确配置的Master权重；省略时只读实际值，不指定默认")
    parser.add_argument("--project-pipeline", action="store_true", help="核对主体项目合成及非 PIE 预览新接口；历史图不能冒充此接口")
    args = parser.parse_args()
    if args.body_fx:
        if args.exposure_weight is not None:
            parser.error("--body-fx 不消费表面曝光配置")
        verify_body_fx()
    else:
        verify(recompile=args.compile, expected_exposure=args.exposure_weight, project_pipeline=args.project_pipeline)
