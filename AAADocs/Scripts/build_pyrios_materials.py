"""Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>.

Builds editable UE assets from the already imported Pyrios textures and the
AnimeStudio material JSON. Safe to rerun: it updates Generated assets and
binds their instances to the Pyrios skeletal mesh for editor previews.
"""
import json
from pathlib import Path
import unreal


ROOT = "/Game/Characters/Player/Pyrios/Materials"
OUT = ROOT + "/Generated"
JSON_DIR = Path(__file__).resolve().parents[2] / "Content/Characters/Player/Pyrios/Materials"
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary


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
    result = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if result is None:
        result = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, OUT, asset_class, factory)
    if result is None:
        raise RuntimeError("Could not create " + path)
    return result


def add_custom(material, x, y, code, input_nodes, desc):
    c = node(material, unreal.MaterialExpressionCustom, x, y,
             code=code, output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3, description=desc)
    inputs = []
    for name in input_nodes:
        i = unreal.CustomInput()
        i.set_editor_property("input_name", name)
        inputs.append(i)
    c.set_editor_property("inputs", inputs)
    for name, source in input_nodes.items():
        if isinstance(source, tuple):
            connect(source[0], c, name, source[1])
        else:
            connect(source, c, name)
    return c


def vector_param(m, name, y, default=(1, 1, 1, 1)):
    return node(m, unreal.MaterialExpressionVectorParameter, -950, y,
                parameter_name=name, default_value=unreal.LinearColor(*default))


def scalar_param(m, name, y, default):
    return node(m, unreal.MaterialExpressionScalarParameter, -700, y,
                parameter_name=name, default_value=default)


def texture_param(m, name, y, sample_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR):
    tex = node(m, unreal.MaterialExpressionTextureSampleParameter2D, -1150, y,
               parameter_name=name, sampler_type=sample_type)
    # A valid default is required before the instance supplies its texture.
    suffix = {"MainTex": "D", "LightTex": "N", "OtherDataTex": "M", "OtherDataTex2": "A"}[name]
    default = EAL.load_asset(ROOT + "/Texture/Pyrois_Body_Map1_" + suffix)
    tex.set_editor_property("texture", default)
    return tex


