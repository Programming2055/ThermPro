import { useEffect, useState } from "react";
import { libraryReleasesApi } from "@/api/client";
import type { LibraryRelease } from "@/types/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import styles from "./ListPage.module.css";

export function LibraryReleasesPage() {
  const [releases, setReleases] = useState<LibraryRelease[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    libraryReleasesApi
      .list()
      .then((r) => {
        setReleases(r.items);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load library releases");
        setLoading(false);
      });
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.heading}>Library Releases</h1>
      </div>
      <p className={styles.sub}>
        Immutable versioned engineering data libraries. Approved releases cannot be modified —
        corrections require a new release with a new semantic version (DR-002).
      </p>

      {loading && <p className={styles.message}>Loading…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && releases.length === 0 && (
        <p className={styles.message}>No library releases. Import a dataset to create one.</p>
      )}

      {releases.length > 0 && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Version</th>
              <th>Status</th>
              <th>SHA-256</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {releases.map((r) => (
              <tr key={r.id}>
                <td className={styles.nameCell}>{r.library_name}</td>
                <td>
                  <code className={styles.code}>{r.version}</code>
                </td>
                <td>
                  <StatusBadge status={r.status} />
                </td>
                <td>
                  <code className={styles.hash} title={r.content_hash_sha256 ?? ""}>
                    {r.content_hash_sha256 ? r.content_hash_sha256.slice(0, 12) + "…" : "—"}
                  </code>
                </td>
                <td className={styles.dateCell}>
                  {new Date(r.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
