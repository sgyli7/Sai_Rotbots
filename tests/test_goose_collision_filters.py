import copy
import json
import pytest

from scripts.evaluation.check_goose_collision_filters import (
    POLICY, check_rows, collision_policy, source_filter_probe, validate_policy,
)


def test_bound_source_pairs_actually_filter_and_keep_environment_contacts():
    policy = json.loads(POLICY.read_text())
    validate_policy(policy)
    assert check_rows(source_filter_probe(), policy)["total_fixtures"] == 97


@pytest.mark.parametrize("pair", [
    {"head_upper_bill_envelope", "torso_envelope"},
    {"left_flexible_sole", "right_flexible_sole"},
])
def test_unrelated_self_contact_cannot_be_silently_excluded(pair):
    policy = copy.deepcopy(collision_policy())
    row = next(r for r in policy["pairs"] if {r["first"], r["second"]} == pair)
    assert row["collision_enabled"] is True
    row["collision_enabled"] = False
    with pytest.raises(ValueError, match="selective"):
        validate_policy(policy)
