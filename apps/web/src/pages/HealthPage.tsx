import { useEffect, useState } from "react";
import { healthApi } from "@/api/client";
import type { HealthResponse, ReadinessResponse } from "@/types/api";
import { useSystemStore } from "@/store";
import styles from "./HealthPage.module.css";

export function HealthPage() {
  const { setReadiness } = useSystemStore();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readiness, setReadinessLocal] = useState<ReadinessResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);

  const refresh = () => {
    setLoading(true);
    setError(null);
    Promise.all([healthApi.health(), healthApi.ready()])
      .then(([h, r]) => {
        setHealth(h);
        setReadinessLocal(r);
        setReadiness(r);
        setCheckedAt(new Date());
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Health check failed");
        setLoading(false);
      });
  };

  useEffect(refresh, []);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.heading}>System Health</h1>
        <button onClick={refresh} className={styles.refreshBtn} disabled={loading}>
          {loading ? "Checking…" : "Refresh"}
        </button>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      {health && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Liveness</h2>
          <dl className={styles.dl}>
            <dt>Status</dt>
            <dd>
              <span className={health.status === "ok" ? styles.ok : styles.fail}>
                {health.status.toUpperCase()}
              </span>
            </dd>
            <dt>Version</dt>
            <dd>
              <code>{health.version}</code>
            </dd>
          </dl>
        </section>
      )}

      {readiness && (
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Readiness Checks</h2>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Check</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(readiness.checks ?? {}).map(([name, status]) => (
                <tr key={name}>
                  <td>
                    <code>{name}</code>
                  </td>
                  <td>
                    <span className={status === "ok" ? styles.ok : styles.fail}>
                      {String(status).toUpperCase()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {checkedAt && (
        <p className={styles.footer}>Last checked: {checkedAt.toLocaleTimeString()}</p>
      )}
    </div>
  );
}
