"use client";

import { useState } from "react";
import { drawingThumbnailUrl } from "@/lib/api";
import type { DrawingRecord } from "@/lib/types";

function confColor(conf: number): string {
  if (conf >= 0.9) return "var(--color-primary)";
  if (conf >= 0.8) return "var(--color-secondary)";
  return "var(--color-error)";
}

export default function ActivityTable({
  records,
}: {
  records: DrawingRecord[];
}) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  if (!records.length) {
    return (
      <p className="text-xs text-text-tertiary">최근 활동이 없습니다.</p>
    );
  }

  return (
    <div className="bg-surface-1 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-outline/10">
        <div>
          <h3 className="text-base font-heading font-bold text-text-primary uppercase tracking-[0.04em]">
            Recent Activity
          </h3>
          <p className="text-[9px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>
            최근 등록 도면 및 분류 결과
          </p>
        </div>
        <span className="text-[10px] text-primary font-mono uppercase cursor-pointer hover:underline">
          View All Logs
        </span>
      </div>

      {/* Table */}
      <table className="w-full text-left">
        <thead className="bg-surface-3">
          <tr>
            {["File Preview", "Drawing ID", "Format", "Category", "YOLO Confidence", "Timestamp"].map(
              (h) => (
                <th
                  key={h}
                  className="px-5 py-2.5 text-[10px] uppercase tracking-[0.1em] font-bold text-text-secondary"
                >
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {records.map((rec) => {
            const conf = rec.yolo_confidence;
            const color = confColor(conf);
            const fmt = rec.dxf_path ? "DXF" : "PNG";
            const ts = rec.registered_at
              ? rec.registered_at.split("T")[1]?.slice(0, 5) ?? ""
              : "";
            const isHovered = hoveredId === rec.drawing_id;

            return (
              <tr
                key={rec.drawing_id}
                className="border-b border-background hover:bg-surface-2/50 transition-colors"
                onMouseEnter={() => setHoveredId(rec.drawing_id)}
                onMouseLeave={() => setHoveredId(null)}
              >
                {/* Preview — 48px + hover popup */}
                <td className="px-5 py-2 relative">
                  <div className="w-12 h-12 bg-surface-3 border border-outline/15 overflow-hidden rounded-sm">
                    <img
                      src={drawingThumbnailUrl(rec.drawing_id)}
                      alt={rec.file_name}
                      className="w-full h-full object-contain opacity-80 hover:opacity-100 transition-opacity"
                      onError={(e) => {
                        const el = e.target as HTMLImageElement;
                        el.style.display = "none";
                      }}
                    />
                  </div>

                  {/* Hover preview popup */}
                  {isHovered && (
                    <div className="absolute left-16 top-0 z-50 w-80 bg-surface-1 border border-outline/20 shadow-2xl shadow-black/60 overflow-hidden pointer-events-none">
                      <div className="aspect-square bg-viewer-bg flex items-center justify-center">
                        <img
                          src={drawingThumbnailUrl(rec.drawing_id)}
                          alt={rec.file_name}
                          className="max-w-full max-h-full object-contain"
                        />
                      </div>
                      <div className="p-3.5 space-y-1.5">
                        <div className="text-xs font-bold text-text-primary font-heading truncate">
                          {rec.file_name}
                        </div>
                        <div className="flex gap-3 text-[11px]">
                          <span className="text-text-tertiary">
                            Category:{" "}
                            <span className="text-text-secondary">
                              {rec.category?.replace(/_/g, " ") || "—"}
                            </span>
                          </span>
                        </div>
                        {rec.part_numbers?.length > 0 && (
                          <div className="text-[11px] text-primary font-mono">
                            {rec.part_numbers.join(", ")}
                          </div>
                        )}
                        {rec.materials?.length > 0 && (
                          <div className="text-[11px] text-text-tertiary">
                            Material: {rec.materials.join(", ")}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </td>

                {/* ID + filename */}
                <td className="px-5 py-2">
                  <div className="text-xs font-mono text-text-primary">
                    #{rec.drawing_id.slice(0, 12)}
                  </div>
                  <div className="text-[10px] text-text-tertiary truncate max-w-[140px]">
                    {rec.file_name}
                  </div>
                </td>

                {/* Format */}
                <td className="px-5 py-2">
                  <span className="text-[10px] px-2 py-0.5 bg-surface-3 text-text-secondary">
                    {fmt}
                  </span>
                </td>

                {/* Category */}
                <td className="px-5 py-2 text-[11px] text-text-secondary">
                  {rec.category?.replace(/_/g, " ").slice(0, 25) || "—"}
                </td>

                {/* YOLO / Part Number */}
                <td className="px-5 py-2">
                  {conf > 0 ? (
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{
                          background: color,
                          boxShadow: `0 0 6px ${color}80`,
                        }}
                      />
                      <span
                        className="text-xs font-mono font-semibold"
                        style={{ color }}
                      >
                        {(conf * 100).toFixed(1)}%
                      </span>
                    </div>
                  ) : rec.part_numbers?.length ? (
                    <span className="text-[10px] font-mono text-primary">
                      {rec.part_numbers[0]}
                    </span>
                  ) : (
                    <span className="text-xs text-text-tertiary">—</span>
                  )}
                </td>

                {/* Timestamp */}
                <td className="px-5 py-2 text-[11px] text-text-tertiary font-mono">
                  {ts || rec.file_name?.slice(0, 15) || "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
