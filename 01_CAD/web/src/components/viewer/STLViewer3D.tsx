"use client";

import { useRef, useMemo, useCallback } from "react";
import { Canvas, useLoader, useThree } from "@react-three/fiber";
import { OrbitControls, Stage } from "@react-three/drei";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import * as THREE from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

/** Mesh from STL file URL (STLLoader) */
function STLFileMesh({
  url,
  wireframe,
}: {
  url: string;
  wireframe: boolean;
}) {
  const geometry = useLoader(STLLoader, url);

  useMemo(() => {
    geometry.center();
    geometry.computeVertexNormals();
  }, [geometry]);

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color="#5eb4ff"
        metalness={0.3}
        roughness={0.5}
        wireframe={wireframe}
      />
    </mesh>
  );
}

/** Mesh from raw vertices/normals data (for STEP/IGES converted by backend) */
function BufferMesh({
  vertices,
  normals,
  wireframe,
}: {
  vertices: number[];
  normals: number[];
  wireframe: boolean;
}) {
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(vertices, 3)
    );
    if (normals.length > 0) {
      geo.setAttribute(
        "normal",
        new THREE.Float32BufferAttribute(normals, 3)
      );
    } else {
      geo.computeVertexNormals();
    }
    geo.center();
    return geo;
  }, [vertices, normals]);

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color="#5eb4ff"
        metalness={0.3}
        roughness={0.5}
        wireframe={wireframe}
      />
    </mesh>
  );
}

export interface MeshData {
  vertices: number[];
  normals: number[];
}

export interface ViewerControls {
  reset: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
}

export default function STLViewer3D({
  fileUrl,
  meshData,
  wireframe = false,
  onControlsReady,
  onResetCamera,
}: {
  fileUrl?: string;
  meshData?: MeshData;
  wireframe?: boolean;
  onControlsReady?: (controls: ViewerControls) => void;
  /** @deprecated use onControlsReady instead */
  onResetCamera?: (reset: () => void) => void;
}) {
  const controlsRef = useRef<OrbitControlsImpl>(null);

  const handleCreated = ({ camera }: { camera: THREE.Camera }) => {
    const controls: ViewerControls = {
      reset: () => controlsRef.current?.reset(),
      zoomIn: () => {
        camera.position.multiplyScalar(0.8);
        controlsRef.current?.update();
      },
      zoomOut: () => {
        camera.position.multiplyScalar(1.25);
        controlsRef.current?.update();
      },
    };
    onControlsReady?.(controls);
    onResetCamera?.(() => controlsRef.current?.reset());
  };

  return (
    <Canvas
      camera={{ position: [0, 0, 5], fov: 50 }}
      style={{ background: "var(--bg)" }}
      onCreated={handleCreated}
    >
      <Stage environment="city" intensity={0.5}>
        {fileUrl && <STLFileMesh url={fileUrl} wireframe={wireframe} />}
        {meshData && !fileUrl && (
          <BufferMesh
            vertices={meshData.vertices}
            normals={meshData.normals}
            wireframe={wireframe}
          />
        )}
      </Stage>
      <OrbitControls
        ref={controlsRef}
        enableDamping
        dampingFactor={0.1}
        autoRotate={false}
      />
    </Canvas>
  );
}
