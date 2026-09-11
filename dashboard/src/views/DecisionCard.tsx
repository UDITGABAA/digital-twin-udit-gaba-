import { motion, AnimatePresence } from "motion/react";
import { ArrowRight, Path, CheckCircle, ArrowDown, MagnifyingGlass } from "@phosphor-icons/react";
import type { ChangeVerdict, Control, Route } from "../types";

const VERDICT = {
  blocked: { word: "Block.", tag: "tag-red", sentence: "This change severs a business flow the bank cannot lose." },
  review: { word: "Review.", tag: "tag-yellow", sentence: "Not wrong, not yet defensible. Take it to the board with the caveats." },
  deploy: { word: "Deploy.", tag: "tag-green", sentence: "Real security gain, no flow affected, evidence good enough to act on." },
};

export const routeText = (r: Route) =>
  [r[0]?.src, ...r.map((e) => e.dst)].filter((v, i, a) => i === 0 || v !== a[i - 1]).join(" → ");

const pct = (v: number | null, eliminated: boolean) =>
  eliminated ? "route eliminated" : v === null ? "—" : `${v > 0 ? "+" : ""}${v.toFixed(0)}%`;

export function DecisionCard({ verdict, catalogue, onPick, onAdopt, onHighlight }: {
  verdict: ChangeVerdict | null; catalogue: Control[];
  onPick: (ids: string[]) => void; onAdopt: () => void; onHighlight: (r: Route | null) => void;
}) {
  const name = (id: string) => catalogue.find((c) => c.id === id)?.name ?? id;

  if (!verdict) {
    return (
      <section className="card relative min-h-[460px] overflow-hidden p-8">
        <div className="hero-light" />
        <div className="relative">
          <h2 className="display text-[36px]">Propose a change.</h2>
          <p className="mt-3 max-w-[48ch] text-[15px] leading-relaxed text-muted">
            Pick controls above. You get the attacker's new route, the business flows the change would sever, the cost, how
            sure we are — and a verdict a change board can act on.
          </p>
          <dl className="mt-8 grid max-w-[46ch] grid-cols-[7rem_1fr] gap-y-2 text-sm text-muted">
            <dt className="label">Security</dt><dd>modelled attacker effort, p(success), paths — both metrics, labelled</dd>
            <dt className="label">Business</dt><dd>the legitimate flows the same rule would cut</dd>
            <dt className="label">Confidence</dt><dd>computed from the evidence behind exactly the elements that decided it</dd>
          </dl>
        </div>
      </section>
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
      <motion.section key={verdict.after_twin_id + verdict.control_ids.join()}
        initial={{ opacity: 0, transform: "translateY(6px)" }} animate={{ opacity: 1, transform: "translateY(0px)" }} exit={{ opacity: 0 }}
        transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }} className="card relative overflow-hidden p-8">
        <div className="hero-light" />
        <div className="relative">
          <div className="flex items-start justify-between gap-6">
            <div className="min-w-0">
              <div className="label">Proposed change · cost {verdict.cost} · {o.agent_id} · {verdict.before.n} seeded trials</div>
              <h2 className="display mt-2 text-[30px]">{verdict.control_ids.map(name).join(" + ")}</h2>
            </div>
            <div className="shrink-0 text-right">
              <div className="display text-[40px] leading-none text-accent">{v.word}</div>
              <span className={`tag mt-2 ${v.tag}`}>{verdict.recommendation}</span>
            </div>
          </div>
          <p className="mt-3 max-w-[60ch] text-[15px] text-muted">{v.sentence}</p>

          {/* What happens next. Nothing on this page changes the twin until you adopt. */}
          <div className="mt-5 flex flex-wrap items-center gap-3 rounded-lg border border-line bg-raised px-4 py-3 text-sm">
            {verdict.recommendation === "deploy" && (
              <>
                <span className="text-text">Nothing has changed yet. Adopt it and the twin, the numbers above and the attacker's routes all update — a child twin, with the parent kept.</span>
                <button className="btn btn-ink ml-auto" onClick={onAdopt}><CheckCircle weight="bold" />Adopt into twin</button>
              </>
            )}
            {verdict.recommendation === "review" && (
              <>
                <MagnifyingGlass weight="bold" className="text-yellow-ink" />
                <span className="text-text">Not adoptable as is. {verdict.confidence.unknowns.length ? `Verify the ${verdict.confidence.unknowns.length} inferred item${verdict.confidence.unknowns.length > 1 ? "s" : ""} listed under Confidence, ` : ""}
                  {verdict.broken_flows.length ? "decide whether the affected flow can be re-routed, " : ""}
                  {verdict.delta.effort_increase_pct !== null && verdict.delta.effort_increase_pct < 5 && !verdict.delta.route_eliminated ? "or pair it with a control that closes the route it leaves open, " : ""}
                  then re-run.</span>
                <button className="btn ml-auto" onClick={onAdopt} title="adopt anyway - the caveats stay in the lineage">Adopt anyway</button>
              </>
            )}
            {verdict.recommendation === "blocked" && (
              <>
                <ArrowDown weight="bold" className="text-red-ink" />
                <span className="text-text">Do not deploy this. {verdict.alternatives.length ? "The safer option below gets most of the security gain without cutting a P1/P2 flow — pick it and adopt that instead." : "Scope the rule so the affected flows are excepted, then re-run."}</span>
              </>
            )}
          </div>

          <dl className="mt-7 grid grid-cols-[8.5rem_1fr] gap-y-4 border-t border-line pt-6 text-sm">
            <dt className="label pt-1">Security</dt>
            <dd className="flex flex-wrap items-baseline gap-x-5 gap-y-1">
              <span><b className={`text-xl ${strong ? "text-green-ink" : "text-yellow-ink"}`}>{pct(d.effort_increase_pct, d.route_eliminated)}</b> <span className="text-muted">attacker effort</span></span>
              <span><span className="text-muted">p(success)</span> {verdict.before.p_success.toFixed(2)} <ArrowRight className="inline h-3 w-3 text-faint" weight="bold" /> <b className="text-ink">{verdict.after.p_success.toFixed(2)}</b></span>
              <span><span className="text-muted">critical paths</span> {o.naive_before} <ArrowRight className="inline h-3 w-3 text-faint" weight="bold" /> <b className="text-ink">{o.naive_after}</b> <span className="text-faint">industry metric, −{d.naive_path_reduction_pct.toFixed(0)}%</span></span>
            </dd>

            <dt className="label pt-1">{routeLabel}</dt>
            <dd>
              {route ? (
                <button className="group inline-flex items-center gap-2 text-left text-accent-deep hover:underline" onClick={() => onHighlight(route)}>
                  <Path className="h-4 w-4 shrink-0 text-accent" weight="bold" /><span className="mono text-[12.5px]">{routeText(route)}</span>
                </button>
              ) : <span className="text-faint">none viable in {verdict.after.n} trials</span>}
            </dd>

            <dt className="label pt-1">Business</dt>
            <dd className="space-y-1">
              {verdict.broken_flows.length === 0 ? (
                <span className="text-green-ink">no legitimate flow affected</span>
              ) : verdict.broken_flows.map((f) => (
                <div key={f.id} className={f.criticality >= 4 ? "font-medium text-red-ink" : "text-yellow-ink"}>
                  <span className={`tag mr-2 ${f.criticality >= 4 ? "tag-red" : "tag-yellow"}`}>P{6 - f.criticality}</span>
                  breaks {f.name} — {f.src} → {f.dst} <span className="mono">{f.protocol}/{f.port}</span> as {f.identity_id}
                </div>
              ))}
            </dd>

            <dt className="label pt-1">Confidence</dt>
            <dd>
              <b className="text-ink">{verdict.confidence.level}</b> <span className="text-faint">({verdict.confidence.score.toFixed(2)})</span>
              {verdict.confidence.undetermined && <span className="ml-2 text-red-ink">cannot be determined — an assumed element decides this</span>}
              <ul className="mt-1 space-y-0.5 text-[13px] text-muted">
                {verdict.confidence.unknowns.slice(0, 3).map((u) => <li key={u}>{u}</li>)}
              </ul>
            </dd>

            <dt className="label pt-1">Why</dt>
            <dd className="text-text">{verdict.reasons.join("; ")}</dd>
          </dl>

          {verdict.alternatives.length > 0 && (
            <div className="mt-7 border-t border-line pt-5">
              <div className="label">{critical ? "Safer option" : "Also consider"}</div>
              <div className="mt-2 divide-y divide-line">
                {verdict.alternatives.map((a) => (
                  <button key={a.control_ids.join()} onClick={() => onPick(a.control_ids)}
                    className="group flex w-full items-center justify-between gap-4 py-3 text-left text-sm transition-colors hover:bg-raised">
                    <span className="font-medium text-ink group-hover:underline">{a.control_ids.map(name).join(" + ")}</span>
                    <span className="flex shrink-0 items-center gap-3 text-muted">
                      <span>{pct(a.effort_increase_pct, a.route_eliminated)}</span>
                      <span>Δp {a.p_success_delta.toFixed(2)}</span>
                      <span>cost {a.cost}</span>
                      <span>{a.broken_flows.length ? `breaks ${a.broken_flows.join(", ")}` : "no flows affected"}</span>
                      <span className={`tag ${a.recommendation === "deploy" ? "tag-green" : a.recommendation === "blocked" ? "tag-red" : "tag-yellow"}`}>{a.recommendation}</span>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.section>
    </AnimatePresence>
  );
}
