import { useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { Empty, ErrorBox, Field, Loading } from "../pages";
import {
  blankRequirements,
  stages,
  type PlantProfile,
  type ProfileInput,
  type Stage,
} from "./types";
import {
  refreshInventory,
  RequirementsFields,
  RequirementSummary,
} from "./shared";

function ProfileForm({
  initial,
  onSaved,
  onCancel,
}: {
  initial?: PlantProfile;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<ProfileInput>(() =>
    initial
      ? {
          ...blankRequirements(),
          ...Object.fromEntries(
            Object.keys(blankRequirements()).map((k) => [
              k,
              initial[k as keyof PlantProfile],
            ]),
          ),
          common_name: initial.common_name,
          scientific_name: initial.scientific_name,
          description: initial.description,
          common_diseases: initial.common_diseases,
          stage_requirements: initial.stage_requirements,
        }
      : {
          ...blankRequirements(),
          common_name: "",
          scientific_name: "",
          description: "",
          common_diseases: [],
          stage_requirements: {},
        },
  );
  const [diseases, setDiseases] = useState(
    initial?.common_diseases.join("\n") ?? "",
  );
  const save = useMutation({
    mutationFn: () =>
      api(
        `/plant-profiles${initial ? `/${initial.id}` : ""}`,
        initial ? "PUT" : "POST",
        {
          ...form,
          common_diseases: diseases
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean),
        },
      ),
    onSuccess: async () => {
      await refreshInventory();
      onSaved();
    },
  });
  function submit(e: FormEvent) {
    e.preventDefault();
    save.mutate();
  }
  return (
    <form
      className="panel inventory-form"
      onSubmit={submit}
      aria-label="Профиль растения"
    >
      <h2>{initial ? "Редактирование профиля" : "Новый профиль растения"}</h2>
      <div className="form-grid">
        <Field label="Название культуры">
          <input
            required
            maxLength={100}
            value={form.common_name}
            onChange={(e) => setForm({ ...form, common_name: e.target.value })}
          />
        </Field>
        <Field label="Научное название">
          <input
            maxLength={200}
            value={form.scientific_name}
            onChange={(e) =>
              setForm({ ...form, scientific_name: e.target.value })
            }
          />
        </Field>
      </div>
      <Field label="Описание профиля">
        <textarea
          maxLength={5000}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </Field>
      <p>
        Укажите требования для своей культуры и условий выращивания. Неизвестные
        диапазоны оставьте пустыми. Эти значения пока не меняют правила
        автополива.
      </p>
      <RequirementsFields
        value={form}
        onChange={(r) => setForm({ ...form, ...r })}
      />
      <Field label="Распространённые заболевания — по одному на строку">
        <textarea
          value={diseases}
          onChange={(e) => setDiseases(e.target.value)}
        />
      </Field>
      <details>
        <summary>Требования по стадиям роста</summary>
        <p>Пустые поля стадии наследуют общие требования профиля.</p>
        {(Object.entries(stages) as [Stage, string][]).map(([stage, label]) => (
          <section className="stage-section" key={stage}>
            <label className="check">
              <input
                type="checkbox"
                checked={!!form.stage_requirements[stage]}
                onChange={(e) => {
                  const next = { ...form.stage_requirements };
                  if (e.target.checked) next[stage] = blankRequirements();
                  else delete next[stage];
                  setForm({ ...form, stage_requirements: next });
                }}
              />
              {label}
            </label>
            {form.stage_requirements[stage] && (
              <RequirementsFields
                prefix={`${label}: `}
                value={form.stage_requirements[stage]}
                onChange={(r) =>
                  setForm({
                    ...form,
                    stage_requirements: {
                      ...form.stage_requirements,
                      [stage]: r,
                    },
                  })
                }
              />
            )}
          </section>
        ))}
      </details>
      <ErrorBox error={save.error} />
      <div className="actions">
        <button disabled={save.isPending}>Сохранить профиль</button>
        <button className="button secondary" type="button" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </form>
  );
}
export function PlantProfiles() {
  const q = useQuery({
    queryKey: ["foundation", "profiles"],
    queryFn: () => api<PlantProfile[]>("/plant-profiles"),
  });
  const [editing, setEditing] = useState<PlantProfile | "new" | null>(null);
  const remove = useMutation({
    mutationFn: (id: string) => api(`/plant-profiles/${id}`, "DELETE"),
    onSuccess: refreshInventory,
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">СПРАВОЧНИК ПОЛЬЗОВАТЕЛЯ</span>
          <h1>Профили растений</h1>
          <p>
            Требования культуры и её стадий роста. Экземпляры растений создаются
            внутри территории.
          </p>
        </div>
        <button onClick={() => setEditing("new")}>Добавить профиль</button>
      </div>
      <ErrorBox error={q.error || remove.error} />
      {q.isPending && <Loading />}
      {editing && (
        <ProfileForm
          key={editing === "new" ? "new" : editing.id}
          initial={editing === "new" ? undefined : editing}
          onSaved={() => setEditing(null)}
          onCancel={() => setEditing(null)}
        />
      )}
      <div className="inventory-grid">
        {q.data?.map((p) => (
          <article className="panel" key={p.id}>
            <h2>{p.common_name}</h2>
            <i>{p.scientific_name}</i>
            <p>{p.description}</p>
            <RequirementSummary value={p} />
            {p.common_diseases.length > 0 && (
              <p>Заболевания: {p.common_diseases.join(", ")}</p>
            )}
            <p>
              Особые стадии:{" "}
              {Object.keys(p.stage_requirements)
                .map((s) => stages[s as Stage])
                .join(", ") || "не заданы"}
            </p>
            <div className="actions">
              <button
                className="button secondary"
                onClick={() => setEditing(p)}
              >
                Редактировать
              </button>
              <button
                className="button secondary"
                disabled={remove.isPending}
                onClick={() => {
                  if (window.confirm(`Удалить профиль «${p.common_name}»?`))
                    remove.mutate(p.id);
                }}
              >
                Удалить
              </button>
            </div>
          </article>
        ))}
      </div>
      {q.data?.length === 0 && !editing && (
        <Empty title="Профилей пока нет">
          <p>Создайте профиль и укажите только известные требования.</p>
        </Empty>
      )}
    </>
  );
}
