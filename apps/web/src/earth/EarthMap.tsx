import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Circle,
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { api } from "../api";
import { ErrorBox } from "../pages";
import type { Layer, MapPoint } from "./types";
import type { Area } from "../global/types";
import "leaflet/dist/leaflet.css";

function Actions({
  area,
  onSelect,
}: {
  area?: Area;
  onSelect?: (lat: number, lng: number) => void;
}) {
  const map = useMap();
  const latitude = area?.latitude,
    longitude = area?.longitude,
    radius = area?.radius_km;
  useEffect(() => {
    if (
      latitude !== undefined &&
      longitude !== undefined &&
      radius !== undefined
    )
      map.flyTo(
        [latitude, longitude],
        Math.max(3, Math.min(11, Math.round(11 - Math.log2(radius / 2)))),
      );
  }, [map, latitude, longitude, radius]);
  useMapEvents({
    click: (e) =>
      onSelect?.(
        Math.max(-85, Math.min(85, e.latlng.lat)),
        ((((e.latlng.lng + 180) % 360) + 360) % 360) - 180,
      ),
  });
  return null;
}

export function EarthMap({
  area,
  onSelect,
  points = [],
  ocean = false,
  extraLayer,
}: {
  area?: Area;
  onSelect?: (lat: number, lng: number) => void;
  points?: MapPoint[];
  ocean?: boolean;
  extraLayer?: string;
}) {
  const catalog = useQuery({
    queryKey: ["earth-layers"],
    queryFn: () => api<{ items: Layer[]; fetched_at: string }>("/earth/layers"),
    staleTime: 3600000,
  });
  const [layerId, setLayerId] = useState(
    ocean
      ? "MODIS_Aqua_L2_Chlorophyll_A"
      : "MODIS_Terra_CorrectedReflectance_TrueColor",
  );
  const [date, setDate] = useState(() =>
    new Date(Date.now() - 2 * 86400000).toISOString().slice(0, 10),
  );
  const [compare, setCompare] = useState(false);
  const [otherDate, setOtherDate] = useState(() =>
    new Date(Date.now() - 367 * 86400000).toISOString().slice(0, 10),
  );
  const [playing, setPlaying] = useState(false);
  const [tileError, setTileError] = useState(false);
  const [tileLoading, setTileLoading] = useState(false);
  const [showPoints, setShowPoints] = useState(true);
  const layer = catalog.data?.items.find((x) => x.id === layerId);
  const monthly =
    layer?.time_ranges.some((range) => range.endsWith("/P1M")) ?? false;
  const today = new Date().toISOString().slice(0, 10);
  const latest = layer?.default_date?.slice(0, 10) || today;
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => {
      setDate((value) => {
        const next = new Date(value + "T00:00:00Z");
        if (monthly) {
          next.setUTCDate(1);
          next.setUTCMonth(next.getUTCMonth() + 1);
        } else next.setUTCDate(next.getUTCDate() + 1);
        const nextDate = next.toISOString().slice(0, 10);
        return nextDate > latest ? latest : nextDate;
      });
    }, 1800);
    return () => clearInterval(timer);
  }, [playing, monthly, latest]);
  useEffect(() => {
    if (date >= latest && playing) setPlaying(false);
  }, [date, latest, playing]);
  function pane(selectedDate: string) {
    return (
      <MapContainer
        center={area ? [area.latitude, area.longitude] : [20, 0]}
        zoom={area ? 6 : 2}
        minZoom={2}
        maxZoom={18}
        className="earth-map"
        worldCopyJump
      >
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />
        {layer && (
          <TileLayer
            key={layer.id + selectedDate}
            url={`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer.id}/default/${selectedDate}/${layer.matrix}/{z}/{y}/{x}.${layer.extension}`}
            attribution="NASA GIBS / Earthdata"
            maxNativeZoom={layer.max_zoom}
            maxZoom={18}
            eventHandlers={{
              loading: () => setTileLoading(true),
              load: () => setTileLoading(false),
              tileerror: () => setTileError(true),
            }}
          />
        )}
        {extraLayer && (
          <TileLayer
            url={extraLayer}
            attribution="UMD Hansen / Google Earth Engine"
          />
        )}
        <Actions area={area} onSelect={onSelect} />
        {area && (
          <Circle
            center={[area.latitude, area.longitude]}
            radius={area.radius_km * 1000}
            pathOptions={{ color: "#d0e8a0", weight: 2, fillOpacity: 0.05 }}
          />
        )}
        {showPoints &&
          points.map((p) => (
            <CircleMarker
              key={p.id}
              center={[p.latitude, p.longitude]}
              radius={5}
              pathOptions={{ color: "#f2b175", fillOpacity: 0.85, weight: 1 }}
            >
              <Popup>
                <strong>{p.name}</strong>
                <p>{p.detail}</p>
                {p.url && (
                  <a href={p.url} target="_blank" rel="noreferrer">
                    Источник
                  </a>
                )}
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>
    );
  }
  return (
    <section className="global-map-panel">
      <div className="earth-map-controls">
        <label>
          Слой наблюдений
          <select
            value={layerId}
            onChange={(e) => {
              setLayerId(e.target.value);
              const selected = catalog.data?.items.find(
                (item) => item.id === e.target.value,
              );
              if (
                selected?.default_date &&
                /^\d{4}-\d{2}-\d{2}/.test(selected.default_date)
              )
                setDate(selected.default_date.slice(0, 10));
              setTileError(false);
              setPlaying(false);
            }}
          >
            <option value="osm">Базовая карта OpenStreetMap</option>
            {catalog.data?.items.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Дата карты
          <input
            aria-label="Дата карты"
            type="date"
            min="2000-01-01"
            max={today}
            value={date}
            onChange={(e) => {
              if (e.target.value) {
                setDate(e.target.value);
                setTileError(false);
              }
            }}
          />
        </label>
        <button
          className="global-secondary"
          disabled={!layer || date >= latest}
          onClick={() => setPlaying(!playing)}
        >
          {playing
            ? "Остановить"
            : monthly
              ? "Анимация по месяцам"
              : "Анимация по дням"}
        </button>
        <label className="global-toggle">
          <input
            type="checkbox"
            checked={compare}
            onChange={(e) => setCompare(e.target.checked)}
          />
          Сравнить даты
        </label>
        {points.length > 0 && (
          <label className="global-toggle">
            <input
              type="checkbox"
              checked={showPoints}
              onChange={(e) => setShowPoints(e.target.checked)}
            />
            Метки ({points.length})
          </label>
        )}
      </div>
      {compare && (
        <label className="earth-compare-date">
          Вторая дата
          <input
            type="date"
            max={today}
            min="2000-01-01"
            value={otherDate}
            onChange={(e) => e.target.value && setOtherDate(e.target.value)}
          />
        </label>
      )}
      <ErrorBox error={catalog.error} />
      {(catalog.isPending || (layer && tileLoading)) && (
        <p className="global-map-notice" role="status">
          Загружаем спутниковый слой NASA…
        </p>
      )}
      <div className={compare ? "earth-map-compare" : ""}>
        <div>
          {pane(date)}
          <p className="earth-map-date">{date}</p>
        </div>
        {compare && (
          <div>
            {pane(otherDate)}
            <p className="earth-map-date">{otherDate}</p>
          </div>
        )}
      </div>
      <div className="global-map-caption">
        <span>
          {layer?.source ?? "OpenStreetMap"} · {layer?.name ?? "Базовая карта"}
        </span>
        <span>
          {area
            ? `${area.latitude.toFixed(4)}°, ${area.longitude.toFixed(4)}° · ${area.radius_km} км`
            : "Глобальный охват"}
        </span>
      </div>
      {layer && (
        <details className="earth-layer-info">
          <summary>Легенда и доступность слоя</summary>
          {layer.legend && (
            <a href={layer.legend} target="_blank" rel="noreferrer">
              Открыть легенду NASA
            </a>
          )}
          <p>
            Последняя дата по каталогу: {layer.default_date}. Диапазон:{" "}
            {layer.time_ranges.join(", ")}.
          </p>
          <p>
            Облачность, орбиты и периодичность продукта оставляют пробелы.
            Пустой пиксель не означает отсутствие загрязнения. Карта Web
            Mercator охватывает широты до ±85°; полюса смотрите в{" "}
            <a
              href="https://worldview.earthdata.nasa.gov/"
              target="_blank"
              rel="noreferrer"
            >
              NASA Worldview
            </a>
            .
          </p>
        </details>
      )}
      {layer && date > layer.default_date.slice(0, 10) && (
        <p className="global-map-notice" role="status">
          Для этого продукта последняя дата в каталоге — {layer.default_date}.
          Выберите доступную дату; прозрачная карта не означает отсутствия
          явления.
        </p>
      )}
      {tileError && (
        <p className="global-map-notice" role="status">
          Часть снимка недоступна для этой даты или масштаба. Выберите дату из
          диапазона слоя.
        </p>
      )}
    </section>
  );
}
