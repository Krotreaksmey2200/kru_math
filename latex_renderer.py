"""
LaTeX Math Equation & Khmer Text Rendering Engine.
Renders mixed Khmer text and LaTeX mathematical formulas into high-resolution images
with a clean white background (or transparent sticker).
"""

import os
import io
import re
import urllib.parse
import aiohttp
import logging
from typing import Optional, List, Tuple
from PIL import Image

logger = logging.getLogger("MathBot.LaTeX")

# Configure bundled Khmer font
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts", "KhmerFont.ttf")

# Configure Matplotlib for headless server environment
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib.font_manager import FontProperties

    plt.rcParams.update({
        "mathtext.fontset": "cm",        # Authentic Computer Modern LaTeX font
        "font.family": "sans-serif",
        "figure.autolayout": False,
    })

    KHMER_FP = FontProperties(fname=FONT_PATH) if os.path.exists(FONT_PATH) else None
    MATPLOTLIB_AVAILABLE = True
except Exception as e:
    logger.warning("Matplotlib not available for local LaTeX render: %s", e)
    MATPLOTLIB_AVAILABLE = False
    KHMER_FP = None


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


def clean_math_part(text: str) -> str:
    """Cleans up internal Khmer words from math expressions to keep math parsing pristine."""
    s = text.strip()
    s = re.sub(r'\bដែល\b', '', s)
    s = re.sub(r'\bដោយ\b', '', s)
    s = re.sub(r'\bនាំឱ្យ\b', r'\\implies ', s)
    s = re.sub(r'[\u1780-\u17FF]', '', s)
    s = re.sub(r'\(\s*\)', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return normalize_to_latex(s)


def parse_line_khmer_and_math(line: str) -> Tuple[str, str]:
    """
    Parses a single line into (Khmer text prefix, LaTeX math expression).
    Handles labels with colons ("• ទម្រង់ពីជគណិត៖ z = a + bi...")
    and natural text before math ("សាលារៀន \int x^3 dx").
    """
    line = line.strip()
    # Strip leading bullets and numbering
    line = re.sub(r'^[•\-\*\d\.\)]+\s*', '', line)

    has_khmer = bool(re.search(r'[\u1780-\u17FF]', line))
    if not has_khmer:
        return ("", clean_math_part(line))

    # Pattern 1: Khmer label ending with colon e.g. "ទម្រង់ពីជគណិត៖ z = a + bi..."
    m1 = re.match(r'^([\u1780-\u17FF\s\(\)]+[៖:])\s*(.*)$', line)
    if m1:
        return (m1.group(1).strip(), clean_math_part(m1.group(2)))

    # Pattern 2: Khmer words followed by a math expression e.g. "សាលារៀន \int x^3 dx"
    m2 = re.match(r'^([\u1780-\u17FF\s]+?)\s+([\\$a-zA-Z0-9].*)$', line)
    if m2:
        return (m2.group(1).strip(), clean_math_part(m2.group(2)))

    # Pattern 3: Pure Khmer text with no clear math
    return (line, "")


def clean_and_extract_equations(raw_text: str) -> List[str]:
    """Fallback helper: extracts only the math parts as a list of strings."""
    lines = raw_text.splitlines() if "\n" in raw_text else [raw_text]
    equations = []
    for line in lines:
        _, math = parse_line_khmer_and_math(line)
        if math:
            equations.append(math)
    return equations or [normalize_to_latex(raw_text)]


def render_with_matplotlib(latex_str: str, bg_color: str = "#FFFFFF") -> Optional[bytes]:
    """
    Render mixed Khmer text and LaTeX equations on a clean white background (#FFFFFF).
    Uses bundled Khmer font for authentic Khmer calligraphy and Computer Modern for LaTeX.
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    raw_lines = latex_str.splitlines() if "\n" in latex_str else [latex_str]
    parsed_lines = [parse_line_khmer_and_math(l) for l in raw_lines if l.strip()]

    if not parsed_lines:
        return None

    num_lines = len(parsed_lines)

    try:
        fig_height = max(1.1, 0.5 + num_lines * 0.72)
        fig = plt.figure(figsize=(7.5, fig_height), dpi=260)
        fig.patch.set_facecolor(bg_color)
        ax = plt.subplot(111)
        ax.patch.set_facecolor(bg_color)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        plt.axis("off")

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()

        y_step = 1.0 / (num_lines + 1)

        text_color = "#0F172A" if bg_color.upper() == "#FFFFFF" else "#F8F9FA"
        khmer_color = "#1E293B" if bg_color.upper() == "#FFFFFF" else "#E2E8F0"

        for idx, (kh, math) in enumerate(parsed_lines):
            y_pos = 1.0 - (idx + 1) * y_step
            x_cursor = 0.04

            # Draw Khmer text if present
            if kh:
                if KHMER_FP:
                    t_kh = ax.text(
                        x_cursor, y_pos, kh,
                        fontproperties=KHMER_FP,
                        size=16,
                        color=khmer_color,
                        va="center"
                    )
                else:
                    t_kh = ax.text(x_cursor, y_pos, kh, size=15, color=khmer_color, va="center")

                fig.canvas.draw()
                bbox = t_kh.get_window_extent(renderer=renderer)
                bbox_data = inv.transform(bbox)
                x_cursor = bbox_data[1][0] + 0.025

            # Draw LaTeX math expression if present
            if math:
                ax.text(
                    x_cursor, y_pos,
                    f"${math}$",
                    size=18,
                    color=text_color,
                    va="center"
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


async def render_latex_to_png(latex_str: str, bg_color: str = "#FFFFFF") -> Optional[bytes]:
    """
    Main entry point: Renders mixed Khmer text and LaTeX equations into a clean PNG image.
    Defaults to clean white background (#FFFFFF) per user preference.
    """
    # 1. Try local Matplotlib with Khmer Font + Computer Modern LaTeX
    png_bytes = render_with_matplotlib(latex_str, bg_color=bg_color)
    if png_bytes and len(png_bytes) > 200:
        return png_bytes

    # 2. Fallback to online CodeCogs renderer
    png_bytes = await render_with_codecogs(latex_str)
    if png_bytes and len(png_bytes) > 200:
        return png_bytes

    return None


def render_latex_to_transparent_webp(latex_str: str) -> Optional[bytes]:
    """
    Renders mixed Khmer text & LaTeX math into a transparent-background WebP sticker.
    Dual-theme compatible with dark slate font.
    Conforms to Telegram sticker dimensions (<=512px).
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    raw_lines = latex_str.splitlines() if "\n" in latex_str else [latex_str]
    parsed_lines = [parse_line_khmer_and_math(l) for l in raw_lines if l.strip()]
    if not parsed_lines:
        return None

    num_lines = len(parsed_lines)
    try:
        fig_height = max(1.1, 0.5 + num_lines * 0.7)
        fig = plt.figure(figsize=(7.5, fig_height), dpi=300)
        fig.patch.set_alpha(0.0)
        ax = plt.subplot(111)
        ax.patch.set_alpha(0.0)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        plt.axis("off")

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()

        y_step = 1.0 / (num_lines + 1)
        for idx, (kh, math) in enumerate(parsed_lines):
            y_pos = 1.0 - (idx + 1) * y_step
            x_cursor = 0.04

            if kh:
                if KHMER_FP:
                    t_kh = ax.text(
                        x_cursor, y_pos, kh,
                        fontproperties=KHMER_FP,
                        size=17,
                        color="#1A1B26",
                        va="center",
                        path_effects=[pe.withStroke(linewidth=1.8, foreground="#FFFFFF")]
                    )
                else:
                    t_kh = ax.text(
                        x_cursor, y_pos, kh,
                        size=16,
                        color="#1A1B26",
                        va="center",
                        path_effects=[pe.withStroke(linewidth=1.8, foreground="#FFFFFF")]
                    )

                fig.canvas.draw()
                bbox = t_kh.get_window_extent(renderer=renderer)
                bbox_data = inv.transform(bbox)
                x_cursor = bbox_data[1][0] + 0.025

            if math:
                ax.text(
                    x_cursor, y_pos, f"${math}$",
                    size=19,
                    ha="left", va="center",
                    color="#1A1B26",
                    path_effects=[pe.withStroke(linewidth=1.8, foreground="#FFFFFF")]
                )

        png_buf = io.BytesIO()
        plt.savefig(
            png_buf,
            format="png",
            transparent=True,
            bbox_inches="tight",
            pad_inches=0.15
        )
        plt.close(fig)
        png_buf.seek(0)

        img = Image.open(png_buf)
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)

        webp_buf = io.BytesIO()
        img.save(webp_buf, format="WEBP")
        return webp_buf.getvalue()
    except Exception as e:
        logger.debug("Transparent WebP render failed: %s", e)
        try:
            plt.close(fig)
        except Exception:
            pass
        return None
