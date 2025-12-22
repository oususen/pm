<template>
  <div class="gantt-container" :data-embedded="props.embedded">
    <div class="toolbar" v-if="!props.embedded">
      <div class="toolbar-left">
        <div class="field">
          <label>ライン</label>
          <select v-model="selectedLine" @change="loadData">
            <option value="">選択してください</option>
            <option v-for="line in lines" :key="line.id" :value="line.id">
              {{ line.line_code }} - {{ line.line_name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>基準日</label>
          <input type="date" v-model="baseDate" @change="loadData" />
        </div>
      </div>
      <div class="toolbar-right">
        <button class="btn" @click="loadData" :disabled="!selectedLine">
          読込
        </button>
        <button class="btn primary" @click="generateSchedule" :disabled="!selectedLine">
          実行
        </button>
        <button class="btn" @click="saveSchedule" :disabled="!processGanttData.length">
          保存
        </button>
      </div>
    </div>

    <div v-if="processGanttData.length" class="gantt-wrapper">
      <div class="gantt-scroll">
        <!-- 各工程のガントチャート -->
        <div
          v-for="proc in processGanttData"
          :key="proc.process_id"
          class="process-gantt-card"
        >
          <div class="process-gantt-head">
            <div class="process-info">
              <div class="process-name">{{ proc.process_name }}</div>
              <div class="process-sub">{{ proc.line_name }}</div>
            </div>
          </div>
          <div class="gantt-chart">
            <!-- タイムライン ヘッダー -->
            <div class="timeline-header">
              <div class="timeline-label">品番</div>
              <div class="timeline-axis" :style="{ width: timelineWidthPx + 'px' }">
                <div
                  v-for="slot in timelineSlots"
                  :key="slot.key"
                  class="time-slot-header"
                  :class="slot.dayClass"
                  :style="{ width: pixelsPerDay + 'px' }"
                >
                  <div class="time-slot-day">{{ slot.dayLabel }}</div>
                  <div class="time-slot-label">{{ slot.label }}</div>
                </div>
              </div>
            </div>
            <!-- 各品番のガントバー -->
            <div
              v-for="(item, idx) in proc.items"
              :key="idx"
              class="gantt-row"
            >
              <div class="gantt-row-label">
                <div class="product-code">{{ item.product_code }}</div>
                <div class="product-qty">計画: {{ item.plan_qty }}</div>
              </div>
              <div class="gantt-row-bars" :style="{ width: timelineWidthPx + 'px' }">
                <div
                  v-for="bar in item.bars"
                  :key="bar.key"
                  class="gantt-bar-wrapper"
                  :style="{
                    left: bar.leftPx + 'px',
                    width: bar.widthPx + 'px',
                  }"
                  :data-plan-id="bar.planId"
                  :data-process-id="bar.processId"
                  :data-duration-ms="bar.durationMs"
                  @mousedown="handleDragStart"
                >
                  <span class="lot-badge">{{ bar.planQty }}</span>
                  <div
                    class="gantt-bar"
                    :style="{
                      backgroundColor: bar.color,
                    }"
                  >
                    <span class="gantt-bar-label">{{ bar.label }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-if="!proc.items.length" class="no-data">
            この工程には計画データがありません
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty-message">
      ラインを選択して「読込」ボタンをクリックしてください
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineProps } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  presetLine: { type: [String, Number], default: '' },
  presetBaseDate: { type: String, default: '' },
})

const route = useRoute()
const selectedLine = ref('')
const baseDate = ref(new Date().toISOString().slice(0, 10))
const lines = ref([])
const processGanttData = ref([])
const pixelsPerDay = 100
const timelineStart = ref(null)
const timelineEnd = ref(null)
const timelineSlots = ref([])
const debugEnabled = true

const logDebug = (...args) => {
  if (debugEnabled) console.info('[ProcessGanttView]', ...args)
}

// 5日間（一昨日、昨日、今日、明日、明後日）
const displayDays = computed(() => {
  const base = new Date(baseDate.value)
  const days = []
  for (let offset = -2; offset <= 2; offset++) {
    const d = new Date(base)
    d.setDate(d.getDate() + offset)
    days.push({ date: d.toISOString().slice(0, 10), label: formatDayLabel(d) })
  }
  return days
})

const timelineWidthPx = computed(() => timelineSlots.value.length * pixelsPerDay)

