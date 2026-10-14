"""
mobile_api.py — mobil ilova (PWA/APK) uchun backend API.
(2026-07-16: rasm, tushuntirish xati so'rovi/yuborish qo'shildi)

Alohida servis (port 8090) — ishlaydigan dashboard'ga (8080) tegmaydi.
Bir xil ma'lumot fayllarini o'qiydi: live_cache.json, monthly_report.json,
employee_map.json.

Rollar:
  • employee — faqat O'ZINI ko'radi
  • hr / director — HAMMANI ko'radi (+ HR boshqaruv keyingi bosqichda)

Endpointlar:
  POST /api/mobile/login      {login, password}  -> {token, role, name, must_change}
  POST /api/mobile/logout     (Bearer)
  POST /api/mobile/password   {new_password}     (Bearer) parol o'zgartirish
  GET  /api/mobile/me         (Bearer) -> o'zining bugungi holati + oylik statistikasi
  GET  /api/mobile/all        (Bearer, faqat hr/director) -> hamma xodim holati

Ishga tushirish:
    python mobile_api.py
"""

import os
import re
import json
import time
from pathlib import Path
from datetime import datetime

from aiohttp import web

import accounts

try:
    import roles
except Exception:
    roles = None

try:
    import surveys
except Exception:
    surveys = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(".")
CACHE_FILE = BASE_DIR / "live_cache.json"
MONTHLY_FILE = BASE_DIR / "monthly_report.json"
MAP_FILE = BASE_DIR / "employee_map.json"
PHOTOS_DIR = BASE_DIR / "photos"
EXPLANATIONS_FILE = BASE_DIR / "explanations.json"          # main17 bilan umumiy
EXP_REQUESTS_FILE = BASE_DIR / "explanation_requests.json"  # HR so'rovlari (mobil)
HIDDEN_FILE = BASE_DIR / "dashboard_hidden.json"            # dashboard bilan umumiy
OLIMLAR_FILE = BASE_DIR / "olimlar.json"                    # PhD/DSc belgilangan xodimlar
PHOTO_OVERRIDES_FILE = BASE_DIR / "photo_overrides.json"    # HR yuklagan rasmlar (card -> fayl)

PORT = int(os.getenv("MOBILE_API_PORT", "8090"))


