import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Grid, Float } from "@react-three/drei";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import * as THREE from "three";
import { useBridge } from "../lib/useBridge";
import type { VoiceState } from "../lib/bridge";

const RED = "#ff2a2a";
const DIM = "#3d0f14";

function useEnergy() {
  const { voice, level } = useBridge();
  const ref = useRef({ voice, level });
  ref.current = { voice, level };
  return ref;
}

/** Audio-reactive mouth: a curved row of bars that dance with voice energy. */
function Mouth() {
  const energy = useEnergy();
  const bars = useMemo(() => {
    const arr: { x: number; w: number; phase: number; mesh?: THREE.Mesh }[] = [];
    const N = 21;
    for (let i = 0; i < N; i++) {
      const t = (i / (N - 1)) * 2 - 1; // -1..1
      arr.push({ x: t * 0.62, w: 0.055 + Math.abs(t) * 0.02, phase: i * 0.9 });
    }
    return arr;
  }, []);
  const group = useRef<THREE.Group>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const { voice, level } = energy.current;
    const speaking = voice === "speaking";
    const amp = speaking ? 0.55 + level * 2.2 : 0.045;
    group.current?.children.forEach((child, i) => {
      const m = child as THREE.Mesh;
      const n =
        Math.abs(Math.sin(t * 11 + bars[i].phase) * 0.6) +
        Math.abs(Math.sin(t * 23 + bars[i].phase * 1.7) * 0.4);
      const s = speaking
        ? 0.08 + n * amp * (1 - Math.abs(bars[i].x) * 0.35)
        : 0.05 + n * amp;
      m.scale.y = s;
      const mat = m.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = speaking ? 1.6 + n * 2.4 : 0.9;
    });
  });

  return (
    <group ref={group} position={[0, -0.52, 1.02]}>
      {bars.map((b, i) => (
        <mesh key={i} position={[b.x, 0, 0]}>
          <boxGeometry args={[b.w, 0.3, 0.05]} />
          <meshStandardMaterial color="#1a0508" emissive={RED} emissiveIntensity={1} />
        </mesh>
      ))}
    </group>
  );
}

function Eyes({ voice }: { voice: VoiceState }) {
  const left = useRef<THREE.Mesh>(null);
  const right = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const blink = Math.sin(t * 0.7) > 0.995 ? 0.15 : 1;
    const think = voice === "thinking" ? 0.55 + Math.abs(Math.sin(t * 9)) * 0.45 : 1;
    [left, right].forEach((r) => {
      if (!r.current) return;
      r.current.scale.y = blink * think;
      const mat = r.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = voice === "thinking" ? 4.5 : 2.6;
    });
  });
  const geo = <octahedronGeometry args={[0.09, 0]} />;
  const mat = <meshStandardMaterial color="#1a0508" emissive={RED} emissiveIntensity={2.6} />;
  return (
    <group position={[0, 0.18, 1.04]}>
      <mesh ref={left} position={[-0.32, 0, 0]} rotation={[0, 0, Math.PI / 4]}>
        {geo}
        {mat}
      </mesh>
      <mesh ref={right} position={[0.32, 0, 0]} rotation={[0, 0, Math.PI / 4]}>
        {geo}
        {mat}
      </mesh>
    </group>
  );
}

function Rings({ voice }: { voice: VoiceState }) {
  const r1 = useRef<THREE.Mesh>(null);
  const r2 = useRef<THREE.Mesh>(null);
  const r3 = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const boost = voice === "thinking" ? 3.2 : voice === "speaking" ? 1.8 : 1;
    if (r1.current) {
      r1.current.rotation.z = t * 0.35 * boost;
      r1.current.rotation.x = Math.PI / 2.15 + Math.sin(t * 0.4) * 0.12;
    }
    if (r2.current) {
      r2.current.rotation.z = -t * 0.22 * boost;
      r2.current.rotation.y = Math.sin(t * 0.3) * 0.5;
    }
    if (r3.current) {
      r3.current.rotation.z = t * 0.5 * boost;
    }
  });
  return (
    <group>
      <mesh ref={r1} rotation={[Math.PI / 2.15, 0, 0]}>
        <torusGeometry args={[1.85, 0.006, 8, 128]} />
        <meshStandardMaterial color={RED} emissive={RED} emissiveIntensity={1.8} />
      </mesh>
      <mesh ref={r2} rotation={[Math.PI / 2.8, 0.4, 0]}>
        <torusGeometry args={[2.25, 0.004, 8, 128]} />
        <meshStandardMaterial color={DIM} emissive={RED} emissiveIntensity={0.9} />
      </mesh>
      <mesh ref={r3} rotation={[0, Math.PI / 3, Math.PI / 5]}>
        <torusGeometry args={[2.7, 0.003, 8, 128]} />
        <meshStandardMaterial color={DIM} emissive={RED} emissiveIntensity={0.6} />
      </mesh>
    </group>
  );
}

