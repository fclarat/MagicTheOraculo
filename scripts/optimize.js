#!/usr/bin/env node
/*
 * Offline optimizer for the Magic The Mini Games Oracle engine. Replicates the engine
 * exactly but keeps a *pruned active set* (cards a perfect player has already
 * ruled out are dropped), so thousands of games run in seconds.
 *
 * Sweeps the tunable knobs to minimise average questions while keeping the
 * hit-rate (single guess correct OR target inside the pick-list) high.
 *   node scripts/optimize.js
 */
const fs = require('fs');
const path = require('path');
const DATA = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'cards.json'), 'utf8'));
const FEATS = DATA.features, NF = FEATS.length, CARDS = DATA.cards, NC = CARDS.length;
const FM = CARDS.map(c => { const a = new Int8Array(NF); for (let j = 0; j < NF; j++) { const ch = c.f[j]; a[j] = ch === '1' ? 1 : ch === '0' ? 0 : -1; } return a; });
// feature-major copy for cache-friendly, fast inner loops
const FT = []; for (let j = 0; j < NF; j++) { const col = new Int8Array(NC); for (let i = 0; i < NC; i++) col[i] = FM[i][j]; FT.push(col); }
const FID = {}; FEATS.forEach((f, i) => FID[f.id] = i);
const CMC_THR = { cmc_le1: ['le', 1], cmc_ge3: ['ge', 3], cmc_ge4: ['ge', 4], cmc_ge5: ['ge', 5], cmc_ge6: ['ge', 6], cmc_ge8: ['ge', 8] };
const COLOR_IDS = ['white', 'blue', 'black', 'red', 'green'];
const P_YES = { 1: 0.85, 0: 0.15, '-1': 0.5 };
const PRUNE = 12;   // drop cards whose log-prob is >e^12 below the max (perfect player keeps the true card at the top, so this is safe and shrinks the set fast)

const DEF = {   // "mago" operating point
  PRIOR_EXP: 0.35, PRIOR_BASE: 40, PRIOR_NULL: 9000, BETA: 1.8,
  GUESS_P: 0.86, GUESS_MIN_Q: 8, GUESS_MID_P: 0.6, GUESS_RATIO: 4, GUESS_MAX_Q: 20,
  MIN_GAIN: 0.03, LIST_MAX_Q: 18, LIST_N: 8, LIST_FRAC: 0.15,
  LIST_COVER: 0.9, ANS_YES: 0.9,
};

function constraints(answers) { let lo = 0, hi = 99; const cYes = new Set(), cNo = new Set(); let clYes = false, clNo = false, mYes = false, mNo = false; for (const [j, a] of answers) { const id = FEATS[j].id, yes = a >= 0.85, no = a <= 0.15; if (CMC_THR[id]) { const [t, N] = CMC_THR[id]; if (t === 'ge') { if (yes) lo = Math.max(lo, N); else if (no) hi = Math.min(hi, N - 1); } else { if (yes) hi = Math.min(hi, N); else if (no) lo = Math.max(lo, N + 1); } } else if (COLOR_IDS.includes(id)) { if (yes) cYes.add(id); else if (no) cNo.add(id); } else if (id === 'colorless') { if (yes) clYes = true; else if (no) clNo = true; } else if (id === 'multicolor') { if (yes) mYes = true; else if (no) mNo = true; } } return { lo, hi, cYes, cNo, clYes, clNo, mYes, mNo }; }
function determined(j, C) { const id = FEATS[j].id; if (CMC_THR[id]) { const [t, N] = CMC_THR[id]; return t === 'ge' ? (C.lo >= N || C.hi < N) : (C.hi <= N || C.lo > N); } if (COLOR_IDS.includes(id)) { if (C.clYes) return true; if (C.cYes.has(id) || C.cNo.has(id)) return true; if (C.cYes.size >= 1 && C.mNo) return true; if (C.cNo.size >= 4 && C.clNo) return true; return false; } if (id === 'colorless') return C.clYes || C.clNo || C.cYes.size >= 1; if (id === 'multicolor') return C.mYes || C.mNo || C.cYes.size >= 2 || C.clYes || C.cNo.size >= 4; return false; }

