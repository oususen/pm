<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">長期負荷チャート <DataSourceDialog title="長期負荷チャート" :sources="dsSources" /></h1>
        <p class="helper-text">顧客需要 × ラインサイクルタイムから、H/日を棒グラフ・負荷時間(h)を折れ線で表示（工程負荷は設備台数反映後）</p>
      </div>
      <div class="page-actions">
        <button v-if="result" class="btn-secondary" @click="exportExcel">Excel出力</button>
        <router-link to="/production/actual-cycle-time" class="btn-secondary">出来高集計</router-link>
        <router-link to="/production/line-cycle-time" class="btn-secondary">サイクルタイム入力</router-link>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-row">
          <div class="filter-field">
            <label>開始日</label>
            <input type="date" v-model="filters.startDate" />
          </div>
          <div class="filter-field">
            <label>期間</label>
            <select v-model="filters.period" @change="applyPeriod">
              <option value="3m">3ヶ月</option>
              <option value="6m">6ヶ月</option>
              <option value="1y">1年</option>
              <option value="custom">カスタム</option>
            </select>
          </div>
          <div v-if="filters.period === 'custom'" class="filter-field">
            <label>終了日</label>
            <input type="date" v-model="filters.endDate" />
          </div>
          <div class="filter-field">
            <label>集計</label>
            <select v-model="filters.aggregate">
              <option value="daily">日別</option>
              <option value="weekly">週別</option>
              <option value="monthly">月別</option>
            </select>
          </div>
          <div class="filter-actions">
            <button class="btn-primary" @click="loadData" :disabled="loading || !hasSelection">
              {{ loading ? '計算中...' : '計算' }}
            </button>
            <div class="settings-anchor">
              <button class="btn-secondary" @click="toggleDemandConfig">
                需要設定
              </button>
              <div class="demand-summary-inline">{{ demandSourceSummary }}</div>
              <div v-if="demandConfigOpen" class="settings-popover">
                <div class="settings-popover-title">需要ソース切替</div>
                <div class="settings-field">
                  <label>OrderLine使用最終日</label>
                  <input type="date" v-model="orderLineUntilDate" />
                </div>
                <p class="settings-helper">
                  指定日までは受注明細 `OrderLine`、翌日以後は `LineDemand` を使います。未設定なら全期間 `LineDemand` です。
                </p>
                <p v-if="!canEditDemandConfig" class="settings-helper warning">
                  この設定を保存できるのは管理者のみです。
                </p>
                <div class="settings-actions">
                  <button class="btn-link" @click="clearDemandConfig" :disabled="demandConfigSaving || !canEditDemandConfig">クリア</button>
                  <button class="btn-primary" @click="saveDemandConfig" :disabled="demandConfigSaving || !canEditDemandConfig">
                    {{ demandConfigSaving ? '保存中...' : '保存' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- グループ選択 -->
        <div class="filter-row">
          <div class="filter-field wide">
            <label>グループ選択</label>
            <div class="line-chips">
              <label v-for="g in groups" :key="g.id" class="chip-label">
                <input type="checkbox" v-model="selectedGroupIds" :value="g.id" />
                <span class="chip chip-group">{{ g.name }}</span>
              </label>
            </div>
          </div>
        </div>

        <!-- ライン個別選択 -->
        <div class="filter-row">
          <div class="filter-field wide">
            <label>ライン個別選択</label>
            <div class="line-chips">
              <label v-for="line in prodLines" :key="line.id" class="chip-label">
                <input type="checkbox" v-model="selectedLineIds" :value="line.id" />
                <span class="chip">{{ line.line_code }}</span>
              </label>
              <button class="btn-link" @click="selectAllLines">全選択</button>
              <button class="btn-link" @click="clearAll">全解除</button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="result" class="chart-area">
        <!-- グループ集計 -->
        <div v-for="gc in groupCharts" :key="'g-' + gc.groupId" class="line-chart-block group-block">
          <h3 class="line-title group-title">{{ gc.groupName }}（{{ gc.lines.length }}ライン合算）</h3>
          <div class="chart-legend-inline" style="--legend-line-color:#8e44ad;">
            <span class="chart-legend-item"><span class="legend-bar-swatch"></span>H/日</span>
            <span class="chart-legend-item"><span class="legend-line-swatch"></span>負荷(h)</span>
          </div>
          <div class="chart-canvas">
            <div class="y-axis left-axis">
              <div class="y-axis-label top">{{ formatPerDayAxisLabel(chartAxes(gc.data).leftMaxHours) }}h/日</div>
              <div class="y-axis-label mid">{{ formatPerDayAxisLabel(chartAxes(gc.data).leftMaxHours / 2) }}h/日</div>
              <div class="y-axis-label bottom">0h/日</div>
            </div>
            <div class="bar-chart-wrapper">
              <div class="bar-chart" :style="chartWidthStyle(gc.data.length)">
                <div class="chart-guides">
                  <div class="chart-guide top"></div>
                  <div class="chart-guide mid"></div>
                  <div class="chart-guide bottom"></div>
                </div>
                <svg
                  class="line-overlay"
                  :style="[chartOverlayStyle(gc.data.length), { color: '#8e44ad' }]"
                  :viewBox="`0 0 ${chartPlotWidth(gc.data.length)} ${CHART_BODY_HEIGHT}`"
                  preserveAspectRatio="none"
                  aria-hidden="true"
                >
                  <path v-if="gc.data.length > 1" :d="buildLoadLinePath(gc.data, chartAxes(gc.data).rightMaxSec)" class="line-path"></path>
                  <circle
                    v-for="(point, index) in buildLoadLinePoints(gc.data, chartAxes(gc.data).rightMaxSec)"
                    :key="`group-point-${gc.groupId}-${index}`"
                    class="line-point"
                    :cx="point.x"
                    :cy="point.y"
                    r="3"
                  ></circle>
                </svg>
                <div
                  v-for="d in gc.data"
                  :key="d.date"
                  class="bar-col"
                  @mouseenter="showTooltip($event, gc.groupName, d)"
                  @mouseleave="hideTooltip"
                >
                  <div class="bar-label-stack">
                    <div class="bar-label-top">{{ formatFinishedQty(d.finished_qty) }}台</div>
                    <div class="bar-label-top">{{ formatLoadHours(d.line_load_sec) }}h</div>
                  </div>
                  <div class="bar-track">
                    <div class="bar-fill per-day-bar" :style="barStyle(d, '#60a5fa', chartAxes(gc.data).leftMaxHours)"></div>
                  </div>
                  <div class="bar-label">{{ formatDateLabel(d) }}</div>
                </div>
              </div>
            </div>
            <div class="y-axis right-axis">
              <div class="y-axis-label top">{{ formatLoadHours(chartAxes(gc.data).rightMaxSec) }}h</div>
              <div class="y-axis-label mid">{{ formatLoadHours(chartAxes(gc.data).rightMaxSec / 2) }}h</div>
              <div class="y-axis-label bottom">0h</div>
            </div>
          </div>
        </div>

        <!-- ライン個別 -->
        <div v-for="line in result.lines" :key="line.line_id" class="line-chart-block">
          <h3 class="line-title">{{ line.line_code }} {{ line.line_name }}</h3>
          <div v-if="lineWarning(line)" class="calendar-warning">
            ⚠ {{ lineWarning(line) }}
          </div>
          <div class="chart-legend-inline" style="--legend-line-color:#e74c3c;">
            <span class="chart-legend-item"><span class="legend-bar-swatch"></span>H/日</span>
            <span class="chart-legend-item"><span class="legend-line-swatch"></span>負荷(h)</span>
          </div>
          <div class="chart-canvas">
            <div class="y-axis left-axis">
              <div class="y-axis-label top">{{ formatPerDayAxisLabel(chartAxes(lineDisplayData(line)).leftMaxHours) }}h/日</div>
              <div class="y-axis-label mid">{{ formatPerDayAxisLabel(chartAxes(lineDisplayData(line)).leftMaxHours / 2) }}h/日</div>
              <div class="y-axis-label bottom">0h/日</div>
            </div>
            <div class="bar-chart-wrapper">
              <div class="bar-chart" :style="chartWidthStyle(lineDisplayData(line).length)">
                <div class="chart-guides">
                  <div class="chart-guide top"></div>
                  <div class="chart-guide mid"></div>
                  <div class="chart-guide bottom"></div>
                </div>
                <svg
                  class="line-overlay"
                  :style="[chartOverlayStyle(lineDisplayData(line).length), { color: '#e74c3c' }]"
                  :viewBox="`0 0 ${chartPlotWidth(lineDisplayData(line).length)} ${CHART_BODY_HEIGHT}`"
                  preserveAspectRatio="none"
                  aria-hidden="true"
                >
                  <path v-if="lineDisplayData(line).length > 1" :d="buildLoadLinePath(lineDisplayData(line), chartAxes(lineDisplayData(line)).rightMaxSec)" class="line-path"></path>
                  <circle
                    v-for="(point, index) in buildLoadLinePoints(lineDisplayData(line), chartAxes(lineDisplayData(line)).rightMaxSec)"
                    :key="`line-point-${line.line_id}-${index}`"
                    class="line-point"
                    :cx="point.x"
                    :cy="point.y"
                    r="3"
                  ></circle>
                </svg>
                <div
                  v-for="d in lineDisplayData(line)"
                  :key="d.date"
                  class="bar-col"
                  @mouseenter="showTooltip($event, `${line.line_code} ${line.line_name}`, d)"
                  @mouseleave="hideTooltip"
                >
                  <div class="bar-label-stack">
                    <div class="bar-label-top">{{ formatFinishedQty(d.finished_qty) }}台</div>
                    <div class="bar-label-top">{{ formatLoadHours(d.line_load_sec) }}h</div>
                  </div>
                  <div class="bar-track">
                    <div class="bar-fill per-day-bar" :style="barStyle(d, '#60a5fa', chartAxes(lineDisplayData(line)).leftMaxHours)"></div>
                  </div>
                  <div class="bar-label">{{ formatDateLabel(d) }}</div>
                </div>
              </div>
            </div>
            <div class="y-axis right-axis">
              <div class="y-axis-label top">{{ formatLoadHours(chartAxes(lineDisplayData(line)).rightMaxSec) }}h</div>
              <div class="y-axis-label mid">{{ formatLoadHours(chartAxes(lineDisplayData(line)).rightMaxSec / 2) }}h</div>
              <div class="y-axis-label bottom">0h</div>
            </div>
          </div>
          <div v-if="lineProcesses(line).length" class="process-chart-list">
            <div
              v-for="proc in lineProcesses(line)"
              :key="`${line.line_id}_${proc.process_id}`"
              class="process-chart-block"
            >
              <h4 class="process-title">
                {{ proc.process_code }} {{ proc.process_name }}
                <span v-if="proc.equipment_count > 1" class="process-note">（{{ proc.equipment_count }}台で按分）</span>
              </h4>
              <div class="chart-legend-inline" style="--legend-line-color:#2563eb;">
                <span class="chart-legend-item"><span class="legend-bar-swatch"></span>H/日</span>
                <span class="chart-legend-item"><span class="legend-line-swatch"></span>負荷(h)</span>
              </div>
              <div class="chart-canvas">
                <div class="y-axis left-axis">
                  <div class="y-axis-label top">{{ formatPerDayAxisLabel(chartAxes(processDisplayData(line, proc), { fixedLeftMaxHours: 24 }).leftMaxHours) }}h/日</div>
                  <div class="y-axis-label mid">{{ formatPerDayAxisLabel(chartAxes(processDisplayData(line, proc), { fixedLeftMaxHours: 24 }).leftMaxHours / 2) }}h/日</div>
                  <div class="y-axis-label bottom">0h/日</div>
                </div>
                <div class="bar-chart-wrapper">
                  <div class="bar-chart process-bar-chart" :style="chartWidthStyle(processDisplayData(line, proc).length)">
                    <div class="chart-guides">
                      <div class="chart-guide top"></div>
                      <div class="chart-guide mid"></div>
                      <div class="chart-guide bottom"></div>
                    </div>
                    <svg
                      class="line-overlay"
                      :style="[chartOverlayStyle(processDisplayData(line, proc).length), { color: '#2563eb' }]"
                      :viewBox="`0 0 ${chartPlotWidth(processDisplayData(line, proc).length)} ${CHART_BODY_HEIGHT}`"
                      preserveAspectRatio="none"
                      aria-hidden="true"
                    >
                      <path v-if="processDisplayData(line, proc).length > 1" :d="buildLoadLinePath(processDisplayData(line, proc), chartAxes(processDisplayData(line, proc), { fixedLeftMaxHours: 24 }).rightMaxSec)" class="line-path"></path>
                      <circle
                        v-for="(point, index) in buildLoadLinePoints(processDisplayData(line, proc), chartAxes(processDisplayData(line, proc), { fixedLeftMaxHours: 24 }).rightMaxSec)"
                        :key="`proc-point-${line.line_id}-${proc.process_id}-${index}`"
                        class="line-point"
                        :cx="point.x"
                        :cy="point.y"
                        r="3"
                      ></circle>
                    </svg>
                    <div
                      v-for="d in processDisplayData(line, proc)"
                      :key="`${proc.process_id}_${d.date}`"
                      class="bar-col"
                      @mouseenter="showTooltip($event, `${line.line_code} ${line.line_name} / ${proc.process_code} ${proc.process_name}`, d)"
                      @mouseleave="hideTooltip"
                    >
                      <div class="bar-label-stack">
                        <div class="bar-label-top">{{ formatFinishedQty(d.finished_qty) }}台</div>
                        <div class="bar-label-top">{{ formatLoadHours(d.line_load_sec) }}h</div>
                      </div>
                      <div class="bar-track">
                        <div class="bar-fill per-day-bar" :style="barStyle(d, '#93c5fd', chartAxes(processDisplayData(line, proc), { fixedLeftMaxHours: 24 }).leftMaxHours)"></div>
                      </div>
                      <div class="bar-label">{{ formatDateLabel(d) }}</div>
                    </div>
                  </div>
                </div>
                <div class="y-axis right-axis">
                  <div class="y-axis-label top">{{ formatLoadHours(chartAxes(processDisplayData(line, proc), { fixedLeftMaxHours: 24 }).rightMaxSec) }}h</div>
                  <div class="y-axis-label mid">{{ formatLoadHours(chartAxes(processDisplayData(line, proc), { fixedLeftMaxHours: 24 }).rightMaxSec / 2) }}h</div>
                  <div class="y-axis-label bottom">0h</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!result && !loading" class="empty-state">
        グループまたはラインを選択して「計算」を押してください
      </div>
    </div>

    <div v-if="tooltip.visible" class="chart-tooltip" :style="{ top: tooltip.y + 'px', left: tooltip.x + 'px' }">
      <div class="tooltip-title">{{ tooltip.line }} / {{ tooltip.date }}</div>
      <div class="tooltip-row">完成品: {{ formatFinishedQty(tooltip.finishedQty) }}台</div>
      <div class="tooltip-row">H/日: {{ formatTooltipPerDayHours(tooltip.perDayHours) }}</div>
      <div class="tooltip-row">負荷: {{ formatHours(tooltip.loadMin) }}h</div>
      <div v-for="p in tooltip.processes" :key="p.process_code" class="tooltip-row">
        {{ p.process_code }} {{ p.process_name }}:
        <template v-if="p.equipment_count > 1">
          {{ formatHours(p.raw_load_min) }}h ÷ {{ p.equipment_count }}台 = {{ formatHours(p.load_min) }}h
        </template>
        <template v-else>
          {{ formatHours(p.load_min) }}h
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import ExcelJS from 'exceljs'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const LINE_LOAD_DEMAND_SOURCE_CONFIG_KEY = 'production.line_load_demand_source_config'
const dsSources = [
  { op: '読み取り', table: 'm_line', desc: 'ライン個別選択の候補' },
  { op: '読み取り', table: 'accounts_unit / accounts_unit_line_mapping', desc: 'グループ選択とライン紐付け' },
  { op: '設定読み書き', table: 'system_settings', desc: '長期負荷チャートの需要ソース切替設定' },
  { op: '負荷計算', table: 't_order_line', desc: '切替日以前の最終品需要（受注明細）' },
  { op: '負荷計算', table: 't_line_demand', desc: '最終品の需要数量（内示 + 確定）' },
  { op: '負荷計算', table: 'm_line_cycle_time', desc: 'ライン別サイクルタイム（秒/個）' },
  { op: '参照', table: 'm_line / m_calendar_day', desc: 'ライン勤務カレンダと稼働分' },
]

const loading = ref(false)
const prodLines = ref([])
const groups = ref([])
const unitLineMappings = ref([])
const selectedLineIds = ref([])
const selectedGroupIds = ref([])
const result = ref(null)
const demandConfigOpen = ref(false)
const demandConfigSaving = ref(false)
const demandConfigExists = ref(false)
const orderLineUntilDate = ref('')

const today = new Date()
const addMonths = (date, months) => {
  const d = new Date(date)
  d.setMonth(d.getMonth() + months)
  return d.toISOString().slice(0, 10)
}
const filters = reactive({
  startDate: today.toISOString().slice(0, 10),
  endDate: addMonths(today, 6),
  period: '6m',
  aggregate: 'monthly',
})

const applyPeriod = () => {
  const base = new Date(filters.startDate)
  if (filters.period === '3m') filters.endDate = addMonths(base, 3)
  else if (filters.period === '6m') filters.endDate = addMonths(base, 6)
  else if (filters.period === '1y') filters.endDate = addMonths(base, 12)
}

watch(() => filters.startDate, () => {
  if (filters.period !== 'custom') applyPeriod()
})

const tooltip = reactive({
  visible: false, x: 0, y: 0,
  line: '', date: '', availMin: 0, loadMin: 0, utilization: 0, perDayHours: null, finishedQty: 0, processes: [],
})

const CHART_BODY_HEIGHT = 120
const BAR_COLUMN_WIDTH = 36
const CHART_COLUMN_GAP = 2

onMounted(async () => {
  const [linesRes, groupsRes, mappingsRes] = await Promise.all([
    api.lines.getLines({ is_active: true, line_type: 'PROD' }),
    api.accounts.getUnits({ page_size: 200 }),
    api.accounts.getUnitLineMappings({ page_size: 20000 }),
  ])
  prodLines.value = (linesRes.data.results || linesRes.data).sort((a, b) => a.line_code.localeCompare(b.line_code))
  groups.value = Array.isArray(groupsRes.data) ? groupsRes.data : (groupsRes.data.results || [])
  unitLineMappings.value = Array.isArray(mappingsRes.data) ? mappingsRes.data : (mappingsRes.data.results || [])
  await loadDemandConfig()
})

const canEditDemandConfig = computed(() => Boolean(authState.user?.is_staff || authState.user?.is_superuser))

const parseDemandConfigValue = (rawValue) => {
  if (!rawValue) return ''
  try {
    const payload = JSON.parse(rawValue)
    if (payload && typeof payload === 'object' && payload.orderline_until_date) {
      return String(payload.orderline_until_date)
    }
  } catch (_error) {
    if (/^\d{4}-\d{2}-\d{2}$/.test(String(rawValue))) {
      return String(rawValue)
    }
  }
  return ''
}

const demandSourceSummary = computed(() => (
  orderLineUntilDate.value
    ? `orderline受注基準は ${orderLineUntilDate.value} まで、それ以降は受注展開結果line_demand基準、設定は左の「需要設定」ボタンから変更可能`
    : '受注基準の設定なし'
))

const loadDemandConfig = async () => {
  try {
    const res = await api.systemSettings.getAll()
    const row = res.data?.[LINE_LOAD_DEMAND_SOURCE_CONFIG_KEY]
    demandConfigExists.value = Boolean(row)
    orderLineUntilDate.value = parseDemandConfigValue(row?.value)
  } catch (error) {
    console.error('長期負荷チャート需要設定の取得に失敗しました', error)
    demandConfigExists.value = false
    orderLineUntilDate.value = ''
  }
}

const toggleDemandConfig = () => {
  demandConfigOpen.value = !demandConfigOpen.value
}

const saveDemandConfig = async () => {
  if (!canEditDemandConfig.value) return
  demandConfigSaving.value = true
  try {
    const value = JSON.stringify({
      orderline_until_date: orderLineUntilDate.value || null,
    })
    if (demandConfigExists.value) {
      await api.systemSettings.updateByKey({
        [LINE_LOAD_DEMAND_SOURCE_CONFIG_KEY]: value,
      })
    } else {
      await api.systemSettings.create({
        key: LINE_LOAD_DEMAND_SOURCE_CONFIG_KEY,
        value,
        description: '長期負荷チャートの需要ソース切替設定',
      })
      demandConfigExists.value = true
    }
    alert('保存しました。')
    demandConfigOpen.value = false
    await loadDemandConfig()
  } catch (error) {
    console.error('長期負荷チャート需要設定の保存に失敗しました', error)
    alert(error?.response?.data?.detail || '保存に失敗しました。')
  } finally {
    demandConfigSaving.value = false
  }
}

const clearDemandConfig = async () => {
  orderLineUntilDate.value = ''
  await saveDemandConfig()
}

const groupLineMap = computed(() => {
  const map = {}
  for (const m of unitLineMappings.value) {
    if (!map[m.unit]) map[m.unit] = []
    map[m.unit].push(m.line)
  }
  return map
})

const allSelectedLineIds = computed(() => {
  const ids = new Set(selectedLineIds.value)
  for (const gid of selectedGroupIds.value) {
    for (const lid of (groupLineMap.value[gid] || [])) {
      ids.add(lid)
    }
  }
  return [...ids]
})

const hasSelection = computed(() => allSelectedLineIds.value.length > 0)

const selectAllLines = () => { selectedLineIds.value = prodLines.value.map(l => l.id) }
const clearAll = () => { selectedLineIds.value = []; selectedGroupIds.value = [] }

const loadData = async () => {
  if (!allSelectedLineIds.value.length) return
  loading.value = true
  try {
    const res = await api.lineLoad.calculate({
      line_ids: allSelectedLineIds.value,
      start_date: filters.startDate,
      end_date: filters.endDate,
      aggregate: filters.aggregate,
    })
    result.value = res.data
  } catch (e) {
    alert('計算エラー: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const groupCharts = computed(() => {
  if (!result.value) return []
  const charts = []
  for (const gid of selectedGroupIds.value) {
    const group = groups.value.find(g => g.id === gid)
    if (!group) continue
    const lineIds = groupLineMap.value[gid] || []
    const lines = result.value.lines.filter(l => lineIds.includes(l.line_id))
    if (!lines.length) continue

    const dateMap = {}
    for (const line of lines) {
      for (const d of lineDisplayData(line)) {
        if (!dateMap[d.date]) {
          dateMap[d.date] = { available_min: 0, load_sec: 0, finished_qty: 0, working_days: 0, month_label: d.month_label, week_label: d.week_label }
        }
        dateMap[d.date].available_min += d.available_min
        dateMap[d.date].load_sec += d.line_load_sec
        dateMap[d.date].finished_qty += Number(d.finished_qty || 0)
        dateMap[d.date].working_days = Math.max(dateMap[d.date].working_days, d.working_days || 0)
      }
    }

    const data = Object.entries(dateMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, v]) => ({
        date,
        month_label: v.month_label,
        week_label: v.week_label,
        available_min: v.available_min,
        finished_qty: Math.round(v.finished_qty * 1000) / 1000,
        line_load_sec: v.load_sec,
        line_load_min: Math.round(v.load_sec / 60 * 10) / 10,
        working_days: v.working_days || 0,
        utilization: v.available_min > 0 ? Math.round(v.load_sec / (v.available_min * 60) * 1000) / 10 : 0,
        is_working_day: true,
        processes: [],
      }))

    charts.push({ groupId: gid, groupName: group.name, lines: lineIds, data })
  }
  return charts
})

const lineHasCalendar = (line) => {
  return line.data.some(d => d.available_min > 0)
}

const lineHasLoad = (line) => {
  return line.data.some(d => d.line_load_sec > 0)
}

const lineWarning = (line) => {
  const hasCal = lineHasCalendar(line)
  const hasLoad = lineHasLoad(line)
  if (!hasCal && hasLoad) return 'カレンダー未設定です。折れ線の負荷時間(h)のみ表示し、H/日の棒は表示できません'
  if (!hasCal && !hasLoad) return 'カレンダー未設定・負荷データなし'
  return ''
}

const lineDisplayData = (line) => {
  if (lineHasCalendar(line)) return line.data.filter(x => x.is_working_day)
  return line.data.filter(x => x.line_load_sec > 0)
}

const formatLoadHours = (sec) => {
  return Math.round((sec || 0) / 3600 * 10) / 10
}

const lineProcesses = (line) => {
  const seen = new Map()
  for (const d of line.data) {
    for (const p of (d.processes || [])) {
      if (!seen.has(p.process_id)) {
        seen.set(p.process_id, {
          process_id: p.process_id,
          process_code: p.process_code,
          process_name: p.process_name,
          equipment_count: p.equipment_count || 1,
        })
      }
    }
  }
  return [...seen.values()].sort((a, b) => a.process_code.localeCompare(b.process_code))
}

const processDisplayData = (line, proc) => {
  const baseData = lineDisplayData(line)
  return baseData.map((d) => {
    const detail = (d.processes || []).find(p => p.process_id === proc.process_id)
    const rawLoadSec = detail?.raw_load_sec ?? 0
    const rawLoadMin = detail?.raw_load_min ?? 0
    const loadSec = detail?.load_sec ?? 0
    const loadMin = detail?.load_min ?? 0
    const utilization = detail?.utilization ?? 0
    return {
      date: d.date,
      month_label: d.month_label,
      week_label: d.week_label,
      available_min: d.available_min,
      finished_qty: Number(detail?.finished_qty || 0),
      line_load_sec: loadSec,
      line_load_min: loadMin,
      working_days: d.working_days || 0,
      utilization,
      is_working_day: d.is_working_day,
      processes: [{
        process_id: proc.process_id,
        process_code: proc.process_code,
        process_name: proc.process_name,
        equipment_count: proc.equipment_count || 1,
        raw_load_sec: rawLoadSec,
        raw_load_min: rawLoadMin,
        load_sec: loadSec,
        load_min: loadMin,
        utilization,
      }],
    }
  })
}

const barStyle = (d, color = '#e74c3c', maxPerDayHours = 1) => {
  const perDayHours = getPerDayHours(d)
  const pct = perDayHours === null ? 0 : (perDayHours / Math.max(Number(maxPerDayHours) || 0, 1)) * 100
  return { height: pct + '%', minHeight: pct > 0 ? '1px' : '0', backgroundColor: color }
}

const getPerDayHours = (d) => {
  const workingDays = Number(d?.working_days || 0)
  if (workingDays <= 0) return null
  const loadSec = Number(d?.line_load_sec || 0)
  return Math.round((loadSec / 3600 / workingDays) * 10) / 10
}

const formatPerDayAxisLabel = (hours) => {
  const safeHours = Number(hours || 0)
  return Math.round(safeHours * 10) / 10
}

const formatTooltipPerDayHours = (hours) => {
  if (hours === null || hours === undefined) return '-'
  return formatPerDayAxisLabel(hours)
}

const chartAxes = (items, options = {}) => {
  const fixedLeftMaxHours = options.fixedLeftMaxHours ?? null
  let leftMaxHours = fixedLeftMaxHours
  let rightMaxSec = 0

  if (leftMaxHours === null) {
    leftMaxHours = 0
    for (const item of (items || [])) {
      const perDayHours = getPerDayHours(item)
      if (perDayHours !== null && perDayHours > leftMaxHours) leftMaxHours = perDayHours
    }
  }

  for (const item of (items || [])) {
    const loadSec = Number(item?.line_load_sec || 0)
    if (loadSec > rightMaxSec) rightMaxSec = loadSec
  }

  return {
    leftMaxHours: Math.max(Number(leftMaxHours) || 0, 1),
    rightMaxSec: Math.max(rightMaxSec, 3600),
  }
}

const chartPlotWidth = (count) => {
  if (!count) return 0
  return count * BAR_COLUMN_WIDTH + Math.max(count - 1, 0) * CHART_COLUMN_GAP
}

const chartWidthStyle = (count) => ({
  width: `${chartPlotWidth(count)}px`,
})

const chartOverlayStyle = (count) => ({
  width: `${chartPlotWidth(count)}px`,
})

const buildLoadLinePoints = (items, maxLoadSec = 3600) => {
  if (!items?.length) return []
  return items.map((item, index) => {
    const x = index * (BAR_COLUMN_WIDTH + CHART_COLUMN_GAP) + (BAR_COLUMN_WIDTH / 2)
    const ratio = Math.max(0, Math.min(1, Number(item?.line_load_sec || 0) / Math.max(Number(maxLoadSec) || 0, 3600)))
    const y = CHART_BODY_HEIGHT - (ratio * CHART_BODY_HEIGHT)
    return { x, y }
  })
}

const buildLoadLinePath = (items, maxLoadSec = 3600) => {
  const points = buildLoadLinePoints(items, maxLoadSec)
  if (!points.length) return ''
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
}

const formatDateLabel = (d) => {
  if (d.month_label) return d.month_label
  if (d.week_label) return d.week_label
  return d.date.slice(5)
}

const formatHours = (minutes) => {
  const hours = (Number(minutes) || 0) / 60
  return Math.round(hours * 10) / 10
}

const formatFinishedQty = (qty) => {
  const safeQty = Number(qty || 0)
  return Number.isInteger(safeQty) ? String(safeQty) : String(Math.round(safeQty * 10) / 10)
}

const formatExcelHours = (minutes) => {
  const hours = (Number(minutes) || 0) / 60
  return Number(hours.toFixed(2))
}

const formatExcelHoursPerDay = (minutes, workingDays) => {
  if (!workingDays) return ''
  const hours = (Number(minutes) || 0) / 60
  return Number((hours / workingDays).toFixed(2))
}

const formatExcelQty = (qty) => {
  const safeQty = Number(qty || 0)
  if (!Number.isFinite(safeQty)) return ''
  if (Math.abs(safeQty - Math.round(safeQty)) < 0.000001) return Math.round(safeQty)
  return Number(safeQty.toFixed(3))
}

const formatExcelDateTime = (date = new Date()) => {
  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mi = String(date.getMinutes()).padStart(2, '0')
  return `${yyyy}/${mm}/${dd} ${hh}:${mi}`
}

const getExportUserName = async () => {
  await ensureAuth()
  const user = authState.user
  if (!user) return '不明'
  return `${user.last_name || ''} ${user.first_name || ''}`.trim()
    || user.display_name
    || user.username
    || user.email
    || '不明'
}

const toExcelArgb = (hex) => `FF${String(hex || '#ffffff').replace('#', '').toUpperCase()}`

const makeExcelBorder = (thick = false, color = '#b8c2cc') => ({
  style: thick ? 'medium' : 'thin',
  color: { argb: toExcelArgb(color) },
})

const applyExcelCellStyle = (cell, {
  align = 'center',
  bold = false,
  color = '#1f2937',
  bg = '#ffffff',
  numFmt = null,
  wrapText = false,
  thickLeft = false,
  thickRight = false,
  thickTop = false,
  thickBottom = false,
} = {}) => {
  cell.font = {
    bold,
    name: 'Meiryo',
    size: 10,
    color: { argb: toExcelArgb(color) },
  }
  cell.alignment = {
    horizontal: align,
    vertical: 'middle',
    wrapText,
  }
  cell.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: toExcelArgb(bg) },
  }
  cell.border = {
    top: makeExcelBorder(thickTop),
    left: makeExcelBorder(thickLeft),
    right: makeExcelBorder(thickRight),
    bottom: makeExcelBorder(thickBottom),
  }
  if (numFmt) {
    cell.numFmt = numFmt
  }
}

