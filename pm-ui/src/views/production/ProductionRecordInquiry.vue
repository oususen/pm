<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">生産実績照会</h2>
      <p class="subtitle">開始〜終了をセッション単位で照会します（中断区間も表示）。</p>
    </div>

    <div class="filters">
      <div class="filter-row filter-row-period">
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
      <div class="filter-row">
        <label>品番</label>
        <input v-model="productCode" type="text" placeholder="部分一致" />
      </div>
      <div class="filter-row">
        <label>区分</label>
        <select v-model="sessionType">
          <option value="">-- すべて --</option>
          <option value="WORK">作業セッション</option>
          <option value="PAUSE">中断セッション</option>
          <option value="CANCEL">中止セッション</option>
        </select>
      </div>
      <div class="filter-row">
        <label>状態</label>
        <select v-model="status">
          <option value="">-- すべて --</option>
          <option value="OPEN">進行中</option>
          <option value="CLOSED">終了</option>
        </select>
      </div>
      <div class="filter-row">
        <label>不整合</label>
        <select v-model="hasIssue">
          <option value="">-- すべて --</option>
          <option value="true">あり</option>
          <option value="false">なし</option>
        </select>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="loadSessions">検索</button>
        <button class="btn btn-secondary" :disabled="loading" @click="resetFilters">リセット</button>
      </div>
      <div class="export-actions">
        <button class="btn btn-secondary" :disabled="loading || !sessions.length" @click="exportCsv">CSV出力</button>
        <button class="btn btn-secondary" :disabled="loading || !sessions.length" @click="exportExcel">Excel出力</button>
        <button class="btn btn-secondary" :disabled="loading || !sessions.length" @click="exportExcel2">Excel出力2</button>
        <button class="btn btn-secondary" :disabled="loading || !sessions.length" @click="exportPdf">印刷(PDF)</button>
      </div>
    </div>

    <div v-if="loading" class="loading">読込中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else>
      <div class="summary-block">
        <div class="summary-line">
          <div class="summary-line-head">中断除く加工情報</div>
          <div class="summary-line-item">
            <span class="summary-label">期間合計実績</span>
            <span class="summary-value summary-value--md">{{ formatNumber(totalProductionQty) }}</span>
          </div>
          <div class="summary-line-item">
            <span class="summary-label">期間合計作業時間（休憩除外）</span>
            <span class="summary-value summary-value--md">{{ formatDuration(totalEffectiveWorkSeconds, true) }}</span>
          </div>
          <div class="summary-line-item">
            <span class="summary-label">期間出来高（台/h）</span>
            <span class="summary-value summary-value--md">{{ formatProductivity(totalProductivityPerHour) }}</span>
          </div>
        </div>
        <div class="summary-line">
          <div class="summary-line-head">中断含む加工情報</div>
          <div class="summary-line-item">
            <span class="summary-label">期間合計実績</span>
            <span class="summary-value summary-value--md">{{ formatNumber(totalProductionQty) }}</span>
          </div>
          <div class="summary-line-item">
            <span class="summary-label">期間合計作業時間（中断含む）</span>
            <span class="summary-value summary-value--md">{{ formatDuration(totalDurationIncludingPauseSeconds, true) }}</span>
            <span class="summary-meta">正味加工時間 {{ formatDuration(totalEffectiveWorkSeconds, true) }}</span>
            <span class="summary-meta">中断時間 {{ formatDuration(totalPauseSeconds, true) }}</span>
          </div>
          <div class="summary-line-item">
            <span class="summary-label">期間出来高（台/h）</span>
            <span class="summary-value summary-value--md">{{ formatProductivity(totalProductivityIncludingPausePerHour) }}</span>
          </div>
        </div>
        <div class="summary-formula">
          計算式（中断除く）: 出来高 = 実績台数 / 作業時間（休憩除外）
        </div>
        <div class="summary-formula">
          計算式（中断含む）: 出来高 = 実績台数 / 作業時間（中断含む）
        </div>
      </div>

      <div class="table-wrap">
        <table class="list-table">
        <thead>
          <tr>
            <th>レコードID</th>
            <th>開始</th>
            <th>終了</th>
            <th>区分</th>
            <th>開始操作</th>
            <th>終了操作</th>
            <th>工程</th>
            <th>品番</th>
            <th>品名</th>
            <th>作業者</th>
            <th class="num">継続時間</th>
            <th class="num">作業時間(休憩除外)</th>
            <th class="num">生産数量</th>
            <th class="num">実績数量</th>
            <th class="num">出来高(台/h)</th>
            <th class="num">出来高</th>
            <th>不整合</th>
          </tr>
        </thead>
          <tbody>
            <tr
              v-for="(row, rowIndex) in sessions"
              :key="`${row.id}-${row.product || row.product_code || 'none'}-${rowIndex}`"
              :class="{ 'row-pause': row.session_type === 'PAUSE' }"
            >
              <td>{{ row.id ?? '—' }}</td>
              <td>{{ formatDateTime(row.started_at) }}</td>
              <td>{{ row.ended_at ? formatDateTime(row.ended_at) : '—' }}</td>
              <td>
                <span class="badge" :class="getSessionTypeClass(row)">
                  {{ getSessionTypeLabel(row) }}
                </span>
              </td>
              <td>{{ row.start_action || '—' }}</td>
              <td>{{ row.end_action || '—' }}</td>
              <td>{{ row.process_code }} / {{ row.process_name }}</td>
              <td>{{ row.product_code || '—' }}</td>
              <td>{{ row.product_name || '' }}</td>
              <td>{{ row.operator_name || '—' }}</td>
              <td class="num">{{ formatDuration(row.duration_seconds, row.ended_at) }}</td>
              <td class="num">{{ formatDuration(row.effective_work_seconds, true) }}</td>
              <td class="num">{{ formatNumber(row.production_qty ?? '') }}</td>
              <td class="num">{{ formatProductionQty(row) }}</td>
              <td class="num">{{ formatProductivity(row.productivity_per_hour, row) }}</td>
              <td class="num">{{ formatProductivity(calcDurationBasedProductivity(row), row) }}</td>
              <td>
                <span v-if="row.issue_count > 0" class="issue">
                  {{ (row.issue_flags || []).join(', ') }}
                </span>
                <span v-else>—</span>
              </td>
            </tr>
            <tr v-if="!sessions.length">
              <td colspan="17" class="no-data">データがありません</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { exportProductionSummaryExcel } from '@/utils/productionRecordExport2'
