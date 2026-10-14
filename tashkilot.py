# -*- coding: utf-8 -*-
"""Tashkilot ma'lumotlari — YAGONA MANBA (tashkilot.json).

Nomi, to'liq nomi, tushuntirish xati kimga yoziladi — barchasi shu fayldan.
Boshqa tashkilotga o'rnatishda faqat tashkilot.json va mobile/logo.png
almashtiriladi.
"""
from __future__ import annotations

import json
from pathlib import Path

FILE = Path(__file__).resolve().parent / "tashkilot.json"

DEFAULT = {
    "name": "Tashkilot",
    "name_ru": "",
    "short": "",
    "full": "Tashkilot",
    "explanation_addressee": "Tashkilot rahbariga",
}


def get() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return {**DEFAULT, **d}
    except Exception:
        pass
    return dict(DEFAULT)


def public() -> dict:
    """Ilovaga beriladigan qism (maxfiy narsa yo'q)."""
    d = get()
    return {k: d.get(k, "") for k in ("name", "name_ru", "short", "full")}
