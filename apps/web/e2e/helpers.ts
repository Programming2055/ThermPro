import { expect } from "@playwright/test";
import type { Page } from "@playwright/test";

export const uniqueName = (prefix: string): string =>
  `${prefix}-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e4)}`;

export async function createProject(page: Page, name: string): Promise<void> {
  await page.goto("/projects/new");
  await page.locator("#name").fill(name);
  await page.getByRole("button", { name: /create/i }).click();
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByText(name)).toBeVisible();
}

/** Open the New Calculation form with the given project selected. */
export async function openNewCalculation(page: Page, projectName: string): Promise<void> {
  await page.goto("/calculations/new");
  const select = page.getByLabel("Project");
  await expect(select.locator("option", { hasText: projectName })).toHaveCount(1);
  await select.selectOption({ label: projectName });
}

export const airTemperatureC = async (page: Page): Promise<number> => {
  const text = await page.getByTestId("air-temperature").first().innerText();
  const m = /(-?\d+(?:\.\d+)?) °C/.exec(text);
  if (!m) throw new Error(`No °C value in "${text}"`);
  return Number(m[1]);
};
