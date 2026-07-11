<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">出荷進度管理</h2>
      <div class="page-actions">
        <input v-model.trim="filters.productCode" type="text" placeholder="品番" />
        <input v-model.trim="filters.customerCode" type="text" placeholder="得意先" />
        <input v-model.trim="filters.shipToCode" type="text" placeholder="納入先" />
        <input v-model="filters.startDate" type="date" />
        <input v-model="filters.endDate" type="date" />
        <button @click="load" :disabled="loading">検索</button>
      </div>
    </div>

    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'actual' }" @click="tab = 'actual'">実績変更</button>
      <button class="tab" :class="{ active: tab === 'adjust' }" @click="tab = 'adjust'">進度調整</button>
    </div>

    <div v-if="loading" class="status-text">読込中...</div>
    <div v-else-if="error" class="status-text error">{{ error }}</div>

    <!-- 実績変更タブ -->
    <div v-else-if="tab === 'actual'" class="tab-body">
      <div class="helper-text">
        出発済・完了の便に紐づく実績は、この画面では変更できません。
      </div>
      <div v-if="!actualRows.length" class="status-text">データがありません</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>出荷日</th>
              <th>品番</th>
              <th>得意先</th>
              <th>納入先</th>
              <th class="num">数量</th>
              <th class="num">変更後</th>
              <th>状態</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in actualRows" :key="row.id" :class="{ changed: row._edited, locked: row.is_locked }">
              <td>{{ row.shipment_date }}</td>
              <td>{{ row.product_code }}</td>
              <td>{{ row.customer_code }}</td>
              <td>{{ row.ship_to_code || '-' }}</td>
              <td class="num">{{ row.quantity }}</td>
              <td class="num edit-cell">
                <input
                  type="number"
                  step="1"
                  min="0"
                  :value="row._newQty"
                  :disabled="row.is_locked"
                  @input="onActualQtyChange(row, $event.target.value)"
                />
              </td>
              <td>{{ row.is_locked ? '便実績' : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="actualRows.length" class="action-bar">
        <span class="change-count">変更: {{ actualChangedCount }}件</span>
        <button class="btn-save" :disabled="saving || !actualChangedCount" @click="saveActuals">
          {{ saving ? '保存中...' : '実績を保存' }}
        </button>
      </div>
    </div>

    <!-- 進度調整タブ -->
    <div v-else-if="tab === 'adjust'" class="tab-body">
      <div v-if="!adjustRows.length" class="status-text">データがありません</div>
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>日付</th>
              <th>品番</th>
              <th>得意先</th>
              <th>納入先</th>
              <th class="num">内示</th>
              <th class="num">確定</th>
              <th class="num">実績</th>
              <th class="num">調整</th>
              <th class="num">進度</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in adjustRows" :key="row.id" :class="{ changed: row._edited }">
              <td>{{ row.plan_date }}</td>
              <td>{{ row.product_code }}</td>
              <td>{{ row.customer_code }}</td>
              <td>{{ row.ship_to_code || '-' }}</td>
              <td class="num">{{ formatQty(row.forecast_qty) }}</td>
              <td class="num">{{ formatQty(row.firm_qty) }}</td>
              <td class="num">{{ formatQty(row.actual_qty) }}</td>
              <td class="num edit-cell">
                <input
                  type="number"
                  step="1"
                  :value="row._newAdjust"
                  @input="onAdjustQtyChange(row, $event.target.value)"
                />
              </td>
              <td class="num" :class="{ negative: row.progress_qty < 0 }">{{ formatQty(row.progress_qty) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="adjustRows.length" class="action-bar">
        <span class="change-count">変更: {{ adjustChangedCount }}件</span>
        <button class="btn-save" :disabled="saving || !adjustChangedCount" @click="saveAdjust">
          {{ saving ? '保存中...' : '調整値を保存' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import api from '@/api/client'

const formatDate = (d) => {
  const yyyy = String(d.getFullYear())
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const today = new Date()
const weekAgo = new Date(today)
weekAgo.setDate(weekAgo.getDate() - 7)

const tab = ref('actual')
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const actualRows = ref([])
const adjustRows = ref([])

const filters = reactive({
  productCode: '',
  customerCode: '',
  shipToCode: '',
  startDate: formatDate(weekAgo),
  endDate: formatDate(today),
})

const formatQty = (val) => {
  if (val === 0 || val === null || val === undefined) return ''
  return Number(val).toLocaleString()
}

const actualChangedCount = computed(() => actualRows.value.filter((r) => r._edited).length)
const adjustChangedCount = computed(() => adjustRows.value.filter((r) => r._edited).length)

const onActualQtyChange = (row, value) => {
  if (row.is_locked) return
  const newVal = String(value || '0')
  row._newQty = newVal
  row._edited = newVal !== row.quantity
}

const onAdjustQtyChange = (row, value) => {
  const newVal = parseInt(value || '0', 10) || 0
  row._newAdjust = newVal
  row._edited = newVal !== row.adjust_qty
}

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const [actualRes, adjustRes] = await Promise.all([
      api.shippingProgress.getActuals({
        start_date: filters.startDate,
        end_date: filters.endDate,
        product_code: filters.productCode,
        customer_code: filters.customerCode,
        ship_to_code: filters.shipToCode,
      }),
      api.shippingProgress.get({
        start_date: filters.startDate,
        end_date: filters.endDate,
        product_code: filters.productCode,
        customer_code: filters.customerCode,
        ship_to_code: filters.shipToCode,
      }),
    ])
    actualRows.value = (actualRes.data?.results || []).map((r) => ({
      ...r,
      _newQty: r.quantity,
      _edited: false,
    }))
    adjustRows.value = (adjustRes.data?.results || []).map((r) => ({
      ...r,
      _newAdjust: r.adjust_qty,
      _edited: false,
    }))
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || '読み込みに失敗しました'
  } finally {
    loading.value = false
  }
}

const saveActuals = async () => {
  const changed = actualRows.value.filter((r) => r._edited && !r.is_locked)
  if (!changed.length) return
  saving.value = true
  try {
    const res = await api.shippingProgress.saveActuals({
      items: changed.map((r) => ({ id: r.id, quantity: r._newQty })),
    })
    window.alert(res.data?.detail || '保存しました。')
    await load()
  } catch (e) {
    window.alert(e?.response?.data?.detail || e?.message || '保存に失敗しました')
  } finally {
    saving.value = false
  }
}

const saveAdjust = async () => {
  const changed = adjustRows.value.filter((r) => r._edited)
  if (!changed.length) return
  saving.value = true
  try {
    const res = await api.shippingProgress.saveAdjust({
      items: changed.map((r) => ({ id: r.id, adjust_qty: r._newAdjust })),
    })
    window.alert(res.data?.detail || '保存しました。')
    await load()
  } catch (e) {
    window.alert(e?.response?.data?.detail || e?.message || '保存に失敗しました')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page-container {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 8px;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
}
.page-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.page-actions input,
.page-actions button {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}
.page-actions button {
  background: #3b82f6;
  color: #fff;
  cursor: pointer;
  font-weight: 500;
}
.page-actions button:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
.tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid #e5e7eb;
}
.tab {
  padding: 8px 20px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
.tab.active {
  color: #1e40af;
  border-bottom-color: #3b82f6;
}
.tab-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.table-wrap {
  flex: 1;
  overflow: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th,
.data-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  white-space: nowrap;
}
.data-table thead th {
  position: sticky;
  top: 0;
  background: #f3f4f6;
  font-weight: 600;
  z-index: 1;
}
.num {
  text-align: right;
}
.edit-cell input {
  width: 90px;
  padding: 4px 6px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  text-align: right;
}
tr.changed {
  background: #fef9c3;
}
.negative {
  color: #dc2626;
  font-weight: 700;
}
.action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-top: 1px solid #e5e7eb;
}
.change-count {
  font-size: 13px;
  color: #475569;
}
.btn-save {
  padding: 8px 20px;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btn-save:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
.status-text {
  text-align: center;
  color: #6b7280;
  padding: 40px;
}
.status-text.error {
  color: #dc2626;
}
.helper-text {
  color: #64748b;
  font-size: 12px;
}
tr.locked {
  background: #f8fafc;
}
.edit-cell input:disabled {
  background: #e5e7eb;
  color: #6b7280;
  cursor: not-allowed;
}
</style>
