<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">工程実績入力</h1>
        <p class="helper-text">
          製造指示ごとの工程別実績を登録・編集します。ステータスが中止の指示は入力できません。
        </p>
      </div>
      <div class="page-actions">
        <button class="btn-secondary" @click="goOrders">製造指示一覧へ</button>
      </div>
    </div>

    <div class="page-content">
      <section v-if="order" class="summary">
        <div><label>指示番号</label><span>{{ order.order_no }}</span></div>
        <div><label>製品</label><span>{{ order.product_code }} - {{ order.product_name }}</span></div>
        <div><label>数量</label><span>{{ formatNumber(order.order_qty) }}</span></div>
        <div><label>ライン</label><span>{{ order.line_code }}</span></div>
        <div><label>ステータス</label><span>{{ order.status_display }}</span></div>
        <div><label>予定期間</label><span>{{ order.scheduled_start_date }} ~ {{ order.scheduled_end_date }}</span></div>
      </section>

      <div class="form-and-list">
        <div class="form-card">
          <h3>実績入力</h3>
          <form class="form-grid" @submit.prevent="saveActual">
            <div class="form-group">
              <label>工程 (ルーティング)</label>
              <select v-model="form.routing_step" @change="onRoutingStepChange">
                <option value="">選択してください</option>
                <option v-for="step in routingSteps" :key="step.id" :value="step.id">
                  {{ step.step_no }}: {{ step.process_name }} ({{ step.line_name || 'ライン指定なし' }})
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>工程 *</label>
              <select v-model="form.process" required>
                <option value="">選択してください</option>
                <option v-for="p in processes" :key="p.id" :value="p.id">
                  {{ p.process_code }} - {{ p.process_name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>ライン *</label>
              <select v-model="form.line" required>
                <option value="">選択してください</option>
                <option v-for="l in lines" :key="l.id" :value="l.id">
                  {{ l.line_code }} - {{ l.line_name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>完了数量 *</label>
              <input v-model.number="form.completed_qty" type="number" min="0" step="0.001" required />
            </div>

            <div class="form-group">
              <label>実績工数(分) *</label>
              <input v-model.number="form.actual_duration_min" type="number" min="1" step="1" required />
            </div>

            <div class="form-group">
              <label>完了日時 *</label>
              <input v-model="form.completed_at" type="datetime-local" required />
            </div>

            <div class="form-group">
              <label>作業者</label>
              <input v-model="form.operator" placeholder="任意" />
            </div>

            <div class="form-group full-row">
              <label>備考</label>
              <textarea v-model="form.remark" rows="3"></textarea>
            </div>

            <div class="form-actions">
              <button type="button" class="btn-secondary" @click="resetForm">リセット</button>
              <button type="submit" class="btn-primary" :disabled="orderLocked">
                {{ editingId ? '更新' : '登録' }}
              </button>
            </div>
            <p v-if="orderLocked" class="text-danger small">中止済みの指示には実績を登録できません。</p>
          </form>
        </div>

        <div class="list-card">
          <h3>登録済み実績</h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>工程</th>
                <th>ライン</th>
                <th class="text-right">完了数量</th>
                <th class="text-right">工数(分)</th>
                <th>完了日時</th>
                <th>作業者</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="actual in actuals" :key="actual.id">
                <td>{{ actual.process_code }} - {{ actual.process_name }}</td>
                <td>{{ actual.line_code }}</td>
                <td class="text-right">{{ formatNumber(actual.completed_qty) }}</td>
                <td class="text-right">{{ actual.actual_duration_min }}</td>
                <td>{{ formatDateTime(actual.completed_at) }}</td>
                <td>{{ actual.operator || '-' }}</td>
                <td>
                  <div class="btn-group">
                    <button class="btn-sm" @click="editActual(actual)" :disabled="orderLocked">編集</button>
                    <button class="btn-sm btn-danger" @click="deleteActual(actual)" :disabled="orderLocked">削除</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="!actuals.length" class="no-data">実績がありません</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/api/client'

export default {
  name: 'ProcessActualEntry',
  data() {
    return {
      order: null,
      actuals: [],
      routingSteps: [],
      processes: [],
      lines: [],
      editingId: null,
      form: {
        routing_step: '',
        process: '',
        line: '',
        completed_qty: 0,
        actual_duration_min: 1,
        completed_at: '',
        operator: '',
        remark: ''
      }
    }
  },
  computed: {
    orderLocked() {
      return this.order && this.order.status === 'CANCELED'
    }
  },
  mounted() {
    this.fetchMaster()
    this.fetchOrder()
  },
  methods: {
    async fetchMaster() {
      try {
        const [processRes, lineRes] = await Promise.all([
          api.processes.getProcesses({ is_active: true }),
          api.lines.getLines()
        ])
        this.processes = processRes.data?.results || processRes.data || []
        this.lines = lineRes.data?.results || lineRes.data || []
      } catch (error) {
        console.error('マスタ取得エラー', error)
      }
    },
    async fetchOrder() {
      try {
        const { id } = this.$route.params
        const res = await api.orders.getProductionOrder(id)
        const data = res.data?.results || res.data
        this.order = data
        this.actuals = data.actuals || []
        this.form.line = data.line
        this.form.completed_at = this.toDateTimeLocal(new Date())
        if (data.routing) {
          this.fetchRoutingSteps(data.routing)
        }
      } catch (error) {
        console.error('製造指示取得エラー', error)
        alert('製造指示の取得に失敗しました')
      }
    },
    async fetchRoutingSteps(routingId) {
      try {
        const res = await api.routings.getRoutingSteps({ routing: routingId })
        this.routingSteps = res.data?.results || res.data || []
      } catch (error) {
        console.error('ルーティング工程取得エラー', error)
      }
    },
    resetForm() {
      this.editingId = null
      this.form = {
        routing_step: '',
        process: '',
        line: this.order?.line || '',
        completed_qty: 0,
        actual_duration_min: 1,
        completed_at: this.toDateTimeLocal(new Date()),
        operator: '',
        remark: ''
      }
    },
    onRoutingStepChange() {
      const step = this.routingSteps.find((s) => s.id === this.form.routing_step)
      if (step) {
        this.form.process = step.process
        this.form.line = step.line || this.form.line
      }
    },
    async saveActual() {
      if (this.orderLocked) return
      if (!this.order) return
      if (!this.form.process || !this.form.line || !this.form.completed_at) {
        alert('必須項目を入力してください')
        return
      }
      if (this.form.actual_duration_min < 1) {
        alert('実績工数は1以上で入力してください')
        return
      }
      const payload = {
        production_order: this.order.id,
        routing_step: this.form.routing_step || null,
        process: this.form.process,
        line: this.form.line,
        completed_qty: this.form.completed_qty,
        actual_duration_min: this.form.actual_duration_min,
        completed_at: this.form.completed_at,
        operator: this.form.operator,
        remark: this.form.remark
      }
      try {
        if (this.editingId) {
          await api.orders.updateProcessActual(this.editingId, payload)
          alert('実績を更新しました')
        } else {
          await api.orders.createProcessActual(payload)
          alert('実績を登録しました')
        }
        this.resetForm()
        this.fetchOrder()
      } catch (error) {
        console.error('保存エラー', error)
        alert('保存に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    editActual(actual) {
      this.editingId = actual.id
      this.form = {
        routing_step: actual.routing_step || '',
        process: actual.process,
        line: actual.line,
        completed_qty: Number(actual.completed_qty),
        actual_duration_min: Number(actual.actual_duration_min),
        completed_at: this.toDateTimeLocal(actual.completed_at),
        operator: actual.operator,
        remark: actual.remark
      }
    },
    async deleteActual(actual) {
      if (this.orderLocked) return
      if (!confirm('この実績を削除しますか？')) return
      try {
        await api.orders.deleteProcessActual(actual.id)
        alert('削除しました')
        this.fetchOrder()
      } catch (error) {
        console.error('削除エラー', error)
        alert('削除に失敗しました: ' + (error.response?.data?.detail || error.message))
      }
    },
    goOrders() {
      this.$router.push('/production/orders')
    },
    formatNumber(value) {
      return Number(value || 0).toLocaleString('ja-JP', { minimumFractionDigits: 0, maximumFractionDigits: 3 })
    },
    formatDateTime(value) {
      if (!value) return ''
      return new Date(value).toLocaleString('ja-JP')
    },
    toDateTimeLocal(value) {
      const d = value instanceof Date ? value : new Date(value)
      const yyyy = d.getFullYear()
      const mm = String(d.getMonth() + 1).padStart(2, '0')
      const dd = String(d.getDate()).padStart(2, '0')
      const hh = String(d.getHours()).padStart(2, '0')
      const min = String(d.getMinutes()).padStart(2, '0')
      return `${yyyy}-${mm}-${dd}T${hh}:${min}`
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

.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
  background: #f8fafc;
  border: 1px solid #e3e7eb;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.summary label {
  font-weight: bold;
  margin-right: 6px;
}

.form-and-list {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 16px;
}

.form-card,
.list-card {
  background: #fff;
  border: 1px solid #e3e7eb;
  border-radius: 8px;
  padding: 14px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
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
  padding: 8px;
  border: 1px solid #d0d5dd;
  border-radius: 6px;
}

.form-actions {
  display: flex;
  gap: 8px;
  align-items: center;
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
  padding: 8px;
  border-bottom: 1px solid #edf1f5;
}

.btn-group {
  display: flex;
  gap: 4px;
}

.text-right {
  text-align: right;
}

.text-danger {
  color: #d13438;
  font-weight: bold;
}

.small {
  font-size: 0.85rem;
}
</style>
