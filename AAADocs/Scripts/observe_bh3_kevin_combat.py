"""@file observe_bh3_kevin_combat.py
@brief 权威 PIE 的有限战斗／Standby 事实观察；导入时不执行 UE 操作。

已有权威 PIE 中显式调用：
    observer = start(source_avatar, target_avatar, label='Ice01_contact', seconds=8)
    observer = start_standby(encounter, support_component, seconds=8)
    observer.mark('cancel_requested')
    report = observer.stop()  # 超时也清理；重复 stop 返回同一报告

只观察，不生成 Actor、不激活能力、不改位姿／gravity、不写地图或资产。
报告写入 Saved/Codex；report_path 为实际写入路径，写入失败时为 None。
采样和报告存在不代表玩法 PASS；Standby 可见结果仍须运行原图。
"""
import json
import math
from pathlib import Path
import re
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
_active = None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class _PIEObserver:
    """两个观察入口共享的有限 Slate 监听及本次资源清理。"""

    def __init__(self, label, seconds, mode):
        import unreal
        self.ue = unreal
        require(math.isfinite(seconds) and 0 < seconds <= 60, '观察时长必须为 (0, 60] 秒')
        self.world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        require(self.world, '需要活动 PIE 世界')
        self.mode = mode
        self.label = re.sub(r'[^A-Za-z0-9_-]', '_', label)[:80] or 'observation'
        self.started_wall_time = time.monotonic()
        self.deadline = self.started_wall_time + seconds
        self.started_game_time = unreal.GameplayStatics.get_time_seconds(self.world)
        self.metadata = {'world': self.world.get_path_name(), 'source': None, 'target': None,
                         'requested_wall_seconds': float(seconds)}
        self.limitations = ['Slate 采样可能漏过短暂窗口，未采到的事实保留 Unknown。',
                            '不自动判 PASS，不证明联机、原作 hitbox 或实际可见结果。']
        self.samples, self.events, self.errors = [], [], []
        self.bindings = []
        self.tick_handle = None
        self.stopped = False
        self.initial = None
        self.report = None
        self.output = None

    def validate_world_actors(self, *actors):
        require(all(self.ue.SystemLibrary.is_valid(actor) for actor in actors), '观察 Actor 已失效')
        current = self.ue.GameplayStatics.get_all_actors_of_class(self.world, self.ue.Actor)
        require(all(actor in current for actor in actors), '不能观察编辑器世界或其他 PIE 实例的 Actor')

    @staticmethod
    def number(value):
        result = float(value)
        require(math.isfinite(result), '原生观察值非有限数')
        return result

    @staticmethod
    def vector(value):
        return [_PIEObserver.number(value.x), _PIEObserver.number(value.y), _PIEObserver.number(value.z)]

    @staticmethod
    def path(value):
        return value.get_path_name() if value else None

    @staticmethod
    def transform(value):
        return {'translation_cm': _PIEObserver.vector(value.translation),
                'rotation_xyzw': [_PIEObserver.number(getattr(value.rotation, axis)) for axis in 'xyzw'],
                'scale': _PIEObserver.vector(value.scale3d)}

    def clock_sample(self):
        return {'game_seconds': self.number(self.ue.GameplayStatics.get_time_seconds(self.world)
                                           - self.started_game_time),
                'wall_seconds': self.number(time.monotonic() - self.started_wall_time)}

    def bind_listeners(self):
        pass

    def mark(self, name):
        require(not self.stopped, '观察已经停止')
        self.events.append({'kind': 'marker', 'name': str(name), **self.snapshot()})

    def begin(self):
        try:
            self.initial = self.snapshot()
            self.bind_listeners()
            self.tick_handle = self.ue.register_slate_post_tick_callback(self.tick)
            self.events.append({'kind': 'marker', 'name': 'observation_started', **self.initial})
        except Exception as exc:
            self.errors.append(str(exc))
            self.stop('setup_error')
            raise
        return self

    def tick(self, delta_seconds):
        if self.stopped:
            return
        try:
            world = self.ue.get_editor_subsystem(self.ue.UnrealEditorSubsystem).get_game_world()
            if world != self.world:
                self.stop('PIE_world_changed')
                return
            self.samples.append(self.snapshot())
            if time.monotonic() >= self.deadline:
                self.stop('observation_timeout')
        except Exception as exc:
            self.errors.append(str(exc))
            self.stop('sampling_error')

    def listeners_pending(self):
        return self.tick_handle is not None or bool(self.bindings)

    def cleanup_listeners(self):
        # 清理失败保留原 handle／delegate，以便调用者对本次资源重试 stop。
        if self.tick_handle is not None:
            try:
                self.ue.unregister_slate_post_tick_callback(self.tick_handle)
                self.tick_handle = None
            except Exception as exc:
                self.errors.append('tick_cleanup: ' + str(exc))
        remaining = []
        for delegate, callback in self.bindings:
            try:
                delegate.remove_callable(callback)
            except Exception as exc:
                self.errors.append('delegate_cleanup: ' + str(exc))
                remaining.append((delegate, callback))
        self.bindings = remaining

    def release_objects(self):
        self.world = None

    def stop(self, reason='manual_stop'):
        """解除本次监听并返回缓存报告；report_path 只在真实写入后发布。"""
        if self.stopped and not self.listeners_pending() and self.report.get('report_path'):
            return self.report
        self.stopped = True
        self.cleanup_listeners()
        if self.report is None:
            self.report = {'mode': self.mode, 'label': self.label, 'stop_reason': str(reason),
                           **self.metadata, 'initial': self.initial, 'events': self.events,
                           'samples': self.samples, 'errors': self.errors, 'limitations': self.limitations,
                           'report_path': None}
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
            prefix = 'kevin_standby_observe_' if self.mode == 'standby_grounding' else 'kevin_combat_observe_'
            self.output = ROOT / 'Saved/Codex' / (prefix + self.label + '_' + stamp + '.json')
        self.report['listeners_released'] = not self.listeners_pending()
        self.report['status'] = 'observer_error' if self.errors else 'observed_requires_review'
        self.report['report_path'] = str(self.output)
        try:
            self.output.parent.mkdir(parents=True, exist_ok=True)
            self.output.write_text(json.dumps(self.report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
        except Exception as exc:
            self.errors.append('report_write: ' + str(exc))
            self.report['status'] = 'observer_error'
            self.report['report_path'] = None
            self.ue.log_error('KEVIN_OBSERVATION report_write: ' + str(exc))
        finally:
            self.release_objects()
        if self.report['report_path']:
            self.ue.log('KEVIN_OBSERVATION ' + self.report['report_path'])
        return self.report


class CombatObserver(_PIEObserver):
    def __init__(self, source, target, label, seconds):
        super().__init__(label, seconds, 'combat')
        require(source and target and source != target, '需要两个不同的 PIE Avatar')
        self.validate_world_actors(source, target)
        require(source.has_authority(), '在服务器实例观察权威判定')
        self.source, self.target = source, target
        self.metadata.update(source=self.path(source), target=self.path(target))
        self.mesh = source.get_editor_property('Mesh')
        self.trace = source.get_component_by_class(self.ue.GGYGOMeleeTraceComponent)
        self.movement = source.get_component_by_class(self.ue.GGYGOCharacterMovementComponent)
        self.health = target.get_component_by_class(self.ue.GGYGOHealthComponent)
        require(self.mesh and self.trace and self.movement and self.health, '缺少被测组件')
        require(self.health.get_health() > 0, '目标必须存活且完成 ASC/Health 初始化')
        self.limitations.append('MeleeTrace 命中只发给原窗口的原生订阅，Python 不观察命中；trace_open 只读 is_tracing，不证明命中、去重或 GE 身份。')

    def snapshot(self):
        anim = self.mesh.get_anim_instance()
        montage = anim.get_current_active_montage() if anim else None
        return {
            **self.clock_sample(),
            'montage': montage.get_path_name() if montage else None,
            'montage_seconds': float(anim.montage_get_position(montage)) if montage else None,
            'trace_open': bool(self.trace.is_tracing()),
            'action_motion_active': bool(self.movement.has_active_action_motion()),
            'source_location_cm': self.vector(self.source.get_actor_location()),
            'target_location_cm': self.vector(self.target.get_actor_location()),
            'target_health': float(self.health.get_health()),
            'mesh_tick_option': str(self.mesh.get_editor_property('VisibilityBasedAnimTickOption')),
            'mesh_uro': bool(self.mesh.get_editor_property('bEnableUpdateRateOptimizations')),
        }

    def on_health(self, component, old_value, new_value, instigator):
        if self.stopped:
            return
        self.events.append({'kind': 'health_changed', 'old': float(old_value), 'new': float(new_value),
            'instigator': instigator.get_path_name() if instigator else None, **self.snapshot()})

    def bind_listeners(self):
        for component, name, callback in [(self.health, 'OnHealthChanged', self.on_health)]:
            delegate = component.get_editor_property(name)
            delegate.add_callable(callback)
            self.bindings.append((delegate, callback))

    def release_objects(self):
        super().release_objects()
        self.source = self.target = self.mesh = self.trace = self.movement = self.health = None


class StandbyObserver(_PIEObserver):
    BODY_ANCHORS = ('Bip001-Pelvis', 'Bip001-Head', 'Bip001-HeadNub',
                    'Bip001-L-Foot', 'Bip001-R-Foot', 'Bip001-L-Toe0', 'Bip001-R-Toe0')

    def __init__(self, encounter, support, label, seconds):
        super().__init__(label, seconds, 'standby_grounding')
        require(isinstance(encounter, self.ue.GGYGOBossEncounter), '需要真实 GGYGOBossEncounter UObject')
        require(isinstance(support, self.ue.StaticMeshComponent), '需要真实支持 StaticMeshComponent UObject')
        require(self.ue.SystemLibrary.is_valid(support), '支持组件已失效')
        self.validate_world_actors(encounter, support.get_owner())
        require(encounter.has_authority(), 'Standby 只观察 Authority PIE Encounter')
        require(support.get_editor_property('StaticMesh'), '支持组件缺少实际 StaticMesh')
        self.encounter, self.support = encounter, support
        self.source = self.state = self.controller = None
        self.metadata.update(encounter=self.path(encounter), support_actor=self.path(support.get_owner()),
                             support_component=self.path(support),
                             support_mesh=self.path(support.get_editor_property('StaticMesh')),
                             support_transform_at_start=self.transform(support.get_world_transform()),
                             support_attach_parent=self.path(support.get_attach_parent()),
                             encounter_transform_at_start=self.transform(encounter.get_actor_transform()),
                             spawn_return_transform=None, first_avatar_observation=None, visual_verified=None)
        self.limitations.extend([
            '首个 Slate 位姿差包含此前物理推进，不能标为 FinishSpawning 返回瞬间调整。',
            'CurrentFloor 只在 Walking 时读取；未观察到 Falling→Walking 不宣称观察了落地转换。',
            '净空探测使用实际胶囊 profile；实例 response overrides 须结合 body_native_text 审核。',
            '骨点／AnimInstance 数据不证明可见 StandBy 或实际播放的 Sequence；需要同次 PIE 原图。'])

    def hit_sample(self, hit, movement):
        if hit is None:
            return None
        require(isinstance(hit, self.ue.HitResult), '原生查询应返回 HitResult 或 None')
        fields = hit.to_tuple()
        require(len(fields) == 18, '原生 BreakHitResult 签名发生变化')
        raw = hit.export_text()
        depths = re.findall(r'(?:^|[,\(])PenetrationDepth=([^,\)]+)', raw)
        require(len(depths) == 1, '原生 PenetrationDepth 不可读')
        return {'blocking_hit': bool(fields[0]), 'initial_penetration': bool(fields[1]),
                'penetration_depth_cm': self.number(depths[0]), 'distance_cm': self.number(fields[3]),
                'location_cm': self.vector(fields[4]), 'impact_cm': self.vector(fields[5]),
                'normal': self.vector(fields[6]), 'impact_normal': self.vector(fields[7]),
                'actor': self.path(fields[9]), 'component': self.path(fields[10]),
                'is_expected_support': fields[9] == self.support.get_owner() and fields[10] == self.support,
                'native_cmc_is_walkable': bool(movement.is_walkable(hit)), 'native_hit_text': raw}

    def snapshot(self):
        require(self.ue.SystemLibrary.is_valid(self.encounter)
                and self.ue.SystemLibrary.is_valid(self.support), '原 Encounter／支持组件已退役')
        source = self.encounter.get_boss_avatar()
        state = self.encounter.get_boss_state()
        controller = self.encounter.get_boss_controller()
        require(all(self.ue.SystemLibrary.is_valid(actor) for actor in (source, state, controller)
                    if actor is not None), '原 Encounter 发布的装配对象已失效')
        row = {**self.clock_sample(), 'source': self.path(source), 'state': self.path(state),
               'controller': self.path(controller), 'ready_asc': None, 'phase': 'waiting_assembly'}
        if self.source is not None:
            require((source, state, controller) == (self.source, self.state, self.controller),
                    '原 Encounter 装配已退役或改变，不能续借新的 Avatar')
        if not (source and state and controller):
            return row
        if self.source is None:
            self.validate_world_actors(source, state, controller)
            require(source.has_authority(), '实际 Boss Avatar 不具 Authority')
            self.source, self.state, self.controller = source, state, controller
            self.metadata['source'] = self.path(source)
            self.metadata['first_avatar_observation'] = {**row,
                'actor_age_game_seconds': self.number(source.get_game_time_since_creation()),
                'transform': self.transform(source.get_actor_transform())}
        require(state.get_avatar_pawn() == source and controller.get_controlled_pawn() == source
                and source.get_controller() == controller, '原 State／Controller／Avatar 拓扑不一致')
        definition = state.get_boss_definition()
        require(definition == self.encounter.get_editor_property('BossDefinition'), '实际 BossDefinition 不一致')
        pawn_data = state.get_initial_pawn_data()
        require(pawn_data and source.get_class() == pawn_data.get_editor_property('PawnClass'), '实际 PawnData／PawnClass 不一致')
        extension = source.get_component_by_class(self.ue.GGYGOPawnExtensionComponent)
        require(extension, '实际 Avatar 缺少 PawnExtension')
        asc = extension.get_ggygo_ability_system_component()
        if asc:
            require(asc == state.get_ggygo_ability_system_component(), '当前 Ready ASC 与原 State ASC 不一致')
        row.update(definition=self.path(definition), pawn_data=self.path(pawn_data),
                   pawn_class=self.path(source.get_class()), ready_asc=self.path(asc),
                   phase='ready' if asc else 'waiting_ready',
                   actor_age_game_seconds=self.number(source.get_game_time_since_creation()),
                   source_transform=self.transform(source.get_actor_transform()),
                   encounter_transform=self.transform(self.encounter.get_actor_transform()))
        first = self.metadata['encounter_transform_at_start']['translation_cm']
        row['location_delta_from_encounter_at_start_cm'] = [a - b for a, b in zip(row['source_transform']['translation_cm'], first)]
        capsule = source.get_editor_property('CapsuleComponent')
        movement = source.get_editor_property('CharacterMovement')
        mesh = source.get_editor_property('Mesh')
        require(capsule and movement and mesh, '实际 Avatar 缺少 Capsule／CMC／Mesh')
        radius = self.number(capsule.get_scaled_capsule_radius())
        half_height = self.number(capsule.get_scaled_capsule_half_height())
        require(0 < radius <= half_height, '实际 scaled capsule 尺寸无效')
        center, up = self.vector(capsule.get_world_location()), self.vector(capsule.get_up_vector())
        gravity = self.vector(movement.get_gravity_direction())
        gravity_scale = self.number(movement.get_editor_property('GravityScale'))
        gravity_z = self.number(movement.get_gravity_z())
        mode = movement.get_editor_property('MovementMode')
        complex_move = bool(capsule.get_editor_property('bTraceComplexOnMove'))
        profile = str(capsule.get_collision_profile_name())
        normal_gravity = abs(gravity_scale - 1.0) <= 1e-4 and gravity_z < 0 and all(
            abs(a - b) <= 1e-4 for a, b in zip(gravity, (0, 0, -1)))
        upright = all(abs(a - b) <= 1e-4 for a, b in zip(up, (0, 0, 1)))
        row.update(gravity_scale=gravity_scale, gravity_direction=gravity, gravity_z_cm_s2=gravity_z,
                   normal_gravity_observed=normal_gravity, movement_mode=str(mode),
                   moving_on_ground=bool(movement.is_moving_on_ground()),
                   velocity_cm_s=self.vector(movement.get_editor_property('Velocity')),
                   action_motion_active=bool(movement.has_active_action_motion()),
                   capsule={'radius_cm': radius, 'half_height_cm': half_height, 'center_cm': center,
                            'bottom_cm': [a - b * half_height for a, b in zip(center, up)],
                            'up': up, 'profile': profile, 'collision_enabled': str(capsule.get_collision_enabled()),
                            'trace_complex_on_move': complex_move,
                            'body_native_text': capsule.get_editor_property('BodyInstance').export_text()},
                   current_floor=None, current_floor_validity='not_walking', clearance_probe=None)
        if mode == self.ue.MovementMode.MOVE_WALKING:
            floor = movement.get_editor_property('CurrentFloor')
            blocking = bool(floor.get_editor_property('bBlockingHit'))
            line = bool(floor.get_editor_property('bLineTrace'))
            row['current_floor_validity'] = 'walking'
            row['current_floor'] = {'blocking_hit': blocking,
                'walkable_floor': bool(floor.get_editor_property('bWalkableFloor')), 'line_trace': line,
                'distance_cm': self.number(floor.get_editor_property('LineDist' if line else 'FloorDist')),
                'hit': self.hit_sample(floor.get_editor_property('HitResult'), movement) if blocking else None}
        # Kismet 胶囊 sweep 为世界 Z 轴；只对当前明确的普通 gravity／upright 契约执行。
        if normal_gravity and upright and not complex_move:
            step = self.number(movement.get_editor_property('MaxStepHeight'))
            require(step >= 0 and profile not in ('', 'None'), '实际净空 query 配置无效')
            end = [center[0], center[1], center[2] - half_height - step]
            hit = self.ue.SystemLibrary.capsule_trace_single_by_profile(
                self.world, self.ue.Vector(*center), self.ue.Vector(*end), radius, half_height,
                profile, False, [source], self.ue.DrawDebugTrace.NONE, False)
            row['clearance_probe'] = {'profile': profile, 'complex': False, 'ignored_actor': self.path(source),
                                     'start_cm': center, 'end_cm': end, 'hit': self.hit_sample(hit, movement)}
        else:
            row['clearance_probe'] = {'hit': None, 'not_sampled_reason': '需要普通 gravity、upright capsule 和 simple move'}
        anim = mesh.get_anim_instance()
        montage = anim.get_current_active_montage() if anim else None
        row.update(mesh=self.path(mesh.get_skeletal_mesh_asset()), anim_instance_class=self.path(anim.get_class()) if anim else None,
                   montage=self.path(montage), montage_seconds=self.number(anim.montage_get_position(montage)) if montage else None,
                   mesh_tick_option=str(mesh.get_editor_property('VisibilityBasedAnimTickOption')),
                   mesh_uro=bool(mesh.get_editor_property('bEnableUpdateRateOptimizations')), body_anchors_world_cm=None)
        if anim:
            for name in self.BODY_ANCHORS:
                require(mesh.get_bone_index(name) >= 0, '实际 Mesh 缺少精确骨点：' + name)
            row['body_anchors_world_cm'] = {name: self.vector(mesh.get_socket_transform(
                name, self.ue.RelativeTransformSpace.RTS_WORLD).translation) for name in self.BODY_ANCHORS}
        return row

    def release_objects(self):
        super().release_objects()
        self.encounter = self.support = self.source = self.state = self.controller = None


def start(source_avatar, target_avatar, label='combat', seconds=8.0):
    global _active
    if _active and (not _active.stopped or _active.listeners_pending()):
        raise RuntimeError('上一次观察仍在运行；先调用 stop()')
    _active = CombatObserver(source_avatar, target_avatar, label, seconds)
    return _active.begin()


def start_standby(encounter, expected_support_component, label='P3_StandBy', seconds=8.0):
    """@param encounter 当前 Authority PIE 的原生 Encounter，不执行 SpawnBoss。
    @param expected_support_component 同一 PIE 世界的实际支持 StaticMeshComponent UObject。
    @param seconds 从入口起计的有限 wall deadline；真实游戏推进另记 game_seconds。
    @return Observer；调用者在 PIE 结束前 stop()，保存报告并释放本次监听。
    Ready 尚未真实就绪时继续有限观察；超时／Unknown 不代替成功。
    """
    global _active
    if _active and (not _active.stopped or _active.listeners_pending()):
        raise RuntimeError('上一次观察仍在运行；先调用 stop()')
    _active = StandbyObserver(encounter, expected_support_component, label, seconds)
    return _active.begin()
