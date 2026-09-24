import * as THREE from "three";

type Particle = {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  life: number;
  max: number;
  active: boolean;
};

export class Particles {
  points: THREE.Points;
  private pos: Float32Array;
  private col: Float32Array;
  private pool: Particle[] = [];
  private geo: THREE.BufferGeometry;
  private mat: THREE.PointsMaterial;
  private n = 160;

  constructor() {
    this.pos = new Float32Array(this.n * 3);
    this.col = new Float32Array(this.n * 3);
    this.geo = new THREE.BufferGeometry();
    this.geo.setAttribute("position", new THREE.BufferAttribute(this.pos, 3));
    this.geo.setAttribute("color", new THREE.BufferAttribute(this.col, 3));
    this.mat = new THREE.PointsMaterial({
      size: 0.08,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
      depthWrite: false,
      sizeAttenuation: true,
    });
    this.points = new THREE.Points(this.geo, this.mat);
    this.points.frustumCulled = false;
    for (let i = 0; i < this.n; i++) {
      this.pool.push({
        x: 0,
        y: -10,
        z: 0,
        vx: 0,
        vy: 0,
        vz: 0,
        life: 0,
        max: 1,
        active: false,
      });
      this.pos[i * 3 + 1] = -10;
    }
  }

  burst(x: number, y: number, z: number, n: number, color: THREE.Color, speed = 1.6) {
    let spawned = 0;
    for (const p of this.pool) {
      if (p.active) continue;
      p.active = true;
      p.x = x;
      p.y = y;
      p.z = z;
      const th = Math.random() * Math.PI * 2;
      const sp = (0.4 + Math.random()) * speed;
      p.vx = Math.cos(th) * sp;
      p.vy = 0.8 + Math.random() * 1.4;
      p.vz = Math.sin(th) * sp;
      p.life = p.max = 0.4 + Math.random() * 0.35;
      p.x += 0;
      spawned++;
      if (spawned >= n) break;
    }
    this.tint = color;
  }

  private tint = new THREE.Color(0xe8e0d0);

  update(dt: number) {
    const c = this.tint;
    for (let i = 0; i < this.n; i++) {
      const p = this.pool[i]!;
      if (!p.active) {
        this.pos[i * 3 + 1] = -20;
        continue;
      }
      p.life -= dt;
      if (p.life <= 0) {
        p.active = false;
        this.pos[i * 3 + 1] = -20;
        continue;
      }
      p.vy -= 4.2 * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.z += p.vz * dt;
      this.pos[i * 3] = p.x;
      this.pos[i * 3 + 1] = p.y;
      this.pos[i * 3 + 2] = p.z;
      const a = p.life / p.max;
      this.col[i * 3] = c.r * a;
      this.col[i * 3 + 1] = c.g * a;
      this.col[i * 3 + 2] = c.b * a;
    }
    const pa = this.geo.attributes.position;
    const ca = this.geo.attributes.color;
    if (pa) pa.needsUpdate = true;
    if (ca) ca.needsUpdate = true;
  }

  dispose() {
    this.geo.dispose();
    this.mat.dispose();
  }
}
