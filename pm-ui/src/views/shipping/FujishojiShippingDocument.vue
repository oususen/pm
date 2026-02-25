<template>
  <div class="fujishoji-document">
    <h2 class="page-title">富士商事出荷指示書</h2>

    <div class="card">
      <div class="card-header">
        <h3>出荷指示書生成</h3>
      </div>
      <div class="card-body">

        <!-- 日付選択 -->
        <div class="form-group">
          <label for="target-date">出荷日</label>
          <div class="date-selector">
            <input
              id="target-date"
              v-model="targetDate"
              type="date"
              class="form-control"
            />
            <button @click="loadAvailableDates" class="btn btn-secondary" :disabled="loading">
              📅 利用可能な日付を表示
            </button>
          </div>
        </div>

        <!-- 利用可能な日付チップ -->
        <div v-if="availableDates.length > 0" class="available-dates">
          <h4>利用可能な日付（フロア製品受注あり）</h4>
          <div class="date-chips">
            <button
              v-for="date in availableDates"
              :key="date"
              @click="selectDate(date)"
              class="date-chip"
              :class="{ active: targetDate === date }"
            >
              {{ formatDate(date) }}
            </button>
          </div>
        </div>

        <!-- アクションボタン -->
        <div class="action-buttons">
          <button @click="previewData"  class="btn btn-info"    :disabled="loading    || !targetDate">🔍 データプレビュー</button>
          <button @click="downloadPdf"  class="btn btn-primary" :disabled="pdfLoading || !targetDate">📄 PDF生成</button>
        </div>

        <div v-if="loading || pdfLoading" class="loading-indicator">
          <div class="spinner"></div>
          <p>{{ pdfLoading ? 'PDF生成中...' : 'データを取得中...' }}</p>
        </div>
        <div v-if="errorMessage"   class="alert alert-danger">{{ errorMessage }}</div>
        <div v-if="successMessage" class="alert alert-success">{{ successMessage }}</div>
      </div>
    </div>

    <!-- データプレビュー -->
    <div v-if="showPreview && docData" class="card mt-3">
      <div class="card-header">
        <h3>出荷データプレビュー - {{ formatDate(docData.date) }}</h3>
      </div>
      <div class="card-body">

        <!-- サマリ -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">①8:00便</div>
            <div class="stat-value">{{ docData.trip1.length }}<span class="stat-unit">台車</span></div>
          </div>
          <div class="stat-card">
            <div class="stat-label">②8:00便</div>
            <div class="stat-value">{{ docData.trip2.length }}<span class="stat-unit">台車</span></div>
          </div>
          <div class="stat-card">
            <div class="stat-label">合計</div>
            <div class="stat-value">
              {{ docData.trip1.length + docData.trip2.length }}
              <span class="stat-unit">/ {{ docData.carts_per_trip * 2 }}台車</span>
            </div>
          </div>
          <div class="stat-card" v-if="overCount > 0">
            <div class="stat-label over">⚠ 超過</div>
            <div class="stat-value over">{{ overCount }}<span class="stat-unit">台車</span></div>
          </div>
        </div>

        <!-- 凡例 -->
        <div class="legend-row">
          <!-- 左: 1-5 -->
          <div class="legend-group">
            <div
              v-for="p in legendLeft"
              :key="p.product_code"
              class="legend-item"
              :style="{ backgroundColor: p.color, color: isLight(p.color) ? '#222' : '#fff' }"
            >
              <span class="leg-num">[{{ p.number }}]</span>
              <span class="leg-code">{{ p.product_code }}</span>
              <span class="leg-label">（{{ p.label }}）</span>
            </div>
          </div>
          <!-- 右: A-F -->
          <div class="legend-group">
            <div
              v-for="p in legendRight"
              :key="p.product_code"
              class="legend-item"
              :style="{ backgroundColor: p.color, color: isLight(p.color) ? '#222' : '#fff' }"
            >
              <span class="leg-num">[{{ p.number }}]</span>
              <span class="leg-code">{{ p.product_code }}</span>
              <span class="leg-label">（{{ p.label }}）</span>
            </div>
          </div>
        </div>

        <!-- 台車グリッド（縦積み・列優先） -->
        <div class="trips-section">

          <!-- ①8:00便 -->
          <div class="trip-wrapper">
            <div class="trip-label-row">
              <div class="trip-label">①8:00便</div>
            </div>
            <div class="cart-grid">
              <div
                v-for="(cart, i) in trip1Grid"
                :key="'t1-' + i"
                class="cart-cell"
                :style="cellStyle(cart)"
              >
                <template v-if="cart">
                  <span class="cell-num">[{{ cart.number }}]</span>
                  <span class="cell-type">{{ cellType(cart.label) }}</span>
                  <span class="cell-model">{{ cellModel(cart.label) }}{{ qtySymbol(cart.qty_in_cart) }}</span>
                </template>
              </div>
            </div>
          </div>

          <!-- ②8:00便 -->
          <div class="trip-wrapper">
            <div class="trip-label-row">
              <div class="trip-label">②8:00便</div>
            </div>
            <div class="cart-grid">
              <div
                v-for="(cart, i) in trip2Grid"
                :key="'t2-' + i"
                class="cart-cell"
                :style="cellStyle(cart)"
              >
                <template v-if="cart">
                  <span class="cell-num">[{{ cart.number }}]</span>
                  <span class="cell-type">{{ cellType(cart.label) }}</span>
                  <span class="cell-model">{{ cellModel(cart.label) }}{{ qtySymbol(cart.qty_in_cart) }}</span>
                </template>
              </div>
            </div>
          </div>

          <!-- ③④追加便（横並び） -->
          <div class="extra-sections">
            <div class="extra-wrapper">
              <div class="extra-label-row">
                <div class="extra-label">③追加_日商便</div>
              </div>
              <div class="extra-grid">
                <div v-for="i in 4" :key="'e3-' + i" class="cart-cell empty"></div>
              </div>
            </div>
            <div class="extra-wrapper">
              <div class="extra-label-row">
                <div class="extra-label">④追加便</div>
              </div>
              <div class="extra-grid">
                <div v-for="i in 4" :key="'e4-' + i" class="cart-cell empty"></div>
              </div>
            </div>
          </div>

        </div>

        <!-- フッター -->
        <div class="footer-summary" :class="{ over: overCount > 0 }">
          合計 {{ docData.trip1.length + docData.trip2.length }}台車
          （{{ docData.items_per_cart }}個入り × {{ docData.carts_per_trip }}台車/便 × 2便）
          <span v-if="overCount > 0" class="over-text">　★{{ overCount }}台車超過</span>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/api/client'

