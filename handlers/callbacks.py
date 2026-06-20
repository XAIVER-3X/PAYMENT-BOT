from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from config import IMG_START, IMG_MENU, TIER_IMAGES, VIP_TIERS, INVITE_LINKS, GIRLS_LIST
from db import is_user_blocked, is_user_vip, get_vip_expiry, get_latest_accepted_tier
from keyboards import (
    kb_main_menu, kb_blocked, kb_pay, kb_allgirls_browse, kb_allgirls_pay,
    kb_extra_service,
)
from messages import (
    build_plan_list_msg, build_tier_msg, build_allgirls_all_msg,
    build_allgirls_browse_msg, build_extra_service_msg, build_mystatus_msg,
)
from utils import edit_or_send_photo

router = Router()


@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()


@router.callback_query(F.data == "back")
async def cb_back(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    txt, ents = build_plan_list_msg()
    await edit_or_send_photo(call.bot, call, IMG_START, txt, ents, kb_main_menu())


@router.callback_query(F.data == "support_back")
async def cb_support_back(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    txt, ents = build_plan_list_msg()
    await edit_or_send_photo(call.bot, call, IMG_START, txt, ents, kb_main_menu())


@router.callback_query(F.data == "mystatus")
async def cb_mystatus(call: CallbackQuery):
    await call.answer()
    if is_user_vip(call.from_user.id):
        expiry_raw = get_vip_expiry(call.from_user.id)
        expiry = datetime.fromisoformat(expiry_raw).strftime("%d %b %Y  %H:%M")
        tier_key = get_latest_accepted_tier(call.from_user.id)
        invite_link = INVITE_LINKS.get(tier_key, "") if tier_key else ""
        txt, ents = build_mystatus_msg(True, expiry, invite_link)
    else:
        txt, ents = build_mystatus_msg(False)
    await call.message.answer(txt, entities=ents)


@router.callback_query(F.data.startswith("tier:"))
async def cb_tier_selected(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if is_user_blocked(call.from_user.id):
        await call.message.answer("🚫 Your account is restricted.", reply_markup=kb_blocked())
        return

    key = call.data.split(":", 1)[1]
    if key not in VIP_TIERS:
        return

    await state.update_data(tier=key)
    txt, ents = build_tier_msg(key)
    img = TIER_IMAGES.get(key, IMG_MENU)
    await edit_or_send_photo(call.bot, call, img, txt, ents, kb_pay(key))


@router.callback_query(F.data == "allgirls_browse")
async def cb_allgirls_browse(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    if is_user_blocked(call.from_user.id):
        await call.message.answer("🚫 Your account is restricted.", reply_markup=kb_blocked())
        return

    txt, ents = build_allgirls_browse_msg()
    img = TIER_IMAGES.get("allgirls", IMG_MENU)
    await edit_or_send_photo(call.bot, call, img, txt, ents, kb_allgirls_browse())


@router.callback_query(F.data.startswith("girl_noop:"))
async def cb_girl_noop(call: CallbackQuery):
    idx = int(call.data.split(":")[1])
    girl = GIRLS_LIST[idx - 1] if idx <= len(GIRLS_LIST) else "?"
    await call.answer(f"👆 To buy {girl}'s VIP — tap Buy Separate below!", show_alert=True)


@router.callback_query(F.data == "allgirls_buyall")
async def cb_allgirls_buyall(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if is_user_blocked(call.from_user.id):
        await call.message.answer("🚫 Your account is restricted.", reply_markup=kb_blocked())
        return

    await state.update_data(tier="allgirls_all")
    txt, ents = build_allgirls_all_msg()
    img = TIER_IMAGES.get("allgirls", IMG_MENU)
    await edit_or_send_photo(call.bot, call, img, txt, ents, kb_allgirls_pay("allgirls_all"))


@router.callback_query(F.data == "show_extra")
async def cb_show_extra(call: CallbackQuery):
    await call.answer()
    if is_user_blocked(call.from_user.id):
        await call.message.answer("🚫 Your account is restricted.", reply_markup=kb_blocked())
        return

    txt, ents = build_extra_service_msg(GIRLS_LIST)
    img = TIER_IMAGES.get("allgirls", IMG_MENU)
    await edit_or_send_photo(call.bot, call, img, txt, ents, kb_extra_service())
