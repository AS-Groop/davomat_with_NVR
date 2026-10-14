"""
dashboard_server.py — HR situatsion monitoring web dashboard.

Bot bilan bir vaqtda fonda ishlaydi (aiohttp).
Cloudflare Tunnel orqali internetga chiqariladi.
Parol himoyasi (.env: DASHBOARD_PASSWORD).
"""

import os
import re
import json
import asyncio
import secrets
from pathlib import Path
from datetime import datetime
from typing import Any
from collections import defaultdict, deque

from aiohttp import web

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import roles

BASE_DIR = Path(".")
TEMPLATES_DIR = BASE_DIR / "templates"
PHOTOS_DIR = BASE_DIR / "photos"

DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8080"))
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "").strip()
DASHBOARD_BIND = os.getenv("DASHBOARD_BIND", "127.0.0.1")
DASHBOARD_REFRESH_SECONDS = int(os.getenv("DASHBOARD_REFRESH_SECONDS", "10"))
# Carousel (panellar guruhi) almashinish vaqti — sekund.
DASHBOARD_CAROUSEL_SECONDS = int(os.getenv("DASHBOARD_CAROUSEL_SECONDS", "30"))
# Carousel guruhlari — qaysi panel qaysi guruhda. Panellar: inside, outside, safari, ruxsat.
# Guruhlar "|" bilan, panellar "," bilan ajratiladi.
DASHBOARD_CAROUSEL_GROUPS = os.getenv(
    "DASHBOARD_CAROUSEL_GROUPS", "outside,safari | ruxsat"
).strip()
try:
    import tashkilot as _tashkilot
    _ORG = _tashkilot.get()
except Exception:
    _ORG = {"name": "Tashkilot", "full": "Tashkilot"}
ORG_FULL_NAME = os.getenv("ORG_FULL_NAME", _ORG.get("full", ""))
ORG_NAME = os.getenv("ORG_NAME", _ORG.get("name", ""))
EXIT_WARN_MIN = int(os.getenv("EXIT_WARN_MINUTES", "10"))

CACHE_FILE = BASE_DIR / "live_cache.json"
EXEMPTIONS_FILE = BASE_DIR / "exemptions.json"
EXIT_TRACKING_FILE = BASE_DIR / "exit_tracking.json"

DASHBOARD_HIDDEN_FILE = BASE_DIR / "dashboard_hidden.json"
REASONS_FILE = BASE_DIR / "reasons.json"
EXIT_REASONS_FILE = BASE_DIR / "exit_reasons.json"
LATE_EXCUSED_FILE = BASE_DIR / "late_excused.json"
MONTHLY_REPORT_FILE = BASE_DIR / "monthly_report.json"

_VALID_TOKENS: set[str] = set()
_PREV_INSIDE: set[str] | None = None
_EVENTS: deque = deque(maxlen=30)


