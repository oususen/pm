<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">日次ミックス順序ボード（7品固定運転向け）</h1>
        <p class="helper-text">
          ライン内の当日順序をドラッグで並べ替え、優先度(=順序)として保存します。量産の定常順序はテンプレート化し、例外のみ当日差し込みできます。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn-secondary" @click="applyTemplate" :disabled="!lineId || !orders.length">テンプレ適用</button>
        <button class="btn-secondary" @click="saveTemplate" :disabled="!lineId || !orders.length">テンプレ保存</button>
        <button class="btn-primary" @click="saveSequence" :disabled="!dirty">順序を保存</button>
      </div>
    </div>

    <div class="filter-bar">
      <div class="filter-row">
        <div class="filter-field">
          <label>ライン</label>
          <select v-model="lineId">
            <option value="">選択してください</option>
            <option v-for="l in lines" :key="l.id" :value="l.id">
              {{ l.line_code }} - {{ l.line_name }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>対象日</label>
          <input type="date" v-model="targetDate" />
        </div>
        <div class="filter-field">
          <label>検索（品番/指示番号）</label>
          <input v-model="keyword" placeholder="例: YD60000441" />
        </div>
        <div class="filter-field">
          <label>固定7品（品番リスト）</label>
          <textarea
            v-model="fixedProductsText"
            rows="3"
            placeholder="1行1品番。未入力なら全件を表示"
          />
        </div>
        <div class="filter-actions">
          <button class="btn-primary" @click="fetchOrders" :disabled="!lineId">読み込み</button>
          <button class="btn-secondary" @click="resetFilters">リセット</button>
        </div>
      </div>
      <div class="pill-row">
        <span class="pill">対象ライン: {{ currentLineLabel }}</span>
        <span class="pill">日付: {{ targetDate }}</span>
        <span class="pill info">件数: {{ orderedOrders.length }}</span>
        <span class="pill warn" v-if="dirty">未保存の順序変更があります</span>
      </div>
    </div>

    <div class="lane-wrapper">
      <div class="lane-head">
        <div class="lane-title">当日シーケンス</div>
        <div class="lane-meta">
          <span>定常順序を維持しつつ、必要なロットだけ前後に差し込みます。</span>
        </div>
      </div>

      <div
        class="order-list"
        @dragover.prevent
        @drop.prevent="onDropToEnd"
      >
        <div
          v-for="(order, idx) in orderedOrders"
          :key="order.id"
          class="order-card"
          draggable="true"
          @dragstart="onDragStart(order.id)"
          @dragover.prevent
          @drop.prevent="onDrop(order.id)"
          :class="{
            highlight: isFixedProduct(order.product_code),
            ydHighlight: order.product_code === 'YD60000441'
          }"
        >
          <div class="order-left">
            <div class="seq-badge">#{{ idx + 1 }}</div>
            <div class="product-code">{{ order.product_code }}</div>
            <div class="product-name">{{ order.product_name }}</div>
            <div class="order-no">指示: {{ order.order_no }}</div>
          </div>
          <div class="order-right">
            <div class="meta-row">
              <span class="meta">数量 {{ formatNumber(order.order_qty) }}</span>
              <span class="meta">優先度 {{ order.priority ?? 0 }}</span>
              <span class="badge" :class="statusClass(order.status)">{{ order.status_display || order.status }}</span>
            </div>
            <div class="meta-row">
              <span class="meta">開始 {{ order.scheduled_start_date }}</span>
              <span class="meta">完了 {{ order.scheduled_end_date }}</span>
              <span class="meta warn" v-if="order.is_fixed">定常</span>
              <span class="meta accent" v-else>例外差し込み</span>
            </div>
          </div>
        </div>

        <div v-if="!orderedOrders.length" class="empty">
          ラインと日付を指定して読み込んでください。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import api from '@/api/client'

const hostBase = typeof window !== 'undefined' ? window.location.hostname : 'localhost'
const API_BASE = import.meta.env.VITE_API_BASE_URL || `http://${hostBase}:8000/api`

