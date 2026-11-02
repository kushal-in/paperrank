// retro.js - count-up numbers and the slow spin of the hero 3D chart. Plain JS, no libraries.
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function countUp(el) {
    if (el.dataset.done) return; el.dataset.done = '1';
    var to = parseFloat(el.dataset.to), dec = parseInt(el.dataset.dec || '0', 10);
    var fmt = function (v) { return v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }); };
    if (reduce) { el.textContent = fmt(to); return; }
    var t0 = null, dur = 1400;
    function step(t) {
      if (t0 === null) t0 = t;
      var p = Math.min((t - t0) / dur, 1), e = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(to * e);
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  var spinning = null, angle = 0, paused = false, resumeTimer = null;
  function spin() {
    var host = document.getElementById('hero3d');
    var gd = host && host.querySelector('.js-plotly-plot');
    if (!gd || !window.Plotly || !gd._fullLayout || !gd._fullLayout.scene) { spinning = null; return; }
    if (!paused && !reduce) {
      angle += 0.0045;
      var r = 2.45;
      try {
        window.Plotly.relayout(gd, { 'scene.camera.eye': { x: r * Math.cos(angle), y: r * Math.sin(angle), z: 0.95 } });
      } catch (e) {}
    }
    spinning = setTimeout(spin, 60);
  }
  function arm() {
    var host = document.getElementById('hero3d');
    if (!host || host.dataset.armed) return;
    host.dataset.armed = '1';
    var stop = function () { paused = true; clearTimeout(resumeTimer); };
    var go = function () { clearTimeout(resumeTimer); resumeTimer = setTimeout(function () { paused = false; }, 3500); };
    host.addEventListener('pointerdown', stop); host.addEventListener('wheel', function () { stop(); go(); }, { passive: true });
    window.addEventListener('pointerup', go);
    if (!spinning) spinning = setTimeout(spin, 800);
  }

  new MutationObserver(function () {
    document.querySelectorAll('.countup').forEach(countUp);
    arm();
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
