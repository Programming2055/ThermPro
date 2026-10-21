import { expect, test } from "@playwright/test";
import { airTemperatureC, createProject, openNewCalculation, uniqueName } from "./helpers";

test.describe("MODE 2 calculation through the real solver", () => {
  let project: string;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    project = uniqueName("E2E-Calc");
    await createProject(page, project);
    await page.close();
  });

  test("default inputs converge to a valid, physically sensible result", async ({ page }) => {
    await openNewCalculation(page, project);
    await page.getByRole("button", { name: "Run calculation" }).click();

    await expect(page).toHaveURL(/\/calculation-runs\/[0-9a-f-]{36}$/);
    await expect(page.getByTestId("run-status")).toContainText("COMPLETED");
    await expect(page.getByTestId("invalid-banner")).toHaveCount(0);

    // 200 W * (400/630)^2 = 80.6 W generated
    await expect(page.getByTestId("heat-generated")).toContainText("80.6 W");
    // Air must be hotter than the 40 °C ambient
    expect(await airTemperatureC(page)).toBeGreaterThan(40);
    await expect(page.getByTestId("convergence-table")).toBeVisible();
    await expect(page.getByTestId("assumptions")).toContainText("Single well-mixed air zone");
  });

  test("a higher device load produces a higher air temperature", async ({ page }) => {
    const run = async (loadA: string): Promise<number> => {
      await openNewCalculation(page, project);
      await page.getByLabel("Load [A]").fill(loadA);
      await page.getByRole("button", { name: "Run calculation" }).click();
      await expect(page.getByTestId("run-status")).toContainText("COMPLETED");
      return airTemperatureC(page);
    };
    const low = await run("200");
    const high = await run("600");
    expect(high).toBeGreaterThan(low);
  });

  test("no devices means no self-heating: air stays at ambient", async ({ page }) => {
    await openNewCalculation(page, project);
    await page.getByRole("button", { name: "Remove device 1" }).click();
    await expect(page.getByTestId("device-row")).toHaveCount(0);
    await page.getByRole("button", { name: "Run calculation" }).click();
    await expect(page.getByTestId("run-status")).toContainText("COMPLETED");
    await expect(page.getByTestId("heat-generated")).toContainText("0.0 W");
    expect(await airTemperatureC(page)).toBeCloseTo(40, 0);
  });

  test("devices can be added and each contributes heat", async ({ page }) => {
    await openNewCalculation(page, project);
    await page.getByRole("button", { name: "Add device" }).click();
    await expect(page.getByTestId("device-row")).toHaveCount(2);
    await page.getByRole("button", { name: "Run calculation" }).click();
    await expect(page.getByTestId("run-status")).toContainText("COMPLETED");
    // 80.6 W (default MCCB) + 60 W * (100/160)^2 = 23.4 W
    await expect(page.getByTestId("heat-generated")).toContainText("104.1 W");
  });

  test("CR-ENG-005: an unconverged run is shown as RESULT INVALID", async ({ page }) => {
    await openNewCalculation(page, project);
    await page.getByLabel("Max iterations").fill("1");
    await page.getByLabel("Convergence tolerance [K]").fill("0.000000001");
    await page.getByRole("button", { name: "Run calculation" }).click();

    await expect(page.getByTestId("run-status")).toContainText("NON CONVERGED");
    await expect(page.getByTestId("invalid-banner")).toContainText("RESULT INVALID");
    await expect(page.getByTestId("invalid-frame")).toContainText("RESULT INVALID");
    await expect(page.getByTestId("warnings")).toContainText("NON-CONVERGED");
  });

  test("low-confidence device data raises a visible warning, with no hidden margin", async ({
    page,
  }) => {
    await openNewCalculation(page, project);
    await page.getByLabel("Data confidence").selectOption("UNKNOWN");
    await page.getByRole("button", { name: "Run calculation" }).click();
    await expect(page.getByTestId("warnings")).toContainText("DATA_CONFIDENCE_LOW");
    await expect(page.getByTestId("warnings")).toContainText("No margin has been applied");
  });

  test("restricted faces reduce heat rejection and raise the temperature", async ({ page }) => {
    const run = async (restrict: string[]): Promise<number> => {
      await openNewCalculation(page, project);
      for (const face of restrict) await page.getByLabel(face, { exact: true }).check();
      await page.getByRole("button", { name: "Run calculation" }).click();
      await expect(page.getByTestId("run-status")).toContainText("COMPLETED");
      return airTemperatureC(page);
    };
    const open = await run([]);
    const wallMounted = await run(["REAR", "BOTTOM"]);
    expect(wallMounted).toBeGreaterThan(open);
  });

  test("the run appears in the list and its detail page survives a reload", async ({ page }) => {
    await openNewCalculation(page, project);
    await page.getByRole("button", { name: "Run calculation" }).click();
    await expect(page.getByTestId("run-status")).toContainText("COMPLETED");
    const url = page.url();
    const id = url.split("/").pop() as string;

    await page.reload();
    await expect(page.getByTestId("run-status")).toContainText("COMPLETED");

    await page.goto("/calculation-runs");
    await page.getByRole("link", { name: new RegExp(`^${id.slice(0, 8)}`) }).click();
    await expect(page).toHaveURL(url);
  });
});

test.describe("input validation and errors", () => {
  test("client validation blocks impossible inputs and keeps the user on the form", async ({
    page,
  }) => {
    await page.goto("/calculations/new");
    await page.getByLabel("External height [m]").fill("0");
    await page.getByRole("button", { name: "Run calculation" }).click();
    await expect(page.getByTestId("form-problems")).toContainText("Height must be greater than 0");
    await expect(page).toHaveURL(/\/calculations\/new$/);
  });

  test("a fully insulated enclosure is rejected", async ({ page }) => {
    await page.goto("/calculations/new");
    for (const face of ["FRONT", "REAR", "LEFT", "RIGHT", "TOP", "BOTTOM"])
      await page.getByLabel(face, { exact: true }).check();
    await page.getByRole("button", { name: "Run calculation" }).click();
    await expect(page.getByTestId("form-problems")).toContainText("At least one face");
  });

  test("a server-side 422 is shown with its real message, not 'HTTP 422'", async ({ page }) => {
    const project = uniqueName("E2E-Err");
    await createProject(page, project);
    await openNewCalculationWithRoute(page, project);
    await page.getByRole("button", { name: "Run calculation" }).click();
    await expect(page.getByTestId("submit-error")).toContainText(
      "InputSnapshot failed schema validation"
    );
    await expect(page.getByTestId("submit-error")).not.toContainText("HTTP 422");
  });

  test("an unknown calculation id shows an error, not a blank page", async ({ page }) => {
    await page.goto("/calculation-runs/00000000-0000-0000-0000-00000000dead");
    await expect(page.getByRole("alert")).toBeVisible();
  });
});

async function openNewCalculationWithRoute(page: import("@playwright/test").Page, project: string) {
  await page.route("**/api/v1/calculation-runs", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        detail: {
          message: "InputSnapshot failed schema validation: bad",
          errors: ["x is required"],
        },
      }),
    });
  });
  await openNewCalculation(page, project);
}
