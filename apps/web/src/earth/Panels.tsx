import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { format } from "../api";
import type { Metric, Source } from "./types";
import { sourceNames } from "./types";

export function Metrics({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="global-metrics earth-metrics">
      {metrics.map((m) => (
        <article className="global-metric" key={m.id}>
          <div className="global-metric-name">
            <h3>{m.label}</h3>
          </div>
          <div className="global-metric-value">
            {format(m.value, 3)}
            <small>{m.unit}</small>
          </div>
          <p className="global-metric-explanation">{m.description}</p>
          {m.quality != null && (
            <small>Доля валидных пикселей: {format(m.quality * 100)}%</small>
          )}
          <footer>
            <span>{m.source}</span>
            <time>
              {m.observed_at?.slice(0, 16).replace("T", " ") ?? "Нет измерения"}
            </time>
            <span>
              {m.kind === "model"
                ? "Расчётная модель"
                : m.kind === "satellite"
                  ? "Спутниковый продукт"
                  : "Наблюдения"}
            </span>
          </footer>
        </article>
      ))}
    </div>
  );
}

export function Chart({ metrics }: { metrics: Metric[] }) {
  const [key, setKey] = useState("");
  const candidates = metrics.filter((m) => m.history?.length);
  const metric = candidates.find((m) => m.id === key) ?? candidates[0];
  if (!metric)
    return <p className="global-muted">Временной ряд пока недоступен.</p>;
  return (
    <section className="global-panel">
      <div className="global-section-heading">
        <h2>Изменения во времени</h2>
        <label>
          Показатель
          <select value={metric.id} onChange={(e) => setKey(e.target.value)}>
            {candidates.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="global-muted">
        {metric.source} · {metric.unit} · {metric.description}
      </p>
      <div
        className="global-chart"
        role="img"
        aria-label={`График: ${metric.label}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={metric.history}>
            <CartesianGrid stroke="#33484b" strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={(v) => String(v).slice(0, 10)}
              minTickGap={70}
              stroke="#a5b9b6"
            />
            <YAxis width={50} domain={["auto", "auto"]} stroke="#a5b9b6" />
            <Tooltip
              contentStyle={{
                background: "#172a2e",
                border: "1px solid #59706d",
                color: "#fff",
              }}
            />
            <Area
              isAnimationActive={false}
              type="monotone"
              dataKey="value"
              name={metric.label}
              stroke="#b5dc8a"
              fill="#b5dc8a"
              fillOpacity={0.12}
              connectNulls={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <details>
        <summary>Данные таблицей</summary>
        <div className="global-table-scroll earth-data-table">
          <table>
            <thead>
              <tr>
                <th>Дата (UTC)</th>
                <th>{metric.unit}</th>
              </tr>
            </thead>
            <tbody>
              {metric.history.map((p, i) => (
                <tr key={p.date + i}>
                  <td>{p.date}</td>
                  <td>{format(p.value, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}

export function Sources({ sources }: { sources: Record<string, Source> }) {
  return (
    <div className="earth-source-status">
      {Object.entries(sources).map(([key, s]) => (
        <div key={key}>
          <strong>{sourceNames[key] ?? key}</strong>
          <span
            className={s.status === "ok" ? "global-success" : "global-warning"}
          >
            {s.status === "ok"
              ? "Ответ получен"
              : s.status === "needs_configuration"
                ? "Нужна настройка"
                : "Недоступен"}
          </span>
          {s.message && <p>{s.message}</p>}
        </div>
      ))}
    </div>
  );
}
