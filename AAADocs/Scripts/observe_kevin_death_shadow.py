"""@file observe_kevin_death_shadow.py
@brief 暂停 BT 后用已配置伤害 GE 触发原死亡链；比较死亡后正常 VSM 与无缓存画面。

仅验证死亡阴影，不代替完整普攻胜利。只输出必要截图，无录音，不保存生产资产。
"""
import sys
from pathlib import Path
import time
import unreal as ue
sys.path.insert(0,str(Path(__file__).resolve().parent))
from observe_kevin_battle import Battle, log
import wire_bh3_kevin_combat as wire

class ShadowBattle(Battle):
    def setup(self, world):
        if not super().setup(world): return False
        self.encounter.get_boss_controller().get_editor_property('brain_component').stop_logic('死亡阴影隔离诊断')
        log('DEATH_FIXTURE', trigger='GE_Damage_SetByCaller via ASC (isolated death only)', production_death_blueprint=True, direct_destroy=False, production_config_writes=False)
        self.death_trigger_at=ue.GameplayStatics.get_time_seconds(world)+2
        return True

    def key(self,name,down):
        # 复现死亡只施加已配置伤害 GE，不操作玩家，也不把本夹具计作完整交战证据。
        if down: return
        super().key(name,down)

    def capture(self, label):
        if label in ('start','cleanup','cleanup_uncached','death_finished') or 'Death' in label:
            super().capture(label)

    def on_death(self, actor):
        component=self.boss.get_editor_property('mesh')
        origin,extent,radius=ue.SystemLibrary.get_component_bounds(component)
        properties={key:str(component.get_editor_property(key)) for key in ('bounds_scale','component_use_fixed_skel_bounds','use_attach_parent_bound','shadow_cache_invalidation_behavior','physics_asset_override')}
        scratch=ue.DynamicMesh()
        options=ue.GeometryScriptCopyMeshFromComponentOptions()
        lod=ue.GeometryScriptMeshReadLOD()
        lod.set_editor_property('LODType',ue.GeometryScriptLODType.RENDER_DATA)
        lod.set_editor_property('LODIndex',0)
        options.set_editor_property('RequestedLOD',lod)
        copied,transform,outcome=ue.GeometryScript_SceneUtils.copy_mesh_from_component(component,scratch,options,False)
        if copied != scratch or outcome != ue.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('原生蒙皮表面读取失败')
        box=ue.GeometryScript_MeshQueries.get_mesh_bounding_box(scratch)
        corners=[transform.transform_location(ue.Vector(x,y,z)) for x in (box.min.x,box.max.x) for y in (box.min.y,box.max.y) for z in (box.min.z,box.max.z)]
        required=max(abs(getattr(v,axis)-getattr(origin,axis))/getattr(extent,axis) for v in corners for axis in ('x','y','z'))
        log('DEATH_BOUNDS',properties=properties,origin=origin.export_text(),extent=extent.export_text(),posed_local_box=box.export_text(),required_scale=required,physics_asset=str(component.get_skeletal_mesh_asset().get_editor_property('physics_asset')))
        scratch.reset()
        super().on_death(actor)

    def finish(self, reason):
        if reason == 'boss_removed' and not hasattr(self,'shadow_probe_done'):
            self.shadow_probe_done=True
            self.state='shadow_probe'
            self.probe_at=time.monotonic()+1
            return
        super().finish(reason)

    def run(self):
        if self.state == 'battle' and not hasattr(self,'death_triggered') and ue.GameplayStatics.get_time_seconds(self.world)>=self.death_trigger_at:
            self.death_triggered=True
            if not all(hasattr(self.asc,name) for name in ('make_outgoing_spec','make_effect_context','apply_gameplay_effect_spec_to_self')): raise RuntimeError('缺原 ASC 伤害入口')
            effect=ue.load_class(None,'/Game/GameplayEffects/Damage/GE_Damage_SetByCaller.GE_Damage_SetByCaller_C')
            spec=self.asc.make_outgoing_spec(effect,1.0,self.asc.make_effect_context())
            damage=ue.GameplayTag()
            if not damage.import_text('(TagName="SetByCaller.Damage")'): raise RuntimeError('伤害标签无效')
            spec=ue.AbilitySystemLibrary.assign_tag_set_by_caller_magnitude(spec,damage,self.health.get_max_health())
            self.asc.apply_gameplay_effect_spec_to_self(spec)
        if self.state == 'shadow_probe':
            self.poll_images()
            if time.monotonic() < self.probe_at or self.pending: return
            if not hasattr(self,'cache_disabled'):
                ue.SystemLibrary.execute_console_command(self.world,'r.Shadow.Virtual.Cache 0')
                log('SHADOW_PROBE',cache_disabled=True,purpose='仅在生产死亡及原清理读回后鉴别缓存残影，不保存')
                self.cache_disabled=True
                self.probe_at=time.monotonic()+1
                return
            self.capture('cleanup_uncached')
            super().finish('boss_removed')
            return
        super().run()

ue.log('KEVIN_BOUNDS_READBACK '+str(wire.configure_mesh_bounds(apply=False)))
battle=ShadowBattle(record_audio=False)
