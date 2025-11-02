from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import os
import logging

# -------------------------------------------------
# 🚀 1. Logging setup
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("🚀 Starting FastAPI server (main.py)")

# -------------------------------------------------
# 2. FastAPI app setup
# -------------------------------------------------
app = FastAPI(title="Loanword API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Allow all (fine for dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# 3. Database connection
# -------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Ensure sslmode=require if missing
    if "sslmode" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"
    logger.info(f"Using DATABASE_URL: {DATABASE_URL.split('@')[1][:20]}...")  # hide credentials
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    except Exception as e:
        logger.error(f"❌ Error creating engine: {e}")
        engine = None
else:
    logger.warning("⚠️ DATABASE_URL not found in environment")
    engine = None

# -------------------------------------------------
# 4. Request model (from Flutter)
# -------------------------------------------------
class GenerateRequest(BaseModel):
    knownLanguages: list[str]
    targetLanguage: str
    difficulty: str

# -------------------------------------------------
# 5. Routes
# -------------------------------------------------
@app.get("/")
def root():
    return {"message": "Loanword API live 🎉", "docs": "/docs"}

@app.get("/v1/health")
def health():
    return {"ok": True}

@app.get("/v1/envcheck")
def envcheck():
    """Check if DATABASE_URL is being read"""
    return {
        "DATABASE_URL_seen": bool(DATABASE_URL),
        "masked": DATABASE_URL[:30] + "..." if DATABASE_URL else None,
    }

@app.get("/v1/dbtest")
def db_test():
    """Test PostgreSQL connection"""
    if not engine:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": "Database engine not initialized"},
        )

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT NOW()")).fetchone()
            return {"status": "ok", "time": str(result[0])}
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)},
        )

# -------------------------------------------------
# 6. Mock deck generator
# -------------------------------------------------
CATALOG = {
    ("es", "ar"): [
        {
            "id": "c1",
            "targetLang": "es",
            "lemma": "almohada",
            "sourceLang": "ar",
            "sourceForm": "al-mikhadda",
            "gloss": "pillow",
            "exampleTarget": "La almohada es nueva.",
            "exampleGloss": "The pillow is new.",
            "ipa": "al.mo.ˈaða",
        },
        {
            "id": "c2",
            "targetLang": "es",
            "lemma": "aceituna",
            "sourceLang": "ar",
            "sourceForm": "zaytūn",
            "gloss": "olive",
            "exampleTarget": "La aceituna es verde.",
            "exampleGloss": "The olive is green.",
            "ipa": "a.θei̯.ˈtu.na",
        },
    ],
    ("fr", "en"): [
        {
            "id": "c5",
            "targetLang": "fr",
            "lemma": "week-end",
            "sourceLang": "en",
            "sourceForm": "weekend",
            "gloss": "weekend",
            "exampleTarget": "Le week-end commence vendredi soir.",
            "exampleGloss": "The weekend starts Friday night.",
            "ipa": "wikˈɛnd",
        },
    ],
}

@app.post("/v1/decks/generate")
def generate_deck(req: GenerateRequest):
    """Return a mock deck depending on known/target languages"""
    logger.info(f"Generating deck for {req.knownLanguages} → {req.targetLanguage}")

    if not req.knownLanguages:
        return JSONResponse(
            status_code=400,
            content={"error": "VALIDATION_ERROR", "message": "knownLanguages must contain at least one code"},
        )

    if req.targetLanguage in req.knownLanguages:
        return JSONResponse(
            status_code=400,
            content={"error": "VALIDATION_ERROR", "message": "targetLanguage must not be in knownLanguages"},
        )

    pair = next(
        (k for k in CATALOG.keys() if k[0] == req.targetLanguage and k[1] in req.knownLanguages),
        None,
    )

    cards = CATALOG.get(pair, [])
    return {
        "deckId": f"deck_{req.targetLanguage}",
        "targetLanguage": req.targetLanguage,
        "knownLanguages": req.knownLanguages,
        "difficulty": req.difficulty,
        "cards": cards,
    }
