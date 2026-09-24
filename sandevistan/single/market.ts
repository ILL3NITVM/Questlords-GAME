// Single-file build: no server. Returning null makes DeskApp fetch Coinbase directly.
import type { MarketTick } from "@/game/strategy";

export const getMarket = async (): Promise<MarketTick | null> => null;
export const getCandles = async (): Promise<number[] | null> => null;
export type { MarketTick };
