/**
 * NapoleonPanel – main panel component that ports all functionality
 * from napoleon_panel.py to React.  Supports:
 *
 *  - Category navigation with cheat toggles
 *  - Search filtering
 *  - Settings (theme, animation, quick commands)
 *  - 3D battle map, memory heatmap, resource graph
 *  - Preset management, video tutorials, capture integration
 *  - Responsive: windowed, fullscreen, and overlay modes
 */

import { useState, useMemo, useCallback } from "react";
import { AnimatePresence } from "framer-motion";

import Header from "./Header";
import SearchBar from "./SearchBar";
import CategoryNav from "./CategoryNav";
import CheatToggle from "./CheatToggle";
import SettingsPanel from "./SettingsPanel";
import BattleMap from "./BattleMap";
import MemoryHeatmap from "./MemoryHeatmap";
import ResourceGraph from "./ResourceGraph";
import PresetManager from "./PresetManager";
import VideoTutorial from "./VideoTutorial";
import CaptureIntegration from "./CaptureIntegration";

import { useTheme } from "../hooks/useTheme";
import { useWebSocket } from "../hooks/useWebSocket";

import type { CheatCommand, CategoryMeta, CheatPreset, MemoryHeatmapEntry, ResourceHistoryEntry } from "../types/cheats";
import { CheatCategory } from "../types/cheats";
import type { InboundMessage } from "../types/websocket";

const WS_URL = `ws://${typeof window !== "undefined" ? window.location.hostname : "localhost"}:8765`;

// Default categories when server has not yet responded
const DEFAULT_CATEGORIES: Record<string, CategoryMeta> = {
  [CheatCategory.TREASURY]: { icon: "treasury.svg", emoji: "💰", tooltip: "Treasury — Imperial finances" },
  [CheatCategory.MILITARY]: { icon: "sword.svg", emoji: "⚔️", tooltip: "Military — Army commands" },
  [CheatCategory.CAMPAIGN]: { icon: "campaign.svg", emoji: "🏰", tooltip: "Campaign — Strategic options" },
  [CheatCategory.BATTLE]: { icon: "shield.svg", emoji: "🛡️", tooltip: "Battle — Combat modifiers" },
  [CheatCategory.DIPLOMACY]: { icon: "diplomacy.svg", emoji: "🤝", tooltip: "Diplomacy — Relations" },
};

type DisplayMode = "windowed" | "fullscreen" | "overlay";

