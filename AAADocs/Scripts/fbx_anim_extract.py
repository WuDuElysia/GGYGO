"""
从二进制 FBX 中按 take 抽取指定节点的旋转/位移轨道并做运动学分析。

依赖同目录 fbx_bin_reader.py 的最小解析器。

核心用途：
  1. 判断某个动画 take（如 TurnBack）的"转身"烤在哪个节点上
     （Root / Bone_Root / Loc_Character / Bip001 / Bip001 Pelvis 的 Lcl Rotation Z 轴）。
  2. 汇总所有 take 的时长、根节点位移与偏航（yaw）变化，用于批量解读。

FBX 时间单位：1 秒 = 46186158000 units（FBXTIME）。

用法:
  python fbx_anim_extract.py <fbx> take <take名子串>       # 详查单个 take 的关键节点轨道
  python fbx_anim_extract.py <fbx> catalog [过滤子串]        # 批量汇总所有(或过滤)take
"""

import sys
from collections import defaultdict
from fbx_bin_reader import FbxReader, decode_placeholder

FBXTIME = 46186158000.0

# 关注的节点（承载角色整体运动与朝向的候选）
ROOT_NODES = ['Root', 'Bone_Root', 'Loc_Character', 'Bip001', 'Bip001 Pelvis']


def obj_id(node):
    for p in node.props:
        if isinstance(p, int):
            return p
    return None


def obj_name(node):
    for p in node.props:
        if isinstance(p, bytes):
            return p.split(b'\x00')[0].decode('utf-8', 'replace')
    return ''


def build_index(roots):
    top = {n.name: n for n in roots}
    objs = top.get('Objects')
    conns = top.get('Connections')

    id2node = {}
    id2type = {}
    model_id2name = {}
    curve_nodes = {}   # id -> node
    curves = {}        # id -> node
    stacks = {}        # id -> name
    layers = {}        # id -> name

    for c in objs.children:
        oid = obj_id(c)
        if oid is None:
            continue
        id2node[oid] = c
        id2type[oid] = c.name
        if c.name == 'Model':
            model_id2name[oid] = obj_name(c)
        elif c.name == 'AnimationCurveNode':
            curve_nodes[oid] = c
        elif c.name == 'AnimationCurve':
            curves[oid] = c
        elif c.name == 'AnimationStack':
            stacks[oid] = obj_name(c)
        elif c.name == 'AnimationLayer':
            layers[oid] = obj_name(c)

    # 连接：C 节点 props = [type(S), src(L), dst(L), (prop(S))]
    child_conns = defaultdict(list)   # parent_id -> [(child_id, prop)]
    parent_conns = defaultdict(list)  # child_id -> [(parent_id, prop)]
    for c in conns.children if conns else []:
        if c.name != 'C':
            continue
        ctype = c.props[0].decode() if isinstance(c.props[0], bytes) else ''
        src = c.props[1]
        dst = c.props[2]
        prop = None
        if len(c.props) > 3 and isinstance(c.props[3], bytes):
            prop = c.props[3].decode('utf-8', 'replace')
        child_conns[dst].append((src, prop))
        parent_conns[src].append((dst, prop))

    return {
        'id2type': id2type, 'model_id2name': model_id2name,
        'curve_nodes': curve_nodes, 'curves': curves,
        'stacks': stacks, 'layers': layers,
        'child_conns': child_conns, 'parent_conns': parent_conns,
        'id2node': id2node,
    }


def get_curve_arrays(f, curve_node):
    """从 AnimationCurve 对象里取 (KeyTime[int64], KeyValueFloat[float])。"""
    times, values = None, None
    for c in curve_node.children:
        if c.name == 'KeyTime' and c.props:
            ph = c.props[0]
            times = decode_placeholder(f, ph) if isinstance(ph, tuple) else ph
        elif c.name == 'KeyValueFloat' and c.props:
            ph = c.props[0]
            values = decode_placeholder(f, ph) if isinstance(ph, tuple) else ph
    return times or [], values or []


