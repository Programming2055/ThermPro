import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import styles from "./AppShell.module.css";

interface Props {
  children: ReactNode;
}

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/projects", label: "Projects" },
  { to: "/library-releases", label: "Libraries" },
  { to: "/calculation-runs", label: "Calculations" },
  { to: "/health", label: "Health" },
] as const;

export function AppShell({ children }: Props) {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandName}>ThermPro</span>
          <span className={styles.brandSub}>LV Thermal Twin</span>
        </div>
        <nav className={styles.nav}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={"end" in item ? item.end : false}
              className={({ isActive }) =>
                [styles.navItem, isActive ? styles.navItemActive : ""].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className={styles.footer}>
          <span className={styles.versionBadge}>M1 Foundation</span>
        </div>
      </aside>
      <main className={styles.main}>{children}</main>
    </div>
  );
}
