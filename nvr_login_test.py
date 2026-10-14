# -*- coding: utf-8 -*-
"""nvr_login_test.py — NVR login diagnostikasi.

Bu faylni O'ZINGIZNING kompyuteringizda, oddiy terminalda ishga tushiring:
    python nvr_login_test.py

Konsolda chiqqan BARCHA matnni nusxalab, Claude'ga yuboring.

Nima qiladi: NVR veb-klienti ishlatadigan xuddi shu login protokolini
(challenge-response: /reqLogin -> parolni nonce bilan xeshlash -> /doLogin)
takrorlaydi va har bir qadam natijasini chop etadi. Hech narsani
o'zgartirmaydi, faqat login urinadi.

Sozlamalar (IP, login, parol) kodda EMAS — .env dan o'qiladi
(NVR_HOST, NVR_USER, NVR_PASSWORD), xuddi nvr_live.py dagidek.
"""
from __future__ import annotations

import hashlib
import os
import re
import socket

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

IP = os.getenv("NVR_HOST", "")
PORT = 80
USER = os.getenv("NVR_USER", "admin")
PASSWORD = os.getenv("NVR_PASSWORD", "")


def http_post(path: str, body: bytes, cookie: str | None = None) -> tuple[int, dict, str]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    s.settimeout(10)
    s.connect((IP, PORT))
    local_addr = s.getsockname()
    cookie_line = f"Cookie: {cookie}\r\n" if cookie else ""
    req = (
        f"POST {path} HTTP/1.1\r\n"
        f"Host: {IP}\r\n"
        f"Connection: keep-alive\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Accept: application/xml, text/xml, */*; q=0.01\r\n"
        f"X-Requested-With: XMLHttpRequest\r\n"
        f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36\r\n"
        f"Content-Type: application/x-www-form-urlencoded; charset=UTF-8\r\n"
        f"Origin: http://{IP}\r\n"
        f"Referer: http://{IP}/\r\n"
        f"{cookie_line}"
        f"Accept-Encoding: identity\r\n"
        f"Accept-Language: ru,en-US;q=0.9,en;q=0.8,uz;q=0.7\r\n"
        f"\r\n"
    ).encode("ascii") + body
    print(f"  [local addr: {local_addr}]")
    s.sendall(req)
    chunks = []
    while True:
        try:
            c = s.recv(65536)
        except Exception:
            break
        if not c:
            break
        chunks.append(c)
    s.close()
    raw = b"".join(chunks)
    head, _, body_out = raw.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0].decode("ascii", "replace")
    status_code = int(status_line.split()[1]) if len(status_line.split()) > 1 else 0
    return status_code, {}, body_out.decode("utf-8", "replace")


def main():
    if not IP or not PASSWORD:
        print("XATO: .env da NVR_HOST yoki NVR_PASSWORD yo'q.")
        return
    print("=" * 60)
    print(f"1) /reqLogin ga ulanmoqda ({IP})...")
    req1 = (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<request version="1.0"  systemType="NVMS-9000" clientType="WEB">'
        "<token>null</token></request>"
    )
    status, _, resp1 = http_post("/reqLogin", req1.encode("utf-8"))
    print(f"   HTTP status: {status}")
    print(f"   Javob:\n{resp1}\n")

    nonce_m = re.search(r"<nonce>(.*?)</nonce>", resp1)
    token_m = re.search(r"<token>(.*?)</token>", resp1)
    sid_m = re.search(r"<sessionId>(.*?)</sessionId>", resp1)
    if not nonce_m or not token_m or not sid_m:
        print("XATO: reqLogin javobida nonce/token/sessionId topilmadi. To'xtatildi.")
        return
    nonce, token = nonce_m.group(1), token_m.group(1)
    sid = sid_m.group(1).strip("{}")
    print(f"   nonce = {nonce}")
    print(f"   token = {token}")
    print(f"   sessionId = {sid}\n")

    md5_pw = hashlib.md5(PASSWORD.encode("utf-8")).hexdigest().upper()
    sha1_final = hashlib.sha1((md5_pw + nonce).encode("utf-8")).hexdigest().upper()
    print("2) Parol xeshi hisoblanmoqda...")
    print(f"   MD5(parol).upper()      = {md5_pw}")
    print(f"   SHA1(MD5+nonce).upper() = {sha1_final}\n")

    req2 = (
        '<?xml version="1.0" encoding="utf-8" ?>'
        f'<request version="1.0"   systemType="NVMS-9000" clientType="WEB">'
        f"<token>{token}</token>"
        f"<content><userName><![CDATA[{USER}]]></userName>"
        f"<password><![CDATA[{sha1_final}]]></password></content></request>"
    )
    print("3) /doLogin yuborilmoqda (Cookie: sessionId=... bilan)...")
    status, _, resp2 = http_post("/doLogin", req2.encode("utf-8"), cookie=f"sessionId={sid}")
    print(f"   HTTP status: {status}")
    print(f"   Javob:\n{resp2}\n")

    if "<status>success</status>" in resp2:
        print("NATIJA: ✅ LOGIN MUVAFFAQIYATLI!")
    else:
        print("NATIJA: ❌ Login rad etildi (yuqoridagi javobni to'liq yuboring).")
    print("=" * 60)


if __name__ == "__main__":
    main()
