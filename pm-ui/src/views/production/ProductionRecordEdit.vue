<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">実績変更</h2>
      <p class="subtitle">セッション単位で実績数量・開始時刻・終了時刻を修正/削除します。</p>
    </div>
    <p v-if="!canView" class="error">この画面を閲覧する権限がありません。</p>
    <p v-else-if="!canEdit" class="loading">閲覧のみ可能です（編集権限がありません）。</p>

    <!-- 新規セッション後入力フォーム -->
    <div v-if="canEdit" class="add-section">
      <button class="btn btn-toggle" @click="showAddForm = !showAddForm">
        {{ showAddForm ? '▲ 新規セッション追加を閉じる' : '▼ 新規セッション追加（登録し忘れ補完）' }}
      </button>
      <div v-if="showAddForm" class="add-form">
        <div class="add-form-row">
          <label>ライン <span class="required">*</span></label>
          <select v-model="newLineId" @change="newProcessId = ''">
            <option value="">-- 選択 --</option>
            <option v-for="line in lines" :key="line.id" :value="String(line.id)">
              {{ line.line_code }} - {{ line.line_name }}
            </option>
          </select>
        </div>
        <div class="add-form-row">
          <label>工程 <span class="required">*</span></label>
          <select v-model="newProcessId">
            <option value="">-- 選択 --</option>
            <option v-for="p in newFilteredProcesses" :key="p.id" :value="String(p.id)">
              {{ p.process_code }} - {{ p.process_name }}
            </option>
          </select>
        </div>
        <div class="add-form-row product-row">
          <label>品番 <span class="required">*</span></label>
          <div class="product-autocomplete">
            <input
              v-model="newProductCode"
              type="text"
              placeholder="品番または品名で検索"
              autocomplete="off"
              @input="onProductInput"
              @keydown.down.prevent="moveSuggestion(1)"
              @keydown.up.prevent="moveSuggestion(-1)"
              @keydown.enter.prevent="confirmSuggestion"
              @keydown.escape="closeSuggestions"
              @blur="onProductBlur"
            />
            <ul v-if="showSuggestions && productSuggestions.length" class="suggestion-list">
              <li
                v-for="(p, i) in productSuggestions"
                :key="p.product_code"
                :class="{ active: i === suggestionIndex }"
                @mousedown.prevent="selectProduct(p)"
              >
                <span class="sug-code">{{ p.product_code }}</span>
                <span class="sug-name">{{ p.product_name }}</span>
              </li>
            </ul>
            <p v-if="!newProcessId && newProductCode.length >= 1" class="sug-empty">工程を先に選択してください</p>
            <p v-else-if="showSuggestions && productSearching" class="sug-loading">読込中...</p>
            <p v-else-if="showSuggestions && newProductCode.length >= 1 && !productSearching && !productSuggestions.length" class="sug-empty">該当なし</p>
          </div>
        </div>
        <div class="add-form-row">
          <label>開始日時 <span class="required">*</span></label>
          <input v-model="newStartedAt" type="datetime-local" />
        </div>
        <div class="add-form-row">
          <label>終了日時 <span class="required">*</span></label>
          <input v-model="newEndedAt" type="datetime-local" />
        </div>
        <div class="add-form-row">
          <label>実績数量 <span class="required">*</span></label>
          <input v-model.number="newProductionQty" type="number" min="0" step="1" class="qty-input" />
        </div>
        <div class="add-form-actions">
          <button class="btn" :disabled="adding" @click="addSession">
            {{ adding ? '登録中...' : '追加登録' }}
          </button>
          <span v-if="addError" class="add-error">{{ addError }}</span>
        </div>
      </div>
    </div>

    <div class="filters" v-if="canView">
      <div class="filter-row">
        <label>レコードID</label>
        <input v-model="sessionId" type="number" min="1" placeholder="例: 12345" />
      </div>
      <div class="filter-row">
        <label>期間</label>
        <input v-model="startDate" type="date" />
        <span>〜</span>
        <input v-model="endDate" type="date" />
      </div>
      <div class="filter-row">
        <label>ライン</label>
        <select v-model="lineId">
          <option value="">-- すべて --</option>
          <option v-for="line in lines" :key="line.id" :value="String(line.id)">
            {{ line.line_code }} - {{ line.line_name }}
          </option>
        </select>
      </div>
      <div class="filter-row">
        <label>工程</label>
        <select v-model="processId">
          <option value="">-- すべて --</option>
          <option v-for="p in filteredProcesses" :key="p.id" :value="String(p.id)">
            {{ p.process_code }} - {{ p.process_name }}
          </option>
        </select>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="loadSessions">検索</button>
      </div>
    </div>

    <div v-if="loading" class="loading">読込中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else class="table-wrap">
      <table class="list-table">
        <thead>
          <tr>
            <th>レコードID</th>
            <th>工程</th>
            <th>品番</th>
            <th>開始時刻</th>
            <th>終了時刻</th>
            <th class="num">実績数量</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in sessions" :key="row.row_key">
            <td>{{ row.id }}</td>
            <td>{{ row.process_code }} / {{ row.process_name }}</td>
            <td>{{ row.product_code || '—' }}</td>
            <td>
              <input v-model="edits[row.row_key].started_at" type="datetime-local" :disabled="!canEdit || row.record_source === 'LASER'" />
            </td>
            <td>
              <input v-model="edits[row.row_key].ended_at" type="datetime-local" :disabled="!canEdit || row.record_source === 'LASER'" />
            </td>
            <td class="num">
              <input
                v-model.number="edits[row.row_key].production_qty"
                type="number"
                min="0"
                step="1"
                class="qty-input"
                :disabled="!canEdit"
              />
            </td>
            <td class="action-cell">
              <button class="btn btn-secondary" :disabled="savingId === row.row_key || !canEdit" @click="saveRow(row)">保存</button>
              <button class="btn btn-danger" :disabled="savingId === row.row_key || !canEdit" @click="deleteRow(row)">削除</button>
            </td>
          </tr>
          <tr v-if="!sessions.length">
            <td colspan="7" class="no-data">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const loading = ref(false)
