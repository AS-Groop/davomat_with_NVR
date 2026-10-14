# -*- coding: utf-8 -*-
"""build_departments.py — xodimlarning BO'LIM va LAVOZIMini users.xlsx dan oladi
va employee_departments.json ga (JSHSHIR bo'yicha) yozadi.

Tushuntirish xati, dashboard va hisobotlar bo'lim/lavozimni shu fayldan oladi.
users.xlsx dagi ustunlar: "bo'lim" (yoki bolim / department / guruh) va
"lavozim" (yoki position). Qo'lda tuzatishlar uchun:
employee_departments_manual.json  {"<jshshir>": {"department": "...", "position": "..."}}

Ishga tushirish:  python build_departments.py   (start_all.py o'zi chaqiradi)
"""
import json
import re
from pathlib import Path

BASE_DIR = Path(".")
USERS = BASE_DIR / "users.xlsx"
OUT_FILE = BASE_DIR / "employee_departments.json"
MANUAL_FILE = BASE_DIR / "employee_departments_manual.json"


def _key(v):
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower().replace("ʻ", "").replace("‘", "").replace("'", ""))


def _clean(v):
    s = "" if v is None else str(v).strip()
    return "" if s.lower() in ("nan", "none") else s


def main():
    try:
        import openpyxl
        wb = openpyxl.load_workbook(USERS, read_only=True, data_only=True)
    except Exception as e:
        print(f"  users.xlsx o'qilmadi: {e}")
        return
    rows = list(wb.active.iter_rows(values_only=True))
    wb.close()
    hdr = None
    for i, r in enumerate(rows[:10]):
        keys = [_key(c) for c in r]
        if "familiya" in keys or "cardnumber" in keys:
            hdr = i
            break
    if hdr is None:
        print("  users.xlsx da sarlavha qatori topilmadi")
        return
    keys = [_key(c) for c in rows[hdr]]

    def col(*names):
        return next((keys.index(n) for n in names if n in keys), None)
    c_card = col("cardnumber", "card", "jshshir", "pinfl")
    c_ln, c_fn, c_mn = col("familiya", "familya"), col("ism"), col("sharif")
    c_dep = col("bolim", "department", "guruh", "bulim")
    c_pos = col("lavozim", "position", "lavozimi")
    out = {}
    for r in rows[hdr + 1:]:
        g = lambda c: _clean(r[c]) if c is not None and c < len(r) else ""
        card = re.sub(r"\D", "", g(c_card).split(".")[0])
        if not card:
            continue
        out[card] = {"department": g(c_dep), "position": g(c_pos),
                     "full_name": " ".join(x for x in (g(c_ln), g(c_fn), g(c_mn)) if x)}
    try:
        manual = json.loads(MANUAL_FILE.read_text(encoding="utf-8"))
        for card, v in (manual or {}).items():
            out.setdefault(str(card), {}).update({k: v[k] for k in ("department", "position", "full_name") if v.get(k)})
    except Exception:
        pass
    OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    with_dep = sum(1 for v in out.values() if v.get("department"))
    print(f"  {len(out)} xodim · bo'limi ko'rsatilgan: {with_dep}")


if __name__ == "__main__":
    main()
