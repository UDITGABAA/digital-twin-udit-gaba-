import { useEffect, useMemo, useRef, useState } from "react";
import { ReactFlow, Background, Handle, Position, MarkerType, type Edge as FEdge, type Node as FNode, type NodeProps } from "@xyflow/react";
import { Crown, Database, Globe, HardDrives, Desktop, Cpu, CloudArrowUp } from "@phosphor-icons/react";
import type { Asset, Blast, Graph, Route } from "../types";

const ZONE_ORDER = ["external", "dmz", "clinical", "corp", "mgmt", "prod"];
const zonesOf = (assets: Asset[]) => {
  const seen = Array.from(new Set(assets.map((a) => a.zone)));
  return [...ZONE_ORDER.filter((z) => seen.includes(z)), ...seen.filter((z) => !ZONE_ORDER.includes(z))];
};
const NODE_W = 204;
const STAGE_H = 600;

export interface ReplayState {
  breached: Set<string>;       // assets the attacker holds in the current trial
  traversed: Set<string>;      // edge keys succeeded so far
  active: string | null;       // node currently being attacked
  activeEdge: string | null;   // edge key being attempted
  failedEdge: string | null;
  detected: boolean;
}

const edgeKey = (src: string, dst: string, technique: string) => `${src}|${dst}|${technique}`;

function Icon({ kind }: { kind: string }) {
  const p = { className: "h-3.5 w-3.5 shrink-0 text-muted", weight: "bold" as const };
  switch (kind) {
    case "database": return <Database {...p} />;
    case "internet": return <Globe {...p} />;
    case "workstation": return <Desktop {...p} />;
    case "share": return <HardDrives {...p} />;
    case "cloud_role": return <CloudArrowUp {...p} />;
    default: return <Cpu {...p} />;
  }
}

