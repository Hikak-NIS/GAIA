import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api, client, dateTime } from "../api";
import { ErrorBox } from "../pages";
import type { Area, GlobalMarker } from "../global/types";
import { useGlobalUser } from "../global/GlobalLayout";
import { EarthMap } from "./EarthMap";
import { Chart, Metrics, Sources } from "./Panels";
import { Assistant, binaryRequest } from "./Assistant";
import { ModelPanel } from "./ModelPanel";
import type { EarthAnalysis, Source } from "./types";

export default function ExplorePage({ ocean = false }: { ocean?: boolean }) {
  const user = useGlobalUser();
  const [params, setParams] = useSearchParams(),
    id = params.get("analysis");
  const [area, setArea] = useState<Area>({
    name: ocean ? "Северная Атлантика" : "Приаралье",
    latitude: ocean ? 40 : 45.2,
    longitude: ocean ? -40 : 60.3,
    radius_km: 20,
  });
  const [start, setStart] = useState(() =>
    new Date(Date.now() - 31 * 86400000).toISOString().slice(0, 10),
  );
  const [end, setEnd] = useState(() =>
    new Date(Date.now() - 86400000).toISOString().slice(0, 10),
  );
  const [satellite, setSatellite] = useState(true),
    [gee, setGee] = useState(false),
    [title, setTitle] = useState(""),
    [note, setNote] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [imageSelection, setImageSelection] = useState("");
  useEffect(
    () => () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    },
    [imageUrl],
  );
  const body = { area, start, end, ocean, satellite, earth_engine: gee };
  const selectionKey = JSON.stringify({ area, start, end });
  const history = useQuery({
    queryKey: ["earth-history"],
    queryFn: () =>
      api<{ id: string; name: string; created_at: string }[]>(
        "/global/analyses",
      ),
  });
  const selected = useQuery({
    queryKey: ["earth-analysis", id],
    queryFn: () => api<EarthAnalysis>(`/global/analyses/${id}`),
    enabled: !!id,
  });
  const markers = useQuery({
    queryKey: ["global-markers"],
    queryFn: () => api<GlobalMarker[]>("/global/markers"),
  });
  const run = useMutation({
    mutationFn: () => api<EarthAnalysis>("/earth/analyses", "POST", body),
    onSuccess: (data) => {
      client.setQueryData(["earth-analysis", data.id], data);
      setParams({ analysis: data.id });
      client.invalidateQueries({ queryKey: ["earth-history"] });
      setImageUrl("");
    },
  });
  const preview = useMutation({
    mutationFn: async () => ({
      blob: await binaryRequest("/earth/satellite-image", body),
      selection: selectionKey,
    }),
    onSuccess: ({ blob, selection }) => {
      setImageUrl(URL.createObjectURL(blob));
      setImageSelection(selection);
    },
  });
  const add = useMutation({
    mutationFn: () =>
      api("/global/markers", "POST", {
        title,
        note,
        category: ocean ? "water" : "other",
        latitude: area.latitude,
        longitude: area.longitude,
      }),
    onSuccess: () => {
      setTitle("");
      setNote("");
      client.invalidateQueries({ queryKey: ["global-markers"] });
    },
  });
  const remove = useMutation({
    mutationFn: (mid: string) => api(`/global/markers/${mid}`, "DELETE"),
    onSuccess: () => client.invalidateQueries({ queryKey: ["global-markers"] }),
  });
  const result = selected.data;
  const changed =
    !!result &&
    (JSON.stringify(result.area) !== JSON.stringify(area) ||
      result.period.start !== start ||
      result.period.end !== end ||
      result.ocean !== ocean);
  function restore(data: EarthAnalysis) {
    setArea(data.area);
    setStart(data.period.start);
    setEnd(data.period.end);
  }
  function exportResult() {
    if (!result) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `GAIA-observations-${result.id}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <>
      <div className="global-page-heading">
        <span className="global-overline">
          {ocean
            ? "GAIA OCEAN / ВОДНЫЕ ЭКОСИСТЕМЫ"
            : "GAIA GLOBAL / АНАЛИЗ ТЕРРИТОРИИ"}
        </span>
        <h1>
          {ocean
            ? "Вода связывает всю планету."
            : "От наблюдения — к пониманию."}
        </h1>
        <p>
          {ocean
            ? "Морские модели, спектральные индикаторы качества воды и история водной поверхности."
            : "Выберите территорию и период. Сопоставьте спутниковые наблюдения, почву и атмосферу."}
        </p>
      </div>
      <EarthMap
        area={area}
        onSelect={(latitude, longitude) =>
          setArea({ ...area, latitude, longitude })
        }
        ocean={ocean}
        points={markers.data?.map((m) => ({
          ...m,
          name: m.title,
          detail: m.note,
        }))}
      />
      <form
        className="global-panel earth-selection"
        onSubmit={(e) => {
          e.preventDefault();
          run.mutate();
        }}
      >
        <div className="earth-form-grid">
          <label>
            Название территории
            <input
              required
              maxLength={120}
              value={area.name}
              onChange={(e) => setArea({ ...area, name: e.target.value })}
            />
          </label>
          <label>
            Широта
            <input
              type="number"
              step="any"
              min={-85}
              max={85}
              required
              value={area.latitude}
              onChange={(e) =>
                setArea({ ...area, latitude: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Долгота
            <input
              type="number"
              step="any"
              min={-180}
              max={180}
              required
              value={area.longitude}
              onChange={(e) =>
                setArea({ ...area, longitude: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Радиус, км
            <input
              type="number"
              min={1}
              max={50}
              step="any"
              required
              value={area.radius_km}
              onChange={(e) =>
                setArea({ ...area, radius_km: Number(e.target.value) })
              }
            />
          </label>
          <label>
            Начало периода
            <input
              type="date"
              required
              value={start}
              max={end}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label>
            Конец периода
            <input
              type="date"
              required
              value={end}
              min={start}
              max={new Date().toISOString().slice(0, 10)}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
        </div>
        <div className="earth-button-row">
          <label className="global-toggle">
            <input
              type="checkbox"
              checked={satellite}
              onChange={(e) => setSatellite(e.target.checked)}
            />
            Индексы Sentinel-2
          </label>
          <label className="global-toggle">
            <input
              type="checkbox"
              checked={gee}
              onChange={(e) => setGee(e.target.checked)}
            />
            Архивный анализ Earth Engine
          </label>
          <button disabled={run.isPending}>
            {run.isPending
              ? "Запрашиваем источники…"
              : "Анализировать территорию"}
          </button>
        </div>
        <p className="global-muted">
          Индексы Sentinel-2 и Earth Engine требуют подключения аккаунтов.
          Каталоги снимков и модели окружающей среды запрашиваются независимо.
        </p>
        <ErrorBox error={run.error} />
      </form>
      <div className="global-result-toolbar">
        <label>
          Сохранённые анализы
          <select
            value={id ?? ""}
            onChange={(e) => {
              setParams(e.target.value ? { analysis: e.target.value } : {});
              setImageUrl("");
            }}
          >
            <option value="">Выберите результат</option>
            {history.data?.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} · {dateTime(a.created_at)}
              </option>
            ))}
          </select>
        </label>
        {result && (
          <button className="global-secondary" onClick={exportResult}>
            Экспорт JSON
          </button>
        )}
      </div>
      <ErrorBox error={history.error || selected.error || markers.error} />
      {result && (
        <>
          <section className="global-panel">
            <span className="global-overline">
              СОХРАНЁННЫЙ РЕЗУЛЬТАТ · {result.ocean ? "OCEAN" : "GLOBAL"}
            </span>
            <h2>{result.area.name}</h2>
            <p>
              {result.area.latitude}°, {result.area.longitude}° ·{" "}
              {result.period.start} — {result.period.end}
            </p>
            {changed && (
              <p className="global-warning">
                Параметры выбора отличаются от результата. Выполните новый
                анализ или{" "}
                <button
                  className="global-secondary"
                  onClick={() => restore(result)}
                >
                  Восстановить параметры результата
                </button>
                .
              </p>
            )}
            <p className="global-muted">{result.coverage_note}</p>
            <Sources sources={result.sources as Record<string, Source>} />
          </section>
          <h2>Наблюдения и показатели</h2>
          {result.metrics.length ? (
            <Metrics metrics={result.metrics} />
          ) : (
            <p>
              Численные источники не вернули данных. Проверьте подключения и
              период; значения не подставляются автоматически.
            </p>
          )}
          <Chart metrics={result.metrics} />
          <section className="global-panel">
            <h2>Оценка состояния</h2>
            <p>{result.assessment.explanation}</p>
          </section>
          <div className="global-recommendations">
            {result.recommendations.map((r) => (
              <article key={r.title} className="global-recommendation">
                <div>
                  <span className="global-priority">{r.priority}</span>
                  <h3>{r.title}</h3>
                  <p>{r.detail}</p>
                  <small>Основание: {r.basis}</small>
                </div>
              </article>
            ))}
          </div>
          <section className="global-panel">
            <div className="global-section-heading">
              <h2>Снимки Sentinel‑2</h2>
              <button
                className="global-secondary"
                disabled={preview.isPending}
                onClick={() => preview.mutate()}
              >
                {preview.isPending
                  ? "Получаем изображение…"
                  : "Получить снимок выбранной области"}
              </button>
            </div>
            <p className="global-muted">
              Кнопка обрабатывает текущие параметры формы через Sentinel Hub.
              Изображение — мозаика наименее облачных сцен за выбранный период;
              значения индексов рассчитываются отдельно.
            </p>
            <ErrorBox error={preview.error} />
            {imageUrl && imageSelection !== selectionKey && (
              <p className="global-warning">
                Параметры области или периода изменились. Получите новый снимок
                для выбранной области.
              </p>
            )}
            {imageUrl && imageSelection === selectionKey && (
              <img
                className="earth-satellite-image"
                src={imageUrl}
                alt="Снимок выбранной области Sentinel-2"
              />
            )}
            <div className="earth-scenes">
              {result.sources.sentinel_catalog?.data?.items?.map((scene) => (
                <article key={scene.id}>
                  {scene.preview && (
                    <img
                      src={scene.preview}
                      alt="Обзор сцены Sentinel-2"
                      loading="lazy"
                    />
                  )}
                  <a href={scene.url} target="_blank" rel="noreferrer">
                    {scene.id}
                  </a>
                  <p>
                    {scene.datetime} · Облачность{" "}
                    {scene.cloud_cover ?? "не указана"}
                    {scene.cloud_cover != null ? "%" : ""}
                  </p>
                </article>
              ))}
            </div>
            {result.sources.sentinel_catalog?.status === "ok" &&
              !result.sources.sentinel_catalog.data?.items?.length && (
                <p>Сцены за этот период не найдены.</p>
              )}
          </section>
        </>
      )}
      {ocean && (
        <section className="global-panel">
          <h2>Что показывают водные индикаторы</h2>
          <div className="earth-topic-grid">
            <article>
              <h3>Мутность</h3>
              <p>
                Красная отражательная способность помогает отслеживать взвесь.
                Перевод в NTU или мг/л требует локальной калибровки и поправок
                на атмосферу, дно и блики.
              </p>
            </article>
            <article>
              <h3>Цветение воды</h3>
              <p>
                NDCI — спектральный индикатор. Карта NASA показывает спутниковый
                продукт хлорофилла-а. Токсичность и конкретный вид водорослей по
                этим значениям не устанавливаются.
              </p>
            </article>
            <article>
              <h3>Площадь водоёмов</h3>
              <p>
                Earth Engine рассчитывает историю площади сезонной и постоянной
                воды из JRC 1.4 за 2012–2021. Это архивный ряд с явно указанными
                годами.
              </p>
            </article>
          </div>
        </section>
      )}
      <ModelPanel ocean={ocean} />
      <section className="global-panel">
        <h2>Полевые заметки на карте</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            add.mutate();
          }}
        >
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
              Заметка
              <input
                maxLength={3000}
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>
          </div>
          <p className="global-muted">
            Будет сохранена выбранная точка: {area.latitude}°, {area.longitude}
            °.
          </p>
          <button disabled={add.isPending}>Сохранить маркер</button>
        </form>
        <ErrorBox error={add.error || remove.error} />
        <div className="global-marker-list">
          {markers.data?.slice(0, 20).map((m) => (
            <div key={m.id}>
              <div>
                <strong>{m.title}</strong>
                <p>{m.note}</p>
              </div>
              {(m.creator_id === user.id || user.role === "superadmin") && (
                <button
                  className="global-secondary"
                  onClick={() => {
                    if (confirm(`Удалить маркер «${m.title}»?`))
                      remove.mutate(m.id);
                  }}
                >
                  Удалить
                </button>
              )}
            </div>
          ))}
        </div>
      </section>
      <Assistant analysisId={result?.id} />
    </>
  );
}
