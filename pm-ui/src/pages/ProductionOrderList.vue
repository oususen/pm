<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">製造指示管理</h1>
      <div class="page-actions">
        <button @click="fetchOrders" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>指示番号/品番</label>
          <input
            v-model="filters.search"
            @keyup.enter="fetchOrders"
            placeholder="指示番号・品番で検索"
          />
        </div>
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
          <label>ステータス</label>
          <select v-model="filters.status">
            <option value="">すべて</option>
            <option value="PLANNED">計画済</option>
            <option value="RELEASED">指示済</option>
            <option value="IN_PROGRESS">進行中</option>
            <option value="COMPLETED">完了</option>
            <option value="CANCELED">中止</option>
          </select>
        </div>
        <div class="filter-field">
          <label>開始予定日</label>
          <input v-model="filters.scheduled_start_date" type="date" />
        </div>
        <div class="filter-actions">
          <button @click="fetchOrders" class="btn-primary">検索</button>
          <button @click="resetFilters" class="btn-secondary">リセット</button>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>指示番号</th>
            <th>品番</th>
            <th>品名</th>
            <th>ライン</th>
            <th>指示数量</th>
            <th>開始予定日</th>
            <th>終了予定日</th>
            <th>優先度</th>
            <th>ステータス</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in orders" :key="order.id">
            <td>{{ order.order_no }}</td>
            <td>{{ order.product_code }}</td>
            <td>{{ order.product_name }}</td>
            <td>{{ order.line_code }}</td>
            <td class="text-right">{{ formatNumber(order.order_qty) }}</td>
            <td>{{ formatDate(order.scheduled_start_date) }}</td>
            <td>{{ formatDate(order.scheduled_end_date) }}</td>
            <td class="text-center">{{ order.priority }}</td>
            <td>
              <span :class="getStatusClass(order.status)">
                {{ order.status_display }}
              </span>
            </td>
            <td>
              <div class="btn-group">
                <button
                  v-if="order.status === 'PLANNED'"
                  @click="releaseOrder(order)"
                  class="btn-sm btn-primary"
                  title="製造指示発行"
                >
                  発行
                </button>
                <button
                  v-if="order.status === 'RELEASED'"
                  @click="startOrder(order)"
                  class="btn-sm btn-success"
                  title="製造開始"
                >
                  開始
                </button>
                <button
                  v-if="order.status === 'IN_PROGRESS'"
                  @click="completeOrder(order)"
                  class="btn-sm btn-info"
                  title="製造完了"
                >
                  完了
                </button>
                <button
                  v-if="['PLANNED', 'RELEASED', 'IN_PROGRESS'].includes(order.status)"
                  @click="cancelOrder(order)"
                  class="btn-sm btn-danger"
                  title="製造中止"
                >
                  中止
                </button>
                <button @click="viewDetails(order)" class="btn-sm">詳細</button>
                <button @click="editOrder(order)" class="btn-sm">編集</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="orders.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '製造指示編集' : '製造指示新規作成' }}</h2>
        <form @submit.prevent="saveOrder">
          <div class="form-group">
            <label>指示番号 *</label>
            <input v-model="formData.order_no" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>製品 *</label>
            <select v-model="formData.product" required @change="onProductChange">
              <option value="">選択してください</option>
              <option v-for="product in products" :key="product.id" :value="product.id">
                {{ product.product_code }} - {{ product.product_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>ルーティング</label>
            <select v-model="formData.routing">
              <option value="">選択してください</option>
              <option v-for="routing in routings" :key="routing.id" :value="routing.id">
                {{ routing.routing_code }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>ライン *</label>
            <select v-model="formData.line" required>
              <option value="">選択してください</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>指示数量 *</label>
            <input v-model.number="formData.order_qty" type="number" step="0.001" required />
          </div>
          <div class="form-group">
            <label>開始予定日 *</label>
            <input v-model="formData.scheduled_start_date" type="date" required />
          </div>
          <div class="form-group">
            <label>終了予定日</label>
            <input v-model="formData.scheduled_end_date" type="date" />
          </div>
          <div class="form-group">
            <label>優先度</label>
            <input v-model.number="formData.priority" type="number" />
          </div>
          <div class="form-group">
            <label>備考</label>
            <textarea v-model="formData.remark" rows="3"></textarea>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 詳細ダイアログ -->
    <div v-if="showDetailDialog" class="modal-overlay" @click.self="closeDetailDialog">
      <div class="modal-content modal-lg">
        <h2>製造指示詳細</h2>
        <div v-if="selectedOrder" class="detail-content">
          <div class="detail-section">
            <h3>基本情報</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>指示番号:</label>
                <span>{{ selectedOrder.order_no }}</span>
              </div>
              <div class="detail-item">
                <label>品番:</label>
                <span>{{ selectedOrder.product_code }}</span>
              </div>
              <div class="detail-item">
                <label>品名:</label>
                <span>{{ selectedOrder.product_name }}</span>
              </div>
              <div class="detail-item">
                <label>ライン:</label>
                <span>{{ selectedOrder.line_code }} - {{ selectedOrder.line_name }}</span>
              </div>
              <div class="detail-item">
                <label>指示数量:</label>
                <span>{{ formatNumber(selectedOrder.order_qty) }}</span>
              </div>
              <div class="detail-item">
                <label>ステータス:</label>
                <span :class="getStatusClass(selectedOrder.status)">
                  {{ selectedOrder.status_display }}
                </span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>スケジュール</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>開始予定日:</label>
                <span>{{ formatDate(selectedOrder.scheduled_start_date) }}</span>
              </div>
              <div class="detail-item">
                <label>終了予定日:</label>
                <span>{{ formatDate(selectedOrder.scheduled_end_date) }}</span>
              </div>
              <div class="detail-item">
                <label>実績開始日:</label>
                <span>{{ formatDateTime(selectedOrder.actual_start_date) }}</span>
              </div>
              <div class="detail-item">
                <label>実績終了日:</label>
                <span>{{ formatDateTime(selectedOrder.actual_end_date) }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="selectedOrder.actuals && selectedOrder.actuals.length > 0">
            <h3>工程実績</h3>
            <table class="data-table">
              <thead>
                <tr>
                  <th>工程</th>
                  <th>ライン</th>
                  <th>完了数量</th>
                  <th>実績時間(分)</th>
                  <th>完了日時</th>
                  <th>作業者</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="actual in selectedOrder.actuals" :key="actual.id">
                  <td>{{ actual.process_code }} - {{ actual.process_name }}</td>
                  <td>{{ actual.line_code }}</td>
                  <td class="text-right">{{ formatNumber(actual.completed_qty) }}</td>
                  <td class="text-right">{{ actual.actual_duration_min }}</td>
                  <td>{{ formatDateTime(actual.completed_at) }}</td>
                  <td>{{ actual.operator }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="form-actions">
          <button @click="closeDetailDialog" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api/orders'

export default {
  name: 'ProductionOrderList',
  data() {
    return {
      orders: [],
      products: [],
      routings: [],
      lines: [],
      filters: {
        search: '',
        line: '',
        status: '',
        scheduled_start_date: ''
      },
      showDialog: false,
      showDetailDialog: false,
      isEdit: false,
      formData: this.getEmptyFormData(),
      selectedOrder: null
    }
  },
  mounted() {
    this.fetchOrders()
    this.fetchProducts()
    this.fetchLines()
  },
  methods: {
    getEmptyFormData() {
      return {
        order_no: '',
        product: '',
        routing: '',
        line: '',
        order_qty: 0,
        scheduled_start_date: '',
        scheduled_end_date: '',
        priority: 100,
        remark: ''
      }
    },
    async fetchOrders() {
      try {
        const params = {}
        if (this.filters.search) params.search = this.filters.search
        if (this.filters.line) params.line = this.filters.line
        if (this.filters.status) params.status = this.filters.status
        if (this.filters.scheduled_start_date) params.scheduled_start_date = this.filters.scheduled_start_date

        const response = await axios.get(`${API_BASE_URL}/production-orders/`, { params })
        this.orders = response.data
      } catch (error) {
        console.error('製造指示取得エラー:', error)
        alert('製造指示の取得に失敗しました')
      }
    },
    async fetchProducts() {
      try {
        const response = await axios.get('http://localhost:8000/api/masters/products/')
        this.products = response.data
      } catch (error) {
        console.error('製品取得エラー:', error)
      }
    },
    async fetchLines() {
      try {
        const response = await axios.get('http://localhost:8000/api/masters/lines/')
        this.lines = response.data
      } catch (error) {
        console.error('ライン取得エラー:', error)
      }
    },
    async fetchRoutings(productId) {
      if (!productId) {
        this.routings = []
        return
      }
      try {
        const response = await axios.get(`http://localhost:8000/api/masters/routings/?product=${productId}`)
        this.routings = response.data
      } catch (error) {
        console.error('ルーティング取得エラー:', error)
      }
    },
    onProductChange() {
      this.fetchRoutings(this.formData.product)
    },
    resetFilters() {
      this.filters = {
        search: '',
        line: '',
        status: '',
        scheduled_start_date: ''
      }
      this.fetchOrders()
    },
    showNewDialog() {
      this.isEdit = false
      this.formData = this.getEmptyFormData()
      this.routings = []
      this.showDialog = true
    },
    editOrder(order) {
      this.isEdit = true
      this.formData = {
        id: order.id,
        order_no: order.order_no,
        product: order.product,
        routing: order.routing,
        line: order.line,
        order_qty: order.order_qty,
        scheduled_start_date: order.scheduled_start_date,
        scheduled_end_date: order.scheduled_end_date,
        priority: order.priority,
        remark: order.remark
      }
      this.fetchRoutings(order.product)
      this.showDialog = true
    },
    async saveOrder() {
      try {
        if (this.isEdit) {
          await axios.put(`${API_BASE_URL}/production-orders/${this.formData.id}/`, this.formData)
          alert('製造指示を更新しました')
        } else {
          await axios.post(`${API_BASE_URL}/production-orders/`, this.formData)
          alert('製造指示を作成しました')
        }
        this.closeDialog()
        this.fetchOrders()
      } catch (error) {
        console.error('保存エラー:', error)
        alert('保存に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    closeDialog() {
      this.showDialog = false
    },
    async viewDetails(order) {
      try {
        const response = await axios.get(`${API_BASE_URL}/production-orders/${order.id}/`)
        this.selectedOrder = response.data
        this.showDetailDialog = true
      } catch (error) {
        console.error('詳細取得エラー:', error)
        alert('詳細の取得に失敗しました')
      }
    },
    closeDetailDialog() {
      this.showDetailDialog = false
      this.selectedOrder = null
    },
    async releaseOrder(order) {
      if (!confirm(`製造指示「${order.order_no}」を発行しますか？`)) return
      try {
        await axios.post(`${API_BASE_URL}/production-orders/${order.id}/release/`)
        alert('製造指示を発行しました')
        this.fetchOrders()
      } catch (error) {
        console.error('発行エラー:', error)
        alert('発行に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    async startOrder(order) {
      if (!confirm(`製造指示「${order.order_no}」を開始しますか？`)) return
      try {
        await axios.post(`${API_BASE_URL}/production-orders/${order.id}/start/`)
        alert('製造を開始しました')
        this.fetchOrders()
      } catch (error) {
        console.error('開始エラー:', error)
        alert('開始に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    async completeOrder(order) {
      if (!confirm(`製造指示「${order.order_no}」を完了しますか？`)) return
      try {
        await axios.post(`${API_BASE_URL}/production-orders/${order.id}/complete/`)
        alert('製造を完了しました')
        this.fetchOrders()
      } catch (error) {
        console.error('完了エラー:', error)
        alert('完了に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    async cancelOrder(order) {
      if (!confirm(`製造指示「${order.order_no}」を中止しますか？`)) return
      try {
        await axios.post(`${API_BASE_URL}/production-orders/${order.id}/cancel/`)
        alert('製造を中止しました')
        this.fetchOrders()
      } catch (error) {
        console.error('中止エラー:', error)
        alert('中止に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    getStatusClass(status) {
      const statusClasses = {
        'PLANNED': 'badge badge-secondary',
        'RELEASED': 'badge badge-primary',
        'IN_PROGRESS': 'badge badge-warning',
        'COMPLETED': 'badge badge-success',
        'CANCELED': 'badge badge-danger'
      }
      return statusClasses[status] || 'badge'
    },
    formatNumber(value) {
      if (value == null) return '0'
      return parseFloat(value).toLocaleString('ja-JP', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 3
      })
    },
    formatDate(value) {
      if (!value) return ''
      return value
    },
    formatDateTime(value) {
      if (!value) return ''
      return new Date(value).toLocaleString('ja-JP')
    }
  }
}
</script>

<style scoped>
.text-right {
  text-align: right;
}

.text-center {
  text-align: center;
}

.badge {
  display: inline-block;
  padding: 0.25em 0.6em;
  font-size: 75%;
  font-weight: 700;
  line-height: 1;
  text-align: center;
  white-space: nowrap;
  vertical-align: baseline;
  border-radius: 0.25rem;
}

.badge-secondary {
  background-color: #6c757d;
  color: white;
}

.badge-primary {
  background-color: #007bff;
  color: white;
}

.badge-warning {
  background-color: #ffc107;
  color: #212529;
}

.badge-success {
  background-color: #28a745;
  color: white;
}

.badge-danger {
  background-color: #dc3545;
  color: white;
}

.btn-group {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.modal-lg {
  max-width: 900px;
}

.detail-content {
  padding: 1rem 0;
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h3 {
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #dee2e6;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.detail-item {
  display: flex;
  gap: 0.5rem;
}

.detail-item label {
  font-weight: bold;
  min-width: 120px;
}
</style>
