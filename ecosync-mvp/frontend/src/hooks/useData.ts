'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  AQCurrent, AQForecast, EnergyConsumption, EnergyForecast,
  WasteBinsResponse, OverflowRiskResponse,
  AlertsResponse, AlertStats,
  ReportsResponse, MetricsSummary, GeoJSONFeatureCollection,
  GreenSpaceCoverage, HeatIslandAnalysis, InterventionsResponse, SatelliteAnalysis,
  CitizenStats, NearbyIssuesResponse, CommunityStatsResponse, MyReportsResponse,
  ZoningOverviewResponse, PlannerROIResponse, PlannerTimelineResponse, PlanningScenariosResponse
} from '@/types';

export function useMetrics() {
  return useQuery<MetricsSummary>({ queryKey: ['metrics', 'summary'], queryFn: api.metrics.summary, refetchInterval: 30000 });
}

export function useAlerts(params?: { severity?: string; status?: string; limit?: number }) {
  return useQuery<AlertsResponse>({ queryKey: ['alerts', params], queryFn: () => api.alerts.list(params), refetchInterval: 15000 });
}

export function useAlertStats() {
  return useQuery<AlertStats>({ queryKey: ['alerts', 'stats'], queryFn: api.alerts.stats, refetchInterval: 10000 });
}

export function useSensorGeoJSON() {
  return useQuery<GeoJSONFeatureCollection>({ queryKey: ['sensors', 'geojson'], queryFn: api.sensors.geojson, refetchInterval: 30000 });
}

export function useAirQuality() {
  return useQuery<AQCurrent>({ queryKey: ['aq', 'current'], queryFn: api.airQuality.current, refetchInterval: 20000 });
}

export function useAQForecast() {
  return useQuery<AQForecast>({ queryKey: ['aq', 'forecast'], queryFn: api.airQuality.forecast, refetchInterval: 60000 });
}

export function useEnergyConsumption(period = '24h') {
  return useQuery<EnergyConsumption>({ queryKey: ['energy', 'consumption', period], queryFn: () => api.energy.consumption({ period }), refetchInterval: 30000 });
}

export function useEnergyForecast() {
  return useQuery<EnergyForecast>({ queryKey: ['energy', 'forecast'], queryFn: api.energy.forecast, refetchInterval: 60000 });
}

export function useWasteBins(params?: { status?: string; zone?: string; limit?: number }) {
  return useQuery<WasteBinsResponse>({ queryKey: ['waste', 'bins', params], queryFn: () => api.waste.bins(params), refetchInterval: 20000 });
}

export function useOverflowRisk() {
  return useQuery<OverflowRiskResponse>({ queryKey: ['waste', 'overflow'], queryFn: api.waste.overflowRisk, refetchInterval: 30000 });
}

export function usePredictions() {
  return useQuery<EnergyForecast>({ queryKey: ['predictions'], queryFn: () => api.predictions.energy(), refetchInterval: 60000 });
}

export function useReports(params?: { status?: string; category?: string; page?: number }) {
  return useQuery<ReportsResponse>({ queryKey: ['reports', params], queryFn: () => api.reports.list(params), refetchInterval: 30000 });
}

export function useGreenSpaceCoverage() {
  return useQuery<GreenSpaceCoverage>({ queryKey: ['green-space', 'coverage'], queryFn: api.greenSpace.coverage, refetchInterval: 60000 });
}

export function useHeatIslandAnalysis() {
  return useQuery<HeatIslandAnalysis>({ queryKey: ['green-space', 'heat-islands'], queryFn: api.greenSpace.heatIslands, refetchInterval: 120000 });
}

export function useGreenInterventions() {
  return useQuery<InterventionsResponse>({ queryKey: ['green-space', 'interventions'], queryFn: api.greenSpace.interventions, refetchInterval: 120000 });
}

export function useSatelliteAnalysis() {
  return useQuery<SatelliteAnalysis>({ queryKey: ['green-space', 'satellite'], queryFn: api.greenSpace.satellite, refetchInterval: 300000 });
}

export function useCitizenStats() {
  return useQuery<CitizenStats>({ queryKey: ['citizen', 'stats'], queryFn: api.citizen.stats, refetchInterval: 60000 });
}

export function useNearbyIssues(params?: { lat?: number; lng?: number; radius_km?: number }) {
  return useQuery<NearbyIssuesResponse>({ queryKey: ['citizen', 'nearby', params], queryFn: () => api.citizen.nearby(params), refetchInterval: 30000 });
}

export function useCommunityStats() {
  return useQuery<CommunityStatsResponse>({ queryKey: ['citizen', 'community'], queryFn: api.citizen.community, refetchInterval: 120000 });
}

export function useMyReports(params?: { email?: string; phone?: string }) {
  return useQuery<MyReportsResponse>({ queryKey: ['citizen', 'reports', params], queryFn: () => api.citizen.myReports(params), refetchInterval: 30000 });
}

export function useZoningOverview() {
  return useQuery<ZoningOverviewResponse>({ queryKey: ['planner', 'zoning'], queryFn: api.planner.zoning, refetchInterval: 60000 });
}

export function usePlannerROI() {
  return useQuery<PlannerROIResponse>({ queryKey: ['planner', 'roi'], queryFn: api.planner.roi, refetchInterval: 120000 });
}

export function usePlannerTimeline() {
  return useQuery<PlannerTimelineResponse>({ queryKey: ['planner', 'timeline'], queryFn: api.planner.timeline, refetchInterval: 300000 });
}

export function usePlanningScenarios() {
  return useQuery<PlanningScenariosResponse>({ queryKey: ['planner', 'scenarios'], queryFn: api.planner.scenarios, refetchInterval: 300000 });
}
