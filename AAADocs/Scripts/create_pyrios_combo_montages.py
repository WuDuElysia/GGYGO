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

run_cancel_split() is the separate CancelSplit entry for the three existing Normal
Montages: it only appends one stock Event.Montage.MoveCancelPoint whose authored
GetTime equals the native End Section GetTime (Main end). The engine-computed
TriggerTimeOffset is kept as an original fact; movement permission belongs to the
GA's live-position gate, never to this tool. It never rebuilds Montages, moves or
creates the legacy CancelPoint, or writes GA/AS/Skeleton packages. Its exact
section/notify floats come only from the native timeline getter declared below.
"""
import hashlib
import json
import math
import os
import re
import struct
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


# ---------------------------------------------------------------------------
# CancelSplit: append an independent stock movement point to existing Montages.
# ---------------------------------------------------------------------------
CANCEL_SPLIT_REQUEST_ID = 'GGYGO-Action-CancelSplit-20261012-01'
MOVE_SIGNAL_NOTIFY_NAME = 'Event.Montage.MoveCancelPoint'
STOCK_POINT_CLASS = '/Script/AnimGraphRuntime.AnimNotify_PlayMontageNotify'
STOCK_WINDOW_CLASS = '/Script/AnimGraphRuntime.AnimNotify_PlayMontageNotifyWindow'
MAIN_SECTION = 'Main'
END_SECTION = 'End'
MOTION_SLOT = 'FullBody'
CANCEL_SPLIT_TARGETS = tuple(
    BASE + '/Attack/AM_Pyrios_Attack_Normal_' + index for index in ('01', '02', '03'))
# Packages this entry must never change. Paths are relative to the project Content dir.
CANCEL_SPLIT_PROTECTED = (
    'Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo',
    *('Characters/Player/Pyrios/Animation/' + PREFIX + index + suffix
      for index in ('01', '02', '03') for suffix in ('', '_End')),
    *('Characters/Player/Pyrios/Animation/Avatar_Male_Size03_Pyrois_Ani_Attack_' + skill + suffix
      for skill in ('Special_01', 'ExSpecial_01', 'Rush_01') for suffix in ('', '_End')),
    *('Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_' + skill
      for skill in ('Special_01', 'ExSpecial_01', 'Rush_01')),
    'Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model_Skeleton',
    'Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model',
    'BP/Anim/ABP_Pyrios',
)
PACKAGE_SUFFIXES = ('.uasset', '.uexp', '.ubulk')
# Interface dependency, not an existing API: the Editor-only read-only getter must
# return these reflected fields (Python names) from native GetTime/GetTriggerTime/
# TriggerTimeOffset/IsBranchingPoint. Absent class/function/field is a rejection.
# Native source: UGGYGOLinearMontageAuthorLibrary::ReadMontageTimelineFacts (GGYGOEditor).
# Section time is FCompositeSection::GetTime; notify_class/state_class are the Notify /
# NotifyStateClass class paths ('' when absent); stock_notify_name is the broadcast
# NotifyName of a PlayMontageNotify/Window or subclass (exact class is checked here),
# otherwise 'None'. The getter exists in source only until the same-version build loads it.
TIMELINE_LIBRARY = 'GGYGOLinearMontageAuthorLibrary'
TIMELINE_GETTER = 'read_montage_timeline_facts'
TIMELINE_FIELDS = dict(succeeded=bool, error=str, play_length=float,
                       sections=list, segments=list, notifies=list)
SECTION_FIELDS = dict(section_name=str, next_section_name=str, time=float,
                      slot_index=int, segment_index=int)
SEGMENT_FIELDS = dict(slot_name=str, slot_index=int, segment_index=int, start_pos=float,
                      end_pos=float, anim_reference=str)
NOTIFY_FIELDS = dict(guid=str, track_index=int, notify_class=str, notify_object=str,
                     stock_notify_name=str, state_class=str, time=float,
                     trigger_time_offset=float, trigger_time=float, duration=float,
                     end_trigger_time=float, slot_index=int, segment_index=int,
                     link_method=str, is_branching_point=bool, linked_to_self=bool)
SETTING_PROPERTIES = ('rate_scale', 'loop', 'enable_auto_blend_out', 'blend_out_trigger_time')
BLEND_PROPERTIES = ('blend_in', 'blend_out')


class CancelSplitError(RuntimeError):
    """A required native fact, contract or protection is absent; nothing is repaired."""

    def __init__(self, reason, montage_path=None):
        where = (' [' + montage_path + ']') if montage_path else ''
        super().__init__('Animation CancelSplit' + where + ': ' + reason)


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _f32_bits(value):
    return struct.pack('<f', value).hex()


# Native GetTriggerTimeOffsetForType results; any other offset is an unknown engine fact.
NO_OFFSET = 0.0
OFFSET_BEFORE = _f32(-1e-4)


def _native_float(value, label, path):
    """Accept only finite values that are exact float32 native reads."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CancelSplitError('native float field is not numeric: ' + label, path)
    value = float(value)
    if not math.isfinite(value) or _f32(value) != value:
        raise CancelSplitError('native float field is nonfinite or not float32: ' + label, path)
    return value


