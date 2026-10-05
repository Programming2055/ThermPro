import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { calculationRunsApi } from "@/api/client";
import type { CalculationRun } from "@/types/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import styles from "./ListPage.module.css";

export function CalculationRunsPage() {
  const [runs, setRuns] = useState<CalculationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    calculationRunsApi
      .list()
      .then((r) => {
        setRuns(r.items);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load calculation runs");
        setLoading(false);
      });
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.heading}>Calculation Runs</h1>
      </div>
      <p className={styles.sub}>
        Immutable calculation snapshots. A run is stored when it is submitted and
        solved when it is executed; the stored result is the calculation record.
      </p>

      {loading && <p className={styles.message}>Loading…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && runs.length === 0 && (
        <p className={styles.message}>No calculation runs yet.</p>
      )}

      {runs.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Mode</th>
              <th>Result</th>
              <th>Input Checksum</th>
              <th>Submitted</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>
                  <Link to={`/calculation-runs/${run.id}`}>
                    <code className={styles.hash} title={run.id}>
                      {run.id.slice(0, 8)}…
                    </code>
                  </Link>
                </td>
                <td>
                  <StatusBadge status={run.status} />
                </td>
                <td>
                  <code className={styles.code}>{run.mode ?? "—"}</code>
                </td>
                <td>
                  {run.has_result ? (
                    <Link to={`/calculation-runs/${run.id}`}>View result</Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td>
                  <code className={styles.hash} title={run.input_checksum_sha256}>
                    {run.input_checksum_sha256
                      ? run.input_checksum_sha256.slice(0, 12) + "…"
                      : "—"}
                  </code>
                </td>
                <td className={styles.dateCell}>
                  {new Date(run.submitted_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
