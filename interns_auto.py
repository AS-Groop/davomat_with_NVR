# -*- coding: utf-8 -*-
"""Amaliyotchilarni AVTOMATIK nofaol qilish.

Qoida (HR qarori):
  - Oxirgi 10 KALENDAR kun ichida turniketdan birorta ham kirish/chiqish
    bo'lmagan amaliyotchi avtomatik NOFAOL bo'ladi — dashboarddan yashiriladi.
    interns.xlsx ga tegilmaydi.
  - Yangi qo'shilgan (hali kirmagan) amaliyotchi uchun 10 kun ro'yxatga
    qo'shilgan kundan sanaladi.
  - Avtomatik nofaol bo'lgan amaliyotchi turniketdan o'tsa — o'zi qaytadi.
  - HR qo'lda nofaol qilganlar (interns_inactive.json) avtomatik QAYTMAYDI.
  - HR qayta faol qilsa — shu kundan yana 10 kun sanaladi.

Ma'lumot: interns_auto.json
  first_seen: {card: "YYYY-MM-DD"}  — ro'yxatda birinchi ko'ringan kun
  last_seen:  {card: "YYYY-MM-DD"}  — oxirgi kirish/chiqish kuni
  grace:      {card: "YYYY-MM-DD"}  — HR qayta faol qilgan kun
  auto:       {card: {"since": "YYYY-MM-DD", "last_seen": "YYYY-MM-DD"|""}}
  checked:    "YYYY-MM-DD"            — kunlik tekshiruv oxirgi marta

Sinov (hech narsani o'zgartirmaydi):  python interns_auto.py
"""
from __future__ import annotations

import json
import os
import threading
import time as _time
from datetime import date, datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
AUTO_FILE = BASE_DIR / "interns_auto.json"
INACTIVE_DAYS = int(os.getenv("INTERN_INACTIVE_DAYS", "10"))
RETURN_CHECK_SECONDS = 300          # avtomatik nofaollar qaytdimi — 5 daqiqada bir

_LOCK = threading.RLock()
_last_return_check = 0.0


def _today() -> date:
    return date.today()


def _iso(d: date) -> str:
    return d.isoformat()


def _d(s: str) -> date | None:
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def load() -> dict:
    try:
        d = json.loads(AUTO_FILE.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}
    for k in ("first_seen", "last_seen", "grace", "auto"):
        if not isinstance(d.get(k), dict):
            d[k] = {}
    d.setdefault("checked", "")
    return d


def save(d: dict) -> None:
    tmp = AUTO_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(AUTO_FILE)


def auto_cards() -> set:
    return set(load()["auto"].keys())


def info() -> dict:
    """HR paneli uchun: {card: {"auto": bool, "since", "last_seen"}}"""
    d = load()
    out = {}
    for c, v in d["last_seen"].items():
        out.setdefault(c, {})["last_seen"] = v
    for c, v in d["auto"].items():
        out.setdefault(c, {}).update({"auto": True, "since": v.get("since", ""),
                                      "last_seen": v.get("last_seen", "") or out.get(c, {}).get("last_seen", "")})
    return out


# ─────────────────────── worker chaqiradi ───────────────────────
def note_roster(cards) -> None:
    """Ro'yxatdagi kartalar — birinchi ko'ringan kunni eslab qolamiz.

    Birinchi ishga tushishda (fayl yo'q) mavjud amaliyotchilar "eski" deb
    olinadi — ular uchun kutish muddati yo'q, oxirgi 10 kunda kelmagan
    bo'lsa darhol nofaol bo'ladi.
    """
    with _LOCK:
        first_run = not AUTO_FILE.exists()
        d = load()
        changed = first_run
        for c in cards:
            c = str(c)
            if c and c not in d["first_seen"]:
                d["first_seen"][c] = "2000-01-01" if first_run else _iso(_today())
                changed = True
        if changed:
            save(d)


def note_seen(cards) -> bool:
    """Bugun kirish/chiqishi bor kartalar. Avtomatik nofaol bo'lsa — qaytaradi.
    True — ro'yxat o'zgardi (worker amaliyotchilarni qayta yuklashi kerak)."""
    today = _iso(_today())
    changed_list = False
    with _LOCK:
        d = load()
        dirty = False
        for c in cards:
            c = str(c)
            if d["last_seen"].get(c) != today:
                d["last_seen"][c] = today
                dirty = True
            if c in d["auto"]:
                del d["auto"][c]
                dirty = changed_list = True
                print(f"[AMALIYOTCHI] {c} qaytib keldi — yana faol")
        if dirty:
            save(d)
    return changed_list


def _baseline(d: dict, card: str) -> date:
    """Kutish qaysi kundan sanaladi: oxirgi kelgan / ro'yxatga qo'shilgan / HR qaytargan."""
    cands = [_d(d["last_seen"].get(card, "")), _d(d["first_seen"].get(card, "")),
             _d(d["grace"].get(card, ""))]
    cands = [x for x in cands if x]
    return max(cands) if cands else date(2000, 1, 1)


