/* Minimal equity sparkline — area + line + last dot, auto-scaled. */
export function drawSparkline(id, series, color) {
  const c = document.getElementById(id);
  if (!c) return;
  const r = c.getBoundingClientRect(), d = Math.min(3, window.devicePixelRatio || 1);
  const w = Math.max(1, Math.floor(r.width * d)), h = Math.max(1, Math.floor(r.height * d));
  if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
  const ctx = c.getContext("2d");
  ctx.setTransform(d, 0, 0, d, 0, 0);
  const W = r.width, H = r.height;
  ctx.clearRect(0, 0, W, H);
  if (!series || series.length < 2) return;
  const lo = Math.min(...series), hi = Math.max(...series), span = (hi - lo) || 1;
  const xAt = i => i / (series.length - 1) * W;
  const yAt = v => H - 6 - ((v - lo) / span) * (H - 12);

  ctx.beginPath();
  series.forEach((v, i) => { const x = xAt(i), y = yAt(v); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, color + "40"); g.addColorStop(1, "transparent");
  ctx.fillStyle = g; ctx.fill();

  ctx.beginPath();
  series.forEach((v, i) => { const x = xAt(i), y = yAt(v); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.strokeStyle = color; ctx.lineWidth = 1.4; ctx.stroke();

  const lx = xAt(series.length - 1), ly = yAt(series[series.length - 1]);
  ctx.fillStyle = color; ctx.beginPath(); ctx.arc(lx, ly, 2.2, 0, Math.PI * 2); ctx.fill();
}
