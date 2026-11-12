import { useState, type FormEvent, type ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Link,
  Navigate,
  NavLink,
  Outlet,
  useNavigate,
  useParams,
} from "react-router-dom";
import {
  Leaf,
  LayoutDashboard,
  MapPin,
  Plus,
  ArrowUpRight,
  UserRound,
  LogOut,
  Sprout,
} from "lucide-react";
import { api, ApiError, client, format } from "./api";
import type { User, Territory, TerritoryInput } from "./types";
import { TerritoryMap } from "./Map";
import { NicknameEditor } from "./NicknameEditor";
export function ErrorBox({ error }: { error: unknown }) {
  return error ? (
    <p role="alert" className="error">
      {error instanceof Error ? error.message : String(error)}
    </p>
  ) : null;
}
export function Loading() {
  return (
    <div role="status" className="skeleton">
      Загружаем данные участка…
    </div>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <Sprout size={36} />
      <h3>{title}</h3>
      {children}
    </div>
  );
}
export function Landing() {
  return (
    <div className="landing">
      <header>
        <Link className="brand" to="/">
          <Leaf />
          GAIA<span>наблюдать · заботиться</span>
        </Link>
        <nav>
          <Link to="/login">Войти</Link>
          <Link className="button" to="/register">
            Создать аккаунт <ArrowUpRight size={18} />
          </Link>
        </nav>
      </header>
      <main className="hero">
        <div>
          <span className="eyebrow">
            ВАШ МАЛЕНЬКИЙ УЧАСТОК. БОЛЬШАЯ ЗАБОТА.
          </span>
          <h1>
            Почувствуйте,
            <br />
            чем живёт
            <br />
            <em>ваш сад.</em>
          </h1>
          <p>
            Наблюдайте за почвой, погодой и растениями. Объединяйте показания
            устройств, спутниковые снимки и полевые наблюдения.
          </p>
          <Link className="button large" to="/register">
            Создать свой участок <ArrowUpRight size={20} />
          </Link>
          <small>GAIA Grow · Участки, растения и окружающая среда</small>
        </div>
        <div className="hero-panel">
          <div className="hero-panel-top">
            <Leaf size={28} />
            <span>GAIA / ЖИВАЯ СИСТЕМА</span>
          </div>
          <h2>
            От сухой почвы
            <br />к устойчивому росту
          </h2>
          <div className="journey">
            <p>
              <b>01</b>
              <span>
                Наблюдение<small>Датчики, погода и ваши заметки</small>
              </span>
            </p>
            <p>
              <b>02</b>
              <span>
                Понятное решение<small>Каждое действие имеет причину</small>
              </span>
            </p>
            <p>
              <b>03</b>
              <span>
                Бережный полив<small>С ограничением времени и воды</small>
              </span>
            </p>
          </div>
          <div className="hero-footer">
            <span className="dot" /> Наблюдения с источниками и временем
            измерения.
          </div>
        </div>
      </main>
      <footer>GAIA — система наблюдения за природной территорией</footer>
    </div>
  );
}
export function AuthPage({ register = false }: { register?: boolean }) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [nickname, setNickname] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [challenge, setChallenge] = useState<{
    challenge_id: string;
    email_hint: string;
  } | null>(null);
  const [code, setCode] = useState("");
  const mutation = useMutation({
    mutationFn: async () => {
      const result = await api<{
        challenge_id: string;
        email_hint: string;
        verification_required: boolean;
      }>(
        "/auth/" + (register ? "register" : "login"),
        "POST",
        register
          ? { name, nickname, email, password }
          : { identifier: email, password },
      );
      if (
        result.verification_required !== true ||
        !result.challenge_id ||
        !result.email_hint
      ) {
        throw new Error(
          "Запущена устаревшая версия сервера GAIA. Остановите старый API на порту 8000 и запустите проект заново. Код подтверждения не был отправлен.",
        );
      }
      return result;
    },
    onSuccess: (value) => {
      setChallenge(value);
      setCode("");
    },
  });
  const verify = useMutation({
    mutationFn: () =>
      api<User>("/auth/verify-email", "POST", {
        challenge_id: challenge?.challenge_id,
        code,
      }),
    onSuccess: (user) => {
      client.clear();
      client.setQueryData(["me"], user);
      navigate("/app");
    },
  });
  const resend = useMutation({
    mutationFn: () =>
      api<{ challenge_id: string; email_hint: string }>(
        "/auth/resend-email",
        "POST",
        { challenge_id: challenge?.challenge_id },
      ),
    onSuccess: (value) => {
      setChallenge(value);
      setCode("");
    },
  });
  if (challenge)
    return (
      <div className="auth-page">
        <form
          className="auth-card"
          onSubmit={(e) => {
            e.preventDefault();
            verify.mutate();
          }}
        >
          <h1>Подтвердите email</h1>
          <p>
            Код отправлен на {challenge.email_hint}. Он действует 10 минут.
            Проверьте также папку «Спам».
          </p>
          <Field label="Код из письма">
            <input
              required
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </Field>
          <ErrorBox error={verify.error || resend.error} />
          <button disabled={verify.isPending}>
            {verify.isPending ? "Проверяем…" : "Подтвердить и войти"}
          </button>
          <button
            type="button"
            className="button secondary"
            disabled={resend.isPending}
            onClick={() => resend.mutate()}
          >
            Отправить код повторно
          </button>
          <p>Повторная отправка доступна через минуту.</p>
          <button
            type="button"
            className="button secondary"
            onClick={() => {
              setChallenge(null);
              verify.reset();
              resend.reset();
            }}
          >
            Назад ко входу
          </button>
        </form>
      </div>
    );
  return (
    <div className="auth-page">
      <Link to="/" className="brand">
        <Leaf />
        GAIA
      </Link>
      <form
        className="auth-card"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <span className="eyebrow">НАЧНИТЕ С ЗАБОТЫ</span>
        <h1>{register ? "Ваш сад начинается здесь" : "С возвращением"}</h1>
        <p>
          {register
            ? "Создайте аккаунт, чтобы сохранить участок и историю наблюдений."
            : "Войдите, чтобы увидеть, как чувствует себя ваш участок."}
        </p>
        {register && (
          <Field label="Ваше имя">
            <input
              required
              maxLength={100}
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
            />
          </Field>
        )}
        {register && (
          <Field label="Ник">
            <input
              aria-label="Ник"
              aria-describedby="nickname-help"
              required
              minLength={3}
              maxLength={32}
              pattern="[A-Za-z0-9_]{3,32}"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              autoComplete="username"
            />
            <small id="nickname-help">
              3–32 символа: латинские буквы, цифры и _.
            </small>
          </Field>
        )}
        <Field label={register ? "Email" : "Ник или email"}>
          <input
            type={register ? "email" : "text"}
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete={register ? "email" : "username"}
          />
        </Field>
        <Field label="Пароль">
          <input
            type="password"
            required
            minLength={register ? 10 : 1}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={register ? "new-password" : "current-password"}
          />
        </Field>
        {register && <small>Не менее 10 символов</small>}
        <ErrorBox error={mutation.error} />
        <button disabled={mutation.isPending}>
          {mutation.isPending
            ? "Подождите…"
            : register
              ? "Создать аккаунт"
              : "Войти"}
        </button>
        <p>
          {register ? "Уже есть аккаунт?" : "Впервые здесь?"}{" "}
          <Link to={register ? "/login" : "/register"}>
            {register ? "Войти" : "Зарегистрироваться"}
          </Link>
        </p>
      </form>
    </div>
  );
}
export function AppLayout() {
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/users/me"),
    refetchInterval: 5000,
  });
  const territories = useQuery({
    queryKey: ["territories"],
    queryFn: () => api<Territory[]>("/territories"),
    enabled: !!me.data,
  });
  if (me.isPending) return <Loading />;
  if (me.error instanceof ApiError && me.error.status === 401)
    return <Navigate to="/login" replace />;
  if (me.error || !me.data)
    return (
      <ErrorBox error={me.error ?? new Error("Не удалось загрузить аккаунт")} />
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" to="/app">
          <Leaf />
          GAIA GROW
        </Link>
        <span className="sidebar-caption">ПРОСТРАНСТВО ЗАБОТЫ</span>
        <NavLink to="/app" end>
          <LayoutDashboard size={19} />
          Мои территории
        </NavLink>
        <NavLink to="/app/plant-profiles">
          <Sprout size={19} />
          Профили растений
        </NavLink>
        {me.data.role !== "user" && (
          <NavLink to="/global">
            <Leaf size={19} />
            GAIA Global
          </NavLink>
        )}
        <div className="territory-links">
          {territories.data?.map((t) => (
            <NavLink to={"/app/territories/" + t.id} key={t.id}>
              <MapPin size={17} />
              {t.name}
            </NavLink>
          ))}
        </div>
        <Link to="/app/new" className="add-link">
          <Plus size={17} />
          Добавить территорию
        </Link>
        <div className="sidebar-bottom">
          <div className="simulation-note">
            <Sprout />
            <b>Наблюдение за участком</b>
            <p>
              Подключите устройства, добавьте растения и сопоставляйте полевые
              измерения с погодой и спутниковыми снимками.
            </p>
          </div>
          <NavLink to="/app/profile">
            <UserRound size={19} />
            {me.data.name}
          </NavLink>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>Наблюдайте. Понимайте. Заботьтесь.</span>
          <span className="badge">GAIA GROW</span>
        </header>
        <nav className="mobile-navigation" aria-label="Главная навигация">
          <Link to="/app">Территории</Link>
          <Link to="/app/plant-profiles">Профили растений</Link>
          <Link to="/app/new">Новая территория</Link>
          <Link to="/app/profile">Аккаунт</Link>
          {me.data.role !== "user" && <Link to="/global">GAIA Global</Link>}
        </nav>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
export function DashboardPage() {
  const q = useQuery({
    queryKey: ["territories"],
    queryFn: () => api<Territory[]>("/territories"),
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">ВАШЕ ПРОСТРАНСТВО</span>
          <h1>Мои территории</h1>
          <p>Всё, что растёт, начинается с внимания.</p>
        </div>
        <Link className="button" to="/app/new">
          <Plus size={18} />
          Создать территорию
        </Link>
      </div>
      {q.isPending ? <Loading /> : <ErrorBox error={q.error} />}
      <div className="territory-grid">
        {q.data?.map((t) => (
          <Link
            className="territory-card"
            to={"/app/territories/" + t.id}
            key={t.id}
          >
            <div className="territory-card-art">
              <MapPin size={38} />
              <span>
                {format(t.latitude, 4)}° / {format(t.longitude, 4)}°
              </span>
            </div>
            <div>
              <span className="eyebrow">ТЕРРИТОРИЯ · ЗОНЫ И РАСТЕНИЯ</span>
              <h2>
                {t.name}
                <ArrowUpRight size={22} />
              </h2>
              <p>{t.description || "Участок готов к наблюдению"}</p>
              <small>
                {format(t.area, 0)} м² · {t.timezone}
              </small>
            </div>
          </Link>
        ))}
      </div>
      {q.data?.length === 0 && (
        <Empty title="Добавьте свой первый участок">
          <p>
            Выберите точку на карте, добавьте растения и подключите датчики для
            наблюдения за участком.
          </p>
          <Link className="button" to="/app/new">
            Создать территорию
          </Link>
        </Empty>
      )}
    </>
  );
}
export function TerritoryForm({
  initial,
  onSave,
  pending,
  error,
}: {
  initial?: Territory;
  onSave: (value: TerritoryInput) => void;
  pending: boolean;
  error: unknown;
}) {
  const [value, setValue] = useState<TerritoryInput>(
    initial
      ? {
          name: initial.name,
          description: initial.description,
          latitude: initial.latitude,
          longitude: initial.longitude,
          area: initial.area,
          timezone: initial.timezone,
        }
      : {
          name: "Мой двор",
          description: "",
          latitude: 43.2389,
          longitude: 76.8897,
          area: 100,
          timezone: "Asia/Almaty",
        },
  );
  return (
    <form
      className="territory-form"
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        onSave(value);
      }}
    >
      <div className="form-grid">
        <Field label="Название территории">
          <input
            required
            maxLength={100}
            value={value.name}
            onChange={(e) => setValue({ ...value, name: e.target.value })}
          />
        </Field>
        <Field label="Площадь, м²">
          <input
            required
            type="number"
            min="1"
            max="1000000"
            value={value.area}
            onChange={(e) =>
              setValue({ ...value, area: Number(e.target.value) })
            }
          />
        </Field>
        <Field label="Широта">
          <input
            required
            type="number"
            step="any"
            min="-90"
            max="90"
            value={value.latitude}
            onChange={(e) =>
              setValue({ ...value, latitude: Number(e.target.value) })
            }
          />
        </Field>
        <Field label="Долгота">
          <input
            required
            type="number"
            step="any"
            min="-180"
            max="180"
            value={value.longitude}
            onChange={(e) =>
              setValue({ ...value, longitude: Number(e.target.value) })
            }
          />
        </Field>
      </div>
      <p className="muted">
        Нажмите на карту, чтобы выбрать точку. Координаты также можно ввести с
        клавиатуры.
      </p>
      <TerritoryMap
        latitude={value.latitude}
        longitude={value.longitude}
        onSelect={(latitude, longitude) =>
          setValue({
            ...value,
            latitude: Number(latitude.toFixed(6)),
            longitude: Number(longitude.toFixed(6)),
          })
        }
      />
      <Field label="Описание">
        <textarea
          maxLength={5000}
          value={value.description}
          onChange={(e) => setValue({ ...value, description: e.target.value })}
        />
      </Field>
      <Field label="Временная зона IANA">
        <input
          required
          value={value.timezone}
          onChange={(e) => setValue({ ...value, timezone: e.target.value })}
        />
      </Field>
      <ErrorBox error={error} />
      <button disabled={pending}>
        {pending ? "Сохраняем…" : "Сохранить территорию"}
      </button>
    </form>
  );
}
export function NewTerritory() {
  const nav = useNavigate();
  const mutation = useMutation({
    mutationFn: (value: TerritoryInput) =>
      api<Territory>("/territories", "POST", value),
    onSuccess: async (t) => {
      await client.invalidateQueries({ queryKey: ["territories"] });
      nav("/app/territories/" + t.id + "/simulation");
    },
  });
  return (
    <>
      <span className="eyebrow">01 / ВЫБЕРИТЕ МЕСТО</span>
      <h1>Новая территория</h1>
      <p>Начните с небольшого участка, который знаете и любите.</p>
      <section className="panel">
        <TerritoryForm
          onSave={(value) => mutation.mutate(value)}
          pending={mutation.isPending}
          error={mutation.error}
        />
      </section>
    </>
  );
}
export function Profile() {
  const nav = useNavigate();
  const q = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/users/me"),
  });
  const logout = useMutation({
    mutationFn: () => api("/auth/logout", "POST"),
    onSuccess: () => {
      client.clear();
      nav("/");
    },
  });
  return (
    <section className="panel narrow">
      <span className="eyebrow">АККАУНТ</span>
      <h1>Ваш профиль</h1>
      <h2>{q.data?.name}</h2>
      <p>{q.data?.email}</p>
      {q.data && (
        <>
          <p>
            Роль:{" "}
            {q.data.role === "superadmin"
              ? "Главный администратор"
              : q.data.role === "admin"
                ? "Администратор"
                : "Пользователь"}
          </p>
          <NicknameEditor key={q.data.id} user={q.data} />
          {q.data.role !== "user" && (
            <p>
              <Link to="/global">Открыть GAIA Global →</Link>
            </p>
          )}
        </>
      )}
      <p>Территории и наблюдения сохраняются в вашей учётной записи.</p>
      <button onClick={() => logout.mutate()} disabled={logout.isPending}>
        <LogOut size={18} />
        Выйти из аккаунта
      </button>
      <ErrorBox error={logout.error} />
    </section>
  );
}
export function Settings() {
  const { tid = "" } = useParams();
  const nav = useNavigate();
  const q = useQuery({
    queryKey: ["territory", tid],
    queryFn: () => api<Territory>("/territories/" + tid),
  });
  const save = useMutation({
    mutationFn: (value: TerritoryInput) =>
      api("/territories/" + tid, "PUT", value),
    onSuccess: () => client.invalidateQueries(),
  });
  const remove = useMutation({
    mutationFn: () => api("/territories/" + tid, "DELETE"),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["territories"] });
      nav("/app");
    },
  });
  const credential = useMutation({
    mutationFn: () =>
      api<{ sensor_id: string; api_key: string; explanation: string }>(
        `/territories/${tid}/sensors/device-credential`,
        "POST",
      ),
  });
  return (
    <section className="panel">
      <h2>Настройки территории</h2>
      {q.data && (
        <TerritoryForm
          initial={q.data}
          onSave={(v) => save.mutate(v)}
          pending={save.isPending}
          error={save.error}
        />
      )}
      <h3>Будущий Raspberry Pi</h3>
      <p>
        Ключ предназначен для приёма телеметрии. Управление физическим GPIO не
        подключено.
      </p>
      <button
        className="secondary"
        onClick={() => {
          if (
            confirm(
              "Выпустить новый ключ устройства? Старый ключ будет отозван.",
            )
          )
            credential.mutate();
        }}
      >
        Выпустить ключ устройства
      </button>
      {credential.data && (
        <div className="notice">
          <p>{credential.data.explanation}</p>
          <p>
            sensor_id: <code>{credential.data.sensor_id}</code>
          </p>
          <p>
            API key: <code>{credential.data.api_key}</code>
          </p>
        </div>
      )}
      <ErrorBox error={credential.error} />
      <hr />
      <button
        className="danger"
        onClick={() => {
          if (
            confirm(
              "Удалить территорию со всей историей, наблюдениями и фотографиями?",
            )
          )
            remove.mutate();
        }}
        disabled={remove.isPending}
      >
        Удалить территорию
      </button>
      <ErrorBox error={remove.error} />
    </section>
  );
}
