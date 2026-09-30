from django.urls import path

from ocr.views import OCRRecognitionView, OCRStatusView, OCRWorkerStopView


urlpatterns = [
    path('ocr/status/', OCRStatusView.as_view(), name='ocr-status'),
    path('ocr/recognize/', OCRRecognitionView.as_view(), name='ocr-recognize'),
    path('ocr/worker/stop/', OCRWorkerStopView.as_view(), name='ocr-worker-stop'),
]
