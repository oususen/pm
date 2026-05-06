<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">在庫引当 {{ isEdit ? '編集' : '新規登録' }}</h1>
        <p class="helper-text">
          製品×保管場所の在庫・最小在庫・引当数量を管理します。可用在庫はリアルタイムで計算されます。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn-secondary" @click="goList">一覧へ戻る</button>
        <button class="btn-danger" v-if="isEdit" @click="deleteAllocation" :disabled="!canEdit">削除</button>
        <button class="btn-primary" @click="saveAllocation" :disabled="!canEdit">保存</button>
      </div>
    </div>

    <div class="page-content">
      <p v-if="!canEdit" class="helper-text">閲覧のみ可能です（編集権限がありません）。</p>
      <form class="form-grid" @submit.prevent="saveAllocation">
        <div class="form-group">
          <label>製品 *</label>
          <div class="typeahead">
            <input
              v-model="productSearch"
              @keyup.enter.prevent="searchProducts"
              placeholder="品番・品名で検索"
              :disabled="isEdit"
            />
            <button type="button" class="btn-secondary btn-sm" @click="searchProducts" :disabled="isEdit">
              検索
            </button>
          </div>
          <select v-model="form.product" required :disabled="isEdit">
            <option value="">選択してください</option>
            <option v-for="p in products" :key="p.id" :value="p.id">
              {{ p.product_code }} - {{ p.product_name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>保管場所 *</label>
          <input v-model="form.location" required placeholder="例) MAIN, SUB-01" />
        </div>

        <div class="form-group">
          <label>現在在庫 *</label>
          <input v-model.number="form.current_stock" type="number" min="0" step="0.001" required />
        </div>

        <div class="form-group">
          <label>引当済数量 *</label>
          <div class="inline-control">
            <input v-model.number="form.reserved_qty" type="number" min="0" step="0.001" required />
            <div class="chip-group">
              <button type="button" class="chip" @click="adjustReserved(10)">+10</button>
              <button type="button" class="chip" @click="adjustReserved(100)">+100</button>
              <button type="button" class="chip" @click="adjustReserved(-10)">-10</button>
              <button type="button" class="chip" @click="adjustReserved(-100)">-100</button>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>最小在庫 *</label>
          <input v-model.number="form.min_stock_qty" type="number" min="0" step="1" required />
        </div>

        <div class="form-group">
          <label>ボトルネック</label>
          <label class="checkbox-inline">
            <input type="checkbox" v-model="form.is_bottleneck" />
            ボトルネック品としてマーク
          </label>
        </div>

        <div class="form-group">
          <label>可用在庫</label>
          <div class="readonly-box" :class="{ 'text-danger': availableQty < form.min_stock_qty }">
            {{ formatNumber(availableQty) }} （現在在庫 - 引当済）
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

export default {
  name: 'StockAllocationForm',
  data() {
    return {
      form: {
        product: '',
        location: '',
        current_stock: 0,
        reserved_qty: 0,
        min_stock_qty: 0,
        is_bottleneck: false
      },
      products: [],
      productSearch: '',
      loading: false
    }
  },
  computed: {
    isEdit() {
      return Boolean(this.$route.params.id)
    },
    availableQty() {
      return Number(this.form.current_stock || 0) - Number(this.form.reserved_qty || 0)
    },
    canEdit() {
      const user = authState.user
      if (!user) return false
      const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
      if (permissions.some((item) => item.resource === 'production.stock_allocations')) {
        return hasPermission(user, 'production.stock_allocations', 'edit')
      }
      return hasPermission(user, 'production', 'edit')
    }
  },
  mounted() {
    this.searchProducts()
    if (this.isEdit) {
      this.fetchAllocation()
    }
  },
  methods: {
    async searchProducts() {
      try {
        const params = { page_size: 1000 }
        if (this.productSearch) params.search = this.productSearch
        const res = await api.products.getProducts(params)
        this.products = Array.isArray(res.data) ? res.data : (res.data?.results || [])
      } catch (error) {
        console.error('製品検索エラー', error)
        alert('製品の取得に失敗しました')
      }
    },
    async fetchAllocation() {
      this.loading = true
      try {
        const { id } = this.$route.params
        const res = await api.orders.getStockAllocation(id)
        const data = res.data
        this.form = {
          product: data.product,
          location: data.location,
          current_stock: Number(data.current_stock),
          reserved_qty: Number(data.reserved_qty),
          min_stock_qty: Number(data.min_stock_qty),
          is_bottleneck: data.is_bottleneck
        }
        if (!this.products.some((p) => p.id === data.product)) {
          this.products.push({
            id: data.product,
            product_code: data.product_code,
            product_name: data.product_name,
          })
        }
      } catch (error) {
        console.error('取得エラー', error)
        alert('データ取得に失敗しました')
      } finally {
        this.loading = false
      }
    },
    validateForm() {
      if (!this.form.product) {
        alert('製品を選択してください')
        return false
      }
      if (!this.form.location) {
        alert('保管場所を入力してください')
        return false
      }
      if (this.form.current_stock < 0 || this.form.reserved_qty < 0 || this.form.min_stock_qty < 0) {
        alert('数値は0以上で入力してください')
        return false
      }
      if (!Number.isInteger(Number(this.form.min_stock_qty))) {
        alert('最小在庫は整数で入力してください')
        return false
      }
      return true
    },
    async saveAllocation() {
      if (!this.canEdit) return
      if (!this.validateForm()) return
      const payload = {
        ...this.form,
        min_stock_qty: Number.parseInt(this.form.min_stock_qty, 10),
      }
      try {
        if (this.isEdit) {
          await api.orders.updateStockAllocation(this.$route.params.id, payload)
          alert('在庫引当を更新しました')
        } else {
          await api.orders.createStockAllocation(payload)
          alert('在庫引当を登録しました')
        }
        this.goList()
      } catch (error) {
        console.error('保存エラー', error)
        alert('保存に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    async deleteAllocation() {
      if (!this.canEdit) return
      if (!confirm('この在庫引当を削除しますか？')) return
      try {
        await api.orders.deleteStockAllocation(this.$route.params.id)
        alert('削除しました')
        this.goList()
      } catch (error) {
        console.error('削除エラー', error)
        alert('削除に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    adjustReserved(amount) {
      if (!this.canEdit) return
      const next = Number(this.form.reserved_qty || 0) + amount
      this.form.reserved_qty = next < 0 ? 0 : next
    },
    goList() {
      this.$router.push('/production/stock-allocations')
    },
    formatNumber(value) {
      return Number(value || 0).toLocaleString('ja-JP', { minimumFractionDigits: 0, maximumFractionDigits: 3 })
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

.page-content {
  background: #fff;
  border: 1px solid #e3e7eb;
  border-radius: 8px;
  padding: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group input,
.form-group select {
  padding: 10px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
}

.typeahead {
  display: flex;
  gap: 6px;
}

.inline-control {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chip-group {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.chip {
  border: 1px solid #d0d5dd;
  background: #f5f7fa;
  border-radius: 12px;
  padding: 4px 8px;
  cursor: pointer;
}

.chip:hover {
  background: #e8ecf1;
}

.checkbox-inline {
  display: flex;
  gap: 8px;
  align-items: center;
}

.readonly-box {
  padding: 10px;
  background: #f8fafc;
  border: 1px dashed #d0d5dd;
  border-radius: 6px;
}

.text-danger {
  color: #d13438;
  font-weight: bold;
}
</style>

