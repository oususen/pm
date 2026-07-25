<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">長期負荷チャート <DataSourceDialog title="長期負荷チャート" :sources="dsSources" /></h1>
        <p class="helper-text">顧客需要 × ラインサイクルタイムからライン別・工程別の負荷時間を表示（単位: h / 工程負荷は設備台数反映後）</p>
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
          <div class="bar-chart-wrapper">
            <div class="bar-chart">
              <div
                v-for="d in gc.data"
                :key="d.date"
                class="bar-col"
                @mouseenter="showTooltip($event, gc.groupName, d)"
                @mouseleave="hideTooltip"
              >
                <div class="bar-label-top">{{ formatLoadHours(d.line_load_sec) }}h</div>
                <div class="bar-track">
                  <div class="bar-fill" :style="barStyle(gc.data, d, '#8e44ad')"></div>
                </div>
                <div class="bar-label">{{ formatDateLabel(d) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ライン個別 -->
        <div v-for="line in result.lines" :key="line.line_id" class="line-chart-block">
          <h3 class="line-title">{{ line.line_code }} {{ line.line_name }}</h3>
          <div v-if="lineWarning(line)" class="calendar-warning">
            ⚠ {{ lineWarning(line) }}
          </div>
          <div class="bar-chart-wrapper">
            <div class="bar-chart">
              <div
                v-for="d in lineDisplayData(line)"
                :key="d.date"
                class="bar-col"
                @mouseenter="showTooltip($event, `${line.line_code} ${line.line_name}`, d)"
                @mouseleave="hideTooltip"
              >
                <div class="bar-label-top">{{ formatLoadHours(d.line_load_sec) }}h</div>
                <div class="bar-track">
                  <div class="bar-fill" :style="barStyle(lineDisplayData(line), d, '#e74c3c')"></div>
                </div>
                <div class="bar-label">{{ formatDateLabel(d) }}</div>
              </div>
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
              <div class="bar-chart-wrapper">
                <div class="bar-chart process-bar-chart">
                  <div
                    v-for="d in processDisplayData(line, proc)"
                    :key="`${proc.process_id}_${d.date}`"
                    class="bar-col"
                    @mouseenter="showTooltip($event, `${line.line_code} ${line.line_name} / ${proc.process_code} ${proc.process_name}`, d)"
                    @mouseleave="hideTooltip"
                  >
                    <div class="bar-label-top">{{ formatLoadHours(d.line_load_sec) }}h</div>
                    <div class="bar-track">
                      <div class="bar-fill" :style="barStyle(processDisplayData(line, proc), d, '#3498db')"></div>
                    </div>
                    <div class="bar-label">{{ formatDateLabel(d) }}</div>
                  </div>
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
import * as XLSX from 'xlsx'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 'm_line', desc: 'ライン個別選択の候補' },
  { op: '読み取り', table: 'accounts_unit / accounts_unit_line_mapping', desc: 'グループ選択とライン紐付け' },
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
  line: '', date: '', availMin: 0, loadMin: 0, utilization: 0, processes: [],
})

