"""@file configure_pyrios_normal03_phases.py
@brief 将第三段普攻后半段的时序写回既有 Niagara 资产。

运行在自有 Editor：apply(ue, output_dir)。阶段值成为 Niagara User Float，
Emitter State 在阶段起点之后再执行源内部 Delay，源 System.Age 曲线使用
阶段局部时间。粒子 Age／NormalizedAge、Burst 相对时间、材质和几何不变。
工具只制作资产，不在游戏中运行；Montage 与 GA 保持现有调用入口。
"""
import gzip
import json
import math
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'AAADocs/Assets/Pyrios/FX/Pyrios_Normal03_Phases.json'
NS = 'NiagaraToolsets.NiagaraToolset_System.'
COMPILE = 'GGYGOEditor.GGYGONiagaraCompileLibrary.'
STAGES = ('EmitterSpawnScript', 'EmitterUpdateScript', 'ParticleSpawnScript', 'ParticleUpdateScript')
HLSL = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'


def require(ok, reason):
    if not ok:
        raise RuntimeError('Normal03.Phases: ' + reason)


def number(kind, value):
    return {'struct': {'refPath': '/Script/Niagara.Niagara' + kind}, 'value': {'value': value}}


def expression(value):
    return {'struct': {'refPath': HLSL}, 'value': {'hlslExpression': value}}


def phase_parameter(phase):
    return 'User.Normal03_' + phase['member'] + '_StartSeconds'


def load_configuration():
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    phases = {row['prefix']: row for row in config['phases']}
    require(len(phases) == len(config['phases']), '阶段前缀重复')
    require(all(math.isfinite(row['start_seconds']) and 0 < row['start_seconds'] < config['main_seconds']
                for row in phases.values()), '阶段时点越出 Main')
    source = json.loads(gzip.decompress((ROOT / config['reference']['source_preparation']).read_bytes()))
    specs = {}
    for ordinal, (prefab, member) in enumerate(source['actions']['Normal03']['members'].items()):
        prefix = 'M%02d_' % ordinal
        if prefix not in phases:
            continue
        require(prefab == 'Eff_Pyrois_Attack_Normal_03_' + phases[prefix]['member'], '源组合前缀不匹配')
        for spec in member['plan']['specs']:
            require(spec.get('source_mode') != 'Emitter' and not spec.get('particle_trail_child')
                    and spec['loop'] is False, '本次阶段修复要求独立单次粒子发射器')
            # NiagaraBuilder.lower_native_emitter_specs 对正式组合统一追加该后缀。
            specs[prefix + spec['name'] + '_UEFX'] = spec
    return config, phases, specs


def emitter_changes(ref, rows, phase, source_spec):
    """只变更已读回的 Delay 和阶段局部年龄表达式；保留其余当前参数。"""
    update = rows['EmitterUpdateScript']
    states = [m for m in update if m['moduleName'] == 'EmitterState']
    require(len(states) == 1, '缺少唯一 Emitter State: ' + ref['emitterName'])
    inputs = {x['name']: x['value'] for x in states[0]['inputs']}
    require(inputs['Life Cycle Mode']['value']['displayName'] == 'Self'
            and inputs['Loop Behavior']['value']['displayName'] == 'Once', '生命周期不是 Self / Once')
    parameter = phase_parameter(phase)
    delay = expression(format(float(source_spec['delay']), '.17g') + ' + ' + parameter)
    changes = []

    def add(stage, module, name, before, after):
        if before != after:
            changes.append({'ref': dict(ref, scriptName=stage, moduleName=module, inputNameStack=[name]),
                            'before': before, 'after': after})

    # 已制作的参数允许再次只读；其它 Delay 改动必须显式核对，不能重复叠加。
    old_delay = inputs['Loop Delay']
    old_enabled = inputs['UseLoopDelay']
    already = old_delay == delay
    if not already:
        require(old_delay['struct']['refPath'] == '/Script/Niagara.NiagaraFloat', '源 Delay 已改为其它表达式')
        effective_delay = old_delay['value']['value'] if old_enabled['value']['value'] else 0.0
        require(abs(effective_delay - source_spec['delay']) < 1e-6, '当前 Delay 偏离已导出来源')
    add('EmitterUpdateScript', 'EmitterState', 'UseLoopDelay', old_enabled, number('Bool', -1))
    add('EmitterUpdateScript', 'EmitterState', 'Loop Delay', old_delay, delay)
    shifted = 'max(0.0, System.Age - ' + parameter + ')'
    for stage, modules in rows.items():
        for module in modules:
            for item in module['inputs']:
                value = item['value']
                if value.get('struct', {}).get('refPath') != HLSL:
                    continue
                hlsl = value['value']['hlslExpression']
                if 'System.Age' not in hlsl:
                    continue
                if parameter in hlsl:
                    require(already, '仅局部完成过阶段改写，须先检查未保存图')
                    continue
                require(not already, 'Delay 已偏移但仍有未偏移的源 System.Age')
                after = re.sub(r'\bSystem\.Age\b', shifted, hlsl)
                add(stage, module['moduleName'], item['name'], value, expression(after))
    return changes