export default function NapoleonPanel() {
  const { theme, setThemeName } = useTheme();

  /* ---- state ---- */
  const [cheats, setCheats] = useState<CheatCommand[]>([]);
  const [cheatStates, setCheatStates] = useState<Record<string, boolean>>({});
  const [categories, setCategories] = useState<Record<string, CategoryMeta>>(DEFAULT_CATEGORIES);
  const [activeCategory, setActiveCategory] = useState<string | "settings">(CheatCategory.TREASURY);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCount, setActiveCount] = useState(0);
  const [presets, setPresets] = useState<CheatPreset[]>([]);
  const [heatmapData, setHeatmapData] = useState<MemoryHeatmapEntry[]>([]);
  const [historyData, setHistoryData] = useState<ResourceHistoryEntry[]>([]);
  const [statusMessage, setStatusMessage] = useState("Ready — Attach to Napoleon Total War process to begin");
  const [displayMode, setDisplayMode] = useState<DisplayMode>("windowed");

  /* ---- WebSocket ---- */
  const handleMessage = useCallback(
    (msg: InboundMessage) => {
      switch (msg.type) {
        case "state_snapshot":
          setCheats(msg.cheats);
          setCheatStates(msg.cheat_states);
          setCategories(msg.categories);
          setActiveCount(msg.active_count);
          setPresets(msg.presets);
          if (msg.current_theme) setThemeName(msg.current_theme);
          break;
        case "cheat_toggled":
          setCheatStates((prev) => ({ ...prev, [msg.cheat_id]: msg.enabled }));
          setActiveCount(msg.active_count);
          break;
        case "all_activated":
          setCheatStates((prev) => {
            const next = { ...prev };
            for (const k of Object.keys(next)) next[k] = true;
            return next;
          });
          setActiveCount(msg.active_count);
          setStatusMessage("🎉 All cheats activated! Vive l'Empereur!");
          break;
        case "all_deactivated":
          setCheatStates((prev) => {
            const next = { ...prev };
            for (const k of Object.keys(next)) next[k] = false;
            return next;
          });
          setActiveCount(0);
          setStatusMessage("All cheats deactivated");
          break;
        case "theme_changed":
          setThemeName(msg.theme);
          setStatusMessage(`Theme changed to ${msg.theme}`);
          break;
        case "preset_saved":
          setPresets((prev) => [...prev, msg.preset]);
          break;
        case "preset_loaded":
          setCheatStates(msg.cheat_states);
          setActiveCount(msg.active_count);
          setThemeName(msg.current_theme);
          break;
        case "memory_heatmap":
          setHeatmapData(msg.data);
          break;
        case "resource_history":
          setHistoryData(msg.data);
          break;
        case "error":
          setStatusMessage(`Error: ${msg.message}`);
          break;
      }
    },
    [setThemeName],
  );

  const { connected, send } = useWebSocket({ url: WS_URL, onMessage: handleMessage });

  /* ---- handlers ---- */
  const toggleCheat = useCallback(
    (cheatId: string, enabled: boolean) => {
      send({ type: "toggle_cheat", cheat_id: cheatId, enabled });
      // Optimistic update
      setCheatStates((prev) => ({ ...prev, [cheatId]: enabled }));
      setActiveCount((prev) => prev + (enabled ? 1 : -1));
      const cmd = cheats.find((c) => c.id === cheatId);
      setStatusMessage(enabled ? `✓ Activated: ${cmd?.name ?? cheatId}` : "Cheat deactivated");
    },
    [send, cheats],
  );

  /* ---- derived ---- */
  const filteredCheats = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const catCheats = activeCategory === "settings" ? [] : cheats.filter((c) => c.category === activeCategory);
    if (!q) return catCheats;
    return catCheats.filter(
      (c) => c.name.toLowerCase().includes(q) || c.description.toLowerCase().includes(q) || c.id.toLowerCase().includes(q),
    );
  }, [cheats, activeCategory, searchQuery]);

  const activeCheatNames = useMemo(
    () => cheats.filter((c) => cheatStates[c.id]).map((c) => c.name),
    [cheats, cheatStates],
  );

  /* ---- display mode styles ---- */
  const containerStyle: React.CSSProperties = {
    minHeight: "100vh",
    background: theme.colors.background,
    color: theme.colors.primary,
    fontFamily: "Georgia, serif",
    ...(displayMode === "fullscreen" ? { position: "fixed", inset: 0, zIndex: 9999 } : {}),
    ...(displayMode === "overlay"
      ? {
          position: "fixed",
          top: 10,
          right: 10,
          width: 420,
          maxHeight: "90vh",
          overflow: "auto",
          borderRadius: 12,
          border: `2px solid ${theme.colors.primary}`,
          boxShadow: "0 0 30px rgba(0,0,0,0.7)",
          zIndex: 99999,
        }
      : {}),
  };

  return (
    <div style={containerStyle}>
      {/* Display mode toggle */}
      <div style={{ display: "flex", gap: 4, padding: "4px 8px", justifyContent: "flex-end" }}>
        {(["windowed", "fullscreen", "overlay"] as DisplayMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setDisplayMode(m)}
            style={{
              padding: "2px 8px",
              fontSize: 11,
              border: `1px solid ${displayMode === m ? theme.colors.primary : "transparent"}`,
              borderRadius: 4,
              background: displayMode === m ? theme.colors.panel : "transparent",
              color: displayMode === m ? theme.colors.primary : "#95a5a6",
              cursor: "pointer",
            }}
          >
            {m}
          </button>
        ))}
      </div>

      <Header />

      {/* Live Stats */}
      <div
        style={{
          display: "flex",
          gap: 16,
          padding: "8px 16px",
          background: `rgba(44,62,80,0.5)`,
          justifyContent: "center",
          fontSize: 14,
        }}
      >
        <span>⚔️ Active: <strong>{activeCount}</strong></span>
        <span>🌐 {connected ? "Connected" : "Disconnected"}</span>
      </div>

      <SearchBar value={searchQuery} onChange={setSearchQuery} />
      <CategoryNav categories={categories} active={activeCategory} onSelect={setActiveCategory} />

      {/* Main content area */}
      <div style={{ padding: "0 16px 16px", minHeight: 300 }}>
        {activeCategory === "settings" ? (
          <div>
            <SettingsPanel
              onActivateAll={() => send({ type: "activate_all" })}
              onDeactivateAll={() => send({ type: "deactivate_all" })}
              onThemeChange={(t) => send({ type: "set_theme", theme: t })}
            />
            <PresetManager
              presets={presets}
              onSave={(name) => send({ type: "save_preset", name })}
              onLoad={(index) => send({ type: "load_preset", index })}
              onReorder={setPresets}
            />
            <VideoTutorial />
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(340, 1fr))",
              gap: 12,
              paddingTop: 12,
            }}
          >
            <AnimatePresence>
              {filteredCheats.map((cmd) => (
                <CheatToggle
                  key={cmd.id}
                  command={cmd}
                  enabled={!!cheatStates[cmd.id]}
                  onToggle={toggleCheat}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Advanced panels (always visible below main content) */}
      <div style={{ borderTop: `1px solid ${theme.colors.primary}`, marginTop: 8 }}>
        <BattleMap />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, padding: "0 8px" }}>
          <MemoryHeatmap data={heatmapData} />
          <ResourceGraph data={historyData} />
        </div>
        <CaptureIntegration activeCheatNames={activeCheatNames} />
      </div>

      {/* Status bar */}
      <footer
        style={{
          padding: "6px 16px",
          background: theme.colors.panel,
          borderTop: `2px solid ${theme.colors.primary}`,
          color: theme.colors.primary,
          fontSize: 13,
        }}
      >
        {statusMessage}
      </footer>
    </div>
  );
}
