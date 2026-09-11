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
  if (!before || !after) {
    return (
      <div className="panel p-4 text-sm text-fg-muted">
        <div className="label">Attacker effort</div>
        <div className="mt-2">Propose a change to compare the before/after effort distributions — path count says how many routes exist; this says what the routes the attacker actually picks cost.</div>
      </div>
    );
  }
  const data = histogram(before, after);
  return (
    <div className="panel p-4">
      <div className="label">Attacker effort per successful trial</div>
      <div className="mt-1 text-sm text-fg-muted">
        mean {before.mean_effort?.toFixed(1) ?? "—"} → <b className="text-fg">{after.mean_effort?.toFixed(1) ?? "—"}</b> · p90 {before.p90_effort?.toFixed(1) ?? "—"} → <b className="text-fg">{after.p90_effort?.toFixed(1) ?? "—"}</b> · successes {before.effort_distribution.length} → <b className="text-fg">{after.effort_distribution.length}</b> of {before.n}
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} barGap={-12} margin={{ top: 12, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="var(--color-ink-700)" vertical={false} />
          <XAxis dataKey="bucket" tick={{ fill: "var(--color-fg-faint)", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "var(--color-fg-faint)", fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: "rgba(126,166,255,0.06)" }} contentStyle={{ background: "var(--color-ink-850)", border: "1px solid var(--color-ink-700)", borderRadius: 8, fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="before" fill="var(--color-ember)" fillOpacity={0.5} name="before" radius={[3, 3, 0, 0]} />
          <Bar dataKey="after" fill="var(--color-verdigris)" fillOpacity={0.75} name="after" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
