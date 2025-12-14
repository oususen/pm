<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">在庫引当一覧</h1>
        <p class="helper-text">
          可用在庫と最小在庫を並べて確認し、引当/解除を素早く実行します。
        </p>
      </div>
      <div class="page-actions">
        <button @click="fetchAllocations" class="btn-secondary">再読込</button>
        <button @click="downloadCsv" class="btn-secondary">CSV出力</button>
        <button @click="bulkRelease" class="btn-danger" :disabled="!selectedIds.length">一括解除</button>
        <button @click="goNew" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-row">
          <div class="filter-field wide">
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
          <div class="filter-field checkbox-field">
            <label>
              <input type="checkbox" v-model="filters.shortageOnly" />
              最小在庫割れのみ
            </label>
          </div>
          <div class="filter-actions">
            <button @click="fetchAllocations" class="btn-primary">検索</button>
            <button @click="resetFilters" class="btn-secondary">リセット</button>
          </div>
        </div>
      </div>

      <div class="summary-bar">
        <span>件数: {{ filteredAllocations.length }} / {{ allocations.length }}</span>
        <span :class="{ 'text-danger': shortageCount > 0 }">最小在庫割れ: {{ shortageCount }}件</span>
      </div>

      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 36px">
                <input type="checkbox" :checked="isAllSelected" @change="toggleAll" />
              </th>
              <th>品番</th>
              <th>品名</th>
              <th>保管場所</th>
              <th class="text-right">現在在庫</th>
              <th class="text-right">引当済</th>
              <th class="text-right">可用在庫</th>
              <th class="text-right">最小在庫</th>
              <th class="text-right">差分</th>
              <th>ボトルネック</th>
              <th>更新</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="allocation in filteredAllocations" :key="allocation.id">
              <td class="text-center">
                <input
                  type="checkbox"
                  :value="allocation.id"
                  v-model="selectedIds"
                />
              </td>
              <td>{{ allocation.product_code }}</td>
              <td>{{ allocation.product_name }}</td>
              <td>{{ allocation.location }}</td>
              <td class="text-right">{{ formatNumber(allocation.current_stock) }}</td>
              <td class="text-right">{{ formatNumber(allocation.reserved_qty) }}</td>
              <td
                class="text-right"
                :class="{ 'text-danger': allocation.available_qty < allocation.min_stock_qty }"
              >
                {{ formatNumber(allocation.available_qty) }}
              </td>
              <td class="text-right">{{ formatNumber(allocation.min_stock_qty) }}</td>
              <td
                class="text-right"
                :class="{ 'text-danger': allocation.available_qty < allocation.min_stock_qty }"
              >
                {{ formatNumber(allocation.available_qty - allocation.min_stock_qty) }}
              </td>
              <td>
                <span v-if="allocation.is_bottleneck" class="badge badge-warning">ボトルネック</span>
              </td>
              <td>{{ formatDateTime(allocation.updated_at) }}</td>
              <td>
                <div class="btn-group">
                  <button @click="showReserveDialog(allocation)" class="btn-sm btn-primary">引当</button>
                  <button @click="showReleaseDialog(allocation)" class="btn-sm btn-secondary">解除</button>
                  <button @click="goEdit(allocation.id)" class="btn-sm">編集</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!filteredAllocations.length" class="no-data">
        条件に合致するデータがありません
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

const API_BASE = 'http://localhost:8000/api'

