"""
core/agents/validator_agent.py

Two levels of validation:
  1. JSON Structure        -> format, required fields, km consistency
  2. Session consistency   -> variation, consecutive types, relative paces
     (absolute physiological hard limits -> safety_rules.validate_plan_hard_limits)
"""

import re
import logging
from typing import Tuple, List, Optional, Dict

from core.rules.safety_rules import validate_plan_hard_limits

logger = logging.getLogger(__name__)

# Types that are not running sessions
NON_RUNNING_TYPES = {
    "REST", "RECOVERY", "REST_ACTIVE",
    "STRENGTH", "CROSS",
    # legacy
    "Off", "rest", "off",
}

# Intense types - for relative consistency validation
INTENSE_TYPES = {
    "INTERVAL", "TEMPO", "THRESHOLD",
    "FARTLEK", "RACE_PACE", "HILL_REPS",
}

# Intensity hierarchy for relative validation
# Lower score = slower session
INTENSITY_RANK: Dict[str, int] = {
    "REST":        0,
    "RECOVERY":    1,
    "REST_ACTIVE": 1,
    "EASY_RUN":    2,
    "LONG_RUN":    2,
    "EA":          3,
    "FARTLEK":     3,
    "STRIDES":     3,
    "HILL_REPS":   4,
    "TEMPO":       4,
    "THRESHOLD":   5,
    "RACE_PACE":   5,
    "INTERVAL":    6,
}

VALID_TYPES = set(INTENSITY_RANK.keys())


def parse_pace_range(pace_str: str) -> Optional[Tuple[float, float]]:
    """
    Parse a pace range.
    Accepts: "4:15-4:30/km", "4:15/km", "4:15"
    Returns (min_s, max_s) or None.
    """
    if not pace_str or pace_str.strip() in ("N/A", "n/a", ""):
        return None

    # Range: "4:15-4:30/km"
    m = re.match(r"(\d+):(\d{2})\s*[-–]\s*(\d+):(\d{2})", pace_str)
    if m:
        fast_s = int(m.group(1)) * 60 + int(m.group(2))
        slow_s = int(m.group(3)) * 60 + int(m.group(4))
        return (min(fast_s, slow_s), max(fast_s, slow_s))

    # Single pace: "4:15/km" or "4:15"
    m = re.match(r"(\d+):(\d{2})", pace_str)
    if m:
        s = int(m.group(1)) * 60 + int(m.group(2))
        return (s, s)

    return None


def pace_range_center(pace_str: str) -> Optional[float]:
    """Center of the pace range in seconds."""
    r = parse_pace_range(pace_str)
    if r:
        return (r[0] + r[1]) / 2
    return None


