import type { ComplianceStatus, HotspotSeverity } from "@/types/api";

type Verdict = ComplianceStatus | HotspotSeverity;

/**
 * A badge for a compliance verdict or a hotspot severity.
 *
 * Separate from StatusBadge, which speaks about a *run*. Reusing it here
 * printed "COMPLETED" next to a passing temperature check and "FAILED" next
 * to a critical hotspot — words from the wrong vocabulary, in a table an
 * engineer signs off.
 */
const STYLES: Record<Verdict, React.CSSProperties> = {
  PASS: { background: "#c6f6d5", color: "#22543d", borderColor: "#9ae6b4" },
  OK: { background: "#c6f6d5", color: "#22543d", borderColor: "#9ae6b4" },
  FAIL: { background: "#fed7d7", color: "#742a2a", borderColor: "#fc8181" },
  CRITICAL: { background: "#fed7d7", color: "#742a2a", borderColor: "#fc8181" },
  WARNING: { background: "#fefcbf", color: "#744210", borderColor: "#faf089" },
  NOT_APPLICABLE: {
    background: "#edf2f7",
    color: "#4a5568",
    borderColor: "#e2e8f0",
  },
};

const LABELS: Record<Verdict, string> = {
  PASS: "PASS",
  FAIL: "FAIL",
  NOT_APPLICABLE: "N/A",
  CRITICAL: "CRITICAL",
  WARNING: "WARNING",
  OK: "OK",
};

const BASE: React.CSSProperties = {
  padding: "2px 8px",
  borderRadius: "9999px",
  borderWidth: 1,
  borderStyle: "solid",
  fontSize: "0.7rem",
  fontWeight: 700,
  letterSpacing: "0.03em",
  display: "inline-block",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return <span style={{ ...BASE, ...STYLES[verdict] }}>{LABELS[verdict]}</span>;
}
