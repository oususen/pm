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
        <button class="btn" @click="saveSchedule" :disabled="mergeConsecutive || !processGanttData.length">
          保存
        </button>
      </div>
    </div>

    <div v-if="processGanttData.length" class="gantt-wrapper">
      <div class="view-mode-bar">
        <span class="view-mode-label">表示モード</span>
        <button
          type="button"
          class="mode-btn"
          :class="{ active: !mergeConsecutive }"
          @click="mergeConsecutive = false"
        >
          分解
        </button>
        <button
          type="button"
          class="mode-btn"
          :class="{ active: mergeConsecutive }"
          @click="mergeConsecutive = true"
        >
          連結（同一製品の連続をまとめる）
        </button>
        <span class="view-mode-hint">連結中は編集・保存を無効化</span>
      </div>
      <div class="gantt-scroll">
        <!-- 各工程のガントチャート -->
        <div
          v-for="proc in renderedProcessGantt"
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
            <div
              v-if="workBands.length || workMarkers.length"
              class="gantt-guides"
              :style="{ width: timelineWidthPx + 'px' }"
            >
              <div
                v-for="band in workBands"
                :key="band.key"
                class="gantt-guide-band"
                :style="{ left: band.leftPx + 'px', width: band.widthPx + 'px' }"
              ></div>
              <div
                v-for="marker in workMarkers"
                :key="marker.key"
                class="gantt-guide-line"
                :class="marker.type"
                :style="{ left: marker.leftPx + 'px' }"
              ></div>
            </div>
            <!-- タイムライン ヘッダー -->
            <div class="timeline-header">
              <div class="timeline-label">品番</div>
              <div class="timeline-axis" :style="{ width: timelineWidthPx + 'px' }">
                <div
                  v-for="slot in timelineSlots"
                  :key="slot.key"
                  class="time-slot-header"
                  :class="slot.dayClass"
                  :style="{ width: pixelsPerSlot + 'px' }"
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
              </div>
              <div class="gantt-row-bars" :style="{ width: timelineWidthPx + 'px' }">
                <div
                  v-for="bar in item.displayBars || item.bars"
                  :key="bar.key"
                  class="gantt-bar-wrapper"
                  :style="{
                    left: bar.leftPx + 'px',
                    width: bar.widthPx + 'px',
                  }"
                  :data-plan-id="bar.planId"
                  :data-process-id="bar.processId"
                  :data-output-product-id="bar.outputProductId"
                  :data-duration-ms="bar.durationMs"
                  :data-quantity="bar.planQty"
                  :data-quantity-edited="bar.quantityEdited ? '1' : ''"
                  @mousedown="onBarMouseDown"
                >
                  <div
                    class="gantt-bar"
                    :style="{
                      backgroundColor: bar.color,
                    }"
                  >
                    <span class="gantt-bar-label">
                      <span class="plan-qty" @mousedown.stop @click.stop="openQuantityEdit(bar)">{{ formatQuantity(bar.planQty) }}</span>
                      <span class="qty-separator">|</span>
                      <span class="start-time" @mousedown.stop @click.stop="openStartTimeEdit(bar)">{{ bar.startLabel }}</span>
                      <span class="time-separator">-</span>
                      <span class="end-time">{{ bar.endLabel }}</span>
                      <span v-if="bar.durationLabel" class="duration">({{ bar.durationLabel }})</span>
                    </span>
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
import { ref, computed, onMounted, watch, defineProps, defineExpose, defineEmits } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  presetLine: { type: [String, Number], default: '' },
  presetBaseDate: { type: String, default: '' },
  presetStartDate: { type: String, default: '' },
  presetEndDate: { type: String, default: '' },
})
const emit = defineEmits(['dirty-change'])
const TANK_LINE_CODE = 'L2200'
const TANK_PRODUCT_ORDER = [
  'YD60003386',
  'YD60011305',
  'YD60000441',
  'YD60008491',
  'YD60009848',
  'YD60014764',
]

