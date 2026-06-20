"""
Profile + channel + admin-extra handlers.
All NEW — added on top of original bot. Original code untouched.
"""
import asyncio
import traceback
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import BOT_USERNAME, VIP_TIERS, INVITE_LINKS, IMG_START
from db import (
    get_user_referral_stats, get_user_referral_code,
    use_commission_for_package, set_vip,
    get_channel_links, set_channel_link,
    get_all_user_ids, log_error,
    add_referral_commission, get_referrer_of_user,
    update_ticket_with_reply, close_support_session, get_ticket,
    get_open_tickets, is_user_vip, get_vip_expiry, get_latest_accepted_tier,
    update_ticket_status,
)
from keyboards import kb_profile, kb_back_only, kb_channel_menu, kb_admin_panel, kb_admin_back
from messages import MsgBuilder, build_admin_msg
from utils import (
    Flow, edit_or_send_photo, send_photo,
    safe_answer, safe_reply, safe_send_msg, safe_edit_text,
    smart_edit, notify_admins, restore_admin_panel,
)

router = Router()

_BOT = BOT_USERNAME.strip().lstrip("@").rstrip(":")


def _msg_profile(uid: int):
    stats = get_user_referral_stats(uid)
    code  = get_user_referral_code(uid)
    link  = f"https://t.me/{_BOT}?start=ref_{code}"
    bal   = stats["commission_balance"]

    m = MsgBuilder()
    m.emoji("crown").text("  ").bold("MY PROFILE").text("  ").emoji("crown").nl()
    m.sep()
    m.emoji("profile").text("  ID: ").code(str(uid)).nl()
    m.nl()

    if is_user_vip(uid):
        raw      = get_vip_expiry(uid)
        expiry   = datetime.fromisoformat(raw).strftime("%d %b %Y")
        tier_key = get_latest_accepted_tier(uid)
        invite   = INVITE_LINKS.get(tier_key or "", "")
        m.emoji("check_green").text("  ").bold("VIP Active").text(f" — expires {expiry}").nl()
        if invite:
            m.emoji("lock").text("  Group: ").link("Join Here", invite).nl()
    else:
        m.emoji("siren").text("  ").bold("Not VIP").text(" — use /start to purchase").nl()

    m.nl()
    m.emoji("fire").text("  ").bold("Referral & Commission").nl()
    m.sep()
    m.text("👥  Referrals:      ").bold(str(stats["total_referred"])).nl()
    m.emoji("pound").text("  Total Earned:  ").bold(f"£{stats['total_commission']:,.2f}").nl()
    m.emoji("card").text("  Balance:        ").bold(f"£{bal:,.2f}")
    if bal >= 30:
        m.text("  ").emoji("new").text(" ").italic("Redeem available")
    m.nl()
    m.emoji("check").text("  Free Packages: ").bold(str(stats["free_package_earned"])).nl()

    m.nl()
    m.emoji("link").text("  ").bold("Your Referral Link").nl()
    m.sep()
    m.code(link).nl()

    m.nl()
    m.emoji("stats").text("  ").bold("Commission Rates").nl()
    m.sep()
    m.blockquote(
        "💷  £80 plan  →  earn £16\n"
        "💷  £60 plan  →  earn £12\n"
        "💷  £40 plan  →  earn £8\n"
        "💷  £30 plan  →  earn £6"
    ).nl()
    m.nl()
    m.italic("Share your link — earn 20% on every referral purchase. "
             "Accumulate £30 and redeem a free VIP package.").nl()
    m.nl()
    m.emoji("siren").text("  ").bold("Important: ").italic(
        "Commission is only credited once your referral completes a purchase. "
        "Referrals who join but do not buy will not top up your balance."
    )
    return m.build()


def _msg_channel_empty():
    m = MsgBuilder()
    m.emoji("globe").text("  ").bold("CHANNELS").nl()
    m.sep()
    m.emoji("siren").text("  ").bold("No channels configured yet.").nl()
    m.italic("Check back soon — links will appear here.")
    return m.build()


def _msg_channel_list():
    m = MsgBuilder()
    m.emoji("globe").text("  ").bold("OUR CHANNELS").nl()
    m.sep()
    m.emoji("check_green").text("  ").bold("Join our official channels below:")
    return m.build()


