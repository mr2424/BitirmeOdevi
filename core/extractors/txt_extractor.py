# File: core\extractors\txt_extractor.py
from core.extractors.base import BaseExtractor


class TxtExtractor(BaseExtractor):
    extensions = {".txt"}

    def metin_cikar(self, dosya_yolu: str) -> str:
        try:
            with open(dosya_yolu, "r", encoding="utf-8") as f:
                return " ".join(f.read().split())
        except UnicodeDecodeError:
            with open(dosya_yolu, "r", encoding="latin-1") as f:
                return " ".join(f.read().split())
        except Exception as e:
            print(f"[Hata] TXT okunamadi: {dosya_yolu} :: {e}")
            return ""