def _read_struct(value, schema, label, path):
    result = {}
    for name, kind in schema.items():
        try:
            raw = value.get_editor_property(name)
        except Exception as error:
            raise CancelSplitError('timeline getter field is unavailable: ' + label + '.' + name,
                                   path) from error
        if kind is float:
            result[name] = _native_float(raw, label + '.' + name, path)
        elif kind is bool:
            if not isinstance(raw, bool):
                raise CancelSplitError('timeline getter field is not bool: ' + label + '.' + name, path)
            result[name] = raw
        elif kind is int:
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise CancelSplitError('timeline getter field is not int: ' + label + '.' + name, path)
            result[name] = raw
        elif kind is list:
            result[name] = list(raw)
        else:
            result[name] = str(raw)
    return result


def read_timeline_facts(montage):
    """Read native Montage timeline facts; no T3D, StartPos, source-frame or Gate fallback."""
    path = montage.get_path_name()
    library = getattr(unreal, TIMELINE_LIBRARY, None)
    getter = getattr(library, TIMELINE_GETTER, None) if library is not None else None
    if getter is None:
        raise CancelSplitError('required native getter ' + TIMELINE_LIBRARY + '.' + TIMELINE_GETTER
                               + ' is not available in the loaded Editor modules', path)
    result = getter(montage)
    top = _read_struct(result, TIMELINE_FIELDS, 'result', path)
    if not top['succeeded']:
        raise CancelSplitError('native timeline getter failed: ' + top['error'], path)
    facts = dict(play_length=top['play_length'])
    facts['sections'] = [_read_struct(value, SECTION_FIELDS, 'sections[%d]' % index, path)
                         for index, value in enumerate(top['sections'])]
    facts['segments'] = [_read_struct(value, SEGMENT_FIELDS, 'segments[%d]' % index, path)
                         for index, value in enumerate(top['segments'])]
    facts['notifies'] = [_read_struct(value, NOTIFY_FIELDS, 'notifies[%d]' % index, path)
                         for index, value in enumerate(top['notifies'])]
    return facts


def _main_end(facts, path):
    """Main end is the native End Section GetTime, the same source the GA reads.

    Segment seams are geometry kept unchanged and reported as evidence; a float seam that
    differs from the Section time is not a second Main end and is never used to place points.
    """
    length = facts['play_length']
    if length <= 0:
        raise CancelSplitError('Montage play length is not positive', path)
    sections = facts['sections']
    if [value['section_name'] for value in sections] != [MAIN_SECTION, END_SECTION]:
        raise CancelSplitError('Montage must have exactly the Main/End sections', path)
    main, end = sections
    if (main['next_section_name'] != END_SECTION or end['next_section_name'] != 'None'
            or main['time'] != 0.0 or not 0.0 < end['time'] < length):
        raise CancelSplitError('Main must start at 0, link to End, and End must start inside the Montage',
                               path)
    segments = facts['segments']
    if (len(segments) != 2 or any(value['slot_name'] != MOTION_SLOT for value in segments)
            or len({value['slot_index'] for value in segments}) != 1
            or [value['segment_index'] for value in segments] != [0, 1]):
        raise CancelSplitError('Montage must have exactly one FullBody Main/End segment pair', path)
    if segments[0]['start_pos'] != 0.0:
        raise CancelSplitError('Main segment must start at 0', path)
    return end['time']


