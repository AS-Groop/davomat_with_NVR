# Linux serverga ko'chirish — qo'llanma

Shart: server **institut ichki tarmog'ida** turishi kerak — NVR (`192.168.10.35`)
va FaceID qurilmalarga (`192.168.100.x`) to'g'ridan-to'g'ri yeta olishi shart
(ular internetga chiqmaydi). Bulut serverga (DigitalOcean, AWS va h.k.)
qo'yilsa, bu tarmoqqa VPN/tunnel kerak bo'ladi — bu qo'llanma shunga kirmaydi.

## 1. Server talablari

- Ubuntu 22.04+ / Debian 12+ (yoki shunga yaqin) — boshqa distro ham bo'ladi.
- Python **3.10+** (`python3 --version` bilan tekshiring).
- Ichki tarmoqda doimiy IP (DHCP emas — reservation yoki statik).

## 2. Kerakli paketlar

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip fonts-liberation git
```

`fonts-liberation` — tushuntirish xati va yo'qlama varaqasi PDF'larida
kirill/lotin shriftlar to'g'ri chiqishi uchun shart (loyihada Windows/Mac/
Linux shriftlari avtomatik qidiriladi, lekin Linux'da shu paket bo'lishi
kerak).

## 3. Vaqt mintaqasini tekshiring — MUHIM

Tizim `datetime.now()` orqali ishlaydi (kechikish, tushlik, kuniga 4 marta
NVR yangilanishi — `00:00/10:00/18:00/23:00`). Server vaqti **Toshkent**
vaqtida bo'lishi shart, aks holda hammasi noto'g'ri hisoblanadi:

```bash
sudo timedatectl set-timezone Asia/Tashkent
timedatectl   # tekshirish — "Asia/Tashkent" ko'rinishi kerak
```

## 4. Kodni ko'chirish

```bash
sudo mkdir -p /opt/mmtri_davomat
sudo chown $USER:$USER /opt/mmtri_davomat
cd /opt/mmtri_davomat
git clone <GitHub-repo-manzili> .
```

**Diqqat:** `.gitignore` tufayli quyidagilar GitHub'da YO'Q — ularni eski
(Windows) kompyuterdan **qo'lda** nusxalashingiz kerak (masalan
`scp`, flash, yoki umumiy papka orqali):

- `.env`
- `users.xlsx`
- `accounts.json`
- `tokens.json`
- `nvr_reports/` (butun papka — tarixiy ma'lumot shu yerda)
- `monthly_reports/` (oylik arxiv)
- `live_cache.json`
- `photos/` (xodim rasmlari)
- `faceid_devices.json` (agar `FACEID_SOURCE=devices` ishlatilsa)

```bash
# masalan Windows kompyuterdan Linux serverga (Windows'da PowerShell'dan):
scp .env users.xlsx accounts.json tokens.json live_cache.json faceid_devices.json ^
    user@linux-server:/opt/mmtri_davomat/
scp -r nvr_reports monthly_reports photos user@linux-server:/opt/mmtri_davomat/
```

## 5. Python muhiti va kutubxonalar

```bash
cd /opt/mmtri_davomat
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## 6. Sinab ko'ring (xizmat sifatida o'rnatishdan OLDIN)

```bash
cd /opt/mmtri_davomat
venv/bin/python nvr_login_test.py      # NVR bilan ulanish ishlayaptimi?
venv/bin/python start_all.py           # Ctrl+C bilan to'xtatish mumkin
```

Boshqa terminaldan (yoki brauzerdan) tekshiring:
```bash
curl -I http://localhost:8090/
curl -I http://localhost:8080/
```
`200`/`302` qaytsa — ishlayapti. `Ctrl+C` bilan to'xtating.

## 7. Doimiy xizmat sifatida ishga tushirish (systemd)

Loyiha ichida tayyor **`mmtri-davomat.service`** fayli bor. Uni moslang:

```bash
sudo nano mmtri-davomat.service
```
- `User=mmtri` — alohida (root bo'lmagan) foydalanuvchi yarating:
  `sudo useradd -r -s /usr/sbin/nologin mmtri` va fayllarga egalik bering:
  `sudo chown -R mmtri:mmtri /opt/mmtri_davomat`
- `WorkingDirectory` va `ExecStart` — agar boshqa papkaga joylagan bo'lsangiz
  to'g'rilang.

So'ng:
```bash
sudo cp mmtri-davomat.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mmtri-davomat
sudo systemctl status mmtri-davomat     # "active (running)" ko'rinishi kerak
journalctl -u mmtri-davomat -f          # jonli log (konsol o'rniga)
```

Endi server qayta yonsa ham, dastur yiqilib qolsa ham (`Restart=always`)
tizim o'zi qayta ishga tushadi — Windows'dagi "oynani yopmang" degan
cheklov endi yo'q.

## 8. Portlarni ochish (agar firewall yoqilgan bo'lsa)

```bash
sudo ufw allow 8090/tcp
sudo ufw allow 8080/tcp
```

## 9. Internetdan kirish (ixtiyoriy)

`start_tunnel.bat` o'rniga Linux uchun cloudflared:
```bash
curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared
./cloudflared tunnel --url http://localhost:8090 &
./cloudflared tunnel --url http://localhost:8080 &
```
Doimiy bo'lishi uchun buni ham systemd xizmatiga aylantirish mumkin
(so'rasangiz tayyorlab beraman).

## 10. Kundalik yangilash (kod o'zgarganda)

```bash
cd /opt/mmtri_davomat
git pull
venv/bin/pip install -r requirements.txt   # kutubxona qo'shilgan bo'lsa
sudo systemctl restart mmtri-davomat
```

## 11. Zaxira nusxa — serverda ham unutmang

Ma'lumotlar (`users.xlsx`, `accounts.json`, `nvr_reports/`,
`monthly_reports/`, `.env`) endi Linux serverda — ularni muntazam
zaxiralash tartibini shu yerda ham o'rnating (masalan `cron` orqali boshqa
diskka/serverga nusxalash).
