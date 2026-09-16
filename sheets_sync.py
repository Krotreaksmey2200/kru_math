"""
Google Sheets Synchronization Module.
Enables math teachers to update derivative formulas and exercises directly from Google Sheets
without touching any code or restarting the bot.

Supports two sync methods:
1. Public/Published CSV URL (Easiest - 0 API setup, just 'Publish to Web' as CSV)
2. Service Account via gspread (Enterprise / Private Sheets)
"""

import csv
import io
import logging
from typing import Dict, Any, List, Optional
import aiohttp
from pathlib import Path

from config import GOOGLE_SHEET_CSV_URL
from database import db

logger = logging.getLogger("MathBot.SheetsSync")


async def fetch_csv_from_url(url: str) -> str:
    """Download CSV text content from a Google Sheet URL (supports sharing & published links)."""
    clean_url = url.strip()
    if "/edit" in clean_url:
        clean_url = clean_url.split("/edit")[0] + "/export?format=csv"
    elif not clean_url.endswith("output=csv") and not clean_url.endswith("format=csv"):
        if "/d/" in clean_url:
            sheet_id = clean_url.split("/d/")[1].split("/")[0]
            clean_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(clean_url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status != 200:
                raise ValueError(f"Failed to fetch CSV, HTTP Status: {resp.status}")
            return await resp.text()



def parse_csv_exercises(csv_content: str) -> List[Dict[str, Any]]:
    """
    Parse CSV rows into exercise dicts.
    Expected CSV columns:
    id | category_id | code | title | problem | hints | solution_steps | final_answer | difficulty | keywords
    Note: solution_steps can be multiple lines or separated by '||' or numbered lines.
    """
    reader = csv.DictReader(io.StringIO(csv_content.strip()))
    exercises = []

    for row in reader:
        # Normalize column keys to lowercase
        norm_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        if not norm_row.get("title") or not norm_row.get("problem"):
            continue

        raw_steps = norm_row.get("solution_steps", "")
        # Allow steps separated by '||' or '\n'
        if "||" in raw_steps:
            steps = [s.strip() for s in raw_steps.split("||") if s.strip()]
        elif "\n" in raw_steps:
            steps = [s.strip() for s in raw_steps.split("\n") if s.strip()]
        else:
            steps = [raw_steps] if raw_steps else []

        ex = {
            "id": norm_row.get("id") or f"ex_{len(exercises)+1}",
            "category_id": norm_row.get("category_id") or "basic",
            "code": norm_row.get("code") or norm_row.get("id", ""),
            "title": norm_row.get("title", ""),
            "problem": norm_row.get("problem", ""),
            "hints": norm_row.get("hints", ""),
            "solution_steps": steps,
            "final_answer": norm_row.get("final_answer", ""),
            "difficulty": norm_row.get("difficulty", "មធ្យម"),
            "keywords": [k.strip() for k in norm_row.get("keywords", "").split(",") if k.strip()]
        }
        exercises.append(ex)

    return exercises


async def sync_from_google_sheet(csv_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync exercises from Google Sheet published CSV URL.
    Returns summary of imported items.
    """
    url = csv_url or GOOGLE_SHEET_CSV_URL
    if not url:
        raise ValueError("Google Sheet CSV URL is not configured. Provide a URL or set GOOGLE_SHEET_CSV_URL in .env.")

    logger.info("Fetching exercises from Google Sheet: %s", url)
    content = await fetch_csv_from_url(url)
    exercises = parse_csv_exercises(content)

    if not exercises:
        return {"status": "warning", "message": "មិនមានលំហាត់ណាមួយត្រូវបានរកឃើញនៅក្នុង Sheet នោះទេ។", "count": 0}

    imported_count = 0
    for ex in exercises:
        db.save_exercise(ex)
        imported_count += 1

    return {
        "status": "success",
        "message": f"បានធ្វើសមកាលកម្ម (Sync) លំហាត់ចំនួន {imported_count} ដោយជោគជ័យ!",
        "count": imported_count
    }


def sync_via_gspread(credentials_file: str, spreadsheet_title: str) -> Dict[str, Any]:
    """
    Alternative: Sync using Google Cloud Service Account json key via gspread.
    Useful for private Google Sheets.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open(spreadsheet_title).sheet1
        records = sheet.get_all_records()

        count = 0
        for row in records:
            norm_row = {k.strip().lower(): str(v).strip() for k, v in row.items()}
            if not norm_row.get("title") or not norm_row.get("problem"):
                continue

            raw_steps = norm_row.get("solution_steps", "")
            steps = [s.strip() for s in raw_steps.split("||") if s.strip()] if "||" in raw_steps else [raw_steps]

            ex = {
                "id": norm_row.get("id") or f"ex_gs_{count+1}",
                "category_id": norm_row.get("category_id", "basic"),
                "code": norm_row.get("code", ""),
                "title": norm_row.get("title", ""),
                "problem": norm_row.get("problem", ""),
                "hints": norm_row.get("hints", ""),
                "solution_steps": steps,
                "final_answer": norm_row.get("final_answer", ""),
                "difficulty": norm_row.get("difficulty", "មធ្យម"),
                "keywords": [k.strip() for k in norm_row.get("keywords", "").split(",") if k.strip()]
            }
            db.save_exercise(ex)
            count += 1

        return {"status": "success", "count": count}
    except Exception as e:
        logger.error("gspread sync error: %s", e)
        return {"status": "error", "message": str(e)}
