"""
Retrieval-Augmented Generation (RAG) Engine for Math Telegram Bot.
Uses Google Gemini API (100% Free Tier) for Embeddings and Generation,
and SQLite + NumPy for lightweight, fast vector similarity search without heavy dependencies.
"""

import io
import json
import logging
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np

from config import GEMINI_API_KEY, DATABASE_PATH

logger = logging.getLogger("MathBot.RAG")

# Configure Google Generative AI if key is present
_genai_configured = False
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _genai_configured = True
        logger.info("Google Gemini RAG engine initialized successfully!")
    except Exception as e:
        logger.error("Failed to initialize Google Generative AI: %s", e)


def is_rag_available() -> bool:
    """Check if RAG system has a valid Gemini API key configured."""
    return bool(GEMINI_API_KEY and _genai_configured)


class RAGDatabase:
    """Handles storage of RAG documents and vector embeddings in SQLite."""
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_rag_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_rag_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    num_chunks INTEGER NOT NULL,
                    created_at TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    FOREIGN KEY (doc_id) REFERENCES rag_documents (id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def save_document_chunks(self, doc_id: str, filename: str, file_type: str, chunks_with_embeddings: List[Tuple[str, List[float]]]):
        """Save a document and its embedded text chunks."""
        now = datetime.utcnow()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO rag_documents (id, filename, file_type, num_chunks, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (doc_id, filename, file_type, len(chunks_with_embeddings), now))

            # Delete any old chunks for this doc_id
            cursor.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))

            for idx, (content, embedding) in enumerate(chunks_with_embeddings):
                chunk_id = f"{doc_id}_{idx}"
                cursor.execute("""
                    INSERT INTO rag_chunks (id, doc_id, chunk_index, content, embedding_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (chunk_id, doc_id, idx, content, json.dumps(embedding)))

            conn.commit()

    def get_documents(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rag_documents ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def delete_document(self, doc_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))
            cursor.execute("DELETE FROM rag_documents WHERE id = ?", (doc_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get_all_chunks_with_embeddings(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT rc.id, rc.doc_id, rc.content, rc.embedding_json, rd.filename
                FROM rag_chunks rc
                JOIN rag_documents rd ON rc.doc_id = rd.id
            """)
            rows = cursor.fetchall()
            result = []
            for r in rows:
                result.append({
                    "id": r["id"],
                    "doc_id": r["doc_id"],
                    "content": r["content"],
                    "filename": r["filename"],
                    "embedding": json.loads(r["embedding_json"])
                })
            return result


