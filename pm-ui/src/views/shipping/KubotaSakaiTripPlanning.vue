<template>
  <div class="trip-planning-page">
    <div class="toolbar">
      <div class="field">
        <label>出荷日</label>
        <input v-model="targetDate" type="date" />
      </div>
      <div class="field search-field">
        <label>検索</label>
        <input v-model.trim="keyword" type="text" placeholder="品番/品名" @keydown.enter="loadGrid" />
      </div>
      <button class="btn save-btn" :disabled="loading || saving" @click="save">保存</button>
      <button class="btn" :disabled="loading" @click="loadGrid">表示のみ</button>
    </div>

    <div class="summary">
      <div v-for="item in truckSummaries" :key="item.truck_id" class="summary-card" :class="{ error: item.errors?.length }">
        <div class="truck-name">{{ item.truck_name }}</div>
        <div class="value">{{ item.occupancy_percent }}%</div>
        <div class="sub">重量 {{ formatNumber(item.total_weight) }}kg</div>
      </div>
    </div>

    <div class="table-wrap">
      <table class="grid">
        <thead>
          <tr>
            <th>調整後納期</th>
            <th>品番</th>
            <th>品名</th>
            <th>数量</th>
            <th>未割付</th>
            <th>割付</th>
            <th>期限</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.order_line_id" :class="{ overdue: row.overdue }">
            <td>{{ row.adjusted_due_date }}</td>
            <td>{{ row.product_code }}</td>
            <td>{{ row.product_name }}</td>
            <td class="num">{{ formatNumber(row.qty) }}</td>
            <td class="num">{{ formatNumber(row.unassigned_qty_preview) }}</td>
            <td>
              <div v-for="(al, idx) in row.allocations" :key="`${row.order_line_id}-${idx}`" class="allocation-row">
                <select v-model.number="al.truck_id">
                  <option :value="null">便を選択</option>
                  <option v-for="truck in trucks" :key="truck.id" :value="truck.id">{{ truck.name }}</option>
                </select>
                <input v-model="al.qty" type="text" inputmode="decimal" @input="recalcRow(row)" />
                <button class="mini" @click="addAllocation(row)">+</button>
                <button class="mini danger" :disabled="row.allocations.length <= 1" @click="removeAllocation(row, idx)">-</button>
              </div>
            </td>
            <td :class="{ warn: row.overdue }">{{ row.deadline_date }}</td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="7" class="empty">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="note">未割付期限: 調整後納期の{{ assignmentDeadlineDays }}営業日前</div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '@/api/client'

