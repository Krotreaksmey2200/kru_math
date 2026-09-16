"""
Telegram Inline Query Handler.
Allows students to type `@botusername <keyword>` inside ANY Telegram chat/group
and view private instant previews of derivative formulas and step-by-step exercise solutions.
"""

from uuid import uuid4
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import db
from handlers.exercises import format_formula_html, format_exercise_solution_html


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries (@botusername keyword)."""
    inline_query = update.inline_query
    if not inline_query:
        return

    query = inline_query.query.strip()
    user = inline_query.from_user
    db.track_user(user.id, user.username, user.first_name, user.last_name)

    articles = []

    if not query:
        # If user hasn't typed anything yet, show popular formulas and exercises
        formulas = db.get_formulas()[:5]
        exercises = db.get_exercises()[:5]

        for f in formulas:
            articles.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"📐 {f['title_km']}",
                    description=f"រូបមន្ត៖ {f['formula']}",
                    input_message_content=InputTextMessageContent(
                        format_formula_html(f),
                        parse_mode=ParseMode.HTML
                    )
                )
            )

        for ex in exercises:
            articles.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"📝 {ex.get('code', 'លំហាត់')}៖ {ex['title']}",
                    description=f"{ex['problem']}",
                    input_message_content=InputTextMessageContent(
                        format_exercise_solution_html(ex),
                        parse_mode=ParseMode.HTML
                    )
                )
            )
    else:
        # Search for query
        results = db.search(query)
        formulas = results.get("formulas", [])[:10]
        exercises = results.get("exercises", [])[:10]

        for f in formulas:
            articles.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"📐 {f['title_km']}",
                    description=f"រូបមន្ត៖ {f['formula']}",
                    input_message_content=InputTextMessageContent(
                        format_formula_html(f),
                        parse_mode=ParseMode.HTML
                    )
                )
            )

        for ex in exercises:
            articles.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"🎯 {ex.get('code', 'លំហាត់')}៖ {ex['title']}",
                    description=f"ចម្លើយ៖ {ex.get('final_answer', '')} | {ex['problem']}",
                    input_message_content=InputTextMessageContent(
                        format_exercise_solution_html(ex),
                        parse_mode=ParseMode.HTML
                    )
                )
            )

    # If no results found, return an instructional item
    if not articles:
        articles.append(
            InlineQueryResultArticle(
                id="no_results",
                title="🔍 រកមិនឃើញលទ្ធផលទេ (No Results)",
                description=f"មិនមានលំហាត់ ឬរូបមន្តត្រូវនឹង «{query}» ទេ",
                input_message_content=InputTextMessageContent(
                    f"🔎 មិនមានលទ្ធផលសម្រាប់ «<b>{query}</b>» ទេ។ សាកល្បងពាក្យគន្លឹះដូចជា៖ <code>sin</code>, <code>cos</code>, <code>power</code>, <code>លំហាត់១</code>",
                    parse_mode=ParseMode.HTML
                )
            )
        )

    # is_personal=True ensures queries are cached per individual student
    await inline_query.answer(articles, cache_time=5, is_personal=True)
