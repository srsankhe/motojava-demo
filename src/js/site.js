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

  document.addEventListener('DOMContentLoaded', function () {
    initServiceForm();
  });
})();
