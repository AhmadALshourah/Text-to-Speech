/* =========================================================================
   app.js — TTS workspace logic

   Ideas implemented:
   IDEA-07  : Voice preview button
   IDEA-08  : .txt file upload
   IDEA-11  : Persistent voice/rate/volume preferences
   IDEA-18  : Auto language detection → suggests matching voices
   IDEA-19  : Keyboard shortcuts (Ctrl+Enter, Space, Ctrl+S)
   IDEA-20  : Word count alongside char count
   IDEA-22  : Focus mode toggle
   IDEA-23  : Drag & drop .txt files onto the textarea
   IDEA-24  : Accessibility (aria-live regions)
   IDEA-25  : SSML mode toggle
   ========================================================================= */

const PREFS_KEY = "vf_prefs";

/* ── Custom Audio Player ─────────────────────────────────────────────────── */
class AudioPlayer {
  constructor() {
    this.audio          = document.getElementById("audioEl");
    this.playBtn        = document.getElementById("playBtn");
    this.progressFill   = document.getElementById("progressFill");
    this.progressTrack  = document.getElementById("progressTrack");
    this.currentTimeEl  = document.getElementById("currentTime");
    this.durationEl     = document.getElementById("duration");
    this.waveform       = document.getElementById("waveform");

    this.audio.addEventListener("timeupdate",     () => this._onTick());
    this.audio.addEventListener("ended",          () => this._onEnded());
    this.audio.addEventListener("loadedmetadata", () => this._onLoaded());
    this.playBtn.addEventListener("click",        () => this.toggle());
    this.progressTrack.addEventListener("click",  (e) => this._seek(e));
  }

  load(url) {
    this.audio.src = url;
    this.progressFill.style.width = "0%";
    this.currentTimeEl.textContent = "0:00";
    this.durationEl.textContent    = "0:00";
    this._setPlaying(false);
  }

  toggle() { this.audio.paused ? this._play() : this._pause(); }

  // IDEA-04 fix: sync UI state only after promise resolves
  _play() {
    this.audio.play()
      .then(() => this._setPlaying(true))
      .catch(() => this._setPlaying(false));
  }

  _pause() {
    this.audio.pause();
    this._setPlaying(false);
  }

  _setPlaying(playing) {
    this.playBtn.textContent = playing ? "⏸" : "▶";
    this.playBtn.setAttribute("aria-label", playing ? "إيقاف مؤقت" : "تشغيل");
    this.waveform.classList.toggle("playing", playing);
  }

  _onTick() {
    if (!this.audio.duration) return;
    const pct = (this.audio.currentTime / this.audio.duration) * 100;
    this.progressFill.style.width = pct + "%";
    this.currentTimeEl.textContent = _fmt(this.audio.currentTime);
  }

  _onLoaded() { this.durationEl.textContent = _fmt(this.audio.duration); }

  _onEnded() {
    this._setPlaying(false);
    this.progressFill.style.width = "0%";
    this.currentTimeEl.textContent = "0:00";
  }

  _seek(e) {
    if (!this.audio.duration) return;
    const rect = this.progressTrack.getBoundingClientRect();
    const pct  = (e.clientX - rect.left) / rect.width;
    this.audio.currentTime = Math.max(0, Math.min(1, pct)) * this.audio.duration;
  }
}

function _fmt(s) {
  if (!s || isNaN(s)) return "0:00";
  const m   = Math.floor(s / 60);
  const sec = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}

/* ── Range sliders ───────────────────────────────────────────────────────── */
function initRanges() {
  [
    { id: "rate",   labelId: "rateVal" },
    { id: "volume", labelId: "volVal"  },
  ].forEach(({ id, labelId }) => {
    const input = document.getElementById(id);
    const label = document.getElementById(labelId);
    if (!input || !label) return;

    const update = () => {
      const v   = Number(input.value);
      label.textContent = `${v >= 0 ? "+" : ""}${v}%`;
      const min = Number(input.min);
      const max = Number(input.max);
      const pct = ((v - min) / (max - min)) * 100;
      input.style.background = `linear-gradient(to right, var(--violet) ${pct}%, rgba(255,255,255,.1) ${pct}%)`;
    };

    input.addEventListener("input", update);
    update();
  });
}

