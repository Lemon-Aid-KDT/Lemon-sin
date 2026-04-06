"use client";

export default function OllamaStatus({
  connected,
  model,
  ramUsedGb,
  ramTotalGb,
}: {
  connected: boolean;
  model: string;
  ramUsedGb: number;
  ramTotalGb: number;
}) {
  const ramPct = ramTotalGb > 0 ? (ramUsedGb / ramTotalGb) * 100 : 0;

  return (
    <div className="bg-surface-3/70 backdrop-blur-xl border border-outline/15 p-6 relative overflow-hidden h-full">
      <h3 className="text-sm font-heading font-bold text-text-primary uppercase tracking-[0.06em] mb-1">
        System Status (Ollama)
      </h3>
      <p className="text-[10px] text-text-tertiary mb-4" style={{ fontFamily: "var(--font-ko)" }}>시스템 상태</p>

      {/* Status */}
      <div className="flex items-center gap-3 mb-6">
        <div
          className={`w-[10px] h-[10px] rounded-full ${
            connected
              ? "bg-primary shadow-[0_0_8px_rgba(94,180,255,0.6)]"
              : "bg-error shadow-[0_0_8px_rgba(255,113,108,0.6)]"
          }`}
        />
        <span
          className={`text-xs font-heading font-semibold uppercase ${
            connected ? "text-primary" : "text-error"
          }`}
        >
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>

      {/* Model */}
      <div className="mb-5">
        <span className="text-[10px] text-text-tertiary uppercase tracking-[0.08em] font-bold">
          Active Model
        </span>
        <div className="text-sm font-semibold text-text-primary font-mono mt-1">
          {model}{" "}
          <span className="text-text-tertiary text-[10px]">
            (Auto-selected)
          </span>
        </div>
      </div>

      {/* RAM */}
      <div>
        <div className="flex justify-between text-[10px] uppercase tracking-[0.1em] font-bold mb-1.5">
          <span className="text-text-secondary">RAM Usage</span>
          <span className="text-primary">
            {ramUsedGb.toFixed(1)}GB / {ramTotalGb.toFixed(0)}GB
          </span>
        </div>
        <div className="h-[10px] bg-viewer-bg border border-outline/20 p-[2px]">
          <div
            className="h-full bg-primary transition-all duration-500"
            style={{ width: `${Math.min(ramPct, 100)}%` }}
          />
        </div>
      </div>

      {/* Restart Button */}
      <button className="mt-5 w-full py-2 border border-outline/30 text-[10px] font-bold uppercase tracking-wider text-text-secondary hover:text-text-primary hover:border-outline/50 transition-colors">
        Restart Inference Engine
        <span className="block text-[9px] font-normal normal-case tracking-normal opacity-60 mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>추론 엔진 재시작</span>
      </button>
    </div>
  );
}