import {
  exportCsv as _exportCsv,
  exportExcel as _exportExcel,
  exportPdf as _exportPdf,
} from '@/utils/productionRecordExport'

const loading = ref(false)
const error = ref('')
const sessions = ref([])

const lines = ref([])
const processes = ref([])

const today = new Date()
const toISODate = (d) => d.toISOString().slice(0, 10)
const startDate = ref(toISODate(new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)))
const endDate = ref(toISODate(new Date(today.getTime() + 24 * 60 * 60 * 1000)))
const lineId = ref('')
const processId = ref('')
const productCode = ref('')
const sessionType = ref('')
const status = ref('')
const hasIssue = ref('')

const filteredProcesses = computed(() => {
  if (!lineId.value) return processes.value
  return processes.value.filter((p) => String(p.line) === String(lineId.value))
})

const isCountableProductionRow = (row) => {
  if (!row || row.session_type !== 'WORK') return false
  const endAction = String(row.end_action || '').toUpperCase()
  return ['END', 'PAUSE'].includes(endAction)
}

const isCanceledSession = (row) => {
  if (!row) return false
  return String(row.end_action || '').toUpperCase() === 'CANCEL'
}

const getSessionTypeLabel = (row) => {
  if (isCanceledSession(row)) return '中止'
  return row.session_type === 'PAUSE' ? '中断' : '作業'
}

const getSessionTypeClass = (row) => {
  if (isCanceledSession(row)) return 'badge-cancel'
  return row.session_type === 'PAUSE' ? 'badge-pause' : 'badge-work'
}