const setWorksheetColumns = (worksheet, cols) => {
  cols.forEach((col, index) => {
    worksheet.getColumn(index + 1).width = (col?.wch || col?.width || 10) + 1
  })
}

const writeSheetRows = (worksheet, startRow, rows) => {
  rows.forEach((row, rowIndex) => {
    row.forEach((value, colIndex) => {
      worksheet.getCell(startRow + rowIndex, colIndex + 1).value = value
    })
  })
}

const decorateSheetHeader = (worksheet, title, totalCols, userName) => {
  const aggLabel = filters.aggregate === 'monthly' ? '月別' : filters.aggregate === 'weekly' ? '週別' : '日別'
  const safeCols = Math.max(totalCols, 4)
  worksheet.mergeCells(1, 1, 1, safeCols)
  worksheet.getCell(1, 1).value = title
  applyExcelCellStyle(worksheet.getCell(1, 1), {
    align: 'left',
    bold: true,
    color: '#1f2937',
    bg: '#dce6f1',
    thickBottom: true,
  })
  worksheet.getRow(1).height = 24

  const metaRows = [
    ['作成日', formatExcelDateTime(), '作成者', userName],
    ['開始日', filters.startDate, '終了日', filters.endDate],
    ['集計', aggLabel, '画面', '長期負荷チャート'],
  ]
  metaRows.forEach((values, index) => {
    const rowNo = index + 2
    values.forEach((value, colIndex) => {
      const isLabel = colIndex % 2 === 0
      worksheet.getCell(rowNo, colIndex + 1).value = value
      applyExcelCellStyle(worksheet.getCell(rowNo, colIndex + 1), {
        align: isLabel ? 'center' : 'left',
        bold: isLabel,
        bg: isLabel ? '#eef3f8' : '#ffffff',
      })
    })
    worksheet.getRow(rowNo).height = 19
  })
  worksheet.getRow(5).height = 8
}

