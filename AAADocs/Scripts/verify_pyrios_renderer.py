"""只读核对 Pyrios 表面材质资产；--compile 时显式重编译（会把材质包标脏）。"""
import argparse
import sys
from pathlib import Path
import unreal

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyrios_material_plan import SLOT_INSTANCES, SUFFIXES, load_plan

ROOT = "/Game/Characters/Player/Pyrios/Materials"
JSON_DIR = Path(__file__).resolve().parents[1] / "Assets/Pyrios/Rendering/UnityMaterials"
GLOBALS_PATH = Path(__file__).resolve().parents[1] / "Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json"


def close(color, value):
    return all(abs(a - b) <= 1e-4 * max(1.0, abs(b))
               for a, b in zip((color.r, color.g, color.b, color.a), value))


def verify(recompile=False):
    mel = unreal.MaterialEditingLibrary
    eal = unreal.EditorAssetLibrary
    for name in ("M_Pyrois_Toon", "M_Pyrois_Outline", "MI_Pyrois_Body_1", "MI_Pyrois_Body_2", "MI_Pyrois_Weapon01"):
        path = ROOT + "/Generated/" + name
        assert eal.does_asset_exist(path), path
        material = eal.load_asset(path)
        assert material is not None
        if isinstance(material, unreal.Material):
            assert mel.has_material_usage(material, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
            if recompile:
                mel.recompile_material(material)
                assert mel.get_statistics(material).num_pixel_shader_instructions > 0, name
                unreal.log("PYRIOS_VERIFY_COMPILED " + name)
        unreal.log("PYRIOS_VERIFY_ASSET " + path)

    plan = load_plan(JSON_DIR, GLOBALS_PATH)
    mesh = eal.load_asset("/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model")
    assert mesh is not None
    for slot in mesh.get_editor_property("materials"):
        slot_name = str(slot.get_editor_property("material_slot_name"))
        if slot_name in SLOT_INSTANCES:
            actual = slot.get_editor_property("material_interface")
            assert actual and actual.get_name() == SLOT_INSTANCES[slot_name], (slot_name, actual)
    unreal.log("PYRIOS_VERIFY_EDITOR_PREVIEW_OK")

    for name, srgb in plan["texture_srgb"].items():
        tex = eal.load_asset(ROOT + "/Texture/" + name)
        assert tex.get_editor_property("srgb") == srgb, (name, srgb)

    for suffix in SUFFIXES:
        mi = eal.load_asset(ROOT + "/Generated/MI_Pyrois_" + suffix)
        for slot, name in plan["textures"][suffix].items():
            actual = mel.get_material_instance_texture_parameter_value(mi, slot)
            default = next(plan["textures"][s][slot] for s in SUFFIXES if plan["textures"][s][slot])
            assert actual is not None and actual.get_name() == (name or default), (suffix, slot, actual)
        expected = dict(plan["globals"])
        expected.update(plan["params"][suffix])
        for name, value in expected.items():
            assert close(mel.get_material_instance_vector_parameter_value(mi, name), value), (suffix, name)
        unreal.log("PYRIOS_VERIFY_PARAMS %s %d" % (suffix, len(expected)))

    unreal.log("PYRIOS_VERIFY_OK")
    unreal.log("PYRIOS_VERIFY_COMPILATION " + ("CHECKED" if recompile else "NOT_RUN"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile", action="store_true", help="Mutating check: recompiles and dirties material packages")
    verify(recompile=parser.parse_args().compile)
