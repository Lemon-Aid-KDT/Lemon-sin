"use client";

import { useState, useCallback, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Upload, FolderOpen, Trash2, Play } from "lucide-react";
import { apiUpload, apiFetch, drawingThumbnailUrl } from "@/lib/api";
import type { DrawingRecord, StatsResponse } from "@/lib/types";
import ProcessingQueue from "@/components/register/ProcessingQueue";
import type { QueueItem } from "@/components/register/ProcessingQueue";

export default function RegisterPage() {
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [gnnEnabled, setGnnEnabled] = useState(true);
  const [aiEnabled, setAiEnabled] = useState(true);
  const stageTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>[]>>(new Map());

  // Simulate stage progression for visual feedback
  const simulateStages = (fileId: string) => {
    const stages = [
      { key: "ocr", delay: 800, pct: 40 },
      { key: "embedding", delay: 2000, pct: 60 },
      { key: "yolo", delay: 3500, pct: 80 },
    ];
    const timers: ReturnType<typeof setTimeout>[] = [];
    for (const { key, delay, pct } of stages) {
      const t = setTimeout(() => {
        setQueueItems((prev) =>
          prev.map((item) => {
            if (item.fileId !== fileId || item.status === "indexed") return item;
            const nextStages = { ...item.stages, [key]: "done" as const };
            const nextKey = stages[stages.indexOf({ key, delay, pct }) + 1]?.key;
            if (nextKey) nextStages[nextKey] = "processing";
            return { ...item, overallPct: pct, stages: nextStages };
          })
        );
      }, delay);
      timers.push(t);
    }
    stageTimersRef.current.set(fileId, timers);
  };

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<StatsResponse>("/stats"),
  });

  // Single file registration
  const registerMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiUpload<DrawingRecord>("/drawings/register", formData, {
        category: "",
        use_llm: aiEnabled ? "true" : "false",
      });
    },
    onMutate: (file) => {
      const id = Math.random().toString(36).slice(2, 10);
      const newItem: QueueItem = {
        fileName: file.name.toUpperCase(),
        fileSize: `${(file.size / 1024 / 1024).toFixed(1)} MB`,
        fileId: id,
        status: "processing",
        overallPct: 10,
        stages: { ocr: "processing", embedding: "queued", yolo: "queued", rendering: "queued" },
      };
      setQueueItems((prev) => [newItem, ...prev]);
      simulateStages(id);
      return { id };
    },
    onSuccess: (data, _file, ctx) => {
      // Clear simulation timers
      const timers = stageTimersRef.current.get(ctx?.id ?? "");
      timers?.forEach(clearTimeout);
      stageTimersRef.current.delete(ctx?.id ?? "");

      const drawingId = data?.drawing_id ?? "";
      const thumbUrl = drawingId ? drawingThumbnailUrl(drawingId) : undefined;
      setQueueItems((prev) =>
        prev.map((item) =>
          item.fileId === ctx?.id
            ? {
                ...item,
                status: "indexed" as const,
                overallPct: 100,
                stages: { ocr: "done", embedding: "done", yolo: "done", rendering: "done" },
                thumbnailUrl: thumbUrl,
                drawingId,
              }
            : item
        )
      );
    },
    onError: (_err, _file, ctx) => {
      setQueueItems((prev) =>
        prev.map((item) =>
          item.fileId === ctx?.id
            ? { ...item, status: "queued" as const, overallPct: 0 }
            : item
        )
      );
    },
  });

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return;
      Array.from(files).forEach((f) => registerMutation.mutate(f));
    },
    [registerMutation]
  );

  const totalIndexed = stats?.total_drawings ?? 0;

  return (
    <div>
      {/* Header — Stitch style */}
      <div className="flex items-start justify-between mb-6 pb-4 border-b border-outline/15">
        <div>
          <h1 className="text-2xl font-heading font-bold text-text-primary">
            Drawing Registration
          </h1>
          <p className="text-xs text-text-tertiary mt-1 max-w-lg">
            Initialize structural ingestion pipeline. Upload technical assets for
            OCR analysis, neural embedding, and spatial classification.
          </p>
          <p className="text-[11px] text-text-tertiary mt-0.5 max-w-lg" style={{ fontFamily: "var(--font-ko)" }}>
            도면 이미지를 업로드하면 자동으로 OCR, 임베딩, 분류가 수행됩니다.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-4 py-2 border border-outline/20 text-[10px] font-bold uppercase tracking-wider text-text-secondary hover:text-text-primary hover:border-outline/40 transition-colors">
            <FolderOpen size={14} />
            <div className="text-left"><div>Folder Bulk Upload</div><div className="text-[8px] font-normal normal-case tracking-normal opacity-60" style={{ fontFamily: "var(--font-ko)" }}>폴더 일괄 업로드</div></div>
          </button>
          <button
            onClick={() => setQueueItems([])}
            className="flex items-center gap-2 px-4 py-2 border border-outline/20 text-[10px] font-bold uppercase tracking-wider text-text-secondary hover:text-text-primary hover:border-outline/40 transition-colors"
          >
            <Trash2 size={14} />
            <div className="text-left"><div>Clear Queue</div><div className="text-[8px] font-normal normal-case tracking-normal opacity-60" style={{ fontFamily: "var(--font-ko)" }}>큐 초기화</div></div>
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-primary text-background text-[10px] font-bold uppercase tracking-wider hover:bg-primary-dark transition-colors">
            <Play size={14} />
            <div className="text-left"><div>Start Indexing</div><div className="text-[8px] font-normal normal-case tracking-normal opacity-60" style={{ fontFamily: "var(--font-ko)" }}>인덱싱 시작</div></div>
          </button>
        </div>
      </div>

      {/* Two-Column Layout */}
      <div className="grid grid-cols-12 gap-6">
        {/* Left: Upload + Config */}
        <div className="col-span-4 space-y-6">
          {/* Upload Zone */}
          <label className="flex flex-col items-center justify-center h-48 border-2 border-dashed border-outline/30 bg-surface-1 cursor-pointer hover:border-primary/40 transition-colors">
            <Upload size={36} className="text-text-tertiary mb-2 group-hover:text-primary transition-colors" />
            <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">
              Upload Drawings
            </span>
            <span className="text-[10px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>도면 업로드</span>
            <span className="text-[10px] text-text-tertiary mt-1">(PNG, JPG, DXF, DWG, STEP, IGES, STL)</span>
            <span className="text-[10px] text-text-tertiary uppercase mt-0.5">
              Drag &amp; Drop or Click to Browse
            </span>
            <span className="text-[9px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>파일을 끌어놓거나 클릭하여 선택</span>
            <input
              type="file"
              className="hidden"
              multiple
              accept=".png,.jpg,.jpeg,.dxf,.dwg,.stp,.step,.igs,.iges,.stl"
              onChange={(e) => handleFiles(e.target.files)}
            />
          </label>

          {/* Pipeline Configuration */}
          <div className="bg-surface-1 border border-outline/10 p-5">
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-4">
              Pipeline Configuration <span className="text-[9px] font-normal normal-case tracking-normal text-text-tertiary opacity-80 ml-1" style={{ fontFamily: "var(--font-ko)" }}>파이프라인 설정</span>
            </h4>
            <div className="space-y-3">
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-xs text-text-secondary">Enable GNN Structure Embedding <span className="text-[9px] text-text-tertiary" style={{ fontFamily: "var(--font-ko)" }}>GNN 구조 임베딩</span></span>
                <div className="relative">
                  <input type="checkbox" className="sr-only" checked={gnnEnabled} onChange={() => setGnnEnabled(!gnnEnabled)} />
                  <div className={`w-10 h-5 rounded-full transition-colors ${gnnEnabled ? "bg-primary" : "bg-surface-3"}`}>
                    <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${gnnEnabled ? "translate-x-5 ml-0.5" : "translate-x-0.5"}`} />
                  </div>
                </div>
              </label>
              <label className="flex items-center justify-between cursor-pointer">
                <span className="text-xs text-text-secondary">AI Analysis Post-Registration <span className="text-[9px] text-text-tertiary" style={{ fontFamily: "var(--font-ko)" }}>등록 후 AI 분석</span></span>
                <div className="relative">
                  <input type="checkbox" className="sr-only" checked={aiEnabled} onChange={() => setAiEnabled(!aiEnabled)} />
                  <div className={`w-10 h-5 rounded-full transition-colors ${aiEnabled ? "bg-primary" : "bg-surface-3"}`}>
                    <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${aiEnabled ? "translate-x-5 ml-0.5" : "translate-x-0.5"}`} />
                  </div>
                </div>
              </label>
            </div>
            <div className="mt-4 pt-3 border-t border-outline/10 text-[10px] text-text-tertiary font-mono space-y-0.5">
              <div>ACTIVE MODEL: CAD-NET_V2.1</div>
              <div>PRECISION: FP16</div>
              <div>CONTEXT: GLOBAL ARCHITECTURAL</div>
            </div>
          </div>
        </div>

        {/* Right: Processing Queue */}
        <div className="col-span-8">
          <ProcessingQueue items={queueItems} />
          {queueItems.length === 0 && (
            <div className="flex items-center justify-center h-48 text-text-tertiary text-sm">
              Upload drawings to start processing
            </div>
          )}
        </div>
      </div>

      {/* Bottom Stats */}
      <div className="flex justify-center gap-12 mt-8 pt-6 border-t border-outline/10">
        <div className="text-center">
          <div className="text-3xl font-heading font-bold text-primary">{totalIndexed.toLocaleString()}</div>
          <div className="text-[10px] text-text-tertiary uppercase tracking-[0.1em]">Total Indexed</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-heading font-bold text-success">99.8%</div>
          <div className="text-[10px] text-text-tertiary uppercase tracking-[0.1em]">Accuracy</div>
        </div>
      </div>
    </div>
  );
}
