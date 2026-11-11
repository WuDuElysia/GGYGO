"""@file minimal_multiplayer_checks.py
@brief 最小联机的值证据断言；不连接 UE，不启动进程，不签发视觉验收。

保留既有纠正重放、原资源退役、初始取消和 FX 复制断言。
观察来源缺失时返回 missing 或抛出错误，不从相邻帧补出接收点事实。
"""
import copy
import json
import math
import re
from pathlib import Path

# EGGYGOActionCurveSourceMode::OriginalMontage；与 CompletedInterval 的 SourceKind 枚举不同。
ORIGINAL_MONTAGE_SOURCE_MODE = 1
def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def native_success(value, operation):
    # 已核 UE bool + 单 FString out：true 是 str（包括空串），false 是 None。
    require(type(value) is str, operation + ' 未返回真实成功单 Out: ' + repr(value))


def merge_observation_page(previous, page):
    """追加同一原窗的余下全部记录；拒绝缺页、重复页及换源。"""
    records = previous["records"] if previous else []
    require(page.get("read_success") and page["records_start_index"] == len(records)
            and page["record_count"] == len(records) + len(page["records"]), "观察分页不连续或不完整")
    if previous and previous.get("original_source"):
        require(page.get("original_source") == previous["original_source"], "原观察分页换源")
    records.extend(page["records"])
    page["records"] = records
    return page


def player_id(state):
    """已核实的 BlueprintGetter 反射属性；没有独立 get_player_id Python 方法。"""
    require(state is not None, '缺原 PlayerState')
    value = state.get_editor_property('player_id')
    require(type(value) is int, '原 PlayerId 属性不是 int32')
    return value


def facing_native_snapshot(record, expected):
    """读取原 Finalize 当栈的纯值诊断；保 Unavailable/NoActionSource，不造默认源。"""
    value = record['movement_action_native']
    require(isinstance(value, dict) and type(value['status']) is int and value['status'] in (0, 1, 2)
            and type(value['available']) is bool and type(value['diagnostic']) is str,
            '原 RMS 诊断 schema 不符')
    require(value['available'] is (value['status'] != 0), '原 RMS available/status 不一致')
    if not value['available']:
        require(not any(k in value for k in ('frame', 'world', 'character', 'movement', 'active_sources', 'pending_sources')),
                'Unavailable 不能带默认有效帧/源')
        return copy.deepcopy(value)
    frame = value['frame']
    require(type(frame) is str and frame.isascii() and frame.isdigit() and len(frame) <= 20
            and (frame == '0' or not frame.startswith('0')) and int(frame) <= 0xFFFFFFFFFFFFFFFF,
            '原 RMS 本机 frame 不是精确 uint64 字符串')
    require(type(value['local_role']) is int and all(value[k] == v for k, v in expected.items()),
            '原 RMS 不是本次观察 World/Character/CMC/Role')
    number = lambda x: type(x) in (int, float) and math.isfinite(x)
    require(number(value['world_time_seconds']), '原 RMS 世界时间不是有限数值')
    for container in ('active_sources', 'pending_sources'):
        require(isinstance(value[container], list), '原 RMS active/pending 未分列')
        if value['status'] == 2:
            require(not value[container], 'NoActionSource 不能含实际源')
        for source in value[container]:
            require(isinstance(source, dict)
                    and all(type(source[k]) is str for k in ('script_struct', 'instance_name'))
                    and all(type(source[k]) is int for k in ('source_mode', 'local_id'))
                    and all(type(source[k]) is bool for k in ('native_imported', 'finished', 'marked_for_removal',
                        'explicitly_cancelled', 'has_entry_actor_rotation', 'has_original_montage_binding'))
                    and all(number(source[k]) for k in ('montage_start_seconds', 'native_time_seconds',
                        'duration_seconds', 'play_rate')), '原 RMS 源字段不完整或非有限')
            if source['has_entry_actor_rotation']:
                rotation = source['entry_actor_rotation']
                require(isinstance(rotation, list) and len(rotation) == 4 and all(number(x) for x in rotation)
                        and sum(x*x for x in rotation) > 0.0, '原 RMS raw Entry quaternion 无效')
            else:
                require('entry_actor_rotation' not in source, '缺原 Entry 时不能填 identity quaternion')
            if not source['has_original_montage_binding']:
                require(not any(k in source for k in ('montage', 'sections', 'segments')), '缺 binding 时不能造默认 Montage')
                continue
            require(all(type(source[k]) is str for k in ('montage', 'slot', 'binding_initial_section_name'))
                    and all(type(source[k]) is int for k in ('track_index', 'binding_initial_section_index'))
                    and all(number(source[k]) for k in ('binding_start_seconds', 'binding_end_seconds')),
                    '原 RMS Montage binding 字段不符')
            require(isinstance(source['sections'], list) and isinstance(source['segments'], list), '原 binding 范围未分列')
            for section in source['sections']:
                require(type(section['name']) is str and type(section['index']) is int
                        and all(number(section[k]) for k in ('start_seconds', 'end_seconds')), '原 binding section 无效')
            for segment in source['segments']:
                require(type(segment['sequence']) is str and type(segment['index']) is int
                        and all(number(segment[k]) for k in ('montage_start_seconds', 'montage_end_seconds',
                            'sequence_start_seconds', 'sequence_end_seconds', 'source_seconds_per_montage_second')),
                        '原 binding segment 无效')
    return copy.deepcopy(value)


def ability_system_live(record, expected):
    """只消费该原 Mesh 的公开 ASC/KnownTasks 快照；Unavailable 不发布零计数。"""
    value = record['ability_system_live']
    require(isinstance(value, dict) and type(value['available']) is bool
            and type(value['diagnostic']) is str and type(value['local_role']) is int
            and type(value['locally_controlled']) is bool, 'ASC live schema 不完整')
    frame = value['live_frame']
    require(type(frame) is str and frame.isascii() and frame.isdigit() and len(frame) <= 20
            and (frame == '0' or not frame.startswith('0')) and int(frame) <= 0xFFFFFFFFFFFFFFFF,
            'ASC live_frame 不是原精确 uint64')
    require(value['pawn'] == expected['pawn'] and value['world'] == expected['world']
            and value['local_role'] == expected['local_role'], 'ASC live 不是原观察 Pawn/World/Role')
    if not value['available']:
        require(not any(k in value for k in ('specs', 'known_tasks', 'known_task_count', 'tag_counts',
                    'unread_known_task_count', 'unread_ability_instance_count')), 'Unavailable 不得带零任务或默认数组')
        return copy.deepcopy(value)
    require(value['ability_system'] == expected['ability_system']
            and value['avatar_actor'] == expected['pawn'] and value['ability_system_world'] == expected['world'],
            'ASC live 原接口/Avatar/World 不符')
    require(all(type(value[k]) is int and value[k] >= 0 for k in (
        'known_task_count', 'unread_known_task_count', 'unread_ability_instance_count'))
        and isinstance(value['specs'], list) and isinstance(value['known_tasks'], list)
        and value['known_task_count'] == len(value['known_tasks']) and isinstance(value['tag_counts'], dict),
        'ASC live 公开清单／不可读计数不符')
    require(all(type(k) is str and type(v) is int and v >= 0 for k, v in value['tag_counts'].items()),
            'ASC live 实际标签计数不符')
    specs, tasks = set(), set()
    for spec in value['specs']:
        require(type(spec['spec_handle']) is str and spec['spec_handle'] not in specs
                and type(spec['ability']) is str and type(spec['active']) is bool
                and isinstance(spec['instances'], list), '原 Spec 重复或字段不完整')
        specs.add(spec['spec_handle'])
        for instance in spec['instances']:
            require(instance['spec_handle'] == spec['spec_handle'] and type(instance['instance']) is str
                    and type(instance['instance_class']) is str and type(instance['instance_object_id']) is int
                    and type(instance['active']) is bool, '原 Spec 实例字段不符')
    for task in value['known_tasks']:
        key = task['task'], task['task_object_id']
        require(type(key[0]) is str and type(key[1]) is int and key not in tasks
                and type(task['task_class']) is str and type(task['state']) is int and task['state'] in range(5)
                and type(task['finished']) is bool and type(task['has_task_owner']) is bool
                and isinstance(task['owner_matches'], list), '原 KnownTask 去重／状态不完整')
        tasks.add(key)
        require(all(any(match == instance for spec in value['specs'] for instance in spec['instances'])
                    for match in task['owner_matches']), 'KnownTask 归属不是同次实际 Spec-instance 视图')
    return copy.deepcopy(value)


