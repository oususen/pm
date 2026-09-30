<template>
  <div class="ocr-reader">
    <header class="page-header">
      <div>
        <h2>OCR・文書読取</h2>
        <p>画像やPDF内の日本語・英数字を文字にします。ファイルは保存せず、社外へも送信しません。</p>
      </div>
      <span class="status" :class="{ unavailable: selectedEngineStatus && !selectedEngineStatus.available }">{{ selectedEngineStatus?.available ? '利用可能' : 'OCR確認中・利用不可' }}</span>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <section class="reader-card">
      <div class="file-row">
        <label>読取方式
          <select v-model="engine">
            <option v-for="(label, key) in ocrStatus?.engines" :key="key" :value="key" :disabled="!ocrStatus?.[key]?.available">{{ label }}{{ ocrStatus?.[key]?.available ? '' : '（準備中）' }}</option>
          </select>
        </label>
        <label class="select-file">ファイルを選択<input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp" capture="environment" @change="selectImage" /></label>
        <span>{{ selectedFile?.name || 'PDF（全ページ）、PNG、JPG、WEBP、BMP（15MBまで）' }}</span>
        <button :disabled="!selectedFile || recognizing || !selectedEngineStatus?.available" @click="recognize">{{ recognizing ? '文字認識中…' : '文字を認識' }}</button>
      </div>
      <p class="help">{{ selectedEngineStatus?.message || '読取エンジンを確認しています。' }} PDFは全ページを処理します。枚数が多いと時間がかかります。OCRはこのPC内で実行されます。</p>
    </section>

    <section v-if="selectedFile" class="result-grid">
      <article class="panel"><h3>{{ isPdf ? 'PDFプレビュー' : '画像' }}</h3><iframe v-if="isPdf && previewUrl" :src="previewUrl" :title="selectedFile.name" class="pdf-preview" /><img v-else-if="previewUrl" :src="previewUrl" :alt="selectedFile.name" /></article>
      <article class="panel"><div class="panel-title"><h3>認識結果 <small v-if="result">{{ result.engine_label }}・{{ result.character_count }}文字{{ isPdf ? `・${result.completed_page_count}/${result.page_count}ページ処理` : '' }}</small></h3><button v-if="result?.text" class="copy" @click="copyText">コピー</button></div><textarea readonly :value="result?.text || (recognizing ? '文字を認識しています…' : '「文字を認識」を押すと結果が表示されます。')" /></article>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '@/api/client'

const ocrStatus = ref(null)
const engine = ref('paddle')
const selectedFile = ref(null)
const previewUrl = ref('')
const result = ref(null)
const recognizing = ref(false)
const error = ref('')
const selectedEngineStatus = computed(() => ocrStatus.value?.[engine.value])
const isPdf = computed(() => selectedFile.value?.name?.toLowerCase().endsWith('.pdf'))

const loadStatus = async () => {
  try {
    ocrStatus.value = (await api.ocr.status()).data
    if (!ocrStatus.value?.paddle?.available) engine.value = 'tesseract'
  } catch (requestError) { error.value = requestError.response?.data?.detail || 'OCRの状態を確認できません。' }
}
const selectImage = (event) => {
  const file = event.target.files?.[0] || null
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  selectedFile.value = file
  previewUrl.value = file ? URL.createObjectURL(file) : ''
  result.value = null
  error.value = ''
}
const recognize = async () => {
  const form = new FormData()
  form.append('image', selectedFile.value)
  form.append('engine', engine.value)
  recognizing.value = true
  error.value = ''
  try { result.value = (await api.ocr.recognize(form)).data } catch (requestError) { error.value = requestError.response?.data?.detail || '文字認識に失敗しました。' } finally { recognizing.value = false }
}
const copyText = async () => {
  try { await navigator.clipboard.writeText(result.value.text) } catch { error.value = 'コピーできませんでした。認識結果を選択してコピーしてください。' }
}
onMounted(loadStatus)
onBeforeUnmount(() => { if (previewUrl.value) URL.revokeObjectURL(previewUrl.value) })
</script>

<style scoped>
.pdf-preview{display:block;width:100%;height:520px;margin-top:10px;border:0}
.ocr-reader{max-width:1100px;margin:0 auto;padding:14px 16px;color:#334155}.page-header{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.page-header h2{margin:0;font-size:19px}.page-header p,.help{margin:5px 0 0;color:#64748b;font-size:12px;line-height:1.6}.status{padding:6px 9px;border-radius:6px;background:#e8f8f2;color:#157567;font-size:12px;white-space:nowrap}.status.unavailable,.error{background:#fff1ee;color:#ae5146}.reader-card,.panel{margin-top:14px;padding:13px;border:1px solid #dce8e5;border-radius:10px;background:#fff}.file-row,.panel-title{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.file-row>label:not(.select-file){display:flex;align-items:center;gap:5px;font-size:12px}.file-row select,.select-file,button{border:1px solid #93bfb5;border-radius:6px;padding:6px 10px;background:#fff;color:#147a6d;font-size:12px;cursor:pointer}.select-file input{display:none}button:disabled{opacity:.45;cursor:not-allowed}.file-row span{font-size:12px;color:#64748b}.result-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px}.panel h3{margin:0;font-size:14px;color:#176b60}.panel h3 small{font-weight:400;color:#64748b}.panel img{display:block;max-width:100%;max-height:520px;margin-top:10px;object-fit:contain}.panel-title{justify-content:space-between}.copy{padding:4px 8px}.panel textarea{box-sizing:border-box;width:100%;height:420px;margin-top:10px;padding:9px;border:1px solid #dce8e5;border-radius:6px;resize:vertical;font:13px/1.65 Consolas,'Meiryo',sans-serif;color:#334155;background:#f8fbfa}.error{margin:12px 0 0;padding:8px 10px;border-radius:6px;font-size:12px}@media(max-width:760px){.page-header{display:grid}.result-grid{grid-template-columns:1fr}.panel textarea{height:260px}}
</style>
