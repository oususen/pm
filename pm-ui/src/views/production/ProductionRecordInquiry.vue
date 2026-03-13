<template>
  <div class="page">
    <div class="page-header">
      <h2 class="page-title">生産実績照会</h2>
      <p class="subtitle">開始〜終了をセッション単位で照会します（中断区間も表示。期間は08:00〜翌07:59で判定）。</p>
    </div>

    <div class="tab-bar">
      <button
        v-for="tab in recordTabs"
        :key="tab.key"
        type="button"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-show="operationalTabKeys.includes(activeTab)">
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
          <option v-for="line in visibleLines" :key="line.id" :value="String(line.id)">
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
      <div class="filter-row">
        <label>生産数0</label>
        <select v-model="excludeZeroProduction">
          <option value="">-- すべて --</option>
          <option value="true">除く</option>
        </select>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="loadSessions">検索</button>
        <button class="btn btn-secondary" :disabled="loading" @click="resetFilters">リセット</button>
      </div>
      <div class="export-actions">
        <button class="btn btn-secondary" :disabled="loading || !sessions.length" @click="exportCsv">CSV出力</button>
        <button class="btn btn-secondary" :disabled="loading || !sessions.length" @click="exportExcel">Excel出力</button>
        <button class="btn btn-secondary" :disabled="loading || !sessions.length" @click="exportExcel2">基幹システム入力用Excel</button>
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
            <th>中断理由</th>
            <th>工程</th>
            <th>品番</th>
            <th>品名</th>
            <th>作業者</th>
            <th class="num">継続時間</th>
            <th class="num">作業時間(休憩除き)</th>
            <th class="num">作業時間(休憩、中断除き)</th>
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
              <td>{{ row.pause_reason || '—' }}</td>
              <td>{{ row.process_code }} / {{ row.process_name }}</td>
              <td>{{ row.product_code || '—' }}</td>
              <td>{{ row.product_name || '' }}</td>
              <td>{{ row.operator_name || '—' }}</td>
              <td class="num">{{ formatDuration(row.duration_seconds, row.ended_at) }}</td>
              <td class="num">{{ formatDuration(row.effective_work_seconds, true) }}</td>
              <td class="num">{{ formatDuration(calcWorkSecondsExcludingPause(row), true) }}</td>
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
              <td colspan="19" class="no-data">データがありません</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    </div>

    <div v-show="activeTab === 'floor'" class="empty-tab">
      フロアタブは準備中です。
    </div>
    <div v-show="activeTab === 'blade'" class="empty-tab">
      ブレードタブは準備中です。
    </div>
    <div v-show="activeTab === 'line-settings'" class="settings-panel">
      <h3 class="settings-title">対象ライン編集</h3>
      <p class="settings-note">対象タブを選び、抽出するラインを設定します。</p>
      <div class="settings-selector">
        <label>対象タブ</label>
        <select v-model="settingsTargetTab">
          <option v-for="tab in configurableTabs" :key="`line-setting-${tab.key}`" :value="tab.key">
            {{ tab.label }}
          </option>
        </select>
      </div>
      <div class="settings-list">
        <label v-for="line in lines" :key="`target-${line.id}`" class="settings-check">
          <input
            type="checkbox"
            :checked="isTargetLineSelected(line.line_code)"
            @change="toggleTargetLine(line.line_code)"
          />
          <span>{{ line.line_code }} - {{ line.line_name }}</span>
        </label>
      </div>
      <div class="settings-actions">
        <button class="btn" type="button" @click="saveTargetLines">保存</button>
      </div>
      <div v-if="targetLineSaveMessage" class="settings-message">{{ targetLineSaveMessage }}</div>
    </div>
    <div v-show="activeTab === 'mapping-settings'" class="settings-panel">
      <h3 class="settings-title">マッピング作成</h3>
      <p class="settings-note">対象タブ選択後、まず加工品一覧を表示します。基幹品番を編集して保存してください。</p>
      <div class="settings-selector">
        <label>対象タブ</label>
        <select v-model="settingsTargetTab">
          <option v-for="tab in configurableTabs" :key="`map-setting-${tab.key}`" :value="tab.key">
            {{ tab.label }}
          </option>
        </select>
      </div>
      <div class="settings-selector">
        <label>工程フィルタ</label>
        <select v-model="mappingProcessFilter">
          <option value="">-- すべて --</option>
          <option v-for="code in mappingProcessFilterOptions" :key="`map-process-${code}`" :value="code">
            {{ code }}
          </option>
        </select>
      </div>
      <div v-if="mappingCandidateLoading" class="settings-info">加工品一覧を読込中...</div>
      <div v-else-if="mappingCandidateError" class="settings-error">{{ mappingCandidateError }}</div>
      <div class="table-wrap settings-table-wrap">
        <table class="list-table mapping-table">
          <thead>
            <tr>
              <th>アプリ品番</th>
              <th>工程コード</th>
              <th>基幹品番</th>
              <th>工順</th>
              <th title="品番確定後→工程順のEnterキー回数（自動入力用）">工程順行きエンター回数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredMappingEditRows" :key="`map-${settingsTargetTab}-${item.index}`">
              <td>
                <input v-model="item.row.appProductCode" type="text" class="map-input" placeholder="例: YD40000001" />
              </td>
              <td>
                <input v-model="item.row.processCode" type="text" class="map-input" placeholder="例: 4010" />
              </td>
              <td>
                <input v-model="item.row.coreProductCode" type="text" class="map-input" placeholder="例: A-0001" />
              </td>
              <td>
                <input v-model="item.row.coreProcessOrder" type="text" class="map-input" placeholder="例: 10" />
              </td>
              <td>
                <input v-model.number="item.row.enterCount" type="number" class="map-input map-input-narrow" min="1" max="20" placeholder="空=デフォ" />
              </td>
              <td>
                <button class="btn btn-secondary" type="button" @click="copyAppToCore(item.row)">コピー</button>
                <button class="btn btn-secondary" type="button" @click="removeMappingRow(item.index)">削除</button>
              </td>
            </tr>
            <tr v-if="!filteredMappingEditRows.length">
              <td colspan="6" class="no-data">加工品がありません</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="settings-actions">
        <button class="btn btn-secondary" type="button" @click="addMappingRow">行追加</button>
        <button class="btn" type="button" @click="saveMappings">保存</button>
      </div>
      <div v-if="mappingSaveMessage" class="settings-message">{{ mappingSaveMessage }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { authState } from '@/auth'
import api from '@/api/client'
import { hasPermission } from '@/router'
import { addDays, formatISODate, getBusinessDate } from '@/utils/dateUtil'
import { exportProductionSummaryExcel } from '@/utils/productionRecordExport2'
import {
  createDefaultMappingsByTab,
  createDefaultTargetLineCodesByTab,
  getProductionRecordMappingsByTab,
  getTargetLineCodesByTab,
  loadProductionRecordMappingsByTab,
  loadTargetLineCodesByTab,
  normalizeProductionRecordMappingsByTab,
  normalizeTargetLineCodesByTab,
  saveProductionRecordMappingsByTab,
  saveTargetLineCodesByTab,
} from '@/config/productionRecordSettings'
import {
  exportCsv as _exportCsv,
  exportExcel as _exportExcel,
  exportPdf as _exportPdf,
} from '@/utils/productionRecordExport'

const loading = ref(false)
const error = ref('')
const sessions = ref([])
const activeTab = ref('tank')
const operationalTabKeys = ['tank', 'laser']
const settingsTargetTab = ref('tank')
const configurableTabs = [
  { key: 'tank', label: 'タンク' },
  { key: 'floor', label: 'フロア' },
  { key: 'blade', label: 'ブレード' },
  { key: 'laser', label: '板金' },
]
const baseRecordTabs = [
  { key: 'tank', label: 'タンク' },
  { key: 'floor', label: 'フロア' },
  { key: 'blade', label: 'ブレード' },
  { key: 'laser', label: '板金' },
]
const settingsTabs = [
  { key: 'line-settings', label: '対象ライン編集' },
  { key: 'mapping-settings', label: 'マッピング作成' },
]

const lines = ref([])
const processes = ref([])

const buildDefaultDateRange = () => {
  const businessToday = getBusinessDate()
  return {
    start: formatISODate(addDays(businessToday, -7)),
    end: formatISODate(businessToday),
  }
}
const defaultDateRange = buildDefaultDateRange()
const startDate = ref(defaultDateRange.start)
const endDate = ref(defaultDateRange.end)
const lineId = ref('')
const processId = ref('')
const productCode = ref('')
const sessionType = ref('')
const status = ref('')
const hasIssue = ref('')
const excludeZeroProduction = ref('')
const targetLineCodesByTab = ref(createDefaultTargetLineCodesByTab())
const targetLineSaveMessage = ref('')
const mappingsByTab = ref(createDefaultMappingsByTab())
const mappingEditRows = ref(getProductionRecordMappingsByTab(mappingsByTab.value, settingsTargetTab.value))
const mappingSaveMessage = ref('')
const mappingCandidateLoading = ref(false)
const mappingCandidateError = ref('')
const mappingProcessFilter = ref('')
const ACTIVE_LINE_CODES = computed(() => getTargetLineCodesByTab(targetLineCodesByTab.value, activeTab.value))
const canEditRecordInquirySettings = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const hasSpecific = permissions.some((item) => item.resource === 'production.record_inquiry')
  if (hasSpecific) return hasPermission(user, 'production.record_inquiry', 'edit')
  return hasPermission(user, 'production', 'edit')
})
const recordTabs = computed(() => (
  canEditRecordInquirySettings.value
    ? [...baseRecordTabs, ...settingsTabs]
    : baseRecordTabs
))

