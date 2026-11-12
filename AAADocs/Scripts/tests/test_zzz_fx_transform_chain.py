"""变换交换与动画整区间的真实回归；矩阵 oracle 独立于生成器 TRS 运算。

源夹具来自 Normal01 的 root/Trail/rot/Shining 与原 11 键旋转；不含角色特判。
本测试不导入 Unreal，不将离线矩阵一致性提升为保存或 Native 验收。
"""

from copy import deepcopy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import zzz_fx_niagara as N

SOURCE_NODES = [{'name': 'root', 'pos': {'x': -0.0645131841301918, 'y': 0.10999999940395355, 'z': -0.07702159881591797}, 'rot': {'x': 0.058891553431749344, 'y': 0.00731752859428525, 'z': -0.05331580713391304, 'w': 0.9968127608299255}, 'scale': {'x': 1.0, 'y': 1.0, 'z': 1.0}}, {'name': 'Trail', 'pos': {'x': -0.09000000357627869, 'y': 1.1299999952316284, 'z': -0.05000000074505806}, 'rot': {'x': -0.05520937964320183, 'y': 0.05739675834774971, 'z': 0.9816156625747681, 'w': -0.1734597086906433}, 'scale': {'x': 0.8500000238418579, 'y': 0.8999999761581421, 'z': 0.8500000238418579}}, {'name': 'rot', 'pos': {'x': 0.0, 'y': 0.0, 'z': 0.0}, 'rot': {'x': 0.0, 'y': 0.6545693278312683, 'z': 0.0, 'w': -0.7560020089149475}, 'scale': {'x': 1.0, 'y': 1.0, 'z': 1.0}}, {'name': 'Shining', 'pos': {'x': 0.0, 'y': 0.0, 'z': 0.0}, 'rot': {'x': 0.9233577251434326, 'y': -1.4901162970204496e-08, 'z': 0.38394078612327576, 'w': 0.0}, 'scale': {'x': 1.0, 'y': 1.0, 'z': 1.0}}]
SOURCE_KEYS = [{'time': 0.0, 'value': [-0.0, -0.9976432, -0.0, 0.06861588], 'in': [0.0, 30.182474, 0.0, -56.26413], 'out': [0.0, 30.182474, 0.0, -56.26413], 'weighted': 0}, {'time': 0.016666668, 'value': [-0.0, -0.4946019, -0.0, -0.86911964], 'in': [0.0, 41.80119, 0.0, -29.609484], 'out': [0.0, 41.80119, 0.0, -29.609484], 'weighted': 0}, {'time': 0.033333335, 'value': [-0.0, 0.39572984, -0.0, -0.91836697], 'in': [0.0, 29.859478, 0.0, 0.10520685], 'out': [0.0, 29.859478, 0.0, 0.10520685], 'weighted': 0}, {'time': 0.050000004, 'value': [-0.0, 0.50071406, -0.0, -0.86561275], 'in': [0.0, 5.2690344, 0.0, 2.9301128], 'out': [0.0, 5.2690344, 0.0, 2.9301128], 'weighted': 0}, {'time': 0.06666667, 'value': [-0.0, 0.57136434, -0.0, -0.82069653], 'in': [0.0, 3.4593148, 0.0, 2.3365743], 'out': [0.0, 3.4593148, 0.0, 2.3365743], 'weighted': 0}, {'time': 0.083333336, 'value': [-0.0, 0.61602455, -0.0, -0.78772694], 'in': [0.0, 2.106811, 0.0, 1.6094972], 'out': [0.0, 2.106811, 0.0, 1.6094972], 'weighted': 0}, {'time': 0.1, 'value': [-0.0, 0.64159137, -0.0, -0.76704663], 'in': [0.0, 1.1291529, 0.0, 0.92823577], 'out': [0.0, 1.1291529, 0.0, 0.92823577], 'weighted': 0}, {'time': 0.11666667, 'value': [-0.0, 0.653663, -0.0, -0.75678575], 'in': [0.0, 0.4617083, 0.0, 0.39420247], 'out': [0.0, 0.4617083, 0.0, 0.39420247], 'weighted': 0}, {'time': 0.13333334, 'value': [-0.0, 0.65698165, -0.0, -0.75390655], 'in': [0.0, 0.06641503, 0.0, 0.05753514], 'out': [0.0, 0.06641503, 0.0, 0.05753514], 'weighted': 0}, {'time': 0.15, 'value': [-0.0, 0.6558768, -0.0, -0.7548679], 'in': [0.0, -0.07236958, 0.0, -0.062863834], 'out': [0.0, -0.07236958, 0.0, -0.062863834], 'weighted': 0}, {'time': 0.16666667, 'value': [-0.0, 0.6545693, -0.0, -0.756002], 'in': [0.0, -0.07844926, 0.0, -0.06804586], 'out': [0.0, -0.07844926, 0.0, -0.06804586], 'weighted': 0}]


