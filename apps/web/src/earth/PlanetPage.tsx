import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { ErrorBox } from "../pages";
import { EarthMap } from "./EarthMap";
import { Metrics, Chart } from "./Panels";
import { Assistant } from "./Assistant";
import type { Metric, Source } from "./types";
import { eventPoints, type Events } from "./events";
import { PolarPanel } from "./PolarPanel";

export function OceanSummary() {
  const q = useQuery({
    queryKey: ["ocean-overview"],
    queryFn: () =>
      api<{
        points: { id: string; name: string }[];
        sources: Record<string, Source<{ metrics: Metric[] }>>;
        note: string;
      }>("/earth/ocean-overview"),
    staleTime: 1800000,
  });
  return (
    <section className="global-panel earth-ocean-summary">
      <div className="global-section-heading">
        <div>
          <span className="global-overline">СВЯЗАННАЯ СИСТЕМА</span>
          <h2>GAIA Ocean</h2>
        </div>
        <Link className="button" to="/global/ocean">
          Открыть Ocean →
        </Link>
      </div>
      <p>
        Температура моря, хлорофилл, водная поверхность и исследование
        загрязнения.
      </p>
      <ErrorBox error={q.error} />
      {q.isPending && <p role="status">Получаем морские данные…</p>}
      <div className="earth-ocean-points">
        {q.data?.points.map((p) => (
          <article key={p.id}>
            <h3>{p.name}</h3>
            {q.data.sources[p.id].status === "ok" ? (
              <Metrics
                metrics={
                  q.data.sources[p.id].data?.metrics.filter(
                    (m) => m.id === "sea_surface_temperature",
                  ) ?? []
                }
              />
            ) : (
              <p>Морская модель недоступна.</p>
            )}
          </article>
        ))}
      </div>
      <p className="global-muted">{q.data?.note}</p>
    </section>
  );
}

export default function PlanetPage() {
  const q = useQuery({
    queryKey: ["earth-planet"],
    queryFn: () =>
      api<{
        fetched_at: string;
        sources: {
          temperature: Source<Metric>;
          co2: Source<Metric>;
          arctic_ice?: Source<Metric>;
          antarctic_ice?: Source<Metric>;
          events: Source<Events>;
        };
        note: string;
      }>("/earth/planet"),
    staleTime: 1800000,
  });
  const metrics = q.data
    ? [
        q.data.sources.temperature.data,
        q.data.sources.co2.data,
        q.data.sources.arctic_ice?.data,
        q.data.sources.antarctic_ice?.data,
      ].filter((m): m is Metric => !!m)
    : [];
  return (
    <>
      <div className="global-page-heading">
        <span className="global-overline">
          GAIA GLOBAL / ОБСЕРВАТОРИЯ ЗЕМЛИ
        </span>
        <h1>Одна планета. Связанные системы.</h1>
        <p>
          Климат, суша, атмосфера и океан — наблюдения с проверяемым
          происхождением.
        </p>
      </div>
      <div className="earth-section-links">
        <Link to="/global/territories">Исследовать территорию ↗</Link>
        <Link to="/global/ocean">Вода и океан ↗</Link>
        <Link to="/global/events">Пожары и природные события ↗</Link>
      </div>
      <EarthMap points={eventPoints(q.data?.sources.events.data)} />
      <ErrorBox error={q.error} />
      {q.isPending && <p role="status">Получаем наблюдения планеты…</p>}
      <section className="earth-section">
        <div className="global-section-heading">
          <h2>Климатические индикаторы Земли</h2>
          <button
            className="global-secondary"
            disabled={q.isFetching}
            onClick={() => q.refetch()}
          >
            Обновить
          </button>
        </div>
        <Metrics metrics={metrics} />
        {q.data &&
          Object.entries(q.data.sources)
            .filter(([, s]) => s.status !== "ok")
            .map(([key, s]) => (
              <p key={key} className="global-warning">
                {key}: {s.message}
              </p>
            ))}
        <p className="global-muted">
          {q.data?.note} Последнее получение:{" "}
          {q.data?.fetched_at.slice(0, 16).replace("T", " ") ?? "ожидание"} UTC.
        </p>
        <Chart metrics={metrics} />
      </section>
      <PolarPanel
        north={q.data?.sources.arctic_ice?.data?.observed_at}
        south={q.data?.sources.antarctic_ice?.data?.observed_at}
      />
      <OceanSummary />
      <section className="global-panel">
        <h2>Повреждения и изменения экосистем</h2>
        <div className="earth-topic-grid">
          <article>
            <h3>Леса и растительность</h3>
            <p>
              NDVI на временных картах, потеря древесного покрова по UMD Hansen
              через Earth Engine. Для определения причины нужны дополнительные
              свидетельства.
            </p>
          </article>
          <article>
            <h3>Атмосфера и пожары</h3>
            <p>
              Спутниковые аэрозоли, CAMS для выбранной территории, каталог EONET
              и очаги FIRMS.
            </p>
          </article>
          <article>
            <h3>Лёд и водный баланс</h3>
            <p>
              Морской лёд, снежный покров и сравнение дат. Изменение снежного
              покрова само по себе не измеряет массу ледника.
            </p>
          </article>
        </div>
      </section>
      <Assistant />
    </>
  );
}