const buildBases = () => {
  const bases = [
    import.meta.env.VITE_API_BASE_URL,
    `http://${hostBase}:8000/api`,
    `http://${hostBase}:8081/api`,
    'http://localhost:8081/api',
    'http://localhost:8000/api',
  ].filter(Boolean)
  return Array.from(new Set(bases))
}

const prodOrderPath = '/production-orders/'

const lines = ref([])
const lineId = ref('')
const targetDate = ref(new Date().toISOString().slice(0, 10))
const orders = ref([])
const keyword = ref('')
const fixedProductsText = ref('YD60000441')
const draggingId = ref(null)
const originalOrderIds = ref([])

const orderedOrders = computed(() => {
  let data = [...orders.value]
  if (keyword.value) {
    const k = keyword.value.toLowerCase()
    data = data.filter((o) =>
      `${o.product_code}${o.product_name}${o.order_no}`.toLowerCase().includes(k)
    )
  }
  const fixedList = fixedProductList.value
  if (fixedList.length) {
    data = data.filter((o) => fixedList.includes(o.product_code))
  }
  return data.sort((a, b) => (a._seq ?? 0) - (b._seq ?? 0))
})

const fixedProductList = computed(() =>
  fixedProductsText.value
    .split('\n')
    .map((t) => t.trim())
    .filter(Boolean)
)

const currentLineLabel = computed(() => {
  const l = lines.value.find((x) => String(x.id) === String(lineId.value))
  return l ? `${l.line_code} - ${l.line_name}` : '未選択'
})

const dirty = computed(() => {
  const nowIds = orderedOrders.value.map((o) => o.id)
  return JSON.stringify(nowIds) !== JSON.stringify(originalOrderIds.value)
})

const statusClass = (status) => {
  const map = {
    PLANNED: 'badge-secondary',
    RELEASED: 'badge-primary',
    IN_PROGRESS: 'badge-warning',
    COMPLETED: 'badge-success',
    CANCELED: 'badge-danger'
  }
  return map[status] || 'badge-secondary'
}

const isFixedProduct = (code) => fixedProductList.value.includes(code)

const ensurePlaceholders = (data) => {
  const codes = new Set(data.map((o) => o.product_code))
  const missing = fixedProductList.value.filter((c) => !codes.has(c))
  if (!missing.length) return data
  const baseSeq = data.length
  const placeholders = missing.map((code, idx) => ({
    id: `local-${code}-${idx}`,
    product_code: code,
    product_name: '(プレースホルダ)',
    order_no: 'LOCAL-ONLY',
    status: 'PLANNED',
    status_display: 'プレースホルダ',
    order_qty: 0,
    scheduled_start_date: targetDate.value,
    scheduled_end_date: targetDate.value,
    _seq: baseSeq + idx + 1,
    is_fixed: true,
    is_local: true
  }))
  return [...data, ...placeholders]
}

const resetFilters = () => {
  keyword.value = ''
  fixedProductsText.value = 'YD60000441'
}

const fetchLines = async () => {
  // 1st: 既存APIクライアント（/lines/）
  try {
    const res = await api.lines.getLines()
    lines.value = res.data?.results || res.data || []
    if (Array.isArray(lines.value)) return
  } catch (e) {
    console.error('ライン取得エラー (client)', e)
  }

  // 2nd: /masters/lines/ へのフォールバック
  const bases = buildBases()
  for (const base of bases) {
    try {
      const res = await axios.get(`${base}/lines/`)
      lines.value = res.data?.results || res.data || []
      return
    } catch (e) {
      console.error(`ライン取得エラー (${base}/lines/)`, e)
    }
  }
  alert('ライン取得に失敗しました。VITE_API_BASE_URL をバックエンドに合わせて設定してください。')
}

