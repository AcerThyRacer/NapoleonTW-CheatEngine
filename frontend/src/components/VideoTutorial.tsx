/**
 * Built-in video tutorial player for each cheat type.
 * Uses react-player for cross-platform playback.
 */

import { useState } from "react";
import ReactPlayer from "react-player";
import { useTheme } from "../hooks/useTheme";

interface Tutorial {
  id: string;
  title: string;
  description: string;
  url: string;
  cheatId?: string;
}

// Placeholder tutorials – in production these would link to actual recordings
const TUTORIALS: Tutorial[] = [
  {
    id: "intro",
    title: "Getting Started",
    description: "Overview of the Napoleon TW Cheat Engine and how to attach to the game process.",
    url: "",
  },
  {
    id: "treasury",
    title: "Treasury Cheats",
    description: "How to use the Imperial Treasury cheat for unlimited gold.",
    url: "",
    cheatId: "infinite_gold",
  },
  {
    id: "military",
    title: "Military Cheats",
    description: "Instant recruitment and unlimited movement explained.",
    url: "",
    cheatId: "instant_recruitment",
  },
  {
    id: "battle",
    title: "Battle Cheats",
    description: "God mode, infinite ammo, and devastating artillery walkthrough.",
    url: "",
    cheatId: "god_mode",
  },
  {
    id: "memory",
    title: "Memory Scanning",
    description: "Advanced memory scanning and freezing tutorial.",
    url: "",
  },
  {
    id: "presets",
    title: "Preset Sharing",
    description: "How to save, share, and import cheat presets.",
    url: "",
  },
];

export default function VideoTutorial() {
  const { theme } = useTheme();
  const [selected, setSelected] = useState<Tutorial>(TUTORIALS[0]);

  return (
    <div style={{ padding: 12 }}>
      <h3 style={{ color: theme.colors.primary, fontFamily: "Georgia, serif", margin: "0 0 12px" }}>
        🎬 Video Tutorials
      </h3>
      <div style={{ display: "flex", gap: 12 }}>
        {/* Sidebar */}
        <div style={{ width: 220, flexShrink: 0 }}>
          {TUTORIALS.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelected(t)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "8px 12px",
                marginBottom: 4,
                borderRadius: 6,
                border: selected.id === t.id ? `2px solid ${theme.colors.primary}` : "1px solid transparent",
                background: selected.id === t.id ? theme.colors.panel : "transparent",
                color: selected.id === t.id ? theme.colors.primary : "#95a5a6",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: selected.id === t.id ? "bold" : "normal",
              }}
            >
              {t.title}
            </button>
          ))}
        </div>

        {/* Player area */}
        <div style={{ flex: 1 }}>
          <div
            style={{
              width: "100%",
              aspectRatio: "16/9",
              background: "#000",
              borderRadius: 8,
              overflow: "hidden",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: `1px solid ${theme.colors.primary}`,
            }}
          >
            {selected.url ? (
              <ReactPlayer url={selected.url} width="100%" height="100%" controls />
            ) : (
              <div style={{ color: "#95a5a6", textAlign: "center", padding: 20 }}>
                <span style={{ fontSize: 48, display: "block", marginBottom: 10 }}>🎥</span>
                <p>Video tutorial placeholder</p>
                <p style={{ fontSize: 12 }}>Add video URLs in production</p>
              </div>
            )}
          </div>
          <h4 style={{ color: theme.colors.primary, margin: "10px 0 4px" }}>{selected.title}</h4>
          <p style={{ color: "#95a5a6", fontSize: 13, margin: 0 }}>{selected.description}</p>
        </div>
      </div>
    </div>
  );
}
