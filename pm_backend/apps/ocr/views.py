"""OCR・文書読取API。画像は処理後に保存せず削除する。"""
import os
from pathlib import Path
from tempfile import TemporaryDirectory, mkstemp

import fitz

from rest_framework import parsers, status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from ocr.services import ENGINE_CHOICES, IMAGE_SUFFIXES, OCRRecognitionError, all_status, extract_image_text, extract_images_text, paddle_status, status


PDF_SUFFIX = '.pdf'


class OCRStatusView(APIView):
    def get(self, request):
        return Response(all_status())


class OCRRecognitionView(APIView):
    """画像またはPDFを一時ファイルで認識し、文字列だけを返す。"""
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        image = request.FILES.get('image')
        engine = request.data.get('engine', 'tesseract')
        if not image:
            return Response({'detail': '認識する画像を選択してください。'}, status=http_status.HTTP_400_BAD_REQUEST)
        suffix = Path(image.name).suffix.lower()
        if suffix not in IMAGE_SUFFIXES and suffix != PDF_SUFFIX:
            return Response({'detail': 'PDF、PNG、JPG、WEBP、BMP形式のファイルを選択してください。'}, status=http_status.HTTP_400_BAD_REQUEST)
        if image.size > 15 * 1024 * 1024:
            return Response({'detail': '認識する画像は15MBまでです。'}, status=http_status.HTTP_400_BAD_REQUEST)
        if engine not in ENGINE_CHOICES:
            return Response({'detail': '選択できないOCRエンジンです。'}, status=http_status.HTTP_400_BAD_REQUEST)
        current_status = paddle_status() if engine == 'paddle' else status()
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
                            page_texts = extract_images_text(page_paths, engine=engine)
                            extracted_text = '\n\n'.join(
                                f'【{page_number}ページ】\n{text}'
                                for page_number, text in enumerate(page_texts, start=1)
                            )
                except OCRRecognitionError:
                    raise
                except Exception:
                    return Response({'detail': 'PDFを読み込めませんでした。破損していないPDFか確認してください。'}, status=http_status.HTTP_400_BAD_REQUEST)
            else:
                page_texts = None
                extracted_text = extract_image_text(temporary_path, engine=engine)
        except OCRRecognitionError as exc:
            return Response({'detail': str(exc)}, status=http_status.HTTP_503_SERVICE_UNAVAILABLE)
        finally:
            Path(temporary_path).unlink(missing_ok=True)
        return Response({
            'file_name': image.name,
            'engine': engine,
            'engine_label': ENGINE_CHOICES[engine],
            'text': extracted_text,
            'character_count': len(extracted_text),
            'page_count': len(page_texts) if page_texts is not None else 1,
            'completed_page_count': len(page_texts) if page_texts is not None else 1,
            'message': '全ページをローカルで処理しました。元ファイルは保存・外部送信していません。',
        })
