<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">消耗品 入出庫履歴 <DataSourceDialog title="消耗品 入出庫履歴" :sources="dsSources" /></h1>
      <button class="btn-primary" :disabled="loading" @click="fetchAll">更新</button>
    </div>

    <div class="filter-bar">
      <label>期間（業務日）: <input v-model="filters.date_from" type="date" /> ～ <input v-model="filters.date_to" type="date" /></label>
      <label>区分:
        <select v-model="filters.movement_type">
          <option value="">すべて</option>
          <option value="outbound">出庫</option>
          <option value="inbound">入庫</option>
        </select>
      </label>
      <label>集計階層:
        <select v-model="filters.org_level">
          <option v-for="l in orgLevels" :key="l.key" :value="l.key">{{ l.label }}</option>
        </select>
      </label>
      <label>検索: <input v-model="filters.search" placeholder="コード/品名/作業者/備考" @keyup.enter="fetchAll" /></label>
      <button class="btn-primary" @click="fetchAll">検索</button>
    </div>

    <!-- 部署別集計 -->
    <div class="section-title">{{ orgLevelLabel }}別集計 <small>（行をクリックで明細を絞り込み）</small></div>
    <table class="data-table summary-table">
      <thead>
        <tr><th>{{ orgLevelLabel }}</th><th>出庫 件数</th><th>出庫 数量</th><th>出庫 金額</th><th>入庫 件数</th><th>入庫 数量</th><th>入庫 金額</th></tr>
      </thead>
      <tbody>
        <tr
          v-for="row in summaryRows"
          :key="row.org_name"
          :class="['clickable', { selected: selectedOrg === row.org_name }]"
          @click="toggleOrg(row.org_name)"
        >
          <td>{{ row.org_name }}</td>
          <td class="num">{{ row.outbound.count }}</td>
          <td class="num">{{ row.outbound.quantity }}</td>
          <td class="num">{{ formatPrice(row.outbound.total_amount) }}</td>
          <td class="num">{{ row.inbound.count }}</td>
          <td class="num">{{ row.inbound.quantity }}</td>
          <td class="num">{{ formatPrice(row.inbound.total_amount) }}</td>
        </tr>
      </tbody>
    </table>

    <!-- 明細 -->
    <div class="section-title">
      明細 {{ movements.length }}件
      <span v-if="selectedOrg">（{{ orgLevelLabel }}: {{ selectedOrg }} <button class="btn-link" @click="toggleOrg(selectedOrg)">解除</button>）</span>
    </div>
    <div v-if="loading" class="loading-message">読み込み中...</div>
    <table v-else class="data-table">
      <thead>
        <tr>
          <th>日時</th><th>区分</th><th>コード</th><th>品名</th><th>数量</th><th>処理後在庫</th><th>金額</th>
          <th>作業者</th><th>{{ orgLevelLabel }}</th><th>使用ライン</th><th>備考</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in movements" :key="m.id">
          <td class="nowrap">{{ formatDateTime(m.moved_at) }}</td>
          <td :class="m.movement_type">{{ m.movement_type_label }}<span v-if="m.inbound_type_label">（{{ m.inbound_type_label }}）</span></td>
          <td class="mono">{{ m.consumable_code }}</td>
          <td>{{ m.consumable_name }}</td>
          <td class="num">{{ m.quantity }} {{ m.unit }}</td>
          <td class="num">{{ m.stock_after }}</td>
          <td class="num">{{ formatPrice(m.total_amount) }}</td>
          <td>{{ m.worker_name }}</td>
          <td>{{ m[orgField] || '（未設定）' }}</td>
          <td>{{ m.usage_line }}</td>
          <td>{{ m.note }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import { businessToday, formatDateTime, formatPrice, rowsOf, toLocalDateString } from './consumableUtils'

const dsSources = [
  { op: '読み', table: 't_consumable_stock_movement', desc: '入出庫履歴（部署名は記録時点の値）' },
]

const orgLevels = [
  { key: 'team', label: '班', field: 'team_name' },
  { key: 'group', label: '係', field: 'group_name' },
  { key: 'unit', label: 'グループ', field: 'unit_name' },
  { key: 'division', label: '事業部', field: 'division_name' },
]

const today = businessToday()
const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
const filters = ref({
  date_from: toLocalDateString(monthStart),
  date_to: toLocalDateString(today),
  movement_type: '',
  org_level: 'team',
  search: '',
})
const selectedOrg = ref('')
const movements = ref([])
const summary = ref([])
const loading = ref(false)

const orgLevelLabel = computed(() => orgLevels.find((l) => l.key === filters.value.org_level).label)
const orgField = computed(() => orgLevels.find((l) => l.key === filters.value.org_level).field)

const summaryRows = computed(() => {
  const empty = () => ({ count: 0, quantity: 0, total_amount: 0 })
  const map = new Map()
  summary.value.forEach((r) => {
    if (!map.has(r.org_name)) map.set(r.org_name, { org_name: r.org_name, outbound: empty(), inbound: empty() })
    map.get(r.org_name)[r.movement_type] = r
  })
  return [...map.values()]
})

const baseParams = () => {
  const params = {}
  Object.entries(filters.value).forEach(([k, v]) => {
    if (v) params[k] = v
  })
  return params
}

async function fetchMovements() {
  loading.value = true
  try {
    const params = { ...baseParams(), page_size: 0 }
    // 「（未設定）」は空文字の部署で絞り込む
    if (selectedOrg.value) params.org_name = selectedOrg.value === '（未設定）' ? '' : selectedOrg.value
    movements.value = rowsOf(await api.consumables.listMovements(params))
  } finally {
    loading.value = false
  }
}

async function fetchSummary() {
  summary.value = (await api.consumables.summarizeMovements(baseParams())).data
}

function fetchAll() {
  fetchSummary()
  fetchMovements()
}

function toggleOrg(name) {
  selectedOrg.value = selectedOrg.value === name ? '' : name
  fetchMovements()
}

watch(() => filters.value.org_level, () => {
  selectedOrg.value = ''
  fetchAll()
})

onMounted(fetchAll)
</script>

<style scoped>
.page-container { padding: 12px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.page-title { font-size: 1.2em; margin: 0; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 8px; font-size: 0.85em; }
.section-title { font-weight: 600; margin: 8px 0 4px; font-size: 0.9em; }
.section-title small { font-weight: normal; color: #777; }
.btn-primary { background: #1565c0; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-link { border: none; background: none; color: #1565c0; cursor: pointer; text-decoration: underline; }
.loading-message { padding: 12px; color: #666; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
.data-table th, .data-table td { padding: 3px 6px; border: 1px solid #ddd; text-align: left; }
.data-table th { background: #f5f5f5; white-space: nowrap; }
.data-table .num { text-align: right; white-space: nowrap; }
.data-table .mono { font-family: monospace; }
.data-table .nowrap { white-space: nowrap; }
.summary-table { width: auto; min-width: 60%; }
.clickable { cursor: pointer; }
.clickable:hover { background: #f0f6ff; }
.selected { background: #e3f2fd; }
td.outbound { color: #e65100; }
td.inbound { color: #2e7d32; }
</style>
