import { useEffect, useState } from "react";
import {
  Circle,
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import { Crosshair, Layers } from "lucide-react";
import { categoryNames, type Area, type GlobalMarker } from "./types";
import "leaflet/dist/leaflet.css";

function MapActions({
  area,
  onSelect,
}: {
  area: Area;
  onSelect: (lat: number, lng: number) => void;
}) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(
      [area.latitude, area.longitude],
      Math.max(3, Math.min(10, Math.round(10 - Math.log2(area.radius_km / 3)))),
    );
  }, [map, area.latitude, area.longitude, area.radius_km]);
  useMapEvents({
    click: (e) =>
      onSelect(
        Math.max(-85, Math.min(85, e.latlng.lat)),
        ((((e.latlng.lng + 180) % 360) + 360) % 360) - 180,
      ),
  });
  return null;
}
export function GlobalMap({
  area,
  markers,
  onSelect,
}: {
  area: Area;
  markers: GlobalMarker[];
  onSelect: (lat: number, lng: number) => void;
}) {
  const [layer, setLayer] = useState("osm");
  const [showMarkers, setShowMarkers] = useState(true);
  const [tileError, setTileError] = useState(false);
  const [date] = useState(() =>
    new Date(Date.now() - 2 * 86400000).toISOString().slice(0, 10),
  );
  return (
    <section
      className="global-map-panel"
      aria-label="Интерактивная экологическая карта"
    >
      <div className="global-map-tools">
        <span>
          <Crosshair size={16} />
          Выбор территории
        </span>
        <div>
          <label>
            <Layers size={15} />
            <span className="sr-only">Подложка карты</span>
            <select
              aria-label="Подложка карты"
              value={layer}
              onChange={(e) => {
                setLayer(e.target.value);
                setTileError(false);
              }}
            >
              <option value="osm">OpenStreetMap</option>
              <option value="nasa">NASA GIBS · спутник</option>
            </select>
          </label>
          <label className="global-toggle">
            <input
              type="checkbox"
              checked={showMarkers}
              onChange={(e) => setShowMarkers(e.target.checked)}
            />
            Маркеры
          </label>
        </div>
      </div>
      <MapContainer
        center={[area.latitude, area.longitude]}
        zoom={5}
        className="global-map"
        scrollWheelZoom
        worldCopyJump
        maxBounds={[
          [-85, -540],
          [85, 540],
        ]}
        minZoom={2}
        aria-label="Карта GAIA Global"
      >
        <TileLayer
          key={layer + date}
          url={
            layer === "nasa"
              ? `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`
              : "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          }
          attribution={
            layer === "nasa"
              ? "NASA GIBS / EOSDIS"
              : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          }
          maxNativeZoom={layer === "nasa" ? 9 : 19}
          maxZoom={18}
          eventHandlers={{ tileerror: () => setTileError(true) }}
        />
        <MapActions area={area} onSelect={onSelect} />
        <Circle
          center={[area.latitude, area.longitude]}
          radius={area.radius_km * 1000}
          pathOptions={{
            color: "#466c36",
            fillColor: "#b6eb87",
            fillOpacity: 0.25,
            weight: 2,
            dashArray: "6 5",
          }}
        />
        <CircleMarker
          center={[area.latitude, area.longitude]}
          radius={6}
          pathOptions={{ color: "#fff", fillColor: "#325e36", fillOpacity: 1 }}
        >
          <Popup>
            {area.name}
            <br />
            Радиус: {area.radius_km} км
          </Popup>
        </CircleMarker>
        {showMarkers &&
          markers.map((m) => (
            <CircleMarker
              key={m.id}
              center={[m.latitude, m.longitude]}
              radius={7}
              pathOptions={{
                color: "#543610",
                fillColor: "#f4b85f",
                fillOpacity: 0.95,
              }}
            >
              <Popup>
                <b>{m.title}</b>
                <p>{categoryNames[m.category]} · ручной маркер</p>
                <p>{m.note}</p>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>
      <div className="global-map-caption">
        <span>
          {area.latitude.toFixed(4)}°, {area.longitude.toFixed(4)}°
        </span>
        <span>Клик по карте — выбрать центр · радиус {area.radius_km} км</span>
      </div>
      {layer === "nasa" && (
        <p className="global-map-notice">
          NASA GIBS · дата подложки {date}. Облачность и пробелы возможны.
          Подложка не используется для DEMO-расчётов.
        </p>
      )}
      {tileError && (
        <p className="global-map-notice" role="status">
          Часть тайлов не загрузилась. Проверьте интернет или смените подложку.
          Координаты и DEMO-анализ доступны независимо от карты.
        </p>
      )}
    </section>
  );
}
