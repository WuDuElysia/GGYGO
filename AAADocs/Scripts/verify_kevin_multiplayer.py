"""@file verify_kevin_multiplayer.py
@brief 检查 P3 双端原始观察；图像通过读回后仍须人工查看，不签视觉或独立进程验收。
"""
import argparse
import json
import math
from pathlib import Path
from minimal_multiplayer_checks import require, fx_reached


def verify(folder):
    data = json.loads((folder / 'observations.json').read_text(encoding='utf-8'))
    require(data['error'] is None, '运行错误：' + str(data['error']))
    require(data['completed'] == ['Ice03', 'Fire02', 'AirChain01'], '三招未完整执行')
    rows = data['records']
    require(bool(rows), '没有真实观察')
    paired = next(e for e in data['events'] if e['event'] == 'paired')
    require(paired['channels']['server']['pawn_net_guid'] == paired['channels']['client']['pawn_net_guid'], 'Boss NetGUID 不匹配')
    for row in rows:
        for side, role in (('server', 'AUTHORITY'), ('client', 'SIMULATED_PROXY')):
            ep = row['endpoints'][side]
            require(role in ep['role'], 'Boss 角色权限不符')
            require(ep['channel']['connection_open'] and ep['channel'].get('channel_id'), '原 ActorChannel 断开')
            require(ep['base'] not in [p['pawn'] for p in ep['players'].values() if p['pawn']], '角色成为 Boss 基底')
        require(not row['endpoints']['client']['active'], '客户端执行了服务器专属 Boss 能力')
    actions = {}
    for action in data['completed']:
        samples = [r for r in rows if r['action'] == action]
        visible = [r for r in samples if action in (r['endpoints']['client']['montage'] or '')]
        require(len(visible) >= 2, action+' 没有客户端 Montage 进度')
        positions = {r['endpoints']['client']['position'] for r in visible}
        require(len(positions) >= 2, action+' 客户端 Montage 未推进')
        poses = {json.dumps(r['endpoints']['client']['bone_pose'], sort_keys=True) for r in visible}
        require(len(poses) >= 2, action+' 客户端骨骼未变化')
        actions[action] = dict(client_montage_samples=len(visible), distinct_poses=len(poses))
    first, last = rows[0]['endpoints'], rows[-1]['endpoints']
    damage = {}
    for player_id, before in first['server']['players'].items():
        after = last['server']['players'][player_id]['health']
        remote = last['client']['players'][player_id]['health']
        require(after == remote, '最终客户端血量未收敛：'+player_id)
        if before['health'] is not None and after < before['health']:
            damage[player_id] = dict(before=before['health'], server_after=after, client_after=remote)
    require(bool(damage), '没有服务器命中伤害与客户端属性复制证据')
    distance = math.dist(last['server']['location'], last['client']['location'])
    require(distance < 1, '静止后两端胶囊未收敛')
    require(all('WALKING' in ep['movement'] for ep in last.values()), '最终未 Walking')
    air_end = next(e['game_time'] for e in data['events'] if e['event'] == 'action_complete' and e['action'] == 'AirChain01')
    stable = [r for r in rows if r['game_time'] >= air_end+2]
    require(stable and stable[-1]['game_time']-stable[0]['game_time'] >= 2
            and all('WALKING' in e['movement'] and e['base'] for r in stable for e in r['endpoints'].values()),
            '落地后没有两秒游戏时间的双端稳定站立')
    require(not any(r['character'] for r in data['landed']), '发生角色 Landed')
    require(any(r['action'] == 'AirChain01' and not r['character'] for r in data['landed']), '空连缺环境落地')
    contacts = [r for r in data['contacts'] if r['action'] == 'AirChain01' and 'FALLING' in r['movement']]
    require(bool(contacts), '空连缺真实下落角色接触')
    require(data['close_setup'] is not None, '缺明确的贴身测试摆位记录')
    require(all(not v for e in data['events'] if e['event'] == 'skill_cleanup' for v in e['resources'].values()), '技能资源未清')
    cleanup = next(e for e in data['events'] if e['event'] == 'encounter_cleanup')
    require(not any(cleanup['bosses'].values()), 'Encounter 销毁未复制')
    fx = data['fx']['client']
    require(not fx['evidence_incomplete'], 'FX 观察溢出')
    reached = [r for r in fx['records'] if fx_reached(r)]
    require(bool(reached), '客户端 FX 没有实际 Niagara 模拟到达证据')
    created = {r['component_id'] for r in fx['records'] if r['kind'] == 'RemoteCreated'}
    destroyed = {r['component_id'] for r in fx['records'] if r['kind'] == 'ComponentDestroyed'}
    require(created and created <= destroyed, '客户端创建的 FX 组件没有逐项销毁事实')
    for action in data['completed']:
        begin = next(e['elapsed'] for e in data['events'] if e['event'] == 'request' and e['action'] == action)
        end = next(e['elapsed'] for e in data['events'] if e['event'] == 'action_complete' and e['action'] == action)
        require(any(begin <= r['drain_host_elapsed_seconds'] <= end for r in reached), action+' 缺 FX 到达证据')
    hit_assets = {v['asset'] for r in rows for v in r['resources']['client']
                  if isinstance(v, dict) and 'HitImpact' in v['asset']}
    require(bool(hit_assets), '缺客户端命中 Cue 实际 FX 组件')
    require(data['images'] and all(i['file_write_complete'] and i['file_readback_verified'] and i['net_mode'] == 3
                                 for i in data['images']), '客户端图像读回不完整')
    log = (folder / 'editor.log').read_text(encoding='utf-8', errors='replace')
    require('IpConnection' in log and '127.0.0.1:' in log and 'Join succeeded' in log, '缺原生 IP 连接握手')
    production = sorted({a for r in rows if r['phase'] == 'production' for a in r['endpoints']['server']['active']})
    require(bool(production), '没有正式 BT 动作观察')
    return dict(passed=True, topology=data['topology'], production_bt_actions=production, actions=actions, damage=damage,
                stable_walking_game_seconds=stable[-1]['game_time']-stable[0]['game_time'],
                final_capsule_distance_cm=distance, client_fx_reached=len(reached), client_fx_destroyed=len(created),
                client_hit_assets=sorted(hit_assets), falling_character_contacts=len(contacts), client_images=len(data['images']),
                visual_review='required', independent_processes='uncovered')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    result = verify(args.folder)
    (args.folder / 'checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
