/* QuadCOM ❖ GLIMMER — hardware compute governor (V44)
 *
 *   AVAILABLE HEADROOM → GLIMMER → USEFUL COMPUTE
 *
 * GLIMMER sits between the desk and the device. It probes what the browser
 * legitimately exposes, measures how healthy the page is, and converts spare,
 * safe headroom into QuadCOM output (trade odds, risk cones, parameter sweeps,
 * fleet correlation). When the page starts paying for that work in frame time,
 * event-loop delay, memory faults, GPU faults or lifecycle interruptions, it
 * gives the resource back.
 *
 * Rules this file keeps:
 *  - WebGPU is the browser path toward Metal-class GPUs. It is never reported
 *    as native Metal access.
 *  - Nothing the browser does not expose is invented: no temperatures, wattage,
 *    VRAM, GPU % or CPU package metrics. Pressure is inferred and labelled so.
 *  - No hidden hardware identifiers are read (no adapter vendor/renderer strings).
 *  - Acceleration is an optimisation layer. Every workload has a CPU path, and
 *    the degradation order is fixed per workload kind.
 */
(() => {
'use strict';

const VERSION = '45.0';
const STORE = 'quadcom-v44-glimmer';
const WASM_B64 = 'AGFzbQEAAAABEQJgA39/fwF9YAZ/f39/f38AAwMCAAEFAwEAAQcaAwZtZW1vcnkCAANkb3QAAAdkb3RNYW55AAEKkgECWgIBewF/IAAgAkECdGohBAJAA0AgACAETw0BIAMgAP0ABAAgAf0ABAD95gH95AEhAyAAQRBqIQAgAUEQaiEBDAALCyAD/R8AIAP9HwGSIAP9HwKSIAP9HwOSCzUBAX8CQANAIAYgA08NASAFIAAgASAEEAA4AgAgBUEEaiEFIAEgAmohASAGQQFqIQYMAAsLCw=='; // tools/glimmer-wasm.mjs

const CLASSES = ['P1', 'P2', 'P3'];               // P0 (interactive) belongs to the desk; GLIMMER only yields to it
const TICK_MS = 500;
const BASE_DT = 5;                                 // resample step for price history, seconds
const MAX_STEPS = 720;                             // per simulated path
const NB = 64;                                     // histogram bins per distribution
const CONE_HORIZONS = [12 * 60, 60 * 60, 4 * 60 * 60];
const CONE_TARGET = 2_000_000;                     // effective paths per history epoch; beyond this, extra paths add little
const SWEEP_EVERY = 30_000, CORR_EVERY = 60_000, ODDS_EVERY = 5_000;
// Duty-cycle ceilings at 100% envelope (ms of busy time per wall second).
const CAP = { gpu: 300, worker: 750, main: 60 };
// Slice targets per backend: coarse jobs, but short enough to yield.
const SLICE_MS = { gpu: 14, gl2: 40, worker: 60, main: 4 };
// Fixed degradation chains. Deterministic: first usable backend wins.
const CHAINS = { mc: ['gpu', 'gl2', 'worker', 'main'], sweep: ['gpu', 'worker', 'main'], corr: ['worker', 'main'] };
// Below these sizes the upload/dispatch/readback overhead outweighs GPU parallelism.
const GPU_MIN_WORK = { mc: 262_144, sweep: 131_072 };

const t = () => performance.now();
const wall = () => Date.now();
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const yieldToUI = () => new Promise(r => { const c = new MessageChannel(); c.port1.onmessage = () => r(); c.port2.postMessage(0); });
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const pct = x => Number.isFinite(x) ? `${(x * 100).toFixed(x < 0.1 ? 1 : 0)}%` : '—';
const ms = x => Number.isFinite(x) ? `${x < 10 ? x.toFixed(1) : Math.round(x)}ms` : '—';
const emit = (type, detail) => { try { dispatchEvent(new CustomEvent(`glimmer:${type}`, { detail })); } catch (_) {} };

/* ───────────────────────── shared kernels ─────────────────────────
 * Stringified into workers and also called on the main thread, so every CPU
 * backend runs the same code. WGSL/GLSL versions mirror it line for line.
 */
function glimmerKernels() {
  'use strict';
  const pcg = v => {
    const s = (Math.imul(v >>> 0, 747796405) + 2891336453) >>> 0;
    const w = Math.imul((s >>> ((s >>> 28) + 4)) ^ s, 277803737) >>> 0;
    return ((w >>> 22) ^ w) >>> 0;
  };
  const bin = (z, nb) => { const b = Math.floor((z + 1) * 0.5 * nb); return b < 0 ? 0 : b >= nb ? nb - 1 : b; };
  const binD = (z, nb) => { const b = Math.floor(z * nb); return b < 0 ? 0 : b >= nb ? nb - 1 : b; };

  // Block-bootstrap Monte Carlo. Records terminal log-return at three
  // checkpoints, full-path max drawdown and TP/SL first passage.
  // hist layout: [c0 bins | c1 bins | c2 bins | mdd bins | neither, tp, sl, pad]
  function mcTally(p, x0, x1, x2, mdd, hit, hist) {
    const nb = p.nb;
    hist[bin(x0 / p.h0, nb)]++; hist[nb + bin(x1 / p.h1, nb)]++; hist[2 * nb + bin(x2 / p.h2, nb)]++;
    hist[3 * nb + binD(mdd / p.h2, nb)]++; hist[4 * nb + hit]++;
  }
  function mc(p, from, count, hist) {
    const r = p.returns, R = r.length;
    for (let i = from; i < from + count; i++) {
      let st = pcg((p.seed ^ pcg(i)) >>> 0), j = 0, x = 0, peak = 0, mdd = 0, hit = 0, x0 = 0, x1 = 0, x2 = 0;
      for (let s = 0; s < p.steps; s++) {
        if (s % p.block === 0) { st = pcg(st); j = st % R; } else if (++j >= R) j = 0;
        x += r[j] * p.scale;
        if (x > peak) peak = x;
        if (peak - x > mdd) mdd = peak - x;
        if (hit === 0) { const v = p.side * x; if (v >= p.tp) hit = 1; else if (v <= -p.sl) hit = 2; }
        if (s + 1 === p.c0) x0 = x; if (s + 1 === p.c1) x1 = x; if (s + 1 === p.c2) x2 = x;
      }
      mcTally(p, x0, x1, x2, mdd, hit, hist);
    }
    return hist;
  }

  // Momentum / reversion parameter sweep with a train/holdout split.
  // out[k*4..] = [train Sharpe, holdout Sharpe, holdout log-PnL, position changes]
  function sweep(p, from, count, out) {
    const y = p.y, T = y.length, nL = p.Ls.length, nT = p.Ths.length, per = nL * nT;
    const sr = (s, q, n) => { if (n < 2) return 0; const m = s / n; return m / Math.sqrt(Math.max(q / n - m * m, 1e-18)); };
    for (let c = from; c < from + count; c++) {
      const mode = (c / per) | 0, rem = c % per, L = p.Ls[(rem / nT) | 0] | 0, th = p.Ths[rem % nT];
      const norm = 1 / (p.sigma * Math.sqrt(L));
      let pos = 0, trS = 0, trQ = 0, trN = 0, hoS = 0, hoQ = 0, hoN = 0, trades = 0;
      for (let k = L; k + 1 < T; k++) {
        const m = (y[k] - y[k - L]) * norm;
        let sg = m > th ? 1 : m < -th ? -1 : 0;
        if (mode === 1) sg = -sg;
        const ch = Math.abs(sg - pos);
        if (ch > 0) trades++;
        const ret = sg * (y[k + 1] - y[k]) - p.cost * ch;
        pos = sg;
        if (k + 1 < p.split) { trS += ret; trQ += ret * ret; trN++; } else { hoS += ret; hoQ += ret * ret; hoN++; }
      }
      const o = (c - from) * 4;
      out[o] = sr(trS, trQ, trN) * p.ann; out[o + 1] = sr(hoS, hoQ, hoN) * p.ann; out[o + 2] = hoS; out[o + 3] = trades;
    }
    return out;
  }

  // Upper-triangle correlation of z-scored rows. `dotMany` is the Wasm SIMD
  // kernel when available; otherwise plain JS.
  function corr(p, from, count, acc, dotMany) {
    const Z = p.Z, N = p.N, K = p.K;
    const row = new Float32Array(N);
    for (let i = from; i < from + count && i < N; i++) {
      const n = N - i - 1;
      if (n <= 0) continue;
      if (dotMany) dotMany(i, i + 1, n, row);
      else for (let j = i + 1; j < N; j++) { let s = 0; const a = i * K, b = j * K; for (let k = 0; k < K; k++) s += Z[a + k] * Z[b + k]; row[j - i - 1] = s; }
      for (let q = 0; q < n; q++) {
        const d = row[q], a = Math.abs(d);
        acc.sumSq += d * d; acc.sumAbs += a; acc.pairs++;
        acc.rowAbs[i] += a; acc.rowAbs[i + 1 + q] += a;
      }
    }
    return acc;
  }
  return { pcg, mc, mcTally, sweep, corr };
}
const K = glimmerKernels();

/* WebGL2 transform-feedback version of `mc`, used inside OffscreenCanvas
 * workers when WebGPU is absent. Stringified into the worker. */
function glimmerGL2() {
  const VS = `#version 300 es
precision highp float;precision highp int;precision highp sampler2D;
uniform sampler2D uR;uniform int uW;uniform uint uLen,uSteps,uSeed,uBlock,uC0,uC1,uC2,uOff;uniform float uScale,uSide,uTp,uSl;
out vec4 vX;out float vHit;
uint pcg(uint v){uint s=v*747796405u+2891336453u;uint w=((s>>((s>>28u)+4u))^s)*277803737u;return (w>>22u)^w;}
float ret(uint j){int k=int(j);return texelFetch(uR,ivec2(k%uW,k/uW),0).r;}
void main(){uint i=uint(gl_VertexID)+uOff;uint st=pcg(uSeed^pcg(i));uint j=0u;float x=0.,pk=0.,mdd=0.,hit=0.,x0=0.,x1=0.,x2=0.;
for(uint s=0u;s<uSteps;s++){if(s%uBlock==0u){st=pcg(st);j=st%uLen;}else{j++;if(j>=uLen)j=0u;}
x+=ret(j)*uScale;pk=max(pk,x);mdd=max(mdd,pk-x);
if(hit==0.){float v=uSide*x;if(v>=uTp)hit=1.;else if(v<=-uSl)hit=2.;}
if(s+1u==uC0)x0=x;if(s+1u==uC1)x1=x;if(s+1u==uC2)x2=x;}
vX=vec4(x0,x1,x2,mdd);vHit=hit;gl_Position=vec4(0.);gl_PointSize=1.;}`;
  const FS = `#version 300 es
precision mediump float;out vec4 o;void main(){o=vec4(0.);}`;
  let gl = null, prog = null, loc = null, tex = null, tfb = null, buf = null, bufPaths = 0, retKey = null, lost = false;
  function init() {
    try {
      if (typeof OffscreenCanvas !== 'function') return false;
      const c = new OffscreenCanvas(1, 1);
      c.addEventListener('webglcontextlost', e => { e.preventDefault(); lost = true; });
      gl = c.getContext('webgl2', { antialias: false, depth: false, stencil: false, powerPreference: 'default' });
      if (!gl) return false;
      const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw Error(gl.getShaderInfoLog(s)); return s; };
      prog = gl.createProgram();
      gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
      gl.transformFeedbackVaryings(prog, ['vX', 'vHit'], gl.INTERLEAVED_ATTRIBS);
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw Error(gl.getProgramInfoLog(prog));
      loc = {};
      for (const n of ['uR', 'uW', 'uLen', 'uSteps', 'uSeed', 'uBlock', 'uC0', 'uC1', 'uC2', 'uOff', 'uScale', 'uSide', 'uTp', 'uSl']) loc[n] = gl.getUniformLocation(prog, n);
      tex = gl.createTexture(); tfb = gl.createTransformFeedback();
      gl.bindVertexArray(gl.createVertexArray());
      return true;
    } catch (_) { gl = null; return false; }
  }
  function run(p, from, count, hist, K) {
    if (!gl || lost || gl.isContextLost()) { lost = true; throw Error('gl2 context lost'); }
    gl.useProgram(prog);
    if (retKey !== p.key) {
      const R = p.returns.length, W = Math.min(R, 2048), H = Math.ceil(R / W), data = new Float32Array(W * H);
      data.set(p.returns);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.R32F, W, H, 0, gl.RED, gl.FLOAT, data);
      gl.uniform1i(loc.uW, W);
      retKey = p.key;
    }
    if (bufPaths < count) {
      if (buf) gl.deleteBuffer(buf);
      buf = gl.createBuffer(); gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, buf);
      gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER, count * 20, gl.STREAM_READ); bufPaths = count;
      gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER, null);
    }
    gl.uniform1i(loc.uR, 0); gl.uniform1ui(loc.uLen, p.returns.length); gl.uniform1ui(loc.uSteps, p.steps);
    gl.uniform1ui(loc.uSeed, p.seed >>> 0); gl.uniform1ui(loc.uBlock, p.block); gl.uniform1ui(loc.uC0, p.c0);
    gl.uniform1ui(loc.uC1, p.c1); gl.uniform1ui(loc.uC2, p.c2); gl.uniform1ui(loc.uOff, from);
    gl.uniform1f(loc.uScale, p.scale); gl.uniform1f(loc.uSide, p.side); gl.uniform1f(loc.uTp, p.tp); gl.uniform1f(loc.uSl, p.sl);
    gl.enable(gl.RASTERIZER_DISCARD);
    gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK, tfb);
    gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, buf);
    gl.beginTransformFeedback(gl.POINTS); gl.drawArrays(gl.POINTS, 0, count); gl.endTransformFeedback();
    gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER, 0, null);
    gl.disable(gl.RASTERIZER_DISCARD);
    const out = new Float32Array(count * 5);
    gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.getBufferSubData(gl.ARRAY_BUFFER, 0, out); gl.bindBuffer(gl.ARRAY_BUFFER, null);
    if (gl.getError() !== gl.NO_ERROR) throw Error('gl2 error');
    for (let i = 0; i < count; i++) { const o = i * 5; K.mcTally(p, out[o], out[o + 1], out[o + 2], out[o + 3], out[o + 4] | 0, hist); }
    return hist;
  }
  return { init, run, get ok() { return !!gl && !lost; } };
}