def combo_task_evidence(records, arm):
    """从布防起逐帧核原 ASC 的公开任务；只声明 KnownTasks，不代签私有 ActiveTasks。"""
    require(len(records) > arm['record_index'], '布防后的原 Pose 记录丢失')
    seen, last, last_spec = {}, None, None
    for index in range(arm['record_index'], len(records)):
        live = ability_system_live(records[index], arm['expected'])
        require(index != arm['record_index'] or live['live_frame'] == arm['live_frame'], '原布防记录位置/帧已改变')
        require(last is None or int(live['live_frame']) >= int(last['live_frame']), '原 ASC live_frame 倒退')
        require(live['available'] and live['diagnostic'] == ''
                and live['unread_known_task_count'] == 0 and live['unread_ability_instance_count'] == 0,
                '布防后的原 ASC/任务不可读，不能当作零资源')
        require(all(live[k] == arm[k] for k in ('pawn_object_id', 'ability_system_object_id', 'owner_actor')),
                '原 ASC/Pawn/Owner 在布防后已换代')
        specs = [s for s in live['specs'] if s['spec_handle'] == arm['spec_handle']]
        require(len(specs) == 1 and specs[0]['ability'] == arm['ability_cdo'], '布防的原生产 Spec 已退役或被替换')
        spec = specs[0]
        for task in live['known_tasks']:
            matches = [i for i in task['owner_matches'] if i['spec_handle'] == arm['spec_handle']]
            if task['task_class'] != arm['task_class'] or not matches:
                continue
            require(task['has_task_owner'] and len(matches) == 1
                    and matches[0]['instance_class'] == arm['ability_class'], '原 WaitComboInput 的真实 Owner 不唯一')
            if task['state'] in (2, 3) and not task['finished']:
                require(spec['active'] and matches[0]['active'], '活动 WaitComboInput 没有原活动 Spec/instance')
                key = task['task'], task['task_object_id']
                original = seen.setdefault(key, dict(record_index=index, live_frame=live['live_frame'],
                    ability_system=live['ability_system'], spec_handle=spec['spec_handle'],
                    instance=copy.deepcopy(matches[0]), task=copy.deepcopy(task)))
                require(original['instance']['instance'] == matches[0]['instance']
                        and original['instance']['instance_object_id'] == matches[0]['instance_object_id'],
                        '原任务的实际实例身份已改变')
        last, last_spec = live, spec
    keys = {(t['task'], t['task_object_id']) for t in last['known_tasks']}
    selected = [t for t in last['known_tasks'] if any(i['spec_handle'] == arm['spec_handle'] for i in t['owner_matches'])]
    attacking = last['tag_counts'].get('State.Attacking', 0)  # available 全量拥有标签中缺席，才表示实际未拥有。
    cleaned = (not last_spec['active'] and not any(i['active'] for i in last_spec['instances'])
               and not selected and not keys.intersection(seen) and attacking == 0)
    return dict(scope='Authority ASC public KnownTasks; private Ability.ActiveTasks not observed',
        arm=copy.deepcopy(arm), seen=list(seen.values()), last_record_index=len(records)-1,
        last_live=last, last_spec=last_spec, cleanup_verified=cleaned)


def initial_native_records(records, expected, start=None):
    """RMS 仅在真实可读起点后认证；之后的 Unavailable 不会被跳过。"""
    values = [facing_native_snapshot(row, expected) for row in records]
    if start is None:
        start = next((i for i, value in enumerate(values) if value['status'] != 0), None)
    require(start is None or type(start) is int and 0 <= start < len(values), '原 RMS 布防位置丢失')
    selected = values[start:] if start is not None else []
    return dict(expected=expected, start_record_index=start, record_count=len(values),
        no_action_source=bool(selected) and all(v['status'] == 2 for v in selected),
        last=values[-1] if values else None)


def initial_route_evidence(log, tasks, sources, owner_closed):
    """成功 Initial 的独立前置，保持完整方向/Rebase 验收的原谓词。"""
    rows = log['rows']
    missing = []
    pair = {}
    for side, boundary in (('owner', 'SendAttempt'), ('authority', 'RPCImplementation')):
        source = sources.get((side, 0))
        if source is None:
            missing.append(side + '.InitialSource')
            continue
        found = [r for r in rows if r['kind'] == 'AbilitySystem.OwnedStepInput'
            and all(r['fields'].get(k) == v for k, v in dict(Boundary=boundary, ASC=source['asc'],
                World=source['world'], Spec=source['ability_spec_handle'], Kind='0', SourceStep='-1').items())]
        if len(found) != 1:
            missing.append(side + '.ActualInitial')
        else:
            pair[side] = found[0]
    if len(pair) == 2:
        left, right = (pair[s]['fields'] for s in ('owner', 'authority'))
        require(all(left[k] == right[k] for k in ('Spec', 'ActivationKey', 'Request', 'Edge', 'Entry')),
                '成功 Initial Send/RPC 不属于同一实际请求')
    unavailable = [r for r in rows if (r['kind'] == 'AbilitySystem.OwnedStepInput'
        and r['fields'].get('Boundary') in ('InitialUnavailableSend', 'InitialUnavailableRPC', 'InitialSourceRejected'))
        or r['kind'] == 'Combat.PlayerCombo.InitialUnavailable']
    source = sources.get(('authority', 0))
    seen = [t for t in tasks['seen'] if source is not None
        and t['instance']['instance'] == source['ability'] and t['spec_handle'] == source['ability_spec_handle']
        and t['ability_system'] == source['asc']]
    if not seen:
        missing.append('OriginalWaitComboInputActiveOrPausedNotObserved')
    if not tasks['cleanup_verified']:
        missing.append('AuthorityKnownTasksOrGAOrAttackingNotRetired')
    if not owner_closed:
        missing.append('OwnerPublicCleanupNotObserved')
    if unavailable:
        missing.append('UnexpectedInitialUnavailable')
    if log['errors']:
        missing.append('UnexpectedUEError')
    return dict(verified=not missing, missing=missing, initial=pair, unavailable=unavailable,
                errors=copy.deepcopy(log['errors']), known_tasks=tasks)


def facing_rotation_equal(left, right):
    """比较原 quaternion 的等价朝向；保留两侧原值，不以归一化结果替换证据。"""
    return min(max(abs(a-b) for a, b in zip(left, right)),
               max(abs(a+b) for a, b in zip(left, right))) <= 0.000001


def facing_log_rows(path, offset, end=None):
    """读取原进程此次入场后的完整日志行；原字段及行文一并保留。"""
    with path.open('rb') as stream:
        size = stream.seek(0, 2)
        require(size >= offset and (end is None or offset <= end <= size), '原宿主日志被截断或区间错误')
        stream.seek(offset)
        raw = stream.read() if end is None else stream.read(end-offset)
    raw = raw[:raw.rfind(b'\n')+1]  # 先截完整字节行，避免读到异步 writer 的半个 UTF-8 字符。
    tags = ('Input.MovementEvaluation', 'Movement.ActionStartInput', 'Movement.ActionStartBasis',
            'Combat.PlayerCombo.StepFacing', 'Combat.PlayerCombo.EntryRequest',
            'Combat.PlayerCombo.CorrectionSend', 'Combat.PlayerCombo.CorrectionReceive',
            'AbilitySystem.OwnedStepInput', 'Combat.PlayerCombo.InitialUnavailable')
    rows, errors = [], []
    number = r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?'
    quaternion = re.compile(r'(Entry|Basis|RebasedEntry)=(X=(' + number + ') Y=(' + number
                            + ') Z=(' + number + ') W=(' + number + '))')
    for line in raw.decode('utf-8-sig').splitlines(keepends=True):
        if not line.endswith('\n'):
            continue  # 异步 writer 的未完行留给下次原回调，不发布半行。
        error = re.search(r':\s*(?:Error|Fatal):\s*', line)
        if error is not None:
            errors.append(dict(raw=line.rstrip('\r\n'), message=line[error.end():].rstrip('\r\n')))
        tag = next((name for name in tags if '[' + name + '] ' in line), None)
        if tag is None:
            continue
        body = line.split('[' + tag + '] ', 1)[1].rstrip('\r\n')
        quats = {}
        for match in quaternion.finditer(body):
            quats[match[1]] = [float(match[i]) for i in (3, 4, 5, 6)]
        body = quaternion.sub(lambda match: match[1] + '=Quaternion', body)
        fields = {}
        for match in re.finditer(r"([A-Za-z][A-Za-z0-9]*)=('[^']*'|.*?)(?= [A-Za-z][A-Za-z0-9]*=|$)", body):
            key, value = match.groups()
            require(key not in fields, '原日志字段重复: ' + tag + '.' + key)
            fields[key] = value[1:-1] if value.startswith("'") and value.endswith("'") else value
        fields.update(quats)
        rows.append(dict(kind=tag, fields=fields, raw=line.rstrip('\r\n')))
    return dict(log=str(path), offset=offset, read_end=offset+len(raw),
                rows=rows, errors=errors)


