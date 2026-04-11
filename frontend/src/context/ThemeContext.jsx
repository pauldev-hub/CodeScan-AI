import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { THEME_STORAGE_KEY } from "../utils/constants";

const ThemeContext = createContext(null);

const getInitialTheme = () => "dark";
const hasManualThemeChoice = () => true;

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(getInitialTheme);
  const [manualChoice, setManualChoice] = useState(hasManualThemeChoice);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
  }, [manualChoice, theme]);

  useEffect(() => {
    setTheme("dark");
    return undefined;
  }, [manualChoice]);

  const toggleTheme = useCallback(() => {
    setManualChoice(true);
    setTheme("dark");
  }, []);

  const setThemePreference = useCallback((_nextTheme) => {
    setManualChoice(true);
    setTheme("dark");
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
