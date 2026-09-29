"""Create the standalone movement test map from the Unreal Editor Python console.
Refuses to replace an existing map or leave dirty editor map packages behind.
"""
import json
from pathlib import Path
import unreal

MAP = '/Game/Map/L_Movement_Test'
REPORT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'LevelDesign'
REPORT.mkdir(parents=True, exist_ok=True)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if unreal.EditorAssetLibrary.does_asset_exist(MAP):
    raise RuntimeError('Map already exists; inspect it before editing.')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Current map has unsaved changes; preserve it before switching.')
assert levels.new_level(MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode', unreal.load_class(None, '/Game/BP/GamePlay/BP_GameMode.BP_GameMode_C'))

def spawn(cls, label, xyz, rotation=(0, 0, 0)):
    actor = actors.spawn_actor_from_class(cls, unreal.Vector(*xyz), unreal.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]))
    actor.set_actor_label(label)
    return actor

cube = unreal.load_asset('/Engine/BasicShapes/Cube')
grid = unreal.load_asset('/Game/Map/Materials/M_MovementGrid')
if not grid:
    grid = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_MovementGrid', '/Game/Map/Materials', unreal.Material, unreal.MaterialFactoryNew())
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
    unreal.EditorAssetLibrary.save_loaded_asset(grid)
assert cube and grid
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
assert levels.save_current_level()
gm = unreal.get_default_object(world.get_world_settings().get_editor_property('default_game_mode'))
exp = gm.get_editor_property('experience')
roster = exp.get_editor_property('squad_members')
report = dict(map=MAP, size_cm=[100000,100000,100], ground_top_z_cm=0, player_start_cm=[0,0,150], collision_profile=str(comp.get_collision_profile_name()), collision_enabled=str(comp.get_collision_enabled()), pawn_response=str(comp.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)), object_type=str(comp.get_collision_object_type()), mesh=cube.get_path_name(), material=grid.get_path_name(), game_mode=gm.get_class().get_path_name(), experience=exp.get_path_name(), roster=[dict(pawn_data=p.get_path_name(),pawn_class=p.get_editor_property('pawn_class').get_path_name(),movement_set=p.get_editor_property('movement_set').get_path_name(),input_config=p.get_editor_property('input_config').get_path_name()) for p in roster])
(REPORT/'map_configuration.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MOVEMENT_TEST_CREATED', json.dumps(report))
