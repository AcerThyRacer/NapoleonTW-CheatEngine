/**
 * Drag-and-drop cheat preset sharing using react-dnd.
 * Users can save current cheat states as named presets and reorder them.
 */

import { useCallback } from "react";
import { DndProvider, useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { useTheme } from "../hooks/useTheme";
import type { CheatPreset } from "../types/cheats";

const ITEM_TYPE = "PRESET";

interface PresetCardProps {
  preset: CheatPreset;
  index: number;
  onLoad: (index: number) => void;
  onMove: (from: number, to: number) => void;
}

function PresetCard({ preset, index, onLoad, onMove }: PresetCardProps) {
  const { theme } = useTheme();
  const activeCount = Object.values(preset.cheat_states).filter(Boolean).length;
  const date = new Date(preset.created_at * 1000);

  const [{ isDragging }, drag] = useDrag({
    type: ITEM_TYPE,
    item: { index },
    collect: (monitor) => ({ isDragging: monitor.isDragging() }),
  });

  const [, drop] = useDrop({
    accept: ITEM_TYPE,
    hover: (item: { index: number }) => {
      if (item.index !== index) {
        onMove(item.index, index);
        item.index = index;
      }
    },
  });

  return (
    <div
      ref={(node) => { drag(drop(node)); }}
      style={{
        opacity: isDragging ? 0.5 : 1,
        padding: "10px 14px",
        background: `linear-gradient(90deg, rgba(44,62,80,0.8), rgba(26,37,47,0.8))`,
        border: `1px solid ${theme.colors.primary}`,
        borderRadius: 8,
        cursor: "grab",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}
    >
      <span style={{ fontSize: 22 }}>📋</span>
      <div style={{ flex: 1 }}>
        <div style={{ color: theme.colors.primary, fontWeight: "bold", fontSize: 14 }}>
          {preset.name}
        </div>
        <div style={{ color: "#95a5a6", fontSize: 11 }}>
          {activeCount} cheats · {date.toLocaleString()}
        </div>
      </div>
      <button
        onClick={() => onLoad(index)}
        style={{
          padding: "6px 14px",
          borderRadius: 6,
          border: `1px solid ${theme.colors.primary}`,
          background: theme.colors.panel,
          color: theme.colors.primary,
          cursor: "pointer",
          fontWeight: "bold",
        }}
      >
        Load
      </button>
    </div>
  );
}

interface PresetManagerProps {
  presets: CheatPreset[];
  onSave: (name: string) => void;
  onLoad: (index: number) => void;
  onReorder: (presets: CheatPreset[]) => void;
}

export default function PresetManager({ presets, onSave, onLoad, onReorder }: PresetManagerProps) {
  const { theme } = useTheme();

  const handleMove = useCallback(
    (from: number, to: number) => {
      const updated = [...presets];
      const [moved] = updated.splice(from, 1);
      updated.splice(to, 0, moved);
      onReorder(updated);
    },
    [presets, onReorder],
  );

  const handleSave = () => {
    const name = window.prompt("Preset name:");
    if (name) onSave(name);
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div style={{ padding: 12 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
          <h3 style={{ color: theme.colors.primary, fontFamily: "Georgia, serif", margin: 0 }}>
            📦 Cheat Presets
          </h3>
          <button
            onClick={handleSave}
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border: `1px solid ${theme.colors.primary}`,
              background: theme.colors.panel,
              color: theme.colors.primary,
              cursor: "pointer",
              fontWeight: "bold",
            }}
          >
            + Save Current
          </button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {presets.length === 0 && (
            <p style={{ color: "#95a5a6", fontSize: 13 }}>
              No presets yet — save your current cheat configuration above.
              Drag and drop to reorder presets.
            </p>
          )}
          {presets.map((p, i) => (
            <PresetCard key={i} preset={p} index={i} onLoad={onLoad} onMove={handleMove} />
          ))}
        </div>
      </div>
    </DndProvider>
  );
}
