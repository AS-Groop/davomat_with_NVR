# -*- coding: utf-8 -*-
"""
explanation_pdf.py — rasmiy "Tushuntirish xati" PDF generatori.

Har bir tushuntirish (kechikish / kelmaslik / erta chiqish) uchun
xodimning FIO, guruh, lavozim, sana va IMZOSI bilan A4 PDF yasaydi.
PDF'lar explanations/pdf/ papkasida to'planadi.

Guruh/lavozim employee_departments.json dan olinadi
(uni build_departments.py users.xlsx dan yig'adi).

reportlab talab qilinadi:  pip install reportlab
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(".")
PDF_DIR = BASE_DIR / "explanations" / "pdf"
DEPT_FILE = BASE_DIR / "employee_departments.json"

UZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun",
             "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"]

# Times New Roman'da ba'zi modifikator apostroflar (ʻ U+02BB, ʼ U+02BC) yo'q —
# ularni Times qo'llaydigan jingalak tirnoqlarga almashtiramiz.
_APOS_MAP = {
    "ʻ": "‘",  # ʻ (o'/g' turned comma) -> ' (left single quote)
    "ʼ": "’",  # ʼ (tutuq belgisi)      -> ' (right single quote)
    "ʽ": "’",
    "`": "‘",  # ` -> '
}


def _norm(s):
    """Matndagi maxsus apostroflarni Times o'qiy oladigan belgilarga o'giradi."""
    return "".join(_APOS_MAP.get(ch, ch) for ch in str(s or ""))


# ─────────────────────── KIRILL → LOTIN ───────────────────────
# Rasmiy hujjatlar faqat lotin alifbosida bo'lishi kerak. Xodim telefonida
# kirillcha yozsa ham, hujjatga lotinda tushadi.

_CYR_MULTI = [
    # Avval ko'p harfli birikmalar (tartib muhim)
    ("Ў", "O‘"), ("ў", "o‘"), ("Ғ", "G‘"), ("ғ", "g‘"),
    ("Ҳ", "H"), ("ҳ", "h"), ("Қ", "Q"), ("қ", "q"),
    ("Ю", "Yu"), ("ю", "yu"), ("Я", "Ya"), ("я", "ya"),
    ("Ё", "Yo"), ("ё", "yo"), ("Ж", "J"), ("ж", "j"),
    ("Ч", "Ch"), ("ч", "ch"), ("Ш", "Sh"), ("ш", "sh"),
    ("Ц", "S"), ("ц", "s"), ("Щ", "Sh"), ("щ", "sh"),
]
_CYR_ONE = {
    "А": "A", "а": "a", "Б": "B", "б": "b", "В": "V", "в": "v",
    "Г": "G", "г": "g", "Д": "D", "д": "d", "Е": "E", "е": "e",
    "З": "Z", "з": "z", "И": "I", "и": "i", "Й": "Y", "й": "y",
    "К": "K", "к": "k", "Л": "L", "л": "l", "М": "M", "м": "m",
    "Н": "N", "н": "n", "О": "O", "о": "o", "П": "P", "п": "p",
    "Р": "R", "р": "r", "С": "S", "с": "s", "Т": "T", "т": "t",
    "У": "U", "у": "u", "Ф": "F", "ф": "f", "Х": "X", "х": "x",
    "Ъ": "’", "ъ": "’", "Ь": "", "ь": "",
    "Ы": "I", "ы": "i", "Э": "E", "э": "e",
}


def has_cyrillic(s):
    return any("Ѐ" <= ch <= "ӿ" for ch in str(s or ""))


def to_latin(s):
    """Kirillcha matnni lotinga o'giradi. Lotin matn o'zgarishsiz qaytadi."""
    s = str(s or "")
    if not has_cyrillic(s):
        return s
    for a, b in _CYR_MULTI:
        s = s.replace(a, b)
    out = []
    for ch in s:
        out.append(_CYR_ONE.get(ch, ch))
    res = "".join(out)
    # "Ye" qoidasi: so'z boshida va unlidan keyin "е" -> "ye"
    res = re.sub(r"(?<![A-Za-zʼ‘’])E(?=[a-z])", "Ye", res)
    res = re.sub(r"(?<=[aeiouAEIOU])e", "ye", res)
    return res

# ─────────────────────────── SHRIFT ───────────────────────────

_FONT_CANDIDATES = [
    # (oddiy, qalin) — Times New Roman ustuvor
    (r"C:\Windows\Fonts\times.ttf", r"C:\Windows\Fonts\timesbd.ttf"),        # Windows: Times New Roman
    ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"),        # Linux: Times-metrik
    ("/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
     "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
    ("/Library/Fonts/Times New Roman.ttf", "/Library/Fonts/Times New Roman Bold.ttf"),
]

_FONT_OK = None   # (regular_name, bold_name) yoki False


def _ensure_fonts():
    global _FONT_OK
    if _FONT_OK is not None:
        return _FONT_OK
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except Exception as e:
        print(f"[EXPL_PDF] reportlab yo'q: {e}")
        _FONT_OK = False
        return False
    for reg, bold in _FONT_CANDIDATES:
        if os.path.exists(reg):
            try:
                pdfmetrics.registerFont(TTFont("ExplReg", reg))
                b = bold if os.path.exists(bold) else reg
                pdfmetrics.registerFont(TTFont("ExplBold", b))
                _FONT_OK = ("ExplReg", "ExplBold")
                return _FONT_OK
            except Exception:
                continue
    print("[EXPL_PDF] mos shrift topilmadi (DejaVu/Arial/Times)")
    _FONT_OK = False
    return False


# ─────────────────────────── YORDAMCHILAR ───────────────────────────

def short_name(fio):
    """'ALIYEV VALI KARIMOVICH' -> 'V.Aliyev'."""
    parts = str(fio or "").split()
    if not parts:
        return ""
    fam = parts[0]
    ism = parts[1] if len(parts) > 1 else ""
    fam_fmt = fam[:1].upper() + fam[1:].lower()
    low = ism.lower()
    if low[:2] in ("sh", "ch", "ng"):
        ini = ism[:2].capitalize()
    elif ism:
        ini = ism[:1].upper()
    else:
        ini = ""
    return f"{ini}.{fam_fmt}" if ini else fam_fmt


def _add_i(s):
    """So'z oxiriga -i / -si egalik qo'shimchasi."""
    s = s.rstrip()
    if not s:
        return s
    last = s[-1].lower()
    if last in "iı":
        return s                        # allaqachon -i bilan tugagan (masalan 'rahbari')
    if last in "aeou":
        return s + "si"
    return s + "i"


def _possessive(pos):
    """Lavozimga egalik qo'shimchasi. Qavs bo'lsa — qavsdan oldingi (bosh) so'zga qo'shadi.
    'Bosh inspektor' -> 'bosh inspektori'
    'Guruh rahbari'  -> 'guruh rahbari'
    'Bosh mutaxassis (yordamchi buxgalter)' -> 'bosh mutaxassisi (yordamchi buxgalter)'"""
    p = str(pos or "").strip().lower()
    if not p:
        return p
    idx = p.find("(")
    if idx > 0:
        head = p[:idx].rstrip()
        rest = p[idx:]
        return (_add_i(head) + " " + rest).strip()
    return _add_i(p)


def dept_info(card):
    """employee_departments.json dan {department, position} (card bo'yicha)."""
    try:
        data = json.loads(DEPT_FILE.read_text(encoding="utf-8"))
        rec = data.get(str(card)) or {}
        return rec.get("department", "") or "", rec.get("position", "") or ""
    except Exception:
        return "", ""


def from_line(card, fio):
    """'Malakani baholash guruhi bosh mutaxassisi V.Aliyevdan'."""
    dept, pos = dept_info(card)
    sn = short_name(fio)
    parts = [p for p in [dept.strip(), _possessive(pos)] if p]
    lead = " ".join(parts)
    return (lead + " " + sn + "dan").strip() if lead else (sn + "dan")


def body_text(kind, day, month_name, year, time_str, minutes, reason):
    # Xodim kirill alifbosida yozgan bo'lsa — lotinga o'giramiz (rasmiy hujjat)
    reason = to_latin(reason)
    if kind == "late":
        return (f"Men {year}-yil {day}-{month_name} kuni ishga soat {time_str} da "
                f"{minutes} daqiqa kechikib keldim, bunga sabab {reason}.")
    if kind == "absent":
        return (f"Men {year}-yil {day}-{month_name} kuni ish joyiga kelmadim, "
                f"bunga sabab {reason}.")
    if kind == "exit":
        return (f"Men {year}-yil {day}-{month_name} kuni ish vaqti tugamasdan, "
                f"soat {time_str} da ish joyini tark etdim, bunga sabab {reason}.")
    return (f"Men {year}-yil {day}-{month_name} kuni, bunga sabab {reason}.")


def _fmt_date_parts(date_iso):
    """'2026-07-21' -> (day='21', month_name='iyul', year='2026', 'DD.MM.YYYY-yil')."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(date_iso or ""))
    if not m:
        d = datetime.now()
        return str(d.day), UZ_MONTHS[d.month - 1], str(d.year), d.strftime("%d.%m.%Y-yil")
    y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return str(da), UZ_MONTHS[mo - 1], str(y), f"{da:02d}.{mo:02d}.{y}-yil"


def _late_minutes(first_entry, work_start):
    def _mins(t):
        mm = re.match(r"^(\d{1,2}):(\d{2})", str(t or ""))
        return int(mm.group(1)) * 60 + int(mm.group(2)) if mm else None
    a, b = _mins(first_entry), _mins(work_start or "09:00")
    if a is None or b is None:
        return None
    return a - b if a > b else None


# ─────────────────────────── PDF QURISH ───────────────────────────

def _wrap(text, font, size, maxw, pdfmetrics):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(t, font, size) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _render_letter(out_path, fio, card, title, body, sign_date, signature_path=None):
    """Rasmiy xat (tushuntirish/ariza) — bir xil shakl: manzil, kimdan, sarlavha, matn, imzo."""
    fonts = _ensure_fonts()
    if not fonts:
        return None
    REG, BOLD = fonts
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics

    W, H = A4
    LM, RM = 70, 70
    CW = W - LM - RM
    CM = 72 / 2.54
    FS = 14
    LEAD = 17

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_path), pagesize=A4)

    # ── Kimga (manzil) — 8.5 sm dan chapga tekislangan ──
    ax = 8.5 * CM
    bw = W - RM - ax
    try:
        import tashkilot
        addr = tashkilot.get()["explanation_addressee"]
    except Exception:
        addr = "Tashkilot rahbariga"
    y = H - 70
    c.setFont(REG, FS)
    for ln in _wrap(_norm(addr), REG, FS, bw, pdfmetrics):
        c.drawString(ax, y, ln)
        y -= LEAD
    # ── Kimdan ──
    y -= 6
    for ln in _wrap(_norm(from_line(card, fio)), REG, FS, bw, pdfmetrics):
        c.drawString(ax, y, ln)
        y -= LEAD

    # ── Sarlavha (chiziqsiz) ──
    y -= 40
    c.setFont(BOLD, FS)
    c.drawCentredString(W / 2, y, _norm(title))

    # ── Matn (ikki tomonlama tekislash, odinarniy) ──
    y -= 32
    c.setFont(REG, FS)
    blines = _wrap(_norm(body), REG, FS, CW, pdfmetrics)
    for i, ln in enumerate(blines):
        words = ln.split()
        if i != len(blines) - 1 and len(words) > 1:
            tw2 = sum(pdfmetrics.stringWidth(w, REG, FS) for w in words)
            gap = (CW - tw2) / (len(words) - 1)
            cx = LM
            for w in words:
                c.drawString(cx, y, w)
                cx += pdfmetrics.stringWidth(w, REG, FS) + gap
        else:
            c.drawString(LM, y, ln)
        y -= LEAD

    # ── Pastki qator: sana | imzo | qisqa ism ──
    y -= 50
    c.setFont(REG, FS)
    c.drawString(LM, y, sign_date)
    sname = _norm(short_name(fio))
    nw = pdfmetrics.stringWidth(sname, BOLD, FS)
    c.setFont(BOLD, FS)
    c.drawString(W - RM - nw, y, sname)
    date_right = LM + pdfmetrics.stringWidth(sign_date, REG, FS)
    name_left = W - RM - nw
    mid = (date_right + name_left) / 2
    if signature_path and Path(signature_path).exists():
        try:
            img = ImageReader(str(signature_path))
            iw, ih = img.getSize()
            disp_w = 110.0
            disp_h = disp_w * ih / iw
            if disp_h > 46:
                disp_h = 46.0
                disp_w = disp_h * iw / ih
            c.drawImage(img, mid - disp_w / 2, y - 6, width=disp_w, height=disp_h,
                        mask="auto", preserveAspectRatio=True)
        except Exception:
            c.line(mid - 55, y - 2, mid + 55, y - 2)
    else:
        c.line(mid - 55, y - 2, mid + 55, y - 2)

    c.showPage()
    c.save()
    return str(out_path)


def build_pdf(out_path, fio, card, kind, date_iso, time_str, reason,
              signature_path=None, work_start=None):
    """Bitta tushuntirish xati PDF yasaydi."""
    day, month_name, year, sign_date = _fmt_date_parts(date_iso)
    minutes = _late_minutes(time_str, work_start) if kind == "late" else None
    if kind == "late" and minutes is None:
        minutes = ""
    body = body_text(kind, day, month_name, year, time_str, minutes, reason)
    return _render_letter(out_path, fio, card, "Tushuntirish xati", body, sign_date, signature_path)


# ─────────────────────────── ARIZA ───────────────────────────

ARIZA_PDF_DIR = BASE_DIR / "arizalar" / "pdf"


def _fmt_date_uz(iso):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    if not m:
        return str(iso or "")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{d}-{UZ_MONTHS[mo - 1]} {y}-yil"


def ariza_body_text(atype, date_from, date_to, text):
    df = _fmt_date_uz(date_from)
    dt = _fmt_date_uz(date_to) if (date_to and date_to != date_from) else ""
    rng = f"{df} dan {dt} gacha" if dt else df
    if atype == "tatil":
        s = f"Meni {rng} navbatdagi mehnat taʼtiliga chiqishimga ruxsat berishingizni soʻrayman."
    elif atype == "ruxsat":
        s = f"Meni {rng} ish joyida boʻlmasligimga ruxsat berishingizni soʻrayman."
    elif atype == "moddiy":
        s = "Menga moddiy yordam koʻrsatishingizni soʻrayman."
    else:
        s = ""
    text = to_latin(str(text or "").strip())   # kirillcha yozilsa — lotinga
    if text:
        s = (s + " " + text).strip() if s else text
    return s


def ariza_pdf_path_for(aid, fio):
    safe = re.sub(r"[^\w\-]+", "_", str(fio or ""), flags=re.UNICODE)[:50] or "xodim"
    ARIZA_PDF_DIR.mkdir(parents=True, exist_ok=True)
    return ARIZA_PDF_DIR / f"{aid}_{safe}.pdf"


def build_ariza_pdf(out_path, fio, card, atype, created_date, date_from, date_to,
                    text, signature_path=None):
    """Ariza PDF (tushuntirish xati bilan bir xil shaklda, sarlavha — 'Ariza')."""
    _, _, _, sign_date = _fmt_date_parts(created_date)
    body = ariza_body_text(atype, date_from, date_to, text)
    return _render_letter(out_path, fio, card, "Ariza", body, sign_date, signature_path)


def pdf_path_for(card, fio, date_iso, kind):
    """Barqaror fayl nomi — bir kun+tur uchun bitta fayl (qayta yuborilsa ustiga yoziladi)."""
    safe = re.sub(r"[^\w\-]+", "_", str(fio or ""), flags=re.UNICODE)[:60] or "xodim"
    kind_txt = {"late": "kechikish", "absent": "kelmaslik", "exit": "erta_chiqish"}.get(kind, kind)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    return PDF_DIR / f"{date_iso}_{safe}_{kind_txt}.pdf"
