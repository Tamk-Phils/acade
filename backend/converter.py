"""
Document Converter: Converts DOCX to PDF using LibreOffice headless
and generates high-resolution page previews with pdftoppm.
"""
import os
import shutil
import subprocess
import glob
from typing import List, Dict, Any

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
