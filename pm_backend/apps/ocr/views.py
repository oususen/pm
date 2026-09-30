"""OCR・文書読取API。画像は処理後に保存せず削除する。"""
import os
from pathlib import Path
from tempfile import TemporaryDirectory, mkstemp

import fitz

from rest_framework import parsers, status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from ocr.services import ENGINE_CHOICES, IMAGE_SUFFIXES, OCRRecognitionError, all_status, extract_image_tables, extract_image_text, extract_images_tables, extract_images_text, paddle_status, paddle_table_status, status


PDF_SUFFIX = '.pdf'


class OCRStatusView(APIView):
    def get(self, request):
        return Response(all_status())


class OCRRecognitionView(APIView):
    """画像またはPDFを一時ファイルで認識し、文字列または編集用表を返す。"""
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        image = request.FILES.get('image')
        engine = request.data.get('engine', 'tesseract')
        mode = request.data.get('mode', 'text')
        if not image:
            return Response({'detail': '認識する画像を選択してください。'}, status=http_status.HTTP_400_BAD_REQUEST)
        suffix = Path(image.name).suffix.lower()
        if suffix not in IMAGE_SUFFIXES and suffix != PDF_SUFFIX:
            return Response({'detail': 'PDF、PNG、JPG、WEBP、BMP形式のファイルを選択してください。'}, status=http_status.HTTP_400_BAD_REQUEST)
        if image.size > 15 * 1024 * 1024:
            return Response({'detail': '認識する画像は15MBまでです。'}, status=http_status.HTTP_400_BAD_REQUEST)
        if engine not in ENGINE_CHOICES:
            return Response({'detail': '選択できないOCRエンジンです。'}, status=http_status.HTTP_400_BAD_REQUEST)
        if mode not in {'text', 'table'}:
            return Response({'detail': '選択できない読み取り方式です。'}, status=http_status.HTTP_400_BAD_REQUEST)
        if mode == 'table' and engine != 'paddle':
            return Response({'detail': '表認識にはPaddleOCRを選択してください。'}, status=http_status.HTTP_400_BAD_REQUEST)
        current_status = paddle_table_status() if mode == 'table' else (paddle_status() if engine == 'paddle' else status())
        if not current_status['available']:
            return Response({'detail': current_status['message']}, status=http_status.HTTP_503_SERVICE_UNAVAILABLE)
        descriptor, temporary_path = mkstemp(suffix=suffix)
        try:
            # WindowsでもTesseractが開けるよう、一時ファイルを閉じてから渡す。
            with os.fdopen(descriptor, 'wb') as temporary:
                for chunk in image.chunks():
                    temporary.write(chunk)
            if suffix == PDF_SUFFIX:
                try:
                    with fitz.open(temporary_path) as document:
                        if document.needs_pass:
                            return Response({'detail': 'パスワード保護されたPDFは読み取れません。'}, status=http_status.HTTP_400_BAD_REQUEST)
                        if len(document) == 0:
                            return Response({'detail': 'ページがないPDFです。'}, status=http_status.HTTP_400_BAD_REQUEST)
                        with TemporaryDirectory(prefix='pm-ocr-pdf-') as page_directory:
                            page_paths = []
                            for page_number, page in enumerate(document, start=1):
                                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                                page_path = Path(page_directory) / f'page-{page_number:02}.png'
                                pixmap.save(str(page_path))
                                page_paths.append(page_path)
                            if mode == 'table':
                                page_tables = extract_images_tables(page_paths)
                                page_texts = None
                                extracted_text = ''
                            else:
                                page_texts = extract_images_text(page_paths, engine=engine)
                                page_tables = None
                                extracted_text = '\n\n'.join(
                                    f'【{page_number}ページ】\n{text}'
                                    for page_number, text in enumerate(page_texts, start=1)
                                )
                except OCRRecognitionError:
                    raise
                except Exception:
                    return Response({'detail': 'PDFを読み込めませんでした。破損していないPDFか確認してください。'}, status=http_status.HTTP_400_BAD_REQUEST)
            else:
                if mode == 'table':
                    page_texts = None
                    page_tables = [extract_image_tables(temporary_path)]
                    extracted_text = ''
                else:
                    page_texts = None
                    page_tables = None
                    extracted_text = extract_image_text(temporary_path, engine=engine)
        except OCRRecognitionError as exc:
            return Response({'detail': str(exc)}, status=http_status.HTTP_503_SERVICE_UNAVAILABLE)
        finally:
            Path(temporary_path).unlink(missing_ok=True)
        processed_page_count = (
            len(page_tables) if page_tables is not None
            else len(page_texts) if page_texts is not None
            else 1
        )
        return Response({
            'file_name': image.name,
            'engine': engine,
            'engine_label': ENGINE_CHOICES[engine],
            'text': extracted_text,
            'character_count': len(extracted_text),
            'page_count': processed_page_count,
            'completed_page_count': processed_page_count,
            'mode': mode,
            'tables': [
                {'page_number': page_number, 'table_number': table_number, 'rows': rows}
                for page_number, tables in enumerate(page_tables or [], start=1)
                for table_number, rows in enumerate(tables, start=1)
            ] if mode == 'table' else [],
            'table_count': sum(len(tables) for tables in page_tables or []) if mode == 'table' else 0,
            'message': '全ページを開発PC内で処理しました。元ファイルは保存・外部送信していません。',
        })
