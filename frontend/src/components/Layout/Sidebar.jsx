import { BarChart3, Home, MessageSquare, ScanLine, Settings, Trophy } from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { APP_ROUTES } from "../../utils/constants";

const links = [
  { label: "Dashboard", to: APP_ROUTES.dashboard, icon: Home },
  { label: "New Scan", to: APP_ROUTES.scan, icon: ScanLine },
  { label: "Activity", to: APP_ROUTES.activity, icon: BarChart3 },
  { label: "DevChat", to: APP_ROUTES.chat, icon: MessageSquare },
  { label: "Settings", to: APP_ROUTES.settings, icon: Settings },
];

const SidebarNav = ({ linksToRender, onNavigate }) => (
  <nav className="space-y-2">
    {linksToRender.map((link) => {
      const Icon = link.icon;
      return (
        <NavLink
          key={link.label}
          to={link.to}
          onClick={onNavigate}
          className={({ isActive }) =>
            `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
              isActive ? "bg-accent/15 text-accent" : "text-text2 hover:bg-bg3"
            }`
          }
        >
          <Icon size={16} />
          <span className="hidden xl:inline">{link.label}</span>
          <span className="xl:hidden md:hidden">{link.label}</span>
        </NavLink>
      );
    })}
  </nav>
);

const Sidebar = ({ mobileOpen = false, onClose }) => (
  <>
    <SidebarContent mobileOpen={mobileOpen} onClose={onClose} />
  </>
);

const SidebarContent = ({ mobileOpen, onClose }) => {
  const { user } = useAuth();
  const adminLinks = user?.role === "admin"
    ? [
        { label: "Admin", to: APP_ROUTES.admin, icon: Settings },
        { label: "Queue", to: APP_ROUTES.adminQueue, icon: BarChart3 },
        { label: "Incidents", to: APP_ROUTES.adminIncidents, icon: ScanLine },
      ]
    : [];
  const linksToRender = [...links, ...adminLinks];

  return (
    <>
      <aside className="hidden shrink-0 border-r border-border bg-[color:var(--panel)] p-4 md:block md:w-[84px] xl:w-[240px]">
        <div className="mb-4 rounded-[20px] border border-border bg-bg3/70 p-3 xl:p-4">
          <p className="text-[10px] uppercase tracking-[0.22em] text-text3">Operator</p>
          <p className="mt-2 text-sm font-semibold text-text">{user?.username || "Secure reviewer"}</p>
          <p className="mt-1 text-xs text-text2">{user?.plan || "free"} plan</p>
        </div>
        <div className="mb-4 rounded-[20px] border border-border bg-[linear-gradient(135deg,rgba(214,161,108,0.18),rgba(255,255,255,0.02))] p-3 xl:p-4">
          <div className="flex items-center gap-2 text-accent">
            <Trophy size={14} />
            <span className="text-[10px] uppercase tracking-[0.22em]">Momentum</span>
          </div>
          <p className="mt-3 text-sm font-semibold text-text">Keep your fix streak alive</p>
          <p className="mt-1 text-xs text-text2">Dashboard now tracks progress, score trends, and guided next actions.</p>
        </div>
        <SidebarNav linksToRender={linksToRender} />
      </aside>

      <div className={`fixed inset-0 z-40 md:hidden ${mobileOpen ? "" : "pointer-events-none"}`}>
        <button
          type="button"
          onClick={onClose}
          className={`absolute inset-0 bg-black/35 transition-opacity duration-300 ${mobileOpen ? "opacity-100" : "opacity-0"}`}
          aria-label="Close navigation"
        />
        <aside
          className={`absolute left-0 top-0 h-full w-[260px] border-r border-border bg-[color:var(--panel-strong)] p-4 shadow-xl transition-transform duration-300 ${
            mobileOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-text2">Navigation</p>
          <SidebarNav linksToRender={linksToRender} onNavigate={onClose} />
        </aside>
      </div>
    </>
  );
};

export default Sidebar;
