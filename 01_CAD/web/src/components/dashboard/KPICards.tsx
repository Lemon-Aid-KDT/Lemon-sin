"use client";

interface KPIItem {
  label: string;
  ko?: string;
  value: string;
  sub?: string;
  color: string;
  pct: number;
  badges?: string[];
}

export default function KPICards({
  totalDrawings,
  totalCategories,
  vectorChannels,
  searchLatency,
}: {
  totalDrawings: number;
  totalCategories: number;
  vectorChannels: number;
  searchLatency: number;
}) {
  const items: KPIItem[] = [
    {
      label: "Registered Drawings",
      ko: "등록된 도면 수",
      value: totalDrawings.toLocaleString(),
      sub: totalDrawings > 0 ? "+12%" : "",
      color: "var(--color-primary)",
      pct: 75,
    },
    {
      label: "Total Categories",
      ko: "전체 카테고리",
      value: String(totalCategories),
      sub: "Mapped from 12 Industry Standards",
      color: "var(--color-secondary)",
      pct: 60,
    },
    {
      label: "Vector Channels",
      ko: "벡터 채널",
      value: String(vectorChannels),
      color: "var(--color-tertiary)",
      pct: 100,
      badges: ["IMAGE", "TEXT", "GNN"],
    },
    {
      label: "Search Latency",
      ko: "검색 응답 시간",
      value: `${searchLatency}s`,
      sub: "P99 Response Rate: 142ms",
      color: "var(--color-success)",
      pct: 40,
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-4">
      {items.map((item) => (
        <div
          key={item.label}
          className="bg-surface-1 p-6 border-l-2"
          style={{ borderLeftColor: item.color }}
        >
          <p className="text-xs text-text-secondary uppercase tracking-[0.1em] font-bold font-heading mb-0.5">
            {item.label}
          </p>
          {item.ko && (
            <p className="text-[11px] text-text-tertiary mb-2" style={{ fontFamily: "var(--font-ko)" }}>
              {item.ko}
            </p>
          )}
          <div className="flex items-baseline gap-2">
            <span className="text-[2rem] font-heading font-bold text-text-primary tracking-tight leading-none">
              {item.value}
            </span>
            {item.sub && !item.badges && (
              <span
                className="text-xs font-semibold"
                style={{ color: item.color }}
              >
                {item.sub}
              </span>
            )}
          </div>

          {item.sub && !item.badges && item.label !== "Registered Drawings" && (
            <p className="text-[10px] text-text-tertiary mt-2">{item.sub}</p>
          )}

          {item.badges && (
            <div className="flex gap-1.5 mt-3">
              {item.badges.map((b) => (
                <span
                  key={b}
                  className="text-[9px] font-mono font-semibold px-2 py-0.5 border rounded-sm"
                  style={{
                    color: item.color,
                    borderColor: `color-mix(in srgb, ${item.color} 30%, transparent)`,
                  }}
                >
                  {b}
                </span>
              ))}
            </div>
          )}

          <div className="mt-4 h-1 bg-surface-3 overflow-hidden">
            <div
              className="h-full transition-all duration-700"
              style={{
                width: `${item.pct}%`,
                background: item.color,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
