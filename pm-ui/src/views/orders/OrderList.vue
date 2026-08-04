<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">受注一覧 <DataSourceDialog title="受注一覧" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button @click="fetchOrders" class="btn-primary">更新</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-panel">
        <div class="filter-row">
          <label class="filter-item">
            <span>受注番号</span>
            <input v-model="filters.orderNo" class="filter-input" type="text" />
          </label>
          <label class="filter-item">
            <span>取込ファイル</span>
            <input v-model="filters.sourceFile" class="filter-input" type="text" />
          </label>
          <label class="filter-item">
            <span>得意先</span>
            <select v-model="filters.customer" class="filter-input">
              <option value="">すべて</option>
              <option v-for="option in customerOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
        <div class="filter-row">
          <label class="filter-item">
            <span>受注タイプ</span>
            <select v-model="filters.orderType" class="filter-input">
              <option value="">すべて</option>
              <option v-for="option in orderTypeOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
          <label class="filter-item">
            <span>受注日</span>
            <input v-model="filters.orderDate" class="filter-input" type="date" />
          </label>
          <label class="filter-item">
            <span>ステータス</span>
            <select v-model="filters.status" class="filter-input">
              <option value="">すべて</option>
              <option v-for="option in statusOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
        <div class="filter-row">
          <label class="filter-item">
            <span>製品コード</span>
            <input v-model="filters.productCode" class="filter-input" type="text" placeholder="部分一致" />
          </label>
          <label class="filter-item">
            <span>納期</span>
            <div style="display:flex;gap:4px;align-items:center">
              <input v-model="filters.dueDateFrom" class="filter-input" type="date" />
              <span>～</span>
              <input v-model="filters.dueDateTo" class="filter-input" type="date" />
            </div>
          </label>
          <label class="filter-item">
            <span>納入地</span>
            <input v-model="filters.shipToCode" class="filter-input" type="text" placeholder="部分一致" />
          </label>
        </div>
        <div class="filter-actions">
          <button type="button" class="btn-secondary" @click="resetFilters">クリア</button>
        </div>
      </div>
      <div v-if="loading" class="info-banner">読み込み中...</div>
      <div v-else-if="errorMessage" class="error-banner">{{ errorMessage }}</div>
      <table class="data-table">
        <thead>
          <tr>
            <th>受注番号</th>
            <th>取込ファイル</th>
            <th>得意先</th>
            <th>受注タイプ</th>
            <th>版番号</th>
            <th>受注日</th>
            <th>ステータス</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in filteredOrders" :key="order.id">
            <td>{{ order.order_no }}</td>
            <td>{{ order.source_file || '-' }}</td>
            <td>{{ order.customer_name }}</td>
            <td>{{ order.order_type_display }}</td>
            <td>{{ order.version_no }}</td>
            <td>{{ order.order_date || '-' }}</td>
            <td>{{ order.status_display }}</td>
            <td>
              <button @click="viewDetails(order)" class="btn-sm">詳細</button>
              <button v-if="canDelete && order.status === 'OPEN'" @click="confirmClose(order)" class="btn-sm btn-warning">クローズ</button>
              <button v-if="canDelete" @click="confirmDelete(order)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!loading && !errorMessage && filteredOrders.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 詳細ダイアログ -->
    <div v-if="showDetailsDialog" class="modal-overlay" @click.self="closeDetailsDialog">
      <div class="modal-content modal-large">
        <h2>受注詳細</h2>
        <div class="details-section">
          <p><strong>受注番号:</strong> {{ selectedOrder.order_no }}</p>
          <p><strong>得意先:</strong> {{ selectedOrder.customer_name }}</p>
          <p><strong>受注タイプ:</strong> {{ selectedOrder.order_type_display }}</p>
          <p><strong>版番号:</strong> {{ selectedOrder.version_no }}</p>
          <p><strong>受注日:</strong> {{ selectedOrder.order_date || '-' }}</p>
          <p><strong>ステータス:</strong> {{ selectedOrder.status_display }}</p>
          <p><strong>取込ファイル:</strong> {{ selectedOrder.source_file || '-' }}</p>
          <p><strong>取込システム:</strong> {{ selectedOrder.source_system || '-' }}</p>
        </div>
        <h3>受注明細</h3>
        <div class="detail-filter-row">
          <label class="detail-filter-item">
            <span>注番</span>
            <input v-model="lineFilters.customerOrderNo" class="filter-input" type="text" />
          </label>
          <label class="detail-filter-item">
            <span>製品コード</span>
            <input v-model="lineFilters.productCode" class="filter-input" type="text" />
          </label>
          <label class="detail-filter-item">
            <span>納期</span>
            <div style="display:flex;gap:4px;align-items:center">
              <input v-model="lineFilters.dueDateFrom" class="filter-input" type="date" />
              <span>～</span>
              <input v-model="lineFilters.dueDateTo" class="filter-input" type="date" />
            </div>
          </label>
          <label class="detail-filter-item" style="flex:0 1 75px;min-width:75px">
            <span>納入地</span>
            <input v-model="lineFilters.shipToCode" class="filter-input" type="text" />
          </label>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>行番号</th>
              <th>注番</th>
              <th>製品コード</th>
              <th>製品名</th>
              <th>数量</th>
              <th>納期</th>
              <th>納入地</th>
              <th>備考</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in filteredOrderLines" :key="line.id">
              <td>{{ line.line_no }}</td>
              <td>{{ line.customer_order_no || '-' }}</td>
              <td>{{ line.product_code }}</td>
              <td>{{ line.product_name || '-' }}</td>
              <td>{{ Math.round(Number(line.quantity)) }}</td>
              <td>{{ line.due_date }}</td>
              <td>{{ line.ship_to_code || '-' }}</td>
              <td>{{ line.remark || '-' }}</td>
              <td>
                <button
                  v-if="canDelete"
                  type="button"
                  class="btn-sm btn-danger"
                  @click="deleteOrderLine(line)"
                >削除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="form-actions">
          <button type="button" @click="closeDetailsDialog" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_order', desc: '受注ヘッダ' },
  { op: '読み取り', table: 't_order_line', desc: '受注明細' },
]

