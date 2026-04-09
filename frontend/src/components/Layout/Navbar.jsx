import { Menu, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { APP_ROUTES } from "../../utils/constants";
import ThemeToggle from "./ThemeToggle";

const Navbar = ({ showMenuButton = false, onMenuToggle }) => {
  const { isAuthenticated, user } = useAuth();

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg2/90 backdrop-blur">
      <div className="mx-auto flex h-[52px] max-w-[1400px] items-center justify-between px-4">
        <div className="flex items-center gap-2">
          {showMenuButton ? (
            <button
              type="button"
              onClick={onMenuToggle}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border bg-bg3 text-text md:hidden"
              aria-label="Open navigation"
            >
              <Menu size={16} />
            </button>
          ) : null}

          <Link to={APP_ROUTES.landing} className="inline-flex items-center gap-2 text-sm font-bold text-text">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-accent text-white">
              <ShieldCheck size={16} />
            </span>
            CodeScan AI
          </Link>
        </div>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          <span className="rounded-full border border-border bg-bg3 px-3 py-1 text-xs text-text2">
            {isAuthenticated ? user?.email || "Signed In" : "Guest"}
          </span>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
