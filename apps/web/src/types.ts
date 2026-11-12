export interface User {
  id: string;
  name: string;
  email: string;
  nickname: string;
  role: "user" | "admin" | "superadmin";
}
export interface Territory {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  latitude: number;
  longitude: number;
  area: number;
  timezone: string;
  polygon: { type: "Polygon"; coordinates: number[][][] } | null;
  created_at: string;
  updated_at: string;
}
export type TerritoryInput = Pick<
  Territory,
  "name" | "description" | "latitude" | "longitude" | "area" | "timezone"
>;
export interface Reading {
  id: string;
  timestamp: string;
  received_at: string;
  source: string;
  air_temperature_c: number | null;
  air_humidity_pct: number | null;
  soil_moisture_pct: number | null;
  light_lux: number | null;
  quality: string;
}
export interface Simulation {
  status: string;
  scenario: string;
  seed: number;
  speed: number;
  tick_index: number;
  clock: string;
  soil: number;
  reservoir_l: number;
  total_water_l: number;
}
export interface Rule {
  mode: "off" | "manual" | "automatic";
  trigger_pct: number;
  target_pct: number;
  max_duration_s: number;
  cooldown_s: number;
  daily_limit_l: number;
  min_reservoir_l: number;
  block_rain: boolean;
  rain_threshold_pct: number;
}
export interface IrrigationState {
  pump_on: boolean;
  emergency: boolean;
  daily_water_l: number;
  run_water_l: number;
}
export interface Alert {
  id: string;
  code: string;
  severity: string;
  status: string;
  title: string;
  explanation: string;
  recommendation: string;
  created_at: string;
  resolved_at: string | null;
}
export interface Dashboard {
  territory: Territory;
  reading: Reading | null;
  simulation: Simulation;
  rule: Rule;
  zone: IrrigationState;
  alerts: Alert[];
  status: string;
  reasons: string[];
}
export interface IrrigationEvent {
  id: string;
  timestamp: string;
  action: string;
  reason: string;
  duration_s: number;
  estimated_water_l: number;
  actor: string;
}
export interface Observation {
  id: string;
  category: string;
  severity: string;
  text: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  photo_path: string | null;
  source: string;
}
export interface Weather {
  status: string;
  fetched_at: string | null;
  error: string | null;
  data: {
    current: {
      temperature_2m: number;
      relative_humidity_2m: number;
      precipitation: number;
      wind_speed_10m: number;
    };
    next_6h_probability: number;
    next_6h_precipitation_mm: number;
  } | null;
}
export interface Satellite {
  url: string;
  date: string;
  explanation: string;
}
export interface Report {
  id: string;
  period_start: string;
  period_end: string;
  created_at: string;
  data: {
    date: string;
    reading_count: number;
    summary: string;
    alert_count: number;
    irrigation_count: number;
    duration_s: number;
    water_l: number;
    water_accounting: string;
    recommendations: string[];
    observations: string[];
    sources: string[];
    weather: Record<string, number | string> | null;
    stats: Record<string, { min: number; max: number; mean: number } | null>;
  };
}
export const scenarios: Record<string, string> = {
  normal: "Обычная погода",
  drought: "Засуха",
  heatwave: "Аномальная жара",
  rain: "Дождь",
  frost: "Заморозок",
  sensor_failure: "Отказ датчика",
};
export const sources: Record<string, string> = {
  simulated: "Симуляция",
  device: "Устройство",
  manual: "Ручное наблюдение",
  weather: "Open-Meteo",
  satellite: "NASA GIBS",
};
export const categories: Record<string, string> = {
  vegetation: "Растительность",
  soil: "Почва",
  water: "Вода",
  litter: "Мусор",
  pest: "Вредители",
  weather: "Погода",
  other: "Другое",
};