def _load(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


API_PHOTOS_FILE = BASE_DIR / "api_photos.json"


def _photo_for(card):
    """Xodim/amaliyotchi rasmi fayl nomi (photos/ ichida).
    1) HR qo'lda yuklagan (photo_overrides.json) — ustuvor
    2) API'dan yuklangan (api_photos.json — fetch_all_photos.py)
    3) users.xlsx (roles) dagi photo_file
    4) photos/<card>.jpg|png — to'g'ridan-to'g'ri fayl"""
    card = str(card)
    # 1) HR qo'lda
    try:
        ov = _load(PHOTO_OVERRIDES_FILE, {})
        f = ov.get(card) if isinstance(ov, dict) else None
        if f and (PHOTOS_DIR / str(f)).exists():
            return str(f)
    except Exception:
        pass
    # 2) API'dan yuklangan
    try:
        ap = _load(API_PHOTOS_FILE, {})
        f = ap.get(card) if isinstance(ap, dict) else None
        if f and (PHOTOS_DIR / str(f)).exists():
            return str(f)
    except Exception:
        pass
    # 3) roles / users.xlsx
    if roles is not None:
        try:
            rec = roles.get_record_by_card(card)
            if rec and rec.get("photo_file") and (PHOTOS_DIR / str(rec["photo_file"])).exists():
                return str(rec["photo_file"])
        except Exception:
            pass
    # 4) photos/<card>.<ext> to'g'ridan-to'g'ri
    for ext in ("jpg", "jpeg", "png"):
        if (PHOTOS_DIR / f"{card}.{ext}").exists():
            return f"{card}.{ext}"
    return None


def _enrich_photos(rows):
    for r in rows or []:
        r["photo_file"] = _photo_for(str(r.get("card_number", "")))
    return rows


def _load_hidden_cards():
    """Dashboard'da yashirilgan xodimlar (dashboard_hidden.json)."""
    data = _load(HIDDEN_FILE, {"hidden_cards": []})
    if not isinstance(data, dict):
        return set()
    return set(str(c) for c in data.get("hidden_cards", []))


def _filter_hidden(rows):
    """Yashirilgan card raqamlarni ro'yxatdan olib tashlaydi (dashboard kabi)."""
    hidden = _load_hidden_cards()
    if not hidden:
        return list(rows or [])
    return [r for r in (rows or []) if str(r.get("card_number", "")) not in hidden]


# ─────────────── IZOH / SAFARI / TA'TIL (dashboard bilan bir xil) ───────────────

REASONS_FILE = BASE_DIR / "reasons.json"
EXIT_REASONS_FILE = BASE_DIR / "exit_reasons.json"
LATE_EXCUSED_FILE = BASE_DIR / "late_excused.json"
EXEMPTIONS_FILE = BASE_DIR / "exemptions.json"
EXIT_TRACK_FILE = BASE_DIR / "exit_tracking.json"     # bot monitor yozadi (10+ daqiqa tashqarida)
EXIT_MOBILE_FILE = BASE_DIR / "exit_mobile.json"      # xodim mobil orqali yozgan chiqish izohlari


def _exit_prompt_for(card):
    """Xodim hozir 10+ daqiqa binoni tark etganmi? (bot exit_tracking.json dan).
    Bot faqat ish vaqti + ish kuni + 'oddiy' turkumда yozadi, shu sabab qo'shimcha
    tekshiruv kerak emas."""
    tr = _load(EXIT_TRACK_FILE, {}).get(str(card))
    if not isinstance(tr, dict) or not tr.get("warned"):
        return None
    since = str(tr.get("exit_time", ""))
    mins = None
    try:
        mins = int((datetime.now() - datetime.strptime(since, "%Y-%m-%d %H:%M:%S")).total_seconds() // 60)
    except Exception:
        pass
    return {"exit_time": tr.get("last_event", ""), "minutes": mins}


ANNOUNCE_FILE = BASE_DIR / "announcements.json"


def _active_announcements():
    """Muddati o'tmagan e'lonlar (HR/rahbar yuborgan). Telegram bot o'rniga."""
    data = _load(ANNOUNCE_FILE, {"items": []})
    items = data.get("items", []) if isinstance(data, dict) else []
    today = datetime.now().strftime("%Y-%m-%d")
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        until = str(it.get("until", "") or "")
        if until and until < today:
            continue
        out.append({"id": it.get("id"), "text": it.get("text", ""),
                    "date": it.get("date", "")})
        if len(out) >= 5:
            break
    return out


def _my_exit_today(card):
    """Xodimning bugungi chiqish izohi (yozgan bo'lsa)."""
    rid = f"{_today_iso()}_{card}"
    return _load(EXIT_MOBILE_FILE, {"requests": {}}).get("requests", {}).get(rid)


def _today_iso():
    return datetime.now().strftime("%Y-%m-%d")


def _reasons_today(path):
    """{card: text} — faqat bugungi kunga tegishli izohlar."""
    d = _today_iso()
    out = {}
    for card, info in (_load(path, {}) or {}).items():
        if isinstance(info, dict) and str(info.get("date", ""))[:10] in ("", d):
            txt = str(info.get("text", "") or "").strip()
            if txt:
                out[str(card)] = txt
    return out


def _excused_today():
    """Bugun 'sababli' (uzrli) deb belgilangan kartalar to'plami."""
    d = _today_iso()
    out = set()
    for card, info in (_load(LATE_EXCUSED_FILE, {}) or {}).items():
        if isinstance(info, dict):
            if "date" in info:                       # eski format
                if str(info.get("date", ""))[:10] == d:
                    out.add(str(card))
            elif d in info:                          # yangi format (sana kalitlari)
                out.add(str(card))
    return out


def _attach_reason(rows, reasons):
    for r in rows or []:
        txt = reasons.get(str(r.get("card_number", "")))
        if txt:
            r["reason"] = txt
    return rows


def _attach_excused(rows, excused):
    for r in rows or []:
        if str(r.get("card_number", "")) in excused:
            r["excused"] = True
    return rows


def _exemptions_split():
    """Bugun faol ruxsat/safarilarni ikkiga ajratadi -> (safari_list, tatil_list)."""
    d = _today_iso()
    data = _load(EXEMPTIONS_FILE, {"records": []})
    records = data.get("records", []) if isinstance(data, dict) else []
    # Takrorlar: eng so'nggi set_at ustun. card -> info
    active = {}
    for info in records:
        if not isinstance(info, dict) or info.get("active") is False:
            continue
        df = str(info.get("date_from", ""))[:10]
        dt = str(info.get("date_to", "") or df)[:10]
        if df and not (df <= d <= (dt or df)):
            continue
        card = str(info.get("card_number", "") or "")
        if not card:
            continue
        prev = active.get(card)
        if prev is None or str(info.get("set_at", "")) >= str(prev.get("set_at", "")):
            active[card] = info
    safari, tatil = [], []
    for card, info in active.items():
        item = {
            "card_number": card,
            "full_name": info.get("full_name") or info.get("name") or "?",
            "note": info.get("note", ""),
            "date_from": info.get("date_from", ""),
            "date_to": info.get("date_to", ""),
            "photo_file": _photo_for(card),
        }
        ty = str(info.get("type") or "").lower().strip()
        if ty in ("safari", "safar", "xizmat_safari", "xizmat safari", "komandirovka"):
            safari.append(item)
        elif ty in ("ruxsat", "tatil", "mehnat_tatili", "mehnat tatili", "tatil_mehnat"):
            tatil.append(item)
    return safari, tatil


# ─────────────────────────── AUTH YORDAMCHILARI ───────────────────────────

def _bearer(request):
    h = request.headers.get("Authorization", "")
    if h.startswith("Bearer "):
        return h[7:].strip()
    # ba'zi klientlar token'ni query'да yuboradi
    return request.query.get("token", "").strip()


def _require_login(request):
    """Token tekshiradi. (login, account) yoki (None, None)."""
    token = _bearer(request)
    login = accounts.check_token(token)
    if not login:
        return None, None
    acc = accounts.get_account(login)
    if not acc or not acc.get("active", True):
        return None, None
    return login, acc


def _role_of(acc):
    return (acc.get("role") or "employee").lower()


def _can_view_all(login_id, acc):
    """Hammani kim ko'ra oladi: HR, direktor, super_admin va 'rahbar' turkumi
    (o'rinbosarlar)."""
    if _role_of(acc) in ("hr", "director", "super_admin"):
        return True
    if roles is not None:
        try:
            rec = roles.get_record_by_card(str(login_id))
            if rec and str(rec.get("category", "")).lower() == "rahbar":
                return True
        except Exception:
            pass
    return False


def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


def json_ok(data, status=200):
    return _cors(web.json_response(data, status=status))


def json_err(message, status=400):
    return _cors(web.json_response({"error": message}, status=status))


# ─────────────────────────── MA'LUMOT ───────────────────────────

def _find_employee_in_cache(card):
    """live_cache.json 'employees' ro'yxatidan card bo'yicha topadi."""
    cache = _load(CACHE_FILE, {})
    for r in cache.get("employees", []) or []:
        if str(r.get("card_number")) == str(card):
            return r, cache
    return None, cache


def _monthly_for(card):
    """monthly_report.json dan xodimning oylik statistikasi + reyting o'rni."""
    rep = _load(MONTHLY_FILE, {})
    out = {"year_month": rep.get("year_month", ""), "work": None, "late": None,
           "rank": None}
    card = str(card)
    # Ish soatlari reytingi (top_work total_minutes bo'yicha kamayish tartibida)
    tw = rep.get("top_work", []) or []
    for i, r in enumerate(tw):
        if str(r.get("card_number")) == card:
            out["work"] = r
            out["rank"] = {"work_pos": i + 1, "work_total": len(tw)}
            break
    # Kechikish reytingi (faqat kechikkanlar orasida)
    tl = [r for r in (rep.get("top_late", []) or []) if (r.get("late_count") or 0) > 0]
    for i, r in enumerate(tl):
        if str(r.get("card_number")) == card:
            out["late"] = r
            if out["rank"] is None:
                out["rank"] = {}
            out["rank"]["late_pos"] = i + 1
            out["rank"]["late_total"] = len(tl)
            break
    return out


# ─────────────────────────── ENDPOINTLAR ───────────────────────────

# Brute-force himoyasi (xotirada): login+IP bo'yicha xato urinishlar.
_LOGIN_FAILS = {}          # {key: [timestamp, ...]}
_LOGIN_MAX_FAILS = 5       # necha marta xato -> bloklash
_LOGIN_WINDOW = 300        # 5 daqiqa ichida
_LOGIN_BLOCK = 900         # 15 daqiqa bloklash


_TRUSTED_PROXY_IPS = ("127.0.0.1", "::1")


def _client_ip(request):
    """Haqiqiy mijoz IP'si.

    XAVFSIZLIK: X-Real-IP/X-Forwarded-For sarlavhalariga FAQAT so'rov
    to'g'ridan-to'g'ri shu serverdagi ishonchli proksidan (nginx,
    127.0.0.1) kelganda ishonamiz. Aks holda (masalan kimdir backend
    portiga — 8090 — to'g'ridan-to'g'ri ulansa) bu sarlavhalar mijozning
    o'zi tomonidan soxtalashtirilgan bo'lishi mumkin — X-Forwarded-For'ni
    proksi faqat QO'SHADI (almashtirmaydi), shu sabab uning birinchi
    qiymatiga ko'r-ko'rona ishonib bo'lmaydi.
    """
    remote = str(request.remote or "")
    if remote not in _TRUSTED_PROXY_IPS:
        return remote or "?"
    xri = request.headers.get("X-Real-IP", "").strip()
    if xri:
        return xri
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return remote or "?"


def _login_blocked(key):
    now = time.time()
    fails = [t for t in _LOGIN_FAILS.get(key, []) if now - t < _LOGIN_BLOCK]
    _LOGIN_FAILS[key] = fails
    recent = [t for t in fails if now - t < _LOGIN_WINDOW]
    return len(recent) >= _LOGIN_MAX_FAILS


def _login_fail(key):
    _LOGIN_FAILS.setdefault(key, []).append(time.time())


def _is_internal_ip(ip: str) -> bool:
    return ip == "::1" or ip.startswith(("127.", "10.", "192.168.", "172.16.", "172.17.",
                                          "172.18.", "172.19.", "172.2", "172.30.", "172.31."))


def _is_external(request) -> bool:
    """So'rov internet orqali (nginx/davomat.uz yoki Cloudflare tunnel) keldimi?

    `_client_ip()` orqali HAQIQIY mijoz IP'sini oladi (ishonchli proksi —
    127.0.0.1'dagi nginx — orqali kelgan bo'lsagina X-Real-IP/
    X-Forwarded-For'ga ishonadi, aks holda soxtalashtirish xavfi bor).
    Agar haqiqiy IP ichki tarmoqniki bo'lsa — tashqi emas.
    """
    if request.headers.get("CF-Connecting-IP") or request.headers.get("CF-Ray"):
        return True
    ip = str(_client_ip(request) or "")
    return not _is_internal_ip(ip)


async def login(request):
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    lg = str(body.get("login", "")).strip()
    pw = str(body.get("password", ""))
    if not lg or not pw:
        return json_err("login va password kerak")
    key = f"{lg}|{_client_ip(request)}"
    if _login_blocked(key):
        return json_err("Juda ko'p urinish. 15 daqiqadan so'ng qayta urining.", status=429)
    acc = accounts.authenticate(lg, pw)
    if not acc:
        _login_fail(key)
        return json_err("Login yoki parol noto'g'ri", status=401)
    # ── Dastlabki parol + internet orqali kirish = TAQIQ ──
    # Dastlabki parol JSHSHIRning oxirgi 6 raqami. JSHSHIRni bilgan
    # odam internetdan kirib, parolni o'zi almashtirib olishi mumkin.
    # Shuning uchun parolini hali almashtirmagan xodim faqat idorada
    # (mahalliy tarmoqda) kirishi mumkin.
    if acc.get("must_change") and _is_external(request):
        return json_err(
            "Parolingiz hali dastlabki holatda. Xavfsizlik uchun uni "
            "birinchi marta ish joyidagi tarmoqdan almashtirishingiz kerak. "
            "Kadrlar bo'limiga murojaat qiling.", status=403)
    _LOGIN_FAILS.pop(key, None)   # muvaffaqiyatli — tozalaymiz
    token = accounts.issue_token(lg)
    resp = json_ok({
        "token": token,
        "role": _role_of(acc),
        "view_all": _can_view_all(lg, acc),
        "name": acc.get("name", ""),
        "must_change": bool(acc.get("must_change", False)),
    })
    # Rasmlar (img teglari) uchun — cookie (header yubora olmaydi)
    try:
        resp.set_cookie("sess", token, max_age=accounts.TOKEN_TTL,
                        httponly=True, samesite="Lax", path="/")
    except Exception:
        pass
    return resp


async def logout(request):
    accounts.revoke_token(_bearer(request))
    resp = json_ok({"ok": True})
    try:
        resp.del_cookie("sess", path="/")
    except Exception:
        pass
    return resp


async def change_password(request):
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    newp = str(body.get("new_password", ""))
    if len(newp) < 6:
        return json_err("Parol kamida 6 belgi bo'lsin")
    if newp.strip() == "" or newp == str(login_id):
        return json_err("Parol JSHSHIR yoki bo'sh bo'lmasin")
    accounts.set_password(login_id, newp)
    # Boshqa qurilmalardagi eski sessiyalarni bekor qilamiz (joriysini qoldiramiz)
    try:
        accounts.revoke_all_for_login(login_id, except_token=_bearer(request))
    except Exception:
        pass
    return json_ok({"ok": True})


async def me(request):
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    card = login_id  # login = jshshir
    row, cache = _find_employee_in_cache(card)
    monthly = _monthly_for(card)
    # O'zining bugungi izohi (dashboard bilan bir xil manba)
    if row:
        rtxt = _reasons_today(REASONS_FILE).get(str(card))
        if rtxt:
            row["reason"] = rtxt
        if str(card) in _excused_today():
            row["excused"] = True
    my_exit = _my_exit_today(card)
    return json_ok({
        "name": acc.get("name", ""),
        "role": _role_of(acc),
        "view_all": _can_view_all(login_id, acc),
        "card_number": card,
        "photo_file": _photo_for(card),
        "today": row or {"status": "nomalum", "timeline": []},
        "updated_at": cache.get("updated_at", ""),
        "monthly": monthly,
        # Binoni tark etish (10+ daqiqa) — hali izoh yozmagan bo'lsa oyna chiqadi
        "exit_prompt": (_exit_prompt_for(card) if not my_exit else None),
        "my_exit": my_exit,
        # HR/rahbar e'lonlari (Telegram bot o'rniga — ilova ichida)
        "announcements": _active_announcements(),
        # Yo'qlamalar: qatnashdimi / sabab so'ralyaptimi
        "yoqlama": _my_yoqlama(card),
    })


async def monthly_for_card(request):
    """Bitta xodimning oylik statistikasi (kechikish/kelmaslik kunlari) — HR/rahbar yoki egasi."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    card = str(request.match_info.get("card", "")).strip()
    if not card:
        return json_err("card kerak")
    if not _can_view_all(login_id, acc) and str(card) != str(login_id):
        return json_err("Ruxsat yo'q", status=403)
    return json_ok({"monthly": _monthly_for(card)})


MONTHLY_DIR = BASE_DIR / "monthly_reports"     # arxiv: monthly_reports/YYYY-MM.json

# Reytinglarda ko'rsatilmaydigan turkumlar.
#   haydovchi — ish vaqti tabiatan tartibsiz (erta/kech yurishadi)
#   rahbar    — direktor va o'rinbosarlari
# Ularning shaxsiy statistikasi saqlanadi, faqat reytingda qatnashmaydi.
RATING_EXCLUDE_CATEGORIES = {"haydovchi", "rahbar"}


def _rating_excluded(card):
    if roles is None:
        return False
    try:
        return str(roles.get_category_by_card(str(card)) or "").lower() in RATING_EXCLUDE_CATEGORIES
    except Exception:
        return False
_BUILDING = set()                               # hozir qurilayotgan oylar


def _month_report(ym):
    """Oylik hisobot: joriy oy -> monthly_report.json, eskisi -> arxivdan."""
    cur = _load(MONTHLY_FILE, {})
    if not ym or str(cur.get("year_month", "")) == ym:
        return cur
    p = MONTHLY_DIR / f"{ym}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _available_months():
    """Reyting mavjud bo'lgan oylar (yangidan eskiga)."""
    out = set()
    cur = _load(MONTHLY_FILE, {}).get("year_month", "")
    if cur:
        out.add(str(cur))
    try:
        for p in MONTHLY_DIR.glob("*.json"):
            if re.match(r"^\d{4}-\d{2}$", p.stem):
                out.add(p.stem)
    except Exception:
        pass
    return sorted(out, reverse=True)


def _build_month_bg(ym):
    """Oylik hisobotni fon oqimida quradi va arxivga yozadi (sekin — 1-2 daqiqa)."""
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


async def late_list(request):
    """HR/rahbar: oylik KECHIKUVCHILAR ro'yxati — eng ko'p kechikkandan boshlab.

    /api/mobile/late?month=YYYY-MM
    """
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q", status=403)

    ym = str(request.query.get("month", "")).strip()
    if ym and not re.match(r"^\d{4}-\d{2}$", ym):
        return json_err("Oy formati: YYYY-MM")
    rep = _month_report(ym) if ym else _load(MONTHLY_FILE, {})
    if rep is None:
        _build_month_bg(ym)
        return json_ok({"year_month": ym, "building": True, "late": [], "total": 0,
                        "months": _available_months()})

    rows = []
    for r in (rep.get("top_late", []) or []):
        cnt = int(r.get("late_count") or 0)
        if cnt <= 0:
            continue
        card = str(r.get("card_number", ""))
        if _rating_excluded(card):      # haydovchilar reytingga kirmaydi
            continue
        rows.append({
            "card_number": card,
            "full_name": r.get("full_name", ""),
            "late_count": cnt,
            "late_total": int(r.get("late_total") or cnt),
            "late_excused": int(r.get("late_excused") or 0),
            "work_start": r.get("work_start", ""),
            "late_days": r.get("late_days", []),
        })
    # Eng ko'p kechikkan birinchi
    rows.sort(key=lambda x: (-x["late_count"], x["full_name"]))
    for i, r in enumerate(rows, 1):
        r["pos"] = i
    return json_ok({
        "year_month": rep.get("year_month", ""),
        "total": len(rows),
        "late": rows,
        "months": _available_months(),
    })


async def rating_months(request):
    """Reyting uchun mavjud oylar ro'yxati."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    return json_ok({"months": _available_months(),
                    "current": _load(MONTHLY_FILE, {}).get("year_month", "")})


async def rating_list(request):
    """Oylik reyting ro'yxati (ish soatlari bo'yicha).
    Hamma xodim BARCHANING o'rnini ko'radi, lekin SOATLAR faqat HR/rahbarga.
    O'zining soatini har kim o'zi ko'radi."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    ym = str(request.query.get("month", "")).strip()
    if ym and not re.match(r"^\d{4}-\d{2}$", ym):
        return json_err("Oy formati: YYYY-MM")
    rep = _month_report(ym) if ym else _load(MONTHLY_FILE, {})
    if rep is None:
        # Bu oy hali hisoblanmagan — fonda quramiz, ilova keyin qayta so'raydi
        _build_month_bg(ym)
        return json_ok({"year_month": ym, "building": True, "rating": [],
                        "total": 0, "months": _available_months()})
    can_all = _can_view_all(login_id, acc)
    rows = []
    _tw = [r for r in (rep.get("top_work", []) or [])
           if not _rating_excluded(r.get("card_number"))]
    for i, r in enumerate(_tw):
        card = str(r.get("card_number", ""))
        mine = card == str(login_id)
        item = {
            "pos": i + 1,
            "full_name": r.get("full_name", ""),
            "me": mine,
        }
        # Kartani faqat HR/rahbar oladi (qatorni bosib kunlarni ko'rish uchun)
        if can_all:
            item["card_number"] = card
        # Soat/kun faqat HR-rahbarga yoki o'ziga
        if can_all or mine:
            item["total_hours_str"] = r.get("total_hours_str", "")
            item["days_worked"] = r.get("days_worked")
            item["avg_hours_str"] = r.get("avg_hours_str", "")
        rows.append(item)
    return json_ok({
        "year_month": rep.get("year_month", ""),
        "total": len(rows),
        "show_hours": can_all,
        "rating": rows,
        "months": _available_months(),
        "updated_at": rep.get("updated_at", ""),
    })


async def days_for_card(request):
    """Xodimning oy bo'yicha KUNLIK tarixi — qaysi kuni nechada kelgan/ketgan.

    /api/mobile/days/{card}?month=YYYY-MM
    Egasi yoki HR/rahbar ko'ra oladi. Ma'lumot biometrik tizimdan olinadi.
    """
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    card = str(request.match_info.get("card", "")).strip()
    if not card:
        return json_err("card kerak")
    if not _can_view_all(login_id, acc) and str(card) != str(login_id):
        return json_err("Ruxsat yo'q", status=403)

    ym = str(request.query.get("month", "")).strip() or datetime.now().strftime("%Y-%m")
    if not re.match(r"^\d{4}-\d{2}$", ym):
        return json_err("Oy formati: YYYY-MM")

    import calendar as _cal
    y, mo = map(int, ym.split("-"))
    start = f"{ym}-01"
    end = f"{ym}-{_cal.monthrange(y, mo)[1]:02d}"
    today = datetime.now().strftime("%Y-%m-%d")
    if end > today:
        end = today

    try:
        import biocontrol_api as _bio
        days_data = _bio.get_events_by_day(card, start, end)
    except Exception as e:
        return json_err(f"Biometrik tizimga ulanib bo'lmadi: {e}", status=502)

    # Xodimning ish boshlanish vaqti (kechikish belgisi uchun)
    ws = "09:00:00"
    try:
        if roles is not None:
            rec = roles.get_record_by_card(card)
            if rec and rec.get("work_start"):
                ws = str(rec["work_start"])
    except Exception:
        pass
    try:
        import analyze_biocontrol_api as _an
        late_th = _an.late_threshold_for(_an.parse_work_start(ws))
        calc_min = _an.calc_day_minutes
    except Exception:
        late_th, calc_min = None, None

    # Tadbir VA xizmat safari kunlari — kechikish hisoblanmaydi,
    # to'liq ish kuni (8 soat) yoziladi
    tadbir_days = set()
    try:
        import analyze_biocontrol_api as _an2
        tadbir_days = set(_an2.load_fullday_days("exemptions.json", ym).get(card, set()))
    except Exception:
        pass

    out = []
    for day in sorted(set(list(days_data.keys()) + list(tadbir_days))):
        if day < start or day > end:
            continue
        evs = sorted(days_data.get(day, []), key=lambda x: x["dt"])
        first_in = last_out = None
        for ev in evs:
            t = str(ev.get("type", "")).lower()
            if "вход" in t and first_in is None:
                first_in = ev["dt"]
            if "выход" in t:
                last_out = ev["dt"]
        mins = calc_min(evs) if calc_min else 0
        try:                       # HR imtiyoz kuni: 09:00 da kirgan deb
            if mins > 0:
                mins += _an.entry_credit_minutes(day, evs, _an.parse_work_start(ws))
            late_th = _an.late_threshold_for(_an.parse_work_start(ws), day)
        except Exception:
            pass
        is_tadbir = day in tadbir_days
        if is_tadbir:
            # To'liq ish kuni (8 soat) + 18:00 dan keyin qolib ishlagani
            extra = 0
            try:
                extra = _an.calc_minutes_after(evs)
            except Exception:
                pass
            mins = max(mins, 8 * 60 + extra)
        is_late = bool(first_in and late_th and first_in.time() > late_th) and not is_tadbir
        out.append({
            "date": day,
            "in": first_in.strftime("%H:%M") if first_in else "",
            "out": last_out.strftime("%H:%M") if last_out else "",
            "hours": f"{mins // 60}:{mins % 60:02d}",
            "minutes": mins,
            "late": is_late,
            "tadbir": is_tadbir,
            "events": [{"t": e["dt"].strftime("%H:%M"),
                        "kind": ("in" if "вход" in str(e.get("type", "")).lower() else "out")}
                       for e in evs],
        })
    out.reverse()   # yangi kun tepada
    return json_ok({"card": card, "year_month": ym, "days": out, "total": len(out)})


async def exit_submit(request):
    """Xodim binoni tark etish sababini yozadi. {text}"""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    text = str(body.get("text", "")).strip()
    if len(text) < 3:
        return json_err("Sabab kamida 3 belgi bo'lsin")
    today = _today_iso()
    rid = f"{today}_{login_id}"
    tr = _load(EXIT_TRACK_FILE, {}).get(str(login_id), {})
    exit_time = tr.get("last_event", "") if isinstance(tr, dict) else ""
    full_name = acc.get("name", "") or _name_for_card(login_id)
    data = _load(EXIT_MOBILE_FILE, {"requests": {}})
    data.setdefault("requests", {})[rid] = {
        "id": rid, "card_number": login_id, "full_name": full_name,
        "date": today, "exit_time": exit_time, "text": text,
        "submitted_at": _now_str(), "status": "pending",
        "hr_note": "", "shown": False,
        "reviewed_by": None, "reviewed_at": None,
    }
    _save(EXIT_MOBILE_FILE, data)
    return json_ok({"ok": True, "id": rid})


async def all_employees(request):
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q (faqat HR/direktor/rahbariyat)", status=403)
    cache = _load(CACHE_FILE, {})
    reasons = _reasons_today(REASONS_FILE)
    exit_reasons = _reasons_today(EXIT_REASONS_FILE)
    excused = _excused_today()

    at_work = _enrich_photos(_filter_hidden(cache.get("at_work", [])))
    not_at_work = _enrich_photos(_filter_hidden(cache.get("not_at_work", [])))
    lunch = _enrich_photos(_filter_hidden(cache.get("lunch", [])))
    late = _enrich_photos(_filter_hidden(cache.get("late", [])))
    absent = _enrich_photos(_filter_hidden(cache.get("absent", [])))
    employees = _enrich_photos(_filter_hidden(cache.get("employees", [])))
    interns = _enrich_photos(_filter_hidden(cache.get("interns", [])))

    # Izohlar (dashboard bilan bir xil): kirish izohi + chiqish izohi + uzrli
    _attach_reason(absent, reasons)
    _attach_reason(late, reasons)
    _attach_reason(employees, reasons)
    _attach_reason(not_at_work, exit_reasons)
    _attach_excused(late, excused)
    _attach_excused(employees, excused)

    safari, tatil = _exemptions_split()

    return json_ok({
        "updated_at": cache.get("updated_at", ""),
        "summary": cache.get("summary", {}),
        "at_work": at_work,
        "not_at_work": not_at_work,
        "lunch": lunch,
        "late": late,
        "absent": absent,
        "employees": employees,
        "interns": interns,
        "safari": safari,
        "tatil": tatil,
    })


# ─────────────────────────── TUSHUNTIRISH XATI ───────────────────────────
#
# Oqim:
#   1) HR mobil orqali xodimdan tushuntirish so'raydi  -> explanation_requests.json
#   2) Xodim mobilda so'rovni ko'radi va matn yuboradi -> explanations.json +
#      explanations/YYYY-MM/*.txt (main17 / Telegram-bot bilan bir xil format)

def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_requests():
    return _load(EXP_REQUESTS_FILE, {"requests": {}})


def _req_id(card, date, kind):
    return f"{date}_{card}_{kind}"


def _name_for_card(card):
    row, _ = _find_employee_in_cache(card)
    if row:
        return row.get("full_name", "")
    if roles is not None:
        try:
            rec = roles.get_record_by_card(str(card))
            if rec:
                return rec.get("full_name", "") or rec.get("name", "")
        except Exception:
            pass
    return ""


SIGNATURES_DIR = BASE_DIR / "explanations" / "signatures"


def _save_signature(exp_id, data_url):
    """Barmoq bilan chizilgan imzo (dataURL PNG) ni saqlaydi. Fayl nomini qaytaradi."""
    import base64
    s = str(data_url or "")
    if not s:
        return None
    if "," in s and s.strip().lower().startswith("data:"):
        s = s.split(",", 1)[1]
    try:
        raw = base64.b64decode(s, validate=False)
    except Exception:
        return None
    if raw[:8] != b"\x89PNG\r\n\x1a\n" or len(raw) < 200 or len(raw) > 1024 * 1024:
        return None
    SIGNATURES_DIR.mkdir(parents=True, exist_ok=True)
    fname = re.sub(r"[^\w\-]+", "_", str(exp_id)) + ".png"
    (SIGNATURES_DIR / fname).write_bytes(raw)
    return fname


def _write_explanation(card, full_name, telegram_id, date, kind, first_entry, text,
                       signature_file=None):
    """main17.save_explanation_record bilan bir xil formatda saqlaydi."""
    exp_id = _req_id(card, date, kind)
    data = _load(EXPLANATIONS_FILE, {"records": {}})
    data.setdefault("records", {})[exp_id] = {
        "exp_id": exp_id, "type": kind,
        "card_number": card, "full_name": full_name,
        "telegram_id": telegram_id, "date": date,
        "first_entry": first_entry, "explanation": text,
        "submitted_at": _now_str(), "status": "pending",
        "reviewed_by": None, "reviewed_at": None,
        "source": "mobile",
        "signature_file": signature_file,
    }
    _save(EXPLANATIONS_FILE, data)
    try:
        ym = (date or _now_str())[:7]
        folder = BASE_DIR / "explanations" / ym
        folder.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^\w\-]+", "_", full_name, flags=re.UNICODE)[:60]
        kind_txt = {"late": "kechikish", "exit": "tark_etish"}.get(kind, kind)
        path = folder / f"{date}_{safe_name}_{kind_txt}.txt"
        if path.exists():
            path = folder / f"{date}_{safe_name}_{kind_txt}_{datetime.now().strftime('%H%M%S')}.txt"
        body = (
            "TUSHUNTIRISH XATI\n"
            + "=" * 44 + "\n"
            f"F.I.Sh.         : {full_name}\n"
            f"Card raqami     : {card}\n"
            f"Telegram ID     : {telegram_id}\n"
            f"Sana            : {date}\n"
            f"Turi            : {kind_txt}\n"
            f"Birinchi kirish : {first_entry}\n"
            f"Yuborilgan vaqt : {_now_str()}\n"
            f"Manba           : mobil ilova\n"
            + "=" * 44 + "\n\n"
            f"{text}\n"
        )
        path.write_text(body, encoding="utf-8")
    except Exception as e:
        print(f"[EXPLANATION_FILE] saqlanmadi: {e}")
    # Word faylni ham yangilaymiz (xodimning barcha xatlari bitta .docx da)
    try:
        _build_word_for_card(card)
    except Exception as e:
        print(f"[EXPLANATION_WORD] saqlanmadi: {e}")
    # Rasmiy PDF (tushuntirish xati) — imzo, guruh/lavozim bilan
    try:
        _build_pdf_for(card, full_name, date, kind, first_entry, signature_file)
    except Exception as e:
        print(f"[EXPLANATION_PDF] saqlanmadi: {e}")


