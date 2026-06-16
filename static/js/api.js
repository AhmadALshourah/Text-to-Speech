/* =========================================================================
   api.js — Shared utilities
   - Auth helpers (token storage, session management)
   - Fetch wrapper with auto-refresh (IDEA-14)
   - i18n system — Arabic / English (IDEA-35)
   - Toast notifications
   - Theme (light / dark)
   - Animated background orbs
   - Button ripple effect
   ========================================================================= */

const TOKEN_KEY = "vf_token";
const USER_KEY  = "vf_user";
const LANG_KEY  = "vf_lang";

/* ── Auth helpers ─────────────────────────────────────────────────────────── */
const Auth = {
  getToken() { return localStorage.getItem(TOKEN_KEY); },

  setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  getUser() {
    try { return JSON.parse(localStorage.getItem(USER_KEY)); }
    catch { return null; }
  },

  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  isLoggedIn() { return !!localStorage.getItem(TOKEN_KEY); },
};

/* ── Token freshness (client-side, no network) ───────────────────────────── */
function isTokenFresh(minSecondsLeft = 60) {
  const token = Auth.getToken();
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp > 0 && Date.now() / 1000 < payload.exp - minSecondsLeft;
  } catch {
    return false;
  }
}

/* ── Refresh token (IDEA-14) ─────────────────────────────────────────────── */
let _refreshPromise = null;  // deduplicate concurrent refresh calls

async function refreshAccessToken() {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "include",   // send the HttpOnly refresh cookie
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        Auth.clear();
        return false;
      }
      const data = await res.json();
      Auth.setSession(data.access_token, data.user);
      return true;
    } catch {
      Auth.clear();
      return false;
    } finally {
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

/* ── Generic fetch wrapper ───────────────────────────────────────────────── */
async function apiRequest(path, { method = "GET", body, auth = false } = {}) {
  // Proactively refresh if token expires within 60 seconds
  if (auth && !isTokenFresh(60)) {
    const ok = await refreshAccessToken();
    if (!ok && auth) {
      location.href = "/login";
      throw new Error("انتهت الجلسة.");
    }
  }

  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const t = Auth.getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  const res = await fetch(path, {
    method,
    headers,
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });

  // On 401 — try one silent refresh, then retry
  if (res.status === 401 && auth) {
    const ok = await refreshAccessToken();
    if (!ok) {
      location.href = "/login";
      throw new Error("انتهت الجلسة.");
    }
    // Retry once with fresh token
    const t2 = Auth.getToken();
    const headers2 = { "Content-Type": "application/json", "Authorization": `Bearer ${t2}` };
    const res2 = await fetch(path, {
      method, headers: headers2, credentials: "include",
      body: body ? JSON.stringify(body) : undefined,
    });
    return _handleResponse(res2);
  }

  return _handleResponse(res);
}

async function _handleResponse(res) {
  if (!res.ok) {
    let message = `خطأ (${res.status})`;
    try {
      const data = await res.json();
      if (data.detail) {
        message = Array.isArray(data.detail)
          ? data.detail.map((d) => d.msg).join("، ")
          : data.detail;
      }
    } catch { /* ignore */ }
    if (res.status === 401) Auth.clear();
    throw new Error(message);
  }
  return res.status === 204 ? null : res.json();
}

/* ── i18n — IDEA-35 ──────────────────────────────────────────────────────── */
const i18n = {
  _t: {},
  _lang: "ar",

  async init() {
    const saved = localStorage.getItem(LANG_KEY) || "ar";
    await this.setLang(saved, false);   // false = don't re-apply on first load (done below)
    this.apply();
  },

  async setLang(lang, applyNow = true) {
    try {
      const r = await fetch(`/static/i18n/${lang}.json`);
      if (r.ok) this._t = await r.json();
    } catch { /* keep existing */ }
    this._lang = lang;
    localStorage.setItem(LANG_KEY, lang);
    document.documentElement.lang = lang;
    document.documentElement.dir  = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.setAttribute("data-lang", lang);
    // update toggle button label
    const btn = document.getElementById("langToggle");
    if (btn) btn.title = lang === "ar" ? "Switch to English" : "التبديل للعربية";
    if (applyNow) this.apply();
  },

  t(key, fallback = "") {
    return this._t[key] ?? fallback ?? key;
  },

  apply() {
    // Text content
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.getAttribute("data-i18n");
      const val = this._t[key];
      if (val !== undefined) el.textContent = val;
    });
    // Placeholder
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
      const val = this._t[el.getAttribute("data-i18n-placeholder")];
      if (val !== undefined) el.placeholder = val;
    });
    // Title attribute
    document.querySelectorAll("[data-i18n-title]").forEach(el => {
      const val = this._t[el.getAttribute("data-i18n-title")];
      if (val !== undefined) el.title = val;
    });
    // aria-label
    document.querySelectorAll("[data-i18n-aria]").forEach(el => {
      const val = this._t[el.getAttribute("data-i18n-aria")];
      if (val !== undefined) el.setAttribute("aria-label", val);
    });
    // Page title
    const titleEl = document.querySelector("title[data-i18n]");
    if (titleEl) {
      const val = this._t[titleEl.getAttribute("data-i18n")];
      if (val !== undefined) document.title = val;
    }
  },

  toggleLang() {
    const next = this._lang === "ar" ? "en" : "ar";
    this.setLang(next, true);
  },
};

