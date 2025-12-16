<template>
  <div class="monitor-container">
    <div class="toolbar">
      <h2 class="page-title">ライン稼働監視</h2>
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

    <!-- ライン状態一覧 -->
    <div class="lines-section">
      <div class="section-header">
        <h3>ライン状態</h3>
        <span class="update-time">最終更新: {{ lastUpdate }}</span>
      </div>

      <div class="lines-grid">
        <div
          v-for="line in lines"
          :key="line.line"
          class="line-card"
          :class="getLineCardClass(line.current_state)"
        >
          <!-- カードヘッダー -->
          <div class="line-card__header">
            <div class="line-name">{{ line.line_name }}</div>
            <span class="state-badge" :class="getStateBadgeClass(line.current_state)">
              {{ line.state_display }}
            </span>
          </div>

          <!-- メトリクス -->
          <div class="line-card__metrics">
            <div class="metric-row">
              <span class="metric-label">本日計画</span>
              <span class="metric-value">{{ formatNumber(line.today_plan) }}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">本日実績</span>
              <span class="metric-value highlight">{{ formatNumber(line.today_output) }}</span>
            </div>
            <div class="metric-row">
              <span class="metric-label">達成率</span>
              <span
                class="metric-value"
                :class="getAchievementClass(line.achievement_rate)"
              >
                {{ line.achievement_rate }}%
              </span>
            </div>
            <div class="metric-row">
              <span class="metric-label">進捗</span>
              <span class="metric-value">{{ line.progress }}%</span>
            </div>
          </div>

          <!-- 現在生産中 -->
          <div v-if="line.current_product_code" class="line-card__current">
            <div class="current-label">現在生産中</div>
            <div class="current-product">{{ line.current_product_code }}</div>
            <div class="current-name">{{ line.current_product_name }}</div>
          </div>
          <div v-else class="line-card__current empty">
            <div class="current-label">待機中</div>
          </div>

          <!-- 進捗バー -->
          <div class="progress-bar-container">
            <div
              class="progress-bar-fill"
              :style="{ width: Math.min(line.progress, 100) + '%' }"
              :class="getProgressBarClass(line.progress)"
            ></div>
          </div>
        </div>
      </div>

      <div v-if="!lines.length" class="no-data">
        ライン情報がありません
      </div>
    </div>

    <!-- ローディング -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '@/api/client'

const lines = ref([])
const loading = ref(false)
const autoRefresh = ref(true)
const lastUpdate = ref('')
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
    const res = await api.lineRealtime.getLineStatuses()
    lines.value = res.data || []
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

// ヘルパー関数
const formatNumber = (value) => {
  if (value === null || value === undefined) return '0'
  return Number(value).toLocaleString()
}

const getLineCardClass = (state) => {
  return `state-${state.toLowerCase()}`
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

.lines-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

/* ラインカード */
.line-card {
  border: 1px solid #d7dfe8;
  border-radius: 6px;
  border-left: 4px solid #cbd5e1;
  padding: 12px;
  background: #f8fafc;
  transition: all 0.3s;
}

.line-card.state-running {
  border-left-color: #16a34a;
  background: #f0fdf4;
}

.line-card.state-breakdown {
  border-left-color: #ef4444;
  background: #fef2f2;
  animation: pulse-red 2s infinite;
}

.line-card.state-maintenance {
  border-left-color: #f59e0b;
  background: #fffbeb;
}

.line-card.state-setup {
  border-left-color: #0ea5e9;
  background: #f0f9ff;
}

@keyframes pulse-red {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.8; }
}

.line-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.line-name {
  font-size: 15px;
  font-weight: 700;
  color: #1f2a44;
}

.state-badge {
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
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

.line-card__metrics {
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

.line-card__current {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
}

.line-card__current.empty {
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

.no-data {
  text-align: center;
  color: #94a3b8;
  padding: 40px 20px;
  font-size: 14px;
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
