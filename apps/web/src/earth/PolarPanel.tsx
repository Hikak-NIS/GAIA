import { useState } from "react";

const months = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function PolarImage({
  hemisphere,
  latest,
}: {
  hemisphere: "north" | "south";
  latest?: string | null;
}) {
  const [selection, setSelection] = useState("");
  const [failedUrl, setFailedUrl] = useState("");
  const [loadedUrl, setLoadedUrl] = useState("");
  const date = selection || latest?.slice(0, 10);
  const parts = date?.split("-");
  const url = parts
    ? `https://noaadata.apps.nsidc.org/NOAA/G02135/${hemisphere}/daily/images/${parts[0]}/${parts[1]}_${months[Number(parts[1]) - 1]}/${hemisphere === "north" ? "N" : "S"}_${parts.join("")}_conc_v4.0.png`
    : "";
  return (
    <figure>
      <h3>{hemisphere === "north" ? "Арктика" : "Антарктика"}</h3>
      <label>
        Дата полярного снимка
        <input
          type="date"
          min="1978-10-26"
          max={latest?.slice(0, 10) || new Date().toISOString().slice(0, 10)}
          value={date || ""}
          onChange={(e) => setSelection(e.target.value)}
        />
      </label>
      {url && failedUrl !== url && loadedUrl !== url && (
        <p role="status">Загружаем спутниковую карту NSIDC…</p>
      )}
      {url && failedUrl !== url ? (
        <a href={url} target="_blank" rel="noreferrer">
          <img
            src={url}
            onLoad={() => setLoadedUrl(url)}
            onError={() => setFailedUrl(url)}
            alt={`Концентрация морского льда: ${hemisphere === "north" ? "Арктика" : "Антарктика"}, ${date}, NSIDC`}
          />
        </a>
      ) : (
        <p role="status">
          Изображение за выбранную дату недоступно. Выберите другую дату или
          откройте источник.
        </p>
      )}
      <figcaption>
        NSIDC Sea Ice Index v4 · {date || "ожидание данных"}. Концентрация льда
        в процентах; легенда включена в изображение. Пробелы наблюдений не
        означают отсутствие льда.
      </figcaption>
    </figure>
  );
}

export function PolarPanel({
  north,
  south,
}: {
  north?: string | null;
  south?: string | null;
}) {
  return (
    <section className="global-panel">
      <h2>Полярные области целиком</h2>
      <p>
        Спутниковые карты морского льда в полярной проекции охватывают оба
        полюса. Это дополнение к карте мира, которая ограничена широтами ±85°.
      </p>
      <div className="earth-polar-grid">
        <PolarImage hemisphere="north" latest={north} />
        <PolarImage hemisphere="south" latest={south} />
      </div>
      <a
        href="https://nsidc.org/data/g02135/versions/4"
        target="_blank"
        rel="noreferrer"
      >
        Описание продукта и ограничения NSIDC
      </a>
    </section>
  );
}
