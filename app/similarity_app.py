# File: app\similarity_app.py
import os
import shutil
import itertools
import json
from datetime import datetime
from core.document_processor import DocumentProcessor
from core.analiz_motoru import BenzerlikMotoru
from db.database import ResultDatabase


class SimilarityApp:
    """PDF benzerlik analizinin ana is mantigini yonetir."""

    def __init__(self, model_mode: str = "heavy", ocr_mode: str = "heavy"):
        self.klasor = "dokumanlar"
        os.makedirs(self.klasor, exist_ok=True)

        self.model_mode = model_mode
        self.ocr_mode = ocr_mode

        self.config = self._load_config()
        self.doc_processor = DocumentProcessor(ocr_mode=self.ocr_mode)
        self.motor = BenzerlikMotoru(
            mode=self.model_mode,
            lexical_w=self.config["lexical_weight"],
            semantic_w=self.config["semantic_weight"],
        )
        self.db = ResultDatabase()

        self.veriler = {}
        self.yeni_yukleme_var = False
        self.log_cb = None
        self.detaylar = {}

    def set_options(self, model_mode: str, ocr_mode: str, log_cb=None):
        """Model/OCR modlarini gunceller."""
        self.model_mode = model_mode
        self.ocr_mode = ocr_mode
        self.log_cb = log_cb

        self.config = self._load_config()
        self.doc_processor = DocumentProcessor(ocr_mode=self.ocr_mode)
        self.motor = BenzerlikMotoru(
            mode=self.model_mode,
            lexical_w=self.config["lexical_weight"],
            semantic_w=self.config["semantic_weight"],
        )
        self.config = self._load_config()

    def klasor_yukle(self, klasor_yolu):
        self.veriler = {}
        yuklenen_var = False

        for f in os.listdir(klasor_yolu):
            uzanti = f.lower().rsplit(".", 1)
            ext = f".{uzanti[1]}" if len(uzanti) == 2 else ""
            if ext not in {".pdf", ".docx", ".txt"}:
                continue

            kaynak = os.path.join(klasor_yolu, f)
            hedef = os.path.join(self.klasor, f)

            if not os.path.exists(hedef):
                shutil.copy(kaynak, hedef)

            # Analizde kullanabilmek icin dosya var olsa da metni yukle
            try:
                metin = self.doc_processor.metin_cikar(hedef)
                if metin:
                    self.veriler[f] = metin
                    yuklenen_var = True
                    self._safe_log(f"Yuklendi: {f}")
                else:
                    self._safe_log(f"[Uyari] Metin cikarilamadi: {f}")
            except Exception as e:
                self._safe_log(f"[Hata] {f} islenemedi: {e}")

        self.yeni_yukleme_var = yuklenen_var

    def analiz_et(self, progress_cb=None, cancel_cb=None):
        if not self.yeni_yukleme_var or len(self.veriler) < 2:
            return [], None

        sonuclar = []
        run_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.db.save_run_meta(run_time, self.model_mode, self.ocr_mode)
        dokumanlar = list(self.veriler.keys())
        toplam = len(dokumanlar) * (len(dokumanlar) - 1) // 2
        adim = 0

        for d1, d2 in itertools.combinations(dokumanlar, 2):
            if cancel_cb and cancel_cb():
                self._safe_log("Analiz iptal edildi.")
                break

            try:
                lex, sem, final = self.motor.hesapla(
                    self.veriler[d1], self.veriler[d2]
                )
            except Exception as e:
                self._safe_log(f"[Hata] Hesaplama basarisiz: {d1} <> {d2} :: {e}")
                continue

            durum = "TEMIZ"
            if final > self.config["kopya_esik"]:
                durum = "KOPYA"
            elif final > self.config["supheli_esik"]:
                durum = "SUPHELI"

            s = {
                "dosya1": d1,
                "dosya2": d2,
                "lex": round(lex, 2),
                "sem": round(sem, 2),
                "final": round(final, 2),
                "durum": durum,
                "tarih": run_time,
            }

            try:
                self.db.save_result(s, tarih=run_time)
            except Exception as e:
                self._safe_log(f"[Hata] DB kaydi basarisiz: {d1} <> {d2} :: {e}")
                continue

            sonuclar.append(s)
            try:
                detay_list = self._chunk_evidence(
                    self.veriler[d1], self.veriler[d2]
                )
                self.detaylar[(d1, d2, run_time)] = detay_list
                self.db.save_evidences(run_time, d1, d2, detay_list)
            except Exception as e:
                self._safe_log(f"[Hata] Detay hesaplanamadi: {d1} <> {d2} :: {e}")

            adim += 1

            if progress_cb:
                progress_cb(adim, toplam)
            self._safe_log(f"Karsilastirildi: {d1} <> {d2} (final={final:.2f})")

        # Aynı veriyi tekrar analiz etmemek icin yukleme bayragi sifirlanir
        self.yeni_yukleme_var = False
        return sonuclar, run_time

    def get_detay(self, d1, d2, tarih):
        key = (d1, d2, tarih)
        alt_key = (d2, d1, tarih)
        if key in self.detaylar:
            return self.detaylar[key]
        if alt_key in self.detaylar:
            return self.detaylar[alt_key]
        return self.db.get_evidences(tarih, d1, d2)

    def _chunk_evidence(self, metin1, metin2, top_n=3):
        """Cümle/paragraph bazinda en benzer parcalari getirir."""
        parcalar1 = self._metni_parcalara_bol(metin1)
        parcalar2 = self._metni_parcalara_bol(metin2)

        if not parcalar1 or not parcalar2:
            return []

        try:
            tfidf_texts = parcalar1 + parcalar2
            vectorizer = BenzerlikMotoru._shared_vectorizer()
            tfidf = vectorizer.fit_transform(tfidf_texts)
            m1 = tfidf[0 : len(parcalar1)]
            m2 = tfidf[len(parcalar1) :]
            sim_matrix = m1 * m2.T  # sparse

            # En yuksek top_n skor
            best = []
            for i, row in enumerate(sim_matrix):
                row = row.toarray().ravel()
                if not row.size:
                    continue
                j = row.argmax()
                skor = row[j]
                best.append((skor, parcalar1[i], parcalar2[j]))

            best = sorted(best, key=lambda x: x[0], reverse=True)[:top_n]
            return [
                {"p1": p1, "p2": p2, "score": float(skor)}
                for skor, p1, p2 in best
                if skor > 0
            ]
        except Exception:
            return []

    def _metni_parcalara_bol(self, metin, min_len=30):
        raw_parts = []
        for sep in [".", "\n", ";"]:
            if sep in metin:
                raw_parts = metin.split(sep)
                break
        if not raw_parts:
            raw_parts = [metin]
        parts = []
        for p in raw_parts:
            t = " ".join(p.split()).strip()
            if len(t) >= min_len:
                parts.append(t)
        return parts

    def _safe_log(self, msg: str):
        if self.log_cb:
            try:
                self.log_cb(msg)
            except Exception:
                pass

    def _load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # Basit dogrulama
            if cfg.get("lexical_weight", 0.7) + cfg.get("semantic_weight", 0.3) <= 0:
                raise ValueError("Agirlik toplami sifir/negatif olamaz.")
            return {
                "lexical_weight": float(cfg.get("lexical_weight", 0.7)),
                "semantic_weight": float(cfg.get("semantic_weight", 0.3)),
                "kopya_esik": float(cfg.get("kopya_esik", 0.75)),
                "supheli_esik": float(cfg.get("supheli_esik", 0.5)),
            }
        except Exception:
            return {
                "lexical_weight": 0.7,
                "semantic_weight": 0.3,
                "kopya_esik": 0.75,
                "supheli_esik": 0.5,
            }
