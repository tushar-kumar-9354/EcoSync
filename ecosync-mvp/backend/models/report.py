from pydantic import BaseModel
from datetime import datetime


class CitizenReportCreate(BaseModel):
    category: str
    location: dict
    description: str
    severity: str | None = None
    reporter_anonymous: bool = True
    photos: list[str] | None = None
