# File: core\ocr_motoru.py
import cv2
import numpy as np
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch
from core.model_paths import resolve_model_path


class TrOCREngine:
    """PDF icindeki gorsellerden metin okumak icin TrOCR tabanli motor."""

    MODEL_MAP = {
        "heavy": ("microsoft/trocr-base-printed", "ocr_heavy"),
        "light": ("microsoft/trocr-small-printed", "ocr_light"),
    }

    def __init__(self, mode: str = "heavy"):
        # GPU varsa CUDA'yi kullan
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Sistem] OCR motoru basliyor... Cihaz: {self.device}")

        model_name, alias = self.MODEL_MAP.get(mode, self.MODEL_MAP["heavy"])
        model_path = resolve_model_path(model_name, alias)

        # Onceden egitilmis TrOCR modellerini yukle
        print(f"[Sistem] TrOCR modeli yukleniyor... ({model_path})")
        self.processor = TrOCRProcessor.from_pretrained(model_path, use_fast=False)
        self.model = VisionEncoderDecoderModel.from_pretrained(
            model_path
        ).to(self.device)

        print("[Sistem] OCR motoru hazir!")

    def satir_bul_ve_kes(self, pil_image):
        """OpenCV ile metin satirlarini tespit eder ve parcalara ayirir."""

        img = np.array(pil_image)
        img = img[:, :, ::-1].copy()  # RGB -> BGR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Gurultu azaltma ve ikili goruntuye cevirme
        blur = cv2.GaussianBlur(gray, (7, 7), 0)
        thresh = cv2.threshold(
            blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )[1]

        # Metin satirlarini birlestirmek icin genisletme
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 5))
        dilate = cv2.dilate(thresh, kernel, iterations=1)

        # Konturlari bul
        cnts = cv2.findContours(
            dilate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]

        # Yukaridan asagiya sirala
        cnts = sorted(cnts, key=lambda x: cv2.boundingRect(x)[1])

        satir_resimleri = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if h > 15 and w > 15:  # Gurultuyu ele
                roi = img[y : y + h, x : x + w]
                roi_pil = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
                satir_resimleri.append(roi_pil)

        return satir_resimleri

    def ocr_yap(self, image):
        """
        Tek bir gorseli alir:
        - Satirlara boler
        - Her satiri OCR ile okur
        """

        try:
            satirlar = self.satir_bul_ve_kes(image)
            full_text = ""

            # Satir bulunamazsa tum gorseli dene
            if not satirlar:
                satirlar = [image]

            for satir_img in satirlar:
                pixel_values = self.processor(
                    images=satir_img, return_tensors="pt"
                ).pixel_values.to(self.device)

                generated_ids = self.model.generate(pixel_values)
                generated_text = self.processor.batch_decode(
                    generated_ids, skip_special_tokens=True
                )[0]

                full_text += generated_text + " "

            return full_text

        except Exception as e:
            print(f"OCR hatasi: {e}")
            return ""
