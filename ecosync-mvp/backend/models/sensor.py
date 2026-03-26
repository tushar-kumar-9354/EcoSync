from pydantic import BaseModel
from datetime import datetime


class Sensor(BaseModel):
    id: str
    type: str
    name: str
    lat: float
    lng: float
    zone: str
    is_active: bool = True
    installed_at: datetime
    last_reading_at: datetime | None = None
