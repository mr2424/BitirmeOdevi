# File: core\analiz_motoru.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from core.model_paths import resolve_model_path


class BenzerlikMotoru:
    """Metinler arasindaki lexical ve semantik benzerligi hesaplar."""

    MODEL_MAP = {
        "heavy": ("paraphrase-multilingual-MiniLM-L12-v2", "semantic_heavy"),
        "light": ("distiluse-base-multilingual-cased-v1", "semantic_light"),
    }

    def __init__(self, mode: str = "heavy", lexical_w: float = 0.7, semantic_w: float = 0.3):
        model_name, alias = self.MODEL_MAP.get(mode, self.MODEL_MAP["heavy"])
        model_path = resolve_model_path(model_name, alias)
        print(f"[Sistem] Semantik yapay zeka modeli yukleniyor... ({model_path})")
        self.semantic_model = SentenceTransformer(model_path)
        self.lexical_w = lexical_w
        self.semantic_w = semantic_w
        print("[Sistem] Analiz motoru hazir!")

    def hesapla(self, metin1, metin2):
        """
        Iki metin icin lexical, semantik ve agirlikli final skorunu dondurur.
        """

        # Cok kisa metinler anlamsiz sonuc uretir
        if len(metin1) < 10 or len(metin2) < 10:
            return 0, 0, 0

        # ---------------- LEXICAL BENZERLIK ----------------
        try:
            vectorizer = TfidfVectorizer()
            tfidf = vectorizer.fit_transform([metin1, metin2])
            lexical_score = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        except Exception:
            lexical_score = 0.0

        # ---------------- SEMANTIC BENZERLIK ----------------
        try:
            emb1 = self.semantic_model.encode(metin1)
            emb2 = self.semantic_model.encode(metin2)
            semantic_score = float(
                np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            )
        except Exception:
            semantic_score = 0.0

        # ---------------- AGIRLIKLI SKOR ----------------
        final_score = (lexical_score * self.lexical_w) + (semantic_score * self.semantic_w)

        return lexical_score, semantic_score, final_score

    @staticmethod
    def _shared_vectorizer():
        """Chunk karsilastirmada paylasilan basit TF-IDF vectorizer."""
        return TfidfVectorizer()