def _msg_redeem(balance: float, available: list):
    m = MsgBuilder()
    m.emoji("gift").text("  ").bold("REDEEM COMMISSION").nl()
    m.sep()
    m.emoji("card").text("  Balance: ").bold(f"£{balance:,.2f}").nl()
    m.nl()
    m.emoji("lock").text("  ").bold("Available Packages:").nl()
    m.sep()
    pkg_lines = ""
    for i, (k, p) in enumerate(available):
        name = VIP_TIERS[k]["label"].split("—")[0].strip()
        pkg_lines += f"✅  {i+1}.  {name} — £{p}\n"
    m.blockquote(pkg_lines.rstrip()).nl()
    m.nl()
    m.italic("Reply with the number — e.g. ").bold("1")
    return m.build()


def _msg_broadcast_prompt():
    m = MsgBuilder()
    m.emoji("broadcast").text("  ").bold("BROADCAST TO ALL USERS").nl()
    m.sep()
    m.emoji("check_green").text("  ").italic("Send the message you want delivered to all users:")
    return m.build()


def _msg_channel_config(links: list):
    m = MsgBuilder()
    m.emoji("channel").text("  ").bold("SET CHANNEL LINKS").nl()
    m.sep()
    if links:
        m.emoji("check_green").text("  ").bold("Current links:").nl()
        for i, (n, u) in enumerate(links):
            m.emoji("lock").text(f"  {i+1}. {n}").nl()
            m.text(f"      {u}").nl()
        m.nl()
    m.emoji("new").text("  ").bold("Send up to 5 links, one per line:").nl()
    m.blockquote("Channel Name|https://t.me/link\nUpdates|https://t.me/link2\n...")
    return m.build()


def _msg_open_tickets(tickets: list):
    m = MsgBuilder()
    m.emoji("ticket").text("  ").bold("OPEN SUPPORT TICKETS").nl()
    m.sep()
    for tid, uid, subject, created in tickets[:10]:
        m.emoji("check_green").text("  ID: ").code(str(tid)).text("   User: ").code(str(uid)).nl()
        m.emoji("new").text(f"  {subject}").nl()
        m.emoji("lock").text(f"  {created}").nl()
        m.nl()
    return m.build()


def _msg_reply_prompt():
    m = MsgBuilder()
    m.emoji("pencil").text("  ").bold("SEND REPLY").nl()
    m.sep()
    m.italic("Type your reply — it will be sent directly to the user:")
    return m.build()


@router.callback_query(F.data == "channel_menu")
async def cb_channel_menu(call: CallbackQuery):
    await call.answer()
    links = get_channel_links()
    if not links:
        txt, ents = _msg_channel_empty()
        await edit_or_send_photo(call.bot, call, IMG_START, txt, ents, kb_channel_menu([]))
        return
    txt, ents = _msg_channel_list()
    await edit_or_send_photo(call.bot, call, IMG_START, txt, ents, kb_channel_menu(links))


@router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    await call.answer()
    txt, ents = _msg_profile(call.from_user.id)
    await edit_or_send_photo(call.bot, call, IMG_START, txt, ents, kb_profile())


@router.callback_query(F.data == "profile_use_commission")
async def cb_use_commission(call: CallbackQuery, state: FSMContext):
    await call.answer()
    stats   = get_user_referral_stats(call.from_user.id)
    balance = stats["commission_balance"]
    if balance < 30:
        await call.answer(f"Need at least £30. Your balance: £{balance:.2f}", show_alert=True)
        return
    available = []
    for key, tier in VIP_TIERS.items():
        if key in ("allgirls_all", "allgirls_separate"):
            continue
        for price in (80, 60, 40, 30):
            if f"£{price}" in tier["label"] and balance >= price:
                available.append((key, price))
                break
    if not available:
        await call.answer("Not enough balance for any package.", show_alert=True)
        return
    txt, ents = _msg_redeem(balance, available)
    await edit_or_send_photo(call.bot, call, IMG_START, txt, ents, kb_back_only())
    await state.set_state(Flow.use_commission)
    await state.update_data(available_tiers=available, balance=balance)


