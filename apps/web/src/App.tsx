import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { CreateProjectPage } from "@/pages/CreateProjectPage";
import { LibraryReleasesPage } from "@/pages/LibraryReleasesPage";
import { CalculationRunsPage } from "@/pages/CalculationRunsPage";
import { HealthPage } from "@/pages/HealthPage";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/new" element={<CreateProjectPage />} />
        <Route path="/library-releases" element={<LibraryReleasesPage />} />
        <Route path="/calculation-runs" element={<CalculationRunsPage />} />
        <Route path="/health" element={<HealthPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
