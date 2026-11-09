/* MotoJava demo — bike gallery and lightbox. */
(function () {
  'use strict';
  var gal = document.querySelector('[data-gallery]');
  var lb = document.querySelector('[data-lightbox]');
  if (!gal || !lb) return;

  var main = gal.querySelector('.gallery-main');
  var thumbs = Array.prototype.slice.call(gal.querySelectorAll('.thumbs button'));
  var srcs = thumbs.map(function (b) { return b.getAttribute('data-full'); });
  var srcsets = thumbs.map(function (b) { return b.getAttribute('data-srcset') || ''; });

  /* The main <img> uses srcset with width descriptors, so src alone is ignored by the
     browser's source selection; both must change together. */
  function setMain(i) {
    if (srcsets[i]) main.srcset = srcsets[i]; else main.removeAttribute('srcset');
    main.src = srcs[i];
    main.alt = label(i);
  }
  var title = main.getAttribute('alt').replace(/, photo \d+ of \d+$/, '');
  var lbImg = lb.querySelector('.lb-img');
  var counter = lb.querySelector('.lb-counter');
  var index = 0;
  var opener = null;
  var startX = null;

  function label(i) { return title + ', photo ' + (i + 1) + ' of ' + srcs.length; }

  function select(i) {
    index = (i + srcs.length) % srcs.length;
    setMain(index);
    thumbs.forEach(function (b, j) { b.setAttribute('aria-current', j === index ? 'true' : 'false'); });
  }

  function show(i) {
    index = (i + srcs.length) % srcs.length;
    lbImg.src = srcs[index];
    lbImg.alt = label(index);
    counter.textContent = (index + 1) + ' of ' + srcs.length;
    select(index);
  }

  function open(i, fromEl) {
    opener = fromEl || document.activeElement;
    show(i);
    if (typeof lb.showModal === 'function') lb.showModal(); else lb.setAttribute('open', '');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    if (lb.open) lb.close(); else lb.removeAttribute('open');
    document.body.style.overflow = '';
    if (opener && typeof opener.focus === 'function') opener.focus();
  }

  thumbs.forEach(function (b, i) {
    b.addEventListener('click', function () { select(i); });
    b.addEventListener('dblclick', function () { open(i, b); });
  });
  gal.querySelector('[data-open]').addEventListener('click', function (e) { open(index, thumbs[index] || e.currentTarget); });
  lb.querySelector('[data-prev]').addEventListener('click', function () { show(index - 1); });
  lb.querySelector('[data-next]').addEventListener('click', function () { show(index + 1); });
  lb.querySelector('[data-close]').addEventListener('click', close);
  lb.addEventListener('cancel', function (e) { e.preventDefault(); close(); });
  lb.addEventListener('click', function (e) { if (e.target === lb) close(); });
  lb.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') show(index - 1);
    if (e.key === 'ArrowRight') show(index + 1);
  });
  lb.addEventListener('touchstart', function (e) { startX = e.touches[0].clientX; }, { passive: true });
  lb.addEventListener('touchend', function (e) {
    if (startX === null) return;
    var dx = e.changedTouches[0].clientX - startX;
    if (dx > 40) show(index - 1); else if (dx < -40) show(index + 1);
    startX = null;
  });

  select(0);
})();
