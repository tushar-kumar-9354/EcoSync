import random
from datetime import datetime, timedelta
from typing import Any


class PredictionService:
    """Generates mock AI predictions with realistic variance and confidence intervals."""

    def __init__(self, db: Any):
        self.db = db

    def get_energy_forecast(self, hours: int = 24) -> dict[str, Any]:
        """Generate 24-hour energy demand forecast."""
        now = datetime.now()
        base_demand = 4500  # kWh baseline

        predictions = []
        for i in range(hours):
            future = now + timedelta(hours=i)
            hour = future.hour
            is_weekend = future.weekday() >= 5

            # Business pattern
            if is_weekend:
                multiplier = 0.6 if 10 <= hour <= 16 else 0.4
            else:
                multiplier = 1.2 if 9 <= hour <= 17 else 0.7

            base = base_demand * multiplier
            uncertainty = 0.03 + (i * 0.008)
            value = base * random.gauss(1.0, uncertainty)
            value = max(1000, min(8000, value))

            predictions.append({
                "id": f"pred-energy-{i}",
                "type": "energy_demand",
                "timestamp": future.isoformat(),
                "horizon": f"{i}h",
                "value": round(value, 1),
                "unit": "kWh",
                "confidence_interval": {
                    "lower": round(value * 0.88, 1),
                    "upper": round(value * 1.12, 1),
                    "confidence": round(max(0.6, 1.0 - (i * 0.015)), 2)
                },
                "model_version": "lstm-transformer-v2.1"
            })

        peak_hour = None
        peak_value = 0
        for p in predictions[:12]:
            if p["value"] > peak_value:
                peak_value = p["value"]
                peak_hour = p["timestamp"][11:16]

        return {
            "predictions": predictions,
            "base_demand": base_demand,
            "peak_expected": True,
            "peak_hour": peak_hour
        }

    def get_aqi_forecast(self, hours: int = 48) -> dict[str, Any]:
        """Generate 48-hour AQI forecast."""
        now = datetime.now()
        predictions = []

        for i in range(hours):
            future = now + timedelta(hours=i)
            hour = future.hour

            # AQI patterns
            if 7 <= hour <= 9 or 17 <= hour <= 19:
                base = 65
            elif 22 <= hour or hour <= 5:
                base = 40
            else:
                base = 55

            uncertainty = 0.02 + (i * 0.006)
            aqi = int(base * random.gauss(1.0, uncertainty))
            aqi = max(15, min(250, aqi))

            predictions.append({
                "id": f"pred-aqi-{i}",
                "type": "aqi_forecast",
                "timestamp": future.isoformat(),
                "horizon": f"{i}h",
                "value": aqi,
                "unit": "AQI",
                "confidence_interval": {
                    "lower": max(10, int(aqi * 0.82)),
                    "upper": min(300, int(aqi * 1.18)),
                    "confidence": round(max(0.5, 1.0 - (i * 0.01)), 2)
                },
                "model_version": "lstm-transformer-v2.1"
            })

        # Determine trend
        recent = sum(p["value"] for p in predictions[:6]) / 6
        later = sum(p["value"] for p in predictions[-6:]) / 6
        trend = "improving" if later < recent * 0.9 else "worsening" if later > recent * 1.1 else "stable"

        return {
            "hourly": predictions,
            "trend": trend,
            "dominant_pollutant": "PM2.5"
        }

    def get_overflow_predictions(self) -> list[dict[str, Any]]:
        """Generate bin overflow risk predictions."""
        predictions = []
        for sensor in self.db.sensors:
            if sensor["type"] != "waste_bin":
                continue

            # Find most recent reading
            bin_readings = [r for r in self.db.readings if r.get("bin_id") == sensor["id"]]
            if not bin_readings:
                continue

            latest = sorted(bin_readings, key=lambda x: x["timestamp"], reverse=True)[0]
            fill = latest.get("fill_percent", 50)

            # Predict overflow in 2 hours
            risk = min(1.0, max(0, (fill - 50) / 50 + random.uniform(0, 0.2)))
            if fill > 60:
                predictions.append({
                    "bin_id": sensor["id"],
                    "name": sensor["name"],
                    "current_fill": fill,
                    "overflow_risk_2h": round(risk, 2),
                    "recommended_action": "Schedule collection" if risk > 0.7 else "Monitor",
                    "zone": sensor["zone"],
                    "lat": sensor["lat"],
                    "lng": sensor["lng"]
                })

        return sorted(predictions, key=lambda x: x["overflow_risk_2h"], reverse=True)[:10]
