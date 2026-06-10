<template>
  <div class="page-container">
    <h2 class="page-title">完成品在庫 <DataSourceDialog title="完成品在庫" :sources="dsSources" /></h2>

    <div class="tab-row">
      <button class="tab-btn" :class="{ active: tab === 'list' }" @click="tab = 'list'">在庫一覧</button>
      <button class="tab-btn" :class="{ active: tab === 'adjust' }" @click="tab = 'adjust'">在庫調整</button>
    </div>

    <div v-if="tab === 'list'">
      <div class="prepare-form">
        <label>
          <span class="field-label">検索</span>
          <input v-model="filters.keyword" class="input input-lg" placeholder="品目コード・品番・品名" />
        </label>
        <label>
          <span class="field-label">区分</span>
          <select v-model="filters.tx_type" class="input">
            <option value="">全区分</option>
            <option value="RECEIPT">入庫</option>
            <option value="SHIP">出庫</option>
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
          <thead><tr><th>品目コード</th><th>品番</th><th>品名</th><th>現在庫(個)</th></tr></thead>
          <tbody>
            <tr v-for="s in filteredSummary" :key="`${s.item_code}-${s.product_number}`">
              <td>{{ s.item_code }}</td>
              <td>{{ s.product_number || '-' }}</td>
              <td>{{ s.product_name || s.item_name || '-' }}</td>
              <td class="text-right" :class="{ neg: Number(s.stock_qty) < 0 }">{{ s.stock_qty }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">在庫データがありません</div>
      </div>

      <div class="section">
        <h3>在庫履歴</h3>
        <table v-if="filteredTxList.length" class="data-table">
          <thead><tr><th>日付</th><th>区分</th><th>品目コード</th><th>品番</th><th>品名</th><th>増減(個)</th><th>理由</th></tr></thead>
          <tbody>
            <tr v-for="t in filteredTxList" :key="t.id">
              <td>{{ t.tx_date }}</td>
              <td>{{ txLabel(t.tx_type) }}</td>
              <td>{{ t.item_code }}</td>
              <td>{{ t.product_number || '-' }}</td>
              <td>{{ t.product_name || t.item_name || '-' }}</td>
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

      <div v-if="adjustMode === 'single'" class="prepare-form">
        <label>
          <span class="field-label">品目選択</span>
          <select v-model="adjust.item_code" class="input input-lg" @change="onSelectSingleItem">
            <option value="">品目選択</option>
            <option v-for="s in masterRows" :key="`m-${s.item_code}`" :value="s.item_code">
              {{ s.item_code }} | {{ s.product_number || '-' }} | {{ s.product_name || s.item_name || '-' }}
            </option>
          </select>
        </label>
        <label>
          <span class="field-label">品目名称</span>
          <input v-model="adjust.item_name" class="input input-lg" placeholder="品目名称" />
        </label>
        <label>
          <span class="field-label">増減数</span>
          <input v-model.number="adjust.qty_change" type="number" class="input input-sm" placeholder="個" />
        </label>
        <label>
          <span class="field-label">日付</span>
          <input v-model="adjust.tx_date" type="date" class="input" />
        </label>
        <label>
          <span class="field-label">理由</span>
          <input v-model="adjust.reason" class="input input-lg" placeholder="棚卸調整理由（必須）" />
        </label>
        <button class="btn-primary" @click="createAdjust">調整登録</button>
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
        <table v-if="masterRows.length" class="data-table">
          <thead><tr><th><input type="checkbox" :checked="isAllChecked" @change="toggleAll" /></th><th>品目コード</th><th>品番</th><th>品名</th><th>現在庫(個)</th><th>調整量(個)</th></tr></thead>
          <tbody>
            <tr v-for="s in masterRows" :key="`b-${s.item_code}`">
              <td class="text-center"><input type="checkbox" :checked="isChecked(s.item_code)" @change="toggleOne(s.item_code, $event)" /></td>
              <td>{{ s.item_code }}</td>
              <td>{{ s.product_number || '-' }}</td>
              <td>{{ s.product_name || s.item_name || '-' }}</td>
              <td class="text-right" :class="{ neg: Number(s.stock_qty) < 0 }">{{ s.stock_qty }}</td>
              <td><input v-model.number="batchQtyMap[s.item_code]" type="number" class="input input-sm" placeholder="0以外" /></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">在庫データがありません</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_outsource_product_stock', desc: '完成品在庫サマリ・履歴の取得' },
  { op: '読み書き', table: 't_outsource_product_stock', desc: '棚卸調整の登録' },
  { op: '読み取り', table: 't_outsource_item', desc: '品目マスタの取得' },
]

