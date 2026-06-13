# Issues — VoiceForge Application

All issues found during a full code audit. Severity: 🔴 Critical → 🟠 High → 🟡 Medium → 🔵 Low.

---

## 🔴 Critical

### ISS-01 — Audio files accumulate on disk (disk leak)
**File:** `app/routers/tts.py`  
Every call to `/api/tts/synthesize` writes a UUID-named `.mp3` file to `audio_output/` and **never deletes it**. `FileResponse` streams it to the client and returns, leaving the file permanently on disk. A moderately active instance fills storage indefinitely.  
**Fix:** Pass a `BackgroundTask(filepath.unlink, missing_ok=True)` to `FileResponse` so the file is deleted after streaming completes. ✅ Fixed

### ISS-02 — XSS vulnerability in toast notifications
**File:** `static/js/api.js` — `toast()` function  
The message is interpolated directly into `el.innerHTML`:
```js
el.innerHTML = `…<span style="flex:1">${message}</span>…`;
```
`message` often comes from `data.detail` in API error responses. A server returning `<img src=x onerror=alert(1)>` in `detail` would execute arbitrary JS in the user's browser.  
**Fix:** Build the toast element with `document.createElement` and assign `message` via `.textContent`. ✅ Fixed

---

## 🟠 High

### ISS-03 — CORS: `allow_origins=["*"]` + `allow_credentials=True` is invalid
**File:** `main.py`  
The CORS spec (and all major browsers) **reject** `Access-Control-Allow-Origin: *` when `Access-Control-Allow-Credentials: true` is also set. The combination produces a CORS error for any cross-origin credentialed request. Since the frontend is served from the same FastAPI process (same origin), `allow_credentials=True` is not needed at all.  
**Fix:** Remove `allow_credentials=True` from `CORSMiddleware`. ✅ Fixed

### ISS-04 — AudioPlayer shows wrong state when autoplay is blocked
**File:** `static/js/app.js` — `AudioPlayer._play()`  
```js
_play() {
  this.audio.play().catch(() => {});   // ← error silently swallowed
  this._setPlaying(true);              // ← UI set to playing BEFORE promise resolves
}
```
`audio.play()` returns a Promise. If the browser blocks autoplay (autoplay policy), the Promise rejects, the `.catch` discards it, but the UI already shows ⏸ and the waveform animates — with no audio playing.  
**Fix:** Set playing state inside `.then()` / `.catch()` callbacks so it always matches reality. ✅ Fixed

---

## 🟡 Medium

### ISS-05 — Rate/volume accept any arbitrary string (no format validation)
**File:** `app/schemas/tts.py`  
`rate` and `volume` fields default to `"+0%"` but accept any string with no validation. A client can send `"not-a-rate"` or `"100"`, which edge-tts will reject with an opaque internal error instead of a clean 422.  
**Fix:** Add a `field_validator` with a regex `^[+-]\d{1,3}%$`. ✅ Fixed

### ISS-06 — Insecure default `SECRET_KEY` — app silently runs in unsafe mode
**File:** `app/config.py`  
If `.env` is absent or doesn't define `SECRET_KEY`, the app runs with `"dev-only-insecure-secret-change-me"`. JWTs signed with this key are predictable to anyone who reads the source. There is no warning.  
**Fix:** Log a prominent `WARNING` at startup when the default key is detected. ✅ Fixed

### ISS-07 — No retry when voice list fails to load
**File:** `static/js/app.js` — `loadVoices()`  
When the request to `/api/tts/voices` fails, the select element is left showing `⏳ جارٍ تحميل…` (loading) with no way for the user to recover without refreshing the whole page.  
**Fix:** Show an error option in the select and reveal a hidden "إعادة المحاولة" button. ✅ Fixed

### ISS-08 — Unnecessary `/api/auth/me` round-trip on every page load
**File:** `static/js/app.js` — boot section  
Every workspace page load fires a network request solely to check if the JWT is still valid. Since the payload (including `exp`) is base64-readable client-side, expiry can be checked locally with zero latency — the server call is only needed for tokens that are already expired.  
**Fix:** Add `isTokenFresh()` to `api.js`; skip the `/me` call when the token is still fresh. ✅ Fixed

---

## 🔵 Low

### ISS-09 — Dead / misleading comment in `app.js`
**File:** `static/js/app.js` line 103  
```js
// Warn state on char count (reused logic below, not related)
```
This comment appears inside `initRanges()` and refers to nothing — it is a leftover from a previous edit.  
**Fix:** Remove the comment. ✅ Fixed

### ISS-10 — Implicit string-to-number coercion for rate/volume sign check
**File:** `static/js/app.js` — `handleSynthesize()`  
```js
const rate = `${rateRaw >= 0 ? "+" : ""}${rateRaw}%`;
```
`rateRaw` is a string (from `input.value`). The comparison `"10" >= 0` works due to JS type coercion, but it is fragile and unclear.  
**Fix:** Wrap with `Number()`: `Number(rateRaw) >= 0`. ✅ Fixed

### ISS-11 — Auth pages have no theme toggle
**Files:** `templates/login.html`, `templates/register.html`  
`api.js` wires the theme toggle to `#themeToggle`, which does not exist on auth pages. The saved theme is still applied, but users cannot switch it without navigating to the workspace first.  
**Fix:** Add a small floating theme toggle button to both auth pages. ✅ Fixed

### ISS-12 — Toast dismiss animation direction wrong in RTL
**File:** `static/js/api.js` — `toast()` close handler  
```js
el.style.transform = "translateX(20px)"; // always slides right
```
In RTL layout, toasts stack on the left side. The dismiss slide should go left (`translateX(-20px)`) not right.  
**Fix:** Derive the direction from `document.documentElement.dir`. ✅ Fixed

---

## Summary

| ID | Severity | File(s) | Status |
|----|----------|---------|--------|
| ISS-01 | 🔴 Critical | `app/routers/tts.py` | ✅ Fixed |
| ISS-02 | 🔴 Critical | `static/js/api.js` | ✅ Fixed |
| ISS-03 | 🟠 High | `main.py` | ✅ Fixed |
| ISS-04 | 🟠 High | `static/js/app.js` | ✅ Fixed |
| ISS-05 | 🟡 Medium | `app/schemas/tts.py` | ✅ Fixed |
| ISS-06 | 🟡 Medium | `app/config.py` / `main.py` | ✅ Fixed |
| ISS-07 | 🟡 Medium | `static/js/app.js`, `templates/index.html` | ✅ Fixed |
| ISS-08 | 🟡 Medium | `static/js/api.js`, `static/js/app.js` | ✅ Fixed |
| ISS-09 | 🔵 Low | `static/js/app.js` | ✅ Fixed |
| ISS-10 | 🔵 Low | `static/js/app.js` | ✅ Fixed |
| ISS-11 | 🔵 Low | `templates/login.html`, `templates/register.html` | ✅ Fixed |
| ISS-12 | 🔵 Low | `static/js/api.js` | ✅ Fixed |
