"""Create the fixed movement fixture after preflight; importing is read-only.

run() never overwrites an existing map. A clean, already-open fixture can be
inspected again to recover its report. Partial/dirty maps require manual review.
"""
import json
from pathlib import Path
from uuid import uuid4
import unreal

MAP = '/Game/Map/L_Movement_Test'
MATERIAL = '/Game/Map/Materials/M_MovementGrid'
GAME_MODE = '/Game/BP/GamePlay/BP_GameMode.BP_GameMode_C'


def _path(obj):
    return obj.get_path_name() if obj else None


def _saved_file(package, extension):
    return Path(unreal.Paths.convert_relative_path_to_full(
        unreal.Paths.project_content_dir())) / (package.removeprefix('/Game/') + extension)


def preflight():
    """Read every referenced configuration before creating any package."""
    if unreal.EditorLevelLibrary.get_pie_worlds(False):
        raise RuntimeError('Stop PIE before inspecting/creating the fixture')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Dirty map packages must be preserved before proceeding')
    dirty_content = {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    gm_class = unreal.load_class(None, GAME_MODE)
    if not gm_class:
        raise RuntimeError('Missing BP_GameMode')
    gm = unreal.get_default_object(gm_class)
    exp = gm.get_editor_property('experience')
    if not isinstance(exp, unreal.GGYGOExperienceDefinition):
        raise RuntimeError('Missing or invalid Experience')
    roster = list(exp.get_editor_property('squad_members'))
    if not roster:
        raise RuntimeError('This fixture requires a nonempty default roster')
    members = []
    refs = [gm_class, exp]
    for index, pawn_data in enumerate(roster):
        if not isinstance(pawn_data, unreal.GGYGOPawnData):
            raise RuntimeError('Invalid PawnData at roster index ' + str(index))
        pawn_class = pawn_data.get_editor_property('pawn_class')
        if not pawn_class or not isinstance(unreal.get_default_object(pawn_class), unreal.Pawn):
            raise RuntimeError('Invalid PawnClass at roster index ' + str(index))
        movement = pawn_data.get_editor_property('movement_set')
        inputs = pawn_data.get_editor_property('input_config')
        if movement and not isinstance(movement, unreal.GGYGOMovementSet):
            raise RuntimeError('Invalid MovementSet at roster index ' + str(index))
        if inputs and not isinstance(inputs, unreal.GGYGOInputConfig):
            raise RuntimeError('Invalid InputConfig at roster index ' + str(index))
        # Null MovementSet/InputConfig are legal PawnData values. They are
        # recorded, not dereferenced or silently replaced with character data.
        members.append(dict(pawn_data=_path(pawn_data), pawn_class=_path(pawn_class),
                            movement_set=_path(movement), input_config=_path(inputs)))
        refs.extend([pawn_data, pawn_class, movement, inputs])
    cube = unreal.load_asset('/Engine/BasicShapes/Cube')
    if not isinstance(cube, unreal.StaticMesh):
        raise RuntimeError('Missing engine Cube StaticMesh')
    grid = unreal.load_asset(MATERIAL)
    if unreal.EditorAssetLibrary.does_asset_exist(MATERIAL) and not grid:
        raise RuntimeError('Existing material cannot be loaded')
    if grid and not isinstance(grid, unreal.Material):
        raise RuntimeError('Existing grid asset is not a Material')
    refs.append(grid)
    dirty_refs = sorted({_path(ref).split('.')[0] for ref in refs if ref} & dirty_content)
    if dirty_refs:
        raise RuntimeError('Referenced packages have unsaved edits: ' + ', '.join(dirty_refs))
    if grid and not _saved_file(MATERIAL, '.uasset').is_file():
        raise RuntimeError('Existing grid has no saved package; preserve/review it first')
    return dict(gm_class=gm_class, cube=cube, grid=grid,
                configuration=dict(game_mode=_path(gm_class), experience=_path(exp), roster=members))


def _create_material(report):
    grid = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_MovementGrid', '/Game/Map/Materials', unreal.Material, unreal.MaterialFactoryNew())
    if not isinstance(grid, unreal.Material):
        raise RuntimeError('Grid material creation failed')
    report['material_created'] = True
    edit = unreal.MaterialEditingLibrary
    position = edit.create_material_expression(grid, unreal.MaterialExpressionWorldPosition, -500, 0)
    checker = edit.create_material_expression(grid, unreal.MaterialExpressionCustom, -250, 0)
    custom_input = unreal.CustomInput()
    custom_input.set_editor_property('input_name', 'WorldPosition')
    checker.set_editor_property('inputs', [custom_input])
    checker.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    checker.set_editor_property('code', '''float2 cell = floor(WorldPosition.xy / 500.0);
float parity = fmod(abs(cell.x + cell.y), 2.0);
float2 uv = frac(WorldPosition.xy / 500.0);
float edge = min(min(uv.x, 1.0-uv.x), min(uv.y, 1.0-uv.y));
float gridLine = 1.0 - smoothstep(0.006, 0.012, edge);
return lerp(lerp(float3(0.13,0.16,0.20), float3(0.19,0.23,0.28), parity), float3(0.38,0.46,0.55), gridLine);''')
    edit.connect_material_expressions(position, '', checker, 'WorldPosition')
    edit.connect_material_property(checker, '', unreal.MaterialProperty.MP_BASE_COLOR)
    roughness = edit.create_material_expression(grid, unreal.MaterialExpressionConstant, -250, 240)
    roughness.set_editor_property('r', 0.85)
    edit.connect_material_property(roughness, '', unreal.MaterialProperty.MP_ROUGHNESS)
    edit.recompile_material(grid)
    if not unreal.EditorAssetLibrary.save_loaded_asset(grid):
        raise RuntimeError('Material save failed; generated material retained for review')
    if not _saved_file(MATERIAL, '.uasset').is_file():
        raise RuntimeError('Material save returned success but package is missing')
    return grid


def spawn(cls, label, xyz, rotation=(0, 0, 0)):
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actors.spawn_actor_from_class(cls, unreal.Vector(*xyz),
        unreal.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]))
    if not actor:
        raise RuntimeError('Failed to spawn ' + label)
    actor.set_actor_label(label)
    return actor


