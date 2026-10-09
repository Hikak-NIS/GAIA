import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { ErrorBox, Field, Loading } from "../pages";
import { refreshInventory } from "./shared";
import type { TerritoryZone } from "./types";

function ZoneForm({
  tid,
  initial,
  onDone,
}: {
  tid: string;
  initial?: TerritoryZone;
  onDone: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const save = useMutation({
    mutationFn: () =>
      api(
        initial ? `/zones/${initial.id}` : `/territories/${tid}/zones`,
        initial ? "PUT" : "POST",
        { name, description },
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
      <h2>{initial ? "Редактирование зоны" : "Новая зона"}</h2>
      <Field label="Название зоны">
        <input
          required
          maxLength={100}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </Field>
      <Field label="Описание зоны">
        <textarea
          maxLength={5000}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </Field>
      <ErrorBox error={save.error} />
      <div className="actions">
        <button disabled={save.isPending}>Сохранить зону</button>
        <button className="button secondary" type="button" onClick={onDone}>
          Отмена
        </button>
      </div>
    </form>
  );
}
export function Zones() {
  const { tid = "" } = useParams();
  const q = useQuery({
    queryKey: ["foundation", "zones", tid],
    queryFn: () => api<TerritoryZone[]>(`/territories/${tid}/zones`),
  });
  const [editing, setEditing] = useState<TerritoryZone | "new" | null>(null);
  const remove = useMutation({
    mutationFn: (id: string) => api(`/zones/${id}`, "DELETE"),
    onSuccess: refreshInventory,
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Зоны территории</h2>
          <p>
            Основная зона использует существующий симулятор и виртуальный насос.
            Дополнительные зоны организуют растения и реальные устройства.
          </p>
        </div>
        <button onClick={() => setEditing("new")}>Добавить зону</button>
      </div>
      <ErrorBox error={q.error || remove.error} />
      {q.isPending && <Loading />}
      {editing && (
        <ZoneForm
          tid={tid}
          key={editing === "new" ? "new" : editing.id}
          initial={editing === "new" ? undefined : editing}
          onDone={() => setEditing(null)}
        />
      )}
      <div className="inventory-grid">
        {q.data?.map((z) => (
          <article className="panel" key={z.id}>
            <span className="eyebrow">
              {z.is_default ? "ОСНОВНАЯ ЗОНА" : "ЗОНА"}
            </span>
            <h3>{z.name}</h3>
            <p>{z.description || "Описание не задано"}</p>
            <div className="actions">
              <Link className="button secondary" to={`../plants?zone=${z.id}`}>
                Растения зоны
              </Link>
              <Link className="button secondary" to={`../devices?zone=${z.id}`}>
                Устройства зоны
              </Link>
              <button
                className="button secondary"
                onClick={() => setEditing(z)}
              >
                Редактировать
              </button>
              {!z.is_default && (
                <button
                  className="button secondary"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (window.confirm(`Удалить зону «${z.name}»?`))
                      remove.mutate(z.id);
                  }}
                >
                  Удалить
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
