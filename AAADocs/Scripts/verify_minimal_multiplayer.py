"""@file verify_minimal_multiplayer.py @brief 重读双端值证据；截图可见性由人工看图确认。"""
import argparse
import json
import math
from pathlib import Path
from types import SimpleNamespace

import minimal_multiplayer_checks as check


def expected_native(rows):
    check.require(bool(rows), "缺自然 Finalize 记录")
    native = rows[0]["movement_action_native"]
    check.require(native["available"], "入场原 Native RMS 不可读")
    return {key: native[key] for key in ("world", "character", "movement", "local_role")}


def validate_run(data):
    check.require(data["error"] is None and not data["cleanup_errors"] and data["phase"] == "captured",
                  "观察未正常收集或归还：" + str(data.get("error")))
    if "editor_slate_throttling" in data:
        check.require(data["editor_slate_throttling"] == 0 and data["clocks"]
                      and all(clock["available"] and clock["slate_allows_expensive_tasks"]
                              for row in data["clocks"] for clock in row["worlds"].values()),
                      "本测试 Editor 仍被 Slate 阻止 PIE World Tick")
    for row in data["pose"]["records"]:
        network = row["network_driver_live"]
        check.require(network["available"] and network["net_test_enabled"] and network["named_driver_matches"], "NetDriver 读回不可用")
        check.require(network["driver_world"] == network["world"] and all(network[k] == 0 for k in
            ("incoming_loss_percent", "incoming_frame_delay", "incoming_buffer_bloat_ms")), "含延迟之外的网络模拟")
    for action in data["actions"]:
        state = action["state"]
        check.require(not state["evidence_incomplete"] and not state["active"] and state["subscriptions_released"], "动作观察未完整归还")
    fx = data["fx"]
    check.require(fx and not fx["evidence_incomplete"] and not fx["active"] and fx["subscriptions_released"], "FX 观察未完整归还")


def final_interval(records, source):
    """终态必须含实际 CMC 完成区间，不能从 Task 结束推断已消费根运动尾段。"""
    raw_sources = [raw for row in records for group in ("active_sources", "pending_sources")
                   for raw in row["movement_action_native"].get(group, [])
                   if raw.get("montage") == source["montage"] and not raw["native_imported"]]
    ends = {raw["binding_end_seconds"] for raw in raw_sources}
    check.require(len(ends) == 1, "缺唯一原 Montage RMS 末端")
    end = next(iter(ends))
    intervals = [row["movement_completed_interval"] for row in records
                 if row["movement_completed_interval"]["action_handle"] == source["cmc_motion_handle"]
                 and row["movement_completed_interval"]["source_kind"] == 2]
    terminal = [v for v in intervals if v["status"] == 1 and v["has_native_source_interval"]
                and v["native_source_finished"] and abs(v["motion_end_seconds"] - end) <= 0.00001]
    check.require(bool(terminal), "未采到原 RMS 真实末段消费")
    last = terminal[-1]
    check.require(last["native_delta_seconds"] > 0 and last["native_end_seconds"] > last["native_start_seconds"]
                  and last["motion_end_seconds"] > last["motion_start_seconds"] and last["source_intervals"],
                  "末段没有真实 Native 步长与源区间")
    check.require(last["curve_yaw_applied"] and math.isfinite(last["requested_yaw_delta_degrees"])
                  and all(math.isfinite(x) for key in ("actual_before", "actual_after")
                          for field in ("translation", "rotation") for x in last[key][field]), "末段 XYZ/Yaw 结果不可用")
    return last


def verify_attack(authority, observer, log):
    resources = {tuple(item["key"]): item["state"] for item in authority["actions"]}
    check.require(set(resources) == {("owner", 0, 0), ("authority", 0, 0)}, "attack-only 必须只有两端各一个原 Task/Montage")
    check.require(all(check.natural_exit(state) for state in resources.values()), "原 GA 非自然结束或缺原生完整历史")
    check.require([(event["action"], event["edge"]) for event in authority["input_events"]]
                  == [("Attack", "Press"), ("Attack", "Release")], "attack-only 混入移动或额外攻击")
    check.require(not log["errors"], "attack-only 存在 UE 错误")
    tasks = check.combo_task_evidence(authority["pose"]["records"], authority["arm"])
    check.require(tasks["seen"] and tasks["cleanup_verified"] and authority["owner_public"]["cleanup_verified"], "原任务或公开资源未归还")
    last = final_interval(authority["pose"]["records"], resources[("authority", 0, 0)]["original_source"])
    check.require(observer["pose"]["records"][-1]["movement_action_native"]["status"] == 2, "远端 RMS 未退役")
    return dict(natural_exit=True, final_interval=last, known_tasks=tasks)