export default {
  name: 'StockAllocationList',
  data() {
    return {
      allocations: [],
      filters: {
        search: '',
        location: '',
        is_bottleneck: '',
        shortageOnly: false
      },
      selectedIds: [],
      showReserveDialogFlag: false,
      showReleaseDialogFlag: false,
      selectedAllocation: null,
      reserveQty: 0,
      releaseQty: 0,
      loading: false
    }
  },
  computed: {
    filteredAllocations() {
      return this.allocations.filter((item) => {
        if (this.filters.shortageOnly && !(parseFloat(item.available_qty) < parseFloat(item.min_stock_qty))) {
          return false
        }
        return true
      })
    },
    shortageCount() {
      return this.allocations.filter(
        (item) => parseFloat(item.available_qty) < parseFloat(item.min_stock_qty)
      ).length
    },
    isAllSelected() {
      return this.filteredAllocations.length > 0 &&
        this.filteredAllocations.every((item) => this.selectedIds.includes(item.id))
    }
  },
  mounted() {
    this.fetchAllocations()
  },
  methods: {
    async fetchAllocations() {
      this.loading = true
      try {
        const params = {}
        if (this.filters.search) params.search = this.filters.search
        if (this.filters.location) params.location = this.filters.location
        if (this.filters.is_bottleneck) params.is_bottleneck = this.filters.is_bottleneck === 'true'

        const response = await axios.get(`${API_BASE}/orders/stock-allocations/`, { params })
        this.allocations = response.data
        this.selectedIds = []
      } catch (error) {
        console.error('在庫引当取得エラー:', error)
        alert('在庫引当の取得に失敗しました')
      } finally {
        this.loading = false
      }
    },
    resetFilters() {
      this.filters = {
        search: '',
        location: '',
        is_bottleneck: '',
        shortageOnly: false
      }
      this.fetchAllocations()
    },
    goNew() {
      this.$router.push('/production/stock-allocations/new')
    },
    goEdit(id) {
      this.$router.push(`/production/stock-allocations/${id}/edit`)
    },
    showReserveDialog(allocation) {
      this.selectedAllocation = allocation
      this.reserveQty = allocation.available_qty > 0 ? allocation.available_qty : 0
      this.showReserveDialogFlag = true
    },
    closeReserveDialog() {
      this.showReserveDialogFlag = false
      this.selectedAllocation = null
    },
    async reserveStock() {
      try {
        await axios.post(`${API_BASE}/orders/stock-allocations/${this.selectedAllocation.id}/reserve/`, {
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
      this.releaseQty = allocation.reserved_qty
      this.showReleaseDialogFlag = true
    },
    closeReleaseDialog() {
      this.showReleaseDialogFlag = false
      this.selectedAllocation = null
    },
    async releaseStock() {
      try {
        await axios.post(`${API_BASE}/orders/stock-allocations/${this.selectedAllocation.id}/release/`, {
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
    async bulkRelease() {
      const targets = this.allocations.filter(
        (item) => this.selectedIds.includes(item.id) && parseFloat(item.reserved_qty) > 0
      )
      if (!targets.length) {
        alert('解除対象がありません')
        return
      }
      if (!confirm(`選択した${targets.length}件の引当を全量解除します。よろしいですか？`)) return

      for (const target of targets) {
        try {
          await axios.post(`${API_BASE}/orders/stock-allocations/${target.id}/release/`, {
            quantity: target.reserved_qty
          })
        } catch (error) {
          console.error('一括解除エラー:', error)
          alert(`ID ${target.id} の解除に失敗しました: ${error.response?.data?.detail || error.message}`)
          break
        }
      }
      this.fetchAllocations()
    },
    toggleAll(event) {
      if (event.target.checked) {
        this.selectedIds = this.filteredAllocations.map((item) => item.id)
      } else {
        this.selectedIds = []
      }
    },
    downloadCsv() {
      if (!this.filteredAllocations.length) {
        alert('出力対象がありません')
        return
      }
      const header = [
        'id',
        'product_code',
        'product_name',
        'location',
        'current_stock',
        'reserved_qty',
        'available_qty',
        'min_stock_qty',
        'is_bottleneck',
        'updated_at'
      ]
      const rows = this.filteredAllocations.map((item) =>
        [
          item.id,
          item.product_code,
          item.product_name,
          item.location,
          item.current_stock,
          item.reserved_qty,
          item.available_qty,
          item.min_stock_qty,
          item.is_bottleneck,
          item.updated_at
        ].map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')
      )
      const csv = [header.join(','), ...rows].join('\n')
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'stock_allocations.csv'
      a.click()
      window.URL.revokeObjectURL(url)
    },
    formatNumber(value) {
      if (value == null) return '0'
      return parseFloat(value).toLocaleString('ja-JP', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 3
      })
    },
    formatDateTime(value) {
      if (!value) return ''
      return new Date(value).toLocaleString('ja-JP')
    }
  }
}
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
  grid-template-columns: repeat(4, minmax(0, 1fr)) 220px;
  gap: 12px;
  align-items: end;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-field.wide {
  grid-column: span 2;
}

.filter-field input,
.filter-field select {
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

.btn-group {
  display: flex;
  gap: 4px;
}

.text-right {
  text-align: right;
}

.text-center {
  text-align: center;
}

.text-danger {
  color: #d13438;
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