def resolve_take_curvenodes(idx, stack_id):
    """返回 take 下 {model_name: {prop: {chan: curve_id}}}。"""
    child_conns = idx['child_conns']
    id2type = idx['id2type']
    model_id2name = idx['model_id2name']

    # stack -> layers
    layer_ids = [cid for cid, _ in child_conns.get(stack_id, [])
                 if id2type.get(cid) == 'AnimationLayer']
    result = defaultdict(lambda: defaultdict(dict))
    for lid in layer_ids:
        for cnid, _ in child_conns.get(lid, []):
            if id2type.get(cnid) != 'AnimationCurveNode':
                continue
            # curvenode -> model (parent OP with prop = "Lcl Rotation"/...)
            model_name = None
            model_prop = None
            for pid, prop in idx['parent_conns'].get(cnid, []):
                if pid in model_id2name:
                    model_name = model_id2name[pid]
                    model_prop = prop
                    break
            if model_name is None:
                continue
            # curves -> curvenode (child OP with prop "d|X"/"d|Y"/"d|Z")
            for curid, cprop in child_conns.get(cnid, []):
                if id2type.get(curid) == 'AnimationCurve':
                    chan = (cprop or '').replace('d|', '')
                    result[model_name][model_prop][chan] = curid
    return result


def summarize(vals):
    if not vals:
        return None
    return {
        'first': vals[0], 'last': vals[-1],
        'min': min(vals), 'max': max(vals),
        'delta': vals[-1] - vals[0], 'n': len(vals),
    }


def take_detail(path, sub):
    r = FbxReader(path)
    roots = r.parse()
    idx = build_index(roots)
    matches = [(sid, nm) for sid, nm in idx['stacks'].items() if sub.lower() in nm.lower()]
    if not matches:
        print(f'没有匹配 "{sub}" 的 take')
        r.close()
        return
    for sid, nm in matches:
        print(f'\n================ TAKE: {nm} ================')
        cn = resolve_take_curvenodes(idx, sid)

        # 时长：扫描该 take 全部曲线的时间范围
        tmin, tmax = None, None
        for model_name, props in cn.items():
            for prop, chans in props.items():
                for chan, curid in chans.items():
                    times, _ = get_curve_arrays(r.f, idx['curves'][curid])
                    if times:
                        lo, hi = times[0] / FBXTIME, times[-1] / FBXTIME
                        tmin = lo if tmin is None else min(tmin, lo)
                        tmax = hi if tmax is None else max(tmax, hi)
        if tmin is not None:
            print(f'时长: {tmax - tmin:.3f}s  (帧数约 {round((tmax-tmin)*30)} @30fps)')

        for model_name in ROOT_NODES:
            if model_name not in cn:
                continue
            print(f'\n  [节点] {model_name}')
            for prop in ('Lcl Translation', 'Lcl Rotation'):
                chans = cn[model_name].get(prop)
                if not chans:
                    continue
                print(f'    {prop}:')
                for chan in ('X', 'Y', 'Z'):
                    curid = chans.get(chan)
                    if curid is None:
                        continue
                    _, vals = get_curve_arrays(r.f, idx['curves'][curid])
                    s = summarize(vals)
                    if s:
                        print(f'      {chan}: first={s["first"]:.2f} last={s["last"]:.2f} '
                              f'min={s["min"]:.2f} max={s["max"]:.2f} delta={s["delta"]:.2f} keys={s["n"]}')
    r.close()


def _node_delta(r, idx, cn, node_name, prop, chan):
    d = cn.get(node_name, {}).get(prop, {})
    curid = d.get(chan)
    if curid is None:
        return None
    _, v = get_curve_arrays(r.f, idx['curves'][curid])
    if not v:
        return None
    return v[-1] - v[0]


