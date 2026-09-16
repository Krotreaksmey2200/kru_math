"""
Teacher Admin Command Handlers.
Secured by TEACHER_ADMIN_ID.
Allows the math teacher to add, update, delete exercises, sync from Google Sheets,
broadcast announcements to students, and view real-time statistics directly from Telegram.
"""

import io
import json
import logging
from functools import wraps
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import is_admin, TEACHER_ADMIN_IDS
from database import db
from sheets_sync import sync_from_google_sheet

logger = logging.getLogger("MathBot.Admin")


def admin_only(func):
    """Decorator to restrict handler execution to verified teachers only."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user or not is_admin(user.id):
            logger.warning("Unauthorized admin access attempt by user %s (@%s)", user.id if user else "Unknown", user.username if user else "")
            if update.effective_chat:
                await update.effective_chat.send_message(
                    "⛔️ <b>ការបដិសេធសិទ្ធិ (Access Denied):</b>\n"
                    "មុខងារនេះសម្រាប់តែលោកគ្រូអ្នកគ្រូបង្រៀន (Admin) ប៉ុណ្ណោះ។\n"
                    f"User ID របស់អ្នកគឺ៖ <code>{user.id if user else 'N/A'}</code>",
                    parse_mode=ParseMode.HTML
                )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


from config import is_admin, TEACHER_ADMIN_IDS, GOOGLE_SHEET_VIEW_URL


def build_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Buttons for teacher management dashboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 មើលស្ថិតិ (Stats)", callback_data="admin_stats_cb"),
            InlineKeyboardButton("📦 ទាញយក Backup", callback_data="admin_backup_cb")
        ],
        [
            InlineKeyboardButton("📄 បើក Google Sheet", url=GOOGLE_SHEET_VIEW_URL or "https://docs.google.com/spreadsheets"),
            InlineKeyboardButton("🔄 Sync ពី Google Sheets", callback_data="admin_sync_cb")
        ],
        [
            InlineKeyboardButton("➕ របៀបបញ្ចូលលំហាត់", callback_data="admin_add_guide_cb"),
            InlineKeyboardButton("🏠 ម៉ឺនុយដើម (Home)", callback_data="menu_main")
        ]
    ])



def format_admin_dashboard_text() -> str:
    """Format dashboard message."""
    stats = db.get_stats()
    return (
        "👨‍🏫 <b>ផ្ទាំងគ្រប់គ្រងលោកគ្រូ (Teacher Admin Dashboard)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 សិស្សចុះឈ្មោះសរុប៖ <b>{stats['total_users']}</b> នាក់\n"
        f"📝 លំហាត់ក្នុងប្រព័ន្ធ៖ <b>{stats['total_exercises']}</b> លំហាត់\n"
        f"📐 រូបមន្តដេរីវេ៖ <b>{stats['total_formulas']}</b> រូបមន្ត\n"
        f"🔍 ចំនួនស្វែងរកសរុប៖ <b>{stats['total_searches']}</b> ដង\n\n"
        "🛠 <b>មុខងារគ្រប់គ្រងរហ័ស (Quick Actions)៖</b>\n"
        "ចុចប៊ូតុងខាងក្រោម ឬប្រើពាក្យបញ្ជាផ្ទាល់៖\n"
        "• <code>/stats</code> - មើលស្ថិតិសិស្ស\n"
        "• <code>/add</code> - បញ្ចូលលំហាត់ថ្មី\n"
        "• <code>/delete &lt;code&gt;</code> - លុបលំហាត់\n"
        "• <code>/sync_sheets [url]</code> - Sync ពី Google Sheets\n"
        "• <code>/broadcast &lt;សារ&gt;</code> - ផ្ញើសារទៅសិស្សទាំងអស់\n"
        "• <code>/backup</code> - ទាញយកទិន្នន័យ Backup"
    )


@admin_only
async def admin_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display teacher dashboard and quick management commands."""
    msg = format_admin_dashboard_text()
    await update.effective_chat.send_message(
        msg,
        parse_mode=ParseMode.HTML,
        reply_markup=build_admin_panel_keyboard()
    )



