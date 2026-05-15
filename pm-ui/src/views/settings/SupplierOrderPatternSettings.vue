<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">納入パターン設定</h1>
      <div class="page-actions">
        <button class="btn-primary" @click="fetchPatterns">更新</button>
        <button class="btn-success" @click="openNew">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>コード</th>
            <th>パターン名</th>
            <th>繰返し種別</th>
            <th>条件</th>
            <th>有効</th>
            <th>備考</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ row.pattern_code }}</td>
            <td>{{ row.pattern_name }}</td>
            <td>{{ row.recurrence_type_display }}</td>
            <td>{{ conditionLabel(row) }}</td>
            <td>{{ row.is_active ? '有効' : '無効' }}</td>
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
        <h2>{{ isEdit ? '納入パターン編集' : '納入パターン新規作成' }}</h2>
        <form @submit.prevent="save">
          <div class="form-group">
            <label>パターンコード *</label>
            <input v-model.trim="form.pattern_code" required maxlength="30" placeholder="例: W-MON" />
          </div>
          <div class="form-group">
            <label>パターン名 *</label>
            <input v-model.trim="form.pattern_name" required maxlength="100" placeholder="例: 毎週月曜" />
          </div>
          <div class="form-group">
            <label>繰返し種別 *</label>
            <select v-model="form.recurrence_type" required>
              <option v-for="item in recurrenceOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
          <div class="form-group" v-if="form.recurrence_type === 'MONTHLY_NTH_DOW'">
            <label>第N週 *（複数選択可）</label>
            <div class="checkbox-row">
              <label v-for="w in 5" :key="w" class="checkbox-item">
                <input type="checkbox" :value="w" v-model="form.nth_weeks" />
                第{{ w }}
              </label>
            </div>
          </div>
          <div class="form-group" v-if="['WEEKLY', 'MONTHLY_NTH_DOW'].includes(form.recurrence_type)">
            <label>曜日 *（複数選択可）</label>
            <div class="checkbox-row">
              <label v-for="item in dayOptions" :key="item.value" class="checkbox-item">
                <input type="checkbox" :value="item.value" v-model="form.days_of_week" />
                {{ item.label }}
              </label>
            </div>
          </div>
          <div class="form-group" v-if="form.recurrence_type === 'MONTHLY_DATE'">
            <label>日付 *（複数選択可）</label>
            <div class="checkbox-row checkbox-row-wrap">
              <label v-for="d in 31" :key="d" class="checkbox-item">
                <input type="checkbox" :value="d" v-model="form.days_of_month" />
                {{ d }}
              </label>
            </div>
          </div>
          <div class="form-group" v-if="form.recurrence_type === 'EVERY_N_BUSINESS_DAYS'">
            <label>間隔営業日数 *</label>
            <input v-model.number="form.interval_days" type="number" min="1" required placeholder="例: 2（2営業日ごと）" />
          </div>
          <div class="form-group" v-if="form.recurrence_type === 'EVERY_N_BUSINESS_DAYS'">
            <label>開始基準日 *</label>
            <input v-model="form.start_date" type="date" required />
          </div>
          <div class="form-group">
            <label>
              <input v-model="form.is_active" type="checkbox" />
              有効
            </label>
          </div>
          <div class="form-group">
            <label>備考</label>
            <input v-model="form.note" maxlength="200" />
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
const showDialog = ref(false)
const isEdit = ref(false)

