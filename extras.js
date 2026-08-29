/* Shared "mental reward" layer for the Magic The Oráculo mini-games:
   per-device stats (localStorage), a celebration modal with a win/loss card,
   a streak + win-rate + guess-distribution block, share-to-clipboard, confetti. */
window.MTO = (function () {
  const esc = s => String(s).replace(/[&<>"]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]));
  const key = g => 'mto_stats_' + g;
  const blank = () => ({ played: 0, won: 0, cur: 0, max: 0, lastWin: null, dist: {} });
  function stats(g) { try { const s = JSON.parse(localStorage.getItem(key(g))); if (s && typeof s.played === 'number') return Object.assign(blank(), s); } catch (e) {} return blank(); }
  function save(g, s) { try { localStorage.setItem(key(g), JSON.stringify(s)); } catch (e) {} }
  const ymd = d => d.toISOString().slice(0, 10);

  function record(g, { won, mode, score }) {
    const s = stats(g); s.played++;
    if (won) { s.won++; if (score != null) s.dist[score] = (s.dist[score] || 0) + 1; }
    if (mode === 'daily') {
      const today = ymd(new Date()), yest = ymd(new Date(Date.now() - 864e5));
      if (won) { s.cur = s.lastWin === today ? s.cur : (s.lastWin === yest ? s.cur + 1 : 1); s.lastWin = today; if (s.cur > s.max) s.max = s.cur; }
      else s.cur = 0;
    }
    save(g, s); return s;
  }

  function statsHtml(s, distLabel) {
    const pct = s.played ? Math.round(100 * s.won / s.played) : 0;
    let h = `<div class="mto-stats">
      <div><b>${s.played}</b><span>jugadas</span></div>
      <div><b>${pct}%</b><span>ganadas</span></div>
      <div><b>${s.cur}</b><span>racha</span></div>
      <div><b>${s.max}</b><span>mejor</span></div></div>`;
    const keys = Object.keys(s.dist).map(Number).sort((a, b) => a - b);
    if (keys.length) {
      const mx = Math.max(...keys.map(k => s.dist[k]));
      h += `<div class="mto-dist">` + keys.map(k =>
        `<div class="mto-bar"><span class="bk">${k}</span><i style="width:${Math.max(9, Math.round(100 * s.dist[k] / mx))}%">${s.dist[k]}</i></div>`).join('') + `</div>`;
      if (distLabel) h += `<div class="mto-distlab">${esc(distLabel)}</div>`;
    }
    return h;
  }

  function copy(t) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(t).catch(() => fallbackCopy(t));
    fallbackCopy(t);
  }
  function fallbackCopy(t) { const ta = document.createElement('textarea'); ta.value = t; ta.style.cssText = 'position:fixed;left:-9999px'; document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); } catch (e) {} ta.remove(); }

  function confetti() {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const cv = document.createElement('canvas'); cv.className = 'mto-confetti';
    cv.width = innerWidth; cv.height = innerHeight; document.body.appendChild(cv);
    const x = cv.getContext('2d'), cols = ['#e3b45a', '#57c98a', '#4a9fd6', '#b98bd0', '#dc5138', '#f4ecd0'];
    const P = Array.from({ length: 140 }, () => ({
      x: innerWidth / 2 + (Math.random() - .5) * 140, y: innerHeight / 3,
      vx: (Math.random() - .5) * 12, vy: Math.random() * -14 - 4,
      s: Math.random() * 6 + 3, c: cols[(Math.random() * cols.length) | 0], a: 1, rot: Math.random() * 6
    }));
    let t = 0;
    (function frame() {
      t++; x.clearRect(0, 0, cv.width, cv.height);
      P.forEach(p => { p.vy += .5; p.x += p.vx; p.y += p.vy; p.rot += .2; p.a -= .012;
        x.globalAlpha = Math.max(0, p.a); x.fillStyle = p.c;
        x.save(); x.translate(p.x, p.y); x.rotate(p.rot); x.fillRect(-p.s / 2, -p.s / 2, p.s, p.s * .6); x.restore(); });
      if (t < 130) requestAnimationFrame(frame); else cv.remove();
    })();
  }

  function end(g, o) {
    const s = record(g, { won: o.won, mode: o.mode, score: o.score });
    let m = document.getElementById('mto-modal');
    if (!m) { m = document.createElement('div'); m.id = 'mto-modal'; m.className = 'mto-modal'; document.body.appendChild(m); }
    m.innerHTML = `<div class="mto-panel" role="dialog" aria-modal="true">
      <button class="mto-x" aria-label="Cerrar">✕</button>
      <div class="mto-eyebrow" style="color:${o.won ? 'var(--good)' : 'var(--bad)'}">${o.won ? '¡Le pegaste! 🎉' : 'Casi…'}</div>
      <h2 class="mto-title">${esc(o.title || '')}</h2>
      ${o.subtitle ? `<p class="mto-sub">${esc(o.subtitle)}</p>` : ''}
      ${o.bodyHtml || ''}
      ${statsHtml(s, o.distLabel)}
      <div class="mto-actions">
        ${o.shareText ? `<button class="btn btn-primary mto-share">Compartir 📋</button>` : ''}
        <button class="btn mto-again">Jugar de nuevo</button>
        <a class="btn" href="index.html">Otros juegos</a>
      </div>
      <div class="mto-copied" hidden>¡Copiado al portapapeles!</div>
    </div>`;
    m.classList.add('show');
    const close = () => m.classList.remove('show');
    m.querySelector('.mto-x').onclick = close;
    m.onclick = e => { if (e.target === m) close(); };
    m.querySelector('.mto-again').onclick = () => o.onAgain ? o.onAgain() : location.reload();
    const sb = m.querySelector('.mto-share');
    if (sb) sb.onclick = () => { copy(o.shareText); const c = m.querySelector('.mto-copied'); c.hidden = false; setTimeout(() => { c.hidden = true; }, 1800); };
    if (o.won) confetti();
    return s;
  }

  return { end, stats, record, statsHtml };
})();

/* colorblind-safe palette (shared + persisted): swaps green/gold for orange/blue.
   Applied to <html> so tiles pick it up before first render; any #cbtoggle button
   in the page is auto-wired. The setting is shared across all games. */
(function () {
  try { if (localStorage.getItem('mto_cb') === '1') document.documentElement.classList.add('cb'); } catch (e) {}
  function sync(btn) { if (btn) btn.setAttribute('aria-pressed', document.documentElement.classList.contains('cb') ? 'true' : 'false'); }
  window.MTO.cbInit = function () {
    var btn = document.getElementById('cbtoggle'); if (!btn) return;
    sync(btn);
    btn.onclick = function () {
      var now = document.documentElement.classList.toggle('cb');
      try { localStorage.setItem('mto_cb', now ? '1' : '0'); } catch (e) {}
      sync(btn);
    };
  };
  if (document.readyState !== 'loading') window.MTO.cbInit();
  else document.addEventListener('DOMContentLoaded', window.MTO.cbInit);
})();
