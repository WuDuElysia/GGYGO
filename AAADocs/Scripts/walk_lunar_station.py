"""真实单人 PIE 走关。只向生产输入装配发按键，转向使用控制器；不移动 Actor 或调用机关。"""
import json
import math
import os
from pathlib import Path
import time
import traceback
import subprocess
import unreal as ue

OUT = Path(os.environ["GGYGO_STATION_OUTPUT"])
ROUTE = os.environ["GGYGO_STATION_ROUTE"]
MAP = "/Game/Map/LunarStation/L_LunarStation"
TARGET = "L_KevinBoss_P3"
PYRIOS = "/Game/BP/Character/Player/BP_PC_Pyrios.BP_PC_Pyrios_C"


class ViewportMovie:
    def __init__(self, encoder):
        self.frame = OUT / "录像当前帧.png"
        self.ticket = None
        self.next_capture = 0
        self.frames = 0
        self.stream = subprocess.Popen([encoder,"-loglevel","error","-nostdin","-n",
            "-use_wallclock_as_timestamps","1","-f","image2pipe","-c:v","png","-i","pipe:0",
            "-vf","fps=6,scale=1280:-2","-c:v","mpeg4","-q:v","3","-pix_fmt","yuv420p",
            str(OUT / (ROUTE+".mp4"))], stdin=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)

    def tick(self, world, now, capture):
        if self.ticket:
            result = self.ticket.read_result()
            if result.status == ue.GGYGOViewportReadbackStatus.COMPLETE:
                assert result.file_write_complete and result.file_readback_verified
                self.stream.stdin.write(self.frame.read_bytes())
                self.stream.stdin.flush()
                self.frames += 1
                self.ticket.release()
                self.ticket = None
                self.frame.unlink()
            elif result.status in (ue.GGYGOViewportReadbackStatus.FAILED,ue.GGYGOViewportReadbackStatus.CANCELLED):
                raise RuntimeError("录像取帧失败 " + str(result.error))
        if capture and not self.ticket and now >= self.next_capture:
            self.ticket = ue.GGYGOViewportReadbackLibrary.begin_game_viewport_readback_to_file(world,str(self.frame),0)
            assert self.ticket
            self.next_capture = now + 1/6

    def close(self):
        if self.ticket:
            self.ticket.release()
            self.ticket = None
        try:
            self.stream.stdin.close()
        finally:
            try:
                code = self.stream.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.stream.kill()
                self.stream.wait()
                raise
            finally:
                self.frame.unlink(missing_ok=True)
        if code or not self.frames:
            raise RuntimeError("录像编码失败，退出码 " + str(code))


