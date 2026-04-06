"use client";

import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { Upload, Trash2 } from "lucide-react";
import { apiUpload, API_BASE } from "@/lib/api";
import type { ClassifyResponse } from "@/lib/types";
import DrawingViewer from "@/components/analysis/DrawingViewer";
import AnalysisSidebar from "@/components/analysis/AnalysisSidebar";
import QAPanel from "@/components/analysis/QAPanel";

const IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".bmp", ".tiff"];
const DXF_EXTS = [".dxf"];
const CAD_3D_EXTS = [".stp", ".step", ".igs", ".iges", ".stl"];

export default function AnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [cadInfo, setCadInfo] = useState<string | null>(null);
  const [yoloCategory, setYoloCategory] = useState("");
  const [yoloConfidence, setYoloConfidence] = useState(0);
  const [metadata, setMetadata] = useState<Record<string, string>>({});

  const handleClear = useCallback(() => {
    if (imageUrl && imageUrl.startsWith("blob:")) {
      URL.revokeObjectURL(imageUrl);
    }
    setFile(null);
    setImageUrl(null);
    setCadInfo(null);
    setYoloCategory("");
    setYoloConfidence(0);
    setMetadata({});
  }, [imageUrl]);

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (!f) return;
      setFile(f);
      setImageUrl(null);
      setCadInfo(null);
      setYoloCategory("");
      setYoloConfidence(0);
      setMetadata({});

      const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();

      if (IMAGE_EXTS.includes(ext)) {
        // 이미지: 브라우저에서 직접 표시
        setImageUrl(URL.createObjectURL(f));
      } else if (DXF_EXTS.includes(ext)) {
        // DXF: SVG 변환
        try {
          const fd = new FormData();
          fd.append("file", f);
          const result = await apiUpload<{ svg: string }>("/viewer/dxf", fd);
          if (result.svg) {
            const svgBlob = new Blob([result.svg], { type: "image/svg+xml" });
            setImageUrl(URL.createObjectURL(svgBlob));
          }
        } catch {
          // DXF 변환 실패 → register fallback
          await tryRegisterForThumbnail(f);
        }
      } else if (CAD_3D_EXTS.includes(ext)) {
        // STP/STEP/IGES/STL: register → thumbnail, 실패 시 /viewer/stl로 메시 정보 표시
        const registered = await tryRegisterForThumbnail(f);
        if (!registered) {
          // Register 실패 → viewer/stl API로 3D 메시 정보 추출
          try {
            const fd = new FormData();
            fd.append("file", f);
            const stlResult = await apiUpload<{
              triangle_count: number;
              vertex_count: number;
              format: string;
              file_size_bytes: number;
            }>("/viewer/stl", fd);
            setCadInfo(
              `3D Model: ${stlResult.format.toUpperCase()} | ` +
              `${stlResult.triangle_count.toLocaleString()} triangles | ` +
              `${(stlResult.file_size_bytes / 1024).toFixed(0)} KB`
            );
            setMetadata((prev) => ({
              ...prev,
              Format: stlResult.format.toUpperCase(),
              Triangles: stlResult.triangle_count.toLocaleString(),
              Vertices: stlResult.vertex_count.toLocaleString(),
            }));
          } catch {
            setCadInfo(`3D File: ${f.name} (preview unavailable)`);
          }
        }
      } else {
        // 기타: DWG 등 → register 시도
        await tryRegisterForThumbnail(f);
      }
    },
    []
  );

  /** Register 시도 → thumbnail URL 반환, 성공 여부 return */
  async function tryRegisterForThumbnail(f: File): Promise<boolean> {
    try {
      const formData = new FormData();
      formData.append("file", f);
      const record = await apiUpload<{ drawing_id: string }>(
        "/drawings/register", formData, { category: "", use_llm: "false" }
      );
      setImageUrl(`${API_BASE}/drawings/${record.drawing_id}/thumbnail`);
      setMetadata((prev) => ({ ...prev, "Drawing ID": record.drawing_id }));
      return true;
    } catch {
      return false;
    }
  }

  const classifyMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("No file");
      const formData = new FormData();
      formData.append("file", file);
      return apiUpload<ClassifyResponse>("/drawings/classify", formData);
    },
    onSuccess: (data) => {
      setYoloCategory(data.category);
      setYoloConfidence(data.confidence);
      setMetadata((prev) => ({
        ...prev,
        Category: data.category,
        Confidence: `${(data.confidence * 100).toFixed(1)}%`,
      }));
    },
  });

  // Empty state
  if (!file) {
    return (
      <div>
        <div className="mb-6">
          <h1 className="text-2xl font-heading font-bold uppercase tracking-tight">
            Analysis
          </h1>
          <p className="text-sm text-text-tertiary uppercase tracking-[0.1em] mt-0.5">
            Real-time geometric inspection and metadata extraction
          </p>
          <p className="text-sm text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>
            AI가 도면을 분석하여 설명, 분류, 질문 답변을 제공합니다.
          </p>
        </div>

        <label className="flex flex-col items-center justify-center h-64 border-2 border-dashed border-outline/30 bg-surface-1 cursor-pointer hover:border-primary/40 transition-colors">
          <Upload size={48} className="text-text-tertiary mb-3" />
          <span className="text-base font-bold text-text-secondary uppercase tracking-wider">
            Upload Drawing
          </span>
          <span className="text-sm text-text-tertiary mt-1">
            PNG, JPG, DXF, DWG, STEP, IGES, STL
          </span>
          <span className="text-sm text-text-tertiary mt-0.5 uppercase">
            Drag &amp; Drop or Click to Browse
          </span>
          <input
            type="file"
            className="hidden"
            accept=".png,.jpg,.jpeg,.dxf,.dwg,.stp,.step,.igs,.iges,.stl"
            onChange={handleFileChange}
          />
        </label>

        <div className="grid grid-cols-3 gap-4 mt-8">
          {[
            { title: "Description", desc: "AI analyzes drawing structure and features automatically" },
            { title: "Classification", desc: "AI determines drawing category with YOLO-cls" },
            { title: "Q&A", desc: "Ask questions and get AI-powered technical answers" },
          ].map((card) => (
            <div
              key={card.title}
              className="bg-surface-1 border border-outline/10 p-6 text-center hover:border-primary/20 transition-colors"
            >
              <h4 className="text-base font-heading font-semibold text-text-primary mb-2">
                {card.title}
              </h4>
              <p className="text-sm text-text-tertiary leading-relaxed">
                {card.desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Analysis view
  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 7rem)" }}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h1 className="text-lg font-heading font-bold uppercase tracking-tight">
            Analysis
          </h1>
          <p className="text-sm text-text-tertiary font-mono">
            {file.name}
          </p>
        </div>
        <button
          onClick={handleClear}
          className="flex items-center gap-2 px-4 py-2 border border-outline/20 text-xs font-bold uppercase tracking-wider text-text-secondary hover:text-error hover:border-error/30 transition-colors"
        >
          <Trash2 size={16} />
          <div className="text-left">
            <div>Clear Drawing</div>
            <div className="text-xs font-normal normal-case tracking-normal opacity-60" style={{ fontFamily: "var(--font-ko)" }}>도면 초기화</div>
          </div>
        </button>
      </div>

      <div className="flex flex-1 min-h-0">
        <div className={`flex-[6] ${file?.name.toLowerCase().endsWith(".dxf") ? "dxf-invert" : ""}`}>
          <DrawingViewer imageUrl={imageUrl} cadInfo={cadInfo} />
        </div>

        <div className="flex-[4] max-w-[380px]">
          <AnalysisSidebar
            metadata={metadata}
            yoloCategory={yoloCategory}
            yoloConfidence={yoloConfidence}
            onClassify={() => classifyMutation.mutate()}
          />
        </div>
      </div>

      <QAPanel file={file} />
    </div>
  );
}
