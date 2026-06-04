"""
core/rules/safety_rules.py

Two distinct layers:
  A) Informational warnings -> injected into LLM prompt
  B) Hard limits          -> validated on generated JSON plan (post-LLM)

Principle: the LLM is free to choose its philosophy.
But certain physiological rules are universal
and must be checked in code, not in prompt.
"""

from datetime import datetime, date
from typing import Tuple, List, Dict, Any, Optional


# LAYER A - INFORMATIONAL WARNINGS (context for LLM)
# ====================================================

def build_athlete_context_warnings(request) -> List[str]:
    """
    Generates contextual warnings injected into the prompt.
    The LLM uses them to adapt its philosophy - it is not forced.
    """
    warnings = []

    # Recent injury
    last_injury = getattr(request, "last_injury", None)
    return_date = getattr(request, "return_date", None)
    if last_injury and return_date:
        try:
            if isinstance(return_date, str):
                return_dt = datetime.strptime(return_date, "%Y-%m-%d").date()
            else:
                return_dt = return_date
            days = (date.today() - return_dt).days
            if days < 30:
                warnings.append(
                    f"RECENT RETURN FROM INJURY ({last_injury}, {days}d): "
                    "Very progressive volume, zero intense sessions for first 2 weeks."
                )
            elif days < 90:
                warnings.append(
                    f"RETURN FROM INJURY ({last_injury}, {days}d): "
                    "Progressive intensity, monitor warning signs."
                )
        except Exception:
            pass

    # Age
    age = getattr(request, "age", None)
    if age:
        if age >= 60:
            warnings.append(
                "ATHLETE 60+: Longer recovery between intense sessions. "
                "Prefer max 2 quality sessions per week. Sleep and nutrition critical."
            )
        elif age >= 50:
            warnings.append(
                "ATHLETE 50+: Allow 48-72h recovery after intense sessions. "
                "Adjust total volume if signs of accumulated fatigue."
            )
        elif age < 18:
            warnings.append(
                "JUNIOR ATHLETE: Limit high intensity sessions. "
                "Prioritize aerobic development and technique."
            )

    # Current volume
    vol = getattr(request, "current_volume", 0) or 0
    if vol > 150:
        warnings.append(
            f"HIGH VOLUME ({vol}km/week): Monitor signs of overload. "
            "Do not increase if chronic fatigue is present."
        )
    elif vol < 20:
        warnings.append(
            f"LOW VOLUME ({vol}km/week): Very gradual progression needed. "
            "Build aerobic base before introducing intensity."
        )

    # Time until goal
    goal_date = getattr(request, "goal_date", None)
    if goal_date:
        try:
            if isinstance(goal_date, str):
                goal_dt = datetime.strptime(goal_date, "%Y-%m-%d").date()
            else:
                goal_dt = goal_date
            weeks_left = (goal_dt - date.today()).days / 7
            if weeks_left < 6:
                warnings.append(
                    f"SHORT TIME FRAME ({weeks_left:.0f} weeks): "
                    "Maintenance/taper plan only. Do not increase volume."
                )
            elif weeks_left < 10:
                warnings.append(
                    f"LIMITED TIME FRAME ({weeks_left:.0f} weeks): "
                    "Priority to specificity. Little room to build base."
                )
        except Exception:
            pass

    # Frequency vs availability
    freq  = getattr(request, "current_frequency", 0) or 0
    avail = getattr(request, "availability", 0) or 0
    if avail < freq:
        warnings.append(
            f"FREQUENCY ({freq}d/w) > AVAILABILITY ({avail}d/w): "
            "Adapt plan to declared actual availability."
        )

    return warnings


# LAYER B - HARD LIMITS (POST-generation validation)
# ====================================================

INTENSE_TYPES = {"INTERVAL", "TEMPO", "THRESHOLD", "FARTLEK", "RACE", "VO2MAX"}
EASY_TYPES    = {"EASY_RUN", "RECOVERY", "EASY", "LONG_RUN", "REST", "CROSS"}

def classify_session(session_type: str) -> str:
    """Returns 'intense', 'easy', or 'unknown'."""
    t = session_type.upper().strip()
    if t in INTENSE_TYPES:
        return "intense"
    if t in EASY_TYPES:
        return "easy"
    return "unknown"


