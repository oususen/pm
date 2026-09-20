<template>
  <main class="worker-shift-chart">
    <header class="page-header">
      <h1>{{ t('workerShiftChart.title') }}</h1>
      <p class="page-desc">{{ t('workerShiftChart.description') }}</p>
      <div class="header-controls">
        <button class="today-button" type="button" @click="moveDate(-1)">{{ t('workerShiftChart.previousDay') }}</button>
        <label>{{ t('workerShiftChart.date') }} <input v-model="selectedDate" type="date" /></label>
        <button class="today-button" type="button" @click="moveDate(1)">{{ t('workerShiftChart.nextDay') }}</button>
        <label>{{ t('workerShiftChart.line') }}
          <select v-model.number="currentLineId">
            <option v-for="line in availableLines" :key="line.id" :value="line.id">{{ line.name }}</option>
          </select>
        </label>
      </div>
    </header>

    <p v-if="loading" class="notice">{{ t('workerShiftChart.loading') }}</p>
    <p v-else-if="!availableLines.length" class="notice">
      {{ t('workerShiftChart.noLines') }}
    </p>

    <template v-else>
      <section class="my-shift" :aria-label="t('workerShiftChart.myShift')">
        <span class="section-label">{{ t('workerShiftChart.myShift') }}</span>
        <template v-if="myAssignments.length">
          <strong>{{ myWorker.name }}</strong>
          <span v-for="assignment in myAssignments" :key="assignment.id" class="my-job">
            {{ assignment.start_time.slice(0, 5) }}〜{{ endLabel(assignment) }}　{{ assignment.process_name }}
          </span>
        </template>
        <span v-else>{{ t('workerShiftChart.noAssignments') }}</span>
      </section>

      <section class="chart-card">
        <div class="chart-header">
          <div>
            <h2>{{ formattedDate }}　{{ currentLine?.name }}</h2>
            <p>{{ t('workerShiftChart.chartHint', { start: `${startHour}:00`, end: `${endHour}:00` }) }}</p>
          </div>
          <div class="legend">
            <span v-for="process in currentLine?.line_processes || []" :key="process.id">
              <i :style="{ background: process.color }"></i>{{ process.process_name }}
            </span>
          </div>
        </div>

        <div class="chart-scroll">
          <div class="chart" :style="{ '--hours': displayHours }">
            <div class="time-row"><div class="worker-title">{{ t('workerShiftChart.worker') }}</div><div class="time-scale"><span v-for="hour in timeLabels" :key="hour" :style="{ left: `${(hour - startHour) / displayHours * 100}%` }" :class="{ 'half-label': hour % 1 !== 0 }">{{ Math.floor(hour) }}:{{ hour % 1 ? '30' : '00' }}</span></div></div>
            <div v-for="worker in currentLine?.workers || []" :key="worker.id" class="worker-row" :class="{ mine: Number(worker.user) === currentUserId }">
              <div class="worker-name">
                <strong>{{ worker.name }}</strong>
                <small>{{ t('workerShiftChart.shiftStart', { shift: shiftTypeLabel(worker.shift_type), time: actualStart(worker) }) }}</small>
                <small class="worker-total">{{ t('workerShiftChart.totalWork', { hours: totalWork(worker) }) }}</small>
              </div>
              <div class="track">
                <span v-for="assignment in assignmentsFor(worker.id)" :key="assignment.id" class="assignment"
                  :style="assignmentStyle(assignment)" :title="t('workerShiftChart.assignmentTitle', { process: assignment.process_name, start: assignment.start_time.slice(0, 5), end: endLabel(assignment) })">
                  <b>{{ assignment.process_name }} <em>{{ t('workerShiftChart.units', { units: assignment.units || 0 }) }}</em></b>
                  <small>{{ t('workerShiftChart.assignmentHours', { start: assignment.start_time.slice(0, 5), end: endLabel(assignment), hours: assignment.work_hours }) }}</small>
                </span>
                <span v-for="(breakTime, index) in breaksForWorker(worker.id)" :key="`break-${index}`" class="break-bar" :class="{ meal: breakTime.label === 'meal' }" :style="breakStyle(breakTime)" :title="t('workerShiftChart.breakTitle', { label: breakLabel(breakTime.label), start: clockLabel(breakTime.start), end: clockLabel(breakTime.end) })">
                  <b v-if="breakTime.label === 'meal'">{{ breakLabel(breakTime.label) }}</b>
                </span>
                <div v-if="breaksForWorker(worker.id).length" class="break-summary"><strong>{{ t('workerShiftChart.automaticBreak') }}</strong><span v-for="(breakTime, index) in breaksForWorker(worker.id)" :key="`summary-${index}`">{{ t('workerShiftChart.breakTitle', { label: breakLabel(breakTime.label), start: clockLabel(breakTime.start), end: clockLabel(breakTime.end) }) }}</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="process-stats">
        <article v-for="process in processStats" :key="process.id" class="stat-card">
          <header>
            <span><i :style="{ background: process.color }"></i>{{ process.name }}</span>
            <b :class="process.achieved ? 'good' : 'bad'">{{ process.statusText }}</b>
          </header>
          <p>目標 {{ process.reqLabel }}／配置済 {{ process.placedLabel }}</p>
        </article>
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { t } from '@/i18n'

