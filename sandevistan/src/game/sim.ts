import { FlyBrain } from "./brain";
import type { Actions } from "./input";
import type { MarketTick, SignalSide } from "./strategy";

export const FIXED_DT = 1 / 60;
export const ARENA = 12.5;
export const BEST_KEY = "sandevistan-best";
export const DESK_KEY = "sandevistan-fly-desk-v1";

export type Phase = "title" | "play" | "paused" | "dead" | "won";
export type DriveMode = "auto" | "remote";

export type Pickup = { x: number; z: number; taken: boolean; spin: number; kind: "sucrose" | "poop" };
export type Obstacle = { x: number; z: number; r: number; kind: PropKind };
export type PropKind = "mug" | "cap" | "dish" | "cable" | "clip" | "crumb" | "spoon";

export type Stomp = {
  x: number;
  z: number;
  t: number;
  phase: "warn" | "slam" | "fade";
  r: number;
};

export type LightPatch = { x: number; z: number; r: number; a: number };

export type Npc = {
  x: number;
  z: number;
  yaw: number;
  speed: number;
  gait: number;
  wander: number;
};

export type TrailPose = { x: number; z: number; yaw: number; life: number };

export type JuiceEvent =
  | { kind: "pickup"; x: number; z: number }
  | { kind: "dash" }
  | { kind: "stomp"; x: number; z: number }
  | { kind: "hit" }
  | { kind: "death" }
  | { kind: "win" }
  | { kind: "mode" }
  | { kind: "trade" }
  | { kind: "fill"; side: "buy" | "sell"; x: number; z: number }
  | { kind: "poop"; x: number; z: number };

export type Snapshot = {
  x: number;
  z: number;
  yaw: number;
  speed: number;
  gait: number;
  dashT: number;
  dashCd: number;
  isotope: number;
  sucrose: number;
  sucroseTotal: number;
  score: number;
  best: number;
  time: number;
  mode: DriveMode;
  alive: boolean;
  phase: Phase;
  motorL: number;
  motorR: number;
  olfactory: number;
  visual: number;
  cx: number;
  firing: number;
  intendedSteer: number;
  intendedThrottle: number;
  inLight: boolean;
  deadT: number;
  banner: string;
  btc: number;
  btcChg: number;
  deskNote: string;
  deskSide: SignalSide;
  deskEngine: "python" | "ts";
  deskEquity: number;
  deskPnl: number;
  deskQty: number;
  poopLive: number;
  poopEaten: number;
  lastFill: string;
  flyHunt: number;
};

function clamp(v: number, a: number, b: number) {
  return Math.max(a, Math.min(b, v));
}

function wrapAngle(a: number) {
  while (a > Math.PI) a -= Math.PI * 2;
  while (a < -Math.PI) a += Math.PI * 2;
  return a;
}

