const ocr = [
  {
    path: '/ocr',
    name: 'OCRReader',
    component: () => import('@/views/ocr/OCRReader.vue'),
    meta: { pageTitle: 'OCR・文書読取', resource: 'ai' },
  },
]

export default ocr
