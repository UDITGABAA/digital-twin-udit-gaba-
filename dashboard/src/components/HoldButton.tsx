/* Ported from KokonutUI hold-button.tsx (Kokonut Labs, MIT): press-and-hold with a fill that
   completes the action. Here it launches the attack replay - a deliberate, physical start for the
   one moment on the page that is allowed to be theatrical. The fill is a CSS transition driven by
   state (cheapest tool that works); a timer completes the action. Keyboard: hold Enter/Space. */
import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "../lib/cn";

export function HoldButton({ onComplete, holdMs = 700, disabled, children, className }: {
  onComplete: () => void; holdMs?: number; disabled?: boolean; children: ReactNode; className?: string;
}) {
  const [holding, setHolding] = useState(false);
  const timer = useRef<number | null>(null);

  function start() {
    if (disabled || holding) return;
    setHolding(true);
    timer.current = window.setTimeout(() => { timer.current = null; setHolding(false); onComplete(); }, holdMs);
  }
  function end() {
    if (timer.current !== null) { window.clearTimeout(timer.current); timer.current = null; }
    setHolding(false);
  }
  useEffect(() => () => { if (timer.current !== null) window.clearTimeout(timer.current); }, []);

  return (
    <button type="button" disabled={disabled} aria-label="hold to run the attack"
      onPointerDown={start} onPointerUp={end} onPointerLeave={end} onPointerCancel={end}
      onKeyDown={(e) => { if ((e.key === "Enter" || e.key === " ") && !e.repeat) { e.preventDefault(); start(); } }}
      onKeyUp={(e) => { if (e.key === "Enter" || e.key === " ") end(); }}
      className={cn("btn btn-accent relative min-w-36 touch-none select-none overflow-hidden", className)}>
      <span aria-hidden className="absolute top-0 left-0 h-full bg-white/25"
        style={{ width: holding ? "100%" : "0%", transition: holding ? `width ${holdMs}ms linear` : "width 120ms ease-out" }} />
      <span className="relative z-10 flex items-center gap-2">{holding ? "keep holding…" : children}</span>
    </button>
  );
}
