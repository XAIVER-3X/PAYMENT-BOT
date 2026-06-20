# coding: utf-8
# author: @algoanhaf

from io import BytesIO
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf",          "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/calibri.ttf",        "C:/Windows/Fonts/calibrib.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]

FONT, FONT_BOLD = None, None
for _r, _b in _FONT_CANDIDATES:
    if __import__("os").path.exists(_r) and __import__("os").path.exists(_b):
        FONT, FONT_BOLD = _r, _b
        break

_ASCII_MAP = {
    "£": "GBP ", "€": "EUR ", "$": "$", "¥": "JPY ",
    "—": "-", "–": "-", "•": "*", "·": "*",
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
}


def _s(s):
    s = str(s)
    for k, v in _ASCII_MAP.items():
        s = s.replace(k, v)
    return s.encode("ascii", "ignore").decode("ascii")


def _mask_username(u):
    u = str(u)
    prefix = '@' if u.startswith('@') else ''
    name = u[len(prefix):]
    if len(name) <= 6:
        return prefix + name
    show = max(4, len(name) // 4)
    return prefix + name[:show] + '****' + name[-show:]


def _font(size, bold=False):
    path = FONT_BOLD if bold else FONT
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate_invoice_image(
    invoice_number, customer_name, username, user_id, plan_label,
    duration_days, amount, currency, payment_method,
    voucher_serial, transaction_id, timestamp=None,
):
    W, H = 640, 780
    BG       = (15, 15, 25)
    CARD     = (24, 24, 38)
    ACCENT   = (130, 80, 255)
    GREEN    = (46, 213, 115)
    WHITE    = (255, 255, 255)
    GRAY     = (140, 140, 160)
    DIVIDER  = (40, 40, 58)

    if timestamp is None:
        timestamp = datetime.now().strftime("%d %b %Y  %H:%M")

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # top accent bar
    draw.rectangle([(0, 0), (W, 6)], fill=ACCENT)

    # header
    draw.rectangle([(0, 6), (W, 100)], fill=CARD)
    draw.text((36, 22), "PAYMENT RECEIPT", font=_font(22, bold=True), fill=WHITE)
    draw.text((36, 56), _s(f"#{invoice_number}"), font=_font(13), fill=GRAY)

    # green circle tick
    cx, cy, r = W - 60, 54, 26
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=GREEN)
    draw.text((cx - 9, cy - 12), "✓", font=_font(22, bold=True), fill=(10, 10, 10))

    # card body
    pad = 36
    card_top = 118
    draw.rounded_rectangle([(20, card_top), (W - 20, H - 20)], radius=18, fill=CARD)

    y = card_top + 32

    # customer name big
    draw.text((pad + 4, y), _s(customer_name), font=_font(26, bold=True), fill=WHITE)
    y += 36
    draw.text((pad + 4, y), _s(_mask_username(username)), font=_font(14), fill=GRAY)
    y += 38

    draw.line([(pad, y), (W - pad, y)], fill=DIVIDER, width=1)
    y += 24

    # plan section label
    draw.text((pad, y), "PLAN PURCHASED", font=_font(11, bold=True), fill=ACCENT)
    y += 22
    draw.text((pad, y), _s(plan_label), font=_font(16, bold=True), fill=WHITE)
    y += 38

    draw.line([(pad, y), (W - pad, y)], fill=DIVIDER, width=1)
    y += 24

    # amount section
    draw.text((pad, y), "AMOUNT PAID", font=_font(11, bold=True), fill=ACCENT)
    y += 22
    draw.text((pad, y), _s(f"{amount} {currency}"), font=_font(28, bold=True), fill=GREEN)
    y += 40

    draw.line([(pad, y), (W - pad, y)], fill=DIVIDER, width=1)
    y += 24

    # payment method row
    draw.text((pad, y), "METHOD", font=_font(11, bold=True), fill=ACCENT)
    draw.text((W - pad - _font(13).getlength(_s(payment_method)), y),
              _s(payment_method), font=_font(13), fill=GRAY)
    y += 26

    draw.text((pad, y), "DATE", font=_font(11, bold=True), fill=ACCENT)
    draw.text((W - pad - _font(13).getlength(_s(timestamp)), y),
              _s(timestamp), font=_font(13), fill=GRAY)
    y += 44

    # verified stamp
    stamp_x1, stamp_y1 = pad, y
    stamp_x2, stamp_y2 = W - pad, y + 72
    draw.rounded_rectangle([(stamp_x1, stamp_y1), (stamp_x2, stamp_y2)],
                            radius=10, outline=GREEN, width=2)
    mid = (stamp_x1 + stamp_x2) // 2
    draw.text((mid - _font(14, bold=True).getlength("VERIFIED PAYMENT") // 2, y + 14),
              "VERIFIED PAYMENT", font=_font(14, bold=True), fill=GREEN)
    draw.text((mid - _font(12).getlength("Your VIP access has been activated") // 2, y + 38),
              "Your VIP access has been activated", font=_font(12), fill=GRAY)
    y += 92

    # bottom note
    note = "Keep this receipt for your records."
    draw.text((mid - _font(11).getlength(note) // 2, y + 4),
              note, font=_font(11), fill=DIVIDER)

    # bottom accent bar
    draw.rectangle([(0, H - 6), (W, H)], fill=ACCENT)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf