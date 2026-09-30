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
        <label>出力方式
          <select v-model="mode" @change="result = null">
            <option value="text">文字を抽出</option>
            <option value="table" :disabled="!ocrStatus?.table_recognition?.available">表として読み取る{{ ocrStatus?.table_recognition?.available ? '' : '（開発PCで利用不可）' }}</option>
          </select>
        </label>
        <label v-if="mode === 'table'">表認識
          <select v-model="tableMode" @change="result = null">
            <option value="fast">高速（罫線表）</option>
            <option value="accurate">高精度（複雑な表）</option>
          </select>
        </label>
        <label v-if="mode === 'text'">OCRエンジン
          <select v-model="engine">
            <option v-for="(label, key) in ocrStatus?.engines" :key="key" :value="key" :disabled="!ocrStatus?.[key]?.available">{{ label }}{{ ocrStatus?.[key]?.available ? '' : '（準備中）' }}</option>
          </select>
        </label>
        <label class="resident-option"><input v-model="keepAlive" type="checkbox" :disabled="recognizing" @change="changeKeepAlive" /> Paddleモデルを常駐</label>
        <span v-if="workerRunning" class="worker-status">常駐中</span>
        <label class="select-file">ファイルを選択<input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp" capture="environment" @change="selectImage" /></label>
        <span>{{ selectedFile?.name || 'PDF（全ページ）、PNG、JPG、WEBP、BMP（15MBまで）' }}</span>
        <button :disabled="!selectedFile || recognizing || !selectedEngineStatus?.available" @click="recognize">{{ recognizing ? '認識中…' : mode === 'table' ? '表を読み取る' : '文字を認識' }}</button>
      </div>
      <p class="help">{{ selectedEngineStatus?.message || '読取エンジンを確認しています。' }} {{ modeHelp }} 常駐をONにすると2回目以降が速くなり、OFFにするとメモリを解放します。ファイルと表認識モデルは開発PC内で扱い、本番PCへ転送しません。</p>
    </section>

    <section v-if="selectedFile" class="result-grid">
      <article class="panel"><h3>{{ isPdf ? 'PDFプレビュー' : '画像' }}</h3><iframe v-if="isPdf && previewUrl" :src="previewUrl" :title="selectedFile.name" class="pdf-preview" /><img v-else-if="previewUrl" :src="previewUrl" :alt="selectedFile.name" /></article>
      <article class="panel">
        <div class="panel-title"><h3>認識結果 <small v-if="result">{{ mode === 'table' ? `${result.table_count}表` : `${result.engine_label}・${result.character_count}文字` }}{{ isPdf ? `・${result.completed_page_count}/${result.page_count}ページ処理` : '' }}</small></h3><button v-if="hasCopyableResult" class="copy" @click="copyResult">{{ mode === 'table' ? '表をコピー' : 'コピー' }}</button></div>
        <template v-if="mode === 'table' && result">
          <p v-if="!result.tables?.length" class="empty-tables">表を検出できませんでした。通常の「文字を抽出」でもお試しください。</p>
          <section v-for="table in result.tables" :key="`${table.page_number}-${table.table_number}`" class="recognized-table">
            <h4>{{ isPdf ? `${table.page_number}ページ・` : '' }}表{{ table.table_number }} <small>セルは直接編集できます</small></h4>
            <div class="table-scroll"><table><tbody><tr v-for="(row, rowIndex) in table.rows" :key="rowIndex"><td v-for="(cell, columnIndex) in row" :key="columnIndex"><input v-model="table.rows[rowIndex][columnIndex]" :style="{ width: `${cellInputSize(cell)}ch` }" :aria-label="`表${table.table_number} 行${rowIndex + 1} 列${columnIndex + 1}`" /></td></tr></tbody></table></div>
          </section>
        </template>
        <textarea v-else readonly :value="result?.text || (recognizing ? '認識しています…' : mode === 'table' ? '「表を読み取る」を押すと結果が表示されます。' : '「文字を認識」を押すと結果が表示されます。')" />
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '@/api/client'

const ocrStatus = ref(null)
const engine = ref('paddle')
const mode = ref('text')
const tableMode = ref('accurate')
const keepAlive = ref(localStorage.getItem('pm-ocr-keep-alive') === 'true')
const workerRunning = ref(false)
const selectedFile = ref(null)
const previewUrl = ref('')
const result = ref(null)
const recognizing = ref(false)
const error = ref('')
const selectedEngineStatus = computed(() => mode.value === 'table' ? ocrStatus.value?.table_recognition : ocrStatus.value?.[engine.value])
const modeHelp = computed(() => {
  if (mode.value !== 'table') return 'PDFは全ページを処理します。枚数が多いと時間がかかります。'
  return tableMode.value === 'fast'
    ? '高速モードは罫線付き表向けです。結合セルや罫線のない表は高精度モードをご利用ください。'
    : '高精度モードは複雑な表向けですが、処理時間とメモリ使用量が増えます。'
})
const isPdf = computed(() => selectedFile.value?.name?.toLowerCase().endsWith('.pdf'))
const hasCopyableResult = computed(() => mode.value === 'table' ? Boolean(result.value?.tables?.length) : Boolean(result.value?.text))
const cellInputSize = (cell) => Math.min(48, Math.max(12, Array.from(String(cell ?? '')).length + 3))

