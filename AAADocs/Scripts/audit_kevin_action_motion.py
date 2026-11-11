"""Read-only source audit for the explicitly selected Kevin montage XYZ actions.

The Wiring config owns the confirmed mesh basis. This audit emits a read-only
snapshot for the editor builder; it never edits sources, configs or UE assets.
"""
import argparse
import bisect
import hashlib
import json
import math
import re
from pathlib import Path

from fbx_bin_reader import FbxReader
from fbx_anim_extract import build_index, resolve_take_curvenodes, get_curve_arrays, FBXTIME
from import_bh3_kevin_demonbattle import SOURCE, properties

PROJECT = Path(__file__).resolve().parents[2]
MONTAGE_CONFIG = Path('AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Montage_Config.json')
BASIS_CONFIG = Path('AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Wiring_Config.json')
ANIMATION = '/Game/Characters/Boss/Kevin/DemonBattle/Animation/'
TIME_TOLERANCE = 1e-5


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def read_basis(wiring):
    basis = wiring.get('motion_asset_basis')
    require(isinstance(basis, dict) and basis.get('confirmed') is True,
            f'{BASIS_CONFIG}: motion_asset_basis is unconfirmed; provisional assembly cannot supply motion coordinates')
    q, s = basis.get('mesh_relative_rotation_xyzw'), basis.get('mesh_relative_scale')
    require(isinstance(q, list) and len(q) == 4 and all(finite_number(v) for v in q),
            f'{BASIS_CONFIG}: finite normalized xyzw quaternion required')
    require(abs(sum(v * v for v in q) - 1.) <= 1e-5,
            f'{BASIS_CONFIG}: mesh basis quaternion is not normalized')
    require(isinstance(s, list) and len(s) == 3 and all(finite_number(v) and v > 0 for v in s)
            and max(s) - min(s) <= 1e-5,
            f'{BASIS_CONFIG}: finite positive uniform mesh scale required; no approximate nonuniform conversion')
    # Values remain an exact snapshot. UE already imports cm; CMC applies scale once.
    return {'confirmed': True, 'mesh_relative_rotation_xyzw': q, 'mesh_relative_scale': s}


def selected_actions(config):
    names, catalog = config.get('selected_actions'), config.get('actions')
    require(config.get('schema_version') == 2 and isinstance(names, list) and names,
            f'{MONTAGE_CONFIG}: schema2 and explicit nonempty selected_actions required; no default batch')
    require(all(isinstance(n, str) and re.fullmatch(r'(?:BOSS|BOS)_411_Ani_[A-Za-z0-9_]+', n) for n in names)
            and len(names) == len(set(names)), f'{MONTAGE_CONFIG}: invalid/duplicate selected clip names')
    require(isinstance(catalog, list), f'{MONTAGE_CONFIG}: action catalog required')
    selected = []
    for name in names:
        matches = [a for a in catalog if isinstance(a, dict) and a.get('source_clip') == name]
        require(len(matches) == 1, f'{MONTAGE_CONFIG}: selected clip {name} is missing/ambiguous')
        action = matches[0]
        derived = action.get('sequence_override')
        require(action.get('source_sequence') == ANIMATION + 'AS_' + name,
                f'{name}: exact imported source_sequence required')
        require(action.get('require_sequence_override') is True
                and isinstance(derived, str) and re.fullmatch(re.escape(ANIMATION) + r'Derived/[A-Za-z0-9_]+', derived),
                f'{name}: explicit derived_sequence in the Kevin Derived directory required')
        require(action.get('motion_curve_reference') == 'original_ue_model_with_fbx_full_grid',
                f'{name}: explicit imported FBX/native Model reference required; JSON is not a motion substitute')
        require(isinstance(action.get('motion_bone'), str) and action['motion_bone'],
                f'{name}: motion_bone required')
        anchor = action.get('pose_anchor_sequence')
        require(isinstance(anchor, str) and anchor.startswith(ANIMATION + 'AS_') and '/' not in anchor[len(ANIMATION):],
                f'{name}: explicit original pose anchor required for the assembled batch')
        selected.append(action)
    require(len({a['sequence_override'] for a in selected}) == len(selected),
            f'{MONTAGE_CONFIG}: derived target collision')
    return selected


