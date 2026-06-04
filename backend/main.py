from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth, users, plans, workouts
from db.database import engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Running Coach API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(plans.router)
app.include_router(workouts.router)

@app.get("/")
def root():
    return {"message": "AI Running Coach API is running!"}

@app.get("/health")
def health():
    return {"status": "ok"}