const styleSimpleTable = (worksheet, startRow, rowCount, colCount, options = {}) => {
  const headerBg = options.headerBg || '#5b9bd5'
  const headerColor = options.headerColor || '#ffffff'
  const integerCols = new Set(options.integerCols || [])
  const decimalCols = new Set(options.decimalCols || [])
  const leftAlignCols = new Set(options.leftAlignCols || [])
  const decimalNumFmt = options.decimalNumFmt || '0.00'

  for (let col = 1; col <= colCount; col += 1) {
    applyExcelCellStyle(worksheet.getCell(startRow, col), {
      bold: true,
      color: headerColor,
      bg: headerBg,
      thickTop: true,
      thickBottom: true,
    })
  }

  for (let row = startRow + 1; row < startRow + rowCount; row += 1) {
    const zebraBg = row % 2 === 0 ? '#f8fbff' : '#ffffff'
    for (let col = 1; col <= colCount; col += 1) {
      const cell = worksheet.getCell(row, col)
      const numFmt = integerCols.has(col) ? '0' : decimalCols.has(col) ? decimalNumFmt : null
      applyExcelCellStyle(cell, {
        align: leftAlignCols.has(col) ? 'left' : numFmt ? 'right' : 'center',
        bg: zebraBg,
        numFmt,
      })
    }
  }
}

