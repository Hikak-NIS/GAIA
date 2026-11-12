import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  Download,
  Globe2,
  MapPin,
  Plus,
  Radio,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { api, client, dateTime } from "../api";
import { ErrorBox } from "../pages";
import { useGlobalUser } from "./GlobalLayout";
import { GlobalMap } from "./GlobalMap";
import {
  Factors,
  HealthPanel,
  HistoryChart,
  IndicatorCards,
  Recommendations,
} from "./AnalysisPanels";
import {
  categoryNames,
  presets,
  weightNames,
  type Analysis,
  type AnalysisSummary,
  type Area,
  type GlobalMarker,
  type GlobalSettings,
  type Provider,
  type Scenario,
  type Weights,
} from "./types";

function WeightEditor({ settings }: { settings: GlobalSettings }) {
  const [weights, setWeights] = useState(settings.weights);
  const save = useMutation({
    mutationFn: () =>
      api<GlobalSettings>("/global/settings", "PUT", {
        weights,
        expected_revision: settings.revision,
      }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["global-settings"] });
      client.invalidateQueries({ queryKey: ["admin-audit"] });
    },
  });
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  return (
    <form
      className="global-weight-form"
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <p>
        Веса применяются только к новым анализам. Сохранённые результаты
        сохраняют свою версию модели.
      </p>
      <div className="global-weight-fields">
        {Object.entries(weightNames).map(([key, name]) => (
          <label key={key}>
            {name}, %
            <input
              type="number"
              min={0}
              max={100}
              step="0.1"
              required
              value={weights[key as keyof Weights]}
              onChange={(e) =>
                setWeights({ ...weights, [key]: Number(e.target.value) })
              }
            />
          </label>
        ))}
      </div>
      <p className={Math.abs(total - 100) > 0.001 ? "global-warning" : ""}>
        Сумма: {total.toFixed(1)}% / 100%
      </p>
      <ErrorBox error={save.error} />
      <button disabled={save.isPending || Math.abs(total - 100) > 0.001}>
        Сохранить веса
      </button>
    </form>
  );
}

