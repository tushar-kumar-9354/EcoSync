from datetime import datetime
from typing import Any


class SimulatedDB:
    """In-memory database for MVP simulation."""

    def __init__(self):
        self.sensors: list[dict[str, Any]] = []
        self.readings: list[dict[str, Any]] = []
        self.alerts: list[dict[str, Any]] = []
        self.reports: list[dict[str, Any]] = []
        self.predictions: list[dict[str, Any]] = []
        self.metrics: dict[str, Any] = {}
        self.ws_clients: list[Any] = []

    def reset(self):
        self.sensors.clear()
        self.readings.clear()
        self.alerts.clear()
        self.reports.clear()
        self.predictions.clear()


db = SimulatedDB()
