import { useState } from "react";
import { Scale } from "lucide-react";
import type { Control, Portfolio } from "../types";

export function OptimizerPanel({ catalogue, run, onPick }: {
  catalogue: Control[]; run: (budget: number) => Promise<Portfolio>; onPick: (ids: string[]) => void;
}) {
  const [budget, setBudget] = useState(5);
  const [p, setP] = useState<Portfolio | null>(null);
  const [busy, setBusy] = useState(false);
  const name = (id: string) => catalogue.find((c) => c.id === id)?.name ?? id;

  const Col = ({ title, ids, cost, reduction, broken, good }: { title: string; ids: string[]; cost: number; reduction: number; broken: string[]; good: boolean }) => (
    <div className={`panel-raised flex-1 p-3 ${good ? "border-deploy/50" : ""}`}>
      <div className="label">{title}</div>
      <ul className="mt-1.5 space-y-0.5 text-sm">{ids.map((id) => <li key={id}>{name(id)}</li>)}{!ids.length && <li className="text-fg-faint">nothing within budget</li>}</ul>
      <div className="mt-2 text-xs text-fg-muted">risk −{reduction.toFixed(2)} of {p?.baseline_risk.toFixed(2)} · cost {cost}</div>
      <div className={`text-xs ${broken.some((b) => b === "F1" || b === "F2") ? "font-semibold text-block" : broken.length ? "text-review" : "text-deploy"}`}>
        {broken.length ? `breaks ${broken.join(", ")}` : "breaks nothing"}
      </div>
      <button className="mt-2 text-xs text-signal hover:underline" onClick={() => onPick(ids)}>evaluate this portfolio →</button>
    </div>
  );

  return (
    <div className="panel p-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="label">Portfolio within budget</div>
        <input type="range" min={1} max={20} value={budget} onChange={(e) => setBudget(+e.target.value)} className="w-36 accent-signal" aria-label="budget" />
        <span className="text-sm">budget <b>{budget}</b></span>
        <button className="btn btn-primary" disabled={busy} onClick={async () => { setBusy(true); try { setP(await run(budget)); } finally { setBusy(false); } }}>
          <Scale className="h-3.5 w-3.5" />{busy ? "scoring…" : "optimise"}
        </button>
        {p && <span className="text-xs text-fg-faint">{p.evaluated} portfolios scored exhaustively, both adversaries</span>}
      </div>
      {p ? (
        <div className="mt-3 flex gap-3">
          <Col title="Rank by paths eliminated (the brief)" ids={p.naive} cost={p.naive_cost} reduction={p.naive_risk_reduction} broken={p.naive_broken_flows} good={false} />
          <Col title="Constrained optimum — never break a P1/P2 flow" ids={p.constrained} cost={p.constrained_cost} reduction={p.constrained_risk_reduction} broken={p.constrained_broken_flows} good />
        </div>
      ) : (
        <div className="mt-2 text-sm text-fg-muted">Every subset of the catalogue within budget, scored with the same route policy the agent uses; any portfolio that breaks a P1/P2 flow is discarded.</div>
      )}
    </div>
  );
}
