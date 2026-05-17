<template>
  <div class="page-container">
    <h2 class="page-title">材料所要量</h2>

    <div class="toolbar">
      <select v-model="filterSupplied" @change="fetchMaterials" class="filter-select">
        <option value="false">未支給のみ</option>
        <option value="">全て</option>
        <option value="true">支給済のみ</option>
      </select>
      <button class="btn-month" @click="shiftMonth(-1)">◀ 前月</button>
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchMaterials" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchMaterials" class="filter-date" />
      <button class="btn-month" @click="shiftMonth(1)">次月 ▶</button>
      <select v-model="viewMode" class="filter-select">
        <option value="byCase">案件別</option>
        <option value="byDate">支給日別</option>
        <option value="byMaterial">材料別集約</option>
      </select>
      <div class="summary-badges" v-if="materials.length">
        <span class="badge badge-total">全{{ materials.length }}件</span>
        <span class="badge badge-pending">未支給: {{ pendingCount }}件</span>
        <span class="badge badge-overdue" v-if="overdueCount">期限超過: {{ overdueCount }}件</span>
      </div>
    </div>

    <!-- 案件別表示 -->
    <div v-if="viewMode === 'byCase'">
      <div v-for="group in groupedByCase" :key="group.case_no" class="date-group">
        <div class="group-header clickable" @click="toggleCase(group.case_no)">
          <span class="toggle-icon">{{ expandedCases.has(group.case_no) ? '▼' : '▶' }}</span>
          <span class="group-title">{{ group.case_no }}</span>
          <span class="group-count">{{ group.item_name }} / {{ group.items.length }}材料</span>
        </div>
        <table v-if="expandedCases.has(group.case_no)" class="data-table">
          <thead><tr><th>支給予定日</th><th>加工日</th><th>材料コード</th><th>材料名称</th><th>調達先</th><th>必要数量</th><th>状態</th></tr></thead>
          <tbody>
            <tr v-for="m in group.items" :key="m.id" :class="rowClass(m)">
              <td :class="{ 'text-danger': isOverdue(m) }">{{ m.supply_date }}</td>
              <td>{{ m.process_date }}</td>
              <td>{{ m.material_code }}</td>
              <td>{{ m.material_name }}</td>
              <td>{{ m.supplier_name || '-' }}</td>
              <td class="text-right">{{ formatQty(m.required_qty) }}</td>
              <td class="text-center"><span :class="statusClass(m)">{{ statusText(m) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 支給日別表示 -->
    <div v-if="viewMode === 'byDate'">
      <div v-for="group in groupedByDate" :key="group.date" class="date-group">
        <div class="group-header" :class="{ overdue: group.isOverdue, today: group.isToday }">
          <span class="group-title">{{ group.date }}</span>
          <span class="group-count">{{ group.items.length }}件</span>
          <button v-if="group.items.some(m => !m.supplied)" class="btn-supply-all" @click="supplyAll(group.items)">一括支給済</button>
        </div>
        <table class="data-table">
          <thead><tr><th>案件番号</th><th>品目名称</th><th>加工日</th><th>材料コード</th><th>材料名称</th><th>調達先</th><th>必要数量</th><th>状態</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="m in group.items" :key="m.id" :class="rowClass(m)">
              <td class="case-no">{{ m.case_no }}</td>
              <td>{{ m.item_name }}</td>
              <td>{{ m.process_date }}</td>
              <td>{{ m.material_code }}</td>
              <td>{{ m.material_name }}</td>
              <td>{{ m.supplier_name || '-' }}</td>
              <td class="text-right">{{ formatQty(m.required_qty) }}</td>
              <td class="text-center"><span :class="statusClass(m)">{{ statusText(m) }}</span></td>
              <td>
                <button v-if="!m.supplied" class="btn-supply" @click="markSupplied(m)">支給済</button>
                <button v-else class="btn-undo" @click="undoSupply(m)">取消</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 材料別集約表示 -->
    <div v-if="viewMode === 'byMaterial'">
      <table class="data-table">
        <thead><tr><th>材料コード</th><th>材料名称</th><th>調達先</th><th>必要合計</th><th>支給済合計</th><th>残数</th><th>関連案件数</th><th>最早支給日</th></tr></thead>
        <tbody>
          <tr v-for="agg in aggregatedByMaterial" :key="agg.material_code" :class="{ 'row-supplied': agg.remaining <= 0 }">
            <td>{{ agg.material_code }}</td>
            <td>{{ agg.material_name }}</td>
            <td>{{ agg.supplier_name || '-' }}</td>
            <td class="text-right">{{ formatQty(agg.total_required) }}</td>
            <td class="text-right">{{ formatQty(agg.total_supplied) }}</td>
            <td class="text-right" :class="{ 'text-danger': agg.remaining > 0 }">{{ formatQty(agg.remaining) }}</td>
            <td class="text-center">{{ agg.order_count }}</td>
            <td :class="{ 'text-danger': agg.isOverdue }">{{ agg.earliest_date }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!materials.length && !loading" class="empty-state">材料所要量データがありません</div>
    <div v-if="loading" class="loading">読み込み中...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

const materials = ref([])
const loading = ref(false)
const filterSupplied = ref('false')
function monthRange(d) {
  const y = d.getFullYear(), m = d.getMonth()
  const from = `${y}-${String(m + 1).padStart(2, '0')}-01`
  const to = `${y}-${String(m + 1).padStart(2, '0')}-${String(new Date(y, m + 1, 0).getDate()).padStart(2, '0')}`
  return { from, to }
}
const { from: initFrom, to: initTo } = monthRange(new Date())
const paintingFrom = ref(initFrom)
const paintingTo = ref(initTo)

function shiftMonth(delta) {
  const d = new Date(paintingFrom.value + 'T00:00:00')
  d.setMonth(d.getMonth() + delta)
  const { from, to } = monthRange(d)
  paintingFrom.value = from
  paintingTo.value = to
  fetchMaterials()
}
const viewMode = ref('byCase')

const today = new Date().toISOString().slice(0, 10)
const expandedCases = ref(new Set())

function toggleCase(caseNo) {
  if (expandedCases.value.has(caseNo)) {
    expandedCases.value.delete(caseNo)
  } else {
    expandedCases.value.add(caseNo)
  }
  expandedCases.value = new Set(expandedCases.value)
}

const pendingCount = computed(() => materials.value.filter(m => !m.supplied).length)
const overdueCount = computed(() => materials.value.filter(m => !m.supplied && m.supply_date < today).length)

function formatQty(val) {
  const n = parseFloat(val)
  return Number.isInteger(n) ? n.toLocaleString() : n.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function isOverdue(m) { return !m.supplied && m.supply_date < today }

function rowClass(m) {
  if (m.supplied) return 'row-supplied'
  if (isOverdue(m)) return 'row-overdue'
  return ''
}

function statusClass(m) {
  if (m.supplied) return 'st-done'
  if (isOverdue(m)) return 'st-overdue'
  return 'st-pending'
}

function statusText(m) {
  if (m.supplied) return '支給済'
  if (isOverdue(m)) return '期限超過'
  return '未支給'
}

// 案件別
const groupedByCase = computed(() => {
  const map = {}
  for (const m of materials.value) {
    const key = m.case_no
    if (!map[key]) map[key] = { case_no: m.case_no, item_name: m.item_name, items: [] }
    map[key].items.push(m)
  }
  for (const g of Object.values(map)) {
    g.items.sort((a, b) => a.supply_date.localeCompare(b.supply_date) || a.material_code.localeCompare(b.material_code))
  }
  return Object.values(map).sort((a, b) => a.case_no.localeCompare(b.case_no))
})

// 支給日別
const groupedByDate = computed(() => {
  const map = {}
  for (const m of materials.value) {
    const d = m.supply_date
    if (!map[d]) map[d] = { date: d, items: [], isOverdue: d < today, isToday: d === today }
    map[d].items.push(m)
  }
  return Object.values(map).sort((a, b) => a.date.localeCompare(b.date))
})

// 材料別集約
const aggregatedByMaterial = computed(() => {
  const map = {}
  for (const m of materials.value) {
    const key = m.material_code
    if (!map[key]) {
      map[key] = {
        material_code: m.material_code, material_name: m.material_name,
        supplier_name: m.supplier_name,
        total_required: 0, total_supplied: 0, remaining: 0,
        order_count: new Set(), earliest_date: m.supply_date,
      }
    }
    const agg = map[key]
    agg.total_required += parseFloat(m.required_qty)
    agg.total_supplied += parseFloat(m.supplied_qty || 0)
    agg.order_count.add(m.case_no)
    if (m.supply_date < agg.earliest_date) agg.earliest_date = m.supply_date
  }
  return Object.values(map).map(agg => ({
    ...agg, remaining: agg.total_required - agg.total_supplied,
    order_count: agg.order_count.size,
    isOverdue: agg.total_required - agg.total_supplied > 0 && agg.earliest_date < today,
  })).sort((a, b) => a.earliest_date.localeCompare(b.earliest_date))
})


async function fetchMaterials() {
  loading.value = true
  try {
    const params = { ordering: 'supply_date' }
    if (filterSupplied.value) params.supplied = filterSupplied.value
    if (paintingFrom.value) params.painting_date_from = paintingFrom.value
    if (paintingTo.value) params.painting_date_to = paintingTo.value
    const res = await api.outsource.getMaterials(params)
    materials.value = res.data.results || res.data
  } finally { loading.value = false }
}

async function markSupplied(m) {
  try {
    await api.outsource.supplyMaterial(m.id, { supplied_qty: m.required_qty })
    m.supplied = true; m.supplied_qty = m.required_qty
  } catch (err) { console.error(err) }
}

async function undoSupply(m) {
  try {
    await api.outsource.updateMaterial(m.id, { ...m, supplied: false, supplied_qty: 0 })
    m.supplied = false; m.supplied_qty = 0
  } catch (err) { console.error(err) }
}

async function supplyAll(items) {
  for (const m of items) { if (!m.supplied) await markSupplied(m) }
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

.summary-badges { display: flex; gap: 8px; }
.badge { padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge-total { background: #e3f2fd; color: #1565c0; }
.badge-pending { background: #fff3e0; color: #e65100; }
.badge-overdue { background: #fbe9e7; color: #c62828; }

.date-group { margin-bottom: 16px; }
.group-header {
  display: flex; align-items: center; gap: 12px;
  padding: 6px 12px; background: #f5f5f5; border-radius: 4px 4px 0 0; font-size: 13px; font-weight: 600;
}
.group-header.overdue { background: #fbe9e7; color: #c62828; }
.group-header.today { background: #e8f5e9; color: #2e7d32; }
.clickable { cursor: pointer; user-select: none; }
.toggle-icon { font-size: 10px; width: 12px; }
.group-title { font-size: 14px; }
.group-count { color: #888; font-weight: 400; }
.btn-supply-all { margin-left: auto; padding: 2px 10px; background: #e8f5e9; border: 1px solid #81c784; border-radius: 4px; cursor: pointer; font-size: 11px; }

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
.btn-undo { padding: 2px 8px; background: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; font-size: 11px; color: #888; }

.empty-state, .loading { text-align: center; padding: 32px; color: #999; font-size: 14px; }
</style>
