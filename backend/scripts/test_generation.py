#!/usr/bin/env python3
"""
scripts/test_generation.py
Complete API test - verifies:
1. JSON structure of the plan
2. Pace consistency (no more hallucinations)
3. Weekly volume consistency
4. RAG context quality
"""

import requests
import json
import re
from typing import Optional


API_URL = "http://localhost:8000"


# HELPERS
# ------------------------------------------------------------

def pace_to_seconds(pace_str: str) -> Optional[float]:
    """Converts 'mm:ss/km' to seconds."""
    m = re.match(r"(\d+):(\d{2})", pace_str or "")
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    return None


def validate_structure(plan: dict) -> tuple[bool, list]:
    """Checks the JSON structure of the plan."""
    errors = []
    required = ["total_km", "weeks", "coach_analysis"]
    for key in required:
        if key not in plan:
            errors.append(f"Missing key: '{key}'")

    if "weeks" in plan:
        for w in plan["weeks"]:
            if len(w.get("days", [])) != 7:
                errors.append(f"Week {w.get('week')}: {len(w.get('days', []))} days instead of 7")
            if "weekly_km" not in w:
                errors.append(f"Week {w.get('week')}: 'weekly_km' missing")

    return len(errors) == 0, errors


def validate_paces(plan: dict, half_pace_s: float) -> tuple[bool, list]:
    """
    Checks that plan paces are physiologically consistent.
    Easy Run max = half_pace x 1.35 | VO2max min = half_pace x 0.88
    """
    errors = []
    ef_max_s  = half_pace_s * 1.35   # Easy Run max
    vma_min_s = half_pace_s * 0.88   # VO2max min

    for w in plan.get("weeks", []):
        w_num = w.get("week", "?")
        for day in w.get("days", []):
            d_num = day.get("day", "?")
            for slot in ["morning", "afternoon"]:
                session = day.get(slot, {})
                stype   = session.get("type", "REST")
                if stype in ("REST", "STRENGTH", "Off"):
                    continue

                pace_str = session.get("pace", "")
                pace_s   = pace_to_seconds(pace_str)
                if not pace_s:
                    continue

                # Too fast for VO2max?
                if pace_s < vma_min_s - 10:
                    errors.append(
                        f"Week {w_num} Day {d_num} {slot}: "
                        f"pace {pace_str} TOO FAST "
                        f"(min VO2max allowed: {int(vma_min_s//60)}:{int(vma_min_s%60):02d}/km)"
                    )

                # Too slow for Easy Run?
                if stype == "EASY_RUN" and pace_s > ef_max_s + 30:
                    errors.append(
                        f"Week {w_num} Day {d_num} {slot}: "
                        f"pace {pace_str} very slow for a RUN"
                    )

    return len(errors) == 0, errors


def validate_volumes(plan: dict) -> tuple[bool, list]:
    """Checks volume consistency."""
    errors = []
    total_declared = plan.get("total_km", 0)
    total_calc     = sum(w.get("weekly_km", 0) for w in plan.get("weeks", []))

    if abs(total_declared - total_calc) > 5:
        errors.append(
            f"declared total_km ({total_declared}) != "
            f"sum of weekly_km ({round(total_calc, 1)})"
        )

    # Check logical progression
    volumes = [w.get("weekly_km", 0) for w in plan.get("weeks", [])]
    for i in range(1, len(volumes) - 2):
        if volumes[i] > volumes[i-1] * 1.15:
            errors.append(
                f"Week {i+1}: volume progression too fast "
                f"({volumes[i-1]}km -> {volumes[i]}km)"
            )

    return len(errors) == 0, errors


# TESTS
# ------------------------------------------------------------

