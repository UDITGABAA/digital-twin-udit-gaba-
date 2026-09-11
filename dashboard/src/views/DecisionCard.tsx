import { motion, AnimatePresence } from "motion/react";
import { ShieldCheck, ShieldAlert, ShieldQuestion, Route as RouteIcon, ArrowRight } from "lucide-react";
import type { ChangeVerdict, Control, Route } from "../types";

const VERDICT = {
  blocked: { label: "BLOCK", cls: "bg-block text-white", Icon: ShieldAlert },
  review: { label: "REVIEW", cls: "bg-review text-ink-950", Icon: ShieldQuestion },
  deploy: { label: "DEPLOY", cls: "bg-deploy text-ink-950", Icon: ShieldCheck },
};

export const routeText = (r: Route) =>
  [r[0]?.src, ...r.map((e) => e.dst)].filter((v, i, a) => i === 0 || v !== a[i - 1]).join(" → ");

const pct = (v: number | null, eliminated: boolean) =>
  eliminated ? "route eliminated" : v === null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(0)}%`;

export function DecisionCard({ verdict, catalogue, onPick, onHighlight }: {
  verdict: ChangeVerdict | null; catalogue: Control[];
  onPick: (ids: string[]) => void; onHighlight: (r: Route | null) => void;
}) {
  const name = (id: string) => catalogue.find((c) => c.id === id)?.name ?? id;

  if (!verdict) {
    return (
      <div className="panel flex h-full min-h-[440px] flex-col justify-center p-6 text-fg-muted">
        <div className="text-lg font-semibold text-fg">Propose a change.</div>
        <p className="mt-1 max-w-[52ch] text-sm">
          Pick one or more controls. You get the attacker's new route, the business flows the change would sever, the cost,
          how sure we are — and a verdict a change board can act on.
        </p>
      </div>
    );
  }

  const v = VERDICT[verdict.recommendation];
  const d = verdict.delta;
  const o = verdict.outcomes[0];
  const route = d.substituted_paths[0] ?? verdict.after.routes[0]?.route ?? null;
  const routeLabel = d.substituted_paths[0] ? "Attacker's new route" : "Best remaining route";
  const critical = verdict.broken_flows.some((f) => f.criticality >= 4);
  const strong = d.route_eliminated || (d.effort_increase_pct ?? 0) >= 5;

  return (
    <AnimatePresence mode="wait">
      <motion.div key={verdict.after_twin_id + verdict.control_ids.join()} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
        transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }} className="panel h-full p-6" style={{ boxShadow: "var(--shadow-lift)" }}>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="label">Proposed change</div>
            <h2 className="mt-1 text-xl font-semibold leading-tight text-balance">{verdict.control_ids.map(name).join(" + ")}</h2>
            <div className="mt-1 text-sm text-fg-muted">cost {verdict.cost} · adversary {o.agent_id} · {verdict.before.n} seeded trials</div>
          </div>
          <div className={`flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-xl font-bold tracking-wide ${v.cls}`}>
            <v.Icon className="h-5 w-5" />{v.label}
          </div>
        </div>

        <dl className="mt-5 grid grid-cols-[8.5rem_1fr] gap-y-3.5 text-sm">
          <dt className="text-fg-muted">Security</dt>
          <dd>
            <span className={`text-lg font-semibold ${strong ? "text-deploy" : "text-review"}`}>{pct(d.effort_increase_pct, d.route_eliminated)}</span>
            <span className="text-fg-muted"> modelled attacker effort</span>
            <span className="mx-2 text-ink-600">|</span>
            <span className="text-fg-muted">p(success)</span> {verdict.before.p_success.toFixed(2)} <ArrowRight className="inline h-3 w-3 text-fg-faint" /> <b>{verdict.after.p_success.toFixed(2)}</b>
            <span className="mx-2 text-ink-600">|</span>
            <span className="text-fg-muted">critical paths</span> {o.naive_before} <ArrowRight className="inline h-3 w-3 text-fg-faint" /> {o.naive_after}
            <span className="text-fg-faint"> (industry metric, −{d.naive_path_reduction_pct.toFixed(0)}%)</span>
          </dd>

          <dt className="text-fg-muted">{routeLabel}</dt>
          <dd>
            {route ? (
              <button className="group inline-flex items-center gap-2 text-left text-signal hover:underline" onClick={() => onHighlight(route)}>
                <RouteIcon className="h-4 w-4 shrink-0 opacity-70 group-hover:opacity-100" /><span className="mono text-[12.5px]">{routeText(route)}</span>
              </button>
            ) : <span className="text-fg-faint">none viable in {verdict.after.n} trials</span>}
          </dd>

          <dt className="text-fg-muted">Business</dt>
          <dd>
            {verdict.broken_flows.length === 0 ? (
              <span className="text-deploy">no legitimate flow affected</span>
            ) : verdict.broken_flows.map((f) => (
              <div key={f.id} className={f.criticality >= 4 ? "font-semibold text-block" : "text-review"}>
                Breaks {f.name} — {f.src} → {f.dst} {f.protocol}/{f.port} as {f.identity_id} <span className="rounded bg-ink-800 px-1.5 py-0.5 text-[11px]">P{6 - f.criticality}</span>
              </div>
            ))}
          </dd>

          <dt className="text-fg-muted">Confidence</dt>
          <dd>
            <b>{verdict.confidence.level}</b> <span className="text-fg-faint">({verdict.confidence.score.toFixed(2)})</span>
            {verdict.confidence.undetermined && <span className="ml-2 text-block">cannot be determined — an assumed element decides this</span>}
            <div className="mt-1 space-y-0.5">
              {verdict.confidence.unknowns.slice(0, 3).map((u) => <div key={u} className="text-xs text-fg-muted">{u}</div>)}
            </div>
          </dd>

          <dt className="text-fg-muted">Why</dt>
          <dd className="text-fg">{verdict.reasons.join("; ")}</dd>
        </dl>

        {verdict.alternatives.length > 0 && (
          <div className="mt-5 border-t border-ink-700 pt-4">
            <div className="label">{critical ? "Safer option" : "Also consider"}</div>
            <div className="mt-2 space-y-2">
              {verdict.alternatives.map((a) => (
                <button key={a.control_ids.join()} onClick={() => onPick(a.control_ids)}
                  className="panel-raised flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-sm transition-colors hover:border-signal">
                  <span className="font-medium">{a.control_ids.map(name).join(" + ")}</span>
                  <span className="shrink-0 text-fg-muted">
                    {pct(a.effort_increase_pct, a.route_eliminated)} · Δp {a.p_success_delta.toFixed(2)} · cost {a.cost} ·{" "}
                    {a.broken_flows.length ? `breaks ${a.broken_flows.join(", ")}` : "no flows affected"} ·{" "}
                    <b className={a.recommendation === "deploy" ? "text-deploy" : a.recommendation === "blocked" ? "text-block" : "text-review"}>{a.recommendation.toUpperCase()}</b>
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </motion.div>
    </AnimatePresence>
  );
}
