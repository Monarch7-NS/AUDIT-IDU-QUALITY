"use client";

import { useState, useMemo } from "react";
import { HoursRow } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid,
} from "recharts";

interface Props { rows: HoursRow[]; }

const TYPE_COLORS = { CM: "#0f172a", TD: "#475569", TP: "#94a3b8" };

export default function HoursChart({ rows }: Props) {
  const [typeFilter, setTypeFilter] = useState<string>("Tous");
  const [top, setTop] = useState<number>(20);

  const filtered = useMemo(() => {
    let r = typeFilter === "Tous" ? rows : rows.filter(x => x.type === typeFilter);
    return r.filter(x => x.ecart > 0).slice(0, top);
  }, [rows, typeFilter, top]);

  const chartData = filtered.map(r => ({
    name: `${r.module} ${r.type}`,
    Maquette: r.maquette,
    ADE: r.ade,
    ecart: r.ecart,
    type: r.type,
  }));

  return (
    <div className="space-y-4">
      <Card className="border-slate-100 shadow-none">
        <CardContent className="p-5">
          <div className="flex flex-wrap items-end gap-6">
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Type de séance</p>
              <div className="flex gap-2">
                {["Tous", "CM", "TD", "TP"].map(t => (
                  <button
                    key={t}
                    onClick={() => setTypeFilter(t)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                      typeFilter === t
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white text-slate-500 border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Top N</p>
              <select
                value={top}
                onChange={e => setTop(Number(e.target.value))}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-slate-900 bg-white text-slate-700"
              >
                {[10, 20, 30, 50].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div className="ml-auto">
              <span className="text-[11px] text-slate-400">
                <span className="font-semibold text-slate-600">{filtered.length}</span> modules avec écart
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-100 shadow-none">
        <CardHeader className="pb-0 pt-5 px-6">
          <CardTitle className="text-sm font-semibold text-slate-700">Comparaison Maquette vs ADE — Volume horaire</CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6 pt-4">
          <ResponsiveContainer width="100%" height={380}>
            <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 100 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f8fafc" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 9, fill: "#94a3b8" }}
                angle={-45}
                textAnchor="end"
                interval={0}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#94a3b8" }}
                axisLine={false}
                tickLine={false}
                label={{ value: "Heures", angle: -90, position: "insideLeft", fontSize: 10, fill: "#94a3b8" }}
              />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: "1px solid #f1f5f9", fontSize: 11, boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.05)" }}
                formatter={(v, name) => [`${v}h`, name]}
                cursor={{ fill: "#f8fafc" }}
              />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, paddingTop: 12 }} />
              <Bar dataKey="Maquette" fill="#93c5fd" radius={[3, 3, 0, 0]} maxBarSize={16} />
              <Bar dataKey="ADE" fill="#fca5a5" radius={[3, 3, 0, 0]} maxBarSize={16} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="border-slate-100 shadow-none overflow-hidden">
        <CardHeader className="py-3 px-5 border-b border-slate-50">
          <CardTitle className="text-sm font-semibold text-slate-700">Détail des écarts</CardTitle>
        </CardHeader>
        <div className="overflow-auto max-h-80">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 sticky top-0">
              <tr>
                {["Module", "Type", "Maquette", "ADE", "Écart %"].map((h, i) => (
                  <th key={h} className={`px-4 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-widest ${i >= 2 ? "text-right" : "text-left"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <tr key={i} className="border-t border-slate-50 hover:bg-slate-50/50 transition-colors">
                  <td className="px-4 py-2.5">
                    <code className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md font-mono">{r.module}</code>
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className="inline-block px-2 py-0.5 rounded text-white text-[10px] font-bold"
                      style={{ backgroundColor: TYPE_COLORS[r.type as keyof typeof TYPE_COLORS] || "#64748b" }}
                    >
                      {r.type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{r.maquette}h</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{r.ade}h</td>
                  <td className="px-4 py-2.5 text-right font-semibold" style={{ color: r.ecart > 50 ? "#ef4444" : r.ecart > 20 ? "#f59e0b" : "#64748b" }}>
                    {r.ecart === 100 ? "∞" : `${r.ecart}%`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
