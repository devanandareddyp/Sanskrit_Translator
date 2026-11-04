"""FastAPI API for the Sanskrit-to-English translator."""
import io
import logging
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

from document_utils import extract_image_text, extract_pdf_pages
from translator import translate, model_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sanskrit-to-English Translator API",
    description="Local API for text, PDF, and image translation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=30000)


@app.get("/")
def root():
    return {"message": "Sanskrit Translator API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", **model_status()}


@app.post("/translate")
def translate_endpoint(request: TranslateRequest):
    try:
        result = translate(request.text)
        return {"translation": result}
    except Exception as exc:
        logger.exception("Text translation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {type(exc).__name__}: {exc}",
        )


async def read_upload(file: UploadFile) -> bytes:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum upload size is 15 MB.",
        )
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return content


@app.post("/translate/pdf")
async def translate_pdf(
    file: UploadFile = File(...),
    force_ocr: bool = Form(False),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")
    content = await read_upload(file)

    try:
        pages = extract_pdf_pages(content, force_ocr=force_ocr)
        translated_pages = []
        for page in pages:
            translated = translate(page["text"]) if page["text"].strip() else ""
            translated_pages.append({
                "page": page["page"],
                "method": page["method"],
                "source_text": page["text"],
                "translation": translated,
            })
        combined = "\n\n".join(
            f"PAGE {p['page']}\n{p['translation'] or '[No readable text detected.]'}"
            for p in translated_pages
        )
        return {"pages": translated_pages, "translation": combined}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("PDF translation failed")
        raise HTTPException(
            status_code=500,
            detail=f"PDF translation failed: {type(exc).__name__}: {exc}",
        )


@app.post("/translate/image")
async def translate_image(file: UploadFile = File(...)):
    content = await read_upload(file)
    try:
        image = Image.open(io.BytesIO(content))
        extracted = extract_image_text(image)
        translated = translate(extracted) if extracted.strip() else ""
        return {"extracted_text": extracted, "translation": translated}
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Could not read this image.")
    except Exception as exc:
        logger.exception("Image translation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Image translation failed: {type(exc).__name__}: {exc}",
        )