const targetDate     = ref('')
const loading        = ref(false)
const pdfLoading     = ref(false)
const errorMessage   = ref('')
const successMessage = ref('')
const availableDates = ref([])
const docData        = ref(null)
const showPreview    = ref(false)

const CARTS_PER_TRIP = 14

// 凡例グループ（固定）
const legendLeft  = [
  { product_code: "YD40006245", number: "1", label: "U-5 CAB",       color: "#FFB6C1" },
  { product_code: "YD40006630", number: "2", label: "U-5 CANOPY",    color: "#87CEEB" },
  { product_code: "YD40006237", number: "3", label: "55UR CAB",      color: "#90EE90" },
  { product_code: "YD40006618", number: "4", label: "55UR CANOPY",   color: "#FFD700" },
  { product_code: "YD40002946", number: "5", label: "30/40UR",       color: "#FFA500" },
]
const legendRight = [
  { product_code: "YD40006842", number: "A", label: "5t-EN CAB",     color: "#CD853F" },
  { product_code: "YD40007003", number: "B", label: "3t-EN CAB",     color: "#D3D3D3" },
  { product_code: "YD40007243", number: "C", label: "U-5NA CAB",     color: "#4682B4" },
  { product_code: "YD40007372", number: "D", label: "U-5NA CANOPY",  color: "#2F4F4F" },
  { product_code: "YD40007722", number: "E", label: "U-6EN 5tKTEG", color: "#FF6347" },
  { product_code: "YD40007688", number: "F", label: "55US-6 KTEG",   color: "#9370DB" },
]

const overCount = computed(() => {
  if (!docData.value) return 0
  return Math.max(0, docData.value.trip1.length + docData.value.trip2.length - CARTS_PER_TRIP * 2)
})

