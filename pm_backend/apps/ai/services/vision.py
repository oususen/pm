"""添付画像をOpenRouterの画像対応モデルへ安全に渡すための準備処理。"""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from ai.config.models import AIKnowledgeDocument
from ai.services.knowledge_retriever import IMAGE_SUFFIXES


MAX_IMAGE_DIMENSION = 1600
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_PDF_PAGES = 3
PDF_SUFFIXES = {'.pdf'}


def _jpeg_data_url(image):
    """Pillow画像を、外部API送信用の縮小JPEGへ変換する。"""
    image = ImageOps.exif_transpose(image).convert('RGB')
    image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
    output = BytesIO()
    image.save(output, format='JPEG', quality=85, optimize=True)
    encoded = output.getvalue()
    if len(encoded) > MAX_IMAGE_BYTES:
        raise ValueError('添付画像が大きすぎるため、4MB以下の画像を添付してください。')
    return f"data:image/jpeg;base64,{base64.b64encode(encoded).decode('ascii')}"


def _pdf_page_data_urls(path):
    """PDF先頭ページを画像化する。変換結果はメモリ上だけで保持する。"""
    import fitz

    try:
        with fitz.open(path) as pdf:
            if pdf.page_count < 1:
                raise ValueError('PDFにページがありません。')
            data_urls = []
            for page_index in range(min(pdf.page_count, MAX_PDF_PAGES)):
                pixmap = pdf.load_page(page_index).get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                with Image.open(BytesIO(pixmap.tobytes('png'))) as image:
                    data_urls.append(_jpeg_data_url(image))
            return data_urls, pdf.page_count
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError('添付PDFを画像として読み込めませんでした。') from exc


def selected_visual_attachment(document_ids):
    """明示的に添付された画像またはPDFを、外部API送信用画像へ変換する。

    PDFは先頭3ページまでを画像化する。元ファイルは変更・複製保存せず、
    送信用画像だけをメモリ上で生成する。
    """
    if not document_ids:
        return None
    document = next(
        (
            # 明示添付は利用者自身の今回限りの指定なので、ナレッジ一覧の有効/無効には従わない。
            item for item in AIKnowledgeDocument.objects.filter(id__in=document_ids)
            if Path(item.file.name).suffix.lower() in IMAGE_SUFFIXES | PDF_SUFFIXES
        ),
        None,
    )
    if not document:
        return None
    try:
        suffix = Path(document.file.name).suffix.lower()
        if suffix in PDF_SUFFIXES:
            data_urls, total_pages = _pdf_page_data_urls(document.file.path)
            return {
                'name': document.name,
                'kind': 'PDF',
                'data_urls': data_urls,
                'total_pages': total_pages,
            }
        with Image.open(document.file.path) as source:
            data_url = _jpeg_data_url(source)
    except (FileNotFoundError, OSError, UnidentifiedImageError, ValueError) as exc:
        raise ValueError(f'添付資料「{document.name}」を画像として読み込めませんでした。') from exc
    return {
        'name': document.name,
        'kind': '画像',
        'data_urls': [data_url],
        'total_pages': 1,
    }
