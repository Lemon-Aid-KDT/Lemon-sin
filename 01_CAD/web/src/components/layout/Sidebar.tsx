"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  Search,
  BrainCircuit,
  Layers3,
  Box,
  Wrench,
  FileText,
  HelpCircle,
  Plus,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", ko: "대시보드", icon: LayoutDashboard },
  { href: "/register", label: "Registration", ko: "도면 등록", icon: Upload },
  { href: "/search", label: "Search", ko: "도면 검색", icon: Search },
  { href: "/analysis", label: "Analysis", ko: "도면 분석", icon: BrainCircuit },
  { href: "/viewer/dxf", label: "DXF Viewer", ko: "DXF 뷰어", icon: Layers3 },
  { href: "/viewer/stl", label: "3D Viewer", ko: "3D 뷰어", icon: Box },
  { href: "/tools", label: "Tools", ko: "도구", icon: Wrench },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-16 bottom-8 w-64 bg-surface-1 border-r border-outline/15 flex flex-col z-40">
      {/* Branding */}
      <div className="px-5 pt-5 pb-4 border-b border-outline/10">
        <div className="text-[11px] font-bold text-text-tertiary uppercase tracking-[0.12em] font-heading">
          Engineering Terminal
        </div>
        <div className="text-[10px] text-text-tertiary font-mono mt-0.5">
          v5.4.0-PRO
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-3 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-sm text-[13px] font-medium transition-all duration-150 ${
                isActive
                  ? "bg-primary/8 text-primary border-l-[3px] border-primary pl-[9px]"
                  : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
              }`}
            >
              <item.icon size={16} strokeWidth={isActive ? 2.2 : 1.5} />
              <div className="flex flex-col">
                <span className="uppercase tracking-[0.04em]">{item.label}</span>
                <span className="text-[10px] font-normal tracking-normal opacity-60" style={{ fontFamily: "var(--font-ko)" }}>
                  {item.ko}
                </span>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* New Project Button */}
      <div className="px-3 pb-3">
        <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-background text-xs font-bold uppercase tracking-wider rounded-sm hover:bg-primary-dark transition-colors">
          <Plus size={14} />
          New Project
        </button>
      </div>

      {/* Footer Links */}
      <div className="px-5 py-3 border-t border-outline/10 space-y-2">
        <Link
          href="#"
          className="flex items-center gap-2 text-[11px] text-text-tertiary hover:text-text-secondary transition-colors"
        >
          <FileText size={12} />
          Documentation
        </Link>
        <Link
          href="#"
          className="flex items-center gap-2 text-[11px] text-text-tertiary hover:text-text-secondary transition-colors"
        >
          <HelpCircle size={12} />
          Support
        </Link>
      </div>
    </aside>
  );
}
