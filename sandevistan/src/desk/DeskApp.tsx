import { useEffect, useRef, useSyncExternalStore } from "react";
import { Activity, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NeuralPanel } from "@/game/NeuralPanel";
import { getMarket } from "@/lib/market";
import { decide, type MarketTick } from "@/game/strategy";
import { FlyBook, type BookSnap, type Side, type Ticket } from "./book";

const book = new FlyBook();

async function pullMarket(): Promise<MarketTick> {
  try {
    return await getMarket();
  } catch {
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
}

function usd(n: number, digits = 2) {
  return n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${(n * 100).toFixed(2)}%`;
}

export function DeskApp() {
  const snap = useSyncExternalStore(book.subscribe, book.getSnapshot, book.getSnapshot);

  useEffect(() => {
    book.load();
    let stop = false;
    const tick = () => {
      void pullMarket()
        .then((m) => {
          if (!stop) book.apply(m);
        })
        .catch(() => {
          if (!stop) book.markStale();
        });
    };
    tick();
    const id = window.setInterval(tick, 4000);
    let raf = 0;
    let last = performance.now();
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      book.senseStep(dt);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => {
      stop = true;
      window.clearInterval(id);
      cancelAnimationFrame(raf);
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
                  {snap.status === "live" ? snap.source : snap.status === "stale" ? "tape delayed" : "warming"}
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
                  value={`${snap.pnlOpen >= 0 ? "+" : ""}$${usd(snap.pnlOpen)}`}
                  tone={snap.pnlOpen >= 0 ? "up" : "down"}
                />
                <Stat label="FRASS" value={String(snap.poop)} />
              </dl>
            </div>
            <TicketCard snap={snap} />
          </div>
        </section>

        <section className="rounded-xl border border-border bg-surface p-4 shadow-panel">
          <p className="font-mono text-xs tracking-widest text-muted">TAPE</p>
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
                    {row.pnl >= 0 ? "+" : ""}${usd(row.pnl)}
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

function TicketCard({ snap }: { snap: BookSnap }) {
  const t = snap.open;
  if (!t || !snap.price) {
    return (
      <div className="rounded-xl border border-border bg-surface p-4 shadow-panel">
        <p className="font-mono text-xs tracking-widest text-muted">TICKET</p>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          Flat. When smell and vote agree, the fly opens one side with a take profit and a stop. Nothing else.
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-border bg-surface p-4 shadow-panel">
      <div className="flex items-baseline justify-between">
        <p className="font-mono text-xs tracking-widest text-muted">TICKET</p>
        <p className={`font-mono text-sm ${t.side === "long" ? "text-accent" : "text-danger"}`}>
          {t.side === "long" ? "LONG" : "SHORT"}
        </p>
      </div>
      <p className="mt-2 font-mono text-lg tabular-nums text-fg">{t.qty.toFixed(5)} BTC</p>
      <dl className="mt-3 grid grid-cols-3 gap-2 font-mono text-xs">
        <Level label="SL" price={t.sl} entry={t.entry} side={t.side} kind="sl" />
        <Level label="ENTRY" price={t.entry} entry={t.entry} side={t.side} kind="entry" />
        <Level label="TP" price={t.tp} entry={t.entry} side={t.side} kind="tp" />
      </dl>
      <Rail ticket={t} price={snap.price} />
      <p className={`mt-3 font-mono text-sm tabular-nums ${snap.pnlOpen >= 0 ? "text-accent" : "text-danger"}`}>
        {snap.pnlOpen >= 0 ? "+" : ""}${usd(snap.pnlOpen)} unrealized
      </p>
    </div>
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
