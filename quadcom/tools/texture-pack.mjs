// AURUM texture pack for QuadCOM — generated, deterministic, seamlessly tiling.
//   node tools/texture-pack.mjs        -> writes textures/*.png + textures/pack.json
//
// No image tooling is required: the PNG encoder below is ~30 lines on top of zlib.
// Every texture is periodic in both axes, so any `background-repeat` or GPU
// `repeat` sampler tiles without seams.
import { deflateSync } from "node:zlib";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "textures");
mkdirSync(OUT, { recursive: true });

/* ── PNG ─────────────────────────────────────────────────────────── */
const CRC = new Uint32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
const crc32 = buf => { let c = 0xffffffff; for (const b of buf) c = CRC[(c ^ b) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
}
function png(w, h, rgba) {
  const raw = Buffer.alloc((w * 4 + 1) * h);
  for (let y = 0; y < h; y++) { raw[y * (w * 4 + 1)] = 0; rgba.copy ? rgba.copy(raw, y * (w * 4 + 1) + 1, y * w * 4, (y + 1) * w * 4) : raw.set(rgba.subarray(y * w * 4, (y + 1) * w * 4), y * (w * 4 + 1) + 1); }
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw, { level: 9 })), chunk("IEND", Buffer.alloc(0))]);
}

/* ── periodic noise ──────────────────────────────────────────────── */
const hash = (x, y, s) => { let h = Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(s, 2246822519); h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967296; };
const fade = t => t * t * t * (t * (t * 6 - 15) + 10);
// Value noise with integer periods px/py → tiles exactly.
function vnoise(x, y, px, py, s) {
  const xi = Math.floor(x), yi = Math.floor(y), fx = fade(x - xi), fy = fade(y - yi);
  const w = (a, b) => hash(((a % px) + px) % px, ((b % py) + py) % py, s);
  const a = w(xi, yi), b = w(xi + 1, yi), c = w(xi, yi + 1), d = w(xi + 1, yi + 1);
  return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
}
function fbm(u, v, fx, fy, oct, s) { let sum = 0, amp = 0.5, norm = 0; for (let o = 0; o < oct; o++) { const m = 1 << o; sum += amp * vnoise(u * fx * m, v * fy * m, fx * m, fy * m, s + o * 17); norm += amp; amp *= 0.5; } return sum / norm; }
const mix = (a, b, t) => a + (b - a) * t;
const ramp = (stops, t) => { t = Math.max(0, Math.min(1, t)); for (let i = 1; i < stops.length; i++) if (t <= stops[i][0]) { const [t0, c0] = stops[i - 1], [t1, c1] = stops[i], k = (t - t0) / (t1 - t0); return c0.map((c, j) => mix(c, c1[j], k)); } return stops[stops.length - 1][1]; };

function make(name, w, h, fn, meta) {
  const buf = Buffer.alloc(w * h * 4);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const [r, g, b, a = 255] = fn(x / w, y / h, x, y);
    const o = (y * w + x) * 4;
    buf[o] = Math.round(Math.max(0, Math.min(255, r))); buf[o + 1] = Math.round(Math.max(0, Math.min(255, g)));
    buf[o + 2] = Math.round(Math.max(0, Math.min(255, b))); buf[o + 3] = Math.round(Math.max(0, Math.min(255, a)));
  }
  writeFileSync(join(OUT, `${name}.png`), png(w, h, buf));
  return { file: `${name}.png`, width: w, height: h, ...meta };
}

/* ── the pack ────────────────────────────────────────────────────── */
const GOLD = [[0, [18, 12, 3]], [0.35, [74, 53, 16]], [0.62, [168, 125, 38]], [0.84, [217, 173, 69]], [1, [246, 217, 120]]];
const pack = [];

// Brushed gold: long anisotropic streaks (x-period 2, y-period 128) over a slow sheen.
pack.push(make("aurum-brushed", 512, 128, (u, v) => {
  const streak = fbm(u, v, 2, 128, 4, 11), fine = vnoise(u * 6, v * 128, 6, 128, 29);
  const sheen = 0.5 + 0.5 * Math.cos((u * 2 + v) * Math.PI * 2);
  return ramp(GOLD, 0.30 + streak * 0.42 + fine * 0.12 + sheen * 0.16);
}, { role: "gold material: panel headers, primary buttons, Vision fan and ring", tile: "repeat" }));

