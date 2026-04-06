"use client";

import { useRef } from "react";
import { Search, Image, Layers3, X } from "lucide-react";

export default function SearchBar({
  query,
  onQueryChange,
  onSearch,
  onImageUpload,
  onDxfUpload,
  isLoading,
  uploadedFileName,
  onClearUpload,
}: {
  query: string;
  onQueryChange: (q: string) => void;
  onSearch: () => void;
  onImageUpload: (file: File) => void;
  onDxfUpload: (file: File) => void;
  isLoading: boolean;
  uploadedFileName?: string;
  onClearUpload?: () => void;
}) {
  const imageInputRef = useRef<HTMLInputElement>(null);
  const dxfInputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        {/* Search Input */}
        <div className="flex-1 flex items-center gap-2 bg-surface-2 border border-outline/15 px-4 py-2.5 rounded-sm focus-within:border-primary/40 transition-colors">
          <Search size={16} className="text-text-tertiary flex-shrink-0" />
          <input
            type="text"
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-tertiary outline-none font-body"
            placeholder="Natural Language Search (e.g., 'M8 Bolt with SUS304')"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSearch()}
          />
        </div>

        {/* Image Upload */}
        <button
          onClick={() => imageInputRef.current?.click()}
          className="flex items-center gap-2 px-5 py-2.5 bg-surface-2 border border-outline/15 text-xs font-bold uppercase tracking-wider text-text-secondary hover:text-text-primary hover:border-outline/30 transition-colors"
        >
          <Image size={14} />
          <div className="text-left">
            <div>Image Upload</div>
            <div className="text-[9px] font-normal opacity-60 normal-case tracking-normal" style={{ fontFamily: "var(--font-ko)" }}>이미지 업로드</div>
          </div>
        </button>
        <input
          ref={imageInputRef}
          type="file"
          className="hidden"
          accept=".png,.jpg,.jpeg,.bmp,.tiff"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onImageUpload(f);
            e.target.value = "";
          }}
        />

        {/* DXF Upload */}
        <button
          onClick={() => dxfInputRef.current?.click()}
          className="flex items-center gap-2 px-5 py-2.5 bg-surface-2 border border-outline/15 text-xs font-bold uppercase tracking-wider text-text-secondary hover:text-text-primary hover:border-outline/30 transition-colors"
        >
          <Layers3 size={14} />
          <div className="text-left">
            <div>DXF Upload</div>
            <div className="text-[9px] font-normal opacity-60 normal-case tracking-normal" style={{ fontFamily: "var(--font-ko)" }}>DXF 업로드</div>
          </div>
        </button>
        <input
          ref={dxfInputRef}
          type="file"
          className="hidden"
          accept=".dxf"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onDxfUpload(f);
            e.target.value = "";
          }}
        />

        {/* Execute Search */}
        <button
          onClick={onSearch}
          disabled={isLoading}
          className="px-6 py-2.5 bg-primary text-background text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-primary-dark transition-colors disabled:opacity-50"
        >
          {isLoading ? "Searching..." : "Execute Search"}
        </button>
      </div>

      {/* Uploaded file indicator */}
      {uploadedFileName && (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 border border-primary/20 w-fit">
          <span className="text-[11px] text-primary font-mono">
            {uploadedFileName}
          </span>
          {onClearUpload && (
            <button onClick={onClearUpload} className="text-primary/60 hover:text-primary transition-colors">
              <X size={12} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