def verify_correction(authority, observer, log):
    resources = {tuple(item["key"]): item["state"] for item in authority["actions"]}
    sources = check.facing_replay_sources(log["rows"], {key: state["original_source"] for key, state in resources.items()})
    result = dict(direction_driver=authority["direction_driver"], input_events=authority["input_events"])
    check.facing_replay_driver_evidence(result, "ComboStepFacingHeld")
    inputs = check.facing_input_evidence(log["rows"], sources, authority["direction_driver"], authority["owner_endpoint"])
    corrections = check.facing_correction_evidence(log["rows"], inputs, [v["original_source"] for v in resources.values()])
    replay = check.facing_reject_replay_evidence(log["rows"], resources, inputs, corrections, authority["direction_driver"])
    bindings = {tuple(item["key"]): {key: item[key] for key in ("slot", "main")} for item in authority["bindings"]}
    retirement = check.facing_resource_retirement(log["rows"], resources, bindings)
    check.require(check.facing_replay_actions_complete({key: SimpleNamespace(state=value, source=value["original_source"])
                  for key, value in resources.items()}), "最后原动作未自然结束")
    tasks = check.combo_task_evidence(authority["pose"]["records"], authority["arm"])
    initial = check.initial_route_evidence(log, tasks, sources, authority["owner_public"]["cleanup_verified"])
    steps = {str(step): source for (side, step), source in sources.items() if side == "authority"}
    local = check.facing_pose_evidence(authority["pose"]["records"], expected_native(authority["pose"]["records"]), steps, imported=False)
    remote = check.facing_pose_evidence(observer["pose"]["records"], expected_native(observer["pose"]["records"]), steps, imported=True)
    for step, evidence in inputs["steps"].items():
        native_id = int(evidence["endpoints"]["authority"]["basis"]["fields"]["NativeId"])
        local["steps"][step]["accepted_native_id"] = native_id
        accepted = [item for item in local["steps"][step]["sources"] if item["first"]["source"]["local_id"] == native_id]
        check.require(len(accepted) == 1 and accepted[0]["progressed"], "Authority 原接受 RMS 缺唯一实际推进：" + step)
    missing = inputs["missing"] + corrections["missing"] + replay["missing"] + retirement["missing"] + initial["missing"]
    if not local["no_action_source"]:
        missing.append("NativeRMSNotRetired")
    check.require(not missing, "纠正重放未覆盖：" + repr(missing))
    return dict(input=inputs, correction=corrections, replay=replay, retirement=retirement, initial=initial,
                authority_native=local, observer_native=remote,
                observer_native_execution="uncovered; simulated proxy has no local action RMS Apply contract",
                observer_replication_frame_pairing="uncovered; not inferred from actor movement or empty RMS groups")


