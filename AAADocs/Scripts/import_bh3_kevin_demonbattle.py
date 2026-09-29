"""Import the isolated BH3 Kevin DemonBattle package without overwriting assets.

Outside UE: python import_bh3_kevin_demonbattle.py --stage audit
UE Cmd: py "F:/ue_project/GGYGO/AAADocs/Scripts/import_bh3_kevin_demonbattle.py" --stage smoke
After reviewing smoke preview: repeat with --stage all.
Uses adjacent generic FBX reader, never edits source FBX or applies Pyrios processing.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fbx_bin_reader import FbxReader, decode_placeholder
from fbx_anim_extract import build_index, obj_name, FBXTIME

SOURCE = Path(r'F:\AnimeStudio\Exports\BH3\Animator\Kevin\05_BOSS_411_DemonBattle')
BASE = '/Game/Characters/Boss/Kevin/DemonBattle'
MESH = BASE + '/Mesh/SK_Kevin_DemonBattle'
SKELETON = MESH + '_Skeleton'
OUT = Path(__file__).resolve().parents[2] / 'Saved/Codex'
OWNER = 'BH3_Kevin_DemonBattle_v1'

def write(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def string(value):
    return value.split(b'\0')[0].decode('utf-8') if isinstance(value, bytes) else value

def properties(node):
    p = next((c for c in node.children if c.name == 'Properties70'), None)
    return {string(c.props[0]): [string(v) for v in c.props[4:]] for c in p.children} if p else {}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect_fbx(path):
    reader = FbxReader(str(path))
    try:
        assert reader.read_header() < 7500, 'Generic reader only supports 32-bit FBX records'
        roots = reader.parse()
        top = {n.name: n for n in roots}
        idx = build_index(roots)
        models = idx['model_id2name']
        assert len(set(models.values())) == len(models), 'Duplicate FBX model names'
        hierarchy = {}
        kinds = {}
        for ident, name in models.items():
            hierarchy[name] = next((models[p] for p, _ in idx['parent_conns'][ident] if p in models), None)
            kinds[name] = string(idx['id2node'][ident].props[2])
        takes = []
        if 'Takes' in top:
            for n in top['Takes'].children:
                if n.name == 'Take':
                    takes.append({'name': string(n.props[0]), **{c.name: [string(v) for v in c.props] for c in n.children}})
        key_min, key_max = None, None
        for n in idx['curves'].values():
            for c in n.children:
                if c.name == 'KeyTime':
                    times = decode_placeholder(reader.f, c.props[0])
                    if times:
                        key_min = min(times) if key_min is None else min(key_min, min(times))
                        key_max = max(times) if key_max is None else max(key_max, max(times))
        return {'version':reader.version, 'hierarchy':hierarchy, 'kinds':kinds,
                'globals':properties(top['GlobalSettings']), 'takes':takes,
                'key_range_seconds':None if key_min is None else [key_min/FBXTIME,key_max/FBXTIME],
                'materials':[obj_name(n) for n in top['Objects'].children if n.name == 'Material']}
    finally:
        reader.close()

def audit():
    bh3 = SOURCE.parents[2]
    files = sorted(p for p in bh3.rglob('*') if p.is_file())
    groups = collections.defaultdict(list)
    for p in files:
        parts = p.relative_to(bh3).parts
        group = '/'.join(parts[:3] if parts[0] == 'Animator' else parts[:2])
        groups[group].append(p)
    inventory = {k:{'files':len(v),'bytes':sum(p.stat().st_size for p in v),
                    'extensions':dict(collections.Counter(p.suffix for p in v))} for k,v in groups.items()}
    settings = json.loads((SOURCE/'anim_settings.json').read_text(encoding='utf-8-sig'))
    model = inspect_fbx(SOURCE/'BOSS_411.fbx')
    clips = []
    for entry in settings['clips']:
        path = SOURCE / entry['fbx']
        data = inspect_fbx(path)
        meta = json.loads((SOURCE/entry['json']).read_text(encoding='utf-8-sig'))
        clip = meta['clip']
        differences = {n:[model['hierarchy'].get(n),data['hierarchy'].get(n)]
                       for n in model['hierarchy'].keys() | data['hierarchy'].keys()
                       if n not in model['hierarchy'] or n not in data['hierarchy'] or model['hierarchy'][n] != data['hierarchy'][n]}
        # Animation files replace the seven mesh nodes with LimbNode placeholders.
        # Require the entire named hierarchy, units and axes to match, not a name prefix.
        coordinate_keys = ['UpAxis','UpAxisSign','FrontAxis','FrontAxisSign','CoordAxis','CoordAxisSign','UnitScaleFactor']
        coordinate_match = all(data['globals'][k] == model['globals'][k] for k in coordinate_keys)
        clips.append({'name':entry['name'], 'asset_name':'AS_'+re.sub('[^a-zA-Z0-9_]', '_',entry['name']),
                      'fbx':entry['fbx'], 'json':entry['json'], 'sha256':sha(path),
                      'compatible':not differences and coordinate_match, 'hierarchy_differences':differences,
                      'coordinate_match':coordinate_match, 'sample_rate':clip['sampleRate'],
                      'loop':clip['muscleClip']['loopTime'], 'json_range_seconds':[clip['muscleClip']['startTime'],clip['muscleClip']['stopTime']],
                      'key_range_seconds':data['key_range_seconds'], 'takes':data['takes']})
    assert settings['clipCount'] == len(clips) == 79
    assert len({c['asset_name'].lower() for c in clips}) == len(clips), 'Destination collision'
    assert {p.name for p in (SOURCE/'anim').glob('*.fbx')} == {Path(c['fbx']).name for c in clips}, 'Unindexed FBX'
    result = {'source':str(SOURCE), 'inventory':inventory, 'inventory_files':len(files),
              'model':model, 'model_sha256':sha(SOURCE/'BOSS_411.fbx'), 'clips':clips,
              'source_settings':{k:v for k,v in settings.items() if k != 'clips'}}
    write('bh3_demonbattle_source_audit.json',result)
    return result

def set_properties(obj, **values):
    for name,value in values.items():
        obj.set_editor_property(name,value)

def options(unreal, animation, skeleton=None, rate=60):
    ui = unreal.FbxImportUI()
    set_properties(ui, automated_import_should_detect_type=False,
                   mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION if animation else unreal.FBXImportType.FBXIT_SKELETAL_MESH,
                   import_as_skeletal=True, import_mesh=not animation, import_animations=animation,
                   import_materials=False, import_textures=False, create_physics_asset=False,
                   skeleton=skeleton, override_full_name=True)
    for data in [ui.skeletal_mesh_import_data, ui.anim_sequence_import_data]:
        set_properties(data, import_uniform_scale=1.0, import_translation=unreal.Vector(0,0,0),
                       import_rotation=unreal.Rotator(0,0,0), convert_scene=True,
                       convert_scene_unit=True, force_front_x_axis=False)
    set_properties(ui.skeletal_mesh_import_data, update_skeleton_reference_pose=False,
                   use_t0_as_ref_pose=False, import_meshes_in_bone_hierarchy=True, import_morph_targets=True)
    set_properties(ui.anim_sequence_import_data, use_default_sample_rate=False, custom_sample_rate=int(rate),
                   animation_length=unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
                   snap_to_closest_frame_boundary=True, import_bone_tracks=True,
                   import_custom_attribute=True, preserve_local_transform=False)
    return ui

def existing(unreal, path, expected_class, digest, skeleton=None):
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        return None
    obj = unreal.load_asset(path)
    assert isinstance(obj, expected_class), 'Existing asset has wrong type: '+path
    assert unreal.EditorAssetLibrary.get_metadata_tag(obj,'BH3.ImportOwner') == OWNER, 'Unowned existing asset: '+path
    assert unreal.EditorAssetLibrary.get_metadata_tag(obj,'BH3.SourceSHA256') == digest, 'Source changed: '+path
    if skeleton:
        assert obj.get_editor_property('skeleton') == skeleton, 'Skeleton mismatch: '+path
    return obj

def import_one(unreal, source, destination, ui, digest, expected_class):
    assert not unreal.EditorAssetLibrary.does_asset_exist(destination), 'Refusing overwrite'
    task = unreal.AssetImportTask()
    set_properties(task, filename=str(source), destination_path=destination.rsplit('/',1)[0],
                   destination_name=destination.rsplit('/',1)[1], automated=True, replace_existing=False,
                   replace_existing_settings=False, save=False, options=ui, factory=unreal.FbxFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    results = task.get_objects()
    candidates = [x for x in results if isinstance(x, expected_class)]
    assert len(candidates) == 1, 'Expected one imported asset: '+str(task.imported_object_paths)
    obj = candidates[0]
    actual = obj.get_path_name().split('.')[0]
    if actual != destination:
        assert not unreal.EditorAssetLibrary.does_asset_exist(destination)
        assert unreal.EditorAssetLibrary.rename_asset(actual,destination)
    unreal.EditorAssetLibrary.set_metadata_tag(obj,'BH3.ImportOwner',OWNER)
    unreal.EditorAssetLibrary.set_metadata_tag(obj,'BH3.SourceSHA256',digest)
    unreal.EditorAssetLibrary.set_metadata_tag(obj,'BH3.SourceFile',str(source))
    return obj

def run(stage):
    data = audit()
    if stage == 'audit':
        print('BH3 audit: %d files, %d/%d compatible clips' % (data['inventory_files'],sum(c['compatible'] for c in data['clips']),len(data['clips'])))
        return
    import unreal
    report = {'stage':stage,'mesh':MESH,'skeleton':SKELETON,'clips':[],'complete':False}
    report_name = 'bh3_demonbattle_'+stage+'_report.json'
    cvar = 'Interchange.FeatureFlags.Import.FBX'
    prior = unreal.SystemLibrary.get_console_variable_int_value(cvar)
    try:
        unreal.SystemLibrary.execute_console_command(None,cvar+' 0')
        mesh = existing(unreal,MESH,unreal.SkeletalMesh,data['model_sha256'])
        if mesh is None:
            assert not unreal.EditorAssetLibrary.does_asset_exist(SKELETON), 'Skeleton destination already exists'
            mesh = import_one(unreal,SOURCE/'BOSS_411.fbx',MESH,options(unreal,False),data['model_sha256'],unreal.SkeletalMesh)
            skeleton = mesh.get_editor_property('skeleton')
            assert skeleton.get_path_name().split('.')[0] == SKELETON, 'Unexpected skeleton path'
            unreal.EditorAssetLibrary.set_metadata_tag(skeleton,'BH3.ImportOwner',OWNER)
            unreal.EditorAssetLibrary.save_loaded_asset(skeleton,only_if_is_dirty=False)
            unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False)
        skeleton = mesh.get_editor_property('skeleton')
        assert skeleton.get_path_name().split('.')[0] == SKELETON
        assert unreal.EditorAssetLibrary.get_metadata_tag(skeleton,'BH3.ImportOwner') == OWNER
        report['material_slots'] = [str(m.material_slot_name) for m in mesh.materials]
        report['bounds'] = str(mesh.get_bounds())
        selection = [c for c in data['clips'] if c['name'] == 'BOSS_411_Ani_StandBy'] if stage == 'smoke' else data['clips']
        if stage == 'all':
            smoke = json.loads((OUT/'bh3_demonbattle_smoke_report.json').read_text(encoding='utf-8'))
            assert smoke['complete'], 'Run and review smoke stage first'
        for c in selection:
            row = {'source':c['fbx'],'asset':BASE+'/Animation/'+c['asset_name']}
            report['clips'].append(row)
            if not c['compatible']:
                row['status']='nonmatching'; continue
            if c['key_range_seconds'] is None:
                row['status']='source_empty'
                row['reason']='Source FBX has no animation curves; no AnimSequence generated.'
                write(report_name,report)
                continue
            try:
                seq = existing(unreal,row['asset'],unreal.AnimSequence,c['sha256'],skeleton)
                row['status'] = 'existing_verified' if seq else 'imported'
                if seq is None:
                    seq = import_one(unreal,SOURCE/c['fbx'],row['asset'],options(unreal,True,skeleton,c['sample_rate']),c['sha256'],unreal.AnimSequence)
                    assert seq.get_editor_property('skeleton') == skeleton
                    set_properties(seq, enable_root_motion=False, force_root_lock=False)
                    unreal.EditorAssetLibrary.set_metadata_tag(seq,'BH3.SourceLoopTime',str(c['loop']))
                    unreal.EditorAssetLibrary.save_loaded_asset(seq,only_if_is_dirty=False)
                row['duration'] = seq.get_play_length()
                row['skeleton'] = seq.get_editor_property('skeleton').get_path_name()
                row['enable_root_motion'] = seq.get_editor_property('enable_root_motion')
                row['force_root_lock'] = seq.get_editor_property('force_root_lock')
                assert row['duration'] > 0
                unreal.log('BH3_IMPORT '+row['status']+' '+row['asset'])
            except Exception:
                row['status']='failed'; row['error']=traceback.format_exc()
                unreal.log_error(row['error'])
                if stage == 'smoke': raise
            finally:
                write(report_name,report)
        unreal.EditorAssetLibrary.save_loaded_asset(skeleton,only_if_is_dirty=True)
        report['complete'] = all(c['status'] in ('imported','existing_verified') for c in report['clips'])
        report['counts'] = dict(collections.Counter(c['status'] for c in report['clips']))
        report['importable_complete'] = all(c['status'] in ('imported','existing_verified','source_empty') for c in report['clips'])
        report['index_fully_imported'] = report['complete']
    except Exception:
        report['error']=traceback.format_exc()
        raise
    finally:
        unreal.SystemLibrary.execute_console_command(None,cvar+' '+str(prior))
        write(report_name,report)
        unreal.log('BH3_IMPORT_REPORT '+str(OUT/report_name))

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',choices=['audit','smoke','all'],default='audit')
    run(parser.parse_args().stage)