const error = ref('')
const savingId = ref(null)
const sessions = ref([])
const edits = ref({})

const lines = ref([])
const processes = ref([])

// 新規セッション追加フォーム
const showAddForm = ref(false)
const adding = ref(false)
const addError = ref('')
const newLineId = ref('')
const newProcessId = ref('')
const newProductCode = ref('')
const newStartedAt = ref('')
const newEndedAt = ref('')
const newProductionQty = ref(0)

// 品番オートコンプリート（工程のラインで絞り込み）
const lineProducts = ref([])          // 選択工程のライン製品プール
const productSuggestions = ref([])
const showSuggestions = ref(false)
const productSearching = ref(false)
const suggestionIndex = ref(-1)

// 工程が変わったらそのラインの製品を先読み
watch(() => newProcessId.value, async (processId) => {
  lineProducts.value = []
  newProductCode.value = ''
  showSuggestions.value = false
  if (!processId) return

  const proc = processes.value.find((p) => String(p.id) === String(processId))
  const lineId = proc?.line
  if (!lineId) return

  productSearching.value = true
  try {
    const res = await api.products.getLineFinalCandidates(lineId, processId)
    const group = (res.data || []).find((g) => String(g.line_id) === String(lineId))
    lineProducts.value = group?.products || []
  } catch {
    lineProducts.value = []
  } finally {
    productSearching.value = false
  }
})

const filterProducts = (keyword) => {
  if (!keyword) { productSuggestions.value = []; showSuggestions.value = false; return }
  showSuggestions.value = true
  const kw = keyword.toLowerCase()
  productSuggestions.value = lineProducts.value
    .filter((p) => p.product_code.toLowerCase().includes(kw) || p.product_name.toLowerCase().includes(kw))
    .slice(0, 20)
}

const onProductInput = () => {
  suggestionIndex.value = -1
  filterProducts(newProductCode.value)
}

const selectProduct = (p) => {
  newProductCode.value = p.product_code
  showSuggestions.value = false
  productSuggestions.value = []
}

const moveSuggestion = (dir) => {
  if (!showSuggestions.value || !productSuggestions.value.length) return
  const max = productSuggestions.value.length - 1
  suggestionIndex.value = Math.max(0, Math.min(max, suggestionIndex.value + dir))
}

const confirmSuggestion = () => {
  if (suggestionIndex.value >= 0 && productSuggestions.value[suggestionIndex.value]) {
    selectProduct(productSuggestions.value[suggestionIndex.value])
  }
}