// Obsidian grain: near-black mineral grain with rare gold dust.
pack.push(make("obsidian-grain", 256, 256, (u, v) => {
  const g = fbm(u, v, 16, 16, 5, 3), fine = vnoise(u * 128, v * 128, 128, 128, 5);
  const dust = hash(Math.floor(u * 256), Math.floor(v * 256), 91) > 0.9975 ? 0.55 : 0;
  const k = 3 + g * 8 + fine * 3;
  return [k * 0.85 + dust * 150, k + dust * 115, k * 0.9 + dust * 40];
}, { role: "panel substrate; Vision background", tile: "repeat" }));

// Carbon weave: 2x2 twill of tows, each with a cylindrical highlight.
pack.push(make("carbon-weave", 64, 64, (u, v, x, y) => {
  const cell = 16, cx = Math.floor(x / cell), cy = Math.floor(y / cell), lx = (x % cell) / cell, ly = (y % cell) / cell;
  const warp = ((cx + cy) & 3) < 2;                       // twill diagonal
  const across = warp ? ly : lx, along = warp ? lx : ly;
  const cyl = Math.sin(across * Math.PI);                 // tow cross-section
  const fibre = vnoise(along * 4 + cx * 7, across * 24, 4 * 4 + 64, 24, 13) * 0.35;
  const k = 7 + cyl * 16 + fibre * 10 - (warp ? 0 : 3);
  return [k, k * 1.04, k * 1.02];
}, { role: "control surfaces (buttons, chips); Vision region backing", tile: "repeat" }));

// Glass sheen: soft diagonal bands with alpha, for glazing over dark surfaces.
pack.push(make("glass-sheen", 256, 256, (u, v) => {
  const d = u + v, band = Math.pow(0.5 + 0.5 * Math.cos(d * Math.PI * 2), 6), band2 = Math.pow(0.5 + 0.5 * Math.cos((d * 3 + 0.3) * Math.PI * 2), 16) * 0.5;
  const n = fbm(u, v, 4, 4, 3, 41) * 0.25;
  return [255, 244, 214, (band * 0.75 + band2 + n * 0.3) * 46];
}, { role: "glass glaze over Vision regions", tile: "repeat", alpha: true }));

// Quad-diamond lattice: the QuadCOM diamond as a fine gold line lattice, with alpha.
pack.push(make("quad-lattice", 64, 64, (u, v) => {
  const a = Math.abs(((u + v) * 2) % 1 - 0.5), b = Math.abs(((u - v + 1) * 2) % 1 - 0.5);
  const line = Math.max(Math.exp(-Math.pow((0.5 - a) * 64, 2)), Math.exp(-Math.pow((0.5 - b) * 64, 2)));
  const node = Math.exp(-(Math.pow((a - 0.5) * 20, 2) + Math.pow((b - 0.5) * 20, 2)));
  return [230, 184, 78, Math.min(255, line * 38 + node * 70)];
}, { role: "Vision background lattice", tile: "repeat", alpha: true }));

writeFileSync(join(OUT, "pack.json"), JSON.stringify({
  name: "AURUM", version: "45.0", generator: "tools/texture-pack.mjs", license: "Generated for QuadCOM; free to use with this project.",
  note: "All textures tile seamlessly. Colour tokens follow the V43 palette (gold #d9ad45, hi #f3d477, mint #92d7b7, red #e47f70).",
  textures: pack,
}, null, 2) + "\n");
console.log(pack.map(p => `${p.file} ${p.width}x${p.height}`).join("\n"));

/* ════════════════ REGALIA skin pack ════════════════
 * Ornate layer: mandala watermarks,
 * art-deco corners, filigree bands, starburst cells and a kaleidoscope
 * substrate in gold with magenta and teal glints. Line art is supersampled
 * 3x3 for clean anti-aliasing. Alpha is baked low so the skin never competes
 * with data ink.
 */
const SV = join(OUT, "regalia");
mkdirSync(SV, { recursive: true });
const G_ = [217, 173, 69], GH = [246, 217, 120], MAG = [196, 58, 150], TEAL = [52, 190, 180];
const lineAA = (d, w) => Math.max(0, 1 - Math.abs(d) / w);          // d and w in normalized units
function over(dst, rgb, a) { const k = a * (1 - dst[3]); dst[0] += rgb[0] * k; dst[1] += rgb[1] * k; dst[2] += rgb[2] * k; dst[3] += k; }
// Supersampled RGBA maker. fn(x, y) → list of [rgb, alpha] layers, front first.
function makeSS(dir, name, w, h, fn, meta, ss = 3) {
  const buf = Buffer.alloc(w * h * 4);
  for (let py = 0; py < h; py++) for (let px = 0; px < w; px++) {
    let r = 0, g = 0, b = 0, a = 0;
    for (let sy = 0; sy < ss; sy++) for (let sx = 0; sx < ss; sx++) {
      const acc = [0, 0, 0, 0];
      for (const [rgb, al] of fn((px + (sx + 0.5) / ss) / w, (py + (sy + 0.5) / ss) / h)) { if (al > 0) over(acc, rgb, Math.min(1, al)); if (acc[3] > 0.995) break; }
      r += acc[0]; g += acc[1]; b += acc[2]; a += acc[3];
    }
    const n = ss * ss, o = (py * w + px) * 4, A = a / n;
    buf[o] = A ? Math.round(r / n / A) : 0; buf[o + 1] = A ? Math.round(g / n / A) : 0; buf[o + 2] = A ? Math.round(b / n / A) : 0; buf[o + 3] = Math.round(A * 255);
  }
  writeFileSync(join(dir, `${name}.png`), png(w, h, buf));
  return { file: `regalia/${name}.png`, width: w, height: h, ...meta };
}
const svPack = [];