def _build_world(world, plan):
    world.get_world_settings().set_editor_property('default_game_mode', plan['gm_class'])
    cube, grid = plan['cube'], plan['grid']
    floor = spawn(unreal.StaticMeshActor, 'Movement_Floor_1000m', (0, 0, -50))
    floor.set_actor_scale3d(unreal.Vector(1000, 1000, 1))
    comp = floor.static_mesh_component
    comp.set_static_mesh(cube)
    comp.set_material(0, grid)
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    comp.set_collision_profile_name('BlockAll')
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    comp.set_collision_object_type(unreal.CollisionChannel.ECC_WORLD_STATIC)
    comp.set_collision_profile_name('BlockAll')
    floor.set_folder_path('TestGround')
    start = spawn(unreal.PlayerStart, 'PlayerStart_Movement', (0, 0, 150))
    start.set_folder_path('PlayerSetup')
    sun = spawn(unreal.DirectionalLight, 'Sun_Movement', (0, 0, 1000), (-40, -30, 0))
    sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(10)
    sun.light_component.set_editor_property('atmosphere_sun_light', True)
    sky = spawn(unreal.SkyAtmosphere, 'Sky_Movement', (0, 0, 0))
    skylight = spawn(unreal.SkyLight, 'Ambient_Movement', (0, 0, 500))
    skylight.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    skylight.light_component.set_editor_property('real_time_capture', True)
    skylight.light_component.set_intensity(1)
    for actor in (sun, sky, skylight):
        actor.set_folder_path('Lighting')
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-900, -900, 650), unreal.Rotator(pitch=-25, yaw=45, roll=0))


def _vector(value):
    return [value.x, value.y, value.z]


def _rotation(actor):
    value = actor.get_actor_rotation()
    return [value.pitch, value.yaw, value.roll]


