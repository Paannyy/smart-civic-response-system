from app.api.complaints import ALLOWED_STATUS_TRANSITIONS


def test_pending_can_be_assigned():
    assert "assigned" in ALLOWED_STATUS_TRANSITIONS["pending"]


def test_assigned_can_be_in_progress():
    assert "in_progress" in ALLOWED_STATUS_TRANSITIONS["assigned"]


def test_in_progress_can_be_resolved():
    assert "resolved" in ALLOWED_STATUS_TRANSITIONS["in_progress"]


def test_resolved_cannot_change():
    assert ALLOWED_STATUS_TRANSITIONS["resolved"] == set()


def test_invalid_transition_is_not_allowed():
    assert "pending" not in ALLOWED_STATUS_TRANSITIONS["in_progress"]
    assert "in_progress" not in ALLOWED_STATUS_TRANSITIONS["resolved"]