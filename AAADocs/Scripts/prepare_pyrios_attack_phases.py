"""用已制作来源生成带动作阶段的新 Niagara 版本，只复用既存材质和几何。

配置只改变源 System.Age 的局部起点与粒子启动 Delay；Particle.Age 保持原生。
静态残影增加同一 System.Age 驱动的可见窗，不新增运行调度器。
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'AAADocs/Assets/Pyrios/FX/Pyrios_Attack_Phases.json'
OUT = ROOT / 'Saved/Codex/PyriosActionFX_20261111/AttackPhasePreparation_20261112'


def phase_spec(spec, phase):
    start = float(phase['start_seconds'])
    local_age = 'max(0.0, System.Age - ' + format(start, '.17g') + ')'
    spec['project_phase'] = dict(phase, configuration_mode='ProjectConfigured')
    for stage in ('spawn', 'update', 'emitter_spawn', 'emitter_update'):
        spec[stage] = [(name, kind, re.sub(r'\bSystem\.Age\b', local_age, code))
                       for name, kind, code in spec.get(stage, [])]
    if spec.get('source_mode') != 'Emitter':
        # 子拖尾从父粒子采样，保其原生采样器；父粒子的出生仍只由原 Delay 控制。
        if not spec.get('particle_trail_child'):
            spec['delay'] += start
        if spec['renderer']['kind'] == 'generated_ribbon':
            spec['renderer']['generator']['geometry']['delay_seconds'] += start
        return
    end = float(phase['end_seconds'])
    if spec['renderer']['kind'] == 'component_mesh':
        visible = '((System.Age >= %s && System.Age < %s) ? 0 : 1)' % (format(start, '.17g'), format(end, '.17g'))
        for stage in ('emitter_spawn', 'emitter_update'):
            spec[stage].append(('Emitter.UEFX_PhaseVisibility', 'Int', visible))
        for draw in spec['renderer']['draws']:
            draw['phase_visibility'] = True
    elif spec['renderer']['kind'] == 'light':
        for stage in ('emitter_spawn', 'emitter_update'):
            spec[stage] = [(n, k, '((%s) && System.Age >= %s && System.Age < %s)' %
                           (v, format(start, '.17g'), format(end, '.17g')) if n.endswith('ComponentEnabled') else v)
                           for n, k, v in spec[stage]]
    else:
        raise ValueError('未支持的组件阶段：' + spec['name'])


def prepare():
    sys.path.insert(0, str(ROOT / 'Saved/Codex/FXRestoration_20261022_F1'))
    import project_fx_prepare as old
    from zzz_fx_asset_session import version_name
    from zzz_fx_build import independent_system_plan, compile_unit_plans
    from zzz_fx_niagara_ue import NiagaraBuilder
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    source = json.loads(gzip.decompress((ROOT / config['source_preparation']).read_bytes()))
    policy = json.loads((ROOT / 'Saved/Codex/FXRestoration_20261022_F1/project_actions.json').read_text(encoding='utf-8'))
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {'configuration': str(CONFIG), 'actions': {}, 'plans': []}
    for action, settings in config['actions'].items():
        original = source['actions'][action]
        plan = old._compose_action_plan(action, original['members'], policy)
        if old._composition_identity(plan) != original['plan_identity']:
            raise ValueError('既有来源组合身份变化：' + action)
        phases = {p['prefix']: p for p in settings['phases']}
        if settings.get('existing_late_phases'):
            phases.update({p['prefix']: p for p in json.loads((ROOT / settings['existing_late_phases']).read_text(encoding='utf-8'))['phases']})
        for spec in plan['specs']:
            phase_spec(spec, phases[spec['name'][:4]])
        action_plans = [plan]
        for phase in settings.get('front_phases', []):
            file = ROOT / config['front_preparation'] / ('Eff_Pyrois_Attack_' + action + '_01_' + phase['member'] + '.json')
            front = json.loads(file.read_text(encoding='utf-8'))
            for spec in front['specs']:
                phase_spec(spec, phase)
            action_plans.append(front)
        manifest['actions'][action] = []
        for plan in action_plans:
            previous = plan['system']
            plan['system'] = previous.rsplit('/', 1)[0] + '/' + version_name('NS_Pyrios_' + action + '_Phased_' + plan['name'], plan['specs'])
            plan['targets'] = sorted((set(plan['targets']) - {previous}) | {plan['system']})
            for unit in compile_unit_plans(independent_system_plan(plan)):
                for spec in unit['specs']:
                    NiagaraBuilder.validate_spec(spec)
                filename = OUT / (unit['system'].rsplit('/', 1)[-1] + '.json')
                filename.write_text(json.dumps(unit, ensure_ascii=False, indent=1), encoding='utf-8')
                manifest['plans'].append(str(filename))
                manifest['actions'][action].append({'system': unit['system'], 'emitters': len(unit['specs']), 'file': str(filename)})
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({a: {'systems': len(p), 'emitters': sum(u['emitters'] for u in p)} for a, p in manifest['actions'].items()}))


if __name__ == '__main__':
    prepare()
