import * as THREE from "three";
import { Input } from "./input";
import { RoachSim, FIXED_DT } from "./sim";
import { World } from "./world";
import { RoachView } from "./roach";
import { Particles } from "./particles";
import { SimAudio } from "./audio";
import type { ControlsProbe } from "./controlsTest";

const _fwd = new THREE.Vector3();
const _cam = new THREE.Vector3();
const _look = new THREE.Vector3();
const _up = new THREE.Vector3(0, 1, 0);

export class Game {
  sim = new RoachSim();
  input = new Input();
  audio = new SimAudio();
  renderer: THREE.WebGLRenderer;
  scene = new THREE.Scene();
  camera: THREE.PerspectiveCamera;
  private world: World;
  private player: RoachView;
  private npcs: RoachView[] = [];
  private ghosts: THREE.Group[] = [];
  private ghostMat: THREE.MeshStandardMaterial;
  private ghostGeo: THREE.BufferGeometry;
  private particles: Particles;
  private timer = new THREE.Timer();
  private acc = 0;
  private raf = 0;
  private disposed = false;
  private canvas: HTMLCanvasElement;
  private ro: ResizeObserver;
  private orbitA = 0.8;
  private reduced: boolean;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.08;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.camera = new THREE.PerspectiveCamera(50, 1, 0.08, 80);
    this.scene.background = new THREE.Color(0x0c0f0d);
    this.scene.fog = new THREE.Fog(0x0c0f0d, 12, 38);

    this.world = new World();
    this.world.buildProps(this.sim.obstacles);
    this.world.buildPickups(this.sim.pickups);
    this.world.buildPoops();
    this.world.buildLightPatches(this.sim.lights.length);
    this.scene.add(this.world.group);

    this.player = new RoachView("cyborg");
    this.scene.add(this.player.group);
    for (const _ of this.sim.npcs) {
      const v = new RoachView("wild");
      this.npcs.push(v);
      this.scene.add(v.group);
    }

    this.ghostMat = new THREE.MeshStandardMaterial({
      color: 0x8dbea8,
      transparent: true,
      opacity: 0.22,
      emissive: 0x8dbea8,
      emissiveIntensity: 0.6,
      depthWrite: false,
    });
    const ghostGeo = new THREE.SphereGeometry(1, 10, 8);
    this.ghostGeo = ghostGeo;
    for (let i = 0; i < 8; i++) {
      const g = new THREE.Group();
      const body = new THREE.Mesh(ghostGeo, this.ghostMat);
      body.scale.set(0.22, 0.12, 0.5);
      g.add(body);
      g.visible = false;
      this.scene.add(g);
      this.ghosts.push(g);
    }

    this.particles = new Particles();
    this.scene.add(this.particles.points);

    this.timer.connect(document);
    this.resize();
    this.ro = new ResizeObserver(() => this.resize());
    this.ro.observe(canvas.parentElement ?? canvas);

