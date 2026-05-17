<template>
  <div class="page-container">
    <h2 class="page-title">材料手配</h2>

    <div class="toolbar">
      <select v-model="filterSupplied" @change="fetchMaterials" class="filter-select">
        <option value="false">未支給のみ</option>
        <option value="">全て</option>
        <option value="true">支給済のみ</option>
      </select>
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchMaterials" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchMaterials" class="filter-date" />
      <div class="summary-badges" v-if="materials.length">
        <span class="badge badge-total">全{{ materials.length }}件</span>
        <span class="badge badge-pending">未支給: {{ pendingCount }}件</span>
        <span class="badge badge-overdue" v-if="overdueCount">期限超過: {{ overdueCount }}件</span>
      </div>
      <button
        v-if="hasUnsupplied"
        class="btn-primary btn-export"
        :disabled="exporting"
        @click="exportPurchaseOrder"
      >{{ exporting ? '出力中...' : '注文書Excel出力' }}</button>
    </div>

    <!-- メーカ別表示 -->
    <div v-for="group in groupedBySupplier" :key="group.supplier" class="supplier-group">
      <div class="group-header">
        <span class="group-title">{{ group.supplier }}</span>
        <span class="group-count">{{ group.items.length }}品目 / 合計 {{ formatQty(group.totalQty) }}</span>
        <button v-if="group.items.some(m => !m.supplied)" class="btn-supply-all" @click="supplyAll(group.items)">一括支給済</button>
      </div>
      <table class="data-table">
        <thead><tr><th>支給予定日</th><th>材料コード</th><th>材料名称</th><th>必要数量</th><th>案件番号</th><th>品目名称</th><th>加工日</th><th>状態</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="m in group.items" :key="m.id" :class="rowClass(m)">
            <td :class="{ 'text-danger': isOverdue(m) }">{{ m.supply_date }}</td>
            <td>{{ m.material_code }}</td>
            <td>{{ m.material_name }}</td>
            <td class="text-right">{{ formatQty(m.required_qty) }}</td>
            <td class="case-no">{{ m.case_no }}</td>
            <td>{{ m.item_name }}</td>
            <td>{{ m.process_date }}</td>
            <td class="text-center"><span :class="statusClass(m)">{{ statusText(m) }}</span></td>
            <td>
              <button v-if="!m.supplied" class="btn-supply" @click="markSupplied(m)">支給済</button>
              <button v-else class="btn-undo" @click="undoSupply(m)">取消</button>
            </td>
          </tr>
        </tbody>
        <tfoot><tr class="total-row"><td colspan="3">小計</td><td class="text-right">{{ formatQty(group.totalQty) }}</td><td colspan="5"></td></tr></tfoot>
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
const exporting = ref(false)
const filterSupplied = ref('false')
const paintingFrom = ref('')
const paintingTo = ref('')

const today = new Date().toISOString().slice(0, 10)

const pendingCount = computed(() => materials.value.filter(m => !m.supplied).length)
const overdueCount = computed(() => materials.value.filter(m => !m.supplied && m.supply_date < today).length)
const hasUnsupplied = computed(() => materials.value.some(m => !m.supplied))

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

const groupedBySupplier = computed(() => {
  const map = {}
  for (const m of materials.value) {
    const supplier = m.supplier_name || '調達先未設定'
    if (!map[supplier]) map[supplier] = { supplier, items: [], totalQty: 0 }
    map[supplier].items.push(m)
    map[supplier].totalQty += parseFloat(m.required_qty)
  }
  for (const g of Object.values(map)) {
    g.items.sort((a, b) => a.supply_date.localeCompare(b.supply_date) || a.material_code.localeCompare(b.material_code))
  }
  return Object.values(map).sort((a, b) => a.supplier.localeCompare(b.supplier))
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

async function exportPurchaseOrder() {
  exporting.value = true
  try {
    const res = await api.outsource.generatePurchaseOrder({ unsupplied_only: true })
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `注文書_${new Date().toISOString().slice(0, 10)}.xlsx`
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
