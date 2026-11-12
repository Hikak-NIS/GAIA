import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useParams, Link } from "react-router-dom";
import { api } from "../api";
import { ErrorBox, Loading } from "../pages";
import type { Territory } from "../types";
import type { Device } from "../foundation/types";
import { ChannelTable } from "../foundation/shared";
import { EarthMap } from "./EarthMap";
import { Metrics, Chart, Sources } from "./Panels";
import { Assistant } from "./Assistant";
import type { Metric, Source } from "./types";

export function GrowLayout() {
  const { tid = "" } = useParams();
  const q = useQuery({
    queryKey: ["territory", tid],
    queryFn: () => api<Territory>(`/territories/${tid}`),
  });
  if (q.isPending) return <Loading />;
  if (!q.data) return <ErrorBox error={q.error} />;
  return (
    <>
      <div className="territory-heading">
        <div>
          <span className="eyebrow">GAIA GROW / ТЕРРИТОРИЯ</span>
          <h1>{q.data.name}</h1>
          <p>
            {q.data.latitude}°, {q.data.longitude}° · {q.data.area} м²
          </p>
        </div>
      </div>
      <nav className="tabs" aria-label="Разделы территории">
        {[
          ["", "Мониторинг"],
          ["map", "Спутниковая карта"],
          ["zones", "Зоны"],
          ["plants", "Растения"],
          ["devices", "Устройства"],
          ["observations", "Наблюдения"],
          ["settings", "Настройки"],
        ].map(([path, label]) => (
          <NavLink key={label} to={path} end={path === ""}>
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet context={{ dashboard: { territory: q.data } }} />
      <Assistant territoryId={tid} />
    </>
  );
}

export function GrowOverview({ mapOnly = false }: { mapOnly?: boolean }) {
  const { tid = "" } = useParams();
  const territory = useQuery({
    queryKey: ["territory", tid],
    queryFn: () => api<Territory>(`/territories/${tid}`),
  });
  const devices = useQuery({
    queryKey: ["foundation", "devices", tid],
    queryFn: () => api<Device[]>(`/territories/${tid}/devices?source=REAL`),
    refetchInterval: 15000,
    enabled: !mapOnly,
  });
  const environment = useQuery({
    queryKey: ["grow-environment", tid],
    queryFn: () =>
      api<Record<string, Source<{ metrics: Metric[] }>>>(
        `/grow/territories/${tid}/environment`,
      ),
    staleTime: 1800000,
    enabled: !mapOnly,
  });
  const metrics = Object.values(environment.data ?? {}).flatMap(
    (s) => s.data?.metrics ?? [],
  );
  const channels = devices.data?.flatMap((d) => d.channels ?? []) ?? [];
  const area = territory.data
    ? {
        name: territory.data.name,
        latitude: territory.data.latitude,
        longitude: territory.data.longitude,
        radius_km: 1,
      }
    : undefined;
  function exportData() {
    const url = URL.createObjectURL(
      new Blob(
        [
          JSON.stringify(
            {
              territory: territory.data,
              devices: devices.data,
              environment: environment.data,
            },
            null,
            2,
          ),
        ],
        { type: "application/json" },
      ),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `GAIA-Grow-${tid}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <>
      <ErrorBox error={territory.error || devices.error || environment.error} />
      {!mapOnly && (
        <section className="panel">
          <div className="page-heading">
            <h2>Полевые измерения</h2>
            <button className="button secondary" onClick={exportData}>
              Экспорт наблюдений
            </button>
          </div>
          <ChannelTable channels={channels} />
          {!devices.data?.length && (
            <p>
              Нет подключённых приборов.{" "}
              <Link to="devices">Добавьте устройство</Link> и отправьте
              телеметрию. До получения показаний состояние почвы не
              определяется.
            </p>
          )}
        </section>
      )}
      <div className="global-app earth-grow">
        <EarthMap area={area} />
        <p className="global-muted">
          Круг радиусом 1 км показывает окружение участка, а не его границы.
          Спутниковое разрешение может быть грубее размера участка.
        </p>
        {!mapOnly && (
          <>
            <h2>Погода, почва и атмосфера</h2>
            <p className="global-muted">
              Ближайшие ячейки расчётных моделей; не заменяют датчики участка.
            </p>
            {environment.isPending && (
              <p role="status">Получаем окружающие условия…</p>
            )}
            <Sources sources={environment.data ?? {}} />
            <Metrics metrics={metrics} />
            <Chart metrics={metrics} />
          </>
        )}
      </div>
    </>
  );
}
