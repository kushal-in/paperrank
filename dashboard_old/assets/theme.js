/* Look switcher: "revaluation" <-> "sarkari". Dash tells us the theme through the clientside callback in app.py. */
(function () {
  function overlay(ms, done) {
    var o = document.getElementById('gov-loading');
    if (!o) { done(); return; }
    var skip = document.getElementById('gov-skip');
    var finished = false;
    o.classList.add('on');
    skip.style.visibility = 'hidden';
    function fin() { if (finished) return; finished = true; o.classList.remove('on'); done(); }
    setTimeout(function () { skip.style.visibility = 'visible'; }, 2200);
    skip.onclick = fin;
    setTimeout(fin, ms);
  }
  function sessionPopup() {
    setInterval(function () {
      var p = document.getElementById('gov-session');
      if (p && document.documentElement.getAttribute('data-theme') === 'sarkari') p.classList.add('on');
    }, 45000);
    document.addEventListener('click', function (e) {
      if (e.target && e.target.id === 'gov-extend') document.getElementById('gov-session').classList.remove('on');
    });
  }
  sessionPopup();
  window.dash_clientside = Object.assign({}, window.dash_clientside, {
    rev: {
      applyTheme: function (theme) {
        var root = document.documentElement;
        if (!theme) return '';
        if (!window.__themeSeen) { window.__themeSeen = true; root.setAttribute('data-theme', theme); return ''; }
        if (root.getAttribute('data-theme') === theme) return '';
        if (theme === 'sarkari') { overlay(6000, function () { root.setAttribute('data-theme', theme); }); }
        else { root.setAttribute('data-theme', theme); }
        return '';
      }
    }
  });
})();
