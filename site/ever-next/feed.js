/* QuadCOM ❖ EVER NEXT page: modes, facets, mix-and-match chips, endless passes and local marks.
 * Marks (DONE / LATER / SKIP) are a per-browser convenience in localStorage; nothing is sent anywhere. */
(() => {
  'use strict';
  const list = document.querySelector('[data-en-list]'), ctl = document.querySelector('[data-en-controls]');
  if (!list || !ctl || !window.QCEverNext) return;
  const $ = s => ctl.querySelector(s), more = document.querySelector('[data-more]');
  const help = $('.qc-en-help'), count = $('.qc-en-count'), composeBox = $('.qc-en-compose');
  const F = name => $(`[data-f="${name}"]`);
  const KEY = 'quadcom-ever-next';
  let marks = {}; try { marks = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (_) { marks = {}; }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(marks)); } catch (_) {} };
  const esc = t => String(t).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const PAGE = 40;
  let feed, mode = 'feed', results = [], pos = 0, endless = true;
  const auto = {};   // facets SWEEP / POLISH filled in themselves; cleared again when leaving those modes
  const announce = t => { const el = ctl.querySelector('[data-en-announce]'); if (el) { el.textContent = ''; setTimeout(() => { el.textContent = t; }, 30); } };
  const plural = (n, w) => `${n.toLocaleString('en-US')} ${w}${n === 1 ? '' : 'S'}`;

  const HELP = {
    feed: 'Every item in order: measured first, then cycle by cycle and depth by depth. When a pass ends, the next pass begins.',
    today: 'Five items for today, the same for everyone on the same UTC day: up to two measured, three from the whole feed, all different aspects.',
    sweep: 'One aspect across every surface it applies to. Pick an aspect; depth starts at OBSERVE.',
    polish: 'One surface through every aspect that applies to it. Pick a surface; depth starts at OBSERVE.',
    compose: 'A seeded bundle from the current facets: distinct aspects and surfaces. The same seed always composes the same bundle.',
  };
  const facets = () => ({ layer: F('layer').value, surface: F('surface').value, aspect: F('aspect').value, depth: F('depth').value,
    cycle: F('cycle').value, status: F('status').value, q: F('q').value });

  function row(it) {
    const mk = marks[it.id] ? marks[it.id][0] : '';
    const btn = (v, label) => `<button type="button" data-mark="${v}" aria-pressed="${mk === v}">${label}</button>`;
    const ev = it.evidence ? it.evidence.map(e => `<p class="qc-en-ev"><b>MEASURED:</b> ${esc(e.text)} <small>(${esc(e.src)})</small></p>`).join('') : '';
    return `<li class="qc-en-item${mk ? ' is-' + mk : ''}" data-id="${esc(it.id)}"><div class="qc-en-meta"><span class="qc-en-id">P${it.pass} · ${esc(it.id)}</span>`
      + `<span class="qc-en-depth">${it.depthName}</span><span class="qc-en-cycle">CYCLE ${it.cycle + 1} · BAR: ${esc(it.bar)}</span>`
      + (it.evidence ? `<span class="qc-en-sev s${Math.max(...it.evidence.map(e => e.sev))}">MEASURED</span>` : '') + `</div>`
      + `<p class="qc-en-text">${esc(it.text)}</p>${ev}`
      + `<div class="qc-en-foot"><span class="qc-en-chips"><button type="button" data-set="surface" data-v="${it.surface.id}">${esc(it.surface.name)}</button>`
      + `<button type="button" data-set="aspect" data-v="${it.aspect.id}">${esc(it.aspect.name)}</button></span>`
      + `<span class="qc-en-actions" role="group" aria-label="Mark ${esc(it.id)}">${btn('done', 'DONE')}${btn('later', 'LATER')}${btn('skip', 'SKIP')}<button type="button" data-copy>COPY</button></span></div></li>`;
  }
  function renderMore() {
    if (!results.length) { more.hidden = true; return; }
    const html = [];
    // Stop at the end of each pass: the next pass is a deliberate step, never a silent repeat.
    const boundary = (Math.floor(pos / results.length) + 1) * results.length;
    const stop = Math.min(pos + PAGE, boundary);
    for (; pos < stop; pos++) html.push(row(feed.item(results[pos % results.length], Math.floor(pos / results.length) + 1)));
    list.insertAdjacentHTML('beforeend', html.join(''));
    const atBoundary = pos % results.length === 0;
    more.hidden = !endless && pos >= results.length;
    more.textContent = endless && atBoundary ? `PASS ${pos / results.length} COMPLETE · BEGIN PASS ${pos / results.length + 1}` : 'SHOW MORE';
  }
  function run() {
    const f = facets();
    help.textContent = HELP[mode];
    composeBox.hidden = mode !== 'compose';
    const fill = (name, value) => { F(name).value = value; f[name] = value; auto[name] = value; };
    if (mode === 'sweep' && !f.aspect) fill('aspect', feed.item(feed.today()[0]).aspect.id);
    if (mode === 'polish' && !f.surface) fill('surface', feed.item(feed.today()[0]).surface.id);
    if ((mode === 'sweep' || mode === 'polish') && f.depth === '') fill('depth', '0');
    if (mode === 'today') { results = feed.today(); endless = false; }
    else if (mode === 'compose') {
      if (!F('seed').value) F('seed').value = String(Date.now() % 1e6);
      results = feed.compose(feed.select(f, marks), +F('size').value, +F('seed').value || 1); endless = false;
    } else {
      results = feed.select(f, marks, mode === 'sweep' ? 'surface' : mode === 'polish' ? 'aspect' : null);
      endless = mode === 'feed';
    }
    const n = results.length;
    count.textContent = mode === 'today' || mode === 'compose' ? plural(n, 'ITEM') :
      n ? `${plural(n, 'MATCHING ITEM')} PER PASS${endless ? ' · PASSES CONTINUE ENDLESSLY' : ''}` : 'NO ITEMS MATCH · CLEAR A FACET';
    list.innerHTML = ''; pos = 0; renderMore();
  }
  const setMode = m => {
    if (m !== mode) for (const [k, v] of Object.entries(auto)) { if (F(k).value === v) F(k).value = ''; delete auto[k]; }
    mode = m; for (const b of ctl.querySelectorAll('[data-mode]')) { const on = b.dataset.mode === m; b.setAttribute('aria-checked', on); b.tabIndex = on ? 0 : -1; } run(); };

  ctl.querySelectorAll('[data-mode]').forEach((b, i, all) => {
    b.addEventListener('click', () => setMode(b.dataset.mode));
    b.addEventListener('keydown', e => { const d = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key]; if (!d) return; e.preventDefault(); const n = all[(i + d + all.length) % all.length]; setMode(n.dataset.mode); n.focus(); });
  });
  for (const el of ctl.querySelectorAll('select[data-f]')) el.addEventListener('change', run);
  let t = 0; F('q').addEventListener('input', () => { clearTimeout(t); t = setTimeout(run, 180); });
  F('seed').addEventListener('change', run);
  $('[data-shuffle]').addEventListener('click', () => { F('seed').value = String(Math.floor(Math.random() * 1e6)); run(); });
  $('[data-reset]').addEventListener('click', () => { for (const el of ctl.querySelectorAll('[data-f]')) if (el.dataset.f !== 'size') el.value = ''; setMode('feed'); });
  $('[data-export]').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify({ exported: new Date().toISOString(), marks }, null, 2)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'quadcom-ever-next-marks.json'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
  more.addEventListener('click', renderMore);
  // Auto-load within a pass (up to 400 items); crossing into a new pass always takes a tap.
  if ('IntersectionObserver' in window) new IntersectionObserver(es => { if (es.some(e => e.isIntersecting) && !more.hidden && pos > 0 && pos < 400 && pos % results.length) renderMore(); }, { rootMargin: '600px' }).observe(more);

  list.addEventListener('click', e => {
    const li = e.target.closest('.qc-en-item'); if (!li) return;
    const set = e.target.closest('[data-set]');
    if (set) {
      const el = F(set.dataset.set); el.value = set.dataset.v; delete auto[set.dataset.set];
      setMode(mode === 'today' || mode === 'compose' ? 'feed' : mode);
      ctl.scrollIntoView({ block: 'start' }); el.focus({ preventScroll: true });   // keyboard focus lands on the facet it set
      announce(`Filtered by ${set.textContent}`); return;
    }
    const mk = e.target.closest('[data-mark]');
    if (mk) {
      const id = li.dataset.id, v = mk.dataset.mark, cur = marks[id] ? marks[id][0] : '';
      if (cur === v) delete marks[id]; else marks[id] = [v, Date.now()];
      save();
      li.className = 'qc-en-item' + (marks[id] ? ' is-' + marks[id][0] : '');
      for (const b of li.querySelectorAll('[data-mark]')) b.setAttribute('aria-pressed', String(marks[id] ? marks[id][0] === b.dataset.mark : false));
      return;
    }
    if (e.target.closest('[data-copy]')) {
      const text = li.querySelector('.qc-en-id').textContent + ' — ' + li.querySelector('.qc-en-text').textContent;
      (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject()).then(() => { e.target.textContent = 'COPIED'; announce(`Copied ${li.dataset.id}`); setTimeout(() => { e.target.textContent = 'COPY'; }, 1400); })
        .catch(() => announce('Copy is not available in this browser'));
    }
  });

  fetch('/ever-next/axes.json?v=58').then(r => r.ok ? r.json() : Promise.reject()).then(ax => {
    feed = QCEverNext.create(ax);
    ctl.hidden = false;
    const want = new URLSearchParams(location.search);
    for (const k of ['surface', 'aspect', 'layer', 'depth', 'cycle', 'status', 'q']) if (want.has(k) && F(k)) F(k).value = want.get(k);
    setMode(['today', 'sweep', 'polish', 'compose'].includes(want.get('mode')) ? want.get('mode') : 'feed');
  }).catch(() => { count.textContent = ''; });
})();
