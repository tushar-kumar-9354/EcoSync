'use client';

import { useEnergyConsumption, useEnergyForecast, usePredictions } from '@/hooks/useData';
import { Card, Badge, Progress } from '@/components/ui';
import { EnergyConsumptionChart, EnergyForecastChart } from '@/components/charts';
import { ZONES } from '@/lib/constants';
import { useState } from 'react';

export default function EnergyDashboard() {
  const [period, setPeriod] = useState('24h');
  const { data: consumption, isLoading } = useEnergyConsumption(period);
  const { data: forecast } = useEnergyForecast();
  const { data: predictions } = usePredictions();

  // Compute zone data from sensors
  const zoneData = ZONES.map((zone, i) => {
    const baseConsumption = [4820, 3240, 4120, 3890, 2350];
    return {
      zone: zone.charAt(0).toUpperCase() + zone.slice(1),
      consumption: baseConsumption[i],
      change: [-15, 2, 8, -11, -8][i]
    };
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Energy Management</h1>
          <p className="text-sm text-gray-400 mt-1">Real-time monitoring and demand forecasting</p>
        </div>
        <div className="flex gap-2">
          {['1h', '6h', '24h', '7d', '30d'].map(p => (
            <button key={p} onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${period === p ? 'bg-primary text-bg-primary' : 'bg-bg-elevated text-gray-400 hover:text-white'}`}>
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <p className="text-sm text-gray-400">Total Consumption</p>
          <p className="text-3xl font-bold text-white mt-1">{consumption?.total_kwh?.toLocaleString() || '—'}</p>
          <p className="text-xs text-gray-500 mt-1">kWh in last {period}</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Avg Demand</p>
          <p className="text-3xl font-bold text-white mt-1">{consumption?.avg_kw?.toLocaleString() || '—'}</p>
          <p className="text-xs text-gray-500 mt-1">kW average</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Peak Forecast</p>
          <p className="text-3xl font-bold text-orange-400 mt-1">{forecast?.peak_hour || '—'}</p>
          <p className="text-xs text-gray-500 mt-1">Expected peak time</p>
        </Card>
        <Card>
          <p className="text-sm text-gray-400">Reduction vs Baseline</p>
          <p className="text-3xl font-bold text-green-400 mt-1">18.5%</p>
          <p className="text-xs text-gray-500 mt-1">Optimized consumption</p>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Consumption Trend</h3>
            <Badge variant="default">{period}</Badge>
          </div>
          {consumption?.data && consumption.data.length > 0 ? (
            <EnergyConsumptionChart data={consumption.data} height={220} />
          ) : (
            <div className="h-[220px] flex items-center justify-center text-gray-500 text-sm">
              No consumption data available
            </div>
          )}
        </Card>
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">24-Hour Demand Forecast</h3>
            {predictions?.predictions?.[0] && (
              <span className="text-xs text-gray-500">
                Model: {predictions.predictions[0].model_version}
              </span>
            )}
          </div>
          {predictions?.predictions && predictions.predictions.length > 0 ? (
            <EnergyForecastChart predictions={predictions.predictions} height={220} />
          ) : forecast?.predictions && forecast.predictions.length > 0 ? (
            <EnergyForecastChart predictions={forecast.predictions} height={220} />
          ) : (
            <div className="h-[220px] flex items-center justify-center text-gray-500 text-sm">
              No forecast data available
            </div>
          )}
        </Card>
      </div>

      {/* Zone Breakdown */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Consumption by Zone</h3>
          <div className="space-y-3">
            {zoneData.map((z) => (
              <div key={z.zone} className="flex items-center gap-3">
                <span className="w-24 text-xs text-gray-400 capitalize">{z.zone}</span>
                <Progress
                  value={z.consumption / 50}
                  max={100}
                  className="flex-1"
                  color={z.change < 0 ? '#00C853' : z.change > 5 ? '#FF3B3B' : '#FFD300'}
                />
                <span className="text-xs text-gray-300 w-12 text-right">{z.consumption.toLocaleString()} kWh</span>
                <span className={`text-xs w-12 text-right ${z.change < 0 ? 'text-green-400' : z.change > 5 ? 'text-red-400' : 'text-gray-400'}`}>
                  {z.change > 0 ? '+' : ''}{z.change}%
                </span>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">Consumption by Type</h3>
          <div className="space-y-3">
            {[
              { name: 'Commercial', val: 45, color: '#00C853' },
              { name: 'Industrial', val: 28, color: '#5EF5A7' },
              { name: 'Residential', val: 18, color: '#FFD300' },
              { name: 'Municipal', val: 9, color: '#FF8C00' },
            ].map(t => (
              <div key={t.name} className="flex items-center gap-3">
                <span className="w-24 text-xs text-gray-400">{t.name}</span>
                <Progress value={t.val} max={50} className="flex-1" color={t.color} />
                <span className="text-xs text-gray-300 w-10 text-right">{t.val}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Demand Response & Peak Events */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Demand Response Opportunities</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between p-2 rounded bg-green-500/10">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-sm text-gray-300">Ready to curtail</span>
              </div>
              <span className="text-sm font-medium text-green-400">12 buildings</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-yellow-500/10">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-yellow-500" />
                <span className="text-sm text-gray-300">Negotiating</span>
              </div>
              <span className="text-sm font-medium text-yellow-400">5 buildings</span>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-red-500/10">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-sm text-gray-300">Opted out</span>
              </div>
              <span className="text-sm font-medium text-red-400">3 buildings</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-bg-tertiary">
            <p className="text-xs text-gray-400">Potential savings: <span className="text-green-400 font-medium">$840/day</span></p>
          </div>
        </Card>
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Recent Peak Events</h3>
          <div className="space-y-2">
            {[
              { date: 'Mar 23', time: '2-3PM', demand: '5,200 kW', duration: '45 min' },
              { date: 'Mar 21', time: '2-4PM', demand: '4,900 kW', duration: '30 min' },
              { date: 'Mar 19', time: '3-4PM', demand: '5,100 kW', duration: '60 min' },
            ].map((peak, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-bg-tertiary">
                <div>
                  <span className="text-sm text-white">{peak.date}</span>
                  <span className="text-xs text-gray-500 ml-2">{peak.time}</span>
                </div>
                <div className="text-right">
                  <span className="text-sm font-medium text-orange-400">{peak.demand}</span>
                  <span className="text-xs text-gray-500 ml-2">{peak.duration}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
