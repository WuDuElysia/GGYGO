"""BH3 Stage source audit and controlled scene import (UE 5.8).

Offline: python -B import_bh3_stages.py audit [--stage P1|P3|all]
UE Python, only in the coordinator's exclusive window:
    import import_bh3_stages as stages
    stages.import_geometry('P1')
    # Or execute this file with: geometry --stage P1
Standard full Editor, only in the coordinator's isolated process window:
    -ExecutePythonScript=".../import_bh3_stages.py editor_api_preflight --stage P3"
    -ExecutePythonScript=".../import_bh3_stages.py editor_p1_preflight --stage P1 --failed-manifest ... --empty-map-sha256 ... --saved-scene-backup ..."
    -ExecutePythonScript=".../import_bh3_stages.py editor_continue_geometry --stage P3 --failed-report ... --empty-map-backup ..."
    -ExecutePythonScript=".../import_bh3_stages.py continue_geometry --stage P1 --failed-manifest ... --empty-map-sha256 ... --saved-scene-backup ..."
These Editor entries require -unattended -nowrite and
    -DisablePlugins=ModelContextProtocol,MCPClientToolset,AllToolsets
The native PythonScript Commandlet does not provide the required static mesh
editor subsystem; it is not an asset execution mode for this importer.

The geometry phase deliberately reports materials, lighting, collision and
playability as unresolved. It does not synthesize Unity shaders or colliders.
Importing geometry is a partial delivery, never a complete restoration claim.
Each Stage keeps its native SceneImport entry at the Stage root; geometry is
created directly in StaticMeshes using Interchange's asset type subfolders.
Later material, texture and source collider resources belong to Materials,
Textures and Collision respectively; this phase does not create those assets.
"""

import argparse
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import traceback
import uuid

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = SCRIPT_DIR.parent.parent
SOURCE = Path('F:/AnimeStudio/Exports/BH3/Stage')
OWNER = 'GGYGO.BH3.Stage.Geometry.v1'
STAGES = {'P1': 'Stage_KevinBoss_P1', 'P3': 'Stage_KevinBoss_P3'}
FBX_MAGIC = b'Kaydara FBX Binary  \x00\x1a\x00'
NULL_RECORD = bytes(13)
# This explicit exception identifies one approved failed result, not a generic
# overwrite policy. Normal imports continue to require absent destinations.
SAVED_PARTIAL_P1 = {
    'run_directory': 'P1_54a9905b74d54ca5afc6760a7076e9b3',
    'scene_bytes': 15427,
    'scene_sha256': '85f1db4a1ef0fec5923edcdb4a50f7d3ca2bb7e6eac7b8119da102b04da0a70f',
    'map_sha256': '28068d502646ab2a82d2f00cfbaa064a814c0bcd8f16e1663b071d0845a5099c',
}
OWNED_EMPTY_P3 = {
    'run_directory': 'P3_f67ef3791f7f485e9681073bd0fc8bad',
    'map_bytes': 6387,
    'map_sha256': 'e81ed6996a01b36b8cd32d3052ac007595bd97f8b1f92761d622416507b0442f',
}

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from fbx_bin_reader import FbxReader, decode_placeholder, prop_str
from fbx_anim_extract import build_index, obj_name


def require(condition, message):
    if not condition:
        raise RuntimeError('BH3.Stage: ' + message)


def stage_paths(stage, source_root=SOURCE):
    require(stage in STAGES, 'unknown stage ' + str(stage))
    name = STAGES[stage]
    return (Path(source_root) / name,
            '/Game/Environments/BH3/Stage/' + name,
            '/Game/Map/BH3/L_KevinBoss_' + stage)


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def properties(node):
    return {prop_str(p.props[0]): [prop_str(v) if isinstance(v, bytes) else v for v in p.props[4:]]
            for group in node.children if group.name == 'Properties70'
            for p in group.children if p.name == 'P'}


def identity_name(kind, object_id, original):
    # Identity comes from the FBX ID; the readable suffix is not a lookup key.
    suffix = re.sub(r'[^A-Za-z0-9_]', '_', original).strip('_')[:64]
    return {'Model': 'N', 'Geometry': 'G', 'Material': 'M'}[kind] + str(object_id) + ('_' + suffix if suffix else '')


def _array(reader, node, child_name):
    matches = [c for c in node.children if c.name == child_name]
    require(len(matches) == 1 and len(matches[0].props) == 1,
            f'{node.name} {obj_name(node)} requires one {child_name} array')
    return decode_placeholder(reader.f, matches[0].props[0])


def _geometry(reader, node):
    vertices = _array(reader, node, 'Vertices')
    indices = _array(reader, node, 'PolygonVertexIndex')
    require(len(vertices) % 3 == 0 and all(math.isfinite(v) for v in vertices),
            'invalid vertices in ' + obj_name(node))
    sizes, size = [], 0
    for index in indices:
        require(0 <= (index if index >= 0 else -index - 1) < len(vertices) // 3,
                'invalid polygon vertex in ' + obj_name(node))
        size += 1
        if index < 0:
            require(size >= 3, 'degenerate polygon in ' + obj_name(node))
            sizes.append(size)
            size = 0
    require(size == 0 and sizes, 'unfinished/empty polygon list in ' + obj_name(node))
    layers = [c for c in node.children if c.name == 'LayerElementMaterial']
    require(len(layers) == 1, 'unsupported material layers in ' + obj_name(node))
    layer = layers[0]
    values = {c.name: c.props for c in layer.children}
    mapping = prop_str(values['MappingInformationType'][0])
    reference = prop_str(values['ReferenceInformationType'][0])
    require(mapping in ('AllSame', 'ByPolygon') and reference == 'IndexToDirect',
            f'unsupported material mapping {mapping}/{reference} in {obj_name(node)}')
    material_indices = _array(reader, layer, 'Materials')
    require(len(material_indices) == (1 if mapping == 'AllSame' else len(sizes)),
            'material index count mismatch in ' + obj_name(node))
    return {'vertices': len(vertices) // 3, 'polygons': len(sizes),
            'triangles': sum(n - 2 for n in sizes),
            'bounds': [[min(vertices[a::3]), max(vertices[a::3])] for a in range(3)],
            'material_mapping': mapping,
            'used_material_indices': sorted(set(material_indices)),
            'material_polygon_counts': dict(collections.Counter(material_indices))}


