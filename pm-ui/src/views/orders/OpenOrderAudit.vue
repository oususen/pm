<template>
  <div class="page-container audit-page">
    <div class="page-header">
      <h1 class="page-title">旧OPEN受注洗い出し <DataSourceDialog title="旧OPEN受注洗い出し" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button class="btn-secondary" :disabled="loading" @click="exportCsv">CSV出力</button>
      </div>
    </div>

    <div class="filter-panel">
      <div class="filter-row">
        <label class="filter-item">
          <span>基準納期日</span>
          <input v-model="cutoffDate" class="filter-input" type="date" />
        </label>
        <label class="filter-item">
          <span>得意先</span>
          <select v-model="customerCode" class="filter-input">
            <option value="">すべて</option>
            <option v-for="customer in customerOptions" :key="customer.customer_code" :value="customer.customer_code">
              {{ customer.customer_code }} {{ customer.customer_name }}
            </option>
          </select>
        </label>
        <label class="filter-item">
          <span>受注タイプ</span>
          <select v-model="orderType" class="filter-input">
            <option value="">すべて</option>
            <option value="FIRM">FIRM</option>
            <option value="FORECAST">FORECAST</option>
          </select>
        </label>
        <label class="filter-item">
          <span>納入地</span>
          <input v-model.trim="shipToCode" class="filter-input" type="text" placeholder="ZGHC など" />
        </label>
        <label class="filter-item">
          <span>品番</span>
          <input v-model.trim="productCode" class="filter-input" type="text" placeholder="部分一致" />
        </label>
        <label class="filter-item">
          <span>受注番号</span>
          <input v-model.trim="orderNo" class="filter-input" type="text" placeholder="部分一致" />
        </label>
        <div class="filter-item filter-btn-wrap">
          <span>&nbsp;</span>
          <button class="btn-primary" :disabled="loading" @click="loadRows">検索</button>
        </div>
      </div>
      <div class="hint-box">
        対象は選択得意先の `OPEN` 受注明細です。基準納期日以前の明細を洗い出します。
      </div>
    </div>

    <div class="summary-panel">
      <div class="summary-card">
        <div class="summary-label">受注ヘッダ数</div>
        <div class="summary-value">{{ groupedOrders.length }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">受注明細数</div>
        <div class="summary-value">{{ filteredRows.length }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">数量合計</div>
        <div class="summary-value">{{ formatNumber(totalQuantity) }}</div>
      </div>
    </div>

    <div v-if="loading" class="info-banner">読み込み中...</div>
    <div v-else-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <div v-else class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>受注番号</th>
            <th>受注タイプ</th>
            <th>明細数</th>
            <th>数量合計</th>
            <th>最小納期</th>
            <th>最大納期</th>
            <th>取込ファイル</th>
            <th>明細</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="group in groupedOrders" :key="group.orderNo">
            <tr class="group-row">
              <td>{{ group.orderNo }}</td>
              <td>{{ group.orderType }}</td>
              <td>{{ group.lines.length }}</td>
              <td>{{ formatNumber(group.totalQty) }}</td>
              <td>{{ group.minDueDate }}</td>
              <td>{{ group.maxDueDate }}</td>
              <td>{{ group.sourceFile || '-' }}</td>
              <td>
                <button class="btn-sm" @click="toggleExpanded(group.orderNo)">
                  {{ expandedOrderNos.has(group.orderNo) ? '閉じる' : '表示' }}
                </button>
              </td>
            </tr>
            <tr v-if="expandedOrderNos.has(group.orderNo)" class="detail-row">
              <td colspan="8">
                <table class="detail-table">
                  <thead>
                    <tr>
                      <th>受注タイプ</th>
                      <th>行番号</th>
                      <th>注番</th>
                      <th>品番</th>
                      <th>品名</th>
                      <th>数量</th>
                      <th>納期</th>
                      <th>納入地</th>
                      <th>出荷実績数</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="line in group.lines" :key="line.id">
                      <td>{{ line.effective_order_type || line.order_type || '-' }}</td>
                      <td>{{ line.line_no }}</td>
                      <td>{{ line.customer_order_no || '-' }}</td>
                      <td>{{ line.product_code }}</td>
                      <td>{{ line.product_name || '-' }}</td>
                      <td>{{ formatNumber(line.quantity) }}</td>
                      <td>{{ line.due_date }}</td>
                      <td>{{ line.ship_to_code || '-' }}</td>
                      <td>{{ formatNumber(line.actual_shipment_qty) }}</td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div v-if="!groupedOrders.length" class="no-data">対象データがありません</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_order', desc: '受注ヘッダ（OPEN受注のみ抽出）' },
  { op: '読み取り', table: 't_order_line', desc: '受注明細（旧OPEN受注明細の洗い出し）' },
  { op: '読み取り', table: 'm_customer', desc: '得意先マスタ（絞り込み）' },
]

const cutoffDate = ref('')
const customerCode = ref('')
const orderType = ref('')
const shipToCode = ref('')
const productCode = ref('')
const orderNo = ref('')
const loading = ref(false)
const errorMessage = ref('')
const rows = ref([])
const expandedOrderNos = ref(new Set())
const customerOptions = ref([])

const normalize = (value) => String(value || '').toLowerCase()
const parseNumber = (value) => {
  const num = Number(value || 0)
  return Number.isFinite(num) ? num : 0
}
const formatNumber = (value) => {
  const num = parseNumber(value)
  if (Math.abs(num) < 0.000001) return '0'
  return Number.isInteger(num) ? String(num) : num.toFixed(3).replace(/\.?0+$/, '')
}

const filteredRows = computed(() => {
  return rows.value.filter((row) => {
    if (shipToCode.value && !normalize(row.ship_to_code).includes(normalize(shipToCode.value))) return false
    if (productCode.value && !normalize(row.product_code).includes(normalize(productCode.value))) return false
    if (orderNo.value && !normalize(row.order_no).includes(normalize(orderNo.value))) return false
    return true
  })
})

const groupedOrders = computed(() => {
  const map = new Map()
  for (const row of filteredRows.value) {
    const key = row.order_no
    if (!map.has(key)) {
      map.set(key, {
        orderNo: row.order_no,
        orderType: row.effective_order_type || row.order_type || '-',
        sourceFile: row.source_file,
        lines: [],
        totalQty: 0,
        minDueDate: row.due_date,
        maxDueDate: row.due_date,
      })
    }
    const group = map.get(key)
    group.lines.push(row)
    group.totalQty += parseNumber(row.quantity)
    if (row.due_date < group.minDueDate) group.minDueDate = row.due_date
    if (row.due_date > group.maxDueDate) group.maxDueDate = row.due_date
  }
  return Array.from(map.values()).sort((a, b) => a.maxDueDate.localeCompare(b.maxDueDate) || a.orderNo.localeCompare(b.orderNo))
})

const totalQuantity = computed(() => filteredRows.value.reduce((sum, row) => sum + parseNumber(row.quantity), 0))

const loadCustomers = async () => {
  try {
    const res = await api.customers.getCustomers()
    const list = res.data?.results || res.data || []
    customerOptions.value = [...list].sort((a, b) => {
      return String(a.customer_code || '').localeCompare(String(b.customer_code || ''))
    })
  } catch {
    customerOptions.value = []
  }
}

const loadRows = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const params = {}
    if (cutoffDate.value) params.due_date__lte = cutoffDate.value
    if (customerCode.value) params.customer_code = customerCode.value
    if (orderType.value) params.order_type = orderType.value
    if (shipToCode.value) params.ship_to_code = shipToCode.value
    if (productCode.value) params.product_code = productCode.value
    const res = await api.orders.openOrderAudit(params)
    rows.value = res.data || []
    expandedOrderNos.value = new Set()
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || '旧OPEN受注の取得に失敗しました。'
  } finally {
    loading.value = false
  }
}

