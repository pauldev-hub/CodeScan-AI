import { Moon, Sun } from "lucide-react";

import { useTheme } from "../../hooks/useTheme";

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="relative h-10 w-[74px] rounded-full border border-border bg-bg3 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
      aria-label="Toggle theme"
    >
      <span
        className={`absolute top-1 h-8 w-8 rounded-full bg-[linear-gradient(135deg,var(--accent),var(--accent-2))] shadow-[0_10px_18px_rgba(214,161,108,0.24)] transition-transform [transition-duration:400ms] [transition-timing-function:cubic-bezier(0.4,0,0.2,1)] ${
          theme === "dark" ? "translate-x-8" : "translate-x-0"
        }`}
      />
      <span className="relative z-10 flex h-full items-center justify-between px-1 text-text2">
        <Sun size={14} />
        <Moon size={14} />
      </span>
    </button>
  );
};

export default ThemeToggle;
