"""
Telegram Handler for LaTeX Math Rendering.
Provides /latex and /render commands, plus button callbacks for rendering formulas
as transparent stickers and KaTeX-compatible $ ... $ math text.
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
    """Handle /latex and /render commands with transparent sticker and KaTeX math."""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    # Extract user input
    formula_str = " ".join(context.args).strip() if context.args else ""

    if not formula_str:
        help_text = (
            "📐 <b>កម្មវិធី Render សមីការ LaTeX & Sticker ថ្លា (Transparent Math)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "លោកគ្រូ និងសិស្សអាចវាយកូដ LaTeX ឬរូបមន្តគណិតវិទ្យា/រូបវិទ្យា/គីមីវិទ្យា ដើម្បីឱ្យបូត Render ចេញជា <b>Sticker ថ្លា (Transparent)</b> និងអត្ថបទ KaTeX <code>$...$</code> បានភ្លាមៗ!\n\n"
            "📌 <b>របៀបប្រើប្រាស់៖</b>\n"
            "<code>/latex &lt;កូដ LaTeX ឬរូបមន្ត&gt;</code>\n\n"
            "💡 <b>ឧទាហរណ៍គំរូ (ចុច Copy ទៅវាយសាកល្បង)៖</b>\n"
            "• <code>/latex \\int_{0}^{1} (3x^2 - 2x + 4) dx = 4</code>\n"
            "• <code>/latex \\lim_{x \\to 0} \\frac{\\sin(5x)}{x} = 5</code>\n"
            "• <code>/latex x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}</code>\n"
            "• <code>/latex T = 2\\pi \\sqrt{\\frac{m}{k}}</code>\n"
            "• <code>/latex pH = -\\log[H_3O^+]</code>\n"
            "• <code>/latex z = r(\\cos\\theta + i\\sin\\theta)</code>"
        )
        await chat.send_message(help_text, parse_mode=ParseMode.HTML)
        return

    wait_msg = await chat.send_message("⏳ <i>កំពុង Render សមីការជា Sticker ថ្លា...</i>", parse_mode=ParseMode.HTML)

    try:
        escaped_code = html.escape(formula_str)

        # 1. Try sending as native Transparent WebP Sticker
        webp_bytes = render_latex_to_transparent_webp(formula_str)
        if webp_bytes:
            await chat.send_sticker(sticker=io.BytesIO(webp_bytes))
            await chat.send_message(
                f"📐 <b>សមីការ LaTeX (KaTeX Inline)៖</b>\n<code>${escaped_code}$</code>",
                parse_mode=ParseMode.HTML
            )
            try:
                await wait_msg.delete()
            except Exception:
                pass
            return

        # 2. Fallback to HD PNG photo
        png_bytes = await render_latex_to_png(formula_str)
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
    """Callback triggered by [🌟 មើលជា Sticker ថ្លា] button on a formula."""
    form = db.get_formula_by_id(form_id)
    if not form:
        await query.answer("រកមិនឃើញរូបមន្តនេះទេ!", show_alert=True)
        return

    formula_text = form.get("formula", "")
    await query.answer("⏳ កំពុង Render Sticker សមីការថ្លា...")
    chat = query.message.chat if query.message else None
    if not chat:
        return

    title = form.get("title_km", "រូបមន្ត")
    clean_eqs = clean_and_extract_equations(formula_text)
    katex_code = " \\\\ ".join(clean_eqs) if clean_eqs else formula_text

    # 1. Try sending as Transparent WebP Sticker
    webp_bytes = render_latex_to_transparent_webp(formula_text)
    if webp_bytes:
        try:
            await chat.send_sticker(sticker=io.BytesIO(webp_bytes))
            await chat.send_message(
                f"📐 <b>{title} (KaTeX Inline)៖</b>\n<code>${html.escape(katex_code)}$</code>",
                parse_mode=ParseMode.HTML
            )
            return
        except Exception as e:
            logger.warning("send_sticker failed for formula, falling back to photo: %s", e)

    # 2. Fallback to HD PNG Photo
    png_bytes = await render_latex_to_png(formula_text)
    if png_bytes:
        caption = f"📐 <b>{title}</b>\n<code>${html.escape(katex_code)}$</code>"
        await chat.send_photo(
            photo=io.BytesIO(png_bytes),
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    else:
        await query.answer("មិនអាច Render រូបភាពសម្រាប់រូបមន្តនេះទេ!", show_alert=True)


async def render_exercise_callback(query, ex_id: str):
    """Callback triggered by [🌟 មើលជា Sticker ថ្លា] button on an exercise."""
    ex = db.get_exercise_by_id(ex_id)
    if not ex:
        await query.answer("រកមិនឃើញលំហាត់នេះទេ!", show_alert=True)
        return

    math_text = ex.get("final_answer") or ex.get("problem") or ""
    await query.answer("⏳ កំពុង Render Sticker សមីការថ្លា...")
    chat = query.message.chat if query.message else None
    if not chat:
        return

    code = ex.get("code", "លំហាត់")
    title = ex.get("title", "")
    clean_eqs = clean_and_extract_equations(math_text)
    katex_code = " \\\\ ".join(clean_eqs) if clean_eqs else math_text

    # 1. Try sending as Transparent WebP Sticker
    webp_bytes = render_latex_to_transparent_webp(math_text)
    if webp_bytes:
        try:
            await chat.send_sticker(sticker=io.BytesIO(webp_bytes))
            await chat.send_message(
                f"📝 <b>{code}៖ {title} (KaTeX Inline)៖</b>\n<code>${html.escape(katex_code)}$</code>",
                parse_mode=ParseMode.HTML
            )
            return
        except Exception as e:
            logger.warning("send_sticker failed for exercise, falling back to photo: %s", e)

    # 2. Fallback to HD PNG Photo
    png_bytes = await render_latex_to_png(math_text)
    if png_bytes:
        caption = f"📝 <b>{code}៖ {title}</b>\n<code>${html.escape(katex_code)}$</code>"
        await chat.send_photo(
            photo=io.BytesIO(png_bytes),
            caption=caption,
            parse_mode=ParseMode.HTML
        )
    else:
        await query.answer("មិនអាច Render រូបភាពសម្រាប់លំហាត់នេះទេ!", show_alert=True)
