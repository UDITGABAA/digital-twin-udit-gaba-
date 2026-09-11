import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis, ResponsiveContainer } from "recharts";
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
      <section className="card p-6">
        <div className="label">Attacker effort</div>
        <p className="mt-2 max-w-[44ch] text-sm text-muted">Path count says how many routes exist. This says what the routes the attacker actually picks cost — before and after the change.</p>
      </section>
    );
  }
  const data = histogram(before, after);
  return (
    <section className="card p-6">
      <div className="flex items-baseline justify-between gap-4">
        <div className="label">Attacker effort per successful trial</div>
        <div className="flex gap-4 text-[11px] text-muted">
          <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: "var(--color-line-strong)" }} />before</span>
          <span><i className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: "var(--color-accent)" }} />after</span>
        </div>
      </div>
      <div className="mt-1 text-sm text-muted">
        mean {before.mean_effort?.toFixed(1) ?? "—"} → <b className="text-ink">{after.mean_effort?.toFixed(1) ?? "—"}</b> · p90 {before.p90_effort?.toFixed(1) ?? "—"} → <b className="text-ink">{after.p90_effort?.toFixed(1) ?? "—"}</b> · successes {before.effort_distribution.length} → <b className="text-ink">{after.effort_distribution.length}</b> of {before.n}
      </div>
      <ResponsiveContainer width="100%" height={190}>
        <BarChart data={data} barGap={-10} margin={{ top: 14, right: 4, left: -22, bottom: 0 }}>
          <CartesianGrid stroke="var(--color-line)" vertical={false} />
          <XAxis dataKey="bucket" tick={{ fill: "var(--color-faint)", fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "var(--color-faint)", fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: "var(--color-raised)" }} contentStyle={{ background: "var(--color-surface)", border: "1px solid var(--color-line)", borderRadius: 8, fontSize: 12 }} />
          <Bar dataKey="before" fill="var(--color-line-strong)" name="before" radius={[2, 2, 0, 0]} />
          <Bar dataKey="after" fill="var(--color-accent)" name="after" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </section>
  );
}
