"""
core/rules/formulas.py
Calculates objective REFERENCES from records.
Pace zones are determined by LLM + RAG according to chosen philosophy.
"""

import re
from typing import Optional, Dict
from dataclasses import dataclass


# 1. PARSING
# ------------------------------------------------------------

def parse_time_to_seconds(time_str: str) -> Optional[float]:
    if not time_str or str(time_str).strip() in ("", "N/A", "n/a"):
        return None
    time_str = str(time_str).strip()
    m = re.match(r'^(\d+):(\d{2}):(\d{2})$', time_str)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    m = re.match(r'^(\d+):(\d{2})$', time_str)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    try:
        return float(time_str)
    except ValueError:
        return None


def seconds_to_pace_str(seconds_per_km: float) -> str:
    if not seconds_per_km or seconds_per_km <= 0:
        return "N/A"
    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}:{seconds:02d}/km"


def pace_to_kmh(seconds_per_km: float) -> float:
    return round(3600 / seconds_per_km, 2)


# 2. RIEGEL
# ------------------------------------------------------------

def riegel_pace(source_pace_s: float, source_dist_km: float, target_dist_km: float) -> float:
    """Predicts pace (sec/km) on target_dist from source_dist."""
    return source_pace_s * (target_dist_km / source_dist_km) ** 0.06


# 3. EXTRACTION OF RAW RECORDS
# ------------------------------------------------------------

# Distances in km associated with each attribute
RECORD_DISTANCES = {
    "record_400m":     0.4,
    "record_800m":     0.8,
    "record_1500m":    1.5,
    "record_5000m":    5.0,
    "record_10000m":   10.0,
    "record_half":     21.0975,
    "record_marathon": 42.195,
}

def extract_all_records(request) -> Dict[str, float]:
    """
    Returns all available records in sec/km (actual pace, no Riegel).
    Key = attribute name, value = sec/km.
    """
    records = {}
    for attr, dist_km in RECORD_DISTANCES.items():
        val = getattr(request, attr, None)
        if not val:
            continue
        secs = parse_time_to_seconds(str(val))
        if secs is not None:
            records[attr] = secs / dist_km  # actual pace in sec/km
    return records


# 4. AEROBIC/ANAEROBIC PROFILE
# ------------------------------------------------------------

def compute_aerobic_profile(records: Dict[str, float]) -> dict:
    """
    Calculates the aerobic/anaerobic ratio of the athlete.
    
    Principle: if the athlete is better at short distances (ratio > 1.15),
    they have an anaerobic profile (sprinter/middle-distance).
    If close to 1.0, pure aerobic profile (marathoner).
    
    Returns a dict with ratio and interpretation.
    """
    short_paces = []  # 400m, 800m, 1500m
    long_paces  = []  # 10k, half, marathon

    short_attrs = ["record_400m", "record_800m", "record_1500m"]
    long_attrs  = ["record_10000m", "record_half", "record_marathon"]

    for attr in short_attrs:
        if attr in records:
            # Extrapolate to 5k for uniformity
            short_paces.append(riegel_pace(records[attr], RECORD_DISTANCES[attr], 5.0))

    for attr in long_attrs:
        if attr in records:
            # Extrapolate to 5k for uniformity
            long_paces.append(riegel_pace(records[attr], RECORD_DISTANCES[attr], 5.0))

    if not short_paces or not long_paces:
        return {
            "ratio": None,
            "profile": "unknown",
            "description": "Undetermined profile - only one type of record available."
        }

    avg_short = sum(short_paces) / len(short_paces)
    avg_long  = sum(long_paces)  / len(long_paces)

    # ratio = long_pace / short_pace (> 1 = long slower = normal)
    # the higher the ratio, the more "anaerobic" the athlete
    ratio = avg_long / avg_short

    if ratio < 1.08:
        profile = "aerobic_elite"
        description = "Highly aerobic profile (pure marathoner). High aerobic base."
    elif ratio < 1.13:
        profile = "aerobic"
        description = "Balanced aerobic profile. Good half/marathon potential."
    elif ratio < 1.20:
        profile = "mixed"
        description = "Mixed aerobic/anaerobic profile. Strong on 5k-10k."
    else:
        profile = "anaerobic"
        description = "Anaerobic dominant profile (middle-distance/sprinter). Easy Run naturally faster relative to estimated half pace."

    return {
        "ratio": round(ratio, 3),
        "profile": profile,
        "description": description,
        "avg_short_5k_pace": seconds_to_pace_str(avg_short),
        "avg_long_5k_pace":  seconds_to_pace_str(avg_long),
    }


# 5. PRIMARY RACE REFERENCE
# ------------------------------------------------------------

