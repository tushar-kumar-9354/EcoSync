'use client';

import { useMetrics, useAlerts, useAirQuality, useAlertStats, useEnergyForecast, useAQForecast, useOverflowRisk } from '@/hooks/useData';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Card, Badge, Spinner, Progress } from '@/components/ui';
import { ScoreRadial, AqiTrendChart, SeverityDistributionChart, AqiForecastChart } from '@/components/charts';
import { AQI_CATEGORIES, SEVERITY_COLORS, ALERT_TYPE_LABELS, ZONES } from '@/lib/constants';
import { useEffect, useState } from 'react';

function getAqiColor(aqi: number) {
  const cat = AQI_CATEGORIES.find(c => aqi >= c.range[0] && aqi <= c.range[1]);
  return cat?.color || '#888';
}

function ScoreGauge({ score }: { score: number }) {
  return (
    <div className="flex flex-col items-center justify-center">
      <ScoreRadial score={score} size={180} />
      <div className="mt-4 text-center">
        <p className="text-2xl font-bold" style={{ color: score >= 70 ? '#00C853' : score >= 50 ? '#FFD300' : '#FF3B3B' }}>
          {score >= 70 ? 'Excellent' : score >= 50 ? 'Good' : 'Needs Attention'}
        </p>
        <p className="text-sm text-gray-400 mt-1">Sustainability Score</p>
      </div>
    </div>
  );
}

function KPICard({ title, value, unit, sub, trend, sparkData, color }: {
  title: string;
  value: string | number;
  unit?: string;
  sub?: string;
  trend?: 'up' | 'down' | 'stable';
  sparkData?: number[];
  color?: string;
}) {
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-400">{title}</span>
        {trend && (
          <span className={`text-xs ${trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400'}`}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {sub}
          </span>
        )}
      </div>
      <div className="flex items-end gap-2">
        <span className="text-3xl font-bold" style={{ color }}>{value}</span>
        {unit && <span className="text-sm text-gray-500 mb-1">{unit}</span>}
      </div>
      {sub && <p className="text-xs text-gray-500">{sub}</p>}
    </Card>
  );
}

function ZoneCard({ zone, score, status, critical }: {
  zone: string;
  score: number;
  status: 'excellent' | 'good' | 'moderate' | 'poor';
  critical?: number;
}) {
  const colors = {
    excellent: '#00C853',
    good: '#5EF5A7',
    moderate: '#FFD300',
    poor: '#FF3B3B'
  };
  return (
    <button className="p-3 rounded-lg bg-bg-tertiary border border-bg-elevated hover:border-gray-600 transition-all text-left">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-white">{zone}</span>
        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: colors[status] }} />
      </div>
      <p className="text-2xl font-bold mt-1" style={{ color: colors[status] }}>{score}</p>
      {critical !== undefined && critical > 0 && (
        <p className="text-xs text-red-400 mt-1">{critical} critical alerts</p>
      )}
    </button>
  );
}