const closeSuggestions = () => { showSuggestions.value = false }
const onProductBlur = () => { setTimeout(() => { showSuggestions.value = false }, 150) }

const today = new Date()
const toISODate = (d) => d.toISOString().slice(0, 10)
const sessionId = ref('')
const startDate = ref(toISODate(new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)))
const endDate = ref(toISODate(new Date(today.getTime() + 24 * 60 * 60 * 1000)))
const lineId = ref('')
const processId = ref('')

const canAccessRecordEdit = (level = 'view') => {
  const user = authState.user
  if (!user) return false
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === 'production.record_edit')) {
    return hasPermission(user, 'production.record_edit', level)
  }
  return hasPermission(user, 'production', level)
}

const canView = computed(() => canAccessRecordEdit('view'))
const canEdit = computed(() => canAccessRecordEdit('edit'))

const filteredProcesses = computed(() => {
  if (!lineId.value) return processes.value
  return processes.value.filter((p) => String(p.line) === String(lineId.value))
})

const newFilteredProcesses = computed(() => {
  if (!newLineId.value) return processes.value
  return processes.value.filter((p) => String(p.line) === String(newLineId.value))
})

const toLocalDateTimeInput = (value) => {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const loadMasters = async () => {
  try {
    const [lineRes, processRes] = await Promise.all([
      api.lines.getProductionLines(),
      api.processes.getProcesses({ is_active: true }),
    ])
    lines.value = lineRes.data?.results || lineRes.data || []
    processes.value = processRes.data?.results || processRes.data || []
  } catch (e) {
    console.error('マスタ読込失敗:', e)
  }
}

const buildEditMap = (rows) => {
  const map = {}
  rows.forEach((row) => {
    map[row.row_key] = {
      started_at: toLocalDateTimeInput(row.started_at),
      ended_at: toLocalDateTimeInput(row.ended_at),
      production_qty: Number(row.production_qty || 0),
    }
  })
  edits.value = map
}

const loadSessions = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = {
      limit: 1000,
      start_date: startDate.value,
      end_date: endDate.value,
    }
    if (lineId.value) params.line_id = lineId.value
    if (processId.value) params.process_id = processId.value
    const laserParams = {
      page_size: 1000,
      work_date__gte: startDate.value,
      work_date__lte: endDate.value,
      ordering: '-work_date,-created_at',
    }
    const [processRes, brakeRes, laserRes] = await Promise.all([
      api.processRealtime.getSessions(params),
      api.brakeLineActuals.getSessions(params),
      api.laserActuals.getLaserActuals(laserParams),
    ])
    const processRows = (Array.isArray(processRes.data) ? processRes.data : []).map((row) => ({
      ...row,
      record_source: 'PROCESS',
      row_key: `PROCESS-${row.id}`,
    }))
    const brakeRows = (Array.isArray(brakeRes.data) ? brakeRes.data : []).map((row) => ({
      ...row,
      record_source: 'BRAKE',
      row_key: `BRAKE-${row.id}-${row.started_at || ''}`,
    }))
    const laserRaw = Array.isArray(laserRes.data?.results) ? laserRes.data.results : (Array.isArray(laserRes.data) ? laserRes.data : [])
    const laserRows = laserRaw.flatMap((row) => {
      const details = Array.isArray(row?.details) ? row.details : []
      const componentDetails = details.filter((detail) => String(detail?.detail_type || '').toUpperCase() === 'COMPONENT')
      const base = {
        id: row?.id,
        started_at: row?.created_at || null,
        ended_at: row?.created_at || null,
        process_code: row?.equipment_process_code || row?.equipment_code || '',
        process_name: row?.equipment_name || '',
        product_code: '',
        production_qty: 0,
        record_source: 'LASER',
        laser_operator_action: row?.operator_action || 'END',
        laser_units_per_shot: 0,
        laser_shot_count: Number(row?.shot_count || 0),
        equipment_process_id: row?.equipment_process_id ?? null,
      }
      if (!componentDetails.length) {
        return [{ ...base, row_key: `LASER-${row?.id}-none` }]
      }
      return componentDetails.map((detail, idx) => ({
        ...base,
        product_code: detail?.product_code || '',
        production_qty: Number(detail?.total_qty || 0),
        laser_units_per_shot: Number(detail?.units_per_shot || 0),
        detail_id: detail?.id ?? null,
        row_key: `LASER-${row?.id}-${idx}`,
      }))
    })
    const selectedLineProcessIds = lineId.value
      ? new Set(
        processes.value
          .filter((p) => String(p.line) === String(lineId.value))
          .map((p) => String(p.id)),
      )
      : null
    const filteredLaserRows = laserRows.filter((row) => {
      if (selectedLineProcessIds && row.equipment_process_id != null && !selectedLineProcessIds.has(String(row.equipment_process_id))) {
        return false
      }
      if (processId.value && row.equipment_process_id != null && String(row.equipment_process_id) !== String(processId.value)) {
        return false
      }
      return true
    })
    const rows = [...processRows, ...brakeRows, ...filteredLaserRows]
      .sort((a, b) => {
        const ta = a.started_at || ''
        const tb = b.started_at || ''
        return ta < tb ? 1 : ta > tb ? -1 : 0
      })
    const filtered = sessionId.value
      ? rows.filter((row) => String(row.id) === String(sessionId.value))
      : rows
    sessions.value = filtered
    buildEditMap(filtered)
  } catch (e) {
    console.error('セッション読込失敗:', e)
    error.value = '実績の取得に失敗しました。'
    sessions.value = []
    edits.value = {}
  } finally {
    loading.value = false
  }
}

