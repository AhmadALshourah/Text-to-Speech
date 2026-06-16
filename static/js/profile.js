const MONTHLY_LIMIT = 500_000;

document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.isLoggedIn()) { location.href = "/login"; return; }

  document.getElementById("logoutBtn")?.addEventListener("click", () => {
    Auth.clear(); location.href = "/login";
  });

  await loadProfile();

  document.getElementById("passwordForm")
    .addEventListener("submit", handlePasswordChange);

  document.getElementById("deleteAccountBtn")
    .addEventListener("click", handleDeleteAccount);
});

async function loadProfile() {
  try {
    const p      = await apiRequest("/api/auth/profile", { auth: true });
    const lang   = localStorage.getItem("vf_lang") || "ar";
    const locale = lang === "ar" ? "ar-SA" : "en-US";

    document.getElementById("avatarCircle").textContent =
      p.username.slice(0, 2).toUpperCase();
    document.getElementById("profileUsername").textContent = p.username;
    document.getElementById("profileEmail").textContent    = p.email;

    const joined = new Date(p.created_at).toLocaleDateString(locale, {
      year: "numeric", month: "long", day: "numeric",
    });
    document.getElementById("profileJoined").textContent =
      lang === "ar" ? `انضم في ${joined}` : `Joined ${joined}`;

    document.getElementById("statTotal").textContent =
      p.total_conversions.toLocaleString(locale);
    document.getElementById("statChars").textContent =
      p.monthly_chars_used.toLocaleString(locale);

    const pct = Math.min(100, (p.monthly_chars_used / MONTHLY_LIMIT) * 100).toFixed(1);
    document.getElementById("statQuota").textContent  = pct + "%";
    document.getElementById("quotaText").textContent  =
      `${p.monthly_chars_used.toLocaleString(locale)} / ${MONTHLY_LIMIT.toLocaleString(locale)}`;
    document.getElementById("quotaFill").style.width      = pct + "%";
    document.getElementById("quotaFill").style.background =
      pct > 80 ? "var(--danger)" : pct > 60 ? "#f59e0b" : "var(--accent)";

    document.getElementById("profileCard").style.display = "block";
  } catch (err) {
    toast(err.message || "فشل تحميل الملف الشخصي", "error");
  }
}

async function handlePasswordChange(e) {
  e.preventDefault();
  const btn     = document.getElementById("savePwdBtn");
  const current = document.getElementById("currentPwd").value;
  const newPwd  = document.getElementById("newPwd").value;
  const confirm = document.getElementById("confirmPwd").value;

  if (newPwd !== confirm) {
    toast("كلمتا المرور الجديدتان غير متطابقتين", "error");
    return;
  }
  if (newPwd.length < 6) {
    toast("كلمة المرور يجب أن تكون 6 أحرف على الأقل", "error");
    return;
  }

  const orig = btn.innerHTML;
  btn.disabled  = true;
  btn.innerHTML = `<span class="spinner"><span></span><span></span><span></span><span></span><span></span></span>&nbsp;جارٍ الحفظ…`;

  try {
    await apiRequest("/api/auth/password", {
      method: "PATCH",
      auth: true,
      body: { current_password: current, new_password: newPwd },
    });
    toast("تم تحديث كلمة المرور بنجاح", "success");
    e.target.reset();
  } catch (err) {
    toast(err.message || "فشل تحديث كلمة المرور", "error");
  } finally {
    btn.disabled  = false;
    btn.innerHTML = orig;
  }
}

async function handleDeleteAccount() {
  if (!window.confirm(
    "هل أنت متأكد تماماً؟\n\nسيتم حذف حسابك وجميع بياناتك بشكل نهائي ولا يمكن التراجع."
  )) return;

  try {
    await apiRequest("/api/auth/account", { method: "DELETE", auth: true });
    Auth.clear();
    toast("تم حذف حسابك. وداعاً", "info", 3000);
    setTimeout(() => (location.href = "/register"), 2000);
  } catch (err) {
    toast(err.message || "فشل حذف الحساب", "error");
  }
}
