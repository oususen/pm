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
        <button class="btn primary" @click="loadData" :disabled="!selectedLine">
          読込
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
                  v-for="slot in timeSlots"
                  :key="slot.key"
                  class="time-slot-header"
                  :class="slot.dayClass"
                  :style="{ width: slot.widthPx + 'px' }"
                >
                  <div v-if="slot.showDay" class="time-slot-day">{{ slot.dayLabel }}</div>
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
const workPatterns = ref([])
const lineCalendarDays = ref([])
const processStepOrders = ref({})

const slotWidth = 60 // 1時間あたりのピクセル幅
const minuteWidth = computed(() => slotWidth / 60)
const BUFFER_FACTOR = 3 // バッファ台数（将来設定する場合ここをパラメータ化）

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

// 非稼働時間を除いた連続タイムライン
const workingSegments = computed(() => buildWorkingSegments())
const timelineWidthPx = computed(() =>
  workingSegments.value.reduce((sum, seg) => sum + seg.durationMin * minuteWidth.value, 0)
)
const timeSlots = computed(() => buildTimeSlots())

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

const fetchWorkPatterns = async () => {
  const res = await api.workPatterns.getWorkPatterns()
  workPatterns.value = res.data.results || res.data || []
}

const loadData = async () => {
  if (!selectedLine.value) return
  processGanttData.value = []
  lineCalendarDays.value = []

  try {
    const startDate = displayDays.value[0].date
    const endDate = displayDays.value[displayDays.value.length - 1].date

    if (!workPatterns.value.length) {
      await fetchWorkPatterns()
    }

    const line =
      lines.value.find((l) => l.id === selectedLine.value) ||
      (await api.lines.getLine(selectedLine.value)).data

    const [calRes, stepRes, ganttRes] = await Promise.all([
      line?.calendar
        ? api.calendars.getCalendarDays(line.calendar)
        : Promise.resolve({ data: [] }),
      api.routings.getRoutingStepsByLine(selectedLine.value),
      api.lineBacklogs.expandProcesses({
        line_id: selectedLine.value,
        start_date: startDate,
        end_date: endDate,
        read_only: false,  // 計算結果をDBに保存（工程別の計画数を自動計算）
      }),
    ])

    lineCalendarDays.value = calRes.data?.results || calRes.data || []
    const stepList = stepRes.data?.results || stepRes.data || []
    processStepOrders.value = buildProcessStepMap(stepList)

    const rawData = ganttRes.data?.items || ganttRes.data?.results || ganttRes.data || []
    processGanttData.value = buildProcessGantt(rawData)
  } catch (e) {
    console.error('工程ガント読込エラー', e)
    alert('データ読込に失敗しました')
  }
}

function buildProcessStepMap(steps = []) {
  const map = {}
  steps.forEach((s) => {
    if (!s.process) return
    const stepNo = s.step_no || 0
    if (!map[s.process] || stepNo > map[s.process]) {
      map[s.process] = stepNo
    }
  })
  return map
}

