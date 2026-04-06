"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { StatsResponse, CategoryCount } from "@/lib/types";
import { isOllamaConnected } from "@/lib/types";
import KPICards from "@/components/dashboard/KPICards";
import CategoryChart from "@/components/dashboard/CategoryChart";
import OllamaStatus from "@/components/dashboard/OllamaStatus";
import DrawingExplorer from "@/components/dashboard/DrawingExplorer";

export default function DashboardPage() {
  // Stats
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<StatsResponse>("/stats"),
    refetchInterval: 10_000,
  });

  // Category counts — 실제 API 데이터 사용
  const categories: CategoryCount[] = stats?.category_counts
    ? Object.entries(stats.category_counts)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 8)
        .map(([name, count]) => ({ name, count }))
    : [];

  const now = new Date();
  const timeStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")} | ${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}:${String(now.getSeconds()).padStart(2, "0")}`;

  return (
    <div>
      {/* Header + Server Time */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-heading font-bold text-text-primary uppercase tracking-tight">
            Dashboard
          </h1>
          <p className="text-xs text-text-tertiary uppercase tracking-[0.1em] mt-0.5">
            System Overview &amp; Metric Analysis
          </p>
          <p className="text-[11px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>
            등록된 도면 현황과 시스템 상태를 한눈에 확인합니다.
          </p>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-text-tertiary uppercase tracking-[0.08em]">
            Local Server Time
          </p>
          <p className="text-lg font-heading font-bold text-text-primary tracking-tight">
            {timeStr}
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <KPICards
        totalDrawings={stats?.total_drawings ?? 0}
        totalCategories={stats?.categories?.length ?? 0}
        vectorChannels={3}
        searchLatency={0.104}
      />

      {/* Category Chart (6) + Ollama Status (4) */}
      <div className="grid grid-cols-10 gap-4 mt-6">
        <div className="col-span-6">
          <CategoryChart categories={categories} />
        </div>
        <div className="col-span-4">
          <OllamaStatus
            connected={isOllamaConnected(stats)}
            model={stats?.ollama_model || (isOllamaConnected(stats) ? "Qwen3.5 9b" : "N/A")}
            ramUsedGb={12.2}
            ramTotalGb={24}
          />
        </div>
      </div>

      {/* Drawing Explorer (전체 도면 탐색기) */}
      <div className="mt-6">
        <DrawingExplorer />
      </div>
    </div>
  );
}