def validate_series(times, values, label, clip_start, clip_end):
    require(times and len(times) == len(values)
            and all(finite_number(v) for v in times + values), f'{label}: missing/nonfinite curve data')
    require(all(a < b for a, b in zip(times, times[1:])), f'{label}: unordered/duplicate timestamps')
    if len(times) == 1:
        require(abs(times[0] - clip_start) <= TIME_TOLERANCE,
                f'{label}: explicit constant channel must be anchored at the clip origin')
    else:
        require(times[0] <= clip_start + TIME_TOLERANCE and times[-1] >= clip_end - TIME_TOLERANCE,
                f'{label}: source support does not cover the complete effective clip domain')
    # Source support may extend beyond the effective clip. Every source key remains validated;
    # the output domain comes from the authored clip and is checked against the native UE model.


def clip_frame_grid(clip_start, clip_end, rate):
    require(finite_number(clip_start) and abs(clip_start) <= TIME_TOLERANCE
            and finite_number(clip_end) and clip_end > clip_start and finite_number(rate) and rate > 0,
            'clip domain: zero-origin, positive duration and finite sample rate required')
    frames = round(clip_end * rate)
    require(frames > 0 and abs(frames / rate - clip_end) <= TIME_TOLERANCE,
            'clip domain: effective end must lie on the declared frame grid')
    times = [i / rate for i in range(frames + 1)]
    times[-1] = clip_end
    return times


def take_domains(roots, name, clip_start, clip_end):
    takes = [take for node in roots if node.name == 'Takes' for take in node.children
             if take.name == 'Take' and take.props
             and (take.props[0].decode('utf-8') if isinstance(take.props[0], bytes) else take.props[0]) == name]
    require(len(takes) == 1, f'{name}: explicit matching FBX take domain required')
    domains = {}
    for key in ('LocalTime', 'ReferenceTime'):
        entries = [c for c in takes[0].children if c.name == key]
        require(len(entries) == 1 and len(entries[0].props) == 2
                and all(isinstance(v, int) and not isinstance(v, bool) for v in entries[0].props),
                f'{name}: missing/invalid FBX take {key}')
        start, end = [v / FBXTIME for v in entries[0].props]
        require(start < end and start <= clip_start + TIME_TOLERANCE and end >= clip_end - TIME_TOLERANCE,
                f'{name}: FBX take {key} does not cover the effective clip')
        domains[key] = [start, end]
    return domains


def support_domain(series):
    times, _ = series
    return {'keys': len(times), 'range_seconds': [times[0], times[-1]]}


def interpolate(times, values, t):
    if len(times) == 1:
        return values[0]
    require(times[0] - TIME_TOLERANCE <= t <= times[-1] + TIME_TOLERANCE,
            f'curve sample {t}: outside validated source domain')
    if abs(t - times[0]) <= TIME_TOLERANCE:
        return values[0]
    if abs(t - times[-1]) <= TIME_TOLERANCE:
        return values[-1]
    i = bisect.bisect_right(times, t)
    require(0 < i < len(times), f'curve sample {t}: no enclosing source interval')
    alpha = (t - times[i - 1]) / (times[i] - times[i - 1])
    return values[i - 1] + alpha * (values[i] - values[i - 1])


def quat_xyz(euler_degrees):
    x, y, z = [math.radians(v) / 2 for v in euler_degrees]
    cx, cy, cz = math.cos(x), math.cos(y), math.cos(z)
    sx, sy, sz = math.sin(x), math.sin(y), math.sin(z)
    return [sx * cy * cz - cx * sy * sz, cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz, cx * cy * cz + sx * sy * sz]


def angle(a, b):
    norm = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    require(math.isfinite(norm) and norm > 1e-8, 'source rotation: invalid zero/nonfinite quaternion')
    return math.degrees(2 * math.acos(min(1., abs(sum(x * y for x, y in zip(a, b)) / norm))))


