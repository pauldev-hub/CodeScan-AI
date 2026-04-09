import { Moon, Sun } from "lucide-react";

import { useTheme } from "../../hooks/useTheme";

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="relative h-9 w-16 rounded-full border border-border bg-bg3 p-1"
      aria-label="Toggle theme"
    >
      <span
        className={`absolute top-1 h-7 w-7 rounded-full bg-bg2 shadow transition-transform [transition-duration:400ms] [transition-timing-function:cubic-bezier(0.4,0,0.2,1)] ${
          theme === "dark" ? "translate-x-7" : "translate-x-0"
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
