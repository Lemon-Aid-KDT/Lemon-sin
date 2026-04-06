"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Settings, User } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { StatsResponse } from "@/lib/types";
import { isOllamaConnected } from "@/lib/types";
import SettingsPanel from "@/components/settings/SettingsPanel";
import UserPanel from "@/components/settings/UserPanel";

export default function TopNav() {
  const [showSettings, setShowSettings] = useState(false);
  const [showUser, setShowUser] = useState(false);

  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<StatsResponse>("/stats"),
    refetchInterval: 10_000,
    retry: false,
  });

  const isConnected = isOllamaConnected(stats);
  const modelName = stats?.ollama_model || (isConnected ? "Connected" : "N/A");

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 h-16 bg-background border-b border-outline/15 flex items-center justify-between px-6">
        {/* Left: Brand */}
        <div className="flex items-center gap-5">
          <span className="font-heading text-[15px] font-bold text-text-primary uppercase tracking-[0.06em]">
            CAD Vision v5.6
          </span>
        </div>

        {/* Center: Global Search */}
        <div className="flex-1 max-w-[500px] mx-6">
          <div className="flex items-center gap-2 bg-surface-2 border border-outline/15 px-4 py-[7px] rounded-sm">
            <Search size={14} className="text-text-tertiary" />
            <span className="text-xs text-text-tertiary font-body">
              Global schematic search...
            </span>
          </div>
        </div>

        {/* Right: Status */}
        <div className="flex items-center gap-4">
          <span className="text-[10px] text-text-tertiary font-mono uppercase tracking-wider">
            Terminal Status
          </span>

          <div
            className={`flex items-center gap-2 text-[11px] font-mono px-3 py-[3px] border ${
              isConnected
                ? "bg-primary/8 border-primary/25 text-primary"
                : "bg-surface-2 border-outline/15 text-text-tertiary"
            }`}
          >
            <div
              className={`w-[5px] h-[5px] rounded-full ${
                isConnected
                  ? "bg-primary shadow-[0_0_4px_rgba(94,180,255,0.6)]"
                  : "bg-text-tertiary"
              }`}
            />
            <span>Ollama: {modelName}</span>
          </div>

          <div
            className={`flex items-center gap-[6px] px-3 py-1 rounded-sm border ${
              isConnected
                ? "bg-primary/10 border-primary/25"
                : "bg-error/10 border-error/25"
            }`}
          >
            <div
              className={`w-[7px] h-[7px] rounded-full ${
                isConnected
                  ? "bg-primary shadow-[0_0_6px_rgba(94,180,255,0.5)]"
                  : "bg-error shadow-[0_0_6px_rgba(255,113,108,0.5)]"
              }`}
            />
            <span
              className={`text-[10px] font-semibold font-mono ${
                isConnected ? "text-primary" : "text-error"
              }`}
            >
              {isConnected ? "Connected" : "Disconnected"}
            </span>
          </div>

          {/* Settings Button */}
          <button
            onClick={() => { setShowSettings(true); setShowUser(false); }}
            className="p-1.5 text-text-tertiary hover:text-text-secondary transition-colors"
          >
            <Settings size={16} />
          </button>

          {/* User Button */}
          <div className="relative">
            <button
              onClick={() => { setShowUser(!showUser); setShowSettings(false); }}
              className="p-1.5 text-text-tertiary hover:text-text-secondary transition-colors"
            >
              <User size={16} />
            </button>
            {showUser && <UserPanel onClose={() => setShowUser(false)} />}
          </div>
        </div>
      </header>

      {/* Settings Panel (slide-over) */}
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </>
  );
}