/* ───────────────────────── state ───────────────────────── */
const G = {
  version: VERSION,
  caps: { probed: false },
  health: {
    state: 'GREEN', pending: 'GREEN', streak: 0, envelope: 0.15, frameMs: 0, p50: 0, p95: 0, nominal: 16.67, hz: 60,
    missRate: 0, loopLag: 0, longTaskMs: 0, lastInput: -Infinity, settleUntil: 0, memFaultAt: -Infinity, gpuFaultAt: -Infinity,
    pressure: 'NORMAL', osPressure: null, battery: null, since: { AMBER: 0, RED: 0 }, reasons: [],
  },
  budget: { gpu: 0, worker: 0, main: 0, used: [], allowed: [], use: 0 },
  queue: { P1: [], P2: [], P3: [] }, running: new Set(), seq: 1,
  perf: {},                                          // `${kind}:${backend}` -> {unitMs, best, n}
  results: {}, data: { epoch: 0, key: '', series: null, builtAt: 0, histLen: 0 },
  plan: null, lastWall: wall(), suspended: false, stale: 0, memScale: 1, log: [],
};

function note(msg) { G.log.push(`${new Date().toISOString().slice(11, 19)} ${msg}`); if (G.log.length > 40) G.log.shift(); }

/* ───────────────────────── capability probe ─────────────────────────
 * Only what the browser exposes, only what scheduling needs. */
function probeSync() {
  const c = G.caps;
  const has = (o, k) => { try { return !!o && k in o; } catch (_) { return false; } };
  c.webgpuApi = has(navigator, 'gpu');
  try { const cv = document.createElement('canvas'); const gl = cv.getContext('webgl2'); c.webgl2 = !!gl; gl?.getExtension('WEBGL_lose_context')?.loseContext(); } catch (_) { c.webgl2 = false; }
  c.wasm = typeof WebAssembly === 'object' && typeof WebAssembly.instantiate === 'function';
  try { c.wasmSimd = c.wasm && WebAssembly.validate(b64(WASM_B64)); } catch (_) { c.wasmSimd = false; }
  c.workers = typeof Worker === 'function';
  c.crossOriginIsolated = !!globalThis.crossOriginIsolated;
  c.sab = typeof SharedArrayBuffer === 'function' && c.crossOriginIsolated;
  c.offscreenCanvas = typeof OffscreenCanvas === 'function';
  c.offscreenTransfer = typeof HTMLCanvasElement === 'function' && 'transferControlToOffscreen' in HTMLCanvasElement.prototype;
  try { const ch = new MessageChannel(), ab = new ArrayBuffer(8); ch.port1.postMessage(ab, [ab]); c.transferables = ab.byteLength === 0; ch.port1.close(); ch.port2.close(); } catch (_) { c.transferables = false; }
  c.webCodecs = typeof VideoEncoder === 'function' || typeof VideoDecoder === 'function';
  c.webAudio = typeof AudioContext === 'function' || typeof webkitAudioContext === 'function';
  c.mediaCapabilities = has(navigator, 'mediaCapabilities');
  c.indexedDB = has(globalThis, 'indexedDB');
  c.cacheApi = has(globalThis, 'caches');
  c.serviceWorker = has(navigator, 'serviceWorker');
  c.opfs = !!navigator.storage?.getDirectory;
  c.idleCallback = typeof requestIdleCallback === 'function';
  c.longTask = (PerformanceObserver?.supportedEntryTypes || []).includes('longtask');
  c.pressureObserver = typeof PressureObserver === 'function';
  c.battery = typeof navigator.getBattery === 'function';
  c.jsHeap = !!performance.memory;                 // non-standard, Chromium only
  c.deviceMemory = navigator.deviceMemory ?? null; // coarse bucket, Chromium only
  c.logicalCores = navigator.hardwareConcurrency || null;
  c.dpr = devicePixelRatio || 1;
  c.network = navigator.connection ? { type: navigator.connection.effectiveType || null, saveData: !!navigator.connection.saveData } : null;
  c.online = navigator.onLine;
}

async function probeAsync() {
  const c = G.caps;
  try { if (navigator.storage?.estimate) { const e = await navigator.storage.estimate(); c.storage = { usage: e.usage ?? null, quota: e.quota ?? null }; } } catch (_) {}
  try { if (navigator.storage?.persisted) c.storagePersisted = await navigator.storage.persisted(); } catch (_) {}
  if (c.battery) {
    try {
      const b = await navigator.getBattery();
      const read = () => { G.health.battery = { level: b.level, charging: b.charging }; };
      read(); b.addEventListener('levelchange', read); b.addEventListener('chargingchange', read);
    } catch (_) { c.battery = false; }
  }
  if (c.pressureObserver) {
    try {
      const po = new PressureObserver(recs => { const r = recs[recs.length - 1]; if (r) G.health.osPressure = r.state; });
      await po.observe('cpu', { sampleInterval: 2000 });
    } catch (_) { c.pressureObserver = false; }
  }
  await gpuAcquire('probe');
  c.probed = true;
  emit('caps', c);
}

/* ───────────────────────── worker plan ─────────────────────────
 * hardwareConcurrency is a ceiling, not a licence. Reserve a share for
 * WebKit, rendering, input, networking and the OS. */
function makePlan() {
  const logical = navigator.hardwareConcurrency || 2;
  const reserve = Math.max(2, Math.round(logical * 0.34));
  const total = Math.max(1, logical - reserve);
  const coreWorkers = Math.min(2, total);
  const glimmerMax = G.caps.workers ? Math.max(1, Math.min(4, total - coreWorkers)) : 0;
  return { logical, reserve, total, coreWorkers, glimmerMax };
}

/* ───────────────────────── health monitor ───────────────────────── */
const frames = new Float32Array(180); let fIdx = 0, fCount = 0, lastFrameT = 0, frameMissFlags = new Uint8Array(180);
function frameSampler(ts) {
  if (!document.hidden) {
    if (lastFrameT) {
      const dt = ts - lastFrameT;
      if (dt > 0 && dt < 1000) {
        frames[fIdx] = dt; frameMissFlags[fIdx] = dt > G.health.nominal * 1.7 ? 1 : 0;
        fIdx = (fIdx + 1) % frames.length; fCount = Math.min(frames.length, fCount + 1);
      }
    }
    lastFrameT = ts;
  } else lastFrameT = 0;
  requestAnimationFrame(frameSampler);
}
function frameStats() {
  if (fCount < 20) return null;
  const a = Array.from(frames.subarray(0, fCount)).sort((x, y) => x - y);
  const p50 = a[Math.floor(a.length * 0.5)], p95 = a[Math.floor(a.length * 0.95)];
  // Snap nominal cadence to a real refresh interval (ProMotion devices run 120 Hz).
  const nominal = [8.33, 11.11, 16.67, 33.33].reduce((b, v) => Math.abs(v - p50) < Math.abs(b - p50) ? v : b, 16.67);
  let miss = 0; const recent = Math.min(fCount, 120);
  for (let k = 1; k <= recent; k++) miss += frameMissFlags[(fIdx - k + frames.length) % frames.length];
  return { p50, p95, nominal, missRate: miss / recent, last: frames[(fIdx - 1 + frames.length) % frames.length] };
}
let loopExpected = 0;
function loopProbe() {
  const now = t();
  if (loopExpected && !document.hidden) { const lag = Math.max(0, now - loopExpected); G.health.loopLag = G.health.loopLag * 0.8 + lag * 0.2; }
  loopExpected = now + 100; setTimeout(loopProbe, 100);
}
const longTasks = [];
function watchLongTasks() {
  if (!G.caps.longTask) return;
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) longTasks.push([e.startTime, e.duration]); }).observe({ type: 'longtask', buffered: false }); } catch (_) {}
}

const RANK = { GREEN: 0, AMBER: 1, RED: 2 };
function assessHealth() {
  const h = G.health, now = t(), fs = frameStats(), reasons = [];
  if (fs) { h.p50 = fs.p50; h.p95 = fs.p95; h.nominal = fs.nominal; h.hz = Math.round(1000 / fs.nominal); h.missRate = fs.missRate; h.frameMs = fs.last; }
  while (longTasks.length && longTasks[0][0] < now - 2000) longTasks.shift();
  h.longTaskMs = longTasks.reduce((s, x) => s + x[1], 0) / 2;
  let raw = 'GREEN';
  const red = (c, why) => { if (c) { raw = 'RED'; reasons.push(why); } };
  const amber = (c, why) => { if (c) { if (raw === 'GREEN') raw = 'AMBER'; reasons.push(why); } };
  red(document.hidden, 'hidden');
  red(G.suspended, 'suspended');
  if (fs) { red(fs.missRate > 0.25, 'frames missed'); red(fs.p95 > fs.nominal * 3, 'p95 frame'); }
  red(h.loopLag > 120, 'event-loop delay');
  red(now - h.memFaultAt < 10_000, 'memory fault');
  red(now - h.gpuFaultAt < 5_000, 'gpu fault');
  red(h.osPressure === 'critical', 'os pressure critical');
  if (fs) { amber(fs.missRate > 0.08, 'frames slipping'); amber(fs.p95 > fs.nominal * 1.8, 'p95 rising'); }
  amber(h.loopLag > 40, 'loop delay rising');
  amber(h.longTaskMs > 150, 'long tasks');
  amber(h.osPressure === 'serious', 'os pressure serious');
  amber(!!h.battery && !h.battery.charging && h.battery.level < 0.2, 'low battery');
  amber(!!G.caps.network?.saveData, 'save-data');
  // Hysteresis: worsen quickly, recover slowly.
  const cur = h.state;
  if (RANK[raw] > RANK[cur]) {
    if (raw === 'RED' || (h.pending === raw && ++h.streak >= 2)) { h.state = raw; h.streak = 0; }
    else if (h.pending !== raw) { h.pending = raw; h.streak = 1; }
  } else if (RANK[raw] < RANK[cur]) {
    const need = cur === 'RED' ? 6 : 8;
    if (h.pending === raw) { if (++h.streak >= need) { h.state = raw; h.streak = 0; } } else { h.pending = raw; h.streak = 1; }
  } else { h.pending = raw; h.streak = 0; }
  if (h.state !== cur) { note(`health ${cur}→${h.state}${reasons.length ? ' (' + reasons.join(', ') + ')' : ''}`); if (h.state !== 'GREEN') h.since[h.state] = now; }
  h.reasons = reasons;
  // Envelope: additive increase, multiplicative decrease, immediate stop on RED.
  if (h.state === 'GREEN') h.envelope = Math.min(1, h.envelope + 0.03);
  else if (h.state === 'AMBER') h.envelope = Math.max(0.05, h.envelope * 0.88);
  else h.envelope = 0;
  h.pressure = inferPressure();
  const cap = { HEADROOM: 1, NORMAL: 1, PRESSURE: 0.5, 'THROTTLED-LIKE': 0.2 }[h.pressure];
  if (h.battery && !h.battery.charging && h.battery.level < 0.2) h.envelope = Math.min(h.envelope, 0.3);
  h.envelope = Math.min(h.envelope, cap);
  if (h.state === 'RED') cancelClass('P3', 'health red');
}

