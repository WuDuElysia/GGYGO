"""Read-only sanity check for the Pyrios render assets and JSON parameter wiring."""
import json
from pathlib import Path
import unreal

root = "/Game/Characters/Player/Pyrios/Materials"
json_dir = Path(__file__).resolve().parents[2] / "Content/Characters/Player/Pyrios/Materials"
for name in ("M_Pyrois_Toon", "M_Pyrois_Outline", "MI_Pyrois_Body_1", "MI_Pyrois_Body_2", "MI_Pyrois_Weapon01"):
    path = root + "/Generated/" + name
    assert unreal.EditorAssetLibrary.does_asset_exist(path), path
    material = unreal.EditorAssetLibrary.load_asset(path)
    assert material is not None
    if isinstance(material, unreal.Material):
        assert unreal.MaterialEditingLibrary.has_material_usage(material, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        errors = unreal.MaterialEditingLibrary.recompile_material(material)
        assert not errors, "%s: %s" % (name, errors)
        unreal.log("PYRIOS_VERIFY_COMPILED " + name)
    unreal.log("PYRIOS_VERIFY_ASSET " + path)

mesh = unreal.EditorAssetLibrary.load_asset("/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model")
assert mesh is not None
slots = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("materials")]
unreal.log("PYRIOS_VERIFY_SLOTS " + str(slots))
assert all(any(token in slot.lower() for slot in slots) for token in ("body_1", "body_2", "weapon"))
expected_preview = {
    "MAT_Pyrois_Body_1": "MI_Pyrois_Body_1",
    "MAT_Pyrois_Body_2": "MI_Pyrois_Body_2",
    "MAT_Pyrois_Weapon01": "MI_Pyrois_Weapon01",
}
for slot in mesh.get_editor_property("materials"):
    slot_name = str(slot.get_editor_property("material_slot_name"))
    if slot_name in expected_preview:
        actual = slot.get_editor_property("material_interface")
        assert actual and actual.get_name() == expected_preview[slot_name], (slot_name, actual)
unreal.log("PYRIOS_VERIFY_EDITOR_PREVIEW_OK")

assert hasattr(unreal, "GGYGOPyriosRenderComponent")

for body in ("Body_Map1", "Body_Map2", "Weapon"):
    for suffix in ("N", "M", "A"):
        tex = unreal.EditorAssetLibrary.load_asset(root + "/Texture/Pyrois_" + body + "_" + suffix)
        assert not tex.get_editor_property("srgb")
        assert tex.get_editor_property("compression_settings") == unreal.TextureCompressionSettings.TC_BC7

for name, expected in (("Body_1", "Pyrois_Body_Map1_D"),
                       ("Body_2", "Pyrois_Body_Map2_D"),
                       ("Weapon01", "Pyrois_Weapon_D")):
    mi = unreal.EditorAssetLibrary.load_asset(root + "/Generated/MI_Pyrois_" + name)
    actual = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mi, "MainTex")
    assert actual is not None and actual.get_name() == expected, (name, actual)
    data = json.loads((json_dir / ("MAT_Pyrois_" + name + ".json")).read_text(encoding="utf-8"))
    properties = data["m_SavedProperties"]
    for i in range(1, 6):
        end = "" if i == 1 else str(i)
        source_texture = properties["m_TexEnvs"].get("_MatCapTex" + end, {}).get("m_Texture", {})
        expected_texture = source_texture.get("Name", "") if not source_texture.get("IsNull", True) else ""
        enabled = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, "MatCapEnabled%d" % i)
        assert enabled == float(bool(expected_texture) and bool(properties["m_Floats"].get("_MatCap", 0))), (name, i, enabled)
        if expected_texture:
            actual_texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mi, "MatCapTex%d" % i)
            assert actual_texture and actual_texture.get_name() == expected_texture, (name, i, actual_texture)
    unreal.log("PYRIOS_VERIFY_JSON_MATCAP " + name)

unreal.log("PYRIOS_VERIFY_OK")
