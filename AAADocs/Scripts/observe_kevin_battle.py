"""@file observe_kevin_battle.py
@brief 从 P3 正式 Encounter 入口观察战斗，以玩家输入操作，不修改运行时生命或直接激活 Boss。
"""
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import unreal as ue

sys.dont_write_bytecode = True
OUT = Path(os.environ['GGYGO_KEVIN_LOG']).parent
MAP = '/Game/Map/BH3/L_KevinBoss_P3'
TESTS = ''
CONFIG = json.loads(Path('F:/ue_project/GGYGO/AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Montage_Config.json').read_text(encoding='utf-8-sig'))
RECOVERY = {a['montage'].rsplit('/',1)[-1]:max((w['end_seconds'] for w in a.get('hit_windows',[])),default=0) for a in CONFIG['skill_assemblies']}
VISUAL_MODE = os.environ.get('GGYGO_KEVIN_DIAGNOSTIC_CAMERA') == '1'
STATIONARY_SECONDS = 4.0


def log(kind, **values):
    ue.log('KEVIN_BATTLE_' + kind + ' ' + json.dumps(values, ensure_ascii=False))


class Battle:
    def __init__(self, record_audio=True):
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.state = 'boot'
        self.started = time.monotonic()
        self.deadline = self.started + 180
        self.pressed = set()
        self.captures = []
        self.pending = []
        self.observed = set()
        self.scheduled_images = []
        self.last_sample = -1
        self.last_attack = -1
        self.last_flight_image = -1
        self.was_flying = False
        self.last_dash = False
        self.dash_start = None
        self.dash_count = 0
        self.chase_complete = False
        self.input_policy = dict(sign=-1, clearance=100.0)
        self.policy_read_at=0
        self.camera = None
        self.seen_fx = set()
        self.seen_audio = set()
        self.world = self.pc = self.pawn = self.boss = self.encounter = None
        self.recording = False
        self.record_audio = record_audio
        self.advancing = False
        self.handle = ue.register_slate_post_tick_callback(self.tick)

    def key(self, name, down):
        if (name in self.pressed) == down:
            return
        result = ue.GGYGOPlayerInputBridgeLibrary.submit_digital_key_event(self.world, self.lp, self.pc,
            self.pawn, self.pinput, self.input_comp, self.device, self.keys[name], down)
        if result is None:
            raise RuntimeError('原玩家输入装配拒绝：' + name)
        if result[-1]:
            raise RuntimeError('原玩家输入装配拒绝：' + str(result[-1]))
        (self.pressed.add if down else self.pressed.discard)(name)

    def capture(self, label):
        path = OUT / (str(len(self.captures)).zfill(3) + '_' + label + '.png')
        task = ue.GGYGOViewportReadbackLibrary.begin_game_viewport_readback_to_file(self.world, str(path), 0)
        if task is None:
            raise RuntimeError('游戏 viewport 读回请求失败')
        item = dict(path=str(path), label=label, task=task)
        self.captures.append(item)
        self.pending.append(item)

    def poll_images(self):
        for item in list(self.pending):
            result = item['task'].read_result()
            if result.status in (ue.GGYGOViewportReadbackStatus.COMPLETE, ue.GGYGOViewportReadbackStatus.FAILED,
                                 ue.GGYGOViewportReadbackStatus.CANCELLED):
                log('IMAGE', path=item['path'], status=str(result.status), error=result.error,
                    saved=result.file_write_complete, readback=result.file_readback_verified)
                item.pop('task').release()
                self.pending.remove(item)

    def setup(self, world):
        pc = ue.GameplayStatics.get_player_controller(world, 0)
        pawn = pc.get_controlled_pawn() if pc else None
        if not pawn:
            return False
        encounters = ue.GameplayStatics.get_all_actors_of_class(world, ue.GGYGOBossEncounter)
        if len(encounters) != 1:
            raise RuntimeError('P3 正式 Encounter 不唯一')
        encounter = encounters[0]
        boss = encounter.get_boss_avatar()
        if not boss:
            return False
        boss_state = encounter.get_boss_state()
        health = ue.GGYGOHealthComponent.find_health_component(boss)
        player_health = ue.GGYGOHealthComponent.find_health_component(pawn)
        if not health or not player_health:
            return False
        lib = ue.get_default_object(ue.load_class(None, '/Script/Engine.SubsystemBlueprintLibrary'))
        sub = lib.call_method('GetLocalPlayerSubSystemFromPlayerController',
                             args=(pc, ue.EnhancedInputLocalPlayerSubsystem.static_class()))
        lp = sub.get_outer()
        status, ipc, ipawn, pinput, comp, user, device, diagnostic = \
            ue.GGYGOPlayerInputBridgeLibrary.read_local_player_input_assembly(world, lp)
        if status != ue.GGYGOPlayerInputAssemblyStatus.READY:
            return False
        if ipc != pc or ipawn != pawn:
            raise RuntimeError('玩家装配来源不一致')
        self.world, self.pc, self.pawn, self.boss, self.encounter = world, pc, pawn, boss, encounter
        self.lp, self.pinput, self.input_comp, self.device = lp, pinput, comp, device
        self.boss_state, self.health, self.player_health = boss_state, health, player_health
        self.keys = {}
        for name in ('W', 'S', 'D', 'LeftMouseButton'):
            value = ue.Key()
            if not value.import_text(name) or value.export_text() != name:
                raise RuntimeError('数字键构造失败')
            self.keys[name] = value
        self.asc = ue.AbilitySystemLibrary.get_ability_system_component(boss)
        self.boss_move = boss.get_editor_property('character_movement')
        self.boss_anim = boss.get_editor_property('mesh').get_anim_instance()
        self.health_callback = self.on_boss_health
        self.death_callback = self.on_death
        self.landed_callback = self.on_landed
        health.on_health_changed.add_callable(self.health_callback)
        health.on_death_finished.add_callable(self.death_callback)
        boss.landed_delegate.add_callable(self.landed_callback)
        self.death_finished = False
        self.phase = str(boss_state.get_current_phase_tag().export_text())
        self.started = time.monotonic()
        self.deadline = self.started + 600
        if self.record_audio:
            ue.AudioMixerLibrary.start_recording_output(world, 600.0, None)
            self.recording = True
        if VISUAL_MODE:
            self.place_diagnostic_camera()
        combo=ue.load_class(None,'/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo.GA_Pyrios_Attack_Combo_C')
        log('PLAYER_FACING_POLICY', policies=[str(step.get_editor_property('start_facing_policy')) for step in ue.get_default_object(combo).get_editor_property('combo_steps')])
        log('INTERVENTIONS', movement_aim='Held W projected through diagnostic ControlYaw; tangent attack input', input_policy=self.input_policy, first_two_dashes_stationary=True, automatic_digital_keys=['W','S','D','LeftMouseButton'], diagnostic_camera=VISUAL_MODE, direct_boss_activation=False, health_writes=False, actor_position_writes=False, bt_stopped=False)
        log('READY', world=world.get_path_name(), pawn=pawn.get_path_name(), boss=boss.get_path_name(),
            health=health.get_health(), player_health=player_health.get_health(), phase=self.phase)
        self.capture('start')
        self.player_start = pawn.get_actor_location()
        return True

    def place_diagnostic_camera(self):
        # 只生成本次 PIE 的观察相机；不改生产相机资产、角色或技能位置。
        transform = ue.Transform()
        transform.translation = self.boss.get_actor_location() + ue.Vector(0, -1100, 900)
        transform.rotation = ue.MathLibrary.find_look_at_rotation(
            transform.translation, self.boss.get_actor_location()).quaternion()
        gameplay = ue.GameplayStatics.get_default_object()
        self.camera = gameplay.call_method('BeginDeferredActorSpawnFromClass', args=(self.world,
            ue.CameraActor.static_class(), transform, ue.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,
            None, ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        gameplay.call_method('FinishSpawningActor', args=(self.camera, transform,
            ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        self.camera.get_component_by_class(ue.CameraComponent).set_field_of_view(70)
        self.pc.set_view_target_with_blend(self.camera, 0.0)
        log('DIAGNOSTIC_CAMERA', actor=self.camera.get_path_name(), production_camera_changed=False)

    def on_boss_health(self, component, old, new, instigator):
        log('HEALTH', old=old, new=new, instigator=instigator.get_path_name() if instigator else None)

    def on_death(self, actor):
        self.death_finished = True
        log('DEATH_FINISHED', actor=actor.get_path_name())
        self.capture('death_finished')
        self.detach()

    def on_landed(self, hit):
        values = ue.GameplayStatics.get_default_object().call_method('BreakHitResult', args=(hit,))
        active_at_landing=[]
        for handle in self.asc.get_all_abilities():
            ability, instance=ue.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(self.asc,handle)
            if instance and ue.AbilitySystemLibrary.is_gameplay_ability_active(ability): active_at_landing.append(ability.get_class().get_name())
        log('LANDED', active_abilities=active_at_landing, seconds=time.monotonic()-self.started, game_time=ue.GameplayStatics.get_time_seconds(self.world), character=isinstance(values[9], ue.Character), actor=values[9].get_path_name() if values[9] else None, montage=self.boss_anim.get_current_active_montage().get_name() if self.boss_anim.get_current_active_montage() else None, hit=hit.export_text())
        self.scheduled_images.append((time.monotonic() + .25, 'landed'))

    def detach(self):
        if hasattr(self, 'health_callback'):
            self.health.on_health_changed.remove_callable(self.health_callback)
            self.health.on_death_finished.remove_callable(self.death_callback)
            self.boss.landed_delegate.remove_callable(self.landed_callback)
            del self.health_callback

    def cleanup_observation(self):
        actors = ue.GameplayStatics.get_all_actors_of_class(self.world, ue.Actor)
        resources = []
        for actor in actors:
            if isinstance(actor, (ue.GGYGOBossProjectile, ue.GGYGOBossAudioActor)):
                resources.append(actor.get_path_name())
        for cls, prop in ((ue.NiagaraComponent, 'asset'), (ue.AudioComponent, 'sound')):
            for component in ue.ObjectIterator(cls):
                if component.get_world() != self.world:
                    continue
                asset = component.get_editor_property(prop)
                active = component.is_active() if cls == ue.NiagaraComponent else component.is_playing()
                if asset and '/Kevin/' in asset.get_path_name() and active:
                    resources.append(component.get_path_name())
        log('CLEANUP', boss_avatar=ue.SystemLibrary.is_valid(self.encounter.get_boss_avatar()),
            resources=resources, death_finished=self.death_finished)
        self.capture('cleanup')

    def observe_presentation(self, now):
        # 包含 Outer 为 World 的独立声音／Niagara；只读原 PIE 的真实活动实例。
        for cls, prop, seen, kind in ((ue.NiagaraComponent, 'asset', self.seen_fx, 'FX'),
                                     (ue.AudioComponent, 'sound', self.seen_audio, 'AUDIO')):
            for component in ue.ObjectIterator(cls):
                if component.get_world() != self.world:
                    continue
                asset = component.get_editor_property(prop)
                active = component.is_active() if kind == 'FX' else component.is_playing()
                if not asset or '/Kevin/' not in asset.get_path_name() or not active:
                    continue
                if asset.get_path_name() in seen:
                    continue
                seen.add(asset.get_path_name())
                log(kind, seconds=now - self.started, asset=asset.get_path_name(),
                    component=component.get_path_name(), active=active,
                    world_transform=component.get_world_transform().export_text())
                if kind == 'FX':
                    self.scheduled_images.extend([(now + .05, asset.get_name()),
                                                  (now + .3, asset.get_name() + '_030')])

    def run(self):
        now = time.monotonic()
        if self.state == 'boot':
            if '-nosound' in ue.SystemLibrary.get_command_line().lower():
                raise RuntimeError('战斗实拍必须启用音频')
            if not self.levels.load_level(MAP):
                raise RuntimeError('P3 加载失败')
            support = ue.load_asset('/Game/Environments/BH3/Stage/Stage_KevinBoss_P3/StaticMeshes/SM_KevinBossP3_PawnSupport')
            ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem).get_collision_complexity(support)
            ue.SystemLibrary.execute_console_command(None, 'au.DisableAppVolume 1')
            ue.SystemLibrary.execute_console_command(None, 'au.NeverDisableSubmixes 1')
            ue.SystemLibrary.execute_console_command(None, 'Slate.bAllowThrottling 0')
            ue.SystemLibrary.execute_console_command(None, 't.MaxFPS 60')
            ue.SystemLibrary.execute_console_command(None, 'r.MotionBlurQuality 0')
            log('CAPTURE_SETTINGS', motion_blur=False, purpose='诊断取景，未保存生产相机或渲染配置')
            self.state = 'begin'
            return
        if self.state == 'begin':
            self.levels.editor_request_begin_play()
            self.state = 'starting'
            return
        if self.state == 'starting':
            world = self.editor.get_game_world()
            if world and self.setup(world):
                self.state = 'battle'
            elif now > self.deadline:
                raise RuntimeError('正式 PIE／角色输入未在时限内就绪')
            return
        if self.state == 'ending':
            self.poll_images()
            if not self.pending or now > self.deadline:
                self.levels.editor_request_end_play()
                self.state = 'quit'
            return
        if self.state == 'quit':
            if self.editor.get_game_world() is None:
                if not TESTS:
                    ue.unregister_slate_post_tick_callback(self.handle)
                    ue.SystemLibrary.quit_editor()
                    return
                self.test_offset = Path(os.environ['GGYGO_KEVIN_LOG']).stat().st_size
                ue.SystemLibrary.execute_console_command(self.editor.get_editor_world(), 'Automation RunTests ' + TESTS, None)
                self.state, self.deadline = 'testing', now + 120
            return
        if self.state == 'testing':
            with Path(os.environ['GGYGO_KEVIN_LOG']).open('rb') as stream:
                stream.seek(self.test_offset)
                output = stream.read().decode('utf-8', errors='replace')
            if 'Automation Test Queue Empty' in output or now > self.deadline:
                log('AUTOMATION', success='Automation Test Queue Empty' in output and
                    'Result={Fail}' not in output and output.count('Result={Success}') == 1,
                    completed=output.count('Test Completed.'), expected=1)
                ue.unregister_slate_post_tick_callback(self.handle)
                ue.SystemLibrary.quit_editor()
            return
        self.poll_images()
        if self.state == 'cleanup':
            if ue.GameplayStatics.get_time_seconds(self.world) >= self.cleanup_at:
                player_asc=ue.AbilitySystemLibrary.get_ability_system_component(self.pawn)
                player_active=[]
                for h in player_asc.get_all_abilities():
                    a,i=ue.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(player_asc,h)
                    if i and ue.AbilitySystemLibrary.is_gameplay_ability_active(a): player_active.append(a.get_class().get_name())
                player_motion=self.pawn.get_editor_property('character_movement').has_active_action_motion()
                if player_active or player_motion:
                    if ue.GameplayStatics.get_time_seconds(self.world)-self.removed_game_time > 20: raise RuntimeError('玩家普攻未在收尾时限内归还')
                    return
                log('PLAYER_QUIET', active=player_active, action_motion=player_motion)
                log('CLEANUP_WAIT', game_seconds=ue.GameplayStatics.get_time_seconds(self.world)-self.removed_game_time)
                self.cleanup_observation()
                self.finish('boss_removed')
            return
        elapsed = now - self.started
        if (OUT/'stop_requested').is_file():
            self.finish('operator_stop')
            return
        if now >= self.policy_read_at:
            self.policy_read_at=now+1
            policy_file=OUT.parent/'input_policy.json'
            if policy_file.is_file():
                policy=json.loads(policy_file.read_text(encoding='utf-8-sig'))
                if policy != self.input_policy:
                    self.input_policy=policy
                    log('INPUT_POLICY', **policy, seconds=elapsed)
        self.key('LeftMouseButton', False)
        if not ue.SystemLibrary.is_valid(self.encounter.get_boss_avatar()):
            log('BOSS_REMOVED', death_finished=self.death_finished, seconds=elapsed)
            for name in list(self.pressed):
                self.key(name, False)
            self.removed_game_time = ue.GameplayStatics.get_time_seconds(self.world)
            self.state, self.cleanup_at = 'cleanup', self.removed_game_time + 5.0
            return
        if self.player_health.get_health() <= 0:
            self.finish('player_dead')
            return
        if now > self.deadline:
            self.finish('timeout')
            return
        location = self.boss.get_actor_location() - self.pawn.get_actor_location()
        distance = math.hypot(location.x, location.y)
        airborne = self.boss_move.get_editor_property('movement_mode') == ue.MovementMode.MOVE_FLYING
        if self.was_flying and not airborne:
            self.capture('flight_released')
            self.scheduled_images.append((now + .15, 'falling_hold'))
        if airborne and now - self.last_flight_image > 2:
            self.capture('flight')
            self.last_flight_image = now
        self.was_flying = airborne
        pitch = min(45, math.degrees(math.atan2(location.z, max(1, distance))) - 8)
        self.pc.set_control_rotation(ue.Rotator(pitch=pitch, yaw=math.degrees(math.atan2(location.y, location.x)), roll=0))
        if self.camera:
            center = self.boss.get_actor_location() + ue.Vector(0, 0, 30)
            # 保持观察相机与控制朝向一致，避免改变玩家输入消费的相机平面方向。
            toward_boss = ue.Vector(location.x / max(1, distance), location.y / max(1, distance), 0)
            camera_location = center - toward_boss * 1100 + ue.Vector(0, 0, 900)
            self.camera.set_actor_location_and_rotation(camera_location,
                ue.MathLibrary.find_look_at_rotation(camera_location, center), False, True)
        # 诊断操作员依据原招式窗口观察收招；所有移动/攻击仍经原玩家输入。
        montage = self.boss_anim.get_current_active_montage()
        montage_name = montage.get_name() if montage else ''
        position = self.boss_anim.montage_get_position(montage) if montage else 0
        ready = self.chase_complete
        player_montage = self.pawn.get_editor_property('mesh').get_anim_instance().get_current_active_montage()
        combo_running = player_montage is not None and 'Normal_' in player_montage.get_name()
        safe = montage is None or 'DashF' in montage_name or 'LandingRecovery' in montage_name or position > RECOVERY.get(montage_name, 1000)+.05
        retreat = not safe or airborne
        attack_intent = ready and not airborne and abs(location.z)<250 and (combo_running and distance<900 or safe and distance<420)
        if attack_intent:
            # QualifiedInput 对非零 Held 轴按当前 ControlYaw 投影；零轴保持角色朝向。
            # 通过正常 W 输入斜向经过目标，避免原攻击曲线持续顶住双方胶囊。
            clearance = float(self.input_policy['clearance'])
            angle = float(self.input_policy['sign'])*math.degrees(math.asin(min(1.0,clearance/max(distance,clearance))))
            self.pc.set_control_rotation(ue.Rotator(pitch=pitch, yaw=math.degrees(math.atan2(location.y,location.x))+angle, roll=0))
        self.key('S', ready and retreat and not attack_intent and distance < (1100 if airborne else 650))
        self.key('D', ready and retreat and not attack_intent)
        self.key('W', attack_intent or ready and not retreat and not combo_running and distance>300)
        if attack_intent and now-self.last_attack >= .22:
            self.key('LeftMouseButton',True)
            self.last_attack=now
        if now - self.last_sample < .1:
            return
        self.last_sample = now
        self.observe_presentation(now)
        for due, label in list(self.scheduled_images):
            if now >= due:
                self.capture(label)
                self.scheduled_images.remove((due, label))
        phase = self.boss_state.get_current_phase_tag().export_text()
        if phase != self.phase:
            self.phase = phase
            log('PHASE', phase=phase, health=self.health.get_health(), seconds=elapsed)
            self.capture('phase')
        active = []
        for handle in self.asc.get_all_abilities():
            ability, instance = ue.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(self.asc, handle)
            if instance and ue.AbilitySystemLibrary.is_gameplay_ability_active(ability):
                name = ability.get_class().get_name()
                active.append(name)
                if name not in self.observed:
                    self.observed.add(name)
                    log('ACTION', ability=name, seconds=elapsed)
                    self.capture(name)
                    self.scheduled_images.extend([(now + .35, name + '_035'), (now + 1.1, name + '_110')])
        montage = self.boss_anim.get_current_active_montage()
        dash = 'BP_GA_Kevin_DashF_KVB_C' in active
        position = self.boss.get_actor_location()
        if dash and not self.last_dash:
            self.dash_start = (elapsed, position, self.health.get_health(), self.player_health.get_health())
            self.dash_count += 1
            log('DASH_BEGIN', number=self.dash_count, seconds=elapsed, distance=distance,
                boss_location=[position.x, position.y, position.z], player_stationary=not self.chase_complete)
        if not dash and self.last_dash:
            start_time, start_position, boss_health, player_health = self.dash_start
            delta = position - start_position
            player_delta = self.pawn.get_actor_location() - self.player_start
            log('DASH_END', number=self.dash_count, seconds=elapsed, duration=elapsed-start_time,
                displacement=[delta.x, delta.y, delta.z], distance=distance,
                boss_health_delta=self.health.get_health()-boss_health,
                player_health_delta=self.player_health.get_health()-player_health,
                player_displacement=[player_delta.x, player_delta.y, player_delta.z])
            if self.dash_count >= 2: self.chase_complete = True
        self.last_dash = dash
        log('SAMPLE', seconds=round(elapsed, 3), health=self.health.get_health(),
            player_health=self.player_health.get_health(), distance=round(distance, 2),
            phase=phase, abilities=active, game_time=ue.GameplayStatics.get_time_seconds(self.world), movement=str(self.boss_move.get_editor_property('movement_mode')),
            action_motion=self.boss_move.has_active_action_motion(),
            boss_yaw=self.boss.get_actor_rotation().yaw, player_montage=player_montage.get_name() if player_montage else None, player_location=[self.pawn.get_actor_location().x,self.pawn.get_actor_location().y,self.pawn.get_actor_location().z],
            control_yaw=self.encounter.get_boss_controller().get_control_rotation().yaw,
            montage=montage.get_name() if montage else None,
            boss_location=[self.boss.get_actor_location().x, self.boss.get_actor_location().y, self.boss.get_actor_location().z])

    def finish(self, reason):
        for name in list(self.pressed):
            try:
                self.key(name, False)
            except RuntimeError as error:
                log('RELEASE_REJECTED', key=name, diagnostic=str(error))
                self.pressed.discard(name)
        if self.recording:
            ue.AudioMixerLibrary.stop_recording_output(self.world, ue.AudioRecordingExportType.WAV_FILE,
                                                       'battle_audio', str(OUT), None)
            self.recording = False
        self.detach()
        log('FINISH', reason=reason, observed=sorted(self.observed))
        self.state, self.deadline = 'ending', time.monotonic() + 15

    def tick(self, _dt):
        if self.advancing:
            return
        self.advancing = True
        try:
            self.run()
        except Exception:
            ue.log_error('KEVIN_BATTLE_FAILURE ' + traceback.format_exc())
            self.finish('error')
        finally:
            self.advancing = False


if __name__ == '__main__':
    battle = Battle()