const loadStatus = async () => {
  try {
    ocrStatus.value = (await api.ocr.status()).data
    workerRunning.value = Boolean(ocrStatus.value?.paddle_worker?.running)
    if (!ocrStatus.value?.paddle?.available) engine.value = 'tesseract'
  } catch (requestError) { error.value = requestError.response?.data?.detail || 'OCRの状態を確認できません。' }
}
const changeKeepAlive = async () => {
  localStorage.setItem('pm-ocr-keep-alive', String(keepAlive.value))
  if (keepAlive.value) return
  try {
    await api.ocr.stopWorker()
    workerRunning.value = false
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || 'PaddleOCRの常駐を停止できませんでした。'
  }
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
  form.append('engine', mode.value === 'table' ? 'paddle' : engine.value)
  form.append('mode', mode.value)
  form.append('table_mode', tableMode.value)
  form.append('keep_alive', String(keepAlive.value))
  recognizing.value = true
  error.value = ''
  try {
    result.value = (await api.ocr.recognize(form)).data
    workerRunning.value = keepAlive.value && (mode.value === 'table' || engine.value === 'paddle')
  } catch (requestError) {
    error.value = requestError.response?.data?.detail || '文字認識に失敗しました。'
  } finally { recognizing.value = false }
}
const copyResult = async () => {
  let text = result.value.text || ''
  if (mode.value === 'table') {
    text = result.value.tables.map((table) => {
      const title = isPdf.value ? `【${table.page_number}ページ・表${table.table_number}】\n` : `【表${table.table_number}】\n`
      return title + table.rows.map((row) => row.map((cell) => String(cell ?? '').replace(/[\t\r\n]+/g, ' ')).join('\t')).join('\n')
    }).join('\n\n')
  }
  try { await navigator.clipboard.writeText(text) } catch { error.value = 'コピーできませんでした。認識結果を選択してコピーしてください。' }
}
onMounted(loadStatus)
onBeforeUnmount(() => { if (previewUrl.value) URL.revokeObjectURL(previewUrl.value) })
</script>

<style scoped>
.pdf-preview{display:block;width:100%;height:520px;margin-top:10px;border:0}
.recognized-table{margin-top:12px}.recognized-table h4{margin:0 0 6px;font-size:12px;color:#176b60}.recognized-table h4 small,.empty-tables{font-size:11px;font-weight:400;color:#64748b}.table-scroll{max-width:100%;overflow:auto;border:1px solid #dce8e5;border-radius:6px}.recognized-table table{border-collapse:collapse;min-width:100%;font-size:12px}.recognized-table td{min-width:90px;padding:0;border:1px solid #dce8e5}.recognized-table input{box-sizing:border-box;width:100%;min-width:90px;padding:7px;border:0;background:transparent;color:#334155;font:inherit}.recognized-table input:focus{outline:2px solid #38a891;outline-offset:-2px}.empty-tables{margin:12px 0}
.ocr-reader{max-width:1100px;margin:0 auto;padding:14px 16px;color:#334155}.page-header{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.page-header h2{margin:0;font-size:19px}.page-header p,.help{margin:5px 0 0;color:#64748b;font-size:12px;line-height:1.6}.status{padding:6px 9px;border-radius:6px;background:#e8f8f2;color:#157567;font-size:12px;white-space:nowrap}.status.unavailable,.error{background:#fff1ee;color:#ae5146}.reader-card,.panel{margin-top:14px;padding:13px;border:1px solid #dce8e5;border-radius:10px;background:#fff}.file-row,.panel-title{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.file-row>label:not(.select-file){display:flex;align-items:center;gap:5px;font-size:12px}.resident-option{padding:5px 8px;border-radius:6px;background:#f2f8f6;color:#176b60}.resident-option input{accent-color:#178b79}.worker-status{padding:3px 7px;border-radius:10px;background:#e8f8f2;color:#157567!important}.file-row select,.select-file,button{border:1px solid #93bfb5;border-radius:6px;padding:6px 10px;background:#fff;color:#147a6d;font-size:12px;cursor:pointer}.select-file input{display:none}button:disabled{opacity:.45;cursor:not-allowed}.file-row span{font-size:12px;color:#64748b}.result-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px}.panel h3{margin:0;font-size:14px;color:#176b60}.panel h3 small{font-weight:400;color:#64748b}.panel img{display:block;max-width:100%;max-height:520px;margin-top:10px;object-fit:contain}.panel-title{justify-content:space-between}.copy{padding:4px 8px}.panel textarea{box-sizing:border-box;width:100%;height:420px;margin-top:10px;padding:9px;border:1px solid #dce8e5;border-radius:6px;resize:vertical;font:13px/1.65 Consolas,'Meiryo',sans-serif;color:#334155;background:#f8fbfa}.error{margin:12px 0 0;padding:8px 10px;border-radius:6px;font-size:12px}@media(max-width:760px){.page-header{display:grid}.result-grid{grid-template-columns:1fr}.panel textarea{height:260px}}
</style>
