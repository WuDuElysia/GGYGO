"""Read-only JSON/FBX audit for the two initial ground-action motion assets.

Produces Saved/Codex/kevin_motion_source.json for the UE editor builder.
No animation assets or exported source files are modified.
"""
import bisect
import hashlib
import json
import math
from pathlib import Path

from fbx_bin_reader import FbxReader
from fbx_anim_extract import build_index, resolve_take_curvenodes, get_curve_arrays, FBXTIME
from import_bh3_kevin_demonbattle import SOURCE, properties

PROJECT = Path(__file__).resolve().parents[2]


def interpolate(times, values, t):
    i = bisect.bisect_right(times, t)
    if i == 0:
        return values[0]
    if i == len(times):
        return values[-1]
    alpha = (t - times[i - 1]) / (times[i] - times[i - 1])
    return values[i - 1] + alpha * (values[i] - values[i - 1])


def quat_xyz(euler_degrees):
    x, y, z = [math.radians(v) / 2 for v in euler_degrees]
    cx, cy, cz = math.cos(x), math.cos(y), math.cos(z)
    sx, sy, sz = math.sin(x), math.sin(y), math.sin(z)
    return [sx * cy * cz - cx * sy * sz, cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz, cx * cy * cz + sx * sy * sz]


def angle(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return math.degrees(2 * math.acos(min(1., abs(dot / norm))))


def inspect(suffix):
    name = 'BOSS_411_Ani_Ice_Attack_' + suffix
    fbx = SOURCE / 'anim' / (name + '.fbx')
    meta_path = fbx.with_suffix('.json')
    meta = json.loads(meta_path.read_text(encoding='utf-8-sig'))
    reader = FbxReader(str(fbx))
    try:
        roots = reader.parse()
        idx = build_index(roots)
        tracks = resolve_take_curvenodes(idx, next(iter(idx['stacks'])))
        globals_ = properties(next(n for n in roots if n.name == 'GlobalSettings'))
        assert globals_['UpAxis'] == [1], globals_
        assert globals_['UnitScaleFactor'] == [1.], globals_
        bone_id = next(k for k, v in idx['model_id2name'].items() if v == 'Bip001')
        bone_props = properties(idx['id2node'][bone_id])
        assert bone_props.get('RotationOrder', [0]) == [0], bone_props
        for prop in ('PreRotation', 'PostRotation', 'RotationPivot', 'RotationOffset', 'ScalingPivot', 'ScalingOffset'):
            assert all(abs(x) < 1e-5 for x in bone_props.get(prop, [0, 0, 0])), (prop, bone_props)
        channels = {}
        for prop in ('Lcl Translation', 'Lcl Rotation'):
            for axis in 'XYZ':
                times, values = get_curve_arrays(reader.f, idx['curves'][tracks['Bip001'][prop][axis]])
                channels[prop, axis] = ([t / FBXTIME for t in times], values)
        json_curves = {c['attribute']: ([k['t'] for k in c['keys']], [k['v'] for k in c['keys']])
                       for c in meta['clip']['rootMotionCurves']}
        samples, max_pos, max_angle = [], 0., 0.
        # Use the original FBX key grid; JSON timestamps carry float rounding.
        for t in channels['Lcl Translation', 'X'][0]:
            pos = [interpolate(*channels['Lcl Translation', a], t) for a in 'XYZ']
            q = quat_xyz([interpolate(*channels['Lcl Rotation', a], t) for a in 'XYZ'])
            rt = [interpolate(*json_curves['RootT.' + a], t) for a in 'xyz']
            rq = [interpolate(*json_curves['RootQ.' + a], t) for a in 'xyzw']
            # Exporter's Unity -> FBX reflection of X, and the documented baked x100 unit scale.
            expected_t = [-rt[0] * 100., rt[1] * 100., rt[2] * 100.]
            expected_q = [rq[0], -rq[1], -rq[2], rq[3]]
            max_pos = max(max_pos, math.dist(pos, expected_t))
            max_angle = max(max_angle, angle(q, expected_q))
            samples.append({'time': t, 'fbx_translation_cm': pos, 'fbx_rotation_xyzw': q})
        # The independently baked JSON/FBX tracks can differ slightly between their sample grids.
        assert max_pos < .25 and max_angle < .25, (name, 'JSON/FBX mismatch cm/degrees', max_pos, max_angle)
        assert abs(samples[0]['time']) < 1e-6
        return {'suffix': suffix, 'source_sequence': '/Game/Characters/Boss/Kevin/DemonBattle/Animation/AS_' + name,
                'source_fbx': str(fbx), 'source_json': str(meta_path),
                'fbx_sha256': hashlib.sha256(fbx.read_bytes()).hexdigest(),
                'json_sha256': hashlib.sha256(meta_path.read_bytes()).hexdigest(),
                'fbx_settings': globals_, 'duration': samples[-1]['time'],
                'json_to_fbx_translation_error_cm': max_pos, 'json_to_fbx_rotation_error_deg': max_angle,
                'json_start_translation_m': [json_curves['RootT.' + a][1][0] for a in 'xyz'],
                'samples': samples}
    finally:
        reader.close()


if __name__ == '__main__':
    result = {'schema': 1, 'clips': [inspect(s) for s in ('01', '02')]}
    out = PROJECT / 'Saved/Codex/kevin_motion_source.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(out), 'clips': [{k: v for k, v in c.items() if k in
          ('suffix', 'duration', 'json_to_fbx_translation_error_cm', 'json_to_fbx_rotation_error_deg')}
          for c in result['clips']]}, ensure_ascii=False))