function AssetNode({ data }: NodeProps) {
  const a = data.asset as Asset;
  const cls = data.className as string;
  return (
    <div className={`rf-node ${cls}`}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div className="name">
        <Icon kind={a.kind} />
        <span className="truncate">{a.name}</span>
        {a.crown_jewel && <Crown className="ml-auto h-3.5 w-3.5 shrink-0 text-accent" weight="fill" />}
      </div>
      <div className="meta">{a.id} · C{a.criticality}</div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { asset: AssetNode };

export function Stage({ graph, route, blast, replay, startZones, onSelectAsset }: {
  graph: Graph | null; route: Route | null; blast: Blast | null; replay: ReplayState | null;
  startZones: string[]; onSelectAsset: (id: string) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(1100);
  useEffect(() => {
    if (!box.current) return;
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width));
    ro.observe(box.current);
    return () => ro.disconnect();
  }, []);

  const { nodes, edges, zones } = useMemo(() => {
    if (!graph) return { nodes: [] as FNode[], edges: [] as FEdge[], zones: [] as string[] };
    const ZONES = zonesOf(graph.assets);
    const laneW = width / ZONES.length;
    const counts: Record<string, number> = {};
    graph.assets.forEach((a) => { counts[a.zone] = (counts[a.zone] ?? 0) + 1; });
    const onRoute = new Set(route?.map((e) => edgeKey(e.src, e.dst, e.technique)));
    const routeNodes = new Set(route?.flatMap((e) => [e.src, e.dst]));
    const reach = new Set(blast?.reachable);
    const perZone: Record<string, number> = {};
    const focus = !!route || !!replay;

    const nodes: FNode[] = graph.assets.map((a) => {
      const col = ZONES.indexOf(a.zone);
      const row = (perZone[a.zone] = (perZone[a.zone] ?? 0) + 1);
      const n = counts[a.zone] ?? 1;
      const y = 40 + ((STAGE_H - 80) / (n + 1)) * row - 24;
      const x = col * laneW + (laneW - NODE_W) / 2;
      const cls = [
        a.crown_jewel ? "crown" : "",
        routeNodes.has(a.id) ? "on-route" : "",
        replay?.breached.has(a.id) ? "breached" : "",
        replay?.active === a.id ? "active" : "",
        reach.has(a.id) || blast?.asset_id === a.id ? "reach" : "",
        !replay && !route && startZones.includes(a.zone) ? "start" : "",
        focus && !routeNodes.has(a.id) && !replay?.breached.has(a.id) && replay?.active !== a.id ? "dim" : "",
      ].join(" ");
      return { id: a.id, type: "asset", position: { x, y }, data: { asset: a, className: cls }, draggable: false };
    });

    const edges: FEdge[] = [];
    graph.attack_edges.filter((e) => e.src !== e.dst).forEach((e) => {
      const k = edgeKey(e.src, e.dst, e.technique);
      const hot = onRoute.has(k) || replay?.traversed.has(k);
      const attempting = replay?.activeEdge === k;
      const failed = replay?.failedEdge === k;
      const color = failed ? "var(--color-yellow-ink)" : hot || attempting ? "var(--color-accent)" : e.p_success < 0.5 ? "var(--color-line-strong)" : "var(--color-accent-soft)";
      edges.push({
        id: "a:" + k, source: e.src, target: e.dst, animated: !!(hot || attempting),
        label: `${e.technique} · ${e.attck}${e.p_success < 0.5 ? ` · p ${e.p_success.toFixed(2)}` : ""}`,
        labelStyle: { fill: hot || attempting ? "var(--color-accent-deep)" : "var(--color-faint)", fontSize: 9.5, fontWeight: 500 },
        labelBgStyle: { fill: "var(--color-surface)", fillOpacity: 0.95 }, labelBgPadding: [4, 2], labelBgBorderRadius: 4,
        style: { stroke: color, strokeWidth: hot || attempting ? 2.5 : 1.3, opacity: focus && !hot && !attempting && !failed ? 0.28 : 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color, width: 14, height: 14 },
      });
    });
    graph.flows.forEach((f) => edges.push({
      id: "f:" + f.id, source: f.src, target: f.dst, label: `${f.id} · ${f.protocol}/${f.port}`,
      labelStyle: { fill: "var(--color-blue-ink)", fontSize: 9.5 }, labelBgStyle: { fill: "var(--color-surface)", fillOpacity: 0.95 },
      style: { stroke: "var(--color-blue-ink)", strokeWidth: 1.3, strokeDasharray: "5 4", opacity: focus ? 0.25 : 0.7 },
    }));
    return { nodes, edges, zones: ZONES };
  }, [graph, route, blast, replay, startZones, width]);

  return (
    <section ref={box} className="card relative overflow-hidden" style={{ height: STAGE_H }}>
      <div className="pointer-events-none absolute inset-0 z-10">
        {zones.map((z, i) => (
          <div key={z} className="lane" style={{ left: `${(i / zones.length) * 100}%`, width: `${100 / zones.length}%` }}>
            <span className="lane-label">{z}</span>
          </div>
        ))}
      </div>
      <ReactFlow key={width} nodes={nodes} edges={edges} nodeTypes={nodeTypes} defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        onNodeClick={(_, n) => onSelectAsset(n.id)} nodesDraggable={false} colorMode="light" minZoom={1} maxZoom={1}
        zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} panOnDrag={false} panOnScroll={false} preventScrolling={false} proOptions={{ hideAttribution: true }}>
        <Background color="var(--color-line)" gap={24} size={1.2} />
      </ReactFlow>
      <div className="pointer-events-none absolute bottom-3 left-4 z-10 flex gap-5 text-[11px] text-faint">
        <span><i className="mr-1.5 inline-block h-[3px] w-4 rounded-sm align-middle" style={{ background: "var(--color-accent)" }} />attack edge · technique · ATT&CK id</span>
        <span><i className="mr-1.5 inline-block h-[3px] w-4 rounded-sm align-middle" style={{ background: "var(--color-blue-ink)" }} />legitimate flow</span>
        <span><i className="mr-1.5 inline-block h-[3px] w-4 rounded-sm align-middle" style={{ background: "var(--color-yellow-ink)" }} />blast radius</span>
        <span>click an asset for its blast radius</span>
      </div>
    </section>
  );
}

export { edgeKey };
