/**
 * Application state management using Zustand.
 *
 * Milestone 1: minimal store covering system status and navigation state.
 */
import { create } from "zustand";
import type { ReadinessResponse } from "@/types/api";

interface SystemState {
  readiness: ReadinessResponse | null;
  readinessCheckedAt: string | null;
  setReadiness: (r: ReadinessResponse) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  readiness: null,
  readinessCheckedAt: null,
  setReadiness: (r) =>
    set({ readiness: r, readinessCheckedAt: new Date().toISOString() }),
}));