/* Pressure is inferred from observed efficiency: when the same kernel on the
 * same backend takes persistently longer per unit of work than its best
 * observed rate, while the desk is not busier, the device is behaving as if
 * throttled. No temperature is read or claimed. */
function inferPressure() {
  const h = G.health, now = t();
  let eff = 1, n = 0;
  for (const k in G.perf) { const p = G.perf[k]; if (p.n >= 6 && p.best > 0 && now - p.at < 60_000) { eff = Math.max(eff, p.unitMs / p.best); n++; } }
  G.health.efficiency = n ? eff : null;
  const visible = !document.hidden;
  if (eff >= 1.9 || (visible && h.state === 'RED' && now - h.since.RED > 10_000)) return 'THROTTLED-LIKE';
  if (eff >= 1.35 || (h.state === 'AMBER' && now - h.since.AMBER > 15_000)) return 'PRESSURE';
  if (h.state === 'GREEN' && eff < 1.15) return 'HEADROOM';
  return 'NORMAL';
}
function recordPerf(kind, backend, units, elapsed) {
  if (!(units > 0) || !(elapsed > 0)) return;
  const k = `${kind}:${backend}`, u = elapsed / units * 1e6;  // ms per million units
  const p = G.perf[k] || (G.perf[k] = { unitMs: u, best: u, n: 0, at: 0 });
  p.unitMs = p.n ? p.unitMs * 0.8 + u * 0.2 : u;
  p.n++; p.at = t();
  if (p.n >= 3) p.best = Math.min(p.best * 1.0005, p.unitMs);  // best slowly relaxes so old records do not pin it
}

/* ───────────────────────── budget ───────────────────────── */
function refillBudget(dtSec) {
  const e = G.health.envelope, b = G.budget, nW = W.list.filter(w => w.ready).length;
  const allow = { gpu: e * CAP.gpu, worker: e * CAP.worker * Math.max(1, nW), main: e * CAP.main };
  for (const k in allow) b[k] = Math.min(allow[k], b[k] + allow[k] * dtSec);
  b.allowed.push([t(), (allow.gpu + allow.worker + allow.main) * dtSec]);
  const cut = t() - 5000;
  while (b.allowed.length && b.allowed[0][0] < cut) b.allowed.shift();
  while (b.used.length && b.used[0][0] < cut) b.used.shift();
  const A = b.allowed.reduce((s, x) => s + x[1], 0), U = b.used.reduce((s, x) => s + x[1], 0);
  b.use = A > 0 ? clamp(U / A, 0, 1) : 0;
}
function account(backend, elapsed, cls = 'P2') {
  const pool = backend === 'gl2' ? 'worker' : backend;
  if (!(pool in CAP) || !Number.isFinite(elapsed)) return;
  if (cls === 'P2' || cls === 'P3') { G.budget[pool] -= elapsed; G.budget.used.push([t(), elapsed]); }
}
function isIdle() { return t() - G.health.lastInput > 1500; }
function admit(cls, backend) {
  const h = G.health;
  if (document.hidden || G.suspended) return false;
  if (cls === 'P0' || cls === 'P1') return true;
  if (t() < h.settleUntil || h.state === 'RED' || h.envelope < 0.05) return false;
  if (cls === 'P3' && (h.state !== 'GREEN' || !isIdle() || h.envelope < 0.25)) return false;
  if (backend) { const pool = backend === 'gl2' ? 'worker' : backend; if ((G.budget[pool] ?? 0) <= 0) return false; }
  return true;
}

/* ───────────────────────── WebGPU backend ───────────────────────── */
const GPU = {
  state: 'PROBING', adapter: null, device: null, features: [], limits: {}, inflight: 0, lastMs: null, queueMs: null,
  strikes: 0, losses: 0, retryAt: 0, listeners: new Set(), acquiring: null, pipes: {}, bufs: {}, generation: 0,
};
const LIMIT_KEYS = ['maxComputeWorkgroupSizeX', 'maxComputeInvocationsPerWorkgroup', 'maxComputeWorkgroupsPerDimension', 'maxStorageBufferBindingSize', 'maxBufferSize'];

const WGSL_MC = `
struct P{R:u32,steps:u32,paths:u32,offset:u32,seed:u32,block:u32,nb:u32,c0:u32,c1:u32,c2:u32,q0:u32,q1:u32,scale:f32,side:f32,tp:f32,sl:f32,h0:f32,h1:f32,h2:f32,q2:f32};
@group(0) @binding(0) var<storage,read> ret:array<f32>;
@group(0) @binding(1) var<storage,read_write> hist:array<atomic<u32>>;
@group(0) @binding(2) var<uniform> p:P;
fn pcg(v:u32)->u32{let s=v*747796405u+2891336453u;let w=((s>>((s>>28u)+4u))^s)*277803737u;return (w>>22u)^w;}
fn bin(z:f32,nb:u32)->u32{return u32(clamp(i32(floor((z+1.0)*0.5*f32(nb))),0,i32(nb)-1));}
@compute @workgroup_size(64) fn main(@builtin(global_invocation_id) gid:vec3<u32>){
  if(gid.x>=p.paths){return;}
  let i=gid.x+p.offset;var st=pcg(p.seed^pcg(i));var j=0u;var x=0.0;var pk=0.0;var mdd=0.0;var hit=0u;var x0=0.0;var x1=0.0;var x2=0.0;
  for(var s=0u;s<p.steps;s++){
    if(s%p.block==0u){st=pcg(st);j=st%p.R;}else{j=j+1u;if(j>=p.R){j=0u;}}
    x=x+ret[j]*p.scale;pk=max(pk,x);mdd=max(mdd,pk-x);
    if(hit==0u){let v=p.side*x;if(v>=p.tp){hit=1u;}else if(v<=(-p.sl)){hit=2u;}}
    if(s+1u==p.c0){x0=x;} if(s+1u==p.c1){x1=x;} if(s+1u==p.c2){x2=x;}
  }
  let nb=p.nb;
  atomicAdd(&hist[bin(x0/p.h0,nb)],1u);atomicAdd(&hist[nb+bin(x1/p.h1,nb)],1u);atomicAdd(&hist[2u*nb+bin(x2/p.h2,nb)],1u);
  atomicAdd(&hist[3u*nb+u32(clamp(i32(floor(mdd/p.h2*f32(nb))),0,i32(nb)-1))],1u);atomicAdd(&hist[4u*nb+hit],1u);
}`;
const WGSL_SWEEP = `
struct S{T:u32,nL:u32,nT:u32,split:u32,count:u32,offset:u32,q0:u32,q1:u32,sigma:f32,cost:f32,ann:f32,q2:f32};
@group(0) @binding(0) var<storage,read> d:array<f32>;
@group(0) @binding(1) var<storage,read_write> outv:array<vec4<f32>>;
@group(0) @binding(2) var<uniform> p:S;
fn sr(s:f32,q:f32,n:f32)->f32{if(n<2.0){return 0.0;}let m=s/n;return m/sqrt(max(q/n-m*m,1e-18));}
@compute @workgroup_size(64) fn main(@builtin(global_invocation_id) gid:vec3<u32>){
  if(gid.x>=p.count){return;}
  let c=gid.x+p.offset;let per=p.nL*p.nT;let mode=c/per;let rem=c%per;
  let L=u32(d[p.T+rem/p.nT]);let th=d[p.T+p.nL+rem%p.nT];let norm=1.0/(p.sigma*sqrt(f32(L)));
  var pos=0.0;var trS=0.0;var trQ=0.0;var trN=0.0;var hoS=0.0;var hoQ=0.0;var hoN=0.0;var trades=0.0;
  for(var k=L;k+1u<p.T;k++){
    let m=(d[k]-d[k-L])*norm;var sg=select(select(0.0,-1.0,m<(-th)),1.0,m>th);if(mode==1u){sg=-sg;}
    let ch=abs(sg-pos);if(ch>0.0){trades=trades+1.0;}
    let r=sg*(d[k+1u]-d[k])-p.cost*ch;pos=sg;
    if(k+1u<p.split){trS=trS+r;trQ=trQ+r*r;trN=trN+1.0;}else{hoS=hoS+r;hoQ=hoQ+r*r;hoN=hoN+1.0;}
  }
  outv[gid.x]=vec4<f32>(sr(trS,trQ,trN)*p.ann,sr(hoS,hoQ,hoN)*p.ann,hoS,trades);
}`;

