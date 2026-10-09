import { expect, test } from "@playwright/test";

test("засуха запускает объяснимый автополив и данные сохраняются после входа", async ({
  page,
}) => {
  const email = `gaia-e2e-${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Ваше имя").fill("Анна");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill("garden-pass-123");
  await page.getByRole("button", { name: "Создать аккаунт" }).click();
  await expect(
    page.getByRole("heading", { name: "Мои территории" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Добавить территорию" }).click();
  await page.getByRole("button", { name: "Сохранить территорию" }).click();
  await expect(
    page.getByRole("heading", { name: "Симуляция участка" }),
  ).toBeVisible();

  await page.getByLabel("Сценарий").selectOption("drought");
  await page.getByLabel("Скорость").selectOption("60");
  await page.getByRole("button", { name: "Запустить" }).click();
  await page.getByRole("link", { name: "Полив" }).click();
  await page.getByLabel("Режим").selectOption("automatic");
  await page.getByLabel("Порог влажности, %").fill("30");
  await page.getByLabel("Цель влажности, %").fill("45");
  await page.getByRole("button", { name: "Сохранить правила" }).click();

  await expect(
    page.getByText("Автополив включён", { exact: false }),
  ).toBeVisible({ timeout: 25_000 });
  await expect(
    page.getByText("Достигнута целевая влажность", { exact: false }),
  ).toBeVisible({ timeout: 25_000 });
  await expect(page.getByText(/л$/).first()).toBeVisible();

  await page.getByRole("link", { name: "Наблюдения" }).click();
  await page.getByLabel("Описание").fill("Листья восстановили упругость");
  await page.getByRole("button", { name: "Добавить наблюдение" }).click();
  await expect(page.getByText("Листья восстановили упругость")).toBeVisible();

  await page.getByRole("link", { name: "Отчёты" }).click();
  await page.getByRole("button", { name: "Сформировать за сегодня" }).click();
  await expect(page.getByText("Получено", { exact: false })).toBeVisible();

  await page.getByRole("link", { name: "Анна" }).click();
  await page.getByRole("button", { name: "Выйти из аккаунта" }).click();
  await page.getByRole("link", { name: "Войти" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Пароль").fill("garden-pass-123");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(
    page.getByRole("link", { name: "Мой двор", exact: true }),
  ).toBeVisible();
});
