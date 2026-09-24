import * as THREE from "three";

type Leg = {
  root: THREE.Group;
  femur: THREE.Group;
  tibia: THREE.Group;
  side: number;
  index: number;
};

function mat(color: number, extra?: THREE.MeshStandardMaterialParameters) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness: 0.58,
    metalness: 0.04,
    ...extra,
  });
}

export class RoachView {
  group = new THREE.Group();
  private rig = new THREE.Group();
  private legs: Leg[] = [];
  private antennae: THREE.Group[] = [];
  private leds: THREE.Mesh[] = [];
  private ledMat: THREE.MeshStandardMaterial;
  private implantLight: THREE.PointLight | null = null;
  private materials: THREE.Material[] = [];
  private geometries: THREE.BufferGeometry[] = [];
  kind: "cyborg" | "wild";

  constructor(kind: "cyborg" | "wild") {
    this.kind = kind;
    this.ledMat = mat(0x8dbea8, {
      emissive: 0x8dbea8,
      emissiveIntensity: kind === "cyborg" ? 1.6 : 0,
      roughness: 0.3,
    });
    this.materials.push(this.ledMat);
    this.build();
    this.group.add(this.rig);
  }

  private geo<T extends THREE.BufferGeometry>(g: T) {
    this.geometries.push(g);
    return g;
  }

  private mesh(g: THREE.BufferGeometry, m: THREE.Material) {
    const mesh = new THREE.Mesh(g, m);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    return mesh;
  }

  private build() {
    const chitin = mat(0x6a3d28);
    const dark = mat(0x3a2218);
    const stripe = mat(0x24150f);
    const wing = mat(0x7a4a32, { transparent: true, opacity: 0.55, roughness: 0.72 });
    const metal = mat(0x2c3230, { metalness: 0.82, roughness: 0.28 });
    const eye = mat(0x0c0a08, { roughness: 0.2 });
    this.materials.push(chitin, dark, stripe, wing, metal, eye);

    const abdomen = this.mesh(this.geo(new THREE.SphereGeometry(1, 18, 12)), chitin);
    abdomen.scale.set(0.22, 0.13, 0.4);
    abdomen.position.set(0, 0.13, 0.22);
    this.rig.add(abdomen);

    for (let i = 0; i < 5; i++) {
      const ring = this.mesh(this.geo(new THREE.TorusGeometry(0.2, 0.012, 6, 16)), dark);
      ring.rotation.x = Math.PI / 2;
      ring.position.set(0, 0.16, 0.02 + i * 0.1);
      ring.scale.set(1 - i * 0.08, 1.4, 1);
      this.rig.add(ring);
    }

    const thorax = this.mesh(this.geo(new THREE.SphereGeometry(1, 16, 12)), chitin);
    thorax.scale.set(0.2, 0.12, 0.18);
    thorax.position.set(0, 0.14, -0.18);
    this.rig.add(thorax);

    const pronotum = this.mesh(this.geo(new THREE.SphereGeometry(1, 16, 12)), chitin);
    pronotum.scale.set(0.24, 0.08, 0.16);
    pronotum.position.set(0, 0.18, -0.32);
    this.rig.add(pronotum);

    const s1 = this.mesh(this.geo(new THREE.BoxGeometry(0.04, 0.02, 0.18)), stripe);
    s1.position.set(-0.06, 0.255, -0.3);
    const s2 = s1.clone();
    s2.position.x = 0.06;
    this.rig.add(s1, s2);

    const head = this.mesh(this.geo(new THREE.SphereGeometry(1, 12, 10)), dark);
    head.scale.set(0.1, 0.09, 0.11);
    head.position.set(0, 0.13, -0.5);
    this.rig.add(head);

    const eyeG = this.geo(new THREE.SphereGeometry(0.035, 8, 6));
    const eL = this.mesh(eyeG, eye);
    eL.position.set(-0.08, 0.15, -0.54);
    const eR = this.mesh(eyeG, eye);
    eR.position.set(0.08, 0.15, -0.54);
    this.rig.add(eL, eR);

    const wingG = this.geo(new THREE.PlaneGeometry(0.28, 0.7));
    const wL = this.mesh(wingG, wing);
    wL.rotation.x = -Math.PI / 2;
    wL.rotation.z = 0.18;
    wL.position.set(-0.08, 0.22, 0.08);
    const wR = this.mesh(wingG, wing);
    wR.rotation.x = -Math.PI / 2;
    wR.rotation.z = -0.18;
    wR.position.set(0.08, 0.22, 0.08);
    this.rig.add(wL, wR);

    const cercusG = this.geo(new THREE.CylinderGeometry(0.008, 0.004, 0.16, 5));
    cercusG.rotateX(Math.PI / 2);
    const cL = this.mesh(cercusG, dark);
    cL.position.set(-0.08, 0.1, 0.58);
    cL.rotation.y = 0.4;
    const cR = this.mesh(cercusG, dark);
    cR.position.set(0.08, 0.1, 0.58);
    cR.rotation.y = -0.4;
    this.rig.add(cL, cR);

    this.buildAntennae(dark);
    this.buildLegs(dark);

    if (this.kind === "cyborg") {
      const pack = this.mesh(this.geo(new THREE.BoxGeometry(0.18, 0.07, 0.16)), metal);
      pack.position.set(0, 0.28, -0.16);
      this.rig.add(pack);
      const ridge = this.mesh(this.geo(new THREE.BoxGeometry(0.2, 0.012, 0.02)), this.ledMat);
      ridge.position.set(0, 0.32, -0.16);
      this.rig.add(ridge);
      const ledG = this.geo(new THREE.SphereGeometry(0.018, 8, 6));
      for (const [x, z] of [
        [-0.05, -0.2],
        [0.05, -0.2],
        [-0.05, -0.12],
        [0.05, -0.12],
      ] as const) {
        const led = this.mesh(ledG, this.ledMat);
        led.position.set(x, 0.325, z);
        this.rig.add(led);
        this.leds.push(led);
      }
      const wireG = this.geo(new THREE.CylinderGeometry(0.006, 0.006, 0.22, 5));
      const w1 = this.mesh(wireG, metal);
      w1.position.set(-0.07, 0.24, -0.34);
      w1.rotation.x = 0.9;
      w1.rotation.z = 0.3;
      const w2 = this.mesh(wireG, metal);
      w2.position.set(0.07, 0.24, -0.34);
      w2.rotation.x = 0.9;
      w2.rotation.z = -0.3;
      this.rig.add(w1, w2);

      this.implantLight = new THREE.PointLight(0x8dbea8, 0.55, 3.2);
      this.implantLight.position.set(0, 0.4, -0.16);
      this.rig.add(this.implantLight);
    }
  }