def run_test(name: str, payload: dict, expected_half_pace_s: float = None):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(
            f"{API_URL}/plans/generate",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        plan = response.json()

        print(f"\nResponse received")
        print(f"   Weeks      : {len(plan.get('weeks', []))}")
        print(f"   Total volume: {plan.get('total_km', 0)} km")
        print(f"   Analysis   : {plan.get('coach_analysis', '')[:150]}...")

        # Test 1: Structure
        ok_struct, struct_errors = validate_structure(plan)
        print(f"\nJSON Structure: {'OK' if ok_struct else 'ERRORS'}")
        for e in struct_errors:
            print(f"   {e}")

        # Test 2: Paces
        if expected_half_pace_s:
            ok_paces, pace_errors = validate_paces(plan, expected_half_pace_s)
            print(f"\nPace consistency: {'OK' if ok_paces else 'HALLUCINATIONS DETECTED'}")
            for e in pace_errors:
                print(f"   {e}")
        
        # Test 3: Volumes
        ok_vol, vol_errors = validate_volumes(plan)
        print(f"\nVolume consistency: {'OK' if ok_vol else 'ERRORS'}")
        for e in vol_errors:
            print(f"   {e}")

        # Show an example session
        if plan.get("weeks"):
            week1 = plan["weeks"][0]
            day1  = week1.get("days", [{}])[0]
            print(f"\nExample session (Week1 Day1):")
            print(f"   Morning  : {day1.get('morning', {})}")
            print(f"   Afternoon: {day1.get('afternoon', {})}")

        return plan

    except requests.exceptions.Timeout:
        print("Timeout - API is taking too long to respond")
    except requests.exceptions.ConnectionError:
        print("API not accessible - run: python run.py")
    except Exception as e:
        print(f"Error: {e}")

    return None


def test_rag_retrieval():
    """Direct RAG test - verifies that books are properly queried."""
    print(f"\n{'='*60}")
    print("DIRECT RAG TEST")
    print(f"{'='*60}")

    try:
        from core.agents.retriever_agent import RetrieverAgent
        retriever = RetrieverAgent()

        result = retriever.run(
            goal_distance="half marathon",
            athlete_context="half 1h12 50km/week advanced level",
        )

        if result and len(result) > 100:
            print(f"RAG functional - {len(result)} characters retrieved")
            print(f"\nRAG context excerpt:")
            print(result[:500])
            print("...")
        else:
            print(f"RAG empty or insufficient: '{result}'")

    except Exception as e:
        print(f"RAG error: {e}")


# MAIN
# ------------------------------------------------------------

if __name__ == "__main__":
    print("COMPLETE TESTS - Running Coach SaaS")
    print("=" * 60)

    # Test 1 - Direct RAG
    test_rag_retrieval()

    # Test 2 - Elite athlete half 1h12
    # Half pace = 72min / 21.097km = 204s/km = 3:24/km
    run_test(
        name="Elite - Half 1h12 | 50km/week",
        payload={
            "age": 30,
            "gender": "M",
            "current_volume": 50,
            "current_frequency": 5,
            "goal_distance": "half",
            "goal_date": "2026-10-15",
            "availability": 5,
            "record_half": "1:12:00",
            "double_session": "no",
        },
        expected_half_pace_s=204,  # 3:24/km
    )

    # Test 3 - Beginner 10k
    run_test(
        name="Beginner - 10k | 30km/week",
        payload={
            "age": 35,
            "gender": "F",
            "current_volume": 30,
            "current_frequency": 3,
            "goal_distance": "10k",
            "goal_date": "2026-09-20",
            "availability": 3,
            "record_5000m": "28:00",
            "double_session": "no",
        },
        expected_half_pace_s=320,  # ~5:20/km
    )

    # Test 4 - Return from injury
    run_test(
        name="Return from injury - Marathon",
        payload={
            "age": 42,
            "gender": "M",
            "current_volume": 40,
            "current_frequency": 4,
            "goal_distance": "marathon",
            "goal_date": "2026-12-06",
            "availability": 4,
            "record_marathon": "3:15:00",
            "last_injury": "achilles tendinitis",
            "return_date": "2026-05-01",
            "double_session": "no",
        },
        expected_half_pace_s=276,  # ~4:36/km
    )

    print(f"\n{'='*60}")
    print("TESTS COMPLETE")
    print("=" * 60)