const tankLineOptions = computed(() => {
  const codeSet = new Set(ACTIVE_LINE_CODES.value)
  return (Array.isArray(lines.value) ? lines.value : []).filter((line) => codeSet.has(String(line?.line_code || '')))
})

const visibleLines = computed(() => {
  if (operationalTabKeys.includes(activeTab.value)) return tankLineOptions.value
  return lines.value
})

const tankProcessIdSet = computed(() => {
  const lineIds = new Set(tankLineOptions.value.map((line) => String(line.id)))
  const ids = new Set()
  const baseProcesses = Array.isArray(processes.value) ? processes.value : []
  baseProcesses.forEach((p) => {
    if (lineIds.has(String(p?.line))) ids.add(String(p.id))
  })
  return ids
})

const filteredProcesses = computed(() => {
  let base = Array.isArray(processes.value) ? processes.value : []
  if (operationalTabKeys.includes(activeTab.value)) {
    const allowed = tankProcessIdSet.value
    base = base.filter((p) => allowed.has(String(p.id)))
  }
  if (!lineId.value) return base
  return base.filter((p) => String(p.line) === String(lineId.value))
})

const mappingProcessFilterOptions = computed(() => {
  const codes = new Set()
  ;(Array.isArray(mappingEditRows.value) ? mappingEditRows.value : []).forEach((row) => {
    const code = String(row?.processCode || '').trim()
    if (code) codes.add(code)
  })
  return Array.from(codes).sort((a, b) => a.localeCompare(b))
})

