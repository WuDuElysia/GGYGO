"""Inspect Pyrios assets without mutation by default; --compile explicitly recompiles."""
import argparse
import json
from pathlib import Path
import unreal


def verify(recompile=False):
    root = "/Game/Characters/Player/Pyrios/Materials"
    json_dir = Path(__file__).resolve().parents[2] / "Content/Characters/Player/Pyrios/Materials"
    calibration = json.loads((Path(__file__).resolve().parents[1] / "Assets/Pyrios/Rendering/Pyrios_Editor_Calibration.json").read_text(encoding="utf-8"))
    for name in ("M_Pyrois_Toon", "M_Pyrois_Outline", "MI_Pyrois_Body_1", "MI_Pyrois_Body_2", "MI_Pyrois_Weapon01"):
        path = root + "/Generated/" + name
        assert unreal.EditorAssetLibrary.does_asset_exist(path), path
        material = unreal.EditorAssetLibrary.load_asset(path)
        assert material is not None
        if isinstance(material, unreal.Material):
            assert unreal.MaterialEditingLibrary.has_material_usage(material, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
            if recompile:
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
        for source, target in (("_Glossiness", "Glossiness"), ("_Metallic", "MetallicScale"),
                               ("_SpecIntensity", "SpecStrength"), ("_RimGlow", "RimStrength")):
            actual_value = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, target)
            assert abs(actual_value - float(properties["m_Floats"][source])) < 1e-4, (name, target, actual_value)
        for i in range(1, 6):
            end = "" if i == 1 else str(i)
            for source, target in (("_SpecularColor", "SpecularColor"),
                                   ("_RimGlowLightColor", "RimGlowLightColor")):
                expected_color = properties["m_Colors"][source + end]
                actual_color = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi, target + str(i))
                assert all(abs(getattr(actual_color, key) - expected_color[key]) < 1e-4
                           for key in ("r", "g", "b", "a")), (name, target, i, actual_color)
            actual_shadow = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, "ShadowIntensity%d" % i)
            assert abs(actual_shadow - float(properties["m_Floats"]["_PerObjectShadowIntensity" + end])) < 1e-4
            source_texture = properties["m_TexEnvs"].get("_MatCapTex" + end, {}).get("m_Texture", {})
            expected_texture = source_texture.get("Name", "") if not source_texture.get("IsNull", True) else ""
            enabled = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, "MatCapEnabled%d" % i)
            assert enabled == float(bool(expected_texture) and bool(properties["m_Floats"].get("_MatCap", 0))), (name, i, enabled)
            if expected_texture:
                actual_texture = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mi, "MatCapTex%d" % i)
                assert actual_texture and actual_texture.get_name() == expected_texture, (name, i, actual_texture)
        selected_calibration = dict(calibration["shared"])
        selected_calibration.update(calibration.get(name, {}))
        for target, expected_value in selected_calibration.items():
            if isinstance(expected_value, list):
                actual_value = unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(mi, target)
                assert all(abs(getattr(actual_value, key) - value) < 1e-4
                           for key, value in zip(("r", "g", "b", "a"), expected_value)), (name, target, actual_value)
            else:
                actual_value = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, target)
                assert abs(actual_value - expected_value) < 1e-4, (name, target, actual_value)
        unreal.log("PYRIOS_VERIFY_JSON_MATCAP " + name)

    unreal.log("PYRIOS_VERIFY_OK")
    unreal.log("PYRIOS_VERIFY_COMPILATION " + ("CHECKED" if recompile else "NOT_RUN"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile", action="store_true", help="Mutating check: recompiles and dirties material packages")
    verify(recompile=parser.parse_args().compile)
