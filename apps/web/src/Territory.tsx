import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useOutletContext, useParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  CloudRain,
  Droplets,
  Gauge,
  History,
  Pause,
  Play,
  RotateCcw,
  Square,
  StepForward,
  Sun,
  Thermometer,
} from "lucide-react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, client, dateTime, endpoint, format } from "./api";
import { Empty, ErrorBox, Field, Loading } from "./pages";
import { TerritoryMap } from "./Map";
import { registerGaiaTools } from "./webmcp";
import {
  categories,
  scenarios,
  sources,
  type Alert,
  type Dashboard,
  type IrrigationEvent,
  type Observation,
  type Reading,
  type Report,
  type Rule,
  type Satellite,
  type Weather,
} from "./types";

type TerritoryContext = {
  dashboard: Dashboard;
  refresh: () => Promise<unknown>;
};
const tabs = [
  ["", "Обзор"],
  ["map", "Карта"],
  ["zones", "Зоны"],
  ["plants", "Растения"],
  ["devices", "Устройства"],
  ["metrics", "Показатели"],
  ["simulation", "Симуляция"],
  ["irrigation", "Полив"],
  ["observations", "Наблюдения"],
  ["alerts", "Предупреждения"],
  ["reports", "Отчёты"],
  ["settings", "Настройки"],
];

