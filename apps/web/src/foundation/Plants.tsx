import { useState, type FormEvent } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { Empty, ErrorBox, Field, Loading } from "../pages";
import {
  ChannelTable,
  refreshInventory,
  RequirementSummary,
  SourceBadge,
  useInventory,
} from "./shared";
import {
  channelNames,
  stages,
  type Device,
  type Plant,
  type PlantInput,
  type PlantProfile,
  type PlantReadings,
  type Stage,
  type TerritoryZone,
} from "./types";

function PlantForm({
  tid,
  zones,
  devices,
  profiles,
  initial,
  onDone,
}: {
  tid: string;
  zones: TerritoryZone[];
  devices: Device[];
  profiles: PlantProfile[];
  initial?: Plant;
  onDone: () => void;
}) {
  const [form, setForm] = useState<PlantInput>(() => ({
    name: initial?.name ?? "",
    profile_id: initial?.profile_id ?? profiles[0]?.id ?? "",
    zone_id: initial?.zone_id ?? zones[0]?.id ?? "",
    planted_on: initial?.planted_on ?? null,
    growth_stage: initial?.growth_stage ?? "vegetative",
    camera_device_id: initial?.camera_device_id ?? null,
    sensor_channel_ids: initial?.sensor_channel_ids ?? [],
  }));
  const save = useMutation({
    mutationFn: () =>
      api(
        initial ? `/plants/${initial.id}` : `/territories/${tid}/plants`,
        initial ? "PUT" : "POST",
        form,
      ),
    onSuccess: async () => {
      await refreshInventory();
      onDone();
    },
  });
  const localDevices = devices.filter((d) => d.zone_id === form.zone_id);
  function submit(e: FormEvent) {
    e.preventDefault();
    save.mutate();
  }
  return (
    <form className="panel inventory-form" onSubmit={submit}>
      <h3>{initial ? "Редактирование растения" : "Новое растение"}</h3>
      <div className="form-grid">
        <Field label="Название растения">
          <input
            required
            maxLength={100}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </Field>
        <Field label="Профиль культуры">
          <select
            required
            value={form.profile_id}
            onChange={(e) => setForm({ ...form, profile_id: e.target.value })}
          >
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.common_name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Зона растения">
          <select
            required
            value={form.zone_id}
            onChange={(e) =>
              setForm({
                ...form,
                zone_id: e.target.value,
                sensor_channel_ids: [],
                camera_device_id: null,
              })
            }
          >
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Дата посадки">
          <input
            type="date"
            value={form.planted_on ?? ""}
            onChange={(e) =>
              setForm({ ...form, planted_on: e.target.value || null })
            }
          />
        </Field>
        <Field label="Стадия роста">
          <select
            value={form.growth_stage}
            onChange={(e) =>
              setForm({ ...form, growth_stage: e.target.value as Stage })
            }
          >
            {Object.entries(stages).map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Камера растения">
          <select
            value={form.camera_device_id ?? ""}
            onChange={(e) =>
              setForm({ ...form, camera_device_id: e.target.value || null })
            }
          >
            <option value="">Без камеры</option>
            {localDevices
              .filter((d) => d.device_type === "CAMERA")
              .map((d) => (
                <option key={d.id} value={d.id} disabled={!d.active}>
                  {d.name}
                </option>
              ))}
          </select>
        </Field>
      </div>
      <fieldset className="sensor-picker">
        <legend>Привязанные сенсоры</legend>
        <p>
          Выберите только каналы, измеряющие условия этого растения. Источники
          сохраняются раздельно.
        </p>
        {localDevices
          .filter((d) => d.channels.length)
          .map((d) => (
            <div key={d.id}>
              <h4>
                {d.name} <SourceBadge source={d.source} />
                {!d.active &&
                  " · Деактивировано: снимите привязку или активируйте устройство"}
              </h4>
              {d.channels.map((c) => (
                <label className="check" key={c.id}>
                  <input
                    type="checkbox"
                    checked={form.sensor_channel_ids.includes(c.id)}
                    disabled={
                      !d.active && !form.sensor_channel_ids.includes(c.id)
                    }
                    onChange={(e) =>
                      setForm({
                        ...form,
                        sensor_channel_ids: e.target.checked
                          ? [...form.sensor_channel_ids, c.id]
                          : form.sensor_channel_ids.filter((id) => id !== c.id),
                      })
                    }
                  />
                  {channelNames[c.sensor_type]}
                </label>
              ))}
            </div>
          ))}
        {!localDevices.some((d) => d.channels.length) && (
          <p>В этой зоне пока нет активных сенсоров.</p>
        )}
      </fieldset>
      <ErrorBox error={save.error} />
      <div className="actions">
        <button disabled={save.isPending || !profiles.length}>
          Сохранить растение
        </button>
        <button type="button" className="button secondary" onClick={onDone}>
          Отмена
        </button>
      </div>
    </form>
  );
}
export function Plants() {
  const { tid = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const zone = params.get("zone") ?? "";
  const inventory = useInventory(tid);
  const q = useQuery({
    queryKey: ["foundation", "plants", tid],
    queryFn: () => api<Plant[]>(`/territories/${tid}/plants`),
  });
  const [adding, setAdding] = useState(false);
  const filtered = q.data?.filter((p) => !zone || p.zone_id === zone);
  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Растения территории</h2>
          <p>
            Профиль задаёт требования, экземпляр связывает растение с зоной и
            сенсорами.
          </p>
        </div>
        <button
          disabled={
            inventory.pending ||
            !!inventory.error ||
            !inventory.profiles.data?.length
          }
          onClick={() => setAdding(true)}
        >
          Добавить растение
        </button>
      </div>
      <ErrorBox error={inventory.error || q.error} />
      {(inventory.pending || q.isPending) && <Loading />}
      {inventory.profiles.data?.length === 0 && (
        <div className="panel">
          <p>Сначала создайте профиль культуры.</p>
          <Link className="button" to="/app/plant-profiles">
            Перейти к профилям
          </Link>
        </div>
      )}
      <Field label="Фильтр зоны растений">
        <select
          value={zone}
          onChange={(e) =>
            setParams(e.target.value ? { zone: e.target.value } : {})
          }
        >
          <option value="">Все зоны</option>
          {inventory.zones.data?.map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </select>
      </Field>
      {adding && (
        <PlantForm
          tid={tid}
          zones={inventory.zones.data ?? []}
          profiles={inventory.profiles.data ?? []}
          devices={inventory.devices.data ?? []}
          onDone={() => setAdding(false)}
        />
      )}
      <div className="inventory-grid">
        {filtered?.map((p) => (
          <article className="panel" key={p.id}>
            <span className="eyebrow">
              {inventory.zones.data?.find((z) => z.id === p.zone_id)?.name}
            </span>
            <h3>{p.name}</h3>
            <p>
              {
                inventory.profiles.data?.find(
                  (profile) => profile.id === p.profile_id,
                )?.common_name
              }{" "}
              · {stages[p.growth_stage]}
            </p>
            <p>Оценка состояния ещё не рассчитана</p>
            <p>Привязано сенсоров: {p.sensor_channel_ids.length}</p>
            <Link className="button secondary" to={p.id}>
              Открыть растение
            </Link>
          </article>
        ))}
      </div>
      {filtered?.length === 0 && (
        <Empty title="Растений пока нет">
          <p>Добавьте экземпляр растения и выберите его профиль.</p>
        </Empty>
      )}
    </>
  );
}
export function PlantDetail() {
  const { tid = "", pid = "" } = useParams();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [source, setSource] = useState("");
  const inventory = useInventory(tid);
  const q = useQuery({
    queryKey: ["foundation", "plant", pid],
    queryFn: () => api<Plant>(`/plants/${pid}`),
  });
  const readings = useQuery({
    queryKey: ["foundation", "plant-readings", pid, source],
    queryFn: () =>
      api<PlantReadings>(
        `/plants/${pid}/readings?limit=20${source ? `&source=${source}` : ""}`,
      ),
    refetchInterval: 5000,
  });
  const remove = useMutation({
    mutationFn: () => api(`/plants/${pid}`, "DELETE"),
    onSuccess: async () => {
      await refreshInventory();
      navigate(`/app/territories/${tid}/plants`);
    },
  });
  if (q.isPending || inventory.pending) return <Loading />;
  if (!q.data || inventory.error)
    return <ErrorBox error={q.error || inventory.error} />;
  const plant = q.data;
  if (plant.territory_id !== tid)
    return (
      <ErrorBox
        error={new Error("Растение не принадлежит выбранной территории")}
      />
    );
  return (
    <>
      <Link to={`/app/territories/${tid}/plants`}>← Все растения</Link>
      <div className="page-heading">
        <div>
          <h2>{plant.name}</h2>
          <p>
            {
              inventory.profiles.data?.find((p) => p.id === plant.profile_id)
                ?.common_name
            }{" "}
            · {stages[plant.growth_stage]} ·{" "}
            {inventory.zones.data?.find((z) => z.id === plant.zone_id)?.name}
          </p>
          <p>Дата посадки: {plant.planted_on ?? "не указана"}</p>
        </div>
        <div className="actions">
          <button
            className="button secondary"
            onClick={() => setEditing(!editing)}
          >
            Редактировать растение
          </button>
          <button
            className="button secondary"
            disabled={remove.isPending}
            onClick={() => {
              if (
                window.confirm(
                  `Удалить растение «${plant.name}»? История устройств сохранится.`,
                )
              )
                remove.mutate();
            }}
          >
            Удалить растение
          </button>
        </div>
      </div>
      <ErrorBox error={q.error || readings.error || remove.error} />
      {editing && (
        <PlantForm
          key={plant.id}
          tid={tid}
          initial={plant}
          zones={inventory.zones.data ?? []}
          profiles={inventory.profiles.data ?? []}
          devices={inventory.devices.data ?? []}
          onDone={() => setEditing(false)}
        />
      )}
      <div className="panel">
        <h3>Состояние растения</h3>
        <p>
          {readings.data?.health_explanation ??
            "Оценка состояния ещё не рассчитана"}
          . Health Score и диагноз появятся после подключения проверяемых
          методов анализа.
        </p>
        {plant.camera_device_id && (
          <p>
            Камера:{" "}
            {
              inventory.devices.data?.find(
                (d) => d.id === plant.camera_device_id,
              )?.name
            }
            . Захват изображений пока не подключён.
          </p>
        )}
      </div>
      {readings.data && (
        <section className="panel">
          <h3>Требования текущей стадии</h3>
          <RequirementSummary value={readings.data.effective_requirements} />
        </section>
      )}
      <section className="panel">
        <h3>Показания привязанных сенсоров</h3>
        <Field label="Источник показаний растения">
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">Все, с отдельной маркировкой</option>
            <option value="REAL">REAL</option>
            <option value="SIMULATED">SIMULATED</option>
          </select>
        </Field>
        {readings.isPending ? (
          <Loading />
        ) : (
          readings.data && <ChannelTable channels={readings.data.channels} />
        )}
      </section>
      <section className="panel">
        <h3>История привязанных сенсоров</h3>
        <p>
          До 20 последних измерений каждого выбранного канала. Привязка
          показывает историю канала, а не самостоятельное измерение растения.
        </p>
        {readings.data && (
          <ChannelTable channels={readings.data.history} history />
        )}
      </section>
    </>
  );
}
