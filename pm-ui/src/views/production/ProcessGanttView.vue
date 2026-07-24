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
        <button class="btn" @click="saveEditChanges" :disabled="mergeConsecutive || !processGanttData.length || !hasEditChanges">
          時間数量保存
        </button>
        <button class="btn" @click="saveStructureChanges" :disabled="mergeConsecutive || !processGanttData.length || !hasStructureChanges">
          追加削除保存
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
        <div class="view-filter">
          <input
            v-model.trim="processKeyword"
            type="text"
            placeholder="工程で絞込"
            class="view-filter-input"
          />
          <input
            v-model.trim="productKeyword"
            type="text"
            placeholder="品番で絞込"
            class="view-filter-input"
          />
        </div>
        <span class="view-mode-count">{{ renderedProcessCount }}工程 / {{ renderedItemCount }}品番</span>
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
          <div
            class="gantt-chart"
            :style="{
              '--process-col-width': processColWidthPx + 'px',
              '--product-col-width': productColWidthPx + 'px',
              minWidth: chartContentWidthPx + 'px',
            }"
          >
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
              <div class="timeline-process-label">工程コード</div>
              <div class="timeline-label">品番</div>
              <div class="timeline-axis" :style="{ width: timelineWidthPx + 'px' }">
                <div
                  v-for="slot in visibleTimelineSlots"
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
              <div class="gantt-row-process">
                <div class="process-name-inline">{{ getProcessCode(proc) }}</div>
              </div>
              <div class="gantt-row-label">
                <div class="product-code">{{ item.product_code }}</div>
              </div>
              <div class="gantt-row-bars" :style="{ width: timelineWidthPx + 'px' }">
                <div
                  v-for="bar in item.displayBars || item.bars"
                  :key="bar.key"
                  class="gantt-bar-wrapper"
                  :class="{ 'is-temporary': bar.isTemporary }"
                  :title="buildBarTooltip(bar, item, proc)"
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
                  @mousedown="onBarMouseDown($event, bar)"
                >
                  <span v-if="bar.isDaySeqStart" class="seq-marker start">s</span>
                  <div
                    class="gantt-bar"
                    :style="{
                      backgroundColor: bar.color,
                    }"
                  >
                    <span class="gantt-bar-label" @mousedown.stop @click.stop="openBarEdit(bar)">
                      <span class="plan-qty">{{ formatQuantity(bar.planQty) }}</span>
                      <span class="qty-separator">|</span>
                      <span class="start-time">{{ bar.startLabel }}</span>
                      <span class="time-separator">-</span>
                      <span class="end-time">{{ bar.endLabel }}</span>
                      <span v-if="bar.durationLabel" class="duration">({{ bar.durationLabel }})</span>
                    </span>
                    <button
                      class="gantt-bar-delete-btn"
                      title="このバーを削除"
                      @mousedown.stop
                      @click.stop="deleteBar(bar)"
                    >×</button>
                  </div>
                  <span v-if="bar.isDaySeqEnd" class="seq-marker end">e</span>
                </div>
                <button
                  v-if="props.showAddAnchors"
                  v-for="anchor in rowAddAnchors"
                  :key="`add-${idx}-${anchor.key}`"
                  type="button"
                  class="gantt-row-add-btn"
                  :style="{ left: Math.max(anchor.leftPx - 10, 2) + 'px' }"
                  :title="`${anchor.dateKey} 17:00付近に追加`"
                  :disabled="manualAddLoading || mergeConsecutive || !item.product_id"
                  @click.stop="openManualAdd(proc, item, anchor)"
                >
                  +
                </button>
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
    <div v-if="barEditDialog.visible" class="bar-edit-overlay" @click.self="closeBarEditDialog">
      <div class="bar-edit-dialog">
        <h4>ガント編集</h4>
        <p v-if="barEditDialog.productCode" class="bar-edit-product">品番: {{ barEditDialog.productCode }}</p>
        <div class="bar-edit-grid">
          <label>数量<input v-model="barEditDialog.qty" type="text" placeholder="例: 30" /></label>
          <label>日<input v-model="barEditDialog.day" type="text" placeholder="例: 502" /></label>
          <label>時間<input v-model="barEditDialog.time" type="text" placeholder="例: 1120" /></label>
        </div>
        <div class="bar-edit-option-row">
          <label class="bar-edit-check">
            <input v-model="barEditDialog.cascadeBySeq" type="checkbox" />
            同工程の後続SEQNOも時間を連鎖更新する
          </label>
        </div>
        <p class="bar-edit-hint">日: MDD/MMDD（502=5月2日） 時間: HMM/HHMM（1120=11:20）</p>
        <ol class="bar-edit-steps">
          <li>入力ボックスにカーソルを合わせる</li>
          <li>ダブルクリックで元の数値を全選択</li>
          <li>新しい値を入力</li>
          <li>Tabキーで次の入力枠へ移動</li>
          <li>数量→日→時間をすべて入力</li>
          <li>OKを押す</li>
          <li>最後に「時間数量保存」で確定</li>
        </ol>
        <div class="bar-edit-actions">
          <button class="btn" @click="closeBarEditDialog">キャンセル</button>
          <button class="btn primary" @click="applyBarEditFromDialog">OK</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { ref, computed, onMounted, watch, defineProps, defineExpose, defineEmits } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

const props = defineProps({
  embedded: { type: Boolean, default: false },
  presetLine: { type: [String, Number], default: '' },
  presetBaseDate: { type: String, default: '' },
  presetStartDate: { type: String, default: '' },
  presetEndDate: { type: String, default: '' },
  filterProcessId: { type: [String, Number], default: '' },
  autoGenerateIfEmpty: { type: Boolean, default: true },
  showAddAnchors: { type: Boolean, default: true },
  hideEmptyRows: { type: Boolean, default: false },
})
const emit = defineEmits(['dirty-change', 'mode-change', 'edit-dirty-change', 'structure-dirty-change'])
const TANK_LINE_CODE = 'L2200'
const L2201_LINE_CODE = 'L2201'
const FLOOR_4001_COPRODUCT_CHILD_DISPLAY_EXCEPTION_CODES = new Set(['YD40002683'])
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
const baseDate = ref(formatISODate(new Date()))
const lines = ref([])
const processGanttData = ref([])
const mergeConsecutive = ref(false)
const HIDE_WEEKENDS_KEY = 'processGanttView.hideWeekends'
const hideWeekends = ref(localStorage.getItem(HIDE_WEEKENDS_KEY) === '1')
const processKeyword = ref('')
const productKeyword = ref('')
const slotHours = 4
const pixelsPerSlot = 80
const mergeGapToleranceMs = 60 * 1000 // 連続とみなす隙間（1分）
const sameBusinessDayMergeGapToleranceMs = 120 * 60 * 1000 // 同一稼働日内なら最大120分の分断を連結
const businessDayBoundaryHour = 8
const manualAddAnchorHour = 17
const manualAddAnchorMinute = 0
const processColWidthPx = 75
const productColWidthPx = 120
const workStartFallback = { hour: 8, minute: 0 }
const workMinutesFallback = 480
const timelineStart = ref(null)
const timelineEnd = ref(null)
const timelineSlots = ref([])
const hasUnsavedChanges = ref(false)
const hasEditChanges = ref(false)
const hasStructureChanges = ref(false)
const manualAddLoading = ref(false)
const pendingDeletes = ref([])
const debugEnabled = true
const calendarDayMap = ref({})
const workPatternMap = ref({})
const daisoCalendarId = ref(undefined)
const processOutputCandidatesMap = ref({})
const processCoproductChildMap = ref({})
const processCodeMap = ref({})
const barEditDialog = ref({
  visible: false,
  bar: null,
  productCode: '',
  qty: '',
  day: '',
  time: '',
  cascadeBySeq: false,
})
const selectedLineObj = computed(() =>
  lines.value.find((l) => String(l.id) === String(selectedLine.value))
)
const tankOrderMap = computed(() => new Map(TANK_PRODUCT_ORDER.map((code, idx) => [code, idx])))
const isTankLine = computed(() => selectedLineObj.value?.line_code === TANK_LINE_CODE)
const isL2201Line = computed(
  () => String(selectedLineObj.value?.line_code || '').trim().toUpperCase() === L2201_LINE_CODE
)