def _build_pdf_for(card, full_name, date, kind, first_entry, signature_file):
    """Rasmiy tushuntirish xati PDF yasaydi (explanation_pdf moduli orqali)."""
    try:
        import explanation_pdf as epdf
    except Exception as e:
        print(f"[EXPLANATION_PDF] modul yuklanmadi: {e}")
        return
    # tushuntirish matni (endigina saqlangan yozuvdan)
    rec = _load(EXPLANATIONS_FILE, {"records": {}}).get("records", {}).get(_req_id(card, date, kind), {})
    reason = rec.get("explanation", "") or ""
    # ish boshlanish vaqti (kechikish daqiqasini hisoblash uchun)
    row, _ = _find_employee_in_cache(card)
    work_start = (row or {}).get("work_start") or ""
    # 'exit' uchun chiqish vaqti, 'late' uchun kirish vaqti
    if kind == "exit":
        time_str = (row or {}).get("last_event_time") or (row or {}).get("last_exit") or "-"
    else:
        time_str = first_entry or "-"
    sig_path = (SIGNATURES_DIR / str(signature_file)) if signature_file else None
    out = epdf.pdf_path_for(card, full_name, date, kind)
    res = epdf.build_pdf(
        out_path=out, fio=full_name, card=card, kind=kind, date_iso=date,
        time_str=time_str, reason=reason,
        signature_path=str(sig_path) if sig_path else None,
        work_start=work_start,
    )
    if res:
        print(f"[EXPLANATION_PDF] saqlandi: {res}")
    return exp_id


