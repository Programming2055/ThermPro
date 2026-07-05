// Shared StatusBadge — re-exports from apps/web for package consumers.
// In a fully built monorepo this would be a standalone component with its own CSS.
export type { } from "./types";

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  COMPLETED: { background: "#c6f6d5", color: "#276749", border: "1px solid #9ae6b4" },
  CONVERGED: { background: "#c6f6d5", color: "#276749", border: "1px solid #9ae6b4" },
  APPROVED: { background: "#c6f6d5", color: "#276749", border: "1px solid #9ae6b4" },
  RUNNING: { background: "#bee3f8", color: "#2a4365", border: "1px solid #90cdf4" },
  PENDING: { background: "#bee3f8", color: "#2a4365", border: "1px solid #90cdf4" },
  UNDER_REVIEW: { background: "#bee3f8", color: "#2a4365", border: "1px solid #90cdf4" },
  FAILED: { background: "#fed7d7", color: "#742a2a", border: "1px solid #fc8181" },
  REJECTED: { background: "#fed7d7", color: "#742a2a", border: "1px solid #fc8181" },
  ENGINE_NOT_IMPLEMENTED: { background: "#fefcbf", color: "#744210", border: "1px solid #faf089" },
};

const BASE: React.CSSProperties = {
  padding: "2px 8px",
  borderRadius: "9999px",
  fontSize: "0.7rem",
  fontWeight: 600,
  letterSpacing: "0.03em",
  display: "inline-block",
  background: "#edf2f7",
  color: "#4a5568",
  border: "1px solid #e2e8f0",
};

interface Props {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: Props) {
  return (
    <span
      className={className}
      style={{ ...BASE, ...(STATUS_STYLES[status] ?? {}) }}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
