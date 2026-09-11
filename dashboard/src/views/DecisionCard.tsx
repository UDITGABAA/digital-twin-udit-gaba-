import type { ChangeVerdict, Control, Route } from "../types";

const VERDICT = {
  blocked: { label: "BLOCK", cls: "bg-red-600 text-white" },
  review: { label: "REVIEW", cls: "bg-amber-500 text-black" },
  deploy: { label: "DEPLOY", cls: "bg-emerald-500 text-black" },
};

export const routeText = (r: Route) =>
  [r[0]?.src, ...r.map((e) => e.dst)].filter((v, i, a) => i === 0 || v !== a[i - 1]).join(" → ");

const pct = (v: number | null, eliminated: boolean) =>
  eliminated ? "route eliminated" : v === null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(0)}%`;

export function DecisionCard({ verdict, catalogue, onPick, onHighlight }: {
  verdict: ChangeVerdict | null; catalogue: Control[];
  onPick: (ids: string[]) => void; onHighlight: (r: Route | null) => void;
}) {
  if (!verdict) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
        Pick one or more controls on the left to see the change-board verdict.
      </div>
    );
  }
  const name = (id: string) => catalogue.find((c) => c.id === id)?.name ?? id;
  const v = VERDICT[verdict.recommendation];
  const d = verdict.delta;
  const o = verdict.outcomes[0];
  const route = d.substituted_paths[0] ?? verdict.after.routes[0]?.route ?? null;
  const routeLabel = d.substituted_paths[0] ? "Attacker's NEW route" : "Attacker's best remaining route";
  const critical = verdict.broken_flows.filter((f) => f.criticality >= 4);

  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-400">Proposed change</div>
          <div className="text-xl font-semibold">{verdict.control_ids.map(name).join(" + ")}</div>
          <div className="text-sm text-slate-400">cost {verdict.cost} · agent {o.agent_id} · {verdict.before.n} trials, seed {verdict.before.seed}</div>
        </div>
        <div className={`rounded-lg px-5 py-3 text-2xl font-black tracking-wider ${v.cls}`}>{v.label}</div>
      </div>

      <dl className="mt-5 grid grid-cols-[9rem_1fr] gap-y-3 text-sm">
        <dt className="text-slate-400">Security</dt>
        <dd>
          <span className={`text-lg font-semibold ${d.route_eliminated || (d.effort_increase_pct ?? 0) >= 5 ? "text-emerald-300" : "text-amber-300"}`}>{pct(d.effort_increase_pct, d.route_eliminated)}</span>
          <span className="text-slate-400"> modelled attacker effort</span>
          <span className="mx-2 text-slate-600">·</span>
          p(success) {verdict.before.p_success.toFixed(2)} → <b>{verdict.after.p_success.toFixed(2)}</b>
          <span className="mx-2 text-slate-600">·</span>
          <span className="text-slate-400">critical paths {o.naive_before} → {o.naive_after} (industry metric, −{d.naive_path_reduction_pct.toFixed(0)}%)</span>
        </dd>

        <dt className="text-slate-400">{routeLabel}</dt>
        <dd>
          {route ? (
            <button className="text-left font-mono text-sky-300 hover:underline" onClick={() => onHighlight(route)}>
              {routeText(route)}
            </button>
          ) : <span className="text-slate-500">none viable in {verdict.after.n} trials</span>}
        </dd>

        <dt className="text-slate-400">Business</dt>
        <dd>
          {verdict.broken_flows.length === 0 ? (
            <span className="text-emerald-300">no legitimate flow affected</span>
          ) : verdict.broken_flows.map((f) => (
            <div key={f.id} className={f.criticality >= 4 ? "text-red-300 font-semibold" : "text-amber-300"}>
              BREAKS {f.name} — {f.src} → {f.dst} {f.protocol}/{f.port} as {f.identity_id} (P{6 - f.criticality})
            </div>
          ))}
        </dd>

        <dt className="text-slate-400">Confidence</dt>
        <dd>
          <b>{verdict.confidence.level}</b> <span className="text-slate-500">({verdict.confidence.score.toFixed(2)})</span>
          {verdict.confidence.undetermined && <span className="ml-2 text-red-300">cannot be determined — an assumed element decides this</span>}
          {verdict.confidence.unknowns.slice(0, 3).map((u) => <div key={u} className="text-xs text-slate-400">· {u}</div>)}
        </dd>

        <dt className="text-slate-400">Why</dt>
        <dd className="text-slate-300">{verdict.reasons.join("; ")}</dd>
      </dl>

      {verdict.alternatives.length > 0 && (
        <div className="mt-5 border-t border-slate-800 pt-4">
          <div className="text-xs uppercase tracking-widest text-slate-400">{critical.length ? "Safer option" : "Also consider"}</div>
          {verdict.alternatives.map((a) => (
            <button key={a.control_ids.join()} onClick={() => onPick(a.control_ids)}
              className="mt-2 flex w-full items-center justify-between rounded-lg border border-slate-700 bg-slate-800/60 px-4 py-2 text-left text-sm hover:border-sky-500">
              <span>{a.control_ids.map(name).join(" + ")}</span>
              <span className="text-slate-300">
                {pct(a.effort_increase_pct, a.route_eliminated)} effort · Δp {a.p_success_delta.toFixed(2)} · cost {a.cost} ·{" "}
                {a.broken_flows.length ? `breaks ${a.broken_flows.join(", ")}` : "no flows affected"} ·{" "}
                <b className={a.recommendation === "deploy" ? "text-emerald-300" : "text-amber-300"}>{a.recommendation.toUpperCase()}</b>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