const styleMonthlyLoadTable = (worksheet, startRow, dates, rowCount) => {
  const colCount = 1 + (dates.length * 3)
  for (let col = 1; col <= colCount; col += 1) {
    const isMonthEndCol = col > 1 && ((col - 1) % 3 === 0)
    applyExcelCellStyle(worksheet.getCell(startRow, col), {
      bold: true,
      color: '#ffffff',
      bg: '#4472c4',
      thickTop: true,
      thickBottom: true,
      thickRight: isMonthEndCol,
    })
    applyExcelCellStyle(worksheet.getCell(startRow + 1, col), {
      bold: true,
      color: '#1f2937',
      bg: '#d9e2f3',
      thickBottom: true,
      thickRight: isMonthEndCol,
    })
  }

  for (let row = startRow + 2; row < startRow + rowCount; row += 1) {
    const zebraBg = row % 2 === 0 ? '#f8fbff' : '#ffffff'
    applyExcelCellStyle(worksheet.getCell(row, 1), {
      align: 'left',
      bg: zebraBg,
    })
    for (let index = 0; index < dates.length; index += 1) {
      const baseCol = 2 + (index * 3)
      applyExcelCellStyle(worksheet.getCell(row, baseCol), {
        align: 'right',
        bg: zebraBg,
        numFmt: '0.00',
      })
      applyExcelCellStyle(worksheet.getCell(row, baseCol + 1), {
        align: 'right',
        bg: zebraBg,
        numFmt: '0',
      })
      applyExcelCellStyle(worksheet.getCell(row, baseCol + 2), {
        align: 'right',
        bg: zebraBg,
        numFmt: '0.00',
        thickRight: true,
      })
    }
  }
}

