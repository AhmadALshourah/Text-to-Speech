/* VoiceForge — Animations Layer
   Safe: never hides elements. Only enhances existing CSS animations. */

(function () {
  'use strict';

  /* ── Button ripple ────────────────────────────────────────────────────── */
  function initRipple() {
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.btn, .play-btn, .dl-btn, .share-btn');
      if (!btn || btn.disabled) return;

      var r    = btn.getBoundingClientRect();
      var size = Math.max(r.width, r.height) * 1.6;
      var x    = e.clientX - r.left  - size / 2;
      var y    = e.clientY - r.top   - size / 2;

      var el = document.createElement('span');
      el.className = 'ripple';
      el.style.cssText = 'width:' + size + 'px;height:' + size + 'px;left:' + x + 'px;top:' + y + 'px;';

      if (getComputedStyle(btn).position === 'static') btn.style.position = 'relative';
      btn.appendChild(el);
      el.addEventListener('animationend', function () { el.remove(); }, { once: true });
    });
  }

  /* ── Range slider fill track ─────────────────────────────────────────── */
  function updateRangeFill(input) {
    var min = +input.min || 0;
    var max = +input.max || 100;
    var val = +input.value;
    var pct = ((val - min) / (max - min)) * 100;
    /* Always fill left→right so gradient matches visual */
    input.style.background =
      'linear-gradient(to right, var(--violet) ' + pct + '%, rgba(255,255,255,.1) ' + pct + '%)';
  }

  function initRangeFills() {
    document.querySelectorAll('input[type="range"]').forEach(function (input) {
      updateRangeFill(input);
      input.addEventListener('input', function () { updateRangeFill(input); });
    });
  }

  /* ── Topbar shadow on scroll ─────────────────────────────────────────── */
  function initTopbarScroll() {
    var topbar = document.querySelector('.topbar');
    if (!topbar) return;
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        topbar.classList.toggle('scrolled', window.scrollY > 8);
        ticking = false;
      });
    }, { passive: true });
  }

  /* ── Magnetic synth button ───────────────────────────────────────────── */
  function initMagnetic() {
    var btn = document.getElementById('synthBtn');
    if (!btn) return;
    btn.addEventListener('mousemove', function (e) {
      var r  = btn.getBoundingClientRect();
      var dx = (e.clientX - r.left  - r.width  / 2) * 0.2;
      var dy = (e.clientY - r.top   - r.height / 2) * 0.15;
      btn.style.transform = 'translate(' + dx + 'px,' + dy + 'px) scale(1.012)';
    });
    btn.addEventListener('mouseleave', function () {
      btn.style.transform = '';
    });
  }

  /* ── Play button pulsing ring class toggle ───────────────────────────── */
  function initPlayBtnRing() {
    var playBtn = document.getElementById('playBtn');
    if (!playBtn) return;
    var waveform = document.getElementById('waveform');
    /* Observe waveform class changes */
    if (!waveform || typeof MutationObserver === 'undefined') return;
    var mo = new MutationObserver(function () {
      playBtn.classList.toggle('is-playing', waveform.classList.contains('playing'));
    });
    mo.observe(waveform, { attributes: true, attributeFilter: ['class'] });
  }

  /* ── Stagger entrance for stat items ────────────────────────────────── */
  function initStatStagger() {
    document.querySelectorAll('.stats-strip .stat-item').forEach(function (el, i) {
      el.style.animationDelay = (0.28 + i * 0.07) + 's';
      el.style.animation = 'fade-up .6s var(--ease) ' + (0.28 + i * 0.07) + 's both';
    });
  }

  /* ── Progress-fill shimmer pause on hover ───────────────────────────── */
  function initProgressHover() {
    var track = document.getElementById('progressTrack');
    var fill  = document.getElementById('progressFill');
    if (!track || !fill) return;
    track.addEventListener('mouseenter', function () { fill.style.animationPlayState = 'paused'; });
    track.addEventListener('mouseleave', function () { fill.style.animationPlayState = 'running'; });
  }

  /* ── Card entrance stagger ───────────────────────────────────────────── */
  function initCardStagger() {
    document.querySelectorAll('.card').forEach(function (card, i) {
      /* Only add delay if no animation already set inline */
      if (!card.style.animation) {
        card.style.animationDelay = (0.1 + i * 0.06) + 's';
        card.style.animation = 'fade-up .7s var(--ease) ' + (0.1 + i * 0.06) + 's both';
      }
    });
  }

  /* ── Boot ────────────────────────────────────────────────────────────── */
  function boot() {
    initRipple();
    initRangeFills();
    initTopbarScroll();
    initProgressHover();
    initStatStagger();
    initCardStagger();
    initPlayBtnRing();

    /* Magnetic hover — only on desktop pointer */
    if (window.matchMedia('(pointer: fine)').matches) {
      initMagnetic();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
