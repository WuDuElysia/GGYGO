"""DXBC value/address dependencies must survive output-driven pruning."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import zzz_dxbc_hlsl as T


def program(*instructions, profile="ps_5_0"):
    return {
        "asm": [profile, "dcl_temps 4", "dcl_indexableTemp x0[5], 4",
                "dcl_indexableTemp x1[5], 4", "dcl_output o0.xyzw",
                *instructions, "ret"],
        "bind": {
            "cbbind": {1: "UnityPerMaterial"},
            "cb": {"UnityPerMaterial": {"size": 1056, "params": [
                {"kind": "V", "name": "_Index", "offset": 1028,
                 "dim": 1, "arr": 0, "type": 0},
                {"kind": "V", "name": "_OuterIndex", "offset": 1032,
                 "dim": 1, "arr": 0, "type": 0}]}},
            "tex": {0: {"name": "TestTexture", "sampler": 0, "dim": 2}},
            "smp": {},
        },
    }


INDEX_WRITE = "br0.y = (uint)(_Index);"
ARRAY_WRITE = "bx0[br0.y].x = bv8.y;"


class TranslationCase(unittest.TestCase):
    def translated(self, *instructions, outputs=None, profile="ps_5_0"):
        return T.translate(program(*instructions, profile=profile), "b", {},
                           {0: "x"} if outputs is None else outputs)

    def assert_index_definition(self, result):
        self.assertIn(INDEX_WRITE, result["code"])
        self.assertIn("_Index", result["mat_params"])


class AddressDependencyTests(TranslationCase):
    def test_back03_original_ftou_before_dynamic_destination(self):
        # Preserve the original address producer and write verbatim. Keep the
        # earlier front-face bit value live to reproduce the stale-index path.
        result = self.translated(
            "movc r0.y, v11.x, l(1.000000), l(-1.000000)",
            "mov o0.y, r0.y",
            "mov x0[4].x, l(0.000000)",
            "ftou r0.y, cb1[64].y",
            "mov x0[r0.y + 0].x, v8.y",
            "mov o0.x, x0[4].x", outputs={0: "xy"})
        self.assert_index_definition(result)
        self.assertIn(ARRAY_WRITE, result["code"])
        self.assertLess(result["code"].index(INDEX_WRITE),
                        result["code"].index(ARRAY_WRITE))
        self.assertEqual(set(result["live_inputs"]), {("v11", "x"), ("v8", "y")})

    def test_arithmetic_families_read_destination_address(self):
        instructions = ["mov x0[r0.y + 0].x, v8.y",
                        "movc x0[r0.y + 0].x, v11.x, v8.y, l(0.000000)",
                        "mad x0[r0.y + 0].x, v8.y, v8.y, v8.y",
                        "not x0[r0.y + 0].x, v8.y",
                        "ineg x0[r0.y + 0].x, v8.y"]
        instructions += ["%s x0[r0.y + 0].x, v8.y" % op
                         for op in (*T.FLOAT_UNARY, *T.CONV)]
        instructions += ["%s x0[r0.y + 0].x, v8.y, v8.y" % op
                         for op in (*T.FLOAT_BINARY, *T.FLOAT_CMP,
                                    *T.INT_BINARY, *T.INT_CMP, "dp2", "dp3", "dp4")]
        for instruction in instructions:
            with self.subTest(instruction=instruction):
                result = self.translated("ftou r0.y, cb1[64].y", instruction,
                                         "mov o0.x, x0[4].x")
                self.assert_index_definition(result)

    def test_sample_entry_points_read_destination_address(self):
        for base, suffix in (("sample", ""), ("sample_l", ", v3.x"),
                             ("sample_b", ", v3.y")):
            for indexable in (False, True):
                op = base + ("_indexable(texture2d)(float,float,float,float)"
                             if indexable else "")
                with self.subTest(op=op):
                    result = self.translated(
                        "ftou r0.y, cb1[64].y",
                        op + " x0[r0.y + 0].x, v1.xyxx, t0.xyzw, s0" + suffix,
                        "mov o0.x, x0[4].x")
                    self.assert_index_definition(result)
                    self.assertIn("TestTexture", result["textures"])
                    self.assertIn(("v1", "x"), result["live_inputs"])
                    self.assertIn(("v1", "y"), result["live_inputs"])
                    if suffix:
                        self.assertIn(("v3", suffix[-1]), result["live_inputs"])

    def test_sincos_reads_each_nonnull_destination_address(self):
        for instruction in ("sincos x0[r0.y + 0].x, null, v8.y",
                            "sincos null, x0[r0.y + 0].x, v8.y",
                            "sincos x0[r0.y + 0].x, x1[r0.z + 0].x, v8.y"):
            with self.subTest(instruction=instruction):
                result = self.translated("ftou r0.y, cb1[64].y", "mov r0.z, v2.z",
                                         instruction, "mov o0.x, x0[4].x")
                self.assert_index_definition(result)
                if "x1[" in instruction:
                    self.assertIn(("v2", "z"), result["live_inputs"])
                else:
                    self.assertNotIn(("v2", "z"), result["live_inputs"])

    def test_address_dependency_applies_to_vs_and_nonzero_offset(self):
        result = self.translated("ftou r0.y, cb1[64].y",
                                 "mov x0[r0.y + 1].x, v8.y", "mov o0.x, x0[4].x",
                                 profile="vs_5_0")
        self.assert_index_definition(result)
        self.assertIn("bx0[br0.y + 1].x = bv8.y;", result["code"])

    def test_destination_value_is_not_an_address_read(self):
        result = self.translated("mov r0.y, v2.x", "mov r0.y, v3.y",
                                 "mov o0.x, r0.y")
        self.assertEqual(result["live_inputs"], [("v3", "y")])
        self.assertNotIn("bv2.x", result["code"])

    def test_dead_array_write_still_prunes_its_index_and_inputs(self):
        result = self.translated("ftou r0.y, cb1[64].y",
                                 "mov x0[r0.y + 0].x, v8.y",
                                 "mov o0.x, l(1.000000)")
        self.assertNotIn(INDEX_WRITE, result["code"])
        self.assertNotIn("bx0[br0.y]", result["code"])
        self.assertEqual(result["live_inputs"], [])
        self.assertEqual(dict(result["mat_params"]), {})

    def test_undefined_live_destination_address_is_rejected(self):
        with self.assertRaisesRegex(T.TranslateError, "写入前被读取"):
            self.translated("mov x0[r0.y + 0].x, v8.y", "mov o0.x, x0[4].x")

    def test_missing_provider_for_live_address_is_rejected_but_dead_is_pruned(self):
        source = program("ftou r0.y, cb1[64].y", "mov x0[r0.y + 0].x, v8.y",
                         "mov o0.x, x0[4].x")
        source["bind"]["cbbind"][1] = "AddressGlobals"
        source["bind"]["cb"]["AddressGlobals"] = source["bind"]["cb"].pop("UnityPerMaterial")
        with self.assertRaisesRegex(T.TranslateError, "没有提供方"):
            T.translate(source, "b", {}, {0: "x"})
        source["asm"][-2] = "mov o0.x, l(1.000000)"
        result = T.translate(source, "b", {}, {0: "x"})
        self.assertEqual(result["missing"], [])

    def test_existing_dynamic_source_addresses_remain_live(self):
        for operand in ("x0[r0.y + 0].x", "icb[r0.y + 0].x", "cb2[r0.y + 0].x"):
            with self.subTest(operand=operand):
                source = program("ftou r0.y, cb1[64].y", "mov o0.x, " + operand)
                source["asm"].insert(1, "dcl_immediateConstantBuffer { {1, 2, 3, 4} }")
                source["bind"]["cbbind"][2] = "Globals"
                source["bind"]["cb"]["Globals"] = {"size": 16, "params": [
                    {"kind": "V", "name": "Lookup", "offset": 0,
                     "dim": 4, "arr": 1, "type": 0}]}
                result = T.translate(source, "b", {"Lookup": {"rows": ["float4(1,2,3,4)"]}}, {0: "x"})
                self.assert_index_definition(result)

    def test_both_branch_index_definitions_and_predicate_survive(self):
        result = self.translated("if_nz v11.x", "ftou r0.y, cb1[64].y", "else",
                                 "mov r0.y, v2.z", "endif",
                                 "mov x0[r0.y + 0].x, v8.y", "mov o0.x, x0[4].x")
        self.assert_index_definition(result)
        self.assertEqual(set(result["live_inputs"]), {("v11", "x"), ("v2", "z"), ("v8", "y")})

    def test_missing_definition_on_one_branch_is_rejected(self):
        with self.assertRaisesRegex(T.TranslateError, "写入前被读取"):
            self.translated("if_nz v11.x", "ftou r0.y, cb1[64].y", "endif",
                             "mov x0[r0.y + 0].x, v8.y", "mov o0.x, x0[4].x")


class LoopAddressTests(TranslationCase):
    def test_zero_condition_loop_jumps_keep_their_target_dependencies(self):
        result = self.translated("loop", "ftou r0.y, cb1[64].y", "breakc_z v11.x",
                                 "mov r0.y, l(0)", "endloop",
                                 "mov x0[r0.y + 0].x, v8.y", "mov o0.x, x0[4].x")
        self.assert_index_definition(result)
        result = self.translated("mov r0.y, l(0)", "loop",
                                 "mov x0[r0.y + 0].x, v8.y",
                                 "ftou r0.y, cb1[64].y", "continuec_z v11.x",
                                 "mov r0.y, l(1)", "break", "endloop",
                                 "mov o0.x, x0[4].x")
        self.assert_index_definition(result)

    def test_conditional_break_preserves_the_index_at_loop_exit(self):
        result = self.translated("loop", "ftou r0.y, cb1[64].y", "breakc_nz v11.x",
                                 "mov r0.y, l(0)", "endloop",
                                 "mov x0[r0.y + 0].x, v8.y", "mov o0.x, x0[4].x")
        self.assert_index_definition(result)

    def test_break_in_branch_preserves_the_index_at_loop_exit(self):
        result = self.translated("loop", "ftou r0.y, cb1[64].y",
                                 "if_nz v11.x", "break", "endif",
                                 "mov r0.y, l(0)", "endloop",
                                 "mov x0[r0.y + 0].x, v8.y", "mov o0.x, x0[4].x")
        self.assert_index_definition(result)

    def test_continue_preserves_index_for_the_next_iteration(self):
        result = self.translated("mov r0.y, l(0)", "loop",
                                 "mov x0[r0.y + 0].x, v8.y",
                                 "ftou r0.y, cb1[64].y", "continuec_nz v11.x",
                                 "mov r0.y, l(1)", "break", "endloop",
                                 "mov o0.x, x0[4].x")
        self.assert_index_definition(result)
        self.assertNotIn("br0.y = 1u;", result["code"])

    def test_nested_loop_exit_uses_nearest_break_target(self):
        result = self.translated("loop", "ftou r0.y, cb1[64].z", "loop",
                                 "ftou r0.y, cb1[64].y", "break", "endloop",
                                 "break", "endloop", "mov x0[r0.y + 0].x, v8.y",
                                 "mov o0.x, x0[4].x")
        self.assert_index_definition(result)
        self.assertNotIn("_OuterIndex", result["mat_params"])

    def test_unconditional_continue_prunes_unreachable_index_write(self):
        result = self.translated("mov r0.y, l(0)", "loop",
                                 "mov x0[r0.y + 0].x, v8.y",
                                 "if_nz v11.x", "break", "endif",
                                 "ftou r0.y, cb1[64].y", "continue",
                                 "mov r0.y, l(3)", "endloop",
                                 "mov o0.x, x0[4].x")
        self.assert_index_definition(result)
        self.assertNotIn("br0.y = 3u;", result["code"])

    def test_break_before_index_definition_does_not_hide_undefined_input(self):
        with self.assertRaisesRegex(T.TranslateError, "写入前被读取"):
            self.translated("loop", "breakc_nz v11.x", "ftou r0.y, cb1[64].y",
                             "endloop", "mov x0[r0.y + 0].x, v8.y", "mov o0.x, x0[4].x")

    def test_control_predicates_preserve_their_material_bindings(self):
        for instructions in (("discard_nz cb1[64].y",),
                             ("discard_z cb1[64].y",),
                             ("loop", "breakc_nz cb1[64].y", "endloop"),
                             ("loop", "continuec_z cb1[64].y", "break", "endloop")):
            with self.subTest(instructions=instructions):
                result = self.translated(*instructions, "mov o0.x, l(1.000000)")
                self.assertIn("_Index", result["mat_params"])

    def test_missing_control_predicate_provider_is_rejected(self):
        source = program("discard_nz cb1[64].y", "mov o0.x, l(1.000000)")
        source["bind"]["cbbind"][1] = "PredicateGlobals"
        source["bind"]["cb"]["PredicateGlobals"] = source["bind"]["cb"].pop("UnityPerMaterial")
        with self.assertRaisesRegex(T.TranslateError, "没有提供方"):
            T.translate(source, "b", {}, {0: "x"})

    def test_loop_jump_outside_loop_is_rejected(self):
        for jump in ("break", "continue", "breakc_nz v11.x", "continuec_z v11.x"):
            with self.subTest(jump=jump), self.assertRaisesRegex(T.TranslateError, "loop"):
                self.translated(jump, "mov o0.x, l(1.000000)")


if __name__ == "__main__":
    unittest.main()