def audit_stage(stage, source_root=SOURCE):
    """Read source evidence; missing shader/light/collider data stays visible."""
    folder, asset_root, map_path = stage_paths(stage, source_root)
    fbx = folder / (folder.name + '.fbx')
    require(fbx.is_file(), 'missing source ' + str(fbx))
    reader = FbxReader(fbx)
    try:
        roots = reader.parse()
        require(reader.version == 7300, f'{fbx}: unsupported FBX version {reader.version}')
        top = {n.name: n for n in roots}
        require('Objects' in top and 'Connections' in top and 'GlobalSettings' in top,
                'missing FBX scene sections in ' + str(fbx))
        ids = [n.props[0] for n in top['Objects'].children if n.props and isinstance(n.props[0], int)]
        require(len(ids) == len(set(ids)), 'duplicate FBX object IDs in ' + str(fbx))
        index = build_index(roots)
        objects = index['id2node']
        globals_ = properties(top['GlobalSettings'])
        require(globals_.get('UnitScaleFactor') == [1.0],
                'unit convention changed; review source ' + str(fbx))
        expected_axes = {'UpAxis': 1, 'UpAxisSign': 1, 'FrontAxis': 2,
                         'FrontAxisSign': 1, 'CoordAxis': 0, 'CoordAxisSign': 1}
        require(all(globals_.get(k) == [v] for k, v in expected_axes.items()),
                'axis convention changed; review source ' + str(fbx))
        require(not index['curves'], 'animated Stage requires an explicit animation scope')
        require(not any(n.name == 'Deformer' for n in objects.values()),
                'skinned Stage requires an explicit skeletal scope')
        names = {str(i): identity_name(n.name, i, obj_name(n))
                 for i, n in objects.items() if n.name in ('Model', 'Geometry', 'Material')}
        geometries = {str(i): dict(_geometry(reader, n), name=obj_name(n), import_name=names[str(i)])
                      for i, n in objects.items() if n.name == 'Geometry'}
        materials = {}
        for i, n in objects.items():
            if n.name != 'Material':
                continue
            material_file = folder / 'Materials' / (obj_name(n) + '.json')
            require(material_file.is_file(), 'missing material JSON ' + str(material_file))
            data = json.loads(material_file.read_text(encoding='utf-8-sig'))
            textures = []
            for parameter, setting in data['m_SavedProperties']['m_TexEnvs'].items():
                ref = setting['m_Texture']
                if ref['IsNull']:
                    continue
                texture_name = ref['Name']
                path = folder / (texture_name + '.png') if texture_name else None
                textures.append({'parameter': parameter, 'reference': ref,
                                 'scale': setting['m_Scale'], 'offset': setting['m_Offset'],
                                 'file': str(path) if path else None,
                                 'present': bool(path and path.is_file())})
            materials[str(i)] = {'name': obj_name(n), 'import_name': names[str(i)],
                                 'json': str(material_file), 'shader': data['m_Shader'],
                                 'textures': textures}
        models = {}
        for i, n in objects.items():
            if n.name != 'Model':
                continue
            parents = [p for p, prop in index['parent_conns'][i]
                       if prop is None and (p == 0 or objects.get(p) and objects[p].name == 'Model')]
            require(len(parents) == 1, f'model {i} requires exactly one parent')
            children = [c for c, prop in index['child_conns'][i] if prop is None]
            geometry = [str(c) for c in children if objects[c].name == 'Geometry']
            slots = [str(c) for c in children if objects[c].name == 'Material']
            require(prop_str(n.props[2]) in ('Null', 'Mesh'), f'unsupported model type for {i}')
            require(len(geometry) == (1 if prop_str(n.props[2]) == 'Mesh' else 0),
                    f'model {i} has unexpected geometry connections')
            for g in geometry:
                require(all(0 <= m < len(slots) for m in geometries[g]['used_material_indices']),
                        f'model {i} material index exceeds its {len(slots)} slots')
            models[str(i)] = {'name': obj_name(n), 'import_name': names[str(i)],
                              'parent': str(parents[0]), 'geometry': geometry,
                              'material_slots': slots, 'properties': properties(n)}
        root_ids = [i for i, m in models.items() if m['parent'] == '0']
        require(len(root_ids) == 1, 'scene requires one source root')
        for i in models:
            seen, cursor = set(), i
            while cursor != '0':
                require(cursor in models and cursor not in seen, f'invalid model hierarchy at {i}')
                seen.add(cursor)
                cursor = models[cursor]['parent']
        files = sorted(p for p in folder.rglob('*') if p.is_file())
        require(all((folder / Path(prop_str(c.props[0]).replace('\\', '/')).name).is_file()
                    for n in objects.values() if n.name in ('Texture', 'Video')
                    for c in n.children if c.name in ('FileName', 'Filename', 'RelativeFilename') and c.props),
                'FBX references a missing texture in ' + str(fbx))
        return {'stage': stage, 'source': str(fbx), 'source_sha256': file_hash(fbx),
                'asset_root': asset_root, 'map': map_path,
                'files': dict(collections.Counter(p.suffix.lower() for p in files)),
                'globals': globals_, 'models': models, 'geometries': geometries,
                'materials': materials, 'identity_names': names,
                'root_id': root_ids[0],
                'unresolved_texture_refs': [dict(t, material=m['name']) for m in materials.values()
                                           for t in m['textures'] if not t['present']],
                'collision_named_nodes': [i for i, m in models.items() if 'collision' in m['name'].lower()],
                'source_light_count': sum(n.name == 'NodeAttribute' and len(n.props) > 2
                                          and prop_str(n.props[2]) == 'Light' for n in objects.values()),
                'restoration_complete': False}
    finally:
        reader.close()


def audit_summary(audit):
    return {'stage': audit['stage'], 'files': audit['files'],
            'model_nodes': len(audit['models']),
            'unique_model_names': len({m['name'] for m in audit['models'].values()}),
            'mesh_assets': len(audit['geometries']), 'material_definitions': len(audit['materials']),
            'vertices': sum(g['vertices'] for g in audit['geometries'].values()),
            'triangles': sum(g['triangles'] for g in audit['geometries'].values()),
            'unresolved_texture_refs': audit['unresolved_texture_refs'],
            'collision_named_nodes': audit['collision_named_nodes'],
            'source_light_count': audit['source_light_count'],
            'asset_root': audit['asset_root'], 'map': audit['map'],
            'restoration_complete': False}


def _property_end(data, offset):
    type_ = chr(data[offset])
    cursor = offset + 1
    scalar_sizes = {'Y': 2, 'C': 1, 'I': 4, 'F': 4, 'D': 8, 'L': 8}
    if type_ in scalar_sizes:
        return cursor + scalar_sizes[type_]
    if type_ in 'SR':
        return cursor + 4 + struct.unpack_from('<I', data, cursor)[0]
    if type_ in 'fdlib':
        count, encoding, size = struct.unpack_from('<III', data, cursor)
        require(encoding in (0, 1), 'invalid binary FBX array encoding')
        return cursor + 12 + (size if encoding else count * {'f': 4, 'd': 8, 'l': 8, 'i': 4, 'b': 1}[type_])
    raise RuntimeError(f'BH3.Stage: unsupported binary FBX property {type_!r}')


def identity_fbx_bytes(source, names, expected_sha256=None):
    """Change only object-name strings; retain raw scalar/array payloads and footer.

    Existing helpers intentionally discard scalar type codes and raw R payloads,
    so rewriting their decoded tree would lose information. This small record
    walker copies raw property blocks and adjusts absolute 32-bit node offsets.
    """
    data = Path(source).read_bytes()
    if expected_sha256 is not None:
        require(hashlib.sha256(data).hexdigest() == expected_sha256,
                'FBX source changed since the audit: ' + str(source))
    require(data[:23] == FBX_MAGIC and struct.unpack_from('<I', data, 23)[0] == 7300,
            'identity copy only supports the audited binary FBX 7300 format')
    output = bytearray(data[:27])
    changed = set()

    def copy_node(start, parent):
        end, count, length, name_length = struct.unpack_from('<IIIB', data, start)
        require(start < end <= len(data), 'invalid binary FBX node range')
        node_name = data[start + 13:start + 13 + name_length].decode('utf-8')
        prop_start = start + 13 + name_length
        prop_end = prop_start + length
        require(prop_end <= end, 'invalid binary FBX property range')
        spans, cursor = [], prop_start
        for _ in range(count):
            next_ = _property_end(data, cursor)
            require(next_ <= prop_end, 'binary FBX property overflow')
            spans.append((cursor, next_))
            cursor = next_
        require(cursor == prop_end, 'binary FBX property length mismatch')
        block = data[prop_start:prop_end]
        if parent == 'Objects' and node_name in ('Model', 'Geometry', 'Material'):
            require(count >= 2 and chr(data[spans[0][0]]) == 'L'
                    and chr(data[spans[1][0]]) == 'S', 'unexpected FBX object header')
            object_id = str(struct.unpack_from('<q', data, spans[0][0] + 1)[0])
            require(object_id in names and object_id not in changed, 'unexpected/repeated object ' + object_id)
            a, b = spans[1]
            old_name = data[a + 5:b]
            separator = old_name.find(b'\x00\x01')
            require(separator >= 0, 'object name lacks FBX class suffix ' + object_id)
            new_name = names[object_id].encode('utf-8') + old_name[separator:]
            replacement = b'S' + struct.pack('<I', len(new_name)) + new_name
            block = data[prop_start:a] + replacement + data[b:prop_end]
            changed.add(object_id)
        new_start = len(output)
        output.extend(bytes(13))
        output.extend(data[start + 13:prop_start])
        output.extend(block)
        cursor = prop_end
        while cursor < end:
            if data[cursor:cursor + 13] == NULL_RECORD:
                require(cursor + 13 == end, 'unexpected bytes after child terminator')
                output.extend(NULL_RECORD)
                cursor += 13
            else:
                cursor = copy_node(cursor, node_name)
        struct.pack_into('<IIIB', output, new_start, len(output), count, len(block), name_length)
        return end

    cursor = 27
    while data[cursor:cursor + 13] != NULL_RECORD:
        cursor = copy_node(cursor, '')
    output.extend(NULL_RECORD)
    cursor += 13
    require(changed == set(names), 'identity copy did not rename every expected object')
    # The first footer marker must immediately follow the root null record.
    # Only the zero region AFTER that marker changes with the new file length:
    # align to 16 bytes, then retain four reserved zero bytes before the version.
    # Padding before the marker passes our record reader but FBXSDK rejects it.
    footer = data[cursor:]
    zero_count = len(footer) - 16 - 140
    # The first marker is file-specific; retain its source bytes verbatim.
    require(4 <= zero_count < 20 and footer[:16] != bytes(16)
            and footer[-16:] == bytes.fromhex('f85a8c6adef5d97eece90ce3758f290b')
            and footer[16:-140] == bytes(zero_count)
            and zero_count == 4 + (-(cursor + 16) % 16)
            and struct.unpack_from('<I', footer, len(footer) - 140)[0] == 7300
            and footer[-136:-16] == bytes(120), 'unexpected binary FBX footer')
    output.extend(footer[:16])
    output.extend(bytes(4 + (-len(output) % 16)))
    output.extend(footer[-140:])
    return bytes(output)


