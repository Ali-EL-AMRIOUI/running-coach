# core/agents/analyzer_agent.py

"""
Rôle : analyse stratégique UNIQUEMENT.
- Choisit UNE philosophie cohérente depuis le RAG
- Donne des directives de structure (phases, types séances, progression)
- Ne définit PAS les allures → c'est le LLM+RAG qui les dérive
  depuis les références objectives (allure de course, VMA, profil)
"""

import logging
from core.agents.base_agent import BaseAgent
from core.rules.formulas import (
    build_athlete_references_prompt,
    compute_aerobic_profile,
    extract_all_records,
    estimate_vma,
    best_race_reference,
    RECORD_DISTANCES,
)

logger = logging.getLogger(__name__)


class AnalyzerAgent(BaseAgent):

    def run(
        self,
        request,
        knowledge_context: str = None,
        extra_context: dict = None,
    ) -> str:
        logger.info("🧠 AnalyzerAgent : analyse stratégique...")

        if not knowledge_context:
            knowledge_context = "Aucune connaissance scientifique disponible."

        extra_context = extra_context or {}

        # ── Références objectives depuis le nouveau formulas.py ──────
        # Ces références sont des faits bruts, pas des zones imposées
        references_block = extra_context.get(
            "references_block",
            build_athlete_references_prompt(request)
        )

        # Profil aérobie calculé
        all_records  = extract_all_records(request)
        aerobic_prof = compute_aerobic_profile(all_records)
        vma_data     = estimate_vma(all_records)

        profile_label = {
            "aerobic_elite": "Profil aérobie élite (marathonien pur)",
            "aerobic":       "Profil aérobie équilibré (bon semi/marathon)",
            "mixed":         "Profil mixte (5k-10k dominant)",
            "anaerobic":     "Profil anaérobie (demi-fondeur/sprinteur)",
            "unknown":       "Profil indéterminé (records insuffisants)",
        }.get(aerobic_prof.get("profile", "unknown"), "Profil indéterminé")

        # Warnings contextuels
        safety_context = ""
        warnings = extra_context.get("safety_warnings", [])
        if warnings:
            safety_context = "\nPOINTS D'ATTENTION ATHLÈTE :\n" + \
                "\n".join(f"  • {w}" for w in warnings)

        # VMA context
        vma_context = ""
        if vma_data:
            vma_context = (
                f"VMA estimée : ~{vma_data['vma_kmh']} km/h "
                f"({vma_data['vma_pace']}) — depuis {[m for m,_ in vma_data['methods']]}"
            )

        prompt = f"""Tu es un coach expert en physiologie de l'endurance.
Ta mission : analyser le profil de l'athlète et choisir UNE philosophie
d'entraînement cohérente depuis les méthodes des experts.

══════════════════════════════════════════════════
PROFIL ATHLÈTE
══════════════════════════════════════════════════
Objectif    : {request.goal_distance}
Âge         : {request.age} ans | Sexe : {request.gender}
Volume      : {request.current_volume} km/sem
Fréquence   : {request.current_frequency} séances/sem
Double séance : {request.double_session}
Blessure    : {getattr(request, 'last_injury', 'Aucune') or 'Aucune'}
Reprise     : {getattr(request, 'return_date', 'N/A') or 'N/A'}
Années pratique : {getattr(request, 'years_practice', 'N/A') or 'N/A'}
Records     : {self._format_records(request)}

PROFIL PHYSIOLOGIQUE CALCULÉ :
  • Catégorie : {profile_label}
  • {aerobic_prof.get('description', '')}
  • {vma_context}
{safety_context}

══════════════════════════════════════════════════
RÉFÉRENCES OBJECTIVES (calculées depuis les records)
══════════════════════════════════════════════════
{references_block}

IMPORTANT : Ces valeurs sont des RÉFÉRENCES BRUTES.
Tu vas choisir une philosophie d'entraînement dans les livres ci-dessous
et dériver les zones d'intensité selon cette philosophie et le profil
aérobie/anaérobie de l'athlète.
Un profil anaérobie aura une EF naturellement plus rapide
(en % de son allure de course) qu'un profil aérobie élite.

══════════════════════════════════════════════════
MÉTHODES EXPERTES — LIVRES (RAG)
══════════════════════════════════════════════════
{knowledge_context[:4000]}

══════════════════════════════════════════════════
MISSION
══════════════════════════════════════════════════
Rédige une analyse stratégique (250-300 mots) :

1. NIVEAU PHYSIOLOGIQUE
   Évalue le niveau réel de l'athlète depuis ses records ET son profil
   aérobie/anaérobie. Un athlète 1500m avec semi estimé à 1h05 n'est pas
   le même profil qu'un marathonien à 1h05.

2. PHILOSOPHIE D'ENTRAÎNEMENT CHOISIE
   Choisis UNE méthode cohérente depuis les livres RAG.
   Justifie ce choix selon le profil ET l'objectif.
   Exemples : Seiler 80/20 si profil aérobie, Daniels VDOT si profil mixte,
   Lydiard base si débutant, Canova spécifique si élite semi.
   ⚠️ Une seule philosophie — pas un mélange incohérent.

3. ZONES D'INTENSITÉ SELON LA PHILOSOPHIE CHOISIE
   Dérive les zones depuis l'allure de référence ET la philosophie.
   Exemples :
   - Seiler → EF = allure conversationnelle (~65-72% VMA)
   - Daniels → zones VDOT depuis l'allure de course
   - Lydiard → base aérobie longue (pas de % fixe, ressenti)
   Adapte au profil : anaérobie → EF plus rapide en % VMA.

4. STRUCTURE HEBDOMADAIRE
   Types de séances, ratio intensité/volume, jours clés.

5. PROGRESSION VOLUME
   Volume de départ réaliste, progression semaine par semaine,
   semaines de décharge, taper.

6. POINTS DE VIGILANCE
   Blessures, âge, retour de blessure, surcharge.

══════════════════════════════════════════════════
TERMINE PAR CE BLOC JSON EXACT (rien après)
══════════════════════════════════════════════════

DIRECTIVES_PLANNER:
{{
  "philosophie": "<méthode choisie et pourquoi>",
  "source_rag": "<livre(s) utilisé(s)>",
  "phases": ["<phase 1>", "<phase 2>", "<phase 3>"],
  "volume_depart_km": <nombre>,
  "volume_pic_km": <nombre>,
  "ratio_intensite": "<ex: 80% facile 20% intense>",
  "seances_cles": ["<séance 1>", "<séance 2>", "<séance 3>"],
  "zones_intensite": {{
    "description": "<comment les zones sont définies selon la philosophie>",
    "ef_description": "<description EF selon la méthode, ex: allure conversationnelle>",
    "seuil_description": "<description seuil selon la méthode>",
    "vma_description": "<description VMA/interval selon la méthode>"
  }},
  "variation_journaliere": "<règle de variation: ex: après séance intense → EF obligatoire>",
  "points_vigilance": ["<point 1>", "<point 2>"],
  "profil_aerobique": "{aerobic_prof.get('profile', 'unknown')}",
  "double_session": "{request.double_session}",
  "double_session_days": "{getattr(request, 'double_session_days', 'N/A')}"
}}"""

        # Structuration des messages attendus par l'execute_with_fallback
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es un coach expert en physiologie de l'endurance. "
                    "Tu analyses le profil complet de l'athlète et choisis "
                    "UNE philosophie d'entraînement cohérente depuis les livres. "
                    "Tu ne hardcodes JAMAIS de pourcentages d'allure — "
                    "tu laisses la philosophie choisie définir les zones "
                    "en fonction du profil aérobie/anaérobie de l'athlète. "
                    "Le JSON DIRECTIVES_PLANNER doit être valide et complet."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        # ✅ Utilisation de notre méthode globale robuste et centralisée
        return self.execute_with_fallback(messages)

    def _format_records(self, request) -> str:
        records = []
        fields = [
            ("400m", "record_400m"), ("800m", "record_800m"),
            ("1500m", "record_1500m"), ("5km", "record_5000m"),
            ("10km", "record_10000m"), ("Semi", "record_half"),
            ("Marathon", "record_marathon"),
        ]
        for dist, attr in fields:
            val = getattr(request, attr, None)
            if val and str(val).strip() not in ("", "N/A"):
                records.append(f"{dist}: {val}")
        return ", ".join(records) if records else "Non fournis"