onMounted(async () => {
  const [linesRes, groupsRes, mappingsRes] = await Promise.all([
    api.lines.getLines({ is_active: true, line_type: 'PROD' }),
    api.accounts.getUnits({ page_size: 200 }),
    api.accounts.getUnitLineMappings({ page_size: 20000 }),
  ])
  prodLines.value = (linesRes.data.results || linesRes.data).sort((a, b) => a.line_code.localeCompare(b.line_code))
  groups.value = Array.isArray(groupsRes.data) ? groupsRes.data : (groupsRes.data.results || [])
  unitLineMappings.value = Array.isArray(mappingsRes.data) ? mappingsRes.data : (mappingsRes.data.results || [])
})

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
          dateMap[d.date] = { available_min: 0, load_sec: 0, month_label: d.month_label, week_label: d.week_label }
        }
        dateMap[d.date].available_min += d.available_min
        dateMap[d.date].load_sec += d.line_load_sec
      }
    }

    const data = Object.entries(dateMap)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, v]) => ({
        date,
        month_label: v.month_label,
        week_label: v.week_label,
        available_min: v.available_min,
        line_load_sec: v.load_sec,
        line_load_min: Math.round(v.load_sec / 60 * 10) / 10,
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
  if (!hasCal && hasLoad) return 'カレンダー未設定です。負荷時間(h)のみ表示しています'
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
      line_load_sec: loadSec,
      line_load_min: loadMin,
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

const barStyle = (source, d, color = '#e74c3c') => {
  const allLoads = source.map(x => x.line_load_sec).filter(x => x > 0)
  const maxLoad = Math.max(...allLoads, 1)
  const pct = (d.line_load_sec / maxLoad) * 100
  return { height: pct + '%', backgroundColor: color }
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

const showTooltip = (ev, label, d) => {
  tooltip.visible = true
  tooltip.x = ev.clientX + 12
  tooltip.y = ev.clientY + 12
  tooltip.line = label
  tooltip.date = d.month_label || d.week_label || d.date
  tooltip.availMin = d.available_min
  tooltip.loadMin = d.line_load_min || 0
  tooltip.utilization = d.utilization
  tooltip.processes = d.processes || []
}

const hideTooltip = () => { tooltip.visible = false }

const exportExcel = () => {
  if (!result.value) return
  const wb = XLSX.utils.book_new()

  // グループ集計シート
  for (const gc of groupCharts.value) {
    const rows = [['日付', '稼働(分)', '負荷(h)', '負荷率(%)']]
    for (const d of gc.data) {
      rows.push([d.month_label || d.week_label || d.date, d.available_min, formatHours(d.line_load_min), d.utilization])
    }
    const ws = XLSX.utils.aoa_to_sheet(rows)
    ws['!cols'] = [{ wch: 14 }, { wch: 10 }, { wch: 10 }, { wch: 10 }]
    XLSX.utils.book_append_sheet(wb, ws, gc.groupName.slice(0, 31))
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

  // 負荷率シート
  const header = ['ライン', ...dateLabels]
  const utilRows = [header]
  for (const line of result.value.lines) {
    const dateMap = {}
    for (const d of lineDisplayData(line)) { dateMap[d.date] = d }
    const row = [`${line.line_code} ${line.line_name}${lineHasCalendar(line) ? '' : ' ※カレンダー未設定'}`]
    for (const d of dates) {
      const val = dateMap[d.date]
      row.push(val ? (lineHasCalendar(line) ? val.utilization : formatLoadHours(val.line_load_sec) + 'h') : '')
    }
    utilRows.push(row)
  }
  const wsUtil = XLSX.utils.aoa_to_sheet(utilRows)
  wsUtil['!cols'] = [{ wch: 30 }, ...dateLabels.map(() => ({ wch: 10 }))]
  XLSX.utils.book_append_sheet(wb, wsUtil, '負荷率(%)')

  // 負荷時間シート
  const loadRows = [header]
  for (const line of result.value.lines) {
    const dateMap = {}
    for (const d of lineDisplayData(line)) { dateMap[d.date] = d }
    const row = [`${line.line_code} ${line.line_name}`]
    for (const d of dates) {
      const val = dateMap[d.date]
      row.push(val ? formatHours(val.line_load_min) : '')
    }
    loadRows.push(row)
  }
  const wsLoad = XLSX.utils.aoa_to_sheet(loadRows)
  wsLoad['!cols'] = [{ wch: 24 }, ...dateLabels.map(() => ({ wch: 10 }))]
  XLSX.utils.book_append_sheet(wb, wsLoad, '負荷(h)')

  const agg = filters.aggregate === 'monthly' ? '月別' : filters.aggregate === 'weekly' ? '週別' : '日別'
  XLSX.writeFile(wb, `長期負荷_${agg}_${filters.startDate}_${filters.endDate}.xlsx`)
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

.bar-chart-wrapper { overflow-x: auto; }
.bar-chart { display: flex; gap: 2px; align-items: flex-end; min-height: 160px; padding-bottom: 20px; position: relative; }
.bar-col { display: flex; flex-direction: column; align-items: center; min-width: 36px; flex-shrink: 0; cursor: pointer; }
.bar-label-top { font-size: 9px; color: #666; margin-bottom: 2px; white-space: nowrap; }
.bar-track { width: 28px; height: 120px; background: #f0f0f0; border-radius: 3px 3px 0 0; position: relative; display: flex; align-items: flex-end; }
.bar-fill { width: 100%; border-radius: 3px 3px 0 0; transition: height 0.3s; min-height: 1px; }
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
