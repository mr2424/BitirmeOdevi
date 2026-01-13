# File: core\extractors\docx_extractor.py
import zipfile
from core.extractors.base import BaseExtractor


class DocxExtractor(BaseExtractor):
    extensions = {".docx"}

    def metin_cikar(self, dosya_yolu: str) -> str:
        try:
            with zipfile.ZipFile(dosya_yolu) as docx:
                xml = docx.read("word/document.xml").decode("utf-8")
        except Exception as e:
            print(f"[Hata] DOCX okunamadi: {dosya_yolu} :: {e}")
            return ""

        # Basit tag temizleme; docx icindeki text nodelarini ayrıştır
        metin = []
        parca = []
        i = 0
        while i < len(xml):
            if xml[i] == "<":
                if parca:
                    metin.append("".join(parca))
                    parca = []
                j = xml.find(">", i)
                if j == -1:
                    break
                i = j + 1
            else:
                parca.append(xml[i])
                i += 1

        if parca:
            metin.append("".join(parca))

        metin_str = " ".join(metin)
        return " ".join(metin_str.split())