def catalog(path, filt=None):
    r = FbxReader(path)
    roots = r.parse()
    idx = build_index(roots)
    rows = []
    for sid, nm in idx['stacks'].items():
        if filt and filt.lower() not in nm.lower():
            continue
        cn = resolve_take_curvenodes(idx, sid)
        tmin, tmax = None, None
        for model_name, props in cn.items():
            for prop, chans in props.items():
                for chan, curid in chans.items():
                    times, _ = get_curve_arrays(r.f, idx['curves'][curid])
                    if times:
                        lo, hi = times[0] / FBXTIME, times[-1] / FBXTIME
                        tmin = lo if tmin is None else min(tmin, lo)
                        tmax = hi if tmax is None else max(tmax, hi)
        dur = (tmax - tmin) if tmin is not None else 0.0
        # Root 节点：gameplay root motion（位移 + yaw）
        r_rx = _node_delta(r, idx, cn, 'Root', 'Lcl Rotation', 'X')
        r_ry = _node_delta(r, idx, cn, 'Root', 'Lcl Rotation', 'Y')
        r_rz = _node_delta(r, idx, cn, 'Root', 'Lcl Rotation', 'Z')
        r_tx = _node_delta(r, idx, cn, 'Root', 'Lcl Translation', 'X')
        r_ty = _node_delta(r, idx, cn, 'Root', 'Lcl Translation', 'Y')
        r_tz = _node_delta(r, idx, cn, 'Root', 'Lcl Translation', 'Z')
        # Loc_Character 节点：部分演出/入场位移
        l_tx = _node_delta(r, idx, cn, 'Loc_Character', 'Lcl Translation', 'X')
        l_ty = _node_delta(r, idx, cn, 'Loc_Character', 'Lcl Translation', 'Y')
        rows.append((nm, dur, r_rx, r_ry, r_rz, r_tx, r_ty, r_tz, l_tx, l_ty))

    rows.sort(key=lambda x: x[0])

    def fmt(v):
        return ('%.1f' % v) if v is not None else '-'

    print(f'{"take":66s} {"dur":>6s} '
          f'{"RootrX":>8s} {"RootrY":>8s} {"RootrZ":>8s} '
          f'{"RoottX":>8s} {"RoottY":>8s} {"RoottZ":>8s} '
          f'{"LoctX":>8s} {"LoctY":>8s}')
    for nm, dur, rx, ry, rz, tx, ty, tz, ltx, lty in rows:
        print(f'{nm[:66]:66s} {dur:6.2f} '
              f'{fmt(rx):>8s} {fmt(ry):>8s} {fmt(rz):>8s} '
              f'{fmt(tx):>8s} {fmt(ty):>8s} {fmt(tz):>8s} '
              f'{fmt(ltx):>8s} {fmt(lty):>8s}')
    r.close()


def trace(path, sub, node='Root', samples=16):
    """打印某 take 指定节点 Lcl Rotation Y / Lcl Translation Z 的时间采样，观察运动形状。"""
    r = FbxReader(path)
    roots = r.parse()
    idx = build_index(roots)
    matches = [(sid, nm) for sid, nm in idx['stacks'].items() if sub.lower() in nm.lower()]
    for sid, nm in matches:
        cn = resolve_take_curvenodes(idx, sid)
        if node not in cn:
            continue
        print(f'\n=== TRACE {nm} / {node} ===')
        rotY = cn[node].get('Lcl Rotation', {}).get('Y')
        trZ = cn[node].get('Lcl Translation', {}).get('Z')
        ry_t, ry_v = get_curve_arrays(r.f, idx['curves'][rotY]) if rotY else ([], [])
        tz_t, tz_v = get_curve_arrays(r.f, idx['curves'][trZ]) if trZ else ([], [])
        n = max(len(ry_v), len(tz_v))
        if n == 0:
            continue
        print(f'{"t(norm)":>8s} {"rotY":>9s} {"transZ":>9s}')
        for i in range(0, n, max(1, n // samples)):
            t = i / (n - 1) if n > 1 else 0
            ry = ry_v[i] if i < len(ry_v) else float('nan')
            tz = tz_v[i] if i < len(tz_v) else float('nan')
            print(f'{t:8.2f} {ry:9.2f} {tz:9.2f}')
    r.close()


if __name__ == '__main__':
    path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'take'
    arg = sys.argv[3] if len(sys.argv) > 3 else ''
    if mode == 'take':
        take_detail(path, arg)
    elif mode == 'catalog':
        catalog(path, arg or None)
    elif mode == 'trace':
        trace(path, arg, sys.argv[4] if len(sys.argv) > 4 else 'Root')
