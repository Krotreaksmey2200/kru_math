"""
Telegram Handlers for RAG AI Assistant and Document Ingestion.
Enables students to ask conceptual math questions (/ask),
and enables the teacher to upload PDF lesson documents directly in Telegram chat.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode, ChatType
from telegram.ext import ContextTypes

from config import is_admin, GEMINI_API_KEY
from handlers.group_privacy import send_solution_with_privacy
from rag_engine import (
    is_rag_available,
    index_pdf_document,
    answer_with_rag,
    rag_db
)

logger = logging.getLogger("MathBot.RAGHandler")


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /ask <question> command using RAG AI.
    Example: /ask តើដេរីវេនៃ sin(3x) គណនាយ៉ាងម៉េច?
    """
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        help_msg = (
            "🤖 <b>ជំនួយការឆ្លាតវៃ RAG AI គណិតវិទ្យា</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "សិស្សអាចសួរសំណួរ ឬចម្ងល់មេរៀនគណិតវិទ្យាជាភាសាខ្មែរតាមបែបធម្មជាតិ!\n\n"
            "📌 <b>របៀបប្រើប្រាស់៖</b>\n"
            "• <code>/ask តើដេរីវេនៃអនុគមន៍បណ្ដាក់ u^n រកយ៉ាងម៉េច?</code>\n"
            "• <code>/ask ហេតុអ្វីបានជាដេរីវេនៃ cos(x) ស្មើ -sin(x)?</code>\n"
            "• <code>/ask ជួយពន្យល់ពីច្បាប់ផលចែក u/v ឱ្យងាយចាំបន្តិច</code>"
        )
        await chat.send_message(help_msg, parse_mode=ParseMode.HTML)
        return

    # Check if RAG is configured
    if not is_rag_available():
        notice = (
            "⚠️ <b>ប្រព័ន្ធ RAG AI មិនទាន់ត្រូវបានកំណត់ GEMINI_API_KEY នៅឡើយទេ៖</b>\n\n"
            "លោកគ្រូអាចយក API Key ឥតគិតថ្លៃ (Free 100%) នៅ៖\n"
            "👉 https://aistudio.google.com/app/apikey\n"
            "រួចដាក់ចូលក្នុង Environment Variable <code>GEMINI_API_KEY</code> លើ Render!"
        )
        await chat.send_message(notice, parse_mode=ParseMode.HTML)
        return

    student_name = user.first_name or user.username or "ប្អូនសិស្ស"

    # Send temporary waiting indicator with student name and fun vibe
    wait_msg = await chat.send_message(
        f"🧠 <b>កំពុងបើកក្បួនគណិតដេរីវេឱ្យប្អូន {student_name}...</b> ⏳\n"
        f"<i>រង់ចាំបន្តិចណា៎ គិតលឿនដូច Wifi 5G កុំទាន់បាក់ទឹកចិត្ត! 🚀😎</i>",
        parse_mode=ParseMode.HTML
    )

    result = await answer_with_rag(question, student_name=student_name)
    answer_text = result.get("answer", "")
    sources = result.get("sources", [])

    # Format response message
    formatted_msg = (
        f"❓ <b>សំណួររបស់ប្អូន {student_name}៖</b> <i>{question}</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{answer_text}\n"
    )

    if sources:
        formatted_msg += f"\n📚 <b>ឯកសារយោង៖</b> {', '.join(sources)}\n"

    # Delete waiting message
    try:
        await wait_msg.delete()
    except Exception:
        pass

    # Send with privacy protection if in group
    is_group = chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
    if is_group:
        await send_solution_with_privacy(
            update=update,
            context=context,
            solution_text=formatted_msg,
            deep_link_payload="rag_help"
        )
    else:
        await chat.send_message(formatted_msg, parse_mode=ParseMode.HTML)


