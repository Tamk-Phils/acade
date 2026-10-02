"""
Document Converter: Converts DOCX to PDF using LibreOffice headless
and generates high-resolution page previews with pdftoppm.
Features a high-fidelity pure-Python fallback previewer that preserves
tables, figures, formulas, and Senate formatting rules.
"""
import os
import shutil
import subprocess
import glob
import io
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import docx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def is_libreoffice_available() -> bool:
    """Returns True if libreoffice or soffice is installed and executable."""
    return bool(shutil.which("libreoffice") or shutil.which("soffice"))

def is_pdftoppm_available() -> bool:
    """Returns True if pdftoppm is installed and executable."""
    return bool(shutil.which("pdftoppm"))

def convert_docx_to_pdf(docx_path: str, output_dir: str) -> str:
    """Converts a DOCX file to PDF using headless LibreOffice."""
    lo_bin = shutil.which("libreoffice") or shutil.which("soffice")
    if not lo_bin:
        raise RuntimeError("LibreOffice binary not found in system PATH. Install libreoffice or deploy with Docker to enable PDF conversion.")

    abs_out_dir = os.path.abspath(output_dir)
    os.makedirs(abs_out_dir, exist_ok=True)
    lo_profile_dir = os.path.join(abs_out_dir, f"lo_profile_{os.getpid()}")
    os.makedirs(lo_profile_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(docx_path))[0]
    pdf_path = os.path.join(abs_out_dir, f"{base_name}.pdf")
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception:
            pass

    try:
        cmd = [
            lo_bin,
            f"-env:UserInstallation=file://{lo_profile_dir}",
            "--headless",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            abs_out_dir,
            os.path.abspath(docx_path)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
        
        if not os.path.exists(pdf_path):
            pdfs = glob.glob(os.path.join(abs_out_dir, "*.pdf"))
            if pdfs:
                pdf_path = pdfs[0]
            else:
                raise FileNotFoundError(f"PDF output not found for {docx_path}")
        return pdf_path
    finally:
        try:
            shutil.rmtree(lo_profile_dir, ignore_errors=True)
        except Exception:
            pass


def generate_page_previews(pdf_path: str, preview_dir: str, dpi: int = 120, max_pages: int = 100) -> List[str]:
    """Generates PNG images for each page of the PDF using pdftoppm, purging stale pages first."""
    ppm_bin = shutil.which("pdftoppm")
    if not ppm_bin:
        raise RuntimeError("pdftoppm binary not found in system PATH. Install poppler-utils to enable page previews.")

    if os.path.exists(preview_dir):
        shutil.rmtree(preview_dir, ignore_errors=True)
    os.makedirs(preview_dir, exist_ok=True)

    prefix = os.path.join(preview_dir, "page")
    cmd = [
        ppm_bin,
        "-png",
        "-r", str(dpi),
        pdf_path,
        prefix
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed: {result.stderr}")

    page_files = sorted(glob.glob(os.path.join(preview_dir, "page-*.png")))
    return page_files[:max_pages]


def _get_font(size: int = 14, bold: bool = False) -> ImageFont.ImageFont:
    """Loads system Serif or Sans TTF font prioritizing LiberationSerif (metric-identical to Times New Roman)."""
    candidates = [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in candidates:
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default(size=size)


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Wraps text into lines that fit within max_width pixels, cleanly expanding tabs and spaces."""
    cleaned = text.replace("\t", "    ")
    lines = []
    for para in cleaned.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        words = para.split(" ")
        current_line: List[str] = []
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_w = bbox[2] - bbox[0]
            if line_w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        if current_line:
            lines.append(" ".join(current_line))
    return lines


def _draw_justified_line(
    draw: ImageDraw.ImageDraw,
    line: str,
    font: ImageFont.ImageFont,
    x_left: int,
    max_width: int,
    y: int,
    fill: str = "#1E293B",
    is_last_line: bool = False
):
    """Draws a line of text justified to max_width by distributing space between words."""
    words = line.strip().split()
    if is_last_line or len(words) <= 1:
        draw.text((x_left, y), line, font=font, fill=fill)
        return

    word_widths = [draw.textbbox((0, 0), w, font=font)[2] - draw.textbbox((0, 0), w, font=font)[0] for w in words]
    total_word_w = sum(word_widths)
    space_needed = max_width - total_word_w
    if space_needed <= 0 or space_needed > len(words) * 35:
        draw.text((x_left, y), line, font=font, fill=fill)
        return

    num_gaps = len(words) - 1
    base_space = space_needed // num_gaps
    extra_space = space_needed % num_gaps

    cur_x = x_left
    for idx, (word, w_w) in enumerate(zip(words, word_widths)):
        draw.text((cur_x, y), word, font=font, fill=fill)
        cur_x += w_w
        if idx < num_gaps:
            cur_x += base_space + (1 if idx < extra_space else 0)


def generate_pure_python_previews(
    docx_path: str,
    preview_dir: str,
    dpi: int = 120,
    max_pages: int = 100,
    metadata: Optional[Any] = None
) -> List[str]:
    """
    High-fidelity pure-Python preview generator using Pillow.
    Renders official Senate A4 pages with full support for:
    - Official UBa central crest logo
    - Table grids with headers and cell borders
    - Embedded diagrams and drawings extracted from docx parts
    - Boxed statutory titles
    - Dynamic Roman preliminary and Arabic body page numbering
    """
    if os.path.exists(preview_dir):
        shutil.rmtree(preview_dir, ignore_errors=True)
    os.makedirs(preview_dir, exist_ok=True)

    try:
        doc = docx.Document(docx_path)
    except Exception as e:
        print(f"[AcadFormat Converter] Error reading docx for preview: {e}")
        return []

    # Collect body items in document order: paragraphs ('p') and tables ('tbl')
    body_items: List[Tuple[str, Any]] = []
    for child in doc.element.body:
        tag = child.tag.split("}")[-1]
        if tag == "p":
            p = docx.text.paragraph.Paragraph(child, doc)
            body_items.append(("p", p))
        elif tag == "tbl":
            t = docx.table.Table(child, doc)
            body_items.append(("tbl", t))

    # Partition into logical pages based on page breaks
    pages_items: List[List[Tuple[str, Any]]] = []
    curr_page: List[Tuple[str, Any]] = []

    for item_type, item in body_items:
        if item_type == "p":
            p_has_break_before = bool(item.paragraph_format.page_break_before or item._p.xpath('.//w:pPr/w:pageBreakBefore'))
            if p_has_break_before and curr_page:
                pages_items.append(curr_page)
                curr_page = []

            curr_page.append((item_type, item))
            has_break = any("w:br" in r._r.xml and "page" in r._r.xml for r in item.runs) or bool(item._p.xpath('.//w:pPr/w:sectPr'))
            if has_break:
                pages_items.append(curr_page)
                curr_page = []
        else:
            curr_page.append((item_type, item))

    if curr_page:
        pages_items.append(curr_page)

    if max_pages and max_pages > 0:
        pages_items = pages_items[:max_pages]

    if not pages_items:
        return []

    W, H = 992, 1403  # A4 at 120 DPI
    left_margin = 140
    right_margin = W - 120
    max_text_w = right_margin - left_margin

    # Official Logo Loading: Prioritize UBa central crest
    logo_img = None
    uba_logo_path = os.path.join(ASSETS_DIR, "uba_logo.png")
    coltech_logo_path = os.path.join(ASSETS_DIR, "coltech_logo.png")
    if os.path.exists(uba_logo_path):
        try:
            logo_img = Image.open(uba_logo_path).convert("RGBA")
            logo_img.thumbnail((110, 110), Image.Resampling.LANCZOS)
        except Exception:
            pass
    elif os.path.exists(coltech_logo_path):
        try:
            logo_img = Image.open(coltech_logo_path).convert("RGBA")
            logo_img.thumbnail((110, 110), Image.Resampling.LANCZOS)
        except Exception:
            pass

    coltech_img = None
    if os.path.exists(coltech_logo_path):
        try:
            coltech_img = Image.open(coltech_logo_path).convert("RGBA")
            coltech_img.thumbnail((85, 85), Image.Resampling.LANCZOS)
        except Exception:
            pass

    f_normal = _get_font(13, False)
    f_bold = _get_font(13, True)
    f_title = _get_font(15, True)
    f_h1 = _get_font(15, True)
    f_h2 = _get_font(13, True)
    f_tbl_hdr = _get_font(12, True)
    f_tbl_cell = _get_font(11, False)
    f_footer = _get_font(12, False)

    # Detect body start page dynamically (first page with actual CHAPTER 1 or INTRODUCTION, ignoring TOC)
    import re
    body_start_page = 999
    for p_idx, page_content in enumerate(pages_items):
        is_prelim = any(
            itype == "p" and any(k in elem.text.strip().upper() for k in [
                "TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES", "PRELIMINARY",
                "DECLARATION", "CERTIFICATION", "ABSTRACT", "RÉSUMÉ", "DEDICATION", "ACKNOWLEDGEMENT"
            ])
            for itype, elem in page_content
        )
        if is_prelim:
            continue

        for itype, elem in page_content:
            if itype == "p":
                t = elem.text.strip().upper()
                is_toc_entry = bool(re.search(r'(?:\.{2,}|\t|\s{3,})\d+\s*$', t))
                if not is_toc_entry and (t.startswith("CHAPTER 1") or t == "INTRODUCTION" or t.startswith("1.1 ")):
                    body_start_page = p_idx + 1
                    break
        if body_start_page != 999:
            break

    rendered_pages = []
    page_counter = 1

    def start_new_page():
        nonlocal page_counter
        p_img = Image.new("RGB", (W, H), "white")
        p_draw = ImageDraw.Draw(p_img)
        p_draw.rectangle([(0, 0), (W-1, H-1)], outline="#CBD5E1", width=1)
        return p_img, p_draw, 100

    current_img, draw, curr_y = start_new_page()

    def finish_page(img_to_save, p_num):
        # Draw bottom-centered page footer
        if p_num > 2:
            if p_num < body_start_page:
                romans = ["", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii"]
                r_idx = p_num - 1
                r_text = romans[r_idx] if r_idx < len(romans) else str(r_idx)
                draw_f = ImageDraw.Draw(img_to_save)
                draw_f.text((W // 2, 1335), r_text, font=f_footer, fill="#475569", anchor="mm")
            else:
                arabic_num = str(p_num - body_start_page + 1)
                draw_f = ImageDraw.Draw(img_to_save)
                draw_f.text((W // 2, 1335), arabic_num, font=f_footer, fill="#475569", anchor="mm")

        out_file = os.path.join(preview_dir, f"page-{p_num:02d}.png")
        img_to_save.save(out_file, "PNG", optimize=True)
        rendered_pages.append(out_file)

    for idx, page_content in enumerate(pages_items):
        is_cover_or_title = (idx < 2)

        if idx > 0 and curr_y > 100:
            finish_page(current_img, page_counter)
            page_counter += 1
            if max_pages and page_counter > max_pages:
                break
            current_img, draw, curr_y = start_new_page()

        for itype, elem in page_content:
            if itype == "tbl":
                t = elem
                num_rows = len(t.rows)
                num_cols = len(t.columns) if num_rows > 0 else 0

                # 1. 1x1 Boxed Title Table
                if num_rows == 1 and num_cols == 1:
                    t_text = t.rows[0].cells[0].text.strip().upper()
                    if t_text:
                        t_lines = _wrap_text(t_text, f_title, max_text_w - 40, draw)
                        b_h = max(70, len(t_lines) * 24 + 26)
                        if curr_y + b_h > 1280 and curr_y > 150:
                            finish_page(current_img, page_counter)
                            page_counter += 1
                            current_img, draw, curr_y = start_new_page()
                        draw.rectangle([(left_margin, curr_y), (right_margin, curr_y + b_h)], outline="black", width=2)
                        ty = curr_y + 14
                        for tl in t_lines:
                            draw.text((W // 2, ty), tl, font=f_title, fill="black", anchor="mm")
                            ty += 24
                        curr_y += b_h + 20
                    continue

                # 2. 1x3 Header Banner Table
                if num_rows == 1 and num_cols == 3:
                    c0_txt = t.rows[0].cells[0].text.strip()
                    c2_txt = t.rows[0].cells[2].text.strip()
                    banner_h = 100
                    if curr_y + banner_h > 1280 and curr_y > 150:
                        finish_page(current_img, page_counter)
                        page_counter += 1
                        current_img, draw, curr_y = start_new_page()

                    # Left School
                    w_left = _wrap_text(c0_txt, f_bold, 240, draw)
                    ly = curr_y + 10
                    for wl in w_left:
                        draw.text((left_margin + 120, ly), wl, font=f_bold, fill="black", anchor="ma")
                        ly += 18

                    # Center Logo (UBa Official Crest)
                    if logo_img:
                        current_img.paste(logo_img, ((W - logo_img.width) // 2, curr_y), mask=logo_img)

                    # Right Dept
                    w_right = _wrap_text(c2_txt, f_bold, 240, draw)
                    ry = curr_y + 10
                    for wr in w_right:
                        draw.text((right_margin - 120, ry), wr, font=f_bold, fill="black", anchor="ma")
                        ry += 18

                    curr_y += banner_h + 20
                    continue

                # 3. 1x2 Signature Table
                if num_rows == 1 and num_cols == 2:
                    s0 = t.rows[0].cells[0].text.strip()
                    s1 = t.rows[0].cells[1].text.strip()
                    draw.text((left_margin, curr_y), s0, font=f_normal, fill="black")
                    draw.text((right_margin, curr_y), s1, font=f_normal, fill="black", anchor="ra")
                    curr_y += 30
                    continue

                # 4. Multi-row Data Tables (Render grid and cell contents)
                if num_rows > 1 and num_cols > 0:
                    col_w = max_text_w // num_cols
                    for r_idx, row in enumerate(t.rows):
                        # Calculate needed row height
                        row_cells_text = [c.text.strip().replace("\t", " ") for c in row.cells]
                        wrapped_cells = [_wrap_text(ctxt, f_tbl_hdr if r_idx == 0 else f_tbl_cell, col_w - 12, draw) for ctxt in row_cells_text]
                        max_cell_lines = max([len(lines) for lines in wrapped_cells] or [1])
                        row_h = max(24, max_cell_lines * 16 + 10)

                        if curr_y + row_h > 1280 and curr_y > 150:
                            finish_page(current_img, page_counter)
                            page_counter += 1
                            current_img, draw, curr_y = start_new_page()

                        # Header fill
                        if r_idx == 0:
                            draw.rectangle([(left_margin, curr_y), (right_margin, curr_y + row_h)], fill="#F1F5F9", outline="#64748B", width=1)
                        else:
                            draw.rectangle([(left_margin, curr_y), (right_margin, curr_y + row_h)], outline="#CBD5E1", width=1)

                        # Cell borders and text
                        for c_idx in range(num_cols):
                            cx = left_margin + c_idx * col_w
                            if c_idx > 0:
                                draw.line([(cx, curr_y), (cx, curr_y + row_h)], fill="#94A3B8" if r_idx == 0 else "#CBD5E1", width=1)
                            
                            c_font = f_tbl_hdr if r_idx == 0 else f_tbl_cell
                            c_color = "black" if r_idx == 0 else "#1E293B"
                            cy = curr_y + 5
                            if c_idx < len(wrapped_cells):
                                for cline in wrapped_cells[c_idx]:
                                    draw.text((cx + 6, cy), cline, font=c_font, fill=c_color)
                                    cy += 16
                        curr_y += row_h
                    curr_y += 15
                    continue

            # Paragraph Processing
            p = elem
            txt = p.text.strip()

            # Check for embedded drawings or images
            has_drawing = bool(p._p.xpath('.//w:drawing') or p._p.xpath('.//w:pict'))
            if has_drawing:
                fig_drawn = False
                rIds = p._p.xpath('.//a:blip/@r:embed')
                for rId in rIds:
                    if rId in doc.part.related_parts:
                        try:
                            part = doc.part.related_parts[rId]
                            fig_im = Image.open(io.BytesIO(part.blob))
                            # Scale maintaining aspect ratio (max width max_text_w, max height 380)
                            scale = min(max_text_w / fig_im.width, 380 / fig_im.height, 1.0)
                            nw = int(fig_im.width * scale)
                            nh = int(fig_im.height * scale)
                            fig_resized = fig_im.resize((nw, nh), Image.Resampling.LANCZOS)
                            
                            if curr_y + nh + 20 > 1280 and curr_y > 150:
                                finish_page(current_img, page_counter)
                                page_counter += 1
                                current_img, draw, curr_y = start_new_page()

                            current_img.paste(fig_resized, ((W - nw) // 2, curr_y))
                            curr_y += nh + 12
                            fig_drawn = True
                            break
                        except Exception:
                            pass
                if not fig_drawn:
                    # Draw a clean diagram placeholder box
                    box_h = 160
                    if curr_y + box_h > 1280 and curr_y > 150:
                        finish_page(current_img, page_counter)
                        page_counter += 1
                        current_img, draw, curr_y = start_new_page()
                    draw.rectangle([(left_margin + 50, curr_y), (right_margin - 50, curr_y + box_h)], fill="#F8FAFC", outline="#94A3B8", width=1)
                    draw.text((W // 2, curr_y + box_h // 2), "[System Figure / Diagram]", font=f_bold, fill="#475569", anchor="mm")
                    curr_y += box_h + 12

            if not txt:
                if not has_drawing:
                    curr_y += 8
                continue

            # TOC line rendering with dot leaders
            if ("\t" in txt or re.search(r'\.{3,}\s*\d+$', txt)) and idx > 1:
                parts = txt.split("\t") if "\t" in txt else re.split(r'\.{3,}\s*', txt)
                t_title = parts[0].strip()
                t_page = parts[-1].strip() if len(parts) > 1 else ""
                is_major_toc = any(t_title.upper().startswith(ch) for ch in ["CHAPTER", "CHAPITRE", "PRELIMINARY", "REFERENCES", "APPENDICES"])
                t_font = f_bold if is_major_toc else f_normal

                if curr_y + 26 > 1280 and curr_y > 150:
                    finish_page(current_img, page_counter)
                    page_counter += 1
                    current_img, draw, curr_y = start_new_page()

                draw.text((left_margin, curr_y), t_title, font=t_font, fill="black")
                if t_page:
                    page_bbox = draw.textbbox((0, 0), t_page, font=t_font)
                    page_w = page_bbox[2] - page_bbox[0]
                    draw.text((right_margin - page_w, curr_y), t_page, font=t_font, fill="black")

                    title_bbox = draw.textbbox((0, 0), t_title, font=t_font)
                    t_w = title_bbox[2] - title_bbox[0]
                    dot_start = left_margin + t_w + 10
                    dot_end = right_margin - page_w - 10
                    if dot_end > dot_start:
                        dot_str = ". " * max(1, (dot_end - dot_start) // 12)
                        draw.text((dot_start, curr_y), dot_str, font=f_normal, fill="#94A3B8")
                curr_y += 22
                continue

            p_style = getattr(p.style, "name", "Normal")
            is_ch = bool(re.match(r'^(?:CHAPTER|CHAPITRE)\s+\d+', txt, re.IGNORECASE))
            is_sec = bool(re.match(r'^\d+\.\d+(?:\.\d+)*\.?\s*', txt)) and len(txt) < 180 and not (txt.count('.') > 2 and txt.endswith('.'))
            is_style_h = "Heading" in p_style and len(txt) < 180
            is_run_bold = bool(p.runs and any(r.bold for r in p.runs) and len(txt) < 90 and not txt.endswith('.'))
            is_cap = bool(re.match(r'^(?:Figure|Fig\.?|Table|Tableau)\s*(?:\d+|[IVXLCDM]+)?[:.\s]', txt, re.IGNORECASE))

            is_heading = is_ch or is_sec or is_style_h or (txt.isupper() and len(txt) < 70) or is_run_bold or is_cap

            if is_ch:
                p_font = f_h1
            elif is_sec or is_style_h or is_run_bold or is_cap:
                p_font = f_h2
            else:
                p_font = f_normal

            # Prevent preliminary headings from ever being boxed as titles
            is_prelim_header = any(k in txt.upper() for k in [
                "DECLARATION", "ORIGINALITY", "CERTIFICATION", "DEDICATION", "ACKNOWLEDGEMENT",
                "ABSTRACT", "RESUME", "RÉSUMÉ", "TABLE OF CONTENTS", "LIST OF", "PRELIMINARY",
                "ANNEX", "APPENDIX", "THE UNIVERSITY", "COLLEGE", "FACULTY", "DEPARTMENT"
            ])

            # Boxed title check on cover/title page (strictly for true project titles)
            is_boxed_title = is_cover_or_title and not is_prelim_header and (
                ("ORCHESTRATOR" in txt.upper() or "DESIGN" in txt.upper() or "SYSTEM" in txt.upper() or "INVESTIGATION" in txt.upper() or len(txt) > 28)
                and not any(k in txt.upper() for k in ["SUBMITTED", "PRESENTED", "SUPERVISED", "SUPERVISOR", "REGISTRATION", "DATE", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"])
            )

            if is_boxed_title:
                t_lines = _wrap_text(txt.upper(), f_title, max_text_w - 40, draw)
                b_h = max(70, len(t_lines) * 24 + 26)
                if curr_y + b_h > 1280 and curr_y > 150:
                    finish_page(current_img, page_counter)
                    page_counter += 1
                    current_img, draw, curr_y = start_new_page()
                draw.rectangle([(left_margin, curr_y), (right_margin, curr_y + b_h)], outline="black", width=2)
                ty = curr_y + 14
                for tl in t_lines:
                    draw.text((W // 2, ty), tl, font=f_title, fill="black", anchor="mm")
                    ty += 24
                curr_y += b_h + 20
                continue

            wrapped = _wrap_text(txt, p_font, max_text_w, draw)
            line_h = 24 if is_heading else 20
            p_needed_h = len(wrapped) * line_h + (14 if is_heading else 8)

            if curr_y + p_needed_h > 1280 and curr_y > 150:
                finish_page(current_img, page_counter)
                page_counter += 1
                if max_pages and page_counter > max_pages:
                    break
                current_img, draw, curr_y = start_new_page()

            if is_cover_or_title or (txt.isupper() and len(txt) < 60) or is_ch or is_cap:
                align = "center"
            elif is_heading:
                align = "left"
            else:
                align = "justify"

            for l_idx, line in enumerate(wrapped):
                is_last = (l_idx == len(wrapped) - 1)
                if align == "center":
                    draw.text((W // 2, curr_y), line, font=p_font, fill="black", anchor="ma")
                elif align == "left":
                    draw.text((left_margin, curr_y), line, font=p_font, fill="#0F172A")
                elif align == "justify":
                    _draw_justified_line(draw, line, p_font, left_margin, max_text_w, curr_y, fill="#1E293B", is_last_line=is_last)
                curr_y += line_h
            curr_y += 12 if is_heading else 6

    if curr_y > 100:
        finish_page(current_img, page_counter)

    return sorted(glob.glob(os.path.join(preview_dir, "page-*.png")))


def image_file_to_base64_data_url(file_path: str) -> str:
    """Converts a local image file (PNG/JPG) to a Base64 data URL for instant zero-request client rendering."""
    try:
        import base64
        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        ext = os.path.splitext(file_path)[1].lower().replace(".", "")
        mime = "image/png" if ext == "png" else ("image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""


def images_to_pdf(image_paths: List[str], output_pdf_path: str) -> bool:
    """Assembles a list of image files into a single multi-page PDF document."""
    try:
        valid_imgs = []
        for p in image_paths:
            if os.path.exists(p):
                try:
                    valid_imgs.append(Image.open(p).convert("RGB"))
                except Exception:
                    pass
        if not valid_imgs:
            return False
        valid_imgs[0].save(output_pdf_path, "PDF", resolution=120.0, save_all=True, append_images=valid_imgs[1:])
        return os.path.exists(output_pdf_path)
    except Exception as e:
        print(f"[AcadFormat Converter] Error assembling images to PDF: {e}")
        return False


def generate_document_previews(
    docx_path: str,
    output_dir: str,
    preview_dir: str,
    dpi: int = 120,
    max_pages: int = 100,
    metadata: Optional[Any] = None
) -> Tuple[Optional[str], List[str], List[str]]:
    """
    Primary preview orchestrator:
    1. Converts DOCX to true vector PDF via LibreOffice headless.
    2. Generates crisp page preview PNGs using pdftoppm.
    3. Seamlessly falls back to pure-Python preview generator without overwriting the native PDF.
    Always returns (pdf_path, preview_page_paths, preview_data_urls).
    """
    out_pdf_path = None
    preview_pages: List[str] = []
    preview_data_urls: List[str] = []

    # Step 1: Generate true vector PDF via LibreOffice
    if is_libreoffice_available():
        try:
            out_pdf_path = convert_docx_to_pdf(docx_path, output_dir)
            if out_pdf_path and os.path.exists(out_pdf_path):
                try:
                    from backend.restructurer import sync_toc_page_numbers
                    if sync_toc_page_numbers(docx_path, out_pdf_path):
                        # TOC was updated with exact page numbers, re-convert to synchronize PDF
                        out_pdf_path = convert_docx_to_pdf(docx_path, output_dir)
                except Exception as sync_err:
                    print(f"[AcadFormat Converter] TOC sync warning: {sync_err}")
        except Exception as lo_err:
            print(f"[AcadFormat Converter] LibreOffice conversion skipped: {lo_err}")

    # Step 2: Generate previews from the true PDF if pdftoppm is available
    if out_pdf_path and os.path.exists(out_pdf_path) and is_pdftoppm_available():
        try:
            preview_pages = generate_page_previews(out_pdf_path, preview_dir, dpi=dpi, max_pages=max_pages)
            if preview_pages:
                preview_data_urls = [image_file_to_base64_data_url(p) for p in preview_pages]
                return out_pdf_path, preview_pages, preview_data_urls
        except Exception as ppm_err:
            print(f"[AcadFormat Converter] pdftoppm preview generation failed: {ppm_err}")

    # Step 3: Pure-Python preview generator fallback (renders tables, figures, boxed titles)
    try:
        preview_pages = generate_pure_python_previews(docx_path, preview_dir, dpi=dpi, max_pages=max_pages, metadata=metadata)
        if preview_pages:
            preview_data_urls = [image_file_to_base64_data_url(p) for p in preview_pages]
            # ONLY assemble an image PDF if LibreOffice could not produce a vector PDF
            if not out_pdf_path or not os.path.exists(out_pdf_path):
                candidate_pdf = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(docx_path))[0]}.pdf")
                if images_to_pdf(preview_pages, candidate_pdf):
                    out_pdf_path = candidate_pdf
    except Exception as py_err:
        print(f"[AcadFormat Converter] Pure-Python preview generator error: {py_err}")

    return out_pdf_path, preview_pages, preview_data_urls