# ─── WORD (.docx) — har xodimning barcha tushuntirish xatlari bitta faylda ───
# Kutubxona talab qilmaydi: docx = zip + XML (stdlib bilan yoziladi).

WORD_DIR = BASE_DIR / "explanations" / "word"

_DOCX_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>"""

_DOCX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>"""


def _dx(text):
    """XML uchun matnni tozalash."""
    return (str(text or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _dp(text, bold=False, size=None):
    """Bitta paragraf (w:p). size — yarim-punktlarda (24 = 12pt)."""
    rpr = ""
    if bold or size:
        rpr = ("<w:rPr>" + ("<w:b/>" if bold else "")
               + (f'<w:sz w:val="{size}"/>' if size else "") + "</w:rPr>")
    return (f"<w:p><w:r>{rpr}"
            f'<w:t xml:space="preserve">{_dx(text)}</w:t></w:r></w:p>')


def _word_safe_name(full_name):
    return re.sub(r"[^\w\-]+", "_", str(full_name or ""), flags=re.UNICODE)[:60] or "xodim"


def _word_path_for(card, full_name=None):
    WORD_DIR.mkdir(parents=True, exist_ok=True)
    # avval card bo'yicha mavjud faylni qidiramiz
    for p in WORD_DIR.glob(f"{card}_*.docx"):
        return p
    name = full_name or _name_for_card(card) or "xodim"
    return WORD_DIR / f"{card}_{_word_safe_name(name)}.docx"


def _png_size(raw):
    """PNG o'lchamini (px) IHDR dan o'qiydi."""
    import struct
    try:
        w, h = struct.unpack(">II", raw[16:24])
        return int(w), int(h)
    except Exception:
        return 300, 110


def _docx_image_p(rid_n, w_px, h_px):
    """Imzo rasmi joylashgan paragraf (inline drawing). EMU: 1px = 9525."""
    max_w = 280  # ko'rinish eni (px)
    k = min(1.0, max_w / max(1, w_px))
    cx, cy = int(w_px * k * 9525), int(h_px * k * 9525)
    return (
        f'<w:p><w:r><w:drawing>'
        f'<wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{rid_n}" name="imzo{rid_n}"/>'
        f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:nvPicPr><pic:cNvPr id="{rid_n}" name="imzo{rid_n}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="rIdImg{rid_n}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>'
        f'<a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
    )


def _build_word_for_card(card):
    """Xodimning BARCHA tushuntirishlarini explanations.json dan yig'ib,
    bitta .docx fayl qilib (qayta) yozadi. Imzolar rasm sifatida kiradi."""
    import zipfile
    recs = _load(EXPLANATIONS_FILE, {"records": {}}).get("records", {})
    mine = [r for r in recs.values() if str(r.get("card_number")) == str(card)]
    if not mine:
        return None
    mine.sort(key=lambda r: (r.get("date") or "", r.get("submitted_at") or ""))
    full_name = mine[-1].get("full_name") or _name_for_card(card)
    kind_lbl = {"late": "Kechikish", "absent": "Kelmaslik", "exit": "Tark etish"}

    body = [
        _dp("TUSHUNTIRISH XATLARI", bold=True, size=32),
        _dp(full_name, bold=True, size=28),
        _dp(f"Card: {card}", size=20),
        _dp(""),
    ]
    images = []  # (n, png_bytes)
    for r in mine:
        body.append(_dp("─" * 40))
        body.append(_dp(f"{r.get('date','')} · {kind_lbl.get(r.get('type',''), r.get('type',''))}", bold=True, size=24))
        if r.get("first_entry") and r.get("first_entry") != "-":
            body.append(_dp(f"Birinchi kirish: {r.get('first_entry')}", size=20))
        body.append(_dp(f"Yuborilgan: {r.get('submitted_at','')}", size=20))
        body.append(_dp(""))
        for line in str(r.get("explanation", "")).splitlines() or [""]:
            body.append(_dp(line))
        # imzo (bo'lsa — rasm, bo'lmasa — chiziq)
        sig = r.get("signature_file")
        sig_path = SIGNATURES_DIR / str(sig) if sig else None
        if sig_path and sig_path.exists():
            raw = sig_path.read_bytes()
            n = len(images) + 1
            images.append((n, raw))
            w_px, h_px = _png_size(raw)
            body.append(_dp("Imzo:", size=20))
            body.append(_docx_image_p(n, w_px, h_px))
        else:
            body.append(_dp(""))
            body.append(_dp("Imzo: ______________________", size=20))
        body.append(_dp(""))

    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           "<w:body>" + "".join(body) + "<w:sectPr/></w:body></w:document>")

    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for n, _raw in images:
        rels.append(f'<Relationship Id="rIdImg{n}" '
                    f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                    f'Target="media/imzo{n}.png"/>')
    rels.append("</Relationships>")

    path = _word_path_for(card, full_name)
    tmp = path.with_suffix(".docx.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _DOCX_CT)
        z.writestr("_rels/.rels", _DOCX_RELS)
        z.writestr("word/_rels/document.xml.rels", "".join(rels))
        z.writestr("word/document.xml", doc)
        for n, raw in images:
            z.writestr(f"word/media/imzo{n}.png", raw)
    tmp.replace(path)
    return path


async def explain_self(request):
    """Xodim O'ZI oldindan sabab yozadi (HR so'rovisiz).
    {kind: late|absent, date: YYYY-MM-DD (bugun yoki kelajak), text}
    HR ro'yxatida o'sha sanada 'javob berilgan' sifatida ko'rinadi."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    kind = str(body.get("kind", "late")).strip().lower()
    if kind not in ("late", "absent"):
        return json_err("kind late yoki absent bo'lsin")
    text = str(body.get("text", "")).strip()
    if len(text) < 10:
        return json_err("Sabab kamida 10 belgi bo'lsin")
    today = datetime.now().strftime("%Y-%m-%d")
    date = str(body.get("date", "")).strip() or today
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        return json_err("Sana formati: YYYY-MM-DD")
    if date < today:
        return json_err("O'tgan sanaga yozib bo'lmaydi")
    rid = _req_id(login_id, date, kind)
    data = _load_requests()
    existing = data["requests"].get(rid)
    if existing and existing.get("status") == "answered":
        return json_err("Bu sana uchun allaqachon sabab yozilgan")
    full_name = acc.get("name", "") or _name_for_card(login_id)
    row, _ = _find_employee_in_cache(login_id)
    sig_file = _save_signature(rid, body.get("signature"))
    _write_explanation(login_id, full_name, (row or {}).get("telegram_id"),
                       date, kind, (row or {}).get("first_entry", "-") or "-", text,
                       signature_file=sig_file)
    data["requests"][rid] = {
        "req_id": rid, "card_number": login_id,
        "full_name": full_name,
        "kind": kind, "date": date,
        "note": "",
        "requested_by": full_name,
        "requested_at": _now_str(),
        "status": "answered",
        "answered_at": _now_str(),
        "self": True,  # xodim o'zi yozgan
    }
    _save(EXP_REQUESTS_FILE, data)
    return json_ok({"ok": True, "req_id": rid})


async def explain_word(request):
    """HR: xodimning barcha tushuntirishlari .docx fayli (har safar yangilab beriladi)."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q", status=403)
    card = str(request.match_info.get("card", "")).strip()
    if not card or "/" in card or ".." in card:
        return json_err("card noto'g'ri")
    try:
        path = _build_word_for_card(card)
    except Exception as e:
        return json_err(f"Word yaratilmadi: {e}", status=500)
    if not path:
        return json_err("Bu xodimda tushuntirishlar yo'q", status=404)
    resp = web.FileResponse(path)
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    resp.headers["Content-Disposition"] = f'attachment; filename="{path.name}"'
    return _cors(resp)


YOQLAMA_FILE = BASE_DIR / "yoqlama.json"


def _my_yoqlama(card):
    """Xodimga tegishli oxirgi yo'qlamalar: qatnashdimi va javob berganmi."""
    d = _load(YOQLAMA_FILE, {"items": []})
    items = d.get("items", []) if isinstance(d, dict) else []
    card = str(card)
    out = []
    for it in items[:12]:
        marks = it.get("marks", {}) or {}
        if card not in marks:
            continue
        att = bool(marks.get(card))
        reason = (it.get("reasons", {}) or {}).get(card)
        out.append({
            "id": it.get("id"), "title": it.get("title", ""),
            "date": it.get("date", ""), "time": it.get("time", ""),
            "attended": att,
            "reason": (reason or {}).get("text") if isinstance(reason, dict) else None,
            "answered": bool(reason),
        })
    return out


async def yoqlama_reason(request):
    """Xodim qatnashmagan tadbir uchun sabab yozadi. {id, text}"""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    yid = str(body.get("id", "")).strip()
    text = str(body.get("text", "")).strip()
    if len(text) < 3:
        return json_err("Sababni yozing (kamida 3 belgi)")
    d = _load(YOQLAMA_FILE, {"items": []})
    items = d.get("items", []) if isinstance(d, dict) else []
    it = next((x for x in items if str(x.get("id")) == yid), None)
    if not it:
        return json_err("Yo'qlama topilmadi", status=404)
    card = str(login_id)
    if card not in (it.get("marks", {}) or {}):
        return json_err("Bu yo'qlamada yo'qsiz", status=403)
    if (it.get("marks", {}) or {}).get(card):
        return json_err("Siz qatnashgansiz — sabab kerak emas")
    it.setdefault("reasons", {})[card] = {
        "text": text,
        "at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",
    }
    _save(YOQLAMA_FILE, d)
    return json_ok({"ok": True})


async def signature_img(request):
    """Tushuntirish xatidagi qo'lyozma imzo rasmi — HR/rahbar yoki egasi.

    HR modalida imzoni darhol ko'rish uchun (PDF ochmasdan).
    Token: Bearer, cookie yoki ?token=...
    """
    login_id, acc = _require_login(request)
    if not login_id:
        tok = request.query.get("token", "")
        if tok:
            acc = accounts.check_token(tok)
            login_id = (acc or {}).get("login") if acc else None
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    exp_id = str(request.match_info.get("exp_id", "")).strip()
    if not exp_id or "/" in exp_id or ".." in exp_id:
        return json_err("exp_id noto'g'ri")
    rec = _load(EXPLANATIONS_FILE, {"records": {}}).get("records", {}).get(exp_id)
    if not rec:
        return json_err("Topilmadi", status=404)
    if not _can_view_all(login_id, acc) and str(rec.get("card_number")) != str(login_id):
        return json_err("Ruxsat yo'q", status=403)
    sig = str(rec.get("signature_file", "") or "")
    if not sig or "/" in sig or ".." in sig:
        return json_err("Imzo yo'q", status=404)
    p = SIGNATURES_DIR / sig
    if not p.exists():
        return json_err("Imzo fayli topilmadi", status=404)
    return _cors(web.FileResponse(p))


async def explain_pdf(request):
    """Imzolangan tushuntirish xati PDF — HR/rahbar yoki EGASI (o'z xati)."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    exp_id = str(request.match_info.get("exp_id", "")).strip()
    if not exp_id or "/" in exp_id or ".." in exp_id:
        return json_err("exp_id noto'g'ri")
    rec = _load(EXPLANATIONS_FILE, {"records": {}}).get("records", {}).get(exp_id)
    if not rec:
        return json_err("Tushuntirish topilmadi", status=404)
    # Ruxsat: HR/rahbar YOKI o'z xati
    if not _can_view_all(login_id, acc) and str(rec.get("card_number")) != str(login_id):
        return json_err("Ruxsat yo'q", status=403)
    try:
        import explanation_pdf as epdf
    except Exception as e:
        return json_err(f"PDF moduli yo'q (reportlab o'rnating): {e}", status=500)
    card = str(rec.get("card_number", ""))
    date = rec.get("date", "")
    kind = rec.get("type", "")
    full_name = rec.get("full_name", "") or _name_for_card(card)
    reason = rec.get("explanation", "") or ""
    sig = rec.get("signature_file")
    sig_path = (SIGNATURES_DIR / str(sig)) if sig else None
    row, _ = _find_employee_in_cache(card)
    work_start = (row or {}).get("work_start") or ""
    if kind == "exit":
        time_str = (row or {}).get("last_event_time") or rec.get("first_entry") or "-"
    else:
        time_str = rec.get("first_entry") or "-"
    try:
        out = epdf.pdf_path_for(card, full_name, date, kind)
        res = epdf.build_pdf(
            out_path=out, fio=full_name, card=card, kind=kind, date_iso=date,
            time_str=time_str, reason=reason,
            signature_path=str(sig_path) if (sig_path and sig_path.exists()) else None,
            work_start=work_start,
        )
    except Exception as e:
        return json_err(f"PDF yaratilmadi: {e}", status=500)
    if not res:
        return json_err("PDF yaratilmadi — reportlab o'rnatilganini tekshiring", status=500)
    resp = web.FileResponse(res)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'inline; filename="{Path(res).name}"'
    return _cors(resp)


async def explain_delete(request):
    """HR: tushuntirishни butunlay o'chiradi (sinov/xato). {id} = exp_id."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q", status=403)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    exp_id = str(body.get("id", "")).strip()
    if not exp_id or "/" in exp_id or ".." in exp_id:
        return json_err("id noto'g'ri")
    data = _load(EXPLANATIONS_FILE, {"records": {}})
    rec = data.get("records", {}).get(exp_id)
    if not rec:
        return json_err("Topilmadi", status=404)
    full_name = rec.get("full_name", "")
    date = str(rec.get("date", ""))
    kind = rec.get("type", "")
    sig = rec.get("signature_file")

    # 1) explanations.json
    del data["records"][exp_id]
    _save(EXPLANATIONS_FILE, data)
    # 2) explanation_requests.json (HR ro'yxati shundan)
    reqs = _load(EXP_REQUESTS_FILE, {"requests": {}})
    if exp_id in reqs.get("requests", {}):
        del reqs["requests"][exp_id]
        _save(EXP_REQUESTS_FILE, reqs)
    # 3) fayllar
    try:
        if sig:
            sp = SIGNATURES_DIR / str(sig)
            if sp.exists():
                sp.unlink()
        safe = re.sub(r"[^\w\-]+", "_", str(full_name), flags=re.UNICODE)[:60]
        ym = date[:7]
        for folder in (BASE_DIR / "explanations" / ym, BASE_DIR / "explanations" / "pdf"):
            if folder.exists():
                for f in folder.glob(f"{date}_{safe}_*"):
                    try:
                        f.unlink()
                    except Exception:
                        pass
        # PDF (barqaror nom)
        try:
            import explanation_pdf as epdf
            pp = epdf.pdf_path_for(rec.get("card_number"), full_name, date, kind)
            if Path(pp).exists():
                Path(pp).unlink()
        except Exception:
            pass
    except Exception as e:
        print(f"[EXPLAIN_DELETE] fayl o'chirishда xato: {e}")
    return json_ok({"ok": True})


async def explain_request(request):
    """HR xodimdan tushuntirish so'raydi. {card, kind: late|absent, date?, note?}"""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q (faqat HR/direktor/rahbariyat)", status=403)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    kind = str(body.get("kind", "late")).strip().lower()
    if not card:
        return json_err("card kerak")
    if kind not in ("late", "absent"):
        return json_err("kind late yoki absent bo'lsin")
    # super_admin'dan tushuntirish so'ralmaydi — tugma bosilsa ham hech narsa sodir bo'lmaydi
    target_acc = accounts.get_account(card)
    if target_acc and (target_acc.get("role") or "").lower() == "super_admin":
        return json_ok({"ok": True})
    date = str(body.get("date", "")).strip() or datetime.now().strftime("%Y-%m-%d")
    rid = _req_id(card, date, kind)
    data = _load_requests()
    existing = data["requests"].get(rid)
    if existing and existing.get("status") == "answered":
        return json_err("Bu so'rovga allaqachon javob berilgan")
    data["requests"][rid] = {
        "req_id": rid, "card_number": card,
        "full_name": _name_for_card(card),
        "kind": kind, "date": date,
        "note": str(body.get("note", "")).strip(),
        "requested_by": acc.get("name", login_id),
        "requested_at": _now_str(),
        "status": "pending",
        "answered_at": None,
    }
    _save(EXP_REQUESTS_FILE, data)
    return json_ok({"ok": True, "req_id": rid})


async def explain_cancel(request):
    """HR yuborilgan tushuntirish so'rovini qaytarib oladi. {req_id}
    Faqat hali javob berilmagan (pending) so'rovni bekor qilish mumkin."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q", status=403)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    rid = str(body.get("req_id", "")).strip()
    data = _load_requests()
    req = data["requests"].get(rid)
    if not req:
        return json_err("So'rov topilmadi", status=404)
    if req.get("status") == "answered":
        return json_err("Javob berilgan so'rovni qaytarib bo'lmaydi")
    del data["requests"][rid]
    _save(EXP_REQUESTS_FILE, data)
    return json_ok({"ok": True})


async def explain_requests_all(request):
    """HR: barcha so'rovlar ro'yxati (javob matni bilan)."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q", status=403)
    data = _load_requests()
    exps = _load(EXPLANATIONS_FILE, {"records": {}}).get("records", {})
    out = []
    for r in data["requests"].values():
        r = dict(r)
        if r.get("status") == "answered":
            rec = exps.get(r.get("req_id")) or {}
            r["explanation"] = rec.get("explanation", "")
            r["submitted_at"] = rec.get("submitted_at", r.get("answered_at"))
        out.append(r)
    return json_ok({"requests": out})