const startHour = 8
const endHour = 22
const displayHours = endHour - startHour
function formatLocalDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}
const today = formatLocalDate(new Date())
const selectedDate = ref(today)
const lines = ref([])
const currentLineId = ref(null)
const assignments = ref([])
const processLoads = ref({})
const loading = ref(true)
let assignmentRequestId = 0

const currentUserId = computed(() => Number(authState.user?.id || 0))
const availableLines = computed(() => lines.value.filter(line =>
  line.workers?.some(worker => Number(worker.user) === currentUserId.value)
))
const currentLine = computed(() => availableLines.value.find(line => line.id === currentLineId.value) || null)
const myWorker = computed(() => currentLine.value?.workers?.find(worker => Number(worker.user) === currentUserId.value) || null)
const myAssignments = computed(() => myWorker.value ? assignmentsFor(myWorker.value.id) : [])
const formattedDate = computed(() => selectedDate.value.replaceAll('-', '/'))
const timeLabels = computed(() => Array.from({ length: displayHours * 2 + 1 }, (_, index) => startHour + index * 0.5))

function minutes(value) {
  const [hour, minute] = String(value || '00:00').split(':').map(Number)
  return hour * 60 + minute
}

function clockLabel(value) {
  const minutesInDay = value % (24 * 60)
  return `${String(Math.floor(minutesInDay / 60)).padStart(2, '0')}:${String(minutesInDay % 60).padStart(2, '0')}`
}

function workerDay(workerId) {
  const jobs = assignmentsFor(workerId)
  if (!jobs.length) return null
  const start = Math.min(...jobs.map(job => minutes(job.start_time)))
  const end = Math.max(...jobs.map(job => endMinutes(job)))
  return { start, end }
}

function breaksForSpan(start, end) {
  const breaks = []
  if (start >= 15 * 60 || start < 5 * 60) {
    for (const [offset, length, label] of [[120, 10, 'break'], [250, 45, 'meal'], [415, 10, 'break'], [545, 10, 'break']]) breaks.push({ start: start + offset, end: start + offset + length, label })
  } else {
    for (const [offset, length, label] of [[120, 10, 'break'], [240, 45, 'meal'], [420, 10, 'break']]) {
      if (start + offset < start + 545) breaks.push({ start: start + offset, end: start + offset + length, label })
    }
    if (end > start + 545) {
      breaks.push({ start: start + 545, end: start + 555, label: 'beforeOvertime' })
      for (let breakStart = start + 675; breakStart < end; breakStart += 130) breaks.push({ start: breakStart, end: breakStart + 10, label: 'overtime' })
    }
  }
  return breaks.filter(item => item.start < end)
}

function breakLabel(label) {
  return t(`workerShiftChart.break.${label}`)
}

function shiftTypeLabel(shiftType) {
  const key = { 朝: 'morning', 昼: 'day', 夜: 'night' }[shiftType]
  return key ? t(`workerShiftChart.shift.${key}`) : shiftType
}

function endMinutes(assignment) {
  const jobs = assignmentsFor(assignment.worker)
  const shiftStart = jobs.length ? Math.min(...jobs.map(job => minutes(job.start_time))) : minutes(assignment.start_time)
  let end = minutes(assignment.start_time)
  let remaining = Math.round(Number(assignment.work_hours || 0) * 60)
  while (remaining > 0) {
    const nextBreak = breaksForSpan(shiftStart, end + remaining + 600).find(item => item.start >= end && item.start < end + remaining)
    if (!nextBreak) return end + remaining
    remaining -= nextBreak.start - end
    end = nextBreak.end
  }
  return end
}

function endLabel(assignment) {
  return clockLabel(endMinutes(assignment))
}

function assignmentsFor(workerId) {
  return assignments.value
    .filter(assignment =>
      assignment.date === selectedDate.value &&
      Number(assignment.worker) === Number(workerId)
    )
    .sort((a, b) => minutes(a.start_time) - minutes(b.start_time))
}

