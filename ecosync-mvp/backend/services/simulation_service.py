import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import Any


class SimulationService:
    """Orchestrates realistic sensor data simulation across all sensor types."""

    ZONES = ["connaught", "chandni", "karol", "saket", "dwarka"]
    BASELINE_AQI = {"connaught": 180, "chandni": 165, "karol": 195, "saket": 155, "dwarka": 145}
    FILL_RATES = {"residential": 0.5, "commercial": 1.5, "park": 0.8, "street": 1.0}
    BASE_CONSUMPTION = {"office": 500, "retail": 200, "residential": 80, "industrial": 800, "municipal": 150}

    def __init__(self, db: Any, update_interval: int = 15):
        self.db = db
        self.update_interval = update_interval
        self._running = False
        self._task = None

    def initialize_sensors(self):
        """Create sensor registry in the database."""
        lat_base, lng_base = 28.61, 77.20

        # Air quality sensors (4 per zone = 20 total)
        for i, zone in enumerate(self.ZONES):
            for j in range(4):
                offset = i * 0.025 + j * 0.005
                self.db.sensors.append({
                    "id": f"aq-{zone[:3]}-{i * 4 + j + 1:02d}",
                    "type": "air_quality",
                    "name": f"{zone.title()} AQ Station {j + 1}",
                    "lat": lat_base + offset,
                    "lng": lng_base + offset,
                    "zone": zone,
                    "is_active": True,
                    "installed_at": (datetime.now() - timedelta(days=random.randint(30, 365))).isoformat(),
                    "last_reading_at": None
                })

        # Waste bins (8 per zone = 40 total)
        bin_types = ["residential", "commercial", "park", "street"]
        for i, zone in enumerate(self.ZONES):
            for j in range(8):
                offset = i * 0.025 + j * 0.004
                self.db.sensors.append({
                    "id": f"bin-{zone[:3]}-{i * 8 + j + 1:02d}",
                    "type": "waste_bin",
                    "name": f"{zone.title()} Bin {j + 1}",
                    "lat": lat_base + 0.01 + offset,
                    "lng": lng_base + 0.01 + offset,
                    "zone": zone,
                    "is_active": True,
                    "bin_type": bin_types[j % 4],
                    "installed_at": (datetime.now() - timedelta(days=random.randint(60, 730))).isoformat(),
                    "last_reading_at": None
                })

        # Energy meters (6 per zone = 30 total)
        building_types = ["office", "retail", "residential", "industrial", "municipal"]
        for i, zone in enumerate(self.ZONES):
            for j in range(6):
                offset = i * 0.025 + j * 0.004
                self.db.sensors.append({
                    "id": f"meter-{zone[:3]}-{i * 6 + j + 1:02d}",
                    "type": "energy_meter",
                    "name": f"{zone.title()} Building {j + 1}",
                    "lat": lat_base + 0.02 + offset,
                    "lng": lng_base + 0.02 + offset,
                    "zone": zone,
                    "is_active": True,
                    "building_type": building_types[j % 5],
                    "installed_at": (datetime.now() - timedelta(days=random.randint(90, 1095))).isoformat(),
                    "last_reading_at": None
                })

    def seed_historical_data(self, hours: int = 48):
        """Pre-populate historical readings."""
        now = datetime.now()
        start_time = now - timedelta(hours=hours)

        for sensor in self.db.sensors:
            for hour_offset in range(hours):
                timestamp = start_time + timedelta(hours=hour_offset)
                reading = self._generate_reading(sensor, timestamp)
                self.db.readings.append(reading)

    def _generate_reading(self, sensor: dict, timestamp: datetime) -> dict:
        """Generate reading based on sensor type."""
        sensor_type = sensor["type"]

        if sensor_type == "air_quality":
            return self._generate_aq_reading(sensor, timestamp)
        elif sensor_type == "waste_bin":
            return self._generate_waste_reading(sensor, timestamp)
        elif sensor_type == "energy_meter":
            return self._generate_energy_reading(sensor, timestamp)
        return {}

    def _generate_aq_reading(self, sensor: dict, timestamp: datetime) -> dict:
        baseline = self.BASELINE_AQI.get(sensor["zone"], 40)
        hour = timestamp.hour
        diurnal = 1.3 if 7 <= hour <= 9 else (1.4 if 17 <= hour <= 19 else (0.6 if 22 <= hour or hour <= 5 else 1.0))
        weekday_factor = 1.2 if timestamp.weekday() < 5 else 1.0
        aqi = int(baseline * diurnal * weekday_factor * random.gauss(1.0, 0.08))
        aqi = max(10, min(300, aqi))
        category = "Good" if aqi <= 50 else "Moderate" if aqi <= 100 else "Unhealthy for Sensitive Groups" if aqi <= 150 else "Unhealthy" if aqi <= 200 else "Very Unhealthy"

        return {
            "sensor_id": sensor["id"],
            "timestamp": timestamp.isoformat(),
            "aqi": aqi,
            "category": category,
            "pm25": round(12 * diurnal * random.gauss(1.0, 0.1), 1),
            "pm10": round(25 * diurnal * random.gauss(1.0, 0.1), 1),
            "no2": round(20 * diurnal * random.gauss(1.0, 0.08), 1),
            "o3": round(0.035 * (2 - diurnal) * random.gauss(1.0, 0.05), 4),
            "co": round(0.5 * diurnal * random.gauss(1.0, 0.06), 2),
            "lat": sensor["lat"],
            "lng": sensor["lng"]
        }

    def _generate_waste_reading(self, sensor: dict, timestamp: datetime) -> dict:
        rate = self.FILL_RATES.get(sensor.get("bin_type", "residential"), 1.0)
        hours = random.randint(1, 72)
        fill = min(100.0, hours * rate * abs(random.gauss(1.0, 0.1)))

        return {
            "bin_id": sensor["id"],
            "timestamp": timestamp.isoformat(),
            "fill_percent": round(fill, 1),
            "overflow_risk": round(min(1.0, max(0, (fill - 60) / 100)), 2),
            "zone": sensor["zone"],
            "bin_type": sensor.get("bin_type", "residential"),
            "lat": sensor["lat"],
            "lng": sensor["lng"]
        }

    def _generate_energy_reading(self, sensor: dict, timestamp: datetime) -> dict:
        base = self.BASE_CONSUMPTION.get(sensor.get("building_type", "office"), 100)
        hour = timestamp.hour
        is_weekend = timestamp.weekday() >= 5

        if is_weekend:
            occupancy = 0.6 if 10 <= hour <= 16 else (0.4 if 7 <= hour <= 22 else 0.2)
        else:
            occupancy = 1.0 if 8 <= hour <= 18 else (0.15 if 22 <= hour or hour <= 5 else 0.4)

        consumption = base * occupancy * (1.2 if timestamp.weekday() < 5 else 0.6) * abs(random.gauss(1.0, 0.05))

        return {
            "meter_id": sensor["id"],
            "timestamp": timestamp.isoformat(),
            "consumption_kwh": round(consumption, 2),
            "demand_kw": round(consumption, 2),
            "building_type": sensor.get("building_type", "office"),
            "zone": sensor["zone"],
            "lat": sensor["lat"],
            "lng": sensor["lng"]
        }

    def _check_thresholds(self, sensor: dict, reading: dict, timestamp: datetime):
        """Check readings against thresholds and create alerts."""
        sensor_type = sensor["type"]

        if sensor_type == "air_quality":
            aqi = reading.get("aqi", 0)
            if aqi > 150:
                self._create_alert(sensor, "air_quality", "HIGH" if aqi < 200 else "CRITICAL",
                    f"Air Quality Alert: AQI {aqi}", f"AQI has reached {aqi} ({reading['category']}) at {sensor['name']}",
                    aqi, 150, "AQI", timestamp)
            elif aqi > 100:
                self._create_alert(sensor, "air_quality", "MEDIUM",
                    f"Moderate Air Quality: AQI {aqi}", f"AQI has reached {aqi}",
                    aqi, 100, "AQI", timestamp)

        elif sensor_type == "waste_bin":
            fill = reading.get("fill_percent", 0)
            if fill > 90:
                self._create_alert(sensor, "bin_overflow", "HIGH",
                    f"Bin Overflow Risk: {fill}% full", f"Bin at {sensor['name']} is {fill}% full",
                    fill, 90, "%", timestamp)

        elif sensor_type == "energy_meter":
            consumption = reading.get("consumption_kwh", 0)
            base = self.BASE_CONSUMPTION.get(sensor.get("building_type", "office"), 100)
            if consumption > base * 1.5:
                self._create_alert(sensor, "energy_peak", "MEDIUM",
                    f"Energy Spike: {consumption:.0f} kWh", f"Unusual energy consumption at {sensor['name']}",
                    consumption, base * 1.5, "kWh", timestamp)

    def _create_alert(self, sensor: dict, alert_type: str, severity: str, title: str, message: str,
                      current_value: float, threshold: float, unit: str, timestamp: datetime):
        # Avoid duplicate alerts within 5 minutes
        recent = any(
            a.get("type") == alert_type and
            a.get("location", {}).get("address") == sensor["name"] and
            (timestamp - datetime.fromisoformat(a["triggered_at"])).total_seconds() < 300
            for a in self.db.alerts
        )
        if recent:
            return

        alert_id = f"ALT-{timestamp.strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        self.db.alerts.append({
            "id": alert_id,
            "type": alert_type,
            "severity": severity,
            "status": "ACTIVE",
            "title": title,
            "message": message,
            "location": {"lat": sensor["lat"], "lng": sensor["lng"], "address": sensor["name"]},
            "current_value": current_value,
            "threshold": threshold,
            "unit": unit,
            "triggered_at": timestamp.isoformat(),
            "acknowledged_at": None,
            "resolved_at": None,
            "acknowledged_by": None,
            "assigned_to": None,
            "tags": []
        })

    async def start(self):
        """Start the simulation loop."""
        self._running = True
        self._task = asyncio.create_task(self._simulation_loop())

    async def stop(self):
        """Stop the simulation loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _simulation_loop(self):
        """Main loop updating sensor readings periodically."""
        while self._running:
            try:
                await self._update_readings()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Simulation error: {e}")
                await asyncio.sleep(self.update_interval)

    async def _update_readings(self):
        """Generate new readings for all active sensors."""
        now = datetime.now()

        for sensor in self.db.sensors:
            if not sensor.get("is_active", True):
                continue

            reading = self._generate_reading(sensor, now)
            sensor["last_reading_at"] = now.isoformat()
            self.db.readings.append(reading)
            self._check_thresholds(sensor, reading, now)

        # Cap readings to prevent memory issues
        if len(self.db.readings) > 10000:
            self.db.readings = self.db.readings[-5000:]
