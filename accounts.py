"""
accounts.py — mobil ilova uchun hisob va token boshqaruvi.

Xavfsiz parol hash (pbkdf2, stdlib — qo'shimcha kutubxona kerak emas).
Hisoblar accounts.json da, tokenlar tokens.json da.

Hisob = jshshir (card) bilan kiradi. Rol employee_map.json dan.
"""

import os
import json
import time
import hmac
import hashlib
import secrets
from pathlib import Path

BASE_DIR = Path(".")
ACCOUNTS_FILE = BASE_DIR / "accounts.json"
TOKENS_FILE = BASE_DIR / "tokens.json"

TOKEN_TTL = 30 * 24 * 3600  # 30 kun
PBKDF2_ITERS = 200_000


# ─────────────────────────── JSON YORDAMCHILARI ───────────────────────────

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


# ─────────────────────────── PAROL HASH ───────────────────────────

def hash_password(password: str, salt: str = None):
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                             bytes.fromhex(salt), PBKDF2_ITERS)
    return salt, dk.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, h = hash_password(password, salt)
    return hmac.compare_digest(h, expected_hash)


# ─────────────────────────── HISOBLAR ───────────────────────────

def load_accounts() -> dict:
    """{login(jshshir): {name, role, salt, hash, must_change, active}}"""
    return _load(ACCOUNTS_FILE, {})


def save_accounts(data: dict):
    _save(ACCOUNTS_FILE, data)


def get_account(login: str):
    return load_accounts().get(str(login).strip())


def create_account(login: str, password: str, name: str = "", role: str = "employee",
                   must_change: bool = True, overwrite: bool = False) -> bool:
    """Yangi hisob yaratadi. overwrite=False bo'lsa mavjudini o'zgartirmaydi."""
    login = str(login).strip()
    accounts = load_accounts()
    if login in accounts and not overwrite:
        return False
    salt, h = hash_password(password)
    accounts[login] = {
        "name": name,
        "role": role or "employee",
        "salt": salt,
        "hash": h,
        "must_change": bool(must_change),
        "active": True,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_accounts(accounts)
    return True


def set_password(login: str, new_password: str, clear_must_change: bool = True) -> bool:
    login = str(login).strip()
    accounts = load_accounts()
    if login not in accounts:
        return False
    salt, h = hash_password(new_password)
    accounts[login]["salt"] = salt
    accounts[login]["hash"] = h
    if clear_must_change:
        accounts[login]["must_change"] = False
    save_accounts(accounts)
    return True


def set_role(login: str, role: str) -> bool:
    login = str(login).strip()
    accounts = load_accounts()
    if login not in accounts:
        return False
    accounts[login]["role"] = role
    save_accounts(accounts)
    return True


def set_active(login: str, active: bool) -> bool:
    login = str(login).strip()
    accounts = load_accounts()
    if login not in accounts:
        return False
    accounts[login]["active"] = bool(active)
    save_accounts(accounts)
    return True


def delete_account(login: str) -> bool:
    """Hisobни butunlay o'chiradi va barcha sessiyaларини bekor qiladi."""
    login = str(login).strip()
    accounts = load_accounts()
    if login not in accounts:
        return False
    accounts.pop(login, None)
    save_accounts(accounts)
    try:
        revoke_all_for_login(login)
    except Exception:
        pass
    return True


def authenticate(login: str, password: str):
    """Login+parolni tekshiradi. To'g'ri bo'lsa hisob dict, aks holda None."""
    acc = get_account(login)
    if not acc or not acc.get("active", True):
        return None
    if verify_password(password, acc.get("salt", ""), acc.get("hash", "")):
        return acc
    return None


# ─────────────────────────── TOKENLAR ───────────────────────────

def _load_tokens() -> dict:
    return _load(TOKENS_FILE, {})


def _save_tokens(data: dict):
    _save(TOKENS_FILE, data)


def issue_token(login: str) -> str:
    """Yangi token yaratadi va saqlaydi."""
    tokens = _load_tokens()
    # eskirganlarini tozalaymiz
    now = time.time()
    tokens = {t: v for t, v in tokens.items() if v.get("expires", 0) > now}
    token = secrets.token_urlsafe(32)
    tokens[token] = {"login": str(login).strip(), "expires": now + TOKEN_TTL}
    _save_tokens(tokens)
    return token


def check_token(token: str):
    """Token to'g'ri bo'lsa login qaytaradi, aks holda None."""
    if not token:
        return None
    tokens = _load_tokens()
    info = tokens.get(token)
    if not info:
        return None
    if info.get("expires", 0) < time.time():
        return None
    return info.get("login")


def revoke_token(token: str):
    tokens = _load_tokens()
    if token in tokens:
        del tokens[token]
        _save_tokens(tokens)


def revoke_all_for_login(login: str, except_token: str = None):
    """Xodimning barcha tokenlarini bekor qiladi (parol o'zgarganda).
    except_token — shu tokenni qoldiradi (joriy sessiya)."""
    login = str(login).strip()
    tokens = _load_tokens()
    new = {t: v for t, v in tokens.items()
           if v.get("login") != login or t == except_token}
    if len(new) != len(tokens):
        _save_tokens(new)


if __name__ == "__main__":
    # tez test
    create_account("99999999999999", "1234", "TEST XODIM", "employee", overwrite=True)
    acc = authenticate("99999999999999", "1234")
    print("Auth OK:", bool(acc), acc.get("name") if acc else None)
    print("Auth wrong:", authenticate("99999999999999", "0000"))
    tok = issue_token("99999999999999")
    print("Token:", tok[:20], "... -> login:", check_token(tok))
