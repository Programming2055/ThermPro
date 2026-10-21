import { expect, test } from "@playwright/test";
import { createProject, uniqueName } from "./helpers";

test.describe("platform shell", () => {
  test("dashboard loads and the sidebar navigates", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await page.getByRole("link", { name: "Calculations" }).click();
    await expect(page).toHaveURL(/\/calculation-runs$/);
    await expect(page.getByRole("heading", { name: "Calculation Runs" })).toBeVisible();
  });

  test("health page reports the live backend as reachable", async ({ page }) => {
    await page.goto("/health");
    await expect(page.getByRole("heading", { name: /health/i }).first()).toBeVisible();
    await expect(page.getByText(/error|failed/i)).toHaveCount(0);
  });

  test("a new project can be created and is listed", async ({ page }) => {
    const name = uniqueName("E2E-Project");
    await createProject(page, name);
  });

  test("unknown routes fall back to the dashboard", async ({ page }) => {
    await page.goto("/does-not-exist");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });
});
