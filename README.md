# AI Running Coach

> SaaS platform for AI-powered, science-based running training plans.
> Generates personalized periodized plans for athletes of all levels — beginner to elite.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST /plans/generate                                            │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   AgentOrchestrator                       │   │
│  │                                                           │   │
│  │  1. formulas.py       → objective references from PRs    │   │
│  │  2. progression_rules → safety bounds (level detection)  │   │
│  │  3. safety_rules      → contextual warnings (Layer A)    │   │
│  │  4. RetrieverAgent    → RAG (9 expert books, Qdrant)     │   │
│  │  5. AnalyzerAgent     → philosophy selection + profile   │   │
│  │  6. PlannerAgent      → JSON plan generation (4-wk chunks│   │
│  │  7. ValidatorAgent    → structure + hard limits (Layer B) │   │
│  │  8. ExplainerAgent    → pedagogical explanation          │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  TrainingPlanSchema (structured JSON)                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

**RAG < Code < RAG** — a 3-layer hierarchy:

| Layer | Responsibility | Implementation |
|-------|---------------|----------------|
| Python (pre-LLM) | Objective references, safety bounds | `formulas.py`, `progression_rules.py` |
| RAG + LLM | Philosophy selection, intensity zones, plan structure | `analyzer_agent.py`, `planner_agent.py` |
| Python (post-LLM) | Hard limit validation, structural integrity | `safety_rules.py`, `validator_agent.py` |

Python never hardcodes training zones. The LLM chooses one coherent philosophy from the RAG knowledge base (Seiler, Daniels, Lydiard, Canova...) and derives zones from objective athlete references.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM (primary) | Groq — `llama-3.3-70b-versatile` |
| LLM (fallback) | Groq `qwen/qwen3-32b` → `llama-4-scout` → Gemini `2.0-flash` |
| Embeddings | Infinity + `BAAI/bge-m3` (1024 dims) |
| Re-ranking | `BAAI/bge-reranker-v2-m3` via Infinity |
| Vector DB | Qdrant Cloud (4849 chunks indexed) |
| Backend | FastAPI + SQLAlchemy + SQLite |
| Auth | JWT (python-jose) |
| Frontend | Next.js 14 + Tailwind CSS |
| Payments | Stripe |

---

## RAG Knowledge Base

9 expert books indexed in Qdrant:

| Book | Author | Method |
|------|--------|--------|
| Daniels' Running Formula | Jack Daniels | VDOT, intensity zones |
| Advanced Marathoning | Pete Pfitzinger | Advanced marathon plans |
| Science of Running | Steve Magness | Performance physiology |
| Training for the Uphill Athlete | Kilian Jornet et al. | Aerobic endurance |
| Lydiard Running | Arthur Lydiard | Aerobic base, periodization |
| Does Polarized Training Improve Performance | Seiler et al. | Polarized training |
| Seiler 2011 | Stephen Seiler | 80/20 distribution |
| The Future of Endurance Training | Stephen Seiler | Modern methods |
| Science of Running (PDF) | Steve Magness | Biomechanics |

---

## Installation

### Prerequisites

- Python 3.12+
- Node.js 18+ (frontend)
- NVIDIA GPU (recommended for Infinity embeddings)
- Qdrant Cloud account (free tier available)
- Groq Cloud account (free tier — 100k tokens/day per model)
- Gemini API key (recommended fallback — 1500 req/day free)

### 1. Clone

```bash
git clone https://github.com/Ali-EL-AMRIOUI/running-coach.git
cd running-coach
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Linux/Mac
# venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 3. Environment variables

```bash
cp .env.template .env
```

```env
# LLM
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxx   # fallback — recommended

# Vector DB
QDRANT_URL=https://xxxx.us-east4-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Embeddings
INFINITY_URL=http://localhost:7997

# App
DATABASE_URL=sqlite:///./running_coach.db
SECRET_KEY=change-this-to-a-random-secret-key

# Payments (optional)
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxx
```

### 4. Start Infinity embedding server

```bash
# Terminal 1
bash scripts/start_infinity.sh
```

Wait for:
```
✅ Application startup complete.
✅ Uvicorn running on http://0.0.0.0:7997
```

### 5. Index books into Qdrant

```bash
# Terminal 2
python scripts/index_books_direct.py
```

Expected output:
```
✅ 9 books indexed
✅ 4849 chunks
✅ Dense 1024 dims (BAAI/bge-m3)
```

### 6. Start API

```bash
# Terminal 3
uvicorn main:app --reload
```

API available at `http://localhost:8000`
Swagger docs: `http://localhost:8000/docs`

### 7. Start Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Frontend available at `http://localhost:3000`

---

## API Reference

### Training Plans

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/plans/generate` | Generate a personalized plan |
| `GET` | `/plans/` | List all plans |
| `GET` | `/plans/{id}` | Get a plan |
| `POST` | `/plans/{id}/feedback` | Submit feedback |
| `DELETE` | `/plans/{id}` | Delete a plan |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Login |

### Workout Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/workouts/` | Log a session |
| `GET` | `/workouts/` | Session history |

---

## Example Request

```bash
curl -X POST http://localhost:8000/plans/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 30,
    "gender": "M",
    "current_volume": 50,
    "current_frequency": 5,
    "goal_distance": "half",
    "goal_date": "2026-10-15",
    "availability": 5,
    "record_half": "1:12:00",
    "double_session": "no"
  }'
```

### Response structure

```json
{
  "coach_rationale": "Strategic justification...",
  "total_km": 680.5,
  "weeks": [
    {
      "week": 1,
      "phase": "Foncier",
      "weekly_km": 52.0,
      "days": [
        {
          "day": 1,
          "morning": {
            "type": "EF",
            "km": 10.0,
            "pace": "4:40-4:55/km",
            "details": "45min EF conversationnel à 4:40-4:55/km — base aérobie"
          },
          "afternoon": {
            "type": "REST",
            "km": 0,
            "pace": "N/A",
            "details": "Repos"
          }
        }
      ]
    }
  ],
  "metadata": {
    "niveau_athlete": "intermediate",
    "profil_aerobique": "aerobic",
    "reference_pace": "3:24/km",
    "is_valid": true,
    "hard_violations": [],
    "safety_warnings": []
  }
}
```

---

## Pipeline RAG

```
1. PlanRequest received
        │
        ▼
2. Python — objective references (formulas.py)
   Records → aerobic/anaerobic profile + race reference pace + estimated VMA
        │
        ▼
3. Python — safety bounds (progression_rules.py)
   Level detection → max progression rate + peak volume ceiling
        │
        ▼
4. Python — contextual warnings (safety_rules.py Layer A)
   Age, injury history, volume, timeline → informational context for LLM
        │
        ▼
5. RAG — multi-query dense search (RetrieverAgent)
   5 queries adapted to aerobic profile → Qdrant bge-m3 1024 dims
   Multi-query reranking → top 6 chunks
        │
        ▼
6. LLM — strategic analysis (AnalyzerAgent)
   Chooses ONE coherent philosophy from RAG
   Derives intensity zones from philosophy + aerobic profile
   NOT from hardcoded percentages
        │
        ▼
7. LLM — plan generation in 4-week chunks (PlannerAgent)
   Day-by-day variation enforced (J-1/J+1 logic)
   Pace ranges, not fixed values
   weekly_km computed from actual day km (never estimated upfront)
        │
        ▼
8. Python — hard limit validation (ValidatorAgent + safety_rules.py Layer B)
   Structure, consecutive intense sessions, deload weeks, taper
   Violations → regenerate with error feedback (up to 3 attempts)
        │
        ▼
9. Plan saved to DB + returned to athlete
```

---

## Athlete Session Types

| Type | Description | Pace format |
|------|-------------|-------------|
| `REST` | Complete rest | N/A |
| `RECOVERY` | Active recovery, < 30min | Range e.g. `5:30-6:00/km` |
| `EF` | Easy/Fundamental endurance | Range e.g. `4:40-4:55/km` |
| `EA` | Active endurance (between EF and threshold) | Range |
| `LONG_RUN` | Long run (extended EF, variations possible) | Range |
| `TEMPO` | Tempo / lactate threshold (20-40min) | Range |
| `THRESHOLD` | Lactate threshold intervals (8-15min) | Range |
| `INTERVAL` | VO2max intervals (30s-3min) | Range |
| `FARTLEK` | Free accelerations within EF | Range + note |
| `HILL_REPS` | Hill repetitions | `effort 85-95% VMA` |
| `RACE_PACE` | Goal race pace blocks | Range |
| `STRIDES` | Short accelerations after EF | `10-12s progressive` |
| `REST_ACTIVE` | Cross-training (bike, swim, walk) | N/A |

---

## Safety System

### Layer A — Contextual warnings (pre-LLM)
Injected as context into prompts. The LLM adapts freely.
- Recent injury return (< 30 days, < 90 days)
- Age 50+ / 60+ / junior
- High current volume (> 150 km/week)
- Short timeline (< 6 weeks, < 10 weeks)
- Frequency vs availability mismatch

### Layer B — Hard limits (post-LLM validation)
Applied on generated JSON. Violations trigger regeneration.
- Two consecutive intense sessions → blocked
- No complete rest day in a week → warning
- Intensity ratio > 30% of weekly volume → warning
- Double intense session same day (AM + PM) → blocked
- Weekly volume progression > 15% → warning
- No deload week in 4-week block → warning
- Insufficient taper before race → warning

---

## Rate Limit Strategy

Groq free tier: 100k tokens/day **per model**. The system cascades automatically:

```
llama-3.3-70b-versatile  (100k TPD)
        ↓ rate limit / error
qwen/qwen3-32b           (100k TPD, separate quota)
        ↓ rate limit / error
llama-4-scout-17b        (100k TPD, separate quota)
        ↓ rate limit / error
gemini-2.0-flash         (1500 req/day, no token limit)
```

Set `GEMINI_API_KEY` in `.env` to activate the Gemini fallback.

---

## Project Structure

```
running-coach/
├── backend/
│   ├── api/                    # FastAPI routes
│   ├── core/
│   │   ├── agents/             # LLM agents (orchestrator, planner, analyzer...)
│   │   ├── llm/                # Prompts
│   │   └── rules/              # Python rules (formulas, safety, progression)
│   ├── db/                     # SQLAlchemy models + CRUD
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic (auth, payments, strava...)
│   ├── tests/                  # Pytest test suite
│   └── utils/                  # Helpers, logger, exceptions
└── frontend/                   # Next.js 14 + Tailwind
```

---

## Running Tests

```bash
cd backend
pytest tests/ -v

# Integration test — full RAG + generation pipeline
python scripts/test_generation.py
```

---

## Troubleshooting

**Infinity won't start**
```bash
infinity_emb v2 --model-id BAAI/bge-m3 --model-id BAAI/bge-reranker-v2-m3 \
  --port 7997 --no-bettertransformer --device cuda
```

**Qdrant dimension mismatch**
```bash
python scripts/index_books_direct.py
```

**0 chunks found**
```bash
# Check books path in index_books_direct.py
BOOKS_DIR = Path("/home/pc/AI/projects/running-coach/data/books")
```

**Groq rate limit**
Add `GEMINI_API_KEY` to `.env` — the system falls back automatically.

---

## Author

**Ali EL AMRIOUI**


- [GitHub](https://github.com/Ali-EL-AMRIOUI)

---

## License

MIT License — see [LICENSE](LICENSE) for details.