function getDayClass(dateStr) {
  const d = new Date(dateStr)
  const dow = d.getDay()
  if (dow === 0) return 'sun'
  if (dow === 6) return 'sat'
  return ''
}

const fetchLines = async () => {
  const res = await api.lines.getLines()
  lines.value = res.data.results || res.data || []
}

const loadData = async () => {
  if (!selectedLine.value) return
  processGanttData.value = []

  try {
    const startDate = displayDays.value[0].date
    const endDate = displayDays.value[displayDays.value.length - 1].date

    logDebug('loadData', { line: selectedLine.value, startDate, endDate })
    const ganttRes = await api.lineGanttPlans.getLineGanttPlans({
      line: selectedLine.value,
      plan_date__gte: startDate,
      plan_date__lte: endDate,
    })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    logDebug('loadData response', { count: rawPlans.length, sample: rawPlans[0] })
    if (!rawPlans.length && props.embedded) {
      logDebug('loadData no data, auto-generate')
      await generateSchedule(false)
      return
    }
    processGanttData.value = buildProcessGantt(rawPlans)
  } catch (e) {
    console.error('工程ガント読込エラー', e)
    alert('データ読込に失敗しました')
  }
}

const generateSchedule = async (clearExisting = true) => {
  if (!selectedLine.value) return
  processGanttData.value = []

  try {
    const startDate = displayDays.value[0].date
    const endDate = displayDays.value[displayDays.value.length - 1].date
    logDebug('generateSchedule', { line: selectedLine.value, startDate, endDate, clearExisting })
    const ganttRes = await api.lineGanttPlans.generate({
      line_id: selectedLine.value,
      start_date: startDate,
      end_date: endDate,
      clear_existing: clearExisting,
    })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    logDebug('generateSchedule response', { count: rawPlans.length, sample: rawPlans[0] })
    processGanttData.value = buildProcessGantt(rawPlans)
    return rawPlans
  } catch (e) {
    console.error('工程ガント生成エラー', e)
    alert('ガント計画の生成に失敗しました')
  }
}

const saveSchedule = async () => {
  if (!timelineStart.value) {
    alert('保存するスケジュールがありません')
    return
  }
  const bars = document.querySelectorAll('.gantt-bar-wrapper')
  if (!bars.length) {
    alert('保存するスケジュールがありません')
    return
  }

  const updates = []
  const msPerDay = 1000 * 60 * 60 * 24
  bars.forEach((bar) => {
    const planId = bar.dataset.planId
    const processId = Number(bar.dataset.processId)
    const durationMs = Number(bar.dataset.durationMs)
    if (!planId || !processId || !durationMs) return

    const currentLeft = parseFloat(bar.style.left || '0')
    const daysFromStart = currentLeft / pixelsPerDay
    const newStartMs = timelineStart.value.getTime() + (daysFromStart * msPerDay)

    const roundMs = 1000 * 60 * 5
    const roundedStartMs = Math.round(newStartMs / roundMs) * roundMs
    const finalStart = new Date(roundedStartMs)
    const finalEnd = new Date(roundedStartMs + durationMs)

    updates.push({
      plan_id: planId,
      process_id: processId,
      start_time: toLocalISO(finalStart),
      end_time: toLocalISO(finalEnd),
    })
  })

  if (!updates.length) {
    alert('保存対象のデータがありません')
    return
  }

  try {
    logDebug('saveSchedule', { updates: updates.length })
    await api.lineGanttPlans.bulkUpdate(updates)
    alert('保存しました')
  } catch (e) {
    console.error('保存エラー', e)
    alert('保存に失敗しました')
  }
}

let draggedBar = null
let dragStartX = 0
let dragOriginalLeft = 0
let isDragging = false

function getDragTooltip() {
  let tooltip = document.getElementById('dragTooltip')
  if (!tooltip) {
    tooltip = document.createElement('div')
    tooltip.id = 'dragTooltip'
    tooltip.style.position = 'fixed'
    tooltip.style.backgroundColor = 'rgba(0, 0, 0, 0.8)'
    tooltip.style.color = '#fff'
    tooltip.style.padding = '4px 8px'
    tooltip.style.borderRadius = '4px'
    tooltip.style.fontSize = '12px'
    tooltip.style.zIndex = '9999'
    tooltip.style.pointerEvents = 'none'
    tooltip.style.display = 'none'
    document.body.appendChild(tooltip)
  }
  return tooltip
}

