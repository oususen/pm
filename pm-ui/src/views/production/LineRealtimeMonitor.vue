<template>
  <div class="monitor-container">
    <div class="toolbar">
      <h2 class="page-title">ライン稼働監視 <DataSourceDialog title="ライン稼働監視" :sources="dsSources" /></h2>
      <div class="toolbar-right">
        <button class="btn" @click="loadData" :disabled="loading">
          {{ loading ? '更新中...' : '再読込' }}
        </button>
        <button class="btn" @click="toggleAutoRefresh">
          自動更新: {{ autoRefresh ? 'ON' : 'OFF' }}
        </button>
      </div>
    </div>

    <!-- KPIサマリー -->
    <div class="kpi-section">
      <div class="kpi-card">
        <div class="kpi-label">稼働中ライン数</div>
        <div class="kpi-value running">{{ runningCount }} / {{ lines.length }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">本日総生産数</div>
        <div class="kpi-value">{{ totalOutput }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">本日総計画数</div>
        <div class="kpi-value">{{ totalPlan }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">平均達成率</div>
        <div class="kpi-value" :class="getAchievementClass(avgAchievement)">
          {{ avgAchievement }}%
        </div>
      </div>
    </div>

    <!-- 工程状態一覧 -->
    <div class="lines-section">
      <div class="section-header">
        <h3>工程状態</h3>
        <span class="update-time">最終更新: {{ lastUpdate }}</span>
      </div>
      <div class="line-selector">
        <div class="line-selector__label">ライン選択</div>
        <div v-if="!lines.length" class="no-data">
          ライン情報がありません
        </div>
        <div v-else class="line-selector__grid">
          <button
            v-for="line in lines"
            :key="line.line"
            type="button"
            class="line-select-card"
            :class="[getStatusCardClass(line.current_state), { 'is-selected': isSelectedLine(line.line) }]"
            :aria-pressed="isSelectedLine(line.line)"
            @click="selectLine(line.line)"
          >
            <div class="line-select-name">{{ line.line_name }}</div>
            <span class="state-badge" :class="getStateBadgeClass(line.current_state)">
              {{ line.state_display }}
            </span>
          </button>
        </div>
      </div>

      <div v-if="!selectedLineId && lines.length" class="no-data">
        ラインを選択してください
      </div>
      <div v-else>
        <div v-if="processLoading" class="process-loading">
          工程を読み込み中...
        </div>
        <div v-else-if="processError" class="process-error">
          {{ processError }}
        </div>
        <div v-else-if="!processStatuses.length" class="no-data">
          工程が登録されていません
        </div>
        <div v-else class="status-grid">
          <div
            v-for="process in processStatuses"
            :key="process.id"
            class="status-card"
            :class="getStatusCardClass(process.current_state)"
          >
            <div class="status-card__header">
              <div class="status-name">{{ process.process_name }}</div>
              <div class="status-header-right">
                <span class="state-badge" :class="getStateBadgeClass(process.current_state)">
                  {{ process.state_display }}
                </span>
                <div
                  v-if="shouldShowStateStart(process)"
                  class="state-start-time"
                >
                  開始: {{ formatTime(process.state_started_at) }}
                </div>
              </div>
            </div>

            <div class="status-card__metrics">
              <div class="metric-row">
                <span class="metric-label">本日計画</span>
                <span class="metric-value">{{ formatNumber(process.today_plan) }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">本日実績</span>
                <span class="metric-value highlight">{{ formatNumber(process.today_output) }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">達成率</span>
                <span
                  class="metric-value"
                  :class="getAchievementClass(process.achievement_rate)"
                >
                  {{ process.achievement_rate }}%
                </span>
              </div>
              <div class="metric-row">
                <span class="metric-label">進捗</span>
                <span class="metric-value">{{ process.progress }}%</span>
              </div>
            </div>

            <div v-if="process.current_product_code" class="status-card__current">
              <div class="current-label">現在生産中</div>
              <div class="current-product">{{ process.current_product_code }}</div>
              <div class="current-name">{{ process.current_product_name }}</div>
            </div>
            <div v-else class="status-card__current empty">
              <div class="current-label">待機中</div>
            </div>

            <div class="progress-bar-container">
              <div
                class="progress-bar-fill"
                :style="{ width: Math.min(process.progress, 100) + '%' }"
                :class="getProgressBarClass(process.progress)"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ローディング -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_line_realtime', desc: 'ラインリアルタイム状態' },
  { op: '読み取り', table: 'm_line', desc: 'ライン一覧' },
  { op: '読み取り', table: 't_process_realtime_record', desc: '工程リアルタイム実績' },
]

const lines = ref([])
const loading = ref(false)
const autoRefresh = ref(true)
const lastUpdate = ref('')
const selectedLineId = ref('')
const processStatuses = ref([])
const processLoading = ref(false)
const processError = ref('')
let refreshInterval = null

// KPI計算
const runningCount = computed(() => {
  return lines.value.filter(l => l.current_state === 'RUNNING').length
})

const totalOutput = computed(() => {
  return lines.value.reduce((sum, l) => sum + Number(l.today_output || 0), 0)
})

const totalPlan = computed(() => {
  return lines.value.reduce((sum, l) => sum + Number(l.today_plan || 0), 0)
})

const avgAchievement = computed(() => {
  if (lines.value.length === 0) return 0
  const total = lines.value.reduce((sum, l) => sum + Number(l.achievement_rate || 0), 0)
  return (total / lines.value.length).toFixed(1)
})

// データ読み込み
const loadData = async () => {
  loading.value = true
  try {
    const [statusRes, productionLinesRes] = await Promise.all([
      api.lineRealtime.getLineStatuses(),
      api.lines.getProductionLines({ is_active: true }),
    ])
    const productionLinePayload = productionLinesRes?.data || []
    const productionLines = Array.isArray(productionLinePayload)
      ? productionLinePayload
      : productionLinePayload.results || []
    const productionLineIds = new Set(productionLines.map(line => String(line.id)))
    const statusPayload = statusRes?.data || []
    const allStatuses = Array.isArray(statusPayload)
      ? statusPayload
      : statusPayload.results || []
    lines.value = allStatuses.filter(line => productionLineIds.has(String(line.line)))
    if (selectedLineId.value) {
      const exists = lines.value.some(line => String(line.line) === String(selectedLineId.value))
      if (!exists) {
        selectedLineId.value = ''
        processStatuses.value = []
      }
    }
    if (selectedLineId.value) {
      await fetchProcessStatuses(selectedLineId.value)
    }
    lastUpdate.value = new Date().toLocaleTimeString('ja-JP')
  } catch (error) {
    console.error('ライン状態取得エラー:', error)
    alert('データの読み込みに失敗しました')
  } finally {
    loading.value = false
  }
}

// 自動更新切り替え
const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

const startAutoRefresh = () => {
  if (refreshInterval) return
  refreshInterval = setInterval(() => {
    loadData()
  }, 10000) // 10秒ごと
}

const stopAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

const fetchProcessStatuses = async (lineId) => {
  processLoading.value = true
  processError.value = ''
  try {
    const res = await api.processRealtime.getProcessStatuses({ line_id: lineId })
    const data = res.data || []
    processStatuses.value = Array.isArray(data) ? data : []
  } catch (error) {
    console.error('工程取得エラー:', error)
    processError.value = '工程の読み込みに失敗しました'
    processStatuses.value = []
  } finally {
    processLoading.value = false
  }
}

const selectLine = (lineId) => {
  if (!lineId) {
    selectedLineId.value = ''
    return
  }
  selectedLineId.value = String(lineId)
}

const isSelectedLine = (lineId) => {
  if (!selectedLineId.value) return false
  return String(lineId) === String(selectedLineId.value)
}

// ヘルパー関数
const formatNumber = (value) => {
  if (value === null || value === undefined) return '0'
  return Number(value).toLocaleString()
}

const getStatusCardClass = (state) => {
  const label = state ? String(state).toLowerCase() : 'unknown'
  return `state-${label}`
}

const getStateBadgeClass = (state) => {
  const classes = {
    'RUNNING': 'badge-running',
    'IDLE': 'badge-idle',
    'SETUP': 'badge-setup',
    'MAINTENANCE': 'badge-maintenance',
    'BREAKDOWN': 'badge-breakdown',
    'STOPPED': 'badge-stopped',
  }
  return classes[state] || ''
}

const shouldShowStateStart = (process) => {
  if (!process) return false
  return Boolean(process.state_started_at)
}

const formatTime = (value) => {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
}

const getAchievementClass = (rate) => {
  const r = Number(rate)
  if (r >= 100) return 'excellent'
  if (r >= 90) return 'good'
  if (r >= 80) return 'warning'
  return 'critical'
}

const getProgressBarClass = (progress) => {
  const p = Number(progress)
  if (p >= 90) return 'excellent'
  if (p >= 70) return 'good'
  if (p >= 50) return 'warning'
  return 'critical'
}

// ライフサイクル
onMounted(() => {
  loadData()
  if (autoRefresh.value) {
    startAutoRefresh()
  }
})

onUnmounted(() => {
  stopAutoRefresh()
})

watch(selectedLineId, (lineId) => {
  if (!lineId) {
    processStatuses.value = []
    return
  }
  fetchProcessStatuses(lineId)
})
</script>

<style scoped>
.monitor-container {
  padding: 8px 10px 14px;
  background: #eef2f6;
  min-height: 100vh;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  color: #1f2a44;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #e1e8f4;
  border: 1px solid #c5cfde;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 12px;
}

.page-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.toolbar-right {
  display: flex;
  gap: 6px;
}

.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}

.btn:hover {
  background: #f3f4f6;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* KPIセクション */
.kpi-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-card {
  background: #fff;
  border: 1px solid #d7dfe8;
  border-radius: 6px;
  padding: 12px;
}

.kpi-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #1f2a44;
}

.kpi-value.running {
  color: #16a34a;
}

.kpi-value.excellent {
  color: #16a34a;
}

.kpi-value.good {
  color: #0ea5e9;
}

.kpi-value.warning {
  color: #f59e0b;
}

.kpi-value.critical {
  color: #ef4444;
}

/* ラインセクション */
.lines-section {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.section-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
}

.update-time {
  font-size: 12px;
  color: #64748b;
}

.no-data {
  text-align: center;
  color: #94a3b8;
  padding: 40px 20px;
  font-size: 14px;
}

.line-selector {
  margin-bottom: 12px;
}

.line-selector__label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}

.line-selector__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
}

.line-select-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #d7dfe8;
  border-left: 4px solid #cbd5e1;
  border-radius: 6px;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.2s;
}

