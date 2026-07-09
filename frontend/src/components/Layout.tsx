import { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../lib/store";

const NAV = [
  { to: "/apply", label: "New Assessment" },
  { to: "/portfolio", label: "Portfolio Heat Map" },
  { to: "/alerts", label: "Alert Feed" },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { role, username, logout } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 flex items-center h-20 gap-6">
          <NavLink to="/" className="shrink-0 mr-2 hover:opacity-90 transition-opacity">
            <img src="/logo.png" alt="IDBI Fin Logo" className="h-14 w-auto object-contain" />
          </NavLink>
          <nav className="flex gap-1 flex-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `px-3 py-1.5 rounded-lg text-sm font-medium ${
                    isActive ? "bg-idbi-teal/10 text-idbi-teal" : "text-slate-600 hover:bg-slate-100"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="text-sm text-slate-500">
            {username} · <span className="uppercase text-xs font-semibold">{role}</span>
          </div>
          <button className="btn-ghost text-sm" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