async def explain_my(request):
    """Xodim: o'ziga tegishli so'rovlar."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    data = _load_requests()
    mine = [r for r in data["requests"].values()
            if str(r.get("card_number")) == str(login_id)]
    mine.sort(key=lambda r: r.get("requested_at", ""), reverse=True)
    return json_ok({"requests": mine})


async def explain_submit(request):
    """Xodim tushuntirish matnini yuboradi. {req_id, text}"""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    rid = str(body.get("req_id", "")).strip()
    text = str(body.get("text", "")).strip()
    if len(text) < 10:
        return json_err("Tushuntirish kamida 10 belgi bo'lsin")
    data = _load_requests()
    req = data["requests"].get(rid)
    if not req:
        return json_err("So'rov topilmadi", status=404)
    if str(req.get("card_number")) != str(login_id):
        return json_err("Bu so'rov sizga tegishli emas", status=403)
    if req.get("status") == "answered":
        return json_err("Allaqachon javob berilgan")
    row, _ = _find_employee_in_cache(login_id)
    first_entry = (row or {}).get("first_entry", "-") or "-"
    telegram_id = (row or {}).get("telegram_id")
    full_name = req.get("full_name") or acc.get("name", "") or _name_for_card(login_id)
    sig_file = _save_signature(rid, body.get("signature"))
    _write_explanation(login_id, full_name, telegram_id,
                       req.get("date"), req.get("kind"), first_entry, text,
                       signature_file=sig_file)
    req["status"] = "answered"
    req["answered_at"] = _now_str()
    _save(EXP_REQUESTS_FILE, data)
    return json_ok({"ok": True})


# ─────────────────────────── RASM YUKLASH (HR) ───────────────────────────

async def photo_upload(request):
    """HR xodim rasmini yuklaydi. JSON: {card, image} (dataURL yoki sof base64).
    Rasm photos/ ga saqlanadi, photo_overrides.json da qayd etiladi —
    mobil ilova ham, TV dashboard ham shu rasmni ko'rsatadi."""
    import base64
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q (faqat HR/direktor/rahbariyat)", status=403)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    img = str(body.get("image", ""))
    if not card or "/" in card or ".." in card:
        return json_err("card noto'g'ri")
    if not img:
        return json_err("image kerak")
    # dataURL bo'lsa: "data:image/jpeg;base64,...."
    if "," in img and img.strip().lower().startswith("data:"):
        img = img.split(",", 1)[1]
    try:
        raw = base64.b64decode(img, validate=False)
    except Exception:
        return json_err("base64 xato")
    if len(raw) < 100:
        return json_err("Rasm juda kichik")
    if len(raw) > 6 * 1024 * 1024:
        return json_err("Rasm juda katta (maks 6MB)")
    # format: magic baytlar bo'yicha
    if raw[:3] == b"\xff\xd8\xff":
        ext = "jpg"
    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
        ext = "png"
    else:
        return json_err("Faqat JPG yoki PNG")
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{card}_hr.{ext}"
    # eski yuklangan (boshqa kengaytmali) faylni tozalaymiz
    for old_ext in ("jpg", "png"):
        old = PHOTOS_DIR / f"{card}_hr.{old_ext}"
        if old_ext != ext and old.exists():
            try:
                old.unlink()
            except Exception:
                pass
    (PHOTOS_DIR / fname).write_bytes(raw)
    ov = _load(PHOTO_OVERRIDES_FILE, {})
    if not isinstance(ov, dict):
        ov = {}
    ov[card] = fname
    _save(PHOTO_OVERRIDES_FILE, ov)
    return json_ok({"ok": True, "photo_file": fname})


