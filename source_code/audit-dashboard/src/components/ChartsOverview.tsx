"use client";

import { Scores, Anomaly } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip, Legend,
} from "recharts";

interface Props { scores: Scores; anomalies: Anomaly[]; }

const DIMS = [
  { subject: "Complétude",   key: "completude"  },
  { subject: "Exactitude",   key: "exactitude"  },
  { subject: "Séquencement", key: "conformite"  },
  { subject: "Unicité",      key: "unicite"     },
  { subject: "Cohérence",    key: "coherence"   },
] as const;

const CRIT_COLORS: Record<string, string> = {
  bloquant: "#ef4444",
  majeur:   "#f59e0b",
  mineur:   "#60a5fa",
};

const CRIT_LABELS: Record<string, string> = {
  bloquant: "Bloquant",
  majeur:   "Majeur",
  mineur:   "Mineur",
};

export default function ChartsOverview({ scores, anomalies }: Props) {
  const radarData = DIMS.map(d => ({ subject: d.subject, value: scores[d.key], fullMark: 100 }));

  const counts: Record<string, number> = {};
  anomalies.forEach(a => { counts[a.criticite] = (counts[a.criticite] || 0) + 1; });
  const pieData = Object.entries(counts).map(([k, v]) => ({ name: CRIT_LABELS[k] || k, value: v, key: k }));

  return (
    <div className="grid grid-cols-2 gap-4">
      <Card className="border-slate-100 shadow-none">
        <CardHeader className="pb-2 pt-5 px-6">
          <CardTitle className="text-sm font-semibold text-slate-700">Scores par dimension qualité</CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6">
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
              <PolarGrid stroke="#f1f5f9" />
              <PolarAngleAxis
                dataKey="subject"
                tick={{ fontSize: 11, fill: "#94a3b8", fontWeight: 500 }}
              />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9, fill: "#cbd5e1" }} />
              <Radar
                name="Score"
                dataKey="value"
                stroke="#0f172a"
                fill="#0f172a"
                fillOpacity={0.08}
                strokeWidth={2}
                dot={{ fill: "#0f172a", r: 3, strokeWidth: 0 }}
              />
              <Tooltip
                formatter={(v) => [`${Number(v).toFixed(0)}/100`, "Score"]}
                contentStyle={{ borderRadius: 8, border: "1px solid #f1f5f9", fontSize: 11, boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.05)" }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="border-slate-100 shadow-none">
        <CardHeader className="pb-2 pt-5 px-6">
          <CardTitle className="text-sm font-semibold text-slate-700">Répartition des anomalies</CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-6">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={75}
                outerRadius={115}
                paddingAngle={4}
                dataKey="value"
                label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                labelLine={{ stroke: "#cbd5e1", strokeWidth: 1 }}
              >
                {pieData.map(entry => (
                  <Cell key={entry.key} fill={CRIT_COLORS[entry.key] || "#94a3b8"} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v, name) => [v, name]}
                contentStyle={{ borderRadius: 8, border: "1px solid #f1f5f9", fontSize: 11, boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.05)" }}
              />
              <Legend
                iconType="circle"
                iconSize={8}
                formatter={(value) => <span style={{ fontSize: 11, color: "#64748b" }}>{value}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
