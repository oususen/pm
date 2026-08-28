<template>
  <div class="results-page">
    <div class="caption">棚卸結果確認</div>

    <div class="filters">
      <label class="filter-field">
        <span>棚卸日</span>
        <input v-model="filters.stocktake_date" type="date" />
      </label>
      <label class="filter-field">
        <span>エリア</span>
        <select v-model="filters.area_name">
          <option value="">すべて</option>
          <option v-for="a in areaChoices" :key="a" :value="a">{{ a }}</option>
        </select>
      </label>
      <label class="filter-field">
        <span>品番</span>
        <input v-model="filters.product_code" type="text" placeholder="品番" @keyup.enter="load" />
      </label>
      <label class="filter-field">
        <span>置き場</span>
        <select v-model="filters.stock_location">
          <option value="">すべて</option>
          <option v-for="loc in locationChoices" :key="loc" :value="loc">{{ loc }}</option>
        </select>
      </label>
      <button class="btn" @click="load" :disabled="loading">検索</button>
      <button type="button" class="btn btn-mode" @click="toggleMode">
        表示: {{ isSummary ? '合計' : '分行' }}
      </button>
    </div>

    <div v-if="loading" class="center">読み込み中...</div>
    <div v-else-if="error" class="center error">{{ error }}</div>
    <div v-else>
      <p class="count">{{ displayRows.length }} 件</p>
      <div class="table-wrap">
        <!-- 合計モード -->
        <table v-if="isSummary" class="grid">
          <thead>
            <tr>
              <th class="col-code">品番</th>
              <th class="col-name">品名</th>
              <th class="col-area">入力エリア</th>
              <th class="col-loc">置き場</th>
              <th class="col-num">机上在庫</th>
              <th class="col-num">机上進度</th>
              <th class="col-num">現物数</th>
              <th class="col-num">差異</th>
              <th class="col-cnt">入力件数</th>
              <th class="col-person">最終入力者</th>
              <th class="col-date">最終更新日時</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in displayRows" :key="row.product_id">
              <td>{{ row.product_code }}</td>
              <td>{{ row.product_name || '-' }}</td>
              <td>{{ row.area_names || '-' }}</td>
              <td>{{ row.stock_locations || '-' }}</td>
              <td class="num">{{ row.system_stock_qty }}</td>
              <td class="num">{{ row.system_progress_qty }}</td>
              <td class="num">{{ row.actual_stock_qty }}</td>
              <td class="num" :class="diffClass(row.diff_qty)">{{ formatSigned(row.diff_qty) }}</td>
              <td class="num">{{ row.record_count }}</td>
              <td>{{ row.updated_by_name || '-' }}</td>
              <td>{{ formatDatetime(row.updated_at) }}</td>
            </tr>
            <tr v-if="displayRows.length === 0">
              <td colspan="11" class="center">データなし</td>
            </tr>
          </tbody>
        </table>
        <!-- 分行モード -->
        <table v-else class="grid">
          <thead>
            <tr>
              <th class="col-code">品番</th>
              <th class="col-name">品名</th>
              <th class="col-area">入力エリア</th>
              <th class="col-loc">置き場</th>
              <th class="col-num">机上在庫</th>
              <th class="col-num">机上進度</th>
              <th class="col-num">現物数</th>
              <th class="col-person">記入者</th>
              <th class="col-person">カウンター</th>
              <th class="col-note">備考</th>
              <th class="col-person">更新者</th>
              <th class="col-date">更新日時</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in displayRows" :key="row.id">
              <td>{{ row.product_code }}</td>
              <td>{{ row.product_name || '-' }}</td>
              <td>{{ row.area_name || '-' }}</td>
              <td>{{ row.stock_locations || '-' }}</td>
              <td class="num">{{ row.system_stock_qty }}</td>
              <td class="num">{{ row.system_progress_qty }}</td>
              <td class="num">{{ row.actual_stock_qty }}</td>
              <td>{{ row.recorder_name || '-' }}</td>
              <td>{{ row.counter_name || '-' }}</td>
              <td>{{ row.note || '-' }}</td>
              <td>{{ row.updated_by_name || '-' }}</td>
              <td>{{ formatDatetime(row.updated_at) }}</td>
            </tr>
            <tr v-if="displayRows.length === 0">
              <td colspan="12" class="center">データなし</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '@/api/client'

