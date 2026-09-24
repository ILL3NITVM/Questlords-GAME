import { createServerFn } from "@tanstack/react-start";
import type { MarketTick } from "@/game/strategy";

export const getMarket = createServerFn({ method: "GET" }).handler(async () => {
  const { fetchMarket } = await import("./market.server");
  return fetchMarket();
});

export type { MarketTick };