const saveRow = async (row) => {
  if (!canEdit.value) return
  const id = row.id
  const edit = edits.value[row.row_key]
  if (!edit) return
  if (!window.confirm(`レコードID ${id} を更新します。よろしいですか？`)) return

  savingId.value = row.row_key
  try {
    const payload = {
      started_at: edit.started_at || null,
      ended_at: edit.ended_at || null,
      production_qty: Number(edit.production_qty || 0),
    }
    if (String(row?.record_source || '').toUpperCase() === 'LASER') {
      if (!row.detail_id) {
        alert('この行は明細IDが取得できないため更新できません。')
        return
      }
      await api.laserActuals.patchLaserActualDetail(row.detail_id, {
        total_qty: Number(edit.production_qty || 0),
      })
    } else if (String(row?.record_source || '').toUpperCase() === 'BRAKE') {
      await api.brakeLineActuals.updateSession(id, payload)
    } else {
      await api.processRealtime.updateSession(id, payload)
    }
    await loadSessions()
    alert('更新しました。LineBacklog.actual_qty も差分反映済みです。')
  } catch (e) {
    console.error('更新失敗:', e)
    alert('更新に失敗しました。入力形式を確認してください。')
  } finally {
    savingId.value = null
  }
}

const deleteRow = async (row) => {
  if (!canEdit.value) return
  const id = row.id
  if (!window.confirm(`レコードID ${id} を削除します。よろしいですか？`)) return
  savingId.value = row.row_key
  try {
    if (String(row?.record_source || '').toUpperCase() === 'LASER') {
      await api.laserActuals.deleteLaserActual(id)
    } else if (String(row?.record_source || '').toUpperCase() === 'BRAKE') {
      await api.brakeLineActuals.deleteSession(id)
    } else {
      await api.processRealtime.deleteSession(id)
    }
    await loadSessions()
    alert('削除しました。LineBacklog.actual_qty も減算反映済みです。')
  } catch (e) {
    console.error('削除失敗:', e)
    alert('削除に失敗しました。')
  } finally {
    savingId.value = null
  }
}

