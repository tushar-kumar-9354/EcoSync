'use client';

import { useWasteBins, useOverflowRisk, useSensorGeoJSON } from '@/hooks/useData';
import { Card, Badge, Progress } from '@/components/ui';
import { CategoryBreakdownChart, FillDistributionChart } from '@/components/charts';
import { useState } from 'react';

function getStatusColor(status: string) {
  switch (status) {
    case 'critical': return '#FF3B3B';
    case 'warning': return '#FF8C00';
    case 'moderate': return '#FFD300';
    default: return '#00C853';
  }
}

export default function WasteDashboard() {
  const { data: binsData, isLoading } = useWasteBins({ limit: 50 });
  const { data: overflowData } = useOverflowRisk();
  const { data: geoJSON } = useSensorGeoJSON();
  const [selectedZone, setSelectedZone] = useState<string | null>(null);

  const bins = binsData?.bins || [];
  const criticalBins = bins.filter(b => b.status === 'critical');
  const warningBins = bins.filter(b => b.status === 'warning');
  const moderateBins = bins.filter(b => b.status === 'moderate');
  const normalBins = bins.filter(b => b.status === 'normal');

  // Zone distribution
  const zoneCounts = bins.reduce((acc: Record<string, { total: number; critical: number }>, bin) => {
    const zone = bin.zone || 'unknown';
    if (!acc[zone]) acc[zone] = { total: 0, critical: 0 };
    acc[zone].total++;
    if (bin.status === 'critical') acc[zone].critical++;
    return acc;
  }, {});

  const zones = Object.entries(zoneCounts).map(([zone, counts]) => ({
    zone: zone.charAt(0).toUpperCase() + zone.slice(1),
    bins: counts.total,
    critical: counts.critical
  }));

  // Fill distribution for donut chart
  const fillDistribution = [
    { name: '0-25%', value: 15, color: '#00C853' },
    { name: '25-50%', value: 28, color: '#5EF5A7' },
    { name: '50-75%', value: 32, color: '#FFD300' },
    { name: '75-90%', value: 18, color: '#FF8C00' },
    { name: '90%+', value: 7, color: '#FF3B3B' },
  ];

  // Category breakdown (simulated for reports)
  const reportCategories = [
    { category: 'illegal_dumping', count: 234, color: '#FF3B3B' },
    { category: 'drainage_problem', count: 156, color: '#FF8C00' },
    { category: 'air_quality', count: 112, color: '#FFD300' },
    { category: 'streetlight', count: 89, color: '#5EF5A7' },
    { category: 'noise_complaint', count: 67, color: '#00C853' },
    { category: 'park_maintenance', count: 52, color: '#3498DB' },
  ];

  // Fleet status (simulated)
  const fleetStatus = {
    active: 10,
    enRoute: 2,
    idle: 0,
    totalMiles: 187,
    fuelSaved: 23,
    routesToday: 12
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Waste Management</h1>
          <p className="text-sm text-gray-400 mt-1">Bin monitoring, collection optimization, and diversion tracking</p>
        </div>
        <div className="flex gap-2">
          {['All', 'Connaught', 'Chandni', 'Karol', 'Saket', 'Dwarka'].map(zone => (
            <button key={zone} onClick={() => setSelectedZone(zone === 'All' ? null : zone.toLowerCase())}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${selectedZone === (zone === 'All' ? null : zone.toLowerCase()) ? 'bg-primary text-bg-primary' : 'bg-bg-elevated text-gray-400 hover:text-white'}`}>
              {zone}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-5 gap-4">
        <Card>
          <p className="text-sm text-gray-400">Total Bins</p>
          <p className="text-3xl font-bold text-white mt-1">{binsData?.total || bins.length}</p>
          <p className="text-xs text-gray-500 mt-1">Active sensors</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Avg Fill Level</p>
          <p className="text-3xl font-bold text-white mt-1">
            {bins.length > 0
              ? Math.round(bins.reduce((s, b) => s + b.fill_percent, 0) / bins.length)
              : 0}%
          </p>
          <p className="text-xs text-gray-500 mt-1">Across all zones</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Critical Bins</p>
          <p className="text-3xl font-bold text-red-400 mt-1">{criticalBins.length}</p>
          <p className="text-xs text-gray-500 mt-1">Requires immediate collection</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Fleet Status</p>
          <div className="flex items-center gap-2 mt-1">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-lg font-bold text-white">{fleetStatus.active}</span>
            <span className="text-xs text-gray-500">active</span>
            {fleetStatus.enRoute > 0 && (
              <>
                <div className="w-2 h-2 rounded-full bg-yellow-500 ml-2" />
                <span className="text-lg font-bold text-yellow-400">{fleetStatus.enRoute}</span>
                <span className="text-xs text-gray-500">en route</span>
              </>
            )}
          </div>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Diversion Rate</p>
          <p className="text-3xl font-bold text-green-400 mt-1">41.8%</p>
          <p className="text-xs text-green-400/70 mt-1">↑ improving</p>
        </Card>
      </div>

      {/* Main content: Map + Overflow Risk */}
      <div className="grid grid-cols-12 gap-6">
        {/* Bin Map */}
        <Card className="col-span-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Bin Fill Levels by Zone</h3>
            <div className="flex gap-3 text-xs">
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500" /> Normal</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-400" /> Moderate</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-orange-500" /> Warning</span>
              <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500" /> Critical</span>
            </div>
          </div>

          {/* Zone cards with bin counts */}
          <div className="grid grid-cols-5 gap-3">
            {zones.map(z => (
              <div key={z.zone} className="p-3 rounded-lg bg-bg-tertiary border border-bg-elevated">
                <p className="text-sm font-medium text-white">{z.zone}</p>
                <p className="text-2xl font-bold mt-1" style={{ color: z.critical > 0 ? '#FF3B3B' : '#00C853' }}>
                  {z.bins}
                </p>
                <p className="text-xs text-gray-500">bins</p>
                {z.critical > 0 && (
                  <p className="text-xs text-red-400 mt-1">{z.critical} critical</p>
                )}
              </div>
            ))}
          </div>

          {/* Overflow Risk Predictions */}
          <div className="mt-4">
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Overflow Risk (2h Prediction)</h4>
            <div className="space-y-2 max-h-48 overflow-auto">
              {(overflowData?.predictions || []).slice(0, 8).map((p) => (
                <div key={p.bin_id} className="flex items-center justify-between p-2 rounded-lg bg-bg-tertiary border-l-2"
                  style={{
                    borderColor: p.overflow_risk_2h > 0.9 ? '#FF3B3B' : p.overflow_risk_2h > 0.7 ? '#FF8C00' : '#FFD300'
                  }}>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-white">{p.name}</span>
                    <Badge variant={p.overflow_risk_2h > 0.9 ? 'critical' : p.overflow_risk_2h > 0.7 ? 'high' : 'medium'}>
                      {p.overflow_risk_2h > 0.9 ? 'IMMINENT' : p.overflow_risk_2h > 0.7 ? 'HIGH' : 'MODERATE'}
                    </Badge>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold" style={{ color: p.overflow_risk_2h > 0.7 ? '#FF3B3B' : '#FFD300' }}>
                      {Math.round(p.overflow_risk_2h * 100)}%
                    </p>
                    <p className="text-xs text-gray-500">{p.current_fill.toFixed(0)}% full</p>
                  </div>
                </div>
              ))}
              {(!overflowData?.predictions || overflowData.predictions.length === 0) && (
                <p className="text-sm text-gray-500 text-center py-4">No overflow risks predicted</p>
              )}
            </div>
          </div>
        </Card>

        {/* Fleet Status + Diversion */}
        <Card className="col-span-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Today&apos;s Operations</h3>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">Fleet Utilization</span>
                <span className="text-sm font-medium text-white">{fleetStatus.active + fleetStatus.enRoute}/12</span>
              </div>
              <Progress value={(fleetStatus.active + fleetStatus.enRoute) / 12 * 100} max={100} color="#00C853" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-bg-tertiary">
                <p className="text-2xl font-bold text-white">{fleetStatus.totalMiles}</p>
                <p className="text-xs text-gray-500">miles today</p>
              </div>
              <div className="p-3 rounded-lg bg-bg-tertiary">
                <p className="text-2xl font-bold text-green-400">↓{fleetStatus.fuelSaved}%</p>
                <p className="text-xs text-gray-500">fuel saved</p>
              </div>
            </div>

            <div className="pt-3 border-t border-bg-tertiary">
              <p className="text-sm text-gray-400 mb-2">Routes Completed</p>
              <div className="space-y-1">
                {['Route 1: Karol Zone', 'Route 2: Saket Zone', 'Route 3: Dwarka Zone'].map((route, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-300">{route}</span>
                    <Badge variant={i === 0 ? 'high' : 'default'}>{i === 0 ? 'In Progress' : i === 1 ? 'Queued' : 'Completed'}</Badge>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Fill Distribution + Bins by Status */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Fill Level Distribution</h3>
          <div className="grid grid-cols-2 gap-4">
            <FillDistributionChart distribution={fillDistribution} height={180} />
            <div className="space-y-2">
              {fillDistribution.map(f => (
                <div key={f.name} className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">{f.name}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-2 rounded-full bg-bg-tertiary overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${f.value}%`, backgroundColor: f.color }} />
                    </div>
                    <span className="text-gray-300 w-8">{f.value}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Bins by Status</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
              <p className="text-2xl font-bold text-green-400">{normalBins.length}</p>
              <p className="text-xs text-gray-400">Normal (0-50%)</p>
            </div>
            <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <p className="text-2xl font-bold text-yellow-400">{moderateBins.length}</p>
              <p className="text-xs text-gray-400">Moderate (50-75%)</p>
            </div>
            <div className="p-3 rounded-lg bg-orange-500/10 border border-orange-500/20">
              <p className="text-2xl font-bold text-orange-400">{warningBins.length}</p>
              <p className="text-xs text-gray-400">Warning (75-90%)</p>
            </div>
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-2xl font-bold text-red-400">{criticalBins.length}</p>
              <p className="text-xs text-gray-400">Critical (90%+)</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