def build_main():
    m = asset("M_Pyrois_Toon", unreal.MaterialFactoryNew(), unreal.Material)
    MEL.delete_all_material_expressions(m)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", False)
    MEL.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    MEL.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS)
    d = texture_param(m, "MainTex", -900)
    n = texture_param(m, "LightTex", -650, unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    packed = texture_param(m, "OtherDataTex", -400, unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    aux = texture_param(m, "OtherDataTex2", -150, unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    bump = scalar_param(m, "BumpScale", 50, 1.0)
    ysign = scalar_param(m, "NormalYSign", 175, 1.0)
    decode = add_custom(m, -600, 0,
        "float2 xy = (LightTex.rg * 2.0 - 1.0) * float2(BumpScale, BumpScale * NormalYSign); return normalize(float3(xy, sqrt(saturate(1.0 - dot(xy, xy)))));",
        {"LightTex": n, "BumpScale": bump, "NormalYSign": ysign}, "Decode packed tangent normal, retaining B as ramp bias")
    normal = node(m, unreal.MaterialExpressionTransform, -250, 0,
                  transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
                  transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    connect(decode, normal, "")
    camera = node(m, unreal.MaterialExpressionCameraVectorWS, -850, 250)
    inputs = {
        "Albedo": d, "LightTex": n, "Packed": (packed, "RGBA"), "Aux": aux,
        "NormalWS": normal, "CameraWS": camera,
        "LightDirection": vector_param(m, "KeyLightDirectionWS", 350, (0.35, 0.25, 0.9, 0)),
        "LightColor": vector_param(m, "KeyLightColor", 500),
        "Visibility": scalar_param(m, "KeyLightVisibility", 650, 1.0),
        "EmissionColor": vector_param(m, "EmissionColor", 800, (0, 1, 2, 1)),
        "EmissionStrength": scalar_param(m, "EmissionStrength", 950, 0),
        "RimStrength": scalar_param(m, "RimStrength", 1100, 0.15),
        "SpecStrength": scalar_param(m, "SpecStrength", 1250, 0.1),
        "SpecPower": scalar_param(m, "SpecPower", 1400, 40),
        "MatCapStrength": scalar_param(m, "MatCapStrength", 1550, 0),
        "MatCapStrength2": scalar_param(m, "MatCapStrength2", 1625, 0),
        "CameraRight": vector_param(m, "CameraRightWS", 1700, (0, 1, 0, 0)),
        "CameraUp": vector_param(m, "CameraUpWS", 1850, (0, 0, 1, 0)),
    }
    matcap = node(m, unreal.MaterialExpressionTextureObjectParameter, -950, 2000,
                  parameter_name="MatCapTex")
    matcap.set_editor_property("texture", EAL.load_asset(ROOT + "/Texture/Eff_Matcap_125"))
    inputs["MatCapTex"] = matcap
    matcap2 = node(m, unreal.MaterialExpressionTextureObjectParameter, -950, 2100,
                   parameter_name="MatCapTex2")
    matcap2.set_editor_property("texture", EAL.load_asset(ROOT + "/Texture/Eff_MatCap_075"))
    inputs["MatCapTex2"] = matcap2
    inputs["MatCapTint"] = vector_param(m, "MatCapTint", 1900)
    inputs["MatCapTint2"] = vector_param(m, "MatCapTint2", 2000)
    for i in range(1, 6):
        inputs["Shallow%d" % i] = vector_param(m, "ShallowColor%d" % i, 2150 + i * 135, (0.95, 0.95, 0.95, 1))
        inputs["Shadow%d" % i] = vector_param(m, "ShadowColor%d" % i, 3000 + i * 135, (0.65, 0.65, 0.7, 1))
    code = r'''
float3 N = normalize(NormalWS);
float3 L = normalize(LightDirection.rgb);
float3 V = normalize(CameraWS);
float bias = (LightTex.b * 2.0 - 1.0) * 0.22;
float ramp = saturate(dot(N, L) * 0.5 + 0.5 + bias);
float band = smoothstep(0.32, 0.48, ramp);
float id = saturate(Packed.r);
float3 shallow = id < 0.2 ? Shallow1.rgb : (id < 0.4 ? Shallow2.rgb : (id < 0.6 ? Shallow3.rgb : (id < 0.8 ? Shallow4.rgb : Shallow5.rgb)));
float3 shadow = id < 0.2 ? Shadow1.rgb : (id < 0.4 ? Shadow2.rgb : (id < 0.6 ? Shadow3.rgb : (id < 0.8 ? Shadow4.rgb : Shadow5.rgb)));
float3 diffuse = lerp(shadow, shallow, band * saturate(Visibility));
float3 H = normalize(L + V);
float spec = pow(saturate(dot(N, H)), max(2.0, SpecPower)) * Packed.b * SpecStrength;
float rim = pow(1.0 - saturate(dot(N, V)), 3.0) * RimStrength;
float2 mcUV = float2(dot(N, CameraRight.rgb), dot(N, CameraUp.rgb)) * 0.5 + 0.5;
float3 mc = Texture2DSample(MatCapTex, MatCapTexSampler, mcUV).rgb * Packed.a * MatCapStrength * MatCapTint.rgb;
mc += Texture2DSample(MatCapTex2, MatCapTex2Sampler, mcUV).rgb * Packed.a * MatCapStrength2 * MatCapTint2.rgb;
float3 glow = EmissionColor.rgb * Aux.b * EmissionStrength;
return Albedo.rgb * diffuse * LightColor.rgb + spec * LightColor.rgb + rim * LightColor.rgb + mc + glow;
'''
    custom = add_custom(m, 100, 0, code, inputs, "Pyrios toon ramp, specular, rim, MatCap and emission")
    if not MEL.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("Could not connect emissive output")
    errors = MEL.recompile_material(m)
    if errors:
        raise RuntimeError("Toon material failed to compile: " + "; ".join(errors))
    EAL.save_loaded_asset(m)
    return m


def build_outline():
    m = asset("M_Pyrois_Outline", unreal.MaterialFactoryNew(), unreal.Material)
    MEL.delete_all_material_expressions(m)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property("two_sided", True)
    MEL.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    MEL.set_base_material_usage(m, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS)
    width = scalar_param(m, "OutlineWidth", 0, 0.6)
    normal = node(m, unreal.MaterialExpressionVertexNormalWS, -700, -200)
    multiply = node(m, unreal.MaterialExpressionMultiply, -300, -150)
    connect(normal, multiply, "A")
    connect(width, multiply, "B")
    MEL.connect_material_property(multiply, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    sign = node(m, unreal.MaterialExpressionTwoSidedSign, -700, 250)
    enabled = scalar_param(m, "OutlineOpacity", 350, 1.0)
    opacity = add_custom(m, -300, 250, "float v = (Sign < 0 ? 1.0 : 0.0) * Enabled; return float3(v, v, v);",
                         {"Sign": sign, "Enabled": enabled}, "Back faces only")
    MEL.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    color = vector_param(m, "OutlineColor", 500, (0.025, 0.025, 0.04, 1))
    MEL.connect_material_property(color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    errors = MEL.recompile_material(m)
    if errors:
        raise RuntimeError("Outline material failed to compile: " + "; ".join(errors))
    EAL.save_loaded_asset(m)


def set_instance(main, suffix):
    mi = asset("MI_Pyrois_" + suffix, unreal.MaterialInstanceConstantFactoryNew(), unreal.MaterialInstanceConstant)
    MEL.set_material_instance_parent(mi, main)
    data = json.loads((JSON_DIR / ("MAT_Pyrois_" + suffix + ".json")).read_text(encoding="utf-8"))
    p = data["m_SavedProperties"]
    for source, target in (("_MainTex", "MainTex"), ("_LightTex", "LightTex"),
                           ("_OtherDataTex", "OtherDataTex"), ("_OtherDataTex2", "OtherDataTex2")):
        texture_name = p["m_TexEnvs"][source]["m_Texture"]["Name"]
        tex = EAL.load_asset(ROOT + "/Texture/" + texture_name)
        if tex is None:
            raise RuntimeError("Missing texture " + texture_name)
        MEL.set_material_instance_texture_parameter_value(mi, target, tex)
    colors = p["m_Colors"]
    for i in range(1, 6):
        end = "" if i == 1 else str(i)
        for source, target in (("_ShallowColor", "ShallowColor"), ("_ShadowColor", "ShadowColor")):
            c = colors[source + end]
            MEL.set_material_instance_vector_parameter_value(mi, target + str(i),
                unreal.LinearColor(c["r"], c["g"], c["b"], c["a"]))
    c = colors["_EmissionColor"]
    MEL.set_material_instance_vector_parameter_value(mi, "EmissionColor", unreal.LinearColor(c["r"], c["g"], c["b"], 1))
    floats = p["m_Floats"]
    for source, target in (("_Emission", "EmissionStrength"), ("_SpecIntensity", "SpecStrength"),
                           ("_RimGlow", "RimStrength")):
        MEL.set_material_instance_scalar_parameter_value(mi, target, float(floats.get(source, 0)))
    matcap_settings = {
        "Body_1": ("Eff_Matcap_125", 0.3, "Eff_MatCap_075", 0.12),
        "Body_2": ("Eff_Matcap_125", 0.18, "Eff_MatCap_070", 0.05),
        "Weapon01": ("Eff_Matcap_125", 0.4, "Eff_MatCap_019", 0.15),
    }
    first, strength, second, strength2 = matcap_settings[suffix]
    for param, texname in (("MatCapTex", first), ("MatCapTex2", second)):
        MEL.set_material_instance_texture_parameter_value(mi, param, EAL.load_asset(ROOT + "/Texture/" + texname))
    enabled = 1 if floats.get("_MatCap", 0) else 0
    MEL.set_material_instance_scalar_parameter_value(mi, "MatCapStrength", strength * enabled)
    MEL.set_material_instance_scalar_parameter_value(mi, "MatCapStrength2", strength2 * enabled)
    for source, target in (("_MatCapColorTint", "MatCapTint"), ("_MatCapColorTint2", "MatCapTint2")):
        c = colors.get(source, {"r": 1, "g": 1, "b": 1, "a": 1})
        MEL.set_material_instance_vector_parameter_value(mi, target, unreal.LinearColor(c["r"], c["g"], c["b"], c["a"]))
    MEL.set_material_instance_scalar_parameter_value(mi, "RimStrength", 0.15 * float(floats.get("_RimGlow", 0)))
    MEL.set_material_instance_scalar_parameter_value(mi, "BumpScale", float(floats.get("_BumpScale", 1.0)))
    EAL.save_loaded_asset(mi)


def configure_packed_textures():
    # _LightTex.B is diffuse bias, so normal-map BC5 compression would erase it.
    # The M/A maps also need linear sampling and their alpha channel intact.
    for body in ("Body_Map1", "Body_Map2", "Weapon"):
        for suffix in ("N", "M", "A"):
            tex = EAL.load_asset(ROOT + "/Texture/Pyrois_" + body + "_" + suffix)
            if tex is None:
                raise RuntimeError("Missing packed texture for " + body + suffix)
            tex.set_editor_property("srgb", False)
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_BC7)
            EAL.save_loaded_asset(tex)


def bind_editor_preview_materials():
    mesh_path = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"
    mesh = EAL.load_asset(mesh_path)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("Missing Pyrios skeletal mesh: " + mesh_path)
    materials = list(mesh.get_editor_property("materials"))
    names = {
        "MAT_Pyrois_Body_1": "MI_Pyrois_Body_1",
        "MAT_Pyrois_Body_2": "MI_Pyrois_Body_2",
        "MAT_Pyrois_Weapon01": "MI_Pyrois_Weapon01",
    }
    bound = set()
    for index, slot in enumerate(materials):
        slot_name = str(slot.get_editor_property("material_slot_name"))
        instance_name = names.get(slot_name)
        if instance_name is None:
            continue
        instance = EAL.load_asset(OUT + "/" + instance_name)
        if not isinstance(instance, unreal.MaterialInstanceConstant):
            raise RuntimeError("Missing Pyrios material instance: " + instance_name)
        slot.set_editor_property("material_interface", instance)
        materials[index] = slot
        bound.add(slot_name)
    if bound != set(names):
        raise RuntimeError("Pyrios material slots differ from expected: " + str(bound))
    mesh.set_editor_property("materials", materials)
    if not EAL.save_loaded_asset(mesh):
        raise RuntimeError("Could not save Pyrios skeletal mesh material slots")
    unreal.log("PYRIOS_EDITOR_PREVIEW_MATERIALS " + str(sorted(bound)))


def main():
    EAL.make_directory(OUT)
    configure_packed_textures()
    m = build_main()
    build_outline()
    for suffix in ("Body_1", "Body_2", "Weapon01"):
        set_instance(m, suffix)
    bind_editor_preview_materials()
    unreal.log("PYRIOS_MATERIAL_BUILD_OK")


if __name__ == "__main__":
    main()