const totalProductionQty = computed(() => {
  return (Array.isArray(sessions.value) ? sessions.value : []).reduce((sum, row) => {
    if (!isCountableProductionRow(row)) return sum
    return sum + Number(row.production_qty || 0)
  }, 0)
})

const totalEffectiveWorkSeconds = computed(() => {
  const rows = Array.isArray(sessions.value) ? sessions.value : []
  const countedSessionIds = new Set()
  return rows.reduce((sum, row) => {
    if (!isCountableProductionRow(row)) return sum
    const sessionId = row?.id == null ? '' : String(row.id)
    if (sessionId) {
      if (countedSessionIds.has(sessionId)) return sum
      countedSessionIds.add(sessionId)
    }
    return sum + Number(row.effective_work_seconds || 0)
  }, 0)
})

const totalProductivityPerHour = computed(() => {
  const workSeconds = Number(totalEffectiveWorkSeconds.value || 0)
  if (workSeconds <= 0) return null
  return (Number(totalProductionQty.value || 0) * 3600) / workSeconds
})

const totalDurationIncludingPauseSeconds = computed(() => {
  const rows = Array.isArray(sessions.value) ? sessions.value : []
  const countedSessionIds = new Set()
  return rows.reduce((sum, row) => {
    const sessionId = row?.id == null ? '' : String(row.id)
    if (sessionId) {
      if (countedSessionIds.has(sessionId)) return sum
      countedSessionIds.add(sessionId)
    }
    return sum + Number(row.duration_seconds || 0)
  }, 0)
})

const totalProductivityIncludingPausePerHour = computed(() => {
  const workSeconds = Number(totalDurationIncludingPauseSeconds.value || 0)
  if (workSeconds <= 0) return null
  return (Number(totalProductionQty.value || 0) * 3600) / workSeconds
})

const totalPauseSeconds = computed(() => {
  const total = Number(totalDurationIncludingPauseSeconds.value || 0)
  const net = Number(totalEffectiveWorkSeconds.value || 0)
  return Math.max(total - net, 0)
})

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

const loadSessions = async () => {
  loading.value = true
  error.value = ''
  const wantsCancelOnly = sessionType.value === 'CANCEL'
  try {
    const params = {
      limit: 1000,
      start_date: startDate.value,
      end_date: endDate.value,
    }
    if (lineId.value) params.line_id = lineId.value
    if (processId.value) params.process_id = processId.value
    if (productCode.value.trim()) params.product_code = productCode.value.trim()
    if (sessionType.value && sessionType.value !== 'CANCEL') params.session_type = sessionType.value
    if (status.value) params.status = status.value
    if (hasIssue.value) params.has_issue = hasIssue.value

    const res = await api.processRealtime.getSessions(params)
    const items = res.data || []
    if (wantsCancelOnly) {
      sessions.value = items.filter((row) => isCanceledSession(row))
    } else if (sessionType.value === 'WORK') {
      sessions.value = items.filter((row) => row.session_type === 'WORK' && !isCanceledSession(row))
    } else {
      sessions.value = items
    }
  } catch (e) {
    console.error('セッション読込失敗:', e)
    error.value = '生産実績の取得に失敗しました。'
    sessions.value = []
  } finally {
    loading.value = false
  }
}

const resetFilters = async () => {
  lineId.value = ''
  processId.value = ''
  productCode.value = ''
  sessionType.value = ''
  status.value = ''
  hasIssue.value = ''
  startDate.value = toISODate(new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000))
  endDate.value = toISODate(new Date(today.getTime() + 24 * 60 * 60 * 1000))
  await loadSessions()
}