const route = useRoute()
const selectedLine = ref('')
const baseDate = ref(new Date().toISOString().slice(0, 10))
const lines = ref([])
const processGanttData = ref([])
const mergeConsecutive = ref(false)
const slotHours = 4
const pixelsPerSlot = 80
const mergeGapToleranceMs = 60 * 1000 // 連続とみなす隙間（1分）
const workStartFallback = { hour: 8, minute: 0 }
const workMinutesFallback = 480
const timelineStart = ref(null)
const timelineEnd = ref(null)
const timelineSlots = ref([])
const hasUnsavedChanges = ref(false)
const debugEnabled = true
const calendarDayMap = ref({})
const workPatternMap = ref({})
const selectedLineObj = computed(() =>
  lines.value.find((l) => String(l.id) === String(selectedLine.value))
)
const tankOrderMap = computed(() => new Map(TANK_PRODUCT_ORDER.map((code, idx) => [code, idx])))
const isTankLine = computed(() => selectedLineObj.value?.line_code === TANK_LINE_CODE)

const logDebug = (...args) => {
  if (debugEnabled) console.info('[ProcessGanttView]', ...args)
}

const setUnsavedChanges = (isDirty) => {
  const next = !!isDirty
  if (hasUnsavedChanges.value === next) return
  hasUnsavedChanges.value = next
  emit('dirty-change', next)
}

const displayDays = computed(() => {
  if (props.presetStartDate && props.presetEndDate) {
    return buildDisplayDays(props.presetStartDate, props.presetEndDate)
  }
  const base = new Date(baseDate.value)
  const days = []
  for (let offset = -2; offset <= 2; offset++) {
    const d = new Date(base)
    d.setDate(d.getDate() + offset)
    days.push({ date: d.toISOString().slice(0, 10), label: formatDayLabel(d) })
  }
  return days
})

const timelineWidthPx = computed(() => timelineSlots.value.length * pixelsPerSlot)
const workMarkers = computed(() => {
  if (!timelineStart.value || !timelineEnd.value) return []
  const markers = []
  const start = new Date(timelineStart.value)
  const end = new Date(timelineEnd.value)
  const cursor = new Date(start)
  cursor.setHours(0, 0, 0, 0)
  const msPerSlot = slotHours * 60 * 60 * 1000
  while (cursor <= end) {
    const dateKey = formatDateKey(cursor)
    const workStart = getWorkStartForDate(dateKey)
    if (!workStart) {
      cursor.setDate(cursor.getDate() + 1)
      continue
    }
    const startMarkerTime = new Date(cursor)
    startMarkerTime.setHours(workStart.hour, workStart.minute, 0, 0)
    const startLeftPx = ((startMarkerTime.getTime() - start.getTime()) / msPerSlot) * pixelsPerSlot
    if (startLeftPx >= 0 && startLeftPx <= timelineWidthPx.value) {
      markers.push({
        key: `${dateKey}-start-${workStart.hour}-${workStart.minute}`,
        leftPx: startLeftPx,
        type: 'start',
      })
    }

    const workEnd = getWorkEndForDate(dateKey, workStart)
    if (workEnd) {
      const endMarkerTime = new Date(cursor)
      endMarkerTime.setDate(endMarkerTime.getDate() + workEnd.dayOffset)
      endMarkerTime.setHours(workEnd.hour, workEnd.minute, 0, 0)
      const endLeftPx = ((endMarkerTime.getTime() - start.getTime()) / msPerSlot) * pixelsPerSlot
      if (endLeftPx >= 0 && endLeftPx <= timelineWidthPx.value) {
        markers.push({
          key: `${dateKey}-end-${workEnd.hour}-${workEnd.minute}-${workEnd.dayOffset}`,
          leftPx: endLeftPx,
          type: 'end',
        })
      }
    }
    cursor.setDate(cursor.getDate() + 1)
  }
  return markers
})

