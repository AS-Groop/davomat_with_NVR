# MMTRI Davomat tizimi — loyiha tahlili (ishga tushirish uchun yozib olingan)

## Nima uchun kerak
Haqiqiy FaceID qurilmalarga ulab tizimni real ishga tushirishdan oldin
arxitekturani tushunib olish va ulanish holatini hujjatlashtirish uchun.

## Arxitektura (qisqa)
- **Yagona kirish nuqtasi (hodisalar manbasi):** `biocontrol_api.py` — `.env` dagi
  `FACEID_SOURCE` ga qarab 3 manbadan birini tanlaydi:
  - `devices` → `faceid_devices.py` → `faceid_devices.json` dagi qurilmalar
    (Hikvision ISAPI, port 80, HTTP POST `/ISAPI/AccessControl/AcsEvent`;
    yoki ZKTeco `pyzk`, TCP port 4370)
  - `demo` → soxta, barqaror (seed asosida) ma'lumot, qurilmasiz sinov uchun
  - `biocontrol` → tashqi OneDesk/BioControl HTTP API (enter.mininnovation.uz)
- **Bosh jarayon:** `start_all.py` → `build_departments.py` (users.xlsx dan
  bo'lim/lavozim keshini yangilaydi) → `mobile_api.py` (bitta processda 3 qism):
  - Mobil ilova + API — port 8090 (`.env: MOBILE_API_PORT`)
  - Dashboard (katta ekran) — port 8080 (`.env: DASHBOARD_PORT`)
  - Jonli worker (fon oqimi) — `WORKER_POLL_SECONDS` har safar `biocontrol_api`
    orqali hodisalarni o'qib, `live_cache.json` ni yangilaydi
- **Xodimlar ro'yxati:** `users.xlsx` (ustunlar: familiya/ism/sharif,
  card_number=JSHSHIR, faceid=qurilmadagi raqam, bo'lim, lavozim, work_start,
  role, category, active). `faceid` ustuni bo'sh bo'lsa — JSHSHIR qurilmadagi
  raqam deb olinadi (`faceid_devices.device_id`).
- **Hisoblar:** `accounts.json` — login=JSHSHIR, parol hash+salt;
  `tokens.json` — sessiya tokenlari.
- **Boshqa ma'lumot fayllari:** `exemptions.json` (uzrli kechikish/xizmat
  safari/ta'til), `holidays.json`, `entry_overrides.json` (HR qo'lda tuzatgan
  kirish vaqti), `late_grace_days.json` (bir kunlik imtiyoz), `monthly_report*`.

## Qurilma integratsiyasi — qo'llab-quvvatlanadigan turlar
`faceid_devices.py` faqat ikki turni biladi:
1. **Hikvision** — HTTP ISAPI, Digest auth, `/ISAPI/System/deviceInfo` va
   `/ISAPI/AccessControl/AcsEvent?format=json` (POST, `AcsEventCond` bilan).
2. **ZKTeco** — `pyzk` kutubxonasi orqali TCP 4370 (`get_attendance()`).

ONVIF Profile A/Pacs yoki boshqa proprietar protokollar **qo'llab-
quvvatlanmaydi** — agar qurilma shunday bo'lsa, `faceid_devices.py` ga yangi
klass qo'shish kerak bo'ladi (pastdagi `FACEID_ULANISH_HOLATI.md` ga qarang).

## Ishga tushirish oqimi (real qurilma bilan)
1. `faceid_devices.json` — qurilmalar ro'yxati (host, port, user, password_env,
   direction).
2. `.env` — `FACEID_SOURCE=devices`, `FACEID_PASS_1`/`FACEID_PASS_2` qurilma
   parollari.
3. `faceid_tekshir.py` (yoki `FACEID_TEKSHIR.bat`) — ulanishni **o'zgartirmasdan**
   tekshiradi, bugungi o'tishlarni ko'rsatadi.
4. `start_all.py` (yoki `2_ISHGA_TUSHIRISH.bat`) — to'liq tizimni ishga
   tushiradi (mobil ilova 8090, dashboard 8080, fon worker).

## Shu sessiyada qilingan
- `users.xlsx`, `accounts.json` va boshqa `demo/` fayllar **tegilmadi** —
  mavjud demo (soxta) xodimlar ro'yxati saqlanib qoldi, foydalanuvchi talabiga
  ko'ra.
- `faceid_devices.json` haqiqiy IP manzillar bilan yaratildi, `.env` da
  `FACEID_SOURCE=devices` qilindi — batafsil ulanish holati va topilgan
  muammo `FACEID_ULANISH_HOLATI.md` da.
