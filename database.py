"""
SQLite Database Layer for Math Telegram Bot.
Handles persistence for formulas, exercises, users, and usage statistics.
Automatically seeds initial data from lessons.json.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import DATABASE_PATH, LESSONS_JSON_PATH

logger = logging.getLogger("MathBot.Database")


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create tables if they don't exist and auto-seed initial data."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY,
                    name_km TEXT NOT NULL,
                    name_en TEXT,
                    description TEXT,
                    sort_order INTEGER DEFAULT 0
                )
            """)
            try:
                cursor.execute("ALTER TABLE categories ADD COLUMN sort_order INTEGER DEFAULT 0")
            except Exception:
                pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS formulas (
                    id TEXT PRIMARY KEY,
                    category_id TEXT,
                    title_km TEXT NOT NULL,
                    title_en TEXT,
                    formula TEXT NOT NULL,
                    explanation TEXT,
                    example TEXT,
                    keywords TEXT,
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS exercises (
                    id TEXT PRIMARY KEY,
                    category_id TEXT,
                    code TEXT UNIQUE,
                    title TEXT NOT NULL,
                    problem TEXT NOT NULL,
                    hints TEXT,
                    solution_steps TEXT NOT NULL,
                    final_answer TEXT NOT NULL,
                    difficulty TEXT,
                    keywords TEXT,
                    FOREIGN KEY (category_id) REFERENCES categories (id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen TIMESTAMP,
                    last_active TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    query TEXT,
                    created_at TIMESTAMP
                )
            """)
            conn.commit()

        # Sync categories, formulas, and exercises from lessons.json on startup
        self._seed_or_sync_lessons()

    def _seed_or_sync_lessons(self):
        """Seed or sync categories, formulas, and exercises from lessons.json."""
        json_path = Path(LESSONS_JSON_PATH)
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.import_json_data(data)
                logger.info("Successfully synced database from %s", LESSONS_JSON_PATH)
            except Exception as e:
                logger.error("Failed to sync database from %s: %s", LESSONS_JSON_PATH, e)

    def import_json_data(self, data: Dict[str, Any], overwrite: bool = True):
        """Import lessons, formulas, and exercises from JSON dictionary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Import categories
            for cat in data.get("categories", []):
                cursor.execute("""
                    INSERT INTO categories (id, name_km, name_en, description, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name_km = excluded.name_km,
                        name_en = excluded.name_en,
                        description = excluded.description,
                        sort_order = excluded.sort_order
                """, (cat["id"], cat["name_km"], cat.get("name_en", ""), cat.get("description", ""), cat.get("sort_order", 0)))

            # Import formulas
            for form in data.get("formulas", []):
                keywords_str = ",".join(form.get("keywords", [])) if isinstance(form.get("keywords"), list) else form.get("keywords", "")
                cursor.execute("""
                    INSERT INTO formulas (id, category_id, title_km, title_en, formula, explanation, example, keywords)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        category_id = excluded.category_id,
                        title_km = excluded.title_km,
                        title_en = excluded.title_en,
                        formula = excluded.formula,
                        explanation = excluded.explanation,
                        example = excluded.example,
                        keywords = excluded.keywords
                """, (
                    form["id"],
                    form.get("category_id", "basic"),
                    form["title_km"],
                    form.get("title_en", ""),
                    form["formula"],
                    form.get("explanation", ""),
                    form.get("example", ""),
                    keywords_str
                ))

            # Import exercises
            for ex in data.get("exercises", []):
                solution_steps_str = json.dumps(ex["solution_steps"], ensure_ascii=False) if isinstance(ex.get("solution_steps"), list) else str(ex.get("solution_steps", ""))
                keywords_str = ",".join(ex.get("keywords", [])) if isinstance(ex.get("keywords"), list) else ex.get("keywords", "")

                cursor.execute("""
                    INSERT INTO exercises (id, category_id, code, title, problem, hints, solution_steps, final_answer, difficulty, keywords)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        category_id = excluded.category_id,
                        code = excluded.code,
                        title = excluded.title,
                        problem = excluded.problem,
                        hints = excluded.hints,
                        solution_steps = excluded.solution_steps,
                        final_answer = excluded.final_answer,
                        difficulty = excluded.difficulty,
                        keywords = excluded.keywords
                """, (
                    ex["id"],
                    ex.get("category_id", "basic"),
                    ex.get("code", ex["id"]),
                    ex["title"],
                    ex["problem"],
                    ex.get("hints", ""),
                    solution_steps_str,
                    ex.get("final_answer", ""),
                    ex.get("difficulty", "មធ្យម"),
                    keywords_str
                ))

            conn.commit()

    # --- User Tracking ---
    def track_user(self, user_id: int, username: Optional[str], first_name: Optional[str], last_name: Optional[str]):
        """Record or update user activity."""
        now = datetime.utcnow()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, first_seen, last_active)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_active = excluded.last_active
            """, (user_id, username, first_name, last_name, now, now))
            conn.commit()

    def log_search(self, user_id: int, query: str):
        """Log a user's search query."""
        now = datetime.utcnow()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO search_logs (user_id, query, created_at)
                VALUES (?, ?, ?)
            """, (user_id, query, now))
            conn.commit()

    def get_all_user_ids(self) -> List[int]:
        """Get all user IDs registered with the bot (for teacher announcements)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            return [row["user_id"] for row in cursor.fetchall()]

    # --- Queries ---
    def get_categories(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories ORDER BY sort_order ASC, rowid ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_formulas(self, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category_id:
                cursor.execute("SELECT * FROM formulas WHERE category_id = ?", (category_id,))
            else:
                cursor.execute("SELECT * FROM formulas")
            return [dict(row) for row in cursor.fetchall()]

    def get_formula_by_id(self, formula_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM formulas WHERE id = ?", (formula_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_exercises(self, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category_id:
                cursor.execute("SELECT * FROM exercises WHERE category_id = ?", (category_id,))
            else:
                cursor.execute("SELECT * FROM exercises")
            rows = cursor.fetchall()
            result = []
            for row in rows:
                item = dict(row)
                try:
                    item["solution_steps"] = json.loads(item["solution_steps"])
                except Exception:
                    item["solution_steps"] = [item["solution_steps"]]
                result.append(item)
            return result

    def get_exercise_by_id(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            try:
                item["solution_steps"] = json.loads(item["solution_steps"])
            except Exception:
                item["solution_steps"] = [item["solution_steps"]]
            return item

    def get_exercise_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM exercises WHERE LOWER(code) = LOWER(?) OR LOWER(id) = LOWER(?)", (code, code))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            try:
                item["solution_steps"] = json.loads(item["solution_steps"])
            except Exception:
                item["solution_steps"] = [item["solution_steps"]]
            return item

    def search(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search formulas and exercises by keyword, title, problem, code, or formula.
        Supports Khmer digits and text.
        """
        q = query.strip().lower()
        # Khmer to Arabic numeral normalizer helper for search
        khmer_to_arabic = {"១": "1", "២": "2", "៣": "3", "៤": "4", "៥": "5", "៦": "6", "៧": "7", "៨": "8", "៩": "9", "០": "0"}
        arabic_to_khmer = {v: k for k, v in khmer_to_arabic.items()}
        q_alt = q
        for k, v in khmer_to_arabic.items():
            if k in q_alt:
                q_alt = q_alt.replace(k, v)
        for k, v in arabic_to_khmer.items():
            if k in q:
                q_alt = q.replace(k, v)

        search_term = f"%{q}%"
        search_alt = f"%{q_alt}%"

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Search formulas
            cursor.execute("""
                SELECT * FROM formulas 
                WHERE LOWER(title_km) LIKE ? OR LOWER(title_en) LIKE ? OR LOWER(formula) LIKE ? 
                   OR LOWER(keywords) LIKE ? OR LOWER(explanation) LIKE ?
                   OR LOWER(title_km) LIKE ? OR LOWER(keywords) LIKE ?
            """, (search_term, search_term, search_term, search_term, search_term, search_alt, search_alt))
            matched_formulas = [dict(r) for r in cursor.fetchall()]

            # Search exercises
            cursor.execute("""
                SELECT * FROM exercises 
                WHERE LOWER(title) LIKE ? OR LOWER(code) LIKE ? OR LOWER(problem) LIKE ? 
                   OR LOWER(keywords) LIKE ? OR LOWER(id) LIKE ?
                   OR LOWER(title) LIKE ? OR LOWER(code) LIKE ? OR LOWER(keywords) LIKE ?
            """, (search_term, search_term, search_term, search_term, search_term, search_alt, search_alt, search_alt))
            matched_exercises = []
            for r in cursor.fetchall():
                item = dict(r)
                try:
                    item["solution_steps"] = json.loads(item["solution_steps"])
                except Exception:
                    item["solution_steps"] = [item["solution_steps"]]
                matched_exercises.append(item)

            return {
                "formulas": matched_formulas,
                "exercises": matched_exercises
            }

    # --- Admin Mutations ---
    def save_exercise(self, ex: Dict[str, Any]) -> str:
        """Add or update an exercise. Handles existing code smoothly."""
        solution_steps_str = json.dumps(ex["solution_steps"], ensure_ascii=False) if isinstance(ex.get("solution_steps"), list) else str(ex.get("solution_steps", ""))
        keywords_str = ",".join(ex.get("keywords", [])) if isinstance(ex.get("keywords"), list) else ex.get("keywords", "")

        ex_id = ex.get("id")
        code = ex.get("code")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check if exercise already exists by code or ID
            if code:
                cursor.execute("SELECT id FROM exercises WHERE LOWER(code) = LOWER(?)", (code,))
                existing = cursor.fetchone()
                if existing:
                    ex_id = existing[0]

            if not ex_id:
                ex_id = f"ex_{int(datetime.utcnow().timestamp())}"

            cursor.execute("""
                INSERT INTO exercises (id, category_id, code, title, problem, hints, solution_steps, final_answer, difficulty, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    category_id = excluded.category_id,
                    code = excluded.code,
                    title = excluded.title,
                    problem = excluded.problem,
                    hints = excluded.hints,
                    solution_steps = excluded.solution_steps,
                    final_answer = excluded.final_answer,
                    difficulty = excluded.difficulty,
                    keywords = excluded.keywords
            """, (
                ex_id,
                ex.get("category_id", "basic"),
                code or ex_id,
                ex["title"],
                ex["problem"],

                ex.get("hints", ""),
                solution_steps_str,
                ex.get("final_answer", ""),
                ex.get("difficulty", "មធ្យម"),
                keywords_str
            ))
            conn.commit()
        return ex_id

    def delete_exercise(self, ex_id: str) -> bool:
        """Delete an exercise by ID or code."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM exercises WHERE id = ? OR LOWER(code) = LOWER(?)", (ex_id, ex_id))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def delete_formula(self, form_id: str) -> bool:
        """Delete a formula by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM formulas WHERE id = ?", (form_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def get_stats(self) -> Dict[str, int]:
        """Return total users, exercises, formulas, and queries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            users_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM exercises")
            ex_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM formulas")
            form_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM search_logs")
            searches_count = cursor.fetchone()[0]

            return {
                "total_users": users_count,
                "total_exercises": ex_count,
                "total_formulas": form_count,
                "total_searches": searches_count
            }

    def export_all(self) -> Dict[str, Any]:
        """Export all categories, formulas, and exercises to JSON-serializable dict."""
        return {
            "categories": self.get_categories(),
            "formulas": self.get_formulas(),
            "exercises": self.get_exercises()
        }


# Global database instance
db = Database()
