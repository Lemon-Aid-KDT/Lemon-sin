"use client";

import { drawingThumbnailUrl } from "@/lib/api";
import { Star } from "lucide-react";

function matchColor(score: number): string {
  if (score >= 0.95) return "var(--color-secondary)";
  if (score >= 0.9) return "var(--color-primary)";
  return "var(--color-text-secondary)";
}

export default function ResultCard({
  drawingId,
  fileName,
  score,
  category,
  partNumber,
  fileSize,
  modified,
  onClick,
}: {
  drawingId: string;
  fileName: string;
  score: number;
  category: string;
  partNumber?: string;
  fileSize?: string;
  modified?: string;
  onClick?: () => void;
}) {
  const pct = (score * 100).toFixed(1);
  const color = matchColor(score);
  const fmt = fileName.split(".").pop()?.toUpperCase() || "PNG";

  return (
    <div
      onClick={onClick}
      className="bg-surface-1 border border-outline/10 overflow-hidden cursor-pointer transition-all duration-300 hover:border-primary/30 hover:-translate-y-0.5 group"
    >
      {/* Image */}
      <div className="aspect-[16/10] bg-viewer-bg relative overflow-hidden">
        {drawingId ? (
          <img
            src={drawingThumbnailUrl(drawingId)}
            alt={fileName}
            className="w-full h-full object-cover opacity-60 grayscale-[30%] transition-all duration-500 group-hover:opacity-100 group-hover:grayscale-0 group-hover:scale-105"
            onError={(e) => {
              const el = e.target as HTMLImageElement;
              el.style.display = "none";
              const parent = el.parentElement;
              if (parent && !parent.querySelector(".placeholder-icon")) {
                const placeholder = document.createElement("div");
                placeholder.className = "placeholder-icon absolute inset-0 flex items-center justify-center text-text-tertiary text-xs font-mono";
                placeholder.textContent = "NO PREVIEW";
                parent.appendChild(placeholder);
              }
            }}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-text-tertiary text-xs font-mono">
            NO PREVIEW
          </div>
        )}
        {/* Scanning line */}
        <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-b from-transparent via-primary to-transparent animate-[scan_3s_linear_infinite] opacity-15" />

        {/* Match Badge */}
        <div className="absolute top-2 right-2">
          <div
            className="flex items-center gap-1 px-2 py-0.5 backdrop-blur-md text-xs font-bold"
            style={{ background: `${color}20`, color }}
          >
            {score >= 0.95 && <Star size={10} fill="currentColor" />}
            {pct}% MATCH
          </div>
        </div>

        {/* Part Number Badge */}
        {partNumber && (
          <div className="absolute bottom-2 left-2 px-2 py-0.5 bg-viewer-bg/60 backdrop-blur-md border-l-2 border-primary">
            <span className="text-[10px] font-mono text-primary uppercase">
              PART: {partNumber}
            </span>
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-4">
        <h4 className="text-[13px] font-bold text-text-primary font-heading truncate mb-1">
          {fileName}
          <sup className="text-[9px] text-text-tertiary ml-1">{fmt}</sup>
        </h4>

        <div className="text-[10px] text-text-tertiary mb-2">
          <span className="uppercase">Category: </span>
          <span className="text-text-secondary">
            {category?.replace(/_/g, " ") || "—"}
          </span>
        </div>

        {/* Meta Grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px]">
          {fileSize && (
            <>
              <span className="text-text-tertiary">Size</span>
              <span className="text-text-secondary font-mono">{fileSize}</span>
            </>
          )}
          {modified && (
            <>
              <span className="text-text-tertiary">Modified</span>
              <span className="text-text-secondary font-mono">{modified}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