# ─────────────────────────── OLIMLAR (PhD/DSc karuseli) ───────────────────────────

async def olimlar_list(request):
    """Belgilangan olimlar ro'yxati (karusel uchun). Login kifoya."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    data = _load(OLIMLAR_FILE, {"olimlar": {}})
    out = []
    for card, rec in (data.get("olimlar") or {}).items():
        out.append({
            "card_number": str(card),
            "full_name": rec.get("full_name") or _name_for_card(card),
            "degree": rec.get("degree", ""),
            "photo_file": _photo_for(card),
        })
    out.sort(key=lambda r: r.get("full_name", ""))
    return json_ok({"olimlar": out})


async def olimlar_set(request):
    """HR xodimni olim sifatida belgilaydi. {card, degree: phd|dsc|""}."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q (faqat HR/direktor/rahbariyat)", status=403)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    card = str(body.get("card", "")).strip()
    degree = str(body.get("degree", "")).strip().lower()
    if not card:
        return json_err("card kerak")
    if degree not in ("phd", "dsc", ""):
        return json_err("degree phd, dsc yoki bo'sh bo'lsin")
    data = _load(OLIMLAR_FILE, {"olimlar": {}})
    data.setdefault("olimlar", {})
    if degree:
        data["olimlar"][card] = {
            "full_name": _name_for_card(card),
            "degree": degree,
            "set_by": acc.get("name", login_id),
            "set_at": _now_str(),
        }
    else:
        data["olimlar"].pop(card, None)
    _save(OLIMLAR_FILE, data)
    return json_ok({"ok": True, "card": card, "degree": degree})


async def photo_handler(request):
    # Autentifikatsiya: cookie (img), Authorization header yoki ?token=
    tok = (request.cookies.get("sess") or _bearer(request)
           or request.query.get("token", ""))
    if not accounts.check_token(tok):
        return web.Response(status=401)
    fname = request.match_info.get("fname", "")
    if not fname or "/" in fname or "\\" in fname or ".." in fname:
        return web.Response(status=404)
    path = PHOTOS_DIR / fname
    if not path.exists() or not path.is_file():
        return web.Response(status=404)
    resp = web.FileResponse(path)
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


# ─────────────────────────── ARIZA (xodim -> HR/rahbar) ───────────────────────────

ARIZA_FILE = BASE_DIR / "arizalar.json"
ARIZA_TYPES = {"tatil", "ruxsat", "moddiy", "erkin"}


