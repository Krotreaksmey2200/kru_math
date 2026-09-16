"""
Start and Help Command Handlers.
Supports bilingual welcome (Khmer & English), interactive menu, and deep-link payload routing.
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes

from database import db
from handlers.exercises import (
    build_main_menu_keyboard,
    format_exercise_solution_html,
    format_formula_html
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with deep-link support (e.g., /start ex_1)."""
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    # Track user in database
    db.track_user(user.id, user.username, user.first_name, user.last_name)

    # Check for deep-linking parameters (e.g. "ex_1" or "form_power")
    args = context.args
    if args and len(args) > 0:
        payload = args[0]

        # Deep-link to an exercise solution
        if payload.startswith("ex_"):
            ex_id = payload
            ex = db.get_exercise_by_id(ex_id) or db.get_exercise_by_code(payload.replace("ex_", ""))
            if ex:
                solution_text = format_exercise_solution_html(ex)
                back_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📚 ទៅកាន់ម៉ឺនុយលំហាត់", callback_data="menu_exercises")],
                    [InlineKeyboardButton("🏠 ម៉ឺនុយដើម (Home)", callback_data="menu_main")]
                ])
                await chat.send_message(
                    text=f"🔓 <b>ដំណោះស្រាយផ្ទាល់ខ្លួនរបស់អ្នក៖</b>\n\n{solution_text}",
                    parse_mode=ParseMode.HTML,
                    reply_markup=back_kb
                )
                return

        # Deep-link to a formula
        elif payload.startswith("form_"):
            form_id = payload
            form = db.get_formula_by_id(form_id)
            if form:
                formula_text = format_formula_html(form)
                back_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📐 មើលរូបមន្តផ្សេងទៀត", callback_data="menu_formulas")],
                    [InlineKeyboardButton("🏠 ម៉ឺនុយដើម (Home)", callback_data="menu_main")]
                ])
                await chat.send_message(
                    text=formula_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=back_kb
                )
                return

    # Default /start message (Bilingual Khmer & English)
    welcome_message = (
        f"👋 <b>សួស្ដី {user.first_name}! / Hello {user.first_name}!</b>\n\n"
        "🇰🇭 <b>ស្វាគមន៍មកកាន់ប្រព័ន្ធជំនួយគណិតវិទ្យា៖ ដេរីវេនៃអនុគមន៍</b>\n"
        "ខ្ញុំជាជំនួយការបង្រៀនគណិតវិទ្យា សម្រាប់ជួយប្អូនៗក្នុងការរៀនរូបមន្ត និងដោះស្រាយលំហាត់ដេរីវេ (ត្រៀមប្រឡងបាក់ឌុប)។\n\n"
        "🇬🇧 <b>Welcome to Calculus Derivative Assistant!</b>\n"
        "I am your automated math assistant for learning derivative formulas, rules, and step-by-step exam exercises.\n\n"
        "✨ <b>លក្ខណៈពិសេសចម្បង / Key Features:</b>\n"
        "• 📐 រូបមន្តគ្រឹះ ផលគុណ ផលចែក ដេរីវេបណ្ដាក់ និងត្រីកោណមាត្រ\n"
        "• 📝 លំហាត់អនុវត្តជាមួយដំណោះស្រាយមួយជំហានៗយ៉ាងក្បោះក្បាយ\n"
        "• 🔒 <b>Group Privacy:</b> នៅពេលសួរក្នុងគ្រុប ដំណោះស្រាយនឹងផ្ញើទៅកាន់ DM របស់អ្នកដោយសុវត្ថិភាព\n"
        "• ⚡️ <b>Inline Mode:</b> វាយ <code>@botusername លំហាត់១</code> ក្នុងគ្រុបណាក៏បានដើម្បីមើលចម្លើយ\n\n"
        "👇 <i>សូមជ្រើសរើសផ្នែកដែលអ្នកចង់សិក្សាខាងក្រោម៖</i>"
    )

    await chat.send_message(
        text=welcome_message,
        parse_mode=ParseMode.HTML,
        reply_markup=build_main_menu_keyboard(user.id)
    )



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command with bilingual guidance."""
    help_text = (
        "📚 <b>សៀវភៅណែនាំប្រើប្រាស់ / USER GUIDE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🇰🇭 <b>ភាសាខ្មែរ៖</b>\n"
        "1. <b>ការស្វែងរករហ័ស៖</b> អ្នកអាចវាយឈ្មោះលំហាត់ ឬពាក្យគន្លឹះក្នុងប្រអប់ឆាតបានភ្លាមៗ ដូចជា៖\n"
        "   • <code>លំហាត់១</code>, <code>លំហាត់៤</code>, <code>ex2</code>\n"
        "   • <code>sin(x)</code>, <code>cos(x)</code>, <code>tan(x)</code>\n"
        "   • <code>power rule</code>, <code>chain rule</code>, <code>ផលគុណ</code>\n"
        "2. <b>ការប្រើប្រាស់ក្នុងគ្រុប (Group Privacy):</b>\n"
        "   • ដើម្បីការពារកុំឱ្យចម្លើយបង្ហាញជាសាធារណៈដល់អ្នកដទៃ បូតនឹងផ្ញើដំណោះស្រាយទៅកាន់ <b>Private Message (DM)</b> របស់អ្នក។\n"
        "   • សារជូនដំណឹងក្នុងគ្រុបនឹងលុបដោយស្វ័យប្រវត្តិក្នង ៨ វិនាទី។\n"
        "3. <b>ការប្រើប្រាស់ Inline Query:</b>\n"
        "   • នៅក្នុងគ្រុប ឬឆាតណាមួយ គ្រាន់តែវាយឈ្មោះបូត ឧទាហរណ៍៖\n"
        "     <code>@botusername sin(x)</code>\n"
        "   • អ្នកនឹងឃើញបញ្ជីរូបមន្ត និងលំហាត់លោតឡើងមកមើលជាឯកជនភ្លាមៗ!\n\n"
        "🇬🇧 <b>ENGLISH:</b>\n"
        "• <b>Quick Search:</b> Send keywords like <code>ex1</code>, <code>sin(x)</code>, or <code>chain rule</code> directly.\n"
        "• <b>Group Privacy:</b> When triggered in a group chat, solutions are dispatched straight to your private DM to prevent spoilers.\n"
        "• <b>Inline Mode:</b> Type <code>@botusername &lt;query&gt;</code> in any chat to preview formulas and exercises.\n\n"
        "📌 <b>បញ្ជីពាក្យបញ្ជា / Commands:</b>\n"
        "/start - បើកម៉ឺនុយដើម (Start Bot)\n"
        "/formulas - បញ្ជីរូបមន្តដេរីវេ (Derivative Formulas)\n"
        "/exercises - បញ្ជីលំហាត់អនុវត្ត (Practice Exercises)\n"
        "/search - ណែនាំពីការស្វែងរក (Search Guide)\n"
        "/help - បង្ហាញជំនួយនេះ (Help)"
    )

    back_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 ម៉ឺនុយដើម (Home)", callback_data="menu_main")]
    ])

    await update.effective_chat.send_message(
        text=help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=back_kb
    )
