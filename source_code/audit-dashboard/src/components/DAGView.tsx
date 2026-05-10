"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { Dependance } from "@/types";
import { Card, CardContent } from "@/components/ui/card";

interface Props { dependances: Dependance[]; }

const TYPE_COLOR: Record<string, { bg: string; border: string; text: string }> = {
  CM: { bg: "#eff6ff", border: "#2563eb", text: "#1d4ed8" },
  TD: { bg: "#f5f3ff", border: "#7c3aed", text: "#6d28d9" },
  TP: { bg: "#ecfdf5", border: "#059669", text: "#047857" },
};

function isInversion(typeA: string, typeB: string): boolean {
  return (typeA === "TP" && ["CM", "TD"].includes(typeB)) || (typeA === "TD" && typeB === "CM");
}

function buildGraph(deps: Dependance[], module: string): { nodes: Node[]; edges: Edge[] } {
  const filtered = deps.filter(
    d => d.module_precedent === module && d.module_suivant === module
  );

  const nodeSet = new Set<string>();
  filtered.forEach(d => {
    nodeSet.add(`${d.type_precedent.trim()}_${d.numero_precedent}`);
    nodeSet.add(`${d.type_suivant.trim()}_${d.numero_suivant}`);
  });

  const nodeArr = [...nodeSet];
  const cols: Record<string, number> = {};
  const rows: Record<string, number> = {};
  const typeGroups: Record<string, string[]> = { CM: [], TD: [], TP: [] };
  nodeArr.forEach(n => {
    const t = n.split("_")[0];
    (typeGroups[t] || (typeGroups["OTHER"] = [])).push(n);
  });

  let col = 0;
  Object.entries(typeGroups).forEach(([type, nodes]) => {
    if (nodes.length === 0) return;
    nodes.sort().forEach((n, ri) => {
      cols[n] = col;
      rows[n] = ri;
    });
    col++;
  });

  const nodes: Node[] = nodeArr.map(n => {
    const type = n.split("_")[0];
    const style = TYPE_COLOR[type] || { bg: "#f8fafc", border: "#94a3b8", text: "#334155" };
    return {
      id: n,
      data: { label: n },
      position: { x: (cols[n] || 0) * 180, y: (rows[n] || 0) * 90 },
      style: {
        background: style.bg,
        border: `2px solid ${style.border}`,
        color: style.text,
        borderRadius: 10,
        padding: "8px 14px",
        fontWeight: 700,
        fontSize: 12,
        boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
        minWidth: 80,
        textAlign: "center",
      },
    };
  });

  const edges: Edge[] = filtered.map((d, i) => {
    const from = `${d.type_precedent.trim()}_${d.numero_precedent}`;
    const to   = `${d.type_suivant.trim()}_${d.numero_suivant}`;
    const inv  = isInversion(d.type_precedent.trim(), d.type_suivant.trim());
    return {
      id: `e-${i}`,
      source: from,
      target: to,
      animated: inv,
      style: { stroke: inv ? "#ef4444" : "#94a3b8", strokeWidth: inv ? 2.5 : 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: inv ? "#ef4444" : "#94a3b8" },
      label: inv ? "⚠️ Inversion" : undefined,
      labelStyle: { fontSize: 10, fill: "#ef4444", fontWeight: 600 },
    };
  });

  return { nodes, edges };
}