function Head() {
  const energy = useEnergy();
  const head = useRef<THREE.Group>(null);
  const core = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const { voice, level } = energy.current;
    if (head.current) {
      // subtle idle scan + react to voice
      head.current.rotation.y = Math.sin(t * 0.25) * 0.16;
      head.current.rotation.x = Math.sin(t * 0.19) * 0.06;
      head.current.position.y = Math.sin(t * 0.8) * 0.03;
    }
    if (core.current) {
      const pulse = voice === "speaking" ? 1 + level * 0.9 : 1 + Math.sin(t * 2.1) * 0.05;
      core.current.scale.setScalar(pulse);
      const mat = core.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = voice === "speaking" ? 4.5 + level * 5 : 2.4 + Math.sin(t * 2.1) * 0.8;
    }
  });

  return (
    <group ref={head}>
      {/* dark shell */}
      <mesh>
        <icosahedronGeometry args={[1.28, 1]} />
        <meshStandardMaterial color="#0c0306" metalness={0.9} roughness={0.35} flatShading />
      </mesh>
      {/* red wireframe overlay */}
      <mesh scale={1.003}>
        <icosahedronGeometry args={[1.28, 1]} />
        <meshBasicMaterial color={RED} wireframe transparent opacity={0.85} />
      </mesh>
      {/* cheek plates */}
      <mesh position={[0, -0.18, 1.02]}>
        <boxGeometry args={[1.5, 0.02, 0.02]} />
        <meshBasicMaterial color={RED} />
      </mesh>
      <mesh position={[0, 0.52, 0.98]}>
        <boxGeometry args={[1.1, 0.015, 0.015]} />
        <meshBasicMaterial color={RED} />
      </mesh>
      {/* inner core */}
      <mesh ref={core} position={[0, 0, 0.2]}>
        <icosahedronGeometry args={[0.42, 1]} />
        <meshStandardMaterial color="#200407" emissive={RED} emissiveIntensity={2.4} />
      </mesh>
      <Eyes voice={energy.current.voice} />
      <Mouth />
    </group>
  );
}

function FaceRig() {
  const snap = useBridge();
  const voice = snap.voice;
  return (
    <group>
      <Float speed={1.4} rotationIntensity={0.12} floatIntensity={0.35}>
        <Head />
      </Float>
      <Rings voice={voice} />
      <Grid
        position={[0, -1.9, 0]}
        args={[30, 30]}
        cellSize={0.55}
        cellThickness={0.6}
        cellColor="#240710"
        sectionSize={2.75}
        sectionThickness={1.1}
        sectionColor={RED}
        fadeDistance={26}
        fadeStrength={1.4}
        infiniteGrid
      />
    </group>
  );
}

export default function Face() {
  return (
    <Canvas
      camera={{ position: [0, 0.1, 4.6], fov: 42 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: false }}
      onCreated={({ scene }) => {
        scene.background = new THREE.Color("#050103");
        scene.fog = new THREE.Fog("#050103", 7, 22);
      }}
    >
      <ambientLight intensity={0.25} color="#ff5533" />
      <pointLight position={[3, 3, 4]} intensity={14} color={RED} distance={16} />
      <pointLight position={[-4, -2, 2]} intensity={8} color="#ff7a45" distance={14} />
      <FaceRig />
      <EffectComposer>
        <Bloom intensity={1.35} luminanceThreshold={0.18} luminanceSmoothing={0.4} mipmapBlur />
        <Vignette eskil={false} offset={0.18} darkness={0.85} />
      </EffectComposer>
    </Canvas>
  );
}
