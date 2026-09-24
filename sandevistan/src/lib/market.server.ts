import { spawn } from "node:child_process";
import { join } from "node:path";
import { decide, type DeskSignal, type MarketTick } from "@/game/strategy";

async function getJson(url: string) {
  const res = await fetch(url, {
    headers: { accept: "application/json", "user-agent": "sandevistan-fly-desk/1.0" },
    signal: AbortSignal.timeout(7000),
  });
  if (!res.ok) throw new Error(`${url} ${res.status}`);
  return res.json() as Promise<unknown>;
}

async function coinbase() {
  const [ticker, stats, candles] = await Promise.all([
    getJson("https://api.exchange.coinbase.com/products/BTC-USD/ticker"),
    getJson("https://api.exchange.coinbase.com/products/BTC-USD/stats"),
    getJson("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60"),
  ]);
  const t = ticker as { price?: string };
  const s = stats as { open?: string };
  const raw = candles as number[][];
  const rows = [...raw].sort((a, b) => (a[0] ?? 0) - (b[0] ?? 0));
  const last = rows[rows.length - 1];
  const closes = rows.map((r) => Number(r[4])).filter((n) => Number.isFinite(n)).slice(-30);
  const price = Number(t.price ?? closes[closes.length - 1]);
  const open = Number(s.open);
  const change24 = open ? (price - open) / open : 0;
  const high = Number(last?.[2] ?? price);
  const low = Number(last?.[1] ?? price);
  return { price, change24, high, low, closes, source: "coinbase" };
}

async function kraken() {
  const data = (await getJson("https://api.kraken.com/0/public/Ticker?pair=XBTUSD")) as {
    result?: { XXBTZUSD?: { c?: string[]; o?: string } };
  };
  const row = data.result?.XXBTZUSD;
  const price = Number(row?.c?.[0]);
  const open = Number(row?.o);
  if (!Number.isFinite(price)) throw new Error("kraken empty");
  const change24 = open ? (price - open) / open : 0;
  const closes = [open, price];
  return { price, change24, high: price, low: price, closes, source: "kraken" };
}

function pythonSignal(closes: number[]): Promise<DeskSignal | null> {
  const script = join(process.cwd(), "python", "fly_desk.py");
  return new Promise((resolve) => {
    const child = spawn("python3", [script], { stdio: ["pipe", "pipe", "pipe"] });
    let out = "";
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      resolve(null);
    }, 1800);
    child.stdout.on("data", (c: Buffer) => {
      out += c.toString("utf8");
    });
    child.on("error", () => {
      clearTimeout(timer);
      resolve(null);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        resolve(null);
        return;
      }
      try {
        const parsed = JSON.parse(out) as DeskSignal;
        parsed.engine = "python";
        resolve(parsed);
      } catch {
        resolve(null);
      }
    });
    child.stdin.write(JSON.stringify({ closes }));
    child.stdin.end();
  });
}

export async function fetchMarket(): Promise<MarketTick> {
  let book: { price: number; change24: number; high: number; low: number; closes: number[]; source: string };
  try {
    book = await coinbase();
  } catch {
    book = await kraken();
  }
  const py = await pythonSignal(book.closes);
  const signal = py ?? decide(book.closes, "ts");
  return { ...book, signal };
}

/** One Coinbase call at granularity 60: as many candles as it returns (≤300). */
export async function fetchCandles(): Promise<number[]> {
  const raw = (await getJson("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60")) as number[][];
  if (!Array.isArray(raw)) throw new Error("coinbase candles: bad payload");
  return [...raw]
    .sort((a, b) => (a[0] ?? 0) - (b[0] ?? 0))
    .map((r) => Number(r[4]))
    .filter((n) => Number.isFinite(n) && n > 0);
}
