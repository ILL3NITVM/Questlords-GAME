import { useRef } from "react";
import { Cpu, Zap } from "lucide-react";
import { useSyncExternalStore } from "react";
import type { Game } from "./game";

export function TouchControls({ game }: { game: Game }) {
  const snap = useSyncExternalStore(game.sim.subscribe, game.sim.getSnapshot, game.sim.getSnapshot);
  const stick = useRef<HTMLDivElement>(null);
  const pid = useRef<number | null>(null);

  if (snap.phase !== "play") return null;

  const onDown = (e: React.PointerEvent<HTMLDivElement>) => {
    pid.current = e.pointerId;
    e.currentTarget.setPointerCapture(e.pointerId);
    move(e);
  };
  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (pid.current !== e.pointerId) return;
    move(e);
  };
  const onUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (pid.current !== e.pointerId) return;
    pid.current = null;
    game.input.setTouch(0, 0);
    const knob = stick.current?.querySelector("[data-knob]") as HTMLElement | null;
    if (knob) knob.style.transform = "translate(-50%,-50%)";
  };
  const move = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = stick.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    let x = (e.clientX - cx) / (r.width * 0.42);
    let y = (cy - e.clientY) / (r.height * 0.42);
    const m = Math.hypot(x, y);
    if (m > 1) {
      x /= m;
      y /= m;
    }
    game.input.setTouch(x, y);
    const knob = el.querySelector("[data-knob]") as HTMLElement | null;
    if (knob) knob.style.transform = `translate(calc(-50% + ${x * 28}px), calc(-50% + ${-y * 28}px))`;
  };

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-end justify-between p-4 md:hidden">
      <div
        ref={stick}
        className="pointer-events-auto relative size-24 rounded-full border border-border bg-surface/80"
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        aria-label="Move"
      >
        <div
          data-knob
          className="absolute left-1/2 top-1/2 size-11 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent/80"
        />
      </div>
      <div className="pointer-events-auto flex flex-col gap-2">
        <button
          type="button"
          className="flex size-12 items-center justify-center rounded-md border border-border bg-surface/90 text-fg"
          onPointerDown={() => game.input.pulseToggle()}
          aria-label="Toggle fly brain"
        >
          <Cpu className="size-5" />
        </button>
        <button
          type="button"
          className="flex size-14 items-center justify-center rounded-md border border-accent/40 bg-accent text-accent-fg"
          onPointerDown={() => game.input.setTouchDash(true)}
          onPointerUp={() => game.input.setTouchDash(false)}
          onPointerCancel={() => game.input.setTouchDash(false)}
          aria-label="Sandevistan dash"
        >
          <Zap className="size-6" />
        </button>
      </div>
    </div>
  );
}
