<template>
  <main class="worker-shift-chart">
    <header class="page-header">
      <div>
        <h1>シフト確認</h1>
        <p>自分の配置と、同じラインで勤務するメンバーの担当を確認できます。</p>
      </div>
      <button class="today-button" type="button" @click="selectedDate = today">今日</button>
    </header>

    <section class="filters" aria-label="表示条件">
      <label>日付 <input v-model="selectedDate" type="date" /></label>
      <label>ライン
        <select v-model.number="currentLineId">
          <option v-for="line in availableLines" :key="line.id" :value="line.id">{{ line.name }}</option>
        </select>
      </label>
    </section>

    <p v-if="loading" class="notice">シフトを読み込んでいます…</p>
    <p v-else-if="!availableLines.length" class="notice">
      あなたに紐づくシフトラインがありません。管理者に作業者の登録を依頼してください。
    </p>

    <template v-else>
      <section class="my-shift" aria-label="自分のシフト">
        <span class="section-label">自分のシフト</span>
        <template v-if="myAssignments.length">
          <strong>{{ myWorker.name }}</strong>
          <span v-for="assignment in myAssignments" :key="assignment.id" class="my-job">
            {{ assignment.start_time.slice(0, 5) }}〜{{ endLabel(assignment) }}　{{ assignment.process_name }}
          </span>
        </template>
        <span v-else>この日の配置はありません。</span>
      </section>

      <section class="chart-card">
        <div class="chart-header">
          <div>
            <h2>{{ formattedDate }}　{{ currentLine?.name }}</h2>
            <p>青い行があなたです。表示時間は 8:00〜22:00 です。</p>
          </div>
          <div class="legend">
            <span v-for="process in currentLine?.line_processes || []" :key="process.id">
              <i :style="{ background: process.color }"></i>{{ process.process_name }}
            </span>
          </div>
        </div>

        <div class="chart-scroll">
          <div class="chart" :style="{ '--hours': displayHours }">
            <div class="time-row"><div class="worker-title">作業者</div><div class="time-scale"><span v-for="hour in timeLabels" :key="hour" :style="{ left: `${(hour - startHour) / displayHours * 100}%` }">{{ hour }}:00</span></div></div>
            <div v-for="worker in currentLine?.workers || []" :key="worker.id" class="worker-row" :class="{ mine: Number(worker.user) === currentUserId }">
              <div class="worker-name">
                <strong>{{ worker.name }}</strong>
                <small>{{ worker.shift_type }}勤・{{ actualStart(worker) }}出勤</small>
                <small class="worker-total">実働合計 {{ totalWork(worker) }}h</small>
              </div>
              <div class="track">
                <span v-for="assignment in assignmentsFor(worker.id)" :key="assignment.id" class="assignment"
                  :style="assignmentStyle(assignment)" :title="`${assignment.process_name} ${assignment.start_time.slice(0, 5)}〜${endLabel(assignment)}`">
                  <b>{{ assignment.process_name }} <em>{{ assignment.units || 0 }}台</em></b>
                  <small>{{ assignment.start_time.slice(0, 5) }}〜{{ endLabel(assignment) }}・実働{{ assignment.work_hours }}h</small>
                </span>
                <span v-for="(breakTime, index) in breaksForWorker(worker.id)" :key="`break-${index}`" class="break-bar" :class="{ meal: breakTime.label === '昼休憩' }" :style="breakStyle(breakTime)" :title="`${breakTime.label} ${clockLabel(breakTime.start)}〜${clockLabel(breakTime.end)}`">
                  <b v-if="breakTime.label === '昼休憩'">昼休憩</b>
                </span>
                <div v-if="breaksForWorker(worker.id).length" class="break-summary"><strong>自動休憩</strong><span v-for="(breakTime, index) in breaksForWorker(worker.id)" :key="`summary-${index}`">{{ breakTime.label }} {{ clockLabel(breakTime.start) }}〜{{ clockLabel(breakTime.end) }}</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'

const startHour = 8
const endHour = 22
const displayHours = endHour - startHour
const today = new Date().toISOString().slice(0, 10)
const selectedDate = ref(today)
const lines = ref([])
const currentLineId = ref(null)
const assignments = ref([])
const loading = ref(true)

const currentUserId = computed(() => Number(authState.user?.id || 0))
const availableLines = computed(() => lines.value.filter(line =>
  line.workers?.some(worker => Number(worker.user) === currentUserId.value)
))
const currentLine = computed(() => availableLines.value.find(line => line.id === currentLineId.value) || null)
const myWorker = computed(() => currentLine.value?.workers?.find(worker => Number(worker.user) === currentUserId.value) || null)
const myAssignments = computed(() => myWorker.value ? assignmentsFor(myWorker.value.id) : [])
const formattedDate = computed(() => selectedDate.value.replaceAll('-', '/'))
const timeLabels = computed(() => Array.from({ length: displayHours + 1 }, (_, index) => startHour + index))

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
    for (const [offset, length, label] of [[120, 10, '休憩'], [250, 45, '昼休憩'], [415, 10, '休憩'], [545, 10, '休憩']]) breaks.push({ start: start + offset, end: start + offset + length, label })
  } else {
    for (const [offset, length, label] of [[120, 10, '休憩'], [240, 45, '昼休憩'], [420, 10, '休憩']]) {
      if (start + offset < start + 545) breaks.push({ start: start + offset, end: start + offset + length, label })
    }
    if (end > start + 545) {
      breaks.push({ start: start + 545, end: start + 555, label: '残業前休憩' })
      for (let breakStart = start + 675; breakStart < end; breakStart += 130) breaks.push({ start: breakStart, end: breakStart + 10, label: '残業休憩' })
    }
  }
  return breaks.filter(item => item.start < end)
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
    .filter(assignment => Number(assignment.worker) === Number(workerId))
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
  return clockLabel(workerDay(worker.id)?.start ?? minutes(worker.work_start))
}

