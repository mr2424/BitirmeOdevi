# File: core\extractors\pdf_extractor.py
import io
import fitz  # PyMuPDF
from PIL import Image
from core.extractors.base import BaseExtractor
from core.ocr_motoru import TrOCREngine


class PdfExtractor(BaseExtractor):
    extensions = {".pdf"}

    def __init__(self, ocr_mode: str = "heavy"):
        self._ocr_engine = None
        self.ocr_mode = ocr_mode

    @property
    def ocr_engine(self) -> TrOCREngine:
        # Lazy yukle (ilk PDF geldiginde)
        if self._ocr_engine is None:
            self._ocr_engine = TrOCREngine(mode=self.ocr_mode)
        return self._ocr_engine

    def metin_cikar(self, dosya_yolu: str) -> str:
        tam_metin = []
        print(f"--> Dosya isleniyor: {dosya_yolu}")

        with fitz.open(dosya_yolu) as doc:
            for sayfa_no, page in enumerate(doc, start=1):
                # Metin katmani
                text = page.get_text()
                tam_metin.append(text)

                # Gorsel katmani
                image_list = page.get_images(full=True)

                if image_list and self.ocr_mode != "off":
                    print(
                        f"    Sayfa {sayfa_no}: "
                        f"{len(image_list)} resim bulundu, OCR yapiliyor..."
                    )

                    for img in image_list:
                        try:
                            xref = img[0]
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]

                            pil_image = Image.open(
                                io.BytesIO(image_bytes)
                            ).convert("RGB")

                            # Kucuk ikon ve logolari ele
                            if pil_image.width > 100 and pil_image.height > 50:
                                ocr_sonuc = self.ocr_engine.ocr_yap(pil_image)
                                tam_metin.append(ocr_sonuc)

                        except Exception as e:
                            print(f"    Resim okuma hatasi: {e}")

        birlestirilmis = " ".join(tam_metin)
        return " ".join(birlestirilmis.split())
