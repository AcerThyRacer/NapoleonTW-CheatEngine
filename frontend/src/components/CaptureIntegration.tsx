/**
 * Screenshot / video capture integration with cheat markers.
 * Allows capturing the current UI state annotated with active cheat info.
 */

import { useCallback, useRef, useState } from "react";
import { useTheme } from "../hooks/useTheme";

interface CaptureIntegrationProps {
  activeCheatNames: string[];
}

export default function CaptureIntegration({ activeCheatNames }: CaptureIntegrationProps) {
  const { theme } = useTheme();
  const [lastCapture, setLastCapture] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleScreenshot = useCallback(() => {
    // Use the native Canvas API to draw a snapshot with cheat markers
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 200;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Background
    ctx.fillStyle = theme.colors.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Border
    ctx.strokeStyle = theme.colors.primary;
    ctx.lineWidth = 3;
    ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4);

    // Title
    ctx.fillStyle = theme.colors.primary;
    ctx.font = "bold 20px Georgia";
    ctx.fillText("Napoleon TW Cheat Engine — Capture", 20, 35);

    // Timestamp
    ctx.fillStyle = "#95a5a6";
    ctx.font = "13px Georgia";
    ctx.fillText(new Date().toLocaleString(), 20, 55);

    // Active cheats
    ctx.fillStyle = theme.colors.primary;
    ctx.font = "bold 15px Georgia";
    ctx.fillText("Active Cheats:", 20, 85);

    ctx.font = "13px Georgia";
    ctx.fillStyle = "#2ecc71";
    activeCheatNames.forEach((name, i) => {
      const y = 105 + i * 18;
      if (y < canvas.height - 10) {
        ctx.fillText(`✓ ${name}`, 30, y);
      }
    });

    if (activeCheatNames.length === 0) {
      ctx.fillStyle = "#95a5a6";
      ctx.fillText("No cheats active", 30, 105);
    }

    // Convert to data URL
    const dataUrl = canvas.toDataURL("image/png");
    setLastCapture(dataUrl);

    // Trigger download
    const link = document.createElement("a");
    link.download = `napoleon-capture-${Date.now()}.png`;
    link.href = dataUrl;
    link.click();
  }, [theme, activeCheatNames]);

  return (
    <div ref={containerRef} style={{ padding: 12 }}>
      <h3 style={{ color: theme.colors.primary, fontFamily: "Georgia, serif", margin: "0 0 8px" }}>
        📸 Capture Integration
      </h3>
      <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
        <button
          onClick={handleScreenshot}
          style={{
            padding: "8px 18px",
            borderRadius: 6,
            border: `1px solid ${theme.colors.primary}`,
            background: theme.colors.panel,
            color: theme.colors.primary,
            cursor: "pointer",
            fontWeight: "bold",
          }}
        >
          📸 Screenshot with Markers
        </button>
      </div>
      {lastCapture && (
        <div style={{ border: `1px solid ${theme.colors.primary}`, borderRadius: 6, overflow: "hidden" }}>
          <img src={lastCapture} alt="Last capture" style={{ width: "100%", display: "block" }} />
        </div>
      )}
      <p style={{ color: "#95a5a6", fontSize: 11, marginTop: 6 }}>
        Captures include cheat markers showing which cheats are active at time of screenshot.
      </p>
    </div>
  );
}