rag_db = RAGDatabase()


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract full text from uploaded PDF document bytes."""
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    full_text = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            full_text.append(f"--- [ទំព័រ {i+1}] ---\n{page_text.strip()}")
    return "\n\n".join(full_text)


def chunk_text(text: str, chunk_size: int = 700, chunk_overlap: int = 120) -> List[str]:
    """Split text into overlapping semantic chunks respecting paragraphs and sentences."""
    cleaned = text.strip()
    if not cleaned:
        return []

    # First split by paragraphs
    paragraphs = cleaned.split("\n\n")
    chunks = []
    current_chunk = ""

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(current_chunk) + len(p) <= chunk_size:
            current_chunk += "\n\n" + p if current_chunk else p
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # If paragraph itself exceeds chunk_size, split by sentences or slice
            if len(p) > chunk_size:
                start = 0
                while start < len(p):
                    end = min(start + chunk_size, len(p))
                    chunks.append(p[start:end].strip())
                    start += (chunk_size - chunk_overlap)
                current_chunk = ""
            else:
                current_chunk = p

    if current_chunk:
        chunks.append(current_chunk.strip())

    return [c for c in chunks if len(c) > 25]


def get_embedding(text: str) -> List[float]:
    """Get vector embedding using Google Gemini models/gemini-embedding-001."""
    if not is_rag_available():
        raise ValueError("GEMINI_API_KEY is not configured or invalid.")
    import google.generativeai as genai
    response = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_document"
    )
    return response["embedding"]


def get_query_embedding(query: str) -> List[float]:
    """Get embedding for user search query."""
    if not is_rag_available():
        raise ValueError("GEMINI_API_KEY is not configured.")
    import google.generativeai as genai
    response = genai.embed_content(
        model="models/gemini-embedding-001",
        content=query,
        task_type="retrieval_query"
    )
    return response["embedding"]



def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


async def index_pdf_document(filename: str, pdf_bytes: bytes) -> Dict[str, Any]:
    """Extract, chunk, embed, and store a PDF document into RAG database."""
    if not is_rag_available():
        return {
            "success": False,
            "error": "សូមបញ្ចូល GEMINI_API_KEY ក្នុង .env ជាមុនសិន ដើម្បីប្រើប្រាស់មុខងារ RAG (Free នៅ aistudio.google.com/app/apikey)"
        }

    text = extract_text_from_pdf(pdf_bytes)
    if not text or len(text.strip()) < 30:
        return {"success": False, "error": "មិនអាចអានអត្ថបទចេញពី File PDF នេះបានទេ (អាចជា PDF រូបភាព Scan)"}

    chunks = chunk_text(text)
    if not chunks:
        return {"success": False, "error": "ឯកសារនេះទទេ ឬខ្លីពេក"}

    # Compute embeddings for chunks
    chunks_with_embeddings = []
    for chunk in chunks:
        emb = get_embedding(chunk)
        chunks_with_embeddings.append((chunk, emb))

    doc_id = f"doc_{int(datetime.utcnow().timestamp())}"
    rag_db.save_document_chunks(doc_id, filename, "pdf", chunks_with_embeddings)

    return {
        "success": True,
        "doc_id": doc_id,
        "filename": filename,
        "num_chunks": len(chunks),
        "message": f"បានបញ្ចូលឯកសារ «{filename}» ទៅក្នុង RAG ដោយជោគជ័យ (ចំនួន {len(chunks)} កថាខណ្ឌ)!"
    }


def search_knowledge_base(query: str, top_k: int = 3, similarity_threshold: float = 0.50) -> List[Dict[str, Any]]:
    """Search for relevant chunks using vector cosine similarity."""
    all_chunks = rag_db.get_all_chunks_with_embeddings()
    if not all_chunks:
        return []

    q_vec = np.array(get_query_embedding(query), dtype=np.float32)
    scored_chunks = []

    for item in all_chunks:
        c_vec = np.array(item["embedding"], dtype=np.float32)
        score = cosine_similarity(q_vec, c_vec)
        if score >= similarity_threshold:
            scored_chunks.append({
                "score": score,
                "content": item["content"],
                "filename": item["filename"],
                "doc_id": item["doc_id"]
            })

    # Sort descending by similarity score
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]


async def answer_with_rag(question: str) -> Dict[str, Any]:
    """
    RAG Pipeline:
    1. Retrieve relevant lesson chunks from teacher's documents.
    2. Prompt Gemini 1.5 Flash to synthesize an accurate, step-by-step math explanation.
    """
    if not is_rag_available():
        return {
            "success": False,
            "answer": (
                "⚠️ <b>ប្រព័ន្ធ RAG AI មិនទាន់ត្រូវបានបើកដំណើរការនៅឡើយទេ៖</b>\n\n"
                "សូមលោកគ្រូបញ្ចូល <b>GEMINI_API_KEY</b> ក្នុងឯកសារ <code>.env</code> ជាមុនសិន។\n"
                "👉 យក API Key ឥតគិតថ្លៃ (Free 100%) នៅ៖ https://aistudio.google.com/app/apikey"
            ),
            "sources": []
        }

    relevant_chunks = search_knowledge_base(question, top_k=3)
    
    # Format context from retrieved chunks
    if relevant_chunks:
        context_text = "\n\n".join([f"[ប្រភពពីឯកសារ៖ {c['filename']}]\n{c['content']}" for c in relevant_chunks])
    else:
        context_text = "មិនមានឯកសារផ្ទៃក្នុងជាក់លាក់សម្រាប់សំណួរនេះទេ។ សូមពន្យល់ដោយផ្អែកលើចំណេះដឹងគណិតវិទ្យាដេរីវេទូទៅ។"

    system_prompt = (
        "អ្នកគឺជាគ្រូបង្រៀនគណិតវិទ្យាដ៏ពូកែ និងរួសរាយរាក់ទាក់ម្នាក់នៅកម្ពុជា ដែលកំពុងជួយបង្រៀនសិស្សវិទ្យាល័យថ្នាក់ទី១១ និងទី១២ (ត្រៀមប្រឡងបាក់ឌុប) លើមេរៀន 'ដេរីវេនៃអនុគមន៍'។\n\n"
        "ការណែនាំសំខាន់ៗ៖\n"
        "១. សូមពន្យល់ជាភាសាខ្មែរយ៉ាងច្បាស់លាស់ មួយជំហានៗ (Step-by-step)។\n"
        "២. ប្រើប្រាស់រូបមន្តគណិតវិទ្យា និងនិមិត្តសញ្ញាឱ្យបានត្រឹមត្រូវ និងស្អាតបាត (ឧ. (u/v)' = (u'v - uv')/v² , (sin x)' = cos x)។\n"
        "៣. ផ្អែកលើខ្លឹមសារមេរៀនខាងក្រោមនេះ ដើម្បីឆ្លើយឱ្យស៊ីគ្នាជាមួយវិធីសាស្រ្តបង្រៀនរបស់លោកគ្រូ។\n"
        "៤. បង្ហាញការលើកទឹកចិត្ត និងភាពកក់ក្ដៅដល់សិស្ស។\n\n"
        f"ខ្លឹមសារឯកសារមេរៀនយោង (Context)៖\n{context_text}"
    )

    try:
        import google.generativeai as genai
        model = genai.GenerativeModel("models/gemini-3.6-flash", system_instruction=system_prompt)
        response = await model.generate_content_async(question)
        answer_text = response.text.strip()


        sources = list(set([c["filename"] for c in relevant_chunks]))
        return {
            "success": True,
            "answer": answer_text,
            "sources": sources
        }
    except Exception as e:
        logger.error("Gemini generation failed: %s", e)
        return {
            "success": False,
            "answer": f"❌ មានបញ្ហាបច្ចេកទេសក្នុងការឆ្លើយតបពី AI៖ <code>{str(e)}</code>",
            "sources": []
        }
