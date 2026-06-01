<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">納入パターン設定 <button v-if="authState.user?.is_superuser" class="ds-btn" @click="showDataSource = true" title="データソース"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg></button></h1>
      <div class="page-actions">
        <button class="btn-primary" @click="refreshAll">更新</button>
      </div>
    </div>

    <div class="page-content">
      <div class="section-header">
        <h2 class="section-title">パターン定義</h2>
        <button class="btn-success btn-sm" @click="openNewPattern">新規</button>
      </div>
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
          <tr v-for="row in patternRows" :key="row.id">
            <td>{{ row.pattern_code }}</td>
            <td>{{ row.pattern_name }}</td>
            <td>{{ row.recurrence_type_display }}</td>
            <td>{{ conditionLabel(row) }}</td>
            <td>{{ row.is_active ? '有効' : '無効' }}</td>
            <td>{{ row.note }}</td>
            <td class="actions-cell">
              <button class="btn-sm" @click="openEditPattern(row)">編集</button>
              <button class="btn-sm btn-danger" @click="removePattern(row.id)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="patternRows.length === 0" class="no-data">データがありません</div>

      <div class="section-header mt">
        <h2 class="section-title">仕入れ先割当</h2>
        <button class="btn-success btn-sm" @click="openNewSchedule">新規</button>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>仕入先</th>
            <th>パターン</th>
            <th>LT(日)</th>
            <th>有効</th>
            <th>備考</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in scheduleRows" :key="row.id">
            <td>{{ row.supplier_code }} - {{ row.supplier_name }}</td>
            <td>{{ row.pattern_code }} - {{ row.pattern_name }}</td>
            <td>{{ row.lead_time_days }}</td>
            <td>{{ row.is_enabled ? '有効' : '無効' }}</td>
            <td>{{ row.note }}</td>
            <td class="actions-cell">
              <button class="btn-sm" @click="openEditSchedule(row)">編集</button>
              <button class="btn-sm btn-danger" @click="removeSchedule(row.id)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="scheduleRows.length === 0" class="no-data">データがありません</div>
    </div>

    <div v-if="showPatternDialog" class="modal-overlay" @click.self="showPatternDialog = false">
      <div class="modal-content">
        <h2>{{ isEditPattern ? '納入パターン編集' : '納入パターン新規作成' }}</h2>
        <form @submit.prevent="savePattern">
          <div class="form-group">
            <label>パターンコード *</label>
            <input v-model.trim="patternForm.pattern_code" required maxlength="30" placeholder="例: W-MON" />
          </div>
          <div class="form-group">
            <label>パターン名 *</label>
            <input v-model.trim="patternForm.pattern_name" required maxlength="100" placeholder="例: 毎週月曜" />
          </div>
          <div class="form-group">
            <label>繰返し種別 *</label>
            <select v-model="patternForm.recurrence_type" required>
              <option v-for="item in recurrenceOptions" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select>
          </div>
          <div class="form-group" v-if="patternForm.recurrence_type === 'MONTHLY_NTH_DOW'">
            <label>第N週 *（複数選択可）</label>
            <div class="checkbox-row">
              <label v-for="w in 5" :key="w" class="checkbox-item">
                <input type="checkbox" :value="w" v-model="patternForm.nth_weeks" />
                第{{ w }}
              </label>
            </div>
          </div>
          <div class="form-group" v-if="['WEEKLY', 'MONTHLY_NTH_DOW'].includes(patternForm.recurrence_type)">
            <label>曜日 *（複数選択可）</label>
            <div class="checkbox-row">
              <label v-for="item in dayOptions" :key="item.value" class="checkbox-item">
                <input type="checkbox" :value="item.value" v-model="patternForm.days_of_week" />
                {{ item.label }}
              </label>
            </div>
          </div>
          <div class="form-group" v-if="patternForm.recurrence_type === 'MONTHLY_DATE'">
            <label>日付 *（複数選択可）</label>
            <div class="checkbox-row checkbox-row-wrap">
              <label v-for="d in 31" :key="d" class="checkbox-item">
                <input type="checkbox" :value="d" v-model="patternForm.days_of_month" />
                {{ d }}
              </label>
            </div>
          </div>
          <div class="form-group" v-if="patternForm.recurrence_type === 'EVERY_N_BUSINESS_DAYS'">
            <label>間隔営業日数 *</label>
            <input v-model.number="patternForm.interval_days" type="number" min="1" required placeholder="例: 2（2営業日ごと）" />
          </div>
          <div class="form-group">
            <label>
              <input v-model="patternForm.is_active" type="checkbox" />
              有効
            </label>
          </div>
          <div class="form-group">
            <label>備考</label>
            <input v-model="patternForm.note" maxlength="200" />
          </div>
          <div class="form-actions">
            <button class="btn-primary" type="submit">保存</button>
            <button class="btn-secondary" type="button" @click="showPatternDialog = false">キャンセル</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showScheduleDialog" class="modal-overlay" @click.self="showScheduleDialog = false">
      <div class="modal-content">
        <h2>{{ isEditSchedule ? '仕入れ先スケジュール編集' : '仕入れ先スケジュール新規作成' }}</h2>
        <form @submit.prevent="saveSchedule">
          <div class="form-group">
            <label>仕入先 *</label>
            <select v-model="scheduleForm.supplier" required>
              <option value="">選択してください</option>
              <option v-for="s in suppliers" :key="s.id" :value="s.id">
                {{ s.supplier_code }} - {{ s.supplier_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>パターン *</label>
            <select v-model="scheduleForm.pattern" required>
              <option value="">選択してください</option>
              <option v-for="p in activePatterns" :key="p.id" :value="p.id">
                {{ p.pattern_code }} - {{ p.pattern_name }}
              </option>
            </select>
          </div>
          <div class="form-group" v-if="selectedSchedulePattern?.recurrence_type === 'EVERY_N_BUSINESS_DAYS'">
            <label>開始基準日 *</label>
            <input v-model="scheduleForm.start_date" type="date" required />
          </div>
          <div class="form-group">
            <label>リードタイム(日)</label>
            <input v-model.number="scheduleForm.lead_time_days" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>
              <input v-model="scheduleForm.is_enabled" type="checkbox" />
              有効
            </label>
          </div>
          <div class="form-group">
            <label>備考</label>
            <input v-model="scheduleForm.note" />
          </div>
          <div class="form-actions">
            <button class="btn-primary" type="submit">保存</button>
            <button class="btn-secondary" type="button" @click="showScheduleDialog = false">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
    <!-- データソースモーダル -->
    <div v-if="showDataSource" class="ds-overlay" @click.self="showDataSource = false">
      <div class="ds-modal">
        <div class="ds-header"><h3>データソース</h3><button class="ds-close" @click="showDataSource = false">&times;</button></div>
        <table class="ds-table">
          <thead><tr><th>操作</th><th>テーブル</th><th>説明</th></tr></thead>
          <tbody>
            <tr class="ds-section"><td colspan="3"><strong>パターン定義</strong></td></tr>
            <tr><td>パターン 読み書き</td><td>supplier_order_pattern</td><td>納入パターン定義（繰返し種別・曜日・間隔等）</td></tr>
            <tr class="ds-section"><td colspan="3"><strong>仕入先割当</strong></td></tr>
            <tr><td>スケジュール 読み書き</td><td>supplier_order_schedule</td><td>仕入先×パターン割当（開始基準日・リードタイム）</td></tr>
            <tr class="ds-section"><td colspan="3"><strong>マスタ</strong></td></tr>
            <tr><td>仕入先 読み取り</td><td>m_supplier</td><td>仕入先マスタ</td></tr>
            <tr><td>営業日カレンダー 読み取り</td><td>m_calendar</td><td>営業日判定（N営業日ごと計算用）</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'

const showDataSource = ref(false)
const patternRows = ref([])
const scheduleRows = ref([])
const suppliers = ref([])
const showPatternDialog = ref(false)
const showScheduleDialog = ref(false)
const isEditPattern = ref(false)
const isEditSchedule = ref(false)

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

const defaultPatternForm = () => ({
  id: null,
  pattern_code: '',
  pattern_name: '',
  recurrence_type: 'WEEKLY',
  days_of_week: [],
  nth_weeks: [],
  days_of_month: [],
  interval_days: 2,
  is_active: true,
  note: '',
})

const patternForm = ref(defaultPatternForm())

const scheduleForm = ref({
  id: null,
  supplier: '',
  pattern: '',
  start_date: '',
  lead_time_days: 0,
  is_enabled: true,
  note: '',
})

const activePatterns = computed(() => patternRows.value.filter(p => p.is_active))
const selectedSchedulePattern = computed(() => {
  const id = Number(scheduleForm.value.pattern)
  if (!id) return null
  return patternRows.value.find((p) => Number(p.id) === id) || null
})

const dayLabel = (value) => {
  const found = dayOptions.find((item) => item.value === Number(value))
  return found ? found.label : value
}

const daysLabel = (csv) => parseCsvInts(csv).map(dayLabel).join('・')

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
  if (row.recurrence_type === 'EVERY_N_BUSINESS_DAYS') return `${row.interval_days}営業日ごと`
  return ''
}

const fetchPatterns = async () => {
  const response = await api.supplierOrderPatterns.list()
  patternRows.value = response.data || []
}

const fetchSchedules = async () => {
  const response = await api.supplierOrderSchedules.list()
  scheduleRows.value = response.data || []
}

const fetchSuppliers = async () => {
  const response = await api.suppliers.getSuppliers()
  suppliers.value = response.data.results || response.data || []
}

const refreshAll = async () => {
  await Promise.all([fetchPatterns(), fetchSchedules(), fetchSuppliers()])
}

const openNewPattern = () => {
  isEditPattern.value = false
  patternForm.value = defaultPatternForm()
  showPatternDialog.value = true
}

const openEditPattern = (row) => {
  isEditPattern.value = true
  patternForm.value = {
    ...row,
    days_of_week: parseCsvInts(row.days_of_week),
    nth_weeks: parseCsvInts(row.nth_weeks),
    days_of_month: parseCsvInts(row.days_of_month),
  }
  showPatternDialog.value = true
}

const buildPatternPayload = () => {
  const payload = {
    pattern_code: patternForm.value.pattern_code,
    pattern_name: patternForm.value.pattern_name,
    recurrence_type: patternForm.value.recurrence_type,
    is_active: Boolean(patternForm.value.is_active),
    note: patternForm.value.note || '',
    nth_weeks: '',
    days_of_week: '',
    days_of_month: '',
  }
  if (['WEEKLY', 'MONTHLY_NTH_DOW'].includes(patternForm.value.recurrence_type)) {
    payload.days_of_week = [...patternForm.value.days_of_week].sort((a, b) => a - b).join(',')
  }
  if (patternForm.value.recurrence_type === 'MONTHLY_DATE') {
    payload.days_of_month = [...patternForm.value.days_of_month].sort((a, b) => a - b).join(',')
  }
  if (patternForm.value.recurrence_type === 'MONTHLY_NTH_DOW') {
    payload.nth_weeks = [...patternForm.value.nth_weeks].sort((a, b) => a - b).join(',')
  }
  if (patternForm.value.recurrence_type === 'EVERY_N_BUSINESS_DAYS') {
    payload.interval_days = Number(patternForm.value.interval_days)
  }
  return payload
}

const savePattern = async () => {
  const payload = buildPatternPayload()
  if (isEditPattern.value) {
    await api.supplierOrderPatterns.update(patternForm.value.id, payload)
  } else {
    await api.supplierOrderPatterns.create(payload)
  }
  showPatternDialog.value = false
  await fetchPatterns()
}

const removePattern = async (id) => {
  if (!confirm('削除しますか？')) return
  try {
    await api.supplierOrderPatterns.delete(id)
    await fetchPatterns()
  } catch (e) {
    const msg = e.response?.data?.detail || '削除に失敗しました'
    alert(msg)
  }
}

const openNewSchedule = () => {
  isEditSchedule.value = false
  scheduleForm.value = { id: null, supplier: '', pattern: '', start_date: '', lead_time_days: 0, is_enabled: true, note: '' }
  showScheduleDialog.value = true
}

const openEditSchedule = (row) => {
  isEditSchedule.value = true
  scheduleForm.value = { ...row }
  showScheduleDialog.value = true
}

const saveSchedule = async () => {
  const isEveryNBusinessDays = selectedSchedulePattern.value?.recurrence_type === 'EVERY_N_BUSINESS_DAYS'
  const payload = {
    supplier: scheduleForm.value.supplier,
    pattern: scheduleForm.value.pattern,
    start_date: isEveryNBusinessDays ? (scheduleForm.value.start_date || null) : null,
    lead_time_days: Number(scheduleForm.value.lead_time_days || 0),
    is_enabled: Boolean(scheduleForm.value.is_enabled),
    note: scheduleForm.value.note || '',
  }
  if (isEditSchedule.value) {
    await api.supplierOrderSchedules.update(scheduleForm.value.id, payload)
  } else {
    await api.supplierOrderSchedules.create(payload)
  }
  showScheduleDialog.value = false
  await fetchSchedules()
}

const removeSchedule = async (id) => {
  if (!confirm('削除しますか？')) return
  await api.supplierOrderSchedules.delete(id)
  await fetchSchedules()
}

onMounted(refreshAll)
</script>

<style scoped>
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.section-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0;
}
.mt {
  margin-top: 24px;
}
.actions-cell {
  white-space: nowrap;
}
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
.ds-btn { margin-left: 8px; padding: 4px 6px; border: 1px solid #94a3b8; border-radius: 4px; background: #f8fafc; color: #475569; cursor: pointer; vertical-align: middle; display: inline-flex; align-items: center; }
.ds-btn:hover { background: #e2e8f0; }
.ds-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 9999; display: flex; align-items: center; justify-content: center; }
.ds-modal { background: #fff; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,.2); max-width: 700px; width: 90%; max-height: 80vh; overflow: auto; }
.ds-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid #e5e7eb; }
.ds-header h3 { margin: 0; font-size: 15px; }
.ds-close { border: none; background: none; font-size: 22px; cursor: pointer; color: #64748b; }
.ds-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ds-table th, .ds-table td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
.ds-table th { background: #f8fafc; font-weight: 600; color: #374151; }
.ds-table td:first-child { white-space: nowrap; font-weight: 500; color: #2563eb; }
.ds-table td:nth-child(2) { font-family: monospace; font-size: 12px; color: #0f172a; }
.ds-section td { background: #f0f4ff; padding: 6px 12px; }
</style>
