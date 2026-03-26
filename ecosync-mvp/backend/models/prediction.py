from pydantic import BaseModel
from datetime import datetime


class ConfidenceInterval(BaseModel):
    lower: float
    upper: float
    confidence: float


class Prediction(BaseModel):
    id: str
    type: str
    timestamp: datetime
    horizon: str
    value: float
    unit: str
    confidence_interval: ConfidenceInterval
    model_version: str
    factors: dict | None = None
