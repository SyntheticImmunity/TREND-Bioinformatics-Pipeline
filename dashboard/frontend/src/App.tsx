import { Routes, Route, NavLink, Outlet } from "react-router-dom";
import { cn } from "@/lib/cn";

import Home from "@/pages/Home";
import Library from "@/pages/Library";
import ConstructDetail from "@/pages/ConstructDetail";
import Run from "@/pages/Run";
import RunExample from "@/pages/RunExample";
import Results from "@/pages/Results";
import Project from "@/pages/Project";
import Glossary from "@/pages/Glossary";
import Health from "@/pages/Health";

const NAV: { to: string; label: string }[] = [
  { to: "/library", label: "Library" },
  { to: "/run", label: "Pipeline" },
  { to: "/run/example", label: "Verify" },
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
                end={item.to === "/run"}
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

      <footer className="border-t border-cream-border mt-22">
        <div className="mx-auto max-w-[1200px] px-6 py-8 text-sm text-muted">
          TREND · MIT licensed
        </div>
      </footer>
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
        <Route path="/run" element={<Run />} />
        <Route path="/run/example" element={<RunExample />} />
        <Route path="/results" element={<Results />} />
        <Route path="/project" element={<Project />} />
        <Route path="/glossary" element={<Glossary />} />
        <Route path="/health" element={<Health />} />
      </Route>
    </Routes>
  );
}
