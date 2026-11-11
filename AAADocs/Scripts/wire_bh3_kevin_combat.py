"""制作 Kevin 装配接线，保留旧单招入口及其失败证据。

--boss-production 使用独立 production 配置，消费已保存 GA，制作阶段 BP、目标 BTS、
BB/BT 与数据接线。预检不写包；apply 必须绑定该次完整 before；readback 不修改资产。
原 assembly/combat 入口仍只解释旧自动化单招配置，不作为新 Boss 完成交付。

Runs only in the coordinator's full Editor window. Assembly needs no attack,
Socket, GE or motion curve. Combat requires the calibrated paired XYZ assets and
explicit temporary test values; it never manufactures a Profile or starts an AI tree.
Original Kevin assets and maps are read-only. Existing owned targets are compared,
never silently repaired or overwritten. Use --readback in a fresh Editor process.
Use --calibrate-basis to measure a transient native StandBy assembly. It only logs
measurements, destroys its preview and never confirms config or saves packages.
--audit-p3-support 在已打开的 P3 原生 Editor 中只读核对三组碰撞与 Pawn 胶囊查询。
该入口只把原生结果写入 Saved/KevinP3Support，不创建 Actor、修改碰撞或开始 PIE。
"""
import argparse
import hashlib
import json
import math
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Wiring_Config.json'
MONTAGES = ROOT / 'AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Montage_Config.json'
OWNER = 'GGYGO.KevinCombat.Wiring.v1'
OWNER_KEY = 'GGYGO.KevinCombat.Owner'


def require(condition, message):
    if not condition:
        raise RuntimeError('[BossAI.KevinWiring] ' + message)


def finite_values(values, count, field):
    require(isinstance(values, list) and len(values) == count, field + ' needs ' + str(count) + ' values')
    require(all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
                for x in values), field + ' must be finite')
    return values


def read_config():
    cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    require(cfg['schema_version'] == 2, 'unsupported wiring schema')
    require(cfg['base'] == '/Game/Characters/Boss/Kevin/DemonBattle', 'unexpected asset namespace')
    require(cfg['attack_trigger'] == 'automation_only' and cfg['behavior_tree'] == '',
            'this delivery has no automatic attack or targeting policy')
    paths = list(cfg['assets'].values()) + [row['ability'] for row in cfg['actions']]
    require(len(set(paths)) == len(paths), 'output package paths must be unique')
    require(all(path.startswith(cfg['base'] + '/') and '.' not in path for path in paths),
            'outputs must be dedicated package paths')
    require(len(cfg['actions']) == 1 and cfg['actions'][0]['id'] == cfg['initial_action'],
            'only the selected first action belongs to this delivery')
    finite_values(cfg['mesh_relative_location'], 3, 'mesh_relative_location')
    finite_values(cfg['mesh_relative_rotation'], 3, 'mesh_relative_rotation')
    scale = finite_values(cfg['mesh_relative_scale'], 3, 'mesh_relative_scale')
    require(scale[0] > 0 and scale[0] == scale[1] == scale[2], 'assembly scale must be positive and uniform')
    radius, height = cfg['capsule_radius'], cfg['capsule_half_height']
    require(all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in (radius, height))
            and 0 < radius <= height, 'capsule needs finite height >= radius > 0')
    return cfg


def compiled_blueprint(unreal, bp):
    status = bp.get_editor_property('Status')
    require(status == unreal.BlueprintStatus.BS_UP_TO_DATE,
            'Blueprint is not compiled without warnings: ' + bp.get_path_name() + ' status=' + str(status))
    cls = bp.generated_class()
    require(cls is not None, 'Blueprint has no generated class: ' + bp.get_path_name())
    return cls


def verify_single_main_section(unreal, montage):
    """只读原生 Section 导出；完整核对唯一 Main、Absolute 零起点和终止链接。"""
    require(montage.get_num_sections() == 1 and str(montage.get_section_name(0)) == 'Main',
            'expected exactly one Main section: ' + montage.get_path_name())
    filename = ROOT / 'Saved/Codex' / ('kevin_montage_sections_' + uuid.uuid4().hex + '.t3d')
    filename.parent.mkdir(parents=True, exist_ok=True)
    require(not filename.exists(), 'native Section audit export already exists: ' + str(filename))
    task = unreal.AssetExportTask()
    task.set_editor_property('object', montage)
    task.set_editor_property('exporter', unreal.ObjectExporterT3D())
    task.set_editor_property('filename', str(filename))
    task.set_editor_property('automated', True)
    task.set_editor_property('prompt', False)
    task.set_editor_property('replace_identical', False)
    require(unreal.Exporter.run_asset_export_task(task) and filename.is_file(),
            'native Section export failed: ' + montage.get_path_name() + ' audit=' + str(filename))
    text = filename.read_text(encoding='utf-8-sig')
    require(re.search(r'^Begin Object Class=/Script/Engine.AnimMontage Name="'
                      + re.escape(montage.get_name()) + r'"', text),
            'native Section export is not the target Montage: ' + str(filename))
    sections, depth = {}, 0
    for line in text.splitlines():
        if re.match(r'^\s*Begin Object\b', line):
            depth += 1
        elif re.match(r'^\s*End Object\s*$', line):
            depth -= 1
            require(depth >= 0, 'unbalanced native Section export: ' + str(filename))
        elif depth == 1 and re.match(r'^\s*CompositeSections\b', line):
            section = re.match(r'^\s*CompositeSections\((\d+)\)=(.*)$', line)
            require(section is not None, 'unreadable native Section record: ' + str(filename))
            index = int(section.group(1))
            require(index not in sections, 'duplicate native Section record: ' + str(filename))
            sections[index] = section.group(2)
    require(depth == 0 and sorted(sections) == [0], 'native export needs exactly Section 0: ' + str(filename))
    raw = sections[0]
    names = re.findall(r'(?:^|[,\(])SectionName="([^"]+)"(?=[,\)])', raw)
    require(names == ['Main'], 'native Section name/getter disagree: ' + str(filename))
    next_names = re.findall(r'(?:^|[,\(])NextSectionName="([^"]+)"(?=[,\)])', raw)
    # 原生 T3D 省略构造默认；FCompositeSection 的 NextSectionName 构造值为 NAME_None。
    require(next_names == ['None'] or (not next_names and 'NextSectionName=' not in raw),
            'Main must have no next section: ' + str(filename))
    # 同一 FAnimLinkableElement 基类的实际默认；Notify 的 EndLink 在前，主链字段在后。
    defaults = unreal.AnimNotifyEvent().export_text()

    def link_field(name):
        pattern = r'(?:^|[,\(])' + name + r'=([^,\)]+)(?=[,\)])'
        actual = re.findall(pattern, raw)
        require(len(actual) <= 1, 'ambiguous native Section ' + name + ': ' + str(filename))
        if actual:
            return actual[0]
        values = re.findall(pattern, defaults)
        require(values, 'native link constructor default unavailable: ' + name)
        return values[-1]

    require(link_field('LinkMethod') == 'Absolute', 'Main must use Absolute time: ' + str(filename))
    start = float(link_field('LinkValue'))
    require(math.isfinite(start) and start == 0.0, 'Main must start at zero: ' + str(filename))


def calibration_bounds(points):
    require(points, 'empty body surface cannot supply calibration bounds')
    return {'vertices': len(points), 'min_actor_cm': [min(p[axis] for p in points) for axis in range(3)],
            'max_actor_cm': [max(p[axis] for p in points) for axis in range(3)]}


