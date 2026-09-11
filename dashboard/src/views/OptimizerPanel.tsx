import { useState } from "react";
import type { Control, Portfolio } from "../types";

export function OptimizerPanel({ catalogue, run, onPick }: {
  catalogue: Control[]; run: (budget: number) => Promise<Portfolio>; onPick: (ids: string[]) => void;
}) {
  const [budget, setBudget] = useState(9);
  const [p, setP] = useState<Portfolio | null>(null);
  const [busy, setBusy] = useState(false);
  const name = (id: string) => catalogue.find((c) => c.id === id)?.name ?? id;

  const Col = ({ title, ids, cost, reduction, broken, tone }: { title: string; ids: string[]; cost: number; reduction: number; broken: string[]; tone: string }) => (
    <div className={`flex-1 rounded-lg border p-3 ${tone}`}>
      <div className="text-xs uppercase tracking-widest text-slate-400">{title}</div>
      <ul className="mt-1 text-sm">{ids.map((id) => <li key={id}>· {name(id)}</li>)}{!ids.length && <li className="text-slate-500">nothing within budget</li>}</ul>
      <div className="mt-2 text-xs text-slate-300">risk −{reduction.toFixed(2)} of {p?.baseline_risk.toFixed(2)} · cost {cost}</div>
      <div className={`text-xs ${broken.some((b) => b === "F1" || b === "F2") ? "text-red-300 font-semibold" : broken.length ? "text-amber-300" : "text-emerald-300"}`}>
        {broken.length ? `breaks ${broken.join(", ")}` : "breaks nothing"}
      </div>
      <button className="mt-2 text-xs text-sky-300 hover:underline" onClick={() => onPick(ids)}>evaluate this portfolio →</button>
    </div>
  );

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center gap-3">
        <div className="text-sm font-semibold">Portfolio within budget</div>
        <input type="range" min={1} max={20} value={budget} onChange={(e) => setBudget(+e.target.value)} className="w-40" />
        <span className="text-sm text-slate-300">budget {budget}</span>
        <button disabled={busy} onClick={async () => { setBusy(true); try { setP(await run(budget)); } finally { setBusy(false); } }}
          className="rounded bg-sky-600 px-3 py-1 text-sm font-semibold hover:bg-sky-500 disabled:opacity-50">
          {busy ? "scoring…" : "optimise"}
        </button>
        {p && <span className="text-xs text-slate-500">{p.evaluated} portfolios scored exhaustively, both agents</span>}
      </div>
      {p && (
        <div className="mt-3 flex gap-3">
          <Col title="Rank by paths eliminated (the brief)" ids={p.naive} cost={p.naive_cost} reduction={p.naive_risk_reduction} broken={p.naive_broken_flows} tone="border-slate-700" />
          <Col title="Constrained optimum (never break a P1/P2 flow)" ids={p.constrained} cost={p.constrained_cost} reduction={p.constrained_risk_reduction} broken={p.constrained_broken_flows} tone="border-emerald-700" />
        </div>
      )}
    </div>
  );
}
