"""DXBC value/address dependencies must survive output-driven pruning."""
import ast
import re
import struct
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


def bfi_reference(width, offset, insert, base):
    """Independent bit-by-bit oracle; do not reuse the emitted mask formula."""
    result = base & 0xFFFFFFFF
    for bit in range(32):
        if (offset & 31) <= bit < (offset & 31) + (width & 31):
            value = (insert >> (bit - (offset & 31))) & 1
            result = (result & ~(1 << bit)) | (value << bit)
    return result


def emitted_uint_rhs(text, registers=None):
    """Evaluate only the emitted bfi expression's unsigned HLSL subset."""
    expression = text.split(" = ", 1)[1].removesuffix(";")
    expression = re.sub(r"\b(\d+)u\b", r"\1", expression)
    registers = registers or {}

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            return registers[node.value.id]["xyzw".index(node.attr)]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            values = [visit(arg) for arg in node.args]
            if re.fullmatch(r"uint[234]", node.func.id) and len(values) == int(node.func.id[-1]):
                return tuple(values)
            if node.func.id == "asuint" and len(values) == 1:
                return struct.unpack("<I", struct.pack("<f", values[0]))[0]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
            return ~visit(node.operand) & 0xFFFFFFFF
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.BitAnd):
                value = left & right
            elif isinstance(node.op, ast.BitOr):
                value = left | right
            elif isinstance(node.op, ast.LShift):
                if not 0 <= right < 32:
                    raise ValueError("emitted shift count is outside uint32")
                value = left << right
            elif isinstance(node.op, ast.Sub):
                value = left - right
            else:
                raise ValueError("unsupported emitted operator")
            return value & 0xFFFFFFFF
        raise ValueError("unsupported emitted expression: " + ast.dump(node))

    return visit(ast.parse(expression, mode="eval").body)


