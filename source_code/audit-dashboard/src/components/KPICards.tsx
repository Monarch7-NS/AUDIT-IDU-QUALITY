"use client";

import { Summary, Scores } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

interface Props { summary: Summary; scores: Scores; }

const dims = [
  { key: "completude",  label: "Complétude",    icon: "○" },
  { key: "exactitude",  label: "Exactitude",    icon: "◎" },
  { key: "conformite",  label: "Séquencement",  icon: "⬡" },
  { key: "unicite",     label: "Unicité",       icon: "◈" },
  { key: "coherence",   label: "Cohérence",     icon: "◉" },
] as const;

function scoreVariant(v: number) {
  return v >= 80 ? "emerald" : v >= 60 ? "amber" : "red";
}

function scoreLabel(v: number) {
  return v >= 80 ? "Bon" : v >= 60 ? "Moyen" : "Critique";
}

function scoreTextColor(v: number) {
  return v >= 80 ? "text-emerald-600" : v >= 60 ? "text-amber-500" : "text-red-500";
}

function progressColor(v: number) {
  return v >= 80 ? "bg-emerald-500" : v >= 60 ? "bg-amber-400" : "bg-red-500";
}

export default function KPICards({ summary, scores }: Props) {
  return (
    <div className="space-y-4">
      {/* Global score + anomaly cards */}
      <div className="grid grid-cols-5 gap-4">
        <Card className="col-span-1 border-slate-100 shadow-none bg-slate-900 text-white">
          <CardContent className="p-5">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Score global</p>
            <div className="flex items-end gap-1 mt-2">
              <span className={`text-5xl font-bold ${scores.global >= 80 ? "text-emerald-400" : scores.global >= 60 ? "text-amber-400" : "text-red-400"}`}>
                {scores.global.toFixed(0)}
              </span>
              <span className="text-slate-500 text-lg mb-1">/100</span>
            </div>
            <div className="mt-3">
              <div className="h-1 rounded-full bg-slate-700">
                <div
                  className={`h-1 rounded-full ${scores.global >= 80 ? "bg-emerald-400" : scores.global >= 60 ? "bg-amber-400" : "bg-red-400"}`}
                  style={{ width: `${scores.global}%` }}
                />
              </div>
            </div>
            <p className="text-[11px] text-slate-400 mt-2">Toutes dimensions</p>
          </CardContent>
        </Card>

        {[
          { label: "Bloquantes", val: summary.bloquant, sub: "Action immédiate", color: "text-red-600", border: "border-red-100", dot: "bg-red-500" },
          { label: "Majeures",   val: summary.majeur,   sub: "Revue recommandée", color: "text-amber-600", border: "border-amber-100", dot: "bg-amber-400" },
          { label: "Mineures",   val: summary.mineur,   sub: "À surveiller", color: "text-blue-600", border: "border-blue-100", dot: "bg-blue-400" },
          { label: "Total anomalies", val: summary.total_anomalies, sub: "Toutes criticités", color: "text-slate-700", border: "border-slate-100", dot: "bg-slate-400" },
        ].map(({ label, val, sub, color, border, dot }) => (
          <Card key={label} className={`border shadow-none ${border}`}>
            <CardContent className="p-5">
              <div className="flex items-center gap-2 mb-2">
                <span className={`h-2 w-2 rounded-full ${dot}`} />
                <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">{label}</p>
              </div>
              <p className={`text-4xl font-bold ${color}`}>{val}</p>
              <p className="text-[11px] text-slate-400 mt-2">{sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* KDI — Indicateurs Clés de Défaillance */}
      <div className="grid grid-cols-3 gap-4">
        {[
          {
            label: "Modules avec Écart d'Heures",
            value: "21",
            total: "36",
            sub: "modules présentent un écart > 15% entre maquette et ADE",
            color: "text-red-600",
            progress: (21 / 36) * 100,
            pcolor: "bg-red-500",
          },
          {
            label: "Modules avec Séquence Invalidée",
            value: "20",
            total: "23",
            sub: "modules ont au moins une inversion de prérequis détectée",
            color: "text-amber-600",
            progress: (20 / 23) * 100,
            pcolor: "bg-amber-400",
          },
          {
            label: "Sessions Orphelines",
            value: "211",
            total: null,
            sub: "séances présentes dans ADE sans correspondance maquette",
            color: "text-violet-600",
            progress: (211 / 677) * 100,
            pcolor: "bg-violet-500",
          },
        ].map(({ label, value, total, sub, color, progress, pcolor }) => (
          <Card key={label} className="border-slate-100 shadow-none">
            <CardContent className="p-5">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 mb-3">{label}</p>
              <div className="flex items-end gap-1">
                <span className={`text-4xl font-bold ${color}`}>{value}</span>
                {total && <span className="text-slate-400 text-lg mb-0.5">/ {total}</span>}
              </div>
              <div className="mt-3 h-1.5 rounded-full bg-slate-100">
                <div className={`h-1.5 rounded-full ${pcolor}`} style={{ width: `${progress}%` }} />
              </div>
              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">{sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Dimension scores */}
      <div className="grid grid-cols-5 gap-4">
        {dims.map(({ key, label, icon }) => {
          const val = scores[key];
          return (
            <Card key={key} className="border-slate-100 shadow-none">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">{label}</p>
                  <span className="text-slate-300 text-xs">{icon}</span>
                </div>
                <div className="flex items-end gap-1">
                  <span className={`text-2xl font-bold ${scoreTextColor(val)}`}>{val.toFixed(0)}</span>
                  <span className="text-slate-400 text-xs mb-0.5">/100</span>
                </div>
                <div className="mt-2 h-1 rounded-full bg-slate-100">
                  <div className={`h-1 rounded-full ${progressColor(val)}`} style={{ width: `${val}%` }} />
                </div>
                <p className={`text-[10px] font-medium mt-2 ${scoreTextColor(val)}`}>{scoreLabel(val)}</p>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