async function gpuAcquire(why) {
  if (GPU.acquiring) return GPU.acquiring;
  GPU.acquiring = (async () => {
    if (!navigator.gpu) { GPU.state = 'UNAVAILABLE'; return null; }
    try {
      const adapter = await Promise.race([navigator.gpu.requestAdapter({ powerPreference: 'high-performance' }), sleep(2500).then(() => null)]);
      if (!adapter) throw Error('no adapter');
      const device = await adapter.requestDevice();
      GPU.adapter = adapter; GPU.device = device; GPU.generation++;
      GPU.features = [...adapter.features].sort();
      GPU.limits = Object.fromEntries(LIMIT_KEYS.map(k => [k, adapter.limits[k]]));
      GPU.pipes = {}; GPU.bufs = {};
      const gen = GPU.generation;
      device.lost.then(info => onGpuLost(info, gen));
      device.addEventListener?.('uncapturederror', e => { G.health.gpuFaultAt = t(); note(`gpu uncaptured: ${String(e.error?.message || e.error).slice(0, 60)}`); });
      device.pushErrorScope('validation');
      GPU.pipes.mc = device.createComputePipeline({ layout: 'auto', compute: { module: device.createShaderModule({ code: WGSL_MC }), entryPoint: 'main' } });
      GPU.pipes.sweep = device.createComputePipeline({ layout: 'auto', compute: { module: device.createShaderModule({ code: WGSL_SWEEP }), entryPoint: 'main' } });
      const err = await device.popErrorScope();
      if (err) throw Error(`pipeline: ${err.message}`);
      GPU.state = 'READY'; GPU.strikes = 0;
      G.caps.webgpu = { features: GPU.features, limits: GPU.limits };
      note(`webgpu device ready (${why})`);
      if (why !== 'probe') for (const fn of GPU.listeners) { try { fn(device); } catch (_) {} }
      return { adapter, device };
    } catch (e) {
      GPU.device = null; GPU.state = 'UNAVAILABLE';
      G.caps.webgpu = G.caps.webgpu || null;
      note(`webgpu unavailable: ${String(e.message || e).slice(0, 60)}`);
      return null;
    } finally { GPU.acquiring = null; }
  })();
  return GPU.acquiring;
}
function onGpuLost(info, gen) {
  if (gen !== GPU.generation) return;
  GPU.device = null; GPU.pipes = {}; GPU.bufs = {}; GPU.inflight = 0;
  GPU.losses++; G.health.gpuFaultAt = t();
  note(`webgpu device lost: ${String(info?.message || info?.reason || '').slice(0, 60)}`);
  // Retry a bounded number of times; the desk keeps running on CPU meanwhile.
  GPU.state = GPU.losses <= 3 ? 'DEGRADED' : 'UNAVAILABLE';
  if (GPU.losses <= 3) GPU.retryAt = t() + 2000 * GPU.losses;
}
function gpuUsable() {
  return !!GPU.device && (GPU.state === 'READY' || GPU.state === 'BUSY' || GPU.state === 'DEGRADED') && GPU.inflight < 1 && t() > (GPU.coolUntil || 0);
}
function gpuStrike(why) {
  GPU.strikes++; G.health.gpuFaultAt = t(); note(`gpu strike ${GPU.strikes}: ${why}`);
  GPU.state = 'DEGRADED';
  if (GPU.strikes >= 3) { GPU.coolUntil = t() + 60_000; GPU.strikes = 0; note('gpu cooling down 60s; CPU backends take over'); }
}
function gpuBuffer(name, size, usage) {
  const d = GPU.device, cur = GPU.bufs[name];
  if (cur && cur.size >= size) return cur;
  cur?.destroy?.();
  const b = d.createBuffer({ size: Math.max(16, Math.ceil(size / 16) * 16), usage });
  GPU.bufs[name] = b; GPU.bufs[`${name}:bg`] = null;
  return b;
}
async function gpuDispatch(kind, p, from, count) {
  const d = GPU.device, SB = GPUBufferUsage, gen = GPU.generation;
  GPU.inflight++; GPU.state = 'BUSY';
  const t0 = t();
  let staging = null;
  try {
    d.pushErrorScope('out-of-memory'); d.pushErrorScope('validation');
    let outBytes, input, output, uni;
    if (kind === 'mc') {
      input = gpuBuffer('mcRet', p.returns.length * 4, SB.STORAGE | SB.COPY_DST);
      if (GPU.bufs.mcKey !== p.key || input !== GPU.bufs.mcRetLast) { d.queue.writeBuffer(input, 0, p.returns); GPU.bufs.mcKey = p.key; GPU.bufs.mcRetLast = input; }
      outBytes = (4 * p.nb + 4) * 4;
      output = gpuBuffer('mcHist', outBytes, SB.STORAGE | SB.COPY_SRC | SB.COPY_DST);
      uni = gpuBuffer('mcUni', 80, SB.UNIFORM | SB.COPY_DST);
      const ab = new ArrayBuffer(80), u = new Uint32Array(ab), f = new Float32Array(ab);
      u.set([p.returns.length, p.steps, count, from, p.seed >>> 0, p.block, p.nb, p.c0, p.c1, p.c2, 0, 0]);
      f.set([p.scale, p.side, p.tp, p.sl, p.h0, p.h1, p.h2, 0], 12);
      d.queue.writeBuffer(uni, 0, ab);
    } else {
      const T = p.y.length, nL = p.Ls.length, nT = p.Ths.length;
      input = gpuBuffer('swData', (T + nL + nT) * 4, SB.STORAGE | SB.COPY_DST);
      if (GPU.bufs.swKey !== p.key || input !== GPU.bufs.swLast) {
        const data = new Float32Array(T + nL + nT); data.set(p.y); data.set(p.Ls, T); data.set(p.Ths, T + nL);
        d.queue.writeBuffer(input, 0, data); GPU.bufs.swKey = p.key; GPU.bufs.swLast = input;
      }
      outBytes = count * 16;
      output = gpuBuffer('swOut', outBytes, SB.STORAGE | SB.COPY_SRC);
      uni = gpuBuffer('swUni', 48, SB.UNIFORM | SB.COPY_DST);
      const ab = new ArrayBuffer(48), u = new Uint32Array(ab), f = new Float32Array(ab);
      u.set([T, nL, nT, p.split, count, from, 0, 0]); f.set([p.sigma, p.cost, p.ann, 0], 8);
      d.queue.writeBuffer(uni, 0, ab);
    }
    const bgKey = `${kind}:bg`;
    let bg = GPU.bufs[bgKey];
    if (!bg || bg.input !== input || bg.output !== output) {
      bg = { group: d.createBindGroup({ layout: GPU.pipes[kind].getBindGroupLayout(0), entries: [{ binding: 0, resource: { buffer: input } }, { binding: 1, resource: { buffer: output } }, { binding: 2, resource: { buffer: uni } }] }), input, output };
      GPU.bufs[bgKey] = bg;
    }
    staging = d.createBuffer({ size: Math.ceil(outBytes / 16) * 16, usage: SB.MAP_READ | SB.COPY_DST });
    const enc = d.createCommandEncoder();
    if (kind === 'mc') enc.clearBuffer(output);
    const pass = enc.beginComputePass();
    pass.setPipeline(GPU.pipes[kind]); pass.setBindGroup(0, bg.group);
    pass.dispatchWorkgroups(Math.ceil(count / 64)); pass.end();
    enc.copyBufferToBuffer(output, 0, staging, 0, Math.ceil(outBytes / 4) * 4);
    d.queue.submit([enc.finish()]);
    const q0 = t();
    d.queue.onSubmittedWorkDone?.().then(() => { GPU.queueMs = t() - q0; }).catch(() => {});
    const [ve, oe] = await Promise.all([d.popErrorScope(), d.popErrorScope()]);
    if (oe) { G.health.memFaultAt = t(); G.memScale = Math.max(0.125, G.memScale * 0.5); throw Error(`gpu out-of-memory`); }
    if (ve) throw Error(`gpu validation: ${ve.message}`);
    // Never block the UI on GPU completion; bound the wait so a stuck kernel degrades instead of hanging.
    const limit = kind === 'mc' ? 2500 : 3000;
    const mapped = staging.mapAsync(GPUMapMode.READ).then(() => true);
    const ok = await Promise.race([mapped, sleep(limit).then(() => false)]);
    if (!ok) { gpuStrike(`${kind} exceeded ${limit}ms`); mapped.then(() => staging.destroy()).catch(() => {}); staging = null; throw Error('gpu slow'); }
    const raw = staging.getMappedRange().slice(0);
    staging.unmap();
    GPU.lastMs = t() - t0;
    return kind === 'mc' ? new Uint32Array(raw) : new Float32Array(raw, 0, count * 4);
  } catch (e) {
    if (gen === GPU.generation && GPU.device && !/slow/.test(e.message)) gpuStrike(e.message);
    throw e;
  } finally {
    staging?.destroy?.();
    GPU.inflight = Math.max(0, GPU.inflight - 1);
    if (GPU.state === 'BUSY') GPU.state = GPU.strikes ? 'DEGRADED' : 'READY';
  }
}

/* ───────────────────────── calibration ─────────────────────────
 * Each accelerated backend must reproduce the JS reference kernel on a small
 * fixed problem before it is trusted. f32 GPU arithmetic may move a handful
 * of paths across a bin edge, so the comparison is a tight tolerance rather
 * than bit equality. A backend that disagrees is excluded, never "fixed up". */
G.cal = { done: false };
function calProblem() {
  const R = 1024, returns = new Float32Array(R);
  for (let i = 0; i < R; i++) returns[i] = (K.pcg(i + 7) / 4294967296 - 0.5) * 0.002;
  let v = 0; for (const r of returns) v += r * r;
  const sd = Math.sqrt(v / R);
  const mc = { key: 'cal-mc', returns, steps: 128, block: 8, scale: 1, nb: NB, seed: 12345, c0: 32, c1: 64, c2: 128, side: 1, tp: 0.004, sl: 0.004, h0: 5 * sd * Math.sqrt(32), h1: 5 * sd * Math.sqrt(64), h2: 5 * sd * Math.sqrt(128) };
  const y = new Float32Array(512); for (let i = 1; i < y.length; i++) y[i] = y[i - 1] + returns[i];
  const sweep = { key: 'cal-sw', y, Ls: Float32Array.from([2, 4, 8, 16]), Ths: Float32Array.from([0, 0.4, 0.8]), split: 358, sigma: sd, cost: 1e-4, ann: 1 };
  return { mc, sweep, paths: 2048, combos: 24 };
}
const histClose = (a, b, paths) => { let d = 0; for (let i = 0; i < a.length; i++) d += Math.abs(a[i] - b[i]); return d / (5 * paths) < 0.02; };
const sweepClose = (a, b) => { for (let i = 0; i < b.length; i++) { const tol = i % 4 === 3 ? 2 : 0.02 + Math.abs(b[i]) * 0.02; if (!(Math.abs(a[i] - b[i]) <= tol)) return false; } return true; };
async function calibrate() {
  const P = calProblem(), cal = G.cal;
  const refMc = K.mc(P.mc, 0, P.paths, new Uint32Array(4 * NB + 4));
  const refSw = K.sweep(P.sweep, 0, P.combos, new Float32Array(P.combos * 4));
  if (GPU.device) {
    cal.gpu = {};
    try { const t0 = t(), o = await gpuDispatch('mc', P.mc, 0, P.paths); cal.gpu.mc = histClose(o, refMc, P.paths); cal.gpu.mcMs = t() - t0; } catch (e) { cal.gpu.mc = false; note(`calibration gpu mc: ${e.message}`); }
    try { const o = await gpuDispatch('sweep', P.sweep, 0, P.combos); cal.gpu.sweep = sweepClose(o, refSw); } catch (e) { cal.gpu.sweep = false; note(`calibration gpu sweep: ${e.message}`); }
  }
  for (let i = 0; i < 20 && !W.list.some(r => r.ready); i++) await sleep(100);
  const split = (params, names) => { const b = {}, sc = {}; for (const k in params) (names.includes(k) ? b : sc)[k] = params[k]; return [b, sc]; };
  let rec = idleWorker(false);
  if (rec) {
    try { const [b, sc] = split(P.mc, ['returns']); const m = await workerRun(rec, 'mc', P.mc.key, b, sc, 0, P.paths, false); cal.worker = histClose(m.out, refMc, P.paths); } catch (e) { cal.worker = false; }
    rec = idleWorker(true);
    if (rec) {
      try { const [b, sc] = split(P.mc, ['returns']); const m = await workerRun(rec, 'mc', P.mc.key, b, sc, 0, P.paths, true); cal.gl2 = m.engine === 'gl2' && histClose(m.out, refMc, P.paths); } catch (e) { cal.gl2 = false; }
      if (cal.gl2 === false) for (const r of W.list) r.gl2 = false;
    }
  }
  cal.done = true;
  note(`calibration: gpu ${cal.gpu ? `mc ${cal.gpu.mc ? 'ok' : 'FAIL'} sweep ${cal.gpu.sweep ? 'ok' : 'FAIL'}` : 'n/a'} · gl2 ${cal.gl2 ?? 'n/a'} · worker ${cal.worker ?? 'n/a'}`);
  if (cal.worker === false) { W.disabled = true; for (const r of W.list) r.w.terminate(); W.list = []; }
  emit('calibrated', cal);
  pump();
}
const calOk = (backend, kind) => backend === 'gpu' ? G.cal.gpu?.[kind] !== false : backend === 'gl2' ? G.cal.gl2 !== false : true;

