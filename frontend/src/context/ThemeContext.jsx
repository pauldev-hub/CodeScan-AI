import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { THEME_STORAGE_KEY } from "../utils/constants";

const ThemeContext = createContext(null);

const getSystemTheme = () => {
  if (typeof window === "undefined" || !window.matchMedia) {
    return "light";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};

const getInitialTheme = () => {
  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  if (savedTheme === "light" || savedTheme === "dark") {
    return savedTheme;
  }
  return getSystemTheme();
};

const hasManualThemeChoice = () => {
  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
  return savedTheme === "light" || savedTheme === "dark";
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(getInitialTheme);
  const [manualChoice, setManualChoice] = useState(hasManualThemeChoice);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    if (manualChoice) {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } else {
      localStorage.removeItem(THEME_STORAGE_KEY);
    }
  }, [manualChoice, theme]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = (event) => {
      if (!manualChoice) {
        setTheme(event.matches ? "dark" : "light");
      }
    };

    mediaQuery.addEventListener("change", onChange);
    return () => mediaQuery.removeEventListener("change", onChange);
  }, [manualChoice]);

  const toggleTheme = useCallback(() => {
    setManualChoice(true);
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  const setThemePreference = useCallback((nextTheme) => {
    if (nextTheme !== "light" && nextTheme !== "dark") {
      return;
    }
    setManualChoice(true);
    setTheme(nextTheme);
  }, []);

  const value = useMemo(
    () => ({ theme, isDark: theme === "dark", setTheme: setThemePreference, toggleTheme, manualChoice }),
    [manualChoice, setThemePreference, theme, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useThemeContext = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useThemeContext must be used inside ThemeProvider");
  }
  return context;
};
