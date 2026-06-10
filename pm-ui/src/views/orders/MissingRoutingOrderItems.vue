<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">ルーティング未設定の注文品 <DataSourceDialog title="ルーティング未設定の注文品" :sources="dsSources" /></h1>
        <p class="page-subtitle">受注明細のうち、製品にルーティングが未設定の注文品を一覧表示します。</p>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" :disabled="loading || !filteredItems.length" @click="exportExcel">Excel出力</button>
        <button class="btn-primary" :disabled="loading" @click="load">更新</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-row">
        <label class="filter-item">
          <span>客先</span>
          <select v-model="customerFilter" class="filter-input">
            <option value="">すべて</option>
            <option v-for="option in customerOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>
      <div v-if="loading" class="info-banner">読み込み中...</div>
      <div v-else-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

      <div v-if="!loading && filteredItems.length" class="summary">対象件数: {{ filteredItems.length }}件</div>

      <table v-if="filteredItems.length" class="data-table">
        <thead>
          <tr>
            <th>得意先</th>
            <th>受注番号</th>
            <th>行</th>
            <th>品番</th>
            <th>品名</th>
            <th class="num">数量</th>
            <th>納期</th>
            <th>備考</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredItems" :key="item.id">
            <td>{{ item.customer_name || '-' }}</td>
            <td>{{ item.order_no || '-' }}</td>
            <td>{{ item.line_no }}</td>
            <td>{{ item.product_code || '-' }}</td>
            <td>{{ item.product_name || '-' }}</td>
            <td class="num">{{ formatNumber(item.quantity) }}</td>
            <td>{{ formatDate(item.due_date) }}</td>
            <td>{{ item.remark || '-' }}</td>
          </tr>
        </tbody>
      </table>

      <div v-else-if="!loading" class="no-data">ルーティング未設定の注文品はありません。</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_order', desc: '受注ヘッダ' },
  { op: '読み取り', table: 't_order_line', desc: '受注明細（ルーティング未設定）' },
]

const items = ref([])
const loading = ref(false)
const errorMessage = ref('')
const customerFilter = ref('')

const formatDate = (value) => (value ? String(value).replace(/-/g, '/') : '-')
const formatNumber = (value) => Number(value || 0).toLocaleString()

const normalizeCustomerValue = (value) => String(value ?? '').replace(/\s+/g, ' ').trim().toLowerCase()

const getCustomerInfo = (item) => {
  const customerCode = item.customer_code || item.order?.customer?.customer_code || ''
  const customerName = item.customer_name || item.order?.customer?.customer_name || ''
  const label = [customerCode, customerName].filter(Boolean).join(' ')
  const key = `${normalizeCustomerValue(customerCode)}|${normalizeCustomerValue(customerName)}`
  return { customerCode, customerName, label, key }
}

const customerOptions = computed(() => {
  const map = new Map()
  items.value.forEach((item) => {
    const { key, label } = getCustomerInfo(item)
    if (!key) return
    if (!map.has(key)) map.set(key, { value: key, label })
  })
  return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label, 'ja'))
})

const filteredItems = computed(() => {
  if (!customerFilter.value) return items.value
  const targetKey = normalizeCustomerValue(customerFilter.value)
  return items.value.filter((item) => {
    const { key } = getCustomerInfo(item)
    return key === customerFilter.value || normalizeCustomerValue(key) === targetKey
  })
})

const formatDateForFile = () => {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}${m}${d}`
}

const exportExcel = () => {
  if (!filteredItems.value.length) return

  const rows = filteredItems.value.map((item) => ({
    得意先コード: item.customer_code || item.order?.customer?.customer_code || '',
    得意先名: item.customer_name || item.order?.customer?.customer_name || '',
    受注番号: item.order_no || '',
    行: item.line_no ?? '',
    品番: item.product_code || '',
    品名: item.product_name || '',
    数量: Number(item.quantity || 0),
    納期: item.due_date || '',
    備考: item.remark || '',
  }))

  const worksheet = XLSX.utils.json_to_sheet(rows)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, '未設定品')
  XLSX.writeFile(workbook, `ルーティング未設定注文品_${formatDateForFile()}.xlsx`)
}

const load = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await api.orders.getMissingRoutingOrderItems()
    items.value = Array.isArray(response.data?.results) ? response.data.results : []
  } catch (error) {
    console.error('Failed to load missing routing items', error)
    errorMessage.value = 'ルーティング未設定の注文品の取得に失敗しました。'
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.page-container { padding: 16px; }
.page-header { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:12px; }
.header-actions { display:flex; gap:8px; }
.page-title { margin:0; font-size:22px; }
.page-subtitle { margin:4px 0 0; color:#64748b; font-size:13px; }
.page-content { background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:12px; }
.filter-row { display:flex; flex-wrap:wrap; gap:12px; margin-bottom:12px; }
.filter-item { display:grid; gap:4px; font-size:13px; color:#334155; }
.filter-input { min-width:220px; border:1px solid #cbd5e1; border-radius:8px; padding:8px 10px; background:#fff; }
.summary { color:#1e3a8a; font-size:13px; margin-bottom:8px; }
.data-table { width:100%; border-collapse:collapse; font-size:13px; }
.data-table th, .data-table td { border:1px solid #e2e8f0; padding:8px; text-align:left; vertical-align:top; }
.data-table th { background:#f8fafc; }
.num { text-align:right; }
.info-banner, .error-banner, .no-data { padding:8px 10px; border-radius:8px; font-size:13px; }
.info-banner { background:#eff6ff; color:#1d4ed8; }
.error-banner { background:#fef2f2; color:#b91c1c; }
.no-data { color:#64748b; }
.btn-primary { border:none; border-radius:8px; background:#284b8f; color:#fff; padding:8px 12px; cursor:pointer; }
.btn-primary:disabled { opacity:.6; cursor:not-allowed; }
.btn-secondary { border:1px solid #284b8f; border-radius:8px; background:#fff; color:#284b8f; padding:8px 12px; cursor:pointer; }
.btn-secondary:disabled { opacity:.6; cursor:not-allowed; }
</style>