def quaternion_matrix(q):
    x, y, z, w = q
    return ((1 - 2 * (y*y + z*z), 2 * (x*y - w*z), 2 * (x*z + w*y)),
            (2 * (x*y + w*z), 1 - 2 * (x*x + z*z), 2 * (y*z - w*x)),
            (2 * (x*z - w*y), 2 * (y*z + w*x), 1 - 2 * (x*x + y*y)))


def matmul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def matvec(a, vector):
    return tuple(sum(a[i][j] * vector[j] for j in range(3)) for i in range(3))


def rotation_at(keys, time):
    if time <= keys[0]["time"]:
        q = keys[0]["value"]
    elif time >= keys[-1]["time"]:
        q = keys[-1]["value"]
    else:
        a, b = next((a, b) for a, b in zip(keys, keys[1:]) if a["time"] <= time <= b["time"])
        dt = b["time"] - a["time"]
        t = (time - a["time"]) / dt
        h00, h10, h01, h11 = 2*t**3 - 3*t*t + 1, t**3 - 2*t*t + t, -2*t**3 + 3*t*t, t**3 - t*t
        q = tuple(h00*a["value"][i] + h10*dt*a["out"][i] + h01*b["value"][i] + h11*dt*b["in"][i]
                  for i in range(4))
    norm = math.sqrt(sum(value * value for value in q))
    return tuple(value / norm for value in q)


def curve(values, outgoing=None):
    result = [{"time": float(i), "value": tuple(q), "in": (0.,)*4, "out": (0.,)*4, "weighted": 0}
              for i, q in enumerate(values)]
    if outgoing is not None:
        result[0]["out"] = outgoing
    return result


class TransformCommutationTests(unittest.TestCase):
    def setUp(self):
        self.chain = N.Chain()
        self.chain.S = (.8500000238418579, .8999999761581421, .8500000238418579)

    def test_oblique_half_turn_preserves_source_scale_subspaces(self):
        q = tuple(SOURCE_NODES[-1]["rot"][axis] for axis in "xyzw")
        self.assertTrue(self.chain.commutes(q))
        r = quaternion_matrix(q)
        self.assertLess(max(abs((self.chain.S[i] - self.chain.S[j]) * r[i][j])
                            for i in range(3) for j in range(3)), 2e-9)

    def test_constant_half_turn_with_three_distinct_scales_is_supported(self):
        self.chain.S = (1., 2., 3.)
        self.assertTrue(self.chain.commutes((1., 0., 0., 0.)))

    def test_real_45_degree_x_noncommutation_is_refused(self):
        q = (math.sin(math.pi/8), 0., 0., math.cos(math.pi/8))
        self.assertFalse(self.chain.commutes(q))
        self.chain.push((0., 0., 0.), q, (1., 1., 1.))
        self.assertTrue(self.chain.sheared)
        with self.assertRaises(N.SpecError):
            self.chain.push((0., 0., 0.), (0., 0., 0., 1.), (1., 1., 1.))

    def test_endpoints_do_not_authorize_a_noncommuting_interval(self):
        keys = curve(((0., 0., 0., 1.), (1., 0., 0., 0.)))
        self.assertTrue(all(self.chain.commutes(key["value"]) for key in keys))
        self.assertFalse(self.chain.commutes(rotation_at(keys, .5)))
        self.assertFalse(self.chain.rotation_curve_commutes(keys))
        with self.assertRaises(N.SpecError):
            self.chain.push((0.,)*3, (0., 0., 0., 1.), (1.,)*3, anim_rot=keys, t="System.Age")

    def test_tangents_cannot_leave_a_commuting_endpoint_subspace(self):
        keys = curve(((0., 0., 0., 1.), (0., 0., 0., 1.)), outgoing=(1., 0., 0., 0.))
        self.assertTrue(all(self.chain.commutes(key["value"]) for key in keys))
        self.assertFalse(self.chain.commutes(rotation_at(keys, .5)))
        self.assertFalse(self.chain.rotation_curve_commutes(keys))

    def test_source_y_curve_entire_support_is_commuting(self):
        self.assertEqual(len(SOURCE_KEYS), 11)
        self.assertTrue(all(key[field][i] == 0. for key in SOURCE_KEYS
                            for field in ("value", "in", "out") for i in (0, 2)))
        self.assertTrue(self.chain.rotation_curve_commutes(SOURCE_KEYS))

    def test_uniform_scale_does_not_restrict_rotation_curve(self):
        self.chain.S = (2., 2., 2.)
        self.assertTrue(self.chain.rotation_curve_commutes(curve(((0., 0., 0., 1.), (1., 0., 0., 0.)))))

    def test_signed_scale_is_not_replaced_by_absolute_scale(self):
        self.chain.S = (-1., 1., 1.)
        self.assertFalse(self.chain.commutes((0., 0., math.sin(math.pi/8), math.cos(math.pi/8))))
        self.assertTrue(self.chain.commutes((1., 0., 0., 0.)))

    def test_anisotropic_parent_with_correlated_xy_half_turn_is_commuting(self):
        self.chain.S = (2., 2., 3.)
        keys = curve(((1., 0., 0., 0.), (0., 1., 0., 0.)))
        self.assertTrue(self.chain.rotation_curve_commutes(keys))
        for time in (.1, .3, .7, .9):
            self.assertTrue(self.chain.commutes(rotation_at(keys, time)))

    def test_generated_curve_and_source_values_are_retained(self):
        keys_before, nodes_before = deepcopy(SOURCE_KEYS), deepcopy(SOURCE_NODES)
        clip = {"rotation": {"root/Trail/rot": SOURCE_KEYS}, "position": {}, "scale": {}, "euler": {}}
        result = N.node_chain(None, SOURCE_NODES, clip, "System.Age")
        self.assertFalse(getattr(result, "sheared", False))
        self.assertTrue(result.animated)
        self.assertTrue(any("System.Age" in expression for _, _, expression in result.temps))
        self.assertEqual(SOURCE_KEYS, keys_before)
        self.assertEqual(SOURCE_NODES, nodes_before)

    def test_source_hierarchy_matches_independent_full_affine_matrices(self):
        times = sorted({0., .55, .75, *(key["time"] for key in SOURCE_KEYS),
                        *((a["time"] + b["time"]) / 2 for a, b in zip(SOURCE_KEYS, SOURCE_KEYS[1:]))})
        for time in times:
            matrix, origin = ((1.,0.,0.), (0.,1.,0.), (0.,0.,1.)), (0.,0.,0.)
            chain = N.Chain()
            for node in SOURCE_NODES:
                q = tuple(node["rot"][axis] for axis in "xyzw")
                if node["name"] == "rot":
                    q = rotation_at(SOURCE_KEYS, time)
                scale = tuple(node["scale"][axis] for axis in "xyz")
                position = tuple(node["pos"][axis] for axis in "xyz")
                delta = matvec(matrix, position)
                origin = tuple(origin[i] + delta[i] for i in range(3))
                rotation = quaternion_matrix(q)
                matrix = matmul(matrix, tuple(tuple(rotation[i][j] * scale[j] for j in range(3)) for i in range(3)))
                chain.push(position, q, scale)
            self.assertFalse(getattr(chain, "sheared", False))
            rotation = quaternion_matrix(chain.Q)
            trs = tuple(tuple(rotation[i][j] * chain.S[j] for j in range(3)) for i in range(3))
            for point in ((0.,0.,0.), (1.,0.,0.), (0.,1.,0.), (0.,0.,1.), (-2.,1.5,.25)):
                expected, actual = matvec(matrix, point), matvec(trs, point)
                self.assertLess(max(abs(origin[i] + expected[i] - chain.P[i] - actual[i]) for i in range(3)), 1e-6)


