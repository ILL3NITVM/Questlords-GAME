import { useEffect, useRef, useSyncExternalStore } from "react";
import { Activity, History, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NeuralPanel } from "@/game/NeuralPanel";
import { getCandles, getMarket } from "@/lib/market";
import { decide, type MarketTick } from "@/game/strategy";
import { FlyBook, MAX_OPEN, type BookSnap, type Side, type Ticket } from "./book";
import { pnlAt } from "./rules";

const book = new FlyBook();

async function pullMarket(): Promise<MarketTick> {
  const viaServer = await getMarket().catch(() => null);
  if (viaServer) return viaServer;
  const [ticker, stats, candles] = await Promise.all([
    fetch("https://api.exchange.coinbase.com/products/BTC-USD/ticker").then((r) => r.json()),
    fetch("https://api.exchange.coinbase.com/products/BTC-USD/stats").then((r) => r.json()),
    fetch("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60").then((r) => r.json()),
  ]);
  const price = Number((ticker as { price?: string }).price);
  const open = Number((stats as { open?: string }).open);
  const rows = [...(candles as number[][])].sort((a, b) => (a[0] ?? 0) - (b[0] ?? 0));
  const closes = rows.map((r) => Number(r[4])).filter((n) => Number.isFinite(n)).slice(-30);
  const last = rows[rows.length - 1];
  return {
    price,
    change24: open ? (price - open) / open : 0,
    high: Number(last?.[2] ?? price),
    low: Number(last?.[1] ?? price),
    closes,
    source: "coinbase-direct",
    signal: decide(closes, "ts"),
  };
}

/** Backtest candles. Server first, then Coinbase direct. Never invented. */
async function pullCandles(): Promise<number[]> {
  const viaServer = await getCandles().catch(() => null);
  if (viaServer) return viaServer;
  const res = await fetch("https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60");
  if (!res.ok) throw new Error(`Coinbase candles ${res.status}`);
  const rows = (await res.json()) as number[][];
  if (!Array.isArray(rows)) throw new Error("Coinbase candles: bad payload");
  return [...rows]
    .sort((a, b) => (a[0] ?? 0) - (b[0] ?? 0))
    .map((r) => Number(r[4]))
    .filter((n) => Number.isFinite(n) && n > 0);
}

