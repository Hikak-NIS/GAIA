import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { ErrorBox } from "../pages";
import { EarthMap } from "./EarthMap";
import { eventPoints, type Events } from "./events";
import type { MapPoint } from "./types";

export function EventsPage() {
  const [category, setCategory] = useState("all"),
    [firms, setFirms] = useState(false),
    [forest, setForest] = useState(false);
  const events = useQuery({
    queryKey: ["earth-events"],
    queryFn: () => api<Events>("/earth/events"),
    staleTime: 900000,
  });
  const hotspots = useQuery({
    queryKey: ["earth-fires"],
    queryFn: () =>
      api<{
        items: {
          latitude: number;
          longitude: number;
          date: string;
          confidence: string;
        }[];
        note: string;
      }>("/earth/fires"),
    enabled: firms,
    staleTime: 900000,
  });
  const forestLayer = useQuery({
    queryKey: ["earth-forest-map"],
    queryFn: () => api<{ url: string; note: string }>("/earth/forest-map"),
    enabled: forest,
    staleTime: 900000,
  });
  const filtered = events.data
    ? {
        ...events.data,
        items: events.data.items.filter(
          (e) =>
            category === "all" || e.categories.some((c) => c.id === category),
        ),
      }
    : undefined;
  const points = eventPoints(filtered).concat(
    firms
      ? (hotspots.data?.items.map((p, i) => ({
          ...p,
          id: `fire-${i}`,
          name: "Тепловая аномалия VIIRS",
          detail: `${p.date} · confidence ${p.confidence}`,
        })) ?? [])
      : [],
  );
  return (
    <>
      <div className="global-page-heading">
        <span className="global-overline">ИЗМЕНЕНИЯ И НАГРУЗКИ</span>
        <h1>События на планете</h1>
        <p>Пожары, штормы, ледовые события и изменения древесного покрова.</p>
      </div>
      <div className="global-panel earth-button-row">
        <label>
          Категория
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="all">Все события</option>
            <option value="wildfires">Пожары</option>
            <option value="severeStorms">Штормы</option>
            <option value="seaLakeIce">Морской и озёрный лёд</option>
            <option value="volcanoes">Вулканы</option>
          </select>
        </label>
        <label className="global-toggle">
          <input
            type="checkbox"
            checked={firms}
            onChange={(e) => setFirms(e.target.checked)}
          />
          Очаги FIRMS за сутки
        </label>
        <label className="global-toggle">
          <input
            type="checkbox"
            checked={forest}
            onChange={(e) => setForest(e.target.checked)}
          />
          Потери лесного покрова · Earth Engine
        </label>
      </div>
      <ErrorBox error={events.error || hotspots.error || forestLayer.error} />
      <EarthMap
        points={points}
        extraLayer={forest ? forestLayer.data?.url : undefined}
      />
      <p className="global-muted">
        {events.data?.note} {firms && hotspots.data?.note}{" "}
        {forest && forestLayer.data?.note}
      </p>
      <div className="earth-event-list">
        {filtered?.items.slice(0, 50).map((e) => (
          <article className="global-panel" key={e.id}>
            <h3>{e.name}</h3>
            <p>
              {e.categories.map((c) => c.title).join(", ")} ·{" "}
              {e.date.slice(0, 10)}
            </p>
            <p>
              {e.latitude}°, {e.longitude}°
            </p>
            {e.sources[0] && (
              <a href={e.sources[0].url} target="_blank" rel="noreferrer">
                Первоисточник ↗
              </a>
            )}
          </article>
        ))}
      </div>
    </>
  );
}

export function OrganizationsPage() {
  const q = useQuery({
    queryKey: ["earth-organizations"],
    queryFn: () =>
      api<{
        items: (MapPoint & {
          focus: string;
          city: string;
          source_url: string;
        })[];
        note: string;
      }>("/earth/organizations"),
  });
  return (
    <>
      <div className="global-page-heading">
        <span className="global-overline">
          СООБЩЕСТВО / ЭКОЛОГИЧЕСКИЕ ОРГАНИЗАЦИИ
        </span>
        <h1>Знания и действия по всему миру.</h1>
        <p>{q.data?.note}</p>
      </div>
      <ErrorBox error={q.error} />
      <EarthMap
        points={q.data?.items.map((p) => ({
          ...p,
          detail: `${p.city}. ${p.focus}`,
        }))}
      />
      <div className="earth-topic-grid">
        {q.data?.items.map((p) => (
          <article className="global-panel" key={p.id}>
            <h2>{p.name}</h2>
            <p>{p.city}</p>
            <p>{p.focus}</p>
            <a href={p.source_url} target="_blank" rel="noreferrer">
              Сайт и контакты организации ↗
            </a>
          </article>
        ))}
      </div>
    </>
  );
}

export function IntegrationsPage() {
  const q = useQuery({
    queryKey: ["integrations-status"],
    queryFn: () =>
      api<{
        config_path?: string;
        items?: {
          name: string;
          configured: boolean;
          variables: string[];
          url: string;
        }[];
        note?: string;
      }>("/integrations/status"),
  });
  return (
    <>
      <div className="global-page-heading">
        <span className="global-overline">ИНТЕГРАЦИИ / НАСТРОЙКИ СЕРВЕРА</span>
        <h1>Подключения данных и ИИ</h1>
        <p>
          Ключи вводятся в <code>D:\GAIA\.env</code>. После изменения
          перезапустите сервер. Не вставляйте ключи в чат или файлы frontend.
        </p>
      </div>
      <ErrorBox error={q.error} />
      {q.data && !q.data.items && (
        <p>Настройки подключений доступны главному администратору.</p>
      )}
      <div className="earth-topic-grid">
        {q.data?.items?.map((item) => (
          <article className="global-panel" key={item.name}>
            <span
              className={item.configured ? "global-success" : "global-warning"}
            >
              {item.configured
                ? "Настройка найдена · доступ не проверен"
                : "Нужно заполнить"}
            </span>
            <h2>{item.name}</h2>
            <ul>
              {item.variables.map((v) => (
                <li key={v}>
                  <code>{v}</code>
                </li>
              ))}
            </ul>
            <a href={item.url} target="_blank" rel="noreferrer">
              Открыть настройки провайдера ↗
            </a>
          </article>
        ))}
      </div>
      <p className="global-muted">{q.data?.note}</p>
      <section className="global-panel">
        <h2>Настройка и обучение</h2>
        <p>
          Пошаговое подключение: <code>docs/real-data-setup.md</code>.
        </p>
        <p>
          Сбор проб, формат датасета, обучение и проверка модели:{" "}
          <code>docs/model-training.md</code>.
        </p>
        <p>
          Доступность источников и ограничения измерений:{" "}
          <code>docs/earth-data-methods.md</code>.
        </p>
      </section>
    </>
  );
}