def calibration_body_geometry(unreal, component, component_to_actor):
    """Read posed LOD0 surfaces by material; all scratch data belongs to this call."""
    mesh = component.get_skeletal_mesh_asset()
    # The public materials descriptor invokes the native BlueprintGetter and its async read barrier.
    slots = [str(slot.get_editor_property('MaterialSlotName')) for slot in mesh.materials]
    body_slots = ('BOSS_411_Material_Body01', 'BOSS_411_Material_Body02', 'BOSS_411_Material_Face')
    require(all(slots.count(name) == 1 for name in body_slots),
            mesh.get_path_name() + ': exact unique Body01/Body02/Face material slots required')
    # The public Python constructor creates the receiver in the transient package.
    scratch = unreal.DynamicMesh()
    try:
        options = unreal.GeometryScriptCopyMeshFromComponentOptions()
        lod = unreal.GeometryScriptMeshReadLOD()
        lod.set_editor_property('LODType', unreal.GeometryScriptLODType.RENDER_DATA)
        lod.set_editor_property('LODIndex', 0)
        options.set_editor_property('RequestedLOD', lod)
        options.set_editor_property('bWantNormals', False)
        options.set_editor_property('bWantTangents', False)
        copied, component_to_world, outcome = unreal.GeometryScript_SceneUtils.copy_mesh_from_component(
            component, scratch, options, False)
        require(copied == scratch and outcome == unreal.GeometryScriptOutcomePins.SUCCESS,
                component.get_path_name() + ': native CPU-skinned LOD0 geometry copy failed; mesh='
                + mesh.get_path_name() + ' requested=RenderData:0 copied_is_receiver=' + str(copied == scratch)
                + ' component_lods=' + str(component.get_num_lods()) + ' outcome=' + str(outcome)
                + ' return_types=' + repr([type(value).__name__ for value in (copied, component_to_world, outcome)]))
        # UE's Python name generation splits the native trailing "IDs" into "I_Ds".
        require(unreal.GeometryScript_MeshQueries.get_has_material_i_ds(scratch),
                component.get_path_name() + ': posed geometry has no material partition')
        points = {}
        sections = {}
        anatomical_roots = ('Bip001-L-Foot', 'Bip001-R-Foot', 'Bip001-Head')
        bone_names = [str(component.get_bone_name(index)) for index in range(component.get_num_bones())]
        bone_groups = {root: {index for index, name in enumerate(bone_names)
                              if name == root or component.bone_is_child_of(name, root)} for root in anatomical_roots}
        surfaces = {root: [] for root in anatomical_roots}
        for name in body_slots:
            receiver, triangle_list = unreal.GeometryScript_Materials.get_triangles_by_material_id(scratch, slots.index(name))
            require(receiver == scratch, 'material query returned another geometry receiver: ' + name)
            triangles = list(unreal.GeometryScript_List.convert_index_list_to_array(triangle_list))
            require(triangles, 'posed LOD0 has no body triangles: ' + name)
            vertices = set()
            for triangle in triangles:
                indices, valid = unreal.GeometryScript_MeshQueries.get_triangle_indices(scratch, triangle)
                require(valid, 'invalid posed body triangle: ' + name + ':' + str(triangle))
                vertices.update((indices.x, indices.y, indices.z))
            for vertex in vertices:
                if vertex not in points:
                    position, valid = unreal.GeometryScript_MeshQueries.get_vertex_position(scratch, vertex)
                    require(valid, 'invalid posed body vertex: ' + str(vertex))
                    position = component_to_actor.transform_location(position)
                    row = [position.x, position.y, position.z]
                    finite_values(row, 3, 'posed body vertex ' + str(vertex))
                    points[vertex] = row
                    receiver, influence, valid = unreal.GeometryScript_BoneWeights.get_largest_vertex_bone_weight(scratch, vertex)
                    bone_index = influence.get_editor_property('BoneIndex')
                    weight = float(influence.get_editor_property('Weight'))
                    require(receiver == scratch and valid and math.isfinite(weight) and weight > 0
                            and 0 <= bone_index < len(bone_names), 'missing/invalid posed body skin influence: ' + str(vertex))
                    for root, group in bone_groups.items():
                        if bone_index in group:
                            surfaces[root].append(row)
            section_points = [points[vertex] for vertex in vertices]
            sections[name] = {'triangles': len(triangles), **calibration_bounds(section_points)}
        anatomical_surfaces = {root: calibration_bounds(surface) for root, surface in surfaces.items()}
        return list(points.values()), sections, anatomical_surfaces, component_to_world
    finally:
        scratch.reset()


def calibrate_basis():
    """Measure the configured candidate in the native Editor; no asset or config writes.

    The sole preview Actor owns Mesh/Capsule/AnimInstance resources and is destroyed
    on both success and failure. Editor transaction dirtiness is reported, never cleared.
    Geometry covers Body01/Body02/Face only; capsule policy and visual approval remain external.
    """
    import unreal
    cfg = read_config()
    command_line = unreal.SystemLibrary.get_command_line()
    require(not re.search(r'(?:^|\s)-run=', command_line, re.IGNORECASE),
            'basis calibration requires the full native Editor, not a Commandlet host')
    require(not re.search(r'(?:^|\s)-nullrhi(?:\s|$)', command_line, re.IGNORECASE),
            cfg['mesh'] + ': posed RenderData LOD0 calibration requires a rendering Editor host; '
            '-NullRHI disables FApp::CanEverRender and prevents the required native MeshObject creation')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    require(levels is not None and actors is not None and not levels.is_in_play_in_editor(),
            'basis calibration requires the full Editor with inactive PIE')
    montage_cfg = json.loads(MONTAGES.read_text(encoding='utf-8-sig'))
    idle_cfg = montage_cfg['anim_blueprint']
    require(idle_cfg['asset'] == cfg['anim_blueprint'] and idle_cfg['mode'] == 'guard_standard_slot_idle_loop',
            'basis calibration requires the configured ordinary-slot StandBy ABP')
    mesh = unreal.load_asset(cfg['mesh'])
    abp = unreal.load_asset(cfg['anim_blueprint'])
    idle = unreal.load_asset(idle_cfg['idle_sequence'])
    require(isinstance(mesh, unreal.SkeletalMesh) and isinstance(abp, unreal.AnimBlueprint)
            and isinstance(idle, unreal.AnimSequence),
            'missing/wrong calibration Mesh, ABP or StandBy: ' + repr([cfg['mesh'], cfg['anim_blueprint'], idle_cfg['idle_sequence']]))
    skeleton = mesh.get_editor_property('skeleton')
    require(skeleton is not None and abp.get_editor_property('TargetSkeleton') == skeleton
            and idle.get_editor_property('skeleton') == skeleton, 'calibration Mesh/ABP/StandBy Skeleton mismatch')
    cls = compiled_blueprint(unreal, abp)
    require(unreal.MathLibrary.class_is_child_of(cls, unreal.GGYGOMontageGuardAnimInstance.static_class())
            and str(unreal.get_default_object(cls).get_editor_property('RequiredPoseCorrectionSlot')) == 'None',
            'calibration ABP must use ordinary-slot Guard mode')
    dirty_content = unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    require(all(obj.get_outer() not in dirty_content for obj in (mesh, abp, idle, skeleton)),
            'calibration dependency is dirty; preserve and freeze its original author first')
    before_content = {p.get_name() for p in dirty_content}
    before_maps = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
    selected = list(actors.get_selected_level_actors())
    options = unreal.AnimPoseEvaluationOptions()
    options.set_editor_property('EvaluationType', unreal.AnimDataEvalType.COMPRESSED)
    options.set_editor_property('bShouldRetarget', True)
    options.set_editor_property('bExtractRootMotion', False)
    options.set_editor_property('bIncorporateRootMotionIntoPose', True)
    options.set_editor_property('OptionalSkeletalMesh', mesh)
    options.set_editor_property('bEvaluateCurves', False)
    source_pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(idle, 0.0, options)
    require(unreal.AnimPoseExtensions.is_valid(source_pose), 'native StandBy t=0 pose evaluation failed: ' + idle.get_path_name())
    anchors = ('Bip001-Pelvis', 'Bip001-Head', 'Bip001-HeadNub',
               'Bip001-L-Foot', 'Bip001-R-Foot', 'Bip001-L-Toe0', 'Bip001-R-Toe0')
    pose_names = {str(name) for name in unreal.AnimPoseExtensions.get_bone_names(source_pose)}
    require(set(anchors).issubset(pose_names), 'StandBy is missing exact imported body anchors: ' + repr(sorted(set(anchors) - pose_names)))
    preview = None
    result = None
    try:
        preview = actors.spawn_actor_from_class(unreal.GGYGOBossCharacter, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0), True)
        require(preview is not None, 'failed to spawn transient native BossCharacter calibration receiver')
        require(preview.get_editor_property('AutoPossessAI') == unreal.AutoPossessAI.DISABLED,
                'calibration native BossCharacter would create an automatic Controller')
        preview.set_actor_enable_collision(False)
        component = preview.get_editor_property('Mesh')
        capsule = preview.get_editor_property('CapsuleComponent')
        require(component is not None and capsule is not None, 'native calibration Actor lacks Mesh/Capsule')
        require(preview.get_editor_property('RootComponent') == capsule and component.get_attach_parent() == capsule,
                'native calibration Mesh must attach directly to the authoritative Capsule root')
        require(component.get_editor_property('bEnableAnimation')
                and not component.get_editor_property('bUseRefPoseOnInitAnim'),
                'native calibration Mesh would initialize without an evaluated animation pose')
        component.set_visibility(True)
        component.set_skeletal_mesh_asset(mesh)
        # Python exposes override_min_lod as the editor flag, shadowing the native method.
        # The public setter changes MinLodModel; this editable flag enables its use.
        component.set_editor_property('bOverrideMinLod', True)
        component.set_min_lod(0)
        component.set_forced_lod(1)
        require(component.get_editor_property('bOverrideMinLod')
                and component.get_editor_property('MinLodModel') == 0 and component.get_forced_lod() == 1,
                'native calibration Mesh refused exact LOD0 selection')
        capsule.set_capsule_size(cfg['capsule_radius'], cfg['capsule_half_height'])
        basis = cfg['motion_asset_basis']
        require(isinstance(basis['confirmed'], bool), 'motion_asset_basis.confirmed must be explicit boolean')
        angles = cfg['mesh_relative_rotation']
        rotation = unreal.Rotator(pitch=angles[0], yaw=angles[1], roll=angles[2])
        scale = cfg['mesh_relative_scale']
        if basis['confirmed']:
            quat = finite_values(basis['mesh_relative_rotation_xyzw'], 4, 'confirmed calibration rotation')
            require(abs(sum(x * x for x in quat) - 1.0) <= 0.00001, 'confirmed calibration rotation must be normalized')
            scale = finite_values(basis['mesh_relative_scale'], 3, 'confirmed calibration scale')
            require(scale[0] > 0 and scale[0] == scale[1] == scale[2], 'confirmed calibration scale must be positive and uniform')
            rotation = unreal.Quat(*quat).rotator()
        component.set_editor_property('RelativeLocation', unreal.Vector(*cfg['mesh_relative_location']))
        component.set_editor_property('RelativeRotation', rotation)
        component.set_relative_scale3d(unreal.Vector(*scale))
        # SetAnimInstanceClass -> InitAnim evaluates and refreshes synchronously in an Editor world.
        # The exact StandBy anchor comparison rejects ref-pose or another graph result.
        component.set_anim_instance_class(cls)
        instance = component.get_anim_instance()
        require(instance is not None and instance.get_class() == cls
                and instance.get_current_active_montage() is None, 'calibration has no clean actual StandBy AnimInstance')
        actor_transform = preview.get_actor_transform()
        relative = unreal.MathLibrary.make_relative_transform(component.get_world_transform(), actor_transform)
        actor_scale = actor_transform.scale3d
        require([actor_scale.x, actor_scale.y, actor_scale.z] == [1.0, 1.0, 1.0], 'calibration native Actor scale must be identity')
        anchor_rows = {}
        for name in anchors:
            require(component.get_bone_index(name) >= 0, 'calibration Mesh is missing exact bone ' + name)
            actual = component.get_socket_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT).translation
            expected = unreal.AnimPoseExtensions.get_bone_pose(source_pose, name, unreal.AnimPoseSpaces.WORLD).translation
            error = math.sqrt(sum((a - b) ** 2 for a, b in zip((actual.x, actual.y, actual.z), (expected.x, expected.y, expected.z))))
            require(math.isfinite(error) and error <= 0.2,
                    'ABP initial body anchor differs from native compressed StandBy t=0: ' + name + ' error_cm=' + str(error))
            local = relative.transform_location(actual)
            anchor_rows[name] = {'component_cm': [actual.x, actual.y, actual.z],
                                 'actor_cm': [local.x, local.y, local.z], 'standby_error_cm': error}
        points, sections, anatomical_surfaces, component_world = calibration_body_geometry(unreal, component, relative)
        bounds = calibration_bounds(points)
        lower, upper = bounds['min_actor_cm'], bounds['max_actor_cm']
        radius, height = capsule.get_unscaled_capsule_radius(), capsule.get_unscaled_capsule_half_height()
        segment_half = height - radius
        distances = [math.sqrt(point[0] ** 2 + point[1] ** 2 + max(abs(point[2]) - segment_half, 0.0) ** 2) for point in points]
        feet = [anchor_rows['Bip001-' + side + '-Foot']['actor_cm'] for side in ('L', 'R')]
        toes = [anchor_rows['Bip001-' + side + '-Toe0']['actor_cm'] for side in ('L', 'R')]
        forward = [sum(toes[side][axis] - feet[side][axis] for side in range(2)) * 0.5 for axis in range(3)]
        require(math.hypot(forward[0], forward[1]) > 0.0001, 'StandBy feet/toes do not define a finite horizontal facing reference')
        head = anchor_rows['Bip001-Head']['actor_cm']
        up = [head[axis] - sum(foot[axis] for foot in feet) * 0.5 for axis in range(3)]
        q, s, p = relative.rotation, relative.scale3d, relative.translation
        actual_basis = {'mesh_relative_rotation_xyzw': [q.x, q.y, q.z, q.w], 'mesh_relative_scale': [s.x, s.y, s.z]}
        finite_values(actual_basis['mesh_relative_rotation_xyzw'], 4, 'actual Mesh-to-Actor quaternion')
        finite_values(actual_basis['mesh_relative_scale'], 3, 'actual Mesh-to-Actor scale')
        require(abs(sum(value * value for value in actual_basis['mesh_relative_rotation_xyzw']) - 1.0) <= 0.00001
                and s.x > 0 and s.x == s.y == s.z, 'actual Mesh-to-Actor basis is not normalized/positive uniform')
        soles = {side: anatomical_surfaces['Bip001-' + side + '-Foot']['min_actor_cm'][2] for side in ('L', 'R')}
        result = {'status': 'measured_candidate_requires_review', 'config': str(CONFIG),
                  'mesh': mesh.get_path_name(), 'anim_blueprint': abp.get_path_name(), 'standby': idle.get_path_name(),
                  'pose': 'native_ABP_initial_pose_matches_compressed_StandBy_t0', 'pose_tolerance_cm': 0.2,
                  'actor': preview.get_path_name(), 'basis': actual_basis, 'mesh_relative_location': [p.x, p.y, p.z],
                  'mesh_to_actor': relative.export_text(), 'component_to_world': component_world.export_text(),
                  'actor_to_world': actor_transform.export_text(),
                  'actor_to_mesh': unreal.MathLibrary.invert_transform(relative).export_text(),
                  'actor_to_mesh_rotation_xyzw': [-q.x, -q.y, -q.z, q.w], 'actor_to_mesh_scale': [1.0 / s.x, 1.0 / s.y, 1.0 / s.z],
                  'anchors': anchor_rows, 'body_sections': sections, 'body_vertex_count': len(points),
                  'body_bounds_actor_cm': {'min': lower, 'max': upper, 'height': upper[2] - lower[2]},
                  'anatomical_surfaces': anatomical_surfaces,
                  'surface_classification': 'Body01/Body02/Face vertices grouped by actual largest skin influence in Foot/Head bone hierarchies',
                  'feet_to_toes_actor_cm': forward, 'feet_to_head_actor_cm': up,
                  'facing_yaw_from_actor_x_degrees': math.degrees(math.atan2(forward[1], forward[0])),
                  'capsule': {'radius': radius, 'half_height': height, 'bottom_actor_z': -height, 'top_actor_z': height,
                              'body_min_above_bottom_cm': lower[2] + height,
                              'sole_above_bottom_cm': {side: sole + height for side, sole in soles.items()},
                              'sole_alignment_mesh_delta_z_cm': -height - min(soles.values()),
                              'body_top_below_capsule_top_cm': height - upper[2],
                              'head_surface_top_actor_z': anatomical_surfaces['Bip001-Head']['max_actor_cm'][2],
                              'sole_to_head_surface_span_cm': anatomical_surfaces['Bip001-Head']['max_actor_cm'][2] - min(soles.values()),
                              'face_top_actor_z': sections['BOSS_411_Material_Face']['max_actor_cm'][2],
                              'outside_body_vertices': sum(distance > radius + 0.0001 for distance in distances),
                              'max_body_surface_outside_cm': max(0.0, max(distances) - radius)},
                  'confirmed_written': False, 'saved': [], 'runtime_ready_verified': False,
                  'excluded_surfaces': 'weapon, wings, hair, eye; body feet/head bones are distinct from surface extrema'}
    finally:
        destroyed = preview is None or actors.destroy_actor(preview)
        after_content = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        after_maps = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
        selection_unchanged = list(actors.get_selected_level_actors()) == selected
        cleanup = {'transient_actor_destroyed': destroyed, 'content_dirty_unchanged': after_content == before_content,
                   'map_dirty_added': sorted(after_maps - before_maps), 'map_dirty_removed': sorted(before_maps - after_maps),
                   'selection_unchanged': selection_unchanged, 'packages_saved': []}
        unreal.log('KEVIN_BASIS_CALIBRATION_CLEANUP ' + json.dumps(cleanup, ensure_ascii=False))
        require(destroyed, 'failed to destroy the sole transient calibration Actor')
        require(after_content == before_content and selection_unchanged,
                'calibration changed content dirtiness or existing Actor selection; preserve the Editor for inspection')
    result['cleanup'] = cleanup
    unreal.log('KEVIN_BASIS_CALIBRATION ' + json.dumps(result, ensure_ascii=False))
    return result