function timeToMinutes(timeStr) {
  if (!timeStr) return 0
  const [h, m] = timeStr.split(':').map(Number)
  return h * 60 + (m || 0)
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

function addMinutes(date, min) {
  return new Date(date.getTime() + min * 60 * 1000)
}

function buildWorkingSegments() {
  const calMap = new Map()
  lineCalendarDays.value.forEach((d) => calMap.set(d.target_date, d))
  const patternMap = new Map()
  workPatterns.value.forEach((p) => patternMap.set(p.id, p))


  const segments = []
  let offset = 0

  displayDays.value.forEach((day) => {
    const cal = calMap.get(day.date)
    if (cal && cal.is_working_day === false) {
      return
    }

    const pattern = cal && cal.work_pattern ? patternMap.get(cal.work_pattern) : null
    let startMin = pattern && pattern.start_time ? timeToMinutes(pattern.start_time) : 8 * 60
    let endMin
    if (pattern && pattern.end_time) {
      endMin = timeToMinutes(pattern.end_time)
      if (endMin <= startMin) {
        endMin += 24 * 60
      }
    } else {
      const workMinutes = cal && cal.work_minutes != null ? Number(cal.work_minutes) : 8 * 60
      endMin = startMin + workMinutes
    }

    const breaks = []
    if (pattern && Array.isArray(pattern.break_times)) {
      pattern.break_times.forEach((bt) => {
        const bs = timeToMinutes(bt.break_start)
        let be = timeToMinutes(bt.break_end)
        if (be <= bs) {
          be += 24 * 60
        }
        breaks.push({ start: bs, end: be })
      })
      breaks.sort((a, b) => a.start - b.start)
    }

    const base = new Date(`${day.date}T00:00:00`)
    let cursor = startMin

    const pushSeg = (sMin, eMin) => {
      if (eMin <= sMin) return
      const start = new Date(base.getTime() + sMin * 60 * 1000)
      const end = new Date(base.getTime() + eMin * 60 * 1000)
      const durationMin = eMin - sMin
      segments.push({
        start,
        end,
        date: day.date,
        dayLabel: day.label,
        dayClass: getDayClass(day.date),
        durationMin,
        offsetMin: offset,
      })
      offset += durationMin
    }

    breaks.forEach((br) => {
      if (br.start > cursor) {
        pushSeg(cursor, Math.min(br.start, endMin))
      }
      cursor = Math.max(cursor, br.end)
    })

    if (cursor < endMin) {
      pushSeg(cursor, endMin)
    }
  })


  return segments
}

function buildTimeSlots() {
  const slots = []
  workingSegments.value.forEach((seg) => {
    let current = new Date(seg.start)
    let first = true
    while (current < seg.end) {
      const nextHour = new Date(current)
      nextHour.setHours(nextHour.getHours() + 1, 0, 0, 0)
      const next = nextHour > seg.end ? seg.end : nextHour
      const widthMin = (next.getTime() - current.getTime()) / (60 * 1000)
      slots.push({
        key: `${seg.date}_${current.getHours()}_${current.getMinutes()}`,
        label: `${pad2(current.getHours())}:${pad2(current.getMinutes())}`,
        dayLabel: seg.dayLabel,
        dayClass: seg.dayClass,
        widthPx: widthMin * minuteWidth.value,
        showDay: first,
      })
      current = next
      first = false
    }
  })
  return slots
}

function alignToWorkingSegments(targetTime, segments) {
  if (!segments.length || !targetTime) return null

  // targetTime の日付を取得（YYYY-MM-DD形式）
  const targetDate = targetTime.toISOString().slice(0, 10)

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i]

    // セグメントが targetTime の日付と同じ、またはそれ以降の場合
    if (seg.date >= targetDate) {
      // targetTime がセグメント内にある場合、targetTime を使用
      if (targetTime >= seg.start && targetTime < seg.end) {
        return { index: i, cursor: new Date(targetTime) }
      }
      // targetTime がセグメント開始前の場合、セグメントの開始時刻を使用
      if (targetTime <= seg.start) {
        return { index: i, cursor: new Date(seg.start) }
      }
    }
  }
  return null
}

function advanceCursor(state, minutes, segments) {
  if (!state) return null
  let remaining = minutes
  let idx = state.index
  let cursor = new Date(state.cursor)

  while (remaining > 0 && idx < segments.length) {
    const seg = segments[idx]
    const available = (seg.end.getTime() - cursor.getTime()) / (60 * 1000)
    if (available > remaining) {
      cursor = addMinutes(cursor, remaining)
      remaining = 0
      return { index: idx, cursor }
    }
    remaining -= available
    idx += 1
    if (idx < segments.length) {
      cursor = new Date(segments[idx].start)
    }
  }

  return idx < segments.length ? { index: idx, cursor } : null
}

function findSegmentIndexByTime(segments, targetTime) {
  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i]
    if (targetTime >= seg.start && targetTime < seg.end) return i
  }
  return -1
}

function timeToOffsetMinutes(segments, time) {
  const idx = findSegmentIndexByTime(segments, time)
  if (idx < 0) return 0
  const seg = segments[idx]
  return seg.offsetMin + (time.getTime() - seg.start.getTime()) / (60 * 1000)
}

function rewindTime(segments, anchorTime, offsetMin) {
  if (!segments.length || !anchorTime) return anchorTime
  let remaining = offsetMin
  let idx = findSegmentIndexByTime(segments, anchorTime)
  let cursor = anchorTime
  if (idx < 0) {
    if (anchorTime < segments[0].start) return segments[0].start
    idx = segments.length - 1
    cursor = new Date(segments[idx].end)
  }
  let iteration = 0
  while (remaining > 0 && idx >= 0) {
    const seg = segments[idx]
    const available = (cursor.getTime() - seg.start.getTime()) / (60 * 1000)
    if (available >= remaining) {
      const result = new Date(cursor.getTime() - remaining * 60 * 1000)
      return result
    }
    remaining -= available
    idx -= 1
    if (idx >= 0) {
      cursor = new Date(segments[idx].end)
    }
    iteration++
  }
  // まだ残り時間がある場合、最後のセグメントの開始時刻からさらに巻き戻す
  if (remaining > 0 && segments.length > 0) {
    const result = new Date(segments[0].start.getTime() - remaining * 60 * 1000)
    return result
  }
  return segments[0].start
}

