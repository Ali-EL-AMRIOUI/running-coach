"""
tests/test_core/test_rules.py
Unit tests for core/rules/safety_rules.py and core/rules/progression_rules.py.
"""

import pytest
from datetime import date, timedelta

from core.rules.safety_rules import (
    build_athlete_context_warnings,
    classify_session,
    validate_plan_hard_limits,
)
from core.rules.progression_rules import (
    detect_level,
    get_progression_bounds,
)


class FakeRequest:
    """Minimal stand-in for PlanRequest in these unit tests."""
    def __init__(self, **kwargs):
        defaults = {
            "age": 30,
            "last_injury": None,
            "return_date": None,
            "current_volume": 40,
            "current_frequency": 4,
            "availability": 4,
            "goal_date": None,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


# --- classify_session ---

class TestClassifySession:

    def test_interval_is_intense(self):
        assert classify_session("INTERVAL") == "intense"

    def test_easy_run_is_easy(self):
        assert classify_session("EASY_RUN") == "easy"

    def test_case_insensitive(self):
        assert classify_session("interval") == "intense"

    def test_unknown_type(self):
        assert classify_session("SOMETHING_WEIRD") == "unknown"


# --- build_athlete_context_warnings ---

class TestAthleteContextWarnings:

    def test_recent_injury_triggers_warning(self):
        recent_date = (date.today() - timedelta(days=10)).isoformat()
        request = FakeRequest(last_injury="achilles", return_date=recent_date)
        warnings = build_athlete_context_warnings(request)
        assert any("RETURN FROM INJURY" in w or "RECENT RETURN" in w for w in warnings)

    def test_no_injury_no_warning(self):
        request = FakeRequest()
        warnings = build_athlete_context_warnings(request)
        assert not any("INJURY" in w for w in warnings)

    def test_senior_athlete_triggers_warning(self):
        request = FakeRequest(age=65)
        warnings = build_athlete_context_warnings(request)
        assert any("60+" in w for w in warnings)

    def test_junior_athlete_triggers_warning(self):
        request = FakeRequest(age=15)
        warnings = build_athlete_context_warnings(request)
        assert any("JUNIOR" in w for w in warnings)

    def test_availability_below_frequency_triggers_warning(self):
        request = FakeRequest(current_frequency=6, availability=3)
        warnings = build_athlete_context_warnings(request)
        assert any("FREQUENCY" in w for w in warnings)

    def test_short_timeframe_triggers_warning(self):
        soon = (date.today() + timedelta(weeks=3)).isoformat()
        request = FakeRequest(goal_date=soon)
        warnings = build_athlete_context_warnings(request)
        assert any("SHORT TIME FRAME" in w for w in warnings)


# --- validate_plan_hard_limits ---

def make_session(session_type, km=10.0):
    return {"type": session_type, "km": km, "pace": "5:00-5:30/km", "details": ""}


def make_rest_day(day_num):
    return {
        "day": day_num,
        "morning": make_session("REST", 0),
        "afternoon": make_session("REST", 0),
    }


def make_easy_day(day_num, km=8.0):
    return {
        "day": day_num,
        "morning": make_session("EASY_RUN", km),
        "afternoon": make_session("REST", 0),
    }


def make_intense_day(day_num, km=10.0):
    return {
        "day": day_num,
        "morning": make_session("INTERVAL", km),
        "afternoon": make_session("REST", 0),
    }


class TestValidatePlanHardLimits:

    def test_empty_plan_is_invalid(self):
        result = validate_plan_hard_limits([], FakeRequest())
        assert result["valid"] is False
        assert len(result["violations"]) > 0

    def test_week_with_wrong_day_count_is_invalid(self):
        week = {
            "week": 1,
            "weekly_km": 10,
            "days": [make_easy_day(1)],  # only 1 day instead of 7
        }
        result = validate_plan_hard_limits([week], FakeRequest())
        assert result["valid"] is False
        assert any("instead of 7" in v for v in result["violations"])

    def test_two_consecutive_intense_days_is_invalid(self):
        days = [make_intense_day(1), make_intense_day(2)] + [make_rest_day(i) for i in range(3, 8)]
        week = {"week": 1, "weekly_km": 20, "days": days}
        result = validate_plan_hard_limits([week], FakeRequest())
        assert result["valid"] is False
        assert any("consecutive intense" in v for v in result["violations"])

    def test_intense_then_easy_is_valid(self):
        days = [make_intense_day(1), make_easy_day(2)] + [make_rest_day(i) for i in range(3, 8)]
        week = {"week": 1, "weekly_km": 18, "days": days}
        result = validate_plan_hard_limits([week], FakeRequest())
        assert result["valid"] is True

    def test_intense_double_session_same_day_is_invalid(self):
        day = {
            "day": 1,
            "morning": make_session("INTERVAL", 8),
            "afternoon": make_session("THRESHOLD", 8),
        }
        days = [day] + [make_rest_day(i) for i in range(2, 8)]
        week = {"week": 1, "weekly_km": 16, "days": days}
        result = validate_plan_hard_limits([week], FakeRequest())
        assert result["valid"] is False
        assert any("double session" in v for v in result["violations"])

    def test_reasonable_week_with_no_rest_day_gives_warning_not_violation(self):
        days = [make_easy_day(i) for i in range(1, 8)]
        week = {"week": 1, "weekly_km": 56, "days": days}
        result = validate_plan_hard_limits([week], FakeRequest())
        # No full rest day -> should be a warning, not a blocking violation
        assert any("rest" in w.lower() for w in result["warnings"])

    def test_excessive_progression_between_weeks_gives_warning(self):
        week1 = {"week": 1, "weekly_km": 40, "days": [make_easy_day(i) for i in range(1, 8)]}
        week2 = {"week": 2, "weekly_km": 70, "days": [make_easy_day(i) for i in range(1, 8)]}  # +75%
        result = validate_plan_hard_limits([week1, week2], FakeRequest())
        assert any("progression" in w.lower() for w in result["warnings"])


# --- detect_level ---

class TestDetectLevel:

    def test_elite_from_half_record(self):
        level = detect_level(current_volume=100, record_half="1:10:00")
        assert level == "elite"

    def test_beginner_from_half_record(self):
        level = detect_level(current_volume=20, record_half="2:00:00")
        assert level == "beginner"

    def test_fallback_to_volume_without_records(self):
        level = detect_level(current_volume=90)
        assert level == "advanced"

    def test_fallback_beginner_low_volume(self):
        level = detect_level(current_volume=15)
        assert level == "beginner"


# --- get_progression_bounds ---

class TestProgressionBounds:

    def test_returns_expected_keys(self):
        bounds = get_progression_bounds(40, "half", "intermediate")
        assert "max_weekly_increase" in bounds
        assert "max_peak_volume_km" in bounds

    def test_elite_has_higher_peak_than_beginner(self):
        elite_bounds = get_progression_bounds(80, "marathon", "elite")
        beginner_bounds = get_progression_bounds(40, "marathon", "beginner")
        assert elite_bounds["max_peak_volume_km"] > beginner_bounds["max_peak_volume_km"]