function totalWork(worker) {
  return assignmentsFor(worker.id).reduce((sum, assignment) => sum + Number(assignment.work_hours || 0), 0)
}

async function loadAssignments() {
  if (!currentLineId.value) {
    assignments.value = []
    return
  }
  const { data } = await api.shifts.getAssignments({ shift_line: currentLineId.value, date: selectedDate.value })
  assignments.value = data || []
}

onMounted(async () => {
  try {
    const { data } = await api.shifts.getLines()
    lines.value = data || []
    currentLineId.value = availableLines.value[0]?.id || null
    await loadAssignments()
  } finally {
    loading.value = false
  }
})

watch([currentLineId, selectedDate], loadAssignments)
</script>

<style scoped>
.worker-shift-chart{max-width:1540px;margin:0 auto;padding:10px 20px 40px;color:#17243a}.page-header{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:6px}.page-header h1{font-size:18px;margin:0 0 3px}.page-header p,.chart-header p{margin:0;color:#667085;font-size:12px}.today-button{border:1px solid #17365d;background:#fff;color:#17365d;border-radius:5px;padding:5px 12px;font-size:12px;font-weight:bold;cursor:pointer}.filters{display:flex;gap:8px;align-items:center;margin:0 0 6px;padding:8px 12px;background:#fff;border:1px solid #dfe5ec;border-radius:8px}.filters label{display:flex;align-items:center;gap:5px;font-size:11px;font-weight:bold;color:#667085}.filters input,.filters select{height:auto;padding:5px 7px;border:1px solid #cbd5e1;border-radius:4px;background:#fff;font-size:13px}.notice,.my-shift{margin:8px 0;padding:10px 14px;border-radius:8px;background:#fff;border:1px solid #dfe5ec}.my-shift{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px}.section-label{font-weight:bold;color:#17365d}.my-job{padding:4px 8px;border-radius:4px;background:#e9f0fb}.chart-card{background:#fff;border:1px solid #dfe5ec;border-radius:8px;overflow:hidden}.chart-header{display:flex;justify-content:space-between;gap:15px;padding:15px 18px;border-bottom:1px solid #dfe5ec}.chart-header h2{font-size:18px;margin:0 0 3px}.legend{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:10px;font-size:12px;font-weight:bold}.legend span{white-space:nowrap}.legend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:5px}.chart-scroll{overflow-x:auto}.chart{min-width:900px}.time-row,.worker-row{display:grid;grid-template-columns:140px 1fr}.time-row{font-size:10px;font-weight:bold;color:#627083}.worker-title,.time-scale{height:49px;background:#f7f9fb}.worker-title{padding:16px;border-right:1px solid #dfe5ec;font-size:12px;color:#17243a}.time-scale,.track{position:relative;background-image:linear-gradient(to right,#edf0f4 1px,transparent 1px);background-size:calc(100% / var(--hours)) 100%}.time-scale span{position:absolute;top:16px;transform:translateX(-50%)}.time-scale span:first-child{transform:none}.time-scale span:last-child{transform:translateX(-100%)}.worker-row{height:94px}.worker-name{height:94px;padding:12px 16px;border-top:1px solid #dfe5ec;border-right:1px solid #dfe5ec;background:#edf5ff;border-left:5px solid #3b82f6}.worker-name strong,.worker-name small{display:block}.worker-name small{margin-top:3px;font-size:11px;color:#2563a9;font-weight:bold}.worker-name .worker-total{color:#14734d;font-weight:bold}.worker-row:not(.mine) .worker-name{background:#f8fafc;border-left-color:transparent}.track{height:94px;border-top:1px solid #dfe5ec}.assignment{position:absolute;top:7px;height:48px;min-width:4px;border:0;border-radius:6px;color:#fff;text-align:left;padding:6px 9px;overflow:hidden;box-shadow:0 2px 4px #1d29394d}.assignment b,.assignment small{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.assignment b{font-size:12px}.assignment small{font-size:9px;margin-top:2px}.assignment em{font-style:normal;background:#ffffff35;padding:1px 4px;border-radius:4px}.break-bar{position:absolute;top:5px;height:52px;z-index:2;pointer-events:none;background:#ffd52b;border:2px solid #8d6800;border-radius:4px;box-shadow:0 1px 3px #0004;min-width:5px}.break-bar.meal{background:repeating-linear-gradient(135deg,#ffe67a,#ffe67a 8px,#ffc928 8px,#ffc928 16px);padding:5px 3px;color:#332700;text-align:center}.break-bar.meal b{font-size:9px;white-space:nowrap}.break-summary{position:absolute;left:0;right:0;bottom:5px;height:27px;display:flex;align-items:center;gap:12px;padding:4px 8px;background:#fff9d8;border-top:1px solid #e2c75d;color:#624b00;font-size:10px;font-weight:bold;white-space:nowrap;overflow:hidden}.break-summary strong{background:#ffd52b;color:#493700;border-radius:4px;padding:2px 6px}@media(max-width:700px){.worker-shift-chart{padding:10px}.page-header{align-items:center}.page-header p{display:none}.filters{flex-wrap:wrap}.chart-header{display:block}.legend{justify-content:flex-start;margin-top:9px}.time-row,.worker-row{grid-template-columns:115px 1fr}.worker-title,.worker-name{padding-left:9px;padding-right:9px}}
</style>