function pickDurationMinutes(rec) {
  // ルーティングで計算されたcomputed_time_minを最優先で使用し、
  // cycle_time_min（m_process_cycle_time）は参照しない。
  if (rec.computed_time_min != null) return Number(rec.computed_time_min)
  const qty = Number(rec.plan_qty || 0)
  const durationPer = rec.duration_min != null ? Number(rec.duration_min) : 0
  if (durationPer > 0 && qty > 0) {
    return qty * durationPer
  }
  return 0
}

function recordSorter(a, b) {
  if (a.plan_date !== b.plan_date) {
    return String(a.plan_date || '').localeCompare(String(b.plan_date || ''))
  }
  const aSeq = a.sequence_no != null ? a.sequence_no : Number.POSITIVE_INFINITY
  const bSeq = b.sequence_no != null ? b.sequence_no : Number.POSITIVE_INFINITY
  if (aSeq !== bSeq) return aSeq - bSeq
  return (a.product_code || '').localeCompare(b.product_code || '')
}

function itemSorter(a, b) {
  const aSeq = a.sequence_no != null ? a.sequence_no : Number.POSITIVE_INFINITY
  const bSeq = b.sequence_no != null ? b.sequence_no : Number.POSITIVE_INFINITY
  if (aSeq !== bSeq) return aSeq - bSeq
  return (a.product_code || '').localeCompare(b.product_code || '')
}

function formatTimeRange(start, durationMin) {
  const end = addMinutes(start, durationMin)
  return `${formatTime(start)} - ${formatTime(end)}`
}

function computeEndTime(start, durationMin, segments) {
  if (!start || durationMin <= 0) return start
  let idx = findSegmentIndexByTime(segments, start)
  let cursor = new Date(start)
  if (idx < 0) {
    if (segments.length && start < segments[0].start) {
      idx = 0
      cursor = new Date(segments[0].start)
    } else {
      return addMinutes(start, durationMin)
    }
  }
  const endState = advanceCursor({ index: idx, cursor }, durationMin, segments)
  return endState ? endState.cursor : addMinutes(start, durationMin)
}

function formatTimeRangeWithSegments(start, durationMin, segments) {
  const end = computeEndTime(start, durationMin, segments)
  return `${formatTime(start)} - ${formatTime(end)}`
}

