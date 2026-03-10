/**
 * Theme hook for dark / light Napoleon-era military styling.
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { ThemeColors } from "../types/cheats";

export type ThemeMode = "dark" | "light";

export interface NapoleonTheme {
  mode: ThemeMode;
  colors: ThemeColors;
  name: string;
}

const DEFAULT_THEMES: Record<string, ThemeColors> = {
  napoleon_gold: {
    primary: "#d4af37",
    secondary: "#f1c40f",
    background: "#1a252f",
    panel: "#2c3e50",
  },
  imperial_blue: {
    primary: "#3498db",
    secondary: "#2980b9",
    background: "#1a252f",
    panel: "#2c3e50",
  },
  royal_purple: {
    primary: "#9b59b6",
    secondary: "#8e44ad",
    background: "#1a252f",
    panel: "#2c3e50",
  },
  battlefield_steel: {
    primary: "#95a5a6",
    secondary: "#7f8c8d",
    background: "#1a252f",
    panel: "#2c3e50",
  },
  midnight_command: {
    primary: "#e74c3c",
    secondary: "#c0392b",
    background: "#0f1419",
    panel: "#1a252f",
  },
};

const LIGHT_OVERRIDES: Partial<ThemeColors> = {
  background: "#f5f0e8",
  panel: "#e8e0d0",
};

function resolveTheme(name: string, mode: ThemeMode): NapoleonTheme {
  const base = DEFAULT_THEMES[name] ?? DEFAULT_THEMES.napoleon_gold;
  const colors: ThemeColors =
    mode === "light" ? { ...base, ...LIGHT_OVERRIDES } : base;
  return { mode, colors, name };
}

interface ThemeContextValue {
  theme: NapoleonTheme;
  setThemeName: (name: string) => void;
  toggleMode: () => void;
  availableThemes: string[];
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({
  children,
  initialTheme = "napoleon_gold",
  initialMode = "dark",
}: {
  children: ReactNode;
  initialTheme?: string;
  initialMode?: ThemeMode;
}) {
  const [themeName, setName] = useState(initialTheme);
  const [mode, setMode] = useState<ThemeMode>(initialMode);

  const theme = resolveTheme(themeName, mode);
  const availableThemes = Object.keys(DEFAULT_THEMES);

  const setThemeName = useCallback((name: string) => {
    if (DEFAULT_THEMES[name]) setName(name);
  }, []);

  const toggleMode = useCallback(() => {
    setMode((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setThemeName, toggleMode, availableThemes }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}
