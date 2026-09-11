/* Ported from KokonutUI smooth-tab.tsx (Kokonut Labs, MIT): the sliding-background segmented
   control, without the demo card area. Keyboard: arrow keys move, Enter/Space select. */
import * as React from "react";
import { motion } from "motion/react";
import { cn } from "../lib/cn";

export interface TabItem { id: string; title: string; hint?: string }

export function SegmentedTabs({ items, value, onChange, className }: {
  items: TabItem[]; value: string; onChange: (id: string) => void; className?: string;
}) {
  const [dims, setDims] = React.useState({ width: 0, left: 0 });
  const refs = React.useRef<Map<string, HTMLButtonElement>>(new Map());
  const box = React.useRef<HTMLDivElement>(null);

  React.useLayoutEffect(() => {
    const update = () => {
      const b = refs.current.get(value), c = box.current;
      if (b && c) { const r = b.getBoundingClientRect(), cr = c.getBoundingClientRect(); setDims({ width: r.width, left: r.left - cr.left }); }
    };
    requestAnimationFrame(update);
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [value, items]);

  const move = (e: React.KeyboardEvent, i: number) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const next = items[(i + (e.key === "ArrowRight" ? 1 : -1) + items.length) % items.length];
    onChange(next.id); refs.current.get(next.id)?.focus();
  };

  return (
    <div ref={box} role="tablist" className={cn("relative inline-flex items-center gap-1 rounded-lg border border-line bg-surface p-1", className)}>
      <motion.div aria-hidden className="absolute top-1 bottom-1 rounded-md bg-ink" initial={false}
        animate={{ transform: `translateX(${dims.left}px)`, width: dims.width }}
        transition={{ type: "spring", stiffness: 500, damping: 40, mass: 0.6 }} style={{ left: 0 }} />
      {items.map((t, i) => {
        const on = t.id === value;
        return (
          <button key={t.id} role="tab" aria-selected={on} title={t.hint} ref={(el) => { if (el) refs.current.set(t.id, el); }}
            onClick={() => onChange(t.id)} onKeyDown={(e) => move(e, i)}
            className={cn("relative z-10 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors duration-200", on ? "text-white" : "text-muted hover:text-ink")}>
            {t.title}
          </button>
        );
      })}
    </div>
  );
}
