/**
 * Settings panel – Theme selection, overlay presets, animation speed,
 * sound effects toggle, and quick activate/deactivate buttons.
 */

import { useTheme } from "../hooks/useTheme";

interface SettingsPanelProps {
  onActivateAll: () => void;
  onDeactivateAll: () => void;
  onThemeChange: (theme: string) => void;
}

const THEME_LABELS: Record<string, string> = {
  napoleon_gold: "Napoleon Gold",
  imperial_blue: "Imperial Blue",
  royal_purple: "Royal Purple",
  battlefield_steel: "Battlefield Steel",
  midnight_command: "Midnight Command",
};

export default function SettingsPanel({
  onActivateAll,
  onDeactivateAll,
  onThemeChange,
}: SettingsPanelProps) {
  const { theme, setThemeName, toggleMode, availableThemes } = useTheme();

  const groupStyle: React.CSSProperties = {
    border: `1px solid ${theme.colors.primary}`,
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
  };

  const labelStyle: React.CSSProperties = {
    color: theme.colors.primary,
    fontFamily: "Georgia, serif",
    fontWeight: "bold",
    fontSize: 16,
    marginBottom: 8,
    display: "block",
  };

  return (
    <div style={{ padding: 20 }}>
      {/* Theme */}
      <div style={groupStyle}>
        <span style={labelStyle}>🎨 Imperial Theme</span>
        <select
          value={theme.name}
          onChange={(e) => {
            setThemeName(e.target.value);
            onThemeChange(e.target.value);
          }}
          style={{
            width: "100%",
            padding: "6px 10px",
            borderRadius: 6,
            border: `1px solid ${theme.colors.primary}`,
            background: theme.colors.panel,
            color: theme.colors.primary,
          }}
        >
          {availableThemes.map((t) => (
            <option key={t} value={t}>
              {THEME_LABELS[t] ?? t}
            </option>
          ))}
        </select>

        <button
          onClick={toggleMode}
          style={{
            marginTop: 10,
            padding: "6px 16px",
            borderRadius: 6,
            border: `1px solid ${theme.colors.primary}`,
            background: theme.colors.panel,
            color: theme.colors.primary,
            cursor: "pointer",
          }}
        >
          Toggle {theme.mode === "dark" ? "Light" : "Dark"} Mode
        </button>
      </div>

      {/* Animation */}
      <div style={groupStyle}>
        <span style={labelStyle}>⚡ Animation Settings</span>
        <label style={{ color: "#95a5a6", fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
          Animation Speed
          <input type="range" min={1} max={10} defaultValue={7} style={{ flex: 1 }} />
        </label>
        <label style={{ color: "#95a5a6", fontSize: 13, display: "flex", alignItems: "center", gap: 8, marginTop: 8 }}>
          <input type="checkbox" defaultChecked /> Enable Sound Effects
        </label>
      </div>

      {/* Quick Commands */}
      <div style={groupStyle}>
        <span style={labelStyle}>⚡ Quick Commands</span>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onActivateAll}
            style={{
              flex: 1,
              padding: "10px 20px",
              borderRadius: 8,
              border: `2px solid ${theme.colors.primary}`,
              background: theme.colors.panel,
              color: theme.colors.primary,
              fontWeight: "bold",
              cursor: "pointer",
            }}
          >
            Activate All Cheats
          </button>
          <button
            onClick={onDeactivateAll}
            style={{
              flex: 1,
              padding: "10px 20px",
              borderRadius: 8,
              border: `2px solid ${theme.colors.primary}`,
              background: theme.colors.panel,
              color: theme.colors.primary,
              fontWeight: "bold",
              cursor: "pointer",
            }}
          >
            Deactivate All Cheats
          </button>
        </div>
      </div>
    </div>
  );
}
