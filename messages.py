from aiogram.types import MessageEntity

from config import (
    CUSTOM_EMOJI, VIP_TIERS,
    MSG_PLAN_LIST_HEADER, MSG_PLAN_LIST_FEATURES, MSG_PLAN_LIST_FOOTER,
    MSG_CODE_PROMPT_TITLE, MSG_CODE_PROMPT_BODY, MSG_CODE_PROMPT_FOOTER,
    MSG_SUPPORT_SUBJECT_TITLE, MSG_SUPPORT_SUBJECT_STEP, MSG_SUPPORT_SUBJECT_QUESTION, MSG_SUPPORT_SUBJECT_EXAMPLE, MSG_SUPPORT_SUBJECT_CANCEL,
    MSG_SUPPORT_BLOCKED_TITLE, MSG_SUPPORT_BLOCKED_STEP, MSG_SUPPORT_BLOCKED_HELP, MSG_SUPPORT_BLOCKED_CANCEL,
    MSG_PAYMENT_SUCCESS_TITLE, MSG_PAYMENT_SUCCESS_WELCOME, MSG_PAYMENT_SUCCESS_ACTIVE, MSG_PAYMENT_SUCCESS_VOUCHER,
    MSG_MYSTATUS_TITLE, MSG_MYSTATUS_ACTIVE, MSG_MYSTATUS_EXPIRES, MSG_MYSTATUS_JOIN, MSG_MYSTATUS_NOT_VIP, MSG_MYSTATUS_NOT_VIP_HELP,
    MSG_ADMIN_TITLE, MSG_ADMIN_WELCOME, MSG_ADMIN_TOTAL_USERS, MSG_ADMIN_VIP_MEMBERS, MSG_ADMIN_PENDING_PAY, MSG_ADMIN_OPEN_TICKETS, MSG_ADMIN_SELECT_ACTION
)
from db import get_admin_stats


def _utf16_len(s):
    return len(s.encode("utf-16-le")) // 2


class MsgBuilder:

    def __init__(self):
        self._text = ""
        self._entities = []

    def _add(self, etype, content, **extra):
        offset = _utf16_len(self._text)
        length = _utf16_len(content)
        self._text += content
        self._entities.append(MessageEntity(type=etype, offset=offset, length=length, **extra))
        return self

    def _add_multi(self, types, content, **extra):
        """Apply multiple entity types over the same text span (e.g. bold+italic)."""
        offset = _utf16_len(self._text)
        length = _utf16_len(content)
        self._text += content
        for t in types:
            self._entities.append(MessageEntity(type=t, offset=offset, length=length, **extra))
        return self

    # ── Plain helpers ─────────────────────────────────────────────────────────
    def text(self, s):           self._text += s;        return self
    def nl(self, n=1):           self._text += "\n" * n; return self

    # ── Telegram font styles ──────────────────────────────────────────────────
    def bold(self, s):           return self._add("bold", s)
    def italic(self, s):         return self._add("italic", s)
    def underline(self, s):      return self._add("underline", s)
    def strikethrough(self, s):  return self._add("strikethrough", s)
    def spoiler(self, s):        return self._add("spoiler", s)
    def code(self, s):           return self._add("code", s)
    def pre(self, s, lang=""):   return self._add("pre", s, language=lang)
    def blockquote(self, s):     return self._add("blockquote", s)
    def link(self, label, url):  return self._add("text_link", label, url=url)

    # ── Combo styles ──────────────────────────────────────────────────────────
    def bold_italic(self, s):    return self._add_multi(["bold", "italic"], s)
    def bold_underline(self, s): return self._add_multi(["bold", "underline"], s)

    # ── Custom emoji — always creates a proper entity ─────────────────────────
    def emoji(self, key):
        if key not in CUSTOM_EMOJI:
            return self
        eid, fallback = CUSTOM_EMOJI[key]
        if eid and eid.isdigit():
            self._add("custom_emoji", fallback, custom_emoji_id=eid)
        else:
            self._text += fallback
        return self

    # ── Separators ────────────────────────────────────────────────────────────
    def sep(self):
        self._text += "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        return self

    def hsep(self):
        self._text += "━━━━━━━━━━━━━━━━━━━━\n"
        return self

    # ── Box helpers — emoji icons now create real custom_emoji entities ───────
    def box_open(self, key):
        eid, fb = CUSTOM_EMOJI.get(key, ("", "◆"))
        self._text += "┌"
        if eid and eid.isdigit():
            self._add("custom_emoji", fb, custom_emoji_id=eid)
            self._add("custom_emoji", fb, custom_emoji_id=eid)
        else:
            self._text += fb + fb
        self._text += "\n"
        return self

    def box_row(self, icon_key, label, value=None):
        eid, fb = CUSTOM_EMOJI.get(icon_key, ("", "▪"))
        self._text += "├─"
        if eid and eid.isdigit():
            self._add("custom_emoji", fb, custom_emoji_id=eid)
        else:
            self._text += fb
        self._text += " "
        self._add("bold", str(label))
        if value is not None:
            self._text += "  "
            self._add("bold", str(value))
        self._text += "\n"
        return self

    def box_last(self, icon_key, label, value=None):
        eid, fb = CUSTOM_EMOJI.get(icon_key, ("", "▪"))
        self._text += "└─"
        if eid and eid.isdigit():
            self._add("custom_emoji", fb, custom_emoji_id=eid)
        else:
            self._text += fb
        self._text += " "
        self._add("bold", str(label))
        if value is not None:
            self._text += "  "
            self._add("bold", str(value))
        self._text += "\n"
        return self

    def build(self):
        return self._text, self._entities