/* ───────────────────────── worker pool ───────────────────────── */
const W = { list: [], url: null, crashes: [], disabled: false, seq: 1, lastGrow: 0 };
function workerSource() {
  return `'use strict';
const K=(${glimmerKernels.toString()})();
const GL=(${glimmerGL2.toString()})();
let wasm=null,data=new Map(),gl2=false;
function wasmDotMany(key,Kp,N){const m=wasm.exports.memory,need=N*Kp*4+N*4;if(m.buffer.byteLength<need)m.grow(Math.ceil((need-m.buffer.byteLength)/65536));
  if(wasm.loaded!==key){new Float32Array(m.buffer,0,N*Kp).set(data.get(key).Z);wasm.loaded=key}
  const outOff=N*Kp*4;return(i,j0,n,row)=>{wasm.exports.dotMany(i*Kp*4,j0*Kp*4,Kp*4,n,Kp,outOff);row.set(new Float32Array(m.buffer,outOff,n))}}
onmessage=async e=>{const m=e.data;
  if(m.type==='init'){if(m.wasm){try{const r=await WebAssembly.instantiate(m.wasm);wasm=r.instance}catch(_){wasm=null}}
    if(m.gl2)gl2=GL.init();postMessage({type:'ready',wasm:!!wasm,gl2});return}
  if(m.type==='ping'){postMessage({type:'pong'});return}
  if(m.type==='drop'){data.delete(m.key);if(wasm&&wasm.loaded===m.key)wasm.loaded=null;return}
  if(m.type!=='job')return;
  const t0=performance.now();
  try{
    if(m.payload)data.set(m.key,m.payload);
    const bulk=data.get(m.key);if(!bulk)throw Error('missing data '+m.key);
    const p=Object.assign({key:m.key},bulk,m.scalars);
    let out,engine='js';
    if(m.kind==='mc'){const hist=new Uint32Array(4*p.nb+4);if(m.useGL&&gl2&&GL.ok){GL.run(p,m.from,m.count,hist,K);engine='gl2'}else K.mc(p,m.from,m.count,hist);out=hist}
    else if(m.kind==='sweep'){out=K.sweep(p,m.from,m.count,new Float32Array(m.count*4))}
    else if(m.kind==='corr'){const acc={sumSq:0,sumAbs:0,pairs:0,rowAbs:new Float64Array(p.N)};let dm=null;if(wasm){dm=wasmDotMany(m.key,p.K,p.N);engine='wasm-simd'}K.corr(p,m.from,m.count,acc,dm);out=acc}
    const tr=out.buffer?[out.buffer]:out.rowAbs?[out.rowAbs.buffer]:[];
    postMessage({type:'done',id:m.id,out,engine,ms:performance.now()-t0},tr);
  }catch(err){if(/gl2/.test(String(err&&err.message)))gl2=false;postMessage({type:'fail',id:m.id,msg:String(err&&err.message||err),gl2})}
};`;
}
function spawnWorker() {
  if (W.disabled || !G.caps.workers) return null;
  try {
    W.url = W.url || URL.createObjectURL(new Blob([workerSource()], { type: 'text/javascript' }));
    const rec = { id: W.seq++, w: new Worker(W.url), ready: false, busy: false, job: null, keys: new Set(), wasm: false, gl2: false, pong: t() };
    rec.w.onmessage = e => onWorkerMessage(rec, e.data);
    rec.w.onerror = e => { e.preventDefault?.(); workerCrash(rec, e.message || 'worker error'); };
    rec.w.onmessageerror = () => workerCrash(rec, 'message error');
    rec.w.postMessage({ type: 'init', wasm: G.caps.wasmSimd ? b64(WASM_B64) : null, gl2: G.caps.webgl2 && G.caps.offscreenCanvas });
    W.list.push(rec);
    return rec;
  } catch (e) { note(`worker spawn failed: ${e.message}`); W.disabled = true; return null; }
}
function onWorkerMessage(rec, m) {
  if (!m) return;
  if (m.type === 'ready') { rec.ready = true; rec.wasm = m.wasm; rec.gl2 = m.gl2; G.caps.workerWasmSimd = G.caps.workerWasmSimd || m.wasm; G.caps.workerWebGL2 = G.caps.workerWebGL2 || m.gl2; pump(); return; }
  if (m.type === 'pong') { rec.pong = t(); return; }
  const job = rec.job; rec.busy = false; rec.job = null;
  if (!job) return;
  if (m.type === 'fail') { if (m.gl2 === false) rec.gl2 = false; job.reject(Error(m.msg)); }
  else job.resolve(m);
  pump();
}
function workerCrash(rec, why) {
  note(`worker ${rec.id} crashed: ${String(why).slice(0, 50)}`);
  try { rec.w.terminate(); } catch (_) {}
  W.list = W.list.filter(x => x !== rec);
  rec.job?.reject(Error('worker crashed'));
  const now = t();
  W.crashes = W.crashes.filter(x => now - x < 60_000); W.crashes.push(now);
  if (W.crashes.length >= 3) { W.disabled = true; note('workers disabled after repeated crashes; main-thread JS takes over'); for (const r of W.list) { try { r.w.terminate(); } catch (_) {} r.job?.reject(Error('workers disabled')); } W.list = []; }
  else setTimeout(() => { if (W.list.length < 1) spawnWorker(); }, 1000 * W.crashes.length);
}
function idleWorker(needGL) { return W.list.find(r => r.ready && !r.busy && (!needGL || r.gl2)); }
function workerRun(rec, kind, key, bulk, scalars, from, count, useGL) {
  return new Promise((resolve, reject) => {
    const id = W.seq++;
    rec.busy = true; rec.job = { id, resolve, reject };
    const msg = { type: 'job', id, kind, key, scalars, from, count, useGL };
    // Bulk arrays cross the thread boundary once per worker; later slices send only scalars.
    if (!rec.keys.has(key)) { msg.payload = bulk; rec.keys.add(key); if (rec.keys.size > 6) { const old = rec.keys.values().next().value; rec.keys.delete(old); rec.w.postMessage({ type: 'drop', key: old }); } }
    rec.w.postMessage(msg);
  });
}
/* Grow slowly when healthy and work is waiting; shrink when the page is under strain. */
function tuneWorkers() {
  if (!G.plan || W.disabled) return;
  const h = G.health, now = t(), idle = W.list.filter(r => r.ready && !r.busy);
  const pending = G.queue.P1.length + G.queue.P2.length + G.queue.P3.length + G.running.size;
  if (W.list.length === 0 && G.plan.glimmerMax > 0) { spawnWorker(); W.lastGrow = now; return; }
  if (h.state === 'GREEN' && h.envelope > 0.6 && pending > W.list.length && W.list.length < G.plan.glimmerMax && now - W.lastGrow > 10_000) { spawnWorker(); W.lastGrow = now; note(`worker pool → ${W.list.length}`); }
  if ((h.state === 'RED' || h.pressure === 'THROTTLED-LIKE') && W.list.length > 1 && idle.length) {
    const r = idle[idle.length - 1]; r.w.terminate(); W.list = W.list.filter(x => x !== r); W.lastGrow = now; note(`worker pool → ${W.list.length}`);
  }
}

/* ───────────────────────── executor ─────────────────────────
 * Jobs are split into coarse slices sized from measured throughput, so a
 * lower-priority job can pause between slices and resume later. */
function backendFor(job) {
  for (const b of CHAINS[job.kind]) {
    if (job.failed.has(b) || !calOk(b, job.kind)) continue;
    if (b === 'gpu') { if (!GPU.device || GPU.state === 'UNAVAILABLE' || t() < (GPU.coolUntil || 0)) continue; if (job.work < GPU_MIN_WORK[job.kind]) continue; return gpuUsable() && admit(job.cls, 'gpu') ? 'gpu' : null; }
    if (b === 'gl2') { if (!G.caps.workerWebGL2 || job.work < GPU_MIN_WORK.mc || !W.list.some(r => r.gl2)) continue; return idleWorker(true) && admit(job.cls, 'gl2') ? 'gl2' : null; }
    if (b === 'worker') { if (W.disabled || !W.list.some(r => r.ready)) continue; return idleWorker(false) && admit(job.cls, 'worker') ? 'worker' : null; }
    if (b === 'main') {
      // Main-thread compute is a last resort: only when no worker exists, and never while frames slip.
      if (G.caps.workers && !W.disabled && W.list.length) continue;
      if (job.cls !== 'P1' && G.health.state !== 'GREEN') return null;
      return admit(job.cls, 'main') ? 'main' : null;
    }
  }
  return null;
}
function sliceSize(job, backend) {
  const p = G.perf[`${job.kind}:${backend}`];
  const perUnit = job.unitWork;                             // work units per slice unit (e.g. steps per path)
  const target = SLICE_MS[backend] * (job.cls === 'P1' ? 1.5 : 1);
  let n = p ? Math.floor(target / (p.unitMs / 1e6) / perUnit) : job.firstSlice[backend] || 1024;
  n = Math.floor(n * G.memScale);
  const cap = job.kind === 'mc' ? 262_144 : job.kind === 'sweep' ? 8192 : 64;
  return Math.min(job.total - job.done, cap, Math.max(job.kind === 'corr' ? 4 : 64, n));
}
async function runSlice(job, backend) {
  const from = job.done, count = sliceSize(job, backend), t0 = t();
  let out, engine = backend;
  if (backend === 'gpu') out = await gpuDispatch(job.kind, job.params, from, count);
  else if (backend === 'worker' || backend === 'gl2') {
    const rec = idleWorker(backend === 'gl2');
    if (!rec) throw Error('no idle worker');
    const bulk = {}, scalars = {};
    for (const k in job.params) (job.bulk.includes(k) ? bulk : scalars)[k] = job.params[k];
    const m = await workerRun(rec, job.kind, job.params.key, bulk, scalars, from, count, backend === 'gl2');
    out = m.out; engine = m.engine === 'gl2' ? 'gl2' : m.engine === 'wasm-simd' ? 'wasm-simd' : 'worker';
    if (backend === 'gl2' && m.engine !== 'gl2') engine = 'worker';
  } else {
    if (job.kind === 'mc') out = K.mc(job.params, from, count, new Uint32Array(4 * job.params.nb + 4));
    else if (job.kind === 'sweep') out = K.sweep(job.params, from, count, new Float32Array(count * 4));
    else { out = { sumSq: 0, sumAbs: 0, pairs: 0, rowAbs: new Float64Array(job.params.N) }; K.corr(job.params, from, count, out, null); }
    engine = 'js';
  }
  const elapsed = t() - t0;
  recordPerf(job.kind, backend, count * job.unitWork, elapsed);
  account(backend, elapsed, job.cls);
  job.merge(out, from, count);
  job.done += count; job.engines.add(engine); job.ms += elapsed;
}
async function execute(job) {
  G.running.add(job);
  job.started = job.started || t();
  try {
    while (job.done < job.total) {
      if (job.cancelled) throw Error('cancelled');
      const backend = backendFor(job);
      if (!backend) {
        // Nothing admitted right now: park the job with its progress and let the governor re-queue it.
        if (!job.chainAlive()) throw Error('no backend');
        job.parked = true; return;
      }
      try { await runSlice(job, backend); }
      catch (e) {
        if (job.cancelled) throw e;
        note(`${job.kind} slice on ${backend} failed: ${String(e.message).slice(0, 50)} → next backend`);
        job.fails[backend] = (job.fails[backend] || 0) + 1;
        if (backend !== 'worker' || W.disabled || job.fails[backend] >= 3) job.failed.add(backend);
        if (/memory|RangeError/i.test(e.message) || e instanceof RangeError) { G.health.memFaultAt = t(); G.memScale = Math.max(0.125, G.memScale * 0.5); }
      }
      if (backend === 'main') await yieldToUI();
    }
    job.parked = false;
    job.finish();
    // Chain the next useful job straight away while budget remains, instead of idling until the next tick.
    if (job.cls !== 'P1') setTimeout(produce, 0);
  } catch (e) {
    if (e.message !== 'cancelled') note(`${job.kind} ${job.cls} dropped: ${e.message}`);
    job.parked = false; job.dead = true;
  } finally {
    G.running.delete(job);
    if (job.parked && !job.cancelled) G.queue[job.cls].unshift(job);
    pump();
  }
}
function newJob(spec) {
  const job = Object.assign({ id: G.seq++, done: 0, ms: 0, engines: new Set(), failed: new Set(), fails: {}, cancelled: false, created: t(), firstSlice: {} }, spec);
  job.chainAlive = () => CHAINS[job.kind].some(b => !job.failed.has(b) && (b !== 'gpu' || (GPU.state !== 'UNAVAILABLE' && job.work >= GPU_MIN_WORK[job.kind])) && (b !== 'worker' || (!W.disabled && W.list.length)) && (b !== 'gl2' || W.list.some(r => r.gl2)));
  return job;
}
function submit(job) { G.queue[job.cls].push(job); pump(); return job; }
function queued(tag) {
  for (const j of G.running) if (j.tag === tag && !j.dead) return true;
  return CLASSES.some(c => G.queue[c].some(j => j.tag === tag && !j.cancelled));
}
function cancelClass(cls, why) {
  let n = 0;
  for (const j of G.queue[cls]) { j.cancelled = true; n++; }
  G.queue[cls] = [];
  for (const j of G.running) if (j.cls === cls) { j.cancelled = true; n++; }
  if (n) note(`cancelled ${n} ${cls} job(s): ${why}`);
}
let pumping = false;
function pump() {
  if (pumping) return; pumping = true;
  try {
    for (const cls of CLASSES) {
      const q = G.queue[cls];
      while (q.length) {
        const job = q[0];
        if (job.cancelled || job.dead) { q.shift(); continue; }
        if (!admit(cls)) break;
        if (!backendFor(job)) { if (!job.chainAlive()) { q.shift(); job.dead = true; note(`${job.kind} has no usable backend`); continue; } break; }
        q.shift(); job.parked = false; execute(job);
      }
    }
  } finally { pumping = false; }
}

/* ───────────────────────── data from the desk ───────────────────────── */
function feed() { try { const f = window.__quadcomGlimmerFeed?.(); return f && f.ready ? f : null; } catch (_) { return null; } }
function rebuildSeries(f) {
  const d = G.data;
  if (d.series && (f.histLen === d.histLen && f.histLast === d.histLast)) return d.series;
  if (d.series && t() - d.builtAt < 10_000) return d.series;
  let h;
  try { h = f.hist(); } catch (_) { return d.series; }
  const n = h.p.length;
  if (n < 30) return d.series;
  // Resample irregular ticks to a fixed grid; do not bridge recorded gaps.
  const dt = BASE_DT * 1000, t0 = h.t[0], t1 = h.t[n - 1], cells = Math.floor((t1 - t0) / dt);
  if (cells < 60) return d.series;
  const grid = new Float64Array(cells + 1), gapCell = new Uint8Array(cells + 1);
  let k = 0, last = h.p[0];
  for (let c = 0; c <= cells; c++) {
    const edge = t0 + c * dt;
    while (k < n && h.t[k] <= edge) { if (h.g[k]) gapCell[c] = 1; last = h.p[k]; k++; }
    grid[c] = last;
  }
  const rets = [];
  for (let c = 1; c <= cells; c++) if (!gapCell[c] && grid[c] > 0 && grid[c - 1] > 0) rets.push(Math.log(grid[c] / grid[c - 1]));
  if (rets.length < 60) return d.series;
  const returns = Float32Array.from(rets.slice(-8192));
  let m = 0; for (const r of returns) m += r; m /= returns.length;
  let v = 0; for (const r of returns) v += (r - m) ** 2;
  const sigma = Math.sqrt(v / Math.max(1, returns.length - 1)) || 1e-6;
  const y = new Float32Array(Math.min(grid.length, 4096)), off = grid.length - y.length;
  for (let i = 0; i < y.length; i++) y[i] = Math.log(grid[off + i] / grid[off]);
  d.epoch++; d.builtAt = t(); d.histLen = f.histLen; d.histLast = f.histLast;
  d.series = { epoch: d.epoch, key: `s${d.epoch}`, returns, sigma, y, spanMin: cells * BASE_DT / 60, price: f.price };
  return d.series;
}
function mcParams(s, horizons, side, tp, sl, seed) {
  const maxH = Math.max(...horizons), baseSteps = Math.ceil(maxH / BASE_DT), k = Math.max(1, Math.ceil(baseSteps / MAX_STEPS));
  const steps = Math.ceil(baseSteps / k), scale = Math.sqrt(k), sig = s.sigma * scale;
  const cs = horizons.map(h => clamp(Math.round(h / BASE_DT / k), 1, steps));
  return {
    key: s.key, returns: s.returns, steps, block: Math.min(12, steps), scale, nb: NB, seed,
    c0: cs[0], c1: cs[1] ?? cs[0], c2: cs[2] ?? cs[0], side, tp, sl,
    h0: 5 * sig * Math.sqrt(cs[0]), h1: 5 * sig * Math.sqrt(cs[1] ?? cs[0]), h2: 5 * sig * Math.sqrt(cs[2] ?? cs[0]), stepK: k,
  };
}
function density(hist, off, nb) {
  let m = 0; for (let i = 0; i < nb; i++) m = Math.max(m, hist[off + i]);
  return Array.from({ length: nb }, (_, i) => m ? Math.round(hist[off + i] / m * 1e4) / 1e4 : 0);
}
function histQuantiles(hist, off, nb, H, qs) {
  let n = 0; for (let i = 0; i < nb; i++) n += hist[off + i];
  if (!n) return qs.map(() => NaN);
  return qs.map(q => {
    const target = q * n; let acc = 0;
    for (let i = 0; i < nb; i++) {
      const c = hist[off + i];
      if (acc + c >= target) { const frac = c ? (target - acc) / c : 0.5; const z = (i + frac) / nb * 2 - 1; return Math.expm1(z * H); }
      acc += c;
    }
    return Math.expm1(H);
  });
}

