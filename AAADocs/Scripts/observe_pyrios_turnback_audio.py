"""独立 PIE：通过生产 W/S 输入连续做两次转身，核对第一段 Foley 的播放与清理。"""
import json
import os
import time
import traceback
from pathlib import Path

import unreal as ue

OUT = Path(os.environ["GGYGO_TURNBACK_AUDIO_OUT"])
SOUND = "/Game/Characters/Player/Pyrios/Audio/TurnBack/SW_Pyrios_Foley_Pyrois_TurnBack.SW_Pyrios_Foley_Pyrois_TurnBack"


class Run:
    def __init__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.level = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.state, self.phase, self.in_tick = "starting", "run_up", False
        self.deadline = time.monotonic() + 120
        self.frames, self.events, self.sounds, self.images = [], [], {}, []
        self.keys_down, self.keys, self.pending = set(), {}, []
        self.turns, self.completed, self.ready = 0, 0, 0
        self.previous_phase = ue.GGYGOTurnBackPhase.NONE
        self.recording, self.error = False, None
        self.world = None
        self.handle = ue.register_slate_post_tick_callback(self.tick)
        (OUT / "pie_request_TurnBack.json").write_text("{}", encoding="utf-8")

    def key(self, name, pressed):
        result = ue.GGYGOPlayerInputBridgeLibrary.submit_digital_key_event(
            self.world, self.lp, self.pc, self.pawn, self.pinput, self.input_comp, self.device, self.keys[name], pressed)
        if result is None:
            raise RuntimeError("生产输入被拒绝 " + name)
        if pressed:
            self.keys_down.add(name)
        else:
            self.keys_down.discard(name)
        self.events.append({"frame": ue.SystemLibrary.get_frame_count(), "key": name, "pressed": pressed})

    def tick(self, _dt):
        if self.in_tick:
            return
        self.in_tick = True
        try:
            if self.state == "ending":
                if self.editor.get_game_world() is None:
                    self.quit()
                return
            if time.monotonic() > self.deadline:
                if self.state == "draining":
                    for item in self.pending:
                        item.update(status="timeout", verified=False)
                        item.pop("task").release()
                    self.pending.clear()
                else:
                    raise RuntimeError("转身观察超时 " + self.state + "/" + self.phase)
            if self.state == "starting":
                self.assemble()
            elif self.state == "running":
                self.observe()
            elif self.state == "draining":
                self.poll_images()
                if not self.pending:
                    self.level.editor_request_end_play()
                    self.state = "ending"
        except Exception:
            self.error = traceback.format_exc()
            ue.log_error(self.error)
            self.finish()
        finally:
            self.in_tick = False

    def assemble(self):
        world = self.editor.get_game_world()
        if world is None:
            return
        if not world.get_path_name().startswith("/Game/Map/UEDPIE_0_L_Movement_Test"):
            raise RuntimeError("不是 L_Movement_Test PIE")
        pc = ue.GameplayStatics.get_player_controller(world, 0)
        pawn = ue.GameplayStatics.get_player_pawn(world, 0)
        if not pc or not pawn:
            return
        if pawn.get_class().get_name() != "BP_PC_Pyrios_C":
            raise RuntimeError("不是生产 Pyrios")
        move = pawn.get_editor_property("character_movement")
        if move.get_movement_set() is None:
            return
        idle = move.is_moving_on_ground() and pawn.get_velocity().length_squared() < 1e-5
        self.ready = self.ready + 1 if idle else 0
        if self.ready < 45:
            return
        lib = ue.get_default_object(ue.load_class(None, "/Script/Engine.SubsystemBlueprintLibrary"))
        subsystem = lib.call_method("GetLocalPlayerSubSystemFromPlayerController",
                                   args=(pc, ue.EnhancedInputLocalPlayerSubsystem.static_class()))
        lp = subsystem.get_outer()
        status, _, _, pinput, comp, _, device, diagnostic = ue.GGYGOPlayerInputBridgeLibrary.read_local_player_input_assembly(world, lp)
        if status != ue.GGYGOPlayerInputAssemblyStatus.READY:
            raise RuntimeError("生产输入未就绪 " + str(diagnostic))
        mapping = ue.load_asset("/Game/Input/Mappings/IMC_Default")
        action = ue.load_asset("/Game/Input/Actions/IA_Move")
        for name in ("W", "S"):
            matches = [r.get_editor_property("key") for r in mapping.get_editor_property("default_key_mappings").get_editor_property("mappings")
                       if r.get_editor_property("action") == action and str(r.get_editor_property("key").get_editor_property("key_name")) == name]
            if len(matches) != 1 or pc.is_input_key_down(matches[0]):
                raise RuntimeError("生产移动键不唯一或已按下 " + name)
            self.keys[name] = matches[0]
        self.world, self.pc, self.pawn, self.move, self.lp = world, pc, pawn, move, lp
        self.pinput, self.input_comp, self.device = pinput, comp, device
        self.mesh = pawn.get_editor_property("mesh")
        sound = ue.load_asset(SOUND)
        self.sound_duration = float(sound.get_editor_property("duration"))
        if sound.get_editor_property("looping") or self.sound_duration <= 0:
            raise RuntimeError("转身声音必须是有明确时长的单次素材")
        self.wall_start = time.monotonic()
        ue.SystemLibrary.execute_console_command(world, "au.DisableAppVolume 1", pc)
        ue.SystemLibrary.execute_console_command(world, "t.MaxFPS 60", pc)
        ue.AudioMixerLibrary.start_recording_output(world, 60.0, None)
        self.recording = True
        self.deadline, self.state = time.monotonic() + 60, "running"
        self.key("W", True)

    def observe(self):
        frame = int(ue.SystemLibrary.get_frame_count())
        game_time = ue.SystemLibrary.get_game_time_in_seconds(self.world)
        phase = self.move.get_turn_back_phase()
        motion = self.move.get_locomotion_motion_type()
        current, live, playing, audio_state = [], [], [], []
        owned = {component.get_path_name() for component in self.pawn.get_components_by_class(ue.AudioComponent)
                 if component.get_editor_property("sound") and component.get_editor_property("sound").get_path_name() == SOUND}
        for component in ue.ObjectIterator(ue.AudioComponent):
            name = component.get_path_name()
            valid = ue.SystemLibrary.is_valid(component)
            if not valid:
                if name in self.sounds:
                    current.append(name)
                    audio_state.append({"path": name, "valid": False, "owned": name in owned})
                continue
            if component.get_world() != self.world:
                continue
            sound = component.get_editor_property("sound")
            if not sound or sound.get_path_name() != SOUND:
                continue
            current.append(name)
            live.append(name)
            is_playing = component.is_playing()
            if is_playing:
                playing.append(name)
            item = self.sounds.setdefault(name, {"first_frame": frame, "first_phase": str(phase),
                                                "first_game_time": game_time,
                                                "attached_mesh": component.get_attach_parent() == self.mesh,
                                                "playing_observed": False})
            item["last_frame"] = frame
            item["last_valid_game_time"] = game_time
            item["playing_observed"] |= is_playing
            if is_playing:
                item["last_playing_game_time"] = game_time
            audio_state.append({"path": name, "valid": True, "owned": name in owned, "playing": is_playing,
                                "attached_mesh": component.get_attach_parent() == self.mesh})
        if phase == ue.GGYGOTurnBackPhase.TURNING and self.previous_phase != phase:
            self.turns += 1
            self.events.append({"frame": frame, "game_time": game_time, "turn_start": self.turns})
            self.capture("turn_" + str(self.turns))
        self.previous_phase = phase
        self.frames.append({"frame": frame, "game_time": game_time, "wall_elapsed": time.monotonic() - self.wall_start,
                            "phase": str(phase), "motion": str(motion), "audio": current, "audio_state": audio_state,
                            "owned_audio": sorted(owned)})
        self.poll_images()
        if self.phase == "run_up":
            full_run = (self.move.get_resolved_gait() == ue.GGYGOGait.RUN and self.move.get_walk_run_blend_alpha() == 1.0
                        and motion == ue.GGYGOLocomotionMotionType.WALK_RUN)
            if full_run:
                self.run_frame = getattr(self, "run_frame", frame)
                if frame - self.run_frame >= 20:
                    self.key("S", True)
                    self.key("W", False)
                    self.phase = "first_turn"
        elif self.phase == "first_turn" and self.turns == 1 and motion == ue.GGYGOLocomotionMotionType.WALK_RUN:
            self.completed = 1
            self.key("W", True)
            self.key("S", False)
            self.phase = "second_turn"
        elif self.phase == "second_turn" and self.turns == 2 and motion == ue.GGYGOLocomotionMotionType.WALK_RUN:
            self.completed = 2
            self.key("W", False)
            self.end_time, self.phase = game_time, "tail"
        elif self.phase == "tail" and game_time - self.end_time > max(3.0, self.sound_duration + 0.5):
            # 保留枚举残留，另核原生有效性与 Actor 组件所有权；不强制 GC 或代替生产代码销毁。
            self.final_audio = {"game_time": game_time, "tail_game_seconds": game_time - self.end_time,
                                "enumerated": current, "valid": live, "playing": playing, "owned": sorted(owned)}
            self.finish()

    def capture(self, name):
        filename = OUT / (name + ".png")
        task = ue.GGYGOViewportReadbackLibrary.begin_game_viewport_readback_to_file(self.world, str(filename), 0)
        if not task:
            raise RuntimeError("游戏 viewport 截图请求失败")
        item = {"path": str(filename), "task": task}
        self.images.append(item)
        self.pending.append(item)

    def poll_images(self):
        for item in list(self.pending):
            result = item["task"].read_result()
            if result.status in (ue.GGYGOViewportReadbackStatus.COMPLETE, ue.GGYGOViewportReadbackStatus.FAILED,
                                  ue.GGYGOViewportReadbackStatus.CANCELLED):
                item.update(status=str(result.status), verified=result.file_write_complete and result.file_readback_verified)
                item.pop("task").release()
                self.pending.remove(item)

    def finish(self):
        for name in list(self.keys_down):
            self.key(name, False)
        if self.recording:
            ue.AudioMixerLibrary.stop_recording_output(self.world, ue.AudioRecordingExportType.WAV_FILE, "master", str(OUT), None)
            self.recording = False
        self.state, self.deadline = "draining", time.monotonic() + 15

    def quit(self):
        ue.unregister_slate_post_tick_callback(self.handle)
        starts = [e["frame"] for e in self.events if "turn_start" in e]
        first = [s["first_frame"] for s in self.sounds.values()]
        checks = {"two_turns_completed": self.turns == self.completed == 2,
                  "one_sound_per_turn": len(first) == 2 and sorted(first) == starts,
                  "playing_attached_to_mesh": bool(self.sounds) and all(s["attached_mesh"] and s["playing_observed"] for s in self.sounds.values()),
                  "audio_stopped": hasattr(self, "final_audio") and not self.final_audio["playing"],
                  "audio_released": hasattr(self, "final_audio") and not self.final_audio["valid"] and not self.final_audio["owned"],
                  "screenshots_written": len(self.images) == 2 and all(s.get("verified") for s in self.images)}
        report = {"error": self.error, "checks": checks, "passed": self.error is None and all(checks.values()),
                  "events": self.events, "sounds": self.sounds, "images": self.images,
                  "final_audio": getattr(self, "final_audio", None), "sound_duration": getattr(self, "sound_duration", None),
                  "dirty": [p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
        (OUT / "run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT / "frames.json").write_text(json.dumps(self.frames, ensure_ascii=False), encoding="utf-8")
        (OUT / "quit.flag").write_text("quit", encoding="utf-8")
        ue.log("[TurnBackAudio] " + str(checks))


ue._pyrios_turnback_audio_observation = Run()