const canDelete = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const entry = permissions.find((item) => item.resource === 'orders.list')
  if (entry) return Boolean(entry.can_edit)
  return hasPermission(user, 'orders', 'edit')
})

const orders = ref([])
const showDetailsDialog = ref(false)
const selectedOrder = ref({})
const orderLines = ref([])
const lineFilters = ref({ customerOrderNo: '', productCode: '', dueDateFrom: '', dueDateTo: '', shipToCode: '' })
const loading = ref(false)
const errorMessage = ref('')
const filters = ref({
  orderNo: '',
  sourceFile: '',
  customer: '',
  orderType: '',
  orderDate: '',
  status: '',
  productCode: '',
  dueDateFrom: '',
  dueDateTo: '',
  shipToCode: '',
})

const normalizeText = (value) => (value ?? '').toString().toLowerCase()

const resolveOrderType = (order) => order.order_type || order.order_type_display || ''
const resolveStatus = (order) => order.status || order.status_display || ''
const resolveCustomer = (order) => order.customer_name || ''

const orderTypeOptions = computed(() => {
  const options = new Map()
  orders.value.forEach((order) => {
    const value = resolveOrderType(order)
    if (!value) return
    const label = order.order_type_display || value
    if (!options.has(value)) {
      options.set(value, { value, label })
    }
  })
  return Array.from(options.values())
})

const statusOptions = computed(() => {
  const options = new Map()
  orders.value.forEach((order) => {
    const value = resolveStatus(order)
    if (!value) return
    const label = order.status_display || value
    if (!options.has(value)) {
      options.set(value, { value, label })
    }
  })
  return Array.from(options.values())
})

const customerOptions = computed(() => {
  const options = new Map()
  orders.value.forEach((order) => {
    const value = resolveCustomer(order)
    if (!value) return
    if (!options.has(value)) {
      options.set(value, { value, label: value })
    }
  })
  return Array.from(options.values())
})

const filteredOrders = computed(() => {
  const currentFilters = filters.value
  return orders.value.filter((order) => {
    if (
      currentFilters.sourceFile &&
      !normalizeText(order.source_file).includes(normalizeText(currentFilters.sourceFile))
    ) {
      return false
    }
    if (currentFilters.customer && resolveCustomer(order) !== currentFilters.customer) {
      return false
    }
    if (currentFilters.orderType && resolveOrderType(order) !== currentFilters.orderType) {
      return false
    }
    if (currentFilters.orderDate && (order.order_date || '') !== currentFilters.orderDate) {
      return false
    }
    if (currentFilters.status && resolveStatus(order) !== currentFilters.status) {
      return false
    }
    return true
  })
})

const filteredOrderLines = computed(() => {
  const f = lineFilters.value
  return orderLines.value.filter((line) => {
    if (
      f.customerOrderNo &&
      !normalizeText(line.customer_order_no).includes(normalizeText(f.customerOrderNo))
    ) return false
    if (f.productCode && !normalizeText(line.product_code).includes(normalizeText(f.productCode))) return false
    if (f.dueDateFrom && (line.due_date || '') < f.dueDateFrom) return false
    if (f.dueDateTo && (line.due_date || '') > f.dueDateTo) return false
    if (f.shipToCode && !normalizeText(line.ship_to_code).includes(normalizeText(f.shipToCode))) return false
    return true
  })
})