def _segment_seam(facts):
    """Evidence only: native Main segment end / End segment start beside the Section time."""
    segments = facts['segments']
    section = facts['sections'][1]['time']
    return dict(section_end_f32=_f32_bits(section),
                main_segment_end_f32=_f32_bits(segments[0]['end_pos']),
                end_segment_start_f32=_f32_bits(segments[1]['start_pos']),
                bitwise_equal=(_f32_bits(segments[0]['end_pos']) == _f32_bits(section)
                               == _f32_bits(segments[1]['start_pos'])))


def _named(facts, name):
    """Stock point/window declarations carrying a case-insensitive FName."""
    return [value for value in facts['notifies']
            if value['stock_notify_name'].casefold() == name.casefold()]


def _require_stock_point(notify, name, length, path):
    owned = notify['notify_object'].startswith(path + ':')
    if (notify['notify_class'] != STOCK_POINT_CLASS or notify['state_class'] not in ('', 'None')
            or notify['stock_notify_name'] != name or notify['duration'] != 0.0
            or not notify['linked_to_self'] or not notify['is_branching_point'] or not owned
            or not 0.0 <= notify['time'] <= length or not 0.0 <= notify['trigger_time'] <= length):
        raise CancelSplitError('%s must be one owned stock zero-duration BranchingPoint inside the '
                               'Montage' % name, path)


def _require_move_point_facts(notify, main_end, facts, path):
    """Authored time equals Main end; the native offset is kept, never compensated."""
    _require_stock_point(notify, MOVE_SIGNAL_NOTIFY_NAME, facts['play_length'], path)
    if _f32_bits(notify['time']) != _f32_bits(main_end):
        raise CancelSplitError('MoveCancelPoint authored GetTime must equal the End Section GetTime; '
                               'existing points are never moved', path)
    offset = notify['trigger_time_offset']
    if _f32_bits(offset) not in (_f32_bits(NO_OFFSET), _f32_bits(OFFSET_BEFORE)):
        raise CancelSplitError('MoveCancelPoint has an unexpected native TriggerTimeOffset', path)
    if _f32_bits(notify['trigger_time']) != _f32_bits(_f32(notify['time'] + offset)):
        raise CancelSplitError('MoveCancelPoint GetTriggerTime is not GetTime + TriggerTimeOffset', path)
    collisions = [value['guid'] for value in facts['notifies']
                  if value is not notify and value['is_branching_point']
                  and _f32_bits(value['trigger_time']) == _f32_bits(notify['trigger_time'])]
    if collisions:
        raise CancelSplitError('MoveCancelPoint native trigger time collides with BranchingPoint '
                               + ', '.join(collisions) + '; no point is moved', path)


