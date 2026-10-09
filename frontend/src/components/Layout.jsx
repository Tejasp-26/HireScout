import { Briefcase, LayoutDashboard, LogOut, Search, Sparkles, UploadCloud, Users } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../lib/auth";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/candidates", label: "Candidates", icon: Users },
  { to: "/jobs", label: "Jobs & Matching", icon: Briefcase },
  { to: "/import", label: "Import Resumes", icon: UploadCloud },
  { to: "/assistant", label: "AI Assistant", icon: Sparkles },
];

export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white">
        <Search size={18} strokeWidth={2.5} />
      </div>
      <div className="leading-tight">
        <div className="text-lg font-bold tracking-tight">HireScout</div>
        <div className="text-xs text-slate-500">AI resume screening</div>
      </div>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 whitespace-nowrap rounded-xl px-3 py-2.5 text-sm font-medium transition ${
      isActive ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
    }`;

  return (
    <div className="min-h-screen md:flex">
      <aside className="border-b border-slate-200 bg-white md:sticky md:top-0 md:flex md:h-screen md:w-64 md:flex-col md:border-b-0 md:border-r">
        <div className="flex items-center justify-between px-4 py-4 md:px-5 md:py-6">
          <Logo />
          <button onClick={handleLogout} className="text-slate-500 md:hidden" aria-label="Log out">
            <LogOut size={18} />
          </button>
        </div>

        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col md:pb-0">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={linkClass}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden border-t border-slate-200 p-4 md:block">
          <div className="text-sm font-semibold">{user?.name}</div>
          <div className="text-xs capitalize text-slate-500">{user?.role}</div>
          <button onClick={handleLogout} className="mt-3 flex items-center gap-2 text-sm text-slate-500 hover:text-red-600">
            <LogOut size={16} /> Log out
          </button>
        </div>
      </aside>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8 md:py-8">
        <Outlet />
      </main>
    </div>
  );
}