const filteredMappingEditRows = computed(() => {
  const rows = Array.isArray(mappingEditRows.value) ? mappingEditRows.value : []
  const filterCode = String(mappingProcessFilter.value || '').trim()
  return rows
    .map((row, index) => ({ row, index }))
    .filter((item) => !filterCode || String(item.row?.processCode || '').trim() === filterCode)
})

const normalizeList = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const isCountableProductionRow = (row) => {
  if (!row) return false
  const endAction = String(row.end_action || '').toUpperCase()
  if (String(row.record_source || '').toUpperCase() === 'LASER') {
    return ['END', 'PAUSE'].includes(endAction)
  }
  if (row.session_type !== 'WORK') return false
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
    return sum + Number(row.effective_work_seconds || 0)
  }, 0)
})

const totalProductivityIncludingPausePerHour = computed(() => {
  const workSeconds = Number(totalDurationIncludingPauseSeconds.value || 0)
  if (workSeconds <= 0) return null
  return (Number(totalProductionQty.value || 0) * 3600) / workSeconds
})

const totalPauseSeconds = computed(() => {
  const rows = Array.isArray(sessions.value) ? sessions.value : []
  const countedSessionIds = new Set()
  return rows.reduce((sum, row) => {
    const sessionId = row?.id == null ? '' : String(row.id)
    if (sessionId) {
      if (countedSessionIds.has(sessionId)) return sum
      countedSessionIds.add(sessionId)
    }
    return String(row?.session_type || '').toUpperCase() === 'PAUSE'
      ? sum + Number(row?.duration_seconds || 0)
      : sum
  }, 0)
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

const applyProductionRecordSettingsPayload = (payload) => {
  targetLineCodesByTab.value = normalizeTargetLineCodesByTab(payload?.target_line_codes_by_tab)
  mappingsByTab.value = normalizeProductionRecordMappingsByTab(payload?.mappings_by_tab)
  mappingEditRows.value = getProductionRecordMappingsByTab(mappingsByTab.value, settingsTargetTab.value)
}

const loadProductionRecordSettings = async () => {
  try {
    const res = await api.productionRecordSettings.getSettings()
    applyProductionRecordSettingsPayload(res.data || {})
  } catch (e) {
    console.error('生産実績照会設定取得失敗:', e)
    // API障害時はローカル保存値で継続運用する
    targetLineCodesByTab.value = loadTargetLineCodesByTab()
    mappingsByTab.value = loadProductionRecordMappingsByTab()
    mappingEditRows.value = getProductionRecordMappingsByTab(mappingsByTab.value, settingsTargetTab.value)
  }
}

const saveProductionRecordSettings = async () => {
  const payload = {
    target_line_codes_by_tab: normalizeTargetLineCodesByTab(targetLineCodesByTab.value),
    mappings_by_tab: normalizeProductionRecordMappingsByTab(mappingsByTab.value),
  }
  try {
    const res = await api.productionRecordSettings.saveSettings(payload)
    applyProductionRecordSettingsPayload(res.data || payload)
  } catch (e) {
    console.error('生産実績照会設定保存失敗:', e)
    // API障害時はローカルへ退避
    targetLineCodesByTab.value = saveTargetLineCodesByTab(payload.target_line_codes_by_tab)
    mappingsByTab.value = saveProductionRecordMappingsByTab(payload.mappings_by_tab)
    mappingEditRows.value = getProductionRecordMappingsByTab(mappingsByTab.value, settingsTargetTab.value)
    throw e
  }
}

const loadSessions = async () => {
  loading.value = true
  error.value = ''
  const wantsCancelOnly = sessionType.value === 'CANCEL'
  try {
    if (activeTab.value === 'laser') {
      const laserParams = {
        page_size: 1000,
        work_date__gte: startDate.value,
        work_date__lte: endDate.value,
        ordering: '-work_date,-created_at',
      }

      const laserRes = await api.laserActuals.getLaserActuals(laserParams)
      let laserItems = normalizeList(laserRes.data).flatMap((row) => {
        const action = String(row?.operator_action || '').toUpperCase()
        const isOpen = action === 'START' || action === 'RESUME'
        const totalMinutes = Number(row?.total_process_time || 0)
        const effectiveSeconds = Math.max(0, Math.round(totalMinutes * 60))
        const componentDetails = normalizeList(row?.details)
          .filter((detail) => String(detail?.detail_type || '').toUpperCase() === 'COMPONENT')

        const buildLaserRow = (detail) => {
          const productionQty = Number(detail?.total_qty || 0)
          const productivity = productionQty > 0 && effectiveSeconds > 0
            ? (productionQty * 3600) / effectiveSeconds
            : null
          return {
            id: row?.id,
            started_at: row?.created_at || null,
            ended_at: isOpen ? null : (row?.created_at || null),
            session_type: 'WORK',
            start_action: action || '—',
            end_action: action || '—',
            pause_reason: row?.operator_action_reason || '',
            process_code: row?.equipment_code || '',
            process_name: row?.equipment_name || '',
            product_code: detail?.product_code || '',
            product_name: detail?.product_name || '',
            operator_name: row?.created_by_name || row?.updated_by_name || '—',
            duration_seconds: effectiveSeconds,
            effective_work_seconds: effectiveSeconds,
            production_qty: productionQty,
            productivity_per_hour: productivity,
            issue_count: 0,
            issue_flags: [],
            record_source: 'LASER',
          }
        }

        if (!componentDetails.length) {
          return [buildLaserRow(null)]
        }
        return componentDetails.map((detail) => buildLaserRow(detail))
      })

      const keyword = String(productCode.value || '').trim().toLowerCase()
      if (keyword) {
        laserItems = laserItems.filter((row) => {
          const code = String(row?.product_code || '').toLowerCase()
          const name = String(row?.product_name || '').toLowerCase()
          return code.includes(keyword) || name.includes(keyword)
        })
      }

      if (lineId.value) {
        const selectedLine = lines.value.find((line) => String(line.id) === String(lineId.value))
        const lineCode = String(selectedLine?.line_code || '').trim().toLowerCase()
        if (lineCode) {
          laserItems = laserItems.filter((row) => {
            const processLabel = `${row?.process_code || ''} ${row?.process_name || ''}`.toLowerCase()
            return processLabel.includes(lineCode)
          })
        }
      }

      if (processId.value) {
        const selectedProcess = processes.value.find((proc) => String(proc.id) === String(processId.value))
        const processCode = String(selectedProcess?.process_code || '').trim().toLowerCase()
        if (processCode) {
          laserItems = laserItems.filter((row) => {
            const processLabel = `${row?.process_code || ''} ${row?.process_name || ''}`.toLowerCase()
            return processLabel.includes(processCode)
          })
        }
      }

      if (status.value === 'OPEN') {
        laserItems = laserItems.filter((row) => !row.ended_at)
      } else if (status.value === 'CLOSED') {
        laserItems = laserItems.filter((row) => !!row.ended_at)
      }

      if (excludeZeroProduction.value === 'true') {
        laserItems = laserItems.filter((row) => Number(row?.production_qty || 0) !== 0)
      }

      if (hasIssue.value === 'true') {
        laserItems = []
      }

      if (wantsCancelOnly) {
        laserItems = laserItems.filter((row) => isCanceledSession(row))
      } else if (sessionType.value === 'WORK') {
        laserItems = laserItems.filter((row) => row.session_type === 'WORK' && !isCanceledSession(row))
      } else if (sessionType.value === 'PAUSE') {
        laserItems = laserItems.filter((row) => String(row?.end_action || '').toUpperCase() === 'PAUSE')
      }

      sessions.value = laserItems
      return
    }

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
    const filteredByTab = operationalTabKeys.includes(activeTab.value)
      ? items.filter((row) => tankProcessIdSet.value.has(String(row?.process || '')))
      : items

    const filteredByProduction = excludeZeroProduction.value === 'true'
      ? filteredByTab.filter((row) => Number(row?.production_qty || 0) !== 0)
      : filteredByTab

    if (wantsCancelOnly) {
      sessions.value = filteredByProduction.filter((row) => isCanceledSession(row))
    } else if (sessionType.value === 'WORK') {
      sessions.value = filteredByProduction.filter((row) => row.session_type === 'WORK' && !isCanceledSession(row))
    } else {
      sessions.value = filteredByProduction
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
  const nextDefaultDateRange = buildDefaultDateRange()
  lineId.value = ''
  processId.value = ''
  productCode.value = ''
  sessionType.value = ''
  status.value = ''
  hasIssue.value = ''
  excludeZeroProduction.value = ''
  startDate.value = nextDefaultDateRange.start
  endDate.value = nextDefaultDateRange.end
  await loadSessions()
}

watch(activeTab, async (nextTab) => {
  if ((nextTab === 'line-settings' || nextTab === 'mapping-settings') && !canEditRecordInquirySettings.value) {
    activeTab.value = 'tank'
    return
  }
  if (nextTab === 'mapping-settings') {
    await loadMappingCandidates(settingsTargetTab.value)
    return
  }
  if (!operationalTabKeys.includes(nextTab)) return
  const visibleLineIds = new Set(visibleLines.value.map((line) => String(line.id)))
  if (lineId.value && !visibleLineIds.has(String(lineId.value))) {
    lineId.value = ''
    processId.value = ''
  }
  await loadSessions()
})

watch(settingsTargetTab, (nextTab) => {
  void loadMappingCandidates(nextTab)
  targetLineSaveMessage.value = ''
  mappingSaveMessage.value = ''
  mappingProcessFilter.value = ''
})

const buildMappingKey = (appProductCode, processCode) => {
  const app = String(appProductCode || '').trim().toUpperCase()
  const proc = String(processCode || '').trim().toUpperCase()
  return `${app}__${proc}`
}

const loadMappingCandidates = async (tabKey = settingsTargetTab.value) => {
  mappingCandidateLoading.value = true
  mappingCandidateError.value = ''
  mappingProcessFilter.value = ''
  try {
    const targetCodes = new Set(getTargetLineCodesByTab(targetLineCodesByTab.value, tabKey))
    const targetLineIds = new Set(
      (Array.isArray(lines.value) ? lines.value : [])
        .filter((line) => targetCodes.has(String(line?.line_code || '').toUpperCase()))
        .map((line) => String(line.id)),
    )
    const targetProcesses = (Array.isArray(processes.value) ? processes.value : [])
      .filter((p) => targetLineIds.has(String(p?.line)))
    const targetProcessMap = new Map(
      targetProcesses.map((p) => [String(p.id), String(p?.process_code || '').trim()]),
    )

    const existing = getProductionRecordMappingsByTab(mappingsByTab.value, tabKey)
    const exactMap = new Map(existing.map((row) => [buildMappingKey(row.appProductCode, row.processCode), row]))
    const fallbackMap = new Map(existing.map((row) => [String(row.appProductCode || '').trim().toUpperCase(), row]))

    const candidateMap = new Map()
    const routingResults = await Promise.all(Array.from(targetLineIds).map(async (lineId) => {
      try {
        const res = await api.routings.getRoutingSteps({ line: lineId, page_size: 5000 })
        return res.data?.results || res.data || []
      } catch (_e) {
        return []
      }
    }))

    routingResults.flat().forEach((step) => {
      const processId = String(step?.process || '')
      if (!targetProcessMap.has(processId)) return
      const processCode = targetProcessMap.get(processId)
      const appCode = String(step?.output_product_code || '').trim()
      if (!processCode || !appCode) return
      const key = buildMappingKey(appCode, processCode)
      if (candidateMap.has(key)) return
      const exactCore = exactMap.get(key)
      const fallbackCore = fallbackMap.get(appCode.toUpperCase())
      candidateMap.set(key, {
        appProductCode: appCode,
        processCode,
        coreProductCode: exactCore?.coreProductCode || fallbackCore?.coreProductCode || '',
        coreProcessOrder: exactCore?.coreProcessOrder || fallbackCore?.coreProcessOrder || '',
        enterCount: exactCore?.enterCount ?? fallbackCore?.enterCount ?? 2,
      })
    })

    // 既存保存分（ルーティング上で消えた品番含む）は編集できるよう残す
    existing.forEach((row) => {
      const key = buildMappingKey(row.appProductCode, row.processCode)
      if (!candidateMap.has(key)) {
        candidateMap.set(key, {
          appProductCode: row.appProductCode,
          processCode: row.processCode,
          coreProductCode: row.coreProductCode,
          coreProcessOrder: row.coreProcessOrder || '',
          enterCount: row.enterCount ?? 2,
        })
      }
    })

    mappingEditRows.value = Array.from(candidateMap.values()).sort((a, b) => {
      const p = String(a.appProductCode || '').localeCompare(String(b.appProductCode || ''))
      if (p !== 0) return p
      return String(a.processCode || '').localeCompare(String(b.processCode || ''))
    })
  } catch (e) {
    console.error('加工品一覧取得失敗:', e)
    mappingCandidateError.value = '加工品一覧の取得に失敗しました。'
    mappingEditRows.value = getProductionRecordMappingsByTab(mappingsByTab.value, tabKey)
  } finally {
    mappingCandidateLoading.value = false
  }
}

const isTargetLineSelected = (lineCode) => {
  const code = String(lineCode || '').trim().toUpperCase()
  if (!code) return false
  const current = getTargetLineCodesByTab(targetLineCodesByTab.value, settingsTargetTab.value)
  return current.includes(code)
}

const toggleTargetLine = (lineCode) => {
  if (!canEditRecordInquirySettings.value) return
  const code = String(lineCode || '').trim().toUpperCase()
  if (!code) return
  const tabKey = settingsTargetTab.value
  const current = new Set(getTargetLineCodesByTab(targetLineCodesByTab.value, tabKey))
  if (current.has(code)) current.delete(code)
  else current.add(code)
  targetLineCodesByTab.value = {
    ...targetLineCodesByTab.value,
    [tabKey]: Array.from(current),
  }
  targetLineSaveMessage.value = ''
}

const saveTargetLines = async () => {
  if (!canEditRecordInquirySettings.value) return
  try {
    await saveProductionRecordSettings()
  } catch (e) {
    console.error('対象ライン保存失敗:', e)
    targetLineSaveMessage.value = '対象ラインの保存に失敗しました。'
    return
  }
  targetLineSaveMessage.value = '対象ラインを保存しました。'

  if (operationalTabKeys.includes(activeTab.value)) {
    const selectedLineCode = lines.value.find((line) => String(line.id) === String(lineId.value))?.line_code
    const savedActiveCodes = getTargetLineCodesByTab(targetLineCodesByTab.value, activeTab.value)
    if (selectedLineCode && !savedActiveCodes.includes(String(selectedLineCode).toUpperCase())) {
      lineId.value = ''
      processId.value = ''
    }
    await loadSessions()
  }
  if (activeTab.value === 'mapping-settings') {
    await loadMappingCandidates(settingsTargetTab.value)
  }
}

const addMappingRow = () => {
  if (!canEditRecordInquirySettings.value) return
  mappingEditRows.value.push({ appProductCode: '', processCode: '', coreProductCode: '', coreProcessOrder: '', enterCount: 2 })
  mappingSaveMessage.value = ''
}

const removeMappingRow = (index) => {
  if (!canEditRecordInquirySettings.value) return
  mappingEditRows.value.splice(index, 1)
  mappingSaveMessage.value = ''
}

const copyAppToCore = (row) => {
  if (!canEditRecordInquirySettings.value) return
  if (!row) return
  row.coreProductCode = String(row.appProductCode || '').trim()
  mappingSaveMessage.value = ''
}

const saveMappings = () => {
  if (!canEditRecordInquirySettings.value) return
  const persist = async () => {
    const tabKey = settingsTargetTab.value
    mappingsByTab.value = {
      ...mappingsByTab.value,
      [tabKey]: mappingEditRows.value,
    }
    await saveProductionRecordSettings()
    mappingEditRows.value = getProductionRecordMappingsByTab(mappingsByTab.value, tabKey)
    mappingSaveMessage.value = 'マッピングを保存しました。'
  }

  persist().catch((e) => {
    console.error('マッピング保存失敗:', e)
    mappingSaveMessage.value = 'マッピングの保存に失敗しました。'
  })
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

const calcWorkSecondsExcludingPause = (row) => {
  if (!row) return 0
  return String(row.session_type || '').toUpperCase() === 'PAUSE'
    ? 0
    : Math.max(Number(row.effective_work_seconds || 0), 0)
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

const exportExcel2 = () => {
  const confirmed = window.confirm('出力したexcelの内容を基幹システムに入力するため、必ず期間を入力したい日にしてください')
  if (!confirmed) return
  exportProductionSummaryExcel(
    sessions.value,
    startDate.value,
    endDate.value,
    { tabKey: activeTab.value, mappingsByTab: mappingsByTab.value },
  )
}

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
  await loadProductionRecordSettings()
  await loadMappingCandidates(settingsTargetTab.value)
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
.tab-bar {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  border-bottom: 1px solid #cbd5e1;
}
.tab-item {
  padding: 7px 14px;
  border: 1px solid #cbd5e1;
  border-bottom: none;
  border-radius: 8px 8px 0 0;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.tab-item.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #fff;
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
.empty-tab {
  margin-top: 8px;
  padding: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
  color: #64748b;
  font-weight: 700;
}
.settings-panel {
  margin-top: 8px;
  padding: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #fff;
}
.settings-title {
  margin: 0;
  font-size: 17px;
}
.settings-note {
  margin: 6px 0 12px;
  color: #64748b;
  font-size: 13px;
}
.settings-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.settings-selector label {
  font-size: 13px;
  font-weight: 700;
}
.settings-selector select {
  min-width: 160px;
  padding: 7px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
}
.settings-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 8px;
}
.settings-check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.settings-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
.settings-message {
  margin-top: 8px;
  color: #166534;
  font-size: 13px;
  font-weight: 700;
}
.settings-info {
  margin: 6px 0 8px;
  color: #1e3a8a;
  font-size: 13px;
  font-weight: 700;
}
.settings-error {
  margin: 6px 0 8px;
  color: #991b1b;
  font-size: 13px;
  font-weight: 700;
}
.settings-table-wrap {
  margin-top: 8px;
}
.mapping-table {
  min-width: 760px;
}
.map-input-narrow {
  min-width: 60px !important;
  width: 70px !important;
  text-align: center;
}
.map-input {
  width: 100%;
  min-width: 140px;
  padding: 7px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
}
</style>
