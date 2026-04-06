"use client";

import { CheckCircle, Loader2, Clock, Image as ImageIcon } from "lucide-react";

type StageStatus = "done" | "processing" | "queued";

interface QueueItem {
  fileName: string;
  fileSize: string;
  fileId: string;
  status: "processing" | "indexed" | "queued";
  overallPct: number;
  stages: Record<string, StageStatus>;
  thumbnailUrl?: string;
  drawingId?: string;
}

const STAGE_LABELS = ["OCR Extraction", "Embedding", "YOLO Class", "Rendering"];
const STAGE_KEYS = ["ocr", "embedding", "yolo", "rendering"];

function StageIcon({ status }: { status: StageStatus }) {
  if (status === "done") return <CheckCircle size={14} className="text-success" />;
  if (status === "processing") return <Loader2 size={14} className="text-secondary animate-spin" />;
  return <Clock size={14} className="text-text-tertiary" />;
}

export default function ProcessingQueue({ items }: { items: QueueItem[] }) {
  if (!items.length) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-heading font-bold text-text-primary uppercase tracking-[0.04em]">
          Recently Uploaded Files
        </h3>
        <span className="text-[10px] font-mono px-2 py-0.5 bg-primary/10 text-primary border border-primary/20">
          {items.length} Active Tasks
        </span>
      </div>

      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.fileId} className="bg-surface-2/50 border border-outline/10 p-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-surface-3 border border-outline/15 flex items-center justify-center overflow-hidden">
                  {item.thumbnailUrl ? (
                    <img
                      src={item.thumbnailUrl}
                      alt={item.fileName}
                      className="w-full h-full object-contain"
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                  ) : (
                    <ImageIcon size={16} className="text-text-tertiary" />
                  )}
                </div>
                <div>
                  <div className="text-xs font-bold text-text-primary uppercase font-heading">
                    {item.fileName}
                  </div>
                  <div className="text-[10px] text-text-tertiary font-mono">
                    SIZE: {item.fileSize} | ID: {item.fileId}
                  </div>
                </div>
              </div>
              <span className={`text-[10px] font-bold uppercase font-mono ${
                item.status === "indexed" ? "text-success" :
                item.status === "processing" ? "text-secondary" : "text-text-tertiary"
              }`}>
                {item.status === "processing" ? `${item.overallPct}% Processing` : item.status.toUpperCase()}
              </span>
            </div>

            {/* 4-Stage Pipeline */}
            <div className="grid grid-cols-4 gap-3">
              {STAGE_KEYS.map((key, i) => {
                const status = item.stages[key] || "queued";
                return (
                  <div key={key}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[9px] text-text-tertiary uppercase tracking-wider">
                        {STAGE_LABELS[i]}
                      </span>
                      <StageIcon status={status} />
                    </div>
                    <div className="h-1 bg-surface-3 overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${
                          status === "done" ? "bg-success w-full" :
                          status === "processing" ? "bg-primary w-1/2" : "w-0"
                        }`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export type { QueueItem };
