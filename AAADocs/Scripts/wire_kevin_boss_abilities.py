"""Kevin GA/GE 的定向制作入口；仅由统筹在标准 Editor 制作窗调用。

prepare 只创建/配置本脚本独占包，返回未保存对象；save_prepared 才逐包保存。
不启动 UE、不运行测试、不写 Montage/BT/标签，也不覆盖旧 Ice01 自动化资产。
动作组合和时点消费 Animation 的实际 Montage 配置，FX/Audio 消费原作者配方。
"""
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Ability_Config.json'
OWNER_KEY = 'GGYGO.KevinAbilities.Owner'
OWNER = 'KVB-20261105-01'


def require(condition, message):
    if not condition:
        raise RuntimeError('[KevinAbilities] ' + message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def package(class_path):
    require(class_path.startswith('/Game/') and class_path.endswith('_C') and '.' in class_path,
            '需要完整 Blueprint Class 路径: ' + class_path)
    return class_path.split('.')[0]


def planned_targets(config_path=CONFIG):
    cfg = read_json(config_path)
    require(cfg['schema'] == 'GGYGO.KevinAbilities/v1', '未知配置版本')
    require(len(cfg['initial_effects']) == 1 and cfg['persistent_abilities'] == [cfg['death']['ability']],
            '本制作配方需要一份初始化GE及一份Death持久能力')
    targets = [row['ability'] for row in cfg['templates'].values()] + cfg['initial_effects']
    targets += [row['cooldown_effect'] for row in cfg['abilities']]
    targets += [row['ability'] for row in cfg['abilities']] + cfg['persistent_abilities']
    paths = [package(path) for path in targets]
    require(len(paths) == len(set(paths)), '重复目标包')
    require(all(path.startswith(cfg['base'] + '/') for path in paths), '目标越过独占 Abilities 目录')
    return paths


def authoring_inputs(config_path=CONFIG):
    """本入口实际读取的源文件；UE加载的包/父依赖由统筹宿主另按真实集合保护。"""
    cfg = read_json(config_path)
    return [str(Path(__file__).resolve()), str(Path(config_path).resolve()),
            str(ROOT / cfg['animation_config']), str(ROOT / cfg['fx_config']), str(ROOT / cfg['audio_config']),
            str(ROOT / 'AAADocs/Scripts/build_bh3_kevin_fx.py')]


def _fx_plan(cfg):
    path = ROOT / 'AAADocs/Scripts/build_bh3_kevin_fx.py'
    module = ModuleType('kevin_fx_for_ability_authoring')
    module.__file__ = str(path)
    exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), module.__dict__)
    return module.make_plan(read_json(ROOT / cfg['fx_config']))


def tag(u, name):
    value = u.GameplayTag()
    require(value.import_text('(TagName="' + name + '")')
            and u.GameplayTagLibrary.is_gameplay_tag_valid(value)
            and str(u.GameplayTagLibrary.get_tag_name(value)) == name,
            '原作者尚未注册真实标签: ' + name)
    return value


def transform(u, location, rotation, scale=(1, 1, 1)):
    # 配方使用 Pitch/Yaw/Roll；Python NativeMakeFunc 的位置参数却是 Roll/Pitch/Yaw。
    return u.Transform(u.Vector(*location),
                       u.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]), u.Vector(*scale))


def struct(u, name, fields):
    value = getattr(u, name)()
    # EditDefaultsOnly 结构字段不允许 Python 临时实例逐字段 setter；原生文本导入组装值，
    # 再由所属蓝图 CDO 保存，并走下面的编译后读回和原生能力校验。
    def text(field):
        if field is None:
            return 'None'
        if isinstance(field, u.Object):
            return '"' + field.get_path_name() + '"'
        if hasattr(field, 'export_text'):
            return field.export_text()
        if isinstance(field, u.EnumBase):
            return str(field.value)
        if isinstance(field, bool):
            return 'True' if field else 'False'
        if isinstance(field, (int, float)):
            return repr(field)
        if isinstance(field, (list, tuple, u.Array)):
            return '(' + ','.join(text(item) for item in field) + ')'
        return json.dumps(str(field), ensure_ascii=False)
    require(value.import_text('(' + ','.join(key + '=' + text(field) for key, field in fields.items()) + ')'),
            '原生结构导入失败: ' + name)
    return value