// Mandala watermark: 16-fold kaleidoscope (gold rings, magenta/teal petals, gold diamond heart).
svPack.push(makeSS(SV, "mandala", 512, 512, (u, v) => {
  const x = u * 2 - 1, y = v * 2 - 1, r = Math.hypot(x, y), th = Math.atan2(y, x);
  if (r > 1) return [];
  const fold = 16, f = th / (Math.PI * 2 / fold), a = Math.abs((((f % 1) + 1) % 1) - 0.5) * 2, par = ((Math.floor(f) % 2) + 2) % 2;
  const L = [], fade = Math.pow(1 - r, 0.35);
  const dia = Math.abs(x) + Math.abs(y);
  if (dia < 0.13) { const s = 1 - dia / 0.13; L.push([GH.map((c, i) => c * (0.6 + 0.4 * s) + G_[i] * 0) , 0.62]); }
  L.push([GH, lineAA(dia - 0.15, 0.008) * 0.8]);
  L.push([G_, lineAA(Math.max(Math.abs(x), Math.abs(y)) - 0.11, 0.006) * 0.55]);
  for (const [rr, al] of [[0.2, 0.6], [0.34, 0.45], [0.56, 0.5], [0.8, 0.42], [0.96, 0.5]]) L.push([G_, lineAA(r - rr, 0.0065) * al]);
  const pr = (r - 0.2) / 0.3;                                          // inner petals 0.2..0.5
  if (pr > 0 && pr < 1) { const edge = 0.95 * Math.sin(Math.PI * pr); const d = a - edge; if (d < 0) L.push([par ? MAG : TEAL, 0.34 * (0.4 + 0.6 * (1 - a / Math.max(edge, 1e-3)))]); L.push([G_, lineAA(d, 0.02) * 0.6]); }
  const sp = (r - 0.56) / 0.24;                                         // outer spear petals 0.56..0.8
  if (sp > 0 && sp < 1) { const edge = 0.6 * (1 - sp) * Math.sin(Math.PI * Math.min(1, sp * 2.2)); const aa = Math.abs(a - (par ? 0 : 1)); const d = aa - edge; if (d < 0) L.push([par ? TEAL : MAG, 0.22]); L.push([GH, lineAA(d, 0.018) * 0.55]); }
  if (r > 0.34 && r < 0.96) L.push([G_, lineAA(a * (Math.PI * 2 / fold) * r / 2, 0.0045) * 0.35]);   // spokes
  const dotR = Math.hypot(r - 0.62, (1 - a) * Math.PI * 2 / fold * 0.62 / 2); L.push([GH, (dotR < 0.014 ? 0.75 : 0)]);
  const scal = 0.86 + 0.035 * Math.cos(th * fold * 2); L.push([G_, lineAA(r - scal, 0.006) * 0.5]);          // lace scallop
  if (r > 0.56 && r < 0.8) L.push([G_, lineAA(Math.sin(th * 48) * 0.01 + (r - 0.68) * 0.25, 0.0025) * 0.35]);
  return L.map(([c, al]) => [c, al * fade * 0.55]);
}, { role: "panel watermark (centered, contain)", alpha: true }));

