import asyncio
import logging
import sys
import traceback

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ErrorEvent

from config import BOT_TOKEN
from db import init_db, is_user_blocked, log_error, get_unnotified_errors, mark_errors_notified, get_expiring_vip_users, mark_vip_reminder_sent
from handlers import admin, callbacks, payments, start, support
from handlers import profile
from handlers import livechat
from keyboards import kb_back, kb_blocked
from utils import notify_admins

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


fallback_router = Router()


@fallback_router.message(StateFilter(None))
async def fallback(msg: Message, state: FSMContext):
    if is_user_blocked(msg.from_user.id):
        from config import MSG_ACCOUNT_RESTRICTED_BODY
        await msg.answer(f"🚫 {MSG_ACCOUNT_RESTRICTED_BODY}", reply_markup=kb_blocked())
    else:
        await msg.answer("Use /start to explore our VIP plans! 🔞", reply_markup=kb_back())


# ── VIP expiry reminder ───────────────────────────────────────────────────────
async def _expiry_reminder(bot: Bot):
    """Check once per hour; send reminder 3 days before VIP expiry."""
    while True:
        try:
            await asyncio.sleep(3600)
            for uid in get_expiring_vip_users(days_ahead=3):
                try:
                    await bot.send_message(
                        uid,
                        "⏳ <b>VIP Expiring Soon!</b>\n\n"
                        "Your VIP access expires in <b>3 days</b>.\n"
                        "Renew now to keep access to all premium content!\n\n"
                        "Use /start to purchase a new plan. 🔥",
                        parse_mode="HTML",
                    )
                    mark_vip_reminder_sent(uid)
                except Exception:
                    pass
        except Exception as e:
            log.error("Expiry reminder task crashed: %s", e)
            await asyncio.sleep(60)
# ─────────────────────────────────────────────────────────────────────────────


# ── NEW: background error monitor ────────────────────────────────────────────
async def _error_monitor(bot: Bot):
    while True:
        try:
            await asyncio.sleep(300)   # check every 5 min
            errors = get_unnotified_errors()
            if not errors:
                continue
            ids   = [e[0] for e in errors]
            text  = "🚨 <b>Bot Errors</b>\n\n"
            for eid, etype, emsg, created in errors[:5]:
                text += f"🔴 <b>{etype}</b>\n💬 {emsg[:150]}\n🕐 {created}\n\n"
            if len(errors) > 5:
                text += f"…and {len(errors)-5} more"
            await notify_admins(bot, text)
            mark_errors_notified(ids)
        except Exception as e:
            log.error("Error monitor crashed: %s", e)
            await asyncio.sleep(60)
# ────────────────────────────────────────────────────────────────────────────


async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # ── NEW: global error handler ─────────────────────────────────────────────
    @dp.errors()
    async def on_error(event: ErrorEvent):
        exc = event.exception
        tb  = traceback.format_exc()
        log.error("Unhandled: %s\n%s", exc, tb)
        log_error(type(exc).__name__, str(exc), tb[:2000])
        try:
            await notify_admins(bot,
                f"⚠️ <b>Bot Error</b>\n\n<b>{type(exc).__name__}</b>\n{str(exc)[:300]}")
        except Exception:
            pass
    # ─────────────────────────────────────────────────────────────────────────

    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(livechat.router)
    dp.include_router(payments.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)
    dp.include_router(callbacks.router)
    dp.include_router(fallback_router)

    log.info("Bot started")

    # ── start background tasks ───────────────────────────────────────────────
    monitor  = asyncio.create_task(_error_monitor(bot))
    reminder = asyncio.create_task(_expiry_reminder(bot))
    # ─────────────────────────────────────────────────────────────────────────

    retry_delay = 3
    while True:
        try:
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                polling_timeout=30,
            )
            break
        except KeyboardInterrupt:
            log.info("Stopped.")
            monitor.cancel()
            reminder.cancel()
            break
        except Exception as e:
            log.error(f"Polling crashed: {e}. Restarting in {retry_delay}s...")
            log_error("POLLING_CRASH", str(e), traceback.format_exc())
            try:
                await notify_admins(bot,
                    f"🚨 <b>Bot Crashed!</b>\n\n{str(e)[:300]}\n\nRestarting in {retry_delay}s…")
            except Exception:
                pass
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
