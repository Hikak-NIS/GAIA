import { readFile } from "node:fs/promises";
import { expect, type Page } from "@playwright/test";

export async function confirmEmail(page: Page, email: string) {
  await expect(
    page.getByRole("heading", { name: "Подтвердите email" }),
  ).toBeVisible();
  const mailbox = JSON.parse(
    await readFile(
      new URL("../../../data/e2e-mailbox.json", import.meta.url),
      "utf8",
    ),
  );
  await page.getByLabel("Код из письма").fill(mailbox[email]);
  await page.getByRole("button", { name: "Подтвердить и войти" }).click();
  await expect(
    page.getByRole("heading", { name: "Мои территории" }),
  ).toBeVisible();
}
