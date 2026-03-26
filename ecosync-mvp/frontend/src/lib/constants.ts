export const CITY_BOUNDS = {
  lat: { min: 28.50, max: 28.75 },
  lng: { min: 77.00, max: 77.40 },
};

export const ZONES = ['connaught', 'chandni', 'karol', 'saket', 'dwarka'] as const;

export const AQI_CATEGORIES = [
  { range: [0, 50], label: 'Good', color: '#00E400', advice: 'Air quality is satisfactory.' },
  { range: [51, 100], label: 'Moderate', color: '#FFFF00', advice: 'Sensitive individuals should limit outdoor exertion.' },
  { range: [101, 150], label: 'Unhealthy for Sensitive Groups', color: '#FF7E00', advice: 'Sensitive groups should reduce outdoor activities.' },
  { range: [151, 200], label: 'Unhealthy', color: '#FF0000', advice: 'Everyone should reduce outdoor exertion.' },
  { range: [201, 300], label: 'Very Unhealthy', color: '#8F3F97', advice: 'Avoid outdoor activities. Use air purifiers.' },
  { range: [301, 500], label: 'Hazardous', color: '#7E0023', advice: 'Stay indoors. Emergency warnings in effect.' },
];

export const SEVERITY_COLORS = {
  CRITICAL: '#FF3B3B',
  HIGH: '#FF8C00',
  MEDIUM: '#FFD300',
  LOW: '#00C853',
};

export const ALERT_TYPE_LABELS: Record<string, string> = {
  air_quality: 'Air Quality',
  energy_peak: 'Energy Peak',
  bin_overflow: 'Bin Overflow',
  sensor_malfunction: 'Sensor Issue',
  heat_emergency: 'Heat Emergency',
  water_quality: 'Water Quality',
};

export const REPORT_CATEGORIES = [
  { value: 'illegal_dumping', label: 'Illegal Dumping' },
  { value: 'noise_complaint', label: 'Noise Complaint' },
  { value: 'air_quality_concern', label: 'Air Quality Concern' },
  { value: 'water_quality_issue', label: 'Water Quality Issue' },
  { value: 'streetlight_outage', label: 'Streetlight Outage' },
  { value: 'drainage_problem', label: 'Drainage Problem' },
  { value: 'tree_damage', label: 'Tree Damage' },
  { value: 'park_maintenance', label: 'Park Maintenance' },
  { value: 'general_inquiry', label: 'General Inquiry' },
];
