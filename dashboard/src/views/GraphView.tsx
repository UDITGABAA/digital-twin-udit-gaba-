import { useMemo } from "react";
import { ReactFlow, Background, type Edge as FEdge, type Node as FNode, MarkerType } from "@xyflow/react";
import type { Blast, Graph, Route } from "../types";

const ZONES = ["external", "dmz", "corp", "mgmt", "prod"];
const ZONE_COLOR: Record<string, string> = { external: "#475569", dmz: "#b45309", corp: "#1d4ed8", mgmt: "#6d28d9", prod: "#047857" };

export function GraphView({ graph, route, blast, onSelectAsset }: {
  graph: Graph | null; route: Route | null; blast: Blast | null; onSelectAsset: (id: string) => void;
}) {
  const { nodes, edges } = useMemo(() => {
    if (!graph) return { nodes: [] as FNode[], edges: [] as FEdge[] };
    const onRoute = new Set(route?.map((e) => `${e.src}|${e.dst}|${e.technique}`));
    const routeNodes = new Set(route?.flatMap((e) => [e.src, e.dst]));
    const reach = new Set(blast?.reachable);
    const perZone: Record<string, number> = {};
    const nodes: FNode[] = graph.assets.map((a) => {
      const col = ZONES.indexOf(a.zone);
      const row = (perZone[a.zone] = (perZone[a.zone] ?? 0) + 1);
      const hot = routeNodes.has(a.id) || reach.has(a.id) || blast?.asset_id === a.id;
      return {
        id: a.id, position: { x: col * 220 + 20, y: row * 110 + 20 },
        data: { label: `${a.crown_jewel ? "👑 " : ""}${a.name}\n${a.id} · ${a.zone} · C${a.criticality}` },
        style: {
          background: ZONE_COLOR[a.zone] ?? "#334155", color: "white", borderRadius: 10, fontSize: 11, width: 180,
          whiteSpace: "pre-line", border: hot ? "3px solid #f59e0b" : a.crown_jewel ? "3px solid #fbbf24" : "1px solid #0f172a",
          opacity: route && !routeNodes.has(a.id) ? 0.45 : 1,
        },
      };
    });
    const edges: FEdge[] = [];
    graph.attack_edges.filter((e) => e.src !== e.dst).forEach((e) => {
      const key = `${e.src}|${e.dst}|${e.technique}`;
      const hot = onRoute.has(key);
      edges.push({
        id: "a:" + key, source: e.src, target: e.dst, animated: hot,
        label: `${e.technique} (${e.attck})${e.p_success < 0.5 ? ` p=${e.p_success.toFixed(2)}` : ""}`,
        labelStyle: { fill: hot ? "#fbbf24" : "#94a3b8", fontSize: 9 }, labelBgStyle: { fill: "#0f172a" },
        style: { stroke: hot ? "#f59e0b" : e.p_success < 0.5 ? "#475569" : "#ef4444", strokeWidth: hot ? 3 : 1.2, opacity: route && !hot ? 0.3 : 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: hot ? "#f59e0b" : "#ef4444" },
      });
    });
    graph.flows.forEach((f) => edges.push({
      id: "f:" + f.id, source: f.src, target: f.dst, label: `${f.id} ${f.protocol}/${f.port}`,
      labelStyle: { fill: "#34d399", fontSize: 9 }, labelBgStyle: { fill: "#0f172a" },
      style: { stroke: "#34d399", strokeWidth: 1.5, strokeDasharray: "6 4", opacity: route ? 0.35 : 0.9 },
    }));
    return { nodes, edges };
  }, [graph, route, blast]);

  return (
    <div className="h-[560px] rounded-xl border border-slate-800 bg-slate-950">
      <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}
        onNodeClick={(_, n) => onSelectAsset(n.id)} nodesDraggable={false} colorMode="dark"
        zoomOnScroll={false} panOnScroll={false} preventScrolling={false}>
        <Background color="#1e293b" />
      </ReactFlow>
      <div className="px-3 py-1 text-xs text-slate-500">
        red = attack edge (technique, ATT&CK id) · green dashed = legitimate flow · amber = highlighted route / blast radius · click an asset for blast radius
      </div>
    </div>
  );
}
