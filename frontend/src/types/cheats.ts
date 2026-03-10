/**
 * Core cheat and category types for the Napoleon TW Cheat Engine UI.
 * Mirrors the Python dataclasses in src/server/websocket_server.py.
 */

export enum CheatCategory {
  TREASURY = "treasury",
  MILITARY = "military",
  CAMPAIGN = "campaign",
  BATTLE = "battle",
  DIPLOMACY = "diplomacy",
  QUALITY_OF_LIFE = "quality",
}

export interface CategoryMeta {
  icon: string;
  emoji: string;
  tooltip: string;
}

export interface CheatCommand {
  id: string;
  name: string;
  description: string;
  category: CheatCategory;
  icon: string;
  default_value: number;
  min_value: number;
  max_value: number;
  is_toggle: boolean;
  is_slider: boolean;
}

export interface ThemeColors {
  primary: string;
  secondary: string;
  background: string;
  panel: string;
}

export interface CheatPreset {
  name: string;
  cheat_states: Record<string, boolean>;
  theme: string;
  created_at: number;
}

export interface MemoryHeatmapEntry {
  address: string;
  value: number;
  intensity: number;
  label?: string;
}

export interface ResourceHistoryEntry {
  timestamp: number;
  active_count: number;
  cheat_id: string;
  enabled: boolean;
}
