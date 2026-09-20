<template>
  <div class="m-page">
    <!-- ヘッダー -->
    <div class="m-header">
      <div class="m-title">検収 <span class="m-badge">スマホ</span></div>
      <select v-model="selectedSupplier" @change="onSupplierChange" class="m-select">
        <option value="">-- 仕入先 --</option>
        <option v-for="s in suppliers" :key="s.id" :value="s.id">
          {{ s.supplier_code }} {{ s.supplier_name }}
        </option>
      </select>
      <div class="m-header-row">
        <input type="date" v-model="targetDate" @change="onTargetDateChange" class="m-date" />
        <button class="m-btn primary" @click="loadData" :disabled="!selectedSupplier || loading">取得</button>
      </div>
    </div>

    <!-- タブ -->
    <div class="m-tabs">
      <button :class="['m-tab', { active: activeTab === 'progress' }]" @click="activeTab = 'progress'; loadData()">進度方式</button>
      <button :class="['m-tab', { active: activeTab === 'delivery_list' }]" @click="activeTab = 'delivery_list'; loadData()">納入リスト</button>
    </div>

    <!-- サマリーバー -->
    <div v-if="currentRows.length" class="m-summary">
      <div class="m-summary-item">
        <span class="m-summary-num">{{ currentRows.length }}</span>
        <span class="m-summary-label">全件</span>
      </div>
      <div class="m-summary-item">
        <span class="m-summary-num done">{{ receivedCount }}</span>
        <span class="m-summary-label">検収済</span>
      </div>
      <div class="m-summary-item">
        <span class="m-summary-num pending">{{ pendingCount }}</span>
        <span class="m-summary-label">未検収</span>
      </div>
    </div>

    <!-- フィルタ（折りたたみ） -->
    <div v-if="currentRows.length" class="m-filter-toggle" @click="showFilter = !showFilter">
      フィルタ {{ showFilter ? '▲' : '▼' }}
      <span v-if="hasActiveFilter" class="m-filter-active">ON</span>
    </div>
    <div v-if="showFilter && currentRows.length" class="m-filter">
      <input v-model="filterCode" class="m-filter-input" placeholder="品番検索" />
      <div class="m-filter-row">
        <label class="m-filter-label">移動先:</label>
        <select v-model="filterDest" class="m-filter-select">
          <option value="">すべて</option>
          <option v-for="o in destOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
      </div>
      <div class="m-filter-btns">
        <span class="m-filter-label">G:</span>
        <button :class="['m-fbtn', { active: filterG === '' }]" @click="filterG = ''">全</button>
        <button :class="['m-fbtn', { active: filterG === 'yes' }]" @click="filterG = 'yes'">有</button>
        <button :class="['m-fbtn', { active: filterG === 'no' }]" @click="filterG = 'no'">無</button>
      </div>
      <div class="m-filter-btns">
        <span class="m-filter-label">数変更:</span>
        <button :class="['m-fbtn', { active: filterHeld === '' }]" @click="filterHeld = ''">全</button>
        <button :class="['m-fbtn', { active: filterHeld === 'yes' }]" @click="filterHeld = 'yes'">有</button>
        <button :class="['m-fbtn', { active: filterHeld === 'no' }]" @click="filterHeld = 'no'">無</button>
      </div>
      <div class="m-filter-btns">
        <span class="m-filter-label">差異:</span>
        <button :class="['m-fbtn', { active: filterDiff === '' }]" @click="filterDiff = ''">全</button>
        <button :class="['m-fbtn', { active: filterDiff === 'yes' }]" @click="filterDiff = 'yes'">有</button>
        <button :class="['m-fbtn', { active: filterDiff === 'no' }]" @click="filterDiff = 'no'">無</button>
      </div>
      <div class="m-filter-btns">
        <span class="m-filter-label">実績:</span>
        <button :class="['m-fbtn', { active: filterActual === '' }]" @click="filterActual = ''">全</button>
        <button :class="['m-fbtn', { active: filterActual === 'yes' }]" @click="filterActual = 'yes'">有</button>
        <button :class="['m-fbtn', { active: filterActual === 'no' }]" @click="filterActual = 'no'">無</button>
      </div>
    </div>

    <!-- 読み込み中 -->
    <div v-if="loading" class="m-loading">読み込み中...</div>

    <!-- カード一覧 -->
    <div v-if="!loading && filteredRows.length" class="m-cards">
      <div
        v-for="row in filteredRows"
        :key="row.product_id"
        :ref="(el) => { if (el) cardRefs[row.product_code] = el }"
        :class="['m-card', {
          'card-done': isReceived(row),
          'card-held': row.held,
          'card-highlight': highlightCode === row.product_code,
        }]"
      >
        <div class="m-card-head">
          <div class="m-card-code">{{ row.product_code }}</div>
          <span v-if="isReceived(row)" class="m-badge-done">検収済</span>
          <span v-else-if="row.held" class="m-badge-held">保留</span>
        </div>
        <div class="m-card-name">{{ row.product_name }}</div>

        <div class="m-card-nums">
          <div class="m-num-col">
            <span class="m-num-label">予定</span>
            <span class="m-num-val">{{ row.expected_qty }}</span>
          </div>
          <div class="m-num-col">
            <span class="m-num-label">実績</span>
            <span class="m-num-val actual">{{ row.actual_qty || 0 }}</span>
          </div>
          <div class="m-num-col">
            <span class="m-num-label">差異</span>
            <span :class="['m-num-val', diffClass(row)]">{{ diffVal(row) }}</span>
          </div>
        </div>

        <template v-if="!isReceived(row)">
          <div class="m-card-input-row">
            <label class="m-input-label">実数</label>
            <input
              type="number"
              v-model.number="row.received_qty"
              min="0"
              class="m-input-qty"
              :class="{ 'qty-changed': row.split || row.held }"
              :readonly="!row.held"
              inputmode="numeric"
            />
          </div>
          <div class="m-card-input-row">
            <label class="m-input-label">備考</label>
            <input v-model="row.note" class="m-input-note" />
          </div>
          <div class="m-card-actions">
            <button
              v-if="!row.held"
              class="m-btn success m-btn-receive"
              @click="receiveSingle(row)"
              :disabled="saving"
            >検収</button>
            <button
              v-if="!row.held"
              class="m-btn split"
              @click="promptSplit(row)"
            >分割</button>
            <button
              class="m-btn hold"
              :class="{ active: row.held }"
              @click="toggleHold(row)"
            >{{ row.held ? '保留解除' : '数変更' }}</button>
            <button
              v-if="row.held"
              class="m-btn danger"
              :class="{ active: row.non_delivery }"
              @click="toggleNonDelivery(row)"
            >未納</button>
            <button
              v-if="row.held"
              class="m-btn success m-btn-receive"
              @click="receiveSingle(row)"
              :disabled="saving"
            >検収</button>
          </div>
        </template>
      </div>
    </div>

    <div v-if="!loading && selectedSupplier && !currentRows.length" class="m-empty">
      納入予定データがありません
    </div>

    <!-- QRスキャンボタン（フローティング） -->
    <button v-if="currentRows.length && !showScanner" class="m-fab" @click="openScanner">
      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    </button>

    <!-- QRスキャナモーダル -->
    <div v-if="showScanner" class="m-scanner-overlay" @click.self="closeScanner">
      <div class="m-scanner-modal">
        <div class="m-scanner-header">
          <span>QRスキャン</span>
          <button class="m-scanner-close" @click="closeScanner">&times;</button>
        </div>
        <div class="m-scanner-body">
          <video ref="videoRef" class="m-scanner-video" playsinline autoplay></video>
          <canvas ref="canvasRef" class="m-scanner-canvas"></canvas>
          <div class="m-scanner-guide"></div>
        </div>
        <div v-if="scanResult" class="m-scanner-result">
          <span class="m-scanner-result-code">{{ scanResult.code }}</span>
          <span class="m-scanner-result-qty">数量: {{ scanResult.qty }}</span>
        </div>
        <div v-if="scanError" class="m-scanner-error">{{ scanError }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, nextTick } from 'vue'