def plan_move_cancel_point(facts, path):
    """Pure plan: validate both signals and Main end; never grants or schedules permission."""
    main_end = _main_end(facts, path)
    length = facts['play_length']
    for name in (SIGNAL_NOTIFY_NAME, MOVE_SIGNAL_NOTIFY_NAME):
        if any(value['notify_class'] == STOCK_WINDOW_CLASS or value['state_class'] not in ('', 'None')
               for value in _named(facts, name)):
            raise CancelSplitError(name + ' is also declared by a Montage Notify Window/state', path)
    legacy = _named(facts, SIGNAL_NOTIFY_NAME)
    if len(legacy) != 1:
        raise CancelSplitError('legacy CancelPoint must exist exactly once; it is never created here',
                               path)
    _require_stock_point(legacy[0], SIGNAL_NOTIFY_NAME, length, path)
    moves = _named(facts, MOVE_SIGNAL_NOTIFY_NAME)
    if len(moves) > 1:
        raise CancelSplitError('MoveCancelPoint is duplicated', path)
    plan = dict(path=path, main_end=main_end, main_end_f32=_f32_bits(main_end),
                legacy_guid=legacy[0]['guid'], segment_seam=_segment_seam(facts))
    if moves:
        _require_move_point_facts(moves[0], main_end, facts, path)
        plan.update(action='existing preserved', move_guid=moves[0]['guid'])
    else:
        plan.update(action='append')
    return plan


def _notify_map(facts):
    result = {}
    for value in facts['notifies']:
        if not value['guid'] or value['guid'] in result:
            raise CancelSplitError('notify Guid is empty or duplicated: ' + value['guid'])
        result[value['guid']] = value
    return result


def _geometry(facts):
    return dict(play_length=facts['play_length'], sections=facts['sections'],
                segments=facts['segments'])


def montage_settings(montage):
    """Montage-level blend/rate settings that the append must keep."""
    path = montage.get_path_name()
    result = {}
    try:
        for name in SETTING_PROPERTIES:
            result[name] = montage.get_editor_property(name)
        for name in BLEND_PROPERTIES:
            blend = montage.get_editor_property(name)
            result[name] = dict(blend_time=blend.get_editor_property('blend_time'),
                                blend_option=str(blend.get_editor_property('blend_option')))
    except Exception as error:
        raise CancelSplitError('Montage blend/rate settings are unavailable', path) from error
    return result


def verify_appended(before, after, path):
    """All old notifies, sections, segments, length and settings unchanged; one valid new point."""
    if _geometry(before['facts']) != _geometry(after['facts']):
        raise CancelSplitError('sections/segments/length changed during append', path)
    if before['settings'] != after['settings']:
        raise CancelSplitError('Montage blend/rate settings changed during append', path)
    old = _notify_map(before['facts'])
    new = _notify_map(after['facts'])
    if any(new.get(guid) != value for guid, value in old.items()):
        raise CancelSplitError('an existing notify changed or disappeared during append', path)
    added = [value for guid, value in new.items() if guid not in old]
    if len(added) != 1:
        raise CancelSplitError('append must add exactly one notify', path)
    plan = plan_move_cancel_point(after['facts'], path)
    if plan['action'] != 'existing preserved' or plan['move_guid'] != added[0]['guid']:
        raise CancelSplitError('appended notify is not the validated MoveCancelPoint', path)
    return added[0]


def append_move_cancel_point(montage, plan):
    """Append one stock point at the planned native Main end; the caller verifies and saves."""
    path = montage.get_path_name()
    if plan.get('action') != 'append' or plan.get('path') != path:
        raise CancelSplitError('append requires this Montage\'s validated append plan', path)
    library = unreal.AnimationLibrary
    if SIGNAL_TRACK not in [str(name) for name in library.get_animation_notify_track_names(montage)]:
        library.add_animation_notify_track(montage, SIGNAL_TRACK)
    point = library.add_animation_notify_event(
        montage, SIGNAL_TRACK, plan['main_end'], unreal.AnimNotify_PlayMontageNotify)
    if point is None or point.get_outer() != montage:
        raise CancelSplitError('native stock point creation failed', path)
    point.set_editor_property('notify_name', MOVE_SIGNAL_NOTIFY_NAME)
    return point.get_path_name()


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest().upper()


def _package_state(relative, required):
    base = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())) / relative
    state = {}
    for suffix in PACKAGE_SUFFIXES:
        file = base.with_name(base.name + suffix)
        state[suffix] = _sha256(file) if file.is_file() else None
    if required and state['.uasset'] is None:
        raise CancelSplitError('protected or target package is missing on disk: ' + relative)
    return state


