import { useSyncExternalStore } from "react";
import { Button } from "@/components/ui/button";
import type { Game } from "./game";
import type { Snapshot } from "./sim";

function titleStore(game: Game | null) {
  return {
    subscribe: (fn: () => void) => (game?.sim ? game.sim.subscribe(fn) : () => {}),
    get: (): Snapshot | null => game?.sim?.getSnapshot() ?? null,
  };
}

export function TitleOverlay({ game, onStart }: { game: Game | null; onStart: () => void }) {
  const store = titleStore(game);
  const snap = useSyncExternalStore(store.subscribe, store.get, store.get);
  if (snap && snap.phase !== "title") return null;

  return (
    <div className="absolute inset-0 z-20 flex items-end justify-start md:items-center">
      <div className="w-full max-w-md p-4 md:p-6">
        <div className="rounded-xl border border-border bg-surface/95 p-4 shadow-panel md:p-5">
          <p className="font-mono text-xs tracking-widest text-muted">REAL · PROTOCOL 07</p>
          <h1 className="mt-2 font-sans text-3xl font-semibold tracking-tight text-fg md:text-4xl">
            SANDEVISTAN
          </h1>
          <p className="mt-1 font-sans text-lg font-medium tracking-tight text-accent">Cockroach</p>
          <p className="mt-4 max-w-prose text-sm leading-relaxed text-muted">
            A digital fruit-fly connectome socketed into <em className="text-fg">Periplaneta americana</em>.
            The fly places Bitcoin orders with its legs. Full autonomy — you watch.
            Kenyon cells whisper; descending neurons fill. Demo book. Poop pays.
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 font-mono text-xs text-subtle">
            <div>
              <dt className="text-muted">IMPLANT</dt>
              <dd className="text-fg">Brain motor control</dd>
            </div>
            <div>
              <dt className="text-muted">CONNECTOME</dt>
              <dd className="text-fg">~140k neurons</dd>
            </div>
            <div>
              <dt className="text-muted">COUPLING</dt>
              <dd className="text-fg">Exotic H isotope</dd>
            </div>
            <div>
              <dt className="text-muted">BURST</dt>
              <dd className="text-fg">Here then there</dd>
            </div>
            <div>
              <dt className="text-muted">DESK</dt>
              <dd className="text-fg">BTC demo · poop pnl</dd>
            </div>
          </dl>
          <div className="mt-5 flex flex-col gap-2">
            <Button size="lg" className="w-full" onClick={onStart}>
              Release the fly
            </Button>
            {snap?.btc ? (
              <p className="font-mono text-xs leading-relaxed text-subtle">
                Live BTC ${snap.btc.toLocaleString(undefined, { maximumFractionDigits: 0 })} · autonomous desk · demo
              </p>
            ) : (
              <p className="font-mono text-xs leading-relaxed text-subtle">
                Full autonomy. The fly trades.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
