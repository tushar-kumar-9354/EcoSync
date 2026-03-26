import asyncio
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Query, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys
import os
# Support both local (python main.py from backend/) and Render (uvicorn backend.main:app)
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == "backend":
    # Running locally: python main.py from inside backend/ folder
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import settings
    from database import db
    from models.report import CitizenReportCreate
    from services.simulation_service import SimulationService
    from services.prediction_service import PredictionService
else:
    # Running on Render: uvicorn backend.main:app from ecosync-mvp/
    from backend.config import settings
    from backend.database import db
    from backend.models.report import CitizenReportCreate
    from backend.services.simulation_service import SimulationService
    from backend.services.prediction_service import PredictionService

# Initialize services
simulation = SimulationService(db, settings.simulation_update_interval)
prediction_service = PredictionService(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    simulation.initialize_sensors()
    simulation.seed_historical_data(48)
    await simulation.start()
    yield
    # Shutdown
    await simulation.stop()


import os

_cors_origins = settings.get_cors_origins()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH & INFO
# ============================================================================

@app.get("/")
async def root():
    return {"name": "EcoSync API", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============================================================================
# SENSORS
# ============================================================================

@app.get("/api/v1/sensors")
async def list_sensors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    type: Optional[str] = None
):
    sensors = db.sensors
    if type:
        sensors = [s for s in sensors if s["type"] == type]
    return {"total": len(sensors), "sensors": sensors[skip:skip + limit]}


@app.get("/api/v1/sensors/{sensor_id}")
async def get_sensor(sensor_id: str):
    sensor = next((s for s in db.sensors if s["id"] == sensor_id), None)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@app.get("/api/v1/sensors/geojson")
async def sensors_geojson():
    """All sensors as GeoJSON FeatureCollection."""
    features = []
    for sensor in db.sensors:
        reading = None
        if sensor["type"] == "air_quality":
            readings = [r for r in db.readings if r.get("sensor_id") == sensor["id"]]
            reading = sorted(readings, key=lambda x: x["timestamp"], reverse=True)[0] if readings else None
        elif sensor["type"] == "waste_bin":
            readings = [r for r in db.readings if r.get("bin_id") == sensor["id"]]
            reading = sorted(readings, key=lambda x: x["timestamp"], reverse=True)[0] if readings else None
        elif sensor["type"] == "energy_meter":
            readings = [r for r in db.readings if r.get("meter_id") == sensor["id"]]
            reading = sorted(readings, key=lambda x: x["timestamp"], reverse=True)[0] if readings else None

        properties = {
            "id": sensor["id"],
            "name": sensor["name"],
            "type": sensor["type"],
            "zone": sensor["zone"],
            "is_active": sensor["is_active"]
        }

        if reading:
            if sensor["type"] == "air_quality":
                properties.update({"aqi": reading.get("aqi"), "category": reading.get("category")})
            elif sensor["type"] == "waste_bin":
                properties.update({"fill_percent": reading.get("fill_percent"), "overflow_risk": reading.get("overflow_risk")})
            elif sensor["type"] == "energy_meter":
                properties.update({"consumption_kwh": reading.get("consumption_kwh")})

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [sensor["lng"], sensor["lat"]]},
            "properties": properties
        })

    return {"type": "FeatureCollection", "features": features}


# ============================================================================
# AIR QUALITY
# ============================================================================

@app.get("/api/v1/aq/current")
async def aq_current():
    """Current AQI values from all stations."""
    stations = []
    for sensor in db.sensors:
        if sensor["type"] != "air_quality":
            continue
        readings = [r for r in db.readings if r.get("sensor_id") == sensor["id"]]
        latest = sorted(readings, key=lambda x: x["timestamp"], reverse=True)[0] if readings else None
        if latest:
            stations.append({
                "id": sensor["id"],
                "name": sensor["name"],
                "lat": sensor["lat"],
                "lng": sensor["lng"],
                "aqi": latest.get("aqi", 50),
                "category": latest.get("category", "Unknown"),
                "pm25": latest.get("pm25", 0),
                "pm10": latest.get("pm10", 0),
                "no2": latest.get("no2", 0),
                "o3": latest.get("o3", 0),
                "co": latest.get("co", 0),
                "timestamp": latest.get("timestamp")
            })

    if not stations:
        return {"timestamp": datetime.now().isoformat(), "aqi": 45, "category": "Good", "stations": []}

    avg_aqi = sum(s["aqi"] for s in stations) / len(stations)
    max_aqi_station = max(stations, key=lambda x: x["aqi"])

    return {
        "timestamp": datetime.now().isoformat(),
        "aqi": int(avg_aqi),
        "category": max_aqi_station["category"],
        "dominant_pollutant": "PM2.5",
        "stations": stations
    }


