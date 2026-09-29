"""Build a baseline editor preview for the BH3 Kevin DemonBattle export.

Run in the UE 5.8 editor after the animation import owns and finishes the mesh:
    py F:/ue_project/GGYGO/AAADocs/Scripts/setup_bh3_kevin_materials.py

Only /Game/Characters/Boss/Kevin/DemonBattle is modified. This is a texture
preview, not a port of the BH3 character shaders or their runtime lighting.
The imported source PNGs and JSON files are read without being modified.
Rerunning refreshes the eight generated MI assets and three preview masters.
"""

import json
from pathlib import Path

import unreal


SOURCE = Path(r"F:\AnimeStudio\Exports\BH3\Animator\Kevin\05_BOSS_411_DemonBattle")
BASE = "/Game/Characters/Boss/Kevin/DemonBattle"
MESH_PATH = BASE + "/Mesh/SK_Kevin_DemonBattle"
TEXTURES = BASE + "/Textures"
MATERIALS = BASE + "/Materials"
PREVIEW = MATERIALS + "/Preview"

# Base color comes from _MainTex in each source JSON. The other bound textures
# are imported, but are not interpreted as UE baked lightmaps or normal maps.
SLOTS = {
    "BOSS_411_Material_Body01": ("M_Kevin_Preview_Opaque", 0.65, 0.35),
    "BOSS_411_Material_Body02": ("M_Kevin_Preview_Masked", 0.70, 0.30),
    "BOSS_411_Material_Eye": ("M_Kevin_Preview_Masked", 0.35, 0.45),
    "BOSS_411_Material_Face": ("M_Kevin_Preview_Opaque", 0.80, 0.20),
    "BOSS_411_Material_Hair": ("M_Kevin_Preview_Masked", 0.60, 0.35),
    "BOSS_411_Material_Wing": ("M_Kevin_Preview_Masked", 0.70, 0.30),
    "BOSS_411_Material_Wings_Blue": ("M_Kevin_Preview_Translucent", 0.0, 0.0),
    "BOSS_411_Weapon_Blade_Material": ("M_Kevin_Preview_Opaque", 0.40, 0.40),
}
DATA_TEXTURE_SLOTS = {"_LightMapTex", "_FaceMapTex", "_SPNoiseTex", "_SPTex"}

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def checked(condition, message):
    if not condition:
        raise RuntimeError(message)


def load_source():
    checked(SOURCE.is_dir(), "Missing source directory: " + str(SOURCE))
    result = {}
    image_names = set()
    data_names = set()
    for slot in SLOTS:
        path = SOURCE / "Materials" / (slot + ".json")
        checked(path.is_file(), "Missing source material: " + str(path))
        data = json.loads(path.read_text(encoding="utf-8"))
        checked(data.get("m_Name") == slot, "Unexpected material name in " + str(path))
        textures = data["m_SavedProperties"]["m_TexEnvs"]
        main = textures["_MainTex"]["m_Texture"]
        checked(main.get("Name") and not main.get("IsNull"), slot + " has no _MainTex")
        for property_name, entry in textures.items():
            texture = entry.get("m_Texture") or {}
            if texture.get("IsNull", True):
                continue
            name = texture.get("Name", "")
            checked(name and (SOURCE / (name + ".png")).is_file(),
                    slot + " lacks " + property_name + " PNG: " + name)
            image_names.add(name)
            if property_name in DATA_TEXTURE_SLOTS:
                data_names.add(name)
        result[slot] = data
    checked(len(result) == 8, "Expected eight source materials")
    checked(len(image_names) == 16, "Unexpected number of bound PNGs: " + str(sorted(image_names)))
    return result, image_names, data_names