class ValidatorAgent:

    def run(
        self,
        plan_data: dict,
        request,
        zones: dict = None,     # kept for backward compatibility, no longer used
        goal_dist_km: float = 21.0975,
    ) -> Tuple[bool, List[str]]:

        logger.info("ValidatorAgent: structure + consistency validation...")
        errors   = []
        warnings = []

        # Minimal safeguard
        if not isinstance(plan_data, dict) or "weeks" not in plan_data:
            return False, ["Key 'weeks' missing in JSON."]

        double_allowed = str(getattr(request, "double_session", "no")).lower()
        total_km_calc  = 0.0

        for w_idx, week in enumerate(plan_data["weeks"]):
            w_num    = week.get("week", w_idx + 1)
            days     = week.get("days", [])
            weekly_km = week.get("weekly_km", 0) or 0
            total_km_calc += weekly_km

            # 1. 7 days required
            if len(days) != 7:
                errors.append(
                    f"Week {w_num}: {len(days)} days instead of 7."
                )

            # 2. Real km vs declared km consistency
            real_km = round(sum(
                (day.get("morning",   {}) or {}).get("km", 0)
                + (day.get("afternoon", {}) or {}).get("km", 0)
                for day in days
            ), 1)
            if weekly_km > 0 and abs(real_km - weekly_km) > 8:
                errors.append(
                    f"Week {w_num}: {real_km}km actual vs {weekly_km}km declared "
                    f"(difference {abs(real_km - weekly_km):.1f}km)."
                )

            # Collect sessions for inter-day analysis
            day_sessions = []  # [(morning_type, afternoon_type), ...]

            for day in days:
                d_num = day.get("day", "?")
                morning   = day.get("morning")   or {}
                afternoon = day.get("afternoon") or {}

                # 3. Required fields
                if "morning" not in day or "afternoon" not in day:
                    errors.append(
                        f"Week {w_num} Day {d_num}: morning or afternoon missing."
                    )
                    day_sessions.append(("REST", "REST"))
                    continue

                m_type = (morning.get("type")   or "REST").upper().strip()
                a_type = (afternoon.get("type") or "REST").upper().strip()
                day_sessions.append((m_type, a_type))

                # 4. Valid types
                for slot_name, stype in [("morning", m_type), ("afternoon", a_type)]:
                    if stype not in VALID_TYPES:
                        errors.append(
                            f"Week {w_num} Day {d_num} {slot_name}: "
                            f"unknown type '{stype}'. "
                            f"Valid types: {sorted(VALID_TYPES)}"
                        )

                # 5. Double session not allowed
                if double_allowed == "no":
                    m_run = m_type not in NON_RUNNING_TYPES
                    a_run = a_type not in NON_RUNNING_TYPES
                    if m_run and a_run:
                        errors.append(
                            f"Week {w_num} Day {d_num}: double session "
                            f"({m_type}+{a_type}) not allowed."
                        )

                # 6. Intense double session morning+afternoon
                if (m_type in INTENSE_TYPES and a_type in INTENSE_TYPES):
                    errors.append(
                        f"Week {w_num} Day {d_num}: INTENSE double session "
                        f"({m_type}+{a_type}) - physiologically dangerous."
                    )

                # 7. Pace consistency vs session type
                for slot_name, slot, stype in [
                    ("morning",   morning,   m_type),
                    ("afternoon", afternoon, a_type),
                ]:
                    if stype in NON_RUNNING_TYPES:
                        continue

                    pace_str = slot.get("pace", "")
                    pace_r   = parse_pace_range(pace_str)

                    # Pace range required for running sessions
                    if not pace_r and stype not in NON_RUNNING_TYPES:
                        warnings.append(
                            f"Week {w_num} Day {d_num} {slot_name}: "
                            f"pace missing or invalid format ('{pace_str}')."
                        )

                    # km = 0 for non-REST session -> suspicious
                    km = slot.get("km", 0) or 0
                    if km == 0 and stype not in NON_RUNNING_TYPES:
                        errors.append(
                            f"Week {w_num} Day {d_num} {slot_name}: "
                            f"type {stype} but km=0."
                        )

                    # details required for intense sessions
                    if stype in INTENSE_TYPES:
                        details = slot.get("details", "")
                        if not details or len(details) < 20:
                            warnings.append(
                                f"Week {w_num} Day {d_num} {slot_name}: "
                                f"session {stype} without sufficient details."
                            )

            # 8. Inter-day relative consistency
            # Verifies that intensity varies (not same rank for 3 consecutive days)
            self._check_consecutive_intensity(
                day_sessions, w_num, errors, warnings
            )

        # 9. total_km consistency
        declared_total = plan_data.get("total_km", 0) or 0
        if declared_total > 0 and abs(declared_total - total_km_calc) > 15:
            warnings.append(
                f"declared total_km ({declared_total}) != "
                f"sum of weekly_km ({round(total_km_calc, 1)})."
            )

        # 10. Physiological hard limits (safety_rules)
        hard = validate_plan_hard_limits(
            plan_weeks   = plan_data.get("weeks", []),
            request      = request,
            goal_dist_km = goal_dist_km,
        )
        errors.extend(hard.get("violations", []))
        warnings.extend(hard.get("warnings",  []))

        # Log
        if warnings:
            for w in warnings:
                logger.warning(f"{w}")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info("Plan valid (structure + consistency + hard limits)")
        else:
            logger.warning(f"{len(errors)} error(s), {len(warnings)} warning(s)")

        return is_valid, errors

    # Helpers
    # ------------------------------------------------------------

    def _check_consecutive_intensity(
        self,
        day_sessions: List[Tuple[str, str]],
        week_num,
        errors: List[str],
        warnings: List[str],
    ) -> None:
        """
        Verifies there are no 3 consecutive days at the same intensity rank
        and that after INTENSE there is REST or EASY_RUN/RECOVERY.
        """
        def day_rank(m_type: str, a_type: str) -> int:
            # Ignore recovery/rest slots to evaluate day intensity
            active_ranks = [
                INTENSITY_RANK.get(t, 2)
                for t in (m_type, a_type)
                if t not in NON_RUNNING_TYPES
            ]
            return max(active_ranks) if active_ranks else 0

        ranks = [day_rank(m, a) for m, a in day_sessions]

        for i in range(len(ranks)):
            # After intense (>=4) -> next day must be <= 2
            if ranks[i] >= 4 and i + 1 < len(ranks):
                if ranks[i + 1] >= 4:
                    errors.append(
                        f"Week {week_num}, days {i+1}-{i+2}: "
                        f"two consecutive intense sessions "
                        f"({day_sessions[i][0]}/{day_sessions[i][1]} -> "
                        f"{day_sessions[i+1][0]}/{day_sessions[i+1][1]})."
                    )

            # 3 consecutive identical Easy Run days
            if i >= 2 and ranks[i] == ranks[i-1] == ranks[i-2] == 2:
                warnings.append(
                    f"Week {week_num}, days {i}-{i+2}: "
                    f"3 consecutive days same Easy Run level - vary intensity or duration."
                )