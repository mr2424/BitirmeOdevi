# File: core\document_processor.py
from core.extractors import PdfExtractor, DocxExtractor, TxtExtractor


class DocumentProcessor:
    """
    Tek arayuzle coklu format destegi sunan yonetici (Strategy).
    Kullanicidan bagimsiz olarak uygun extractor'a delege eder.
    """

    def __init__(self, ocr_mode: str = "heavy"):
        self.extractors = [
            PdfExtractor(ocr_mode=ocr_mode),
            DocxExtractor(),
            TxtExtractor(),
        ]

    def metin_cikar(self, dosya_yolu: str) -> str:
        for ex in self.extractors:
            if ex.destekler_mi(dosya_yolu):
                return ex.metin_cikar(dosya_yolu)

        print(f"[Uyari] Desteklenmeyen format: {dosya_yolu}")
        return ""