function formatLocalDate(date = new Date()) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const summary = ref([])
const txList = ref([])
const itemMasterMap = ref({})
const itemMasterList = ref([])
const tab = ref('list')
const adjustMode = ref('single')
const filters = ref({
  keyword: '',
  tx_type: '',
  date_from: '',
  date_to: '',
})
const adjust = ref({
  item_code: '',
  item_name: '',
  qty_change: null,
  tx_date: formatLocalDate(),
  reason: '',
})
const batchChecked = ref([])
const batchQtyMap = ref({})
const batchDate = ref(formatLocalDate())
const batchReason = ref('')

const TX_MAP = { RECEIPT: '入庫', SHIP: '出庫', ADJUST: '棚卸調整' }
function txLabel(t) { return TX_MAP[t] || t }

const summaryView = computed(() => summary.value.map((row) => {
  const m = itemMasterMap.value[row.item_code] || {}
  return {
    ...row,
    product_number: m.product_number || '',
    product_name: m.item_name || row.item_name || '',
  }
}))

const txListView = computed(() => txList.value.map((row) => {
  const m = itemMasterMap.value[row.item_code] || {}
  return {
    ...row,
    product_number: m.product_number || '',
    product_name: m.item_name || row.item_name || '',
  }
}))

const stockMap = computed(() => {
  const m = {}
  for (const s of summaryView.value) m[s.item_code] = Number(s.stock_qty || 0)
  return m
})

const masterRows = computed(() => itemMasterList.value.map((it) => ({
  item_code: it.item_code,
  product_number: it.product_number || '',
  product_name: it.item_name || '',
  item_name: it.item_name || '',
  stock_qty: stockMap.value[it.item_code] ?? 0,
})))

const filteredTxList = computed(() => {
  const kw = filters.value.keyword.trim().toLowerCase()
  return txListView.value.filter((r) => {
    if (filters.value.tx_type && r.tx_type !== filters.value.tx_type) return false
    if (filters.value.date_from && r.tx_date < filters.value.date_from) return false
    if (filters.value.date_to && r.tx_date > filters.value.date_to) return false
    if (!kw) return true
    return (
      (r.item_code || '').toLowerCase().includes(kw) ||
      (r.product_number || '').toLowerCase().includes(kw) ||
      (r.product_name || '').toLowerCase().includes(kw)
    )
  })
})

const filteredSummary = computed(() => {
  const kw = filters.value.keyword.trim().toLowerCase()
  if (!kw) return summaryView.value
  return summaryView.value.filter((r) =>
    (r.item_code || '').toLowerCase().includes(kw) ||
    (r.product_number || '').toLowerCase().includes(kw) ||
    (r.product_name || '').toLowerCase().includes(kw)
  )
})

async function fetchSummary() {
  const res = await api.outsource.getProductStockSummary()
  summary.value = res.data || []
}

async function fetchTx() {
  const res = await api.outsource.getProductStockTx({ ordering: '-tx_date' })
  txList.value = res.data.results || res.data
}

async function fetchItemMaster() {
  const res = await api.outsource.getItems()
  const list = res.data.results || res.data
  const map = {}
  for (const it of list) map[it.item_code] = it
  itemMasterList.value = list
  itemMasterMap.value = map
}

async function createAdjust() {
  if (!adjust.value.item_code || !adjust.value.qty_change || !adjust.value.reason) {
    alert('品目コード・増減数・理由を入力してください')
    return
  }
  await api.outsource.createProductStockAdjust(adjust.value)
  adjust.value.qty_change = null
  adjust.value.reason = ''
  await Promise.all([fetchSummary(), fetchTx()])
}

function onSelectSingleItem() {
  const target = masterRows.value.find((x) => x.item_code === adjust.value.item_code)
  if (target) adjust.value.item_name = target.product_name || target.item_name || ''
}

function isChecked(code) {
  return batchChecked.value.includes(code)
}

const isAllChecked = computed(() => {
  return masterRows.value.length > 0 && batchChecked.value.length === masterRows.value.length
})

function toggleAll(e) {
  batchChecked.value = e.target.checked ? masterRows.value.map((s) => s.item_code) : []
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
      const row = masterRows.value.find((s) => s.item_code === code)
      return {
        item_code: code,
        item_name: row?.product_name || row?.item_name || '',
        qty_change: Number(batchQtyMap.value[code] || 0),
      }
    })
    .filter((x) => Number.isFinite(x.qty_change) && x.qty_change !== 0)
  if (!targets.length) {
    alert('調整量(0以外)を入力してください')
    return
  }

  for (const t of targets) {
    await api.outsource.createProductStockAdjust({
      item_code: t.item_code,
      item_name: t.item_name,
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
  await Promise.all([fetchSummary(), fetchTx(), fetchItemMaster()])
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
.input-lg { width: 260px; }
.btn-primary { padding: 5px 12px; border: none; background: #1976d2; color: #fff; border-radius: 4px; cursor: pointer; font-size: 12px; }
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
