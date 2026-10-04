"""创建隔离的 Kevin 战斗资产；没有 --apply 时仅预检，不改 UE。

依赖动画 builder 的 ABP/DefaultSlot、Montage/人工窗口/Socket，及 Movement 的 MotionProfile。
不修改关卡、旧 Boss Test、Pyrios；既有资产只读核验并保留用户调参。
运行：py "F:/ue_project/GGYGO/AAADocs/Scripts/wire_bh3_kevin_combat.py" --apply
配置中的伤害、范围、胶囊、朝向均是人工暂定值，不是原游戏数据。
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Wiring_Config.json'
MONTAGES = ROOT / 'AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Montage_Config.json'
OWNER = 'GGYGO.KevinCombat.Wiring.v1'
OWNER_KEY = 'GGYGO.KevinCombat.Owner'


def read_config():
    config = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    assert config['base'].startswith('/Game/Characters/Boss/Kevin/DemonBattle/')
    assert len({row['action_tag'] for row in config['actions']}) == len(config['actions']), '动作 Tag 必须唯一'
    assert len({row['ability'] for row in config['actions']}) == len(config['actions']), '能力资产名必须唯一'
    return config


def run(apply=False):
    import unreal
    cfg = read_config()
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    records = []
    differences = []

    def load(path):
        asset = unreal.load_object(None, path) if '.' in path else unreal.load_asset(path)
        assert asset, '缺少依赖：' + path
        return asset

    def tag(name):
        value = unreal.GameplayTag()
        value.import_text('(TagName="%s")' % name)
        assert str(value.get_editor_property('TagName')) == name, 'GameplayTag 尚未登记：' + name
        return value

    def struct(kind, **fields):
        value = kind()
        for key, item in fields.items():
            value.set_editor_property(key, item)
        return value

    def create(name, cls=None, parent=None):
        path = cfg['base'] + '/' + name
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            asset = load(path)
            assert unreal.EditorAssetLibrary.get_metadata_tag(asset, OWNER_KEY) == OWNER, '拒绝覆盖未知资产：' + path
            records.append({'path': path, 'status': 'existing_owned_asset_preserved'})
            return asset, False
        if not apply:
            records.append({'path': path, 'status': 'missing_not_created'})
            return None, False
        if parent:
            factory = unreal.BlueprintFactory()
            factory.set_editor_property('parent_class', parent)
            asset_cls = unreal.Blueprint
        else:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property('data_asset_class', cls)
            asset_cls = cls
        asset = tools.create_asset(name, cfg['base'], asset_cls, factory)
        assert asset, '创建失败：' + path
        unreal.EditorAssetLibrary.set_metadata_tag(asset, OWNER_KEY, OWNER)
        unreal.EditorAssetLibrary.set_metadata_tag(asset, 'GGYGO.KevinCombat.Tuning', 'manual_provisional_not_source_gameplay')
        records.append({'path': path, 'status': 'created'})
        return asset, True

    def save(asset, blueprint=False):
        if blueprint:
            unreal.BlueprintEditorLibrary.compile_blueprint(asset)
        assert unreal.EditorAssetLibrary.save_loaded_asset(asset), '保存失败：' + asset.get_path_name()

    def cdo(blueprint):
        return unreal.get_default_object(blueprint.generated_class())

    def comparable(value):
        if isinstance(value, unreal.Object):
            return value.get_path_name()
        if hasattr(value, 'export_text'):
            return value.export_text()
        if isinstance(value, (list, tuple, unreal.Array)):
            return [comparable(item) for item in value]
        return value

    def configure(asset, values, fresh):
        if asset is None:
            return
        for key, expected in values.items():
            if fresh:
                asset.set_editor_property(key, expected)
            else:
                actual = asset.get_editor_property(key)
                if comparable(actual) != comparable(expected):
                    differences.append({'asset': asset.get_path_name(), 'property': key,
                        'actual': str(comparable(actual)), 'configured': str(comparable(expected)),
                        'action': 'preserved'})

    def linked_time(event):
        # 首版 builder 使用 Absolute 链接；相对/比例链接必须先显式支持再接线。
        assert event.get_editor_property('LinkMethod') == unreal.AnimLinkMethod.ABSOLUTE, '仅支持 Absolute Notify 时间'
        return float(event.get_editor_property('LinkValue'))

    # 先完成依赖预检，避免缺一项仍写出半套玩法资产。
    mesh = load(cfg['mesh'])
    abp = load(cfg['anim_blueprint'])
    abp_class = abp.generated_class()
    assert abp_class, 'ABP 尚未编译'
    damage_effect = load(cfg['damage_effect'])
    expected_skeleton = mesh.get_editor_property('skeleton')
    assert abp.get_editor_property('TargetSkeleton') == expected_skeleton, 'ABP 骨架不匹配'
    montage_cfg = json.loads(MONTAGES.read_text(encoding='utf-8-sig'))
    for socket_name in (cfg['trace_start_socket'], cfg['trace_end_socket']):
        socket = mesh.find_socket(socket_name)
        assert socket, 'Mesh/Skeleton 缺少 Socket：' + socket_name
        assert str(socket.get_editor_property('BoneName')) == montage_cfg['socket_config']['parent_bone'], 'Socket 武器骨不匹配'
    manifest = {row['source_clip']: row for row in montage_cfg['actions']}
    dependencies = {}
    for row in cfg['actions']:
        spec = manifest[row['source_clip']]
        assert spec['damage_enabled'] and spec['hit_windows'], '命中窗口尚未标定：' + row['id']
        assert spec['sequence_override'], '需要派生原地动画：' + row['id']
        montage = load(row['montage'])
        assert montage.get_editor_property('skeleton') == expected_skeleton, 'Montage 骨架不匹配'
        slots = montage.get_editor_property('SlotAnimTracks')
        assert len(slots) == 1 and str(slots[0].get_editor_property('SlotName')) == montage_cfg['slot'], 'Montage Slot 不匹配'
        segments = slots[0].get_editor_property('AnimTrack').get_editor_property('AnimSegments')
        assert len(segments) == 1, '首版仅支持单段线性 Montage'
        sequence = load(spec['sequence_override'])
        segment = segments[0]
        assert segment.get_editor_property('AnimReference') == sequence, '实际 Montage 未引用派生原地动画'
        assert not sequence.get_editor_property('bEnableRootMotion'), '派生动画不得启用原生 RootMotion'
        assert segment.get_editor_property('LoopingCount') == 1, '首版不支持循环段'
        assert abs(float(segment.get_editor_property('AnimPlayRate')) - 1.0) < 0.0001, '段内变速尚未支持'
        length = float(montage.get_editor_property('SequenceLength'))
        assert abs(float(segment.get_editor_property('StartPos'))) < 0.0001, '段必须从零开始'
        assert abs(float(segment.get_editor_property('AnimStartTime'))) < 0.0001, '不支持裁剪后的动作起点'
        assert abs(float(segment.get_editor_property('AnimEndTime')) - length) <= 0.001, '段必须覆盖完整轨迹'
        sections = montage.get_editor_property('CompositeSections')
        assert len(sections) == 1 and str(sections[0].get_editor_property('NextSectionName')) == 'None', '首版仅支持单 Section 自然结束'
        assert montage.get_editor_property('bEnableAutoBlendOut'), '必须启用自动混出'
        profile = load(row['motion_profile'])
        duration = float(profile.get_editor_property('Duration'))
        assert math.isfinite(length) and length > 0 and abs(duration - length) <= 0.001, 'Profile/Montage 时长不匹配'
        assert profile.get_editor_property('TranslationCurve'), 'Profile 缺少位移曲线'
        actual_windows = []
        for event in unreal.AnimationLibrary.get_animation_notify_events(montage):
            state = event.get_editor_property('NotifyStateClass')
            if not isinstance(state, unreal.GGYGOAnimNotifyState_GameplayEventWindow):
                continue
            begin = str(state.get_editor_property('BeginEventTag').get_editor_property('TagName'))
            end = str(state.get_editor_property('EndEventTag').get_editor_property('TagName'))
            if begin == 'Event.Montage.HitWindowBegin' and end == 'Event.Montage.HitWindowEnd':
                start = linked_time(event)
                actual_windows.append((start, start + float(event.get_editor_property('Duration'))))
        actual_windows.sort()
        expected_windows = sorted((window['start_frame'] / spec['frame_rate'], window['end_frame'] / spec['frame_rate'])
                                  for window in spec['hit_windows'])
        assert len(actual_windows) == len(expected_windows), '实际 Notify 窗口数量不匹配'
        for index, (actual, expected) in enumerate(zip(actual_windows, expected_windows)):
            assert all(abs(a - b) <= 0.001 for a, b in zip(actual, expected)), '实际 Notify 时间与标定不匹配'
            assert 0 <= actual[0] < actual[1] <= length, 'Notify 窗口越界'
            assert index == 0 or actual_windows[index - 1][1] < actual[0], '窗口必须分离，避免同帧 End/Begin 顺序歧义'
        dependencies[row['id']] = (montage, profile, tag(row['action_tag']))
    form_tag, phase_tag, cue_tag = tag(cfg['form_tag']), tag(cfg['phase_tag']), tag(cfg['hit_cue'])
    behavior_tree = load(cfg['behavior_tree']) if cfg['behavior_tree'] else None
    names = [row['ability'] for row in cfg['actions']] + ['DA_AbilitySet_Kevin_DemonBattle',
        'BP_Kevin_DemonBattle', 'DA_Pawn_Kevin_DemonBattle', 'DA_ActionSet_Kevin_DemonBattle', 'DA_Boss_Kevin_DemonBattle']
    for name in names:
        path = cfg['base'] + '/' + name
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            assert unreal.EditorAssetLibrary.get_metadata_tag(load(path), OWNER_KEY) == OWNER, '拒绝覆盖未知资产：' + path
    ability_blueprints = []
    action_defs = []
    for row in cfg['actions']:
        montage, profile, action_tag = dependencies[row['id']]
        bp, fresh = create(row['ability'], parent=unreal.GGYGOBossMeleeAbility)
        if bp is None:
            continue
        default = cdo(bp)
        values = {'AttackMontage': montage, 'DamageEffect': damage_effect, 'ActionTag': action_tag,
                      'HitCueTag': cue_tag, 'Damage': row['damage'], 'PoiseDamage': row['poise_damage'],
                      'TraceStartSocket': cfg['trace_start_socket'], 'TraceEndSocket': cfg['trace_end_socket'],
                      'TraceRadius': row['trace_radius'], 'MontagePlayRate': row['play_rate'],
                      'ActionMotionProfile': profile}
        configure(default, values, fresh)
        if fresh:
            save(bp, True)
        ability_blueprints.append(bp)
        action_defs.append(struct(unreal.GGYGOBossActionDefinition, ActionTag=action_tag,
            AbilityClass=bp.generated_class(), BaseWeight=row['base_weight'], MinDistance=row['min_distance'],
            MaxDistance=row['max_distance'], MaxFacingAngle=row['max_facing_angle'],
            RepeatPenalty=row['repeat_penalty']))

    ability_set, fresh = create('DA_AbilitySet_Kevin_DemonBattle', cls=unreal.GGYGOAbilitySet)
    if len(ability_blueprints) == len(cfg['actions']):
        configure(ability_set, {'GrantedGameplayAbilities': [
            struct(unreal.GGYGOAbilitySet_GameplayAbility, Ability=bp.generated_class(), AbilityLevel=1)
            for bp in ability_blueprints]}, fresh)
    if fresh:
        save(ability_set)

    pawn_bp, fresh = create('BP_Kevin_DemonBattle', parent=unreal.GGYGOBossCharacter)
    default = cdo(pawn_bp) if pawn_bp else None
    mesh_component = default.get_editor_property('Mesh') if default else None
    if pawn_bp and not fresh:
        configure(mesh_component, {'SkeletalMesh': mesh, 'AnimClass': abp_class,
            'RelativeLocation': unreal.Vector(*cfg['mesh_relative_location']),
            'RelativeRotation': unreal.Rotator(*cfg['mesh_relative_rotation'])}, False)
        configure(default.get_editor_property('CapsuleComponent'), {'CapsuleRadius': cfg['capsule_radius'],
            'CapsuleHalfHeight': cfg['capsule_half_height']}, False)
    if fresh:
        default = cdo(pawn_bp)
        mesh_component = default.get_editor_property('Mesh')
        mesh_component.set_skeletal_mesh_asset(mesh)
        mesh_component.set_anim_instance_class(abp_class)
        mesh_component.set_editor_property('RelativeLocation', unreal.Vector(*cfg['mesh_relative_location']))
        mesh_component.set_editor_property('RelativeRotation', unreal.Rotator(*cfg['mesh_relative_rotation']))
        default.get_editor_property('CapsuleComponent').set_capsule_size(cfg['capsule_radius'], cfg['capsule_half_height'])
        save(pawn_bp, True)

    pawn_data, fresh = create('DA_Pawn_Kevin_DemonBattle', cls=unreal.GGYGOPawnData)
    if pawn_bp and ability_set:
        configure(pawn_data, {'PawnClass': pawn_bp.generated_class(), 'AbilitySets': [ability_set]}, fresh)
    if fresh:
        save(pawn_data)

    action_set, fresh = create('DA_ActionSet_Kevin_DemonBattle', cls=unreal.GGYGOBossActionSet)
    if len(ability_blueprints) == len(cfg['actions']):
        configure(action_set, {'Actions': action_defs}, fresh)
    if fresh:
        save(action_set)

    definition, fresh = create('DA_Boss_Kevin_DemonBattle', cls=unreal.GGYGOBossDefinition)
    configure(definition, {'InitialFormTag': form_tag, 'InitialPhaseTag': phase_tag,
        'BehaviorTree': behavior_tree}, fresh)
    if pawn_data and action_set:
        configure(definition, {
            'Forms': [struct(unreal.GGYGOBossFormDefinition, FormTag=form_tag, AvatarPawnData=pawn_data)],
            'Phases': [struct(unreal.GGYGOBossPhaseDefinition, PhaseTag=phase_tag, EnterHealthThreshold=1.0, ActionSet=action_set)]}, fresh)
    if fresh:
        save(definition)

    report = {'status': 'created_requires_readback_and_runtime_validation' if apply else 'preflight_passed_no_mutation', 'assets': records,
              'definition': definition.get_path_name() if definition else None, 'behavior_tree_bound': bool(behavior_tree),
              'existing_asset_differences': differences, 'automatic_action_selection_verified': False,
              'tuning': 'manual_provisional', 'level_modified': False}
    if apply:
        out = ROOT / 'Saved/Codex/bh3_kevin_combat_wiring.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('KEVIN_COMBAT_WIRING ' + json.dumps(report, ensure_ascii=False))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    run(args.apply)