def find_meshes():
    # Bind only the explicitly imported DemonBattle mesh. Other Boss assets
    # under BASE remain untouched if this script is rerun later.
    mesh = EAL.load_asset(MESH_PATH)
    checked(isinstance(mesh, unreal.SkeletalMesh), "Missing SkeletalMesh " + MESH_PATH)
    meshes = [mesh]
    found = set()
    for mesh in meshes:
        for entry in mesh.get_editor_property("materials"):
            slot = str(entry.get_editor_property("material_slot_name"))
            if slot in SLOTS:
                found.add(slot)
    missing = sorted(set(SLOTS) - found)
    checked(not missing, "Imported SkeletalMesh lacks FBX slots: " + str(missing))
    return meshes


def import_textures(names, data_names):
    EAL.make_directory(TEXTURES)
    pending = []
    for name in sorted(names):
        if EAL.does_asset_exist(TEXTURES + "/" + name):
            continue
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(SOURCE / (name + ".png")))
        task.set_editor_property("destination_path", TEXTURES)
        task.set_editor_property("destination_name", name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("save", True)
        pending.append(task)
    if pending:
        TOOLS.import_asset_tasks(pending)
    textures = {}
    for name in sorted(names):
        asset = EAL.load_asset(TEXTURES + "/" + name)
        checked(isinstance(asset, unreal.Texture2D), "Texture import failed: " + name)
        if name in data_names:
            # BH3's named LightMap/FaceMap/SP maps are packed shader inputs,
            # not UE's baked scene lightmaps. Keep channels and alpha linear.
            asset.set_editor_property("srgb", False)
            asset.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_BC7)
        else:
            asset.set_editor_property("srgb", True)
        checked(EAL.save_loaded_asset(asset), "Could not save texture " + name)
        textures[name] = asset
    return textures


def expression(material, cls, x, y, **properties):
    item = MEL.create_material_expression(material, cls, x, y)
    for name, value in properties.items():
        item.set_editor_property(name, value)
    return item


def link(source, output, target, input_name):
    checked(MEL.connect_material_expressions(source, output, target, input_name),
            "Could not connect material expression " + input_name)


def make_master(name, default_texture):
    path = PREVIEW + "/" + name
    material = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if material is None:
        material = TOOLS.create_asset(name, PREVIEW, unreal.Material, unreal.MaterialFactoryNew())
    checked(isinstance(material, unreal.Material), "Could not create master: " + path)
    MEL.delete_all_material_expressions(material)
    translucent = name.endswith("Translucent")
    masked = name.endswith("Masked")
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT
                                 if translucent else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT
                                 if translucent else (unreal.BlendMode.BLEND_MASKED if masked
                                                      else unreal.BlendMode.BLEND_OPAQUE))
    material.set_editor_property("two_sided", translucent or masked)
    MEL.set_base_material_usage(material, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    MEL.set_base_material_usage(material, unreal.MaterialUsage.MATUSAGE_MORPH_TARGETS)

    color = expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -900, 0,
                       parameter_name="MainTex", sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    color.set_editor_property("texture", default_texture)
    tint = expression(material, unreal.MaterialExpressionVectorParameter, -900, 260,
                      parameter_name="PreviewTint", default_value=unreal.LinearColor(1, 1, 1, 1))
    tinted = expression(material, unreal.MaterialExpressionMultiply, -530, 0)
    link(color, "", tinted, "A")
    link(tint, "", tinted, "B")

    if translucent:
        gain = expression(material, unreal.MaterialExpressionScalarParameter, -530, 280,
                          parameter_name="PreviewEmissionGain", default_value=0.65)
        emission = expression(material, unreal.MaterialExpressionMultiply, -250, 0)
        link(tinted, "", emission, "A")
        link(gain, "", emission, "B")
        checked(MEL.connect_material_property(emission, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR),
                "Could not connect translucent emissive")
        checked(MEL.connect_material_property(color, "A", unreal.MaterialProperty.MP_OPACITY),
                "Could not connect translucent alpha")
    else:
        checked(MEL.connect_material_property(tinted, "", unreal.MaterialProperty.MP_BASE_COLOR),
                "Could not connect base color")
        roughness = expression(material, unreal.MaterialExpressionScalarParameter, -500, 380,
                               parameter_name="PreviewRoughness", default_value=0.65)
        specular = expression(material, unreal.MaterialExpressionScalarParameter, -500, 520,
                              parameter_name="PreviewSpecular", default_value=0.35)
        checked(MEL.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS),
                "Could not connect roughness")
        checked(MEL.connect_material_property(specular, "", unreal.MaterialProperty.MP_SPECULAR),
                "Could not connect specular")
        if masked:
            checked(MEL.connect_material_property(color, "A", unreal.MaterialProperty.MP_OPACITY_MASK),
                    "Could not connect masked alpha")

    errors = MEL.recompile_material(material)
    checked(not errors, name + " compile errors: " + str(errors))
    checked(EAL.save_loaded_asset(material), "Could not save " + path)
    return material


