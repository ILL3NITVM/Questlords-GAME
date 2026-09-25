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