@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View detailed statistics."""
    stats = db.get_stats()
    msg = (
        "📊 <b>ស្ថិតិប្រព័ន្ធបូតគណិតវិទ្យា៖</b>\n\n"
        f"• ចំនួនសិស្សកំពុងប្រើប្រាស់៖ <b>{stats['total_users']}</b>\n"
        f"• ចំនួនលំហាត់ដេរីវេ៖ <b>{stats['total_exercises']}</b>\n"
        f"• ចំនួនរូបមន្តដេរីវេ៖ <b>{stats['total_formulas']}</b>\n"
        f"• ចំនួនដងនៃការស្វែងរក៖ <b>{stats['total_searches']}</b>\n"
    )
    await update.effective_chat.send_message(msg, parse_mode=ParseMode.HTML)


@admin_only
async def admin_sync_sheets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger synchronization from a Google Sheet CSV URL."""
    custom_url = context.args[0].strip() if context.args else None

    wait_msg = await update.effective_chat.send_message(
        "⏳ <b>កំពុងទាញយកទិន្នន័យពី Google Sheets...</b> សូមរង់ចាំបន្តិច",
        parse_mode=ParseMode.HTML
    )

    try:
        result = await sync_from_google_sheet(csv_url=custom_url)
        await wait_msg.edit_text(
            f"✅ <b>ជោគជ័យ!</b>\n{result['message']}\n"
            f"ចំនួនលំហាត់ដែលបាន Sync៖ <b>{result['count']}</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error("Sheet sync failed: %s", e)
        await wait_msg.edit_text(
            f"❌ <b>បរាជ័យក្នុងការ Sync៖</b>\n<code>{str(e)}</code>\n\n"
            "💡 <b>គន្លឹះ៖</b> សូមប្រាកដថា Google Sheet ត្រូវបាន Publish ទៅ Web ជា CSV:\n"
            "<i>File -> Share -> Publish to web -> Comma-separated values (.csv)</i>",
            parse_mode=ParseMode.HTML
        )


@admin_only
async def admin_add_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Add or update an exercise via Telegram message.
    Usage example:
    /add
    code: លំហាត់៩
    title: ដេរីវេនៃ tan(3x)
    category: trig
    problem: គណនាដេរីវេ y = tan(3x)
    hints: ប្រើ (tan u)' = u'/cos²u
    step: u = 3x => u' = 3
    step: y' = 3 / cos²(3x)
    answer: y' = 3 / cos²(3x)
    keywords: tan, tan(3x), លំហាត់៩
    """
    raw_text = update.effective_message.text
    # Strip command prefix
    lines = raw_text.split("\n")[1:] if "\n" in raw_text else []

    if not lines:
        sample = (
            "📝 <b>ទម្រង់សម្រាប់បញ្ចូលលំហាត់ថ្មី (Copy & Paste):</b>\n\n"
            "<code>/add\n"
            "code: លំហាត់៩\n"
            "title: ដេរីវេនៃអនុគមន៍តង់សង់ tan(3x)\n"
            "category: trig\n"
            "problem: គណនាដេរីវេនៃ y = tan(3x)\n"
            "hints: ប្រើរូបមន្ត (tan u)' = u' / cos²(u)\n"
            "step: ជំហានទី១៖ តាង u = 3x => u' = 3\n"
            "step: ជំហានទី២៖ y' = (3x)' / cos²(3x) = 3 / cos²(3x)\n"
            "answer: y' = 3 / cos²(3x)\n"
            "difficulty: មធ្យម\n"
            "keywords: tan, tan(3x), លំហាត់៩</code>"
        )
        await update.effective_chat.send_message(sample, parse_mode=ParseMode.HTML)
        return

    # Parse key-value lines
    data = {"solution_steps": [], "keywords": []}
    for line in lines:
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip().lower()
        val = val.strip()

        if key == "code":
            data["code"] = val
        elif key == "title":
            data["title"] = val
        elif key in ("category", "cat", "category_id"):
            data["category_id"] = val
        elif key == "problem":
            data["problem"] = val
        elif key in ("hint", "hints"):
            data["hints"] = val
        elif key in ("step", "steps"):
            data["solution_steps"].append(val)
        elif key in ("answer", "final_answer"):
            data["final_answer"] = val
        elif key in ("difficulty", "diff"):
            data["difficulty"] = val
        elif key in ("keyword", "keywords"):
            data["keywords"].extend([k.strip() for k in val.split(",") if k.strip()])

    if not data.get("title") or not data.get("problem"):
        await update.effective_chat.send_message(
            "⚠️ ខ្វះព័ត៌មានចាំបាច់! សូមប្រាកដថាមានបញ្ចូល <code>title:</code> និង <code>problem:</code> យ៉ាងតិច។",
            parse_mode=ParseMode.HTML
        )
        return

    # Generate or reuse ID
    ex_id = data.get("code") or f"ex_{int(update.effective_message.date.timestamp())}"
    data["id"] = ex_id
    saved_id = db.save_exercise(data)

    await update.effective_chat.send_message(
        f"✅ <b>បានរក្សាទុកលំហាត់ដោយជោគជ័យ!</b>\n\n"
        f"• កូដសម្គាល់៖ <b>{data.get('code', saved_id)}</b>\n"
        f"• ចំណងជើង៖ {data['title']}\n"
        f"• ចំនួនជំហានដំណោះស្រាយ៖ {len(data['solution_steps'])}\n\n"
        f"<i>សិស្សអាចស្វែងរកលំហាត់នេះបានភ្លាមៗ!</i>",
        parse_mode=ParseMode.HTML
    )


@admin_only
async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete an exercise by code or ID."""
    if not context.args:
        await update.effective_chat.send_message(
            "⚠️ <b>សូមបញ្ជាក់កូដលំហាត់ដែលចង់លុប៖</b>\nឧទាហរណ៍៖ <code>/delete លំហាត់៩</code> ឬ <code>/delete ex_1</code>",
            parse_mode=ParseMode.HTML
        )
        return

    target = context.args[0].strip()
    deleted = db.delete_exercise(target)
    if deleted:
        await update.effective_chat.send_message(
            f"🗑 <b>បានលុបលំហាត់ «{target}» ចេញពីប្រព័ន្ធរួចរាល់!</b>",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.effective_chat.send_message(
            f"⚠️ រកមិនឃើញលំហាត់ដែលមានកូដ «{target}» ឡើយ។",
            parse_mode=ParseMode.HTML
        )


@admin_only
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast an announcement message to all registered students."""
    if not context.args:
        await update.effective_chat.send_message(
            "📢 <b>របៀបផ្ញើសារប្រកាសទៅកាន់សិស្សទាំងអស់៖</b>\n"
            "<code>/broadcast សួស្ដីប្អូនៗ! លោកគ្រូបានបញ្ចូលលំហាត់ត្រៀមប្រឡងថ្មីចំនួន ៣ បន្ថែមទៀត។</code>",
            parse_mode=ParseMode.HTML
        )
        return

    broadcast_text = " ".join(context.args)
    user_ids = db.get_all_user_ids()
    sent_count = 0
    fail_count = 0

    status_msg = await update.effective_chat.send_message(
        f"📡 កំពុងផ្ញើសារទៅកាន់សិស្សចំនួន <b>{len(user_ids)}</b> នាក់...",
        parse_mode=ParseMode.HTML
    )

    formatted_broadcast = (
        "📢 <b>សារជូនដំណឹងពីលោកគ្រូ៖</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{broadcast_text}"
    )

    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=formatted_broadcast,
                parse_mode=ParseMode.HTML
            )
            sent_count += 1
        except Exception:
            fail_count += 1

    await status_msg.edit_text(
        f"✅ <b>បានផ្ញើសារជូនដំណឹងរួចរាល់!</b>\n\n"
        f"• ផ្ញើបានជោគជ័យ៖ <b>{sent_count}</b> នាក់\n"
        f"• បរាជ័យ (Block bot/ឈប់ប្រើ)៖ <b>{fail_count}</b> នាក់",
        parse_mode=ParseMode.HTML
    )


@admin_only
async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export the current database as a downloadable JSON file."""
    data = db.export_all()
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    bio = io.BytesIO(json_bytes)
    bio.name = "math_lessons_backup.json"

    await update.effective_chat.send_document(
        document=bio,
        caption="📦 <b>ឯកសារបម្រុងទុកទិន្នន័យលំហាត់ និងរូបមន្ត (Backup JSON)</b>",
        parse_mode=ParseMode.HTML
    )
