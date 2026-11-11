"""@file test_minimal_multiplayer_checks.py @brief 证据缺失和错误关联不得变成联机通过。"""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import minimal_multiplayer_checks as check
from verify_minimal_multiplayer import final_interval


class EvidenceTests(unittest.TestCase):
    def test_observation_pages_keep_records_and_latest_terminal_metadata(self):
        previous = dict(records=[{"frame": 1}], original_source={"task": "original"}, active=True)
        page = dict(read_success=True, records_start_index=1, record_count=2,
                    records=[{"frame": 2}], original_source={"task": "original"}, active=False)
        merged = check.merge_observation_page(previous, page)
        self.assertEqual(merged["records"], [{"frame": 1}, {"frame": 2}])
        self.assertFalse(merged["active"])

    def test_observation_pages_reject_missing_duplicate_or_replaced_source(self):
        previous = dict(records=[{"frame": 1}], original_source={"task": "original"})
        valid = dict(read_success=True, records_start_index=1, record_count=2,
                     records=[{"frame": 2}], original_source={"task": "original"})
        for changed in [dict(records_start_index=0), dict(records_start_index=2),
                        dict(record_count=3), dict(read_success=False), dict(original_source={"task": "successor"})]:
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                check.merge_observation_page(copy.deepcopy(previous), {**valid, **changed})

    def test_initial_press_is_not_matched_to_later_continue(self):
        rows, sources = [], {}
        for side, world, remote in (("owner", "Client", "0"), ("authority", "Server", "1")):
            source = dict(ability=world + "/GA", world=world, step_token="1", cmc_motion_handle=10,
                montage_instance_id=7, cmc=world + "/CMC", pawn=world + "/Pawn", montage="Montage")
            sources[(side, 0)] = source
            rows.extend([
                dict(kind="Combat.PlayerCombo.StepFacing", fields=dict(Ability=source["ability"], World=world,
                    Step="0", StepToken="1", Handle="10", Instance="7", Mode="1", Entry=[0, 0, 0, 1], StepOrigin="0")),
                dict(kind="Movement.ActionStartBasis", fields=dict(CMC=source["cmc"], Montage="Montage", Handle="10",
                    Instance="7", Request="0", Entry=[0, 0, 0, 1], Session="4", EdgeEvaluation="8", StepEvaluation="8")),
                dict(kind="Movement.ActionStartInput", fields=dict(CMC=source["cmc"], World=world, Pawn=source["pawn"],
                    Remote=remote, Request="0", Kind="0", SourceStep="-1", Session="4", EdgeEvaluation="8",
                    StepEvaluation="8", AxisX="0", AxisY="1", ControlYaw="0", InputState="1"))])
        owner = dict(world="Client", pc="PC", pawn="Client/Pawn", player_input="Input")
        rows.append(dict(kind="Input.MovementEvaluation", fields=dict(Phase="Completed", World="Client", PC="PC",
            Pawn="Client/Pawn", PlayerInput="Input", SessionSerial="4", EvaluationSerial="8", EntryFrame="11",
            CompletedFrame="11", ValueState="Readable", ActionValue="(X=0,Y=1)", Action="Move")))
        result = check.facing_input_evidence(rows, sources,
            dict(variant="reject_replay", first_press_frame=10, second_press_frame=20, third_press_frame=30), owner)
        self.assertIn("0", result["steps"])
        self.assertEqual(set(result["steps"]["0"]["evaluations"]), {"edge", "step"})
        self.assertIn("owner.OriginalStep1", result["missing"])

    def test_nearby_snapshot_does_not_prove_prediction_alive_at_receive(self):
        result = check.facing_prediction_at_receive(dict(receive=dict(fields={})), {})
        self.assertFalse(result["verified"])
        self.assertIn("PreTaskActive", result["missing"])

    def test_cancelled_exit_is_not_natural(self):
        state = dict(natural_completion_history_complete=True, original_ga_full_exit_completed=True,
                     original_exit_cancelled=False)
        self.assertTrue(check.natural_exit(state))
        state["original_exit_cancelled"] = True
        self.assertFalse(check.natural_exit(state))
        self.assertFalse(check.natural_exit(dict(original_ga_full_exit_completed=True)))

    def test_closed_snapshot_requires_received_replication(self):
        joined = dict(terminal_occurrence="9", close_revision="5")
        state = dict(records=[])
        self.assertIsNone(check.fx_replication_witness(state, joined, closed=True))
        state["records"].append(dict(kind="StateReceived", active_occurrences=[], state_revision="5", native_event_frame="8"))
        self.assertIsNotNone(check.fx_replication_witness(state, joined, closed=True))
        state["records"].append(dict(kind="RemoteCreated", occurrence="9"))
        with self.assertRaises(RuntimeError):
            check.fx_replication_witness(state, joined, closed=True)

    def test_visual_trial_pins_the_requested_production_unit(self):
        row = dict(has_record=True, active_record=True, avatar_mesh_association_known=True)
        state = dict(records=[dict(row, system="Ground", occurrence="7"),
                              dict(row, system="Other", occurrence="8")])
        self.assertEqual(check.fx_active(state, "Ground")["occurrence"], "7")
        state["records"].append(dict(has_terminal=True, terminal_occurrence="7"))
        self.assertIsNone(check.fx_active(state, "Ground"))

    def test_desired_age_does_not_substitute_actual_age(self):
        row = dict(occurrence="1", active_record=True, has_record=True, avatar_mesh_association_known=True,
            remote_entry=True, resource_state_known=True, controller_valid=True, controller_age_valid=True,
            target_age_valid=True, reached=True, rendering_enabled=True, registered=True, controller_complete=False,
            controller_pending_spawn=False, actual_execution_state=0, requested_execution_state=0,
            controller_age=0.54, target_age=0.55, desired_age=0.55, effective_step=0.033)
        self.assertTrue(check.fx_reached(row))
        row["controller_age"] = 0.0
        self.assertFalse(check.fx_reached(row))
        row["controller_age"] = 0.54
        row["controller_age_valid"] = False
        self.assertFalse(check.fx_reached(row))

    def test_final_interval_requires_actual_end_and_step(self):
        interval = dict(action_handle=7, source_kind=2, status=1, has_native_source_interval=True,
            native_source_finished=True, motion_start_seconds=0.98, motion_end_seconds=1.0,
            native_start_seconds=0.98, native_end_seconds=1.0, native_delta_seconds=0.02,
            source_intervals=[{}], curve_yaw_applied=True, requested_yaw_delta_degrees=0.0,
            actual_before=dict(translation=[0, 0, 0], rotation=[0, 0, 0, 1]),
            actual_after=dict(translation=[1, 0, 0], rotation=[0, 0, 0, 1]))
        records = [dict(movement_completed_interval=interval, movement_action_native=dict(
            active_sources=[dict(montage="M", native_imported=False, binding_end_seconds=1.0)], pending_sources=[]))]
        source = dict(montage="M", cmc_motion_handle=7)
        self.assertEqual(final_interval(records, source), interval)
        for field, value in (("motion_end_seconds", 0.99), ("native_delta_seconds", 0), ("curve_yaw_applied", False)):
            wrong = copy.deepcopy(records)
            wrong[0]["movement_completed_interval"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                final_interval(wrong, source)

    def test_viewport_requires_actual_age_on_its_own_draw_frame(self):
        row = dict(kind="Snapshot", native_event_frame="10", occurrence="1", state_revision="1",
            generation="1", component_id="2", controller_id="3", begin_server_time=1.0, has_terminal=False,
            active_record=True, has_record=True, avatar_mesh_association_known=True, remote_entry=True,
            resource_state_known=True, controller_valid=True, controller_age_valid=True, target_age_valid=True,
            reached=True, rendering_enabled=True, registered=True, controller_complete=False,
            controller_pending_spawn=False, actual_execution_state=0, requested_execution_state=0,
            controller_age=0.5, target_age=0.51, effective_step=0.033)
        draw = dict(row, native_event_frame="11", controller_age=0.6)
        state = dict(records=[row, draw])
        joined = dict(occurrence="1", state_revision="1", begin_server_time=1.0)
        native = dict(request_frame="10", render_callback_frame="11", readback_complete_frame="15")
        self.assertIsNone(check.fx_viewport_witness("live_first", state, joined, native))
        state["records"].append(dict(row, native_event_frame="12"))
        self.assertIsNone(check.fx_viewport_witness("live_first", state, joined, native))
        native["render_callback_frame"] = "12"
        self.assertIsNotNone(check.fx_viewport_witness("live_first", state, joined, native))

    def test_channel_cleanup_reason_and_guid_must_match(self):
        anchor = dict(pawn_full_name="Pawn /Game/World.Pawn", channel_index=12, pawn_net_guid="42")
        line = "LogNetTraffic: UActorChannel::CleanUp (ChIndex: 12): Pawn /Game/World.Pawn | NetGuid: 42 | Reason: Relevancy"
        self.assertTrue(check.fx_channel_log_event(line, anchor, cleanup=True))
        self.assertFalse(check.fx_channel_log_event(line.replace("Relevancy", "Destroyed"), anchor, cleanup=True))
        self.assertFalse(check.fx_channel_log_event(line.replace("42", "43"), anchor, cleanup=True))

    def tail_fixture(self):
        start = dict(kind="Snapshot", native_event_frame="10", occurrence="1", generation="2", component_id="3",
            active_record=True, has_record=True, avatar_mesh_association_known=True, remote_entry=True,
            resource_state_known=True, controller_valid=True, controller_age_valid=True, target_age_valid=True,
            reached=True, rendering_enabled=True, registered=True, controller_complete=False,
            controller_pending_spawn=False, actual_execution_state=0, requested_execution_state=0,
            controller_age=0.5, target_age=0.51, effective_step=0.033, remote_seek_delta_seconds=0.033)
        hidden = dict(start, native_event_frame="12", rendering_enabled=False, target_age=0.7)
        tail = dict(hidden, kind="TailTransferred", native_event_frame="13", rendering_enabled=True,
                    active_record=False, tail_transferred=True)
        draw = dict(tail, kind="Snapshot", native_event_frame="14", controller_age=0.6)
        complete = dict(draw, kind="NaturalCompleted", native_event_frame="15", controller_age=0.7)
        destroyed = dict(complete, kind="ComponentDestroyed")
        probe = dict(start=start, hidden=hidden, tail=tail, applied_frame="11", applied_budget=0.000001,
                     original_budget=0.01, tail_native_tick_mode=True)
        return dict(records=[start, hidden, tail, draw, complete, destroyed]), probe

    def test_tail_draw_requires_same_component_and_exact_frame(self):
        packet, probe = self.tail_fixture()
        native = dict(render_callback_frame="14")
        self.assertIsNotNone(check.fx_tail_viewport_witness(packet, probe, native))
        for change in (dict(component_id="4"), dict(native_event_frame="16"), dict(rendering_enabled=False)):
            changed = copy.deepcopy(packet)
            changed["records"][3].update(change)
            with self.subTest(change=change):
                self.assertIsNone(check.fx_tail_viewport_witness(changed, probe, native))

    def test_tail_probe_requires_real_hidden_gap_and_natural_release(self):
        packet, probe = self.tail_fixture()
        self.assertIsNotNone(check.fx_tail_seek_evidence(packet, probe))
        for invalid in ("no_gap", "no_release", "wrong_clock"):
            changed, stimulus = copy.deepcopy((packet, probe))
            if invalid == "no_gap":
                stimulus["hidden"]["target_age"] = 0.51
            elif invalid == "no_release":
                changed["records"].pop()
            else:
                stimulus["tail_native_tick_mode"] = False
            with self.subTest(invalid=invalid), self.assertRaises(RuntimeError):
                check.fx_tail_seek_evidence(changed, stimulus)

    def test_pooled_channel_reopen_must_name_the_new_proxy(self):
        anchor = dict(pawn="/Game/World.Pawn_2", pawn_full_name="Pawn /Game/World.Pawn_2",
                      channel_index=12, pawn_net_guid="42")
        line = "LogNetLifecycle: UActorChannel::ProcessBunch: Creating ChIndex: 12 Actor: Pawn_2"
        self.assertTrue(check.fx_channel_log_event(line, anchor, cleanup=False, creation=True))
        self.assertFalse(check.fx_channel_log_event(line.replace("Pawn_2", "Pawn_1"), anchor, cleanup=False, creation=True))
        self.assertFalse(check.fx_channel_log_event(line.replace("12", "13"), anchor, cleanup=False, creation=True))


if __name__ == "__main__":
    unittest.main()
