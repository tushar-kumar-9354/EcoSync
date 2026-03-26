export interface AQStation {
  id: string;
  name: string;
  lat: number;
  lng: number;
  aqi: number;
  category: string;
  pm25: number;
  pm10: number;
  no2: number;
  o3: number;
  co: number;
  timestamp?: string;
}

export interface AQCurrent {
  timestamp: string;
  aqi: number;
  category: string;
  dominant_pollutant: string;
  stations: AQStation[];
}

export interface AQPrediction {
  id: string;
  type: string;
  timestamp: string;
  horizon: string;
  value: number;
  unit: string;
  confidence_interval: {
    lower: number;
    upper: number;
    confidence: number;
  };
  model_version: string;
}

export interface AQForecast {
  hourly: AQPrediction[];
  trend: string;
  dominant_pollutant: string;
}

export interface EnergyConsumption {
  period: string;
  total_kwh: number;
  avg_kw: number;
  data: Array<{ timestamp: string; consumption_kwh: number }>;
}

export interface EnergyForecast {
  predictions: AQPrediction[];
  base_demand: number;
  peak_expected: boolean;
  peak_hour?: string;
}

export interface WasteBin {
  id: string;
  name: string;
  type: string;
  zone: string;
  lat: number;
  lng: number;
  fill_percent: number;
  overflow_risk: number;
  status: string;
  last_reading?: string;
}

export interface WasteBinsResponse {
  bins: WasteBin[];
  total: number;
}

export interface OverflowPrediction {
  bin_id: string;
  name: string;
  current_fill: number;
  overflow_risk_2h: number;
  recommended_action: string;
  zone: string;
  lat: number;
  lng: number;
}

export interface OverflowRiskResponse {
  predictions: OverflowPrediction[];
  count: number;
}

export interface Alert {
  id: string;
  type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED';
  title: string;
  message: string;
  location: { lat: number; lng: number; address: string };
  current_value: number;
  threshold: number;
  unit: string;
  triggered_at: string;
  acknowledged_at?: string;
  resolved_at?: string;
  acknowledged_by?: string;
  assigned_to?: string;
  tags: string[];
}

export interface AlertsResponse {
  alerts: Alert[];
  total: number;
}

export interface AlertStats {
  total_active: number;
  by_severity: { CRITICAL: number; HIGH: number; MEDIUM: number; LOW: number };
  acknowledged: number;
  resolved_today: number;
}

export interface CitizenReport {
  id: string;
  category: string;
  status: string;
  location: { lat: number; lng: number; address: string };
  description: string;
  severity?: string;
  reporter_anonymous: boolean;
  created_at: string;
  updated_at: string;
  assigned_department: string;
  estimated_resolution: string;
  nlp_confidence: number;
  sentiment?: number;
  photos: string[];
}

export interface ReportsResponse {
  reports: CitizenReport[];
  total: number;
  page: number;
}

export interface MetricsSummary {
  timestamp: string;
  sustainability_score: number;
  energy: {
    total_kwh_today: number;
    reduction_percent: number;
    trend: string;
  };
  waste: {
    diversion_rate: number;
    bins_critical: number;
    trend: string;
  };
  air_quality: {
    aqi: number;
    category: string;
    trend: string;
  };
  alerts: {
    active: number;
    critical: number;
  };
  reports: {
    pending: number;
    submitted_today: number;
  };
}

export interface GeoJSONFeature {
  type: 'Feature';
  geometry: { type: 'Point'; coordinates: [number, number] };
  properties: Record<string, any>;
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

export interface GreenSpaceCoverage {
  city_avg_coverage_pct: number;
  total_trees: number;
  total_parks: number;
  zones: Record<string, {
    coverage_pct: number;
    trees: number;
    parks: number;
    canopy_score: number;
  }>;
}

export interface HeatIslandZone {
  zone: string;
  avg_surface_temp: number;
  delta_from_baseline: number;
  risk_level: string;
}

export interface HeatIslandAnalysis {
  analysis_date: string;
  baseline_temp: number;
  zones: HeatIslandZone[];
}

export interface GreenIntervention {
  id: string;
  zone: string;
  type: string;
  priority_score: number;
  est_cost: number;
  est_co2_kg: number;
  est_cooling_deg: number;
  description: string;
  roi_years: number;
}

export interface InterventionsResponse {
  interventions: GreenIntervention[];
  total_est_cost: number;
}

export interface SatelliteAnalysis {
  analysis_date: string;
  source: string;
  resolution_m: number;
  ndvi_by_zone: Record<string, number>;
  canopy_cover_by_zone: Record<string, number>;
}

// Citizen Portal Types
export interface CitizenStats {
  total_reports: number;
  resolved_this_month: number;
  avg_resolution_days: number;
  reports_by_category: Record<string, number>;
  participation_growth_pct: number;
  active_citizens: number;
  top_reporter_zone: string;
  response_sla_compliance_pct: number;
}

export interface NearbyIssue {
  id: string;
  category: string;
  status: string;
  distance_km: number;
  lat: number;
  lng: number;
  address: string;
  reported_at: string;
  votes: number;
}

export interface NearbyIssuesResponse {
  issues: NearbyIssue[];
  search_radius_km: number;
}

export interface WeeklyCommunityData {
  week: string;
  reports_submitted: number;
  reports_resolved: number;
  new_citizens: number;
  avg_sentiment: number;
}

export interface CommunityStatsResponse {
  weekly: WeeklyCommunityData[];
  total_citizens: number;
  growth_pct: number;
}

export interface TrackedReport {
  id: string;
  category: string;
  status: string;
  location: { lat: number; lng: number; address: string };
  description: string;
  created_at: string;
  updated_at: string;
  assigned_department: string;
  estimated_resolution: string;
  resolution_notes: string | null;
  votes: number;
}

export interface MyReportsResponse {
  reports: TrackedReport[];
  total: number;
  resolved: number;
  pending: number;
  account_email: string;
}

// Planner Dashboard Types
export interface ZonePlanningData {
  area_km2: number;
  population: number;
  green_coverage_pct: number;
  energy_kwh_per_capita: number;
  waste_kg_per_capita_day: number;
  avg_aqi: number;
  density: string;
  land_use: string;
  priority_score: number;
  investment_need: number;
}

export interface ZoningOverviewResponse {
  zones: Record<string, ZonePlanningData>;
  city_area_km2: number;
  total_population: number;
}

export interface PlannerInvestment {
  id: string;
  zone: string;
  type: string;
  cost: number;
  annual_savings: number;
  co2_kg: number;
  health_benefit_usd: number;
  payback_years: number;
}

export interface PlannerROIResponse {
  investments: PlannerInvestment[];
  total_cost: number;
  total_annual_savings: number;
  avg_payback_years: number;
  total_co2_kg_yr: number;
  total_health_benefit_usd: number;
  five_year_roi_pct: number;
}

export interface TimelineActivity {
  name: string;
  budget: number;
  status: string;
  completion_pct: number;
}

export interface TimelinePhase {
  quarter: string;
  activities: TimelineActivity[];
}

export interface PlannerTimelineResponse {
  phases: TimelinePhase[];
  total_budget: number;
}

export interface PlanningScenario {
  id: string;
  name: string;
  description: string;
  total_budget: number;
  co2_reduction_kg_yr: number;
  priority_zones: string[];
  projects: number;
}

export interface PlanningScenariosResponse {
  scenarios: PlanningScenario[];
}
