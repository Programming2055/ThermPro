import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { calculationRunsApi, projectsApi } from "@/api/client";
import type { Project } from "@/types/api";
import { buildInputSnapshot, DEFAULT_FORM, FACES, validateForm } from "@/lib/calculationInput";
import type {
  CalculationForm,
  DataConfidence,
  DeviceForm,
  Face,
  ThermalModel,
} from "@/lib/calculationInput";
import styles from "./CalculationPages.module.css";

const NEW_DEVICE: DeviceForm = {
  name: "",
  loadCurrentA: 100,
  ratedCurrentA: 160,
  powerAtRatedW: 60,
  thermalModel: "QUADRATIC",
  dataConfidence: "MEDIUM",
};

export function NewCalculationPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [form, setForm] = useState<CalculationForm>(DEFAULT_FORM);
  const [problems, setProblems] = useState<string[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    projectsApi
      .list(1, 100)
      .then((r) => {
        setProjects(r.items);
        setProjectId((cur) => cur || r.items[0]?.id || "");
      })
      .catch((e: unknown) =>
        setSubmitError(e instanceof Error ? e.message : "Failed to load projects")
      );
  }, []);

  const num =
    <K extends keyof CalculationForm>(key: K) =>
    (e: { target: { value: string } }) =>
      setForm((f) => ({ ...f, [key]: Number(e.target.value) }));

  const setDevice = (i: number, patch: Partial<DeviceForm>) =>
    setForm((f) => ({
      ...f,
      devices: f.devices.map((d, j) => (j === i ? { ...d, ...patch } : d)),
    }));

  const toggleFace = (face: Face) =>
    setForm((f) => ({
      ...f,
      restricted: f.restricted.includes(face)
        ? f.restricted.filter((x) => x !== face)
        : [...f.restricted, face],
    }));

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    const found = validateForm(form);
    if (!projectId) found.unshift("Select a project (create one first).");
    setProblems(found);
    if (found.length > 0) return;
    setSubmitting(true);
    try {
      const run = await calculationRunsApi.submit(projectId, buildInputSnapshot(form));
      navigate(`/calculation-runs/${run.id}`);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className={styles.page} onSubmit={onSubmit} noValidate>
      <h1 className={styles.heading}>New Calculation</h1>
      <p className={styles.sub}>
        MODE 2 — zonal steady-state thermal model, natural convection and radiation. Device losses
        are entered inline; no library release is pinned.
      </p>

      {problems.length > 0 && (
        <div className={styles.problems} role="alert" data-testid="form-problems">
          Please fix:
          <ul>
            {problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </div>
      )}
      {submitError && (
        <div className={styles.problems} role="alert" data-testid="submit-error">
          {submitError}
        </div>
      )}

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Project</h2>
        <div className={styles.field}>
          <label htmlFor="project">Project</label>
          <select id="project" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            {projects.length === 0 && <option value="">No projects</option>}
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {projects.length === 0 && <Link to="/projects/new">Create a project</Link>}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Enclosure</h2>
        <div className={styles.grid}>
          <Num
            id="height"
            label="External height [m]"
            value={form.heightM}
            onChange={num("heightM")}
          />
          <Num id="width" label="External width [m]" value={form.widthM} onChange={num("widthM")} />
          <Num id="depth" label="External depth [m]" value={form.depthM} onChange={num("depthM")} />
          <Num
            id="wall-thickness"
            label="Wall thickness [m]"
            value={form.wallThicknessM}
            onChange={num("wallThicknessM")}
            step="0.001"
          />
          <Num
            id="wall-k"
            label="Wall conductivity [W/(m·K)]"
            value={form.wallConductivity}
            onChange={num("wallConductivity")}
          />
          <Num
            id="emissivity"
            label="Surface emissivity [-]"
            value={form.emissivity}
            onChange={num("emissivity")}
            step="0.05"
          />
        </div>
        <fieldset className={styles.checks} style={{ border: 0, padding: 0, marginTop: "0.75rem" }}>
          <legend className={styles.kvLabel}>Faces that cannot exchange heat (adiabatic)</legend>
          {FACES.map((face) => (
            <label key={face}>
              <input
                type="checkbox"
                checked={form.restricted.includes(face)}
                onChange={() => toggleFace(face)}
              />{" "}
              {face}
            </label>
          ))}
        </fieldset>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Service conditions</h2>
        <div className={styles.grid}>
          <Num
            id="ambient-max"
            label="Max ambient [°C]"
            value={form.ambientMaxC}
            onChange={num("ambientMaxC")}
          />
          <Num
            id="ambient-avg"
            label="24 h average ambient [°C]"
            value={form.ambientAvgC}
            onChange={num("ambientAvgC")}
          />
          <Num
            id="humidity"
            label="Max relative humidity [%]"
            value={form.humidityPercent}
            onChange={num("humidityPercent")}
          />
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Devices (heat sources)</h2>
        {form.devices.map((d, i) => (
          <div key={i} className={styles.deviceRow} data-testid="device-row">
            <div className={styles.field}>
              <label htmlFor={`dev-name-${i}`}>Name</label>
              <input
                id={`dev-name-${i}`}
                value={d.name}
                onChange={(e) => setDevice(i, { name: e.target.value })}
              />
            </div>
            <Num
              id={`dev-load-${i}`}
              label="Load [A]"
              value={d.loadCurrentA}
              onChange={(e) => setDevice(i, { loadCurrentA: Number(e.target.value) })}
            />
            <Num
              id={`dev-rated-${i}`}
              label="Rated [A]"
              value={d.ratedCurrentA}
              onChange={(e) => setDevice(i, { ratedCurrentA: Number(e.target.value) })}
            />
            <Num
              id={`dev-power-${i}`}
              label="Loss at rated [W]"
              value={d.powerAtRatedW}
              onChange={(e) => setDevice(i, { powerAtRatedW: Number(e.target.value) })}
            />
            <div className={styles.field}>
              <label htmlFor={`dev-model-${i}`}>Loss model</label>
              <select
                id={`dev-model-${i}`}
                value={d.thermalModel}
                onChange={(e) => setDevice(i, { thermalModel: e.target.value as ThermalModel })}
              >
                <option value="QUADRATIC">Quadratic (I²)</option>
                <option value="LINEAR">Linear</option>
                <option value="FIXED_POWER">Fixed</option>
              </select>
            </div>
            <div className={styles.field}>
              <label htmlFor={`dev-conf-${i}`}>Data confidence</label>
              <select
                id={`dev-conf-${i}`}
                value={d.dataConfidence}
                onChange={(e) => setDevice(i, { dataConfidence: e.target.value as DataConfidence })}
              >
                {(["HIGH", "MEDIUM", "LOW", "UNKNOWN"] as const).map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className={styles.btnGhost}
              aria-label={`Remove device ${i + 1}`}
              onClick={() =>
                setForm((f) => ({ ...f, devices: f.devices.filter((_, j) => j !== i) }))
              }
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          className={styles.btnGhost}
          onClick={() => setForm((f) => ({ ...f, devices: [...f.devices, { ...NEW_DEVICE }] }))}
        >
          Add device
        </button>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Solver settings</h2>
        <div className={styles.grid}>
          <Num
            id="max-iter"
            label="Max iterations"
            value={form.maxIterations}
            onChange={num("maxIterations")}
          />
          <Num
            id="tolerance"
            label="Convergence tolerance [K]"
            value={form.toleranceK}
            onChange={num("toleranceK")}
            step="any"
          />
          <Num
            id="relaxation"
            label="Relaxation factor"
            value={form.relaxation}
            onChange={num("relaxation")}
            step="0.05"
          />
        </div>
      </section>

      <button type="submit" className={styles.btn} disabled={submitting}>
        {submitting ? "Running…" : "Run calculation"}
      </button>
    </form>
  );
}

interface NumProps {
  id: string;
  label: string;
  value: number;
  onChange: (e: { target: { value: string } }) => void;
  step?: string;
}

function Num({ id, label, value, onChange, step }: NumProps) {
  return (
    <div className={styles.field}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="number"
        step={step ?? "any"}
        value={Number.isFinite(value) ? value : ""}
        onChange={onChange}
      />
    </div>
  );
}
