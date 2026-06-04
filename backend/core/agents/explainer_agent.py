# core/agents/explainer_agent.py

import logging
from core.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Key session types to highlight
KEY_SESSION_TYPES = {"INTERVAL", "TEMPO", "THRESHOLD", "RACE_PACE", "HILL_REPS"}


class ExplainerAgent(BaseAgent):

    def run(self, plan_data: dict) -> str:
        logger.info("ExplainerAgent: generating explanation...")

        total_km = plan_data.get("total_km", "?")
        weeks    = plan_data.get("weeks", [])
        n_weeks  = len(weeks)

        # Present phases
        phases = list({
            w.get("phase", "")
            for w in weeks if w.get("phase")
        })

        # Planner rationale if available
        rationale = plan_data.get("coach_rationale", "")[:300]

        # Extract key sessions with their paces
        key_sessions = self._extract_key_sessions(weeks)

        # Volume by phase for context
        phase_summary = self._summarize_phases(weeks)

        prompt = f"""You are an expert running coach, educational and motivating.

TRAINING PLAN:
- Duration    : {n_weeks} weeks
- Total volume: {total_km} km
- Phases      : {', '.join(phases) if phases else 'Not specified'}
- Logic       : {rationale or 'Personalized plan based on athlete profile'}

SUMMARY BY PHASE:
{phase_summary}

KEY SESSIONS IN THE PLAN:
{key_sessions}

Write a warm and motivating explanation in ENGLISH (180-220 words):

1. PLAN LOGIC: explain why these phases appear in this order
   (e.g., "The first 4 weeks build your aerobic base...")

2. KEY SESSIONS: cite 2-3 concrete sessions from the plan with their real
   physiological benefit (use the sessions extracted above)

3. VARIATION: explain why intensities vary day by day
   (recovery, adaptation, supercompensation)

4. INJURY PREVENTION TIPS: 2 concrete tips specific to the plan

5. MOTIVATION: one personalized final sentence of encouragement

Use only the sessions and paces present in the plan.
Do not mention any pace you have not seen in the data."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"ExplainerAgent: {e}")
            return (
                "Plan generated successfully. Respect the indicated paces, "
                "recover well between intense sessions, "
                "and progress week by week. Happy training."
            )

    def _extract_key_sessions(self, weeks: list) -> str:
        """Extracts key sessions with details and paces - max 5."""
        found = []
        for week in weeks:
            if len(found) >= 5:
                break
            for day in week.get("days", []):
                for slot_name in ("morning", "afternoon"):
                    slot = day.get(slot_name, {}) or {}
                    if slot.get("type", "") in KEY_SESSION_TYPES:
                        phase   = week.get("phase", "")
                        details = slot.get("details", "")[:120]
                        pace    = slot.get("pace", "N/A")
                        found.append(
                            f"  - [{phase}] {slot.get('type')} "
                            f"— {details} (pace: {pace})"
                        )
                    if len(found) >= 5:
                        break

        return "\n".join(found) if found else "  - Mostly easy aerobic running sessions"

    def _summarize_phases(self, weeks: list) -> str:
        """Summarizes volume and dominant session types by phase."""
        phase_data: dict = {}
        for week in weeks:
            phase = week.get("phase", "Unknown")
            km    = week.get("weekly_km", 0) or 0
            if phase not in phase_data:
                phase_data[phase] = {"weeks": 0, "total_km": 0.0}
            phase_data[phase]["weeks"]    += 1
            phase_data[phase]["total_km"] += km

        lines = []
        for phase, data in phase_data.items():
            avg = data["total_km"] / data["weeks"] if data["weeks"] else 0
            lines.append(
                f"  - {phase}: {data['weeks']} weeks, "
                f"avg {avg:.0f}km/week, total {data['total_km']:.0f}km"
            )
        return "\n".join(lines) if lines else "  - Data not available"