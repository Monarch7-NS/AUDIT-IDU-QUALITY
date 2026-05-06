"use client";

import { useState, useMemo } from "react";
import { Anomaly } from "@/types";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

interface Props { anomalies: Anomaly[]; }

const CRIT_STYLE: Record<string, string> = {
  bloquant: "bg-red-50 text-red-700 border-red-200 hover:bg-red-100",
  majeur:   "bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100",
  mineur:   "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100",
};

const PRIORITY: Record<string, number> = { bloquant: 1, majeur: 2, mineur: 3 };

export default function AnomalyTable({ anomalies }: Props) {
  const dims = useMemo(() => [...new Set(anomalies.map(a => a.dimension))].sort(), [anomalies]);
  const [dimFilter, setDimFilter] = useState<string[]>(dims);
  const [critFilter, setCritFilter] = useState<string[]>(["bloquant", "majeur", "mineur"]);
  const [search, setSearch] = useState("");

  const filtered = useMemo(() =>
    anomalies
      .filter(a => dimFilter.includes(a.dimension))
      .filter(a => critFilter.includes(a.criticite))
      .filter(a => !search || a.description.toLowerCase().includes(search.toLowerCase()) || a.code_module.toLowerCase().includes(search.toLowerCase()))
      .sort((a, b) => (PRIORITY[a.criticite] || 9) - (PRIORITY[b.criticite] || 9)),
    [anomalies, dimFilter, critFilter, search]
  );

  const toggleDim = (d: string) =>
    setDimFilter(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);
  const toggleCrit = (c: string) =>
    setCritFilter(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]);

  return (
    <div className="space-y-4">
      <Card className="border-slate-100 shadow-none">
        <CardContent className="p-5">
          <div className="flex flex-wrap gap-6 items-start">
            <div className="flex-1 min-w-[220px]">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Rechercher</p>
              <Input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Module ou description…"
                className="border-slate-200 text-sm h-9 rounded-lg focus-visible:ring-1 focus-visible:ring-slate-900"
              />
            </div>
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Criticité</p>
              <div className="flex gap-2">
                {(["bloquant", "majeur", "mineur"] as const).map(c => (
                  <button
                    key={c}
                    onClick={() => toggleCrit(c)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                      critFilter.includes(c) ? CRIT_STYLE[c] : "bg-slate-50 text-slate-400 border-slate-100"
                    }`}
                  >
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest mb-2">Dimension</p>
              <div className="flex flex-wrap gap-2">
                {dims.map(d => (
                  <button
                    key={d}
                    onClick={() => toggleDim(d)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border capitalize ${
                      dimFilter.includes(d)
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white text-slate-400 border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-100 shadow-none overflow-hidden">
        <CardHeader className="py-3 px-5 border-b border-slate-50">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold text-slate-700">Journal des anomalies</CardTitle>
            <span className="text-[11px] text-slate-400">
              <span className="font-semibold text-slate-600">{filtered.length}</span> / {anomalies.length} anomalie(s)
            </span>
          </div>
        </CardHeader>
        <div className="overflow-auto max-h-[540px]">
          <Table>
            <TableHeader className="bg-slate-50/80 sticky top-0">
              <TableRow className="border-slate-100 hover:bg-transparent">
                <TableHead className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest w-28">Criticité</TableHead>
                <TableHead className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest w-32">Dimension</TableHead>
                <TableHead className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest w-36">Module</TableHead>
                <TableHead className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest">Description</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((a, i) => (
                <TableRow key={i} className="border-slate-50 hover:bg-slate-50/50">
                  <TableCell className="py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-[11px] font-semibold border ${CRIT_STYLE[a.criticite]}`}>
                      {a.criticite.charAt(0).toUpperCase() + a.criticite.slice(1)}
                    </span>
                  </TableCell>
                  <TableCell className="text-slate-500 text-xs capitalize py-3">{a.dimension}</TableCell>
                  <TableCell className="py-3">
                    <code className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md font-mono">{a.code_module}</code>
                  </TableCell>
                  <TableCell className="text-slate-600 text-xs leading-relaxed py-3">{a.description}</TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-16 text-center text-sm text-slate-400">
                    Aucune anomalie ne correspond aux filtres sélectionnés.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  );
}