import jsQR from 'jsqr'
import api from '@/api/client'

const suppliers = ref([])
const selectedSupplier = ref('')
const today = new Date()
const targetDate = ref(
  `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
)
const activeTab = ref('delivery_list')
const loading = ref(false)
const saving = ref(false)

const rows = ref([])
const deliveryListRows = ref([])
const filterCode = ref('')
const filterG = ref('')
const filterDest = ref('')
const filterHeld = ref('')
const filterDiff = ref('')
const filterActual = ref('')
const showFilter = ref(false)
const highlightCode = ref('')
const cardRefs = ref({})

const currentRows = computed(() => activeTab.value === 'progress' ? rows.value : deliveryListRows.value)

const isReceived = (r) => !r._manual && r.actual_qty && r.actual_qty >= r.expected_qty

const receivedCount = computed(() => currentRows.value.filter(isReceived).length)
const pendingCount = computed(() => currentRows.value.filter((r) => !isReceived(r)).length)
const hasActiveFilter = computed(() => filterCode.value || filterG.value || filterDest.value || filterHeld.value || filterDiff.value || filterActual.value)

const destOptions = computed(() => {
  const set = new Set()
  for (const r of currentRows.value) if (r.transfer_destination) set.add(r.transfer_destination)
  return [...set].sort().map((k) => ({
    value: k,
    label: currentRows.value.find((r) => r.transfer_destination === k)?.transfer_destination_label || k,
  }))
})

const filteredRows = computed(() => {
  return currentRows.value.filter((r) => {
    if (filterCode.value && !r.product_code.toUpperCase().includes(filterCode.value.toUpperCase())) return false
    if (filterDest.value && r.transfer_destination !== filterDest.value) return false
    if (filterG.value === 'yes' && !r.product_code.endsWith('G')) return false
    if (filterG.value === 'no' && r.product_code.endsWith('G')) return false
    if (filterHeld.value === 'yes' && !r.held) return false
    if (filterHeld.value === 'no' && r.held) return false
    if (filterDiff.value === 'yes' && r.actual_qty && r.actual_qty === r.expected_qty) return false
    if (filterDiff.value === 'no' && (!r.actual_qty || r.actual_qty !== r.expected_qty)) return false
    if (filterActual.value === 'yes' && !r.actual_qty) return false
    if (filterActual.value === 'no' && r.actual_qty) return false
    return true
  })
})

const diffVal = (row) => {
  if (!row.actual_qty) return ''
  return row.expected_qty - row.actual_qty
}
const diffClass = (row) => {
  const d = diffVal(row)
  if (d === '') return ''
  if (d > 0) return 'diff-short'
  if (d < 0) return 'diff-over'
  return ''
}

const getDefaultGFilter = () => {
  const supplier = suppliers.value.find((s) => s.id === selectedSupplier.value)
  if (!supplier) return ''
  if (supplier.supplier_type === 'outsource') return 'yes'
  if (supplier.supplier_type === 'purchase') return 'no'
  return ''
}

const fetchSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = (res.data.results || res.data || []).sort((a, b) =>
    (a.supplier_code || '').localeCompare(b.supplier_code || '')
  )
}

const onSupplierChange = () => {
  rows.value = []
  deliveryListRows.value = []
  filterCode.value = ''
  filterG.value = getDefaultGFilter()
  filterDest.value = ''
  filterHeld.value = ''
  filterDiff.value = ''
  filterActual.value = ''
  if (selectedSupplier.value) loadData()
}

const onTargetDateChange = () => {
  if (selectedSupplier.value) loadData()
}

const loadData = async () => {
  if (!selectedSupplier.value) return
  if (activeTab.value === 'progress') await loadProgressData()
  else await loadDeliveryListData()
}

const loadProgressData = async () => {
  loading.value = true
  rows.value = []
  try {
    const res = await api.client.get('/purchase-receiving/', {
      params: {
        supplier_id: selectedSupplier.value,
        target_date: targetDate.value,
        basis: 'progress',
      },
    })
    const data = res.data
    rows.value = (data.items || []).map((item) => ({
      ...item,
      received_qty: Math.max(0, (item.expected_qty || 0) - (item.actual_qty || 0)),
      held: false,
      split: false,
      confirmed: false,
      note: item.product_code || '',
    }))
  } catch {
    alert('データの取得に失敗しました。')
  } finally {
    loading.value = false
  }
}

const loadDeliveryListData = async () => {
  loading.value = true
  deliveryListRows.value = []
  try {
    const res = await api.client.get('/purchase-delivery-schedules/', {
      params: { supplier_id: selectedSupplier.value, target_date: targetDate.value },
    })
    deliveryListRows.value = (res.data.items || []).map((r) => ({
      ...r,
      received_qty: Math.max(0, (r.expected_qty || 0) - (r.actual_qty || 0)),
      held: false,
      split: false,
      confirmed: false,
      note: r.product_code || '',
    }))
  } catch {
    alert('データの取得に失敗しました。')
  } finally {
    loading.value = false
  }
}

const receiveSingle = async (row) => {
  if (row.held && Number(row.received_qty) === 0 && !row.non_delivery) {
    if (!confirm('数量0で検収しますか？')) return
  }
  saving.value = true
  try {
    await api.client.post('/purchase-receiving/', {
      supplier_id: selectedSupplier.value,
      target_date: targetDate.value,
      source: 'PURCHASE_RECEIVING_MOBILE',
      items: [{
        product_id: row.product_id,
        expected_qty: row.expected_qty,
        received_qty: row.received_qty,
        note: row.note || '',
        non_delivery: !!row.non_delivery,
      }],
    })
    row.actual_qty = (row.actual_qty || 0) + Number(row.received_qty)
    row.received_qty = Math.max(0, (row.expected_qty || 0) - row.actual_qty)
    row.held = false
    row.split = false
    row.non_delivery = false
  } catch (err) {
    const data = err.response?.data
    const detail = data?.detail || (typeof data === 'string' ? data : JSON.stringify(data))
    alert(`検収に失敗しました。\n${detail || err.message}`)
  } finally {
    saving.value = false
  }
}

const promptSplit = (row) => {
  const remaining = Math.max(0, (row.expected_qty || 0) - (row.actual_qty || 0))
  const input = prompt(`今回の入荷数を入力（残数: ${remaining}）`, remaining)
  if (input === null) return
  const val = Number(input)
  if (isNaN(val) || val < 0) { alert('数値を入力してください'); return }
  row.received_qty = val
  row.split = true
}

const toggleHold = (row) => {
  row.held = !row.held
  row.split = false
  if (row.held) {
    row.received_qty = 0
  } else {
    row.received_qty = Math.max(0, (row.expected_qty || 0) - (row.actual_qty || 0))
    row.non_delivery = false
  }
}

const toggleNonDelivery = (row) => {
  row.non_delivery = !row.non_delivery
  if (row.non_delivery) {
    row.received_qty = 0
    row.note = '未納'
  } else {
    row.note = row.product_code || ''
  }
}

// === QRスキャナ ===
const showScanner = ref(false)
const videoRef = ref(null)
const canvasRef = ref(null)
const scanResult = ref(null)
const scanError = ref('')
let scanStream = null
let scanAnimFrame = null

const openScanner = async () => {
  showScanner.value = true
  scanResult.value = null
  scanError.value = ''
  await nextTick()
  try {
    scanStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } },
    })
    videoRef.value.srcObject = scanStream
    videoRef.value.play()
    requestScanFrame()
  } catch {
    scanError.value = 'カメラを起動できません。カメラの権限を確認してください。'
  }
}

const closeScanner = () => {
  showScanner.value = false
  stopScan()
}

const stopScan = () => {
  if (scanAnimFrame) { cancelAnimationFrame(scanAnimFrame); scanAnimFrame = null }
  if (scanStream) { scanStream.getTracks().forEach((t) => t.stop()); scanStream = null }
}

const requestScanFrame = () => {
  scanAnimFrame = requestAnimationFrame(scanFrame)
}

const scanFrame = () => {
  if (!showScanner.value || !videoRef.value || !canvasRef.value) return
  const video = videoRef.value
  if (video.readyState < video.HAVE_ENOUGH_DATA) { requestScanFrame(); return }

  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
  const code = jsQR(imageData.data, canvas.width, canvas.height)

  if (code) {
    handleQRResult(code.data)
  } else {
    requestScanFrame()
  }
}

const handleQRResult = (data) => {
  const parts = data.split(',')
  if (parts.length < 3) {
    scanError.value = `不明なQR: ${data}`
    requestScanFrame()
    return
  }
  const productCode = parts[0]
  const qty = parseInt(parts[2], 10)

  scanResult.value = { code: productCode, qty }
  scanError.value = ''

  const row = currentRows.value.find((r) => r.product_code === productCode)
  if (row) {
    if (!isReceived(row)) {
      row.received_qty = qty
    }
    closeScanner()
    scrollToCard(productCode)
  } else {
    scanError.value = `${productCode} はリストにありません`
    setTimeout(() => { scanError.value = ''; requestScanFrame() }, 2000)
  }
}

const scrollToCard = async (code) => {
  highlightCode.value = code
  await nextTick()
  const el = cardRefs.value[code]
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  setTimeout(() => { highlightCode.value = '' }, 2500)
}

onMounted(fetchSuppliers)
onUnmounted(stopScan)
</script>

<style scoped>
.m-page {
  min-height: 100dvh;
  background: #f1f5f9;
  padding-bottom: 80px;
}

/* ヘッダー */
.m-header {
  background: #1e293b;
  color: #fff;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.m-title {
  font-size: 18px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 8px;
}
.m-badge {
  font-size: 10px;
  font-weight: 700;
  background: #3b82f6;
  padding: 2px 8px;
  border-radius: 10px;
}
.m-select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: none;
  font-size: 15px;
  background: #334155;
  color: #fff;
}
.m-select option { background: #1e293b; }
.m-header-row {
  display: flex;
  gap: 8px;
}
.m-date {
  flex: 1;
  padding: 10px 12px;
  border-radius: 8px;
  border: none;
  font-size: 15px;
  background: #334155;
  color: #fff;
  color-scheme: dark;
}

/* タブ */
.m-tabs {
  display: flex;
  background: #e2e8f0;
}
.m-tab {
  flex: 1;
  padding: 10px;
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all .2s;
}
.m-tab.active {
  background: #fff;
  color: #1e293b;
  box-shadow: 0 -2px 0 #3b82f6 inset;
}

/* ボタン共通 */
.m-btn {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: opacity .2s;
}
.m-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.m-btn.primary { background: #3b82f6; color: #fff; }
.m-btn.success { background: #16a34a; color: #fff; }
.m-btn.danger { background: #dc2626; color: #fff; }
.m-btn.danger.active { background: #991b1b; }
.m-btn.split { background: #3b82f6; color: #fff; }
.m-btn.split.active { background: #2563eb; }
.m-btn.hold { background: #f59e0b; color: #fff; }
.m-btn.hold.active { background: #d97706; }

/* サマリー */
.m-summary {
  display: flex;
  gap: 1px;
  background: #e2e8f0;
  margin: 0;
}
.m-summary-item {
  flex: 1;
  background: #fff;
  padding: 10px 0;
  text-align: center;
}
.m-summary-num {
  display: block;
  font-size: 22px;
  font-weight: 800;
  color: #1e293b;
}
.m-summary-num.done { color: #16a34a; }
.m-summary-num.pending { color: #ea580c; }
.m-summary-label {
  font-size: 11px;
  color: #64748b;
}

/* フィルタ */
.m-filter-toggle {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
}
.m-filter-active {
  font-size: 10px;
  background: #3b82f6;
  color: #fff;
  padding: 1px 6px;
  border-radius: 8px;
}
.m-filter {
  background: #fff;
  padding: 10px 16px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.m-filter-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
}
.m-filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.m-filter-select {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
}
.m-filter-btns {
  display: flex;
  align-items: center;
  gap: 4px;
}
.m-filter-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  min-width: 36px;
}
.m-fbtn {
  padding: 6px 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
}
.m-fbtn.active {
  background: #3b82f6;
  color: #fff;
  border-color: #3b82f6;
}

/* 読み込み */
.m-loading, .m-empty {
  padding: 40px 16px;
  text-align: center;
  font-size: 14px;
  color: #94a3b8;
}

/* カード一覧 */
.m-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 12px;
}

.m-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
  padding: 14px 16px;
  transition: box-shadow .3s, border-color .3s;
  border: 2px solid transparent;
}
.m-card.card-done {
  background: #f0fdf4;
  opacity: 0.7;
}
.m-card.card-held {
  border-color: #f59e0b;
  background: #fffbeb;
}
.m-card.card-highlight {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,.3);
  animation: card-flash .6s ease-in-out 3;
}
@keyframes card-flash {
  0%, 100% { box-shadow: 0 0 0 3px rgba(59,130,246,.3); }
  50% { box-shadow: 0 0 0 6px rgba(59,130,246,.15); }
}

.m-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2px;
}
.m-card-code {
  font-size: 16px;
  font-weight: 800;
  color: #1e293b;
}
.m-card-name {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 10px;
}
.m-badge-done {
  font-size: 11px;
  font-weight: 700;
  background: #dcfce7;
  color: #166534;
  padding: 2px 10px;
  border-radius: 10px;
}
.m-badge-held {
  font-size: 11px;
  font-weight: 700;
  background: #fef3c7;
  color: #92400e;
  padding: 2px 10px;
  border-radius: 10px;
}

.m-card-nums {
  display: flex;
  gap: 1px;
  background: #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
}
.m-num-col {
  flex: 1;
  background: #f8fafc;
  padding: 6px 0;
  text-align: center;
}
.m-num-label {
  display: block;
  font-size: 10px;
  color: #94a3b8;
  font-weight: 600;
}
.m-num-val {
  display: block;
  font-size: 18px;
  font-weight: 800;
  color: #1e293b;
}
.m-num-val.actual { color: #2563eb; }
.m-num-val.diff-short { color: #dc2626; }
.m-num-val.diff-over { color: #2563eb; }

.m-card-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.m-input-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  min-width: 36px;
}
.m-input-qty {
  flex: 1;
  padding: 10px 12px;
  border: 2px solid #d1d5db;
  border-radius: 8px;
  font-size: 20px;
  font-weight: 700;
  text-align: right;
  color: #1e293b;
  inputmode: numeric;
}
.m-input-qty[readonly] {
  background: #f8fafc;
  color: #1e293b;
  border-color: #e2e8f0;
}
.m-input-qty.qty-changed {
  background: #fffbeb;
  border-color: #f59e0b;
  color: #92400e;
}
.m-input-note {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
}

.m-card-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.m-btn-receive { flex: 1; }

/* QRスキャンFAB */
.m-fab {
  position: fixed;
  bottom: 24px;
  right: 20px;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: #3b82f6;
  color: #fff;
  border: none;
  box-shadow: 0 4px 16px rgba(59,130,246,.4);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  transition: transform .2s;
}
.m-fab:active { transform: scale(0.9); }

/* スキャナモーダル */
.m-scanner-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.85);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}
.m-scanner-modal {
  width: 92vw;
  max-width: 400px;
  background: #1e293b;
  border-radius: 16px;
  overflow: hidden;
}
.m-scanner-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
}
.m-scanner-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 28px;
  cursor: pointer;
}
.m-scanner-body {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  overflow: hidden;
  background: #000;
}
.m-scanner-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.m-scanner-canvas {
  display: none;
}
.m-scanner-guide {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 200px;
  height: 200px;
  border: 3px solid rgba(59,130,246,.7);
  border-radius: 16px;
  box-shadow: 0 0 0 9999px rgba(0,0,0,.3);
}
.m-scanner-result {
  padding: 12px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #fff;
}
.m-scanner-result-code {
  font-size: 16px;
  font-weight: 700;
}
.m-scanner-result-qty {
  font-size: 14px;
  color: #94a3b8;
}
.m-scanner-error {
  padding: 10px 18px;
  font-size: 13px;
  color: #f87171;
  text-align: center;
}
</style>