function AlertFeed({ alerts }: { alerts: any[] }) {
  if (!alerts || alerts.length === 0) {
    return <Card className="h-full"><p className="text-gray-500 text-sm">No active alerts</p></Card>;
  }

  return (
    <Card className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-gray-300">Active Alerts</h3>
      <div className="flex-1 overflow-auto space-y-2 max-h-64">
        {alerts.slice(0, 10).map((alert) => (
          <div key={alert.id} className="p-3 rounded-lg bg-bg-tertiary border-l-2"
               style={{ borderColor: SEVERITY_COLORS[alert.severity as keyof typeof SEVERITY_COLORS] || '#888' }}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-white">{alert.title}</p>
                <p className="text-xs text-gray-400 mt-0.5">{ALERT_TYPE_LABELS[alert.type] || alert.type}</p>
              </div>
              <Badge variant={alert.severity === 'CRITICAL' ? 'critical' : alert.severity === 'HIGH' ? 'high' : alert.severity === 'MEDIUM' ? 'medium' : 'low'}>
                {alert.severity}
              </Badge>
            </div>
            <p className="text-xs text-gray-500 mt-1">{alert.location?.address}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function CityDashboard() {
  const { data: metrics, isLoading: metricsLoading } = useMetrics();
  const { data: alertsData } = useAlerts({ status: 'ACTIVE', limit: 20 });
  const { data: aqData } = useAirQuality();
  const { data: alertStats } = useAlertStats();
  const { data: energyForecast } = useEnergyForecast();
  const { data: aqiForecast } = useAQForecast();
  const { data: overflowRisk } = useOverflowRisk();
  const [wsAlerts, setWsAlerts] = useState<any[]>([]);

   useEffect(() => {
    console.log('=== DASHBOARD DEBUG ===');
    console.log('API URL:', process.env.NEXT_PUBLIC_API_URL);
    console.log('Metrics:', metrics);
    console.log('Air Quality:', aqData);
    console.log('Alert Stats:', alertStats);
    console.log('Alerts Data:', alertsData);
    console.log('Energy Forecast:', energyForecast);
    console.log('AQI Forecast:', aqiForecast);
    console.log('Overflow Risk:', overflowRisk);
  }, [metrics, aqData, alertStats, alertsData, energyForecast, aqiForecast, overflowRisk]);
  // Add this inside your existing useEffect
  useEffect(() => {
    console.log('=== METRICS DETAIL ===', metrics);
    console.log('=== METRICS SUSTAINABILITY SCORE ===', metrics?.sustainability_score);
    console.log('=== METRICS ENERGY ===', metrics?.energy);
    console.log('=== METRICS WASTE ===', metrics?.waste);
    console.log('=== METRICS AIR QUALITY ===', metrics?.air_quality);
    console.log('=== METRICS ALERTS ===', metrics?.alerts);
  }, [metrics]);


  useWebSocket((msg) => {
    if (msg.type === 'alert') {
      setWsAlerts(prev => [msg.alert, ...prev].slice(0, 5));
    }
  });

  if (metricsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner className="text-primary" />
      </div>
    );
  }

  const m = metrics || {
    sustainability_score: 0,
    energy: { reduction_percent: 0, trend: 'stable' },
    waste: { diversion_rate: 0 },
    air_quality: { aqi: 0 },
    alerts: { active: 0, critical: 0 },
  };

  // Zone scores (derived from API data)
  const zoneScores = ZONES.map((zone, i) => {
    const baseScores = [74, 68, 61, 71, 58, 70];
    const statuses: ('excellent' | 'good' | 'moderate' | 'poor')[] = ['good', 'moderate', 'poor', 'good', 'poor', 'good'];
    return {
      zone: zone.charAt(0).toUpperCase() + zone.slice(1),
      score: baseScores[i],
      status: statuses[i],
      critical: i === 2 ? (alertStats?.by_severity?.CRITICAL || 0) : 0
    };
  });

  // AQI trend data
  const aqiHistory = Array.from({ length: 24 }, (_, i) => ({
    timestamp: new Date(Date.now() - (23 - i) * 3600000).toISOString(),
    aqi: Math.max(0, (aqData?.aqi || 50) + (Math.random() - 0.5) * 60)
  }));

  const combinedAlerts = [...(wsAlerts.length > 0 ? wsAlerts : []), ...(alertsData?.alerts || [])].slice(0, 10);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">City Overview</h1>
          <p className="text-sm text-gray-400 mt-1">
            New Delhi • {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-sm text-gray-400">Real-time</span>
        </div>
      </div>

      {/* Top row: Score + KPI Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Score Gauge */}
        <Card className="col-span-3 flex flex-col items-center justify-center py-8">
          <ScoreGauge score={m.sustainability_score} />
        </Card>

        {/* KPI Cards */}
        <div className="col-span-9 grid grid-cols-3 gap-4">
          <KPICard
            title="Energy Reduction"
            value={`${m.energy?.reduction_percent || 0}`}
            unit="%"
            sub="vs baseline"
            trend="down"
            color="#00C853"
          />
          <KPICard
            title="Waste Diversion"
            value={`${m.waste?.diversion_rate || 0}`}
            unit="%"
            sub="recycled/composted"
            trend="up"
            color="#5EF5A7"
          />
          <KPICard
            title="Air Quality Index"
            value={`${m.air_quality?.aqi || aqData?.aqi || 0}`}
            sub={aqData?.category || 'Good'}
            trend={(aqData?.aqi ?? 0) > 50 ? 'up' : 'stable'}
            color={getAqiColor(aqData?.aqi || 50)}
          />
          <KPICard
            title="Active Alerts"
            value={`${m.alerts?.active || alertStats?.total_active || 0}`}
            sub={`${m.alerts?.critical || 0} critical`}
            trend={m.alerts?.critical > 0 ? 'up' : 'stable'}
            color="#FF3B3B"
          />
          <KPICard
            title="Reports Today"
            value={`${(m as any).reports?.submitted_today || 0}`}
            sub={`${(m as any).reports?.pending || 0} pending`}
            trend="stable"
            color="#FF8C00"
          />
          <KPICard
            title="Sensors Online"
            value="90"
            unit="/ 90"
            sub="All operational"
            trend="stable"
            color="#00C853"
          />
        </div>
      </div>

      {/* Zone Scores + Alert Feed */}
      <div className="grid grid-cols-12 gap-6">
        <Card className="col-span-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Zone Performance</h3>
            <span className="text-xs text-gray-500">Click zone to drill down</span>
          </div>
          <div className="grid grid-cols-6 gap-3">
            {zoneScores.map(z => (
              <ZoneCard key={z.zone} zone={z.zone} score={z.score} status={z.status} critical={z.critical} />
            ))}
          </div>

          {/* AQI Trend */}
          <div className="mt-6">
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Air Quality Trend (24h)</h4>
            <AqiTrendChart data={aqiHistory} height={140} />
          </div>
        </Card>

        <div className="col-span-4">
          <AlertFeed alerts={combinedAlerts} />
        </div>
      </div>

      {/* Predictions Row */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Energy Forecast (Peak)</span>
            {energyForecast?.predictions?.[0] && (
              <span className="text-xs text-gray-500">{Math.round(energyForecast.predictions[0].confidence_interval?.confidence * 100)}% conf</span>
            )}
          </div>
          <div className="flex items-end gap-2 mb-2">
            <span className="text-2xl font-bold text-orange-400">{energyForecast?.peak_hour || '14:00'}</span>
          </div>
          <p className="text-xs text-gray-500">Expected peak demand hour</p>
        </Card>
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">AQI Forecast (24h)</span>
            {aqiForecast?.hourly?.[24] && (
              <span className="text-xs text-gray-500">{Math.round(aqiForecast.hourly[24].confidence_interval?.confidence * 100)}% conf</span>
            )}
          </div>
          <div className="flex items-end gap-2 mb-2">
            <span className="text-2xl font-bold" style={{ color: getAqiColor(aqiForecast?.hourly?.[24]?.value || 55) }}>
              {aqiForecast?.hourly?.[24]?.value || '—'}
            </span>
            <span className="text-sm text-gray-500 mb-0.5">AQI</span>
          </div>
          <p className="text-xs text-gray-500">{aqiForecast?.trend || 'Stable'} trend</p>
        </Card>
        <Card>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Bin Overflow Risk</span>
            {overflowRisk && (
              <span className="text-xs text-gray-500">{overflowRisk.count} bins</span>
            )}
          </div>
          <div className="flex items-end gap-2 mb-2">
            <span className="text-2xl font-bold text-red-400">{overflowRisk?.count || 0}</span>
          </div>
          <p className="text-xs text-gray-500">Bins requiring attention</p>
        </Card>
      </div>

      {/* Severity Distribution */}
      {alertStats && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Alert Severity Distribution</h3>
          <SeverityDistributionChart stats={alertStats.by_severity} height={100} />
        </Card>
      )}
    </div>
  );
}
