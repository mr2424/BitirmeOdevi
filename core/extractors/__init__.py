# File: core\extractors\__init__.py
from core.extractors.base import BaseExtractor
from core.extractors.pdf_extractor import PdfExtractor
from core.extractors.docx_extractor import DocxExtractor
from core.extractors.txt_extractor import TxtExtractor

__all__ = [
    "BaseExtractor",
    "PdfExtractor",
    "DocxExtractor",
    "TxtExtractor",
]