@router.message(Flow.use_commission)
async def on_use_commission(msg: Message, state: FSMContext):
    data      = await state.get_data()
    available = data.get("available_tiers", [])
    balance   = data.get("balance", 0)
    raw       = (msg.text or "").strip()
    selected  = None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(available):
            selected = available[idx]
    else:
        for key, price in available:
            if raw.lower() in VIP_TIERS[key]["label"].lower():
                selected = (key, price)
                break
    if not selected:
        m = MsgBuilder()
        m.emoji("siren").text("  ").bold("Invalid.").text(" Send the number shown — e.g. ").bold("1")
        txt, ents = m.build()
        await safe_answer(msg, txt, ents)
        return
    key, price = selected
    use_commission_for_package(msg.from_user.id, price)
    days = VIP_TIERS[key]["days"]
    set_vip(msg.from_user.id, days)
    m = MsgBuilder()
    m.emoji("check_green").text("  ").bold("Package Redeemed!").nl()
    m.sep()
    m.emoji("card").text("  Used: ").bold(f"£{price}").nl()
    m.emoji("diamond").text("  VIP for: ").bold(f"{days} days").nl()
    m.emoji("pound").text("  Remaining: ").bold(f"£{balance - price:,.2f}")
    txt, ents = m.build()
    await safe_answer(msg, txt, ents)
    await state.clear()


@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(call: CallbackQuery, state: FSMContext):
    from db import is_admin
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    await state.set_state(Flow.admin_broadcast)
    await state.update_data(panel_msg_id=call.message.message_id, panel_chat_id=call.message.chat.id)
    txt, ents = _msg_broadcast_prompt()
    await smart_edit(call, txt, entities=ents, reply_markup=kb_admin_back())
    await call.answer()


@router.message(Flow.admin_broadcast)
async def on_admin_broadcast(msg: Message, state: FSMContext):
    from db import is_admin
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    text = (msg.text or "").strip()
    if not text:
        await msg.answer("Cannot be empty.")
        return
    data = await state.get_data()
    uids = get_all_user_ids()

    try:
        await msg.delete()
    except Exception:
        pass

    m = MsgBuilder()
    m.text("🔄  Sending to ").bold(str(len(uids))).text(" users…")
    stxt, sents = m.build()
    status = await safe_answer(msg, stxt, sents)

    ok = fail = 0
    total = len(uids)
    for i, uid in enumerate(uids, 1):
        try:
            await msg.bot.send_message(
                uid,
                f"📢 <b>━━━━ ANNOUNCEMENT ━━━━</b>\n\n{text}",
                parse_mode="HTML",
            )
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.01)
        if i % 50 == 0 or i == total:
            try:
                m_prog = MsgBuilder()
                m_prog.text("🔄  Progress: ").bold(f"{i}/{total}").text(f"  —  ✅ {ok}  ❌ {fail}")
                ptxt, pents = m_prog.build()
                await safe_edit_text(status, ptxt, pents)
            except Exception:
                pass

    m2 = MsgBuilder()
    m2.emoji("check_green").text("  ").bold("Broadcast Complete").nl()
    m2.sep()
    m2.emoji("check_green").text("  Delivered: ").bold(str(ok)).nl()
    m2.emoji("siren").text("  Failed:    ").bold(str(fail))
    dtxt, dents = m2.build()
    try:
        await safe_edit_text(status, dtxt, dents)
    except Exception:
        pass

    await state.clear()
    await restore_admin_panel(
        msg.bot, data.get("panel_chat_id"), data.get("panel_msg_id"), msg.from_user.first_name
    )


@router.callback_query(F.data == "admin_channels")
async def cb_admin_channels(call: CallbackQuery, state: FSMContext):
    from db import is_admin
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    await state.set_state(Flow.admin_set_channels)
    await state.update_data(panel_msg_id=call.message.message_id, panel_chat_id=call.message.chat.id)
    txt, ents = _msg_channel_config(get_channel_links())
    await smart_edit(call, txt, entities=ents, reply_markup=kb_admin_back())
    await call.answer()


