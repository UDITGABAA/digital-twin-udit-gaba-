import { useState } from "react";
import { Scales } from "@phosphor-icons/react";
import type { Control, Portfolio } from "../types";

export function OptimizerPanel({ catalogue, run, onPick }: {
  catalogue: Control[]; run: (budget: number) => Promise<Portfolio>; onPick: (ids: string[]) => void;
}) {
  const [budget, setBudget] = useState(5);
  const [p, setP] = useState<Portfolio | null>(null);
  const [busy, setBusy] = useState(false);
  const name = (id: string) => catalogue.find((c) => c.id === id)?.name ?? id;

  const Col = ({ title, ids, cost, reduction, broken, good }: { title: string; ids: string[]; cost: number; reduction: number; broken: string[]; good: boolean }) => (
    <div className={`flex-1 rounded-lg border p-4 ${good ? "border-green-ink/40 bg-green-tint/40" : "border-line"}`}>
      <div className="label">{title}</div>
      <ul className="mt-2 space-y-1 text-sm text-ink">{ids.map((id) => <li key={id}>{name(id)}</li>)}{!ids.length && <li className="text-faint">nothing within budget</li>}</ul>
      <div className="mt-3 text-xs text-muted">risk −{reduction.toFixed(2)} of {p?.baseline_risk.toFixed(2)} · cost {cost}</div>
      <div className={`mt-1 text-xs ${broken.some((b) => b === "F1" || b === "F2") ? "font-medium text-red-ink" : broken.length ? "text-yellow-ink" : "text-green-ink"}`}>
        {broken.length ? `breaks ${broken.join(", ")}` : "breaks nothing"}
      </div>
      <button className="mt-3 text-xs font-medium text-accent-deep hover:underline" onClick={() => onPick(ids)}>evaluate this portfolio →</button>
    </div>
  );

  return (
    <section className="card p-6">
      <div className="flex flex-wrap items-center gap-3">
        <div className="label">Portfolio within budget</div>
        <input type="range" min={1} max={20} value={budget} onChange={(e) => setBudget(+e.target.value)} className="w-32 accent-accent" aria-label="budget" />
        <span className="text-sm text-ink">budget <b>{budget}</b></span>
        <button className="btn btn-ink" disabled={busy} onClick={async () => { setBusy(true); try { setP(await run(budget)); } finally { setBusy(false); } }}>
          <Scales weight="bold" />{busy ? "scoring…" : "optimise"}
        </button>
        {p && <span className="text-xs text-faint">{p.evaluated} portfolios scored, both adversaries</span>}
      </div>
      {p ? (
        <div className="mt-4 flex gap-3">
          <Col title="Rank by paths eliminated — the brief" ids={p.naive} cost={p.naive_cost} reduction={p.naive_risk_reduction} broken={p.naive_broken_flows} good={false} />
          <Col title="Constrained optimum — never break a P1/P2 flow" ids={p.constrained} cost={p.constrained_cost} reduction={p.constrained_risk_reduction} broken={p.constrained_broken_flows} good />
        </div>
      ) : (
        <p className="mt-2 max-w-[52ch] text-sm text-muted">Every subset of the catalogue within budget, scored with the same route policy the agent uses. Any portfolio that breaks a P1/P2 flow is discarded before ranking.</p>
      )}
    </section>
  );
}
