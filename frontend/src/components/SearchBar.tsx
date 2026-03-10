/**
 * Search bar for filtering cheats by name, description, or id.
 */

import { useTheme } from "../hooks/useTheme";

interface SearchBarProps {
  value: string;
  onChange: (query: string) => void;
}

export default function SearchBar({ value, onChange }: SearchBarProps) {
  const { theme } = useTheme();

  return (
    <div
      style={{
        height: 44,
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "4px 16px",
        background: `rgba(26, 37, 47, 0.86)`,
        borderBottom: `1px solid ${theme.colors.primary}`,
      }}
    >
      <span role="img" aria-label="search">🔍</span>
      <input
        type="text"
        placeholder="Search cheats…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          flex: 1,
          background: `rgba(44, 62, 80, 0.7)`,
          border: `1px solid ${theme.colors.primary}`,
          borderRadius: 6,
          color: theme.colors.primary,
          padding: "4px 10px",
          fontSize: 13,
          outline: "none",
        }}
      />
      {value && (
        <button
          onClick={() => onChange("")}
          style={{
            background: "transparent",
            border: "none",
            color: theme.colors.primary,
            cursor: "pointer",
            fontSize: 16,
          }}
          aria-label="Clear search"
        >
          ✕
        </button>
      )}
    </div>
  );
}