@app.get("/api/v1/aq/forecast")
async def aq_forecast():
    """48-hour AQI forecast."""
    return prediction_service.get_aqi_forecast(48)


@app.get("/api/v1/aq/history")
async def aq_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    zone: Optional[str] = None
):
    """Historical AQI data."""
    end = datetime.now()
    start = end - timedelta(days=7)

    readings = []
    for r in db.readings:
        if r.get("sensor_id", "").startswith("aq-"):
            ts = datetime.fromisoformat(r["timestamp"])
            if ts >= start and ts <= end:
                sensor = next((s for s in db.sensors if s["id"] == r["sensor_id"]), None)
                if sensor and (not zone or sensor["zone"] == zone):
                    readings.append({**r, "zone": sensor["zone"]})

    readings.sort(key=lambda x: x["timestamp"])
    return {"readings": readings[-100:], "count": len(readings)}


# ============================================================================
# ENERGY
# ============================================================================

@app.get("/api/v1/energy/consumption")
async def energy_consumption(
    period: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    granularity: str = Query("1h", pattern="^(15m|1h|1d)$")
):
    """Aggregated energy consumption."""
    hours = {"1h": 1, "6h": 6, "24h": 24, "7d": 168, "30d": 720}.get(period, 24)
    end = datetime.now()
    start = end - timedelta(hours=hours)

    readings = [r for r in db.readings if r.get("meter_id", "").startswith("meter-")]
    readings = [r for r in readings if start <= datetime.fromisoformat(r["timestamp"]) <= end]
    readings.sort(key=lambda x: x["timestamp"])

    if not readings:
        return {"period": period, "total_kwh": 0, "avg_kw": 0, "data": []}

    aggregated = {}
    for r in readings:
        ts = datetime.fromisoformat(r["timestamp"])
        key = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        if key not in aggregated:
            aggregated[key] = []
        aggregated[key].append(r["consumption_kwh"])

    data = []
    for ts, vals in sorted(aggregated.items()):
        data.append({"timestamp": ts, "consumption_kwh": round(sum(vals) / len(vals), 1)})

    total = sum(r["consumption_kwh"] for r in readings)
    return {
        "period": period,
        "total_kwh": round(total, 1),
        "avg_kw": round(total / hours, 1) if hours > 0 else 0,
        "data": data[-100:]
    }


@app.get("/api/v1/energy/forecast")
async def energy_forecast():
    """24-hour energy demand forecast."""
    return prediction_service.get_energy_forecast(24)


