import { expect, test } from "@playwright/test";
import { confirmEmail } from "./mailbox";

test("Global и Ocean: планета, анализ, карты дат, организации и отзыв доступа", async ({
  page,
  browser,
}) => {
  test.setTimeout(150000);
  const nickname = `earth_${Date.now()}`,
    email = `${nickname}@example.com`;
  const markerTitle = `Точка отбора проб ${nickname}`;
  const ctx = await browser.newContext(),
    member = await ctx.newPage();
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  member.on("pageerror", (e) => errors.push(e.message));
  page.on("dialog", (d) => d.accept());
  member.on("dialog", (d) => d.accept());
  try {
    await member.goto("http://localhost:5174/register");
    await member.getByLabel("Ваше имя").fill("Earth member");
    await member.getByLabel("Ник", { exact: true }).fill(nickname);
    await member.getByLabel("Email", { exact: true }).fill(email);
    await member.getByLabel("Пароль").fill("garden-pass-123");
    await member.getByRole("button", { name: "Создать аккаунт" }).click();
    await confirmEmail(member, email);
    await member.goto("http://localhost:5174/global");
    await expect(
      member.getByRole("heading", { name: "Доступ к GAIA Global ограничен" }),
    ).toBeVisible();
    expect(
      (
        await member.request.get("http://localhost:5174/api/v1/earth/planet")
      ).status(),
    ).toBe(403);
    await page.goto("/login");
    await page.getByLabel("Ник или email").fill("E2EChief");
    await page.getByLabel("Пароль").fill("test-only-global-123");
    await page.getByRole("button", { name: "Войти", exact: true }).click();
    await confirmEmail(page, "chief-e2e@example.com");
    await page.goto("/global/access");
    await page.getByLabel("Поиск по нику, email или имени").fill(nickname);
    await page.getByRole("button", { name: "Найти", exact: true }).click();
    await page
      .getByRole("button", { name: "Назначить администратором" })
      .click();
    await expect(
      page.getByRole("button", { name: "Отозвать доступ" }),
    ).toBeVisible();
    await member.reload();
    await expect(
      member.getByRole("heading", { name: "Одна планета. Связанные системы." }),
    ).toBeVisible();
    await expect(
      member.getByRole("heading", {
        name: "Глобальная концентрация CO₂",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      member.getByRole("heading", { name: "GAIA Ocean", exact: true }),
    ).toBeVisible();
    await expect(
      member.getByRole("heading", { name: "Полярные области целиком" }),
    ).toBeVisible();
    await expect(member.locator(".earth-polar-grid img")).toHaveCount(2);
    await expect
      .poll(
        () =>
          member
            .locator(".earth-polar-grid img")
            .evaluateAll((images) =>
              images.every(
                (image) =>
                  (image as HTMLImageElement).complete &&
                  (image as HTMLImageElement).naturalWidth > 0,
              ),
            ),
        { timeout: 30000 },
      )
      .toBe(true);
    await expect
      .poll(
        () =>
          member
            .locator('img[src*="gibs.earthdata.nasa.gov"]')
            .evaluateAll((images) =>
              images.some(
                (image) =>
                  (image as HTMLImageElement).complete &&
                  (image as HTMLImageElement).naturalWidth > 0,
              ),
            ),
        { timeout: 30000 },
      )
      .toBe(true);
    await member.screenshot({
      path: test.info().outputPath("planet-desktop.png"),
      fullPage: true,
    });
    await member.getByRole("link", { name: "Территории", exact: true }).click();
    await member
      .getByRole("button", { name: "Анализировать территорию" })
      .click();
    await expect(
      member.getByRole("heading", {
        name: "Наблюдения и показатели",
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      member.getByRole("heading", { name: "PM₂.₅", exact: true }),
    ).toBeVisible();
    expect(await member.locator(".global-metric").count()).toBeGreaterThan(5);
    await expect(member.locator("body")).not.toContainText(
      /DEMO|SIMULATED|Локальный MVP/,
    );
    const savedUrl = member.url(),
      savedId = new URL(savedUrl).searchParams.get("analysis");
    expect(savedId).toBeTruthy();
    await member.getByLabel("Сравнить даты").check();
    await expect(member.getByLabel("Вторая дата")).toBeVisible();
    await expect(member.locator(".leaflet-container")).toHaveCount(2);
    await member.getByLabel("Сравнить даты").uncheck();
    const download = member.waitForEvent("download");
    await member.getByRole("button", { name: "Экспорт JSON" }).click();
    expect((await download).suggestedFilename()).toContain("GAIA-observations");
    await member.getByLabel("Название маркера").fill(markerTitle);
    await member
      .getByLabel("Заметка", { exact: true })
      .fill("Проверить состав воды");
    await member.getByRole("button", { name: "Сохранить маркер" }).click();
    await expect(member.getByText(markerTitle, { exact: true })).toBeVisible();
    await member.getByLabel("Название территории").fill("Изменённая область");
    await expect(member.getByText(/Параметры выбора отличаются/)).toBeVisible();
    await member.goto(savedUrl);
    await expect(
      member.getByRole("heading", { name: "Наблюдения и показатели" }),
    ).toBeVisible();
    await member.screenshot({
      path: test.info().outputPath("territory-desktop.png"),
      fullPage: true,
    });
    await member.getByRole("link", { name: "GAIA Ocean", exact: true }).click();
    await expect(
      member.getByRole("heading", { name: "Вода связывает всю планету." }),
    ).toBeVisible();
    await expect(
      member.getByRole("heading", {
        name: "Микропластик · предварительный риск",
      }),
    ).toBeVisible();
    await member.setViewportSize({ width: 390, height: 844 });
    await expect
      .poll(
        () =>
          member
            .locator('img[src*="gibs.earthdata.nasa.gov"]')
            .evaluateAll((images) =>
              images.some(
                (image) =>
                  (image as HTMLImageElement).complete &&
                  (image as HTMLImageElement).naturalWidth > 0,
              ),
            ),
        { timeout: 30000 },
      )
      .toBe(true);
    expect(
      await member.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await member.screenshot({
      path: test.info().outputPath("ocean-mobile.png"),
      fullPage: true,
    });
    await member
      .getByRole("link", { name: "Организации", exact: true })
      .click();
    await expect(
      member.getByRole("heading", { name: "UNEP", exact: true }),
    ).toBeVisible();
    expect(
      await member.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
    await page.getByRole("button", { name: "Отозвать доступ" }).click();
    await expect(
      member.getByRole("heading", { name: "Доступ к GAIA Global ограничен" }),
    ).toBeVisible({ timeout: 10000 });
    expect(
      (
        await member.request.get(
          `http://localhost:5174/api/v1/global/analyses/${savedId}`,
        )
      ).status(),
    ).toBe(403);
    await page.goto("/global/integrations");
    await expect(
      page.getByRole("heading", { name: "Подключения данных и ИИ" }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  } finally {
    await ctx.close();
  }
});
