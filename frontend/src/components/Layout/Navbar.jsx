import { LogOut, Menu, Settings, ShieldCheck, Sparkles } from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { APP_ROUTES } from "../../utils/constants";
import ThemeToggle from "./ThemeToggle";

const Navbar = ({ showMenuButton = false, onMenuToggle }) => {
  const { isAuthenticated, user, enterGuestMode, loading, signOut } = useAuth();
  const navigate = useNavigate();

  const onLogout = async () => {
    await signOut();
    navigate(APP_ROUTES.landing, { replace: true });
  };

  const onGuestClick = async () => {
    if (isAuthenticated || loading) {
      return;
    }
    try {
      await enterGuestMode();
      navigate(APP_ROUTES.dashboard, { replace: true });
    } catch {
      // Keep current view when guest session bootstrap fails.
    }
  };

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-[color:var(--panel)] backdrop-blur-xl">
      <div className="mx-auto flex h-[60px] w-[min(1880px,calc(100vw-24px))] items-center justify-between px-3 md:px-4">
        <div className="flex items-center gap-2">
          {showMenuButton ? (
            <button
              type="button"
              onClick={onMenuToggle}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-bg3 text-text md:hidden"
              aria-label="Open navigation"
            >
              <Menu size={16} />
            </button>
          ) : null}

          <Link to={APP_ROUTES.landing} className="inline-flex items-center gap-3 text-sm font-bold text-text">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,var(--accent),var(--accent-2))] text-[#24150c] shadow-[0_14px_24px_rgba(214,161,108,0.22)]">
              <ShieldCheck size={16} />
            </span>
            <span>
              <span className="block text-[13px] uppercase tracking-[0.22em] text-text3">Workspace</span>
              <span className="block text-sm text-text">CodeScan AI</span>
            </span>
          </Link>
        </div>

        <div className="flex items-center gap-3">
          <nav className="hidden items-center gap-2 lg:flex">
            {isAuthenticated ? (
              <>
                <NavLink to={APP_ROUTES.dashboard} className="rounded-full px-3 py-2 text-sm text-text2 transition-colors hover:bg-bg3 hover:text-text">
                  Dashboard
                </NavLink>
                <NavLink to={APP_ROUTES.scan} className="rounded-full px-3 py-2 text-sm text-text2 transition-colors hover:bg-bg3 hover:text-text">
                  Scan
                </NavLink>
                <NavLink to={APP_ROUTES.activity} className="rounded-full px-3 py-2 text-sm text-text2 transition-colors hover:bg-bg3 hover:text-text">
                  Activity
                </NavLink>
                <NavLink to={APP_ROUTES.chat} className="rounded-full px-3 py-2 text-sm text-text2 transition-colors hover:bg-bg3 hover:text-text">
                  DevChat
                </NavLink>
                <NavLink to={APP_ROUTES.settings} className="rounded-full px-3 py-2 text-sm text-text2 transition-colors hover:bg-bg3 hover:text-text">
                  Settings
                </NavLink>
              </>
            ) : (
              <>
                <NavLink to={APP_ROUTES.login} className="rounded-full px-3 py-2 text-sm text-text2 transition-colors hover:bg-bg3 hover:text-text">
                  Login
                </NavLink>
                <NavLink to={APP_ROUTES.signup} className="inline-flex items-center gap-2 rounded-full border border-border bg-bg3 px-3 py-2 text-sm text-text transition-colors hover:border-[color:var(--border-strong)]">
                  <Sparkles size={14} className="text-accent" />
                  Create account
                </NavLink>
              </>
            )}
          </nav>
          <ThemeToggle />
          {isAuthenticated ? (
            <span className="rounded-full border border-border bg-bg3 px-3 py-1.5 text-xs text-text2">
              {user?.email || "Signed In"}
            </span>
          ) : (
            <button
              type="button"
              onClick={onGuestClick}
              disabled={loading}
              className="rounded-full border border-border bg-bg3 px-3 py-1.5 text-xs text-text2 transition-colors hover:border-[color:var(--border-strong)] hover:text-text disabled:cursor-not-allowed disabled:opacity-60"
            >
              Continue as Guest
            </button>
          )}
          {isAuthenticated ? (
            <>
              <Link
                to={APP_ROUTES.settings}
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-bg3 text-text"
                aria-label="Settings"
              >
                <Settings size={14} />
              </Link>
              <button
                type="button"
                onClick={onLogout}
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-bg3 text-text"
                aria-label="Logout"
              >
                <LogOut size={14} />
              </button>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
};

export default Navbar;