const logDebug = (...args) => {
  if (debugEnabled) console.info('[ProcessGanttView]', ...args)
}

const emitDirtyState = () => {
  const nextOverall = hasEditChanges.value || hasStructureChanges.value
  if (hasUnsavedChanges.value !== nextOverall) {
    hasUnsavedChanges.value = nextOverall
    emit('dirty-change', nextOverall)
  }
  emit('edit-dirty-change', hasEditChanges.value)
  emit('structure-dirty-change', hasStructureChanges.value)
}

const setEditDirty = (isDirty) => {
  const next = !!isDirty
  if (hasEditChanges.value === next) return
  hasEditChanges.value = next
  emitDirtyState()
}

const setStructureDirty = (isDirty) => {
  const next = !!isDirty
  if (hasStructureChanges.value === next) return
  hasStructureChanges.value = next
  emitDirtyState()
}

const setMergeConsecutive = (isMerged) => {
  mergeConsecutive.value = !!isMerged
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
    days.push({ date: formatISODate(d), label: formatDayLabel(d) })
  }
  return days
})

const visibleTimelineSlots = computed(() => {
  if (!hideWeekends.value) return timelineSlots.value
  return timelineSlots.value.filter(s => s.dayClass !== 'sat' && s.dayClass !== 'sun')
})

const normalizedProcessKeyword = computed(() => String(processKeyword.value || '').trim().toLowerCase())
const normalizedProductKeyword = computed(() => String(productKeyword.value || '').trim().toLowerCase())

const weekendMsRanges = computed(() => {
  if (!hideWeekends.value) return []
  const msPerSlot = slotHours * 60 * 60 * 1000
  const ranges = []
  for (const slot of timelineSlots.value) {
    if (slot.dayClass === 'sat' || slot.dayClass === 'sun') {
      const start = new Date(slot.key).getTime()
      if (ranges.length > 0 && ranges[ranges.length - 1].end === start) {
        ranges[ranges.length - 1].end = start + msPerSlot
      } else {
        ranges.push({ start, end: start + msPerSlot })
      }
    }
  }
  return ranges
})

function getWeekendMsBefore(timeMs) {
  if (!hideWeekends.value || !timelineStart.value) return 0
  const startMs = timelineStart.value.getTime()
  let total = 0
  for (const range of weekendMsRanges.value) {
    if (range.end <= startMs) continue
    if (range.start >= timeMs) break
    const overlapStart = Math.max(range.start, startMs)
    const overlapEnd = Math.min(range.end, timeMs)
    if (overlapEnd > overlapStart) total += overlapEnd - overlapStart
  }
  return total
}

function timeToCollapsedPx(timeMs) {
  if (!timelineStart.value) return 0
  const msPerSlot = slotHours * 60 * 60 * 1000
  const rawMs = timeMs - timelineStart.value.getTime()
  const weekendMs = getWeekendMsBefore(timeMs)
  return ((rawMs - weekendMs) / msPerSlot) * pixelsPerSlot
}

function collapsedPxToTimeMs(px) {
  if (!timelineStart.value) return 0
  const msPerSlot = slotHours * 60 * 60 * 1000
  const targetCollapsedMs = (px / pixelsPerSlot) * msPerSlot
  const startMs = timelineStart.value.getTime()
  let accumulatedCollapsed = 0
  let currentRealMs = startMs
  for (const range of weekendMsRanges.value) {
    const nonWeekendBefore = range.start - currentRealMs
    if (accumulatedCollapsed + nonWeekendBefore >= targetCollapsedMs) {
      return currentRealMs + (targetCollapsedMs - accumulatedCollapsed)
    }
    accumulatedCollapsed += nonWeekendBefore
    currentRealMs = range.end
  }
  return currentRealMs + (targetCollapsedMs - accumulatedCollapsed)
}

