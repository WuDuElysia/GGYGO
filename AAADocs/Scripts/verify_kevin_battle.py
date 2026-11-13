"""@file verify_kevin_battle.py
@brief 从单份连续交战日志核追击、切阶段、空连落地、普攻死亡和清理；画面须另行查看。
"""
import json
import math
import re
import sys
from pathlib import Path

folder = Path(sys.argv[1])
log = (folder/'editor.log').read_text(encoding='utf-8', errors='replace')
events = []
for line in log.splitlines():
    match = re.search(r'KEVIN_BATTLE_(\w+) (\{.*\})', line)
    if match:
        events.append((match[1], json.loads(match[2])))


def rows(kind):
    return [value for name, value in events if name == kind]


def require(value, message):
    if not value:
        raise RuntimeError(message)


require('KEVIN_BATTLE_FAILURE' not in log, '脚本运行错误')
require(len(rows('READY')) == 1 and len(rows('FINISH')) == 1, '不是一份连续试次')
require(rows('FINISH')[0]['reason'] == 'boss_removed', '没有完成 Boss 生产死亡')
ready = rows('READY')[0]
require(ready['health'] == 1200 and ready['player_health'] == 100, '原生产初始数值不符')
intervention = rows('INTERVENTIONS')[0]
require(all(intervention[k] is False for k in ('direct_boss_activation','health_writes','actor_position_writes','bt_stopped')),
        '存在超出玩家输入和诊断相机的干预')
dash = rows('DASH_END')[:2]
require(len(dash) == 2, '缺两次追击')
for d in dash:
    require(abs(math.hypot(*d['displacement'][:2])-711.144) < 1, '追击未覆盖完整原轨迹')
    require(d['boss_health_delta'] == d['player_health_delta'] == 0, '追击期间发生伤害')
    require(math.sqrt(sum(v*v for v in d['player_displacement'])) < .001, '前两段追击时玩家未保持静止')
health = rows('HEALTH')
require(health and health[-1]['new'] == 0, '没有生产伤害降到零血')
require(all(x['new'] < x['old'] and x['instigator'] and 'GGYGOCharacterSlot' in x['instigator'] for x in health),
        '伤害链不全来自玩家 Slot')
require(any(x['old'] > 600 and x['new'] <= 600 for x in health), '没有 50% 阈值穿越')
phase = rows('PHASE')
require(len(phase) == 1 and 'Kevin.Two' in phase[0]['phase'] and phase[0]['health'] <= 600, '切阶段事实不符')
samples = rows('SAMPLE')
require(samples[-1]['player_health'] > 0, '玩家未存活')
air = [x for x in rows('LANDED') if any('AirChain' in a for a in x.get('active_abilities', []))]
require({a for x in air for a in x['active_abilities'] if 'AirChain' in a} == {'BP_GA_Kevin_AirChain01_KVB_C','BP_GA_Kevin_AirChain02_KVB_C'}, '缺一条空连的当栈落地事实')
require(air and all(not x['character'] and 'StaticMeshActor_0' in x['actor'] for x in air), '空连缺当栈 GA／环境落地')
require(not any(x['character'] for x in rows('LANDED')), '仍有角色 Landed')
require(rows('PLAYER_QUIET') and not rows('PLAYER_QUIET')[-1]['active'] and not rows('PLAYER_QUIET')[-1]['action_motion'], '玩家自身能力未完成收尾')
require('LogGGYGOAbilitySystem: Error:' not in log, '仍有 AbilitySystem 运行错误')
require(rows('DEATH_FINISHED') and rows('CLEANUP_WAIT')[-1]['game_seconds'] >= 5, '缺死亡完成或五秒游戏时间清理')
cleanup = rows('CLEANUP')[-1]
require(cleanup['death_finished'] and not cleanup['boss_avatar'] and not cleanup['resources'], '死亡资源清理不完整')
images = rows('IMAGE')
require(images and all(x['saved'] and x['readback'] and 'COMPLETE' in x['status'] for x in images), '截图读回失败')
result = dict(passed=True, first_two_dash_cm=[math.hypot(*x['displacement'][:2]) for x in dash],
    phase_change=phase[0], air_landings=[dict(game_time=x['game_time'], abilities=x['active_abilities'], actor=x['actor']) for x in air],
    boss_health=health[-1]['new'], player_health=samples[-1]['player_health'],
    cleanup_game_seconds=rows('CLEANUP_WAIT')[-1]['game_seconds'], images=len(images),
    observed=rows('FINISH')[0]['observed'], input_policy_changes=rows('INPUT_POLICY'), visual_review='required')
(folder/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
