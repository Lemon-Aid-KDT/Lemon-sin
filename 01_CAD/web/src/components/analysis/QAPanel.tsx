"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Paperclip, MessageSquare, BrainCircuit } from "lucide-react";
import { apiStreamSSE } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  type?: "narrative" | "qa";
}

function getLanguageSuffix(): string {
  if (typeof window === "undefined") return "Answer in both English and Korean.";
  const pref = localStorage.getItem("cad_language_pref") || "both";
  if (pref === "en") return "Answer in English only.";
  if (pref === "ko") return "한국어로만 답변하세요. 모든 내용을 한국어로 작성해주세요.";
  return "Answer in both English and Korean.";
}

function buildDescriptionPrompt(): string {
  return `You are an expert mechanical engineer. Describe this technical drawing in detail including Part Type, Key Features, Dimensions, Material, and Application. ${getLanguageSuffix()}`;
}

function buildQALanguageSuffix(): string {
  if (typeof window === "undefined") return "";
  const pref = localStorage.getItem("cad_language_pref") || "both";
  if (pref === "en") return " Answer in English only.";
  if (pref === "ko") return " 한국어로만 답변하세요.";
  return "";
}

export default function QAPanel({ file }: { file: File | null }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasDescription, setHasDescription] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Reset when file changes
  useEffect(() => {
    setMessages([]);
    setHasDescription(false);
  }, [file]);

  const streamQuestion = async (question: string, type: "narrative" | "qa") => {
    if (!file || isStreaming) return;
    setIsStreaming(true);

    // Add user message for Q&A, or system label for narrative
    if (type === "qa") {
      setMessages((prev) => [...prev, { role: "user", content: question, type }]);
    } else {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: "Generate Drawing Description 도면 설명 생성", type: "narrative" },
      ]);
    }

    let fullText = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "", type }]);

    const formData = new FormData();
    formData.append("file", file);

    await apiStreamSSE(
      "/drawings/analyze/stream",
      formData,
      { question, num_predict: "2048" },
      (token) => {
        fullText += token;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: fullText, type };
          return updated;
        });
      },
      () => {
        setIsStreaming(false);
        if (type === "narrative") setHasDescription(true);
      },
      (err) => {
        fullText += `\n[Error: ${err}]`;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: fullText, type };
          return updated;
        });
        setIsStreaming(false);
      }
    );
  };

  const handleSend = () => {
    if (!input.trim()) return;
    const question = input.trim() + buildQALanguageSuffix();
    setInput("");
    streamQuestion(question, "qa");
  };

  const handleGenerateDescription = () => {
    streamQuestion(buildDescriptionPrompt(), "narrative");
  };

  return (
    <div className="border-t border-outline/15 bg-surface-1">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-outline/10">
        <div className="flex items-center gap-2">
          <MessageSquare size={14} className="text-primary" />
          <div>
            <span className="text-xs font-heading font-bold text-text-secondary uppercase tracking-[0.06em]">
              Technical Assistant
            </span>
            <span className="text-[9px] text-text-tertiary ml-2" style={{ fontFamily: "var(--font-ko)" }}>AI 설명 생성 + 기술 질의응답</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Generate Description button */}
          {!hasDescription && file && (
            <button
              onClick={handleGenerateDescription}
              disabled={isStreaming}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-primary/15 border border-primary/25 text-[10px] font-bold text-primary uppercase hover:bg-primary/25 transition-colors disabled:opacity-40"
            >
              <BrainCircuit size={12} />
              Generate Description
            </button>
          )}
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_4px_rgba(94,180,255,0.5)]" />
            <span className="text-[9px] font-mono text-text-tertiary">
              Active
            </span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="max-h-64 overflow-y-auto px-5 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-6">
            <p className="text-[11px] text-text-tertiary">
              Click &quot;Generate Description&quot; for AI analysis, or ask a technical question below.
            </p>
            <p className="text-[10px] text-text-tertiary mt-1" style={{ fontFamily: "var(--font-ko)" }}>
              &quot;Generate Description&quot; 버튼으로 AI 분석을 실행하거나, 아래에서 기술 질문을 입력하세요.
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className="flex gap-3">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-bold ${
                msg.role === "user"
                  ? "bg-surface-3 text-text-secondary"
                  : msg.type === "narrative"
                  ? "bg-tertiary/15 text-tertiary"
                  : "bg-primary/15 text-primary"
              }`}
            >
              {msg.role === "user" ? "U" : "AI"}
            </div>
            <div className="flex-1 min-w-0">
              {msg.role === "user" && msg.type === "narrative" && (
                <span className="text-[9px] text-tertiary font-mono uppercase mb-1 block">System Narrative</span>
              )}
              <div className="text-xs text-text-secondary leading-relaxed whitespace-pre-wrap break-words">
                {msg.content}
                {isStreaming && i === messages.length - 1 && msg.role === "assistant" && (
                  <span className="text-primary animate-pulse">▌</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="flex items-center gap-2 px-5 py-3 border-t border-outline/10">
        <button className="text-text-tertiary hover:text-text-secondary transition-colors">
          <Paperclip size={14} />
        </button>
        <input
          type="text"
          className="flex-1 bg-transparent text-xs text-text-primary placeholder:text-text-tertiary outline-none font-body"
          placeholder="Ask a technical question about this drawing..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          disabled={!file || isStreaming}
        />
        <button
          onClick={handleSend}
          disabled={!file || isStreaming || !input.trim()}
          className="w-8 h-8 bg-primary/15 text-primary flex items-center justify-center rounded-sm hover:bg-primary/25 transition-colors disabled:opacity-30"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
