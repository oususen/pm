<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">安全在庫一覧</h1>
        <p class="helper-text">
          品番ごとの安全在庫（最小在庫）と在庫不足状況を確認します。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn-secondary" @click="loadRows">再読込</button>
        <button class="btn-secondary" @click="downloadCsv">CSV出力</button>
        <button class="btn-primary" @click="goAllocationList">在庫引当一覧へ</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-row">
          <div class="filter-field wide">
            <label>品番/品名</label>
            <input
              v-model="filters.search"
              placeholder="品番・品名で検索"
              @keyup.enter="loadRows"
            />
          </div>
          <div class="filter-field">
            <label>保管場所</label>
            <input
              v-model="filters.location"
              placeholder="保管場所"
              @keyup.enter="loadRows"
            />
          </div>
          <div class="filter-field checkbox-field">
            <label>
              <input v-model="filters.shortageOnly" type="checkbox" />
              安全在庫割れのみ
            </label>
          </div>
          <div class="filter-actions">
            <button class="btn-primary" @click="loadRows">検索</button>
            <button class="btn-secondary" @click="resetFilters">リセット</button>
          </div>
        </div>
      </div>

      <div class="summary-bar">
        <span>件数: {{ filteredRows.length }} / {{ rows.length }}</span>
        <span :class="{ 'text-danger': shortageCount > 0 }">
          安全在庫割れ: {{ shortageCount }}件
        </span>
      </div>

      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>品番</th>
              <th>品名</th>
              <th>保管場所</th>
              <th class="text-right">現在在庫</th>
              <th class="text-right">引当済</th>
              <th class="text-right">可用在庫</th>
              <th class="text-right">安全在庫</th>
              <th class="text-right">不足数</th>
              <th>更新日時</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="row.id">
              <td>{{ row.product_code }}</td>
              <td>{{ row.product_name }}</td>
              <td>{{ row.location }}</td>
              <td class="text-right">{{ formatNumber(row.current_stock) }}</td>
              <td class="text-right">{{ formatNumber(row.reserved_qty) }}</td>
              <td class="text-right" :class="{ 'text-danger': isShortage(row) }">
                {{ formatNumber(row.available_qty) }}
              </td>
              <td class="text-right">{{ formatNumber(row.min_stock_qty) }}</td>
              <td class="text-right" :class="{ 'text-danger': isShortage(row) }">
                {{ formatNumber(shortageQty(row)) }}
              </td>
              <td>{{ formatDateTime(row.updated_at) }}</td>
              <td>
                <button
                  class="btn-sm"
                  :disabled="!canEdit"
                  @click="goEdit(row.id)"
                >
                  編集
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!filteredRows.length" class="no-data">
        条件に合致するデータがありません
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const router = useRouter()
const rows = ref([])
const filters = reactive({
  search: '',
  location: '',
  shortageOnly: false,
})

const canEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === 'production.stock_allocations')) {
    return hasPermission(user, 'production.stock_allocations', 'edit')
  }
  return hasPermission(user, 'production', 'edit')
})

const toNumber = (value) => Number(value || 0)
const shortageQty = (row) => {
  const shortage = toNumber(row.min_stock_qty) - toNumber(row.available_qty)
  return shortage > 0 ? shortage : 0
}
const isShortage = (row) => shortageQty(row) > 0

const filteredRows = computed(() =>
  rows.value.filter((row) => {
    if (filters.shortageOnly && !isShortage(row)) return false
    return true
  })
)

const shortageCount = computed(() => rows.value.filter((row) => isShortage(row)).length)

const loadRows = async () => {
  try {
    const params = { page_size: 20000 }
    if (filters.search) params.search = filters.search
    if (filters.location) params.location = filters.location
    const res = await api.orders.getStockAllocations(params)
    const data = Array.isArray(res.data) ? res.data : (res.data?.results || [])
    rows.value = data
  } catch (error) {
    console.error('安全在庫一覧の取得に失敗', error)
    alert('安全在庫一覧の取得に失敗しました。')
  }
}

const resetFilters = () => {
  filters.search = ''
  filters.location = ''
  filters.shortageOnly = false
  loadRows()
}

const goEdit = (id) => {
  if (!canEdit.value) return
  router.push(`/production/stock-allocations/${id}/edit`)
}

const goAllocationList = () => {
  router.push('/production/stock-allocations')
}

const downloadCsv = () => {
  if (!filteredRows.value.length) {
    alert('出力対象がありません')
    return
  }
  const header = [
    'product_code',
    'product_name',
    'location',
    'current_stock',
    'reserved_qty',
    'available_qty',
    'min_stock_qty',
    'shortage_qty',
    'updated_at',
  ]
  const lines = filteredRows.value.map((row) =>
    [
      row.product_code,
      row.product_name,
      row.location,
      row.current_stock,
      row.reserved_qty,
      row.available_qty,
      row.min_stock_qty,
      shortageQty(row),
      row.updated_at,
    ]
      .map((value) => `"${String(value ?? '').replace(/"/g, '""')}"`)
      .join(',')
  )
  const csv = [header.join(','), ...lines].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'safety_stock_list.csv'
  a.click()
  window.URL.revokeObjectURL(url)
}

const formatNumber = (value) =>
  Number(value || 0).toLocaleString('ja-JP', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  })

const formatDateTime = (value) => {
  if (!value) return ''
  return new Date(value).toLocaleString('ja-JP')
}

onMounted(() => {
  loadRows()
})
</script>

<style scoped>
.header-left {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.helper-text {
  margin: 0;
  color: #5c6670;
  font-size: 0.9rem;
}

.filter-bar {
  background: #fff;
  border: 1px solid #e3e7eb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.filter-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) 220px;
  gap: 12px;
  align-items: end;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-field.wide {
  grid-column: span 1;
}

.filter-field input {
  padding: 8px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
}

.checkbox-field {
  justify-content: center;
}

.filter-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.summary-bar {
  display: flex;
  gap: 16px;
  font-size: 0.95rem;
  margin-bottom: 8px;
}

.table-wrapper {
  overflow: auto;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e3e7eb;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead {
  background: #f8fafc;
}

.data-table th,
.data-table td {
  padding: 10px;
  border-bottom: 1px solid #edf1f5;
}

.text-right {
  text-align: right;
}

.text-danger {
  color: #d13438;
  font-weight: 700;
}

@media (max-width: 900px) {
  .filter-row {
    grid-template-columns: 1fr;
  }

  .filter-actions {
    justify-content: flex-start;
  }
}
</style>
