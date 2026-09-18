"""
Exercises and Formulas Presentation Module.
Handles navigation menus, formula views, exercise lists, hints, and step-by-step solutions.
"""

import re
import json
from typing import Optional, List, Dict, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes

from database import db
from handlers.group_privacy import send_solution_with_privacy


def wrap_math_latex(text: str) -> str:
    """Wraps math formulas and equations with $ ... $ for KaTeX / Telegram Web rendering."""
    if not text:
        return text

    lines = text.splitlines()
    out_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out_lines.append("")
            continue

        if stripped.startswith("$") and stripped.endswith("$"):
            out_lines.append(f"<code>{stripped}</code>")
            continue

        if any(c in stripped for c in "=+-*/^<>\\()|[]{}_∫√²³π"):
            # Check for label with colon, e.g. "• ទម្រង់ពីជគណិត៖ ..."
            m1 = re.match(r'^(.*?[៖:]\s*)(.+)$', stripped)
            if m1:
                prefix, math_part = m1.group(1), m1.group(2).strip()
                out_lines.append(f"{prefix}<code>${math_part}$</code>")
                continue

            # Check for Khmer words at beginning before equation, e.g. "គណនា y = ..."
            m2 = re.match(r'^([•\-\*\s]*[\u1780-\u17FF\s]+)\s+([a-zA-Z0-9\\].*)$', stripped)
            if m2:
                prefix, math_part = m2.group(1).strip(), m2.group(2).strip()
                out_lines.append(f"{prefix} <code>${math_part}$</code>")
                continue

            out_lines.append(f"<code>${stripped}$</code>")
        else:
            out_lines.append(line)

    return "\n".join(out_lines)



def format_formula_html(form: Dict[str, Any]) -> str:
    """Format a formula item into a clean, modern HTML message with $...$ KaTeX math."""
    title_km = form.get("title_km", "")
    title_en = form.get("title_en", "")
    formula = form.get("formula", "")
    explanation = form.get("explanation", "")
    example = form.get("example", "")

    wrapped_formula = wrap_math_latex(formula)
    wrapped_example = wrap_math_latex(example)

    msg = (
        f"📐 <b>{title_km}</b>\n"
        f"<i>({title_en})</i>\n\n"
        f"📌 <b>រូបមន្ត (Formula)៖</b>\n"
        f"{wrapped_formula}\n\n"
    )
    if explanation:
        msg += f"💡 <b>ពន្យល់៖</b> {explanation}\n\n"
    if example:
        msg += f"📝 <b>ឧទាហរណ៍៖</b>\n{wrapped_example}\n"

    return msg


def format_exercise_problem_html(ex: Dict[str, Any]) -> str:
    """Format exercise statement with $...$ KaTeX math without showing the full solution."""
    code = ex.get("code", "")
    title = ex.get("title", "")
    problem = ex.get("problem", "")
    difficulty = ex.get("difficulty", "មធ្យម")

    wrapped_problem = wrap_math_latex(problem)

    msg = (
        f"📝 <b>{code}៖ {title}</b>\n"
        f"📊 <b>កម្រិត៖</b> {difficulty}\n\n"
        f"❓ <b>ប្រធានលំហាត់៖</b>\n"
        f"{wrapped_problem}\n\n"
        f"<i>ចុចប៊ូតុងខាងក្រោមដើម្បីមើលតម្រុយ ឬដំណោះស្រាយលម្អិត។</i>"
    )
    return msg


def format_exercise_solution_html(ex: Dict[str, Any]) -> str:
    """Format full step-by-step exercise solution with $...$ KaTeX math."""
    code = ex.get("code", "")
    title = ex.get("title", "")
    problem = ex.get("problem", "")
    steps = ex.get("solution_steps", [])
    final_answer = ex.get("final_answer", "")

    wrapped_problem = wrap_math_latex(problem)

    msg = (
        f"🎯 <b>ដំណោះស្រាយលម្អិត៖ {code}</b>\n"
        f"📘 <b>ប្រធានបទ៖</b> {title}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>ប្រធាន៖</b>\n{wrapped_problem}\n\n"
    )

    if steps:
        msg += "📋 <b>ដំណើរការដោះស្រាយ៖</b>\n"
        for step in steps:
            msg += f"\n{step}\n"

    if final_answer:
        wrapped_answer = wrap_math_latex(final_answer)
        msg += f"\n━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"✅ <b>ចម្លើយចុងក្រោយ៖</b>\n{wrapped_answer}\n"

    return msg


