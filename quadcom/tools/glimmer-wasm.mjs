// Assembles GLIMMER's tiny Wasm SIMD kernel by hand (no toolchain dependency)
// and prints it as base64 for embedding in glimmer.js.
//   node tools/glimmer-wasm.mjs          -> base64
//   node tools/glimmer-wasm.mjs --test   -> self-test against a JS reference
//
// Exports:
//   memory                                   growable linear memory
//   dot(a, b, n) -> f32                      f32x4 dot product, n % 4 == 0
//   dotMany(a, base, strideBytes, count, n, out)
//                                            out[j] = dot(a, base + j*stride, n)
const u = (...b) => b;
const leb = n => { const o = []; do { let b = n & 0x7f; n >>>= 7; if (n) b |= 0x80; o.push(b); } while (n); return o; };
const str = s => [...leb(s.length), ...Buffer.from(s)];
const section = (id, body) => [id, ...leb(body.length), ...body];
const vec = items => [...leb(items.length), ...items.flat()];

const I32 = 0x7f, F32 = 0x7d, V128 = 0x7b;
const types = vec([
  u(0x60, 3, I32, I32, I32, 1, F32),
  u(0x60, 6, I32, I32, I32, I32, I32, I32, 0),
]);
const funcs = vec([[0], [1]]);
const memory = vec([[0x00, 0x01]]);
const exports = vec([
  [...str("memory"), 0x02, 0],
  [...str("dot"), 0x00, 0],
  [...str("dotMany"), 0x00, 1],
]);
const dotBody = [
  0x02, 0x01, V128, 0x01, I32,              // locals: acc v128 (3), end i32 (4)
  0x20, 0, 0x20, 2, 0x41, 2, 0x74, 0x6a, 0x21, 4,
  0x02, 0x40, 0x03, 0x40,
  0x20, 0, 0x20, 4, 0x4f, 0x0d, 1,
  0x20, 3,
  0x20, 0, 0xfd, 0x00, 0x04, 0x00,
  0x20, 1, 0xfd, 0x00, 0x04, 0x00,
  0xfd, 0xe6, 0x01,                         // f32x4.mul
  0xfd, 0xe4, 0x01,                         // f32x4.add
  0x21, 3,
  0x20, 0, 0x41, 16, 0x6a, 0x21, 0,
  0x20, 1, 0x41, 16, 0x6a, 0x21, 1,
  0x0c, 0, 0x0b, 0x0b,
  0x20, 3, 0xfd, 0x1f, 0,
  0x20, 3, 0xfd, 0x1f, 1, 0x92,
  0x20, 3, 0xfd, 0x1f, 2, 0x92,
  0x20, 3, 0xfd, 0x1f, 3, 0x92,
  0x0b,
];
const dotManyBody = [
  0x01, 0x01, I32,                          // local j (6)
  0x02, 0x40, 0x03, 0x40,
  0x20, 6, 0x20, 3, 0x4f, 0x0d, 1,
  0x20, 5, 0x20, 0, 0x20, 1, 0x20, 4, 0x10, 0, 0x38, 0x02, 0x00,
  0x20, 5, 0x41, 4, 0x6a, 0x21, 5,
  0x20, 1, 0x20, 2, 0x6a, 0x21, 1,
  0x20, 6, 0x41, 1, 0x6a, 0x21, 6,
  0x0c, 0, 0x0b, 0x0b, 0x0b,
];
const code = vec([[...leb(dotBody.length), ...dotBody], [...leb(dotManyBody.length), ...dotManyBody]]);
const bytes = Uint8Array.from([
  0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00,
  ...section(1, types), ...section(3, funcs), ...section(5, memory),
  ...section(7, exports), ...section(10, code),
]);

if (process.argv.includes("--test")) {
  if (!WebAssembly.validate(bytes)) throw Error("invalid module");
  const { instance } = await WebAssembly.instantiate(bytes);
  const { memory, dot, dotMany } = instance.exports;
  const n = 72, count = 50, f = new Float32Array(memory.buffer);
  for (let i = 0; i < n * (count + 1); i++) f[i] = Math.sin(i * 0.37);
  const ref = j => { let s = 0; for (let k = 0; k < n; k++) s += f[k] * f[(j + 1) * n + k]; return s; };
  if (Math.abs(dot(0, n * 4, n) - ref(0)) > 1e-3) throw Error("dot mismatch");
  const out = n * (count + 1);
  dotMany(0, n * 4, n * 4, count, n, out * 4);
  for (let j = 0; j < count; j++) if (Math.abs(f[out + j] - ref(j)) > 1e-3) throw Error("dotMany mismatch " + j);
  console.log(`ok · ${bytes.length} bytes`);
} else {
  console.log(Buffer.from(bytes).toString("base64"));
}
