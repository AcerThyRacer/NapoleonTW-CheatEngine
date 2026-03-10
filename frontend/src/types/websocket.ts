/**
 * WebSocket message types exchanged between the React frontend and
 * the Python backend server.
 */

import type {
  CheatCommand,
  CategoryMeta,
  ThemeColors,
  CheatPreset,
  MemoryHeatmapEntry,
  ResourceHistoryEntry,
} from "./cheats";

/* ---- Outbound (client → server) ---- */

export interface ToggleCheatMessage {
  type: "toggle_cheat";
  cheat_id: string;
  enabled: boolean;
}

export interface ActivateAllMessage {
  type: "activate_all";
}

export interface DeactivateAllMessage {
  type: "deactivate_all";
}

export interface SetThemeMessage {
  type: "set_theme";
  theme: string;
}

export interface GetStateMessage {
  type: "get_state";
}

export interface SavePresetMessage {
  type: "save_preset";
  name: string;
}

export interface LoadPresetMessage {
  type: "load_preset";
  index: number;
}

export interface GetMemoryHeatmapMessage {
  type: "get_memory_heatmap";
}

export interface GetResourceHistoryMessage {
  type: "get_resource_history";
}

export type OutboundMessage =
  | ToggleCheatMessage
  | ActivateAllMessage
  | DeactivateAllMessage
  | SetThemeMessage
  | GetStateMessage
  | SavePresetMessage
  | LoadPresetMessage
  | GetMemoryHeatmapMessage
  | GetResourceHistoryMessage;

/* ---- Inbound (server → client) ---- */

export interface StateSnapshotMessage {
  type: "state_snapshot";
  cheats: CheatCommand[];
  cheat_states: Record<string, boolean>;
  categories: Record<string, CategoryMeta>;
  themes: Record<string, ThemeColors>;
  current_theme: string;
  active_count: number;
  presets: CheatPreset[];
}

export interface CheatToggledMessage {
  type: "cheat_toggled";
  cheat_id: string;
  enabled: boolean;
  active_count: number;
}

export interface AllActivatedMessage {
  type: "all_activated";
  active_count: number;
}

export interface AllDeactivatedMessage {
  type: "all_deactivated";
  active_count: number;
}

export interface ThemeChangedMessage {
  type: "theme_changed";
  theme: string;
}

export interface PresetSavedMessage {
  type: "preset_saved";
  preset: CheatPreset;
}

export interface PresetLoadedMessage {
  type: "preset_loaded";
  cheat_states: Record<string, boolean>;
  current_theme: string;
  active_count: number;
}

export interface MemoryHeatmapMessage {
  type: "memory_heatmap";
  data: MemoryHeatmapEntry[];
}

export interface ResourceHistoryMessage {
  type: "resource_history";
  data: ResourceHistoryEntry[];
}

export interface ErrorMessage {
  type: "error";
  message: string;
}

export type InboundMessage =
  | StateSnapshotMessage
  | CheatToggledMessage
  | AllActivatedMessage
  | AllDeactivatedMessage
  | ThemeChangedMessage
  | PresetSavedMessage
  | PresetLoadedMessage
  | MemoryHeatmapMessage
  | ResourceHistoryMessage
  | ErrorMessage;