def _target_relative(path):
    return path[len('/Game/'):]


def _dirty_packages():
    utils = unreal.EditorLoadingAndSavingUtils
    return dict(content=sorted(p.get_path_name() for p in utils.get_dirty_content_packages()),
                maps=sorted(p.get_path_name() for p in utils.get_dirty_map_packages()))


def _require_clean(label):
    dirty = _dirty_packages()
    if dirty != dict(content=[], maps=[]):
        raise CancelSplitError(label + ': host has dirty packages; user work is preserved, '
                               'nothing is saved or discarded')
    return dirty


def _authorize(authorization):
    """The coordinator supplies the owned fresh host; this tool never guesses or attaches."""
    if not isinstance(authorization, dict):
        raise CancelSplitError('explicit authorization is required')
    mode = authorization.get('mode')
    if (authorization.get('request_id') != CANCEL_SPLIT_REQUEST_ID
            or mode not in ('plan', 'author', 'cold')
            or authorization.get('host_pid') != os.getpid()
            or not str(authorization.get('window_id') or '').strip()):
        raise CancelSplitError('authorization must name this request, a plan/author/cold mode, the '
                               'current owned host_pid and the granted window_id')
    return mode


def _create_report_dir(report_dir):
    saved = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())).resolve()
    directory = Path(report_dir).resolve()
    if saved not in directory.parents:
        raise CancelSplitError('report directory must be under the project Saved directory')
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def _point_record(notify, plan):
    return dict(guid=notify['guid'], notify_object=notify['notify_object'],
                time=notify['time'], time_f32=_f32_bits(notify['time']),
                trigger_time_offset=notify['trigger_time_offset'],
                trigger_time_offset_f32=_f32_bits(notify['trigger_time_offset']),
                trigger_time=notify['trigger_time'], trigger_time_f32=_f32_bits(notify['trigger_time']),
                main_end_f32=plan['main_end_f32'], slot_index=notify['slot_index'],
                segment_index=notify['segment_index'], link_method=notify['link_method'])


def _load_author_report(author_report):
    try:
        expected = json.loads(Path(author_report).read_text(encoding='utf-8'))
    except Exception as error:
        raise CancelSplitError('cold readback requires the successful author report') from error
    if (expected.get('request_id') != CANCEL_SPLIT_REQUEST_ID or expected.get('mode') != 'author'
            or expected.get('success') is not True):
        raise CancelSplitError('author report is not a successful CancelSplit author run')
    return expected


