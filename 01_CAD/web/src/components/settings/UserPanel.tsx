"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { StatsResponse } from "@/lib/types";
import { isOllamaConnected } from "@/lib/types";

export default function UserPanel({ onClose }: { onClose: () => void }) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [displayName, setDisplayName] = useState("Engineer");

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<StatsResponse>("/stats"),
  });

  // Load name from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("cad_user_name");
    if (saved) setDisplayName(saved);
  }, []);

  // Save name on change
  const handleNameChange = (name: string) => {
    setDisplayName(name);
    localStorage.setItem("cad_user_name", name);
  };

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  return (
    <div
      ref={panelRef}
      className="absolute top-14 right-0 w-64 bg-surface-1 border border-outline/20 shadow-2xl shadow-background/60 z-50"
    >
      {/* User Info */}
      <div className="px-4 py-3 border-b border-outline/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-primary/15 border border-primary/25 flex items-center justify-center text-primary font-bold text-sm">
            {displayName.charAt(0).toUpperCase()}
          </div>
          <div>
            <input
              value={displayName}
              onChange={(e) => handleNameChange(e.target.value)}
              className="bg-transparent text-xs font-bold text-text-primary outline-none w-full"
              placeholder="Display Name"
            />
            <p className="text-[10px] text-text-tertiary">CAD Vision User</p>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="px-4 py-3 space-y-2 text-[10px]">
        <div className="flex justify-between">
          <span className="text-text-tertiary">API Status</span>
          <span className={isOllamaConnected(stats) ? "text-success font-bold" : "text-error font-bold"}>
            {isOllamaConnected(stats) ? "Connected" : "Disconnected"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-tertiary">Drawings</span>
          <span className="text-text-secondary font-mono">{(stats?.total_drawings ?? 0).toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-tertiary">Model</span>
          <span className="text-text-secondary font-mono">{stats?.ollama_model || "N/A"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-tertiary">Categories</span>
          <span className="text-text-secondary font-mono">{stats?.categories?.length ?? 0}</span>
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-outline/10">
        <p className="text-[9px] text-text-tertiary font-mono">CAD Vision v5.6 — Local Session</p>
      </div>
    </div>
  );
}