const formatDateTime = (value) => {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const h = d.getHours()
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}${mm}${dd} ${h}${min}`
}

const formatDuration = (seconds, endedAt) => {
  const isOpen = !endedAt
  const baseSeconds = Number(seconds || 0)
  let total = baseSeconds
  if (isOpen && total <= 0) {
    total = 0
  }
  const hh = Math.floor(total / 3600)
  const mm = Math.floor((total % 3600) / 60)
  const ss = total % 60
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}

const formatNumber = (value) => {
  if (value === null || value === undefined || value === '') return ''
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  return n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 3 })
}

const formatProductionQty = (row) => {
  if (!isCountableProductionRow(row)) return '—'
  return formatNumber(row.production_qty || 0)
}

const calcDurationBasedProductivity = (row) => {
  if (!row || !isCountableProductionRow(row)) return null
  const qty = Number(row.production_qty || 0)
  const durationSeconds = Number(row.duration_seconds || 0)
  if (!Number.isFinite(qty) || !Number.isFinite(durationSeconds) || qty <= 0 || durationSeconds <= 0) {
    return null
  }
  return (qty * 3600) / durationSeconds
}

const formatProductivity = (value, row = null) => {
  if (row && !isCountableProductionRow(row)) return '—'
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const exportCsv = () => _exportCsv(sessions.value, startDate.value, endDate.value)

const exportExcel = () => _exportExcel(sessions.value, startDate.value, endDate.value)

const exportExcel2 = () => exportProductionSummaryExcel(sessions.value, startDate.value, endDate.value)

const exportPdf = () => {
  const lineLabel = lines.value.find((l) => String(l.id) === String(lineId.value))?.line_code || ''
  const processLabel = processes.value.find((p) => String(p.id) === String(processId.value))?.process_code || ''
  _exportPdf(sessions.value, {
    lineLabel,
    processLabel,
    startDate: startDate.value,
    endDate: endDate.value,
    summary: {
      totalProductionQty: totalProductionQty.value,
      totalEffectiveWorkSeconds: totalEffectiveWorkSeconds.value,
      totalProductivityPerHour: totalProductivityPerHour.value,
      totalDurationIncludingPauseSeconds: totalDurationIncludingPauseSeconds.value,
      totalPauseSeconds: totalPauseSeconds.value,
      totalProductivityIncludingPausePerHour: totalProductivityIncludingPausePerHour.value,
    },
  })
}

onMounted(async () => {
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
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px 12px;
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #ffffff;
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-row-period {
  grid-column: span 2;
}
.filter-row label {
  min-width: 44px;
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
  font-size: 13px;
}
.filter-row-period input[type="date"] {
  flex: 1 1 0;
  min-width: 0;
  max-width: 115px;
  padding: 6px 4px;
}
.actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.export-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  grid-column: 1 / -1;
  padding-top: 4px;
  border-top: 1px dashed #e2e8f0;
  margin-top: 2px;
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
.btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.btn-secondary {
  border-color: #64748b;
  background: #64748b;
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
.summary-block {
  margin-bottom: 8px;
}
.summary-line {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #ffffff;
  overflow-x: auto;
  margin-bottom: 6px;
}
.summary-line-head {
  flex: 0 0 auto;
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}
.summary-line-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  white-space: nowrap;
}
.summary-meta {
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}
.summary-row {
  display: flex;
  justify-content: flex-end;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
  font-weight: 700;
}
.summary-label {
  color: #334155;
  font-size: 13px;
}
.summary-value {
  color: #0f172a;
  font-size: 20px;
}
.summary-value--md {
  font-size: 18px;
}
.summary-formula {
  display: flex;
  justify-content: flex-end;
  color: #64748b;
  font-size: 12px;
  margin-top: 2px;
}
.list-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1360px;
}
.list-table th,
.list-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  font-size: 13px;
  text-align: left;
  vertical-align: top;
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
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}
.badge-work {
  background: #dbeafe;
  color: #1d4ed8;
}
.badge-pause {
  background: #ffedd5;
  color: #c2410c;
}
.badge-cancel {
  background: #e2e8f0;
  color: #475569;
}
.row-pause {
  background: #fff7ed;
}
.issue {
  color: #b91c1c;
  font-weight: 700;
}
.no-data {
  text-align: center !important;
  color: #64748b;
  padding: 20px !important;
}
</style>