def make_instance(slot, data, master, textures, roughness, specular):
    name = "MI_" + slot
    path = MATERIALS + "/" + name
    instance = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if instance is None:
        instance = TOOLS.create_asset(name, MATERIALS, unreal.MaterialInstanceConstant,
                                      unreal.MaterialInstanceConstantFactoryNew())
    checked(isinstance(instance, unreal.MaterialInstanceConstant), "Could not create MI: " + path)
    MEL.set_material_instance_parent(instance, master)
    tex_name = data["m_SavedProperties"]["m_TexEnvs"]["_MainTex"]["m_Texture"]["Name"]
    MEL.set_material_instance_texture_parameter_value(instance, "MainTex", textures[tex_name])
    color = data["m_SavedProperties"]["m_Colors"].get("_Color", {})
    MEL.set_material_instance_vector_parameter_value(instance, "PreviewTint",
        unreal.LinearColor(color.get("r", 1), color.get("g", 1), color.get("b", 1), color.get("a", 1)))
    if master.get_name().endswith("Translucent"):
        MEL.set_material_instance_scalar_parameter_value(instance, "PreviewEmissionGain", 0.65)
    else:
        MEL.set_material_instance_scalar_parameter_value(instance, "PreviewRoughness", roughness)
        MEL.set_material_instance_scalar_parameter_value(instance, "PreviewSpecular", specular)
    checked(EAL.save_loaded_asset(instance), "Could not save " + path)
    return instance


def bind_meshes(meshes, instances):
    bound = set()
    for mesh in meshes:
        entries = list(mesh.get_editor_property("materials"))
        changed = False
        for index, entry in enumerate(entries):
            slot = str(entry.get_editor_property("material_slot_name"))
            if slot not in instances:
                continue
            entry.set_editor_property("material_interface", instances[slot])
            entries[index] = entry
            changed = True
            bound.add(slot)
        if changed:
            mesh.set_editor_property("materials", entries)
            checked(EAL.save_loaded_asset(mesh), "Could not save SkeletalMesh " + mesh.get_name())
    checked(bound == set(SLOTS), "Unbound Kevin material slots: " + str(sorted(set(SLOTS) - bound)))
    unreal.log("BH3_KEVIN_BOUND " + str(sorted(bound)))


def main():
    materials, names, data_names = load_source()
    meshes = find_meshes()  # No assets are changed if the imported mesh is absent.
    EAL.make_directory(MATERIALS)
    EAL.make_directory(PREVIEW)
    textures = import_textures(names, data_names)
    default_texture = textures["Monster_Boss_411_Texture_Body_Color"]
    masters = {name: make_master(name, default_texture)
               for name in sorted({entry[0] for entry in SLOTS.values()})}
    instances = {}
    for slot, (master_name, roughness, specular) in SLOTS.items():
        instances[slot] = make_instance(slot, materials[slot], masters[master_name],
                                        textures, roughness, specular)
    bind_meshes(meshes, instances)
    unreal.log("BH3_KEVIN_PREVIEW_OK textures=%d materials=%d meshes=%d" %
               (len(textures), len(instances), len(meshes)))


if __name__ == "__main__":
    main()
