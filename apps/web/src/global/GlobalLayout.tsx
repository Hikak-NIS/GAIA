import { useQuery } from "@tanstack/react-query";
import {
  Link,
  NavLink,
  Navigate,
  Outlet,
  useOutletContext,
} from "react-router-dom";
import { ArrowUpLeft, Globe2, ShieldCheck, MapPinned } from "lucide-react";
import { api, ApiError } from "../api";
import type { User } from "../types";
import "./global.css";

export function GlobalLayout() {
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/users/me"),
    refetchInterval: 3000,
  });
  if (me.isPending)
    return (
      <div className="global-gate" role="status">
        Проверяем доступ к GAIA Global…
      </div>
    );
  if (me.error instanceof ApiError && me.error.status === 401)
    return <Navigate to="/login" replace />;
  if (me.error || !me.data)
    return (
      <div className="global-gate">
        <h1>Не удалось проверить доступ</h1>
        <p role="alert">{me.error?.message}</p>
        <button onClick={() => me.refetch()}>Повторить</button>
      </div>
    );
  if (me.data.role === "user")
    return (
      <div className="global-gate">
        <ShieldCheck size={36} />
        <h1>Доступ к GAIA Global ограничен</h1>
        <p>
          Главный администратор должен назначить вашему аккаунту роль
          администратора.
        </p>
        <Link className="button" to="/app">
          Вернуться в GAIA
        </Link>
      </div>
    );
  return (
    <div className="global-app">
      <header className="global-topbar">
        <Link to="/global" className="global-brand">
          <Globe2 size={28} />
          <span>
            GAIA <b>GLOBAL</b>
          </span>
          <small>ENVIRONMENTAL INTELLIGENCE</small>
        </Link>
        <div className="global-user">
          <span className="global-role">
            {me.data.role === "superadmin"
              ? "ГЛАВНЫЙ АДМИНИСТРАТОР"
              : "АДМИНИСТРАТОР"}
          </span>
          <Link to="/app/profile">@{me.data.nickname}</Link>
        </div>
      </header>
      <div className="global-frame">
        <aside className="global-nav">
          <div>
            <span className="global-overline">РАБОЧЕЕ ПРОСТРАНСТВО</span>
            <NavLink to="/global" end>
              <MapPinned size={18} />
              Обзор планеты
            </NavLink>
            <NavLink to="/global/territories">Территории</NavLink>
            <NavLink to="/global/ocean">GAIA Ocean</NavLink>
            <NavLink to="/global/events">Изменения и события</NavLink>
            <NavLink to="/global/organizations">Организации</NavLink>
            {me.data.role === "superadmin" && (
              <NavLink to="/global/integrations">Подключения и API</NavLink>
            )}
            {me.data.role === "superadmin" && (
              <NavLink to="/global/access">
                <ShieldCheck size={18} />
                Управление доступом
              </NavLink>
            )}
          </div>
          <div className="global-nav-bottom">
            <div className="global-nav-note">
              <span className="global-status-dot" />
              Земля · Океан · Экосистемы
              <p>
                От наблюдения
                <br />к восстановлению.
              </p>
            </div>
            <Link to="/app">
              <ArrowUpLeft size={17} />
              Мои территории
            </Link>
          </div>
        </aside>
        <main className="global-main">
          <Outlet context={me.data} />
        </main>
      </div>
    </div>
  );
}
export function useGlobalUser() {
  return useOutletContext<User>();
}
