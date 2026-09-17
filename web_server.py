"""
Lightweight Asynchronous HTTP Web Server & Teacher Management Portal.
Provides:
1. Health check endpoint for Cloud deployments (Render, Koyeb)
2. Interactive Web Portal at /admin for adding, editing, and managing math exercises easily.
"""

import json
import logging
from aiohttp import web
from config import PORT, GOOGLE_SHEET_VIEW_URL, GOOGLE_SHEET_CSV_URL, GEMINI_API_KEY
from database import db
from sheets_sync import sync_from_google_sheet
from rag_engine import rag_db, is_rag_available, index_pdf_document, answer_with_rag

logger = logging.getLogger("MathBot.WebServer")




async def health_check_handler(request):
    """Simple healthcheck endpoint."""
    stats = db.get_stats()
    return web.json_response({
        "status": "healthy",
        "service": "Telegram Math Derivative Bot",
        "registered_students": stats["total_users"],
        "exercises_count": stats["total_exercises"],
        "formulas_count": stats["total_formulas"]
    })


async def get_exercises_api(request):
    """API endpoint returning all exercises."""
    return web.json_response(db.get_exercises())


async def add_exercise_api(request):
    """API endpoint to create or update an exercise."""
    try:
        data = await request.json()
        if not data.get("title") or not data.get("problem"):
            return web.json_response({"error": "Title and Problem are required"}, status=400)

        # Process solution steps
        raw_steps = data.get("solution_steps", [])
        if isinstance(raw_steps, str):
            steps = [s.strip() for s in raw_steps.split("||") if s.strip()]
        else:
            steps = raw_steps

        # Process keywords
        raw_kw = data.get("keywords", [])
        if isinstance(raw_kw, str):
            kw = [k.strip() for k in raw_kw.split(",") if k.strip()]
        else:
            kw = raw_kw

        ex_payload = {
            "id": data.get("id") or data.get("code") or f"ex_{int(request.loop.time())}",
            "code": data.get("code", "លំហាត់"),
            "category_id": data.get("category_id", "basic"),
            "title": data.get("title"),
            "problem": data.get("problem"),
            "hints": data.get("hints", ""),
            "solution_steps": steps,
            "final_answer": data.get("final_answer", ""),
            "difficulty": data.get("difficulty", "មធ្យម"),
            "keywords": kw
        }
        saved_id = db.save_exercise(ex_payload)
        return web.json_response({"success": True, "id": saved_id})
    except Exception as e:
        logger.error("Failed to add exercise via API: %s", e)
        return web.json_response({"error": str(e)}, status=500)


async def delete_exercise_api(request):
    """API endpoint to delete an exercise."""
    ex_id = request.match_info.get("id")
    deleted = db.delete_exercise(ex_id)
    return web.json_response({"success": deleted})


async def sync_sheet_api(request):
    """API endpoint to trigger Google Sheet CSV synchronization."""
    try:
        data = await request.json() if request.can_read_body else {}
    except Exception:
        data = {}
    csv_url = data.get("csv_url") or GOOGLE_SHEET_CSV_URL
    try:
        res = await sync_from_google_sheet(csv_url=csv_url)
        return web.json_response(res)
    except Exception as e:
        logger.error("API sheet sync failed: %s", e)
        return web.json_response({"status": "error", "message": str(e)}, status=400)


async def get_rag_docs_api(request):
    """API returning list of uploaded RAG documents."""
    return web.json_response({
        "rag_available": is_rag_available(),
        "documents": rag_db.get_documents()
    })


async def upload_rag_pdf_api(request):
    """API to upload and index PDF document for RAG."""
    if not is_rag_available():
        return web.json_response({
            "success": False,
            "error": "សូមកំណត់ GEMINI_API_KEY ក្នុង .env ជាមុនសិន (Free នៅ aistudio.google.com/app/apikey)"
        }, status=400)

    try:
        reader = await request.multipart()
        field = await reader.next()
        if not field or field.name != "pdf_file":
            return web.json_response({"success": False, "error": "No file field found"}, status=400)

        filename = field.filename or "document.pdf"
        file_bytes = await field.read()
        res = await index_pdf_document(filename, file_bytes)
        return web.json_response(res, status=200 if res.get("success") else 400)
    except Exception as e:
        logger.error("Failed to upload PDF via API: %s", e)
        return web.json_response({"success": False, "error": str(e)}, status=500)


