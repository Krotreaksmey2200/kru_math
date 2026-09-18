"""
Telegram Handler for LaTeX Math Rendering.
Provides /latex and /render commands, plus button callbacks for rendering
both Khmer text and LaTeX equations on a clean white background.
"""

import io
import html
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from latex_renderer import (
    render_latex_to_png,
    render_latex_to_transparent_webp,
    clean_and_extract_equations
)
from database import db

logger = logging.getLogger("MathBot.LaTeXHandler")


async def latex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /latex and /render commands with white background photo and KaTeX text."""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    # Extract user input
    formula_str = " ".join(context.args).strip() if context.args else ""

    if not formula_str:
        help_text = (
            "📐 <b>កម្មវិធី Render សមីការ LaTeX & អក្សរខ្មែរ (ផ្ទៃពណ៌ស HD)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "លោកគ្រូ និងសិស្សអាចវាយកូដ LaTeX ឬលាយជាមួយអក្សរខ្មែរ ដើម្បីឱ្យបូត Render ចេញជារូបភាព **ផ្ទៃពណ៌សស្អាត** និងអត្ថបទ KaTeX <code>$...$</code> បានភ្លាមៗ!\n\n"
            "📌 <b>របៀបប្រើប្រាស់៖</b>\n"
            "<code>/latex &lt;អក្សរខ្មែរ ឬកូដ LaTeX&gt;</code>\n\n"
            "💡 <b>ឧទាហរណ៍គំរូ (ចុច Copy ទៅវាយសាកល្បង)៖</b>\n"
            "• <code>/latex សាលារៀន \\int x^3 dx</code>\n"
            "• <code>/latex \\int_{0}^{1} (3x^2 - 2x + 4) dx = 4</code>\n"
            "• <code>/latex \\lim_{x \\to 0} \\frac{\\sin(5x)}{x} = 5</code>\n"
            "• <code>/latex x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}</code>\n"
            "• <code>/latex ទម្រង់ពីជគណិត៖ z = a + bi</code>"
        )
        await chat.send_message(help_text, parse_mode=ParseMode.HTML)
        return

    wait_msg = await chat.send_message("⏳ <i>កំពុង Render រូបភាពសមីការផ្ទៃពណ៌ស...</i>", parse_mode=ParseMode.HTML)

    try:
        escaped_code = html.escape(formula_str)

        # 1. Render HD photo with clean white background (#FFFFFF)
        png_bytes = await render_latex_to_png(formula_str, bg_color="#FFFFFF")
        if png_bytes:
            caption = f"📐 <b>សមីការ LaTeX (KaTeX Inline)៖</b>\n<code>${escaped_code}$</code>"
            await chat.send_photo(
                photo=io.BytesIO(png_bytes),
                caption=caption,
                parse_mode=ParseMode.HTML
            )
            try:
                await wait_msg.delete()
            except Exception:
                pass
            return
        else:
            await wait_msg.edit_text(
                "⚠️ <b>មិនអាច Render សមីការនេះបានទេ៖</b>\n"
                "សូមពិនិត្យមើល syntax នៃកូដ LaTeX ឡើងវិញ (ឧទាហរណ៍៖ <code>/latex \\frac{a}{b}</code>)។",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error("Error in latex_command: %s", e)
        await wait_msg.edit_text("❌ មានបញ្ហាក្នុងដំណើរការ Render សូមព្យាយាមម្ដងទៀត។")


async def render_formula_callback(query, form_id: str):
    """Callback triggered by [🖼 មើលរូបភាពសមីការ (Render ផ្ទៃស)] button on a formula."""
    form = db.get_formula_by_id(form_id)
    if not form:
        await query.answer("រកមិនឃើញរូបមន្តនេះទេ!", show_alert=True)
        return

    await query.answer("⏳ កំពុង Render រូបភាពសមីការផ្ទៃពណ៌ស...")
    chat = query.message.chat if query.message else None
    if not chat:
        return

    title = form.get("title_km", "រូបមន្ត")
    from latex_renderer import render_formula_card
    png_bytes = render_formula_card(
        title_km=title,
        formula_raw=form.get("formula", ""),
        example_raw=form.get("example", ""),
        title_en=form.get("title_en", ""),
        explanation=form.get("explanation", "")
    )
    if png_bytes:
        caption = f"📐 <b>{title}</b>"
        await chat.send_photo(
            photo=io.BytesIO(png_bytes),
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    else:
        await query.answer("មិនអាច Render រូបភាពសម្រាប់រូបមន្តនេះទេ!", show_alert=True)


async def render_exercise_callback(query, ex_id: str):
    """Callback triggered by [🖼 មើលរូបភាពសមីការ (Render ផ្ទៃស)] button on an exercise."""
    ex = db.get_exercise_by_id(ex_id)
    if not ex:
        await query.answer("រកមិនឃើញលំហាត់នេះទេ!", show_alert=True)
        return

    await query.answer("⏳ កំពុង Render រូបភាពសមីការផ្ទៃពណ៌ស...")
    chat = query.message.chat if query.message else None
    if not chat:
        return

    code = ex.get("code", "លំហាត់")
    title = ex.get("title", "")
    steps = ex.get("solution_steps", [])
    sol = "\n".join(steps)
    if ex.get("final_answer"):
        sol += "\nដូចនេះ៖ " + ex.get("final_answer")

    from latex_renderer import render_exercise_card
    png_bytes = render_exercise_card(
        code=code,
        title=title,
        difficulty=ex.get("difficulty", "មធ្យម"),
        problem_raw=ex.get("problem", ""),
        solution_raw=sol
    )
    if png_bytes:
        caption = f"📝 <b>{code}៖ {title}</b>"
        await chat.send_photo(
            photo=io.BytesIO(png_bytes),
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    else:
        await query.answer("មិនអាច Render រូបភាពសម្រាប់លំហាត់នេះទេ!", show_alert=True)
