# File: db\database.py
import sqlite3
import threading
from datetime import datetime
import os
import csv


class ResultDatabase:
    def __init__(self):
        os.makedirs("db", exist_ok=True)
        # check_same_thread=False: GUI thread + worker thread paylasimi icin
        self.conn = sqlite3.connect("db/results.db", check_same_thread=False)
        self.lock = threading.Lock()
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        with self.lock:
            self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dosya1 TEXT,
            dosya2 TEXT,
            lex REAL,
            sem REAL,
            final REAL,
            durum TEXT,
            tarih TEXT
        )
        """)
            self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            tarih TEXT PRIMARY KEY,
            model TEXT,
            ocr_mode TEXT
        )
        """)
            self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            dosya1 TEXT,
            dosya2 TEXT,
            parca1 TEXT,
            parca2 TEXT,
            skor REAL
        )
        """)
            self.conn.commit()

    def save_result(self, r: dict, tarih: str | None = None):
        """Sonucu kaydeder. Tarih verilirse tum satirlar ayni zaman damgasi alir."""
        zaman = tarih or datetime.now().strftime("%Y-%m-%d %H:%M")
        with self.lock:
            self.cursor.execute("""
        INSERT INTO results
        (dosya1, dosya2, lex, sem, final, durum, tarih)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            r["dosya1"],
            r["dosya2"],
            r["lex"],
            r["sem"],
            r["final"],
            r["durum"],
            zaman
        ))
            self.conn.commit()

    def sonuc_kaydet(self, r: dict):
        """Turkce isimle geriye donuk uyumluluk saglar."""
        self.save_result(r)

    def save_run_meta(self, tarih: str, model: str, ocr_mode: str):
        """Run bilgisini saklar; ayni tarih varsa gunceller."""
        with self.lock:
            self.cursor.execute("""
        INSERT INTO runs (tarih, model, ocr_mode)
        VALUES (?, ?, ?)
        ON CONFLICT(tarih) DO UPDATE SET model=excluded.model, ocr_mode=excluded.ocr_mode
        """, (tarih, model, ocr_mode))
            self.conn.commit()

    def get_all_results(self):
        with self.lock:
            self.cursor.execute("""
        SELECT dosya1, dosya2, lex, sem, final, durum, tarih
        FROM results
        ORDER BY id DESC
        """)
            return self.cursor.fetchall()

    def get_runs(self):
        """Farkli calisma zamanlarini listeler (en yeni once)."""
        with self.lock:
            self.cursor.execute("""
        SELECT tarih, model, ocr_mode FROM runs
        ORDER BY tarih DESC
        """)
            rows = self.cursor.fetchall()
        # Eski kayitlar icin fallback
        if not rows:
            with self.lock:
                self.cursor.execute("""
            SELECT DISTINCT tarih FROM results ORDER BY tarih DESC
            """)
                rows = [(r[0], None, None, None) for r in self.cursor.fetchall()]
        return rows

    def get_results_by_tarih(self, tarih):
        """Belirli bir zaman damgasi icin sonuclari dondurur."""
        with self.lock:
            self.cursor.execute("""
        SELECT dosya1, dosya2, lex, sem, final, durum, tarih
        FROM results
        WHERE tarih = ?
        ORDER BY id DESC
        """, (tarih,))
            return self.cursor.fetchall()

    def export_csv(self, file_path: str):
        """Tum sonuclari CSV olarak disari aktarir."""
        rows = self.get_all_results()
        header = ["dosya1", "dosya2", "lex", "sem", "final", "durum", "tarih"]
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)

    def clear_all(self):
        """Tum kayitlari siler."""
        with self.lock:
            self.cursor.execute("DELETE FROM results")
            self.cursor.execute("DELETE FROM runs")
            self.cursor.execute("DELETE FROM evidences")
            self.conn.commit()

    def save_evidences(self, tarih: str, dosya1: str, dosya2: str, evidences: list[dict]):
        """Parca bazli kanitlari toplu kaydeder."""
        if not evidences:
            return
        rows = [
            (tarih, dosya1, dosya2, e["p1"], e["p2"], e["score"])
            for e in evidences
        ]
        with self.lock:
            self.cursor.executemany("""
            INSERT INTO evidences (tarih, dosya1, dosya2, parca1, parca2, skor)
            VALUES (?, ?, ?, ?, ?, ?)
            """, rows)
            self.conn.commit()

    def get_evidences(self, tarih: str, dosya1: str, dosya2: str):
        """Belirli run ve dosya cifti icin kanitlari getirir."""
        with self.lock:
            self.cursor.execute("""
            SELECT parca1, parca2, skor FROM evidences
            WHERE tarih = ? AND (
                (dosya1 = ? AND dosya2 = ?) OR (dosya1 = ? AND dosya2 = ?)
            )
            """, (tarih, dosya1, dosya2, dosya2, dosya1))
            rows = self.cursor.fetchall()
        return [
            {"p1": r[0], "p2": r[1], "score": r[2]}
            for r in rows
        ]