def inspect_current(plan):
    """Read back the authored fixture properties, never repair actors here."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split('.')[0] != MAP:
        raise RuntimeError('Open the existing movement map explicitly before inspection')
    if world.get_world_settings().get_editor_property('default_game_mode') != plan['gm_class']:
        raise RuntimeError('Existing map GameMode differs; preserve it for review')
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    expected = {
        'Movement_Floor_1000m': unreal.StaticMeshActor, 'PlayerStart_Movement': unreal.PlayerStart,
        'Sun_Movement': unreal.DirectionalLight, 'Sky_Movement': unreal.SkyAtmosphere,
        'Ambient_Movement': unreal.SkyLight}
    found = {}
    for label, cls in expected.items():
        matches = [a for a in actors if a.get_actor_label() == label]
        if len(matches) != 1 or not isinstance(matches[0], cls):
            raise RuntimeError('Missing, duplicated or wrong actor type: ' + label)
        found[label] = matches[0]
    floor = found['Movement_Floor_1000m']
    comp = floor.static_mesh_component
    start = found['PlayerStart_Movement']
    if (_vector(floor.get_actor_location()) != [0, 0, -50]
            or _vector(floor.get_actor_scale3d()) != [1000, 1000, 1]
            or _rotation(floor) != [0, 0, 0]
            or _vector(start.get_actor_location()) != [0, 0, 150]
            or _rotation(start) != [0, 0, 0]
            or comp.get_editor_property('static_mesh') != plan['cube']
            or comp.get_material(0) != plan['grid']
            or str(comp.get_collision_profile_name()) != 'BlockAll'
            or comp.get_collision_enabled() != unreal.CollisionEnabled.QUERY_AND_PHYSICS
            or comp.get_collision_object_type() != unreal.CollisionChannel.ECC_WORLD_STATIC
            or comp.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN) != unreal.CollisionResponse.BLOCK):
        raise RuntimeError('Existing fixture geometry/collision differs; preserve it for review')
    return dict(map=MAP, size_cm=[100000, 100000, 100], ground_top_z_cm=0,
                player_start_cm=_vector(start.get_actor_location()),
                floor_rotation_degrees=_rotation(floor), player_start_rotation_degrees=_rotation(start),
                collision_profile=str(comp.get_collision_profile_name()),
                collision_enabled=str(comp.get_collision_enabled()),
                pawn_response=str(comp.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)),
                object_type=str(comp.get_collision_object_type()),
                mesh=_path(plan['cube']), material=_path(plan['grid']), **plan['configuration'])


def run():
    """Return truthful phase/result data, including partial failure.

    Existing maps are only inspected while already open and clean. No delete,
    SaveAll, silent reload, or automatic retry-save of a dirty user map.
    """
    report = dict(status='preflight_failed', phase='preflight', map=MAP,
                  material_created=False, material_saved=False, map_creation_attempted=False,
                  map_created=False, map_saved=False, configuration_verified=False,
                  configuration_verification_scope='GameMode/default roster references, expected actor presence, floor geometry/collision, PlayerStart transform',
                  lighting_and_material_rendering_verified=False,
                  report_written=False, runtime_acceptance_verified=False)
    try:
        plan = preflight()
        exists = unreal.EditorAssetLibrary.does_asset_exist(MAP) or _saved_file(MAP, '.umap').exists()
        if exists:
            report['phase'] = 'inspect_existing'
            if plan['grid'] is None:
                raise RuntimeError('Existing map grid material is missing; preserve map for review')
            if not _saved_file(MAP, '.umap').is_file():
                raise RuntimeError('Existing map has no saved package; review partial output')
            report['configuration'] = inspect_current(plan)
            report.update(status='existing_inspected', map_saved=True, configuration_verified=True,
                          recovery='Read-only inspection; no assets saved. Lighting/material rendering and PIE remain unverified.')
        else:
            report['phase'] = 'material'
            if plan['grid'] is None:
                # Creation can fail after allocation; a failed result does not
                # imply that the package is absent or safe to overwrite.
                report['material_creation_attempted'] = True
                report['material_created'] = None  # Allocation outcome unknown until create_asset returns.
                plan['grid'] = _create_material(report)
            report['material_saved'] = True
            report['phase'] = 'create_map'
            report['map_creation_attempted'] = True
            report['map_created'] = None  # new_level can allocate/save before reporting failure.
            levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            if not levels.new_level(MAP):
                raise RuntimeError('new_level failed; inspect any partial map')
            report['map_created'] = True
            report['phase'] = 'build_actors'
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            _build_world(world, plan)
            report['phase'] = 'readback'
            report['configuration'] = inspect_current(plan)
            report['configuration_verified'] = True
            report['phase'] = 'save_map'
            if not levels.save_current_level():
                raise RuntimeError('Map save failed; complete in-memory map retained for review')
            if not _saved_file(MAP, '.umap').is_file():
                raise RuntimeError('Map save returned success but package is missing')
            report.update(status='created', map_saved=True,
                          recovery='Rerun on the clean open map to inspect/recover its report without rebuilding.')
        report['phase'] = 'report'
    except Exception as error:
        report['error'] = str(error)
        if report['phase'] != 'preflight':
            report['status'] = 'existing_requires_review' if report['phase'] == 'inspect_existing' else 'partial_failure'
        report['recovery'] = (
            'Preserve partial assets. If the map is complete, review/save it explicitly then rerun for read-only inspection. '
            'Incomplete maps/materials require manual review; this script never deletes or overwrites them. '
            'After resolving missing dependencies with no partial map present, rerun creation.')
    # Best-effort inventory distinguishes saved package presence from completed
    # fixture saves (new_level may already have saved an empty map).
    report['map_package_present'] = _saved_file(MAP, '.umap').is_file()
    report['material_package_present'] = _saved_file(MATERIAL, '.uasset').is_file()
    output = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'LevelDesign'
    report['report_path'] = str(output / ('map_configuration_' + uuid4().hex + '.json'))
    try:
        output.mkdir(parents=True, exist_ok=True)
        report['report_written'] = True
        Path(report['report_path']).write_text(json.dumps(report, indent=2), encoding='utf-8')
    except Exception as error:
        report['report_written'] = False
        report['report_error'] = str(error)
        report['asset_result'] = report['status']
        report['status'] = 'report_failed'
    unreal.log('MOVEMENT_TEST_RESULT ' + json.dumps(report))
    return report


if __name__ == '__main__':
    movement_level_result = run()