const workBands = computed(() => {
  if (!timelineStart.value || !timelineEnd.value) return []
  const bands = []
  const start = new Date(timelineStart.value)
  const end = new Date(timelineEnd.value)
  const cursor = new Date(start)
  cursor.setHours(0, 0, 0, 0)
  const msPerSlot = slotHours * 60 * 60 * 1000
  while (cursor <= end) {
    const dateKey = formatDateKey(cursor)
    const workStart = getWorkStartForDate(dateKey)
    if (!workStart) {
      cursor.setDate(cursor.getDate() + 1)
      continue
    }
    const workEnd = getWorkEndForDate(dateKey, workStart)
    if (!workEnd) {
      cursor.setDate(cursor.getDate() + 1)
      continue
    }
    const startTime = new Date(cursor)
    startTime.setHours(workStart.hour, workStart.minute, 0, 0)
    const endTime = new Date(cursor)
    endTime.setDate(endTime.getDate() + workEnd.dayOffset)
    endTime.setHours(workEnd.hour, workEnd.minute, 0, 0)
    const startMs = startTime.getTime()
    const endMs = endTime.getTime()
    if (endMs > startMs) {
      const clampedStart = Math.max(startMs, start.getTime())
      const clampedEnd = Math.min(endMs, end.getTime())
      if (clampedEnd > clampedStart) {
        const leftPx = ((clampedStart - start.getTime()) / msPerSlot) * pixelsPerSlot
        const widthPx = ((clampedEnd - clampedStart) / msPerSlot) * pixelsPerSlot
        bands.push({
          key: `${dateKey}-${clampedStart}`,
          leftPx,
          widthPx,
        })
      }
    }
    cursor.setDate(cursor.getDate() + 1)
  }
  return bands
})

const renderedProcessGantt = computed(() =>
  processGanttData.value.map((proc) => ({
    ...proc,
    items: proc.items.map((item) => ({
      ...item,
      displayBars: mergeConsecutive.value ? mergeBars(item.bars) : item.bars,
    })),
  }))
)

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

const formatDateKey = (dateObj) => {
  return `${dateObj.getFullYear()}-${pad2(dateObj.getMonth() + 1)}-${pad2(dateObj.getDate())}`
}

const parseTimeParts = (value) => {
  if (!value) return null
  const parts = String(value).split(':')
  if (parts.length < 2) return null
  const hour = Number(parts[0])
  const minute = Number(parts[1])
  if (Number.isNaN(hour) || Number.isNaN(minute)) return null
  return { hour, minute }
}

const getWorkStartForDate = (dateKey) => {
  const day = calendarDayMap.value[dateKey]
  if (day && day.is_working_day === false) return null
  if (day && day.work_pattern) {
    const pattern = workPatternMap.value[String(day.work_pattern)]
    const parsed = parseTimeParts(pattern?.start_time)
    if (parsed) return parsed
  }
  return workStartFallback
}

const getWorkEndForDate = (dateKey, startParts) => {
  const day = calendarDayMap.value[dateKey]
  if (day && day.is_working_day === false) return null
  const start = startParts || workStartFallback
  let endParts = null
  let dayOffset = 0

  if (day && day.work_pattern) {
    const pattern = workPatternMap.value[String(day.work_pattern)]
    const parsed = parseTimeParts(pattern?.end_time)
    if (parsed) {
      endParts = parsed
      if (parsed.hour < start.hour || (parsed.hour === start.hour && parsed.minute <= start.minute)) {
        dayOffset = 1
      }
    }
  }

  if (!endParts) {
    const workMinutes = day && day.work_minutes != null ? Number(day.work_minutes) : workMinutesFallback
    if (!Number.isFinite(workMinutes)) return null
    const startMinutes = start.hour * 60 + start.minute
    const endMinutesTotal = Math.max(0, startMinutes + workMinutes)
    dayOffset = Math.floor(endMinutesTotal / (24 * 60))
    const endMinutesInDay = endMinutesTotal % (24 * 60)
    endParts = {
      hour: Math.floor(endMinutesInDay / 60),
      minute: endMinutesInDay % 60,
    }
  }

  return { ...endParts, dayOffset }
}

const loadWorkPatternData = async (lineId, startDate, endDate) => {
  calendarDayMap.value = {}
  workPatternMap.value = {}
  if (!lineId) return

  let calendarId = null
  const line = lines.value.find((item) => String(item.id) === String(lineId))
  if (line && line.calendar) {
    calendarId = line.calendar
  } else {
    try {
      const lineRes = await api.lines.getLine(lineId)
      calendarId = lineRes.data?.calendar ?? null
    } catch (e) {
      console.error('ライン勤務カレンダ取得エラー', e)
      calendarId = null
    }
  }
  if (!calendarId) return

  try {
    const daysRes = await api.calendars.getCalendarDays(calendarId)
    const days = daysRes.data?.results || daysRes.data || []
    const filtered = days.filter((day) => {
      if (!day.target_date) return false
      if (startDate && day.target_date < startDate) return false
      if (endDate && day.target_date > endDate) return false
      return true
    })
    const dayMap = {}
    const patternIds = new Set()
    filtered.forEach((day) => {
      dayMap[day.target_date] = day
      if (day.work_pattern) patternIds.add(String(day.work_pattern))
    })
    calendarDayMap.value = dayMap
    if (patternIds.size) {
      const patternsRes = await api.workPatterns.getWorkPatterns()
      const patterns = patternsRes.data?.results || patternsRes.data || []
      const patternMap = {}
      patterns.forEach((pattern) => {
        patternMap[String(pattern.id)] = pattern
      })
      workPatternMap.value = patternMap
    }
  } catch (e) {
    console.error('勤務パターン取得エラー', e)
  }
}

