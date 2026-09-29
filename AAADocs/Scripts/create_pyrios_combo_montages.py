"""Create the three initial Pyrios combo Montages from the confirmed contract.

Run in the Unreal Editor Python console. Existing assets are never overwritten.
Section names/links and skeleton Slot registration must be completed in Persona:
the UE 5.8 Python API does not expose CompositeSections for editing.
Window/recovery values below are initial animation candidates, pending in-game QA.
"""
import json
from pathlib import Path
import unreal

BASE = '/Game/Characters/Player/Pyrios/Animation'
PREFIX = 'Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_'
FPS = 60.0
# Main is retained in full to preserve its measured exact seam with End frame 0.
# End is trimmed using the segment; source sequences remain untouched.
STEPS = [
    # Close before automatic BlendOut starts at montage frame 116; GA closes
    # gameplay windows on BlendOut, so the authored interval must end earlier.
    dict(index='01', main_frames=101, end_frames=30, hit=(4, 14), combo=(16, 115)),
    dict(index='02', main_frames=81, end_frames=45, hit=(4, 15), combo=(17, 99)),
    dict(index='03', main_frames=84, end_frames=90, hit=(20, 54), combo=(56, 102)),
]

def segment(sequence, start, end):
    value = unreal.AnimSegment()
    value.import_text('(StartPos=%f,AnimStartTime=0,AnimEndTime=%f,AnimPlayRate=1,LoopingCount=1)' % (start, end))
    value.set_editor_property('anim_reference', sequence)
    value.set_editor_property('cached_play_length', sequence.get_play_length())
    return value

def tag(name):
    value = unreal.GameplayTag()
    value.import_text('(TagName="%s")' % name)
    return value

def add_window(montage, name, frames):
    unreal.AnimationLibrary.add_animation_notify_track(montage, name)
    window = unreal.AnimationLibrary.add_animation_notify_state_event(
        montage, name, frames[0] / FPS, (frames[1] - frames[0]) / FPS,
        unreal.GGYGOAnimNotifyState_GameplayEventWindow)
    window.set_editor_property('begin_event_tag', tag('Event.Montage.' + name + 'Begin'))
    window.set_editor_property('end_event_tag', tag('Event.Montage.' + name + 'End'))

def configure_candidate(montage, step):
    for property_name, seconds in (('blend_in', 0.1), ('blend_out', 0.25)):
        blend = montage.get_editor_property(property_name)
        blend.set_editor_property('blend_time', seconds)
        blend.set_editor_property('blend_option', unreal.AlphaBlendOption.HERMITE_CUBIC)
        montage.set_editor_property(property_name, blend)
    montage.set_editor_property('blend_out_trigger_time', -1.0)
    montage.set_editor_property('enable_auto_blend_out', True)
    montage.set_editor_property('loop', False)
    add_window(montage, 'HitWindow', step['hit'])
    add_window(montage, 'ComboWindow', step['combo'])
    assert unreal.EditorAssetLibrary.save_loaded_asset(montage, only_if_is_dirty=False)

def run():
    result = []
    for step in STEPS:
        name = 'AM_Pyrios_Attack_Normal_' + step['index']
        path = BASE + '/Attack/' + name
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            result.append({'path': path, 'status': 'existing asset preserved'})
            continue
        main = unreal.load_asset(BASE + '/' + PREFIX + step['index'])
        end = unreal.load_asset(BASE + '/' + PREFIX + step['index'] + '_End')
        assert main and end and main.get_editor_property('skeleton') == end.get_editor_property('skeleton')
        assert abs(main.get_play_length() * FPS - step['main_frames']) < 0.01
        factory = unreal.AnimMontageFactory()
        factory.set_editor_property('source_animation', main)
        montage = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, BASE + '/Attack', unreal.AnimMontage, factory)
        assert montage
        main_time = step['main_frames'] / FPS
        end_time = step['end_frames'] / FPS
        track = unreal.AnimTrack(anim_segments=[segment(main, 0, main_time), segment(end, main_time, end_time)])
        montage.set_editor_property('slot_anim_tracks', [unreal.SlotAnimationTrack(slot_name='FullBody', anim_track=track)])
        # Native PostLoad recalculates composite length from the authored tracks;
        # SequenceLength is not editable through the public Python API.
        assert unreal.EditorAssetLibrary.save_loaded_asset(montage, only_if_is_dirty=False)
        unreal.EditorLoadingAndSavingUtils.reload_packages(
            [montage.get_outer()], unreal.ReloadPackagesInteractionMode.ASSUME_POSITIVE)
        montage = unreal.load_asset(path)
        assert abs(montage.get_play_length() - main_time - end_time) < 0.001, 'Montage length not updated'
        configure_candidate(montage, step)
        result.append({'path': path, 'status': 'created; Main/End sections pending', 'length': montage.get_play_length(), **step})
    report_dir = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'Codex'
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / 'PyriosComboCreation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.log_warning('PYRIOS_COMBO_CREATION ' + json.dumps(result))

if __name__ == '__main__':
    run()
