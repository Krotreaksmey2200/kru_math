"""
Search and Natural Message Handler.
Processes text messages, math keywords, exercise codes, and /search command.
Integrates with Group Privacy module so solutions in groups go to Private DM.
"""

from typing import List
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes

from database import db
from handlers.group_privacy import send_solution_with_privacy
from handlers.exercises import (
    format_formula_html,
    format_exercise_problem_html,
    format_exercise_solution_html,
    build_exercise_action_keyboard
)


async def handle_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search <query> command."""
    query = " ".join(context.args).strip() if context.args else ""
    if not query:
        await update.effective_chat.send_message(
            text="🔍 <b>សូមបញ្ចូលពាក្យដែលចង់ស្វែងរក៖</b>\nឧទាហរណ៍៖ <code>/search sin(x)</code> ឬ <code>/search លំហាត់១</code>",
            parse_mode=ParseMode.HTML
        )
        return

    await perform_search_and_reply(update, context, query)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ordinary text messages from users (auto keyword detection)."""
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()
    # Ignore bot commands (already handled by CommandHandlers)
    if text.startswith("/"):
        return

    await perform_search_and_reply(update, context, text)


async def perform_search_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    """Search database and respond with appropriate privacy precautions."""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    is_group = chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
    bot_info = await context.bot.get_me()

    # Log the search
    db.track_user(user.id, user.username, user.first_name, user.last_name)
    db.log_search(user.id, query)

    # 1. Direct check: Is this a direct request for a specific exercise code (e.g. "លំហាត់១", "ex1")?
    direct_ex = db.get_exercise_by_code(query)
    if direct_ex:
        solution_text = format_exercise_solution_html(direct_ex)
        if is_group:
            # Privacy Protection: Send solution to DM!
            await send_solution_with_privacy(
                update=update,
                context=context,
                solution_text=solution_text,
                deep_link_payload=f"ex_{direct_ex['id']}"
            )
            return
        else:
            # In DM: show exercise card with buttons
            kb = build_exercise_action_keyboard(direct_ex["id"], in_group=False)
            await chat.send_message(
                text=format_exercise_problem_html(direct_ex),
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
            return

    # 2. General Search across formulas and exercises
    results = db.search(query)
    matched_formulas = results.get("formulas", [])
    matched_exercises = results.get("exercises", [])

    if not matched_formulas and not matched_exercises:
        if not is_group:
            # In private chat, give friendly 'no results' feedback
            no_result_text = (
                f"🔎 មិនបានរកឃើញលទ្ធផលសម្រាប់ «<b>{query}</b>» ទេ។\n\n"
                "💡 <b>ពាក្យគន្លឹះដែលអ្នកអាចសាកល្បង៖</b>\n"
                "• <code>លំហាត់១</code> ដល់ <code>លំហាត់៨</code>\n"
                "• <code>sin</code>, <code>cos</code>, <code>tan</code>\n"
                "• <code>power rule</code>, <code>chain rule</code>\n"
                "• <code>ផលគុណ</code>, <code>ផលចែក</code>, <code>ឫស</code>\n"
                "• <code>e^x</code>, <code>ln</code>"
            )
            await chat.send_message(text=no_result_text, parse_mode=ParseMode.HTML)
        return

    # 3. Handling Group Search Results
    if is_group:
        # In a group, if exercises are found, provide deep links to view solutions privately
        buttons = []
        for ex in matched_exercises[:4]:
            url = f"https://t.me/{bot_info.username}?start=ex_{ex['id']}"
            buttons.append([InlineKeyboardButton(f"🔒 {ex.get('code', 'លំហាត់')}: {ex['title'][:20]}", url=url)])

        for f in matched_formulas[:2]:
            url = f"https://t.me/{bot_info.username}?start=form_{f['id']}"
            buttons.append([InlineKeyboardButton(f"📐 រូបមន្ត: {f['title_km'][:20]}", url=url)])

        reply_markup = InlineKeyboardMarkup(buttons)
        group_response = (
            f"🔍 រកឃើញលទ្ធផលចំនួន <b>{len(matched_formulas) + len(matched_exercises)}</b> សម្រាប់ «{query}»:\n"
            f"<i>(ដើម្បីរក្សាភាពឯកជន សូមចុចប៊ូតុងខាងក្រោមដើម្បីបើកមើលក្នុង DM)</i>"
        )
        await chat.send_message(text=group_response, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return

    # 4. Handling Private Chat Search Results
    # Display matched formulas as text with Render button
    for form in matched_formulas[:2]:
        msg_text = format_formula_html(form)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🖼 Render រូបភាពសមីការ (HD Card)", callback_data=f"form_render_{form['id']}")]
        ])
        await chat.send_message(text=msg_text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # Display matched exercises
    for ex in matched_exercises[:3]:
        kb = build_exercise_action_keyboard(ex["id"], in_group=False)
        await chat.send_message(
            text=format_exercise_problem_html(ex),
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )
