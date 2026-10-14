"""
biocontrol_api.py — KIRISH/CHIQISH MA'LUMOTLARI MANBASI (yagona kirish nuqtasi).

Butun tizim (jonli dashboard, oylik hisobot, ilova) hodisalarni shu moduldan oladi.
Manba .env dagi FACEID_SOURCE bilan tanlanadi:
  devices     — FaceID qurilmalari (Hikvision / ZKTeco), faceid_devices.json  [faceid_devices.py]
  demo        — qurilmasiz sinov uchun soxta ma'lumot
  nvr_reports — NVR'dan qo'lda eksport qilingan Attendance Day Report (.xls),
                nvr_reports/ papkasidan o'qiladi  [nvr_report_import.py]
  biocontrol  — OneDesk / BioControl (enter.mininnovation.uz) API (pastda)

--- BioControl API haqida ---

API (aniqlangan format):
  POST http://enter.mininnovation.uz/api.php   (body: raw JSON)

  1) Kirish/chiqish tarixi (asosiy):
     {
       "action": "get_reports",
       "card":   "<jshshir>",          # 14 xonali
       "type":   "1",                  # 1 = KIRISH, 2 = CHIQISH
       "start":  "2026-07-01 00:00:00",
       "end":    "2026-07-06 23:59:59"
     }
     Javob: {"status": true, "reports": [
                {"id":"535","card":"...","ip":"...","type":"1","dt":"2026-07-01 09:25:55"}, ...
            ]}

  2) Bugungi kunlik holat (qo'shimcha):
     {"action":"attendance","cards":[<jshshir>, ...]}
     Javob: {"status": true, "attendance":[
                {"name":"...","card":"...","dt":"...","before_9_15":false,
                 "between_9_15_9_30":false,"after_9_30":true,"absent":false}, ...
            ]}

Bu modul hodisalarni analyze_biocontrol.py kutadigan formatga o'giradi:
  {"dt": datetime, "type": "вход"/"выход"}
shunda mavjud hisoblash mantig'i (calc_day_minutes, kechikish) o'zgarishsiz ishlaydi.
"""

import os
import time
import requests
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

SOURCE = os.getenv("FACEID_SOURCE", "demo").strip().lower()
BIOCONTROL_URL = os.getenv("BIOCONTROL_API_URL", "https://enter.mininnovation.uz/api.php")
API_URL = {"devices": "FaceID qurilmalari (faceid_devices.json)",
           "demo": "DEMO — soxta ma'lumot (FACEID_SOURCE=demo)",
           "nvr_reports": "NVR eksport fayllari (nvr_reports/)"}.get(SOURCE, BIOCONTROL_URL)
TIMEOUT = 30
RETRIES = 3
RETRY_DELAY = 2.0  # soniya

# type kodlari -> rus tilidagi belgilar (worker.py / analyze bilan mos)
TYPE_ENTER = "1"   # KIRISH  -> "вход"
TYPE_EXIT = "2"    # CHIQISH -> "выход"
LABEL_ENTER = "вход"
LABEL_EXIT = "выход"


def _session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "biocontrol-client/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    return s


_SESSION = _session()

# Har bir oqim (thread) o'z ulanishidan foydalanadi — parallel so'rovlar
# bir-biriga xalal bermasin (live_worker xodimlarni parallel so'raydi).
import threading as _threading
_TL = _threading.local()


def _sess():
    s = getattr(_TL, "s", None)
    if s is None:
        s = _session()
        _TL.s = s
    return s


def _post(payload):
    """API'ga POST (JSON). Xatoga chidamli — RETRIES marta urinadi."""
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            r = _sess().post(BIOCONTROL_URL, json=payload, timeout=TIMEOUT)
            r.raise_for_status()
            # javob JSON bo'lmasligi mumkin — himoyalanamiz
            try:
                return r.json()
            except ValueError:
                return {"status": False, "_raw": r.text[:500]}
        except Exception as e:
            last_err = e
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY)
    # barcha urinishlar muvaffaqiyatsiz
    return {"status": False, "_error": str(last_err)}


def _fmt_card(card):
    """Jshshir'ni 14 xonali matnga o'giradi (butun son bo'lsa ham)."""
    s = str(card).strip()
    # faqat raqamlar
    s = "".join(ch for ch in s if ch.isdigit())
    return s