def window_pair(u, begin, end):
    return struct(u, 'GGYGOBossWindowTags', {'Begin': tag(u, begin), 'End': tag(u, end)})


def canonical(value):
    import unreal

    if value is None:
        return None
    if isinstance(value, unreal.Transform):
        # Rotator 转 Quaternion 的 -0 与序列化后的 +0 数值相同，不比较文本符号。
        return (tuple(getattr(value.translation, axis) for axis in ('x', 'y', 'z')),
                tuple(getattr(value.rotation, axis) for axis in ('x', 'y', 'z', 'w')),
                tuple(getattr(value.scale3d, axis) for axis in ('x', 'y', 'z')))
    if hasattr(value, 'get_path_name'):
        return value.get_path_name()
    if hasattr(value, 'export_text'):
        return value.export_text()
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, 'items'):
        return sorted((str(canonical(k)), canonical(v)) for k, v in value.items())
    try:
        return [canonical(v) for v in value]
    except TypeError:
        return str(value)


def _successful(result, field):
    # 使用显式结果结构保留Native诊断；不猜bool+OutError的Python打包形态。
    require(result.get_editor_property('bSucceeded') is True,
            field + ' 失败: ' + result.get_editor_property('Error'))


def playback_value(u, win, load):
    units = [struct(u, 'GGYGONiagaraEffectUnit', {'System': load(unit['system']),
             'FieldSettings': struct(u, 'GGYGOFXFieldSettings', {'Mode': u.GGYGOFXFieldMode.NO_CUSTOM_FIELD})})
             for unit in win['system_units']]
    trs = win['local_transform']
    return struct(u, 'GGYGOComboStepFX', {'Mode': u.GGYGOComboFXMode.MONTAGE_WINDOW,
        'System': None, 'SystemUnits': units, 'BeginEventTag': tag(u, win['begin_event_tag']),
        'EndEventTag': tag(u, win['end_event_tag']), 'SocketName': win['socket_name'],
        'Space': getattr(u.GGYGONiagaraEffectSpace, win['space'].upper()),
        'LocalTransform': transform(u, trs['translation'], trs['rotation_degrees'], trs['scale']),
        'NormalStopMode': getattr(u.GGYGONiagaraEffectStopMode, _enum_name(win['normal_stop_mode'])),
        'AbortStopMode': getattr(u.GGYGONiagaraEffectStopMode, _enum_name(win['abort_stop_mode'])),
        'RemoteSeekDeltaSeconds': win['remote_seek_delta_seconds'],
        'RemoteMaxSimTimeSeconds': win['remote_max_sim_time_seconds']})


