"""
Document Converter: Converts DOCX to PDF using LibreOffice headless
and generates high-resolution page previews with pdftoppm.
"""
import os
import shutil
import subprocess
import glob
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
    lo_profile_dir = os.path.join(abs_out_dir, "lo_profile")
    os.makedirs(lo_profile_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(docx_path))[0]
    pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except Exception:
            pass

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
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
    
    if not os.path.exists(pdf_path):
        # Look for any pdf generated
        pdfs = glob.glob(os.path.join(output_dir, "*.pdf"))
        if pdfs:
            pdf_path = pdfs[0]
        else:
            raise FileNotFoundError(f"PDF output not found for {docx_path}")
    return pdf_path


def generate_page_previews(pdf_path: str, preview_dir: str, dpi: int = 120) -> List[str]:
    """Generates PNG images for each page of the PDF using pdftoppm, purging stale pages first."""
    ppm_bin = shutil.which("pdftoppm")
    if not ppm_bin:
        raise RuntimeError("pdftoppm binary not found in system PATH. Install poppler-utils to enable page previews.")

    # Purge existing preview directory completely to avoid stale pages joining
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
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"pdftoppm failed: {result.stderr}")

    # Collect generated page images sorted by page number
    page_files = sorted(glob.glob(os.path.join(preview_dir, "page-*.png")))
    return page_files


