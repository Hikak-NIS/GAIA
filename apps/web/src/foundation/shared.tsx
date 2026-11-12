import { useQuery } from "@tanstack/react-query";
import { api, client, dateTime, format } from "../api";
import { Field } from "../pages";
import {
  channelNames,
  type Channel,
  type DataSource,
  type Device,
  type PlantProfile,
  type Requirements,
  type TerritoryZone,
} from "./types";

export const refreshInventory = () =>
  client.invalidateQueries({ queryKey: ["foundation"] });
export function useInventory(tid: string) {
  const zones = useQuery({
    queryKey: ["foundation", "zones", tid],
    queryFn: () => api<TerritoryZone[]>(`/territories/${tid}/zones`),
  });
  const profiles = useQuery({
    queryKey: ["foundation", "profiles"],
    queryFn: () => api<PlantProfile[]>("/plant-profiles"),
  });
  const devices = useQuery({
    queryKey: ["foundation", "devices", tid],
    queryFn: () => api<Device[]>(`/territories/${tid}/devices`),
    refetchInterval: 5000,
  });
  return {
    zones,
    profiles,
    devices,
    pending: zones.isPending || profiles.isPending || devices.isPending,
    error: zones.error || profiles.error || devices.error,
  };
}
export function SourceBadge({ source }: { source: DataSource }) {
  if (source !== "REAL") return null;
  return (
    <span className={`source-badge source-${source.toLowerCase()}`}>
      Прибор
    </span>
  );
}
export function ChannelTable({
  channels,
  history = false,
  timezone,
}: {
  channels: Channel[];
  history?: boolean;
  timezone?: string;
}) {
  return (
    <div className="table-scroll">
      <table className="inventory-table">
        <thead>
          <tr>
            <th>Сенсор</th>
            <th>Источник</th>
            <th>Значение</th>
            <th>Качество</th>
            <th>Измерено</th>
          </tr>
        </thead>
        <tbody>
          {channels.map((c, i) => (
            <tr key={`${c.id}-${c.timestamp}-${i}`}>
              <td>
                {channelNames[c.sensor_type] ?? c.sensor_type}
                <small className="source">Канал {c.id.slice(0, 8)}</small>
              </td>
              <td>
                <SourceBadge source={c.source} />
              </td>
              <td>
                {format(c.current_value)} {c.unit}
              </td>
              <td>
                {c.quality === "valid"
                  ? "Валидно"
                  : c.quality === "missing"
                    ? "Нет данных"
                    : c.quality === "invalid"
                      ? "Невалидно"
                      : "Устарело"}
                {c.availability === "STALE" && (
                  <small className="source">Данные устарели</small>
                )}
                {c.availability === "DISABLED" && (
                  <small className="source">Устройство отключено</small>
                )}
              </td>
              <td>
                {c.timestamp ? dateTime(c.timestamp, timezone) : "—"}
                {c.received_at && (
                  <small className="source">
                    Получено: {dateTime(c.received_at, timezone)}
                  </small>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {channels.length === 0 && (
        <p>{history ? "История пока пуста." : "Привязанных сенсоров нет."}</p>
      )}
    </div>
  );
}
const ranges = [
  ["soil_moisture", "Влажность почвы, %", 0, 100],
  ["temperature", "Температура, °C", -60, 70],
  ["humidity", "Влажность воздуха, %", 0, 100],
  ["ph", "pH", 0, 14],
] as const;
export function RequirementsFields({
  value,
  onChange,
  prefix = "",
}: {
  value: Requirements;
  onChange: (r: Requirements) => void;
  prefix?: string;
}) {
  return (
    <div className="form-grid">
      {ranges.map(([key, label, min, max]) => (
        <fieldset className="range-fields" key={key}>
          <legend>
            {prefix}
            {label}
          </legend>
          {(["min", "max"] as const).map((bound) => {
            const name = `${key}_${bound}` as keyof Requirements;
            return (
              <Field
                label={`${prefix}${label} — ${bound === "min" ? "минимум" : "максимум"}`}
                key={bound}
              >
                <input
                  type="number"
                  step="any"
                  min={min}
                  max={max}
                  value={value[name] ?? ""}
                  onChange={(e) =>
                    onChange({
                      ...value,
                      [name]:
                        e.target.value === "" ? null : Number(e.target.value),
                    })
                  }
                />
              </Field>
            );
          })}
        </fieldset>
      ))}
      {(
        [
          ["light_requirements", "Требования к свету"],
          ["irrigation_requirements", "Требования к поливу"],
          ["nutrient_requirements", "Требования к питанию"],
        ] as const
      ).map(([key, label]) => (
        <Field label={prefix + label} key={key}>
          <textarea
            maxLength={3000}
            value={value[key]}
            onChange={(e) => onChange({ ...value, [key]: e.target.value })}
          />
        </Field>
      ))}
    </div>
  );
}
export function RequirementSummary({ value }: { value: Requirements }) {
  return (
    <dl className="requirements-summary">
      {ranges.map(([key, label]) => (
        <div key={key}>
          <dt>{label}</dt>
          <dd>
            {value[`${key}_min`] === null
              ? "Не задано"
              : `${value[`${key}_min`]}–${value[`${key}_max`]}`}
          </dd>
        </div>
      ))}
      {(
        [
          ["light_requirements", "Свет"],
          ["irrigation_requirements", "Полив"],
          ["nutrient_requirements", "Питание"],
        ] as const
      ).map(([key, label]) => (
        <div key={key}>
          <dt>{label}</dt>
          <dd>{value[key] || "Не задано"}</dd>
        </div>
      ))}
    </dl>
  );
}
