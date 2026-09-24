import { createServerFn } from "@tanstack/react-start";
import type { MarketTick } from "@/game/strategy";

export const getMarket = createServerFn({ method: "GET" }).handler(async () => {
  const { fetchMarket } = await import("./market.server");
  return fetchMarket();
});

export type { MarketTick };

/** Up to 300 one-minute BTC-USD closes, oldest → newest. For the backtest only. */
export const getCandles = createServerFn({ method: "GET" }).handler(async () => {
  const { fetchCandles } = await import("./market.server");
  return fetchCandles();
});