export function TerritoryLayout() {
  const { tid = "" } = useParams();
  const query = useQuery({
    queryKey: ["dashboard", tid],
    queryFn: () => api<Dashboard>(endpoint(tid, "dashboard")),
    refetchInterval: 2_000,
  });
  useEffect(() => registerGaiaTools(tid), [tid]);
  if (query.isPending) return <Loading />;
  if (!query.data)
    return (
      <ErrorBox error={query.error ?? new Error("Территория не найдена")} />
    );
  const dashboard = query.data;
  return (
    <>
      <div className="territory-heading">
        <div>
          <span className="eyebrow">
            ТЕРРИТОРИЯ /{" "}
            {dashboard.simulation.status === "running"
              ? "НАБЛЮДЕНИЕ ИДЁТ"
              : "НАБЛЮДЕНИЕ ОСТАНОВЛЕНО"}
          </span>
          <h1>{dashboard.territory.name}</h1>
        </div>
        <div className={`health health-${dashboard.status}`}>
          <span className="health-dot" />
          {dashboard.status === "normal"
            ? "Всё спокойно"
            : dashboard.status === "critical"
              ? "Требуется внимание"
              : "Есть предупреждения"}
        </div>
        <span className="simulation-badge">
          SIMULATED · Обзор, полив и отчёты показывают симуляцию. REAL-данные —
          в устройствах и растениях.
        </span>
      </div>
      <nav className="tabs" aria-label="Разделы территории">
        {tabs.map(([path, label]) => (
          <NavLink key={label} to={path} end={path === ""}>
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet
        key={tid}
        context={
          {
            dashboard,
            refresh: () => query.refetch(),
          } satisfies TerritoryContext
        }
      />
    </>
  );
}

function useTerritory() {
  return useOutletContext<TerritoryContext>();
}

function Source({ value }: { value?: string }) {
  return (
    <small className="source">
      Источник: {sources[value ?? ""] ?? value ?? "нет данных"}
    </small>
  );
}

function Metric({
  icon,
  label,
  value,
  unit,
  source,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit?: string;
  source?: string;
}) {
  return (
    <article className="metric">
      <div className="metric-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <strong>
          {value}
          {unit && <small>{unit}</small>}
        </strong>
        {source && <Source value={source} />}
      </div>
    </article>
  );
}

export function Overview() {
  const { dashboard: d } = useTerritory();
  const { tid = "" } = useParams();
  const weather = useQuery({
    queryKey: ["weather", tid],
    queryFn: () => api<Weather>(endpoint(tid, "weather")),
    staleTime: 15 * 60_000,
  });
  const r = d.reading;
  return (
    <div className="stack">
      {d.reasons.length > 0 && (
        <div className={`status-strip ${d.status}`}>
          <AlertTriangle />
          <div>
            <b>
              {d.status === "critical"
                ? "Участку нужна помощь"
                : "Обратите внимание"}
            </b>
            <p>{d.reasons[0]}</p>
          </div>
        </div>
      )}
      <section className="metrics-grid">
        <Metric
          icon={<Thermometer />}
          label="Температура воздуха"
          value={format(r?.air_temperature_c)}
          unit=" °C"
          source={r?.source}
        />
        <Metric
          icon={<Droplets />}
          label="Влажность воздуха"
          value={format(r?.air_humidity_pct)}
          unit="%"
          source={r?.source}
        />
        <Metric
          icon={<Gauge />}
          label="Влажность почвы"
          value={format(r?.soil_moisture_pct)}
          unit="%"
          source={r?.source}
        />
        <Metric
          icon={<Sun />}
          label="Освещённость"
          value={format(r?.light_lux, 0)}
          unit=" лк"
          source={r?.source}
        />
        <Metric
          icon={<CloudRain />}
          label="Вероятность дождя, 6 ч"
          value={format(weather.data?.data?.next_6h_probability)}
          unit="%"
          source="weather"
        />
        <Metric
          icon={<Activity />}
          label="Виртуальный насос"
          value={d.zone.pump_on ? "Работает" : "Выключен"}
          source="simulated"
        />
        <Metric
          icon={<AlertTriangle />}
          label="Активные предупреждения"
          value={String(d.alerts.length)}
        />
        <Metric
          icon={<Droplets />}
          label="Расход воды сегодня"
          value={format(d.zone.daily_water_l, 2)}
          unit=" л"
          source="simulated"
        />
      </section>
      <section className="overview-grid">
        <div className="panel progress-panel">
          <span className="eyebrow">ЗАПАС ВОДЫ</span>
          <div
            className="ring"
            style={
              {
                "--amount": `${d.simulation.reservoir_l}%`,
              } as React.CSSProperties
            }
          >
            <strong>{format(d.simulation.reservoir_l, 1)}</strong>
            <small>литров</small>
          </div>
          <p>Сегодня использовано {format(d.zone.daily_water_l, 2)} л</p>
        </div>
        <div className="panel">
          <div className="panel-title">
            <div>
              <span className="eyebrow">ПОСЛЕДНИЙ СИГНАЛ</span>
              <h2>
                {r
                  ? dateTime(r.timestamp, d.territory.timezone)
                  : "Показаний пока нет"}
              </h2>
            </div>
            <span className={`quality ${r?.quality ?? "invalid"}`}>
              {r?.quality === "valid" ? "валидно" : "нет данных"}
            </span>
          </div>
          <p>
            {r
              ? `Данные поступили через единый контракт телеметрии. Текущий сценарий: ${scenarios[d.simulation.scenario]}.`
              : "Запустите симуляцию или выполните один шаг."}
          </p>
          <Source value={r?.source} />
        </div>
        <div className="panel">
          <div className="panel-title">
            <div>
              <span className="eyebrow">ПОГОДА</span>
              <h2>
                {weather.data?.status === "available"
                  ? "Open-Meteo на связи"
                  : weather.data?.status === "stale"
                    ? "Последние сохранённые данные"
                    : "Данные недоступны"}
              </h2>
            </div>
            <CloudRain />
          </div>
          {weather.data?.data ? (
            <p>
              {format(weather.data.data.current.temperature_2m)} °C · влажность{" "}
              {format(weather.data.data.current.relative_humidity_2m)}% · ветер{" "}
              {format(weather.data.data.current.wind_speed_10m)} км/ч
            </p>
          ) : (
            <p>{weather.data?.error ?? "Получаем прогноз…"}</p>
          )}
          <small>
            {weather.data?.fetched_at
              ? `Обновлено ${dateTime(weather.data.fetched_at, d.territory.timezone)}`
              : "Последнего успешного обновления нет"}
          </small>
        </div>
      </section>
      <MiniChart />
    </div>
  );
}

function MiniChart() {
  const { dashboard } = useTerritory();
  const { tid = "" } = useParams();
  const readings = useQuery({
    queryKey: ["readings", tid, "mini"],
    queryFn: () => api<Reading[]>(endpoint(tid, "sensors/readings")),
    refetchInterval: 5000,
  });
  const data = (readings.data ?? []).slice(-60).map((r) => ({
    time: dateTime(r.timestamp, dashboard.territory.timezone),
    soil: r.soil_moisture_pct,
    temp: r.air_temperature_c,
  }));
  return (
    <section className="panel chart-panel">
      <div className="panel-title">
        <div>
          <span className="eyebrow">ПОСЛЕДНИЕ 60 ПОКАЗАНИЙ</span>
          <h2>Как меняется участок</h2>
        </div>
        <Source value="simulated" />
      </div>
      {data.length ? (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d8dfd2" />
            <XAxis dataKey="time" minTickGap={30} />
            <YAxis yAxisId="left" domain={[0, 100]} />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Legend />
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="soil"
              name="Почва, %"
              stroke="#246246"
              dot={false}
              strokeWidth={3}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="temp"
              name="Температура, °C"
              stroke="#d98628"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <Empty title="График появится после запуска симуляции" />
      )}
    </section>
  );
}

export function Metrics() {
  const { dashboard } = useTerritory();
  const { tid = "" } = useParams();
  const [range, setRange] = useState("24h");
  const anchor = dashboard.reading?.timestamp ?? dashboard.simulation.clock;
  const start = new Date(
    new Date(anchor).getTime() -
      (range === "24h" ? 1 : range === "7d" ? 7 : 30) * 86400000,
  ).toISOString();
  const q = useQuery({
    queryKey: ["readings", tid, range],
    queryFn: () =>
      api<Reading[]>(
        `${endpoint(tid, "sensors/readings")}?start=${encodeURIComponent(start)}`,
      ),
    refetchInterval: 5000,
  });
  const data = (q.data ?? []).map((r) => ({
    time: dateTime(r.timestamp, dashboard.territory.timezone),
    soil: r.soil_moisture_pct,
    temp: r.air_temperature_c,
    humidity: r.air_humidity_pct,
    light: r.light_lux,
  }));
  return (
    <section className="panel chart-panel">
      <div className="panel-title">
        <div>
          <span className="eyebrow">ДИНАМИКА</span>
          <h2>Показатели территории</h2>
        </div>
        <div className="segmented">
          {[
            ["24h", "24 часа"],
            ["7d", "7 дней"],
            ["30d", "30 дней"],
          ].map(([v, l]) => (
            <button
              className={range === v ? "active" : ""}
              onClick={() => setRange(v)}
              key={v}
            >
              {l}
            </button>
          ))}
        </div>
      </div>
      <ErrorBox error={q.error} />
      {data.length ? (
        <ResponsiveContainer width="100%" height={460}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" hide />
            <YAxis yAxisId="pct" domain={[0, 100]} />
            <YAxis yAxisId="temp" orientation="right" />
            <Tooltip />
            <Legend />
            <Line
              yAxisId="pct"
              dataKey="soil"
              name="Влажность почвы, %"
              stroke="#246246"
              dot={false}
              strokeWidth={3}
            />
            <Line
              yAxisId="pct"
              dataKey="humidity"
              name="Влажность воздуха, %"
              stroke="#438f9c"
              dot={false}
            />
            <Line
              yAxisId="temp"
              dataKey="temp"
              name="Температура, °C"
              stroke="#d98628"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <Empty title="В выбранном периоде нет показаний" />
      )}
      <Source value={q.data?.at(-1)?.source} />
    </section>
  );
}

export function Simulation() {
  const { dashboard: d, refresh } = useTerritory();
  const { tid = "" } = useParams();
  const [scenario, setScenario] = useState(d.simulation.scenario);
  const [speed, setSpeed] = useState(d.simulation.speed);
  const [seed, setSeed] = useState(d.simulation.seed);
  const mutation = useMutation({
    mutationFn: (action: string) =>
      api(endpoint(tid, "simulations"), "POST", {
        action,
        scenario,
        speed,
        seed,
      }),
    onSuccess: async () => {
      await refresh();
      await client.invalidateQueries({ queryKey: ["readings", tid] });
    },
  });
  const run = (action: string) => {
    if (
      action === "reset" &&
      !confirm(
        "Сбросить состояние симуляции? История и лимиты безопасности сохранятся.",
      )
    )
      return;
    mutation.mutate(action);
  };
  return (
    <div className="two-col">
      <section className="panel">
        <span className="eyebrow">УПРАВЛЕНИЕ ВРЕМЕНЕМ</span>
        <h2>Симуляция участка</h2>
        <p>
          Одна реальная секунда равна выбранному количеству виртуальных секунд.
          Все показания проходят через тот же сервис, что и данные Raspberry Pi.
        </p>
        <div className="form-grid">
          <Field label="Сценарий">
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
            >
              {Object.entries(scenarios).map(([v, l]) => (
                <option value={v} key={v}>
                  {l}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Скорость">
            <select
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
            >
              <option value={1}>×1</option>
              <option value={10}>×10</option>
              <option value={60}>×60</option>
            </select>
          </Field>
          <Field label="Random seed">
            <input
              type="number"
              min="0"
              max="2147483647"
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
            />
          </Field>
        </div>
        <div className="button-row">
          <button
            onClick={() =>
              run(d.simulation.status === "paused" ? "resume" : "start")
            }
          >
            <Play />
            Запустить
          </button>
          <button className="secondary" onClick={() => run("pause")}>
            <Pause />
            Пауза
          </button>
          <button className="secondary" onClick={() => run("stop")}>
            <Square />
            Стоп
          </button>
          <button className="secondary" onClick={() => run("tick")}>
            <StepForward />
            Один шаг
          </button>
          <button className="ghost" onClick={() => run("reset")}>
            <RotateCcw />
            Сброс
          </button>
        </div>
        <ErrorBox error={mutation.error} />
      </section>
      <section className="panel state-card">
        <span className="eyebrow">СОСТОЯНИЕ</span>
        <h2>
          {d.simulation.status === "running"
            ? "Симуляция идёт"
            : d.simulation.status === "paused"
              ? "Симуляция на паузе"
              : "Симуляция остановлена"}
        </h2>
        <dl>
          <div>
            <dt>Сценарий</dt>
            <dd>{scenarios[d.simulation.scenario]}</dd>
          </div>
          <div>
            <dt>Шаг</dt>
            <dd>{d.simulation.tick_index}</dd>
          </div>
          <div>
            <dt>Виртуальное время</dt>
            <dd>{dateTime(d.simulation.clock, d.territory.timezone)}</dd>
          </div>
          <div>
            <dt>Seed</dt>
            <dd>{d.simulation.seed}</dd>
          </div>
        </dl>
        <div className="notice">
          Для приёмочного пути выберите «Засуха», ×60, сохраните автоматический
          полив и запустите симуляцию.
        </div>
      </section>
    </div>
  );
}

export function Irrigation() {
  const { dashboard: d, refresh } = useTerritory();
  const { tid = "" } = useParams();
  const [rule, setRule] = useState<Rule>({
    mode: d.rule.mode,
    trigger_pct: d.rule.trigger_pct,
    target_pct: d.rule.target_pct,
    max_duration_s: d.rule.max_duration_s,
    cooldown_s: d.rule.cooldown_s,
    daily_limit_l: d.rule.daily_limit_l,
    min_reservoir_l: d.rule.min_reservoir_l,
    block_rain: d.rule.block_rain,
    rain_threshold_pct: d.rule.rain_threshold_pct,
  });
  const [duration, setDuration] = useState(300);
  const save = useMutation({
    mutationFn: () => api<Rule>(endpoint(tid, "irrigation/rules"), "PUT", rule),
    onSuccess: async () => {
      await refresh();
      await client.invalidateQueries({ queryKey: ["events", tid] });
    },
  });
  const action = useMutation({
    mutationFn: (value: string) =>
      api<{ message: string }>(endpoint(tid, "irrigation/actions"), "POST", {
        action: value,
        duration_s: duration,
      }),
    onSuccess: async () => {
      await refresh();
      await client.invalidateQueries({ queryKey: ["events", tid] });
    },
  });
  const update = <K extends keyof Rule>(key: K, value: Rule[K]) =>
    setRule({ ...rule, [key]: value });
  return (
    <div className="stack">
      <div className={`pump-banner ${d.zone.pump_on ? "on" : ""}`}>
        <div className="pump-symbol">
          <Droplets />
        </div>
        <div>
          <span className="eyebrow">ВИРТУАЛЬНЫЙ НАСОС</span>
          <h2>{d.zone.pump_on ? "Полив идёт" : "Насос выключен"}</h2>
          <p>
            Запас {format(d.simulation.reservoir_l, 2)} л · сегодня{" "}
            {format(d.zone.daily_water_l, 2)} л
          </p>
        </div>
        <button
          className="danger"
          onClick={() => {
            if (confirm("Включить аварийную блокировку виртуального насоса?"))
              action.mutate("emergency");
          }}
        >
          Аварийный стоп
        </button>
      </div>
      <div className="two-col">
        <form
          className="panel"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <span className="eyebrow">ПРАВИЛА БЕЗОПАСНОСТИ</span>
          <h2>Автоматический полив</h2>
          <Field label="Режим">
            <select
              value={rule.mode}
              onChange={(e) => update("mode", e.target.value as Rule["mode"])}
            >
              <option value="off">Выключен</option>
              <option value="manual">Ручной</option>
              <option value="automatic">Автоматический</option>
            </select>
          </Field>
          <div className="form-grid">
            <Field label="Порог влажности, %">
              <input
                type="number"
                min="1"
                max="90"
                value={rule.trigger_pct}
                onChange={(e) => update("trigger_pct", Number(e.target.value))}
              />
            </Field>
            <Field label="Цель влажности, %">
              <input
                type="number"
                min="2"
                max="95"
                value={rule.target_pct}
                onChange={(e) => update("target_pct", Number(e.target.value))}
              />
            </Field>
            <Field label="Макс. длительность, с">
              <input
                type="number"
                min="10"
                max="7200"
                value={rule.max_duration_s}
                onChange={(e) =>
                  update("max_duration_s", Number(e.target.value))
                }
              />
            </Field>
            <Field label="Cooldown, с">
              <input
                type="number"
                min="0"
                max="86400"
                value={rule.cooldown_s}
                onChange={(e) => update("cooldown_s", Number(e.target.value))}
              />
            </Field>
            <Field label="Дневной лимит, л">
              <input
                type="number"
                min="0.1"
                max="500"
                step="0.1"
                value={rule.daily_limit_l}
                onChange={(e) =>
                  update("daily_limit_l", Number(e.target.value))
                }
              />
            </Field>
            <Field label="Минимум в резервуаре, л">
              <input
                type="number"
                min="1"
                max="100"
                step="0.1"
                value={rule.min_reservoir_l}
                onChange={(e) =>
                  update("min_reservoir_l", Number(e.target.value))
                }
              />
            </Field>
          </div>
          <label className="check">
            <input
              type="checkbox"
              checked={rule.block_rain}
              onChange={(e) => update("block_rain", e.target.checked)}
            />
            <span>Не поливать, если ожидается дождь</span>
          </label>
          {rule.block_rain && (
            <Field label="Порог вероятности дождя, %">
              <input
                type="number"
                min="0"
                max="100"
                value={rule.rain_threshold_pct}
                onChange={(e) =>
                  update("rain_threshold_pct", Number(e.target.value))
                }
              />
            </Field>
          )}
          <button disabled={save.isPending}>Сохранить правила</button>
          <ErrorBox error={save.error} />
        </form>
        <section className="panel">
          <span className="eyebrow">РУЧНОЕ УПРАВЛЕНИЕ</span>
          <h2>Команды симуляции</h2>
          <p>
            Ручной запуск доступен только в ручном режиме и при валидном свежем
            показании.
          </p>
          <Field label="Длительность, с">
            <input
              type="number"
              min="10"
              max="7200"
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
            />
          </Field>
          <div className="button-row">
            <button
              onClick={() => action.mutate("start")}
              disabled={d.zone.pump_on}
            >
              Запустить насос
            </button>
            <button className="secondary" onClick={() => action.mutate("stop")}>
              Остановить
            </button>
            {d.zone.emergency && (
              <button
                className="secondary"
                onClick={() => action.mutate("clear_emergency")}
              >
                Снять аварийную блокировку
              </button>
            )}
          </div>
          {action.data && <p className="notice">{action.data.message}</p>}
          <ErrorBox error={action.error} />
          <p className="warning-copy">
            <AlertTriangle /> Команды управляют только симуляцией. Физическое
            реле не подключено.
          </p>
        </section>
      </div>
      <EventHistory />
    </div>
  );
}

function EventHistory() {
  const { dashboard } = useTerritory();
  const { tid = "" } = useParams();
  const q = useQuery({
    queryKey: ["events", tid],
    queryFn: () => api<IrrigationEvent[]>(endpoint(tid, "irrigation/events")),
    refetchInterval: 3000,
  });
  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <span className="eyebrow">ОБЪЯСНИМАЯ ИСТОРИЯ</span>
          <h2>Решения по поливу</h2>
        </div>
        <History />
      </div>
      {q.data?.length ? (
        <div className="timeline">
          {q.data.map((e) => (
            <article key={e.id}>
              <span className={`timeline-dot ${e.action}`} />
              <div>
                <div>
                  <b>
                    {e.action === "start"
                      ? "Запуск"
                      : e.action === "stop"
                        ? "Остановка"
                        : e.action === "denied"
                          ? "Запуск отклонён"
                          : e.action === "configure"
                            ? "Настройка"
                            : "Аварийная команда"}
                  </b>
                  <time>
                    {dateTime(e.timestamp, dashboard.territory.timezone)}
                  </time>
                </div>
                <p>{e.reason}</p>
                {e.action === "stop" && (
                  <small>
                    {format(e.duration_s, 0)} с ·{" "}
                    {format(e.estimated_water_l, 2)} л
                  </small>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty title="История решений пока пуста" />
      )}
    </section>
  );
}

export function MapPage() {
  const { dashboard } = useTerritory();
  const { tid = "" } = useParams();
  const [satelliteOn, setSatelliteOn] = useState(false);
  const observations = useQuery({
    queryKey: ["observations", tid],
    queryFn: () => api<Observation[]>(endpoint(tid, "observations")),
  });
  const satellite = useQuery({
    queryKey: ["satellite", tid],
    queryFn: () => api<Satellite>(endpoint(tid, "satellite")),
    enabled: satelliteOn,
  });
  return (
    <section className="panel map-panel">
      <div className="panel-title">
        <div>
          <span className="eyebrow">КАРТА ТЕРРИТОРИИ</span>
          <h2>{dashboard.territory.name}</h2>
        </div>
        <label className="check">
          <input
            type="checkbox"
            checked={satelliteOn}
            onChange={(e) => setSatelliteOn(e.target.checked)}
          />
          <span>Обзорный спутниковый слой</span>
        </label>
      </div>
      <TerritoryMap
        latitude={dashboard.territory.latitude}
        longitude={dashboard.territory.longitude}
        polygon={dashboard.territory.polygon}
        observations={observations.data}
        satellite={satellite.data}
      />
      {satellite.data && (
        <p className="notice">
          {satellite.data.explanation} Снимок: {satellite.data.date}.
        </p>
      )}
      <p className="muted">
        Маркеры наблюдений видны только владельцу территории. Базовая карта:
        OpenStreetMap.
      </p>
    </section>
  );
}

export function Observations() {
  const { dashboard } = useTerritory();
  const { tid = "" } = useParams();
  const [category, setCategory] = useState("vegetation");
  const [severity, setSeverity] = useState("info");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const q = useQuery({
    queryKey: ["observations", tid],
    queryFn: () => api<Observation[]>(endpoint(tid, "observations")),
  });
  const create = useMutation({
    mutationFn: async () => {
      const observation = await api<Observation>(
        endpoint(tid, "observations"),
        "POST",
        {
          category,
          severity,
          text,
          timestamp: new Date().toISOString(),
          latitude: dashboard.territory.latitude,
          longitude: dashboard.territory.longitude,
        },
      );
      if (file) {
        const form = new FormData();
        form.append("file", file);
        return api<Observation>(
          `${endpoint(tid, "observations")}/${observation.id}/photo`,
          "POST",
          form,
        );
      }
      return observation;
    },
    onSuccess: async () => {
      setText("");
      setFile(null);
      await client.invalidateQueries({ queryKey: ["observations", tid] });
    },
  });
  return (
    <div className="two-col">
      <form
        className="panel"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <span className="eyebrow">РУЧНОЕ НАБЛЮДЕНИЕ</span>
        <h2>Что вы заметили?</h2>
        <div className="form-grid">
          <Field label="Категория">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {Object.entries(categories).map(([v, l]) => (
                <option value={v} key={v}>
                  {l}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Важность">
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              <option value="info">Информация</option>
              <option value="warning">Предупреждение</option>
              <option value="critical">Критично</option>
            </select>
          </Field>
        </div>
        <Field label="Описание">
          <textarea
            required
            maxLength={5000}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Например: молодые листья начали скручиваться"
          />
        </Field>
        <Field label="Фото — JPEG, PNG или WebP до 5 МБ (необязательно)">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </Field>
        <p className="muted">
          Наблюдение будет отмечено в центре территории. API также принимает
          координаты рядом с участком.
        </p>
        <button disabled={create.isPending}>
          {create.isPending ? "Сохраняем…" : "Добавить наблюдение"}
        </button>
        <ErrorBox error={create.error} />
      </form>
      <section className="panel">
        <span className="eyebrow">ЖУРНАЛ</span>
        <h2>Ваши заметки</h2>
        {q.data?.length ? (
          <div className="observation-list">
            {q.data.map((o) => (
              <article key={o.id}>
                <div>
                  <span className={`severity ${o.severity}`}>
                    {o.severity === "critical"
                      ? "Критично"
                      : o.severity === "warning"
                        ? "Важно"
                        : "Информация"}
                  </span>
                  <small>
                    {categories[o.category]} ·{" "}
                    {dateTime(o.timestamp, dashboard.territory.timezone)}
                  </small>
                </div>
                <p>{o.text}</p>
                {o.photo_path && (
                  <img
                    src={`/api/v1${endpoint(tid, `observations/${o.id}/photo`)}`}
                    alt="Фото к наблюдению"
                    loading="lazy"
                  />
                )}
              </article>
            ))}
          </div>
        ) : (
          <Empty title="Наблюдений пока нет" />
        )}
      </section>
    </div>
  );
}

export function AlertsPage() {
  const { dashboard } = useTerritory();
  const { tid = "" } = useParams();
  const [showResolved, setShowResolved] = useState(false);
  const q = useQuery({
    queryKey: ["alerts", tid],
    queryFn: () => api<Alert[]>(endpoint(tid, "alerts")),
    refetchInterval: 3000,
  });
  const rows = (q.data ?? []).filter(
    (a) => showResolved || a.status === "active",
  );
  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <span className="eyebrow">ПРАВИЛА, А НЕ ЧЁРНЫЙ ЯЩИК</span>
          <h2>Предупреждения</h2>
        </div>
        <label className="check">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
          />
          <span>Показать завершённые</span>
        </label>
      </div>
      {q.isPending ? (
        <Loading />
      ) : q.error ? (
        <ErrorBox error={q.error} />
      ) : rows.length ? (
        <div className="alert-list">
          {rows.map((a) => (
            <article
              className={`alert-item ${a.severity} ${a.status}`}
              key={a.id}
            >
              <AlertTriangle />
              <div>
                <div>
                  <h3>{a.title}</h3>
                  <time>
                    {dateTime(a.created_at, dashboard.territory.timezone)}
                  </time>
                </div>
                <p>{a.explanation}</p>
                <small>
                  <b>Рекомендация:</b> {a.recommendation}
                </small>
                {a.status === "resolved" && (
                  <span className="resolved-label">
                    Завершено{" "}
                    {a.resolved_at &&
                      dateTime(a.resolved_at, dashboard.territory.timezone)}
                  </span>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty title="Активных предупреждений нет">
          <p>Система продолжает проверять почву, погоду, резервуар и насос.</p>
        </Empty>
      )}
    </section>
  );
}

export function Reports() {
  const { dashboard } = useTerritory();
  const { tid = "" } = useParams();
  const [selected, setSelected] = useState<Report | null>(null);
  const q = useQuery({
    queryKey: ["reports", tid],
    queryFn: () => api<Report[]>(endpoint(tid, "reports")),
  });
  const create = useMutation({
    mutationFn: () => api<Report>(endpoint(tid, "reports"), "POST"),
    onSuccess: async (r) => {
      setSelected(r);
      await client.invalidateQueries({ queryKey: ["reports", tid] });
    },
  });
  const report = selected ?? q.data?.[0];
  return (
    <div className="two-col reports">
      <section className="panel">
        <div className="panel-title">
          <div>
            <span className="eyebrow">СОХРАНЁННЫЕ ОТЧЁТЫ</span>
            <h2>Ежедневные итоги</h2>
          </div>
          <button onClick={() => create.mutate()} disabled={create.isPending}>
            Сформировать за сегодня
          </button>
        </div>
        <ErrorBox error={create.error} />
        {q.data?.length ? (
          <div className="report-list">
            {q.data.map((r) => (
              <button
                className={report?.id === r.id ? "active" : ""}
                onClick={() => setSelected(r)}
                key={r.id}
              >
                <b>{r.data.date}</b>
                <span>
                  {r.data.reading_count} показаний · {r.data.alert_count}{" "}
                  предупреждений
                </span>
              </button>
            ))}
          </div>
        ) : (
          <Empty title="Отчётов пока нет" />
        )}
      </section>
      <section className="panel report-paper">
        {report ? (
          <>
            <span className="eyebrow">ОТЧЁТ / {report.data.date}</span>
            <h2>{dashboard.territory.name}</h2>
            <p>{report.data.summary}</p>
            <div className="report-numbers">
              <div>
                <strong>{report.data.irrigation_count}</strong>
                <span>запусков полива</span>
              </div>
              <div>
                <strong>{format(report.data.water_l, 2)} л</strong>
                <span>израсходовано</span>
              </div>
              <div>
                <strong>{report.data.alert_count}</strong>
                <span>предупреждений</span>
              </div>
            </div>
            <h3>Показатели</h3>
            <div className="stats-table">
              {Object.entries(report.data.stats).map(([key, value]) => (
                <div key={key}>
                  <span>
                    {key === "soil_moisture_pct"
                      ? "Почва"
                      : key === "air_temperature_c"
                        ? "Температура"
                        : key === "air_humidity_pct"
                          ? "Влажность воздуха"
                          : "Свет"}
                  </span>
                  <b>
                    {value
                      ? `${format(value.min)} / ${format(value.mean)} / ${format(value.max)}`
                      : "нет данных"}
                  </b>
                </div>
              ))}
            </div>
            <small>
              Минимум / среднее / максимум. Источники:{" "}
              {report.data.sources.map((s) => sources[s] ?? s).join(", ") ||
                "нет"}
              .
            </small>
            <h3>Рекомендации</h3>
            <ul>
              {report.data.recommendations.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
            <p className="muted">{report.data.water_accounting}</p>
          </>
        ) : (
          <Empty title="Выберите или сформируйте отчёт" />
        )}
      </section>
    </div>
  );
}
