# Project Phases — Text-to-Speech Web Application

تحويل سكربت Python بسيط إلى تطبيق ويب متكامل لتحويل النص إلى كلام، مع نظام
مصادقة (تسجيل دخول / إنشاء حساب)، واجهة وتصميم عصري، وبنية برمجية منظمة.

**Stack:** FastAPI · HTML/CSS/JS · edge-tts (free) · SQLite · SQLAlchemy · JWT (bcrypt)

---

## الحالة العامة (Status Legend)
- ✅ مكتمل (Done)
- 🔄 قيد التنفيذ (In Progress)
- ⬜ لم يبدأ (Pending)

---

## Phase 0 — تهيئة المشروع والنظافة (Cleanup & Setup) ✅
- [x] إنشاء `.gitignore` (يتجاهل `.venv/`, `.env`, `*.db`, `audio_output/`, `__pycache__/`, `*.mp3`).
- [x] إنشاء `requirements.txt` بالاعتمادات المتوافقة مع Python 3.14.
- [x] إنشاء `.env.example` (يحوي `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `DATABASE_URL`).
- [x] إنشاء هيكل المجلدات (`app/`, `static/`, `templates/`) وملفات `__init__.py`.

## Phase 1 — تحسين الكود الأساسي ونقله إلى Class (Core Refactor) ✅
- [x] استبدال محرك OpenAI بمحرك `edge-tts` المجاني داخل `class TTSService`.
- [x] تصحيح الأخطاء الإملائية + إضافة type hints ومعالجة أخطاء.
- [x] `TTSService.synthesize(...)` و `TTSService.list_voices()`.

## Phase 2 — طبقة قاعدة البيانات (Database Layer) ✅
- [x] `app/database.py`: SQLAlchemy engine لـ SQLite + `SessionLocal` + `Base`.
- [x] `app/models/user.py`: `class User`.
- [x] إنشاء الجداول تلقائياً عند الإقلاع.

## Phase 3 — طبقة الأمان والمصادقة (Auth & Security) ✅
- [x] `app/core/security.py`: `class SecurityManager` (bcrypt + JWT).
- [x] `app/schemas/`: مخططات Pydantic (User + TTS).
- [x] `app/services/auth_service.py`: `class AuthService`.
- [x] `app/dependencies.py`: `get_db`, `get_current_user`.

## Phase 4 — مسارات الـ API (API Routers) ✅
- [x] `routers/auth.py`: register / login / me.
- [x] `routers/tts.py`: voices / synthesize (محمي بـ JWT).
- [x] `main.py`: تجميع التطبيق + CORS + تقديم static/templates.

## Phase 5 — الواجهة الأمامية HTML (Frontend Structure) ✅
- [x] `login.html`, `register.html`, `index.html`.
- [x] `js/api.js`, `js/auth.js`, `js/app.js`.
- [x] حماية الصفحة الرئيسية وإعادة التوجيه.

## Phase 6 — التصميم وتجربة المستخدم (UI/UX & Design) ✅
- [x] `css/styles.css`: نظام تصميم كامل + متغيرات + responsive.
- [x] وضع داكن/فاتح + رسائل (toasts) + حالات تحميل + انتقالات.

## Phase 7 — التوثيق واللمسات النهائية (Docs & Polish) ✅
- [x] `README.md` بخطوات التثبيت والتشغيل.
- [x] مراجعة نهائية واختبار شامل end-to-end.

---

## كيفية التشغيل (How to Run)
```bash
# 1) تفعيل البيئة الافتراضية وتثبيت الاعتمادات
.venv\Scripts\activate
pip install -r requirements.txt

# 2) إنشاء ملف .env من النموذج وتعبئة SECRET_KEY
copy .env.example .env

# 3) تشغيل الخادم
uvicorn main:app --reload

# 4) فتح المتصفح
#   http://127.0.0.1:8000        ← التطبيق
#   http://127.0.0.1:8000/docs   ← توثيق API (Swagger)
```
