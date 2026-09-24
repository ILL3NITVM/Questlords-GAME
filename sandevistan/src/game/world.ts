import * as THREE from "three";
import { ARENA, type LightPatch, type Obstacle, type Pickup, type Stomp } from "./sim";

function std(color: number, extra?: THREE.MeshStandardMaterialParameters) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness: 0.72,
    metalness: 0.04,
    ...extra,
  });
}

export class World {
  group = new THREE.Group();
  private materials: THREE.Material[] = [];
  private geometries: THREE.BufferGeometry[] = [];
  private pickupMeshes: THREE.Mesh[] = [];
  private pickupLights: THREE.PointLight[] = [];
  private poopMeshes: THREE.Group[] = [];
  private stompMesh: THREE.Mesh;
  private stompMat: THREE.MeshBasicMaterial;
  private stompFill: THREE.Mesh;
  private stompFillMat: THREE.MeshBasicMaterial;
  private lightMeshes: THREE.Mesh[] = [];
  private lightMat: THREE.MeshBasicMaterial;
  private floorTex: THREE.CanvasTexture;
  private tickerTex!: THREE.CanvasTexture;
  private tickerCtx!: CanvasRenderingContext2D;

  constructor() {
    this.floorTex = this.makeFloor();
    this.buildFloor();
    this.buildWalls();
    this.buildLights();
    this.buildTicker();
    this.stompMat = new THREE.MeshBasicMaterial({
      color: 0x1a120e,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    this.materials.push(this.stompMat);
    const sg = new THREE.RingGeometry(0.72, 1, 40);
    this.geometries.push(sg);
    this.stompMesh = new THREE.Mesh(sg, this.stompMat);
    this.stompMesh.rotation.x = -Math.PI / 2;
    this.stompMesh.position.y = 0.03;
    this.group.add(this.stompMesh);
    this.stompFillMat = new THREE.MeshBasicMaterial({
      color: 0x2a1814,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    this.materials.push(this.stompFillMat);
    const fg = new THREE.CircleGeometry(0.72, 32);
    this.geometries.push(fg);
    this.stompFill = new THREE.Mesh(fg, this.stompFillMat);
    this.stompFill.rotation.x = -Math.PI / 2;
    this.stompFill.position.y = 0.028;
    this.group.add(this.stompFill);

    this.lightMat = new THREE.MeshBasicMaterial({
      color: 0xd8c9a0,
      transparent: true,
      opacity: 0.16,
      depthWrite: false,
    });
    this.materials.push(this.lightMat);
  }

  private buildTicker() {
    const c = document.createElement("canvas");
    c.width = 256;
    c.height = 160;
    const ctx = c.getContext("2d")!;
    this.tickerCtx = ctx;
    this.tickerTex = new THREE.CanvasTexture(c);
    this.tickerTex.colorSpace = THREE.SRGBColorSpace;
    const screenMat = new THREE.MeshBasicMaterial({ map: this.tickerTex });
    this.materials.push(screenMat);
    const g = new THREE.Group();
    g.position.set(1.35, 0, 1.7);
    g.rotation.y = 0.35;
    const body = new THREE.Mesh(
      this.geo(new THREE.BoxGeometry(0.52, 0.05, 0.92)),
      this.mat(std(0x1c1e1d, { metalness: 0.45, roughness: 0.38 })),
    );
    body.position.y = 0.035;
    body.castShadow = true;
    const screen = new THREE.Mesh(this.geo(new THREE.PlaneGeometry(0.44, 0.74)), screenMat);
    screen.rotation.x = -Math.PI / 2;
    screen.position.y = 0.064;
    g.add(body, screen);
    this.group.add(g);
    this.drawTicker(0, 0, "FLAT", "waiting");
  }

  updateTicker(price: number, chg: number, book: string, fill: string) {
    this.drawTicker(price, chg, book, fill);
    this.tickerTex.needsUpdate = true;
  }

  private drawTicker(price: number, chg: number, book: string, fill: string) {
    const g = this.tickerCtx;
    g.fillStyle = "#101412";
    g.fillRect(0, 0, 256, 160);
    g.fillStyle = "#8dbea8";
    g.font = "600 14px ui-monospace, monospace";
    g.fillText("FLY DESK  DEMO", 16, 28);
    g.fillStyle = "#e8e0d0";
    g.font = "700 28px ui-monospace, monospace";
    g.fillText(price ? `$${Math.round(price).toLocaleString()}` : "BTC —", 16, 64);
    g.fillStyle = chg >= 0 ? "#8dbea8" : "#c45c4a";
    g.font = "600 16px ui-monospace, monospace";
    g.fillText(price ? `${chg >= 0 ? "+" : ""}${(chg * 100).toFixed(2)}%` : "", 16, 88);
    g.fillStyle = "#c4b8a4";
    g.font = "500 13px ui-monospace, monospace";
    g.fillText(book, 16, 114);
    g.fillStyle = "#9aa39f";
    g.font = "500 11px ui-monospace, monospace";
    g.fillText(fill.slice(0, 28), 16, 138);
  }

  private geo<T extends THREE.BufferGeometry>(g: T) {
    this.geometries.push(g);
    return g;
  }
  private mat<T extends THREE.Material>(m: T) {
    this.materials.push(m);
    return m;
  }

  private makeFloor() {
    const c = document.createElement("canvas");
    c.width = 512;
    c.height = 512;
    const g = c.getContext("2d")!;
    g.fillStyle = "#c4b8a4";
    g.fillRect(0, 0, 512, 512);
    const tile = 128;
    for (let y = 0; y < 4; y++) {
      for (let x = 0; x < 4; x++) {
        const shade = 186 + ((x * 7 + y * 13) % 18);
        g.fillStyle = `rgb(${shade},${shade - 12},${shade - 28})`;
        g.fillRect(x * tile + 3, y * tile + 3, tile - 6, tile - 6);
        g.fillStyle = "rgba(90,70,50,0.08)";
        g.fillRect(x * tile + 18, y * tile + 40, 50, 22);
      }
    }
    g.strokeStyle = "#9a9080";
    g.lineWidth = 6;
    for (let i = 0; i <= 4; i++) {
      g.beginPath();
      g.moveTo(i * tile, 0);
      g.lineTo(i * tile, 512);
      g.stroke();
      g.beginPath();
      g.moveTo(0, i * tile);
      g.lineTo(512, i * tile);
      g.stroke();
    }
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(8, 8);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    return tex;
  }

  private buildFloor() {
    const size = ARENA * 2 + 4;
    const floor = new THREE.Mesh(
      this.geo(new THREE.PlaneGeometry(size, size)),
      this.mat(std(0xffffff, { map: this.floorTex, roughness: 0.82 })),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    this.group.add(floor);
  }

  private buildWalls() {
    const wall = this.mat(std(0x8d8680));
    const base = this.mat(std(0x5c5852));
    const h = 2.4;
    const t = 0.4;
    const span = ARENA * 2 + 0.4;
    const sides: [number, number, number, number][] = [
      [0, ARENA + t / 2, span, t],
      [0, -ARENA - t / 2, span, t],
      [ARENA + t / 2, 0, t, span],
      [-ARENA - t / 2, 0, t, span],
    ];
    for (const [x, z, w, d] of sides) {
      const m = new THREE.Mesh(this.geo(new THREE.BoxGeometry(w, h, d)), wall);
      m.position.set(x, h / 2, z);
      m.castShadow = true;
      m.receiveShadow = true;
      this.group.add(m);
      const b = new THREE.Mesh(this.geo(new THREE.BoxGeometry(w + 0.02, 0.28, d + 0.02)), base);
      b.position.set(x, 0.14, z);
      this.group.add(b);
    }
  }

  private buildLights() {
    const hemi = new THREE.HemisphereLight(0xcdd4cc, 0x2a241c, 0.55);
    this.group.add(hemi);
    const dir = new THREE.DirectionalLight(0xf3efe6, 1.35);
    dir.position.set(8, 16, 6);
    dir.castShadow = true;
    dir.shadow.mapSize.set(1024, 1024);
    dir.shadow.camera.near = 2;
    dir.shadow.camera.far = 40;
    dir.shadow.camera.left = -18;
    dir.shadow.camera.right = 18;
    dir.shadow.camera.top = 18;
    dir.shadow.camera.bottom = -18;
    dir.shadow.bias = -0.0008;
    this.group.add(dir);
    const fill = new THREE.DirectionalLight(0x8dbea8, 0.18);
    fill.position.set(-6, 8, -4);
    this.group.add(fill);

    const fixture = this.mat(std(0x2a2e2c, { metalness: 0.6, roughness: 0.3 }));
    const glow = this.mat(std(0xf2f0e4, { emissive: 0xf2f0e4, emissiveIntensity: 0.8 }));
    for (const z of [-6, 0, 6]) {
      const bar = new THREE.Mesh(this.geo(new THREE.BoxGeometry(10, 0.08, 0.4)), fixture);
      bar.position.set(0, 4.6, z);
      const tube = new THREE.Mesh(this.geo(new THREE.BoxGeometry(9.4, 0.06, 0.18)), glow);
      tube.position.set(0, 4.52, z);
      this.group.add(bar, tube);
    }
  }

  buildProps(obstacles: Obstacle[]) {
    for (const o of obstacles) {
      const prop = this.makeProp(o);
      prop.position.set(o.x, 0, o.z);
      this.group.add(prop);
    }
  }

  private makeProp(o: Obstacle) {
    const g = new THREE.Group();
    if (o.kind === "mug") {
      const ceramic = this.mat(std(0xe8e2d6, { roughness: 0.35 }));
      const body = new THREE.Mesh(this.geo(new THREE.CylinderGeometry(1.45, 1.35, 3.1, 24, 1, true)), ceramic);
      body.position.y = 1.55;
      body.castShadow = true;
      const bottom = new THREE.Mesh(this.geo(new THREE.CircleGeometry(1.35, 24)), ceramic);
      bottom.rotation.x = -Math.PI / 2;
      bottom.position.y = 0.02;
      const handle = new THREE.Mesh(this.geo(new THREE.TorusGeometry(0.7, 0.12, 8, 16, Math.PI)), ceramic);
      handle.position.set(1.45, 1.7, 0);
      handle.rotation.y = Math.PI / 2;
      g.add(body, bottom, handle);
    } else if (o.kind === "dish") {
      const glass = this.mat(std(0xdfe8e4, { transparent: true, opacity: 0.35, roughness: 0.2, metalness: 0.1 }));
      const dish = new THREE.Mesh(this.geo(new THREE.CylinderGeometry(1.15, 1.15, 0.18, 28, 1, true)), glass);
      dish.position.y = 0.12;
      const floor = new THREE.Mesh(this.geo(new THREE.CircleGeometry(1.12, 28)), glass);
      floor.rotation.x = -Math.PI / 2;
      floor.position.y = 0.04;
      g.add(dish, floor);
    } else if (o.kind === "cap") {
      const m = this.mat(std(0x3d5c4a));
      const cap = new THREE.Mesh(this.geo(new THREE.CylinderGeometry(0.7, 0.7, 0.22, 20)), m);
      cap.position.y = 0.12;
      cap.castShadow = true;
      g.add(cap);
    } else if (o.kind === "cable") {
      const pts = [
        new THREE.Vector3(-1.6, 0.08, 0),
        new THREE.Vector3(-0.4, 0.1, 0.5),
        new THREE.Vector3(0.5, 0.08, -0.3),
        new THREE.Vector3(1.8, 0.1, 0.2),
      ];
      const curve = new THREE.CatmullRomCurve3(pts);
      const cable = new THREE.Mesh(
        this.geo(new THREE.TubeGeometry(curve, 24, 0.08, 6, false)),
        this.mat(std(0x1c1c1c, { roughness: 0.45 })),
      );
      cable.castShadow = true;
      g.add(cable);
    } else if (o.kind === "clip") {
      const metal = this.mat(std(0x9aa3a0, { metalness: 0.85, roughness: 0.25 }));
      const a = new THREE.Mesh(this.geo(new THREE.TorusGeometry(0.28, 0.035, 6, 18, Math.PI * 1.2)), metal);
      a.rotation.x = Math.PI / 2;
      a.position.y = 0.06;
      g.add(a);
    } else if (o.kind === "spoon") {
      const metal = this.mat(std(0xb7bdc0, { metalness: 0.8, roughness: 0.22 }));
      const handle = new THREE.Mesh(this.geo(new THREE.BoxGeometry(0.16, 0.06, 2.6)), metal);
      handle.position.y = 0.05;
      handle.castShadow = true;
      const bowl = new THREE.Mesh(this.geo(new THREE.SphereGeometry(0.28, 10, 8, 0, Math.PI * 2, 0, Math.PI / 2)), metal);
      bowl.position.set(0, 0.04, -1.4);
      g.add(handle, bowl);
    } else {
      const crumb = new THREE.Mesh(this.geo(new THREE.DodecahedronGeometry(0.28, 0)), this.mat(std(0xc4a574)));
      crumb.position.y = 0.18;
      crumb.castShadow = true;
      g.add(crumb);
    }
    return g;
  }

  buildPickups(pickups: Pickup[]) {
    const sugar = this.mat(
      std(0xd8efe4, {
        roughness: 0.22,
        metalness: 0.08,
        emissive: 0x8dbea8,
        emissiveIntensity: 0.55,
      }),
    );
    const g = this.geo(new THREE.OctahedronGeometry(0.32, 0));
    for (const p of pickups) {
      const m = new THREE.Mesh(g, sugar);
      m.position.set(p.x, 0.28, p.z);
      m.castShadow = true;
      this.group.add(m);
      this.pickupMeshes.push(m);
      const l = new THREE.PointLight(0x8dbea8, 0.55, 3.2);
      l.position.set(p.x, 0.5, p.z);
      this.group.add(l);
      this.pickupLights.push(l);
    }
  }

  buildPoops(max = 8) {
    const dung = this.mat(std(0x5a3c28, { roughness: 0.86, metalness: 0.02 }));
    const nub = this.geo(new THREE.SphereGeometry(0.16, 8, 6));
    for (let i = 0; i < max; i++) {
      const g = new THREE.Group();
      for (const [x, z, s] of [
        [0, 0, 1],
        [0.14, 0.08, 0.72],
        [-0.12, 0.06, 0.64],
      ] as const) {
        const m = new THREE.Mesh(nub, dung);
        m.position.set(x, 0.1 * s, z);
        m.scale.setScalar(s);
        m.castShadow = true;
        g.add(m);
      }
      g.visible = false;
      this.group.add(g);
      this.poopMeshes.push(g);
    }
  }

  buildLightPatches(n: number) {
    const g = this.geo(new THREE.CircleGeometry(1, 24));
    for (let i = 0; i < n; i++) {
      const m = new THREE.Mesh(g, this.lightMat);
      m.rotation.x = -Math.PI / 2;
      m.position.y = 0.03;
      this.group.add(m);
      this.lightMeshes.push(m);
    }
  }

  update(pickups: Pickup[], poops: Pickup[], stomps: Stomp[], lights: LightPatch[], t: number) {
    pickups.forEach((p, i) => {
      const m = this.pickupMeshes[i];
      const l = this.pickupLights[i];
      if (!m) return;
      m.visible = !p.taken;
      if (l) l.visible = !p.taken;
      if (!p.taken) {
        m.rotation.y = t * 1.4 + p.spin;
        m.position.y = 0.26 + Math.sin(t * 2.2 + p.spin) * 0.06;
      }
    });

    this.poopMeshes.forEach((g, i) => {
      const p = poops[i];
      if (!p || p.taken) {
        g.visible = false;
        return;
      }
      g.visible = true;
      g.position.set(p.x, 0, p.z);
      g.rotation.y = p.spin;
      const bob = 1 + Math.sin(t * 2 + p.spin) * 0.04;
      g.scale.setScalar(bob);
    });

    const s = stomps.find((x) => x.phase !== "fade") ?? stomps[stomps.length - 1];
    if (s) {
      this.stompMesh.visible = true;
      this.stompFill.visible = true;
      this.stompMesh.position.set(s.x, 0.03, s.z);
      this.stompFill.position.set(s.x, 0.028, s.z);
      const scale = s.r * (s.phase === "warn" ? 0.55 + s.t * 0.45 : 1);
      this.stompMesh.scale.setScalar(scale);
      this.stompFill.scale.setScalar(scale);
      if (s.phase === "warn") {
        this.stompMat.opacity = 0.35 + s.t * 0.35;
        this.stompFillMat.opacity = 0.08 + s.t * 0.1;
        this.stompMat.color.set(0xc45c4a);
      } else if (s.phase === "slam") {
        this.stompMat.opacity = 0.7;
        this.stompFillMat.opacity = 0.28;
        this.stompMat.color.set(0x2a1814);
      } else {
        this.stompMat.opacity = 0.2 * (1 - s.t / 0.5);
        this.stompFillMat.opacity = 0.08 * (1 - s.t / 0.5);
      }
    } else {
      this.stompMat.opacity = 0;
      this.stompFillMat.opacity = 0;
    }

    lights.forEach((l, i) => {
      const m = this.lightMeshes[i];
      if (!m) return;
      m.position.set(l.x, 0.03, l.z);
      m.scale.setScalar(l.r);
    });
  }

  dispose() {
    this.group.removeFromParent();
    this.floorTex.dispose();
    this.tickerTex.dispose();
    for (const g of this.geometries) g.dispose();
    for (const m of this.materials) m.dispose();
  }
}