/* ── Char + Word counter — IDEA-20 ──────────────────────────────────────────── */
function initCharCounter() {
  const ta      = document.getElementById("text");
  const counter = document.getElementById("charCount");
  if (!ta || !counter) return;

  const update = () => {
    const chars = ta.value.length;
    const words = ta.value.trim() ? ta.value.trim().split(/\s+/).length : 0;
    counter.textContent = `${chars.toLocaleString("ar")} حرف · ${words.toLocaleString("ar")} كلمة / 5000`;
    counter.classList.toggle("warn", chars > 4500);
    // Auto-detect language and highlight matching voices — IDEA-18
    _highlightMatchingVoices(ta.value);
  };

  ta.addEventListener("input", update);
  update();
}

/* ── Language detection + voice highlighting — IDEA-18 ──────────────────── */
function _detectLang(text) {
  if (!text.trim()) return null;
  const arabicChars = (text.match(/[؀-ۿ]/g) || []).length;
  return arabicChars / text.length > 0.25 ? "ar" : "en";
}

function _highlightMatchingVoices(text) {
  const lang = _detectLang(text);
  if (!lang) return;
  const select = document.getElementById("voice");
  if (!select) return;

  [...select.options].forEach((opt) => {
    const matches = opt.value.startsWith(lang + "-") || opt.value === "";
    opt.style.fontWeight = matches ? "700" : "";
    opt.style.opacity    = matches ? "1" : "0.55";
  });

  // Suggest if current selection doesn't match detected language
  const current = select.value;
  if (current && !current.startsWith(lang + "-")) {
    const hint = document.getElementById("langHint");
    if (hint) {
      hint.textContent =
        lang === "ar"
          ? "💡 تم رصد نص عربي — يُقترح اختيار صوت عربي"
          : "💡 English text detected — consider an English voice";
      hint.style.display = "block";
    }
  } else {
    const hint = document.getElementById("langHint");
    if (hint) hint.style.display = "none";
  }
}

/* ── Voice loading with retry — IDEA-07 ─────────────────────────────────── */
async function loadVoices() {
  const select   = document.getElementById("voice");
  const retryBtn = document.getElementById("voiceRetryBtn");
  if (!select) return;

  if (retryBtn) retryBtn.style.display = "none";
  select.disabled = true;
  select.innerHTML = '<option disabled selected>⏳ جارٍ تحميل الأصوات…</option>';

  try {
    const voices = await apiRequest("/api/tts/voices");
    select.innerHTML = "";
    select.disabled  = false;

    const grouped = {};
    voices.forEach((v) => {
      const lang = v.locale.split("-")[0].toUpperCase();
      if (!grouped[lang]) grouped[lang] = [];
      grouped[lang].push(v);
    });

    Object.entries(grouped).forEach(([lang, list]) => {
      const grp = document.createElement("optgroup");
      grp.label = lang;
      list.forEach((v) => {
        const opt = document.createElement("option");
        opt.value = v.id;
        opt.textContent = `${v.name} · ${v.gender === "Female" ? "♀" : "♂"} · ${v.locale}`;
        grp.appendChild(opt);
      });
      select.appendChild(grp);
    });

    // Restore saved preference — IDEA-11
    const savedVoice = _loadPrefs().voice;
    if (savedVoice && [...select.options].some((o) => o.value === savedVoice)) {
      select.value = savedVoice;
    }
  } catch {
    select.innerHTML = '<option disabled selected>⚠️ فشل تحميل الأصوات</option>';
    if (retryBtn) retryBtn.style.display = "block";
    toast("تعذّر تحميل قائمة الأصوات", "error");
  }
}

/* ── Voice preview — IDEA-07 ─────────────────────────────────────────────── */
let previewPlayer = null;

