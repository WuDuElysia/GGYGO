"""@file observe_kevin_multiplayer.py
@brief 正式 P3 的 Listen Server/Client 复制诊断；只驱动本次 PIE，不保存资产。

复用最小联机的 PIE、原生 FX/ActorChannel 观察和视口读回。
Kevin 使用专用 AnimInstance；姿态取当前骨骼与实际截图，不冒充玩家 finalize 观察。
先观察正式 BT，再暂停决策，向原 GAS 请求确定的三招；不改轨迹或生命。
空连前只在服务器摆放静止玩家，使原轨迹真实落到其胶囊；客户端位置仅走复制。
"""
import json
import os
import sys
import time
import traceback
from pathlib import Path
import unreal as ue

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import minimal_multiplayer_checks as check

OUT = Path(os.environ['GGYGO_KEVIN_NETWORK_OUT'])


def path(obj):
    return obj.get_path_name() if obj else None


def vec(value):
    return [value.x, value.y, value.z]


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def worlds():
    return list(ue.EditorLevelLibrary.get_pie_worlds(True))


def active(asc):
    result = []
    for handle in asc.get_all_abilities():
        ability, instance = ue.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(asc, handle)
        if instance and ue.AbilitySystemLibrary.is_gameplay_ability_active(ability):
            result.append(ability.get_class().get_name())
    return result


