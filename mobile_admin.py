"""
mobile_admin.py — mobil ilova uchun HR BOSHQARUV (admin) endpointlari.

Telegram-botdagi (main17.py) HR funksiyalarining mobil ekvivalenti.
Bir xil JSON fayllarga yozadi — bot, dashboard va mobil o'zaro sinxron.

Ruxsat: faqat role="hr" (Xabar yuborish — hr + director).

Endpointlar (hammasi Bearer token bilan):
  GET  /api/mobile/admin/overview                — umumiy holat (monitoring, bayramlar soni, ...)
  GET  /api/mobile/admin/exemptions              — Ruxsat & Safari yozuvlari
  POST /api/mobile/admin/exemptions/add          {card, type, date_from, date_to, note}
  POST /api/mobile/admin/exemptions/remove       {id}
  GET  /api/mobile/admin/reasons                 — bugungi izohlar (kirish/chiqish)
  POST /api/mobile/admin/reason                  {card, text}  (text bo'sh -> o'chirish)
  POST /api/mobile/admin/exit_reason             {card, text}  (text bo'sh -> o'chirish)
  POST /api/mobile/admin/late_excused            {card, date?} -> toggle
  GET  /api/mobile/admin/holidays
  POST /api/mobile/admin/holidays/add            {date, name}
  POST /api/mobile/admin/holidays/remove         {date}
  GET  /api/mobile/admin/hidden                  — dashboardda yashirilganlar
  POST /api/mobile/admin/hidden/toggle           {card}
  GET  /api/mobile/admin/worktime
  POST /api/mobile/admin/worktime/set            {card, time}  (time bo'sh -> o'chirish)
  POST /api/mobile/admin/broadcast               {text}        (hr + director)
  GET  /api/mobile/admin/explanations            ?month=YYYY-MM
  POST /api/mobile/admin/explanations/status     {exp_id, status: reviewed|pending}
  POST /api/mobile/admin/monitor                 {enabled: true/false}
"""

import os
import json
import uuid
import re
from pathlib import Path
from datetime import datetime, timedelta

import aiohttp
from aiohttp import web

try:
    import roles
except Exception:
    roles = None

BASE_DIR = Path(".")
EXEMPTIONS_FILE = BASE_DIR / "exemptions.json"
REASONS_FILE = BASE_DIR / "reasons.json"
EXIT_REASONS_FILE = BASE_DIR / "exit_reasons.json"
LATE_EXCUSED_FILE = BASE_DIR / "late_excused.json"
HOLIDAYS_FILE = BASE_DIR / "holidays.json"
HIDDEN_FILE = BASE_DIR / "dashboard_hidden.json"
WORK_OVERRIDES_FILE = BASE_DIR / "work_overrides.json"
ENTRY_OVERRIDES_FILE = BASE_DIR / "entry_overrides.json"
EXPLANATIONS_FILE = BASE_DIR / "explanations.json"
MONITOR_STATE_FILE = BASE_DIR / "monitor_state.json"
CACHE_FILE = BASE_DIR / "live_cache.json"
INTERNS_ROSTER_FILE = BASE_DIR / "interns_roster.json"
INACTIVE_INTERNS_FILE = BASE_DIR / "interns_inactive.json"
EXIT_MOBILE_FILE = BASE_DIR / "exit_mobile.json"
EXP_REQUESTS_FILE = BASE_DIR / "explanation_requests.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, data):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")


def _name_for_card(card):
    card = str(card)
    # 1) live_cache (users.xlsx dagi xodimlar)
    cache = _load(CACHE_FILE, {})
    for r in cache.get("employees", []) or []:
        if str(r.get("card_number")) == card:
            nm = r.get("full_name", "")
            if nm and nm != "?":
                return nm
    # 2) biometrik (kirish-chiqish) tizimi — attendance javobida 'name' bor
    try:
        import biocontrol_api as _bio
        res = _bio.attendance([card])
        if isinstance(res, list):
            for it in res:
                if str(it.get("card")) == card and it.get("name"):
                    return str(it.get("name")).strip()
    except Exception:
        pass
    return "?"


# ─────────────── mobile_api.py dan olinadigan yordamchilar ───────────────
# build_app chaqirilganda inject qilinadi (aylanma import bo'lmasligi uchun).

_require_login = None
_role_of = None
json_ok = None
json_err = None


def _auth_hr(request, allow_director=False):
    """(login, acc) yoki (None, javob). Faqat HR (ixtiyoriy: +director).
    super_admin — HR'ning barcha huquqlariga ega, shu sabab hamma joyda ham
    ruxsat beriladi."""
    login_id, acc = _require_login(request)
    if not login_id:
        return None, json_err("Avtorizatsiya kerak", status=401)
    role = _role_of(acc)
    allowed = {"hr", "director", "super_admin"} if allow_director else {"hr", "super_admin"}
    if role not in allowed:
        return None, json_err("Ruxsat yo'q (faqat HR)", status=403)
    return (login_id, acc), None


def _auth_super_admin(request):
    """(login, acc) yoki (None, javob). Faqat super_admin — xodimlarning
    kirish/chiqish vaqtini qo'lda tuzatish kabi eng yuqori darajadagi
    amallar uchun."""
    login_id, acc = _require_login(request)
    if not login_id:
        return None, json_err("Avtorizatsiya kerak", status=401)
    if _role_of(acc) != "super_admin":
        return None, json_err("Ruxsat yo'q (faqat super_admin)", status=403)
    return (login_id, acc), None


def _by(login_id):
    return f"mobile:{login_id}"


# ─────────────────────────── OVERVIEW ───────────────────────────

