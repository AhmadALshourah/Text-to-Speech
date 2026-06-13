/* =========================================================================
   auth.js — Login and Register page logic.
   ========================================================================= */

document.addEventListener("DOMContentLoaded", () => {
  if (Auth.isLoggedIn()) { location.href = "/"; return; }

  document.getElementById("loginForm")   ?.addEventListener("submit", handleLogin);
  document.getElementById("registerForm")?.addEventListener("submit", handleRegister);
});

/* ── Loading state helpers ───────────────────────────────────────────────── */
function setBtnLoading(btn, loading, label) {
  if (loading) {
    btn.disabled     = true;
    btn.dataset.orig = btn.innerHTML;
    btn.innerHTML    = `<span class="spinner"><span></span><span></span><span></span><span></span><span></span></span>&nbsp;${label}`;
  } else {
    btn.disabled  = false;
    btn.innerHTML = btn.dataset.orig || label;
  }
}

/* ── Login ───────────────────────────────────────────────────────────────── */
async function handleLogin(e) {
  e.preventDefault();
  const btn      = e.target.querySelector("button[type=submit]");
  const email    = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  setBtnLoading(btn, true, "جارٍ التحقق…");

  try {
    const data = await apiRequest("/api/auth/login", {
      method: "POST",
      body: { email, password },
    });
    Auth.setSession(data.access_token, data.user);
    toast("مرحباً بك مجدداً 👋", "success");
    setTimeout(() => (location.href = "/"), 700);
  } catch (err) {
    toast(err.message, "error");
    setBtnLoading(btn, false, "تسجيل الدخول");
  }
}

/* ── Register ────────────────────────────────────────────────────────────── */
async function handleRegister(e) {
  e.preventDefault();
  const btn      = e.target.querySelector("button[type=submit]");
  const username = document.getElementById("username").value.trim();
  const email    = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const confirm  = document.getElementById("confirm").value;

  if (password !== confirm) {
    toast("كلمتا المرور غير متطابقتين", "error");
    return;
  }
  if (password.length < 6) {
    toast("كلمة المرور يجب أن تكون 6 أحرف على الأقل", "error");
    return;
  }

  setBtnLoading(btn, true, "جارٍ الإنشاء…");

  try {
    const data = await apiRequest("/api/auth/register", {
      method: "POST",
      body: { username, email, password },
    });
    Auth.setSession(data.access_token, data.user);
    toast("تم إنشاء حسابك بنجاح ✨", "success");
    setTimeout(() => (location.href = "/"), 700);
  } catch (err) {
    toast(err.message, "error");
    setBtnLoading(btn, false, "إنشاء الحساب");
  }
}