const formatLocalDate = (date) => {
  const yyyy = String(date.getFullYear())
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const targetDate = ref(formatLocalDate(new Date()))
const keyword = ref('')
const loading = ref(false)
const saving = ref(false)
const assignmentDeadlineDays = ref(3)
const trucks = ref([])
const truckSummaries = ref([])
const rows = ref([])

const parseNumber = (value) => {
  if (value === null || value === undefined || value === '') return 0
  const num = Number(String(value).replace(/,/g, ''))
  return Number.isFinite(num) ? num : 0
}

const formatNumber = (value) => {
  const num = parseNumber(value)
  if (Math.abs(num) < 0.000001) return '0'
  return Number.isInteger(num) ? String(num) : num.toFixed(3).replace(/\.?0+$/, '')
}

const recalcRow = (row) => {
  const assigned = row.allocations.reduce((sum, item) => sum + parseNumber(item.qty), 0)
  row.unassigned_qty_preview = Number((parseNumber(row.qty) - assigned).toFixed(3))
}

const normalizeAllocation = (item = null) => ({
  truck_id: item?.truck_id ?? null,
  qty: item?.qty ?? '',
})

const loadGrid = async () => {
  loading.value = true
  try {
    const res = await api.kubotaSakaiTripAssignments.grid({
      target_date: targetDate.value,
      keyword: keyword.value,
    })
    trucks.value = Array.isArray(res.data?.trucks) ? res.data.trucks : []
    truckSummaries.value = Array.isArray(res.data?.truck_summaries) ? res.data.truck_summaries : []
    assignmentDeadlineDays.value = Number(res.data?.assignment_deadline_days || 3)
    const payloadRows = Array.isArray(res.data?.rows) ? res.data.rows : []
    rows.value = payloadRows.map((row) => {
      const allocations = Array.isArray(row.allocations) && row.allocations.length
        ? row.allocations.map((a) => normalizeAllocation(a))
        : [normalizeAllocation()]
      const wrapped = { ...row, allocations, unassigned_qty_preview: parseNumber(row.unassigned_qty) }
      recalcRow(wrapped)
      return wrapped
    })
  } catch (error) {
    const message = error?.response?.data?.detail || 'データ取得に失敗しました。'
    alert(message)
  } finally {
    loading.value = false
  }
}

const addAllocation = (row) => {
  row.allocations.push(normalizeAllocation())
}

const removeAllocation = (row, idx) => {
  if (row.allocations.length <= 1) return
  row.allocations.splice(idx, 1)
  recalcRow(row)
}

const save = async () => {
  saving.value = true
  try {
    const payloadRows = rows.value.map((row) => ({
      order_line_id: row.order_line_id,
      allocations: row.allocations
        .map((item) => ({
          truck_id: item.truck_id,
          qty: parseNumber(item.qty),
        }))
        .filter((item) => item.truck_id && item.qty > 0),
    }))
    await api.kubotaSakaiTripAssignments.bulkSave(targetDate.value, payloadRows)
    await loadGrid()
    alert('保存しました。')
  } catch (error) {
    const detail = error?.response?.data?.detail || '保存に失敗しました。'
    const errors = error?.response?.data?.errors
    if (Array.isArray(errors) && errors.length > 0) {
      const lines = errors.map((item) => {
        if (item.truck_name) return `${item.truck_name}: ${(item.errors || []).join(', ')}`
        if (item.order_line_id) return `order_line_id=${item.order_line_id}: ${item.detail || '入力エラー'}`
        return JSON.stringify(item)
      })
      alert([detail, ...lines].join('\n'))
    } else {
      alert(detail)
    }
  } finally {
    saving.value = false
  }
}

onMounted(loadGrid)
</script>

<style scoped>
.trip-planning-page {
  padding: 8px;
  background: #eef2f6;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toolbar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #e1e8f4;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 8px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.field label {
  font-size: 12px;
  color: #374151;
}
.field input,
.field select {
  min-width: 120px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.search-field input {
  min-width: 220px;
}
.btn {
  padding: 6px 12px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.save-btn {
  background: #dff3e6;
  border-color: #8fc8a1;
}
.summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
}
.summary-card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 8px;
}
.summary-card.error {
  border-color: #ef4444;
  background: #fff1f2;
}
.truck-name {
  font-size: 12px;
  color: #374151;
}
.value {
  font-size: 20px;
  font-weight: 700;
}
.sub {
  font-size: 12px;
  color: #6b7280;
}
.table-wrap {
  flex: 1;
  overflow: auto;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
}
.grid {
  width: 100%;
  border-collapse: collapse;
}
.grid th,
.grid td {
  border: 1px solid #d7dfe8;
  padding: 6px;
  font-size: 12px;
  vertical-align: top;
}
.grid th {
  background: #e7edf7;
}
.allocation-row {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
}
.allocation-row select,
.allocation-row input {
  border: 1px solid #d1d5db;
  border-radius: 3px;
  padding: 2px 4px;
}
.allocation-row input {
  width: 80px;
  text-align: right;
}
.mini {
  width: 24px;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  background: #fff;
  cursor: pointer;
}
.mini.danger {
  color: #b91c1c;
}
.num {
  text-align: right;
}
.overdue {
  background: #fff1f2;
}
.warn {
  color: #b91c1c;
  font-weight: 700;
}
.empty {
  text-align: center;
  color: #6b7280;
  padding: 20px 0;
}
.note {
  font-size: 12px;
  color: #6b7280;
}
</style>
