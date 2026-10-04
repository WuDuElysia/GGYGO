"""Wire only the seven accepted Profiles into the formal default MovementSet.

Import is inert. In the coordinator's exclusive Unreal Python window:
    api = runpy.run_path('F:/ue_project/GGYGO/AAADocs/Scripts/wire_pyrios_locomotion_profiles.py')
    inspection = api['inspect']()       # read-only; inspect inspection.receipt
    result = api['apply'](inspection)   # explicit, once, in that same process

Only DA_Movement_Default may be edited/saved. Native validation is mandatory;
there is no asset creation, tuning, retry, rollback, SaveAll or report-file write.
Receipts are returned and printed for the coordinator to preserve separately.
Same-process readback is not a cold read or proof of new-source runtime/Run.
"""

import copy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import struct


PROJECT = Path('F:/ue_project/GGYGO')
SCRIPT = PROJECT / 'AAADocs/Scripts/wire_pyrios_locomotion_profiles.py'
DA_PACKAGE = '/Game/System/DA_Movement_Default'
MOVEMENT = '/Game/Characters/Player/Pyrios/Animation/Movement/'
DA_CLASS = '/Script/GGYGO.GGYGOMovementSet'
PROFILE_CLASS = '/Script/GGYGO.GGYGOLocomotionMotionProfile'
DA_BEFORE_SHA256 = '7943CDC3A9F761386EEB08E4D9785E4B98121CAB5D5FA45C4AE7A5ED8A01F678'
AUTHOR = PROJECT / 'AAADocs/Scripts/create_pyrios_walk_motion_profiles.py'
AUTHOR_SHA256 = '098C9EAEBA204F47DF5C24CA9BA3B044B6F73D2072D0430DEDF8158938AEA424'
EVIDENCE = PROJECT / 'Saved/ValidationRecords/LocomotionAssetReadback_20261003_Pawn00.json'
EVIDENCE_SHA256 = '159C5B59079F6D88860A07C2E3699755435F6EAEF0B9F1828D55735F46A345A2'

