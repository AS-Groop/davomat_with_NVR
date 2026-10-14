"""
roles.py — Rollar, turkumlar, bayram/dam olish kunlari va rozilik moduli.

Bot 3 xil ROL va xodim TURKUMLARI bilan ishlaydi:

  ROL (interfeys/ruxsat):
    - hr        : to'liq admin huquqi (uzrli, bayram, xabar yuborish). Hech kim ko'rmaydi.
    - director  : hammani ko'radi (tushuntirish, kechikkanlar), lekin hr funksiyalari yo'q.
    - employee  : faqat o'zini ko'radi.

  TURKUM (nazorat turi — bot tushuntirish so'raydimi?):
    - oddiy       : kechikish/chiqib ketish aniqlanadi, tushuntirish SO'RALADI.
    - amaliyotchi : faqat keldi/ketdi ko'rinadi, tushuntirish SO'RALMAYDI.
    - haydovchi   : faqat keldi/ketdi, tushuntirish SO'RALMAYDI.
    - rahbar      : direktor/o'rinbosarlar — faqat keldi/ketdi, tushuntirish SO'RALMAYDI.

Rol va turkum users.xlsx dagi `role` va `category` ustunlaridan o'qiladi.
Bayram kunlari holidays.json da saqlanadi (HR bot orqali kiritadi).
Rozilik consent.json da saqlanadi (xodim /start bosishi bilan beriladi).
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, date
from typing import Any, Optional

import pandas as pd

BASE_DIR = Path(".")

EMPLOYEE_FILE_CANDIDATES = [
    BASE_DIR / "users.xlsx",
    BASE_DIR / "users(2).xlsx",
    BASE_DIR / "employees.xlsx",
]

HOLIDAYS_FILE = BASE_DIR / "holidays.json"
CONSENT_FILE = BASE_DIR / "consent.json"

# Legacy adminlar (.env dagi AUTHORIZED_USERS) — avtomatik HR hisoblanadi.
AUTHORIZED_USERS = [
    int(x.strip())
    for x in os.getenv("AUTHORIZED_USERS", "").split(",")
    if x.strip().isdigit()
]

# Turkumlar: faqat "oddiy" turkumdan tushuntirish so'raladi.
ASK_EXPLANATION_CATEGORIES = {"oddiy"}

VALID_ROLES = {"hr", "director", "employee"}
VALID_CATEGORIES = {"oddiy", "amaliyotchi", "haydovchi", "rahbar", "masofaviy"}

# Rozilik matni (xodim /start bosganda bir marta ko'rsatiladi).
CONSENT_TEXT = (
    "🔐 Maxfiylik va rozilik\n"
    "────────────────────────────\n"
    "Ushbu bot sizning ish vaqtidagi kirish va chiqish ma'lumotlaringizni "
    "(faqat ish maqsadida) qayd etadi va ko'rsatadi.\n\n"
    "Botdan foydalanishni davom ettirish orqali siz ushbu ma'lumotlarning "
    "qayd etilishiga rozilik bildirasiz.\n"
    "────────────────────────────"
)


# ─────────────────────────── MATN NORMALLASH ───────────────────────────

def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = (
        text.replace("o‘", "o").replace("g‘", "g")
        .replace("o'", "o").replace("g'", "g")
        .replace("’", "").replace("'", "").replace('"', "")
    )
    text = re.sub(r"[^a-zа-яё0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _norm_col(value: Any) -> str:
    return _norm(value).replace(" ", "_")


# ─────────────────────────── EXCEL O'QISH ───────────────────────────

def _find_employee_file() -> Optional[Path]:
    for path in EMPLOYEE_FILE_CANDIDATES:
        if path.exists():
            return path
    return None


def _detect_header_row(df_raw: pd.DataFrame) -> int:
    keywords = ["familiya", "familya", "ism", "sharif", "card", "telegram",
                "role", "category", "turkum", "active"]
    best_idx, best_score = 0, -1
    for idx in range(min(len(df_raw), 15)):
        row_text = " ".join(_norm(x) for x in df_raw.iloc[idx].tolist())
        score = sum(1 for k in keywords if k in row_text)
        if score > best_score:
            best_score, best_idx = score, idx
    return best_idx


# Kesh: faylni har safar emas, o'zgarganda qayta o'qiymiz.
_CACHE: dict[str, Any] = {"mtime": None, "by_tg": {}, "by_card": {}, "rows": []}


def _get(row: dict, *names: str) -> str:
    for name in names:
        if name in row and pd.notna(row[name]):
            return str(row[name]).strip()
    return ""


def _normalize_role(raw: str) -> str:
    r = _norm(raw)
    if r in {"hr", "inson_resurslari", "kadr"}:
        return "hr"
    if r in {"director", "direktor", "rahbar_director"}:
        return "director"
    return "employee"


def _normalize_category(raw: str) -> str:
    c = _norm(raw)
    if c in {"amaliyotchi", "intern", "praktikant", "stajyor"}:
        return "amaliyotchi"
    if c in {"haydovchi", "driver", "shofyor"}:
        return "haydovchi"
    if c in {"rahbar", "direktor", "orinbosar", "director", "deputy"}:
        return "rahbar"
    # bo'sh yoki noma'lum bo'lsa — "oddiy" (xavfsiz: tushuntirish so'raladi)
    return "oddiy"


def _reload_if_needed() -> None:
    path = _find_employee_file()
    if not path:
        _CACHE.update({"mtime": None, "by_tg": {}, "by_card": {}, "rows": []})
        return

    mtime = path.stat().st_mtime
    if _CACHE["mtime"] == mtime and _CACHE["rows"]:
        return  # kesh yangi

    df_preview = pd.read_excel(path, header=None)
    header_row = _detect_header_row(df_preview)
    df = pd.read_excel(path, header=header_row)
    df.columns = [_norm_col(c) for c in df.columns]

    by_tg: dict[int, dict] = {}
    by_card: dict[str, dict] = {}
    rows: list[dict] = []

    for _, raw in df.iterrows():
        row = raw.to_dict()
        last_name = _get(row, "familiya", "familya", "last_name")
        first_name = _get(row, "ism", "first_name", "name")
        middle_name = _get(row, "sharif", "middle_name", "otchestvo")
        full_name = " ".join(x for x in [last_name, first_name, middle_name] if x).strip()

        card = _get(row, "card_number", "card", "cardnumber", "karta_raqami")
        tg_raw = _get(row, "telegram_id", "telegram", "telegramid", "tg_id", "telegram_id_")
        role = _normalize_role(_get(row, "role", "rol", "lavozim_turi"))
        category = _normalize_category(_get(row, "category", "turkum", "kategoriya"))
        birthday = _get(row, "tugilgan_sana", "birthday", "bday", "tugilgan", "tavallud")
        photo_file = _get(row, "photo_file", "photo", "rasm")

        tg_id = None
        digits = re.sub(r"\D", "", tg_raw)
        if digits:
            try:
                tg_id = int(digits)
            except ValueError:
                tg_id = None

        rec = {
            "full_name": full_name,
            "card_number": card,
            "telegram_id": tg_id,
            "role": role,
            "category": category,
            "birthday": birthday,
            "photo_file": photo_file,
        }
        rows.append(rec)
        if tg_id is not None:
            by_tg[tg_id] = rec
        if card:
            by_card[card] = rec

    _CACHE.update({"mtime": mtime, "by_tg": by_tg, "by_card": by_card, "rows": rows})


def reload() -> None:
    """Keshni majburiy yangilash."""
    _CACHE["mtime"] = None
    _reload_if_needed()


# ─────────────────────────── ROL FUNKSIYALARI ───────────────────────────

def get_record_by_tg(tg_id: int) -> Optional[dict]:
    _reload_if_needed()
    return _CACHE["by_tg"].get(tg_id)


def get_record_by_card(card: str) -> Optional[dict]:
    _reload_if_needed()
    return _CACHE["by_card"].get(str(card).strip())


def all_employees() -> list[dict]:
    """Hamma xodimlar (HR, direktor, oddiy — barchasi) ro'yxati."""
    _reload_if_needed()
    return list(_CACHE["by_card"].values())