const timelineWidthPx = computed(() => visibleTimelineSlots.value.length * pixelsPerSlot)
const chartContentWidthPx = computed(() => processColWidthPx + productColWidthPx + timelineWidthPx.value)
const rowAddAnchors = computed(() => {
  if (!timelineStart.value || !timelineEnd.value) return []
  const anchors = []
  const startMs = timelineStart.value.getTime()
  const endMs = timelineEnd.value.getTime()
  const cursor = new Date(timelineStart.value)
  cursor.setHours(0, 0, 0, 0)

  while (cursor.getTime() < endMs) {
    const dateKey = formatDateKey(cursor)
    const dayClass = getDayClass(dateKey)
    if (hideWeekends.value && (dayClass === 'sat' || dayClass === 'sun')) {
      cursor.setDate(cursor.getDate() + 1)
      continue
    }
    const workStart = getWorkStartForDate(dateKey)
    if (!workStart) {
      cursor.setDate(cursor.getDate() + 1)
      continue
    }

    const anchorTime = new Date(cursor)
    anchorTime.setHours(manualAddAnchorHour, manualAddAnchorMinute, 0, 0)
    const anchorMs = anchorTime.getTime()
    if (anchorMs >= startMs && anchorMs < endMs) {
      anchors.push({
        key: dateKey,
        dateKey: dateKey,
        leftPx: timeToCollapsedPx(anchorMs),
        startAt: anchorTime,
      })
    }
    cursor.setDate(cursor.getDate() + 1)
  }
  return anchors
})
const workMarkers = computed(() => {
  if (!timelineStart.value || !timelineEnd.value) return []
  const markers = []
  const end = new Date(timelineEnd.value)
  const cursor = new Date(timelineStart.value)
  cursor.setHours(0, 0, 0, 0)
  while (cursor <= end) {
    const dateKey = formatDateKey(cursor)
    const dayClass = getDayClass(dateKey)
    if (hideWeekends.value && (dayClass === 'sat' || dayClass === 'sun')) {
      cursor.setDate(cursor.getDate() + 1)
      continue
    }
    const workStart = getWorkStartForDate(dateKey)
    if (!workStart) {
      cursor.setDate(cursor.getDate() + 1)
      continue
    }
    const startMarkerTime = new Date(cursor)
    startMarkerTime.setHours(workStart.hour, workStart.minute, 0, 0)
    const startLeftPx = timeToCollapsedPx(startMarkerTime.getTime())
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
      const endLeftPx = timeToCollapsedPx(endMarkerTime.getTime())
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
  while (cursor <= end) {
    const dateKey = formatDateKey(cursor)
    const dayClass = getDayClass(dateKey)
    if (hideWeekends.value && (dayClass === 'sat' || dayClass === 'sun')) {
      cursor.setDate(cursor.getDate() + 1)
      continue
    }
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
        const leftPx = timeToCollapsedPx(clampedStart)
        const widthPx = timeToCollapsedPx(clampedEnd) - leftPx
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

const selectedDisplayRange = computed(() => {
  const days = Array.isArray(displayDays.value) ? displayDays.value : []
  if (!days.length) return null
  const start = new Date(`${days[0].date}T00:00:00`)
  start.setHours(businessDayBoundaryHour, 0, 0, 0)
  const end = new Date(`${days[days.length - 1].date}T00:00:00`)
  end.setDate(end.getDate() + 1)
  end.setHours(businessDayBoundaryHour, 0, 0, 0)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return null
  return { startMs: start.getTime(), endMs: end.getTime() }
})

const hasBarInSelectedDisplayRange = (bar) => {
  const range = selectedDisplayRange.value
  if (!range) return true
  const startMs = new Date(bar?.startTime).getTime()
  const endMs = new Date(bar?.endTime).getTime()
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) return false
  return startMs < range.endMs && endMs > range.startMs
}

const matchesKeyword = (values, keyword) => {
  if (!keyword) return true
  return values.some((value) => String(value || '').toLowerCase().includes(keyword))
}

const processMatchesKeyword = (proc) => matchesKeyword([
  proc?.process_name,
  proc?.process_code,
  getProcessCode(proc),
], normalizedProcessKeyword.value)

const itemMatchesKeyword = (item) => matchesKeyword([
  item?.product_code,
  item?.product_name,
  item?.parent_product_code,
], normalizedProductKeyword.value)

const renderedProcessGantt = computed(() =>
  processGanttData.value
    .filter((proc) => {
      if (!props.filterProcessId) return true
      return String(proc.process_id) === String(props.filterProcessId)
    })
    .filter((proc) => processMatchesKeyword(proc))
    .map((proc) => ({
      ...proc,
      items: proc.items
        .map((item) => ({
          ...item,
          displayBars: mergeConsecutive.value ? mergeBars(item.bars) : item.bars,
        }))
        .filter((item) => itemMatchesKeyword(item))
        .filter((item) =>
          !props.hideEmptyRows ||
          (Array.isArray(item.displayBars) && item.displayBars.some((bar) => hasBarInSelectedDisplayRange(bar)))
        ),
    }))
    .filter((proc) => proc.items.length > 0)
)

const renderedProcessCount = computed(() => renderedProcessGantt.value.length)
const renderedItemCount = computed(() =>
  renderedProcessGantt.value.reduce((total, proc) => total + (Array.isArray(proc.items) ? proc.items.length : 0), 0)
)

const applyDailySeqMarkers = (procEntry) => {
  const allBars = []
  ;(procEntry?.items || []).forEach((item) => {
    ;(item?.bars || []).forEach((bar) => {
      bar.isDaySeqStart = false
      bar.isDaySeqEnd = false
      allBars.push(bar)
    })
  })
  const DAY_CHANGE_HOUR = 8
  const days = Array.isArray(displayDays.value) ? displayDays.value : []
  days.forEach((day) => {
    const dayStart = new Date(`${day.date}T00:00:00`).getTime() + (DAY_CHANGE_HOUR * 60 * 60 * 1000)
    if (!Number.isFinite(dayStart)) return
    const dayEnd = dayStart + (24 * 60 * 60 * 1000)
    const candidates = allBars.filter((bar) => {
      const startMs = new Date(bar?.startTime).getTime()
      const endMs = new Date(bar?.endTime).getTime()
      if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) return false
      return !(startMs >= dayEnd || endMs <= dayStart)
    })
    if (!candidates.length) return
    const startBar = candidates.slice().sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime())[0]
    const endBar = candidates.slice().sort((a, b) => new Date(b.endTime).getTime() - new Date(a.endTime).getTime())[0]
    if (startBar) startBar.isDaySeqStart = true
    if (endBar) endBar.isDaySeqEnd = true
  })
}

const findBarEntry = (targetBar) => {
  for (const proc of processGanttData.value) {
    for (const item of proc.items || []) {
      const index = (item.bars || []).findIndex((bar) => bar === targetBar || bar.key === targetBar?.key)
      if (index >= 0) {
        return { proc, item, index, bar: item.bars[index] }
      }
    }
  }
  return null
}

const getBarIdentityKey = (bar) => {
  if (!bar) return ''
  return [
    bar.planId ?? bar.plan_id,
    bar.processId ?? bar.process_id,
    bar.outputProductId ?? bar.output_product_id ?? '',
  ].join('::')
}

const countTemporaryBars = () => {
  let count = 0
  processGanttData.value.forEach((proc) => {
    ;(proc.items || []).forEach((item) => {
      ;(item.bars || []).forEach((bar) => {
        if (bar?.isTemporary) count += 1
      })
    })
  })
  return count
}

const refreshStructureDirty = () => {
  setStructureDirty(countTemporaryBars() > 0 || pendingDeletes.value.length > 0)
}

const ensureStructureCategoryAvailable = () => {
  if (hasEditChanges.value) {
    alert('時間・数量の未保存変更があります。先に時間数量保存を実行してください。')
    return false
  }
  return true
}

const ensureEditCategoryAvailable = (bar = null) => {
  if (bar?.isTemporary) return true
  if (hasStructureChanges.value) {
    alert('追加・削除の未保存変更があります。先に追加削除保存を実行してください。')
    return false
  }
  return true
}

function getDayClass(dateStr) {
  const d = new Date(dateStr)
  const dow = d.getDay()
  if (dow === 0) return 'sun'
  if (dow === 6) return 'sat'
  // カレンダ上の休日（祝日・GW等）も日曜と同じスタイルにする
  const day = calendarDayMap.value[dateStr]
  if (isNonWorkingCalendarDay(day)) return 'sun'
  return ''
}

const fetchLines = async () => {
  const res = await api.lines.getLines({ page_size: 500 })
  lines.value = res.data.results || res.data || []
}

const shouldDisplayProductInProcess = (
  processId,
  productId,
  productCode,
  childMapSource = processCoproductChildMap.value
) => {
  const code = String(productCode || '').trim()
  const codeUpper = code.toUpperCase()
  if (codeUpper.startsWith('ST')) return true
  if (FLOOR_4001_COPRODUCT_CHILD_DISPLAY_EXCEPTION_CODES.has(codeUpper)) {
    const processCode = String(
      processCodeMap.value[Number(processId)] || processCodeMap.value[String(processId)] || ''
    ).trim()
    if (processCode === '4001' || Number(processId) === 4001) return true
  }
  const pid = Number(productId)
  if (!Number.isFinite(pid) || pid <= 0) return false
  const childSet = childMapSource?.[Number(processId)]
  if (childSet && childSet.has(pid)) return false
  return true
}

const appendProcessOutputCandidate = (targetMap, processId, productId, productCode, productName = '') => {
  const pid = Number(processId)
  const outId = Number(productId)
  const code = String(productCode || '').trim()
  if (!Number.isFinite(pid) || pid <= 0) return
  if (!Number.isFinite(outId) || outId <= 0) return
  if (!code) return
  if (!targetMap[pid]) targetMap[pid] = []
  if (targetMap[pid].some((item) => Number(item.product_id) === outId)) return
  targetMap[pid].push({
    product_id: outId,
    product_code: code,
    product_name: String(productName || '').trim(),
  })
}

const loadProcessOutputCandidates = async (lineId) => {
  if (!lineId) {
    processOutputCandidatesMap.value = {}
    processCoproductChildMap.value = {}
    return
  }
  try {
    const res = await api.routings.getRoutingStepsByLine(lineId)
    const rows = res.data?.results || res.data || []
    const nextChildMap = {}
    const lineCode = String(lines.value.find((l) => String(l.id) === String(lineId))?.line_code || '').trim().toUpperCase()
    const l2201Mode = lineCode === L2201_LINE_CODE
    const coproductBomsRes = await api.boms.getBOMs({
      is_coproduct: true,
      is_active: true,
      page_size: 5000,
    })
    const coproductBoms = coproductBomsRes.data?.results || coproductBomsRes.data || []
    const coproductBomIdSet = new Set(
      (Array.isArray(coproductBoms) ? coproductBoms : [])
        .map((bom) => Number(bom?.id))
        .filter((bomId) => Number.isFinite(bomId) && bomId > 0)
    )
    const bomItemsRes = await api.bomItems.getBOMItems({
      line: lineId,
      page_size: 5000,
    })
    const bomItems = bomItemsRes.data?.results || bomItemsRes.data || []
    ;(Array.isArray(bomItems) ? bomItems : []).forEach((item) => {
      const bomId = Number(item?.bom)
      const processId = Number(item?.process)
      const childId = Number(item?.child_product)
      if (!coproductBomIdSet.has(bomId)) return
      if (!Number.isFinite(processId) || processId <= 0) return
      if (!Number.isFinite(childId) || childId <= 0) return
      if (!nextChildMap[processId]) nextChildMap[processId] = new Set()
      nextChildMap[processId].add(childId)
    })
    processCoproductChildMap.value = nextChildMap

    const nextMap = {}
    rows.forEach((row) => {
      const processId = Number(row?.process)
      const productId = Number(row?.output_product)
      const productCode = String(row?.output_product_code || '').trim()
      if (!Number.isFinite(processId) || processId <= 0) return
      if (!Number.isFinite(productId) || productId <= 0) return
      if (!productCode) return
      if (!shouldDisplayProductInProcess(processId, productId, productCode, nextChildMap)) return
      appendProcessOutputCandidate(
        nextMap,
        processId,
        productId,
        productCode,
        String(row?.output_product_name || '').trim()
      )
    })

    // L2201専用: 下ガントの候補行にST連産品を表示する
    if (l2201Mode) {
      const products = await api.products.getAllProducts({
        line: lineId,
        is_line_final_product: true,
      })
      ;(Array.isArray(products) ? products : []).forEach((product) => {
        if (Number(product?.line) !== Number(lineId)) return
        const productCode = String(product?.product_code || '').trim()
        if (!productCode.toUpperCase().startsWith('ST')) return
        if (!shouldDisplayProductInProcess(product?.process, product?.id, productCode, nextChildMap)) return
        appendProcessOutputCandidate(
          nextMap,
          product?.process,
          product?.id,
          productCode,
          String(product?.product_name || '').trim()
        )
      })
    }
    processOutputCandidatesMap.value = nextMap
  } catch (e) {
    console.error('工程ガント候補品番取得エラー', e)
    processOutputCandidatesMap.value = {}
    processCoproductChildMap.value = {}
  }
}

const formatDateKey = (dateObj) => {
  return `${dateObj.getFullYear()}-${pad2(dateObj.getMonth() + 1)}-${pad2(dateObj.getDate())}`
}

const getBusinessDateKey = (dateObj) => {
  if (!(dateObj instanceof Date) || Number.isNaN(dateObj.getTime())) return ''
  const target = new Date(dateObj)
  if (target.getHours() < businessDayBoundaryHour) {
    target.setDate(target.getDate() - 1)
  }
  return formatDateKey(target)
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

const isNonWorkingCalendarDay = (day) => {
  if (!day) return false
  const isWorking = day.is_working_day
  if (isWorking === false) return true
  if (typeof isWorking === 'string' && isWorking.toLowerCase() === 'false') return true
  return false
}

const getWorkStartForDate = (dateKey) => {
  const day = calendarDayMap.value[dateKey]
  if (isNonWorkingCalendarDay(day)) return null
  if (day && day.work_pattern) {
    const pattern = workPatternMap.value[String(day.work_pattern)]
    const parsed = parseTimeParts(pattern?.start_time)
    if (parsed) return parsed
  }
  return workStartFallback
}

const getWorkEndForDate = (dateKey, startParts) => {
  const day = calendarDayMap.value[dateKey]
  if (isNonWorkingCalendarDay(day)) return null
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

const resolveDaisoCalendarId = async () => {
  if (daisoCalendarId.value !== undefined) return daisoCalendarId.value || null
  const pickDaiso = (rows) => {
    const list = rows || []
    const exact = list.find((row) => String(row.calendar_code || '').trim().toLowerCase() === 'daiso')
    if (exact) return exact
    return list.find((row) => {
      const code = String(row.calendar_code || '').trim().toLowerCase()
      const name = String(row.calendar_name || '').trim().toLowerCase()
      return code.includes('daiso') || name.includes('daiso') || name.includes('ダイソウ')
    })
  }
  try {
    const res = await api.calendars.getCalendars({ search: 'daiso', page_size: 200 })
    const rows = res.data?.results || res.data || []
    let daiso = pickDaiso(rows)
    if (!daiso) {
      const fallbackRes = await api.calendars.getCalendars({ page_size: 5000 })
      const fallbackRows = fallbackRes.data?.results || fallbackRes.data || []
      daiso = pickDaiso(fallbackRows)
    }
    daisoCalendarId.value = daiso?.id || null
  } catch (e) {
    console.error('DAISOカレンダ取得エラー', e)
    daisoCalendarId.value = null
  }
  return daisoCalendarId.value || null
}

const resolveLineCalendarId = async (lineId) => {
  let calendarId = null
  const line = lines.value.find((item) => String(item.id) === String(lineId))
  const lineCalendar = line?.calendar?.id ?? line?.calendar ?? null
  if (lineCalendar) {
    calendarId = lineCalendar
  } else {
    try {
      const lineRes = await api.lines.getLine(lineId)
      calendarId = lineRes.data?.calendar?.id ?? lineRes.data?.calendar ?? null
    } catch (e) {
      console.error('ライン勤務カレンダ取得エラー', e)
    }
  }
  if (calendarId) return calendarId
  return await resolveDaisoCalendarId()
}

const loadWorkPatternData = async (lineId, startDate, endDate) => {
  calendarDayMap.value = {}
  workPatternMap.value = {}
  if (!lineId) return

  const calendarId = await resolveLineCalendarId(lineId)
  if (!calendarId) return

  const filterByRange = (days) => {
    return (days || []).filter((day) => {
      if (!day.target_date) return false
      if (startDate && day.target_date < startDate) return false
      if (endDate && day.target_date > endDate) return false
      return true
    })
  }

  try {
    const daysRes = await api.calendars.getCalendarDays(calendarId, { page_size: 5000 })
    const days = daysRes.data?.results || daysRes.data || []
    const primaryFiltered = filterByRange(days)
    const mergedByDate = new Map(primaryFiltered.map((day) => [day.target_date, day]))

    const daisoId = await resolveDaisoCalendarId()
    if (daisoId && String(daisoId) !== String(calendarId)) {
      const daisoRes = await api.calendars.getCalendarDays(daisoId, { page_size: 5000 })
      const daisoDays = daisoRes.data?.results || daisoRes.data || []
      const daisoFiltered = filterByRange(daisoDays)
      daisoFiltered.forEach((day) => {
        if (!mergedByDate.has(day.target_date)) {
          mergedByDate.set(day.target_date, day)
        }
      })
    }

    const filtered = Array.from(mergedByDate.values())
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

const ensureProcessCodes = async (plans) => {
  const nextMap = { ...processCodeMap.value }
  const processIds = new Set()
  let changed = false

  ;(Array.isArray(plans) ? plans : []).forEach((plan) => {
    const processes = Array.isArray(plan?.processes_plan) ? plan.processes_plan : []
    processes.forEach((proc) => {
      const processId = Number(proc?.process_id)
      if (!Number.isFinite(processId) || processId <= 0) return
      processIds.add(processId)
      const code = String(proc?.process_code || '').trim()
      if (code && nextMap[processId] !== code) {
        nextMap[processId] = code
        changed = true
      }
    })
  })

  const missingIds = Array.from(processIds).filter((id) => !String(nextMap[id] || '').trim())
  if (missingIds.length) {
    const fetched = await Promise.all(
      missingIds.map(async (id) => {
        try {
          const res = await api.processes.getProcess(id)
          const code = String(res.data?.process_code || '').trim()
          return code ? { id, code } : null
        } catch (e) {
          console.error(`工程コード取得エラー process_id=${id}`, e)
          return null
        }
      })
    )
    fetched.forEach((item) => {
      if (!item) return
      if (nextMap[item.id] !== item.code) {
        nextMap[item.id] = item.code
        changed = true
      }
    })
  }

  if (changed) {
    processCodeMap.value = nextMap
  }
}

const loadData = async () => {
  if (!selectedLine.value) return
  pendingDeletes.value = []
  setEditDirty(false)
  setStructureDirty(false)
  processGanttData.value = []

  try {
    const startDate = displayDays.value[0].date
    const endDate = displayDays.value[displayDays.value.length - 1].date

    logDebug('loadData', { line: selectedLine.value, startDate, endDate })
    await loadWorkPatternData(selectedLine.value, startDate, endDate)
    await loadProcessOutputCandidates(selectedLine.value)
    const ganttRes = await api.lineGanttPlans.getLineGanttPlans({
      line: selectedLine.value,
      plan_date__gte: startDate,
      plan_date__lte: endDate,
    })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    logDebug('loadData response', { count: rawPlans.length, sample: rawPlans[0] })
    if (!rawPlans.length && props.embedded && props.autoGenerateIfEmpty) {
      logDebug('loadData no data, auto-generate')
      await generateSchedule(false)
      return
    }
    await ensureProcessCodes(rawPlans)
    processGanttData.value = buildProcessGantt(rawPlans)
  } catch (e) {
    console.error('工程ガント読込エラー', e)
    alert('データ読込に失敗しました')
  }
}

const generateSchedule = async (clearExisting = true) => {
  if (!selectedLine.value) return
  pendingDeletes.value = []
  setEditDirty(false)
  setStructureDirty(false)
  processGanttData.value = []

  try {
    const startDate = displayDays.value[0].date
    const endDate = displayDays.value[displayDays.value.length - 1].date
    logDebug('generateSchedule', { line: selectedLine.value, startDate, endDate, clearExisting })
    await loadWorkPatternData(selectedLine.value, startDate, endDate)
    await loadProcessOutputCandidates(selectedLine.value)
    const ganttRes = await api.lineGanttPlans.generate({
      line_id: selectedLine.value,
      start_date: startDate,
      end_date: endDate,
      clear_existing: clearExisting,
    })
    const rawPlans = ganttRes.data?.results || ganttRes.data || []
    logDebug('generateSchedule response', { count: rawPlans.length, sample: rawPlans[0] })
    await ensureProcessCodes(rawPlans)
    processGanttData.value = buildProcessGantt(rawPlans)
    return rawPlans
  } catch (e) {
    console.error('工程ガント生成エラー', e)
    alert('ガント計画の生成に失敗しました')
  }
}

const buildEditUpdates = () => {
  const updates = []
  processGanttData.value.forEach((proc) => {
    ;(proc.items || []).forEach((item) => {
      ;(item.bars || []).forEach((bar) => {
        if (!bar || bar.isTemporary) return
        const payload = {
          plan_id: bar.planId,
          process_id: bar.processId,
          start_time: toLocalISO(bar.startTime),
          end_time: toLocalISO(bar.endTime),
        }
        if (Number.isFinite(Number(bar.outputProductId)) && Number(bar.outputProductId) > 0) {
          payload.output_product_id = Number(bar.outputProductId)
        }
        if (bar.quantityEdited) {
          payload.quantity = Math.round(Number(bar.planQty || 0) * 1000) / 1000
        }
        updates.push(payload)
      })
    })
  })
  return updates
}

const collectTemporaryCreates = () => {
  const creates = []
  processGanttData.value.forEach((proc) => {
    ;(proc.items || []).forEach((item) => {
      ;(item.bars || []).forEach((bar) => {
        if (!bar?.isTemporary) return
        creates.push({
          line_id: Number(selectedLine.value),
          process_id: Number(bar.processId),
          output_product_id: Number(bar.outputProductId),
          start_time: toLocalISO(bar.startTime),
          end_time: toLocalISO(bar.endTime),
          quantity: Math.round(Number(bar.planQty || 0) * 1000) / 1000,
          process_number: Number(bar.processNumber || 0),
        })
      })
    })
  })
  return creates
}

const saveEditChanges = async () => {
  if (mergeConsecutive.value) {
    alert('連結表示では保存できません。分解表示に切り替えてください。')
    return
  }
  if (hasStructureChanges.value) {
    alert('追加・削除の未保存変更があります。先に追加削除保存を実行してください。')
    return
  }
  if (!timelineStart.value) {
    alert('保存するスケジュールがありません')
    return
  }
  const updates = buildEditUpdates()
  if (!updates.length) {
    alert('保存するスケジュールがありません')
    return
  }

  try {
    logDebug('saveEditChanges', { updates: updates.length })
    await api.lineGanttPlans.bulkUpdate(updates)
    clearQuantityEditedFlags()
    setEditDirty(false)
    alert('時間・数量変更を保存しました')
  } catch (e) {
    console.error('保存エラー', e)
    alert('保存に失敗しました')
  }
}

const saveStructureChanges = async () => {
  if (mergeConsecutive.value) {
    alert('連結表示では保存できません。分解表示に切り替えてください。')
    return
  }
  if (hasEditChanges.value) {
    alert('時間・数量の未保存変更があります。先に時間数量保存を実行してください。')
    return
  }
  const creates = collectTemporaryCreates()
  const deletes = pendingDeletes.value.map((item) => ({ ...item }))
  if (!creates.length && !deletes.length) {
    alert('保存対象の追加・削除がありません')
    return
  }
  try {
    manualAddLoading.value = true
    logDebug('saveStructureChanges', { creates: creates.length, deletes: deletes.length })
    await api.lineGanttPlans.bulkStructureSave({ creates, deletes })
    pendingDeletes.value = []
    setStructureDirty(false)
    await loadData()
    alert('追加・削除を保存しました')
  } catch (e) {
    console.error('追加削除保存エラー', e)
    alert('追加・削除の保存に失敗しました')
  } finally {
    manualAddLoading.value = false
  }
}

const clearQuantityEditedFlags = () => {
  processGanttData.value.forEach((proc) => {
    if (!proc.items) return
    proc.items.forEach((item) => {
      if (!item.bars) return
      item.bars.forEach((bar) => {
        bar.quantityEdited = false
        bar.scheduleEdited = false
      })
    })
  })
}

defineExpose({ saveSchedule: saveEditChanges, saveEditChanges, saveStructureChanges, setMergeConsecutive, hideWeekends })

let draggedBar = null
let draggedBarModel = null
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

function syncDraggedBarModelFromElement() {
  if (!draggedBar || !draggedBarModel || !timelineStart.value) return
  const currentLeft = parseFloat(draggedBar.style.left || '0')
  const roundMs = 1000 * 60 * 5
  const newStartMs = collapsedPxToTimeMs(currentLeft)
  const roundedStartMs = Math.round(newStartMs / roundMs) * roundMs
  draggedBarModel.startTime = new Date(roundedStartMs)
  draggedBarModel.endTime = new Date(roundedStartMs + Number(draggedBarModel.durationMs || 0))
  updateBarDisplay(draggedBarModel)
}

function onBarMouseDown(e, bar) {
  if (mergeConsecutive.value) {
    alert('連結表示中はバー編集できません。分解表示に切り替えてください。')
    return
  }
  if (bar?.isTemporary) {
    if (!ensureStructureCategoryAvailable()) return
  } else if (!ensureEditCategoryAvailable(bar)) {
    return
  }
  handleDragStart(e, bar)
}

function handleDragStart(e, bar) {
  if (e.button !== 0) return
  draggedBar = e.currentTarget
  draggedBarModel = bar || null
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
  const currentLeft = parseFloat(draggedBar.style.left || '0')
  const newStartMs = collapsedPxToTimeMs(currentLeft)
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
    syncDraggedBarModelFromElement()
    if (draggedBarModel?.isTemporary) {
      setStructureDirty(true)
      alert('位置を調整しました。追加削除保存で確定してください。')
    } else {
      if (draggedBarModel) draggedBarModel.scheduleEdited = true
      setEditDirty(true)
      alert('位置を調整しました。時間数量保存で確定してください。')
    }
  }

  draggedBar = null
  draggedBarModel = null
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
    days.push({ date: formatISODate(current), label: formatDayLabel(current) })
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
      dayClass: getDayClass(formatISODate(current)),
    })
    current.setHours(current.getHours() + slotHours)
  }
  return slots
}

function getProcessCode(proc) {
  const code = String(proc?.process_code || '').trim()
  if (code) return code
  const processId = Number(proc?.process_id)
  if (!Number.isFinite(processId) || processId <= 0) return ''
  const mappedCode = String(processCodeMap.value[processId] || processCodeMap.value[String(processId)] || '').trim()
  if (mappedCode) return mappedCode
  return ''
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
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.round(parsed * 1000) / 1000
}

function formatTimeRange(start, end) {
  return `${formatDateTime(start)} - ${formatDateTime(end)}`
}

function buildBarTooltip(bar, item, proc) {
  if (!bar) return ''
  const detailLines = []
  if (proc?.process_name) detailLines.push(`工程: ${proc.process_name}`)
  if (item?.product_code) detailLines.push(`品番: ${item.product_code}`)
  detailLines.push(`数量: ${formatQuantity(bar.planQty)}`)
  if (Array.isArray(bar.mergedPlanIds) && bar.mergedPlanIds.length > 1) {
    detailLines.push(`連結本数: ${bar.mergedPlanIds.length}`)
  }
  if (bar.startLabel && bar.endLabel) {
    detailLines.push(`時間: ${bar.startLabel} - ${bar.endLabel}`)
  }
  if (bar.durationLabel) detailLines.push(`所要分: ${bar.durationLabel}`)
  if (bar.isTemporary) detailLines.push('状態: 追加未保存')
  if (bar.quantityEdited) detailLines.push('数量変更: 未保存')
  if (bar.scheduleEdited) detailLines.push('時間変更: 未保存')
  return detailLines.join('\n')
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

function parseCompactDayInput(value, fallbackDate) {
  const raw = String(value ?? '').trim()
  if (!/^\d{3,4}$/.test(raw)) return null
  const monthPart = raw.length === 3 ? raw.slice(0, 1) : raw.slice(0, 2)
  const dayPart = raw.length === 3 ? raw.slice(1) : raw.slice(2)
  const month = Number(monthPart)
  const day = Number(dayPart)
  if (!Number.isInteger(month) || !Number.isInteger(day)) return null
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  const year = fallbackDate?.getFullYear?.() ?? new Date().getFullYear()
  const test = new Date(year, month - 1, day, 0, 0, 0, 0)
  if (
    Number.isNaN(test.getTime()) ||
    test.getFullYear() !== year ||
    test.getMonth() !== month - 1 ||
    test.getDate() !== day
  ) return null
  return { year, month, day }
}

function parseCompactTimeInput(value) {
  const raw = String(value ?? '').trim()
  if (!/^\d{3,4}$/.test(raw)) return null
  const hourPart = raw.length === 3 ? raw.slice(0, 1) : raw.slice(0, 2)
  const minutePart = raw.slice(-2)
  const hour = Number(hourPart)
  const minute = Number(minutePart)
  if (!Number.isInteger(hour) || !Number.isInteger(minute)) return null
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null
  return { hour, minute }
}

function toCompactDayInput(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return ''
  return `${date.getMonth() + 1}${pad2(date.getDate())}`
}

function toCompactTimeInput(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) return ''
  return `${date.getHours()}${pad2(date.getMinutes())}`
}

function roundToFiveMinutes(date) {
  const ms = date.getTime()
  const roundMs = 1000 * 60 * 5
  return new Date(Math.round(ms / roundMs) * roundMs)
}

function updateBarDisplay(bar) {
  if (!timelineStart.value) return
  bar.leftPx = timeToCollapsedPx(bar.startTime.getTime())
  bar.widthPx = Math.max(timeToCollapsedPx(bar.endTime.getTime()) - bar.leftPx, 20)
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

function shouldMergeBarByRule(currentBar, nextBar) {
  const gap = nextBar.startTime.getTime() - currentBar.endTime.getTime()
  if (gap >= -mergeGapToleranceMs && gap <= mergeGapToleranceMs) {
    return true
  }

  const currentBusinessDate = getBusinessDateKey(currentBar.startTime)
  const nextBusinessDate = getBusinessDateKey(nextBar.startTime)
  if (!currentBusinessDate || !nextBusinessDate || currentBusinessDate !== nextBusinessDate) {
    return false
  }

  return gap >= -sameBusinessDayMergeGapToleranceMs && gap <= sameBusinessDayMergeGapToleranceMs
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
    if (shouldMergeBarByRule(current, cloned)) {
      current.endTime = new Date(Math.max(current.endTime.getTime(), cloned.endTime.getTime()))
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

async function openBarEdit(bar) {
  if (!bar || !bar.startTime || !bar.durationMs) return
  if (mergeConsecutive.value) {
    alert('連結表示中は編集できません。分解表示に切り替えてください。')
    return
  }
  if (bar.isTemporary) {
    if (!ensureStructureCategoryAvailable()) return
  } else if (!ensureEditCategoryAvailable(bar)) {
    return
  }

  barEditDialog.value = {
    visible: true,
    bar,
    productCode: findBarEntry(bar)?.item?.product_code || '',
    qty: formatQuantity(bar.planQty),
    day: toCompactDayInput(bar.startTime),
    time: toCompactTimeInput(bar.startTime),
  }
}

function closeBarEditDialog() {
  barEditDialog.value.visible = false
  barEditDialog.value.bar = null
  barEditDialog.value.productCode = ''
  barEditDialog.value.cascadeBySeq = false
}

async function cascadeFollowingBarsBySequence(baseBar) {
  const baseSeq = Number(baseBar?.sequenceNo)
  const processId = Number(baseBar?.processId)
  if (!Number.isFinite(baseSeq) || !Number.isFinite(processId)) return

  const targets = []
  processGanttData.value.forEach((proc) => {
    if (Number(proc.process_id) !== processId) return
    proc.items.forEach((item) => {
      item.bars.forEach((bar) => {
        if (!bar || bar === baseBar || bar.isTemporary) return
        const seq = Number(bar.sequenceNo)
        if (!Number.isFinite(seq) || seq <= baseSeq) return
        targets.push(bar)
      })
    })
  })
  if (!targets.length) return

  targets.sort((a, b) => {
    const aSeq = Number(a.sequenceNo)
    const bSeq = Number(b.sequenceNo)
    if (aSeq !== bSeq) return aSeq - bSeq
    return a.startTime - b.startTime
  })

  let cursor = new Date(baseBar.endTime)
  for (const bar of targets) {
    const durationMs = Number(bar.durationMs || 0)
    bar.startTime = new Date(cursor)

    if (Number(bar.totalMinutesRequired) > 0 && selectedLine.value) {
      try {
        const res = await api.lineGanttPlans.calcEndTime({
          line_id: Number(selectedLine.value),
          start_time: toLocalISO(bar.startTime),
          working_minutes: Number(bar.totalMinutesRequired),
        })
        if (res.data?.end_time) {
          bar.endTime = new Date(res.data.end_time)
          bar.durationMs = bar.endTime.getTime() - bar.startTime.getTime()
        } else {
          bar.endTime = new Date(bar.startTime.getTime() + Math.max(durationMs, 0))
        }
      } catch {
        bar.endTime = new Date(bar.startTime.getTime() + Math.max(durationMs, 0))
      }
    } else {
      bar.endTime = new Date(bar.startTime.getTime() + Math.max(durationMs, 0))
    }

    updateBarDisplay(bar)
    bar.scheduleEdited = true
    cursor = new Date(bar.endTime)
  }
}

async function applyBarEditFromDialog() {
  const bar = barEditDialog.value.bar
  if (!bar) return
  const qtyInput = String(barEditDialog.value.qty ?? '').trim()
  const dayInput = String(barEditDialog.value.day ?? '').trim()
  const timeInput = String(barEditDialog.value.time ?? '').trim()
  const shouldCascade = !!barEditDialog.value.cascadeBySeq

  const parsedQty = parseQuantityInput(qtyInput)
  if (parsedQty === null) {
    alert('数量の形式が正しくありません。例: 0 / 18 / 18.5')
    return
  }
  const parsedDay = parseCompactDayInput(dayInput, bar.startTime)
  if (!parsedDay) {
    alert('日付の形式が正しくありません。例: 502（5月2日）')
    return
  }
  const parsedTime = parseCompactTimeInput(timeInput)
  if (!parsedTime) {
    alert('時刻の形式が正しくありません。例: 1120（11:20）')
    return
  }
  closeBarEditDialog()

  const newStart = new Date(
    parsedDay.year,
    parsedDay.month - 1,
    parsedDay.day,
    parsedTime.hour,
    parsedTime.minute,
    0,
    0
  )
  bar.planQty = parsedQty
  bar.startTime = newStart
  bar.endTime = new Date(newStart.getTime() + bar.durationMs)

  if (bar.cycleTimeMinutes > 0 && parsedQty > 0 && selectedLine.value) {
    try {
      const totalMinutes = parsedQty * bar.cycleTimeMinutes + (bar.setupTimeMinutes || 0)
      const effectiveMinutes = totalMinutes / bar.parallelCount
      const res = await api.lineGanttPlans.calcEndTime({
        line_id: Number(selectedLine.value),
        start_time: toLocalISO(bar.startTime),
        working_minutes: effectiveMinutes,
      })
      if (res.data?.end_time) {
        bar.endTime = new Date(res.data.end_time)
        bar.durationMs = bar.endTime.getTime() - bar.startTime.getTime()
        bar.totalMinutesRequired = effectiveMinutes
      }
    } catch (e) {
      console.error('終了時刻の再計算に失敗しました', e)
    }
  }

  updateBarDisplay(bar)
  if (shouldCascade) {
    await cascadeFollowingBarsBySequence(bar)
  }
  if (bar.isTemporary) {
    setStructureDirty(true)
    alert('数量・時間を変更しました。追加削除保存で確定してください。')
  } else {
    bar.quantityEdited = true
    bar.scheduleEdited = true
    setEditDirty(true)
    alert('数量・時間を変更しました。時間数量保存で確定してください。')
  }
}

function openStartTimeEdit(bar) {
  if (!bar || !bar.startTime || !bar.durationMs) return
  if (mergeConsecutive.value) {
    alert('連結表示中は開始時刻を編集できません。分解表示に切り替えてください。')
    return
  }
  if (bar.isTemporary) {
    if (!ensureStructureCategoryAvailable()) return
  } else if (!ensureEditCategoryAvailable(bar)) {
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
  if (bar.isTemporary) {
    setStructureDirty(true)
    alert('開始時間を変更しました。追加削除保存で確定してください。')
  } else {
    bar.scheduleEdited = true
    setEditDirty(true)
    alert('開始時間を変更しました。時間数量保存で確定してください。')
  }
}

async function openQuantityEdit(bar) {
  if (!bar) return
  if (mergeConsecutive.value) {
    alert('連結表示中は数量を編集できません。分解表示に切り替えてください。')
    return
  }
  if (bar.isTemporary) {
    if (!ensureStructureCategoryAvailable()) return
  } else if (!ensureEditCategoryAvailable(bar)) {
    return
  }
  const input = window.prompt('数量を入力してください（0以上）', formatQuantity(bar.planQty))
  if (input === null) return
  const parsed = parseQuantityInput(input)
  if (parsed === null) {
    alert('数量の形式が正しくありません。例: 0 / 18 / 18.5')
    return
  }
  bar.planQty = parsed

  if (bar.cycleTimeMinutes > 0 && parsed > 0 && selectedLine.value) {
    try {
      const totalMinutes = parsed * bar.cycleTimeMinutes + (bar.setupTimeMinutes || 0)
      const effectiveMinutes = totalMinutes / bar.parallelCount
      const res = await api.lineGanttPlans.calcEndTime({
        line_id: Number(selectedLine.value),
        start_time: toLocalISO(bar.startTime),
        working_minutes: effectiveMinutes,
      })
      if (res.data?.end_time) {
        bar.endTime = new Date(res.data.end_time)
        bar.durationMs = bar.endTime.getTime() - bar.startTime.getTime()
        bar.totalMinutesRequired = effectiveMinutes
        bar.scheduleEdited = true
      }
    } catch (e) {
      console.error('終了時刻の再計算に失敗しました', e)
    }
  }

  updateBarDisplay(bar)
  if (bar.isTemporary) {
    setStructureDirty(true)
    alert('数量を変更しました。追加削除保存で確定してください。')
  } else {
    bar.quantityEdited = true
    setEditDirty(true)
    alert('数量・時間を変更しました。時間数量保存で確定してください。')
  }
}

async function deleteBar(bar) {
  if (!bar) return
  if (mergeConsecutive.value) {
    alert('連結表示中は削除できません。分解表示に切り替えてください。')
    return
  }
  if (!ensureStructureCategoryAvailable()) return
  if (!confirm('このプロセスのバーを削除しますか？')) return
  const entry = findBarEntry(bar)
  if (!entry) {
    alert('削除対象のバーが見つかりません。')
    return
  }
  entry.item.bars.splice(entry.index, 1)
  if (!bar.isTemporary) {
    const deleteKey = getBarIdentityKey(bar)
    if (!pendingDeletes.value.some((item) => getBarIdentityKey(item) === deleteKey)) {
      pendingDeletes.value.push({
        plan_id: bar.planId,
        process_id: bar.processId,
        output_product_id: bar.outputProductId || null,
      })
    }
  }
  refreshStructureDirty()
  alert('削除予定に追加しました。追加削除保存で確定してください。')
}

async function openManualAdd(proc, item, anchor) {
  if (!selectedLine.value || !proc?.process_id || !item?.product_id) return
  if (mergeConsecutive.value) {
    alert('連結表示中は追加できません。分解表示に切り替えてください。')
    return
  }
  if (!ensureStructureCategoryAvailable()) return

  const defaultStart = anchor?.startAt ? new Date(anchor.startAt) : new Date()
  const defaultEnd = new Date(defaultStart.getTime() + 120 * 60 * 1000)

  const startInput = window.prompt(
    '追加バーの開始日時を入力してください (YYYY-MM-DD HH:mm)',
    formatDateTimeInput(defaultStart)
  )
  if (startInput === null) return
  const startDt = parseDateTimeInput(startInput)
  if (!startDt) {
    alert('開始日時の形式が正しくありません。例: 2026-03-02 17:30')
    return
  }

  const endInput = window.prompt(
    '追加バーの終了日時を入力してください (YYYY-MM-DD HH:mm)',
    formatDateTimeInput(defaultEnd)
  )
  if (endInput === null) return
  const endDt = parseDateTimeInput(endInput)
  if (!endDt) {
    alert('終了日時の形式が正しくありません。例: 2026-03-02 18:00')
    return
  }
  if (endDt.getTime() <= startDt.getTime()) {
    alert('終了日時は開始日時より後にしてください。')
    return
  }

  const qtyInput = window.prompt('数量を入力してください（0より大きい数値）', '1')
  if (qtyInput === null) return
  const qty = parseQuantityInput(qtyInput)
  if (qty === null) {
    alert('数量の形式が正しくありません。例: 18 または 18.5')
    return
  }

  const confirmMessage = [
    `工程: ${proc.process_name || ''}`,
    `品番: ${item.product_code || item.product_name || item.product_id}`,
    `時間: ${formatTimeRange(startDt, endDt)}`,
    `数量: ${formatQuantity(qty)}`,
    '',
    'この内容で追加しますか？',
  ].join('\n')
  if (!window.confirm(confirmMessage)) return

  try {
    manualAddLoading.value = true
    const tempKey = `TEMP_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    const durationMs = endDt.getTime() - startDt.getTime()
    const newBar = {
      key: tempKey,
      planId: tempKey,
      processId: Number(proc.process_id),
      processNumber: Number(proc.process_number || 0),
      outputProductId: Number(item.product_id),
      startTime: startDt,
      endTime: endDt,
      durationMs,
      planQty: qty,
      quantityEdited: false,
      scheduleEdited: false,
      totalMinutesRequired: Math.max(durationMs / 60000, 0),
      cycleTimeMinutes: 0,
      setupTimeMinutes: 0,
      parallelCount: 1,
      color: getBarColor(item.product_id),
      label: '',
      startLabel: '',
      endLabel: '',
      durationLabel: '',
      leftPx: 0,
      widthPx: 0,
      isTemporary: true,
    }
    item.bars.push(newBar)
    item.bars.sort((a, b) => a.startTime - b.startTime)
    updateBarDisplay(newBar)
    setStructureDirty(true)
    alert('追加予定に登録しました。追加削除保存で確定してください。')
  } finally {
    manualAddLoading.value = false
  }
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
          process_code: getProcessCode(proc),
          process_name: proc.process_name || '',
          process_number: proc.process_number || 0,
          items: [],
          itemsMap: new Map(),
        })
      }
      const procEntry = processMap.get(key)
      if (!procEntry.process_code) {
        procEntry.process_code = getProcessCode(proc)
      }
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

      const shouldMergeSameSlotBars = isL2201Line.value
      const timeSlotKey = `${startTime.getTime()}_${endTime.getTime()}`
      const barKey = proc.coproduct_group_key ||
        (shouldMergeSameSlotBars
          ? `${proc.process_id}_${outputProductId}_${timeSlotKey}`
          : `${plan.plan_id}_${proc.process_id}_${proc.output_product_id}`)
      const existingBar = (proc.coproduct_group_key || shouldMergeSameSlotBars) ? item.barsMap.get(barKey) : null
      if (existingBar) {
        existingBar.startTime = new Date(Math.min(existingBar.startTime.getTime(), startTime.getTime()))
        existingBar.endTime = new Date(Math.max(existingBar.endTime.getTime(), endTime.getTime()))
        existingBar.durationMs = existingBar.endTime.getTime() - existingBar.startTime.getTime()
        existingBar.planQty = proc.coproduct_group_key
          ? Math.max(existingBar.planQty, qtyValue)
          : Number(existingBar.planQty || 0) + qtyValue
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
          processNumber: proc.process_number || 0,
          outputProductId: outputProductId,
          startTime,
          endTime,
          durationMs: endTime.getTime() - startTime.getTime(),
          planQty: qtyValue,
          quantityEdited: false,
          scheduleEdited: false,
          totalMinutesRequired: Number(proc.total_minutes_required ?? 0),
          cycleTimeMinutes: Number(proc.cycle_time_minutes ?? 0),
          setupTimeMinutes: Number(proc.setup_time_minutes ?? 0),
          parallelCount: Number(proc.parallel_count ?? 1) || 1,
          sequenceNo: plan.sequence_no != null ? Number(plan.sequence_no) : null,
          color: getBarColor(colorKey),
          label: '',
          startLabel: '',
          endLabel: '',
          durationLabel: '',
          leftPx: 0,
          widthPx: 0,
          isTemporary: false,
        }
        item.bars.push(newBar)
        if (proc.coproduct_group_key || shouldMergeSameSlotBars) {
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
    procEntry.items = procEntry.items.filter((item) =>
      shouldDisplayProductInProcess(procEntry.process_id, item.product_id, item.product_code)
    )

    const candidates = processOutputCandidatesMap.value[procEntry.process_id] || []
    const existingProductIds = new Set(
      procEntry.items
        .map((item) => Number(item.product_id))
        .filter((pid) => Number.isFinite(pid) && pid > 0)
    )
    candidates.forEach((candidate) => {
      const pid = Number(candidate.product_id)
      if (!Number.isFinite(pid) || pid <= 0 || existingProductIds.has(pid)) return
      if (!shouldDisplayProductInProcess(procEntry.process_id, pid, candidate.product_code)) return
      procEntry.items.push({
        product_id: pid,
        product_code: candidate.product_code || String(pid),
        product_name: candidate.product_name || '',
        parent_product_code: candidate.product_code || String(pid),
        plan_qty: 0,
        sequence_no: null,
        bars: [],
        barsMap: new Map(),
      })
      existingProductIds.add(pid)
    })

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
    applyDailySeqMarkers(procEntry)
  })

  return Array.from(processMap.values()).sort((a, b) => {
    const diff = (b.process_number || 0) - (a.process_number || 0)
    if (diff !== 0) return diff
    return (b.process_id || 0) - (a.process_id || 0)
  })
}

function getBarColor(productId) {
  const colors = ['#E3A12B', '#E3D92B', '#85E32B', '#2BE3DA', '#2BB1E3', '#2BE3DF', '#2BE36F', '#51E32B', '#BFE32B']
  const hash = Math.abs(Number(productId) || 0) % colors.length
  return colors[hash]
}

watch(
  mergeConsecutive,
  (next) => {
    emit('mode-change', next)
  },
  { immediate: true }
)

watch([calendarDayMap, workPatternMap], () => {
  if (!timelineStart.value || !timelineEnd.value || !timelineSlots.value.length) return
  timelineSlots.value = buildTimelineSlots(timelineStart.value, timelineEnd.value)
})

watch(hideWeekends, (v) => {
  localStorage.setItem(HIDE_WEEKENDS_KEY, v ? '1' : '0')
  processGanttData.value.forEach((proc) => {
    ;(proc.items || []).forEach((item) => {
      ;(item.bars || []).forEach((bar) => updateBarDisplay(bar))
    })
  })
})

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
  flex-wrap: wrap;
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
  flex-wrap: wrap;
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
.view-filter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.view-filter-input {
  width: 132px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 12px;
  background: #fff;
}
.view-mode-count {
  font-size: 12px;
  font-weight: 700;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 3px 8px;
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
.seq-marker {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  font-weight: 700;
  color: #ffffff;
  background: #dc2626;
  border: 1px solid #b91c1c;
  border-radius: 8px;
  padding: 0 4px;
  line-height: 1.2;
  pointer-events: none;
  z-index: 4;
}
.seq-marker.start {
  left: -14px;
}
.seq-marker.end {
  right: -14px;
}
.gantt-chart {
  --process-col-width: 150px;
  --product-col-width: 120px;
  --fixed-cols-width: calc(var(--process-col-width) + var(--product-col-width));
  display: flex;
  flex-direction: column;
  position: relative;
}
.gantt-guides {
  position: absolute;
  top: 0;
  bottom: 0;
  left: var(--fixed-cols-width);
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
.timeline-process-label {
  width: var(--process-col-width);
  min-width: var(--process-col-width);
  padding: 4px 8px;
  font-size: 13px;
  font-weight: 700;
  background: #e8edf4;
  border-right: 1px solid #d1d5db;
  display: flex;
  align-items: center;
  justify-content: center;
  position: sticky;
  left: 0;
  z-index: 4;
}
.timeline-label {
  width: var(--product-col-width);
  min-width: var(--product-col-width);
  padding: 4px 8px;
  font-size: 13px;
  font-weight: 700;
  background: #f3f4f6;
  border-right: 1px solid #d1d5db;
  display: flex;
  align-items: center;
  justify-content: center;
  position: sticky;
  left: var(--process-col-width);
  z-index: 4;
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
.gantt-row-process {
  position: sticky;
  left: 0;
  z-index: 2;
  width: var(--process-col-width);
  min-width: var(--process-col-width);
  padding: 4px 8px;
  border-right: 1px solid #d1d5db;
  display: flex;
  align-items: center;
  background: #f1f5f9;
}
.gantt-row-label {
  position: sticky;
  left: var(--process-col-width);
  z-index: 2;
  width: var(--product-col-width);
  min-width: var(--product-col-width);
  padding: 4px 6px;
  border-right: 1px solid #d1d5db;
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: #fafafa;
}
.process-name-inline {
  width: 100%;
  font-size: 12px;
  font-weight: 700;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
.gantt-row-add-btn {
  position: absolute;
  top: 5px;
  width: 20px;
  height: 20px;
  border: 1px solid #0f766e;
  border-radius: 9999px;
  background: #ffffff;
  color: #0f766e;
  font-size: 14px;
  font-weight: 700;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 4;
  padding: 0;
}
.gantt-row-add-btn:hover {
  background: #ecfeff;
}
.gantt-row-add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
.gantt-bar-wrapper.is-temporary .gantt-bar {
  outline: 2px dashed #f59e0b;
  outline-offset: 1px;
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
.gantt-bar-delete-btn {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: none;
  background: #dc2626;
  color: #fff;
  font-size: 10px;
  line-height: 1;
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 0;
  z-index: 10;
}
.gantt-bar-wrapper:hover .gantt-bar-delete-btn {
  display: flex;
}
.gantt-bar-delete-btn:hover {
  background: #991b1b;
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
.bar-edit-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 12px;
  z-index: 2100;
}
.bar-edit-dialog {
  width: min(460px, calc(100vw - 24px));
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
}
.bar-edit-dialog h4 {
  margin: 0 0 10px;
  font-size: 16px;
}
.bar-edit-product {
  margin: -4px 0 8px;
  font-size: 13px;
  color: #1f2937;
  font-weight: 600;
}
.bar-edit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  align-items: end;
}
.bar-edit-grid label {
  font-size: 12px;
  color: #374151;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.bar-edit-grid input {
  width: 100%;
  box-sizing: border-box;
  height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
}
.bar-edit-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #6b7280;
}
.bar-edit-option-row {
  margin-top: 8px;
}
.bar-edit-check {
  font-size: 12px;
  color: #374151;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.bar-edit-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.bar-edit-steps {
  margin: 8px 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: #4b5563;
  line-height: 1.45;
}
</style>
