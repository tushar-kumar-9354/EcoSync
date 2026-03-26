'use client';

import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from 'recharts';
import { Card } from '@/components/ui';

interface ChartTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function ChartTooltip({ active, payload, label }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-bg-primary border border-bg-tertiary rounded-lg px-3 py-2 shadow-lg">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      {payload.map((entry, i) => (
        <p key={i} className="text-sm font-medium" style={{ color: entry.color }}>
          {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
        </p>
      ))}
    </div>
  );
}

// Energy Consumption Chart
export function EnergyConsumptionChart({
  data,
  height = 220
}: {
  data: Array<{ timestamp: string; consumption_kwh: number }>;
  height?: number;
}) {
  const formatted = data.map(d => ({
    time: new Date(d.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
    kWh: d.consumption_kwh
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={formatted} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <defs>
          <linearGradient id="energyGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#00C853" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#00C853" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" />
        <XAxis dataKey="time" tick={{ fill: '#6B7280', fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={v => `${v}`} />
        <Tooltip content={<ChartTooltip />} />
        <Area type="monotone" dataKey="kWh" name="Consumption" stroke="#00C853" fill="url(#energyGradient)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// Energy Forecast Chart
export function EnergyForecastChart({
  predictions,
  height = 220
}: {
  predictions: Array<{ horizon: string; value: number; confidence_interval?: { lower: number; upper: number } }>;
  height?: number;
}) {
  const data = predictions.slice(0, 24).map(p => ({
    time: p.horizon,
    Forecast: p.value,
    ...(p.confidence_interval ? { 'Lower': p.confidence_interval.lower, 'Upper': p.confidence_interval.upper } : {})
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" />
        <XAxis dataKey="time" tick={{ fill: '#6B7280', fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip content={<ChartTooltip />} />
        <Line type="monotone" dataKey="Upper" stroke="#1A2332" strokeWidth={1} dot={false} strokeDasharray="3 3" />
        <Line type="monotone" dataKey="Lower" stroke="#1A2332" strokeWidth={1} dot={false} strokeDasharray="3 3" />
        <Line type="monotone" dataKey="Forecast" name="Forecast" stroke="#FF8C00" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// Zone Consumption Bar Chart
export function ZoneConsumptionChart({
  zones
}: {
  zones: Array<{ zone: string; consumption: number; change?: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={zones} layout="vertical" margin={{ top: 5, right: 30, left: 60, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#6B7280', fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis type="category" dataKey="zone" tick={{ fill: '#9CA3AF', fontSize: 12 }} tickLine={false} axisLine={false} width={55} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="consumption" name="kWh" fill="#00C853" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// AQI Trend Chart
export function AqiTrendChart({
  data,
  height = 160
}: {
  data: Array<{ timestamp: string; aqi: number }>;
  height?: number;
}) {
  const formatted = data.map(d => ({
    time: new Date(d.timestamp).toLocaleTimeString('en-US', { hour: '2-digit' }),
    AQI: d.aqi
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={formatted} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" />
        <XAxis dataKey="time" tick={{ fill: '#6B7280', fontSize: 10 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: '#6B7280', fontSize: 10 }} tickLine={false} axisLine={false} domain={[0, 500]} />
        <Tooltip content={<ChartTooltip />} />
        <Line type="monotone" dataKey="AQI" name="AQI" stroke="#FF8C00" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// AQI Forecast Chart with confidence bands
export function AqiForecastChart({
  predictions,
  height = 160
}: {
  predictions: Array<{ horizon: string; value: number; confidence_interval?: { lower: number; upper: number } }>;
  height?: number;
}) {
  const data = predictions.slice(0, 48).map(p => ({
    time: p.horizon,
    Forecast: p.value,
    ...(p.confidence_interval ? { 'Lower': p.confidence_interval.lower, 'Upper': p.confidence_interval.upper } : {})
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <defs>
          <linearGradient id="aqiGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#FF8C00" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#FF8C00" stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" />
        <XAxis dataKey="time" tick={{ fill: '#6B7280', fontSize: 10 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: '#6B7280', fontSize: 10 }} tickLine={false} axisLine={false} domain={[0, 400]} />
        <Tooltip content={<ChartTooltip />} />
        <Area type="monotone" dataKey="Upper" fill="none" stroke="#1A2332" strokeWidth={1} strokeDasharray="3 3" />
        <Area type="monotone" dataKey="Lower" fill="url(#aqiGradient)" stroke="#1A2332" strokeWidth={1} />
        <Line type="monotone" dataKey="Forecast" name="AQI Forecast" stroke="#FF8C00" strokeWidth={2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// Sentiment Trend Chart
export function SentimentTrendChart({
  data,
  height = 120
}: {
  data: Array<{ date: string; sentiment: number; volume: number }>;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: -30, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" />
        <XAxis dataKey="date" tick={{ fill: '#6B7280', fontSize: 10 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: '#6B7280', fontSize: 10 }} tickLine={false} axisLine={false} domain={[-1, 1]} />
        <Tooltip content={<ChartTooltip />} />
        <Line type="monotone" dataKey="sentiment" name="Sentiment" stroke="#5EF5A7" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

// Category Breakdown Bar Chart (Horizontal)
export function CategoryBreakdownChart({
  categories,
  height = 200
}: {
  categories: Array<{ category: string; count: number; color?: string }>;
  height?: number;
}) {
  const COLORS = ['#00C853', '#5EF5A7', '#FFD300', '#FF8C00', '#FF3B3B', '#9B59B6', '#3498DB', '#E74C3C'];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={categories} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#6B7280', fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis type="category" dataKey="category" tick={{ fill: '#9CA3AF', fontSize: 11 }} tickLine={false} axisLine={false} width={95} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="count" name="Reports" radius={[0, 4, 4, 0]}>
          {categories.map((_, index) => (
            <Cell key={`cell-${index}`} fill={categories[index].color || COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Fill Level Distribution Donut Chart
export function FillDistributionChart({
  distribution,
  height = 180
}: {
  distribution: Array<{ name: string; value: number; color: string }>;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={distribution}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={75}
          paddingAngle={2}
          dataKey="value"
        >
          {distribution.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  );
}

// Sustainability Score Radial
export function ScoreRadial({
  score,
  size = 160
}: {
  score: number;
  size?: number;
}) {
  const rotation = (score / 100) * 180;
  const color = score >= 70 ? '#00C853' : score >= 50 ? '#FFD300' : '#FF3B3B';

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size / 2 }}>
      <svg viewBox="0 0 160 80" className="w-full h-full">
        {/* Background arc */}
        <path
          d="M 10 75 A 70 70 0 0 1 150 75"
          fill="none"
          stroke="#1A2332"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Score arc */}
        <path
          d="M 10 75 A 70 70 0 0 1 150 75"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${(score / 100) * 220} 220`}
          style={{ transition: 'stroke-dasharray 0.5s ease' }}
        />
        {/* Score text */}
        <text x="80" y="60" textAnchor="middle" className="fill-white" style={{ fontSize: '28px', fontWeight: 'bold' }}>
          {score}
        </text>
        <text x="80" y="75" textAnchor="middle" className="fill-gray-400" style={{ fontSize: '10px' }}>
          /100
        </text>
      </svg>
    </div>
  );
}

// Severity Distribution Bar
export function SeverityDistributionChart({
  stats,
  height = 80
}: {
  stats: { CRITICAL: number; HIGH: number; MEDIUM: number; LOW: number };
  height?: number;
}) {
  const data = [
    { name: 'Critical', value: stats.CRITICAL || 0, color: '#FF3B3B' },
    { name: 'High', value: stats.HIGH || 0, color: '#FF8C00' },
    { name: 'Medium', value: stats.MEDIUM || 0, color: '#FFD300' },
    { name: 'Low', value: stats.LOW || 0, color: '#00C853' },
  ];

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <XAxis dataKey="name" tick={{ fill: '#9CA3AF', fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis hide />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="value" name="Count" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Coverage Radar Chart
export function CoverageRadarChart({
  data,
  height = 280
}: {
  data: Array<{ zone: string; coverage: number; trees: number; parks: number; canopy: number }>;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} margin={{ top: 5, right: 30, bottom: 5, left: 30 }}>
        <PolarGrid stroke="#1A2332" />
        <PolarAngleAxis dataKey="zone" tick={{ fill: '#9CA3AF', fontSize: 11 }} />
        <PolarRadiusAxis tick={{ fill: '#6B7280', fontSize: 10 }} />
        <Radar name="Coverage %" dataKey="coverage" stroke="#00C853" fill="#00C853" fillOpacity={0.2} strokeWidth={2} />
        <Radar name="Canopy Score" dataKey="canopy" stroke="#5EF5A7" fill="#5EF5A7" fillOpacity={0.1} strokeWidth={2} />
        <Tooltip content={<ChartTooltip />} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

// Heat Island Bar Chart
export function HeatIslandBarChart({
  zones,
  height = 200
}: {
  zones: Array<{ zone: string; avg_surface_temp: number; delta_from_baseline: number; risk_level: string }>;
  height?: number;
}) {
  const data = zones.map(z => ({
    zone: z.zone.charAt(0).toUpperCase() + z.zone.slice(1),
    'Delta (°C)': z.delta_from_baseline,
    'Surface Temp': z.avg_surface_temp,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" />
        <XAxis dataKey="zone" tick={{ fill: '#9CA3AF', fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="Delta (°C)" name="Delta (°C)" fill="#FF8C00" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// Intervention Priority Chart
export function InterventionPriorityChart({
  interventions,
  height = 200
}: {
  interventions: Array<{ id: string; zone: string; priority_score: number; est_cost: number; type: string }>;
  height?: number;
}) {
  const data = interventions.map(i => ({
    name: `${i.type} (${i.zone})`,
    score: i.priority_score,
    cost: i.est_cost / 1000,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" />
        <XAxis dataKey="name" tick={{ fill: '#9CA3AF', fontSize: 10 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="score" name="Priority Score" fill="#00C853" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// NDVI Zone Chart
export function NdviZoneChart({
  ndvi,
  height = 200
}: {
  ndvi: Record<string, number>;
  height?: number;
}) {
  const data = Object.entries(ndvi).map(([zone, value]) => ({
    zone: zone.charAt(0).toUpperCase() + zone.slice(1),
    NDVI: value,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1A2332" />
        <XAxis dataKey="zone" tick={{ fill: '#9CA3AF', fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: '#6B7280', fontSize: 11 }} tickLine={false} axisLine={false} domain={[0, 0.7]} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="NDVI" name="NDVI" fill="#5EF5A7" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
