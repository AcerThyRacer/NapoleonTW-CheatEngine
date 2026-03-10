/**
 * CheatToggle – toggle switch for a single cheat.
 * Mirrors CheatToggleButton from napoleon_panel.py.
 */

import { motion } from "framer-motion";
import { useTheme } from "../hooks/useTheme";
import type { CheatCommand } from "../types/cheats";

interface CheatToggleProps {
  command: CheatCommand;
  enabled: boolean;
  onToggle: (cheatId: string, enabled: boolean) => void;
}

export default function CheatToggle({ command, enabled, onToggle }: CheatToggleProps) {
  const { theme } = useTheme();

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "10px 14px",
        background: `linear-gradient(90deg, rgba(44,62,80,0.8), rgba(26,37,47,0.8))`,
        border: `1px solid ${theme.colors.primary}`,
        borderRadius: 8,
        cursor: "pointer",
        transition: "border-color 0.2s",
      }}
      whileHover={{ borderColor: theme.colors.secondary, scale: 1.01 }}
    >
      {/* Icon */}
      <span style={{ fontSize: 28, width: 50, textAlign: "center" }}>{command.icon}</span>

      {/* Text */}
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 14, fontWeight: "bold", color: theme.colors.primary }}>
          {command.name}
        </div>
        <div style={{ fontFamily: "Georgia, serif", fontSize: 11, color: "#95a5a6" }}>
          {command.description}
        </div>
      </div>

      {/* Slider for speed-type cheats */}
      {command.is_slider && (
        <input
          type="range"
          min={command.min_value}
          max={command.max_value}
          defaultValue={command.default_value}
          style={{ width: 80 }}
          title={`${command.min_value}–${command.max_value}`}
        />
      )}

      {/* Toggle button */}
      <button
        onClick={() => onToggle(command.id, !enabled)}
        style={{
          width: 80,
          height: 40,
          borderRadius: 20,
          border: `2px solid ${enabled ? "#fff" : "#95a5a6"}`,
          background: enabled
            ? "linear-gradient(180deg, #27ae60, #2ecc71)"
            : "linear-gradient(180deg, #c0392b, #e74c3c)",
          color: "#fff",
          fontWeight: "bold",
          fontSize: 13,
          cursor: "pointer",
          transition: "all 0.2s",
        }}
      >
        {enabled ? "ON" : "OFF"}
      </button>
    </motion.div>
  );
}
