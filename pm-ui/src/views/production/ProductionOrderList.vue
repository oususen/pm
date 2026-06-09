<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">製造指示一覧</h1>
        <p class="helper-text">ステータス別の製造指示を一覧し、発行/開始/完了/中止を操作できます。</p>
      </div>
      <div class="page-actions">
        <button class="btn-secondary" @click="fetchOrders">再読込</button>
        <button class="btn-success" @click="goNew" :disabled="!canEdit">新規指示作成</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-row">
          <div class="filter-field">
            <label>指示番号/品番</label>
            <input v-model="filters.search" @keyup.enter="onEnterFilter" placeholder="指示番号・品番で検索" />
          </div>
          <div class="filter-field">
            <label>ライン</label>
            <select v-model="filters.line" @keyup.enter="onEnterFilter">
              <option value="">すべて</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
          </div>
          <div class="filter-field">
            <label>開始予定日(From)</label>
            <input v-model="filters.scheduled_start_date_from" type="date" @keyup.enter="onEnterFilter" />
          </div>
          <div class="filter-field">
            <label>開始予定日(To)</label>
            <input v-model="filters.scheduled_start_date_to" type="date" @keyup.enter="onEnterFilter" />
          </div>
          <div class="filter-field">
            <label>優先度≧</label>
            <input v-model.number="filters.priority_min" type="number" min="0" @keyup.enter="onEnterFilter" />
          </div>
        </div>
        <div class="filter-row">
          <div class="filter-field">
            <label>ステータス</label>
            <div class="status-group">
              <label v-for="opt in statusOptions" :key="opt.value" class="status-check">
                <input type="checkbox" :value="opt.value" v-model="filters.statuses" />
                <span :class="getStatusClass(opt.value)">{{ opt.label }}</span>
              </label>
            </div>
          </div>
          <div class="filter-field checkbox-field">
            <label>
              <input type="checkbox" v-model="filters.unallocatedOnly" />
              在庫引当未紐付のみ
            </label>
          </div>
          <div class="filter-actions">
            <button class="btn-primary" @click="fetchOrders">検索</button>
            <button class="btn-secondary" @click="resetFilters">リセット</button>
          </div>
        </div>
      </div>

      <div class="summary-bar">
        <span>件数: {{ filteredOrders.length }}</span>
        <span v-for="opt in statusOptions" :key="opt.value">
          {{ opt.label }}: {{ statusCount[opt.value] || 0 }}
        </span>
      </div>

      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>指示番号</th>
              <th>品番</th>
              <th>品名</th>
              <th>ライン</th>
              <th class="text-right">指示数量</th>
              <th>予定期間</th>
              <th class="text-center">優先度</th>
              <th>ステータス</th>
              <th>引当状況</th>
              <th>更新</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in filteredOrders" :key="order.id">
              <td>{{ order.order_no }}</td>
              <td>{{ order.product_code }}</td>
              <td>{{ order.product_name }}</td>
              <td>{{ order.line_code }}</td>
              <td class="text-right">{{ formatNumber(order.order_qty) }}</td>
              <td>{{ formatDate(order.scheduled_start_date) }} ~ {{ formatDate(order.scheduled_end_date) }}</td>
              <td class="text-center">{{ order.priority ?? 0 }}</td>
              <td><span :class="getStatusClass(order.status)">{{ order.status_display }}</span></td>
              <td>
                <span v-if="order.allocation" class="badge badge-success">紐付済</span>
                <span v-else class="badge badge-warning">未紐付</span>
              </td>
              <td>{{ formatDateTime(order.updated_at) }}</td>
              <td>
                <div class="btn-group">
                  <button class="btn-sm" @click="openDetail(order)">詳細</button>
                  <button class="btn-sm" @click="goEdit(order.id)" :disabled="!canEdit">編集</button>
                  <button class="btn-sm btn-secondary" @click="goActuals(order.id)">実績入力</button>
                  <button
                    v-if="order.status === 'PLANNED'"
                    class="btn-sm btn-primary"
                    :disabled="!canEdit"
                    @click="transition(order, 'release')"
                  >
                    発行
                  </button>
                  <button
                    v-if="order.status === 'RELEASED'"
                    class="btn-sm btn-success"
                    :disabled="!canEdit"
                    @click="transition(order, 'start')"
                  >
                    開始
                  </button>
                  <button
                    v-if="order.status === 'IN_PROGRESS'"
                    class="btn-sm btn-info"
                    :disabled="!canEdit"
                    @click="transition(order, 'complete')"
                  >
                    完了
                  </button>
                  <button
                    v-if="['PLANNED', 'RELEASED', 'IN_PROGRESS'].includes(order.status)"
                    class="btn-sm btn-danger"
                    :disabled="!canEdit"
                    @click="transition(order, 'cancel')"
                  >
                    中止
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!filteredOrders.length" class="no-data">
        条件に合致するデータがありません
      </div>
    </div>

    <!-- 詳細ダイアログ -->
    <div v-if="showDetailDialog" class="modal-overlay" @click.self="closeDetailDialog">
      <div class="modal-content modal-lg">
        <h2>製造指示詳細</h2>
        <div v-if="selectedOrder" class="detail-grid">
          <div><label>指示番号</label><span>{{ selectedOrder.order_no }}</span></div>
          <div><label>製品</label><span>{{ selectedOrder.product_code }} - {{ selectedOrder.product_name }}</span></div>
          <div><label>ライン</label><span>{{ selectedOrder.line_code }}</span></div>
          <div><label>ルーティング</label><span>{{ selectedOrder.routing_code || '-' }}</span></div>
          <div><label>数量</label><span>{{ formatNumber(selectedOrder.order_qty) }}</span></div>
          <div><label>予定期間</label><span>{{ formatDate(selectedOrder.scheduled_start_date) }} ~ {{ formatDate(selectedOrder.scheduled_end_date) }}</span></div>
          <div><label>ステータス</label><span>{{ selectedOrder.status_display }}</span></div>
          <div><label>在庫引当</label><span>{{ selectedOrder.allocation ? '紐付済' : '未紐付' }}</span></div>
          <div class="full-row"><label>備考</label><span>{{ selectedOrder.remark || '-' }}</span></div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="closeDetailDialog">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

