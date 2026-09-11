import NumberFlow, { type Format } from "@number-flow/react";
import type { ReactNode } from "react";

/* A figure with a quiet label. Numbers animate (NumberFlow, the same primitive KokonutUI uses)
   because a changing number is a state change worth making legible; text values do not. */
export function Stat({ label, value, format, suffix, sub, delta, deltaBad, children }: {
  label: string; value?: number; format?: Format; suffix?: string; sub?: string;
  delta?: string; deltaBad?: boolean; children?: ReactNode;
}) {
  return (
    <div className="min-w-0">
      <div className="label">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-1.5 text-[17px] font-semibold text-ink">
        {value !== undefined && <NumberFlow value={value} format={format} suffix={suffix} />}
        {children}
        {sub && <span className="text-xs font-normal text-faint">{sub}</span>}
        {delta && <span className={`text-xs font-semibold ${deltaBad ? "text-red-ink" : "text-green-ink"}`}>{delta}</span>}
      </div>
    </div>
  );
}
