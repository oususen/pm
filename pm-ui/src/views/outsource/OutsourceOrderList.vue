<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">FB受注一覧 <DataSourceDialog title="FB受注一覧" :sources="dsSources" /></h2>
      <RouterLink to="/outsource/orders/import" class="btn-primary">受注取込</RouterLink>
    </div>

    <div class="filter-row">
      <select v-model="filterStatus" @change="fetchOrders" class="filter-select">
        <option value="">全ステータス</option>
        <option value="IMPORTED">取込済</option>
        <option value="SENT_TO_SUB">展開送付済</option>
        <option value="SPLIT_REGISTERED">分割計画登録済</option>
        <option value="IN_PROGRESS">加工中</option>
        <option value="COMPLETED">完了</option>
      </select>
      <button class="btn-month" @click="shiftMonth(-1)">◀ 前月</button>
      <label class="filter-label">塗装日:</label>
      <input type="date" v-model="paintingFrom" @change="fetchOrders" class="filter-date" />
      <span class="filter-sep">〜</span>
      <input type="date" v-model="paintingTo" @change="fetchOrders" class="filter-date" />
      <button class="btn-month" @click="shiftMonth(1)">次月 ▶</button>
      <input
        v-model="searchText"
        @input="debouncedFetch"
        placeholder="品目コード・品番・名称で検索"
        class="search-input"
      />
    </div>

    <table class="data-table" v-if="orders.length">
      <thead>
        <tr>
          <th>案件番号</th>
          <th>品目コード</th>
          <th>品番</th>
          <th>品目名称</th>
          <th>数量</th>
          <th>塗装名</th>
          <th>塗装日</th>
          <th>最早着手</th>
          <th>最遅完了日</th>
          <th>ステータス</th>
          <th>分割数</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="o in orders" :key="o.id" @click="goDetail(o.id)" class="clickable-row">
          <td class="case-no">{{ o.case_no }}</td>
          <td>{{ o.item_code }}</td>
          <td>{{ o.product_number || '-' }}</td>
          <td>{{ o.item_name }}</td>
          <td class="text-right">{{ o.order_qty }}</td>
          <td>{{ o.painting_name }}</td>
          <td>{{ o.painting_date }}</td>
          <td>{{ o.earliest_start || '-' }}</td>
          <td>{{ o.latest_finish || '-' }}</td>
          <td><span class="status-badge" :class="'st-' + o.status">{{ statusLabel(o.status) }}</span></td>
          <td class="text-center">{{ o.split_count || 0 }}</td>
        </tr>
      </tbody>
    </table>

    <div v-else-if="!loading" class="empty-state">データがありません</div>
    <div v-if="loading" class="loading">読み込み中...</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_outsource_order / t_outsource_order_line', desc: '受注一覧の取得' },
]

const router = useRouter()
const orders = ref([])
const loading = ref(false)
const filterStatus = ref('')
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
  fetchOrders()
}
const searchText = ref('')

let debounceTimer = null
function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(fetchOrders, 300)
}

const STATUS_MAP = {
  IMPORTED: '取込済',
  SENT_TO_SUB: '展開送付済',
  SPLIT_REGISTERED: '分割登録済',
  IN_PROGRESS: '加工中',
  COMPLETED: '完了',
}

function statusLabel(s) { return STATUS_MAP[s] || s }

async function fetchOrders() {
  loading.value = true
  try {
    const params = {}
    if (filterStatus.value) params.status = filterStatus.value
    if (paintingFrom.value) params.painting_date_from = paintingFrom.value
    if (paintingTo.value) params.painting_date_to = paintingTo.value
    if (searchText.value) params.search = searchText.value
    const res = await api.outsource.getOrders(params)
    orders.value = res.data.results || res.data
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

function goDetail(id) {
  router.push(`/outsource/orders/${id}`)
}

onMounted(fetchOrders)
</script>

<style scoped>
.page-container { padding: 16px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.page-title { font-size: 18px; }
.btn-primary {
  padding: 6px 14px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 4px;
  text-decoration: none;
  font-size: 13px;
}

.filter-row { display: flex; gap: 8px; margin-bottom: 12px; }
.filter-select, .search-input {
  padding: 4px 8px;
  font-size: 13px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.filter-label { font-size: 12px; color: #555; }
.filter-date { padding: 3px 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; width: 130px; }
.filter-sep { font-size: 12px; color: #888; }
.btn-month { padding: 3px 8px; font-size: 11px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-month:hover { background: #e3f2fd; }
.search-input { width: 220px; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; white-space: nowrap; }
.data-table th { background: #f5f5f5; position: sticky; top: 0; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.case-no { font-family: monospace; font-size: 11px; }
.clickable-row { cursor: pointer; }
.clickable-row:hover { background: #f0f7ff; }

.status-badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.st-IMPORTED { background: #e3f2fd; color: #1565c0; }
.st-SENT_TO_SUB { background: #fff3e0; color: #e65100; }
.st-SPLIT_REGISTERED { background: #e8f5e9; color: #2e7d32; }
.st-IN_PROGRESS { background: #fce4ec; color: #c62828; }
.st-COMPLETED { background: #f5f5f5; color: #616161; }

.empty-state, .loading { text-align: center; padding: 32px; color: #999; font-size: 14px; }
</style>
