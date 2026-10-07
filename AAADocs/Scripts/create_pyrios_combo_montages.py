"""Create the three initial Pyrios combo Montages from the confirmed contract.

Run in the Unreal Editor Python console. Existing assets are never overwritten.
Section names/links and skeleton Slot registration must be completed in Persona:
the UE 5.8 Python API does not expose CompositeSections for editing.
Gameplay windows below retain their authored timing. End uses the complete source
sequence; natural blend starts in its last target sampling interval. Blend duration
remains an independent Montage setting. Runtime validation is still required.
Each new Montage receives one native cancel point; legacy Hit/Combo windows stay.
ensure_interruption_signal() is an explicit authoring helper for a later approved
asset migration. run() still preserves every existing asset without loading it.
"""
import json
import math
import re
from pathlib import Path
import unreal

BASE = '/Game/Characters/Player/Pyrios/Animation'
PREFIX = 'Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_'
FPS = 60.0
GA_PATH = '/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo'
SIGNAL_NOTIFY_NAME = 'Event.Montage.CancelPoint'
SIGNAL_TRACK = 'ActionSignal'
# Main is retained in full to preserve its measured exact seam with End frame 0.
# FPS describes the original Main/window authoring contract, not target sampling.
# Both source sequences remain untouched.
STEPS = [
    dict(index='01', main_frames=101, hit=(4, 14), combo=(16, 115), next_step_index=1),
    dict(index='02', main_frames=81, hit=(4, 15), combo=(17, 99), next_step_index=2),
    dict(index='03', main_frames=84, hit=(20, 54), combo=(56, 102), next_step_index=0),
]


def full_end_settings(sequence, segment_rate, montage_rate, requested_rate):
    """Use GetSamplingFrameRate's backing target rate, never source/model FPS."""
    path = sequence.get_path_name()
    try:
        platform_rate = sequence.get_editor_property('platform_target_frame_rate')
        rate = platform_rate.get_editor_property('default')
        numerator = int(rate.get_editor_property('numerator'))
        denominator = int(rate.get_editor_property('denominator'))
    except Exception as error:
        raise RuntimeError('Animation asset generator: target sampling rate unavailable: '
                           + path) from error
    length = float(sequence.get_play_length())
    source_rate = float(sequence.get_editor_property('rate_scale'))
    rates = (source_rate, float(segment_rate), float(montage_rate), float(requested_rate))
    if (numerator <= 0 or denominator <= 0 or not math.isfinite(length) or length <= 0
            or any(not math.isfinite(value) or value <= 0 for value in rates)):
        raise RuntimeError('Animation asset generator: invalid full End length, target '
                           'sampling rate or forward playback rate: ' + path)
    interval = denominator / numerator
    if length < interval:
        raise RuntimeError('Animation asset generator: End is shorter than its target '
                           'sampling interval: ' + path)
    return dict(length=length, sampling_numerator=numerator,
                sampling_denominator=denominator,
                trigger_seconds=interval / (rates[0] * rates[1] * rates[2] * rates[3]))


def requested_step_rate(step, play_rates):
    """Read the production GA, or accept explicitly supplied bootstrap settings."""
    if play_rates is not None:
        if step['index'] not in play_rates:
            raise RuntimeError('Animation asset generator: missing explicit play rate for '
                               + step['index'])
        return float(play_rates[step['index']])
    ga = unreal.load_asset(GA_PATH)
    if ga is None:
        raise RuntimeError('Animation asset generator: required GA is missing: ' + GA_PATH
                           + '; initial setup must provide run(play_rates={...}) explicitly')
    steps = unreal.get_default_object(ga.generated_class()).get_editor_property('combo_steps')
    index = int(step['index']) - 1
    if index >= len(steps):
        raise RuntimeError('Animation asset generator: GA has no configured step '
                           + step['index'] + ': ' + GA_PATH)
    configured = steps[index]
    if (str(configured.get_editor_property('interruption_notify_name')) != SIGNAL_NOTIFY_NAME
            or int(configured.get_editor_property('next_step_index')) != step['next_step_index']):
        raise RuntimeError('Animation asset generator: GA signal/next-step configuration '
                           'does not match the production contract: ' + GA_PATH
                           + ' step ' + step['index'])
    return float(configured.get_editor_property('play_rate'))


