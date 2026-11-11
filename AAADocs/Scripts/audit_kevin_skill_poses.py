"""只读分析 Kevin 的原 FBX：原始轨迹、骨骼姿态和端点连续性，不创建 UE 资产。

图仅为源骨骼 FK 示意，不含蒙皮、碰撞或原游戏事件。窗口由作者看图后配置，
不把速度峰、命名或相邻姿态自动转换成技能／伤害窗口。
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from fbx_bin_reader import FbxReader
from fbx_anim_extract import build_index, resolve_take_curvenodes, get_curve_arrays, FBXTIME
from import_bh3_kevin_demonbattle import properties

PROJECT = Path(__file__).resolve().parents[2]
MANIFEST = PROJECT / 'AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Action_Manifest.json'
JOINTS = ('Bip001', 'Bip001 Pelvis', 'Bip001 Spine', 'Bip001 Spine1', 'Bip001 Spine2',
          'Bip001 Neck', 'Bip001 Head', 'Bip001 L Clavicle', 'Bip001 L UpperArm',
          'Bip001 L Forearm', 'Bip001 L Hand', 'Bip001 R Clavicle', 'Bip001 R UpperArm',
          'Bip001 R Forearm', 'Bip001 R Hand', 'Bip001 L Thigh', 'Bip001 L Calf',
          'Bip001 L Foot', 'Bip001 R Thigh', 'Bip001 R Calf', 'Bip001 R Foot',
          'Bip001 Prop1', 'LeftHandThrowPoint', 'AP_Hand_UC_R', 'AP_Hand_Center_R')


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rotation(v):
    x, y, z = np.radians(v)
    cx, cy, cz = np.cos([x, y, z])
    sx, sy, sz = np.sin([x, y, z])
    return np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]) @ np.array(
        [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array(
        [[1, 0, 0], [0, cx, -sx], [0, sx, cx]])


def sampled(channels, default, time):
    return np.array([float(np.interp(time, *channels[a])) if a in channels else default[n]
                     for n, a in enumerate('XYZ')])


def inspect(source, entry, native_durations):
    fbx = source / entry['source_fbx']
    meta_path = source / entry['source_json']
    meta = json.loads(meta_path.read_text(encoding='utf-8-sig'))
    result = dict(name=entry['name'], source_empty=entry['source_empty'],
                  source_fbx_sha256=sha(fbx), source_json_sha256=sha(meta_path))
    if entry['source_empty']:
        result['reason'] = '原索引为空轨道；不生成动画或技能'
        return result, None
    reader = FbxReader(str(fbx))
    try:
        roots = reader.parse()
        index = build_index(roots)
        require(len(index['stacks']) == 1, f'{fbx}: 必须是唯一原始 Take')
        tracks = resolve_take_curvenodes(index, next(iter(index['stacks'])))
        ids = index['model_id2name']
        require(len(set(ids.values())) == len(ids), f'{fbx}: 同名 Model 无法唯一求 FK')
        by_name = {v: k for k, v in ids.items()}
        require('Bip001' in by_name, f'{fbx}: 缺 Bip001')
        defaults, curves, parents = {}, {}, {}
        support_start, support_end = entry['fbx_key_range_seconds']
        native_key = entry['sequence'] + '.' + entry['sequence'].rsplit('/', 1)[1]
        require(native_key in native_durations, f'{fbx}: 缺已有原生有效片段域，不以支持键末端代替')
        start, end = 0., native_durations[native_key]
        require(math.isfinite(start) and math.isfinite(end) and end >= start, f'{fbx}: 非法 Take 范围')
        for mid, name in ids.items():
            prop = properties(index['id2node'][mid])
            require(prop.get('RotationOrder', [0]) == [0], f'{fbx}: {name} 非 XYZ 旋转序')
            for field in ('PreRotation', 'PostRotation', 'RotationPivot', 'RotationOffset',
                          'ScalingPivot', 'ScalingOffset'):
                require(all(abs(x) < 1e-5 for x in prop.get(field, [0, 0, 0])),
                        f'{fbx}: {name} 非零 {field}；此简图不支持，拒绝猜测')
            defaults[mid] = prop
            ps = [pid for pid, unused in index['parent_conns'].get(mid, []) if pid in ids]
            require(len(ps) <= 1, f'{fbx}: {name} 多父节点')
            parents[mid] = ps[0] if ps else None
            curves[mid] = {}
            for field, axes in tracks.get(name, {}).items():
                curves[mid][field] = {}
                for axis, cid in axes.items():
                    ts, vs = get_curve_arrays(reader.f, index['curves'][cid])
                    require(ts and len(ts) == len(vs), f'{fbx}: {name}.{field}.{axis} 缺曲线')
                    curves[mid][field][axis] = ([t / FBXTIME for t in ts], vs)

        def pose(time):
            cache = {}

            def world(mid):
                if mid in cache:
                    return cache[mid]
                prop, channels = defaults[mid], curves[mid]
                t = sampled(channels.get('Lcl Translation', {}), prop.get('Lcl Translation', [0, 0, 0]), time)
                r = sampled(channels.get('Lcl Rotation', {}), prop.get('Lcl Rotation', [0, 0, 0]), time)
                s = sampled(channels.get('Lcl Scaling', {}), prop.get('Lcl Scaling', [1, 1, 1]), time)
                local = np.eye(4)
                local[:3, :3] = rotation(r) @ np.diag(s)
                local[:3, 3] = t
                parent = parents[mid]
                cache[mid] = world(parent) @ local if parent is not None else local
                return cache[mid]

            return {name: world(by_name[name])[:3, 3].tolist() for name in JOINTS if name in by_name}

        # 保留原生采样域，不从极短片段扩造动作；零时长 Take 只读一个姿态。
        rate = float(entry['sample_rate'])
        require(rate > 0 and math.isfinite(rate), f'{fbx}: 非法采样率')
        count = max(1, int(round((end - start) * rate)) + 1)
        times = np.linspace(start, end, count)
        root_id = by_name['Bip001']
        root_curve = curves[root_id].get('Lcl Translation', {})
        root_default = defaults[root_id].get('Lcl Translation', [0, 0, 0])
        path = np.array([sampled(root_curve, root_default, t) for t in times])
        displacement = path[-1] - path[0]
        path_length = float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum())
        selected = sorted(set(int(round(v)) for v in np.linspace(0, count - 1, min(count, 8))))
        poses = [pose(float(times[i])) for i in selected]
        joints = sorted(poses[0])
        centered = [{n: (np.array(p[n]) - np.array(p['Bip001'])).tolist() for n in joints} for p in (poses[0], poses[-1])]
        body = [n for n in joints if 'Prop' not in n and 'Point' not in n and not n.startswith('AP_')]
        endpoint_rms = float(np.sqrt(np.mean([np.linalg.norm(np.array(centered[0][n]) - centered[1][n]) ** 2 for n in body])))
        edge_names = {}
        for name in joints:
            parent = parents[by_name[name]]
            while parent is not None and ids[parent] not in joints:
                parent = parents[parent]
            if parent is not None:
                edge_names[name] = ids[parent]
        result.update(duration_seconds=end - start, sample_rate=rate, source_loop=entry['source_loop_time'],
                      fbx_support_range_seconds=[support_start, support_end],
                      duration_origin='prior_native_readback; current_UE_readback_pending',
                      sample_count=count, source_root_displacement_cm=displacement.tolist(),
                      source_root_range_cm=(path.max(axis=0) - path.min(axis=0)).tolist(),
                      source_root_path_cm=path_length, body_endpoint_rms_cm=endpoint_rms,
                      pose_times_seconds=[float(times[i]) for i in selected],
                      endpoint_body_relative=centered, available_points=joints)
        return result, dict(poses=poses, edges=edge_names, times=result['pose_times_seconds'])
    finally:
        reader.f.close()


def page(rows, filename):
    width, cell, row_h, label = 1520, 170, 192, 145
    image = Image.new('RGB', (width, 42 + row_h * len(rows)), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 12)
    draw.text((8, 5), 'Kevin SOURCE FK / front X-Y and side Z-Y; red=Prop1. NO SKIN / NO HIT TIMING.', fill='black', font=font)
    draw.text((8, 21), 'Each row uses one fixed scale; Bip001 centered for limb visibility. Root trajectory is in JSON.', fill='black', font=font)
    for row, (facts, data) in enumerate(rows):
        top = 42 + row * row_h
        short = facts['name'].replace('BOSS_411_Ani_', '').replace('BOS_411_Ani_', '')
        for n in range(0, len(short), 19):
            draw.text((4, top + n // 19 * 15), short[n:n+19], fill='black', font=font)
        draw.text((4, top + 65), f"{facts['duration_seconds']:.3f}s", fill='black', font=font)
        visible = [{n: (np.array(p) - np.array(pose['Bip001'])).tolist()
                    for n, p in pose.items()} for pose in data['poses']]
        all_points = np.array([p for pose in visible for p in pose.values()])
        lo, hi = all_points.min(axis=0), all_points.max(axis=0)
        span = max(float(max(hi - lo)), 180.)
        scale = min((cell - 12) / span, 77 / max(float(hi[1] - lo[1]), 100.))
        center = (lo + hi) / 2
        for col, (pose, time) in enumerate(zip(visible, data['times'])):
            left = label + col * cell
            draw.text((left + 4, top + 4), f'{time:.3f}s', fill='black', font=font)
            for view, axis in enumerate((0, 2)):
                def xy(name):
                    p = pose[name]
                    return (left + cell / 2 + (p[axis] - center[axis]) * scale,
                            top + 61 + view * 88 - (p[1] - center[1]) * scale)
                for child, parent in data['edges'].items():
                    draw.line([xy(parent), xy(child)], fill='#d43224' if child == 'Bip001 Prop1' else '#184d83', width=2)
                draw.ellipse([xy('Bip001')[0]-2, xy('Bip001')[1]-2, xy('Bip001')[0]+2, xy('Bip001')[1]+2], fill='black')
        draw.line((0, top + row_h - 1, width, top + row_h - 1), fill='#cccccc')
    image.save(filename, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    require(not out.exists(), f'保留旧证据，输出目录已存在：{out}')
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    source = Path(manifest['source'])
    native_path = PROJECT / 'Saved/Codex/bh3_demonbattle_verification.json'
    native = json.loads(native_path.read_text(encoding='utf-8-sig'))
    native_durations = {c['asset']: c['duration'] for c in native['clips']}
    out.mkdir(parents=True)
    facts, rows, pages = [], [], []
    for entry in manifest['actions']:
        fact, data = inspect(source, entry, native_durations)
        if data is not None:
            fact['pose_page'] = f'poses_{len(rows) // 6 + 1:02d}.png'
            rows.append((fact, data))
        facts.append(fact)
        if len(facts) % 10 == 0:
            print('source clips:', len(facts), flush=True)
    for first in range(0, len(rows), 6):
        name = f'poses_{first // 6 + 1:02d}.png'
        page(rows[first:first+6], out / name)
        pages.append(name)
    report = dict(schema='GGYGO.KevinSourcePoseCatalog/v1', source=str(source), clips=facts,
                  native_duration_readback=str(native_path), native_duration_readback_sha256=sha(native_path),
                  manifest_before_sha256=sha(MANIFEST), pose_pages=pages,
                  scope='源 FBX 骨骼 FK 与原始轨迹；无 UE/蒙皮/碰撞/原游戏事件/运行验收')
    (out / 'source_pose_catalog.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(clips=len(facts), valid=len(rows), bytes=sum(p.stat().st_size for p in out.iterdir())), ensure_ascii=False))


if __name__ == '__main__':
    main()