function assignmentStyle(assignment) {
  const process = currentLine.value?.line_processes?.find(item => Number(item.id) === Number(assignment.line_process))
  const start = minutes(assignment.start_time)
  const end = endMinutes(assignment)
  const chartStart = startHour * 60
  const chartEnd = endHour * 60
  const visibleStart = Math.max(start, chartStart)
  const visibleEnd = Math.min(end, chartEnd)
  const left = (visibleStart - chartStart) / (chartEnd - chartStart) * 100
  const width = Math.max(0, (visibleEnd - visibleStart) / (chartEnd - chartStart) * 100)
  return { left: `${left}%`, width: `${width}%`, background: process?.color || '#64748b' }
}

function breaksForWorker(workerId) {
  const day = workerDay(workerId)
  return day ? breaksForSpan(day.start, day.end).filter(item => item.end > startHour * 60 && item.start < endHour * 60) : []
}

function breakStyle(breakTime) {
  const visibleStart = Math.max(breakTime.start, startHour * 60)
  const visibleEnd = Math.min(breakTime.end, endHour * 60)
  return { left: `${(visibleStart - startHour * 60) / (displayHours * 60) * 100}%`, width: `${(visibleEnd - visibleStart) / (displayHours * 60) * 100}%` }
}

function actualStart(worker) {
  const day = workerDay(worker.id)
  return day ? clockLabel(day.start) : (worker.work_start || '').slice(0, 5)
}

function totalWork(worker) {
  return assignmentsFor(worker.id).reduce((sum, assignment) => sum + Number(assignment.work_hours || 0), 0)
}

function fmtHours(n) {
  return (Math.abs(n - Math.round(n)) < 0.01 ? Math.round(n) : n.toFixed(1)) + 'h'
}

function netDuration(assignment) {
  const day = workerDay(assignment.worker)
  let start = minutes(assignment.start_time)
  if (day) while (start < day.start) start += 1440
  let end = endMinutes(assignment)
  let mins = end - start
  breaksForSpan(day ? day.start : start, end).forEach(b => {
    mins -= Math.max(0, Math.min(end, b.end) - Math.max(start, b.start))
  })
  return Math.max(0, mins) / 60
}

const processStats = computed(() => {
  const line = currentLine.value
  if (!line) return []
  const active = assignments.value.filter(a => a.date === selectedDate.value)
  return (line.line_processes || []).map(p => {
    const placed = active.filter(a => {
      if (a.line_process) return a.line_process === p.id
      return a.process && a.process === p.process
    }).reduce((s, a) => s + netDuration(a), 0)
    const loadData = p.process ? processLoads.value[String(p.process)] : null
    const req = loadData ? +loadData.load_hours : 0
    const d = placed - req
    const achieved = req <= 0 ? true : d >= -0.01
    const rate = req > 0 ? Math.round(placed / req * 100) : (placed > 0 ? 100 : 0)
    return {
      id: p.id,
      name: p.process_name,
      color: p.color,
      achieved,
      rate,
      statusText: req <= 0 ? '―' : achieved ? '完了' : 'あと ' + fmtHours(-d),
      reqLabel: req > 0 ? fmtHours(req) : '―',
      placedLabel: fmtHours(placed),
    }
  })
})

function moveDate(days) {
  const date = new Date(`${selectedDate.value}T00:00:00`)
  date.setDate(date.getDate() + days)
  selectedDate.value = formatLocalDate(date)
}

async function loadProcessLoads() {
  if (!currentLineId.value || !selectedDate.value) return
  try {
    const { data } = await api.shifts.getProcessLoads(currentLineId.value, selectedDate.value)
    processLoads.value = data.loads || {}
  } catch {
    processLoads.value = {}
  }
}

async function loadAssignments() {
  const requestId = ++assignmentRequestId
  assignments.value = []
  if (!currentLineId.value) {
    return
  }
  try {
    const { data } = await api.shifts.getAssignments({ shift_line: currentLineId.value, date: selectedDate.value })
    if (requestId === assignmentRequestId) {
      assignments.value = data || []
    }
  } catch (error) {
    if (requestId === assignmentRequestId) {
      assignments.value = []
    }
  }
}

onMounted(async () => {
  try {
    const { data } = await api.shifts.getLines()
    lines.value = data || []
    currentLineId.value = availableLines.value[0]?.id || null
    await Promise.all([loadAssignments(), loadProcessLoads()])
  } finally {
    loading.value = false
  }
})

watch([currentLineId, selectedDate], () => { loadAssignments(); loadProcessLoads() })
</script>

