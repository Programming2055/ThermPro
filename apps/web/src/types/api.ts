/**
 * TypeScript types aligned with the M0-03 / M0-04 JSON schemas
 * and the API contract defined in M0-02.
 *
 * Fan states per DR-005: six states, canonical names.
 * Standards profiles: MVP scope only (DR-007).
 * No ARC_FLASH mode (DR-008).
 */

// ─── Enums ──────────────────────────────────────────────────────────────────

export type CalculationMode = "MODE_1" | "MODE_2" | "MODE_3" | "MODE_4";

export type StandardProfile =
  | "IEC_61439_1"
  | "IEC_61439_2"
  | "IEC_TR_60890"
  | "MANUFACTURER_LIMITS"
  | "PROJECT_DEFINED";

/** Fan operating states per DR-005. Six states replace the previous boolean. */
export type FanOperatingState =
  | "RUNNING_FORWARD"
  | "STOPPED_FREE_FLOW"
  | "STOPPED_WITH_DAMPER"
  | "FAILED_OPEN"
  | "FAILED_BLOCKED"
  | "REVERSE_FLOW_ESTIMATED";

/** Busbar joint condition per DR-004. UNKNOWN requires sensitivity scenarios. */
export type JointCondition =
  | "NEW_VALIDATED"
  | "NEW_ASSUMED"
  | "MEASURED"
  | "AGED"
  | "DEGRADED"
  | "UNKNOWN";

export type ContactResistanceSource =
  | "MEASURED"
  | "MANUFACTURER"
  | "JOINT_LIBRARY"
  | "USER_ASSUMPTION";

export type KAcSource =
  | "MANUFACTURER"
  | "VALIDATED_CORRELATION"
  | "GEOMETRY_FREQUENCY_LIBRARY"
  | "USER_INPUT"
  | "NOT_APPLIED";

export type LibraryStatus =
  | "DRAFT"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "SUPERSEDED"
  | "WITHDRAWN";

export type CalculationRunStatus =
  | "DRAFT"
  | "VALIDATING"
  | "REJECTED"
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "ENGINE_NOT_IMPLEMENTED";

// ─── Library manifest ────────────────────────────────────────────────────────

export interface LibraryPin {
  name: string;
  version: string;
  content_hash_sha256: string;
}

export interface LibraryManifest {
  material_library?: LibraryPin;
  device_library?: LibraryPin;
  conductor_library?: LibraryPin;
  ventilation_device_library?: LibraryPin;
  iec60890_coefficient_library?: LibraryPin;
  busbar_joint_library?: LibraryPin;
  ac_resistance_library?: LibraryPin;
}

// ─── API response types ──────────────────────────────────────────────────────

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Array<{ field: string; issue: string }>;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Project ─────────────────────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  is_archived: boolean;
  /** Standard profile is stored on the project for UI display; aligns with M0-02. */
  standard_profile?: StandardProfile;
  created_at: string;
  updated_at?: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  standard_profile?: StandardProfile;
}

// ─── Library releases ────────────────────────────────────────────────────────

export interface LibraryRelease {
  id: string;
  library_name: string;
  version: string;
  status: LibraryStatus;
  content_hash_sha256: string;
  description: string | null;
  created_at: string | null;
}

export interface CreateLibraryReleaseRequest {
  library_name: string;
  version: string;
  entries: Record<string, unknown>[];
  description?: string;
}

// ─── Dataset manifest ────────────────────────────────────────────────────────

export interface DatasetManifest {
  id: string;
  library_manifest: LibraryManifest;
  created_at: string;
}

// ─── Calculation runs ────────────────────────────────────────────────────────

export interface CalculationRun {
  id: string;
  project_id: string;
  status: CalculationRunStatus;
  mode: CalculationMode;
  schema_version: string;
  input_checksum_sha256: string;
  rejection_reason: string | null;
  submitted_at: string;
  completed_at: string | null;
}

// ─── Artifacts ───────────────────────────────────────────────────────────────

export type ArtifactType =
  | "REPORT_PDF"
  | "REPORT_XLSX"
  | "TEST_IMPORT"
  | "CAD_FILE"
  | "SCREENSHOT"
  | "THERMAL_FIELD"
  | "CFD_PACKAGE"
  | "LARGE_TRACE";

export interface CalculationArtifact {
  id: string;
  calculation_run_id: string;
  artifact_type: ArtifactType;
  object_key: string;
  content_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  created_at: string;
}

// ─── Health ──────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  service: string;
}

export interface ReadinessResponse {
  status: string;
  checks: Record<string, string>;
}