const downloadWorkbook = async (workbook, filename) => {
  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}

const showTooltip = (ev, label, d) => {
  tooltip.visible = true
  tooltip.x = ev.clientX + 12
  tooltip.y = ev.clientY + 12
  tooltip.line = label
  tooltip.date = d.month_label || d.week_label || d.date
  tooltip.availMin = d.available_min
  tooltip.loadMin = d.line_load_min || 0
  tooltip.perDayHours = getPerDayHours(d)
  tooltip.finishedQty = Number(d.finished_qty || 0)
  tooltip.utilization = d.utilization
  tooltip.processes = d.processes || []
}

const hideTooltip = () => { tooltip.visible = false }

const buildProductProcessLoadSheet = (dates, dateLabels) => {
  const rows = [['ライン', '工程', '完成品コード', '完成品名', ...dateLabels]]

  for (const line of result.value.lines) {
    const displayData = lineDisplayData(line)
    const dateMap = new Map(displayData.map(d => [d.date, d]))
    const processMap = new Map()
    for (const d of displayData) {
      for (const process of (d.processes || [])) {
        const processKey = process.process_id
        if (!processMap.has(processKey)) {
          processMap.set(processKey, {
            process_id: process.process_id,
            process_code: process.process_code,
            process_name: process.process_name,
            products: new Map(),
          })
        }
        const processEntry = processMap.get(processKey)
        for (const product of (process.products || [])) {
          if (!processEntry.products.has(product.product_code)) {
            processEntry.products.set(product.product_code, {
              product_code: product.product_code,
              product_name: product.product_name,
            })
          }
        }
      }
    }

    for (const processEntry of [...processMap.values()].sort((a, b) => a.process_code.localeCompare(b.process_code))) {
      for (const productEntry of [...processEntry.products.values()].sort((a, b) => a.product_code.localeCompare(b.product_code))) {
        const row = [
          `${line.line_code} ${line.line_name}`,
          `${processEntry.process_code} ${processEntry.process_name}`,
          productEntry.product_code,
          productEntry.product_name,
        ]
        for (const d of dates) {
          const dateEntry = dateMap.get(d.date)
          const process = dateEntry?.processes?.find(item => item.process_id === processEntry.process_id)
          const product = process?.products?.find(item => item.product_code === productEntry.product_code)
          row.push(product ? formatExcelHours(product.load_min) : '')
        }
        rows.push(row)
      }
    }
  }

  return rows
}