def verify_initial(authority, observer, log):
    fault, owner = authority["fault"], authority["owner_public"]
    check.require(fault and fault["applied"] and not authority["actions"], "缺初始数据故障未施加或已经起段")
    events = authority["input_events"]
    check.require([(e["action"], e["edge"]) for e in events] == [("Attack", "Press"), ("Attack", "Release")]
                  and int(events[1]["owner_submission_frame"]) > int(events[0]["owner_submission_frame"]), "取消试次不是一次分帧攻击")
    tasks = check.combo_task_evidence(authority["pose"]["records"], authority["arm"])
    rows, handle = log["rows"], authority["arm"]["spec_handle"]
    send = [r for r in rows if r["kind"] == "AbilitySystem.OwnedStepInput" and r["fields"].get("Boundary") == "InitialUnavailableSend"
            and r["fields"].get("ASC") == owner["asc"]]
    rpc = [r for r in rows if r["kind"] == "AbilitySystem.OwnedStepInput" and r["fields"].get("Boundary") == "InitialUnavailableRPC"
           and r["fields"].get("ASC") == authority["arm"]["expected"]["ability_system"]]
    received = [r for r in rows if r["kind"] == "Combat.PlayerCombo.InitialUnavailable" and r["fields"].get("Boundary") == "Receive"
                and any(r["fields"].get("Ability") == i["instance"] for i in tasks["last_spec"]["instances"])]
    check.require(len(send) == len(rpc) == len(received) == 1, "缺唯一 InitialUnavailable Send/RPC/Receive")
    sent, remote, final = [seq[0]["fields"] for seq in (send, rpc, received)]
    check.require(sent["Spec"] == remote["Spec"] == final["Spec"] == handle
                  and sent["ActivationKey"] == remote["ActivationKey"] == final["ActivationKey"] and sent["ActivationKey"]
                  and rows.index(send[0]) < rows.index(rpc[0]) < rows.index(received[0])
                  and final["Step"] == "-1" and final["Task"] not in ("", "None"), "取消消息未配到同激活的起段前任务")
    check.require(not any(r["kind"] == "AbilitySystem.OwnedStepInput" and r["fields"].get("Spec") == handle
                  and r["fields"].get("Boundary") in ("SendAttempt", "RPCImplementation") for r in rows), "缺数据却发送了完整输入")
    expected_error = ("PlayerCombo [" + owner["ability"] + "] Body rejected: Avatar/Mesh [" + owner["mesh"]
                      + "], Trace [None] or World [" + owner["world"] + "] is invalid.")
    check.require(len(log["errors"]) == 1 and log["errors"][0]["message"] == expected_error, "不是唯一的原 owner 缺 Trace 错误")
    check.require(tasks["cleanup_verified"] and owner["cleanup_verified"], "取消后原任务/GA/Attacking 未清理")
    for data in (authority, observer):
        native = check.initial_native_records(data["pose"]["records"], expected_native(data["pose"]["records"]))
        check.require(native["no_action_source"], "起段失败却存在 RMS")
    return dict(send=send[0], rpc=rpc[0], receive=received[0], known_tasks=tasks, expected_error=expected_error)


