import traceback

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import VIP_TIERS, TIER_EXPECTED_AMOUNT
from db import (
    is_admin, block_user, unblock_user, reset_key_attempts,
    get_accepted_payments, get_open_tickets, get_payment, get_ticket,
    update_payment_status, update_ticket_status, set_vip, mark_key_used,
    get_admin_stats, get_all_users_page,
    add_referral_commission, get_referrer_of_user, grant_approve_access,
    get_analytics_stats, get_top_referrers, reset_vip_reminder,
    log_error,
)
from keyboards import kb_admin_panel, kb_admin_back, kb_user_list, kb_give_vip_tiers, kb_paid_users_list
from messages import build_admin_msg
from utils import Flow, smart_edit, notify_admins, restore_admin_panel

router = Router()


# ── Back to admin panel ───────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_back")
async def cb_admin_back(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    await state.clear()
    txt, ents = build_admin_msg(call.from_user.first_name)
    await smart_edit(call, txt, entities=ents, reply_markup=kb_admin_panel())
    await call.answer()


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        total, vip, pending, tickets = get_admin_stats()
        text = (
            "📊  <b>BOT STATISTICS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "╔‼️‼️\n"
            f"║  👥  <b>Total Users</b>  —  <code>{total:,}</code>\n"
            f"║  ⭐  <b>VIP Members</b>  —  <code>{vip:,}</code>\n"
            f"║  ⏳  <b>Pending Pays.</b>  —  <code>{pending:,}</code>\n"
            f"║  🎫  <b>Open Tickets</b>  —  <code>{tickets:,}</code>\n"
            "╚══════════════════"
        )
        await smart_edit(call, text, reply_markup=kb_admin_back())
        await call.answer()
    except Exception as e:
        log_error("ADMIN_STATS", str(e), traceback.format_exc())
        await call.answer(f"Error: {e}", show_alert=True)


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_analytics")
async def cb_admin_analytics(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        s = get_analytics_stats()
        # Sales breakdown box
        bd_items = list(s["breakdown"].items())
        if bd_items:
            bd_lines = []
            for tier, count in bd_items:
                label = VIP_TIERS.get(tier, {}).get("label", tier).split("—")[0].strip()
                rev   = TIER_EXPECTED_AMOUNT.get(tier, 0) * count
                bd_lines.append(f"║  📦  <b>{label}</b>  ×<code>{count}</code> - <b>£{rev:,}</b>")
            breakdown_box = "╔📦 <b><u>SALES BREAKDOWN</u></b>\n" + "\n".join(bd_lines) + "\n╚══════════════════"
        else:
            breakdown_box = "╔📦 <b><u>SALES BREAKDOWN</u></b>\n║  <i>No sales yet</i>\n╚══════════════════"

        text = (
            "📈  <b><u>ANALYTICS DASHBOARD</u></b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "╔👥 <b><u>USERS</u></b>\n"
            f"║  ☑️  <b>Total</b>        <code>{s['total_users']:,}</code>\n"
            f"║  🆕  <b>New Today</b>    <code>{s['new_today']:,}</code>\n"
            f"║  📅  <b>This Week</b>    <code>{s['new_week']:,}</code>\n"
            f"║  ⭐  <b>Active VIPs</b>  <code>{s['active_vip']:,}</code>\n"
            f"║  ⏳  <b>Pending</b>      <code>{s['pending_payments']:,}</code>\n"
            "╚══════════════════\n\n"
            "╔💰 <b><u>REVENUE</u></b>\n"
            f"║  🏦  <b>All Time</b>    <b>£{s['total_revenue']:,.0f}</b>\n"
            f"║  📆  <b>This Week</b>   <b>£{s['week_revenue']:,.0f}</b>\n"
            f"║  ☀️  <b>Today</b>       <b>£{s['today_revenue']:,.0f}</b>\n"
            "╚══════════════════\n\n"
            f"{breakdown_box}\n\n"
            f"🏆  <b>Top Tier:</b>  {s['top_tier']}\n"
            f"💸  <b>Commission:</b>  <b>£{s['total_commission']:,.2f}</b>"
        )
        await smart_edit(call, text, reply_markup=kb_admin_back())
        await call.answer()
    except Exception as e:
        log_error("ADMIN_ANALYTICS", str(e), traceback.format_exc())
        await notify_admins(call.bot, f"⚠️ Analytics error: {e}")
        await call.answer(f"Error: {e}", show_alert=True)


# ── Leaderboard ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_leaderboard")
async def cb_admin_leaderboard(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        rows = get_top_referrers(10)
        if not rows:
            await call.answer("No referrers yet.", show_alert=True)
            return
        medals = ["🥇", "🥈", "🥉"]
        text = "🏆  <b><u>TOP REFERRERS</u></b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, (uid, username, first_name, balance, total_refs) in enumerate(rows):
            medal = medals[i] if i < 3 else f"<b>{i+1}.</b>"
            name  = f"@{username}" if username else (first_name or str(uid))
            text += f"{medal}  <b>{name}</b>\n      <code>{total_refs} refs</code>  ·  <b>£{float(balance):,.2f}</b>\n\n"
        await smart_edit(call, text, reply_markup=kb_admin_back())
        await call.answer()
    except Exception as e:
        log_error("ADMIN_LEADERBOARD", str(e), traceback.format_exc())
        await call.answer(f"Error: {e}", show_alert=True)


# ── Paid users ────────────────────────────────────────────────────────────────

def _build_paid_page_text(rows, page, total_pages, total):
    text = f"💰 <b>Recent Paid Users</b>  (Page {page + 1}/{total_pages}  •  Total: {total})\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
    for pid, uid, tier, created in rows:
        label = VIP_TIERS.get(tier, {}).get("label", tier)
        date  = created[:10] if created else "—"
        text += f"👤 <code>{uid}</code>\n📦 {label}\n📅 {date}\n\n"
    return text


@router.callback_query(F.data == "admin_pending")
async def cb_admin_pending(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        limit = 5
        rows, total = get_accepted_payments(limit=limit, offset=0)
        if not rows:
            await call.answer("No paid users yet.", show_alert=True)
            return
        total_pages = max(1, (total + limit - 1) // limit)
        text = _build_paid_page_text(rows, 0, total_pages, total)
        await smart_edit(call, text, reply_markup=kb_paid_users_list(0, total_pages))
        await call.answer()
    except Exception as e:
        log_error("ADMIN_PENDING", str(e), traceback.format_exc())
        await call.answer(f"Error: {e}", show_alert=True)


@router.callback_query(F.data.startswith("paid_page:"))
async def cb_paid_page(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        page  = int(call.data.split(":")[1])
        limit = 5
        offset = page * limit
        rows, total = get_accepted_payments(limit=limit, offset=offset)
        if not rows:
            await call.answer("No more entries.", show_alert=True)
            return
        total_pages = max(1, (total + limit - 1) // limit)
        text = _build_paid_page_text(rows, page, total_pages, total)
        await smart_edit(call, text, reply_markup=kb_paid_users_list(page, total_pages))
        await call.answer()
    except Exception as e:
        log_error("ADMIN_PAID_PAGE", str(e), traceback.format_exc())
        await call.answer(f"Error: {e}", show_alert=True)


# ── Open tickets ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_tickets")
async def cb_admin_tickets(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        rows = get_open_tickets()
        if not rows:
            await call.answer("No open tickets", show_alert=True)
            return
        text = "🎫 <b>Open Tickets</b>\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        for tid, uid, subject, created in rows:
            text += f"ID: <code>{tid}</code> | User: <code>{uid}</code>\nSubject: {subject}\nTime: {created}\n\n"
        await smart_edit(call, text[:4000], reply_markup=kb_admin_back())
        await call.answer()
    except Exception as e:
        log_error("ADMIN_TICKETS", str(e), traceback.format_exc())
        await call.answer(f"Error: {e}", show_alert=True)


# ── Block user ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_block")
async def cb_admin_block(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    await state.set_state(Flow.block_user_id)
    await state.update_data(panel_msg_id=call.message.message_id, panel_chat_id=call.message.chat.id)
    await smart_edit(call,
        "🚫 <b>Block User</b>\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        "Send the numeric Telegram user ID to block:",
        reply_markup=kb_admin_back())
    await call.answer()


@router.message(Flow.block_user_id)
async def on_block_user(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    try:
        uid = int(msg.text.strip() if msg.text else "")
    except (ValueError, AttributeError):
        await msg.answer("❌ Invalid ID — send a numeric Telegram user ID:")
        return
    try:
        block_user(uid)
    except Exception as e:
        log_error("BLOCK_USER", str(e), traceback.format_exc())
        await notify_admins(msg.bot, f"⚠️ Failed to block user {uid}: {e}")
        await msg.answer(f"❌ Error blocking user: {e}")
        return
    await state.clear()
    try:
        await msg.delete()
    except Exception:
        pass
    await restore_admin_panel(msg.bot, data.get("panel_chat_id"), data.get("panel_msg_id"), msg.from_user.first_name)
    await msg.answer(f"🚫 User <code>{uid}</code> has been blocked.", parse_mode="HTML")


# ── Unblock user ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_unblock")
async def cb_admin_unblock(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    await state.set_state(Flow.unblock_user_id)
    await state.update_data(panel_msg_id=call.message.message_id, panel_chat_id=call.message.chat.id)
    await smart_edit(call,
        "✅ <b>Unblock User</b>\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        "Send the numeric Telegram user ID to unblock:",
        reply_markup=kb_admin_back())
    await call.answer()


@router.message(Flow.unblock_user_id)
async def on_unblock_user(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    try:
        uid = int(msg.text.strip() if msg.text else "")
    except (ValueError, AttributeError):
        await msg.answer("❌ Invalid ID — send a numeric Telegram user ID:")
        return
    try:
        unblock_user(uid)
        reset_key_attempts(uid)
    except Exception as e:
        log_error("UNBLOCK_USER", str(e), traceback.format_exc())
        await notify_admins(msg.bot, f"⚠️ Failed to unblock user {uid}: {e}")
        await msg.answer(f"❌ Error unblocking user: {e}")
        return
    await state.clear()
    try:
        await msg.delete()
    except Exception:
        pass
    await restore_admin_panel(msg.bot, data.get("panel_chat_id"), data.get("panel_msg_id"), msg.from_user.first_name)
    await msg.answer(f"✅ User <code>{uid}</code> has been unblocked.", parse_mode="HTML")


# ── Manage users (paginated list) ─────────────────────────────────────────────

@router.callback_query(F.data == "admin_manage_user")
async def cb_manage_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        offset, limit = 0, 10
        users, total = get_all_users_page(offset, limit)
        if not users:
            await call.answer("No users found.", show_alert=True)
            return
        total_pages = (total + limit - 1) // limit
        text = "👥 <b>USER LIST</b>\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        for uid, username, first_name, is_vip, is_blocked in users:
            name = f"@{username}" if username else (first_name or "N/A")
            status = "🚫" if is_blocked else "✅"
            vip    = "⭐" if is_vip else "  "
            text += f"{status}{vip} <code>{uid}</code> — {name}\n"
        text += f"\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\nPage 1/{total_pages}"
        await smart_edit(call, text, reply_markup=kb_user_list(0, total_pages, offset, limit))
        await call.answer()
    except Exception as e:
        log_error("ADMIN_MANAGE_USER", str(e), traceback.format_exc())
        await notify_admins(call.bot, f"⚠️ User list error: {e}")
        await call.answer(f"Error: {e}", show_alert=True)


@router.callback_query(F.data.startswith("user_page:"))
async def cb_user_page(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        _, offset_str, page_str = call.data.split(":")
        offset = int(offset_str)
        page   = int(page_str)
        limit  = 10
        users, total = get_all_users_page(offset, limit)
        if not users:
            await call.answer("No more users", show_alert=True)
            return
        total_pages = (total + limit - 1) // limit
        text = "👥 <b>USER LIST</b>\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        for uid, username, first_name, is_vip, is_blocked in users:
            name = f"@{username}" if username else (first_name or "N/A")
            status = "🚫" if is_blocked else "✅"
            vip    = "⭐" if is_vip else "  "
            text += f"{status}{vip} <code>{uid}</code> — {name}\n"
        text += f"\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\nPage {page + 1}/{total_pages}"
        await smart_edit(call, text, reply_markup=kb_user_list(page, total_pages, offset, limit))
        await call.answer()
    except Exception as e:
        log_error("ADMIN_USER_PAGE", str(e), traceback.format_exc())
        await call.answer(f"Error: {e}", show_alert=True)


# ── Payment verdict ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("accept_pay:"))
@router.callback_query(F.data.startswith("reject_pay:"))
async def cb_payment_verdict(call: CallbackQuery):
    bot = call.bot
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        action, pid = call.data.split(":", 1)
        payment_id  = int(pid)
        row = get_payment(payment_id)
        if not row:
            await call.answer("Payment not found", show_alert=True)
            return

        user_id, tier_key, code = row

        if action == "accept_pay":
            days = VIP_TIERS[tier_key]["days"]
            set_vip(user_id, days)
            mark_key_used(code, user_id)
            reset_key_attempts(user_id)
            update_payment_status(payment_id, "accepted", call.from_user.id)
            grant_approve_access(user_id, days)

            referrer_id = get_referrer_of_user(user_id)
            if referrer_id:
                try:
                    amount = TIER_EXPECTED_AMOUNT.get(tier_key, 0) * 0.20
                    add_referral_commission(referrer_id, user_id, payment_id, amount)
                    await bot.send_message(
                        referrer_id,
                        f"💰 <b>Commission Earned!</b>\n\n"
                        f"Your referral just purchased a plan.\n"
                        f"You earned: <b>£{amount:.2f}</b>\n\n"
                        f"Open your <b>Profile</b> to check your balance.",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

            user_msg = (
                f"✅ <b>Payment Verified!</b>\n\n"
                f"Your VIP access has been activated for {days} days. Welcome aboard! 🎉"
            )
        else:
            update_payment_status(payment_id, "rejected", call.from_user.id)
            user_msg = (
                "❌ <b>Payment Not Verified</b>\n\n"
                "We couldn't verify your payment. Please contact support."
            )

        try:
            await bot.send_message(user_id, user_msg, parse_mode="HTML")
        except Exception:
            pass

        await call.message.edit_reply_markup(reply_markup=None)
        label = "✅ Accepted" if action == "accept_pay" else "❌ Rejected"
        await call.message.reply(f"{label} — user notified.")
    except Exception as e:
        log_error("PAYMENT_VERDICT", str(e), traceback.format_exc())
        await notify_admins(bot, f"⚠️ Payment verdict error: {e}")
        await call.answer(f"Error: {e}", show_alert=True)
    await call.answer()


# ── Ticket verdict ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("accept_ticket:"))
@router.callback_query(F.data.startswith("reject_ticket:"))
async def cb_ticket_verdict(call: CallbackQuery):
    bot = call.bot
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    try:
        action, tid = call.data.split(":", 1)
        ticket_id   = int(tid)
        row = get_ticket(ticket_id)
        if not row:
            await call.answer("Ticket not found", show_alert=True)
            return

        user_id = row[0]

        if action == "accept_ticket":
            update_ticket_status(ticket_id, "accepted", call.from_user.id)
            user_msg = (
                "🎫 <b>Support Ticket Accepted</b>\n\n"
                "Your ticket is being looked into. We'll reach out soon."
            )
        else:
            update_ticket_status(ticket_id, "rejected", call.from_user.id)
            user_msg = (
                "🎫 <b>Support Ticket Rejected</b>\n\n"
                "We couldn't process your request. Please try again."
            )

        try:
            await bot.send_message(user_id, user_msg, parse_mode="HTML")
        except Exception:
            pass

        await call.message.edit_reply_markup(reply_markup=None)
        label = "✅ Accepted" if action == "accept_ticket" else "❌ Rejected"
        await call.message.reply(f"{label} — user notified.")
    except Exception as e:
        log_error("TICKET_VERDICT", str(e), traceback.format_exc())
        await notify_admins(bot, f"⚠️ Ticket verdict error: {e}")
        await call.answer(f"Error: {e}", show_alert=True)
    await call.answer()


# ── Give VIP Manually ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_give_vip")
async def cb_admin_give_vip(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    await state.set_state(Flow.admin_give_vip_uid)
    await state.update_data(panel_msg_id=call.message.message_id, panel_chat_id=call.message.chat.id)
    await smart_edit(call,
        "🎁 <b>Give VIP Manually</b>\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        "Send the user's <b>numeric Telegram ID</b>:",
        reply_markup=kb_admin_back())
    await call.answer()


@router.message(Flow.admin_give_vip_uid)
async def on_give_vip_uid(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    try:
        uid = int(msg.text.strip() if msg.text else "")
    except (ValueError, AttributeError):
        await msg.answer("❌ Invalid ID — send a numeric Telegram user ID:")
        return
    await state.update_data(target_uid=uid)
    try:
        await msg.delete()
    except Exception:
        pass
    tier_msg = await msg.answer(
        f"👤 User <code>{uid}</code> selected.\n\nChoose a VIP tier to grant:",
        parse_mode="HTML",
        reply_markup=kb_give_vip_tiers(),
    )
    await state.update_data(tier_msg_id=tier_msg.message_id)


@router.callback_query(F.data.startswith("give_vip_tier:"))
async def cb_give_vip_tier(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    tier_key     = call.data.split(":", 1)[1]
    default_days = VIP_TIERS.get(tier_key, {}).get("days", 30)
    await state.update_data(tier_key=tier_key)
    await state.set_state(Flow.admin_give_vip_days)
    await smart_edit(call,
        f"📦 Tier: <b>{VIP_TIERS[tier_key]['label']}</b>\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"How many days? (send <b>0</b> for default: {default_days} days)",
        reply_markup=kb_admin_back())
    await call.answer()


@router.message(Flow.admin_give_vip_days)
async def on_give_vip_days(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear()
        return
    data     = await state.get_data()
    uid      = data.get("target_uid")
    tier_key = data.get("tier_key")
    default_days = VIP_TIERS.get(tier_key, {}).get("days", 30)
    try:
        days = int(msg.text.strip() if msg.text else "0")
        if days <= 0:
            days = default_days
    except (ValueError, AttributeError):
        days = default_days

    try:
        set_vip(uid, days)
        reset_vip_reminder(uid)
        grant_approve_access(uid, days)
    except Exception as e:
        log_error("GIVE_VIP", str(e), traceback.format_exc())
        await notify_admins(msg.bot, f"⚠️ Give VIP error for user {uid}: {e}")
        await msg.answer(f"❌ Error granting VIP: {e}")
        await state.clear()
        return

    await state.clear()
    # Delete admin's typed message and the tier selection message
    for mid in (msg.message_id, data.get("tier_msg_id")):
        if mid:
            try:
                await msg.bot.delete_message(msg.chat.id, mid)
            except Exception:
                pass
    try:
        await msg.bot.send_message(
            uid,
            f"🎉 <b>VIP Access Granted!</b>\n\n"
            f"An admin has granted you <b>{days} days</b> of VIP access.\n"
            f"Enjoy your premium membership!",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await restore_admin_panel(
        msg.bot,
        data.get("panel_chat_id"),
        data.get("panel_msg_id"),
        msg.from_user.first_name,
    )
    await msg.answer(
        f"✅ VIP granted to <code>{uid}</code> for <b>{days} days</b>.",
        parse_mode="HTML",
    )


# ── Cancel any admin flow ─────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_cancel")
async def cb_admin_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    txt, ents = build_admin_msg(call.from_user.first_name)
    await smart_edit(call, txt, entities=ents, reply_markup=kb_admin_panel())
    await call.answer()