def _signal_record(montage, notify_name):
    """Read the stock name and actual trigger; cached event display names are not identity."""
    path = montage.get_path_name()
    length = float(montage.get_play_length())
    if not math.isfinite(length) or length <= 0:
        raise RuntimeError('Animation signal authoring: invalid Montage length: ' + path)
    matches = []
    for event in unreal.AnimationLibrary.get_animation_notify_events(montage):
        notify = event.get_editor_property('notify')
        state = event.get_editor_property('notify_state_class')
        names = []
        for obj in (notify, state):
            if obj is None:
                continue
            if isinstance(obj, (unreal.AnimNotify_PlayMontageNotify,
                                unreal.AnimNotify_PlayMontageNotifyWindow)):
                # A subclass may override the display getter. Native Broadcast
                # still uses this editable FName; match it before rejecting it.
                names.append(str(obj.get_editor_property('notify_name')))
            else:
                names.append(str(obj.get_notify_name()))
        # The configured name is ASCII; FName identity ignores letter case.
        if any(name.casefold() == notify_name.casefold() for name in names):
            matches.append((event, notify, state))
    if not matches:
        return None
    if len(matches) != 1:
        raise RuntimeError('Animation signal authoring: duplicate notify '
                           + notify_name + ': ' + path)
    event, notify, state = matches[0]
    if (state is not None or notify is None
            or notify.get_class() != unreal.AnimNotify_PlayMontageNotify.static_class()
            or notify.get_outer() != montage):
        raise RuntimeError('Animation signal authoring: requires one owned stock point notify '
                           + notify_name + ': ' + path)
    trigger = float(unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event))
    duration = float(unreal.AnimationLibrary.get_anim_notify_event_duration(event))
    exported = event.export_text()
    # Native export includes the EndLink before the inherited main link. Only
    # read its last LinkedMontage value; never write this private struct field.
    links = re.findall(r'LinkedMontage=("[^"]*"|None)', exported)
    if (not links or links[-1].split("'", 1)[-1].rstrip('\'"') != path
            or not math.isfinite(trigger) or not 0 <= trigger <= length
            or duration != 0):
        raise RuntimeError('Animation signal authoring: invalid original montage link/trigger '
                           + notify_name + ': ' + path)
    return dict(notify_name=str(notify.get_notify_name()), trigger_seconds=trigger,
                duration_seconds=duration, notify_path=notify.get_path_name(),
                event_export=exported)


def ensure_interruption_signal(montage, notify_name=SIGNAL_NOTIFY_NAME):
    """Add a missing point at the actual End entry; preserve a valid authored point."""
    if str(notify_name) != SIGNAL_NOTIFY_NAME:
        raise RuntimeError('Animation signal authoring: unexpected configured name: '
                           + str(notify_name) + ' on ' + montage.get_path_name())
    existing = _signal_record(montage, str(notify_name))
    if existing is not None:
        return dict(status='existing signal preserved', **existing)
    tracks = montage.get_editor_property('slot_anim_tracks')
    full_body = [track for track in tracks if str(track.get_editor_property('slot_name')) == 'FullBody']
    if len(full_body) != 1:
        raise RuntimeError('Animation signal authoring: requires one FullBody track: '
                           + montage.get_path_name())
    segments = full_body[0].get_editor_property('anim_track').get_editor_property('anim_segments')
    if len(segments) != 2:
        raise RuntimeError('Animation signal authoring: requires the authored Main/End pair: '
                           + montage.get_path_name())
    display_time = float(segments[1].get_editor_property('start_pos'))
    if not math.isfinite(display_time) or not 0 <= display_time <= montage.get_play_length():
        raise RuntimeError('Animation signal authoring: invalid End entry: ' + montage.get_path_name())
    track_names = unreal.AnimationLibrary.get_animation_notify_track_names(montage)
    if SIGNAL_TRACK not in [str(name) for name in track_names]:
        unreal.AnimationLibrary.add_animation_notify_track(montage, SIGNAL_TRACK)
    point = unreal.AnimationLibrary.add_animation_notify_event(
        montage, SIGNAL_TRACK, display_time, unreal.AnimNotify_PlayMontageNotify)
    if point is None or point.get_outer() != montage:
        raise RuntimeError('Animation signal authoring: native point creation failed: '
                           + montage.get_path_name())
    point.set_editor_property('notify_name', notify_name)
    created = _signal_record(montage, str(notify_name))
    if created is None:
        raise RuntimeError('Animation signal authoring: created point could not be verified: '
                           + montage.get_path_name())
    return dict(status='signal created', display_seconds=display_time, **created)


