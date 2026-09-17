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

    # Send temporary waiting indicator
    wait_msg = await chat.send_message(
        "🧠 <b>កំពុងស្វែងរកក្នុងសៀវភៅមេរៀន និងរៀបចំការពន្យល់...</b> ⏳",
        parse_mode=ParseMode.HTML
    )

    result = await answer_with_rag(question)
    answer_text = result.get("answer", "")
    sources = result.get("sources", [])

    # Format response message
    formatted_msg = (
        f"❓ <b>សំណួរ៖</b> <i>{question}</i>\n"
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
    """
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not message.document or not user or not chat:
        return

    # Only verified teacher can add documents to knowledge base
    if not is_admin(user.id):
        return

    doc = message.document
    filename = doc.file_name or "document.pdf"

    if not filename.lower().endswith(".pdf"):
        await chat.send_message(
            "⚠️ បច្ចុប្បន្នប្រព័ន្ធ RAG គាំទ្រការ Upload ឯកសារជាទម្រង់ <b>.PDF</b> ប៉ុណ្ណោះ។",
            parse_mode=ParseMode.HTML
        )
        return

    wait_msg = await chat.send_message(
        f"📥 <b>កំពុងទាញយកឯកសារ «{filename}» និងបំបែកជា Embeddings...</b>\n"
        "<i>ដំណើរការនេះអាចចំណាយពេលពីរបីវិនាទី សូមរង់ចាំ</i>",
        parse_mode=ParseMode.HTML
    )

    try:
        tg_file = await doc.get_file()
        file_bytes = await tg_file.download_as_bytearray()

        res = await index_pdf_document(filename, bytes(file_bytes))
        if res.get("success"):
            await wait_msg.edit_text(
                f"✅ <b>ជោគជ័យ!</b>\n{res['message']}\n\n"
                f"សិស្សអាចចាប់ផ្ដើមសួរមេរៀនតាមរយៈ <code>/ask &lt;សំណួរ&gt;</code> បានភ្លាមៗ!",
                parse_mode=ParseMode.HTML
            )
        else:
            await wait_msg.edit_text(
                f"❌ <b>បរាជ័យក្នុងការ Index៖</b>\n{res.get('error', 'Unknown error')}",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error("Failed to process uploaded PDF: %s", e)
        await wait_msg.edit_text(
            f"❌ <b>មានបញ្ហាបច្ចេកទេស៖</b> <code>{str(e)}</code>",
            parse_mode=ParseMode.HTML
        )


async def rag_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show RAG knowledge base status and loaded documents."""
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user or not is_admin(user.id):
        return

    docs = rag_db.get_documents()
    status_emoji = "🟢 កំពុងដំណើរការ (Active)" if is_rag_available() else "🔴 មិនទាន់ដាក់ GEMINI_API_KEY"

    msg = (
        "📚 <b>ស្ថានភាពប្រព័ន្ធ RAG AI Knowledge Base</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"• ស្ថានភាព AI៖ <b>{status_emoji}</b>\n"
        f"• ចំនួនសៀវភៅ/ឯកសារ PDF៖ <b>{len(docs)}</b> ក្បាល\n\n"
    )

    if docs:
        msg += "📋 <b>បញ្ជីឯកសារដែលបាន Upload៖</b>\n"
        for d in docs:
            msg += f"• 📄 <b>{d['filename']}</b> ({d['num_chunks']} កថាខណ្ឌ) — ID: <code>{d['id']}</code>\n"
        msg += "\n💡 <i>ដើម្បីលុបឯកសារ សូមប្រើ៖</i> <code>/rag_delete &lt;id&gt;</code>"
    else:
        msg += "<i>មិនទាន់មានឯកសារ PDF ណាមួយត្រូវបាន Upload ចូលប្រព័ន្ធនៅឡើយទេ។ លោកគ្រូគ្រាន់តែផ្ញើ File PDF ចូលឆាតនេះដើម្បីបញ្ចូល!</i>"

    await chat.send_message(msg, parse_mode=ParseMode.HTML)


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
        await chat.send_message(f"🗑 <b>បានលុបឯកសារ «{target_id}» ចេញពី RAG រួចរាល់!</b>", parse_mode=ParseMode.HTML)
    else:
        await chat.send_message(f"⚠️ រកមិនឃើញឯកសារដែលមាន ID «{target_id}» ទេ។", parse_mode=ParseMode.HTML)
