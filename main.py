from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---- FastAPI setup ----
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Request model ----
class GenerateRequest(BaseModel):
    knownLanguages: list[str]
    targetLanguage: str
    difficulty: str

# ---- Mock decks ----
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
    ("es", "en"): [
        {
            "id": "c3",
            "targetLang": "es",
            "lemma": "hotel",
            "sourceLang": "en",
            "sourceForm": "hotel",
            "gloss": "hotel",
            "exampleTarget": "El hotel está cerca del mar.",
            "exampleGloss": "The hotel is near the sea.",
            "ipa": "oˈtel",
        },
        {
            "id": "c4",
            "targetLang": "es",
            "lemma": "fútbol",
            "sourceLang": "en",
            "sourceForm": "football",
            "gloss": "football / soccer",
            "exampleTarget": "Me gusta el fútbol.",
            "exampleGloss": "I like football.",
            "ipa": "ˈfutβol",
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

# ---- Endpoint: POST /v1/decks/generate ----
@app.post("/v1/decks/generate")
def generate_deck(req: GenerateRequest):
    # Basic validation
    if not req.knownLanguages:
        return JSONResponse(
            status_code=400,
            content={
                "error": "VALIDATION_ERROR",
                "message": "knownLanguages must contain at least one language code",
            },
        )
    if req.targetLanguage in req.knownLanguages:
        return JSONResponse(
            status_code=400,
            content={
                "error": "VALIDATION_ERROR",
                "message": "targetLanguage must not be in knownLanguages",
            },
        )

    # Find matching pair (target, any known)
    pair = next(
        (k for k in CATALOG.keys() if k[0] == req.targetLanguage and k[1] in req.knownLanguages),
        None,
    )

    if pair:
        cards = CATALOG[pair]
    else:
        cards = []

    return {
        "deckId": f"deck_{req.targetLanguage}",
        "targetLanguage": req.targetLanguage,
        "knownLanguages": req.knownLanguages,
        "difficulty": req.difficulty,
        "cards": cards,
    }

# ---- Health check ----
@app.get("/v1/health")
def health():
    return {"ok": True}
