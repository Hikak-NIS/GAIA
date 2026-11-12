export interface Area {
  name: string;
  latitude: number;
  longitude: number;
  radius_km: number;
}
export type Scenario = "degraded" | "recovering" | "balanced";
export interface Weights {
  vegetation: number;
  moisture: number;
  temperature: number;
  change: number;
  precipitation: number;
}
export interface GlobalSettings {
  weights: Weights;
  revision: number;
}
export const weightNames: Record<keyof Weights, string> = {
  vegetation: "Растительность",
  moisture: "Влажность почвы",
  temperature: "Температурная аномалия",
  change: "Динамика покрова",
  precipitation: "Осадки",
};
export interface Metric {
  id: string;
  name: string;
  value: number;
  unit: string;
  min: number;
  max: number;
  explanation: string;
  source: string;
  provider: string;
  updated_at: string;
}
export interface Factor {
  id: string;
  name: string;
  score: number;
  weight: number;
  contribution: number;
  explanation: string;
  formula: string;
}
export interface Recommendation {
  id: string;
  priority: "high" | "medium" | "low";
  problem: string;
  action: string;
  expected_effect: string;
  evidence: string;
  source: string;
}
export interface Analysis {
  id: string;
  created_at: string;
  area: Area;
  scenario: Scenario;
  source: string;
  gehi: {
    score: number;
    level: string;
    label: string;
    factors: Factor[];
    model_version: string;
    weights_revision: number;
    weights: Weights;
    notice: string;
  };
  metrics: Metric[];
  recommendations: Recommendation[];
  history: {
    date: string;
    source: string;
    ndvi: number;
    vegetation_cover: number;
    soil_moisture: number;
    precipitation: number;
  }[];
}
export interface AnalysisSummary {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  created_at: string;
  source: string;
}
export interface GlobalMarker {
  id: string;
  creator_id: string;
  title: string;
  category: string;
  note: string;
  latitude: number;
  longitude: number;
  created_at: string;
}
export interface Provider {
  id: string;
  name: string;
  available: boolean;
  status: string;
  url: string | null;
  requirements: string;
  products: string[];
}
export const presets = [
  {
    id: "aral",
    name: "Приаралье · Казахстан",
    latitude: 45.1,
    longitude: 60.2,
    radius_km: 50,
    scenario: "degraded" as Scenario,
  },
  {
    id: "alatau",
    name: "Заилийский Алатау",
    latitude: 43.1,
    longitude: 77.1,
    radius_km: 25,
    scenario: "balanced" as Scenario,
  },
  {
    id: "amazon",
    name: "Амазония · Бразилия",
    latitude: -3.5,
    longitude: -62.1,
    radius_km: 100,
    scenario: "recovering" as Scenario,
  },
];
export const categoryNames: Record<string, string> = {
  vegetation: "Растительность",
  water: "Вода",
  erosion: "Эрозия",
  pressure: "Нагрузка",
  other: "Другое",
};
