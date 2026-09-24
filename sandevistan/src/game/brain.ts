export const LAYER = {
  al: 0,
  ol: 1,
  mb: 2,
  cx: 3,
  dn: 4,
} as const;

export const COUNTS = { al: 8, ol: 6, mb: 12, cx: 8, dn: 6 };
export const N_NEURONS =
  COUNTS.al + COUNTS.ol + COUNTS.mb + COUNTS.cx + COUNTS.dn;

export type BrainNode = {
  i: number;
  x: number;
  y: number;
  layer: number;
};

export type BrainEdge = { i: number; j: number; w: number };

export type Senses = {
  olf: number;
  visL: number;
  visR: number;
  threat: number;
  speed: number;
};

function offset(layer: number) {
  let o = 0;
  if (layer > 0) o += COUNTS.al;
  if (layer > 1) o += COUNTS.ol;
  if (layer > 2) o += COUNTS.mb;
  if (layer > 3) o += COUNTS.cx;
  return o;
}

export class FlyBrain {
  act = new Float32Array(N_NEURONS);
  nodes: BrainNode[] = [];
  edges: BrainEdge[] = [];
  motorL = 0;
  motorR = 0;
  firing = 0;
  intendedSteer = 0;
  intendedThrottle = 0;
  olfactory = 0;
  visual = 0;
  cx = 0;

  constructor() {
    this.layout();
    this.connect();
  }

  private layout() {
    const cols = [
      { layer: LAYER.al, n: COUNTS.al, x: 0.1 },
      { layer: LAYER.ol, n: COUNTS.ol, x: 0.28 },
      { layer: LAYER.mb, n: COUNTS.mb, x: 0.5 },
      { layer: LAYER.cx, n: COUNTS.cx, x: 0.72 },
      { layer: LAYER.dn, n: COUNTS.dn, x: 0.9 },
    ];
    let i = 0;
    for (const col of cols) {
      for (let k = 0; k < col.n; k++) {
        const t = (k + 0.5) / col.n;
        this.nodes.push({ i, x: col.x, y: 0.1 + t * 0.8, layer: col.layer });
        i++;
      }
    }
  }

  private connect() {
    const rng = mulberry32(140000);
    const link = (a: number, b: number, n: number, w: number) => {
      const oa = offset(a);
      const ob = offset(b);
      const na = this.nodes.filter((nd) => nd.layer === a).length;
      const nb = this.nodes.filter((nd) => nd.layer === b).length;
      for (let k = 0; k < n; k++) {
        const i = oa + ((rng() * na) | 0);
        const j = ob + ((rng() * nb) | 0);
        this.edges.push({ i, j, w: w * (0.6 + rng() * 0.8) });
      }
    };
    link(LAYER.al, LAYER.mb, 18, 0.55);
    link(LAYER.ol, LAYER.mb, 12, 0.45);
    link(LAYER.ol, LAYER.cx, 8, 0.5);
    link(LAYER.mb, LAYER.cx, 16, 0.4);
    link(LAYER.cx, LAYER.dn, 14, 0.7);
    link(LAYER.al, LAYER.dn, 6, 0.25);
  }

  reset() {
    this.act.fill(0);
    this.motorL = 0;
    this.motorR = 0;
    this.firing = 0;
  }

  step(dt: number, senses: Senses) {
    const next = new Float32Array(this.act.length);
    const leak = Math.exp(-3.2 * dt);

    const al0 = offset(LAYER.al);
    for (let k = 0; k < COUNTS.al; k++) {
      const drive = senses.olf * (0.45 + 0.55 * hash01(k + 3));
      next[al0 + k] = this.act[al0 + k] * leak + drive;
    }
    const ol0 = offset(LAYER.ol);
    for (let k = 0; k < COUNTS.ol; k++) {
      const side = k < COUNTS.ol / 2 ? senses.visL : senses.visR;
      next[ol0 + k] = this.act[ol0 + k] * leak + side * 0.85 + senses.threat * 0.5;
    }

    for (const e of this.edges) {
      const pre = this.act[e.i] > 0.42 ? this.act[e.i] : this.act[e.i] * 0.25;
      next[e.j] += pre * e.w * dt * 14;
    }

    let fire = 0;
    for (let i = 0; i < next.length; i++) {
      next[i] = Math.max(0, Math.min(1.4, next[i]));
      if (next[i] > 0.55) fire++;
    }
    this.act = next;
    this.firing = fire / N_NEURONS;

    const dn0 = offset(LAYER.dn);
    let l = 0;
    let r = 0;
    for (let k = 0; k < 3; k++) l += this.act[dn0 + k];
    for (let k = 3; k < 6; k++) r += this.act[dn0 + k];
    this.motorL = l / 3;
    this.motorR = r / 3;

    this.olfactory = mean(this.act, al0, COUNTS.al);
    this.visual = mean(this.act, ol0, COUNTS.ol);
    this.cx = mean(this.act, offset(LAYER.cx), COUNTS.cx);

    const diff = this.motorR - this.motorL;
    this.intendedSteer = clamp(diff * 1.4 + (senses.visL - senses.visR) * 0.6, -1, 1);
    this.intendedThrottle = clamp(
      0.35 + this.olfactory * 0.5 + senses.threat * 0.55 + senses.speed * 0.05,
      0.15,
      1,
    );
    return {
      steer: this.intendedSteer,
      throttle: this.intendedThrottle,
    };
  }
}

function mean(a: Float32Array, start: number, n: number) {
  let s = 0;
  for (let i = 0; i < n; i++) s += a[start + i];
  return s / n;
}

function clamp(v: number, a: number, b: number) {
  return Math.max(a, Math.min(b, v));
}

function hash01(n: number) {
  const x = Math.sin(n * 127.1) * 43758.5453;
  return x - Math.floor(x);
}

function mulberry32(a: number) {
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
