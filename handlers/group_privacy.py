"""
Group Privacy Protection Module.
Ensures students receive exercise solutions privately in their Direct Message (DM)
when triggered inside a Telegram group or supergroup.
"""

import asyncio
import logging
from typing import Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, Message
from telegram.constants import ChatType, ParseMode
from telegram.error import Forbidden, BadRequest, TelegramError
from telegram.ext import ContextTypes

from config import GROUP_NOTICE_AUTO_DELETE_SECONDS, logger


async def auto_delete_message(bot, chat_id: int, message_id: int, delay_seconds: int = 8):
    """Background task to delete a temporary group notification after a delay."""
    await asyncio.sleep(delay_seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.debug("Successfully auto-deleted message %s in chat %s", message_id, chat_id)
    except (BadRequest, TelegramError) as e:
        # Ignore if message was already deleted or bot lacks delete permission
        logger.debug("Could not auto-delete message: %s", e)


async def send_solution_with_privacy(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    solution_text: str,
    deep_link_payload: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None
) -> None:
    """
    Sends math solution according to the Group Privacy Requirement:
    1. If in Private Chat: sends directly to the user.
    2. If in Group/Supergroup:
       - Tries to DM the student privately.
       - If successful: sends self-deleting confirmation notice in the group.
       - If failed (student hasn't started DM): sends deep-link button so student can unlock DM.
    """
    effective_chat = update.effective_chat
    effective_user = update.effective_user
    bot = context.bot

    if not effective_chat or not effective_user:
        return

    is_group = effective_chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]

    if not is_group:
        # Private chat: Send directly
        await effective_chat.send_message(
            text=solution_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        return

    # In a Group / Supergroup
    user_id = effective_user.id
    user_mention = effective_user.mention_html()
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    deep_link_url = f"https://t.me/{bot_username}?start={deep_link_payload}"

    try:
        # Attempt 1: Dispatch solution directly to student's DM
        await bot.send_message(
            chat_id=user_id,
            text=solution_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

        # Notify the group with a self-deleting message
        notice_text = (
            f"🔒 <b>{user_mention}</b> ដំណោះស្រាយត្រូវបានផ្ញើទៅកាន់សារផ្ទាល់ខ្លួនរបស់អ្នកហើយ 📩\n"
            f"<i>(សារជូនដំណឹងនេះនឹងលុបដោយស្វ័យប្រវត្តិក្នង {GROUP_NOTICE_AUTO_DELETE_SECONDS} វិនាទី)</i>"
        )
        group_notice: Message = await effective_chat.send_message(
            text=notice_text,
            parse_mode=ParseMode.HTML
        )

        # Schedule automatic deletion of the notification to keep group chat clean
        asyncio.create_task(
            auto_delete_message(
                bot,
                chat_id=effective_chat.id,
                message_id=group_notice.message_id,
                delay_seconds=GROUP_NOTICE_AUTO_DELETE_SECONDS
            )
        )

    except Forbidden:
        # Student has NEVER clicked /start on the bot in private DM, or blocked the bot
        fallback_text = (
            f"⚠️ <b>{user_mention}</b> បូតមិនទាន់អាចផ្ញើសារផ្ទាល់ខ្លួន (DM) ទៅកាន់អ្នកបានទេ "
            f"ដោយសារអ្នកមិនទាន់បានចុច <b>Start</b> ជាមួយបូតនៅឡើយ។\n\n"
            f"👉 សូមចុចប៊ូតុងខាងក្រោមដើម្បីបើកមើលដំណោះស្រាយក្នុងសារផ្ទាល់ខ្លួន៖"
        )
        fallback_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 បើកមើលដំណោះស្រាយក្នុង DM", url=deep_link_url)]
        ])

        fallback_msg: Message = await effective_chat.send_message(
            text=fallback_text,
            parse_mode=ParseMode.HTML,
            reply_markup=fallback_keyboard
        )

        # Auto-delete fallback notification after 35 seconds to keep group neat
        asyncio.create_task(
            auto_delete_message(
                bot,
                chat_id=effective_chat.id,
                message_id=fallback_msg.message_id,
                delay_seconds=35
            )
        )

    except Exception as e:
        logger.error("Error sending private solution: %s", e)
        # Fallback to direct button link
        fallback_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 មើលដំណោះស្រាយក្នុង DM", url=deep_link_url)]
        ])
        await effective_chat.send_message(
            text=f"📌 <b>{user_mention}</b> សូមចុចទីនេះដើម្បីទទួលបានដំណោះស្រាយ៖",
            parse_mode=ParseMode.HTML,
            reply_markup=fallback_keyboard
        )