def prepare_stage(stage, destination, source_root=SOURCE):
    """New-only import copy and machine-consumed source manifest; no UE calls."""
    return _prepare_audit(audit_stage(stage, source_root), destination)


def _prepare_audit(audit, destination):
    # Reuse the run's read-only audit. Its source hash validates the exact bytes
    # copied here instead of repeating the complete source/geometry scan.
    destination = Path(destination)
    require(not destination.exists(), 'preparation directory already exists ' + str(destination))
    encoded = identity_fbx_bytes(audit['source'], audit['identity_names'], audit['source_sha256'])
    destination.mkdir(parents=True, exist_ok=False)
    staged_fbx = destination / (STAGES[audit['stage']] + '.fbx')
    with staged_fbx.open('xb') as stream:
        stream.write(encoded)
    audit['import_source'] = str(staged_fbx)
    audit['import_source_sha256'] = file_hash(staged_fbx)
    with (destination / 'source_manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(audit, stream, ensure_ascii=False, indent=2)
    return audit


def _set_properties(obj, **values):
    for key, value in values.items():
        obj.set_editor_property(key, value)
        require(obj.get_editor_property(key) == value,
                f'{type(obj).__name__}: property {key} did not retain the requested value')


def _pipelines(unreal):
    assets = unreal.InterchangeGenericAssetsPipeline()
    _set_properties(assets, use_source_name_for_asset=False, scene_name_sub_folder=False,
                    asset_type_sub_folders=True, import_offset_uniform_scale=1.0,
                    import_offset_translation=unreal.Vector(0, 0, 0),
                    import_offset_rotation=unreal.Rotator(0, 0, 0))
    common = assets.get_editor_property('common_meshes_properties')
    _set_properties(common, bake_meshes=False, bake_pivot_meshes=False,
                    import_lods=False, keep_sections_separate=True,
                    convert_statics_with_animated_transform_to_skeletals=False,
                    vertex_color_import_option=unreal.InterchangeVertexColorImportOption.IVCIO_REPLACE,
                    recompute_normals=False, recompute_tangents=True, remove_degenerates=False)
    mesh = assets.get_editor_property('mesh_pipeline')
    _set_properties(mesh, import_static_meshes=True, import_skeletal_meshes=False,
                    combine_static_meshes_behavior=unreal.InterchangeCombineStaticMeshesBehavior.DO_NOT_COMBINE,
                    collision=False, import_collision_according_to_mesh_name=False,
                    build_nanite=False, generate_lightmap_u_vs=False)
    _set_properties(assets.get_editor_property('animation_pipeline'), import_animations=False)
    material = assets.get_editor_property('material_pipeline')
    _set_properties(material, import_materials=False, reuse_existing_materials=False,
                    create_new_materials=False)
    _set_properties(material.get_editor_property('texture_pipeline'), import_textures=False)
    level = unreal.InterchangeGenericLevelPipeline()
    _set_properties(level, scene_hierarchy_type=unreal.InterchangeSceneHierarchyType.CREATE_LEVEL_ACTORS,
                    delete_missing_actors=False, delete_missing_assets=False,
                    force_reimport_deleted_actors=False, force_reimport_deleted_assets=False,
                    use_hierarchical_ism_components=False)
    stack = unreal.InterchangePipelineStackOverride()
    stack.add_pipeline(assets)
    stack.add_pipeline(level)
    # Keep strong Python references until synchronous import returns. The native
    # override API resolves and duplicates these transient pipeline instances.
    return assets, level, stack


def _package_file(package, extension):
    require(package.startswith('/Game/'), 'package outside permitted content root: ' + package)
    return PROJECT / 'Content' / (package[6:] + extension)


def _mesh_package(audit, geometry):
    # Matches the native type suffix, before factory creation and first save.
    return audit['asset_root'] + '/StaticMeshes/' + geometry['import_name']


def _expected_packages(audit):
    root = audit['asset_root']
    return {_mesh_package(audit, g): 'StaticMesh' for g in audit['geometries'].values()} | {
        root + '/SceneImport_' + STAGES[audit['stage']]: 'InterchangeSceneImportAsset'}


def _require_absent_packages(unreal, packages):
    for package in packages:
        object_name = package.rsplit('/', 1)[1]
        require(unreal.find_object(None, package + '.' + object_name) is None,
                'target UObject already exists: ' + package)
        require(not unreal.EditorAssetLibrary.does_asset_exist(package),
                'target asset already exists: ' + package)
        require(not any(_package_file(package, ext).exists() for ext in ('.uasset', '.umap')),
                'target package already exists on disk: ' + package)


def _require_new_stage_assets(unreal, audit):
    root = audit['asset_root']
    disk_directory = PROJECT / 'Content' / root[6:]
    require(not disk_directory.exists(), 'target directory already exists: ' + str(disk_directory))
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    require(not registry.get_assets_by_path(root, recursive=True, include_only_on_disk_assets=False),
            'target namespace contains registered assets: ' + root)
    _require_absent_packages(unreal, _expected_packages(audit))


def _require_new_targets(unreal, audit):
    _require_new_stage_assets(unreal, audit)
    _require_absent_packages(unreal, [audit['map']])


def _failed_source_evidence(audit, manifest_path):
    require(manifest_path.is_file(), 'missing failed-run manifest: ' + str(manifest_path))
    failed = json.loads(manifest_path.read_text(encoding='utf-8'))
    for key in ('stage', 'asset_root', 'map', 'source_sha256', 'identity_names'):
        require(failed[key] == audit[key], 'failed-run manifest differs at ' + key)
    require(Path(failed['source']).resolve() == Path(audit['source']).resolve(),
            'failed-run manifest refers to another source FBX')
    failed_source = manifest_path.parent / (STAGES[audit['stage']] + '.fbx')
    require(Path(failed['import_source']).resolve() == failed_source and failed_source.is_file(),
            'failed-run manifest does not bind its own FBX: ' + str(failed_source))
    require(file_hash(failed_source) == failed['import_source_sha256'],
            'failed import FBX changed: ' + str(failed_source))
    return {'failed_manifest': str(manifest_path), 'failed_source': str(failed_source),
            'failed_source_sha256': failed['import_source_sha256']}


def _empty_resume_evidence(audit, failed_manifest, empty_map_sha256, saved_scene_backup):
    """Verify the approved saved failure and its explicit independent backup."""
    require(audit['stage'] == 'P1', 'saved continuation is approved only for the known P1 failure')
    manifest_path = Path(failed_manifest).resolve()
    scratch_root = (PROJECT / 'Saved' / 'BH3StageImports').resolve()
    require(manifest_path.name == 'source_manifest.json'
            and manifest_path.parent.parent == scratch_root
            and manifest_path.parent.name == SAVED_PARTIAL_P1['run_directory'],
            'saved continuation manifest is not the approved failed run: ' + str(manifest_path))
    require(isinstance(empty_map_sha256, str)
            and empty_map_sha256.lower() == SAVED_PARTIAL_P1['map_sha256'],
            'saved continuation empty-map SHA256 differs from the approved result')
    source_evidence = _failed_source_evidence(audit, manifest_path)
    scene_package = audit['asset_root'] + '/SceneImport_' + STAGES[audit['stage']]
    backup = Path(saved_scene_backup).resolve()
    require(not backup.is_relative_to((PROJECT / 'Content').resolve()),
            'scene backup must be outside Content: ' + str(backup))
    evidence = dict(source_evidence, empty_map_sha256=empty_map_sha256.lower(),
                    saved_scene_package=scene_package, saved_scene_backup=str(backup),
                    saved_scene_bytes=SAVED_PARTIAL_P1['scene_bytes'],
                    saved_scene_sha256=SAVED_PARTIAL_P1['scene_sha256'])
    _require_saved_scene_files(evidence)
    return evidence


def _require_saved_scene_files(evidence):
    """Recheck protected disk bytes across the native import/save boundary."""
    scene_file = _package_file(evidence['saved_scene_package'], '.uasset')
    backup = Path(evidence['saved_scene_backup'])
    for path in (scene_file, backup):
        require(path.is_file() and path.stat().st_size == evidence['saved_scene_bytes']
                and file_hash(path) == evidence['saved_scene_sha256'],
                'approved failed scene or backup changed: ' + str(path))
    require(not os.path.samefile(scene_file, backup),
            'scene backup is the live package or a hard link: ' + str(backup))


def _p3_empty_map_evidence(audit, failed_report, empty_map_backup):
    """Consume the actual failed CLI report and its coordinator-owned map backup."""
    require(audit['stage'] == 'P3', 'owned empty Commandlet map continuation is P3 only')
    report_path = Path(failed_report).resolve()
    run_id = OWNED_EMPTY_P3['run_directory'][3:]
    require(report_path == (PROJECT / 'Saved' / 'AutomationReports'
            / ('BH3_Stage_P3_Geometry_' + run_id + '.json')).resolve() and report_path.is_file(),
            'owned P3 map report is not the approved failed run: ' + str(report_path))
    failed = json.loads(report_path.read_text(encoding='utf-8'))
    require(failed['stage'] == 'P3' and failed['editor_pid'] == 76080
            and failed['phase'] == 'readback' and failed['host_mode'] == 'commandlet'
            and failed['created_map'] == audit['map'] and not failed['saved_assets']
            and failed['map_saved'] is False and failed['geometry_import_verified'] is False,
            'owned P3 map report does not describe the approved unsaved geometry failure')
    require("AttributeError: 'StaticMaterial' object has no attribute 'imported_material_slot_name'"
            in failed['error'], 'owned P3 map report has another failure cause')
    # This known failure preceded the type-folder layout and never saved a
    # mesh. Verify its historical package identities exactly; they are not
    # destinations for the new import or a second supported production layout.
    root = audit['asset_root']
    expected = {root + '/' + g['import_name']: 'StaticMesh' for g in audit['geometries'].values()} | {
        root + '/SceneImport_' + STAGES[audit['stage']]: 'InterchangeSceneImportAsset'}
    require(failed['expected_packages'] == expected
            and {p.split('.')[0] for p in failed['actual_registered_assets']} == set(expected),
            'failed P3 asset identities differ from the source result')
    manifest_path = (PROJECT / 'Saved' / 'BH3StageImports'
                     / OWNED_EMPTY_P3['run_directory'] / 'source_manifest.json').resolve()
    require(Path(failed['source_manifest']).resolve() == manifest_path,
            'failed P3 report refers to another source manifest')
    source_evidence = _failed_source_evidence(audit, manifest_path)
    backup = Path(empty_map_backup).resolve()
    require(not backup.is_relative_to((PROJECT / 'Content').resolve()),
            'empty-map backup must be outside Content: ' + str(backup))
    evidence = dict(source_evidence, failed_report=str(report_path), map=audit['map'],
                    empty_map_backup=str(backup), empty_map_bytes=OWNED_EMPTY_P3['map_bytes'],
                    empty_map_sha256=OWNED_EMPTY_P3['map_sha256'])
    _require_owned_p3_map_files(evidence)
    return evidence


def _require_owned_p3_map_files(evidence):
    map_file = _package_file(evidence['map'], '.umap')
    backup = Path(evidence['empty_map_backup'])
    for path in (map_file, backup):
        require(path.is_file() and path.stat().st_size == evidence['empty_map_bytes']
                and file_hash(path) == evidence['empty_map_sha256'],
                'approved empty P3 map or backup changed: ' + str(path))
    require(not os.path.samefile(map_file, backup), 'empty-map backup is the live map or a hard link')


def _load_owned_p3_map(unreal, audit, evidence, editor, levels):
    _require_new_stage_assets(unreal, audit)
    _require_owned_p3_map_files(evidence)
    map_object = audit['map'] + '.' + audit['map'].rsplit('/', 1)[1]
    require(unreal.find_object(None, map_object) is None,
            'owned P3 map is already loaded; preserve unknown startup work')
    require(levels.load_level(audit['map']), 'cannot load the approved owned empty P3 map')
    world = editor.get_editor_world()
    level = levels.get_current_level()
    require(world is not None and world.get_path_name() == map_object
            and level is not None and level.get_outer() == world
            and level.get_path_name() == map_object + ':PersistentLevel',
            'owned P3 map/current persistent level differs after load')
    require(not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            and not unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors(),
            'owned P3 map is dirty or contains user actors after load')
    return world, level


def _scene_source_binding(unreal, scene, source):
    """Read the native import data across the scene reimport boundary."""
    require(scene is not None and scene.get_class().get_name() == 'InterchangeSceneImportAsset',
            'scene source query requires InterchangeSceneImportAsset')
    data = scene.get_editor_property('asset_import_data')
    require(isinstance(data, unreal.InterchangeAssetImportData), 'scene has no Interchange import data')
    filenames = [str(Path(path).resolve()) for path in data.extract_filenames()]
    require(filenames == [str(Path(source).resolve())], 'scene source binding differs: ' + str(filenames))
    node_uid = data.get_editor_property('node_unique_id')
    require(node_uid == 'Factory_SceneImport_' + Path(source).resolve().as_posix(),
            'scene node UID differs from its source binding: ' + str(node_uid))
    return data, {'scene_object': scene.get_path_name(), 'scene_class': scene.get_class().get_path_name(),
                  'import_data_class': data.get_class().get_path_name(), 'source_filenames': filenames,
                  'node_uid': node_uid}


def _read_saved_p1_scene(unreal, audit, evidence):
    """Read only the protected P1 partial and require all new targets absent."""
    root = audit['asset_root']
    packages = _expected_packages(audit)
    scene_package = evidence['saved_scene_package']
    require(packages.get(scene_package) == 'InterchangeSceneImportAsset',
            'saved continuation scene package is outside the expected source result')
    scene_file = _package_file(scene_package, '.uasset')
    disk_files = {p.resolve() for p in (PROJECT / 'Content' / root[6:]).rglob('*') if p.is_file()}
    require(disk_files == {scene_file.resolve()},
            'resume Stage disk content differs from the sole saved failed scene: ' + str(disk_files))
    _require_saved_scene_files(evidence)
    _require_absent_packages(unreal, [p for p in packages if p != scene_package])
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    actual = {str(a.package_name) for a in registry.get_assets_by_path(
        root, recursive=True, include_only_on_disk_assets=False)}
    require(actual == {scene_package}, 'resume namespace differs from the sole failed scene asset: ' + str(actual))
    scene = unreal.EditorAssetLibrary.load_asset(scene_package)
    data, state = _scene_source_binding(unreal, scene, evidence['failed_source'])
    require(state['scene_object'] == scene_package + '.' + scene_package.rsplit('/', 1)[1],
            'saved P1 scene loaded from another object path')
    container = data.get_node_container()
    require(container is not None, 'saved P1 scene has no public stored node container')
    node_ids = sorted(str(uid) for uid in container.get_nodes(unreal.InterchangeBaseNode.static_class()))
    graph = []
    for uid in node_ids:
        node = container.get_node(uid)
        require(node is not None and node.get_unique_id() == uid, 'stored P1 graph node cannot be read: ' + uid)
        row = {'uid': uid, 'class': node.get_class().get_path_name(), 'display_label': node.get_display_label()}
        if isinstance(node, unreal.InterchangeFactoryBaseNode):
            dependencies = sorted(str(dep) for dep in node.get_factory_dependencies())
            dependency_count = node.get_factory_dependencies_count()
            require(len(dependencies) == dependency_count, 'stored P1 dependency query disagrees at ' + uid)
            row.update(factory_dependencies=dependencies, factory_dependency_count=dependency_count)
        graph.append(row)
    require(state['node_uid'] in node_ids, 'saved P1 graph is missing its source-bound import node')
    metadata = {str(key): str(value) for key, value in unreal.EditorAssetLibrary.get_metadata_tag_values(scene).items()}
    # The non-editable array is not exposed to Python. The reflected interface
    # finds a non-null entry; it cannot enumerate the array or its null slots.
    require(callable(getattr(scene, 'get_asset_user_data_of_class', None)),
            'saved P1 scene has no reflected AssetUserData query interface')
    user_data_class = unreal.AssetUserData.static_class()
    first_user_data = scene.get_asset_user_data_of_class(user_data_class)
    state.update(stored_graph=graph, metadata=metadata, asset_user_data={
        'read_api': 'IInterface_AssetUserData.GetAssetUserDataOfClass',
        'query_class': user_data_class.get_path_name(),
        'non_null_entry_present': first_user_data is not None,
        'first_non_null_entry': (None if first_user_data is None else {
            'object': first_user_data.get_path_name(), 'class': first_user_data.get_class().get_path_name()}),
        'complete_array_readback': False,
    })
    return scene, data, state


def _load_owned_p1_result(unreal, audit, evidence, editor, levels):
    """Adopt the clean saved failure whose two-node graph was read natively."""
    map_file = _package_file(audit['map'], '.umap')
    require(map_file.is_file() and file_hash(map_file) == evidence['empty_map_sha256'],
            'owned empty P1 map changed before load')
    scene, data, state = _read_saved_p1_scene(unreal, audit, evidence)
    common_uid = 'CommonPipelineDataFactoryNode'
    expected_graph = [
        {'uid': common_uid, 'class': '/Script/InterchangeFactoryNodes.InterchangeCommonPipelineDataFactoryNode',
         'display_label': common_uid, 'factory_dependencies': [], 'factory_dependency_count': 0},
        {'uid': state['node_uid'], 'class': '/Script/InterchangeFactoryNodes.InterchangeSceneImportAssetFactoryNode',
         'display_label': 'SceneImport_' + STAGES['P1'],
         'factory_dependencies': [common_uid], 'factory_dependency_count': 1},
    ]
    require(state['stored_graph'] == expected_graph, 'saved P1 graph differs from the actual two-node failed import')
    require(not state['metadata'] and not state['asset_user_data']['non_null_entry_present'],
            'saved P1 scene metadata or non-null user data changed')
    # UE does not serialize this translator cache with the scene package. A
    # cold load legitimately has no cache; native reimport then loads the
    # current project settings. Validate those before import and the factory's
    # actual effective settings before saving the result.
    stored_settings = data.get_translator_settings()
    state['stored_translator_settings'] = (None if stored_settings is None
                                           else _translator_convention(stored_settings))
    state['translator_settings_validation'] = 'current_native_preflight_and_factory_effective_settings_before_save'
    require(levels.load_level(audit['map']), 'cannot load the approved owned empty P1 map')
    world = editor.get_editor_world()
    level = levels.get_current_level()
    map_object = audit['map'] + '.' + audit['map'].rsplit('/', 1)[1]
    require(world is not None and world.get_path_name() == map_object
            and level is not None and level.get_outer() == world
            and level.get_path_name() == map_object + ':PersistentLevel',
            'owned P1 map/current persistent level differs after load')
    require(not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            and not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
            and not unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors(),
            'owned P1 result is dirty or contains actors; preserve it and refuse continuation')
    _require_saved_scene_files(evidence)
    require(file_hash(map_file) == evidence['empty_map_sha256'], 'owned empty P1 map changed during native load')
    return world, level, scene, state


def _translator_settings(unreal, manager, source_data):
    translator = manager.get_translator_for_source_data(source_data)
    require(isinstance(translator, unreal.InterchangeFbxTranslator), 'native FBX translator unavailable')
    settings = translator.get_settings()
    return _translator_convention(settings)


def _translator_convention(settings):
    # Read native settings, including the project's explicit axes/unit policy.
    # Reject a different convention without rewriting project/editor settings.
    require(settings is not None and settings.get_class().get_name() == 'InterchangeFbxTranslatorSettings',
            'native FBX translator settings unavailable or wrong class')
    expected = {'convert_scene': True, 'force_front_x_axis': False, 'convert_scene_unit': True,
                'using_luf_coordinate_system': False}
    actual = {key: settings.get_editor_property(key) for key in expected}
    require(actual == expected, 'FBX translator convention differs: ' + str(actual))
    return actual


def _transform_readback(transform):
    translation = transform.translation
    scale = transform.scale3d
    rotation = transform.rotation
    values = {'translation': [translation.x, translation.y, translation.z],
              'scale': [scale.x, scale.y, scale.z],
              'quaternion': [rotation.x, rotation.y, rotation.z, rotation.w]}
    require(all(math.isfinite(v) for row in values.values() for v in row), 'nonfinite imported transform')
    return values


def _material_slot_contract(audit, model):
    # Native FBX scene/mesh translation keeps repeated references as separate
    # slots and names them by occurrence of the same material object, not by
    # the source slot index. The identity copy gives each object its FBX ID.
    occurrences = collections.Counter()
    slots = []
    for source_index, material_id in enumerate(model['material_slots']):
        occurrence = occurrences[material_id]
        name = audit['materials'][material_id]['import_name']
        if occurrence:
            name += '_Section' + str(occurrence)
        slots.append({'source_slot_index': source_index, 'material_id': material_id,
                      'repeat_index': occurrence, 'imported_slot_name': name})
        occurrences[material_id] += 1
    return slots


def _native_asset_result(audit, imported_objects):
    """Validate this synchronous call's OnAssetDone results before any save."""
    expected = _expected_packages(audit)
    result = {}
    for obj in imported_objects:
        require(obj is not None, 'native import reported a null asset')
        path = obj.get_path_name()
        package = path.split('.')[0]
        require(package in expected and path == package + '.' + package.rsplit('/', 1)[1],
                'native import returned an unexpected object: ' + path)
        require(package not in result, 'native import reported a duplicate package: ' + package)
        require(obj.get_class().get_name() == expected[package], 'native import returned another class: ' + path)
        result[package] = obj
    require(set(result) == set(expected), 'native import asset result differs from the source manifest')
    return result


def _geometry_readback(unreal, audit, import_level, baseline_actors, native_assets=None):
    actor_editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh_editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    require(actor_editor is not None and mesh_editor is not None,
            'required actor/mesh subsystem disappeared before scene readback')
    actors = actor_editor.get_all_level_actors()
    imported = {a.get_actor_label(): a for a in actors if a.get_path_name() not in baseline_actors}
    require(len(imported) == len(actors) - len(baseline_actors), 'duplicate imported actor labels')
    expected_labels = {m['import_name'] for m in audit['models'].values()}
    require(expected_labels.issubset(imported), 'source nodes missing from imported scene')
    extra = set(imported) - expected_labels
    require(extra in (set(), {'RootNode'}), 'unexpected imported actors: ' + str(sorted(extra)))
    if extra:
        require(imported['RootNode'].get_attach_parent_actor() is None,
                'native FBX RootNode has an unexpected parent')
    rows = {}
    for model_id, model in audit['models'].items():
        actor = imported[model['import_name']]
        parent = actor.get_attach_parent_actor()
        if model['parent'] == '0':
            require(parent is None or extra == {'RootNode'} and parent == imported['RootNode'],
                    f'source root {model_id} has an unexpected parent')
        else:
            expected_parent = audit['models'][model['parent']]['import_name']
            require(parent == imported[expected_parent], f'model {model_id} lost its source parent')
        require(actor.get_level() == import_level,
                f'model {model_id} imported into a different level')
        component = actor.get_editor_property('root_component')
        require(component is not None, f'model {model_id} has no root component')
        row = {'actor': actor.get_path_name(), 'source_name': model['name'], 'source_id': model_id,
               'parent_source_id': model['parent'],
               'world_transform': _transform_readback(actor.get_actor_transform()),
               'local_transform': _transform_readback(component.get_relative_transform())}
        components = actor.get_components_by_class(unreal.StaticMeshComponent)
        if model['geometry']:
            require(len(components) == 1, f'model {model_id} does not have one mesh component')
            mesh = components[0].get_editor_property('static_mesh')
            geometry = audit['geometries'][model['geometry'][0]]
            package = _mesh_package(audit, geometry)
            require(mesh is not None and mesh.get_path_name().split('.')[0] == package,
                    f'model {model_id} references a different geometry')
            if native_assets is not None:
                require(mesh == native_assets[package], f'model {model_id} does not reference its native import result')
            slot_names = [str(s.get_editor_property('imported_material_slot_name'))
                          for s in mesh.get_editor_property('static_materials')]
            slot_contract = _material_slot_contract(audit, model)
            expected_slots = [slot['imported_slot_name'] for slot in slot_contract]
            require(slot_names == expected_slots, f'model {model_id} material slots differ: {slot_names} / {expected_slots}')
            section_slots = [mesh_editor.get_lod_material_slot(mesh, 0, section)
                             for section in range(mesh.get_num_sections(0))]
            require(len(section_slots) == len(geometry['used_material_indices'])
                    and set(section_slots) == set(geometry['used_material_indices']),
                    f'model {model_id} lost polygon material assignments')
            row.update(mesh=package, material_slots=slot_names, material_slot_sources=slot_contract,
                       section_material_slots=section_slots,
                       local_bounds=str(mesh.get_bounding_box()))
        else:
            require(not components, f'Null model {model_id} unexpectedly became a mesh')
        rows[model_id] = row
    assets = unreal.EditorAssetLibrary.list_assets(audit['asset_root'], recursive=True, include_folder=False)
    packages = {p.split('.')[0] for p in assets}
    expected_packages = _expected_packages(audit)
    if native_assets is None:
        require(packages == set(expected_packages), 'imported package set differs from the source manifest')
        for package, class_name in expected_packages.items():
            obj = unreal.EditorAssetLibrary.load_asset(package)
            require(obj is not None and obj.get_class().get_name() == class_name,
                    'unexpected imported class at ' + package)
    else:
        # Scene reimport does not emit AssetCreated for its new meshes. Their
        # exact result set was validated through OnAssetDone; the registry may
        # omit them until the explicit package saves and disk scan below.
        require(set(assets) <= {obj.get_path_name() for obj in native_assets.values()},
                'registered assets outside the native source result')
    return rows


def _save_geometry_asset(unreal, obj, audit, report, resume_scene, evidence):
    package = obj.get_path_name().split('.')[0]
    require(package in _expected_packages(audit), 'refusing to save out-of-scope asset ' + package)
    if resume_scene is not None and obj == resume_scene:
        require(evidence is not None and package == evidence['saved_scene_package']
                and obj.get_class().get_name() == 'InterchangeSceneImportAsset',
                'refusing to save an unverified existing scene object: ' + package)
        _require_saved_scene_files(evidence)
    else:
        require(not _package_file(package, '.uasset').exists(), 'refusing to replace disk package ' + package)
    if resume_scene is not None:
        outer = obj.get_outer()
        require(outer.get_class().get_name() == 'Package' and outer.get_path_name() == package,
                'native result has another package outer: ' + package)
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'BH3.ImportOwner', OWNER)
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'BH3.SourceSHA256', audit['source_sha256'])
    unreal.EditorAssetLibrary.set_metadata_tag(obj, 'BH3.StagePhase', 'GeometryOnly')
    if resume_scene is None:
        require(unreal.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False), 'save failed: ' + package)
    else:
        # SaveLoadedAsset requires registry membership, which native Scene
        # reimport does not publish for newly created meshes. Save exactly the
        # verified native UObject's package, then index its actual disk file.
        require(unreal.EditorLoadingAndSavingUtils.save_packages([outer], False), 'package save failed: ' + package)
    require(_package_file(package, '.uasset').is_file(), 'saved package missing from disk: ' + package)
    require(obj.get_outer() not in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
            'saved package still dirty: ' + package)
    report['saved_assets'].append(package)