function makeEngine(P) {
  const PRIOR_LP = new Float64Array(NC);
  { let s = 0; for (let i = 0; i < NC; i++) { const w = 1 / Math.pow((CARDS[i].rk || P.PRIOR_NULL) + P.PRIOR_BASE, P.PRIOR_EXP); PRIOR_LP[i] = w; s += w; } for (let i = 0; i < NC; i++) PRIOR_LP[i] = Math.log(PRIOR_LP[i] / s); }
  // Start every game from the top-3000 by prior (one sort per param set). Cards
  // below that never win against a popular target, so this matches the app's
  // active-set cap while avoiding a 32k sort every turn.
  const PRIOR_ORDER = Array.from({ length: NC }, (_, i) => i).sort((a, b) => PRIOR_LP[b] - PRIOR_LP[a]);
  const ACT0 = Int32Array.from(PRIOR_ORDER.slice(0, Math.min(3000, NC)));

  function nextFeature(act, pp, asked, answers) {
    const C = constraints(answers);
    if (C.cYes.size === 1 && !C.mYes && !C.mNo && !C.clYes) { const mj = FID.multicolor; if (mj != null && !asked.has(mj)) return { j: mj, gain: 1 }; }
    const M = act.length;
    const ps = new Float64Array(M); let s = 0;
    for (let x = 0; x < M; x++) { ps[x] = Math.pow(pp[x], P.BETA); s += ps[x]; }
    for (let x = 0; x < M; x++) ps[x] /= s;
    let H = 0; for (let x = 0; x < M; x++) { const q = ps[x]; if (q > 1e-12) H -= q * Math.log(q); }
    let best = -1, bg = -Infinity;
    for (let j = 0; j < NF; j++) {
      if (asked.has(j) || determined(j, C)) continue;
      const col = FT[j];
      let pyes = 0; for (let x = 0; x < M; x++) { const v = col[act[x]]; pyes += ps[x] * (v === 1 ? 0.85 : v === 0 ? 0.15 : 0.5); }
      const pno = 1 - pyes; if (pyes < 1e-6 || pno < 1e-6) continue;
      let hy = 0, hn = 0; for (let x = 0; x < M; x++) { const v = col[act[x]]; const w = v === 1 ? 0.85 : v === 0 ? 0.15 : 0.5; const ay = ps[x] * w / pyes, an = ps[x] * (1 - w) / pno; if (ay > 1e-12) hy -= ay * Math.log(ay); if (an > 1e-12) hn -= an * Math.log(an); }
      const g = H - (pyes * hy + pno * hn); if (g > bg) { bg = g; best = j; }
    }
    return { j: best, gain: bg };
  }

  function play(t) {
    const lp = Float64Array.from(PRIOR_LP);
    let act = Int32Array.from(ACT0);
    const asked = new Set(), answers = new Map(); let qcount = 0, steps = 0;
    const N = Math.max(2, P.LIST_N);
    while (true) {
      const m = act.length;
      let mx = -Infinity; for (let k = 0; k < m; k++) { const v = lp[act[k]]; if (v > mx) mx = v; }
      let s = 0; const pp = new Float64Array(m); for (let k = 0; k < m; k++) { pp[k] = Math.exp(lp[act[k]] - mx); s += pp[k]; } for (let k = 0; k < m; k++) pp[k] /= s;
      // top-N over active set
      const top = [];
      for (let k = 0; k < m; k++) { const v = pp[k]; if (top.length < N) { top.push([k, v]); if (top.length === N) top.sort((a, b) => b[1] - a[1]); } else if (v > top[N - 1][1]) { top[N - 1] = [k, v]; let q = N - 1; while (q > 0 && top[q][1] > top[q - 1][1]) { const tt = top[q]; top[q] = top[q - 1]; top[q - 1] = tt; q--; } } }
      top.sort((a, b) => b[1] - a[1]);
      const a0 = top[0], b0 = top[1]; const ratio = b0 ? a0[1] / b0[1] : Infinity;
      let guess = null;
      if (a0[1] >= P.GUESS_P) guess = a0;
      else if (qcount >= P.GUESS_MIN_Q && a0[1] >= P.GUESS_MID_P && ratio >= P.GUESS_RATIO) guess = a0;
      else if (qcount >= P.GUESS_MAX_Q) guess = a0;
      if (guess) return { q: qcount, hit: act[guess[0]] === t };
      let cover = 0; for (let z = 0; z < top.length; z++) cover += top[z][1];
      const cont = top.filter(c => c[1] >= top[0][1] * P.LIST_FRAC);
      if (cover >= P.LIST_COVER && cont.length >= 2) return { q: qcount, hit: cont.some(c => act[c[0]] === t), list: cont.length };
      const nf = nextFeature(act, pp, asked, answers);
      if (nf.j < 0 || nf.gain < P.MIN_GAIN || qcount >= P.LIST_MAX_Q) {
        if (cont.length >= 2) return { q: qcount, hit: cont.some(c => act[c[0]] === t), list: cont.length };
        return { q: qcount, hit: act[top[0][0]] === t };
      }
      const col = FT[nf.j]; const v = col[t]; const av = v === 1 ? P.ANS_YES : v === 0 ? (1 - P.ANS_YES) : 0.5;
      const ly = Math.log(av), ln = Math.log(1 - av), lu = Math.log(0.5);
      for (let k = 0; k < m; k++) { const fv = col[act[k]]; lp[act[k]] += fv === 1 ? ly : fv === 0 ? ln : lu; }
      asked.add(nf.j); answers.set(nf.j, av); if (v !== -1) qcount++;
      // prune ruled-out cards
      let mx2 = -Infinity; for (let k = 0; k < m; k++) { const val = lp[act[k]]; if (val > mx2) mx2 = val; }
      const thr = mx2 - PRUNE, keep = [];
      for (let k = 0; k < m; k++) if (lp[act[k]] >= thr) keep.push(act[k]);
      act = Int32Array.from(keep);
      if (++steps > 45) return { q: qcount, hit: false };
    }
  }
  return { play };
}

