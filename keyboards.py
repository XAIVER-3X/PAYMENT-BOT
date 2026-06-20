from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    VIP_TIERS, GIRLS_LIST, GIRLS_SEPARATE_LINK,
    BTN_LIVE_CHAT, BTN_PROFILE, BTN_SUPPORT, BTN_VIP_STATUS, BTN_CHANNEL,
    BTN_CONTACT_SUPPORT, BTN_PAY_NOW, BTN_IVE_PAID, BTN_SHOW_SEPARATE,
    BTN_BACK, BTN_BACK_TO_PLANS, BTN_BUY_SEPARATE, BTN_BUY_ALL,
    BTN_REDEEM_COMMISSION, BTN_TOP_REFERRERS, BTN_CLOSE_CHAT, BTN_CLOSE_SESSION,
    BTN_CANCEL, BTN_ACCEPT, BTN_REJECT, BTN_REPLY, BTN_CLOSE,
    BTN_STATS, BTN_ANALYTICS, BTN_PAID_USERS, BTN_LEADERBOARD, BTN_BLOCK_USER,
    BTN_UNBLOCK_USER, BTN_OPEN_TICKETS, BTN_GIVE_VIP, BTN_MANAGE_USERS,
    BTN_BROADCAST, BTN_SET_CHANNELS, BTN_REPLY_SUPPORT, BTN_PREV, BTN_NEXT, BTN_ADMIN_PANEL
)


def kb_main_menu():
    rows = []
    for key, tier in VIP_TIERS.items():
        if key in ("allgirls_all", "allgirls_separate"):
            continue
        rows.append([InlineKeyboardButton(text=f"  {tier['btn']}  ", callback_data=f"tier:{key}")])
    rows.append([
        InlineKeyboardButton(text=f"  {BTN_LIVE_CHAT}  ", callback_data="live_chat"),
        InlineKeyboardButton(text=f"  {BTN_PROFILE}  ",   callback_data="profile"),
    ])
    rows.append([
        InlineKeyboardButton(text=f"  {BTN_SUPPORT}  ",   callback_data="support"),
        InlineKeyboardButton(text=f"  {BTN_VIP_STATUS}  ", callback_data="mystatus"),
    ])
    rows.append([InlineKeyboardButton(text=f"  {BTN_CHANNEL}  ", callback_data="channel_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_blocked():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_CONTACT_SUPPORT} ", callback_data="support_blocked")]
    ])


def kb_pay(tier_key):
    tier_link = VIP_TIERS[tier_key].get("link", "")
    pay_btn = (
        InlineKeyboardButton(text=f" {BTN_PAY_NOW} ", url=tier_link)
        if tier_link
        else InlineKeyboardButton(text=f" {BTN_PAY_NOW} — Contact Support ", callback_data="support")
    )
    rows = [
        [pay_btn],
        [InlineKeyboardButton(text=f" {BTN_IVE_PAID} ", callback_data=f"paid:{tier_key}")],
    ]
    if tier_key == "allgirls":
        rows.append([InlineKeyboardButton(text=f" {BTN_SHOW_SEPARATE} ", callback_data="show_extra")])
    rows.append([
        InlineKeyboardButton(text=f" {BTN_SUPPORT} ", callback_data="support"),
        InlineKeyboardButton(text=f" {BTN_BACK} ",     callback_data="back"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_allgirls_browse():
    rows = []
    for i in range(0, len(GIRLS_LIST), 2):
        row = []
        for j in range(2):
            if i + j < len(GIRLS_LIST):
                idx = i + j + 1
                name = GIRLS_LIST[i + j]
                row.append(InlineKeyboardButton(text=f" {idx}) {name} ", callback_data=f"girl_noop:{idx}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text=f" {BTN_BUY_SEPARATE} ", callback_data="allgirls_buyseparate"),
        InlineKeyboardButton(text=f" {BTN_BUY_ALL} ",       callback_data="allgirls_buyall"),
    ])
    rows.append([InlineKeyboardButton(text=f" {BTN_BACK} ", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_allgirls_pay(tier_key):
    tier = VIP_TIERS[tier_key]
    tier_link = tier.get("link", "")
    pay_btn = (
        InlineKeyboardButton(text=f" {BTN_PAY_NOW} ", url=tier_link)
        if tier_link
        else InlineKeyboardButton(text=f" {BTN_PAY_NOW} — Contact Support ", callback_data="support")
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [pay_btn],
        [InlineKeyboardButton(text=f" {BTN_IVE_PAID} ", callback_data=f"paid:{tier_key}")],
        [InlineKeyboardButton(text=f" {BTN_SUPPORT} ", callback_data="support"),
         InlineKeyboardButton(text=f" {BTN_BACK} ",     callback_data="allgirls_browse")],
    ])


def kb_girl_pay(girl_name):
    pay_btn = (
        InlineKeyboardButton(text=" 💳  Pay Now — £25 (G2A) ", url=GIRLS_SEPARATE_LINK)
        if GIRLS_SEPARATE_LINK
        else InlineKeyboardButton(text=" 💳  Pay Now — Contact Support ", callback_data="support")
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [pay_btn],
        [InlineKeyboardButton(text=f" {BTN_IVE_PAID} ",  callback_data="paid:allgirls_separate")],
        [InlineKeyboardButton(text=f" {BTN_BACK} ",                 callback_data="allgirls_browse")],
    ])


def kb_extra_service():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f" {BTN_BUY_SEPARATE} ", callback_data="allgirls_buyseparate"),
            InlineKeyboardButton(text=f" {BTN_BUY_ALL} ",        callback_data="tier:allgirls"),
        ],
        [InlineKeyboardButton(text=f" {BTN_BACK_TO_PLANS} ", callback_data="back")],
    ])


