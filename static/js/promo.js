/* promo.js — VoiceForge landing page interactivity (no inline scripts, CSP-safe) */

(function () {
  "use strict";

  /* ── Equalizer ─────────────────────────────────────────── */
  function buildEqualizer() {
    const wrap = document.getElementById("heroEqualizer");
    if (!wrap) return;
    const BAR_COUNT = 32;
    const frag = document.createDocumentFragment();
    for (let i = 0; i < BAR_COUNT; i++) {
      const span = document.createElement("span");
      span.className = "eq-bar";
      span.style.setProperty("--dur", (0.55 + Math.random() * 0.7).toFixed(2) + "s");
      span.style.setProperty("--del", (Math.random() * 0.6).toFixed(2) + "s");
      span.style.setProperty("--h",   (28 + Math.random() * 56).toFixed(0) + "%");
      frag.appendChild(span);
    }
    wrap.appendChild(frag);
  }

  /* ── Navbar scroll shadow ───────────────────────────────── */
  function initNavScroll() {
    const nav = document.getElementById("promoNav");
    if (!nav) return;
    const toggle = () => nav.classList.toggle("scrolled", window.scrollY > 40);
    toggle();
    window.addEventListener("scroll", toggle, { passive: true });
  }

  /* ── Smooth scroll for anchor links ────────────────────── */
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach((a) => {
      a.addEventListener("click", (e) => {
        const id = a.getAttribute("href").slice(1);
        const el = id ? document.getElementById(id) : null;
        if (!el) return;
        e.preventDefault();
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  /* ── Counter animation ──────────────────────────────────── */
  function animateCounter(el) {
    const target = parseInt(el.dataset.counter, 10);
    if (isNaN(target)) return;
    const dur = 1100;
    const start = performance.now();
    function easeOut(t) { return 1 - (1 - t) * (1 - t); }
    function step(now) {
      const t = Math.min((now - start) / dur, 1);
      el.textContent = Math.round(easeOut(t) * target);
      if (t < 1) requestAnimationFrame(step);
      else el.textContent = target;
    }
    requestAnimationFrame(step);
  }

  /* ── Scroll-reveal (IntersectionObserver) ───────────────── */
  function initReveal() {
    const els = Array.from(document.querySelectorAll("[data-animate]"));
    if (!els.length) return;

    /* Safety net — reveal all after 2.5 s in case observer never fires */
    const safetyTimer = setTimeout(() => {
      els.forEach((el) => {
        el.setAttribute("data-in", "");
      });
    }, 2500);

    /* Immediate fallback for browsers without IntersectionObserver */
    if (typeof IntersectionObserver === "undefined") {
      clearTimeout(safetyTimer);
      els.forEach((el) => el.setAttribute("data-in", ""));
      return;
    }

    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target;

          /* Apply stagger delay as CSS variable */
          const stagger = el.dataset.stagger;
          if (stagger) el.style.setProperty("--stagger", stagger);

          el.setAttribute("data-in", "");
          obs.unobserve(el);

          /* Animate counters found inside this element */
          el.querySelectorAll("[data-counter]").forEach(animateCounter);
          if (el.dataset.counter !== undefined) animateCounter(el);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    els.forEach((el) => obs.observe(el));

    /* Clear safety timer once the page is fully interacted with */
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) clearTimeout(safetyTimer);
    }, { once: true });
  }

  /* ── Bootstrap ──────────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    buildEqualizer();
    initNavScroll();
    initSmoothScroll();
    initReveal();
  });
})();
