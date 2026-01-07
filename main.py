from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "loanwords.db"

app = FastAPI(title="Loanword API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

@app.get("/v1/health")
def health():
    return {"ok": True}

@app.get("/v1/decks/generate")
def generate_deck(
    target: str = Query(..., description="Target language code, e.g. bg"),
    known: list[str] = Query(..., description="Known languages, e.g. en,fr"),
    limit: int = 20,
):
    con = get_db()
    cur = con.cursor()

    q = f"""
    SELECT target_word, rel_type, source_lang, source_word, gloss
    FROM loan_edges
    WHERE target_lang = ?
      AND source_lang IN ({",".join("?" for _ in known)})
    ORDER BY RANDOM()
    LIMIT ?
    """

    rows = cur.execute(q, [target, *known, limit]).fetchall()

    cards = [
        {
            "id": f"{target}-{r['target_word']}-{i}",
            "targetLang": target,
            "lemma": r["target_word"],
            "sourceLang": r["source_lang"],
            "sourceForm": r["source_word"],
            "gloss": r["gloss"] or "",
        }
        for i, r in enumerate(rows)
    ]

    return {
        "deckId": f"{target}-loanwords",
        "targetLanguage": target,
        "knownLanguages": known,
        "difficulty": "auto",
        "cards": cards,
    }