def best_race_reference(request, target_dist_km: float = 21.0975) -> Optional[dict]:
    """
    Returns the reference pace on the target distance,
    from the most reliable record available.
    Priority: exact record > close distance > long extrapolation.
    """
    # Priority based on proximity to target distance
    if target_dist_km <= 5.0:
        priority_order = ["record_5000m", "record_1500m", "record_10000m",
                          "record_800m", "record_half", "record_400m", "record_marathon"]
    elif target_dist_km <= 10.0:
        priority_order = ["record_10000m", "record_5000m", "record_half",
                          "record_1500m", "record_marathon", "record_800m", "record_400m"]
    elif target_dist_km <= 21.0975:
        priority_order = ["record_half", "record_10000m", "record_marathon",
                          "record_5000m", "record_1500m", "record_800m", "record_400m"]
    else:
        priority_order = ["record_marathon", "record_half", "record_10000m",
                          "record_5000m", "record_1500m", "record_800m", "record_400m"]

    records = extract_all_records(request)

    for attr in priority_order:
        if attr not in records:
            continue
        source_dist = RECORD_DISTANCES[attr]
        source_pace = records[attr]

        if source_dist == target_dist_km:
            estimated_pace_s = source_pace
            is_direct = True
        else:
            estimated_pace_s = riegel_pace(source_pace, source_dist, target_dist_km)
            is_direct = False

        return {
            "source_record":   attr,
            "source_dist_km":  source_dist,
            "is_direct":       is_direct,
            "target_dist_km":  target_dist_km,
            "estimated_pace_s": estimated_pace_s,
            "estimated_pace":  seconds_to_pace_str(estimated_pace_s),
            "estimated_speed_kmh": pace_to_kmh(estimated_pace_s),
        }

    return None


# 6. ESTIMATED VO2MAX (multi-methods)
# ------------------------------------------------------------

def estimate_vma(records: Dict[str, float]) -> Optional[dict]:
    """
    Estimates VO2max from available records.
    Method: pace over 3-6 minutes ≈ VO2max (1500m record or extrapolation).
    
    Returns VO2max in km/h + method used.
    """
    estimates = []

    # Method 1: from 1500m (duration ~3:30-6:00 = close to VO2max)
    if "record_1500m" in records:
        vma_from_1500 = pace_to_kmh(records["record_1500m"] * 0.96)
        estimates.append(("1500m", vma_from_1500))

    # Method 2: from 5000m (Cooper: VO2max ≈ 5k pace / 0.875)
    if "record_5000m" in records:
        vma_from_5k = pace_to_kmh(records["record_5000m"] * 0.875)
        estimates.append(("5000m", vma_from_5k))

    # Method 3: from 10k (VO2max ≈ 10k pace / 0.82)
    if "record_10000m" in records:
        vma_from_10k = pace_to_kmh(records["record_10000m"] * 0.82)
        estimates.append(("10000m", vma_from_10k))

    if not estimates:
        return None

    # Weighted average (shorter distances are more reliable for VO2max)
    weights = {"1500m": 3, "5000m": 2, "10000m": 1}
    total_w = sum(weights[m] for m, _ in estimates)
    vma_weighted = sum(v * weights[m] for m, v in estimates) / total_w

    return {
        "vma_kmh":   round(vma_weighted, 1),
        "vma_pace":  seconds_to_pace_str(3600 / vma_weighted),
        "methods":   estimates,
        "note": "VO2max estimated from records - refine with field test (Vameval, Cooper...)",
    }


# 7. PROMPT BLOCK - REFERENCES ONLY
# ------------------------------------------------------------

def build_athlete_references_prompt(request, goal_dist_km: float = 21.0975) -> str:
    """
    Generates the OBJECTIVE REFERENCES block to inject into prompts.
    
    Does NOT contain fixed pace zones.
    LLM + RAG choose the philosophy and derive the zones.
    """
    records      = extract_all_records(request)
    race_ref     = best_race_reference(request, goal_dist_km)
    aerobic_prof = compute_aerobic_profile(records)
    vma_data     = estimate_vma(records)

    lines = ["=" * 55]
    lines.append("ATHLETE'S OBJECTIVE REFERENCES (Python calculated)")
    lines.append("=" * 55)

    # Raw available records
    if records:
        lines.append("\nPROVIDED RECORDS:")
        for attr, pace_s in records.items():
            dist = RECORD_DISTANCES[attr]
            total_s = pace_s * dist
            h = int(total_s // 3600)
            m = int((total_s % 3600) // 60)
            s = int(total_s % 60)
            time_str = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"
            lines.append(f"  - {attr.replace('record_', '').upper():10s} : {time_str}  ({seconds_to_pace_str(pace_s)})")
    else:
        lines.append("\nNo records provided.")

    # Race reference
    if race_ref:
        direct = "direct record" if race_ref["is_direct"] else f"extrapolated from {race_ref['source_record']}"
        lines.append(f"\nGOAL PACE ({goal_dist_km}km):")
        lines.append(f"  - {race_ref['estimated_pace']} ({race_ref['estimated_speed_kmh']} km/h) - {direct}")
    else:
        lines.append("\nGOAL PACE: undetermined (no record)")

    # Estimated VO2max
    if vma_data:
        lines.append(f"\nESTIMATED VO2max: ~{vma_data['vma_kmh']} km/h ({vma_data['vma_pace']})")
        lines.append(f"   {vma_data['note']}")

    # Aerobic profile
    lines.append(f"\nAEROBIC/ANAEROBIC PROFILE:")
    lines.append(f"  - Type    : {aerobic_prof['profile']}")
    lines.append(f"  - Ratio   : {aerobic_prof.get('ratio', 'N/A')}")
    lines.append(f"  - Analysis: {aerobic_prof['description']}")

    lines.append("\n" + "=" * 55)
    lines.append("INSTRUCTIONS FOR LLM:")
    lines.append("-" * 55)
    lines.append(
        "These values are REFERENCES, not rigid constraints.\n"
        "Use the method from RAG books to determine actual\n"
        "pace zones according to the chosen training philosophy.\n"
        "Adapt intensities to the athlete's aerobic profile.\n"
        "An 'anaerobic' profile will have a faster Easy Run relative\n"
        "to their half pace than an 'aerobic_elite' profile."
    )
    lines.append("=" * 55)

    return "\n".join(lines)