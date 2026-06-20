from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InputMediaPhoto, BufferedInputFile

from config import IMG_MENU, STICKER_IDS
from db import get_all_admins


support_cooldown = {}
_photo_cache = {}


class Flow(StatesGroup):
    waiting_code     = State()
    support_subject  = State()
    support_body     = State()
    support_blocked  = State()
    block_user_id    = State()
    unblock_user_id  = State()
    waiting_girl_num = State()
    admin_broadcast    = State()
    admin_set_channels = State()
    admin_reply_ticket = State()
    use_commission     = State()
    # Give VIP manually
    admin_give_vip_uid  = State()
    admin_give_vip_days = State()
    # Live 2-way support chat
    live_chat_active    = State()
    admin_live_reply    = State()


def user_link(u):
    if u.username:
        return f'<a href="https://t.me/{u.username}">@{u.username}</a>'
    return f'<a href="tg://user?id={u.id}">Click Here</a>'


def _resolve_img(path):
    p = Path(path)
    if p.exists():
        return str(p)
    return str(IMG_MENU)


# ── Custom emoji error helpers ────────────────────────────────────────────────

def _is_emoji_err(exc: Exception) -> bool:
    s = str(exc)
    return "DOCUMENT_INVALID" in s or "custom_emoji" in s.lower()


def _drop_emoji_ents(entities):
    """Strip custom_emoji entities — fallback char is already in the text."""
    if not entities:
        return entities
    kept = [e for e in entities if e.type != "custom_emoji"]
    return kept or None


# ── Safe send helpers (retry without custom emoji on DOCUMENT_INVALID) ────────

