<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">発注スケジュール設定</h1>
      <div class="page-actions">
        <button class="btn-primary" @click="fetchSchedules">更新</button>
        <button class="btn-success" @click="openNew">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>仕入先</th>
            <th>パターン</th>
            <th>条件</th>
            <th>LT(日)</th>
            <th>有効</th>
            <th>備考</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ row.supplier_code }} - {{ row.supplier_name }}</td>
            <td>{{ patternLabel(row.pattern_type) }}</td>
            <td>{{ patternCondition(row) }}</td>
            <td>{{ row.lead_time_days }}</td>
            <td>{{ row.is_enabled ? '有効' : '無効' }}</td>
            <td>{{ row.note }}</td>
            <td>
              <button class="btn-sm" @click="openEdit(row)">編集</button>
              <button class="btn-sm btn-danger" @click="remove(row.id)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="rows.length === 0" class="no-data">データがありません</div>
    </div>

    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '発注スケジュール編集' : '発注スケジュール新規作成' }}</h2>
        <form @submit.prevent="save">
          <div class="form-group">
            <label>仕入先 *</label>
            <select v-model="form.supplier" required>
              <option value="">選択してください</option>
              <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
                {{ supplier.supplier_code }} - {{ supplier.supplier_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>パターン *</label>
            <select v-model="form.pattern_type" required>
              <option v-for="item in patternOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
          <div class="form-group" v-if="form.pattern_type === 'WEEKLY_NTH_DAY'">
            <label>第N週 *</label>
            <input v-model.number="form.nth_week" type="number" min="1" max="5" required />
          </div>
          <div class="form-group" v-if="['WEEKLY_NTH_DAY', 'EVERY_WEEK'].includes(form.pattern_type)">
            <label>曜日 *</label>
            <select v-model.number="form.day_of_week" required>
              <option v-for="item in dayOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
          <div class="form-group" v-if="form.pattern_type === 'MONTHLY_DATE'">
            <label>日付 *</label>
            <input v-model.number="form.day_of_month" type="number" min="1" max="31" required />
          </div>
          <div class="form-group">
            <label>リードタイム(日)</label>
            <input v-model.number="form.lead_time_days" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>
              <input v-model="form.is_enabled" type="checkbox" />
              有効
            </label>
          </div>
          <div class="form-group">
            <label>備考</label>
            <input v-model="form.note" />
          </div>
          <div class="form-actions">
            <button class="btn-primary" type="submit">保存</button>
            <button class="btn-secondary" type="button" @click="closeDialog">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '@/api/client'

const rows = ref([])
const suppliers = ref([])
const showDialog = ref(false)
const isEdit = ref(false)

const patternOptions = [
  { value: 'WEEKLY_NTH_DAY', label: '月の第N週の曜日' },
  { value: 'MONTHLY_DATE', label: '毎月日付' },
  { value: 'EVERY_WEEK', label: '毎週曜日' },
]

const dayOptions = [
  { value: 0, label: '月' },
  { value: 1, label: '火' },
  { value: 2, label: '水' },
  { value: 3, label: '木' },
  { value: 4, label: '金' },
  { value: 5, label: '土' },
  { value: 6, label: '日' },
]

const form = ref({
  id: null,
  supplier: '',
  pattern_type: 'WEEKLY_NTH_DAY',
  nth_week: 1,
  day_of_week: 0,
  day_of_month: 1,
  lead_time_days: 0,
  is_enabled: true,
  note: '',
})

const patternLabel = (value) => {
  const found = patternOptions.find((item) => item.value === value)
  return found ? found.label : value
}

const dayLabel = (value) => {
  const found = dayOptions.find((item) => item.value === Number(value))
  return found ? found.label : value
}

const patternCondition = (row) => {
  if (row.pattern_type === 'WEEKLY_NTH_DAY') return `第${row.nth_week} ${dayLabel(row.day_of_week)}`
  if (row.pattern_type === 'MONTHLY_DATE') return `毎月${row.day_of_month}日`
  if (row.pattern_type === 'EVERY_WEEK') return `毎週${dayLabel(row.day_of_week)}`
  return ''
}

const fetchSuppliers = async () => {
  const response = await api.suppliers.getSuppliers()
  suppliers.value = response.data.results || response.data || []
}

const fetchSchedules = async () => {
  const response = await api.supplierOrderSchedules.list()
  rows.value = response.data || []
}

const openNew = () => {
  isEdit.value = false
  form.value = {
    id: null,
    supplier: '',
    pattern_type: 'WEEKLY_NTH_DAY',
    nth_week: 1,
    day_of_week: 0,
    day_of_month: 1,
    lead_time_days: 0,
    is_enabled: true,
    note: '',
  }
  showDialog.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  form.value = { ...row }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const buildPayload = () => {
  const payload = {
    supplier: form.value.supplier,
    pattern_type: form.value.pattern_type,
    lead_time_days: Number(form.value.lead_time_days || 0),
    is_enabled: Boolean(form.value.is_enabled),
    note: form.value.note || '',
    nth_week: null,
    day_of_week: null,
    day_of_month: null,
  }
  if (form.value.pattern_type === 'WEEKLY_NTH_DAY') {
    payload.nth_week = Number(form.value.nth_week || 1)
    payload.day_of_week = Number(form.value.day_of_week || 0)
  }
  if (form.value.pattern_type === 'MONTHLY_DATE') {
    payload.day_of_month = Number(form.value.day_of_month || 1)
  }
  if (form.value.pattern_type === 'EVERY_WEEK') {
    payload.day_of_week = Number(form.value.day_of_week || 0)
  }
  return payload
}

const save = async () => {
  const payload = buildPayload()
  if (isEdit.value) {
    await api.supplierOrderSchedules.update(form.value.id, payload)
  } else {
    await api.supplierOrderSchedules.create(payload)
  }
  showDialog.value = false
  await fetchSchedules()
}

const remove = async (id) => {
  if (!confirm('削除しますか？')) return
  await api.supplierOrderSchedules.delete(id)
  await fetchSchedules()
}

onMounted(async () => {
  await Promise.all([fetchSuppliers(), fetchSchedules()])
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
  padding: 24px;
  border-radius: 8px;
  min-width: 500px;
}
.form-group {
  margin-bottom: 10px;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
