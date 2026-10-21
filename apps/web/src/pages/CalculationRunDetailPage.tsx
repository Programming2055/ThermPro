import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { calculationRunsApi } from "@/api/client";
import type { CalculationRun } from "@/types/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { kelvinToCelsius } from "@/lib/calculationInput";
import styles from "./CalculationPages.module.css";

const fmt = (v: number | null | undefined, digits = 1): string =>
  v === null || v === undefined ? "—" : v.toFixed(digits);
const tempCell = (k: number | null | undefined): string =>
  k === null || k === undefined ? "—" : `${fmt(kelvinToCelsius(k))} °C (${fmt(k)} K)`;

export function CalculationRunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<CalculationRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    calculationRunsApi
      .get(runId)
      .then(setRun)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load run"));
  }, [runId]);

  if (error) return <p role="alert">{error}</p>;
  if (!run) return <p>Loading…</p>;

  const res = run.result_snapshot ?? null;
  // CR-ENG-005: anything that is not a converged, valid result is shown as invalid.
  const invalid =
    run.status === "NON_CONVERGED" || run.status === "FAILED" || (res !== null && !res.is_valid);

  const body = (
    <>
      {invalid && (
        <div className={styles.invalidBanner} role="alert" data-testid="invalid-banner">
          RESULT INVALID — {run.rejection_reason ?? "the solver did not produce a valid result"}. Do
          not use these values.
        </div>
      )}

      <div className={styles.kv}>
        <Kv label="Status" value={<StatusBadge status={run.status} />} testId="run-status" />
        <Kv label="Mode" value={run.mode} />
        <Kv label="Engine" value={run.engine_version ?? "—"} />
        {res && (
          <Kv label="Iterations" value={String(res.convergence_trace.length)} testId="iterations" />
        )}
        {res && (
          <Kv
            label="Heat generated"
            value={`${fmt(res.total_heat_generation_w)} W`}
            testId="heat-generated"
          />
        )}
        {res && <Kv label="Heat dissipated" value={`${fmt(res.total_heat_dissipation_w)} W`} />}
        {res && (
          <Kv
            label="Energy balance error"
            value={`${fmt(res.energy_balance_error_percent, 3)} %`}
          />
        )}
      </div>

      {res && res.compartment_results.length > 0 && (
        <section className={styles.section} style={{ marginTop: "1rem" }}>
          <h2 className={styles.sectionTitle}>Compartment results</h2>
          <table className={styles.table} data-testid="compartment-table">
            <thead>
              <tr>
                <th>Compartment</th>
                <th>Mean air temperature</th>
                <th>Heat generated</th>
                <th>Heat to ambient</th>
              </tr>
            </thead>
            <tbody>
              {res.compartment_results.map((c) => (
                <tr key={c.compartment_id}>
                  <td>{c.compartment_id}</td>
                  <td data-testid="air-temperature">{tempCell(c.mean_air_temperature_k)}</td>
                  <td>{fmt(c.total_heat_generation_w)} W</td>
                  <td>{fmt(c.heat_to_ambient_w)} W</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {res && res.warnings.length > 0 && (
        <section className={styles.section} data-testid="warnings">
          <h2 className={styles.sectionTitle}>Warnings</h2>
          {res.warnings.map((w, i) => (
            <div key={i} className={styles.warn}>
              <strong>{w.code}</strong> — {w.message}
            </div>
          ))}
        </section>
      )}

      {res && res.assumptions && res.assumptions.length > 0 && (
        <section className={styles.section} data-testid="assumptions">
          <h2 className={styles.sectionTitle}>Modelling assumptions</h2>
          <ul>
            {res.assumptions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </section>
      )}

      {res && res.convergence_trace.length > 0 && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Convergence history</h2>
          <table className={styles.table} data-testid="convergence-table">
            <thead>
              <tr>
                <th>Iteration</th>
                <th>Max ΔT [K]</th>
                <th>UA total [W/K]</th>
              </tr>
            </thead>
            <tbody>
              {res.convergence_trace.map((t) => (
                <tr key={t.iteration}>
                  <td>{t.iteration}</td>
                  <td>{t.max_delta_k.toExponential(2)}</td>
                  <td>{fmt(t.ua_total_w_per_k, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {!res && (
        <p className={styles.sub} data-testid="no-result">
          No result: this run was stored but not solved (
          {run.status.replace(/_/g, " ").toLowerCase()}).
        </p>
      )}

      <p className={styles.sub}>
        Input checksum (SHA-256): <span className={styles.mono}>{run.input_checksum_sha256}</span>
      </p>
    </>
  );

  return (
    <div className={styles.page}>
      <p className={styles.sub}>
        <Link to="/calculation-runs">← All calculations</Link>
      </p>
      <h1 className={styles.heading}>Calculation {run.id.slice(0, 8)}</h1>
      {invalid ? (
        <div className={styles.invalid} data-testid="invalid-frame">
          <div className={styles.watermark} aria-hidden="true">
            RESULT INVALID
          </div>
          {body}
        </div>
      ) : (
        body
      )}
    </div>
  );
}

function Kv({ label, value, testId }: { label: string; value: React.ReactNode; testId?: string }) {
  return (
    <div className={styles.kvItem}>
      <div className={styles.kvLabel}>{label}</div>
      <div className={styles.kvValue} data-testid={testId}>
        {value}
      </div>
    </div>
  );
}
