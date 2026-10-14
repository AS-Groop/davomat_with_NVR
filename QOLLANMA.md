# MMTRI Davomat tizimi — o'rnatish qo'llanmasi

Milliy malaka tizimini rivojlantirish instituti uchun ish vaqti nazorati:
FaceID qurilmasidan kirish/chiqish, jonli dashboard (katta ekran), xodimlar
uchun mobil ilova, oylik hisobot va reyting, tushuntirish xati va arizalar.

---

## 1. Nima kerak

| | |
|---|---|
| Kompyuter | Doim yoqiq turadigan Windows kompyuter (FaceID bilan bir tarmoqda) |
| Python | 3.10 yoki yangiroq — python.org dan, o'rnatishda **"Add Python to PATH"** belgilansin |
| Xodimlar ro'yxati | `users.xlsx` (namuna: `users_namuna.xlsx`) |
| FaceID | Qurilma IP manzili, admin login va paroli |
| Internet orqali kirish (ixtiyoriy) | `cloudflared.exe` yoki o'z domeni |

## 2. Avval DEMO bilan ko'rib chiqish (qurilmasiz, 5 daqiqa)

1. `1_ORNATISH.bat` — kutubxonalarni o'rnatadi.
2. `.env` faylni Bloknotda ochib, `DASHBOARD_PASSWORD=` ga parol yozing.
3. `DEMO_ISHGA_TUSHIRISH.bat` — o'ylab topilgan 23 xodim bilan tizim ishga tushadi.
4. Brauzerda:
   - Ilova: `http://localhost:8090` — HR: login `90751163726516`, parol `726516`
     (birinchi kirishda parol almashtiriladi)
   - Dashboard: `http://localhost:8080` — `.env` dagi parol bilan

Ko'rib bo'lgach: oynani yoping, papkadagi `users.xlsx`, `accounts.json`,
`tokens.json`, `live_cache.json`, `monthly_report.json`, `new_accounts.txt`,
`employee_departments.json` fayllarini o'chiring (bular demo ma'lumotlari).

## 3. Haqiqiy ishga tushirish

### 3.1. Xodimlar ro'yxati
`users_namuna.xlsx` ni to'ldirib, **`users.xlsx`** nomi bilan saqlang:

| Ustun | Nima yoziladi |
|---|---|
| familiya, ism, sharif | F.I.Sh. |
| card_number | JSHSHIR (14 raqam) — ilovaga kirish logini |
| faceid | FaceID qurilmadagi xodim raqami (bo'sh bo'lsa JSHSHIR olinadi) |
| bo'lim, lavozim | Tushuntirish xati va hisobotlar uchun |
| work_start | Ish boshlanishi, masalan `09:00` |
| role | `hr` — Boshqaruv paneliga kiradi; `director` — hisobotlarni ko'radi |
| category | `rahbar` / `haydovchi` / `masofaviy` — kechikkan/kelmagan ro'yxatida chiqmaydi |
| active | bo'sh = faol, `0` = ishdan bo'shagan |

Kamida bitta xodimga `role = hr` yozing.

### 3.2. FaceID qurilmani ulash

**Qurilma markasini aniqlang** (qurilma orqasidagi yorliq yoki menyu → "Device info").

1. `faceid_devices_namuna.json` ni **`faceid_devices.json`** nomi bilan nusxalang va to'ldiring:
   - `type`: `hikvision` yoki `zkteco`
   - `host`: qurilma IP manzili (masalan `192.168.1.64`)
   - `user`: odatda `admin` (Hikvision)
   - `password_env`: `.env` dagi parol o'zgaruvchisi nomi (`FACEID_PASS_1`)
   - `direction`:
     - `in` — qurilma faqat kirishda; `out` — faqat chiqishda
     - `auto` — bitta qurilma ikkala tomonga (qurilmadagi Kirish/Chiqish holati
       yoki kun ichida navbatma-navbat hisoblanadi)
2. `.env` da:
   ```
   FACEID_SOURCE=devices
   FACEID_PASS_1=qurilma_paroli
   ```
3. **`FACEID_TEKSHIR.bat`** — qurilmaga ulanadi va bugungi o'tishlarni ko'rsatadi.
   Ro'yxatdagi `raqam=...` lar `users.xlsx` dagi `faceid` ustuni bilan mos bo'lishi kerak.
   Bitta xodimni tekshirish: `FACEID_TEKSHIR.bat 31234567890123`