const buildProductProcessQtySheet = (dates, dateLabels) => {
  const rows = [['ライン', '工程', '完成品コード', '完成品名', ...dateLabels]]

  for (const line of result.value.lines) {
    const displayData = lineDisplayData(line)
    const dateMap = new Map(displayData.map(d => [d.date, d]))
    const processMap = new Map()
    for (const d of displayData) {
      for (const process of (d.processes || [])) {
        const processKey = process.process_id
        if (!processMap.has(processKey)) {
          processMap.set(processKey, {
            process_id: process.process_id,
            process_code: process.process_code,
            process_name: process.process_name,
            products: new Map(),
          })
        }
        const processEntry = processMap.get(processKey)
        for (const product of (process.products || [])) {
          if (!processEntry.products.has(product.product_code)) {
            processEntry.products.set(product.product_code, {
              product_code: product.product_code,
              product_name: product.product_name,
            })
          }
        }
      }
    }

    for (const processEntry of [...processMap.values()].sort((a, b) => a.process_code.localeCompare(b.process_code))) {
      for (const productEntry of [...processEntry.products.values()].sort((a, b) => a.product_code.localeCompare(b.product_code))) {
        const row = [
          `${line.line_code} ${line.line_name}`,
          `${processEntry.process_code} ${processEntry.process_name}`,
          productEntry.product_code,
          productEntry.product_name,
        ]
        for (const d of dates) {
          const dateEntry = dateMap.get(d.date)
          const process = dateEntry?.processes?.find(item => item.process_id === processEntry.process_id)
          const product = process?.products?.find(item => item.product_code === productEntry.product_code)
          row.push(product ? formatExcelQty(product.finished_qty) : '')
        }
        rows.push(row)
      }
    }
  }

  return rows
}

const buildMonthlyLoadSheet = (dates) => {
  const monthHeader = ['ライン']
  const subHeader = ['']
  const merges = [{ s: { r: 0, c: 0 }, e: { r: 1, c: 0 } }]
  let colIndex = 1

  for (const d of dates) {
    const label = d.month_label || d.date
    monthHeader.push(label, '', '')
    subHeader.push('H/月', '稼働日', 'H/日')
    merges.push({ s: { r: 0, c: colIndex }, e: { r: 0, c: colIndex + 2 } })
    colIndex += 3
  }

  const rows = [monthHeader, subHeader]
  for (const line of result.value.lines) {
    const dateMap = new Map(lineDisplayData(line).map(d => [d.date, d]))
    const row = [`${line.line_code} ${line.line_name}`]
    for (const d of dates) {
      const val = dateMap.get(d.date)
      row.push(
        val ? formatExcelHours(val.line_load_min) : '',
        val?.working_days || '',
        val ? formatExcelHoursPerDay(val.line_load_min, val.working_days || 0) : '',
      )
    }
    rows.push(row)
  }

  return {
    rows,
    merges,
    cols: [{ wch: 24 }, ...dates.flatMap(() => ([{ wch: 10 }, { wch: 8 }, { wch: 10 }]))],
  }
}

const renderBarChartImage = (items, opts = {}) => {
  const { title = '', barColor = '#8e44ad' } = opts
  const n = items.length
  if (!n) return null
  const w = Math.max(500, Math.min(1400, n * 50 + 120))
  const h = 340
  const dpr = 2
  const canvas = document.createElement('canvas')
  canvas.width = w * dpr
  canvas.height = h * dpr
  const ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, w, h)

  const pad = { top: 32, right: 20, bottom: 56, left: 54 }
  const cw = w - pad.left - pad.right
  const ch = h - pad.top - pad.bottom
  const maxVal = Math.max(...items.map(d => d.value), 0.01)
  const niceMax = Math.ceil(maxVal / 10) * 10 || maxVal
  const slotW = cw / n
  const barW = Math.max(3, slotW * 0.65)

  for (let i = 0; i <= 4; i++) {
    const y = pad.top + ch * (1 - i / 4)
    ctx.strokeStyle = '#e5e7eb'
    ctx.lineWidth = 0.5
    ctx.beginPath()
    ctx.moveTo(pad.left, y)
    ctx.lineTo(pad.left + cw, y)
    ctx.stroke()
    ctx.fillStyle = '#888'
    ctx.font = '10px Arial, sans-serif'
    ctx.textAlign = 'right'
    const yVal = (niceMax * i) / 4
    ctx.fillText(yVal % 1 === 0 ? String(yVal) : yVal.toFixed(1), pad.left - 6, y + 3)
  }

  items.forEach((d, i) => {
    const cx = pad.left + i * slotW + slotW / 2
    const bh = Math.max(0, (d.value / niceMax) * ch)
    const x = cx - barW / 2
    const y = pad.top + ch - bh
    ctx.fillStyle = barColor
    ctx.fillRect(x, y, barW, bh)
    if (n <= 36 && d.value > 0) {
      ctx.fillStyle = '#333'
      ctx.font = `${Math.min(10, Math.max(7, barW * 0.6))}px Arial, sans-serif`
      ctx.textAlign = 'center'
      ctx.fillText(d.value.toFixed(1), cx, y - 3)
    }
    ctx.fillStyle = '#666'
    ctx.font = '9px Arial, sans-serif'
    ctx.save()
    ctx.translate(cx, pad.top + ch + 6)
    if (n > 12) { ctx.rotate(-Math.PI / 4); ctx.textAlign = 'right' }
    else { ctx.textAlign = 'center' }
    ctx.fillText(d.label, 0, 0)
    ctx.restore()
  })

  if (title) {
    ctx.fillStyle = '#333'
    ctx.font = 'bold 13px Arial, sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(title, w / 2, 16)
  }
  ctx.fillStyle = '#888'
  ctx.font = '10px Arial, sans-serif'
  ctx.textAlign = 'center'
  ctx.save()
  ctx.translate(12, pad.top + ch / 2)
  ctx.rotate(-Math.PI / 2)
  ctx.fillText('h', 0, 0)
  ctx.restore()

  return canvas.toDataURL('image/png')
}

const addChartImageToSheet = (workbook, ws, chartPng, startRow, itemCount) => {
  if (!chartPng) return
  const imgId = workbook.addImage({ base64: chartPng.split(',')[1], extension: 'png' })
  const imgW = Math.max(500, Math.min(1400, itemCount * 50 + 120))
  ws.addImage(imgId, { tl: { col: 0, row: startRow }, ext: { width: imgW, height: 340 } })
}