function usd(n: number, digits = 2) {
  return n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function signedUsd(n: number) {
  return `${n >= 0 ? "+" : "-"}$${usd(Math.abs(n))}`;
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(2)}%`;
}

export function DeskApp() {
  const snap = useSyncExternalStore(book.subscribe, book.getSnapshot, book.getSnapshot);

  useEffect(() => {
    book.load();
    let running = false;
    let gen = 0;
    let id = 0;
    let raf = 0;
    let last = performance.now();

    const poll = (g: number) => {
      void pullMarket()
        .then((m) => {
          if (g !== gen) return;
          book.apply(m);
          // After the poll resolves, never in front of it.
          if (book.shouldAutoAsk()) void book.askBacktest(pullCandles);
        })
        .catch(() => {
          if (g === gen) book.markStale();
        });
    };
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      book.senseStep(dt);
      raf = requestAnimationFrame(loop);
    };
    const start = () => {
      if (running) return;
      running = true;
      const g = ++gen;
      poll(g);
      id = window.setInterval(() => poll(g), 4000);
      last = performance.now();
      raf = requestAnimationFrame(loop);
    };
    // Hidden tab: no poll, no rAF, no TP/SL. Save and sleep.
    const stop = () => {
      if (!running) return;
      running = false;
      gen++;
      window.clearInterval(id);
      cancelAnimationFrame(raf);
      book.sleep();
    };
    const resume = () => {
      if (running || document.visibilityState === "hidden") return;
      book.wake();
      start();
    };
    const onVisibility = () => (document.visibilityState === "hidden" ? stop() : resume());

    if (document.visibilityState !== "hidden") start();
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", stop);
    window.addEventListener("pageshow", resume);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", stop);
      window.removeEventListener("pageshow", resume);
      stop();
    };
  }, []);

  const up = snap.change24 >= 0;

  return (
    <main className="min-h-dvh bg-bg text-fg">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 md:p-6">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="font-mono text-xs tracking-widest text-muted">PROTOCOL 07 · DEMO BOOK</p>
            <h1 className="mt-1 font-sans text-3xl font-semibold tracking-tight text-fg">SANDEVISTAN</h1>
            <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted">
              No kitchen. The fly only opens tickets — take profit, stop loss, its own senses.
            </p>
          </div>
          <Button
            variant="secondary"
            className="min-h-11"
            onClick={() => book.setArmed(!snap.armed)}
            aria-pressed={snap.armed}
          >
            {snap.armed ? <Pause className="size-4" /> : <Play className="size-4" />}
            {snap.armed ? "Halt entries" : "Arm the fly"}
          </Button>
        </header>

        {snap.banner ? (
          <p className="rounded-md border border-accent/40 bg-surface px-3 py-2 font-mono text-xs tracking-widest text-accent">
            {snap.banner}
          </p>
        ) : null}

        <section className="grid gap-4 md:grid-cols-5">
          <div className="flex flex-col gap-4 md:col-span-3">
            <div className="rounded-xl border border-border bg-surface p-4 shadow-panel">
              <div className="flex items-baseline justify-between gap-3">
                <p className="font-mono text-xs tracking-widest text-muted">BTC-USD</p>
                <p className="font-mono text-xs text-subtle">
                  {snap.status === "live"
                    ? snap.source
                    : snap.status === "stale"
                      ? "tape delayed"
                      : snap.status === "asleep"
                        ? "asleep"
                        : "warming"}
                  {snap.engine === "python" ? " · py" : ""}
                </p>
              </div>
              <p className="mt-2 font-mono text-4xl font-medium tabular-nums tracking-tight text-fg">
                {snap.price ? `$${usd(snap.price, 0)}` : "—"}
              </p>
              <p className={`mt-1 font-mono text-sm tabular-nums ${up ? "text-accent" : "text-danger"}`}>
                {snap.price ? pct(snap.change24) : "waiting on the tape"}
                <span className="text-subtle"> 24h</span>
              </p>
              <Spark closes={snap.closes} />
            </div>

            <div className="rounded-xl border border-border bg-surface p-4 shadow-panel">
              <div className="mb-3 flex items-center justify-between">
                <p className="font-mono text-xs tracking-widest text-muted">OWN SENSES</p>
                <Activity className="size-3.5 text-accent" aria-hidden />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <Sense label="SMELL" value={snap.senses.smell} signed />
                <Sense label="GLARE" value={snap.senses.glare} />
                <Sense label="HUNGER" value={snap.senses.hunger} />
                <Sense label="VOTE" value={snap.senses.vote} signed />
              </div>
              <div className="mt-4">
                <NeuralPanel brain={book.brain} height={132} />
              </div>
              <p className="mt-3 text-sm leading-relaxed text-muted">{snap.note}</p>
            </div>
          </div>

          <div className="flex flex-col gap-4 md:col-span-2">
            <div className="rounded-xl border border-border bg-surface p-4 shadow-panel">
              <p className="font-mono text-xs tracking-widest text-muted">BOOK</p>
              <dl className="mt-3 grid grid-cols-2 gap-3 font-mono text-xs">
                <Stat label="EQUITY" value={`$${usd(snap.equity, 0)}`} />
                <Stat label="CASH" value={`$${usd(snap.cash, 0)}`} />
                <Stat
                  label="OPEN PNL"
                  value={signedUsd(snap.pnlOpen)}
                  tone={snap.pnlOpen >= 0 ? "up" : "down"}
                />
                <Stat label="FRASS" value={String(snap.poop)} />
              </dl>
            </div>
            <TicketList snap={snap} />
            <BacktestCard snap={snap} />
          </div>
        </section>

        <section className="rounded-xl border border-border bg-surface p-4 shadow-panel">
          <div className="flex items-baseline justify-between gap-3">
            <p className="font-mono text-xs tracking-widest text-muted">TAPE</p>
            <p className="font-mono text-xs text-subtle">
              {snap.open.length} of {MAX_OPEN} open
            </p>
          </div>
          {snap.history.length === 0 ? (
            <p className="mt-3 text-sm text-muted">No closes yet. The fly is still smelling the book.</p>
          ) : (
            <ul className="mt-3 divide-y divide-border">
              {snap.history.slice(0, 8).map((row) => (
                <li key={row.id} className="flex items-center justify-between gap-3 py-2 font-mono text-xs">
                  <span className="text-fg">{row.side === "long" ? "LONG" : "SHORT"}</span>
                  <span className={row.kind === "tp" ? "text-accent" : "text-danger"}>
                    {row.kind === "tp" ? "TP" : "SL"}
                  </span>
                  <span className="hidden text-subtle sm:inline">
                    {usd(row.entry, 0)} → {usd(row.exit, 0)}
                  </span>
                  <span className={`tabular-nums ${row.pnl >= 0 ? "text-accent" : "text-danger"}`}>
                    {signedUsd(row.pnl)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  return (
    <div>
      <dt className="text-subtle">{label}</dt>
      <dd className={`mt-1 text-sm tabular-nums ${tone === "up" ? "text-accent" : tone === "down" ? "text-danger" : "text-fg"}`}>
        {value}
      </dd>
    </div>
  );
}

function Sense({ label, value, signed }: { label: string; value: number; signed?: boolean }) {
  const mag = signed ? Math.abs(value) : value;
  const hot = signed ? value >= 0 : true;
  return (
    <div>
      <div className="flex items-baseline justify-between font-mono text-xs text-muted">
        <span>{label}</span>
        <span className={signed ? (value >= 0 ? "text-accent" : "text-danger") : "text-fg"}>
          {signed ? value.toFixed(2) : value.toFixed(2)}
        </span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
        <div
          className={`h-full rounded-full ${hot ? "bg-accent" : "bg-danger"}`}
          style={{ width: `${Math.max(4, Math.min(100, mag * 100))}%` }}
        />
      </div>
    </div>
  );
}

function TicketList({ snap }: { snap: BookSnap }) {
  const n = snap.open.length;
  return (
    <div className="rounded-xl border border-border bg-surface p-4 shadow-panel">
      <div className="flex items-baseline justify-between">
        <p className="font-mono text-xs tracking-widest text-muted">TICKETS</p>
        <p className="font-mono text-xs text-subtle">
          {n} / {MAX_OPEN} live
        </p>
      </div>
      {n === 0 ? (
        <p className="mt-3 text-sm leading-relaxed text-muted">
          Flat. When smell and vote agree, the fly opens a side with its own take profit and stop. Up to{" "}
          {MAX_OPEN} at once.
        </p>
      ) : (
        <ul className="mt-2 divide-y divide-border">
          {[...snap.open].reverse().map((t) => (
            <TicketRow key={t.id} ticket={t} price={snap.price} />
          ))}
        </ul>
      )}
    </div>
  );
}

function TicketRow({ ticket: t, price }: { ticket: Ticket; price: number }) {
  const pnl = price ? pnlAt(t, price) : 0;
  return (
    <li className="py-3">
      <div className="flex items-baseline justify-between gap-3 font-mono">
        <p className={`text-sm ${t.side === "long" ? "text-accent" : "text-danger"}`}>
          {t.side === "long" ? "LONG" : "SHORT"}
          <span className="ml-2 text-xs tabular-nums text-fg">{t.qty.toFixed(5)} BTC</span>
        </p>
        <p className={`text-sm tabular-nums ${pnl >= 0 ? "text-accent" : "text-danger"}`}>
          {signedUsd(pnl)}
        </p>
      </div>
      <dl className="mt-2 grid grid-cols-3 gap-2 font-mono text-xs">
        <Level label="SL" price={t.sl} entry={t.entry} side={t.side} kind="sl" />
        <Level label="ENTRY" price={t.entry} entry={t.entry} side={t.side} kind="entry" />
        <Level label="TP" price={t.tp} entry={t.entry} side={t.side} kind="tp" />
      </dl>
      {price ? <Rail ticket={t} price={price} /> : null}
    </li>
  );
}

function BacktestCard({ snap }: { snap: BookSnap }) {
  const bt = snap.backtest;
  const r = bt.result;
  return (
    <section aria-label="Backtest" className="rounded-xl border border-border bg-surface p-4 shadow-panel">
      <div className="flex items-baseline justify-between">
        <p className="font-mono text-xs tracking-widest text-muted">BACKTEST</p>
        <p className="font-mono text-xs text-subtle">width x{snap.bias.toFixed(2)}</p>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-muted">
        {bt.running ? "Replaying the tape on a separate $10,000 paper book…" : bt.line || "The fly has not been asked yet."}
      </p>
      {bt.error ? <p className="mt-2 font-mono text-xs text-danger">{bt.error}</p> : null}
      {r ? (
        <dl className="mt-3 grid grid-cols-2 gap-3 font-mono text-xs">
          <Stat label="TRADES" value={`${r.trades} · ${r.candles}m`} />
          <Stat label="WIN RATE" value={r.trades ? `${Math.round(r.winRate * 100)}%` : "—"} />
          <Stat label="NET PNL" value={signedUsd(r.net)} tone={r.net >= 0 ? "up" : "down"} />
          <Stat label="MAX DD" value={`${(r.maxDrawdown * 100).toFixed(2)}%`} />
        </dl>
      ) : null}
      <Button
        variant="secondary"
        className="mt-4 min-h-11 w-full"
        disabled={bt.running}
        onClick={() => void book.askBacktest(pullCandles)}
      >
        <History className="size-4" />
        Let the fly backtest
      </Button>
    </section>
  );
}

function Level({
  label,
  price,
  entry,
  kind,
}: {
  label: string;
  price: number;
  entry: number;
  side: Side;
  kind: "sl" | "tp" | "entry";
}) {
  const d = entry ? (price - entry) / entry : 0;
  return (
    <div>
      <dt className="text-subtle">{label}</dt>
      <dd className={`mt-1 tabular-nums ${kind === "tp" ? "text-accent" : kind === "sl" ? "text-danger" : "text-fg"}`}>
        {usd(price, 0)}
      </dd>
      <dd className="text-subtle">{kind === "entry" ? "—" : pct(d)}</dd>
    </div>
  );
}

function Rail({ ticket, price }: { ticket: Ticket; price: number }) {
  const lo = Math.min(ticket.sl, ticket.tp, ticket.entry, price);
  const hi = Math.max(ticket.sl, ticket.tp, ticket.entry, price);
  const span = hi - lo || 1;
  const x = (v: number) => ((v - lo) / span) * 100;
  return (
    <div className="relative mt-4 h-8">
      <div className="absolute inset-x-0 top-3 h-1.5 rounded-full bg-surface-2" />
      <Mark left={x(ticket.sl)} tone="down" />
      <Mark left={x(ticket.tp)} tone="up" />
      <Mark left={x(price)} tone="now" />
    </div>
  );
}

function Mark({ left, tone }: { left: number; tone: "up" | "down" | "now" }) {
  return (
    <span
      className={`absolute top-1.5 size-3 -translate-x-1/2 rounded-full ${
        tone === "up" ? "bg-accent" : tone === "down" ? "bg-danger" : "border-2 border-fg bg-bg"
      }`}
      style={{ left: `${left}%` }}
    />
  );
}

function Spark({ closes }: { closes: number[] }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    if (closes.length < 2) return;
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const span = max - min || 1;
    ctx.beginPath();
    closes.forEach((c, i) => {
      const x = (i / (closes.length - 1)) * w;
      const y = h - ((c - min) / span) * (h - 8) - 4;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#8dbea8";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }, [closes]);
  return <canvas ref={ref} className="mt-4 h-16 w-full" aria-hidden />;
}