def run(apply=False, batch='assembly', readback=False):
    import unreal
    cfg = read_config()
    require(batch in ('assembly', 'combat'), 'unknown batch')
    require(not (apply and readback), '--apply and --readback are mutually exclusive')
    require(not re.search(r'(?:^|\s)-run=', unreal.SystemLibrary.get_command_line(), re.IGNORECASE),
            'use the full native Editor, not a Commandlet host')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    require(levels is not None and not levels.is_in_play_in_editor(), 'full Editor with inactive PIE required')
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    eal = unreal.EditorAssetLibrary
    records = []
    targets = {}
    saved = []
    install_attack = False

    def load(path):
        obj = unreal.load_object(None, path) if '.' in path else unreal.load_asset(path)
        require(obj is not None, 'missing dependency ' + path)
        return obj

    def tag(name):
        value = unreal.GameplayTag()
        value.import_text('(TagName="' + name + '")')
        actual = str(value.get_editor_property('TagName'))
        # Python import_text uses PPF_None: native import clears unregistered names.
        # Exact round trip also rejects redirects; IsGameplayTagValid only checks non-null.
        require(actual == name if name else actual in ('', 'None'),
                'GameplayTag import differs: requested=' + name + ' imported=' + actual + ' config=' + str(CONFIG))
        require(not name or unreal.GameplayTagLibrary.is_gameplay_tag_valid(value),
                'GameplayTag is invalid: ' + name + ' config=' + str(CONFIG))
        return value

    def comparable(value):
        if isinstance(value, unreal.Name):
            return str(value)
        if isinstance(value, unreal.Object):
            return value.get_path_name()
        if isinstance(value, (list, tuple, unreal.Array)):
            return [comparable(item) for item in value]
        if hasattr(value, 'export_text'):
            return value.export_text()
        return value

    def check_properties(obj, values):
        require(obj is not None, 'missing receiver during existing asset comparison')
        for key, expected in values.items():
            actual = obj.get_editor_property(key)
            # Scalar UPROPERTY floats round to float32 when written; allow only that
            # representation error. Object identities, enums and structured fields stay exact.
            numeric = (isinstance(actual, (int, float)) and not isinstance(actual, bool)
                       and isinstance(expected, (int, float)) and not isinstance(expected, bool)
                       and (isinstance(actual, float) or isinstance(expected, float)))
            equal = (math.isfinite(actual) and math.isfinite(expected)
                     and math.isclose(actual, expected, rel_tol=0.0000001, abs_tol=0.00000001)
                     if numeric else comparable(actual) == comparable(expected))
            require(equal,
                    obj.get_path_name() + '.' + key + ' differs; preserve existing content and reconcile explicitly')

    mesh = load(cfg['mesh'])
    abp = load(cfg['anim_blueprint'])
    abp_class = compiled_blueprint(unreal, abp)
    skeleton = mesh.get_editor_property('skeleton')
    require(skeleton is not None and abp.get_editor_property('TargetSkeleton') == skeleton, 'Mesh/ABP Skeleton mismatch')
    require(unreal.MathLibrary.class_is_child_of(abp_class, unreal.GGYGOMontageGuardAnimInstance.static_class()),
            'ABP must inherit the owned-playback Guard')
    require(str(unreal.get_default_object(abp_class).get_editor_property('RequiredPoseCorrectionSlot')) == 'None',
            'derived in-place assets require explicit ordinary-slot mode')
    basis = cfg['motion_asset_basis']
    require(isinstance(basis['confirmed'], bool), 'motion_asset_basis.confirmed must be explicit boolean')
    angles = cfg['mesh_relative_rotation']
    rotation = unreal.Rotator(pitch=angles[0], yaw=angles[1], roll=angles[2])
    scale = unreal.Vector(*cfg['mesh_relative_scale'])
    if basis['confirmed']:
        quat = finite_values(basis['mesh_relative_rotation_xyzw'], 4, 'motion_asset_basis.rotation')
        basis_scale = finite_values(basis['mesh_relative_scale'], 3, 'motion_asset_basis.scale')
        require(abs(sum(x * x for x in quat) - 1.0) <= 0.00001, 'confirmed basis rotation must be normalized')
        require(basis_scale[0] > 0 and basis_scale[0] == basis_scale[1] == basis_scale[2],
                'confirmed basis scale must be positive and uniform')
        rotation = unreal.Quat(*quat).rotator()
        scale = unreal.Vector(*basis_scale)
    else:
        require(batch == 'assembly', 'combat needs the actual confirmed Mesh-to-Actor basis')
    require(not apply or basis['confirmed'], 'saving the production assembly requires its confirmed Mesh-to-Actor basis')
    montage = damage_effect = None
    action_tag = None
    row = cfg['actions'][0]
    if batch == 'combat':
        require(cfg['combat_tuning_status'] == 'temporary_automation_test_initial_values_not_balance',
                'combat values must explicitly identify their temporary test purpose')
        require(not row.get('motion_profile'), 'new Kevin combat must not consume a legacy CV/DA Profile')
        montage_cfg = json.loads(MONTAGES.read_text(encoding='utf-8-sig'))
        require(montage_cfg['selected_actions'] == [row['source_clip']], 'Animation selection differs from first action')
        specs = [spec for spec in montage_cfg['actions'] if spec['source_clip'] == row['source_clip']]
        require(len(specs) == 1, 'selected action has no unique Montage specification')
        spec = specs[0]
        require(spec.get('window_source') == 'manual_candidate' and spec.get('test_only') is True
                and spec.get('original_game_window_known') is False,
                'selected action needs an explicit project automation test window; source-game timing remains unknown')
        require(spec.get('hit_windows_confirmed') is True,
                'selected project automation test window has not been technically confirmed')
        require(spec['damage_enabled'] and spec['hit_windows'] and spec['sequence_override'],
                'selected action needs explicit derived source and hit windows')
        montage = load(row['montage'])
        sequence = load(spec['sequence_override'])
        require(montage.get_editor_property('skeleton') == skeleton
                and sequence.get_editor_property('skeleton') == skeleton, 'selected motion Skeleton mismatch')
        require(eal.get_metadata_tag(sequence, 'GGYGO.MotionBuilder') == 'KevinMontageXYZ.v2'
                and eal.get_metadata_tag(sequence, 'GGYGO.MotionCurveSpace') == 'ActorLocalCmXYZ.v1',
                'derived sequence does not identify the paired XYZ producer/space')
        paired_basis = json.loads(eal.get_metadata_tag(sequence, 'GGYGO.MotionAssetBasis'))
        require(paired_basis == basis, 'derived XYZ asset basis differs from the actual configured assembly')
        require(not sequence.get_editor_property('bEnableRootMotion'), 'native animation RootMotion must be disabled')
        slots = montage.get_editor_property('SlotAnimTracks')
        require(len(slots) == 1 and str(slots[0].get_editor_property('SlotName')) == 'DefaultSlot', 'expected one DefaultSlot')
        segments = slots[0].get_editor_property('AnimTrack').get_editor_property('AnimSegments')
        require(len(segments) == 1, 'expected one complete linear source segment')
        segment = segments[0]
        length = float(montage.get_editor_property('SequenceLength'))
        require(math.isfinite(length) and length > 0, 'invalid Montage duration')
        require(segment.get_editor_property('AnimReference') == sequence
                and int(segment.get_editor_property('LoopingCount')) == 1
                and float(segment.get_editor_property('AnimPlayRate')) == 1.0
                and float(segment.get_editor_property('StartPos')) == 0.0
                and float(segment.get_editor_property('AnimStartTime')) == 0.0
                and abs(float(segment.get_editor_property('AnimEndTime')) - length) <= 0.001
                and abs(float(sequence.get_editor_property('SequenceLength')) - length) <= 0.001,
                'source segment must cover the entire paired sequence once')
        verify_single_main_section(unreal, montage)
        require(montage.get_editor_property('bEnableAutoBlendOut'), 'expected one naturally terminating Main')
        grid = None
        for name in ('RootMotion_PosX', 'RootMotion_PosY', 'RootMotion_PosZ'):
            times, values = unreal.AnimationLibrary.get_float_keys(sequence, name)
            require(len(times) >= 2 and len(times) == len(values)
                    and all(math.isfinite(x) for x in list(times) + list(values))
                    and abs(times[0]) <= 0.000001 and abs(times[-1] - length) <= 0.001
                    and all(a < b for a, b in zip(times, times[1:])), 'required complete finite curve missing: ' + name)
            require(grid is None or list(times) == grid, 'XYZ axes do not share the original complete key grid')
            grid = list(times)
        for name in (cfg['trace_start_socket'], cfg['trace_end_socket']):
            socket = mesh.find_socket(name)
            require(socket is not None and str(socket.get_editor_property('BoneName')) == montage_cfg['socket_config']['parent_bone'],
                    'missing real weapon Socket ' + name)
        actual_windows = []
        for event in unreal.AnimationLibrary.get_animation_notify_events(montage):
            state = event.get_editor_property('NotifyStateClass')
            if isinstance(state, unreal.GGYGOAnimNotifyState_GameplayEventWindow):
                begin = str(state.get_editor_property('BeginEventTag').get_editor_property('TagName'))
                end = str(state.get_editor_property('EndEventTag').get_editor_property('TagName'))
                require(begin == 'Event.Montage.HitWindowBegin' and end == 'Event.Montage.HitWindowEnd', 'unexpected melee event pair')
                require(event.get_editor_property('LinkMethod') == unreal.AnimLinkMethod.ABSOLUTE, 'expected Absolute window times')
                start = float(unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event))
                duration = float(unreal.AnimationLibrary.get_anim_notify_event_duration(event))
                require(math.isfinite(start) and math.isfinite(duration), 'nonfinite native hit window')
                actual_windows.append((start, start + duration))
        expected = sorted((w['start_frame'] / spec['frame_rate'], w['end_frame'] / spec['frame_rate']) for w in spec['hit_windows'])
        actual_windows.sort()
        require(len(actual_windows) == len(expected), 'actual hit window count differs')
        for index, (actual, authored) in enumerate(zip(actual_windows, expected)):
            require(all(abs(a - b) <= 0.001 for a, b in zip(actual, authored))
                    and 0 <= actual[0] < actual[1] <= length
                    and (index == 0 or actual_windows[index - 1][1] < actual[0]), 'invalid or different hit window')
        for key in ('play_rate', 'trace_radius', 'damage', 'poise_damage'):
            require(isinstance(row[key], (int, float)) and not isinstance(row[key], bool)
                    and math.isfinite(row[key]), 'nonfinite combat tuning ' + key)
        require(row['play_rate'] > 0 and row['trace_radius'] >= 1 and row['damage'] >= 0 and row['poise_damage'] >= 0,
                'invalid combat tuning')
        damage_effect = load(cfg['damage_effect'])
        require(unreal.MathLibrary.class_is_child_of(damage_effect, unreal.GameplayEffect.static_class()),
                'damage_effect must be a GameplayEffect class')
        damage_definition = unreal.get_default_object(damage_effect)
        executions = damage_definition.get_editor_property('Executions')
        require(damage_definition.get_editor_property('DurationPolicy') == unreal.GameplayEffectDurationType.INSTANT
                and len(executions) == 1
                and executions[0].get_editor_property('CalculationClass') == unreal.GGYGODamageExecution.static_class()
                and not executions[0].get_editor_property('CalculationModifiers')
                and not damage_definition.get_editor_property('Modifiers'),
                'selected damage GE must use the existing Instant DamageExecution without extra modifiers')
        action_tag = tag(row['action_tag'])
    form_tag, phase_tag = tag(cfg['form_tag']), tag(cfg['phase_tag'])
    cue_tag = tag(cfg['hit_cue'])
    definitions = {
        'movement': (cfg['assets']['movement'], unreal.GGYGOMovementSet, None),
        'pawn': (cfg['assets']['pawn'], None, unreal.GGYGOBossCharacter),
        'pawn_data': (cfg['assets']['pawn_data'], unreal.GGYGOPawnData, None),
        'definition': (cfg['assets']['definition'], unreal.GGYGOBossDefinition, None),
    }
    if batch == 'combat':
        definitions = {
            'ability': (row['ability'], None, unreal.GGYGOBossMeleeAbility),
            'ability_set': (cfg['assets']['ability_set'], unreal.GGYGOAbilitySet, None),
            **definitions,
        }
    dirty_packages = unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    dirty = {p.get_name() for p in dirty_packages}
    inputs = [mesh, abp, skeleton] + ([montage, sequence, damage_effect] if batch == 'combat' else [])
    require(all(obj.get_outer() not in dirty_packages for obj in inputs), 'input asset package is dirty; freeze/save its original author first')
    for key, (path, cls, parent) in definitions.items():
        require(path not in dirty, 'target package is dirty: ' + path)
        if eal.does_asset_exist(path):
            obj = load(path)
            require(eal.get_metadata_tag(obj, OWNER_KEY) == OWNER, 'refuse unknown target ' + path)
            require(isinstance(obj, unreal.Blueprint if parent else cls), 'wrong target asset class ' + path)
            if parent:
                require(obj.get_blueprint_parent_class() == parent.static_class(), 'wrong Blueprint parent ' + path)
                compiled_blueprint(unreal, obj)
            targets[key] = obj
        else:
            require(not readback, 'readback target was not saved: ' + path)
            targets[key] = None

    def dependency(key):
        require(targets[key] is not None, 'existing graph references missing target ' + definitions[key][0])
        return targets[key]

    def values(key):
        if key == 'ability':
            return {'AttackMontage': montage, 'DamageEffect': damage_effect, 'ActionTag': action_tag,
                    'HitCueTag': cue_tag, 'Damage': row['damage'], 'PoiseDamage': row['poise_damage'],
                    'TraceStartSocket': cfg['trace_start_socket'], 'TraceEndSocket': cfg['trace_end_socket'],
                    'TraceRadius': row['trace_radius'], 'MontagePlayRate': row['play_rate'],
                    'bUseMontageSourceMotion': True, 'ActionMotionProfile': None,
                    'MotionSlot': 'DefaultSlot', 'MotionSection': 'Main', 'MotionTranslationScale': 1.0}
        if key == 'ability_set':
            ability_class = compiled_blueprint(unreal, dependency('ability'))
            grant = unreal.GGYGOAbilitySet_GameplayAbility()
            # These editor-only fields have no Python constructor parameters.
            require(grant.import_text('(Ability="' + ability_class.get_path_name() + '",AbilityLevel=1)'),
                    'AbilitySet row native import failed: ' + ability_class.get_path_name())
            require(grant.get_editor_property('Ability') == ability_class
                    and grant.get_editor_property('AbilityLevel') == 1,
                    'AbilitySet row native import differs: ' + ability_class.get_path_name())
            return {'GrantedGameplayAbilities': [grant]}
        if key == 'movement':
            return {'bUseCurveDrivenSpeed': True}
        if key == 'pawn_data':
            return {'PawnClass': compiled_blueprint(unreal, dependency('pawn')), 'MovementSet': dependency('movement'),
                    'AbilitySets': [dependency('ability_set')] if batch == 'combat' else []}
        if key == 'definition':
            # Initialize native values; standalone struct instances cannot edit EditDefaultsOnly fields.
            form = unreal.GGYGOBossFormDefinition(form_tag=form_tag, avatar_pawn_data=dependency('pawn_data'))
            phase = unreal.GGYGOBossPhaseDefinition(phase_tag=phase_tag, enter_health_threshold=1.0, action_set=None)
            return {'InitialFormTag': form_tag, 'InitialPhaseTag': phase_tag, 'BehaviorTree': None,
                    'Forms': [form], 'Phases': [phase]}
        return {}

    def inspect(key, obj):
        nonlocal install_attack
        receiver = unreal.get_default_object(compiled_blueprint(unreal, obj)) if definitions[key][2] else obj
        if key == 'pawn_data' and batch == 'combat' and targets['ability_set'] is None:
            require(not receiver.get_editor_property('AbilitySets')
                    and eal.get_metadata_tag(obj, 'GGYGO.KevinCombat.Batch') == 'assembly',
                    'cannot attach selected ability to an unknown or nonempty PawnData ability list')
            check_properties(receiver, {'PawnClass': compiled_blueprint(unreal, dependency('pawn')), 'MovementSet': dependency('movement')})
            install_attack = True
        elif key == 'pawn_data' and batch == 'combat' and not receiver.get_editor_property('AbilitySets'):
            require(eal.get_metadata_tag(obj, 'GGYGO.KevinCombat.Batch') == 'assembly', 'only the explicit empty assembly may install its selected attack')
            check_properties(receiver, {'PawnClass': compiled_blueprint(unreal, dependency('pawn')), 'MovementSet': dependency('movement')})
            install_attack = True
        else:
            check_properties(receiver, values(key))
        if key == 'pawn':
            component = receiver.get_editor_property('Mesh')
            require(component.get_skeletal_mesh_asset() == mesh, 'assembly Mesh asset differs: ' + obj.get_path_name())
            check_properties(component, {
                'AnimClass': abp_class, 'RelativeLocation': unreal.Vector(*cfg['mesh_relative_location']),
                'RelativeRotation': rotation, 'RelativeScale3D': scale})
            check_properties(receiver.get_editor_property('CapsuleComponent'), {
                'CapsuleRadius': cfg['capsule_radius'], 'CapsuleHalfHeight': cfg['capsule_half_height']})
            require(receiver.get_editor_property('AutoPossessAI') == unreal.AutoPossessAI.DISABLED, 'Encounter must own Controller creation')

    # Complete all available existing graph comparisons before the first write.
    for key in definitions:
        if targets[key] is not None:
            inspect(key, targets[key])
    require(not readback or not install_attack, 'readback found an assembly without its selected attack attachment')
    for key, (path, cls, parent) in definitions.items():
        obj = targets[key]
        fresh = obj is None and apply
        if fresh:
            folder, name = path.rsplit('/', 1)
            if parent:
                factory = unreal.BlueprintFactory()
                factory.set_editor_property('parent_class', parent)
                asset_class = unreal.Blueprint
            else:
                factory = unreal.DataAssetFactory()
                factory.set_editor_property('data_asset_class', cls)
                asset_class = cls
            obj = tools.create_asset(name, folder, asset_class, factory)
            require(obj is not None, 'create failed: ' + path)
            targets[key] = obj
            eal.set_metadata_tag(obj, OWNER_KEY, OWNER)
            eal.set_metadata_tag(obj, 'GGYGO.KevinCombat.Batch', batch)
            if parent:
                generated = obj.generated_class()
                require(generated is not None, 'new Blueprint factory did not issue a generated class: ' + path)
                receiver = unreal.get_default_object(generated)
            else:
                receiver = obj
            for prop, expected in values(key).items():
                receiver.set_editor_property(prop, expected)
            if key == 'pawn':
                component = receiver.get_editor_property('Mesh')
                component.set_skeletal_mesh_asset(mesh)
                component.set_anim_instance_class(abp_class)
                component.set_editor_property('RelativeLocation', unreal.Vector(*cfg['mesh_relative_location']))
                component.set_editor_property('RelativeRotation', rotation)
                component.set_editor_property('RelativeScale3D', scale)
                receiver.get_editor_property('CapsuleComponent').set_capsule_size(cfg['capsule_radius'], cfg['capsule_half_height'])
            if parent:
                unreal.BlueprintEditorLibrary.compile_blueprint(obj)
            inspect(key, obj)
            require(eal.save_loaded_asset(obj, only_if_is_dirty=False), 'save failed: ' + path)
            require(obj.get_outer() not in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'save left target dirty: ' + path)
            saved.append(path)
        if not fresh and obj is not None and key == 'pawn_data' and install_attack and apply:
            obj.set_editor_property('AbilitySets', values(key)['AbilitySets'])
            check_properties(obj, values(key))
            eal.set_metadata_tag(obj, 'GGYGO.KevinCombat.Batch', 'combat')
            require(eal.save_loaded_asset(obj, only_if_is_dirty=False), 'selected attack attachment save failed: ' + path)
            require(obj.get_outer() not in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'attack attachment left target dirty: ' + path)
            saved.append(path)
        records.append({'path': path, 'status': 'created_saved_fields_verified' if fresh else
                        ('existing_fields_verified' if obj is not None else 'missing_not_created')})
    result = {'status': 'saved_fields_verified_runtime_pending' if apply else
              ('readback_fields_verified_runtime_pending' if readback else 'preflight_no_mutation'),
              'batch': batch, 'assets': records, 'saved': saved,
              'definition': cfg['assets']['definition'], 'demonstration_map': cfg['demonstration_map'],
              'attack_trigger': cfg['attack_trigger'], 'initial_action': cfg['initial_action'],
              'selected_attack_attachment_pending': install_attack and not apply,
              'assembly_basis_confirmed': basis['confirmed'], 'assembly_alignment_status': cfg['assembly_alignment_status'],
              'alignment_verified': False, 'runtime_ready_verified': False,
              'animation_graph_verified': False, 'movement_xyz_verified': False, 'hit_verified': False,
              'level_modified': False, 'audio_gap': cfg['audio_gap']}
    if batch == 'combat':
        result['combat_tuning_status'] = cfg['combat_tuning_status']
        result['hit_window_source'] = spec['window_source']
        result['hit_window_test_only'] = spec['test_only']
        result['original_game_window_known'] = spec['original_game_window_known']
    if apply:
        out = ROOT / 'Saved/Codex/bh3_kevin_combat_wiring.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('KEVIN_COMBAT_WIRING ' + json.dumps(result, ensure_ascii=False))
    return result


