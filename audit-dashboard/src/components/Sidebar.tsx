"use client";

import { Separator } from "@/components/ui/separator";

interface NavItem { id: string; label: string; icon: React.ReactNode; }

interface SidebarProps {
  nav: NavItem[];
  active: string;
  setActive: (id: string) => void;
  generatedAt: string;
}

export default function Sidebar({ nav, active, setActive, generatedAt }: SidebarProps) {
  const date = generatedAt ? new Date(generatedAt).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" }) : "—";
  return (
    <aside className="fixed left-0 top-0 h-screen w-[240px] bg-white border-r border-slate-100 flex flex-col z-20">
      <div className="px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-slate-900 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <rect x="1" y="1" width="6" height="6" rx="1.5" fill="white" fillOpacity="0.9"/>
              <rect x="9" y="1" width="6" height="6" rx="1.5" fill="white" fillOpacity="0.5"/>
              <rect x="1" y="9" width="6" height="6" rx="1.5" fill="white" fillOpacity="0.5"/>
              <rect x="9" y="9" width="6" height="6" rx="1.5" fill="white" fillOpacity="0.9"/>
            </svg>
          </div>
          <div>
            <p className="font-semibold text-slate-900 text-sm leading-none">Polytech IDU</p>
            <p className="text-[11px] text-slate-400 mt-0.5">Audit Qualité</p>
          </div>
        </div>
      </div>

      <Separator />

      <div className="px-3 py-3 flex-1 overflow-y-auto">
        <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest px-3 mb-2">Navigation</p>
        <nav className="space-y-0.5">
          {nav.map(item => (
            <button
              key={item.id}
              onClick={() => setActive(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 text-left group ${
                active === item.id
                  ? "bg-slate-900 text-white"
                  : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <span className={`flex-shrink-0 ${active === item.id ? "text-white" : "text-slate-400 group-hover:text-slate-600"}`}>
                {item.icon}
              </span>
              <span className="font-medium text-[13px]">{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      <Separator />
      <div className="px-6 py-4">
        <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">Rapport généré</p>
        <p className="text-xs font-medium text-slate-600 mt-1">{date}</p>
      </div>
    </aside>
  );
}