ZKTeco uchun qo'shimcha: `python -m pip install pyzk` (1_ORNATISH.bat buni o'rnatadi).

Agar qurilma OneDesk/BioControl tizimiga ulangan bo'lsa (NQAAE dagidek):
`FACEID_SOURCE=biocontrol`.

> Muhim: Hikvision va ZKTeco ulanishi ochiq hujjatlar asosida yozilgan va
> sinov serverida tekshirilgan, lekin **haqiqiy qurilmada birinchi marta
> FACEID_TEKSHIR.bat bilan albatta sinab ko'ring**.

### 3.3. Ishga tushirish
`2_ISHGA_TUSHIRISH.bat` — oynani yopmang. Konsolda:
```
✅ live_worker_api ishga tushdi — NN xodim ...
   API: FaceID qurilmalari (faceid_devices.json)
[..] cache yangilandi — ishda:.. kech:.. (N sek)
```
Xodimlarning hisoblari avtomatik ochiladi: login — JSHSHIR, dastlabki parol —
JSHSHIR ning oxirgi 6 raqami. Ro'yxat `new_accounts.txt` da — tarqatib bo'lgach
**faylni o'chiring**.

### 3.4. Telefondan / internetdan kirish
- Ichki tarmoqda: `http://<kompyuter-IP>:8090`
- Internetdan: `cloudflared.exe` ni papkaga qo'ying va `start_tunnel.bat` ni ishga
  tushiring — ikkita `https://....trycloudflare.com` havola chiqadi
  (kompyuter o'chsa havola o'zgaradi; doimiy havola uchun o'z domeni kerak).
- Xavfsizlik: dastlabki parol bilan internetdan kirib bo'lmaydi — xodim parolini
  avval ish joyidagi tarmoqda almashtiradi.

## 4. Kundalik ish

| Vazifa | Qayerda |
|---|---|
| Kim ishda, kim kechikdi | Dashboard / ilova "Bosh" |
| Uzrli kechikish, xizmat safari, ta'til, bayram kunlari | Ilova → Boshqaruv |
| Tushuntirish xati so'rash va ko'rish | Ilova → Tushuntirish |
| Arizalar | Ilova → Ariza |
| Oylik hisobot, reyting | Ilova → Boshqaruv → Reyting; har kuni ertalab avtomatik yangilanadi; darhol — `HISOBOTNI_YANGILASH.bat` |
| Yangi xodim | `users.xlsx` ga qo'shish (saqlangach o'zi o'qiladi) yoki Boshqaruv → Xodim qo'shish |
| Xodim rasmi | Boshqaruv → Rasm yuklash |

## 5. Sozlamalar

- **Tashkilot nomi, tushuntirish xati kimga yoziladi** — `tashkilot.json`
- **Logotip** — `mobile/logo.png` (kvadrat PNG), ilova belgilari — `mobile/icons/`
- **Ish vaqti, kechikish chegarasi, tushlik** — `.env` (`WORK_START`, `LATE_GRACE_MINUTES`, ...)
- **Dam olish/bayram kunlari** — Boshqaruv → Bayramlar (yoki `holidays.json`)
- **Bir kunlik imtiyoz** (hamma kechikmagan deb hisoblansin) — `late_grace_days.json`:
  `{"2026-10-09": {"until": "23:59", "entry_as": "09:00"}}`
- **Bitta xodimning kirish vaqtini tuzatish** — `entry_overrides.json`:
  `{"2026-10-09": {"<JSHSHIR>": {"in": "09:01"}}}`

## 6. Zaxira nusxa

Har kuni (yoki haftada) papkani to'liq boshqa diskka nusxalang. Eng muhimlari:
`users.xlsx`, `accounts.json`, `.env`, `exemptions.json`, `late_excused.json`,
`explanations*`, `arizalar*`, `monthly_reports/`, `photos/`.

**`.env` faylni hech kimga bermang** — unda parollar bor.

## 7. Shaxsga doir ma'lumotlar

Tizim JSHSHIR, rasm va kirish-chiqish vaqtlarini qayta ishlaydi. Institutda bu
haqda buyruq (yoki ichki tartib) bo'lishi va xodimlar xabardor qilinishi kerak;
ma'lumotlar institut kompyuterida (O'zbekiston hududida) saqlanadi.
