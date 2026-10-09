import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMapEvents,
  Polygon,
  useMap,
} from "react-leaflet";
import { useEffect } from "react";
import type { Observation, Satellite, Territory } from "./types";
import "leaflet/dist/leaflet.css";
function SelectPoint({
  onSelect,
}: {
  onSelect?: (lat: number, lng: number) => void;
}) {
  useMapEvents({ click: (e) => onSelect?.(e.latlng.lat, e.latlng.lng) });
  return null;
}
function Center({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.panTo([lat, lng]);
  }, [map, lat, lng]);
  return null;
}
export function TerritoryMap({
  latitude,
  longitude,
  polygon = null,
  observations = [],
  onSelect,
  satellite,
}: {
  latitude: number;
  longitude: number;
  polygon?: Territory["polygon"];
  observations?: Observation[];
  onSelect?: (lat: number, lng: number) => void;
  satellite?: Satellite;
}) {
  return (
    <MapContainer
      center={[latitude, longitude]}
      zoom={satellite ? 9 : 17}
      className="map"
      scrollWheelZoom={false}
      aria-label="Карта территории"
    >
      <TileLayer
        key={satellite?.url ?? "osm"}
        attribution={
          satellite ? "NASA GIBS / EOSDIS" : "&copy; OpenStreetMap contributors"
        }
        url={
          satellite?.url ?? "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        }
        maxNativeZoom={satellite ? 9 : 19}
        maxZoom={19}
      />
      <Center lat={latitude} lng={longitude} />
      <SelectPoint onSelect={onSelect} />
      <CircleMarker
        center={[latitude, longitude]}
        radius={10}
        pathOptions={{ color: "#174b39", fillColor: "#abd36e", fillOpacity: 1 }}
      >
        <Popup>Центр территории</Popup>
      </CircleMarker>
      {polygon && (
        <Polygon
          positions={polygon.coordinates[0].map((c) => [c[1], c[0]])}
          pathOptions={{ color: "#246246" }}
        />
      )}
      {observations.map((o) => (
        <CircleMarker
          key={o.id}
          center={[o.latitude, o.longitude]}
          radius={7}
          pathOptions={{
            color: o.severity === "critical" ? "#ad3535" : "#bd801a",
          }}
        >
          <Popup>{o.text}</Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
