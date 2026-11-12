import { useState } from "react";
import {
  AreaChart,
  Area,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowUpRight,
  Droplets,
  Leaf,
  ThermometerSun,
  CloudRain,
  ScanLine,
  TrendingUp,
  Activity,
} from "lucide-react";
import { format } from "../api";
import type { Analysis, Metric } from "./types";

const icons: Record<string, typeof Leaf> = {
  ndvi: Leaf,
  lst: ThermometerSun,
  precipitation: CloudRain,
  soil_moisture: Droplets,
  vegetation_cover: ScanLine,
  degradation: Activity,
  vegetation_change: TrendingUp,
};
export function IndicatorCards({ metrics }: { metrics: Metric[] }) {
  return (
    <section aria-labelledby="indicators-title">
      <div className="global-section-heading">
        <div>
          <span className="global-overline">01 / НАБЛЮДЕНИЕ</span>
          <h2 id="indicators-title">Экологические показатели</h2>
        </div>
        <span className="global-demo-badge">DEMO / SIMULATED DATA</span>
      </div>
      <div className="global-metrics">
        {metrics.map((m) => {
          const Icon = icons[m.id] ?? Activity;
          const percent = Math.max(
            0,
            Math.min(100, ((m.value - m.min) / (m.max - m.min)) * 100),
          );
          return (
            <article className="global-metric" key={m.id}>
              <div className="global-metric-name">
                <Icon size={18} />
                <h3>{m.name}</h3>
              </div>
              <p className="global-metric-value">
                {format(m.value, m.id === "ndvi" ? 3 : 1)}
                <small>{m.unit}</small>
              </p>
              <div className="global-meter" aria-hidden="true">
                <span style={{ width: `${percent}%` }} />
              </div>
              <p className="global-metric-explanation">{m.explanation}</p>
              <footer>
                <span>DEMO · GAIA v1</span>
                <time>{m.updated_at}</time>
              </footer>
            </article>
          );
        })}
      </div>
    </section>
  );
}
export function HealthPanel({ analysis }: { analysis?: Analysis }) {
  const score = analysis?.gehi.score ?? 0;
  return (
    <section
      className={`global-health global-level-${analysis?.gehi.level ?? "unknown"}`}
    >
      <span className="global-overline">GAIA ENVIRONMENTAL HEALTH INDEX</span>
      <div className="global-score">
        <svg viewBox="0 0 160 160" aria-hidden="true">
          <circle
            cx="80"
            cy="80"
            r="68"
            fill="none"
            stroke="currentColor"
            strokeWidth="5"
            opacity="0.12"
          />
          <circle
            cx="80"
            cy="80"
            r="68"
            fill="none"
            stroke="var(--health-color)"
            strokeWidth="5"
            strokeDasharray={`${score * 4.2726} 427.26`}
            transform="rotate(-90 80 80)"
            strokeLinecap="round"
          />
        </svg>
        <div>
          <strong>{analysis ? score : "—"}</strong>
          <span>GEHI / 100</span>
        </div>
      </div>
      <h2>{analysis?.gehi.label ?? "Территория ждёт анализа"}</h2>
      <p>
        {analysis
          ? "Оценка выбранного DEMO-сценария"
          : "Выберите область и запустите демонстрационный анализ."}
      </p>
      <div className="global-scale">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <div className="global-scale-labels">
        <span>0 · критическое</span>
        <span>100 · хорошее</span>
      </div>
      <div className="global-health-disclaimer">
        <span className="global-demo-badge">КОНЦЕПТУАЛЬНЫЙ ИНДЕКС</span>
        <p>
          Не научно валидирован. Не является оценкой реального состояния этой
          местности.
        </p>
      </div>
    </section>
  );
}
export function Factors({ analysis }: { analysis: Analysis }) {
  return (
    <section className="global-panel">
      <div className="global-section-heading">
        <div>
          <span className="global-overline">02 / ОБЪЯСНЕНИЕ</span>
          <h2>Из чего складывается GEHI</h2>
        </div>
        <span className="global-muted">
          {analysis.gehi.model_version} · веса v{analysis.gehi.weights_revision}
        </span>
      </div>
      <p className="global-muted">
        Сумма нормированных оценок × их веса. Итог округляется до целого;
        высокое значение означает лучшее условное состояние.
      </p>
      <div className="global-factors">
        {analysis.gehi.factors.map((f) => (
          <div className="global-factor" key={f.id}>
            <div>
              <strong>{f.name}</strong>
              <span>
                вес {f.weight}% · вклад {format(f.contribution, 2)}
              </span>
            </div>
            <div className="global-factor-bar">
              <span style={{ width: `${f.score}%` }} />
            </div>
            <p>{f.explanation}</p>
            <details>
              <summary>Формула</summary>
              <code>{f.formula}</code>
            </details>
          </div>
        ))}
      </div>
      <p className="global-footnote">
        Шкала: 0–20 — критическое; 21–40 — сильная деградация; 41–60 —
        умеренная; 61–80 — удовлетворительное; 81–100 — хорошее. Пороги и
        климатические ориентиры демонстрационные.
      </p>
    </section>
  );
}
export function HistoryChart({ analysis }: { analysis: Analysis }) {
  const [metric, setMetric] = useState<
    "ndvi" | "vegetation_cover" | "soil_moisture" | "precipitation"
  >("ndvi");
  const names = {
    ndvi: "NDVI",
    vegetation_cover: "Покров, %",
    soil_moisture: "Влажность, % об.",
    precipitation: "Осадки, мм/30 дней",
  };
  return (
    <section className="global-panel">
      <div className="global-section-heading">
        <div>
          <span className="global-overline">03 / ДИНАМИКА</span>
          <h2>12 месяцев наблюдений</h2>
        </div>
        <span className="global-demo-badge">DEMO</span>
      </div>
      <div
        className="global-chart-options"
        role="group"
        aria-label="Показатель графика"
      >
        {Object.entries(names).map(([k, n]) => (
          <button
            key={k}
            aria-pressed={metric === k}
            className={metric === k ? "selected" : ""}
            onClick={() => setMetric(k as typeof metric)}
          >
            {n}
          </button>
        ))}
      </div>
      <p className="global-muted">
        Синтетический временной ряд. Последняя точка —{" "}
        {analysis.history.at(-1)?.date}; значения не получены со спутника.
      </p>
      <div
        className="global-chart"
        role="img"
        aria-label={`DEMO-график ${names[metric]}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={analysis.history}
            margin={{ top: 10, left: -20, right: 12, bottom: 5 }}
          >
            <defs>
              <linearGradient
                id="global-chart-fill"
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor="#b4db83" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#b4db83" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              stroke="#2c3c3f"
              strokeDasharray="3 5"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={(v) => String(v).slice(2, 7)}
              stroke="#8ba1a2"
              tick={{ fontSize: 11 }}
              minTickGap={25}
            />
            <YAxis
              stroke="#8ba1a2"
              tick={{ fontSize: 11 }}
              domain={metric === "ndvi" ? [0, 1] : [0, "auto"]}
            />
            <Tooltip
              contentStyle={{
                background: "#17262a",
                border: "1px solid #405458",
                color: "#edf4ee",
              }}
              labelFormatter={(v) => `${v} · DEMO`}
            />
            <Area
              type="monotone"
              dataKey={metric}
              name={names[metric]}
              stroke="#b4db83"
              fill="url(#global-chart-fill)"
              strokeWidth={2}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <details>
        <summary>Данные графика в таблице</summary>
        <div className="global-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Дата · DEMO</th>
                <th>{names[metric]}</th>
              </tr>
            </thead>
            <tbody>
              {analysis.history.map((row) => (
                <tr key={row.date}>
                  <td>{row.date}</td>
                  <td>{row[metric]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
export function Recommendations({ analysis }: { analysis: Analysis }) {
  return (
    <section aria-labelledby="restoration-title">
      <div className="global-section-heading">
        <div>
          <span className="global-overline">04 / ДЕЙСТВИЕ</span>
          <h2 id="restoration-title">Стратегия восстановления</h2>
        </div>
        <span className="global-muted">
          {analysis.recommendations.length} направлений
        </span>
      </div>
      <p className="global-muted">
        Предварительные направления по DEMO-показателям. Перед применением нужны
        полевое обследование и проверка специалистами.
      </p>
      <div className="global-recommendations">
        {analysis.recommendations.map((r, i) => (
          <article className="global-recommendation" key={r.id}>
            <div className="global-recommendation-number">
              {String(i + 1).padStart(2, "0")}
            </div>
            <div>
              <span className={`global-priority priority-${r.priority}`}>
                {r.priority === "high"
                  ? "Высокий"
                  : r.priority === "medium"
                    ? "Средний"
                    : "Низкий"}{" "}
                приоритет
              </span>
              <h3>{r.problem}</h3>
              <p>{r.action}</p>
              <div className="global-effect">
                <ArrowUpRight size={16} />
                <p>{r.expected_effect}</p>
              </div>
              <small>Основание: {r.evidence}</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
