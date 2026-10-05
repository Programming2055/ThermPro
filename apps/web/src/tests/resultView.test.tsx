/**
 * Tests for the result experience.
 *
 * The one that matters most is the CR-ENG-005 watermark: an unconverged
 * result shown without it is the failure mode this rule exists to prevent,
 * and it is exactly the kind of regression a refactor introduces quietly.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ResultInvalidWatermark } from "@/components/results/ResultInvalidWatermark";
import { ConvergenceChart } from "@/components/results/ConvergenceChart";
import { CalculationResultPage } from "@/pages/CalculationResultPage";
import type { CalculationRun, ResultSnapshot } from "@/types/api";

const RUN_ID = "11111111-2222-3333-4444-555555555555";

function run(overrides: Partial<CalculationRun> = {}): CalculationRun {
  return {
    id: RUN_ID,
    project_id: "99999999-9999-9999-9999-999999999999",
    status: "COMPLETED",
    mode: "MODE_2",
    schema_version: "1.0",
    input_checksum_sha256: "a".repeat(64),
    rejection_reason: null,
    submitted_at: "2026-10-05T09:00:00Z",
    started_at: "2026-10-05T09:00:01Z",
    completed_at: "2026-10-05T09:00:02Z",
    engine_version: "0.4.0",
    result_checksum_sha256: "b".repeat(64),
    has_result: true,
    ...overrides,
  };
}

function result(overrides: Partial<ResultSnapshot> = {}): ResultSnapshot {
  return {
    schema_version: "1.0",
    run_id: RUN_ID,
    mode: "MODE_2",
    status: "CONVERGED",
    engine_version: "0.4.0",
    standard_profile: ["IEC_61439_2"],
    failure_reason: null,
    solver_summary: {
      outer_iterations_used: 9,
      inner_iterations_total: 9,
      wall_clock_s: 0.0123,
      final_max_delta_T_K: 0.004,
      final_energy_imbalance_fraction: 0.00015,
      final_mass_imbalance_fraction: null,
      convergence_trace: [
        { iteration: 1, max_delta_T_K: 12.0, inner_iterations: 1, energy_imbalance_W: 40, mass_imbalance_fraction: null },
        { iteration: 2, max_delta_T_K: 3.1, inner_iterations: 1, energy_imbalance_W: 11, mass_imbalance_fraction: null },
        { iteration: 3, max_delta_T_K: 0.26, inner_iterations: 1, energy_imbalance_W: 1.2, mass_imbalance_fraction: null },
        { iteration: 4, max_delta_T_K: 0.004, inner_iterations: 1, energy_imbalance_W: 0.05, mass_imbalance_fraction: null },
      ],
    },
    temperatures: {
      ambient_K: 308.15,
      entities: [
        {
          entity_id: "joint-1",
          entity_type: "BUSBAR_JOINT",
          name: "Main busbar joint",
          temperature_K: 388.76,
          temperature_C: 115.61,
          temperature_rise_K: 80.61,
          power_loss_W: 9.9,
        },
        {
          entity_id: "device-1",
          entity_type: "DEVICE",
          name: "Incomer ACB",
          temperature_K: 334.22,
          temperature_rise_K: 26.07,
          power_loss_W: 140.6,
        },
      ],
      thermal_cells: [
        {
          cell_id: "air:c1",
          compartment_id: "aaaaaaaa-0000-0000-0000-000000000001",
          centre_x_m: 0.4,
          centre_y_m: 0.3,
          centre_z_m: 1.5,
          temperature_K: 322.19,
        },
      ],
    },
    hotspots: [
      {
        entity_id: "joint-1",
        entity_type: "BUSBAR_JOINT",
        name: "Main busbar joint",
        temperature_K: 388.76,
        temperature_rise_K: 80.61,
        limit_K: 70.0,
        excess_K: 10.61,
        severity: "CRITICAL",
      },
    ],
    derating: [
      {
        entity_id: "joint-1",
        entity_type: "BUSBAR_JOINT",
        name: "Main busbar joint",
        current_loading_factor: 1.0,
        recommended_loading_factor: 0.93,
        margin_K: -10.61,
        action_required: true,
      },
    ],
    compliance: {
      overall_compliant: false,
      checks: [
        {
          check_id: "TEMP_RISE_JOINT_IEC61439",
          entity_id: "joint-1",
          entity_type: "JOINT",
          name: "Main busbar joint",
          standard: "IEC_61439_2",
          clause: "IEC 61439-1 Table 6",
          limit_K: 70.0,
          actual_rise_K: 80.61,
          margin_K: -10.61,
          status: "FAIL",
          note: "Terminals and bolted connections",
        },
      ],
    },
    airflow: {
      total_flow_rate_m3s: 0.0141,
      fan_operating_points: [],
      opening_flows: [],
      buoyancy_stack_pressure_Pa: 0.41,
    },
    k_ac_warnings: [
      {
        segment_id: "segment-1",
        warning_code: "K_AC_UNITY_FALLBACK",
        message: "Busbar was evaluated with K_AC = 1.0 (DC resistance only).",
      },
    ],
    mode_1_result: null,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/calculation-runs/${RUN_ID}`]}>
      <Routes>
        <Route path="/calculation-runs/:runId" element={<CalculationResultPage />} />
      </Routes>
    </MemoryRouter>
  );
}

function mockFetch(
  runBody: CalculationRun,
  resultBody: ResultSnapshot | null,
  onExecute?: () => void
) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "POST" && url.endsWith("/execute")) {
      onExecute?.();
      return Promise.resolve(
        new Response(JSON.stringify(runBody), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );
    }
    const body = url.endsWith("/result") ? resultBody : runBody;
    return Promise.resolve(
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });
}

describe("ResultInvalidWatermark", () => {
  it("leaves a converged result untouched", () => {
    render(
      <ResultInvalidWatermark status="CONVERGED" failureReason={null}>
        <p>42.0 °C</p>
      </ResultInvalidWatermark>
    );
    expect(screen.getByText("42.0 °C")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("marks an unconverged result invalid (CR-ENG-005)", () => {
    const { container } = render(
      <ResultInvalidWatermark status="NON_CONVERGED" failureReason="last max ΔT = 3.2 K">
        <p>42.0 °C</p>
      </ResultInvalidWatermark>
    );
    expect(screen.getByRole("alert")).toHaveTextContent("RESULT INVALID");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "must not be used for a compliance assessment"
    );
    expect(screen.getByText(/last max ΔT = 3.2 K/)).toBeInTheDocument();
    // The watermark overlays the numbers rather than sitting above them,
    // so it survives scrolling, a screenshot and a print.
    const overlay = container.querySelector("[data-watermark]");
    expect(overlay).not.toBeNull();
    expect(overlay?.getAttribute("data-watermark")).toBe("RESULT\nINVALID");
  });

  it("marks a failed calculation invalid too", () => {
    render(
      <ResultInvalidWatermark status="FAILED" failureReason="CR-ENG-002: no dataset">
        <p>nothing here</p>
      </ResultInvalidWatermark>
    );
    expect(screen.getByRole("alert")).toHaveTextContent("RESULT INVALID");
    expect(screen.getByText(/CR-ENG-002/)).toBeInTheDocument();
  });
});

describe("ConvergenceChart", () => {
  it("renders nothing for a trace too short to plot", () => {
    const { container } = render(<ConvergenceChart trace={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("describes the decay for a screen reader", () => {
    render(
      <ConvergenceChart trace={result().solver_summary.convergence_trace!} />
    );
    expect(screen.getByRole("img")).toHaveAccessibleName(
      /fell from 12.0 K to 0.00400 K over 4 iterations/
    );
  });
});

describe("CalculationResultPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch(run(), result()));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows temperatures in °C alongside their rise", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Incomer ACB")).toBeInTheDocument());
    // 388.76 K − 273.15 = 115.61 °C
    expect(screen.getAllByText("115.6").length).toBeGreaterThan(0);
    expect(screen.getAllByText("80.6").length).toBeGreaterThan(0);
  });

  it("reports the compliance verdict and the failing check", async () => {
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("✕ Not compliant")).toBeInTheDocument()
    );
    expect(
      screen.getByText("Terminals and bolted connections")
    ).toBeInTheDocument();
  });

  it("lists the hotspot and its excess", async () => {
    renderPage();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Hotspots" })).toBeInTheDocument()
    );
    expect(screen.getByText("+10.6")).toBeInTheDocument();
  });

  it("surfaces the non-suppressible K_AC warning (CR-ENG-011)", async () => {
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("K_AC_UNITY_FALLBACK")).toBeInTheDocument()
    );
  });

  it("shows the derating recommendation", async () => {
    renderPage();
    await waitFor(() =>
      expect(screen.getByText("93 %")).toBeInTheDocument()
    );
  });

  it("does not watermark a converged result", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("Incomer ACB")).toBeInTheDocument());
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("watermarks a non-converged result (CR-ENG-005)", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch(
        run(),
        result({
          status: "NON_CONVERGED",
          failure_reason: "Solver did not converge within 1 iteration.",
          compliance: { overall_compliant: false, checks: [] },
        })
      )
    );
    renderPage();
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("RESULT INVALID")
    );
  });

  it("offers to run a queued calculation", async () => {
    const onExecute = vi.fn();
    vi.stubGlobal(
      "fetch",
      mockFetch(run({ status: "PENDING", has_result: false }), null, onExecute)
    );
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByText(/has not produced a result yet/)
      ).toBeInTheDocument()
    );
    await userEvent.click(screen.getByRole("button", { name: "Run calculation" }));
    await waitFor(() => expect(onExecute).toHaveBeenCalled());
  });
});
