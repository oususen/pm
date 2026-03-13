<template>
  <div class="laser-actual-page">
    <div class="page-header">
      <h2>レーザー実績入力</h2>
      <p class="page-note">タブレット向け画面（既存の工程作業入力とは別UI）</p>
    </div>

    <div class="tab-bar">
      <button
        type="button"
        class="tab-item"
        :class="{ active: activeTab === 'entry' }"
        @click="activeTab = 'entry'"
      >
        実績入力
      </button>
      <button
        type="button"
        class="tab-item"
        :class="{ active: activeTab === 'list' }"
        @click="activeTab = 'list'"
      >
        一覧
      </button>
    </div>

    <section v-show="activeTab === 'entry'" class="panel form-panel">
        <div class="panel-head">
          <h3>{{ isEditMode ? 'レーザー実績編集' : 'レーザー実績登録' }}</h3>
        </div>

        <div v-if="formMessage" class="message" :class="`is-${formMessageType}`">
          {{ formMessage }}
        </div>

        <div class="form-grid two-col">
          <div class="field">
            <label class="required">作業日</label>
            <input v-model="form.work_date" type="date" />
          </div>
          <div class="field">
            <label class="required">使用設備</label>
            <select v-model="form.equipment">
              <option value="">-- 選択 --</option>
              <option v-for="equipment in equipments" :key="equipment.id" :value="String(equipment.id)">
                {{ equipment.equipment_code }} - {{ equipment.equipment_name }}
              </option>
            </select>
          </div>
        </div>

        <div class="field">
          <label class="required">パターン番号（検索選択）</label>
          <input
            v-model.trim="patternKeyword"
            type="text"
            placeholder="パターン番号で絞り込み"
          />
          <select v-model="form.pattern" class="pattern-select">
            <option value="">-- パターン選択 --</option>
            <option v-for="pattern in filteredPatterns" :key="pattern.id" :value="String(pattern.id)">
              {{ pattern.pattern_no }} / 材料:{{ pattern.material_code || '-' }} / 設備:{{ pattern.equipment_code || '-' }}
            </option>
          </select>
        </div>

        <div class="form-grid two-col">
          <div class="field">
            <label class="required">回数</label>
            <input
              v-model.number="form.shot_count"
              type="number"
              min="1"
              step="1"
              inputmode="numeric"
              placeholder="1以上の整数"
            />
          </div>
          <div class="field">
            <label>備考</label>
            <input
              v-model.trim="form.remarks"
              type="text"
              placeholder="任意"
            />
          </div>
        </div>

        <div v-if="selectedPattern" class="snapshot">
          <div class="snapshot-summary">
            <div><span class="label">使用材料</span><span>{{ selectedPattern.material_code || '-' }}</span></div>
            <div><span class="label">1回あたり加工時間</span><span>{{ formatNumber(processTimePerShot, 1) }} 分</span></div>
            <div><span class="label">総加工時間</span><span>{{ formatNumber(totalProcessTime, 1) }} 分</span></div>
          </div>

          <div class="snapshot-block">
            <h4>構成部品一覧</h4>
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>品番</th>
                    <th>取り数</th>
                    <th>実績数</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in componentRows" :key="row.product_id || row.product_code">
                    <td>{{ row.product_code || '-' }}</td>
                    <td class="num">{{ formatNumber(row.units_per_shot, 0) }}</td>
                    <td class="num">{{ formatNumber(row.total_qty, 0) }}</td>
                  </tr>
                  <tr v-if="!componentRows.length">
                    <td colspan="3">構成部品はありません。</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="snapshot-block">
            <h4>完成品一覧</h4>
            <div class="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>完成品番号</th>
                    <th>完成品取り数</th>
                    <th>完成品実績換算数</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in finishedRows" :key="row.product_id || row.product_code">
                    <td>{{ row.product_code || '-' }}</td>
                    <td class="num">{{ formatNumber(row.units_per_shot, 1) }}</td>
                    <td class="num">{{ formatNumber(row.total_qty, 1) }}</td>
                  </tr>
                  <tr v-if="!finishedRows.length">
                    <td colspan="3">完成品はありません。</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="actions">
          <button class="btn primary" :disabled="!canSave || formSubmitting" @click="saveActual">
            {{ formSubmitting ? '処理中...' : isEditMode ? '更新' : '保存' }}
          </button>
          <button class="btn" :disabled="formSubmitting" @click="resetForm">クリア</button>
          <button
            v-if="isEditMode"
            class="btn danger"
            :disabled="formSubmitting"
            @click="deleteActual"
          >
            削除
          </button>
        </div>
    </section>

    <section v-show="activeTab === 'list'" class="panel list-panel">
        <div class="panel-head">
          <h3>一覧 / 検索</h3>
        </div>

        <div v-if="listMessage" class="message" :class="`is-${listMessageType}`">
          {{ listMessage }}
        </div>

        <div class="search-grid">
          <div class="field">
            <label>日付From</label>
            <input v-model="filters.work_date_from" type="date" />
          </div>
          <div class="field">
            <label>日付To</label>
            <input v-model="filters.work_date_to" type="date" />
          </div>
          <div class="field">
            <label>設備</label>
            <select v-model="filters.equipment">
              <option value="">すべて</option>
              <option v-for="equipment in equipments" :key="`filter-${equipment.id}`" :value="String(equipment.id)">
                {{ equipment.equipment_code }} - {{ equipment.equipment_name }}
              </option>
            </select>
          </div>
          <div class="field">
            <label>パターン番号</label>
            <input
              v-model.trim="filters.pattern_no"
              type="text"
              placeholder="部分一致"
            />
          </div>
        </div>

        <div class="search-actions">
          <button class="btn primary" :disabled="listLoading" @click="loadActuals">
            {{ listLoading ? '検索中...' : '検索' }}
          </button>
          <button class="btn" :disabled="listLoading" @click="resetFilters">条件クリア</button>
        </div>

        <div class="result-meta">{{ actuals.length }} 件</div>

        <div class="table-scroll list-table">
          <table>
            <thead>
              <tr>
                <th>日付</th>
                <th>設備</th>
                <th>パターン番号</th>
                <th class="num">回数</th>
                <th class="num">総加工時間</th>
                <th>登録者</th>
                <th>登録日時</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in actuals"
                :key="row.id"
                :class="{ active: String(form.id || '') === String(row.id) }"
                @click="setFormFromRecord(row)"
              >
                <td>{{ row.work_date }}</td>
                <td>{{ row.equipment_code || '-' }}</td>
                <td>{{ row.pattern_no || '-' }}</td>
                <td class="num">{{ formatNumber(row.shot_count, 0) }}</td>
                <td class="num">{{ formatNumber(row.total_process_time, 1) }}</td>
                <td>{{ row.created_by_name || '-' }}</td>
                <td>{{ formatDateTime(row.created_at) }}</td>
              </tr>
              <tr v-if="!actuals.length">
                <td colspan="7">データがありません。</td>
              </tr>
            </tbody>
          </table>
        </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { getLocaleCode } from '@/i18n'