class Walk:
    def __init__(self):
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.stage = "boot"
        self.entered = time.monotonic()
        self.start = self.entered
        self.world_name = None
        self.keys_down = set()
        self.keys = {}
        for name in ("W","D","LeftMouseButton"):
            key = ue.Key()
            assert key.import_text(name)
            self.keys[name] = key
        self.trace = []
        self.pending = []
        self.hold = None
        self.index = 0
        self.route = [
            ("B",20,0,4),("K_out",33,0,4),("B_return",20,0,4),("W1",20,-28,4)]
        if ROUTE == "Upper":
            self.route += [("Q",19,-52,4),("O",57.4,-52,10),("V",57,-28,10)]
        self.route += [("W2",34.8,-28,6)]
        check_return = os.environ.get("GGYGO_STATION_CHECK_RETURN")=="1"
        if check_return:
            self.route += [("V_reverse",57,-28,10),("O_reverse",57.5,-52,10),("Q_reverse",19,-52,4),
                           ("W1_again",20,-28,4),("W2_again",34.8,-28,6),
                           ("W1_reverse",20,-28,4),("W2_final",34.8,-28,6)]
        self.route += [("I",36.5,0,4),("K_open",34.2,0,4),("B_shortcut",20,0,4),("I_shortcut",36.5,0,4),("H",66,0,8)]
        if check_return:
            self.route += [("T_turn",79.6,0,8),("H_back",66,0,8)]
        self.route += [("T_before",82,0,8),("T_cross",86,0,8)]
        self.last_log = 0
        self.attack_at = 0
        self.coasting = False
        self.movie = None
        self.health = None
        self.health_callback = self.on_boss_health
        self.player_hit = False
        self.handle = ue.register_slate_post_tick_callback(self.tick)

    def record(self, event, **fields):
        row = dict(event=event,seconds=round(time.monotonic()-self.start,2),**fields)
        self.trace.append(row)
        ue.log("LUNAR_WALK " + json.dumps(row, ensure_ascii=False))

    def state(self, stage):
        self.stage, self.entered = stage,time.monotonic()

    def assembly(self, world):
        pc = ue.GameplayStatics.get_player_controller(world,0)
        pawn = pc.get_controlled_pawn() if pc else None
        if not pawn:
            return None
        lib = ue.get_default_object(ue.load_class(None,"/Script/Engine.SubsystemBlueprintLibrary"))
        sub = lib.call_method("GetLocalPlayerSubSystemFromPlayerController",
                              args=(pc,ue.EnhancedInputLocalPlayerSubsystem.static_class()))
        if not sub:
            return None
        lp = sub.get_outer()
        status, controller, body, inputs, comp, user, device, error = ue.GGYGOPlayerInputBridgeLibrary.read_local_player_input_assembly(world,lp)
        if status != ue.GGYGOPlayerInputAssemblyStatus.READY:
            return None
        assert pc == controller and pawn == body and pawn.get_class().get_path_name() == PYRIOS
        return (world,lp,pc,pawn,inputs,comp,device)

    def key(self, ctx, name, down):
        if (name in self.keys_down) == down:
            return
        res = ue.GGYGOPlayerInputBridgeLibrary.submit_digital_key_event(*ctx,self.keys[name],down)
        assert res is not None and not res[-1], str(res)
        (self.keys_down.add if down else self.keys_down.remove)(name)

    def capture(self, world, name):
        path = OUT / (name+".png")
        ticket = ue.GGYGOViewportReadbackLibrary.begin_game_viewport_readback_to_file(world,str(path),0)
        assert ticket, name
        self.pending.append((name,ticket))

    def poll(self):
        for item in self.pending[:]:
            name,ticket = item
            r = ticket.read_result()
            if r.status == ue.GGYGOViewportReadbackStatus.COMPLETE:
                assert r.file_write_complete and r.file_readback_verified, name
                ticket.release()
                self.pending.remove(item)
                self.record("截图",file=name+".png")
            elif r.status in (ue.GGYGOViewportReadbackStatus.FAILED,ue.GGYGOViewportReadbackStatus.CANCELLED):
                raise RuntimeError(str(r.error))

    def look(self, ctx, yaw, pitch=-6):
        ctx[2].set_control_rotation(ue.Rotator(pitch=pitch,yaw=yaw,roll=0))

    def hold_view(self, ctx, label, yaw, pitch=-5):
        self.key(ctx,"W",False)
        self.look(ctx,yaw,pitch)
        self.hold = (ue.GameplayStatics.get_time_seconds(ctx[0])+1.4,label,yaw,pitch)

    def gate(self, world):
        cls=ue.load_class(None,"/Game/Map/LunarStation/BP_InsidePlate.BP_InsidePlate_C")
        plates=ue.GameplayStatics.get_all_actors_of_class(world,cls)
        assert len(plates)==1
        plate=plates[0]
        return plate.get_editor_property("GateLeaf").get_actor_location().y, plate.get_actor_enable_collision()

    def walk(self, ctx, now):
        world,lp,pc,pawn,*_ = ctx
        if self.hold:
            until,label,yaw,pitch = self.hold
            self.look(ctx,yaw,pitch)
            if ue.GameplayStatics.get_time_seconds(world) >= until:
                if label=="08_短廊折返":
                    position = pawn.get_actor_location()
                    assert 8000<position.x<8414,position
                    self.record("短廊内停步",x_cm=round(position.x))
                self.capture(world,label)
                self.hold = None
                self.entered = now
            return
        name,x,y,z = self.route[self.index]
        pos = pawn.get_actor_location()
        dx,dy=x*100-pos.x,y*100-pos.y
        distance = math.hypot(dx,dy)
        if now-self.last_log>3:
            ue.log("LUNAR_POSITION "+str((name,round(pos.x),round(pos.y),round(pos.z))))
            self.last_log=now
        if now-self.entered>45:
            raise RuntimeError("到达点位超时 "+str((name,pos,distance)))
        self.look(ctx,math.degrees(math.atan2(dy,dx)))
        if ROUTE=="Upper" and name=="T_cross" and not self.coasting and pos.x>=8290:
            self.coasting=True
            self.record("短廊松开 W，靠制动余量过门",x=round(pos.x))
        self.key(ctx,"W",not self.coasting)
        if name == "K_out":
            if pos.x > 3195:
                raise RuntimeError("从外侧穿透了闸门")
            if self.entered_gate is None and pos.x>3090:
                self.entered_gate = ue.GameplayStatics.get_time_seconds(world)
            if self.entered_gate is None or ue.GameplayStatics.get_time_seconds(world)-self.entered_gate < 1.5:
                return
            gate_y, enabled=self.gate(world)
            assert 3080<pos.x<3195 and abs(gate_y)<2 and enabled, (pos,gate_y,enabled)
            self.hold_view(ctx,"02_闸门外侧",0)
        elif distance>60:
            return
        # 以脚底验证实际标高，允许胶囊贴坡与拐角处的误差。
        feet=pos.z-pawn.get_component_by_class(ue.CapsuleComponent).get_scaled_capsule_half_height()
        assert abs(feet-z*100)<75, (name,feet,z)
        gate_y,enabled=self.gate(world)
        if name in ("B","W1","W2","O","I"):
            assert abs(gate_y)<2 and enabled,(name,gate_y,enabled)
        if name == "O":
            self.hold_view(ctx,"03_看台回望",85,-9)
        if name == "T_turn":
            self.hold_view(ctx,"08_短廊折返",180,-4)
        if name == "H_back":
            self.hold_view(ctx,"09_前庭回望南站",180,-3)
        if name in ("K_open","B_shortcut","I_shortcut","H","T_before"):
            assert abs(gate_y-480)<2 and not enabled,(name,gate_y,enabled)
        if name == "K_open":
            self.hold_view(ctx,"04_闸内回望",180,-4)
        if name == "H":
            self.hold_view(ctx,"05_双拱前庭",0,5)
        self.record("到达",point=name,xyz=[round(pos.x),round(pos.y),round(pos.z)],foot_cm=round(feet),
                    gate_y_cm=round(gate_y),plate_enabled=enabled)
        self.index+=1
        self.entered=now
        if self.index == len(self.route):
            raise RuntimeError("角色穿过了短廊却没有触发转图")

    def on_boss_health(self, component, old, new, instigator):
        if component == self.health and new < old and instigator == self.player_slot:
            self.player_hit = True
            self.record("玩家命中",before=old,after=new,instigator=instigator.get_path_name())

    def fight(self, ctx, now):
        world,lp,pc,pawn,*_=ctx
        encounters=ue.GameplayStatics.get_all_actors_of_class(world,ue.GGYGOBossEncounter)
        assert len(encounters)==1, str(encounters)
        boss=encounters[0].get_boss_avatar()
        if not boss:
            return
        cls=boss.get_class()
        assert cls.get_name()=="BP_Kevin_DemonBattle_C"
        assert len(ue.GameplayStatics.get_all_actors_of_class(world,cls))==1
        hp=ue.GGYGOHealthComponent.find_health_component(boss).get_health()
        p=pawn.get_actor_location()
        b=boss.get_actor_location()
        if self.stage=="arrive":
            self.record("P3 接手",pawn=pawn.get_class().get_name(),boss=cls.get_name(),
                        health=hp,playerspawn=[round(p.x),round(p.y),round(p.z)],boss_count=1)
            self.initial_hp=hp
            assert hp==1200
            self.health=ue.GGYGOHealthComponent.find_health_component(boss)
            self.player_slot=ue.AbilitySystemLibrary.get_ability_system_component(pawn).get_owner()
            assert self.player_slot and self.player_slot.get_class().get_name()=="GGYGOCharacterSlot"
            self.health.on_health_changed.add_callable(self.health_callback)
            self.p3_start=(p.x,p.y)
            self.released_at=ue.GameplayStatics.get_time_seconds(world)
            self.barrier_step=0
            ue.SystemLibrary.execute_console_command(world,"Editor.AsyncAssetCompilationFinishAll")
            self.state("fight")
            self.capture(world,"06_P3出生")
        elapsed=ue.GameplayStatics.get_time_seconds(world)-self.released_at
        if ROUTE=="Lower" and self.barrier_step<4:
            if elapsed>1.0 and self.barrier_step==0:
                self.key(ctx,"D",True)
                self.record("W 未释放，按 D")
                self.barrier_step=1
            elif elapsed>1.3 and self.barrier_step==1:
                self.key(ctx,"D",False)
                self.record("只释放 D")
                self.barrier_step=2
            elif elapsed>1.6 and self.barrier_step==2:
                self.key(ctx,"D",True)
                self.record("W 仍按住，再按 D")
                self.barrier_step=3
            elif elapsed>2.1 and self.barrier_step==3:
                self.key(ctx,"D",False)
                self.key(ctx,"W",False)
                self.record("真正释放过门前按住的 W")
                self.barrier_step=4
            return
        if elapsed<2.4:
            return
        delta=math.hypot(b.x-p.x,b.y-p.y)
        steer=math.degrees(math.atan2(b.y-p.y,b.x-p.x))
        if delta<420:
            steer-=math.degrees(math.asin(min(1,100/max(1,delta))))
        self.look(ctx,steer)
        self.key(ctx,"W",ROUTE!="Upper")
        self.key(ctx,"LeftMouseButton",False)
        if delta<400 and now>self.attack_at:
            self.key(ctx,"LeftMouseButton",True)
            self.attack_at=now+.24
        moved=math.hypot(p.x-self.p3_start[0],p.y-self.p3_start[1])
        if self.player_hit and hp<self.initial_hp and (ROUTE=="Upper" or moved>55):
            if ROUTE=="Upper":
                self.record("落点首次普攻已命中，期间无方向键",health=hp)
            self.key(ctx,"W",False)
            self.key(ctx,"LeftMouseButton",False)
            self.record("P3 交战",initial_hp=self.initial_hp,current_hp=hp,player_moved_cm=round(moved),boss_count=1)
            self.capture(world,"07_P3命中")
            self.state("done")

    def update(self):
        now=time.monotonic()
        if self.stage=="quit":
            if not self.editor.get_game_world():
                ue.unregister_slate_post_tick_callback(self.handle)
                ue.SystemLibrary.quit_editor()
            return
        if now-self.entered>150:
            raise RuntimeError("阶段超时 "+self.stage)
        self.poll()
        if self.stage=="boot":
            level="/Game/Map/BH3/"+TARGET if ROUTE=="P3Control" else MAP
            if self.editor.get_editor_world().get_outermost().get_name()!=level:
                assert self.levels.load_level(level)
            ue.SystemLibrary.execute_console_command(None,"Slate.bAllowThrottling 0")
            ue.SystemLibrary.execute_console_command(None,"t.MaxFPS 60")
            ue.SystemLibrary.execute_console_command(self.editor.get_editor_world(),"Editor.AsyncAssetCompilationFinishAll")
            self.levels.editor_request_begin_play()
            self.state("start")
            return
        if self.stage=="done":
            if self.movie:
                self.movie.tick(None,now,False)
            if not self.pending and (not self.movie or not self.movie.ticket):
                self.finish(True)
            return
        world=self.editor.get_game_world()
        if not world:
            return
        ctx=self.assembly(world)
        if not ctx:
            return
        if self.stage=="start":
            if ROUTE=="P3Control":
                assert TARGET in world.get_name()
                self.state("arrive")
                return
            assert "L_LunarStation" in world.get_name()
            if os.environ.get("GGYGO_STATION_FFMPEG"):
                self.movie = ViewportMovie(os.environ["GGYGO_STATION_FFMPEG"])
            ue.SystemLibrary.execute_console_command(world,"Editor.AsyncAssetCompilationFinishAll")
            self.record("独立出生",world=world.get_name(),pawn=ctx[3].get_class().get_name(),route=ROUTE)
            self.entered_gate=None
            self.state("walk")
            self.hold_view(ctx,"01_南站远望",0,2)
        if self.movie:
            # 临近实际 OpenLevel 的最后几步停止发起旧 World 的异步请求，目的地重新起拍。
            before_travel = self.stage=="walk" and self.route[self.index][0]=="T_cross"
            self.movie.tick(world,now,not before_travel)
        if self.stage=="walk" and TARGET in world.get_name():
            assert self.route[self.index][0]=="T_cross"
            assert ("W" in self.keys_down)==(ROUTE=="Lower")
            self.record("门槛切换",held=sorted(self.keys_down))
            self.state("arrive")
        if self.stage=="walk":
            self.walk(ctx,now)
        elif self.stage in ("arrive","fight"):
            self.fight(ctx,now)

    def finish(self, success):
        if self.movie:
            movie,self.movie = self.movie,None
            try:
                movie.close()
                self.record("视口录像",file=ROUTE+".mp4",captured_frames=movie.frames)
            except Exception:
                self.record("录像失败",detail=traceback.format_exc())
                success=False
        if self.health:
            self.health.on_health_changed.remove_callable(self.health_callback)
            self.health=None
        (OUT/"walk.json").write_text(json.dumps(dict(route=ROUTE,success=success,events=self.trace),
                                                ensure_ascii=False,indent=2),encoding="utf-8")
        self.state("quit")
        if self.editor.get_game_world():
            self.levels.editor_request_end_play()

    def tick(self, delta):
        try:
            self.update()
        except Exception:
            self.record("失败",detail=traceback.format_exc())
            self.finish(False)


station_walk=Walk()
