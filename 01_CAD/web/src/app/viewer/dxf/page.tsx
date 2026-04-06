"use client";

import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { Layers3, Eye, EyeOff, Trash2 } from "lucide-react";
import { apiUpload } from "@/lib/api";

interface DXFLayer { name: string; color: string; entity_count: number; visible: boolean; }
interface DXFResult { svg: string; layers: DXFLayer[]; entities: Record<string, number>; total_entities: number; }

export default function DXFViewerPage() {
  const [result, setResult] = useState<DXFResult | null>(null);
  const [hiddenLayers, setHiddenLayers] = useState<Set<string>>(new Set());

  const convertMutation = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return apiUpload<DXFResult>("/viewer/dxf", fd);
    },
    onSuccess: (data) => setResult(data),
  });

  const handleClear = useCallback(() => {
    setResult(null);
    setHiddenLayers(new Set());
  }, []);

  const toggleLayer = (name: string) => {
    setHiddenLayers((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-heading font-bold uppercase tracking-tight">DXF Viewer</h1>
          <p className="text-xs text-text-tertiary uppercase tracking-[0.1em] mt-0.5">Interactive 2D drawing viewer with layer controls</p>
          <p className="text-[11px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>레이어 제어가 가능한 인터랙티브 2D 도면 뷰어</p>
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
        <label className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-outline/30 bg-surface-1 cursor-pointer hover:border-primary/40 transition-colors">
          <Layers3 size={40} className="text-text-tertiary mb-3" />
          <span className="text-sm font-bold text-text-secondary uppercase">Upload DXF File</span>
          <span className="text-[10px] text-text-tertiary" style={{ fontFamily: "var(--font-ko)" }}>DXF 파일 업로드</span>
          <span className="text-[10px] text-text-tertiary mt-1">Drag & Drop or Click to Browse</span>
          <span className="text-[9px] text-text-tertiary" style={{ fontFamily: "var(--font-ko)" }}>파일을 끌어놓거나 클릭하여 선택</span>
          <input type="file" className="hidden" accept=".dxf" onChange={(e) => e.target.files?.[0] && convertMutation.mutate(e.target.files[0])} />
          {convertMutation.isPending && <div className="mt-3 w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />}
        </label>
      ) : (
        <div className="grid grid-cols-4 gap-4" style={{ height: "calc(100vh - 12rem)" }}>
          {/* SVG Viewer (3/4) */}
          <div className="col-span-3 bg-surface-2 border border-outline/15 overflow-auto p-4">
            <div dangerouslySetInnerHTML={{ __html: result.svg }} className="w-full dxf-svg-container" />
          </div>

          {/* Right Panel (1/4) */}
          <div className="col-span-1 space-y-4 overflow-y-auto">
            {/* Layers */}
            <div className="bg-surface-1 border border-outline/10 p-4">
              <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
                Layers 레이어 ({result.layers.length})
              </h4>
              <div className="space-y-1">
                {result.layers.map((layer) => (
                  <button key={layer.name} onClick={() => toggleLayer(layer.name)}
                    className="flex items-center justify-between w-full px-2 py-1.5 text-xs hover:bg-surface-2 transition-colors rounded-sm">
                    <div className="flex items-center gap-2">
                      {hiddenLayers.has(layer.name) ? <EyeOff size={12} className="text-text-tertiary" /> : <Eye size={12} className="text-primary" />}
                      <span className={hiddenLayers.has(layer.name) ? "text-text-tertiary" : "text-text-secondary"}>{layer.name}</span>
                    </div>
                    <span className="text-[10px] font-mono text-text-tertiary">{layer.entity_count}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Entity Stats */}
            <div className="bg-surface-1 border border-outline/10 p-4">
              <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
                Entities 엔티티 ({result.total_entities})
              </h4>
              <div className="space-y-1">
                {Object.entries(result.entities).sort(([,a],[,b]) => b - a).map(([type, count]) => (
                  <div key={type} className="flex justify-between text-xs">
                    <span className="text-text-secondary">{type}</span>
                    <span className="font-mono text-text-tertiary">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
