import type { CalculationRunStatus, LibraryStatus } from "@/types/api";
import clsx from "clsx";

type Status = CalculationRunStatus | LibraryStatus;

const STATUS_STYLES: Record<string, string> = {
  // Calculation run statuses
  COMPLETED: "badge-success",
  CONVERGED: "badge-success",
  APPROVED: "badge-success",
  RUNNING: "badge-info",
  VALIDATING: "badge-info",
  PENDING: "badge-info",
  UNDER_REVIEW: "badge-info",
  ENGINE_NOT_IMPLEMENTED: "badge-warning",
  DRAFT: "badge-neutral",
  FAILED: "badge-error",
  REJECTED: "badge-error",
  CANCELLED: "badge-neutral",
  SUPERSEDED: "badge-neutral",
  WITHDRAWN: "badge-error",
};

interface Props {
  status: Status;
  className?: string;
}

export function StatusBadge({ status, className }: Props) {
  const style = STATUS_STYLES[status] ?? "badge-neutral";
  return (
    <span
      className={clsx("badge", style, className)}
      style={BADGE_CSS[style]}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

const BADGE_CSS: Record<string, React.CSSProperties> = {
  "badge-success": {
    background: "#c6f6d5",
    color: "#276749",
    border: "1px solid #9ae6b4",
    padding: "2px 8px",
    borderRadius: "9999px",
    fontSize: "0.7rem",
    fontWeight: 600,
    letterSpacing: "0.03em",
    display: "inline-block",
  },
  "badge-info": {
    background: "#bee3f8",
    color: "#2a4365",
    border: "1px solid #90cdf4",
    padding: "2px 8px",
    borderRadius: "9999px",
    fontSize: "0.7rem",
    fontWeight: 600,
    letterSpacing: "0.03em",
    display: "inline-block",
  },
  "badge-warning": {
    background: "#fefcbf",
    color: "#744210",
    border: "1px solid #faf089",
    padding: "2px 8px",
    borderRadius: "9999px",
    fontSize: "0.7rem",
    fontWeight: 600,
    letterSpacing: "0.03em",
    display: "inline-block",
  },
  "badge-error": {
    background: "#fed7d7",
    color: "#742a2a",
    border: "1px solid #fc8181",
    padding: "2px 8px",
    borderRadius: "9999px",
    fontSize: "0.7rem",
    fontWeight: 600,
    letterSpacing: "0.03em",
    display: "inline-block",
  },
  "badge-neutral": {
    background: "#edf2f7",
    color: "#4a5568",
    border: "1px solid #e2e8f0",
    padding: "2px 8px",
    borderRadius: "9999px",
    fontSize: "0.7rem",
    fontWeight: 600,
    letterSpacing: "0.03em",
    display: "inline-block",
  },
};
