/* Bon·Appétit site. No frameworks, no build step. */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const icon = (id, cls = 'i') => `<svg class="${cls}" aria-hidden="true"><use href="#i-${id}"/></svg>`;
  const isNum = (v) => typeof v === 'number' && isFinite(v);

  /* ---------- Foundation behaviour: reveal + range fill ---------- */
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { rootMargin: '0px 0px -8% 0px' });
    $$('.reveal').forEach((el) => io.observe(el));
  } else $$('.reveal').forEach((el) => el.classList.add('in'));
  const fillRange = (r) => r.style.setProperty('--val', ((r.value - r.min) / (r.max - r.min)) * 100 + '%');
  $$('.range').forEach((r) => { r.addEventListener('input', () => fillRange(r)); fillRange(r); });

  /* Segmented control helper */
  function bindSegmented(group, onPick) {
    group.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b || b.disabled || !group.contains(b)) return;
      $$('button', group).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      onPick(b);
    });
  }
  function pressIn(group, pred) { $$('button', group).forEach((x) => x.setAttribute('aria-pressed', String(pred(x)))); }

  /* ---------- Hero: line-by-line decode ---------- */
  (function hero() {
    const app = $('#heroApp'), vis = $('#heroVisual');
    if (!app) return;
    const rows = $$('.dec-row', app), lines = $$('.rc[data-i]', app);
    const st = $('#heroStatus'), stt = $('#heroStatusText');
    const n = rows.length;
    const finish = () => {
      rows.forEach((r) => r.classList.add('is-in'));
      lines.forEach((l) => { l.classList.remove('is-reading'); l.classList.add('is-done'); });
      st.classList.remove('is-busy');
      stt.textContent = n + ' lines read · 1 question';
      app.classList.add('is-done'); vis.classList.add('is-done');
    };
    if (reduce) { finish(); return; }
    let i = 0;
    const step = () => {
      if (i >= n) { setTimeout(finish, 120); return; }
      const l = lines[i];
      l.classList.add('is-reading');
      stt.textContent = `reading ${i + 1} of ${n}`;
      setTimeout(() => {
        l.classList.remove('is-reading'); l.classList.add('is-done');
        rows[i].classList.add('is-in');
        i++;
        setTimeout(step, 130);
      }, 430);
    };
    setTimeout(step, 650);
  })();

  /* ---------- Privacy feature: language picker ---------- */
  (function settingsLang() {
    const g = $('#settingsLang'), q = $('#settingsQ');
    if (!g || !q) return;
    const Q = {
      de: ['Rückfrage', 'Geriebener Gruyère oder geriebener Parmesan?'],
      fr: ['Question', 'Gruyère râpé ou parmesan râpé ?'],
      it: ['Domanda', 'Gruyère grattugiato o parmigiano grattugiato?'],
      en: ['Review question', 'Grated Gruyère, or grated Parmesan?'],
    };
    bindSegmented(g, (b) => {
      const l = b.dataset.l;
      q.textContent = Q[l][1];
      q.setAttribute('lang', l);
      q.previousElementSibling.textContent = Q[l][0];
      q.previousElementSibling.setAttribute('lang', l);
    });
  })();

  /* ---------- Copy buttons ---------- */
  $$('.copy').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const pre = document.getElementById('code-' + btn.dataset.copy);
      if (!pre) return;
      const text = pre.innerText.split('\n').map((l) => l.replace(/^\$\s?/, '')).join('\n').trim();
      const label = $('span', btn);
      try { await navigator.clipboard.writeText(text); label.textContent = 'Copied'; }
      catch (_) {
        const r = document.createRange(); r.selectNodeContents(pre);
        const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
        label.textContent = 'Selected';
      }
      setTimeout(() => { label.textContent = 'Copy'; }, 1600);
    });
  });

  /* ---------- Data loading ---------- */
  const getJSON = (url) => fetch(url, { cache: 'no-cache' }).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });

  /* ==========================================================
     Try it on this page
     ========================================================== */
  const GROUPS = [
    ['vegetables_fruit', 'Veg and fruit', 'Vegetables and fruit'],
    ['grains_potatoes', 'Grains, potatoes', 'Grains, potatoes and pulses'],
    ['dairy', 'Dairy', 'Milk and dairy products'],
    ['protein', 'Meat, fish, eggs', 'Meat, fish, eggs and tofu'],
    ['fats_nuts', 'Oils and nuts', 'Oils, fats and nuts'],
    ['sweets_snacks_drinks', 'Sweets, drinks', 'Sweets, salty snacks and sweet drinks'],
  ];
  const SHORT = Object.fromEntries(GROUPS.map((g) => [g[0], g[1]]));
  const CHIP = { vegetables_fruit: 'Veg and fruit', grains_potatoes: 'Grains', dairy: 'Dairy', protein: 'Protein', fats_nuts: 'Fats and nuts', sweets_snacks_drinks: 'Sweets and drinks' };
  const LANGNAME = { de: 'Deutsch', fr: 'Français', it: 'Italiano', en: 'English' };
  const SRC = { fsvo: 'FSVO', off: 'Open Food Facts' };
  const SALT_GUIDE = 5, FV_GUIDE = 5;

  const ctlReceipt = $('#ctlReceipt'), ctlSize = $('#ctlSize'), sizeOut = $('#sizeOut'), ctlLang = $('#ctlLang'), ctlReview = $('#ctlReview');
  const preview = $('#preview'), hint = $('#receiptHint'), note = $('#tryNote'), pill = $('#pvPill');
  const state = { data: null, idx: 0, size: 4, lang: 'de', langChosen: false, showReview: true, resolved: {}, shown: {} };

  const fmtGrams = (g) => !isNum(g) ? '' : g >= 1000 ? (Math.round(g / 10) / 100).toString().replace(/\.?0+$/, '') + ' kg' : Math.round(g) + ' g';
  const fmtConf = (c) => isNum(c) ? c.toFixed(2) : '';

  function quiet(title, sub) {
    return `<div class="quiet">${icon('clock')}<b>${esc(title)}</b><span>${esc(sub)}</span></div>`;
  }

  function lineRow(r, line, i) {
    const raw = `<div class="dec-row__raw">${esc(line.raw)}${line.qty > 1 ? ' · ' + esc(line.qty) + 'x' : ''}</div>`;
    const k = `style="--k:${i}"`;
    if (line.status === 'review') {
      const key = r.id + ':' + i, done = state.resolved[key];
      const cands = (line.candidates || []).map((c) => `<button class="opt" type="button" data-key="${esc(key)}" data-pick="${esc(c.name)}">${esc(c.name)}</button>`).join('');
      const tail = done
        ? `<div class="resolved">${icon('check')}Linked to ${esc(done)}. Remembered for next week.</div>`
        : (cands ? `<div class="opt-row">${cands}</div>` : '');
      return `<div class="dec-row dec-row--review" ${k}><div>${raw}<div class="dec-row__name">${esc(line.question || line.decoded || 'Needs a look')}</div><div class="dec-row__meta"><span class="gchip gchip--review">${done ? 'Answered' : 'Asked you'}</span>${line.decoded ? `<span>${esc(line.decoded)}</span>` : ''}</div>${tail}</div><span class="ask-ic">${icon('ask')}</span></div>`;
    }
    if (line.status === 'nonfood') {
      const why = line.reason && line.reason !== line.decoded ? `<span>${esc(line.reason)}</span>` : '';
      return `<div class="dec-row dec-row--nonfood" ${k}><div>${raw}<div class="dec-row__name">${esc(line.decoded || line.reason || 'Not food')}</div><div class="dec-row__meta"><span class="gchip gchip--none">Not food</span>${why}</div></div></div>`;
    }
    const m = line.match || {};
    const grp = m.group && CHIP[m.group] ? `<span class="gchip g-${esc(m.group)}">${esc(CHIP[m.group])}</span>` : '';
    const src = m.name ? `<span>${esc(SRC[m.source] || m.source || '')}${m.source ? ': ' : ''}${esc(m.name)}</span>` : '';
    return `<div class="dec-row" ${k}><div>${raw}<div class="dec-row__name">${esc(line.decoded || m.name || line.raw)}</div><div class="dec-row__meta">${grp}${isNum(line.grams) ? `<span class="t-mono">${fmtGrams(line.grams)}</span>` : ''}${src}</div></div><div class="conf">${fmtConf(line.confidence)}<i style="--c:${isNum(line.confidence) ? line.confidence : 0}"></i></div></div>`;
  }

  function renderLines(still) {
    const r = state.data.receipts[state.idx];
    const lines = r.lines || [];
    const count = (s) => lines.filter((l) => l.status === s).length;
    const nLinked = count('linked'), nReview = count('review'), nNon = count('nonfood');
    const rows = lines.map((l, i) => (l.status === 'review' && !state.showReview) ? '' : lineRow(r, l, i)).join('');
    const hidden = !state.showReview && nReview ? `<p class="wk__fine" style="margin-top:10px">${nReview} ${nReview === 1 ? 'question is' : 'questions are'} hidden. Switch on “Show what Apertus abstained on” to see ${nReview === 1 ? 'it' : 'them'}.</p>` : '';
    const box = $('.wk__lines', preview);
    box.classList.toggle('is-still', !!still);
    box.innerHTML =
      `<div class="wk__head"><span class="app__label">Receipt lines</span><span class="status"><span class="status__dot"></span>${nLinked} linked · ${nReview} asked · ${nNon} set aside</span></div><div class="dec dec--raw">${rows}</div>${hidden}`;
  }

  function metric(id, label, extra = '') {
    return `<div class="metric ${extra}"><span class="metric__v" id="${id}">0</span><span class="metric__k">${label}</span>${extra.includes('has-ref') ? `<span class="metric__ref" id="${id}Ref"></span>` : ''}</div>`;
  }

  function renderSummaryShell() {
    const r = state.data.receipts[state.idx];
    const s = (state.data.summary || {})[r.id];
    const sum = $('.wk__sum', preview);
    const head = `<div class="app__head"><div><div class="app__title">${esc(r.label || r.id)}</div><div class="app__sub">${esc(r.shop || '')}${r.shop ? ' · ' : ''}${esc(r.days || 7)} days · ${(r.lines || []).length} lines</div></div></div>`;
    if (!s) { sum.innerHTML = head + quiet('Results are being computed.', 'This week’s summary appears here when it is ready.'); return; }
    const vals = GROUPS.map((g) => (s.pyramid || {})[g[0]]).filter(isNum);
    const recs = GROUPS.map((g) => (s.recommended || {})[g[0]]).filter(isNum);
    const max = Math.min(1, Math.max(0.01, ...vals, ...recs) * 1.12);
    const bars = GROUPS.map(([k, short, long]) => {
      const v = (s.pyramid || {})[k], rec = (s.recommended || {})[k];
      return `<div class="bar" title="${esc(long)}"><span>${esc(short)}</span><span class="bar__track"><span class="bar__fill g-${k}" data-w="${isNum(v) ? (v / max) * 100 : 0}"></span>${isNum(rec) ? `<span class="bar__rec" style="--r:${(rec / max) * 100}%" title="Guide: ${Math.round(rec * 100)}%"></span>` : ''}</span><span class="bar__v">${isNum(v) ? Math.round(v * 100) + '%' : 'n/a'}</span></div>`;
    }).join('');
    sum.innerHTML = `${head}
      <div><div class="wk__block-title">Food pyramid shares<span>this week against the guide</span></div><div class="bars">${bars}</div>
        <div class="legend"><span><i></i>This week</span><span><i class="rec"></i>Swiss food pyramid guide</span></div></div>
      <div><div class="wk__block-title">Per person and day<span id="pvPeople"></span></div>
        <div class="metrics">
          ${metric('mSugar', 'sugar')}
          ${metric('mSalt', 'salt, guide at most 5 g', 'has-ref')}
          ${metric('mSat', 'saturated fat')}
          ${metric('mFv', 'portions of fruit and veg, guide 5', 'has-ref')}
          ${metric('mUpf', 'of the food bought is ultra-processed (NOVA 4)', 'metric--wide')}
        </div></div>
      <div><div class="wk__block-title">Swaps from the same shop<span id="pvLang"></span></div><div class="nudges" id="pvNudges"></div></div>
      <p class="wk__fine" id="pvFine"></p>`;
    const fills = $$('.bar__fill', sum);
    const apply = () => fills.forEach((f) => f.style.setProperty('--w', f.dataset.w + '%'));
    if (reduce) apply(); else requestAnimationFrame(() => requestAnimationFrame(apply));
    state.shown = {};
    updateNumbers(true);
    renderNudges();
  }

  function tween(el, to, dec, unit, key) {
    if (!el) return;
    const from = isNum(state.shown[key]) ? state.shown[key] : to;
    state.shown[key] = to;
    const fmt = (v) => v.toFixed(dec) + (unit ? `<small>${unit}</small>` : '');
    if (reduce || from === to) { el.innerHTML = fmt(to); return; }
    const t0 = performance.now(), d = 380;
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / d), e = 1 - Math.pow(1 - p, 3);
      el.innerHTML = fmt(from + (to - from) * e);
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  function updateNumbers() {
    const r = state.data.receipts[state.idx];
    const s = (state.data.summary || {})[r.id];
    sizeOut.textContent = state.size;
    if (!s) return;
    const base = isNum(r.household_size) && r.household_size > 0 ? r.household_size : state.size;
    const f = base / state.size;
    const set = (id, v, dec, unit) => isNum(v) ? tween($('#' + id), v, dec, unit, id) : ($('#' + id).textContent = 'n/a');
    set('mSugar', isNum(s.sugar_g_per_day) ? s.sugar_g_per_day * f : null, 0, 'g');
    set('mSalt', isNum(s.salt_g_per_day) ? s.salt_g_per_day * f : null, 1, 'g');
    set('mSat', isNum(s.satfat_g_per_day) ? s.satfat_g_per_day * f : null, 0, 'g');
    set('mFv', isNum(s.fruit_veg_portions_per_day) ? s.fruit_veg_portions_per_day * f : null, 1, '');
    set('mUpf', isNum(s.upf_share) ? s.upf_share * 100 : null, 0, '%');
    const ref = (id, v, guide, overIsBad) => {
      const el = $('#' + id + 'Ref'); if (!el || !isNum(v)) return;
      el.style.setProperty('--p', Math.min(100, (v / guide) * 100) + '%');
      el.classList.toggle('is-over', overIsBad && v > guide);
    };
    ref('mSalt', s.salt_g_per_day * f, SALT_GUIDE, true);
    ref('mFv', s.fruit_veg_portions_per_day * f, FV_GUIDE, false);
    const ppl = $('#pvPeople'); if (ppl) ppl.textContent = `${state.size} ${state.size === 1 ? 'person' : 'people'}`;
    const fine = $('#pvFine');
    if (fine) fine.textContent = `Amounts are per person and day, from ${r.days || 7} days of shopping shared by ${state.size} ${state.size === 1 ? 'person' : 'people'}. Pyramid shares do not depend on household size. Guides follow the Swiss dietary recommendations.`;
  }

  function renderNudges() {
    const r = state.data.receipts[state.idx];
    const s = (state.data.summary || {})[r.id];
    const box = $('#pvNudges'); if (!box || !s) return;
    let list = (s.nudges || []).filter((n) => n.lang === state.lang);
    let lang = state.lang;
    if (!list.length) { list = (s.nudges || []).filter((n) => n.lang === 'en'); lang = 'en'; }
    $('#pvLang').textContent = LANGNAME[lang] || lang;
    box.innerHTML = list.length
      ? list.map((n) => `<div class="nudge" lang="${esc(n.lang)}">${icon('swap')}<span>${esc(n.text)}</span></div>`).join('')
      : `<p class="wk__fine">No suggestions for this week.</p>`;
  }

  function renderAll() {
    const d = state.data;
    if (!d || !Array.isArray(d.receipts) || !d.receipts.length) {
      preview.innerHTML = quiet('Results are being computed.', 'The sample week appears here once it is ready.');
      return;
    }
    preview.innerHTML = `<div class="wk"><div class="wk__lines"></div><div class="wk__sum"></div></div>`;
    renderLines();
    renderSummaryShell();
    const r = d.receipts[state.idx];
    hint.textContent = `${r.label || r.id} · ${(r.lines || []).length} lines`;
  }

  function selectReceipt(i) {
    state.idx = i;
    const r = state.data.receipts[i];
    if (isNum(r.household_size)) { state.size = Math.max(1, Math.min(6, Math.round(r.household_size))); ctlSize.value = state.size; fillRange(ctlSize); }
    if (!state.langChosen && r.lang && LANGNAME[r.lang]) { state.lang = r.lang; pressIn(ctlLang, (b) => b.dataset.l === state.lang); }
    renderAll();
  }

  function initTry(d) {
    state.data = d;
    if (!d || !Array.isArray(d.receipts) || !d.receipts.length) { renderAll(); hint.textContent = 'Sample receipts are not available yet.'; return; }
    ctlReceipt.innerHTML = d.receipts.map((r, i) => {
      const short = `${r.shop || 'Receipt'} · ${(r.lang || '').toUpperCase()}`;
      return `<button type="button" aria-pressed="${i === 0}" data-i="${i}" title="${esc(r.label || '')}" aria-label="${esc(r.label || short)}">${esc(short)}</button>`;
    }).join('');
    bindSegmented(ctlReceipt, (b) => selectReceipt(+b.dataset.i));
    bindSegmented(ctlLang, (b) => { state.lang = b.dataset.l; state.langChosen = true; renderNudges(); });
    ctlSize.addEventListener('input', () => { state.size = +ctlSize.value; updateNumbers(); });
    ctlReview.addEventListener('change', () => { state.showReview = ctlReview.checked; renderLines(true); });
    preview.addEventListener('click', (e) => {
      const b = e.target.closest('.opt'); if (!b) return;
      state.resolved[b.dataset.key] = b.dataset.pick;
      renderLines(true);
    });
    if (d.note) {
      pill.textContent = 'Sample data';
      note.textContent = 'These are sample receipts with illustrative numbers. Real pipeline output replaces them.';
    } else { pill.textContent = 'Pipeline output'; note.textContent = ''; }
    selectReceipt(0);
  }

  getJSON('data/demo.json').then(initTry).catch(() => {
    initTry(null);
  });

  /* ==========================================================
     Evidence
     ========================================================== */
  const METHOD_INFO = {
    fuzzy: ['Fuzzy match', 'string similarity'],
    embed: ['Embeddings only', 'nearest food'],
    embeddings: ['Embeddings only', 'nearest food'],
    apertus: ['Apertus alone', 'guesses nutrients'],
    apertus_only: ['Apertus alone', 'guesses nutrients'],
    llm: ['Apertus alone', 'guesses nutrients'],
    hybrid: ['Full hybrid', 'search, Apertus, food layer'],
    oracle: ['Oracle', 'best possible FSVO match'],
  };
  const DEFAULT_METHODS = ['fuzzy', 'embed', 'apertus', 'hybrid', 'oracle'].map((id) => ({ id, label: METHOD_INFO[id][0] }));
  const pct = (v) => isNum(v) ? Math.round(v <= 1 ? v * 100 : v) + '%' : 'n/a';
  const fx = (v, d) => isNum(v) ? v.toFixed(d) : 'n/a';
  const computing = '<span class="computing">computing</span>';
  let results = null;

  function renderTable(res) {
    const done = res && res.status === 'done' && Array.isArray(res.methods) && res.methods.length;
    const methods = done ? res.methods : DEFAULT_METHODS;
    const scored = methods.filter((m) => m.id !== 'oracle' && isNum(m.kcal_mae));
    const best = scored.length ? scored.reduce((a, b) => (b.kcal_mae < a.kcal_mae ? b : a)).id : null;
    const body = methods.map((m) => {
      const info = METHOD_INFO[m.id] || [];
      const name = `${esc(m.label || info[0] || m.id)}${info[1] ? `<small>${esc(info[1])}</small>` : ''}`;
      const cells = done
        ? [fx(m.kcal_mae, 1), fx(m.sugar_mae, 1) + (isNum(m.sugar_mae) ? ' g' : ''), fx(m.salt_mae, 2) + (isNum(m.salt_mae) ? ' g' : ''), pct(m.within20_kcal), pct(m.group_acc), pct(m.abstain), isNum(m.n) ? m.n.toLocaleString('en-US') : 'n/a']
        : Array(7).fill(computing);
      const cls = [m.id === best ? 'is-best' : '', m.id === 'oracle' ? 'is-oracle' : ''].join(' ').trim();
      return `<tr${cls ? ` class="${cls}"` : ''}><td>${name}</td>${cells.map((c) => `<td>${c}</td>`).join('')}</tr>`;
    }).join('');
    $('#resultsTable tbody').innerHTML = body;
    $('#nProducts').textContent = done && isNum(res.n_products) ? `${res.n_products.toLocaleString('en-US')} products` : 'Results are being computed';
  }

  function niceStep(max) {
    const raw = max / 4, p = Math.pow(10, Math.floor(Math.log10(raw))), n = raw / p;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
  }

  function renderChart(res) {
    const host = $('#chart'); if (!host) return;
    const done = res && res.status === 'done' && Array.isArray(res.methods) && res.methods.some((m) => isNum(m.kcal_mae));
    const methods = done ? res.methods.filter((m) => isNum(m.kcal_mae)) : DEFAULT_METHODS;
    const W = Math.max(280, Math.round(host.clientWidth || 480));
    const labelW = W < 400 ? 118 : 132, valW = 64, rowH = 40, top = 6, barH = 16;
    const plotW = W - labelW - valW;
    const H = top + methods.length * rowH + 26;
    const vals = methods.map((m) => m.kcal_mae).filter(isNum);
    const step = done ? niceStep(Math.max(...vals)) : 25;
    const max = done ? Math.ceil((Math.max(...vals) * 1.02) / step) * step : 100;
    const x = (v) => labelW + (v / max) * plotW;
    const scored = methods.filter((m) => m.id !== 'oracle' && isNum(m.kcal_mae));
    const best = scored.length ? scored.reduce((a, b) => (b.kcal_mae < a.kcal_mae ? b : a)).id : null;
    let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${done ? 'Bar chart of mean energy error by method' : 'Chart placeholder, results are being computed'}">
      <defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" style="fill:var(--surface)"/><line x1="0" y1="0" x2="0" y2="6" style="stroke:var(--ink-4);stroke-width:2"/></pattern></defs>`;
    for (let t = 0; done && t <= max + 1e-9; t += step) {
      const gx = x(t);
      svg += `<line class="grid" x1="${gx}" x2="${gx}" y1="${top}" y2="${H - 20}"/>`;
      if (done) svg += `<text class="tick" x="${gx}" y="${H - 4}" text-anchor="middle">${+t.toFixed(2)}</text>`;
    }
    methods.forEach((m, i) => {
      const y = top + i * rowH + (rowH - barH) / 2;
      const info = METHOD_INFO[m.id] || [];
      const label = m.label || info[0] || m.id;
      svg += `<text class="lbl" x="0" y="${y + barH / 2 + 4.5}">${esc(label)}</text>`;
      if (done) {
        const cls = m.id === 'oracle' ? 'b b--oracle' : m.id === best ? 'b b--best' : 'b';
        const w = Math.max(2, x(m.kcal_mae) - labelW);
        svg += `<rect class="${cls}" x="${labelW}" y="${y}" width="${w}" height="${barH}" rx="4"><title>${esc(label)}: ${m.kcal_mae.toFixed(1)} kcal</title></rect>`;
        svg += `<text class="val" x="${labelW + w + 8}" y="${y + barH / 2 + 4}">${m.kcal_mae.toFixed(1)}</text>`;
      } else {
        svg += `<rect class="b b--ghost" x="${labelW}" y="${y}" width="${plotW}" height="${barH}" rx="4"/>`;
        svg += `<text class="tick" x="${labelW + 10}" y="${y + barH / 2 + 4}">computing</text>`;
      }
    });
    svg += '</svg>';
    host.innerHTML = svg;
    $('#chartCap').textContent = done
      ? 'Mean absolute error in kcal per 100 g. The hatched bar is the oracle: the closest any FSVO food could get.'
      : 'Results are being computed. Each bar will show the mean energy error in kcal per 100 g; the oracle row marks the best any FSVO match could do.';
  }

  function renderCost(res) {
    const c = res && res.status === 'done' && res.cost;
    $('#costSec').innerHTML = c && isNum(c.sec_per_line) ? c.sec_per_line.toFixed(2) : computing;
    $('#costChf').innerHTML = c && isNum(c.chf_per_1000_receipts) ? c.chf_per_1000_receipts.toFixed(2) : computing;
  }

  function renderByLang(res) {
    const host = $('#byLang');
    const rows = res && res.status === 'done' && Array.isArray(res.by_lang) ? res.by_lang.filter((r) => r && typeof r === 'object') : [];
    if (!rows.length) { host.hidden = true; return; }
    const keys = Object.keys(rows[0]);
    const isPct = (k) => /within|acc|abstain|share|rate/i.test(k);
    const fmt = (k, v) => !isNum(v) ? esc(v) : isPct(k) ? pct(v) : Number.isInteger(v) ? v.toLocaleString('en-US') : v.toFixed(2);
    host.innerHTML = `<div class="table-card"><div class="table-card__head"><h3 class="t-title">By receipt language</h3></div><div class="table-scroll" tabindex="0" role="region" aria-label="Results by language"><table class="rt" style="min-width:${Math.max(420, keys.length * 110)}px"><thead><tr>${keys.map((k) => `<th scope="col">${esc(k.replace(/_/g, ' '))}</th>`).join('')}</tr></thead><tbody>${rows.map((r) => `<tr>${keys.map((k) => `<td>${fmt(k, r[k])}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div>`;
    host.hidden = false;
  }

  function renderResults(res) {
    results = res;
    renderTable(res); renderChart(res); renderCost(res); renderByLang(res);
  }
  renderResults(null);
  getJSON('data/results.json').then(renderResults).catch(() => renderResults(null));
  let rz;
  window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => renderChart(results), 120); });
})();
