import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { projectsApi } from "@/api/client";
import type { Project } from "@/types/api";
import styles from "./ListPage.module.css";

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    projectsApi
      .list()
      .then((r) => {
        setProjects(r.items);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load projects");
        setLoading(false);
      });
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.heading}>Projects</h1>
        <Link to="/projects/new" className={styles.primaryBtn}>
          New Project
        </Link>
      </div>

      {loading && <p className={styles.message}>Loading…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && projects.length === 0 && (
        <p className={styles.message}>No projects yet. Create your first project.</p>
      )}

      {projects.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Description</th>
              <th>Standard Profile</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td className={styles.nameCell}>{p.name}</td>
                <td className={styles.descCell}>{p.description ?? "—"}</td>
                <td>
                  <code className={styles.code}>{p.standard_profile}</code>
                </td>
                <td className={styles.dateCell}>
                  {new Date(p.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