/* ── Toast notifications ─────────────────────────────────────────────────── */
const TOAST_ICONS = { success: "✅", error: "❌", info: "💬" };

function toast(message, type = "info", duration = 3800) {
  let stack = document.querySelector(".toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "toast-stack";
    document.body.appendChild(stack);
  }

  const el = document.createElement("div");
  el.className = `toast ${type}`;

  const iconSpan = document.createElement("span");
  iconSpan.className = "toast-icon";
  iconSpan.textContent = TOAST_ICONS[type] || "💬";

  const msgSpan = document.createElement("span");
  msgSpan.style.flex = "1";
  msgSpan.textContent = message;

  const closeBtn = document.createElement("button");
  closeBtn.className = "toast-close";
  closeBtn.setAttribute("aria-label", "إغلاق");
  closeBtn.textContent = "✕";

  el.append(iconSpan, msgSpan, closeBtn);

  const close = () => {
    el.style.opacity = "0";
    el.style.transform = `translateX(20px)`;
    el.style.transition = "opacity .3s, transform .3s";
    setTimeout(() => el.remove(), 320);
  };

  closeBtn.addEventListener("click", close);
  stack.appendChild(el);
  setTimeout(close, duration);
}

/* ── Button ripple effect ────────────────────────────────────────────────── */
function addRipple(e) {
  const btn = e.currentTarget;
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const x = e.clientX - rect.left - size / 2;
  const y = e.clientY - rect.top  - size / 2;
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  ripple.style.cssText = `width:${size}px;height:${size}px;left:${x}px;top:${y}px`;
  btn.appendChild(ripple);
  ripple.addEventListener("animationend", () => ripple.remove());
}

function initRipples() {
  document.querySelectorAll(".btn-primary").forEach(btn => btn.addEventListener("click", addRipple));
}

/* ── Animated background orbs ────────────────────────────────────────────── */
function injectBgOrbs() {
  if (document.querySelector(".bg-orbs")) return;
  const wrap = document.createElement("div");
  wrap.className = "bg-orbs";
  wrap.innerHTML = `
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
  `;
  document.body.insertBefore(wrap, document.body.firstChild);
}

/* ── Theme (light / dark) ────────────────────────────────────────────────── */
const THEME_KEY = "vf_theme";

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(THEME_KEY, theme);
  const btn = document.getElementById("themeToggle");
  if (btn) btn.textContent = theme === "dark" ? "☀️" : "🌙";
}

function initTheme() {
  const saved       = localStorage.getItem(THEME_KEY);
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(saved || (prefersDark ? "dark" : "light"));
  const btn = document.getElementById("themeToggle");
  if (btn) {
    btn.addEventListener("click", () => {
      applyTheme(
        document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"
      );
    });
  }
}

function initLangToggle() {
  const btn = document.getElementById("langToggle");
  if (btn) btn.addEventListener("click", () => i18n.toggleLang());
}

/* ── Boot ────────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", async () => {
  injectBgOrbs();
  initTheme();
  initRipples();
  await i18n.init();   // load translations and apply
  initLangToggle();

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  }
});
