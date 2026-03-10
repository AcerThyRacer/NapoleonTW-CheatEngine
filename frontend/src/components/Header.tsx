/**
 * Header component – Imperial eagle, title, crown with cannon-smoke
 * particle effects rendered via framer-motion animations.
 */

import { motion } from "framer-motion";
import { useTheme } from "../hooks/useTheme";

interface SmokeParticle {
  id: number;
  x: number;
  delay: number;
}

function CannonSmoke() {
  const particles: SmokeParticle[] = Array.from({ length: 12 }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    delay: Math.random() * 3,
  }));

  return (
    <div className="cannon-smoke" style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}>
      {particles.map((p) => (
        <motion.div
          key={p.id}
          style={{
            position: "absolute",
            left: `${p.x}%`,
            bottom: 0,
            width: 24,
            height: 24,
            borderRadius: "50%",
            background: "rgba(200, 200, 200, 0.15)",
          }}
          animate={{ y: [-10, -80], opacity: [0.4, 0], scale: [0.5, 2] }}
          transition={{ duration: 3, delay: p.delay, repeat: Infinity, ease: "easeOut" }}
        />
      ))}
    </div>
  );
}

export default function Header() {
  const { theme } = useTheme();

  return (
    <header
      style={{
        position: "relative",
        height: 120,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
        background: `linear-gradient(90deg, ${theme.colors.background} 0%, ${theme.colors.panel} 50%, ${theme.colors.background} 100%)`,
        borderBottom: `3px solid ${theme.colors.primary}`,
        overflow: "hidden",
      }}
    >
      <CannonSmoke />
      <span style={{ fontSize: 48, zIndex: 1 }} role="img" aria-label="eagle">🦅</span>
      <div style={{ textAlign: "center", zIndex: 1 }}>
        <h1
          style={{
            fontFamily: "Georgia, serif",
            fontSize: 28,
            fontWeight: "bold",
            color: theme.colors.primary,
            margin: 0,
          }}
        >
          NAPOLEON&apos;S COMMAND PANEL
        </h1>
        <p
          style={{
            fontFamily: "Georgia, serif",
            fontSize: 14,
            color: "#95a5a6",
            margin: 0,
          }}
        >
          Total War Control System
        </p>
      </div>
      <span style={{ fontSize: 48, zIndex: 1 }} role="img" aria-label="crown">👑</span>
    </header>
  );
}
