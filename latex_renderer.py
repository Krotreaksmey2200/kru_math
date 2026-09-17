"""
LaTeX Math Equation Rendering Engine.
Renders LaTeX math formulas into high-resolution PNG images.
Supports local high-speed rendering via Matplotlib with automatic online fallback (CodeCogs).
"""

import io
import re
import urllib.parse
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger("MathBot.LaTeX")

# Configure Matplotlib for headless server environment
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
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
    ]

    for orig, rep in replacements:
        s = s.replace(orig, rep)

    return s


def render_with_matplotlib(latex_str: str) -> Optional[bytes]:
    """Render LaTeX string using local matplotlib.mathtext with a sleek dark slate badge."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    clean = normalize_to_latex(latex_str)

    try:
        # Create small figure with dark slate background
        fig = plt.figure(figsize=(0.1, 0.1), dpi=260)
        fig.patch.set_facecolor("#1E1E2E")  # Modern dark slate
        plt.axis("off")

        # Render math text in crisp white/light
        plt.text(
            0.5,
            0.5,
            f"${clean}$",
            size=18,
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
            pad_inches=0.18
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
    clean = normalize_to_latex(latex_str)
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
    Main entry point: Renders a LaTeX string into PNG image bytes.
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
