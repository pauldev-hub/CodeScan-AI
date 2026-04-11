import { MoonStar } from "lucide-react";

import { useTheme } from "../../hooks/useTheme";

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="inline-flex h-10 items-center gap-2 rounded-full border border-border bg-bg3 px-3 text-sm text-text2"
      aria-label="Dark mode enabled"
    >
      <MoonStar size={14} className="text-accent" />
      <span>{theme === "dark" ? "Dark" : "Dark"}</span>
    </button>
  );
};

export default ThemeToggle;