def apply(ue, output_dir):
    """同一 Editor 内逐系统写入、编译和精确保存；失败保留报告与原包备份。"""
    from zzz_fx_niagara_ue import NiagaraBuilder

    config, phases, specs = load_configuration()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)
    report = {'configuration': str(CONFIG), 'systems': [], 'success': False, 'visual_verified': False}

    def call(full_name, **args):
        toolset, name = full_name.rsplit('.', 1)
        result = ue.ToolsetRegistry.execute_tool(toolset, name, json.dumps(args))
        require(result.get_editor_property('is_complete'), '工具仍在执行: ' + full_name)
        require(not result.get_editor_property('error'), str(result.get_editor_property('error')))
        return json.loads(result.get_editor_property('value'))['returnValue']

    def dirty():
        return {p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}

    initial_dirty = dirty()
    require(not (initial_dirty & set(config['systems'])), '目标 Niagara 有未保存工作')
    require(not ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world(), '需要非 PIE Editor')
    seen = set()
    try:
        for path in config['systems']:
            system = ue.load_asset(path)
            require(isinstance(system, ue.NiagaraSystem), '缺 Niagara 系统: ' + path)
            system_ref = {'refPath': system.get_path_name()}
            summary = call(NS + 'GetSystemSummary', system=system_ref)
            selected = [e['emitterName'] for e in summary['emitters'] if e['emitterName'][:4] in phases]
            if not selected:
                continue
            row = {'system': path, 'emitters': selected, 'changes': [], 'saved': False}
            report['systems'].append(row)
            variables = call(NS + 'GetUserVariables', system=system_ref)['userVariables']
            existing = {v['name']: v for v in variables}
            additions = []
            for prefix in sorted({name[:4] for name in selected}):
                phase = phases[prefix]
                name = phase_parameter(phase)
                value = number('Float', phase['start_seconds'])
                if name in existing:
                    require(abs(existing[name]['defaultValue']['value']['value'] - phase['start_seconds']) < 1e-6,
                            '已有阶段参数与制作配置不同: ' + name)
                else:
                    additions.append({'name': name, 'type': {'classStructOrEnum': {'refPath': '/Script/Niagara.NiagaraFloat'}},
                                      'defaultValue': value, 'description': phase['purpose']})
            for name in selected:
                require(name in specs and name not in seen, '发射器缺源或重复: ' + name)
                seen.add(name)
                ref = dict(system=system_ref, emitterName=name, rendererIndex=-1)
                stacks = {stage: call(NS + 'GetScriptStackInputValues', scriptRef=dict(ref, scriptName=stage,
                          moduleName='', inputNameStack=[])) for stage in STAGES}
                row['changes'].extend(emitter_changes(ref, stacks, phases[name[:4]], specs[name]))
                ue.log('[Normal03.Phases] 已检查 ' + name)
            row['added_variables'] = additions
            (out / 'authoring.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            if not row['changes'] and not additions:
                row['already_configured'] = True
                continue
            disk = ROOT / ('Content/' + path[6:] + '.uasset')
            shutil.copy2(disk, out / disk.name)
            if additions:
                call(NS + 'AddUserVariables', system=system_ref, variablesToAdd=additions)
            for change in row['changes']:
                stored = call(NS + 'SetStackInputData', stackInputRef=change['ref'], inputData=change['after'])
                require(stored == change['after'], '输入写后读回不同: ' + str(change['ref']))
            call(COMPILE + 'CompileAuthoringBatch', system=system_ref)
            state = call(COMPILE + 'ReadSystemState', system=system_ref)
            NiagaraBuilder.verify_native_compilation(path, state)
            require(not state['bCompilationPending'] and state['bNativeReady'], '系统未编译就绪')
            diagnostics = NiagaraBuilder.compile_state_from_diagnostics(path,
                call(COMPILE + 'ReadSystemCompileDiagnostics', system=system_ref))
            NiagaraBuilder.verify_compile_state(path, diagnostics)
            row['compile'] = {k: diagnostics[k] for k in ('aggregateStatus', 'bIsCompiling', 'bIsStale', 'bHasErrors', 'bHasWarnings')}
            require(not (dirty() - initial_dirty - {path}), '发现额外脏包，停止保存')
            require(ue.EditorAssetLibrary.save_loaded_asset(system, False), '保存失败: ' + path)
            row['saved'] = True
            ue.log('[Normal03.Phases] 已保存 ' + path)
            ue.collect_garbage()
        require(seen == set(specs), '未覆盖全部指定阶段发射器: ' + str(sorted(set(specs) - seen)))
        report['success'] = True
        return report
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        report['dirty_after'] = sorted(dirty())
        (out / 'authoring.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
