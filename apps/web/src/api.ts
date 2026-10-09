import { QueryClient } from "@tanstack/react-query";
export const client = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: true } },
});
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const form = body instanceof FormData;
  const response = await fetch("/api/v1" + path, {
    method,
    credentials: "include",
    headers: {
      "X-GAIA-Request": "1",
      ...(form ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  });
  if (!response.ok) {
    const value: unknown = await response.json().catch(() => null);
    let message = "Не удалось выполнить запрос";
    if (value && typeof value === "object" && "detail" in value) {
      message =
        typeof value.detail === "string"
          ? value.detail
          : "Проверьте заполненные поля";
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export const endpoint = (tid: string, suffix: string) =>
  `/territories/${tid}/${suffix}`;
export const format = (value: number | null | undefined, digits = 1) =>
  value == null
    ? "—"
    : value.toLocaleString("ru-RU", { maximumFractionDigits: digits });
export const dateTime = (value: string, tz = "Asia/Almaty") =>
  new Date(
    value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value) ? value : value + "Z",
  ).toLocaleString("ru-RU", {
    timeZone: tz,
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
