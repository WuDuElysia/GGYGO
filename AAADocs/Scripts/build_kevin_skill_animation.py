"""Kevin 可编辑 Montage 制作入口；GA、AI、FX 和 Audio 仍各自拥有执行逻辑。

Root 先消费原 Motion/Slot/Socket/ABP 原生制作入口，再在同一已准入窗口调用 run。
只创建明确批准的新 Montage；已有目标只核验，不重建或删除作者 Notify。
源序列和 FBX 从不写入。失败保留真实未保存现场，不回滚其他组资产。
"""
import argparse
import hashlib
import json
import math
import struct
from collections import Counter
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT / 'AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Montage_Config.json'
ROOT = '/Game/Characters/Boss/Kevin/DemonBattle/Animation/'
OWNER = 'GGYGO.KevinSkillAnimation/v1'


def require(ok, message):
    if not ok:
        raise RuntimeError('Kevin Animation: ' + message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def load_config(expected_sha256):
    require(digest(CONFIG) == expected_sha256, '配置身份改变，不能消费旧制作计划')
    cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    require(cfg['skill_assembly_schema'] == OWNER, '缺准确技能装配合同')
    return cfg


def make_plan(cfg, skill_ids):
    require(skill_ids and len(skill_ids) == len(set(skill_ids)), '必须显式选择唯一技能，不隐式制作全部')
    catalog = {row['id']: row for row in cfg['skill_assemblies']}
    require(len(catalog) == len(cfg['skill_assemblies']), '重复技能 id')
    rows = []
    for key in skill_ids:
        require(key in catalog, '未知技能：' + key)
        row = catalog[key]
        require(row['montage'].startswith(ROOT + 'Montage/') and row['play_rate'] == 1., '目标或速率合同无效')
        segments = row['segments']
        require(segments and segments[0]['section'] == row['main_section'], '缺首段')
        require(len({s['section'] for s in segments}) == len(segments), '重复 Section')
        require(all(s['loop_count'] == 1 and s['derived_sequence'].startswith(ROOT + 'Derived/') for s in segments),
                '只制作明确的完整源有限单次片段')
        require(row['motion_end_section'] == (segments[-1]['section'] if len(segments) > 1 else 'None'), '首末段不一致')
        previous = -1.
        for window in row['hit_windows']:
            start, end = window['start_seconds'], window['end_seconds']
            require(all(type(x) in (int, float) and math.isfinite(x) for x in (start, end))
                    and start >= 0 and start > previous and end > start, 'Hit 窗口必须顺序、非重叠且有限')
            require(window.get('begin_event_tag') and window.get('end_event_tag'), '缺每窗唯一标签：' + key)
            previous = end
        rows.append(row)
    require(len({r['montage'] for r in rows}) == len(rows), '技能目标冲突')
    return rows


def dirty(ue):
    lib = ue.EditorLoadingAndSavingUtils
    return dict(content=sorted(p.get_path_name() for p in lib.get_dirty_content_packages()),
                maps=sorted(p.get_path_name() for p in lib.get_dirty_map_packages()))


def load(ue, package, cls):
    obj = ue.EditorAssetLibrary.load_asset(package)
    require(isinstance(obj, cls) and obj.get_path_name() == package + '.' + package.rsplit('/', 1)[1],
            '缺实际原资产或发生重定向：' + package)
    return obj


def tag(ue, name):
    value = ue.GameplayTag()
    value.import_text('(TagName="' + name + '")')
    require(value.export_text() == '(TagName="' + name + '")'
            and ue.GameplayTagLibrary.is_gameplay_tag_valid(value), '标签未注册：' + name)
    return value


def timeline(ue, montage):
    facts = ue.GGYGOLinearMontageAuthorLibrary.read_montage_timeline_facts(montage)
    require(facts.get_editor_property('succeeded'), str(facts.get_editor_property('error')))
    sections = [{k: str(s.get_editor_property(k)) if k in ('section_name', 'next_section_name')
                 else s.get_editor_property(k) for k in ('section_name', 'next_section_name', 'time')}
                for s in facts.get_editor_property('sections')]
    tracks = montage.get_editor_property('slot_anim_tracks')
    segments = []
    for track in tracks:
        for s in track.get_editor_property('anim_track').get_editor_property('anim_segments'):
            values = {k: s.get_editor_property(k) for k in
                      ('start_pos', 'anim_start_time', 'anim_end_time', 'anim_play_rate', 'looping_count')}
            values['source'] = s.get_editor_property('anim_reference').get_path_name()
            values['slot'] = str(track.get_editor_property('slot_name'))
            segments.append(values)
    native_notifies = list(facts.get_editor_property('notifies'))
    return dict(native=facts.export_text(), sections=sections, segments=segments,
                play_length=facts.get_editor_property('play_length'),
                notifies=[n.export_text() for n in native_notifies],
                notify_values=[{k: n.get_editor_property(k) for k in
                                ('guid', 'notify_object', 'time', 'duration', 'trigger_time_offset', 'end_trigger_time')}
                               for n in native_notifies])


def state_specs(row, fx_windows, audio_windows):
    specs = []
    for i, window in enumerate(row['hit_windows'], 1):
        specs.append(dict(id=f'Hit{i:02d}', start=window['start_seconds'], end=window['end_seconds'],
                          begin=window['begin_event_tag'], finish=window['end_event_tag'], track='KVB_Hit'))
    for fx in fx_windows:
        if fx['action_id'] == row['id']:
            specs.append(dict(id='FX_' + fx['phase_id'], start=fx['window_seconds'][0], end=fx['window_seconds'][1],
                              begin=fx['begin_event_tag'], finish=fx['end_event_tag'], track='KVB_FX'))
    for audio in audio_windows:
        if audio['action_id'] == row['id']:
            specs.append(dict(id='Audio_' + audio['phase_id'], start=audio['window_seconds'][0],
                              end=audio['window_seconds'][1], begin=audio['begin_tag'],
                              finish=audio['end_tag'], track='KVB_AudioLoop'))
    tags = [s[k] for s in specs for k in ('begin', 'finish')]
    require(len(set(tags)) == len(tags), '同一 Montage 不允许复用窗口标签：' + row['id'])
    return specs


def read_states(ue, montage, values):
    result = []
    for event in ue.AnimationLibrary.get_animation_notify_events(montage):
        state = event.get_editor_property('notify_state_class')
        if isinstance(state, ue.GGYGOAnimNotifyState_GameplayEventWindow):
            native = next(n for n in values if n['notify_object'] == state.get_path_name())
            result.append(dict(object=state.get_path_name(), native=native,
                               begin=state.get_editor_property('begin_event_tag').export_text(),
                               end=state.get_editor_property('end_event_tag').export_text(),
                               flags=state.get_editor_property('notify_state_behavior_flags'),
                               tick=str(event.get_editor_property('montage_tick_type'))))
    return result


def read_audio(ue, montage, values):
    result = []
    for event in ue.AnimationLibrary.get_animation_notify_events(montage):
        notify = event.get_editor_property('notify')
        if isinstance(notify, ue.AnimNotify_PlaySound):
            native = next(n for n in values if n['notify_object'] == notify.get_path_name())
            sound = notify.get_editor_property('Sound')
            require(sound is not None, 'PlaySound 缺真实 Sound')
            result.append(dict(object=notify.get_path_name(), guid=native['guid'], time=native['time'],
                               sound=sound.get_path_name(), volume=notify.get_editor_property('volume_multiplier'),
                               pitch=notify.get_editor_property('pitch_multiplier'),
                               follow=notify.get_editor_property('follow'),
                               attach_name=str(notify.get_editor_property('attach_name'))))
    return result


def _append_notifies(ue, montage, specs, sounds):
    tracks = []
    for spec in specs:
        if spec['track'] not in tracks:
            ue.AnimationLibrary.add_animation_notify_track(montage, spec['track'])
            tracks.append(spec['track'])
        state = ue.AnimationLibrary.add_animation_notify_state_event(
            montage, spec['track'], spec['start'], spec['end'] - spec['start'], ue.GGYGOAnimNotifyState_GameplayEventWindow)
        require(state is not None and state.get_outer() == montage, 'State 工厂未返回原 Montage 子对象')
        state.set_editor_property('begin_event_tag', spec['tags'][0])
        state.set_editor_property('end_event_tag', spec['tags'][1])
        state.set_editor_property('notify_state_behavior_flags', 1)
    if sounds:
        ue.AnimationLibrary.add_animation_notify_track(montage, 'KVB_Audio')
    for audio, sound in sounds:
        point = ue.AnimationLibrary.add_animation_notify_event(
            montage, 'KVB_Audio', audio['time_seconds'], ue.AnimNotify_PlaySound)
        require(point is not None and point.get_outer() == montage, 'PlaySound 工厂未返回原 Montage 子对象')
        point.set_editor_property('Sound', sound)
        parameters = audio['parameters']
        for name, value in [('volume_multiplier', parameters['volume']), ('pitch_multiplier', parameters['pitch']),
                            ('follow', parameters['follow']), ('attach_name', parameters['attach_name'])]:
            point.set_editor_property(name, value)


def _read_and_verify_notifies(ue, montage, specs, sounds):
    observed = timeline(ue, montage)
    states = read_states(ue, montage, observed['notify_values'])
    points = read_audio(ue, montage, observed['notify_values'])
    by_tags = {(x['begin'], x['end']): x for x in states}
    require(len(states) == len(specs) == len(by_tags), 'State 数量或唯一标签对不同制作合同')
    for spec in specs:
        pair = (spec['tags'][0].export_text(), spec['tags'][1].export_text())
        require(pair in by_tags, 'State 标签对不同制作合同')
        state = by_tags[pair]
        require(state['flags'] == 1 and state['tick'] == str(ue.MontageNotifyTickType.QUEUED), 'State 不是Queued/NoMerge')
        native = state['native']
        expected_end = f32(f32(spec['start']) + f32(spec['end'] - spec['start']))
        require(native['time'] == f32(spec['start']) and native['duration'] == f32(expected_end - f32(spec['start'])),
                'State 原生时间不同创建参数')
    actual = Counter((x['sound'], x['time'], x['volume'], x['pitch'], x['follow'], x['attach_name']) for x in points)
    expected = Counter((sound.get_path_name(), f32(x['time_seconds']), f32(x['parameters']['volume']),
                        f32(x['parameters']['pitch']), x['parameters']['follow'], str(x['parameters']['attach_name']))
                       for x, sound in sounds)
    require(actual == expected, 'PlaySound 资产/时间/表现参数或多路数量不同作者配置')
    return dict(timeline=observed, states=states, audio=points)


def run(ue, *, skill_ids, expected_config_sha256, approved_new_packages, known_dirty,
        fx_windows, audio_events, audio_windows, acknowledged_audio_gaps, save=False):
    """Root 显式传入 FX make_plan 的 action_windows 与 Audio 的单次声事件。

    audio_events 每项为 action_id/event_id/time_seconds/sound/parameters；持续声和真命中声
    由各组的 GA 配置消费，不能作为 PlaySound 事件塞进本参数。
    """
    cfg = load_config(expected_config_sha256)
    rows = make_plan(cfg, skill_ids)
    require(set(skill_ids) <= {w['action_id'] for w in fx_windows}, 'FX 尚未给完整动作制作配置')
    audio_covered = {e['action_id'] for e in audio_events} | {w['action_id'] for w in audio_windows}
    require(set(skill_ids) <= audio_covered | set(acknowledged_audio_gaps), 'Audio 尚未交事件或明确来源缺口')
    require(not ue.EditorLevelLibrary.get_pie_worlds(True), '资产制作不能处于 PIE')
    require(dirty(ue) == known_dirty, '进入制作时 dirty 不同已准入集合')
    require(hasattr(ue.GGYGOLinearMontageAuthorLibrary, 'author_new_montage')
            and hasattr(ue.GGYGOLinearMontageAuthorLibrary, 'validate_montage'), '缺已编译原生制作接口')
    require(ue.AnimNotifyEvent().get_editor_property('montage_tick_type') == ue.MontageNotifyTickType.QUEUED,
            '原生新 State 默认不是 Queued，拒绝猜测事件构造合同')
    skeleton = load(ue, cfg['skeleton'], ue.Skeleton)
    prepared, missing = [], []
    # 整批解析原输入和标签后才创建第一个包。
    for row in rows:
        sources = [load(ue, s['derived_sequence'], ue.AnimSequence) for s in row['segments']]
        require(all(s.get_editor_property('skeleton') == skeleton
                    and not s.get_editor_property('enable_root_motion')
                    and not s.get_editor_property('force_root_lock') for s in sources), '派生骨架或双重根移无效')
        for source in sources:
            require(ue.EditorAssetLibrary.get_metadata_tag(source, 'GGYGO.MotionPoseAnchor')
                    == cfg['anim_blueprint']['idle_sequence'] + '.' + cfg['anim_blueprint']['idle_sequence'].rsplit('/', 1)[1],
                    '派生未消费本批公共姿态锚：' + source.get_path_name())
        require(all(source.get_play_length() == segment['duration_source_seconds']
                    for source, segment in zip(sources, row['segments'])), '当前原生有效域不同旧读回，须重核制作配置')
        specs = state_specs(row, fx_windows, audio_windows)
        for spec in specs:
            require(0 <= spec['start'] < spec['end'] <= sum(s.get_play_length() for s in sources), '窗口超出完整时间轴')
            spec['tags'] = (tag(ue, spec['begin']), tag(ue, spec['finish']))
        sounds = []
        for audio in audio_events:
            if audio['action_id'] == row['id']:
                require(set(audio['parameters']) == {'volume', 'pitch', 'follow', 'attach_name'}, '缺完整单次声表现参数')
                require(type(audio['time_seconds']) in (int, float)
                        and math.isfinite(audio['time_seconds'])
                        and 0 <= audio['time_seconds'] < sum(s.get_play_length() for s in sources), '单次声时间非法')
                sounds.append((audio, load(ue, audio['sound'], ue.SoundBase)))
        exists = ue.EditorAssetLibrary.does_asset_exist(row['montage'])
        montage = load(ue, row['montage'], ue.AnimMontage) if exists else None
        if not exists:
            require(row['montage'] in approved_new_packages, '未明确批准新包：' + row['montage'])
            missing.append(row['montage'])
        else:
            require(ue.EditorAssetLibrary.get_metadata_tag(montage, 'GGYGO.KevinAssemblyConfig') == expected_config_sha256,
                    '已有目标属于其它制作合同，保留原资产：' + row['montage'])
        prepared.append((row, sources, specs, sounds, montage))
    require(set(missing) == set(approved_new_packages), '批准的新包集合必须准确对应本批缺项')
    require(dirty(ue) == known_dirty, '只读准入改变 dirty；保留现场')
    report = dict(schema=OWNER, config_sha256=expected_config_sha256, saved=[], created=[], montages={},
                  production_complete=False, runtime_verified=False, visual_verified=False)
    for row, sources, specs, sounds, montage in prepared:
        sections = [s['section'] for s in row['segments']]
        if montage is None:
            factory = ue.AnimMontageFactory()
            factory.set_editor_property('source_animation', sources[0])
            package = row['montage']
            montage = ue.AssetToolsHelpers.get_asset_tools().create_asset(
                package.rsplit('/', 1)[1], package.rsplit('/', 1)[0], ue.AnimMontage, factory)
            require(montage is not None, 'Montage 工厂失败：' + package)
            report['created'].append(package)
            authored = ue.GGYGOLinearMontageAuthorLibrary.author_new_montage(montage, cfg['slot'], sources, sections)
            require(authored.get_editor_property('succeeded'), '完整源制作失败：' + authored.export_text())
            for field in ('blend_in', 'blend_out'):
                blend = montage.get_editor_property(field)
                blend.set_editor_property('blend_time', row[field + '_seconds'])
                montage.set_editor_property(field, blend)
            montage.set_editor_property('enable_auto_blend_out', True)
            montage.set_editor_property('blend_out_trigger_time', 0.)
            _append_notifies(ue, montage, specs, sounds)
            ue.EditorAssetLibrary.set_metadata_tag(montage, 'GGYGO.KevinAssemblyConfig', expected_config_sha256)
        validated = ue.GGYGOLinearMontageAuthorLibrary.validate_montage(montage, cfg['slot'], sources, sections)
        # 在断言前保留原生 Error/export_text，不能再次丢失 Cold R1 的实际失败信息。
        entry = dict(native_validation=validated.export_text())
        report['montages'][row['id']] = entry
        require(validated.get_editor_property('succeeded'), '完整线性合同失败：' + validated.export_text())
        entry.update(_read_and_verify_notifies(ue, montage, specs, sounds))
        entry['package'] = row['montage']
        entry['asset'] = montage
    if save:
        for entry in report['montages'].values():
            if entry['package'] in report['created']:
                require(ue.EditorAssetLibrary.save_loaded_asset(entry['asset'], only_if_is_dirty=False), '准确 Montage 保存失败')
                report['saved'].append(entry['package'])
    for entry in report['montages'].values():
        del entry['asset']
    report['production_complete'] = save
    return report


def prepare_presentations(ue, *, presentation_ids, expected_config_sha256, approved_existing_packages,
                          known_dirty, fx_windows, audio_events, acknowledged_audio_gaps, save=False):
    """仅追加原生制作器刚建的非位移表现窗；原曲线已结束，落地姿态不再驱动胶囊。"""
    cfg = load_config(expected_config_sha256)
    catalog = {x['id']: x for x in cfg['presentation_contracts']}
    require(presentation_ids and len(presentation_ids) == len(set(presentation_ids)), '表现选择必须明确唯一')
    rows = [catalog[key] for key in presentation_ids]
    require({row['montage'] for row in rows} == set(approved_existing_packages), '批准的表现包集合不同本批')
    require(not ue.EditorLevelLibrary.get_pie_worlds(True) and dirty(ue) == known_dirty, '表现接线准入状态不符')
    prepared = []
    for row in rows:
        require(row['movement_mode'] == 'presentation_only_no_CMC_curve_execution', '不得将表现片当位移兜底')
        montage = load(ue, row['montage'], ue.AnimMontage)
        require(ue.EditorAssetLibrary.get_metadata_tag(montage, 'GGYGO.AssetBuilder') == 'KevinCombatAssets.v2',
                '原生制作归属不符，保留原包')
        before = timeline(ue, montage)
        source = load(ue, row['source_sequence'], ue.AnimSequence)
        require(before['sections'] == [dict(section_name='Main', next_section_name='None', time=0.)]
                and len(before['segments']) == 1 and before['play_length'] == row['expected_duration_seconds'],
                '表现不是完整单 Main 原片')
        segment = before['segments'][0]
        require(segment['source'] == source.get_path_name() and segment['slot'] == cfg['slot']
                and segment['start_pos'] == segment['anim_start_time'] == 0.
                and segment['anim_end_time'] == source.get_play_length()
                and segment['anim_play_rate'] == segment['looping_count'] == 1, '表现原段被裁剪或替换')
        specs = state_specs(dict(id=row['id'], hit_windows=[]), fx_windows, [])
        for spec in specs:
            require(0 <= spec['start'] < spec['end'] <= before['play_length'], '表现窗越界')
            spec['tags'] = (tag(ue, spec['begin']), tag(ue, spec['finish']))
        sounds = []
        for audio in audio_events:
            if audio['action_id'] == row['id']:
                require(0 <= audio['time_seconds'] < before['play_length']
                        and set(audio['parameters']) == {'volume', 'pitch', 'follow', 'attach_name'}, '表现声配置不完整')
                sounds.append((audio, load(ue, audio['sound'], ue.SoundBase)))
        require(sounds or row['id'] in acknowledged_audio_gaps, '表现声尚未交付或明确缺口')
        stamp = ue.EditorAssetLibrary.get_metadata_tag(montage, 'GGYGO.KevinPresentationConfig')
        require(not stamp or stamp == expected_config_sha256, '表现包属于其他版本，保留原接线')
        if stamp:
            _read_and_verify_notifies(ue, montage, specs, sounds)
        else:
            require(not before['notifies'], '已有作者 Notify，拒绝覆盖或重复叠加')
        prepared.append((row, montage, specs, sounds, bool(stamp)))
    require(dirty(ue) == known_dirty, '表现只读准入改变 dirty')
    report = dict(schema=OWNER, scope='presentation_only', saved=[], entries={}, runtime_verified=False, visual_verified=False)
    for row, montage, specs, sounds, existing in prepared:
        if not existing:
            _append_notifies(ue, montage, specs, sounds)
            ue.EditorAssetLibrary.set_metadata_tag(montage, 'GGYGO.KevinPresentationConfig', expected_config_sha256)
        report['entries'][row['id']] = _read_and_verify_notifies(ue, montage, specs, sounds)
        if save and not existing:
            require(ue.EditorAssetLibrary.save_loaded_asset(montage, only_if_is_dirty=False), '准确表现包保存失败')
            report['saved'].append(row['montage'])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='只输出现有 Kevin 装配计划，不启动 UE')
    parser.add_argument('--skill', action='append', required=True)
    args = parser.parse_args()
    cfg = load_config(digest(CONFIG))
    print(json.dumps(make_plan(cfg, args.skill), ensure_ascii=False, indent=2))