class BfiTests(TranslationCase):
    def instruction(self, text):
        return T.translate_ins(T.Ctx(program(), "b", {}), *T.split_instr(text))

    def test_original_aura_dither_pair_keeps_pixel_and_icb_chain(self):
        pair = ("bfi r2.y, l(2), l(2), r2.y, l(0)",
                "bfi r2.y, l(2), l(0), r2.z, r2.y")
        source = program("ftou r2.yz, v0.xxyx", *pair,
                         "add r2.y, v1.x, -icb[r2.y + 4].x",
                         "lt r2.y, r2.y, l(0.000000)", "discard_nz r2.y",
                         "mov o0.x, v2.x")
        rows = ", ".join("{0, 0, 0, 0}" for _ in range(20))
        source["asm"].insert(1, "dcl_immediateConstantBuffer { " + rows + " }")
        result = T.translate(source, "b", {}, {0: "x"})
        self.assertIn("br2.yz = (uint2)(asfloat(bv0.xy));", result["code"])
        self.assertIn("bicb[br2.y + 4].x", result["code"])
        self.assertIn("if (br2.y != 0u) { clip(-1.0); }", result["code"])
        self.assertEqual(set(result["live_inputs"]),
                         {("v0", "x"), ("v0", "y"), ("v1", "x"), ("v2", "x")})
        lines = [self.instruction(text).text for text in pair]
        for x in range(8):
            for y in range(8):
                with self.subTest(x=x, y=y):
                    first = emitted_uint_rhs(lines[0], {"br2": (0, x, y, 0)})
                    final = emitted_uint_rhs(lines[1], {"br2": (0, first, y, 0)})
                    self.assertEqual(final, (x % 4) * 4 + y % 4)
        self.assertTrue(all(line in result["code"] for line in lines))

    def test_uint32_boundaries_and_raw_literal_bits(self):
        cases = [(0, 7, 0xFFFFFFFF, 0xA5A5A5A5),
                 (32, 7, 0xFFFFFFFF, 0xA5A5A5A5), (33, 0, 1, 0),
                 (31, 1, 0xFFFFFFFF, 1), (31, 31, 1, 0),
                 (31, 31, 0, 0xFFFFFFFF), (2, 32, 3, 0),
                 (0xFFFFFFFF, 0xFFFFFFFF, 1, 0), (31, 0, 0, 0xFFFFFFFF)]
        for values in cases:
            with self.subTest(values=values):
                text = "bfi r0.x, " + ", ".join("l(0x%08x)" % v for v in values)
                actual = emitted_uint_rhs(self.instruction(text).text)
                self.assertEqual(actual, bfi_reference(*values))
        actual = emitted_uint_rhs(self.instruction(
            "bfi r0.x, l(31), l(0), l(1.000000), l(-1)").text)
        self.assertEqual(actual, bfi_reference(31, 0, 0x3F800000, 0xFFFFFFFF))

    def test_masked_swizzles_and_scalar_broadcast(self):
        registers = {"bv1": (0, 31, 33, 2), "bv2": (31, 0, 32, 1),
                     "bv3": (0xFFFFFFFF, 3, 1, 0), "bv4": (0, 1, 2, 0xA5A5A5A5)}
        for mask in ("x", "yw", "xyz", "xyzw"):
            with self.subTest(mask=mask):
                ins = self.instruction("bfi r0." + mask + ", v1.wzyx, v2.zwxy, v3.yxxx, v4.w")
                expected, uses = [], set()
                for c in mask:
                    p = "xyzw".index(c)
                    components = ("wzyx"[p], "zwxy"[p], "yxxx"[p], "w")
                    values = [registers["bv%d" % i]["xyzw".index(s)]
                              for i, s in enumerate(components, 1)]
                    expected.append(bfi_reference(*values))
                    uses.update(("v%d" % i, s) for i, s in enumerate(components, 1))
                self.assertEqual(emitted_uint_rhs(ins.text, registers),
                                 expected[0] if len(mask) == 1 else tuple(expected))
                self.assertEqual(ins.uses, uses)
                self.assertEqual(ins.defs, [("r0", c, True) for c in mask])

    def test_aliased_swizzle_reads_all_old_components_before_one_write(self):
        ins = self.instruction("bfi r0.xy, l(2), l(0), r0.yxxx, r0.zwxx")
        old = (2, 1, 0xA5A5A5A5, 0x5A5A5A5A)
        self.assertEqual(ins.text.count(" = "), 1)
        self.assertEqual(ins.text.count(";"), 1)
        self.assertEqual(emitted_uint_rhs(ins.text, {"br0": old}),
                         (bfi_reference(2, 0, old[1], old[2]),
                          bfi_reference(2, 0, old[0], old[3])))
        self.assertEqual(ins.uses, {("r0", c) for c in "xyzw"})
        result = self.translated("mov r0.xyzw, v1.xyzw",
                                 "bfi r0.xy, l(2), l(0), r0.yxxx, r0.zwxx",
                                 "mov o0.xy, r0.xyxx", outputs={0: "xy"})
        self.assertEqual(set(result["live_inputs"]), {("v1", c) for c in "xyzw"})

    def test_dynamic_destination_address_stays_live_and_undefined_is_rejected(self):
        text = "bfi x0[r0.y + 0].x, l(2), l(0), v8.y, v3.z"
        result = self.translated("ftou r0.y, cb1[64].y", text, "mov o0.x, x0[4].x")
        self.assert_index_definition(result)
        self.assertEqual(set(result["live_inputs"]), {("v8", "y"), ("v3", "z")})
        with self.assertRaisesRegex(T.TranslateError, "写入前被读取"):
            self.translated(text, "mov o0.x, x0[4].x")

    def test_each_of_four_sources_is_a_live_read(self):
        for i in range(4):
            operands = ["l(2)", "l(0)", "l(3)", "l(0)"]
            operands[i] = "r1.y"
            text = "bfi r0.x, " + ", ".join(operands)
            with self.subTest(source=i):
                result = self.translated("mov r1.y, v1.z", text, "mov o0.x, r0.x")
                self.assertEqual(result["live_inputs"], [("v1", "z")])
                with self.assertRaisesRegex(T.TranslateError, "写入前被读取"):
                    self.translated(text, "mov o0.x, r0.x")

    def test_dead_bfi_prunes_source_address_and_missing_globals(self):
        source = program("ftou r1.y, cb1[64].y",
                         "bfi r0.x, cb2[0].x, l(0), x0[r1.y + 0].x, v3.w",
                         "mov o0.x, r0.x")
        source["bind"]["cbbind"][2] = "Globals"
        source["bind"]["cb"]["Globals"] = {"size": 16, "params": [
            {"kind": "V", "name": "Width", "offset": 0, "dim": 1, "arr": 0, "type": 0}]}
        with self.assertRaisesRegex(T.TranslateError, "没有提供方"):
            T.translate(source, "b", {}, {0: "x"})
        source["asm"][-2] = "mov o0.x, l(1.000000)"
        result = T.translate(source, "b", {}, {0: "x"})
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["live_inputs"], [])
        self.assertEqual(dict(result["mat_params"]), {})
        self.assertNotIn("<<", result["code"])
        self.assertNotIn("bx0[br1.y]", result["code"])

    def test_live_source_array_address_and_vs_path(self):
        result = self.translated("ftou r1.y, cb1[64].y",
                                 "bfi o0.x, l(2), l(0), x0[r1.y + 0].x, v3.w",
                                 profile="vs_5_0")
        self.assertIn("br1.y = (uint)(_Index);", result["code"])
        self.assertEqual(result["live_inputs"], [("v3", "w")])
        with self.assertRaisesRegex(T.TranslateError, "写入前被读取"):
            self.translated("bfi o0.x, l(2), l(0), x0[r1.y + 0].x, v3.w")

    def test_invalid_saturate_or_arity_is_rejected(self):
        for text, message in (("bfi_sat r0.x, l(2), l(0), l(3), l(0)", "_sat"),
                              ("bfi", "四个源"),
                              ("bfi r0.x, l(2), l(0), l(3)", "四个源"),
                              ("bfi r0.x, l(2), l(0), l(3), l(0), l(1)", "四个源")):
            with self.subTest(text=text), self.assertRaisesRegex(T.TranslateError, message):
                self.instruction(text)


if __name__ == "__main__":
    unittest.main()