const exportExcel = async () => {
  if (!result.value) return
  const userName = await getExportUserName()
  const workbook = new ExcelJS.Workbook()
  workbook.creator = userName
  workbook.created = new Date()
  workbook.modified = new Date()

  // グループ集計シート
  for (const gc of groupCharts.value) {
    const rows = filters.aggregate === 'monthly'
      ? [['日付', '負荷(H)', '稼働日', 'H/日']]
      : [['日付', '負荷(H)']]
    for (const d of gc.data) {
      if (filters.aggregate === 'monthly') {
        rows.push([
          d.month_label || d.week_label || d.date,
          formatExcelHours(d.line_load_min),
          d.working_days || '',
          formatExcelHoursPerDay(d.line_load_min, d.working_days || 0),
        ])
      } else {
        rows.push([d.month_label || d.week_label || d.date, formatExcelHours(d.line_load_min)])
      }
    }
    const cols = filters.aggregate === 'monthly'
      ? [{ wch: 14 }, { wch: 10 }, { wch: 8 }, { wch: 10 }]
      : [{ wch: 14 }, { wch: 10 }]
    const ws = workbook.addWorksheet(gc.groupName.slice(0, 31))
    setWorksheetColumns(ws, cols)
    decorateSheetHeader(ws, `長期負荷チャート ${gc.groupName}`, cols.length, userName)
    writeSheetRows(ws, 6, rows)
    styleSimpleTable(ws, 6, rows.length, cols.length, {
      leftAlignCols: [1],
      integerCols: filters.aggregate === 'monthly' ? [3] : [],
      decimalCols: filters.aggregate === 'monthly' ? [2, 4] : [2],
    })
    ws.views = [{ state: 'frozen', xSplit: 0, ySplit: 6 }]
    const chartItems = gc.data.map(d => ({
      label: d.month_label || d.week_label || d.date,
      value: formatExcelHours(d.line_load_min),
    }))
    const chartRow = rows.length + 7
    addChartImageToSheet(workbook, ws, renderBarChartImage(chartItems, {
      title: `${gc.groupName} 負荷合計(h)`, barColor: '#8e44ad',
    }), chartRow, chartItems.length)
    const perDayItems = gc.data.map(d => ({
      label: d.month_label || d.week_label || d.date,
      value: formatExcelHoursPerDay(d.line_load_min, d.working_days || 0) || 0,
    }))
    addChartImageToSheet(workbook, ws, renderBarChartImage(perDayItems, {
      title: `${gc.groupName} 日あたり負荷(h/日)`, barColor: '#2980b9',
    }), chartRow + 20, perDayItems.length)
  }

  // ライン別シート（全ラインまとめ）
  const dates = []
  const dateSet = new Set()
  for (const line of result.value.lines) {
    for (const d of lineDisplayData(line)) {
      if (!dateSet.has(d.date)) {
        dateSet.add(d.date)
        dates.push(d)
      }
    }
  }
  dates.sort((a, b) => a.date.localeCompare(b.date))
  const dateLabels = dates.map(d => d.month_label || d.week_label || d.date)

  const header = ['ライン', ...dateLabels]

  // 負荷時間シート
  let wsLoad
  let loadDataRowCount = 0
  if (filters.aggregate === 'monthly') {
    const monthlyLoadSheet = buildMonthlyLoadSheet(dates)
    wsLoad = workbook.addWorksheet('負荷(h)')
    setWorksheetColumns(wsLoad, monthlyLoadSheet.cols)
    decorateSheetHeader(wsLoad, '長期負荷チャート 負荷(h)', monthlyLoadSheet.cols.length, userName)
    writeSheetRows(wsLoad, 6, monthlyLoadSheet.rows)
    monthlyLoadSheet.merges.forEach((merge) => {
      wsLoad.mergeCells(
        6 + merge.s.r,
        merge.s.c + 1,
        6 + merge.e.r,
        merge.e.c + 1,
      )
    })
    styleMonthlyLoadTable(wsLoad, 6, dates, monthlyLoadSheet.rows.length)
    wsLoad.views = [{ state: 'frozen', xSplit: 1, ySplit: 7 }]
    loadDataRowCount = monthlyLoadSheet.rows.length
  } else {
    const loadRows = [header]
    for (const line of result.value.lines) {
      const dateMap = {}
      for (const d of lineDisplayData(line)) { dateMap[d.date] = d }
      const row = [`${line.line_code} ${line.line_name}`]
      for (const d of dates) {
        const val = dateMap[d.date]
        row.push(val ? formatExcelHours(val.line_load_min) : '')
      }
      loadRows.push(row)
    }
    wsLoad = workbook.addWorksheet('負荷(h)')
    const cols = [{ wch: 24 }, ...dateLabels.map(() => ({ wch: 10 }))]
    setWorksheetColumns(wsLoad, cols)
    decorateSheetHeader(wsLoad, '長期負荷チャート 負荷(h)', cols.length, userName)
    writeSheetRows(wsLoad, 6, loadRows)
    styleSimpleTable(wsLoad, 6, loadRows.length, cols.length, {
      leftAlignCols: [1],
      decimalCols: Array.from({ length: cols.length - 1 }, (_, index) => index + 2),
    })
    wsLoad.views = [{ state: 'frozen', xSplit: 1, ySplit: 6 }]
    loadDataRowCount = loadRows.length
  }
  // 全ライン合計チャート
  const totalByDate = {}
  const totalWdByDate = {}
  for (const line of result.value.lines) {
    for (const d of lineDisplayData(line)) {
      totalByDate[d.date] = (totalByDate[d.date] || 0) + (d.line_load_min || 0)
      totalWdByDate[d.date] = Math.max(totalWdByDate[d.date] || 0, d.working_days || 0)
    }
  }
  const loadChartItems = dates.map(d => ({
    label: d.month_label || d.week_label || d.date,
    value: formatExcelHours(totalByDate[d.date] || 0),
  }))
  const loadChartRow = loadDataRowCount + 8
  addChartImageToSheet(workbook, wsLoad, renderBarChartImage(loadChartItems, {
    title: '全ライン合計 負荷(h)', barColor: '#e74c3c',
  }), loadChartRow, loadChartItems.length)
  const loadPerDayItems = dates.map(d => ({
    label: d.month_label || d.week_label || d.date,
    value: formatExcelHoursPerDay(totalByDate[d.date] || 0, totalWdByDate[d.date] || 0) || 0,
  }))
  addChartImageToSheet(workbook, wsLoad, renderBarChartImage(loadPerDayItems, {
    title: '全ライン合計 日あたり負荷(h/日)', barColor: '#2980b9',
  }), loadChartRow + 20, loadPerDayItems.length)

  const productProcessRows = buildProductProcessLoadSheet(dates, dateLabels)
  const wsProductProcess = workbook.addWorksheet('完成品別各工程ライン負荷')
  const productCols = [
    { wch: 24 },
    { wch: 22 },
    { wch: 16 },
    { wch: 24 },
    ...dateLabels.map(() => ({ wch: 10 })),
  ]
  setWorksheetColumns(wsProductProcess, productCols)
  decorateSheetHeader(wsProductProcess, '長期負荷チャート 完成品別各工程ライン負荷', productCols.length, userName)
  writeSheetRows(wsProductProcess, 6, productProcessRows)
  styleSimpleTable(wsProductProcess, 6, productProcessRows.length, productCols.length, {
    leftAlignCols: [1, 2, 3, 4],
    decimalCols: Array.from({ length: productCols.length - 4 }, (_, index) => index + 5),
  })
  wsProductProcess.views = [{ state: 'frozen', xSplit: 4, ySplit: 6 }]

  const productProcessQtyRows = buildProductProcessQtySheet(dates, dateLabels)
  const wsProductProcessQty = workbook.addWorksheet('完成品別各工程ライン台数')
  setWorksheetColumns(wsProductProcessQty, productCols)
  decorateSheetHeader(wsProductProcessQty, '長期負荷チャート 完成品別各工程ライン台数', productCols.length, userName)
  writeSheetRows(wsProductProcessQty, 6, productProcessQtyRows)
  styleSimpleTable(wsProductProcessQty, 6, productProcessQtyRows.length, productCols.length, {
    leftAlignCols: [1, 2, 3, 4],
    decimalCols: Array.from({ length: productCols.length - 4 }, (_, index) => index + 5),
    decimalNumFmt: '0.###',
  })
  wsProductProcessQty.views = [{ state: 'frozen', xSplit: 4, ySplit: 6 }]

  const agg = filters.aggregate === 'monthly' ? '月別' : filters.aggregate === 'weekly' ? '週別' : '日別'
  await downloadWorkbook(workbook, `長期負荷_${agg}_${filters.startDate}_${filters.endDate}.xlsx`)
}
</script>

