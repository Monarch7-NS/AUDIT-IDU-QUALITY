"use client";

import { useEffect, useState } from "react";
import { AuditReport, HoursRow, Dependance } from "@/types";
import Sidebar from "./Sidebar";
import KPICards from "./KPICards";
import ChartsOverview from "./ChartsOverview";
import AgendaView from "./AgendaView";
import AnomalyTable from "./AnomalyTable";
import HoursChart from "./HoursChart";
import DAGView from "./DAGView";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const NAV = [
  {
    id: "kpi",
    label: "Vue générale",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="1" y="9" width="4" height="6" rx="1"/>
        <rect x="6" y="5" width="4" height="10" rx="1"/>
        <rect x="11" y="1" width="4" height="14" rx="1"/>
      </svg>
    ),
  },
  {
    id: "agenda",
    label: "Agenda pédagogique",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="1" y="2" width="14" height="13" rx="2"/>
        <path d="M5 1v2M11 1v2M1 6h14"/>
      </svg>
    ),
  },
  {
    id: "anomalies",
    label: "Anomalies",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M8 1L15 14H1L8 1z"/>
        <path d="M8 6v3M8 11v1"/>
      </svg>
    ),
  },
  {
    id: "heures",
    label: "Écarts horaires",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="8" cy="8" r="7"/>
        <path d="M8 4v4l3 2"/>
      </svg>
    ),
  },
  {
    id: "dag",
    label: "Séquencement DAG",
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="3" cy="8" r="2"/>
        <circle cx="13" cy="3" r="2"/>
        <circle cx="13" cy="13" r="2"/>
        <path d="M5 8l6-4M5 8l6 4"/>
      </svg>
    ),
  },
];

export default function Dashboard() {
  const [report, setReport]   = useState<AuditReport | null>(null);
  const [hours, setHours]     = useState<HoursRow[]>([]);
  const [deps, setDeps]       = useState<Dependance[]>([]);
  const [active, setActive]   = useState("kpi");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/data/report.json").then(r => r.json()),
      fetch("/data/hours.json").then(r => r.json()),
      fetch("/data/dependances.json").then(r => r.json()),
    ]).then(([rep, hrs, dep]) => {
      setReport(rep);
      setHours(hrs);
      setDeps(dep);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-900 border-t-transparent" />
          <p className="text-sm text-slate-400">Chargement du rapport…</p>
        </div>
      </div>
    );
  }

  if (!report) return <p className="p-8 text-red-600">Erreur de chargement du rapport.</p>;

  const currentNav = NAV.find(n => n.id === active);
  const globalScore = report.scores.global;

  return (
    <div className="flex h-screen bg-slate-50/50 overflow-hidden">
      <Sidebar nav={NAV} active={active} setActive={setActive} generatedAt={report.generated_at} />

      <main className="flex-1 overflow-y-auto ml-[240px]">
        {/* Topbar */}
        <div className="sticky top-0 z-10 bg-white border-b border-slate-100 px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-base font-semibold text-slate-900">{currentNav?.label}</h1>
              <p className="text-[11px] text-slate-400 mt-0.5">Polytech Annecy-Chambéry · Filière IDU</p>
            </div>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold border ${
                globalScore >= 80 ? "bg-emerald-50 border-emerald-200 text-emerald-700" :
                globalScore >= 60 ? "bg-amber-50 border-amber-200 text-amber-700" :
                "bg-red-50 border-red-200 text-red-700"
              }`}>
                <span className={`h-1.5 w-1.5 rounded-full ${globalScore >= 80 ? "bg-emerald-500" : globalScore >= 60 ? "bg-amber-500" : "bg-red-500"}`} />
                Score global : {globalScore.toFixed(0)}/100
              </div>
              <div className="h-8 w-8 rounded-lg bg-slate-900 flex items-center justify-center text-white text-[11px] font-bold">
                IDU
              </div>
            </div>
          </div>
        </div>

        <div className="p-8 space-y-6">
          {active === "kpi" && (
            <>
              <KPICards summary={report.summary} scores={report.scores} />
              <ChartsOverview scores={report.scores} anomalies={report.anomalies} />
            </>
          )}
          {active === "agenda"    && <AgendaView events={report.events} anomalies={report.anomalies} />}
          {active === "anomalies" && <AnomalyTable anomalies={report.anomalies} />}
          {active === "heures"    && <HoursChart rows={hours} />}
          {active === "dag"       && <DAGView dependances={deps} />}
        </div>
      </main>
    </div>
  );
}