def get_role_by_tg(tg_id: int) -> str:
    if tg_id in AUTHORIZED_USERS:
        return "hr"  # legacy adminlar = HR
    rec = get_record_by_tg(tg_id)
    return rec["role"] if rec else "employee"


def is_hr(tg_id: int) -> bool:
    return get_role_by_tg(tg_id) == "hr"


def is_director(tg_id: int) -> bool:
    return get_role_by_tg(tg_id) == "director"


def can_view_reports(tg_id: int) -> bool:
    """HR yoki Direktor — hisobotlarni ko'ra oladi."""
    return get_role_by_tg(tg_id) in {"hr", "director"}


def is_hr_card(card: str) -> bool:
    rec = get_record_by_card(card)
    return bool(rec and rec["role"] == "hr")


def is_hr_tg(tg_id: int) -> bool:
    return is_hr(tg_id)


# ─────────────────────────── TURKUM FUNKSIYALARI ───────────────────────────

def get_category_by_card(card: str) -> str:
    rec = get_record_by_card(card)
    return rec["category"] if rec else "oddiy"


def should_ask_explanation(card: str) -> bool:
    """Faqat 'oddiy' turkumdagi xodimdan tushuntirish so'raladi."""
    return get_category_by_card(card) in ASK_EXPLANATION_CATEGORIES