const toggleExpanded = (orderNoValue) => {
  const next = new Set(expandedOrderNos.value)
  if (next.has(orderNoValue)) next.delete(orderNoValue)
  else next.add(orderNoValue)
  expandedOrderNos.value = next
}

const exportCsv = () => {
  const header = ['得意先コード', '得意先名', '受注番号', '受注タイプ', '行番号', '注番', '品番', '品名', '数量', '納期', '納入地', '出荷実績数', '取込ファイル']
  const lines = [header.join(',')]
  for (const row of filteredRows.value) {
    const cols = [
      row.customer_code || '',
      row.customer_name || '',
      row.order_no,
      row.effective_order_type || row.order_type || '',
      row.line_no,
      row.customer_order_no || '',
      row.product_code,
      row.product_name || '',
      row.quantity,
      row.due_date,
      row.ship_to_code || '',
      row.actual_shipment_qty,
      row.source_file || '',
    ].map((value) => `"${String(value ?? '').replace(/"/g, '""')}"`)
    lines.push(cols.join(','))
  }
  const blob = new Blob([`\uFEFF${lines.join('\n')}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `旧OPEN受注_${customerCode.value || 'all'}_${cutoffDate.value}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await loadCustomers()
})
</script>

<style scoped>
.audit-page {
  padding: 16px;
}

.page-actions {
  display: flex;
  gap: 8px;
}

.filter-panel {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #f8fbff;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-item {
  min-width: 180px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #475569;
}

.filter-input {
  padding: 6px 8px;
  border: 1px solid #cfd8e3;
  border-radius: 4px;
  background: #fff;
}

.filter-btn-wrap {
  min-width: auto;
  justify-content: flex-end;
}

.hint-box {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
}

.summary-panel {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.summary-card {
  min-width: 140px;
  padding: 10px 12px;
  border: 1px solid #d8e3f0;
  border-radius: 8px;
  background: #fff;
}

.summary-label {
  font-size: 12px;
  color: #64748b;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.table-wrap {
  overflow: auto;
}

.group-row {
  background: #f8fbff;
}

.detail-row td {
  padding: 0 !important;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
}

.detail-table th,
.detail-table td {
  border: 1px solid #e2e8f0;
  padding: 6px 8px;
  font-size: 12px;
}

.info-banner,
.error-banner,
.no-data {
  margin-top: 10px;
  font-size: 13px;
}

@media (max-width: 900px) {
  .summary-panel {
    flex-wrap: wrap;
  }
}
</style>