def _process_parameters(unreal):
    _, switches, parameters = unreal.SystemLibrary.parse_command_line(unreal.SystemLibrary.get_command_line())
    switches = {str(s).lstrip('-/').lower() for s in switches}
    parameters = {str(k).lower(): str(v) for k, v in parameters.items()}
    require({'unattended', 'nowrite'}.issubset(switches),
            'isolated process requires -unattended and -nowrite to protect config files')
    disabled = {p.strip().lower() for p in parameters.get('disableplugins', '').split(',')}
    require({'modelcontextprotocol', 'mcpclienttoolset', 'alltoolsets'}.issubset(disabled),
            'isolated process requires MCP server/client/aggregator plugins disabled')
    return parameters


def _require_geometry_api(unreal):
    """Exercise native read APIs before any Stage preparation or import.

    The engine Cube is an explicit read-only fixture, never Stage content or
    a replacement geometry. Mutation bindings are checked without invoking
    them; successful saves still require the actual production save results.
    """
    mesh_editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    require(mesh_editor is not None, 'required StaticMeshEditorSubsystem is unavailable in this host')
    actor_editor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    require(actor_editor is not None, 'required EditorActorSubsystem is unavailable in this host')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    require(levels is not None and all(callable(getattr(levels, name, None))
            for name in ('get_current_level', 'load_level', 'new_level')),
            'required LevelEditorSubsystem or production level bindings unavailable')
    actors = actor_editor.get_all_level_actors()
    cube_path = '/Engine/BasicShapes/Cube.Cube'
    cube = unreal.EditorAssetLibrary.load_asset(cube_path)
    require(cube is not None and cube.get_class().get_name() == 'StaticMesh'
            and cube.get_path_name() == cube_path, 'native API probe requires engine mesh ' + cube_path)
    slots = [str(s.get_editor_property('imported_material_slot_name'))
             for s in cube.get_editor_property('static_materials')]
    section_count = cube.get_num_sections(0)
    require(slots and section_count > 0, 'engine Cube has no material slots/LOD0 sections for API probe')
    section_slots = [mesh_editor.get_lod_material_slot(cube, 0, section) for section in range(section_count)]
    require(all(0 <= slot < len(slots) for slot in section_slots),
            'native section-to-material query failed on ' + cube_path + ': ' + str(section_slots))
    bounds = cube.get_bounding_box()
    require(all(math.isfinite(getattr(vector, axis)) for vector in (bounds.min, bounds.max)
                for axis in ('x', 'y', 'z')), 'native mesh bounds query failed on ' + cube_path)
    prototype = unreal.get_default_object(unreal.StaticMeshActor)
    require(prototype is not None, 'native StaticMeshActor prototype unavailable for read API probe')
    component = prototype.get_editor_property('root_component')
    require(component is not None and len(prototype.get_components_by_class(unreal.StaticMeshComponent)) == 1,
            'native StaticMeshActor prototype component query failed')
    component.get_editor_property('static_mesh')
    _transform_readback(prototype.get_actor_transform())
    _transform_readback(component.get_relative_transform())
    prototype.get_actor_label()
    prototype.get_attach_parent_actor()
    prototype.get_level()
    prototype.get_editor_property('tags')
    unreal.EditorAssetLibrary.get_metadata_tag_values(cube)
    for owner, names in (
        (unreal.EditorAssetLibrary, ('list_assets', 'does_asset_exist', 'set_metadata_tag', 'save_loaded_asset')),
        (unreal.EditorLoadingAndSavingUtils, ('get_dirty_map_packages', 'get_dirty_content_packages', 'save_map')),
        (prototype, ('set_editor_property', 'set_folder_path')),
    ):
        require(all(callable(getattr(owner, name, None)) for name in names),
                'required production API binding unavailable: ' + str(names))
    dirty_maps = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    dirty_content = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    return {'mesh_subsystem': mesh_editor.get_class().get_path_name(),
            'actor_subsystem': actor_editor.get_class().get_path_name(),
            'mesh_probe': cube_path, 'material_slots': slots, 'section_material_slots': section_slots,
            'actor_probe': prototype.get_path_name(), 'current_actor_count': len(actors),
            'dirty_maps': dirty_maps, 'dirty_content': dirty_content,
            'mutation_bindings_only': True, 'save_executed': False}


