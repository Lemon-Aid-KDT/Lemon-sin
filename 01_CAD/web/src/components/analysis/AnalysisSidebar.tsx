"use client";

import { Database, ScanSearch } from "lucide-react";

interface AnalysisSidebarProps {
  metadata: Record<string, string>;
  yoloCategory: string;
  yoloConfidence: number;
  onClassify: () => void;
}

function confColor(c: number): string {
  if (c >= 0.9) return "var(--color-primary)";
  if (c >= 0.8) return "var(--color-secondary)";
  return "var(--color-error)";
}

export default function AnalysisSidebar({
  metadata,
  yoloCategory,
  yoloConfidence,
  onClassify,
}: AnalysisSidebarProps) {
  return (
    <div className="bg-surface-1 border-l border-outline/15 flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="p-5 border-b border-outline/10">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-heading font-bold text-text-primary italic">
            Analysis Overview
          </h3>
          <span className="text-[9px] px-2 py-0.5 bg-secondary/15 text-secondary font-bold font-mono uppercase">
            Live AI Feed
          </span>
        </div>
        <p className="text-[10px] text-text-tertiary mt-1 leading-relaxed">
          Metadata extraction and YOLO classification.
        </p>
        <p className="text-[10px] text-text-tertiary mt-0.5 leading-relaxed" style={{ fontFamily: "var(--font-ko)" }}>
          메타데이터 추출 및 YOLO 분류
        </p>
      </div>

      {/* Scrollable Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {/* Section 1: Extracted Metadata */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Database size={14} className="text-primary" />
            <div>
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em]">
                Extracted Metadata
              </span>
              <span className="text-[9px] text-text-tertiary ml-2" style={{ fontFamily: "var(--font-ko)" }}>추출된 메타데이터</span>
            </div>
          </div>
          <div className="bg-surface-2 border border-outline/10 rounded-sm overflow-hidden">
            {Object.entries(metadata).length > 0 ? (
              Object.entries(metadata).map(([key, val]) => (
                <div
                  key={key}
                  className="flex justify-between px-4 py-2.5 border-b border-outline/10 last:border-b-0 hover:bg-surface-3/50 transition-colors"
                >
                  <span className="text-[10px] text-text-tertiary uppercase">
                    {key}
                  </span>
                  <span className="text-xs text-text-primary font-semibold">
                    {val}
                  </span>
                </div>
              ))
            ) : (
              <div className="px-4 py-6 text-center text-[10px] text-text-tertiary">
                Upload a drawing to extract metadata
                <p className="mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>도면 업로드 시 메타데이터 자동 추출</p>
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Class Prediction */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <ScanSearch size={14} className="text-primary" />
            <div>
              <span className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em]">
                Class Prediction
              </span>
              <span className="text-[9px] text-text-tertiary ml-2" style={{ fontFamily: "var(--font-ko)" }}>YOLO 분류 예측</span>
            </div>
          </div>
          {yoloCategory ? (
            <div
              className="p-4 border rounded-sm"
              style={{
                background: `color-mix(in srgb, ${confColor(yoloConfidence)} 5%, transparent)`,
                borderColor: `color-mix(in srgb, ${confColor(yoloConfidence)} 20%, transparent)`,
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-heading font-bold text-text-primary">
                  {yoloCategory.replace(/_/g, " ")}
                </span>
              </div>
              <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${yoloConfidence * 100}%`,
                    background: confColor(yoloConfidence),
                  }}
                />
              </div>
              <span
                className="text-[10px] font-mono font-semibold mt-1 inline-block"
                style={{ color: confColor(yoloConfidence) }}
              >
                {(yoloConfidence * 100).toFixed(1)}%
              </span>
            </div>
          ) : (
            <button
              onClick={onClassify}
              className="w-full py-2.5 border border-outline/20 text-xs font-bold uppercase tracking-wider text-text-secondary hover:text-primary hover:border-primary/30 transition-colors"
            >
              Run Classification
              <span className="block text-[9px] font-normal normal-case tracking-normal opacity-60 mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>자동 분류 실행</span>
            </button>
          )}
        </div>

        {/* Tip: Description moved to Q&A */}
        <div className="bg-surface-2/50 border border-outline/10 p-3 rounded-sm">
          <p className="text-[10px] text-text-tertiary leading-relaxed">
            AI drawing description is now available in the Technical Assistant panel below.
          </p>
          <p className="text-[10px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>
            AI 도면 설명은 하단의 Technical Assistant 패널에서 생성할 수 있습니다.
          </p>
        </div>
      </div>
    </div>
  );
}
