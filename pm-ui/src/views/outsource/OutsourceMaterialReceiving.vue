<template>
  <div class="page-container">
    <h2 class="page-title">材料検収</h2>

    <div class="toolbar">
      <select v-model="filterOrdered" @change="fetchRows" class="input">
        <option value="true">発注済のみ</option>
        <option value="">全て</option>
      </select>
      <label>塗装日:</label>
      <input v-model="paintingFrom" type="date" class="input" @change="fetchRows" />
      <span>〜</span>
      <input v-model="paintingTo" type="date" class="input" @change="fetchRows" />
      <label>納期日:</label>
      <select v-model="supplyDateFilter" class="input" @change="fetchRows">
        <option value="">全て</option>
        <option v-for="d in dueDateOptions" :key="d" :value="d">{{ d }}</option>
      </select>
      <input v-model="keyword" class="input input-lg" placeholder="材料コード・材料名・案件番号" />
    </div>

    <table v-if="filteredRows.length" class="data-table">
      <thead>
        <tr>
          <th>納期日</th>
          <th>材料コード</th>
          <th>材料名称</th>
          <th>調達先</th>
          <th>発注数</th>
          <th>検収済</th>
          <th>今回検収</th>
          <th>検収日</th>
          <th>理由</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in filteredRows" :key="r.id">
          <td>{{ r.material_due_date || r.supply_date }}</td>
          <td>{{ r.material_code }}</td>
          <td>{{ r.material_name }}</td>
          <td>{{ r.supplier_name || '-' }}</td>
          <td class="text-right">{{ num(r.order_qty || r.required_qty) }}</td>
          <td class="text-right">{{ num(receivedMap[r.id] || 0) }}</td>
          <td><input v-model.number="formMap[r.id].qty" type="number" min="1" step="1" class="input input-sm" /></td>
          <td><input v-model="formMap[r.id].date" type="date" class="input" /></td>
          <td><input v-model="formMap[r.id].reason" class="input input-md" /></td>
          <td><button class="btn-primary" @click="registerReceive(r)">検収登録</button></td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">対象データがありません</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

function monthRange(d) {
  const y = d.getFullYear()
  const m = d.getMonth()
  const from = `${y}-${String(m + 1).padStart(2, '0')}-01`
  const to = `${y}-${String(m + 1).padStart(2, '0')}-${String(new Date(y, m + 1, 0).getDate()).padStart(2, '0')}`
  return { from, to }
}
function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function num(v) {
  const n = Number(v || 0)
  return Number.isInteger(n) ? String(n) : n.toFixed(2)
}

const rows = ref([])
const receivedMap = ref({})
const formMap = ref({})
const filterOrdered = ref('true')
const keyword = ref('')
const { from, to } = monthRange(new Date())
const paintingFrom = ref(from)
const paintingTo = ref(to)
const supplyDateFilter = ref(today())

function addWorkingDays(dateStr, days) {
  const d = new Date(dateStr + 'T00:00:00')
  let remaining = Math.abs(days)
  const direction = days >= 0 ? 1 : -1
  while (remaining > 0) {
    d.setDate(d.getDate() + direction)
    const dow = d.getDay()
    if (dow !== 0 && dow !== 6) remaining--
  }
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const dueDateOptions = computed(() => {
  const t = today()
  const dates = [
    addWorkingDays(t, -2),
    addWorkingDays(t, -1),
    t,
    addWorkingDays(t, 1),
    addWorkingDays(t, 2),
  ]
  return [...new Set(dates)].sort()
})

const filteredRows = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return rows.value.filter((r) => {
    const dueDate = String(r.material_due_date || r.supply_date || '')
    if (supplyDateFilter.value && dueDate !== supplyDateFilter.value) return false
    if (!kw) return true
    return (
      String(r.material_code || '').toLowerCase().includes(kw) ||
      String(r.material_name || '').toLowerCase().includes(kw) ||
      String(r.case_no || '').toLowerCase().includes(kw)
    )
  })
})

function initForm(list) {
  const next = {}
  for (const r of list) {
    next[r.id] = {
      qty: Math.max(1, Math.trunc(Number(r.order_qty || r.required_qty || 1))),
      date: today(),
      reason: '材料検収',
    }
  }
  formMap.value = next
}

async function fetchRows() {
  const params = {}
  if (filterOrdered.value) params.ordered = filterOrdered.value
  if (paintingFrom.value) params.painting_date_from = paintingFrom.value
  if (paintingTo.value) params.painting_date_to = paintingTo.value
  const res = await api.outsource.getMaterials(params)
  rows.value = res.data.results || res.data
  initForm(rows.value)
  await fetchReceivedMap()
}

async function fetchReceivedMap() {
  const map = {}
  let page = 1
  while (true) {
    const res = await api.outsource.getMaterialStockTx({ tx_type: 'RECEIPT', page, page_size: 200 })
    const data = res.data
    const list = data.results || data
    for (const t of list) {
      if (t.ref_type === 'material_requirement_receipt' && t.ref_id) {
        map[t.ref_id] = (map[t.ref_id] || 0) + Number(t.qty_change || 0)
      }
    }
    if (!data.next) break
    page += 1
  }
  receivedMap.value = map
}

async function registerReceive(r) {
  const f = formMap.value[r.id]
  if (!f || !f.qty || Number(f.qty) <= 0) {
    alert('検収数量を入力してください')
    return
  }
  await api.outsource.receiveMaterial(r.id, {
    received_qty: Math.trunc(Number(f.qty)),
    tx_date: f.date,
    reason: f.reason || '材料検収',
  })
  await fetchReceivedMap()
}

onMounted(fetchRows)
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { font-size: 18px; margin-bottom: 10px; }
.toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.input { padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; }
.input-sm { width: 86px; }
.input-md { width: 180px; }
.input-lg { width: 220px; }
.btn-primary { padding: 4px 10px; border: none; background: #1976d2; color: #fff; border-radius: 4px; font-size: 12px; cursor: pointer; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 6px; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.empty { color: #888; padding: 10px; }
</style>
