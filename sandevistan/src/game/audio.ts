export class SimAudio {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  muted = false;
  private chitterT = 0;

  unlock() {
    const ctx = this.ensure();
    if (ctx.state === "suspended") void ctx.resume();
  }

  private ensure() {
    if (!this.ctx) {
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new Ctx();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.22;
      this.master.connect(this.ctx.destination);
    }
    return this.ctx;
  }

  private tone(
    freq: number,
    dur: number,
    type: OscillatorType,
    gain = 0.2,
    slide = 0,
  ) {
    if (this.muted) return;
    const ctx = this.ensure();
    if (ctx.state === "suspended") return;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    if (slide) osc.frequency.exponentialRampToValueAtTime(Math.max(40, freq * slide), ctx.currentTime + dur);
    g.gain.value = gain;
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    osc.connect(g);
    g.connect(this.master!);
    osc.start();
    osc.stop(ctx.currentTime + dur + 0.02);
  }

  dash() {
    this.tone(180, 0.22, "sawtooth", 0.16, 3.4);
    this.tone(90, 0.28, "square", 0.08, 0.5);
  }

  pickup() {
    this.tone(660, 0.08, "triangle", 0.14, 1.4);
    this.tone(990, 0.12, "sine", 0.1, 1.2);
  }

  hit() {
    this.tone(70, 0.18, "square", 0.18, 0.4);
  }

  stomp() {
    this.tone(48, 0.32, "sine", 0.22, 0.35);
  }

  death() {
    this.tone(220, 0.5, "sawtooth", 0.12, 0.2);
  }

  mode() {
    this.tone(440, 0.06, "square", 0.08);
  }

  chitter(dt: number, speed: number) {
    if (this.muted || speed < 0.4) {
      this.chitterT = 0;
      return;
    }
    this.chitterT += dt * (2.2 + speed * 1.4);
    if (this.chitterT > 1) {
      this.chitterT = 0;
      this.tone(140 + Math.random() * 80, 0.03, "square", 0.03);
    }
  }

  neuronTick(firing: number) {
    if (this.muted || firing < 0.18) return;
    if (Math.random() > firing * 0.08) return;
    this.tone(1200 + firing * 800, 0.015, "sine", 0.02);
  }
}