async def handle_document_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle PDF document upload from the teacher to automatically index into RAG.
    Allows teacher to simply drop/send any .PDF directly into chat!
    """
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not message.document or not user or not chat:
        return

    # Check authorization
    if not is_admin(user.id):
        await chat.send_message(
            "⛔️ <b>ការអនុញ្ញាត៖</b> មុខងារ Upload សៀវភៅមេរៀនចូលក្នុងខួរក្បាល RAG AI គឺសម្រាប់តែលោកគ្រូបង្រៀន (Admin) ប៉ុណ្ណោះ។\n\n"
            "ប្អូនៗសិស្សានុសិស្សអាចប្រើប្រាស់ <code>/ask &lt;សំណួរ&gt;</code> ដើម្បីសួរ AI បាន!",
            parse_mode=ParseMode.HTML
        )
        return

    doc = message.document
    filename = doc.file_name or "lesson_document.pdf"
    mime = doc.mime_type or ""

    # Validate file type
    if not (filename.lower().endswith(".pdf") or mime == "application/pdf"):
        await chat.send_message(
            f"⚠️ <b>ឯកសារ «{filename}» មិនមែនជាទម្រង់ PDF ទេ៖</b>\n\n"
            "ប្រព័ន្ធ RAG AI គាំទ្រតែឯកសារប្រភេទ <b>.PDF</b> ប៉ុណ្ណោះ (ឧ. <code>មេរៀន_ថ្នាក់ទី១២.pdf</code>)។\n"
            "សូមលោកគ្រូបំប្លែងឯកសារជា PDF រួចផ្ញើម្តងទៀត។",
            parse_mode=ParseMode.HTML
        )
        return

    # Validate Telegram file size (20MB limit for Bot API)
    file_size = doc.file_size or 0
    if file_size > 20 * 1024 * 1024:
        await chat.send_message(
            f"⚠️ <b>ទំហំឯកសារធំពេក ({round(file_size / (1024*1024), 1)} MB)៖</b>\n\n"
            "Telegram Bot API អនុញ្ញាតឱ្យទាញយកឯកសារត្រឹមអតិបរមា <b>20MB</b>។\n"
            "សូមកាត់បន្ថយទំហំ PDF ឱ្យក្រោម 20MB រួចផ្ញើម្តងទៀត។",
            parse_mode=ParseMode.HTML
        )
        return

    # Check Gemini API availability
    if not is_rag_available():
        await chat.send_message(
            "⚠️ <b>មិនទាន់បានកំណត់ GEMINI_API_KEY៖</b>\n\n"
            "សូមលោកគ្រូបន្ថែម <code>GEMINI_API_KEY</code> ក្នុង Render Dashboard (Environment) ជាមុនសិន ទើបអាចដំណើរការ RAG បាន។",
            parse_mode=ParseMode.HTML
        )
        return

    file_size_kb = round(file_size / 1024, 1) if file_size else 0
    status_msg = await chat.send_message(
        f"📥 <b>បានទទួលឯកសារ៖</b> <code>{filename}</code> ({file_size_kb} KB)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ <b>ដំណាក់កាល ១/៣៖</b> កំពុងទាញយក និងស្រង់ទំព័រមេរៀនចេញពី PDF...",
        parse_mode=ParseMode.HTML
    )

    async def update_progress(stage: str, current: int, total: int, num_pages: int):
        try:
            if stage == "chunking":
                await status_msg.edit_text(
                    f"📄 <b>ឯកសារ៖</b> <code>{filename}</code> (ចំនួន <b>{num_pages}</b> ទំព័រ)\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"✂️ <b>បំបែកបាន៖</b> <b>{total}</b> កថាខណ្ឌ (Chunks)\n"
                    f"⏳ <b>ដំណាក់កាល ២/៣៖</b> កំពុងគណនា AI Embeddings ជាមួយ Google Gemini...",
                    parse_mode=ParseMode.HTML
                )
            elif stage == "embedding":
                pct = int((current / total) * 100) if total else 0
                await status_msg.edit_text(
                    f"📄 <b>ឯកសារ៖</b> <code>{filename}</code> (ចំនួន <b>{num_pages}</b> ទំព័រ)\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🧠 <b>ដំណើរការ Embeddings៖</b> <b>{current}/{total}</b> ({pct}%)\n"
                    f"⏳ <b>ដំណាក់កាល ២/៣៖</b> កំពុងបញ្ចូលក្នុងប្រព័ន្ធចងចាំ RAG...",
                    parse_mode=ParseMode.HTML
                )
        except Exception:
            pass

    try:
        tg_file = await doc.get_file()
        file_bytes = await tg_file.download_as_bytearray()

        res = await index_pdf_document(filename, bytes(file_bytes), progress_callback=update_progress)
        if res.get("success"):
            docs = rag_db.get_documents()
            total_chunks = sum(d["num_chunks"] for d in docs)

            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 សាកល្បងសួរ AI លើមេរៀននេះ (/ask)", callback_data="menu_rag_help")],
                [InlineKeyboardButton("📚 បញ្ជីឯកសារមេរៀនទាំងអស់ (/rag_docs)", callback_data="admin_rag_panel_cb")],
                [InlineKeyboardButton("👨‍🏫 ត្រឡប់ទៅផ្ទាំង Admin", callback_data="admin_dashboard_cb")]
            ])

            await status_msg.edit_text(
                f"🎉 <b>បញ្ចូលសៀវភៅមេរៀនជោគជ័យ ១០០%!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📚 <b>ឈ្មោះឯកសារ៖</b> <code>{filename}</code>\n"
                f"📄 <b>ចំនួនទំព័រ៖</b> <b>{res.get('num_pages', 1)}</b> ទំព័រ\n"
                f"🧩 <b>ចំនួនកថាខណ្ឌ (Chunks)៖</b> <b>{res.get('num_chunks', 0)}</b>\n"
                f"📦 <b>សៀវភៅក្នុងប្រព័ន្ធ RAG សរុប៖</b> <b>{len(docs)}</b> ក្បាល ({total_chunks} Chunks)\n\n"
                f"💡 <b>សិស្សានុសិស្ស និងលោកគ្រូអាចសួរចម្ងល់លើមេរៀននេះបានភ្លាមៗ!</b>\n"
                f"👉 វាយ៖ <code>/ask &lt;សំណួរ&gt;</code> ក្នុងឆាត ឬក្នុងគ្រុប",
                parse_mode=ParseMode.HTML,
                reply_markup=kb
            )
        else:
            await status_msg.edit_text(
                f"❌ <b>បរាជ័យក្នុងការ Index៖</b>\n{res.get('error', 'Unknown error')}",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error("Failed to process uploaded PDF: %s", e)
        await status_msg.edit_text(
            f"❌ <b>មានបញ្ហាបច្ចេកទេសក្នុងការទាញយក៖</b> <code>{str(e)}</code>",
            parse_mode=ParseMode.HTML
        )


def format_rag_panel_text() -> str:
    """Generate status and guide text for RAG document management."""
    docs = rag_db.get_documents()
    status_emoji = "🟢 សកម្ម (Active - Gemini 3.6 & Embeddings)" if is_rag_available() else "🔴 មិនទាន់កំណត់ GEMINI_API_KEY"
    total_chunks = sum(d["num_chunks"] for d in docs)

    msg = (
        "📚 <b>ផ្ទាំងគ្រប់គ្រងសៀវភៅមេរៀន RAG AI Knowledge Base</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"• ស្ថានភាព AI៖ <b>{status_emoji}</b>\n"
        f"• សៀវភៅក្នុងប្រព័ន្ធ៖ <b>{len(docs)}</b> ក្បាល ({total_chunks} Chunks)\n\n"
    )

    if docs:
        msg += "📋 <b>បញ្ជីសៀវភៅមេរៀនដែលបាន Upload៖</b>\n"
        for idx, d in enumerate(docs, 1):
            created_str = d['created_at'][:16] if isinstance(d.get('created_at'), str) else "កាលពីថ្មីៗ"
            msg += f"{idx}. 📄 <b>{d['filename']}</b>\n   └ 🧩 {d['num_chunks']} កថាខណ្ឌ | ID: <code>{d['id']}</code>\n"
        msg += "\n"
    else:
        msg += "<i>មិនទាន់មានឯកសារ PDF ណាមួយត្រូវបាន Upload នៅឡើយទេ។</i>\n\n"

    msg += (
        "📥 <b>របៀប Upload សៀវភៅមេរៀនថ្មីបន្ថែម៖</b>\n"
        "លោកគ្រូគ្រាន់តែ <b>ចុចផ្ញើ (Attach/Send) ឯកសារ .PDF</b> ចូលក្នុងឆាតជាមួយ Bot នេះដោយផ្ទាល់!\n"
        "Bot នឹងអាន ស្រង់ទំព័រ និងបំប្លែងជា AI Embeddings ដោយស្វ័យប្រវត្តិភ្លាមៗ។\n\n"
        "🗑 <i>ដើម្បីលុបឯកសារណាមួយ សូមប្រើ៖</i> <code>/rag_delete &lt;id&gt;</code>"
    )
    return msg


def build_rag_panel_keyboard() -> InlineKeyboardMarkup:
    """Build interactive buttons for RAG document panel."""
    docs = rag_db.get_documents()
    buttons = []

    # Add quick delete buttons for loaded docs if any
    for d in docs[:5]:  # limit to top 5 for neat buttons
        buttons.append([
            InlineKeyboardButton(f"🗑 លុប: {d['filename'][:20]}", callback_data=f"rag_del_cb_{d['id']}")
        ])

    buttons.append([
        InlineKeyboardButton("🔄 Refresh បញ្ជី", callback_data="admin_rag_panel_cb"),
        InlineKeyboardButton("🤖 សាកល្បងសួរ AI (/ask)", callback_data="menu_rag_help")
    ])
    buttons.append([
        InlineKeyboardButton("🔙 ត្រឡប់ទៅផ្ទាំង Admin", callback_data="admin_dashboard_cb")
    ])
    return InlineKeyboardMarkup(buttons)


async def rag_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show RAG knowledge base status and loaded documents."""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user or not is_admin(user.id):
        return

    await chat.send_message(
        format_rag_panel_text(),
        parse_mode=ParseMode.HTML,
        reply_markup=build_rag_panel_keyboard()
    )


async def rag_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a document from RAG knowledge base."""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user or not is_admin(user.id):
        return

    if not context.args:
        await chat.send_message(
            "⚠️ <b>សូមបញ្ជាក់ Document ID ដែលចង់លុប៖</b>\nឧទាហរណ៍៖ <code>/rag_delete doc_12345678</code>\n<i>(មើល ID តាមរយៈ /rag_docs)</i>",
            parse_mode=ParseMode.HTML
        )
        return

    target_id = context.args[0].strip()
    deleted = rag_db.delete_document(target_id)
    if deleted:
        await chat.send_message(
            f"🗑 <b>បានលុបឯកសារ «{target_id}» ចេញពីប្រព័ន្ធ RAG រួចរាល់!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=build_rag_panel_keyboard()
        )
    else:
        await chat.send_message(f"⚠️ រកមិនឃើញឯកសារដែលមាន ID «{target_id}» ទេ។", parse_mode=ParseMode.HTML)
