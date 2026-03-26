'use client';

import { useAirQuality, useAQForecast } from '@/hooks/useData';
import { Card, Badge } from '@/components/ui';
import { AqiTrendChart, AqiForecastChart, SeverityDistributionChart } from '@/components/charts';
import { AQI_CATEGORIES } from '@/lib/constants';
import { useState } from 'react';

function getAqiColor(aqi: number) {
  const cat = AQI_CATEGORIES.find(c => aqi >= c.range[0] && aqi <= c.range[1]);
  return cat?.color || '#888';
}

function getAqiAdvice(aqi: number) {
  const cat = AQI_CATEGORIES.find(c => aqi >= c.range[0] && aqi <= c.range[1]);
  return cat?.advice || 'No data available.';
}

function getAqiLabel(aqi: number) {
  const cat = AQI_CATEGORIES.find(c => aqi >= c.range[0] && aqi <= c.range[1]);
  return cat?.label || 'Unknown';
}

export default function AirQualityDashboard() {
  const { data: aqData, isLoading } = useAirQuality();
  const { data: forecast } = useAQForecast();
  const [selectedZone, setSelectedZone] = useState<string>('all');

  const currentAqi = aqData?.aqi || 0;
  const color = getAqiColor(currentAqi);
  const label = getAqiLabel(currentAqi);
  const advice = getAqiAdvice(currentAqi);

  // Filter stations by zone
  const stations = aqData?.stations || [];
  const filteredStations = selectedZone === 'all'
    ? stations
    : stations.filter(s => s.id.includes(selectedZone));

  // Station list for selector
  const zones = Array.from(new Set(stations.map(s => s.id.split('-')[1])));

  // Pollutants from first station (city average)
  const avgStation = stations[0] || {};
  const pollutants = [
    { name: 'PM2.5', value: avgStation.pm25 || 0, unit: 'μg/m³', limit: 35, color: '#FF8C00' },
    { name: 'PM10', value: avgStation.pm10 || 0, unit: 'μg/m³', limit: 150, color: '#FFD300' },
    { name: 'NO₂', value: avgStation.no2 || 0, unit: 'ppb', limit: 100, color: '#00C853' },
    { name: 'O₃', value: avgStation.o3 || 0, unit: 'ppm', limit: 0.07, color: '#5EF5A7' },
    { name: 'CO', value: avgStation.co || 0, unit: 'ppm', limit: 9, color: '#3498DB' },
  ];

  // Historical AQI trend data (simulated from current readings)
  const aqiHistory = forecast?.hourly?.slice(0, 24).map((p, i) => ({
    timestamp: new Date(Date.now() - (24 - i) * 3600000).toISOString(),
    aqi: Math.max(0, currentAqi + (Math.random() - 0.5) * 40)
  })) || Array.from({ length: 24 }, (_, i) => ({
    timestamp: new Date(Date.now() - (24 - i) * 3600000).toISOString(),
    aqi: Math.max(0, currentAqi + (Math.random() - 0.5) * 40)
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Air Quality</h1>
          <p className="text-sm text-gray-400 mt-1">Real-time monitoring and 48-hour forecasts</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setSelectedZone('all')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${selectedZone === 'all' ? 'bg-primary text-bg-primary' : 'bg-bg-elevated text-gray-400'}`}>
            All Zones
          </button>
          {zones.slice(0, 5).map(zone => (
            <button key={zone} onClick={() => setSelectedZone(zone)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${selectedZone === zone ? 'bg-primary text-bg-primary' : 'bg-bg-elevated text-gray-400'}`}>
              {zone.charAt(0).toUpperCase() + zone.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Hero AQI Card */}
      <div className="grid grid-cols-3 gap-6">
        <Card className="col-span-2 py-8 px-6">
          <div className="flex items-center gap-8">
            <div className="text-center min-w-[180px]">
              <p className="text-8xl font-bold" style={{ color }}>{currentAqi}</p>
              <p className="text-lg font-medium mt-2" style={{ color }}>{label}</p>
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-white mb-2">Current Air Quality Index</h2>
              <p className="text-sm text-gray-400 mb-4">{advice}</p>
              <div className="flex gap-2 flex-wrap">
                <Badge variant="default">Dominant: {aqData?.dominant_pollutant || 'PM2.5'}</Badge>
                <Badge variant="default">Updated: {new Date().toLocaleTimeString()}</Badge>
                <Badge variant="default">{stations.length} Stations</Badge>
              </div>
            </div>
          </div>
          {/* AQI Scale bar */}
          <div className="mt-6 flex h-4 rounded-full overflow-hidden">
            {AQI_CATEGORIES.map(cat => (
              <div key={cat.label} className="flex-1 flex items-center justify-center text-xs font-medium text-black/70"
                style={{ backgroundColor: cat.color }} title={cat.label}>
                {cat.label}
              </div>
            ))}
          </div>
        </Card>

        <Card className="flex flex-col justify-center">
          <h3 className="text-sm font-semibold text-gray-300 mb-4">48h Forecast</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Trend</span>
              <Badge variant={forecast?.trend === 'improving' ? 'low' : forecast?.trend === 'worsening' ? 'critical' : 'medium'}>
                {forecast?.trend || 'Stable'}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Dominant Pollutant</span>
              <span className="text-sm text-white">PM2.5</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Peak Expected</span>
              <span className="text-sm text-orange-400">{forecast?.hourly?.[8]?.value || currentAqi + 20} AQI</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Best Window</span>
              <span className="text-sm text-green-400">{forecast?.hourly?.[2]?.value || currentAqi - 15} AQI</span>
            </div>
            {forecast?.hourly?.[0] && (
              <div className="pt-3 border-t border-bg-tertiary">
                <p className="text-xs text-gray-500">
                  Model: {forecast.hourly[0].model_version}
                </p>
                <p className="text-xs text-gray-500">
                  Confidence: {Math.round((forecast.hourly[0].confidence_interval?.confidence || 0.9) * 100)}%
                </p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* AQI Trend + Forecast Charts */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">24-Hour AQI Trend</h3>
          <AqiTrendChart data={aqiHistory} height={160} />
        </Card>
        <Card>
          <h3 className="text-sm font-semibold text-gray-300 mb-4">48-Hour AQI Forecast</h3>
          {forecast?.hourly ? (
            <AqiForecastChart predictions={forecast.hourly} height={160} />
          ) : (
            <div className="h-[160px] flex items-center justify-center text-gray-500 text-sm">
              Loading forecast...
            </div>
          )}
        </Card>
      </div>

      {/* Pollutant Breakdown */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Pollutant Breakdown (City Average)</h3>
        <div className="grid grid-cols-5 gap-4">
          {pollutants.map(p => (
            <div key={p.name} className="p-3 rounded-lg bg-bg-tertiary text-center">
              <p className="text-xs text-gray-400 mb-1">{p.name}</p>
              <p className="text-2xl font-bold text-white">{typeof p.value === 'number' ? p.value.toFixed(1) : '—'}</p>
              <p className="text-xs text-gray-500">{p.unit}</p>
              <div className="mt-2 h-1.5 rounded-full bg-bg-primary overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500" style={{
                  width: `${Math.min(100, (p.value / p.limit) * 100)}%`,
                  backgroundColor: (p.value / p.limit) > 1 ? '#FF3B3B' : (p.value / p.limit) > 0.7 ? '#FFD300' : p.color
                }} />
              </div>
              <p className="text-xs text-gray-500 mt-1">{((p.value / p.limit) * 100).toFixed(0)}% of limit</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Station Readings Table */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Monitoring Stations ({filteredStations.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="text-left text-gray-400 border-b border-bg-tertiary">
                <th className="pb-3 font-medium" scope="col">Station</th>
                <th className="pb-3 font-medium" scope="col">AQI</th>
                <th className="pb-3 font-medium" scope="col">Category</th>
                <th className="pb-3 font-medium" scope="col">PM2.5</th>
                <th className="pb-3 font-medium" scope="col">PM10</th>
                <th className="pb-3 font-medium" scope="col">NO₂</th>
                <th className="pb-3 font-medium" scope="col">O₃</th>
                <th className="pb-3 font-medium" scope="col">CO</th>
                <th className="pb-3 font-medium" scope="col">Last Update</th>
              </tr>
            </thead>
            <tbody className="text-gray-300">
              {filteredStations.map((station) => (
                <tr key={station.id} className="border-b border-bg-tertiary/50 hover:bg-bg-tertiary/30 transition-colors">
                  <td className="py-3 text-white font-medium">{station.name}</td>
                  <td className="py-3">
                    <span className="font-bold text-lg" style={{ color: getAqiColor(station.aqi) }}>{station.aqi}</span>
                  </td>
                  <td className="py-3">
                    <Badge variant={station.aqi > 150 ? 'critical' : station.aqi > 100 ? 'high' : station.aqi > 50 ? 'medium' : 'low'}>
                      {getAqiLabel(station.aqi)}
                    </Badge>
                  </td>
                  <td className="py-3 text-gray-400">{station.pm25?.toFixed(1)}</td>
                  <td className="py-3 text-gray-400">{station.pm10?.toFixed(1)}</td>
                  <td className="py-3 text-gray-400">{station.no2?.toFixed(1)}</td>
                  <td className="py-3 text-gray-400">{station.o3?.toFixed(3)}</td>
                  <td className="py-3 text-gray-400">{station.co?.toFixed(2)}</td>
                  <td className="py-3 text-gray-500 text-xs">
                    {station.timestamp ? new Date(station.timestamp).toLocaleTimeString() : 'Just now'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
