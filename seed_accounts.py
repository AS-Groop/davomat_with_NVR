"""
seed_accounts.py — employee_map.json dan mobil hisoblar yaratadi.

Har xodimga:
  • login = jshshir (card)
  • boshlang'ich parol = jshshirning oxirgi 6 raqami (xodim keyin o'zgartiradi)
  • rol = employee_map dagi role (employee/hr/director)

Ishlatish:
    python seed_accounts.py

Natija: accounts.json + parollar ro'yxati (xodimlarга tarqatish uchun).
Qayta ishga tushirsangiz — MAVJUD hisoblar/parollar SAQLANADI (buzilmaydi).
"""

import json
from pathlib import Path

import accounts

MAP_FILE = Path("employee_map.json")


def initial_password(card: str) -> str:
    """Boshlang'ich parol — jshshirning oxirgi 6 raqami."""
    digits = "".join(ch for ch in str(card) if ch.isdigit())
    return digits[-6:] if len(digits) >= 6 else (digits or "123456")


def main():
    if not MAP_FILE.exists():
        print("❌ employee_map.json topilmadi. Avval build_employee_map.py ni ishga tushiring.")
        return

    emp_map = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    existing = accounts.load_accounts()

    created, skipped, no_card = 0, 0, 0
    new_creds = []  # tarqatish uchun (faqat yangi yaratilganlar)

    for eid, info in emp_map.items():
        card = "".join(ch for ch in str(info.get("card", "")) if ch.isdigit())
        name = info.get("_name", "") or ""
        role = (info.get("role") or "employee").lower()
        if not card:
            no_card += 1
            continue
        if card in existing:
            skipped += 1
            continue
        pw = initial_password(card)
        if accounts.create_account(card, pw, name=name, role=role, must_change=True):
            created += 1
            new_creds.append((name, card, pw, role))

    print("=" * 55)
    print(f"✅ Hisoblar tayyor.")
    print(f"   Yangi yaratildi: {created}")
    print(f"   Avval mavjud (o'zgarmadi): {skipped}")
    print(f"   Jshshir yo'q (o'tkazildi): {no_card}")

    if new_creds:
        print("\n📋 YANGI HISOBLAR (xodimlarга tarqating — parolni almashtirsin):")
        print(f"{'ISM':35} {'LOGIN (jshshir)':16} {'PAROL':8} ROL")
        print("-" * 70)
        for name, card, pw, role in new_creds:
            print(f"{name[:34]:35} {card:16} {pw:8} {role}")
        # faylga ham yozamiz
        Path("new_accounts.txt").write_text(
            "ISM | LOGIN | PAROL | ROL\n" +
            "\n".join(f"{n} | {c} | {p} | {r}" for n, c, p, r in new_creds),
            encoding="utf-8",
        )
        print("\n(Ro'yxat new_accounts.txt ga ham yozildi.)")
    print("\n⚠️ Boshlang'ich parol = jshshirning oxirgi 6 raqami.")
    print("   Xodim birinchi kirishда parolni o'zgartirishi kerak.")


if __name__ == "__main__":
    main()
