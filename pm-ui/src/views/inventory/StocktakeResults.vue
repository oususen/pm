<template>
  <div class="results-page">
    <div class="caption">棚卸結果確認</div>

    <div class="filters">
      <label class="filter-field">
        <span>棚卸日</span>
        <input v-model="filters.stocktake_date" type="date" />
      </label>
      <label class="filter-field">
        <span>エリア</span>
        <select v-model="filters.area_name">
          <option value="">すべて</option>
          <option v-for="a in areaChoices" :key="a" :value="a">{{ a }}</option>
        </select>
      </label>
      <label class="filter-field">
        <span>品番</span>
        <input v-model="filters.product_code" type="text" placeholder="品番" @keyup.enter="load" />
      </label>
      <label class="filter-field">
        <span>置き場</span>
        <select v-model="filters.stock_location">
          <option value="">すべて</option>
          <option v-for="loc in locationChoices" :key="loc" :value="loc">{{ loc }}</option>
        </select>
      </label>
      <button class="btn" @click="load" :disabled="loading">検索</button>
      <button type="button" class="btn btn-mode" @click="toggleMode">
        表示: {{ isSummary ? '合計' : '分行' }}
      </button>
      <button class="btn btn-excel" @click="openExportDialog('summary')" :disabled="exporting">Excel合計</button>
      <button class="btn btn-excel" @click="openExportDialog('detail')" :disabled="exporting">Excel分行</button>
      <button class="btn btn-excel" @click="openExportDialog('company')" :disabled="exporting">会社集計用Excel</button>
      <button class="btn btn-latest" @click="fetchLatestSystem" :disabled="loading || loadingLatest || rawRows.length === 0">
        {{ loadingLatest ? '取得中...' : '最新机上' }}
      </button>
    </div>

    <div v-if="loading" class="center">読み込み中...</div>
    <div v-else-if="error" class="center error">{{ error }}</div>
    <div v-else>
      <p class="count">{{ displayRows.length }} 件</p>
      <div class="table-wrap">
        <!-- 合計モード -->
        <table v-if="isSummary" class="grid">
          <thead>
            <tr>
              <th class="col-code">品番</th>
              <th class="col-name">品名</th>
              <th class="col-area">入力エリア</th>
              <th class="col-loc">置き場</th>
              <th class="col-num">机上在庫</th>
              <th class="col-num">机上進度</th>
              <th v-if="showLatest" class="col-num col-latest">最新在庫</th>
              <th v-if="showLatest" class="col-num col-latest">最新進度</th>
              <th class="col-num">現物数</th>
              <th class="col-num">差異</th>
              <th class="col-cnt">入力件数</th>
              <th class="col-person">最終更新者</th>
              <th class="col-date">最終更新日時</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in displayRows" :key="row.product_id">
              <td>{{ row.product_code }}</td>
              <td>{{ row.product_name || '-' }}</td>
              <td>{{ row.area_names || '-' }}</td>
              <td>{{ row.stock_locations || '-' }}</td>
              <td class="num">{{ row.system_stock_qty }}</td>
              <td class="num">{{ row.system_progress_qty }}</td>
              <td v-if="showLatest" class="num col-latest">{{ latestSystemMap[row.product_id]?.system_stock_qty ?? '-' }}</td>
              <td v-if="showLatest" class="num col-latest">{{ latestSystemMap[row.product_id]?.system_progress_qty ?? '-' }}</td>
              <td class="num">{{ row.actual_stock_qty }}</td>
              <td class="num" :class="diffClass(row.diff_qty)">{{ formatSigned(row.diff_qty) }}</td>
              <td class="num">{{ row.record_count }}</td>
              <td>{{ row.updated_by_name || '-' }}</td>
              <td>{{ formatDatetime(row.updated_at) }}</td>
            </tr>
            <tr v-if="displayRows.length === 0">
              <td :colspan="showLatest ? 13 : 11" class="center">データなし</td>
            </tr>
          </tbody>
        </table>
        <!-- 分行モード -->
        <table v-else class="grid">
          <thead>
            <tr>
              <th class="col-code">品番</th>
              <th class="col-name">品名</th>
              <th class="col-area">入力エリア</th>
              <th class="col-loc">置き場</th>
              <th class="col-num">机上在庫</th>
              <th class="col-num">机上進度</th>
              <th v-if="showLatest" class="col-num col-latest">最新在庫</th>
              <th v-if="showLatest" class="col-num col-latest">最新進度</th>
              <th class="col-num">現物数</th>
              <th class="col-person">記入者</th>
              <th class="col-person">カウンター</th>
              <th class="col-note">備考</th>
              <th class="col-person">更新者</th>
              <th class="col-date">更新日時</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in displayRows" :key="row.id">
              <td>{{ row.product_code }}</td>
              <td>{{ row.product_name || '-' }}</td>
              <td>{{ row.area_name || '-' }}</td>
              <td>{{ row.stock_locations || '-' }}</td>
              <td class="num">{{ row.system_stock_qty }}</td>
              <td class="num">{{ row.system_progress_qty }}</td>
              <td v-if="showLatest" class="num col-latest">{{ latestSystemMap[row.product_id]?.system_stock_qty ?? '-' }}</td>
              <td v-if="showLatest" class="num col-latest">{{ latestSystemMap[row.product_id]?.system_progress_qty ?? '-' }}</td>
              <td class="num">{{ row.actual_stock_qty }}</td>
              <td>{{ row.recorder_name || '-' }}</td>
              <td>{{ row.counter_name || '-' }}</td>
              <td>{{ row.note || '-' }}</td>
              <td>{{ row.updated_by_name || '-' }}</td>
              <td>{{ formatDatetime(row.updated_at) }}</td>
            </tr>
            <tr v-if="displayRows.length === 0">
              <td :colspan="showLatest ? 14 : 12" class="center">データなし</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div v-if="showExportDialog" class="modal-overlay" @click.self="showExportDialog = false">
    <div class="modal-box">
      <div class="modal-header">Excel出力 — {{ exportTypeLabel }}</div>
      <div class="modal-body">
        <label class="modal-field">
          <span>棚卸日</span>
          <input v-model="exportDate" type="date" />
        </label>
        <label class="modal-field">
          <span>エリア</span>
          <select v-model="exportArea">
            <option value="">すべて</option>
            <option v-for="a in exportAreaChoices" :key="a" :value="a">{{ a }}</option>
          </select>
        </label>
      </div>
      <div class="modal-footer">
        <button type="button" @click="showExportDialog = false">キャンセル</button>
        <button type="button" class="btn-export" @click="executeExport" :disabled="exporting || !exportDate">
          {{ exporting ? '出力中...' : '出力' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import api from '@/api/client'
import * as XLSX from 'xlsx'

const today = new Date()
const yyyy = today.getFullYear()
const mm = String(today.getMonth() + 1).padStart(2, '0')
const dd = String(today.getDate()).padStart(2, '0')

const filters = ref({
  stocktake_date: `${yyyy}-${mm}-${dd}`,
  area_name: '',
  product_code: '',
  stock_location: '',
})
const rawRows = ref([])
const areaChoices = ref([])
const locationChoices = ref([])
const loading = ref(false)
const error = ref('')
const isSummary = ref(true)
const loadingLatest = ref(false)
const showLatest = ref(false)
const latestSystemMap = ref({})

const toggleMode = () => { isSummary.value = !isSummary.value }

const summaryRows = computed(() => {
  const groups = {}
  for (const r of rawRows.value) {
    const pid = r.product_id
    if (!groups[pid]) {
      groups[pid] = {
        product_id: pid,
        product_code: r.product_code,
        product_name: r.product_name,
        category: r.category || '',
        stock_locations: r.stock_locations,
        system_stock_qty: r.system_stock_qty,
        system_progress_qty: r.system_progress_qty,
        actual_stock_qty: 0,
        record_count: 0,
        area_set: new Set(),
        updated_by_name: '',
        updated_at: null,
      }
    }
    const g = groups[pid]
    g.actual_stock_qty += r.actual_stock_qty
    g.record_count++
    if (r.area_name) g.area_set.add(r.area_name)
    if (!g.updated_at || r.updated_at > g.updated_at) {
      g.updated_at = r.updated_at
      g.updated_by_name = r.updated_by_name
    }
  }
  return Object.values(groups)
    .map(g => ({
      ...g,
      area_names: [...g.area_set].sort().join(', '),
      diff_qty: g.actual_stock_qty - g.system_stock_qty,
    }))
    .sort((a, b) => a.product_code.localeCompare(b.product_code))
})

const displayRows = computed(() => isSummary.value ? summaryRows.value : rawRows.value)

const formatDatetime = (val) => {
  if (!val) return '-'
  return val.replace('T', ' ').slice(0, 16)
}

const formatSigned = (value) => {
  const num = Number(value || 0)
  if (num > 0) return `+${num}`
  return `${num}`
}

const diffClass = (val) => ({
  positive: val > 0,
  negative: val < 0,
})

const load = async () => {
  if (!filters.value.stocktake_date) {
    error.value = '棚卸日を指定してください'
    return
  }
  loading.value = true
  error.value = ''
  showLatest.value = false
  latestSystemMap.value = {}
  try {
    const params = { stocktake_date: filters.value.stocktake_date }
    if (filters.value.area_name) params.area_name = filters.value.area_name
    if (filters.value.product_code) params.product_code = filters.value.product_code
    if (filters.value.stock_location) params.stock_location = filters.value.stock_location
    const res = await api.stocktakeRecords.results(params)
    rawRows.value = res.data.rows || []
    areaChoices.value = res.data.area_choices || []
    locationChoices.value = res.data.location_choices || []
  } catch (e) {
    error.value = e?.response?.data?.detail || '取得に失敗しました'
  } finally {
    loading.value = false
  }
}

const fetchLatestSystem = async () => {
  loadingLatest.value = true
  try {
    const params = { stocktake_date: filters.value.stocktake_date }
    if (filters.value.area_name) params.area_name = filters.value.area_name
    if (filters.value.product_code) params.product_code = filters.value.product_code
    const res = await api.stocktakeRecords.latestSystem(params)
    const raw = res.data || {}
    const mapped = {}
    for (const [k, v] of Object.entries(raw)) mapped[Number(k)] = v
    latestSystemMap.value = mapped
    showLatest.value = true
  } catch (e) {
    alert('最新机上の取得に失敗しました')
  } finally {
    loadingLatest.value = false
  }
}

const exporting = ref(false)
const showExportDialog = ref(false)
const exportType = ref('')
const exportDate = ref('')
const exportArea = ref('')
const exportAreaChoices = ref([])

const exportTypeLabel = computed(() => {
  if (exportType.value === 'summary') return 'Excel合計'
  if (exportType.value === 'detail') return 'Excel分行'
  return '会社集計用Excel'
})

const openExportDialog = async (type) => {
  exportType.value = type
  exportDate.value = filters.value.stocktake_date
  exportArea.value = ''
  showExportDialog.value = true
  try {
    const res = await api.stocktakeRecords.results({ stocktake_date: exportDate.value })
    exportAreaChoices.value = res.data.area_choices || []
  } catch (_) {
    exportAreaChoices.value = []
  }
}

const fetchExportRows = async () => {
  const params = { stocktake_date: exportDate.value }
  if (exportArea.value) params.area_name = exportArea.value
  const res = await api.stocktakeRecords.resultsExport(params)
  return res.data.rows || []
}

const buildSummary = (rows) => {
  const groups = {}
  for (const r of rows) {
    const pid = r.product_id
    if (!groups[pid]) {
      groups[pid] = {
        product_id: pid,
        product_code: r.product_code,
        product_name: r.product_name,
        category: r.category || '',
        stock_locations: r.stock_locations,
        system_stock_qty: r.system_stock_qty,
        system_progress_qty: r.system_progress_qty,
        actual_stock_qty: 0,
        record_count: 0,
        area_set: new Set(),
        updated_by_name: '',
        updated_at: null,
      }
    }
    const g = groups[pid]
    g.actual_stock_qty += r.actual_stock_qty
    g.record_count++
    if (r.area_name) g.area_set.add(r.area_name)
    if (!g.updated_at || r.updated_at > g.updated_at) {
      g.updated_at = r.updated_at
      g.updated_by_name = r.updated_by_name
    }
  }
  return Object.values(groups)
    .map(g => ({ ...g, area_names: [...g.area_set].sort().join(', '), diff_qty: g.actual_stock_qty - g.system_stock_qty }))
    .sort((a, b) => a.product_code.localeCompare(b.product_code))
}

const executeExport = async () => {
  exporting.value = true
  try {
    const rows = await fetchExportRows()
    if (exportType.value === 'detail') {
      doExportDetail(rows)
    } else if (exportType.value === 'summary') {
      await doExportSummary(rows)
    } else {
      doExportCompany(rows)
    }
    showExportDialog.value = false
  } catch (e) {
    alert('Excel出力に失敗しました')
  } finally {
    exporting.value = false
  }
}

const doExportSummary = async (rows) => {
  const summary = buildSummary(rows)
  const params = { stocktake_date: exportDate.value }
  if (exportArea.value) params.area_name = exportArea.value
  let latestMap = {}
  try {
    const res = await api.stocktakeRecords.latestSystem(params)
    const raw = res.data || {}
    for (const [k, v] of Object.entries(raw)) latestMap[Number(k)] = v
  } catch (_) { /* 取得失敗時は空欄 */ }
  const header = ['品番', '品名', '入力エリア', '置き場', '机上在庫', '机上進度', '最新在庫', '最新進度', '現物数', '差異', '入力件数', '最終更新者', '最終更新日時']
  const data = summary.map(r => {
    const lat = latestMap[r.product_id] || {}
    return [
      r.product_code, r.product_name || '', r.area_names || '', r.stock_locations || '',
      r.system_stock_qty, r.system_progress_qty,
      lat.system_stock_qty ?? '', lat.system_progress_qty ?? '',
      r.actual_stock_qty, r.diff_qty,
      r.record_count, r.updated_by_name || '', formatDatetime(r.updated_at),
    ]
  })
  const areaSuffix = exportArea.value ? `_${exportArea.value}` : ''
  downloadExcel([header, ...data], `棚卸結果_合計_${exportDate.value}${areaSuffix}`)
}

const doExportDetail = (rows) => {
  const header = ['品番', '品名', '入力エリア', '置き場', '机上在庫', '机上進度', '現物数', '記入者', 'カウンター', '備考', '更新者', '更新日時']
  const data = rows.map(r => [
    r.product_code, r.product_name || '', r.area_name || '', r.stock_locations || '',
    r.system_stock_qty, r.system_progress_qty, r.actual_stock_qty,
    r.recorder_name || '', r.counter_name || '', r.note || '',
    r.updated_by_name || '', formatDatetime(r.updated_at),
  ])
  const areaSuffix = exportArea.value ? `_${exportArea.value}` : ''
  downloadExcel([header, ...data], `棚卸結果_分行_${exportDate.value}${areaSuffix}`)
}

const normalizeCode = (code) => {
  if (/SUB$/i.test(code)) return code
  return code.replace(/[BbGg]$/, '')
}

const getCustomer = (code) => /^[RVrvＲＶ]/.test(code) ? 'クボタ' : 'ティエラ'

const doExportCompany = (rows) => {
  const summary = buildSummary(rows)
  const groups = {}
  for (const r of summary) {
    const code = normalizeCode(r.product_code)
    if (!groups[code]) {
      groups[code] = {
        product_code: code, product_name: r.product_name || '', category: r.category || '',
        area_set: new Set(), actual_stock_qty: 0, customer: getCustomer(code),
      }
    }
    const g = groups[code]
    g.actual_stock_qty += r.actual_stock_qty
    if (r.area_names) r.area_names.split(', ').forEach(a => g.area_set.add(a))
  }
  const allRows = Object.values(groups).sort((a, b) => a.product_code.localeCompare(b.product_code))
  const materialRows = allRows.filter(g => g.category === 'MATERIAL')
  const partsRows = allRows.filter(g => g.category !== 'MATERIAL')

  const header = ['客先', '品番', '品名', '合計', 'エリア']
  const toRow = g => [g.customer, g.product_code, g.product_name, g.actual_stock_qty, [...g.area_set].sort().join(', ')]

  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([header, ...partsRows.map(toRow)]), '部品')
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([header, ...materialRows.map(toRow)]), '材料')
  const areaSuffix = exportArea.value ? `_${exportArea.value}` : ''
  XLSX.writeFile(wb, `棚卸結果_会社集計用_${exportDate.value}${areaSuffix}.xlsx`)
}

