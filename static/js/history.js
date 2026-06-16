let currentPage = 1;
const PER_PAGE  = 20;

document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.isLoggedIn()) { location.href = "/login"; return; }

  document.getElementById("logoutBtn")?.addEventListener("click", () => {
    Auth.clear(); location.href = "/login";
  });

  document.getElementById("prevBtn")?.addEventListener("click", () => changePage(-1));
  document.getElementById("nextBtn")?.addEventListener("click", () => changePage(1));

  // Event delegation for dynamically-created delete buttons
  document.getElementById("historyBody")?.addEventListener("click", async (e) => {
    const btn = e.target.closest(".del-btn");
    if (!btn) return;
    await deleteEntry(Number(btn.dataset.id), btn);
  });

  await loadHistory();
});

async function loadHistory() {
  document.getElementById("loadingState").style.display     = "flex";
  document.getElementById("historyTableWrap").style.display = "none";
  document.getElementById("emptyState").style.display       = "none";
  document.getElementById("pagination").style.display       = "none";

  try {
    const data  = await apiRequest(
      `/api/history?page=${currentPage}&per_page=${PER_PAGE}`,
      { auth: true },
    );
    const rows  = data.items;
    const total = data.total;
    const pages = data.pages;

    document.getElementById("loadingState").style.display = "none";

    if (!rows.length && currentPage === 1) {
      document.getElementById("emptyState").style.display = "flex";
      return;
    }

    renderRows(rows);
    document.getElementById("historyTableWrap").style.display = "block";

    if (pages > 1) {
      document.getElementById("pagination").style.display = "flex";
    }

    document.getElementById("prevBtn").disabled = currentPage === 1;
    document.getElementById("nextBtn").disabled = currentPage >= pages;

    const lang   = localStorage.getItem("vf_lang") || "ar";
    const locale = lang === "ar" ? "ar-SA" : "en-US";
    document.getElementById("pageInfo").textContent = lang === "ar"
      ? `الصفحة ${currentPage} من ${pages} (${total.toLocaleString(locale)} تحويل)`
      : `Page ${currentPage} of ${pages} (${total.toLocaleString(locale)} items)`;

  } catch (err) {
    document.getElementById("loadingState").style.display = "none";
    toast(err.message || "فشل تحميل السجل", "error");
  }
}

function renderRows(rows) {
  const tbody  = document.getElementById("historyBody");
  tbody.innerHTML = "";
  const lang   = localStorage.getItem("vf_lang") || "ar";
  const locale = lang === "ar" ? "ar-SA" : "en-US";

  rows.forEach((r) => {
    const tr      = document.createElement("tr");
    const preview = r.text_preview
      ? (r.text_preview.length > 60 ? r.text_preview.slice(0, 60) + "…" : r.text_preview)
      : "—";
    const date = new Date(r.created_at).toLocaleString(locale, {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });

    tr.innerHTML = `
      <td class="hist-text" title="${escHtml(r.text_preview || '')}">${escHtml(preview)}</td>
      <td><span class="voice-badge">${escHtml(r.voice.split("-").slice(2).join(" "))}</span></td>
      <td class="hist-settings">${r.rate} · ${r.volume}</td>
      <td class="hist-date">${date}</td>
      <td>
        <button class="btn btn-ghost btn-sm del-btn" title="حذف هذا السجل"
                data-id="${r.id}">🗑️</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function deleteEntry(id, btn) {
  btn.disabled = true;
  try {
    await apiRequest(`/api/history/${id}`, { method: "DELETE", auth: true });
    btn.closest("tr").remove();
    toast("تم حذف السجل", "info", 2000);
  } catch (err) {
    btn.disabled = false;
    toast(err.message || "فشل الحذف", "error");
  }
}

function changePage(delta) {
  currentPage = Math.max(1, currentPage + delta);
  loadHistory();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
