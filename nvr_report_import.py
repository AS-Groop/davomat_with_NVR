# -*- coding: utf-8 -*-
"""nvr_report_import.py — NVR'dan qo'lda eksport qilingan "Attendance Day Report"
(.xls, aslida HTML jadval) fayllaridan kirish/chiqish hodisalarini o'qiydi.

Nega kerak: bizdagi FaceID terminal (Tank, Dahua-OEM) va u ulangan NVR
(TVT NVMS-9000 platforma) `faceid_devices.py` kutadigan Hikvision ISAPI
yoki ZKTeco protokollarini bermaydi — shu sabab shu alohida modul yozildi.

Ikki yo'l bilan ma'lumot kelishi mumkin (ikkalasi ham shu modulda
birlashtiriladi):
  1. **Qo'lda eksport** — NVR veb-klientida "Приветствие → Статистика
     посещения → Экспорт → Attendance Report" bilan olingan .xls (HTML
     jadval) fayl shu papkaga (`nvr_reports/`) tashlanadi.
  2. **Avtomatik** — Boshqaruv panelidagi "Yangilash" tugmasi `nvr_live.py`
     orqali NVR'ga to'g'ridan-to'g'ri ulanib, `_live_cache.json` ga yozadi
     (login protokoli reverse-engineering qilingan va ishlaydi — tafsilot
     `nvr_live.py` da).

.env da FACEID_SOURCE=nvr_reports bo'lsa — tizim ikkalasini ham avtomatik
o'qiydi.

Fayl tuzilishi (NVR eksporti, ustunlar tartibi bo'yicha, sarlavha matni
kirill/lotin aralash chiqishi mumkin — shu sabab nom bo'yicha emas, o'rin
bo'yicha o'qiymiz):
  [0] №  [1] Work Number (qurilmadagi xodim raqami — users.xlsx "faceid")
  [2] Имя  ...  [10] Дата ("YYYY/MM/DD")  ...
  [19] All Records — kun davomidagi barcha o'tish vaqtlari, bo'sh joy bilan
       ajratilgan ("09:05 13:59 15:59 18:29"): toq o'rin = kirish,
       juft o'rin = chiqish (navbatma-navbat).

Oxirgi qator — statistika summary ("41 людей ..."), Work Number raqam
bo'lmagani uchun avtomatik o'tkazib yuboriladi.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, date as _date
from pathlib import Path

ENTER, EXIT = "вход", "выход"
BASE_DIR = Path(".")
REPORTS_DIR = BASE_DIR / "nvr_reports"

_LOCK = threading.RLock()
_CACHE = {"listing": None, "rows": []}  # listing = {path: mtime}, rows = parsed hodisalar


def _report_files() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(p for p in REPORTS_DIR.iterdir() if p.suffix.lower() in (".xls", ".xlsx"))


def _parse_file(path: Path) -> list[dict]:
    """Bitta eksport faylidan [{"work_no", "date", "dt", "type"}, ...] qaytaradi."""
    import pandas as pd

    try:
        tables = pd.read_html(path, encoding="utf-8")
    except Exception as e:
        print(f"[NVR_REPORT] {path.name}: o'qib bo'lmadi — {type(e).__name__}: {e}")
        return []
    if not tables:
        return []
    df = tables[0]

    out = []
    for row in df.itertuples(index=False, name=None):
        if len(row) < 20:
            continue
        work_no = str(row[1]).strip()
        if not work_no.isdigit():
            continue  # summary/footer qatori
        date_str = str(row[10]).strip()
        try:
            day = datetime.strptime(date_str, "%Y/%m/%d").date()
        except Exception:
            continue
        records = str(row[19]).strip()
        if not records or records.lower() == "nan":
            continue
        times = records.split()
        nxt = ENTER
        for t in times:
            try:
                hh, mm = t.split(":")[:2]
                dt = datetime(day.year, day.month, day.day, int(hh), int(mm))
            except Exception:
                continue
            out.append({"work_no": work_no, "dt": dt, "type": nxt})
            nxt = EXIT if nxt == ENTER else ENTER
    return out


LIVE_CACHE_FILE = REPORTS_DIR / "_live_cache.json"


def _live_cache_rows() -> list[dict]:
    """nvr_live.py (\"Yangilash\" tugmasi) yozib qo'ygan keshni o'qiydi."""
    try:
        data = json.loads(LIVE_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    out = []
    for day_rows in data.values() if isinstance(data, dict) else []:
        for r in day_rows:
            try:
                out.append({
                    "work_no": str(r["work_no"]),
                    "dt": datetime.fromisoformat(r["dt"]),
                    "type": r["type"],
                })
            except Exception:
                continue
    return out


def _all_rows(force: bool = False) -> list[dict]:
    with _LOCK:
        listing = {p: p.stat().st_mtime for p in _report_files()}
        try:
            listing[LIVE_CACHE_FILE] = LIVE_CACHE_FILE.stat().st_mtime
        except Exception:
            pass
        if not force and listing == _CACHE["listing"]:
            return _CACHE["rows"]
        rows = []
        for p in listing:
            if p == LIVE_CACHE_FILE:
                continue
            rows.extend(_parse_file(p))
        rows.extend(_live_cache_rows())
        _CACHE.update(listing=listing, rows=rows)
        return rows


def events_for_workno(work_no, start_date: str, end_date: str) -> list[dict]:
    """Bitta xodim (qurilmadagi Work Number) uchun berilgan oraliqdagi hodisalar.

    Natija faceid_devices.device_events bilan bir xil shaklda:
      [{"dt": datetime, "type": "вход"/"выход", "raw_type": ""}, ...]
    """
    wn = str(work_no).strip()
    if not wn:
        return []
    a = datetime.strptime(str(start_date)[:10], "%Y-%m-%d").date()
    b = datetime.strptime(str(end_date)[:10], "%Y-%m-%d").date()
    out = [
        {"dt": r["dt"], "type": r["type"], "raw_type": ""}
        for r in _all_rows()
        if r["work_no"] == wn and a <= r["dt"].date() <= b
    ]
    out.sort(key=lambda e: e["dt"])
    return out


def ping() -> bool:
    return bool(_report_files())
