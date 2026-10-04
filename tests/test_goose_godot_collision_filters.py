"""Source-bound native fixtures and rejection guards; not whole-robot tests."""
import copy
import json
from pathlib import Path

import pytest

from scripts.evaluation import check_goose_godot_collision_filters as evaluator
from scripts.evaluation.check_goose_godot_collision_filters import (
    ROOT, POLICY, sha, validate_report,
)

EVIDENCE = ROOT / "robots/Goose_V0.1/evidence"
ACCEPTANCE = EVIDENCE / "task_proxy_11_v1_godot_filter_acceptance.json"
FIXTURES = EVIDENCE / "task_proxy_11_v1_jolt_filter_fixtures.json"


def recorded():
    return json.loads(FIXTURES.read_text())


def test_actual_jolt_record_is_bound_to_current_sources_and_has_complete_coverage():
    acceptance = json.loads(ACCEPTANCE.read_text())
    assert acceptance["native_full_robot_qualified"] is False
    assert acceptance["hardware_modified"] is False
    assert acceptance["full_task_success_claim"] is False
    for path, expected in (acceptance["input_sha256"] | acceptance["receiver_source_sha256"]).items():
        assert sha(ROOT / path) == expected, path
    assert sha(Path(evaluator.__file__)) == acceptance["evaluator_sha256"]
    assert sha(FIXTURES) == acceptance["results"]["jolt"]["result_sha256"]
    assert validate_report(recorded(), json.loads(POLICY.read_text()), "Jolt Physics") == acceptance["results"]["jolt"]["summary"]


@pytest.mark.parametrize("pair,scope", [
    ({"head_upper_bill_envelope", "torso_envelope"}, "same_instance"),
    ({"left_flexible_sole", "right_flexible_sole"}, "same_instance"),
    ({"torso_envelope", "lower_neck_envelope"}, "other_robot"),
])
def test_lost_retained_or_cross_instance_contacts_are_rejected(pair, scope):
    report = copy.deepcopy(recorded())
    row = next(r for r in report["rows"] if r["scope"] == scope
               and {r["first"], r["second"]} == pair and not r["unfiltered_control"])
    row["native_contact_samples"] = 0
    row["collision_enabled"] = False
    with pytest.raises(ValueError, match="filtering mismatch"):
        validate_report(report, json.loads(POLICY.read_text()), "Jolt Physics")


def test_missing_unfiltered_control_is_not_a_passing_ignore_test():
    report = recorded()
    report["rows"] = [r for r in report["rows"] if not (
        r["unfiltered_control"] and {r["first"], r["second"]} == {"torso_envelope", "lower_neck_envelope"})]
    with pytest.raises(ValueError, match="Incomplete"):
        validate_report(report, json.loads(POLICY.read_text()), "Jolt Physics")


@pytest.mark.parametrize("value", [float("nan"), 0.0])
def test_unknown_or_zero_raw_overlap_does_not_pass(value):
    report = recorded()
    report["rows"][0]["raw_penetration_m"] = value
    with pytest.raises(ValueError, match="penetration witness"):
        validate_report(report, json.loads(POLICY.read_text()), "Jolt Physics")


def test_runtime_abort_or_wrong_engine_cannot_inherit_the_recorded_pass():
    report = recorded()
    report["rows"][0] = None
    with pytest.raises(ValueError, match="Invalid native"):
        validate_report(report, json.loads(POLICY.read_text()), "Jolt Physics")
    with pytest.raises(ValueError, match="Wrong actual physics engine"):
        validate_report(recorded(), json.loads(POLICY.read_text()), "GodotPhysics3D")


def test_unqualified_builtin_engine_failure_is_not_promoted_to_jolt_or_task_success():
    rejection = json.loads((EVIDENCE / "godot_physics_collision_filter_rejection.json").read_text())
    assert rejection["physics_engine"] == "GodotPhysics3D"
    assert rejection["passed"] is False
    assert rejection["rejected_fixture_count"] == len(rejection["rejected_rows"]) > 0
    assert rejection["contact_mismatch_count"] > 0
    assert rejection["collision_policy_sha256"] == sha(POLICY)
