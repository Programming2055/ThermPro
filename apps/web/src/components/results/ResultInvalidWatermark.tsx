import type { ReactNode } from "react";
import type { SolverStatus } from "@/types/api";
import styles from "./ResultInvalidWatermark.module.css";

interface Props {
  status: SolverStatus;
  failureReason: string | null;
  children: ReactNode;
}

const INVALID: Record<string, { title: string; detail: string }> = {
  NON_CONVERGED: {
    title: "RESULT INVALID — the solver did not converge",
    detail:
      "These temperatures did not settle within the iteration limit, so they " +
      "are not a solution to the thermal network. CR-ENG-005: they must not " +
      "be used for a compliance assessment, quoted in a report, or relied on " +
      "for a design decision. Re-run with a smaller relaxation factor or a " +
      "higher iteration limit, and check the input for an implausible load.",
  },
  FAILED: {
    title: "RESULT INVALID — the calculation did not run",
    detail:
      "The solver could not produce a temperature field. The reason is below; " +
      "nothing on this page is a thermal result.",
  },
  CANCELLED: {
    title: "RESULT INVALID — the calculation was cancelled",
    detail: "The run was stopped before it finished. No result was produced.",
  },
};

/**
 * Wraps a result in the CR-ENG-005 "RESULT INVALID" treatment when the
 * solver did not converge.
 *
 * A converged result renders untouched: a watermark that appears on
 * everything teaches people to ignore it.
 */
export function ResultInvalidWatermark({ status, failureReason, children }: Props) {
  const invalid = INVALID[status];
  if (!invalid) {
    return <>{children}</>;
  }

  return (
    <div>
      <div className={styles.banner} role="alert">
        <span className={styles.icon} aria-hidden="true">
          ⚠
        </span>
        <div>
          <div className={styles.title}>{invalid.title}</div>
          <p className={styles.detail}>{invalid.detail}</p>
          {failureReason && (
            <p className={styles.detail}>
              <strong>Reported reason:</strong> {failureReason}
            </p>
          )}
        </div>
      </div>
      <div className={styles.overlay} data-watermark={"RESULT\nINVALID"}>
        {children}
      </div>
    </div>
  );
}