.line-select-card:hover {
  background: #f1f5f9;
}

.line-select-card.is-selected {
  border: 2px solid #000000;
  border-left-width: 6px;
  box-shadow: none;
}

.line-select-card:focus-visible {
  outline: 2px solid #93c5fd;
  outline-offset: 2px;
}

.line-select-name {
  font-size: 13px;
  font-weight: 600;
  color: #1f2a44;
}

.line-select-card.state-running {
  border-left-color: #16a34a;
  background: #f0fdf4;
}

.line-select-card.state-breakdown {
  border-left-color: #ef4444;
  background: #fef2f2;
}

.line-select-card.state-maintenance {
  border-left-color: #f59e0b;
  background: #fffbeb;
}

.line-select-card.state-setup {
  border-left-color: #0ea5e9;
  background: #f0f9ff;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.status-card {
  border: 1px solid #d7dfe8;
  border-radius: 6px;
  border-left: 4px solid #cbd5e1;
  padding: 12px;
  background: #f8fafc;
  transition: all 0.3s;
}

.status-card.state-running {
  border-left-color: #16a34a;
  background: #f0fdf4;
}

.status-card.state-breakdown {
  border-left-color: #ef4444;
  background: #fef2f2;
  animation: pulse-red 2s infinite;
}

.status-card.state-maintenance {
  border-left-color: #f59e0b;
  background: #fffbeb;
}

