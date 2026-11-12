export type Metric = {
  id: string;
  label: string;
  value: number | null;
  unit: string;
  observed_at: string | null;
  kind: string;
  source: string;
  source_url?: string;
  description: string;
  history: { date: string; value: number | null }[];
  quality?: number;
};
export type Source<T = { metrics?: Metric[] }> = {
  status: string;
  data?: T;
  message?: string;
};
export type Scene = {
  id: string;
  datetime: string;
  cloud_cover: number | null;
  preview: string | null;
  url: string;
};
export type EarthAnalysis = {
  id: string;
  created_at: string;
  data_kind: string;
  ocean: boolean;
  area: {
    name: string;
    latitude: number;
    longitude: number;
    radius_km: number;
  };
  period: { start: string; end: string };
  metrics: Metric[];
  sources: Record<string, Source<{ metrics?: Metric[]; items?: Scene[] }>>;
  recommendations: {
    title: string;
    detail: string;
    priority: string;
    basis: string;
  }[];
  assessment: { explanation: string };
  coverage_note: string;
};
export type Layer = {
  id: string;
  name: string;
  category: string;
  matrix: string;
  max_zoom: number;
  extension: string;
  default_date: string;
  time_ranges: string[];
  legend: string | null;
  source: string;
};
export type MapPoint = {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  detail?: string;
  url?: string;
};
export const sourceNames: Record<string, string> = {
  weather: "Погода и почва",
  air: "Атмосфера · CAMS",
  marine: "Морские модели",
  sentinel_catalog: "Каталог Sentinel-2",
  nasa_catalog: "Каталог NASA Earthdata",
  sentinel_statistics: "Индексы Sentinel-2",
  earth_engine: "Google Earth Engine",
};