const today = new Date()
const yyyy = today.getFullYear()
const mm = String(today.getMonth() + 1).padStart(2, '0')
const dd = String(today.getDate()).padStart(2, '0')

const filters = ref({
  stocktake_date: `${yyyy}-${mm}-${dd}`,
  area_name: '',
  product_code: '',
  stock_location: '',
})
const rawRows = ref([])
const areaChoices = ref([])
const locationChoices = ref([])
const loading = ref(false)
const error = ref('')
const isSummary = ref(true)

const toggleMode = () => { isSummary.value = !isSummary.value }

const summaryRows = computed(() => {
  const groups = {}
  for (const r of rawRows.value) {
    const pid = r.product_id
    if (!groups[pid]) {
      groups[pid] = {
        product_id: pid,
        product_code: r.product_code,
        product_name: r.product_name,
        stock_locations: r.stock_locations,
        system_stock_qty: r.system_stock_qty,
        system_progress_qty: r.system_progress_qty,
        actual_stock_qty: 0,
        record_count: 0,
        area_set: new Set(),
        updated_by_name: '',
        updated_at: null,
      }
    }
    const g = groups[pid]
    g.actual_stock_qty += r.actual_stock_qty
    g.record_count++
    if (r.area_name) g.area_set.add(r.area_name)
    if (!g.updated_at || r.updated_at > g.updated_at) {
      g.updated_at = r.updated_at
      g.updated_by_name = r.updated_by_name
    }
  }
  return Object.values(groups)
    .map(g => ({
      ...g,
      area_names: [...g.area_set].sort().join(', '),
      diff_qty: g.actual_stock_qty - g.system_stock_qty,
    }))
    .sort((a, b) => a.product_code.localeCompare(b.product_code))
})

const displayRows = computed(() => isSummary.value ? summaryRows.value : rawRows.value)

const formatDatetime = (val) => {
  if (!val) return '-'
  return val.replace('T', ' ').slice(0, 16)
}

const formatSigned = (value) => {
  const num = Number(value || 0)
  if (num > 0) return `+${num}`
  return `${num}`
}

const diffClass = (val) => ({
  positive: val > 0,
  negative: val < 0,
})

const load = async () => {
  if (!filters.value.stocktake_date) {
    error.value = '棚卸日を指定してください'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const params = { stocktake_date: filters.value.stocktake_date }
    if (filters.value.area_name) params.area_name = filters.value.area_name
    if (filters.value.product_code) params.product_code = filters.value.product_code
    if (filters.value.stock_location) params.stock_location = filters.value.stock_location
    const res = await api.stocktakeRecords.results(params)
    rawRows.value = res.data.rows || []
    areaChoices.value = res.data.area_choices || []
    locationChoices.value = res.data.location_choices || []
  } catch (e) {
    error.value = e?.response?.data?.detail || '取得に失敗しました'
  } finally {
    loading.value = false
  }
}

load()
</script>

<style scoped>
.results-page {
  padding: 12px 10px 18px;
  background: #efefdc;
  min-height: 100%;
}
.caption {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 10px;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
  margin-bottom: 12px;
}
.filter-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 13px;
}
.filter-field input,
.filter-field select {
  padding: 4px 6px;
  border: 1px solid #c7ced9;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
}
.btn {
  padding: 5px 14px;
  background: #334155;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn:disabled {
  opacity: 0.5;
}
.btn-mode {
  background: #1e40af;
}
.center {
  text-align: center;
  padding: 24px 0;
  color: #64748b;
}
.error {
  color: #dc2626;
}
.count {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 6px;
}
.table-wrap {
  overflow-x: auto;
}
.grid {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.grid th,
.grid td {
  border: 1px solid #c7ced9;
  padding: 4px 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.grid th {
  background: #e2e8f0;
  font-weight: 600;
  text-align: center;
  position: sticky;
  top: 0;
  z-index: 1;
}
.grid tbody tr:nth-child(even) {
  background: #f8fafc;
}
.grid tbody tr:hover {
  background: #e0f2fe;
}
.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.positive {
  color: #2563eb;
  font-weight: 600;
}
.negative {
  color: #dc2626;
  font-weight: 600;
}
.col-code { width: 160px; }
.col-name { width: 160px; }
.col-area { width: 100px; }
.col-loc { width: 100px; }
.col-num { width: 80px; }
.col-cnt { width: 70px; }
.col-person { width: 90px; }
.col-date { width: 140px; }
.col-note { width: 150px; }
</style>