const downloadExcel = (rows, filename) => {
  const ws = XLSX.utils.aoa_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
  XLSX.writeFile(wb, `${filename}.xlsx`)
}

watch(exportDate, async (newDate) => {
  if (!newDate || !showExportDialog.value) return
  exportArea.value = ''
  try {
    const res = await api.stocktakeRecords.results({ stocktake_date: newDate })
    exportAreaChoices.value = res.data.area_choices || []
  } catch (_) {
    exportAreaChoices.value = []
  }
})

load()
</script>

<style scoped>
.results-page {
  padding: 12px 10px 18px;
  background: #efefdc;
  min-height: 100%;
}
.caption {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 10px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
  margin-bottom: 12px;
}
.filter-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 13px;
}
.filter-field input,
.filter-field select {
  padding: 4px 6px;
  border: 1px solid #c7ced9;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
}
.btn {
  padding: 5px 14px;
  background: #334155;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn:disabled {
  opacity: 0.5;
}
.btn-mode {
  background: #1e40af;
}
.btn-excel {
  background: #16713a;
}
.btn-latest {
  background: #9333ea;
}
.col-latest {
  background: #faf5ff !important;
}
.center {
  text-align: center;
  padding: 24px 0;
  color: #64748b;
}
.error {
  color: #dc2626;
}
.count {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 6px;
}
.table-wrap {
  overflow-x: auto;
}
.grid {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.grid th,
.grid td {
  border: 1px solid #c7ced9;
  padding: 4px 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.grid th {
  background: #e2e8f0;
  font-weight: 600;
  text-align: center;
  position: sticky;
  top: 0;
  z-index: 1;
}
.grid tbody tr:nth-child(even) {
  background: #f8fafc;
}
.grid tbody tr:hover {
  background: #e0f2fe;
}
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.positive {
  color: #2563eb;
  font-weight: 600;
}
.negative {
  color: #dc2626;
  font-weight: 600;
}
.col-code { width: 160px; }
.col-name { width: 160px; }
.col-area { width: 100px; }
.col-loc { width: 100px; }
.col-num { width: 80px; }
.col-cnt { width: 70px; }
.col-person { width: 90px; }
.col-date { width: 140px; }
.col-note { width: 150px; }
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-box {
  width: 320px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}
.modal-header {
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 700;
  background: #16713a;
  color: #fff;
}
.modal-body {
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.modal-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}
.modal-field span {
  font-weight: 600;
  color: #334155;
}
.modal-field input,
.modal-field select {
  padding: 5px 8px;
  border: 1px solid #c7ced9;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
}
.modal-footer {
  padding: 10px 14px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid #e5e7eb;
}
.modal-footer button {
  padding: 5px 16px;
  border: 1px solid #9ca3af;
  background: #f8fafc;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
}
.btn-export {
  background: #16713a !important;
  color: #fff !important;
  border-color: #16713a !important;
}
.btn-export:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