# ── USER FACING MESSAGES ──────────────────────────────────────────────────────

def build_plan_list_msg():
    m = MsgBuilder()
    m.emoji("crown").text("  ").bold_underline(MSG_PLAN_LIST_HEADER).text("  ").emoji("fire").nl()
    m.hsep()
    for feat in MSG_PLAN_LIST_FEATURES:
        m.emoji("check_green").text(" ").bold(feat).nl()
    m.hsep()
    m.emoji("diamond").text("  ").bold(MSG_PLAN_LIST_FOOTER)
    return m.build()


def build_tier_msg(key):
    tier = VIP_TIERS[key]
    m = MsgBuilder()
    m.emoji("adult").text(" ").bold_underline(tier["label"]).nl()
    m.sep()
    for emoji_key, line_text in tier.get("lines", []):
        m.emoji(emoji_key).text(" ").bold(line_text).nl()
    m.sep()
    m.emoji("card").text("  Tap ").bold("Pay Now").italic(" → then tap ").bold("I've Paid")
    return m.build()


def build_code_prompt_msg(amount=None):
    m = MsgBuilder()
    m.emoji("check_green").text(" ").bold_underline(MSG_CODE_PROMPT_TITLE).nl()
    m.sep()
    m.bold(MSG_CODE_PROMPT_BODY).nl()
    m.nl()
    if amount is not None:
        m.emoji("pound").text(" ").bold(f"You need a £{amount}").italic(" Rewarble voucher.").nl()
    m.emoji("lock").text(" ").italic(MSG_CODE_PROMPT_FOOTER)
    return m.build()


def build_allgirls_all_msg():
    tier = VIP_TIERS["allgirls_all"]
    m = MsgBuilder()
    m.emoji("adult").text(" ").bold_underline(tier["label"]).nl()
    m.sep()
    for emoji_key, line_text in tier.get("lines", []):
        m.emoji(emoji_key).text(" ").bold(line_text).nl()
    m.sep()
    m.emoji("card").text("  Tap ").bold("Pay Now").italic(" → then tap ").bold("I've Paid").text("  ").emoji("check_green")
    return m.build()


def build_girl_selected_msg(girl_name):
    tier = VIP_TIERS["allgirls_separate"]
    m = MsgBuilder()
    m.emoji("check_green").text(" ").bold_underline("Selected:").text(f"  {girl_name}").nl()
    m.sep()
    for emoji_key, line_text in tier.get("lines", []):
        m.emoji(emoji_key).text(" ").bold(line_text).nl()
    m.sep()
    m.emoji("card").text("  Tap ").bold("Pay Now").italic(" → then tap ").bold("I've Paid").text("  ").emoji("check_green")
    return m.build()


def build_allgirls_browse_msg():
    m = MsgBuilder()
    m.emoji("adult").text(" ").bold_underline("ALL GIRLS VIP").nl()
    m.sep()
    m.emoji("check_green").text(" ").bold("21 exclusive girls").nl()
    m.emoji("diamond").text(" ").bold("Buy All").italic(" — every girl's folder at once").text("  (£50)").nl()
    m.emoji("new").text(" ").bold("Buy Separate").italic(" — pick any one girl").text("  (£25)").nl()
    m.nl()
    m.emoji("pound").text(" ").bold_italic("Select an option below ↓")
    return m.build()


def build_pick_girl_msg(girls_list):
    m = MsgBuilder()
    m.emoji("adult").text(" ").bold_underline("PICK YOUR GIRL").text(" ").emoji("adult").nl()
    m.sep()
    for i, name in enumerate(girls_list, 1):
        m.emoji("check_green").text(f" {i})  ").bold(name).nl()
    m.sep()
    m.bold("Send the number").italic(f"  (1–{len(girls_list)})").text(" to confirm your choice:")
    return m.build()


