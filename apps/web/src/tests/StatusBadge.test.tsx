import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "@/components/ui/StatusBadge";

describe("StatusBadge", () => {
  it("renders COMPLETED with success style", () => {
    render(<StatusBadge status="COMPLETED" />);
    const badge = screen.getByText("COMPLETED");
    expect(badge).toBeInTheDocument();
  });

  it("renders ENGINE_NOT_IMPLEMENTED with neutral style", () => {
    render(<StatusBadge status="ENGINE_NOT_IMPLEMENTED" />);
    expect(screen.getByText("ENGINE NOT IMPLEMENTED")).toBeInTheDocument();
  });

  it("renders FAILED with error style", () => {
    render(<StatusBadge status="FAILED" />);
    expect(screen.getByText("FAILED")).toBeInTheDocument();
  });

  it("renders APPROVED with success style", () => {
    render(<StatusBadge status="APPROVED" />);
    expect(screen.getByText("APPROVED")).toBeInTheDocument();
  });

  it("renders UNDER_REVIEW with info style", () => {
    render(<StatusBadge status="UNDER_REVIEW" />);
    expect(screen.getByText("UNDER REVIEW")).toBeInTheDocument();
  });

  it("replaces underscores with spaces in label", () => {
    render(<StatusBadge status="ENGINE_NOT_IMPLEMENTED" />);
    expect(screen.getByText("ENGINE NOT IMPLEMENTED")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<StatusBadge status="RUNNING" className="my-class" />);
    expect(container.firstChild).toHaveClass("my-class");
  });
});
