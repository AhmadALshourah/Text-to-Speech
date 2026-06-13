# 🔊 Text-to-Speech Web Application

تطبيق ويب متكامل لتحويل النص إلى كلام طبيعي، مبني بـ **FastAPI** و **edge-tts**
المجاني، مع نظام مصادقة كامل (تسجيل دخول / إنشاء حساب) وواجهة عصرية متجاوبة.

A full-stack Text-to-Speech web app with user authentication, a modern
responsive UI (light/dark theme), and free high-quality speech synthesis.

---

## ✨ المميزات (Features)

- 🎙️ **تحويل نص إلى كلام** بجودة عالية عبر محرك Microsoft `edge-tts` (مجاني، بدون مفتاح API).
- 🌍 **أصوات ولغات متعددة** — العربية، الإنجليزية، الفرنسية، الإسبانية، الألمانية.
- 🎚️ **تحكم بالسرعة ومستوى الصوت**.
- 🔐 **مصادقة آمنة** — تسجيل دخول وإنشاء حساب، كلمات مرور مُجزّأة بـ bcrypt و JWT.
- 🎨 **تصميم عصري متجاوب** مع وضع داكن/فاتح ودعم كامل للعربية (RTL).
- ⬇️ **تشغيل وتحميل** الملف الصوتي مباشرةً من المتصفح.
- 📚 **توثيق API تلقائي** عبر Swagger على `/docs`.

---

## 🏗️ البنية (Architecture)

```
app/
├── config.py          إعدادات التطبيق (Settings)
├── database.py        إعداد SQLAlchemy + SQLite
├── dependencies.py    get_db / get_current_user (حماية JWT)
├── models/user.py     نموذج المستخدم (ORM)
├── schemas/           مخططات Pydantic (user, tts)
├── core/security.py   SecurityManager (bcrypt + JWT)
├── services/          AuthService + TTSService (edge-tts)
└── routers/           auth.py + tts.py

static/    CSS + JavaScript (api, auth, app)
templates/ صفحات HTML (index, login, register)
main.py    نقطة تشغيل FastAPI
```

| الطبقة | التقنية |
|--------|---------|
| Backend | FastAPI |
| Frontend | HTML / CSS / JavaScript |
| TTS Engine | edge-tts (مجاني) |
| Database | SQLite + SQLAlchemy |
| Auth | JWT (PyJWT) + bcrypt |

---

## 🚀 التشغيل (Getting Started)

### المتطلبات
- Python 3.10+ (تم اختباره على 3.14)

### الخطوات

```bash
# 1) تفعيل البيئة الافتراضية
.venv\Scripts\activate          # على Windows

# 2) تثبيت الاعتمادات
pip install -r requirements.txt

# 3) إنشاء ملف .env من النموذج
copy .env.example .env          # على Windows
#  ثم عدّل SECRET_KEY بقيمة عشوائية:
#  python -c "import secrets; print(secrets.token_hex(32))"

# 4) تشغيل الخادم
uvicorn main:app --reload
```

ثم افتح المتصفح على:
- التطبيق: **http://127.0.0.1:8000**
- توثيق API: **http://127.0.0.1:8000/docs**

---

## 🔌 نقاط النهاية (API Endpoints)

| Method | Path | الوصف | محمي |
|--------|------|-------|------|
| POST | `/api/auth/register` | إنشاء حساب جديد | ❌ |
| POST | `/api/auth/login` | تسجيل الدخول (يُرجع JWT) | ❌ |
| GET | `/api/auth/me` | بيانات المستخدم الحالي | ✅ |
| GET | `/api/tts/voices` | قائمة الأصوات المتاحة | ❌ |
| POST | `/api/tts/synthesize` | تحويل نص إلى ملف صوتي | ✅ |

---

## 🔒 الأمان (Security Notes)

- كلمات المرور لا تُخزَّن أبداً كنص صريح — تُجزّأ بـ **bcrypt**.
- المصادقة عبر **JWT** في الترويسة `Authorization: Bearer <token>`.
- ملف `.env` (المفاتيح السرية) وقاعدة البيانات مُستبعدة من Git عبر `.gitignore`.

---

## 📄 الترخيص
مشروع تعليمي ضمن السيرة الذاتية. حرٌّ للاستخدام والتعديل.