def build_extra_service_msg(girls_list):
    m = MsgBuilder()
    m.emoji("adult").text(" ").bold_underline("ALL GIRLS — FULL SERVICE").text(" ").emoji("adult").nl()
    m.sep()
    for i, girl in enumerate(girls_list, 1):
        m.emoji("check_green").text(f" {i})  ").italic(girl).nl()
    m.sep()
    m.emoji("siren").text(" ").bold("174+ More Girls Available").text("  ").emoji("adult")
    return m.build()


def build_support_subject_msg():
    m = MsgBuilder()
    m.emoji("ticket").text(" ").bold_underline(MSG_SUPPORT_SUBJECT_TITLE).nl()
    m.sep()
    m.emoji("new").text(" ").bold(MSG_SUPPORT_SUBJECT_STEP).nl()
    m.nl()
    m.italic(MSG_SUPPORT_SUBJECT_QUESTION).nl()
    m.text("  ").italic(MSG_SUPPORT_SUBJECT_EXAMPLE).nl()
    m.nl()
    m.emoji("check").text("  ").italic(MSG_SUPPORT_SUBJECT_CANCEL)
    return m.build()


def build_support_blocked_msg():
    m = MsgBuilder()
    m.emoji("ticket").text(" ").bold_underline(MSG_SUPPORT_BLOCKED_TITLE).nl()
    m.sep()
    m.emoji("new").text(" ").bold(MSG_SUPPORT_BLOCKED_STEP).nl()
    m.nl()
    m.italic(MSG_SUPPORT_BLOCKED_HELP).nl()
    m.nl()
    m.emoji("check").text("  ").italic(MSG_SUPPORT_BLOCKED_CANCEL)
    return m.build()


def build_payment_success_msg(days, api_data):
    m = MsgBuilder()
    m.emoji("check_green").text("  ").bold_underline(MSG_PAYMENT_SUCCESS_TITLE).text("  🎉").nl()
    m.hsep()
    m.emoji("diamond").text("  ").bold(MSG_PAYMENT_SUCCESS_WELCOME).nl()
    m.emoji("lock").text("  " + MSG_PAYMENT_SUCCESS_ACTIVE + " ").bold(f"{days} days").text(".").nl()
    m.nl()
    m.emoji("card").text("  ").underline(MSG_PAYMENT_SUCCESS_VOUCHER).nl()
    m.sep()
    m.text("  Amount:  ").bold(f"{api_data.get('faceValue')} {api_data.get('faceValueCurrency', 'GBP')}").nl()
    m.text("  Serial:  ").code(str(api_data.get("voucherSerial", ""))).nl()
    m.text("  TX:  ").code(str(api_data.get("transactionWTRX", "")))
    return m.build()


def build_mystatus_msg(is_vip, expiry_str=None, invite_link=None):
    m = MsgBuilder()
    m.emoji("crown").text("  ").bold_underline(MSG_MYSTATUS_TITLE).nl()
    m.hsep()
    if is_vip and expiry_str:
        m.emoji("check_green").text("  ").bold(MSG_MYSTATUS_ACTIVE).nl()
        m.emoji("lock").text("  " + MSG_MYSTATUS_EXPIRES + " ").bold(expiry_str).nl()
        if invite_link and invite_link != "LINK_NOT_SET":
            m.nl()
            m.emoji("link").text("  ").link(MSG_MYSTATUS_JOIN, invite_link).nl()
    else:
        m.emoji("siren").text("  ").bold(MSG_MYSTATUS_NOT_VIP).nl()
        m.nl()
        m.text(MSG_MYSTATUS_NOT_VIP_HELP)
    return m.build()


# ── ADMIN FACING MESSAGES ─────────────────────────────────────────────────────

def build_admin_msg(first_name):
    total, vip, pending, tickets = get_admin_stats()
    m = MsgBuilder()
    # use only first-block verified emoji IDs (adult, check_green, pound, siren, diamond, lock, new)
    m.emoji("lock").text("  ").bold_underline(MSG_ADMIN_TITLE).nl()
    m.hsep()
    m.emoji("check_green").text("  " + MSG_ADMIN_WELCOME + " ").bold(first_name).text("!").nl()
    m.nl()
    m.box_open("siren")
    m.box_row("new",      MSG_ADMIN_TOTAL_USERS,   f"{total:,}")
    m.box_row("diamond",  MSG_ADMIN_VIP_MEMBERS,   f"{vip:,}")
    m.box_row("siren",    MSG_ADMIN_PENDING_PAY,  f"{pending:,}")
    m.box_last("check",   MSG_ADMIN_OPEN_TICKETS,  f"{tickets:,}")
    m.nl()
    m.italic(MSG_ADMIN_SELECT_ACTION)
    return m.build()
