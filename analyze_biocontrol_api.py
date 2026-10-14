"""
analyze_biocontrol_api.py — Oylik hisobotni TO'G'RIDAN-TO'G'RI API'dan oladi.

Eski analyze_biocontrol.py ning API versiyasi:
  • Excel (BioControl.xlsx) O'RNIGA enter.mininnovation.uz API'dan o'qiydi
  • Xodimlarni ism emas, CARD_NUMBER (jshshir) bo'yicha bog'laydi — xatosiz
  • Natija: monthly_report.json (dashboard shuni o'qiydi) — format o'zgarmagan

Ishlatish:
    python analyze_biocontrol_api.py [YYYY-MM] [users.xlsx] [late_excused.json] [exemptions.json]

Misollar:
    python analyze_biocontrol_api.py                 # joriy oy
    python analyze_biocontrol_api.py 2026-06          # 2026-yil iyun
    python analyze_biocontrol_api.py 2026-06 users.xlsx

Mantiq (worker.py / eski analyze bilan bir xil):
  - Har xodimning work_start (ish boshlanishi) hisobga olinadi
  - Kechikish: birinchi kirish > (work_start + 15 daqiqa imtiyoz)
  - Sababsiz kechikish: late_excused.json da belgilanmagan kunlar
  - Ish vaqti: KIRISH->CHIQISH juftliklari yig'indisi (tushliksiz, xom)
"""

import os
import sys
import re
import json
import time
import calendar
from pathlib import Path
from datetime import datetime, time as dtime, timedelta
from collections import defaultdict

import pandas as pd

import biocontrol_api as api

try:
    import roles as _roles
except Exception:
    _roles = None

# ─── Sozlamalar (worker.py / .env bilan bir xil) ───
DEFAULT_WORK_START = "09:00:00"
LATE_GRACE_MINUTES = 15
# Tadbirda bo'lgan kun to'liq ish kuni deb hisoblanadi (8 soat)
FULL_DAY_MINUTES = 8 * 60

# Xodim binoda bo'lmasa ham TO'LIQ ISH KUNI (8 soat) hisoblanadigan turlar.
# Bu kunlarda kechikish ham, kelmagan ham hisoblanmaydi — xodim xizmat
# vazifasini bajargan.
TADBIR_TYPES = ("tadbir", "seminar", "tadbirda", "meropriyatie")
SAFARI_TYPES = ("safari", "safar", "xizmat_safari", "xizmat safari",
                "komandirovka")
FULL_DAY_TYPES = TADBIR_TYPES + SAFARI_TYPES


def _is_workday(day_str):
    """Ish kunimi? Shanba/Yakshanba va bayramlar — ish kuni EMAS."""
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


# ─────────────────────────── YORDAMCHI ───────────────────────────

