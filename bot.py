"""
Main Telegram Bot Entry Point.
Production-ready Math Bot for Derivative of Functions (ដេរីវេនៃអនុគមន៍).
Asynchronous architecture using python-telegram-bot v20+.
"""

import sys
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import (
    BOT_TOKEN,
    TEACHER_ADMIN_IDS,
    ENABLE_WEB_SERVER,
    PORT,
    logger
)
from database import db
from handlers.start_help import start_command, help_command
from handlers.exercises import (
    handle_callback_query,
    build_categories_keyboard,
    build_main_menu_keyboard
)
from handlers.search import handle_search_command, handle_text_message
from handlers.inline_query import inline_query_handler
from handlers.admin import (
    admin_dashboard,
    admin_stats,
    admin_sync_sheets,
    admin_add_exercise,
    admin_delete,
    admin_broadcast,
    admin_backup
)
from handlers.rag_handler import (
    ask_command,
    handle_document_upload,
    rag_status_command,
    rag_delete_command
)
from web_server import start_web_server



# Shortcuts for direct commands
async def formulas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct shortcut to view formula categories."""
    await update.effective_chat.send_message(
        "📐 <b>សូមជ្រើសរើសផ្នែកនៃរូបមន្តដេរីវេដែលចង់មើល៖</b>",
        parse_mode="HTML",
        reply_markup=build_categories_keyboard("form")
    )


async def exercises_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct shortcut to view exercise categories."""
    await update.effective_chat.send_message(
        "📝 <b>សូមជ្រើសរើសកម្រិត ឬផ្នែកនៃលំហាត់ដេរីវេ៖</b>",
        parse_mode="HTML",
        reply_markup=build_categories_keyboard("ex")
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for unhandled exceptions."""
    logger.error("Exception while handling an update: %s", context.error, exc_info=context.error)


def build_application() -> Application:
    """Build and configure the Telegram application."""
    if not BOT_TOKEN or "ABCdefGHI" in BOT_TOKEN:
        logger.error("ERROR: BOT_TOKEN is missing or not configured in .env file! Please set BOT_TOKEN.")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # Core student commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler(["formulas", "formula", "rules"], formulas_command))
    app.add_handler(CommandHandler(["exercises", "exercise", "practice"], exercises_command))
    app.add_handler(CommandHandler("search", handle_search_command))

    # Teacher admin commands
    app.add_handler(CommandHandler("admin", admin_dashboard))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("sync_sheets", admin_sync_sheets))
    app.add_handler(CommandHandler("add", admin_add_exercise))
    app.add_handler(CommandHandler("delete", admin_delete))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("backup", admin_backup))

    # Interactive inline buttons
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Telegram Inline Mode (@botusername keyword)
    app.add_handler(InlineQueryHandler(inline_query_handler))

    # RAG AI and conceptual question answering
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler(["rag_docs", "docs"], rag_status_command))
    app.add_handler(CommandHandler("rag_delete", rag_delete_command))

    # Natural text message search
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Teacher PDF document upload for RAG indexing
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_upload))


    # Error handling
    app.add_error_handler(error_handler)

    return app


async def main():
    """Main async entrypoint."""
    logger.info("Initializing Math Telegram Bot...")
    stats = db.get_stats()
    logger.info("Database loaded: %s formulas, %s exercises, %s users",
                stats["total_formulas"], stats["total_exercises"], stats["total_users"])

    if TEACHER_ADMIN_IDS:
        logger.info("Configured Teacher Admin IDs: %s", list(TEACHER_ADMIN_IDS))
    else:
        logger.warning("No TEACHER_ADMIN_ID configured! Admin commands are currently locked.")

    # Start lightweight HTTP server for Render/Koyeb healthcheck if enabled
    if ENABLE_WEB_SERVER:
        try:
            await start_web_server(PORT)
        except Exception as e:
            logger.warning("Could not start HTTP server on port %s: %s (Continuing bot polling)", PORT, e)

    # Initialize Telegram Application
    application = build_application()

    # Start Polling
    logger.info("Starting Telegram Bot long-polling...")
    async with application:
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        logger.info("Bot is active and listening for messages!")
        
        # Keep running until interrupted
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            logger.info("Stopping bot...")
            await application.updater.stop()
            await application.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped cleanly.")
