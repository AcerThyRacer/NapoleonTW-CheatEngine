/**
 * Interactive 3D battle map using Three.js (via @react-three/fiber).
 * Renders a stylised Napoleon-era battlefield with terrain, unit markers,
 * and hardware-accelerated particle effects for cannon fire and smoke.
 */

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { useTheme } from "../hooks/useTheme";

/* ---------- terrain plane ---------- */

function Terrain() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
      <planeGeometry args={[40, 40, 64, 64]} />
      <meshStandardMaterial color="#3a5f3a" roughness={0.9} />
    </mesh>
  );
}

/* ---------- unit marker ---------- */

function UnitMarker({ position, color }: { position: [number, number, number]; color: string }) {
  return (
    <mesh position={position} castShadow>
      <cylinderGeometry args={[0.3, 0.3, 0.6, 16]} />
      <meshStandardMaterial color={color} />
    </mesh>
  );
}

/* ---------- cannon fire particles ---------- */

function CannonParticles({ count = 200 }: { count?: number }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const particles = useMemo(() => {
    return Array.from({ length: count }, () => ({
      position: new THREE.Vector3(
        (Math.random() - 0.5) * 30,
        Math.random() * 5,
        (Math.random() - 0.5) * 30
      ),
      velocity: new THREE.Vector3(
        (Math.random() - 0.5) * 0.02,
        Math.random() * 0.03 + 0.01,
        (Math.random() - 0.5) * 0.02
      ),
      life: Math.random(),
    }));
  }, [count]);

  useFrame(() => {
    if (!meshRef.current) return;
    particles.forEach((p, i) => {
      p.position.add(p.velocity);
      p.life -= 0.005;
      if (p.life <= 0) {
        p.position.set((Math.random() - 0.5) * 30, 0, (Math.random() - 0.5) * 30);
        p.life = 1;
      }
      dummy.position.copy(p.position);
      dummy.scale.setScalar(p.life * 0.15);
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial color="#ff6600" transparent opacity={0.5} />
    </instancedMesh>
  );
}

/* ---------- smoke particles ---------- */

function SmokeParticles({ count = 150 }: { count?: number }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const particles = useMemo(() => {
    return Array.from({ length: count }, () => ({
      position: new THREE.Vector3(
        (Math.random() - 0.5) * 25,
        Math.random() * 3,
        (Math.random() - 0.5) * 25
      ),
      velocity: new THREE.Vector3(
        (Math.random() - 0.5) * 0.01,
        Math.random() * 0.02 + 0.005,
        (Math.random() - 0.5) * 0.01
      ),
      life: Math.random(),
    }));
  }, [count]);

  useFrame(() => {
    if (!meshRef.current) return;
    particles.forEach((p, i) => {
      p.position.add(p.velocity);
      p.life -= 0.003;
      if (p.life <= 0) {
        p.position.set((Math.random() - 0.5) * 25, 0, (Math.random() - 0.5) * 25);
        p.life = 1;
      }
      dummy.position.copy(p.position);
      dummy.scale.setScalar(p.life * 0.3);
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial color="#cccccc" transparent opacity={0.2} />
    </instancedMesh>
  );
}

/* ---------- main component ---------- */

export default function BattleMap() {
  const { theme } = useTheme();

  // Procedurally placed unit markers
  const unitPositions: Array<{ pos: [number, number, number]; color: string }> = [
    { pos: [-6, 0.3, -3], color: "#2980b9" },
    { pos: [-4, 0.3, -2], color: "#2980b9" },
    { pos: [-5, 0.3, 0], color: "#2980b9" },
    { pos: [5, 0.3, 2], color: "#c0392b" },
    { pos: [7, 0.3, 1], color: "#c0392b" },
    { pos: [6, 0.3, -1], color: "#c0392b" },
  ];

  return (
    <div
      style={{
        width: "100%",
        height: 360,
        border: `1px solid ${theme.colors.primary}`,
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      <Canvas
        shadows
        camera={{ position: [15, 12, 15], fov: 50 }}
        style={{ background: "#1a1a2e" }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 15, 10]} intensity={0.8} castShadow />
        <Terrain />
        {unitPositions.map((u, i) => (
          <UnitMarker key={i} position={u.pos} color={u.color} />
        ))}
        <CannonParticles />
        <SmokeParticles />
        <OrbitControls enableDamping dampingFactor={0.1} />
      </Canvas>
    </div>
  );
}
