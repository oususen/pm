<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">受注一覧</h1>
      <div class="page-actions">
        <button @click="fetchOrders" class="btn-primary">更新</button>
      </div>
    </div>

    <div class="page-content">
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
          <tr v-for="order in orders" :key="order.id">
            <td>{{ order.order_no }}</td>
            <td>{{ order.source_file || '-' }}</td>
            <td>{{ order.customer_name }}</td>
            <td>{{ order.order_type_display }}</td>
            <td>{{ order.version_no }}</td>
            <td>{{ order.order_date || '-' }}</td>
            <td>{{ order.status_display }}</td>
            <td>
              <button @click="viewDetails(order)" class="btn-sm">詳細</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!loading && !errorMessage && orders.length === 0" class="no-data">
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
        <table class="data-table">
          <thead>
            <tr>
              <th>行番号</th>
              <th>製品コード</th>
              <th>製品名</th>
              <th>数量</th>
              <th>納期</th>
              <th>備考</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="line in orderLines" :key="line.id">
              <td>{{ line.line_no }}</td>
              <td>{{ line.product_code }}</td>
              <td>{{ line.product_name || '-' }}</td>
              <td>{{ line.quantity }}</td>
              <td>{{ line.due_date }}</td>
              <td>{{ line.remark || '-' }}</td>
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
import { ref, onMounted } from 'vue'
import api from '../api/client'

const orders = ref([])
const showDetailsDialog = ref(false)
const selectedOrder = ref({})
const orderLines = ref([])
const loading = ref(false)
const errorMessage = ref('')

const fetchOrders = async (retry = 2) => {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await api.orders.getOrders()
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

const viewDetails = async (order) => {
  selectedOrder.value = order
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

onMounted(() => {
  fetchOrders()
})
</script>

<style scoped>
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
  min-width: 800px;
  max-width: 900px;
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

.no-data {
  margin-top: 8px;
  font-size: 13px;
  color: #666;
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
</style>
