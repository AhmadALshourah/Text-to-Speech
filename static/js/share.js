document.addEventListener("DOMContentLoaded", async () => {
  const uuid     = location.pathname.split("/s/")[1];
  const audioUrl = `/api/share/${uuid}/audio`;

  try {
    const probe = await fetch(audioUrl, { method: "HEAD" });
    if (probe.status === 404) { show("notFoundState"); return; }
    if (probe.status === 410) { show("expiredState");  return; }
    if (!probe.ok)            { show("notFoundState"); return; }
  } catch {
    show("notFoundState");
    return;
  }

  show("playerState");

  const audio = document.getElementById("audioEl");
  audio.src   = audioUrl;

  const params     = new URLSearchParams(location.search);
  const voiceParam = params.get("v") || "";
  if (voiceParam) {
    document.getElementById("shareVoiceLabel").textContent = `🎤 ${voiceParam}`;
  }

  const previewEl = document.getElementById("shareTextPreview");
  const textParam = params.get("t") || "";
  if (textParam) {
    previewEl.textContent = decodeURIComponent(textParam);
  } else {
    previewEl.style.display = "none";
  }

  const expParam  = params.get("exp") || "";
  if (expParam) {
    const d        = new Date(parseInt(expParam) * 1000);
    const expiryEl = document.getElementById("expiryNote");
    const lang     = localStorage.getItem("vf_lang") || "ar";
    expiryEl.textContent = lang === "ar"
      ? `ينتهي هذا الرابط في ${d.toLocaleString("ar-SA")}`
      : `This link expires on ${d.toLocaleString("en-US")}`;
  }

  document.getElementById("downloadBtn").href = audioUrl;
  initSharePlayer();
});

function show(id) {
  document.getElementById("loadingState").style.display = "none";
  document.getElementById(id).style.display = "flex";
}

function initSharePlayer() {
  const audio      = document.getElementById("audioEl");
  const playBtn    = document.getElementById("playBtn");
  const fill       = document.getElementById("progressFill");
  const track      = document.getElementById("progressTrack");
  const currentEl  = document.getElementById("currentTime");
  const durationEl = document.getElementById("duration");
  const waveform   = document.getElementById("waveform");

  const fmt = (s) =>
    `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  playBtn.addEventListener("click", () => {
    if (audio.paused) {
      audio.play().then(() => {
        playBtn.textContent = "⏸";
        waveform.classList.add("playing");
      }).catch(() => {});
    } else {
      audio.pause();
      playBtn.textContent = "▶";
      waveform.classList.remove("playing");
    }
  });

  audio.addEventListener("timeupdate", () => {
    if (!audio.duration) return;
    fill.style.width      = (audio.currentTime / audio.duration) * 100 + "%";
    currentEl.textContent = fmt(audio.currentTime);
  });

  audio.addEventListener("loadedmetadata", () => {
    durationEl.textContent = fmt(audio.duration);
  });

  audio.addEventListener("ended", () => {
    playBtn.textContent = "▶";
    waveform.classList.remove("playing");
    fill.style.width = "0%";
  });

  track.addEventListener("click", (e) => {
    const rect = track.getBoundingClientRect();
    audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
  });
}
