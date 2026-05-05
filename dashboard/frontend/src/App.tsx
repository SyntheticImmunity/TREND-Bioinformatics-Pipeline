import { Routes, Route, NavLink, Outlet, Navigate } from "react-router-dom";
import { cn } from "@/lib/cn";

import Home from "@/pages/Home";
import Library from "@/pages/Library";
import ConstructDetail from "@/pages/ConstructDetail";
import RunExample from "@/pages/RunExample";
import Results from "@/pages/Results";
import PwmDetail from "@/pages/PwmDetail";
import Project from "@/pages/Project";
import Glossary from "@/pages/Glossary";
import Health from "@/pages/Health";

const NAV: { to: string; label: string }[] = [
  { to: "/library", label: "Library" },
  { to: "/run/example", label: "Pipeline" },
  { to: "/results", label: "Results" },
  { to: "/project", label: "Projects" },
  { to: "/glossary", label: "Glossary" },
  { to: "/health", label: "System" },
];

function Layout() {
  return (
    <div className="min-h-dvh flex flex-col">
      <header className="sticky top-0 z-10 border-b border-cream-border bg-cream/95 backdrop-blur">
        <div className="mx-auto max-w-[1200px] px-6 py-4 flex items-center gap-8">
          <NavLink to="/" className="no-underline">
            <span className="text-card-title font-semibold tracking-tight text-charcoal">
              TREND
            </span>
            <span className="ml-2 text-sm text-muted">Dashboard</span>
          </NavLink>
          <nav className="flex items-center gap-1 text-sm">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    "no-underline px-3 py-1.5 rounded-standard transition-colors",
                    isActive
                      ? "bg-charcoal-4 text-charcoal"
                      : "text-charcoal-82 hover:bg-charcoal-3",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/library" element={<Library />} />
        <Route path="/library/:id" element={<ConstructDetail />} />
        <Route path="/run" element={<Navigate to="/run/example" replace />} />
        <Route path="/run/example" element={<RunExample />} />
        <Route path="/results" element={<Results />} />
        <Route path="/results/pwm/:pwmName" element={<PwmDetail />} />
        <Route path="/project" element={<Project />} />
        <Route path="/glossary" element={<Glossary />} />
        <Route path="/health" element={<Health />} />
      </Route>
    </Routes>
  );
}