function evalP(over, sample) {
  const P = Object.assign({}, DEF, over);
  const eng = makeEngine(P);
  let sumq = 0, hit = 0, mx = 0, lists = 0, over15 = 0;
  for (const t of sample) { const r = eng.play(t); sumq += r.q; if (r.hit) hit++; if (r.q > mx) mx = r.q; if (r.list) lists++; if (r.q > 15) over15++; }
  const n = sample.length;
  return { avgQ: +(sumq / n).toFixed(2), hitPct: +(100 * hit / n).toFixed(1), maxQ: mx, listPct: +(100 * lists / n).toFixed(0), over15: +(100 * over15 / n).toFixed(0) };
}

const N_SAMPLE = +process.argv[2] || 500;
const POP = []; for (let i = 0; i < N_SAMPLE; i++) POP.push(i);

const combos = [
  ['BETA 3.0', { BETA: 3.0 }],
  ['BETA 3.5', { BETA: 3.5 }],
  ['BETA 4.0', { BETA: 4.0 }],
  ['BETA 5.0', { BETA: 5.0 }],
  ['BETA 6.0', { BETA: 6.0 }],
];

console.log(`cards=${NC} features=${NF}  sample=top ${POP.length} popular\n`);
console.log('combo'.padEnd(24), 'avgQ'.padStart(6), 'hit%'.padStart(6), 'list%'.padStart(6), '>15q%'.padStart(6), 'maxQ'.padStart(6));
const t0 = Date.now();
for (const [name, over] of combos) {
  const r = evalP(over, POP);
  console.log(name.padEnd(24), String(r.avgQ).padStart(6), String(r.hitPct).padStart(6), String(r.listPct).padStart(6), String(r.over15).padStart(6), String(r.maxQ).padStart(6));
}
console.log(`\n(${((Date.now() - t0) / 1000).toFixed(1)}s)`);
