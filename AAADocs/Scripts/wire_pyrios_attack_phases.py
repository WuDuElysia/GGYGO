"""只替换三动作的 FX 单元，并同步角色输入资源准备列表；保留其它动作字段。"""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = '/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_'
CHARACTER = '/Game/BP/Character/Player/BP_PC_Pyrios'


def replace_units(text, units):
    marker = 'SystemUnits='
    if text.count(marker) != 1:
        raise ValueError('原 FX 没有唯一 SystemUnits')
    start = text.index(marker) + len(marker)
    depth, quoted, escaped = 0, False, False
    for i in range(start, len(text)):
        char = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0:
                return text[:start] + '(' + ','.join(u.export_text() for u in units) + ')' + text[i+1:]
    raise ValueError('原 FX 单元序列不完整')


def apply(ue, manifest_path, output_dir):
    from wire_pyrios_combo_fx import protect_step0, replace_step0_fx, graph_snapshot
    sys.path.insert(0, str(ROOT / 'Saved/Codex/FXRestoration_20261022_F1'))
    from action_fx_author import prepare_unit_field_settings
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=False)
    if ue.EditorLevelLibrary.get_pie_worlds(True):
        raise RuntimeError('需要非 PIE 制作窗口')
    world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
    report = {'abilities': [], 'saved': False}
    replaced_systems = set()
    def clean(path):
        if any(p.get_path_name() == path for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('目标有未保存工作：' + path)
    def backup(path):
        source = ROOT / 'Content' / (path[6:] + '.uasset')
        shutil.copy2(source, out / source.name)
    try:
        for action, suffix, index in [('Normal03', 'Combo', 2), ('Special', 'Special_01', 0), ('ExSpecial', 'ExSpecial_01', 0)]:
            path = BASE + suffix
            clean(path)
            bp = ue.load_asset(path)
            cdo = ue.get_default_object(bp.generated_class())
            steps = list(cdo.get_editor_property('combo_steps'))
            original = [step.export_text() for step in steps]
            graphs = graph_snapshot(ue, bp)
            fx = steps[index].get_editor_property('fx')
            old_units = list(fx.get_editor_property('system_units'))
            if not old_units or fx.get_editor_property('system') is not None:
                raise RuntimeError('预期原动作使用 SystemUnits：' + action)
            profile = next((u.get_editor_property('field_settings').get_editor_property('profile') for u in old_units
                            if u.get_editor_property('field_settings').get_editor_property('profile')), None)
            if profile is None:
                raise RuntimeError('原动作缺有效场 Profile：' + action)
            retained = []
            for unit in old_units:
                system_name = unit.get_editor_property('system').get_path_name().split('.')[0]
                if action == 'ExSpecial' and system_name.endswith('NS_Eff_Pyrois_Attack_ExSpecial_01_09_MOD_3f003f915dcc'):
                    retained.append(unit)
                else:
                    replaced_systems.add(system_name)
            if action == 'ExSpecial' and len(retained) != 1:
                raise RuntimeError('ExSpecial 缺少唯一既有武器附着单元')
            units, qualifications = [], []
            for row in manifest['actions'][action]:
                plan = json.loads(Path(row['file']).read_text(encoding='utf-8'))
                system = ue.load_asset(plan['system'])
                if not isinstance(system, ue.NiagaraSystem):
                    raise RuntimeError('新阶段资产未完成：' + plan['system'])
                prepared = prepare_unit_field_settings(ue, plan, profile, world)
                units.append(ue.GGYGONiagaraEffectUnit(system=system, field_settings=prepared['settings']))
                qualifications.append(prepared['qualification'])
            units += retained
            new_fx = ue.GGYGOComboStepFX()
            if not new_fx.import_text(replace_units(fx.export_text(), units)):
                raise RuntimeError('FX 单元构造失败：' + action)
            if replace_units(new_fx.export_text(), []) != replace_units(fx.export_text(), []):
                raise RuntimeError('FX 单元以外的原挂点／变换／停止配置发生变化：' + action)
            new_step = ue.GGYGOComboStep()
            if not new_step.import_text(replace_step0_fx(original[index], new_fx.export_text())):
                raise RuntimeError('动作配置构造失败：' + action)
            if protect_step0(new_step.export_text()) != protect_step0(original[index]):
                raise RuntimeError('非 FX 动作字段发生变化：' + action)
            steps[index] = new_step
            expected = [step.export_text() for step in steps]
            backup(path)
            bp.modify()
            cdo.modify()
            cdo.set_editor_property('combo_steps', steps)
            ue.BlueprintEditorLibrary.compile_blueprint(bp)
            if 'UP_TO_DATE' not in str(bp.get_editor_property('status')):
                raise RuntimeError('GA 蓝图编译失败：' + action)
            actual = [s.export_text() for s in ue.get_default_object(bp.generated_class()).get_editor_property('combo_steps')]
            if actual != expected or graph_snapshot(ue, bp) != graphs:
                raise RuntimeError('GA 写后配置／图不符：' + action)
            if not ue.EditorAssetLibrary.save_loaded_asset(bp, False):
                raise RuntimeError('GA 保存失败：' + action)
            report['abilities'].append({'action': action, 'package': path, 'before': original, 'after': actual,
                                        'non_fx_preserved': True, 'graphs_preserved': True, 'qualifications': qualifications})
        clean(CHARACTER)
        bp = ue.load_asset(CHARACTER)
        cdo = ue.get_default_object(bp.generated_class())
        before = list(cdo.get_editor_property('AbilityInputRenderSystems'))
        expected = [s for s in before if s.get_path_name().split('.')[0] not in replaced_systems]
        for suffix in ('Combo', 'Special_01', 'ExSpecial_01'):
            ga = ue.get_default_object(ue.EditorAssetLibrary.load_blueprint_class(BASE + suffix))
            for step in ga.get_editor_property('combo_steps'):
                fx = step.get_editor_property('fx')
                values = [fx.get_editor_property('system')] if fx.get_editor_property('system') else [u.get_editor_property('system') for u in fx.get_editor_property('system_units')]
                for system in values:
                    if not isinstance(system, ue.NiagaraSystem):
                        raise RuntimeError('生产资源列表含空系统')
                    if system not in expected:
                        expected.append(system)
        graphs = graph_snapshot(ue, bp)
        backup(CHARACTER)
        bp.modify()
        cdo.modify()
        cdo.set_editor_property('AbilityInputRenderSystems', expected)
        ue.BlueprintEditorLibrary.compile_blueprint(bp)
        actual = list(ue.get_default_object(bp.generated_class()).get_editor_property('AbilityInputRenderSystems'))
        if actual != expected or graph_snapshot(ue, bp) != graphs or 'UP_TO_DATE' not in str(bp.get_editor_property('status')):
            raise RuntimeError('角色资源列表或图写后不符')
        if not ue.EditorAssetLibrary.save_loaded_asset(bp, False):
            raise RuntimeError('角色资源列表保存失败')
        report['resources'] = {'before': [s.get_path_name() for s in before], 'after': [s.get_path_name() for s in actual], 'graphs_preserved': True}
        report['saved'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        (out / 'wiring.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    return report
