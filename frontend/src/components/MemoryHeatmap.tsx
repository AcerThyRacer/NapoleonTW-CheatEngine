/**
 * Live memory visualisation heatmap.
 * Renders a grid of coloured cells whose intensity corresponds to
 * the current value at each monitored memory address.
 */

import { useMemo } from "react";
import { useTheme } from "../hooks/useTheme";
import type { MemoryHeatmapEntry } from "../types/cheats";

interface MemoryHeatmapProps {
  data: MemoryHeatmapEntry[];
  columns?: number;
}

function intensityToColor(intensity: number, primary: string): string {
  // Blend from a dark base towards the theme primary colour
  const t = Math.max(0, Math.min(1, intensity));
  const r = Math.round(26 + t * (parseInt(primary.slice(1, 3), 16) - 26));
  const g = Math.round(37 + t * (parseInt(primary.slice(3, 5), 16) - 37));
  const b = Math.round(47 + t * (parseInt(primary.slice(5, 7), 16) - 47));
  return `rgb(${r},${g},${b})`;
}

export default function MemoryHeatmap({ data, columns = 16 }: MemoryHeatmapProps) {
  const { theme } = useTheme();

  // If no live data, show a demo grid
  const cells = useMemo(() => {
    if (data.length > 0) return data;
    return Array.from({ length: columns * 8 }, (_, i) => ({
      address: `0x${(0x00400000 + i * 4).toString(16).toUpperCase()}`,
      value: Math.random() * 255,
      intensity: Math.random(),
      label: undefined,
    }));
  }, [data, columns]);

  return (
    <div style={{ padding: 12 }}>
      <h3 style={{ color: theme.colors.primary, fontFamily: "Georgia, serif", margin: "0 0 8px" }}>
        🔥 Live Memory Heatmap
      </h3>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${columns}, 1fr)`,
          gap: 2,
          borderRadius: 6,
          overflow: "hidden",
          border: `1px solid ${theme.colors.primary}`,
        }}
      >
        {cells.map((cell, i) => (
          <div
            key={i}
            title={`${cell.address}: ${Math.round(cell.value)}${cell.label ? ` (${cell.label})` : ""}`}
            style={{
              width: "100%",
              paddingBottom: "100%",
              background: intensityToColor(cell.intensity, theme.colors.primary),
              transition: "background 0.3s ease",
            }}
          />
        ))}
      </div>
      <p style={{ color: "#95a5a6", fontSize: 11, marginTop: 6 }}>
        {data.length > 0 ? `${data.length} monitored addresses` : "Demo heatmap — connect to process for live data"}
      </p>
    </div>
  );
}