/* ───────────────────────── useful workloads ─────────────────────────
 * Each producer answers: what does this compute give the desk? If nothing,
 * it produces no job and the silicon stays idle. */
const fresh = r => (r && !r.stale ? r : null);    // restored/stale results never suppress recomputation
const producers = {
  // P1 LIVE — first-passage odds for the current best singular trade.
  odds(f, s) {
    const b = f.best;
    if (!b || !Number.isFinite(b.entry) || !Number.isFinite(b.sl) || !Number.isFinite(b.tp) || b.entry <= 0) return;
    const sig = `${b.mode}|${Math.round(b.sl)}|${Math.round(b.tp)}|${s.epoch}`, r = fresh(G.results.odds);
    if (queued('odds') || (r && r.sig === sig) || (r && t() - r.at < ODDS_EVERY && r.mode === b.mode)) return;
    const side = b.mode === 'DIST' ? -1 : 1;
    const tp = Math.abs(Math.log(b.tp / b.entry)), sl = Math.abs(Math.log(b.sl / b.entry));
    if (!(tp > 0 && sl > 0)) return;
    const horizon = clamp(Number.isFinite(b.pivot) && b.pivot > 0 ? b.pivot : 12 * 60, 60, 4 * 3600);
    const p = mcParams(s, [horizon], side, tp, sl, 0x51ED ^ s.epoch);
    const red = G.health.state === 'RED';
    const paths = GPU.device && GPU.state !== 'UNAVAILABLE' ? 32768 : W.list.length ? 8192 : 2048;
    const total = red ? paths >> 2 : paths;
    const hist = new Uint32Array(4 * NB + 4);
    submit(newJob({
      tag: 'odds', kind: 'mc', bulk: ['returns'], cls: 'P1', params: p, total, unitWork: p.steps, work: total * p.steps, firstSlice: { gpu: 32768, gl2: 8192, worker: 2048, main: 256 },
      merge: out => { for (let i = 0; i < hist.length; i++) hist[i] += out[i]; },
      finish() {
        const o = 4 * NB, n = hist[o] + hist[o + 1] + hist[o + 2];
        if (!n) return;
        const pTP = hist[o + 1] / n, pSL = hist[o + 2] / n, rr = tp / sl;
        publish('odds', { sig, mode: b.mode, pTP, pSL, pOpen: hist[o] / n, n, se: Math.sqrt(pTP * (1 - pTP) / n), expR: pTP * rr - pSL, horizon, rr, tpLog: Math.log(b.tp / b.entry), slLog: Math.log(b.sl / b.entry), dens: density(hist, 0, NB), H: p.h0, engines: [...this.engines], ms: this.ms });
      },
    }));
  },
  // P2 OPPORTUNISTIC — risk cone with accumulating coverage per history epoch.
  cone(f, s) {
    if (queued('cone')) return;
    let acc = G.data.cone;
    if (!acc || (acc.key !== s.key && t() - acc.createdAt > 60_000)) {
      // Carry half of the previous epoch's evidence forward rather than discarding it.
      const next = { key: s.key, epoch: s.epoch, createdAt: t(), hist: new Float64Array(4 * NB + 4), paths: 0, p: mcParams(s, CONE_HORIZONS, 1, 1e9, 1e9, 0xC0DE ^ s.epoch) };
      if (acc && acc.hist && Math.abs(acc.p.h2 - next.p.h2) / next.p.h2 < 0.25) { for (let i = 0; i < acc.hist.length; i++) next.hist[i] = acc.hist[i] * 0.5; next.paths = acc.paths * 0.5; }
      acc = G.data.cone = next;
    }
    if (acc.paths >= CONE_TARGET) return;                // enough coverage; leave the silicon idle
    if (!admit('P2')) return;
    const p = { ...acc.p, seed: (acc.p.seed + Math.round(acc.paths) * 2654435761) >>> 0 };
    const gpu = GPU.device && GPU.state !== 'UNAVAILABLE';
    const total = gpu ? 262_144 : W.list.some(r => r.gl2) ? 65_536 : W.list.length ? 16_384 : 2048;
    submit(newJob({
      tag: 'cone', kind: 'mc', bulk: ['returns'], cls: 'P2', params: p, total, unitWork: p.steps, work: total * p.steps, firstSlice: { gpu: 65536, gl2: 16384, worker: 2048, main: 128 },
      merge: out => { for (let i = 0; i < acc.hist.length; i++) acc.hist[i] += out[i]; },
      finish() {
        acc.paths += this.done;
        const qs = [0.05, 0.25, 0.5, 0.75, 0.95], H = [p.h0, p.h1, p.h2];
        const cones = CONE_HORIZONS.map((h, i) => ({ horizon: h, q: histQuantiles(acc.hist, i * NB, NB, H[i], qs) }));
        // Drawdown bins span [0, h2] rather than [-H, H].
        const md = [0.5, 0.95].map(q => { let n = 0; for (let i = 0; i < NB; i++) n += acc.hist[3 * NB + i]; let a = 0; for (let i = 0; i < NB; i++) { a += acc.hist[3 * NB + i]; if (a >= q * n) return Math.expm1((i + 0.5) / NB * p.h2); } return NaN; });
        publish('cone', { cones, dens: [0, 1, 2].map(i => density(acc.hist, i * NB, NB)), H, mdd50: md[0], mdd95: md[1], paths: Math.round(acc.paths), target: CONE_TARGET, stepK: p.stepK, engines: [...this.engines], ms: this.ms });
      },
    }));
  },
  // P2 OPPORTUNISTIC — parameter sensitivity with honest holdout validation.
  sweep(f, s) {
    const r = fresh(G.results.sweep);
    if (queued('sweep') || (r && (r.epoch === s.epoch || t() - r.at < SWEEP_EVERY))) return;
    if (s.y.length < 400 || !admit('P2')) return;
    const T = s.y.length, Lmax = Math.max(8, Math.floor(T / 8)), Ls = [];
    for (let L = 2; L <= Lmax && Ls.length < 48; L = Math.max(L + 1, Math.round(L * 1.15))) Ls.push(L);
    const Ths = Float32Array.from({ length: 16 }, (_, i) => i * 0.16);
    const combos = Ls.length * Ths.length * 2;
    const p = { key: `${s.key}w`, y: s.y, Ls: Float32Array.from(Ls), Ths, split: Math.floor(T * 0.7), sigma: s.sigma, cost: 1e-4, ann: Math.sqrt(3600 / BASE_DT) };
    const out = new Float32Array(combos * 4);
    submit(newJob({
      tag: 'sweep', kind: 'sweep', bulk: ['y', 'Ls', 'Ths'], cls: 'P2', params: p, total: combos, unitWork: T, work: combos * T, firstSlice: { gpu: combos, worker: 256, main: 8 },
      merge: (o, from, count) => out.set(o.subarray(0, count * 4), from * 4),
      finish() {
        let best = -1, bestTrain = -Infinity, posHold = 0, trainSum = 0, holdSum = 0;
        const order = [];
        for (let c = 0; c < combos; c++) { const tr = out[c * 4], ho = out[c * 4 + 1]; order.push(c); if (ho > 0) posHold++; if (tr > bestTrain && out[c * 4 + 3] >= 4) { bestTrain = tr; best = c; } }
        order.sort((a, b) => out[b * 4] - out[a * 4]);
        const top = order.slice(0, Math.max(1, Math.floor(combos * 0.1)));
        for (const c of top) { trainSum += out[c * 4]; holdSum += out[c * 4 + 1]; }
        if (best < 0) return;
        const per = Ls.length * Ths.length, mode = best >= per ? 'REVERT' : 'MOMENTUM', rem = best % per;
        publish('sweep', {
          epoch: s.epoch, combos, mode, L: Ls[(rem / Ths.length) | 0], lookbackMin: Ls[(rem / Ths.length) | 0] * BASE_DT / 60, th: Ths[rem % Ths.length],
          train: out[best * 4], hold: out[best * 4 + 1], trades: out[best * 4 + 3], positiveHold: posHold / combos,
          overfitGap: (trainSum - holdSum) / top.length, span: s.spanMin, engines: [...this.engines], ms: this.ms,
          best, Ls, Ths: Array.from(Ths, x => Math.round(x * 100) / 100), grid: Array.from({ length: combos }, (_, c) => Math.round(out[c * 4 + 1] * 1000) / 1000),
        });
      },
    }));
  },
  // P3 IDLE — fleet correlation → effective number of independent PICOs.
  corr(f) {
    const r = fresh(G.results.corr);
    if (queued('corr') || (r && (r.stamp === f.fleetStamp || t() - r.at < CORR_EVERY))) return;
    if (!admit('P3')) return;
    let fl; try { fl = f.fleet(); } catch (_) { return; }
    const { N, K: KH, m, len } = fl, Kr = KH - 1, Kp = Math.ceil(Kr / 4) * 4;
    const rows = [];
    for (let i = 0; i < N; i++) if (len[i] >= 12) rows.push(i);
    if (rows.length < 16) return;
    let Z;
    try { Z = new Float32Array(rows.length * Kp); } catch (e) { G.health.memFaultAt = t(); return; }
    const valid = [];
    for (let q = 0; q < rows.length; q++) {
      const i = rows[q], n = len[i], base = i * KH, r = new Float64Array(n - 1);
      let mu = 0; for (let k = 1; k < n; k++) { const a = m[base + k - 1], b = m[base + k]; r[k - 1] = a > 0 ? Math.log(b / a) : 0; mu += r[k - 1]; }
      mu /= r.length;
      let ss = 0; for (const x of r) ss += (x - mu) ** 2;
      if (ss < 1e-18) continue;
      const inv = 1 / Math.sqrt(ss), o = valid.length * Kp + (Kr - r.length);
      for (let k = 0; k < r.length; k++) Z[o + k] = (r[k] - mu) * inv;
      valid.push(i);
    }
    const Nv = valid.length;
    if (Nv < 16) return;
    const p = { key: `f${f.fleetStamp}`, Z: Z.subarray(0, Nv * Kp).slice(), N: Nv, K: Kp };
    const acc = { sumSq: 0, sumAbs: 0, pairs: 0, rowAbs: new Float64Array(Nv) };
    submit(newJob({
      tag: 'corr', kind: 'corr', bulk: ['Z'], cls: 'P3', params: p, total: Nv, unitWork: Nv * Kp / 2, work: Nv * Nv * Kp / 2, firstSlice: { worker: 64, main: 4 },
      merge: o => { acc.sumSq += o.sumSq; acc.sumAbs += o.sumAbs; acc.pairs += o.pairs; for (let i = 0; i < Nv; i++) acc.rowAbs[i] += o.rowAbs[i]; },
      finish() {
        let top = 0; for (let i = 1; i < Nv; i++) if (acc.rowAbs[i] > acc.rowAbs[top]) top = i;
        // Participation ratio of the correlation matrix: (tr C)^2 / tr(C^2).
        const effective = (Nv * Nv) / (Nv + 2 * acc.sumSq);
        const spectrum = new Array(32).fill(0);
        for (let i = 0; i < Nv; i++) spectrum[Math.min(31, Math.floor(acc.rowAbs[i] / (Nv - 1) * 32))]++;
        publish('corr', { stamp: f.fleetStamp, n: Nv, effective, spectrum, meanAbs: acc.pairs ? acc.sumAbs / acc.pairs : 0, crowdedId: valid[top] + 1, crowdedMean: acc.rowAbs[top] / (Nv - 1), engines: [...this.engines], ms: this.ms });
      },
    }));
  },
};
function publish(kind, value) {
  G.results[kind] = { ...value, at: t(), wallAt: wall(), stale: false };
  emit('result', { kind, value: G.results[kind] });
  scheduleSave();
}
function produce() {
  if (document.hidden || G.suspended || !G.cal.done) return;
  const f = feed(); if (!f) return;
  const s = rebuildSeries(f); if (!s) return;
  producers.odds(f, s);
  producers.cone(f, s);
  producers.sweep(f, s);
  producers.corr(f, s);
}