def validate_plan_hard_limits(
    plan_weeks: List[Dict],
    request,
    goal_dist_km: float = 21.0975,
) -> Dict[str, Any]:
    """
    Validates the generated JSON plan against physiological hard limits.
    
    Returns:
      {
        "valid": bool,
        "violations": [str],   # blocking errors
        "warnings": [str],     # non-blocking alerts
      }
    """
    violations = []
    warnings   = []

    if not plan_weeks:
        violations.append("Empty plan - no weeks generated.")
        return {"valid": False, "violations": violations, "warnings": warnings}

    weekly_volumes = []

    for week_data in plan_weeks:
        week_num    = week_data.get("week", "?")
        weekly_km   = week_data.get("weekly_km", 0) or 0
        days        = week_data.get("days", [])
        weekly_volumes.append(weekly_km)

        # Rule 1: 7 days per week
        if len(days) != 7:
            violations.append(
                f"Week {week_num}: {len(days)} days instead of 7."
            )

        # Rule 2: no two consecutive intense sessions
        for i in range(len(days) - 1):
            day_a = days[i]
            day_b = days[i + 1]

            sessions_a = _get_all_sessions(day_a)
            sessions_b = _get_all_sessions(day_b)

            a_intense = any(classify_session(s.get("type", "")) == "intense" for s in sessions_a)
            b_intense = any(classify_session(s.get("type", "")) == "intense" for s in sessions_b)

            if a_intense and b_intense:
                violations.append(
                    f"Week {week_num}, days {i+1}-{i+2}: "
                    "two consecutive intense sessions - insufficient recovery."
                )

        # Rule 3: at least 1 full rest or recovery day per week
        rest_days = 0
        for day in days:
            sessions = _get_all_sessions(day)
            if all(s.get("type", "").upper() in {"REST", "RECOVERY"} for s in sessions):
                rest_days += 1
        if rest_days == 0:
            warnings.append(
                f"Week {week_num}: no complete rest/recovery day."
            )

        # Rule 4: intensity/volume ratio
        intense_km = 0.0
        for day in days:
            for s in _get_all_sessions(day):
                if classify_session(s.get("type", "")) == "intense":
                    intense_km += s.get("km", 0) or 0
        if weekly_km > 0:
            ratio = intense_km / weekly_km
            if ratio > 0.30:
                warnings.append(
                    f"Week {week_num}: {ratio*100:.0f}% of volume at high intensity "
                    "(recommended < 25-30% per polarized method)."
                )

        # Rule 5: double session - no two intense on same day
        for day in days:
            day_num   = day.get("day", "?")
            morning   = day.get("morning", {})
            afternoon = day.get("afternoon", {})
            if (morning and afternoon and
                classify_session(morning.get("type", "")) == "intense" and
                classify_session(afternoon.get("type", "")) == "intense"):
                violations.append(
                    f"Week {week_num}, day {day_num}: "
                    "intense double session morning + afternoon - physiologically dangerous."
                )

    # Rule 6: inter-week volume progression
    for i in range(1, len(weekly_volumes)):
        prev = weekly_volumes[i - 1]
        curr = weekly_volumes[i]
        if prev > 0 and curr > prev * 1.15:
            warnings.append(
                f"Week {i+1}: +{((curr/prev)-1)*100:.0f}% progression "
                f"({prev:.0f}->{curr:.0f}km) exceeds recommended 10-15% threshold."
            )

    # Rule 7: deload week every 3-4 weeks
    decharge_found = _check_deload_weeks(weekly_volumes)
    if len(plan_weeks) >= 4 and not decharge_found:
        warnings.append(
            "No deload week detected (volume reduction >=15%). "
            "Recommended every 3-4 weeks for recovery."
        )

    # Rule 8: final taper
    if len(plan_weeks) >= 3:
        last_3 = weekly_volumes[-3:]
        if last_3[-1] > last_3[0] * 0.90:
            warnings.append(
                "Insufficient taper: volume in the last 2 weeks "
                "should be reduced by at least 20-30% before race."
            )

    valid = len(violations) == 0
    return {
        "valid":      valid,
        "violations": violations,
        "warnings":   warnings,
    }


# Internal helpers
# ------------------------------------------------------------

def _get_all_sessions(day: dict) -> List[dict]:
    """Returns all sessions for a day (morning + afternoon)."""
    sessions = []
    if day.get("morning"):
        sessions.append(day["morning"])
    if day.get("afternoon"):
        sessions.append(day["afternoon"])
    return sessions


def _check_deload_weeks(volumes: List[float]) -> bool:
    """
    Checks that there is at least one deload week
    (volume reduced by at least 15% from previous week).
    """
    for i in range(1, len(volumes)):
        if volumes[i] < volumes[i - 1] * 0.85:
            return True
    return False


# MAIN INTERFACE
# ====================================================

def apply_all_safety_checks(request) -> Tuple[List[str], dict]:
    """
    Backward compatibility with existing orchestrator.
    Returns (warnings_for_prompt, {}).
    Hard limits validation is called separately via validate_plan_hard_limits().
    """
    warnings = build_athlete_context_warnings(request)
    return warnings, {}