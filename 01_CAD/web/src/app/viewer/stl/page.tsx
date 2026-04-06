"use client";

import { useState, useCallback, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { Box, Trash2, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { apiUpload } from "@/lib/api";
import type { MeshData, ViewerControls } from "@/components/viewer/STLViewer3D";

const STLViewer3D = dynamic(
  () => import("@/components/viewer/STLViewer3D"),
  { ssr: false, loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  )}
);

interface STLResult {
  vertices: number[];
  normals: number[];
  triangle_count: number;
  vertex_count: number;
  bbox: { min: number[]; max: number[] };
  format: string;
  file_size_bytes: number;
}

const STL_EXTS = [".stl"];

export default function STLViewerPage() {
  const [result, setResult] = useState<STLResult | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [meshData, setMeshData] = useState<MeshData | null>(null);
  const [wireframe, setWireframe] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const viewerControlsRef = useRef<ViewerControls | null>(null);
  const resetCameraRef = useRef<(() => void) | null>(null);

  const parseMutation = useMutation({
    mutationFn: async (file: File) => {
      setParseError(null);
      const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
      const isStl = STL_EXTS.includes(ext);

      // STL files: create blob URL for direct STLLoader parsing
      // STEP/IGES files: only use backend response vertices/normals
      if (isStl) {
        setFileUrl(URL.createObjectURL(file));
        setMeshData(null);
      } else {
        setFileUrl(null);
      }

      const fd = new FormData();
      fd.append("file", file);
      return apiUpload<STLResult>("/viewer/stl", fd);
    },
    onSuccess: (data, file) => {
      setResult(data);
      const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
      const isStl = STL_EXTS.includes(ext);

      // For non-STL (STEP/IGES): use backend-converted vertices/normals
      if (!isStl && data.vertices?.length > 0) {
        setMeshData({ vertices: data.vertices, normals: data.normals ?? [] });
      }
    },
    onError: (err) => {
      setParseError(err instanceof Error ? err.message : "Failed to parse file");
    },
  });

  const handleClear = useCallback(() => {
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    setResult(null);
    setFileUrl(null);
    setMeshData(null);
    setWireframe(false);
    setParseError(null);
  }, [fileUrl]);

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-heading font-bold uppercase tracking-tight">3D Viewer</h1>
          <p className="text-xs text-text-tertiary uppercase tracking-[0.1em] mt-0.5">WebGL-based 3D mesh visualization</p>
          <p className="text-[11px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>WebGL 기반 3D 메시 시각화</p>
        </div>
        {result && (
          <button
            onClick={handleClear}
            className="flex items-center gap-2 px-4 py-2 border border-outline/20 text-[10px] font-bold uppercase tracking-wider text-text-secondary hover:text-error hover:border-error/30 transition-colors"
          >
            <Trash2 size={14} />
            <div className="text-left">
              <div>Clear File</div>
              <div className="text-[9px] font-normal normal-case tracking-normal opacity-60" style={{ fontFamily: "var(--font-ko)" }}>파일 초기화</div>
            </div>
          </button>
        )}
      </div>

      {!result ? (
        <div>
          <label className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-outline/30 bg-surface-1 cursor-pointer hover:border-primary/40 transition-colors">
            <Box size={40} className="text-text-tertiary mb-3" />
            <span className="text-sm font-bold text-text-secondary uppercase">Upload 3D File</span>
            <span className="text-[10px] text-text-tertiary" style={{ fontFamily: "var(--font-ko)" }}>3D 파일 업로드</span>
            <span className="text-[10px] text-text-tertiary mt-1">STL, STEP, IGES — Drag & Drop or Click</span>
            <span className="text-[9px] text-text-tertiary" style={{ fontFamily: "var(--font-ko)" }}>파일을 끌어놓거나 클릭하여 선택</span>
            <input type="file" className="hidden" accept=".stl,.stp,.step,.igs,.iges" onChange={(e) => e.target.files?.[0] && parseMutation.mutate(e.target.files[0])} />
            {parseMutation.isPending && <div className="mt-3 w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />}
          </label>
          {parseError && (
            <div className="mt-4 p-4 bg-error/10 border border-error/20 text-xs text-error space-y-2">
              <p className="font-bold">{parseError}</p>
              <div className="text-text-tertiary space-y-1">
                {parseError.includes("2D") || parseError.includes("와이어프레임") ? (
                  <>
                    <p style={{ fontFamily: "var(--font-ko)" }}>
                      이 파일은 2D 와이어프레임 형태로, 3D 메시 변환이 불가능합니다.
                    </p>
                    <p className="text-primary mt-1">
                      DXF Viewer 페이지에서 2D 도면으로 확인하거나, 3D 솔리드가 포함된 IGES 파일을 업로드하세요.
                    </p>
                  </>
                ) : parseError.includes("CadQuery") || parseError.includes("설치") ? (
                  <>
                    <p>STEP/IGES 파일의 3D 변환에는 CadQuery(OCP) 라이브러리가 필요합니다.</p>
                    <p className="font-mono bg-surface-2 px-2 py-1 rounded-sm text-text-secondary">
                      pip install cadquery
                    </p>
                    <p style={{ fontFamily: "var(--font-ko)" }}>
                      또는 conda 환경에서: conda install -c conda-forge cadquery
                    </p>
                  </>
                ) : (
                  <p style={{ fontFamily: "var(--font-ko)" }}>
                    파일 변환 중 오류가 발생했습니다. 파일이 손상되었거나 지원하지 않는 형식일 수 있습니다.
                  </p>
                )}
                <p className="text-primary mt-2">
                  STL 파일은 별도 변환 없이 바로 열 수 있습니다.
                </p>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4" style={{ height: "calc(100vh - 12rem)" }}>
          {/* 3D Canvas (3/4) */}
          <div className="col-span-3 bg-surface-2 border border-outline/15 relative overflow-hidden">
            {/* Zoom controls overlay */}
            <div className="absolute top-3 left-3 z-10 flex gap-1">
              {[
                { icon: ZoomIn, action: () => viewerControlsRef.current?.zoomIn(), title: "Zoom In" },
                { icon: ZoomOut, action: () => viewerControlsRef.current?.zoomOut(), title: "Zoom Out" },
                { icon: Maximize2, action: () => viewerControlsRef.current?.reset(), title: "Reset View" },
              ].map(({ icon: Icon, action, title }) => (
                <button
                  key={title}
                  onClick={action}
                  title={title}
                  className="w-9 h-9 bg-surface-3/85 backdrop-blur-md border border-outline/20 text-text-primary flex items-center justify-center hover:border-primary/40 hover:shadow-[0_0_6px_rgba(94,180,255,0.3)] transition-all"
                >
                  <Icon size={16} />
                </button>
              ))}
            </div>

            {(fileUrl || meshData) ? (
              <STLViewer3D
                fileUrl={fileUrl ?? undefined}
                meshData={meshData ?? undefined}
                wireframe={wireframe}
                onControlsReady={(c) => { viewerControlsRef.current = c; }}
                onResetCamera={(reset) => { resetCameraRef.current = reset; }}
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-text-tertiary">
                  <Box size={48} className="mx-auto mb-3 opacity-40" />
                  <p className="text-sm">Mesh data not available for 3D preview</p>
                  <p className="text-[10px] mt-1" style={{ fontFamily: "var(--font-ko)" }}>3D 미리보기용 메시 데이터 없음</p>
                </div>
              </div>
            )}
            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-b from-transparent via-primary to-transparent animate-[scan_3s_linear_infinite] opacity-15 pointer-events-none" />
          </div>

          {/* Mesh Info (1/4) */}
          <div className="col-span-1 space-y-4 overflow-y-auto">
            <div className="bg-surface-1 border border-outline/10 p-4">
              <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
                Mesh Information <span className="text-[9px] font-normal normal-case tracking-normal text-text-tertiary opacity-80" style={{ fontFamily: "var(--font-ko)" }}>메시 정보</span>
              </h4>
              <div className="space-y-2">
                {[
                  ["Triangles", result.triangle_count.toLocaleString()],
                  ["Vertices", result.vertex_count.toLocaleString()],
                  ["Format", result.format.toUpperCase()],
                  ["File Size", `${(result.file_size_bytes / 1024).toFixed(1)} KB`],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between text-xs">
                    <span className="text-text-tertiary">{label}</span>
                    <span className="font-mono text-text-secondary">{value}</span>
                  </div>
                ))}
              </div>
            </div>

            {result.bbox && (
              <div className="bg-surface-1 border border-outline/10 p-4">
                <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
                  Bounding Box
                </h4>
                <div className="space-y-1 text-[10px] font-mono">
                  <div className="flex justify-between"><span className="text-text-tertiary">Min</span><span className="text-text-secondary">{result.bbox.min.map((v: number) => v.toFixed(2)).join(", ")}</span></div>
                  <div className="flex justify-between"><span className="text-text-tertiary">Max</span><span className="text-text-secondary">{result.bbox.max.map((v: number) => v.toFixed(2)).join(", ")}</span></div>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <button
                onClick={() => setWireframe((w) => !w)}
                className={`w-full py-2 border text-[10px] font-bold uppercase tracking-wider transition-colors ${
                  wireframe
                    ? "border-primary/30 text-primary"
                    : "border-outline/20 text-text-secondary hover:text-primary hover:border-primary/30"
                }`}
              >
                {wireframe ? "Wireframe ON" : "Toggle Wireframe"}
                <span className="block text-[8px] font-normal normal-case tracking-normal opacity-60" style={{ fontFamily: "var(--font-ko)" }}>와이어프레임 전환</span>
              </button>
              <button
                onClick={() => resetCameraRef.current?.()}
                className="w-full py-2 border border-outline/20 text-[10px] font-bold uppercase tracking-wider text-text-secondary hover:text-primary hover:border-primary/30 transition-colors"
              >
                Reset Camera
                <span className="block text-[8px] font-normal normal-case tracking-normal opacity-60" style={{ fontFamily: "var(--font-ko)" }}>카메라 초기화</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
