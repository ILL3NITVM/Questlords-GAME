import { useSyncExternalStore } from "react";
import { Button } from "@/components/ui/button";
import type { Game } from "./game";

export function EndOverlay({ game, onRestart }: { game: Game; onRestart: () => void }) {
  const snap = useSyncExternalStore(game.sim.subscribe, game.sim.getSnapshot, game.sim.getSnapshot);
  if (snap.phase !== "dead" && snap.phase !== "won" && snap.phase !== "paused") return null;

  const title =
    snap.phase === "won" ? "Connectome locked" : snap.phase === "paused" ? "Paused" : "Molecular decay";
  const copy =
    snap.phase === "won"
      ? "All sucrose recovered. The fly brain is coupled and stable."
      : snap.phase === "paused"
        ? "Implant held. The fly is still sure about the book."
        : "Isotope gone. Motor coupling failed. The structure did not hold.";

  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center bg-bg/50 p-4">
      <div className="w-full max-w-sm rounded-xl border border-border bg-surface p-4 shadow-panel md:p-5">
        <p className="font-mono text-xs tracking-widest text-muted">TRIAL</p>
        <h2 className="mt-2 font-sans text-2xl font-semibold tracking-tight text-fg">{title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-muted">{copy}</p>
        <div className="mt-4 grid grid-cols-2 gap-3 font-mono text-xs">
          <div className="rounded-md bg-surface-2 px-3 py-2">
            <p className="text-muted">SCORE</p>
            <p className="mt-1 text-lg tabular-nums text-fg">{Math.floor(snap.score)}</p>
          </div>
          <div className="rounded-md bg-surface-2 px-3 py-2">
            <p className="text-muted">BEST</p>
            <p className="mt-1 text-lg tabular-nums text-fg">{Math.floor(snap.best)}</p>
          </div>
        </div>
        <div className="mt-4 flex flex-col gap-2">
          {snap.phase === "paused" ? (
            <Button size="lg" className="w-full" onClick={() => game.sim.togglePause()}>
              Resume
            </Button>
          ) : (
            <Button size="lg" className="w-full" onClick={onRestart}>
              Start
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