const addSession = async () => {
  if (!canEdit.value) return
  addError.value = ''
  if (!newProcessId.value) { addError.value = '工程を選択してください。'; return }
  if (!newProductCode.value.trim()) { addError.value = '品番を入力してください。'; return }
  if (!newStartedAt.value) { addError.value = '開始日時を入力してください。'; return }
  if (!newEndedAt.value) { addError.value = '終了日時を入力してください。'; return }
  if (newProductionQty.value < 0) { addError.value = '実績数量は0以上で入力してください。'; return }
  if (!window.confirm('後入力セッションを登録し、LineBacklog.actual_qty に加算します。よろしいですか？')) return

  adding.value = true
  try {
    await api.processRealtime.createSession({
      process_id: Number(newProcessId.value),
      product_code: newProductCode.value.trim(),
      started_at: newStartedAt.value,
      ended_at: newEndedAt.value,
      production_qty: newProductionQty.value,
    })
    // フォームリセット
    newProcessId.value = ''
    newProductCode.value = ''
    newStartedAt.value = ''
    newEndedAt.value = ''
    newProductionQty.value = 0
    lineProducts.value = []
    showAddForm.value = false
    await loadSessions()
    alert('追加登録しました。LineBacklog.actual_qty に加算反映済みです。')
  } catch (e) {
    const msg = e.response?.data?.detail || '登録に失敗しました。入力内容を確認してください。'
    addError.value = msg
    console.error('追加登録失敗:', e)
  } finally {
    adding.value = false
  }
}

onMounted(async () => {
  if (!canView.value) return
  await loadMasters()
  await loadSessions()
})
</script>

<style scoped>
.page {
  padding: 16px;
}
.page-header {
  margin-bottom: 12px;
}
.page-title {
  margin: 0;
  font-size: 22px;
}
.subtitle {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
}
.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 8px 12px;
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-row label {
  min-width: 70px;
  font-weight: 700;
  font-size: 13px;
}
.filter-row input,
.filter-row select {
  flex: 1;
  min-width: 0;
  padding: 7px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
}
.actions {
  display: flex;
  align-items: center;
}
.btn {
  padding: 8px 12px;
  border: 1px solid #1d4ed8;
  background: #1d4ed8;
  color: #fff;
  border-radius: 6px;
  font-weight: 700;
  cursor: pointer;
}
.btn-secondary {
  border-color: #64748b;
  background: #64748b;
}
.btn-danger {
  border-color: #b91c1c;
  background: #b91c1c;
}
.loading,
.error {
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 10px;
}
.loading {
  background: #eff6ff;
  color: #1e3a8a;
}
.error {
  background: #fee2e2;
  color: #991b1b;
}
.table-wrap {
  overflow: auto;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}
.list-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 980px;
}
.list-table th,
.list-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 13px;
  text-align: left;
  vertical-align: middle;
}
.list-table thead th {
  position: sticky;
  top: 0;
  background: #f8fafc;
  z-index: 1;
}
.num {
  text-align: right !important;
}
.qty-input {
  width: 100px;
  text-align: right;
}
.action-cell {
  display: flex;
  gap: 8px;
}
.no-data {
  text-align: center !important;
  color: #64748b;
  padding: 20px !important;
}
.add-section {
  margin-bottom: 12px;
}
.btn-toggle {
  border-color: #0f766e;
  background: #0f766e;
  margin-bottom: 8px;
}
.add-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 8px 12px;
  padding: 12px;
  border: 1px solid #99f6e4;
  border-radius: 10px;
  background: #f0fdfa;
}
.add-form-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.add-form-row label {
  min-width: 80px;
  font-weight: 700;
  font-size: 13px;
}
.add-form-row input,
.add-form-row select {
  flex: 1;
  min-width: 0;
  padding: 7px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
}
.add-form-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  grid-column: 1 / -1;
}
.add-error {
  color: #991b1b;
  font-size: 13px;
}
.required {
  color: #dc2626;
}
.product-row {
  align-items: flex-start;
}
.product-autocomplete {
  flex: 1;
  min-width: 0;
  position: relative;
}
.product-autocomplete input {
  width: 100%;
  box-sizing: border-box;
}
.suggestion-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  margin: 2px 0 0;
  padding: 0;
  list-style: none;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  max-height: 220px;
  overflow-y: auto;
}
.suggestion-list li {
  display: flex;
  gap: 8px;
  padding: 7px 10px;
  cursor: pointer;
  font-size: 13px;
  border-bottom: 1px solid #f1f5f9;
}
.suggestion-list li:last-child {
  border-bottom: none;
}
.suggestion-list li:hover,
.suggestion-list li.active {
  background: #eff6ff;
}
.sug-code {
  font-weight: 700;
  white-space: nowrap;
  color: #1e40af;
}
.sug-name {
  color: #475569;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sug-loading,
.sug-empty {
  margin: 0;
  padding: 8px 10px;
  font-size: 12px;
  color: #64748b;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
}
</style>
