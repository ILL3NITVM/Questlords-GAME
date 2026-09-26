/* QuadCOM ❖ EVER NEXT composer. Turns ever-next/axes.json into an endless, ordered item feed.
 * Items are never stored: each is five small numbers (pairing, move, depth, cycle, pass) and its text is
 * composed on demand, so 100,000+ items per pass cost a few typed arrays. Shared by the page (feed.js)
 * and tools/qa/ever-next.mjs, which checks the count against tools/build-ever-next.py.
 * Order, per pass: measured items first (high before note), then cycle by cycle and depth by depth, mixed by a stable hash
 * so neighbouring items differ in surface and aspect. After the last item the next pass begins. */
(function (root) {
  'use strict';
  const fnv = s => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h; };
  const rng = seed => () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

  function create(ax) {
    const S = ax.surfaces, A = ax.aspects, D = ax.depths;
    const pairS = [], pairA = [];
    S.forEach((s, si) => A.forEach((a, ai) => { if (s.tags.some(t => a.needs.includes(t))) { pairS.push(si); pairA.push(ai); } }));
    const evidence = new Map();
    for (const e of ax.evidence) { const k = e.s + '|' + e.a; if (!evidence.has(k)) evidence.set(k, []); evidence.get(k).push(e); }
    let n = 0;
    for (let p = 0; p < pairS.length; p++) n += 6 * D.length * A[pairA[p]].bars.length;
    const P = new Uint16Array(n), M = new Uint8Array(n), DP = new Uint8Array(n), C = new Uint8Array(n), key = new Float64Array(n);
    let k = 0;
    for (let p = 0; p < pairS.length; p++) {
      const s = S[pairS[p]], a = A[pairA[p]], ev = evidence.get(s.id + '|' + a.id);
      const measured = ev ? 2 - Math.max(...ev.map(e => e.sev)) : 2;  // 0 high, 1 note, 2 unmeasured
      for (let c = 0; c < a.bars.length; c++) for (let d = 0; d < D.length; d++) for (let m = 0; m < 6; m++) {
        P[k] = p; M[k] = m; DP[k] = d; C[k] = c;
        key[k] = measured * 1e12 + c * 1e11 + d * 1e10 + fnv(s.id + a.id + m + d + c);
        k++;
      }
    }
    const order = new Uint32Array(n).map((_, i) => i).sort((x, y) => key[x] - key[y]);

    function item(i, pass) {
      const s = S[pairS[P[i]]], a = A[pairA[P[i]]], d = D[DP[i]], c = C[i], m = M[i];
      return {
        idx: i, pass: pass || 1, surface: s, aspect: a, move: m, depth: DP[i], cycle: c,
        id: `${s.id}.${a.id}.m${m + 1}.d${DP[i] + 1}.c${c + 1}`,
        text: a.moves[m].replace('{s}', s.name) + ' ' + d.text,
        depthName: d.name, bar: a.bars[c], evidence: evidence.get(s.id + '|' + a.id) || null,
      };
    }
    /* Facet test on the numbers alone; text is only composed when a search needs it. */
    function matcher(f, marks) {
      const q = (f.q || '').trim().toLowerCase();
      return i => {
        const s = S[pairS[P[i]]], a = A[pairA[P[i]]];
        if (f.layer !== '' && f.layer != null && s.layer !== +f.layer) return false;
        if (f.surface && s.id !== f.surface) return false;
        if (f.aspect && a.id !== f.aspect) return false;
        if (f.depth !== '' && f.depth != null && DP[i] !== +f.depth) return false;
        if (f.cycle !== '' && f.cycle != null && C[i] !== +f.cycle) return false;
        if (f.status === 'measured' && !evidence.has(s.id + '|' + a.id)) return false;
        if (f.status && f.status !== 'measured') {
          const it = item(i), st = marks && marks[it.id] ? marks[it.id][0] : '';
          if (f.status === 'open' ? st !== '' : st !== f.status) return false;
        }
        if (q) { const it = item(i); if (!(it.id + ' ' + it.text + ' ' + a.name + ' ' + it.bar).toLowerCase().includes(q)) return false; }
        return true;
      };
    }
    /* All matches in feed order (one pass); `sortBy` re-orders for SWEEP (by surface) or POLISH (by aspect). */
    function select(f, marks, sortBy) {
      const ok = matcher(f, marks), out = [];
      for (let j = 0; j < n; j++) if (ok(order[j])) out.push(order[j]);
      if (sortBy === 'surface') out.sort((x, y) => pairS[P[x]] - pairS[P[y]] || M[x] - M[y]);
      if (sortBy === 'aspect') out.sort((x, y) => pairA[P[x]] - pairA[P[y]] || M[x] - M[y]);
      return out;
    }
    /* A seeded bundle of `size` items: distinct aspects and surfaces where the pool allows, then distinct
       surfaces, then anything, so a narrow facet (one aspect, say) still fills the bundle. */
    function compose(pool, size, seed) {
      const r = rng(seed >>> 0), picked = [], aspects = new Set(), surfaces = new Set(), taken = new Set();
      const shuffled = Array.from(pool);
      for (let i = shuffled.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]; }
      for (const stage of [2, 1, 0]) for (const i of shuffled) {
        if (picked.length >= size) break;
        const a = pairA[P[i]], s = pairS[P[i]];
        if (taken.has(i) || (stage === 2 && aspects.has(a)) || (stage >= 1 && surfaces.has(s))) continue;
        picked.push(i); taken.add(i); aspects.add(a); surfaces.add(s);
      }
      return picked;
    }
    /* Five for today: up to two measured items, then three from the whole feed, all distinct aspects. */
    function today(date) {
      const d = date || new Date(), seed = d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
      const measured = select({ status: 'measured' }, null), all = order;
      const two = compose(measured, 2, seed), used = new Set(two.map(i => pairA[P[i]]));
      const rest = compose(Array.from(all).filter(i => !used.has(pairA[P[i]])), 3, seed ^ 0x9e3779b9);
      return two.concat(rest);
    }
    return { total: n, pairs: pairS.length, order, item, select, compose, today, evidenceCount: ax.evidence.length };
  }
  root.QCEverNext = { create, fnv };
})(typeof window !== 'undefined' ? window : globalThis);
