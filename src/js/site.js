/* MotoJava demo — site behaviors: service form (Task 8); nav sheet, text size, hours, call bar (Task 9). */
(function () {
  'use strict';

  /* Service request form: builds a prefilled mailto and opens it. Exposed for checks. */
  function buildMailto(form) {
    var to = form.getAttribute('data-to') || '';
    var get = function (n) { var el = form.elements[n]; return el ? el.value.trim() : ''; };
    var body = 'Name: ' + get('name') + '\nPhone: ' + get('phone') + '\nBike: ' + get('bike') + '\n\n' + get('issue') + '\n';
    return 'mailto:' + to + '?subject=' + encodeURIComponent('Service request') + '&body=' + encodeURIComponent(body);
  }
  window.mjBuildMailto = buildMailto;

  function initServiceForm() {
    var form = document.querySelector('[data-service-form]');
    if (!form) return;
    var note = form.querySelector('[data-form-note]');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var ok = true;
      Array.prototype.forEach.call(form.querySelectorAll('[required]'), function (el) {
        var bad = !el.value.trim();
        el.setAttribute('aria-invalid', bad ? 'true' : 'false');
        if (bad && ok) { el.focus(); ok = false; }
      });
      if (!ok) {
        if (note) { note.textContent = 'Please fill in every field.'; note.hidden = false; }
        return;
      }
      var href = buildMailto(form);
      if (note) { note.textContent = 'Opening your email app with the request filled in.'; note.hidden = false; }
      window.location.href = href;
    });
  }

  /* Mobile nav sheet */
  function initSheet() {
    var btn = document.querySelector('[data-menu]');
    var sheet = document.querySelector('[data-sheet]');
    if (!btn || !sheet) return;
    var panel = sheet.querySelector('.sheet-panel');
    function focusables() {
      return Array.prototype.slice.call(panel.querySelectorAll('a[href], button:not([disabled])'));
    }
    function open() {
      sheet.hidden = false;
      btn.setAttribute('aria-expanded', 'true');
      document.body.classList.add('sheet-open');
      var f = focusables();
      if (f.length) f[0].focus();
    }
    function close() {
      sheet.hidden = true;
      btn.setAttribute('aria-expanded', 'false');
      document.body.classList.remove('sheet-open');
      btn.focus();
    }
    btn.addEventListener('click', function () { sheet.hidden ? open() : close(); });
    sheet.addEventListener('click', function (e) { if (e.target.closest('[data-sheet-close]')) close(); });
    document.addEventListener('keydown', function (e) {
      if (sheet.hidden) return;
      if (e.key === 'Escape') { close(); return; }
      if (e.key === 'Tab') {
        var f = focusables();
        if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
    window.mjSheet = { open: open, close: close };
  }

  /* Text size: two states, persisted, all controls stay in sync */
  function initTextSize() {
    var root = document.documentElement;
    var buttons = Array.prototype.slice.call(document.querySelectorAll('.seg button[data-size]'));
    if (!buttons.length) return;
    function apply(size) {
      if (size === 'large') root.setAttribute('data-text', 'large'); else root.removeAttribute('data-text');
      try { localStorage.setItem('mj-text', size); } catch (e) { /* private mode */ }
      buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-size') === size)); });
    }
    buttons.forEach(function (b) { b.addEventListener('click', function () { apply(b.getAttribute('data-size')); }); });
    apply(root.getAttribute('data-text') === 'large' ? 'large' : 'default');
    window.mjTextSize = apply;
  }

  /* Hours: bold today's row */
  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  function markToday(dayIndex) {
    var i = (typeof dayIndex === 'number') ? dayIndex : new Date().getDay();
    var day = DAYS[((i % 7) + 7) % 7];
    Array.prototype.forEach.call(document.querySelectorAll('[data-hours] [data-day]'), function (row) {
      row.classList.toggle('today', row.getAttribute('data-day') === day);
    });
    return day;
  }
  window.mjMarkToday = markToday;

  document.addEventListener('DOMContentLoaded', function () {
    initServiceForm();
    initSheet();
    initTextSize();
    markToday();
  });
})();