def inspect(action):
    name, bone = action['source_clip'], action['motion_bone']
    fbx = SOURCE / 'anim' / (name + '.fbx')
    meta_path = fbx.with_suffix('.json')
    meta = json.loads(meta_path.read_text(encoding='utf-8-sig'))
    clip = meta['clip']
    require(clip['name'] == name and meta['avatar']['rootMotionBoneName'] == bone,
            f'{meta_path}: clip/root bone differs from selected action')
    require(meta.get('scaleFactorBakedIntoFbx') == 100.,
            f'{meta_path}: documented meter-to-centimeter bake required')
    rate = clip['sampleRate']
    start, duration = clip['muscleClip']['startTime'], action['expected_native_duration_seconds']
    require(action['native_duration_evidence'] == 'Saved/Codex/bh3_demonbattle_verification.json'
            and finite_number(start) and abs(start) <= TIME_TOLERANCE
            and finite_number(duration) and duration > 0 and finite_number(rate) and rate > 0,
            f'{name}: invalid/unhandled trimmed duration or sample rate')
    reader = FbxReader(str(fbx))
    try:
        roots = reader.parse()
        idx = build_index(roots)
        require(len(idx['stacks']) == 1, f'{fbx}: expected one explicit animation take')
        tracks = resolve_take_curvenodes(idx, next(iter(idx['stacks'])))
        domains = take_domains(roots, name, start, duration)
        global_nodes = [n for n in roots if n.name == 'GlobalSettings']
        require(len(global_nodes) == 1, f'{fbx}: missing/ambiguous GlobalSettings')
        globals_ = properties(global_nodes[0])
        require(globals_.get('UpAxis') == [1] and globals_.get('UpAxisSign') == [1]
                and globals_.get('UnitScaleFactor') == [1.], f'{fbx}: unsupported source axes or units: {globals_}')
        ids = [k for k, v in idx['model_id2name'].items() if v == bone]
        require(len(ids) == 1, f'{fbx}: missing/ambiguous motion bone {bone}')
        bone_props = properties(idx['id2node'][ids[0]])
        require(bone_props.get('RotationOrder', [0]) == [0], f'{fbx}: unsupported rotation order: {bone_props}')
        for prop in ('PreRotation', 'PostRotation', 'RotationPivot', 'RotationOffset', 'ScalingPivot', 'ScalingOffset'):
            require(all(abs(x) < 1e-5 for x in bone_props.get(prop, [0, 0, 0])),
                    f'{fbx}: unsupported {bone} {prop}: {bone_props}')
        channels = {}
        require(bone in tracks, f'{fbx}: motion-bone animation missing')
        for prop in ('Lcl Translation', 'Lcl Rotation'):
            require(prop in tracks[bone], f'{fbx}: {bone} {prop} missing')
            for axis in 'XYZ':
                require(axis in tracks[bone][prop], f'{fbx}: {bone} {prop}.{axis} missing')
                times, values = get_curve_arrays(reader.f, idx['curves'][tracks[bone][prop][axis]])
                series = ([t / FBXTIME for t in times], list(values))
                validate_series(*series, f'{fbx}:{bone}:{prop}.{axis}', start, duration)
                channels[prop, axis] = series
        json_curves, json_errors = {}, []
        for curve in clip['rootMotionCurves']:
            attribute = curve['attribute']
            require(attribute not in json_curves, f'{meta_path}: duplicate {attribute}')
            series = ([k['t'] for k in curve['keys']], [k['v'] for k in curve['keys']])
            json_curves[attribute] = series
            try:
                validate_series(*series, f'{meta_path}:{attribute}', start, duration)
            except ValueError as error:
                json_errors.append(str(error))
        required_json = ['RootT.' + a for a in 'xyz'] + ['RootQ.' + a for a in 'xyzw']
        for attribute in required_json:
            if attribute not in json_curves:
                json_errors.append(f'{meta_path}: missing {attribute}')
        support_times = channels['Lcl Translation', 'X'][0]
        require(len(support_times) >= 2
                and all(abs(t - (support_times[0] + i / rate)) <= TIME_TOLERANCE
                        for i, t in enumerate(support_times)),
                f'{fbx}: original support key grid differs from declared {rate} fps')
        # Sample the complete effective frame domain, including its native final interval.
        # Never slice the source arrays or infer the animation length from their extra support.
        times = clip_frame_grid(start, duration, rate)
        samples, max_pos, max_angle, comparisons = [], 0., 0., 0
        for t in times:
            pos = [interpolate(*channels['Lcl Translation', a], t) for a in 'XYZ']
            q = quat_xyz([interpolate(*channels['Lcl Rotation', a], t) for a in 'XYZ'])
            if not json_errors:
                rt = [interpolate(*json_curves['RootT.' + a], t) for a in 'xyz']
                rq = [interpolate(*json_curves['RootQ.' + a], t) for a in 'xyzw']
                expected_t = [-rt[0] * 100., rt[1] * 100., rt[2] * 100.]
                expected_q = [rq[0], -rq[1], -rq[2], rq[3]]
                max_pos = max(max_pos, math.dist(pos, expected_t))
                max_angle = max(max_angle, angle(q, expected_q))
                comparisons += 1
            samples.append({'time': t, 'fbx_translation_cm': pos, 'fbx_rotation_xyzw': q})
        json_agreement = not json_errors and comparisons > 0 and max_pos <= .25 and max_angle <= .25
        if comparisons and not json_agreement:
            json_errors.append(f'{name}: JSON/FBX mismatch {max_pos} cm / {max_angle} degrees')
        return {'source_clip': name, 'source_sequence': action['source_sequence'],
                'pose_anchor_sequence': action['pose_anchor_sequence'],
                'motion_curve_reference': action['motion_curve_reference'],
                'motion_usage': action['motion_usage'],
                'derived_sequence': action['sequence_override'], 'motion_bone': bone,
                'source_fbx': str(fbx), 'source_json': str(meta_path),
                'fbx_sha256': hashlib.sha256(fbx.read_bytes()).hexdigest(),
                'json_sha256': hashlib.sha256(meta_path.read_bytes()).hexdigest(),
                'fbx_settings': globals_, 'duration': duration, 'sample_rate': rate,
                'clip_range_seconds': [start, duration], 'fbx_take_domains_seconds': domains,
                'json_muscle_range_seconds': [clip['muscleClip']['startTime'], clip['muscleClip']['stopTime']],
                'native_duration_evidence': action['native_duration_evidence'],
                'source_support_domains': {
                    'fbx': {prop + '.' + axis: support_domain(series)
                            for (prop, axis), series in channels.items()},
                    'json': {attribute: support_domain(series) for attribute, series in json_curves.items()}},
                'json_agreement': json_agreement, 'json_discrepancies': json_errors,
                'json_comparison_samples': comparisons,
                'json_to_fbx_translation_error_cm': max_pos if comparisons else None,
                'json_to_fbx_rotation_error_deg': max_angle if comparisons else None,
                'samples': samples}
    finally:
        reader.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PROJECT / 'Saved/Codex/kevin_motion_source_xyz.json',
                        help='New source-audit JSON; an existing evidence file is never overwritten')
    args = parser.parse_args()
    config = json.loads((PROJECT / MONTAGE_CONFIG).read_text(encoding='utf-8-sig'))
    wiring = json.loads((PROJECT / BASIS_CONFIG).read_text(encoding='utf-8-sig'))
    actions, basis = selected_actions(config), read_basis(wiring)
    clips, errors = [], []
    for action in actions:
        try:
            clips.append(inspect(action))
        except (ValueError, KeyError) as error:
            errors.append({'source_clip': action['source_clip'], 'error': str(error)})
    result = {'schema': 2, 'montage_config': MONTAGE_CONFIG.as_posix(), 'basis_config': BASIS_CONFIG.as_posix(),
              'motion_asset_basis': basis, 'clips': clips, 'success': not errors, 'errors': errors,
              'reference_mode': 'original_ue_model_with_fbx_full_grid',
              'import_basis_reference_clip': config['import_basis_reference_clip'],
              'json_consistency_complete': not errors and all(c['json_agreement'] for c in clips),
              'native_model_verified': False}
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'output': str(out), 'success': result['success'],
          'json_consistency_complete': result['json_consistency_complete'], 'native_model_verified': False,
          'errors': errors, 'clips': [{k: v for k, v in c.items() if k in
          ('source_clip', 'duration', 'json_to_fbx_translation_error_cm', 'json_to_fbx_rotation_error_deg')}
          for c in result['clips']]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
