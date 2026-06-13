/* =========================================================================
   api.js — Shared utilities: token management, fetch wrapper,
            theme, toasts, background orbs, button ripple.
   ========================================================================= */

const TOKEN_KEY = "vf_token";
const USER_KEY  = "vf_user";

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

/* ── Generic fetch wrapper ───────────────────────────────────────────────── */
async function apiRequest(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const t = Auth.getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

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
  msgSpan.textContent = message; // textContent prevents XSS from server-supplied strings

  const closeBtn = document.createElement("button");
  closeBtn.className = "toast-close";
  closeBtn.setAttribute("aria-label", "إغلاق");
  closeBtn.textContent = "✕";

  el.append(iconSpan, msgSpan, closeBtn);

  const isRTL = document.documentElement.dir === "rtl";
  const close = () => {
    el.style.opacity = "0";
    el.style.transform = `translateX(${isRTL ? "-20px" : "20px"})`;
    el.style.transition = "opacity .3s, transform .3s";
    setTimeout(() => el.remove(), 320);
  };

  closeBtn.addEventListener("click", close);
  stack.appendChild(el);
  setTimeout(close, duration);
}

/* ── Token expiry check (client-side, no network needed) ─────────────────── */
function isTokenFresh() {
  const token = Auth.getToken();
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp > 0 && Date.now() / 1000 < payload.exp - 10;
  } catch {
    return false;
  }
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
  document.querySelectorAll(".btn-primary").forEach((btn) => {
    btn.addEventListener("click", addRipple);
  });
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
  const saved      = localStorage.getItem(THEME_KEY);
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(saved || (prefersDark ? "dark" : "light"));

  const btn = document.getElementById("themeToggle");
  if (btn) {
    btn.addEventListener("click", () => {
      const next =
        document.documentElement.getAttribute("data-theme") === "dark"
          ? "light"
          : "dark";
      applyTheme(next);
    });
  }
}

/* ── Boot ────────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  injectBgOrbs();
  initTheme();
  initRipples();

  // Register Service Worker — IDEA-21 (PWA)
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  }
});