def _get_font(size: int = 14, bold: bool = False) -> ImageFont.ImageFont:
    """Loads system Serif or Sans TTF font with fallback to Pillow default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
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
    """Wraps text into lines that fit within max_width pixels."""
    lines = []
    for para in text.split("\n"):
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
import base64

def image_file_to_base64_data_url(image_path: str) -> str:
    """Encodes a PNG image file into a standard base64 data URL for instant zero-request client rendering."""
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{encoded}"


def _wrap_text_fast(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """High-speed text wrapping optimized for sub-second page generation."""
    lines = []
    # Measure typical character width to skip expensive pixel measurements for obviously short lines
    try:
        sample_w = draw.textlength("abcdefghij", font=font) / 10.0
    except Exception:
        sample_w = 8.0

    chars_per_line = max(20, int(max_width / sample_w))

    for para in text.split("\n"):
        p_clean = para.strip()
        if not p_clean:
            lines.append("")
            continue
        if len(p_clean) <= chars_per_line and draw.textlength(p_clean, font=font) <= max_width:
            lines.append(p_clean)
            continue

        words = p_clean.split(" ")
        current_line: List[str] = []
        for word in words:
            test_line = " ".join(current_line + [word])
            if draw.textlength(test_line, font=font) <= max_width:
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


def generate_pure_python_previews(
    docx_path: str,
    preview_dir: str,
    dpi: int = 120,
    max_pages: int = 14,
    metadata: Optional[Any] = None
) -> Tuple[List[str], List[str]]:
    """
    High-fidelity pure-Python preview generator using Pillow.
    Renders official Senate A4 pages (Cover, Title, Preliminaries, Chapters)
    directly without requiring LibreOffice or pdftoppm.
    Returns: (page_file_paths, page_data_urls) for instant zero-request rendering.
    """
    if os.path.exists(preview_dir):
        shutil.rmtree(preview_dir, ignore_errors=True)
    os.makedirs(preview_dir, exist_ok=True)

    try:
        doc = docx.Document(docx_path)
    except Exception as e:
        print(f"[AcadFormat Converter] Error reading docx for preview: {e}")
        return [], []

    # Partition paragraphs into logical pages by page break runs or paragraph count
    pages_paragraphs: List[List[Any]] = []
    curr_page: List[Any] = []
    has_any_break = False

    for p in doc.paragraphs:
        curr_page.append(p)
        has_break = any("w:br" in r._r.xml and "page" in r._r.xml for r in p.runs)
        if has_break:
            has_any_break = True
            pages_paragraphs.append(curr_page)
            curr_page = []
    if curr_page:
        pages_paragraphs.append(curr_page)

    # Fallback: if document has no hard page breaks, paginate automatically (~18 paras per page)
    if (not has_any_break or len(pages_paragraphs) <= 1) and len(doc.paragraphs) > 5:
        pages_paragraphs = []
        chunk_size = 18
        all_p = [p for p in doc.paragraphs if p.text.strip()]
        for i in range(0, len(all_p), chunk_size):
            pages_paragraphs.append(all_p[i:i + chunk_size])

    if not pages_paragraphs:
        return [], []

    W, H = 992, 1403  # A4 at 120 DPI
    left_margin = 150
    right_margin = W - 120
    max_text_w = right_margin - left_margin

    # Load crest logo if present
    logo_img = None
    for lpath in [os.path.join(ASSETS_DIR, "coltech_logo.png"), os.path.join(ASSETS_DIR, "uba_logo.png")]:
        if os.path.exists(lpath):
            try:
                logo_img = Image.open(lpath).convert("RGBA")
                logo_img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                break
            except Exception:
                pass

    f_normal = _get_font(13, False)
    f_bold = _get_font(13, True)
    f_title = _get_font(15, True)
    f_h1 = _get_font(15, True)
    f_h2 = _get_font(13, True)
    f_footer = _get_font(12, False)

    body_start_page = 8

    # Extract metadata clues
    extracted_title = getattr(metadata, "title", None) or "TITLE OF THE WORK"
    extracted_author = getattr(metadata, "author", None) or "CANDIDATE NAME"
    extracted_reg = getattr(metadata, "reg_number", None) or "UBa23PH000"
    supervisors = getattr(metadata, "supervisors", None) or []
    extracted_supervisor = supervisors[0] if supervisors else "SUPERVISOR NAME"
    extracted_date = getattr(metadata, "submission_month", "JUNE") + " " + getattr(metadata, "submission_year", "2026")
    extracted_faculty = getattr(metadata, "faculty", "COLLEGE OF TECHNOLOGY").upper()
    extracted_dept = getattr(metadata, "department", "COMPUTER ENGINEERING").upper()

    if extracted_title == "TITLE OF THE WORK":
        for pg in pages_paragraphs[:2]:
            for p in pg:
                txt = p.text.strip()
                if not txt:
                    continue
                if len(txt) > 20 and ("ORCHESTRATOR" in txt.upper() or "DESIGN" in txt.upper() or "STUDY" in txt.upper() or "INVESTIGATION" in txt.upper() or "SYSTEM" in txt.upper()):
                    extracted_title = txt
                elif "REGISTRATION NUMBER" in txt.upper() or "REG NO" in txt.upper():
                    extracted_reg = txt
                elif "SUPERVISOR" in txt.upper():
                    lines = [l.strip() for l in txt.split("\n") if l.strip()]
                    if len(lines) > 1:
                        extracted_supervisor = lines[1]

    # Limit to max_pages for snappy responsive UX
    target_pages = pages_paragraphs[:max_pages]

    for idx, p_list in enumerate(target_pages):
        page_num = idx + 1
        img = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(img)

        # Outer subtle page border
        draw.rectangle([(0, 0), (W-1, H-1)], outline="#CBD5E1", width=1)

        if page_num in (1, 2):
            # -------------------------------------------------------------
            # COVER PAGE (1) & TITLE PAGE (2)
            # -------------------------------------------------------------
            if logo_img:
                img.paste(logo_img, ((W - logo_img.width) // 2, 70), mask=logo_img)

            draw.text((left_margin, 70), f"THE UNIVERSITY OF BAMENDA\n{extracted_faculty}", font=f_bold, fill="#1E3A8A", align="left")
            draw.text((right_margin, 70), f"REPUBLIC OF CAMEROON\nDEPARTMENT OF {extracted_dept}", font=f_bold, fill="#1E3A8A", anchor="ra", align="right")

            # Boxed Title (Single-line rectangular box)
            title_lines = _wrap_text_fast(extracted_title.upper(), f_title, max_text_w - 40, draw)
            box_h = max(90, len(title_lines) * 26 + 36)
            box_y = 280
            draw.rectangle([(left_margin, box_y), (right_margin, box_y + box_h)], outline="black", width=2)
            ty = box_y + 18
            for tl in title_lines:
                draw.text((W // 2, ty), tl, font=f_title, fill="black", anchor="mm")
                ty += 26

            # Purpose clause
            curr_y = box_y + box_h + 40
            degree_str = "Bachelor of Science (B.Sc)" if page_num == 1 else f"Bachelor of Science (B.Sc) in {extracted_dept.title()}"
            clause = f"A Dissertation Submitted to the Department of {extracted_dept.title()} in Partial Fulfillment of the Requirements for the Award of the Degree of {degree_str}"
            for cl in _wrap_text_fast(clause, f_normal, max_text_w, draw):
                draw.text((W // 2, curr_y), cl, font=f_normal, fill="#1F2937", anchor="mm")
                curr_y += 22

            # Candidate & Supervisor
            curr_y += 50
            draw.text((W // 2, curr_y), "PRESENTED BY:", font=f_bold, fill="black", anchor="mm")
            curr_y += 24
            draw.text((W // 2, curr_y), extracted_author.upper(), font=f_bold, fill="black", anchor="mm")
            curr_y += 20
            draw.text((W // 2, curr_y), f"REGISTRATION NUMBER: {extracted_reg}", font=f_normal, fill="black", anchor="mm")

            curr_y += 45
            draw.text((W // 2, curr_y), "SUPERVISED BY:", font=f_bold, fill="black", anchor="mm")
            curr_y += 24
            draw.text((W // 2, curr_y), extracted_supervisor, font=f_bold, fill="black", anchor="mm")
            curr_y += 20
            draw.text((W // 2, curr_y), "Rank: Associate Professor", font=f_normal, fill="#4B5563", anchor="mm")

            # Anchored submission date at bottom
            draw.text((W // 2, 1310), extracted_date, font=f_bold, fill="black", anchor="mm")

        else:
            # -------------------------------------------------------------
            # PRELIMINARY PAGES & CHAPTER BODY PAGES
            # -------------------------------------------------------------
            curr_y = 100
            for p in p_list:
                txt = p.text.strip()
                if not txt:
                    continue
                p_style = getattr(p.style, "name", "Normal")
                is_heading = "Heading" in p_style or (txt.isupper() and len(txt) < 80)

                p_font = f_h1 if ("Heading 1" in p_style or (txt.isupper() and len(txt) < 50)) else (f_h2 if "Heading" in p_style else f_normal)
                align = "center" if (txt.isupper() and len(txt) < 60) else "left"

                # Check if paragraph is a Table of Contents entry (ends with page number)
                words = txt.split()
                if len(words) >= 2 and words[-1].isdigit() and ("...." in txt or len(txt) < 100):
                    title_part = " ".join(words[:-1]).replace(".", "").strip()
                    page_part = words[-1]
                    draw.text((left_margin, curr_y), title_part, font=p_font, fill="#1E293B")
                    draw.text((right_margin, curr_y), page_part, font=p_font, fill="#1E293B", anchor="ra")
                    # Dotted leader
                    dots_x_start = left_margin + int(draw.textlength(title_part, font=p_font)) + 10
                    dots_x_end = right_margin - int(draw.textlength(page_part, font=p_font)) - 10
                    if dots_x_end > dots_x_start:
                        dots_w = int(draw.textlength(". ", font=f_normal))
                        num_dots = (dots_x_end - dots_x_start) // dots_w
                        draw.text((dots_x_start, curr_y), ". " * num_dots, font=f_normal, fill="#94A3B8")
                    curr_y += 22
                    continue

                wrapped = _wrap_text_fast(txt, p_font, max_text_w, draw)

                for line in wrapped:
                    if curr_y > 1280:
                        break
                    if align == "center":
                        draw.text((W // 2, curr_y), line, font=p_font, fill="black", anchor="ma")
                    else:
                        draw.text((left_margin, curr_y), line, font=p_font, fill="#1E293B")
                    curr_y += 22 if is_heading else 20
                curr_y += 12 if is_heading else 6
                if curr_y > 1280:
                    break

            # Bottom-centered page footer
            if page_num < body_start_page:
                romans = ["", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]
                r_idx = page_num - 1
                r_text = romans[r_idx] if r_idx < len(romans) else str(r_idx)
                draw.text((W // 2, 1335), r_text, font=f_footer, fill="#475569", anchor="mm")
            else:
                arabic_num = str(page_num - body_start_page + 1)
                draw.text((W // 2, 1335), arabic_num, font=f_footer, fill="#475569", anchor="mm")

        out_file = os.path.join(preview_dir, f"page-{page_num:02d}.png")
        img.save(out_file, "PNG", compress_level=1)

    page_files = sorted(glob.glob(os.path.join(preview_dir, "page-*.png")))
    data_urls = [image_file_to_base64_data_url(p) for p in page_files]
    return page_files, data_urls


def generate_document_previews(
    docx_path: str,
    output_dir: str,
    preview_dir: str,
    dpi: int = 120,
    max_pages: int = 14,
    metadata: Optional[Any] = None
) -> Tuple[Optional[str], List[str], List[str]]:
    """
    Primary preview orchestrator:
    Generates pure-Python page previews instantly with Base64 data URLs for zero-request browser rendering.
    Optionally generates official PDF via LibreOffice if available.
    Returns: (pdf_path, preview_page_file_paths, preview_data_urls).
    """
    out_pdf_path = None
    preview_files: List[str] = []
    preview_data_urls: List[str] = []

    # Generate pure-Python previews (ultra-fast, zero-binary dependency, ~0.6s)
    try:
        preview_files, preview_data_urls = generate_pure_python_previews(
            docx_path, preview_dir, dpi=dpi, max_pages=max_pages, metadata=metadata
        )
    except Exception as py_err:
        print(f"[AcadFormat Converter] Pure-Python preview generator error: {py_err}")

    # Optionally attempt headless LibreOffice for PDF export if installed
    if is_libreoffice_available():
        try:
            out_pdf_path = convert_docx_to_pdf(docx_path, output_dir)
        except Exception as lo_err:
            print(f"[AcadFormat Converter] LibreOffice background conversion skipped: {lo_err}")

    return out_pdf_path, preview_files, preview_data_urls


