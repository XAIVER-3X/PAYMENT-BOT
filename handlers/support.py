import time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import IMG_START, IMG_SUPPORT, SUPPORT_COOLDOWN_SECONDS
from db import add_ticket
from keyboards import kb_main_menu, kb_support_back, kb_ticket_verdict
from messages import (
    build_plan_list_msg, build_support_blocked_msg, build_support_subject_msg,
)
from utils import (
    Flow, notify_admins, send_photo, edit_or_send_photo, support_cooldown, user_link,
)

router = Router()


@router.callback_query(F.data == "support")
async def cb_support(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    uid = call.from_user.id
    now = time.time()
    if now - support_cooldown.get(uid, 0) < SUPPORT_COOLDOWN_SECONDS:
        remaining = int(SUPPORT_COOLDOWN_SECONDS - (now - support_cooldown[uid]))
        await call.answer(f"⏳ Please wait {remaining // 60}m {remaining % 60}s", show_alert=True)
        return

    txt, ents = build_support_subject_msg()
    await edit_or_send_photo(bot, call, IMG_SUPPORT, txt, ents, kb_support_back())

    await state.set_state(Flow.support_subject)
    await call.answer()


@router.callback_query(F.data == "support_blocked")
async def cb_support_blocked(call: CallbackQuery, state: FSMContext):
    bot = call.bot
    uid = call.from_user.id
    now = time.time()
    if now - support_cooldown.get(uid, 0) < SUPPORT_COOLDOWN_SECONDS:
        remaining = int(SUPPORT_COOLDOWN_SECONDS - (now - support_cooldown[uid]))
        await call.answer(f"⏳ Please wait {remaining // 60}m {remaining % 60}s", show_alert=True)
        return

    # Bug 8: set cooldown here (when prompt is first shown) so repeated
    # button presses can't re-enter the subject prompt while still "open"
    support_cooldown[uid] = time.time()

    txt, ents = build_support_blocked_msg()
    await edit_or_send_photo(bot, call, IMG_SUPPORT, txt, ents, kb_support_back())

    await state.set_state(Flow.support_blocked)
    await call.answer()


@router.message(Flow.support_blocked)
async def on_support_blocked(msg: Message, state: FSMContext):
    bot = msg.bot
    u = msg.from_user
    body = msg.text.strip() if msg.text else ""
    ticket_id = add_ticket(u.id, "BLOCKED USER APPEAL", body)
    await notify_admins(
        bot,
        f"🚨 <b>Blocked User Support Request</b>\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"👤 {user_link(u)} • <code>{u.id}</code>\n\n"
        f"💬 {body}\n\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        reply_markup=kb_ticket_verdict(ticket_id),
    )

    await msg.answer(
        "✅ <b>Message received.</b>\n\nOur team will review your case and respond as soon as possible.",
        parse_mode="HTML",
    )
    txt, ents = build_plan_list_msg()
    try:
        await send_photo(bot, msg.chat.id, IMG_START, caption=txt,
                         caption_entities=ents, reply_markup=kb_main_menu())
    except Exception:
        await bot.send_message(msg.chat.id, txt, entities=ents, reply_markup=kb_main_menu())
    await state.clear()


@router.message(Flow.support_subject)
async def on_support_subject(msg: Message, state: FSMContext):
    await state.update_data(subject=msg.text.strip() if msg.text else "No subject")
    await state.set_state(Flow.support_body)
    await msg.answer(
        "📝 <b>Step 2/2 : Describe your issue</b>\n"
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        "Write your problem in detail. We'll reply soon.\n\n"
        "<i>Press Back to cancel.</i>",
        parse_mode="HTML", reply_markup=kb_support_back(),
    )


@router.message(Flow.support_body)
async def on_support_body(msg: Message, state: FSMContext):
    bot = msg.bot
    data = await state.get_data()
    subject = data.get("subject", "No subject")
    body = msg.text.strip() if msg.text else ""
    u = msg.from_user
    support_cooldown[u.id] = time.time()
    ticket_id = add_ticket(u.id, subject, body)
    await notify_admins(
        bot,
        f"🎫 <b>New Support Ticket</b>\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        f"👤 {user_link(u)} • <code>{u.id}</code>\n"
        f"📌 Subject: <b>{subject}</b>\n\n"
        f"💬 {body}\n\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        reply_markup=kb_ticket_verdict(ticket_id),
    )

    await msg.answer(
        "✅ <b>Ticket Submitted</b>\n"
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
        "Your request has been received. Our team will respond within 24 hours.",
        parse_mode="HTML",
    )
    txt, ents = build_plan_list_msg()
    try:
        await send_photo(bot, msg.chat.id, IMG_START, caption=txt,
                         caption_entities=ents, reply_markup=kb_main_menu())
    except Exception:
        await bot.send_message(msg.chat.id, txt, entities=ents, reply_markup=kb_main_menu())
    await state.clear()