const fetchOrders = async (retry = 2) => {
  loading.value = true
  errorMessage.value = ''
  try {
    const params = { page_size: 0 }
    if (filters.value.orderNo) params.order_no = filters.value.orderNo
    if (filters.value.productCode) params.product_code = filters.value.productCode
    if (filters.value.dueDateFrom) params.due_date_from = filters.value.dueDateFrom
    if (filters.value.dueDateTo) params.due_date_to = filters.value.dueDateTo
    if (filters.value.shipToCode) params.ship_to_code = filters.value.shipToCode
    const response = await api.orders.getOrders(params)
    orders.value = response.data.results || response.data
  } catch (error) {
    console.error('Error fetching orders:', error)
    if (retry > 0) {
      setTimeout(() => fetchOrders(retry - 1), 800)
      return
    }
    errorMessage.value = '受注データの取得に失敗しました'
  } finally {
    loading.value = false
  }
}

let debounceTimer = null
watch(
  () => [filters.value.orderNo, filters.value.productCode, filters.value.dueDateFrom, filters.value.dueDateTo, filters.value.shipToCode],
  () => {
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => fetchOrders(), 400)
  }
)

const resetFilters = () => {
  filters.value = {
    orderNo: '',
    sourceFile: '',
    customer: '',
    orderType: '',
    orderDate: '',
    status: '',
    productCode: '',
    dueDateFrom: '',
    dueDateTo: '',
    shipToCode: '',
  }
}

const viewDetails = async (order) => {
  selectedOrder.value = order
  lineFilters.value = { customerOrderNo: '', productCode: '', dueDateFrom: '', dueDateTo: '', shipToCode: '' }
  try {
    const response = await api.orders.getOrderLines(order.id)
    orderLines.value = response.data.results || response.data
    showDetailsDialog.value = true
  } catch (error) {
    console.error('Error fetching order lines:', error)
    alert('Failed to fetch order lines')
  }
}

const closeDetailsDialog = () => {
  showDetailsDialog.value = false
}

const deleteOrderLine = async (line) => {
  const confirmed = window.confirm(
    `明細行を削除しますか？\n品番: ${line.product_code}\n数量: ${Math.round(Number(line.quantity))}\n納期: ${line.due_date}\n納入地: ${line.ship_to_code || '-'}`
  )
  if (!confirmed) return
  try {
    await api.orders.deleteOrderLine(line.id)
    orderLines.value = orderLines.value.filter((row) => row.id !== line.id)
  } catch (error) {
    console.error('Error deleting order line:', error)
    alert('明細行の削除に失敗しました')
  }
}

const confirmClose = async (order) => {
  const confirmed = window.confirm(`受注「${order.order_no}」をクローズしますか？`)
  if (!confirmed) return
  try {
    await api.orders.closeOrder(order.id)
    order.status = 'CLOSED'
    order.status_display = 'クローズ'
  } catch (error) {
    console.error('Error closing order:', error)
    alert('クローズに失敗しました')
  }
}

const confirmDelete = async (order) => {
  const confirmed = window.confirm(
    `受注「${order.order_no}」を削除しますか？\n明細行もすべて削除されます。`
  )
  if (!confirmed) return
  try {
    await api.orders.deleteOrder(order.id)
    orders.value = orders.value.filter((o) => o.id !== order.id)
  } catch (error) {
    console.error('Error deleting order:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchOrders()
})
</script>

<style scoped>
.detail-filter-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.detail-filter-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 150px;
  flex: 1 1 150px;
  font-size: 13px;
  color: #555;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  min-width: 500px;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-large {
  min-width: 960px;
  max-width: 1100px;
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
}

.modal-content h3 {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  color: #555;
}

.details-section {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.details-section p {
  margin: 0.5rem 0;
}

.form-actions {
  margin-top: 1.5rem;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background-color: white;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover {
  background-color: #f5f5f5;
}

.btn-warning {
  background-color: #dd6b20;
  color: white;
  border: none;
  margin-left: 4px;
}

.btn-warning:hover {
  background-color: #c05621;
}

.btn-danger {
  background-color: #e53e3e;
  color: white;
  border: none;
  margin-left: 4px;
}

.btn-danger:hover {
  background-color: #c53030;
}

.no-data {
  margin-top: 8px;
  font-size: 13px;
  color: #666;
}

.filter-panel {
  padding: 12px;
  border: 1px solid #e2e6ef;
  border-radius: 6px;
  background: #fafbff;
  margin-bottom: 12px;
}

.filter-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 200px;
  flex: 1 1 200px;
  font-size: 13px;
  color: #555;
}

.filter-input {
  padding: 6px 8px;
  border: 1px solid #d6dbe7;
  border-radius: 4px;
  font-size: 13px;
  background: #fff;
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
}

.info-banner {
  margin-bottom: 10px;
  padding: 8px 10px;
  background: #eef5ff;
  border: 1px solid #cbd9ff;
  border-radius: 4px;
  color: #1f3b7a;
}

.error-banner {
  margin-bottom: 10px;
  padding: 8px 10px;
  background: #fff4f4;
  border: 1px solid #ffcccc;
  border-radius: 4px;
  color: #c12b2b;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

</style>