def _require_editor_process_host(unreal, stage, editor, levels, world):
    """Accept the verified standard Editor runner and preserve its startup map."""
    require(stage in STAGES, 'isolated Editor host requires an explicit approved Stage')
    parameters = _process_parameters(unreal)
    require(not parameters.get('run') and parameters.get('executepythonscript'),
            'isolated Editor requires -ExecutePythonScript, never a Commandlet')
    require(editor is not None and levels is not None, 'full Editor world/level subsystems unavailable')
    level = levels.get_current_level()
    engine_class = editor.get_outer().get_class().get_path_name()
    require(engine_class == '/Script/UnrealEd.UnrealEdEngine' and world is not None,
            'isolated host is not the fully initialized native UnrealEdEngine/world')
    require(world.get_path_name() == '/Game/Map/Untitled.Untitled'
            and level is not None and level.get_outer() == world
            and level.get_path_name() == world.get_path_name() + ':PersistentLevel'
            and _package_file('/Game/Map/Untitled', '.umap').is_file(),
            'isolated Editor startup differs from the verified saved Untitled world/level')
    require(not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            and not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
            'isolated Editor startup left dirty map/content packages; preserve them and refuse import')
    return {'engine_class': engine_class, 'initial_world': world.get_path_name(),
            'initial_level': level.get_path_name()}


