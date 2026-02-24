<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">製造指示 {{ isEdit ? '編集' : '新規登録' }}</h1>
        <p class="helper-text">製造指示の基本情報と在庫引当の紐付けを行います。</p>
      </div>
      <div class="page-actions">
        <button class="btn-secondary" @click="goList">一覧へ戻る</button>
        <button class="btn-primary" @click="saveOrder" :disabled="!canEdit">保存</button>
      </div>
    </div>

    <div class="page-content">
      <p v-if="!canEdit" class="helper-text">閲覧のみ可能です（編集権限がありません）。</p>
      <form class="form-grid" @submit.prevent="saveOrder">
        <div class="form-group">
          <label>製造指示番号 *</label>
          <input v-model="form.order_no" :disabled="isEdit" required />
          <small class="muted">新規作成時は自動採番: {{ autoOrderNo }}</small>
        </div>

        <div class="form-group">
          <label>製品 *</label>
          <div class="typeahead">
            <input v-model="productSearch" @keyup.enter.prevent="searchProducts" placeholder="品番・品名を検索" />
            <button type="button" class="btn-secondary btn-sm" @click="searchProducts">検索</button>
          </div>
          <select v-model="form.product" required @change="onProductChange">
            <option value="">選択してください</option>
            <option v-for="p in products" :key="p.id" :value="p.id">
              {{ p.product_code }} - {{ p.product_name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>ルーティング</label>
          <select v-model="form.routing">
            <option value="">選択してください</option>
            <option v-for="r in routings" :key="r.id" :value="r.id">
              {{ r.routing_code }} {{ r.routing_name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>ライン *</label>
          <select v-model="form.line" required>
            <option value="">選択してください</option>
            <option v-for="line in lines" :key="line.id" :value="line.id">
              {{ line.line_code }} - {{ line.line_name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>指示数量 *</label>
          <input v-model.number="form.order_qty" type="number" min="0.001" step="0.001" required />
        </div>

        <div class="form-group">
          <label>開始予定日 *</label>
          <input v-model="form.scheduled_start_date" type="date" required />
        </div>

        <div class="form-group">
          <label>完了予定日 *</label>
          <input v-model="form.scheduled_end_date" type="date" required />
        </div>

        <div class="form-group">
          <label>優先度</label>
          <input v-model.number="form.priority" type="number" min="0" />
        </div>

        <div class="form-group">
          <label>在庫引当</label>
          <select v-model="form.allocation">
            <option value="">未選択</option>
            <option v-for="a in allocations" :key="a.id" :value="a.id">
              {{ a.product_code }}@{{ a.location }} / 可用{{ formatNumber(a.available_qty) }}
            </option>
          </select>
          <small class="muted">対象製品の在庫引当を紐付けます。必要に応じて新規作成してください。</small>
        </div>

        <div class="form-group full-row">
          <label>備考</label>
          <textarea v-model="form.remark" rows="3"></textarea>
        </div>

        <div class="form-group">
          <label>ステータス</label>
          <div class="readonly-box">{{ form.status_display || 'PLANNED (計画済)' }}</div>
        </div>

        <div class="form-group">
          <label>負荷試算 (CRP)</label>
          <div class="inline-control">
            <button type="button" class="btn-secondary btn-sm" @click="runCrp">負荷を計算</button>
            <div class="crp-result" v-if="crpResult">
              <div>ライン負荷: {{ formatNumber(crpResult.line_load_minutes) }} 分</div>
              <div>稼働: {{ crpResult.available_minutes }} 分 / 負荷率 {{ crpResult.utilization_rate }}%</div>
              <div :class="{ 'text-danger': crpResult.is_over_capacity }">
                {{ crpResult.is_over_capacity ? 'キャパ超過' : '許容範囲内' }}
              </div>
            </div>
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
  name: 'ProductionOrderForm',
  data() {
    return {
      form: {
        order_no: '',
        product: '',
        routing: '',
        line: '',
        order_qty: 0,
        scheduled_start_date: '',
        scheduled_end_date: '',
        priority: 0,
        allocation: '',
        remark: '',
        status: 'PLANNED',
        status_display: '計画済'
      },
      products: [],
      productSearch: '',
      lines: [],
      routings: [],
      allocations: [],
      crpResult: null,
      loading: false
    }
  },
  computed: {
    isEdit() {
      return Boolean(this.$route.params.id)
    },
    autoOrderNo() {
      const now = new Date()
      const y = now.getFullYear()
      const m = String(now.getMonth() + 1).padStart(2, '0')
      const d = String(now.getDate()).padStart(2, '0')
      const rand = String(Math.floor(Math.random() * 900) + 100)
      return `MO-${y}${m}${d}-${rand}`
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
    this.searchProducts()
    this.fetchLines()
    if (this.isEdit) {
      this.fetchOrder()
    } else {
      this.form.order_no = this.autoOrderNo
    }
  },
  methods: {
    async searchProducts() {
      try {
        const params = {}
        if (this.productSearch) params.search = this.productSearch
        const res = await api.products.getProducts(params)
        this.products = res.data?.results || res.data || []
      } catch (error) {
        console.error('製品取得エラー', error)
      }
    },
    async fetchLines() {
      try {
        const res = await api.lines.getLines()
        this.lines = res.data?.results || res.data || []
      } catch (error) {
        console.error('ライン取得エラー', error)
      }
    },
    async fetchRoutings(productId) {
      if (!productId) {
        this.routings = []
        return
      }
      try {
        const res = await api.routings.getRoutings({ product: productId, is_active: true })
        this.routings = res.data?.results || res.data || []
      } catch (error) {
        console.error('ルーティング取得エラー', error)
      }
    },
    async fetchAllocations(productId) {
      if (!productId) {
        this.allocations = []
        return
      }
      try {
        const res = await api.orders.getStockAllocations({ product: productId })
        this.allocations = res.data?.results || res.data || []
      } catch (error) {
        console.error('在庫引当取得エラー', error)
      }
    },
    async fetchOrder() {
      this.loading = true
      try {
        const { id } = this.$route.params
        const res = await api.orders.getProductionOrder(id)
        const data = res.data?.results || res.data
        this.form = {
          order_no: data.order_no,
          product: data.product,
          routing: data.routing,
          line: data.line,
          order_qty: Number(data.order_qty),
          scheduled_start_date: data.scheduled_start_date,
          scheduled_end_date: data.scheduled_end_date,
          priority: data.priority ?? 0,
          allocation: data.allocation ?? '',
          remark: data.remark,
          status: data.status,
          status_display: data.status_display
        }
        await Promise.all([this.fetchRoutings(data.product), this.fetchAllocations(data.product)])
      } catch (error) {
        console.error('製造指示取得エラー', error)
        alert('データ取得に失敗しました')
      } finally {
        this.loading = false
      }
    },
    onProductChange() {
      this.form.allocation = ''
      this.fetchRoutings(this.form.product)
      this.fetchAllocations(this.form.product)
    },
    validate() {
      if (!this.form.product || !this.form.line || !this.form.order_no) {
        alert('必須項目を入力してください')
        return false
      }
      if (!this.form.scheduled_start_date || !this.form.scheduled_end_date) {
        alert('予定日を入力してください')
        return false
      }
      if (new Date(this.form.scheduled_start_date) > new Date(this.form.scheduled_end_date)) {
        alert('完了予定日は開始予定日以降で指定してください')
        return false
      }
      if (Number(this.form.order_qty) <= 0) {
        alert('指示数量は0より大きい値を入力してください')
        return false
      }
      return true
    },
    async saveOrder() {
      if (!this.canEdit) return
      if (!this.validate()) return
      try {
        if (this.isEdit) {
          await api.orders.updateProductionOrder(this.$route.params.id, this.form)
          alert('製造指示を更新しました')
        } else {
          await api.orders.createProductionOrder(this.form)
          alert('製造指示を登録しました')
        }
        this.goList()
      } catch (error) {
        console.error('保存エラー', error)
        alert('保存に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    async runCrp() {
      if (!this.form.line || !this.form.scheduled_start_date) {
        alert('ラインと開始予定日を入力してください')
        return
      }
      try {
        const res = await api.orders.calculateLineLoad({
          line_id: this.form.line,
          target_date: this.form.scheduled_start_date
        })
        this.crpResult = res.data?.results || res.data
      } catch (error) {
        console.error('CRPエラー', error)
        alert('負荷計算に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    goList() {
      this.$router.push('/production/orders')
    },
    formatNumber(value) {
      if (value == null) return '0'
      return Number(value).toLocaleString('ja-JP', { minimumFractionDigits: 0, maximumFractionDigits: 3 })
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

.form-group.full-row {
  grid-column: 1 / -1;
}

.form-group input,
.form-group select,
.form-group textarea {
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

.readonly-box {
  padding: 10px;
  background: #f8fafc;
  border: 1px dashed #d0d5dd;
  border-radius: 6px;
}

.muted {
  color: #697586;
  font-size: 0.85rem;
}

.crp-result {
  background: #f5f7fa;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
  padding: 8px;
}

.text-danger {
  color: #d13438;
  font-weight: bold;
}
</style>
