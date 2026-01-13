# File: core\extractors\base.py
class BaseExtractor:
    """Ortak arayuz: uzanti kontrolu ve metin cikarma."""

    extensions = set()

    def destekler_mi(self, dosya_yolu: str) -> bool:
        return any(dosya_yolu.lower().endswith(ext) for ext in self.extensions)

    def metin_cikar(self, dosya_yolu: str) -> str:
        raise NotImplementedError
