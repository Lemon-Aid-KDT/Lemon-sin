"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Keyboard } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { StatsResponse, PaginatedResponse } from "@/lib/types";

export default function DrawingSelector({
  value,
  onChange,
  label,
}: {
  value: string;
  onChange: (drawingId: string) => void;
  label?: string;
}) {
  const [manualMode, setManualMode] = useState(false);
  const [category, setCategory] = useState("");

  // Categories from stats (globally cached)
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<StatsResponse>("/stats"),
  });

  // Drawings for selected category
  const { data: drawings, isLoading: drawingsLoading } = useQuery({
    queryKey: ["drawings-by-category", category],
    queryFn: () =>
      apiFetch<PaginatedResponse>(
        `/drawings?category=${encodeURIComponent(category)}&page_size=100`
      ),
    enabled: !!category && !manualMode,
  });

  if (manualMode) {
    return (
      <div className="flex gap-2">
        <input
          className="flex-1 bg-surface-2 border border-outline/15 px-4 py-2 text-sm text-text-primary placeholder:text-text-tertiary outline-none rounded-sm focus:border-primary/40"
          placeholder={label || "Drawing ID"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          onClick={() => setManualMode(false)}
          className="px-3 py-2 border border-outline/15 text-[10px] text-text-tertiary hover:text-text-secondary transition-colors"
          title="Switch to dropdown mode"
        >
          <ChevronDown size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        {/* Category dropdown */}
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            onChange("");
          }}
          className="flex-1 bg-surface-2 border border-outline/15 px-3 py-2 text-sm text-text-secondary outline-none rounded-sm focus:border-primary/40"
        >
          <option value="">
            카테고리 선택...
          </option>
          {(stats?.categories ?? []).map((cat) => (
            <option key={cat} value={cat}>
              {cat.replace(/_/g, " ")}
              {stats?.category_counts?.[cat]
                ? ` (${stats.category_counts[cat]})`
                : ""}
            </option>
          ))}
        </select>

        {/* Drawing dropdown */}
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={!category || drawingsLoading}
          className="flex-1 bg-surface-2 border border-outline/15 px-3 py-2 text-sm text-text-secondary outline-none rounded-sm focus:border-primary/40 disabled:opacity-40"
        >
          <option value="">
            {drawingsLoading
              ? "로딩 중..."
              : category
              ? "도면 선택..."
              : "카테고리를 먼저 선택하세요"}
          </option>
          {(drawings?.items ?? []).map((d) => (
            <option key={d.drawing_id} value={d.drawing_id}>
              {d.file_name} ({d.drawing_id.slice(0, 8)})
            </option>
          ))}
        </select>

        {/* Manual input toggle */}
        <button
          onClick={() => setManualMode(true)}
          className="px-3 py-2 border border-outline/15 text-[10px] text-text-tertiary hover:text-text-secondary transition-colors"
          title="Switch to manual ID input"
        >
          <Keyboard size={14} />
        </button>
      </div>

      {/* Selected drawing info */}
      {value && (
        <div className="text-[10px] text-primary font-mono px-1">
          Selected: {value.slice(0, 24)}...
        </div>
      )}
    </div>
  );
}
