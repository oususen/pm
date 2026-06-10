<template>
  <div class="page-container">
    <h2 class="page-title">材料手配（将来承認タスク実装予定） <DataSourceDialog title="材料手配" :sources="dsSources" /></h2>

    <div class="toolbar">
      <select v-model="filterOrdered" @change="fetchMaterials" class="filter-select">
        <option value="false">未発注のみ</option>
        <option value="">全て</option>
        <option value="true">発注済のみ</option>
      </select>
      <button class="btn-month" @click="shiftMonth(-1)">◀ 前月</button>
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchMaterials" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchMaterials" class="filter-date" />
      <button class="btn-month" @click="shiftMonth(1)">次月 ▶</button>
      <input
        v-model="searchText"
        @input="debouncedFetch"
        placeholder="案件番号・品目名・材料コード"
        class="search-input"
      />
      <div class="summary-badges" v-if="materials.length">
        <span class="badge badge-total">全{{ materials.length }}件</span>
        <span class="badge badge-pending">未発注: {{ pendingCount }}件</span>
        <span class="badge badge-overdue" v-if="overdueCount">期限超過: {{ overdueCount }}件</span>
      </div>
      <button
        v-if="hasUnordered"
        class="btn-primary btn-export"
        :disabled="exporting"
        @click="exportPurchaseOrder"
      >{{ exporting ? '出力中...' : '注文書Excel出力' }}</button>
    </div>

    <!-- 選択アクションバー -->
    <div v-if="selectedIds.length" class="action-bar">
      <span class="action-count">{{ selectedIds.length }}件選択中</span>
      <button class="btn-action btn-action-order" @click="orderSelected">選択を発注済にする</button>
      <button class="btn-action btn-action-export" :disabled="exporting" @click="exportSelected">
        {{ exporting ? '出力中...' : '選択分の注文書Excel出力' }}
      </button>
      <button class="btn-action btn-action-clear" @click="selectedIds = []">選択解除</button>
    </div>

    <!-- メーカ別表示 -->
    <div v-for="group in groupedBySupplier" :key="group.supplier" class="supplier-group">
      <div class="group-header">
        <span class="group-title">{{ group.supplier }}</span>
        <span class="group-count">{{ group.items.length }}品目 / 合計 {{ formatQty(group.totalQty) }}</span>
        <button v-if="group.items.some(m => !m.ordered)" class="btn-supply-all" @click="orderAll(group.items)">一括発注済</button>
      </div>
      <table class="data-table">
        <thead><tr>
          <th class="col-check"><input type="checkbox" @change="toggleGroup(group, $event)" :checked="isGroupAllSelected(group)" /></th>
          <th>材料納期</th><th>支給予定日</th><th>材料コード</th><th>材料名称</th><th>必要数量</th><th>在庫数</th><th>発注数</th><th>案件番号</th><th>品目名称</th><th>加工日</th><th>状態</th><th>操作</th>
        </tr></thead>
        <tbody>
          <tr v-for="m in group.items" :key="m.id" :class="rowClass(m)">
            <td class="text-center"><input type="checkbox" :value="m.id" v-model="selectedIds" /></td>
            <td>
              <input
                type="date"
                class="date-input"
                :value="m.material_due_date || m.supply_date"
                @change="updateMaterialDueDate(m, $event)"
              />
            </td>
            <td :class="{ 'text-danger': isOverdue(m) }">{{ m.supply_date }}</td>
            <td>{{ m.material_code }}</td>
            <td>{{ m.material_name }}</td>
            <td class="text-right">{{ formatQty(m.required_qty) }}</td>
            <td class="text-right">{{ formatQty(stockQtyOf(m.material_code)) }}</td>
            <td>
              <input
                type="number"
                step="1"
                class="qty-input"
                :value="orderedQtyOf(m)"
                @change="updateOrderQty(m, $event)"
              />
            </td>
            <td class="case-no">{{ m.case_no }}</td>
            <td>{{ m.item_name }}</td>
            <td>{{ m.process_date }}</td>
            <td class="text-center"><span :class="statusClass(m)">{{ statusText(m) }}</span></td>
            <td>
              <button v-if="!m.ordered" class="btn-supply" :disabled="!canMarkOrdered(m)" @click="markOrdered(m)">発注済</button>
              <button v-else class="btn-undo" @click="undoOrder(m)">取消</button>
            </td>
          </tr>
        </tbody>
        <tfoot><tr class="total-row"><td colspan="5">小計</td><td class="text-right">{{ formatQty(group.totalQty) }}</td><td colspan="6"></td></tr></tfoot>
      </table>
    </div>

    <div v-if="!materials.length && !loading" class="empty-state">材料支給データがありません</div>
    <div v-if="loading" class="loading">読み込み中...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_outsource_material', desc: '材料発注ステータスの取得・更新' },
  { op: '読み取り', table: 't_outsource_material_stock', desc: '材料在庫数の参照' },
  { op: '読み取り', table: 't_outsource_procurement', desc: '注文書Excel出力' },
]

const materials = ref([])
const materialStockMap = ref({})
const loading = ref(false)
const exporting = ref(false)
const filterOrdered = ref('false')
const searchText = ref('')
const selectedIds = ref([])

let debounceTimer = null
function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchMaterials, 300)
}
function monthRange(d) {
  const y = d.getFullYear(), m = d.getMonth()
  const from = `${y}-${String(m + 1).padStart(2, '0')}-01`
  const to = `${y}-${String(m + 1).padStart(2, '0')}-${String(new Date(y, m + 1, 0).getDate()).padStart(2, '0')}`
  return { from, to }
}
const now = new Date()
const twoMonthsLater = new Date()
twoMonthsLater.setMonth(twoMonthsLater.getMonth() + 2)
const { to: initTo } = monthRange(twoMonthsLater)
const paintingFrom = ref(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`)
const paintingTo = ref(initTo)

function shiftMonth(delta) {
  const d = new Date(paintingFrom.value + 'T00:00:00')
  d.setMonth(d.getMonth() + delta)
  const { from, to } = monthRange(d)
  paintingFrom.value = from
  paintingTo.value = to
  fetchMaterials()
}

function formatLocalDate(date = new Date()) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const today = formatLocalDate()

const pendingCount = computed(() => materials.value.filter(m => !m.ordered).length)
const overdueCount = computed(() => materials.value.filter(m => !m.ordered && m.supply_date < today).length)
const hasUnordered = computed(() => materials.value.some(m => !m.ordered))

function formatQty(val) {
  const n = parseFloat(val)
  return Number.isInteger(n) ? n.toLocaleString() : n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function stockQtyOf(materialCode) {
  return materialStockMap.value[materialCode] ?? 0
}

function orderedQtyOf(m) {
  const v = parseFloat(m.order_qty)
  return Number.isFinite(v) ? v : (parseFloat(m.required_qty) || 0)
}

function canMarkOrdered(m) {
  return Math.trunc(Number(orderedQtyOf(m)) || 0) >= 1
}

function dueDateOf(m) { return m.material_due_date || m.supply_date }
function isOverdue(m) { return !m.ordered && dueDateOf(m) < today }

function rowClass(m) {
  if (m.ordered) return 'row-supplied'
  if (isOverdue(m)) return 'row-overdue'
  return ''
}

function statusClass(m) {
  if (m.ordered) return 'st-done'
  if (isOverdue(m)) return 'st-overdue'
  return 'st-pending'
}

function statusText(m) {
  if (m.ordered) return '発注済'
  if (isOverdue(m)) return '期限超過'
  return '未発注'
}

const groupedBySupplier = computed(() => {
  const map = {}
  for (const m of materials.value) {
    const supplier = m.supplier_name || '調達先未設定'
    if (!map[supplier]) map[supplier] = { supplier, items: [], totalQty: 0 }
    map[supplier].items.push(m)
    map[supplier].totalQty += parseFloat(m.required_qty)
  }
  for (const g of Object.values(map)) {
    g.items.sort((a, b) => dueDateOf(a).localeCompare(dueDateOf(b)) || a.material_code.localeCompare(b.material_code))
  }
  return Object.values(map).sort((a, b) => a.supplier.localeCompare(b.supplier))
})

async function fetchMaterials() {
  loading.value = true
  selectedIds.value = []
  try {
    const params = { ordering: 'material_due_date,supply_date' }
    if (filterOrdered.value) params.ordered = filterOrdered.value
    if (paintingFrom.value) params.painting_date_from = paintingFrom.value
    if (paintingTo.value) params.painting_date_to = paintingTo.value
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const [matRes, stockRes] = await Promise.all([
      api.outsource.getMaterials(params),
      api.outsource.getMaterialStockSummary(),
    ])
    materials.value = matRes.data.results || matRes.data
    const map = {}
    for (const row of (stockRes.data || [])) {
      map[row.material_code] = parseFloat(row.stock_qty || 0)
    }
    materialStockMap.value = map
  } finally { loading.value = false }
}

const todayDate = formatLocalDate()

async function markOrdered(m) {
  if (!canMarkOrdered(m)) {
    alert('発注数は1以上を指定してください')
    return
  }
  try {
    await api.outsource.patchMaterial(m.id, { ordered: true, ordered_at: todayDate })
    m.ordered = true; m.ordered_at = todayDate
  } catch (err) { console.error(err) }
}

async function undoOrder(m) {
  try {
    await api.outsource.patchMaterial(m.id, { ordered: false, ordered_at: null })
    m.ordered = false; m.ordered_at = null
  } catch (err) { console.error(err) }
}

async function updateOrderQty(m, event) {
  const next = Number(event.target.value)
  if (!Number.isFinite(next) || next < 0) {
    event.target.value = orderedQtyOf(m)
    return
  }
  const val = Math.trunc(next)
  if (val === Number(m.order_qty ?? m.required_qty ?? 0)) return
  try {
    await api.outsource.patchMaterial(m.id, { order_qty: val })
    m.order_qty = val
  } catch (err) {
    console.error(err)
    event.target.value = orderedQtyOf(m)
    alert('発注数の更新に失敗しました')
  }
}

async function updateMaterialDueDate(m, event) {
  const next = event.target.value
  if (!next) {
    event.target.value = m.material_due_date || m.supply_date
    return
  }
  if (next === (m.material_due_date || m.supply_date)) return
  try {
    await api.outsource.patchMaterial(m.id, { material_due_date: next })
    m.material_due_date = next
  } catch (err) {
    console.error(err)
    event.target.value = m.material_due_date || m.supply_date
    alert('材料納期の更新に失敗しました')
  }
}

async function orderAll(items) {
  for (const m of items) { if (!m.ordered && canMarkOrdered(m)) await markOrdered(m) }
}

function isGroupAllSelected(group) {
  return group.items.length > 0 && group.items.every(m => selectedIds.value.includes(m.id))
}

function toggleGroup(group, event) {
  const ids = group.items.map(m => m.id)
  if (event.target.checked) {
    const newIds = ids.filter(id => !selectedIds.value.includes(id))
    selectedIds.value = [...selectedIds.value, ...newIds]
  } else {
    selectedIds.value = selectedIds.value.filter(id => !ids.includes(id))
  }
}

async function orderSelected() {
  const targets = materials.value.filter(m => selectedIds.value.includes(m.id) && !m.ordered && canMarkOrdered(m))
  for (const m of targets) { await markOrdered(m) }
  selectedIds.value = []
}

async function exportSelected() {
  exporting.value = true
  try {
    const res = await api.outsource.generatePurchaseOrder({ material_ids: selectedIds.value })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `注文書_${formatLocalDate()}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) { alert(err.response?.data?.error || '出力に失敗しました') }
  finally { exporting.value = false }
}