@app.get("/api/v1/energy/peaks")
async def energy_peaks():
    """Identified peak events."""
    return {
        "peaks": [
            {"id": "peak-1", "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(), "demand_kw": 5200, "duration_min": 45},
            {"id": "peak-2", "timestamp": (datetime.now() - timedelta(days=1, hours=3)).isoformat(), "demand_kw": 4900, "duration_min": 30},
            {"id": "peak-3", "timestamp": (datetime.now() - timedelta(days=2, hours=3)).isoformat(), "demand_kw": 5100, "duration_min": 60},
        ]
    }


# ============================================================================
# WASTE
# ============================================================================

@app.get("/api/v1/waste/bins")
async def list_bins(
    status: Optional[str] = None,
    zone: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """All bins with fill levels."""
    bins = []
    for sensor in db.sensors:
        if sensor["type"] != "waste_bin":
            continue
        if zone and sensor["zone"] != zone:
            continue

        readings = [r for r in db.readings if r.get("bin_id") == sensor["id"]]
        latest = sorted(readings, key=lambda x: x["timestamp"], reverse=True)[0] if readings else None

        fill = latest.get("fill_percent", 0) if latest else 0
        bin_status = "critical" if fill >= 90 else "warning" if fill >= 75 else "moderate" if fill >= 50 else "normal"

        if status and status != bin_status:
            continue

        bins.append({
            "id": sensor["id"],
            "name": sensor["name"],
            "type": sensor.get("bin_type", "residential"),
            "zone": sensor["zone"],
            "lat": sensor["lat"],
            "lng": sensor["lng"],
            "fill_percent": fill,
            "overflow_risk": latest.get("overflow_risk", 0) if latest else 0,
            "status": bin_status,
            "last_reading": latest.get("timestamp") if latest else None
        })

    return {"bins": bins[:limit], "total": len(bins)}


@app.get("/api/v1/waste/overflow-risk")
async def overflow_risk():
    """Bins at risk of overflow."""
    predictions = prediction_service.get_overflow_predictions()
    return {"predictions": predictions, "count": len(predictions)}


@app.get("/api/v1/waste/diversion")
async def waste_diversion():
    """Diversion rate analytics."""
    return {
        "diversion_rate": round(random.uniform(32, 45), 1),
        "trend": random.choice(["improving", "stable"]),
        "weekly_data": [
            {"week": "2026-W11", "rate": 38.2, "recycled_tons": 1240, "organic_tons": 890},
            {"week": "2026-W12", "rate": 39.5, "recycled_tons": 1310, "organic_tons": 920},
            {"week": "2026-W13", "rate": 41.8, "recycled_tons": 1380, "organic_tons": 960},
        ]
    }


# ============================================================================
# ALERTS
# ============================================================================

@app.get("/api/v1/alerts")
async def list_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    alert_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200)
):
    """List alerts with filtering."""
    alerts = db.alerts

    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    if status:
        alerts = [a for a in alerts if a["status"] == status]
    if alert_type:
        alerts = [a for a in alerts if a["type"] == alert_type]

    alerts.sort(key=lambda x: x["triggered_at"], reverse=True)
    return {"alerts": alerts[:limit], "total": len(alerts)}


@app.get("/api/v1/alerts/stats")
async def alert_stats():
    """Alert statistics by severity."""
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for a in db.alerts:
        if a["status"] != "RESOLVED":
            counts[a["severity"]] = counts.get(a["severity"], 0) + 1

    total_active = sum(counts.values())
    return {
        "total_active": total_active,
        "by_severity": counts,
        "acknowledged": len([a for a in db.alerts if a["status"] == "ACKNOWLEDGED"]),
        "resolved_today": len([a for a in db.alerts if a["status"] == "RESOLVED" and
                               datetime.fromisoformat(a["resolved_at"]).date() == datetime.now().date()])
    }


