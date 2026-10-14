# -*- coding: utf-8 -*-
"""faceid_devices.py — FaceID qurilmalaridan kirish/chiqish hodisalarini o'qish.

Qaysi manba ishlatilishi .env dagi FACEID_SOURCE bilan tanlanadi
(biocontrol_api.py shu modulni chaqiradi):

  FACEID_SOURCE=devices   — qurilmalar faceid_devices.json da ro'yxatlangan
                            (Hikvision va/yoki ZKTeco, bir nechtasi bo'lishi mumkin)
  FACEID_SOURCE=demo      — sinov/taqdimot uchun soxta ma'lumot (qurilmasiz)
  FACEID_SOURCE=biocontrol — enter.mininnovation.uz (NQAAE dagidek)

faceid_devices.json namunasi:
[
  {"name": "Kirish", "type": "hikvision", "host": "192.168.1.64", "port": 80,
   "user": "admin", "password_env": "FACEID_PASS_1", "direction": "in"},
  {"name": "Chiqish", "type": "hikvision", "host": "192.168.1.65",
   "user": "admin", "password_env": "FACEID_PASS_2", "direction": "out"},
  {"name": "Asosiy", "type": "zkteco", "host": "192.168.1.201", "port": 4370,
   "password_env": "", "direction": "auto", "use_punch": false}
]

direction:
  "in"   — qurilma faqat kirishda turadi (har o'tish = kirish)
  "out"  — qurilma faqat chiqishda turadi (har o'tish = chiqish)
  "auto" — bitta qurilma ikkala tomonga: Hikvision'da qurilmadagi
           checkIn/checkOut holati, ZKTeco'da punch (use_punch=true) ishlatiladi;
           ular bo'lmasa — kun ichida navbatma-navbat (1-kirish, 2-chiqish, 3-kirish...)

Parollar faylda EMAS, .env da saqlanadi (password_env — o'zgaruvchi nomi).

Xodimni qurilmadagi raqami: users.xlsx dagi "faceid" ustuni. Ustun bo'lmasa
yoki bo'sh bo'lsa — JSHSHIR (card_number) qurilmadagi raqam deb olinadi.

DIQQAT: Hikvision (ISAPI) va ZKTeco (pyzk) ulanishlari ochiq hujjatlar asosida
yozilgan; haqiqiy qurilmada "FACEID_TEKSHIR.bat" bilan sinab ko'rish shart.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

ENTER, EXIT = "вход", "выход"
BASE_DIR = Path(".")
DEVICES_FILE = BASE_DIR / "faceid_devices.json"
USERS_FILE = BASE_DIR / "users.xlsx"
CACHE_TTL = float(os.getenv("FACEID_CACHE_SECONDS", "8"))
TIMEOUT = float(os.getenv("FACEID_TIMEOUT", "15"))

_LOCK = threading.RLock()


# ═════════════════════ Umumiy ═════════════════════
def load_devices() -> list[dict]:
    try:
        d = json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
        return [x for x in d if isinstance(x, dict) and x.get("host")] if isinstance(d, list) else []
    except Exception:
        return []


def _password(dev: dict) -> str:
    env = str(dev.get("password_env") or "").strip()
    return os.getenv(env, "") if env else str(dev.get("password") or "")


def _local(dt: datetime) -> datetime:
    """Vaqt zonasi bo'lsa — kompyuterning mahalliy vaqtiga o'tkazib, zonani olib tashlaydi."""
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


# ── users.xlsx: JSHSHIR -> qurilmadagi raqam ──
_IDMAP = {"mtime": None, "to_dev": {}, "to_card": {}}


def _norm(x) -> str:
    s = str(x or "").strip()
    if s.endswith(".0"):
        s = s[:-2]
    return "".join(ch for ch in s if ch.isalnum())


def _load_idmap():
    try:
        mt = USERS_FILE.stat().st_mtime
    except Exception:
        return
    if _IDMAP["mtime"] == mt:
        return
    to_dev, to_card = {}, {}
    try:
        import openpyxl
        wb = openpyxl.load_workbook(USERS_FILE, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        hdr_i, card_c, dev_c = None, None, None
        for i, row in enumerate(rows[:10]):
            low = [str(c or "").strip().lower() for c in row]
            cc = next((j for j, v in enumerate(low) if v in ("card_number", "card number", "jshshir", "pinfl", "card")), None)
            dc = next((j for j, v in enumerate(low) if v.replace(" ", "").replace("_", "") in
                       ("faceid", "faceidraqam", "faceidraqami", "qurilmaraqami", "employeeno", "deviceid")), None)
            if cc is not None:
                hdr_i, card_c, dev_c = i, cc, dc
                break
        if hdr_i is not None and dev_c is not None:
            for row in rows[hdr_i + 1:]:
                c = _norm(row[card_c] if card_c < len(row) else "")
                d = _norm(row[dev_c] if dev_c < len(row) else "")
                if c and d:
                    to_dev[c] = d
                    to_card[d] = c
        wb.close()
    except Exception as e:
        print(f"[FACEID] users.xlsx dan faceid ustunini o'qib bo'lmadi: {e}")
    _IDMAP.update(mtime=mt, to_dev=to_dev, to_card=to_card)


def device_id(card) -> str:
    _load_idmap()
    c = _norm(card)
    return _IDMAP["to_dev"].get(c, c)


def _assign_directions(events: list[dict]) -> list[dict]:
    """Yo'nalishi noma'lum (type=None) hodisalarga kun ichida navbatma-navbat
    kirish/chiqish beriladi. Ma'lum yo'nalishli hodisa navbatni davom ettiradi."""
    events.sort(key=lambda e: e["dt"])
    last_day, nxt = None, ENTER
    for e in events:
        d = e["dt"].date()
        if d != last_day:
            last_day, nxt = d, ENTER
        if e.get("type") is None:
            e["type"] = nxt
        nxt = EXIT if e["type"] == ENTER else ENTER
    return events


def _dedup_same_pass(events: list[dict], window: int = 30) -> list[dict]:
    """Bitta o'tishda qurilma bir necha marta yozsa (yuz qayta o'qilsa) — bittaga."""
    out = []
    for e in sorted(events, key=lambda x: x["dt"]):
        if out and e.get("dev") == out[-1].get("dev") and \
                (e["dt"] - out[-1]["dt"]).total_seconds() <= window:
            continue
        out.append(e)
    return out


# ═════════════════════ HIKVISION (ISAPI) ═════════════════════
class Hikvision:
    """ISAPI: POST /ISAPI/AccessControl/AcsEvent?format=json (Digest auth)."""

    def __init__(self, dev: dict):
        self.dev = dev
        self.base = f"{dev.get('scheme', 'http')}://{dev['host']}:{int(dev.get('port') or 80)}"
        self._cache: dict = {}
        self._fetch_lock = threading.Lock()

    def _session(self):
        import requests
        from requests.auth import HTTPDigestAuth
        s = requests.Session()
        s.auth = HTTPDigestAuth(self.dev.get("user", "admin"), _password(self.dev))
        s.verify = False
        return s

    def info(self) -> str:
        s = self._session()
        r = s.get(self.base + "/ISAPI/System/deviceInfo", timeout=TIMEOUT)
        r.raise_for_status()
        txt = r.text
        import re
        g = lambda tag: (re.search(f"<{tag}>([^<]*)</{tag}>", txt) or [None, "?"])[1]
        return f"{g('deviceName')} · {g('model')} · {g('serialNumber')} · firmware {g('firmwareVersion')}"

    def _query(self, start: datetime, end: datetime, emp: str | None = None) -> list[dict]:
        s = self._session()
        tz = datetime.now().astimezone().strftime("%z")
        tz = tz[:3] + ":" + tz[3:]
        sid = uuid.uuid4().hex[:16]
        pos, out = 0, []
        for _ in range(500):                      # himoya: cheksiz aylanmasin
            cond = {"searchID": sid, "searchResultPosition": pos, "maxResults": 30,
                    "major": 5, "minor": 0,
                    "startTime": start.strftime("%Y-%m-%dT%H:%M:%S") + tz,
                    "endTime": end.strftime("%Y-%m-%dT%H:%M:%S") + tz}
            if emp:
                cond["employeeNoString"] = emp
            r = s.post(self.base + "/ISAPI/AccessControl/AcsEvent?format=json",
                       json={"AcsEventCond": cond}, timeout=TIMEOUT)
            r.raise_for_status()
            ev = (r.json() or {}).get("AcsEvent") or {}
            items = ev.get("InfoList") or []
            for it in items:
                no = str(it.get("employeeNoString") or it.get("employeeNo") or "").strip()
                if not no:
                    continue                      # tanilmagan yuz / eshik hodisasi
                try:
                    dt = _local(datetime.fromisoformat(str(it.get("time"))))
                except Exception:
                    continue
                st = str(it.get("attendanceStatus") or "").lower()
                out.append({"emp": no, "dt": dt, "status": st, "name": it.get("name", "")})
            pos += len(items)
            status = str(ev.get("responseStatusStrg") or "").upper()
            if status != "MORE" or not items:
                break
        return out

    def events(self, start: datetime, end: datetime, emp: str | None = None) -> list[dict]:
        key = (start, end, emp)
        with self._fetch_lock:                    # parallel oqimlar bir xil so'rovni takrorlamasin
            hit = self._cache.get(key)
            if hit and time.time() - hit[0] < CACHE_TTL:
                return hit[1]
            rows = self._query(start, end, emp)
            if len(self._cache) > 400:
                self._cache.clear()
            self._cache[key] = (time.time(), rows)
            return rows

    def direction(self, row: dict):
        d = str(self.dev.get("direction") or "auto").lower()
        if d in ("in", "kirish"):
            return ENTER
        if d in ("out", "chiqish"):
            return EXIT
        st = row.get("status", "")
        if st in ("checkin", "breakin", "overtimein"):
            return ENTER
        if st in ("checkout", "breakout", "overtimeout"):
            return EXIT
        return None


# ═════════════════════ ZKTECO (pyzk, 4370-port) ═════════════════════
class ZKTeco:
    """pyzk orqali: qurilmadagi barcha yozuvlar bir marta o'qiladi va keshlanadi."""

    def __init__(self, dev: dict):
        self.dev = dev
        self._cache = (0.0, [])
        self._fetch_lock = threading.Lock()

    def _connect(self):
        from zk import ZK                          # pip install pyzk
        pw = _password(self.dev)
        zk = ZK(self.dev["host"], port=int(self.dev.get("port") or 4370), timeout=int(TIMEOUT),
                password=int(pw) if pw.isdigit() else 0, force_udp=bool(self.dev.get("udp")),
                ommit_ping=True)
        return zk.connect()

    def info(self) -> str:
        conn = self._connect()
        try:
            return (f"{conn.get_device_name()} · seriya {conn.get_serialnumber()} · "
                    f"firmware {conn.get_firmware_version()} · {len(conn.get_users())} foydalanuvchi")
        finally:
            conn.disconnect()

    def _all(self) -> list[dict]:
        with self._fetch_lock:
            if time.time() - self._cache[0] < max(CACHE_TTL, 15):
                return self._cache[1]
            return self._fetch_all()

    def _fetch_all(self) -> list[dict]:
        conn = self._connect()
        try:
            recs = conn.get_attendance() or []
        finally:
            try:
                conn.disconnect()
            except Exception:
                pass
        rows = [{"emp": str(r.user_id).strip(), "dt": _local(r.timestamp),
                 "punch": getattr(r, "punch", None)} for r in recs]
        self._cache = (time.time(), rows)
        return rows

    def events(self, start: datetime, end: datetime, emp: str | None = None) -> list[dict]:
        return [r for r in self._all() if start <= r["dt"] <= end and (emp is None or r["emp"] == emp)]

    def direction(self, row: dict):
        d = str(self.dev.get("direction") or "auto").lower()
        if d in ("in", "kirish"):
            return ENTER
        if d in ("out", "chiqish"):
            return EXIT
        if self.dev.get("use_punch"):
            p = row.get("punch")
            if p in (0, 3, 4):
                return ENTER
            if p in (1, 2, 5):
                return EXIT
        return None


