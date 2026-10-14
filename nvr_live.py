# -*- coding: utf-8 -*-
"""nvr_live.py — NVR (TVT/NVMS-9000) bilan to'g'ridan-to'g'ri gaplashib,
kirish/chiqish hodisalarini avtomatik tortib oladi (Boshqaruv panelidagi
"Yangilash" tugmasi shuni chaqiradi).

Protokol (NVR veb-klienti JS kodidan — js/app/login.js,
js/lib/Communication.js, js/app/Attendance/attendRecord.js — o'qib
aniqlangan va haqiqiy login bilan tasdiqlangan):

  1. POST /reqLogin (token=null) -> javobda nonce, token, sessionId.
  2. parol_xesh = SHA1( MD5(parol).hexdigest().upper() + nonce ).hexdigest().upper()
     (nonce — qavslari {...} bilan, o'zgarishsiz).
  3. POST /doLogin, <token>{1-qadamdagi token}</token> + userName/password,
     **MUHIM**: so'rovda `Cookie: sessionId={sessionId, qavslarsiz}` header
     bo'lishi SHART — bu brauzerda sof JavaScript orqali (server buyrug'isiz)
     qo'yiladi, shuning uchun uni ko'rmay qolish oson (Set-Cookie'da yo'q).
     Shu header'siz server doim `errorCode 536870934` bilan rad etadi.
  4. Kirish/chiqish uchun: POST /queryAttendanceStatisticDetail,
     <condition><startTime>YYYY-MM-DD 00:00:00</startTime>
     <endTime>YYYY-MM-DD 23:59:59</endTime><detailType>byDay</detailType>
     <idParam><item>{workNumber}</item>...</idParam></condition>
     Javobda har xodim uchun detail>item>Record>item — kun davomidagi
     barcha punch vaqtlari ("H:M", nol bilan to'ldirilmagan).

Natija `nvr_reports/_live_cache.json` ga yoziladi — `nvr_report_import.py`
shu faylni ham o'qiydi (qo'lda tashlangan .xls fayllar bilan bir qatorda).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE_DIR = Path(".")
REPORTS_DIR = BASE_DIR / "nvr_reports"
LIVE_CACHE_FILE = REPORTS_DIR / "_live_cache.json"
USERS_FILE = BASE_DIR / "users.xlsx"

HOST = os.getenv("NVR_HOST", "")
USER = os.getenv("NVR_USER", "admin")
PASSWORD = os.getenv("NVR_PASSWORD", "")
TIMEOUT = 10

ENTER, EXIT = "вход", "выход"


class NvrError(Exception):
    pass


def _http_post(path: str, body: bytes, cookie: str | None = None) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.settimeout(TIMEOUT)
    s.connect((HOST, 80))
    cookie_line = f"Cookie: {cookie}\r\n" if cookie else ""
    req = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {HOST}\r\n"
        f"Connection: keep-alive\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Accept: application/xml, text/xml, */*; q=0.01\r\n"
        f"X-Requested-With: XMLHttpRequest\r\n"
        f"Content-Type: application/x-www-form-urlencoded; charset=UTF-8\r\n"
        f"Origin: http://{HOST}\r\n"
        f"Referer: http://{HOST}/\r\n"
        f"{cookie_line}"
        f"Accept-Encoding: identity\r\n\r\n"
    ).encode("ascii") + body
    try:
        s.sendall(req)
        chunks = []
        while True:
            c = s.recv(65536)
            if not c:
                break
            chunks.append(c)
    finally:
        s.close()
    raw = b"".join(chunks)
    _, _, body_out = raw.partition(b"\r\n\r\n")
    return body_out.decode("utf-8", "replace")


def login() -> tuple[str, str]:
    """NVR'ga kiradi. Qaytaradi: (token, sessionId) — keyingi so'rovlar uchun.
    Xato bo'lsa NvrError ko'taradi."""
    if not HOST or not PASSWORD:
        raise NvrError("NVR_HOST yoki NVR_PASSWORD .env da yo'q")

    req1 = (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<request version="1.0"  systemType="NVMS-9000" clientType="WEB">'
        "<token>null</token></request>"
    )
    resp1 = _http_post("/reqLogin", req1.encode("utf-8"))
    nonce_m = re.search(r"<nonce>(.*?)</nonce>", resp1)
    token_m = re.search(r"<token>(.*?)</token>", resp1)
    sid_m = re.search(r"<sessionId>(.*?)</sessionId>", resp1)
    if not (nonce_m and token_m and sid_m):
        raise NvrError(f"reqLogin javobi noto'g'ri: {resp1[:300]}")
    nonce, token = nonce_m.group(1), token_m.group(1)
    sid = sid_m.group(1).strip("{}")

    md5_pw = hashlib.md5(PASSWORD.encode("utf-8")).hexdigest().upper()
    pw_hash = hashlib.sha1((md5_pw + nonce).encode("utf-8")).hexdigest().upper()
    req2 = (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<request version="1.0"   systemType="NVMS-9000" clientType="WEB">'
        f"<token>{token}</token>"
        f"<content><userName><![CDATA[{USER}]]></userName>"
        f"<password><![CDATA[{pw_hash}]]></password></content></request>"
    )
    resp2 = _http_post("/doLogin", req2.encode("utf-8"), cookie=f"sessionId={sid}")
    if "<status>success</status>" not in resp2:
        err = re.search(r"<errorCode>(.*?)</errorCode>", resp2)
        raise NvrError(f"Login rad etildi (errorCode={err.group(1) if err else '?'})")
    return token, sid


def _fetch_day(token: str, sid: str, date_str: str, work_numbers: list[str]) -> dict:
    """Bitta kun uchun barcha xodimlarning Record (punch) ro'yxatini qaytaradi:
    {work_no: ["H:M", ...]}."""
    import xml.etree.ElementTree as ET

    items = "".join(f"<item>{wn}</item>" for wn in work_numbers)
    q = (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<request version="1.0"   systemType="NVMS-9000" clientType="WEB">'
        f"<token>{token}</token><condition>"
        f"<startTime>{date_str} 00:00:00</startTime>"
        f"<endTime>{date_str} 23:59:59</endTime>"
        f"<detailType>byDay</detailType><idParam>{items}</idParam>"
        "</condition></request>"
    )
    resp = _http_post(
        "/queryAttendanceStatisticDetail", q.encode("utf-8"), cookie=f"sessionId={sid}"
    )
    if "<status>success</status>" not in resp:
        raise NvrError(f"queryAttendanceStatisticDetail rad etildi: {resp[:300]}")

    out = {}
    root = ET.fromstring(resp)
    for emp in root.findall("./content/AttendanceDetail/item"):
        wn_el = emp.find("idParam")
        if wn_el is None or not (wn_el.text or "").strip():
            continue
        wn = wn_el.text.strip()
        record_times = [
            (rec.text or "").strip()
            for rec in emp.findall("./detail/item/Record/item")
            if (rec.text or "").strip()
        ]
        out[wn] = record_times
    return out


def _work_numbers_from_users() -> list[str]:
    import openpyxl

    wb = openpyxl.load_workbook(USERS_FILE, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        return []
    hdr = [str(c or "").strip().lower() for c in rows[0]]
    if "faceid" not in hdr:
        return []
    fi = hdr.index("faceid")
    out = []
    for row in rows[1:]:
        v = str(row[fi] or "").strip()
        if v.endswith(".0"):
            v = v[:-2]
        if v.isdigit():
            out.append(v)
    return sorted(set(out), key=int)


def refresh(date_str: str | None = None) -> dict:
    """NVR'ga kirib, bugungi (yoki berilgan kun) hodisalarini tortib,
    _live_cache.json ga yozadi. Qaytaradi: {"ok", "count", "employees", "error"}."""
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    work_numbers = _work_numbers_from_users()
    if not work_numbers:
        return {"ok": False, "error": "users.xlsx da faceid ustuni topilmadi"}

    try:
        token, sid = login()
        day_records = _fetch_day(token, sid, date_str, work_numbers)
    except NvrError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    rows = []
    for wn, times in day_records.items():
        if not times:
            continue
        nxt = ENTER
        for t in times:
            try:
                hh, mm = t.split(":")[:2]
                dt = datetime.strptime(date_str, "%Y-%m-%d").replace(
                    hour=int(hh), minute=int(mm)
                )
            except Exception:
                continue
            rows.append({"work_no": wn, "dt": dt.isoformat(), "type": nxt})
            nxt = EXIT if nxt == ENTER else ENTER

    REPORTS_DIR.mkdir(exist_ok=True)
    cache = {}
    if LIVE_CACHE_FILE.exists():
        try:
            cache = json.loads(LIVE_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    cache[date_str] = rows
    LIVE_CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    employees_with_data = len({r["work_no"] for r in rows})
    return {
        "ok": True,
        "date": date_str,
        "employees": employees_with_data,
        "total_queried": len(work_numbers),
        "events": len(rows),
    }


if __name__ == "__main__":
    import sys

    d = sys.argv[1] if len(sys.argv) > 1 else None
    print(refresh(d))