def get_reports(card, type_code, start_date, end_date):
    """Bitta card + bitta type uchun xom hodisalar ro'yxati.
    start_date / end_date: "YYYY-MM-DD" ko'rinishida.
    Qaytaradi: reports list (bo'sh bo'lsa [])."""
    payload = {
        "action": "get_reports",
        "card": _fmt_card(card),
        "type": str(type_code),
        "start": f"{start_date} 00:00:00",
        "end": f"{end_date} 23:59:59",
    }
    data = _post(payload)
    if not isinstance(data, dict) or not data.get("status"):
        return []
    return data.get("reports", []) or []


DEDUP_WINDOW_SECONDS = 90  # bir xil turdagi hodisa shu oraliqda takror bo'lsa — bittaga


def _dedup_events(events):
    """Bir xil turdagi (kirish yoki chiqish) va DEDUP_WINDOW ichida takrorlangan
    hodisalarni bittaga birlashtiradi. Bir necha turniket/eshik bir odam o'tganda
    bir necha marta yozishi mumkin — shuni tozalaydi. (events tartiblangan bo'lishi kerak)"""
    out = []
    for ev in events:
        if out:
            last = out[-1]
            same_type = last["type"] == ev["type"]
            gap = abs((ev["dt"] - last["dt"]).total_seconds())
            if same_type and gap <= DEDUP_WINDOW_SECONDS:
                continue  # takror — o'tkazamiz
        out.append(ev)
    return out


def get_events(card, start_date, end_date):
    """Bitta xodimning KIRISH+CHIQISH hodisalarini birlashtirib qaytaradi.

    Natija (vaqt bo'yicha tartiblangan, takrorlar tozalangan):
      [{"dt": datetime, "type": "вход"|"выход", "raw_type": "1"|"2"}, ...]
    """
    if SOURCE in ("devices", "demo"):
        import faceid_devices as _fd
        events = (_fd.device_events(card, start_date, end_date) if SOURCE == "devices"
                  else _fd.demo_events(card, start_date, end_date))
        events.sort(key=lambda x: x["dt"])
        return _apply_entry_overrides(card, start_date, end_date, _dedup_events(events))
    if SOURCE == "nvr_reports":
        import faceid_devices as _fd
        import nvr_report_import as _nri
        work_no = _fd.device_id(card)
        events = _nri.events_for_workno(work_no, start_date, end_date)
        events.sort(key=lambda x: x["dt"])
        return _apply_entry_overrides(card, start_date, end_date, _dedup_events(events))
    events = []
    for code, label in ((TYPE_ENTER, LABEL_ENTER), (TYPE_EXIT, LABEL_EXIT)):
        for rec in get_reports(card, code, start_date, end_date):
            dt_str = str(rec.get("dt", ""))[:19]
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            events.append({"dt": dt, "type": label, "raw_type": code})
    events.sort(key=lambda x: x["dt"])
    return _apply_entry_overrides(card, start_date, end_date, _dedup_events(events))


# ── super_admin qarori bilan kirish/chiqish vaqtini tuzatish ─────
# entry_overrides.json:
#   {"2026-10-09": {"<JSHSHIR>": {"in": "09:01", "out": "18:30", "izoh": "..."}}}
# "in" — shu kuni BIRINCHI kirish, "out" — shu kuni OXIRGI chiqish deb
# olinadi (ikkalasi ham ixtiyoriy — faqat birini tuzatish ham mumkin).
# Hamma joyda bir xil ishlaydi: jonli dashboard, oylik hisobot, reyting,
# KPI, xodimning ilovadagi kunlari — chunki hammasi shu funksiyadan o'qiydi.
from pathlib import Path as _Path
ENTRY_OVERRIDES_FILE = _Path("entry_overrides.json")
_OVR_CACHE = {"mtime": None, "data": {}}


def _entry_overrides():
    try:
        mt = ENTRY_OVERRIDES_FILE.stat().st_mtime
    except Exception:
        return {}
    if _OVR_CACHE["mtime"] != mt:
        try:
            import json as _json
            raw = _json.loads(ENTRY_OVERRIDES_FILE.read_text(encoding="utf-8")) or {}
        except Exception:
            raw = {}
        data = {}
        for day, cards in (raw.items() if isinstance(raw, dict) else []):
            if not isinstance(cards, dict):
                continue
            for c, v in cards.items():
                if not isinstance(v, dict):
                    continue
                times = {}
                for key in ("in", "out"):
                    hm = v.get(key)
                    if not hm:
                        continue
                    try:
                        times[key] = datetime.strptime(str(hm).strip()[:5], "%H:%M").time()
                    except Exception:
                        continue
                if times:
                    data.setdefault(_fmt_card(c).lstrip("0"), {})[str(day)[:10]] = times
        _OVR_CACHE.update(mtime=mt, data=data)
    return _OVR_CACHE["data"]


