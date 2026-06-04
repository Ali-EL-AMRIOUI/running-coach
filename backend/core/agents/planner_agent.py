"""
core/agents/planner_agent.py

Generation by blocks of max 4 weeks per LLM call.
Drastically reduces token consumption.
"""

import json
import re
import logging
import time
from core.agents.base_agent import BaseAgent
from core.llm.prompts import PLANNER_BIDAILY_PROMPT

logger = logging.getLogger(__name__)

CHUNK_SIZE = 4  # weeks per LLM call - do not exceed


class PlannerAgent(BaseAgent):

    def run(
        self,
        request,
        analysis_context: str,
        weeks_count: int,
        directives: dict = None,
        previous_errors: list = None,
        **kwargs,
    ) -> dict:
        logger.info(f"PlannerAgent: {weeks_count} weeks (blocks of {CHUNK_SIZE})")

        if weeks_count <= CHUNK_SIZE:
            # Short plan - single call
            return self._run_single(
                request, analysis_context, weeks_count,
                directives, previous_errors,
                week_offset=0,
            )
        else:
            # Long plan - block generation
            return self._run_chunked(
                request, analysis_context, weeks_count,
                directives, previous_errors,
            )

    # BLOCK GENERATION (plans > 4 weeks)
    # ------------------------------------------------------------

    def _run_chunked(
        self,
        request,
        analysis_context: str,
        weeks_count: int,
        directives: dict,
        previous_errors: list,
    ) -> dict:
        all_weeks    = []
        rationale    = ""
        last_week_km = request.current_volume  # starting point

        for start in range(0, weeks_count, CHUNK_SIZE):
            end         = min(start + CHUNK_SIZE, weeks_count)
            chunk_size  = end - start
            chunk_index = start // CHUNK_SIZE + 1
            total_chunks = (weeks_count + CHUNK_SIZE - 1) // CHUNK_SIZE

            logger.info(f"  Block {chunk_index}/{total_chunks} - weeks {start+1} to {end}")

            # Continuity context from previous block
            chunk_directives = dict(directives or {})
            chunk_directives["total_weeks"]  = chunk_size
            chunk_directives["week_start"]   = start + 1
            chunk_directives["week_end"]     = end
            chunk_directives["global_total_weeks"] = weeks_count

            if all_weeks:
                last = all_weeks[-1]
                chunk_directives["previous_block_context"] = (
                    f"Previous block ended: week {start}, "
                    f"volume {last.get('weekly_km', last_week_km):.1f}km/week, "
                    f"phase '{last.get('phase', '?')}'. "
                    f"Continue progression from this point without rupture."
                )
                last_week_km = last.get("weekly_km", last_week_km)

            # Block generation with retry
            chunk_data = self._run_single_with_retry(
                request, analysis_context, chunk_size,
                chunk_directives, previous_errors,
                week_offset=start,
            )

            chunk_weeks = chunk_data.get("weeks", [])

            # Renumber correctly
            for i, w in enumerate(chunk_weeks):
                w["week"] = start + i + 1

            all_weeks.extend(chunk_weeks)

            if not rationale:
                rationale = chunk_data.get("coach_rationale", "")

            # Small pause between blocks to avoid rate limit
            if end < weeks_count:
                time.sleep(1.5)

        return {
            "coach_rationale": rationale,
            "weeks": all_weeks,
        }

    # SINGLE GENERATION WITH RETRY
    # ------------------------------------------------------------

    def _run_single_with_retry(
        self,
        request,
        analysis_context: str,
        weeks_count: int,
        directives: dict,
        previous_errors: list,
        week_offset: int = 0,
        max_attempts: int = 2,
    ) -> dict:
        last_error = None
        for attempt in range(max_attempts):
            try:
                return self._run_single(
                    request, analysis_context, weeks_count,
                    directives, previous_errors, week_offset,
                )
            except Exception as e:
                last_error = e
                logger.error(f"    Attempt {attempt+1}: {e}")
                if "429" in str(e):
                    # Rate limit - wait before retrying
                    wait = 60 * (attempt + 1)
                    logger.warning(f"    Rate limit - waiting {wait}s...")
                    time.sleep(wait)
                    raise   # do not retry on 429 - propagate to orchestrator
        raise last_error

    # SINGLE LLM CALL
    # ------------------------------------------------------------

    def _run_single(
        self,
        request,
        analysis_context: str,
        weeks_count: int,
        directives: dict = None,
        previous_errors: list = None,
        week_offset: int = 0,
    ) -> dict:

        directives_str = json.dumps(
            directives, indent=2, ensure_ascii=False
        ) if directives else "{}"

        errors_str = ""
        if previous_errors:
            errors_str = (
                "MANDATORY CORRECTIONS - the previous plan contained these errors:\n"
                + "\n".join(f"  - {e}" for e in previous_errors)
                + "\nFix them absolutely in this new version."
            )

        prompt = PLANNER_BIDAILY_PROMPT
        for key, value in {
            "{athlete_metrics}":   analysis_context,
            "{directives}":        directives_str,
            "{current_volume}":    str(request.current_volume),
            "{current_frequency}": str(request.current_frequency),
            "{previous_errors}":   errors_str or "No previous errors - first generation.",
            "{weeks_count}":       str(weeks_count), 
        }.items():
            prompt = prompt.replace(key, value)

        # Create messages for cascade
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a world-class expert running coach. "
                    "You generate personalized JSON training plans "
                    "based on the athlete's real profile and the scientific methods "
                    "of the world's best experts. "
                    "ABSOLUTE RULES: "
                    "(1) Vary intensities day by day - never two identical consecutive sessions. "
                    "(2) Calculate weekly_km by summing actual km from all days, never estimate it in advance. "
                    "(3) Never N/A for an active session - always a pace range. "
                    "(4) After an intense session -> next day must be REST, RECOVERY, or EASY RUN. "
                    "Return ONLY valid raw JSON, no text before or after."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        # THE MAGIC CALL: Pass through BaseAgent cascade instead of self.client
        raw = self.execute_with_fallback(messages)

        # Clean response
        raw = raw.strip()
        raw = re.sub(r"^```json\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"^```\s*|```$", "", raw)

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON in response.")

        data = json.loads(match.group(0))

        # Default phase if missing
        if "weeks" in data:
            total_global = directives.get("global_total_weeks", weeks_count) if directives else weeks_count
            for i, week in enumerate(data["weeks"]):
                if "phase" not in week:
                    global_i = week_offset + i
                    if   global_i < total_global * 0.40: week["phase"] = "Base"
                    elif global_i < total_global * 0.75: week["phase"] = "Specific"
                    elif global_i < total_global * 0.90: week["phase"] = "Taper"
                    else:                                week["phase"] = "Race Week"

        return data