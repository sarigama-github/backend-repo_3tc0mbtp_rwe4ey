import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from database import create_document, get_documents, db
from schemas import Journey, Interaction, Recommendation, Tea

app = FastAPI(title="Tee & Seele API", description="Backend for the gamified wellness experience")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Tee & Seele API running"}

@app.get("/test")
def test_database():
    """Verify DB connectivity and list available collections"""
    status = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "collections": []
    }
    try:
        if db is None:
            raise RuntimeError("DB not initialized")
        status["database"] = "✅ Connected"
        status["collections"] = db.list_collection_names()
    except Exception as e:
        status["database"] = f"❌ Error: {str(e)[:80]}"
    return status

# --------- Onboarding & Consent ---------
@app.post("/api/journey", response_model=dict)
def start_journey(journey: Journey):
    if not journey.consent:
        raise HTTPException(status_code=400, detail="Consent required to proceed.")
    _id = create_document("journey", journey)
    return {"journey_id": _id}

# --------- Interactions Collection ---------
@app.post("/api/interaction", response_model=dict)
def record_interaction(interaction: Interaction):
    if not interaction.journey_id:
        raise HTTPException(status_code=400, detail="journey_id required")
    _id = create_document("interaction", interaction)
    return {"interaction_id": _id}

# --------- Recommendation Logic ---------
class AnalyzeRequest(BaseModel):
    journey_id: str

@app.post("/api/analyze", response_model=Recommendation)
def analyze(req: AnalyzeRequest):
    # Pull interactions for the journey
    interactions = get_documents("interaction", {"journey_id": req.journey_id})

    # Simple heuristic profile from interaction counts and values
    profile: Dict[str, Any] = {
        "calm_need": 0,
        "focus_need": 0,
        "uplift_need": 0,
        "sleep_need": 0,
    }

    for it in interactions:
        t = it.get("type")
        val = it.get("value", {})
        if t == "metaphor_pick":
            # e.g., chosen metaphors: clouds -> calm, sparks -> uplift, roots -> grounding
            metaphor = val.get("metaphor")
            if metaphor == "clouds":
                profile["calm_need"] += 2
            elif metaphor == "sparks":
                profile["uplift_need"] += 2
            elif metaphor == "roots":
                profile["focus_need"] += 2
        elif t == "spark_collect":
            profile["uplift_need"] += int(val.get("count", 1))
        elif t == "maze_complete":
            profile["focus_need"] += 1
        elif t == "breath_pace":
            pace = val.get("pace", "slow")
            if pace == "slow":
                profile["sleep_need"] += 1
            else:
                profile["calm_need"] += 1
        elif t == "scene_choice":
            scene = val.get("scene")
            if scene == "night":
                profile["sleep_need"] += 1
            elif scene == "meadow":
                profile["calm_need"] += 1

    # Rank needs
    ranked = sorted(profile.items(), key=lambda x: x[1], reverse=True)

    # Fetch tea catalog
    tea_docs = get_documents("tea")
    teas = [Tea(**{k: v for k, v in d.items() if k != "_id"}) for d in tea_docs]

    def score_tea(tea: Tea) -> int:
        score = 0
        top_need = ranked[0][0] if ranked else None
        if top_need == "calm_need" and any(tag in tea.tags for tag in ["calming", "soothing", "anxiety"]):
            score += 3
        if top_need == "sleep_need" and any(tag in tea.tags for tag in ["sleep", "night", "sedative"]):
            score += 3
        if top_need == "focus_need" and any(tag in tea.tags for tag in ["focus", "grounding", "clarity"]):
            score += 3
        if top_need == "uplift_need" and any(tag in tea.tags for tag in ["uplift", "mood", "energize"]):
            score += 3
        # Minor boosts for secondary needs
        for need, val in ranked[1:3]:
            if need == "calm_need" and "calming" in tea.tags:
                score += 1
            if need == "sleep_need" and "sleep" in tea.tags:
                score += 1
            if need == "focus_need" and "focus" in tea.tags:
                score += 1
            if need == "uplift_need" and "uplift" in tea.tags:
                score += 1
        return score

    ranked_teas = sorted(teas, key=score_tea, reverse=True)
    tea_keys = [t.key for t in ranked_teas[:3]] if ranked_teas else []

    rec = Recommendation(journey_id=req.journey_id, profile=profile, teas=tea_keys)
    # Persist recommendation
    create_document("recommendation", rec)
    return rec

# --------- Tea catalog seeding (optional utility) ---------
@app.post("/api/seed-teas")
def seed_teas():
    """Seed a minimal tea catalog if empty."""
    existing = get_documents("tea", {}, limit=1)
    if existing:
        return {"status": "exists"}
    catalog = [
        Tea(
            key="chamomile",
            name="Kamille",
            tags=["calming", "sleep"],
            description="Sanfte Blüten, die Ruhe fördern",
            benefits=["Beruhigend", "Fördert Schlaf"],
            contraindications=["Allergie gegen Korbblütler"],
            interactions=[],
            preparation="2 TL auf 250ml, 8-10 Min. ziehen lassen"
        ),
        Tea(
            key="peppermint",
            name="Pfefferminze",
            tags=["clarity", "uplift"],
            description="Frische Blätter, die klären und beleben",
            benefits=["Erfrischend", "Konzentrationsfördernd"],
            contraindications=["Gallenwegsstörungen (Rücksprache)"],
            interactions=[],
            preparation="1-2 TL auf 250ml, 5-7 Min."
        ),
        Tea(
            key="lavender",
            name="Lavendel",
            tags=["calming", "sleep"],
            description="Blüten mit sanftem Duft, die entspannen",
            benefits=["Entspannend", "Schlaffördernd"],
            contraindications=["Schwangerschaft: Rücksprache"],
            interactions=[],
            preparation="1 TL auf 250ml, 5-7 Min."
        ),
        Tea(
            key="lemonbalm",
            name="Zitronenmelisse",
            tags=["calming", "uplift"],
            description="Zarte Blätter, die beruhigen und aufhellen",
            benefits=["Ausgleichend", "Stimmungsaufhellend"],
            contraindications=["Schilddrüse: Rücksprache"],
            interactions=[],
            preparation="1-2 TL auf 250ml, 5-8 Min."
        ),
    ]
    for t in catalog:
        create_document("tea", t)
    return {"status": "seeded", "count": len(catalog)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
