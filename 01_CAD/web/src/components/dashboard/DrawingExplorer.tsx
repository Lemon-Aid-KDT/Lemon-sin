"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { apiFetch, drawingThumbnailUrl } from "@/lib/api";
import type { PaginatedResponse, StatsResponse } from "@/lib/types";

const PAGE_SIZE = 15;
const MATERIALS = ["S45C", "SUS304", "SUJ2", "FC250", "AL6061", "SS400", "SCM415"];

export default function DrawingExplorer() {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("");
  const [material, setMaterial] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Stats for category list
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: () => apiFetch<StatsResponse>("/stats"),
  });

  // Drawings with filters
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(PAGE_SIZE),
    ...(category && { category }),
    ...(material && { material }),
    ...(search && { search }),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["drawings-explorer", page, category, material, search],
    queryFn: () => apiFetch<PaginatedResponse>(`/drawings?${params}`),
  });

  const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE);

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const handleCategoryChange = (cat: string) => {
    setCategory(cat);
    setPage(1);
  };

  const handleMaterialChange = (mat: string) => {
    setMaterial(mat);
    setPage(1);
  };

  return (
    <div className="bg-surface-1 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-outline/10">
        <div>
          <h3 className="text-base font-heading font-bold text-text-primary uppercase tracking-[0.04em]">
            Drawing Explorer
          </h3>
          <p className="text-[10px] text-text-tertiary mt-0.5" style={{ fontFamily: "var(--font-ko)" }}>
            전체 도면 탐색 · {(data?.total ?? 0).toLocaleString()}건
          </p>
        </div>
        <span className="text-[10px] text-primary font-mono uppercase">
          {(data?.total ?? 0).toLocaleString()} TOTAL
        </span>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-outline/10 bg-surface-2/30">
        {/* Category */}
        <select
          value={category}
          onChange={(e) => handleCategoryChange(e.target.value)}
          className="bg-surface-2 border border-outline/15 px-3 py-1.5 text-xs text-text-secondary outline-none rounded-sm min-w-[160px]"
        >
          <option value="">전체 카테고리</option>
          {(stats?.categories ?? []).map((cat) => (
            <option key={cat} value={cat}>
              {cat.replace(/_/g, " ")}
            </option>
          ))}
        </select>

        {/* Material */}
        <select
          value={material}
          onChange={(e) => handleMaterialChange(e.target.value)}
          className="bg-surface-2 border border-outline/15 px-3 py-1.5 text-xs text-text-secondary outline-none rounded-sm min-w-[120px]"
        >
          <option value="">전체 재질</option>
          {MATERIALS.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>

        {/* Search */}
        <div className="flex-1 flex items-center gap-1.5 bg-surface-2 border border-outline/15 px-3 py-1.5 rounded-sm">
          <Search size={12} className="text-text-tertiary" />
          <input
            type="text"
            placeholder="파일명 또는 부품번호 검색..."
            className="flex-1 bg-transparent text-xs text-text-primary placeholder:text-text-tertiary outline-none"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
        </div>

        <button
          onClick={handleSearch}
          className="px-4 py-1.5 bg-primary text-background text-[11px] font-bold uppercase rounded-sm hover:bg-primary-dark transition-colors"
        >
          검색
        </button>

        {(category || material || search) && (
          <button
            onClick={() => { setCategory(""); setMaterial(""); setSearch(""); setSearchInput(""); setPage(1); }}
            className="px-3 py-1.5 border border-outline/20 text-[11px] text-text-tertiary hover:text-text-secondary rounded-sm transition-colors"
          >
            초기화
          </button>
        )}
      </div>

      {/* Table */}
      <table className="w-full text-left">
        <thead className="bg-surface-3">
          <tr>
            {["도면 미리보기", "Drawing ID", "포맷", "카테고리", "부품번호 / 재질"].map((h) => (
              <th key={h} className="px-5 py-2.5 text-[11px] uppercase tracking-[0.06em] font-bold text-text-secondary" style={{ fontFamily: "var(--font-ko)" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            <tr><td colSpan={5} className="px-5 py-8 text-center text-sm text-text-tertiary">로딩 중...</td></tr>
          ) : (data?.items ?? []).length === 0 ? (
            <tr><td colSpan={5} className="px-5 py-8 text-center text-sm text-text-tertiary">결과가 없습니다.</td></tr>
          ) : (
            (data?.items ?? []).map((rec) => {
              const isHovered = hoveredId === rec.drawing_id;
              return (
                <tr
                  key={rec.drawing_id}
                  className="border-b border-background hover:bg-surface-2/50 transition-colors"
                  onMouseEnter={() => setHoveredId(rec.drawing_id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  {/* Preview */}
                  <td className="px-5 py-2 relative">
                    <div className="w-12 h-12 bg-surface-3 border border-outline/15 overflow-hidden rounded-sm">
                      <img
                        src={drawingThumbnailUrl(rec.drawing_id)}
                        alt={rec.file_name}
                        className="w-full h-full object-contain opacity-80 hover:opacity-100 transition-opacity"
                        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                    {isHovered && (
                      <div className="absolute left-20 top-0 z-50 w-80 bg-surface-1 border border-outline/20 shadow-2xl shadow-black/60 overflow-hidden pointer-events-none">
                        <div className="aspect-square bg-viewer-bg flex items-center justify-center">
                          <img src={drawingThumbnailUrl(rec.drawing_id)} alt="" className="max-w-full max-h-full object-contain" />
                        </div>
                        <div className="p-3.5 space-y-1.5">
                          <div className="text-xs font-bold text-text-primary font-heading">{rec.file_name}</div>
                          <div className="text-[11px] text-text-tertiary">Category: <span className="text-text-secondary">{rec.category?.replace(/_/g, " ")}</span></div>
                          {rec.part_numbers?.length > 0 && <div className="text-[11px] text-primary font-mono">{rec.part_numbers.join(", ")}</div>}
                          {rec.materials?.length > 0 && <div className="text-[11px] text-text-tertiary">Material: {rec.materials.join(", ")}</div>}
                        </div>
                      </div>
                    )}
                  </td>
                  {/* ID + filename */}
                  <td className="px-5 py-2">
                    <div className="text-xs font-mono text-text-primary">#{rec.drawing_id.slice(0, 12)}</div>
                    <div className="text-[11px] text-text-tertiary truncate max-w-[140px]">{rec.file_name}</div>
                  </td>
                  {/* Format */}
                  <td className="px-5 py-2">
                    <span className="text-[11px] px-2 py-0.5 bg-surface-3 text-text-secondary">{rec.dxf_path ? "DXF" : "PNG"}</span>
                  </td>
                  {/* Category */}
                  <td className="px-5 py-2 text-xs text-text-secondary">
                    {rec.category?.replace(/_/g, " ") || "—"}
                  </td>
                  {/* Part Number / Material */}
                  <td className="px-5 py-2">
                    {rec.part_numbers?.length > 0 && (
                      <div className="text-[11px] font-mono text-primary">{rec.part_numbers[0]}</div>
                    )}
                    {rec.materials?.length > 0 && (
                      <div className="text-[10px] text-text-tertiary">{rec.materials.join(", ")}</div>
                    )}
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 px-5 py-3 border-t border-outline/10">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="p-1.5 text-text-tertiary hover:text-text-primary disabled:opacity-30 transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-xs text-text-secondary font-mono">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="p-1.5 text-text-tertiary hover:text-text-primary disabled:opacity-30 transition-colors"
          >
            <ChevronRight size={16} />
          </button>
          <span className="text-[10px] text-text-tertiary ml-2" style={{ fontFamily: "var(--font-ko)" }}>
            총 {(data?.total ?? 0).toLocaleString()}건
          </span>
        </div>
      )}
    </div>
  );
}