def editor_api_preflight(stage):
    """Read capabilities in the native fully initialized Editor Python runner."""
    require(stage == 'P3', 'new-target Editor API preflight is P3 only')
    import unreal
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = editor.get_editor_world() if editor is not None else None
    host = _require_editor_process_host(unreal, stage, editor, levels, world)
    require(not unreal.EditorLevelLibrary.get_pie_worlds(False), 'PIE must be stopped')
    api = _require_geometry_api(unreal)
    audit = audit_stage(stage)
    _require_new_stage_assets(unreal, audit)
    pipelines = _pipelines(unreal)
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    require(not manager.is_interchange_active(), 'another Interchange import/export is active')
    settings = _translator_settings(unreal, manager, manager.create_source_data(audit['source']))
    report = {'stage': stage, 'phase': 'editor_api_preflight', 'editor_pid': os.getpid(),
              'engine_class': host['engine_class'],
              'world': host['initial_world'], 'level': host['initial_level'], 'geometry_api': api,
              'translator_settings': settings, 'asset_type_sub_folders': pipelines[0].get_editor_property('asset_type_sub_folders'),
              'geometry_import_verified': False, 'asset_writes': False}
    unreal.log('BH3_STAGE_EDITOR_API_PREFLIGHT ' + json.dumps(report, ensure_ascii=False))
    return report