def verify_fx(authority, observer):
    case, joined, continuous, state = (observer[k] for k in ("case", "join_record", "network_fx", "fx"))
    check.require(continuous and not continuous["active"] and not continuous["evidence_incomplete"]
                  and continuous["stop_reason"] == "StoppedByCaller", "连续 Publisher 观察不完整")
    key = joined["terminal_occurrence"] if case == "closed_first" else joined["occurrence"]
    terminal = check.fx_dispatched_close(authority["fx"], key)
    check.require(terminal is not None, "Authority 没有该键的终态")
    visual = observer.get("visual_fx")
    if visual:
        check.require(authority.get("visual_fx") == visual and joined["system"] == visual["system"], "可见层不是指定原生产 FX")
        keys = {tuple(item["key"]) for item in authority["actions"]}
        check.require(keys == {(side, step, 0) for side in ("owner", "authority") for step in range(3)},
                      "Normal03 可见场景缺两端原三连真实起段")
        check.require([(e["action"], e["edge"]) for e in authority["input_events"]]
                      == [("Attack", edge) for _ in range(3) for edge in ("Press", "Release")],
                      "Normal03 可见场景不是原三次分帧攻击")
    check.require(observer["images"], "缺客户端视口")
    tail_probe = observer.get("tail_seek_probe")
    tail_evidence = check.fx_tail_seek_evidence(state, tail_probe) if tail_probe else None
    qualified = []
    for capture in observer["images"]:
        native = capture["native"]
        check.require(native["file_write_complete"] and native["file_readback_verified"] and native["resources_released"]
                      and not native["error"] and Path(capture["file"]).is_file(), "视口读回或资源归还未完成")
        check.require(native["world_path"] == state["original_source"]["world"] and native["net_mode"] == 3, "截图不是原客户端 World")
        sample = check.fx_tail_viewport_witness(state, tail_probe, native) if tail_probe \
            else check.fx_viewport_witness(case, state, joined, native)
        witness = check.fx_replication_witness(continuous, joined, closed=case == "closed_first", through_frame=native["render_callback_frame"])
        if sample and witness and (tail_probe or not visual or sample["controller_age"] >= visual["minimum_age"]):
            qualified.append((capture, sample, witness))
    check.require(qualified, "缺同一次自然 Draw 的 FX 和复制快照证据")
    capture, sample, witness = qualified[0]
    native = capture["native"]
    if case == "live_first":
        hidden = authority["relevancy"]["first_hidden"]
        connection, created = (observer["relevancy"][k] for k in ("first_connection", "first_new"))
        check.require(hidden["actor_channel_absent"] and not hidden["pawn_relevant_to_viewer"]
                      and hidden["connection_open"] and connection["connection_open"] and created["connection_open"]
                      and all(connection[k] == created[k] for k in ("world", "connection_id", "viewer_player_id"))
                      and created["pawn_net_guid"] == hidden["pawn_net_guid"] and created["channel_id"] > 0,
                      "首次入场不是同一实际连接从无 Pawn 通道到首次代理")
        check.require(authority["relevancy"]["cull_restored"] > hidden["net_cull_distance_squared"]
                      and authority["relevancy"]["first_release_record"] == joined,
                      "首次相关性恢复没有原 FX 切点或裁剪范围未恢复")
    if case == "reacquire":
        old, new = (observer["relevancy"][k] for k in ("old", "new"))
        check.require(all(old[k] == new[k] for k in ("world", "connection_id", "viewer_player_id", "pawn_net_guid"))
                      and old["pawn_id"] != new["pawn_id"], "重获没有同连接新代理")
        check.require(check.fx_channel_log_event(authority["relevancy"]["close"]["line"], authority["relevancy"]["old"], cleanup=False)
                      and check.fx_channel_log_event(observer["relevancy"]["cleanup"]["line"], old, cleanup=True), "缺原通道 Close/CleanUp Relevancy")
        created = observer["relevancy"]["creation"]
        check.require(created["offset"] >= observer["relevancy"]["cleanup"]["offset"]
                      and check.fx_channel_log_event(created["line"], new, cleanup=False, creation=True),
                      "缺原通道清理后同 NetGUID 新代理的实际 ProcessBunch 创建")
        check.require(check.fx_reacquire_creation(continuous, joined, observer["relevancy"], native["render_callback_frame"]), "缺新 Proxy 的 RemoteCreated")
        check.require(authority["relevancy"]["cull_restored"] == authority["relevancy"]["old"]["net_cull_distance_squared"], "裁剪距离未恢复")
        timeout = authority["relevancy"]["timeout"]
        check.require(timeout["source"] == "process_ini_override" and abs(timeout["actual"] - 0.05) < 0.000001,
                      "缺原 NetDriver 的进程内相关性等待读回")
        old_state = observer.get("old_fx")
        check.require(old_state and not old_state["evidence_incomplete"] and old_state["subscriptions_released"], "缺旧 FX 原观察窗及归还")
        retired = [r for r in old_state["records"] if r["occurrence"] == key and r["resource_state_known"]
                   and r["held_resource_released"] and int(r["component_id"]) > 0]
        check.require(retired, "未观察到同键旧 FX 实际归还")
        check.require(all(r["generation"] != sample["generation"] and r["component_id"] != sample["component_id"] for r in retired)
                      and any(int(r["native_event_frame"]) <= int(sample["native_event_frame"]) for r in retired),
                      "新 FX 沿用了已退役资源，或未证明旧资源归还后后继仍可见")
    if case != "closed_first":
        check.require(any(row["has_terminal"] and all(row[k] == terminal[k] for k in
            ("terminal_occurrence", "close_revision", "close_reason")) for row in state["records"]), "远端终态未与 Authority 对齐")
    return dict(sample=sample, state_received=witness, screenshot=capture["file"],
                qualified_screenshots=[item[0]["file"] for item in qualified], visual_review="required",
                purpose="tail_seek_regression" if tail_probe else "late_relevancy_acceptance",
                tail_seek_regression=tail_evidence)


def verify(folder):
    authority, observer = [json.loads((folder / role / "observations.json").read_text(encoding="utf-8"))
                           for role in ("authority", "observer")]
    for data in (authority, observer):
        validate_run(data)
    check.require(authority["case"] == observer["case"], "两端不是同一试次")
    log = check.facing_log_rows(Path(authority["log_path"]), authority["log_offset"], authority["log_end"])
    case = authority["case"]
    if case == "attack_only":
        detail = verify_attack(authority, observer, log)
    elif case == "correction":
        detail = verify_correction(authority, observer, log)
    elif case == "initial_unavailable":
        detail = verify_initial(authority, observer, log)
    else:
        detail = verify_fx(authority, observer)
    return dict(case=case, numeric_checks_passed=True, visual_review="required", detail=detail)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    result = verify(args.folder.resolve())
    (args.folder / "checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(result["case"] + ": numeric_checks_passed; visual_review=required")
