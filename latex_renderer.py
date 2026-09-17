"""
LaTeX Math Equation Rendering Engine.
Renders LaTeX math formulas and equations into high-resolution PNG images.
Supports local high-speed rendering via Matplotlib (Computer Modern LaTeX font)
with automatic Khmer label extraction, multiline equation alignment, and online fallback.
"""

import io
import re
import urllib.parse
import aiohttp
import logging
from typing import Optional, List

logger = logging.getLogger("MathBot.LaTeX")

# Configure Matplotlib for headless server environment
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "mathtext.fontset": "cm",        # Authentic Computer Modern LaTeX font
        "font.family": "sans-serif",
        "figure.autolayout": False,
    })
    MATPLOTLIB_AVAILABLE = True
except Exception as e:
    logger.warning("Matplotlib not available for local LaTeX render: %s", e)
    MATPLOTLIB_AVAILABLE = False


def normalize_to_latex(text: str) -> str:
    """Normalize unicode math symbols and plain text expressions to valid LaTeX math."""
    s = text.strip()

    # Remove outer math delimiters if present
    if s.startswith("$$") and s.endswith("$$"):
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$"):
        s = s[1:-1].strip()

    # Common unicode conversions
    replacements = [
        ("²", "^2"),
        ("³", "^3"),
        ("⁴", "^4"),
        ("⁵", "^5"),
        ("⁶", "^6"),
        ("ⁿ", "^n"),
        ("⁻¹", "^{-1}"),
        ("⁻²", "^{-2}"),
        ("√", r"\sqrt"),
        ("π", r"\pi"),
        ("θ", r"\theta"),
        ("α", r"\alpha"),
        ("β", r"\beta"),
        ("Δ", r"\Delta"),
        ("λ", r"\lambda"),
        ("φ", r"\varphi"),
        ("ω", r"\omega"),
        ("∫", r"\int"),
        ("·", r"\cdot"),
        ("×", r"\times"),
        ("±", r"\pm"),
        ("≠", r"\neq"),
        ("≤", r"\le"),
        ("≥", r"\ge"),
        ("∞", r"\infty"),
        ("→", r"\to"),
        ("==>", r"\implies"),
        ("=>", r"\implies"),
        ("⇌", r"\rightleftharpoons"),
        ("ℝ", r"\mathbf{R}"),
        (r"\mathbb{R}", r"\mathbf{R}"),
        ("z̄", r"\bar{z}"),
        ("x̄", r"\bar{x}"),
        ("ȳ", r"\bar{y}"),
    ]

    for orig, rep in replacements:
        s = s.replace(orig, rep)

    # Convert \sqrt(...) to \sqrt{...}
    s = re.sub(r'\\sqrt\(([^)]+)\)', r'\\sqrt{\1}', s)

    # Add space before parentheses when following alphanumeric, e.g. "bi (" -> "bi \quad ("
    s = re.sub(r'([a-zA-Z0-9\^}])\s*\(', r'\1 \\quad (', s)

    return s


def clean_and_extract_equations(raw_text: str) -> List[str]:
    """
    Extracts clean mathematical expressions from text.
    Strips Khmer language prefixes, bullet points, and explanatory words
    to prevent tofu/box glyph errors in LaTeX math mode.
    """
    if not raw_text:
        return []

    lines = raw_text.splitlines() if "\n" in raw_text else [raw_text]
    cleaned_equations = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Strip leading bullets, numbers, hyphens
        line = re.sub(r'^[•\-\*\d\.\)]+\s*', '', line)

        # Strip Khmer label prefixes like "ទម្រង់ពីជគណិត៖" or "ម៉ូឌុល៖"
        line = re.sub(r'^[\u1780-\u17FF\s\:\៖\-\(\)]+[\:៖]\s*', '', line)

        # Replace common Khmer connective words with math spacing
        line = re.sub(r'\bដែល\b', '', line)
        line = re.sub(r'\bដោយ\b', '', line)
        line = re.sub(r'\bនាំឱ្យ\b', r'\\implies ', line)
        line = re.sub(r'\bឬ\b', r'\\lor ', line)
        line = re.sub(r'\bនិង\b', r'\\land ', line)

        # Strip any remaining Khmer Unicode characters (U+1780 to U+17FF)
        line = re.sub(r'[\u1780-\u17FF]', '', line)

        # Clean empty parentheses and normalize whitespace
        line = re.sub(r'\(\s*\)', '', line)
        line = re.sub(r'\s+', ' ', line).strip()

        # Only retain lines with mathematical substance
        if line and any(c in line for c in '=+-*/^<>\\()|[]{}_'):
            norm = normalize_to_latex(line)
            if norm:
                cleaned_equations.append(norm)

    # Fallback: if stripping left nothing (e.g. pure LaTeX string with no Khmer text),
    # return the normalized original string
    if not cleaned_equations:
        norm_orig = normalize_to_latex(raw_text)
        # Strip stray Khmer if any
        norm_orig = re.sub(r'[\u1780-\u17FF]', '', norm_orig).strip()
        if norm_orig:
            cleaned_equations.append(norm_orig)

    return cleaned_equations


def render_with_matplotlib(latex_str: str) -> Optional[bytes]:
    """Render LaTeX string using local matplotlib.mathtext with a sleek dark slate badge."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    eq_lines = clean_and_extract_equations(latex_str)
    if not eq_lines:
        return None

    num_lines = len(eq_lines)

    try:
        # Dynamic figure height based on number of equation lines
        fig_height = max(1.0, 0.5 + num_lines * 0.55)
        fig = plt.figure(figsize=(7, fig_height), dpi=260)
        fig.patch.set_facecolor("#1E1E2E")  # Modern dark slate badge
        plt.axis("off")

        # Position lines nicely vertically
        y_step = 1.0 / (num_lines + 1)
        for idx, eq in enumerate(eq_lines):
            y_pos = 1.0 - (idx + 1) * y_step
            plt.text(
                0.5,
                y_pos,
                f"${eq}$",
                size=16,
                ha="center",
                va="center",
                color="#F8F9FA"
            )

        buf = io.BytesIO()
        plt.savefig(
            buf,
            format="png",
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
            pad_inches=0.22
        )
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        logger.debug("Matplotlib render failed for '%s': %s", latex_str, e)
        try:
            plt.close(fig)
        except Exception:
            pass
        return None


async def render_with_codecogs(latex_str: str) -> Optional[bytes]:
    """Fallback online renderer using CodeCogs API."""
    eq_lines = clean_and_extract_equations(latex_str)
    if not eq_lines:
        return None

    clean = r" \\ ".join(eq_lines)
    query = r"\dpi{300}\bg{white} " + clean
    encoded = urllib.parse.quote(query)
    url = f"https://latex.codecogs.com/png.image?{encoded}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.warning("CodeCogs returned status %s for '%s'", resp.status, clean)
    except Exception as e:
        logger.warning("CodeCogs render failed for '%s': %s", clean, e)

    return None


async def render_latex_to_png(latex_str: str) -> Optional[bytes]:
    """
    Main entry point: Renders a LaTeX string or math formula into PNG image bytes.
    Automatically cleans non-math Khmer text and strips tofu glyphs.
    First tries local Matplotlib, then falls back to CodeCogs online renderer.
    """
    # 1. Try local Matplotlib rendering
    png_bytes = render_with_matplotlib(latex_str)
    if png_bytes and len(png_bytes) > 200:
        return png_bytes

    # 2. Fallback to online CodeCogs renderer
    png_bytes = await render_with_codecogs(latex_str)
    if png_bytes and len(png_bytes) > 200:
        return png_bytes

    return None
