"""Source-backed particle shape/atlas checks and strict incomplete-prefab gates."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))
import zzz_fx_build as B
import zzz_fx_material as M
import zzz_fx_particle_motion as P
import zzz_fx_particle_uv as U
import zzz_fx_particle_renderer as R
import zzz_fx_niagara as N
from zzz_fx_niagara_ue import NiagaraBuilder
from zzz_fx_material_ue import Builder as MaterialBuilder
from test_zzz_fx_particle_renderer import RecordingBuilder

SOURCE = Path("F:/AnimeStudio/Exports/ZZZ/Pyrois_SkillFX_Evidence/Prefabs")
POLICY = {"mode": P.EQUIVALENCE_MODE, "dampen_reference_seconds": 1/60,
          "dampen_strength": 1, "viewport_limit_scale": 1}


def source_rows(direction):
    root = json.loads((SOURCE / ("Eff_Pyrois_Evade_%s_01_Smoke.fx.json" % direction)).read_text(encoding="utf-8"))["root"]
    return [(node, list(path)) for node, path, active in B.walk(root) if active and node.get("particle") and
            node["particle"]["renderer"] and node["particle"]["renderer"]["m_Enabled"] and
            any(mat["m_PathID"] for mat in node["particle"]["renderer"]["m_Materials"])]


class Vec(tuple):
    x = property(lambda v: v[0])
    y = property(lambda v: v[1])
    z = property(lambda v: v[2])
    w = property(lambda v: v[3])
    xyz = property(lambda v: Vec(v[:3]))

    def __mul__(self, value):
        return Vec(x * (value[i] if isinstance(value, tuple) else value) for i, x in enumerate(self))

    __rmul__ = __mul__

    def __add__(self, other):
        return Vec(a+b for a, b in zip(self, other))

    def __sub__(self, other):
        return Vec(a-b for a, b in zip(self, other))

    def __truediv__(self, value):
        return self * (1/value)

    def __abs__(self):
        return Vec(abs(x) for x in self)


def evaluate_expression(expression, context):
    # Locally generated expressions only. Damping/projection have one outer
    # ternary; source curve interpolation is covered by the curve suite.
    if "?" in expression:
        expression = expression.strip()
        if expression[0] == "(" and expression[-1] == ")":
            expression = expression[1:-1]
        condition, rest = expression.split("?", 1)
        yes, no = rest.split(":", 1)
        expression = yes if eval(condition, {"__builtins__": {}}, context) else no
    return eval(expression, {"__builtins__": {}}, context)


def math_context(**values):
    def vector(*parts):
        return Vec(x for part in parts for x in (part if isinstance(part, tuple) else (part,)))
    return {"float3": vector, "float4": vector, "float2": vector, "length": lambda v: math.sqrt(sum(x*x for x in v)),
            "cos": math.cos, "sin": math.sin, "abs": abs, "pow": pow, "max": max, "min": min,
            "saturate": lambda v: max(0, min(1, v)), "clamp": lambda v, lo, hi: max(lo, min(hi, v)),
            "cross": lambda a, b: Vec((a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x)), **values}


class RecordingMaterialGraph:
    """Record the actual builder's expression graph without an editor."""
    def __init__(self):
        self.nodes, self.classes, self.calls = {}, {}, []

    def tool(self, name, **args):
        self.calls.append((name, args))
        if name.endswith(".create_material"):
            ref = {"refPath": "/Test/Material"}
            self.nodes[ref["refPath"]] = {}
            return {"returnValue": ref}
        if name.endswith(".add_expression"):
            ref = {"refPath": "/Test/Node%d" % len(self.nodes)}
            self.nodes[ref["refPath"]] = {"Inputs": [{"inputName": ""}]}
            self.classes[ref["refPath"]] = args["expression_class"]["refPath"]
            return {"returnValue": ref}
        if name.endswith(".set_properties"):
            self.nodes[args["instance"]["refPath"]].update(json.loads(args["values"]))
            return {"returnValue": True}
        if name.endswith(".get_properties"):
            values = self.nodes[args["instance"]["refPath"]]
            return {"returnValue": json.dumps({key: values[key] for key in args["properties"]})}
        if name.endswith(".get_expression_input_names"):
            return {"returnValue": [v["inputName"] for v in self.nodes[args["expression"]["refPath"]]["Inputs"]]}
        if name.endswith((".connect_expressions", ".connect_to_output", ".recompile")):
            return {"returnValue": True}
        raise AssertionError("Unexpected editor tool in graph recording: " + name)


