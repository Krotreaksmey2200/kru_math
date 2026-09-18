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
import textwrap
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

    # Multi-char keywords & patterns first
    s = s.replace("log₁₀", r"\log_{10} ")
    s = s.replace("==>", r"\Rightarrow ")
    s = s.replace("=>", r"\Rightarrow ")
    s = s.replace(r"\implies", r"\Rightarrow ")
    s = s.replace("⇌", r"\rightleftharpoons ")

    # Superscripts with negative sign
    s = s.replace("⁻¹", "^{-1}").replace("⁻²", "^{-2}").replace("⁻³", "^{-3}")
    s = s.replace("⁻⁴", "^{-4}").replace("⁻⁵", "^{-5}").replace("⁻ⁿ", "^{-n}")

    # Common unicode conversions
    replacements = [
        ("²", "^2"),
        ("³", "^3"),
        ("⁴", "^4"),
        ("⁵", "^5"),
        ("⁶", "^6"),
        ("ⁿ", "^n"),
        ("₀", "_0"),
        ("₁", "_1"),
        ("₂", "_2"),
        ("₃", "_3"),
        ("₄", "_4"),
        ("ₐ", "_a"),
        ("ᵇ", "^b"),
        ("√", r"\sqrt"),
        ("π", r"\pi "),
        ("θ", r"\theta "),
        ("α", r"\alpha "),
        ("β", r"\beta "),
        ("Δ", r"\Delta "),
        ("λ", r"\lambda "),
        ("φ", r"\varphi "),
        ("ω", r"\omega "),
        ("∫", r"\int "),
        ("·", r" \cdot "),
        ("×", r" \times "),
        ("±", r"\pm "),
        ("≠", r"\neq "),
        ("≤", r"\le "),
        ("≥", r"\ge "),
        ("∞", r"\infty "),
        ("→", r"\to "),
        ("ℝ", r"\mathbf{R}"),
        (r"\mathbb{R}", r"\mathbf{R}"),
        ("z̄", r"\bar{z}"),
        ("x̄", r"\bar{x}"),
        ("ȳ", r"\bar{y}"),
        ("u⃗", r"\vec{u}"),
        ("v⃗", r"\vec{v}"),
    ]

    for orig, rep in replacements:
        s = s.replace(orig, rep)

    # Limits: lim(x→0) or lim(x->0) or lim(x \to 0)
    s = re.sub(
        r"\blim\s*\(\s*([a-zA-Z0-9_]+)\s*(?:→|->|\\to)\s*([+\-a-zA-Z0-9_]+)\s*\)",
        lambda m: r"\lim_{" + m.group(1) + r" \to " + m.group(2) + r"} \, ",
        s
    )
    s = re.sub(r"\blim\b(?!\s*_)", lambda m: r"\lim \, ", s)

    # Standard functions: sin, cos, tan, cot, ln, exp, log
    for fn in ["sin", "cos", "tan", "cot", "ln", "exp", "log"]:
        s = re.sub(rf"(?<![\\a-zA-Z]){fn}(?![a-zA-Z])", lambda m, f=fn: "\\" + f + " ", s)

    # Clean double spaces
    s = re.sub(r"[ \t]+", " ", s)

    # Bracket fractions: [A / B]
    def frac_bracket(m):
        content = m.group(1)
        if "/" in content:
            p = content.rsplit("/", 1)
            num = p[0].strip()
            den = p[1].strip()
            if num.startswith("(") and num.endswith(")"):
                num = num[1:-1].strip()
            if den.startswith("(") and den.endswith(")"):
                den = den[1:-1].strip()
            return r"\frac{" + num + "}{" + den + "}"
        return m.group(0)

    s = re.sub(r"\[([^\]]+/[^\]]+)\]", frac_bracket, s)

    # Standalone simple numeric fractions e.g. " 1/2 ", " (1/2) " but not " 0.2/80 "
    s = re.sub(r"(?<![\.\d\w\\])(\d+)/(\d+)(?![\.\d\w\\])", lambda m: r"\frac{" + m.group(1) + r"}{" + m.group(2) + r"}", s)

    # Convert \sqrt(...) to \sqrt{...}
    s = re.sub(r'\\sqrt\(([^)]+)\)', lambda m: r'\sqrt{' + m.group(1) + r'}', s)
    s = re.sub(r'\\sqrt\[([^\]]+)\]', lambda m: r'\sqrt{' + m.group(1) + r'}', s)
    s = re.sub(r'\\sqrt([0-9a-zA-Z]+)', lambda m: r'\sqrt{' + m.group(1) + r'}', s)

    return s