def editor_p1_preflight(stage, failed_manifest, empty_map_sha256, saved_scene_backup):
    """Inspect the exact saved P1 failure in a separate native Editor; write nothing.

    Graph shape, metadata and dirty state are observations, not assumed empty
    values or a reimport authorization. This does not inspect another process's
    loaded UObject or replace the production continuation's ownership gate.
    """
    require(stage == 'P1' and all(value is not None for value in
            (failed_manifest, empty_map_sha256, saved_scene_backup)),
            'P1 read-only preflight requires its exact manifest, map SHA256 and scene backup')
    audit = audit_stage(stage)
    evidence = _empty_resume_evidence(audit, failed_manifest, empty_map_sha256, saved_scene_backup)
    map_file = _package_file(audit['map'], '.umap')
    require(map_file.is_file() and file_hash(map_file) == evidence['empty_map_sha256'],
            'approved empty P1 map changed before read-only preflight')
    import unreal
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = editor.get_editor_world() if editor is not None else None
    host = _require_editor_process_host(unreal, stage, editor, levels, world)
    require(not unreal.EditorLevelLibrary.get_pie_worlds(False), 'PIE must be stopped')
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    require(not manager.is_interchange_active(), 'another Interchange import/export is active')
    api = _require_geometry_api(unreal)
    scene_package = evidence['saved_scene_package']
    scene, _, scene_state = _read_saved_p1_scene(unreal, audit, evidence)
    require(levels.load_level(audit['map']), 'cannot read the approved saved P1 map')
    world = editor.get_editor_world()
    level = levels.get_current_level()
    map_object = audit['map'] + '.' + audit['map'].rsplit('/', 1)[1]
    require(world is not None and world.get_path_name() == map_object
            and level is not None and level.get_outer() == world
            and level.get_path_name() == map_object + ':PersistentLevel',
            'read-only P1 load returned another world/current level')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    dirty_maps = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    dirty_content = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    # Recheck protected bytes after native load/cache getters, before returning
    # to the standard runner's automatic exit. The coordinator checks again
    # after process exit; this probe never calls a save or a dirty-state setter.
    _require_saved_scene_files(evidence)
    require(file_hash(map_file) == evidence['empty_map_sha256'], 'P1 map bytes changed during read-only preflight')
    report = {'stage': stage, 'phase': 'editor_p1_saved_scene_preflight', 'editor_pid': os.getpid(),
              'host': host, 'geometry_api': api, 'evidence': evidence,
              **scene_state,
              'world': world.get_path_name(), 'level': level.get_path_name(),
              'user_actor_count': len(actors), 'actors': [actor.get_path_name() for actor in actors],
              'dirty_maps': dirty_maps, 'dirty_content': dirty_content,
              'scene_package_dirty': scene_package in dirty_content,
              'asset_writes': False, 'save_executed': False, 'reimport_validated': False}
    unreal.log('BH3_STAGE_P1_SAVED_SCENE_PREFLIGHT ' + json.dumps(report, ensure_ascii=False))
    return report


def import_geometry(stage):
    """Synchronous new-only geometry batch. Never auto-run PIE or SaveAll.

    Caller must hold the exclusive UE asset window. Failure preserves partial
    assets and returns their actual paths in the report; rerun refuses them.
    """
    return _run_geometry(stage)


def continue_geometry(stage, failed_manifest, empty_map_sha256, saved_scene_backup):
    """Resume the protected P1 failure in the standard complete Editor process.

    This is not an automatic recovery path. The ordinary import entry still
    rejects every existing target, including this failed scene artifact.
    """
    require(stage == 'P1' and failed_manifest is not None and empty_map_sha256 is not None and saved_scene_backup is not None,
            'explicit continuation requires its failed manifest, empty-map SHA256 and scene backup')
    return _run_geometry(stage, failed_manifest, empty_map_sha256, saved_scene_backup, editor_process=True)


def continue_editor_geometry(stage, failed_report, empty_map_backup):
    """Import new P3 assets into the approved unchanged empty map; preserve failures."""
    require(stage == 'P3' and failed_report is not None and empty_map_backup is not None,
            'explicit P3 Editor continuation requires its failed report and owned map backup')
    return _run_geometry(stage, editor_process=True, failed_report=failed_report, empty_map_backup=empty_map_backup)