# Step, reflected property, source suffix, saved Profile hash, accepted source hash.
STEPS = (
    ('WalkStart', 'walk_start_profile', 'Walk_Start',
     '288C5AA32276089C0C40CFF78A736070E01F2C5A0FB9AA7E4FAF945EE6F81561',
     'A0F957803207E8BB53DB0CD2333F19E183B60BEFB4E3DA747B432CFA5952818D'),
    ('WalkLoop', 'walk_loop_profile', 'Walk_Loop',
     'D76850A65914DFD90DA6F9F60E98C92E34CE2DAF708C575BB2B1B1FDE19F3AD1',
     'CA56C5DF7F1F1B7282780610E5F9BCB0C28E203086A603D9F3AC02FE80D936BA'),
    ('RunLoop', 'run_loop_profile', 'Run_Loop',
     '7EB28C1AA6913938F78F9B42BF5916F9E6C829F945569DC0305550C743924F20',
     '922D51C476D9C93A4F5733FAF5E3E977F5B37D934DE85A007622AC3730CA3E88'),
    ('StartStop', 'start_stop_profile', 'Walk_Start_End',
     '38B9BC9CFF12C9BD9AC958C4F94AFF7F4B7C5792E7EA88B39D0721FDDCC5DF12',
     '4059B9A4615C9E4E4D4A3CE4E610D32B1754DD0EAF25FBBA730E9D395FB91976'),
    ('WalkStop', 'walk_stop_profile', 'Walk_End',
     '4F8B5F676DA029CD211D594FE7301A3C2CC98B4A97E197CDA1A832173A4D6A7A',
     '1DE5B73B22B0553E18823F9012BEEB4011CA730614032DA9DCDF3EC3A0B99227'),
    ('RunStop', 'run_stop_profile', 'Run_End',
     '22CAD6AC51BBB88F72AE4985FEA7E835C366D03A77427E2E109E81B9C5C0C0E8',
     '48076290557F12E8A849C061BEAFDF5B93FD178A93263C744C30B8CEE66BB93A'),
    ('TurnBack', 'turn_back_profile', 'TurnBack',
     'F513764457837B1A165BDEC1E954B0E2AEC75547D3A4E7A0E4350BC5DC8413AC',
     '71C3B14549CD17FA337B61AEED0B8311D600C7E4592A66101839BD5D0186FD41'),
)
ROOT_RECEIPTS = {
    'PyriosWalkStartMotionProfile_20261004_RootSavedReadback.json': '93CF4BF348411524FF59284056D791E9D9177B93E31582685F55A224D2B22EF4',
    'PyriosWalkLoopMotionProfile_20261004_RootAcceptance.json': '3CA377496FA96786816015473D5100B9EF94466ECBCDD80C9DC8FA98EB91A35D',
    'PyriosRunLoopMotionProfile_20261004_RootAcceptance.json': '2630E755884954D45EF90A58FD86D131E7CEECA1F4D991016362EF71F6677BBA',
    'PyriosStartStopMotionProfile_20261004_RootAcceptance.json': '4799F2E6BAB66AD1C8D79CDA4982652BE3605D2AC2E034A6E4A4A4827D54F8DD',
    'PyriosWalkStopMotionProfile_20261004_RootAcceptance.json': '9A86C82A5047A5F1CA792F3E079913311B5758CABEACC746E77750EA1C12D737',
    'PyriosRunStopMotionProfile_20261004_RootAcceptance.json': 'C9EFE1F7375053C6A387203CA81A68F82286A4318F66C7604B727AAF5411690B',
    'PyriosTurnBackMotionProfile_20261004_RootAcceptance.json': 'C80A45E16D4CB1E62FE60BCD8E9EF0486882A6BFEE42D86E9315BF7D39E48A6C',
}
CORE_PACKAGES = (
    '/Game/BP/Anim/ABP_Pyrios', MOVEMENT + 'BS_Pyrios_WalkRun',
    '/Game/Characters/Player/Pyrios/DA/DA_Pawn_Pyrios',
    '/Game/Characters/Player/Pyrios/DA/DA_InputConfig_Default',
    '/Game/Input/Mappings/IMC_Default', '/Game/Input/Mappings/IMC_MouseLook',
)
FLOAT_FIELDS = (
    'WalkSpeed', 'RunSpeed', 'WalkToRunHoldSeconds', 'WalkRunBlendInterpSpeed',
    'StartStopSelectionSeconds', 'RotationYawRate', 'MaxAcceleration',
    'BrakingDecelerationWalking', 'GroundFriction', 'RootMotionScale',
    'MaxCurveDrivenSpeed', 'TurnBackReverseInputDotThreshold', 'TurnBackMinYawDegrees',
    'TurnBackYawSettleDegrees', 'TurnBackRunOutForwardThreshold',
    'TurnBackRunOutMinSpeed', 'TurnBackDurationSeconds',
)
BOOL_FIELDS = ('bOrientRotationToMovement', 'bUseCurveDrivenSpeed')


def _require(condition, reason):
    if not condition:
        raise RuntimeError('[GGYGO.MovementSetWiring] ' + reason)


def _object_path(package):
    return package + '.' + package.rsplit('/', 1)[1]


def _file(package):
    _require(package.startswith('/Game/') and '.' not in package and ':' not in package,
             'unexpected package path: ' + package)
    return PROJECT / 'Content' / (package[6:] + '.uasset')


def _profile_package(step):
    return MOVEMENT + 'Profiles/DA_LocomotionMotionProfile_Pyrios_' + step