@app.put("/api/v1/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    alert = next((a for a in db.alerts if a["id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert["status"] = "ACKNOWLEDGED"
    alert["acknowledged_at"] = datetime.now().isoformat()
    return alert


@app.put("/api/v1/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    alert = next((a for a in db.alerts if a["id"] == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert["status"] = "RESOLVED"
    alert["resolved_at"] = datetime.now().isoformat()
    return alert


# ============================================================================
# CITIZEN REPORTS
# ============================================================================

@app.get("/api/v1/reports")
async def list_reports(
    status: Optional[str] = None,
    category: Optional[str] = None,
    page: int = Query(1, ge=1)
):
    """List citizen reports."""
    reports = db.reports

    if status:
        reports = [r for r in reports if r["status"] == status]
    if category:
        reports = [r for r in reports if r["category"] == category]

    reports.sort(key=lambda x: x["created_at"], reverse=True)
    per_page = 20
    start = (page - 1) * per_page
    return {"reports": reports[start:start + per_page], "total": len(reports), "page": page}


@app.post("/api/v1/reports")
async def create_report(report: CitizenReportCreate):
    """Submit a new citizen report (mock NLP processing)."""
    now = datetime.now()
    report_id = f"ECO-{now.strftime('%Y%m%d')}-{random.randint(100000, 999999)}"

    dept_map = {
        "illegal_dumping": "Sanitation",
        "noise_complaint": "Police",
        "air_quality_concern": "Environmental",
        "water_quality_issue": "Water",
        "streetlight_outage": "Public Works",
        "drainage_problem": "Infrastructure",
        "tree_damage": "Parks",
        "park_maintenance": "Parks",
        "general_inquiry": "311"
    }

    nlp_confidence = round(random.uniform(0.85, 0.99), 2)
    sentiment = round(random.uniform(-0.3, 0.7), 2)

    new_report = {
        "id": report_id,
        "category": report.category,
        "status": "SUBMITTED",
        "location": report.location,
        "description": report.description,
        "severity": report.severity or "medium",
        "reporter_anonymous": report.reporter_anonymous,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "assigned_department": dept_map.get(report.category, "311"),
        "estimated_resolution": random.choice(["1 business day", "3 business days", "1 week"]),
        "nlp_confidence": nlp_confidence,
        "sentiment": sentiment,
        "photos": report.photos or []
    }

    db.reports.append(new_report)
    return new_report


@app.get("/api/v1/citizen/reports")
async def citizen_my_reports(
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
):
    """Track a citizen's own reports by email or phone."""
    # Return mock tracked reports for a citizen
    now = datetime.now()
    mock_reports = [
        {
            "id": "ECO-20260320-482901",
            "category": "illegal_dumping",
            "status": "RESOLVED",
            "location": {"lat": 28.6198, "lng": 77.2085, "address": "MG Road, Karol Bagh"},
            "description": "Bulk waste dumped near community dustbin",
            "created_at": (now - timedelta(days=14)).isoformat(),
            "updated_at": (now - timedelta(days=12)).isoformat(),
            "assigned_department": "Sanitation",
            "estimated_resolution": "3 business days",
            "resolution_notes": "Waste cleared, area sanitized. Fine issued to offender.",
            "votes": 8,
        },
        {
            "id": "ECO-20260315-729301",
            "category": "streetlight_outage",
            "status": "IN_PROGRESS",
            "location": {"lat": 28.6221, "lng": 77.2102, "address": "Block 4, Karol Bagh Market"},
            "description": "3 streetlights not working for past week",
            "created_at": (now - timedelta(days=10)).isoformat(),
            "updated_at": (now - timedelta(days=2)).isoformat(),
            "assigned_department": "Public Works",
            "estimated_resolution": "5 business days",
            "resolution_notes": "Repair scheduled for March 27. New pole ordered.",
            "votes": 12,
        },
        {
            "id": "ECO-20260322-193847",
            "category": "drainage_problem",
            "status": "SUBMITTED",
            "location": {"lat": 28.6178, "lng": 77.2051, "address": "Near Metro Station, Karol Bagh"},
            "description": "Storm drain blocked, waterlogging during rain",
            "created_at": (now - timedelta(days=2)).isoformat(),
            "updated_at": (now - timedelta(days=2)).isoformat(),
            "assigned_department": "Infrastructure",
            "estimated_resolution": "1 week",
            "resolution_notes": None,
            "votes": 3,
        },
    ]
    total = len(mock_reports)
    resolved = sum(1 for r in mock_reports if r["status"] == "RESOLVED")
    return {
        "reports": mock_reports,
        "total": total,
        "resolved": resolved,
        "pending": total - resolved,
        "account_email": email or "citizen@example.com",
    }


# ============================================================================
# METRICS
# ============================================================================

@app.get("/api/v1/metrics/summary")
async def metrics_summary():
    """City-wide sustainability KPI summary."""
    aq_readings = [r for r in db.readings if r.get("sensor_id", "").startswith("aq-")]
    energy_readings = [r for r in db.readings if r.get("meter_id", "").startswith("meter-")]
    waste_readings = [r for r in db.readings if r.get("bin_id", "").startswith("bin-")]

    avg_aqi = sum(r["aqi"] for r in aq_readings[-20:]) / min(len(aq_readings), 20) if aq_readings else 50
    total_energy = sum(r["consumption_kwh"] for r in energy_readings[-50:]) if energy_readings else 0
    avg_fill = sum(r["fill_percent"] for r in waste_readings[-20:]) / min(len(waste_readings), 20) if waste_readings else 50

    active_alerts = len([a for a in db.alerts if a["status"] == "ACTIVE"])
    pending_reports = len([r for r in db.reports if r["status"] != "RESOLVED" and r["status"] != "CLOSED"])

    aqi_score = max(0, 100 - (avg_aqi - 50)) if avg_aqi else 80
    waste_score = max(0, 100 - avg_fill) if avg_fill else 70
    alert_score = max(0, 100 - active_alerts * 5)
    score = int((aqi_score * 0.35 + waste_score * 0.25 + alert_score * 0.2 + 70 * 0.2))

    return {
        "timestamp": datetime.now().isoformat(),
        "sustainability_score": score,
        "energy": {
            "total_kwh_today": round(total_energy, 1),
            "reduction_percent": round(random.uniform(12, 22), 1),
            "trend": "down"
        },
        "waste": {
            "diversion_rate": round(random.uniform(38, 45), 1),
            "bins_critical": len([b for b in waste_readings[-50:] if b.get("fill_percent", 0) > 85]),
            "trend": "improving"
        },
        "air_quality": {
            "aqi": int(avg_aqi),
            "category": "Good" if avg_aqi <= 50 else "Moderate",
            "trend": "stable"
        },
        "alerts": {
            "active": active_alerts,
            "critical": len([a for a in db.alerts if a["severity"] == "CRITICAL" and a["status"] == "ACTIVE"])
        },
        "reports": {
            "pending": pending_reports,
            "submitted_today": len([r for r in db.reports if
                                   datetime.fromisoformat(r["created_at"]).date() == datetime.now().date()])
        }
    }


# ============================================================================
# GREEN SPACE
# ============================================================================

@app.get("/api/v1/green-space/coverage")
async def green_space_coverage():
    """Green space coverage by zone."""
    zones_data = {
        "connaught": {"coverage_pct": 8.2, "trees": 1240, "parks": 3, "canopy_score": 62},
        "chandni": {"coverage_pct": 12.5, "trees": 2180, "parks": 5, "canopy_score": 71},
        "karol": {"coverage_pct": 5.8, "trees": 890, "parks": 2, "canopy_score": 48},
        "saket": {"coverage_pct": 18.3, "trees": 3420, "parks": 8, "canopy_score": 79},
        "dwarka": {"coverage_pct": 22.1, "trees": 4890, "parks": 11, "canopy_score": 85},
    }
    total_trees = sum(z["trees"] for z in zones_data.values())
    avg_coverage = sum(z["coverage_pct"] for z in zones_data.values()) / len(zones_data)
    return {
        "city_avg_coverage_pct": round(avg_coverage, 1),
        "total_trees": total_trees,
        "total_parks": sum(z["parks"] for z in zones_data.values()),
        "zones": zones_data
    }


@app.get("/api/v1/green-space/heat-islands")
async def heat_island_analysis():
    """Urban heat island analysis by zone."""
    zones = ["connaught", "chandni", "karol", "saket", "dwarka"]
    return {
        "analysis_date": datetime.now().isoformat(),
        "baseline_temp": 34.5,
        "zones": [
            {"zone": z, "avg_surface_temp": round(random.uniform(36, 43), 1),
             "delta_from_baseline": round(random.uniform(1.5, 8.5), 1),
             "risk_level": random.choice(["Low", "Moderate", "High", "Critical"])}
            for z in zones
        ]
    }


@app.get("/api/v1/green-space/interventions")
async def green_interventions():
    """Ranked green infrastructure intervention recommendations."""
    interventions = [
        {"id": "INT-001", "zone": "karol", "type": "tree_planting", "priority_score": 94,
         "est_cost": 180000, "est_co2_kg": 42000, "est_cooling_deg": 2.1,
         "description": "Plant 500 mature shade trees along arterial roads",
         "roi_years": 4},
        {"id": "INT-002", "zone": "connaught", "type": "green_roof", "priority_score": 87,
         "est_cost": 320000, "est_co2_kg": 28000, "est_cooling_deg": 1.4,
         "description": "Convert 20 municipal rooftops to green roofs",
         "roi_years": 6},
        {"id": "INT-003", "zone": "karol", "type": "permeable_pavement", "priority_score": 82,
         "est_cost": 240000, "est_co2_kg": 15000, "est_cooling_deg": 0.8,
         "description": "Replace impervious surfaces in 3 parking areas",
         "roi_years": 5},
        {"id": "INT-004", "zone": "chandni", "type": "tree_planting", "priority_score": 78,
         "est_cost": 95000, "est_co2_kg": 22000, "est_cooling_deg": 1.2,
         "description": "Urban forest corridor along canal walkway",
         "roi_years": 3},
        {"id": "INT-005", "zone": "connaught", "type": "rain_garden", "priority_score": 71,
         "est_cost": 65000, "est_co2_kg": 8000, "est_cooling_deg": 0.5,
         "description": "Install 15 bioswales in flood-prone intersections",
         "roi_years": 3},
    ]
    return {"interventions": interventions, "total_est_cost": sum(i["est_cost"] for i in interventions)}


@app.get("/api/v1/green-space/satellite")
async def satellite_analysis():
    """Satellite-derived vegetation index by zone."""
    zones = ["connaught", "chandni", "karol", "saket", "dwarka"]
    return {
        "analysis_date": datetime.now().isoformat(),
        "source": "Sentinel-2 + Landsat-9",
        "resolution_m": 10,
        "ndvi_by_zone": {
            z: round(random.uniform(0.15, 0.55), 2) for z in zones
        },
        "canopy_cover_by_zone": {
            z: round(random.uniform(5, 25), 1) for z in zones
        }
    }


# ============================================================================
# CITIZEN PORTAL
# ============================================================================

@app.get("/api/v1/citizen/stats")
async def citizen_stats():
    """Community-wide citizen engagement stats."""
    return {
        "total_reports": 2847,
        "resolved_this_month": 312,
        "avg_resolution_days": 2.4,
        "reports_by_category": {
            "illegal_dumping": 423,
            "drainage_problem": 287,
            "air_quality_concern": 198,
            "streetlight_outage": 512,
            "noise_complaint": 341,
            "park_maintenance": 189,
            "tree_damage": 156,
            "water_quality_issue": 98,
            "general_inquiry": 643,
        },
        "participation_growth_pct": round(random.uniform(8, 18), 1),
        "active_citizens": 1247,
        "top_reporter_zone": "karol",
        "response_sla_compliance_pct": round(random.uniform(88, 96), 1),
    }


@app.get("/api/v1/citizen/nearby")
async def nearby_issues(lat: float = Query(28.6139), lng: float = Query(77.2090), radius_km: float = Query(1.0)):
    """Issues reported near a location."""
    zones = ["connaught", "chandni", "karol", "saket", "dwarka"]
    lat_base, lng_base = 28.61, 77.20
    issues = []
    for zone in zones:
        offset_lat = (zones.index(zone) % 3) * 0.02
        offset_lng = (zones.index(zone) // 3) * 0.02
        issues.append({
            "id": f"rpt-{zone[:3]}-001",
            "category": random.choice(["illegal_dumping", "drainage_problem", "streetlight_outage", "park_maintenance"]),
            "status": random.choice(["SUBMITTED", "IN_PROGRESS", "RESOLVED"]),
            "distance_km": round(random.uniform(0.1, radius_km), 2),
            "lat": lat_base + offset_lat,
            "lng": lng_base + offset_lng,
            "address": f"{zone.title()} Area, Near Main Road",
            "reported_at": (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
            "votes": random.randint(0, 24),
        })
    issues.sort(key=lambda x: x["distance_km"])
    return {"issues": issues[:10], "search_radius_km": radius_km}


@app.get("/api/v1/citizen/community")
async def community_stats():
    """Weekly community engagement summary."""
    weeks = ["2026-W10", "2026-W11", "2026-W12", "2026-W13"]
    weekly_data = []
    base_count = 180
    for i, week in enumerate(weeks):
        count = base_count + i * 18 + random.randint(-10, 20)
        weekly_data.append({
            "week": week,
            "reports_submitted": count,
            "reports_resolved": int(count * random.uniform(0.75, 0.92)),
            "new_citizens": random.randint(10, 35),
            "avg_sentiment": round(random.uniform(-0.1, 0.4), 2),
        })
    return {"weekly": weekly_data, "total_citizens": 1247, "growth_pct": round(random.uniform(5, 12), 1)}


# ============================================================================
# PLANNER DASHBOARD
# ============================================================================

@app.get("/api/v1/planner/zoning")
async def zoning_overview():
    """Zone-level planning data combining all sensor types."""
    zones_data = {
        "connaught": {
            "area_km2": 4.2, "population": 28000, "green_coverage_pct": 8.2,
            "energy_kwh_per_capita": 420, "waste_kg_per_capita_day": 1.8,
            "avg_aqi": 178, "density": "high", "land_use": "commercial",
            "priority_score": 87, "investment_need": 1200000,
        },
        "chandni": {
            "area_km2": 6.1, "population": 42000, "green_coverage_pct": 12.5,
            "energy_kwh_per_capita": 380, "waste_kg_per_capita_day": 1.5,
            "avg_aqi": 163, "density": "medium", "land_use": "mixed_residential",
            "priority_score": 72, "investment_need": 850000,
        },
        "karol": {
            "area_km2": 5.8, "population": 65000, "green_coverage_pct": 5.8,
            "energy_kwh_per_capita": 510, "waste_kg_per_capita_day": 2.1,
            "avg_aqi": 192, "density": "very_high", "land_use": "residential",
            "priority_score": 95, "investment_need": 2100000,
        },
        "saket": {
            "area_km2": 7.3, "population": 38000, "green_coverage_pct": 18.3,
            "energy_kwh_per_capita": 340, "waste_kg_per_capita_day": 1.2,
            "avg_aqi": 152, "density": "medium", "land_use": "residential",
            "priority_score": 58, "investment_need": 450000,
        },
        "dwarka": {
            "area_km2": 12.4, "population": 52000, "green_coverage_pct": 22.1,
            "energy_kwh_per_capita": 290, "waste_kg_per_capita_day": 1.0,
            "avg_aqi": 142, "density": "low", "land_use": "suburban",
            "priority_score": 34, "investment_need": 320000,
        },
    }
    return {"zones": zones_data, "city_area_km2": sum(z["area_km2"] for z in zones_data.values()), "total_population": sum(z["population"] for z in zones_data.values())}


@app.get("/api/v1/planner/roi")
async def planner_roi():
    """ROI projections for planned infrastructure investments."""
    investments = [
        {"id": "INV-001", "zone": "karol", "type": "tree_planting", "cost": 180000, "annual_savings": 42000, "co2_kg": 42000, "health_benefit_usd": 28000, "payback_years": 4.3},
        {"id": "INV-002", "zone": "connaught", "type": "green_roof", "cost": 320000, "annual_savings": 38000, "co2_kg": 28000, "health_benefit_usd": 22000, "payback_years": 6.8},
        {"id": "INV-003", "zone": "karol", "type": "permeable_pavement", "cost": 240000, "annual_savings": 31000, "co2_kg": 15000, "health_benefit_usd": 15000, "payback_years": 5.4},
        {"id": "INV-004", "zone": "chandni", "type": "tree_planting", "cost": 95000, "annual_savings": 24000, "co2_kg": 22000, "health_benefit_usd": 18000, "payback_years": 3.9},
        {"id": "INV-005", "zone": "connaught", "type": "rain_garden", "cost": 65000, "annual_savings": 18000, "co2_kg": 8000, "health_benefit_usd": 9000, "payback_years": 3.6},
        {"id": "INV-006", "zone": "karol", "type": "solar_canopy", "cost": 480000, "annual_savings": 72000, "co2_kg": 55000, "health_benefit_usd": 0, "payback_years": 6.7},
        {"id": "INV-007", "zone": "saket", "type": "wetland_restoration", "cost": 210000, "annual_savings": 15000, "co2_kg": 38000, "health_benefit_usd": 42000, "payback_years": 9.8},
        {"id": "INV-008", "zone": "dwarka", "type": "community_garden", "cost": 55000, "annual_savings": 8000, "co2_kg": 6000, "health_benefit_usd": 15000, "payback_years": 3.4},
    ]
    total_cost = sum(i["cost"] for i in investments)
    total_savings = sum(i["annual_savings"] for i in investments)
    return {
        "investments": investments,
        "total_cost": total_cost,
        "total_annual_savings": total_savings,
        "avg_payback_years": round(total_cost / total_savings, 1),
        "total_co2_kg_yr": sum(i["co2_kg"] for i in investments),
        "total_health_benefit_usd": sum(i["health_benefit_usd"] for i in investments),
        "five_year_roi_pct": round(((total_savings * 5) / total_cost) * 100, 1),
    }


@app.get("/api/v1/planner/timeline")
async def planner_timeline():
    """Phased implementation timeline for all planned interventions."""
    phases = [
        {
            "quarter": "2026-Q2",
            "activities": [
                {"name": "Karol Zone Tree Planting (Phase 1)", "budget": 60000, "status": "in_progress", "completion_pct": 45},
                {"name": "Connaught Green Roof Survey", "budget": 15000, "status": "in_progress", "completion_pct": 20},
            ],
        },
        {
            "quarter": "2026-Q3",
            "activities": [
                {"name": "Karol Tree Planting Completion", "budget": 120000, "status": "planned", "completion_pct": 0},
                {"name": "Canal Walk Urban Forest Corridor", "budget": 95000, "status": "planned", "completion_pct": 0},
                {"name": "Connaught Rain Garden Installation", "budget": 65000, "status": "planned", "completion_pct": 0},
            ],
        },
        {
            "quarter": "2026-Q4",
            "activities": [
                {"name": "Connaught Green Roof Construction", "budget": 320000, "status": "planned", "completion_pct": 0},
                {"name": "Karol Permeable Pavement Pilot", "budget": 240000, "status": "planned", "completion_pct": 0},
            ],
        },
        {
            "quarter": "2027-Q1",
            "activities": [
                {"name": "Karol Solar Canopy Installation", "budget": 480000, "status": "planned", "completion_pct": 0},
                {"name": "Dwarka Community Garden Setup", "budget": 55000, "status": "planned", "completion_pct": 0},
            ],
        },
    ]
    return {"phases": phases, "total_budget": sum(a["budget"] for p in phases for a in p["activities"])}


@app.get("/api/v1/planner/scenarios")
async def planning_scenarios():
    """Alternative planning scenarios for what-if analysis."""
    return {
        "scenarios": [
            {
                "id": "conservative",
                "name": "Conservative",
                "description": "Focus on maintenance and small-scale improvements",
                "total_budget": 380000,
                "co2_reduction_kg_yr": 32000,
                "priority_zones": ["karol", "connaught"],
                "projects": 4,
            },
            {
                "id": "balanced",
                "name": "Balanced Growth",
                "description": "Mix of green infrastructure and energy efficiency",
                "total_budget": 950000,
                "co2_reduction_kg_yr": 98000,
                "priority_zones": ["karol", "chandni", "connaught"],
                "projects": 8,
            },
            {
                "id": "ambitious",
                "name": "Ambitious Transformation",
                "description": "Comprehensive green infrastructure across all zones",
                "total_budget": 2100000,
                "co2_reduction_kg_yr": 185000,
                "priority_zones": ["karol", "chandni", "connaught", "saket", "dwarka"],
                "projects": 14,
            },
        ]
    }


# ============================================================================
# PREDICTIONS
# ============================================================================

@app.get("/api/v1/predictions/energy")
async def predictions_energy():
    return prediction_service.get_energy_forecast(24)


@app.get("/api/v1/predictions/aqi")
async def predictions_aqi():
    return prediction_service.get_aqi_forecast(48)


@app.get("/api/v1/predictions/overflow")
async def predictions_overflow():
    return {"predictions": prediction_service.get_overflow_predictions()}


# ============================================================================
# WEBSOCKET
# ============================================================================

@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    db.ws_clients.append(websocket)
    try:
        while True:
            await asyncio.sleep(5)

            if not db.sensors:
                continue

            sensor = random.choice(db.sensors)
            if sensor["type"] == "air_quality":
                latest = [r for r in db.readings if r.get("sensor_id") == sensor["id"]]
                if latest:
                    reading = sorted(latest, key=lambda x: x["timestamp"], reverse=True)[0]
                    await websocket.send_json({
                        "type": "sensor_update",
                        "sensor_id": sensor["id"],
                        "data": reading
                    })

            if random.random() < 0.3 and db.alerts:
                recent = [a for a in db.alerts if a["status"] == "ACTIVE"]
                if recent:
                    alert = random.choice(recent)
                    await websocket.send_json({
                        "type": "alert",
                        "alert": alert
                    })

    except WebSocketDisconnect:
        if websocket in db.ws_clients:
            db.ws_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
