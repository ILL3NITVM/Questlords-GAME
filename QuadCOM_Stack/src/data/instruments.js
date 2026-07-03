/* HARVESTED (Phase 7C) from predecessor QuadCOMv40Complete ->
 * QuadCOM_Full_App_ToolIndicators_Instruments_v19/app/instruments.js.
 * Pure instrument data — adapted unchanged except this provenance header.
 * All instruments are synthetic substrate definitions (.SYN / SBCI).
 * Trimmed: applyInstrumentToState() — coupled to the predecessor state shape;
 * QuadCOM_Stack applies profiles via product.switchAsset() instead. */
export const INSTRUMENT_CATALOG = [
  { id: "SBCI.FX16", name: "Synthetic Bundled Currency Index", alias: "16-FX Basket Model", family: "FX_INDEX", base: 1.08724, tick: 0.00001, min: 1.082, max: 1.093, spreadTicks: 2.2 },
  { id: "EURUSD.SYN", name: "Euro / US Dollar", alias: "Synthetic Spot", family: "FX", base: 1.0894, tick: 0.00001, min: 1.078, max: 1.102, spreadTicks: 1.9 },
  { id: "GBPUSD.SYN", name: "British Pound / US Dollar", alias: "Synthetic Spot", family: "FX", base: 1.2742, tick: 0.00001, min: 1.251, max: 1.299, spreadTicks: 2.3 },
  { id: "USDJPY.SYN", name: "US Dollar / Japanese Yen", alias: "Synthetic Spot", family: "FX", base: 160.42, tick: 0.001, min: 155.0, max: 166.5, spreadTicks: 2.0 },
  { id: "AUDUSD.SYN", name: "Australian Dollar / US Dollar", alias: "Synthetic Spot", family: "FX", base: 0.6672, tick: 0.00001, min: 0.644, max: 0.689, spreadTicks: 2.1 },
  { id: "USDCAD.SYN", name: "US Dollar / Canadian Dollar", alias: "Synthetic Spot", family: "FX", base: 1.3657, tick: 0.00001, min: 1.342, max: 1.389, spreadTicks: 2.2 },
  { id: "USDCHF.SYN", name: "US Dollar / Swiss Franc", alias: "Synthetic Spot", family: "FX", base: 0.8926, tick: 0.00001, min: 0.874, max: 0.911, spreadTicks: 2.0 },
  { id: "NZDUSD.SYN", name: "New Zealand Dollar / US Dollar", alias: "Synthetic Spot", family: "FX", base: 0.6118, tick: 0.00001, min: 0.594, max: 0.632, spreadTicks: 2.2 },
  { id: "XAUUSD.SYN", name: "Gold / US Dollar", alias: "Synthetic Metals", family: "METAL", base: 2352.4, tick: 0.1, min: 2200, max: 2525, spreadTicks: 3.0 },
  { id: "XAGUSD.SYN", name: "Silver / US Dollar", alias: "Synthetic Metals", family: "METAL", base: 31.2, tick: 0.01, min: 24.5, max: 36.5, spreadTicks: 3.2 },
  { id: "BTCUSD.SYN", name: "Bitcoin / US Dollar", alias: "Synthetic Perpetual", family: "CRYPTO", base: 64500, tick: 0.5, min: 52000, max: 78000, spreadTicks: 3.6 },
  { id: "ETHUSD.SYN", name: "Ether / US Dollar", alias: "Synthetic Perpetual", family: "CRYPTO", base: 3525, tick: 0.1, min: 2400, max: 4400, spreadTicks: 3.4 },
  { id: "SOLUSD.SYN", name: "Solana / US Dollar", alias: "Synthetic Perpetual", family: "CRYPTO", base: 156.2, tick: 0.01, min: 85, max: 240, spreadTicks: 3.6 },
  { id: "NAS100.SYN", name: "Nasdaq 100", alias: "Synthetic Index", family: "INDEX", base: 19750, tick: 1, min: 16800, max: 21900, spreadTicks: 2.6 },
  { id: "SPX500.SYN", name: "S&P 500", alias: "Synthetic Index", family: "INDEX", base: 5560, tick: 0.5, min: 4980, max: 6100, spreadTicks: 2.4 },
  { id: "US30.SYN", name: "Dow 30", alias: "Synthetic Index", family: "INDEX", base: 39720, tick: 1, min: 35500, max: 43400, spreadTicks: 2.5 },
  { id: "GER40.SYN", name: "DAX 40", alias: "Synthetic Index", family: "INDEX", base: 18340, tick: 1, min: 16500, max: 20100, spreadTicks: 2.4 },
  { id: "UK100.SYN", name: "FTSE 100", alias: "Synthetic Index", family: "INDEX", base: 8260, tick: 0.5, min: 7380, max: 8940, spreadTicks: 2.3 },
  { id: "WTI.SYN", name: "WTI Crude Oil", alias: "Synthetic Energy", family: "ENERGY", base: 81.2, tick: 0.01, min: 61, max: 102, spreadTicks: 2.8 },
  { id: "BRENT.SYN", name: "Brent Crude Oil", alias: "Synthetic Energy", family: "ENERGY", base: 84.6, tick: 0.01, min: 64, max: 106, spreadTicks: 2.8 },
  { id: "NGAS.SYN", name: "Natural Gas", alias: "Synthetic Energy", family: "ENERGY", base: 2.62, tick: 0.001, min: 1.65, max: 4.4, spreadTicks: 3.0 },
  { id: "CORN.SYN", name: "Corn Futures", alias: "Synthetic Agriculture", family: "AGRI", base: 452, tick: 0.25, min: 360, max: 620, spreadTicks: 2.9 },
  { id: "WHEAT.SYN", name: "Wheat Futures", alias: "Synthetic Agriculture", family: "AGRI", base: 588, tick: 0.25, min: 420, max: 760, spreadTicks: 3.0 },
  { id: "SOYB.SYN", name: "Soybeans Futures", alias: "Synthetic Agriculture", family: "AGRI", base: 1175, tick: 0.25, min: 910, max: 1480, spreadTicks: 2.9 },
  { id: "EURGBP.SYN", name: "Euro / British Pound", alias: "Synthetic Spot", family: "FX", base: 0.8548, tick: 0.00001, min: 0.836, max: 0.874, spreadTicks: 2.0 },
  { id: "EURJPY.SYN", name: "Euro / Japanese Yen", alias: "Synthetic Spot", family: "FX", base: 174.82, tick: 0.001, min: 166.0, max: 184.5, spreadTicks: 2.4 },
  { id: "GBPJPY.SYN", name: "British Pound / Japanese Yen", alias: "Synthetic Spot", family: "FX", base: 204.42, tick: 0.001, min: 192.0, max: 217.0, spreadTicks: 2.8 },
  { id: "AUDJPY.SYN", name: "Australian Dollar / Japanese Yen", alias: "Synthetic Spot", family: "FX", base: 107.05, tick: 0.001, min: 98.0, max: 116.0, spreadTicks: 2.5 },
  { id: "EURAUD.SYN", name: "Euro / Australian Dollar", alias: "Synthetic Spot", family: "FX", base: 1.6328, tick: 0.00001, min: 1.572, max: 1.694, spreadTicks: 2.6 },
  { id: "XRPUSD.SYN", name: "Ripple / US Dollar", alias: "Synthetic Perpetual", family: "CRYPTO", base: 0.52, tick: 0.0001, min: 0.32, max: 0.86, spreadTicks: 3.4 },
  { id: "ADAUSD.SYN", name: "Cardano / US Dollar", alias: "Synthetic Perpetual", family: "CRYPTO", base: 0.45, tick: 0.0001, min: 0.28, max: 0.72, spreadTicks: 3.4 },
  { id: "DOGEUSD.SYN", name: "Dogecoin / US Dollar", alias: "Synthetic Perpetual", family: "CRYPTO", base: 0.128, tick: 0.00005, min: 0.07, max: 0.24, spreadTicks: 3.8 },
  { id: "HK50.SYN", name: "Hang Seng 40", alias: "Synthetic Index", family: "INDEX", base: 17960, tick: 1, min: 15800, max: 20400, spreadTicks: 2.8 },
  { id: "JPN225.SYN", name: "Nikkei 225", alias: "Synthetic Index", family: "INDEX", base: 39580, tick: 5, min: 34500, max: 43800, spreadTicks: 2.7 },
  { id: "XPTUSD.SYN", name: "Platinum / US Dollar", alias: "Synthetic Metals", family: "METAL", base: 962.5, tick: 0.1, min: 820, max: 1120, spreadTicks: 3.3 },
  { id: "XPDUSD.SYN", name: "Palladium / US Dollar", alias: "Synthetic Metals", family: "METAL", base: 1012.0, tick: 0.5, min: 850, max: 1260, spreadTicks: 3.5 },
  { id: "COFFEE.SYN", name: "Coffee Futures", alias: "Synthetic Agriculture", family: "AGRI", base: 218.5, tick: 0.25, min: 165, max: 290, spreadTicks: 3.1 },
  { id: "SUGAR.SYN", name: "Sugar Futures", alias: "Synthetic Agriculture", family: "AGRI", base: 19.4, tick: 0.05, min: 14.5, max: 26.0, spreadTicks: 2.9 },
  { id: "COTTON.SYN", name: "Cotton Futures", alias: "Synthetic Agriculture", family: "AGRI", base: 78.6, tick: 0.05, min: 62.0, max: 98.0, spreadTicks: 3.0 },
  { id: "US10Y.SYN", name: "US 10-Year Treasury Yield", alias: "Synthetic Rates", family: "BOND", base: 4.28, tick: 0.005, min: 3.4, max: 5.4, spreadTicks: 2.2 },
  { id: "DE10Y.SYN", name: "German 10-Year Bund Yield", alias: "Synthetic Rates", family: "BOND", base: 2.42, tick: 0.005, min: 1.6, max: 3.4, spreadTicks: 2.2 },
  { id: "VIX.SYN", name: "Volatility Index", alias: "Synthetic Volatility", family: "VOL", base: 14.8, tick: 0.01, min: 9.0, max: 42.0, spreadTicks: 3.6 }
];

export const DEFAULT_INSTRUMENT_ID = "SBCI.FX16";

export function getInstrumentProfile(id) {
  const found = INSTRUMENT_CATALOG.find(x => x.id === id);
  return found || INSTRUMENT_CATALOG.find(x => x.id === DEFAULT_INSTRUMENT_ID) || INSTRUMENT_CATALOG[0];
}

export function familyLegCount(family) {
  if (family === "FX_INDEX") return 16;
  if (family === "FX") return 10;
  if (family === "CRYPTO") return 12;
  if (family === "INDEX") return 14;
  if (family === "METAL") return 8;
  if (family === "ENERGY") return 9;
  if (family === "AGRI") return 11;
  if (family === "BOND") return 7;
  if (family === "VOL") return 6;
  return 8;
}
