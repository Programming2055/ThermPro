import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { calculationRunsApi } from "@/api/client";
import { ConvergenceChart } from "@/components/results/ConvergenceChart";
import { ResultInvalidWatermark } from "@/components/results/ResultInvalidWatermark";
import { VerdictBadge } from "@/components/results/VerdictBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type {
  CalculationRun,
  ComplianceCheck,
  EntityTemperature,
  Hotspot,
  ResultSnapshot,
} from "@/types/api";
import styles from "./CalculationResultPage.module.css";

const KELVIN_OFFSET = 273.15;

/** Temperatures are computed in kelvin (CR-ENG-003) and read in °C. */
function celsius(kelvin: number): string {
  return (kelvin - KELVIN_OFFSET).toFixed(1);
}

function signed(value: number, digits = 1): string {
  return `${value >= 0 ? "+" : "−"}${Math.abs(value).toFixed(digits)}`;
}

const ENTITY_LABELS: Record<string, string> = {
  DEVICE: "Device",
  BUSBAR_SEGMENT: "Busbar segment",
  BUSBAR_JOINT: "Busbar joint",
  CONDUCTOR: "Conductor",
  SURFACE: "Enclosure surface",
  FAN: "Fan",
  COMPARTMENT_AIR: "Compartment air",
  CALCULATION: "Calculation",
  MODEL: "Model",
};

function label(entityType: string): string {
  return ENTITY_LABELS[entityType] ?? entityType.replace(/_/g, " ").toLowerCase();
}

export function CalculationResultPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<CalculationRun | null>(null);
  const [result, setResult] = useState<ResultSnapshot | null>(null);
  const [compartmentNames, setCompartmentNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    try {
      const fetchedRun = await calculationRunsApi.get(runId);
      setRun(fetchedRun);
      // A run with no stored result is not an error: it is simply queued.
      setResult(fetchedRun.has_result ? await calculationRunsApi.result(runId) : null);
      // M0-04 identifies a thermal cell by compartment id. The names live on
      // the submitted model, so they are read back from it rather than
      // duplicated into the result.
      setCompartmentNames(
        compartmentNamesFrom(await calculationRunsApi.input(runId))
      );
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load the calculation.");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    void load();
  }, [load]);

  const execute = useCallback(async () => {
    if (!runId) return;
    setExecuting(true);
    setError(null);
    try {
      await calculationRunsApi.execute(runId);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "The calculation could not be run.");
    } finally {
      setExecuting(false);
    }
  }, [runId, load]);

  if (loading) {
    return <p className={styles.message}>Loading…</p>;
  }
  if (error && !run) {
    return <p className={styles.error}>{error}</p>;
  }
  if (!run) {
    return <p className={styles.message}>Calculation run not found.</p>;
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h1 className={styles.heading}>Calculation result</h1>
          <p className={styles.sub}>
            Run <code className={styles.code}>{run.id}</code> ·{" "}
            <code className={styles.code}>{run.mode}</code> ·{" "}
            <StatusBadge status={run.status} />
            {/*
              A run completes whether or not the solver converged, so the run
              status alone would read "COMPLETED" above a RESULT INVALID
              banner. Show what the solver actually concluded beside it.
            */}
            {result && result.status !== "CONVERGED" && (
              <>
                {" "}
                <VerdictBadge verdict="FAIL" /> solver: {result.status}
              </>
            )}
            {run.engine_version && <> · engine {run.engine_version}</>}
          </p>
        </div>
        <div className={styles.actions}>
          <Link className={styles.btn} to="/calculation-runs">
            All runs
          </Link>
          <a className={styles.btn} href={calculationRunsApi.cfdExportUrl(run.id)}>
            CFD export
          </a>
          {!result && (
            <button
              className={styles.btn}
              onClick={() => void execute()}
              disabled={executing}
            >
              {executing ? "Running…" : "Run calculation"}
            </button>
          )}
        </div>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      {!result && (
        <p className={styles.message}>
          This run has not produced a result yet. Run it to compute temperatures.
        </p>
      )}

      {result && (
        <ResultInvalidWatermark
          status={result.status}
          failureReason={result.failure_reason}
        >
          <ResultBody
            result={result}
            run={run}
            compartmentNames={compartmentNames}
          />
        </ResultInvalidWatermark>
      )}
    </div>
  );
}