// padGrid: 14個に満たない場合 null で埋める（列優先グリッド用）
const padGrid = (carts) => {
  const g = [...carts]
  while (g.length < CARTS_PER_TRIP) g.push(null)
  return g
}

const trip1Grid = computed(() => padGrid(docData.value?.trip1 || []))
const trip2Grid = computed(() => padGrid(docData.value?.trip2 || []))

const isLight = (hex) => {
  const c = hex.replace('#', '')
  const r = parseInt(c.substr(0,2),16), g = parseInt(c.substr(2,2),16), b = parseInt(c.substr(4,2),16)
  return (r*299 + g*587 + b*114)/1000 > 140
}

const cellStyle = (cart) => {
  if (!cart) return { backgroundColor: '#f2f2f2', border: '1px solid #ddd' }
  return {
    backgroundColor: cart.color,
    border: '1px solid rgba(0,0,0,0.2)',
    color: isLight(cart.color) ? '#222' : '#fff',
  }
}

// セルテキスト（PDF _cell_lines と同ロジック）
const cellType = (label) => {
  if (label.endsWith(' CAB'))    return 'キャブ'
  if (label.endsWith(' CANOPY')) return 'キャノピ'
  if (label.endsWith(' KTEG'))   return label.split(' ').pop()
  return label.split(' ')[0]
}
const cellModel = (label) => {
  if (label.endsWith(' CAB'))    return label.slice(0, -4).trim()
  if (label.endsWith(' CANOPY')) return label.slice(0, -7).trim()
  if (label.endsWith(' KTEG'))   return label.split(' ').slice(0, -1).join(' ')
  const parts = label.split(' ')
  return parts.length > 1 ? parts.slice(1).join(' ') : ''
}
const qtySymbol = (n) => n === 2 ? '②' : `×${n}`

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  const wdays = ['日','月','火','水','木','金','土']
  return `${d.getMonth()+1}月${d.getDate()}日(${wdays[d.getDay()]})`
}

const todayDateStr = () => {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const isTodayOrFutureDate = (dateStr) => !!dateStr && dateStr >= todayDateStr()

const loadAvailableDates = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await api.fujishojiDocument.getAvailableDates()
    const dates = res.data?.dates || []
    availableDates.value = dates.filter(isTodayOrFutureDate)
    if (!availableDates.value.length) {
      errorMessage.value = '今日以降のフロア製品受注データが見つかりません'
    }
  } catch (e) {
    errorMessage.value = '日付取得に失敗しました: ' + (e.response?.data?.error || e.message)
  } finally { loading.value = false }
}

const selectDate = (date) => {
  targetDate.value = date
  errorMessage.value = ''
  successMessage.value = ''
}

const previewData = async () => {
  if (!targetDate.value) return
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  showPreview.value = false
  try {
    const res = await api.fujishojiDocument.getData(targetDate.value)
    docData.value = res.data
    showPreview.value = true
    successMessage.value = 'データを取得しました'
  } catch (e) {
    errorMessage.value = 'データ取得に失敗しました: ' + (e.response?.data?.error || e.message)
  } finally { loading.value = false }
}