async def ariza_create(request):
    """Xodim ariza yuboradi. {type, text, date_from?, date_to?}"""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    atype = str(body.get("type", "")).strip().lower()
    if atype not in ARIZA_TYPES:
        return json_err("Ariza turi noto'g'ri")
    text = str(body.get("text", "")).strip()
    if len(text) < 5:
        return json_err("Matn kamida 5 belgi bo'lsin")
    d_from = str(body.get("date_from", "")).strip()
    d_to = str(body.get("date_to", "")).strip() or d_from
    if atype in ("tatil", "ruxsat"):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d_from):
            return json_err("Sana (dan) kerak: YYYY-MM-DD")
        if d_to and d_to < d_from:
            return json_err("Tugash sanasi boshlanishdan oldin bo'lmasin")
    else:
        d_from = d_to = ""
    import uuid
    aid = uuid.uuid4().hex[:10]
    full_name = acc.get("name", "") or _name_for_card(login_id)
    sig_file = _save_signature("ariza_" + aid, body.get("signature"))
    data = _load(ARIZA_FILE, {"requests": {}})
    data.setdefault("requests", {})[aid] = {
        "id": aid, "card_number": login_id, "full_name": full_name,
        "type": atype, "text": text, "date_from": d_from, "date_to": d_to,
        "created_at": _now_str(), "status": "pending",
        "reviewed_by": None, "reviewed_at": None, "response": "",
        "signature_file": sig_file,
    }
    _save(ARIZA_FILE, data)
    # Rasmiy PDF (imzo bilan) — HR yuklab oladi
    try:
        _build_ariza_pdf(aid)
    except Exception as e:
        print(f"[ARIZA_PDF] saqlanmadi: {e}")
    return json_ok({"ok": True, "id": aid})


def _build_ariza_pdf(aid):
    rec = _load(ARIZA_FILE, {"requests": {}}).get("requests", {}).get(aid)
    if not rec:
        return None
    try:
        import explanation_pdf as epdf
    except Exception as e:
        print(f"[ARIZA_PDF] modul yo'q: {e}")
        return None
    sig = rec.get("signature_file")
    sig_path = (SIGNATURES_DIR / str(sig)) if sig else None
    out = epdf.ariza_pdf_path_for(aid, rec.get("full_name", ""))
    return epdf.build_ariza_pdf(
        out_path=out, fio=rec.get("full_name", ""), card=str(rec.get("card_number", "")),
        atype=rec.get("type", ""), created_date=rec.get("created_at", "")[:10],
        date_from=rec.get("date_from", ""), date_to=rec.get("date_to", ""),
        text=rec.get("text", ""),
        signature_path=str(sig_path) if (sig_path and sig_path.exists()) else None,
    )


async def ariza_pdf(request):
    """Arizaning imzolangan rasmiy PDF'i — HR/rahbar yoki EGASI."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    aid = str(request.match_info.get("aid", "")).strip()
    if not aid or "/" in aid or ".." in aid:
        return json_err("id noto'g'ri")
    rec = _load(ARIZA_FILE, {"requests": {}}).get("requests", {}).get(aid)
    if not rec:
        return json_err("Ariza topilmadi", status=404)
    if not _can_view_all(login_id, acc) and str(rec.get("card_number")) != str(login_id):
        return json_err("Ruxsat yo'q", status=403)
    try:
        res = _build_ariza_pdf(aid)
    except Exception as e:
        return json_err(f"PDF yaratilmadi: {e}", status=500)
    if not res:
        return json_err("PDF yaratilmadi — reportlab kerak", status=500)
    resp = web.FileResponse(res)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'inline; filename="{Path(res).name}"'
    return _cors(resp)


async def ariza_my(request):
    """Xodimning o'z arizalari."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    data = _load(ARIZA_FILE, {"requests": {}})
    mine = [r for r in data.get("requests", {}).values()
            if str(r.get("card_number")) == str(login_id)]
    mine.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return json_ok({"requests": mine})


async def ariza_cancel(request):
    """Xodim o'z (hali ko'rilmagan) arizasini qaytarib oladi. {id}"""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    aid = str(body.get("id", "")).strip()
    data = _load(ARIZA_FILE, {"requests": {}})
    rec = data.get("requests", {}).get(aid)
    if not rec:
        return json_err("Topilmadi", status=404)
    if str(rec.get("card_number")) != str(login_id):
        return json_err("Bu ariza sizga tegishli emas", status=403)
    if rec.get("status") != "pending":
        return json_err("Allaqachon ko'rilgan — qaytarib bo'lmaydi")
    del data["requests"][aid]
    _save(ARIZA_FILE, data)
    return json_ok({"ok": True})


async def ariza_all(request):
    """HR/rahbar: barcha arizalar (kutilayotganlar birinchi)."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q (faqat HR/rahbariyat)", status=403)
    data = _load(ARIZA_FILE, {"requests": {}})
    items = list(data.get("requests", {}).values())
    items.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    items.sort(key=lambda r: r.get("status") != "pending")  # pending oldinda
    return json_ok({
        "requests": items,
        "pending": sum(1 for r in items if r.get("status") == "pending"),
    })


async def ariza_review(request):
    """HR/rahbar: arizani qabul/rad qiladi. {id, status: approved|rejected, response?}"""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q (faqat HR/rahbariyat)", status=403)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    aid = str(body.get("id", "")).strip()
    status = str(body.get("status", "")).strip()
    if status not in ("approved", "rejected", "pending"):
        return json_err("status: approved / rejected")
    data = _load(ARIZA_FILE, {"requests": {}})
    rec = data.get("requests", {}).get(aid)
    if not rec:
        return json_err("Topilmadi", status=404)
    rec["status"] = status
    rec["response"] = str(body.get("response", "")).strip()
    if status == "pending":
        rec["reviewed_by"] = None
        rec["reviewed_at"] = None
    else:
        rec["reviewed_by"] = f"mobile:{login_id}"
        rec["reviewed_at"] = _now_str()
    _save(ARIZA_FILE, data)
    return json_ok({"ok": True})


async def ariza_delete(request):
    """HR/rahbar: arizani butunlay o'chiradi (xato/sinov arizalarni tozalash). {id}"""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    if not _can_view_all(login_id, acc):
        return json_err("Ruxsat yo'q (faqat HR/rahbariyat)", status=403)
    try:
        body = await request.json()
    except Exception:
        return json_err("JSON kutilgan")
    aid = str(body.get("id", "")).strip()
    data = _load(ARIZA_FILE, {"requests": {}})
    if aid in data.get("requests", {}):
        del data["requests"][aid]
        _save(ARIZA_FILE, data)
        return json_ok({"ok": True})
    return json_err("Topilmadi", status=404)


# ═══════════════════ SO'ROVNOMA (alohida link: /ovoz) ═══════════════════
# Bu endpointlar TOKENSIZ ishlaydi — xodim ilovaga kirmasdan ovoz beradi.
# Shaxs JSHSHIR orqali aniqlanadi.

# Faqat MUVAFFAQIYATSIZ urinishlar sanaladi. Shunday qilinmasa, butun
# tashkilot bitta routerdan kirganda haqiqiy xodimlar ham to'silib qolardi.
_OVOZ_FAIL = {}         # IP -> [xato urinishlar vaqti]
_OVOZ_MAX = 15          # 10 daqiqada shuncha XATO urinish
_OVOZ_WIN = 600


def _ovoz_ip(request) -> str:
    ip = request.headers.get("X-Forwarded-For", "") or (request.remote or "?")
    return ip.split(",")[0].strip()


def _ovoz_blocked(request) -> bool:
    """Raqam terib topishga urinayotgan IP to'silganmi?"""
    now = time.time()
    arr = [t for t in _OVOZ_FAIL.get(_ovoz_ip(request), []) if now - t < _OVOZ_WIN]
    return len(arr) >= _OVOZ_MAX


def _ovoz_fail(request) -> None:
    """Xato urinishni qayd etamiz."""
    ip = _ovoz_ip(request)
    now = time.time()
    arr = [t for t in _OVOZ_FAIL.get(ip, []) if now - t < _OVOZ_WIN]
    arr.append(now)
    _OVOZ_FAIL[ip] = arr


async def ovoz_page(request):
    """Ovoz berish sahifasi — alohida link."""
    p = BASE_DIR / "mobile" / "ovoz.html"
    if not p.exists():
        return web.Response(text="ovoz.html topilmadi", status=404)
    return web.FileResponse(p)


async def ovoz_state(request):
    """Ochiq va yakunlangan so'rovnomalar."""
    if surveys is None:
        return _cors(web.json_response({"open": [], "closed": []}))
    only = str(request.query.get("s", "")).strip()
    op = [it for it in surveys.open_surveys() if not only or it["id"] == only]
    cl = [it for it in surveys.closed_surveys() if not only or it["id"] == only]
    return _cors(web.json_response({
        "only": only,
        "open": [{"id": it["id"], "title": it["title"],
                  "question": it.get("question", "")} for it in op],
        "closed": [{"id": it["id"], "title": it["title"],
                    "result": surveys.results(it["id"], with_voters=False)}
                   for it in cl],
    }))


async def ovoz_identify(request):
    """JSHSHIR bo'yicha xodimni aniqlash — barcha ochiq so'rovnomalar bilan."""
    if surveys is None:
        return _cors(web.json_response({"error": "Modul yo'q"}, status=500))
    if _ovoz_blocked(request):
        return _cors(web.json_response(
            {"error": "Juda ko'p xato urinish. 10 daqiqadan keyin qayta urining."},
            status=429))
    try:
        body = await request.json()
    except Exception:
        body = {}
    card = re.sub(r"[^0-9]", "", str(body.get("card", "")))
    if len(card) < 9:
        return _cors(web.json_response({"error": "Raqam to'liq emas"}, status=400))
    emp = surveys.employee(card)
    if not emp:
        _ovoz_fail(request)
        return _cors(web.json_response(
            {"error": "Bu raqam bo'yicha xodim topilmadi. Raqamni tekshiring."},
            status=404))
    return _cors(web.json_response({
        "full_name": emp["full_name"],
        "department": emp.get("department", ""),
        "surveys": surveys.voter_view(card, str(body.get("survey", "")).strip()),
    }))