def kb_code_error():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_CONTACT_SUPPORT} ", callback_data="support"),
         InlineKeyboardButton(text=f" {BTN_BACK} ",             callback_data="back")],
    ])


def kb_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_BACK_TO_PLANS} ", callback_data="back")],
    ])


def kb_back_only():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_BACK} ", callback_data="back")],
    ])


def kb_support_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_BACK} ", callback_data="support_back")],
    ])


def kb_admin_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_STATS} ",        callback_data="admin_stats"),
         InlineKeyboardButton(text=f" {BTN_ANALYTICS} ",    callback_data="admin_analytics")],
        [InlineKeyboardButton(text=f" {BTN_PAID_USERS} ",   callback_data="admin_pending"),
         InlineKeyboardButton(text=f" {BTN_LEADERBOARD} ",  callback_data="admin_leaderboard")],
        [InlineKeyboardButton(text=f" {BTN_BLOCK_USER} ",   callback_data="admin_block"),
         InlineKeyboardButton(text=f" {BTN_UNBLOCK_USER} ", callback_data="admin_unblock")],
        [InlineKeyboardButton(text=f" {BTN_OPEN_TICKETS} ", callback_data="admin_tickets"),
         InlineKeyboardButton(text=f" {BTN_GIVE_VIP} ",     callback_data="admin_give_vip")],
        [InlineKeyboardButton(text=f" {BTN_MANAGE_USERS} ", callback_data="admin_manage_user")],
        [InlineKeyboardButton(text=f" {BTN_BROADCAST} ",    callback_data="admin_broadcast")],
        [InlineKeyboardButton(text=f" {BTN_SET_CHANNELS} ", callback_data="admin_channels")],
        [InlineKeyboardButton(text=f" {BTN_REPLY_SUPPORT} ",callback_data="admin_support_reply")],
    ])


def kb_verdict(payment_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f" {BTN_ACCEPT} ", callback_data=f"accept_pay:{payment_id}"),
        InlineKeyboardButton(text=f" {BTN_REJECT} ", callback_data=f"reject_pay:{payment_id}"),
    ]])


def kb_ticket_verdict(ticket_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_REPLY} ",  callback_data=f"reply_ticket:{ticket_id}")],
        [InlineKeyboardButton(text=f" {BTN_ACCEPT} ", callback_data=f"accept_ticket:{ticket_id}"),
         InlineKeyboardButton(text=f" {BTN_REJECT} ", callback_data=f"reject_ticket:{ticket_id}")],
        [InlineKeyboardButton(text=f" {BTN_CLOSE} ",  callback_data=f"close_ticket:{ticket_id}")],
    ])


def kb_admin_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_ADMIN_PANEL} ", callback_data="admin_back")],
    ])


def kb_paid_users_list(page, total_pages):
    rows = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=BTN_PREV, callback_data=f"paid_page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text=BTN_NEXT, callback_data=f"paid_page:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=f" {BTN_ADMIN_PANEL} ", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_user_list(page, total_pages, offset, limit=10):
    rows = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=BTN_PREV, callback_data=f"user_page:{offset - limit}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text=BTN_NEXT, callback_data=f"user_page:{offset + limit}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=f" {BTN_ADMIN_PANEL} ", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ── NEW keyboards ─────────────────────────────────────────────────────────────

def kb_channel_menu(links):
    rows = [
        [InlineKeyboardButton(text=f" 📡  {n} ", url=u)]
        for n, u in links if u  # skip buttons with empty URLs
    ]
    rows.append([InlineKeyboardButton(text=f" {BTN_BACK} ", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_profile():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_REDEEM_COMMISSION} ", callback_data="profile_use_commission")],
        [InlineKeyboardButton(text=f" {BTN_TOP_REFERRERS} ",     callback_data="leaderboard")],
        [InlineKeyboardButton(text=f" {BTN_BACK} ",               callback_data="back")],
    ])


def kb_give_vip_tiers():
    from config import VIP_TIERS
    rows = []
    for key, tier in VIP_TIERS.items():
        if key in ("allgirls_all", "allgirls_separate"):
            continue
        label = tier["label"].split("—")[0].strip()
        rows.append([InlineKeyboardButton(text=f" {label} ", callback_data=f"give_vip_tier:{key}")])
    rows.append([InlineKeyboardButton(text=f" {BTN_CANCEL} ", callback_data="admin_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_live_chat():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" {BTN_CLOSE_CHAT} ", callback_data="close_live_chat")],
    ])


def kb_admin_live_reply(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f" 💬  Reply to {user_id} ", callback_data=f"live_reply:{user_id}")],
        [InlineKeyboardButton(text=f" {BTN_CLOSE_SESSION} ",        callback_data=f"close_user_chat:{user_id}")],
    ])