def segment(sequence, start, end):
    value = unreal.AnimSegment()
    value.import_text('(StartPos=%.17g,AnimStartTime=0,AnimEndTime=%.17g,AnimPlayRate=1,LoopingCount=1)' % (start, end))
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

def configure_candidate(montage, step, end_settings):
    for property_name, seconds in (('blend_in', 0.1), ('blend_out', 0.25)):
        blend = montage.get_editor_property(property_name)
        blend.set_editor_property('blend_time', seconds)
        blend.set_editor_property('blend_option', unreal.AlphaBlendOption.HERMITE_CUBIC)
        montage.set_editor_property(property_name, blend)
    montage.set_editor_property('blend_out_trigger_time', end_settings['trigger_seconds'])
    montage.set_editor_property('enable_auto_blend_out', True)
    montage.set_editor_property('loop', False)
    add_window(montage, 'HitWindow', step['hit'])
    add_window(montage, 'ComboWindow', step['combo'])
    signal = ensure_interruption_signal(montage)
    assert unreal.EditorAssetLibrary.save_loaded_asset(montage, only_if_is_dirty=False)
    return signal

def run(play_rates=None):
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
        main_source_rate = float(main.get_editor_property('rate_scale'))
        if not math.isfinite(main_source_rate) or main_source_rate <= 0:
            raise RuntimeError('Animation asset generator: invalid Main playback rate: '
                               + main.get_path_name())
        requested_rate = requested_step_rate(step, play_rates)
        # Validate all source dependencies before creating a package. The actual
        # new Montage rate is read again after factory creation below.
        full_end_settings(end, 1.0, 1.0, requested_rate)
        factory = unreal.AnimMontageFactory()
        factory.set_editor_property('source_animation', main)
        montage = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, BASE + '/Attack', unreal.AnimMontage, factory)
        assert montage
        main_time = float(main.get_play_length())
        end_settings = full_end_settings(
            end, 1.0, float(montage.get_editor_property('rate_scale')), requested_rate)
        end_time = end_settings['length']
        track = unreal.AnimTrack(anim_segments=[segment(main, 0, main_time),
                                               segment(end, main_time / main_source_rate, end_time)])
        montage.set_editor_property('slot_anim_tracks', [unreal.SlotAnimationTrack(slot_name='FullBody', anim_track=track)])
        # Native PostLoad recalculates composite length from the authored tracks;
        # SequenceLength is not editable through the public Python API.
        assert unreal.EditorAssetLibrary.save_loaded_asset(montage, only_if_is_dirty=False)
        unreal.EditorLoadingAndSavingUtils.reload_packages(
            [montage.get_outer()], unreal.ReloadPackagesInteractionMode.ASSUME_POSITIVE)
        montage = unreal.load_asset(path)
        expected_length = (main_time / abs(float(main.get_editor_property('rate_scale')))
                           + end_time / abs(float(end.get_editor_property('rate_scale'))))
        assert abs(montage.get_play_length() - expected_length) < 0.001, 'Montage length not updated'
        signal = configure_candidate(montage, step, end_settings)
        result.append({'path': path, 'status': 'created; Main/End sections pending',
                       'length': montage.get_play_length(), 'full_end': end_settings,
                       'requested_play_rate': requested_rate, 'interruption_signal': signal,
                       **step})
    report_dir = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'Codex'
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / 'PyriosComboCreation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.log_warning('PYRIOS_COMBO_CREATION ' + json.dumps(result))

if __name__ == '__main__':
    run()
