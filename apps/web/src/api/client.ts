/**
 * Type-safe API client for the ThermPro backend.
 *
 * All requests go to /api/v1 (proxied to the backend in development).
 * Error responses follow the M0-02 error shape.
 */
import type {
  Project,
  CreateProjectRequest,
  LibraryRelease,
  CreateLibraryReleaseRequest,
  DatasetManifest,
  LibraryManifest,
  CalculationRun,
  CalculationArtifact,
  PaginatedResponse,
  HealthResponse,
  ReadinessResponse,
} from "@/types/api";

const BASE_URL = "/api/v1";

class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: Array<{ field: string; issue: string }>
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // In production this would attach the JWT from the auth store.
  // For M1 development, the backend uses DevAuthProvider (no token needed).

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let errorData: { error?: { code?: string; message?: string; details?: Array<{ field: string; issue: string }> } } = {};
    try {
      errorData = await response.json() as typeof errorData;
    } catch {
      // ignore parse error
    }
    throw new ApiClientError(
      response.status,
      errorData.error?.code ?? "UNKNOWN_ERROR",
      errorData.error?.message ?? `HTTP ${response.status}`,
      errorData.error?.details
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

const get = <T>(path: string) => request<T>("GET", path);
const post = <T>(path: string, body: unknown) => request<T>("POST", path, body);

// ─── Health ──────────────────────────────────────────────────────────────────

export const healthApi = {
  health: () => get<HealthResponse>("/health"),
  ready: () => get<ReadinessResponse>("/ready"),
};

// ─── Projects ────────────────────────────────────────────────────────────────

export const projectsApi = {
  list: (page = 1, pageSize = 20) =>
    get<PaginatedResponse<Project>>(`/projects?page=${page}&page_size=${pageSize}`),

  get: (id: string) => get<Project>(`/projects/${id}`),

  create: (data: CreateProjectRequest) => post<Project>("/projects", data),
};

// ─── Library releases ────────────────────────────────────────────────────────

export const libraryReleasesApi = {
  list: (page = 1, pageSize = 20) =>
    get<PaginatedResponse<LibraryRelease>>(
      `/library-releases?page=${page}&page_size=${pageSize}`
    ),

  get: (id: string) => get<LibraryRelease>(`/library-releases/${id}`),

  create: (data: CreateLibraryReleaseRequest) =>
    post<LibraryRelease>("/library-releases", data),
};

// ─── Dataset manifests ───────────────────────────────────────────────────────

export const datasetManifestsApi = {
  create: (libraryManifest: LibraryManifest) =>
    post<DatasetManifest>("/dataset-manifests", { library_manifest: libraryManifest }),

  get: (id: string) => get<DatasetManifest>(`/dataset-manifests/${id}`),
};

// ─── Calculation runs ────────────────────────────────────────────────────────

export const calculationRunsApi = {
  list: (page = 1, pageSize = 20) =>
    get<PaginatedResponse<CalculationRun>>(
      `/calculation-runs?page=${page}&page_size=${pageSize}`
    ),

  get: (id: string) => get<CalculationRun>(`/calculation-runs/${id}`),

  submit: (inputSnapshot: Record<string, unknown>) =>
    post<CalculationRun>("/calculation-runs", inputSnapshot),
};

// ─── Artifacts ───────────────────────────────────────────────────────────────

export const artifactsApi = {
  upload: (runId: string, formData: FormData) =>
    fetch(`${BASE_URL}/calculation-runs/${runId}/artifacts`, {
      method: "POST",
      body: formData,
    }).then((r) => r.json() as Promise<CalculationArtifact>),

  get: (id: string) => get<CalculationArtifact>(`/artifacts/${id}`),
};

export { ApiClientError };
