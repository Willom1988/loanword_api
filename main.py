from fastapi import FastAPI, Query
from pydantic import BaseModel
import sqlite3
import os
import random
import logging

# --------------------
# App setup
# --------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("loanword_api")

app = FastAPI(title="Loanword API", version="1.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "loanwords.db")

logger.info("🚀 Starting FastAPI (main.py)")
logger.info(f"Using database at: {DB_PATH}")

# --------------------
# Models
# --------------------

class GenerateRequest(BaseModel):
    targetLanguage: str
    knownLanguages: list[str]
    difficulty: str = "beginner"

class Card(BaseModel):
    word: str
    source_language: str
    source_word: str
    relation: str
    gloss: str | None = None

class DeckResponse(BaseModel):
    target_language: str
    known_languages: list[str]
    size: int
    cards: list[Card]

# --------------------
# Helpers
# --------------------

def get_connection():
    if not os.path.exists(DB_PATH):
        raise RuntimeError("loanwords.db not found in API directory")
    return sqlite3.connect(DB_PATH)

def generate_deck_logic(req: GenerateRequest) -> DeckResponse:
    con = get_connection()
    cur = con.cursor()

    placeholders = ",".join("?" for _ in req.knownLanguages)

    sql = f"""
        SELECT
            target_word,
            source_lang,
            source_word,
            rel_type,
            gloss
        FROM loan_edges
        WHERE target_lang = ?
          AND source_lang IN ({placeholders})
        ORDER BY RANDOM()
        LIMIT 20
    """

    params = [req.targetLanguage] + req.knownLanguages
    cur.execute(sql, params)

    rows = cur.fetchall()
    con.close()

    cards = [
        Card(
            word=row[0],
            source_language=row[1],
            source_word=row[2],
            relation=row[3],
            gloss=row[4],
        )
        for row in rows
    ]

    return DeckResponse(
        target_language=req.targetLanguage,
        known_languages=req.knownLanguages,
        size=len(cards),
        cards=cards,
    )

# --------------------
# Routes
# --------------------

@app.get("/v1/health")
def health():
    return {"ok": True}

@app.post("/v1/decks/generate")
def generate_deck(req: GenerateRequest):
    return generate_deck_logic(req)

# 👇 THIS FIXES YOUR "Method Not Allowed" ISSUE
@app.get("/v1/decks/generate")
def generate_deck_get(
    target: str,
    known: list[str] = Query(default=[]),
    difficulty: str = "beginner",
):
    req = GenerateRequest(
        targetLanguage=target,
        knownLanguages=known,
        difficulty=difficulty,
    )
    return generate_deck_logic(req)
