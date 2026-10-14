"""
start_all.py — Davomat tizimini ishga tushiradi.

⚠️ CLOUDFLARED BU YERDA YO'Q — u ALOHIDA oynada ishlaydi (start_tunnel.bat).
   Bu skriptni qayta ishga tushirsangiz, tunnel tegilmaydi va LINK O'ZGARMAYDI.

Bosh boshqaruvchi — mobile_api.py. U bitta jarayonda uchta qismni ko'taradi:
  • Mobil ilova + API           — port 8090
  • Dashboard (katta ekran)     — port 8080
  • Jonli kirdi/chiqdi worker   — fon oqimida (FaceID ma'lumotini o'qiydi)
"""
import subprocess
import sys

print("🏢 Bo'lim/lavozimlar users.xlsx dan yangilanmoqda...")
try:
    subprocess.run([sys.executable, "build_departments.py"], timeout=60)
except Exception as e:
    print(f"   (o'tkazib yuborildi: {e})")

print("🚀 Tizim ishga tushmoqda (mobile_api.py)...")
try:
    proc = subprocess.Popen([sys.executable, "mobile_api.py"])
    proc.wait()
except KeyboardInterrupt:
    print("\n🛑 Tizim to'xtatilmoqda...")
    try:
        proc.terminate()
    except Exception:
        pass
    sys.exit(0)