const fetchOrders = async () => {
  if (!lineId.value) {
    alert('ラインを選択してください')
    return
  }
  const bases = buildBases()
  for (const base of bases) {
    try {
      const params = {
        line: lineId.value,
        scheduled_start_date_from: targetDate.value,
        scheduled_start_date_to: targetDate.value
      }
      const listRes = await axios.get(`${base}${prodOrderPath}`, { params })
      const items = listRes.data?.results || listRes.data || []
      // 詳細を付与（status_display等）
      const detailed = await Promise.all(
        items.map(async (item) => {
          try {
            const res = await axios.get(`${base}${prodOrderPath}${item.id}/`)
            return res.data?.results || res.data || item
          } catch {
            return item
          }
        })
      )
      // 初期順序: priority -> id
      let data = detailed.map((o, idx) => ({
        ...o,
        _seq: o.priority != null ? Number(o.priority) : idx + 1,
        is_fixed: true // 初期は定常扱い
      }))
      data = ensurePlaceholders(data)
      orders.value = data
      originalOrderIds.value = orderedOrders.value.map((o) => o.id)
      return
    } catch (e) {
      console.error(`製造指示取得エラー (${base})`, e)
    }
  }
  alert('データ取得に失敗しました')
}

const onDragStart = (id) => {
  draggingId.value = id
}

const reorder = (targetId = null) => {
  if (!draggingId.value) return
  const data = [...orderedOrders.value]
  const fromIdx = data.findIndex((o) => o.id === draggingId.value)
  if (fromIdx === -1) return
  const dragged = data.splice(fromIdx, 1)[0]

  if (targetId === null) {
    data.push(dragged)
  } else {
    const toIdx = data.findIndex((o) => o.id === targetId)
    data.splice(toIdx, 0, dragged)
  }

  data.forEach((o, idx) => {
    o._seq = idx + 1
    o.is_fixed = isFixedProduct(o.product_code)
  })
  orders.value = data
  draggingId.value = null
}

const onDrop = (targetId) => reorder(targetId)
const onDropToEnd = () => reorder(null)

