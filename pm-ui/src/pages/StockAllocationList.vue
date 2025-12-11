<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">在庫引当管理</h1>
      <div class="page-actions">
        <button @click="fetchAllocations" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>品番/品名</label>
          <input
            v-model="filters.search"
            @keyup.enter="fetchAllocations"
            placeholder="品番・品名で検索"
          />
        </div>
        <div class="filter-field">
          <label>保管場所</label>
          <input
            v-model="filters.location"
            @keyup.enter="fetchAllocations"
            placeholder="保管場所"
          />
        </div>
        <div class="filter-field">
          <label>ボトルネック</label>
          <select v-model="filters.is_bottleneck">
            <option value="">すべて</option>
            <option value="true">ボトルネック</option>
            <option value="false">通常</option>
          </select>
        </div>
        <div class="filter-actions">
          <button @click="fetchAllocations" class="btn-primary">検索</button>
          <button @click="resetFilters" class="btn-secondary">リセット</button>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>品番</th>
            <th>品名</th>
            <th>保管場所</th>
            <th>現在在庫</th>
            <th>引当済</th>
            <th>引当可能</th>
            <th>最小在庫</th>
            <th>ボトルネック</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="allocation in allocations" :key="allocation.id">
            <td>{{ allocation.product_code }}</td>
            <td>{{ allocation.product_name }}</td>
            <td>{{ allocation.location }}</td>
            <td class="text-right">{{ formatNumber(allocation.current_stock) }}</td>
            <td class="text-right">{{ formatNumber(allocation.reserved_qty) }}</td>
            <td class="text-right" :class="{ 'text-danger': allocation.available_qty < allocation.min_stock_qty }">
              {{ formatNumber(allocation.available_qty) }}
            </td>
            <td class="text-right">{{ formatNumber(allocation.min_stock_qty) }}</td>
            <td>
              <span v-if="allocation.is_bottleneck" class="badge badge-warning">ボトルネック</span>
            </td>
            <td>
              <button @click="showReserveDialog(allocation)" class="btn-sm btn-primary">引当</button>
              <button @click="showReleaseDialog(allocation)" class="btn-sm btn-secondary">解除</button>
              <button @click="editAllocation(allocation)" class="btn-sm">編集</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="allocations.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '在庫引当編集' : '在庫引当新規作成' }}</h2>
        <form @submit.prevent="saveAllocation">
          <div class="form-group">
            <label>製品 *</label>
            <select v-model="formData.product" required :disabled="isEdit">
              <option value="">選択してください</option>
              <option v-for="product in products" :key="product.id" :value="product.id">
                {{ product.product_code }} - {{ product.product_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>保管場所 *</label>
            <input v-model="formData.location" required />
          </div>
          <div class="form-group">
            <label>現在在庫 *</label>
            <input v-model.number="formData.current_stock" type="number" step="0.001" required />
          </div>
          <div class="form-group">
            <label>引当済数量</label>
            <input v-model.number="formData.reserved_qty" type="number" step="0.001" />
          </div>
          <div class="form-group">
            <label>最小在庫数量 *</label>
            <input v-model.number="formData.min_stock_qty" type="number" step="0.001" required />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_bottleneck" />
              ボトルネック部品
            </label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 引当ダイアログ -->
    <div v-if="showReserveDialogFlag" class="modal-overlay" @click.self="closeReserveDialog">
      <div class="modal-content modal-sm">
        <h2>在庫引当</h2>
        <form @submit.prevent="reserveStock">
          <div class="info-box">
            <p>品番: {{ selectedAllocation?.product_code }}</p>
            <p>品名: {{ selectedAllocation?.product_name }}</p>
            <p>引当可能数量: {{ formatNumber(selectedAllocation?.available_qty) }}</p>
          </div>
          <div class="form-group">
            <label>引当数量 *</label>
            <input v-model.number="reserveQty" type="number" step="0.001" required min="0" />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">引当実行</button>
            <button type="button" @click="closeReserveDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 引当解除ダイアログ -->
    <div v-if="showReleaseDialogFlag" class="modal-overlay" @click.self="closeReleaseDialog">
      <div class="modal-content modal-sm">
        <h2>引当解除</h2>
        <form @submit.prevent="releaseStock">
          <div class="info-box">
            <p>品番: {{ selectedAllocation?.product_code }}</p>
            <p>品名: {{ selectedAllocation?.product_name }}</p>
            <p>引当済数量: {{ formatNumber(selectedAllocation?.reserved_qty) }}</p>
          </div>
          <div class="form-group">
            <label>解除数量 *</label>
            <input v-model.number="releaseQty" type="number" step="0.001" required min="0" />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-danger">解除実行</button>
            <button type="button" @click="closeReleaseDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api/orders'

export default {
  name: 'StockAllocationList',
  data() {
    return {
      allocations: [],
      products: [],
      filters: {
        search: '',
        location: '',
        is_bottleneck: ''
      },
      showDialog: false,
      isEdit: false,
      formData: {
        product: '',
        location: '',
        current_stock: 0,
        reserved_qty: 0,
        min_stock_qty: 0,
        is_bottleneck: false
      },
      showReserveDialogFlag: false,
      showReleaseDialogFlag: false,
      selectedAllocation: null,
      reserveQty: 0,
      releaseQty: 0
    }
  },
  mounted() {
    this.fetchAllocations()
    this.fetchProducts()
  },
  methods: {
    async fetchAllocations() {
      try {
        const params = {}
        if (this.filters.search) params.search = this.filters.search
        if (this.filters.location) params.location = this.filters.location
        if (this.filters.is_bottleneck) params.is_bottleneck = this.filters.is_bottleneck === 'true'

        const response = await axios.get(`${API_BASE_URL}/stock-allocations/`, { params })
        this.allocations = response.data
      } catch (error) {
        console.error('在庫引当取得エラー:', error)
        alert('在庫引当の取得に失敗しました')
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
    resetFilters() {
      this.filters = {
        search: '',
        location: '',
        is_bottleneck: ''
      }
      this.fetchAllocations()
    },
    showNewDialog() {
      this.isEdit = false
      this.formData = {
        product: '',
        location: '',
        current_stock: 0,
        reserved_qty: 0,
        min_stock_qty: 0,
        is_bottleneck: false
      }
      this.showDialog = true
    },
    editAllocation(allocation) {
      this.isEdit = true
      this.formData = {
        id: allocation.id,
        product: allocation.product,
        location: allocation.location,
        current_stock: allocation.current_stock,
        reserved_qty: allocation.reserved_qty,
        min_stock_qty: allocation.min_stock_qty,
        is_bottleneck: allocation.is_bottleneck
      }
      this.showDialog = true
    },
    async saveAllocation() {
      try {
        if (this.isEdit) {
          await axios.put(`${API_BASE_URL}/stock-allocations/${this.formData.id}/`, this.formData)
          alert('在庫引当を更新しました')
        } else {
          await axios.post(`${API_BASE_URL}/stock-allocations/`, this.formData)
          alert('在庫引当を作成しました')
        }
        this.closeDialog()
        this.fetchAllocations()
      } catch (error) {
        console.error('保存エラー:', error)
        alert('保存に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    closeDialog() {
      this.showDialog = false
    },
    showReserveDialog(allocation) {
      this.selectedAllocation = allocation
      this.reserveQty = 0
      this.showReserveDialogFlag = true
    },
    closeReserveDialog() {
      this.showReserveDialogFlag = false
      this.selectedAllocation = null
    },
    async reserveStock() {
      try {
        await axios.post(`${API_BASE_URL}/stock-allocations/${this.selectedAllocation.id}/reserve/`, {
          quantity: this.reserveQty
        })
        alert('在庫を引当しました')
        this.closeReserveDialog()
        this.fetchAllocations()
      } catch (error) {
        console.error('引当エラー:', error)
        alert('引当に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    showReleaseDialog(allocation) {
      this.selectedAllocation = allocation
      this.releaseQty = 0
      this.showReleaseDialogFlag = true
    },
    closeReleaseDialog() {
      this.showReleaseDialogFlag = false
      this.selectedAllocation = null
    },
    async releaseStock() {
      try {
        await axios.post(`${API_BASE_URL}/stock-allocations/${this.selectedAllocation.id}/release/`, {
          quantity: this.releaseQty
        })
        alert('引当を解除しました')
        this.closeReleaseDialog()
        this.fetchAllocations()
      } catch (error) {
        console.error('解除エラー:', error)
        alert('解除に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    formatNumber(value) {
      if (value == null) return '0'
      return parseFloat(value).toLocaleString('ja-JP', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 3
      })
    }
  }
}
</script>

<style scoped>
.text-right {
  text-align: right;
}

.text-danger {
  color: #dc3545;
  font-weight: bold;
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

.badge-warning {
  background-color: #ffc107;
  color: #212529;
}

.modal-sm {
  max-width: 400px;
}

.info-box {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 0.25rem;
  padding: 1rem;
  margin-bottom: 1rem;
}

.info-box p {
  margin: 0.5rem 0;
}
</style>
