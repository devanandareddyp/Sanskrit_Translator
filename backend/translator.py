
"""IndicTrans2 model loading and Sanskrit-to-English translation."""

import re
from functools import lru_cache
from typing import List

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from IndicTransToolkit import IndicProcessor

MODEL_NAME = "krpraveen/indictrans2-sanskrit-en-finetuned"
MAX_INPUT_TOKENS = 256


@lru_cache(maxsize=1)
def load_model():
    """Load the model only once per backend process."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
    )

    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
    )

    model.to(device)
    model.eval()

    processor = IndicProcessor(inference=True)
    return tokenizer, model, processor, device


def split_text(text: str, max_chars: int = 650) -> List[str]:
    """Split long text into manageable pieces without losing content."""
    text = text.replace("\r\n", "\n").strip()
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []

    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue

        sentences = re.split(r"(?<=[।॥.!?])\s+", paragraph)
        current = ""

        for sentence in sentences:
            if len(sentence) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(
                    sentence[i:i + max_chars]
                    for i in range(0, len(sentence), max_chars)
                )
            elif current and len(current) + len(sentence) + 1 > max_chars:
                chunks.append(current)
                current = sentence
            else:
                current = f"{current} {sentence}".strip()

        if current:
            chunks.append(current)

    return chunks


def translate(text: str) -> str:
    """Translate Sanskrit text into English."""
    if not text or not text.strip():
        return ""

    tokenizer, model, processor, device = load_model()
    chunks = split_text(text)
    results = []

    for start in range(0, len(chunks), 4):
        batch = chunks[start:start + 4]

        model_inputs = processor.preprocess_batch(
            batch,
            src_lang="san_Deva",
            tgt_lang="eng_Latn",
        )

        encoded = tokenizer(
            model_inputs,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=MAX_INPUT_TOKENS,
        )
        encoded = {
            key: value.to(device)
            for key, value in encoded.items()
        }

        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                num_beams=5,
                max_length=256,
            )

        decoded = tokenizer.batch_decode(
            generated,
            skip_special_tokens=True,
        )

        decoded = processor.postprocess_batch(
            decoded,
            lang="eng_Latn",
        )
        results.extend(decoded)

    return "\n\n".join(results)


def model_status():
    """Return model state without forcing a download/load."""
    return {
        "model_name": MODEL_NAME,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "loaded": load_model.cache_info().currsize > 0,
        "indic_processor_available": True,
    }
