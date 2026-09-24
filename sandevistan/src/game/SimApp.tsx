import { useEffect, useRef, useState } from "react";
import type { Game } from "./game";
import { Hud } from "./Hud";
import { TitleOverlay } from "./TitleOverlay";
import { EndOverlay } from "./EndOverlay";
import { getMarket } from "@/lib/market";
import { decide, type MarketTick } from "@/game/strategy";

async function pullMarket(): Promise<MarketTick> {
  try {
    return await getMarket();
  } catch {
    const res = await fetch("https://api.exchange.coinbase.com/products/BTC-USD/ticker");
    const t = (await res.json()) as { price?: string };
    const price = Number(t.price);
    const statsRes = await fetch("https://api.exchange.coinbase.com/products/BTC-USD/stats");
    const s = (await statsRes.json()) as { open?: string };
    const open = Number(s.open);
    const change24 = open ? (price - open) / open : 0;
    const candleRes = await fetch(
      "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60",
    );
    const raw = (await candleRes.json()) as number[][];
    const closes = [...raw]
      .sort((a, b) => (a[0] ?? 0) - (b[0] ?? 0))
      .map((r) => Number(r[4]))
      .filter((n) => Number.isFinite(n))
      .slice(-30);
    return {
      price,
      change24,
      closes,
      source: "coinbase-direct",
      signal: decide(closes, "ts"),
      high: price,
      low: price,
    };
  }
}

export function SimApp() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [game, setGame] = useState<Game | null>(null);
  const pendingStart = useRef(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let instance: Game | null = null;
    let cancelled = false;
    void import("./game").then(({ Game }) => {
      if (cancelled || !canvasRef.current) return;
      instance = new Game(canvasRef.current);
      instance.start();
      setGame(instance);
      const qa = new URLSearchParams(window.location.search).has("qa");
      if (qa || pendingStart.current) {
        instance.audio.unlock();
        instance.sim.startRun();
        pendingStart.current = false;
      }
    });
    return () => {
      cancelled = true;
      instance?.dispose();
      setGame(null);
    };
  }, []);

  useEffect(() => {
    if (!game) return;
    let stop = false;
    const tick = () => {
      void pullMarket()
        .then((m) => {
          if (!stop) game.sim.applyMarket(m);
        })
        .catch(() => {
          /* next interval */
        });
    };
    tick();
    const id = window.setInterval(tick, 5000);
    return () => {
      stop = true;
      window.clearInterval(id);
    };
  }, [game]);

  const start = () => {
    if (!game) {
      pendingStart.current = true;
      return;
    }
    game.audio.unlock();
    game.sim.startRun();
  };

  return (
    <main className="relative h-dvh w-full overflow-hidden bg-bg text-fg">
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full touch-none" />
      <TitleOverlay game={game} onStart={start} />
      {game ? (
        <>
          <Hud game={game} />
          <EndOverlay game={game} onRestart={start} />
        </>
      ) : null}
    </main>
  );
}
