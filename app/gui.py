# File: app\gui.py
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from app.similarity_app import SimilarityApp
from db.database import ResultDatabase


class SimilarityGUI:
    """Masaustu arayuz."""

    def __init__(self):
        self.app = SimilarityApp()
        self.db = ResultDatabase()
        self._queue = queue.Queue()
        self._running = False
        self._cancel_event = threading.Event()
        self.run_records = []

        self.root = tk.Tk()
        self.root.title("Benzerlik Analiz Sistemi")
        self.root.geometry("900x500")

        self._ui()
        self._load_runs_initial()
        # Varsayilan ayarlarla motorlari hazirla
        self.app.set_options(self.model_var.get(), self.ocr_var.get(), log_cb=self._log)
        self._load_config_to_ui()

    def _ui(self):
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, pady=5)

        tk.Button(
            top,
            text="PDF/DOCX/TXT Klasor Yukle",
            command=self.klasor_yukle,
            width=25,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            top,
            text="Analizi Baslat",
            command=self.analiz,
            width=25,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            top,
            text="Iptal",
            command=self.cancel,
            width=10,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            top,
            text="CSV'ye Aktar",
            command=self.export_csv,
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            top,
            text="Temizle (DB)",
            command=self.clear_db,
            width=12,
        ).pack(side=tk.LEFT, padx=5)

        opts = tk.Frame(self.root)
        opts.pack(fill=tk.X, padx=5)

        tk.Label(opts, text="Semantik Model:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value="heavy")
        ttk.Combobox(
            opts,
            textvariable=self.model_var,
            values=["heavy", "light"],
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(opts, text="OCR:").pack(side=tk.LEFT)
        self.ocr_var = tk.StringVar(value="heavy")
        ttk.Combobox(
            opts,
            textvariable=self.ocr_var,
            values=["heavy", "light", "off"],
            width=7,
            state="readonly",
        ).pack(side=tk.LEFT, padx=(0, 10))

        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        # Sol: calisma listesi (tarih-saat)
        sol = tk.Frame(main, width=180)
        sol.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(sol, text="Calisma Gecmisi").pack(anchor="w", padx=5, pady=2)

        self.run_list = tk.Listbox(sol, exportselection=False)
        self.run_list.pack(fill=tk.Y, expand=True, padx=5, pady=2)
        self.run_list.bind("<<ListboxSelect>>", self._run_selected)

        # Sag: sonuc tablosu
        sag = tk.Frame(main)
        sag.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tree_frame = tk.Frame(sag)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("dosya1", "dosya2", "lex", "sem", "final", "durum", "tarih"),
            show="headings",
        )

        for c in self.tree["columns"]:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=120)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.bind("<Double-1>", self._show_detail)

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=5, pady=3)

        self.progress = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 8))

        self.status_var = tk.StringVar(value="Hazir")
        tk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        tk.Label(log_frame, text="Log").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=6, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        cfg_frame = tk.Frame(self.root)
        cfg_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(cfg_frame, text="Kopya Esik").grid(row=0, column=0, sticky="w")
        tk.Label(cfg_frame, text="Supheli Esik").grid(row=0, column=1, sticky="w")
        tk.Label(cfg_frame, text="Lexical Weight").grid(row=0, column=2, sticky="w")
        tk.Label(cfg_frame, text="Semantic Weight").grid(row=0, column=3, sticky="w")

        self.kopya_esik = tk.DoubleVar()
        self.supheli_esik = tk.DoubleVar()
        self.lex_w = tk.DoubleVar()
        self.sem_w = tk.DoubleVar()

        tk.Entry(cfg_frame, textvariable=self.kopya_esik, width=8).grid(row=1, column=0, padx=4)
        tk.Entry(cfg_frame, textvariable=self.supheli_esik, width=8).grid(row=1, column=1, padx=4)
        tk.Entry(cfg_frame, textvariable=self.lex_w, width=8).grid(row=1, column=2, padx=4)
        tk.Entry(cfg_frame, textvariable=self.sem_w, width=8).grid(row=1, column=3, padx=4)
        tk.Button(cfg_frame, text="Kaydet", command=self.save_config).grid(row=1, column=4, padx=8)
        cfg_frame.grid_columnconfigure(0, weight=1)
        cfg_frame.grid_columnconfigure(1, weight=1)
        cfg_frame.grid_columnconfigure(2, weight=1)
        cfg_frame.grid_columnconfigure(3, weight=1)

    def _load_runs_initial(self):
        runs = self.db.get_runs()
        self._populate_runs(runs)
        if runs:
            self._select_run(0)

    def _populate_runs(self, runs):
        self.run_list.delete(0, tk.END)
        self.run_records = runs
        for r in runs:
            tarih, model, ocr_mode = r
            display = f"{tarih} [{model}/{ocr_mode}]"
            self.run_list.insert(tk.END, display)

    def klasor_yukle(self):
        yol = filedialog.askdirectory()
        if yol:
            self.app.klasor_yukle(yol)
            messagebox.showinfo("Bilgi", "PDF'ler yuklendi.")

    def analiz(self):
        if self._running:
            return

        def worker():
            model_mode = self.model_var.get()
            ocr_mode = self.ocr_var.get()
            self.app.set_options(model_mode=model_mode, ocr_mode=ocr_mode, log_cb=self._log)

            sonuclar, run_time = self.app.analiz_et(
                progress_cb=self._progress_cb,
                cancel_cb=self._cancel_event.is_set,
            )
            self._queue.put(("done", sonuclar, run_time))

        self._set_running(True)
        self.progress["value"] = 0
        self.progress["maximum"] = 1
        self.status_var.set("Analiz basliyor...")
        self._cancel_event.clear()

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(100, self._poll_queue)

    def _progress_cb(self, adim, toplam):
        self._queue.put(("progress", adim, toplam))

    def _poll_queue(self):
        while not self._queue.empty():
            item = self._queue.get()
            if item[0] == "progress":
                _, adim, toplam = item
                self.progress["maximum"] = toplam
                self.progress["value"] = adim
                self.status_var.set(f"Ilerleme: {adim}/{toplam}")
            elif item[0] == "done":
                _, sonuclar, run_time = item
                self._on_analysis_done(sonuclar, run_time)

        if self._running:
            self.root.after(100, self._poll_queue)

    def _on_analysis_done(self, sonuclar, run_time):
        self._set_running(False)

        if not sonuclar:
            messagebox.showwarning(
                "Uyari", "Analiz icin once yeni bir klasor yukleyin ve en az iki dosya oldugundan emin olun."
            )
            self.status_var.set("Hazir")
            self.progress["value"] = 0
            return

        # Run listesine yeni meta ile ekle
        mevcut_tarihler = [r[0] for r in self.run_records]
        if run_time not in mevcut_tarihler:
            yeni = (run_time, self.model_var.get(), self.ocr_var.get())
            self.run_records.insert(0, yeni)
            self._populate_runs(self.run_records)
            self.run_list.selection_clear(0, tk.END)
            self.run_list.selection_set(0)

        self.tree.delete(*self.tree.get_children())
        for s in sonuclar:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    s["dosya1"],
                    s["dosya2"],
                    s["lex"],
                    s["sem"],
                    s["final"],
                    s["durum"],
                    s["tarih"],
                ),
            )

        self.status_var.set(f"Tamamlandi: {len(sonuclar)} karsilastirma")
        self.progress["value"] = self.progress["maximum"]

    def cancel(self):
        if self._running:
            self._cancel_event.set()
            self.status_var.set("Iptal ediliyor...")

    def _set_running(self, val: bool):
        self._running = val
        state = tk.DISABLED if val else tk.NORMAL
        for child in self.root.winfo_children():
            if isinstance(child, tk.Frame):
                for btn in child.winfo_children():
                    if isinstance(btn, tk.Button):
                        # Iptal butonu analiz surecinde aktif kalsin
                        if btn["text"] == "Iptal":
                            btn.configure(state=tk.NORMAL)
                        else:
                            btn.configure(state=state)

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All Files", "*.*")],
            title="Sonuclari CSV olarak kaydet",
        )
        if not path:
            return
        try:
            self.db.export_csv(path)
            messagebox.showinfo("Bilgi", "Sonuclar CSV olarak kaydedildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"CSV kaydedilemedi: {e}")

    def clear_db(self):
        if not messagebox.askyesno("Onay", "Tum kayitlari silmek istiyor musunuz?"):
            return
        self.db.clear_all()
        self.tree.delete(*self.tree.get_children())
        self._populate_runs([])
        self.status_var.set("Kayitlar temizlendi")
        self.progress["value"] = 0

    def _log(self, msg: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def save_config(self):
        try:
            kopya = float(self.kopya_esik.get())
            supheli = float(self.supheli_esik.get())
            lex = float(self.lex_w.get())
            sem = float(self.sem_w.get())
            cfg = {
                "kopya_esik": kopya,
                "supheli_esik": supheli,
                "lexical_weight": lex,
                "semantic_weight": sem,
            }
            import json
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            # Config guncellendikten sonra motorlari yeniden kur
            self.app.set_options(self.model_var.get(), self.ocr_var.get(), log_cb=self._log)
            self.status_var.set("Ayarlar kaydedildi")
        except Exception as e:
            messagebox.showerror("Hata", f"Ayar kaydedilemedi: {e}")

    def _load_config_to_ui(self):
        try:
            import json
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.kopya_esik.set(cfg.get("kopya_esik", 0.75))
            self.supheli_esik.set(cfg.get("supheli_esik", 0.5))
            self.lex_w.set(cfg.get("lexical_weight", 0.7))
            self.sem_w.set(cfg.get("semantic_weight", 0.3))
        except Exception:
            # Varsayilanlar
            self.kopya_esik.set(0.75)
            self.supheli_esik.set(0.5)
            self.lex_w.set(0.7)
            self.sem_w.set(0.3)

    def _run_selected(self, event):
        if not self.run_list.curselection():
            return
        idx = self.run_list.curselection()[0]
        self._select_run(idx)

    def _select_run(self, idx):
        tarih = self.run_records[idx][0]
        self.run_list.selection_clear(0, tk.END)
        self.run_list.selection_set(idx)

        results = self.db.get_results_by_tarih(tarih)
        self.tree.delete(*self.tree.get_children())
        for r in results:
            self.tree.insert("", tk.END, values=r)

    def _show_detail(self, event):
        item = self.tree.selection()
        if not item:
            return
        vals = self.tree.item(item[0], "values")
        if len(vals) < 2:
            return
        d1, d2, tarih = vals[0], vals[1], vals[6]
        detaylar = self.app.get_detay(d1, d2, tarih)
        if not detaylar:
            messagebox.showinfo("Bilgi", "Bu eslesme icin detay bulunamadi.")
            return

        top = tk.Toplevel(self.root)
        top.title(f"Detay: {d1} <> {d2}")
        wrap = tk.Frame(top)
        wrap.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(wrap, text="Parca 1", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(wrap, text="Parca 2", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=1, sticky="w")
        tk.Label(wrap, text="Skor", font=("TkDefaultFont", 10, "bold")).grid(row=0, column=2, sticky="w", padx=(8, 0))

        for idx, d in enumerate(detaylar, start=1):
            skor_label = tk.Label(wrap, text=f"{d['score']:.2f}")
            skor_label.grid(row=idx, column=2, sticky="n", padx=(8, 0))

            t1 = tk.Text(wrap, wrap="word", height=6, width=50)
            t1.insert("1.0", d["p1"])
            t1.configure(state=tk.DISABLED)
            t1.grid(row=idx, column=0, sticky="nsew", padx=(0, 4), pady=2)

            t2 = tk.Text(wrap, wrap="word", height=6, width=50)
            t2.insert("1.0", d["p2"])
            t2.configure(state=tk.DISABLED)
            t2.grid(row=idx, column=1, sticky="nsew", padx=(0, 4), pady=2)

        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_columnconfigure(1, weight=1)
        wrap.grid_columnconfigure(2, weight=0)

        tk.Button(top, text="Kapat", command=top.destroy).pack(pady=5)

    def run(self):
        self.root.mainloop()
