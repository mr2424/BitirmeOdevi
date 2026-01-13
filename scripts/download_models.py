# File: scripts\download_models.py
from pathlib import Path

from sentence_transformers import SentenceTransformer
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


SEMANTIC_MODELS = {
    "semantic_heavy": "paraphrase-multilingual-MiniLM-L12-v2",
    "semantic_light": "distiluse-base-multilingual-cased-v1",
}

OCR_MODELS = {
    "ocr_heavy": "microsoft/trocr-base-printed",
    "ocr_light": "microsoft/trocr-small-printed",
}


def _models_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "models"


def download_semantic(alias: str, model_name: str):
    dest = _models_dir() / alias
    dest.mkdir(parents=True, exist_ok=True)
    print(f"[Download] Semantic: {model_name} -> {dest}")
    model = SentenceTransformer(model_name)
    model.save(str(dest))


def download_ocr(alias: str, model_name: str):
    dest = _models_dir() / alias
    dest.mkdir(parents=True, exist_ok=True)
    print(f"[Download] OCR: {model_name} -> {dest}")
    processor = TrOCRProcessor.from_pretrained(model_name, use_fast=False)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    processor.save_pretrained(dest)
    model.save_pretrained(dest)


def main():
    _models_dir().mkdir(parents=True, exist_ok=True)

    for alias, model_name in SEMANTIC_MODELS.items():
        download_semantic(alias, model_name)

    for alias, model_name in OCR_MODELS.items():
        download_ocr(alias, model_name)

    print("[OK] Tum modeller indirildi.")


if __name__ == "__main__":
    main()
