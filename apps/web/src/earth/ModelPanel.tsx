import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { ErrorBox } from "../pages";

export function ModelPanel({ ocean = false }: { ocean?: boolean }) {
  const q = useQuery({
    queryKey: ["earth-models"],
    queryFn: () =>
      api<{
        items: {
          kind: string;
          status: string;
          features: string[];
          message: string;
          report?: Record<string, unknown>;
        }[];
      }>("/earth/models"),
  });
  const model = q.data?.items.find(
    (x) => x.kind === (ocean ? "microplastics" : "land"),
  );
  const [values, setValues] = useState<Record<string, number>>({});
  const prediction = useMutation({
    mutationFn: () =>
      api<{ risk_probability: number; note: string; label_definition: string }>(
        "/earth/models/predict",
        "POST",
        { kind: model?.kind, features: values },
      ),
  });
  return (
    <section className="global-panel">
      <span className="global-overline">МОДЕЛИ И ПОЛЕВЫЕ ДАННЫЕ</span>
      <h2>
        {ocean
          ? "Микропластик · предварительный риск"
          : "Модель риска деградации"}
      </h2>
      <p>{model?.message}</p>
      <p className="global-muted">
        {ocean
          ? "Для оценки концентрации микропластика нужны пробы воды. Модель использует источники нагрузки, гидрологию и полевые метки; снимок не является анализом пробы."
          : "Нужны экспертные метки состояния территорий, спутниковые признаки и полевые измерения."}{" "}
        Инструкция и формат данных: <code>docs/model-training.md</code>.
      </p>
      {model?.status === "research" && (
        <>
          <details>
            <summary>Качество на отложенных территориях</summary>
            <pre className="earth-json">
              {JSON.stringify(model.report, null, 2)}
            </pre>
          </details>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              prediction.mutate();
            }}
          >
            <div className="global-weight-fields">
              {model.features.map((f) => (
                <label key={f}>
                  {f}
                  <input
                    type="number"
                    step="any"
                    required
                    value={values[f] ?? ""}
                    onChange={(e) =>
                      setValues({ ...values, [f]: Number(e.target.value) })
                    }
                  />
                </label>
              ))}
            </div>
            <p className="global-muted">
              Единицы и диапазоны указаны в инструкции обучения. Признаки вне
              диапазона обучения отклоняются.
            </p>
            <button disabled={prediction.isPending}>Оценить риск</button>
          </form>
        </>
      )}
      {prediction.data && (
        <p role="status">
          Вероятность заданного класса:{" "}
          {(prediction.data.risk_probability * 100).toFixed(1)}%.{" "}
          {prediction.data.label_definition}. {prediction.data.note}
        </p>
      )}
      <ErrorBox error={q.error || prediction.error} />
    </section>
  );
}
