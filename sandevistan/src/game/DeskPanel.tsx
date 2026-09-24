import { TrendingUp } from "lucide-react";
import type { Snapshot } from "./sim";

function money(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function usd(n: number) {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function DeskPanel({ snap, compact }: { snap: Snapshot; compact?: boolean }) {
  const up = snap.btcChg >= 0;
  const pnlUp = snap.deskPnl >= 0;
  const side = snap.deskQty > 0 ? "LONG" : "FLAT";

  return (
    <div className="rounded-md border border-border bg-surface/90 px-3 py-2 font-mono text-xs shadow-panel">
      <div className="flex items-center justify-between gap-2 text-muted">
        <span className="inline-flex items-center gap-1.5 tracking-widest">
          <TrendingUp className="size-3.5 text-accent" aria-hidden />
          FLY DESK
        </span>
        <span className="text-subtle">{snap.deskEngine === "python" ? "DEMO · PY" : "DEMO"}</span>
      </div>
      <div className="mt-1.5 flex items-baseline justify-between gap-3">
        <span className="text-muted">BTC</span>
        <span className="tabular-nums text-fg">{snap.btc ? `$${usd(snap.btc)}` : "—"}</span>
      </div>
      <div className="mt-1 flex items-baseline justify-between">
        <span className="text-muted">24H</span>
        <span className={`tabular-nums ${up ? "text-accent" : "text-danger"}`}>
          {snap.btc ? `${up ? "+" : ""}${(snap.btcChg * 100).toFixed(2)}%` : "—"}
        </span>
      </div>
      {compact ? null : (
        <>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-muted">BOOK</span>
            <span className="tabular-nums text-fg">
              {side} · ${money(snap.deskEquity)}
            </span>
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-muted">PNL</span>
            <span className={`tabular-nums ${pnlUp ? "text-accent" : "text-danger"}`}>
              {pnlUp ? "+" : ""}${usd(snap.deskPnl)}
            </span>
          </div>
        </>
      )}
      <div className="mt-1 flex items-baseline justify-between">
        <span className="text-muted">HUNT</span>
        <span className={`tabular-nums ${snap.flyHunt >= 0 ? "text-accent" : "text-danger"}`}>
          {snap.flyHunt >= 0 ? "+" : ""}
          {snap.flyHunt.toFixed(2)}
        </span>
      </div>
      <div className="mt-1 flex items-baseline justify-between gap-2">
        <span className="text-muted">FILL</span>
        <span className="truncate text-right tabular-nums text-fg">{snap.lastFill}</span>
      </div>
      <div className="mt-1 flex items-baseline justify-between">
        <span className="text-muted">POOP</span>
        <span className="tabular-nums text-fg">
          {snap.poopLive} live · {snap.poopEaten} fed
        </span>
      </div>
      {compact ? null : (
        <p className="mt-2 leading-relaxed text-subtle">{snap.deskNote}</p>
      )}
    </div>
  );
}