export default {
  name: 'ProductionOrderList',
  data() {
    return {
      orders: [],
      lines: [],
      filters: {
        search: '',
        line: '',
        statuses: [],
        scheduled_start_date_from: '',
        scheduled_start_date_to: '',
        priority_min: null,
        unallocatedOnly: false
      },
      statusOptions: [
        { value: 'PLANNED', label: '計画済' },
        { value: 'RELEASED', label: '指示済' },
        { value: 'IN_PROGRESS', label: '進行中' },
        { value: 'COMPLETED', label: '完了' },
        { value: 'CANCELED', label: '中止' }
      ],
      showDetailDialog: false,
      selectedOrder: null,
      loading: false
    }
  },
  computed: {
    filteredOrders() {
      let data = [...this.orders]
      if (this.filters.priority_min != null && this.filters.priority_min !== '') {
        data = data.filter((o) => Number(o.priority || 0) >= Number(this.filters.priority_min))
      }
      if (this.filters.unallocatedOnly) {
        data = data.filter((o) => !o.allocation)
      }
      return data
    },
    statusCount() {
      return this.orders.reduce((acc, cur) => {
        acc[cur.status] = (acc[cur.status] || 0) + 1
        return acc
      }, {})
    },
    canEdit() {
      const user = authState.user
      if (!user) return false
      const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
      if (permissions.some((item) => item.resource === 'production.orders')) {
        return hasPermission(user, 'production.orders', 'edit')
      }
      return hasPermission(user, 'production', 'edit')
    }
  },
  mounted() {
    this.fetchLines()
    this.fetchOrders()
  },
  methods: {
    // フィルタ入力でEnter押下時に検索を実行（検索ボタンと同等）
    onEnterFilter() {
      if (this.loading) return
      this.fetchOrders()
    },
    async fetchLines() {
      try {
        const res = await api.lines.getLines({ page_size: 500 })
        this.lines = res.data?.results || res.data || []
      } catch (error) {
        console.error('ライン取得エラー', error)
      }
    },
    async fetchOrders() {
      this.loading = true
      try {
        const params = {}
        if (this.filters.search) params.search = this.filters.search
        if (this.filters.line) params.line = this.filters.line
        if (this.filters.statuses.length) params.status = this.filters.statuses.join(',')
        if (this.filters.scheduled_start_date_from) params.scheduled_start_date_from = this.filters.scheduled_start_date_from
        if (this.filters.scheduled_start_date_to) params.scheduled_start_date_to = this.filters.scheduled_start_date_to

        const listRes = await api.orders.getProductionOrders(params)
        let items = listRes.data?.results || listRes.data || []
        if (!items.length && (this.filters.search || this.filters.line || this.filters.scheduled_start_date_from || this.filters.scheduled_start_date_to)) {
          await api.orders.syncProductionOrdersFromPlan({
            line_id: this.filters.line || undefined,
            start_date: this.filters.scheduled_start_date_from || undefined,
            end_date: this.filters.scheduled_start_date_to || undefined
          })
          const retryRes = await api.orders.getProductionOrders(params)
          items = retryRes.data?.results || retryRes.data || []
        }

        // 詳細を取得して allocation などの付加情報を含める
        const detailed = await Promise.all(
          items.map(async (item) => {
            try {
              const res = await api.orders.getProductionOrder(item.id)
              return res.data?.results || res.data || item
            } catch (error) {
              console.error('詳細取得エラー', error)
              return item
            }
          })
        )
        this.orders = detailed
      } catch (error) {
        console.error('製造指示取得エラー', error)
        alert('製造指示の取得に失敗しました')
      } finally {
        this.loading = false
      }
    },
    resetFilters() {
      this.filters = {
        search: '',
        line: '',
        statuses: [],
        scheduled_start_date_from: '',
        scheduled_start_date_to: '',
        priority_min: null,
        unallocatedOnly: false
      }
      this.fetchOrders()
    },
    async transition(order, action) {
      if (!this.canEdit) return
      const allowMap = {
        release: ['PLANNED'],
        start: ['RELEASED'],
        complete: ['IN_PROGRESS'],
        cancel: ['PLANNED', 'RELEASED', 'IN_PROGRESS']
      }
      if (!allowMap[action].includes(order.status)) {
        alert('現在のステータスでは実行できません')
        return
      }
      const labels = { release: '発行', start: '開始', complete: '完了', cancel: '中止' }
      if (!confirm(`製造指示「${order.order_no}」を${labels[action]}しますか？`)) return

      try {
        await api.orders.transitionProductionOrder(order.id, action)
        alert(`製造指示を${labels[action]}しました`)
        this.fetchOrders()
      } catch (error) {
        console.error('ステータス変更エラー', error)
        alert(`${labels[action]}に失敗しました: ${error.response?.data?.detail || error.message}`)
      }
    },
    goNew() {
      if (!this.canEdit) return
      this.$router.push('/production/orders/new')
    },
    goEdit(id) {
      if (!this.canEdit) return
      this.$router.push(`/production/orders/${id}/edit`)
    },
    goActuals(id) {
      this.$router.push(`/production/orders/${id}/actuals`)
    },
    openDetail(order) {
      this.selectedOrder = order
      this.showDetailDialog = true
    },
    closeDetailDialog() {
      this.showDetailDialog = false
      this.selectedOrder = null
    },
    getStatusClass(status) {
      const classes = {
        PLANNED: 'badge badge-secondary',
        RELEASED: 'badge badge-primary',
        IN_PROGRESS: 'badge badge-warning',
        COMPLETED: 'badge badge-success',
        CANCELED: 'badge badge-danger'
      }
      return classes[status] || 'badge'
    },
    formatNumber(value) {
      if (value == null) return '0'
      return parseFloat(value).toLocaleString('ja-JP', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 3
      })
    },
    formatDate(value) {
      return value || ''
    },
    formatDateTime(value) {
      if (!value) return ''
      return new Date(value).toLocaleString('ja-JP')
    }
  }
}
</script>

<style scoped>
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
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  align-items: end;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-field input,
.filter-field select {
  padding: 8px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
}

.status-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-check {
  display: flex;
  gap: 6px;
  align-items: center;
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
  gap: 12px;
  margin-bottom: 8px;
  font-size: 0.95rem;
}

.table-wrapper {
  background: #fff;
  border: 1px solid #e3e7eb;
  border-radius: 8px;
  overflow: auto;
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

.btn-group {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

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

.modal-lg {
  max-width: 900px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 12px 0;
}

.detail-grid label {
  font-weight: bold;
  margin-right: 6px;
}

.detail-grid .full-row {
  grid-column: span 2;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>