// Art-deco corner (top-left orientation; CSS gets the other three as separate files).
const cornerFn = (u, v) => {
  const L = [], x = u, y = v;
  const lines = [[0.06, 0.95], [0.16, 0.7], [0.26, 0.45]];                // offset, length
  for (const [o, len] of lines) {
    if (x < len) L.push([GH, lineAA(y - o, 0.034) * (1.05 - o) * (1 - x / len * 0.5)]);
    if (y < len) L.push([GH, lineAA(x - o, 0.034) * (1.05 - o) * (1 - y / len * 0.5)]);
  }
  const step = Math.max(Math.abs(x - 0.36), Math.abs(y - 0.36)); L.push([GH, lineAA(step - 0.07, 0.026) * 0.95]);
  const d = Math.abs(x - 0.36) + Math.abs(y - 0.36); if (d < 0.06) L.push([MAG, 0.95]);
  return L;
};
const flips = { tl: (u, v) => [u, v], tr: (u, v) => [1 - u, v], bl: (u, v) => [u, 1 - v], br: (u, v) => [1 - u, 1 - v] };
for (const k of Object.keys(flips)) svPack.push(makeSS(SV, `corner-${k}`, 64, 64, (u, v) => cornerFn(...flips[k](u, v)), { role: `panel corner ${k}`, alpha: true }));

// Filigree band: diamond chain with double rails and magenta jewels, tiles horizontally (period 64).
svPack.push(makeSS(SV, "filigree-band", 256, 32, (u, v) => {
  const x = (u * 256) % 64 / 64, y = v, L = [];
  const dia = Math.abs(x - 0.5) * 0.5 + Math.abs(y - 0.5);
  L.push([MAG, dia < 0.09 ? 0.8 : 0]);
  L.push([GH, lineAA(dia - 0.16, 0.025) * 0.85]);
  L.push([G_, lineAA(dia - 0.3, 0.02) * 0.5]);
  for (const ry of [0.2, 0.8]) if (Math.abs(x - 0.5) > 0.2) L.push([G_, lineAA(y - ry, 0.03) * 0.6]);
  const sc = Math.hypot((x < 0.5 ? x : 1 - x) - 0.1, y - 0.5); L.push([G_, lineAA(sc - 0.07, 0.02) * 0.55]);
  return L.map(([c, a]) => [c, a * 0.6]);
}, { role: "command bar and panel header band", tile: "repeat-x", alpha: true }));

// Starburst: 24 rays, ring and diamond, for instrument cells.
svPack.push(makeSS(SV, "starburst", 256, 256, (u, v) => {
  const x = u * 2 - 1, y = v * 2 - 1, r = Math.hypot(x, y), th = Math.atan2(y, x), L = [];
  if (r > 1) return [];
  const ray = Math.abs(Math.sin(th * 12)), fall = Math.pow(1 - r, 1.6);
  L.push([GH, (ray < 0.06 + 0.04 * (1 - r) ? 0.5 : 0) * fall]);
  L.push([MAG, (Math.abs(Math.sin(th * 12 + Math.PI / 2)) < 0.03 ? 0.25 : 0) * fall]);
  L.push([G_, lineAA(r - 0.38, 0.01) * 0.45]);
  L.push([GH, lineAA(Math.abs(x) + Math.abs(y) - 0.2, 0.012) * 0.7]);
  L.push([TEAL, lineAA(Math.abs(x) + Math.abs(y) - 0.11, 0.01) * 0.45]);
  return L.map(([c, a]) => [c, a * 0.5]);
}, { role: "instrument cell motif (centered)", alpha: true }));

// Kaleidoscope substrate: opaque, tileable diamond field (period 64 → tiles in 256).
svPack.push(makeSS(SV, "kaleido-tile", 256, 256, (u, v) => {
  const X = u * 4, Y = v * 4, fx = X % 1, fy = Y % 1, cx = Math.floor(X), cy = Math.floor(Y);
  const d = Math.abs(fx - 0.5) + Math.abs(fy - 0.5), L = [];
  L.push([G_, lineAA(d - 0.5, 0.012) * 0.28]);
  L.push([G_, lineAA(d - 0.3, 0.008) * 0.16]);
  const star = Math.min(Math.abs(fx - 0.5), Math.abs(fy - 0.5)) + d * 0.35; L.push([GH, (star < 0.035 && d < 0.2 ? 0.35 : 0)]);
  const gl = hash(((cx % 4) + 4) % 4, ((cy % 4) + 4) % 4, 77); if (d < 0.06) L.push([gl > 0.5 ? MAG : TEAL, 0.35]);
  const n = vnoise(u * 32, v * 32, 32, 32, 9);
  L.push([[4 + n * 6, 5 + n * 6, 5 + n * 5], 1]);
  return L;
}, { role: "desk substrate behind panels", tile: "repeat" }, 2));

writeFileSync(join(SV, "pack.json"), JSON.stringify({ name: "REGALIA", version: "46.0", generator: "tools/texture-pack.mjs", note: "Skin only: ornament, no text. Gold #d9ad45/#f6d978, magenta #c43a96, teal #34beb4.", textures: svPack }, null, 2) + "\n");
console.log(svPack.map(p => `${p.file} ${p.width}x${p.height}`).join("\n"));
