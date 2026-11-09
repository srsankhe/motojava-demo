/* MotoJava demo — inventory filters. Types OR together; one price band at a time.
   Selection mirrors to the URL hash: #type=scooter,sport&price=lt3000 */
(function () {
  'use strict';
  var grid = document.querySelector('[data-grid]');
  var bar = document.querySelector('[data-filters]');
  var empty = document.querySelector('[data-empty]');
  if (!grid || !bar) return;

  var cards = Array.prototype.slice.call(grid.querySelectorAll('.card'));
  var state = { type: [], price: '' };

  function inBand(price, band) {
    if (!band) return true;
    var p = parseInt(price, 10);
    if (isNaN(p)) return false;
    if (band === 'lt3000') return p < 3000;
    if (band === '3000-5000') return p >= 3000 && p <= 5000;
    if (band === 'gt5000') return p > 5000;
    return true;
  }

  function apply() {
    var shown = 0;
    cards.forEach(function (c) {
      var okType = state.type.length === 0 || state.type.indexOf(c.getAttribute('data-type')) !== -1;
      var okPrice = inBand(c.getAttribute('data-price'), state.price);
      var show = okType && okPrice;
      c.hidden = !show;
      if (show) shown++;
    });
    if (empty) empty.hidden = shown !== 0;
    bar.querySelectorAll('[data-group]').forEach(function (b) {
      var g = b.getAttribute('data-group'), v = b.getAttribute('data-value');
      var on = g === 'type' ? state.type.indexOf(v) !== -1 : state.price === v;
      b.setAttribute('aria-pressed', String(on));
    });
    var parts = [];
    if (state.type.length) parts.push('type=' + state.type.join(','));
    if (state.price) parts.push('price=' + state.price);
    var hash = parts.length ? '#' + parts.join('&') : '';
    if (hash !== location.hash) history.replaceState(null, '', hash || location.pathname + location.search);
  }

  function readHash() {
    var h = location.hash.replace(/^#/, '');
    state.type = []; state.price = '';
    h.split('&').forEach(function (kv) {
      var i = kv.indexOf('=');
      if (i < 0) return;
      var k = kv.slice(0, i), v = decodeURIComponent(kv.slice(i + 1));
      if (k === 'type') state.type = v.split(',').filter(Boolean);
      if (k === 'price') state.price = v;
    });
  }

  bar.addEventListener('click', function (e) {
    var b = e.target.closest('button');
    if (!b) return;
    if (b.hasAttribute('data-clear')) { state.type = []; state.price = ''; apply(); return; }
    var g = b.getAttribute('data-group'), v = b.getAttribute('data-value');
    if (!g) return;
    if (g === 'type') {
      var i = state.type.indexOf(v);
      if (i === -1) state.type.push(v); else state.type.splice(i, 1);
    } else if (g === 'price') {
      state.price = state.price === v ? '' : v;
    }
    apply();
  });

  window.addEventListener('hashchange', function () { readHash(); apply(); });
  readHash();
  apply();
})();
