"""
Database Schemas for Tee & Seele

Each Pydantic model corresponds to a MongoDB collection. The collection name
is the lowercase of the class name (e.g., Tea -> "tea").

These schemas are used for validation when creating documents via helpers.
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class Tea(BaseModel):
    """
    Tea profiles with traditional effects and basic safety notes.
    Collection: "tea"
    """
    key: str = Field(..., description="Unique key identifier, e.g., 'chamomile'")
    name: str = Field(..., description="Display name")
    tags: List[str] = Field(default_factory=list, description="Effect tags")
    description: str = Field(..., description="Short narrative description")
    benefits: List[str] = Field(default_factory=list, description="Potential benefits")
    contraindications: List[str] = Field(default_factory=list, description="Prominent contraindications")
    interactions: List[str] = Field(default_factory=list, description="Known interaction notes")
    preparation: str = Field(..., description="Simple preparation guide")

class Journey(BaseModel):
    """
    A user's immersive session through the world.
    Collection: "journey"
    """
    consent: bool = Field(..., description="Explicit consent to disclaimer")
    guide_name: Optional[str] = Field(default="Auri", description="Guide character name")
    device: Optional[str] = Field(default=None, description="UA/Device info (anonymized)")

class Interaction(BaseModel):
    """
    Recorded interaction events during a journey.
    Collection: "interaction"
    """
    journey_id: str = Field(..., description="Associated journey id")
    type: Literal[
        "metaphor_pick",
        "spark_collect",
        "maze_complete",
        "breath_pace",
        "scene_choice",
    ]
    value: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary payload per interaction type")

class Recommendation(BaseModel):
    """
    Final tea recommendation for a journey.
    Collection: "recommendation"
    """
    journey_id: str = Field(...)
    profile: Dict[str, Any] = Field(..., description="Computed emotional profile")
    teas: List[str] = Field(..., description="List of tea keys recommended in ranked order")

# Minimal user model retained for potential future use
class User(BaseModel):
    name: str
    email: str
    address: str
    age: Optional[int] = Field(None, ge=0, le=120)
    is_active: bool = True