/* ───────────────────────── lifecycle & persistence ───────────────────────── */
let saveTimer = 0;
function scheduleSave() { if (!saveTimer) saveTimer = setTimeout(save, 4000); }
function save() {
  clearTimeout(saveTimer); saveTimer = 0;
  try {
    const blob = {
      v: VERSION, wall: wall(), envelope: G.health.envelope, perf: G.perf,
      results: G.results,
    };
    localStorage.setItem(STORE, JSON.stringify(blob));
  } catch (_) {}
}
function restore() {
  try {
    const raw = localStorage.getItem(STORE); if (!raw) return;
    const b = JSON.parse(raw); if (!b || !b.v) return;
    const gap = wall() - (b.wall || 0);
    for (const k in b.results || {}) G.results[k] = { ...b.results[k], at: -Infinity, stale: true, restoredGapMs: gap };
    // Throughput baselines survive; a fresh boot re-earns its envelope.
    for (const k in b.perf || {}) G.perf[k] = { ...b.perf[k], n: Math.min(3, b.perf[k].n || 0), at: 0 };
    note(`restored state from ${Math.round(gap / 1000)}s ago`);
  } catch (_) {}
}
function suspend(why) {
  if (G.suspended) return;
  G.suspended = true; G.lastWall = wall();
  cancelClass('P3', why);
  save(); note(`suspend: ${why}`);
}
async function resume(why) {
  if (!G.suspended && why !== 'boot') return;
  G.suspended = false;
  const gap = wall() - G.lastWall;
  note(`resume: ${why} after ${Math.round(gap / 1000)}s`);
  // Do not pretend execution continued while suspended.
  if (gap > 120_000) {
    for (const k in G.results) G.results[k].stale = true;
    G.data.series = null; G.data.cone = null; G.health.envelope = Math.min(G.health.envelope, 0.15);
  }
  G.health.settleUntil = t() + 1200;
  lastFrameT = 0; fCount = 0; loopExpected = 0; G.health.loopLag = 0;
  // Reacquire only a device we previously had; never loop on hardware that was never offered.
  if (!GPU.device && GPU.generation > 0 && GPU.losses <= 3) await gpuAcquire('resume');
  for (const r of W.list) { const sent = t(); r.w.postMessage({ type: 'ping' }); setTimeout(() => { if (r.pong < sent && W.list.includes(r) && !r.busy) workerCrash(r, 'no pong after resume'); }, 1500); }
  pump();
}

/* ───────────────────────── governor loop ───────────────────────── */
let lastTick = t();
function tick() {
  const now = t(), dt = (now - lastTick) / 1000; lastTick = now;
  try {
    assessHealth();
    refillBudget(Math.min(dt, 2));
    if (!GPU.device && GPU.state === 'DEGRADED' && GPU.retryAt && now > GPU.retryAt && !document.hidden) { GPU.retryAt = 0; gpuAcquire('recover'); }
    if (GPU.state === 'DEGRADED' && GPU.device && now - G.health.gpuFaultAt > 30_000) { GPU.state = 'READY'; GPU.strikes = 0; }
    tuneWorkers();
    produce();
    pump();
    if (now - (G._savedAt || 0) > 20_000) { G._savedAt = now; save(); }
  } catch (e) { note(`tick error: ${e.message}`); }
  renderTelemetry();
  setTimeout(tick, TICK_MS);
}

/* ───────────────────────── telemetry ───────────────────────── */
function backendLabel() {
  const l = [];
  if (GPU.device && GPU.state !== 'UNAVAILABLE') l.push('WEBGPU');
  const ready = W.list.filter(r => r.ready);
  if (ready.some(r => r.gl2) && !l.length) l.push('WEBGL2');
  if (ready.some(r => r.wasm)) l.push('WASM·SIMD');
  if (ready.length) l.push(`W${ready.length}`);
  if (!l.length) l.push(G.caps.webgl2 ? 'WEBGL2·JS' : 'JS');
  return l.join('+');
}
function primaryBackend() {
  if (GPU.device && GPU.state !== 'UNAVAILABLE') return 'WEBGPU';
  const ready = W.list.filter(r => r.ready);
  if (ready.some(r => r.wasm)) return 'WASM';
  if (ready.some(r => r.gl2)) return 'WEBGL2';
  if (ready.length) return 'WORKER';
  return 'JS';
}
function gpuStatus() {
  if (GPU.state === 'PROBING') return 'PROBING';
  if (!GPU.device) return GPU.state === 'DEGRADED' ? 'DEGRADED' : 'UNAVAILABLE';
  if (t() < (GPU.coolUntil || 0)) return 'DEGRADED';
  return GPU.state;
}
function snapshot() {
  const h = G.health, c = G.caps;
  return {
    version: VERSION, backend: primaryBackend(), layers: backendLabel(), gpu: gpuStatus(),
    gpuLastMs: GPU.lastMs, gpuQueueMs: GPU.queueMs, gpuLosses: GPU.losses,
    workers: { active: W.list.filter(r => r.busy).length, configured: W.list.length, max: G.plan?.glimmerMax ?? 0, plan: G.plan, disabled: W.disabled },
    frame: { lastMs: h.frameMs, p50: h.p50, p95: h.p95, nominalHz: h.hz, missRate: h.missRate },
    loopLagMs: h.loopLag, longTaskMsPerSec: c.longTask ? h.longTaskMs : null,
    queue: { P1: G.queue.P1.length, P2: G.queue.P2.length, P3: G.queue.P3.length, running: G.running.size },
    health: h.state, reasons: h.reasons, envelope: h.envelope, use: G.budget.use,
    pressure: h.pressure, pressureInferred: true, efficiency: h.efficiency ?? null, osPressure: h.osPressure,
    memory: memoryInfo(), battery: h.battery, caps: c, results: G.results, log: G.log.slice(-12),
  };
}
function memoryInfo() {
  const m = {};
  if (performance.memory) m.jsHeapUsedMB = performance.memory.usedJSHeapSize / 1048576;
  if (G.caps.deviceMemory) m.deviceMemoryGB = G.caps.deviceMemory;
  if (G.caps.storage?.usage != null) { m.storageUsedMB = G.caps.storage.usage / 1048576; m.storageQuotaMB = G.caps.storage.quota / 1048576; }
  m.faultRecent = t() - G.health.memFaultAt < 10_000;
  return m;
}

