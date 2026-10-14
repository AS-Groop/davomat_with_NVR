# FaceID qurilma ulanishi — tekshiruv natijasi (2026-10-13)

## Berilgan ma'lumotlar
- Kirish: `192.168.100.101`
- Chiqish: `192.168.100.102` (birinchi xabarda `.100` edi, ikkinchi xabarda `.102` ga
  to'g'rilandi — shu IP ishlatildi)
- Login: `admin` / Parol: `123456`
- Qo'shimcha: `CAMERA_PORT=554`, `CAMERA_PATH=/profile1` (RTSP video oqimi)

## Qilingan tekshiruvlar
1. `Test-NetConnection` — ikkala IP ham port **80** (HTTP) va **554** (RTSP) da
   ochiq (tarmoqda ko'rinadi).
2. `faceid_tekshir.py` (loyihaning o'z diagnostika skripti, Hikvision ISAPI
   deb urinib) — ikkala qurilma ham `401 Unauthorized` qaytardi (Digest auth
   bilan).
3. To'g'ridan-to'g'ri HTTP so'rovlar (`requests` bilan):
   - Auth yo'q bo'lsa → `401`, `WWW-Authenticate: Basic realm="Basic"` —
     demak qurilma **Basic auth** kutadi, Digest emas (haqiqiy Hikvision
     ISAPI odatda Digest beradi).
   - Basic auth (`admin`/`123456`) bilan → `400`, barcha yo'llar uchun BIR XIL
     javob: `<config xmlns="http://www.ipc.com/ver10" status="failed"
     errorCode="499" IssameOldPwd="false"/>`. Bu javob `/ISAPI/System/deviceInfo`,
     `/ISAPI/AccessControl/AcsEvent`, `/System/deviceInfo`, hatto mavjud
     bo'lmagan yo'llar uchun ham bir xil chiqdi — demak bu Hikvision ISAPI
     EMAS, balki umumiy (OEM) kamera firmware'ning standart xatosi.
4. **Brauzerda ochib ko'rildi** (faqat login sahifasi — parol kiritilmadi):
   - `http://192.168.100.101/` → sahifa nomi **"Web camera"**,
     `Pages/login.htm`, formada "Stream Type: 1920x1080 25fps" maydoni bor.
   - `http://192.168.100.102/` → xuddi shu — **"Web camera"** login sahifasi.

## Xulosa
Berilgan ikki IP — **oddiy IP-kameralar** (video oqim qurilmalari, RTSP
`554/profile1`), ular odatiy veb-kamera login sahifasiga ega va faqat video
ko'rsatish/yozish uchun mo'ljallangan. Ular **kirish/chiqish (attendance)
jurnalini** saqlamaydi va bu loyiha kutadigan ISAPI/`AcsEvent` yoki ZKTeco
protokolini taqdim etmaydi.

`faceid_devices.py` (loyihaning qurilma integratsiyasi) faqat ikki turni
biladi:
- **Hikvision** — haqiqiy access-control terminal, ISAPI `AcsEvent`
- **ZKTeco** — `pyzk`, TCP 4370

Oddiy IP-kamera ikkalasiga ham to'g'ri kelmaydi — undan "kim qachon kirdi/
chiqdi" degan hodisa ro'yxatini olib bo'lmaydi (u faqat video beradi, yuzni
his qilib xodimni aniqlash va buni jurnal qilib saqlash funksiyasi yo'q).

## Nima qilingan (joriy holat)
- `faceid_devices.json` — ikki qurilma shu IP'lar bilan yozildi (`hikvision`
  turi deb, chunki hozircha boshqa variant yo'q).
- `.env`: `FACEID_SOURCE=devices`, `FACEID_PASS_1=123456`,
  `FACEID_PASS_2=123456`.
- Natija: tizim ishga tushadi, ammo fon worker ushbu ikki IP'dan hodisa
  o'qishga urinib, doim ulanish xatosi ko'radi (xavfli emas — faqat HTTP
  GET/POST, qurilmaga zarar yo'q) va **jonli kirish/chiqish ma'lumoti
  bo'lmaydi**.

## Foydalanuvchi javobi va yakuniy qaror (2026-10-13)
Foydalanuvchi tasdiqladi: `192.168.100.101` / `.102` — aynan shu ikki FaceID
qurilmaning IP manzillari (boshqa alohida terminal yo'q). Ammo bu loyihaning
`faceid_devices.py` (Hikvision ISAPI / ZKTeco) integratsiyasi orqali ulardan
attendance (kirish/chiqish) ma'lumotini olib bo'lmadi — qurilmalar hozircha
faqat **VLC orqali RTSP video sifatida** ishlaydi (`rtsp://192.168.100.102:554/
profile1`, `admin`/`123456` — foydalanuvchi buni sinab ko'rib, video oqimga
ulanishni tasdiqladi).

**Qaror:** Birinchi versiyada bu ikki qurilma faqat kamera (video kuzatish)
sifatida alohida (VLC/NVR orqali, shu loyihadan tashqarida) ishlatiladi.
Loyihaning o'zi hech qanday video/RTSP funksiyasiga ega emas va bunga ehtiyoj
yo'q — shu sababli **loyiha kodi o'zgartirilmadi**. Davomat tizimi hozircha
`FACEID_SOURCE=demo` da ishlaydi (mavjud soxta/demo xodimlar bilan), real
FaceID-attendance integratsiyasi keyingi versiyada ulanadi (ehtimol
qurilmaning haqiqiy proprietar API/SDK'sini aniqlash kerak bo'ladi — ISAPI va
pyzk ikkisi ham mos kelmadi).

`faceid_devices.json` fayli real IP'lar bilan saqlab qo'yildi (ishlatilmaydi,
chunki `FACEID_SOURCE=demo`) — keyinchalik haqiqiy integratsiya topilganda
tezda ishga tushirish uchun tayyor turadi.

## Yangilanish — real integratsiya topildi (2026-10-13, davomi)

Foydalanuvchi qurilmalarni NVR orqali boshqarishini aniqladi:
- **NVR**: `192.168.10.35`, model `VS-N308B1-8P`, veb-klient — login/parol
  foydalanuvchida.
- **Terminal**: brand **Tank**, model `VS-E2127-IC`, ONVIF 20.12 — bu haqiqiy
  yuz tanish + kirish nazorati terminali (Face Match, Access Control, Door
  Lock bo'limlari bor).

NVR JS kodidan (`js/index.js`: `systemType="NVMS-9000"`) aniqlandi — bu
**TVT (Shenzhen TVT Digital) OEM** platformasi, "Tank" esa shu platformani
qayta brendlagan diler/sotuvchi. Login (`/doLogin`) challenge-response
(SHA1/MD5) asosida ishlaydi, oddiy Basic/Digest emas — ochiq hujjat
topilmadi. Shu sababli to'g'ridan-to'g'ri HTTP API integratsiyasi (reverse-
engineering) o'rniga **NVR'ning o'z "Attendance" (Приветствие) bo'limidagi
eksport funksiyasidan** foydalanishga qaror qilindi.

### Topilgan NVR imkoniyatlari
1. **"Управление сотрудниками" → Экспорт** → "Файл БД лиц (*.csv + *.jpg)" —
   xodimlar bazasi (ism, bo'lim, lavozim, qurilmadagi "ID сотрудника" 1–41,
   suratlari). 41 ta haqiqiy xodim topildi.
2. **"Приветствие" → Статистика посещения → Экспорт** → "Attendance Report"
   → `.xls` (aslida HTML jadval). Har bir xodim uchun **"All Records"**
   ustunida kun davomidagi barcha kirish/chiqish vaqtlari (bo'sh joy bilan
   ajratilgan, masalan `"09:05 13:59 15:59 18:29"`) — aynan kerakli ma'lumot.

### Qurilgan integratsiya
- **`nvr_report_import.py`** (yangi modul) — `nvr_reports/` papkasidagi
  `.xls`/`.xlsx` fayllarni o'qiydi, "Work Number" (qurilma ID) + "Дата" +
  "All Records" dan foydalanib, toq/juft navbat bilan kirish/chiqish
  hodisalarini quradi.
- **`biocontrol_api.py`** ga yangi manba qo'shildi: `FACEID_SOURCE=nvr_reports`
  — `faceid_devices.device_id()` orqali `users.xlsx` dagi `faceid` ustuni
  bilan qurilma "Work Number"ini bog'laydi (mavjud mantiqdan foydalanildi,
  o'zgartirilmadi).
- **`users.xlsx`** ga NVR'dagi 41 ta haqiqiy xodim **qo'shildi** (mavjud 24 ta
  demo xodim o'chirilmadi — shu bilan Boshqaruv panelidagi demo HR/director
  kirish huquqi buzilmadi):
  - `faceid` = NVR "Work Number" (1–41)
  - `card_number` (login) = **vaqtinchalik** 14 xonali raqam
    `99` + Work Number (masalan `99000000000011`), chunki haqiqiy JSHSHIR
    hali yo'q — HR tomonidan keyin to'g'rilanishi kerak.
  - Boshlang'ich parol = login oxirgi 6 raqami (masalan `000011`),
    ro'yxat `new_accounts.txt` da.
  - `role` hammasiga bo'sh (= oddiy xodim) qoldirildi — hech kimga avtomatik
    `hr`/`director` berilmadi (bu kirish huquqi masalasi, qo'lda
    belgilanishi kerak; masalan Work Number 34 — Allabergenov Anvar
    Alimbayevich, lavozimi "Direktor").
  - **Ism-sharif qisman kesilgan** — NVR terminalidagi ism maydoni uzunligi
    cheklangan (~31-32 belgi), masalan "Abduqahhorov Yorqin Sherali ogl"
    ("o'g'li" so'zining oxiri tushib qolgan). HR keyin to'liq ism bilan
    to'g'rilashi kerak.
  - "Tug'ilgan sana" maydoni **to'ldirilmadi** — NVR eksportidagi sana
    aslida ro'yxatga olingan sana edi, haqiqiy tug'ilgan kun emas.

### Kundalik ishlatish tartibi
1. NVR veb-klientida (`http://192.168.10.35`): **Приветствие → Статистика
   посещения → Экспорт → "Attendance Report"**.
2. Yuklangan faylni loyiha papkasidagi **`nvr_reports/`** ichiga nusxalang
   (nomi muhim emas, eski fayllarni o'chirish shart emas).
3. Fon worker (`WORKER_POLL_SECONDS=10`) avtomatik o'qib, dashboard/ilovani
   yangilaydi.

### Sinov natijasi (2026-10-13)
`biocontrol_api.get_events()` orqali to'liq zanjir sinaldi — masalan
Sheraliyev Asadbek (faceid=11, card=99000000000011) uchun **09:01 kirish**
to'g'ri o'qildi (NVR'dagi haqiqiy qiymat bilan bir xil). Tizim qayta ishga
tushirilgach, `live_cache.json` da 14 nafar xodim "ishda" deb haqiqiy
vaqtlar bilan ko'rindi.

### Qolgan ishlar (HR uchun)
- 41 xodimning haqiqiy JSHSHIR'ini kiritib, `card_number` ustunini
  to'g'rilash (vaqtinchalik `99...` raqamlar o'rniga).
- Ism-shariflarni to'liq (kesilmagan) holatda tekshirish/to'g'rilash.
- Kerakli xodimlarga `role=hr` yoki `role=director` belgilash.
- Eksportni kundalik qo'lda qilish o'rniga, agar NVR'da avtomatik
  (zaplanirovannыy) eksport/email funksiyasi topilsa — shuni sozlash
  mumkin (keyingi versiya uchun).

## "Yangilash" tugmasi — avtomatik login urinishi (2026-10-13, muvaffaqiyatsiz)

Maqsad: Boshqaruv panelida tugma bosilsa, server o'zi NVR'ga kirib,
Attendance hisobotini so'rab, `nvr_reports/` ga avtomatik joylashtirsin.

### Topilgan narsalar (foydali, keyingi urinish uchun saqlanadi)
NVR veb-klienti JS kodini o'qib (`js/app/login.js`, `js/lib/Communication.js`,
`js/app/Attendance/attendRecord.js`) to'liq protokol aniqlandi:

1. **Login (challenge-response):**
   - `POST /reqLogin` — bo'sh so'rov (`<token>null</token>`) → javobda
     `nonce`, `sessionId`, `token` (barchasi `{GUID}` ko'rinishida) keladi.
   - Parol: `hash = SHA1( MD5(parol).hexdigest().UPPER() + nonce ).hexdigest().UPPER()`
     (nonce — qavslari bilan, `{...}` o'zgarishsiz).
   - `POST /doLogin` — `<token>{reqLogin'dan}</token><content><userName>
     <![CDATA[admin]]></userName><password><![CDATA[{hash}]]></password>
     </content>` — muvaffaqiyatli bo'lsa `<status>success</status>`.
   - Bu formula **ikkita mustaqil haqiqiy login namunasi bilan tasdiqlandi**
     (foydalanuvchi DevTools/HAR orqali yuborgan nonce+hash juftliklari —
     ikkalasida ham mos keldi).

2. **Kerakli ma'lumot so'rovi** (login'dan keyin, xuddi shu token bilan):
   ```
   POST /queryAttendanceStatisticDetail
   <condition><startTime>YYYY-MM-DD 00:00:00</startTime>
   <endTime>YYYY-MM-DD 23:59:59</endTime><detailType>byDay</detailType>
   <idParam><item>{workNumber}</item>...</idParam></condition>
   ```
   Javobda `response>content>AttendanceDetail>item` ichida har xodim uchun
   `detail>item>Record>item` — kun davomidagi barcha punch vaqtlari
   ("HH:MM"). Bu `.xls` eksportidagi "All Records" bilan bir xil ma'lumot,
   hech qanday faylga ehtiyojsiz to'g'ridan-to'g'ri olinadi.

### Muammo
Yuqoridagi formula bilan tuzilgan so'rov **mening skriptimdan doim rad
etildi** (`errorCode 536870934`), xuddi shu formula bilan **brauzerda doim
muvaffaqiyatli** ishladi. Tekshirib chiqilgan va inkor etilgan sabablar:
- Format/bayt farqi — yo'q (Content-Length aniq mos keldi).
- Hash formulasi — to'g'ri (2 marta mustaqil tasdiqlandi).
- HTTP sarlavhalar (Accept, Origin, Referer, Content-Type, User-Agent,
  X-Requested-With, Cookie) — barchasi HAR fayldagi bilan aynan bir xil
  qilib yuborildi.
- Vaqt oralig'i — yo'q (TCP_NODELAY bilan ~90ms da bajarilsa ham xato).
- Qurilma xavfsizlik sozlamalari (Allow/Block ro'yxati, ARP himoyasi,
  hujum aniqlash) — barchasi o'chiq, bloklovchi hech narsa yo'q.

Sabab avval aniqlanmadi — pastdagi "YECHIM TOPILDI" bo'limiga qarang.

## YECHIM TOPILDI (2026-10-13, davomi)

Sabab: **`/doLogin` so'rovida `Cookie: sessionId={qavslarsiz GUID}` header
bo'lishi SHART edi.** Bu cookie serverning `Set-Cookie` javobida KELMAYDI —
brauzer uni sof JavaScript orqali (`webSession.ClearAllCookie()` +
`$.cookie(...)`, `js/lib/Communication.js` va `js/lib/webSession.js`) qo'yib
yuboradi, `reqLogin` javobidagi `<sessionId>` qiymatini saqlab turib. Shu
sababli bu HAR faylida ham, oddiy tarmoq tahlilida ham ko'rinmay qolgan edi —
faqat JS kodining o'zini satrma-satr o'qib topildi.

Tasdiqlash: foydalanuvchi o'z kompyuterida (`nvr_login_test.py` orqali, keyin
`dangerouslyDisableSandbox` bilan mening tomonimdan ham) sinalganda — bu
cookie qo'shilgach, `doLogin` **darhol muvaffaqiyatli** bo'ldi.

### Yaratilgan modul: `nvr_live.py`
To'liq avtomatik integratsiya:
1. `login()` — `/reqLogin` → xesh hisoblash → `/doLogin` (sessionId cookie
   bilan) → token qaytaradi.
2. `_fetch_day()` — `/queryAttendanceStatisticDetail` (`detailType=byDay`,
   `idParam`=barcha xodimlarning `users.xlsx` dagi `faceid` qiymatlari) —
   `xml.etree.ElementTree` bilan to'g'ri parse qilinadi (ichma-ich `<item>`
   teglar ko'p — oddiy regex ADASHADI, shu sabab haqiqiy XML parser kerak).
3. `refresh()` — natijani `nvr_reports/_live_cache.json` ga yozadi.
   `nvr_report_import.py` endi shu faylni ham o'qiydi (qo'lda tashlangan
   `.xls` fayllar bilan bir qatorda, `_all_rows()` da birlashtiriladi).

### "Yangilash" tugmasi
- Backend: `mobile_admin.py` → `POST /api/mobile/admin/nvr_refresh` (faqat
  HR roli, `_auth_hr`). `nvr_live.refresh()` ni chaqiradi.
- Frontend: `mobile/app.js` → Boshqaruv → **📡 Monitoring** bo'limi
  (`admSecMonitor`) ichiga "🔄 NVR'dan yangilash" tugmasi qo'shildi.
- Sinov (HTTP orqali, HR hisobi bilan): `{"ok": true, "date": "2026-10-13",
  "employees": 36, "total_queried": 63, "events": 82}` — muvaffaqiyatli.

### .env ga qo'shildi (qiymatlar shu yerda emas — faqat .env da, GitHub'ga ketmaydi)
```
NVR_HOST=...
NVR_USER=admin
NVR_PASSWORD=...
```

### Diagnostika skripti
`nvr_login_test.py` — kerak bo'lsa kelajakda login muammosini qayta
tekshirish uchun qoldirildi (mustaqil, loyihaning qolgan qismiga bog'liq
emas).

## Yangilanish — avtomatik jadval + foydalanuvchi tugmasi (2026-10-13, davomi)

1. **Kuniga 4 marta avtomatik yangilanish** (`live_worker_api.py` →
   `maybe_nvr_refresh()`, `worker_loop()` ichida har 10 sek tekshiriladi):
   `00:00`, `10:00`, `18:00`, `23:00`. Faqat `FACEID_SOURCE=nvr_reports`
   bo'lganda ishlaydi.
2. **Ilovadagi `⟳` tugmasi** (yuqori o'ng burchak, hamma sahifada bor) —
   endi login qilgan **har qanday xodim** bossa, `POST /api/mobile/refresh_nvr`
   chaqiriladi (`mobile_api.py`) — bu ham `nvr_live.refresh()` ni ishga
   tushiradi. Qurilmaga ortiqcha yuk tushmasligi uchun **20 soniyalik
   cooldown** bor (shu oraliqda qayta bosilsa — oxirgi natija qaytariladi,
   qurilmaga qayta murojaat qilinmaydi).
3. Boshqaruv panelidagi "🔄 NVR'dan yangilash" tugmasi (faqat HR) — avvalgidek
   qoladi, alohida endpoint (`/api/mobile/admin/nvr_refresh`).

## Demo xodimlar o'chirildi (2026-10-13, davomi)

Loyiha boshidagi 23 ta demo (soxta) xodim butunlay o'chirildi:
`users.xlsx` dan qatorlar, `accounts.json` dan hisoblar, `exemptions.json`
dagi demo yozuv, `photo_overrides.json` va `photos/` dagi demo rasmlar.

**Muhim:** demo xodimlar orasida yagona `hr`/`director` rolli hisoblar bor
edi — ular o'chirilishidan oldin **Sheraliyev Asadbek Alisher ogli**
(faceid=11, card=99000000000011) ga `role=hr` berildi (foydalanuvchi
tasdiqlashi bilan), aks holda Boshqaruv panelga hech kim kira olmay
qolardi. Bu — `users.xlsx` dagi `role` ustunidan tashqari, `accounts.json`
dagi mavjud hisobning `role` maydonini ham qo'lda yangilashni talab qildi —
chunki hisob allaqachon yaratilgan bo'lsa, `users.xlsx` dagi keyingi
o'zgarish uni **avtomatik yangilamaydi** (`auto_seed_accounts` faqat YANGI
kartalar uchun ishlaydi). Bu loyihaning umumiy xatti-harakati — kelajakda
boshqa xodimga rol berilsa, xuddi shunday qo'lda tuzatish kerak bo'ladi
(yoki HR hisob o'chirib qayta yaratishi mumkin).

Hozir tizimda **jami 41 xodim** bor — hammasi NVR'dan olingan haqiqiy
xodimlar, demo/soxta ma'lumot qolmagan.
