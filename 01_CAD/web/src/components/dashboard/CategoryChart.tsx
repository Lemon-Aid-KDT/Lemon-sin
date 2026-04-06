"use client";

import type { CategoryCount } from "@/lib/types";

export default function CategoryChart({
  categories,
}: {
  categories: CategoryCount[];
}) {
  if (!categories.length) return null;

  const maxCount = Math.max(...categories.map((c) => c.count));

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-heading font-bold text-text-primary uppercase tracking-[0.04em]">
            Category Distribution
          </h3>
          <p className="text-[11px] text-text-tertiary uppercase tracking-[0.1em] mt-0.5">
            Statistical Weighting of Part Types
          </p>
          <p className="text-[10px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>부품 유형별 통계 분포</p>
        </div>
        <div className="flex gap-1">
          <button className="text-[10px] font-bold uppercase px-3 py-1 bg-surface-3 text-text-primary rounded-sm">
            Bar
          </button>
          <button className="text-[10px] font-bold uppercase px-3 py-1 text-text-tertiary hover:bg-surface-2 rounded-sm transition-colors">
            Trend
          </button>
        </div>
      </div>

      {/* Bars */}
      <div className="space-y-4">
        {categories.map((cat) => {
          const pct = maxCount > 0 ? (cat.count / maxCount) * 100 : 0;
          return (
            <div key={cat.name}>
              <div className="flex items-baseline justify-between mb-1">
                <span className="text-xs font-bold text-text-primary uppercase tracking-[0.04em]">
                  {cat.name.replace(/_/g, " ")}
                </span>
                <span className="text-xs font-mono font-semibold text-primary">
                  {cat.count.toLocaleString()} UNITS
                </span>
              </div>
              <div className="h-[6px] bg-surface-3 overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-700 ease-out"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