<style scoped>
.page-container { padding: 12px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.page-title { font-size: 18px; font-weight: 700; margin: 0; }
.helper-text { font-size: 12px; color: #888; margin: 2px 0 0; }
.page-actions { display: flex; gap: 8px; }
.page-content { display: flex; flex-direction: column; gap: 12px; }

.filter-bar { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 10px 12px; }
.filter-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; margin-bottom: 6px; }
.filter-row:last-child { margin-bottom: 0; }
.filter-field { display: flex; flex-direction: column; gap: 2px; }
.filter-field.wide { flex: 1; }
.filter-field label { font-size: 11px; font-weight: 600; color: #666; }
.filter-field input, .filter-field select { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
.filter-actions { display: flex; gap: 6px; }
.settings-anchor { position: relative; display: flex; align-items: center; gap: 8px; }
.settings-popover {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: 280px;
  padding: 10px;
  background: #fff;
  border: 1px solid #d6dce5;
  border-radius: 6px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
  z-index: 20;
}
.settings-popover-title { font-size: 13px; font-weight: 700; color: #1f2937; margin-bottom: 8px; }
.settings-field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.settings-field label { font-size: 11px; font-weight: 600; color: #666; }
.settings-field input { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
.settings-helper { margin: 0; font-size: 11px; color: #666; line-height: 1.5; }
.settings-helper.warning { color: #b45309; margin-top: 4px; }
.settings-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.demand-summary-inline { font-size: 12px; color: #374151; white-space: nowrap; }

.line-chips { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.chip-label { cursor: pointer; }
.chip-label input { display: none; }
.chip { display: inline-block; padding: 2px 8px; border: 1px solid #ccc; border-radius: 12px; font-size: 12px; background: #fff; transition: all 0.15s; }
.chip-group { border-color: #8e44ad; color: #8e44ad; }
.chip-label input:checked + .chip { background: #3498db; color: #fff; border-color: #3498db; }
.chip-label input:checked + .chip-group { background: #8e44ad; border-color: #8e44ad; }

.btn-primary { padding: 5px 14px; background: #3498db; color: #fff; border: none; border-radius: 4px; font-size: 13px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; }
.btn-secondary { padding: 5px 14px; background: #fff; color: #333; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; cursor: pointer; text-decoration: none; }
.btn-link { background: none; border: none; color: #3498db; font-size: 11px; cursor: pointer; text-decoration: underline; padding: 0; }

.chart-area { display: flex; flex-direction: column; gap: 20px; }
.line-chart-block { background: #fff; border: 1px solid #dee2e6; border-radius: 6px; padding: 10px 12px; }
.group-block { border-color: #8e44ad; border-width: 2px; }
.line-title { font-size: 14px; font-weight: 700; margin: 0 0 8px; }
.group-title { color: #8e44ad; }
.process-chart-list { display: flex; flex-direction: column; gap: 14px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #e5e7eb; }
.process-chart-block { background: #fafbfc; border: 1px solid #edf0f2; border-radius: 6px; padding: 10px; }
.process-title { font-size: 13px; font-weight: 700; margin: 0 0 8px; color: #374151; }
.process-note { font-size: 11px; font-weight: 500; color: #6b7280; }
.process-bar-chart { min-height: 130px; }
.chart-legend-inline { display: flex; align-items: center; gap: 14px; margin-bottom: 6px; font-size: 11px; color: #4b5563; }
.chart-legend-item { display: inline-flex; align-items: center; gap: 5px; }
.legend-bar-swatch { width: 14px; height: 10px; border-radius: 3px 3px 0 0; background: #60a5fa; }
.legend-line-swatch { position: relative; width: 16px; height: 10px; }
.legend-line-swatch::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  border-top: 2px solid var(--legend-line-color, #e74c3c);
}
.legend-line-swatch::after {
  content: '';
  position: absolute;
  top: calc(50% - 3px);
  left: calc(50% - 3px);
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--legend-line-color, #e74c3c);
}

.chart-canvas { display: inline-flex; gap: 8px; align-items: flex-start; max-width: 100%; }
.y-axis { width: 48px; height: 120px; margin-top: 14px; position: relative; flex-shrink: 0; }
.right-axis { width: 56px; padding-left: 4px; border-left: 1px solid #e5e7eb; }
.right-axis .y-axis-label { left: 0; right: auto; }
.y-axis-label { position: absolute; right: 0; font-size: 10px; color: #6b7280; line-height: 1; }
.y-axis-label.top { top: 0; transform: translateY(-50%); }
.y-axis-label.mid { top: 50%; transform: translateY(-50%); }
.y-axis-label.bottom { bottom: 0; transform: translateY(50%); }

.bar-chart-wrapper { overflow-x: auto; flex: 0 1 auto; min-width: 0; max-width: calc(100vw - 220px); }
.bar-chart { display: flex; gap: 2px; align-items: flex-end; min-height: 160px; padding-bottom: 20px; position: relative; }
.chart-guides { position: absolute; top: 14px; left: 0; right: 0; height: 120px; pointer-events: none; z-index: 0; }
.chart-guide { position: absolute; left: 0; right: 0; border-top: 1px solid #e5e7eb; }
.chart-guide.top { top: 0; }
.chart-guide.mid { top: 50%; }
.chart-guide.bottom { bottom: 0; }
.line-overlay { position: absolute; left: 0; bottom: 20px; height: 120px; pointer-events: none; z-index: 3; overflow: visible; }
.line-path { fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.line-point { fill: currentColor; stroke: #ffffff; stroke-width: 1; }
.bar-col { display: flex; flex-direction: column; align-items: center; width: 36px; flex-shrink: 0; cursor: pointer; position: relative; z-index: 2; }
.bar-label-stack { display: flex; flex-direction: column; align-items: center; min-height: 24px; margin-bottom: 2px; }
.bar-label-top { font-size: 9px; color: #666; line-height: 1.1; white-space: nowrap; }
.bar-track { width: 28px; height: 120px; background: transparent; position: relative; display: flex; align-items: flex-end; }
.bar-fill { width: 100%; border-radius: 3px 3px 0 0; transition: height 0.3s; min-height: 1px; }
.per-day-bar { opacity: 0.9; }
.bar-label { font-size: 9px; color: #666; margin-top: 3px; white-space: nowrap; }

.chart-tooltip {
  position: fixed; z-index: 9999; background: #333; color: #fff;
  padding: 8px 12px; border-radius: 6px; font-size: 12px; pointer-events: none;
  max-width: 300px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.tooltip-title { font-weight: 700; margin-bottom: 4px; border-bottom: 1px solid #555; padding-bottom: 3px; }
.tooltip-row { margin: 2px 0; }

.calendar-warning {
  background: #fff3cd; color: #856404; border: 1px solid #ffc107; border-radius: 4px;
  padding: 4px 10px; font-size: 12px; margin-bottom: 6px;
}

.empty-state { text-align: center; color: #999; padding: 40px; font-size: 14px; }
</style>
