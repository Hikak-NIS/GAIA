import { expect, test } from "@playwright/test";
import { confirmEmail } from "./mailbox";

test("Устаревший API не показывает ложную отправку кода", async ({ page }) => {
  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "old-server-user", nickname: "old" }),
    }),
  );
  await page.goto("/login");
  await page.getByLabel("Ник или email").fill("old");
  await page.getByLabel("Пароль").fill("test-only-password");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "устаревшая версия сервера",
  );
  await expect(page.getByLabel("Код из письма")).toHaveCount(0);
});

test("Grow: подтверждение email, реальные источники, заметки и повторный вход", async ({
  page,
}) => {
  test.setTimeout(90000);
  const email = `grow-${Date.now()}@example.com`;
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/register");
  await page.getByLabel("Ваше имя").fill("Анна");
  await page.getByLabel("Ник", { exact: true }).fill(`grow_${Date.now()}`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill("garden-pass-123");
  await page.getByRole("button", { name: "Создать аккаунт" }).click();
  await confirmEmail(page, email);
  await page
    .getByRole("link", { name: "Добавить территорию", exact: true })
    .click();
  await page.getByRole("button", { name: "Сохранить территорию" }).click();
  await expect(
    page.getByRole("heading", { name: "Полевые измерения" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Температура воздуха", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Симуляция", exact: true }),
  ).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(
    /DEMO|SIMULATED|Локальный MVP/,
  );
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Экспорт наблюдений" }).click();
  expect((await download).suggestedFilename()).toContain("GAIA-Grow");
  await page.getByRole("link", { name: "Наблюдения", exact: true }).click();
  await page
    .getByLabel("Описание")
    .fill("Участок требует полевого обследования");
  await page.getByRole("button", { name: "Добавить наблюдение" }).click();
  await expect(
    page.getByText("Участок требует полевого обследования", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "ИИ-помощник", exact: true }).click();
  await expect(page.getByLabel("Ваш вопрос")).toBeVisible();
  await page.getByRole("button", { name: "Закрыть помощника" }).click();
  await page.getByRole("link", { name: "Анна", exact: true }).click();
  await page.getByRole("button", { name: "Выйти из аккаунта" }).click();
  await page.goto("/login");
  await page.getByLabel("Ник или email").fill(email);
  await page.getByLabel("Пароль").fill("garden-pass-123");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await confirmEmail(page, email);
  await expect(
    page.getByRole("link", { name: "Мой двор", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
