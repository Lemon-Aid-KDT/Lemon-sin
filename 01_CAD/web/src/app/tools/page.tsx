"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch, apiUpload } from "@/lib/api";
import type { BOMResponse, DimensionCompareResponse, DXFDiffResponse } from "@/lib/types";
import { FileText, Ruler, Layers3, GitBranch, MessageSquare } from "lucide-react";
import DrawingSelector from "@/components/tools/DrawingSelector";

type ToolTab = "bom" | "dimensions" | "dxf-diff" | "versions" | "feedback";

const TABS: { id: ToolTab; label: string; ko: string; icon: typeof FileText }[] = [
  { id: "bom", label: "BOM Extraction", ko: "BOM 추출", icon: FileText },
  { id: "dimensions", label: "Dimension Compare", ko: "치수 비교", icon: Ruler },
  { id: "dxf-diff", label: "DXF Diff", ko: "DXF 비교", icon: Layers3 },
  { id: "versions", label: "Version History", ko: "버전 이력", icon: GitBranch },
  { id: "feedback", label: "Feedback Stats", ko: "피드백 통계", icon: MessageSquare },
];

export default function ToolsPage() {
  const [activeTab, setActiveTab] = useState<ToolTab>("bom");

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-heading font-bold uppercase tracking-tight">Tools</h1>
        <p className="text-xs text-text-tertiary uppercase tracking-[0.1em] mt-0.5">BOM extraction, dimension comparison, DXF diff, version history</p>
        <p className="text-[11px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>BOM 추출, 치수 비교, DXF 비교, 버전 이력 관리</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-outline/15 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-5 py-3 text-[11px] font-heading font-semibold uppercase tracking-[0.06em] transition-colors border-b-2 ${
              activeTab === tab.id
                ? "text-primary border-primary"
                : "text-text-tertiary border-transparent hover:text-text-secondary"
            }`}
          >
            <tab.icon size={14} />
            <div className="text-left">
              <div>{tab.label}</div>
              <div className="text-[9px] font-normal normal-case tracking-normal opacity-60" style={{ fontFamily: "var(--font-ko)" }}>{tab.ko}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === "bom" && <BOMTab />}
        {activeTab === "dimensions" && <DimensionTab />}
        {activeTab === "dxf-diff" && <DXFDiffTab />}
        {activeTab === "versions" && <VersionTab />}
        {activeTab === "feedback" && <FeedbackTab />}
      </div>
    </div>
  );
}

// ── BOM Tab ──
function BOMTab() {
  const [drawingId, setDrawingId] = useState("");
  const bomMutation = useMutation({
    mutationFn: (id: string) => apiFetch<BOMResponse>(`/drawings/${id}/bom`),
  });

  return (
    <div className="max-w-2xl">
      <div className="space-y-3 mb-4">
        <DrawingSelector value={drawingId} onChange={setDrawingId} label="Drawing ID for BOM" />
        <button onClick={() => drawingId && bomMutation.mutate(drawingId)}
          className="px-5 py-2 bg-primary text-background text-xs font-bold uppercase hover:bg-primary-dark transition-colors">
          Extract BOM
        </button>
      </div>
      {bomMutation.data && (
        <div className="bg-surface-1 border border-outline/10 overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-3">
              <tr>{["Item", "Part Name", "Qty", "Material", "Spec"].map((h) => (
                <th key={h} className="px-4 py-2 text-[10px] uppercase tracking-wider font-bold text-text-secondary">{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {bomMutation.data.entries.map((e, i) => (
                <tr key={i} className="border-b border-background">
                  <td className="px-4 py-2 text-text-secondary">{e.item_no}</td>
                  <td className="px-4 py-2 text-text-primary font-semibold">{e.part_name}</td>
                  <td className="px-4 py-2 text-text-secondary">{e.quantity}</td>
                  <td className="px-4 py-2 text-text-secondary">{e.material}</td>
                  <td className="px-4 py-2 text-text-tertiary">{e.specification}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Dimension Compare Tab ──
function DimensionTab() {
  const [id1, setId1] = useState("");
  const [id2, setId2] = useState("");
  const compareMutation = useMutation({
    mutationFn: () => apiFetch<DimensionCompareResponse>("/drawings/compare/dimensions", {
      method: "POST", body: JSON.stringify({ drawing_id_1: id1, drawing_id_2: id2 }),
    }),
  });

  return (
    <div className="max-w-2xl">
      <div className="space-y-3 mb-4">
        <div>
          <p className="text-[10px] text-text-tertiary uppercase tracking-wider mb-1.5">Drawing A (Left)</p>
          <DrawingSelector value={id1} onChange={setId1} label="Drawing ID (Left)" />
        </div>
        <div>
          <p className="text-[10px] text-text-tertiary uppercase tracking-wider mb-1.5">Drawing B (Right)</p>
          <DrawingSelector value={id2} onChange={setId2} label="Drawing ID (Right)" />
        </div>
      </div>
      <button onClick={() => id1 && id2 && compareMutation.mutate()}
        className="px-5 py-2 bg-primary text-background text-xs font-bold uppercase hover:bg-primary-dark transition-colors">
        Compare Dimensions
      </button>
      {compareMutation.data && (
        <div className="mt-4 bg-surface-1 border border-outline/10 p-4">
          <div className="text-lg font-heading font-bold text-primary mb-2">
            {(compareMutation.data.similarity * 100).toFixed(1)}% Similarity
          </div>
          <div className="text-xs text-text-secondary">
            Matched: {compareMutation.data.matched.length} | Changed: {compareMutation.data.changed.length} | Only A: {compareMutation.data.only_in_a.length} | Only B: {compareMutation.data.only_in_b.length}
          </div>
        </div>
      )}
    </div>
  );
}

// ── DXF Diff Tab ──
function DXFDiffTab() {
  const diffMutation = useMutation({
    mutationFn: async (files: { a: File; b: File }) => {
      const fd = new FormData();
      fd.append("file_a", files.a);
      fd.append("file_b", files.b);
      return apiUpload<DXFDiffResponse>("/drawings/diff/dxf", fd);
    },
  });
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);

  return (
    <div className="max-w-2xl">
      <div className="grid grid-cols-2 gap-4 mb-4">
        <label className="flex flex-col items-center justify-center h-24 border border-dashed border-outline/30 bg-surface-1 cursor-pointer hover:border-primary/40">
          <span className="text-[10px] text-text-tertiary uppercase">{fileA ? fileA.name : "DXF File A"}</span>
          <input type="file" className="hidden" accept=".dxf" onChange={(e) => setFileA(e.target.files?.[0] || null)} />
        </label>
        <label className="flex flex-col items-center justify-center h-24 border border-dashed border-outline/30 bg-surface-1 cursor-pointer hover:border-primary/40">
          <span className="text-[10px] text-text-tertiary uppercase">{fileB ? fileB.name : "DXF File B"}</span>
          <input type="file" className="hidden" accept=".dxf" onChange={(e) => setFileB(e.target.files?.[0] || null)} />
        </label>
      </div>
      <button onClick={() => fileA && fileB && diffMutation.mutate({ a: fileA, b: fileB })}
        className="px-5 py-2 bg-primary text-background text-xs font-bold uppercase hover:bg-primary-dark transition-colors disabled:opacity-50" disabled={!fileA || !fileB}>
        Compare DXF
      </button>
      {diffMutation.data && (() => {
        const d = diffMutation.data;
        const total = d.matched_count + d.only_in_a_count + d.only_in_b_count;
        const matchPct = total > 0 ? ((d.matched_count / total) * 100).toFixed(1) : "0.0";
        const layerEntries = Object.entries(d.layer_diff || {});
        const summaryEntries = Object.entries(d.summary || {});
        return (
          <div className="mt-4 space-y-4">
            {/* Match Rate */}
            <div className="bg-surface-1 border border-outline/10 p-4">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-2xl font-heading font-bold text-primary">{matchPct}%</span>
                <span className="text-xs text-text-tertiary uppercase">Overall Match Rate <span style={{ fontFamily: "var(--font-ko)" }}>전체 일치율</span></span>
              </div>
              <div className="h-2 bg-surface-3 rounded-full overflow-hidden mb-4">
                <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${matchPct}%` }} />
              </div>

              {/* 3 Stat Cards */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-surface-2 border border-success/20 p-3 text-center">
                  <div className="text-lg font-heading font-bold text-success">{d.matched_count}</div>
                  <div className="text-[10px] text-text-tertiary uppercase">Matched</div>
                  <div className="text-[9px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>공통 엔티티</div>
                </div>
                <div className="bg-surface-2 border border-secondary/20 p-3 text-center">
                  <div className="text-lg font-heading font-bold text-secondary">{d.only_in_a_count}</div>
                  <div className="text-[10px] text-text-tertiary uppercase">Only in A</div>
                  <div className="text-[9px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>A에만 존재</div>
                </div>
                <div className="bg-surface-2 border border-error/20 p-3 text-center">
                  <div className="text-lg font-heading font-bold text-error">{d.only_in_b_count}</div>
                  <div className="text-[10px] text-text-tertiary uppercase">Only in B</div>
                  <div className="text-[9px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>B에만 존재</div>
                </div>
              </div>
            </div>

            {/* Interpretation Guide */}
            <div className="bg-surface-2/50 border border-outline/10 p-3 text-[10px] text-text-tertiary leading-relaxed">
              <span className="text-text-secondary font-bold uppercase">Interpretation Guide</span>
              <span className="ml-1" style={{ fontFamily: "var(--font-ko)" }}>결과 해석 가이드</span>
              <ul className="mt-1.5 space-y-0.5 list-disc list-inside">
                <li><span className="text-success">Matched</span>: Entities present in both files with identical geometry <span style={{ fontFamily: "var(--font-ko)" }}>(두 파일에 동일하게 존재하는 엔티티)</span></li>
                <li><span className="text-secondary">Only in A</span>: Entities found only in the first file — possibly removed <span style={{ fontFamily: "var(--font-ko)" }}>(첫 번째 파일에만 존재 — 삭제된 요소일 수 있음)</span></li>
                <li><span className="text-error">Only in B</span>: Entities found only in the second file — possibly added <span style={{ fontFamily: "var(--font-ko)" }}>(두 번째 파일에만 존재 — 추가된 요소일 수 있음)</span></li>
              </ul>
            </div>

            {/* Layer Diff */}
            {layerEntries.length > 0 && (
              <div className="bg-surface-1 border border-outline/10 p-4">
                <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
                  Layer Differences <span className="font-normal normal-case tracking-normal text-text-tertiary opacity-80" style={{ fontFamily: "var(--font-ko)" }}>레이어 차이</span>
                </h4>
                <div className="space-y-1.5">
                  {layerEntries.map(([layer, changes]) => (
                    <div key={layer} className="flex items-start gap-3 text-xs">
                      <span className="font-mono text-primary min-w-[120px]">{layer}</span>
                      <span className="text-text-tertiary">{Array.isArray(changes) ? changes.join(", ") : String(changes)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Summary Details */}
            {summaryEntries.length > 0 && (
              <div className="bg-surface-1 border border-outline/10 p-4">
                <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
                  Detail Summary <span className="font-normal normal-case tracking-normal text-text-tertiary opacity-80" style={{ fontFamily: "var(--font-ko)" }}>상세 요약</span>
                </h4>
                <div className="space-y-1">
                  {summaryEntries.map(([key, value]) => (
                    <div key={key} className="flex justify-between text-xs">
                      <span className="text-text-tertiary">{key.replace(/_/g, " ")}</span>
                      <span className="font-mono text-text-secondary">{typeof value === "object" ? JSON.stringify(value) : String(value)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}

// ── Version History Tab ──
function VersionTab() {
  const { data } = useQuery({
    queryKey: ["versions"],
    queryFn: () => apiFetch<{ versions: Record<string, number>; total_parts: number }>("/tools/versions"),
  });

  return (
    <div className="max-w-2xl">
      {data && (
        <>
          <p className="text-sm text-text-secondary mb-4">Total Parts with Versions: <span className="text-text-primary font-bold">{data.total_parts}</span></p>
          <div className="bg-surface-1 border border-outline/10 overflow-hidden max-h-96 overflow-y-auto">
            {Object.entries(data.versions).slice(0, 50).map(([pn, count]) => (
              <div key={pn} className="flex justify-between px-4 py-2 border-b border-background text-xs hover:bg-surface-2 transition-colors">
                <span className="font-mono text-primary">{pn}</span>
                <span className="text-text-tertiary">{count} revisions</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Feedback Stats Tab ──
function FeedbackTab() {
  const { data } = useQuery({
    queryKey: ["feedback-stats"],
    queryFn: () => apiFetch<Record<string, unknown>>("/feedback/stats"),
    retry: false,
  });

  return (
    <div className="max-w-2xl">
      {data ? (
        <pre className="bg-surface-2 border border-outline/10 p-4 text-xs text-text-secondary font-mono overflow-auto max-h-96">
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : (
        <p className="text-sm text-text-tertiary">피드백 데이터가 없습니다.</p>
      )}
    </div>
  );
}