async def delete_rag_doc_api(request):
    """API to delete document from RAG."""
    doc_id = request.match_info.get("id")
    deleted = rag_db.delete_document(doc_id)
    return web.json_response({"success": deleted})


async def ask_rag_api(request):
    """API to test asking question to RAG AI."""
    data = await request.json()
    q = data.get("question", "").strip()
    if not q:
        return web.json_response({"error": "Question is required"}, status=400)
    res = await answer_with_rag(q)
    return web.json_response(res)




async def admin_portal_handler(request):
    """Interactive Khmer & English Teacher Web Portal for managing exercises."""
    stats = db.get_stats()
    html_content = f"""
    <!DOCTYPE html>
    <html lang="km">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ផ្ទាំងគ្រប់គ្រងលំហាត់ - Kru Math Bot</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Kantumruy+Pro:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-main: #0b0f19;
                --bg-card: #151d30;
                --bg-input: #1e293b;
                --primary: #38bdf8;
                --primary-hover: #0284c7;
                --accent: #10b981;
                --danger: #ef4444;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --border: #26354f;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: 'Kantumruy Pro', -apple-system, BlinkMacSystemFont, sans-serif;
                background-color: var(--bg-main);
                color: var(--text-main);
                padding: 1.5rem;
                min-height: 100vh;
            }}
            .container {{ max-width: 1100px; margin: 0 auto; }}
            header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding-bottom: 1.5rem;
                border-bottom: 1px solid var(--border);
                margin-bottom: 2rem;
            }}
            .brand h1 {{ font-size: 1.6rem; color: var(--primary); font-weight: 700; }}
            .brand p {{ color: var(--text-muted); font-size: 0.95rem; }}
            .stats-bar {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}
            .stat-card {{
                background: var(--bg-card);
                border: 1px solid var(--border);
                padding: 1.25rem;
                border-radius: 0.75rem;
                text-align: center;
            }}
            .stat-card .num {{ font-size: 1.8rem; font-weight: 700; color: var(--primary); }}
            .stat-card .label {{ color: var(--text-muted); font-size: 0.85rem; margin-top: 0.3rem; }}
            
            .content-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 2rem;
            }}
            @media (max-width: 860px) {{
                .content-grid {{ grid-template-columns: 1fr; }}
            }}
            
            .card {{
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 0.75rem;
                padding: 1.5rem;
            }}
            .card h2 {{
                font-size: 1.25rem;
                margin-bottom: 1.2rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                color: #fff;
            }}
            .form-group {{ margin-bottom: 1rem; }}
            label {{ display: block; margin-bottom: 0.4rem; font-size: 0.9rem; color: var(--text-muted); font-weight: 500; }}
            input, select, textarea {{
                width: 100%;
                padding: 0.7rem 0.9rem;
                background: var(--bg-input);
                border: 1px solid var(--border);
                border-radius: 0.5rem;
                color: #fff;
                font-family: inherit;
                font-size: 0.95rem;
                transition: border-color 0.2s;
            }}
            input:focus, select:focus, textarea:focus {{
                outline: none;
                border-color: var(--primary);
            }}
            textarea {{ resize: vertical; min-height: 80px; }}
            .btn {{
                background: var(--primary);
                color: #0b0f19;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 0.5rem;
                font-weight: 600;
                font-size: 0.95rem;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                transition: all 0.2s;
            }}
            .btn:hover {{ background: var(--primary-hover); color: #fff; }}
            .btn-danger {{ background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444; padding: 0.35rem 0.75rem; font-size: 0.8rem; border-radius: 0.4rem; cursor: pointer; }}
            .btn-danger:hover {{ background: #ef4444; color: #fff; }}
            
            .exercise-list {{
                display: flex;
                flex-direction: column;
                gap: 1rem;
                max-height: 620px;
                overflow-y: auto;
                padding-right: 0.5rem;
            }}
            .ex-item {{
                background: var(--bg-input);
                border: 1px solid var(--border);
                border-radius: 0.5rem;
                padding: 1rem;
                position: relative;
            }}
            .ex-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }}
            .ex-badge {{
                background: rgba(56, 189, 248, 0.15);
                color: var(--primary);
                padding: 0.2rem 0.6rem;
                border-radius: 9999px;
                font-size: 0.8rem;
                font-weight: 600;
            }}
            .ex-title {{ font-weight: 600; font-size: 1rem; color: #fff; }}
            .ex-problem {{ color: #cbd5e1; font-size: 0.9rem; margin-bottom: 0.5rem; background: rgba(0,0,0,0.2); padding: 0.5rem; border-radius: 0.3rem; }}
            .ex-ans {{ color: var(--accent); font-size: 0.85rem; font-weight: 500; }}
            .toast {{
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                background: var(--accent);
                color: #fff;
                padding: 0.9rem 1.4rem;
                border-radius: 0.5rem;
                box-shadow: 0 10px 20px rgba(0,0,0,0.4);
                display: none;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="brand">
                    <h1>👨‍🏫 ផ្ទាំងគ្រប់គ្រងលំហាត់គណិតវិទ្យា (Math Teacher Portal)</h1>
                    <p>បញ្ចូល និងកែប្រែលំហាត់ដេរីវេសម្រាប់ Telegram Bot (@kru_mathbot)</p>
                </div>
                <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                    <a href="{GOOGLE_SHEET_VIEW_URL or 'https://docs.google.com/spreadsheets'}" target="_blank" class="btn" style="background: #10b981; color: #fff;">
                        📊 បើក Google Sheet
                    </a>
                    <a href="https://t.me/kru_mathbot" target="_blank" class="btn">
                        🤖 បើក Telegram Bot
                    </a>
                </div>
            </header>

            <!-- Google Sheet Live Sync Banner -->
            <div class="card" style="margin-bottom: 2rem; background: linear-gradient(135deg, #132238 0%, #0f172a 100%); border-color: #10b981;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                    <div>
                        <h2 style="color: #10b981; font-size: 1.15rem; margin-bottom: 0.3rem;">📊 ភ្ជាប់ និងធ្វើសមកាលកម្ម Google Sheet</h2>
                        <p style="color: #94a3b8; font-size: 0.85rem;">លោកគ្រូអាចចុចបើកមើល Sheet ឬបញ្ចូល Published CSV URL ដើម្បីទាញយកលំហាត់ថ្មីៗដោយស្វ័យប្រវត្តិ</p>
                    </div>
                    <div style="display: flex; gap: 0.6rem; flex-wrap: wrap; width: 100%; max-width: 580px;">
                        <input type="url" id="sheet_csv_url" value="{GOOGLE_SHEET_CSV_URL}" placeholder="Paste Google Sheet CSV URL (ឧ. https://docs.google.com/.../pub?output=csv)" style="flex: 1; font-size: 0.85rem;">
                        <button onclick="triggerSheetSync()" class="btn" style="background: #0284c7; color: #fff; white-space: nowrap;">
                            🔄 Sync ឥឡូវនេះ
                        </button>
                    </div>
                </div>
            </div>

            <div class="stats-bar">
                <div class="stat-card">
                    <div class="num" id="stat-exercises">{stats['total_exercises']}</div>
                    <div class="label">លំហាត់អនុវត្តសរុប</div>
                </div>
                <div class="stat-card">
                    <div class="num">{stats['total_formulas']}</div>
                    <div class="label">រូបមន្តដេរីវេ</div>
                </div>
                <div class="stat-card">
                    <div class="num">{stats['total_users']}</div>
                    <div class="label">សិស្សចុះឈ្មោះប្រើ</div>
                </div>
                <div class="stat-card">
                    <div class="num">{stats['total_searches']}</div>
                    <div class="label">ដងនៃការស្វែងរក</div>
                </div>
            </div>


            <div class="content-grid">
                <!-- Add Exercise Form -->
                <div class="card">
                    <h2>➕ បញ្ចូលលំហាត់ថ្មី (Add New Exercise)</h2>
                    <form id="addForm">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                            <div class="form-group">
                                <label>កូដលំហាត់ (Code) *</label>
                                <input type="text" id="code" placeholder="ឧ. លំហាត់៩, លំហាត់១០" required>
                            </div>
                            <div class="form-group">
                                <label>ជំពូក / ផ្នែក (Category) *</label>
                                <select id="category_id">
                                    <option value="basic">រូបមន្តគ្រឹះ & ស្វ័យគុណ (Basic)</option>
                                    <option value="arithmetic">ផលបូក ផលគុណ ផលចែក (Arithmetic)</option>
                                    <option value="chain_rule">ដេរីវេបណ្ដាក់ (Chain Rule)</option>
                                    <option value="trig">ត្រីកោណមាត្រ (Trigonometric)</option>
                                    <option value="exp_log">អិចស្បូណង់ស្យែល & លោការីត (Exp/Log)</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-group">
                            <label>ចំណងជើងលំហាត់ (Title) *</label>
                            <input type="text" id="title" placeholder="ឧ. ដេរីវេនៃអនុគមន៍តង់សង់ y = tan(3x)" required>
                        </div>

                        <div class="form-group">
                            <label>ប្រធានលំហាត់ (Problem Statement) *</label>
                            <textarea id="problem" placeholder="ឧ. គណនាដេរីវេនៃ y = tan(3x)" required></textarea>
                        </div>

                        <div class="form-group">
                            <label>តម្រុយ (Hints - Optional)</label>
                            <input type="text" id="hints" placeholder="ឧ. ប្រើរូបមន្ត (tan u)' = u' / cos²(u)">
                        </div>

                        <div class="form-group">
                            <label>ជំហានដំណោះស្រាយ (Solution Steps) *</label>
                            <textarea id="solution_steps" style="min-height: 110px;" placeholder="សរសេរដំណោះស្រាយបំបែកតាមជំហានដោយប្រើសញ្ញា || ឧទាហរណ៍៖&#10;ជំហានទី១៖ តាង u = 3x នាំឱ្យ u' = 3 || ជំហានទី២៖ y' = (3x)' / cos²(3x) = 3 / cos²(3x)" required></textarea>
                        </div>

                        <div class="form-group">
                            <label>ចម្លើយចុងក្រោយ (Final Answer) *</label>
                            <input type="text" id="final_answer" placeholder="ឧ. y' = 3 / cos²(3x)" required>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                            <div class="form-group">
                                <label>កម្រិតលំបាក (Difficulty)</label>
                                <select id="difficulty">
                                    <option value="ងាយស្រួល (Basic)">ងាយស្រួល (Basic)</option>
                                    <option value="មធ្យម (Intermediate)" selected>មធ្យម (Intermediate)</option>
                                    <option value="បាក់ឌុប (BacII Exam)">បាក់ឌុប (BacII Exam)</option>
                                    <option value="កម្រិតខ្ពស់ (Advanced)">កម្រិតខ្ពស់ (Advanced)</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>ពាក្យគន្លឹះស្វែងរក (Keywords)</label>
                                <input type="text" id="keywords" placeholder="ឧ. tan, tan(3x), លំហាត់៩">
                            </div>
                        </div>

                        <button type="submit" class="btn" style="width: 100%; justify-content: center; margin-top: 0.5rem;">
                            💾 រក្សាទុក និងបញ្ចូលទៅក្នុង Bot
                        </button>
                    </form>
                </div>

                <!-- Exercise List -->
                <div class="card">
                    <h2>📋 បញ្ជីលំហាត់កំពុងដំណើរការ (<span id="count-span">0</span>)</h2>
                    <div class="exercise-list" id="exList">
                        <!-- Loaded dynamically -->
                    </div>
                </div>
            </div>

            <!-- RAG Knowledge Base Section -->
            <div class="card" style="margin-top: 2rem; border-color: #38bdf8;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.2rem;">
                    <div>
                        <h2 style="color: #38bdf8; margin-bottom: 0.3rem;">📚 RAG AI Knowledge Base (សៀវភៅ & ឯកសារ PDF)</h2>
                        <p style="color: #94a3b8; font-size: 0.9rem;">ផ្ទុកឯកសារ PDF ចូលទៅក្នុង AI ដើម្បីឱ្យ Bot ចងចាំ និងអាចពន្យល់សិស្សតាមក្បួនសៀវភៅរបស់លោកគ្រូ</p>
                    </div>
                    <span id="rag-badge" class="ex-badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981; font-size: 0.9rem; padding: 0.4rem 0.8rem;">
                        ● Gemini AI: កំពុងពិនិត្យ...
                    </span>
                </div>

                <div class="content-grid" style="margin-top: 1rem;">
                    <!-- Upload PDF form -->
                    <div style="background: var(--bg-input); padding: 1.2rem; border-radius: 0.5rem; border: 1px dashed var(--border);">
                        <h3 style="font-size: 1rem; margin-bottom: 0.8rem; color: #fff;">📤 Upload ឯកសារ PDF មេរៀនថ្មី</h3>
                        <form id="uploadPdfForm">
                            <input type="file" id="pdfFileInput" accept=".pdf" required style="margin-bottom: 0.8rem;">
                            <button type="submit" id="btnUploadPdf" class="btn" style="width: 100%; justify-content: center; background: #38bdf8;">
                                🚀 បញ្ចូលឯកសារទៅក្នុង RAG AI
                            </button>
                        </form>
                        <p style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.8rem;">
                            💡 <i>គន្លឹះ៖ លោកគ្រូក៏អាចផ្ញើ File PDF ចូលទៅក្នុង Telegram Bot ដោយផ្ទាល់បានដែរ!</i>
                        </p>
                    </div>

                    <!-- PDF documents list -->
                    <div>
                        <h3 style="font-size: 1rem; margin-bottom: 0.8rem; color: #fff;">📋 សៀវភៅ/ឯកសារដែលបាន Upload រួច (<span id="rag-doc-count">0</span>)</h3>
                        <div id="ragDocsList" style="display: flex; flex-direction: column; gap: 0.6rem; max-height: 250px; overflow-y: auto;">
                            <!-- Loaded dynamically -->
                        </div>
                    </div>
                </div>

                <!-- Test Ask RAG section -->
                <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border);">
                    <h3 style="font-size: 1rem; margin-bottom: 0.8rem; color: #fff;">💬 សាកល្បងសួរសំណួរទៅកាន់ RAG AI (Test Question)</h3>
                    <div style="display: flex; gap: 0.6rem;">
                        <input type="text" id="ragTestInput" placeholder="ឧ. តើដេរីវេនៃ sin(3x) គណនាយ៉ាងម៉េច? ឬ ច្បាប់ផលគុណ..." style="flex: 1;">
                        <button onclick="testAskRag()" id="btnAskRag" class="btn" style="background: #10b981; color: #fff; white-space: nowrap;">
                            🧠 សួរ AI
                        </button>
                    </div>
                    <div id="ragAnswerBox" style="display: none; margin-top: 1rem; background: var(--bg-input); padding: 1rem; border-radius: 0.5rem; border-left: 3px solid #10b981; line-height: 1.6; font-size: 0.95rem; white-space: pre-wrap;"></div>
                </div>
            </div>
        </div>


        <div class="toast" id="toast"></div>

        <script>
            function showToast(msg) {{
                const t = document.getElementById('toast');
                t.innerText = msg;
                t.style.display = 'block';
                setTimeout(() => {{ t.style.display = 'none'; }}, 3000);
            }}

            async function loadExercises() {{
                const res = await fetch('/api/exercises');
                const list = await res.json();
                document.getElementById('count-span').innerText = list.length;
                document.getElementById('stat-exercises').innerText = list.length;
                const container = document.getElementById('exList');
                container.innerHTML = '';
                
                list.forEach(ex => {{
                    const el = document.createElement('div');
                    el.className = 'ex-item';
                    el.innerHTML = `
                        <div class="ex-header">
                            <div>
                                <span class="ex-badge">${{ex.code || ex.id}}</span>
                                <span style="font-size: 0.8rem; color: #94a3b8; margin-left: 0.4rem;">${{ex.difficulty || ''}}</span>
                            </div>
                            <button class="btn-danger" onclick="deleteEx('${{ex.id}}')">🗑 លុប</button>
                        </div>
                        <div class="ex-title">${{ex.title}}</div>
                        <div class="ex-problem">❓ <b>ប្រធាន៖</b> ${{ex.problem}}</div>
                        <div class="ex-ans">✅ <b>ចម្លើយ៖</b> ${{ex.final_answer}}</div>
                    `;
                    container.appendChild(el);
                }});
            }}

            document.getElementById('addForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const payload = {{
                    code: document.getElementById('code').value.trim(),
                    category_id: document.getElementById('category_id').value,
                    title: document.getElementById('title').value.trim(),
                    problem: document.getElementById('problem').value.trim(),
                    hints: document.getElementById('hints').value.trim(),
                    solution_steps: document.getElementById('solution_steps').value.trim(),
                    final_answer: document.getElementById('final_answer').value.trim(),
                    difficulty: document.getElementById('difficulty').value,
                    keywords: document.getElementById('keywords').value.trim()
                }};

                const res = await fetch('/api/exercises', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(payload)
                }});

                if (res.ok) {{
                    showToast('✅ បានបញ្ចូលលំហាត់ថ្មីដោយជោគជ័យ!');
                    document.getElementById('addForm').reset();
                    loadExercises();
                }} else {{
                    alert('មានបញ្ហាក្នុងការបញ្ចូល');
                }}
            }});

            async function deleteEx(id) {{
                if (!confirm('តើលោកគ្រូពិតជាចង់លុបលំហាត់នេះមែនទេ?')) return;
                const res = await fetch('/api/exercises/' + encodeURIComponent(id), {{ method: 'DELETE' }});
                if (res.ok) {{
                    showToast('🗑 បានលុបលំហាត់រួចរាល់!');
                    loadExercises();
                }}
            }}

            async function triggerSheetSync() {{
                const url = document.getElementById('sheet_csv_url').value.trim();
                showToast('⏳ កំពុងទាញយកទិន្នន័យពី Google Sheets...');
                try {{
                    const res = await fetch('/api/sync_sheet', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ csv_url: url }})
                    }});
                    const data = await res.json();
                    if (res.ok) {{
                        showToast('✅ ' + data.message);
                        loadExercises();
                    }} else {{
                        alert('❌ ' + (data.message || 'បរាជ័យក្នុងការ Sync'));
                    }}
                }} catch (err) {{
                    alert('❌ បរាជ័យក្នុងការតភ្ជាប់៖ ' + err);
                }}
            }}

            async function loadRagDocs() {{
                try {{
                    const res = await fetch('/api/rag/docs');
                    const data = await res.json();
                    const badge = document.getElementById('rag-badge');
                    if (data.rag_available) {{
                        badge.innerText = '● Gemini AI: ដំណើរការ (Active)';
                        badge.style.background = 'rgba(16, 185, 129, 0.2)';
                        badge.style.color = '#10b981';
                    }} else {{
                        badge.innerText = '● ត្រូវការ GEMINI_API_KEY';
                        badge.style.background = 'rgba(239, 68, 68, 0.2)';
                        badge.style.color = '#ef4444';
                    }}

                    const docs = data.documents || [];
                    document.getElementById('rag-doc-count').innerText = docs.length;
                    const container = document.getElementById('ragDocsList');
                    container.innerHTML = '';
                    if (docs.length === 0) {{
                        container.innerHTML = '<p style="color: #94a3b8; font-size: 0.85rem; font-style: italic;">មិនទាន់មានឯកសារ PDF នៅឡើយទេ។</p>';
                        return;
                    }}
                    docs.forEach(d => {{
                        const item = document.createElement('div');
                        item.className = 'ex-item';
                        item.style.padding = '0.6rem 0.8rem';
                        item.innerHTML = `
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <div style="font-weight: 600; font-size: 0.9rem; color: #fff;">📄 ${{d.filename}}</div>
                                    <div style="font-size: 0.75rem; color: #94a3b8;">${{d.num_chunks}} កថាខណ្ឌ</div>
                                </div>
                                <button class="btn-danger" onclick="deleteRagDoc('${{d.id}}')">🗑 លុប</button>
                            </div>
                        `;
                        container.appendChild(item);
                    }});
                }} catch (e) {{
                    console.error('Failed to load RAG docs:', e);
                }}
            }}

            document.getElementById('uploadPdfForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                const fileInput = document.getElementById('pdfFileInput');
                if (!fileInput.files || fileInput.files.length === 0) return;
                const file = fileInput.files[0];

                const formData = new FormData();
                formData.append('pdf_file', file);

                const btn = document.getElementById('btnUploadPdf');
                btn.disabled = true;
                btn.innerText = '⏳ កំពុងដំណើរការ...';
                showToast('⏳ កំពុងទាញយក និងបំបែកជា Embeddings...');

                try {{
                    const res = await fetch('/api/rag/upload', {{
                        method: 'POST',
                        body: formData
                    }});
                    const data = await res.json();
                    if (res.ok) {{
                        showToast('✅ ' + data.message);
                        document.getElementById('uploadPdfForm').reset();
                        loadRagDocs();
                    }} else {{
                        alert('❌ ' + (data.error || 'បរាជ័យក្នុងការ Upload'));
                    }}
                }} catch (err) {{
                    alert('❌ បរាជ័យក្នុងការ Upload៖ ' + err);
                }} finally {{
                    btn.disabled = false;
                    btn.innerText = '🚀 បញ្ចូលឯកសារទៅក្នុង RAG AI';
                }}
            }});

            async function deleteRagDoc(id) {{
                if (!confirm('តើលោកគ្រូពិតជាចង់លុបឯកសារនេះចេញពី RAG មែនទេ?')) return;
                const res = await fetch('/api/rag/docs/' + encodeURIComponent(id), {{ method: 'DELETE' }});
                if (res.ok) {{
                    showToast('🗑 បានលុបឯកសាររួចរាល់!');
                    loadRagDocs();
                }}
            }}

            async function testAskRag() {{
                const q = document.getElementById('ragTestInput').value.trim();
                if (!q) return;
                const ansBox = document.getElementById('ragAnswerBox');
                const btn = document.getElementById('btnAskRag');
                ansBox.style.display = 'block';
                ansBox.innerHTML = '<i>🧠 កំពុងពិចារណា និងស្វែងរកក្នុងសៀវភៅ... សូមរង់ចាំបន្តិច ⏳</i>';
                btn.disabled = true;

                try {{
                    const res = await fetch('/api/rag/ask', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ question: q }})
                    }});
                    const data = await res.json();
                    if (data.answer) {{
                        let html = data.answer;
                        if (data.sources && data.sources.length > 0) {{
                            html += '<br><br><b>📚 ឯកសារយោង៖</b> ' + data.sources.join(', ');
                        }}
                        ansBox.innerHTML = html;
                    }} else {{
                        ansBox.innerHTML = '❌ មិនអាចទទួលបានចម្លើយ៖ ' + (data.error || 'Unknown error');
                    }}
                }} catch (err) {{
                    ansBox.innerHTML = '❌ មានបញ្ហាតភ្ជាប់៖ ' + err;
                }} finally {{
                    btn.disabled = false;
                }}
            }}

            loadExercises();
            loadRagDocs();
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type="text/html")


def make_web_app():
    """Create aiohttp web application."""
    app = web.Application()
    app.router.add_get("/", admin_portal_handler)
    app.router.add_get("/admin", admin_portal_handler)
    app.router.add_get("/health", health_check_handler)
    app.router.add_get("/api/exercises", get_exercises_api)
    app.router.add_post("/api/exercises", add_exercise_api)
    app.router.add_delete("/api/exercises/{id}", delete_exercise_api)
    app.router.add_post("/api/sync_sheet", sync_sheet_api)
    app.router.add_get("/api/rag/docs", get_rag_docs_api)
    app.router.add_post("/api/rag/upload", upload_rag_pdf_api)
    app.router.add_delete("/api/rag/docs/{id}", delete_rag_doc_api)
    app.router.add_post("/api/rag/ask", ask_rag_api)
    return app




async def start_web_server(port: int = PORT):
    """Start the web server in the existing asyncio event loop."""
    app = make_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health check HTTP server started on http://0.0.0.0:%s", port)
    return runner