async function previewVoice() {
  const voice = document.getElementById("voice")?.value;
  const text  = document.getElementById("text")?.value || "";
  if (!voice) { toast("اختر صوتاً أولاً", "error"); return; }

  const btn      = document.getElementById("previewBtn");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) { btn.disabled = true; btn.innerHTML = "⏳"; }

  try {
    // Refresh the access token if it's about to expire (raw fetch bypasses apiRequest)
    if (!isTokenFresh(60)) {
      const ok = await refreshAccessToken();
      if (!ok) { location.href = "/login"; return; }
    }

    const res = await fetch("/api/tts/preview", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${Auth.getToken()}`,
      },
      body: JSON.stringify({ voice, text: text.slice(0, 200) }),
    });

    if (!res.ok) {
      let msg = `فشل جلب المعاينة (${res.status})`;
      try { const d = await res.json(); if (d.detail) msg = d.detail; } catch {}
      throw new Error(msg);
    }

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);

    if (previewPlayer) { previewPlayer.pause(); URL.revokeObjectURL(previewPlayer.src); }
    previewPlayer = new Audio(url);
    previewPlayer.play().catch(() => {});
    toast("جارٍ تشغيل معاينة الصوت 🎧", "info", 3000);
  } catch (err) {
    toast(err.message || "فشلت المعاينة", "error");
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = origHtml; }
  }
}

/* ── Preferences — IDEA-11 ───────────────────────────────────────────────── */
function _loadPrefs() {
  try { return JSON.parse(localStorage.getItem(PREFS_KEY)) || {}; }
  catch { return {}; }
}

function _applyPrefs() {
  const p = _loadPrefs();
  if (p.rate   !== undefined) { const el = document.getElementById("rate");   if (el) el.value = p.rate; }
  if (p.volume !== undefined) { const el = document.getElementById("volume"); if (el) el.value = p.volume; }
}

function savePreferences() {
  const prefs = {
    voice:  document.getElementById("voice")?.value,
    rate:   document.getElementById("rate")?.value,
    volume: document.getElementById("volume")?.value,
  };
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  toast("تم حفظ التفضيلات ✅", "success", 2000);
}

/* ── SSML mode toggle — IDEA-25 ─────────────────────────────────────────── */
function toggleSSML() {
  const ta    = document.getElementById("text");
  const badge = document.getElementById("ssmlBadge");
  const isOn  = ta?.dataset.ssml === "true";
  if (!ta) return;
  ta.dataset.ssml = isOn ? "false" : "true";
  if (badge) badge.style.display = isOn ? "none" : "inline-flex";

  if (!isOn) {
    ta.placeholder = "<speak>\n  مرحباً <break time=\"500ms\"/> كيف حالك؟\n  <prosody rate=\"slow\">هذا النص بطيء.</prosody>\n</speak>";
    toast("وضع SSML مفعّل — ادخل XML مباشرةً", "info", 3000);
  } else {
    ta.placeholder = "اكتب أو الصق نصّك هنا…";
  }
}

/* ── Focus mode — IDEA-22 ───────────────────────────────────────────────── */
function toggleFocusMode() {
  document.body.classList.toggle("focus-mode");
  const btn    = document.getElementById("focusModeBtn");
  const active = document.body.classList.contains("focus-mode");
  if (btn) btn.textContent = active ? "🔲 عرض كامل" : "🎯 تركيز";
}

/* ── Drag & drop + file upload — IDEA-23, IDEA-08 ──────────────────────── */
function initDragDrop() {
  const ta = document.getElementById("text");
  if (!ta) return;

  const setDrag = (on) => ta.classList.toggle("drag-over", on);

  ta.addEventListener("dragover",  (e) => { e.preventDefault(); setDrag(true);  });
  ta.addEventListener("dragleave", ()  => setDrag(false));
  ta.addEventListener("drop", async (e) => {
    e.preventDefault();
    setDrag(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    if (!file.type.startsWith("text/") && !file.name.endsWith(".txt") && !file.name.endsWith(".md")) {
      toast("يُقبل ملفات .txt و .md فقط", "error");
      return;
    }
    ta.value = await file.text();
    ta.dispatchEvent(new Event("input"));
    toast(`تم تحميل: ${file.name}`, "success", 2500);
  });

  document.getElementById("fileUploadInput")?.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    ta.value = await file.text();
    ta.dispatchEvent(new Event("input"));
    toast(`تم تحميل: ${file.name}`, "success", 2500);
    e.target.value = "";  // reset so the same file can be re-selected
  });
}

/* ── Keyboard shortcuts — IDEA-19 ───────────────────────────────────────── */
function initKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    const ctrlOrMeta = e.ctrlKey || e.metaKey;

    // Ctrl+Enter → submit form
    if (ctrlOrMeta && e.key === "Enter") {
      e.preventDefault();
      document.getElementById("ttsForm")?.requestSubmit();
    }

    // Space on document body → play/pause player
    if (e.key === " " && e.target === document.body && player) {
      e.preventDefault();
      player.toggle();
    }

    // Ctrl+S → trigger download
    if (ctrlOrMeta && e.key === "s" && lastBlobUrl) {
      e.preventDefault();
      document.getElementById("downloadBtn")?.click();
    }

    // Escape → exit focus mode
    if (e.key === "Escape" && document.body.classList.contains("focus-mode")) {
      toggleFocusMode();
    }
  });
}

/* ── Synthesize ──────────────────────────────────────────────────────────── */
let lastBlobUrl = null;
let player      = null;

async function handleSynthesize(e) {
  e.preventDefault();

  const btn     = document.getElementById("synthBtn");
  const text    = document.getElementById("text").value.trim();
  const voice   = document.getElementById("voice").value;
  const rateRaw = document.getElementById("rate").value;
  const volRaw  = document.getElementById("volume").value;
  const ssml    = document.getElementById("text")?.dataset.ssml === "true";

  const rate   = `${Number(rateRaw) >= 0 ? "+" : ""}${rateRaw}%`;
  const volume = `${Number(volRaw)  >= 0 ? "+" : ""}${volRaw}%`;

  if (!text) { toast("الرجاء كتابة نص أولاً", "error"); return; }

  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"><span></span><span></span><span></span><span></span><span></span></span>&nbsp;جارٍ التحويل…`;

  // Show progress bar
  const progressBar = document.getElementById("synthProgress");
  if (progressBar) { progressBar.style.display = "block"; progressBar.value = 0; _animateProgress(progressBar, text.length); }

  try {
    const res = await fetch("/api/tts/synthesize", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${Auth.getToken()}`,
      },
      body: JSON.stringify({ text, voice, rate, volume, ssml }),
    });

    if (progressBar) { progressBar.style.display = "none"; clearTimeout(progressBar._timer); }

    if (!res.ok) {
      let msg = `فشل التحويل (${res.status})`;
      try { const d = await res.json(); if (d.detail) msg = d.detail; } catch {}
      if (res.status === 401) { Auth.clear(); location.href = "/login"; return; }
      throw new Error(msg);
    }

    const blob = await res.blob();
    if (lastBlobUrl) URL.revokeObjectURL(lastBlobUrl);
    lastBlobUrl = URL.createObjectURL(blob);

    // Show result panel with ARIA live announcement — IDEA-24
    const resultEl = document.getElementById("result");
    resultEl.classList.add("show");
    resultEl.setAttribute("aria-label", "الصوت جاهز للتشغيل");

    document.getElementById("downloadBtn").href = lastBlobUrl;

    player.load(lastBlobUrl);
    player.toggle();

    toast("تم إنشاء الصوت بنجاح 🎧", "success");
  } catch (err) {
    if (progressBar) progressBar.style.display = "none";
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = orig;
  }
}

// Simple progress animation (indeterminate feel based on text length)
function _animateProgress(bar, textLen) {
  const durationMs = Math.min(8000, Math.max(1500, textLen * 2));
  const start = performance.now();
  function step() {
    const elapsed = performance.now() - start;
    const pct = Math.min(90, (elapsed / durationMs) * 100);
    bar.value = pct;
    if (pct < 90) bar._timer = requestAnimationFrame(step);
  }
  step();
}

/* ── Share audio — IDEA-10 ───────────────────────────────────────────────── */
async function shareAudio() {
  const text    = document.getElementById("text")?.value.trim();
  const voice   = document.getElementById("voice")?.value;
  const rateRaw = document.getElementById("rate")?.value ?? "0";
  const volRaw  = document.getElementById("volume")?.value ?? "0";
  const ssml    = document.getElementById("text")?.dataset.ssml === "true";

  if (!text) { toast(i18n.t("error_no_text", "الرجاء كتابة نص أولاً"), "error"); return; }

  const rate   = `${Number(rateRaw) >= 0 ? "+" : ""}${rateRaw}%`;
  const volume = `${Number(volRaw)  >= 0 ? "+" : ""}${volRaw}%`;

  const btn   = document.getElementById("shareBtn");
  const panel = document.getElementById("sharePanel");
  const input = document.getElementById("shareUrlInput");
  const expEl = document.getElementById("shareExpiryNote");

  const origLabel = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"><span></span><span></span><span></span><span></span><span></span></span>`;

  // Show panel immediately with loading text
  panel.style.display = "block";
  input.value = i18n.t("share_creating", "جارٍ إنشاء الرابط…");
  if (expEl) expEl.textContent = "";

  try {
    const data = await apiRequest("/api/share", {
      method: "POST",
      auth: true,
      body: { text, voice, rate, volume, ssml },
    });

    // Build full URL with metadata query params for the share page
    const params = new URLSearchParams({
      v:   voice,
      t:   text.slice(0, 120),
      exp: Math.floor(new Date(data.expires_at).getTime() / 1000),
    });
    const shareUrl = `${location.origin}/s/${data.uuid}?${params}`;
    input.value = shareUrl;

    if (expEl) {
      const lang   = localStorage.getItem("vf_lang") || "ar";
      const locale = lang === "ar" ? "ar-SA" : "en-US";
      const d = new Date(data.expires_at).toLocaleString(locale);
      expEl.textContent = lang === "ar"
        ? `ينتهي الرابط في ${d}`
        : `Expires ${d}`;
    }

    toast(i18n.t("share_copied", "تم إنشاء الرابط!"), "success", 2500);
  } catch (err) {
    panel.style.display = "none";
    toast(err.message || "فشل إنشاء رابط المشاركة", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = origLabel;
  }
}

function _copyShareUrl() {
  const input = document.getElementById("shareUrlInput");
  if (!input?.value) return;
  navigator.clipboard.writeText(input.value).then(() => {
    toast(i18n.t("share_copied", "تم نسخ الرابط!"), "success", 2000);
  }).catch(() => {
    input.select();
    document.execCommand("copy");
    toast(i18n.t("share_copied", "تم نسخ الرابط!"), "success", 2000);
  });
}

/* ── Boot ────────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.isLoggedIn()) { location.href = "/login"; return; }

  // Show username
  const user = Auth.getUser();
  const nameEl = document.getElementById("userChipName");
  if (nameEl && user) nameEl.textContent = user.username;

  // Logout
  document.getElementById("logoutBtn")?.addEventListener("click", () => {
    Auth.clear();
    location.href = "/login";
  });

  // Verify JWT — skip round-trip if token is fresh
  if (!isTokenFresh()) {
    try {
      await apiRequest("/api/auth/me", { auth: true });
    } catch {
      Auth.clear();
      location.href = "/login";
      return;
    }
  }

  // Init UI modules
  _applyPrefs();
  initCharCounter();
  initRanges();
  initDragDrop();
  initKeyboardShortcuts();

  // Re-run range update after prefs applied (values may have changed)
  initRanges();

  await loadVoices();

  player = new AudioPlayer();

  document.getElementById("ttsForm").addEventListener("submit", handleSynthesize);

  // Buttons previously using inline onclick attributes
  document.getElementById("previewBtn")?.addEventListener("click", previewVoice);
  document.getElementById("ssmlToggleBtn")?.addEventListener("click", toggleSSML);

  // Save-prefs button
  document.getElementById("savePrefsBtn")?.addEventListener("click", savePreferences);

  // Keyboard shortcuts hint
  document.getElementById("shortcutsHint")?.addEventListener("click", () => {
    toast("⌨️  Ctrl+Enter = تحويل  ·  Space = تشغيل/إيقاف  ·  Ctrl+S = تحميل  ·  Esc = خروج التركيز", "info", 5000);
  });

  // Share button — IDEA-10
  document.getElementById("shareBtn")?.addEventListener("click", shareAudio);

  // Copy share URL button
  document.getElementById("shareCopyBtn")?.addEventListener("click", _copyShareUrl);
});
