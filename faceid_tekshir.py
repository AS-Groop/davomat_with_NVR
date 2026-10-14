# -*- coding: utf-8 -*-
"""FaceID ulanishini tekshirish (hech narsani o'zgartirmaydi).

  python faceid_tekshir.py            — qurilmalar bilan aloqa + bugungi so'nggi o'tishlar
  python faceid_tekshir.py <JSHSHIR>  — shu xodimning bugungi kirish/chiqishlari
"""
import os
import sys
from datetime import datetime, timedelta

os.chdir(os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import biocontrol_api as api
import faceid_devices as fd

today = datetime.now().strftime("%Y-%m-%d")
print(f"Manba (FACEID_SOURCE): {api.SOURCE}  →  {api.API_URL}\n")

if len(sys.argv) > 1:
    card = sys.argv[1]
    print(f"Xodim {card} (qurilmadagi raqami: {fd.device_id(card)}) — bugun:")
    for e in api.get_events(card, today, today):
        print(f"   {e['dt']:%H:%M:%S}  {'KIRISH' if e['type'] == api.LABEL_ENTER else 'CHIQISH'}")
    input("\nEnter — chiqish")
    sys.exit()

if api.SOURCE != "devices":
    print("Qurilma rejimi yoqilmagan. .env da FACEID_SOURCE=devices qiling.")
    input("\nEnter — chiqish")
    sys.exit()

devs = fd.devices()
if not devs:
    print("faceid_devices.json topilmadi yoki bo'sh (namuna: faceid_devices_namuna.json).")
for dev in devs:
    nm = dev.dev.get("name") or dev.dev.get("host")
    print(f"■ {nm}  ({dev.dev.get('type')} · {dev.dev.get('host')})")
    try:
        print(f"   ✅ Ulandi: {dev.info()}")
    except Exception as e:
        print(f"   ❌ Ulanib bo'lmadi: {type(e).__name__}: {e}")
        continue
    try:
        a = datetime.strptime(today, "%Y-%m-%d")
        rows = dev.events(a, a + timedelta(hours=23, minutes=59, seconds=59))
        print(f"   Bugun {len(rows)} ta o'tish. So'nggi 15 tasi:")
        for r in sorted(rows, key=lambda x: x["dt"])[-15:]:
            d = dev.direction(r) or "?"
            print(f"     {r['dt']:%H:%M:%S}  raqam={r['emp']:<12} {r.get('name', ''):<25} {d}")
    except Exception as e:
        print(f"   ❌ Hodisalarni o'qib bo'lmadi: {type(e).__name__}: {e}")
print("\nRaqamlar users.xlsx dagi 'faceid' (yoki JSHSHIR) bilan mos kelishi kerak.")
input("\nEnter — chiqish")
