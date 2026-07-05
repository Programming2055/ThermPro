import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { projectsApi } from "@/api/client";
import { StandardProfileSchema } from "@/types/schemas";
import styles from "./CreateProjectPage.module.css";

const CreateProjectSchema = z.object({
  name: z.string().min(1, "Name is required").max(200, "Name too long"),
  description: z.string().max(2000, "Description too long").optional(),
  standard_profile: StandardProfileSchema,
});

type FormValues = z.infer<typeof CreateProjectSchema>;

const STANDARD_PROFILE_LABELS: Record<string, string> = {
  IEC_61439_1: "IEC 61439-1",
  IEC_61439_2: "IEC 61439-2 (ASSEMBLIES)",
  IEC_TR_60890: "IEC TR 60890:2022 (Empirical)",
  MANUFACTURER_LIMITS: "Manufacturer Limits",
  PROJECT_DEFINED: "Project-Defined Limits",
};

export function CreateProjectPage() {
  const navigate = useNavigate();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(CreateProjectSchema),
    defaultValues: {
      standard_profile: "IEC_61439_2",
    },
  });

  const onSubmit = async (data: FormValues) => {
    setSubmitError(null);
    try {
      await projectsApi.create(data);
      navigate("/projects");
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : "Failed to create project");
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.breadcrumb}>
        <Link to="/projects" className={styles.breadcrumbLink}>Projects</Link>
        <span className={styles.breadcrumbSep}>/</span>
        <span>New Project</span>
      </div>
      <h1 className={styles.heading}>Create Project</h1>

      <form onSubmit={handleSubmit(onSubmit)} className={styles.form} noValidate>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="name">
            Project Name <span className={styles.required}>*</span>
          </label>
          <input
            id="name"
            className={`${styles.input} ${errors.name ? styles.inputError : ""}`}
            type="text"
            placeholder="e.g. MCC-A Thermal Analysis"
            {...register("name")}
          />
          {errors.name && (
            <span className={styles.fieldError}>{errors.name.message}</span>
          )}
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="description">
            Description
          </label>
          <textarea
            id="description"
            className={styles.textarea}
            rows={3}
            placeholder="Optional description"
            {...register("description")}
          />
          {errors.description && (
            <span className={styles.fieldError}>{errors.description.message}</span>
          )}
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="standard_profile">
            Standard Profile <span className={styles.required}>*</span>
          </label>
          <select
            id="standard_profile"
            className={`${styles.select} ${errors.standard_profile ? styles.inputError : ""}`}
            {...register("standard_profile")}
          >
            {Object.entries(STANDARD_PROFILE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          {errors.standard_profile && (
            <span className={styles.fieldError}>{errors.standard_profile.message}</span>
          )}
          <p className={styles.hint}>
            Determines applicability conditions, coefficient datasets, and report wording (DR-007).
          </p>
        </div>

        {submitError && <p className={styles.submitError}>{submitError}</p>}

        <div className={styles.actions}>
          <Link to="/projects" className={styles.cancelBtn}>
            Cancel
          </Link>
          <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
            {isSubmitting ? "Creating…" : "Create Project"}
          </button>
        </div>
      </form>
    </div>
  );
}