function mulberry32(seed: number) {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class RoachSim {
  x = 0;
  z = 2;
  yaw = 0;
  speed = 0;
  gait = 0;
  dashT = 0;
  dashCd = 0;
  isotope = 100;
  sucrose = 0;
  sucroseTotal = 8;
  score = 0;
  best = 0;
  time = 0;
  mode: DriveMode = "auto";
  alive = true;
  phase: Phase = "title";
  deadT = 0;
  inLight = false;
  banner = "";
  bannerT = 0;
  trauma = 0;
  fovPunch = 0;
  timeScale = 1;
  btc = 0;
  btcChg = 0;
  deskNote = "Demo desk warming.";
  deskSide: SignalSide = "hold";
  deskEngine: "python" | "ts" = "ts";
  deskCash = 10000;
  deskQty = 0;
  deskEntry = 0;
  deskPnl = 0;
  poopEaten = 0;
  poops: Pickup[] = [];
  lastFill = "waiting for descending neurons";
  flyHunt = 0;
  private tradeCd = 0;
  private marketOlf = 0;
  private marketVis = 0;
  private kenyonConf = 0;

  brain = new FlyBrain();
  pickups: Pickup[] = [];
  obstacles: Obstacle[] = [];
  stomps: Stomp[] = [];
  lights: LightPatch[] = [];
  npcs: Npc[] = [];
  trail: TrailPose[] = [];
  events: JuiceEvent[] = [];

  private stompCd = 4;
  private wander = 0;
  private listeners = new Set<() => void>();
  private snap: Snapshot;
  private emitAcc = 0;

  constructor() {
    try {
      this.best = Number(localStorage.getItem(BEST_KEY) || 0) || 0;
    } catch {
      this.best = 0;
    }
    this.buildWorld(20260921);
    this.loadDesk();
    this.snap = this.makeSnap();
  }

  subscribe = (fn: () => void) => {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  };

  getSnapshot = () => this.snap;

  private emit() {
    this.snap = this.makeSnap();
    for (const l of this.listeners) l();
  }

  private makeSnap(): Snapshot {
    return {
      x: this.x,
      z: this.z,
      yaw: this.yaw,
      speed: this.speed,
      gait: this.gait,
      dashT: this.dashT,
      dashCd: this.dashCd,
      isotope: this.isotope,
      sucrose: this.sucrose,
      sucroseTotal: this.sucroseTotal,
      score: this.score,
      best: this.best,
      time: this.time,
      mode: this.mode,
      alive: this.alive,
      phase: this.phase,
      motorL: this.brain.motorL,
      motorR: this.brain.motorR,
      olfactory: this.brain.olfactory,
      visual: this.brain.visual,
      cx: this.brain.cx,
      firing: this.brain.firing,
      intendedSteer: this.brain.intendedSteer,
      intendedThrottle: this.brain.intendedThrottle,
      inLight: this.inLight,
      deadT: this.deadT,
      banner: this.banner,
      btc: this.btc,
      btcChg: this.btcChg,
      deskNote: this.deskNote,
      deskSide: this.deskSide,
      deskEngine: this.deskEngine,
      deskEquity: this.deskCash + this.deskQty * (this.btc || this.deskEntry),
      deskPnl: this.deskPnl,
      deskQty: this.deskQty,
      poopLive: this.poops.filter((p) => !p.taken).length,
      poopEaten: this.poopEaten,
      lastFill: this.lastFill,
      flyHunt: this.flyHunt,
    };
  }

  startRun() {
    this.x = 0;
    this.z = 3;
    this.yaw = 0;
    this.speed = 0;
    this.gait = 0;
    this.dashT = 0;
    this.dashCd = 0;
    this.isotope = 100;
    this.sucrose = 0;
    this.score = 0;
    this.time = 0;
    this.mode = "auto";
    this.alive = true;
    this.phase = "play";
    this.deadT = 0;
    this.stompCd = 3.5;
    this.tradeCd = 0.4;
    this.deskQty = 0;
    this.deskEntry = 0;
    this.deskPnl = 0;
    this.lastFill = "descending neurons arming";
    this.bannerT = 1.8;
    this.brain.reset();
    this.trail.length = 0;
    this.stomps = [];
    for (const p of this.pickups) p.taken = false;
    this.poops = [];
    this.seedHousePoop();
    this.banner = "FLY IS THE DESK · LEGS LIVE";
    this.emit();
  }

  togglePause() {
    if (this.phase === "play") this.phase = "paused";
    else if (this.phase === "paused") this.phase = "play";
    this.emit();
  }

  applyMarket(tick: MarketTick) {
    if (!Number.isFinite(tick.price) || tick.price <= 0) return;
    this.btc = tick.price;
    this.btcChg = tick.change24;
    this.deskNote = tick.signal.note;
    this.deskSide = tick.signal.side;
    this.deskEngine = tick.signal.engine;
    this.kenyonConf = tick.signal.confidence;
    this.marketOlf =
      tick.signal.side === "buy" ? 0.35 + tick.signal.confidence * 0.55 : tick.change24 > 0 ? 0.22 : 0.05;
    this.marketVis =
      tick.signal.side === "sell" ? 0.35 + tick.signal.confidence * 0.55 : tick.change24 < 0 ? 0.22 : 0.05;
    if (this.deskQty > 0) this.deskPnl = this.deskQty * (tick.price - this.deskEntry);
    else this.deskPnl = 0;

    const equity = this.deskCash + this.deskQty * tick.price;
    if (equity < 800) {
      this.deskCash = 10000;
      this.deskQty = 0;
      this.deskEntry = 0;
      this.deskPnl = 0;
      this.banner = "DEMO REFILL · THE FLY NEVER GOES HUNGRY";
      this.bannerT = 2.2;
    }
    this.saveDesk();
    this.emit();
  }

  private seedHousePoop() {
    this.spawnPoop(1.6, 4.2);
    this.spawnPoop(-2.1, 5.1);
  }

  private spawnPoop(x?: number, z?: number) {
    const live = this.poops.filter((p) => !p.taken).length;
    if (live >= 8) return null;
    let px = x ?? this.x - Math.sin(this.yaw + (Math.random() - 0.5)) * (1.4 + Math.random() * 2.2);
    let pz = z ?? this.z - Math.cos(this.yaw + (Math.random() - 0.5)) * (1.4 + Math.random() * 2.2);
    px = clamp(px, -ARENA + 1, ARENA - 1);
    pz = clamp(pz, -ARENA + 1, ARENA - 1);
    const pile: Pickup = { x: px, z: pz, taken: false, spin: Math.random() * 6, kind: "poop" };
    this.poops.push(pile);
    return pile;
  }

  private shrinkPoop() {
    const live = this.poops.find((p) => !p.taken);
    if (live) live.taken = true;
  }

  private loadDesk() {
    try {
      const raw = localStorage.getItem(DESK_KEY);
      if (!raw) return;
      const s = JSON.parse(raw) as { cash?: number; qty?: number; entry?: number; eaten?: number };
      if (typeof s.cash === "number") this.deskCash = s.cash;
      if (typeof s.qty === "number") this.deskQty = s.qty;
      if (typeof s.entry === "number") this.deskEntry = s.entry;
      if (typeof s.eaten === "number") this.poopEaten = s.eaten;
    } catch {
      /* ignore */
    }
  }

  private saveDesk() {
    try {
      localStorage.setItem(
        DESK_KEY,
        JSON.stringify({
          cash: this.deskCash,
          qty: this.deskQty,
          entry: this.deskEntry,
          eaten: this.poopEaten,
        }),
      );
    } catch {
      /* ignore */
    }
  }

  private buildWorld(seed: number) {
    const rng = mulberry32(seed);
    this.obstacles = [
      { x: -7.4, z: -5.2, r: 1.55, kind: "mug" },
      { x: 6.8, z: -7.1, r: 1.15, kind: "dish" },
      { x: 4.2, z: 6.4, r: 0.7, kind: "cap" },
      { x: -5.6, z: 7.2, r: 0.85, kind: "cable" },
      { x: 8.1, z: 2.4, r: 0.55, kind: "clip" },
      { x: -2.4, z: -8.4, r: 0.5, kind: "spoon" },
      { x: 1.8, z: -3.2, r: 0.45, kind: "crumb" },
    ];
    this.pickups = [];
    let guard = 0;
    while (this.pickups.length < this.sucroseTotal && guard < 80) {
      guard++;
      const x = (rng() * 2 - 1) * (ARENA - 1.6);
      const z = (rng() * 2 - 1) * (ARENA - 1.6);
      if (Math.hypot(x, z) < 2.2) continue;
      if (this.obstacles.some((o) => Math.hypot(o.x - x, o.z - z) < o.r + 0.9)) continue;
      this.pickups.push({ x, z, taken: false, spin: rng() * 6, kind: "sucrose" });
    }
    this.lights = [
      { x: -3, z: 2, r: 2.4, a: 0 },
      { x: 5, z: -4, r: 2.1, a: 2.1 },
    ];
    this.npcs = [
      { x: -4, z: -2, yaw: 1.2, speed: 1.6, gait: 0, wander: 0.4 },
      { x: 5.5, z: 4.2, yaw: -0.6, speed: 1.4, gait: 2, wander: -0.3 },
    ];
    this.stomps = [];
    this.poops = [];
  }

  consumeEvents() {
    const e = this.events.slice();
    this.events.length = 0;
    return e;
  }

  step(dt: number, actions: Actions) {
    if (this.phase === "paused") {
      if (actions.pause) this.togglePause();
      this.emitAcc += dt;
      if (this.emitAcc > 0.08) {
        this.emitAcc = 0;
        this.emit();
      }
      return;
    }
    if (this.phase === "dead" || this.phase === "won") {
      this.deadT += dt;
      this.gait += dt * 8;
      this.speed *= Math.exp(-4 * dt);
      this.brain.step(dt, { olf: 0, visL: 0.2, visR: 0.2, threat: 0, speed: 0 });
      this.updateTrail(dt);
      this.emitAcc += dt;
      if (this.emitAcc > 0.08) {
        this.emitAcc = 0;
        this.emit();
      }
      return;
    }

    if (this.phase === "play" && actions.pause) this.togglePause();

    this.updateLights(dt);
    this.updateStomps(dt);
    this.updateNpcs(dt);

    const senses = this.sense();
    const intent = this.brain.step(dt, senses);
    const seek = this.seekSteer();
    const avoid = clamp((senses.visL - senses.visR) * 1.1, -1, 1);
    const flee = this.fleeSteer();

    let throttle = clamp(intent.throttle * 0.7 + 0.35, 0.2, 1);
    let steer = clamp(intent.steer * 0.35 + seek * 0.7 + avoid + flee, -1, 1);
    if (this.phase === "title") {
      throttle = clamp(0.42 + intent.throttle * 0.25, 0.28, 0.7);
    }
    this.mode = "auto";
    this.huntVote(throttle, this.dashT > 0);
    if (this.phase === "play" && this.alive) this.maybeFlyDash();
    const dashing = this.dashT > 0;

    this.dashT = Math.max(0, this.dashT - dt);
    this.dashCd = Math.max(0, this.dashCd - dt);
    this.timeScale += (1 - this.timeScale) * (1 - Math.exp(-3.2 * dt));
    this.fovPunch *= Math.exp(-4 * dt);
    this.trauma = Math.max(0, this.trauma - dt * 1.6);
    this.bannerT = Math.max(0, this.bannerT - dt);
    if (this.bannerT <= 0) this.banner = "";

    const maxSpeed = dashing ? 16.5 : 4.6;
    const accel = dashing ? 48 : 14;
    const target = dashing ? maxSpeed : throttle * maxSpeed;
    if (target > this.speed) this.speed = Math.min(target, this.speed + accel * dt);
    else this.speed += (target - this.speed) * (1 - Math.exp(-7 * dt));

    const speedFactor = clamp(Math.abs(this.speed) / 4.6, 0.4, 1);
    const reverse = this.speed >= 0 ? 1 : -1;
    this.yaw += steer * 3.35 * speedFactor * reverse * dt;

    const fx = -Math.sin(this.yaw);
    const fz = -Math.cos(this.yaw);
    this.x += fx * this.speed * dt;
    this.z += fz * this.speed * dt;
    this.gait += Math.abs(this.speed) * dt * 11;

    this.collide();
    this.collect();
    this.threatHit();
    if (this.phase === "play") {
      this.tradeCd = Math.max(0, this.tradeCd - dt);
      this.maybeFlyFill(throttle, this.dashT > 0);
    }

    if (this.phase === "play") {
      this.time += dt;
      this.score += Math.abs(this.speed) * dt * 2.2;
      let decay = 1.05;
      if (this.inLight) decay += 3.4;
      if (dashing) decay += 2.2;
      this.isotope = Math.max(0, this.isotope - decay * dt);
      if (this.isotope <= 0) this.kill();
    }

    this.updateTrail(dt);
    this.emitAcc += dt;
    if (this.emitAcc > 0.07) {
      this.emitAcc = 0;
      this.emit();
    }
  }

  private sense() {
    let olf = 0;
    for (const p of this.pickups) {
      if (p.taken) continue;
      const d = Math.hypot(p.x - this.x, p.z - this.z);
      olf = Math.max(olf, clamp(1 - d / 8, 0, 1));
    }
    for (const p of this.poops) {
      if (p.taken) continue;
      const d = Math.hypot(p.x - this.x, p.z - this.z);
      olf = Math.max(olf, clamp(1 - d / 7, 0, 1) * 1.15);
    }
    olf = Math.max(olf, this.marketOlf);
    const probe = (ang: number, dist: number) => {
      const px = this.x - Math.sin(this.yaw + ang) * dist;
      const pz = this.z - Math.cos(this.yaw + ang) * dist;
      for (const o of this.obstacles) {
        const d = Math.hypot(o.x - px, o.z - pz);
        if (d < o.r + 0.35) return 1;
      }
      if (Math.abs(px) > ARENA - 0.4 || Math.abs(pz) > ARENA - 0.4) return 1;
      return 0;
    };
    const visL = Math.max(probe(0.5, 1.2), probe(0.9, 0.9) * 0.7, this.marketVis * 0.65);
    const visR = Math.max(probe(-0.5, 1.2), probe(-0.9, 0.9) * 0.7, this.marketVis * 0.65);

    let threat = 0;
    for (const s of this.stomps) {
      if (s.phase === "fade") continue;
      const d = Math.hypot(s.x - this.x, s.z - this.z);
      threat = Math.max(threat, clamp(1 - d / (s.r + 3), 0, 1));
    }

    this.wander += (Math.random() - 0.5) * 0.8;
    this.wander *= 0.96;

    return {
      olf,
      visL,
      visR,
      threat,
      speed: clamp(this.speed / 8, 0, 1),
    };
  }

  private huntVote(throttle: number, dashing: boolean) {
    let hunt =
      this.brain.olfactory * 0.5 +
      this.brain.cx * 0.3 +
      this.brain.intendedThrottle * 0.2 +
      throttle * 0.45 +
      (this.brain.motorL + this.brain.motorR - 0.8) * 0.18 -
      this.brain.visual * 0.4 -
      (this.inLight ? 0.5 : 0);
    if (dashing) hunt += 0.65;
    if (this.deskSide === "buy") hunt += this.kenyonConf * 0.2;
    if (this.deskSide === "sell") hunt -= this.kenyonConf * 0.2;
    this.flyHunt = clamp(hunt, -1, 1);
    return this.flyHunt;
  }

  private nearestTreat() {
    let nearest = Infinity;
    for (const p of [...this.poops, ...this.pickups]) {
      if (p.taken) continue;
      nearest = Math.min(nearest, Math.hypot(p.x - this.x, p.z - this.z));
    }
    return nearest;
  }

  private maybeFlyDash() {
    if (this.dashCd > 0 || this.isotope < 28) return;
    const threat = this.stomps.some(
      (s) => s.phase !== "fade" && Math.hypot(s.x - this.x, s.z - this.z) < s.r + 2.2,
    );
    const pounce = this.flyHunt > 0.42 && this.nearestTreat() < 2.8 && this.deskQty <= 0;
    const bail = this.flyHunt < -0.2 && this.inLight;
    if (!threat && !pounce && !bail) return;
    this.dashT = 0.55;
    this.dashCd = 2.6;
    this.isotope = Math.max(0, this.isotope - 11);
    this.events.push({ kind: "dash" });
    this.banner = threat || bail ? "SANDEVISTAN · BAIL" : "SANDEVISTAN · FILL";
    this.bannerT = 0.9;
    this.trauma = Math.min(1, this.trauma + 0.45);
    this.fovPunch = 1;
    this.timeScale = 0.28;
  }

  private maybeFlyFill(throttle: number, dashing: boolean) {
    if (this.btc <= 0) return;
    this.huntVote(throttle, dashing);
    if (this.tradeCd > 0) return;
    if (this.flyHunt > 0.28 && this.deskQty <= 0) this.fillBuy(dashing);
    else if (this.flyHunt < -0.1 && this.deskQty > 0) this.fillSell();
  }

  private fillBuy(dashing: boolean) {
    const frac = clamp(0.3 + this.brain.firing * 0.4 + (dashing ? 0.18 : 0), 0.22, 0.82);
    const spend = this.deskCash * frac;
    if (spend < 20 || this.btc <= 0) return;
    this.deskQty = spend / this.btc;
    this.deskCash -= spend;
    this.deskEntry = this.btc;
    this.deskPnl = 0;
    this.tradeCd = dashing ? 0.7 : 1.15;
    this.lastFill = `DN LONG ${this.deskQty.toFixed(5)} @ ${Math.round(this.btc)}`;
    this.banner = "FLY FILL · LONG BTC";
    this.bannerT = 1.5;
    this.events.push({ kind: "fill", side: "buy", x: this.x, z: this.z });
    this.events.push({ kind: "trade" });
    this.saveDesk();
  }

  private fillSell() {
    const qty = this.deskQty;
    if (qty <= 0 || this.btc <= 0) return;
    const proceeds = qty * this.btc;
    const pnl = proceeds - qty * this.deskEntry;
    this.deskCash += proceeds;
    this.deskQty = 0;
    this.deskEntry = 0;
    this.deskPnl = 0;
    this.tradeCd = 1.2;
    this.lastFill = `DN FLAT ${qty.toFixed(5)}  ${pnl >= 0 ? "+" : ""}${Math.round(pnl)}`;
    this.events.push({ kind: "fill", side: "sell", x: this.x, z: this.z });
    this.events.push({ kind: "trade" });
    if (pnl > 0) {
      const pile = this.spawnPoop();
      this.isotope = Math.min(100, this.isotope + 10);
      this.score += 70;
      this.banner = "FLY FILL · FLAT · POOP UP";
      if (pile) this.events.push({ kind: "poop", x: pile.x, z: pile.z });
    } else {
      this.shrinkPoop();
      this.banner = "FLY FILL · FLAT · DIMINISHING POOP";
    }
    this.bannerT = 1.7;
    this.saveDesk();
  }

  private seekSteer() {
    let nearest = Infinity;
    let nx = 0;
    let nz = 0;
    const targets = [
      ...this.poops.filter((p) => !p.taken),
      ...this.pickups.filter((p) => !p.taken),
    ];
    for (const p of targets) {
      const d = Math.hypot(p.x - this.x, p.z - this.z);
      const bias = p.kind === "poop" ? 0.82 : 1;
      if (d * bias < nearest) {
        nearest = d * bias;
        nx = p.x - this.x;
        nz = p.z - this.z;
      }
    }
    if (nearest > 40) return this.wander * 0.3;
    const want = Math.atan2(-nx, -nz);
    return clamp(wrapAngle(want - this.yaw) / 0.7, -1, 1);
  }

  private fleeSteer() {
    let fx = 0;
    let fz = 0;
    for (const s of this.stomps) {
      if (s.phase === "fade") continue;
      const dx = this.x - s.x;
      const dz = this.z - s.z;
      const d = Math.hypot(dx, dz);
      if (d < s.r + 3.5 && d > 0.01) {
        fx += dx / d;
        fz += dz / d;
      }
    }
    if (fx === 0 && fz === 0) return 0;
    const want = Math.atan2(-fx, -fz);
    return clamp(wrapAngle(want - this.yaw) / 0.45, -1, 1);
  }

  private collide() {
    this.x = clamp(this.x, -ARENA, ARENA);
    this.z = clamp(this.z, -ARENA, ARENA);
    for (const o of this.obstacles) {
      const dx = this.x - o.x;
      const dz = this.z - o.z;
      const d = Math.hypot(dx, dz);
      const min = o.r + 0.42;
      if (d < min && d > 1e-4) {
        const n = min / d;
        this.x = o.x + dx * n;
        this.z = o.z + dz * n;
        this.speed *= 0.55;
      }
    }
  }

  private collect() {
    const all = [...this.pickups, ...this.poops];
    for (const p of all) {
      if (p.taken) continue;
      if (Math.hypot(p.x - this.x, p.z - this.z) < 0.72) {
        p.taken = true;
        if (p.kind === "poop") {
          this.poopEaten += 1;
          this.isotope = Math.min(100, this.isotope + 22);
          this.score += 90;
          this.events.push({ kind: "poop", x: p.x, z: p.z });
          this.banner = "FRASS DIVIDEND";
          this.bannerT = 1.1;
          this.saveDesk();
        } else {
          this.sucrose += 1;
          this.isotope = Math.min(100, this.isotope + 18);
          this.score += 120;
          this.events.push({ kind: "pickup", x: p.x, z: p.z });
          this.banner = "SUCROSE · ISOTOPE STABILIZED";
          this.bannerT = 1.1;
          if (this.sucrose >= this.sucroseTotal && this.phase === "play") {
            this.phase = "won";
            this.score += 400;
            this.saveBest();
            this.events.push({ kind: "win" });
            this.banner = "CONNECTOME LOCKED";
            this.bannerT = 4;
          }
        }
      }
    }
  }

  private threatHit() {
    this.inLight = this.lights.some((l) => Math.hypot(l.x - this.x, l.z - this.z) < l.r);
    for (const s of this.stomps) {
      if (s.phase !== "slam") continue;
      if (s.t > 0.12) continue;
      if (Math.hypot(s.x - this.x, s.z - this.z) < s.r * 0.72) {
        this.isotope = Math.max(0, this.isotope - 28);
        this.speed *= 0.2;
        this.trauma = 1;
        this.events.push({ kind: "hit" });
        if (this.isotope <= 0) this.kill();
      }
    }
  }

  private kill() {
    if (!this.alive) return;
    this.alive = false;
    this.phase = "dead";
    this.deadT = 0;
    this.saveBest();
    this.events.push({ kind: "death" });
    this.banner = "MOLECULAR DECAY";
    this.bannerT = 4;
    this.emit();
  }

  private saveBest() {
    this.best = Math.max(this.best, Math.floor(this.score));
    try {
      localStorage.setItem(BEST_KEY, String(this.best));
    } catch {
      /* ignore */
    }
  }

  private updateLights(dt: number) {
    for (const l of this.lights) {
      l.a += dt * 0.35;
      l.x = Math.sin(l.a) * 6.5;
      l.z = Math.cos(l.a * 0.7) * 5.5;
    }
  }

  private updateStomps(dt: number) {
    this.stompCd -= dt * (this.phase === "play" ? 1 : 0.35);
    if (this.stompCd <= 0) {
      this.stompCd = 5.5 + Math.random() * 4;
      const ahead = 2.5 + Math.random() * 3;
      const jx = (Math.random() - 0.5) * 3;
      const jz = (Math.random() - 0.5) * 3;
      const fx = -Math.sin(this.yaw);
      const fz = -Math.cos(this.yaw);
      this.stomps.push({
        x: clamp(this.x + fx * ahead + jx, -ARENA + 1, ARENA - 1),
        z: clamp(this.z + fz * ahead + jz, -ARENA + 1, ARENA - 1),
        t: 0,
        phase: "warn",
        r: 2.1,
      });
    }
    const worldDt = dt * this.timeScale;
    for (const s of this.stomps) {
      s.t += worldDt;
      if (s.phase === "warn" && s.t > 1.15) {
        s.phase = "slam";
        s.t = 0;
        this.events.push({ kind: "stomp", x: s.x, z: s.z });
        this.trauma = Math.min(1, this.trauma + 0.35);
      } else if (s.phase === "slam" && s.t > 0.28) {
        s.phase = "fade";
        s.t = 0;
      }
    }
    this.stomps = this.stomps.filter((s) => !(s.phase === "fade" && s.t > 0.5));
  }

  private updateNpcs(dt: number) {
    for (const n of this.npcs) {
      n.wander += (Math.random() - 0.5) * 2.4 * dt;
      let threatX = 0;
      let threatZ = 0;
      const pd = Math.hypot(n.x - this.x, n.z - this.z);
      if (pd < 3.2) {
        threatX += (n.x - this.x) / (pd + 0.1);
        threatZ += (n.z - this.z) / (pd + 0.1);
      }
      for (const s of this.stomps) {
        const d = Math.hypot(n.x - s.x, n.z - s.z);
        if (d < 4) {
          threatX += (n.x - s.x) / (d + 0.1);
          threatZ += (n.z - s.z) / (d + 0.1);
        }
      }
      const fx = -Math.sin(n.yaw);
      const fz = -Math.cos(n.yaw);
      const wx = fx + n.wander * 0.4 + threatX * 1.6;
      const wz = fz + threatZ * 1.6;
      const want = Math.atan2(-wx, -wz);
      n.yaw += wrapAngle(want - n.yaw) * 2.4 * dt;
      n.speed = 1.5 + (pd < 3.2 ? 2.2 : 0);
      n.x += -Math.sin(n.yaw) * n.speed * dt;
      n.z += -Math.cos(n.yaw) * n.speed * dt;
      n.x = clamp(n.x, -ARENA + 0.5, ARENA - 0.5);
      n.z = clamp(n.z, -ARENA + 0.5, ARENA - 0.5);
      n.gait += n.speed * dt * 11;
      for (const o of this.obstacles) {
        const dx = n.x - o.x;
        const dz = n.z - o.z;
        const d = Math.hypot(dx, dz);
        const min = o.r + 0.4;
        if (d < min && d > 1e-4) {
          n.x = o.x + dx * (min / d);
          n.z = o.z + dz * (min / d);
        }
      }
    }
  }

  private updateTrail(dt: number) {
    if (this.dashT > 0) {
      this.trail.push({ x: this.x, z: this.z, yaw: this.yaw, life: 1 });
      if (this.trail.length > 10) this.trail.shift();
    }
    for (const t of this.trail) t.life -= dt * 2.4;
    this.trail = this.trail.filter((t) => t.life > 0);
  }
}