async def overview(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    mon = _load(MONITOR_STATE_FILE, {})
    holidays = _load(HOLIDAYS_FILE, {})
    d = _today()
    ex_active = [
        r for r in _load(EXEMPTIONS_FILE, {"records": []}).get("records", [])
        if r.get("active") and r.get("date_from", "") <= d <= r.get("date_to", "")
    ]
    exp = _load(EXPLANATIONS_FILE, {"records": {}}).get("records", {})
    pending = sum(1 for r in exp.values() if r.get("status") == "pending")
    return json_ok({
        "monitor_enabled": bool(mon.get("enabled")),
        "monitor_last_checked": mon.get("last_checked_at", ""),
        "cache_updated_at": mon.get("last_cache_updated_at", ""),
        "holidays_count": len(holidays),
        "active_exemptions": len(ex_active),
        "pending_explanations": pending,
    })


async def nvr_refresh(request):
    """Boshqaruv → \"Yangilash\" tugmasi: NVR'ga kirib, bugungi kirish/chiqish
    ma'lumotlarini tortib oladi (nvr_live.py). Faqat FACEID_SOURCE=nvr_reports
    bo'lganda ma'noli."""
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        import nvr_live
    except Exception as e:
        return json_err(f"nvr_live yuklanmadi: {e}", status=500)
    date_str = (request.rel_url.query.get("date") or "").strip() or None
    result = nvr_live.refresh(date_str)
    if not result.get("ok"):
        return json_err(result.get("error", "noma'lum xato"), status=502)
    return json_ok(result)


# ─────────────────────────── RUXSAT & SAFARI ───────────────────────────

async def exemptions_list(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    d = _today()
    records = _load(EXEMPTIONS_FILE, {"records": []}).get("records", [])
    active = [r for r in records if r.get("active")
              and r.get("date_from", "") <= d <= r.get("date_to", "")]
    upcoming = [r for r in records if r.get("active") and r.get("date_from", "") > d]
    return json_ok({"active": active, "upcoming": upcoming})


async def exemptions_add(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    login_id, _ = auth
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    ex_type = str(body.get("type", "")).strip().lower()
    d_from = str(body.get("date_from", "")).strip()
    d_to = str(body.get("date_to", "")).strip() or d_from
    note = str(body.get("note", "")).strip()
    if not card or ex_type not in ("ruxsat", "safari", "tadbir"):
        return json_err("card va type (ruxsat/safari/tadbir) kerak")
    if not DATE_RE.match(d_from) or not DATE_RE.match(d_to):
        return json_err("Sana formati: YYYY-MM-DD")
    if d_to < d_from:
        return json_err("Tugash sanasi boshlanishdan oldin bo'lmasin")
    data = _load(EXEMPTIONS_FILE, {"records": []})
    ex_id = uuid.uuid4().hex[:8]
    data["records"].append({
        "id": ex_id,
        "card_number": card,
        "full_name": _name_for_card(card),
        "type": ex_type,
        "date_from": d_from,
        "date_to": d_to,
        "note": note,
        "set_by": _by(login_id),
        "set_at": _now_str(),
        "active": True,
    })
    _save(EXEMPTIONS_FILE, data)
    return json_ok({"ok": True, "id": ex_id})


async def exemptions_remove(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    ex_id = str(body.get("id", "")).strip()
    data = _load(EXEMPTIONS_FILE, {"records": []})
    for rec in data.get("records", []):
        if rec.get("id") == ex_id:
            rec["active"] = False
            _save(EXEMPTIONS_FILE, data)
            return json_ok({"ok": True})
    return json_err("Yozuv topilmadi", status=404)


# ─────────────────────────── IZOHLAR ───────────────────────────

async def reasons_list(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    d = _today()

    def _fresh(store):
        out = {}
        for card, info in store.items():
            if isinstance(info, dict) and str(info.get("date", ""))[:10] in ("", d):
                out[card] = {"text": info.get("text", ""), "date": info.get("date", ""),
                             "full_name": _name_for_card(card)}
        return out

    return json_ok({
        "reasons": _fresh(_load(REASONS_FILE, {})),
        "exit_reasons": _fresh(_load(EXIT_REASONS_FILE, {})),
    })


async def _set_reason_generic(request, path):
    auth, err = _auth_hr(request)
    if err:
        return err
    login_id, _ = auth
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    text = str(body.get("text", "")).strip()
    if not card:
        return json_err("card kerak")
    data = _load(path, {})
    if not text:
        if str(card) in data:
            del data[str(card)]
            _save(path, data)
        return json_ok({"ok": True, "cleared": True})
    data[str(card)] = {
        "date": str(body.get("date", "")).strip() or _today(),
        "text": text,
        "set_at": _now_str(),
        "by": _by(login_id),
    }
    _save(path, data)
    return json_ok({"ok": True})


async def reason_set(request):
    return await _set_reason_generic(request, REASONS_FILE)


async def exit_reason_set(request):
    return await _set_reason_generic(request, EXIT_REASONS_FILE)


# ─────────────────────────── KECHIKISH UZRLI ───────────────────────────

async def late_excused_list(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    d = _today()
    out = []
    for card, info in _load(LATE_EXCUSED_FILE, {}).items():
        if isinstance(info, dict):
            if "date" in info:  # eski format
                if str(info.get("date", ""))[:10] == d:
                    out.append(card)
            elif d in info:     # yangi format (sana kalitlari)
                out.append(card)
    return json_ok({"excused": out})


async def late_excused_toggle(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    login_id, _ = auth
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    date = str(body.get("date", "")).strip() or _today()
    if not card:
        return json_err("card kerak")
    data = _load(LATE_EXCUSED_FILE, {})
    info = data.get(card)
    # eski format -> yangi format
    if isinstance(info, dict) and "date" in info:
        old_d = str(info.get("date", ""))[:10]
        info = {old_d: {"set_at": info.get("set_at", ""), "by": info.get("by")}} if old_d else {}
    if not isinstance(info, dict):
        info = {}
    if date in info:
        del info[date]
        excused = False
    else:
        info[date] = {"set_at": _now_str(), "by": _by(login_id)}
        excused = True
    if info:
        data[card] = info
    elif card in data:
        del data[card]
    _save(LATE_EXCUSED_FILE, data)
    return json_ok({"ok": True, "excused": excused})


# ─────────────────────────── BAYRAMLAR ───────────────────────────

async def holidays_list(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    data = _load(HOLIDAYS_FILE, {})
    items = [{"date": k, "name": v} for k, v in sorted(data.items())]
    return json_ok({"holidays": items})


async def holidays_add(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    date = str(body.get("date", "")).strip()
    name = str(body.get("name", "")).strip() or "Bayram / dam olish"
    if not DATE_RE.match(date):
        return json_err("Sana formati: YYYY-MM-DD")
    data = _load(HOLIDAYS_FILE, {})
    data[date] = name
    _save(HOLIDAYS_FILE, data)
    return json_ok({"ok": True})


async def holidays_remove(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    date = str(body.get("date", "")).strip()
    data = _load(HOLIDAYS_FILE, {})
    if date not in data:
        return json_err("Topilmadi", status=404)
    del data[date]
    _save(HOLIDAYS_FILE, data)
    return json_ok({"ok": True})


# ─────────────────────────── DASHBOARD KO'RINISH ───────────────────────────

async def hidden_list(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    cards = _load(HIDDEN_FILE, {"hidden_cards": []}).get("hidden_cards", [])
    return json_ok({"hidden": [{"card": c, "full_name": _name_for_card(c)} for c in cards]})


async def hidden_toggle(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    if not card:
        return json_err("card kerak")
    data = _load(HIDDEN_FILE, {"hidden_cards": []})
    cards = set(str(c) for c in data.get("hidden_cards", []))
    if card in cards:
        cards.discard(card)
        hidden = False
    else:
        cards.add(card)
        hidden = True
    _save(HIDDEN_FILE, {"hidden_cards": sorted(cards)})
    return json_ok({"ok": True, "hidden": hidden})


# ─────────────────────────── ISH VAQTI ───────────────────────────

async def worktime_list(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    data = _load(WORK_OVERRIDES_FILE, {})
    items = [{"card": c, "time": t, "full_name": _name_for_card(c)}
             for c, t in data.items()]
    return json_ok({"overrides": items})


async def worktime_set(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    t = str(body.get("time", "")).strip()
    if not card:
        return json_err("card kerak")
    data = _load(WORK_OVERRIDES_FILE, {})
    if not t:
        if card in data:
            del data[card]
            _save(WORK_OVERRIDES_FILE, data)
        return json_ok({"ok": True, "cleared": True})
    if not TIME_RE.match(t):
        return json_err("Vaqt formati: HH:MM yoki HH:MM:SS")
    if len(t) == 4:
        t = "0" + t
    if len(t) == 5:
        t += ":00"
    data[card] = t
    _save(WORK_OVERRIDES_FILE, data)
    return json_ok({"ok": True, "time": t})


# ─────────────────────────── KIRISH/CHIQISH TUZATISH (faqat super_admin) ───────────────────────────

async def attendance_edit_get(request):
    """Bitta xodim + bitta sana uchun hozirgi (haqiqiy) va tuzatilgan
    kirish/chiqish vaqtlarini qaytaradi — forma to'ldirish uchun."""
    auth, err = _auth_super_admin(request)
    if err:
        return err
    card = str(request.rel_url.query.get("card", "")).strip()
    date = str(request.rel_url.query.get("date", "")).strip()
    if not card or not DATE_RE.match(date):
        return json_err("card va date (YYYY-MM-DD) kerak")
    data = _load(ENTRY_OVERRIDES_FILE, {})
    cur = ((data.get(date) or {}).get(card) or {})
    actual_in, actual_out = "", ""
    try:
        import biocontrol_api as _bio
        evs = _bio.get_events(card, date, date)
        actual_in = next((e["dt"].strftime("%H:%M") for e in evs
                          if e["type"] == _bio.LABEL_ENTER), "")
        actual_out = next((e["dt"].strftime("%H:%M") for e in reversed(evs)
                           if e["type"] == _bio.LABEL_EXIT), "")
    except Exception as e:
        print(f"[ATTENDANCE_EDIT] {e}")
    return json_ok({
        "full_name": _name_for_card(card),
        "override_in": cur.get("in", ""), "override_out": cur.get("out", ""),
        "actual_in": actual_in, "actual_out": actual_out,
    })


async def attendance_edit_set(request):
    """Xodimning bitta kundagi kirish/chiqish vaqtini tuzatadi (super_admin).
    in/out bo'sh yuborilsa — o'sha maydon bo'yicha tuzatish o'chiriladi."""
    auth, err = _auth_super_admin(request)
    if err:
        return err
    login_id, _ = auth
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    date = str(body.get("date", "")).strip()
    tin = str(body.get("in", "")).strip()
    tout = str(body.get("out", "")).strip()
    if not card or not DATE_RE.match(date):
        return json_err("card va date (YYYY-MM-DD) kerak")
    if tin and not TIME_RE.match(tin):
        return json_err("Kirish vaqti formati: HH:MM")
    if tout and not TIME_RE.match(tout):
        return json_err("Chiqish vaqti formati: HH:MM")

    data = _load(ENTRY_OVERRIDES_FILE, {})
    day = data.setdefault(date, {})
    if not tin and not tout:
        day.pop(card, None)
        if not day:
            data.pop(date, None)
    else:
        entry = {}
        if tin:
            entry["in"] = tin
        if tout:
            entry["out"] = tout
        entry["izoh"] = f"{login_id} tomonidan qo'lda tuzatildi ({_now_str()})"
        day[card] = entry
    _save(ENTRY_OVERRIDES_FILE, data)
    return json_ok({"ok": True})


# ─────────────────────────── XABAR YUBORISH ───────────────────────────

ANNOUNCE_FILE = BASE_DIR / "announcements.json"


async def broadcast(request):
    """HR/rahbar e'lon yuboradi. Telegram bot olib tashlangani uchun e'lon
    ILOVA ICHIDA ko'rsatiladi — har bir xodim asosiy ekranда ko'radi."""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    login_id, _ = auth
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    text = str(body.get("text", "")).strip()
    if len(text) < 3:
        return json_err("Xabar matni juda qisqa")
    days = body.get("days")
    try:
        days = max(1, min(30, int(days)))
    except Exception:
        days = 3
    data = _load(ANNOUNCE_FILE, {"items": []})
    items = data.get("items", []) if isinstance(data, dict) else []
    aid = uuid.uuid4().hex[:8]
    items.insert(0, {
        "id": aid,
        "text": text,
        "date": _today(),
        "until": (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"),
        "by": _by(login_id),
        "at": _now_str(),
    })
    _save(ANNOUNCE_FILE, {"items": items[:100]})
    total = 0
    try:
        if roles is not None:
            total = len(roles.all_employees())
    except Exception:
        pass
    return json_ok({"ok": True, "id": aid, "days": days, "total": total})


async def announce_list(request):
    """HR: e'lonlar ro'yxati."""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    data = _load(ANNOUNCE_FILE, {"items": []})
    return json_ok({"items": (data.get("items", []) if isinstance(data, dict) else [])[:50]})


async def announce_delete(request):
    """HR: e'lonni o'chiradi. {id}"""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    aid = str(body.get("id", "")).strip()
    data = _load(ANNOUNCE_FILE, {"items": []})
    items = [x for x in (data.get("items", []) if isinstance(data, dict) else [])
             if str(x.get("id")) != aid]
    _save(ANNOUNCE_FILE, {"items": items})
    return json_ok({"ok": True})


# ─────────────────────────── TUSHUNTIRISHLAR ───────────────────────────

async def explanations_list(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    month = request.query.get("month", "").strip() or _today()[:7]
    records = _load(EXPLANATIONS_FILE, {"records": {}}).get("records", {})
    items = [r for r in records.values() if str(r.get("date", "")).startswith(month)]
    items.sort(key=lambda r: (r.get("status") != "pending", r.get("date", "")), )
    return json_ok({"month": month, "records": items})


async def explanations_status(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    login_id, _ = auth
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    exp_id = str(body.get("exp_id", "")).strip()
    status = str(body.get("status", "")).strip()
    if status not in ("reviewed", "pending"):
        return json_err("status: reviewed yoki pending")
    data = _load(EXPLANATIONS_FILE, {"records": {}})
    rec = data.get("records", {}).get(exp_id)
    if not rec:
        return json_err("Topilmadi", status=404)
    rec["status"] = status
    if status == "reviewed":
        rec["reviewed_by"] = _by(login_id)
        rec["reviewed_at"] = _now_str()
    else:
        rec["reviewed_by"] = None
        rec["reviewed_at"] = None
    _save(EXPLANATIONS_FILE, data)
    return json_ok({"ok": True})


# ─────────────────────────── MONITORING ───────────────────────────

async def interns_list(request):
    """HR: barcha amaliyotchilar (faol + nofaol) va holati."""
    auth, err = _auth_hr(request)
    if err:
        return err
    roster = _load(INTERNS_ROSTER_FILE, {"interns": []}).get("interns", [])
    # roster hali yozilmagan bo'lsa — live_cache dagi (faol) amaliyotchilardan
    if not roster:
        cache = _load(CACHE_FILE, {})
        roster = [{"card_number": str(r.get("card_number", "")), "full_name": r.get("full_name", "")}
                  for r in (cache.get("interns", []) or [])]
    inactive = set(str(c) for c in _load(INACTIVE_INTERNS_FILE, {"cards": []}).get("cards", []))
    try:
        import interns_auto
        auto = interns_auto.info()
        days = interns_auto.INACTIVE_DAYS
    except Exception:
        auto, days = {}, 10
    items = []
    seen = set()
    for r in roster:
        card = str(r.get("card_number", "") or "")
        if not card or card in seen:
            continue
        seen.add(card)
        a = auto.get(card, {})
        is_auto = bool(a.get("auto")) and card not in inactive
        reason = ("manual" if card in inactive else "auto" if is_auto
                  else "xlsx" if r.get("reason") == "xlsx" else "")
        items.append({"card": card, "full_name": r.get("full_name", ""),
                      "active": not reason, "reason": reason,
                      "last_seen": a.get("last_seen", ""), "auto_since": a.get("since", "")})
    items.sort(key=lambda x: str(x["full_name"]))
    return json_ok({"interns": items, "count": len(items), "auto_days": days,
                    "active": sum(1 for i in items if i["active"])})


async def intern_active_set(request):
    """HR: amaliyotchini faol/nofaol qiladi. {card, active: true/false}"""
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    active = bool(body.get("active"))
    if not card:
        return json_err("card kerak")
    data = _load(INACTIVE_INTERNS_FILE, {"cards": []})
    cards = set(str(c) for c in data.get("cards", []))
    if active:
        cards.discard(card)
    else:
        cards.add(card)
    _save(INACTIVE_INTERNS_FILE, {"cards": sorted(cards)})
    try:
        import interns_auto
        # Qayta faol — 10 kun shu kundan sanaladi; qo'lda nofaol — avtomatik qaytmaydi
        interns_auto.reactivate(card) if active else interns_auto.drop_auto(card)
    except Exception as e:
        print(f"[AMALIYOTCHI] interns_auto: {e}")
    return json_ok({"ok": True, "active": active})


async def exit_list(request):
    """HR: xodimlar yozgan chiqish izohlari (kutilayotganlar birinchi)."""
    auth, err = _auth_hr(request)
    if err:
        return err
    data = _load(EXIT_MOBILE_FILE, {"requests": {}})
    items = list(data.get("requests", {}).values())
    items.sort(key=lambda r: r.get("submitted_at", ""), reverse=True)
    items.sort(key=lambda r: r.get("status") != "pending")
    return json_ok({
        "requests": items,
        "pending": sum(1 for r in items if r.get("status") == "pending"),
    })


def _create_exit_explanation_request(card, full_name, date, by):
    """Sababsiz chiqish -> tushuntirish xati so'rovi (kind=exit)."""
    reqs = _load(EXP_REQUESTS_FILE, {"requests": {}})
    rid = f"{date}_{card}_exit"
    reqs.setdefault("requests", {})[rid] = {
        "req_id": rid, "card_number": card, "full_name": full_name,
        "kind": "exit", "date": date, "note": "Ruxsatsiz chiqish",
        "requested_by": by, "requested_at": _now_str(),
        "status": "pending",
    }
    _save(EXP_REQUESTS_FILE, reqs)


async def exit_review(request):
    """HR: chiqish izohini ko'rib chiqadi.
    {id, action: accept|show|reject, note?}
      accept — qabul qilindi
      show   — qabul + dashboard 'chiqish izohi'ga qo'shiladi
      reject — sababsiz: tushuntirish xati so'raladi (exit)"""
    auth, err = _auth_hr(request)
    if err:
        return err
    login_id, _ = auth
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    rid = str(body.get("id", "")).strip()
    action = str(body.get("action", "")).strip()
    note = str(body.get("note", "")).strip()
    data = _load(EXIT_MOBILE_FILE, {"requests": {}})
    rec = data.get("requests", {}).get(rid)
    if not rec:
        return json_err("Topilmadi", status=404)
    card = str(rec.get("card_number", ""))
    date = rec.get("date", "")
    rec["hr_note"] = note
    rec["reviewed_by"] = _by(login_id)
    rec["reviewed_at"] = _now_str()
    if action in ("accept", "show"):
        rec["status"] = "accepted"
        if action == "show":
            rec["shown"] = True
            er = _load(EXIT_REASONS_FILE, {})
            er[card] = {"date": date, "text": rec.get("text", ""),
                        "set_at": _now_str(), "by": _by(login_id)}
            _save(EXIT_REASONS_FILE, er)
    elif action == "reject":
        rec["status"] = "rejected"
        _create_exit_explanation_request(card, rec.get("full_name", ""), date, _by(login_id))
    else:
        return json_err("action: accept / show / reject")
    _save(EXIT_MOBILE_FILE, data)
    return json_ok({"ok": True})


async def reset_password(request):
    """HR: xodim parolini tiklaydi (unutganda). {card, password?}
    Vaqtinchalik parol beriladi, xodim birinchi kirishда o'zgartiradi."""
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    if not card:
        return json_err("card kerak")
    import accounts
    import random
    new_pass = str(body.get("password", "")).strip() or str(random.randint(100000, 999999))
    acc = accounts.get_account(card)
    if acc:
        accounts.set_password(card, new_pass, clear_must_change=False)
        accs = accounts.load_accounts()
        if card in accs:
            accs[card]["must_change"] = True
            accounts.save_accounts(accs)
    else:
        # hisob yo'q — yaratamiz
        name = _name_for_card(card)
        role = "employee"
        if roles is not None:
            try:
                rec = roles.get_record_by_card(card)
                if rec and rec.get("role"):
                    role = rec["role"]
            except Exception:
                pass
        accounts.create_account(card, new_pass, name=name, role=role,
                                must_change=True, overwrite=True)
    # Eski sessiyalarni to'liq bekor qilamiz (xavfsizlik)
    try:
        accounts.revoke_all_for_login(card)
    except Exception:
        pass
    return json_ok({"ok": True, "password": new_pass})


async def create_account(request):
    """HR: yangi xodimga PINFL (jshshir) orqali hisob yaratadi.
    {card, name?, role?, password?}
    Boshlang'ich parol berilmasa — jshshirning oxirgi 6 raqami.
    Xodim birinchi kirishда parolni o'zgartiradi (must_change)."""
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = "".join(ch for ch in str(body.get("card", "")) if ch.isdigit())
    if not card or len(card) < 6:
        return json_err("To'g'ri JSHSHIR (PINFL) kiriting")
    import accounts
    if accounts.get_account(card):
        return json_err("Bu JSHSHIR uchun hisob allaqachon mavjud. Parolni tiklash tugmasidan foydalaning.")
    # Ism: berilган bo'lsa — o'sha, aks holда cache/roles'дан topamiz
    name = str(body.get("name", "")).strip()
    if not name or name == "?":
        name = _name_for_card(card)
    role = str(body.get("role", "")).strip().lower()
    if role not in {"employee", "hr", "director"}:
        role = "employee"
        if roles is not None:
            try:
                rec = roles.get_record_by_card(card)
                if rec and rec.get("role"):
                    role = rec["role"]
            except Exception:
                pass
    new_pass = str(body.get("password", "")).strip() or card[-6:]
    accounts.create_account(card, new_pass, name=(name or "?"), role=role,
                            must_change=True, overwrite=False)
    return json_ok({"ok": True, "card": card, "name": name or "?",
                    "role": role, "password": new_pass})


async def accounts_list(request):
    """HR: barcha hisoblar ro'yxati (o'chirish/boshqarish uchun)."""
    auth, err = _auth_hr(request)
    if err:
        return err
    import accounts
    accs = accounts.load_accounts()
    rows = []
    for card, a in accs.items():
        rows.append({
            "card": card,
            "name": a.get("name", "") or "?",
            "role": a.get("role", "employee"),
            "active": a.get("active", True),
            "must_change": a.get("must_change", False),
        })
    rows.sort(key=lambda x: (x["role"] != "hr", x["role"] != "director", x["name"]))
    return json_ok({"accounts": rows, "total": len(rows)})


async def delete_account(request):
    """HR: xodim hisobini butunlay o'chiradi. {card}
    (Xato ochilgan yoki ishдан ketган xodим uchun.)"""
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = "".join(ch for ch in str(body.get("card", "")) if ch.isdigit())
    if not card:
        return json_err("JSHSHIR kerak")
    import accounts
    acc = accounts.get_account(card)
    if not acc:
        return json_err("Bu JSHSHIR uchun hisob topilmadi")
    # (accounts_list yuqorida e'lon qilingan)
    # O'zini o'chirib qo'ymasin
    if str(auth[0]) == card:
        return json_err("O'z hisobingizni o'chira olmaysiz")
    name = acc.get("name", "")
    accounts.delete_account(card)
    return json_ok({"ok": True, "card": card, "name": name})


# ─────────────────────────── XODIM QO'SHISH (users.xlsx) ───────────────────────────

def _norm_hdr(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").strip().lower())


# users.xlsx ustun sarlavhasi -> bizning kalit
_COL_ALIASES = {
    "familya": ["familya", "familiya", "lastname"],
    "ism": ["ism", "firstname", "name"],
    "sharif": ["sharif", "middlename", "otchestvo"],
    "card": ["cardnumber", "card", "kartaraqami", "jshshir", "pinfl"],
    "telegram": ["telegramid", "telegram", "tgid"],
    "role": ["role", "lavozimturi"],
    "photo": ["photofile", "photo", "rasm"],
    "category": ["category", "turkum", "kategoriya"],
    "birth": ["tugilgansana", "tugilgan", "birth"],
    "work_start": ["workstart", "ishboshlanishi", "ishvaqti", "starttime", "boshlanish"],
}


def _employee_xlsx_path():
    try:
        import live_worker_api as lw
        p = lw.find_existing_employee_file()
        if p:
            return Path(p)
    except Exception:
        pass
    for cand in (BASE_DIR / "users.xlsx", BASE_DIR / "employees.xlsx"):
        if cand.exists():
            return cand
    return BASE_DIR / "users.xlsx"


def _add_employee_row(fields: dict):
    """users.xlsx ga yangi xodim qatorini qo'shadi. (ok, xabar/xato) qaytaradi."""
    import openpyxl
    path = _employee_xlsx_path()
    if not path.exists():
        return False, "users.xlsx topilmadi"
    try:
        wb = openpyxl.load_workbook(path)
    except PermissionError:
        return False, "users.xlsx Excelда ochiq — yopib qайta urиниng"
    except Exception as e:
        return False, f"users.xlsx o'qib bo'lmadi: {e}"
    ws = wb.active
    # sarlavha qatorini topamiz (birinchi to'ldirilgan qator)
    hdr_row = 1
    for r in range(1, min(ws.max_row, 6) + 1):
        vals = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
        if any(v not in (None, "") for v in vals):
            hdr_row = r
            break
    # ustun nomi -> indeks
    col_of = {}
    serial_col = None
    for c in range(1, ws.max_column + 1):
        raw = ws.cell(row=hdr_row, column=c).value
        n = _norm_hdr(raw)
        if not n:
            continue
        matched = False
        for key, aliases in _COL_ALIASES.items():
            if n in aliases:
                col_of[key] = c
                matched = True
                break
        if not matched and serial_col is None and n in ("", "unnamed0", "no", "t", "tr", "raqam"):
            serial_col = c
    # 'Unnamed: 0' odatda 1-ustun (tartib raqami)
    if serial_col is None and _norm_hdr(ws.cell(row=hdr_row, column=1).value) in ("", "unnamed0"):
        serial_col = 1
    if "card" not in col_of or "familya" not in col_of:
        return False, "users.xlsx ustunlari tanilmadi (Familya/card number)"

    # dublikat tekshiruvi
    card = fields["card"]
    ccol = col_of["card"]
    for r in range(hdr_row + 1, ws.max_row + 1):
        v = ws.cell(row=r, column=ccol).value
        if v is None:
            continue
        vd = "".join(ch for ch in str(v) if ch.isdigit())
        if vd == card:
            return False, "Bu JSHSHIR allaqachon ro'yxatda bor"

    # yangi qator raqami — birinchi bo'sh qator
    new_row = hdr_row + 1
    while any(ws.cell(row=new_row, column=c).value not in (None, "")
             for c in range(1, ws.max_column + 1)):
        new_row += 1

    def put(key, val):
        if key in col_of and val not in (None, ""):
            ws.cell(row=new_row, column=col_of[key]).value = val

    put("familya", fields.get("familya", ""))
    put("ism", fields.get("ism", ""))
    put("sharif", fields.get("sharif", ""))
    ws.cell(row=new_row, column=ccol).value = int(card) if card.isdigit() else card
    put("role", fields.get("role", "employee"))
    put("category", fields.get("category", "oddiy"))
    put("photo", f"{card}.jpg")
    if fields.get("work_start"):
        put("work_start", fields["work_start"])
    if fields.get("telegram"):
        try:
            put("telegram", int(fields["telegram"]))
        except Exception:
            put("telegram", fields["telegram"])
    if serial_col:
        # tartib raqamini avvalgidan +1
        prev = 0
        for r in range(hdr_row + 1, new_row):
            v = ws.cell(row=r, column=serial_col).value
            try:
                prev = max(prev, int(v))
            except Exception:
                pass
        ws.cell(row=new_row, column=serial_col).value = prev + 1

    try:
        wb.save(path)
    except PermissionError:
        return False, "users.xlsx Excelда ochiq — yopib qайta urиниng"
    except Exception as e:
        return False, f"Saqlashда xato: {e}"
    return True, "ok"


async def employee_add(request):
    """HR: yangi xodimни users.xlsx ga qo'shadi va hisob ochadi.
    {familya, ism, sharif?, card, role?, category?, work_start?, telegram?}"""
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    familya = str(body.get("familya", "")).strip()
    ism = str(body.get("ism", "")).strip()
    sharif = str(body.get("sharif", "")).strip()
    card = "".join(ch for ch in str(body.get("card", "")) if ch.isdigit())
    if not familya or not ism:
        return json_err("Familiya va ism kerak")
    if len(card) < 9:
        return json_err("To'g'ri JSHSHIR (PINFL) kiriting")
    role = str(body.get("role", "")).strip().lower()
    if role not in {"employee", "hr", "director"}:
        role = "employee"
    category = str(body.get("category", "")).strip().lower() or "oddiy"
    work_start = str(body.get("work_start", "")).strip()
    telegram = str(body.get("telegram", "")).strip()

    ok, msg = _add_employee_row({
        "familya": familya, "ism": ism, "sharif": sharif, "card": card,
        "role": role, "category": category,
        "work_start": work_start, "telegram": telegram,
    })
    if not ok:
        return json_err(msg)

    # Hisобni darhol ochamiz (worker ham 10 sek ichida ochardi, lekin darhol bo'lsin)
    import accounts
    full_name = " ".join(x for x in [familya, ism, sharif] if x)
    pw = card[-6:] if len(card) >= 6 else card
    if not accounts.get_account(card):
        accounts.create_account(card, pw, name=full_name, role=role,
                                must_change=True, overwrite=False)

    # Rasmni nqaa (HR tizimi) dan ism bo'yicha tortishga urinamiz
    photo_ok, photo_msg = False, ""
    try:
        import fetch_all_photos
        photo_ok, photo_msg = fetch_all_photos.fetch_one_photo(
            card, familya=familya, ism=ism, full_name=full_name)
    except Exception as e:
        photo_msg = str(e)

    return json_ok({"ok": True, "card": card, "name": full_name,
                    "role": role, "password": pw,
                    "photo": photo_ok, "photo_msg": photo_msg})


async def photo_fetch_api(request):
    """HR: xodim rasmini nqaa (HR tizimi) dan ism bo'yicha tortadi. {card}"""
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = "".join(ch for ch in str(body.get("card", "")) if ch.isdigit())
    if not card:
        return json_err("JSHSHIR kerak")
    full = _name_for_card(card)
    if not full or full == "?":
        return json_err("Xodim ismi topilmadi")
    try:
        import fetch_all_photos
        ok, msg = fetch_all_photos.fetch_one_photo(card, full_name=full)
    except Exception as e:
        return json_err(f"Xato: {e}")
    if not ok:
        return json_err(msg)
    return json_ok({"ok": True, "card": card, "photo_file": msg, "name": full})


# ═══════════════════════ YO'QLAMA ═══════════════════════
# HR tadbir nomini yozadi, xodimlarni "bor / yo'q" deb belgilaydi,
# natijani Word yoki PDF bayonnoma qilib yuklab oladi.
# Qatnashmagan xodimdan ilova o'zi sabab so'raydi.

YOQLAMA_FILE = BASE_DIR / "yoqlama.json"


def _yoq_load():
    d = _load(YOQLAMA_FILE, {"items": []})
    return d if isinstance(d, dict) else {"items": []}


def _yoq_employees():
    """users.xlsx (live_cache) dagi barcha faol xodimlar — alifbo tartibida."""
    cache = _load(CACHE_FILE, {})
    out = []
    for r in cache.get("employees", []) or []:
        card = str(r.get("card_number", "") or "")
        if not card:
            continue
        out.append({"card_number": card, "full_name": r.get("full_name", "")})
    out.sort(key=lambda x: x["full_name"])
    return out


async def yoqlama_list(request):
    """HR: yo'qlamalar ro'yxati (yangidan eskiga)."""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    items = _yoq_load().get("items", [])
    out = []
    for it in items[:60]:
        marks = it.get("marks", {}) or {}
        yes = sum(1 for v in marks.values() if v)
        out.append({
            "id": it.get("id"), "title": it.get("title", ""),
            "date": it.get("date", ""), "time": it.get("time", ""),
            "place": it.get("place", ""),
            "yes": yes, "total": len(marks),
        })
    return json_ok({"items": out})


async def yoqlama_create(request):
    """HR: yangi yo'qlama ochadi. {title, date, time?, place?}
    Ro'yxat barcha xodimlar bilan to'ldiriladi (standart: hamma BOR)."""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    login_id, _ = auth
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    title = str(body.get("title", "")).strip()
    if len(title) < 3:
        return json_err("Tadbir nomini yozing")
    date = str(body.get("date", "")).strip() or _today()
    if not DATE_RE.match(date):
        return json_err("Sana formati: YYYY-MM-DD")
    emps = _yoq_employees()
    if not emps:
        return json_err("Xodimlar ro'yxati bo'sh")
    yid = uuid.uuid4().hex[:8]
    item = {
        "id": yid,
        "title": title,
        "date": date,
        "time": str(body.get("time", "")).strip(),
        "place": str(body.get("place", "")).strip(),
        "by": _by(login_id),
        "at": _now_str(),
        "employees": emps,
        "marks": {e["card_number"]: True for e in emps},   # standart: hamma bor
        "reasons": {},                                      # qatnashmaganlar javobi
    }
    d = _yoq_load()
    d.setdefault("items", []).insert(0, item)
    _save(YOQLAMA_FILE, d)
    return json_ok({"ok": True, "id": yid, "item": item})


async def yoqlama_get(request):
    """HR: bitta yo'qlamani to'liq ochadi."""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    yid = str(request.match_info.get("yid", "")).strip()
    it = next((x for x in _yoq_load().get("items", []) if str(x.get("id")) == yid), None)
    if not it:
        return json_err("Yo'qlama topilmadi", status=404)
    return json_ok({"item": it})


async def yoqlama_mark(request):
    """HR: belgilashni saqlaydi. {id, marks: {card: true/false}}"""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    yid = str(body.get("id", "")).strip()
    marks = body.get("marks") or {}
    if not isinstance(marks, dict):
        return json_err("marks noto'g'ri")
    d = _yoq_load()
    it = next((x for x in d.get("items", []) if str(x.get("id")) == yid), None)
    if not it:
        return json_err("Yo'qlama topilmadi", status=404)
    cur = it.get("marks", {}) or {}
    for k, v in marks.items():
        cur[str(k)] = bool(v)
    it["marks"] = cur
    it["updated_at"] = _now_str()
    _save(YOQLAMA_FILE, d)
    yes = sum(1 for v in cur.values() if v)
    return json_ok({"ok": True, "yes": yes, "total": len(cur)})


async def yoqlama_sign(request):
    """HR: yo'qlamani o'tkazgan xodimni tanlaydi va u imzolaydi.
    {id, card, signature}  — signature: data:image/png;base64,...
    Imzo hujjatga (PDF/Word) tushadi.
    """
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    yid = str(body.get("id", "")).strip()
    card = "".join(ch for ch in str(body.get("card", "")) if ch.isdigit())
    if not card:
        return json_err("Yo'qlamani o'tkazgan xodimni tanlang")

    d = _yoq_load()
    it = next((x for x in d.get("items", []) if str(x.get("id")) == yid), None)
    if not it:
        return json_err("Yo'qlama topilmadi", status=404)

    sig_file = None
    sig = body.get("signature")
    if sig:
        try:
            import mobile_api as _m
            sig_file = _m._save_signature("yoqlama_" + yid, sig)
        except Exception as e:
            return json_err(f"Imzo saqlanmadi: {e}", status=500)

    it["conductor"] = {"card_number": card, "full_name": _name_for_card(card)}
    if sig_file:
        it["signature_file"] = sig_file
    it["signed_at"] = _now_str()
    _save(YOQLAMA_FILE, d)
    return json_ok({"ok": True, "conductor": it["conductor"],
                    "signed": bool(sig_file)})


async def yoqlama_delete(request):
    """HR: yo'qlamani o'chiradi. {id}"""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    yid = str(body.get("id", "")).strip()
    d = _yoq_load()
    d["items"] = [x for x in d.get("items", []) if str(x.get("id")) != yid]
    _save(YOQLAMA_FILE, d)
    return json_ok({"ok": True})


async def yoqlama_doc(request):
    """HR: yo'qlama bayonnomasi — Word yoki PDF.
    /api/mobile/admin/yoqlama/doc/{yid}?fmt=docx|pdf  (token query orqali ham)
    """
    login_id, acc = _require_login(request)
    if not login_id:
        tok = request.query.get("token", "")
        if tok:
            try:
                import accounts as _ac
                acc = _ac.check_token(tok)
                login_id = (acc or {}).get("login") if acc else None
            except Exception:
                pass
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if _role_of(acc) not in ("hr", "director"):
        return json_err("Ruxsat yo'q", status=403)

    yid = str(request.match_info.get("yid", "")).strip()
    it = next((x for x in _yoq_load().get("items", []) if str(x.get("id")) == yid), None)
    if not it:
        return json_err("Yo'qlama topilmadi", status=404)

    fmt = (request.query.get("fmt", "pdf") or "pdf").lower()
    try:
        import yoqlama_doc as ydoc
        p = ydoc.build_docx(it) if fmt == "docx" else ydoc.build_pdf(it)
    except Exception as e:
        return json_err(f"Hujjat yasalmadi: {type(e).__name__}: {e}", status=500)

    ct = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          if fmt == "docx" else "application/pdf")
    resp = web.FileResponse(p, headers={"Content-Type": ct})
    return resp


async def monitor_set(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    enabled = bool(body.get("enabled"))
    state = _load(MONITOR_STATE_FILE, {})
    state["enabled"] = enabled
    _save(MONITOR_STATE_FILE, state)
    return json_ok({"ok": True, "enabled": enabled})


# ─────────────────────────── ROUTER ───────────────────────────


# ═══════════════════ SO'ROVNOMA (HR boshqaruvi) ═══════════════════
try:
    import surveys as _surveys
except Exception:
    _surveys = None


async def surveys_list(request):
    """So'rovnomalar ro'yxati — qisqacha natijasi bilan."""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    if _surveys is None:
        return json_err("So'rovnoma moduli yuklanmadi", status=500)
    out = []
    for it in _surveys.listing():
        r = _surveys.results(it["id"], with_voters=False) or {}
        out.append({
            "id": it["id"], "title": it["title"], "question": it.get("question", ""),
            "kind": it.get("kind", "leader"),
            "active": bool(it.get("active")), "created_at": it.get("created_at", ""),
            "closed_at": it.get("closed_at", ""),
            "total_votes": r.get("total_votes", 0),
            "eligible": r.get("eligible", 0), "turnout": r.get("turnout", 0),
        })
    return json_ok({
        "surveys": out, "link": "/ovoz",
        "kinds": [
            {"id": "leader", "name": _surveys.SURVEY_KINDS["leader"],
             "candidates": len(_surveys.leaders()),
             "voters": len(_surveys.eligible_voters("leader")),
             "question": "Eng yaxshi guruh rahbari deb kimni bilasiz?"},
            {"id": "yosh", "name": _surveys.SURVEY_KINDS["yosh"],
             "candidates": len(_surveys.young_employees()),
             "voters": len(_surveys.eligible_voters("yosh")),
             "question": "Eng yaxshi yosh xodim deb kimni bilasiz?"},
            {"id": "anketa", "name": _surveys.SURVEY_KINDS["anketa"],
             "candidates": len(_surveys.anketa_questions()),
             "voters": len(_surveys.eligible_voters("anketa")),
             "title": (_surveys.anketa_form() or {}).get("title", ""),
             "forms": _surveys.anketa_templates(),
             "question": ""},
        ],
        "candidates": len(_surveys.leaders()),
        "voters": len(_surveys.eligible_voters())})


async def surveys_create(request):
    """Yangi so'rovnoma yaratish."""
    auth, err = _auth_hr(request)
    if err:
        return err
    if _surveys is None:
        return json_err("So'rovnoma moduli yuklanmadi", status=500)
    try:
        body = await request.json()
    except Exception:
        body = {}
    title = str(body.get("title", "")).strip()
    if not title:
        return json_err("So'rovnoma nomini kiriting")
    kind = str(body.get("kind", "leader")).strip()
    it = _surveys.create(title, str(body.get("question", "")).strip(),
                         _by(auth[0]), kind=kind,
                         form_id=str(body.get("form_id", "")).strip())
    return json_ok({"ok": True, "id": it["id"],
                    "candidates": len(_surveys.survey_candidates(it))})


async def surveys_results(request):
    """To'liq natija — kim ovoz bergani va bermagani bilan (HR/rahbariyat)."""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    if _surveys is None:
        return json_err("So'rovnoma moduli yuklanmadi", status=500)
    r = _surveys.results(str(request.query.get("id", "")).strip(), with_voters=True)
    if not r:
        return json_err("So'rovnoma topilmadi", status=404)
    return json_ok(r)


async def surveys_action(request):
    """Yakunlash / qayta ochish / o'chirish."""
    auth, err = _auth_hr(request)
    if err:
        return err
    if _surveys is None:
        return json_err("So'rovnoma moduli yuklanmadi", status=500)
    try:
        body = await request.json()
    except Exception:
        body = {}
    sid = str(body.get("id", "")).strip()
    act = str(body.get("action", "")).strip()
    fn = {"close": _surveys.close, "reopen": _surveys.reopen,
          "delete": _surveys.delete}.get(act)
    if not fn:
        return json_err("Noma'lum amal")
    return json_ok({"ok": bool(fn(sid))})


async def anketa_tpl_get(request):
    """Anketa shablonini konstruktor uchun olish."""
    auth, err = _auth_hr(request)
    if err:
        return err
    if _surveys is None:
        return json_err("So'rovnoma moduli yuklanmadi", status=500)
    d = _surveys.template_get(str(request.query.get("id", "")))
    if not d:
        return json_err("Anketa topilmadi", status=404)
    return json_ok(d)


async def anketa_tpl_save(request):
    """Konstruktorda tuzilgan anketani saqlash."""
    auth, err = _auth_hr(request)
    if err:
        return err
    if _surveys is None:
        return json_err("So'rovnoma moduli yuklanmadi", status=500)
    try:
        body = await request.json()
    except Exception:
        body = {}
    ok_, msg, fid = _surveys.template_save(body if isinstance(body, dict) else {})
    if not ok_:
        return json_err(msg)
    return json_ok({"ok": True, "id": fid})


async def anketa_tpl_delete(request):
    auth, err = _auth_hr(request)
    if err:
        return err
    if _surveys is None:
        return json_err("So'rovnoma moduli yuklanmadi", status=500)
    try:
        body = await request.json()
    except Exception:
        body = {}
    return json_ok({"ok": _surveys.template_delete(str(body.get("id", "")))})


async def employee_remove(request):
    """Xodimni tizimdan butunlay chiqarish (users.xlsx + hisob + bog'liq fayllar)."""
    auth, err = _auth_hr(request)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}
    card = re.sub(r"[^0-9]", "", str(body.get("card", "")))
    if len(card) < 9:
        return json_err("JSHSHIR raqamini to'liq kiriting")
    try:
        import xodim_chiqarish
        ok_, msg, detail = xodim_chiqarish.remove_employee(card)
    except Exception as e:
        return json_err(f"Xatolik: {e}", status=500)
    if not ok_:
        return json_err(msg)
    return json_ok({"ok": True, "message": msg,
                    "full_name": detail.get("full_name", ""),
                    "cleaned": detail.get("cleaned", {}),
                    "backup": detail.get("backup", "")})


async def surveys_answer_doc(request):
    """Muayyan javobni tanlagan xodimlar ro'yxati (Word)."""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    sid = str(request.query.get("id", "")).strip()
    qid = str(request.query.get("q", "")).strip()
    val = str(request.query.get("value", "")).strip()
    if not (sid and qid and val):
        return json_err("id, q va value kerak")
    try:
        import anketa_doc
        path = anketa_doc.build_answer_list_docx(sid, qid, val)
    except Exception as e:
        return json_err(f"Hujjat yaratilmadi: {e}", status=500)
    if not path or not Path(path).exists():
        return json_err("Topilmadi", status=404)
    return web.FileResponse(path, headers={
        "Content-Disposition": f'attachment; filename="{Path(path).name}"'})


async def surveys_doc(request):
    """Anketa natijasini Word faylda yuklab berish."""
    auth, err = _auth_hr(request, allow_director=True)
    if err:
        return err
    sid = str(request.query.get("id", "")).strip()
    try:
        import anketa_doc
        path = anketa_doc.build_docx(sid)
    except Exception as e:
        return json_err(f"Hujjat yaratilmadi: {e}", status=500)
    if not path or not Path(path).exists():
        return json_err("Bu so'rovnoma anketa emas yoki topilmadi", status=404)
    name = Path(path).name
    return web.FileResponse(path, headers={
        "Content-Disposition": f'attachment; filename="{name}"'})


def register(app, require_login, role_of, ok, errf):
    """mobile_api.build_app() ichidan chaqiriladi."""
    global _require_login, _role_of, json_ok, json_err
    _require_login = require_login
    _role_of = role_of
    json_ok = ok
    json_err = errf

    p = "/api/mobile/admin"
    app.router.add_get(f"{p}/surveys", surveys_list)
    app.router.add_post(f"{p}/surveys/create", surveys_create)
    app.router.add_get(f"{p}/surveys/results", surveys_results)
    app.router.add_get(f"{p}/surveys/doc", surveys_doc)
    app.router.add_get(f"{p}/surveys/answer_doc", surveys_answer_doc)
    app.router.add_post(f"{p}/surveys/action", surveys_action)
    app.router.add_get(f"{p}/anketa/get", anketa_tpl_get)
    app.router.add_post(f"{p}/anketa/save", anketa_tpl_save)
    app.router.add_post(f"{p}/anketa/delete", anketa_tpl_delete)
    app.router.add_get(f"{p}/overview", overview)
    app.router.add_post(f"{p}/nvr_refresh", nvr_refresh)
    app.router.add_get(f"{p}/exemptions", exemptions_list)
    app.router.add_post(f"{p}/exemptions/add", exemptions_add)
    app.router.add_post(f"{p}/exemptions/remove", exemptions_remove)
    app.router.add_get(f"{p}/reasons", reasons_list)
    app.router.add_post(f"{p}/reason", reason_set)
    app.router.add_post(f"{p}/exit_reason", exit_reason_set)
    app.router.add_get(f"{p}/late_excused", late_excused_list)
    app.router.add_post(f"{p}/late_excused", late_excused_toggle)
    app.router.add_get(f"{p}/holidays", holidays_list)
    app.router.add_post(f"{p}/holidays/add", holidays_add)
    app.router.add_post(f"{p}/holidays/remove", holidays_remove)
    app.router.add_get(f"{p}/hidden", hidden_list)
    app.router.add_post(f"{p}/hidden/toggle", hidden_toggle)
    app.router.add_get(f"{p}/worktime", worktime_list)
    app.router.add_post(f"{p}/worktime/set", worktime_set)
    app.router.add_get(f"{p}/attendance_edit", attendance_edit_get)
    app.router.add_post(f"{p}/attendance_edit", attendance_edit_set)
    # Xabar yuborish (Telegram bot davridan qolgan) — o'chirilgan
    # app.router.add_post(f"{p}/broadcast", broadcast)
    app.router.add_get(f"{p}/announce/list", announce_list)
    app.router.add_post(f"{p}/announce/delete", announce_delete)
    app.router.add_get(f"{p}/explanations", explanations_list)
    app.router.add_post(f"{p}/explanations/status", explanations_status)
    app.router.add_get(f"{p}/yoqlama", yoqlama_list)
    app.router.add_post(f"{p}/yoqlama/create", yoqlama_create)
    app.router.add_get(f"{p}/yoqlama/{{yid}}", yoqlama_get)
    app.router.add_post(f"{p}/yoqlama/mark", yoqlama_mark)
    app.router.add_post(f"{p}/yoqlama/sign", yoqlama_sign)
    app.router.add_post(f"{p}/yoqlama/delete", yoqlama_delete)
    app.router.add_get(f"{p}/yoqlama/doc/{{yid}}", yoqlama_doc)
    app.router.add_post(f"{p}/monitor", monitor_set)
    app.router.add_get(f"{p}/interns", interns_list)
    app.router.add_post(f"{p}/intern_active", intern_active_set)
    app.router.add_get(f"{p}/exit/list", exit_list)
    app.router.add_post(f"{p}/exit/review", exit_review)
    app.router.add_post(f"{p}/reset_password", reset_password)
    app.router.add_post(f"{p}/create_account", create_account)
    app.router.add_post(f"{p}/delete_account", delete_account)
    app.router.add_post(f"{p}/employee_remove", employee_remove)
    app.router.add_get(f"{p}/accounts_list", accounts_list)
    app.router.add_post(f"{p}/employee_add", employee_add)
    app.router.add_post(f"{p}/photo_fetch_api", photo_fetch_api)
