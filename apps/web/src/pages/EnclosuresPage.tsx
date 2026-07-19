import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { enclosuresApi, projectsApi } from "@/api/client";
import type { Enclosure, Project } from "@/types/api";
import styles from "./ListPage.module.css";

export function EnclosuresPage() {
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("project_id");

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>(projectId ?? "");
  const [enclosures, setEnclosures] = useState<Enclosure[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    projectsApi.list().then((r) => setProjects(r.items)).catch(() => null);
  }, []);

  useEffect(() => {
    if (!selectedProject) {
      setEnclosures([]);
      return;
    }
    setLoading(true);
    setError(null);
    enclosuresApi
      .list(selectedProject)
      .then((items) => {
        setEnclosures(items);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load enclosures");
        setLoading(false);
      });
  }, [selectedProject]);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.heading}>Enclosures</h1>
        {selectedProject && (
          <Link
            to={`/enclosures/new?project_id=${selectedProject}`}
            className={styles.primaryBtn}
          >
            New Enclosure
          </Link>
        )}
      </div>

      <div style={{ marginBottom: "1.5rem" }}>
        <label htmlFor="project-select" style={{ marginRight: "0.5rem" }}>
          Project:
        </label>
        <select
          id="project-select"
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          style={{ padding: "0.25rem 0.5rem", borderRadius: "4px" }}
        >
          <option value="">— select a project —</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {loading && <p className={styles.message}>Loading…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && selectedProject && enclosures.length === 0 && (
        <p className={styles.message}>No enclosures in this project yet.</p>
      )}

      {enclosures.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Name</th>
              <th>External (W × H × D mm)</th>
              <th>Internal (W × H × D mm)</th>
              <th>Installation</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {enclosures.map((enc) => (
              <tr key={enc.id}>
                <td className={styles.nameCell}>{enc.name}</td>
                <td>
                  {Math.round(enc.external_width_m * 1000)} ×{" "}
                  {Math.round(enc.external_height_m * 1000)} ×{" "}
                  {Math.round(enc.external_depth_m * 1000)}
                </td>
                <td>
                  {Math.round(enc.internal_width_m * 1000)} ×{" "}
                  {Math.round(enc.internal_height_m * 1000)} ×{" "}
                  {Math.round(enc.internal_depth_m * 1000)}
                </td>
                <td>
                  <code className={styles.code}>{enc.installation_type}</code>
                </td>
                <td>
                  <Link to={`/enclosures/${enc.id}/edit`} style={{ fontSize: "0.85rem" }}>
                    Edit
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
