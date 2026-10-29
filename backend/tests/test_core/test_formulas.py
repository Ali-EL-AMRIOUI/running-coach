"""
tests/test_core/test_formulas.py
Unit tests for core/rules/formulas.py — pure logic, no DB, no LLM.
"""

import pytest
from core.rules.formulas import (
    parse_time_to_seconds,
    seconds_to_pace_str,
    pace_to_kmh,
    riegel_pace,
    extract_all_records,
    compute_aerobic_profile,
    best_race_reference,
    estimate_vma,
    RECORD_DISTANCES,
)


# --- parse_time_to_seconds ---

class TestParseTimeToSeconds:

    def test_hh_mm_ss_format(self):
        assert parse_time_to_seconds("1:12:00") == 4320

    def test_mm_ss_format(self):
        assert parse_time_to_seconds("28:00") == 1680

    def test_none_input(self):
        assert parse_time_to_seconds(None) is None

    def test_empty_string(self):
        assert parse_time_to_seconds("") is None

    def test_na_string(self):
        assert parse_time_to_seconds("N/A") is None

    def test_invalid_format(self):
        assert parse_time_to_seconds("not a time") is None

    def test_whitespace_is_stripped(self):
        assert parse_time_to_seconds("  28:00  ") == 1680


# --- seconds_to_pace_str ---

class TestSecondsToPaceStr:

    def test_basic_conversion(self):
        assert seconds_to_pace_str(240) == "4:00/km"

    def test_rounds_seconds_with_leading_zero(self):
        assert seconds_to_pace_str(185) == "3:05/km"

    def test_zero_or_negative_returns_na(self):
        assert seconds_to_pace_str(0) == "N/A"
        assert seconds_to_pace_str(-10) == "N/A"


# --- riegel_pace ---

class TestRiegelPace:

    def test_longer_distance_gives_slower_pace(self):
        # 5k pace extrapolated to marathon must be slower (higher sec/km)
        pace_5k = 240  # 4:00/km
        pace_marathon = riegel_pace(pace_5k, 5.0, 42.195)
        assert pace_marathon > pace_5k

    def test_same_distance_returns_same_pace(self):
        pace = riegel_pace(240, 10.0, 10.0)
        assert pace == pytest.approx(240, rel=1e-6)


# --- extract_all_records ---

class FakeRequest:
    """Minimal stand-in for PlanRequest in these unit tests."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestExtractAllRecords:

    def test_extracts_only_provided_records(self):
        request = FakeRequest(record_5000m="20:00", record_half=None)
        records = extract_all_records(request)
        assert "record_5000m" in records
        assert "record_half" not in records

    def test_pace_is_in_seconds_per_km(self):
        request = FakeRequest(record_5000m="20:00")  # 1200s / 5km = 240 s/km
        records = extract_all_records(request)
        assert records["record_5000m"] == pytest.approx(240, rel=1e-6)

    def test_no_records_returns_empty_dict(self):
        request = FakeRequest()
        assert extract_all_records(request) == {}


# --- compute_aerobic_profile ---

class TestComputeAerobicProfile:

    def test_unknown_profile_when_only_one_distance_type(self):
        # Only short-distance records -> cannot compute the ratio
        records = {"record_1500m": 180.0}
        result = compute_aerobic_profile(records)
        assert result["profile"] == "unknown"

    def test_pure_marathoner_is_aerobic_elite(self):
        # 1500m and marathon paces (sec/km) typical of an elite marathoner:
        # both extrapolate to a similar 5k-equivalent pace -> low ratio -> aerobic_elite
        records = {"record_1500m": 180.0, "record_marathon": 213.3}
        result = compute_aerobic_profile(records)
        assert result["profile"] in ("aerobic_elite", "aerobic")

    def test_sprinter_profile_is_anaerobic_or_mixed(self):
        # Much faster short distance relative to long -> high ratio
        records = {"record_400m": 150.0, "record_marathon": 300.0}
        result = compute_aerobic_profile(records)
        assert result["profile"] in ("mixed", "anaerobic")


# --- best_race_reference ---

class TestBestRaceReference:

    def test_returns_none_without_any_record(self):
        request = FakeRequest()
        assert best_race_reference(request, 21.0975) is None

    def test_direct_record_is_flagged_as_direct(self):
        request = FakeRequest(record_half="1:30:00")
        ref = best_race_reference(request, 21.0975)
        assert ref is not None
        assert ref["is_direct"] is True

    def test_extrapolated_record_is_flagged_as_not_direct(self):
        request = FakeRequest(record_5000m="20:00")
        ref = best_race_reference(request, 21.0975)
        assert ref is not None
        assert ref["is_direct"] is False


# --- estimate_vma ---

class TestEstimateVma:

    def test_returns_none_without_records(self):
        assert estimate_vma({}) is None

    def test_returns_estimate_with_1500m(self):
        records = {"record_1500m": 180.0}
        result = estimate_vma(records)
        assert result is not None
        assert result["vma_kmh"] > 0

    def test_weighted_average_uses_available_methods_only(self):
        records = {"record_5000m": 240.0}
        result = estimate_vma(records)
        assert result is not None
        assert result["methods"][0][0] == "5000m"
