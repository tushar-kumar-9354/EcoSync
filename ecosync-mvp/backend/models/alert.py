from pydantic import BaseModel
from datetime import datetime


class Location(BaseModel):
    lat: float
    lng: float
    address: str


class Alert(BaseModel):
    id: str
    type: str
    severity: str
    status: str
    title: str
    message: str
    location: Location
    current_value: float
    threshold: float
    unit: str
    triggered_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    acknowledged_by: str | None = None
    assigned_to: str | None = None
    tags: list[str] = []
