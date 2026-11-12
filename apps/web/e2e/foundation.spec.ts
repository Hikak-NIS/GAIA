import { expect, test } from "@playwright/test";
import { confirmEmail } from "./mailbox";

test("профиль → зона → REAL-устройство → растение и показания", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const email = `foundation-${Date.now()}@example.com`;
  page.on("dialog", (dialog) => dialog.accept());
  await page.goto("/register");
  await page.getByLabel("Ваше имя").fill("Анна Phase 1");
  await page.getByLabel("Ник", { exact: true }).fill(`plant_${Date.now()}`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill("garden-pass-123");
  await page.getByRole("button", { name: "Создать аккаунт" }).click();
  await confirmEmail(page, email);
  await page
    .getByRole("link", { name: "Профили растений", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Добавить профиль" }).click();
  await page.getByLabel("Название культуры").fill("Тестовая культура");
  await page
    .getByLabel("Влажность почвы, % — минимум", { exact: true })
    .fill("20");
  await page
    .getByLabel("Влажность почвы, % — максимум", { exact: true })
    .fill("60");
  await page.getByText("Требования по стадиям роста", { exact: true }).click();
  await page.getByLabel("Цветение", { exact: true }).check();
  await page
    .getByLabel("Цветение: Влажность почвы, % — минимум", { exact: true })
    .fill("30");
  await page
    .getByLabel("Цветение: Влажность почвы, % — максимум", { exact: true })
    .fill("55");
  await page.getByRole("button", { name: "Сохранить профиль" }).click();
  await expect(
    page.getByRole("heading", { name: "Тестовая культура" }),
  ).toBeVisible();

  await page
    .getByRole("link", { name: "Добавить территорию", exact: true })
    .click();
  await page.getByRole("button", { name: "Сохранить территорию" }).click();
  await expect(
    page.getByRole("heading", { name: "Полевые измерения" }),
  ).toBeVisible();
  const tid = page.url().match(/territories\/([^/]+)/)?.[1];
  expect(tid).toBeTruthy();
  await page.getByRole("link", { name: "Зоны", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Основная зона", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Добавить зону" }).click();
  await page.getByLabel("Название зоны").fill("Грядка 1");
  await page.getByRole("button", { name: "Сохранить зону" }).click();
  await expect(
    page.getByRole("heading", { name: "Грядка 1", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Устройства", exact: true }).click();
  await page.getByRole("button", { name: "Добавить устройство" }).click();
  await page.getByLabel("Название устройства").fill("Pi тест");
  await page.getByLabel("Зона устройства").selectOption({ label: "Грядка 1" });
  await page.getByRole("button", { name: "Сохранить устройство" }).click();
  const device = page.locator("article.device-card").filter({
    has: page.getByRole("heading", { name: "Pi тест", exact: true }),
  });
  await expect(device.getByText("OFFLINE", { exact: true })).toBeVisible();
  await device.getByRole("button", { name: "Выдать / сменить ключ" }).click();
  const sensorId = await device
    .getByLabel("Sensor ID", { exact: true })
    .inputValue();
  const key = await device.getByLabel("API key", { exact: true }).inputValue();
  const telemetry = await page.request.post("/api/v1/devices/telemetry", {
    headers: { Authorization: `Bearer ${key}` },
    data: {
      sensor_id: sensorId,
      source: "device",
      timestamp: new Date().toISOString(),
      soil_moisture_pct: 41.2,
      air_temperature_c: 23,
    },
  });
  expect(telemetry.status()).toBe(201);
  await device.getByRole("button", { name: "Скрыть ключ" }).click();
  await expect(device.getByText("ONLINE", { exact: true })).toBeVisible({
    timeout: 10_000,
  });
  await page.getByRole("link", { name: "Растения", exact: true }).click();
  await page.getByRole("button", { name: "Добавить растение" }).click();
  await page.getByLabel("Название растения").fill("Куст у окна");
  await page.getByLabel("Зона растения").selectOption({ label: "Грядка 1" });
  await page.getByLabel("Стадия роста").selectOption("flowering");
  await page.getByLabel("Дата посадки").fill("2026-08-01");
  await page.getByLabel("Влажность почвы", { exact: true }).check();
  await page.getByRole("button", { name: "Сохранить растение" }).click();
  await page.getByRole("link", { name: "Открыть растение" }).click();
  await expect(
    page.getByRole("heading", { name: "Куст у окна" }),
  ).toBeVisible();
  await expect(page.getByText("30–55", { exact: true })).toBeVisible();
  await expect(
    page.locator("table").first().getByText("41,2 %", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("option", { name: "SIMULATED", exact: true }),
  ).toHaveCount(0);
  await page.getByLabel("Источник показаний растения").selectOption("REAL");
  await expect(
    page.locator("table").first().getByText("41,2 %", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Куст у окна" }),
  ).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("foundation-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page
      .getByRole("navigation", { name: "Главная навигация" })
      .getByRole("link", { name: "Профили растений" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: test.info().outputPath("foundation-mobile.png"),
    fullPage: true,
  });
  const deactivate = await page.request.get(
    `/api/v1/territories/${tid}/devices`,
  );
  const allDevices = await deactivate.json();
  const realDevice = allDevices.find(
    (d: { name: string }) => d.name === "Pi тест",
  );
  const changed = await page.request.put(`/api/v1/devices/${realDevice.id}`, {
    headers: { "X-GAIA-Request": "1" },
    data: { name: realDevice.name, zone_id: realDevice.zone_id, active: false },
  });
  expect(changed.status()).toBe(200);
  await page.reload();
  await expect(
    page.getByText("Устройство отключено", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Редактировать растение" }).click();
  await page.getByLabel("Влажность почвы", { exact: true }).uncheck();
  await page.getByRole("button", { name: "Сохранить растение" }).click();
  await expect(
    page.getByText("Привязанных сенсоров нет.", { exact: true }),
  ).toBeVisible();
});
