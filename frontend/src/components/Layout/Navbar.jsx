import { Menu, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { APP_ROUTES } from "../../utils/constants";
import ThemeToggle from "./ThemeToggle";

const Navbar = ({ showMenuButton = false, onMenuToggle }) => {
  const { isAuthenticated, user } = useAuth();

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
          <ThemeToggle />
          <span className="rounded-full border border-border bg-bg3 px-3 py-1.5 text-xs text-text2">
            {isAuthenticated ? user?.email || "Signed In" : "Guest"}
          </span>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