<style scoped>
.worker-shift-chart{max-width:1540px;margin:0 auto;padding:10px 20px 40px;color:#17243a}.page-header{display:flex;gap:8px;align-items:center;margin-bottom:6px}.page-header h1{font-size:18px;margin:0;white-space:nowrap}.page-desc{display:none}.page-header p,.chart-header p{margin:0;color:#667085;font-size:12px}.today-button{border:1px solid #17365d;background:#fff;color:#17365d;border-radius:5px;padding:5px 12px;font-size:12px;font-weight:bold;cursor:pointer}.header-controls{display:flex;gap:8px;align-items:center;margin-left:auto}.header-controls label{display:flex;align-items:center;gap:5px;font-size:11px;font-weight:bold;color:#667085}.header-controls input,.header-controls select{height:auto;padding:5px 7px;border:1px solid #cbd5e1;border-radius:4px;background:#fff;font-size:13px}.notice,.my-shift{margin:8px 0;padding:10px 14px;border-radius:8px;background:#fff;border:1px solid #dfe5ec}.my-shift{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px}.section-label{font-weight:bold;color:#17365d}.my-job{padding:4px 8px;border-radius:4px;background:#e9f0fb}.chart-card{background:#fff;border:1px solid #dfe5ec;border-radius:8px;overflow:hidden}.chart-header{display:flex;justify-content:space-between;gap:15px;padding:15px 18px;border-bottom:1px solid #dfe5ec}.chart-header h2{font-size:18px;margin:0 0 3px}.legend{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:10px;font-size:12px;font-weight:bold}.legend span{white-space:nowrap}.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px}.chart-scroll{overflow-x:auto}.chart{min-width:900px}.time-row,.worker-row{display:grid;grid-template-columns:140px 1fr}.time-row{font-size:10px;font-weight:bold;color:#627083}.worker-title,.time-scale{height:49px;background:#f7f9fb}.worker-title{padding:16px;border-right:1px solid #dfe5ec;font-size:12px;color:#17243a}.time-scale,.track{position:relative;background-image:linear-gradient(to right,#edf0f4 1px,transparent 1px);background-size:calc(100% / var(--hours) / 2) 100%}.time-scale span{position:absolute;top:16px;transform:translateX(-50%)}.time-scale span:first-child{transform:none}.time-scale span:last-child{transform:translateX(-100%)}.time-scale .half-label{font-size:8px;opacity:.5}.worker-row{height:94px}.worker-name{height:94px;padding:12px 16px;border-top:1px solid #dfe5ec;border-right:1px solid #dfe5ec;background:#edf5ff;border-left:5px solid #3b82f6}.worker-name strong,.worker-name small{display:block}.worker-name small{margin-top:3px;font-size:11px;color:#2563a9;font-weight:bold}.worker-name .worker-total{color:#14734d;font-weight:bold}.worker-row:not(.mine) .worker-name{background:#f8fafc;border-left-color:transparent}.track{height:94px;border-top:1px solid #dfe5ec}.assignment{position:absolute;top:7px;height:48px;min-width:4px;border:0;border-radius:6px;color:#fff;text-align:left;padding:6px 9px;overflow:hidden;box-shadow:0 2px 4px #1d29394d}.assignment b,.assignment small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.assignment b{font-size:12px}.assignment small{font-size:9px;margin-top:2px}.assignment em{font-style:normal;background:#ffffff35;padding:1px 4px;border-radius:4px}.break-bar{position:absolute;top:5px;height:52px;z-index:2;pointer-events:none;background:#ffd52b99;border:2px solid #8d680099;border-radius:4px;min-width:5px}.break-bar.meal{background:repeating-linear-gradient(135deg,#ffe67a99,#ffe67a99 8px,#ffc92899 8px,#ffc92899 16px);padding:5px 3px;color:#332700;text-align:center}.break-bar.meal b{font-size:9px;white-space:nowrap}.break-summary{position:absolute;left:0;right:0;bottom:5px;height:27px;display:flex;align-items:center;gap:12px;padding:4px 8px;background:#fff9d8;border-top:1px solid #e2c75d;color:#624b00;font-size:10px;font-weight:bold;white-space:nowrap;overflow:hidden}.break-summary strong{background:#ffd52b;color:#493700;border-radius:4px;padding:2px 6px}.process-stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin-top:8px}.stat-card{background:#fff;border:1px solid #dfe5ec;border-radius:8px;padding:10px 14px}.stat-card header{display:flex;justify-content:space-between;font-size:13px;font-weight:bold}.stat-card header i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px}.stat-card .bad{color:#b42318}.stat-card .good{color:#168256}.meter{height:7px;background:#e9edf2;border-radius:9px;margin:8px 0 6px;overflow:hidden}.meter span{height:100%;display:block;border-radius:9px}.meter-bad{background:#dc2626}.meter-good{background:#16a34a}.stat-card p{margin:0;color:#667085;font-size:11px}.stat-card p span{float:right}@media(max-width:700px){.worker-shift-chart{padding:10px}.page-header{align-items:center}.page-desc{display:none}.header-controls{flex-wrap:wrap;margin-left:0}.chart-header{display:block}.legend{justify-content:flex-start;margin-top:9px}.time-row,.worker-row{grid-template-columns:115px 1fr}.worker-title,.worker-name{padding-left:9px;padding-right:9px}}
</style>