def all_telegram_ids(exclude_hr: bool = False, exclude_categories: set | None = None) -> list[int]:
    """Barcha xodimlarning Telegram ID'lari (xabar yuborish uchun)."""
    _reload_if_needed()
    exclude_categories = exclude_categories or set()
    ids = []
    for rec in _CACHE["rows"]:
        tg = rec.get("telegram_id")
        if tg is None:
            continue
        if exclude_hr and rec.get("role") == "hr":
            continue
        if rec.get("category") in exclude_categories:
            continue
        ids.append(tg)
    return list(dict.fromkeys(ids))  # takrorlarni olib tashlash


def broadcast_telegram_ids() -> list[int]:
    """E'lon yuborish uchun — haydovchi, direktor va o'rinbosarlar (rahbar) chiqariladi."""
    return all_telegram_ids(exclude_categories={"haydovchi", "rahbar"})


def hr_telegram_ids() -> list[int]:
    """HR rolidagi xodimlarning Telegram ID'lari."""
    _reload_if_needed()
    ids = [r["telegram_id"] for r in _CACHE["rows"]
           if r.get("role") == "hr" and r.get("telegram_id") is not None]
    # legacy adminlar ham HR
    ids += [a for a in AUTHORIZED_USERS]
    return list(dict.fromkeys(ids))


# ─────────────────────────── TUG'ILGAN KUN ───────────────────────────

def _parse_birthday_md(s: str):
    """Tug'ilgan sanadan (oy, kun) ni ajratadi. DD.MM.YYYY, YYYY-MM-DD, DD/MM/YYYY."""
    s = str(s or "").strip()
    if not s or s.lower() == "nan":
        return None
    # YYYY-MM-DD
    m = re.match(r"^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$", s)
    if m:
        return (int(m.group(2)), int(m.group(3)))
    # DD.MM.YYYY yoki DD/MM/YYYY yoki DD-MM-YYYY
    m = re.match(r"^(\d{1,2})[-./](\d{1,2})[-./](\d{2,4})$", s)
    if m:
        return (int(m.group(2)), int(m.group(1)))
    return None


def birthdays_today(date_str: Optional[str] = None) -> list[dict]:
    """Bugun (yoki berilgan sanada) tug'ilgan kuni bo'lgan xodimlar."""
    _reload_if_needed()
    d = _parse_date(date_str)
    today_md = (d.month, d.day)
    result = []
    for rec in _CACHE["rows"]:
        md = _parse_birthday_md(rec.get("birthday", ""))
        if md and md == today_md:
            result.append(rec)
    return result


# ─────────────────────────── ROZILIK ───────────────────────────

def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def consent_given(tg_id: int) -> bool:
    data = _load_json(CONSENT_FILE, {})
    return str(tg_id) in data


def set_consent(tg_id: int) -> None:
    data = _load_json(CONSENT_FILE, {})
    if str(tg_id) not in data:
        data[str(tg_id)] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _save_json(CONSENT_FILE, data)


# ─────────────────────────── BAYRAM / DAM OLISH ───────────────────────────

def load_holidays() -> dict[str, str]:
    """{'2026-01-01': 'Yangi yil', ...}"""
    return _load_json(HOLIDAYS_FILE, {})


def add_holiday(date_str: str, name: str = "") -> bool:
    data = load_holidays()
    data[date_str] = name or "Bayram / dam olish"
    _save_json(HOLIDAYS_FILE, data)
    return True


def remove_holiday(date_str: str) -> bool:
    data = load_holidays()
    if date_str in data:
        del data[date_str]
        _save_json(HOLIDAYS_FILE, data)
        return True
    return False


def list_holidays() -> list[tuple[str, str]]:
    data = load_holidays()
    return sorted(data.items())


def is_weekend(date_str: Optional[str] = None) -> bool:
    """Shanba (5) yoki Yakshanba (6)?"""
    d = _parse_date(date_str)
    return d.weekday() >= 5


def is_holiday(date_str: Optional[str] = None) -> bool:
    d = _parse_date(date_str)
    return d.strftime("%Y-%m-%d") in load_holidays()


def is_working_day(date_str: Optional[str] = None) -> bool:
    """Ish kunimi? (dam olish va bayram emas)"""
    return not is_weekend(date_str) and not is_holiday(date_str)


def _parse_date(date_str: Optional[str]) -> date:
    if not date_str:
        return datetime.now().date()
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except Exception:
        return datetime.now().date()


# ─────────────────────────── TEST ───────────────────────────

if __name__ == "__main__":
    reload()
    print(f"Jami xodim: {len(_CACHE['rows'])}")
    print(f"Telegram ID bor: {len(_CACHE['by_tg'])}")
    from collections import Counter
    roles_count = Counter(r["role"] for r in _CACHE["rows"])
    cats_count = Counter(r["category"] for r in _CACHE["rows"])
    print("Rollar:", dict(roles_count))
    print("Turkumlar:", dict(cats_count))
    print("Bugun ish kunimi:", is_working_day())
    print("Bayramlar:", list_holidays())
