from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import os
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("loanword_api")

app = FastAPI(title="Loanword API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- DB URL helpers -------------------
RAW_DB_URL = os.getenv("DATABASE_URL")

def normalize_db_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://") and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url

DATABASE_URL = normalize_db_url(RAW_DB_URL)

def mask_url(u: str | None) -> str | None:
    if not u: return None
    try:
        left, right = u.split("@", 1)
        scheme, creds = left.split("//", 1)
        user = creds.split(":", 1)[0]
        return f"{scheme}//{user}:***@{right}"
    except Exception:
        return u

log.info(f"Using DATABASE_URL: {mask_url(DATABASE_URL)}")

_engine = None
_engine_error = None

def get_engine():
    """Create the engine on first use and cache any failure reason."""
    global _engine, _engine_error
    if _engine or _engine_error:
        return _engine
    if not DATABASE_URL:
        _engine_error = "DATABASE_URL missing"
        return None
    try:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        return _engine
    except Exception as e:
        _engine_error = str(e)
        log.error(f"DB engine creation failed: {e}")
        return None

# ------------------- Simple models & routes -------------------
class GenerateRequest(BaseModel):
    knownLanguages: list[str]
    targetLanguage: str
    difficulty: str

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

@app.get("/")
def root():
    return {"service": "loanword-api", "status": "ok", "docs": "/docs"}

@app.get("/v1/health")
def health():
    return {"ok": True}

@app.get("/v1/envcheck")
def envcheck():
    return {"DATABASE_URL_seen": DATABASE_URL is not None, "DATABASE_URL": mask_url(DATABASE_URL)}

@app.get("/v1/dbtest")
def dbtest():
    eng = get_engine()
    if not eng:
        return JSONResponse(status_code=500, content={
            "status": "error",
            "detail": _engine_error or "Database engine not initialized"
        })
    try:
        with eng.connect() as conn:
            now = conn.execute(text("SELECT NOW()")).fetchone()
            return {"status": "ok", "time": str(now[0])}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

@app.post("/v1/decks/generate")
def generate_deck(req: GenerateRequest):
    if not req.knownLanguages:
        return JSONResponse(status_code=400, content={
            "error": "VALIDATION_ERROR",
            "message": "knownLanguages must contain at least one language code",
        })
    if req.targetLanguage in req.knownLanguages:
        return JSONResponse(status_code=400, content={
            "error": "VALIDATION_ERROR",
            "message": "targetLanguage must not be in knownLanguages",
        })
    pair = next((k for k in CATALOG if k[0] == req.targetLanguage and k[1] in req.knownLanguages), None)
    cards = CATALOG.get(pair, [])
    return {
        "deckId": f"deck_{req.targetLanguage}",
        "targetLanguage": req.targetLanguage,
        "knownLanguages": req.knownLanguages,
        "difficulty": req.difficulty,
        "cards": cards,
    }
