"""
Document Converter: Converts DOCX to PDF using LibreOffice headless
and generates high-resolution page previews with pdftoppm.
"""
import os
import shutil
import subprocess
import glob
from typing import List, Dict, Any
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
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")
        
        if not os.path.exists(pdf_path):
            # Look for any pdf generated
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
    return page_files[:max_pages]


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
                else:
                    lines.append(word)
        if current_line:
            lines.append(" ".join(current_line))
    return lines


def generate_pure_python_previews(
    docx_path: str,
    preview_dir: str,
    dpi: int = 120,
    max_pages: int = 100,
    metadata: Optional[Any] = None
) -> List[str]:
    """
    High-fidelity pure-Python preview generator using Pillow.
    Renders official Senate A4 pages (Cover, Title, Preliminaries, Chapters)
    directly without requiring LibreOffice or pdftoppm. Works reliably in serverless environments.
    """
    if os.path.exists(preview_dir):
        shutil.rmtree(preview_dir, ignore_errors=True)
    os.makedirs(preview_dir, exist_ok=True)

    try:
        doc = docx.Document(docx_path)
    except Exception as e:
        print(f"[AcadFormat Converter] Error reading docx for preview: {e}")
        return []

    # Partition paragraphs into logical pages by page break runs and pageBreakBefore
    pages_paragraphs: List[List[Any]] = []
    curr_page: List[Any] = []
    for p in doc.paragraphs:
        p_has_break_before = bool(p.paragraph_format.page_break_before or p._p.xpath('.//w:pPr/w:pageBreakBefore'))
        if p_has_break_before and curr_page:
            pages_paragraphs.append(curr_page)
            curr_page = []

        curr_page.append(p)
        has_break = any("w:br" in r._r.xml and "page" in r._r.xml for r in p.runs)
        if has_break:
            pages_paragraphs.append(curr_page)
            curr_page = []
    if curr_page:
        pages_paragraphs.append(curr_page)

    if max_pages and max_pages > 0:
        pages_paragraphs = pages_paragraphs[:max_pages]

    if not pages_paragraphs:
        return []

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
    f_title = _get_font(16, True)
    f_h1 = _get_font(15, True)
    f_h2 = _get_font(13, True)
    f_footer = _get_font(12, False)

    body_start_page = 8

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

    for idx, p_list in enumerate(pages_paragraphs):
        is_cover_or_title = (idx < 2)

        if idx > 0 and curr_y > 100:
            finish_page(current_img, page_counter)
            page_counter += 1
            if max_pages and page_counter > max_pages:
                break
            current_img, draw, curr_y = start_new_page()

        if is_cover_or_title and logo_img:
            current_img.paste(logo_img, ((W - logo_img.width) // 2, 60), mask=logo_img)
            curr_y = 175

        for p in p_list:
            txt = p.text.strip()
            if not txt:
                curr_y += 10
                continue

            p_style = getattr(p.style, "name", "Normal")
            is_heading = "Heading" in p_style or (txt.isupper() and len(txt) < 80)
            p_font = f_h1 if ("Heading 1" in p_style or (txt.isupper() and len(txt) < 50)) else (f_h2 if "Heading" in p_style else f_normal)

            # Boxed title check on cover/title page
            is_boxed_title = is_cover_or_title and (
                ("ORCHESTRATOR" in txt.upper() or "DESIGN" in txt.upper() or "STUDY" in txt.upper() or "SYSTEM" in txt.upper() or "INVESTIGATION" in txt.upper() or len(txt) > 25)
                and not any(k in txt.upper() for k in ["THE UNIVERSITY", "L'UNIVERSITE", "COLLEGE", "FACULTY", "DEPARTMENT", "DISSERTATION", "SUBMITTED", "PRESENTED", "SUPERVISED", "SUPERVISOR", "REGISTRATION", "DATE", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"])
            )

            if is_boxed_title:
                t_lines = _wrap_text(txt.upper(), f_title, max_text_w - 40, draw)
                b_h = max(80, len(t_lines) * 26 + 30)
                if curr_y + b_h > 1280 and curr_y > 150:
                    finish_page(current_img, page_counter)
                    page_counter += 1
                    current_img, draw, curr_y = start_new_page()
                draw.rectangle([(left_margin, curr_y), (right_margin, curr_y + b_h)], outline="black", width=2)
                ty = curr_y + 16
                for tl in t_lines:
                    draw.text((W // 2, ty), tl, font=f_title, fill="black", anchor="mm")
                    ty += 26
                curr_y += b_h + 30
                continue

            wrapped = _wrap_text(txt, p_font, max_text_w, draw)
            line_h = 24 if is_heading else 20
            p_needed_h = len(wrapped) * line_h + (12 if is_heading else 8)

            if curr_y + p_needed_h > 1280 and curr_y > 150:
                finish_page(current_img, page_counter)
                page_counter += 1
                if max_pages and page_counter > max_pages:
                    break
                current_img, draw, curr_y = start_new_page()

            align = "center" if (is_cover_or_title or (txt.isupper() and len(txt) < 60)) else "left"
            for line in wrapped:
                if align == "center":
                    draw.text((W // 2, curr_y), line, font=p_font, fill="black", anchor="ma")
                else:
                    draw.text((left_margin, curr_y), line, font=p_font, fill="#1E293B")
                curr_y += line_h
            curr_y += 10 if is_heading else 6

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
        valid_imgs[0].save(output_pdf_path, "PDF", resolution=100.0, save_all=True, append_images=valid_imgs[1:])
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
    1. Attempts headless LibreOffice + pdftoppm if available.
    2. Seamlessly falls back to pure-Python preview generator when LibreOffice is not present.
    Always returns (pdf_path, preview_page_paths, preview_data_urls).
    """
    out_pdf_path = None
    preview_pages: List[str] = []
    preview_data_urls: List[str] = []

    if is_libreoffice_available() and is_pdftoppm_available():
        try:
            out_pdf_path = convert_docx_to_pdf(docx_path, output_dir)
            if out_pdf_path and os.path.exists(out_pdf_path):
                preview_pages = generate_page_previews(out_pdf_path, preview_dir, dpi=dpi, max_pages=max_pages)
                if preview_pages:
                    preview_data_urls = [image_file_to_base64_data_url(p) for p in preview_pages]
                    return out_pdf_path, preview_pages, preview_data_urls
        except Exception as lo_err:
            print(f"[AcadFormat Converter] LibreOffice conversion skipped: {lo_err}")

    # Fallback to pure-Python generator
    try:
        preview_pages = generate_pure_python_previews(docx_path, preview_dir, dpi=dpi, max_pages=max_pages, metadata=metadata)
        if preview_pages:
            preview_data_urls = [image_file_to_base64_data_url(p) for p in preview_pages]
            # Assemble multi-page PDF from previews so PDF export is always guaranteed
            candidate_pdf = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(docx_path))[0]}.pdf")
            if images_to_pdf(preview_pages, candidate_pdf):
                out_pdf_path = candidate_pdf
    except Exception as py_err:
        print(f"[AcadFormat Converter] Pure-Python preview generator error: {py_err}")

    return out_pdf_path, preview_pages, preview_data_urls


