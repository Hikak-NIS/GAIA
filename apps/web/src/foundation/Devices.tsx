import { useState, type FormEvent } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, dateTime } from "../api";
import { Empty, ErrorBox, Field, Loading } from "../pages";
import { ChannelTable, refreshInventory, SourceBadge } from "./shared";
import {
  channelNames,
  deviceNames,
  type Channel,
  type Device,
  type TerritoryZone,
} from "./types";

function DeviceForm({
  tid,
  zones,
  onDone,
  initial,
}: {
  tid: string;
  zones: TerritoryZone[];
  onDone: () => void;
  initial?: Device;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [zone, setZone] = useState(initial?.zone_id ?? zones[0]?.id ?? "");
  const [type, setType] = useState<Device["device_type"]>(
    initial?.device_type ?? "SENSOR",
  );
  const [actuator, setActuator] = useState("PUMP");
  const [active, setActive] = useState(initial?.active ?? true);
  const save = useMutation({
    mutationFn: () =>
      api(
        initial ? `/devices/${initial.id}` : `/territories/${tid}/devices`,
        initial ? "PUT" : "POST",
        initial
          ? { name, zone_id: zone, active }
          : {
              name,
              zone_id: zone,
              device_type: type,
              source: "REAL",
              actuator_type: type === "ACTUATOR" ? actuator : null,
            },
      ),
    onSuccess: async () => {
      await refreshInventory();
      onDone();
    },
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    save.mutate();
  }
  return (
    <form className="panel inventory-form" onSubmit={submit}>
      <h3>{initial ? "Настройки устройства" : "Регистрация устройства"}</h3>
      <div className="form-grid">
        <Field label="Название устройства">
          <input
            required
            maxLength={100}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </Field>
        <Field label="Зона устройства">
          <select
            required
            value={zone}
            onChange={(e) => setZone(e.target.value)}
          >
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name}
              </option>
            ))}
          </select>
        </Field>
        {!initial && (
          <>
            <Field label="Тип устройства">
              <select
                value={type}
                onChange={(e) =>
                  setType(e.target.value as Device["device_type"])
                }
              >
                {Object.entries(deviceNames).map(([v, label]) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Источник устройства">
              <input value="REAL — внешнее оборудование" readOnly />
            </Field>
            {type === "ACTUATOR" && (
              <Field label="Тип привода">
                <select
                  value={actuator}
                  onChange={(e) => setActuator(e.target.value)}
                >
                  {["PUMP", "VALVE", "FAN", "LIGHT", "DOSER"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </Field>
            )}
          </>
        )}
        {initial?.source === "REAL" && (
          <label className="check">
            <input
              type="checkbox"
              checked={active}
              onChange={(e) => setActive(e.target.checked)}
            />
            Устройство активно
          </label>
        )}
      </div>
      <p>
        {initial
          ? "Деактивация отзывает ключ и сохраняет историю. Устройства с историей или привязками нельзя переносить между зонами."
          : "Виртуальная станция и насос уже созданы симулятором. Регистрация REAL-устройства создаёт карточку; сенсорная станция появится ONLINE после приёма телеметрии. Подключение камер и приводов — следующий этап."}
      </p>
      <ErrorBox error={save.error} />
      <div className="actions">
        <button disabled={save.isPending}>Сохранить устройство</button>
        <button className="button secondary" type="button" onClick={onDone}>
          Отмена
        </button>
      </div>
    </form>
  );
}
function CalibrationForm({ channel }: { channel: Channel }) {
  const [scale, setScale] = useState(channel.calibration.scale ?? 1);
  const [offset, setOffset] = useState(channel.calibration.offset ?? 0);
  const [notes, setNotes] = useState(channel.calibration.notes ?? "");
  const save = useMutation({
    mutationFn: () =>
      api(`/sensor-channels/${channel.id}/calibration`, "PUT", {
        scale,
        offset,
        notes,
      }),
    onSuccess: refreshInventory,
  });
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
      className="inventory-form"
    >
      <h4>{channelNames[channel.sensor_type]}</h4>
      <div className="form-grid">
        <Field label="Масштаб калибровки">
          <input
            type="number"
            min="0.000001"
            max="1000"
            step="any"
            required
            value={scale}
            onChange={(e) => setScale(Number(e.target.value))}
          />
        </Field>
        <Field label="Смещение калибровки">
          <input
            type="number"
            min="-100000"
            max="100000"
            step="any"
            required
            value={offset}
            onChange={(e) => setOffset(Number(e.target.value))}
          />
        </Field>
      </div>
      <Field label="Заметки калибровки">
        <textarea
          maxLength={1000}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </Field>
      <ErrorBox error={save.error} />
      <button className="button secondary" disabled={save.isPending}>
        Сохранить метаданные
      </button>
      {save.isSuccess && <span role="status"> Метаданные сохранены</span>}
    </form>
  );
}
function DeviceCard({
  device,
  zones,
  tid,
}: {
  device: Device;
  zones: TerritoryZone[];
  tid: string;
}) {
  const [editing, setEditing] = useState(false);
  const [credential, setCredential] = useState<{
    sensor_id: string;
    api_key: string;
  } | null>(null);
  const rotate = useMutation({
    mutationFn: () =>
      api<{ sensor_id: string; api_key: string }>(
        `/devices/${device.id}/credential`,
        "POST",
      ),
    onSuccess: setCredential,
  });
  return (
    <article className="panel device-card">
      <div className="inventory-card-heading">
        <div>
          <SourceBadge source={device.source} />
          <h3>{device.name}</h3>
        </div>
        <span className={`device-status status-${device.status.toLowerCase()}`}>
          {device.status}
        </span>
      </div>
      <p>
        {deviceNames[device.device_type]} ·{" "}
        {zones.find((z) => z.id === device.zone_id)?.name}
      </p>
      <p>
        Последняя связь:{" "}
        {device.last_seen ? dateTime(device.last_seen) : "ещё не поступала"}
        {!device.active && " · Деактивировано"}
      </p>
      <small className="source">
        Создано: {dateTime(device.created_at)} · ID {device.id}
      </small>
      {device.actuator_state && (
        <p>
          Состояние привода:{" "}
          {device.actuator_state === "UNKNOWN"
            ? "неизвестно — не подключён"
            : device.actuator_state}{" "}
          · {device.safety_status}
        </p>
      )}
      <div className="actions">
        <button
          className="button secondary"
          onClick={() => setEditing(!editing)}
        >
          Настроить
        </button>
        {device.source === "REAL" && device.sensor_id && device.active && (
          <button
            className="button secondary"
            disabled={rotate.isPending}
            onClick={() => {
              if (
                window.confirm(
                  "Выдать новый ключ? Предыдущий ключ этого устройства перестанет работать.",
                )
              )
                rotate.mutate();
            }}
          >
            Выдать / сменить ключ
          </button>
        )}
      </div>
      <ErrorBox error={rotate.error} />
      {credential && (
        <div className="credential-panel">
          <strong>Сохраните ключ сейчас — повторно он не отображается.</strong>
          <Field label="Sensor ID">
            <input readOnly value={credential.sensor_id} />
          </Field>
          <Field label="API key">
            <input readOnly value={credential.api_key} />
          </Field>
          <p>
            Передавайте ключ только в заголовке Authorization: Bearer при
            отправке телеметрии.
          </p>
          <button
            className="button secondary"
            onClick={() => setCredential(null)}
          >
            Скрыть ключ
          </button>
        </div>
      )}
      {editing && (
        <DeviceForm
          key={device.id}
          tid={tid}
          zones={zones}
          initial={device}
          onDone={() => setEditing(false)}
        />
      )}
      {device.channels.length > 0 && (
        <details>
          <summary>Сенсорные каналы ({device.channels.length})</summary>
          <ChannelTable channels={device.channels} />
          {device.source === "REAL" && (
            <details>
              <summary>Метаданные калибровки</summary>
              <p>
                Параметры хранятся для настройки клиента устройства. Сервер
                принимает готовые физические значения и не пересчитывает
                историю.
              </p>
              {device.channels.map((c) => (
                <CalibrationForm key={c.id} channel={c} />
              ))}
            </details>
          )}
        </details>
      )}
    </article>
  );
}
export function Devices() {
  const { tid = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const zone = params.get("zone") ?? "";
  const [source, setSource] = useState("");
  const [adding, setAdding] = useState(false);
  const devices = useQuery({
    queryKey: ["foundation", "devices", tid],
    queryFn: () => api<Device[]>(`/territories/${tid}/devices`),
    refetchInterval: 5000,
  });
  const zones = useQuery({
    queryKey: ["foundation", "zones", tid],
    queryFn: () => api<TerritoryZone[]>(`/territories/${tid}/zones`),
  });
  const filtered = devices.data?.filter(
    (d) => (!source || d.source === source) && (!zone || d.zone_id === zone),
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Устройства территории</h2>
          <p>Станции, камеры и приводы с явным источником данных.</p>
        </div>
        <button disabled={!zones.data} onClick={() => setAdding(true)}>
          Добавить устройство
        </button>
      </div>
      <div className="form-grid">
        <Field label="Фильтр источника">
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">Все источники</option>
            <option value="REAL">REAL</option>
            <option value="SIMULATED">SIMULATED</option>
          </select>
        </Field>
        <Field label="Фильтр зоны">
          <select
            value={zone}
            onChange={(e) =>
              setParams(e.target.value ? { zone: e.target.value } : {})
            }
          >
            <option value="">Все зоны</option>
            {zones.data?.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <ErrorBox error={devices.error || zones.error} />
      {(devices.isPending || zones.isPending) && <Loading />}
      {adding && zones.data && (
        <DeviceForm
          tid={tid}
          zones={zones.data}
          onDone={() => setAdding(false)}
        />
      )}
      <div className="device-list">
        {filtered?.map((device) => (
          <DeviceCard
            key={device.id}
            device={device}
            zones={zones.data ?? []}
            tid={tid}
          />
        ))}
      </div>
      {filtered?.length === 0 && (
        <Empty title="Устройств по этому фильтру нет">
          <p>Измените фильтр или зарегистрируйте устройство.</p>
        </Empty>
      )}
    </>
  );
}