class StaticScaleAxisTests(unittest.TestCase):
    def test_quarter_turn_then_child_preserves_independent_affine_geometry(self):
        nodes = [((.16, .68, 6.82), (0., 0., .01958293840289116, .9998082518577576), (1., 1., 1.)),
                 ((0., 0., 0.), (-.5, .5, -.5, .5), (1., 1.25, 2.200000047683716)),
                 ((-.87, -.065, 0.), (.7071068286895752, 0., 0., .7071067690849304), (.33, .33, .33)),
                 ((0., 0., -.23), (.7071068286895752, 0., 0., -.7071068286895752), (1.6442, 1.6442, .2993))]
        for signed in (False, True):
            chain = N.Chain()
            matrix = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.))
            origin = (0., 0., 0.)
            for index, (position, rotation, scale) in enumerate(nodes):
                if signed and index == 1:
                    scale = (-scale[0], scale[1], scale[2])
                offset = matvec(matrix, position)
                origin = tuple(a + b for a, b in zip(origin, offset))
                r = quaternion_matrix(rotation)
                matrix = matmul(matrix, tuple(tuple(r[i][j] * scale[j] for j in range(3)) for i in range(3)))
                chain.push(position, rotation, scale)
            self.assertFalse(getattr(chain, "sheared", False))
            r = quaternion_matrix(chain.Q)
            trs = tuple(tuple(r[i][j] * chain.S[j] for j in range(3)) for i in range(3))
            for point in ((0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (0., 0., 1.), (-2., 1.5, .25)):
                expected, actual = matvec(matrix, point), matvec(trs, point)
                self.assertLess(max(abs(origin[i] + expected[i] - chain.P[i] - actual[i]) for i in range(3)), 1e-6)

    def test_true_shear_still_rejects_descendant_trs(self):
        chain = N.Chain()
        chain.S = (1., 2., 3.)
        chain.push((0., 0., 0.), (0., 0., math.sin(math.pi / 8), math.cos(math.pi / 8)), (1., 1., 1.))
        self.assertTrue(chain.sheared)
        with self.assertRaises(N.AffineRequired):
            chain.push((1., 0., 0.), (0., 0., 0., 1.), (1., 1., 1.))


if __name__ == "__main__":
    unittest.main()
