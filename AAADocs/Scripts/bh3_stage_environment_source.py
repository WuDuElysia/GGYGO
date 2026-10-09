"""@file Source evidence and affine contracts for BH3 Stage environment assets.

This module is offline. It reads the native supplement and the accepted geometry
result; it never imports Unreal or repairs the frozen scene importer. A plan is
machine input for restore_bh3_stage_environment, not an approval or completion
report. Native shader programs, texture interpretation and UE rendering policy
are separate facts: an unresolved interpretation cannot acquire a default.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

import import_bh3_stages as geometry

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = Path('F:/AnimeStudio/Exports/BH3/Stage')
TEXTURE_METADATA = Path('F:/AnimeStudio/_work/bh3_stage_p3_texture_metadata_20261008/native_texture_metadata_index.json')
OWNER = 'GGYGO.BH3.Stage.Environment.v1'
SCHEMA = 1
DATA_TEXTURE_SLOTS = {'_BumpMap', '_Normal01', '_Normal02', '_MaskTex', '_CausticTex'}
STAGE_COUNTS = {'P3': (10, 97, 99, 17, 5, 2), 'P1': (40, 77, 221, 75, 27, 1)}
P1_SOURCE_BINDING_DIFFERENCES = [{
    'model': '1580589350160', 'source_slot_index': 0,
    'fbx_material': ['cab-dfd24118d86338857f9dee1f0229a58d', '-4043112573400099215'],
    'native_material': ['cab-349b1a4abf79b9f9cabcee577f6f672a', '7290915914611696892']}]


class SourceError(ValueError):
    """An invalid or ambiguous source contract; callers must propagate failure."""


def require(ok, reason):
    if not ok:
        raise SourceError('BH3.Stage.Environment: ' + reason)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key ' + str(key))
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique,
                      parse_constant=lambda value: require(False, 'non-finite JSON value '+value))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def evidence(path):
    path = Path(path).resolve()
    require(path.is_file(), 'missing source ' + str(path))
    raw = path.read_bytes()
    return {'path': path.as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def child_file(root, relative):
    root, path = Path(root).resolve(), (Path(root) / relative).resolve()
    require(path.is_relative_to(root), 'source path escapes its root: ' + str(relative))
    require(path.is_file(), 'missing source ' + str(path))
    return path


def identity(source):
    return source['cab'].lower(), str(source['pathID'])


def safe_name(value):
    return re.sub(r'[^A-Za-z0-9_]', '_', value).strip('_')


def native_local(fields):
    p, q, s = (fields[k] for k in ('m_LocalPosition', 'm_LocalRotation', 'm_LocalScale'))
    # ModelConverter.cs mirrors X and scales meters to centimeters; Interchange
    # then mirrors Y. The FBX root's axis conversion is retained separately.
    return {'translation': [-100*p['x'], -100*p['y'], 100*p['z']],
            'quaternion': [-q['x'], -q['y'], q['z'], q['w']],
            'scale': [s['x'], s['y'], s['z']]}


def matrix(pose):
    x, y, z, w = pose['quaternion']
    require(abs(x*x+y*y+z*z+w*w-1) < 0.0001, 'non-unit source quaternion')
    sx, sy, sz = pose['scale']
    require(min(abs(sx), abs(sy), abs(sz)) > 1e-8, 'singular source scale')
    t = pose['translation']
    return [[(1-2*(y*y+z*z))*sx, 2*(x*y-z*w)*sy, 2*(x*z+y*w)*sz, t[0]],
            [2*(x*y+z*w)*sx, (1-2*(x*x+z*z))*sy, 2*(y*z-x*w)*sz, t[1]],
            [2*(x*z-y*w)*sx, 2*(y*z+x*w)*sy, (1-2*(x*x+y*y))*sz, t[2]],
            [0., 0., 0., 1.]]


def multiply(a, b):
    return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def inverse(a):
    rows = [list(row)+[float(i == j) for j in range(4)] for i, row in enumerate(a)]
    for col in range(4):
        pivot = max(range(col, 4), key=lambda i: abs(rows[i][col]))
        require(abs(rows[pivot][col]) > 1e-12, 'singular affine matrix')
        rows[col], rows[pivot] = rows[pivot], rows[col]
        den = rows[col][col]
        rows[col] = [v/den for v in rows[col]]
        for i in range(4):
            if i != col:
                factor = rows[i][col]
                rows[i] = [v-factor*w for v, w in zip(rows[i], rows[col])]
    return [row[4:] for row in rows]


def point(a, p):
    return [sum(a[i][k]*p[k] for k in range(3))+a[i][3] for i in range(3)]


def difference(a, b):
    return max(abs(a[i][j]-b[i][j]) for i in range(4) for j in range(4))


def map_nodes(components, audit, actors):
    """Map native identity using its actual parent graph and calibrated positions.

    Display paths are nonunique in this prefab. A unique parent/name/position
    match establishes correspondence. Coincident siblings also require their
    authored local rotation/scale to disambiguate identity. Full world affine
    equality remains a separate geometry contract.
    """
    transforms = {str(c['source']['pathID']): c for c in components if c['source']['type'] == 'Transform'}
    objects = {str(c['source']['pathID']): c for c in components if c['source']['type'] == 'GameObject'}
    require(len(transforms) == len(objects) == len(audit['models']), 'source graph cardinality differs')
    roots = [tid for tid, t in transforms.items() if t['fields']['m_Father']['m_PathID'] == 0]
    require(len(roots) == 1, 'source Transform root is ambiguous')
    mapping, poses, visiting, visited = {}, {}, set(), set()

    def visit(tid, parent):
        require(tid in transforms and tid not in visiting and tid not in visited,
                'invalid/cyclic/repeated source Transform ' + tid)
        visiting.add(tid)
        c = transforms[tid]
        f = c['fields']
        require(f['m_GameObject']['m_FileID'] == 0, 'external Transform owner')
        go = objects[str(f['m_GameObject']['m_PathID'])]
        converted = native_local(f)
        candidates = [mid for mid, m in audit['models'].items()
                      if m['parent'] == parent and m['name'] == go['fields']['m_Name']
                      and (parent == '0' or max(abs(x-y) for x, y in zip(
                          converted['translation'], actors[mid]['local_transform']['translation'])) < .03)]
        if len(candidates) > 1:
            candidates = [mid for mid in candidates if difference(matrix(converted),
                          matrix(actors[mid]['local_transform'])) < .03]
        require(len(candidates) == 1, f"native {identity(go['source'])} has {len(candidates)} FBX matches")
        mid = candidates[0]
        require(mid not in mapping.values(), 'two source identities map to FBX node ' + mid)
        mapping[str(go['source']['pathID'])] = mid
        poses[mid] = converted
        for ref in f['m_Children']:
            require(ref['m_FileID'] == 0, 'external Transform child')
            child = transforms[str(ref['m_PathID'])]
            require(child['fields']['m_Father'] == {'m_FileID': 0, 'm_PathID': int(tid)},
                    'source child/parent disagreement')
            visit(str(ref['m_PathID']), mid)
        visiting.remove(tid)
        visited.add(tid)
    visit(roots[0], '0')
    require(len(mapping) == len(audit['models']), 'source graph did not cover all FBX nodes')
    root_id = audit['root_id']
    # The imported axis root is a real retained transform. Verify the authored
    # root is identity rather than guessing how to combine two nonidentity roots.
    require(difference(matrix(poses[root_id]), matrix({'translation': [0, 0, 0],
            'quaternion': [0, 0, 0, 1], 'scale': [1, 1, 1]})) < 1e-5,
            'nonidentity native root requires a verified axis-root contract')
    poses[root_id] = actors[root_id]['local_transform']
    return mapping, poses, objects


def shader_passes(entry, supplement):
    document = read_json(child_file(supplement, entry['fieldsFile']))
    require(identity(document['source']) == identity(entry['source']), 'shader source identity differs')
    form = document['fields']['m_ParsedForm']
    fields_proof = evidence(child_file(supplement, entry['fieldsFile']))
    require(form['m_Name'] == entry['shaderName'] and len(form['m_SubShaders']) == 1,
            'ambiguous shader/subshader identity')
    blob = child_file(supplement, entry['programBlob']['file'])
    require(evidence(blob)['sha256'] == entry['programBlob']['sha256'], 'program blob changed')
    raw = blob.read_bytes()
    count = struct.unpack_from('<I', raw)[0]
    require(4+8*count <= len(raw), 'truncated native shader program table')
    rows = []
    for pi, p in enumerate(form['m_SubShaders'][0]['m_Passes']):
        names = {int(index): name for name, index in p['m_NameIndices']}
        require(len(names) == len(p['m_NameIndices']), 'duplicate native shader name index')
        stages = {}
        for label, key in [('vs', 'progVertex'), ('ps', 'progFragment')]:
            programs = []
            for sub_index, sub in enumerate(p[key]['m_SubPrograms']):
                bi = sub['m_BlobIndex']
                require(0 <= bi < count, 'native BlobIndex out of range')
                offset, size = struct.unpack_from('<II', raw, 4+bi*8)
                require(offset >= 4+count*8 and offset+size <= len(raw), 'program table span out of bounds')
                dx = [d for d in entry['dxbcPrograms'] if offset <= d['offset'] and d['offset']+d['size'] <= offset+size]
                require(len(dx) == 1, 'native shader program does not contain exactly one evidenced DXBC')
                d = dx[0]
                require(hashlib.sha256(raw[d['offset']:d['offset']+d['size']]).hexdigest() == d['sha256'],
                        'native program bytes differ from DXBC evidence')
                require(evidence(child_file(supplement, d['file']))['sha256'] == d['sha256'], 'DXBC file changed')
                programs.append({'blob_index': bi, 'keywords': sorted(names[k] for k in sub['m_KeywordIndices']),
                                 'sha256': d['sha256'],
                                 'source_pass': pi, 'source_stage': key, 'source_subprogram': sub_index})
            stages[label] = programs
        state = p['m_State']
        tags = dict(state['m_Tags']['tags'])
        rows.append({'index': pi, 'name': state['m_Name'], 'lightmode': tags.get('LIGHTMODE', ''),
                     'state': state, 'programs': stages})
    return {'identity': list(identity(entry['source'])), 'name': form['m_Name'],
            'fields': fields_proof,
            'properties': form['m_PropInfo']['m_Props'], 'passes': rows,
            'runtime_variant_selected': False}


def select_program(shader, pass_index, stage, keywords):
    """An explicit compiled candidate is not proof of original runtime selection."""
    require(type(pass_index) is int and 0 <= pass_index < len(shader['passes']), 'invalid explicit Pass index')
    require(stage in ('vs', 'ps') and len(keywords) == len(set(keywords)), 'invalid stage/keyword selection')
    candidates = [p for p in shader['passes'][pass_index]['programs'][stage]
                  if p['keywords'] == sorted(keywords)]
    require(len(candidates) == 1, 'explicit Pass/stage/keywords do not select one native program')
    selected = dict(candidates[0])
    selected['source_fields'] = shader['fields']
    selected['file'] = str(Path(shader['fields']['path']).parent/'DXBC'/(selected['sha256']+'.dxbc'))
    return selected


def disassemble(program):
    """Read-only Windows D3D bytecode inspection; no CLI, file or UE execution."""
    import ctypes
    raw = Path(program['file']).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == program['sha256'], 'selected DXBC changed')
    dll = ctypes.WinDLL('C:/Windows/System32/d3dcompiler_47.dll')
    call = dll.D3DDisassemble
    call.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_char_p,
                     ctypes.POINTER(ctypes.c_void_p)]
    call.restype = ctypes.c_long
    storage = ctypes.create_string_buffer(raw)
    blob = ctypes.c_void_p()
    require(call(storage, len(raw), 0, None, ctypes.byref(blob)) >= 0 and blob.value,
            'native D3DDisassemble rejected selected program')
    table = ctypes.cast(blob, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    pointer = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(table[3])
    size = ctypes.WINFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p)(table[4])
    release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])
    try:
        return ctypes.string_at(pointer(blob), size(blob)).decode('utf-8').rstrip('\x00')
    finally:
        release(blob)


def reflected_subprogram(program):
    """Bind assembly to the SAME serialized program, including shared DXBC cases."""
    import zzz_dxbc_hlsl as dxbc
    proof = program['source_fields']
    require(evidence(proof['path']) == proof, 'selected reflection fields changed')
    form = read_json(proof['path'])['fields']['m_ParsedForm']
    native_pass = form['m_SubShaders'][0]['m_Passes'][program['source_pass']]
    p = native_pass[program['source_stage']]['m_SubPrograms'][program['source_subprogram']]
    require(p['m_BlobIndex'] == program['blob_index'], 'selected reflection BlobIndex changed')
    names = {int(index): name for name, index in native_pass['m_NameIndices']}
    lines = [disassemble(program)]
    for binding in p['m_ConstantBufferBindings']:
        lines.append('//@ CBBIND %s %d' % (names[binding['m_NameIndex']], binding['m_Index']))
    for cb in p['m_ConstantBuffers']:
        name = names[cb['m_NameIndex']]
        require(not cb.get('m_StructParams'), 'native structured CB parameters need an explicit decoder')
        lines.append('//@ CB %s %d' % (name, cb['m_Size']))
        for kind, field in [('V', 'm_VectorParams'), ('M', 'm_MatrixParams')]:
            for item in cb[field]:
                lines.append('//@ %s %s %s %d %d %d %d' % (kind, name, names[item['m_NameIndex']],
                             item['m_Index'], item['m_Dim'] if kind == 'V' else item['m_RowCount'],
                             item['m_ArraySize'], item['m_Type']))
    for tex in p['m_TextureParams']:
        # A negative sampler is a real native packed/global sampler dependency.
        # Its binding is retained; it is never changed to the texture register.
        lines.append('//@ TEX %s %d %d %d' % (names[tex['m_NameIndex']], tex['m_Index'],
                                             tex['m_SamplerIndex'], tex['m_Dim']))
    for sampler in p['m_Samplers']:
        lines.append('//@ SMP %d %d' % (sampler['sampler'], sampler['bindPoint']))
    parsed = dxbc.parse_subprogram('\n'.join(lines))
    require(parsed['asm'] and parsed['in'] and parsed['out'], 'missing native program assembly/signatures')
    return parsed


def native_fragment_dependencies(shader, pass_index, keywords):
    """Discover live inputs; discovery output cannot be submitted as a material."""
    import zzz_dxbc_hlsl as dxbc
    program = select_program(shader, pass_index, 'ps', keywords)
    sub = reflected_subprogram(program)
    result = dxbc.translate(sub, 'P_', {'__discover__': True}, {0: 'xyzw'})
    return {'program_sha256': program['sha256'], 'blob_index': program['blob_index'],
            'missing_globals': sorted(set(name for name, row, comp in result['missing'])),
            'textures': result['textures'], 'live_inputs': result['live_inputs'],
            'source_runtime_selection_verified': False}


def build_plan(stage, geometry_report, source_root=SOURCE, texture_metadata=TEXTURE_METADATA):
    require(stage in STAGE_COUNTS, 'unsupported Stage environment: ' + stage)
    audit = geometry.audit_stage(stage, Path(source_root))
    report = read_json(geometry_report)
    require(report['stage'] == stage and report['geometry_import_verified'] and report['map_saved']
            and report['phase'] == 'geometry_saved_materials_and_smoke_pending', 'geometry has not passed its saved gate')
    actors = report['actors']
    require(set(actors) == set(audit['models']), 'geometry result node set differs')
    for mid, row in actors.items():
        require(row['source_id'] == mid and row['parent_source_id'] == audit['models'][mid]['parent'],
                'geometry result source hierarchy changed')
        require(row['actor'].startswith(audit['map']+'.'+audit['map'].rsplit('/', 1)[1]+':PersistentLevel.'),
                'source actor outside target map')
    base = Path(source_root) / geometry.STAGES[stage]
    supplement = base / 'SourceSupplement'
    index = read_json(supplement / 'source_supplement.json')
    component_doc = read_json(child_file(supplement, index['componentsFile']))
    components = component_doc['components']
    mapping, poses, objects = map_nodes(components, audit, actors)
    native_materials = {identity(m['source']): m for m in index['materials']}
    require(len(native_materials) == STAGE_COUNTS[stage][0], stage + ' native material count differs')
    exports = {}
    for ident, m in native_materials.items():
        file = child_file(base, m['originalExportRelativeFile'])
        require(evidence(file)['sha256'] == m['originalExportSha256'], 'material export/native link changed')
        exports[m['fields']['m_Name']] = ident
    externals = {e['fileID']: e['cab'].lower() for e in component_doc['sourceFile']['externals']}
    own_cab = component_doc['sourceFile']['cab'].lower()
    fbx_material_names = {m['name'] for m in audit['materials'].values()}
    native_used_materials = {(own_cab if ref['m_FileID'] == 0 else externals[ref['m_FileID']], str(ref['m_PathID']))
                            for c in components if c['source']['type'] == 'MeshRenderer' for ref in c['fields']['m_Materials']}
    require(native_used_materials <= set(native_materials), 'native renderer material identity is unresolved')
    unbound_materials = [m for key, m in native_materials.items() if key not in native_used_materials]
    require(set(exports) >= fbx_material_names, 'FBX material is absent from native source')
    objects_by_model = {mid: objects[go] for go, mid in mapping.items()}
    active_states = {}
    def hierarchy_active(mid):
        if mid not in active_states:
            parent = audit['models'][mid]['parent']
            active_states[mid] = bool(objects_by_model[mid]['fields']['m_IsActive']) and (
                parent == '0' or hierarchy_active(parent))
        return active_states[mid]
    textures, materials, renderers, lights, probes, colliders = {}, {}, [], [], [], []
    binding_differences = []
    shaders = {tuple(identity(s['source'])): shader_passes(s, supplement) for s in index['shaders']}
    for ident, m in native_materials.items():
        require(tuple(identity({'cab': m['shaderReference']['cab'], 'pathID': m['shaderReference']['pathID']})) in shaders,
                'material shader dependency is absent')
        if ident not in native_used_materials:
            continue
        key = '/'.join(ident)
        bindings = {}
        for t in m['textureReferences']:
            ti = (t['cab'].lower(), str(t['pathID']))
            tk = '/'.join(ti)
            bindings[t['property']] = tk
            if t.get('existingTextureRelativeFile'):
                file = child_file(base, t['existingTextureRelativeFile'])
                tex = {'identity': list(ti), 'class': 'Texture2D', 'file': evidence(file),
                       'native_settings': None, 'interpretation_verified': False}
            else:
                found = [c for c in index['textures'] if identity(c['source']) == ti]
                require(len(found) == 1, 'unresolved non-null texture ' + tk)
                extra = found[0]
                metadata_file = child_file(supplement, extra['metadataFile'])
                meta = read_json(metadata_file)
                require(identity(meta['source']) == ti, 'supplement texture metadata identity differs: ' + tk)
                if extra['source']['type'] == 'Texture2D':
                    file = child_file(supplement, extra['pngFile'])
                    raw = child_file(supplement, meta['source']['rawFile'])
                    require(evidence(raw)['sha256'] == meta['source']['rawSha256']
                            and raw.stat().st_size == meta['source']['byteSize']
                            and max(span[1] for span in meta['fieldByteSpans'].values()) == raw.stat().st_size,
                            'supplement Texture2D raw/layout changed: ' + tk)
                    png = file.read_bytes()
                    require(png[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', png[16:24])
                            == (meta['fields']['m_Width'], meta['fields']['m_Height'])
                            and meta['fields']['m_ImageCount'] == 1 and not meta['hdrConvertedTo8Bit'],
                            'supplement Texture2D PNG dimensions/type differ: ' + tk)
                    tex = {'identity': list(ti), 'class': 'Texture2D', 'file': evidence(file),
                           'native_settings': meta['fields'], 'native_metadata': evidence(metadata_file),
                           'interpretation_verified': False}
                else:
                    require(extra['source']['type'] == 'Cubemap', 'unsupported supplement texture type: ' + tk)
                    file = child_file(supplement, extra['ddsFile'])
                    require(evidence(file)['sha256'] == meta['ddsSha256'] and not meta['hdrConvertedTo8Bit'],
                            'cubemap payload was changed/downconverted')
                    tex = {'identity': list(ti), 'class': 'TextureCube', 'file': evidence(file),
                           'native_settings': meta['fields'], 'layout': meta['ddsLayout'],
                           'interpretation_verified': False}
            tex['package'] = audit['asset_root']+'/Textures/T_'+safe_name(file.stem)
            if tk in textures:
                require(textures[tk] == tex, 'one texture identity has conflicting evidence')
            textures[tk] = tex
        materials[key] = {'identity': list(ident), 'name': m['fields']['m_Name'], 'fields': m['fields'],
                          'shader': '/'.join(identity({'cab': m['shaderReference']['cab'], 'pathID': m['shaderReference']['pathID']})),
                          'textures': bindings, 'package': audit['asset_root']+'/Materials/M_'+safe_name(m['fields']['m_Name'])}
    for c in components:
        typ = c['source']['type']
        if typ not in ('MeshRenderer', 'Light', 'ReflectionProbe', 'MeshCollider'):
            continue
        mid = mapping[str(c['gameObjectPathID'])]
        f = c['fields']
        row = {'identity': list(identity(c['source'])), 'model': mid, 'actor': actors[mid]['actor'],
               'fields': f, 'owner_active': bool(objects[str(c['gameObjectPathID'])]['fields']['m_IsActive']),
               'source_path': c['nodePath'], 'source_evidence': c['source']}
        if stage == 'P1':
            row['hierarchy_active'] = hierarchy_active(mid)
        if typ == 'MeshRenderer':
            refs, slots = f['m_Materials'], actors[mid]['material_slot_sources']
            require(len(refs) == len(slots), 'native renderer / imported material slot cardinality differs')
            bindings, fbx_bindings = [], []
            for slot in slots:
                ref = refs[slot['source_slot_index']]
                ident = (own_cab if ref['m_FileID'] == 0 else externals[ref['m_FileID']], str(ref['m_PathID']))
                require(ident in native_materials, 'renderer material identity is unresolved')
                fbx_identity = exports[audit['materials'][slot['material_id']]['name']]
                fbx_bindings.append('/'.join(fbx_identity))
                if fbx_identity != ident:
                    difference_row = {'model': mid, 'source_slot_index': slot['source_slot_index'],
                                      'fbx_material': list(fbx_identity), 'native_material': list(ident)}
                    require(stage == 'P1' and difference_row in P1_SOURCE_BINDING_DIFFERENCES,
                            'renderer pointer differs from FBX material provenance: ' + row['source_path']
                            + ' slot=' + str(slot['source_slot_index']) + ' FBX=' + str(fbx_identity) + ' native=' + str(ident))
                    binding_differences.append(difference_row)
                bindings.append('/'.join(ident))
            row.update(mesh=actors[mid]['mesh'], materials=bindings, slots=slots,
                       sections=actors[mid]['section_material_slots'])
            if stage == 'P1':
                row.update(fbx_materials=fbx_bindings, material_binding_authority='native_renderer')
            renderers.append(row)
        elif typ == 'Light':
            require(f['m_Type'] in (0, 1, 2) and f['m_Cookie']['m_PathID'] == f['m_Flare']['m_PathID'] == 0,
                    'unsupported source light type/cookie/flare')
            lights.append(row)
        elif typ == 'ReflectionProbe':
            require(c['fullLayoutParsed'], 'reflection probe layout is incomplete')
            ti = identity(c['m_CustomBakedTextureResolvedSource'])
            found = [t for t in index['textures'] if identity(t['source']) == ti]
            require(len(found) == 1, 'probe custom cubemap is unresolved')
            cube = found[0]
            meta = read_json(child_file(supplement, cube['metadataFile']))
            file = child_file(supplement, cube['ddsFile'])
            require(evidence(file)['sha256'] == meta['ddsSha256'], 'probe cubemap changed')
            tk = '/'.join(ti)
            textures[tk] = {'identity': list(ti), 'class': 'TextureCube', 'file': evidence(file),
                            'native_settings': meta['fields'], 'layout': meta['ddsLayout'],
                            'interpretation_verified': False,
                            'package': audit['asset_root']+'/Textures/T_'+safe_name(file.stem)}
            row['texture'] = tk
            probes.append(row)
        else:
            row['mesh_is_null'] = c.get('sourceMeshIsNull', f['m_Mesh']['m_PathID'] == 0)
            row['cooking_settings_verified'] = bool(c.get('convexOrCookingSettingsInferred'))
            colliders.append(row)
    require((len(renderers), sum(len(r['materials']) for r in renderers), len(textures), len(lights), len(probes))
            == STAGE_COUNTS[stage][1:], stage + ' environment cardinality differs from accepted source')
    metadata_index = read_json(texture_metadata)
    require(evidence(supplement/'source_supplement.json')['sha256'] == metadata_index['sourceMaterialIndexSha256'],
            'Texture2D metadata was extracted for another material index')
    metadata_rows = {identity(t): t for t in metadata_index['textures']}
    require(set(metadata_rows) == {tuple(t['identity']) for t in textures.values()
                                  if t['class'] == 'Texture2D' and 'native_metadata' not in t},
            'Texture2D metadata does not cover the exact source PNG identities')
    for t in textures.values():
        if t['class'] != 'Texture2D' or 'native_metadata' in t:
            continue
        row = metadata_rows[tuple(t['identity'])]
        proof = evidence(row['metadataFile'])
        require(proof['sha256'] == row['metadataSha256'], 'Texture2D metadata changed')
        native = read_json(row['metadataFile'])
        require(identity(native['source']) == tuple(t['identity']), 'Texture2D metadata native identity differs')
        require(evidence(native['source']['rawFile'])['sha256'] == native['source']['rawSha256'], 'native Texture2D bytes changed')
        t['native_settings'] = native['fields']
        t['native_metadata'] = proof
    worlds = {}
    def world(mid):
        if mid not in worlds:
            parent = audit['models'][mid]['parent']
            worlds[mid] = matrix(poses[mid]) if parent == '0' else multiply(world(parent), matrix(poses[mid]))
        return worlds[mid]
    affine = []
    for r in renderers:
        mid = r['model']
        expected = world(mid)
        actual = matrix(actors[mid]['world_transform'])
        correction = multiply(inverse(actual), expected)
        delta = difference(correction, matrix({'translation': [0, 0, 0], 'quaternion': [0, 0, 0, 1], 'scale': [1, 1, 1]}))
        if delta > .02:
            affine.append({'model': mid, 'mesh': r['mesh'], 'source_world': expected, 'saved_world': actual,
                           'correction': correction, 'delta': delta,
                           'package': audit['asset_root']+'/StaticMeshes/SourceAffine/'+r['mesh'].rsplit('/', 1)[1]+'_SourceAffine'})
    plan = {'schema': SCHEMA, 'owner': OWNER, 'stage': stage, 'map': audit['map'], 'asset_root': audit['asset_root'],
            'geometry_report': evidence(geometry_report), 'source_components': evidence(supplement/index['componentsFile']),
            'source_fbx': evidence(audit['source']), 'texture_metadata_index': evidence(texture_metadata), 'geometry_actors': actors,
            'textures': textures, 'materials': materials, 'shaders': {'/'.join(k): v for k, v in shaders.items()},
            'renderers': renderers, 'lights': lights, 'probes': probes, 'colliders': colliders,
            'native_local_poses': poses, 'affine_meshes': affine,
            'remaining': ['native runtime shader variant/environment inputs', '2D color interpretation/normal Importer flags and original mip pixels',
                          'cubemap face orientation/color calibration', 'Unity light units to UE calibration',
                          'source-disabled collider activation policy', 'visual/landing/movement/camera smoke'],
            'restoration_complete': False}
    if stage == 'P1':
        require(binding_differences == P1_SOURCE_BINDING_DIFFERENCES, 'P1 source/FBX binding differences changed')
        plan['source_index'] = evidence(supplement / 'source_supplement.json')
        plan['unbound_materials'] = unbound_materials
        plan['fbx_binding_differences'] = binding_differences
    targets = [t['package'] for t in textures.values()]+[m['package'] for m in materials.values()]+[m['package'] for m in affine]
    require(len(set(targets)) == len(targets), 'two source identities would share a target package')
    plan['digest'] = digest(plan)
    return plan


def validate_plan(plan):
    require(plan.get('schema') == SCHEMA and plan.get('owner') == OWNER and plan.get('stage') in STAGE_COUNTS, 'foreign plan')
    unsigned = {k: v for k, v in plan.items() if k != 'digest'}
    require(plan.get('digest') == digest(unsigned), 'plan content changed')
    proofs = [plan['geometry_report'], plan['source_components'], plan['source_fbx'], plan['texture_metadata_index']]
    if plan['stage'] == 'P1':
        proofs.append(plan['source_index'])
        require(plan['fbx_binding_differences'] == P1_SOURCE_BINDING_DIFFERENCES
                and all(row.get('material_binding_authority') == 'native_renderer' for row in plan['renderers']),
                'P1 explicit native renderer binding contract differs')
        require(all(type(row.get('hierarchy_active')) is bool for rows in
                    ('renderers', 'lights', 'probes', 'colliders') for row in plan[rows]),
                'P1 component hierarchy activation is absent')
    proofs += [t['file'] for t in plan['textures'].values()]
    proofs += [t['native_metadata'] for t in plan['textures'].values() if 'native_metadata' in t]
    proofs += [s['fields'] for s in plan['shaders'].values()]
    for item in proofs:
        require(evidence(item['path']) == item, 'consumed source changed: ' + item['path'])
    require(not plan['restoration_complete'], 'source plan falsely claims complete restoration')
    return plan


def component_enabled(row):
    """原生 Owner／组件启用状态；P1 同时检查源父节点。"""
    return row['owner_active'] and ('hierarchy_active' not in row or row['hierarchy_active']) and bool(row['fields']['m_Enabled'])


def equivalent_settings(plan):
    """Explicit, editable UE rendering policy; the native source plan stays immutable.

    These values are a selected production mode, not recovered Unity globals.
    Each material retains native CAB/PID, texture slots, UV transforms and saved
    properties. UE parameters are prefixed UE_ and kept separate from source data.
    """
    roles = {key: set() for key in plan['textures']}
    for material in plan['materials'].values():
        for slot, key in material['textures'].items():
            roles[key].add(slot)
    data_slots = DATA_TEXTURE_SLOTS
    configs = {}
    for key, texture in plan['textures'].items():
        native = texture['native_settings']['m_TextureSettings']
        cube = texture['class'] == 'TextureCube'
        hdr = cube and texture['layout']['formatName'] == 'BC6H_UF16'
        mixed = bool(roles[key] & data_slots and roles[key] - data_slots)
        require(not mixed or (plan['stage'] == 'P1' and roles[key] == {'_MainTex', '_BumpMap'}),
                'one texture has unresolved color/data roles: ' + key)
        srgb = not hdr and not bool(roles[key] & data_slots)
        configs[key] = {'srgb': srgb, 'compression': 'TC_HDR' if hdr else 'TC_DEFAULT',
                        'filter': {0: 'TF_NEAREST', 1: 'TF_BILINEAR', 2: 'TF_TRILINEAR'}[native['m_FilterMode']],
                        'mip_gen_settings': 'TMGS_LEAVE_EXISTING_MIPS' if cube else 'TMGS_FROM_TEXTURE_GROUP',
                        'interpretation_authority': 'Selected UE equivalent: color slots sRGB, data slots linear; '
                            'native m_ColorSpace is retained as evidence, not interpreted as an importer flag.',
                        'source_roles': sorted(roles[key])}
        if mixed:
            configs[key]['color_decode_slots'] = ['_MainTex']
            configs[key]['interpretation_authority'] = ('Selected UE equivalent: keep the one native texture identity '
                'linear for BumpMap; explicitly decode MainTex RGB from sRGB in the material. '
                'The source DA reference is retained; original normal/importer semantics remain unverified.')
        if not cube:
            wrap = {0: 'TA_WRAP', 1: 'TA_CLAMP', 2: 'TA_MIRROR'}
            configs[key].update(address_x=wrap[native['m_WrapU']], address_y=wrap[native['m_WrapV']])
    graphs = {key: equivalent_graph(plan, material, configs) for key, material in plan['materials'].items()}
    return {'plan_digest': plan['digest'], 'policy': plan['stage'] + '_UE_Equivalent',
            'source_runtime_verified': False, 'textures': configs,
            'rendering': {'purpose': 'ue_equivalent_stage', 'materials': graphs},
            'lighting': {'purpose': 'source_numeric_ue_calibration', 'color_space': 'srgb',
                         'directional_lux_scale': 10.0, 'local_intensity_scale': 1000.0,
                         'local_falloff_exponent': 2.0, 'indirect_lighting_intensity': 1.0,
                         'volumetric_scattering_intensity': 0.0, 'spot_inner_cone_ratio': 0.8,
                         'cube_orientation': 'source_faces_unverified',
                         'differences': ['Source intensities multiplied by explicit UE calibration values; '
                             '10 lux per directional source unit, 1000 legacy unitless units per local source unit.',
                             'Source numeric colors interpreted as sRGB authoring colors and quantized by UE FColor.',
                             'Movable lights; native no-shadow flags and source range/layout retained; no extra sun/sky light.',
                             'UE box capture blending replaces Unity importance/HDR decode; DDS face orientation uncalibrated.']},
            'calibration_pending': ['Original runtime GI/exposure/variant selection', 'Lit visual color/intensity calibration',
                                    'Cubemap face orientation and probe mixing', 'Original mip pixels/normal importer semantics'],
            'collision_modified': False, 'restoration_complete': False}


def equivalent_graph(plan, material, texture_configs):
    """Build evidenced Stage shader families using explicitly selected UE expressions."""
    props = material['fields']['m_SavedProperties']
    family = plan['shaders'][material['shader']]['name'].rsplit('/', 1)[-1]
    require(family in {'Scene_Base', 'Water_Base', 'FogEffect_Texture_Additive_Soft',
                       'AirEffect_LightMap', 'Additive', 'FogEffect_Texture_Additive',
                       'AirEffect_SkyBox', 'Scene_Air_LightMap_Matcap'}, 'unsupported Stage shader family: ' + family)
    graph = {'source_material': material['identity'],
             'source_shader_sha256': plan['shaders'][material['shader']]['fields']['sha256'],
             'family': family, 'nodes': [], 'edges': [], 'outputs': [], 'two_sided': False,
             'blend_mode': 'BLEND_OPAQUE', 'shading_model': 'MSM_DEFAULT_LIT',
             'differences': ['Selected UE equivalent; no Unity GI volume, runtime shader variant, '
                             'custom stencil/SSR/SkyVisibility or original exposure provider is claimed.']}

    def add(name, cls, **spec):
        require(not any(n['id'] == name for n in graph['nodes']), 'duplicate recipe node: ' + name)
        graph['nodes'].append({'id': name, 'class': 'MaterialExpression' + cls, **spec})
        return name

    def scalar(name, value=None, native=None):
        if native is not None:
            require(native in props['m_Floats'], 'missing required source scalar: ' + native)
            return add(name, 'ScalarParameter', source_scalar=native, properties={'parameter_name': native})
        require(type(value) in (int, float) and math.isfinite(value), 'invalid UE scalar: ' + name)
        return add(name, 'ScalarParameter', properties={'parameter_name': name, 'default_value': value})

    def vector(name, value=None, native=None):
        if native is not None:
            require(native in props['m_Colors'], 'missing required source vector: ' + native)
            return add(name, 'VectorParameter', source_vector=native, properties={'parameter_name': native})
        require(len(value) == 4 and all(math.isfinite(v) for v in value), 'invalid UE vector: ' + name)
        return add(name, 'VectorParameter', properties={'parameter_name': name, 'default_value': {'linear_color': value}})

    def custom(name, code, inputs, width=3):
        add(name, 'Custom', properties={'code': code, 'description': 'UE equivalent: ' + name,
                                       'output_type': {'enum': 'CustomMaterialOutputType', 'value': 'CMOT_FLOAT' + str(width)}},
            custom_inputs=list(inputs))
        for pin, (node, output) in inputs.items():
            graph['edges'].append({'from': node, 'output': output, 'to': name, 'input': pin})
        return name

    def output(node, prop, pin=''):
        graph['outputs'].append({'node': node, 'output': pin, 'property': 'MP_' + prop})

    def ref(node, pin=''):
        return node, pin

    uv = add('SourceUV', 'TextureCoordinate', properties={'coordinate_index':
                 1 if family == 'Scene_Base' and props['m_Floats']['_UseUV2'] else 0})
    time = add('UETime', 'Time') if family == 'Water_Base' else None
    samples = {}
    for slot, key in material['textures'].items():
        texture = plan['textures'][key]
        cfg = texture_configs[key]
        sampler = 'SAMPLERTYPE_COLOR' if cfg['srgb'] else 'SAMPLERTYPE_LINEAR_COLOR'
        sample = add('Texture' + slot, 'TextureSampleParameterCube' if texture['class'] == 'TextureCube'
                     else 'TextureSampleParameter2D', source_texture=slot,
                     properties={'parameter_name': slot, 'sampler_type': {'enum': 'MaterialSamplerType', 'value': sampler}})
        samples[slot] = sample
        if texture['class'] == 'TextureCube':
            direction = add('UEReflectionVector', 'ReflectionVectorWS')
            graph['edges'].append({'from': direction, 'output': '', 'to': sample, 'input': 'UVs'})
            continue
        env = props['m_TexEnvs'][slot]
        scale = vector('UE_UVScale' + slot, [env['m_Scale']['X'], env['m_Scale']['Y'], 0., 0.])
        offset = vector('UE_UVOffset' + slot, [env['m_Offset']['X'], env['m_Offset']['Y'], 0., 0.])
        pins = {'UV': ref(uv), 'Scale': ref(scale), 'Offset': ref(offset)}
        code = 'return UV * Scale.xy + Offset.xy;'
        if family == 'Water_Base' and slot in ('_Normal01', '_Normal02'):
            index = '01' if slot == '_Normal01' else '02'
            u_name, v_name = ('_Normal01_U_Speed', '_Normal01_VSpeed') if index == '01' else ('_Normal02_U_Speed', '_Normal02_V_Speed')
            pins.update(Time=ref(time), USpeed=ref(scalar('WaterU' + index, native=u_name)),
                        VSpeed=ref(scalar('WaterV' + index, native=v_name)))
            code = 'return UV * Scale.xy + Offset.xy + Time * float2(USpeed, VSpeed);'
        coord = custom('UV' + slot, code, pins, 2)
        graph['edges'].append({'from': coord, 'output': '', 'to': sample, 'input': 'UVs'})

    def color_sample(slot):
        cfg = texture_configs[material['textures'][slot]]
        if slot not in cfg.get('color_decode_slots', []):
            return ref(samples[slot], 'RGB')
        require(not cfg['srgb'], 'explicit color decode requires a linear texture sample')
        node = custom('UEColorDecode' + slot,
                      'return lerp(RGB / 12.92, pow((RGB + 0.055) / 1.055, 2.4), step(0.04045, RGB));',
                      {'RGB': ref(samples[slot], 'RGB')})
        graph['differences'].append('Mixed color/BumpMap source identity uses raw linear sampling plus '
                                  'explicit MainTex sRGB decoding; DA pixels are not replaced by another normal resource.')
        return ref(node)

    if family == 'Scene_Base':
        main_color = color_sample('_MainTex')
        base = custom('UEBaseColor', 'return Main.rgb * Color.rgb;',
                      {'Main': main_color, 'Color': ref(vector('Color', native='_Color'))})
        output(base, 'BASE_COLOR')
        normal = custom('UENormal', 'float3 n = Normal.rgb * 2.0 - 1.0; '
                        'return normalize(float3(n.xy * Strength, max(n.z, 0.01)));',
                        {'Normal': ref(samples['_BumpMap'], 'RGB'),
                         'Strength': ref(scalar('NormalStrength', native='_NormalBlendIntensity'))})
        output(normal, 'NORMAL')
        rough = custom('UERoughness', 'return clamp(1.0 - Smoothness * Scale, 0.08, 1.0);',
                       {'Smoothness': ref(samples['_BumpMap'], 'A'), 'Scale': ref(scalar('UE_SmoothnessScale', 1.0))}, 1)
        output(rough, 'ROUGHNESS')
        output(scalar('UE_Metallic', 0.0), 'METALLIC')
        output(scalar('UE_Specular', 0.5), 'SPECULAR')
        if props['m_Floats']['_EnableAlphaTest']:
            graph.update(blend_mode='BLEND_MASKED', opacity_mask_clip_value=props['m_Floats']['_CutOff'])
            output(samples['_MainTex'], 'OPACITY_MASK', 'A')
        mask_slot = '_MaskTex' if props['m_Floats']['_UseMaskAsEmission'] else '_MainTex'
        require(mask_slot in samples, 'enabled source emission texture is missing')
        glow = custom('UEEmission', 'return Main.rgb * Color.rgb * Strength * Mask * Gain;',
                      {'Main': main_color, 'Color': ref(vector('EmissionColor', native='_EmissionColor')),
                       'Strength': ref(scalar('EmissionStrength', native='_EmissionStrength')),
                       'Mask': ref(samples[mask_slot], 'R' if mask_slot == '_MaskTex' else 'A'),
                       'Gain': ref(scalar('UE_EmissionGain', 1.0))})
        if props['m_Floats']['_EnableRimGlow']:
            fresnel = add('UERimFresnel', 'Fresnel', properties={'base_reflect_fraction': 0.0})
            graph['edges'].append({'from': scalar('RimPower', native='_RGPower'), 'output': '',
                                   'to': fresnel, 'input': 'ExponentIn'})
            glow = custom('UEEmissionAndRim', 'return Emission + Rim * Color.rgb * Strength * Gain;',
                          {'Emission': ref(glow), 'Rim': ref(fresnel), 'Color': ref(vector('RimColor', native='_RGColor')),
                           'Strength': ref(scalar('RimStrength', native='_RGStrength')), 'Gain': ref(scalar('UE_RimGain', .1))})
        output(glow, 'EMISSIVE_COLOR')
        graph['differences'].append('RGB tangent normal decoding and BumpMap alpha smoothness are explicit UE interpretations; '
                                   'UE lighting/reflection replaces source GI; emission and rim gains remain editable.')
    elif family == 'Scene_Air_LightMap_Matcap':
        require(not props['m_Floats']['_EnableMatcapSpecular'] and not props['m_Floats']['_AlphaClip']
                and not props['m_Floats']['_AlphaDither'], 'enabled Matcap/alpha mode requires its own evidenced UE recipe')
        base = custom('UEBaseColor', 'return Main.rgb * Color.rgb;',
                      {'Main': color_sample('_MainTex'), 'Color': ref(vector('Color', native='_Color'))})
        output(base, 'BASE_COLOR')
        normal = custom('UENormal', 'return normalize(Normal.rgb * 2.0 - 1.0);',
                        {'Normal': ref(samples['_BumpMap'], 'RGB')})
        output(normal, 'NORMAL')
        output(scalar('Roughness', native='_Roughness'), 'ROUGHNESS')
        output(scalar('Metallic', native='_MetalRef'), 'METALLIC')
        output(scalar('Specular', native='_SpecularIntensity'), 'SPECULAR')
        graph['differences'].append('UE Lit source color/normal/roughness replaces Unity air lightmap/GI shading; '
                                   'disabled Matcap has no substituted texture, and no emission is inferred from the material name.')
    elif family == 'Water_Base':
        graph['shading_model'] = 'MSM_SINGLE_LAYER_WATER'
        fresnel = add('UEWaterFresnel', 'Fresnel', properties={'base_reflect_fraction': 0.0})
        graph['edges'].append({'from': scalar('FresnelPower', native='_FresnelPower'), 'output': '',
                               'to': fresnel, 'input': 'ExponentIn'})
        shallow, deep = vector('ShallowColor', native='_ShallowColor'), vector('DeepColor', native='_DeepColor')
        base = custom('UEWaterColor', 'return lerp(Deep.rgb, Shallow.rgb, Fresnel);',
                      {'Deep': ref(deep), 'Shallow': ref(shallow), 'Fresnel': ref(fresnel)})
        output(base, 'BASE_COLOR')
        normal = custom('UEWaterNormal', 'float2 n = ((A.rg + B.rg) - 1.0) * Strength; '
                        'return normalize(float3(n, sqrt(max(1.0-dot(n,n), 0.01))));',
                        {'A': ref(samples['_Normal01'], 'RGB'), 'B': ref(samples['_Normal02'], 'RGB'),
                         'Strength': ref(scalar('WaterNormalStrength', native='_NormalMapScale'))})
        output(normal, 'NORMAL')
        output(scalar('UE_WaterRoughness', .08), 'ROUGHNESS')
        output(scalar('UE_WaterMetallic', 0.0), 'METALLIC')
        output(scalar('WaterSpecular', native='_SepcularValue'), 'SPECULAR')
        output(scalar('UE_WaterOpacity', .65), 'OPACITY')
        reflection = custom('UESourceWaterCube', 'return Cube.rgb * Intensity * CubeIntensity * Fresnel * Gain;',
                            {'Cube': ref(samples['_ReflectionCube'], 'RGB'),
                             'Intensity': ref(scalar('ReflectionIntensity', native='_ReflectionIntensity')),
                             'CubeIntensity': ref(scalar('CubeIntensity', native='_ReflCubeIntensity')),
                             'Fresnel': ref(fresnel), 'Gain': ref(scalar('UE_CubeGain', .1))})
        output(reflection, 'EMISSIVE_COLOR')
        water = add('UEWaterVolume', 'SingleLayerWaterMaterialOutput')
        scatter = custom('UEWaterScattering', 'return max(Shallow.rgb, 0.0) * Density;',
                         {'Shallow': ref(shallow), 'Density': ref(scalar('UE_ScatteringPerCm', .001))})
        absorb = custom('UEWaterAbsorption', 'return (1.0-saturate(Deep.rgb)) * Density;',
                        {'Deep': ref(deep), 'Density': ref(scalar('UE_AbsorptionPerCm', .001))})
        caustic = custom('UEWaterBehind', 'return lerp(float3(1,1,1), Caustic.rgb * Color.rgb * 2.0, saturate(Enabled));',
                        {'Caustic': ref(samples['_CausticTex'], 'RGB'), 'Color': ref(vector('CausticColor', native='_CausticColor')),
                         'Enabled': ref(scalar('EnableCaustics', native='_EnableCausticTex'))})
        for pin, node in [('ScatteringCoefficients', scatter), ('AbsorptionCoefficients', absorb),
                          ('PhaseG', scalar('UE_WaterPhaseG', 0.0)), ('ColorScaleBehindWater', caustic)]:
            graph['edges'].append({'from': node, 'output': '', 'to': water, 'input': pin})
        graph['differences'].append('UE SingleLayerWater replaces source WaterPlane/WaterDepth/POSM/refraction/foam providers; '
                                   'RGB/RG wave decode, per-cm volume density, opacity, roughness and cube gain are UE calibration parameters.')
    else:
        graph['shading_model'] = 'MSM_UNLIT'
        if family == 'AirEffect_SkyBox':
            require(not props['m_Floats']['_EnableTintMask'] and not props['m_Floats']['_EnableSkyDissolve'],
                    'enabled sky tint mask/dissolve requires its own evidenced UE recipe')
            sky = custom('UESkyColor', 'return Main.rgb * Color.rgb;',
                         {'Main': color_sample('_MainTex'), 'Color': ref(vector('SkyColor', native='_MainColor'))})
            output(sky, 'EMISSIVE_COLOR')
            graph.update(two_sided=True)
            graph['differences'].append('Opaque unlit two-sided UE sky retains source MainTex/MainColor and disabled '
                                       'tint/dissolve modes; original stencil/depth/global sky processing is not claimed.')
        elif family == 'AirEffect_LightMap':
            cloud = custom('UECloudColor', 'return Main.rgb * lerp(float3(1,1,1), Shadow.rgb, saturate(Intensity));',
                           {'Main': ref(samples['_MainTex'], 'RGB'), 'Shadow': ref(samples['_ShadowTex'], 'RGB'),
                            'Intensity': ref(scalar('CloudIntensity', native='_LightMapIntensity'))})
            output(cloud, 'EMISSIVE_COLOR')
            graph.update(two_sided=True)
            graph['differences'].append('Opaque unlit cloud layer with source Main/Shadow textures; two-sided UE sky visibility '
                                       'and a source-intensity color blend replace native fog/lightmap/SkyVisibility passes.')
        else:
            graph.update(blend_mode='BLEND_ADDITIVE', two_sided=True)
            color_key = '_MainColor' if family in ('FogEffect_Texture_Additive_Soft', 'FogEffect_Texture_Additive') else '_TintColor'
            color = vector('SourceTint', native=color_key)
            emit = custom('UEAdditiveColor', 'return Main.rgb * Color.rgb * Strength * Gain;',
                          {'Main': ref(samples['_MainTex'], 'RGB'), 'Color': ref(color),
                           'Strength': ref(scalar('EmissionScaler', native='_EmissionScaler')),
                           'Gain': ref(scalar('UE_EmissionGain', 1.0))})
            output(emit, 'EMISSIVE_COLOR')
            opacity = custom('UEAdditiveOpacity', 'return Alpha * TintAlpha;',
                             {'Alpha': ref(samples['_MainTex'], 'A'), 'TintAlpha': ref(color, 'A')}, 1)
            if family == 'FogEffect_Texture_Additive_Soft':
                fade = add('UESoftDepthFade', 'DepthFade', properties={'fade_distance_default': 100.0})
                graph['edges'].extend([{'from': opacity, 'output': '', 'to': fade, 'input': 'Opacity'},
                                       {'from': scalar('UE_SoftDepthFadeCm', 100.0), 'output': '', 'to': fade, 'input': 'FadeDistance'}])
                opacity = fade
            output(opacity, 'OPACITY')
            graph['differences'].append('UE additive surface and native bloom replace separate source LWForward/LWBloom; '
                                       'source tint/emission/UV preserved; optional soft depth fade is an editable UE distance, '
                                       'with no invented original global fog or distortion input.')
    return graph


def write_machine(path, value):
    path = Path(path).resolve()
    require(path.is_relative_to(PROJECT/'Saved') and not path.exists(), 'output must be a fresh project Saved file')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


BCDEC_COMMIT = '93628fe5627102fe5187b7eeb99122dec6612c36'
BCDEC_HEADER_SHA256 = 'f54dcae4a2f5dc3008f66814fb57653134a568cdce461c1b4bb3dfc7d6061204'


def raw_cube_header(width, height, mips, hdr):
    """DX10 DDS, source face order; each face contains all its original mips."""
    words=[124,0x2100f,height,width,width*(8 if hdr else 4),0,mips]+[0]*11
    words += [32,4,int.from_bytes(b'DX10','little'),0,0,0,0,0,0x401008,0xfe00,0,0,0]
    return b'DDS '+struct.pack('<31I',*words)+struct.pack('<5I',10 if hdr else 28,3,4,1,0)


def raw_cube_subresources(raw, layout):
    """Validate an uncompressed DDS and expose all 54 ranges without Unreal."""
    hdr=layout['formatName']=='BC6H_UF16'
    first=layout['mipLayout'][0]
    require(raw[:148]==raw_cube_header(first['width'],first['height'],layout['mips'],hdr),
            'decoded Cube DDS header/layout differs from its source')
    rows=[];offset=148
    for face in range(layout['faces']):
        for mip in layout['mipLayout']:
            size=mip['width']*mip['height']*(8 if hdr else 4)
            require(offset+size<=len(raw),'decoded Cube DDS is truncated')
            rows.append({'face':face,'mip':mip['mip'],'width':mip['width'],'height':mip['height'],
                         'offset':offset,'bytes':size,
                         'sha256':hashlib.sha256(raw[offset:offset+size]).hexdigest()})
            offset+=size
    require(offset==len(raw),'decoded Cube DDS has trailing/lost subresources')
    return rows


def cube_import_file(row, cfg):
    """Resolve the selected transport; source identity is never replaced."""
    if 'decoded_cube' not in cfg:return row['file']
    proof=cfg['decoded_cube']
    hdr=row['layout']['formatName']=='BC6H_UF16'
    require(row['class']=='TextureCube' and proof['source']==row['file']
            and proof['source_order_preserved'] and not proof['mips_generated']
            and proof['alpha']==(1 if hdr else 'BC1 source alpha') and proof['decoder_commit']==BCDEC_COMMIT,
            'decoded Cube transport belongs to another source or changes its layout')
    require(proof['decoder_header']['sha256']==BCDEC_HEADER_SHA256,
            'decoded Cube transport uses another decoder source')
    for key in ('decoder_header','decoder_library','file'):
        require(evidence(proof[key]['path'])==proof[key],'decoded Cube dependency/cache changed: '+key)
    require(Path(proof['file']['path']).resolve().is_relative_to(PROJECT/'Saved/BH3StageEnvironment'),
            'decoded Cube transport is outside its approved cache')
    require(raw_cube_subresources(Path(proof['file']['path']).read_bytes(),row['layout'])==proof['subresources'],
            'decoded Cube pixels/face/mip ranges changed')
    return proof['file']


def verify_exported_cube(raw, row, cfg):
    """Compare native exported Source pixels, allowing its documented BGRA swizzle."""
    require('decoded_cube' in cfg and raw[:4]==b'DDS ' and len(raw)>=148,'native Cube source export is absent/invalid')
    words=struct.unpack_from('<31I',raw,4)
    fmt,dimension,flags,array_size,_=struct.unpack_from('<5I',raw,128)
    layout=row['layout'];first=layout['mipLayout'][0];hdr=layout['formatName']=='BC6H_UF16'
    require(words[0]==124 and words[18]==32 and raw[84:88]==b'DX10'
            and words[2:4]==(first['height'],first['width']) and words[6]==layout['mips']
            and dimension==3 and flags&4 and array_size==1,'native Cube export lost face/mip/dimension layout')
    require(fmt==10 if hdr else fmt in (28,29,87,91),'native Cube source changed bit depth or HDR representation')
    offset=148
    for expected in cfg['decoded_cube']['subresources']:
        pixels=raw[offset:offset+expected['bytes']]
        require(len(pixels)==expected['bytes'],'native Cube source export is truncated')
        if not hdr and fmt in (87,91):
            rgba=bytearray(pixels)
            rgba[0::4],rgba[2::4]=pixels[2::4],pixels[0::4]
            pixels=rgba
        require(hashlib.sha256(pixels).hexdigest()==expected['sha256'],
                'native Cube source pixels differ at face '+str(expected['face'])+' mip '+str(expected['mip']))
        offset+=expected['bytes']
    require(offset==len(raw),'native Cube source export contains foreign/trailing bytes')
    return {'dxgi_format':fmt,'faces':layout['faces'],'mips':layout['mips'],
            'subresources_verified':len(cfg['decoded_cube']['subresources']),'source_pixels_exact':True,'hdr':hdr}


def prepare_cube_transports(plan, settings, decoder_root, cache_root, scope):
    """Explicit offline compatibility conversion, never an import-error fallback.

    BC6H RGB half bits pass through unchanged to RGBA16F; alpha is explicit 1.
    The caller owns the fresh cache; an error leaves evidence and propagates.
    """
    import ctypes
    decoder_root,cache_root=Path(decoder_root).resolve(),Path(cache_root).resolve()
    require(decoder_root==PROJECT/'Saved/BH3StageEnvironment/BCDecoder_20261009',
            'decoder library is outside the approved dependency cache')
    require(cache_root.is_relative_to(PROJECT/'Saved/BH3StageEnvironment') and not cache_root.exists(),
            'Cube conversion requires a fresh approved Saved cache')
    header=evidence(decoder_root/'bcdec.h');library=evidence(decoder_root/'bcdec_native.dll')
    require(header['sha256']==BCDEC_HEADER_SHA256,'decoder header differs from fixed official commit')
    decoder=ctypes.CDLL(library['path'])
    decoder.bcdec_bc1.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int]
    decoder.bcdec_bc6h_half.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
    decoder.bcdec_bc1.restype=decoder.bcdec_bc6h_half.restype=None
    probes={r['texture'] for r in plan['probes']}
    scopes = {'P3': {'probes': 2, 'surface': 1}, 'P1': {'probes': 1}}[plan['stage']]
    require(scope in scopes,'Cube conversion scope is absent from this Stage')
    selected=probes if scope=='probes' else {k for k,v in plan['textures'].items() if v['class']=='TextureCube' and k not in probes}
    require(len(selected)==scopes[scope],'Cube conversion scope differs from the accepted source plan')
    updated=json.loads(json.dumps(settings));cache_root.mkdir(parents=True)
    for key,row in plan['textures'].items():
        if key not in selected:continue
        require('decoded_cube' not in updated['textures'][key],'Cube conversion input is already derived')
        raw=Path(row['file']['path']).read_bytes();layout=row['layout']
        require(layout['faces']==6 and len(layout['mipLayout'])==layout['mips']==(9 if plan['stage']=='P3' else 11),
                'unexpected source Cube layout')
        hdr=layout['formatName']=='BC6H_UF16'
        require(layout['formatName'] in ('BC1_UNORM','BC6H_UF16'),'unsupported Cube source format')
        first=layout['mipLayout'][0];payload=bytearray()
        ranges=[];maximum=0.;over_one=0
        for face in range(6):
            for mip in layout['mipLayout']:
                w,h=mip['width'],mip['height'];pixel_bytes=8 if hdr else 4
                size=16 if hdr else 8;blocks_x=(w+3)//4;blocks_y=(h+3)//4
                start=148+face*layout['faceSize']+mip['faceByteOffset']
                compressed=raw[start:start+mip['size']]
                require(len(compressed)==blocks_x*blocks_y*size,'source Cube compressed range is invalid')
                pixels=bytearray(w*h*pixel_bytes)
                for by in range(blocks_y):
                    for bx in range(blocks_x):
                        index=(by*blocks_x+bx)*size
                        block=ctypes.create_string_buffer(compressed[index:index+size])
                        output=(ctypes.c_uint16*48)() if hdr else (ctypes.c_uint8*64)()
                        if hdr:decoder.bcdec_bc6h_half(block,output,12,0)
                        else:decoder.bcdec_bc1(block,output,16)
                        for y in range(min(4,h-by*4)):
                            for x in range(min(4,w-bx*4)):
                                p=y*4+x;offset=((by*4+y)*w+bx*4+x)*pixel_bytes
                                if hdr:
                                    rgb=[output[p*3+c] for c in range(3)]
                                    values=struct.unpack('<3e',struct.pack('<3H',*rgb))
                                    require(all(math.isfinite(v) and v>=0 for v in values),'BC6H decoded a nonfinite/negative RGB value')
                                    maximum=max(maximum,*values);over_one+=sum(v>1 for v in values)
                                    pixels[offset:offset+8]=struct.pack('<4H',*rgb,0x3c00)
                                else:
                                    pixels[offset:offset+4]=bytes(output[p*4:p*4+4])
                payload.extend(pixels)
                ranges.append({'face':face,'mip':mip['mip'],'source_offset':start,'source_bytes':mip['size'],
                               'source_sha256':hashlib.sha256(compressed).hexdigest()})
        path=cache_root/(row['package'].rsplit('/',1)[1]+('_RGBA16F.dds' if hdr else '_RGBA8.dds'))
        with path.open('xb') as stream:
            stream.write(raw_cube_header(first['width'],first['height'],layout['mips'],hdr));stream.write(payload)
        proof={'source':row['file'],'file':evidence(path),'decoder_header':header,'decoder_library':library,
               'decoder_commit':BCDEC_COMMIT,'decoder_license':'MIT (LICENSE retained in dependency cache)',
               'source_order_preserved':True,'mips_generated':False,'alpha':1 if hdr else 'BC1 source alpha',
               'source_ranges':ranges,'subresources':raw_cube_subresources(path.read_bytes(),layout),
               'hdr_rgb_max':maximum if hdr else None,'hdr_components_over_one':over_one if hdr else None,
               'transport':'BC6H unsigned RGB half bits to RGBA16F' if hdr else 'BC1 decoded RGBA8 UNORM'}
        updated['textures'][key]['decoded_cube']=proof
        cube_import_file(row,updated['textures'][key])
    return updated


def lighting_generation_digest(plan, settings):
    """Existing lamp identity comes from its accepted generation, not new surfaces."""
    if 'preserved_lighting' not in settings:return digest(settings)
    proof=settings['preserved_lighting']
    for key in ('settings','apply_result'):
        require(evidence(proof[key]['path'])==proof[key],'preserved lighting checkpoint changed: '+key)
    original=read_json(proof['settings']['path']);applied=read_json(proof['apply_result']['path'])
    require(original['plan_digest']==applied['plan_digest']==plan['digest']
            and applied['phase']=='lighting_passed' and applied['map_saved'] and not applied['materials_applied']
            and applied['settings_digest']==digest(original),'preserved lighting checkpoint is failed/foreign')
    require(settings['lighting']==original['lighting'],'surface input changes the preserved lighting policy')
    for key in {r['texture'] for r in plan['probes']}:
        require(settings['textures'][key]==original['textures'][key],'surface input changes a preserved probe Cube')
    return applied['settings_digest']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['P1', 'P3'])
    parser.add_argument('--texture-metadata', default=str(TEXTURE_METADATA), help='exact native Texture2D metadata index for the selected source supplement')
    parser.add_argument('--geometry-report')
    parser.add_argument('--settings-for-plan', help='consume an existing accepted plan; --output writes only its UE equivalent settings')
    parser.add_argument('--prepare-cubes', help='existing settings, explicitly decode the selected source Cube scope')
    parser.add_argument('--cube-scope',choices=['probes','surface'])
    parser.add_argument('--preserve-lighting-result', help='accepted saved lighting result, preserved while adding surface inputs')
    parser.add_argument('--decoder-root')
    parser.add_argument('--cube-cache')
    parser.add_argument('--output', required=True)
    parser.add_argument('--equivalent-settings-output', help='optional fresh Saved machine input for the selected UE equivalent mode')
    args = parser.parse_args()
    if args.settings_for_plan:
        require(args.stage is None and args.geometry_report is None and args.equivalent_settings_output is None,
                'settings generation consumes exactly one existing source plan')
        plan = validate_plan(read_json(args.settings_for_plan))
        settings=equivalent_settings(plan)
        if args.prepare_cubes:
            require(args.decoder_root and args.cube_cache and args.cube_scope,'Cube conversion requires its fixed decoder, scope and fresh cache')
            settings=read_json(args.prepare_cubes)
            require(settings['plan_digest']==plan['digest'],'Cube conversion settings belong to another source plan')
            settings=prepare_cube_transports(plan,settings,args.decoder_root,args.cube_cache,args.cube_scope)
            if args.preserve_lighting_result:
                require(args.cube_scope=='surface','preserved lighting requires a surface continuation')
                settings['preserved_lighting']={'settings':evidence(args.prepare_cubes),'apply_result':evidence(args.preserve_lighting_result)}
                lighting_generation_digest(plan,settings)
        write_machine(args.output,settings)
        print(json.dumps({'settings': args.output, 'plan_digest': plan['digest'], 'purpose': 'ue_equivalent_stage'}))
        return
    require(args.stage is not None and args.geometry_report is not None, 'plan generation requires stage and geometry report')
    plan = build_plan(args.stage, args.geometry_report, texture_metadata=args.texture_metadata)
    write_machine(args.output, plan)
    if args.equivalent_settings_output:
        write_machine(args.equivalent_settings_output, equivalent_settings(plan))
    print(json.dumps({'plan': args.output, 'digest': plan['digest'], 'renderers': len(plan['renderers']),
                      'slots': sum(len(r['materials']) for r in plan['renderers']),
                      'affine_meshes': len(plan['affine_meshes']), 'restoration_complete': False}))


if __name__ == '__main__':
    main()