class Run:
    def __init__(self):
        self.started = time.monotonic()
        self.state = 'boot'
        self.error = None
        self.endpoints = {}
        self.records, self.events, self.images, self.pending = [], [], [], []
        self.current = None
        self.queue = ['Ice03', 'Fire02', 'AirChain01']
        self.completed = []
        self.last_sample = -1
        self.landed = []
        self.contacts = []
        self.close_setup = None
        self.busy = False
        self.handle = ue.register_slate_post_tick_callback(self.tick)

    def event(self, name, **value):
        row = dict(event=name, elapsed=time.monotonic()-self.started, **value)
        self.events.append(row)
        ue.log('KEVIN_NETWORK ' + json.dumps(row, ensure_ascii=False))

    def tick(self, _dt):
        if self.busy:
            return
        self.busy = True
        try:
            self.poll_images()
            if time.monotonic()-self.started > 240 and self.state not in ('ending', 'done'):
                raise RuntimeError('联机观察超时，保留未覆盖项')
            self.step()
        except Exception:
            self.error = traceback.format_exc()
            ue.log_error(self.error)
            self.finish()
        finally:
            self.busy = False

    def step(self):
        if self.state == 'boot':
            if time.monotonic()-self.started < 15 or ue.AssetRegistryHelpers.get_asset_registry().is_loading_assets():
                return
            check.require(not worlds(), '只允许启动本宿主 PIE')
            check.require('-nullrhi' not in ue.SystemLibrary.get_command_line().lower(), '需要 D3D12')
            self.les = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
            settings = ue.get_default_object(ue.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
            expected = dict(PlayNetMode='PIE_ListenServer', PlayNumberOfClients=2, RunUnderOneProcess=True,
                bLaunchSeparateServer=False, NewWindowWidth=640, NewWindowHeight=360,
                ClientWindowWidth=640, ClientWindowHeight=360)
            ue.ToolsetLibrary.set_object_properties(settings, json.dumps(expected))
            actual = json.loads(ue.ToolsetLibrary.get_object_properties(settings, list(expected)))
            check.require(actual == expected, 'PIE 配置未读回：' + repr(actual))
            ue.SystemLibrary.execute_console_command(None, 'Slate.bAllowThrottling 0')
            ue.SystemLibrary.execute_console_command(None, 't.MaxFPS 60')
            check.require(ue.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling') == 0,
                          'Slate 节流未关闭')
            self.les.editor_set_viewport_realtime(False)
            self.request = ue.ToolsetRegistry.execute_tool('EditorToolset.EditorAppToolset', 'StartPIE',
                json.dumps(dict(options=dict(playMode='PlayMode_InEditorFloating', warmupSeconds=0.0))))
            check.require(self.request is not None, '没有 PIE 请求')
            self.state = 'pair'
            self.event('start', configuration=actual, topology='one_editor_two_pie_worlds')
            return
        if self.state == 'pair':
            check.require(not self.request.get_editor_property('error'), 'PIE 启动错误')
            if self.request.get_editor_property('is_complete'):
                self.pair()
            return
        if self.state == 'ending':
            if not worlds() and not self.pending:
                save('observations.json', self.result)
                self.state = 'done'
                ue.unregister_slate_post_tick_callback(self.handle)
                ue.SystemLibrary.quit_editor()
            return
        if self.state == 'done':
            return
        now = ue.GameplayStatics.get_time_seconds(self.endpoints['server']['world'])
        if self.state == 'destroyed':
            if now-self.destroyed_at < 3:
                return
            remainder = {side: [path(a) for a in ue.GameplayStatics.get_all_actors_of_class(ep['world'], ue.GGYGOBossCharacter)]
                         for side, ep in self.endpoints.items()}
            self.event('encounter_cleanup', bosses=remainder)
            check.require(not any(remainder.values()), 'Encounter 销毁未复制到客户端')
            self.finish()
            return
        self.sample(now)
        if self.state == 'cleanup_readback':
            if self.pending:
                return
            self.stop_observations()
            self.encounter.destroy_actor()
            self.destroyed_at, self.state = now, 'destroyed'
            return
        if self.state == 'production':
            if now-self.ready_at < 5:
                return
            self.controller.get_editor_property('brain_component').stop_logic('联机三招隔离复验')
            self.controller.set_combat_target(self.remote_target)
            self.controller.set_focus(self.remote_target)
            self.state = 'drain'
            self.event('isolated', target=path(self.remote_target), health_writes=False, teleport=False)
            return
        server = self.endpoints['server']
        running = active(server['asc'])
        if self.state == 'drain':
            if running:
                return
            self.next_at = now+2
            self.state = 'skills'
        if self.state != 'skills':
            return
        if self.current:
            if running:
                self.seen_current |= ('BP_GA_Kevin_' + self.current + '_KVB_C') in running
                age = now-self.action_started
                if self.shots and age >= self.shots[0]:
                    due = self.shots.pop(0)
                    self.capture(self.current + '_' + str(due))
                return
            check.require(self.seen_current, '请求没有进入已授予的能力')
            check.require(not server['move'].has_active_action_motion(), '能力结束仍有动作位移')
            self.event('action_complete', action=self.current, game_time=now)
            self.completed.append(self.current)
            self.current = None
            self.next_at = now+4
            return
        if now < self.next_at:
            return
        if not self.queue:
            self.event('skill_cleanup', resources=self.resources(), game_time=now)
            self.capture('cleanup')
            check.require(not any(self.resources().values()), '技能结束仍有 Kevin 活动资源')
            for side, ep in self.endpoints.items():
                check.require(ep['move'].get_editor_property('movement_mode') == ue.MovementMode.MOVE_WALKING,
                              side+' 最终未 Walking')
                check.require(not isinstance(ue.Pawn.get_movement_base_actor(ep['boss']), ue.Character), '角色基底残留')
            check.require(any(r['action'] == 'AirChain01' and not r['character'] for r in self.landed), '缺真实空连环境落地')
            check.require(not any(r['character'] for r in self.landed), '仍发生角色 Landed')
            check.require(any(r['action'] == 'AirChain01' and 'FALLING' in r['movement'] for r in self.contacts),
                          '空连未实际命中角色胶囊，不能签贴身落地')
            self.state = 'cleanup_readback'
            return
        if self.queue[0] == 'AirChain01':
            if self.close_setup is None:
                target = server['pc'].get_controlled_pawn()
                old = target.get_actor_location()
                location = server['boss'].get_actor_location()+server['boss'].get_actor_forward_vector()*96
                location.z = old.z
                target.set_actor_location(location, False, True)
                target.force_net_update()
                self.controller.set_combat_target(target)
                self.controller.set_focus(target)
                self.close_setup = dict(player_id=str(check.player_id(server['pc'].get_editor_property('player_state'))),
                    original_location=vec(old), setup_location=vec(target.get_actor_location()), game_time=now,
                    scope='server_player_fixture_only; boss_trajectory_and_client_position_not_written')
                self.event('close_landing_setup', **self.close_setup)
                self.next_at = now+2
                return
            player_id = self.close_setup['player_id']
            endpoints = self.records[-1]['endpoints']
            a = endpoints['server']['players'][player_id]['location']
            b = endpoints['client']['players'][player_id]['location']
            check.require(sum((x-y)**2 for x,y in zip(a,b)) < 1, '贴身玩家的位置尚未真实复制')
        self.current = self.queue.pop(0)
        cls = ue.load_class(None, '/Game/Characters/Boss/Kevin/DemonBattle/Abilities/BP_GA_Kevin_'+self.current+'_KVB.BP_GA_Kevin_'+self.current+'_KVB_C')
        accepted = server['asc'].call_method('TryActivateAbilityByClass', args=(cls, False))
        self.event('request', action=self.current, accepted=accepted, game_time=now)
        check.require(accepted, '已授予能力拒绝')
        self.seen_current, self.action_started, self.shots = False, now, [.35, 1.1, 2.0, 4.0]

    def pair(self):
        current = worlds()
        if len(current) != 2:
            return
        for world in current:
            side = 'server' if ue.SystemLibrary.is_server(world) else 'client'
            if ue.SystemLibrary.is_standalone(world):
                return
            bosses = ue.GameplayStatics.get_all_actors_of_class(world, ue.GGYGOBossCharacter)
            if len(bosses) != 1:
                return
            boss = bosses[0]
            asc = ue.AbilitySystemLibrary.get_ability_system_component(boss)
            mesh = boss.get_editor_property('mesh')
            if not asc or not mesh.get_anim_instance():
                return
            pcs = [p for p in ue.GameplayStatics.get_all_actors_of_class(world, ue.PlayerController) if p.is_local_controller()]
            if len(pcs) != 1 or not pcs[0].get_controlled_pawn() or not pcs[0].get_editor_property('player_state'):
                return
            local_pawn = pcs[0].get_controlled_pawn()
            health = ue.GGYGOHealthComponent.find_health_component(local_pawn)
            if not health or health.get_health() <= 0:
                return
            library = ue.get_default_object(ue.load_class(None, '/Script/Engine.SubsystemBlueprintLibrary'))
            sub = library.call_method('GetLocalPlayerSubSystemFromPlayerController',
                args=(pcs[0], ue.EnhancedInputLocalPlayerSubsystem.static_class()))
            assembly = ue.GGYGOPlayerInputBridgeLibrary.read_local_player_input_assembly(world, sub.get_outer())
            if assembly[0] != ue.GGYGOPlayerInputAssemblyStatus.READY:
                return
            self.endpoints[side] = dict(world=world, boss=boss, asc=asc, mesh=mesh, anim=mesh.get_anim_instance(),
                move=boss.get_editor_property('character_movement'), pc=pcs[0])
        if len(self.endpoints) != 2:
            return
        server, client = self.endpoints['server'], self.endpoints['client']
        viewer_id = check.player_id(client['pc'].get_editor_property('player_state'))
        self.channels = {side: ue.GGYGOPlayerActionObservation.create_observation() for side in self.endpoints}
        channels = {side: json.loads(self.channels[side].read_network_fx_channel(ep['world'], viewer_id, ep['boss']))
                    for side, ep in self.endpoints.items()}
        if not all(c.get('connection_open') and c.get('channel_id') for c in channels.values()):
            return
        check.require(channels['server']['pawn_net_guid'] == channels['client']['pawn_net_guid'], '两端 Boss NetGUID 不同')
        self.viewer_id = viewer_id
        targets = [p for p in ue.GameplayStatics.get_all_actors_of_class(server['world'], ue.PlayerController)
                   if p.get_editor_property('player_state') and check.player_id(p.get_editor_property('player_state')) == viewer_id]
        check.require(len(targets) == 1, '服务器缺远端玩家')
        self.remote_target = targets[0].get_controlled_pawn()
        encounters = ue.GameplayStatics.get_all_actors_of_class(server['world'], ue.GGYGOBossEncounter)
        check.require(len(encounters) == 1, '正式 Encounter 不唯一')
        self.encounter = encounters[0]
        self.controller = self.encounter.get_boss_controller()
        self.landed_callback = self.on_landed
        server['boss'].landed_delegate.add_callable(self.landed_callback)
        self.hit_callback = self.on_hit
        server['boss'].on_actor_hit.add_callable(self.hit_callback)
        self.fx = {}
        for side, ep in self.endpoints.items():
            obs = ue.GGYGOPlayerActionObservation.create_observation()
            check.native_success(obs.begin_fx_observation(ep['asc'], ep['boss'], ep['mesh'], 'kevin_network', 4096), side+' FX')
            self.fx[side] = obs
        self.camera = self.make_camera(client)
        self.ready_at = ue.GameplayStatics.get_time_seconds(server['world'])
        self.state = 'production'
        self.event('paired', channels=channels, target=path(self.remote_target), game_time=self.ready_at,
                   roles={s:str(e['boss'].get_local_role()) for s,e in self.endpoints.items()},
                   anim_classes={s:path(e['anim'].get_class()) for s,e in self.endpoints.items()})

    def make_camera(self, ep):
        transform = ue.Transform()
        gameplay = ue.GameplayStatics.get_default_object()
        camera = gameplay.call_method('BeginDeferredActorSpawnFromClass', args=(ep['world'], ue.CameraActor.static_class(),
            transform, ue.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None, ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        gameplay.call_method('FinishSpawningActor', args=(camera, transform, ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        camera.get_component_by_class(ue.CameraComponent).set_field_of_view(80)
        ep['pc'].set_view_target_with_blend(camera, 0.0)
        return camera

    def on_landed(self, hit):
        values = ue.GameplayStatics.get_default_object().call_method('BreakHitResult', args=(hit,))
        row = dict(action=self.current, character=isinstance(values[9], ue.Character), actor=path(values[9]),
                   component=path(values[10]), game_time=ue.GameplayStatics.get_time_seconds(self.endpoints['server']['world']))
        self.landed.append(row)
        self.event('landed', **row)

    def on_hit(self, actor, other, impulse, hit):
        if not isinstance(other, ue.Character):
            return
        server = self.endpoints['server']
        row = dict(action=self.current, other=path(other),
            movement=str(server['move'].get_editor_property('movement_mode')),
            game_time=ue.GameplayStatics.get_time_seconds(server['world']),
            boss_location=vec(actor.get_actor_location()), other_location=vec(other.get_actor_location()))
        self.contacts.append(row)
        self.event('character_contact', **row)

    def resources(self):
        result = {s:[] for s in self.endpoints}
        for side, ep in self.endpoints.items():
            for cls in (ue.GGYGOBossProjectile, ue.GGYGOBossAudioActor):
                result[side].extend(path(a) for a in ue.GameplayStatics.get_all_actors_of_class(ep['world'], cls))
            for cls, prop in ((ue.NiagaraComponent, 'asset'), (ue.AudioComponent, 'sound')):
                for c in ue.ObjectIterator(cls):
                    if c.get_world() != ep['world']:
                        continue
                    asset = c.get_editor_property(prop)
                    playing = c.is_active() if cls == ue.NiagaraComponent else c.is_playing()
                    if playing and asset and '/Kevin/' in path(asset):
                        result[side].append(dict(component=path(c), asset=path(asset)))
        return result

    def sample(self, now):
        ep = self.endpoints['client']
        center = ep['boss'].get_actor_location() + ue.Vector(0,0,30)
        location = center + ep['boss'].get_actor_forward_vector()*1000 + ep['boss'].get_actor_right_vector()*500 + ue.Vector(0,0,800)
        self.camera.set_actor_location_and_rotation(location, ue.MathLibrary.find_look_at_rotation(location,center), False, True)
        if now-self.last_sample < .1:
            return
        self.last_sample = now
        row = dict(game_time=now, phase=self.state, action=self.current, resources=self.resources(), endpoints={})
        for side, ep in self.endpoints.items():
            montage = ep['anim'].get_current_active_montage()
            player_health = {}
            for ps in ue.GameplayStatics.get_game_state(ep['world']).get_editor_property('player_array'):
                pawn = ps.get_pawn()
                health = ue.GGYGOHealthComponent.find_health_component(pawn) if pawn else None
                player_health[str(check.player_id(ps))] = dict(pawn=path(pawn), health=health.get_health() if health else None,
                    location=vec(pawn.get_actor_location()) if pawn else None)
            row['endpoints'][side] = dict(location=vec(ep['boss'].get_actor_location()), role=str(ep['boss'].get_local_role()),
                movement=str(ep['move'].get_editor_property('movement_mode')), base=path(ue.Pawn.get_movement_base_actor(ep['boss'])),
                montage=path(montage), position=ep['anim'].montage_get_position(montage) if montage else None,
                bone_pose={str(ep['mesh'].get_bone_name(i)):ep['mesh'].get_socket_transform(
                    ep['mesh'].get_bone_name(i),ue.RelativeTransformSpace.RTS_COMPONENT).export_text() for i in (0,1,10)},
                action_motion=ep['move'].has_active_action_motion(), active=active(ep['asc']), players=player_health,
                clock=json.loads(ue.GGYGOPlayerActionObservation.read_world_clock(ep['world'])),
                channel=json.loads(self.channels[side].read_network_fx_channel(ep['world'],self.viewer_id,ep['boss'])))
            check.native_success(self.fx[side].sample(time.monotonic()-self.started), side+' FX.Sample')
        self.records.append(row)

    def capture(self, label):
        filename = OUT / (str(len(self.images)+len(self.pending)).zfill(3)+'_'+label+'.png')
        task = ue.GGYGOViewportReadbackLibrary.begin_game_viewport_readback_to_file(self.endpoints['client']['world'], str(filename), 0)
        self.pending.append((task, filename))

    def poll_images(self):
        for task, filename in list(self.pending):
            result = task.read_result()
            if result.status not in (ue.GGYGOViewportReadbackStatus.COMPLETE, ue.GGYGOViewportReadbackStatus.FAILED,
                                     ue.GGYGOViewportReadbackStatus.CANCELLED):
                continue
            self.images.append(dict(file=str(filename), status=str(result.status), world=result.world_path, net_mode=result.net_mode,
                file_write_complete=result.file_write_complete, file_readback_verified=result.file_readback_verified, error=result.error))
            task.release()
            self.pending.remove((task, filename))

    def stop_observations(self):
        for obs in getattr(self, 'fx', {}).values():
            obs.stop_observation()

    def finish(self):
        if self.state == 'ending':
            return
        self.stop_observations()
        self.result = dict(error=self.error, completed=self.completed, events=self.events, records=self.records, landed=self.landed,
            contacts=self.contacts, close_setup=self.close_setup,
            images=self.images, topology='one_editor_two_pie_worlds',
            pose_scope='current_component_space_bones_and_client_images; not_player_finalize_observer',
            fx={s:json.loads(o.get_observation_json()) for s,o in getattr(self,'fx',{}).items()})
        save('observations.json', self.result)
        self.event('finish', error=self.error, completed=self.completed)
        self.state = 'ending'
        ue.get_editor_subsystem(ue.LevelEditorSubsystem).editor_request_end_play()


run = Run()
