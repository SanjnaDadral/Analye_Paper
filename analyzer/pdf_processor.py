import logging
import os
import re
import time
from typing import Dict, List
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

PDF_MAX_PAGES = int(os.getenv("PDF_MAX_PAGES", "30"))
PDF_PREFER_FAST = os.getenv("PDF_PREFER_FAST", "True").lower() == "true"
MIN_TEXT_CHARS_FOR_FAST_OK = 80


def _count_embedded_images_pypdf(reader, pages_to_read: int) -> int:
    n = 0
    for i in range(min(len(reader.pages), pages_to_read)):
        try:
            page = reader.pages[i]
            resources = page.get("/Resources")
            if not resources:
                continue

            xobjects = resources.get("/XObject")
            if not xobjects:
                continue

            for obj in xobjects.values():
                try:
                    if obj.get("/Subtype") == "/Image":
                        n += 1
                except:
                    continue
        except:
            continue
    return n


class PDFProcessor:
    def __init__(self):
        try:
            import pdfplumber
            self._pdfplumber_available = True
        except ImportError:
            self._pdfplumber_available = False

        try:
            import pypdf
            self._pypdf_available = True
        except ImportError:
            self._pypdf_available = False

    # =========================
    # MAIN ENTRY
    # =========================
    def extract_text(self, pdf_file) -> Dict[str, any]:
        try:
            if PDF_PREFER_FAST and self._pypdf_available:
                fast = self._extract_with_pypdf(pdf_file)

                if fast["success"] and len(fast["text"].strip()) > MIN_TEXT_CHARS_FOR_FAST_OK:
                    return fast

                if self._pdfplumber_available:
                    return self._extract_with_pdfplumber(pdf_file)

                return fast

            if self._pdfplumber_available:
                return self._extract_with_pdfplumber(pdf_file)

            return self._extract_with_pypdf(pdf_file)

        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return {"success": False, "error": str(e), "text": "", "pages": 0}

    # =========================
    # PDFPLUMBER (ACCURATE)
    # =========================
    def _extract_with_pdfplumber(self, pdf_file) -> Dict[str, any]:
        import pdfplumber

        try:
            pdf_file.seek(0)

            text_parts = []
            embedded_img = 0

            with pdfplumber.open(pdf_file) as pdf:
                page_count = len(pdf.pages)
                pages_to_read = min(page_count, PDF_MAX_PAGES)

                for page in pdf.pages[:pages_to_read]:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

                    try:
                        embedded_img += len(page.images or [])
                    except:
                        pass

                metadata = self._extract_metadata_pdfplumber(pdf)

            return {
                "success": True,
                "text": "\n\n".join(text_parts),
                "pages": page_count,
                "pages_extracted": pages_to_read,
                "embedded_image_objects": embedded_img,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"pdfplumber error: {e}")
            return {"success": False, "error": str(e), "text": "", "pages": 0}

    # =========================
    # PYPDF (FAST)
    # =========================
    def _extract_with_pypdf(self, pdf_file) -> Dict[str, any]:
        from pypdf import PdfReader

        try:
            pdf_file.seek(0)

            reader = PdfReader(pdf_file)
            page_count = len(reader.pages)
            pages_to_read = min(page_count, PDF_MAX_PAGES)

            text_parts = []

            for page in reader.pages[:pages_to_read]:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            metadata = {}
            if reader.metadata:
                metadata = {
                    "title": reader.metadata.get("/Title", ""),
                    "author": reader.metadata.get("/Author", ""),
                }

            return {
                "success": True,
                "text": "\n\n".join(text_parts),
                "pages": page_count,
                "pages_extracted": pages_to_read,
                "embedded_image_objects": _count_embedded_images_pypdf(reader, pages_to_read),
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"pypdf error: {e}")
            return {"success": False, "error": str(e), "text": "", "pages": 0}

    # =========================
    # METADATA
    # =========================
    def _extract_metadata_pdfplumber(self, pdf):
        try:
            return {
                "title": pdf.metadata.get("Title", ""),
                "author": pdf.metadata.get("Author", ""),
            }
        except:
            return {}

    # =========================
    # TITLE DETECTION
    # =========================
    def extract_title_from_pdf(self, text: str) -> str:
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        for line in lines[:15]:
            if 10 < len(line) < 200:
                return line

        return "Untitled Document"


# =========================
# SINGLETON
# =========================
_pdf_processor = None


def get_pdf_processor():
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor()
    return _pdf_processor