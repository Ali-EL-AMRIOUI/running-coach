# core/rules/progression_rules.py
"""
Progression rules - REFERENCES only.
LLM + RAG generate actual volumes.
Python provides safety bounds and detects level.
"""

from typing import Optional
from core.rules.formulas import parse_time_to_seconds


# LEVEL DETECTION
# ------------------------------------------------------------

def detect_level(
    current_volume: float,
    record_half: str = None,
    record_marathon: str = None,
    record_10k: str = None,
    years_practice: int = None,
) -> str:
    """
    Detects level from available records.
    Priority: half_record > 10k_record > marathon_record > volume > years
    """
    # From half marathon
    if record_half:
        secs = parse_time_to_seconds(record_half)
        if secs:
            if secs < 4500:    return "elite"        # < 1h15
            elif secs < 4800:  return "advanced"     # < 1h20
            elif secs < 5400:  return "intermediate" # < 1h30
            else:              return "beginner"

    # From 10k
    if record_10k:
        secs = parse_time_to_seconds(record_10k)
        if secs:
            if secs < 2100:    return "elite"        # < 35min
            elif secs < 2400:  return "advanced"     # < 40min
            elif secs < 2700:  return "intermediate" # < 45min
            else:              return "beginner"

    # From marathon
    if record_marathon:
        secs = parse_time_to_seconds(record_marathon)
        if secs:
            if secs < 9000:    return "elite"        # < 2h30
            elif secs < 10800: return "advanced"     # < 3h00
            elif secs < 13200: return "intermediate" # < 3h40
            else:              return "beginner"

    # Fallback volume
    if current_volume >= 100: return "elite"
    if current_volume >= 70:  return "advanced"
    if current_volume >= 40:  return "intermediate"
    return "beginner"


# PROGRESSION BOUNDS (safety only)
# ------------------------------------------------------------

# Max weekly progression rate by level
# These values are SAFETY CEILINGS - not targets
MAX_PROGRESSION_RATE = {
    "beginner":     0.10,  # +10% max
    "intermediate": 0.12,  # +12% max
    "advanced":     0.15,  # +15% max
    "elite":        0.15,  # +15% max (they can handle it)
}

# Reasonable MAX peak volume by goal and level
MAX_PEAK_VOLUME = {
    "5k":       {"beginner": 50,  "intermediate": 70,  "advanced": 90,  "elite": 120},
    "10k":      {"beginner": 60,  "intermediate": 80,  "advanced": 100, "elite": 130},
    "half":     {"beginner": 70,  "intermediate": 90,  "advanced": 120, "elite": 160},
    "marathon": {"beginner": 80,  "intermediate": 100, "advanced": 140, "elite": 200},
}


def get_progression_bounds(
    current_volume: float,
    goal_distance: str,
    level: str,
) -> dict:
    """
    Returns progression bounds to inject into LLM context
    AND to use as hard limits in safety_rules.py.
    """
    dist  = goal_distance.lower().replace("-", "").replace(" ", "")
    rate  = MAX_PROGRESSION_RATE.get(level, 0.10)
    peaks = MAX_PEAK_VOLUME.get(dist, MAX_PEAK_VOLUME["half"])
    peak  = peaks.get(level, current_volume * 1.4)

    return {
        "level":               level,
        "max_weekly_increase": rate,
        "max_peak_volume_km":  peak,
        "current_volume_km":   current_volume,
        "note": (
            "These values are SAFETY CEILINGS. "
            "The LLM may choose a more conservative progression "
            "according to the chosen RAG method."
        ),
    }


def build_progression_prompt_block(
    current_volume: float,
    goal_distance: str,
    level: str,
) -> str:
    """Text block to inject into the Analyzer prompt."""
    bounds = get_progression_bounds(current_volume, goal_distance, level)
    return f"""
PROGRESSION BOUNDS (safety - do not exceed):
  - Detected level    : {bounds['level']}
  - Max progression   : +{bounds['max_weekly_increase']*100:.0f}% per week
  - Max peak volume   : {bounds['max_peak_volume_km']} km/week
  - Current volume    : {bounds['current_volume_km']} km/week
  Note: these values are ceilings. The RAG philosophy
  may choose a more conservative progression.
""".strip()