_DEVICES: dict = {"mtime": None, "list": []}


def devices() -> list:
    try:
        mt = DEVICES_FILE.stat().st_mtime
    except Exception:
        mt = None
    if _DEVICES["mtime"] != mt:
        objs = []
        for d in load_devices():
            t = str(d.get("type") or "").lower()
            if t.startswith("hik"):
                objs.append(Hikvision(d))
            elif t.startswith("zk"):
                objs.append(ZKTeco(d))
            else:
                print(f"[FACEID] noma'lum qurilma turi: {t}")
        _DEVICES.update(mtime=mt, list=objs)
    return _DEVICES["list"]


def device_events(card, start_date: str, end_date: str) -> list[dict]:
    """Barcha qurilmalardan bitta xodimning hodisalari: [{"dt", "type"}]."""
    emp = device_id(card)
    a = datetime.strptime(str(start_date)[:10], "%Y-%m-%d")
    b = datetime.strptime(str(end_date)[:10], "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)
    single_day = (b - a).days < 1
    out = []
    for dev in devices():
        try:
            # Bir kunlik so'rov (jonli) — butun kun bir marta olinib, hammaga ulashiladi
            rows = dev.events(a, b, None) if single_day else dev.events(a, b, emp)
        except Exception as e:
            print(f"[FACEID] {dev.dev.get('name') or dev.dev.get('host')}: {type(e).__name__}: {e}")
            continue
        for r in rows:
            if r["emp"] != emp:
                continue
            out.append({"dt": r["dt"], "type": dev.direction(r),
                        "dev": dev.dev.get("host"), "raw_type": ""})
    out = _dedup_same_pass(out)
    return _assign_directions(out)


def ping() -> bool:
    ok = False
    for dev in devices():
        try:
            dev.info()
            ok = True
        except Exception:
            pass
    return ok


# ═════════════════════ DEMO (qurilmasiz sinov) ═════════════════════
def demo_events(card, start_date: str, end_date: str) -> list[dict]:
    """Har xodim uchun barqaror (har safar bir xil) soxta kirish/chiqish.
    Faqat ish kunlari; ~8% kelmagan, ~15% kechikkan. Bugun — faqat hozirgacha."""
    a = datetime.strptime(str(start_date)[:10], "%Y-%m-%d").date()
    b = datetime.strptime(str(end_date)[:10], "%Y-%m-%d").date()
    now = datetime.now()
    out = []
    d = a
    while d <= b:
        if d.weekday() < 5 and d <= now.date():
            seed = int(hashlib.md5(f"{card}|{d}".encode()).hexdigest()[:8], 16)
            rnd = random.Random(seed)
            if rnd.random() > 0.08:
                late = rnd.random() < 0.15
                arr = datetime(d.year, d.month, d.day, 8, 30) + timedelta(
                    minutes=rnd.randint(25, 75) if late else rnd.randint(0, 28))
                lo = datetime(d.year, d.month, d.day, 13, 0) + timedelta(minutes=rnd.randint(0, 15))
                li = lo + timedelta(minutes=rnd.randint(30, 55))
                lv = datetime(d.year, d.month, d.day, 17, 55) + timedelta(minutes=rnd.randint(0, 50))
                seq = [(arr, ENTER)]
                if rnd.random() < 0.6:
                    seq += [(lo, EXIT), (li, ENTER)]
                seq.append((lv, EXIT))
                out += [{"dt": t, "type": k, "raw_type": ""} for t, k in seq if t <= now]
        d += timedelta(days=1)
    return out
