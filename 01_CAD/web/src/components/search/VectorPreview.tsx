"use client";

import { X } from "lucide-react";
import { drawingThumbnailUrl } from "@/lib/api";

export default function VectorPreview({
  drawingId,
  score,
  channelScores,
  onClose,
}: {
  drawingId: string;
  score: number;
  channelScores: Record<string, number>;
  onClose: () => void;
}) {
  return (
    <div className="fixed bottom-12 right-6 w-72 bg-surface-1 border border-outline/20 shadow-2xl shadow-black/50 z-40 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-outline/15">
        <div>
          <span className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em]">
            Vector Preview
          </span>
          <span className="text-[9px] text-text-tertiary ml-1" style={{ fontFamily: "var(--font-ko)" }}>벡터 미리보기</span>
        </div>
        <button
          onClick={onClose}
          className="text-text-tertiary hover:text-text-primary transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      {/* Image */}
      <div className="aspect-square bg-viewer-bg p-4 flex items-center justify-center">
        <img
          src={drawingThumbnailUrl(drawingId)}
          alt="preview"
          className="max-w-full max-h-full opacity-80 grayscale"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      </div>

      {/* Metrics */}
      <div className="p-4 space-y-2.5 text-[11px]">
        <div className="flex justify-between">
          <span className="text-text-tertiary">Embedding Model <span className="text-[9px] opacity-60" style={{ fontFamily: "var(--font-ko)" }}>임베딩 모델</span></span>
          <span className="text-text-secondary font-mono">CLIP-ViT-L/14</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-tertiary">Top Cluster Similarity <span className="text-[9px] opacity-60" style={{ fontFamily: "var(--font-ko)" }}>유사도</span></span>
          <span className="text-secondary font-mono font-bold">
            {score.toFixed(4)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-tertiary">Part Identification <span className="text-[9px] opacity-60" style={{ fontFamily: "var(--font-ko)" }}>부품 식별</span></span>
          <span className="text-primary font-mono">
            {Math.round(score * 100)}% Confidence
          </span>
        </div>
        {Object.entries(channelScores).length > 0 && (
          <div className="pt-2 border-t border-outline/10 space-y-1">
            {Object.entries(channelScores).map(([ch, s]) => (
              <div key={ch} className="flex justify-between text-[10px]">
                <span className="text-text-tertiary uppercase">{ch}</span>
                <span className="text-text-secondary font-mono">
                  {(s as number).toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
