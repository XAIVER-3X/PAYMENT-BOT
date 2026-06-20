from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from datetime import datetime

from config import OWNER_ID, IMG_MENU, IMG_START, INVITE_LINKS
from db import (
    add_user, is_admin, is_user_blocked, set_rewarble_api_key,
    is_user_vip, get_vip_expiry, get_latest_accepted_tier,
    add_user_with_referrer, get_user_by_referral_code,
)
from keyboards import kb_admin_panel, kb_blocked, kb_main_menu
from messages import build_admin_msg, build_plan_list_msg
from utils import send_photo, send_sticker

router = Router()


@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    bot = msg.bot
    u   = msg.from_user

    # Referral tracking — silent, no extra notification message
    referrer_id = None
    if msg.text and len(msg.text.split()) > 1:
        param = msg.text.split()[1]
        if param.startswith("ref_"):
            found = get_user_by_referral_code(param[4:])
            if found and found != u.id:
                referrer_id = found
    add_user_with_referrer(u.id, u.username, u.first_name, referrer_id)
    # No extra notification sent to referrer on join — they only hear when a purchase is made

    if is_admin(u.id):
        txt, ents = build_admin_msg(u.first_name)
        try:
            await send_photo(bot, msg.chat.id, IMG_START, caption=txt,
                             caption_entities=ents, reply_markup=kb_admin_panel())
        except Exception:
            await bot.send_message(msg.chat.id, txt, entities=ents, reply_markup=kb_admin_panel())
        return

    if is_user_blocked(u.id):
        from config import MSG_ACCOUNT_RESTRICTED_HEADER, MSG_ACCOUNT_RESTRICTED_BODY
        await msg.answer(
            f"🚫 <b>{MSG_ACCOUNT_RESTRICTED_HEADER}</b>\n\n"
            f"{MSG_ACCOUNT_RESTRICTED_BODY}",
            parse_mode="HTML", reply_markup=kb_blocked(),
        )
        return

    await send_sticker(bot, msg.chat.id, "welcome")

    txt, ents = build_plan_list_msg()
    try:
        await send_photo(bot, msg.chat.id, IMG_START, caption=txt,
                         caption_entities=ents, reply_markup=kb_main_menu())
    except Exception:
        await msg.answer(txt, entities=ents, reply_markup=kb_main_menu())


@router.message(Command("admin"))
async def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        await msg.answer("Not authorised")
        return
    bot = msg.bot
    txt, ents = build_admin_msg(msg.from_user.first_name)
    try:
        await send_photo(bot, msg.chat.id, IMG_START, caption=txt,
                         caption_entities=ents, reply_markup=kb_admin_panel())
    except Exception:
        await bot.send_message(msg.chat.id, txt, entities=ents, reply_markup=kb_admin_panel())


@router.message(Command("setapikey"))
async def cmd_setapikey(msg: Message):
    if msg.from_user.id != OWNER_ID:
        await msg.answer("❌ Only the bot owner can set the API key.")
        return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Usage: /setapikey YOUR_API_KEY")
        return
    set_rewarble_api_key(parts[1].strip())
    await msg.answer("✅ Rewarble API key saved. Payment verification is now active.")


@router.message(Command("mystatus"))
async def cmd_mystatus(msg: Message):
    from config import MSG_MYSTATUS_EXPIRES, MSG_MYSTATUS_JOIN, MSG_MYSTATUS_NOT_VIP_HELP
    if is_user_vip(msg.from_user.id):
        expiry_raw = get_vip_expiry(msg.from_user.id)
        expiry = datetime.fromisoformat(expiry_raw).strftime("%Y-%m-%d %H:%M")
        tier_key = get_latest_accepted_tier(msg.from_user.id)
        invite_link = INVITE_LINKS.get(tier_key, "") if tier_key else ""
        text = f"✅ <b>You are VIP until {expiry}</b>"
        if invite_link and invite_link != "LINK_NOT_SET":
            text += f"\n\n🔗 {MSG_MYSTATUS_JOIN}\n{invite_link}"
        await msg.answer(text, parse_mode="HTML")
    else:
        await msg.answer(f"❌ {MSG_MYSTATUS_NOT_VIP_HELP}")

