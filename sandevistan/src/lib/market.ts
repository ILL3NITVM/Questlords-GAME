import { createServerFn } from "@tanstack/react-start";
import type { MarketTick } from "@/game/strategy";

/** Null when the server cannot reach Coinbase or Kraken; the client then fetches Coinbase itself. */
export const getMarket = createServerFn({ method: "GET" }).handler(async (): Promise<MarketTick | null> => {
  const { fetchMarket } = await import("./market.server");
  return fetchMarket().catch(() => null);
});

/** Up to 300 one-minute BTC-USD closes, oldest → newest. For the backtest only. Null on failure. */
export const getCandles = createServerFn({ method: "GET" }).handler(async (): Promise<number[] | null> => {
  const { fetchCandles } = await import("./market.server");
  return fetchCandles().catch(() => null);
});

export type { MarketTick };
