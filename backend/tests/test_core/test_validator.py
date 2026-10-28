"""
tests/test_core/test_validator.py
Unit tests for core/agents/validator_agent.py.
"""

import pytest
from core.agents.validator_agent import (
    ValidatorAgent,
    parse_pace_range,
    pace_range_center,
)


class FakeRequest:
    """Minimal stand-in for PlanRequest in these unit tests."""
    def __init__(self, **kwargs):
        defaults = {"double_session": "no"}
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


# --- parse_pace_range ---

class TestParsePaceRange:

    def test_range_format(self):
        assert parse_pace_range("4:15-4:30/km") == (255, 270)

    def test_single_pace_format(self):
        assert parse_pace_range("4:15/km") == (255, 255)

    def test_na_returns_none(self):
        assert parse_pace_range("N/A") is None

    def test_empty_returns_none(self):
        assert parse_pace_range("") is None

    def test_range_is_ordered_min_max_regardless_of_input_order(self):
        result = parse_pace_range("4:30-4:15/km")
        assert result[0] < result[1]


# --- pace_range_center ---

class TestPaceRangeCenter:

    def test_center_of_range(self):
        assert pace_range_center("4:00-4:10/km") == pytest.approx(245.0)

    def test_none_for_na(self):
        assert pace_range_center("N/A") is None


# --- ValidatorAgent full plan validation ---

def make_session(session_type, km=10.0, pace="5:00-5:30/km", details="generic session detail text"):
    return {"type": session_type, "km": km, "pace": pace, "details": details}


def make_rest_day(day_num):
    return {
        "day": day_num,
        "morning": make_session("REST", 0, "N/A", "Rest"),
        "afternoon": make_session("REST", 0, "N/A", "Rest"),
    }


def make_easy_day(day_num, km=8.0):
    return {
        "day": day_num,
        "morning": make_session("EASY_RUN", km),
        "afternoon": make_session("REST", 0, "N/A", "Rest"),
    }


def valid_week(week_num=1):
    """A minimal structurally-valid week: 7 days, 1 full rest day, rest easy runs."""
    days = [make_rest_day(1)] + [make_easy_day(i, km=8.0) for i in range(2, 8)]
    weekly_km = sum(
        d["morning"]["km"] + d["afternoon"]["km"] for d in days
    )
    return {"week": week_num, "phase": "Base", "weekly_km": weekly_km, "days": days}


class TestValidatorAgentStructure:

    def test_valid_plan_passes(self):
        plan = {"weeks": [valid_week(1)]}
        validator = ValidatorAgent()
        is_valid, errors = validator.run(plan, FakeRequest())
        assert is_valid is True
        assert errors == []

    def test_missing_weeks_key_fails(self):
        validator = ValidatorAgent()
        is_valid, errors = validator.run({}, FakeRequest())
        assert is_valid is False
        assert len(errors) > 0

    def test_wrong_day_count_fails(self):
        week = valid_week(1)
        week["days"] = week["days"][:5]  # only 5 days
        plan = {"weeks": [week]}
        validator = ValidatorAgent()
        is_valid, errors = validator.run(plan, FakeRequest())
        assert is_valid is False
        assert any("instead of 7" in e for e in errors)

    def test_unknown_session_type_fails(self):
        week = valid_week(1)
        week["days"][1]["morning"]["type"] = "NOT_A_REAL_TYPE"
        plan = {"weeks": [week]}
        validator = ValidatorAgent()
        is_valid, errors = validator.run(plan, FakeRequest())
        assert is_valid is False
        assert any("unknown type" in e for e in errors)

    def test_double_session_not_allowed_when_disabled(self):
        week = valid_week(1)
        week["days"][1]["morning"] = make_session("EASY_RUN", 5)
        week["days"][1]["afternoon"] = make_session("EASY_RUN", 5)  # both running
        plan = {"weeks": [week]}
        validator = ValidatorAgent()
        is_valid, errors = validator.run(plan, FakeRequest(double_session="no"))
        assert is_valid is False
        assert any("double session" in e for e in errors)

    def test_intense_double_session_always_fails(self):
        week = valid_week(1)
        week["days"][1]["morning"] = make_session("INTERVAL", 8)
        week["days"][1]["afternoon"] = make_session("THRESHOLD", 8)
        plan = {"weeks": [week]}
        validator = ValidatorAgent()
        is_valid, errors = validator.run(plan, FakeRequest(double_session="yes"))
        assert is_valid is False
        assert any("INTENSE double session" in e for e in errors)

    def test_zero_km_on_active_session_fails(self):
        week = valid_week(1)
        week["days"][1]["morning"]["km"] = 0
        plan = {"weeks": [week]}
        validator = ValidatorAgent()
        is_valid, errors = validator.run(plan, FakeRequest())
        assert is_valid is False
        assert any("km=0" in e for e in errors)

    def test_km_mismatch_beyond_tolerance_fails(self):
        week = valid_week(1)
        week["weekly_km"] = week["weekly_km"] + 50  # declared way off from actual
        plan = {"weeks": [week]}
        validator = ValidatorAgent()
        is_valid, errors = validator.run(plan, FakeRequest())
        assert is_valid is False
        assert any("actual vs" in e for e in errors)
