import type {
  AQCurrent, AQForecast, EnergyConsumption, EnergyForecast,
  WasteBinsResponse, OverflowRiskResponse,
  AlertsResponse, AlertStats,
  ReportsResponse, MetricsSummary, GeoJSONFeatureCollection,
  GreenSpaceCoverage, HeatIslandAnalysis, InterventionsResponse, SatelliteAnalysis,
  CitizenStats, NearbyIssuesResponse, CommunityStatsResponse, MyReportsResponse,
  ZoningOverviewResponse, PlannerROIResponse, PlannerTimelineResponse, PlanningScenariosResponse
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  sensors: {
    list: (params?: { skip?: number; limit?: number; type?: string }) => {
      const qs = new URLSearchParams();
      if (params?.skip) qs.set('skip', String(params.skip));
      if (params?.limit) qs.set('limit', String(params.limit));
      if (params?.type) qs.set('type', params.type);
      return fetcher<{ total: number; sensors: any[] }>(`/api/v1/sensors?${qs}`);
    },
    geojson: () => fetcher<GeoJSONFeatureCollection>('/api/v1/sensors/geojson'),
  },
  airQuality: {
    current: () => fetcher<AQCurrent>('/api/v1/aq/current'),
    forecast: () => fetcher<AQForecast>('/api/v1/aq/forecast'),
    history: (params?: { start_date?: string; end_date?: string; zone?: string }) => {
      const qs = new URLSearchParams();
      if (params?.zone) qs.set('zone', params.zone);
      return fetcher<{ readings: any[]; count: number }>(`/api/v1/aq/history?${qs}`);
    },
  },
  energy: {
    consumption: (params?: { period?: string }) => {
      const qs = new URLSearchParams();
      if (params?.period) qs.set('period', params.period);
      return fetcher<EnergyConsumption>(`/api/v1/energy/consumption?${qs}`);
    },
    forecast: () => fetcher<EnergyForecast>('/api/v1/energy/forecast'),
    peaks: () => fetcher<{ peaks: any[] }>('/api/v1/energy/peaks'),
  },
  waste: {
    bins: (params?: { status?: string; zone?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.status) qs.set('status', params.status);
      if (params?.zone) qs.set('zone', params.zone);
      if (params?.limit) qs.set('limit', String(params.limit));
      return fetcher<WasteBinsResponse>(`/api/v1/waste/bins?${qs}`);
    },
    overflowRisk: () => fetcher<OverflowRiskResponse>('/api/v1/waste/overflow-risk'),
    diversion: () => fetcher<any>('/api/v1/waste/diversion'),
  },
  alerts: {
    list: (params?: { severity?: string; status?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params?.severity) qs.set('severity', params.severity);
      if (params?.status) qs.set('status', params.status);
      if (params?.limit) qs.set('limit', String(params.limit));
      return fetcher<AlertsResponse>(`/api/v1/alerts?${qs}`);
    },
    stats: () => fetcher<AlertStats>('/api/v1/alerts/stats'),
    acknowledge: (id: string) =>
      fetch(`${API_BASE}/api/v1/alerts/${id}/acknowledge`, { method: 'PUT' }).then(r => r.json()),
    resolve: (id: string) =>
      fetch(`${API_BASE}/api/v1/alerts/${id}/resolve`, { method: 'PUT' }).then(r => r.json()),
  },
  reports: {
    list: (params?: { status?: string; category?: string; page?: number }) => {
      const qs = new URLSearchParams();
      if (params?.status) qs.set('status', params.status);
      if (params?.category) qs.set('category', params.category);
      if (params?.page) qs.set('page', String(params.page));
      return fetcher<ReportsResponse>(`/api/v1/reports?${qs}`);
    },
    create: (data: any) =>
      fetch(`${API_BASE}/api/v1/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }).then(r => r.json()),
  },
  metrics: {
    summary: () => fetcher<MetricsSummary>('/api/v1/metrics/summary'),
  },
  predictions: {
    energy: () => fetcher<EnergyForecast>('/api/v1/predictions/energy'),
    aqi: () => fetcher<AQForecast>('/api/v1/predictions/aqi'),
    overflow: () => fetcher<OverflowRiskResponse>('/api/v1/predictions/overflow'),
  },
  greenSpace: {
    coverage: () => fetcher<GreenSpaceCoverage>('/api/v1/green-space/coverage'),
    heatIslands: () => fetcher<HeatIslandAnalysis>('/api/v1/green-space/heat-islands'),
    interventions: () => fetcher<InterventionsResponse>('/api/v1/green-space/interventions'),
    satellite: () => fetcher<SatelliteAnalysis>('/api/v1/green-space/satellite'),
  },
  citizen: {
    stats: () => fetcher<CitizenStats>('/api/v1/citizen/stats'),
    nearby: (params?: { lat?: number; lng?: number; radius_km?: number }) => {
      const qs = new URLSearchParams();
      if (params?.lat) qs.set('lat', String(params.lat));
      if (params?.lng) qs.set('lng', String(params.lng));
      if (params?.radius_km) qs.set('radius_km', String(params.radius_km));
      return fetcher<NearbyIssuesResponse>(`/api/v1/citizen/nearby?${qs}`);
    },
    community: () => fetcher<CommunityStatsResponse>('/api/v1/citizen/community'),
    myReports: (params?: { email?: string; phone?: string }) => {
      const qs = new URLSearchParams();
      if (params?.email) qs.set('email', params.email);
      if (params?.phone) qs.set('phone', params.phone || '');
      return fetcher<MyReportsResponse>(`/api/v1/citizen/reports?${qs}`);
    },
  },
  planner: {
    zoning: () => fetcher<ZoningOverviewResponse>('/api/v1/planner/zoning'),
    roi: () => fetcher<PlannerROIResponse>('/api/v1/planner/roi'),
    timeline: () => fetcher<PlannerTimelineResponse>('/api/v1/planner/timeline'),
    scenarios: () => fetcher<PlanningScenariosResponse>('/api/v1/planner/scenarios'),
  },
};
