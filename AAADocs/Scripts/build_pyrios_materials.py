"""Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>.

Builds an editable reconstruction from the imported Pyrios textures, material
JSON and the extracted NapAvatarStandard shader. The game lighting pipeline
and active shader variants still need a frame comparison. Safe to rerun:
updates Generated assets and binds their instances to the skeletal mesh.
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
CALIBRATION_PATH = Path(__file__).resolve().parents[1] / "Assets/Pyrios/Rendering/Pyrios_Editor_Calibration.json"
MEL = unreal.MaterialEditingLibrary
EAL = unreal.EditorAssetLibrary
MESH_PATH = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"
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
    plan = load_plan(JSON_DIR, CALIBRATION_PATH)
    packed = {ROOT + "/Texture/Pyrois_" + body + "_" + suffix
              for body in ("Body_Map1", "Body_Map2", "Weapon") for suffix in ("N", "M", "A")}
    required = {ROOT + "/Texture/" + name for name in plan["textures"]} | packed
    required.add(ROOT + "/Texture/Pyrois_Body_Map1_D")  # Master graph's color default.
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
    check_targets_clean(packed | set(outputs) | {MESH_PATH})
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
    view_normal = node(m, unreal.MaterialExpressionTransform, -50, 150,
                       transform_source_type=unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
                       transform_type=unreal.MaterialVectorCoordTransform.TRANSFORM_VIEW)
    connect(normal, view_normal, "")
    camera = node(m, unreal.MaterialExpressionCameraVectorWS, -850, 250)
    inputs = {
        "Albedo": d, "LightTex": n, "Packed": (packed, "RGBA"), "Aux": aux,
        "NormalWS": normal, "ViewNormal": view_normal, "CameraWS": camera,
        "LightDirection": vector_param(m, "KeyLightDirectionWS", 350, (0.35, 0.25, 0.9, 0)),
        "LightColor": vector_param(m, "KeyLightColor", 500),
        "Visibility": scalar_param(m, "KeyLightVisibility", 650, 1.0),
        "SceneLightStrength": scalar_param(m, "SceneLightStrength", 725, 0.65),
        "EmissionColor": vector_param(m, "EmissionColor", 800, (0, 1, 2, 1)),
        "EmissionStrength": scalar_param(m, "EmissionStrength", 950, 0),
        "RimStrength": scalar_param(m, "RimStrength", 1100, 1),
        "SpecStrength": scalar_param(m, "SpecStrength", 1250, 0.1),
        "UseMatCapMask": scalar_param(m, "UseMatCapMask", 1550, 1),
        "Glossiness": scalar_param(m, "Glossiness", 1650, 1),
        "MetallicScale": scalar_param(m, "MetallicScale", 1750, 1),
        "DiffuseGain": scalar_param(m, "DiffuseGain", 1850, 0.6),
        "SpecularGain": scalar_param(m, "SpecularGain", 1950, 0.4),
        "RimGain": scalar_param(m, "RimGain", 2050, 0.15),
        "MatCapGain": scalar_param(m, "MatCapGain", 2150, 0.35),
        "AmbientFloor": scalar_param(m, "AmbientFloor", 2250, 0.08),
        "DiffuseBiasScale": scalar_param(m, "DiffuseBiasScale", 2350, 0.5),
        "RampLow": scalar_param(m, "RampLow", 2450, 0.38),
        "RampHigh": scalar_param(m, "RampHigh", 2550, 0.7),
        "RoughnessFloor": scalar_param(m, "RoughnessFloor", 2650, 0.18),
        "LightingTint": vector_param(m, "LightingTint", 2750, (0.86, 0.92, 1, 1)),
        "RimShadow": vector_param(m, "RimGlowShadowColor", 2850, (0.5, 0.5, 0.5, 1)),
    }
    # The five JSON MatCap slots track material-ID groups, not five full-body
    # additive coats. Empty slots stay disabled in their material instance.
    for i in range(1, 6):
        base_y = 1800 + i * 550
        matcap = node(m, unreal.MaterialExpressionTextureObjectParameter, -1150, base_y,
                      parameter_name="MatCapTex%d" % i)
        matcap.set_editor_property("texture", EAL.load_asset(ROOT + "/Texture/Eff_Matcap_125"))
        inputs["MatCapTex%d" % i] = matcap
        inputs["MatCapTint%d" % i] = vector_param(m, "MatCapTint%d" % i, base_y + 75)
        for name, default, offset in (("ColorBurst", 1, 150), ("AlphaBurst", 1, 225),
                                      ("BlendMode", 0, 300), ("Enabled", 0, 375)):
            key = "MatCap%s%d" % (name, i)
            inputs[key] = scalar_param(m, key, base_y + offset, default)
    for i in range(1, 6):
        inputs["Shallow%d" % i] = vector_param(m, "ShallowColor%d" % i, 2150 + i * 135, (0.95, 0.95, 0.95, 1))
        inputs["Shadow%d" % i] = vector_param(m, "ShadowColor%d" % i, 3000 + i * 135, (0.65, 0.65, 0.7, 1))
        inputs["SpecColor%d" % i] = vector_param(m, "SpecularColor%d" % i, 3800 + i * 135)
        inputs["RimLight%d" % i] = vector_param(m, "RimGlowLightColor%d" % i, 4600 + i * 135, (0.55, 0.55, 0.55, 1))
        inputs["ShadowIntensity%d" % i] = scalar_param(m, "ShadowIntensity%d" % i, 5400 + i * 135, 1)
    code = r'''
float3 N = normalize(NormalWS);
float3 L = normalize(LightDirection.rgb);
float3 V = normalize(CameraWS);
float id = saturate(Packed.r);
// The exported shader reverses floor(id * 5): 1.0 => group 1, 0.7 => group 2.
int tier = clamp(4 - (int)floor(id * 5.0), 0, 4);
float3 shallow = tier == 0 ? Shallow1.rgb : (tier == 1 ? Shallow2.rgb : (tier == 2 ? Shallow3.rgb : (tier == 3 ? Shallow4.rgb : Shallow5.rgb)));
float3 shadow = tier == 0 ? Shadow1.rgb : (tier == 1 ? Shadow2.rgb : (tier == 2 ? Shadow3.rgb : (tier == 3 ? Shadow4.rgb : Shadow5.rgb)));
float3 specColor = tier == 0 ? SpecColor1.rgb : (tier == 1 ? SpecColor2.rgb : (tier == 2 ? SpecColor3.rgb : (tier == 3 ? SpecColor4.rgb : SpecColor5.rgb)));
float3 rimLight = tier == 0 ? RimLight1.rgb : (tier == 1 ? RimLight2.rgb : (tier == 2 ? RimLight3.rgb : (tier == 3 ? RimLight4.rgb : RimLight5.rgb)));
float shadowIntensity = tier == 0 ? ShadowIntensity1 : (tier == 1 ? ShadowIntensity2 : (tier == 2 ? ShadowIntensity3 : (tier == 3 ? ShadowIntensity4 : ShadowIntensity5)));
float ndl = dot(N, L);
// The exported pass applies a height compensation before adding _LightTex.B.
// The exact runtime ramp coefficients are supplied by game globals, so these
// two thresholds remain editor calibration parameters.
float height = saturate(1.5 + N.z - 0.5 * L.z);
float halfLambert = (ndl + 1.0) * height - 1.0;
float ramp = saturate(0.5 * (halfLambert + 1.0) + (LightTex.b * 2.0 - 1.0) * DiffuseBiasScale);
float lowBand = smoothstep(RampLow - 0.08, RampLow + 0.08, ramp);
float highBand = smoothstep(RampHigh - 0.08, RampHigh + 0.08, ramp);
float3 mid = lerp(shadow, shallow, 0.5);
float3 diffuse = lerp(lerp(shadow, mid, lowBand), shallow, highBand);
diffuse = lerp(shadow, diffuse, saturate(Visibility * shadowIntensity));
float3 H = normalize(L + V);
float metallic = saturate(Packed.g * MetallicScale);
float roughness = max(RoughnessFloor, 1.0 - saturate(Aux.g * Glossiness));
float alpha = roughness * roughness;
float alpha2 = alpha * alpha;
float ndh = saturate(dot(N, H));
float ndv = max(0.001, saturate(dot(N, V)));
float vdh = saturate(dot(V, H));
float direct = saturate(ndl) * saturate(Visibility);
float denom = ndh * ndh * (alpha2 - 1.0) + 1.0;
float D = alpha2 / max(0.001, 3.14159265 * denom * denom);
float k = (roughness + 1.0) * (roughness + 1.0) * 0.125;
float Gv = ndv / (ndv * (1.0 - k) + k);
float Gl = direct / (direct * (1.0 - k) + k);
float3 F0 = lerp(float3(0.04, 0.04, 0.04), Albedo.rgb, metallic);
float3 F = F0 + (float3(1.0, 1.0, 1.0) - F0) * pow(1.0 - vdh, 5.0);
float3 spec = min(float3(2.0, 2.0, 2.0), D * Gv * Gl * F / max(0.01, 4.0 * ndv * direct)) * specColor * Packed.b * SpecStrength * SpecularGain;
float rim = pow(1.0 - ndv, 3.0) * RimStrength * RimGain;
float2 mcUV = normalize(ViewNormal).xy * 0.5 + 0.5;
float3 directColor = LightColor.rgb * max(0.0, SceneLightStrength);
float3 result = Albedo.rgb * (AmbientFloor + diffuse * DiffuseGain * directColor) * LightingTint.rgb;
result += spec * directColor * LightingTint.rgb;
result += rim * lerp(RimShadow.rgb, rimLight, highBand) * directColor;
float3 glow = EmissionColor.rgb * Aux.b * EmissionStrength;
'''
    for i in range(1, 6):
        code += '''
if (MatCapEnabled%(i)d > 0.5 && tier == %(tier)d) {
    float4 cap = Texture2DSample(MatCapTex%(i)d, MatCapTex%(i)dSampler, mcUV);
    float mask = UseMatCapMask > 0.5 ? Packed.a : 1.0;
    float weight = saturate(cap.a * MatCapAlphaBurst%(i)d * mask * MatCapGain);
    float3 tint = cap.rgb * MatCapTint%(i)d.rgb * MatCapColorBurst%(i)d;
    if (MatCapBlendMode%(i)d < 0.5) {
        result = lerp(result, tint, weight);
    } else if (MatCapBlendMode%(i)d < 1.5) {
        result += tint * weight;
    } else {
        float3 overlay = lerp(2.0 * result * tint,
                              1.0 - 2.0 * (1.0 - result) * (1.0 - tint),
                              step(0.5, result));
        result = lerp(result, overlay, weight);
    }
}
''' % {"i": i, "tier": i - 1}
    code += "return result + glow;"
    custom = add_custom(m, 100, 0, code, inputs, "NapAvatar-inspired ramp, GGX, tier rim and MatCap")
    if not MEL.connect_material_property(custom, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("Could not connect emissive output")
    errors = MEL.recompile_material(m)
    if errors:
        raise RuntimeError("Toon material failed to compile: " + "; ".join(errors))
    save(m)
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
    save(m)


def set_instance(main, suffix, data, calibration):
    mi = asset("MI_Pyrois_" + suffix, unreal.MaterialInstanceConstantFactoryNew(), unreal.MaterialInstanceConstant)
    MEL.set_material_instance_parent(mi, main)
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
        for source, target in (("_ShallowColor", "ShallowColor"), ("_ShadowColor", "ShadowColor"),
                               ("_SpecularColor", "SpecularColor"), ("_RimGlowLightColor", "RimGlowLightColor")):
            c = colors[source + end]
            MEL.set_material_instance_vector_parameter_value(mi, target + str(i),
                unreal.LinearColor(c["r"], c["g"], c["b"], c["a"]))
        MEL.set_material_instance_scalar_parameter_value(
            mi, "ShadowIntensity%d" % i, float(p["m_Floats"].get("_PerObjectShadowIntensity" + end, 1)))
    c = colors["_RimGlowShadowColor"]
    MEL.set_material_instance_vector_parameter_value(mi, "RimGlowShadowColor",
        unreal.LinearColor(c["r"], c["g"], c["b"], c["a"]))
    c = colors["_EmissionColor"]
    MEL.set_material_instance_vector_parameter_value(mi, "EmissionColor", unreal.LinearColor(c["r"], c["g"], c["b"], 1))
    floats = p["m_Floats"]
    for source, target in (("_Emission", "EmissionStrength"), ("_SpecIntensity", "SpecStrength"),
                           ("_RimGlow", "RimStrength"), ("_Glossiness", "Glossiness"),
                           ("_Metallic", "MetallicScale")):
        MEL.set_material_instance_scalar_parameter_value(mi, target, float(floats.get(source, 0)))
    MEL.set_material_instance_scalar_parameter_value(mi, "UseMatCapMask", float(floats.get("_UseMatCapMask", 0)))
    for i in range(1, 6):
        end = "" if i == 1 else str(i)
        source_texture = p["m_TexEnvs"].get("_MatCapTex" + end, {}).get("m_Texture", {})
        texture_name = source_texture.get("Name", "")
        has_texture = bool(texture_name) and not source_texture.get("IsNull", True)
        if has_texture:
            texture = EAL.load_asset(ROOT + "/Texture/" + texture_name)
            if texture is None:
                raise RuntimeError("Missing JSON MatCap texture " + texture_name)
            MEL.set_material_instance_texture_parameter_value(mi, "MatCapTex%d" % i, texture)
        MEL.set_material_instance_scalar_parameter_value(
            mi, "MatCapEnabled%d" % i, float(bool(floats.get("_MatCap", 0)) and has_texture))
        for source, target, default in (("_MatCapColorBurst", "MatCapColorBurst", 1),
                                        ("_MatCapAlphaBurst", "MatCapAlphaBurst", 1),
                                        ("_MatCapBlendMode", "MatCapBlendMode", 0)):
            MEL.set_material_instance_scalar_parameter_value(
                mi, target + str(i), float(floats.get(source + end, default)))
        c = colors.get("_MatCapColorTint" + end, {"r": 1, "g": 1, "b": 1, "a": 1})
        MEL.set_material_instance_vector_parameter_value(
            mi, "MatCapTint%d" % i, unreal.LinearColor(c["r"], c["g"], c["b"], c["a"]))
    MEL.set_material_instance_scalar_parameter_value(mi, "BumpScale", float(floats.get("_BumpScale", 1.0)))
    for name, value in calibration.items():
        if isinstance(value, list):
            MEL.set_material_instance_vector_parameter_value(mi, name, unreal.LinearColor(*value))
        else:
            MEL.set_material_instance_scalar_parameter_value(mi, name, float(value))
    save(mi)


def configure_packed_textures():
    # _LightTex.B is diffuse bias, so normal-map BC5 compression would erase it.
    # The M/A maps also need linear sampling and their alpha channel intact.
    for body in ("Body_Map1", "Body_Map2", "Weapon"):
        for suffix in ("N", "M", "A"):
            tex = EAL.load_asset(ROOT + "/Texture/Pyrois_" + body + "_" + suffix)
            if tex is None:
                raise RuntimeError("Missing packed texture for " + body + suffix)
            touch(tex)
            tex.set_editor_property("srgb", False)
            tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_BC7)
            save(tex)


def bind_editor_preview_materials(prechecked=False):
    mesh_path = MESH_PATH
    mesh = EAL.load_asset(mesh_path)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("Missing Pyrios skeletal mesh: " + mesh_path)
    materials = list(mesh.get_editor_property("materials"))
    names = SLOT_INSTANCES
    if not prechecked:
        check_targets_clean({mesh_path})
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
        configure_packed_textures()
        m = build_main()
        build_outline()
        for suffix in SUFFIXES:
            set_instance(m, suffix, plan["materials"][suffix], plan["calibration"][suffix])
        bind_editor_preview_materials(prechecked=True)
        unreal.log("PYRIOS_MATERIAL_BUILD_OK " + json.dumps(JOURNAL.report("complete")))
    except Exception as error:
        unreal.log_error("PYRIOS_MATERIAL_BUILD_FAILED " + json.dumps(JOURNAL.report("failed", str(error))))
        raise
    finally:
        JOURNAL = None


if __name__ == "__main__":
    main()
