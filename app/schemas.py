"""Pydantic request/response models shared across the API + engines."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class EventProfile(BaseModel):
    """Everything the prediction & simulation engines need about an event."""

    name: str = "Untitled Event"
    venue_id: Optional[str] = None
    event_type: str = "sports"
    lat: float
    lon: float
    attendance: int = Field(20000, ge=0)
    start_hour: int = Field(18, ge=0, le=23)
    duration_hours: int = Field(3, ge=1, le=12)
    weekday: int = Field(5, ge=0, le=6)  # 0=Mon, 5=Sat
    weather: str = "clear"


class ScenarioRequest(BaseModel):
    event: EventProfile
    # Interventions toggled on for this run.
    strategy: str = "baseline"  # baseline|diversions|signals|full|emergency
    attendance_multiplier: float = 1.0


class AssistantQuery(BaseModel):
    question: str
    event: Optional[EventProfile] = None