def run_cancel_split(authorization, report_dir, author_report=None):
    """Plan, append or cold-read the MoveCancelPoint on the three Normal Montages only.

    Requires a coordinator-granted owned host (host_pid/window_id), a clean dirty set and the
    native timeline getter. Only the appended Normal Montages are saved, individually, after
    every old notify/section/segment/length/setting and all protected packages are verified.
    Any failure stops before saving, keeps dirty packages for review and writes a create-only
    report. GA/Task consumer contracts are not read or written here.
    """
    mode = _authorize(authorization)
    directory = _create_report_dir(report_dir)
    report = dict(request_id=CANCEL_SPLIT_REQUEST_ID, mode=mode,
                  window_id=authorization['window_id'], host_pid=os.getpid(),
                  script_sha256=_sha256(__file__), targets=list(CANCEL_SPLIT_TARGETS),
                  authorization_scope='caller-supplied host_pid/window_id input gate; not proof of '
                                      'a fresh owned host, which the coordinator must establish',
                  ga_consumer_contract='Combat-owned GA: Normal steps MovementInterruptionMode='
                                       'AuthoredNotify / MovementInterruptionNotifyName='
                                       + MOVE_SIGNAL_NOTIFY_NAME + '; this tool never loads or '
                                       'writes the GA; consumption pending same-version integration',
                  task_contract='pending: AbilitySystem multi-point Task interface not integrated; '
                                'movement permission stays with the GA live-position gate',
                  success=False, saved=[], error=None)
    try:
        expected = _load_author_report(author_report) if mode == 'cold' else None
        library = getattr(unreal, TIMELINE_LIBRARY, None)
        if getattr(library, TIMELINE_GETTER, None) is None:
            raise CancelSplitError('required native getter ' + TIMELINE_LIBRARY + '.'
                                   + TIMELINE_GETTER + ' is not available; no fallback source exists')
        report['dirty_before'] = _require_clean('before')
        report['protected_before'] = {value: _package_state(value, True) for value in CANCEL_SPLIT_PROTECTED}
        report['targets_before'] = {path: _package_state(_target_relative(path), True)
                                    for path in CANCEL_SPLIT_TARGETS}
        if expected is not None and (report['protected_before'] != expected['protected_after']
                                     or report['targets_before'] != expected['targets_after']):
            raise CancelSplitError('disk packages differ from the successful author report')
        montages, records = {}, {}
        # Plan every target before the first write; one rejection leaves all three untouched.
        for path in CANCEL_SPLIT_TARGETS:
            montage = unreal.load_asset(path)
            if montage is None:
                raise CancelSplitError('target Montage failed to load: ' + path)
            object_path = montage.get_path_name()
            facts = read_timeline_facts(montage)
            plan = plan_move_cancel_point(facts, object_path)
            montages[path] = montage
            records[path] = dict(plan=plan, before=dict(facts=facts, settings=montage_settings(montage)))
        report['records'] = records
        if expected is not None:
            for path, record in records.items():
                if (record['plan']['action'] != 'existing preserved'
                        or record['before'] != expected['records'][path]['after']):
                    raise CancelSplitError('cold facts differ from the saved author facts', path)
        appended = []
        if mode == 'author':
            for path, montage in montages.items():
                record = records[path]
                if record['plan']['action'] != 'append':
                    continue
                object_path = montage.get_path_name()
                point_path = append_move_cancel_point(montage, record['plan'])
                appended.append(path)
                after = dict(facts=read_timeline_facts(montage), settings=montage_settings(montage))
                added = verify_appended(record['before'], after, object_path)
                if added['notify_object'] != point_path:
                    raise CancelSplitError('verified point is not the object created here', object_path)
                record['after'] = after
                record['new_point'] = _point_record(added, record['plan'])
            if _dirty_packages() != dict(content=sorted(appended), maps=[]):
                raise CancelSplitError('dirty set is not exactly the appended Normal Montages; not saved')
            for path in appended:
                if not unreal.EditorAssetLibrary.save_loaded_asset(montages[path], only_if_is_dirty=False):
                    raise CancelSplitError('save_loaded_asset returned false', path)
                report['saved'].append(path)
        for record in records.values():
            record.setdefault('after', record['before'])
            if record['plan']['action'] == 'existing preserved':
                moves = _named(record['after']['facts'], MOVE_SIGNAL_NOTIFY_NAME)
                record.setdefault('new_point', _point_record(moves[0], record['plan']))
        report['dirty_after'] = _require_clean('after')
        report['protected_after'] = {value: _package_state(value, True) for value in CANCEL_SPLIT_PROTECTED}
        report['targets_after'] = {path: _package_state(_target_relative(path), True)
                                   for path in CANCEL_SPLIT_TARGETS}
        if report['protected_after'] != report['protected_before']:
            raise CancelSplitError('a protected GA/AS/AM/Skeleton/Mesh/ABP package changed')
        for path in CANCEL_SPLIT_TARGETS:
            changed = report['targets_after'][path] != report['targets_before'][path]
            if changed != (path in appended):
                raise CancelSplitError('target disk change does not match the saved append set', path)
        report['success'] = True
        return report
    except Exception as error:
        report['error'] = str(error)
        try:
            report['dirty_retained'] = _dirty_packages()
        except Exception as dirty_error:
            report['dirty_retained'] = 'unavailable: ' + str(dirty_error)
        raise
    finally:
        with open(directory / ('cancel_split_' + mode + '.json'), 'x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    run()
