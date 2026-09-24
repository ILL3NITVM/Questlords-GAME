export type Actions = {
  throttle: number;
  steer: number;
  dash: boolean;
  dashHeld: boolean;
  toggleMode: boolean;
  pause: boolean;
};

const GAME_CODES = new Set([
  "KeyW",
  "KeyA",
  "KeyS",
  "KeyD",
  "ArrowUp",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "Space",
  "KeyE",
  "ShiftLeft",
  "ShiftRight",
  "KeyP",
  "Escape",
]);

function radialDeadzone(x: number, y: number, dz = 0.15) {
  const m = Math.hypot(x, y);
  if (m < dz) return { x: 0, y: 0 };
  const scale = (m - dz) / (1 - dz) / m;
  return { x: x * scale, y: y * scale };
}

export class Input {
  keys = new Set<string>();
  injected: string[] | null = null;
  injectedSteer: number | null = null;
  touchX = 0;
  touchY = 0;
  touchDash = false;
  touchToggle = false;
  private prevDash = false;
  private prevToggle = false;
  private prevPause = false;
  private dashBuf = 0;
  private onDown: (e: KeyboardEvent) => void;
  private onUp: (e: KeyboardEvent) => void;
  private onBlur: () => void;

  constructor() {
    this.onDown = (e: KeyboardEvent) => {
      if (this.injected) this.injected = null;
      this.keys.add(e.code);
      if (GAME_CODES.has(e.code)) e.preventDefault();
    };
    this.onUp = (e: KeyboardEvent) => {
      this.keys.delete(e.code);
    };
    this.onBlur = () => this.keys.clear();
    window.addEventListener("keydown", this.onDown);
    window.addEventListener("keyup", this.onUp);
    window.addEventListener("blur", this.onBlur);
    document.addEventListener("visibilitychange", this.onBlur);
  }

  setInjectedKeys(codes: string[]) {
    this.injected = codes;
  }

  setInjectedSteer(v: number) {
    this.injectedSteer = v;
  }

  setTouch(x: number, y: number) {
    this.touchX = x;
    this.touchY = y;
  }

  setTouchDash(v: boolean) {
    this.touchDash = v;
  }

  pulseToggle() {
    this.touchToggle = true;
  }

  private has(code: string) {
    if (this.injected) return this.injected.includes(code);
    return this.keys.has(code);
  }

  poll(dt: number): Actions {
    let throttle = 0;
    let steer = 0;
    if (this.has("KeyW") || this.has("ArrowUp")) throttle += 1;
    if (this.has("KeyS") || this.has("ArrowDown")) throttle -= 1;
    if (this.has("KeyA") || this.has("ArrowLeft")) steer += 1;
    if (this.has("KeyD") || this.has("ArrowRight")) steer -= 1;
    if (this.has("ShiftLeft") || this.has("ShiftRight")) {
      if (throttle >= 0) throttle = Math.max(throttle, 0.85);
    }

    const stick = radialDeadzone(this.touchX, this.touchY);
    throttle += stick.y;
    steer += -stick.x;

    const pads = navigator.getGamepads?.() ?? [];
    for (const pad of pads) {
      if (!pad || pad.mapping !== "standard") continue;
      const st = radialDeadzone(pad.axes[0] ?? 0, pad.axes[1] ?? 0);
      throttle += -st.y;
      steer += -st.x;
      if (pad.buttons[0]?.pressed) this.dashBuf = 0.14;
      if (pad.buttons[2]?.pressed) this.touchToggle = true;
      if (pad.buttons[9]?.pressed) this.keys.add("KeyP");
    }

    throttle = Math.max(-1, Math.min(1, throttle));
    steer = Math.max(-1, Math.min(1, steer));
    if (this.injectedSteer !== null) steer = this.injectedSteer;

    const dashDown = this.has("Space") || this.touchDash;
    if (dashDown) this.dashBuf = 0.14;
    this.dashBuf = Math.max(0, this.dashBuf - dt);
    const dash = this.dashBuf > 0 && !this.prevDash;
    if (dash) this.dashBuf = 0;
    this.prevDash = dashDown;

    const toggleDown = this.has("KeyE") || this.touchToggle;
    const toggleMode = toggleDown && !this.prevToggle;
    this.prevToggle = toggleDown;
    this.touchToggle = false;

    const pauseDown = this.has("KeyP") || this.has("Escape");
    const pause = pauseDown && !this.prevPause;
    this.prevPause = pauseDown;

    return { throttle, steer, dash, dashHeld: dashDown, toggleMode, pause };
  }

  dispose() {
    window.removeEventListener("keydown", this.onDown);
    window.removeEventListener("keyup", this.onUp);
    window.removeEventListener("blur", this.onBlur);
    document.removeEventListener("visibilitychange", this.onBlur);
  }
}
