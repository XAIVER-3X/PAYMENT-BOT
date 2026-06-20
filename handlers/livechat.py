"""
Live 2-way support chat.
User enters a persistent chat session; messages are forwarded to all admins.
Admin clicks Reply → enters admin_live_reply state → message sent back to user.
Either side can close the session.
"""
import time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db import (
    is_admin, is_user_blocked,
    create_live_session, get_live_session_status,
    update_live_session_activity, close_live_session,
)
from keyboards import kb_live_chat, kb_admin_live_reply, kb_admin_panel, kb_main_menu
from utils import Flow, notify_admins, user_link, safe_send_msg, smart_edit

router = Router()

# Cooldown map so users can't spam-open chat sessions (60 s)
_chat_cooldown: dict[int, float] = {}
_CHAT_COOLDOWN = 60


# ── User: open live chat ──────────────────────────────────────────────────────

@router.callback_query(F.data == "live_chat")
async def cb_live_chat(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    await call.answer()

    if is_user_blocked(uid):
        await call.message.answer("🚫 Your account is restricted. Contact support.")
        return

    now = time.time()
    if now - _chat_cooldown.get(uid, 0) < _CHAT_COOLDOWN:
        remaining = int(_CHAT_COOLDOWN - (now - _chat_cooldown[uid]))
        await call.message.answer(f"⏳ Please wait {remaining}s before opening a new chat.")
        return

    _chat_cooldown[uid] = now
    create_live_session(uid)
    await state.set_state(Flow.live_chat_active)

    u = call.from_user
    await call.message.answer(
        "💬  <b>LIVE SUPPORT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "You're connected to our support team.\n\n"
        "✏️  Type your message — we'll reply shortly.\n\n"
        "<i>Tap 🔒 Close Chat when you're done.</i>",
        parse_mode="HTML",
        reply_markup=kb_live_chat(),
    )

    await notify_admins(
        call.bot,
        f"🔔  <b>LIVE CHAT OPENED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  {user_link(u)}\n"
        f"🆔  <code>{u.id}</code>\n\n"
        f"<i>Session open — awaiting their message.</i>",
        reply_markup=kb_admin_live_reply(uid),
    )


# ── User: send message in live chat ──────────────────────────────────────────

@router.message(Flow.live_chat_active)
async def on_live_chat_message(msg: Message, state: FSMContext):
    uid = msg.from_user.id

    # Check if admin closed the session from their side
    status = get_live_session_status(uid)
    if status == "closed":
        await msg.answer(
            "🔒 <b>Chat Closed</b>\n\nThis session has been closed by support.\n"
            "Use /start to open a new chat.",
            parse_mode="HTML",
        )
        await state.clear()
        return

    if msg.text and msg.text.startswith("/"):
        await state.clear()
        await msg.answer("Session ended. Use /start to return to the menu.")
        return

    update_live_session_activity(uid)
    u = msg.from_user
    content = msg.text or "[non-text message]"

    await notify_admins(
        msg.bot,
        f"💬  <b>NEW MESSAGE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤  {user_link(u)}\n"
        f"🆔  <code>{u.id}</code>\n\n"
        f"📩  {content}",
        reply_markup=kb_admin_live_reply(uid),
    )

    await msg.answer(
        "✅  <b>Sent!</b>  Our team will reply shortly.",
        parse_mode="HTML",
        reply_markup=kb_live_chat(),
    )


# ── User: close live chat ─────────────────────────────────────────────────────

@router.callback_query(F.data == "close_live_chat")
async def cb_close_live_chat(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    close_live_session(uid)
    await state.clear()
    await call.answer()
    await call.message.answer(
        "🔒  <b>Chat Closed</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Thanks for reaching out!\n"
        "Use /start to return to the menu.",
        parse_mode="HTML",
        reply_markup=kb_main_menu(),
    )
    await notify_admins(
        call.bot,
        f"🔒  <b>CHAT CLOSED BY USER</b>\n\n"
        f"👤  <code>{uid}</code> ended the session.",
    )


# ── Admin: click Reply to User ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("live_reply:"))
async def cb_admin_live_reply(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    target_uid = int(call.data.split(":", 1)[1])

    status = get_live_session_status(target_uid)
    if status == "closed":
        await call.answer("This session is already closed.", show_alert=True)
        return

    await state.update_data(live_reply_target=target_uid)
    await state.set_state(Flow.admin_live_reply)
    await call.message.answer(
        f"✏️  <b>REPLY TO USER</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔  <code>{target_uid}</code>\n\n"
        f"Type your reply below, or send /cancel to abort:",
        parse_mode="HTML",
    )
    await call.answer()


# ── Admin: send reply message to user ────────────────────────────────────────

@router.message(Flow.admin_live_reply)
async def on_admin_live_reply(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id):
        await state.clear()
        return

    if msg.text and msg.text.strip().lower() in ("/cancel", "cancel"):
        await state.clear()
        await msg.answer("❌ Reply cancelled.", reply_markup=kb_admin_panel())
        return

    data       = await state.get_data()
    target_uid = data.get("live_reply_target")
    reply_text = (msg.text or "").strip()

    if not reply_text:
        await msg.answer("Reply cannot be empty.")
        return

    status = get_live_session_status(target_uid)
    if status == "closed":
        await state.clear()
        await msg.answer(
            f"⚠️ Session for user <code>{target_uid}</code> is already closed.",
            parse_mode="HTML",
            reply_markup=kb_admin_panel(),
        )
        return

    try:
        await safe_send_msg(
            msg.bot, target_uid,
            f"💬  <b>SUPPORT REPLY</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{reply_text}",
            parse_mode="HTML",
            reply_markup=kb_live_chat(),
        )
        await msg.answer(
            f"✅  Reply delivered to <code>{target_uid}</code>.",
            parse_mode="HTML",
            reply_markup=kb_admin_panel(),
        )
    except Exception as e:
        await msg.answer(
            f"⚠️ Could not reach user <code>{target_uid}</code>.\nError: {e}",
            parse_mode="HTML",
            reply_markup=kb_admin_panel(),
        )

    await state.clear()


# ── Admin: close user's session ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("close_user_chat:"))
async def cb_close_user_chat(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Not authorised", show_alert=True)
        return
    target_uid = int(call.data.split(":", 1)[1])
    close_live_session(target_uid)

    try:
        await safe_send_msg(
            call.bot, target_uid,
            "🔒 <b>Your support session has been closed by the team.</b>\n\n"
            "Use /start if you need further help.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.reply(f"🔒 Session for <code>{target_uid}</code> closed.", parse_mode="HTML")
    await call.answer()


# ── User-facing leaderboard (from profile) ────────────────────────────────────

@router.callback_query(F.data == "leaderboard")
async def cb_user_leaderboard(call: CallbackQuery):
    from db import get_top_referrers
    from keyboards import kb_back_only
    await call.answer()
    rows = get_top_referrers(10)
    if not rows:
        text = (
            "🏆  <b>TOP REFERRERS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>No referrers yet — be the first!\n"
            "Share your link and earn 20% per sale.</i>"
        )
        await smart_edit(call, text, reply_markup=kb_back_only())
        return
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆  <b>TOP REFERRERS</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (uid, username, first_name, balance, total_refs) in enumerate(rows):
        medal = medals[i] if i < 3 else f"<b>{i+1}.</b>"
        name  = f"@{username}" if username else (first_name or "Anonymous")
        text += f"{medal}  {name}\n      <code>{total_refs} refs</code>  ·  <b>£{float(balance):,.2f}</b>\n\n"
    text += "<i>Share your link — earn 20% on every sale!</i>"
    await smart_edit(call, text, reply_markup=kb_back_only())