def evaluate(cards, get_events, dry_run: bool = False) -> list[dict]:
    """Faol amaliyotchilarni tekshiradi. Nofaol bo'lishi kerak bo'lganlar ro'yxati.

    get_events(card, "YYYY-MM-DD", "YYYY-MM-DD") -> [{"dt": datetime, ...}]
    """
    today = _today()
    limit = today - timedelta(days=INACTIVE_DAYS)       # shu kun va undan oldin — eski
    start = _iso(limit)
    out = []
    d = load()
    for c in cards:
        c = str(c)
        if not c or c in d["auto"]:
            continue
        base = _baseline(d, c)
        if base > limit:
            continue                                 # muddat hali o'tmagan
        try:
            evs = get_events(c, start, _iso(today)) or []
        except Exception as e:
            print(f"[AMALIYOTCHI] {c}: hodisalarni olib bo'lmadi ({e}) — o'tkazildi")
            continue
        if evs:
            last = max(ev["dt"] for ev in evs).date()
            if not dry_run:
                with _LOCK:
                    dd = load()
                    if (_d(dd["last_seen"].get(c, "")) or date(2000, 1, 1)) < last:
                        dd["last_seen"][c] = _iso(last)
                        save(dd)
            if last > limit:
                continue
        last_s = d["last_seen"].get(c, "")
        out.append({"card": c, "last_seen": last_s,
                    "first_seen": d["first_seen"].get(c, "")})
        _time.sleep(0.05)
    return out


_last_fail = 0.0


def maybe_daily(cards, get_events, api_ok=None) -> bool:
    """Kuniga bir marta. True — kimdir nofaol bo'ldi.

    api_ok() — turniket tizimi ishlayaptimi (oddiy xodimlarda hodisa bormi).
    API vaqtincha bo'sh javob qaytarsa, hammani nofaol qilib yubormaslik uchun:
    tekshiruv natijasi qo'llanmaydi va bir soatdan keyin qayta uriniladi.
    """
    global _last_fail
    today = _iso(_today())
    if load().get("checked") == today:
        return False
    if _time.time() - _last_fail < 3600:
        return False
    hits = evaluate(cards, get_events)
    if hits and api_ok is not None:
        try:
            healthy = bool(api_ok())
        except Exception:
            healthy = False
        if not healthy:
            _last_fail = _time.time()
            print("[AMALIYOTCHI] turniket tizimidan ma'lumot kelmadi — tekshiruv 1 soatdan keyin")
            return False
    with _LOCK:
        d = load()
        for h in hits:
            d["auto"][h["card"]] = {"since": today, "last_seen": h["last_seen"]}
            print(f"[AMALIYOTCHI] {h['card']} — {INACTIVE_DAYS} kundan beri kelmagan, "
                  f"avtomatik nofaol (oxirgi: {h['last_seen'] or 'hech qachon'})")
        d["checked"] = today
        save(d)
    return bool(hits)


def check_returns(get_events) -> bool:
    """Avtomatik nofaollardan bugun kirganlar bormi (5 daqiqada bir)."""
    global _last_return_check
    if _time.time() - _last_return_check < RETURN_CHECK_SECONDS:
        return False
    _last_return_check = _time.time()
    today = _iso(_today())
    back = []
    for c in list(load()["auto"].keys()):
        try:
            if get_events(c, today, today):
                back.append(c)
        except Exception:
            pass
        _time.sleep(0.05)
    return note_seen(back) if back else False


# ─────────────────────── HR paneli chaqiradi ───────────────────────
def reactivate(card: str) -> None:
    """HR qayta faol qildi — avtomatik ro'yxatdan chiqadi, 10 kun qaytadan sanaladi."""
    card = str(card)
    with _LOCK:
        d = load()
        d["auto"].pop(card, None)
        d["grace"][card] = _iso(_today())
        save(d)


def drop_auto(card: str) -> None:
    """HR qo'lda nofaol qildi — endi bu 'qo'lda' holat (avtomatik qaytmaydi)."""
    card = str(card)
    with _LOCK:
        d = load()
        if card in d["auto"]:
            d["auto"].pop(card, None)
            save(d)


if __name__ == "__main__":
    # SINOV: hozir kim nofaol bo'lardi (hech narsa o'zgartirilmaydi)
    os.chdir(BASE_DIR)
    import live_worker_api as lw
    import biocontrol_api as api
    interns = lw.load_interns()
    print(f"Faol amaliyotchilar: {len(interns)}. Oxirgi {INACTIVE_DAYS} kun tekshirilmoqda...\n")
    names = {i["card_number"]: i["full_name"] for i in interns}
    hits = evaluate([i["card_number"] for i in interns], api.get_events, dry_run=True)
    if not hits:
        print("Hech kim nofaol bo'lmaydi.")
    for i, h in enumerate(hits, 1):
        print(f"{i:2}. {names.get(h['card'], h['card'])} — oxirgi: {h['last_seen'] or 'hech qachon'}")
    input("\nEnter — chiqish")
