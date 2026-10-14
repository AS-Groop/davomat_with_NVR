"""
live_worker_api.py — JONLI kirdi/chiqdi (API orqali, Playwright'siz).

Bu worker.py NING O'RNINI bosadi:
  • BioControl saytiga brauzer bilan kirish YO'Q (Playwright kerak emas)
  • Excel yuklab olish YO'Q
  • To'g'ridan-to'g'ri enter.mininnovation.uz API'dan har N sekundda o'qiydi
  • worker.py yozadigan AYNAN BIR XIL live_cache.json ni yozadi

Natijada:
  ✅ Dashboard jonli kirdi/chiqdi ko'rsatadi (live_cache.json ni o'qiydi)
  ✅ Bot ham ulanadi (u ham live_cache.json ni o'qiydi)

Ishga tushirish:
    python live_worker_api.py

start_all.py da "python worker.py" o'rniga "python live_worker_api.py" yozing.

.env sozlamalari (ixtiyoriy):
    WORKER_POLL_SECONDS=10      # necha sekundda yangilansin
    WORK_START=09:00:00         # standart ish boshlanishi
    LATE_GRACE_MINUTES=15       # kechikish imtiyozi
    LUNCH_START=13:00:00
    LUNCH_END=14:00:00
"""

import os
import re
import json
import time as time_module
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import Any

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import biocontrol_api as api
import interns_auto

try:
    import roles as _roles
except Exception:
    _roles = None


def _is_workday(day_str):
    """Ish kunimi? Shanba/Yakshanba va bayramlar ish kuni EMAS."""
    d10 = str(day_str)[:10]
    if _roles is not None:
        try:
            return _roles.is_working_day(d10)
        except Exception:
            pass
    try:
        return datetime.strptime(d10, "%Y-%m-%d").weekday() < 5
    except Exception:
        return True


# ─── Sozlamalar (worker.py bilan bir xil) ───
POLL_SECONDS = int(os.getenv("WORKER_POLL_SECONDS", "10"))
DEFAULT_WORK_START = os.getenv("WORK_START", "09:00:00").strip()
LATE_GRACE_MINUTES = int(os.getenv("LATE_GRACE_MINUTES", "15"))
LUNCH_START = os.getenv("LUNCH_START", "13:00:00").strip()
LUNCH_END = os.getenv("LUNCH_END", "14:00:00").strip()

BASE_DIR = Path(".")
CACHE_FILE = BASE_DIR / "live_cache.json"
# HR bot orqali belgilangan ish vaqtlari (users.xlsx ga tegmasdan).
# Format: {"<card>": "HH:MM:SS", ...}. Bo'sh/yo'q bo'lsa — Excel'dagi work_start ishlatiladi.
WORK_OVERRIDES_FILE = BASE_DIR / "work_overrides.json"
EMPLOYEE_FILE_CANDIDATES = [
    BASE_DIR / "users.xlsx",
    BASE_DIR / "users(2).xlsx",
    BASE_DIR / "employees.xlsx",
]

# Amaliyotchilar ALOHIDA faylda (users.xlsx da EMAS).
# Format users.xlsx bilan bir xil: familiya/ism/sharif + "card number" (jshshir).
INTERN_FILE_CANDIDATES = [
    BASE_DIR / "interns.xlsx",
    BASE_DIR / "amaliyotchilar.xlsx",
    BASE_DIR / "praktikantlar.xlsx",
]


