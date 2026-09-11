import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis, ResponsiveContainer } from "recharts";
import type { Result } from "../types";

function histogram(before: Result, after: Result) {
  const all = [...before.effort_distribution, ...after.effort_distribution];
  if (!all.length) return [];
  const lo = Math.floor(Math.min(...all)), hi = Math.ceil(Math.max(...all));
  const step = Math.max(1, Math.ceil((hi - lo) / 14));
  const bins: { bucket: string; before: number; after: number }[] = [];
  for (let x = lo; x <= hi; x += step) bins.push({ bucket: `${x}–${x + step}`, before: 0, after: 0 });
  const put = (v: number, key: "before" | "after") => { const i = Math.min(bins.length - 1, Math.floor((v - lo) / step)); bins[i][key] += 1; };
  before.effort_distribution.forEach((v) => put(v, "before"));
  after.effort_distribution.forEach((v) => put(v, "after"));
  return bins;
}

export function EffortChart({ before, after }: { before: Result | null; after: Result | null }) {
  if (!before || !after) return null;
  const data = histogram(before, after);
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="mb-1 text-sm font-semibold">Attacker effort over {before.n} successful-trial samples — before vs after</div>
      <div className="mb-3 text-xs text-slate-400">
        Path count says how many routes exist; this says how much the routes the attacker actually picks cost.
        mean {before.mean_effort?.toFixed(1) ?? "—"} → {after.mean_effort?.toFixed(1) ?? "—"} · p90 {before.p90_effort?.toFixed(1) ?? "—"} → {after.p90_effort?.toFixed(1) ?? "—"} ·
        successes {before.effort_distribution.length} → {after.effort_distribution.length}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} barGap={-14}>
          <CartesianGrid stroke="#1e293b" />
          <XAxis dataKey="bucket" tick={{ fill: "#94a3b8", fontSize: 10 }} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} />
          <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
          <Legend />
          <Bar dataKey="before" fill="#ef4444" fillOpacity={0.55} name="before (successful trials)" />
          <Bar dataKey="after" fill="#22c55e" fillOpacity={0.7} name="after" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