async def ovoz_answer(request):
    """Anketa javoblarini qabul qilish."""
    if surveys is None:
        return _cors(web.json_response({"error": "Modul yo'q"}, status=500))
    try:
        body = await request.json()
    except Exception:
        body = {}
    good, msg = surveys.submit_answers(
        str(body.get("survey", "")).strip(),
        re.sub(r"[^0-9]", "", str(body.get("card", ""))),
        body.get("answers") or {},
    )
    if not good:
        return _cors(web.json_response({"error": msg}, status=400))
    return _cors(web.json_response({"ok": True, "message": msg}))


async def ovoz_vote(request):
    """Ovoz berish."""
    if surveys is None:
        return _cors(web.json_response({"error": "Modul yo'q"}, status=500))
    try:
        body = await request.json()
    except Exception:
        body = {}
    sid = str(body.get("survey", "")).strip()
    card = re.sub(r"\D", "", str(body.get("card", "")))
    choice = re.sub(r"\D", "", str(body.get("choice", "")))
    ok, msg = surveys.vote(sid, card, choice)
    if not ok:
        return _cors(web.json_response({"error": msg}, status=400))
    return _cors(web.json_response({"ok": True, "message": msg}))


async def health(request):
    return json_ok({"ok": True, "service": "mobile_api", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


_LAST_NVR_REFRESH = {"at": 0.0, "result": None}
NVR_REFRESH_COOLDOWN = 20  # soniya — ko'p odam birdaniga bossa, qurilmaga zarba bermasin


async def refresh_nvr(request):
    """Ilovadagi ⟳ tugmasi: login qilgan HAR QANDAY xodim bosishi mumkin.
    Qurilmaga ortiqcha yuk tushmasin uchun qisqa cooldown bilan."""
    login_id, acc = _require_login(request)
    if not login_id:
        return json_err("Avtorizatsiya kerak", status=401)
    import time as _time
    now = _time.time()
    if _LAST_NVR_REFRESH["result"] and now - _LAST_NVR_REFRESH["at"] < NVR_REFRESH_COOLDOWN:
        return json_ok(_LAST_NVR_REFRESH["result"])
    try:
        import nvr_live
        result = nvr_live.refresh()
    except Exception as e:
        return json_err(f"{type(e).__name__}: {e}", status=500)
    _LAST_NVR_REFRESH.update(at=now, result=result)
    if not result.get("ok"):
        return json_err(result.get("error", "noma'lum xato"), status=502)
    return json_ok(result)


async def options_handler(request):
    return _cors(web.Response())


@web.middleware
async def _auth_mw(request, handler):
    """1) Parol o'zgartirilmaguncha (must_change) amallar bloklanadi.
       2) Bearer token bilan kelgan so'rovga 'sess' cookie o'rnatiladi (rasmlar uchun)."""
    p = request.path
    allowed = ("/api/mobile/login", "/api/mobile/logout",
               "/api/mobile/password", "/api/mobile/health")
    if p.startswith("/api/mobile/") and p not in allowed:
        try:
            login = accounts.check_token(_bearer(request))
            if login:
                acc = accounts.get_account(login)
                if acc and acc.get("must_change"):
                    return json_err("Avval parolni o'zgartiring", status=403)
        except Exception:
            pass
    resp = await handler(request)
    # sess cookie (img teglari uchun) — Bearer bor, cookie yo'q bo'lsa
    try:
        if not request.cookies.get("sess"):
            tok = _bearer(request)
            if tok and accounts.check_token(tok):
                resp.set_cookie("sess", tok, max_age=accounts.TOKEN_TTL,
                                httponly=True, samesite="Lax", path="/")
    except Exception:
        pass
    return resp


def build_app():
    app = web.Application(client_max_size=8 * 1024 * 1024,  # rasm yuklash uchun 8MB
                          middlewares=[_auth_mw])
    app.router.add_post("/api/mobile/login", login)
    app.router.add_post("/api/mobile/logout", logout)
    app.router.add_post("/api/mobile/password", change_password)
    app.router.add_post("/api/mobile/refresh_nvr", refresh_nvr)
    app.router.add_get("/api/mobile/me", me)
    app.router.add_post("/api/mobile/exit/submit", exit_submit)
    app.router.add_get("/api/mobile/monthly/{card}", monthly_for_card)
    app.router.add_get("/api/mobile/rating", rating_list)
    app.router.add_get("/api/mobile/rating/months", rating_months)
    app.router.add_get("/api/mobile/late", late_list)
    app.router.add_get("/api/mobile/days/{card}", days_for_card)
    app.router.add_get("/api/mobile/all", all_employees)
    app.router.add_post("/api/mobile/explain/request", explain_request)
    app.router.add_get("/api/mobile/explain/requests", explain_requests_all)
    app.router.add_get("/api/mobile/explain/my", explain_my)
    app.router.add_post("/api/mobile/explain/submit", explain_submit)
    app.router.add_post("/api/mobile/explain/self", explain_self)
    app.router.add_post("/api/mobile/explain/cancel", explain_cancel)
    app.router.add_get("/api/mobile/explain/word/{card}", explain_word)
    app.router.add_get("/api/mobile/explain/pdf/{exp_id}", explain_pdf)
    app.router.add_get("/api/mobile/signature/{exp_id}", signature_img)
    app.router.add_post("/api/mobile/yoqlama/reason", yoqlama_reason)
    app.router.add_post("/api/mobile/explain/delete", explain_delete)
    app.router.add_post("/api/mobile/photo/upload", photo_upload)
    app.router.add_get("/api/mobile/olimlar", olimlar_list)
    app.router.add_post("/api/mobile/olimlar/set", olimlar_set)
    # ── Ariza (xodim -> HR/rahbar) ──
    app.router.add_post("/api/mobile/ariza/create", ariza_create)
    app.router.add_get("/api/mobile/ariza/pdf/{aid}", ariza_pdf)
    app.router.add_get("/api/mobile/ariza/my", ariza_my)
    app.router.add_post("/api/mobile/ariza/cancel", ariza_cancel)
    app.router.add_get("/api/mobile/ariza/all", ariza_all)
    app.router.add_post("/api/mobile/ariza/review", ariza_review)
    app.router.add_post("/api/mobile/ariza/delete", ariza_delete)
    app.router.add_get("/photos/{fname}", photo_handler)
    # Tashkilot nomi (tashkilot.json) — ilova sarlavhasi uchun
    async def org_js(request):
        try:
            import tashkilot
            data = tashkilot.public()
        except Exception:
            data = {}
        resp = web.Response(text="window.ORG = " + json.dumps(data, ensure_ascii=False) + ";",
                            content_type="application/javascript")
        resp.headers["Cache-Control"] = "no-cache"
        return resp
    app.router.add_get("/org.js", org_js)
    app.router.add_get("/api/mobile/health", health)

    # ── HR BOSHQARUV (admin) endpointlari ──
    try:
        import mobile_admin
        mobile_admin.register(app, _require_login, _role_of, json_ok, json_err)
    except Exception as e:
        print(f"[MOBILE ADMIN] yuklanmadi: {e}")

    app.router.add_route("OPTIONS", "/{tail:.*}", options_handler)

    # ── TWA (Google Play) uchun Digital Asset Links ──
    async def assetlinks(request):
        p = BASE_DIR / "mobile" / ".well-known" / "assetlinks.json"
        if p.exists():
            resp = web.FileResponse(p)
            resp.headers["Content-Type"] = "application/json"
            return _cors(resp)
        return _cors(web.json_response([], status=404))
    app.router.add_get("/.well-known/assetlinks.json", assetlinks)

    # ── PWA statik fayllar (mobile/ papkasi) ──
    mobile_dir = BASE_DIR / "mobile"
    if mobile_dir.exists():
        async def index(request):
            return web.FileResponse(mobile_dir / "index.html")
        app.router.add_get("/", index)
        app.router.add_static("/", path=str(mobile_dir), show_index=False)
    return app


# ═══════════════════ TIZIM BOSHQARUVI ═══════════════════
# Avval hamma narsani Telegram bot (main17.py) boshqarardi.
# Endi BOSH BOSHQARUVCHI — shu fayl. U uchta qismni birga ko'taradi:
#   1) Mobil ilova + API        (shu jarayon, port 8090)
#   2) HR dashboard             (dashboard_server, port 8080)
#   3) Jonli kirdi/chiqdi worker (live_worker_api, fon oqimida)
#
# Ishga tushirish:  python mobile_api.py
#
# .env orqali o'chirish mumkin:
#   START_DASHBOARD=0    — dashboard ko'tarilmaydi
#   START_WORKER=0       — worker ko'tarilmaydi (alohida ishga tushirasiz)

def _start_worker_thread():
    """live_worker_api ni fon oqimida ishga tushiradi (bloklamaydi)."""
    import threading

    def _run():
        try:
            import live_worker_api
            live_worker_api.worker_loop()
        except Exception as e:
            print(f"[WORKER] to'xtadi: {type(e).__name__}: {e}")

    th = threading.Thread(target=_run, name="live-worker", daemon=True)
    th.start()
    return th


async def _run_all():
    import asyncio

    runners = []

    # ── 1) Jonli worker (fon oqimi) ──
    if os.getenv("START_WORKER", "1").strip() != "0":
        _start_worker_thread()
        print("[WORKER] jonli kirdi/chiqdi fon oqimida ishga tushdi.")

    # ── 2) HR dashboard ──
    if os.getenv("START_DASHBOARD", "1").strip() != "0":
        try:
            import dashboard_server
            r = await dashboard_server.start_dashboard()
            if r:
                runners.append(r)
        except Exception as e:
            print(f"[DASHBOARD] ishga tushmadi: {type(e).__name__}: {e}")

    # ── 3) Mobil ilova + API (asosiy) ──
    app = build_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    runners.append(runner)
    print(f"[MOBILE API] http://0.0.0.0:{PORT} da ishga tushdi.")
    print("─" * 52)
    print("✅ Tizim ishlayapti. To'xtatish uchun Ctrl+C.")
    print("─" * 52)

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        for r in runners:
            try:
                await r.cleanup()
            except Exception:
                pass


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(_run_all())
    except KeyboardInterrupt:
        print("\n🛑 Tizim to'xtatildi.")