def _sha(path):
    _require(path.is_file(), 'required file missing: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _check_files(expected):
    for name, digest in expected.items():
        _require(_sha(Path(name)) == digest, 'protected file changed: ' + name)


def _fixed_files():
    expected = {str(AUTHOR): AUTHOR_SHA256, str(EVIDENCE): EVIDENCE_SHA256}
    for step, _, source, profile_hash, source_hash in STEPS:
        expected[str(_file(_profile_package(step)))] = profile_hash
        expected[str(_file(MOVEMENT + 'Avatar_Male_Size03_Pyrois_Ani_' + source))] = source_hash
    for name, digest in ROOT_RECEIPTS.items():
        expected[str(PROJECT / 'Saved/ValidationRecords' / name)] = digest
    _check_files(expected)
    for package in CORE_PACKAGES:
        expected[str(_file(package))] = _sha(_file(package))
    # Preserve these original historical records as well as the accepted assets.
    for name in ('PyriosWalkStartMotionProfile_20261004_Result.json',
                 'PyriosWalkStartMotionProfile_20261004_Readback_R1.json'):
        path = PROJECT / 'Saved/ValidationRecords' / name
        expected[str(path)] = _sha(path)
    return expected


def _dirty(ue):
    utils = ue.EditorLoadingAndSavingUtils
    return {'content': sorted(p.get_path_name() for p in utils.get_dirty_content_packages()),
            'maps': sorted(p.get_path_name() for p in utils.get_dirty_map_packages())}


def _scalars(da):
    # Installed Python ResolvePropertyName preserves native names if not mapped;
    # FindEditorPropertyImpl then uses UClass::FindPropertyByName. No alias guesses.
    result = {}
    for field in FLOAT_FIELDS:
        value = da.get_editor_property(field)
        _require(type(value) is float and math.isfinite(value), 'invalid float: ' + field)
        bits = struct.pack('<f', value)
        _require(struct.unpack('<f', bits)[0] == value, 'non-float32 value: ' + field)
        result[field] = {'value': value, 'float32_le': bits.hex()}
    for field in BOOL_FIELDS:
        value = da.get_editor_property(field)
        _require(type(value) is bool, 'invalid bool: ' + field)
        result[field] = value
    _require(result['WalkToRunHoldSeconds']['value'] == 1.5,
             'existing hold threshold differs from confirmed 1.5 seconds; do not retune')
    _require(result['bUseCurveDrivenSpeed'] is True,
             'existing curve mode differs from confirmed configuration; do not switch mode')
    return result


def _refs(da):
    return {prop: None if (obj := da.get_editor_property(prop)) is None else obj.get_path_name()
            for _, prop, _, _, _ in STEPS}


def _load(ue, assets, package, expected_class):
    obj = assets.load_asset(_object_path(package))
    _require(obj is not None and obj.get_path_name() == _object_path(package)
             and obj.get_class().get_path_name() == expected_class,
             'asset identity/type mismatch: ' + _object_path(package))
    return obj


def _validate(ue, validator, obj):
    # IsObjectValid is a public UFUNCTION: return enum plus out errors/warnings.
    # Observe the actual Python return shape on accepted Profiles before any write.
    raw = validator.is_object_valid(obj, ue.DataValidationUsecase.MANUAL)
    _require(type(raw) is tuple and len(raw) == 3,
             'unexpected IsObjectValid Python result shape: ' + repr(type(raw)))
    state, errors, warnings = raw
    _require(isinstance(state, ue.DataValidationResult)
             and isinstance(errors, (list, tuple, ue.Array))
             and isinstance(warnings, (list, tuple, ue.Array)),
             'unexpected native validation enum/issue-array types')
    return {'object': obj.get_path_name(), 'result': str(state),
            'valid': state == ue.DataValidationResult.VALID,
            'invalid': state == ue.DataValidationResult.INVALID,
            'errors': [str(x) for x in errors], 'warnings': [str(x) for x in warnings],
            'return_shape': [type(x).__name__ for x in raw]}


def _require_valid(validation):
    _require(validation['valid'] and not validation['errors'],
             'native IsDataValid did not pass: ' + json.dumps(validation, ensure_ascii=False))


def _emit(receipt):
    print('PYRIOS_MOVEMENT_SET_WIRING ' + json.dumps(receipt, ensure_ascii=False, allow_nan=False))


class Inspection:
    """One process-local read-only inspection; holds exact objects until apply ends."""

    def __init__(self, ue, assets, validator, da, profiles, protected, receipt):
        self._ue, self._assets, self._validator = ue, assets, validator
        self._da, self._profiles = da, profiles
        self._protected, self._baseline = dict(protected), copy.deepcopy(receipt)
        self._used = False

    @property
    def receipt(self):
        return copy.deepcopy(self._baseline)


def inspect():
    """Read only; returns an Inspection with original refs/scalars and API probe."""
    import unreal as ue

    receipt = {'schema': 'GGYGO.MovementSetWiring/v1', 'mode': 'inspect',
               'status': 'running', 'phase': 'file_preconditions', 'pid': os.getpid(),
               'utc': datetime.now(timezone.utc).isoformat(), 'target': _object_path(DA_PACKAGE),
               'script_sha256': _sha(SCRIPT), 'save_called': False,
               'cold_read_performed': False, 'production_run_verified': False,
               'new_source_runtime_verified': False}
    try:
        protected = _fixed_files()
        receipt['protected_files'] = protected
        receipt['target_sha256_before'] = _sha(_file(DA_PACKAGE))
        _require(receipt['target_sha256_before'] == DA_BEFORE_SHA256,
                 'formal DA differs from original unwired disk baseline')
        receipt['phase'] = 'readonly_api_probe_and_load'
        assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        validator = ue.get_editor_subsystem(ue.EditorValidatorSubsystem)
        _require(assets is not None and validator is not None, 'required native Editor subsystem unavailable')
        _require(callable(assets.load_asset) and callable(assets.save_loaded_asset)
                 and callable(validator.is_object_valid), 'required public Python API unavailable')
        before = _dirty(ue)
        receipt['dirty_before'] = before
        packages = set(CORE_PACKAGES) | {DA_PACKAGE}
        for step, _, source, _, _ in STEPS:
            packages.update((_profile_package(step), MOVEMENT + 'Avatar_Male_Size03_Pyrois_Ani_' + source))
        _require(not packages.intersection(before['content'] + before['maps']),
                 'target/protected package already dirty')
        profiles, validations = {}, {}
        for step, prop, _, _, _ in STEPS:
            obj = _load(ue, assets, _profile_package(step), PROFILE_CLASS)
            _require(obj.get_editor_property('bLoop') is (step in ('WalkLoop', 'RunLoop')),
                     'Profile Loop mismatch: ' + step)
            validations[prop] = _validate(ue, validator, obj)
            _require_valid(validations[prop])
            profiles[prop] = obj
        receipt['profile_validations'] = validations
        da = _load(ue, assets, DA_PACKAGE, DA_CLASS)
        _require(callable(da.modify), 'required public UObject.modify API unavailable')
        receipt['scalars_before'] = _scalars(da)
        receipt['refs_before'] = _refs(da)
        _require(all(x is None for x in receipt['refs_before'].values()),
                 'formal DA is not the original seven-null-reference object; do not overwrite')
        receipt['movement_set_validation_before'] = _validate(ue, validator, da)
        initial = receipt['movement_set_validation_before']
        _require(initial['invalid'] and initial['errors']
                 and any('WalkStartProfile' in x for x in initial['errors']),
                 'unwired curve DA did not expose its actual missing-Profile validation failure')
        receipt['dirty_after'] = _dirty(ue)
        _require(receipt['dirty_after'] == before, 'read-only load/validation changed dirty set')
        _check_files(protected)
        _require(_sha(_file(DA_PACKAGE)) == DA_BEFORE_SHA256, 'read-only inspection changed target disk')
        receipt.update(status='inspect_passed', phase='readonly_complete')
        ticket = Inspection(ue, assets, validator, da, profiles, protected, receipt)
        _emit(receipt)
        return ticket
    except Exception as error:
        receipt.update(status='failed', error=str(error))
        _emit(receipt)
        raise


def apply(inspection):
    """Explicit single attempt using exact objects/values from inspect; saves one DA."""
    _require(type(inspection) is Inspection and not inspection._used,
             'requires an unused Inspection returned by this script in the same process')
    inspection._used = True  # A failed attempt cannot be silently retried with this ticket.
    ue, assets, validator = inspection._ue, inspection._assets, inspection._validator
    da, profiles = inspection._da, inspection._profiles
    original = inspection._baseline
    receipt = copy.deepcopy(original)
    receipt.update(mode='apply', status='running', phase='recheck_original_inspection',
                   utc=datetime.now(timezone.utc).isoformat(), attempted_properties=[],
                   applied_properties=[], save_called=False, save_returned=False)
    try:
        _require(original['pid'] == os.getpid() and original['status'] == 'inspect_passed'
                 and original['script_sha256'] == _sha(SCRIPT), 'inspection process/script changed')
        _check_files(inspection._protected)
        _require(_sha(_file(DA_PACKAGE)) == DA_BEFORE_SHA256, 'target changed since inspection')
        _require(_dirty(ue) == original['dirty_before'], 'dirty set changed since inspection')
        _require(_load(ue, assets, DA_PACKAGE, DA_CLASS) == da, 'original DA object replaced')
        _require(_scalars(da) == original['scalars_before'] and _refs(da) == original['refs_before'],
                 'original DA values/refs changed since inspection')
        wanted = {}
        for step, prop, _, _, _ in STEPS:
            obj = _load(ue, assets, _profile_package(step), PROFILE_CLASS)
            _require(obj == profiles[prop] and obj.get_editor_property('bLoop') is (step in ('WalkLoop', 'RunLoop')),
                     'original Profile object/Loop changed: ' + step)
            wanted[prop] = _object_path(_profile_package(step))
        _require(_dirty(ue) == original['dirty_before'], 'prewrite loads changed dirty set')
        _check_files(inspection._protected)
        receipt['expected_refs'] = wanted
        expected_dirty = copy.deepcopy(original['dirty_before'])
        expected_dirty['content'] = sorted(expected_dirty['content'] + [DA_PACKAGE])
        receipt['phase'] = 'mark_owned_package_dirty'
        modified = da.modify(True)
        receipt['modify_transaction_saved'] = modified
        # False means no transaction was saved; the native call still marks dirty.
        _require(type(modified) is bool, 'unexpected UObject.modify return type')
        _require(_dirty(ue) == expected_dirty, 'Modify did not dirty exactly default DA')
        receipt['phase'] = 'set_seven_references'
        for _, prop, _, _, _ in STEPS:
            receipt['attempted_properties'].append(prop)
            da.set_editor_property(prop, profiles[prop])
            receipt['applied_properties'].append(prop)
        receipt['phase'] = 'native_validation_before_save'
        receipt['refs_before_save'] = _refs(da)
        _require(receipt['refs_before_save'] == wanted, 'seven assigned refs differ')
        _require(_scalars(da) == original['scalars_before'], 'non-Profile values changed before save')
        receipt['validation_before_save'] = _validate(ue, validator, da)
        _require_valid(receipt['validation_before_save'])
        receipt['dirty_before_save'] = _dirty(ue)
        _require(receipt['dirty_before_save'] == expected_dirty, 'dirty delta is not exactly default DA')
        _check_files(inspection._protected)
        _require(_sha(_file(DA_PACKAGE)) == DA_BEFORE_SHA256, 'target disk changed before exact save')
        receipt['phase'] = 'save_only_default_da'
        receipt['save_called'] = True
        saved = assets.save_loaded_asset(da, False)
        receipt['save_returned'] = saved
        _require(type(saved) is bool and saved, 'native SaveLoadedAsset failed')
        receipt['phase'] = 'same_process_readback'
        _require(_load(ue, assets, DA_PACKAGE, DA_CLASS) == da, 'saved DA object replaced')
        receipt['refs_after'] = _refs(da)
        receipt['scalars_after'] = _scalars(da)
        _require(receipt['refs_after'] == wanted and receipt['scalars_after'] == original['scalars_before'],
                 'saved refs/non-Profile readback differs')
        receipt['validation_after'] = _validate(ue, validator, da)
        _require_valid(receipt['validation_after'])
        receipt['dirty_after'] = _dirty(ue)
        _require(receipt['dirty_after'] == original['dirty_before'], 'post-save dirty set differs')
        _check_files(inspection._protected)
        receipt['target_sha256_after'] = _sha(_file(DA_PACKAGE))
        _require(receipt['target_sha256_after'] != DA_BEFORE_SHA256, 'successful wiring did not change saved package')
        receipt.update(status='passed', phase='saved_same_process_readback_complete')
        _emit(receipt)
        return receipt
    except Exception as error:
        receipt.update(status='failed', error=str(error))
        _emit(receipt)
        raise  # Preserve actual unsaved/saved state; never rollback, retry or report success.
    finally:
        inspection._da = None
        inspection._profiles.clear()
        inspection._assets = inspection._validator = inspection._ue = None