def _apply_entry_overrides(card, start_date, end_date, events):
    ovr = _entry_overrides().get(_fmt_card(card).lstrip("0"))
    if not ovr:
        return events
    a, b = str(start_date)[:10], str(end_date)[:10]
    changed = False
    for day, times in ovr.items():
        if not (a <= day <= b):
            continue
        if "in" in times:
            t = times["in"]
            new_dt = datetime.strptime(day, "%Y-%m-%d").replace(hour=t.hour, minute=t.minute)
            first = next((e for e in events if e["dt"].strftime("%Y-%m-%d") == day
                          and e["type"] == LABEL_ENTER), None)
            if first is not None:
                first["dt"] = new_dt
                first["override"] = True
            else:
                # O'sha kuni kirish yozuvi yo'q — qo'lda kirish qo'shiladi
                events.append({"dt": new_dt, "type": LABEL_ENTER, "raw_type": TYPE_ENTER,
                               "override": True})
            changed = True
        if "out" in times:
            t = times["out"]
            new_dt = datetime.strptime(day, "%Y-%m-%d").replace(hour=t.hour, minute=t.minute)
            # o'sha kundagi OXIRGI chiqish hodisasini topamiz
            last = None
            for e in events:
                if e["dt"].strftime("%Y-%m-%d") == day and e["type"] == LABEL_EXIT:
                    last = e
            if last is not None:
                last["dt"] = new_dt
                last["override"] = True
            else:
                # O'sha kuni chiqish yozuvi yo'q — qo'lda chiqish qo'shiladi
                events.append({"dt": new_dt, "type": LABEL_EXIT, "raw_type": TYPE_EXIT,
                               "override": True})
            changed = True
    if changed:
        events.sort(key=lambda x: x["dt"])
    return events


def get_events_by_day(card, start_date, end_date):
    """get_events natijasini kun bo'yicha guruhlaydi:
       {"2026-07-01": [ev, ev, ...], ...}"""
    from collections import defaultdict
    days = defaultdict(list)
    for ev in get_events(card, start_date, end_date):
        days[ev["dt"].strftime("%Y-%m-%d")].append(ev)
    return dict(days)


def attendance(cards):
    """Bugungi kunlik holat (bir yoki bir nechta card).
       cards: list of jshshir.
       Qaytaradi: attendance list."""
    if SOURCE != "biocontrol":
        return []
    payload = {
        "action": "attendance",
        "cards": [int(_fmt_card(c)) for c in cards if _fmt_card(c)],
    }
    data = _post(payload)
    if not isinstance(data, dict) or not data.get("status"):
        return []
    return data.get("attendance", []) or []


def ping(sample_card, sample_date):
    """API tirikligini tekshirish. True/False."""
    if SOURCE == "demo":
        return True
    if SOURCE == "devices":
        import faceid_devices as _fd
        return _fd.ping()
    if SOURCE == "nvr_reports":
        import nvr_report_import as _nri
        return _nri.ping()
    payload = {
        "action": "get_reports",
        "card": _fmt_card(sample_card),
        "type": "1",
        "start": f"{sample_date} 00:00:00",
        "end": f"{sample_date} 23:59:59",
    }
    data = _post(payload)
    return isinstance(data, dict) and data.get("status") is True


# ─── Qo'lda test uchun ───
if __name__ == "__main__":
    import sys
    card = sys.argv[1] if len(sys.argv) > 1 else "99999999999999"
    start = sys.argv[2] if len(sys.argv) > 2 else "2026-07-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2026-07-06"
    print(f"Test: card={card}  {start}..{end}")
    print("API tirik:", ping(card, start))
    evs = get_events(card, start, end)
    print(f"Jami hodisa: {len(evs)}")
    for ev in evs[:20]:
        print(f"  {ev['dt']}  {ev['type']}")
