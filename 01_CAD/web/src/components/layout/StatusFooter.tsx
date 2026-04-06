"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { StatsResponse } from "@/lib/types";

export default function StatusFooter() {
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<StatsResponse>("/stats"),
    refetchInterval: 30_000,
    retry: false,
  });

  const gnnActive = stats?.gnn_enabled ?? false;
  const imageCount = stats?.image_collection_count ?? 0;

  return (
    <footer className="fixed bottom-0 left-0 right-0 z-50 h-8 bg-background border-t border-outline/15 flex items-center justify-center gap-8 px-6 font-mono text-[10px] text-text-tertiary">
      <span>
        <span className="text-success">●</span>{" "}
        SERVER LATENCY:{" "}
        <span className="text-text-primary font-semibold">0.104s</span>
      </span>
      <span>
        INDEX VERSION:{" "}
        <span className="text-text-secondary">2024Q1.DB_ALPHA</span>
      </span>
      <span>
        GIN ENCODER{" "}
        <span
          className={`font-semibold ${gnnActive ? "text-success" : "text-text-tertiary"}`}
        >
          {gnnActive ? "ACTIVE" : "INACTIVE"}
        </span>
      </span>
      <span>
        VECTOR SYNC:{" "}
        <span
          className={`font-semibold ${imageCount > 0 ? "text-success" : "text-secondary"}`}
        >
          {imageCount > 0 ? "OK" : "PENDING"}
        </span>
      </span>
    </footer>
  );
}