async function exportPurchaseOrder() {
  exporting.value = true
  try {
    const res = await api.outsource.generatePurchaseOrder({ unordered_only: true })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `注文書_${formatLocalDate()}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) { alert(err.response?.data?.error || '出力に失敗しました') }
  finally { exporting.value = false }
}

onMounted(fetchMaterials)
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { font-size: 18px; margin-bottom: 12px; }

.toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.filter-select { padding: 4px 8px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.filter-label { font-size: 12px; color: #555; }
.filter-date { padding: 3px 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; width: 130px; }
.filter-sep { font-size: 12px; color: #888; }
.btn-month { padding: 3px 8px; font-size: 11px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-month:hover { background: #e3f2fd; }
.search-input { padding: 4px 8px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; width: 220px; }
.btn-primary { padding: 6px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-export { margin-left: auto; }

.summary-badges { display: flex; gap: 8px; }
.badge { padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge-total { background: #e3f2fd; color: #1565c0; }
.badge-pending { background: #fff3e0; color: #e65100; }
.badge-overdue { background: #fbe9e7; color: #c62828; }

.supplier-group { margin-bottom: 16px; }
.group-header {
  display: flex; align-items: center; gap: 12px;
  padding: 6px 12px; background: #e3f2fd; border-left: 4px solid #1976d2; border-radius: 4px 4px 0 0; font-size: 13px; font-weight: 600;
}
.group-title { font-size: 14px; }
.group-count { color: #888; font-weight: 400; }
.btn-supply-all { margin-left: auto; padding: 2px 10px; background: #e8f5e9; border: 1px solid #81c784; border-radius: 4px; cursor: pointer; font-size: 11px; }
.col-check { width: 30px; text-align: center; }

.action-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; margin-bottom: 8px;
  background: #fff8e1; border: 1px solid #ffe082; border-radius: 4px;
}
.action-count { font-size: 12px; font-weight: 600; color: #e65100; }
.btn-action { padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; border: 1px solid; }
.btn-action-order { background: #e8f5e9; border-color: #81c784; color: #2e7d32; }
.btn-action-export { background: #e3f2fd; border-color: #90caf9; color: #1565c0; }
.btn-action-export:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-action-clear { background: #f5f5f5; border-color: #ccc; color: #666; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 3px 8px; white-space: nowrap; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.text-danger { color: #c62828; font-weight: 600; }
.case-no { font-family: monospace; font-size: 11px; }
.total-row { font-weight: 600; background: #fafafa; }

.row-supplied { opacity: 0.4; }
.row-overdue { background: #fff8e1; }

.st-done { color: #2e7d32; font-size: 11px; font-weight: 600; }
.st-pending { color: #e65100; font-size: 11px; }
.st-overdue { color: #c62828; font-size: 11px; font-weight: 600; }

.btn-supply { padding: 2px 8px; background: #e8f5e9; border: 1px solid #81c784; border-radius: 4px; cursor: pointer; font-size: 11px; }
.btn-supply:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-undo { padding: 2px 8px; background: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; font-size: 11px; color: #888; }
.qty-input {
  width: 90px;
  padding: 2px 6px;
  font-size: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  text-align: right;
}
.date-input {
  width: 130px;
  padding: 2px 6px;
  font-size: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.empty-state, .loading { text-align: center; padding: 32px; color: #999; font-size: 14px; }
</style>
