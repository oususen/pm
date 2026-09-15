"""工程一体チェックシート用のフォント・台紙変換処理。"""
import io
import re
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageFont


FONT_CANDIDATES = {
    False: [
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\YuGothR.ttc",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    True: [
        r"C:\Windows\Fonts\meiryob.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\YuGothB.ttc",
        "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
        "/usr/share/fonts/truetype/takao-gothic/TakaoGothic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}


def safe_filename(value: str) -> str:
    value = str(value or "").strip()
    value = re.sub(r"[\\/:*?\"<>|]+", "_", value)
    return value or "untitled"


def _duplicate_uploaded_file(uploaded_file):
    uploaded_file.seek(0)
    data = uploaded_file.read()
    return ContentFile(data, name=uploaded_file.name), data


def _pdf_first_page_to_png(file_bytes: bytes, stem: str):
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF台紙を使うには PyMuPDF のインストールが必要です。") from exc

    document = fitz.open(stream=file_bytes, filetype="pdf")
    page = document.load_page(0)
    matrix = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    image_bytes = pix.tobytes("png")
    document.close()
    return ContentFile(image_bytes, name=f"{safe_filename(stem)}.png"), pix.width, pix.height


def _normalize_image(file_bytes: bytes, stem: str):
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=f"{safe_filename(stem)}.png"), image.width, image.height


def create_background_assets(uploaded_pdf=None, uploaded_image=None):
    if uploaded_pdf:
        duplicated_pdf, pdf_bytes = _duplicate_uploaded_file(uploaded_pdf)
        background_content, width, height = _pdf_first_page_to_png(pdf_bytes, Path(uploaded_pdf.name).stem)
        return {
            "source_type": "pdf",
            "source_pdf": duplicated_pdf,
            "background_image": background_content,
            "background_width": width,
            "background_height": height,
        }
    if uploaded_image:
        duplicated_image, image_bytes = _duplicate_uploaded_file(uploaded_image)
        background_content, width, height = _normalize_image(image_bytes, Path(uploaded_image.name).stem)
        return {
            "source_type": "image",
            "source_image": duplicated_image,
            "background_image": background_content,
            "background_width": width,
            "background_height": height,
        }
    raise ValueError("台紙PDFまたは台紙画像が必要です。")


def _find_font_path(bold=False):
    for candidate in FONT_CANDIDATES[bool(bold)]:
        if Path(candidate).exists():
            return candidate
    return None


def _font(size, bold=False):
    path = _find_font_path(bold=bold)
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()