def facing_replay_sources(rows, resources):
    """按 Authority 真正接受的 Origin 选 owner 原窗；保留被拒预测窗与 Mode2 原窗。"""
    selected = {}
    for step in (0, 1):
        candidates = [source for (side, index, _serial), source in resources.items()
                      if side == 'authority' and index == step and source is not None]
        require(len(candidates) <= 1, 'reject_replay 的 Authority 同段出现未准资源替换')
        if not candidates:
            continue
        authority = candidates[0]
        accepted = [r for r in rows if r['kind'] == 'Combat.PlayerCombo.StepFacing'
            and all(r['fields'].get(k) == v for k, v in dict(Ability=authority['ability'], World=authority['world'],
                Step=str(step), StepToken=str(authority['step_token']), Mode='1',
                Handle=str(authority['cmc_motion_handle']), Instance=str(authority['montage_instance_id'])).items())]
        require(len(accepted) <= 1, '同原 Authority 资源有多个接受起段')
        if not accepted:
            continue
        origin = accepted[0]['fields']['StepOrigin']
        owners = []
        for (side, index, _serial), source in resources.items():
            if side != 'owner' or index != step or source is None:
                continue
            starts = [r for r in rows if r['kind'] == 'Combat.PlayerCombo.StepFacing'
                and all(r['fields'].get(k) == v for k, v in dict(Ability=source['ability'], World=source['world'],
                    Step=str(step), StepOrigin=origin, StepToken=str(source['step_token']), Mode='1',
                    Handle=str(source['cmc_motion_handle']), Instance=str(source['montage_instance_id'])).items())]
            require(len(starts) <= 1, '同原 owner 资源有多个输入起段')
            if starts:
                require(source['ability_spec_handle'] == authority['ability_spec_handle'], '两端接受 Origin 的 Spec 不同')
                owners.append(source)
        require(len(owners) <= 1, '接受 Origin 无法唯一关联 owner 原资源')
        if owners:
            selected['authority', step] = authority
            selected['owner', step] = owners[0]
    return selected


def facing_input_evidence(rows, sources, driver, owner_endpoint):
    """以同原资源日志关联输入／评价／接受 basis；不比较跨端 local_id 或 Finalize 帧。"""
    missing, steps = [], {}
    for step in (0, 1):
        pair = {}
        for side in ('owner', 'authority'):
            source = sources.get((side, step))
            if source is None:
                missing.append(side + '.OriginalStep' + str(step))
                continue
            facing = [r for r in rows if r['kind'] == 'Combat.PlayerCombo.StepFacing'
                and r['fields'].get('Ability') == source['ability'] and r['fields'].get('World') == source['world']
                and r['fields'].get('Step') == str(step) and r['fields'].get('StepToken') == str(source['step_token'])
                and r['fields'].get('Handle') == str(source['cmc_motion_handle'])
                and r['fields'].get('Instance') == str(source['montage_instance_id'])
                and r['fields'].get('Mode') == '1' and isinstance(r['fields'].get('Entry'), list)]
            if len(facing) != 1:
                missing.append(side + '.AcceptedQualifiedBasis' + str(step))
                continue
            entry = facing[0]['fields']
            basis = [r for r in rows if r['kind'] == 'Movement.ActionStartBasis'
                and all(r['fields'].get(k) == v for k, v in dict(CMC=source['cmc'], Montage=source['montage'],
                    Handle=str(source['cmc_motion_handle']), Instance=str(source['montage_instance_id']),
                    Request=entry['StepOrigin']).items())]
            if len(basis) != 1:
                missing.append(side + '.OriginalCMCBasis' + str(step))
                continue
            accepted = basis[0]['fields']
            require(isinstance(accepted.get('Entry'), list)
                    and facing_rotation_equal(accepted['Entry'], entry['Entry']), 'GA 与原 CMC 接受 basis 不符')
            inputs = [r for r in rows if r['kind'] == 'Movement.ActionStartInput'
                and all(r['fields'].get(k) == v for k, v in dict(CMC=source['cmc'], World=source['world'],
                    Pawn=source['pawn'], Remote='0' if side == 'owner' else '1', Request=entry['StepOrigin'],
                    Kind=str(step), SourceStep=str(step-1), Session=accepted['Session'], EdgeEvaluation=accepted['EdgeEvaluation'],
                    StepEvaluation=accepted['StepEvaluation']).items())]
            if len(inputs) != 1:
                missing.append(side + '.OriginalInputFact' + str(step))
                continue
            fact = inputs[0]['fields']
            axis_x, axis_y, yaw = (float(fact[k]) for k in ('AxisX', 'AxisY', 'ControlYaw'))
            require(all(math.isfinite(v) for v in (axis_x, axis_y, yaw)) and fact['InputState'] == '1'
                    and abs(axis_x) < 0.000001 and (axis_y > 0 if step == 0 else axis_y < 0),
                    '原段首没有实际 Held 的前／反向 ActionValue')
            x, y, z, w = entry['Entry']
            require(abs(x*x+y*y+z*z+w*w-1.0) < 0.00001, '原接受 quaternion 非单位值')
            actual_yaw = math.degrees(math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z)))
            expected_yaw = yaw + math.degrees(math.atan2(axis_x, axis_y))
            require(abs((actual_yaw-expected_yaw+180.0) % 360.0-180.0) < 0.001,
                    '原接受 basis 不符合该次 ActionValue/ControlYaw')
            pair[side] = dict(source=copy.deepcopy(source), step_facing=facing[0], basis=basis[0], input=inputs[0])
        if set(pair) != {'owner', 'authority'}:
            continue
        owner, authority = (pair[side]['input']['fields'] for side in ('owner', 'authority'))
        require(all(owner[k] == authority[k] for k in ('Session', 'EdgeEvaluation', 'StepEvaluation', 'InputState'))
                and all(float(owner[k]) == float(authority[k]) for k in ('AxisX', 'AxisY', 'ControlYaw')),
                'Authority 裁决没有沿原 owner 提交的同一输入事实')
        evaluations = {}
        for name, serial in (('edge', owner['EdgeEvaluation']), ('step', owner['StepEvaluation'])):
            matches = [r for r in rows if r['kind'] == 'Input.MovementEvaluation'
                and all(r['fields'].get(k) == v for k, v in dict(Phase='Completed', World=owner_endpoint['world'],
                    PC=owner_endpoint['pc'], Pawn=owner_endpoint['pawn'], PlayerInput=owner_endpoint['player_input'],
                    SessionSerial=owner['Session'], EvaluationSerial=serial).items())]
            if len(matches) != 1:
                missing.append('owner.' + name + 'Evaluation' + str(step))
                continue
            evaluation = matches[0]['fields']
            require(evaluation['EntryFrame'] == evaluation['CompletedFrame']
                    and int(evaluation['CompletedFrame']) >= 0, '原完整评价的入口／完成帧不符')
            evaluations[name] = matches[0]
        if set(evaluations) == {'edge', 'step'}:
            evaluated = evaluations['step']['fields']
            for evaluation in evaluations.values():
                fields = evaluation['fields']
                value = re.fullmatch(r'\(X=([^,]+),Y=([^\)]+)\)', fields['ActionValue'])
                require(fields['ValueState'] == 'Readable' and value is not None
                        and all(math.isfinite(float(v)) for v in value.groups())
                        and float(value[1]) == float(owner['AxisX']) and float(value[2]) == float(owner['AxisY']),
                        '原 edge／段首完整评价未发布可读且相同的真实 ActionValue')
            continuation = 'second_press_frame'
            if step == 1 and driver.get('variant') == 'reject_replay':
                fields = [name for name in ('second_press_frame', 'third_press_frame') if driver.get(name) is not None]
                completed = int(evaluations['edge']['fields']['CompletedFrame'])
                candidates = [name for index, name in enumerate(fields) if int(driver[name]) <= completed
                    and (index+1 == len(fields) or completed < int(driver[fields[index+1]]))]
                require(len(candidates) == 1, '接受段的真实 edge 求值无法唯一关联原第二/第三 Press')
                continuation = candidates[0]
            press = driver['first_press_frame' if step == 0 else continuation]
            require(press is not None and int(evaluations['edge']['fields']['CompletedFrame']) >= int(press)
                    and int(evaluated['CompletedFrame']) >= int(press), '原 edge／段首评价早于本次实际按键')
        steps[str(step)] = dict(endpoints=pair, evaluations=evaluations)
    if set(steps) == {'0', '1'}:
        first, second = (steps[str(i)]['endpoints']['owner']['input']['fields'] for i in (0, 1))
        require(first['Session'] == second['Session']
                and int(second['EdgeEvaluation']) > int(first['EdgeEvaluation'])
                and all(int(row['StepEvaluation']) >= int(row['EdgeEvaluation']) for row in (first, second)),
                '两次 Press 未保留同原输入会话的独立 edge／段首评价')
        actions = {evaluation['fields']['Action'] for item in steps.values() for evaluation in item['evaluations'].values()}
        require(len(actions) <= 1 and all(path not in ('', 'None') for path in actions),
                '原输入会话的实际 Action 来源发生变化')
    return dict(steps=steps, missing=missing)