const loadData = async () => {
  if (!selectedLine.value) return
  setUnsavedChanges(false)
  processGanttData.value = []

  try {
    const startDate = displayDays.value[0].date
    const endDate = displayDays.value[displayDays.value.length - 1].date

    logDebug('loadData', { line: selectedLine.value, startDate, endDate })
    await loadWorkPatternData(selectedLine.value, startDate, endDate)
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
  setUnsavedChanges(false)
  processGanttData.value = []

  try {
    const startDate = displayDays.value[0].date
    const endDate = displayDays.value[displayDays.value.length - 1].date
    logDebug('generateSchedule', { line: selectedLine.value, startDate, endDate, clearExisting })
    await loadWorkPatternData(selectedLine.value, startDate, endDate)
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
  if (mergeConsecutive.value) {
    alert('連結表示では保存できません。分解表示に切り替えてください。')
    return
  }
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
  const msPerSlot = slotHours * 60 * 60 * 1000
  const msPerPixel = msPerSlot / pixelsPerSlot
  bars.forEach((bar) => {
    const planId = bar.dataset.planId
    const processId = Number(bar.dataset.processId)
    const durationMs = Number(bar.dataset.durationMs)
    if (!planId || !processId || !durationMs) return

    const currentLeft = parseFloat(bar.style.left || '0')
    const newStartMs = timelineStart.value.getTime() + (currentLeft * msPerPixel)

    const roundMs = 1000 * 60 * 5
    const roundedStartMs = Math.round(newStartMs / roundMs) * roundMs
    const finalStart = new Date(roundedStartMs)
    const finalEnd = new Date(roundedStartMs + durationMs)

    const payload = {
      plan_id: planId,
      process_id: processId,
      start_time: toLocalISO(finalStart),
      end_time: toLocalISO(finalEnd),
    }
    const outputProductId = Number(bar.dataset.outputProductId)
    if (Number.isFinite(outputProductId) && outputProductId > 0) {
      payload.output_product_id = outputProductId
    }
    const quantityEdited = bar.dataset.quantityEdited === '1'
    const quantityRaw = bar.dataset.quantity
    const quantityValue = Number(quantityRaw)
    if (
      quantityEdited &&
      quantityRaw !== undefined &&
      quantityRaw !== null &&
      quantityRaw !== '' &&
      Number.isFinite(quantityValue) &&
      quantityValue > 0
    ) {
      payload.quantity = Math.round(quantityValue * 1000) / 1000
    }

    updates.push(payload)
  })

  if (!updates.length) {
    alert('保存対象のデータがありません')
    return
  }

  try {
    logDebug('saveSchedule', { updates: updates.length })
    await api.lineGanttPlans.bulkUpdate(updates)
    clearQuantityEditedFlags()
    setUnsavedChanges(false)
    alert('保存しました')
  } catch (e) {
    console.error('保存エラー', e)
    alert('保存に失敗しました')
  }
}

const clearQuantityEditedFlags = () => {
  processGanttData.value.forEach((proc) => {
    if (!proc.items) return
    proc.items.forEach((item) => {
      if (!item.bars) return
      item.bars.forEach((bar) => {
        bar.quantityEdited = false
      })
    })
  })
}

defineExpose({ saveSchedule })

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

function onBarMouseDown(e) {
  if (mergeConsecutive.value) {
    alert('連結表示中はバー編集できません。分解表示に切り替えてください。')
    return
  }
  handleDragStart(e)
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
  const msPerSlot = slotHours * 60 * 60 * 1000
  const msPerPixel = msPerSlot / pixelsPerSlot
  const currentLeft = parseFloat(draggedBar.style.left || '0')
  const newStartMs = timelineStart.value.getTime() + (currentLeft * msPerPixel)
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
    setUnsavedChanges(true)
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

function buildDisplayDays(startStr, endStr) {
  const start = new Date(startStr)
  const end = new Date(endStr)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return []
  const from = start <= end ? start : end
  const to = start <= end ? end : start
  const days = []
  const current = new Date(from)
  while (current <= to) {
    days.push({ date: current.toISOString().slice(0, 10), label: formatDayLabel(current) })
    current.setDate(current.getDate() + 1)
  }
  return days
}

function floorToSlot(date) {
  const d = new Date(date)
  const base = new Date(d)
  base.setHours(0, 0, 0, 0)
  const minutes = Math.floor((d.getTime() - base.getTime()) / 60000)
  const slotMinutes = slotHours * 60
  const slotStartMinutes = Math.floor(minutes / slotMinutes) * slotMinutes
  return new Date(base.getTime() + slotStartMinutes * 60000)
}

function ceilToSlot(date) {
  const d = new Date(date)
  const base = new Date(d)
  base.setHours(0, 0, 0, 0)
  const slotMinutes = slotHours * 60
  const minutes = Math.floor((d.getTime() - base.getTime()) / 60000)
  const remainder = minutes % slotMinutes
  const isExact = remainder === 0 && d.getMinutes() === 0 && d.getSeconds() === 0 && d.getMilliseconds() === 0
  if (isExact) {
    return new Date(d)
  }
  const slotStartMinutes = Math.floor(minutes / slotMinutes) * slotMinutes + slotMinutes
  return new Date(base.getTime() + slotStartMinutes * 60000)
}

function buildTimelineSlots(startDate, endDate) {
  const slots = []
  const current = new Date(startDate)
  while (current < endDate) {
    slots.push({
      key: current.toISOString(),
      dayLabel: current.getHours() === 0 ? formatDayLabel(current) : '',
      label: formatTime(current),
      dayClass: getDayClass(current.toISOString().slice(0, 10)),
    })
    current.setHours(current.getHours() + slotHours)
  }
  return slots
}

function formatDateTime(date) {
  return `${date.getDate()} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`
}

function formatMinutesLabel(minutes) {
  if (!Number.isFinite(minutes) || minutes <= 0) return ''
  const rounded = Math.round(minutes * 10) / 10
  return Number.isInteger(rounded) ? String(rounded) : rounded.toString()
}

function formatQuantity(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0'
  const rounded = Math.round(num * 1000) / 1000
  if (Number.isInteger(rounded)) return String(rounded)
  return rounded.toString().replace(/(\.\d*?[1-9])0+$/, '$1').replace(/\.0+$/, '')
}

function parseQuantityInput(value) {
  if (value === null || value === undefined) return null
  const normalized = String(value).trim()
  if (!normalized) return null
  if (!/^\d+(\.\d+)?$/.test(normalized)) return null
  const parsed = Number(normalized)
  if (!Number.isFinite(parsed) || parsed <= 0) return null
  return Math.round(parsed * 1000) / 1000
}

function formatTimeRange(start, end) {
  return `${formatDateTime(start)} - ${formatDateTime(end)}`
}

function formatDateTimeInput(date) {
  const y = date.getFullYear()
  const m = pad2(date.getMonth() + 1)
  const d = pad2(date.getDate())
  const hh = pad2(date.getHours())
  const mm = pad2(date.getMinutes())
  return `${y}-${m}-${d} ${hh}:${mm}`
}

function parseDateTimeInput(value) {
  if (!value) return null
  const trimmed = String(value).trim()
  const match = trimmed.match(/^(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})$/)
  if (!match) return null
  const y = Number(match[1])
  const m = Number(match[2])
  const d = Number(match[3])
  const hh = Number(match[4])
  const mm = Number(match[5])
  if (m < 1 || m > 12 || d < 1 || d > 31 || hh < 0 || hh > 23 || mm < 0 || mm > 59) return null
  const date = new Date(y, m - 1, d, hh, mm, 0, 0)
  if (Number.isNaN(date.getTime())) return null
  return date
}

function roundToFiveMinutes(date) {
  const ms = date.getTime()
  const roundMs = 1000 * 60 * 5
  return new Date(Math.round(ms / roundMs) * roundMs)
}

function updateBarDisplay(bar) {
  if (!timelineStart.value) return
  const msPerSlot = slotHours * 60 * 60 * 1000
  bar.leftPx = ((bar.startTime.getTime() - timelineStart.value.getTime()) / msPerSlot) * pixelsPerSlot
  bar.widthPx = Math.max((bar.durationMs / msPerSlot) * pixelsPerSlot, 20)
  bar.startLabel = formatDateTime(bar.startTime)
  bar.endLabel = formatDateTime(bar.endTime)
  bar.durationLabel = formatMinutesLabel(bar.totalMinutesRequired ?? bar.durationMs / 60000)
  bar.label = `${formatQuantity(bar.planQty)}|${bar.startLabel}-${bar.endLabel}${bar.durationLabel ? `(${bar.durationLabel})` : ''}`
}

function cloneBarForMerge(bar) {
  return {
    ...bar,
    startTime: new Date(bar.startTime),
    endTime: new Date(bar.endTime),
    durationMs: bar.durationMs,
    planQty: Number(bar.planQty || 0),
    totalMinutesRequired:
      Number.isFinite(Number(bar.totalMinutesRequired))
        ? Number(bar.totalMinutesRequired)
        : bar.durationMs / 60000,
    mergedPlanIds: [bar.planId || bar.key],
    key: `m-${bar.key}`,
  }
}

// 連結表示用に同一製品の連続バーをまとめる
function mergeBars(bars) {
  if (!mergeConsecutive.value) return bars
  if (!Array.isArray(bars) || bars.length <= 1 || !timelineStart.value) return bars

  const merged = []
  const sorted = [...bars].sort((a, b) => a.startTime - b.startTime)
  let current = null

  sorted.forEach((bar) => {
    const cloned = cloneBarForMerge(bar)
    if (!current) {
      current = cloned
      return
    }
    const gap = cloned.startTime.getTime() - current.endTime.getTime()
    if (gap >= -mergeGapToleranceMs && gap <= mergeGapToleranceMs) {
      current.endTime = new Date(cloned.endTime)
      current.durationMs = current.endTime.getTime() - current.startTime.getTime()
      current.planQty = Number(current.planQty || 0) + Number(cloned.planQty || 0)
      const baseMinutes = Number(current.totalMinutesRequired || current.durationMs / 60000)
      const addMinutes = Number(cloned.totalMinutesRequired || cloned.durationMs / 60000)
      current.totalMinutesRequired = baseMinutes + addMinutes
      current.mergedPlanIds.push(cloned.planId || cloned.key)
      current.key = `m-${current.mergedPlanIds.join('_')}`
    } else {
      updateBarDisplay(current)
      merged.push(current)
      current = cloned
    }
  })

  if (current) {
    updateBarDisplay(current)
    merged.push(current)
  }

  return merged
}

function openStartTimeEdit(bar) {
  if (!bar || !bar.startTime || !bar.durationMs) return
  if (mergeConsecutive.value) {
    alert('連結表示中は開始時刻を編集できません。分解表示に切り替えてください。')
    return
  }
  const input = window.prompt('開始日時を入力してください (YYYY-MM-DD HH:mm)', formatDateTimeInput(bar.startTime))
  if (!input) return
  const parsed = parseDateTimeInput(input)
  if (!parsed) {
    alert('日時の形式が正しくありません。例: 2026-01-07 08:30')
    return
  }
  const newStart = roundToFiveMinutes(parsed)
  const newEnd = new Date(newStart.getTime() + bar.durationMs)
  bar.startTime = newStart
  bar.endTime = newEnd
  updateBarDisplay(bar)
  setUnsavedChanges(true)
  alert('開始時間を変更しました。保存ボタンで確定してください。')
}

function openQuantityEdit(bar) {
  if (!bar) return
  if (mergeConsecutive.value) {
    alert('連結表示中は数量を編集できません。分解表示に切り替えてください。')
    return
  }
  const input = window.prompt('数量を入力してください（0より大きい数値）', formatQuantity(bar.planQty))
  if (input === null) return
  const parsed = parseQuantityInput(input)
  if (parsed === null) {
    alert('数量の形式が正しくありません。例: 18 または 18.5')
    return
  }
  bar.planQty = parsed
  bar.quantityEdited = true
  updateBarDisplay(bar)
  setUnsavedChanges(true)
  alert('数量を変更しました。保存ボタンで確定してください。')
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
          parent_product_code: plan.product_code || '',
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
        existingBar.totalMinutesRequired = Math.max(
          existingBar.totalMinutesRequired || 0,
          Number(proc.total_minutes_required ?? 0)
        )
      } else {
        const colorKey = plan.product || outputProductId
        const newBar = {
          key: barKey,
          planId: plan.plan_id,
          processId: proc.process_id,
          outputProductId: outputProductId,
          startTime,
          endTime,
          durationMs: endTime.getTime() - startTime.getTime(),
          planQty: qtyValue,
          quantityEdited: false,
          totalMinutesRequired: Number(proc.total_minutes_required ?? 0),
          color: getBarColor(colorKey),
          label: '',
          startLabel: '',
          endLabel: '',
          durationLabel: '',
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
  const startDate = floorToSlot(minDate)
  const endDate = ceilToSlot(maxDate)

  timelineStart.value = startDate
  timelineEnd.value = endDate
  timelineSlots.value = buildTimelineSlots(startDate, endDate)

  const msPerSlot = slotHours * 60 * 60 * 1000
  processMap.forEach((procEntry) => {
    procEntry.items.sort((a, b) => {
      const codeA = isTankLine.value ? (a.parent_product_code || a.product_code || '') : (a.product_code || '')
      const codeB = isTankLine.value ? (b.parent_product_code || b.product_code || '') : (b.product_code || '')
      if (isTankLine.value) {
        const priA = tankOrderMap.value.get(codeA) ?? Number.POSITIVE_INFINITY
        const priB = tankOrderMap.value.get(codeB) ?? Number.POSITIVE_INFINITY
        if (priA !== priB) return priA - priB
      }
      const aSeq = a.sequence_no != null ? a.sequence_no : Number.POSITIVE_INFINITY
      const bSeq = b.sequence_no != null ? b.sequence_no : Number.POSITIVE_INFINITY
      if (aSeq !== bSeq) return aSeq - bSeq
      return codeA.localeCompare(codeB)
    })
    procEntry.items.forEach((item) => {
      item.bars.sort((a, b) => a.startTime - b.startTime)
      item.bars.forEach((bar) => {
        updateBarDisplay(bar)
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
  // 冷色系パレット（ブルー/シアン/グリーン寄り）で統一
  const colors = ['#1d4ed8', '#0ea5e9', '#14b8a6', '#22c55e', '#6366f1', '#0891b2']
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
.view-mode-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px;
  font-size: 12px;
  color: #374151;
}
.view-mode-label {
  font-weight: 700;
}
.mode-btn {
  padding: 4px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 14px;
  background: #fff;
  font-size: 12px;
  cursor: pointer;
}
.mode-btn.active {
  background: #2563eb;
  color: #fff;
  border-color: #1d4ed8;
}
.mode-btn:hover {
  background: #f1f5f9;
}
.mode-btn.active:hover {
  background: #1d4ed8;
}
.view-mode-hint {
  color: #6b7280;
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
.gantt-guides {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 120px;
  pointer-events: none;
  z-index: 1;
}
.gantt-guide-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(34, 197, 94, 0.35);
}
.gantt-guide-line.end {
  background: rgba(239, 68, 68, 0.35);
}
.gantt-guide-band {
  position: absolute;
  top: 0;
  bottom: 0;
  background: rgba(239, 68, 68, 0.06);
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
  min-height: 23px;
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
.gantt-row-bars {
  position: relative;
  flex: 1;
  min-height: 30px;
}
.gantt-bar-wrapper {
  position: absolute;
  top: 3px;
  height: 24px;
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
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.3px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding-left: 4px;
  box-sizing: border-box;
  overflow: visible;
}
.gantt-bar-label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #111827;
  white-space: nowrap;
  padding: 0 4px;
  width: 100%;
  text-align: left;
  box-sizing: border-box;
  font-weight: 500;
  letter-spacing: 0.3px;
}
.plan-qty {
  font-weight: 700;
  color: #ffffff;
  background: rgba(0, 0, 0, 0.65);
  padding: 2px 4px;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: underline;
}
.plan-qty:hover {
  background: rgba(0, 0, 0, 0.8);
}
.qty-separator {
  margin: 0 4px 0 2px;
  font-weight: 700;
}
.duration {
  margin-left: 4px;
  font-size: 12px;
  color: #b91c1c;
}
.start-time {
  cursor: pointer;
  text-decoration: underline;
}
.start-time:hover {
  color: #1d4ed8;
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