def prepare(u, config_path=CONFIG, readback=False, update_properties=()):
    """预检依赖与 dirty，配置 GA/GE；可显式更新既有子类的指定 CDO 属性，不改其图、不保存。"""
    require(not (readback and update_properties), '只读核对不可同时更新已有属性')
    cfg = read_json(config_path)
    targets = planned_targets(config_path)
    eal = u.EditorAssetLibrary
    tools = u.AssetToolsHelpers.get_asset_tools()
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    require(not dirty.intersection(targets), '目标包含用户未保存修改: ' + repr(sorted(dirty.intersection(targets))))
    require(not u.EditorLevelLibrary.get_pie_worlds(True), 'PIE 中禁止制作')
    animation = read_json(ROOT / cfg['animation_config'])
    assemblies = {row['id']: row for row in animation['skill_assemblies']}
    audio = read_json(ROOT / cfg['audio_config'])
    audio_actions = {row['action_id']: row for row in audio['actions']}
    ability_rows = {row['key']: row for row in cfg['abilities']}
    fx = _fx_plan(cfg)
    objects = {}
    expected = {}
    effect_paths = set()
    created = set()
    updated = set()

    def load(path):
        obj = eal.load_asset(path)
        require(obj is not None, '缺少真实资产: ' + path)
        return obj

    def load_class(path):
        cls = u.load_class(None, path)
        require(cls is not None, '缺少真实 Class: ' + path)
        return cls

    def blueprint(class_path, parent_path, abstract=False):
        path = package(class_path)
        parent = load_class(parent_path)
        if eal.does_asset_exist(path):
            bp = load(path)
            require(isinstance(bp, u.Blueprint), '目标不是 Blueprint: ' + path)
            require(eal.get_metadata_tag(bp, OWNER_KEY) == OWNER, '拒绝未知资产: ' + path)
            require(bp.get_blueprint_parent_class() == parent, '拒绝改变已有父类: ' + path)
        else:
            require(not readback, '目标尚未制作: ' + path)
            factory = u.BlueprintFactory()
            factory.set_editor_property('ParentClass', parent)
            bp = tools.create_asset(path.rsplit('/', 1)[1], path.rsplit('/', 1)[0], u.Blueprint, factory)
            require(bp is not None, '创建 Blueprint 失败: ' + path)
            eal.set_metadata_tag(bp, OWNER_KEY, OWNER)
            created.add(path)
            bp.set_editor_property('bGenerateAbstractClass', abstract)
        require(bp.get_editor_property('bGenerateAbstractClass') == abstract, 'Blueprint抽象标志不匹配: ' + path)
        if path not in created:
            require(bp.get_editor_property('Status') == u.BlueprintStatus.BS_UP_TO_DATE, '已有Blueprint未干净编译: ' + path)
        require(bp.generated_class() is not None, '缺少生成类: ' + path)
        objects[path] = bp
        return bp, u.get_default_object(bp.generated_class())

    def values(bp, cdo, fields):
        path = bp.get_path_name().split('.')[0]
        expected[path] = fields
        for name, value in fields.items():
            if readback or path not in created:
                if canonical(cdo.get_editor_property(name)) != canonical(value):
                    require(not readback and name in update_properties,
                            '实际 CDO 不匹配: ' + path + '.' + name)
                    cdo.set_editor_property(name, value)
                    updated.add(path)
            else:
                cdo.set_editor_property(name, value)

    # 三份共享可编辑流程图；具体动作与死亡子BP只填CDO，避免逐招复制图。
    template_paths = set()
    for role, recipe in cfg['templates'].items():
        bp, _ = blueprint(recipe['ability'], recipe['native_parent'], abstract=True)
        existing = readback or package(recipe['ability']) not in created
        if role == 'death':
            operation = (u.GGYGOBossAbilityGraphLibrary.validate_death_graph if existing
                         else u.GGYGOBossAbilityGraphLibrary.build_death_graph)
            _successful(operation(bp), '共享死亡图')
        else:
            operation = (u.GGYGOBossAbilityGraphLibrary.validate_action_graph if existing
                         else u.GGYGOBossAbilityGraphLibrary.build_action_graph)
            _successful(operation(bp, role == 'flight'), '共享动作图: ' + role)
        if not existing:
            u.BlueprintEditorLibrary.compile_blueprint(bp)
        require(bp.get_editor_property('Status') == u.BlueprintStatus.BS_UP_TO_DATE, '共享图编译状态无效')
        template_paths.add(package(recipe['ability']))

    # GE 中保存实际 Attribute/Modifier/时长/授予Tag，可直接在编辑器修改。
    initial_bp, initial_cdo = blueprint(cfg['initial_effects'][0], '/Script/GameplayAbilities.GameplayEffect')
    initial = cfg['initial_attributes']
    if not readback and package(cfg['initial_effects'][0]) in created:
        _successful(u.GGYGOBossAbilityAssetConfiguration.configure_initial_attributes(initial_cdo,
                    initial['max_health'], initial['health'], initial['max_poise'], initial['poise']), '初始化GE制作')
        u.BlueprintEditorLibrary.compile_blueprint(initial_bp)
        initial_cdo = u.get_default_object(initial_bp.generated_class())
    effect_paths.add(package(cfg['initial_effects'][0]))
    _successful(u.GGYGOBossAbilityAssetConfiguration.validate_initial_attributes(initial_cdo,
                initial['max_health'], initial['health'], initial['max_poise'], initial['poise']), '初始化GE实际读回')

    for row in cfg['abilities']:
        require(type(row['enabled']) is bool and type(row['entrypoint']) is bool, '启用/入口必须显式bool')
        skill = assemblies.get(row['animation_id'])
        require(skill is not None, '缺少Animation实际技能配置: ' + row['animation_id'])
        montage = load(skill['montage'])
        cooldown_bp, cooldown_cdo = blueprint(row['cooldown_effect'], '/Script/GameplayAbilities.GameplayEffect')
        if not readback and package(row['cooldown_effect']) in created:
            _successful(u.GGYGOBossAbilityAssetConfiguration.configure_cooldown(
                        cooldown_cdo, row['cooldown_seconds'], tag(u, row['cooldown_tag'])), '冷却GE制作')
            u.BlueprintEditorLibrary.compile_blueprint(cooldown_bp)
            cooldown_cdo = u.get_default_object(cooldown_bp.generated_class())
        effect_paths.add(package(row['cooldown_effect']))
        _successful(u.GGYGOBossAbilityAssetConfiguration.validate_cooldown(
                    cooldown_cdo, row['cooldown_seconds'], tag(u, row['cooldown_tag'])), '冷却GE实际读回')
        flow = row['flow']
        parent = cfg['templates']['flight' if flow['flight_landing'] else 'ground']['ability']
        bp, cdo = blueprint(row['ability'], parent)
        recovery = load(animation['landing_presentation_montage']) if flow['flight_landing'] else None
        if recovery is not None:
            contract = next(c for c in animation['presentation_contracts'] if c['id'] == 'LandingRecovery')
            require(contract['movement_mode'] == 'presentation_only_no_CMC_curve_execution'
                    and contract['trigger'] == 'real_landed_only', '必须消费明确的真实落地纯姿态合同')
            _successful(u.GGYGOBossAbilityAssetConfiguration.validate_recovery_montage(recovery, animation['slot']), '实际纯姿态收尾')
        mode = skill['damage_mode']
        mode_enum = {'melee': u.GGYGOBossHitMode.MELEE, 'area': u.GGYGOBossHitMode.AREA_SPHERE,
                     'projectile': u.GGYGOBossHitMode.PROJECTILE, 'none': u.GGYGOBossHitMode.NONE,
                     'per_window': u.GGYGOBossHitMode.NONE}
        require(mode in mode_enum, '缺少明确查询模式: ' + row['key'])
        hit_windows = [window_pair(u, win['begin_event_tag'], win['end_event_tag']) for win in skill['hit_windows']]
        execution = u.Map(u.GameplayTag, u.GGYGOBossWindowExecution)
        if mode == 'per_window':
            for win in skill['hit_windows']:
                source = ability_rows[win['source_action_id']]
                execution[tag(u, win['begin_event_tag'])] = struct(u, 'GGYGOBossWindowExecution', {
                    'Mode': mode_enum[win['damage_mode']], 'Damage': source['damage'], 'PoiseDamage': source['poise_damage'],
                    'HitCueTag': tag(u, win['hit_cue_tag'])})
        windows = [win for win in fx['action_windows'] if win['action_id'] == row['animation_id']]
        require(windows, '攻击尚未配置真实 FX 作者窗: ' + row['key'])
        playback = [playback_value(u, win, load) for win in windows]
        persistent = []
        for sound in audio['owned_audio']:
            if sound['action_id'] != row['animation_id']:
                continue
            sound = sound['persistent_audio']
            persistent.append(struct(u, 'GGYGOBossAudioWindow', {'Events': window_pair(u, sound['begin_tag'], sound['end_tag']),
                'Sound': load(sound['sound']), 'Socket': sound['socket'],
                'RelativeTransform': transform(u, sound['relative_location'], sound['relative_rotation']),
                'Volume': sound['volume'], 'Pitch': sound['pitch']}))
        require(persistent or not row['require_persistent_audio'], '必需持续声尚未合入原作者配置: ' + row['key'])
        fields = {'AttackMontage': montage, 'MontagePlayRate': skill['play_rate'],
                  'bUseMontageSourceMotion': True, 'ActionMotionProfile': None,
                  'MotionSlot': animation['slot'], 'MotionSection': skill['main_section'],
                  'MotionEndSection': skill['motion_end_section'], 'MotionTranslationScale': 1.0,
                  'ActionTag': tag(u, row['action_tag']), 'DamageEffect': load_class(cfg['damage_effect']),
                  'CooldownGameplayEffectClass': cooldown_bp.generated_class(), 'Damage': row['damage'],
                  'PoiseDamage': row['poise_damage'], 'HitMode': mode_enum[mode],
                  'TraceStartSocket': cfg['trace']['start_socket'], 'TraceEndSocket': cfg['trace']['end_socket'],
                  'TraceRadius': cfg['trace']['radius'], 'HitWindowTags': hit_windows,
                  'WindowExecution': execution,
                  'MontageFXWindows': playback, 'PersistentAudio': persistent,
                  'HitCueTag': u.GameplayTag() if mode in ('per_window', 'none') else
                      tag(u, fx['hit_cues'][audio_actions[row['key']]['hit_cue_key']]['tag'])}
        if flow['flight_landing']:
            recovery_windows = [win for win in fx['action_windows'] if win['action_id'] == 'LandingRecovery']
            require(len(recovery_windows) == 1, '纯姿态收尾必须消费唯一实际Impact表现窗')
            fields.update({'LandingTimeoutSeconds': flow['landing_timeout_seconds'], 'LandingRecoveryMontage': recovery,
                           'RecoveryPlayRate': flow['recovery_play_rate'], 'RecoveryFX': playback_value(u, recovery_windows[0], load)})
        if mode == 'area' or 'area_ref' in row:
            area = cfg['area'][row.get('area_ref', row['key'])]
            fields.update({'AreaOffset': u.Vector(*area['offset']), 'AreaRadius': area['radius']})
        if mode == 'projectile' or 'projectile_visual_ref' in row:
            projectile = cfg['projectile']
            visual = fx['projectile_visuals'][row['projectile_visual_ref']]
            visual_trs = visual['local_transform']
            fields.update({'ProjectileSocket': projectile['socket'], 'ProjectileOffset': u.Vector(*projectile['offset']),
                           'ProjectileRadius': projectile['radius'], 'ProjectileSpeed': projectile['speed'],
                           'ProjectileLifetime': projectile['lifetime'], 'ProjectileGravity': projectile['gravity'],
                           'ProjectileSystem': load(visual['system']),
                           'ProjectileVisualTransform': transform(u, visual_trs['translation'], visual_trs['rotation_degrees'], visual_trs['scale'])})
        values(bp, cdo, fields)

    death_bp, death_cdo = blueprint(cfg['death']['ability'], cfg['templates']['death']['ability'])
    sequence = load(animation['presentation_sequences'][cfg['death']['presentation_sequence_key']])
    duration = float(sequence.get_play_length())
    require(duration > 0.0, '实际死亡片段时长无效')
    values(death_bp, death_cdo, {'PresentationSeconds': duration})
    if not readback:
        for path, bp in objects.items():
            if path in effect_paths or path in template_paths or path not in created | updated:
                continue
            u.BlueprintEditorLibrary.compile_blueprint(bp)
            require(bp.get_editor_property('Status') == u.BlueprintStatus.BS_UP_TO_DATE,
                    'Blueprint编译失败或含警告: ' + bp.get_path_name())
        for path, fields in expected.items():
            cdo = u.get_default_object(objects[path].generated_class())
            for name, value in fields.items():
                require(canonical(cdo.get_editor_property(name)) == canonical(value),
                        '编译后CDO不匹配: ' + path + '.' + name +
                        ' actual=' + repr(canonical(cdo.get_editor_property(name))) + ' expected=' + repr(canonical(value)))
    for row in cfg['abilities']:
        cdo = u.get_default_object(objects[package(row['ability'])].generated_class())
        _successful(u.GGYGOBossAbilityAssetConfiguration.validate_ability(cdo), '原生能力配置实际校验: ' + row['key'])
    return {'objects': objects, 'expected': expected, 'targets': targets,
            'created_packages': [path for path in targets if path in created],
            'updated_packages': [path for path in targets if path in updated],
            'asset_configuration_only': True, 'runtime_or_visual_verified': False}


def _enum_name(value):
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', '_', value).upper()


def save_prepared(u, prepared):
    """仅保存 prepare 实际返回的独占包；原生保存失败保留现场。"""
    saved = []
    require(not u.EditorLevelLibrary.get_pie_worlds(True), 'PIE中禁止保存')
    for path in prepared['created_packages'] + prepared['updated_packages']:
        bp = prepared['objects'][path]
        require(u.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False), '单包保存失败: ' + path)
        saved.append(path)
    return saved
