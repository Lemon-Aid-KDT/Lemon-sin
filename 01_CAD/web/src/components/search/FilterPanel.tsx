"use client";

const FILE_FORMATS = [
  { id: "png", label: "PNG (.png)", defaultChecked: true },
  { id: "dxf", label: "DXF (.dxf)", defaultChecked: true },
  { id: "jpg", label: "JPG (.jpg)", defaultChecked: false },
];

const MATERIALS = ["SUS304", "SS400", "S45C", "AL6061"];

interface FilterPanelProps {
  categories: string[];
  selectedFormats: string[];
  onFormatsChange: (f: string[]) => void;
  selectedCategory: string;
  onCategoryChange: (c: string) => void;
  selectedMaterials: string[];
  onMaterialsChange: (m: string[]) => void;
}

export default function FilterPanel({
  categories,
  selectedFormats,
  onFormatsChange,
  selectedCategory,
  onCategoryChange,
  selectedMaterials,
  onMaterialsChange,
}: FilterPanelProps) {
  const toggleFormat = (id: string) => {
    onFormatsChange(
      selectedFormats.includes(id)
        ? selectedFormats.filter((f) => f !== id)
        : [...selectedFormats, id]
    );
  };

  const toggleMaterial = (m: string) => {
    onMaterialsChange(
      selectedMaterials.includes(m)
        ? selectedMaterials.filter((x) => x !== m)
        : [...selectedMaterials, m]
    );
  };

  return (
    <div className="space-y-6">
      {/* FILE FORMAT */}
      <div>
        <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-0.5">
          File Format
        </h4>
        <p className="text-[10px] text-text-tertiary mb-3" style={{ fontFamily: "var(--font-ko)" }}>파일 형식</p>
        <div className="space-y-2">
          {FILE_FORMATS.map((fmt) => (
            <label
              key={fmt.id}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <input
                type="checkbox"
                checked={selectedFormats.includes(fmt.id)}
                onChange={() => toggleFormat(fmt.id)}
                className="w-3.5 h-3.5 rounded-sm border border-outline/30 bg-surface-2 accent-primary"
              />
              <span className="text-xs text-text-secondary group-hover:text-text-primary transition-colors">
                {fmt.label}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* CATEGORY */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em]">
              Category
            </h4>
            <p className="text-[10px] text-text-tertiary" style={{ fontFamily: "var(--font-ko)" }}>카테고리</p>
          </div>
          <span className="text-[10px] font-mono text-primary">
            {categories.length} TOTAL
          </span>
        </div>
        <input
          type="text"
          placeholder="Filter categories..."
          className="w-full bg-surface-2 border border-outline/15 px-3 py-1.5 text-xs text-text-primary placeholder:text-text-tertiary outline-none mb-2 rounded-sm focus:border-primary/40 transition-colors"
        />
        <div className="space-y-0.5 max-h-40 overflow-y-auto">
          <button
            onClick={() => onCategoryChange("")}
            className={`w-full text-left px-3 py-1.5 text-xs rounded-sm transition-colors ${
              !selectedCategory
                ? "bg-primary/10 text-primary border-l-2 border-primary"
                : "text-text-secondary hover:bg-surface-2"
            }`}
          >
            All Categories
          </button>
          {categories.slice(0, 10).map((cat) => (
            <button
              key={cat}
              onClick={() => onCategoryChange(cat)}
              className={`w-full text-left px-3 py-1.5 text-xs rounded-sm transition-colors flex justify-between ${
                selectedCategory === cat
                  ? "bg-primary/10 text-primary border-l-2 border-primary"
                  : "text-text-secondary hover:bg-surface-2"
              }`}
            >
              <span>{cat.replace(/_/g, " ")}</span>
            </button>
          ))}
        </div>
      </div>

      {/* MATERIAL */}
      <div>
        <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-0.5">
          Material
        </h4>
        <p className="text-[10px] text-text-tertiary mb-3" style={{ fontFamily: "var(--font-ko)" }}>재질</p>
        <div className="flex flex-wrap gap-1.5">
          {MATERIALS.map((m) => (
            <button
              key={m}
              onClick={() => toggleMaterial(m)}
              className={`px-3 py-1 text-[10px] font-mono font-semibold rounded-sm border transition-colors ${
                selectedMaterials.includes(m)
                  ? "bg-primary/15 text-primary border-primary/30"
                  : "text-text-tertiary border-outline/20 hover:border-outline/40"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* DATE RANGE */}
      <div>
        <h4 className="text-[10px] font-bold text-text-secondary uppercase tracking-[0.1em] mb-0.5">
          Date Range
        </h4>
        <p className="text-[10px] text-text-tertiary mb-3" style={{ fontFamily: "var(--font-ko)" }}>기간 설정</p>
        <input
          type="date"
          className="w-full bg-surface-2 border border-outline/15 px-3 py-1.5 text-xs text-text-tertiary outline-none rounded-sm mb-1.5"
        />
        <div className="text-center text-[10px] text-text-tertiary my-1">TO</div>
        <input
          type="date"
          className="w-full bg-surface-2 border border-outline/15 px-3 py-1.5 text-xs text-text-tertiary outline-none rounded-sm"
        />
      </div>
    </div>
  );
}