let chip = null, sheet = null, sheetOpen = false, lastChip = 0;
function mountUI() {
  if (!document.getElementById('glimmer-style')) {
    const st = document.createElement('style'); st.id = 'glimmer-style';
    st.textContent = `
html[data-qc-build] .top{grid-auto-flow:column!important;grid-template-columns:minmax(96px,1fr)!important;grid-auto-columns:auto!important}
#glimmerChip{display:inline-flex!important;align-items:center;gap:3px;font-variant-numeric:tabular-nums;color:#f3d477!important;border-color:rgba(243,212,119,.55)!important;background:#070905!important;white-space:nowrap}
#glimmerChip i{width:5px;height:5px;border-radius:50%;background:#92d7b7;flex:0 0 auto}
@media(orientation:portrait){#glimmerChip .gb{display:none}}
#glimmerChip[data-h="AMBER"] i{background:#e0a978}#glimmerChip[data-h="RED"] i{background:#e47f70}
#glimmerSheet{position:fixed;z-index:2147483350;left:max(8px,var(--qc-safe-l,env(safe-area-inset-left,0px)));right:max(8px,var(--qc-safe-r,env(safe-area-inset-right,0px)));
 bottom:max(10px,calc(var(--qc-safe-b,env(safe-area-inset-bottom,0px)) + 6px));max-width:420px;margin-left:auto;max-height:calc(100dvh - 90px);overflow:auto;
 background:rgba(0,0,0,.965);border:.5px solid rgba(243,212,119,.7);border-radius:4px;box-shadow:0 0 18px rgba(217,173,69,.12);
 font:8px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace;color:#f0ede4;padding:6px 7px;display:none}
#glimmerSheet.open{display:block}
#glimmerSheet header{display:flex;justify-content:space-between;align-items:center;color:#f3d477;letter-spacing:.06em;margin-bottom:4px}
#glimmerSheet dd button,#glimmerSheet header button{font:inherit;color:#f3d477;background:#070905;border:.5px solid rgba(217,173,69,.6);border-radius:3px;padding:3px 7px}
#glimmerSheet dl{display:grid;grid-template-columns:auto 1fr;gap:1px 8px;margin:0}
#glimmerSheet dt{color:#9b9687}#glimmerSheet dd{margin:0;overflow-wrap:anywhere}
#glimmerSheet h4{margin:6px 0 2px;font-size:7px;color:#d9ad45;letter-spacing:.08em;font-weight:600}
#glimmerSheet .ok{color:#92d7b7}#glimmerSheet .warn{color:#e0a978}#glimmerSheet .bad{color:#e47f70}#glimmerSheet .dim{color:#9b9687}
#glimmerSheet p{margin:5px 0 0;color:#9b9687;font-size:7px}`;
    document.head.appendChild(st);
  }
  const top = document.querySelector('header.top');
  if (top && !document.getElementById('glimmerChip')) {
    chip = document.createElement('button');
    chip.id = 'glimmerChip'; chip.type = 'button'; chip.className = 'btn';
    chip.setAttribute('aria-controls', 'glimmerSheet'); chip.setAttribute('aria-expanded', 'false');
    chip.innerHTML = '<i aria-hidden="true"></i><span>GLM <span class="gb">—</span> <span class="gu">—</span></span>';
    chip.addEventListener('click', () => toggleSheet());
    const anchor = document.getElementById('viewBtn');
    top.insertBefore(chip, anchor || null);
  }
  if (!document.getElementById('glimmerSheet')) {
    sheet = document.createElement('section');
    sheet.id = 'glimmerSheet'; sheet.setAttribute('role', 'dialog'); sheet.setAttribute('aria-label', 'GLIMMER compute telemetry');
    document.body.appendChild(sheet);
    sheet.addEventListener('click', e => {
      if (e.target.closest('[data-close]')) toggleSheet(false);
      if (e.target.closest('[data-tex]')) { window.__quadcomTexture?.(true); renderTelemetry(true); }
    });
  }
}
function toggleSheet(force) {
  sheetOpen = typeof force === 'boolean' ? force : !sheetOpen;
  sheet?.classList.toggle('open', sheetOpen);
  chip?.setAttribute('aria-expanded', String(sheetOpen));
  if (sheetOpen) renderTelemetry(true);
}
const esc = s => String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
const signed = x => Number.isFinite(x) ? `${x >= 0 ? '+' : '−'}${Math.abs(x * 100).toFixed(2)}%` : '—';
const age = r => r.stale ? `<span class="warn">STALE${r.restoredGapMs ? ' · restored ' + Math.round(r.restoredGapMs / 60000) + 'm' : ''}</span>` : `<span class="dim">${Math.max(0, Math.round((t() - r.at) / 1000))}s ago</span>`;
const hmin = s => s >= 3600 ? `${s / 3600}h` : `${Math.round(s / 60)}m`;
function renderTelemetry(force) {
  const now = t();
  if (chip && (force || now - lastChip > 900)) {
    lastChip = now;
    chip.dataset.h = G.health.state;
    chip.querySelector('.gb').textContent = primaryBackend() === 'WEBGPU' ? 'WGPU' : primaryBackend();
    chip.querySelector('.gu').textContent = `${Math.round(G.budget.use * 100)}%`;
    chip.setAttribute('aria-label', `GLIMMER ${G.health.state}, backend ${primaryBackend()}, using ${Math.round(G.budget.use * 100)} percent of its envelope. Open telemetry`);
  }
  if (!sheetOpen || !sheet) return;
  const s = snapshot(), c = s.caps, R = s.results;
  const cls = { GREEN: 'ok', AMBER: 'warn', RED: 'bad', HEADROOM: 'ok', NORMAL: 'ok', PRESSURE: 'warn', 'THROTTLED-LIKE': 'bad', READY: 'ok', BUSY: 'ok', DEGRADED: 'warn', UNAVAILABLE: 'dim', PROBING: 'dim' };
  const mem = s.memory, memTxt = [
    mem.jsHeapUsedMB != null ? `JS heap ${mem.jsHeapUsedMB.toFixed(0)}MB` : null,
    mem.deviceMemoryGB ? `device ≈${mem.deviceMemoryGB}GB (coarse)` : null,
    mem.storageUsedMB != null ? `storage ${mem.storageUsedMB.toFixed(1)}/${(mem.storageQuotaMB / 1024).toFixed(1)}GB` : null,
    mem.faultRecent ? '<span class="bad">allocation fault</span>' : null,
  ].filter(Boolean).join(' · ') || '<span class="dim">not exposed by this browser</span>';
  const yes = (v, label) => `<span class="${v ? 'ok' : 'dim'}">${label}${v ? '✓' : '—'}</span>`;
  const wg = c.webgpu?.limits;
  const out = [];
  if (R.odds) out.push(`<dt>TRADE ODDS</dt><dd>${R.odds.mode} · TP first <b>${pct(R.odds.pTP)}</b> · SL first ${pct(R.odds.pSL)} · open ${pct(R.odds.pOpen)} · E[R] ${R.odds.expR.toFixed(2)} (R:R ${R.odds.rr.toFixed(2)}, ${hmin(R.odds.horizon)}) · ±${pct(R.odds.se)} · ${R.odds.n.toLocaleString()} paths · ${esc(R.odds.engines.join('/'))} · ${age(R.odds)}</dd>`);
  if (R.cone) out.push(`<dt>RISK CONE</dt><dd>${R.cone.cones.map(x => `${hmin(x.horizon)} P5 ${signed(x.q[0])} · P50 ${signed(x.q[2])} · P95 ${signed(x.q[4])}`).join('<br>')}<br>max DD P50 ${pct(R.cone.mdd50)} · P95 ${pct(R.cone.mdd95)} (4h) · ${R.cone.paths.toLocaleString()}/${(R.cone.target / 1e6).toFixed(0)}M paths · ${esc(R.cone.engines.join('/'))} · ${age(R.cone)}</dd>`);
  if (R.sweep) out.push(`<dt>SIGNAL SWEEP</dt><dd>best-in-train ${R.sweep.mode} ${R.sweep.lookbackMin.toFixed(1)}m θ${R.sweep.th.toFixed(2)}σ → holdout Sharpe <b class="${R.sweep.hold > 0 ? 'ok' : 'bad'}">${R.sweep.hold.toFixed(2)}</b> (train ${R.sweep.train.toFixed(2)}) · ${pct(R.sweep.positiveHold)} of ${R.sweep.combos} combos positive out-of-sample · top-decile overfit gap ${R.sweep.overfitGap.toFixed(2)} · ${esc(R.sweep.engines.join('/'))} · ${age(R.sweep)}</dd>`);
  if (R.corr) out.push(`<dt>FLEET CORR</dt><dd>≈${R.corr.effective.toFixed(1)} effective independent of ${R.corr.n} active PICOs · mean |ρ| ${R.corr.meanAbs.toFixed(3)} · most crowded PICO-${String(R.corr.crowdedId).padStart(4, '0')} (|ρ| ${R.corr.crowdedMean.toFixed(3)}) · ${esc(R.corr.engines.join('/'))} · ${age(R.corr)}</dd>`);
  sheet.innerHTML = `
<header><b>❖ GLIMMER · COMPUTE GOVERNOR</b><button type="button" data-close>CLOSE</button></header>
<dl>
<dt>BACKEND</dt><dd>${s.backend} <span class="dim">(${esc(s.layers)})</span></dd>
<dt>GPU</dt><dd class="${cls[s.gpu] || ''}">${s.gpu}${s.gpuLastMs != null ? ` <span class="dim">· last job ${ms(s.gpuLastMs)} · queue ${ms(s.gpuQueueMs)}</span>` : ''}${s.gpuLosses ? ` <span class="warn">· ${s.gpuLosses} device loss</span>` : ''}</dd>
<dt>WORKERS</dt><dd>${s.workers.active} active / ${s.workers.configured} configured <span class="dim">(max ${s.workers.max}; ${s.workers.plan ? `${s.workers.plan.reserve} of ${s.workers.plan.logical} logical reserved for browser/OS, ${s.workers.plan.coreWorkers} desk` : '—'})</span>${s.workers.disabled ? ' <span class="bad">disabled</span>' : ''}</dd>
<dt>FRAME</dt><dd>${ms(s.frame.lastMs)} · p50 ${ms(s.frame.p50)} · p95 ${ms(s.frame.p95)} · ${s.frame.nominalHz}Hz · missed ${pct(s.frame.missRate)}</dd>
<dt>LOOP</dt><dd>event-loop delay ${ms(s.loopLagMs)}${s.longTaskMsPerSec != null ? ` · long tasks ${ms(s.longTaskMsPerSec)}/s` : ''}</dd>
<dt>QUEUE</dt><dd>P1 ${s.queue.P1} · P2 ${s.queue.P2} · P3 ${s.queue.P3} · running ${s.queue.running}</dd>
<dt>GLIMMER</dt><dd><b>${Math.round(s.use * 100)}%</b> of envelope used · envelope ${Math.round(s.envelope * 100)}% · <span class="${cls[s.health]}">${s.health}</span>${s.reasons.length ? ` <span class="dim">(${esc(s.reasons.join(', '))})</span>` : ''}</dd>
<dt>PRESSURE</dt><dd><span class="${cls[s.pressure]}">${s.pressure}</span> <span class="dim">INFERRED${s.efficiency ? ` · kernel efficiency ×${s.efficiency.toFixed(2)} of best` : ''}</span>${s.osPressure ? ` · browser-reported CPU ${esc(s.osPressure)}` : ''}</dd>
<dt>MEMORY</dt><dd>${memTxt}</dd>
${(() => { const v = window.__quadcomVision?.(); return v ? `<dt>VISION</dt><dd>${v.backend} · ${v.tier}${v.lastMs != null ? ` · encode ${ms(v.lastMs)}` : ''}${v.gpuMs != null ? ` · gpu done ${ms(v.gpuMs)}` : ''} · ${v.renders} renders · texture <button type="button" data-tex>${v.texture === 'aurum' ? 'AURUM' : 'OFF'}</button>${v.error ? ` <span class="bad">${esc(v.error.slice(0, 40))}</span>` : ''}</dd>` : ''; })()}
<dt>VERIFIED</dt><dd>${!G.cal.done ? '<span class="dim">calibrating…</span>' : [G.cal.gpu ? `WebGPU mc ${G.cal.gpu.mc ? '✓' : '✗'} sweep ${G.cal.gpu.sweep ? '✓' : '✗'}` : null, G.cal.gl2 != null ? `WebGL2 mc ${G.cal.gl2 ? '✓' : '✗'}` : null, G.cal.worker != null ? `worker ${G.cal.worker ? '✓' : '✗'}` : null].filter(Boolean).join(' · ') || 'JS reference only'} <span class="dim">vs JS reference</span></dd>
${s.battery ? `<dt>BATTERY</dt><dd>${Math.round(s.battery.level * 100)}% · ${s.battery.charging ? 'charging' : 'discharging'}</dd>` : ''}
</dl>
<h4>USEFUL OUTPUT</h4>
<dl>${out.join('') || '<dt>—</dt><dd class="dim">warming: waiting for enough price history (≥5 min) and a best trade</dd>'}</dl>
<h4>CAPABILITIES (BROWSER-EXPOSED)</h4>
<div>${yes(c.webgpuApi && !!GPU.device, 'WebGPU ')} ${c.webgpu ? `<span class="dim">[${esc((c.webgpu.features || []).join(' ') || 'no optional features')}]</span>` : ''} ${yes(c.webgl2, 'WebGL2 ')} ${yes(c.wasm, 'Wasm ')} ${yes(c.wasmSimd, 'SIMD ')} ${yes(c.workers, 'Workers ')} ${yes(c.sab, 'SAB ')} ${yes(c.offscreenCanvas, 'Offscreen ')} ${yes(c.workerWebGL2, 'OffscreenGL2 ')} ${yes(c.transferables, 'Transfer ')} ${yes(c.webCodecs, 'WebCodecs ')} ${yes(c.webAudio, 'WebAudio ')} ${yes(c.indexedDB, 'IDB ')} ${yes(c.cacheApi, 'Cache ')} ${yes(c.serviceWorker, 'SW ')} ${yes(c.opfs, 'OPFS ')} <span class="dim">DPR ${c.dpr} · ${c.logicalCores ?? '?'} logical${c.network?.type ? ` · net ${esc(c.network.type)}` : ''}</span></div>
${wg ? `<div class="dim">limits: wg ${wg.maxComputeWorkgroupSizeX} · inv ${wg.maxComputeInvocationsPerWorkgroup} · storage ${(wg.maxStorageBufferBindingSize / 1048576).toFixed(0)}MB · buffer ${(wg.maxBufferSize / 1048576).toFixed(0)}MB</div>` : ''}
<p>WebGPU is the browser route to the GPU (Metal-class on Apple devices); it is not native Metal access. Temperature, wattage, VRAM and GPU/CPU utilisation are not exposed to web pages and are not shown. Pressure is inferred from frame timing, event-loop delay and kernel efficiency.</p>`;
}

/* ───────────────────────── boot ───────────────────────── */
function markInput() { G.health.lastInput = t(); if (G.queue.P3.length || [...G.running].some(j => j.cls === 'P3')) cancelClass('P3', 'input'); }
function boot() {
  probeSync();
  G.plan = makePlan();
  restore();
  mountUI();
  for (const ev of ['pointerdown', 'keydown', 'wheel', 'touchstart']) addEventListener(ev, markInput, { passive: true, capture: true });
  addEventListener('orientationchange', () => { G.health.settleUntil = t() + 1500; }, { passive: true });
  addEventListener('resize', () => { G.health.settleUntil = t() + 800; }, { passive: true });
  document.addEventListener('visibilitychange', () => { if (document.hidden) suspend('hidden'); else resume('visible'); });
  addEventListener('pagehide', () => suspend('pagehide'), { passive: true });
  addEventListener('pageshow', e => { if (e.persisted && !document.hidden) resume('pageshow'); }, { passive: true });
  document.addEventListener('freeze', () => suspend('freeze'));
  document.addEventListener('resume', () => resume('resume'));
  addEventListener('online', () => { G.caps.online = true; });
  addEventListener('offline', () => { G.caps.online = false; });
  requestAnimationFrame(frameSampler);
  loopProbe(); watchLongTasks();
  G.plan && G.plan.glimmerMax > 0 && spawnWorker();
  G.ready = probeAsync().catch(e => note(`probe error: ${e.message}`));
  G.calibrated = G.ready.then(calibrate).catch(e => note(`calibration error: ${e.message}`));
  setTimeout(tick, TICK_MS);
  document.documentElement.dataset.qcGlimmer = VERSION;
}

window.GLIMMER = {
  version: VERSION,
  get plan() { return G.plan; },
  get ready() { return G.ready; },
  /** Shared WebGPU device, so the desk and GLIMMER use one device and one set of limits. */
  async gpuDevice() { await G.ready; return GPU.device ? { adapter: GPU.adapter, device: GPU.device } : null; },
  /** Called after GLIMMER re-acquires a device following a loss. */
  onGpuDevice(fn) { GPU.listeners.add(fn); return () => GPU.listeners.delete(fn); },
  /** Whether a job of the given class may start now. */
  admit: (cls, backend) => admit(cls, backend === 'gpu' ? 'gpu' : backend),
  /** Account busy time spent outside GLIMMER's own executor (e.g. the desk's GPU tournament). */
  account,
  label: () => `GLM ${primaryBackend()}`,
  telemetry: snapshot,
  calibration: () => G.cal,
  /** Cheap governor state for renderers deciding their quality tier. */
  governor: () => ({ health: G.health.state, envelope: G.health.envelope, pressure: G.health.pressure, use: G.budget.use, hz: G.health.hz, hidden: document.hidden || G.suspended, gpu: gpuStatus() }),
  results: () => G.results,
  open: () => toggleSheet(true),
};
window.__quadcomGlimmer = snapshot;
boot();
})();