def facing_replay_driver_evidence(result, case):
    """三次原 Press 各保留自己的提交帧，最终样本不转签给被拒的预测段。"""
    driver, events = result['direction_driver'], result['input_events']
    require(case == 'ComboStepFacingHeld' and driver['variant'] == 'reject_replay'
            and driver['attack_attempts'] in (2, 3) and driver['frame_domain'] == 'OwnerInputSubmissionGFrameCounter'
            and driver['sample_frame_domain'] == 'ReadTimeGFrameCounter_NotInputEvaluation', '拒绝重放输入分支/帧域不符')
    replayed = driver['attack_attempts'] == 3
    expected = [('W', 'Press'), ('Attack', 'Press'), ('Attack', 'Release'), ('S', 'Press'), ('W', 'Release'),
                ('Attack', 'Press'), ('Attack', 'Release')]
    if replayed:
        expected += [('Attack', 'Press'), ('Attack', 'Release')]
    expected += [('S', 'Release')]
    require([(e['action'], e['edge']) for e in events] == expected
            and all(e['status'] == 'submitted' for e in events), '拒绝重放只允许原三次 Attack 与原方向边沿')
    frames = [int(e['owner_submission_frame']) for e in events]
    require(all(a <= b for a, b in zip(frames, frames[1:])), '拒绝重放输入提交帧倒退')
    fields = ('forward_frame', 'first_press_frame', 'first_release_frame', 'reverse_frame', 'reverse_frame',
              'second_press_frame', 'second_release_frame')
    if replayed:
        fields += ('third_press_frame', 'third_release_frame')
    require(all(driver[name] is not None and int(driver[name]) == frame for name, frame in zip(fields, frames)),
            '原三次 Attack 帧与输入回执不符')
    require(frames[1] < frames[5] and (not replayed or frames[5] < frames[7] and frames[6] < frames[7]),
            '原独立 Press/Release 顺序不符')
    final_samples, final_press = ('third_samples', 'third_press_frame') if replayed else ('second_samples', 'second_press_frame')
    for name, lower in (('held_samples', driver['reverse_frame']), (final_samples, driver[final_press])):
        samples = driver[name]
        require(len(samples) == 3 and all(int(s['read_gframe']) > int(lower) for s in samples)
                and all(int(a['read_gframe']) < int(b['read_gframe']) and a['position'] < b['position']
                        for a, b in zip(samples, samples[1:])), '拒绝重放缺原 Held/最终接受段三次真实推进: ' + name)
    return copy.deepcopy(driver)






def facing_correction_evidence(rows, input_evidence, resources):
    """匹配原激活的真实发送／接收；同 basis NoOp 不签 ReplayBasis 或 Rebase。"""
    result = dict(steps={}, replay_or_rebase=[], missing=[],
        initial_acceptance='Initial Request0 has no business Correction ACK; acceptance uses original CMC/GA/raw RMS evidence')
    for step, evidence in input_evidence['steps'].items():
        owner, authority = (evidence['endpoints'][side] for side in ('owner', 'authority'))
        source, accepted = authority['source'], authority['step_facing']['fields']
        sends = [r for r in rows if r['kind'] == 'Combat.PlayerCombo.CorrectionSend'
            and all(r['fields'].get(k) == v for k, v in dict(Ability=source['ability'], World=source['world'],
                Spec=source['ability_spec_handle'], Step=step, StepOrigin=accepted['StepOrigin'],
                Handle=str(source['cmc_motion_handle'])).items())
            and r['fields'].get('Accepted') in ('0', '1')
            and re.fullmatch(r'[1-9][0-9]*', r['fields'].get('Request', '')) is not None]
        if step == '0' and not sends:
            continue  # 初段没有业务纠正 ACK；真实 Continue 拒绝可纠回 ServerStep0。
        matched = []
        for sent in sends:
            receives = [r for r in rows if r['kind'] == 'Combat.PlayerCombo.CorrectionReceive'
                and r['fields'].get('Ability') == owner['source']['ability']
                and r['fields'].get('World') == owner['source']['world'] and r['fields'].get('HasBasis') == '1'
                and all(r['fields'].get(k) == sent['fields'][k] for k in (
                    'Spec', 'ActivationKey', 'Revision', 'Request', 'Step', 'StepOrigin', 'Accepted'))]
            for received in receives:
                require(isinstance(sent['fields'].get('Basis'), list)
                        and isinstance(received['fields'].get('Basis'), list)
                        and facing_rotation_equal(sent['fields']['Basis'], accepted['Entry'])
                        and facing_rotation_equal(received['fields']['Basis'], sent['fields']['Basis']),
                        '原纠正发送／接收没有保留 Authority basis')
                matched.append(dict(send=sent, receive=received))
        if not matched:
            result['missing'].append('CorrectionSendReceive' + step)
            continue
        result['steps'][step] = matched
        # ReplayBasis 和 Rebase 的运行日志来自实际执行分支，不能由 CorrectionReceive 推回。
        for row in rows:
            fields = row['fields']
            if (row['kind'] != 'Combat.PlayerCombo.StepFacing'
                    or fields.get('Ability') != owner['source']['ability']
                    or fields.get('World') != owner['source']['world'] or fields.get('Step') != step
                    or fields.get('StepOrigin') != accepted['StepOrigin']):
                continue
            rotation = fields.get('RebasedEntry') if 'RebasedEntry' in fields else fields.get('Entry')
            if 'RebasedEntry' not in fields and fields.get('Mode') != '2':
                continue
            originals = [source for source in resources if source['ability'] == owner['source']['ability']
                and source['step_index'] == int(step) and fields.get('Handle') == str(source['cmc_motion_handle'])
                and fields.get('Instance') == str(source['montage_instance_id'])
                and ('RebasedEntry' in fields or fields.get('StepToken') == str(source['step_token']))]
            if len(originals) != 1:
                continue  # 未取得该 Replay 原资源窗口，日志不转签给之前的 Task。
            require(isinstance(rotation, list) and facing_rotation_equal(rotation, accepted['Entry']),
                    'ReplayBasis／Rebase 使用了不同 Authority basis')
            require(any(rows.index(item['receive']) < rows.index(row) for item in matched),
                    'ReplayBasis／Rebase 早于对应原纠正接收')
            result['replay_or_rebase'].append(row)
    if not result['replay_or_rebase']:
        result['missing'].append('ActualReplayBasisOrRebaseNotObserved')
    activations = {(item['send']['fields']['Spec'], item['send']['fields']['ActivationKey'])
                   for matched in result['steps'].values() for item in matched}
    require(len(activations) <= 1, '两段纠正不属于同一原预测激活')
    return result


