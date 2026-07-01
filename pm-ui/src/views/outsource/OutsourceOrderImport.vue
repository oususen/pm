<template>
  <div class="page-container">
    <h2 class="page-title">FB受注取込 <DataSourceDialog title="FB受注取込" :sources="dsSources" /></h2>

    <div class="import-section">
      <div class="file-input-row">
        <label class="file-label">
          CSV/XLSXファイル選択
          <input type="file" accept=".csv,.xlsx,.xls" @change="onFileSelect" ref="fileInput" />
        </label>
        <select v-if="isCsvFile" v-model="encoding" class="encoding-select">
          <option value="utf-8">UTF-8</option>
          <option value="shift_jis">Shift_JIS</option>
        </select>
        <button class="btn-primary" :disabled="!file || importing" @click="doImport">
          {{ importing ? '取込中...' : '取込実行' }}
        </button>
      </div>

      <div v-if="result" class="result-section">
        <h3>取込結果</h3>
        <div class="result-summary">
          <span class="badge badge-success">作成: {{ result.created_count }}件</span>
          <span class="badge badge-warning">スキップ: {{ result.skipped_count }}件</span>
          <span class="badge badge-error">エラー: {{ result.error_count }}件</span>
        </div>

        <div v-if="result.errors.length" class="error-list">
          <h4>エラー詳細</h4>
          <div v-for="(err, i) in result.errors" :key="i" class="error-item">
            行{{ err.row }}: {{ err.message }}
          </div>
        </div>

        <div v-if="result.skipped.length" class="skip-list">
          <h4>スキップ（登録済み）</h4>
          <div v-for="(s, i) in result.skipped" :key="i" class="skip-item">
            {{ s.case_no }}: {{ s.message }}
          </div>
        </div>
      </div>

      <div v-if="preview.length" class="preview-section">
        <h3>プレビュー（{{ preview.length }}件）</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>品目コード</th>
              <th>品目名称</th>
              <th>塗装名</th>
              <th>塗装日</th>
              <th>数量</th>
              <th>案件番号</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in preview" :key="i">
              <td>{{ row.item_code }}</td>
              <td>{{ row.item_name }}</td>
              <td>{{ row.painting_name }}</td>
              <td>{{ row.painting_date }}</td>
              <td class="text-right">{{ row.qty }}</td>
              <td class="case-no">{{ row.case_no }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_outsource_order / t_outsource_order_line', desc: 'CSV/XLSX取込による受注データ作成' },
]

const file = ref(null)
const encoding = ref('utf-8')
const importing = ref(false)
const preview = ref([])
const result = ref(null)
const fileInput = ref(null)
const isCsvFile = ref(true)

function onFileSelect(e) {
  const f = e.target.files[0]
  if (!f) return
  file.value = f
  isCsvFile.value = !/\.(xlsx|xls)$/i.test(f.name || '')
  result.value = null
  parsePreview(f)
}

function parsePreview(f) {
  if (/\.(xlsx|xls)$/i.test(f.name || '')) {
    parseExcelPreview(f)
    return
  }
  parseCsvPreview(f)
}

function parseCsvPreview(f) {
  const parseCsvLine = (line) => {
    const cols = []
    let cur = ''
    let inQuotes = false
    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i]
      if (ch === '"') {
        if (inQuotes && line[i + 1] === '"') {
          cur += '"'
          i += 1
        } else {
          inQuotes = !inQuotes
        }
      } else if (ch === ',' && !inQuotes) {
        cols.push(cur.trim())
        cur = ''
      } else {
        cur += ch
      }
    }
    cols.push(cur.trim())
    return cols
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target.result
    const lines = text.split(/\r?\n/).filter(l => l.trim())
    if (lines.length < 2) return

    preview.value = lines.slice(1).map(line => {
      const cols = parseCsvLine(line)
      const item_code = cols[0]?.trim() || ''
      const painting_date = cols[3]?.trim() || ''
      const datePart = painting_date.replace(/\//g, '')
      return {
        item_code,
        item_name: cols[1]?.trim() || '',
        painting_name: cols[2]?.trim() || '',
        painting_date,
        qty: cols[4]?.trim() || '',
        case_no: `${datePart}-${item_code}`,
      }
    })
  }
  reader.readAsText(f, encoding.value === 'shift_jis' ? 'Shift_JIS' : 'UTF-8')
}

function parseExcelPreview(f) {
  const reader = new FileReader()
  reader.onload = (e) => {
    const workbook = XLSX.read(e.target.result, { type: 'array' })
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false })
    let lastDenpyoKubun = ''
    let lastDenpyoType = ''

    preview.value = rows.slice(1).filter(cols => cols?.length).map((cols) => {
      const denpyoKubun = String(cols[0] || '').trim() || lastDenpyoKubun
      const denpyoType = String(cols[1] || '').trim() || lastDenpyoType
      if (denpyoKubun) lastDenpyoKubun = denpyoKubun
      if (denpyoType) lastDenpyoType = denpyoType

      const item_code = String(cols[2] || '').trim()
      const painting_date = normalizeExcelDate(cols[5])
      const datePart = painting_date.replace(/\D/g, '')
      const painting_name = [denpyoType, denpyoKubun].filter(Boolean).join(' / ')

      return {
        item_code,
        item_name: String(cols[3] || '').trim(),
        painting_name,
        painting_date,
        qty: String(cols[4] || '').trim(),
        case_no: item_code && datePart ? `${datePart}-${item_code}` : '',
      }
    }).filter(row => row.item_code || row.item_name || row.qty)
  }
  reader.readAsArrayBuffer(f)
}

function normalizeExcelDate(value) {
  const text = String(value || '').trim()
  if (/^\d{8}$/.test(text)) {
    return `${text.slice(0, 4)}/${Number(text.slice(4, 6))}/${Number(text.slice(6, 8))}`
  }
  return text
}

async function doImport() {
  if (!file.value) return
  importing.value = true
  result.value = null

  try {
    const formData = new FormData()
    formData.append('file', file.value)
    formData.append('encoding', encoding.value)

    const res = await api.outsource.importCSV(formData)
    result.value = res.data
  } catch (err) {
    result.value = {
      created_count: 0,
      skipped_count: 0,
      error_count: 1,
      created: [],
      skipped: [],
      errors: [{ row: 0, message: err.response?.data?.error || err.message }],
    }
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { margin-bottom: 16px; font-size: 18px; }

.file-input-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.file-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.encoding-select {
  padding: 4px 8px;
  font-size: 13px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.btn-primary {
  padding: 6px 16px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.preview-section, .result-section { margin-top: 16px; }
.preview-section h3, .result-section h3 { font-size: 14px; margin-bottom: 8px; }

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.data-table th, .data-table td {
  border: 1px solid #ddd;
  padding: 4px 8px;
  text-align: left;
}
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.case-no { font-family: monospace; font-size: 11px; color: #666; }

.result-summary {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}
.badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fff3e0; color: #e65100; }
.badge-error { background: #fbe9e7; color: #c62828; }

.error-list, .skip-list { margin-top: 8px; }
.error-list h4, .skip-list h4 { font-size: 13px; margin-bottom: 4px; }
.error-item { color: #c62828; font-size: 12px; padding: 2px 0; }
.skip-item { color: #e65100; font-size: 12px; padding: 2px 0; }
</style>