def _run_geometry(stage, failed_manifest=None, empty_map_sha256=None, saved_scene_backup=None, *,
                  editor_process=False, failed_report=None, empty_map_backup=None):
    resume_inputs = (failed_manifest, empty_map_sha256, saved_scene_backup)
    require(all(p is None for p in resume_inputs) or all(p is not None for p in resume_inputs),
            'continuation evidence is incomplete; normal import cannot substitute for it')
    require(failed_manifest is None or (stage == 'P1' and editor_process
            and failed_report is None and empty_map_backup is None),
            'saved P1 continuation requires the complete Editor and cannot mix P3 evidence')
    require((failed_report is None and empty_map_backup is None)
            or (failed_report is not None and empty_map_backup is not None
                and editor_process and stage == 'P3' and failed_manifest is None),
            'owned P3 map continuation evidence is incomplete or mixed with another mode')
    require(not editor_process or failed_manifest is not None or failed_report is not None,
            'isolated Editor requires explicit owned P1 or P3 continuation evidence')
    import unreal
    audit = audit_stage(stage)
    evidence = (_empty_resume_evidence(audit, failed_manifest, empty_map_sha256, saved_scene_backup)
                if failed_manifest is not None else None)
    p3_map_evidence = (_p3_empty_map_evidence(audit, failed_report, empty_map_backup)
                       if failed_report is not None else None)
    require(not unreal.EditorLevelLibrary.get_pie_worlds(False), 'PIE must be stopped')
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    require(not manager.is_interchange_active(), 'another Interchange import/export is active')
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    require(editor is not None and levels is not None, 'required editor/level subsystem unavailable')
    old_world = editor.get_editor_world()
    require(old_world is not None, 'no current editor world')
    if editor_process:
        host = _require_editor_process_host(unreal, stage, editor, levels, old_world)
        previous_map = None
    else:
        host = None
        require(not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
                'dirty maps must be preserved before opening the new Stage map')
        previous_map = old_world.get_path_name().split('.')[0]
        require(_package_file(previous_map, '.umap').is_file(), 'current map has no saved disk package')
    geometry_api = _require_geometry_api(unreal)
    p1_result = (_load_owned_p1_result(unreal, audit, evidence, editor, levels)
                 if evidence is not None else None)
    if p1_result is not None:
        require(callable(getattr(unreal.EditorLoadingAndSavingUtils, 'save_packages', None))
                and callable(getattr(unreal.AssetRegistryHelpers.get_asset_registry(), 'scan_modified_asset_files', None)),
                'required native P1 package save / exact disk scan API unavailable')
    pipelines = _pipelines(unreal)
    source_data = manager.create_source_data(audit['source'])
    settings = _translator_settings(unreal, manager, source_data)
    run_id = uuid.uuid4().hex
    scratch = PROJECT / 'Saved' / 'BH3StageImports' / (stage + '_' + run_id)
    audit = _prepare_audit(audit, scratch)
    source_data = manager.create_source_data(audit['import_source'])
    reports = PROJECT / 'Saved' / 'AutomationReports'
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / ('BH3_Stage_' + stage + '_Geometry_' + run_id + '.json')
    report = {'stage': stage, 'editor_pid': os.getpid(), 'phase': 'preflight',
              'host_mode': 'editor_process' if editor_process else 'editor', 'host': host, 'geometry_api': geometry_api,
              'source_manifest': str(scratch / 'source_manifest.json'),
              'summary': audit_summary(audit), 'translator_settings': settings,
              'expected_packages': _expected_packages(audit), 'previous_map': previous_map,
              'created_map': None, 'saved_assets': [], 'map_saved': False,
              'geometry_import_verified': False, 'visual_verified': False,
              'movement_camera_smoke': 'not_run', 'restoration_complete': False,
              'remaining': ['Source shaders and material reconstruction', 'Source lighting',
                            'Source collider configuration / explicit project collision policy',
                            'Visual preview and landing / movement / camera smoke']}
    try:
        require(file_hash(audit['source']) == audit['source_sha256'], 'FBX source changed before import')
        resume_scene = None
        if evidence is not None:
            world, import_level, resume_scene, scene_state = p1_result
            report['resume_evidence'] = dict(evidence, **scene_state)
            report['adopted_empty_map'] = audit['map']
        elif p3_map_evidence is not None:
            report['phase'] = 'load_owned_empty_map'
            world, import_level = _load_owned_p3_map(unreal, audit, p3_map_evidence, editor, levels)
            report['owned_empty_map_evidence'] = p3_map_evidence
            report['adopted_empty_map'] = audit['map']
        else:
            _require_new_targets(unreal, audit)
            report['phase'] = 'create_new_map'
            # new_level can save an empty map before reporting a failure. Record
            # the attempt first; do not delete that map or retry on top of it.
            report['created_map'] = audit['map']
            require(levels.new_level(audit['map']), 'new_level failed; inspect its partial map')
            world = editor.get_editor_world()
            require(world is not None and world.get_path_name().split('.')[0] == audit['map'],
                    'new map did not become the editor world')
            import_level = levels.get_current_level()
            require(import_level is not None and import_level.get_outer() == world
                    and import_level.get_path_name() == world.get_path_name() + ':PersistentLevel',
                    'new map current level is not its persistent level')
        # The continuation gate already established that this world has no
        # editable level actors. A new map records its own actual baseline.
        baseline = (set() if evidence is not None or p3_map_evidence is not None else {
            a.get_path_name() for a in unreal.get_editor_subsystem(
                unreal.EditorActorSubsystem).get_all_level_actors()})
        parameters = unreal.ImportAssetParameters()
        _set_properties(parameters, is_automated=True, replace_existing=False,
                        follow_redirectors=False, force_show_dialog=False,
                        import_level=import_level,
                        override_pipelines=pipelines[2].get_editor_property('override_pipelines'))
        if resume_scene is not None:
            _set_properties(parameters, reimport_asset=resume_scene)
        imported_objects = []
        asset_done = None
        report['phase'] = 'native_scene_import'
        try:
            if resume_scene is not None:
                delegate = parameters.get_editor_property('on_asset_done')
                require(callable(getattr(delegate, 'bind_callable', None))
                        and callable(getattr(delegate, 'unbind', None)), 'native OnAssetDone binding unavailable')
                asset_done = delegate
                asset_done.bind_callable(lambda obj: imported_objects.append(obj))
                parameters.set_editor_property('on_asset_done', asset_done)
                require(bool(parameters.get_editor_property('on_asset_done')), 'native OnAssetDone was not bound')
            require(not manager.is_interchange_active(), 'another Interchange operation started before scene import')
            require(manager.import_scene(audit['asset_root'], source_data, parameters),
                    'Interchange scene import failed; partial assets preserved')
        finally:
            if asset_done is not None:
                asset_done.unbind()
                parameters.set_editor_property('on_asset_done', asset_done)
        require(not manager.is_interchange_active(), 'synchronous scene import is still active')
        report['phase'] = 'readback'
        native_assets = (_native_asset_result(audit, imported_objects) if resume_scene is not None else None)
        if native_assets is not None:
            require(native_assets[evidence['saved_scene_package']] == resume_scene,
                    'native P1 asset result replaced its adopted SceneImport identity')
            report['native_asset_result'] = {'read_api': 'ImportAssetParameters.OnAssetDone',
                                           'objects': sorted(obj.get_path_name() for obj in native_assets.values())}
        report['actors'] = _geometry_readback(unreal, audit, import_level, baseline, native_assets)
        if resume_scene is not None:
            require(unreal.EditorAssetLibrary.load_asset(evidence['saved_scene_package']) == resume_scene,
                    'P1 reimport replaced its adopted SceneImport UObject identity')
            data, report['reimport_source_binding'] = _scene_source_binding(unreal, resume_scene, audit['import_source'])
            report['effective_translator_settings'] = _translator_convention(data.get_translator_settings())
        for row in report['actors'].values():
            actor = unreal.find_object(None, row['actor'])
            require(actor is not None, 'imported actor disappeared: ' + row['actor'])
            tags = list(actor.get_editor_property('tags'))
            tags.extend([unreal.Name(OWNER), unreal.Name('FBX.ModelID=' + row['source_id'])])
            actor.set_editor_property('tags', tags)
            actor.set_folder_path(unreal.Name('BH3/' + STAGES[stage]))
        report['phase'] = 'exact_asset_saves'
        for package in sorted(_expected_packages(audit)):
            obj = native_assets[package] if native_assets is not None else unreal.EditorAssetLibrary.load_asset(package)
            _save_geometry_asset(unreal, obj,
                                 audit, report, resume_scene, evidence)
        if native_assets is not None:
            report['phase'] = 'saved_asset_registry_readback'
            unreal.AssetRegistryHelpers.get_asset_registry().scan_modified_asset_files(
                [str(_package_file(package, '.uasset')) for package in sorted(native_assets)])
            registered = unreal.EditorAssetLibrary.list_assets(audit['asset_root'], recursive=True, include_folder=False)
            require(set(registered) == {obj.get_path_name() for obj in native_assets.values()},
                    'saved native asset registry result differs from the exact source objects')
            report['saved_asset_registry_verified'] = True
        report['phase'] = 'exact_map_save'
        if evidence is not None:
            require(file_hash(_package_file(audit['map'], '.umap')) == evidence['empty_map_sha256'],
                    'owned empty map changed on disk during import; refusing to overwrite it')
        elif p3_map_evidence is not None:
            _require_owned_p3_map_files(p3_map_evidence)
        require(unreal.EditorLoadingAndSavingUtils.save_map(world, audit['map']), 'Stage map save failed')
        require(_package_file(audit['map'], '.umap').is_file(), 'saved Stage map missing from disk')
        require(world.get_outer() not in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
                'saved Stage map still dirty')
        report['map_saved'] = True
        report['geometry_import_verified'] = True
        report['phase'] = 'geometry_saved_materials_and_smoke_pending'
        if previous_map is not None and previous_map != audit['map']:
            require(levels.load_level(previous_map), 'cannot restore the previous saved editor map')
            report['previous_map_restored'] = True
        elif previous_map == audit['map']:
            report['previous_map_retained'] = True
        else:
            report['process_map_retained'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        # No rollback/delete, saving failed imports, or restoration that might
        # discard the newly created unsaved world. Let the caller inspect it.
        report['actual_registered_assets'] = list(unreal.EditorAssetLibrary.list_assets(
            audit['asset_root'], recursive=True, include_folder=False))
        unreal.log_error('BH3_STAGE_FAILED ' + report['error'])
        raise
    finally:
        with report_path.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        unreal.log('BH3_STAGE_REPORT ' + str(report_path))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=[
        'audit', 'geometry', 'continue_geometry', 'editor_continue_geometry', 'editor_api_preflight',
        'editor_p1_preflight'])
    parser.add_argument('--stage', choices=['P1', 'P3', 'all'], default='all')
    parser.add_argument('--failed-manifest')
    parser.add_argument('--empty-map-sha256')
    parser.add_argument('--saved-scene-backup')
    parser.add_argument('--failed-report')
    parser.add_argument('--empty-map-backup')
    args = parser.parse_args()
    if args.command == 'editor_p1_preflight':
        require(args.failed_report is None and args.empty_map_backup is None,
                'P1 saved-scene preflight cannot accept P3 owned-map evidence')
        editor_p1_preflight(args.stage, args.failed_manifest, args.empty_map_sha256, args.saved_scene_backup)
        return
    if args.command == 'editor_api_preflight':
        require(all(value is None for value in (args.failed_manifest, args.empty_map_sha256,
                args.saved_scene_backup, args.failed_report, args.empty_map_backup)),
                'read-only Editor API preflight does not accept continuation arguments')
        editor_api_preflight(args.stage)
        return
    if args.command == 'editor_continue_geometry':
        require(args.failed_manifest is None and args.empty_map_sha256 is None and args.saved_scene_backup is None,
                'P3 Editor continuation cannot accept P1 scene continuation evidence')
        continue_editor_geometry(args.stage, args.failed_report, args.empty_map_backup)
        return
    require(args.failed_report is None and args.empty_map_backup is None,
            'owned P3 map evidence requires editor_continue_geometry')
    if args.command == 'geometry':
        require(args.failed_manifest is None and args.empty_map_sha256 is None and args.saved_scene_backup is None,
                'new-only commands cannot accept continuation evidence')
        require(args.stage != 'all', 'geometry import requires an explicit P1 or P3 stage')
        import_geometry(args.stage)
        return
    if args.command == 'continue_geometry':
        require(args.stage != 'all' and args.failed_manifest is not None
                and args.empty_map_sha256 is not None and args.saved_scene_backup is not None,
                'continue_geometry requires stage, failed manifest, empty-map SHA256 and scene backup')
        continue_geometry(args.stage, args.failed_manifest, args.empty_map_sha256, args.saved_scene_backup)
        return
    require(args.failed_manifest is None and args.empty_map_sha256 is None and args.saved_scene_backup is None,
            'audit does not accept continuation arguments')
    stages = STAGES if args.stage == 'all' else [args.stage]
    for stage in stages:
        print(json.dumps(audit_summary(audit_stage(stage)), ensure_ascii=False))


if __name__ == '__main__':
    main()