  private buildAntennae(matDark: THREE.Material) {
    const segG = this.geo(new THREE.CylinderGeometry(0.01, 0.006, 0.18, 5));
    segG.rotateX(Math.PI / 2);
    for (const side of [-1, 1]) {
      const root = new THREE.Group();
      root.position.set(side * 0.06, 0.16, -0.54);
      let parent: THREE.Object3D = root;
      for (let i = 0; i < 4; i++) {
        const seg = new THREE.Group();
        const m = this.mesh(segG, matDark);
        m.position.z = -0.09;
        seg.add(m);
        if (i === 0) {
          seg.rotation.x = -0.45;
          seg.rotation.y = side * 0.35;
        } else {
          seg.position.z = -0.18;
          seg.rotation.x = -0.18;
          seg.rotation.y = side * 0.08;
        }
        parent.add(seg);
        parent = seg;
      }
      this.rig.add(root);
      this.antennae.push(root);
    }
  }

  private buildLegs(matDark: THREE.Material) {
    const coxaG = this.geo(new THREE.CylinderGeometry(0.022, 0.018, 0.1, 5));
    const femurG = this.geo(new THREE.CylinderGeometry(0.018, 0.014, 0.28, 5));
    const tibiaG = this.geo(new THREE.CylinderGeometry(0.012, 0.008, 0.32, 5));
    coxaG.rotateZ(Math.PI / 2);
    femurG.rotateZ(Math.PI / 2);
    tibiaG.rotateZ(Math.PI / 2);

    const layout = [
      { x: -0.12, z: -0.28, s: -1, len: 1.05 },
      { x: 0.12, z: -0.28, s: 1, len: 1.05 },
      { x: -0.16, z: -0.08, s: -1, len: 1.15 },
      { x: 0.16, z: -0.08, s: 1, len: 1.15 },
      { x: -0.14, z: 0.14, s: -1, len: 1.3 },
      { x: 0.14, z: 0.14, s: 1, len: 1.3 },
    ];

    layout.forEach((L, index) => {
      const root = new THREE.Group();
      root.position.set(L.x, 0.12, L.z);
      const coxa = this.mesh(coxaG, matDark);
      coxa.position.x = L.s * 0.05;
      root.add(coxa);
      const femur = new THREE.Group();
      femur.position.x = L.s * 0.1;
      const femurM = this.mesh(femurG, matDark);
      femurM.position.x = L.s * 0.14 * L.len;
      femurM.scale.x = L.len;
      femur.add(femurM);
      root.add(femur);
      const tibia = new THREE.Group();
      tibia.position.x = L.s * 0.28 * L.len;
      const tibiaM = this.mesh(tibiaG, matDark);
      tibiaM.position.x = L.s * 0.16 * L.len;
      tibiaM.scale.x = L.len;
      tibia.add(tibiaM);
      femur.add(tibia);
      this.rig.add(root);
      this.legs.push({ root, femur, tibia, side: L.s, index });
    });
  }