const saveSequence = async () => {
  if (!dirty.value) {
    alert('変更はありません')
    return
  }
  try {
    const updates = orderedOrders.value
      .filter((o) => !String(o.id).startsWith('local-'))
      .map((o, idx) => ({
        id: o.id,
        priority: idx + 1,
        is_fixed: isFixedProduct(o.product_code)
      }))
    if (!updates.length) {
      alert('保存対象がありません（実データがありません）')
      return
    }
    // PATCHで優先度のみ更新
    const bases = buildBases()
    let saved = false
    for (const base of bases) {
      try {
        await Promise.all(
          updates.map((u) =>
            axios.patch(`${base}${prodOrderPath}${u.id}/`, { priority: u.priority })
          )
        )
        saved = true
        break
      } catch (e) {
        console.error(`保存エラー (${base})`, e)
      }
    }
    if (!saved) {
      alert('保存に失敗しました')
      return
    }
    // 例外差し込みは is_fixed=false として記憶だけ行う（保存後も表示に反映）
    orders.value = orderedOrders.value.map((o, idx) => ({
      ...o,
      priority: idx + 1,
      _seq: idx + 1,
      is_fixed: isFixedProduct(o.product_code)
    }))
    originalOrderIds.value = orderedOrders.value.map((o) => o.id)
    alert('順序を保存しました')
  } catch (e) {
    console.error('保存エラー', e)
    alert('保存に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

const templateKey = computed(() => `sequence-template-line-${lineId.value || 'none'}`)

const saveTemplate = () => {
  if (!lineId.value || !orderedOrders.value.length) {
    alert('ラインと順序を指定してください')
    return
  }
  const seq = orderedOrders.value.map((o) => o.product_code)
  localStorage.setItem(templateKey.value, JSON.stringify(seq))
  alert('テンプレートを保存しました')
}

const applyTemplate = () => {
  if (!lineId.value) {
    alert('ラインを選択してください')
    return
  }
  const raw = localStorage.getItem(templateKey.value)
  if (!raw) {
    alert('保存済みテンプレートがありません')
    return
  }
  const tpl = JSON.parse(raw)
  const data = [...orderedOrders.value]
  data.sort((a, b) => {
    const ia = tpl.indexOf(a.product_code)
    const ib = tpl.indexOf(b.product_code)
    if (ia === -1 && ib === -1) return 0
    if (ia === -1) return 1
    if (ib === -1) return -1
    return ia - ib
  })
  data.forEach((o, idx) => {
    o._seq = idx + 1
    o.is_fixed = isFixedProduct(o.product_code)
  })
  orders.value = data
}

const formatNumber = (v) => {
  if (v == null) return '0'
  return Number(v).toLocaleString('ja-JP', { maximumFractionDigits: 3 })
}

onMounted(() => {
  fetchLines()
})
</script>

<style scoped>
.page-container {
  padding: 12px;
  background: linear-gradient(135deg, #f3f6fb, #e8ecf5);
  color: #1d2742;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.page-title {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 800;
  color: #141b2f;
}
.helper-text {
  margin: 0;
  color: #4a5670;
}
.page-actions {
  display: flex;
  gap: 8px;
}
.filter-bar {
  background: #fff;
  border: 1px solid #d5ddeb;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 12px;
}
.filter-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}
.filter-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.filter-field input,
.filter-field select,
.filter-field textarea {
  padding: 8px;
  border: 1px solid #cfd7e6;
  border-radius: 6px;
  font-size: 14px;
}
.filter-actions {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
.pill-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.pill {
  background: #eef2fb;
  border: 1px solid #cfd7e6;
  padding: 6px 10px;
  border-radius: 16px;
  font-size: 12px;
}
.pill.info {
  background: #e7f5ff;
  border-color: #b5ddff;
}
.pill.warn {
  background: #fff4e5;
  border-color: #ffd8a8;
  color: #d9480f;
}
.lane-wrapper {
  background: #0f172a;
  border-radius: 12px;
  padding: 12px;
  color: #dce4ff;
  box-shadow: 0 10px 30px rgba(17, 24, 39, 0.24);
}
.lane-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.lane-title {
  font-size: 16px;
  font-weight: 700;
}
.lane-meta {
  color: #9fb3ff;
  font-size: 13px;
}
.order-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 260px;
}
.order-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px;
  background: #111a32;
  border: 1px solid #253154;
  border-radius: 10px;
  cursor: grab;
  transition: transform 0.08s ease, border-color 0.08s ease;
}
.order-card:hover {
  transform: translateY(-2px);
  border-color: #3b82f6;
}
.order-card.highlight {
  border-color: #6ee7b7;
  box-shadow: 0 0 0 1px #6ee7b7 inset;
}
.order-card.ydHighlight {
  border-color: #f97316;
  box-shadow: 0 0 0 1px #f97316 inset;
}
.order-left {
  display: grid;
  grid-template-columns: auto;
  gap: 4px;
  min-width: 220px;
}
.seq-badge {
  background: #1e293b;
  border: 1px solid #334155;
  padding: 4px 8px;
  border-radius: 8px;
  font-weight: 700;
  color: #e2e8f0;
  width: fit-content;
}
.product-code {
  font-weight: 700;
  font-size: 15px;
  color: #fff;
}
.product-name {
  color: #cdd7f3;
  font-size: 13px;
}
.order-no {
  color: #94a3b8;
  font-size: 12px;
}
.order-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.meta-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.meta {
  font-size: 13px;
  color: #cbd5f5;
}
.meta.warn {
  color: #fbbf24;
}
.meta.accent {
  color: #60a5fa;
}
.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}
.badge-secondary {
  background: #e2e8f0;
}
.badge-primary {
  background: #bfdbfe;
}
.badge-warning {
  background: #fef08a;
}
.badge-success {
  background: #bbf7d0;
}
.badge-danger {
  background: #fecdd3;
}
.btn-primary,
.btn-secondary {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  background: #fff;
  cursor: pointer;
  font-weight: 700;
}
.btn-primary {
  background: #2563eb;
  border-color: #1d4ed8;
  color: #fff;
}
.btn-secondary:hover,
.btn-primary:hover {
  opacity: 0.92;
}
.empty {
  padding: 20px;
  text-align: center;
  color: #94a3b8;
}

@media (max-width: 720px) {
  .page-header {
    flex-direction: column;
  }
  .order-card {
    flex-direction: column;
  }
}
</style>