/** compartment id → name, read out of the stored M0-03 document. */
function compartmentNamesFrom(input: Record<string, unknown>): Record<string, string> {
  const names: Record<string, string> = {};
  const enclosure = input["enclosure"];
  if (typeof enclosure !== "object" || enclosure === null) return names;
  const compartments = (enclosure as Record<string, unknown>)["compartments"];
  if (!Array.isArray(compartments)) return names;
  for (const entry of compartments) {
    if (typeof entry !== "object" || entry === null) continue;
    const { id, name } = entry as { id?: unknown; name?: unknown };
    if (typeof id === "string" && typeof name === "string") {
      names[id] = name;
    }
  }
  return names;
}

function ResultBody({
  result,
  run,
  compartmentNames,
}: {
  result: ResultSnapshot;
  run: CalculationRun;
  compartmentNames: Record<string, string>;
}) {
  const ambient = result.temperatures.ambient_K;
  const entities = result.temperatures.entities;
  const cells = result.temperatures.thermal_cells ?? [];
  const hottestEntity = entities.reduce<EntityTemperature | null>(
    (best, entity) =>
      best === null || entity.temperature_K > best.temperature_K ? entity : best,
    null
  );
  const hottestAir = cells.reduce<number | null>(
    (best, cell) => (best === null || cell.temperature_K > best ? cell.temperature_K : best),
    null
  );
  const trace = result.solver_summary.convergence_trace ?? [];

  return (
    <>
      <div className={styles.summaryGrid}>
        <Metric label="Ambient" value={`${celsius(ambient)} °C`} note="datum for every rise" />
        {hottestAir !== null && (
          <Metric
            label="Hottest air"
            value={`${celsius(hottestAir)} °C`}
            note={`${(hottestAir - ambient).toFixed(1)} K rise`}
          />
        )}
        {hottestEntity && (
          <Metric
            label="Hottest component"
            value={`${celsius(hottestEntity.temperature_K)} °C`}
            note={hottestEntity.name ?? label(hottestEntity.entity_type)}
          />
        )}
        <Metric
          label="Iterations"
          value={String(result.solver_summary.outer_iterations_used)}
          note={`${result.solver_summary.wall_clock_s.toFixed(2)} s`}
        />
        <Metric
          label="Energy balance"
          value={`${(result.solver_summary.final_energy_imbalance_fraction * 100).toFixed(2)} %`}
          note="generated vs dissipated"
        />
        {result.airflow && (
          <Metric
            label="Ventilation"
            value={`${(result.airflow.total_flow_rate_m3s * 1000).toFixed(1)} L/s`}
            note={
              result.airflow.buoyancy_stack_pressure_Pa !== null
                ? `${result.airflow.buoyancy_stack_pressure_Pa.toFixed(2)} Pa stack`
                : "forced"
            }
          />
        )}
      </div>

      <ComplianceSection checks={result.compliance.checks} compliant={result.compliance.overall_compliant} />
      <HotspotSection hotspots={result.hotspots} />
      <TemperatureSection entities={entities} ambient={ambient} />
      {cells.length > 0 && (
        <AirSection cells={cells} ambient={ambient} names={compartmentNames} />
      )}
      {result.mode_1_result && <Mode1Section mode1={result.mode_1_result} />}
      <WarningSection result={result} />

      {trace.length > 1 && (
        <section className={styles.section}>
          <h2 className={styles.sectionHeading}>Convergence</h2>
          <p className={styles.sectionNote}>
            The largest temperature change per iteration, on a log scale. A run that
            converges falls steadily to the tolerance line; one that flattens above it,
            or climbs, has not found a solution.
          </p>
          <div className={styles.chartBox}>
            <ConvergenceChart trace={trace} />
          </div>
        </section>
      )}

      <p className={styles.footnote}>
        Computed by thermpro_engine {result.engine_version} against{" "}
        {result.standard_profile.join(", ")}. Temperatures are solved in kelvin
        (CR-ENG-003) and shown in °C. Result checksum{" "}
        <code className={styles.code}>
          {run.result_checksum_sha256?.slice(0, 16) ?? "—"}…
        </code>
        , which fixes this document against the input it was computed from.
      </p>
    </>
  );
}

