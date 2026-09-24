import { useEffect, useRef } from "react";
import type { FlyBrain } from "./brain";

export function NeuralPanel({ brain, height = 180 }: { brain: FlyBrain; height?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let raf = 0;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const draw = () => {
      raf = requestAnimationFrame(draw);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(h * dpr)) {
        canvas.width = Math.floor(w * dpr);
        canvas.height = Math.floor(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#0c1010";
      ctx.fillRect(0, 0, w, h);

      for (const e of brain.edges) {
        const a = brain.nodes[e.i];
        const b = brain.nodes[e.j];
        if (!a || !b) continue;
        const drive = brain.act[e.i] * e.w;
        ctx.strokeStyle = `rgba(141,190,168,${0.06 + drive * 0.45})`;
        ctx.lineWidth = 0.6 + drive * 1.4;
        ctx.beginPath();
        ctx.moveTo(a.x * w, a.y * h);
        ctx.lineTo(b.x * w, b.y * h);
        ctx.stroke();
      }

      for (const n of brain.nodes) {
        const v = brain.act[n.i] ?? 0;
        const r = 2.4 + v * 3.2;
        ctx.beginPath();
        ctx.fillStyle = v > 0.55 ? "#cfe7da" : v > 0.25 ? "#8dbea8" : "#3d4a44";
        ctx.arc(n.x * w, n.y * h, r, 0, Math.PI * 2);
        ctx.fill();
      }

      if (reduced) cancelAnimationFrame(raf);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [brain]);

  return (
    <canvas
      ref={ref}
      className="h-full w-full rounded-sm"
      style={{ height }}
      aria-label="Fly brain firing map"
    />
  );
}
