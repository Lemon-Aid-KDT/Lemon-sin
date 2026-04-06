"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch, apiUpload } from "@/lib/api";
import type {
  StatsResponse,
  SearchResult,
  UnifiedSearchResult,
  UnifiedSearchRequest,
} from "@/lib/types";
import SearchBar from "@/components/search/SearchBar";
import FilterPanel from "@/components/search/FilterPanel";
import ResultCard from "@/components/search/ResultCard";
import VectorPreview from "@/components/search/VectorPreview";

/** Convert SearchResult (image/dxf API) → UnifiedSearchResult format */
function toUnified(r: SearchResult): UnifiedSearchResult {
  return {
    record_id: r.drawing_id,
    score: r.score,
    channel_scores: {},
    metadata: {
      file_name: r.file_name,
      file_path: r.file_path,
      category: r.category,
      ...r.metadata,
    },
    thumbnail_path: "",
  };
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedFormats, setSelectedFormats] = useState(["png", "dxf"]);
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([]);
  const [previewResult, setPreviewResult] =
    useState<UnifiedSearchResult | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState("");

  // Stats for categories
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<StatsResponse>("/stats"),
  });

  // Text search mutation (returns UnifiedSearchResult[])
  const searchMutation = useMutation({
    mutationFn: (req: UnifiedSearchRequest) =>
      apiFetch<UnifiedSearchResult[]>("/drawings/search/unified", {
        method: "POST",
        body: JSON.stringify(req),
      }),
  });

  // Image search mutation (returns SearchResult[] → convert to UnifiedSearchResult[])
  const imageSearchMutation = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const raw = await apiUpload<SearchResult[]>("/drawings/search/image", fd, {
        top_k: "12",
      });
      return raw.map(toUnified);
    },
  });

  // DXF structure search mutation (returns SearchResult[] → convert)
  const dxfSearchMutation = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const raw = await apiUpload<SearchResult[]>(
        "/drawings/search/dxf-structure",
        fd,
        { top_k: "12" }
      );
      return raw.map(toUnified);
    },
  });

  const results =
    imageSearchMutation.data ??
    dxfSearchMutation.data ??
    searchMutation.data ??
    [];
  const isLoading =
    searchMutation.isPending ||
    imageSearchMutation.isPending ||
    dxfSearchMutation.isPending;

  const handleSearch = () => {
    if (!query.trim() && !selectedCategory) return;
    setUploadedFileName("");
    imageSearchMutation.reset();
    dxfSearchMutation.reset();
    searchMutation.mutate({
      text: query || "*",
      channels: ["text", "image"],
      top_k: 12,
      category: selectedCategory,
    });
  };

  const handleImageUpload = (file: File) => {
    setUploadedFileName(file.name);
    searchMutation.reset();
    dxfSearchMutation.reset();
    imageSearchMutation.mutate(file);
  };

  const handleDxfUpload = (file: File) => {
    setUploadedFileName(file.name);
    searchMutation.reset();
    imageSearchMutation.reset();
    dxfSearchMutation.mutate(file);
  };

  const handleClearUpload = () => {
    setUploadedFileName("");
    imageSearchMutation.reset();
    dxfSearchMutation.reset();
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <SearchBar
          query={query}
          onQueryChange={setQuery}
          onSearch={handleSearch}
          onImageUpload={handleImageUpload}
          onDxfUpload={handleDxfUpload}
          isLoading={isLoading}
          uploadedFileName={uploadedFileName}
          onClearUpload={uploadedFileName ? handleClearUpload : undefined}
        />
      </div>

      {/* Body: Filter (left) + Results (right) */}
      <div className="flex gap-6">
        {/* Left: Filters */}
        <div className="w-56 flex-shrink-0">
          <FilterPanel
            categories={stats?.categories ?? []}
            selectedFormats={selectedFormats}
            onFormatsChange={setSelectedFormats}
            selectedCategory={selectedCategory}
            onCategoryChange={setSelectedCategory}
            selectedMaterials={selectedMaterials}
            onMaterialsChange={setSelectedMaterials}
          />
        </div>

        {/* Right: Results */}
        <div className="flex-1">
          {results.length > 0 ? (
            <>
              {/* Results Header */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-heading font-bold text-text-primary">
                    Search Results
                  </h2>
                  <p className="text-[11px] text-text-tertiary">
                    Displaying {results.length} matching engineering components
                  </p>
                </div>
                <span className="text-[10px] text-text-tertiary font-mono uppercase">
                  Sort by:{" "}
                  <span className="text-primary font-semibold">
                    Similarity Score ↓
                  </span>
                </span>
              </div>

              {/* 3-column Grid */}
              <div className="grid grid-cols-3 gap-4">
                {results.map((r, i) => (
                  <ResultCard
                    key={r.record_id ? `${r.record_id}-${i}` : `result-${i}`}
                    drawingId={r.record_id ?? ""}
                    fileName={
                      (r.metadata?.file_name as string) ||
                      r.record_id?.slice(0, 12) ||
                      `Result ${i + 1}`
                    }
                    score={r.score ?? 0}
                    category={(r.metadata?.category as string) ?? ""}
                    partNumber={
                      Array.isArray(r.metadata?.part_numbers)
                        ? (r.metadata.part_numbers as string[])[0]
                        : undefined
                    }
                    onClick={() => setPreviewResult(r)}
                  />
                ))}
              </div>
            </>
          ) : isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-sm text-text-tertiary">Searching... <span style={{ fontFamily: "var(--font-ko)" }}>검색 중...</span></p>
              </div>
            </div>
          ) : (
            /* Empty State */
            <div className="flex items-center justify-center h-64">
              <div className="text-center max-w-md">
                <p className="text-4xl mb-4 opacity-30">🔍</p>
                <h3 className="text-base font-heading font-semibold text-text-secondary mb-2">
                  No Results
                </h3>
                <p className="text-xs text-text-tertiary leading-relaxed">
                  Enter a search query above and click Execute Search.
                  <br />
                  Try: &quot;M8 Bolt&quot;, &quot;shaft bearing&quot;, or &quot;SUS304 bracket&quot;
                </p>
                <p className="text-[11px] text-text-tertiary mt-2 leading-relaxed" style={{ fontFamily: "var(--font-ko)" }}>
                  위 검색창에 검색어를 입력하고 검색 실행 버튼을 클릭하세요.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Vector Preview Panel */}
      {previewResult && (
        <VectorPreview
          drawingId={previewResult.record_id ?? ""}
          score={previewResult.score ?? 0}
          channelScores={previewResult.channel_scores ?? {}}
          onClose={() => setPreviewResult(null)}
        />
      )}
    </div>
  );
}