.status-card.state-setup {
  border-left-color: #0ea5e9;
  background: #f0f9ff;
}

@keyframes pulse-red {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.status-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.status-name {
  font-size: 15px;
  font-weight: 700;
  color: #1f2a44;
}

.status-header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.state-badge {
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.state-start-time {
  font-size: 11px;
  color: #64748b;
}

.badge-running {
  background: #d1fae5;
  color: #065f46;
}

.badge-breakdown {
  background: #fee2e2;
  color: #991b1b;
}

.badge-maintenance {
  background: #fef3c7;
  color: #92400e;
}

.badge-setup {
  background: #dbeafe;
  color: #1e40af;
}

.badge-idle {
  background: #f1f5f9;
  color: #475569;
}

.badge-stopped {
  background: #e2e8f0;
  color: #334155;
}

.status-card__metrics {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}

.metric-label {
  color: #64748b;
}

.metric-value {
  font-weight: 600;
  color: #1f2a44;
}

.metric-value.highlight {
  font-size: 16px;
  color: #16a34a;
}

.status-card__current {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
}

.status-card__current.empty {
  text-align: center;
  color: #94a3b8;
}

.current-label {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 4px;
}

.current-product {
  font-size: 14px;
  font-weight: 700;
  color: #1f2a44;
}

.current-name {
  font-size: 12px;
  color: #64748b;
}

.progress-bar-container {
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  transition: width 0.3s;
}

.progress-bar-fill.excellent {
  background: linear-gradient(90deg, #16a34a, #22c55e);
}

.progress-bar-fill.good {
  background: linear-gradient(90deg, #0ea5e9, #38bdf8);
}

.progress-bar-fill.warning {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
}

.progress-bar-fill.critical {
  background: linear-gradient(90deg, #ef4444, #f87171);
}

.process-loading {
  text-align: center;
  padding: 20px;
  color: #64748b;
  font-size: 13px;
}

.process-error {
  text-align: center;
  padding: 20px;
  color: #b91c1c;
  font-size: 13px;
}

/* ローディング */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #e2e8f0;
  border-top-color: #4a7ae5;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