const downloadPdf = async () => {
  if (!targetDate.value) return
  pdfLoading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const res = await api.fujishojiDocument.generatePdf(targetDate.value)
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url  = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `富士商事出荷指示書_${targetDate.value}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    successMessage.value = 'PDFを生成しました'
  } catch (e) {
    errorMessage.value = 'PDF生成に失敗しました: ' + (e.response?.data?.error || e.message)
  } finally { pdfLoading.value = false }
}
</script>

<style scoped>
.fujishoji-document { padding: 20px; }
.page-title { font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #2c3e50; }

.card { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
.card-header { padding: 15px 20px; border-bottom: 1px solid #e0e0e0; }
.card-header h3 { margin: 0; font-size: 18px; font-weight: 600; color: #2c3e50; }
.card-body { padding: 20px; }
.mt-3 { margin-top: 20px; }

.form-group { margin-bottom: 20px; }
.form-group label { display: block; margin-bottom: 8px; font-weight: 600; color: #555; }
.form-control { padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
.date-selector { display: flex; gap: 10px; align-items: center; }
.date-selector input { max-width: 200px; }

.available-dates { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 4px; }
.available-dates h4 { font-size: 14px; font-weight: 600; margin-bottom: 10px; color: #666; }
.date-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.date-chip { padding: 8px 16px; border: 1px solid #ddd; background: white; border-radius: 20px; cursor: pointer; font-size: 14px; transition: all 0.2s; }
.date-chip:hover { background: #f0f0f0; }
.date-chip.active { background: #4caf50; color: white; border-color: #4caf50; }

.action-buttons { display: flex; gap: 10px; margin-top: 20px; }
.btn { padding: 10px 20px; border: none; border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary  { background: #4caf50; color: white; }
.btn-primary:hover:not(:disabled) { background: #45a049; }
.btn-secondary { background: #6c757d; color: white; }
.btn-secondary:hover:not(:disabled) { background: #5a6268; }
.btn-info { background: #17a2b8; color: white; }
.btn-info:hover:not(:disabled) { background: #138496; }

.loading-indicator { display: flex; align-items: center; gap: 15px; padding: 20px; background: #f8f9fa; border-radius: 4px; margin-top: 20px; }
.spinner { width: 24px; height: 24px; border: 3px solid #f3f3f3; border-top: 3px solid #4caf50; border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }

.alert { padding: 15px; border-radius: 4px; margin-top: 20px; }
.alert-danger  { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }

/* ── サマリ ── */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }
.stat-card { padding: 14px 18px; background: #f8f9fa; border-radius: 8px; text-align: center; }
.stat-label { font-size: 13px; color: #666; margin-bottom: 5px; }
.stat-label.over { color: #c00; font-weight: 700; }
.stat-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
.stat-value.over { color: #c00; }
.stat-unit { font-size: 13px; font-weight: normal; margin-left: 4px; color: #666; }

/* ── 凡例 ── */
.legend-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 20px; }
.legend-group { display: flex; flex-direction: column; gap: 2px; align-items: flex-start; }
.legend-item {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 8px; font-size: 11px; border-radius: 2px;
  border: 1px solid rgba(0,0,0,0.12);
  max-width: 100%;
}
.leg-num   { font-weight: 700; min-width: 24px; }
.leg-code  { font-family: monospace; font-size: 10px; }
.leg-label { font-size: 10px; }

/* ── 台車グリッド全体 ── */
.trips-section { display: flex; flex-direction: column; gap: 10px; }

/* ──①②便ラッパー── */
.trip-wrapper { display: flex; flex-direction: column; gap: 3px; }
.trip-label-row { display: flex; }

.trip-label {
  min-width: 80px;
  min-height: 24px;
  background: white;
  color: #111;
  border: 1.5px solid #333;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 13px;
  border-radius: 3px;
  padding: 2px 10px;
  white-space: nowrap;
}

/* 7列×2行 / 列優先埋め */
.cart-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-template-rows: repeat(2, 64px);
  grid-auto-flow: column;
  gap: 3px;
}

/* ── ③④追加便 ── */
.extra-sections { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.extra-wrapper  { display: flex; flex-direction: column; gap: 3px; }
.extra-label-row { display: flex; }
.extra-label {
  min-width: 88px;
  min-height: 22px;
  background: white;
  color: #111;
  border: 1.5px solid #333;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 11px;
  text-align: center;
  border-radius: 3px;
  padding: 2px 10px;
}
.extra-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 56px);
  grid-auto-flow: column;
  gap: 3px;
}

/* ── セル共通 ── */
.cart-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2px;
  text-align: center;
  border-radius: 2px;
  gap: 1px;
}
.cart-cell.empty { background: #f2f2f2; border: 1px solid #ddd; }
.cell-num   { font-size: 10px; font-weight: 700; line-height: 1.2; }
.cell-type  { font-size: 11px; font-weight: 700; line-height: 1.2; }
.cell-model { font-size: 10px; line-height: 1.2; }

/* ── フッター ── */
.footer-summary { margin-top: 12px; font-size: 13px; color: #555; }
.footer-summary.over { color: #c00; font-weight: 600; }
.over-text { font-weight: 700; }
</style>