def load_work_overrides() -> dict:
    """work_overrides.json -> {card: 'HH:MM:SS'} (HR bot yozadi)."""
    try:
        if WORK_OVERRIDES_FILE.exists():
            d = json.loads(WORK_OVERRIDES_FILE.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return {str(k): str(v) for k, v in d.items() if str(v).strip()}
    except Exception:
        pass
    return {}


def apply_work_overrides(employees) -> int:
    """Har xodimга: override bor bo'lsa work_start ni almashtiradi, aks holda
    Excel'dagi asl qiymatni tiklaydi. Qaytaradi: qo'llangan override soni."""
    ov = load_work_overrides()
    n = 0
    for e in employees:
        base = e.get("work_start_excel") or e.get("work_start")
        e["work_start_excel"] = base  # asl (Excel) qiymatni saqlab qo'yamiz
        card = str(e.get("card_number", ""))
        if card in ov:
            e["work_start"] = ov[card]
            n += 1
        else:
            e["work_start"] = base
    return n


# ─────────────────────────── VAQT YORDAMCHILARI ───────────────────────────

def parse_hms(value: str) -> time:
    return datetime.strptime(value, "%H:%M:%S").time()


def parse_work_start(value) -> time:
    s = str(value or "").strip()
    if not s or s.lower() == "nan":
        s = DEFAULT_WORK_START
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except Exception:
            continue
    try:
        frac = float(s)
        if 0 <= frac < 1:
            total_min = int(round(frac * 24 * 60))
            return time(total_min // 60, total_min % 60)
    except Exception:
        pass
    return time(9, 0)


# ── Kunlik imtiyoz ──────────────────────────────────────────────
# Ba'zan butun jamoa kechikadi (yo'l tirbandligi, ob-havo, umumiy tadbir).
# Shunday kunlarda HR bitta kun uchun imtiyoz belgilashi mumkin:
#   late_grace_days.json -> {"2026-09-07": {"until": "09:40"}}
# O'sha kuni ko'rsatilgan vaqtgacha kirgan xodim kechikkan hisoblanmaydi.
# Kelgan aniq vaqt o'zgarmaydi — faqat "kechikdi" belgisi qo'yilmaydi.
GRACE_DAYS_FILE = BASE_DIR / "late_grace_days.json"


def _grace_until(day_str: str):
    """Shu kun uchun imtiyoz vaqti (yoki None)."""
    if not day_str:
        return None
    try:
        with open(GRACE_DAYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        return None
    rec = data.get(str(day_str))
    if not rec:
        return None
    raw = rec.get("until") if isinstance(rec, dict) else rec
    m = re.match(r"(\d{1,2}):(\d{2})", str(raw or ""))
    if not m:
        return None
    try:
        return time(int(m.group(1)), int(m.group(2)), 59)
    except Exception:
        return None


def late_threshold_for(work_start: time, day_str: str = "") -> time:
    base = datetime(2000, 1, 1, work_start.hour, work_start.minute, 0)
    th = (base + timedelta(minutes=LATE_GRACE_MINUTES, seconds=59)).time()
    g = _grace_until(day_str)
    # Imtiyoz faqat yumshatadi: kimningdir ish boshlanishi kechroq bo'lsa,
    # uning o'z chegarasi saqlanadi.
    return max(th, g) if g else th


LUNCH_START_OBJ = parse_hms(LUNCH_START)
LUNCH_END_OBJ = parse_hms(LUNCH_END)
DEFAULT_WORK_START_OBJ = parse_work_start(DEFAULT_WORK_START)


def normalize_text(value) -> str:
    text = str(value or "").strip().lower()
    text = (text.replace("o\u2018", "o").replace("g\u2018", "g")
                .replace("o'", "o").replace("g'", "g")
                .replace("\u2019", "").replace("'", "").replace('"', ""))
    text = re.sub(r"[^a-z\u0430-\u044f\u04510-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ─────────────────────────── XODIMLAR (users.xlsx) ───────────────────────────

def _norm_col(c):
    return normalize_text(c).replace(" ", "_")


def _detect_header_row(df_raw):
    keys = ["familiya", "familya", "ism", "sharif", "card", "telegram", "role", "category", "active"]
    best_idx, best = 0, -1
    for i in range(min(15, len(df_raw))):
        txt = " ".join(normalize_text(x) for x in df_raw.iloc[i].tolist())
        sc = sum(1 for k in keys if k in txt)
        if sc > best:
            best, best_idx = sc, i
    return best_idx


def find_existing_employee_file():
    for p in EMPLOYEE_FILE_CANDIDATES:
        if p.exists():
            return p
    return None


def load_employees() -> list[dict]:
    """users.xlsx -> [{full_name, full_name_norm, card_number, role, telegram_id, work_start}]
    (worker.py load_employees bilan bir xil natija)."""
    path = find_existing_employee_file()
    if not path:
        return []
    df_prev = pd.read_excel(path, header=None)
    hdr = _detect_header_row(df_prev)
    df = pd.read_excel(path, header=hdr)
    df.columns = [_norm_col(c) for c in df.columns]

    def get(row, *names):
        for n in names:
            if n in row and pd.notna(row[n]):
                return row[n]
        return ""

    emps = []
    for _, r in df.iterrows():
        row = r.to_dict()
        ln = str(get(row, "familiya", "last_name", "familya")).strip()
        fn = str(get(row, "ism", "first_name", "name")).strip()
        mn = str(get(row, "sharif", "middle_name", "otchestvo")).strip()
        full = " ".join(x for x in [ln, fn, mn] if x).strip()

        card_raw = str(get(row, "card_number", "cardnumber", "card", "karta_raqami")).strip()
        card = "".join(ch for ch in card_raw if ch.isdigit())
        if card_raw and "." in card_raw and card:
            try:
                card = str(int(float(card_raw)))
            except Exception:
                pass

        role = str(get(row, "role", "lavozim_turi")).strip().lower() or "employee"
        category = str(get(row, "category", "turkum", "kategoriya")).strip().lower() or "oddiy"
        active_raw = str(get(row, "active", "is_active", "faol")).strip().lower()
        tg_raw = str(get(row, "telegram_id", "telegram", "telegramid", "tg_id")).strip()
        ws_raw = get(row, "work_start", "ish_boshlanishi", "ish_vaqti", "start_time", "boshlanish")

        is_active = active_raw not in {"0", "false", "no", "inactive", "off", "yoq", "yo\u2018q"}
        tg_id = int(tg_raw) if tg_raw.isdigit() else None

        if not full or not card or role == "admin" or not is_active:
            continue

        ws = parse_work_start(ws_raw) if str(ws_raw).strip() else DEFAULT_WORK_START_OBJ
        emps.append({
            "full_name": full,
            "full_name_norm": normalize_text(full),
            "card_number": card,
            "role": role,
            "category": category,
            "active": True,
            "telegram_id": tg_id,
            "work_start": ws.strftime("%H:%M:%S"),
        })
    return emps


# ─────────────────────────── AMALIYOTCHILAR (interns.xlsx) ───────────────────────────

def find_intern_file():
    for p in INTERN_FILE_CANDIDATES:
        if p.exists():
            return p
    return None


INACTIVE_INTERNS_FILE = BASE_DIR / "interns_inactive.json"
INTERNS_ROSTER_FILE = BASE_DIR / "interns_roster.json"


def _load_inactive_interns() -> set:
    """HR mobil orqali 'faol emas' belgilagan amaliyotchi kartalari."""
    try:
        data = json.loads(INACTIVE_INTERNS_FILE.read_text(encoding="utf-8"))
        return set(str(c) for c in data.get("cards", []))
    except Exception:
        return set()


def _save_intern_roster(roster: list) -> None:
    """To'liq amaliyotchi ro'yxati (faol+nofaol) — boshqaruv paneli shundan o'qiydi."""
    try:
        tmp = INTERNS_ROSTER_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"interns": roster}, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(INTERNS_ROSTER_FILE)
    except Exception:
        pass


def load_interns() -> list[dict]:
    """interns.xlsx -> [{full_name, card_number}] (faqat FAOL amaliyotchilar).
    'Faol emas' belgilanganlar (interns_inactive.json yoki xlsx 'faol' ustuni) chiqariladi.
    To'liq ro'yxat interns_roster.json ga yoziladi (boshqaruv paneli uchun)."""
    path = find_intern_file()
    if not path:
        _save_intern_roster([])
        return []
    try:
        df_prev = pd.read_excel(path, header=None)
        hdr = _detect_header_row(df_prev)
        df = pd.read_excel(path, header=hdr)
        df.columns = [_norm_col(c) for c in df.columns]
    except Exception:
        return []

    def get(row, *names):
        for n in names:
            if n in row and pd.notna(row[n]):
                return row[n]
        return ""

    inactive_json = _load_inactive_interns()
    auto_off = interns_auto.auto_cards()      # 10 kun kelmagani uchun avtomatik nofaol
    _INACTIVE_WORDS = {"0", "false", "no", "inactive", "off", "yoq", "yo‘q",
                       "нет", "неактив", "faol emas", "nofaol", "-"}
    interns = []
    roster = []
    for _, r in df.iterrows():
        row = r.to_dict()
        ln = str(get(row, "familiya", "last_name", "familya")).strip()
        fn = str(get(row, "ism", "first_name", "name")).strip()
        mn = str(get(row, "sharif", "middle_name", "otchestvo")).strip()
        full = " ".join(x for x in [ln, fn, mn] if x).strip()
        card_raw = str(get(row, "card_number", "cardnumber", "card", "karta_raqami")).strip()
        card = "".join(ch for ch in card_raw if ch.isdigit())
        if card_raw and "." in card_raw and card:
            try:
                card = str(int(float(card_raw)))
            except Exception:
                pass
        if not full or not card:
            continue
        # 'Faol emas' — xlsx 'faol' ustuni yoki HR (interns_inactive.json) orqali
        active_raw = str(get(row, "active", "is_active", "faol", "holat", "status")).strip().lower()
        xlsx_off = active_raw in _INACTIVE_WORDS
        is_inactive = xlsx_off or (card in inactive_json) or (card in auto_off)
        reason = ("xlsx" if xlsx_off else "manual" if card in inactive_json
                  else "auto" if card in auto_off else "")
        roster.append({"card_number": card, "full_name": full, "active": not is_inactive,
                       "reason": reason})
        if is_inactive:
            continue
        interns.append({
            "full_name": full,
            "full_name_norm": normalize_text(full),
            "card_number": card,
        })
    _save_intern_roster(roster)
    return interns


def calc_inside_minutes(events, now_dt) -> int:
    """Bugun jami ichkarida bo'lgan daqiqalar. Ochiq sessiya (hali ichkarida)
    hozirgi vaqtgача hisoblanadi."""
    evs = sorted(events, key=lambda x: x["dt"])
    total = 0
    open_in = None
    for ev in evs:
        t = ev["type"].lower()
        if "вход" in t:
            if open_in is None:
                open_in = ev["dt"]
        elif "выход" in t:
            if open_in is not None:
                d = int((ev["dt"] - open_in).total_seconds() // 60)
                if d > 0:
                    total += d
                open_in = None
    if open_in is not None:  # hali ichkarida — hozirgача
        d = int((now_dt - open_in).total_seconds() // 60)
        if d > 0:
            total += d
    if total > 16 * 60:
        total = 16 * 60
    return total


def build_intern_rows(interns, day_str) -> list[dict]:
    """Har amaliyotchi uchun bugungi kirish/chiqish + ichkarida bo'lgan soat."""
    now_dt = datetime.now()
    rows = []
    all_events = _parallel_events([it["card_number"] for it in interns], day_str)
    for it, events in zip(interns, all_events):
        card = it["card_number"]
        # timeline
        timeline = []
        first_entry = None
        last_exit = None
        for ev in events:
            t = ev["type"].lower()
            kind = "in" if "вход" in t else ("out" if "выход" in t else "other")
            timeline.append({"time": ev["dt"].strftime("%H:%M:%S"), "kind": kind})
            if kind == "in" and first_entry is None:
                first_entry = ev["dt"]
            if kind == "out":
                last_exit = ev["dt"]   # oxirgi chiqish (har safar yangilanadi)

        if not events:
            status = "kelmagan"
            last_time = "-"
        else:
            last = events[-1]
            last_time = last["dt"].strftime("%H:%M:%S")
            status = "ichkarida" if "вход" in last["type"].lower() else "chiqgan"

        mins = calc_inside_minutes(events, now_dt)
        rows.append({
            "full_name": it["full_name"],
            "card_number": card,
            "status": status,
            "first_entry": first_entry.strftime("%H:%M:%S") if first_entry else "-",
            "last_exit": last_exit.strftime("%H:%M:%S") if last_exit else "-",
            "last_event_time": last_time,
            "minutes_inside": mins,
            "hours_inside_str": f"{mins // 60}:{mins % 60:02d}",
            "timeline": timeline,
        })
    # ── TARTIB ──
    # 1) Ichkaridagilar (hozir binoda) — eng tepada
    # 2) Chiqib ketganlar
    # 3) Kelmaganlar — eng pastda
    # Har guruh ichida: BINOGA BIRINCHI KIRGAN BIRINCHI (erta kirish yuqorida)
    _order = {"ichkarida": 0, "chiqgan": 1, "kelmagan": 2}

    def _sort_key(r):
        grp = _order.get(r.get("status"), 3)
        fe = r.get("first_entry") or "-"
        if fe == "-":                        # kelmaganlarda vaqt yo'q
            return (grp, "99:99:99", r["full_name"])
        return (grp, fe, r["full_name"])

    rows.sort(key=_sort_key)
    return rows


def find_employee_by_name(employees, name):
    target = normalize_text(name)
    for e in employees:
        if e["full_name_norm"] == target:
            return e
    for e in employees:
        if target in e["full_name_norm"] or e["full_name_norm"] in target:
            return e
    tw = set(target.split())
    best, bs = None, 0
    for e in employees:
        sc = len(tw & set(e["full_name_norm"].split()))
        if sc > bs:
            best, bs = e, sc
    return best if bs >= 2 else None


# ─────────────── API'DAN attendance_rows (worker format) ───────────────

def parse_dt(value: str) -> datetime:
    return datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")


def fetch_attendance_rows(employees, day_str: str) -> list[dict]:
    """Bugungi (day_str) barcha xodimlar uchun kirish/chiqishlarni API'dan oladi.
    Qaytaradi: [{"name","card","type":"вход/выход","time":"YYYY-MM-DD HH:MM:SS"}, ...]
    (build_state aynan shu formatni kutadi). Takroriy hodisalar tozalangan."""
    rows = []
    # Xodimlar PARALLEL so'raladi (ilgari ketma-ket edi: 73 xodim x 2 so'rov
    # har siklni 3-5 daqiqaga cho'zardi). Natija tartibi o'zgarmaydi.
    events_by_emp = _parallel_events([e["card_number"] for e in employees], day_str)
    for emp, events in zip(employees, events_by_emp):
        card = emp["card_number"]
        # get_events — takroriy hodisalarni avtomatik tozalaydi (bir necha turniket)
        for ev in events:
            rows.append({
                "name": emp["full_name"],
                "card": card,
                "type": ev["type"],
                "time": ev["dt"].strftime("%Y-%m-%d %H:%M:%S"),
            })
    return rows


# Bir vaqtda nechta so'rov (API'ni haddan tashqari yuklamaslik uchun cheklangan)
API_THREADS = max(1, int(os.getenv("WORKER_API_THREADS", "8")))


def _parallel_events(cards, day_str) -> list:
    """Har karta uchun bugungi hodisalar — bir nechta oqimda. Tartib saqlanadi.
    Bitta kartada xato bo'lsa — o'sha karta uchun bo'sh ro'yxat."""
    from concurrent.futures import ThreadPoolExecutor

    def one(card):
        try:
            return api.get_events(card, day_str, day_str)
        except Exception as e:
            print(f"[API] {card}: {e}")
            return []
    if API_THREADS == 1 or len(cards) < 2:
        return [one(c) for c in cards]
    with ThreadPoolExecutor(max_workers=API_THREADS) as ex:
        return list(ex.map(one, cards))


# ─────────────────────────── HOLAT (worker.py bilan bir xil) ───────────────────────────

def build_state(employees, attendance_rows, is_today=True, day_str=None) -> dict:
    # Ish kunimi? (shanba/yakshanba/bayramда kechikish belgilanmaydi)
    _wday = _is_workday(day_str or datetime.now().strftime("%Y-%m-%d"))
    state = {}
    for emp in employees:
        state[emp["card_number"]] = {
            "employee": emp, "events": [], "first_entry": None,
            "last_event": None, "status": "kelmagan", "late": False,
        }
    by_card = {e["card_number"]: e for e in employees}

    for row in attendance_rows:
        emp = None
        card_value = str(row.get("card", "")).strip()
        if card_value and card_value in by_card:
            emp = by_card[card_value]
        if emp is None:
            emp = find_employee_by_name(employees, row.get("name", ""))
        if not emp:
            continue
        state[emp["card_number"]]["events"].append({
            "dt": parse_dt(row["time"]),
            "type": row["type"],
            "name": row.get("name", ""),
        })

    now_time = datetime.now().time()
    for item in state.values():
        item["events"].sort(key=lambda x: x["dt"])
        if not item["events"]:
            item["status"] = "kelmagan"
            continue
        first_entry = None
        for ev in item["events"]:
            if "вход" in ev["type"].lower():
                first_entry = ev["dt"]
                break
        item["first_entry"] = first_entry
        item["last_event"] = item["events"][-1]

        ws_str = item["employee"].get("work_start") or DEFAULT_WORK_START
        try:
            ws_obj = parse_work_start(ws_str)
        except Exception:
            ws_obj = DEFAULT_WORK_START_OBJ
        late_th = late_threshold_for(ws_obj, first_entry.strftime('%Y-%m-%d') if first_entry else '')

        if first_entry and first_entry.time() > late_th and _wday:
            item["late"] = True

        last_type = item["last_event"]["type"].lower()
        last_time = item["last_event"]["dt"].time()
        if "вход" in last_type:
            item["status"] = "ishda"
        elif "выход" in last_type:
            if is_today and (LUNCH_START_OBJ <= now_time < LUNCH_END_OBJ or LUNCH_START_OBJ <= last_time < LUNCH_END_OBJ):
                item["status"] = "tushlikda"
            else:
                item["status"] = "ishda_emas"
        else:
            item["status"] = "nomalum"
    return state


def to_public_rows(state, status_name) -> list[dict]:
    rows = []
    for item in state.values():
        if item["status"] != status_name:
            continue
        emp = item["employee"]
        rows.append({
            "full_name": emp["full_name"],
            "card_number": emp["card_number"],
            "telegram_id": emp.get("telegram_id"),
            "work_start": emp.get("work_start", DEFAULT_WORK_START),
            "status": item["status"],
            "first_entry": item["first_entry"].strftime("%H:%M:%S") if item["first_entry"] else "-",
            "last_event_time": item["last_event"]["dt"].strftime("%H:%M:%S") if item["last_event"] else "-",
        })
    rows.sort(key=lambda x: x["full_name"])
    return rows


def to_late_rows(state) -> list[dict]:
    rows = []
    for item in state.values():
        if not item["late"]:
            continue
        emp = item["employee"]
        rows.append({
            "full_name": emp["full_name"],
            "card_number": emp["card_number"],
            "telegram_id": emp.get("telegram_id"),
            "work_start": emp.get("work_start", DEFAULT_WORK_START),
            "status": item["status"],
            "first_entry": item["first_entry"].strftime("%H:%M:%S") if item["first_entry"] else "-",
            "last_event_time": item["last_event"]["dt"].strftime("%H:%M:%S") if item["last_event"] else "-",
        })
    rows.sort(key=lambda x: x["first_entry"], reverse=True)
    return rows


def to_all_employee_rows(state) -> list[dict]:
    rows = []
    for item in state.values():
        emp = item["employee"]
        timeline = []
        for ev in item.get("events", []):
            t = ev["type"].lower()
            kind = "in" if "вход" in t else ("out" if "выход" in t else "other")
            timeline.append({"time": ev["dt"].strftime("%H:%M:%S"), "kind": kind})
        rows.append({
            "full_name": emp["full_name"],
            "card_number": emp["card_number"],
            "telegram_id": emp.get("telegram_id"),
            "work_start": emp.get("work_start", DEFAULT_WORK_START),
            "status": item["status"],
            "first_entry": item["first_entry"].strftime("%H:%M:%S") if item["first_entry"] else "-",
            "last_event_time": item["last_event"]["dt"].strftime("%H:%M:%S") if item["last_event"] else "-",
            "timeline": timeline,
        })
    rows.sort(key=lambda x: x["full_name"])
    return rows


# ─────────────────────────── CHIQISH KUZATUVI (exit tracking) ───────────────────────────
# Avval Telegram bot (main17.py) yozardi. Bot olib tashlangach — shu yerda.
# mobile_api.py shu fayldan o'qib, xodimга "sababini yozing" so'rovini ko'rsatadi.

EXIT_TRACK_FILE = BASE_DIR / "exit_tracking.json"
EXIT_WARN_MIN = int(os.getenv("EXIT_WARN_MINUTES", "10"))


def _t_parse(s, default="09:00"):
    try:
        p = str(s or default).strip().split(":")
        return time(int(p[0]), int(p[1]) if len(p) > 1 else 0)
    except Exception:
        p = default.split(":")
        return time(int(p[0]), int(p[1]))


def _is_work_hours(dt=None):
    """Ish vaqtimi (tushlikdan tashqari)?"""
    t = (dt or datetime.now()).time()
    ws = _t_parse(os.getenv("WORK_START", "09:00"))
    we = _t_parse(os.getenv("WORK_END", "18:00"))
    ls = _t_parse(os.getenv("LUNCH_START", "13:00"))
    le = _t_parse(os.getenv("LUNCH_END", "14:00"))
    if not (ws <= t <= we):
        return False
    if ls <= t < le:
        return False
    return True


def _is_exempt_today(card, day_str):
    """Ruxsat/safari/tadbir/ta'tilda bo'lsa — chiqish kuzatilmaydi."""
    try:
        data = json.loads((BASE_DIR / "exemptions.json").read_text(encoding="utf-8"))
    except Exception:
        return False
    recs = data.get("records", []) if isinstance(data, dict) else []
    for r in recs:
        if not isinstance(r, dict) or r.get("active") is False:
            continue
        if str(r.get("card_number", "")) != str(card):
            continue
        df = str(r.get("date_from", ""))[:10]
        dt_ = str(r.get("date_to", "") or df)[:10]
        if df <= day_str <= (dt_ or df):
            return True
    return False


def update_exit_tracking(cache):
    """live_cache asosida exit_tracking.json ni yangilaydi.

    Xodim ish vaqtida binodan chiqib 10+ daqiqa qaytmasa — 'warned' belgilanadi.
    Shundan keyin mobil ilova unga "sababini yozing" so'rovini ko'rsatadi.
    """
    now_dt = datetime.now()
    day_str = now_dt.strftime("%Y-%m-%d")
    if not (_is_work_hours(now_dt) and _is_workday(day_str)):
        return
    try:
        track = json.loads(EXIT_TRACK_FILE.read_text(encoding="utf-8"))
        if not isinstance(track, dict):
            track = {}
    except Exception:
        track = {}

    threshold = EXIT_WARN_MIN * 60
    changed = False

    for row in cache.get("employees", []) or []:
        card = str(row.get("card_number", ""))
        if not card:
            continue
        # Faqat "oddiy" turkum — amaliyotchi/haydovchi/rahbardan so'ralmaydi
        ask = True
        if _roles is not None:
            try:
                ask = bool(_roles.should_ask_explanation(card))
            except Exception:
                ask = True
        if not ask or _is_exempt_today(card, day_str):
            if card in track:
                del track[card]
                changed = True
            continue

        status = row.get("status", "")
        last_ev = row.get("last_event_time", "-")

        if status in ("ishda_emas", "nomalum") and last_ev not in ("-", "", None):
            if card not in track:
                track[card] = {
                    "exit_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "full_name": row.get("full_name", "-"),
                    "last_event": last_ev,
                    "warned": False,
                }
                changed = True
            elif not track[card].get("warned"):
                try:
                    ex_dt = datetime.strptime(track[card]["exit_time"], "%Y-%m-%d %H:%M:%S")
                    elapsed = (now_dt - ex_dt).total_seconds()
                except Exception:
                    elapsed = 0
                if elapsed >= threshold:
                    track[card]["warned"] = True
                    changed = True
                    print(f"[CHIQISH] {track[card].get('full_name','-')} — "
                          f"{int(elapsed // 60)} daqiqa tashqarida (sabab so'raladi)")
        else:
            if card in track:
                del track[card]
                changed = True

    if changed:
        try:
            EXIT_TRACK_FILE.write_text(
                json.dumps(track, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[CHIQISH XATO] {e}")


# ─────────────────────────── HISOB AVTO-YARATISH ───────────────────────────

_LAST_SEED_KEY = None  # ortiqcha ishlamaslik uchun (xodimlar to'plami o'zgarmasa — o'tkazamiz)


def auto_seed_accounts(employees) -> int:
    """users.xlsx dagi har bir xodimga hisob (accounts.json) yo'q bo'lsa — yaratadi.

    • login = jshshir (card)
    • boshlang'ich parol = jshshirning oxirgi 6 raqami
    • must_change=True — xodim birinchi kirishда o'zgartiradi
    Mavjud hisoblar buzilmaydi. Yangi yaratilganlar new_accounts.txt ga qo'shiladi.
    """
    global _LAST_SEED_KEY
    try:
        import accounts
    except Exception as e:
        print(f"[SEED ERROR] accounts moduli yuklanmadi: {e}")
        return 0

    # Faqat kartalar to'plami o'zgarганда ishlaymiz (har siklda emas)
    cards = sorted(
        "".join(ch for ch in str(e.get("card_number", "")) if ch.isdigit())
        for e in employees
    )
    key = hash(tuple(cards))
    if key == _LAST_SEED_KEY:
        return 0

    try:
        existing = accounts.load_accounts()
    except Exception as e:
        print(f"[SEED ERROR] accounts.json o'qilmadi: {e}")
        return 0

    created = []
    for e in employees:
        card = "".join(ch for ch in str(e.get("card_number", "")) if ch.isdigit())
        if not card or card in existing:
            continue
        name = e.get("full_name", "") or ""
        role = (e.get("role") or "employee").lower()
        pw = card[-6:] if len(card) >= 6 else (card or "123456")
        try:
            if accounts.create_account(card, pw, name=name, role=role, must_change=True):
                created.append((name, card, pw, role))
        except Exception as ex:
            print(f"[SEED ERROR] {name} ({card}): {ex}")

    _LAST_SEED_KEY = key

    if created:
        print(f"[SEED] {len(created)} ta yangi xodimга hisob yaratildi:")
        for name, card, pw, role in created:
            print(f"       {name} | login={card} | parol={pw}")
        # Tarqatish uchun ro'yxatga qo'shib boramiz (qo'shimcha, ustiga yozmaymiz)
        try:
            line = "\n".join(f"{n} | {c} | {p} | {r}" for n, c, p, r in created)
            f = BASE_DIR / "new_accounts.txt"
            header = "" if f.exists() else "ISM | LOGIN | PAROL | ROL\n"
            with f.open("a", encoding="utf-8") as fh:
                fh.write(header + line + "\n")
        except Exception as ex:
            print(f"[SEED WARN] new_accounts.txt yozilmadi: {ex}")
    return len(created)


# ─────────────────────────── CACHE ───────────────────────────

def save_cache(data):
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cache():
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def build_cache_once(employees, interns=None) -> dict:
    """Bugungi holatni API'dan yig'ib live_cache.json yozadi."""
    interns = interns or []
    # HR bot belgilagan ish vaqtlarini qo'llaymiz (har siklda — yangilanishi mumkin)
    apply_work_overrides(employees)
    day_str = datetime.now().strftime("%Y-%m-%d")
    attendance_rows = fetch_attendance_rows(employees, day_str)
    state = build_state(employees, attendance_rows, is_today=True, day_str=day_str)

    at_work = to_public_rows(state, "ishda")
    not_at_work = to_public_rows(state, "ishda_emas")
    lunch = to_public_rows(state, "tushlikda")
    absent = to_public_rows(state, "kelmagan")
    late = to_late_rows(state)
    # Rahbariyat (direktor va o'rinbosarlari), haydovchilar va masofaviy
    # ishlovchilar "Kelmagan" va "Kechikkan" ro'yxatlarida ko'rsatilmaydi
    # (umumiy "employees" ro'yxatida ko'rinaveradi)
    _hide_cats = {"rahbar", "haydovchi", "masofaviy"}
    _cat_by_card = {e["card_number"]: e.get("category", "oddiy") for e in employees}
    absent = [r for r in absent
              if _cat_by_card.get(str(r.get("card_number")), "oddiy") not in _hide_cats]
    late = [r for r in late
            if _cat_by_card.get(str(r.get("card_number")), "oddiy") not in _hide_cats]
    all_rows = to_all_employee_rows(state)

    # ── amaliyotchilar (alohida fayldan) ──
    intern_rows = []
    try:
        if interns:
            intern_rows = build_intern_rows(interns, day_str)
    except Exception as e:
        print(f"[INTERN ERROR] {e}")

    cache = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "worker_status": "ok",
        "source": "biocontrol_api",
        "summary": {
            "total": len(employees),
            "at_work": len(at_work),
            "not_at_work": len(not_at_work),
            "lunch": len(lunch),
            "late": len(late),
            "absent": len(absent),
            "interns": len(intern_rows),
        },
        "at_work": at_work,
        "not_at_work": not_at_work,
        "lunch": lunch,
        "late": late,
        "absent": absent,
        "employees": all_rows,
        "interns": intern_rows,
    }
    save_cache(cache)
    # Yangi xodimlarga (users.xlsx da bor, lekin hisobi yo'q) — avtomatik hisob ochamiz
    try:
        auto_seed_accounts(employees)
    except Exception as e:
        print(f"[SEED ERROR] {e}")
    # Binoni tark etganlarni kuzatamiz (mobil ilova sabab so'raydi)
    try:
        update_exit_tracking(cache)
    except Exception as e:
        print(f"[CHIQISH XATO] {e}")
    return cache


# ─────────────────────────── OYLIK (kuniga bir marta) ───────────────────────────

def maybe_build_monthly(last_date_holder):
    """Kuniga bir marta monthly_report.json ni yangilaydi."""
    today = datetime.now().strftime("%Y-%m-%d")
    if last_date_holder.get("date") == today:
        return
    try:
        import analyze_biocontrol_api as analyze
        analyze.build_monthly_report(quiet=True)
        last_date_holder["date"] = today
        print(f"[{datetime.now().strftime('%H:%M:%S')}] oylik hisobot yangilandi")
    except Exception as e:
        print(f"[MONTHLY ERROR] {e}")


# ─────────────────────────── NVR AVTOMATIK YANGILANISH (kuniga 4 marta) ───────────────────────────

NVR_REFRESH_TIMES = ("00:00", "10:00", "18:00", "23:00")


def maybe_nvr_refresh(last_slot_holder):
    """Kuniga 4 marta (00:00, 10:00, 18:00, 23:00) NVR'dan avtomatik yangilaydi.
    Faqat FACEID_SOURCE=nvr_reports bo'lganda ma'noli."""
    if api.SOURCE != "nvr_reports":
        return
    now = datetime.now()
    hm = now.strftime("%H:%M")
    if hm not in NVR_REFRESH_TIMES:
        return
    slot = (now.strftime("%Y-%m-%d"), hm)
    if last_slot_holder.get("slot") == slot:
        return  # shu daqiqada allaqachon yangilandi
    last_slot_holder["slot"] = slot  # avval belgilaymiz — xato bo'lsa ham qayta urinib, tiqilib qolmasin
    try:
        import nvr_live
        result = nvr_live.refresh()
        if result.get("ok"):
            print(f"[{now.strftime('%H:%M:%S')}] 🔄 NVR avtomatik yangilandi ({hm}) — "
                  f"{result['employees']}/{result['total_queried']} xodim, {result['events']} hodisa")
        else:
            print(f"[{now.strftime('%H:%M:%S')}] ⚠️ NVR avtomatik yangilash xatosi ({hm}): {result.get('error')}")
    except Exception as e:
        print(f"[{now.strftime('%H:%M:%S')}] ⚠️ NVR avtomatik yangilash xatosi ({hm}): {e}")


# ─────────────────────────── ASOSIY DOIRA ───────────────────────────

def _file_mtime(path):
    """Faylning oxirgi o'zgartirilgan vaqti (yo'q bo'lsa 0)."""
    try:
        return path.stat().st_mtime if path and path.exists() else 0.0
    except Exception:
        return 0.0


def worker_loop():
    employees = load_employees()
    if not employees:
        print("❌ users.xlsx topilmadi yoki bo'sh. To'xtatilmoqda.")
        return
    interns = load_interns()
    print(f"✅ live_worker_api ishga tushdi — {len(employees)} xodim"
          + (f", {len(interns)} amaliyotchi" if interns else " (amaliyotchi fayli yo'q)")
          + f", har {POLL_SECONDS} sek")
    print(f"   API: {api.API_URL}")
    print("   📁 users.xlsx / interns.xlsx kuzatilmoqda — saqlasangiz avtomatik yangilanadi")

    last_monthly = {"date": None}
    last_nvr_refresh = {"slot": None}

    # Fayllarning oxirgi o'zgarish vaqtini eslab qolamiz.
    # Excel'ni saqlaganingizda mtime o'zgaradi -> avtomatik qayta o'qiymiz.
    emp_file = find_existing_employee_file()
    int_file = find_intern_file()
    seen = {
        "emp": _file_mtime(emp_file),
        "int": _file_mtime(int_file),
        "inact": _file_mtime(INACTIVE_INTERNS_FILE),
        "auto": _file_mtime(interns_auto.AUTO_FILE),
    }

    def _roster_cards():
        try:
            d = json.loads(INTERNS_ROSTER_FILE.read_text(encoding="utf-8"))
            return [r.get("card_number") for r in d.get("interns", [])]
        except Exception:
            return [i["card_number"] for i in interns]
    interns_auto.note_roster(_roster_cards())

    while True:
        try:
            # ── XODIMLAR fayli o'zgardimi? ──
            emp_file = find_existing_employee_file()   # fayl nomi ham o'zgargan bo'lishi mumkin
            m = _file_mtime(emp_file)
            if m and m != seen["emp"]:
                time_module.sleep(0.5)  # Excel yozib bo'lishini kutamiz
                new_emps = load_employees()
                if new_emps:                        # bo'sh bo'lsa eskisini saqlaymiz
                    employees = new_emps
                    seen["emp"] = m
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 users.xlsx yangilandi "
                          f"— {len(employees)} xodim")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ users.xlsx bo'sh/xato — "
                          f"eski ro'yxat saqlandi")
                    seen["emp"] = m

            # ── AMALIYOTCHILAR fayli o'zgardimi? ──
            int_file = find_intern_file()
            m = _file_mtime(int_file)
            if m != seen["int"]:
                time_module.sleep(0.5)
                interns = load_interns()
                seen["int"] = m
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 interns.xlsx yangilandi "
                      f"— {len(interns)} amaliyotchi")
                interns_auto.note_roster(_roster_cards())

            # ── AMALIYOTCHILAR: 10 kun kelmaganlar avtomatik nofaol ──
            try:
                def _api_ok():
                    # Oddiy xodimlardan kamida bittasida oxirgi 10 kunda hodisa bo'lsa — API ishlayapti
                    a = (datetime.now() - timedelta(days=interns_auto.INACTIVE_DAYS)).strftime("%Y-%m-%d")
                    b = datetime.now().strftime("%Y-%m-%d")
                    return any(api.get_events(e["card_number"], a, b) for e in employees[:8])
                changed = interns_auto.maybe_daily([i["card_number"] for i in interns],
                                                   api.get_events, _api_ok)
                changed = interns_auto.check_returns(api.get_events) or changed
            except Exception as e:
                changed = False
                print(f"[AMALIYOTCHI] tekshiruv xatosi: {e}")
            # HR panelda faol/nofaol qilgan bo'lsa ham qayta yuklaymiz
            m_in, m_au = _file_mtime(INACTIVE_INTERNS_FILE), _file_mtime(interns_auto.AUTO_FILE)
            if changed or m_in != seen["inact"] or m_au != seen["auto"]:
                interns = load_interns()
                seen["inact"], seen["auto"] = m_in, m_au

            _t0 = time_module.time()
            cache = build_cache_once(employees, interns)
            cache_secs = time_module.time() - _t0
            # Bugun kirgan amaliyotchilar — "oxirgi kelgan kun" yangilanadi
            try:
                interns_auto.note_seen([r["card_number"] for r in cache.get("interns", [])
                                        if r.get("status") != "kelmagan"])
            except Exception:
                pass
            s = cache["summary"]
            print(f"[{datetime.now().strftime('%H:%M:%S')}] cache yangilandi — "
                  f"ishda:{s['at_work']} tushlik:{s['lunch']} chiqib:{s['not_at_work']} "
                  f"kelmagan:{s['absent']} kech:{s['late']} amaliyotchi:{s.get('interns', 0)} "
                  f"({cache_secs:.0f} sek)")
            # oylikni fon rejimida (kuniga bir marta)
            maybe_build_monthly(last_monthly)
            # NVR'dan avtomatik yangilanish (kuniga 4 marta)
            maybe_nvr_refresh(last_nvr_refresh)
        except Exception as e:
            # Xato bo'lsa eski cache'ni O'CHIRMAYMIZ (bot/dashboard "hech kim yo'q" ko'rsatmasin)
            existing = load_cache()
            if existing and existing.get("at_work") is not None:
                existing["worker_status"] = f"error: {e}"
                existing["last_error_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_cache(existing)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] worker xato: {e}")

        time_module.sleep(POLL_SECONDS)


if __name__ == "__main__":
    worker_loop()