def facing_start_rows(rows, source, mode):
    return [row for row in rows if row['kind'] == 'Combat.PlayerCombo.StepFacing'
        and all(row['fields'].get(k) == v for k, v in dict(Ability=source['ability'], World=source['world'],
            Step=str(source['step_index']), StepToken=str(source['step_token']), Mode=str(mode),
            Handle=str(source['cmc_motion_handle']), Instance=str(source['montage_instance_id'])).items())]


def facing_prediction_at_receive(pair, source):
    """接收点的原资源只认该事件实际字段；相邻帧快照不能填此资格。"""
    fields = pair['receive']['fields']
    names = ('PreStep', 'PreOrigin', 'PreStepToken', 'PreTask', 'PreTaskExists', 'PreTaskActive', 'PreHandle', 'PreInstance', 'PreSourceCurrent')
    missing = [name for name in names if name not in fields]
    if missing:
        return dict(available=False, verified=False, missing=missing)
    verified = (fields['PreStep'] == '1' and fields['PreOrigin'] == fields['Request']
        and fields['PreStepToken'] == str(source['step_token']) and fields['PreTask'] == source['task']
        and fields['PreTaskExists'] == fields['PreTaskActive'] == fields['PreSourceCurrent'] == '1'
        and fields['PreHandle'] == str(source['cmc_motion_handle'])
        and fields['PreInstance'] == str(source['montage_instance_id']))
    return dict(available=True, verified=verified, fields={name: fields[name] for name in names}, missing=[])


def facing_reject_replay_evidence(rows, resources, input_evidence, correction, driver):
    """只接受同原激活的 Reject→Mode2 新资源→第三 Press 接受；运输不代应用。"""
    result = dict(verified=False, missing=[], rejected=None, predicted=None, replayed=None, accepted=None)
    initial, final = (input_evidence['steps'].get(str(i)) for i in (0, 1))
    if initial is None:
        result['missing'].append('ReplayOriginalInitialBasis')
        return result
    initial_owner = initial['endpoints']['owner']['source']
    initial_basis = initial['endpoints']['authority']['step_facing']['fields']['Entry']
    rejects = [pair for pair in correction['steps'].get('0', []) if pair['send']['fields']['Accepted'] == '0']
    require(len(rejects) <= 1, '本 variant 只允许一次实际被拒 Continue')
    if not rejects:
        result['missing'].append('ActualRejectedContinueNotObserved')
        return result
    rejected = rejects[0]
    result['rejected'] = rejected
    fields = rejected['send']['fields']
    require(fields['Step'] == '0' and fields['StepOrigin'] == '0' and int(fields['Request']) > 0
            and facing_rotation_equal(rejected['receive']['fields']['Basis'], initial_basis),
            '实际拒绝没有携原 Authority Step0/Origin0/basis')
    attempt = driver['rejected_attempt']
    if attempt is None:
        result['missing'].append('OriginalSecondPressGateObservation')
    else:
        require(attempt['frame_domain'] == 'OwnerInputSubmissionGFrameCounter_NotInputEvaluation'
                and attempt['owner_submission_frame'] == str(driver['second_press_frame']),
                '原门差快照不在第二 Press 的实际提交帧')
        for side in ('owner', 'authority'):
            view = attempt[side]
            require(view['current_step'] == 0 and view['step_source'] == initial['endpoints'][side]['source']
                    and view['attack_continuation_open'] is (side == 'owner')
                    and view['step_record']['live_original_snapshot_available'] is True
                    and view['step_record']['original_ga_resource_source_current'] is True
                    and view['step_record']['sample_frame'] == attempt['owner_submission_frame'],
                    '第二 Press 没有同帧真实 owner0 开门/Authority0 关门及原资源许可')
        result['rejected_attempt'] = copy.deepcopy(attempt)
    predicted, replayed = [], []
    for (side, step, _serial), state in resources.items():
        source = state['original_source']
        if side != 'owner':
            continue
        require(all(source[k] == initial_owner[k] for k in ('ability', 'ability_spec_handle', 'asc', 'pawn', 'world')),
                '拒绝重放混入其它原 GA/ASC/World')
        if step == 1:
            starts = [r for r in facing_start_rows(rows, source, 1) if r['fields']['StepOrigin'] == fields['Request']]
            if starts:
                require(len(starts) == 1, '被拒的原预测资源起段重复')
                predicted.append(dict(source=source, start=starts[0], state=state))
        elif step == 0:
            starts = [r for r in facing_start_rows(rows, source, 2) if r['fields']['StepOrigin'] == '0'
                      and r in correction['replay_or_rebase']]
            if starts:
                require(len(starts) == 1, '原 Mode2 Replay 资源起段重复')
                replayed.append(dict(source=source, start=starts[0], state=state))
    require(len(predicted) <= 1 and len(replayed) <= 1, '原被拒/回放资源关联不唯一')
    if not predicted or not replayed:
        result['missing'].append('OriginalPredicted1AndNewMode2Resource0')
        return result
    prediction, replay = predicted[0], replayed[0]
    old, new = prediction['source'], replay['source']
    receive_live = facing_prediction_at_receive(rejected, old)
    result['prediction_at_receive'] = receive_live
    if not receive_live['verified']:
        result['missing'].append('OriginalPredictionAliveAtCorrectionReceiveNotObserved')
    require(all(new[k] != previous[k] for previous in (initial_owner, old)
                for k in ('task', 'step_token', 'montage_instance_id', 'cmc_motion_handle')),
            'Mode2 未创建真实新 Task/token/Handle/Instance，不能给旧资源换标签')
    require(rows.index(prediction['start']) < rows.index(rejected['receive']) < rows.index(replay['start'])
            and facing_rotation_equal(replay['start']['fields']['Entry'], initial_basis)
            and not facing_rotation_equal(prediction['start']['fields']['Entry'], initial_basis),
            'Mode2 未在原拒绝后沿保存 basis 回放，或错误使用当前反向 basis')
    position, sent_position = float(replay['start']['fields']['Position']), float(rejected['receive']['fields']['Position'])
    require(math.isfinite(position) and math.isfinite(sent_position) and 0 <= position <= sent_position + 0.000001
            and sent_position-position <= 0.001001, '原 Mode2 时钟没有沿服务器 Position/合法末端 clamp')
    if position <= 0:
        result['missing'].append('NonZeroOriginalReplayPositionNotObserved')
    live = [r for r in replay['state']['records'] if r['live_original_snapshot_available']
            and r['original_ga_resource_source_current']]
    if not live:
        result['missing'].append('OriginalMode2LiveTaskClock')
    else:
        require(all(math.isfinite(r['position_seconds']) and r['position_seconds'] + 0.000001 >= position for r in live),
                '原 Mode2 live Task 时钟倒退到纠正前位置')
    result['predicted'] = dict(source=copy.deepcopy(old), start=prediction['start'],
        retirement_record=copy.deepcopy(prediction['state']['records'][-1]) if prediction['state']['records'] else None)
    facts = [r for r in rows if r['kind'] == 'Movement.ActionStartInput'
        and all(r['fields'].get(k) == v for k, v in dict(CMC=old['cmc'], World=old['world'], Pawn=old['pawn'],
            Remote='0', Request=fields['Request'], Kind='1', SourceStep='0', InputState='1').items())]
    if len(facts) != 1 or 'edge' not in initial['evaluations']:
        result['missing'].append('OriginalRejectedInputFact')
    else:
        fact = facts[0]['fields']
        axis = float(fact['AxisX']), float(fact['AxisY'])
        require(all(math.isfinite(v) for v in axis) and abs(axis[0]) < 0.000001 and axis[1] < 0,
                '被拒的实际预测请求没有原反向 Held 输入')
        source_eval = initial['evaluations']['edge']['fields']
        completed = [r for r in rows if r['kind'] == 'Input.MovementEvaluation'
            and all(r['fields'].get(k) == v for k, v in dict(Phase='Completed', World=source_eval['World'],
                PC=source_eval['PC'], Pawn=source_eval['Pawn'], PlayerInput=source_eval['PlayerInput'],
                Action=source_eval['Action'], SessionSerial=fact['Session'], EvaluationSerial=fact['EdgeEvaluation']).items())]
        if len(completed) != 1:
            result['missing'].append('ActualSecondPressInputCompleted')
        else:
            evaluated = completed[0]['fields']
            value = re.fullmatch(r'\(X=([^,]+),Y=([^\)]+)\)', evaluated['ActionValue'])
            require(evaluated['ValueState'] == 'Readable' and evaluated['EntryFrame'] == evaluated['CompletedFrame']
                    and value is not None and all(float(v) == actual for v, actual in zip(value.groups(), axis))
                    and int(evaluated['CompletedFrame']) >= int(driver['second_press_frame'])
                    and (driver.get('third_press_frame') is None
                         or int(evaluated['CompletedFrame']) < int(driver['third_press_frame'])),
                    '原第二 Press 的真实完整输入评价值/帧与被拒请求不符')
        transport = {}
        for side, boundary in (('owner', 'SendAttempt'), ('authority', 'RPCImplementation')):
            source = initial['endpoints'][side]['source']
            matches = [r for r in rows if r['kind'] == 'AbilitySystem.OwnedStepInput'
                and all(r['fields'].get(k) == v for k, v in dict(Boundary=boundary, ASC=source['asc'],
                    World=source['world'], Spec=fields['Spec'], ActivationKey=fields['ActivationKey'],
                    Kind='1', SourceStep='0', Request=fields['Request'], Edge=fact['EdgeEvaluation'], Entry=fact['StepEvaluation']).items())]
            if len(matches) != 1:
                result['missing'].append(side + '.OriginalRejectedRequestTransport')
            else:
                transport[side] = matches[0]
        result['predicted'].update(input=facts[0], input_completed=completed, transport=transport)
    result['replayed'] = dict(source=copy.deepcopy(new), start=replay['start'],
        live_records=copy.deepcopy(live), uses_saved_authority_basis_over_reverse_input=True)
    if final is None:
        result['missing'].append('ThirdPressFinalAcceptedStep1')
        return result
    accepted = [pair for pair in correction['steps'].get('1', []) if pair['send']['fields']['Accepted'] == '1']
    if len(accepted) != 1:
        result['missing'].append('ActualThirdContinueAcceptedSendReceive')
        return result
    accepted = accepted[0]
    final_owner = final['endpoints']['owner']['source']
    require(all(accepted['send']['fields'][k] == fields[k] for k in ('Spec', 'ActivationKey'))
            and int(accepted['send']['fields']['Request']) > int(fields['Request'])
            and accepted['send']['fields']['StepOrigin'] == accepted['send']['fields']['Request']
            and all(final_owner[k] != old[k] for k in ('task', 'step_token', 'montage_instance_id', 'cmc_motion_handle'))
            and all(final_owner[k] != new[k] for k in ('task', 'step_token', 'montage_instance_id', 'cmc_motion_handle')),
            '第三次真实请求没有沿原激活创建最终接受的新 step1 资源')
    if driver['attack_attempts'] != 3 or driver.get('third_press_frame') is None:
        result['missing'].append('OriginalThirdPressNotSubmitted')
    else:
        actual = int(final['evaluations']['edge']['fields']['CompletedFrame']) if 'edge' in final['evaluations'] else None
        if actual is None or actual < int(driver['third_press_frame']):
            result['missing'].append('ActualThirdInputEvaluation')
    result['accepted'] = accepted
    result['verified'] = not result['missing']
    return result


