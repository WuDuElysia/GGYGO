"""Check generated weighted-curve expressions against analytic cubic curves."""
import sys
import math
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import zzz_fx_niagara as N


class Vec4(tuple):
    x = property(lambda value: value[0])
    y = property(lambda value: value[1])
    z = property(lambda value: value[2])
    w = property(lambda value: value[3])


def evaluate_generated(program, output, time):
    # Evaluate only the locally generated arithmetic expressions used by the
    # test fixture, with no builtins or source-file HLSL execution.
    values = {"t": time, "float4": lambda *parts: Vec4(parts),
              "saturate": lambda value: min(1, max(0, value))}
    for name, _, expression in program.entries:
        expression = expression.replace(program.prefix, "v")
        if "?" in expression:
            expression = expression[1:-1]
            condition, branches = expression.split("?", 1)
            true, false = branches.split(":", 1)
            expression = true if eval(condition, {"__builtins__": {}}, values) else false
        values[name.replace(program.prefix, "v")] = eval(expression, {"__builtins__": {}}, values)
    return values[output.replace(program.prefix, "v")]


class WeightedCurveTests(unittest.TestCase):
    def test_weighted_equal_thirds_matches_analytic_smoothstep(self):
        a = {"time": 0, "value": 0, "outSlope": 0, "weightedMode": 2, "outWeight": 1/3}
        b = {"time": 1, "value": 1, "inSlope": 0, "weightedMode": 1, "inWeight": 1/3}
        program = N.CurveProgram("Test")
        output = N.weighted_segment_h(a, b, "t", program)
        # Includes points between the old 1/16 sampling intervals.
        for time in (0, .013, .09, .233, .499, .73, .98, 1):
            self.assertAlmostEqual(evaluate_generated(program, output, time), 3*time*time-2*time**3, delta=2e-7)

    def test_equal_x_y_bezier_remains_linear_with_nonuniform_time_handles(self):
        a = {"time": 2, "value": 2, "outSlope": 1, "weightedMode": 2, "outWeight": .1}
        b = {"time": 5, "value": 5, "inSlope": 1, "weightedMode": 1, "inWeight": .7}
        program = N.CurveProgram("Test")
        output = N.weighted_segment_h(a, b, "t", program)
        for time in (2, 2.013, 2.53, 3.17, 4.52, 5):
            self.assertAlmostEqual(evaluate_generated(program, output, time), time, delta=4e-7)

    def test_weighted_segments_cannot_fall_back_to_linear_sampling(self):
        a = {"time": 0, "value": 0, "outSlope": 0, "weightedMode": 2, "outWeight": .4}
        b = {"time": 1, "value": 1, "inSlope": 0, "weightedMode": 1, "inWeight": .4}
        with self.assertRaises(N.SpecError):
            N.weighted_segment_h(a, b, "t", None)

    def test_invalid_time_handles_are_rejected(self):
        a = {"time": 0, "value": 0, "outSlope": 0, "weightedMode": 2, "outWeight": 1.2}
        b = {"time": 1, "value": 1, "inSlope": 0, "weightedMode": 1, "inWeight": .4}
        with self.assertRaises(N.SpecError):
            N.weighted_segment_h(a, b, "t", N.CurveProgram("Test"))

    def test_quaternion_conversion_commutes_with_mesh_axis_conversion(self):
        def axis_conversion(vector):
            return (-vector[0], vector[2], vector[1])
        qexpr = N.ue_quat_h("q")
        rotations = [N.qeuler_zxy(math.pi/2, 0, 0), N.qeuler_zxy(0, math.pi/2, 0),
                     N.qeuler_zxy(0, 0, math.pi/2), N.qeuler_zxy(.31, -.77, 1.23)]
        for rotation in rotations:
            converted = eval(qexpr, {"__builtins__": {}}, {"q": Vec4(rotation), "float4": lambda *v: Vec4(v)})
            for vector in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (.1, -.3, .7)):
                expected = axis_conversion(N.qrot(rotation, vector))
                actual = N.qrot(converted, axis_conversion(vector))
                for a, b in zip(actual, expected):
                    self.assertAlmostEqual(a, b, places=12)


if __name__ == "__main__":
    unittest.main()
