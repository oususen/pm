<template>
  <div class="progress-pdf-compare">
    <div class="usage-guide">
      <div class="usage-guide-title">使い方</div>
      <div>1. ラインコードを入力します。</div>
      <div>2. 比較したい日付を選択します。</div>
      <div>3. 進度PDFを選択します。</div>
      <div>4. 「突合実行」を押して、一致・不一致・PDF独自・DB独自を確認します。</div>
      <div>5. 必要に応じて「Excel出力」で結果を保存します。</div>
    </div>

    <div class="controls">
      <label>ラインコード:
        <input v-model="lineCode" placeholder="000180" style="width:80px" />
      </label>
      <label>対象日:
        <input type="date" v-model="targetDate" />
      </label>
      <label>PDF:
        <input type="file" accept=".pdf" @change="onFileChange" />
      </label>
      <button @click="compare" :disabled="loading || !file || !targetDate">
        {{ loading ? '解析中...' : '突合実行' }}
      </button>
      <button v-if="result" @click="exportExcel" class="btn-excel">Excel出力</button>
      <button v-if="result && result.mismatch.length" @click="adjustProgress"
        :disabled="adjusting || selectedCount === 0" class="btn-adjust">
        {{ adjusting ? '調整中...' : `進度調整実行 (${selectedCount}件)` }}
      </button>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>
    <div v-if="adjustDone" class="adjust-notice">調整レコードを登録しました。進度は再計算されていません。反映するには進度再計算を実行してください。</div>

    <div v-if="result" class="result-area">
      <div class="summary-bar">
        <span class="badge info">対象日: {{ result.target_date }}</span>
        <span class="badge info">ライン: {{ result.line_name }} ({{ result.line_code }})</span>
        <span class="badge ok">一致: {{ result.summary.match }}</span>
        <span class="badge ng">不一致: {{ result.summary.mismatch }}</span>
        <span class="badge warn">PDF独自: {{ result.summary.pdf_only }}</span>
        <span class="badge warn">DB独自: {{ result.summary.db_only }}</span>
      </div>

      <div v-if="result.mismatch.length" class="section">
        <h3>不一致 ({{ result.mismatch.length }}件)</h3>
        <table class="compare-table">
          <thead>
            <tr>
              <th class="chk"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
              <th>PDF品番</th><th>DB品番</th><th>品名</th><th>工程</th>
              <th class="num">PDF進度</th><th class="num">DB進度</th><th class="num">差異</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in result.mismatch" :key="r.pdf_code" :class="diffClass(r.diff)">
              <td class="chk"><input type="checkbox" v-model="r.selected" /></td>
              <td>{{ r.pdf_code }}</td>
              <td>{{ r.db_code }}</td>
              <td>{{ r.product_name }}</td>
              <td>{{ r.process_code }}</td>
              <td class="num">{{ r.progress_pdf }}</td>
              <td class="num">{{ r.progress_db }}</td>
              <td class="num diff-cell">{{ r.diff > 0 ? '+' : '' }}{{ r.diff }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <details v-if="result.match.length" class="section">
        <summary>一致 ({{ result.match.length }}件)</summary>
        <table class="compare-table">
          <thead>
            <tr>
              <th>PDF品番</th><th>DB品番</th><th>品名</th><th>工程</th><th class="num">進度</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in result.match" :key="r.pdf_code">
              <td>{{ r.pdf_code }}</td>
              <td>{{ r.db_code }}</td>
              <td>{{ r.product_name }}</td>
              <td>{{ r.process_code }}</td>
              <td class="num">{{ r.progress_pdf }}</td>
            </tr>
          </tbody>
        </table>
      </details>

      <details v-if="result.pdf_only.length" class="section">
        <summary>PDF独自 ({{ result.pdf_only.length }}件)</summary>
        <table class="compare-table">
          <thead><tr><th>品番</th><th class="num">進度</th></tr></thead>
          <tbody>
            <tr v-for="r in result.pdf_only" :key="r.pdf_code">
              <td>{{ r.pdf_code }}</td><td class="num">{{ r.progress_pdf }}</td>
            </tr>
          </tbody>
        </table>
      </details>

      <details v-if="result.db_only.length" class="section">
        <summary>DB独自 ({{ result.db_only.length }}件)</summary>
        <table class="compare-table">
          <thead><tr><th>品番</th><th>品名</th><th>工程</th><th class="num">進度</th></tr></thead>
          <tbody>
            <tr v-for="r in result.db_only" :key="r.db_code">
              <td>{{ r.db_code }}</td><td>{{ r.product_name }}</td>
              <td>{{ r.process_code }}</td><td class="num">{{ r.progress_db }}</td>
            </tr>
          </tbody>
        </table>
      </details>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import ExcelJS from 'exceljs'
import api from '@/api/client'

const lineCode = ref('000180')
const targetDate = ref('')
const file = ref(null)
const loading = ref(false)
const adjusting = ref(false)
const adjustDone = ref(false)
const error = ref('')
const result = ref(null)

const selectedCount = computed(() => {
  if (!result.value) return 0
  return result.value.mismatch.filter(r => r.selected).length
})

const allSelected = computed(() => {
  if (!result.value || !result.value.mismatch.length) return false
  return result.value.mismatch.every(r => r.selected)
})

function toggleAll(e) {
  const val = e.target.checked
  result.value.mismatch.forEach(r => { r.selected = val })
}

async function adjustProgress() {
  const items = result.value.mismatch.filter(r => r.selected)
  if (!items.length) return

  const payload = items.map(r => ({
    db_code: r.db_code,
    process_code: r.process_code,
    diff: r.diff,
  }))

  adjusting.value = true
  error.value = ''
  try {
    const preRes = await api.progressPdfCompare.precheck(
      lineCode.value, result.value.target_date, payload
    )
    const ex = preRes.data
    let msg = `${items.length}件の進度調整レコードを登録します。`
    if (ex.existing_count > 0) {
      const details = ex.existing.map(e =>
        `  ${e.product_code} (${e.process_code}): 現在=${e.current_qty} → 新=${e.new_qty}  理由: ${e.current_reason}`
      ).join('\n')
      msg += `\n\n⚠ 既存の調整レコード ${ex.existing_count}件が上書きされます:\n${details}`
    }
    msg += '\n\nよろしいですか？'
    if (!confirm(msg)) { adjusting.value = false; return }

    const res = await api.progressPdfCompare.adjust(
      lineCode.value, result.value.target_date, payload
    )
    const resultMsg = []
    if (res.data.created) resultMsg.push(`新規: ${res.data.created}件`)
    if (res.data.updated) resultMsg.push(`更新: ${res.data.updated}件`)
    adjustDone.value = true
    alert(`進度調整完了\n${resultMsg.join(' / ')}\n\n※ 進度は再計算されていません。反映するには進度再計算を実行してください。`)
  } catch (e) {
    const data = e.response?.data
    if (data?.errors?.length) {
      error.value = data.errors.join('\n')
    } else {
      error.value = data?.detail || e.message
    }
  } finally {
    adjusting.value = false
  }
}

function onFileChange(e) {
  file.value = e.target.files[0] || null
}

async function compare() {
  if (!file.value || !targetDate.value) return
  loading.value = true
  error.value = ''
  result.value = null
  adjustDone.value = false
  try {
    const res = await api.progressPdfCompare.compare(
      file.value, lineCode.value, targetDate.value
    )
    const data = res.data
    data.mismatch.forEach(r => { r.selected = true })
    result.value = data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}

function diffClass(diff) {
  if (Math.abs(diff) >= 10) return 'diff-large'
  if (Math.abs(diff) >= 3) return 'diff-medium'
  return 'diff-small'
}

const HEADER_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF4472C4' } }
const HEADER_FONT = { bold: true, color: { argb: 'FFFFFFFF' }, size: 10 }
const THIN_BORDER = {
  top: { style: 'thin' }, bottom: { style: 'thin' },
  left: { style: 'thin' }, right: { style: 'thin' },
}
const RED_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFCDD2' } }
const YELLOW_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFF9C4' } }
const GREEN_FILL = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE8F5E9' } }

function styleHeader(row) {
  row.eachCell(cell => {
    cell.fill = HEADER_FILL; cell.font = HEADER_FONT
    cell.border = THIN_BORDER; cell.alignment = { vertical: 'middle' }
  })
}

async function exportExcel() {
  const r = result.value
  if (!r) return
  const wb = new ExcelJS.Workbook()
  wb.created = new Date()

  const ws1 = wb.addWorksheet('不一致')
  ws1.columns = [
    { header: 'PDF品番', key: 'pdf_code', width: 16 },
    { header: 'DB品番', key: 'db_code', width: 16 },
    { header: '品名', key: 'product_name', width: 28 },
    { header: '工程', key: 'process_code', width: 6 },
    { header: 'PDF進度', key: 'progress_pdf', width: 10 },
    { header: 'DB進度', key: 'progress_db', width: 10 },
    { header: '差異', key: 'diff', width: 10 },
  ]
  styleHeader(ws1.getRow(1))
  for (const row of r.mismatch) {
    const exRow = ws1.addRow(row)
    exRow.eachCell(cell => { cell.border = THIN_BORDER; cell.font = { size: 10 } })
    const ad = Math.abs(row.diff)
    if (ad >= 10) exRow.eachCell(cell => { cell.fill = RED_FILL })
    else if (ad >= 3) exRow.eachCell(cell => { cell.fill = YELLOW_FILL })
  }

  const ws2 = wb.addWorksheet('一致')
  ws2.columns = [
    { header: 'PDF品番', key: 'pdf_code', width: 16 },
    { header: 'DB品番', key: 'db_code', width: 16 },
    { header: '品名', key: 'product_name', width: 28 },
    { header: '工程', key: 'process_code', width: 6 },
    { header: '進度', key: 'progress_pdf', width: 10 },
  ]
  styleHeader(ws2.getRow(1))
  for (const row of r.match) {
    const exRow = ws2.addRow(row)
    exRow.eachCell(cell => { cell.border = THIN_BORDER; cell.font = { size: 10 }; cell.fill = GREEN_FILL })
  }

  if (r.pdf_only.length) {
    const ws3 = wb.addWorksheet('PDF独自')
    ws3.columns = [
      { header: '品番', key: 'pdf_code', width: 16 },
      { header: '進度', key: 'progress_pdf', width: 10 },
    ]
    styleHeader(ws3.getRow(1))
    for (const row of r.pdf_only) {
      const exRow = ws3.addRow(row)
      exRow.eachCell(cell => { cell.border = THIN_BORDER; cell.font = { size: 10 } })
    }
  }

  if (r.db_only.length) {
    const ws4 = wb.addWorksheet('DB独自')
    ws4.columns = [
      { header: '品番', key: 'db_code', width: 16 },
      { header: '品名', key: 'product_name', width: 28 },
      { header: '工程', key: 'process_code', width: 6 },
      { header: '進度', key: 'progress_db', width: 10 },
    ]
    styleHeader(ws4.getRow(1))
    for (const row of r.db_only) {
      const exRow = ws4.addRow(row)
      exRow.eachCell(cell => { cell.border = THIN_BORDER; cell.font = { size: 10 } })
    }
  }

  const buffer = await wb.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `進度突合_${r.line_code}_${r.target_date}.xlsx`
  link.click()
  window.URL.revokeObjectURL(url)
}
</script>

<style scoped>
.progress-pdf-compare { padding: 8px; }
.usage-guide {
  margin-bottom: 10px;
  padding: 8px 10px;
  background: #eef7ff;
  border: 1px solid #bbdefb;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
}
.usage-guide-title {
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 700;
  color: #1565c0;
}
.controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.controls label { display: flex; align-items: center; gap: 4px; font-size: 13px; }
.controls input, .controls select { font-size: 13px; padding: 2px 4px; }
.controls button {
  padding: 4px 12px; font-size: 13px; cursor: pointer;
  background: #1976d2; color: #fff; border: none; border-radius: 3px;
}
.controls button:disabled { background: #999; cursor: not-allowed; }
.btn-excel { background: #2e7d32 !important; }
.btn-adjust { background: #e65100 !important; }
.chk { width: 28px; text-align: center; }
.error-msg { color: #d32f2f; margin: 4px 0; font-size: 13px; }
.adjust-notice {
  margin: 4px 0; padding: 6px 10px; font-size: 13px; font-weight: 600;
  background: #fff3e0; border: 1px solid #ffb74d; border-radius: 4px; color: #e65100;
}

.summary-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 3px; font-weight: 600; }
.badge.ok { background: #e8f5e9; color: #2e7d32; }
.badge.ng { background: #ffebee; color: #c62828; }
.badge.warn { background: #fff8e1; color: #f57f17; }
.badge.info { background: #e3f2fd; color: #1565c0; }

.section { margin-bottom: 8px; }
.section h3 { font-size: 14px; margin: 4px 0; }
.section summary { font-size: 14px; cursor: pointer; font-weight: 600; }

.compare-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.compare-table th, .compare-table td { border: 1px solid #ddd; padding: 2px 6px; white-space: nowrap; }
.compare-table th { background: #f5f5f5; font-weight: 600; position: sticky; top: 0; }
.num { text-align: right; }
.diff-cell { font-weight: 700; }
.diff-large { background: #ffcdd2; }
.diff-medium { background: #fff9c4; }
.diff-small { background: #f3f3f3; }

.result-area { max-height: calc(100vh - 120px); overflow-y: auto; }
</style>