async def safe_send_msg(bot, chat_id, text, entities=None, reply_markup=None, parse_mode=None):
    try:
        return await bot.send_message(
            chat_id, text, entities=entities,
            reply_markup=reply_markup, parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        if _is_emoji_err(e):
            return await bot.send_message(
                chat_id, text, entities=_drop_emoji_ents(entities),
                reply_markup=reply_markup, parse_mode=parse_mode,
            )
        raise


async def safe_answer(message, text, entities=None, reply_markup=None, parse_mode=None):
    try:
        return await message.answer(text, entities=entities, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if _is_emoji_err(e):
            return await message.answer(
                text, entities=_drop_emoji_ents(entities), reply_markup=reply_markup, parse_mode=parse_mode,
            )
        raise


async def safe_reply(message, text, entities=None, reply_markup=None):
    try:
        return await message.reply(text, entities=entities, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if _is_emoji_err(e):
            return await message.reply(
                text, entities=_drop_emoji_ents(entities), reply_markup=reply_markup,
            )
        raise


async def safe_edit_text(message, text, entities=None, reply_markup=None):
    try:
        return await message.edit_text(text, entities=entities, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if _is_emoji_err(e):
            return await message.edit_text(
                text, entities=_drop_emoji_ents(entities), reply_markup=reply_markup,
            )
        raise


# ── Photo helpers ─────────────────────────────────────────────────────────────

async def send_photo(bot, chat_id, image_path, caption=None, caption_entities=None,
                     reply_markup=None, parse_mode=None):
    img = _resolve_img(image_path)

    async def _do_send(photo, ents):
        m = await bot.send_photo(
            chat_id, photo=photo, caption=caption,
            caption_entities=ents, reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        return m

    async def _send_with_fallback(photo):
        try:
            return await _do_send(photo, caption_entities)
        except TelegramBadRequest as e:
            if _is_emoji_err(e):
                return await _do_send(photo, _drop_emoji_ents(caption_entities))
            raise

    fid = _photo_cache.get(img)
    if fid:
        try:
            return await _send_with_fallback(fid)
        except Exception:
            _photo_cache.pop(img, None)

    m = await _send_with_fallback(FSInputFile(img))
    if m.photo:
        _photo_cache[img] = m.photo[-1].file_id
    return m


async def edit_or_send_photo(bot, call, image_path, caption, caption_entities, reply_markup):
    img = _resolve_img(image_path)
    fid = _photo_cache.get(img)
    photo = fid if fid else FSInputFile(img)

    for ents in (caption_entities, _drop_emoji_ents(caption_entities)):
        try:
            result = await call.message.edit_media(
                InputMediaPhoto(media=photo, caption=caption, caption_entities=ents),
                reply_markup=reply_markup,
            )
            if not fid and result and result.photo:
                _photo_cache[img] = result.photo[-1].file_id
            return
        except TelegramBadRequest as e:
            if _is_emoji_err(e):
                continue
            break
        except Exception:
            break

    # Current message is text — edit it in place instead of sending new
    for ents in (caption_entities, _drop_emoji_ents(caption_entities)):
        pm = None if ents else "HTML"
        try:
            await call.message.edit_text(caption, parse_mode=pm, entities=ents,
                                         reply_markup=reply_markup)
            return
        except TelegramBadRequest as e:
            if _is_emoji_err(e):
                continue
            break
        except Exception:
            break

    # Last resort only — send new message
    try:
        await send_photo(bot, call.message.chat.id, img, caption=caption,
                         caption_entities=caption_entities, reply_markup=reply_markup)
    except Exception:
        await safe_send_msg(bot, call.message.chat.id, caption,
                            entities=caption_entities, reply_markup=reply_markup)


async def edit_message_photo_by_id(bot, chat_id, message_id, image_path,
                                    caption, caption_entities, reply_markup):
    img = _resolve_img(image_path)
    fid = _photo_cache.get(img)

    for ents in (caption_entities, _drop_emoji_ents(caption_entities)):
        try:
            photo = fid if fid else FSInputFile(img)
            result = await bot.edit_message_media(
                chat_id=chat_id, message_id=message_id,
                media=InputMediaPhoto(media=photo, caption=caption, caption_entities=ents),
                reply_markup=reply_markup,
            )
            if not fid and result and result.photo:
                _photo_cache[img] = result.photo[-1].file_id
            return True
        except TelegramBadRequest as e:
            if _is_emoji_err(e):
                continue
            return False
        except Exception:
            return False
    return False


async def send_sticker(bot, chat_id, name):
    fid = STICKER_IDS.get(name)
    if fid:
        try:
            await bot.send_sticker(chat_id, sticker=fid)
        except Exception:
            pass


async def restore_admin_panel(bot, chat_id: int, message_id, first_name: str):
    """Edit a stored message back to the admin panel (caption first, then text)."""
    if not message_id or not chat_id:
        return
    from messages import build_admin_msg
    from keyboards import kb_admin_panel
    txt, ents = build_admin_msg(first_name)
    for _ents in (ents, _drop_emoji_ents(ents)):
        try:
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption=txt, caption_entities=_ents, reply_markup=kb_admin_panel(),
            )
            return
        except TelegramBadRequest as e:
            if _is_emoji_err(e):
                continue
            break
        except Exception:
            break
    for _ents in (ents, _drop_emoji_ents(ents)):
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text=txt, entities=_ents, reply_markup=kb_admin_panel(),
            )
            return
        except TelegramBadRequest as e:
            if _is_emoji_err(e):
                continue
        except Exception:
            pass


async def notify_admins(bot, text, reply_markup=None):
    for admin_id in get_all_admins():
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            pass


async def notify_admins_photo(bot, photo_bytes, filename, caption):
    for admin_id in get_all_admins():
        try:
            file = BufferedInputFile(photo_bytes, filename=filename)
            await bot.send_photo(admin_id, photo=file, caption=caption, parse_mode="HTML")
        except Exception:
            pass


async def smart_edit(call, text: str, reply_markup=None, entities=None):
    parse_mode = None if entities else "HTML"
    for ents in ((entities, parse_mode), (_drop_emoji_ents(entities), parse_mode)):
        e_val, pm = ents
        try:
            await call.message.edit_caption(caption=text, parse_mode=pm,
                                            caption_entities=e_val, reply_markup=reply_markup)
            return
        except TelegramBadRequest as ex:
            if _is_emoji_err(ex):
                continue
            if "not modified" in str(ex).lower():
                return
        except Exception:
            pass
        try:
            await call.message.edit_text(text, parse_mode=pm,
                                         entities=e_val, reply_markup=reply_markup)
            return
        except TelegramBadRequest as ex:
            if _is_emoji_err(ex):
                continue
            if "not modified" in str(ex).lower():
                return
        except Exception:
            pass
        break
    await safe_answer(call.message, text, entities=entities, reply_markup=reply_markup,
                      parse_mode=parse_mode)
