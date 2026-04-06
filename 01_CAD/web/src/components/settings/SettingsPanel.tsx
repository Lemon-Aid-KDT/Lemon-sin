"use client";

import { useState, useEffect, useCallback } from "react";
import { useTheme } from "next-themes";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Sun, Moon, Check, Loader2, AlertCircle, Languages } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { StatsResponse } from "@/lib/types";

interface ModelInfo {
  name: string;
  size: string;
  modified: string;
}

/** Filter models suitable for CAD analysis (VLM models only) */
const CAD_MODEL_PREFIXES = ["gemma4", "qwen3.5", "qwen3", "llava", "bakllava"];
function isCadModel(name: string): boolean {
  const lower = name.toLowerCase();
  return CAD_MODEL_PREFIXES.some((p) => lower.startsWith(p));
}

export default function SettingsPanel({ onClose }: { onClose: () => void }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [selectedModel, setSelectedModel] = useState("");
  const [appliedModel, setAppliedModel] = useState("");
  const [errorDetail, setErrorDetail] = useState("");
  const [language, setLanguage] = useState<"en" | "ko" | "both">("both");
  const queryClient = useQueryClient();

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem("cad_language_pref");
    if (saved === "en" || saved === "ko" || saved === "both") setLanguage(saved);
  }, []);

  const handleLanguageChange = useCallback((lang: "en" | "ko" | "both") => {
    setLanguage(lang);
    localStorage.setItem("cad_language_pref", lang);
  }, []);

  // Current stats
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<StatsResponse>("/stats"),
  });

  // Available models from Ollama
  const { data: modelsData } = useQuery({
    queryKey: ["models"],
    queryFn: () => apiFetch<{ models: ModelInfo[] }>("/models"),
    retry: false,
  });

  // All models + filtered CAD models
  const allModels = modelsData?.models ?? [];
  const cadModels = allModels.filter((m) => isCadModel(m.name));
  const displayModels = cadModels.length > 0 ? cadModels : allModels;

  // Determine active model from stats or TopNav display
  const statsModel = stats?.ollama_model;
  const activeModel = appliedModel || statsModel || "";

  // Initialize selectedModel from active model or first available
  useEffect(() => {
    if (!selectedModel && displayModels.length > 0) {
      if (activeModel && displayModels.some((m) => m.name === activeModel)) {
        setSelectedModel(activeModel);
      } else {
        setSelectedModel(displayModels[0].name);
      }
    }
  }, [activeModel, displayModels, selectedModel]);

  // Model change mutation
  const modelMutation = useMutation({
    mutationFn: async (model: string) => {
      setErrorDetail("");
      return apiFetch<{ status: string; model: string }>("/settings/model", {
        method: "PUT",
        body: JSON.stringify({ model }),
      });
    },
    onSuccess: (data) => {
      setAppliedModel(data.model || selectedModel);
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
    onError: (err) => {
      setErrorDetail(err instanceof Error ? err.message : "Unknown error");
    },
  });

  const isModelChanged = selectedModel !== activeModel && selectedModel !== "";

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-background/40 backdrop-blur-sm z-50" onClick={onClose} />

      {/* Panel */}
      <div className="fixed top-0 right-0 h-full w-80 bg-surface-1 border-l border-outline/15 z-50 flex flex-col overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-outline/10">
          <div>
            <h2 className="text-sm font-heading font-bold text-text-primary uppercase tracking-[0.06em]">
              Settings
            </h2>
            <p className="text-[10px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>설정</p>
          </div>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-primary transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-6">
          {/* Theme Toggle */}
          <div>
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
              Appearance <span className="text-[9px] font-normal normal-case tracking-normal text-text-tertiary opacity-80" style={{ fontFamily: "var(--font-ko)" }}>테마</span>
            </h4>
            {mounted && (
              <div className="flex gap-2">
                <button
                  onClick={() => setTheme("dark")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 border text-[11px] font-bold uppercase transition-colors ${
                    theme === "dark"
                      ? "border-primary/30 bg-primary/10 text-primary"
                      : "border-outline/15 text-text-tertiary hover:text-text-secondary"
                  }`}
                >
                  <Moon size={14} />
                  Dark
                </button>
                <button
                  onClick={() => setTheme("light")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 border text-[11px] font-bold uppercase transition-colors ${
                    theme === "light"
                      ? "border-primary/30 bg-primary/10 text-primary"
                      : "border-outline/15 text-text-tertiary hover:text-text-secondary"
                  }`}
                >
                  <Sun size={14} />
                  Light
                </button>
              </div>
            )}
          </div>

          {/* LLM Model Selection */}
          <div>
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
              LLM Model <span className="text-[9px] font-normal normal-case tracking-normal text-text-tertiary opacity-80" style={{ fontFamily: "var(--font-ko)" }}>LLM 모델</span>
            </h4>

            {/* Current model indicator */}
            <div className="flex items-center gap-2 mb-3 px-3 py-2 bg-surface-2 border border-outline/10">
              <div className={`w-2 h-2 rounded-full ${activeModel ? "bg-success shadow-[0_0_4px_rgba(74,222,128,0.5)]" : "bg-text-tertiary"}`} />
              <span className="text-[11px] text-text-secondary font-mono">{activeModel || "Auto-selected"}</span>
              <span className="text-[9px] text-text-tertiary ml-auto">Active</span>
            </div>

            {/* Model dropdown — CAD-suitable models only */}
            {displayModels.length > 0 ? (
              <div className="space-y-2">
                <select
                  value={selectedModel}
                  onChange={(e) => { setSelectedModel(e.target.value); modelMutation.reset(); }}
                  className="w-full bg-surface-2 border border-outline/15 px-3 py-2 text-xs text-text-secondary outline-none rounded-sm focus:border-primary/40"
                >
                  {displayModels.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.name} {m.size ? `(${m.size})` : ""}
                    </option>
                  ))}
                </select>

                {cadModels.length > 0 && cadModels.length < allModels.length && (
                  <p className="text-[9px] text-text-tertiary">
                    {cadModels.length}/{allModels.length} VLM models shown
                    <span className="ml-1" style={{ fontFamily: "var(--font-ko)" }}>
                      (CAD 분석 가능 모델만 표시)
                    </span>
                  </p>
                )}

                {isModelChanged && (
                  <button
                    onClick={() => modelMutation.mutate(selectedModel)}
                    disabled={modelMutation.isPending}
                    className="w-full flex items-center justify-center gap-2 py-2 bg-primary text-background text-[11px] font-bold uppercase hover:bg-primary-dark transition-colors disabled:opacity-50"
                  >
                    {modelMutation.isPending ? (
                      <><Loader2 size={12} className="animate-spin" /> Applying...</>
                    ) : (
                      <><Check size={12} /> Apply Model Change</>
                    )}
                  </button>
                )}
                {modelMutation.isSuccess && (
                  <p className="text-[10px] text-success">Model changed to {appliedModel}</p>
                )}
                {modelMutation.isError && (
                  <div className="text-[10px] text-error flex items-start gap-1.5">
                    <AlertCircle size={12} className="flex-shrink-0 mt-0.5" />
                    <div>
                      <p>Failed to change model</p>
                      {errorDetail && <p className="text-[9px] text-text-tertiary mt-0.5 font-mono break-all">{errorDetail}</p>}
                      <p className="text-[9px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>
                        백엔드 API가 실행 중인지 확인하세요
                      </p>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-[10px] text-text-tertiary">
                <p className="font-mono">Auto-selected based on RAM + installed models</p>
                <p className="mt-1" style={{ fontFamily: "var(--font-ko)" }}>Ollama 모델 목록을 불러올 수 없습니다</p>
              </div>
            )}
          </div>

          {/* AI Response Language */}
          <div>
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
              <Languages size={12} className="inline mr-1.5 -mt-0.5" />
              AI Language <span className="text-[9px] font-normal normal-case tracking-normal text-text-tertiary opacity-80" style={{ fontFamily: "var(--font-ko)" }}>AI 응답 언어</span>
            </h4>
            <div className="flex gap-1.5">
              {([
                { value: "en" as const, label: "English", ko: "영어" },
                { value: "ko" as const, label: "한국어", ko: "한국어" },
                { value: "both" as const, label: "Both", ko: "둘 다" },
              ]).map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => handleLanguageChange(opt.value)}
                  className={`flex-1 py-2 border text-[11px] font-bold uppercase transition-colors ${
                    language === opt.value
                      ? "border-primary/30 bg-primary/10 text-primary"
                      : "border-outline/15 text-text-tertiary hover:text-text-secondary"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-text-tertiary mt-1.5" style={{ fontFamily: "var(--font-ko)" }}>
              AI 분석 결과의 출력 언어를 선택합니다.
            </p>
          </div>

          {/* Search Weights Info */}
          <div>
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
              Search Weights <span className="text-[9px] font-normal normal-case tracking-normal text-text-tertiary opacity-80" style={{ fontFamily: "var(--font-ko)" }}>검색 가중치</span>
            </h4>
            <div className="space-y-2">
              {[
                { label: "Image (CLIP)", value: "10%", color: "var(--color-primary)" },
                { label: "Text (E5)", value: "60%", color: "var(--color-secondary)" },
                { label: "GNN (Structure)", value: "30%", color: "var(--color-tertiary)" },
              ].map((w) => (
                <div key={w.label} className="flex items-center gap-3">
                  <span className="text-[10px] text-text-tertiary w-28">{w.label}</span>
                  <div className="flex-1 h-1.5 bg-surface-3 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: w.value, background: w.color }} />
                  </div>
                  <span className="text-[10px] font-mono text-text-secondary w-8 text-right">{w.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* YOLO Thresholds Info */}
          <div>
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-3">
              YOLO Thresholds <span className="text-[9px] font-normal normal-case tracking-normal text-text-tertiary opacity-80" style={{ fontFamily: "var(--font-ko)" }}>YOLO 임계값</span>
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-text-tertiary">Classification</span>
                <span className="font-mono text-text-secondary">0.50</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-tertiary">Detection</span>
                <span className="font-mono text-text-secondary">0.30</span>
              </div>
            </div>
          </div>

          {/* Version Info */}
          <div className="pt-4 border-t border-outline/10">
            <div className="space-y-1 text-[10px] font-mono text-text-tertiary">
              <div>CAD Vision v5.6</div>
              <div>Next.js 16 + React 19</div>
              <div>FastAPI + ChromaDB 3-channel</div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
