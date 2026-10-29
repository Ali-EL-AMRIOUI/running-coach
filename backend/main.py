from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth, users, plans, workouts, feedback, payments, webhooks
from config import settings

# Database schema is managed exclusively through Alembic migrations
# (see db/migrations/). Run `alembic upgrade head` before starting the
# server. We deliberately do NOT call Base.metadata.create_all() here:
# doing so would create tables outside of Alembic's tracking, causing
# "relation already exists" errors on the next real migration.
app = FastAPI(title="AI Running Coach API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(plans.router)
app.include_router(workouts.router)
app.include_router(feedback.router)
app.include_router(payments.router)
app.include_router(webhooks.router)

@app.get("/")
def root():
    return {"message": "AI Running Coach API is running!"}

@app.get("/health")
def health():
    return {"status": "ok"}