def evaluate_shape(entries, position, direction, random_values):
    # Execute locally generated arithmetic only; exported JSON never contains
    # executable code. Random inputs are deterministic quadrature sample points.
    particles = SimpleNamespace(URand0=Vec(random_values))
    transient = SimpleNamespace()
    context = {"Particles": particles, "Transient": transient, "cos": math.cos, "sin": math.sin,
               "sqrt": math.sqrt, "pow": pow, "max": max, "float3": lambda *v: Vec(v),
               "normalize": lambda v: Vec(x / math.sqrt(sum(a*a for a in v)) for x in v)}
    for name, _, expression in entries:
        setattr(transient, name.split(".")[1], eval(expression, {"__builtins__": {}}, context))
    return (eval(position, {"__builtins__": {}}, context), eval(direction, {"__builtins__": {}}, context))


def stream_context(**values):
    return {"builtins": set(), "dyn": {}, "mesh": False, "uv_count": 1, "sprite_subuv": True,
            "sprite_uv_tiles": (10, 5), "sprite_rotation_2d": True, "sprite_normal_direction": 1, **values}


class ParticleModules(unittest.TestCase):
    def test_sphere_generated_sampling_has_uniform_solid_angle_and_volume_density(self):
        shape = source_rows("Front")[0][0]["particle"]["system"]["ShapeModule"]
        entries, pos, direction, plan = P.birth_shape_h(shape, "World/Smoke", N.Randoms(), N.f)
        radius2, z, z2 = [], [], []
        for i in range(600):
            # Midpoint quadrature separates radial sampling from direction.
            point, velocity = evaluate_shape(entries, pos, direction, (0.317, (i+.5)/600, (i+.5)/600, 0))
            radius2.append(sum(x*x for x in point) / plan["radius"]**2)
            z.append(velocity.z)
            z2.append(velocity.z**2)
            self.assertAlmostEqual(sum(x*x for x in velocity), 1, places=12)
        self.assertAlmostEqual(sum(z)/len(z), 0, places=12)
        self.assertAlmostEqual(sum(z2)/len(z2), 1/3, delta=1e-5)
        self.assertAlmostEqual(sum(radius2)/len(radius2), 3/5, delta=1e-5)

    def test_cone_base_samples_uniform_area_and_preserves_angle_bounds(self):
        row = next(n for n, _ in source_rows("Front") if n["name"] == "smoke_trail")
        shape = row["particle"]["system"]["ShapeModule"]
        entries, pos, direction, plan = P.birth_shape_h(shape, "Local/Smoke", N.Randoms(), N.f)
        radii = []
        for i in range(400):
            point, velocity = evaluate_shape(entries, pos, direction, (.2, (i+.5)/400, 0, 0))
            radii.append(sum(x*x for x in point) / plan["radius"]**2)
            self.assertEqual(point.z, 0)
            angle = math.degrees(math.acos(velocity.z))
            self.assertLessEqual(angle, plan["angle"])
        self.assertAlmostEqual(sum(radii)/len(radii), .5, places=12)
        self.assertEqual(plan["m_Scale"], tuple(shape["m_Scale"][a] for a in "xyz"))

    def test_actual_smokes_keep_native_dampen_failure_and_all_visible_branches(self):
        counts, blocked = [], 0
        for direction in ("Front", "Back"):
            rows = source_rows(direction)
            counts.append(len(rows))
            for node, path in rows:
                system = node["particle"]["system"]
                P.shape_contract(system["ShapeModule"], node["name"])
                U.contract(system["UVModule"], node["name"])
                if system["ClampVelocityModule"]["enabled"]:
                    with self.assertRaisesRegex(P.MotionError, "native dampen/drag"):
                        N.emitter_spec(node, path, None, {}, {}, {"dyn_params": {}})
                    blocked += 1
        self.assertEqual(counts, [4, 3])
        self.assertEqual(blocked, 6)

    def test_grid_uv_end_frame_wraps_next_uv_before_sampling_even_at_uv_boundaries(self):
        ctx = stream_context()
        expressions = [M.stream_component(name, axis, ctx) for name in ("UV", "UV2") for axis in (0, 1)]
        context = {"floor": math.floor, "fmod": math.fmod, "frac": lambda a: a-math.floor(a),
                   "AtlasFrame": 49.995, "UV0": Vec((.25, .75))}
        results = [eval(code, {"__builtins__": {}}, context) for code in expressions]
        for actual, expected in zip(results, (.925, .05, .025, .85)):
            self.assertAlmostEqual(actual, expected, places=12)
        blend = eval(M.stream_component("AnimBlend", 0, ctx), {"__builtins__": {}}, context)
        self.assertAlmostEqual(blend, .995)
        for v in (0, 1):
            context["UV0"] = Vec((0, v))
            self.assertAlmostEqual(eval(expressions[3], {"__builtins__": {}}, context), 1-v/5)
        self.assertEqual(ctx["builtins"], {"UV0", "AtlasFrame"})
        self.assertEqual(ctx["dyn"], {})

    def test_grid_index_keeps_source_end_scalar_and_birth_stable_randoms(self):
        uv = source_rows("Front")[0][0]["particle"]["system"]["UVModule"]
        randoms = N.Randoms()
        spawn, update, plan = U.entries(uv, "Smoke", randoms, (N.CurveProgram("Spawn"), N.CurveProgram("Update")), N.minmax_curve_h, N.f)
        self.assertEqual(spawn, [])  # Constant zero needs no lifetime state.
        self.assertIn(repr(uv["frameOverTime"]["scalar"]), update[0][2])
        self.assertIn("Particles.NormalizedAge", update[0][2])
        self.assertNotIn("System.Age", update[0][2])
        self.assertNotIn("rand(", update[0][2])
        self.assertEqual(plan["tiles"], (10, 5))
        disabled = copy.deepcopy(uv)
        disabled["enabled"] = False
        disabled["tilesX"] = 0
        self.assertFalse(U.contract(disabled, "Inert")["animated"])

    def test_unsupported_uv_or_shape_modes_fail_with_source_path(self):
        uv = copy.deepcopy(source_rows("Front")[0][0]["particle"]["system"]["UVModule"])
        for field, value in (("mode", 1), ("timeMode", 2), ("tilesX", 0), ("uvChannelMask", 1), ("flipU", .2)):
            bad = {**uv, field: value}
            with self.assertRaisesRegex(U.UVError, "Effect/Smoke"):
                U.contract(bad, "Effect/Smoke")
        shape = copy.deepcopy(source_rows("Front")[0][0]["particle"]["system"]["ShapeModule"])
        shape["radiusThickness"] = .5
        with self.assertRaisesRegex(P.MotionError, "Effect/Smoke"):
            P.shape_contract(shape, "Effect/Smoke")

    def test_billboard_spec_uses_two_dimensional_size_and_preserves_viewport_requirement(self):
        source, path = source_rows("Front")[0]
        node = copy.deepcopy(source)
        # Isolate implemented modules. The unmodified source is strictly tested
        # above; this fixture is never promoted to a complete source prefab.
        for key in ("ClampVelocityModule", "VelocityModule"):
            node["particle"]["system"][key]["enabled"] = False
        mid = str(node["particle"]["renderer"]["m_Materials"][0]["m_PathID"])
        spec = N.emitter_spec(node, path, None, {}, {mid: "/Test/SmokeMaterial"}, {"dyn_params": {}})
        self.assertNotIn("mesh", spec["renderer"])
        self.assertEqual(spec["renderer"]["subuv"]["tiles"], (10, 5))
        self.assertEqual(spec["renderer"]["viewport_size"], (0, 3))
        self.assertEqual(spec["bursts"], [])  # Original probability=0 is inert.
        update = {name: (kind, expr) for name, kind, expr in spec["update"]}
        self.assertEqual(update["Particles.SpriteSize"][0], "Vector2")
        self.assertIn(").xy * 100.0", update["Particles.SpriteSize"][1])
        self.assertIn("-Particles.URot.z", update["Particles.SpriteRotation"][1])
        builder = RecordingBuilder()
        with self.assertRaisesRegex(ValueError, "source_viewport_size_limit"):
            builder.build_system("/Test/Smoke", [spec])
        self.assertEqual(builder.calls, [])
        self.assertEqual(source["particle"]["system"]["ClampVelocityModule"]["enabled"], True)

    def test_native_renderer_transport_avoids_native_next_frame_overflow(self):
        rd = {"kind": "sprite", "material": "/Test/Smoke", "sort": 0, "sort_mode": "None", "sort_attribute": None,
              "pivot_uv": (.5, .5), "facing_mode": "FaceCameraPlane", "alignment": "Unaligned",
              "subuv": {"tiles": (10, 5), "animated": True, "blend": True}}
        builder = RecordingBuilder()
        builder.build_renderer("Smoke", rd)
        actual = builder.renderer_properties
        self.assertEqual(actual["SubImageSize"], {"x": 1, "y": 1})
        self.assertFalse(actual["bSubImageBlend"])
        self.assertEqual(actual["SubImageIndexBinding"]["ParamMapVariable"]["Name"], "None")
        self.assertEqual(actual["MaterialRandomBinding"]["ParamMapVariable"]["Name"], "Particles.SubImageIndex")
        self.assertEqual(actual["PixelCoverageMode"], "Disabled")

    def test_renderer_readback_checks_pivot_not_just_material_substring(self):
        expected = {"Meshes": [{"Mesh": "/Test/Smoke.Smoke", "PivotOffset": {"x": 25, "y": 0, "z": 5}}]}
        actual = {"Meshes": [{"mesh": {"refPath": "/Test/Smoke.Smoke"}, "pivotOffset": {"x": 0, "y": 0, "z": 0}}]}
        with self.assertRaisesRegex(RuntimeError, "PivotOffset.x"):
            NiagaraBuilder.verify_properties(expected, actual, "Smoke")
        actual["Meshes"][0]["pivotOffset"] = {"x": 25, "y": 0, "z": 5}
        NiagaraBuilder.verify_properties(expected, actual, "Smoke")

    def test_linear_velocity_retains_stable_curves_and_rejects_orbit(self):
        velocity = copy.deepcopy(source_rows("Front")[0][0]["particle"]["system"]["VelocityModule"])
        expression, world = P.linear_velocity_h(velocity, "Smoke", N.Randoms(), N.CurveProgram("Update"), N.minmax_curve_h)
        self.assertFalse(world)
        self.assertIn("Particles.URand0.z", expression)
        self.assertIn("Particles.NormalizedAge", expression)
        self.assertNotIn("rand(", expression)
        velocity["orbitalX"]["scalar"] = 1
        with self.assertRaisesRegex(P.MotionError, "orbital/radial solver"):
            P.linear_velocity_h(velocity, "Smoke", N.Randoms(), N.CurveProgram("Update"), N.minmax_curve_h)

    def test_source_burst_count_endpoints_are_not_rounded_to_fixed_count(self):
        source = source_rows("Back")[0][0]["particle"]["system"]["EmissionModule"]["m_Bursts"][0]
        self.assertEqual(N.burst_count(source["countCurve"], "Back/World"), {"min": 1, "max": 2})
        bad = {**source["countCurve"], "scalar": 2.5}
        with self.assertRaisesRegex(N.SpecError, "integer endpoints"):
            N.burst_count(bad, "Back/World")

    def test_standard_velocity_frame_adapter_uses_native_delta_without_pdb_gate(self):
        original, path = source_rows("Front")[0]
        node = copy.deepcopy(original)
        node["particle"]["system"]["ClampVelocityModule"]["enabled"] = False
        mid = str(node["particle"]["renderer"]["m_Materials"][0]["m_PathID"])
        spec = N.emitter_spec(node, path, None, {}, {mid: "/Test/SmokeMaterial"}, {"dyn_params": {}})
        self.assertEqual(spec["requirements"], [])
        spawn = {n: e for n, _, e in spec["spawn"]}
        update = {n: e for n, _, e in spec["update"]}
        self.assertIn("Particles.Position", spawn)
        self.assertNotIn("Particles.UWorldOrigin", spawn)
        self.assertNotIn("Particles.UWorldDir", spawn)
        self.assertEqual(update["Particles.Position"], "(Particles.Position + Particles.Velocity * Engine.DeltaTime)")
        builder = RecordingBuilder()
        with self.assertRaisesRegex(ValueError, "source_viewport_size_limit"):
            builder.build_system("/Test/Smoke", [spec])
        self.assertEqual(builder.calls, [])

    def test_all_seven_original_particles_generate_with_explicit_equivalence(self):
        specs = []
        for direction in ("Front", "Back"):
            rows = source_rows(direction)
            original = copy.deepcopy(rows)
            for node, path in rows:
                rd = node["particle"]["renderer"]
                mid = str(rd["m_Materials"][0]["m_PathID"])
                material = {"dyn_params": {}, "viewport_clamp": R.viewport_plan(rd, POLICY, node["name"])}
                spec = N.emitter_spec(node, path, None, {}, {mid: "/Test/Smoke"}, material, POLICY)
                NiagaraBuilder.validate_spec(spec)
                self.assertFalse(spec["local_space"])  # Local source follows explicit current transforms.
                self.assertEqual(spec["particle_equivalence"], POLICY)
                RecordingBuilder().build_emitter(spec)
                specs.append(spec)
            self.assertEqual(rows, original)  # No disabling/cropping source branches.
        self.assertEqual(len(specs), 7)
        glow = next(s for s in specs if s["path"].endswith("/glow"))
        self.assertEqual(glow["source_particle_lights"], "unbound_no_light_renderer")
        self.assertEqual(len(glow["bursts"]), 1)
        distance = next(s for s in specs if s["path"] == "Local/Smoke_an (1)")
        self.assertEqual(distance["distance_rate"], 1)
        builder = RecordingBuilder()
        builder.build_emitter(distance)
        # The native distance emitter owns its count/remainder; our plan does
        # not add another emission accumulator or clock.
        self.assertTrue(any("SpawnPerUnit" in str(a) for name, a in builder.calls if name == "AddModule"))
        self.assertNotIn("SpawnRemainder", str(distance["emitter_update"]))
        self.assertIn("Emitter.UEFX_PreviousEmissionPosition", str(distance["emitter_spawn"]))

    def test_equivalence_never_hides_invalid_policy_or_missing_geometry_adapter(self):
        for field, value in (("mode", "unknown"), ("dampen_reference_seconds", 0),
                             ("dampen_strength", float("nan")), ("viewport_limit_scale", -1)):
            with self.assertRaises(P.MotionError):
                P.equivalence_policy({**POLICY, field: value})
        node, path = source_rows("Front")[0]
        mid = str(node["particle"]["renderer"]["m_Materials"][0]["m_PathID"])
        with self.assertRaisesRegex(N.SpecError, "viewport geometry adapter"):
            N.emitter_spec(node, path, None, {}, {mid: "/Test/Smoke"}, {"dyn_params": {}}, POLICY)
        clamp = copy.deepcopy(node["particle"]["system"]["ClampVelocityModule"])
        clamp["drag"]["scalar"] = 1
        with self.assertRaisesRegex(P.MotionError, "drag solver"):
            P.check_limit_velocity(clamp, "World/Smoke", POLICY)

    def test_generated_dampen_retains_inertia_and_frame_interval_decay(self):
        clamp = source_rows("Front")[0][0]["particle"]["system"]["ClampVelocityModule"]
        entries = P.dampen_entries(clamp, "limit", "Transient.velocity", N.f)
        def simulate(dt, steps, speed=4, limit=1):
            transient = SimpleNamespace(velocity=Vec((0, 0, speed)))
            ctx = math_context(Transient=transient, Engine=SimpleNamespace(DeltaTime=dt), limit=limit,
                Emitter=SimpleNamespace(UEFX_DampenReferenceSeconds=POLICY["dampen_reference_seconds"], UEFX_DampenStrength=1))
            for _ in range(steps):
                for name, _, expr in entries:
                    setattr(transient, name.split(".")[1], evaluate_expression(expr, ctx))
            return transient.velocity.z
        one = simulate(1/60, 1)
        self.assertAlmostEqual(one, 1+3*(1-clamp["dampen"]))
        self.assertGreater(one, 1)  # Soft limit, not hard clamp or drag of total speed.
        self.assertEqual(simulate(1/60, 1, .5), .5)
        self.assertEqual(simulate(0, 1), 4)
        self.assertEqual(simulate(1/60, 1, 0), 0)
        self.assertAlmostEqual(simulate(1/30, 15), simulate(1/120, 60), places=12)

    def test_source_scaling_modes_separate_shape_birth_from_displacement(self):
        chain = N.Chain()
        chain.push((0, 0, 0), (0, 0, 0, 1), (.4, .4, .4), None, None, "System.Age")
        for smode, expected_birth, expected_move in ((0, 80, 80), (1, 100, 100), (2, 80, 100)):
            scale = chain.S if smode == 0 else (1, 1, 1)
            spawn, update, _, _ = N.sprite_motion({"scalingMode": smode}, "Scaling", chain, scale,
                "shapeP", "shapeD", "float3(0.0,0.0,0.0)", True, N.Randoms(), N.CurveProgram("Update"))
            particles = SimpleNamespace(USpeed=1)
            ctx = math_context(Particles=particles, Transient=SimpleNamespace(), shapeP=Vec((0, 0, 1)), shapeD=Vec((0, 0, 1)),
                Engine=SimpleNamespace(DeltaTime=1, Owner=SimpleNamespace(Position=Vec((0, 0, 0)),
                            Rotation=Vec((0, 0, 0, 1)), Scale=Vec((2, 2, 2)))))
            for name, _, expr in spawn:
                setattr(particles, name.split(".")[1], evaluate_expression(expr, ctx))
            birth = particles.Position.y
            for name, _, expr in update:
                namespace = particles if name.startswith("Particles.") else ctx["Transient"]
                setattr(namespace, name.split(".")[1], evaluate_expression(expr, ctx))
            self.assertAlmostEqual(birth, expected_birth)
            self.assertAlmostEqual(particles.Position.y-birth, expected_move)

    def test_generated_viewport_geometry_handles_near_far_roll_and_orthographic_views(self):
        rd = source_rows("Front")[0][0]["particle"]["renderer"]
        viewport = R.viewport_plan(rd, POLICY, "Smoke")
        def offset(depth, rotation=0, ortho=False, size=(200, 400), scale=1):
            matrix = ((2, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0 if ortho else 1), (0, 0, 0, 1 if ortho else 0))
            ctx = math_context(PSize=Vec(size), PRot=rotation, CenterView=Vec((0, 0, depth)),
                RawWorldPos=Vec((100, 200, 0)), PPos=Vec((0, 0, 0)),
                ResolvedView=SimpleNamespace(ViewToClip=matrix),
                mul=lambda v, m: Vec(sum(v[i]*m[i][j] for i in range(4)) for j in range(4)),
                **{key: value["value"] for key, value in viewport["params"].items()})
            ctx["UEFX_ViewportLimitScale"] = scale
            code = "\n".join(line for line in viewport["code"].splitlines() if not line.startswith("//"))
            for statement in code.split(";"):
                statement = statement.strip()
                if not statement:
                    continue
                if statement.startswith("return "):
                    return evaluate_expression(statement[7:], ctx)
                variable, expression = statement.split("=", 1)
                ctx[variable.split()[-1]] = evaluate_expression(expression, ctx)
        self.assertEqual(offset(10000), (0, 0, 0))  # Unrestricted distant geometry remains unchanged.
        self.assertEqual(offset(100), (0, 0, 0))
        rolled = offset(100, math.pi/2)
        self.assertAlmostEqual(rolled.x, -25)  # Projected longest axis 4 -> max source bound 3.
        self.assertAlmostEqual(rolled.y, -50)
        self.assertEqual(offset(1, size=(0, 0)), (0, 0, 0))
        self.assertEqual(offset(1, ortho=True), offset(10000, ortho=True))
        self.assertGreater(offset(1, scale=2).x, offset(1).x)  # Tunable geometry extent; source colour unaffected.

    def test_native_material_graph_keeps_viewport_out_of_source_pixel_code(self):
        viewport = R.viewport_plan(source_rows("Front")[0][0]["particle"]["renderer"], POLICY, "Smoke")
        graph = RecordingMaterialGraph()
        session = SimpleNamespace(m=graph, begin_create=lambda p: None, created_asset=lambda p: None, save=lambda p: None)
        colour_code = "return float4(1.0, 0.5, 0.1, 0.5);"  # Graph fixture, not a source-shader substitute.
        plan = {"master": "M_GraphFixture", "shader": "Graph fixture", "renderer_kind": "particle", "mesh": False,
                "blend": "BLEND_Translucent", "two_sided": True, "builtins": ["CamPos"], "params": viewport["params"],
                "pixel_params": [], "textures": {}, "code": colour_code, "viewport_clamp": viewport,
                "disable_depth_test": True}
        MaterialBuilder(session).build_master(plan)
        custom = [v for v in graph.nodes.values() if v.get("OutputType")]
        pixel = next(v for v in custom if v["OutputType"] == "CMOT_Float4")
        geometry = next(v for v in custom if v["OutputType"] == "CMOT_Float3")
        self.assertEqual(pixel["Code"], colour_code)
        self.assertTrue(graph.nodes["/Test/Material"]["bDisableDepthTest"])
        self.assertEqual(pixel["Inputs"], [{"inputName": "CamPos"}])
        self.assertEqual([v["inputName"] for v in geometry["Inputs"]], viewport["inputs"])
        self.assertTrue(any(v.get("WorldPositionShaderOffset") == "WPT_ExcludeAllShaderOffsets" for v in graph.nodes.values()))
        self.assertTrue(any(v.get("TransformType") == "TRANSFORMPOSSOURCE_View" for v in graph.nodes.values()))
        outputs = [args["material_property"] for name, args in graph.calls if name.endswith(".connect_to_output")]
        self.assertEqual(set(outputs), {"MP_EmissiveColor", "MP_Opacity", "MP_WorldPositionOffset"})

    def test_missing_resolved_depth_state_does_not_create_a_material(self):
        graph = RecordingMaterialGraph()
        session = SimpleNamespace(m=graph, begin_create=lambda p: self.fail("Must not begin asset creation"))
        with self.assertRaisesRegex(ValueError, "resolved source depth-test"):
            MaterialBuilder(session).build_master({"output_contract": "color"})
        self.assertEqual(graph.calls, [])

    def test_lit_equivalent_graph_preserves_associated_rgb_at_zero_opacity(self):
        import zzz_fx_ue_equivalent as UE
        graph = RecordingMaterialGraph()
        session = SimpleNamespace(m=graph, begin_create=lambda p: None, created_asset=lambda p: None, save=lambda p: None)
        program = {"out": [{"name": "SV_Target", "index": 0, "reg": 0, "mask": "xyzw"}],
                   "asm": ["dcl_output o0.xyzw"]}
        plan = {"master": "M_LitGraphFixture", "shader": "Derived base-effect graph fixture", "renderer_kind": "particle", "mesh": False,
                "blend": "BLEND_AlphaComposite", "two_sided": True, "builtins": ["CamPos"], "params": {}, "textures": {},
                "pixel_params": [], "disable_depth_test": False, "code": "return float4(0.2, 0.1, 0.0, 0.0);",
                "ue_environment": UE.environment(program, "ue_volumetric_nondirectional")}
        MaterialBuilder(session).build_master(plan)
        properties = graph.nodes["/Test/Material"]
        self.assertEqual(properties["ShadingModel"], "MSM_DefaultLit")
        self.assertEqual(properties["TranslucencyLightingMode"], "TLM_VolumetricNonDirectional")
        self.assertEqual(properties["TranslucencyPass"], "MTP_BeforeDOF")
        custom = next(key for key, value in graph.nodes.items() if value.get("OutputType") == "CMOT_Float4")
        connections = {args["material_property"]: args["expression"]["refPath"]
                       for name, args in graph.calls if name.endswith(".connect_to_output")}
        self.assertEqual(connections["MP_BaseColor"], custom)
        self.assertNotEqual(connections["MP_EmissiveColor"], custom)
        self.assertEqual(graph.nodes[connections["MP_EmissiveColor"]]["R"], 0)
        self.assertEqual(graph.nodes[custom]["Code"], plan["code"])
        self.assertFalse(any("MaterialExpressionDivide" in klass for klass in graph.classes.values()))

    def test_material_lighting_readback_mismatch_aborts_before_shader_graph_or_save(self):
        import zzz_fx_ue_equivalent as UE
        class WrongLighting(RecordingMaterialGraph):
            def tool(self, name, **args):
                result = super().tool(name, **args)
                if name.endswith(".get_properties") and "ShadingModel" in args["properties"]:
                    actual = json.loads(result["returnValue"])
                    actual["ShadingModel"] = "MSM_Unlit"
                    result["returnValue"] = json.dumps(actual)
                return result
        graph = WrongLighting()
        session = SimpleNamespace(m=graph, begin_create=lambda p: None, created_asset=lambda p: None,
                                  save=lambda p: self.fail("Mismatched lighting must not save"))
        program = {"out": [{"name": "SV_Target", "index": 0, "reg": 0, "mask": "xyzw"}], "asm": ["dcl_output o0.xyzw"]}
        plan = {"master": "M_ReadbackFixture", "renderer_kind": "particle", "mesh": False,
                "blend": "BLEND_AlphaComposite", "two_sided": True, "disable_depth_test": False,
                "ue_environment": UE.environment(program, "ue_volumetric_nondirectional")}
        with self.assertRaisesRegex(RuntimeError, "ShadingModel.*MSM_DefaultLit.*MSM_Unlit"):
            MaterialBuilder(session).build_master(plan)
        self.assertEqual(len(graph.nodes), 1)


if __name__ == "__main__":
    unittest.main()
