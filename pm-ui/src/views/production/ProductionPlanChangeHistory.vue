<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">生産計画変更履歴</h1>
      <div class="page-actions">
        <button class="btn-primary" :disabled="loading" @click="fetchLogs(1)">検索</button>
        <button class="btn-secondary" :disabled="loading" @click="resetFilters">リセット</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>ライン</label>
          <select v-model="filters.line">
            <option value="">すべて</option>
            <option v-for="line in lines" :key="line.id" :value="line.id">
              {{ line.line_code }} - {{ line.line_name }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>計画日 From</label>
          <input type="date" v-model="filters.plan_date_from" />
        </div>
        <div class="filter-field">
          <label>計画日 To</label>
          <input type="date" v-model="filters.plan_date_to" />
        </div>
        <div class="filter-field keyword-field">
          <label>検索</label>
          <input
            v-model="filters.search"
            type="text"
            placeholder="品番・品名・理由・変更者"
            @keyup.enter="fetchLogs(1)"
          />
        </div>
      </div>

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>変更日時</th>
              <th>計画日</th>
              <th>ライン</th>
              <th>工程</th>
              <th>品番</th>
              <th>品名</th>
              <th>順序</th>
              <th>変更前</th>
              <th>変更後</th>
              <th>差分</th>
              <th>理由</th>
              <th>変更者</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id">
              <td>{{ formatDateTime(log.changed_at) }}</td>
              <td>{{ log.plan_date }}</td>
              <td>{{ [log.line_code, log.line_name].filter(Boolean).join(' - ') }}</td>
              <td>{{ [log.process_code, log.process_name].filter(Boolean).join(' - ') }}</td>
              <td>{{ log.product_code || '-' }}</td>
              <td>{{ log.product_name || '' }}</td>
              <td class="num">{{ log.sequence_no ?? '-' }}</td>
              <td class="num">{{ formatNumber(log.before_qty) }}</td>
              <td class="num">{{ formatNumber(log.after_qty) }}</td>
              <td class="num">{{ formatNumber((log.after_qty || 0) - (log.before_qty || 0)) }}</td>
              <td>{{ log.reason || '' }}</td>
              <td>{{ log.changed_by_username || '-' }}</td>
            </tr>
            <tr v-if="!loading && logs.length === 0">
              <td colspan="12" class="no-data">履歴データがありません</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination-controls" v-if="totalPages > 0">
        <button class="btn-secondary" :disabled="loading || currentPage <= 1" @click="fetchLogs(currentPage - 1)">
          前へ
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }} ページ (全 {{ totalCount }} 件)</span>
        <button class="btn-secondary" :disabled="loading || currentPage >= totalPages" @click="fetchLogs(currentPage + 1)">
          次へ
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'

const loading = ref(false)
const logs = ref([])
const lines = ref([])

const currentPage = ref(1)
const totalCount = ref(0)
const pageSize = 20

const filters = ref({
  line: '',
  plan_date_from: '',
  plan_date_to: '',
  search: '',
})

const totalPages = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.ceil(totalCount.value / pageSize)
})

const formatDateTime = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('ja-JP', { hour12: false, timeZone: 'Asia/Tokyo' })
}

const formatNumber = (value) => {
  const num = Number(value ?? 0)
  if (Number.isNaN(num)) return ''
  return num.toLocaleString('ja-JP')
}

const fetchLines = async () => {
  try {
    const response = await api.lines.getProductionLines()
    lines.value = response.data.results || response.data || []
  } catch (error) {
    console.error('ライン取得エラー:', error)
    lines.value = []
  }
}

const fetchLogs = async (page = 1) => {
  const targetPage = typeof page === 'number' && page > 0 ? page : 1
  loading.value = true
  try {
    const params = {
      page: targetPage,
      page_size: pageSize,
      ordering: '-changed_at',
    }
    if (filters.value.line) params.line = filters.value.line
    if (filters.value.plan_date_from) params.plan_date__gte = filters.value.plan_date_from
    if (filters.value.plan_date_to) params.plan_date__lte = filters.value.plan_date_to
    if (filters.value.search?.trim()) params.search = filters.value.search.trim()

    const response = await api.productionPlanChangeLogs.getLogs(params)
    const data = response.data
    if (data?.results) {
      logs.value = data.results
      totalCount.value = data.count || 0
      currentPage.value = targetPage
    } else {
      const list = Array.isArray(data) ? data : []
      logs.value = list
      totalCount.value = list.length
      currentPage.value = 1
    }
  } catch (error) {
    console.error('変更履歴取得エラー:', error)
    logs.value = []
    totalCount.value = 0
    currentPage.value = 1
    alert('生産計画変更履歴の取得に失敗しました')
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.value = {
    line: '',
    plan_date_from: '',
    plan_date_to: '',
    search: '',
  }
  fetchLogs(1)
}

onMounted(async () => {
  await fetchLines()
  await fetchLogs(1)
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 12px;
}

.filter-field {
  display: flex;
  flex-direction: column;
  min-width: 160px;
}

.filter-field label {
  font-size: 12px;
  color: #555;
  margin-bottom: 4px;
}

.filter-field input,
.filter-field select {
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}

.keyword-field {
  min-width: 280px;
}

.table-wrap {
  overflow: auto;
}

.num {
  text-align: right;
}

.no-data {
  text-align: center;
  color: #6b7280;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
}

.page-info {
  font-size: 14px;
  color: #555;
}
</style>