@router.message(Flow.admin_set_channels)
async def on_admin_set_channels(msg: Message, state: FSMContext):
    from db import is_admin
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    data  = await state.get_data()
    raw   = (msg.text or "").strip()
    saved = 0
    try:
        for i, line in enumerate(raw.split("\n")[:5]):
            if "|" in line:
                name, url = line.split("|", 1)
                set_channel_link(name.strip(), url.strip(), i)
                saved += 1
    except Exception as e:
        log_error("SET_CHANNELS", str(e), traceback.format_exc())
        await notify_admins(msg.bot, f"⚠️ Set channels error: {e}")

    try:
        await msg.delete()
    except Exception:
        pass
    await state.clear()
    await restore_admin_panel(msg.bot, data.get("panel_chat_id"), data.get("panel_msg_id"), msg.from_user.first_name)
    if saved:
        await msg.answer(f"✅ {saved} channel link(s) saved!")
    else:
        await msg.answer("❌ No valid lines found.\nFormat: <code>Channel Name|https://t.me/link</code>", parse_mode="HTML")


@router.callback_query(F.data == "admin_support_reply")
async def cb_admin_support_reply(call: CallbackQuery):
    from db import is_admin
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    tickets = get_open_tickets()
    if not tickets:
        await call.answer("No open tickets", show_alert=True)
        return
    txt, ents = _msg_open_tickets(tickets)
    await smart_edit(call, txt, entities=ents, reply_markup=kb_admin_back())
    await call.answer()


@router.callback_query(F.data.startswith("reply_ticket:"))
async def cb_reply_ticket(call: CallbackQuery, state: FSMContext):
    from db import is_admin
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    tid = int(call.data.split(":", 1)[1])
    await state.update_data(
        reply_ticket_id=tid,
        panel_msg_id=call.message.message_id,
        panel_chat_id=call.message.chat.id,
    )
    await state.set_state(Flow.admin_reply_ticket)
    txt, ents = _msg_reply_prompt()
    await smart_edit(call, txt, entities=ents, reply_markup=kb_admin_back())
    await call.answer()


@router.message(Flow.admin_reply_ticket)
async def on_reply_ticket(msg: Message, state: FSMContext):
    from db import is_admin
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    data  = await state.get_data()
    tid   = data.get("reply_ticket_id")
    reply = (msg.text or "").strip()
    if not reply:
        await msg.answer("Reply cannot be empty.")
        return
    row = get_ticket(tid)
    if not row:
        await msg.answer("Ticket not found.")
        await state.clear()
        return
    user_id = row[0]
    try:
        m = MsgBuilder()
        m.emoji("check_green").text(" ").bold("Support Reply").nl()
        m.sep()
        m.text(reply)
        rtxt, rents = m.build()
        await safe_send_msg(msg.bot, user_id, rtxt, entities=rents)
        update_ticket_with_reply(tid, "replied", msg.from_user.id, reply)
    except Exception as e:
        log_error("REPLY_ERROR", str(e), traceback.format_exc())
        await notify_admins(msg.bot, f"⚠️ Ticket reply error (ticket {tid}): {e}")
        await msg.answer("⚠️ Could not send reply — user may have blocked the bot.")
        await state.clear()
        return
    try:
        await msg.delete()
    except Exception:
        pass
    await state.clear()
    await restore_admin_panel(msg.bot, data.get("panel_chat_id"), data.get("panel_msg_id"), msg.from_user.first_name)
    await msg.answer(f"✅ Reply sent to user <code>{user_id}</code>.", parse_mode="HTML")


@router.callback_query(F.data.startswith("close_ticket:"))
async def cb_close_ticket(call: CallbackQuery):
    from db import is_admin
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        tid = int(call.data.split(":", 1)[1])
        close_support_session(tid)
        update_ticket_status(tid, "closed", call.from_user.id)
        await call.message.edit_reply_markup(reply_markup=None)
        m = MsgBuilder()
        m.emoji("lock").text("  ").bold("Session closed.")
        txt, ents = m.build()
        await safe_reply(call.message, txt, ents)
    except Exception as e:
        log_error("CLOSE_TICKET", str(e), traceback.format_exc())
        await call.answer(f"Error: {e}", show_alert=True)
    await call.answer()