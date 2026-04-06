"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { ZoomIn, ZoomOut, Maximize2, RotateCcw, Box } from "lucide-react";

export default function DrawingViewer({
  imageUrl,
  cadInfo,
}: {
  imageUrl: string | null;
  cadInfo?: string | null;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [cursor, setCursor] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  const zoomIn = () => setScale((s) => Math.min(s * 1.25, 5));
  const zoomOut = () => setScale((s) => Math.max(s / 1.25, 0.2));
  const fit = () => { setScale(1); setRotation(0); setPan({ x: 0, y: 0 }); };
  const rotate = () => setRotation((r) => (r + 90) % 360);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setDragging(true);
    dragStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      const cx = ((e.clientX - rect.left - rect.width / 2) / scale).toFixed(3);
      const cy = (-(e.clientY - rect.top - rect.height / 2) / scale).toFixed(3);
      setCursor({ x: Number(cx), y: Number(cy) });
    }
    if (dragging) {
      setPan({ x: e.clientX - dragStart.current.x, y: e.clientY - dragStart.current.y });
    }
  }, [dragging, scale]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) zoomIn(); else zoomOut();
  }, []);

  return (
    <div className="bg-surface-2 border border-outline/15 relative overflow-hidden h-full flex flex-col">
      {/* Blueprint grid overlay */}
      <div className="absolute inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: "radial-gradient(circle, var(--color-outline) 1px, transparent 1px)",
          backgroundSize: "20px 20px",
          opacity: 0.04,
        }}
      />

      {/* Toolbar */}
      <div className="absolute top-3 left-3 z-10 flex gap-1">
        {[
          { icon: ZoomIn, action: zoomIn, title: "Zoom In" },
          { icon: ZoomOut, action: zoomOut, title: "Zoom Out" },
          { icon: Maximize2, action: fit, title: "Fit" },
          { icon: RotateCcw, action: rotate, title: "Rotate" },
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

      {/* Canvas */}
      <div
        ref={containerRef}
        className="flex-1 relative cursor-grab active:cursor-grabbing select-none"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={() => setDragging(false)}
        onMouseLeave={() => setDragging(false)}
        onWheel={handleWheel}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt="Drawing"
            draggable={false}
            className="absolute top-1/2 left-1/2 max-w-[90%] max-h-[90%] object-contain"
            style={{
              transform: `translate(calc(-50% + ${pan.x}px), calc(-50% + ${pan.y}px)) scale(${scale}) rotate(${rotation}deg)`,
              filter: "contrast(1.1)",
              transformOrigin: "center center",
            }}
          />
        ) : cadInfo ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <Box size={56} className="text-primary/40 mx-auto mb-4" />
              <p className="text-sm font-heading font-semibold text-text-secondary mb-1">3D CAD File Loaded</p>
              <p className="text-xs text-text-tertiary font-mono">{cadInfo}</p>
              <p className="text-xs text-text-tertiary mt-2" style={{ fontFamily: "var(--font-ko)" }}>
                3D 파일이 로드되었습니다. 하단에서 AI 분석을 실행하세요.
              </p>
              <p className="text-xs text-primary/60 mt-1">
                Use 3D Viewer page for interactive 3D preview
              </p>
            </div>
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-text-tertiary">Upload a drawing to analyze</p>
          </div>
        )}

        {/* Scanning line */}
        {imageUrl && (
          <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-b from-transparent via-primary to-transparent animate-[scan_3s_linear_infinite] opacity-15 pointer-events-none" />
        )}
      </div>

      {/* Bottom Info Bar */}
      <div className="flex items-center gap-6 px-4 py-2 bg-viewer-overlay backdrop-blur-md text-[10px] font-mono text-text-tertiary z-10">
        <span>
          <span className="text-primary">CURSOR POSITION</span>{" "}
          X: <span className="text-text-secondary">{cursor.x.toFixed(3)}</span>{" "}
          Y: <span className="text-text-secondary">{cursor.y.toFixed(3)}</span>
        </span>
        <span>
          <span className="text-text-tertiary">LAYER STATUS</span>{" "}
          <span className="text-text-secondary">VISIBLE (4/4)</span>
        </span>
        <span>{Math.round(scale * 100)}% | {rotation}°</span>
      </div>
    </div>
  );
}
