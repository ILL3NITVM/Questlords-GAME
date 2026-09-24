import { useSyncExternalStore } from "react";
import { Activity, Cpu } from "lucide-react";
import type { Game } from "./game";
import { NeuralPanel } from "./NeuralPanel";
import { DeskPanel } from "./DeskPanel";

function fmt(n: number) {
  return Math.floor(n).toLocaleString();
}

function Bar({
  value,
  label,
  warn,
}: {
  value: number;
  label: string;
  warn?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between font-mono text-xs tracking-wide text-muted">
        <span>{label}</span>
        <span className={warn ? "text-danger" : "text-fg"}>{Math.round(value)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
        <div
          className={`h-full rounded-full ${warn ? "bg-danger" : "bg-accent"}`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

export function Hud({ game }: { game: Game }) {
  const snap = useSyncExternalStore(game.sim.subscribe, game.sim.getSnapshot, game.sim.getSnapshot);
  if (snap.phase === "title") return null;

  return (
    <div className="pointer-events-none absolute inset-0 z-10 flex flex-col justify-between p-3 md:p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="rounded-md border border-border bg-surface/90 px-3 py-2 shadow-panel">
          <p className="font-mono text-xs tracking-widest text-muted">PROTOCOL 07</p>
          <p className="font-sans text-sm font-medium tracking-tight text-fg">SANDEVISTAN</p>
        </div>
        <div className="flex max-w-xs flex-col gap-2">
          <div className="min-w-40 rounded-md border border-border bg-surface/90 px-3 py-2 font-mono text-xs shadow-panel">
            <div className="flex justify-between text-muted">
              <span>SCORE</span>
              <span className="tabular-nums text-fg">{fmt(snap.score)}</span>
            </div>
            <div className="mt-1 flex justify-between text-muted">
              <span>BEST</span>
              <span className="tabular-nums text-fg">{fmt(snap.best)}</span>
            </div>
            <div className="mt-1 flex justify-between text-muted">
              <span>SUCROSE</span>
              <span className="tabular-nums text-fg">
                {snap.sucrose}/{snap.sucroseTotal}
              </span>
            </div>
          </div>
          <div className="hidden md:block">
            <DeskPanel snap={snap} />
          </div>
          <div className="md:hidden">
            <DeskPanel snap={snap} compact />
          </div>
        </div>
      </div>

      <div className="mt-3 hidden w-[min(18rem,38vw)] md:block">
        <div className="rounded-lg border border-border bg-surface/90 p-3 shadow-panel">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-xs tracking-widest text-muted">DROSOPHILA CONNECTOME</span>
            <Activity className="size-3.5 text-accent" aria-hidden />
          </div>
          <NeuralPanel brain={game.sim.brain} height={168} />
          <div className="mt-2 grid grid-cols-3 gap-2 font-mono text-xs tracking-wide text-muted">
            <span>AL {snap.olfactory.toFixed(2)}</span>
            <span>CX {snap.cx.toFixed(2)}</span>
            <span>FIRE {Math.round(snap.firing * 100)}%</span>
          </div>
        </div>
      </div>

      <div className="mt-auto flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="w-full max-w-xs rounded-lg border border-border bg-surface/90 p-3 shadow-panel">
          <Bar value={snap.isotope} label="ISOTOPE H-ε" warn={snap.isotope < 28 || snap.inLight} />
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Bar value={snap.motorL * 100} label="MOTOR L" />
            <Bar value={snap.motorR * 100} label="MOTOR R" />
          </div>
          <div className="mt-3 flex items-center justify-between font-mono text-xs text-muted">
            <span className="inline-flex items-center gap-1.5">
              <Cpu className="size-3.5 text-accent" />
              AUTONOMOUS
            </span>
            <span className="tabular-nums">
              {snap.dashT > 0 ? "SANDEVISTAN" : snap.deskQty > 0 ? "LONG" : "HUNTING"}
            </span>
          </div>
        </div>
        <p className="hidden font-mono text-xs tracking-wide text-subtle md:block">
          The fly walks. The fly fills. You watch. P pause
        </p>
      </div>

      {snap.banner ? (
        <div className="pointer-events-none absolute inset-x-0 top-[18%] flex justify-center">
          <p className="rounded-sm border border-accent/40 bg-bg/70 px-4 py-2 font-mono text-xs tracking-widest text-accent md:text-sm">
            {snap.banner}
          </p>
        </div>
      ) : null}
    </div>
  );
}
