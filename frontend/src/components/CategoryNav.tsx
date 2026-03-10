/**
 * Category navigation bar with icon buttons and tooltips.
 */

import { useTheme } from "../hooks/useTheme";
import type { CategoryMeta } from "../types/cheats";
import { CheatCategory } from "../types/cheats";

interface CategoryNavProps {
  categories: Record<string, CategoryMeta>;
  active: string | "settings";
  onSelect: (category: string | "settings") => void;
}

const CATEGORY_ORDER = [
  CheatCategory.TREASURY,
  CheatCategory.MILITARY,
  CheatCategory.CAMPAIGN,
  CheatCategory.BATTLE,
  CheatCategory.DIPLOMACY,
];

export default function CategoryNav({ categories, active, onSelect }: CategoryNavProps) {
  const { theme } = useTheme();

  const btnStyle = (isActive: boolean): React.CSSProperties => ({
    width: 60,
    height: 60,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    border: `2px solid ${isActive ? "#fff" : theme.colors.primary}`,
    borderRadius: 10,
    background: isActive
      ? `linear-gradient(180deg, ${theme.colors.primary}, ${theme.colors.secondary})`
      : `linear-gradient(180deg, #34495e, #2c3e50)`,
    cursor: "pointer",
    fontSize: 22,
    transition: "all 0.2s ease",
  });

  return (
    <nav style={{ display: "flex", gap: 6, padding: "8px 12px", flexWrap: "wrap" }}>
      {CATEGORY_ORDER.map((cat) => {
        const meta = categories[cat] ?? { emoji: "❓", tooltip: cat };
        return (
          <button
            key={cat}
            title={meta.tooltip}
            style={btnStyle(active === cat)}
            onClick={() => onSelect(cat)}
          >
            {meta.emoji}
          </button>
        );
      })}
      <button
        title="Settings — Theme, animations, presets"
        style={btnStyle(active === "settings")}
        onClick={() => onSelect("settings")}
      >
        ⚙️
      </button>
    </nav>
  );
}
