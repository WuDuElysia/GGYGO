"""Geometry-only pivot, stable mirror choice and source draw-order regressions."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import zzz_fx_particle_renderer as R
import zzz_fx_niagara as N
from zzz_fx_niagara_ue import NiagaraBuilder


def renderer():
    return {"m_Pivot": {"x": -.25, "y": .05, "z": 0},
            "m_Flip": {"x": 0, "y": 0, "z": 0}, "m_SortMode": 0, "m_SortingFudge": 0}


class RecordingBuilder(NiagaraBuilder):
    def __init__(self):
        self.sref = {"refPath": "/Test/System.System"}
        self.calls = []
        self.renderer_properties = None

    def ns(self, name, **args):
        self.calls.append((name, args))
        if name in ("AddModule", "AddSetParametersModule"):
            return {"moduleName": "Module%d" % len(self.calls)}
        if name == "AddRenderer":
            return {"rendererIndex": 0}
        if name == "SetRendererData":
            self.renderer_properties = json.loads(args["rendererData"]["propertyValues"])
        if name == "GetRendererData":
            return {"propertyValues": json.dumps(self.renderer_properties)}
        return {}


class RendererTests(unittest.TestCase):
    def test_front_mesh_pivot_uses_centimetres_in_imported_mesh_basis(self):
        contract = R.mesh_contract(renderer(), "Front02/PS4")
        self.assertEqual(contract["pivot_offset"], (25, 0, 5))
        self.assertEqual(contract["pivot_space"], "Mesh")

    def test_offset_rotates_and_scales_with_geometry_without_moving_particle_origin(self):
        contract = R.mesh_contract(renderer(), "Front02/PS4")
        scale = (2, 3, 4)
        pivot = contract["pivot_offset"]
        # Independent Z-axis transform: UE mesh-local offset is scaled before
        # rotation, not interpreted as an unrotated world displacement.
        scaled = tuple(pivot[i] * scale[i] for i in range(3))
        rotated = (-scaled[1], scaled[0], scaled[2])
        origin = (100, 200, 300)
        geometry_center = tuple(origin[i] + rotated[i] for i in range(3))
        self.assertEqual(geometry_center, (100, 250, 320))
        self.assertEqual(origin, (100, 200, 300))

    def test_age_sort_uses_actual_age_not_normalized_age(self):
        source = renderer()
        source["m_SortMode"] = 2
        oldest = R.mesh_contract(source, "Oldest")
        self.assertEqual(oldest["sort_mode"], "CustomAscending")
        self.assertEqual(oldest["sort_attribute"], "Particles.Age")
        source["m_SortMode"] = 3
        youngest = R.mesh_contract(source, "Youngest")
        self.assertEqual(youngest["sort_mode"], "CustomDecending")
        self.assertEqual(youngest["sort_attribute"], "Particles.Age")
        # A longer-lived old particle has a lower normalized age. Resolve the
        # selected attribute over actual particle data: ascending draws the old
        # particle last, in front, while normalized-age sorting reverses it.
        particles = [{"name": "Old", "Particles.Age": .7, "Particles.NormalizedAge": .7/4},
                     {"name": "Young", "Particles.Age": .3, "Particles.NormalizedAge": .3/.4}]
        actual = sorted(particles, key=lambda p: p[oldest["sort_attribute"]])
        normalized = sorted(particles, key=lambda p: p["Particles.NormalizedAge"])
        self.assertEqual([p["name"] for p in actual], ["Young", "Old"])
        self.assertEqual([p["name"] for p in normalized], ["Old", "Young"])

    def test_distance_sort_needs_no_age_attribute(self):
        source = renderer()
        source["m_SortMode"] = 1
        result = R.mesh_contract(source, "Distance")
        self.assertEqual(result["sort_mode"], "ViewDistance")
        self.assertIsNone(result["sort_attribute"])

    def test_scene_sorting_fudge_is_rejected_instead_of_rounded_to_renderer_order(self):
        for value in (-.046, .7):
            source = renderer()
            source["m_SortingFudge"] = value
            with self.assertRaisesRegex(R.RendererError, "scene transparency ordering"):
                R.mesh_contract(source, "Main_Distor")

    def test_invalid_source_fields_fail_with_path(self):
        for field, value in (("m_SortMode", 98), ("m_SortingFudge", float("nan"))):
            source = renderer()
            source[field] = value
            with self.assertRaisesRegex(R.RendererError, "Effect/Emitter"):
                R.mesh_contract(source, "Effect/Emitter")
        for value in (-.01, 1.01, float("inf")):
            source = renderer()
            source["m_Flip"]["x"] = value
            with self.assertRaises(R.RendererError):
                R.mesh_contract(source, "Flip")

    def test_deterministic_flips_do_not_consume_random_values(self):
        randoms = N.Randoms()
        self.assertEqual(R.mesh_flip_h((0, 1, 0), randoms), "float3(1.0, -1.0, 1.0)")
        self.assertEqual(randoms.n, 0)

    def test_partial_flips_use_birth_stable_random_attribute(self):
        randoms = N.Randoms()
        code = R.mesh_flip_h((.25, 0, .75), randoms)
        self.assertIn("Particles.URand0.x < 0.25", code)
        self.assertIn("Particles.URand0.y < 0.75", code)
        self.assertNotIn("rand(", code)
        self.assertEqual(randoms.n, 2)
        self.assertEqual(len(randoms.spawn_entries()), 1)

    def test_builder_sets_geometry_offset_and_live_age_binding(self):
        source = renderer()
        source["m_SortMode"] = 3
        spec = {"name": "Front02", "local_space": True, "loop": False, "duration": .3,
                "delay": 0, "bursts": [], "rate": 0, "spawn": [], "update": [],
                "renderer": {"kind": "mesh", "mesh": "/Test/FrontMesh", "material": "/Test/FrontMaterial",
                             "sort": 0, **R.mesh_contract(source, "Front02")}}
        original = copy.deepcopy(spec)
        builder = RecordingBuilder()
        builder.build_emitter(spec)
        props = builder.renderer_properties
        self.assertEqual(props["Meshes"][0]["PivotOffset"], {"x": 25, "y": 0, "z": 5})
        self.assertEqual(props["Meshes"][0]["PivotOffsetSpace"], "Mesh")
        self.assertEqual(props["SortMode"], "CustomDecending")
        binding = props["CustomSortingBinding"]
        self.assertEqual(binding["ParamMapVariable"]["Name"], "Particles.Age")
        self.assertEqual(binding["DataSetName"], "Age")
        self.assertNotIn("BoundVariable", binding)
        self.assertEqual(spec, original)


if __name__ == "__main__":
    unittest.main()
