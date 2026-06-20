from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    IMG_MENU, TIER_IMAGES, VIP_TIERS, MAX_KEY_ATTEMPTS,
    TIER_EXPECTED_AMOUNT, INVITE_LINKS, GIRLS_LIST, PREVIEW_CHANNEL_ID,
)
from db import (
    is_user_blocked, is_key_used, increment_key_attempts, block_user, set_vip,
    mark_key_used, reset_key_attempts, add_payment, mark_auto_approved,
    # NEW: commission + approve bot
    add_referral_commission, get_referrer_of_user, grant_approve_access,
)
from keyboards import kb_back, kb_back_only, kb_blocked, kb_code_error, kb_girl_pay
from messages import (
    build_code_prompt_msg, build_girl_selected_msg, build_payment_success_msg,
    build_pick_girl_msg,
)
from invoice import generate_invoice_image
from services import verify_rewarble_code
from utils import (
    Flow, edit_or_send_photo, edit_message_photo_by_id, send_photo,
    send_sticker, notify_admins, notify_admins_photo, user_link,
)

router = Router()


@router.callback_query(F.data.startswith("paid:"))
async def cb_paid(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if is_user_blocked(call.from_user.id):
        await call.message.answer("🚫 Your account is restricted.", reply_markup=kb_blocked())
        return

    key = call.data.split(":", 1)[1]
    await state.update_data(tier=key)
    await state.set_state(Flow.waiting_code)

    expected = TIER_EXPECTED_AMOUNT.get(key)
    txt, ents = build_code_prompt_msg(amount=expected)
    img = TIER_IMAGES.get(key, IMG_MENU)
    await edit_or_send_photo(call.bot, call, img, txt, ents, kb_back_only())


@router.callback_query(F.data == "allgirls_buyseparate")
async def cb_allgirls_buyseparate(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if is_user_blocked(call.from_user.id):
        await call.message.answer("🚫 Your account is restricted.", reply_markup=kb_blocked())
        return

    await state.set_state(Flow.waiting_girl_num)
    await state.update_data(list_msg_id=call.message.message_id)

    txt, ents = build_pick_girl_msg(GIRLS_LIST)
    img = TIER_IMAGES.get("allgirls", IMG_MENU)
    await edit_or_send_photo(call.bot, call, img, txt, ents, kb_back_only())


@router.message(Flow.waiting_girl_num)
async def on_girl_number(msg: Message, state: FSMContext):
    bot = msg.bot
    if is_user_blocked(msg.from_user.id):
        await state.clear()
        return

    if msg.text and msg.text.startswith("/"):
        await state.clear()
        await msg.answer("⚠️ Session cancelled. Use /start to start over.", reply_markup=kb_back())
        return

    # Bug 3: guard against non-text input (stickers, photos, etc.)
    if not msg.text:
        await msg.answer(
            f"❌ Please send a number between <b>1 and {len(GIRLS_LIST)}</b>.",
            parse_mode="HTML", reply_markup=kb_back_only(),
        )
        return

    try:
        num = int(msg.text.strip())
        if num < 1 or num > len(GIRLS_LIST):
            raise ValueError
    except ValueError:
        await msg.answer(
            f"❌ Please send a number between <b>1 and {len(GIRLS_LIST)}</b>.",
            parse_mode="HTML", reply_markup=kb_back_only(),
        )
        return

    girl_name = GIRLS_LIST[num - 1]
    await state.update_data(tier="allgirls_separate", selected_girl=girl_name)
    # Bug 1: transition to waiting_code so the user can enter their voucher code
    await state.set_state(Flow.waiting_code)

    txt, ents = build_girl_selected_msg(girl_name)
    img = TIER_IMAGES.get("allgirls", IMG_MENU)
    kb = kb_girl_pay(girl_name)

    data = await state.get_data()
    list_msg_id = data.get("list_msg_id")
    edited = False
    if list_msg_id:
        edited = await edit_message_photo_by_id(bot, msg.chat.id, list_msg_id, img, txt, ents, kb)

    if not edited:
        try:
            await send_photo(bot, msg.chat.id, img, caption=txt, caption_entities=ents, reply_markup=kb)
        except Exception:
            await msg.answer(txt, entities=ents, reply_markup=kb)


@router.message(Flow.waiting_code)
async def on_code_received(msg: Message, state: FSMContext):
    bot = msg.bot

    if msg.text and msg.text.startswith("/"):
        from config import MSG_SESSION_CANCELLED
        await state.clear()
        await msg.answer(MSG_SESSION_CANCELLED, reply_markup=kb_back())
        return

    # Bug 3: guard against non-text input (stickers, photos, etc.)
    if not msg.text:
        from config import MSG_VERIFY_TEXT_ONLY
        await msg.answer(MSG_VERIFY_TEXT_ONLY, reply_markup=kb_back_only())
        return

    data = await state.get_data()
    key = data.get("tier")
    if not key:
        await msg.answer("Please start over with /start")
        await state.clear()
        return

    code = msg.text.strip()
    u = msg.from_user

    if is_key_used(code):
        attempts = increment_key_attempts(u.id)
        remaining = MAX_KEY_ATTEMPTS - attempts

        if attempts >= MAX_KEY_ATTEMPTS:
            block_user(u.id)
            await state.clear()
            await notify_admins(
                bot,
                f"🚫 <b>User Auto-Blocked</b>\n\n"
                f"👤 {user_link(u)} • <code>{u.id}</code>\n"
                f"Reason: Submitted already-used keys {MAX_KEY_ATTEMPTS} times."
            )
            await msg.answer(
                "🚫 <b>Account Restricted</b>\n\n"
                "This key has already been used and you have exceeded the attempt limit.\n"
                "Please contact support.",
                parse_mode="HTML", reply_markup=kb_blocked(),
            )
            return

        await msg.answer(
            f"❌ <b>Key Already Used!</b>\n\n"
            f"This key has already been redeemed by another user.\n"
            f"⚠️ You have <b>{remaining} attempt(s)</b> remaining.\n\n"
            f"Contact support if you believe this is an error.",
            parse_mode="HTML", reply_markup=kb_code_error(),
        )
        return

    success, api_message, api_data = await verify_rewarble_code(code)

    if success:
        face_value = float(api_data.get("faceValue", 0))
        expected_amount = TIER_EXPECTED_AMOUNT.get(key, 0)
        currency = api_data.get("faceValueCurrency", "GBP")

        if face_value < expected_amount:
            await msg.answer(
                f"❌ <b>Wrong Voucher Amount</b>\n"
                f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                f"This voucher is worth <b>{face_value} {currency}</b> but the "
                f"<b>{VIP_TIERS[key]['label']}</b> plan requires "
                f"<b>£{expected_amount}</b>.\n\n"
                f"Please purchase the correct voucher amount and try again, "
                f"or contact support.",
                parse_mode="HTML", reply_markup=kb_code_error(),
            )
            return

        days = VIP_TIERS[key]["days"]
        set_vip(u.id, days)
        mark_key_used(code, u.id)
        reset_key_attempts(u.id)
        payment_id = add_payment(u.id, key, code, status="accepted", api_response=str(api_data))
        mark_auto_approved(payment_id)  # stamps reviewed_at only; no fake reviewed_by=0


        # NEW: approve bot bridge
        grant_approve_access(u.id, days)

        # NEW: referral commission
        referrer_id = get_referrer_of_user(u.id)
        if referrer_id:
            try:
                amount = TIER_EXPECTED_AMOUNT.get(key, 0) * 0.20
                add_referral_commission(referrer_id, u.id, payment_id, amount)
                comm_msg = (
                    "💰 <b>Commission Earned!</b>\n\n"
                    "Your referral just purchased a plan.\n"
                    "You earned: <b>£" + f"{amount:.2f}" + "</b>\n\n"
                    "Open your <b>Profile</b> to check your balance."
                )
                await bot.send_message(referrer_id, comm_msg, parse_mode="HTML")
            except Exception:
                pass

        txt, ents = build_payment_success_msg(days, api_data)
        await msg.answer(txt, entities=ents)

        invoice_buf = generate_invoice_image(
            invoice_number=f"INV{payment_id:06d}",
            customer_name=u.first_name or "Customer",
            username=f"@{u.username}" if u.username else "N/A",
            user_id=u.id,
            plan_label=VIP_TIERS[key]["label"],
            duration_days=days,
            amount=face_value,
            currency=currency,
            payment_method="Rewarble Voucher",
            voucher_serial=str(api_data.get("voucherSerial", "")),
            transaction_id=str(api_data.get("transactionWTRX", "")),
        )
        invoice_bytes = invoice_buf.getvalue()

        try:
            user_invoice = BufferedInputFile(invoice_bytes, filename=f"invoice_{payment_id}.png")
            await bot.send_photo(
                u.id, photo=user_invoice,
                caption=f"🧾 <b>Invoice #{payment_id}</b>\nThank you for your purchase!",
                parse_mode="HTML",
            )
        except Exception:
            pass

        invite_link = INVITE_LINKS.get(key, "")
        try:
            if invite_link and invite_link != "LINK_NOT_SET":
                await bot.send_message(
                    u.id,
                    f"🔗 <b>Your Private Group Invite</b>\n"
                    f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
                    f"Tap below to join your VIP channel:\n{invite_link}\n\n"
                    f"Welcome aboard! 🎉",
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    u.id,
                    "✅ <b>Payment confirmed!</b>\n\n"
                    "Your invite link will be delivered shortly. "
                    "If you don't receive it within a few minutes, please contact support.",
                    parse_mode="HTML",
                )
        except Exception:
            pass

        await send_sticker(bot, u.id, "verified")

        selected_girl = data.get("selected_girl", "")
        girl_line = f"👧 Selected Girl: <b>{selected_girl}</b>\n" if selected_girl else ""
        await notify_admins(
            bot,
            f"✅ <b>Payment Auto-Approved</b>\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n\n"
            f"👤 {user_link(u)} • <code>{u.id}</code>\n"
            f"👑 {VIP_TIERS[key]['label']}\n"
            f"{girl_line}"
            f"🔑 Code: <code>{code}</code>\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"📦 <b>API Response:</b>\n"
            f"• Amount: {face_value} {currency}\n"
            f"• Serial: <code>{api_data.get('voucherSerial')}</code>\n"
            f"• Transaction: <code>{api_data.get('transactionWTRX')}</code>\n"
            f"• State: {api_data.get('state')}"
        )
        await notify_admins_photo(
            bot, invoice_bytes, f"invoice_{payment_id}.png",
            f"🧾 Invoice copy for payment #{payment_id} (user <code>{u.id}</code>)",
        )

        try:
            preview_invoice = BufferedInputFile(invoice_bytes, filename=f"invoice_{payment_id}.png")
            await bot.send_photo(PREVIEW_CHANNEL_ID, photo=preview_invoice)
        except Exception:
            pass

        await state.clear()
    else:
        # Bug 2: if api_data is None it's a service failure (no API key, network error),
        # not the user's fault — do not count it against their attempt limit.
        if api_data is None:
            await msg.answer(
                f"⚠️ <b>Verification Unavailable</b>\n\n"
                f"{api_message}\n\n"
                f"Please try again in a moment or contact support.",
                parse_mode="HTML", reply_markup=kb_code_error(),
            )
            # Notify admin — API key not set or service down
            if "unavailable" in api_message.lower() or "api key" in api_message.lower():
                await notify_admins(
                    bot,
                    f"⚠️ <b>Rewarble API Key Not Set</b>\n\n"
                    f"A user tried to verify a payment but the API key is missing.\n\n"
                    f"Fix: send /setapikey YOUR_KEY to the bot.",
                )
            return

        attempts = increment_key_attempts(u.id)
        remaining = MAX_KEY_ATTEMPTS - attempts

        if attempts >= MAX_KEY_ATTEMPTS:
            block_user(u.id)
            await state.clear()
            await notify_admins(
                bot,
                f"🚫 <b>User Auto-Blocked</b>\n\n"
                f"👤 {user_link(u)} • <code>{u.id}</code>\n"
                f"Reason: Submitted invalid keys {MAX_KEY_ATTEMPTS} times.\n"
                f"Last code: <code>{code}</code>\n"
                f"API error: {api_message}"
            )
            await msg.answer(
                "🚫 <b>Account Restricted</b>\n\n"
                "You have entered too many invalid keys.\n"
                "Only support can help you now.",
                parse_mode="HTML", reply_markup=kb_blocked(),
            )
            return

        await msg.answer(
            f"❌ <b>Invalid Code!</b>\n\n"
            f"{api_message}\n\n"
            f"⚠️ You have <b>{remaining} attempt(s)</b> remaining before your account is restricted.\n\n"
            f"Please check your code and try again.",
            parse_mode="HTML", reply_markup=kb_code_error(),
        )