def facing_resource_retirement(rows, resources, bindings):
    """从原 Task/Instance 读数和后继同 CMC 完整 raw 容器证明实际退出。"""
    result = dict(verified=False, pending=False, missing=[], resources=[])
    streams = {}
    for (side, _step, _serial), state in resources.items():
        source = state['original_source']
        expected = dict(world=source['world'], character=source['pawn'], movement=source['cmc'],
                        local_role=2 if side == 'owner' else 3)
        for record in state['records']:
            native = facing_native_snapshot(record, expected)
            if native['available']:
                require(record['sample_frame'] == native['frame'], '原动作 Sample/raw 不在同一个 GT 读帧')
            streams.setdefault(side, []).append((record, native))
    fixed = ('script_struct', 'instance_name', 'source_mode', 'local_id', 'native_imported',
        'has_original_montage_binding', 'montage', 'slot', 'track_index', 'binding_initial_section_name',
        'binding_initial_section_index', 'binding_start_seconds', 'binding_end_seconds', 'sections', 'segments',
        'montage_start_seconds', 'duration_seconds', 'play_rate')
    identity = lambda source: json.dumps({k: source[k] for k in fixed}, sort_keys=True, allow_nan=False)
    for key, state in resources.items():
        side, step, serial = key
        source = state['original_source']
        label = side + '.' + str(step) + '.' + str(serial)
        expected_binding = bindings[key]
        item = dict(source=copy.deepcopy(source), task_retired=False, instance_retired=False,
                    native_association=None, native_absent=False, native_progressed=False)
        native_candidates, own = {}, []
        starts = facing_start_rows(rows, source, 1) + facing_start_rows(rows, source, 2)
        require(len(starts) <= 1, '同原资源对应多个 Native 起段')
        basis = [r for r in rows if r['kind'] == 'Movement.ActionStartBasis'
            and all(r['fields'].get(k) == v for k, v in dict(CMC=source['cmc'], Montage=source['montage'],
                Handle=str(source['cmc_motion_handle']), Instance=str(source['montage_instance_id'])).items())]
        require(len(basis) <= 1, '原 Handle/Instance 的 NativeId 接受日志不唯一')
        for record in state['records']:
            task, instance = record['original_task_live'], record['original_montage_instance_live']
            binding = record['original_motion_binding']
            require(binding['cmc_motion_handle'] == source['cmc_motion_handle']
                    and binding['montage_instance_id'] == source['montage_instance_id']
                    and type(binding['has_native_id']) is bool, '原 motion binding 已转签后继')
            require(task['path'] == source['task'] and task['object_id'] == source['task_object_id']
                    and type(task['available']) is bool, '原 Task 弱身份不符')
            require(instance['montage_instance_id'] == source['montage_instance_id']
                    and instance['mesh'] == source['mesh'] and instance['mesh_object_id'] == source['mesh_object_id']
                    and instance['anim_instance'] == source['anim_instance']
                    and instance['anim_instance_object_id'] == source['anim_instance_object_id']
                    and type(instance['available']) is bool, '原 Mesh/Anim/Instance 身份不符')
            if task['available']:
                require(type(task['exists']) is bool, '原 Task 存续字段不可读')
                if not task['exists']:
                    require(not any(k in task for k in ('active', 'finished', 'state')), 'Gone 不得填 Task 状态零值')
                else:
                    require(type(task['active']) is bool and type(task['finished']) is bool
                            and type(task['state']) is int and task['state'] in range(5), '原 Task 状态不可读')
            if instance['available']:
                require(type(instance['exists']) is bool, '原 Montage Instance 存续不可读')
                if instance['exists']:
                    require(type(instance['active']) is bool and type(instance['playing']) is bool,
                            '原 Montage Instance 活动状态不可读')
            if not record['original_ga_resource_source_current']:
                item['task_retired'] = (task['available'] and (not task['exists']
                    or not task['active'] and task['finished'] and task['state'] == 4))
                item['instance_retired'] = (instance['available'] and (not instance['exists'] or not instance['active']))
                if item['task_retired'] and item['instance_retired']:
                    item['retirement_record'] = dict(sample_frame=record['sample_frame'], task=task, instance=instance)
            native = facing_native_snapshot(record, dict(world=source['world'], character=source['pawn'],
                movement=source['cmc'], local_role=2 if side == 'owner' else 3))
            if not native['available'] or not record['original_ga_resource_source_current'] or not starts:
                continue
            start = starts[0]['fields']
            for container in ('active_sources', 'pending_sources'):
                for raw in native[container]:
                    if (raw['source_mode'] != ORIGINAL_MONTAGE_SOURCE_MODE or raw['native_imported'] or not raw['has_original_montage_binding']
                            or raw['montage'] != source['montage'] or raw['slot'] != expected_binding['slot']
                            or raw['binding_initial_section_name'] != expected_binding['main']):
                        continue
                    if basis:
                        matches = raw['local_id'] == int(basis[0]['fields']['NativeId'])
                    else:
                        matches = (start['Mode'] == '2' and raw['has_entry_actor_rotation']
                            and abs(raw['montage_start_seconds']-float(start['Position'])) <= 0.000001
                            and facing_rotation_equal(raw['entry_actor_rotation'], start['Entry']))
                    if matches:
                        descriptor = identity(raw)
                        native_candidates.setdefault(descriptor, dict(first_frame=native['frame'], source=copy.deepcopy(raw)))
                        own.append((descriptor, native, container, raw))
        if len(native_candidates) == 1:
            descriptor, association = next(iter(native_candidates.items()))
            item['native_association'] = association
            progression = [(native, raw) for token, native, container, raw in own if token == descriptor
                and container == 'active_sources' and not raw['finished'] and not raw['marked_for_removal']
                and not raw['explicitly_cancelled']]
            item['native_progressed'] = any(int(b[0]['frame']) > int(a[0]['frame'])
                and b[1]['native_time_seconds'] > a[1]['native_time_seconds'] for a, b in zip(progression, progression[1:]))
            reads = streams[side]
            if reads:
                latest_record, latest = max(reads, key=lambda pair: (int(pair[0]['sample_frame']), pair[0]['elapsed_seconds']))
                unavailable = [record['sample_frame'] for record, native in reads if not native['available']
                    and int(record['sample_frame']) >= int(association['first_frame'])]
                if unavailable:
                    result['missing'].append(label + '.RawUnavailableAfterOriginalAssociation')
                item['native_absent'] = (latest['available'] and not unavailable
                    and int(latest['frame']) >= int(association['first_frame'])
                    and not any(raw['local_id'] == association['source']['local_id']
                        for container in ('active_sources', 'pending_sources') for raw in latest[container]))
                item['last_native_read'] = dict(sample_frame=latest_record['sample_frame'], status=latest['status'])
                if latest['available'] and not item['native_absent'] and not unavailable:
                    result['pending'] = True
        else:
            result['missing'].append(label + '.NativeAssociationCount=' + str(len(native_candidates)))
        if not item['task_retired']:
            result['missing'].append(label + '.OriginalTaskNotRetired')
        if not item['instance_retired']:
            result['missing'].append(label + '.OriginalInstanceStillActiveOrUnavailable')
        if not item['native_absent']:
            result['missing'].append(label + '.OriginalNativeNotAbsent')
        if starts and starts[0]['fields']['Mode'] == '2' and not item['native_progressed']:
            result['missing'].append(label + '.ActualMode2NativeProgress')
        result['resources'].append(item)
    result['verified'] = bool(resources) and not result['missing']
    if not resources:
        result['missing'].append('OriginalActionResourceWindowsNotObserved')
    return result