def boss_package_receipt(package):
    """生产写入只接受调用方绑定的磁盘前像，不推定旧回执仍然有效。"""
    require(package.startswith('/Game/'), 'boss package must be under /Game')
    path = ROOT / 'Content' / (package[6:] + '.uasset')
    if not path.exists():
        return {'exists': False}
    data = path.read_bytes()
    return {'exists': True, 'size_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest().upper()}


def read_boss_production_config():
    cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    production = cfg['production']
    require(production['schema'] == 'GGYGO.KevinBossWiring/v1', 'unsupported production schema')
    require(type(production['use_native_approach']) is bool, 'approach route must be explicitly authored')
    source = (ROOT / production['ability_config']).resolve()
    require(source.is_relative_to(ROOT.resolve()), 'ability config must stay in project')
    abilities = json.loads(source.read_text(encoding='utf-8-sig'))
    require(abilities['schema'] == 'GGYGO.KevinAbilities/v1', 'unsupported ability author schema')
    require(abilities['death']['ability'] in abilities['persistent_abilities'], 'required death ability must be granted')
    rows = abilities['abilities']
    require(isinstance(rows, list) and rows, 'ability author must publish explicit actions')
    by_key = {row['key']: row for row in rows}
    require(len(by_key) == len(rows), 'duplicate ability key')
    for row in rows:
        require(isinstance(row['enabled'], bool), 'ability enabled must be explicit')
        require(isinstance(row['entrypoint'], bool), 'ability entrypoint must be explicit')
        require(row['ability'].startswith(cfg['base'] + '/Abilities/'), 'ability outside Kevin namespace')
        require(row['action_tag'].startswith('BossAction.'), 'missing semantic ActionTag')
    phases = production['phases']
    require(len(phases) == 2 and phases[0]['health_threshold'] == 1.0
            and phases[1]['health_threshold'] == 0.5, 'this project design requires two phases at 50 percent')
    for phase in phases:
        require(phase['action_keys'] and len(set(phase['action_keys'])) == len(phase['action_keys']), 'invalid phase action keys')
        require(all(key in by_key for key in phase['action_keys']), 'phase references unpublished ability key')
        require(any(by_key[key]['enabled'] and by_key[key]['entrypoint'] for key in phase['action_keys']),
                'phase has no enabled entrypoint')
    return cfg, production, abilities, by_key


def run_boss(apply=False, readback=False, expected_before=None):
    """完整 Boss 接线入口；只写 Pawn/Data/BB/BT，不创建或编辑 GA、动画、FX、声音。"""
    import unreal
    require(not (apply and readback), 'apply and readback are exclusive')
    cfg, production, abilities, by_key = read_boss_production_config()
    eal = unreal.EditorAssetLibrary
    outputs = [production['state_blueprint'], production['target_service'], production['blackboard'], production['behavior_tree']]
    outputs += [phase['action_set'] for phase in production['phases']]
    outputs += [cfg['assets'][key] for key in ('ability_set', 'pawn_data', 'definition', 'pawn')]
    require(len(set(outputs)) == len(outputs), 'duplicate production output')
    require(all(path.startswith(cfg['base'] + '/') for path in outputs), 'production output outside Kevin namespace')
    dirty = {package.get_name() for package in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    require(not dirty.intersection(outputs), 'owned production target has unsaved work')
    before = {path: boss_package_receipt(path) for path in outputs}
    if apply:
        require(isinstance(expected_before, dict) and expected_before == before,
                'apply requires the exact complete preflight before receipts')
    loaded_classes = {}
    for key, row in by_key.items():
        if not row['enabled']:
            continue  # 显式未启用的缺配对/未闭合族保留缺口，不替换成其它招式。
        package = row['ability'].split('.', 1)[0]
        bp = eal.load_asset(package)
        require(bp is not None and package not in dirty, 'missing or dirty enabled GA: ' + key)
        cls = compiled_blueprint(unreal, bp)
        require(unreal.load_class(None, row['ability']) == cls, 'published GA Class differs from actual Blueprint: ' + key)
        cdo = unreal.get_default_object(cls)
        expected_tag = unreal.GameplayTag()
        require(expected_tag.import_text('(TagName="' + row['action_tag'] + '")'), 'invalid action tag: ' + key)
        require(cdo.get_editor_property('ActionTag').export_text() == expected_tag.export_text(),
                'actual GA ActionTag differs: ' + key)
        loaded_classes[key] = cls
    persistent = [unreal.load_class(None, path) for path in abilities['persistent_abilities']]
    effects = [unreal.load_class(None, path) for path in abilities['initial_effects']]
    require(persistent and effects and all(persistent) and all(effects), 'missing persistent ability or required initial GE')
    shared_pawn = eal.load_asset(production['pawn_parent_blueprint'])
    require(isinstance(shared_pawn, unreal.Blueprint), 'missing shared Boss character Blueprint')
    shared_pawn_class = compiled_blueprint(unreal, shared_pawn)
    require(isinstance(unreal.get_default_object(shared_pawn_class), unreal.GGYGOBossCharacter),
            'shared Boss character has incompatible native base')
    if not apply and not readback:
        return {'status': 'production_preflight_no_mutation', 'before': before, 'outputs': outputs,
                'enabled': list(loaded_classes), 'disabled': [key for key, row in by_key.items() if not row['enabled']]}

    saved, pending_save = [], []
    tools = unreal.AssetToolsHelpers.get_asset_tools()

    def load_or_create(path, cls, factory=None):
        obj = eal.load_asset(path)
        if obj is None:
            require(apply, 'readback target missing: ' + path)
            if factory is None:
                factory = unreal.DataAssetFactory()
                factory.set_editor_property('DataAssetClass', cls)
            obj = tools.create_asset(path.rsplit('/', 1)[1], path.rsplit('/', 1)[0], cls, factory)
        require(obj is not None and isinstance(obj, cls), 'wrong asset class: ' + path)
        return obj

    def compare_value(value):
        if isinstance(value, unreal.Object):
            return value.get_path_name()
        if isinstance(value, (list, tuple, unreal.Array)):
            return [compare_value(item) for item in value]
        if hasattr(value, 'export_text'):
            return value.export_text()
        return value

    def properties(obj, values):
        for name, value in values.items():
            if apply:
                obj.set_editor_property(name, value)
            actual = obj.get_editor_property(name)
            if isinstance(value, float):
                require(math.isfinite(actual) and math.isclose(actual, value, rel_tol=1e-7, abs_tol=1e-8),
                        obj.get_path_name() + '.' + name + ' differs')
            else:
                require(compare_value(actual) == compare_value(value), obj.get_path_name() + '.' + name + ' differs')

    def save(obj):
        if apply:
            pending_save.append(obj)

    def tag(name):
        value = unreal.GameplayTag()
        require(value.import_text('(TagName="' + name + '")'), 'invalid tag text: ' + name)
        return value

    pawn = eal.load_asset(cfg['assets']['pawn'])
    require(pawn is not None, 'missing existing Kevin Pawn')
    if apply and pawn.get_blueprint_parent_class() != shared_pawn_class:
        unreal.BlueprintEditorLibrary.reparent_blueprint(pawn, shared_pawn_class)
        unreal.BlueprintEditorLibrary.compile_blueprint(pawn)
    require(pawn.get_blueprint_parent_class() == shared_pawn_class,
            'Kevin Pawn must inherit the shared Blueprint death policy')
    pawn_cdo = unreal.get_default_object(compiled_blueprint(unreal, pawn))
    properties(pawn_cdo.get_editor_property('character_movement'),
               {'bUseControllerDesiredRotation': True, 'bOrientRotationToMovement': False})
    if apply:
        unreal.BlueprintEditorLibrary.compile_blueprint(pawn)
        compiled_blueprint(unreal, pawn)
    save(pawn)
    blackboard = load_or_create(production['blackboard'], unreal.BlackboardData, unreal.BlackboardDataFactory())
    tree = load_or_create(production['behavior_tree'], unreal.BehaviorTree, unreal.BehaviorTreeFactory())
    state_factory = unreal.BlueprintFactory()
    state_factory.set_editor_property('ParentClass', unreal.GGYGOBossState)
    state_blueprint = load_or_create(production['state_blueprint'], unreal.Blueprint, state_factory)
    service_factory = unreal.BlueprintFactory()
    service_factory.set_editor_property('ParentClass', unreal.BTService_BlueprintBase)
    target_service = load_or_create(production['target_service'], unreal.Blueprint, service_factory)
    action_sets = []
    for phase in production['phases']:
        action_set = load_or_create(phase['action_set'], unreal.GGYGOBossActionSet)
        actions = []
        for key in phase['action_keys']:
            row = by_key[key]
            if not row['enabled'] or not row['entrypoint']:
                continue
            tuning = production['action_tuning'][key]
            action = unreal.GGYGOBossActionDefinition()
            fields = {'ActionTag': '(TagName="' + row['action_tag'] + '")',
                      'AbilityClass': '"' + loaded_classes[key].get_path_name() + '"',
                      'BaseWeight': str(tuning['base_weight']), 'MinDistance': str(tuning['min_distance']),
                      'MaxDistance': str(tuning['max_distance']), 'MaxFacingAngle': str(tuning['max_facing_angle']),
                      'RepeatPenalty': str(tuning['repeat_penalty']), 'UnusedWeightGain': str(tuning['unused_weight_gain']),
                      'MaxWeight': str(tuning['max_weight']),
                      'bRequiresLineOfSight': 'True' if tuning['requires_line_of_sight'] else 'False'}
            require(action.import_text('(' + ','.join(name + '=' + value for name, value in fields.items()) + ')'),
                    'native action row import failed: ' + key)
            actions.append(action)
        properties(action_set, {'Actions': actions})
        save(action_set)
        action_sets.append(action_set)
    ability_set = load_or_create(cfg['assets']['ability_set'], unreal.GGYGOAbilitySet)
    grants, initial_effects = [], []
    for cls in list(loaded_classes.values()) + persistent:
        grant = unreal.GGYGOAbilitySet_GameplayAbility()
        require(grant.import_text('(Ability="' + cls.get_path_name() + '",AbilityLevel=1)'), 'ability grant import failed')
        grants.append(grant)
    for cls in effects:
        effect = unreal.GGYGOAbilitySet_GameplayEffect()
        require(effect.import_text('(GameplayEffect="' + cls.get_path_name() + '",EffectLevel=1.0)'), 'initial effect import failed')
        initial_effects.append(effect)
    properties(ability_set, {'GrantedGameplayAbilities': grants, 'GrantedGameplayEffects': initial_effects,
                             'GrantedAttributes': []})
    save(ability_set)
    pawn_data = load_or_create(cfg['assets']['pawn_data'], unreal.GGYGOPawnData)
    properties(pawn_data, {'PawnClass': compiled_blueprint(unreal, pawn), 'AbilitySets': [ability_set]})
    save(pawn_data)
    definition = load_or_create(cfg['assets']['definition'], unreal.GGYGOBossDefinition)
    forms = [unreal.GGYGOBossFormDefinition(form_tag=tag(cfg['form_tag']), avatar_pawn_data=pawn_data)]
    phases = [unreal.GGYGOBossPhaseDefinition(phase_tag=tag(phase['tag']),
              enter_health_threshold=phase['health_threshold'], action_set=action_set)
              for phase, action_set in zip(production['phases'], action_sets)]
    properties(definition, {'InitialFormTag': tag(cfg['form_tag']), 'InitialPhaseTag': tag(production['phases'][0]['tag']),
               'Forms': forms, 'Phases': phases, 'PersistentAbilitySets': [], 'BehaviorTree': tree,
               'CombatTargetKey': production['target_key'], 'TargetAcquireDistance': production['target_acquire_distance'],
               'TargetLoseDistance': production['target_lose_distance'], 'ApproachDistance': production['approach_distance']})
    native = unreal.GGYGOBossCombatAssetLibrary
    graph_operation = native.build_decision_blueprints if apply else native.validate_decision_blueprints
    graph_result = graph_operation(state_blueprint, target_service, definition)
    require(isinstance(graph_result, unreal.GGYGOBossCombatAssetResult), 'native decision graphs returned an invalid result structure')
    require(graph_result.get_editor_property('bSucceeded') is True, 'native decision graphs: ' + graph_result.get_editor_property('Error'))
    properties(definition, {'BossStateClass': compiled_blueprint(unreal, state_blueprint),
                           'CombatTargetService': compiled_blueprint(unreal, target_service)})
    operation = native.build_combat_tree if apply else native.validate_combat_tree
    tree_result = operation(tree, blackboard, definition, production['decision_interval'], production['target_update_interval'],
                            production['use_native_approach'])
    require(isinstance(tree_result, unreal.GGYGOBossCombatAssetResult), 'native combat tree returned an invalid result structure')
    require(tree_result.get_editor_property('bSucceeded') is True, 'native combat tree: ' + tree_result.get_editor_property('Error'))
    save(blackboard)
    save(tree)
    save(state_blueprint)
    save(target_service)
    save(definition)
    for obj in pending_save:
        eal.set_metadata_tag(obj, OWNER_KEY, 'GGYGO.KevinBossAssembly.v1')
        require(eal.save_loaded_asset(obj, only_if_is_dirty=False), 'save failed: ' + obj.get_path_name())
        saved.append(obj.get_outer().get_name())
        unreal.log('KEVIN_BOSS_SAVED ' + obj.get_path_name())
    return {'status': 'production_saved_runtime_pending' if apply else 'production_readback_runtime_pending',
            'saved': saved, 'enabled': list(loaded_classes), 'disabled': [key for key, row in by_key.items() if not row['enabled']],
            'before': before, 'runtime_verified': False, 'scene_modified': False}


def audit_p3_support(output_path, map_sha256):
    """只审查既有 P3 支撑；查询候选不等于已生成、落地或可玩证明。"""
    import os
    import unreal

    output = Path(output_path).resolve()
    output_root = (ROOT / 'Saved/KevinP3Support').resolve()
    require(output.is_relative_to(output_root) and output.suffix == '.json' and not output.exists(),
            'support output must be a new JSON below ' + str(output_root))
    require(re.fullmatch(r'[0-9a-fA-F]{64}', map_sha256 or ''), 'support audit requires the frozen map SHA256')
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {'mode': 'p3_support_readonly', 'phase': 'host', 'editor_pid': os.getpid(),
              'created_actors': [], 'saved_assets': [], 'map_saved': False, 'pie_started': False,
              'collision_modified': False, 'legal_spawn_verified': False, 'meshes': [], 'queries': [],
              'query_supported_candidates': [], 'errors': []}
    before_actors = before_dirty = before_files = None

    def vector(value):
        values = [float(value.x), float(value.y), float(value.z)]
        return finite_values(values, 3, 'native vector')

    def path_of(obj):
        return obj.get_path_name() if obj is not None else None

    def digest(path):
        require(path.is_file(), 'protected package is missing: ' + str(path))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def dirty_packages():
        loading = unreal.EditorLoadingAndSavingUtils
        return sorted(p.get_name() for p in loading.get_dirty_content_packages()), sorted(
            p.get_name() for p in loading.get_dirty_map_packages())

    def actor_state():
        state = {}
        for actor in actors.get_all_level_actors():
            row = {'class': path_of(actor.get_class()), 'tags': [str(t) for t in actor.get_editor_property('tags')],
                   'pose': actor.get_actor_transform().export_text(), 'parent': path_of(actor.get_attach_parent_actor()),
                   'collision': actor.get_actor_enable_collision(), 'hidden': actor.get_editor_property('hidden'),
                   'components': {}}
            for component in actor.get_components_by_class(unreal.SceneComponent):
                entry = {'pose': component.get_relative_transform().export_text(),
                         'visible': component.get_editor_property('visible'),
                         'hidden_in_game': component.get_editor_property('hidden_in_game')}
                if isinstance(component, unreal.PrimitiveComponent):
                    entry['body'] = component.get_editor_property('body_instance').export_text()
                if isinstance(component, unreal.StaticMeshComponent):
                    entry['mesh'] = path_of(component.get_editor_property('static_mesh'))
                row['components'][path_of(component)] = entry
            state[path_of(actor)] = row
        return state

    def native_query(start, end, complex_trace, capsule_query):
        method = unreal.SystemLibrary.capsule_trace_single_by_profile if capsule_query else unreal.SystemLibrary.line_trace_single_by_profile
        arguments = [world, unreal.Vector(*start), unreal.Vector(*end)]
        if capsule_query:
            arguments.extend([radius, half_height])
        arguments.extend([profile, complex_trace, [], unreal.DrawDebugTrace.NONE, False])
        returned = method(*arguments)
        # UE Python PackReturnValues 将 bool + OutHit 映射为 HitResult 或 None；未命中时不伪造法线/深度。
        row = {'kind': 'capsule' if capsule_query else 'line', 'complex': complex_trace,
               'profile': profile, 'start_cm': start, 'end_cm': end,
               'blocking_hit': returned is not None, 'native_return': type(returned).__name__}
        result['queries'].append(row)
        if returned is None:
            return row
        require(isinstance(returned, unreal.HitResult), 'native query must return HitResult or None')
        hit = returned
        # HasNativeBreak 在 Python StructBase.to_tuple 中调用真实 BreakHitResult。
        fields = hit.to_tuple()
        require(len(fields) == 18, 'native BreakHitResult signature differs')
        require(fields[0], 'query return and native BlockingHit disagree')
        raw = hit.export_text()
        row.update({'initial_penetration': bool(fields[1]), 'native_hit_text': raw,
               'time': float(fields[2]), 'distance_cm': float(fields[3]), 'location_cm': vector(fields[4]),
               'impact_cm': vector(fields[5]), 'normal': vector(fields[6]), 'impact_normal': vector(fields[7]),
               'actor': path_of(fields[9]), 'component': path_of(fields[10]), 'face_index': int(fields[15]),
               'native_cmc_is_walkable': bool(movement.is_walkable(hit))})
        depths = re.findall(r'(?:^|[,\(])PenetrationDepth=([^,\)]+)', raw)
        require(len(depths) == 1 and math.isfinite(float(depths[0])), 'native penetration depth unavailable')
        row['penetration_depth_cm'] = float(depths[0])
        return row

    try:
        cfg = read_config()
        require(cfg['demonstration_map'] == '/Game/Map/BH3/L_KevinBoss_P3', 'unexpected demonstration map')
        levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        mesh_editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        require(levels and editor and actors and mesh_editor and not levels.is_in_play_in_editor(),
                'support audit needs a full Editor with no PIE')
        world = editor.get_editor_world()
        require(world and world.get_path_name() == cfg['demonstration_map'] + '.L_KevinBoss_P3',
                'support audit only reads the already opened P3 world')
        specifications = [('1934927152128', 'G1934921182544_Stage_KevinBoss_P3_Collision'),
                          ('1934927154112', 'G1934921182992_Stage_KevinBoss_P3_CamCollision'),
                          ('1934927135424', 'G1934921163216_Rocks')]
        stage_root = '/Game/Environments/BH3/Stage/Stage_KevinBoss_P3/StaticMeshes/'
        map_file = ROOT / 'Content/Map/BH3/L_KevinBoss_P3.umap'
        files = [map_file, CONFIG, MONTAGES, ROOT / 'Source/GGYGO/AI/Boss/Tests/GGYGOBossMeleeEndReentryTest.cpp',
                 ROOT / ('Content' + cfg['assets']['pawn'].removeprefix('/Game') + '.uasset')]
        files.extend(ROOT / ('Content' + stage_root.removeprefix('/Game') + name + '.uasset') for _, name in specifications)
        before_files = {str(p): digest(p) for p in files}
        require(before_files[str(map_file)] == map_sha256.lower(), 'P3 map does not match the frozen baseline')
        before_dirty = dirty_packages()
        require(before_dirty == ([], []), 'independent audit Editor has dirty packages; refusing to continue')
        before_actors = actor_state()
        result['world'] = world.get_path_name()
        result['actor_count'] = len(before_actors)
        result['phase'] = 'pawn_cdo'
        pawn_bp = unreal.load_asset(cfg['assets']['pawn'])
        require(isinstance(pawn_bp, unreal.Blueprint), 'saved formal Pawn Blueprint missing')
        pawn = unreal.get_default_object(compiled_blueprint(unreal, pawn_bp))
        require(isinstance(pawn, unreal.GGYGOBossCharacter), 'formal Pawn parent differs')
        capsule = pawn.get_editor_property('CapsuleComponent')
        movement = pawn.get_editor_property('CharacterMovement')
        require(capsule and movement, 'formal Pawn capsule/CMC missing')
        radius, half_height = float(capsule.get_unscaled_capsule_radius()), float(capsule.get_unscaled_capsule_half_height())
        require(abs(radius - cfg['capsule_radius']) < .0001 and abs(half_height - cfg['capsule_half_height']) < .0001,
                'actual formal capsule differs from saved configuration')
        profile = str(capsule.get_collision_profile_name())
        require(profile == 'Pawn' and vector(movement.get_gravity_direction()) == [0.0, 0.0, -1.0],
                'this upright Pawn-profile audit requires the actual Pawn profile and native downward gravity')
        gravity_scale = float(movement.get_editor_property('GravityScale'))
        require(math.isfinite(gravity_scale) and gravity_scale > 0, 'actual formal gravity must be positive')
        actual_complex = bool(capsule.get_editor_property('bTraceComplexOnMove'))
        result['pawn'] = {'class': path_of(pawn.get_class()), 'radius_cm': radius, 'half_height_cm': half_height,
                          'profile': profile, 'trace_complex_on_move': actual_complex, 'gravity_scale': gravity_scale,
                          'capsule_body_native_text': capsule.get_editor_property('body_instance').export_text(),
                          'capsule_relative_transform': capsule.get_relative_transform().export_text(),
                          'walkable_floor_z': float(movement.get_walkable_floor_z()),
                          'max_step_height_cm': float(movement.get_editor_property('MaxStepHeight'))}
        result['phase'] = 'body_setup'
        bounds = []
        for model, name in specifications:
            selected = [a for a in actors.get_all_level_actors() if 'FBX.ModelID=' + model in
                        [str(t) for t in a.get_editor_property('tags')]]
            require(len(selected) == 1 and isinstance(selected[0], unreal.StaticMeshActor), 'source Actor identity differs: ' + model)
            actor = selected[0]
            components = actor.get_components_by_class(unreal.StaticMeshComponent)
            require(len(components) == 1, 'expected exactly one mesh component: ' + model)
            component = components[0]
            mesh = component.get_editor_property('static_mesh')
            require(mesh and mesh.get_path_name() == stage_root + name + '.' + name, 'source mesh binding differs: ' + model)
            simple = mesh_editor.get_simple_collision_count(mesh)
            convex = mesh_editor.get_convex_collision_count(mesh)
            complexity = mesh_editor.get_collision_complexity(mesh)
            require(simple >= 0 and convex >= 0, 'native shape count query failed: ' + model)
            # 上述公开 getter 先等待实际 BodySetup 的异步属性；随后只读其 EditAnywhere 反射字段。
            body = mesh.get_editor_property('BodySetup')
            shape = None
            if body is not None:
                geometry = body.get_editor_property('AggGeom')
                shape = {field: len(geometry.get_editor_property(field)) for field in
                         ('SphereElems', 'BoxElems', 'SphylElems', 'ConvexElems', 'TaperedCapsuleElems',
                          'LevelSetElems', 'SkinnedLevelSetElems', 'MLLevelSetElems', 'SkinnedTriangleMeshElems')}
                require(simple == shape['SphereElems'] + shape['BoxElems'] + shape['SphylElems']
                        and convex == shape['ConvexElems'], 'native BodySetup/getter shape counts disagree')
            origin, extent, _ = unreal.SystemLibrary.get_component_bounds(component)
            origin, extent = vector(origin), vector(extent)
            bounds.append((origin, extent))
            result['meshes'].append({'model': model, 'actor': path_of(actor), 'component': path_of(component),
                'mesh': path_of(mesh), 'actor_collision': actor.get_actor_enable_collision(),
                'collision_enabled': str(component.get_collision_enabled()), 'profile': str(component.get_collision_profile_name()),
                'object_type': str(component.get_collision_object_type()),
                'pawn_response': str(component.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)),
                'camera_response': str(component.get_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA)),
                'body_setup': path_of(body), 'collision_complexity': str(complexity),
                'simple_box_sphere_capsule_count': simple, 'convex_count': convex, 'shape_counts': shape,
                'agg_geom_native_text': body.get_editor_property('AggGeom').export_text() if body is not None else None,
                'double_sided_geometry': bool(body.get_editor_property('bDoubleSidedGeometry')) if body is not None else None,
                'bounds_origin_cm': origin, 'bounds_extent_cm': extent})
        result['phase'] = 'native_queries'
        # 三个真实 AABB 决定上下界；中心只选查询柱，不猜测落地 Z 或跳过其它真实阻挡者。
        top = max(o[2] + e[2] for o, e in bounds) + half_height + radius
        bottom = min(o[2] - e[2] for o, e in bounds) - half_height - radius
        for seed_name, xy in [('collision_center', bounds[0][0][:2]), ('rocks_center', bounds[2][0][:2])]:
            start, end = [*xy, top], [*xy, bottom]
            rows = {complex_trace: native_query(start, end, complex_trace, True) for complex_trace in (False, True)}
            row = rows[actual_complex]
            if not row['blocking_hit'] or row['initial_penetration'] or not row['native_cmc_is_walkable']:
                continue
            # 查询候选留一个实际胶囊半径的下降间隔；以后只能靠原重力/CMC 真正落地，当前不宣称稳定站立。
            candidate = row['location_cm'].copy()
            candidate[2] += radius
            clearance = native_query(candidate, candidate, actual_complex, True)
            feet = [native_query([xy[0] + dx, xy[1] + dy, top], [xy[0] + dx, xy[1] + dy, bottom], actual_complex, False)
                    for dx, dy in ((0, 0), (radius, 0), (-radius, 0), (0, radius), (0, -radius))]
            if not clearance['blocking_hit'] and all(f['blocking_hit'] and not f['initial_penetration']
                                                    and f['native_cmc_is_walkable'] and f['component'] == row['component'] for f in feet):
                result['query_supported_candidates'].append({'seed': seed_name, 'capsule_center_cm': candidate,
                    'support_component': row['component'], 'contact_cm': row['impact_cm'],
                    'native_landing_and_idle_pending': True})
        result['phase'] = 'audit_complete_queries_only'
    except Exception as exc:
        result['failure_phase'] = result['phase']
        result['phase'] = 'failed'
        result['errors'].append(type(exc).__name__ + ': ' + str(exc))
    finally:
        try:
            if before_files is not None:
                changed = [name for name, value in before_files.items() if digest(Path(name)) != value]
                result['protected_files'] = before_files
                result['changed_files'] = changed
                if changed:
                    result['errors'].append('protected package bytes changed: ' + repr(changed))
            if before_actors is not None:
                result['actor_state_unchanged'] = actor_state() == before_actors
                result['dirty_packages_unchanged'] = dirty_packages() == before_dirty
                if not result['actor_state_unchanged'] or not result['dirty_packages_unchanged']:
                    result['errors'].append('native actor state or package dirty state changed')
        except Exception as exc:
            result['errors'].append('protection readback failed: ' + type(exc).__name__ + ': ' + str(exc))
        if result['errors']:
            result['phase'] = 'failed'
        with output.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        unreal.log('KEVIN_P3_SUPPORT ' + json.dumps({'phase': result['phase'], 'output': str(output),
            'supported_candidates': len(result['query_supported_candidates']), 'errors': result['errors']}, ensure_ascii=False))
    require(not result['errors'], 'support audit failed; preserved native evidence: ' + str(output))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--batch', choices=('assembly', 'combat'), default='assembly')
    parser.add_argument('--readback', action='store_true')
    parser.add_argument('--calibrate-basis', action='store_true')
    parser.add_argument('--audit-p3-support', action='store_true')
    parser.add_argument('--support-output')
    parser.add_argument('--support-map-sha256')
    parser.add_argument('--boss-production', action='store_true')
    parser.add_argument('--boss-before-json')
    parser.add_argument('--boss-output-json')
    args = parser.parse_args()
    if args.boss_production:
        require(not args.audit_p3_support and not args.calibrate_basis and args.batch == 'assembly',
                'production boss wiring is an isolated mode')
        before = json.loads(Path(args.boss_before_json).read_text(encoding='utf-8-sig'))['before'] if args.boss_before_json else None
        result = run_boss(args.apply, args.readback, before)
        if args.boss_output_json:
            output = Path(args.boss_output_json)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('x', encoding='utf-8') as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
        import unreal
        unreal.log('KEVIN_BOSS_WIRING ' + json.dumps(result, ensure_ascii=False))
    elif args.audit_p3_support:
        require(not args.apply and not args.readback and not args.calibrate_basis and args.batch == 'assembly'
                and args.support_output and args.support_map_sha256,
                '--audit-p3-support is an isolated read-only mode with explicit output and map SHA256')
        audit_p3_support(args.support_output, args.support_map_sha256)
    elif args.calibrate_basis:
        require(not args.apply and not args.readback and args.batch == 'assembly',
                '--calibrate-basis is a separate read-only mode; --apply/--readback/combat are invalid')
        calibrate_basis()
    else:
        run(args.apply, args.batch, args.readback)
