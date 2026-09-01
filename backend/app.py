from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import API routers
from backend.api.routes import jobs, reputation, submissions


app = FastAPI(
    title="Trustlance API",
    description="Backend API for the Trustlance decentralized freelance platform",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTES
# ============================================================

app.include_router(
    jobs.router,
    prefix="/api/jobs",
    tags=["Jobs"]
)

app.include_router(
    reputation.router,
    prefix="/api/reputation",
    tags=["Reputation"]
)

app.include_router(
    submissions.router,
    prefix="/api/submissions",
    tags=["Submissions"]
)

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Trustlance API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Trustlance Backend API"
    }