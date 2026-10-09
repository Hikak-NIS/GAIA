export type DataSource = "REAL" | "SIMULATED";
export type Stage =
  "seedling" | "vegetative" | "flowering" | "fruiting" | "mature";
export const stages: Record<Stage, string> = {
  seedling: "Рассада",
  vegetative: "Вегетация",
  flowering: "Цветение",
  fruiting: "Плодоношение",
  mature: "Зрелое растение",
};
export interface TerritoryZone {
  id: string;
  territory_id: string;
  name: string;
  description: string;
  is_default: boolean;
}
export interface Requirements {
  soil_moisture_min: number | null;
  soil_moisture_max: number | null;
  temperature_min: number | null;
  temperature_max: number | null;
  humidity_min: number | null;
  humidity_max: number | null;
  ph_min: number | null;
  ph_max: number | null;
  light_requirements: string;
  irrigation_requirements: string;
  nutrient_requirements: string;
}
export interface ProfileInput extends Requirements {
  common_name: string;
  scientific_name: string;
  description: string;
  common_diseases: string[];
  stage_requirements: Partial<Record<Stage, Requirements>>;
}
export interface PlantProfile extends ProfileInput {
  id: string;
}
export interface Channel {
  id: string;
  device_id: string;
  sensor_type: string;
  unit: string;
  source: DataSource;
  calibration: { scale?: number; offset?: number; notes?: string };
  current_value: number | null;
  timestamp: string | null;
  received_at: string | null;
  quality: string;
  availability: "CURRENT" | "STALE" | "DISABLED" | "MISSING" | "HISTORICAL";
}
export interface Device {
  id: string;
  territory_id: string;
  zone_id: string;
  name: string;
  device_type: "SENSOR" | "ACTUATOR" | "CAMERA" | "CONTROLLER";
  source: DataSource;
  active: boolean;
  status: "ONLINE" | "OFFLINE" | "WARNING" | "ERROR" | "SIMULATED";
  last_seen: string | null;
  created_at: string;
  updated_at: string;
  sensor_id: string | null;
  channels: Channel[];
  actuator_type: string | null;
  actuator_state: string | null;
  safety_status: string | null;
  last_action: string | null;
}
export interface PlantInput {
  name: string;
  profile_id: string;
  zone_id: string;
  planted_on: string | null;
  growth_stage: Stage;
  camera_device_id: string | null;
  sensor_channel_ids: string[];
}
export interface Plant extends PlantInput {
  id: string;
  territory_id: string;
  health_status: "UNKNOWN";
}
export interface PlantReadings {
  health_status: "UNKNOWN";
  health_explanation: string;
  effective_requirements: Requirements;
  channels: Channel[];
  history: Channel[];
}
export const channelNames: Record<string, string> = {
  soil_moisture_pct: "Влажность почвы",
  air_temperature_c: "Температура воздуха",
  air_humidity_pct: "Влажность воздуха",
  light_lux: "Освещённость",
  pressure_hpa: "Давление",
  battery_pct: "Заряд батареи",
};
export const deviceNames: Record<Device["device_type"], string> = {
  SENSOR: "Сенсорная станция",
  ACTUATOR: "Привод",
  CAMERA: "Камера",
  CONTROLLER: "Контроллер",
};
export const blankRequirements = (): Requirements => ({
  soil_moisture_min: null,
  soil_moisture_max: null,
  temperature_min: null,
  temperature_max: null,
  humidity_min: null,
  humidity_max: null,
  ph_min: null,
  ph_max: null,
  light_requirements: "",
  irrigation_requirements: "",
  nutrient_requirements: "",
});