def _safe_load(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _load_hidden_cards() -> set[str]:
    data = _safe_load(DASHBOARD_HIDDEN_FILE, {"hidden_cards": []})
    return set(str(c) for c in (data.get("hidden_cards", []) if isinstance(data, dict) else []))


def _is_work_hours(now: datetime | None = None) -> bool:
    now = now or datetime.now()
    def _t(s):
        p = s.strip().split(":")
        return int(p[0]) * 60 + (int(p[1]) if len(p) > 1 else 0)
    cur = now.hour * 60 + now.minute
    ws = _t(os.getenv("WORK_START", "09:00"))
    we = _t(os.getenv("WORK_END", "18:00"))
    ls = _t(os.getenv("LUNCH_START", "13:00"))
    le = _t(os.getenv("LUNCH_END", "14:00"))
    if not (ws <= cur < we): return False
    if ls <= cur < le: return False
    return True


def _elapsed_minutes(s):
    if not s: return 0
    s = str(s).strip()
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            d = datetime.strptime(s[:19], f)
            return max(0, int((datetime.now() - d).total_seconds() // 60))
        except Exception:
            continue
    return 0


def _elapsed_since_time(s):
    """Faqat 'HH:MM:SS' (yoki 'HH:MM') vaqtdan bugungi kunga nisbatan o'tgan daqiqa."""
    if not s:
        return 0
    s = str(s).strip()
    for f in ("%H:%M:%S", "%H:%M"):
        try:
            t = datetime.strptime(s, f).time()
            now = datetime.now()
            d = now.replace(hour=t.hour, minute=t.minute,
                            second=getattr(t, "second", 0), microsecond=0)
            return max(0, int((now - d).total_seconds() // 60))
        except Exception:
            continue
    return _elapsed_minutes(s)


# Kechikkanlar/kelmaganlar ro'yxatida KO'RSATILMAYDIGAN turkumlar:
# haydovchi, direktor va o'rinbosarlar (rahbar).
LATE_ABSENT_EXCLUDE_CATEGORIES = {"haydovchi", "rahbar"}


def _exclude_excused_categories(rows):
    """Haydovchi va rahbar (direktor/o'rinbosar) turkumini ro'yxatdan chiqaradi."""
    out = []
    for r in rows or []:
        card = str(r.get("card_number", ""))
        cat = roles.get_category_by_card(card)
        if cat in LATE_ABSENT_EXCLUDE_CATEGORIES:
            continue
        out.append(r)
    return out


def _exclude_drivers(rows):
    """'Chiqqan' panelida haydovchilar ko'rsatilmaydi — ular faqat Jonli efirda ko'rinadi."""
    out = []
    for r in rows or []:
        card = str(r.get("card_number", ""))
        if roles.get_category_by_card(card) == "haydovchi":
            continue
        out.append(r)
    return out


def _filter_hidden(rows):
    """HR tomonidan yashirilgan card raqamlarni olib tashlaydi."""
    hidden = _load_hidden_cards()
    if not hidden:
        return list(rows or [])
    return [r for r in (rows or []) if str(r.get("card_number", "")) not in hidden]


def _photo_for(card):
    # 1) HR mobil ilovadan yuklagan rasm (photo_overrides.json) — ustunlikka ega
    try:
        ov = _safe_load(BASE_DIR / "photo_overrides.json", {})
        f = ov.get(str(card)) if isinstance(ov, dict) else None
        if f and (PHOTOS_DIR / str(f)).exists():
            return str(f)
    except Exception:
        pass
    # 2) users.xlsx (roles) dagi photo_file
    rec = roles.get_record_by_card(str(card))
    if rec and rec.get("photo_file"):
        return str(rec["photo_file"])
    return None


def _enrich(rows, with_elapsed=False):
    out = []
    for r in rows or []:
        card = str(r.get("card_number", ""))
        item = {
            "card_number": card,
            "full_name": r.get("full_name", "?"),
            "first_entry": r.get("first_entry", "") or "",
            "photo_file": _photo_for(card),
        }
        if with_elapsed:
            # Worker chiqish vaqtini "last_event_time" (HH:MM:SS) deb yozadi.
            last = (r.get("last_event_time") or r.get("last_event")
                    or r.get("last_exit") or "")
            if last in ("-", None):
                last = ""
            item["since"] = last
            item["exit_time"] = last  # template uchun chiqish vaqti (HH:MM:SS)
            item["elapsed_min"] = _elapsed_since_time(last) if last else None
        out.append(item)
    return out


def _load_reasons_today() -> dict[str, str]:
    """reasons.json dan FAQAT bugungi kunga tegishli HR izohlarini {card: text} ko'rinishida qaytaradi.

    Format: {"<card>": {"date": "YYYY-MM-DD", "text": "...", "set_at": "..."}}
    Eski kun izohlari ko'rsatilmaydi.
    """
    data = _safe_load(REASONS_FILE, {})
    if not isinstance(data, dict):
        return {}
    today = datetime.now().strftime("%Y-%m-%d")
    out: dict[str, str] = {}
    for card, info in data.items():
        if not isinstance(info, dict):
            continue
        text = str(info.get("text", "") or "").strip()
        if not text:
            continue
        d = str(info.get("date", "") or "")[:10]
        # Sana ko'rsatilmagan bo'lsa — har kuni ko'rsatamiz; aks holda faqat bugun.
        if d and d != today:
            continue
        out[str(card).strip()] = text
    return out


def _attach_reasons(rows):
    """Har bir qatorga (card_number bo'yicha) HR izohini 'reason' maydoniga qo'shadi."""
    reasons = _load_reasons_today()
    if not reasons:
        return rows
    for r in rows or []:
        card = str(r.get("card_number", "")).strip()
        if card in reasons:
            r["reason"] = reasons[card]
    return rows


def _load_exit_reasons_today() -> dict[str, str]:
    """exit_reasons.json dan FAQAT bugungi izohlar {card: text}."""
    data = _safe_load(EXIT_REASONS_FILE, {})
    if not isinstance(data, dict):
        return {}
    today = datetime.now().strftime("%Y-%m-%d")
    out: dict[str, str] = {}
    for card, info in data.items():
        if not isinstance(info, dict):
            continue
        text = str(info.get("text", "") or "").strip()
        if not text:
            continue
        d = str(info.get("date", "") or "")[:10]
        if d and d != today:
            continue
        out[str(card).strip()] = text
    return out


def _attach_exit_reasons(rows):
    """Chiqqanlar (outside) qatoriga HR izohini 'reason' maydoniga qo'shadi."""
    reasons = _load_exit_reasons_today()
    if not reasons:
        return rows
    for r in rows or []:
        card = str(r.get("card_number", "")).strip()
        if card in reasons:
            r["reason"] = reasons[card]
    return rows


def _load_excused_today() -> set[str]:
    """late_excused.json dan FAQAT bugun 'sababli' deb belgilangan kartalar to'plami.
    Yangi format: {"<card>": {"YYYY-MM-DD": {...}, ...}}
    Eski format:  {"<card>": {"date": "...", ...}}"""
    data = _safe_load(LATE_EXCUSED_FILE, {})
    if not isinstance(data, dict):
        return set()
    today = datetime.now().strftime("%Y-%m-%d")
    out = set()
    for card, info in data.items():
        if not isinstance(info, dict):
            continue
        if "date" in info:
            # Eski format — bitta sana
            d = str(info.get("date", "") or "")[:10]
            if d in ("", today):
                out.add(str(card).strip())
        else:
            # Yangi format — sanalar kalit
            if today in info:
                out.add(str(card).strip())
    return out


def _attach_excused(rows):
    """Kechikkan qatorlarga 'excused' (HR sababli = yashil) bayrog'ini qo'yadi."""
    excused = _load_excused_today()
    if not excused:
        return rows
    for r in rows or []:
        card = str(r.get("card_number", "")).strip()
        if card in excused:
            r["excused"] = True
    return rows


def _name_for_card(card, name_lookup):
    """Avval cache name_lookup, topilmasa roles (users.xlsx) dan ism qidiradi."""
    nm = name_lookup.get(card)
    if nm and nm != "?":
        return nm
    # roles orqali (card raqami turli formatda bo'lishi mumkin — to'g'ridan va 0'larsiz)
    try:
        rec = roles.get_record_by_card(str(card))
        if not rec:
            rec = roles.get_record_by_card(str(card).lstrip("0"))
        if rec and rec.get("full_name"):
            return rec["full_name"]
    except Exception:
        pass
    return "?"


def _detect_events(current_inside, name_lookup, event_times=None):
    """Kirish/chiqish voqealarini aniqlaydi.

    VAQT: iloji bo'lsa biometrik qurilmadagi HAQIQIY vaqt olinadi
    (event_times: {card: 'HH:MM:SS'}). Topilmasa — hozirgi vaqt (zaxira).
    Avval doim datetime.now() ishlatilardi, shu sababli feed vaqti
    haqiqiy kirish vaqtidan bir necha soniya/daqiqa farq qilardi.
    """
    global _PREV_INSIDE
    if _PREV_INSIDE is None:
        _PREV_INSIDE = set(current_inside)
        return
    entered = current_inside - _PREV_INSIDE
    left = _PREV_INSIDE - current_inside
    now_t = datetime.now().strftime("%H:%M:%S")
    event_times = event_times or {}

    def _tm(card):
        t = str(event_times.get(str(card), "") or "").strip()
        if t and t != "-" and re.match(r"^\d{1,2}:\d{2}", t):
            return t if len(t) >= 8 else (t + ":00")[:8]
        return now_t

    for card in entered:
        _EVENTS.append({"time": _tm(card), "type": "kirish", "card": card,
                        "name": _name_for_card(card, name_lookup), "photo_file": _photo_for(card)})
    for card in left:
        _EVENTS.append({"time": _tm(card), "type": "chiqish", "card": card,
                        "name": _name_for_card(card, name_lookup), "photo_file": _photo_for(card)})
    _PREV_INSIDE = set(current_inside)

    # Eski voqealarda "?" qolgan bo'lsa, qayta ism qidirib yangilaymiz
    for ev in _EVENTS:
        if ev.get("name") in (None, "", "?"):
            fixed = _name_for_card(str(ev.get("card", "")), name_lookup)
            if fixed and fixed != "?":
                ev["name"] = fixed
                if not ev.get("photo_file"):
                    ev["photo_file"] = _photo_for(str(ev.get("card", "")))


def _birthdays_today():
    items = []
    hidden = _load_hidden_cards()
    for rec in roles.birthdays_today():
        card = str(rec.get("card_number", ""))
        if card in hidden:
            continue
        items.append({
            "full_name": rec.get("full_name", ""),
            "card_number": card,
            "photo_file": rec.get("photo_file"),
            "birthday": rec.get("birthday", ""),
        })
    return items


def collect_state():
    cache = _safe_load(CACHE_FILE, {})
    exemptions = _safe_load(EXEMPTIONS_FILE, {})
    exit_tracking = _safe_load(EXIT_TRACKING_FILE, {})

    today = datetime.now().strftime("%Y-%m-%d")

    # exemptions.json uch xil tuzilishda bo'lishi mumkin:
    #   1) {"records": [ {card_number, type, date_from, date_to, active}, ... ]}  ← HR bot shu formatda yozadi
    #   2) {"YYYY-MM-DD": {card: {...}}}  — sana bo'yicha guruhlangan
    #   3) {card: {...}}                  — to'g'ridan-to'g'ri kartalar
    # Har holatda ham bugungi kunga (date_from..date_to oralig'i) tegishli yozuvlarni yig'amiz.
    def _to_iso(s):
        """'01.06.2026', '2026-06-01', '01/06/2026' -> '2026-06-01'."""
        s = str(s or "").strip()[:10]
        if not s:
            return ""
        m = re.match(r"^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$", s)
        if m:
            return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        m = re.match(r"^(\d{1,2})[-./](\d{1,2})[-./](\d{4})$", s)
        if m:
            return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        return s

    def _in_range(info):
        df = _to_iso(info.get("date_from", ""))
        dt = _to_iso(info.get("date_to", "") or info.get("date_from", ""))
        if not df:
            # sana ko'rsatilmagan bo'lsa — faqat shu kunlik deb hisoblaymiz
            return True
        return df <= today <= (dt or df)

    active_ex: dict[str, dict] = {}

    # 1-tuzilish: {"records": [...]}
    records = exemptions.get("records") if isinstance(exemptions, dict) else None
    if isinstance(records, list):
        for info in records:
            if not isinstance(info, dict):
                continue
            if info.get("active") is False:
                continue
            if not _in_range(info):
                continue
            card = str(info.get("card_number", "") or "")
            if not card:
                continue
            # Takror yozuvlar: eng so'nggisi (set_at bo'yicha) ustun bo'ladi.
            prev = active_ex.get(card)
            if prev is None or str(info.get("set_at", "")) >= str(prev.get("set_at", "")):
                active_ex[card] = info
    elif isinstance(exemptions, dict):
        for key, val in exemptions.items():
            if isinstance(val, dict) and "type" not in val and any(
                isinstance(v, dict) for v in val.values()
            ):
                # 2-tuzilish: key = sana, val = {card: info}
                for card, info in val.items():
                    if isinstance(info, dict) and _in_range(info):
                        active_ex[str(card)] = info
            elif isinstance(val, dict):
                # 3-tuzilish: key = card, val = info
                if _in_range(val):
                    active_ex[str(key)] = val

    today_ex = active_ex

    safari_list, ruxsat_list, tadbir_list = [], [], []
    for card, info in (today_ex or {}).items():
        item = {
            "card_number": card,
            "full_name": info.get("full_name") or info.get("name") or "?",
            "note": info.get("note", ""),
            "date_from": info.get("date_from", ""),
            "date_to": info.get("date_to", ""),
            "photo_file": _photo_for(card),
        }
        t = (info.get("type") or "").lower().strip()
        if t in ("safari", "safar", "xizmat_safari", "xizmat safari", "komandirovka"):
            safari_list.append(item)
        elif t in ("tadbir", "seminar", "tadbirda", "meropriyatie"):
            tadbir_list.append(item)
        elif t in ("ruxsat", "tatil", "mehnat_tatili", "mehnat tatili", "tatil_mehnat"):
            ruxsat_list.append(item)

    at_work = _filter_hidden(cache.get("at_work", []))
    at_lunch = _filter_hidden(cache.get("lunch", []))
    not_at_work = _filter_hidden(cache.get("not_at_work", []))
    late_list = _filter_hidden(cache.get("late", []))
    absent_list = _filter_hidden(cache.get("absent", []))

    # Amaliyotchilar (alohida panel) — live_worker_api yozadi
    interns_list = _filter_hidden(cache.get("interns", []) or [])
    for r in interns_list:
        r["photo_file"] = _photo_for(r.get("card_number"))

    inside = at_work + at_lunch
    inside_cards = {str(r.get("card_number", "")) for r in inside}

    def _norm_card_early(c):
        return str(c or "").strip().lstrip("0")
    _exempt_norm = {_norm_card_early(c) for c in today_ex.keys()}
    outside = [r for r in not_at_work
               if str(r.get("card_number", "")) not in inside_cards
               and _norm_card_early(r.get("card_number", "")) not in _exempt_norm]
    # 'Chiqqan' panelida haydovchilar ko'rsatilmaydi (faqat Jonli efirda).
    outside = _exclude_drivers(outside)

    # ── ISHGA QAYTGANLAR ──
    # Xizmat safari / mehnat ta'tili / tadbirda deb belgilangan xodim binoga
    # KIRSA (biometrikdan o'tsa), u o'sha ustunda qolmaydi — "Ishxonada" ga o'tadi.
    # Masalan: safar 12—14-avgust, lekin xodim 13-avgust ishga qaytdi.
    # Kechikkanlar ro'yxatiga esa baribir tushmaydi (HR belgilagani saqlanadi).
    _inside_norm = {_norm_card_early(c) for c in inside_cards}

    def _drop_returned(rows):
        return [r for r in (rows or [])
                if _norm_card_early(r.get("card_number", "")) not in _inside_norm]

    safari_list = _drop_returned(safari_list)
    ruxsat_list = _drop_returned(ruxsat_list)
    tadbir_list = _drop_returned(tadbir_list)

    # Voqealarni aniqlash — TO'LIQ ma'lumotdan (yashirinlik o'zgarsa, soxta voqea yaratmasin)
    full_inside_cards = {str(r.get("card_number", ""))
                         for r in (cache.get("at_work", []) or []) + (cache.get("lunch", []) or [])}
    name_lookup = {str(r.get("card_number", "")): r.get("full_name", "?")
                   for r in (cache.get("at_work", []) or []) + (cache.get("lunch", []) or [])
                   + (cache.get("not_at_work", []) or []) + (cache.get("employees", []) or [])}
    # users.xlsx dagi BARCHA xodimlarni ham qo'shamiz (ish tugagach cache bo'sh bo'lsa ham ism topilsin)
    try:
        for emp in roles.all_employees():
            card = str(emp.get("card_number", "")).strip()
            if card and (card not in name_lookup or name_lookup[card] == "?"):
                name_lookup[card] = emp.get("full_name", "?")
    except Exception:
        pass
    # Biometrikdagi HAQIQIY hodisa vaqti (feed shu vaqtni ko'rsatadi).
    # Kirganlar uchun — first_entry, chiqqanlar uchun — last_event_time.
    event_times = {}
    for r in (cache.get("employees", []) or []):
        c = str(r.get("card_number", ""))
        if not c:
            continue
        last = str(r.get("last_event_time", "") or "").strip()
        first = str(r.get("first_entry", "") or "").strip()
        t = last if last and last != "-" else first
        if t and t != "-":
            event_times[c] = t
    _detect_events(full_inside_cards, name_lookup, event_times)

    alerts = []
    if _is_work_hours() and roles.is_working_day():
        exempted = {str(c).strip().lstrip("0") for c in today_ex.keys()} if isinstance(today_ex, dict) else set()
        for card, track in (exit_tracking or {}).items():
            if str(card).strip().lstrip("0") in exempted or not roles.should_ask_explanation(card):
                continue
            last = track.get("last_event") or track.get("started_at")
            el = _elapsed_minutes(last)
            if el >= EXIT_WARN_MIN:
                name = track.get("full_name") or name_lookup.get(card, "?")
                alerts.append({"card_number": card, "full_name": name, "since": last,
                               "elapsed_min": el, "photo_file": _photo_for(card)})
    alerts.sort(key=lambda a: -a["elapsed_min"])

    non_working_label = None
    if not roles.is_working_day():
        wd = datetime.now().weekday()
        if roles.is_holiday():
            hols = dict(roles.list_holidays())
            non_working_label = f"Bayram: {hols.get(today, 'Dam olish')}"
        elif wd == 5: non_working_label = "Shanba — dam olish kuni"
        elif wd == 6: non_working_label = "Yakshanba — dam olish kuni"

    hourly = defaultdict(int)
    for r in (cache.get("employees", []) or []):
        fe = r.get("first_entry") or ""
        if fe and ":" in fe:
            try:
                hh = int(fe.split(":")[0])
                if 6 <= hh <= 22: hourly[hh] += 1
            except Exception:
                pass

    # Ish kuni emas bo'lsa, kechikkan/kelmagan ko'rsatilmaydi
    show_late_absent = roles.is_working_day()

    # Safari yoki ta'tilda bo'lganlar kechikkanlar/kelmaganlar ro'yxatida ko'rsatilmaydi.
    def _norm_card(c):
        return str(c or "").strip().lstrip("0")
    exempted_cards = {_norm_card(c) for c in today_ex.keys()}

    def _drop_exempted(rows):
        return [r for r in (rows or [])
                if _norm_card(r.get("card_number", "")) not in exempted_cards]

    # Haydovchi, direktor va o'rinbosarlar (rahbar) kechikkan/kelmaganlar ro'yxatida ko'rsatilmaydi.
    # HR qo'lda kiritgan qisqa izohlar (reasons.json) ism ostida ko'rsatiladi.
    late_shown = _attach_excused(_attach_reasons(_enrich(_drop_exempted(_exclude_excused_categories(late_list))))) if show_late_absent else []
    absent_shown = _attach_reasons(_enrich(_drop_exempted(_exclude_excused_categories(absent_list)))) if show_late_absent else []

    # Kechikkanlar: eng kech kelgan (oxirgi kechikkan) eng tepada ko'rinadi.
    # (worker.py ham shunday beradi, lekin bu yerda ham kafolatlaymiz)
    late_shown.sort(key=lambda r: (r.get("first_entry") or ""), reverse=True)

    # Voqealar — yashiringan kartochkalarsiz
    hidden_now = _load_hidden_cards()
    events_visible = [e for e in _EVENTS if str(e.get("card", "")) not in hidden_now][-20:]

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "org_full_name": ORG_FULL_NAME,
        "non_working_label": non_working_label,
        "summary": {
            "inside": len(inside), "outside": len(outside),
            "safari": len(safari_list), "ruxsat": len(ruxsat_list),
            "tadbir": len(tadbir_list),
            "alerts": len(alerts),
            "late": len(late_shown), "absent": len(absent_shown),
            "interns": len(interns_list),
        },
        "inside": _enrich(inside),
        "outside": _attach_exit_reasons(_enrich(outside, with_elapsed=True)),
        "safari": safari_list,
        "ruxsat": ruxsat_list,
        "tadbir": tadbir_list,
        "interns": interns_list,
        "late": late_shown,
        "absent": absent_shown,
        "alerts": alerts,
        "events": events_visible,
        "birthdays": _birthdays_today(),
        "hourly": [{"h": h, "n": hourly.get(h, 0)} for h in range(7, 19)],
        "refresh_seconds": DASHBOARD_REFRESH_SECONDS,
    }


def _zoom_state():
    try:
        import bron
        return bron.dashboard_state()
    except Exception as e:
        print(f"[DASHBOARD] zoom xonalar: {type(e).__name__}: {e}")
        return []


def _is_authed(request):
    token = request.cookies.get("dash_token", "")
    return bool(token and token in _VALID_TOKENS)


@web.middleware
async def auth_middleware(request, handler):
    if request.path.startswith("/login"):
        return await handler(request)
    if not _is_authed(request):
        if request.path.startswith("/api/"):
            return web.json_response({"error": "auth required"}, status=401)
        if request.path.startswith("/photos/"):
            return web.Response(status=401)
        return web.HTTPFound("/login")
    return await handler(request)


async def login_get(request):
    err = request.query.get("err")
    err_html = '<div class="err">Noto\'g\'ri parol</div>' if err else ''
    return web.Response(text=_render("login.html", {"error_block": err_html}), content_type="text/html")


async def login_post(request):
    data = await request.post()
    password = (data.get("password") or "").strip()
    if not DASHBOARD_PASSWORD or password != DASHBOARD_PASSWORD:
        return web.HTTPFound("/login?err=1")
    token = secrets.token_urlsafe(32)
    _VALID_TOKENS.add(token)
    resp = web.HTTPFound("/")
    resp.set_cookie("dash_token", token, max_age=30*24*3600, httponly=True, samesite="Lax")
    return resp


async def logout(request):
    token = request.cookies.get("dash_token")
    if token: _VALID_TOKENS.discard(token)
    resp = web.HTTPFound("/login")
    resp.del_cookie("dash_token")
    return resp


async def index(request):
    return web.Response(text=_render("dashboard.html", {
        "org_full_name": ORG_FULL_NAME,
        "org_name": ORG_NAME,
        "refresh_seconds": DASHBOARD_REFRESH_SECONDS,
        "carousel_seconds": DASHBOARD_CAROUSEL_SECONDS,
        "carousel_groups": DASHBOARD_CAROUSEL_GROUPS,
    }), content_type="text/html")


async def api_state(request):
    return web.json_response(collect_state())


async def api_timeline(request):
    """Bitta xodimning bugungi kirish-chiqish tarixi (modal uchun)."""
    card = request.match_info.get("card", "")
    card = str(card).strip()
    if not card:
        return web.json_response({"error": "card kerak"}, status=400)

    cache = _safe_load(CACHE_FILE, {})
    rec = None
    for r in (cache.get("employees", []) or []):
        if str(r.get("card_number", "")).strip() == card:
            rec = r
            break

    if rec is None:
        return web.json_response({"error": "topilmadi", "card": card}, status=404)

    timeline = rec.get("timeline", []) or []
    # Juftlik bo'yicha ish vaqtini hisoblash (kirish→chiqish oralig'i)
    return web.json_response({
        "card_number": card,
        "full_name": rec.get("full_name", "?"),
        "photo_file": _photo_for(card),
        "status": rec.get("status", ""),
        "first_entry": rec.get("first_entry", ""),
        "timeline": timeline,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })


MONTHLY_DIR = BASE_DIR / "monthly_reports"      # arxiv: monthly_reports/YYYY-MM.json


def _available_months():
    """Reyting mavjud bo'lgan oylar (yangidan eskiga)."""
    out = set()
    cur = _safe_load(MONTHLY_REPORT_FILE, {}).get("year_month", "")
    if cur:
        out.add(str(cur))
    try:
        for p in MONTHLY_DIR.glob("*.json"):
            if re.match(r"^\d{4}-\d{2}$", p.stem):
                out.add(p.stem)
    except Exception:
        pass
    return sorted(out, reverse=True)


_BUILDING: set[str] = set()      # hozir hisoblanayotgan oylar


def _build_month_bg(ym):
    """Oylik hisobotni fon oqimida quradi va arxivga yozadi (1-2 daqiqa)."""
    import threading

    def _run():
        try:
            import analyze_biocontrol_api as analyze
            rep = analyze.build_monthly_report(ym=ym, quiet=True)
            MONTHLY_DIR.mkdir(exist_ok=True)
            (MONTHLY_DIR / f"{ym}.json").write_text(
                json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[REYTING] {ym} oyi tayyor.")
        except Exception as e:
            print(f"[REYTING XATO] {ym}: {type(e).__name__}: {e}")
        finally:
            _BUILDING.discard(ym)

    if ym in _BUILDING:
        return
    _BUILDING.add(ym)
    threading.Thread(target=_run, name=f"month-{ym}", daemon=True).start()


async def api_monthly(request):
    """Oylik reyting: ko'p ishlagan, ko'p safarda, ko'p sababsiz kechikkan.

    ?month=YYYY-MM — eski oyni ko'rish. Arxivda bo'lmasa — FONDA hisoblanadi
    (avval buni Telegram bot qilardi; bot olib tashlangan).
    """
    ym = str(request.query.get("month", "")).strip()
    report = _safe_load(MONTHLY_REPORT_FILE, {})
    months = _available_months()
    if ym and str(report.get("year_month", "")) != ym:
        if not re.match(r"^\d{4}-\d{2}$", ym):
            return web.json_response({"empty": True, "months": months})
        p = MONTHLY_DIR / f"{ym}.json"
        if not p.exists():
            _build_month_bg(ym)     # fonda hisoblaymiz
            return web.json_response({"empty": True, "building": True,
                                      "year_month": ym, "months": months})
        report = _safe_load(p, {})
    if not report:
        return web.json_response({"empty": True, "months": months})
    report = dict(report)
    report["months"] = months

    # Reytingga kirmaydiganlar: haydovchilar (ish vaqti tartibsiz) va
    # rahbariyat (direktor, o'rinbosarlari) — jonli panelda ham shunday.
    def _drop_excluded(rows):
        out = []
        for r in rows or []:
            try:
                if roles.get_category_by_card(str(r.get("card_number", ""))) in LATE_ABSENT_EXCLUDE_CATEGORIES:
                    continue
            except Exception:
                pass
            out.append(r)
        return out

    for k in ("top_work", "top_safari", "top_late"):
        report[k] = _drop_excluded(report.get(k))
    # Foto fayllarni qo'shamiz
    def _enrich_photos(rows):
        for r in rows or []:
            r["photo_file"] = _photo_for(str(r.get("card_number", "")))
        return rows
    _enrich_photos(report.get("top_work"))
    _enrich_photos(report.get("top_safari"))
    _enrich_photos(report.get("top_late"))
    return web.json_response(report)


async def photo_handler(request):
    fname = request.match_info.get("fname", "")
    if not fname or "/" in fname or "\\" in fname or ".." in fname:
        return web.Response(status=404)
    path = PHOTOS_DIR / fname
    if not path.exists() or not path.is_file():
        return web.Response(status=404)
    return web.FileResponse(path)


def _render(template_name, vars):
    path = TEMPLATES_DIR / template_name
    if not path.exists():
        return f"<h1>Template {template_name} topilmadi</h1>"
    text = path.read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


async def start_dashboard():
    if not DASHBOARD_PASSWORD:
        print("[DASHBOARD] DASHBOARD_PASSWORD .env da kiritilmagan — dashboard yoqilmadi.")
        return None
    if not TEMPLATES_DIR.exists():
        print(f"[DASHBOARD] {TEMPLATES_DIR} papkasi topilmadi — dashboard yoqilmadi.")
        return None
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/login", login_get)
    app.router.add_post("/login", login_post)
    app.router.add_get("/logout", logout)
    app.router.add_get("/", index)
    app.router.add_get("/api/state", api_state)
    app.router.add_get("/api/timeline/{card}", api_timeline)
    app.router.add_get("/api/monthly", api_monthly)
    app.router.add_get("/photos/{fname}", photo_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, DASHBOARD_BIND, DASHBOARD_PORT)
    await site.start()
    print(f"[DASHBOARD] http://{DASHBOARD_BIND}:{DASHBOARD_PORT} da ishga tushdi.")
    return runner


# ─────────────────────────── MUSTAQIL ISHGA TUSHIRISH ───────────────────────────
# Avval dashboard'ni Telegram bot (main17.py) ishga tushirardi.
# Bot olib tashlangach — bu fayl o'zi mustaqil xizmat sifatida ishlaydi:
#     python dashboard_server.py

async def _main():
    runner = await start_dashboard()
    if runner is None:
        return
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\n[DASHBOARD] to'xtatildi.")