def facing_replay_actions_complete(actions):
    """变体可在真实单段未续上时自然退出；末个实际原资源仍须完整自然结束。"""
    for side in ('owner', 'authority'):
        views = [view for (label, _step, _serial), view in actions.items() if label == side]
        if not views or not natural_exit(views[-1].state):
            return False
        final = views[-1]
        for view in views:
            require(all(view.source[k] == final.source[k] for k in ('ability', 'ability_spec_handle', 'asc', 'pawn', 'world')),
                    '重放各代资源不属于原同端 GA/Spec/ASC/World')
            state = view.state
            if state['evidence_incomplete'] or not state['records'] or state['records'][-1]['original_ga_resource_source_current']:
                return False
            if view is not final and not state['original_ga_full_exit_completed']:
                if state['active'] or not state['subscriptions_released'] or state['stop_reason'] != 'OriginalSourceInvalidated':
                    return False
    return True




def facing_pose_evidence(records, expected, steps, *, imported):
    """从原观察窗口重读逐源证据；local_id 只在本进程的同源时间线上分组。"""
    native = [facing_native_snapshot(row, expected) for row in records]
    result = dict(steps={}, no_action_source=bool(native and native[-1]['status'] == 2))
    for step, original in steps.items():
        groups = {}
        for snapshot in native:
            if snapshot['status'] == 0:
                continue
            for container in ('active_sources', 'pending_sources'):
                for source in snapshot[container]:
                    if source['source_mode'] != ORIGINAL_MONTAGE_SOURCE_MODE or source.get('montage') != original['montage']:
                        continue
                    require(source['has_entry_actor_rotation'] and source['has_original_montage_binding']
                            and source['native_imported'] is imported, '原 Montage RMS 的 entry/binding/import 状态不符')
                    key = source['local_id']
                    sample = dict(frame=snapshot['frame'], world_time_seconds=snapshot['world_time_seconds'],
                                  container=container, source=copy.deepcopy(source))
                    groups.setdefault(key, []).append(sample)
        evidence = []
        for samples in groups.values():
            first = samples[0]
            require(all(facing_rotation_equal(first['source']['entry_actor_rotation'], s['source']['entry_actor_rotation'])
                        for s in samples), '同一原 Montage RMS 的 entry 在段内发生变化')
            binding_fields = ('montage', 'slot', 'track_index', 'binding_initial_section_name',
                              'binding_initial_section_index', 'binding_start_seconds', 'binding_end_seconds',
                              'sections', 'segments')
            require(all(all(s['source'][k] == first['source'][k] for k in binding_fields) for s in samples),
                    '同一原 Montage RMS 的完整 binding 发生变化')
            active = [s for s in samples if s['container'] == 'active_sources'
                      and not any(s['source'][k] for k in ('finished', 'marked_for_removal', 'explicitly_cancelled'))]
            progressed = any(int(b['frame']) > int(a['frame'])
                             and b['source']['native_time_seconds'] > a['source']['native_time_seconds']
                             for a, b in zip(active, active[1:]))
            evidence.append(dict(first=first, last=samples[-1], progressed=progressed))
        result['steps'][step] = dict(original_source=copy.deepcopy(original), sources=evidence,
                                     progressed=any(item['progressed'] for item in evidence))
    return result


def fx_active(packet, system=None):
    """只接受原 Authority 关联的 Active 行；Terminal 不能触发迟到 Travel。"""
    if not packet:
        return None
    terminal = {r['terminal_occurrence'] for r in packet['records'] if r.get('has_terminal')}
    rows = [r for r in packet['records'] if r.get('has_record') is True
            and r.get('active_record') is True and r.get('avatar_mesh_association_known') is True
            and (system is None or r.get('system') == system)
            and r.get('occurrence') not in terminal and int(r['occurrence']) > 0]
    return rows[-1] if rows else None




def fx_tail_viewport_witness(packet, probe, native):
    """活尾只认该原实例在真实 Draw 帧的原生样本；不借闭窗前的 reached 或相邻帧。"""
    if not probe or "tail" not in probe:
        return None
    start, tail = probe["start"], probe["tail"]
    rows = [row for row in packet["records"]
            if all(row.get(k) == start[k] for k in ("occurrence", "generation", "component_id"))
            and row["native_event_frame"] == native["render_callback_frame"]
            and int(row["native_event_frame"]) > int(tail["native_event_frame"])
            and all(row.get(k) is True for k in ("tail_transferred", "rendering_enabled", "registered",
                                                "controller_valid", "controller_age_valid"))
            and row.get("controller_complete") is False and row.get("controller_pending_spawn") is False
            and row["controller_age"] > tail["controller_age"]]
    return rows[-1] if rows else None


