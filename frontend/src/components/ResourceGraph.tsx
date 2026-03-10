/**
 * Historical graph of resource values over time using Recharts.
 * Shows the active cheat count and toggle events on a time axis.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceDot,
} from "recharts";
import { useTheme } from "../hooks/useTheme";
import type { ResourceHistoryEntry } from "../types/cheats";

interface ResourceGraphProps {
  data: ResourceHistoryEntry[];
}

function formatTime(ts: number): string {
  const d = new Date(ts * 1000);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

export default function ResourceGraph({ data }: ResourceGraphProps) {
  const { theme } = useTheme();

  const chartData = data.map((d) => ({
    time: formatTime(d.timestamp),
    activeCount: d.active_count,
    cheat: d.cheat_id,
    enabled: d.enabled,
  }));

  // Provide demo data when no history yet
  const displayData =
    chartData.length > 0
      ? chartData
      : [
          { time: "00:00:00", activeCount: 0, cheat: "", enabled: false },
          { time: "00:00:05", activeCount: 2, cheat: "infinite_gold", enabled: true },
          { time: "00:00:10", activeCount: 4, cheat: "god_mode", enabled: true },
          { time: "00:00:15", activeCount: 3, cheat: "infinite_gold", enabled: false },
          { time: "00:00:20", activeCount: 5, cheat: "unlimited_ammo", enabled: true },
        ];

  return (
    <div style={{ padding: 12 }}>
      <h3 style={{ color: theme.colors.primary, fontFamily: "Georgia, serif", margin: "0 0 8px" }}>
        📈 Resource History
      </h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={displayData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis dataKey="time" stroke="#95a5a6" fontSize={11} />
          <YAxis stroke="#95a5a6" fontSize={11} allowDecimals={false} />
          <Tooltip
            contentStyle={{
              background: theme.colors.panel,
              border: `1px solid ${theme.colors.primary}`,
              borderRadius: 6,
              color: theme.colors.primary,
            }}
          />
          <Line
            type="monotone"
            dataKey="activeCount"
            stroke={theme.colors.primary}
            strokeWidth={2}
            dot={{ r: 4, fill: theme.colors.secondary }}
            name="Active Cheats"
          />
          {/* Mark toggle events */}
          {displayData
            .filter((d) => d.cheat)
            .map((d, i) => (
              <ReferenceDot
                key={i}
                x={d.time}
                y={d.activeCount}
                r={5}
                fill={d.enabled ? "#2ecc71" : "#e74c3c"}
                stroke="none"
              />
            ))}
        </LineChart>
      </ResponsiveContainer>
      <p style={{ color: "#95a5a6", fontSize: 11, marginTop: 4 }}>
        {data.length > 0 ? `${data.length} events recorded` : "Demo graph — toggle cheats to see live data"}
      </p>
    </div>
  );
}
