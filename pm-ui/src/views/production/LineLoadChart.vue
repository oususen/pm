<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">長期負荷チャート</h1>
        <p class="helper-text">顧客需要 × ラインサイクルタイムからライン別の負荷率を表示</p>
      </div>
      <div class="page-actions">
        <button v-if="result" class="btn-secondary" @click="exportExcel">Excel出力</button>
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
                <div class="bar-label-top">{{ Math.round(d.utilization) }}%</div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ height: Math.min(d.utilization, 150) / 1.5 + '%', backgroundColor: barColor(d.utilization) }"></div>
                  <div class="bar-100-line"></div>
                </div>
                <div class="bar-label">{{ formatDateLabel(d) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- ライン個別 -->
        <div v-for="line in result.lines" :key="line.line_id" class="line-chart-block">
          <h3 class="line-title">{{ line.line_code }} {{ line.line_name }}</h3>
          <div class="bar-chart-wrapper">
            <div class="bar-chart">
              <div
                v-for="d in line.data.filter(x => x.is_working_day)"
                :key="d.date"
                class="bar-col"
                @mouseenter="showTooltip($event, `${line.line_code} ${line.line_name}`, d)"
                @mouseleave="hideTooltip"
              >
                <div class="bar-label-top">{{ Math.round(d.utilization) }}%</div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ height: Math.min(d.utilization, 150) / 1.5 + '%', backgroundColor: barColor(d.utilization) }"></div>
                  <div class="bar-100-line"></div>
                </div>
                <div class="bar-label">{{ formatDateLabel(d) }}</div>
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
      <div class="tooltip-row">稼働: {{ tooltip.availMin }}分</div>
      <div class="tooltip-row"><b>負荷率: {{ tooltip.utilization }}%</b></div>
      <div v-for="p in tooltip.processes" :key="p.process_code" class="tooltip-row">
        {{ p.process_code }} {{ p.process_name }}: {{ p.load_min }}分 ({{ p.utilization }}%)
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'

const loading = ref(false)
const prodLines = ref([])
const groups = ref([])
const unitLineMappings = ref([])
const selectedLineIds = ref([])
const selectedGroupIds = ref([])
const result = ref(null)

const today = new Date()
const filters = reactive({
  startDate: today.toISOString().slice(0, 10),
  endDate: new Date(today.getTime() + 365 * 86400000).toISOString().slice(0, 10),
  aggregate: 'monthly',
})

const tooltip = reactive({
  visible: false, x: 0, y: 0,
  line: '', date: '', availMin: 0, utilization: 0, processes: [],
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
      for (const d of line.data) {
        if (!d.is_working_day) continue
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

const barColor = (util) => {
  if (util >= 100) return '#e74c3c'
  if (util >= 80) return '#f39c12'
  return '#27ae60'
}

const formatDateLabel = (d) => {
  if (d.month_label) return d.month_label
  if (d.week_label) return d.week_label
  return d.date.slice(5)
}

const showTooltip = (ev, label, d) => {
  tooltip.visible = true
  tooltip.x = ev.clientX + 12
  tooltip.y = ev.clientY + 12
  tooltip.line = label
  tooltip.date = d.month_label || d.week_label || d.date
  tooltip.availMin = d.available_min
  tooltip.utilization = d.utilization
  tooltip.processes = d.processes || []
}

const hideTooltip = () => { tooltip.visible = false }

const exportExcel = () => {
  if (!result.value) return
  const wb = XLSX.utils.book_new()

  // グループ集計シート
  for (const gc of groupCharts.value) {
    const rows = [['日付', '稼働(分)', '負荷(分)', '負荷率(%)']]
    for (const d of gc.data) {
      rows.push([d.month_label || d.week_label || d.date, d.available_min, d.line_load_min, d.utilization])
    }
    const ws = XLSX.utils.aoa_to_sheet(rows)
    ws['!cols'] = [{ wch: 14 }, { wch: 10 }, { wch: 10 }, { wch: 10 }]
    XLSX.utils.book_append_sheet(wb, ws, gc.groupName.slice(0, 31))
  }

  // ライン別シート（全ラインまとめ）
  const dates = []
  const dateSet = new Set()
  for (const line of result.value.lines) {
    for (const d of line.data) {
      if (d.is_working_day && !dateSet.has(d.date)) {
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
    for (const d of line.data) { if (d.is_working_day) dateMap[d.date] = d }
    const row = [`${line.line_code} ${line.line_name}`]
    for (const d of dates) {
      const val = dateMap[d.date]
      row.push(val ? val.utilization : '')
    }
    utilRows.push(row)
  }
  const wsUtil = XLSX.utils.aoa_to_sheet(utilRows)
  wsUtil['!cols'] = [{ wch: 24 }, ...dateLabels.map(() => ({ wch: 10 }))]
  XLSX.utils.book_append_sheet(wb, wsUtil, '負荷率(%)')

  // 負荷時間シート
  const loadRows = [header]
  for (const line of result.value.lines) {
    const dateMap = {}
    for (const d of line.data) { if (d.is_working_day) dateMap[d.date] = d }
    const row = [`${line.line_code} ${line.line_name}`]
    for (const d of dates) {
      const val = dateMap[d.date]
      row.push(val ? val.line_load_min : '')
    }
    loadRows.push(row)
  }
  const wsLoad = XLSX.utils.aoa_to_sheet(loadRows)
  wsLoad['!cols'] = [{ wch: 24 }, ...dateLabels.map(() => ({ wch: 10 }))]
  XLSX.utils.book_append_sheet(wb, wsLoad, '負荷(分)')

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

.bar-chart-wrapper { overflow-x: auto; }
.bar-chart { display: flex; gap: 2px; align-items: flex-end; min-height: 160px; padding-bottom: 20px; position: relative; }
.bar-col { display: flex; flex-direction: column; align-items: center; min-width: 36px; flex-shrink: 0; cursor: pointer; }
.bar-label-top { font-size: 9px; color: #666; margin-bottom: 2px; white-space: nowrap; }
.bar-track { width: 28px; height: 120px; background: #f0f0f0; border-radius: 3px 3px 0 0; position: relative; display: flex; align-items: flex-end; }
.bar-fill { width: 100%; border-radius: 3px 3px 0 0; transition: height 0.3s; min-height: 1px; }
.bar-100-line { position: absolute; bottom: 66.7%; left: -2px; right: -2px; border-top: 1.5px dashed #e74c3c; pointer-events: none; }
.bar-label { font-size: 9px; color: #666; margin-top: 3px; white-space: nowrap; }

.chart-tooltip {
  position: fixed; z-index: 9999; background: #333; color: #fff;
  padding: 8px 12px; border-radius: 6px; font-size: 12px; pointer-events: none;
  max-width: 300px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.tooltip-title { font-weight: 700; margin-bottom: 4px; border-bottom: 1px solid #555; padding-bottom: 3px; }
.tooltip-row { margin: 2px 0; }

.empty-state { text-align: center; color: #999; padding: 40px; font-size: 14px; }
</style>