export default function DAGView({ dependances }: Props) {
  const modules = useMemo(() =>
    [...new Set(dependances.map(d => d.module_precedent))].sort(),
    [dependances]
  );

  const [selected, setSelected] = useState(
    modules.includes("MATH531_IDU") ? "MATH531_IDU" : modules[0] || ""
  );

  const { nodes: initNodes, edges: initEdges } = useMemo(
    () => (selected ? buildGraph(dependances, selected) : { nodes: [], edges: [] }),
    [dependances, selected]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initEdges);

  useEffect(() => {
    const { nodes: n, edges: e } = buildGraph(dependances, selected);
    setNodes(n);
    setEdges(e);
  }, [selected, dependances, setNodes, setEdges]);

  const inversions = useMemo(() =>
    dependances
      .filter(d => d.module_precedent === selected && d.module_suivant === selected)
      .filter(d => isInversion(d.type_precedent.trim(), d.type_suivant.trim())),
    [dependances, selected]
  );

  const totalEdges = useMemo(() =>
    dependances.filter(d => d.module_precedent === selected && d.module_suivant === selected).length,
    [dependances, selected]
  );

  return (
    <div className="space-y-5">
      {/* Controls */}
      <Card className="border-slate-100 shadow-none">
      <CardContent className="p-5">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5 block">Module</label>
            <select
              value={selected}
              onChange={e => setSelected(e.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[200px]"
            >
              {modules.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>
          {/* Stats */}
          <div className="flex gap-4 ml-auto">
            <div className="text-center">
              <p className="text-xl font-bold text-slate-700">{totalEdges}</p>
              <p className="text-xs text-slate-400">Relations</p>
            </div>
            <div className="text-center">
              <p className={`text-xl font-bold ${inversions.length > 0 ? "text-red-500" : "text-emerald-600"}`}>
                {inversions.length}
              </p>
              <p className="text-xs text-slate-400">Inversions</p>
            </div>
            <div className="text-center">
              <p className={`text-xl font-bold ${inversions.length === 0 ? "text-emerald-600" : "text-red-500"}`}>
                {inversions.length === 0 ? "✓ Sain" : "✗ Alerte"}
              </p>
              <p className="text-xs text-slate-400">Statut</p>
            </div>
          </div>
        </div>
      </CardContent>
      </Card>

      {/* Legend */}
      <div className="flex gap-4 flex-wrap">
        {Object.entries(TYPE_COLOR).map(([type, s]) => (
          <div key={type} className="flex items-center gap-2 bg-white rounded-lg border border-slate-100 px-3 py-2">
            <div className="h-3 w-3 rounded" style={{ background: s.bg, border: `2px solid ${s.border}` }} />
            <span className="text-xs font-semibold" style={{ color: s.text }}>{type}</span>
          </div>
        ))}
        <div className="flex items-center gap-2 bg-white rounded-lg border border-red-100 px-3 py-2">
          <div className="h-0.5 w-6 bg-red-500 rounded" />
          <span className="text-xs font-semibold text-red-600">Inversion logique</span>
        </div>
      </div>

      {/* Flow Graph */}
      <div className="bg-white rounded-xl border border-slate-100 overflow-hidden" style={{ height: 480 }}>
        {nodes.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-3 text-slate-400">
            <span className="text-4xl">🕸️</span>
            <p className="text-sm">Aucune dépendance intra-module trouvée pour <strong>{selected}</strong>.</p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            attributionPosition="bottom-left"
          >
            <Background color="#f1f5f9" gap={20} />
            <Controls showInteractive={false} />
            <MiniMap
              nodeColor={n => {
                const type = (n.id as string).split("_")[0];
                return TYPE_COLOR[type]?.border || "#94a3b8";
              }}
              maskColor="rgba(248,250,252,0.8)"
            />
          </ReactFlow>
        )}
      </div>

      {/* Inversions list */}
      {inversions.length > 0 && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-5">
          <h4 className="text-sm font-semibold text-red-700 mb-3">⚠️ Inversions logiques détectées</h4>
          <div className="space-y-2">
            {inversions.map((d, i) => (
              <div key={i} className="flex items-center gap-3 text-xs text-red-600">
                <code className="bg-red-100 px-2 py-0.5 rounded font-mono">{d.type_precedent}_{d.numero_precedent}</code>
                <span>→</span>
                <code className="bg-red-100 px-2 py-0.5 rounded font-mono">{d.type_suivant}_{d.numero_suivant}</code>
                <span className="text-red-400">Ordre illogique (attendu : CM → TD → TP)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
