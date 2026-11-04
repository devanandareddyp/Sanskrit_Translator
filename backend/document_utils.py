"""PDF extraction and OCR helpers."""
import io
import os
import shutil
from pathlib import Path
from typing import List, Dict

import fitz
import pytesseract
from PIL import Image, ImageOps

TESSERACT_EXE = os.getenv(
    "TESSERACT_EXE",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "40"))


def configure_tesseract() -> bool:
    if shutil.which("tesseract"):
        return True
    if Path(TESSERACT_EXE).is_file():
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
        return True
    return False


def ocr_languages():
    try:
        available = set(pytesseract.get_languages(config=""))
    except Exception:
        return None

    if "san" in available and "eng" in available:
        return "san+eng"
    if "san" in available:
        return "san"
    if "eng" in available:
        return "eng"
    return None


def extract_image_text(image: Image.Image) -> str:
    if not configure_tesseract():
        raise RuntimeError(
            "Tesseract OCR was not found. Install Tesseract for Windows "
            "and set TESSERACT_EXE if needed."
        )
    languages = ocr_languages()
    if not languages:
        raise RuntimeError(
            "No OCR language data was found. Install san.traineddata for "
            "Sanskrit OCR (eng.traineddata is a fallback only)."
        )

    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageOps.grayscale(image)
    return pytesseract.image_to_string(
        image, lang=languages, config="--psm 3"
    ).strip()


def extract_pdf_pages(pdf_bytes: bytes, force_ocr: bool = False) -> List[Dict]:
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError("Could not open this PDF file.") from exc

    output = []
    try:
        if document.page_count > MAX_PDF_PAGES:
            raise ValueError(
                f"PDF has {document.page_count} pages. The limit is "
                f"{MAX_PDF_PAGES}; split the PDF and try again."
            )

        for page_index, page in enumerate(document, start=1):
            text = "" if force_ocr else page.get_text("text").strip()
            method = "PDF text"

            if force_ocr or len(text) < 20:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                text = extract_image_text(image)
                method = "OCR"

            output.append({
                "page": page_index,
                "method": method,
                "text": text,
            })
    finally:
        document.close()

    return output