function handleDragStart(e) {
  if (e.button !== 0) return
  draggedBar = e.currentTarget
  dragStartX = e.clientX
  dragOriginalLeft = parseFloat(draggedBar.style.left || '0')
  isDragging = false

  draggedBar.style.cursor = 'grabbing'
  draggedBar.style.zIndex = 10
  draggedBar.classList.remove('was-dragged')

  document.addEventListener('mousemove', handleDragMove)
  document.addEventListener('mouseup', handleDragEnd)

  const tooltip = getDragTooltip()
  tooltip.style.display = 'block'
  updateDragTooltip(e)

  e.preventDefault()
}

function handleDragMove(e) {
  if (!draggedBar) return
  const dx = e.clientX - dragStartX
  if (Math.abs(dx) > 3) {
    isDragging = true
    draggedBar.classList.add('was-dragged')
  }
  const newLeft = dragOriginalLeft + dx
  draggedBar.style.left = `${newLeft}px`
  updateDragTooltip(e)
}

function updateDragTooltip(e) {
  const tooltip = getDragTooltip()
  if (!timelineStart.value) return
  const msPerDay = 1000 * 60 * 60 * 24
  const currentLeft = parseFloat(draggedBar.style.left || '0')
  const daysFromStart = currentLeft / pixelsPerDay
  const newStartMs = timelineStart.value.getTime() + (daysFromStart * msPerDay)
  const roundMs = 1000 * 60 * 5
  const roundedStartMs = Math.round(newStartMs / roundMs) * roundMs
  const newStartDate = new Date(roundedStartMs)

  const durationMs = Number(draggedBar.dataset.durationMs || 0)
  const newEndDate = new Date(roundedStartMs + durationMs)

  const fmt = (d) => `${d.getMonth() + 1}/${d.getDate()} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
  tooltip.textContent = `${fmt(newStartDate)} - ${fmt(newEndDate)}`
  tooltip.style.left = `${e.clientX + 15}px`
  tooltip.style.top = `${e.clientY + 15}px`
}

function handleDragEnd() {
  if (!draggedBar) return
  document.removeEventListener('mousemove', handleDragMove)
  document.removeEventListener('mouseup', handleDragEnd)

  draggedBar.style.cursor = 'grab'
  draggedBar.style.zIndex = ''

  const tooltip = getDragTooltip()
  tooltip.style.display = 'none'

  if (isDragging) {
    alert('位置を調整しました。保存ボタンで確定してください。')
  }

  draggedBar = null
  isDragging = false
}

const toLocalISO = (date) => {
  const offset = date.getTimezoneOffset() * 60000
  const localDate = new Date(date.getTime() - offset)
  return localDate.toISOString().slice(0, 19)
}

function pad2(val) {
  return String(val).padStart(2, '0')
}

function formatTime(date) {
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`
}

function formatDayLabel(dateObj) {
  const weekday = ['日', '月', '火', '水', '木', '金', '土']
  const m = dateObj.getMonth() + 1
  const d = dateObj.getDate()
  const w = weekday[dateObj.getDay()]
  return `${m}/${d}(${w})`
}

function buildTimelineSlots(startDate, endDate) {
  const slots = []
  const current = new Date(startDate)
  while (current <= endDate) {
    slots.push({
      key: current.toISOString().slice(0, 10),
      dayLabel: formatDayLabel(current),
      label: `${current.getMonth() + 1}/${current.getDate()}`,
      dayClass: getDayClass(current.toISOString().slice(0, 10)),
    })
    current.setDate(current.getDate() + 1)
  }
  return slots
}

