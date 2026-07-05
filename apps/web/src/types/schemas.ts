/**
 * Zod schemas for API request/response validation.
 * Aligned with M0-03 / M0-04 JSON schemas and the TypeScript types in api.ts.
 */
import { z } from "zod";

// ─── Enums ──────────────────────────────────────────────────────────────────

export const CalculationModeSchema = z.enum(["MODE_1", "MODE_2", "MODE_3", "MODE_4"]);

export const StandardProfileSchema = z.enum([
  "IEC_61439_1",
  "IEC_61439_2",
  "IEC_TR_60890",
  "MANUFACTURER_LIMITS",
  "PROJECT_DEFINED",
]);

/** Fan operating states per DR-005. Six canonical values. */
export const FanOperatingStateSchema = z.enum([
  "RUNNING_FORWARD",
  "STOPPED_FREE_FLOW",
  "STOPPED_WITH_DAMPER",
  "FAILED_OPEN",
  "FAILED_BLOCKED",
  "REVERSE_FLOW_ESTIMATED",
]);

export const JointConditionSchema = z.enum([
  "NEW_VALIDATED",
  "NEW_ASSUMED",
  "MEASURED",
  "AGED",
  "DEGRADED",
  "UNKNOWN",
]);

export const ContactResistanceSourceSchema = z.enum([
  "MEASURED",
  "MANUFACTURER",
  "JOINT_LIBRARY",
  "USER_ASSUMPTION",
]);

export const KAcSourceSchema = z.enum([
  "MANUFACTURER",
  "VALIDATED_CORRELATION",
  "GEOMETRY_FREQUENCY_LIBRARY",
  "USER_INPUT",
  "NOT_APPLIED",
]);

export const LibraryStatusSchema = z.enum([
  "DRAFT",
  "UNDER_REVIEW",
  "APPROVED",
  "SUPERSEDED",
  "WITHDRAWN",
]);

export const CalculationRunStatusSchema = z.enum([
  "DRAFT",
  "VALIDATING",
  "REJECTED",
  "PENDING",
  "RUNNING",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
  "ENGINE_NOT_IMPLEMENTED",
]);

// ─── Library manifest ────────────────────────────────────────────────────────

export const LibraryPinSchema = z.object({
  name: z.string().min(1),
  version: z.string().regex(/^\d+\.\d+\.\d+$/, "Must be semantic version x.y.z"),
  content_hash_sha256: z.string().length(64, "Must be 64-char SHA-256 hex"),
});

export const LibraryManifestSchema = z.object({
  material_library: LibraryPinSchema.optional(),
  device_library: LibraryPinSchema.optional(),
  conductor_library: LibraryPinSchema.optional(),
  ventilation_device_library: LibraryPinSchema.optional(),
  iec60890_coefficient_library: LibraryPinSchema.optional(),
  busbar_joint_library: LibraryPinSchema.optional(),
  ac_resistance_library: LibraryPinSchema.optional(),
});

// ─── Project ─────────────────────────────────────────────────────────────────

export const CreateProjectSchema = z.object({
  name: z.string().min(1, "Project name is required").max(200),
  customer: z.string().max(200).optional(),
  assembly_designation: z.string().max(100).optional(),
  standard_profile: z
    .array(StandardProfileSchema)
    .min(1, "At least one standard profile required"),
  system_voltage_v: z.number().positive("System voltage must be positive"),
  frequency_hz: z.number().positive("Frequency must be positive"),
  indoor_outdoor: z.enum(["INDOOR", "OUTDOOR"]),
});

export type CreateProjectFormData = z.infer<typeof CreateProjectSchema>;

// ─── Library release ─────────────────────────────────────────────────────────

export const CreateLibraryReleaseSchema = z.object({
  library_name: z.string().min(1, "Library name required"),
  semantic_version: z
    .string()
    .regex(/^\d+\.\d+\.\d+$/, "Must be semantic version x.y.z"),
  effective_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Must be YYYY-MM-DD"),
  source_reference: z.string().min(1, "Source reference required"),
  entries: z.record(z.unknown()),
});

export type CreateLibraryReleaseFormData = z.infer<typeof CreateLibraryReleaseSchema>;
