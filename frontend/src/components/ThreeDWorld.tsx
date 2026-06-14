import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid } from '@react-three/drei';
import * as THREE from 'three';
import type { FrameData } from '../utils/types';
import { useMemo, useRef } from 'react';

// MediaPipe 33-landmark connections
const POSE_CONNECTIONS_3D = [
  // Torso
  ['LEFT_SHOULDER', 'RIGHT_SHOULDER'],
  ['LEFT_SHOULDER', 'LEFT_HIP'],
  ['RIGHT_SHOULDER', 'RIGHT_HIP'],
  ['LEFT_HIP', 'RIGHT_HIP'],
  // Right arm
  ['RIGHT_SHOULDER', 'RIGHT_ELBOW'],
  ['RIGHT_ELBOW', 'RIGHT_WRIST'],
  // Left arm
  ['LEFT_SHOULDER', 'LEFT_ELBOW'],
  ['LEFT_ELBOW', 'LEFT_WRIST'],
  // Right leg
  ['RIGHT_HIP', 'RIGHT_KNEE'],
  ['RIGHT_KNEE', 'RIGHT_ANKLE'],
  ['RIGHT_ANKLE', 'RIGHT_FOOT_INDEX'],
  ['RIGHT_ANKLE', 'RIGHT_HEEL'],
  ['RIGHT_HEEL', 'RIGHT_FOOT_INDEX'],
  // Left leg
  ['LEFT_HIP', 'LEFT_KNEE'],
  ['LEFT_KNEE', 'LEFT_ANKLE'],
  ['LEFT_ANKLE', 'LEFT_FOOT_INDEX'],
  ['LEFT_ANKLE', 'LEFT_HEEL'],
  ['LEFT_HEEL', 'LEFT_FOOT_INDEX'],
  // Head
  ['NOSE', 'LEFT_EYE'],
  ['NOSE', 'RIGHT_EYE'],
  ['LEFT_EYE', 'LEFT_EAR'],
  ['RIGHT_EYE', 'RIGHT_EAR'],
];

interface ThreeDWorldProps {
  activeFrame: FrameData | null;
}

function Skeleton({ landmarks }: { landmarks: Record<string, { x: number; y: number; z: number; v?: number }> }) {
  const joints = useMemo(() => {
    return Object.entries(landmarks)
      .filter(([_, lm]) => (lm.v ?? 1) > 0.05)
      .map(([name, lm]) => {
        // MediaPipe coords: y is down. z is relative depth. 
        // Negate y to stand upright, negate z so +Z is towards camera.
        return { name, pos: new THREE.Vector3(lm.x, -lm.y, -lm.z) };
      });
  }, [landmarks]);

  const bones = useMemo(() => {
    const lines: THREE.Vector3[][] = [];
    for (const [p1, p2] of POSE_CONNECTIONS_3D) {
      const l1 = landmarks[p1];
      const l2 = landmarks[p2];
      if (l1 && l2 && (l1.v ?? 1) > 0.05 && (l2.v ?? 1) > 0.05) {
        lines.push([
          new THREE.Vector3(l1.x, -l1.y, -l1.z),
          new THREE.Vector3(l2.x, -l2.y, -l2.z)
        ]);
      }
    }
    return lines;
  }, [landmarks]);

  // Add a slight vertical offset to ground the skeleton
  const yOffset = 0.8;

  return (
    <group position={[0, yOffset, 0]}>
      {joints.map(({ name, pos }) => {
        // Color coded aesthetic for joints
        const isRight = name.includes('RIGHT');
        const isLeft = name.includes('LEFT');
        const color = isRight ? '#ff7b00' : isLeft ? '#00a8ff' : '#ffffff';
        return (
          <mesh key={name} position={pos}>
            <sphereGeometry args={[0.035, 16, 16]} />
            <meshStandardMaterial color={color} roughness={0.1} metalness={0.5} />
          </mesh>
        );
      })}
      
      {bones.map((pts, i) => {
        const geometry = new THREE.BufferGeometry().setFromPoints(pts);
        return (
          <line key={i} geometry={geometry}>
            <lineBasicMaterial color="#ffffff" linewidth={3} transparent opacity={0.6} />
          </line>
        );
      })}
    </group>
  );
}

export function ThreeDWorld({ activeFrame }: ThreeDWorldProps) {
  const orbitRef = useRef<any>(null);

  const setView = (pos: [number, number, number]) => {
    if (orbitRef.current) {
      orbitRef.current.object.position.set(...pos);
      orbitRef.current.target.set(0, 0.8, 0);
      orbitRef.current.update();
    }
  };

  return (
    <div className="three-d-world-container" style={{ width: '100%', aspectRatio: '16/9', background: '#0a0a0a', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-subtle)', position: 'relative' }}>
      
      {/* Label Overlay */}
      <div style={{ position: 'absolute', top: 12, left: 12, zIndex: 10, background: 'rgba(0,0,0,0.5)', padding: '4px 8px', borderRadius: '4px' }}>
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
          3D World View
        </span>
      </div>

      {/* Camera Controls */}
      <div style={{ position: 'absolute', bottom: 12, right: 12, zIndex: 10, display: 'flex', gap: '8px', background: 'rgba(0,0,0,0.5)', padding: '4px 8px', borderRadius: '6px' }}>
        <button className="speed-btn" onClick={() => setView([0, 1, 3])}>Front</button>
        <button className="speed-btn" onClick={() => setView([3, 1, 0])}>Side</button>
        <button className="speed-btn" onClick={() => setView([0, 4, 0.1])}>Top</button>
        <button className="speed-btn" onClick={() => setView([1.5, 1.5, 2.5])}>Iso</button>
      </div>

      <Canvas camera={{ position: [1.5, 1.5, 2.5], fov: 45 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 10]} intensity={1} />
        
        {/* The Qualisys-like grid floor */}
        <Grid 
          infiniteGrid 
          fadeDistance={10} 
          sectionColor="#444" 
          cellColor="#222" 
          position={[0, -0.5, 0]} 
        />
        
        {activeFrame?.landmarks_3d && (
          <Skeleton landmarks={activeFrame.landmarks_3d} />
        )}
        
        <OrbitControls ref={orbitRef} makeDefault enableDamping dampingFactor={0.1} target={[0, 0.8, 0]} />
      </Canvas>
    </div>
  );
}
