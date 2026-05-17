<template>
  <div class="page-container">
    <h2 class="page-title">外作先展開Excel出力</h2>

    <div class="filter-row">
      <select v-model="filterStatus" @change="fetchOrders" class="filter-select">
        <option value="IMPORTED">取込済（未送付）</option>
        <option value="SENT_TO_SUB">展開送付済</option>
        <option value="">全て</option>
      </select>
      <button class="btn-month" @click="shiftMonth(-1)">◀ 前月</button>
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchOrders" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchOrders" class="filter-date" />
      <button class="btn-month" @click="shiftMonth(1)">次月 ▶</button>
      <button class="btn-primary" :disabled="!selectedIds.length || exporting" @click="doExport">
        {{ exporting ? '出力中...' : `Excel出力（${selectedIds.length}件）` }}
      </button>
    </div>

    <table class="data-table" v-if="orders.length">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleAll" :checked="allSelected" /></th>
          <th>案件番号</th>
          <th>品目コード</th>
          <th>品目名称</th>
          <th>数量</th>
          <th>塗装日</th>
          <th>最早着手</th>
          <th>最遅完了</th>
          <th>ステータス</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="o in orders" :key="o.id">
          <td><input type="checkbox" :value="o.id" v-model="selectedIds" /></td>
          <td class="case-no">{{ o.case_no }}</td>
          <td>{{ o.item_code }}</td>
          <td>{{ o.item_name }}</td>
          <td class="text-right">{{ o.order_qty }}</td>
          <td>{{ o.painting_date }}</td>
          <td>{{ o.earliest_start || '-' }}</td>
          <td>{{ o.latest_finish || '-' }}</td>
          <td>{{ statusLabel(o.status) }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else-if="!loading" class="empty-state">対象案件がありません</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

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
  fetchOrders()
}

const orders = ref([])
const selectedIds = ref([])
const filterStatus = ref('IMPORTED')
const loading = ref(false)
const exporting = ref(false)

const allSelected = computed(() => orders.value.length > 0 && selectedIds.value.length === orders.value.length)

function toggleAll(e) {
  selectedIds.value = e.target.checked ? orders.value.map(o => o.id) : []
}

const STATUS_MAP = { IMPORTED: '取込済', SENT_TO_SUB: '展開送付済', SPLIT_REGISTERED: '分割登録済', IN_PROGRESS: '加工中', COMPLETED: '完了' }
function statusLabel(s) { return STATUS_MAP[s] || s }

async function fetchOrders() {
  loading.value = true
  selectedIds.value = []
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    if (paintingFrom.value) params.painting_date_from = paintingFrom.value
    if (paintingTo.value) params.painting_date_to = paintingTo.value
    const res = await api.outsource.getOrders(params)
    orders.value = res.data.results || res.data
  } finally {
    loading.value = false
  }
}

async function doExport() {
  exporting.value = true
  try {
    const res = await api.outsource.exportExcel(selectedIds.value)
    const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'split_plan_template.xlsx'
    a.click()
    URL.revokeObjectURL(url)
    await fetchOrders()
  } finally {
    exporting.value = false
  }
}

onMounted(fetchOrders)
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { font-size: 18px; margin-bottom: 12px; }
.filter-row { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; }
.filter-select { padding: 4px 8px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.filter-label { font-size: 12px; color: #555; }
.filter-date { padding: 3px 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; width: 130px; }
.filter-sep { font-size: 12px; color: #888; }
.btn-month { padding: 3px 8px; font-size: 11px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-month:hover { background: #e3f2fd; }
.btn-primary { padding: 6px 16px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.case-no { font-family: monospace; font-size: 11px; }
.empty-state { text-align: center; padding: 32px; color: #999; }
</style>
