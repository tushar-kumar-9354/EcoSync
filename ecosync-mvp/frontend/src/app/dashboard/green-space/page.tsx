'use client';

import { useGreenSpaceCoverage, useHeatIslandAnalysis, useGreenInterventions, useSatelliteAnalysis } from '@/hooks/useData';
import { Card, Badge, Progress } from '@/components/ui';
import { CoverageRadarChart, HeatIslandBarChart, InterventionPriorityChart, NdviZoneChart } from '@/components/charts';
import { useState } from 'react';

function getRiskColor(level: string) {
  switch (level) {
    case 'Critical': return '#FF3B3B';
    case 'High': return '#FF8C00';
    case 'Moderate': return '#FFD300';
    case 'Low': return '#00C853';
    default: return '#888';
  }
}

export default function GreenSpaceDashboard() {
  const { data: coverage } = useGreenSpaceCoverage();
  const { data: heatIslands } = useHeatIslandAnalysis();
  const { data: interventions } = useGreenInterventions();
  const { data: satellite } = useSatelliteAnalysis();
  const [selectedZone, setSelectedZone] = useState<string>('all');

  const zones = coverage ? Object.entries(coverage.zones) : [];

  // Filter interventions by zone
  const filteredInterventions = interventions?.interventions.filter(
    i => selectedZone === 'all' || i.zone === selectedZone
  ) || [];

  const totalCost = filteredInterventions.reduce((s, i) => s + i.est_cost, 0);
  const totalCO2 = filteredInterventions.reduce((s, i) => s + i.est_co2_kg, 0);

  // Coverage data for radar-like display
  const coverageData = zones.map(([zone, data]) => ({
    zone: zone.charAt(0).toUpperCase() + zone.slice(1),
    coverage: data.coverage_pct,
    trees: data.trees / 100,
    parks: data.parks,
    canopy: data.canopy_score,
  }));

  // Heat island data
  const heatData = heatIslands?.zones || [];

  // Intervention type labels
  const typeLabels: Record<string, string> = {
    tree_planting: 'Tree Planting',
    green_roof: 'Green Roof',
    permeable_pavement: 'Permeable Pavement',
    rain_garden: 'Rain Garden',
    urban_forest: 'Urban Forest Corridor',
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Green Space & Infrastructure</h1>
          <p className="text-sm text-gray-400 mt-1">Vegetation coverage, heat island analysis, and intervention planning</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setSelectedZone('all')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${selectedZone === 'all' ? 'bg-primary text-bg-primary' : 'bg-bg-elevated text-gray-400 hover:text-white'}`}>
            All Zones
          </button>
          {zones.map(([zone]) => (
            <button key={zone} onClick={() => setSelectedZone(zone)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${selectedZone === zone ? 'bg-primary text-bg-primary' : 'bg-bg-elevated text-gray-400 hover:text-white'}`}>
              {zone.charAt(0).toUpperCase() + zone.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <p className="text-sm text-gray-400">City Avg Coverage</p>
          <p className="text-3xl font-bold text-green-400 mt-1">{coverage?.city_avg_coverage_pct || 0}%</p>
          <p className="text-xs text-gray-500 mt-1">green space</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Total Trees</p>
          <p className="text-3xl font-bold text-white mt-1">{(coverage?.total_trees || 0).toLocaleString()}</p>
          <p className="text-xs text-gray-500 mt-1">planted & monitored</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Total Parks</p>
          <p className="text-3xl font-bold text-white mt-1">{coverage?.total_parks || 0}</p>
          <p className="text-xs text-gray-500 mt-1">parks & green areas</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Interventions Planned</p>
          <p className="text-3xl font-bold text-primary mt-1">{filteredInterventions.length}</p>
          <p className="text-xs text-gray-500 mt-1">${(totalCost / 1000).toLocaleString()}K est. investment</p>
        </Card>
      </div>

      {/* Coverage Overview + Heat Island Analysis */}
      <div className="grid grid-cols-12 gap-6">
        <Card className="col-span-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Zone Coverage Overview</h3>
          <div className="space-y-3">
            {zones.map(([zone, data]) => (
              <div key={zone}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-white capitalize">{zone}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-400">{data.coverage_pct}%</span>
                    <span className="text-xs text-gray-400">{data.trees.toLocaleString()} trees</span>
                  </div>
                </div>
                <Progress
                  value={data.coverage_pct * 4}
                  max={100}
                  color={data.coverage_pct > 15 ? '#00C853' : data.coverage_pct > 10 ? '#5EF5A7' : data.coverage_pct > 6 ? '#FFD300' : '#FF3B3B'}
                />
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-bg-tertiary">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
                <p className="text-xl font-bold text-green-400">5</p>
                <p className="text-xs text-gray-400">Zones Analyzed</p>
              </div>
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
                <p className="text-xl font-bold text-green-400">{satellite ? Object.keys(satellite.ndvi_by_zone).length : 0}</p>
                <p className="text-xs text-gray-400">NDVI Readings</p>
              </div>
            </div>
          </div>
        </Card>

        <Card className="col-span-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Vegetation Index by Zone (NDVI)</h3>
            {satellite && (
              <span className="text-xs text-gray-500">Source: {satellite.source}</span>
            )}
          </div>
          {satellite && (
            <NdviZoneChart ndvi={satellite.ndvi_by_zone} height={200} />
          )}
          <div className="mt-4 grid grid-cols-5 gap-2">
            {satellite && Object.entries(satellite.ndvi_by_zone).map(([zone, ndvi]) => (
              <div key={zone} className="p-2 rounded bg-bg-tertiary text-center">
                <p className="text-xs text-gray-400 capitalize">{zone}</p>
                <p className="text-sm font-bold text-white">{ndvi}</p>
                <p className="text-xs text-gray-500">NDVI</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Heat Island Analysis */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Urban Heat Island Analysis</h3>
            {heatIslands && (
              <span className="text-xs text-gray-500">Baseline: {heatIslands.baseline_temp}°C</span>
            )}
          </div>
          {heatData.length > 0 && (
            <HeatIslandBarChart zones={heatData} height={200} />
          )}
          <div className="mt-4 space-y-2">
            {heatData.map((z) => (
              <div key={z.zone} className="flex items-center justify-between p-2 rounded-lg bg-bg-tertiary">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: getRiskColor(z.risk_level) }} />
                  <span className="text-sm text-white capitalize">{z.zone}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-400">+{z.delta_from_baseline}°C</span>
                  <Badge variant={z.risk_level === 'Critical' || z.risk_level === 'High' ? 'critical' : z.risk_level === 'Moderate' ? 'medium' : 'low'}>
                    {z.risk_level}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Canopy Score by Zone</h3>
          <CoverageRadarChart data={coverageData} height={280} />
        </Card>
      </div>

      {/* Intervention Recommendations */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-300">Intervention Recommendations</h3>
            <p className="text-xs text-gray-500 mt-1">Ranked by priority — highest impact green infrastructure investments</p>
          </div>
          <div className="text-right">
            <p className="text-sm font-bold text-white">${(totalCost / 1000000).toFixed(2)}M</p>
            <p className="text-xs text-gray-500">Total Investment</p>
          </div>
        </div>

        <div className="space-y-3">
          {filteredInterventions.map((intervention) => (
            <div key={intervention.id} className="p-4 rounded-lg bg-bg-tertiary border border-bg-elevated hover:border-gray-600 transition-all">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <Badge variant="default">{typeLabels[intervention.type] || intervention.type}</Badge>
                    <span className="text-xs text-gray-500 capitalize">{intervention.zone}</span>
                    <span className="text-xs text-gray-600">•</span>
                    <span className="text-xs text-gray-500 font-mono">{intervention.id}</span>
                  </div>
                  <p className="text-sm text-white mt-1">{intervention.description}</p>
                  <div className="flex items-center gap-6 mt-2 text-xs text-gray-500 flex-wrap">
                    <span>Est. Cost: <span className="text-white">${intervention.est_cost.toLocaleString()}</span></span>
                    <span>CO₂ Offset: <span className="text-green-400">{intervention.est_co2_kg.toLocaleString()} kg/yr</span></span>
                    <span>Cooling: <span className="text-blue-400">-{intervention.est_cooling_deg}°C</span></span>
                    <span>ROI: <span className="text-white">{intervention.roi_years} yrs</span></span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-primary">{intervention.priority_score}</p>
                  <p className="text-xs text-gray-500">Priority</p>
                  <Progress
                    value={intervention.priority_score}
                    max={100}
                    color="#00C853"
                    className="mt-2"
                  />
                </div>
              </div>
            </div>
          ))}
          {filteredInterventions.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No interventions planned for this zone
            </div>
          )}
        </div>

        {interventions && (
          <div className="mt-4 pt-4 border-t border-bg-tertiary">
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <p className="text-xl font-bold text-white">{(totalCO2 / 1000).toFixed(0)}t</p>
                <p className="text-xs text-gray-500">Est. CO₂ Offset/yr</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-green-400">{filteredInterventions.length}</p>
                <p className="text-xs text-gray-500">Interventions</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-blue-400">
                  -{filteredInterventions.reduce((s, i) => s + i.est_cooling_deg, 0).toFixed(1)}°C
                </p>
                <p className="text-xs text-gray-500">Combined Cooling</p>
              </div>
              <div className="text-center">
                <p className="text-xl font-bold text-primary">
                  ${(totalCost / 1000).toLocaleString()}K
                </p>
                <p className="text-xs text-gray-500">Total Investment</p>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-6">
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-3">CO₂ Sequestration Potential</h3>
          <div className="space-y-3">
            {[
              { activity: 'Tree Planting (500 trees)', co2: 42000, color: '#00C853' },
              { activity: 'Green Roofs (20 sites)', co2: 28000, color: '#5EF5A7' },
              { activity: 'Urban Forest Corridor', co2: 22000, color: '#5EF5A7' },
              { activity: 'Permeable Pavement', co2: 15000, color: '#FFD300' },
              { activity: 'Rain Gardens (15)', co2: 8000, color: '#FFD300' },
            ].map((item) => (
              <div key={item.activity} className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-sm text-gray-300 flex-1">{item.activity}</span>
                <span className="text-sm font-medium text-green-400">{(item.co2 / 1000).toFixed(0)}t/yr</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Green Space Equity</h3>
          <div className="space-y-3">
            {zones.map(([zone, data]) => {
              const equityScore = Math.round((data.coverage_pct / 22) * 100);
              return (
                <div key={zone}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-white capitalize">{zone}</span>
                    <span className="text-xs" style={{ color: equityScore > 70 ? '#00C853' : equityScore > 40 ? '#FFD300' : '#FF3B3B' }}>
                      {equityScore}% equitable
                    </span>
                  </div>
                  <Progress
                    value={equityScore}
                    max={100}
                    color={equityScore > 70 ? '#00C853' : equityScore > 40 ? '#FFD300' : '#FF3B3B'}
                  />
                </div>
              );
            })}
          </div>
          <p className="text-xs text-gray-500 mt-3">Comparing green space access against city average</p>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Satellite Analysis Summary</h3>
          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-bg-tertiary">
              <p className="text-xs text-gray-400">Analysis Source</p>
              <p className="text-sm text-white mt-1">{satellite?.source || 'Loading...'}</p>
            </div>
            <div className="p-3 rounded-lg bg-bg-tertiary">
              <p className="text-xs text-gray-400">Spatial Resolution</p>
              <p className="text-sm text-white mt-1">{satellite?.resolution_m || '—'}m per pixel</p>
            </div>
            <div className="p-3 rounded-lg bg-bg-tertiary">
              <p className="text-xs text-gray-400">Last Updated</p>
              <p className="text-sm text-white mt-1">
                {satellite?.analysis_date ? new Date(satellite.analysis_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