function Metric({ label: text, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className={styles.card}>
      <div className={styles.cardLabel}>{text}</div>
      <div className={styles.cardValue}>{value}</div>
      {note && <div className={styles.cardNote}>{note}</div>}
    </div>
  );
}

function ComplianceSection({
  checks,
  compliant,
}: {
  checks: ComplianceCheck[];
  compliant: boolean;
}) {
  const graded = checks.filter((check) => check.status !== "NOT_APPLICABLE");
  const notes = checks.filter((check) => check.status === "NOT_APPLICABLE");

  return (
    <section className={styles.section}>
      <h2 className={styles.sectionHeading}>Compliance</h2>
      <div className={compliant ? styles.verdictPass : styles.verdictFail}>
        {compliant ? "✓ All checks pass" : "✕ Not compliant"}
      </div>
      {graded.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Check</th>
              <th>Entity</th>
              <th>Clause</th>
              <th className={styles.num}>Limit [K]</th>
              <th className={styles.num}>Actual [K]</th>
              <th className={styles.num}>Margin [K]</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {graded.map((check, index) => (
              <tr
                key={`${check.check_id}-${check.entity_id}-${index}`}
                className={check.status === "FAIL" ? styles.rowCritical : undefined}
              >
                <td>{check.note ?? check.check_id}</td>
                <td>{check.name ?? label(check.entity_type)}</td>
                <td className={styles.code}>{check.clause}</td>
                <td className={styles.num}>{check.limit_K.toFixed(1)}</td>
                <td className={styles.num}>{check.actual_rise_K.toFixed(1)}</td>
                <td className={styles.num}>{signed(check.margin_K)}</td>
                <td>
                  <VerdictBadge verdict={check.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {notes.length > 0 && (
        <ul className={styles.warningList} style={{ marginTop: "0.75rem" }}>
          {notes.map((check, index) => (
            <li key={`${check.check_id}-${index}`} className={styles.warningItem}>
              <strong>{check.check_id}</strong> — {check.note}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function HotspotSection({ hotspots }: { hotspots: Hotspot[] }) {
  if (hotspots.length === 0) {
    return null;
  }
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionHeading}>Hotspots</h2>
      <p className={styles.sectionNote}>
        Components at or near their limit. CRITICAL is over the limit; WARNING is
        within 5 K of it, which is close enough that ordinary modelling uncertainty
        covers the difference.
      </p>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Entity</th>
            <th>Type</th>
            <th className={styles.num}>Temperature [°C]</th>
            <th className={styles.num}>Rise [K]</th>
            <th className={styles.num}>Limit [K]</th>
            <th className={styles.num}>Excess [K]</th>
            <th>Severity</th>
          </tr>
        </thead>
        <tbody>
          {hotspots.map((hotspot) => (
            <tr
              key={hotspot.entity_id}
              className={
                hotspot.severity === "CRITICAL" ? styles.rowCritical : styles.rowWarning
              }
            >
              <td>{hotspot.name ?? hotspot.entity_id.slice(0, 8)}</td>
              <td>{label(hotspot.entity_type)}</td>
              <td className={styles.num}>{celsius(hotspot.temperature_K)}</td>
              <td className={styles.num}>{hotspot.temperature_rise_K.toFixed(1)}</td>
              <td className={styles.num}>{hotspot.limit_K.toFixed(1)}</td>
              <td className={styles.num}>
                {hotspot.excess_K > 0 ? signed(hotspot.excess_K) : "—"}
              </td>
              <td>
                <VerdictBadge verdict={hotspot.severity} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function TemperatureSection({
  entities,
  ambient,
}: {
  entities: EntityTemperature[];
  ambient: number;
}) {
  if (entities.length === 0) {
    return null;
  }
  const sorted = [...entities].sort((a, b) => b.temperature_K - a.temperature_K);
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionHeading}>Component temperatures</h2>
      <p className={styles.sectionNote}>
        Every modelled entity, hottest first. Rises are above the {celsius(ambient)} °C
        ambient the run used.
      </p>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Entity</th>
            <th>Type</th>
            <th className={styles.num}>Temperature [°C]</th>
            <th className={styles.num}>Rise [K]</th>
            <th className={styles.num}>Loss [W]</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((entity) => (
            <tr key={entity.entity_id}>
              <td>{entity.name ?? entity.entity_id.slice(0, 8)}</td>
              <td>{label(entity.entity_type)}</td>
              <td className={styles.num}>{celsius(entity.temperature_K)}</td>
              <td className={styles.num}>{entity.temperature_rise_K.toFixed(1)}</td>
              <td className={styles.num}>
                {entity.power_loss_W != null ? entity.power_loss_W.toFixed(1) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function AirSection({
  cells,
  ambient,
  names,
}: {
  cells: NonNullable<ResultSnapshot["temperatures"]["thermal_cells"]>;
  ambient: number;
  names: Record<string, string>;
}) {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionHeading}>Compartment air</h2>
      <p className={styles.sectionNote}>
        One mean air temperature per compartment, at its centroid. Air is not an
        entity, so it is reported as a thermal cell.
      </p>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Compartment</th>
            <th className={styles.num}>Height [m]</th>
            <th className={styles.num}>Temperature [°C]</th>
            <th className={styles.num}>Rise [K]</th>
          </tr>
        </thead>
        <tbody>
          {[...cells]
            .sort((a, b) => b.centre_z_m - a.centre_z_m)
            .map((cell) => (
              <tr key={cell.cell_id}>
                <td title={cell.compartment_id}>
                  {names[cell.compartment_id] ?? (
                    <code className={styles.code}>
                      {cell.compartment_id.slice(0, 8)}…
                    </code>
                  )}
                </td>
                <td className={styles.num}>{cell.centre_z_m.toFixed(2)}</td>
                <td className={styles.num}>{celsius(cell.temperature_K)}</td>
                <td className={styles.num}>
                  {(cell.temperature_K - ambient).toFixed(1)}
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </section>
  );
}

function Mode1Section({ mode1 }: { mode1: NonNullable<ResultSnapshot["mode_1_result"]> }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionHeading}>IEC TR 60890 (MODE 1)</h2>
      <p className={styles.sectionNote}>
        The empirical method gives enclosure air rises, not component temperatures.
        Its coefficients come from the licensed dataset your administrator imported;
        they are not shipped with this software.
      </p>
      <div className={styles.summaryGrid}>
        <Metric label="Total loss" value={`${mode1.P_total_W.toFixed(0)} W`} />
        <Metric
          label="Effective cooling area"
          value={`${mode1.effective_cooling_area_m2.toFixed(2)} m²`}
          note="A_e = Σ b_j·A_j"
        />
        <Metric
          label="Rise at mid-height"
          value={`${mode1.delta_theta_i_K.toFixed(1)} K`}
          note="Δθ_mid"
        />
        <Metric
          label="Rise at the top"
          value={`${mode1.delta_theta_e_K.toFixed(1)} K`}
          note="Δθ_top = d·Δθ_mid"
        />
      </div>
    </section>
  );
}

function WarningSection({ result }: { result: ResultSnapshot }) {
  const kAc = result.k_ac_warnings ?? [];
  const derating = (result.derating ?? []).filter((item) => item.action_required);
  if (kAc.length === 0 && derating.length === 0) {
    return null;
  }
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionHeading}>Engineering warnings</h2>
      {derating.length > 0 && (
        <>
          <p className={styles.sectionNote}>
            Loading advice. These are first-order estimates assuming the rise scales
            with dissipated power and the loss with the square of the current: a
            starting point, not a substitute for re-running at the reduced current.
          </p>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Entity</th>
                <th className={styles.num}>Loading now</th>
                <th className={styles.num}>Recommended</th>
                <th className={styles.num}>Margin [K]</th>
              </tr>
            </thead>
            <tbody>
              {derating.map((item) => (
                <tr key={item.entity_id} className={styles.rowWarning}>
                  <td>{item.name ?? label(item.entity_type)}</td>
                  <td className={styles.num}>
                    {(item.current_loading_factor * 100).toFixed(0)} %
                  </td>
                  <td className={styles.num}>
                    {(item.recommended_loading_factor * 100).toFixed(0)} %
                  </td>
                  <td className={styles.num}>{signed(item.margin_K)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {kAc.length > 0 && (
        <ul className={styles.warningList} style={{ marginTop: "0.75rem" }}>
          {kAc.map((warning) => (
            <li key={warning.segment_id} className={styles.warningItem}>
              <strong>{warning.warning_code}</strong> — {warning.message}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