  update(state: {
    x: number;
    z: number;
    yaw: number;
    speed: number;
    gait: number;
    dashT: number;
    firing: number;
    alive: boolean;
    deadT: number;
    motorL: number;
    motorR: number;
  }) {
    this.group.position.set(state.x, 0, state.z);
    this.group.rotation.y = state.yaw;

    const dead = !state.alive;
    const roll = dead ? Math.min(1, state.deadT / 0.55) : 0;
    const ease = 1 - Math.pow(1 - roll, 3);
    this.rig.rotation.z = ease * Math.PI;
    this.rig.position.y = dead ? 0.08 + ease * 0.12 : 0.02 + Math.sin(state.gait * 2) * 0.015;

    const bob = Math.sin(state.gait) * 0.04 * Math.min(1, state.speed / 3);
    this.rig.rotation.x = dead ? 0 : bob;

    for (const leg of this.legs) {
      const tripod = leg.index === 0 || leg.index === 3 || leg.index === 4 ? 0 : Math.PI;
      const swing = Math.sin(state.gait + tripod);
      const lift = Math.max(0, swing) * 0.35;
      const stride = swing * 0.28;
      if (dead) {
        const twitch = Math.sin(state.deadT * 18 + leg.index) * 0.2;
        leg.root.rotation.z = leg.side * (0.4 + twitch);
        leg.femur.rotation.z = leg.side * 0.3;
        leg.tibia.rotation.z = -leg.side * 0.5;
      } else {
        leg.root.rotation.y = stride * 0.55;
        leg.root.rotation.z = leg.side * (0.55 + lift * 0.4);
        leg.femur.rotation.z = leg.side * (0.15 - lift * 0.5);
        leg.tibia.rotation.z = -leg.side * (0.7 + lift * 0.3);
        leg.root.rotation.x = -stride * 0.2;
      }
    }

    const t = state.gait * 0.35;
    this.antennae.forEach((a, i) => {
      const s = i === 0 ? -1 : 1;
      a.rotation.y = s * (0.2 + Math.sin(t + i) * 0.18);
      a.rotation.x = -0.15 + Math.sin(t * 1.3 + i * 2) * 0.12;
    });

    if (this.kind === "cyborg") {
      const pulse = 0.8 + state.firing * 2.4 + (state.dashT > 0 ? 3 : 0);
      this.ledMat.emissiveIntensity = pulse;
      if (this.implantLight) this.implantLight.intensity = 0.35 + state.firing * 1.1 + (state.dashT > 0 ? 1.6 : 0);
    }
  }

  dispose() {
    this.group.removeFromParent();
    for (const g of this.geometries) g.dispose();
    for (const m of this.materials) m.dispose();
  }
}