function formatDateTime(date) {
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`
}

function formatTimeRange(start, end) {
  return `${formatDateTime(start)} - ${formatDateTime(end)}`
}

function buildProcessGantt(plans) {
  const processMap = new Map()
  const allDates = []

  plans.forEach((plan) => {
    const processes = Array.isArray(plan.processes_plan) ? plan.processes_plan : []
    processes.forEach((proc) => {
      if (!proc.process_id) return
      const startTime = new Date(proc.start_time)
      const endTime = new Date(proc.end_time)
      if (Number.isNaN(startTime.getTime()) || Number.isNaN(endTime.getTime())) return
      allDates.push(startTime, endTime)

      const key = proc.process_id
      if (!processMap.has(key)) {
        processMap.set(key, {
          process_id: proc.process_id,
          process_name: proc.process_name || '',
          process_number: proc.process_number || 0,
          items: [],
          itemsMap: new Map(),
        })
      }
      const procEntry = processMap.get(key)
      const outputProductId = proc.output_product_id != null ? proc.output_product_id : plan.product
      const outputProductCode = proc.output_product_code || plan.product_code || ''
      const outputProductName = proc.output_product_name || plan.product_name || ''
      const itemKey = outputProductCode || outputProductId
      let item = procEntry.itemsMap.get(itemKey)
      if (!item) {
        item = {
          product_id: outputProductId,
          product_code: outputProductCode,
          product_name: outputProductName,
          plan_qty: 0,
          sequence_no: plan.sequence_no != null ? Number(plan.sequence_no) : null,
          bars: [],
          barsMap: new Map(),
        }
        procEntry.itemsMap.set(itemKey, item)
        procEntry.items.push(item)
      }
      const qtyValue = Number(proc.quantity ?? plan.plan_qty ?? 0)
      if (proc.coproduct_group_key) {
        item.plan_qty = Math.max(item.plan_qty, qtyValue)
      } else {
        item.plan_qty += qtyValue
      }
      const seq = plan.sequence_no != null ? Number(plan.sequence_no) : null
      if (seq != null && (item.sequence_no == null || seq < item.sequence_no)) {
        item.sequence_no = seq
      }

      const barKey = proc.coproduct_group_key || `${plan.plan_id}_${proc.process_id}_${proc.output_product_id}`
      const existingBar = proc.coproduct_group_key ? item.barsMap.get(barKey) : null
      if (existingBar) {
        existingBar.startTime = new Date(Math.min(existingBar.startTime.getTime(), startTime.getTime()))
        existingBar.endTime = new Date(Math.max(existingBar.endTime.getTime(), endTime.getTime()))
        existingBar.durationMs = existingBar.endTime.getTime() - existingBar.startTime.getTime()
        existingBar.planQty = Math.max(existingBar.planQty, qtyValue)
      } else {
        const newBar = {
          key: barKey,
          planId: plan.plan_id,
          processId: proc.process_id,
          startTime,
          endTime,
          durationMs: endTime.getTime() - startTime.getTime(),
          planQty: qtyValue,
          color: getBarColor(outputProductId),
          label: '',
          leftPx: 0,
          widthPx: 0,
        }
        item.bars.push(newBar)
        if (proc.coproduct_group_key) {
          item.barsMap.set(barKey, newBar)
        }
      }
    })
  })

  if (!allDates.length) {
    timelineStart.value = null
    timelineEnd.value = null
    timelineSlots.value = []
    return []
  }

  const minDate = new Date(Math.min(...allDates.map((d) => d.getTime())))
  const maxDate = new Date(Math.max(...allDates.map((d) => d.getTime())))
  const startDate = new Date(minDate)
  const endDate = new Date(maxDate)
  endDate.setDate(endDate.getDate() + 1)

  timelineStart.value = startDate
  timelineEnd.value = endDate
  timelineSlots.value = buildTimelineSlots(startDate, endDate)

  const msPerDay = 1000 * 60 * 60 * 24
  processMap.forEach((procEntry) => {
    procEntry.items.sort((a, b) => {
      const aSeq = a.sequence_no != null ? a.sequence_no : Number.POSITIVE_INFINITY
      const bSeq = b.sequence_no != null ? b.sequence_no : Number.POSITIVE_INFINITY
      if (aSeq !== bSeq) return aSeq - bSeq
      return (a.product_code || '').localeCompare(b.product_code || '')
    })
    procEntry.items.forEach((item) => {
      item.bars.sort((a, b) => a.startTime - b.startTime)
      item.bars.forEach((bar) => {
        const left = ((bar.startTime.getTime() - startDate.getTime()) / msPerDay) * pixelsPerDay
        const width = Math.max(((bar.endTime.getTime() - bar.startTime.getTime()) / msPerDay) * pixelsPerDay, 20)
        bar.leftPx = left
        bar.widthPx = width
        bar.label = formatTimeRange(bar.startTime, bar.endTime)
      })
    })
  })

  return Array.from(processMap.values()).sort((a, b) => {
    const diff = (b.process_number || 0) - (a.process_number || 0)
    if (diff !== 0) return diff
    return (b.process_id || 0) - (a.process_id || 0)
  })
}

function getBarColor(productId) {
  const colors = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#fb923c']
  const hash = (productId || 0) % colors.length
  return colors[hash]
}

watch(
  () => props.presetBaseDate,
  (val) => {
    if (val) baseDate.value = String(val)
  },
  { immediate: true }
)

watch(
  () => props.presetLine,
  async (val) => {
    selectedLine.value = val ? String(val) : ''
    if (selectedLine.value && props.embedded) {
      await loadData()
    }
  },
  { immediate: true }
)

onMounted(async () => {
  try {
    await Promise.all([fetchLines()])
    if (props.embedded) {
      if (selectedLine.value) {
        await loadData()
      }
      return
    }
    const qLine = route.query.line
    const qBase = route.query.base || route.query.base_date
    if (qBase) {
      baseDate.value = String(qBase)
    }
    if (qLine) {
      selectedLine.value = qLine
      await loadData()
    }
  } catch (e) {
    console.error('初期データ取得エラー', e)
  }
})
</script>

<style scoped>
.gantt-container {
  padding: 10px;
  background: #f3f4f6;
  min-height: 100vh;
  font-family: 'Noto Sans JP', sans-serif;
}
[data-embedded='true'] {
  padding: 0;
  background: transparent;
  min-height: auto;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}
.toolbar-left {
  display: flex;
  gap: 12px;
}
.toolbar-right {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field label {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}
.field input,
.field select {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}
.btn {
  padding: 8px 16px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.btn:hover {
  background: #f9fafb;
}
.btn.primary {
  background: #2563eb;
  color: #fff;
  border-color: #1d4ed8;
}
.btn.primary:hover {
  background: #1d4ed8;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.gantt-wrapper {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.gantt-scroll {
  overflow-x: auto;
}
.process-gantt-card {
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px;
}
.process-gantt-head {
  margin-bottom: 6px;
}
.process-info {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}
.process-name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}
.process-sub {
  font-size: 12px;
  color: #6b7280;
}
.gantt-chart {
  display: flex;
  flex-direction: column;
  position: relative;
}
.timeline-header {
  display: flex;
  border-bottom: 2px solid #374151;
  margin-bottom: 4px;
}
.timeline-label {
  width: 120px;
  min-width: 120px;
  padding: 4px 8px;
  font-size: 13px;
  font-weight: 700;
  background: #f3f4f6;
  border-right: 1px solid #d1d5db;
  display: flex;
  align-items: center;
  justify-content: center;
  position: sticky;
  left: 0;
  z-index: 3;
}
.timeline-axis {
  display: flex;
  flex: 1;
  background: #f9fafb;
}
.time-slot-header {
  border-right: 1px solid #e5e7eb;
  text-align: left;
  font-size: 11px;
  padding: 4px 6px;
  background: #f9fafb;
  display: flex;
  flex-direction: column;
  gap: 2px;
  justify-content: center;
}
.time-slot-header.sat {
  background: #dbeafe;
}
.time-slot-header.sun {
  background: #fecaca;
}
.time-slot-day {
  font-size: 10px;
  font-weight: 700;
  color: #111827;
}
.time-slot-label {
  white-space: nowrap;
}
.gantt-row {
  display: flex;
  border-bottom: 1px solid #e5e7eb;
  min-height: 42px;
  position: relative;
}
.gantt-row-label {
  position: sticky;
  left: 0;
  z-index: 2;
  width: 120px;
  min-width: 120px;
  padding: 4px 6px;
  border-right: 1px solid #d1d5db;
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: #fafafa;
}
.product-code {
  font-size: 13px;
  font-weight: 700;
  color: #111827;
}
.product-qty {
  font-size: 11px;
  color: #374151;
}
.gantt-row-bars {
  position: relative;
  flex: 1;
  min-height: 36px;
}
.gantt-bar-wrapper {
  position: absolute;
  top: 6px;
  height: 28px;
  display: flex;
  align-items: center;
  cursor: grab;
  user-select: none;
}
.gantt-bar {
  height: 100%;
  width: 100%;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding-left: 48px;
  box-sizing: border-box;
}
.gantt-bar-label {
  white-space: nowrap;
  padding: 0 6px;
}
.lot-badge {
  position: absolute;
  left: 8px;
  background: #111827;
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}
.no-data {
  padding: 20px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
}
.empty-message {
  padding: 40px;
  text-align: center;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  color: #6b7280;
  font-size: 14px;
}
</style>