def norm(s):
    s = str(s or "").strip().lower()
    s = (s.replace("o\u2018", "o").replace("g\u2018", "g")
           .replace("o'", "o").replace("g'", "g")
           .replace("\u2019", "").replace("'", "").replace('"', "")
           .replace("\u02bb", ""))
    s = re.sub(r"[^a-z\u0430-\u044f\u04510-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_work_start(value):
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
            tot = int(round(frac * 24 * 60))
            return dtime(tot // 60, tot % 60)
    except Exception:
        pass
    return dtime(9, 0)


# ── Kunlik imtiyoz (HR qarori) — late_grace_days.json ──
#   {"2026-09-07": {"until": "09:40"}}                       — 09:40 gacha kechikish emas
#   {"2026-10-07": {"until": "23:59", "entry_as": "09:00"}}  — hamma kechikmagan,
#        09:00 dan keyin kelganlarning ish vaqti 09:00 dan (ish boshidan) hisoblanadi
GRACE_DAYS_FILE = Path("late_grace_days.json")
_GRACE_CACHE = {"mtime": None, "data": {}}


def _hm(raw):
    m = re.match(r"(\d{1,2}):(\d{2})", str(raw or ""))
    if not m:
        return None
    try:
        return dtime(int(m.group(1)), int(m.group(2)))
    except Exception:
        return None


def day_grace(day):
    """Shu kun uchun imtiyoz: {"until": time, "entry_as": time|None} yoki None."""
    if not day:
        return None
    try:
        mt = GRACE_DAYS_FILE.stat().st_mtime
    except Exception:
        return None
    if _GRACE_CACHE["mtime"] != mt:
        try:
            raw = json.loads(GRACE_DAYS_FILE.read_text(encoding="utf-8")) or {}
        except Exception:
            raw = {}
        data = {}
        for d, v in (raw.items() if isinstance(raw, dict) else []):
            v = v if isinstance(v, dict) else {"until": v}
            u = _hm(v.get("until"))
            if u:
                data[str(d)[:10]] = {"until": u.replace(second=59), "entry_as": _hm(v.get("entry_as"))}
        _GRACE_CACHE.update(mtime=mt, data=data)
    return _GRACE_CACHE["data"].get(str(day)[:10])


def late_threshold_for(ws, day=None):
    base = datetime(2000, 1, 1, ws.hour, ws.minute, 0)
    th = (base + timedelta(minutes=LATE_GRACE_MINUTES, seconds=59)).time()
    g = day_grace(day)
    # Imtiyoz faqat yumshatadi
    return max(th, g["until"]) if g else th


def entry_credit_minutes(day, events, ws=None):
    """'entry_as' kuni: kech kelgan xodim ish boshida (09:00) kirgan deb olinadi —
    09:00 dan birinchi kirishgacha bo'lgan daqiqalar ish vaqtiga qo'shiladi."""
    g = day_grace(day)
    if not g or not g.get("entry_as"):
        return 0
    first_in = None
    for ev in sorted(events or [], key=lambda x: x["dt"]):
        if "вход" in str(ev.get("type", "")).lower():
            first_in = ev["dt"]
            break
    if not first_in:
        return 0
    start_t = g["entry_as"]
    if ws and ws > start_t:          # ish kuni kechroq boshlanadigan xodim — o'z vaqtidan
        start_t = ws
    start = first_in.replace(hour=start_t.hour, minute=start_t.minute, second=0, microsecond=0)
    return max(0, int((first_in - start).total_seconds() // 60))


# ─────────────────────────── XODIMLAR (users.xlsx) ───────────────────────────

def load_users(path):
    """users.xlsx -> [{full_name, card_number, work_start}] (admin/hr chiqarilmaydi? — yo'q, hammasi)."""
    raw = pd.read_excel(path, header=None)
    keys = ["familiya", "familya", "ism", "sharif", "card", "telegram", "role", "category"]
    hdr, best = 0, -1
    for i in range(min(15, len(raw))):
        txt = " ".join(norm(x) for x in raw.iloc[i].tolist())
        sc = sum(1 for k in keys if k in txt)
        if sc > best:
            best, hdr = sc, i
    df = pd.read_excel(path, header=hdr)
    df.columns = [norm(c).replace(" ", "_") for c in df.columns]

    def get(row, *names):
        for n in names:
            if n in row and pd.notna(row[n]):
                return str(row[n]).strip()
        return ""

    emps = []
    for _, r in df.iterrows():
        row = r.to_dict()
        ln = get(row, "familiya", "familya", "last_name")
        fn = get(row, "ism", "first_name", "name")
        mn = get(row, "sharif", "middle_name", "otchestvo")
        full = " ".join(x for x in [ln, fn, mn] if x).strip()
        if not full:
            continue
        card_raw = get(row, "card_number", "card", "cardnumber", "karta_raqami")
        # butun son / float bo'lsa ham 14 xonali matnga o'giramiz
        card = "".join(ch for ch in card_raw if ch.isdigit())
        if card_raw and "." in card_raw and card:  # "4.28e13" kabi holatlar ehtimoli
            try:
                card = str(int(float(card_raw)))
            except Exception:
                pass
        ws_raw = get(row, "work_start", "ish_boshlanishi", "ish_vaqti", "start_time", "boshlanish")
        role = norm(get(row, "role", "rol"))
        if role == "admin":
            continue
        if not card:
            continue  # jshshir yo'q — API'dan olib bo'lmaydi
        emps.append({
            "full_name": full,
            "card_number": card,
            "work_start": (parse_work_start(ws_raw) if ws_raw else parse_work_start(DEFAULT_WORK_START)).strftime("%H:%M:%S"),
        })
    return emps


# ─────────────────────────── ISH VAQTI HISOBI ───────────────────────────

def calc_day_minutes(events):
    """Kunlik ish vaqtini KIRISH->CHIQISH juftliklari bo'yicha hisoblaydi."""
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
                delta = int((ev["dt"] - open_in).total_seconds() // 60)
                if delta > 0:
                    total += delta
                open_in = None
    if total > 16 * 60:
        total = 16 * 60
    return total


def parse_hm(value, default="18:00"):
    """'18:00' yoki '18:00:00' -> time."""
    s = str(value or default).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except Exception:
            continue
    return dtime(18, 0)


WORK_END_T = parse_hm(os.getenv("WORK_END", "18:00"))


def calc_minutes_after(events, after_t=None):
    """Belgilangan vaqtdan (masalan 18:00) KEYIN ishlangan daqiqalar.

    Tadbir kunida ishlatiladi: to'liq ish kuni (8 soat) ustiga
    18:00 dan keyin qolib ishlagan vaqt QO'SHILADI.
    """
    after_t = after_t or WORK_END_T
    evs = sorted(events or [], key=lambda x: x["dt"])
    total = 0
    open_in = None
    for ev in evs:
        t = str(ev.get("type", "")).lower()
        if "вход" in t:
            if open_in is None:
                open_in = ev["dt"]
        elif "выход" in t:
            if open_in is not None:
                bound = open_in.replace(hour=after_t.hour, minute=after_t.minute,
                                        second=0, microsecond=0)
                start = max(open_in, bound)
                end = ev["dt"]
                if end > start:
                    total += int((end - start).total_seconds() // 60)
                open_in = None
    return max(0, total)


# ─────────────────────────── UZRLI / SAFAR ───────────────────────────

def load_excused(path):
    """late_excused.json -> {card: set(dates)}"""
    res = {}
    p = Path(path)
    if not p.exists():
        return res
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return res
    for card, info in (data or {}).items():
        if not isinstance(info, dict):
            continue
        if "date" in info:
            d = str(info.get("date", ""))[:10]
            if d:
                res.setdefault(str(card), set()).add(d)
        else:
            res[str(card)] = {str(k)[:10] for k in info.keys()}
    return res


def count_days_in_month(df, dt_, ym):
    try:
        y, mo = map(int, ym.split("-"))
    except Exception:
        return 0
    ms = datetime(y, mo, 1).date()
    me = datetime(y, mo, calendar.monthrange(y, mo)[1]).date()
    try:
        d1 = datetime.strptime(df[:10], "%Y-%m-%d").date()
    except Exception:
        return 0
    try:
        d2 = datetime.strptime(dt_[:10], "%Y-%m-%d").date()
    except Exception:
        d2 = d1
    lo, hi = max(d1, ms), min(d2, me)
    return (hi - lo).days + 1 if hi >= lo else 0


def load_safari(path, ym):
    """exemptions.json -> {card: safari_days}"""
    res = defaultdict(int)
    p = Path(path)
    if not p.exists():
        return res
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return res
    recs = data.get("records", []) if isinstance(data, dict) else []
    for rec in recs:
        if not isinstance(rec, dict) or rec.get("active") is False:
            continue
        t = str(rec.get("type", "")).lower().strip()
        if t not in SAFARI_TYPES:
            continue
        card = str(rec.get("card_number", "") or "")
        if not card:
            continue
        df = str(rec.get("date_from", ""))[:10]
        dt_ = str(rec.get("date_to", "") or df)[:10]
        days = count_days_in_month(df, dt_, ym)
        if days > 0:
            res[card] += days
    return res


def load_fullday_days(path, ym, types=FULL_DAY_TYPES):
    """exemptions.json -> {card: {'YYYY-MM-DD', ...}}

    TADBIR va XIZMAT SAFARI kunlari:
      • kechikish HISOBLANMAYDI (xizmat vazifasini bajargan),
      • to'liq ish kuni (8 soat) ishlagan deb hisoblanadi,
      • "kelmagan" ro'yxatiga tushmaydi.
    """
    res = defaultdict(set)
    p = Path(path)
    if not p.exists():
        return res
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return res
    recs = data.get("records", []) if isinstance(data, dict) else []
    try:
        y, mo = map(int, str(ym).split("-"))
    except Exception:
        return res
    m_start = datetime(y, mo, 1).date()
    m_end = datetime(y, mo, calendar.monthrange(y, mo)[1]).date()
    for rec in recs:
        if not isinstance(rec, dict) or rec.get("active") is False:
            continue
        t = str(rec.get("type", "")).lower().strip()
        if t not in types:
            continue
        card = str(rec.get("card_number", "") or "")
        if not card:
            continue
        df = str(rec.get("date_from", ""))[:10]
        dt_ = str(rec.get("date_to", "") or df)[:10]
        try:
            d1 = datetime.strptime(df, "%Y-%m-%d").date()
        except Exception:
            continue
        try:
            d2 = datetime.strptime(dt_, "%Y-%m-%d").date()
        except Exception:
            d2 = d1
        lo, hi = max(d1, m_start), min(d2, m_end)
        d = lo
        while d <= hi:
            res[card].add(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)
    return res


# ─────────────────────────── ASOSIY ───────────────────────────

def _absent_cutoff(end_date):
    """'Kelmagan' hisobi uchun oxirgi sana — BUGUN kirmaydi.

    Hisobot har kuni tunda quriladi. Agar bugunni ham qo'shsak, hali
    hech kim ishga kelmagan bo'ladi va butun jamoa "kelmagan" bo'lib
    chiqadi. Shuning uchun kecha bilan cheklaymiz.
    """
    try:
        de = datetime.strptime(str(end_date)[:10], "%Y-%m-%d").date()
    except Exception:
        return end_date
    yesterday = datetime.now().date() - timedelta(days=1)
    return min(de, yesterday).strftime("%Y-%m-%d")


def _workdays_between(start_date, end_date):
    """Ikki sana orasidagi ish kunlari (shanba/yakshanbasiz), ikkalasi ham kiradi.
    start_date/end_date: 'YYYY-MM-DD'."""
    try:
        d1 = datetime.strptime(str(start_date)[:10], "%Y-%m-%d").date()
        d2 = datetime.strptime(str(end_date)[:10], "%Y-%m-%d").date()
    except Exception:
        return 0
    if d2 < d1:
        return 0
    n, d = 0, d1
    while d <= d2:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    return n


def month_range(ym):
    """'YYYY-MM' -> (start_date, end_date) 'YYYY-MM-DD'. Joriy oy bo'lsa bugungача."""
    y, mo = map(int, ym.split("-"))
    last = calendar.monthrange(y, mo)[1]
    start = f"{y:04d}-{mo:02d}-01"
    today = datetime.now().date()
    if (y, mo) == (today.year, today.month):
        end = today.strftime("%Y-%m-%d")  # kelajakni so'ramaymiz
    else:
        end = f"{y:04d}-{mo:02d}-{last:02d}"
    return start, end


def load_tadbir_days(path, ym):
    """Faqat tadbir kunlari (eski nom — moslik uchun)."""
    return load_fullday_days(path, ym, TADBIR_TYPES)


def build_monthly_report(ym=None, users_path="users.xlsx",
                         excused_path="late_excused.json",
                         exemptions_path="exemptions.json",
                         quiet=False):
    """Oylik hisobotni yaratib monthly_report.json ga yozadi.
    Boshqa moduldan chaqirish uchun (masalan live_worker_api.py).
    Qaytaradi: report dict."""
    if ym is None:
        ym = datetime.now().strftime("%Y-%m")

    def log(*a, **k):
        if not quiet:
            print(*a, **k)

    start_date, end_date = month_range(ym)
    log(f"📅 Oy: {ym}  ({start_date} … {end_date})")
    log(f"👥 Xodimlar: {users_path}")

    emps = load_users(users_path)
    # HR bot belgilagan ish vaqtlarini qo'llaymiz (work_overrides.json)
    try:
        import live_worker_api as _lw
        applied = _lw.apply_work_overrides(emps)
        if applied:
            log(f"   🕐 Ish vaqti override: {applied} ta xodimда")
    except Exception:
        pass
    emp_by_card = {e["card_number"]: e for e in emps}
    log(f"   Yuklandi: {len(emps)} ta xodim (card bilan)")

    # ── API tirikligini tekshirish ──
    if emps:
        alive = api.ping(emps[0]["card_number"], start_date)
        log(f"🌐 API: {'✅ ishlayapti' if alive else '⚠️ javob status:false (davom etamiz)'}")

    excused_by_card = load_excused(excused_path)
    safari_by_card = load_safari(exemptions_path, ym)
    # Tadbir + xizmat safari — ikkalasi ham to'liq ish kuni hisoblanadi
    tadbir_by_card = load_fullday_days(exemptions_path, ym)
    if tadbir_by_card:
        _n_tad = len(load_fullday_days(exemptions_path, ym, TADBIR_TYPES))
        _n_saf = len(load_fullday_days(exemptions_path, ym, SAFARI_TYPES))
        log(f"   🎤 To'liq ish kuni: {len(tadbir_by_card)} xodim "
            f"(tadbir {_n_tad}, safar {_n_saf})")

    # oydagi ish kunlari (shanba/yakshanbasiz)
    y, mo = map(int, ym.split("-"))
    work_days_in_month = sum(
        1 for d in range(1, calendar.monthrange(y, mo)[1] + 1)
        if datetime(y, mo, d).weekday() < 5
    )

    work_rows, late_rows = [], []
    total = len(emps)
    empty_cards = []

    for idx, emp in enumerate(emps, 1):
        card = emp["card_number"]
        log(f"   [{idx}/{total}] {emp['full_name'][:35]:35} ", end="", flush=True)

        # ── API'dan hodisalar ──
        try:
            days_data = api.get_events_by_day(card, start_date, end_date)
        except Exception as e:
            log(f"XATO: {e}")
            continue

        if not days_data:
            empty_cards.append(card)

        ws = parse_work_start(emp["work_start"])
        late_th = late_threshold_for(ws)
        excused = excused_by_card.get(card, set())
        # TADBIR va XIZMAT SAFARI kunlari: kechikish yo'q + 8 soat
        tadbir_days = tadbir_by_card.get(card, set())

        total_min = 0
        days_worked = 0
        late_total = 0
        late_unexc = 0
        late_days = []

        for day, events in sorted(days_data.items()):
            events.sort(key=lambda x: x["dt"])
            dm = calc_day_minutes(events)
            # HR imtiyoz kuni: kech kelgan 09:00 da kirgan deb hisoblanadi
            if dm > 0:
                dm += entry_credit_minutes(day, events, ws)
            # Tadbir/safar kuni: 8 soat + 18:00 dan keyin qolib ishlagani
            if day in tadbir_days:
                dm = max(dm, FULL_DAY_MINUTES + calc_minutes_after(events))
            if dm > 0:
                total_min += dm
                days_worked += 1
            # birinchi kirish -> kechikish
            first_in = None
            for ev in events:
                if "вход" in ev["type"].lower():
                    first_in = ev["dt"]
                    break
            # Tadbir/safarda bo'lgan kun kechikish HISOBLANMAYDI
            if day in tadbir_days:
                continue
            # Kechikish faqat ISH KUNLARIDA (shanba/yakshanba/bayram hisoblanmaydi)
            if first_in and first_in.time() > late_threshold_for(ws, day) and _is_workday(day):
                late_total += 1
                is_exc = day in excused
                if not is_exc:
                    late_unexc += 1
                late_days.append({
                    "date": day,
                    "time": first_in.strftime("%H:%M:%S"),
                    "excused": is_exc,
                })

        # Tadbir/safarda bo'lib, binoga umuman kirmagan kunlar ham 8 soat
        for td in sorted(tadbir_days):
            if td in days_data:
                continue          # yuqorida hisoblab bo'lindi
            if not _is_workday(td):
                continue          # dam olish/bayram
            if td < str(start_date)[:10] or td > str(end_date)[:10]:
                continue
            total_min += FULL_DAY_MINUTES
            days_worked += 1

        if days_worked > 0:
            h, m = divmod(total_min, 60)
            avg = total_min // days_worked
            # "Kelmagan" ni oyning boshidan emas, xodimning BIRINCHI kunidan
            # bugungacha o'tgan ish kunlari bo'yicha hisoblaymiz (o'tmagan/ishga
            # kirmagan kunlar hisoblanmaydi — yangi xodim ko'p "kelmagan" bo'lmaydi).
            worked_days_list = sorted(days_data.keys())
            first_day = worked_days_list[0] if worked_days_list else None
            # BUGUN hisobga olinmaydi: kun hali tugamagan, xodim kelishi
            # yoki kechroq kirishi mumkin. Hisobot tunda quriladi, shuning
            # uchun bugunni qo'shsak hamma "kelmagan" bo'lib chiqadi.
            absent_end = _absent_cutoff(end_date)
            elapsed_workdays = _workdays_between(first_day, absent_end)
            absent = max(0, elapsed_workdays - days_worked)
            # Kelmagan aniq kunlar: [first_day..end_date] oraligidagi ish kunlari,
            # ishlangan kunlar (days_data) ichida yo'q bo'lganlari.
            absent_days_list = []
            if first_day:
                try:
                    dd = datetime.strptime(str(first_day)[:10], "%Y-%m-%d").date()
                    de = datetime.strptime(str(absent_end)[:10], "%Y-%m-%d").date()
                    while dd <= de:
                        ds = dd.strftime("%Y-%m-%d")
                        if (dd.weekday() < 5 and ds not in days_data
                                and ds not in tadbir_days and _is_workday(ds)):
                            absent_days_list.append(ds)
                        dd += timedelta(days=1)
                except Exception:
                    pass
            work_rows.append({
                "card_number": card,
                "full_name": emp["full_name"],
                "total_minutes": total_min,
                "total_hours_str": f"{h}:{m:02d}",
                "days_worked": days_worked,
                "absent_days": absent,
                "absent_days_list": absent_days_list,
                "avg_hours_str": f"{avg // 60}:{avg % 60:02d}",
            })

        if late_total > 0:
            late_rows.append({
                "card_number": card,
                "full_name": emp["full_name"],
                "work_start": emp["work_start"],
                "late_count": late_unexc,
                "late_total": late_total,
                "late_excused": late_total - late_unexc,
                "late_days": late_days,
            })

        log(f"kun={days_worked:2}  kechikish={late_total}")
        # API'ni bosim ostiga olmaslik uchun kichik pauza
        time.sleep(0.15)

    # ── safar ──
    safari_rows = []
    for card, days in safari_by_card.items():
        emp = emp_by_card.get(card)
        if not emp:
            continue
        safari_rows.append({
            "card_number": card,
            "full_name": emp["full_name"],
            "safari_days": days,
        })

    work_rows.sort(key=lambda x: x["total_minutes"], reverse=True)
    safari_rows.sort(key=lambda x: x["safari_days"], reverse=True)
    late_rows.sort(key=lambda x: x["late_count"], reverse=True)

    report = {
        "year_month": ym,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "biocontrol_api",
        "work_days_in_month": work_days_in_month,
        "top_work": work_rows,
        "top_safari": safari_rows,
        "top_late": late_rows,
    }

    # monthly_report.json — FAQAT joriy oy uchun.
    # Eski oy hisoblanganda uni ustiga yozib yubormaymiz (dashboard buzilmasin).
    _cur_ym = datetime.now().strftime("%Y-%m")
    if ym == _cur_ym:
        Path("monthly_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    else:
        log(f"   (joriy oy emas — monthly_report.json tegilmadi)")
    # Arxiv nusxasi — "oyni tanlab ko'rish" uchun (har doim)
    try:
        arch = Path("monthly_reports")
        arch.mkdir(exist_ok=True)
        (arch / f"{ym}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log(f"   (arxivga yozilmadi: {e})")

    log("\n" + "=" * 50)
    log(f"✅ monthly_report.json yaratildi — {ym}")
    log(f"   Ish kunlari (oyda): {work_days_in_month}")
    log(f"   Ishlagan xodim: {len(work_rows)}")
    log(f"   Kechikkan xodim: {len(late_rows)}")
    log(f"   Safarda: {len(safari_rows)}")
    if empty_cards:
        log(f"   ⚠️ API'dan hodisa kelmagan card: {len(empty_cards)} ta")
        log(f"      (ta'til/ishlamagan bo'lishi mumkin — normal)")

    return report


def main():
    # CLI: python analyze_biocontrol_api.py [YYYY-MM] [users.xlsx] [late_excused.json] [exemptions.json]
    ym = None
    args = sys.argv[1:]
    if args and re.match(r"^\d{4}-\d{2}$", args[0]):
        ym = args[0]
        args = args[1:]
    users_path = args[0] if len(args) > 0 else "users.xlsx"
    excused_path = args[1] if len(args) > 1 else "late_excused.json"
    exemptions_path = args[2] if len(args) > 2 else "exemptions.json"
    build_monthly_report(ym, users_path, excused_path, exemptions_path)


if __name__ == "__main__":
    main()