function buildProcessGantt(rawData) {
  const segments = workingSegments.value
  if (!segments.length) return []

  const processMap = new Map()
  const productProcessMeta = new Map() // key: `${productId}_${processId}` -> { cycleMin, stepNo }
  rawData.forEach((d) => {
    if (!d.process) return
    if (!processMap.has(d.process)) {
      processMap.set(d.process, {
        process_id: d.process,
        process_name: d.process_name || '',
        line_name: d.line_name || '',
        step_no: processStepOrders.value[d.process] || 0,
        items: [],
      })
    }
  })

  rawData.forEach((d) => {
    if (!d.process || !d.product) return
    const proc = processMap.get(d.process)
    let item = proc.items.find((it) => it.product_id === d.product)
    if (!item) {
      item = {
        product_id: d.product,
        product_code: d.product_code || '',
        product_name: d.product_name || '',
        plan_qty: 0,
        sequence_no: d.sequence_no != null ? d.sequence_no : null,
        routing_product_id: d.routing_product_id || d.product,  // ルーティングの親製品ID
        records: [],
        bars: [],
      }
      proc.items.push(item)
    }
    item.plan_qty += Number(d.plan_qty || 0)
    const seq = d.sequence_no != null ? Number(d.sequence_no) : null
    if (seq != null && (item.sequence_no == null || seq < item.sequence_no)) {
      item.sequence_no = seq
    }
    item.records.push(d)

    const cycle = Number(d.cycle_time_min || 0)
    const metaKey = `${d.product}_${d.process}`
    if (!productProcessMeta.has(metaKey)) {
      productProcessMeta.set(metaKey, {
        cycleMin: cycle > 0 ? cycle : null,
        stepNo: d.step_no || processStepOrders.value[d.process] || 0,
      })
    }
  })

  processMap.forEach((proc) => {
    proc.items.sort(itemSorter)
    const flatRecords = []
    proc.items.forEach((item) => {
      item.bars = []
      item.records.forEach((rec) => {
        flatRecords.push({ ...rec, productRef: item })
      })
    })
    flatRecords.sort(recordSorter)

    let cursorState = alignToWorkingSegments(segments[0]?.start, segments)
    flatRecords.forEach((rec) => {
      if (!cursorState) return
      const durationMin = pickDurationMinutes(rec)
      if (durationMin <= 0) return

      if (rec.plan_date) {
        // plan_date の日付で最初のセグメントを探す（タイムゾーン問題を避けるため、seg.dateと直接比較）
        const firstSegOfDay = segments.find(s => s.date === rec.plan_date)
        if (firstSegOfDay) {
          const desired = { index: segments.indexOf(firstSegOfDay), cursor: new Date(firstSegOfDay.start) }
          if (desired.cursor > cursorState.cursor) {
            cursorState = desired
          }
        }
      }

      const seg = segments[cursorState.index]
      const startOffsetMin =
        seg.offsetMin + (cursorState.cursor.getTime() - seg.start.getTime()) / (60 * 1000)

      const startTime = new Date(cursorState.cursor)

      const bar = {
        key: `${rec.product}_${rec.plan_date || 'na'}_${rec.process}`,
        leftPx: startOffsetMin * minuteWidth.value,
        widthPx: durationMin * minuteWidth.value,
        color: getBarColor(rec.product),
        label: formatTimeRangeWithSegments(cursorState.cursor, durationMin, segments),
        planQty: Number(rec.plan_qty || 0),
        startTime,
        durationMin,
      }

      rec.productRef.bars.push(bar)
      cursorState = advanceCursor(cursorState, durationMin, segments)
    })
  })

  // 後工程の開始からバッファ分（cycle×BUFFER_FACTOR）前倒しで前工程を配置（同一製品内）
  const processList = Array.from(processMap.values()).sort((a, b) => {
    const stepDiff = (b.step_no || 0) - (a.step_no || 0)
    if (stepDiff !== 0) return stepDiff
    return (b.process_id || 0) - (a.process_id || 0)
  })

  const productChains = new Map() // routing_product_id -> [{procRef, item, meta}]
  processList.forEach((proc) => {
    proc.items.forEach((item) => {
      const key = item.routing_product_id || item.product_id  // ルーティングの親製品IDでグループ化
      if (!productChains.has(key)) productChains.set(key, [])
      productChains.get(key).push({
        proc,
        item,
        meta: productProcessMeta.get(`${item.product_id}_${proc.process_id}`) || { stepNo: proc.step_no || 0, cycleMin: null },
      })
    })
  })

  const calcCycleMin = (meta, bars) => {
    if (meta && meta.cycleMin && meta.cycleMin > 0) return meta.cycleMin
    if (bars && bars.length && bars[0].planQty) {
      return Math.max(1, bars[0].durationMin / bars[0].planQty)
    }
    return 0
  }

  productChains.forEach((chain, productId) => {
    chain.sort((a, b) => (b.meta.stepNo || 0) - (a.meta.stepNo || 0)) // 後→前
    for (let i = 0; i < chain.length - 1; i++) {
      const later = chain[i]
      const earlier = chain[i + 1]
      if (!later.item.bars.length || !earlier.item.bars.length) continue

      const laterStart = later.item.bars[0].startTime
      const cycleMin = calcCycleMin(earlier.meta, earlier.item.bars)
      if (!cycleMin || !laterStart) continue

      const offsetMin = cycleMin * BUFFER_FACTOR
      const desiredStart = rewindTime(segments, laterStart, offsetMin)

      earlier.item.bars.forEach((bar) => {
        const newStart = desiredStart < bar.startTime ? desiredStart : bar.startTime
        const offsetMinVal = timeToOffsetMinutes(segments, newStart)
        bar.leftPx = offsetMinVal * minuteWidth.value
        bar.startTime = newStart
        bar.label = formatTimeRangeWithSegments(newStart, bar.durationMin, segments)
      })
    }
  })

  return Array.from(processMap.values()).sort((a, b) => {
    const stepDiff = (b.step_no || 0) - (a.step_no || 0)
    if (stepDiff !== 0) return stepDiff
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
    await Promise.all([fetchLines(), fetchWorkPatterns()])
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
