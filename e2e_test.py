"""End-to-end smoke test — uses httpx (handles gzip automatically)."""
import sys
import time
import httpx

# Force UTF-8 output so Arabic voice names print correctly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8002"
c = httpx.Client(base_url=BASE, timeout=30)

def banner(msg): print(f"\n{'='*60}\n{msg}\n{'='*60}")
def ok(msg):     print(f"  [OK]  {msg}")
def fail(msg):   print(f"  [FAIL]  {msg}"); sys.exit(1)

# ── 1. Health ─────────────────────────────────────────────────────────────────
banner("1. Health check")
r = c.get("/health")
assert r.status_code == 200, f"health {r.status_code}: {r.text}"
data = r.json()
assert data["db"] == "ok", f"DB not ok: {data}"
ok(f"health: {data['status']} | db: {data['db']}")

# ── 2. Register ───────────────────────────────────────────────────────────────
banner("2. Register new user")
ts = int(time.time())
email = f"test_{ts}@example.com"
reg = c.post("/api/auth/register", json={
    "username": f"testuser_{ts}",
    "email":    email,
    "password": "TestPass123!",
})
assert reg.status_code == 201, f"register {reg.status_code}: {reg.text}"
token = reg.json()["access_token"]
ok(f"registered — token length: {len(token)}")

# ── 3. Duplicate register ─────────────────────────────────────────────────────
banner("3. Duplicate register -> 409")
dup = c.post("/api/auth/register", json={
    "username": f"testuser_{ts}_2",
    "email":    email,
    "password": "TestPass123!",
})
assert dup.status_code == 409, f"expected 409 got {dup.status_code}: {dup.text}"
ok("duplicate email rejected correctly")

# ── 4. Login ──────────────────────────────────────────────────────────────────
banner("4. Login")
login = c.post("/api/auth/login", json={
    "email":    email,
    "password": "TestPass123!",
})
assert login.status_code == 200, f"login {login.status_code}: {login.text}"
token2 = login.json()["access_token"]
ok(f"login OK — token length: {len(token2)}")

# ── 5. Wrong password -> account lockout ──────────────────────────────────────
banner("5. Wrong password (increments lockout counter)")
bad = c.post("/api/auth/login", json={"email": email, "password": "WRONG"})
assert bad.status_code in (401, 423), f"expected 401/423 got {bad.status_code}"
ok(f"bad password -> {bad.status_code}")

# ── 6. /me endpoint ───────────────────────────────────────────────────────────
banner("6. GET /api/auth/me")
me = c.get("/api/auth/me", headers={"Authorization": f"Bearer {token2}"})
assert me.status_code == 200, f"/me {me.status_code}: {me.text}"
user_data = me.json()
assert "email" in user_data, f"/me missing email: {user_data}"
ok(f"me: {user_data['username']} <{user_data['email']}>")

# ── 7. Voices ─────────────────────────────────────────────────────────────────
banner("7. GET /api/tts/voices")
voices = c.get("/api/tts/voices", headers={"Authorization": f"Bearer {token2}"})
assert voices.status_code == 200, f"voices {voices.status_code}: {voices.text}"
vlist = voices.json()
assert len(vlist) > 0, "voice list empty"
ok(f"voices: {len(vlist)} returned")
# pick Arabic voice
ar_voice = next((v["id"] for v in vlist if "ar" in v.get("locale","").lower()), vlist[0]["id"])
ok(f"using voice id: {ar_voice}")

# ── 8. Voice preview ──────────────────────────────────────────────────────────
banner("8. POST /api/tts/preview")
prev = c.post("/api/tts/preview",
    json={"voice": ar_voice, "text": "مرحبا"},
    headers={"Authorization": f"Bearer {token2}"},
)
assert prev.status_code == 200, f"preview {prev.status_code}: {prev.text}"
assert prev.headers.get("content-type","").startswith("audio/"), f"wrong content-type: {prev.headers.get('content-type')}"
ok(f"preview returned {len(prev.content)} bytes of audio")

# ── 9. Synthesize ─────────────────────────────────────────────────────────────
banner("9. POST /api/tts/synthesize")
synth = c.post("/api/tts/synthesize",
    json={"text": "مرحبا بك في تطبيق تحويل النص إلى كلام.", "voice": ar_voice, "rate": "+0%", "volume": "+0%"},
    headers={"Authorization": f"Bearer {token2}"},
    timeout=60,
)
assert synth.status_code == 200, f"synthesize {synth.status_code}: {synth.text}"
assert synth.headers.get("content-type","").startswith("audio/"), f"wrong content-type: {synth.headers.get('content-type')}"
ok(f"synthesize returned {len(synth.content)} bytes of audio")

# ── 10. History ───────────────────────────────────────────────────────────────
banner("10. GET /api/history")
hist = c.get("/api/history", headers={"Authorization": f"Bearer {token2}"})
assert hist.status_code == 200, f"history {hist.status_code}: {hist.text}"
hdata = hist.json()
assert "items" in hdata, f"missing items key: {hdata}"
ok(f"history: {hdata['total']} item(s), page {hdata['page']}/{hdata['pages']}")

# ── 11. Profile ───────────────────────────────────────────────────────────────
banner("11. GET /api/auth/profile")
profile = c.get("/api/auth/profile", headers={"Authorization": f"Bearer {token2}"})
assert profile.status_code == 200, f"profile {profile.status_code}: {profile.text}"
pdata = profile.json()
assert "monthly_chars_used" in pdata, f"missing quota field: {pdata}"
ok(f"profile: {pdata['total_conversions']} conversions, {pdata['monthly_chars_used']} chars used")

# ── 12. Change password ───────────────────────────────────────────────────────
banner("12. PATCH /api/auth/password")
chpw = c.patch("/api/auth/password",
    json={"current_password": "TestPass123!", "new_password": "NewPass456!"},
    headers={"Authorization": f"Bearer {token2}"},
)
assert chpw.status_code == 204, f"change-password {chpw.status_code}: {chpw.text}"
ok("password changed")

# verify new password works
login3 = c.post("/api/auth/login", json={"email": email, "password": "NewPass456!"})
assert login3.status_code == 200, f"login with new pw {login3.status_code}: {login3.text}"
token3 = login3.json()["access_token"]
ok("login with new password works")

# ── 13. Delete history item ───────────────────────────────────────────────────
banner("13. DELETE /api/history/{id}")
hist2 = c.get("/api/history", headers={"Authorization": f"Bearer {token3}"})
items = hist2.json().get("items", [])
if items:
    conv_id = items[0]["id"]
    del_r = c.delete(f"/api/history/{conv_id}", headers={"Authorization": f"Bearer {token3}"})
    assert del_r.status_code == 204, f"delete history {del_r.status_code}: {del_r.text}"
    ok(f"deleted conversion #{conv_id}")
else:
    ok("no history items to delete (skipped)")

# ── 14. Delete account ────────────────────────────────────────────────────────
banner("14. DELETE /api/auth/account")
del_acc = c.delete("/api/auth/account", headers={"Authorization": f"Bearer {token3}"})
assert del_acc.status_code == 204, f"delete account {del_acc.status_code}: {del_acc.text}"
ok("account deleted")

# verify deleted account can't login
gone = c.post("/api/auth/login", json={"email": email, "password": "NewPass456!"})
assert gone.status_code in (401, 404), f"expected 401/404 got {gone.status_code}"
ok(f"deleted account login blocked -> {gone.status_code}")

# ── Done ──────────────────────────────────────────────────────────────────────
banner("ALL TESTS PASSED")
c.close()