const recurrenceOptions = [
  { value: 'WEEKLY', label: '毎週曜日' },
  { value: 'MONTHLY_DATE', label: '毎月日付' },
  { value: 'MONTHLY_NTH_DOW', label: '月の第N週の曜日' },
  { value: 'EVERY_BUSINESS_DAY', label: '毎営業日' },
  { value: 'EVERY_N_BUSINESS_DAYS', label: 'N営業日ごと' },
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

const parseCsvInts = (value) => {
  if (!value) return []
  if (Array.isArray(value)) return value.map(Number)
  return String(value).split(',').filter(s => s.trim()).map(Number)
}

const defaultForm = () => ({
  id: null,
  pattern_code: '',
  pattern_name: '',
  recurrence_type: 'WEEKLY',
  days_of_week: [],
  nth_weeks: [],
  days_of_month: [],
  interval_days: 2,
  start_date: '',
  is_active: true,
  note: '',
})

const form = ref(defaultForm())

const dayLabel = (value) => {
  const found = dayOptions.find((item) => item.value === Number(value))
  return found ? found.label : value
}

const daysLabel = (csv) => {
  return parseCsvInts(csv).map(dayLabel).join('・')
}

const conditionLabel = (row) => {
  if (row.recurrence_type === 'WEEKLY') return `毎週 ${daysLabel(row.days_of_week)}`
  if (row.recurrence_type === 'MONTHLY_DATE') {
    const days = parseCsvInts(row.days_of_month).join('・')
    return `毎月 ${days}日`
  }
  if (row.recurrence_type === 'MONTHLY_NTH_DOW') {
    const weeks = parseCsvInts(row.nth_weeks).map(w => `第${w}`).join('・')
    return `${weeks} ${daysLabel(row.days_of_week)}`
  }
  if (row.recurrence_type === 'EVERY_BUSINESS_DAY') return '毎営業日'
  if (row.recurrence_type === 'EVERY_N_BUSINESS_DAYS') return `${row.interval_days}営業日ごと (基準: ${row.start_date})`
  return ''
}

const fetchPatterns = async () => {
  const response = await api.supplierOrderPatterns.list()
  rows.value = response.data || []
}

const openNew = () => {
  isEdit.value = false
  form.value = defaultForm()
  showDialog.value = true
}

const openEdit = (row) => {
  isEdit.value = true
  form.value = {
    ...row,
    days_of_week: parseCsvInts(row.days_of_week),
    nth_weeks: parseCsvInts(row.nth_weeks),
    days_of_month: parseCsvInts(row.days_of_month),
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const buildPayload = () => {
  const payload = {
    pattern_code: form.value.pattern_code,
    pattern_name: form.value.pattern_name,
    recurrence_type: form.value.recurrence_type,
    is_active: Boolean(form.value.is_active),
    note: form.value.note || '',
    nth_weeks: '',
    days_of_week: '',
    days_of_month: '',
  }
  if (['WEEKLY', 'MONTHLY_NTH_DOW'].includes(form.value.recurrence_type)) {
    payload.days_of_week = [...form.value.days_of_week].sort((a, b) => a - b).join(',')
  }
  if (form.value.recurrence_type === 'MONTHLY_DATE') {
    payload.days_of_month = [...form.value.days_of_month].sort((a, b) => a - b).join(',')
  }
  if (form.value.recurrence_type === 'MONTHLY_NTH_DOW') {
    payload.nth_weeks = [...form.value.nth_weeks].sort((a, b) => a - b).join(',')
  }
  if (form.value.recurrence_type === 'EVERY_N_BUSINESS_DAYS') {
    payload.interval_days = Number(form.value.interval_days)
    payload.start_date = form.value.start_date
  }
  return payload
}

const save = async () => {
  const payload = buildPayload()
  if (isEdit.value) {
    await api.supplierOrderPatterns.update(form.value.id, payload)
  } else {
    await api.supplierOrderPatterns.create(payload)
  }
  showDialog.value = false
  await fetchPatterns()
}

const remove = async (id) => {
  if (!confirm('削除しますか？')) return
  try {
    await api.supplierOrderPatterns.delete(id)
    await fetchPatterns()
  } catch (e) {
    const msg = e.response?.data?.detail || '削除に失敗しました'
    alert(msg)
  }
}

onMounted(fetchPatterns)
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
.checkbox-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.checkbox-row-wrap {
  gap: 6px 12px;
}
.checkbox-item {
  display: flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  white-space: nowrap;
}
</style>