const localeCode = computed(() => getLocaleCode())

const roundTo = (value, scale) => {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return 0
  const factor = Math.pow(10, scale)
  return Math.round(num * factor) / factor
}

const formatNumber = (value, fractionDigits = 1) => {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return '0'
  return num.toLocaleString(localeCode.value, {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits,
  })
}

const formatDateTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return `${d.toLocaleDateString(localeCode.value)} ${d.toLocaleTimeString(localeCode.value, { hour: '2-digit', minute: '2-digit' })}`
}

const todayYmd = () => {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const shiftDateYmd = (offsetDays) => {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const createEmptyForm = () => ({
  id: null,
  work_date: todayYmd(),
  equipment: '',
  pattern: '',
  shot_count: 1,
  remarks: '',
})

const createDefaultFilters = () => ({
  work_date_from: shiftDateYmd(-14),
  work_date_to: todayYmd(),
  equipment: '',
  pattern_no: '',
})

const normalizeList = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const form = ref(createEmptyForm())
const filters = ref(createDefaultFilters())
const equipments = ref([])
const patterns = ref([])
const actuals = ref([])
const patternKeyword = ref('')
const activeTab = ref('entry')

const formSubmitting = ref(false)
const listLoading = ref(false)

const formMessage = ref('')
const formMessageType = ref('info')
const listMessage = ref('')
const listMessageType = ref('info')

const setFormMessage = (message, type = 'info') => {
  formMessage.value = message
  formMessageType.value = type
}

const setListMessage = (message, type = 'info') => {
  listMessage.value = message
  listMessageType.value = type
}

const clearMessages = () => {
  formMessage.value = ''
  listMessage.value = ''
}

const filteredPatterns = computed(() => {
  const source = Array.isArray(patterns.value) ? patterns.value : []
  const keyword = String(patternKeyword.value || '').trim().toLowerCase()
  if (!keyword) return source
  return source.filter((pattern) => String(pattern.pattern_no || '').toLowerCase().includes(keyword))
})

const selectedPattern = computed(() => {
  if (!form.value.pattern) return null
  return (
    (Array.isArray(patterns.value) ? patterns.value : []).find(
      (pattern) => String(pattern.id) === String(form.value.pattern)
    ) || null
  )
})

const isValidShotCount = computed(() => {
  const shots = Number(form.value.shot_count)
  return Number.isInteger(shots) && shots >= 1
})

const processTimePerShot = computed(() => {
  if (!selectedPattern.value) return 0
  return roundTo(selectedPattern.value.process_time_min, 1)
})

const totalProcessTime = computed(() => {
  if (!selectedPattern.value || !isValidShotCount.value) return 0
  return roundTo(processTimePerShot.value * Number(form.value.shot_count), 1)
})

const componentRows = computed(() => {
  if (!selectedPattern.value) return []
  const shots = isValidShotCount.value ? Number(form.value.shot_count) : 0
  const rows = Array.isArray(selectedPattern.value.component_items)
    ? selectedPattern.value.component_items
    : []
  return rows.map((row) => {
    const units = Number(row.take_qty || 0)
    return {
      product_id: row.component_product,
      product_code: row.component_product_code || '',
      units_per_shot: units,
      total_qty: roundTo(units * shots, 0),
    }
  })
})

const finishedRows = computed(() => {
  if (!selectedPattern.value) return []
  const shots = isValidShotCount.value ? Number(form.value.shot_count) : 0
  const rows = Array.isArray(selectedPattern.value.finished_items)
    ? selectedPattern.value.finished_items
    : []
  return rows.map((row) => {
    const units = Number(row.units_per_shot || 0)
    return {
      product_id: row.finished_product,
      product_code: row.finished_product_code || '',
      units_per_shot: roundTo(units, 1),
      total_qty: roundTo(units * shots, 1),
    }
  })
})

const isEditMode = computed(() => !!form.value.id)

const canSave = computed(() => {
  if (!form.value.work_date) return false
  if (!form.value.equipment) return false
  if (!form.value.pattern) return false
  if (!isValidShotCount.value) return false
  return true
})

const extractErrorMessage = (error, fallback) => {
  const payload = error?.response?.data
  if (typeof payload === 'string' && payload.trim()) return payload.trim()
  if (payload?.detail) return String(payload.detail)
  if (payload && typeof payload === 'object') {
    const firstKey = Object.keys(payload)[0]
    if (firstKey) {
      const val = payload[firstKey]
      if (Array.isArray(val) && val.length) {
        return `${firstKey}: ${val.join(', ')}`
      }
      if (typeof val === 'string' && val) {
        return `${firstKey}: ${val}`
      }
    }
  }
  return fallback
}

const loadEquipments = async () => {
  try {
    const res = await api.equipments.getEquipments({ is_active: true, page_size: 500 })
    equipments.value = normalizeList(res.data)
  } catch (error) {
    equipments.value = []
    setListMessage(extractErrorMessage(error, '設備一覧の取得に失敗しました。'), 'error')
  }
}

const loadPatterns = async () => {
  try {
    const res = await api.laserPatterns.getLaserPatterns({ page_size: 500 })
    patterns.value = normalizeList(res.data)
  } catch (error) {
    patterns.value = []
    setListMessage(extractErrorMessage(error, 'パターン一覧の取得に失敗しました。'), 'error')
  }
}

const buildSearchParams = () => {
  const params = {}
  if (filters.value.work_date_from) params.work_date__gte = filters.value.work_date_from
  if (filters.value.work_date_to) params.work_date__lte = filters.value.work_date_to
  if (filters.value.equipment) params.equipment = filters.value.equipment
  if (filters.value.pattern_no) params.pattern_no = filters.value.pattern_no
  return params
}

const loadActuals = async () => {
  listLoading.value = true
  setListMessage('', 'info')
  try {
    const res = await api.laserActuals.getLaserActuals(buildSearchParams())
    actuals.value = normalizeList(res.data)
  } catch (error) {
    actuals.value = []
    setListMessage(extractErrorMessage(error, '一覧の取得に失敗しました。'), 'error')
  } finally {
    listLoading.value = false
  }
}

const setFormFromRecord = (row) => {
  form.value = {
    id: row.id,
    work_date: row.work_date || todayYmd(),
    equipment: row.equipment ? String(row.equipment) : '',
    pattern: row.pattern ? String(row.pattern) : '',
    shot_count: row.shot_count ?? 1,
    remarks: row.remarks || '',
  }
  patternKeyword.value = row.pattern_no || ''
  activeTab.value = 'entry'
  setFormMessage('', 'info')
}

const resetForm = () => {
  form.value = createEmptyForm()
  patternKeyword.value = ''
  setFormMessage('', 'info')
}

const resetFilters = async () => {
  filters.value = createDefaultFilters()
  await loadActuals()
}

const saveActual = async () => {
  if (!canSave.value || formSubmitting.value) return
  formSubmitting.value = true
  setFormMessage('', 'info')

  const payload = {
    work_date: form.value.work_date,
    equipment: Number(form.value.equipment),
    pattern: Number(form.value.pattern),
    shot_count: Number(form.value.shot_count),
    remarks: form.value.remarks || '',
  }

  try {
    let res
    if (isEditMode.value) {
      res = await api.laserActuals.updateLaserActual(form.value.id, payload)
    } else {
      res = await api.laserActuals.createLaserActual(payload)
    }
    const saved = res?.data || null
    setFormMessage(isEditMode.value ? '更新しました。' : '保存しました。', 'success')
    if (saved?.id) {
      setFormFromRecord(saved)
    } else if (!isEditMode.value) {
      resetForm()
    }
    await loadActuals()
  } catch (error) {
    setFormMessage(extractErrorMessage(error, '保存に失敗しました。入力内容を確認してください。'), 'error')
  } finally {
    formSubmitting.value = false
  }
}

const deleteActual = async () => {
  if (!isEditMode.value || formSubmitting.value) return
  const ok = window.confirm('このレーザー実績を削除します。よろしいですか？')
  if (!ok) return

  formSubmitting.value = true
  setFormMessage('', 'info')
  try {
    await api.laserActuals.deleteLaserActual(form.value.id)
    setFormMessage('削除しました。', 'success')
    resetForm()
    await loadActuals()
  } catch (error) {
    setFormMessage(extractErrorMessage(error, '削除に失敗しました。'), 'error')
  } finally {
    formSubmitting.value = false
  }
}

watch(
  () => form.value.pattern,
  (patternId) => {
    if (!patternId) return
    const selected = patterns.value.find((pattern) => String(pattern.id) === String(patternId))
    if (selected) {
      patternKeyword.value = selected.pattern_no || ''
      if (!form.value.equipment && selected.equipment) {
        form.value.equipment = String(selected.equipment)
      }
    }
  }
)

onMounted(async () => {
  clearMessages()
  await Promise.all([loadEquipments(), loadPatterns()])
  await loadActuals()
})
</script>

<style scoped>
.laser-actual-page {
  padding: 14px;
  display: grid;
  gap: 12px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #0f172a;
}

.page-note {
  margin: 4px 0 0;
  color: #475569;
  font-size: 13px;
}

.tab-bar {
  display: flex;
  gap: 8px;
}

.tab-item {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #1e293b;
  padding: 9px 14px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.tab-item.active {
  background: #2563eb;
  border-color: #1d4ed8;
  color: #ffffff;
}

.panel {
  border: 1px solid #d9e2ec;
  border-radius: 12px;
  background: #ffffff;
  padding: 12px;
  display: grid;
  gap: 10px;
  align-content: start;
}

.panel-head h3 {
  margin: 0;
  font-size: 18px;
}

.message {
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
}

.message.is-success {
  background: #dcfce7;
  color: #166534;
}

.message.is-error {
  background: #fee2e2;
  color: #991b1b;
}

.message.is-info {
  background: #e2e8f0;
  color: #334155;
}

.form-grid {
  display: grid;
  gap: 10px;
}

.form-grid.two-col {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
  display: grid;
  gap: 6px;
}

label {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.required::after {
  content: ' *';
  color: #dc2626;
}

input,
select {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 9px 10px;
  font-size: 14px;
  box-sizing: border-box;
}

input:focus,
select:focus {
  outline: none;
  border-color: #2563eb;
}

.pattern-select {
  min-height: 40px;
}

.snapshot {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fbff;
  padding: 10px;
  display: grid;
  gap: 10px;
}

.snapshot-summary {
  display: grid;
  gap: 6px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.snapshot-summary .label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 3px;
}

.snapshot-block h4 {
  margin: 0 0 6px;
  font-size: 14px;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #1e293b;
  padding: 8px 14px;
  font-size: 14px;
  cursor: pointer;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.btn.primary {
  background: #2563eb;
  border-color: #1d4ed8;
  color: #ffffff;
  font-weight: 700;
}

.btn.danger {
  background: #dc2626;
  border-color: #b91c1c;
  color: #ffffff;
  font-weight: 700;
}

.search-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.search-actions {
  display: flex;
  gap: 8px;
}

.result-meta {
  font-size: 12px;
  color: #475569;
}

.table-scroll {
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  border-bottom: 1px solid #e2e8f0;
  padding: 7px 8px;
  text-align: left;
  white-space: nowrap;
}

th {
  background: #f8fafc;
  position: sticky;
  top: 0;
  z-index: 1;
}

td.num,
th.num {
  text-align: right;
}

.list-table table tbody tr {
  cursor: pointer;
}

.list-table table tbody tr:hover {
  background: #f1f5f9;
}

.list-table table tbody tr.active {
  background: #dbeafe;
}

@media (max-width: 760px) {
  .laser-actual-page {
    padding: 8px;
  }

  .tab-bar {
    width: 100%;
  }

  .tab-item {
    flex: 1;
  }

  .form-grid.two-col,
  .search-grid,
  .snapshot-summary {
    grid-template-columns: 1fr;
  }
}
</style>