from config import is_admin


def build_main_menu_keyboard(user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Main navigation keyboard supporting Math, Physics, and Chemistry."""
    buttons = [
        [
            InlineKeyboardButton("📐 គណិតវិទ្យា", callback_data="subj_math"),
            InlineKeyboardButton("⚡️ រូបវិទ្យា", callback_data="subj_physics"),
            InlineKeyboardButton("🧪 គីមីវិទ្យា", callback_data="subj_chem"),
        ],
        [
            InlineKeyboardButton("📐 រូបមន្ត (Formulas)", callback_data="menu_formulas"),
            InlineKeyboardButton("📝 លំហាត់ (Exercises)", callback_data="menu_exercises")
        ],
        [
            InlineKeyboardButton("🔍 ស្វែងរក (Search)", callback_data="menu_search"),
            InlineKeyboardButton("🤖 សួរសំណួរផ្សេ២😁", callback_data="menu_rag_help")
        ],
        [
            InlineKeyboardButton("ℹ️ ជំនួយ & របៀបប្រើ (Help)", callback_data="menu_help")
        ]
    ]

    # Show Admin Dashboard button if the user is the teacher
    if user_id and is_admin(user_id):
        buttons.append([
            InlineKeyboardButton("👨‍🏫 ផ្ទាំងគ្រប់គ្រងលោកគ្រូ (Admin Dashboard)", callback_data="admin_dashboard_cb")
        ])

    return InlineKeyboardMarkup(buttons)



def build_categories_keyboard(prefix: str, subject: str = "math", page: int = 1, page_size: int = 8) -> InlineKeyboardMarkup:
    """Keyboard for selecting a lesson category with subject switcher tabs and pagination."""
    categories = db.get_categories(subject=subject)
    total_cats = len(categories)
    total_pages = max(1, (total_cats + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_cats = categories[start_idx:end_idx]

    # Subject switcher tabs at the top
    math_tab = "✅ 📐 គណិត" if subject == "math" else "📐 គណិត"
    phys_tab = "✅ ⚡️ រូប" if subject == "physics" else "⚡️ រូប"
    chem_tab = "✅ 🧪 គីមី" if subject == "chem" else "🧪 គីមី"

    buttons = [
        [
            InlineKeyboardButton(math_tab, callback_data=f"{prefix}_subj_math"),
            InlineKeyboardButton(phys_tab, callback_data=f"{prefix}_subj_physics"),
            InlineKeyboardButton(chem_tab, callback_data=f"{prefix}_subj_chem"),
        ]
    ]

    for cat in page_cats:
        name = cat["name_km"]
        buttons.append([InlineKeyboardButton(f"📘 {name}", callback_data=f"{prefix}_cat_{cat['id']}")])

    # Navigation buttons if multiple pages
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton("⬅️ មុន", callback_data=f"{prefix}_p_{subject}_{page - 1}"))
        nav_row.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton("បន្ទាប់ ➡️", callback_data=f"{prefix}_p_{subject}_{page + 1}"))
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("🏠 ម៉ឺនុយដើម (Home)", callback_data="menu_main")])
    return InlineKeyboardMarkup(buttons)


def build_formulas_list_keyboard(category_id: str) -> InlineKeyboardMarkup:
    """Keyboard listing formulas in a selected category."""
    cat = db.get_category_by_id(category_id)
    subject = cat.get("subject", "math") if cat else "math"
    formulas = db.get_formulas(category_id)
    buttons = []
    for f in formulas:
        buttons.append([InlineKeyboardButton(f"📐 {f['title_km']}", callback_data=f"form_view_{f['id']}")])
    buttons.append([InlineKeyboardButton("🔙 ត្រឡប់ទៅបញ្ជីមេរៀន", callback_data=f"form_subj_{subject}")])
    return InlineKeyboardMarkup(buttons)


def build_exercises_list_keyboard(category_id: str) -> InlineKeyboardMarkup:
    """Keyboard listing exercises in a selected category."""
    cat = db.get_category_by_id(category_id)
    subject = cat.get("subject", "math") if cat else "math"
    exercises = db.get_exercises(category_id)
    buttons = []
    for ex in exercises:
        btn_text = f"📝 {ex.get('code', 'លំហាត់')}: {ex['title'][:22]}..." if len(ex['title']) > 22 else f"📝 {ex.get('code', 'លំហាត់')}: {ex['title']}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"ex_view_{ex['id']}")])
    buttons.append([InlineKeyboardButton("🔙 ត្រឡប់ទៅបញ្ជីមេរៀន", callback_data=f"ex_subj_{subject}")])
    return InlineKeyboardMarkup(buttons)


def build_exercise_action_keyboard(exercise_id: str, in_group: bool = False, bot_username: str = "") -> InlineKeyboardMarkup:
    """Action buttons for an exercise problem."""
    buttons = []
    if in_group:
        # If viewed inside a group, the solution button directs to DM for privacy
        dm_url = f"https://t.me/{bot_username}?start=ex_{exercise_id}" if bot_username else "#"
        buttons.append([InlineKeyboardButton("🔒 មើលដំណោះស្រាយក្នុង DM", url=dm_url)])
    else:
        buttons.append([
            InlineKeyboardButton("💡 មើលតម្រុយ (Hint)", callback_data=f"ex_hint_{exercise_id}"),
            InlineKeyboardButton("✅ មើលដំណោះស្រាយ (Solution)", callback_data=f"ex_sol_{exercise_id}")
        ])
        buttons.append([
            InlineKeyboardButton("🖼 មើលរូបភាពសមីការ (Render ផ្ទៃស)", callback_data=f"ex_render_{exercise_id}")
        ])
    buttons.append([InlineKeyboardButton("🔙 ត្រឡប់ក្រោយ (Back)", callback_data="menu_exercises")])
    return InlineKeyboardMarkup(buttons)


# --- Callback Query Handlers ---

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router for all inline button callbacks."""
    query = update.callback_query
    if not query:
        return

    data = query.data
    user = query.from_user
    chat = query.message.chat if query.message else None
    is_group = chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] if chat else False

    # Track user activity
    db.track_user(user.id, user.username, user.first_name, user.last_name)

    # 1. Main Menu
    if data == "menu_main":
        await query.answer()
        welcome_text = (
            "👋 <b>សូមស្វាគមន៍មកកាន់បូត គ្រូបង្រៀនវិទ្យាសាស្ត្រទី១២ (បាក់ឌុប)!</b> 🎓\n\n"
            "ជ្រើសរើសមុខវិជ្ជាខាងក្រោមដើម្បីសិក្សារូបមន្ត ឬដោះស្រាយលំហាត់៖\n"
            "• 📐 <b>គណិតវិទ្យា</b> • ⚡️ <b>រូបវិទ្យា</b> • 🧪 <b>គីមីវិទ្យា</b>"
        )
        await query.edit_message_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_main_menu_keyboard(user.id)
        )

    # Direct Subject selection from main menu
    elif data in ["subj_math", "subj_physics", "subj_chem"]:
        await query.answer()
        subj_code = data.replace("subj_", "")
        subj_name = "គណិតវិទ្យា" if subj_code == "math" else ("រូបវិទ្យា" if subj_code == "physics" else "គីមីវិទ្យា")
        text = f"📚 <b>សូមជ្រើសរើសមេរៀន{subj_name}ថ្នាក់ទី១២ (បាក់ឌុប)៖</b>"
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_categories_keyboard("form", subject=subj_code, page=1)
        )

    # 2. Formulas Menu (Categories)
    elif data == "menu_formulas":
        await query.answer()
        text = "📐 <b>សូមជ្រើសរើសមុខវិជ្ជា និងមេរៀនដែលចង់មើលរូបមន្ត៖</b>"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=build_categories_keyboard("form", subject="math", page=1))

    # Subject Tabs within Formulas
    elif data in ["form_subj_math", "form_subj_physics", "form_subj_chem"]:
        await query.answer()
        subj_code = data.replace("form_subj_", "")
        subj_name = "គណិតវិទ្យា" if subj_code == "math" else ("រូបវិទ្យា" if subj_code == "physics" else "គីមីវិទ្យា")
        text = f"📐 <b>សូមជ្រើសរើសមេរៀន{subj_name}ដែលចង់មើលរូបមន្ត៖</b>"
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_categories_keyboard("form", subject=subj_code, page=1)
        )

    # Pagination for formulas
    elif data.startswith("form_p_"):
        await query.answer()
        parts = data.split("_")
        subj_code = parts[2]
        page_num = int(parts[3])
        subj_name = "គណិតវិទ្យា" if subj_code == "math" else ("រូបវិទ្យា" if subj_code == "physics" else "គីមីវិទ្យា")
        text = f"📐 <b>សូមជ្រើសរើសមេរៀន{subj_name}ដែលចង់មើលរូបមន្ត៖</b>"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=build_categories_keyboard("form", subject=subj_code, page=page_num))

    elif data.startswith("form_page_"):
        await query.answer()
        page_num = int(data.replace("form_page_", ""))
        text = "📐 <b>សូមជ្រើសរើសមេរៀនដែលចង់មើលរូបមន្ត៖</b>"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=build_categories_keyboard("form", subject="math", page=page_num))

    # 3. View Formulas in Category
    elif data.startswith("form_cat_"):
        await query.answer()
        cat_id = data.replace("form_cat_", "")
        formulas = db.get_formulas(cat_id)
        if formulas:
            text = "📐 <b>ជ្រើសរើសរូបមន្តជាក់លាក់ដើម្បីមើលការពន្យល់ និងឧទាហរណ៍៖</b>"
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=build_formulas_list_keyboard(cat_id))
        else:
            cat_obj = db.get_category_by_id(cat_id)
            cat_name = cat_obj["name_km"] if cat_obj else "មេរៀននេះ"
            text = (
                f"📐 <b>{cat_name}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "<i>បច្ចុប្បន្នមិនទាន់មានរូបមន្តដែលបានបញ្ចូលក្នុង Database នៅឡើយទេ។</i>\n\n"
                "💡 <b>ប្អូនៗអាចសួរ AI អំពីក្បួន និងរូបមន្តមេរៀននេះបានភ្លាមៗ៖</b>\n"
                f"👉 វាយ៖ <code>/ask តើរូបមន្តសំខាន់ៗក្នុង {cat_name} មានអ្វីខ្លះ?</code>"
            )
            back_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 សួរ AI លើមេរៀននេះ", callback_data="menu_rag_help")],
                [InlineKeyboardButton("🔙 ត្រឡប់ទៅបញ្ជីមេរៀន", callback_data="menu_formulas")]
            ])
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    # 4. View Specific Formula
    elif data.startswith("form_view_"):
        await query.answer()
        form_id = data.replace("form_view_", "")
        form = db.get_formula_by_id(form_id)
        if form:
            from latex_renderer import render_formula_card
            title_km = form.get("title_km", "")
            formula_raw = form.get("formula", "")
            example_raw = form.get("example", "")
            explanation = form.get("explanation", "")

            back_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ត្រឡប់ក្រោយ (Back)", callback_data=f"form_cat_{form.get('category_id', 'lesson_3')}")]
            ])

            # Render complete card on white background with both Khmer & LaTeX
            png_bytes = render_formula_card(title_km, formula_raw, example_raw)
            if png_bytes and chat:
                caption = f"📐 <b>{title_km}</b>\n"
                if explanation:
                    caption += f"\n💡 <b>ពន្យល់៖</b> {explanation}"
                import io
                await chat.send_photo(
                    photo=io.BytesIO(png_bytes),
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=back_kb
                )
                try:
                    await query.message.delete()
                except Exception:
                    pass
            else:
                msg_text = format_formula_html(form)
                await query.edit_message_text(msg_text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    # 5. Exercises Menu (Categories)
    elif data == "menu_exercises":
        await query.answer()
        text = "📝 <b>សូមជ្រើសរើសមុខវិជ្ជា និងមេរៀនដែលចង់អនុវត្តលំហាត់៖</b>"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=build_categories_keyboard("ex", subject="math", page=1))

    # Subject Tabs within Exercises
    elif data in ["ex_subj_math", "ex_subj_physics", "ex_subj_chem"]:
        await query.answer()
        subj_code = data.replace("ex_subj_", "")
        subj_name = "គណិតវិទ្យា" if subj_code == "math" else ("រូបវិទ្យា" if subj_code == "physics" else "គីមីវិទ្យា")
        text = f"📝 <b>សូមជ្រើសរើសមេរៀន{subj_name}ដែលចង់អនុវត្តលំហាត់៖</b>"
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_categories_keyboard("ex", subject=subj_code, page=1)
        )

    # Pagination for exercises
    elif data.startswith("ex_p_"):
        await query.answer()
        parts = data.split("_")
        subj_code = parts[2]
        page_num = int(parts[3])
        subj_name = "គណិតវិទ្យា" if subj_code == "math" else ("រូបវិទ្យា" if subj_code == "physics" else "គីមីវិទ្យា")
        text = f"📝 <b>សូមជ្រើសរើសមេរៀន{subj_name}ដែលចង់អនុវត្តលំហាត់៖</b>"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=build_categories_keyboard("ex", subject=subj_code, page=page_num))

    elif data.startswith("ex_page_"):
        await query.answer()
        page_num = int(data.replace("ex_page_", ""))
        text = "📝 <b>សូមជ្រើសរើសមេរៀនដែលចង់អនុវត្តលំហាត់៖</b>"
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=build_categories_keyboard("ex", subject="math", page=page_num))

    # 6. View Exercises in Category
    elif data.startswith("ex_cat_"):
        await query.answer()
        cat_id = data.replace("ex_cat_", "")
        exercises = db.get_exercises(cat_id)
        if exercises:
            text = "📝 <b>ជ្រើសរើសលំហាត់ដើម្បីអនុវត្ត និងមើលដំណោះស្រាយ៖</b>"
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=build_exercises_list_keyboard(cat_id))
        else:
            cat_obj = next((c for c in db.get_categories() if c["id"] == cat_id), None)
            cat_name = cat_obj["name_km"] if cat_obj else "មេរៀននេះ"
            text = (
                f"📝 <b>{cat_name}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "<i>មិនទាន់មានលំហាត់ក្នុង Database សម្រាប់មេរៀននេះនៅឡើយទេ។</i>\n\n"
                "💡 <b>ប្អូនៗអាចសុំឱ្យ AI បង្កើតលំហាត់ប្រឡងបាក់ឌុប និងដំណោះស្រាយបានភ្លាមៗ៖</b>\n"
                f"👉 វាយ៖ <code>/ask សូមផ្តល់លំហាត់ ១ លើ {cat_name} ព្រមទាំងដំណោះស្រាយលម្អិត</code>"
            )
            back_kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 សួរ AI លើមេរៀននេះ", callback_data="menu_rag_help")],
                [InlineKeyboardButton("🔙 ត្រឡប់ទៅបញ្ជីមេរៀន", callback_data="menu_exercises")]
            ])
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    elif data == "noop":
        await query.answer()
        return

    # 7. View Exercise Problem
    elif data.startswith("ex_view_"):
        await query.answer()
        ex_id = data.replace("ex_view_", "")
        ex = db.get_exercise_by_id(ex_id)
        if ex:
            bot_info = await context.bot.get_me()
            msg_text = format_exercise_problem_html(ex)
            kb = build_exercise_action_keyboard(ex_id, in_group=is_group, bot_username=bot_info.username)
            await query.edit_message_text(msg_text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # 8. View Exercise Hint
    elif data.startswith("ex_hint_"):
        ex_id = data.replace("ex_hint_", "")
        ex = db.get_exercise_by_id(ex_id)
        if ex:
            hint_text = ex.get("hints") or "មិនមានតម្រុយបន្ថែមសម្រាប់លំហាត់នេះទេ។"
            await query.answer(f"💡 តម្រុយ៖ {hint_text}", show_alert=True)

    # 9. View Exercise Solution (Respecting Privacy)
    elif data.startswith("ex_sol_"):
        await query.answer()
        ex_id = data.replace("ex_sol_", "")
        ex = db.get_exercise_by_id(ex_id)
        if ex:
            solution_text = format_exercise_solution_html(ex)
            if is_group:
                # Group Privacy: Send to student's DM!
                back_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ត្រឡប់ទៅម៉ឺនុយលំហាត់", callback_data="menu_exercises")]
                ])
                await send_solution_with_privacy(
                    update=update,
                    context=context,
                    solution_text=solution_text,
                    deep_link_payload=f"ex_{ex_id}",
                    reply_markup=back_kb
                )
            else:
                # Private chat: Edit current message to show full solution
                back_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("❓ មើលប្រធានឡើងវិញ (Problem)", callback_data=f"ex_view_{ex_id}")],
                    [InlineKeyboardButton("🔙 ត្រឡប់ទៅបញ្ជីលំហាត់", callback_data=f"ex_cat_{ex.get('category_id', 'basic')}")]
                ])
                await query.edit_message_text(solution_text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    # LaTeX Rendering Callbacks
    elif data.startswith("form_render_"):
        form_id = data.replace("form_render_", "")
        from handlers.latex_handler import render_formula_callback
        await render_formula_callback(query, form_id)

    elif data.startswith("ex_render_"):
        ex_id = data.replace("ex_render_", "")
        from handlers.latex_handler import render_exercise_callback
        await render_exercise_callback(query, ex_id)

    # 10. Help Menu
    elif data == "menu_help":
        await query.answer()
        help_text = (
            "ℹ️ <b>របៀបប្រើប្រាស់បូត (User Guide):</b>\n\n"
            "• <b>ស្វែងរកលឿន៖</b> គ្រាន់តែវាយឈ្មោះលំហាត់ ឬពាក្យគន្លឹះ ដូចជា <code>លំហាត់១</code>, <code>sin(x)</code>, <code>power rule</code>, <code>បាក់ឌុប</code>\n"
            "• <b>ប្រើប្រាស់ក្នុងគ្រុប (Group Privacy):</b> ដំណោះស្រាយនឹងត្រូវផ្ញើទៅកាន់ <b>Private Message (DM)</b> របស់អ្នក ដើម្បីរក្សាភាពឯកជន។\n"
            "• <b>មុខងារ Inline:</b> វាយ <code>@botusername លំហាត់១</code> នៅក្នុងគ្រុបណាមួយដើម្បីមើលដំណោះស្រាយជាលក្ខណៈឯកជន។\n\n"
            "📩 ទំនាក់ទំនងលោកគ្រូ៖ បើមានចម្ងល់លើមេរៀន អាចទាក់ទងលោកគ្រូបានជានិច្ច!"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ត្រឡប់ទៅម៉ឺនុយដើម (Home)", callback_data="menu_main")]
        ])
        await query.edit_message_text(help_text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    # 11. Search instructions
    elif data == "menu_search":
        await query.answer()
        search_prompt = (
            "🔍 <b>របៀបស្វែងរក៖</b>\n\n"
            "សូមផ្ញើសារនូវអ្វីដែលអ្នកចង់រក ឧទាហរណ៍៖\n"
            "• <code>លំហាត់១</code> ឬ <code>ex1</code>\n"
            "• <code>sin(x)</code> ឬ <code>cos(x)</code>\n"
            "• <code>ផលគុណ</code> ឬ <code>ផលចែក</code>\n"
            "• <code>chain rule</code>\n"
            "• <code>e^x</code> ឬ <code>ln(x)</code>\n\n"
            "បូតនឹងស្វែងរក និងបង្ហាញលទ្ធផលជូនភ្លាមៗ!"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ត្រឡប់ទៅម៉ឺនុយដើម (Home)", callback_data="menu_main")]
        ])
        await query.edit_message_text(search_prompt, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    # 11b. Ask AI Guide
    elif data == "menu_rag_help":
        await query.answer()
        rag_prompt = (
            "🤖 <b>សួរសំណួរផ្សេងៗ (ជំនួយការឆ្លាតវៃ RAG AI)</b> 😁\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "សិស្សអាចសួរសំណួរ ឬចម្ងល់មេរៀនគណិតវិទ្យាទី១២ ទាំង ១៥ មេរៀន ជាភាសាខ្មែរតាមបែបធម្មជាតិ!\n\n"
            "📌 <b>របៀបប្រើប្រាស់៖</b>\n"
            "គ្រាន់តែវាយពាក្យបញ្ជា <code>/ask &lt;សំណួរ&gt;</code> ឧទាហរណ៍៖\n\n"
            "• <code>/ask តើដេរីវេនៃអនុគមន៍បណ្ដាក់ u^n រកយ៉ាងម៉េច?</code>\n"
            "• <code>/ask ហេតុអ្វីបានជាដេរីវេនៃ cos(x) ស្មើ -sin(x)?</code>\n"
            "• <code>/ask រូបមន្តចំនួនកុំផ្លិចទម្រង់ត្រីកោណមាត្រមានអ្វីខ្លះ?</code>\n"
            "• <code>/ask ជួយពន្យល់ពីច្បាប់ផលចែក u/v ឱ្យងាយចាំបន្តិច</code>\n\n"
            "<i>AI នឹងស្រង់ឯកសារមេរៀនរបស់លោកគ្រូ រួចបកស្រាយមួយជំហានៗយ៉ាងក្បោះក្បាយ!</i>"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ត្រឡប់ទៅម៉ឺនុយដើម (Home)", callback_data="menu_main")]
        ])
        await query.edit_message_text(rag_prompt, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    # 12. Admin Dashboard Callbacks
    elif data == "admin_dashboard_cb":
        if not is_admin(user.id):
            await query.answer("⛔️ សម្រាប់តែគ្រូបង្រៀនប៉ុណ្ណោះ!", show_alert=True)
            return
        await query.answer()
        from handlers.admin import format_admin_dashboard_text, build_admin_panel_keyboard
        await query.edit_message_text(
            format_admin_dashboard_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=build_admin_panel_keyboard()
        )

    elif data == "admin_stats_cb":
        if not is_admin(user.id):
            await query.answer("⛔️ សម្រាប់តែគ្រូបង្រៀនប៉ុណ្ណោះ!", show_alert=True)
            return
        await query.answer()
        stats = db.get_stats()
        stats_text = (
            "📊 <b>ស្ថិតិប្រព័ន្ធបូតគណិតវិទ្យា៖</b>\n\n"
            f"• ចំនួនសិស្សចុះឈ្មោះ៖ <b>{stats['total_users']}</b> នាក់\n"
            f"• ចំនួនលំហាត់គណិតវិទ្យាទី១២៖ <b>{stats['total_exercises']}</b> លំហាត់\n"
            f"• ចំនួនរូបមន្តគណិតវិទ្យាទី១២៖ <b>{stats['total_formulas']}</b> រូបមន្ត\n"
            f"• ចំនួនដងនៃការស្វែងរក៖ <b>{stats['total_searches']}</b> ដង\n"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ត្រឡប់ទៅផ្ទាំង Admin", callback_data="admin_dashboard_cb")]
        ])
        await query.edit_message_text(stats_text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    elif data == "admin_backup_cb":
        if not is_admin(user.id):
            await query.answer("⛔️ សម្រាប់តែគ្រូបង្រៀនប៉ុណ្ណោះ!", show_alert=True)
            return
        await query.answer("📦 កំពុងបង្កើត Backup File...")
        import io
        data_export = db.export_all()
        json_bytes = json.dumps(data_export, ensure_ascii=False, indent=2).encode("utf-8")
        bio = io.BytesIO(json_bytes)
        bio.name = "math_lessons_backup.json"
        await chat.send_document(
            document=bio,
            caption="📦 <b>ឯកសារបម្រុងទុកទិន្នន័យ (Backup JSON)</b>",
            parse_mode=ParseMode.HTML
        )

    elif data == "admin_sync_cb":
        if not is_admin(user.id):
            await query.answer("⛔️ សម្រាប់តែគ្រូបង្រៀនប៉ុណ្ណោះ!", show_alert=True)
            return
        await query.answer()
        from sheets_sync import sync_from_google_sheet
        wait_text = "⏳ <b>កំពុង Sync ទិន្នន័យពី Google Sheets...</b>"
        await query.edit_message_text(wait_text, parse_mode=ParseMode.HTML)
        try:
            res = await sync_from_google_sheet()
            result_text = f"✅ <b>ជោគជ័យ!</b> {res['message']}"
        except Exception as e:
            result_text = f"❌ <b>បរាជ័យក្នុងការ Sync៖</b>\n<code>{e}</code>\n\n<i>សូមពិនិត្យមើល GOOGLE_SHEET_CSV_URL ក្នុង .env ឬប្រើ /sync_sheets &lt;url&gt;</i>"
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ត្រឡប់ទៅផ្ទាំង Admin", callback_data="admin_dashboard_cb")]
        ])
        await query.edit_message_text(result_text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    elif data == "admin_add_guide_cb":
        if not is_admin(user.id):
            await query.answer("⛔️ សម្រាប់តែគ្រូបង្រៀនប៉ុណ្ណោះ!", show_alert=True)
            return
        await query.answer()
        guide = (
            "📝 <b>របៀបបញ្ចូលលំហាត់ថ្មីតាម Telegram៖</b>\n\n"
            "សូម Copy និងបំពេញទម្រង់ខាងក្រោម រួចផ្ញើចូលក្នុងឆាតនេះ៖\n\n"
            "<code>/add\n"
            "code: លំហាត់៩\n"
            "title: ដេរីវេនៃអនុគមន៍ tan(3x)\n"
            "category: trig\n"
            "problem: គណនាដេរីវេនៃ y = tan(3x)\n"
            "hints: ប្រើរូបមន្ត (tan u)' = u' / cos²(u)\n"
            "step: ជំហានទី១៖ តាង u = 3x => u' = 3\n"
            "step: ជំហានទី២៖ y' = 3 / cos²(3x)\n"
            "answer: y' = 3 / cos²(3x)\n"
            "difficulty: មធ្យម\n"
            "keywords: tan, tan(3x), លំហាត់៩</code>"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 ត្រឡប់ទៅផ្ទាំង Admin", callback_data="admin_dashboard_cb")]
        ])
        await query.edit_message_text(guide, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    elif data == "admin_rag_panel_cb":
        if not is_admin(user.id):
            await query.answer("⛔️ សម្រាប់តែគ្រូបង្រៀនប៉ុណ្ណោះ!", show_alert=True)
            return
        await query.answer()
        from handlers.rag_handler import format_rag_panel_text, build_rag_panel_keyboard
        await query.edit_message_text(
            format_rag_panel_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=build_rag_panel_keyboard()
        )

    elif data.startswith("rag_del_cb_"):
        if not is_admin(user.id):
            await query.answer("⛔️ សម្រាប់តែគ្រូបង្រៀនប៉ុណ្ណោះ!", show_alert=True)
            return
        doc_id = data.replace("rag_del_cb_", "")
        from rag_engine import rag_db
        from handlers.rag_handler import format_rag_panel_text, build_rag_panel_keyboard
        deleted = rag_db.delete_document(doc_id)
        if deleted:
            await query.answer(f"🗑 បានលុបឯកសារ «{doc_id}» រួចរាល់!", show_alert=True)
        else:
            await query.answer("⚠️ រកមិនឃើញឯកសារនេះទេ", show_alert=True)
        await query.edit_message_text(
            format_rag_panel_text(),
            parse_mode=ParseMode.HTML,
            reply_markup=build_rag_panel_keyboard()
        )

