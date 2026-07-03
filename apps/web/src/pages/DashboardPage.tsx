import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { healthApi } from "@/api/client";
import type { ReadinessResponse } from "@/types/api";
import { useSystemStore } from "@/store";
import styles from "./DashboardPage.module.css";

export function DashboardPage() {
  const { readiness, readinessCheckedAt, setReadiness } = useSystemStore();
  const [loading, setLoading] = useState(!readiness);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    healthApi
      .ready()
      .then((r) => {
        if (!cancelled) {
          setReadiness(r);
          setLoading(false);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Unknown error");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [setReadiness]);

  return (
    <div className={styles.page}>
      <h1 className={styles.heading}>Dashboard</h1>
      <p className={styles.sub}>
        ThermPro — LV Switchboard Thermal Digital Twin &mdash; Milestone 1 Platform Foundation
      </p>

      <div className={styles.cards}>
        <DashCard
          title="System Status"
          description={loading ? "Checking…" : error ? `Error: ${error}` : systemStatusText(readiness)}
          accent={loading ? "neutral" : error ? "error" : systemAccent(readiness)}
          footer={readinessCheckedAt ? `Checked ${new Date(readinessCheckedAt).toLocaleTimeString()}` : undefined}
        />
        <DashCard
          title="Projects"
          description="Create and manage thermal analysis projects."
          href="/projects"
          accent="neutral"
        />
        <DashCard
          title="Library Releases"
          description="Manage immutable versioned engineering data libraries."
          href="/library-releases"
          accent="neutral"
        />
        <DashCard
          title="Calculation Runs"
          description="Submit and track thermal calculation jobs."
          href="/calculation-runs"
          accent="neutral"
        />
      </div>

      <div className={styles.notice}>
        <strong>ENGINE_NOT_IMPLEMENTED</strong> — The thermal solver has not been integrated in
        Milestone 1. All calculation submissions are accepted and stored with status{" "}
        <code>ENGINE_NOT_IMPLEMENTED</code>. No thermal results are computed.
      </div>
    </div>
  );
}

function systemStatusText(r: ReadinessResponse | null) {
  if (!r) return "Unknown";
  const checks = Object.values(r.checks ?? {});
  const allOk = checks.every((c) => c === "ok");
  return allOk ? "All systems operational" : "Degraded — some checks failing";
}

function systemAccent(r: ReadinessResponse | null): "success" | "error" | "neutral" {
  if (!r) return "neutral";
  const checks = Object.values(r.checks ?? {});
  return checks.every((c) => c === "ok") ? "success" : "error";
}

interface CardProps {
  title: string;
  description: string;
  href?: string;
  footer?: string;
  accent: "success" | "error" | "neutral";
}

function DashCard({ title, description, href, footer, accent }: CardProps) {
  const inner = (
    <div className={`${styles.card} ${styles[`card--${accent}`]}`}>
      <div className={styles.cardTitle}>{title}</div>
      <div className={styles.cardDesc}>{description}</div>
      {footer && <div className={styles.cardFooter}>{footer}</div>}
    </div>
  );
  return href ? <Link to={href} className={styles.cardLink}>{inner}</Link> : inner;
}
