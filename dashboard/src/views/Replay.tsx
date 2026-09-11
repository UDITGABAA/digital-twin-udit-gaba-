import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Play, Pause, SkipForward, RotateCcw, ShieldAlert, Check, X, Radar } from "lucide-react";
import type { Step, Trial } from "../types";
import type { ReplayState } from "./Stage";
import { edgeKey } from "./Stage";

const SPEEDS = [1, 2, 4] as const;

export function Replay({ trials, noiseBudget, label, onState, onRun, running }: {
  trials: Trial[] | null; noiseBudget: number; label: string;
  onState: (s: ReplayState | null) => void; onRun: () => void; running: boolean;
}) {
  const [ti, setTi] = useState(0);         // trial index
  const [si, setSi] = useState(-1);        // step index shown (-1 = none yet)
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const feedRef = useRef<HTMLDivElement>(null);

  const trial = trials?.[ti] ?? null;
  const steps = trial?.steps ?? [];
  const shown = steps.slice(0, si + 1);
  const last: Step | undefined = shown[shown.length - 1];
  const done = trial !== null && si >= steps.length - 1;

  useEffect(() => { setTi(0); setSi(-1); setPlaying(!!trials?.length); }, [trials]);

  useEffect(() => {
    if (!playing || !trial) return;
    if (si >= steps.length - 1) {
      const t = setTimeout(() => { if (ti < (trials?.length ?? 0) - 1) { setTi(ti + 1); setSi(-1); } else setPlaying(false); }, 1400 / speed);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setSi(si + 1), 620 / speed);
    return () => clearTimeout(t);
  }, [playing, si, ti, trial, steps.length, trials, speed]);

  useEffect(() => {
    if (!trial) { onState(null); return; }
    const breached = new Set<string>();
    const traversed = new Set<string>();
    shown.forEach((s) => { if (s.succeeded) { breached.add(s.dst); traversed.add(edgeKey(s.src, s.dst, s.technique)); } });
    if (shown[0]) breached.add(shown[0].src);
    const attempting = last && !last.succeeded && !last.detected && !done ? last : null;
    onState({
      breached, traversed,
      active: last && !done ? last.dst : null,
      activeEdge: last ? edgeKey(last.src, last.dst, last.technique) : null,
      failedEdge: last && !last.succeeded ? edgeKey(last.src, last.dst, last.technique) : null,
      detected: !!last?.detected,
    });
    void attempting;
  }, [si, ti, trial]); // eslint-disable-line

  useEffect(() => { feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" }); }, [si]);

  const noise = last?.noise_so_far ?? 0;
  const outcome = !trial || !done ? null : trial.detected ? "detected" : trial.success ? "success" : "gave up";
  const successes = trials ? trials.filter((t) => t.success).length : 0;

  return (
    <div className="panel flex min-h-[440px] flex-col p-4">
      <div className="flex flex-wrap items-start gap-x-3 gap-y-2">
        <div className="min-w-0 flex-1">
          <div className="label">Attack replay</div>
          <div className="truncate text-sm font-semibold" title={label}>{label}</div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {trials ? (
            <>
              <button className="btn" onClick={() => setPlaying((p) => !p)} aria-label={playing ? "pause" : "play"}>{playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}</button>
              <button className="btn" onClick={() => { setPlaying(false); if (done) { if (ti < trials.length - 1) { setTi(ti + 1); setSi(-1); } } else setSi(steps.length - 1); }} aria-label="skip"><SkipForward className="h-3.5 w-3.5" /></button>
              <button className="btn" onClick={() => { setTi(0); setSi(-1); setPlaying(true); }} aria-label="restart"><RotateCcw className="h-3.5 w-3.5" /></button>
              <button className="btn" onClick={() => setSpeed(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length])}>{speed}×</button>
            </>
          ) : null}
          <button className="btn btn-ember ml-1" onClick={onRun} disabled={running}><Radar className="h-3.5 w-3.5" />{running ? "simulating…" : trials ? "Run again" : "Run attack"}</button>
        </div>
      </div>

      {!trials ? (
        <div className="mt-6 flex flex-1 flex-col items-center justify-center text-center text-sm text-fg-muted">
          <Radar className="mb-3 h-8 w-8 text-fg-faint" />
          Replays the first trials of the seeded simulation, step by step — the same dice the 1,000-trial statistics are built from.
        </div>
      ) : (
        <>
          <div className="mt-4 grid grid-cols-4 gap-3 text-sm">
            <div className="panel-raised px-3 py-2"><div className="label">trial</div><div className="font-semibold">{ti + 1} / {trials.length}</div></div>
            <div className="panel-raised px-3 py-2"><div className="label">route</div><div className="font-semibold">#{(trial?.route_index ?? 0) + 1} · {steps.length ? new Set(steps.map((s) => s.dst)).size : 0} hops</div></div>
            <div className="panel-raised px-3 py-2"><div className="label">effort</div><div className="font-semibold">{(last?.effort_so_far ?? 0).toFixed(0)}</div></div>
            <div className="panel-raised px-3 py-2">
              <div className="label">noise / detection budget</div>
              <div className="mt-1 meter"><div style={{ width: `${Math.min(100, (noise / noiseBudget) * 100)}%` }} /></div>
              <div className="mt-1 text-[11px] text-fg-muted">{noise.toFixed(1)} / {noiseBudget.toFixed(1)}</div>
            </div>
          </div>

          <div ref={feedRef} className="mt-3 h-[232px] space-y-1 overflow-y-auto pr-1">
            <AnimatePresence initial={false}>
              {shown.map((s, i) => (
                <motion.div key={`${ti}-${i}`} initial={{ opacity: 0, y: 6, filter: "blur(2px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                  className={`feed-line ${s.detected ? "detected" : s.succeeded ? "ok" : "fail"}`}>
                  <span className="text-fg-faint">{s.detected ? <ShieldAlert className="h-4 w-4 text-block" /> : s.succeeded ? <Check className="h-4 w-4 text-verdigris" /> : <X className="h-4 w-4 text-review" />}</span>
                  <span>
                    <span className="font-medium">{s.technique}</span>
                    <span className="text-fg-muted"> {s.src === s.dst ? `on ${s.dst}` : `${s.src} → ${s.dst}`}{s.identity_id ? ` as ${s.identity_id}` : ""}</span>
                    {s.detected ? <span className="text-block"> — noise over budget, attacker detected</span> : null}
                  </span>
                  <span className="mono text-fg-faint">{s.roll === null ? "—" : `roll ${s.roll.toFixed(2)} ${s.succeeded ? "<" : "≥"} p ${s.p_success.toFixed(2)}`}{s.attempt > 1 ? ` · try ${s.attempt}` : ""}</span>
                </motion.div>
              ))}
            </AnimatePresence>
            {outcome && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={`mt-2 rounded-lg px-3 py-2 text-sm font-semibold ${outcome === "success" ? "bg-block/20 text-ember-soft" : outcome === "detected" ? "bg-review/15 text-review" : "bg-ink-800 text-fg-muted"}`}>
                {outcome === "success" ? `Crown jewel reached — effort ${trial!.effort.toFixed(0)}, noise ${trial!.noise.toFixed(1)}` : outcome === "detected" ? "Attacker detected before reaching the target" : "Attacker gave up after three failed attempts"}
              </motion.div>
            )}
          </div>
          <div className="mt-2 text-[11px] text-fg-faint">{successes} of {trials.length} replayed trials reach the crown jewel · seed 1 · trial i here is trial i of the statistics</div>
        </>
      )}
    </div>
  );
}
