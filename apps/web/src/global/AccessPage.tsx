import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ShieldCheck, Search } from "lucide-react";
import { api, client, dateTime } from "../api";
import type { User } from "../types";
import { ErrorBox } from "../pages";
import { useGlobalUser } from "./GlobalLayout";

const roles = {
  user: "Пользователь",
  admin: "Администратор",
  superadmin: "Главный администратор",
};
export default function AccessPage() {
  const user = useGlobalUser();
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [onlyAdmins, setOnlyAdmins] = useState(false);
  const [notice, setNotice] = useState("");
  const q = useQuery({
    queryKey: ["admin-users", search, page, onlyAdmins],
    queryFn: () =>
      api<{ items: User[]; total: number; page_size: number }>(
        `/admin/users?q=${encodeURIComponent(search)}&page=${page}&administrators_only=${onlyAdmins}`,
      ),
    enabled: user.role === "superadmin",
  });
  const audit = useQuery({
    queryKey: ["admin-audit"],
    queryFn: () =>
      api<
        {
          id: string;
          actor: string;
          target: string | null;
          action: string;
          details: { previous?: string; role?: string; revision?: number };
          created_at: string;
        }[]
      >("/admin/audit"),
    enabled: user.role === "superadmin",
  });
  const update = useMutation({
    mutationFn: ({ id, role }: { id: string; role: "user" | "admin" }) =>
      api<User>(`/admin/users/${id}/role`, "PUT", { role }),
    onSuccess: (data) => {
      setNotice(
        `@${data.nickname}: ${roles[data.role]}. Изменение уже действует.`,
      );
      client.invalidateQueries({ queryKey: ["admin-users"] });
      client.invalidateQueries({ queryKey: ["admin-audit"] });
    },
  });
  if (user.role !== "superadmin")
    return (
      <section className="global-panel">
        <h1>Только для главного администратора</h1>
        <p>
          Назначать администраторов и просматривать список аккаунтов может
          только главный администратор.
        </p>
      </section>
    );
  return (
    <>
      <div className="global-page-heading">
        <div>
          <span className="global-overline">КОНТРОЛЬ ДОСТУПА</span>
          <h1>
            Команда GAIA Global<span>.</span>
          </h1>
          <p>
            Выбирайте администраторов из зарегистрированных аккаунтов по нику
            или email.
          </p>
        </div>
        <ShieldCheck size={38} />
      </div>
      <div className="global-demo-notice">
        <ShieldCheck size={22} />
        <div>
          <strong>Главный администратор · @{user.nickname}</strong>
          <p>
            {user.email}. Ваша роль защищена от удаления. Администраторы
            получают доступ к Global, но не могут назначать других
            администраторов.
          </p>
        </div>
      </div>
      <section className="global-panel">
        <form
          className="global-access-search"
          onSubmit={(e) => {
            e.preventDefault();
            setSearch(input);
            setPage(1);
          }}
        >
          <label>
            Поиск по нику, email или имени
            <input
              maxLength={254}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Найти аккаунт…"
            />
          </label>
          <button type="submit">
            <Search size={16} />
            Найти
          </button>
          <label className="global-toggle">
            <input
              type="checkbox"
              checked={onlyAdmins}
              onChange={(e) => {
                setOnlyAdmins(e.target.checked);
                setPage(1);
              }}
            />
            Только администраторы
          </label>
        </form>
        <ErrorBox error={q.error || update.error} />
        {notice && (
          <p className="global-success" role="status">
            {notice}
          </p>
        )}
        {q.isPending && <p role="status">Загружаем аккаунты…</p>}
        <div className="global-table-scroll">
          <table className="global-users-table">
            <thead>
              <tr>
                <th>Аккаунт</th>
                <th>Email</th>
                <th>Роль</th>
                <th>Доступ к Global</th>
              </tr>
            </thead>
            <tbody>
              {q.data?.items.map((u) => (
                <tr key={u.id}>
                  <td>
                    <strong>@{u.nickname}</strong>
                    <small>{u.name}</small>
                  </td>
                  <td>{u.email}</td>
                  <td>
                    <span className="global-future-badge">{roles[u.role]}</span>
                  </td>
                  <td>
                    {u.role === "superadmin" ? (
                      <span className="global-muted">Защищённая роль</span>
                    ) : (
                      <button
                        className="global-secondary"
                        disabled={update.isPending}
                        onClick={() => {
                          const role = u.role === "admin" ? "user" : "admin";
                          if (
                            window.confirm(
                              `${role === "admin" ? "Дать доступ к GAIA Global" : "Отозвать доступ к GAIA Global"} у @${u.nickname} (${u.email})?`,
                            )
                          )
                            update.mutate({ id: u.id, role });
                        }}
                      >
                        {u.role === "admin"
                          ? "Отозвать доступ"
                          : "Назначить администратором"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {q.data?.total === 0 && (
          <p className="global-empty-note">
            Аккаунты не найдены. Пользователь должен сначала зарегистрироваться.
          </p>
        )}
        <div className="global-pagination">
          <span>
            Всего: {q.data?.total ?? 0} · страница {page}
          </span>
          <div>
            <button
              className="global-secondary"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Назад
            </button>
            <button
              className="global-secondary"
              disabled={!q.data || page * q.data.page_size >= q.data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Далее
            </button>
          </div>
        </div>
      </section>
      <section className="global-panel">
        <span className="global-overline">ИСТОРИЯ ИЗМЕНЕНИЙ</span>
        <h2>Журнал администрирования</h2>
        <ErrorBox error={audit.error} />
        <div className="global-audit">
          {audit.data?.map((a) => (
            <div key={a.id}>
              <span>
                {a.action === "role_changed"
                  ? `@${a.actor} → @${a.target}: ${a.details.previous} → ${a.details.role}`
                  : `@${a.actor}: веса GEHI, версия ${a.details.revision}`}
              </span>
              <time>{dateTime(a.created_at)}</time>
            </div>
          ))}
        </div>
        {audit.data?.length === 0 && (
          <p className="global-muted">Назначений и изменений весов пока нет.</p>
        )}
      </section>
    </>
  );
}