function Markers({
  area,
  markers,
  onRefresh,
}: {
  area: Area;
  markers: GlobalMarker[];
  onRefresh: () => void;
}) {
  const user = useGlobalUser();
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("other");
  const [note, setNote] = useState("");
  const add = useMutation({
    mutationFn: () =>
      api("/global/markers", "POST", {
        title,
        category,
        note,
        latitude: area.latitude,
        longitude: area.longitude,
      }),
    onSuccess: () => {
      setAdding(false);
      setTitle("");
      setNote("");
      onRefresh();
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/global/markers/${id}`, "DELETE"),
    onSuccess: onRefresh,
  });
  return (
    <section className="global-panel">
      <div className="global-section-heading">
        <div>
          <span className="global-overline">ПОЛЕВЫЕ ЗАМЕТКИ</span>
          <h2>Экологические маркеры</h2>
        </div>
        <button className="global-secondary" onClick={() => setAdding(!adding)}>
          <Plus size={16} />
          Добавить маркер
        </button>
      </div>
      <p className="global-muted">
        Ручные заметки администраторов, не подтверждённые спутниковые
        наблюдения. Отображаются последние 200 маркеров.
      </p>
      {adding && (
        <form
          className="global-marker-form"
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate();
          }}
        >
          <p>
            Точка: {area.latitude.toFixed(4)}°, {area.longitude.toFixed(4)}°.
            Выберите другую точку на карте при необходимости.
          </p>
          <div className="global-two-fields">
            <label>
              Название маркера
              <input
                required
                maxLength={120}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label>
              Категория маркера
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {Object.entries(categoryNames).map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Заметка
            <textarea
              maxLength={3000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <button disabled={add.isPending}>Сохранить маркер</button>
        </form>
      )}
      <ErrorBox error={add.error || remove.error} />
      <div className="global-marker-list">
        {markers.slice(0, 20).map((m) => (
          <div key={m.id}>
            <MapPin size={17} />
            <div>
              <strong>{m.title}</strong>
              <small>
                {categoryNames[m.category]} · {m.latitude.toFixed(3)}°,{" "}
                {m.longitude.toFixed(3)}° · {dateTime(m.created_at)}
              </small>
              <p>{m.note}</p>
            </div>
            {(m.creator_id === user.id || user.role === "superadmin") && (
              <button
                className="global-icon-button"
                aria-label={`Удалить маркер ${m.title}`}
                disabled={remove.isPending}
                onClick={() => {
                  if (window.confirm(`Удалить маркер «${m.title}»?`))
                    remove.mutate(m.id);
                }}
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        ))}
      </div>
      {markers.length > 20 && (
        <p className="global-muted">
          В списке последние 20; на карте — до 200.
        </p>
      )}
      {markers.length === 0 && (
        <p className="global-empty-note">
          Выберите точку на карте и сохраните первую заметку.
        </p>
      )}
    </section>
  );
}

export default function GlobalPage() {
  const user = useGlobalUser();
  const [params, setParams] = useSearchParams();
  const aid = params.get("analysis");
  const [area, setArea] = useState<Area>({
    name: presets[0].name,
    latitude: presets[0].latitude,
    longitude: presets[0].longitude,
    radius_km: presets[0].radius_km,
  });
  const [scenario, setScenario] = useState<Scenario>("degraded");
  const [chosenPreset, setChosenPreset] = useState("aral");
  const history = useQuery({
    queryKey: ["global-history"],
    queryFn: () => api<AnalysisSummary[]>("/global/analyses"),
  });
  const providers = useQuery({
    queryKey: ["global-providers"],
    queryFn: () => api<Provider[]>("/global/providers"),
  });
  const settings = useQuery({
    queryKey: ["global-settings"],
    queryFn: () => api<GlobalSettings>("/global/settings"),
  });
  const markers = useQuery({
    queryKey: ["global-markers"],
    queryFn: () => api<GlobalMarker[]>("/global/markers"),
    refetchInterval: 15000,
  });
  const query = useQuery({
    queryKey: ["global-analysis", aid],
    queryFn: () => api<Analysis>(`/global/analyses/${aid}`),
    enabled: !!aid,
  });
  const run = useMutation({
    mutationFn: () =>
      api<Analysis>("/global/analyses", "POST", {
        area,
        scenario,
        source: "demo",
      }),
    onSuccess: (data) => {
      client.setQueryData(["global-analysis", data.id], data);
      setParams({ analysis: data.id });
      client.invalidateQueries({ queryKey: ["global-history"] });
    },
  });
  const analysis = query.error ? undefined : query.data;
  useEffect(() => {
    if (query.data) {
      setArea(query.data.area);
      setScenario(query.data.scenario);
      setChosenPreset("");
    }
  }, [query.data]);
  const changed =
    analysis &&
    (JSON.stringify(analysis.area) !== JSON.stringify(area) ||
      analysis.scenario !== scenario);
  function pick(lat: number, lng: number) {
    setArea((a) => ({
      ...a,
      name: "Выбранная территория",
      latitude: Number(lat.toFixed(5)),
      longitude: Number(lng.toFixed(5)),
    }));
    setChosenPreset("");
  }
  function exportResult() {
    if (!analysis) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(analysis, null, 2)], {
        type: "application/json",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `GAIA-DEMO-${analysis.id}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <>
      <div className="global-page-heading">
        <div>
          <div className="global-breadcrumb">
            ПЛАНЕТА <span>/</span> ЭКОЛОГИЧЕСКАЯ АНАЛИТИКА
          </div>
          <h1>
            От данных — к восстановлению<span>.</span>
          </h1>
          <p>
            Выберите территорию. Исследуйте сигналы. Определите направления
            действий.
          </p>
        </div>
        <span className="global-live-label">
          <Radio size={16} />
          РАБОЧИЙ ПРОТОТИП
        </span>
      </div>
      <div className="global-demo-notice">
        <Globe2 size={21} />
        <div>
          <strong>Демонстрационный контур</strong>
          <p>
            Все показатели, временные ряды и оценки ниже —{" "}
            <b>DEMO / SIMULATED DATA</b>. Координаты задают область примера, а
            не подтверждают её реальное состояние.
          </p>
        </div>
      </div>
      <div className="global-workbench">
        <div className="global-map-column">
          <GlobalMap area={area} markers={markers.data ?? []} onSelect={pick} />
          <form
            className="global-selection"
            onSubmit={(e) => {
              e.preventDefault();
              run.mutate();
            }}
          >
            <div className="global-selection-top">
              <label>
                Регион для примера
                <select
                  value={chosenPreset}
                  onChange={(e) => {
                    const p = presets.find((p) => p.id === e.target.value);
                    if (p) {
                      setChosenPreset(p.id);
                      setArea({
                        name: p.name,
                        latitude: p.latitude,
                        longitude: p.longitude,
                        radius_km: p.radius_km,
                      });
                      setScenario(p.scenario);
                    }
                  }}
                >
                  <option value="">Своя область</option>
                  {presets.map((p) => (
                    <option value={p.id} key={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Название области
                <input
                  value={area.name}
                  required
                  maxLength={120}
                  onChange={(e) => setArea({ ...area, name: e.target.value })}
                />
              </label>
              <label>
                DEMO-сценарий
                <select
                  value={scenario}
                  onChange={(e) => setScenario(e.target.value as Scenario)}
                >
                  <option value="degraded">Деградация</option>
                  <option value="recovering">Восстановление</option>
                  <option value="balanced">Устойчивый покров</option>
                </select>
              </label>
            </div>
            <div className="global-selection-bottom">
              <label>
                Широта
                <input
                  type="number"
                  required
                  step="any"
                  min={-85}
                  max={85}
                  value={area.latitude}
                  onChange={(e) => {
                    setArea({ ...area, latitude: Number(e.target.value) });
                    setChosenPreset("");
                  }}
                />
              </label>
              <label>
                Долгота
                <input
                  type="number"
                  required
                  step="any"
                  min={-180}
                  max={180}
                  value={area.longitude}
                  onChange={(e) => {
                    setArea({ ...area, longitude: Number(e.target.value) });
                    setChosenPreset("");
                  }}
                />
              </label>
              <label>
                Радиус, км
                <input
                  type="number"
                  required
                  min={1}
                  max={500}
                  step="any"
                  value={area.radius_km}
                  onChange={(e) =>
                    setArea({ ...area, radius_km: Number(e.target.value) })
                  }
                />
              </label>
              <button className="global-primary" disabled={run.isPending}>
                {run.isPending ? "Анализируем…" : "Анализировать территорию"}
                <ArrowRight size={17} />
              </button>
            </div>
            <small>
              Область — круг вокруг выбранного центра, не административная
              граница региона.
            </small>
          </form>
        </div>
        <HealthPanel analysis={analysis} />
      </div>
      <ErrorBox error={run.error || query.error || markers.error} />
      {aid && query.isPending && (
        <p role="status">Загружаем сохранённый анализ…</p>
      )}
      {changed && (
        <div className="global-stale-notice" role="status">
          Выбор изменён. Ниже показан сохранённый анализ «{analysis?.area.name}
          ». Нажмите «Анализировать территорию», чтобы обновить результат.
        </div>
      )}
      <div className="global-result-toolbar">
        <div>
          <span className="global-overline">
            {analysis ? "СОХРАНЁННЫЙ АНАЛИЗ" : "ГОТОВО К АНАЛИЗУ"}
          </span>
          <h2>{analysis?.area.name ?? area.name}</h2>
          {analysis && (
            <p>
              {dateTime(analysis.created_at)} · DEMO ·{" "}
              {analysis.area.latitude.toFixed(4)}°,{" "}
              {analysis.area.longitude.toFixed(4)}° · {analysis.area.radius_km}{" "}
              км
            </p>
          )}
        </div>
        <div>
          <label>
            <span className="sr-only">История анализов</span>
            <select
              aria-label="История анализов"
              value={aid ?? ""}
              onChange={(e) => {
                if (e.target.value) setParams({ analysis: e.target.value });
              }}
            >
              <option value="">Последние анализы</option>
              {history.data?.map((a) => (
                <option value={a.id} key={a.id}>
                  {a.name} · {dateTime(a.created_at)} · DEMO
                </option>
              ))}
            </select>
          </label>
          <button
            className="global-secondary"
            onClick={exportResult}
            disabled={!analysis}
          >
            <Download size={16} />
            Экспорт JSON
          </button>
        </div>
      </div>
      <ErrorBox error={history.error} />
      {analysis ? (
        <>
          <IndicatorCards metrics={analysis.metrics} />
          <div className="global-analysis-grid">
            <Factors analysis={analysis} />
            <HistoryChart analysis={analysis} />
          </div>
          <Recommendations analysis={analysis} />
        </>
      ) : (
        <section className="global-empty">
          <ScanPlaceholder />
          <div>
            <h2>Полный цикл — в одном исследовании</h2>
            <p>
              После запуска появятся 7 индикаторов, объяснение GEHI, динамика
              растительности и направления восстановления. Результат сохранится
              в общей истории администраторов.
            </p>
            <span>01 · Показатели → 02 · Оценка → 03 · Стратегия</span>
          </div>
        </section>
      )}
      <Markers
        area={area}
        markers={markers.data ?? []}
        onRefresh={() =>
          client.invalidateQueries({ queryKey: ["global-markers"] })
        }
      />
      <section className="global-panel">
        <div className="global-section-heading">
          <div>
            <span className="global-overline">ИСТОЧНИКИ И АРХИТЕКТУРА</span>
            <h2>От DEMO к наблюдениям Земли</h2>
          </div>
          <button
            className="global-icon-button"
            onClick={() => providers.refetch()}
            aria-label="Обновить статус источников"
          >
            <RotateCcw size={17} />
          </button>
        </div>
        <ErrorBox error={providers.error} />
        <div className="global-providers">
          {providers.data?.map((p) => (
            <article key={p.id}>
              <span
                className={
                  p.available ? "global-demo-badge" : "global-future-badge"
                }
              >
                {p.available ? "DEMO · ДОСТУПЕН" : "НЕ ПОДКЛЮЧЁН"}
              </span>
              <h3>{p.name}</h3>
              <p>{p.requirements}</p>
              <small>{p.products.join(" · ")}</small>
              {p.url && (
                <a href={p.url} target="_blank" rel="noreferrer">
                  Документация источника ↗
                </a>
              )}
            </article>
          ))}
        </div>
      </section>
      <section className="global-roadmap">
        <div>
          <span className="global-overline">СЛЕДУЮЩИЙ ГОРИЗОНТ</span>
          <h2>Масштабирование наблюдений</h2>
          <p>Возможности следующих этапов, пока не реализованы.</p>
        </div>
        <ol>
          <li>
            <strong>01</strong>
            <span>
              Спутниковые композиты
              <small>Sentinel-2, облачные маски и контроль качества</small>
            </span>
          </li>
          <li>
            <strong>02</strong>
            <span>
              Сравнение и мониторинг
              <small>Полигоны, площадь и многолетняя динамика</small>
            </span>
          </li>
          <li>
            <strong>03</strong>
            <span>
              Прогноз изменений
              <small>Региональная калибровка и проверка полевыми данными</small>
            </span>
          </li>
        </ol>
      </section>
      {user.role === "superadmin" && (
        <details className="global-panel global-model-settings">
          <summary>Настройки концептуальной модели GEHI</summary>
          <ErrorBox error={settings.error} />
          {settings.data && (
            <WeightEditor
              key={settings.data.revision}
              settings={settings.data}
            />
          )}
        </details>
      )}
      <footer className="global-footer">
        <span>GAIA GLOBAL / PROTOTYPE 0.1</span>
        <span>Наблюдать ответственно. Восстанавливать обоснованно.</span>
      </footer>
    </>
  );
}
function ScanPlaceholder() {
  return (
    <div className="global-empty-symbol" aria-hidden="true">
      <Globe2 size={52} strokeWidth={1} />
    </div>
  );
}