    this.installProbe();
    this.loop = this.loop.bind(this);
  }

  private installProbe() {
    const probe: ControlsProbe = {
      getYaw: () => this.sim.yaw,
      getSpeed: () => this.sim.speed,
      setKeys: (codes) => this.input.setInjectedKeys(codes),
      setSteer: (v) => this.input.setInjectedSteer(v),
    };
    window.__controlsTest = probe;
  }

  start() {
    this.timer.update();
    this.raf = requestAnimationFrame(this.loop);
  }

  private loop() {
    if (this.disposed) return;
    this.raf = requestAnimationFrame(this.loop);
    this.timer.update();
    const dt = Math.min(this.timer.getDelta(), 0.1);
    this.acc += dt;
    const actions = this.input.poll(dt);
    let steps = 0;
    while (this.acc >= FIXED_DT && steps < 5) {
      this.sim.step(FIXED_DT, actions);
      this.acc -= FIXED_DT;
      steps++;
    }
    this.present(dt);
  }

  private present(dt: number) {
    const s = this.sim;
    for (const ev of s.consumeEvents()) {
      if (ev.kind === "pickup") {
        this.audio.pickup();
        this.particles.burst(ev.x, 0.4, ev.z, 18, new THREE.Color(0xe8e0d0), 1.4);
      } else if (ev.kind === "dash") {
        this.audio.dash();
      } else if (ev.kind === "stomp") {
        this.audio.stomp();
        this.particles.burst(ev.x, 0.2, ev.z, 22, new THREE.Color(0x3a2a22), 2.2);
      } else if (ev.kind === "hit") {
        this.audio.hit();
      } else if (ev.kind === "death") {
        this.audio.death();
      } else if (ev.kind === "poop") {
        this.audio.pickup();
        this.particles.burst(ev.x, 0.3, ev.z, 16, new THREE.Color(0x6a4a32), 1.2);
      } else if (ev.kind === "fill") {
        this.audio.mode();
        this.particles.burst(
          ev.x,
          0.35,
          ev.z,
          20,
          new THREE.Color(ev.side === "buy" ? 0x8dbea8 : 0xc45c4a),
          1.6,
        );
      } else if (ev.kind === "trade") {
        this.audio.mode();
      } else if (ev.kind === "mode") {
        this.audio.mode();
      } else if (ev.kind === "win") {
        this.audio.pickup();
      }
    }
    this.audio.chitter(dt, s.speed);
    this.audio.neuronTick(s.brain.firing);

    this.player.update({
      x: s.x,
      z: s.z,
      yaw: s.yaw,
      speed: s.speed,
      gait: s.gait,
      dashT: s.dashT,
      firing: s.brain.firing,
      alive: s.alive,
      deadT: s.deadT,
      motorL: s.brain.motorL,
      motorR: s.brain.motorR,
    });
    s.npcs.forEach((n, i) => {
      this.npcs[i]?.update({
        x: n.x,
        z: n.z,
        yaw: n.yaw,
        speed: n.speed,
        gait: n.gait,
        dashT: 0,
        firing: 0.1,
        alive: true,
        deadT: 0,
        motorL: 0.3,
        motorR: 0.3,
      });
    });

    s.trail.forEach((t, i) => {
      const g = this.ghosts[i];
      if (!g) return;
      g.visible = true;
      g.position.set(t.x, 0.16, t.z);
      g.rotation.y = t.yaw;
      g.scale.setScalar(0.85 + (1 - t.life) * 0.4);
    });
    for (let i = s.trail.length; i < this.ghosts.length; i++) {
      const g = this.ghosts[i];
      if (g) g.visible = false;
    }
    this.ghostMat.opacity = s.dashT > 0 ? 0.28 : 0.12;

    this.world.update(s.pickups, s.poops, s.stomps, s.lights, this.timer.getElapsed());
    this.world.updateTicker(
      s.btc,
      s.btcChg,
      s.deskQty > 0 ? `LONG ${s.deskQty.toFixed(4)}` : "FLAT",
      s.lastFill,
    );
    this.particles.update(dt);
    this.updateCamera(dt);
    this.renderer.render(this.scene, this.camera);
  }

  private updateCamera(dt: number) {
    const s = this.sim;
    _fwd.set(-Math.sin(s.yaw), 0, -Math.cos(s.yaw));
    const playing = s.phase === "play" || s.phase === "paused" || s.phase === "dead" || s.phase === "won";

    if (!playing) {
      this.orbitA += dt * 0.22;
      const r = 5.2;
      _cam.set(s.x + Math.sin(this.orbitA) * r, 2.35, s.z + Math.cos(this.orbitA) * r);
      _look.set(s.x, 0.28, s.z);
    } else {
      const dist = 4.35;
      const height = 1.95;
      _cam.copy(this.player.group.position);
      _cam.y = 0;
      _cam.addScaledVector(_up, height);
      _cam.addScaledVector(_fwd, -dist);
      _look.copy(this.player.group.position);
      _look.y = 0.35;
      _look.addScaledVector(_fwd, 1.35);
    }

    if (!this.reduced && s.trauma > 0) {
      const mag = s.trauma * s.trauma * 0.18;
      _cam.x += (Math.random() - 0.5) * mag;
      _cam.y += (Math.random() - 0.5) * mag * 0.6;
    }

    const k = playing ? 6.5 : 3.2;
    const a = 1 - Math.exp(-k * dt);
    this.camera.position.lerp(_cam, a);
    this.camera.lookAt(_look);
    const fov = 50 + s.fovPunch * 10;
    if (Math.abs(this.camera.fov - fov) > 0.05) {
      this.camera.fov = fov;
      this.camera.updateProjectionMatrix();
    }
  }

  private resize() {
    const parent = this.canvas.parentElement ?? this.canvas;
    const w = Math.max(1, parent.clientWidth);
    const h = Math.max(1, parent.clientHeight);
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.raf);
    this.ro.disconnect();
    this.timer.disconnect();
    this.input.dispose();
    this.player.dispose();
    for (const n of this.npcs) n.dispose();
    this.world.dispose();
    this.particles.dispose();
    this.ghostMat.dispose();
    this.ghostGeo.dispose();
    this.renderer.dispose();
    if (window.__controlsTest) delete window.__controlsTest;
  }
}