def fx_tail_seek_evidence(packet, probe):
    start, hidden, tail = (probe[k] for k in ("start", "hidden", "tail"))
    require(fx_reached(start) and 0 < probe["applied_budget"] < probe["original_budget"],
            "缺原 reached 或实际 seek 预算刺激")
    require(all(row in packet["records"] for row in (start, hidden, tail)), "专项快照不在原观察窗")
    require(all(all(row[k] == start[k] for k in ("occurrence", "generation", "component_id")) for row in (hidden, tail)),
            "追赶隐藏／活尾不是同一个原实例")
    require(int(hidden["native_event_frame"]) > int(probe["applied_frame"])
            and hidden["reached"] and not hidden["rendering_enabled"] and hidden["active_record"]
            and hidden["target_age_valid"] and hidden["controller_age_valid"]
            and hidden["target_age"] - hidden["controller_age"] >= hidden["remote_seek_delta_seconds"],
            "未实际覆盖曾 reached 后再次追赶不足并隐藏")
    require(int(tail["native_event_frame"]) > int(hidden["native_event_frame"])
            and tail["kind"] == "TailTransferred" and tail["rendering_enabled"] and probe["tail_native_tick_mode"],
            "正常活尾未恢复原生时间模式和渲染")
    rows = [r for r in packet["records"] if r["component_id"] == start["component_id"]]
    complete = [r for r in rows if r["kind"] == "NaturalCompleted"
                and int(r["native_event_frame"]) > int(tail["native_event_frame"])
                and r["controller_age_valid"] and r["controller_age"] > tail["controller_age"]]
    require(complete and any(r["kind"] == "ComponentDestroyed"
                            and int(r["native_event_frame"]) >= int(complete[0]["native_event_frame"]) for r in rows),
            "原活尾没有真实推进、自然完成与销毁")
    return dict(hidden=hidden, tail=tail, natural_completed=complete[0])


def fx_reached(row):
    """actual controller Age 与原服务器目标 Age 分别来自 Native；desired Age 不作完成时钟。"""
    flags = ('remote_entry', 'resource_state_known', 'controller_valid', 'controller_age_valid',
             'target_age_valid', 'reached', 'rendering_enabled', 'registered',
             'active_record', 'has_record', 'avatar_mesh_association_known')
    if not all(row.get(k) is True for k in flags):
        return False
    if row.get('controller_complete') is not False or row.get('controller_pending_spawn') is not False:
        return False
    # NiagaraTypes.h 的 Active 为 0；GGYGORemoteMontageFXComponent 在 Finalize 后才发布 reached。
    if row.get('actual_execution_state') != 0 or row.get('requested_execution_state') != 0:
        return False
    age, target, step = (row[k] for k in ('controller_age', 'target_age', 'effective_step'))
    return all(type(x) in (int, float) and math.isfinite(x) for x in (age, target, step)) \
        and target >= 0 and age >= 0 and step > 0 and abs(age - target) < step




def fx_dispatched_close(packet, occurrence=None):
    rows = [row for row in (packet or {}).get('records', []) if row['kind'] == 'TerminalDispatched'
            and row['has_terminal'] is True and (occurrence is None or row['terminal_occurrence'] == occurrence)]
    require(len(rows) <= 1, '原 Authority 关闭键不唯一')
    return rows[0] if rows else None


def fx_live_rows(records, joined):
    rows = [row for row in records if row['occurrence'] == joined['occurrence'] and row['has_record'] is True]
    require(all(row['begin_server_time'] == joined['begin_server_time'] for row in rows), '同键原 BeginServerTime 不符')
    return [row for row in rows if int(row['state_revision']) >= int(joined['state_revision']) and fx_reached(row)]


def fx_closed_rows(records, closed):
    key = closed['terminal_occurrence']
    require(not any(row['occurrence'] == key and (row['kind'] == 'RemoteCreated'
                or row['active_record'] or row['remote_entry']) for row in records),
            '闭窗首次加入后观察到旧键重新创建、激活或远端资源')
    # 0 键是原 Publisher 空快照。当前 API 只能证明 attach 后的观察区间。
    return [row for row in records if row['kind'] == 'Snapshot' and row['publisher_context_only'] is True
            and int(row['state_revision']) >= int(closed['close_revision'])]


def fx_replication_witness(state, joined, *, closed, through_frame=None):
    key = joined['terminal_occurrence'] if closed else joined['occurrence']
    records = state['records']
    receipts = [row for row in records if row['kind'] == 'StateReceived']
    creates = [row for row in records if row['kind'] == 'RemoteCreated' and row['occurrence'] == key]
    if closed:
        require(not creates and all(key not in row['active_occurrences'] for row in receipts),
                'B 连续原窗观察到已关闭键的复制活动或 RemoteCreated')
        witness = receipts[0] if receipts and int(receipts[0]['state_revision']) >= int(joined['close_revision']) else None
    else:
        witness = next((row for row in receipts if key in row['active_occurrences']
                        and int(row['state_revision']) >= int(joined['state_revision'])), None)
    return witness if witness and (through_frame is None or int(witness['native_event_frame']) <= int(through_frame)) else None


def fx_reacquire_creation(state, joined, report, draw_frame):
    return next((row for row in state['records'] if row['kind'] == 'RemoteCreated'
                 and row['occurrence'] == joined['occurrence']
                 and int(row['avatar_id']) == report['new']['pawn_id']
                 and int(report['retired']['retired_frame']) <= int(row['native_event_frame']) <= int(draw_frame)), None)


def fx_channel_log_event(line, anchor, *, cleanup, creation=False):
    actor = re.escape(anchor['pawn_full_name'])
    index = anchor['channel_index']
    guid = re.escape(anchor['pawn_net_guid'])
    if creation:
        name = re.escape(anchor['pawn'].rsplit('.', 1)[-1])
        return re.search(rf'LogNetLifecycle: UActorChannel::ProcessBunch: Creating ChIndex: {index} Actor: {name}\s*$', line) is not None
    if cleanup:
        event = rf'UActorChannel::CleanUp \(ChIndex: {index}\): {actor} \| NetGuid: {guid} \| Reason: Relevancy\s*$'
    else:
        event = rf'UActorChannel::Close: ChIndex: {index}, Actor: {actor}, Reason: Relevancy\s*$'
    return re.search(r'LogNetTraffic: (?:Display: |Log: )?' + event, line) is not None


def read_fx_channel_event(path, cursor, anchor, *, cleanup, creation=False):
    with path.open('rb') as log:
        log.seek(cursor)
        while line := log.readline():
            if not line.endswith(b'\n'):
                break
            decoded = line.decode('utf-8', errors='replace').rstrip('\r\n')
            if fx_channel_log_event(decoded, anchor, cleanup=cleanup, creation=creation):
                return log.tell(), dict(path=str(path), offset=cursor, line=decoded)
            cursor = log.tell()
    return cursor, None


def fx_viewport_witness(mode, state, joined, native):
    """在 B 的同一 GT 帧轴核自然 Draw；PNG 中的可见效果另由原图确认。"""
    request_frame = int(native['request_frame'])
    draw_frame = int(native['render_callback_frame'])
    require(0 < request_frame <= draw_frame <= int(native['readback_complete_frame']),
            'B 原视口请求／自然 Draw／读回帧顺序无效')
    records = state['records']
    if mode == 'closed_first':
        candidates = fx_closed_rows(records, joined)
        if not any(int(row['native_event_frame']) <= request_frame for row in candidates):
            return None
    else:
        candidates = fx_live_rows(records, joined)
        if any(row['has_terminal'] and row['terminal_occurrence'] == joined['occurrence']
                and int(row['native_event_frame']) <= draw_frame for row in records):
            return None
        identity = ('generation', 'component_id', 'controller_id')
        ready = {tuple(row[k] for k in identity) for row in candidates
                 if int(row['native_event_frame']) <= request_frame
                 and all(int(row[k]) > 0 for k in identity)}
        candidates = [row for row in candidates if tuple(row[k] for k in identity) in ready]
    return next((row for row in candidates if row['kind'] == 'Snapshot'
                 and int(row['native_event_frame']) == draw_frame), None)


def natural_exit(state):
    """原生完整自然历史与非取消退出为准；旧回执的额外 kind 须保持一致。"""
    return bool(state and state.get('natural_completion_history_complete') is True
                and state.get('original_ga_full_exit_completed') is True
                and state.get('original_exit_cancelled') is False
                and ('original_exit_kind' not in state or state['original_exit_kind'] == 'End'))
