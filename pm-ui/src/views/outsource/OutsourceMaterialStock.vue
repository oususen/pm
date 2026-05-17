<template>
  <div class="page-container">
    <h2 class="page-title">材料在庫</h2>

    <div class="tab-row">
      <button class="tab-btn" :class="{ active: tab === 'list' }" @click="tab = 'list'">在庫一覧</button>
      <button class="tab-btn" :class="{ active: tab === 'adjust' }" @click="tab = 'adjust'">在庫調整</button>
    </div>

    <div v-if="tab === 'list'">
      <div class="prepare-form">
        <label>
          <span class="field-label">検索</span>
          <input v-model="filters.keyword" class="input input-lg" placeholder="材料コード・材料名" />
        </label>
        <label>
          <span class="field-label">調達先</span>
          <select v-model="filters.supplier_name" class="input">
            <option value="">全調達先</option>
            <option v-for="s in supplierOptions" :key="s" :value="s">{{ s }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">区分</span>
          <select v-model="filters.tx_type" class="input">
            <option value="">全区分</option>
            <option value="RECEIPT">入庫</option>
            <option value="ISSUE">出庫</option>
            <option value="ADJUST">棚卸調整</option>
          </select>
        </label>
        <label>
          <span class="field-label">開始日</span>
          <input v-model="filters.date_from" type="date" class="input" />
        </label>
        <label>
          <span class="field-label">終了日</span>
          <input v-model="filters.date_to" type="date" class="input" />
        </label>
      </div>

      <div class="section">
        <h3>現在庫（総量）</h3>
        <table v-if="filteredSummary.length" class="data-table">
          <thead><tr><th>材料コード</th><th>材料名称</th><th>現在庫(個)</th></tr></thead>
          <tbody>
            <tr v-for="s in filteredSummary" :key="s.material_code">
              <td>{{ s.material_code }}</td>
              <td>{{ s.material_name || '-' }}</td>
              <td class="text-right" :class="{ neg: Number(s.stock_qty) < 0 }">{{ s.stock_qty }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">在庫データがありません</div>
      </div>

      <div class="section">
        <h3>在庫履歴</h3>
        <table v-if="filteredTxList.length" class="data-table">
          <thead><tr><th>日付</th><th>区分</th><th>材料コード</th><th>材料名称</th><th>増減(個)</th><th>理由</th></tr></thead>
          <tbody>
            <tr v-for="t in filteredTxList" :key="t.id">
              <td>{{ t.tx_date }}</td>
              <td>{{ txLabel(t.tx_type) }}</td>
              <td>{{ t.material_code }}</td>
              <td>{{ t.material_name || '-' }}</td>
              <td class="text-right" :class="{ pos: Number(t.qty_change) > 0, neg: Number(t.qty_change) < 0 }">{{ t.qty_change }}</td>
              <td>{{ t.reason || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">履歴がありません</div>
      </div>
    </div>

    <div v-else class="section">
      <h3>棚卸調整</h3>
      <div class="subtab-row">
        <button class="tab-btn" :class="{ active: adjustMode === 'single' }" @click="adjustMode = 'single'">個別</button>
        <button class="tab-btn" :class="{ active: adjustMode === 'batch' }" @click="adjustMode = 'batch'">一括</button>
      </div>

      <div class="prepare-form">
        <label>
          <span class="field-label">検索</span>
          <input v-model="adjustFilters.keyword" class="input input-lg" placeholder="材料コード・材料名（調整用）" />
        </label>
        <label>
          <span class="field-label">調達先</span>
          <select v-model="adjustFilters.supplier_name" class="input">
            <option value="">全調達先</option>
            <option v-for="s in supplierOptions" :key="`adj-${s}`" :value="s">{{ s }}</option>
          </select>
        </label>
      </div>

      <div v-if="adjustMode === 'single'" class="prepare-form single-form">
        <label>
          <span class="field-label">品目選択</span>
          <select v-model="adjust.material_code" class="input input-lg" @change="onSelectSingleMaterial">
            <option value="">材料選択</option>
            <option v-for="m in filteredMasterRows" :key="`m-${m.material_code}`" :value="m.material_code">
              {{ m.material_code }} | {{ m.material_name || '-' }}
            </option>
          </select>
        </label>
        <label>
          <span class="field-label">材料名称</span>
          <input v-model="adjust.material_name" class="input input-lg" placeholder="材料名称" />
        </label>
        <label>
          <span class="field-label">現在庫数</span>
          <input :value="singleCurrentStock" class="input input-xs" readonly />
        </label>
        <label>
          <span class="field-label">増減数</span>
          <input v-model.number="adjust.qty_change" type="number" class="input input-xs" placeholder="個" />
        </label>
        <label>
          <span class="field-label">日付</span>
          <input v-model="adjust.tx_date" type="date" class="input" />
        </label>
        <label>
          <span class="field-label">理由</span>
          <input v-model="adjust.reason" class="input input-lg" placeholder="棚卸調整理由（必須）" />
        </label>
        <button class="btn-primary compact-btn" @click="createAdjust">調整登録</button>
      </div>

      <div v-else>
        <div class="prepare-form">
          <label>
            <span class="field-label">理由</span>
            <input v-model="batchReason" class="input input-lg" placeholder="棚卸調整理由（必須）" />
          </label>
          <label>
            <span class="field-label">日付</span>
            <input v-model="batchDate" type="date" class="input" />
          </label>
          <button class="btn-primary" @click="saveBatchAdjust">選択行を一括登録</button>
        </div>
        <table v-if="filteredMasterRows.length" class="data-table">
          <thead><tr><th><input type="checkbox" :checked="isAllChecked" @change="toggleAll" /></th><th>材料コード</th><th>材料名称</th><th>現在庫(個)</th><th>調整量(個)</th></tr></thead>
          <tbody>
            <tr v-for="m in filteredMasterRows" :key="`b-${m.material_code}`">
              <td class="text-center"><input type="checkbox" :checked="isChecked(m.material_code)" @change="toggleOne(m.material_code, $event)" /></td>
              <td>{{ m.material_code }}</td>
              <td>{{ m.material_name || '-' }}</td>
              <td class="text-right" :class="{ neg: Number(m.stock_qty) < 0 }">{{ m.stock_qty }}</td>
              <td><input v-model.number="batchQtyMap[m.material_code]" type="number" class="input input-sm" placeholder="0以外" /></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">材料マスタがありません</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

function formatLocalDate(date = new Date()) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const summary = ref([])
const txList = ref([])
const materialMasterList = ref([])
const tab = ref('list')
const adjustMode = ref('single')
const filters = ref({
  keyword: '',
  supplier_name: '',
  tx_type: '',
  date_from: '',
  date_to: '',
})
const adjustFilters = ref({
  keyword: '',
  supplier_name: '',
})
const adjust = ref({
  material_code: '',
  material_name: '',
  qty_change: null,
  tx_date: formatLocalDate(),
  reason: '',
})
const batchChecked = ref([])
const batchQtyMap = ref({})
const batchDate = ref(formatLocalDate())
const batchReason = ref('')

const TX_MAP = { RECEIPT: '入庫', ISSUE: '出庫', ADJUST: '棚卸調整' }
function txLabel(t) { return TX_MAP[t] || t }
function normalizeSearchText(v) {
  return String(v || '')
    .toLowerCase()
    .replace(/[－ー―‐]/g, '-')
    .replace(/\s+/g, '')
}

const stockMap = computed(() => {
  const m = {}
  for (const s of summary.value) m[s.material_code] = Number(s.stock_qty || 0)
  return m
})

const masterRows = computed(() => materialMasterList.value.map((m) => ({
  material_code: m.material_code,
  material_name: m.material_name || '',
  supplier_name: m.supplier_name || '',
  stock_qty: stockMap.value[m.material_code] ?? 0,
})))

const supplierOptions = computed(() => {
  const set = new Set(materialMasterList.value.map((m) => (m.supplier_name || '').trim()).filter(Boolean))
  return Array.from(set).sort((a, b) => a.localeCompare(b))
})

const filteredMasterRows = computed(() => {
  const kw = normalizeSearchText(adjustFilters.value.keyword)
  return masterRows.value.filter((r) => {
    if (
      adjustFilters.value.supplier_name &&
      (r.supplier_name || '').trim() !== adjustFilters.value.supplier_name.trim()
    ) return false
    if (!kw) return true
    return (
      normalizeSearchText(r.material_code).includes(kw) ||
      normalizeSearchText(r.material_name).includes(kw)
    )
  })
})

const filteredSummary = computed(() => {
  const kw = filters.value.keyword.trim().toLowerCase()
  return summary.value.filter((r) => {
    const m = materialMasterList.value.find((x) => x.material_code === r.material_code)
    if (filters.value.supplier_name && (m?.supplier_name || '') !== filters.value.supplier_name) return false
    if (!kw) return true
    return (
      (r.material_code || '').toLowerCase().includes(kw) ||
      (r.material_name || '').toLowerCase().includes(kw)
    )
  })
})

const filteredTxList = computed(() => {
  const kw = filters.value.keyword.trim().toLowerCase()
  return txList.value.filter((r) => {
    const m = materialMasterList.value.find((x) => x.material_code === r.material_code)
    if (filters.value.supplier_name && (m?.supplier_name || '') !== filters.value.supplier_name) return false
    if (filters.value.tx_type && r.tx_type !== filters.value.tx_type) return false
    if (filters.value.date_from && r.tx_date < filters.value.date_from) return false
    if (filters.value.date_to && r.tx_date > filters.value.date_to) return false
    if (!kw) return true
    return (
      (r.material_code || '').toLowerCase().includes(kw) ||
      (r.material_name || '').toLowerCase().includes(kw)
    )
  })
})

const singleCurrentStock = computed(() => {
  if (!adjust.value.material_code) return 0
  return stockMap.value[adjust.value.material_code] ?? 0
})

async function fetchSummary() {
  const res = await api.outsource.getMaterialStockSummary()
  summary.value = res.data || []
}

async function fetchTx() {
  const res = await api.outsource.getMaterialStockTx({ ordering: '-tx_date' })
  txList.value = res.data.results || res.data
}

async function fetchMaterialMaster() {
  const all = []
  let page = 1
  while (true) {
    const res = await api.outsource.getComponentMaterials({ page, page_size: 200 })
    const data = res.data
    if (Array.isArray(data)) {
      materialMasterList.value = data
      return
    }
    all.push(...(data.results || []))
    if (!data.next) break
    page += 1
  }
  materialMasterList.value = all
}

async function createAdjust() {
  if (!adjust.value.material_code || !adjust.value.qty_change || !adjust.value.reason) {
    alert('材料コード・増減数・理由を入力してください')
    return
  }
  await api.outsource.createMaterialStockAdjust(adjust.value)
  adjust.value.qty_change = null
  adjust.value.reason = ''
  await Promise.all([fetchSummary(), fetchTx()])
}

function onSelectSingleMaterial() {
  const target = masterRows.value.find((x) => x.material_code === adjust.value.material_code)
  if (target) adjust.value.material_name = target.material_name || ''
}

function isChecked(code) {
  return batchChecked.value.includes(code)
}

const isAllChecked = computed(() => {
  return filteredMasterRows.value.length > 0 && filteredMasterRows.value.every((r) => batchChecked.value.includes(r.material_code))
})

function toggleAll(e) {
  if (e.target.checked) {
    const add = filteredMasterRows.value.map((m) => m.material_code).filter((c) => !batchChecked.value.includes(c))
    batchChecked.value = [...batchChecked.value, ...add]
  } else {
    const removeSet = new Set(filteredMasterRows.value.map((m) => m.material_code))
    batchChecked.value = batchChecked.value.filter((c) => !removeSet.has(c))
  }
}

function toggleOne(code, e) {
  if (e.target.checked) {
    if (!batchChecked.value.includes(code)) batchChecked.value.push(code)
  } else {
    batchChecked.value = batchChecked.value.filter((x) => x !== code)
  }
}

async function saveBatchAdjust() {
  if (!batchChecked.value.length) {
    alert('対象行を選択してください')
    return
  }
  if (!batchReason.value.trim()) {
    alert('棚卸調整理由を入力してください')
    return
  }
  const targets = batchChecked.value
    .map((code) => {
      const row = masterRows.value.find((m) => m.material_code === code)
      return {
        material_code: code,
        material_name: row?.material_name || '',
        qty_change: Number(batchQtyMap.value[code] || 0),
      }
    })
    .filter((x) => Number.isFinite(x.qty_change) && x.qty_change !== 0)
  if (!targets.length) {
    alert('調整量(0以外)を入力してください')
    return
  }

  for (const t of targets) {
    await api.outsource.createMaterialStockAdjust({
      material_code: t.material_code,
      material_name: t.material_name,
      qty_change: t.qty_change,
      tx_date: batchDate.value,
      reason: batchReason.value.trim(),
    })
  }
  batchChecked.value = []
  batchQtyMap.value = {}
  batchReason.value = ''
  await Promise.all([fetchSummary(), fetchTx()])
}

onMounted(async () => {
  await Promise.all([fetchSummary(), fetchTx(), fetchMaterialMaster()])
})
</script>

<style scoped>
.page-container { padding: 12px 16px; }
.page-title { font-size: 18px; margin-bottom: 8px; }
.tab-row { display: flex; gap: 4px; margin-bottom: 8px; border-bottom: 2px solid #eee; }
.tab-btn { padding: 6px 14px; border: none; background: transparent; cursor: pointer; font-size: 13px; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.tab-btn.active { border-bottom-color: #1976d2; color: #1976d2; font-weight: 600; }
.subtab-row { display: flex; gap: 4px; margin-bottom: 8px; }
.prepare-form { display: flex; gap: 8px; align-items: end; flex-wrap: wrap; margin-bottom: 8px; }
.prepare-form label { display: inline-flex; align-items: center; gap: 6px; margin: 0; width: auto; flex: 0 0 auto; }
.field-label { min-width: 56px; white-space: nowrap; font-size: 12px; color: #555; }
.input { padding: 4px 7px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.input-sm { width: 120px; }
.input-xs { width: 92px; }
.input-lg { width: 220px; }
.btn-primary { padding: 5px 12px; border: none; background: #1976d2; color: #fff; border-radius: 4px; cursor: pointer; font-size: 12px; }
.single-form { gap: 6px; }
.single-form .field-label { min-width: 46px; }
.single-form .input-lg { width: 200px; }
.single-form .input { padding: 3px 6px; }
.compact-btn { padding: 4px 10px; }
.section { margin-top: 8px; }
.section h3 { font-size: 14px; margin: 0 0 6px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; }
.data-table th { background: #f5f5f5; }
.text-center { text-align: center; }
.text-right { text-align: right; }
.pos { color: #2e7d32; font-weight: 600; }
.neg { color: #c62828; font-weight: 600; }
.empty { color: #999; padding: 8px; }
</style>