def clean_math_part(text: str) -> str:
    """Cleans up internal Khmer words from math expressions to keep math parsing pristine."""
    s = text.strip()
    s = re.sub(r'\bដែល\b', '', s)
    s = re.sub(r'\bដោយ\b', '', s)
    s = re.sub(r'\bនាំឱ្យ\b', r'\\Rightarrow ', s)
    s = re.sub(r'[\u1780-\u17FF]', '', s)
    s = re.sub(r'\(\s*\)', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return normalize_to_latex(s)


def split_line_tokens(text: str) -> List[Tuple[str, str]]:
    """
    Splits a single line into alternating tokens:
    - ('KHMER', khmer_string)
    - ('MATH', latex_math_string)
    Prevents Matplotlib mathtext from choking on Khmer glyphs.
    """
    text = text.strip()
    if not text:
        return []

    # If the text explicitly contains $...$ math blocks, respect them
    if "$" in text and text.count("$") >= 2:
        parts = re.split(r'(\$[^$]+\$)', text)
        tokens = []
        for p in parts:
            if not p:
                continue
            if p.startswith("$") and p.endswith("$") and len(p) > 2:
                inner = p[1:-1].strip()
                # Escape unescaped % inside math
                inner = re.sub(r'(?<!\\)%', r'\\%', inner)
                tokens.append(("MATH", normalize_to_latex(inner)))
            else:
                p_clean = p.strip()
                if p_clean:
                    tokens.append(("KHMER", p_clean))
        if tokens:
            return tokens

    if not re.search(r'[\u1780-\u17FF]', text):
        clean_text = re.sub(r'(?<!\\)%', r'\\%', text)
        return [("MATH", normalize_to_latex(clean_text))]

    parts = re.split(r'([^\u1780-\u17FF\n\r៖:•\-\*]+)', text)
    tokens = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if re.search(r'[\u1780-\u17FF៖:•\-\*]', p):
            tokens.append(("KHMER", p))
        else:
            p_clean = re.sub(r'(?<!\\)%', r'\\%', p)
            tokens.append(("MATH", normalize_to_latex(p_clean)))
    return tokens or [("KHMER", text)]


def parse_line_khmer_and_math(line: str) -> Tuple[str, str]:
    """
    Parses a single line into (Khmer text prefix, LaTeX math expression).
    Handles labels with colons ("• ទម្រង់ពីជគណិត៖ z = a + bi...")
    and natural text before math ("សាលារៀន \int x^3 dx").
    """
    line = line.strip()
    line = re.sub(r'^[•\-\*\d\.\)]+\s*', '', line)

    has_khmer = bool(re.search(r'[\u1780-\u17FF]', line))
    if not has_khmer:
        return ("", clean_math_part(line))

    m1 = re.match(r'^([\u1780-\u17FF\s\(\)]+[៖:])\s*(.*)$', line)
    if m1:
        return (m1.group(1).strip(), clean_math_part(m1.group(2)))

    m2 = re.match(r'^([\u1780-\u17FF\s]+?)\s+([\\$a-zA-Z0-9].*)$', line)
    if m2:
        return (m2.group(1).strip(), clean_math_part(m2.group(2)))

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


def render_formula_card(
    title_km: str,
    formula_raw: str = "",
    example_raw: str = "",
    title_en: str = "",
    explanation: str = ""
) -> Optional[bytes]:
    """
    Renders an entire formula item as a cohesive, beautiful card on a pure white background (#FFFFFF).
    Includes:
    - Khmer title & English subtitle
    - Divider
    - Formula section with full LaTeX equations
    - Explanation section with wrapped Khmer text
    - Example section with full LaTeX equations
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    sections = []

    # 1. Title & Subtitle
    clean_title = re.sub(r'[^\u1780-\u17FF\u0000-\u007Fa-zA-Z0-9\s\(\)\:\.\,\-\+\/]', '', title_km).strip()
    if clean_title:
        sections.append({"type": "TITLE", "text": clean_title, "size": 19, "color": "#0F172A", "height": 1.25})

    clean_en = title_en.strip()
    if clean_en:
        sections.append({"type": "SUBTITLE", "text": f"({clean_en})", "size": 13, "color": "#64748B", "height": 0.75})

    sections.append({"type": "DIVIDER", "height": 0.5})

    # 2. Formula Section
    if formula_raw.strip():
        sections.append({"type": "SECTION", "text": "រូបមន្ត (Formula)៖", "size": 15, "color": "#1E293B", "height": 0.95})
        for line in formula_raw.splitlines():
            line = line.strip()
            if line:
                tokens = split_line_tokens(line)
                sections.append({"type": "TOKENS", "tokens": tokens, "size": 17.5, "height": 1.35})

    # 3. Explanation Section
    if explanation.strip():
        sections.append({"type": "SECTION", "text": "ពន្យល់ (Explanation)៖", "size": 15, "color": "#1E293B", "height": 0.95})
        for wline in textwrap.wrap(explanation.strip(), width=54):
            sections.append({"type": "TEXT", "text": wline, "size": 13.5, "color": "#334155", "height": 0.85})

    # 4. Example Section
    if example_raw.strip():
        sections.append({"type": "SECTION", "text": "ឧទាហរណ៍ (Example)៖", "size": 15, "color": "#1E293B", "height": 0.95})
        for line in example_raw.splitlines():
            line = line.strip()
            if line:
                tokens = split_line_tokens(line)
                sections.append({"type": "TOKENS", "tokens": tokens, "size": 17.5, "height": 1.35})

    if not sections:
        return None

    try:
        total_weight = sum(s["height"] for s in sections)
        fig_height = max(3.0, total_weight * 0.65)
        fig = plt.figure(figsize=(8.8, fig_height), dpi=260)
        fig.patch.set_facecolor("#FFFFFF")
        ax = plt.subplot(111)
        ax.patch.set_facecolor("#FFFFFF")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, total_weight)
        plt.axis("off")

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()

        cur_y = total_weight
        for s in sections:
            cur_y -= s["height"]
            draw_y = cur_y + s["height"] * 0.45

            stype = s["type"]
            text_val = s.get("text", "").replace("•", "-")
            if stype == "TITLE":
                if KHMER_FP:
                    ax.text(0.05, draw_y, text_val, fontproperties=KHMER_FP, size=s["size"], color=s["color"], va="center")
                else:
                    ax.text(0.05, draw_y, text_val, size=s["size"], color=s["color"], va="center")
            elif stype == "SUBTITLE":
                ax.text(0.05, draw_y, text_val, size=s["size"], color=s["color"], style="italic", va="center")
            elif stype == "DIVIDER":
                ax.axhline(y=draw_y, xmin=0.05, xmax=0.95, color="#E2E8F0", linewidth=1.2)
            elif stype == "SECTION":
                if KHMER_FP:
                    ax.text(0.05, draw_y, text_val, fontproperties=KHMER_FP, size=s["size"], color=s["color"], va="center")
                else:
                    ax.text(0.05, draw_y, text_val, size=s["size"], color=s["color"], va="center")
            elif stype == "TEXT":
                if KHMER_FP:
                    ax.text(0.08, draw_y, text_val, fontproperties=KHMER_FP, size=s["size"], color=s["color"], va="center")
                else:
                    ax.text(0.08, draw_y, text_val, size=s["size"], color=s["color"], va="center")
            elif stype == "TOKENS":
                x_cur = 0.08
                for tok_kind, tok_val in s["tokens"]:
                    if tok_kind == "MATH":
                        try:
                            t = ax.text(x_cur, draw_y, f"${tok_val}$", size=s["size"], color="#0F172A", va="center")
                            fig.canvas.draw()
                            bbox = t.get_window_extent(renderer=renderer)
                            x_cur = inv.transform(bbox)[1][0] + 0.02
                        except Exception:
                            t = ax.text(x_cur, draw_y, tok_val, size=s["size"] - 2, color="#0F172A", va="center")
                            fig.canvas.draw()
                            bbox = t.get_window_extent(renderer=renderer)
                            x_cur = inv.transform(bbox)[1][0] + 0.02
                    else:
                        tok_khmer = tok_val.replace("•", "-")
                        if KHMER_FP:
                            t = ax.text(x_cur, draw_y, tok_khmer, fontproperties=KHMER_FP, size=14.5, color="#1E293B", va="center")
                        else:
                            t = ax.text(x_cur, draw_y, tok_khmer, size=14, color="#1E293B", va="center")
                        fig.canvas.draw()
                        bbox = t.get_window_extent(renderer=renderer)
                        x_cur = inv.transform(bbox)[1][0] + 0.02

        buf = io.BytesIO()
        plt.savefig(buf, format="png", facecolor="#FFFFFF", bbox_inches="tight", pad_inches=0.28)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        logger.error("render_formula_card error: %s", e)
        try:
            plt.close(fig)
        except Exception:
            pass
        return None


def render_exercise_card(
    code: str,
    title: str,
    difficulty: str = "មធ្យម",
    problem_raw: str = "",
    solution_raw: str = ""
) -> Optional[bytes]:
    """
    Renders an entire exercise item (problem statement & optional solution) as a clean card.
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    sections = []

    # 1. Title & Difficulty
    header_text = f"{code}៖ {title}".strip()
    sections.append({"type": "TITLE", "text": header_text, "size": 18, "color": "#0F172A", "height": 1.25})
    sections.append({"type": "SUBTITLE", "text": f"កម្រិត៖ {difficulty}", "size": 13, "color": "#64748B", "height": 0.75})
    sections.append({"type": "DIVIDER", "height": 0.5})

    # 2. Problem Statement
    if problem_raw.strip():
        sections.append({"type": "SECTION", "text": "ប្រធានលំហាត់ (Problem)៖", "size": 15, "color": "#1E293B", "height": 0.95})
        for line in problem_raw.splitlines():
            line = line.strip()
            if line:
                tokens = split_line_tokens(line)
                sections.append({"type": "TOKENS", "tokens": tokens, "size": 16.5, "height": 1.25})

    # 3. Solution (if provided)
    if solution_raw.strip():
        sections.append({"type": "DIVIDER", "height": 0.5})
        sections.append({"type": "SECTION", "text": "ដំណោះស្រាយលម្អិត (Solution)៖", "size": 15, "color": "#16A34A", "height": 0.95})
        for line in solution_raw.splitlines():
            line = line.strip()
            if line:
                tokens = split_line_tokens(line)
                sections.append({"type": "TOKENS", "tokens": tokens, "size": 16.5, "height": 1.25})

    if not sections:
        return None

    try:
        total_weight = sum(s["height"] for s in sections)
        fig_height = max(3.0, total_weight * 0.65)
        fig = plt.figure(figsize=(8.8, fig_height), dpi=260)
        fig.patch.set_facecolor("#FFFFFF")
        ax = plt.subplot(111)
        ax.patch.set_facecolor("#FFFFFF")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, total_weight)
        plt.axis("off")

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        inv = ax.transData.inverted()

        cur_y = total_weight
        for s in sections:
            cur_y -= s["height"]
            draw_y = cur_y + s["height"] * 0.45

            stype = s["type"]
            text_val = s.get("text", "").replace("•", "-")
            if stype == "TITLE":
                if KHMER_FP:
                    ax.text(0.05, draw_y, text_val, fontproperties=KHMER_FP, size=s["size"], color=s["color"], va="center")
                else:
                    ax.text(0.05, draw_y, text_val, size=s["size"], color=s["color"], va="center")
            elif stype == "SUBTITLE":
                if KHMER_FP:
                    ax.text(0.05, draw_y, text_val, fontproperties=KHMER_FP, size=s["size"], color=s["color"], va="center")
                else:
                    ax.text(0.05, draw_y, text_val, size=s["size"], color=s["color"], va="center")
            elif stype == "DIVIDER":
                ax.axhline(y=draw_y, xmin=0.05, xmax=0.95, color="#E2E8F0", linewidth=1.2)
            elif stype == "SECTION":
                if KHMER_FP:
                    ax.text(0.05, draw_y, text_val, fontproperties=KHMER_FP, size=s["size"], color=s["color"], va="center")
                else:
                    ax.text(0.05, draw_y, text_val, size=s["size"], color=s["color"], va="center")
            elif stype == "TEXT":
                if KHMER_FP:
                    ax.text(0.08, draw_y, text_val, fontproperties=KHMER_FP, size=s["size"], color=s["color"], va="center")
                else:
                    ax.text(0.08, draw_y, text_val, size=s["size"], color=s["color"], va="center")
            elif stype == "TOKENS":
                x_cur = 0.08
                for tok_kind, tok_val in s["tokens"]:
                    if tok_kind == "MATH":
                        try:
                            t = ax.text(x_cur, draw_y, f"${tok_val}$", size=s["size"], color="#0F172A", va="center")
                            fig.canvas.draw()
                            bbox = t.get_window_extent(renderer=renderer)
                            x_cur = inv.transform(bbox)[1][0] + 0.02
                        except Exception:
                            t = ax.text(x_cur, draw_y, tok_val, size=s["size"] - 2, color="#0F172A", va="center")
                            fig.canvas.draw()
                            bbox = t.get_window_extent(renderer=renderer)
                            x_cur = inv.transform(bbox)[1][0] + 0.02
                    else:
                        tok_khmer = tok_val.replace("•", "-")
                        if KHMER_FP:
                            t = ax.text(x_cur, draw_y, tok_khmer, fontproperties=KHMER_FP, size=14, color="#1E293B", va="center")
                        else:
                            t = ax.text(x_cur, draw_y, tok_khmer, size=13.5, color="#1E293B", va="center")
                        fig.canvas.draw()
                        bbox = t.get_window_extent(renderer=renderer)
                        x_cur = inv.transform(bbox)[1][0] + 0.02

        buf = io.BytesIO()
        plt.savefig(buf, format="png", facecolor="#FFFFFF", bbox_inches="tight", pad_inches=0.28)
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()
    except Exception as e:
        logger.error("render_exercise_card error: %s", e)
        try:
            plt.close(fig)
        except Exception:
            pass
        return None

