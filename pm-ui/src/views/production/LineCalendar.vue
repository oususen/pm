<template>
  <div class="page">
    <div class="header-row">
      <div>
        <h2 class="page-title">ライン勤務カレンダ</h2>
        <p class="hint">勤務時間の編集は常に表示、新規カレンダ作成は必要時のみ開きます。</p>
      </div>
      <button class="btn toggle" @click="showCreator = !showCreator">
        {{ showCreator ? '作成を閉じる' : 'カレンダ作成' }}
      </button>
    </div>

    <div class="section">
      <div class="row">
        <div class="field">
          <label>ライン</label>
          <select v-model.number="selectedLine" @change="onLineChange">
            <option value="">未選択</option>
            <option v-for="l in lines" :key="l.id" :value="l.id">
              {{ l.line_code }} - {{ l.line_name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>割当カレンダ</label>
          <select v-model.number="selectedCalendar">
            <option value="">未選択</option>
            <option v-for="c in calendars" :key="c.id" :value="c.id">
              {{ c.calendar_code }} - {{ c.calendar_name }}
            </option>
          </select>
        </div>
        <div class="actions">
          <button class="btn secondary" @click="showAssign = !showAssign">
            {{ showAssign ? '割当を隠す' : '割当設定' }}
          </button>
          <button class="btn" @click="loadCalendars">再読込</button>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="card inline-card">
        <div class="card-title">勤務日一括登録</div>
        <div class="row inline">
          <div class="field">
            <label>開始日</label>
            <input type="date" v-model="range.start" />
          </div>
          <div class="field">
            <label>終了日</label>
            <input type="date" v-model="range.end" />
          </div>
          <div class="field">
            <label>勤務パターン</label>
            <select v-model.number="range.workPattern" @change="onPatternChange">
              <option value="">選択なし</option>
              <option v-for="p in workPatterns" :key="p.id" :value="p.id">
                {{ p.pattern_name }} ({{ p.start_time }}〜{{ p.end_time }} / {{ formatMinutes(calculateWorkMinutes(p)) }})
              </option>
            </select>
          </div>
          <div class="field small">
            <label>稼働分</label>
            <input type="number" v-model.number="range.workMinutes" min="0" />
          </div>
          <div class="field checkbox inline-check">
            <label>
              <input type="checkbox" v-model="range.isWorkingDay" />
              稼働日として登録
            </label>
          </div>
          <div class="field action-field">
            <label>&nbsp;</label>
            <button class="btn primary" @click="applyRange" :disabled="!selectedCalendar || applyingRange">
              登録 / 更新
            </button>
          </div>
        </div>
      </div>

      <div class="card inline-card">
        <div class="card-title">カレンダコピー</div>
        <div class="row inline">
          <div class="field">
            <label>コピー元</label>
            <select v-model.number="copy.srcId">
              <option value="">選択</option>
              <option v-for="c in calendars" :key="c.id" :value="c.id">
                {{ c.calendar_code }} - {{ c.calendar_name }}
              </option>
            </select>
          </div>
          <div class="field">
            <label>コピー先</label>
            <select v-model.number="copy.dstId">
              <option value="">選択</option>
              <option v-for="c in calendars" :key="c.id" :value="c.id">
                {{ c.calendar_code }} - {{ c.calendar_name }}
              </option>
            </select>
          </div>
          <div class="field">
            <label>開始日</label>
            <input type="date" v-model="copy.start" />
          </div>
          <div class="field">
            <label>終了日</label>
            <input type="date" v-model="copy.end" />
          </div>
          <div class="field action-field">
            <label>&nbsp;</label>
            <button class="btn primary" @click="copyCalendar" :disabled="copyingCalendar">
              コピー実行
            </button>
          </div>
        </div>
      </div>

      <div class="card" v-if="showCreator">
        <div class="card-title">新規カレンダ</div>
        <div class="field">
          <label>カレンダコード</label>
          <input v-model="newCalendar.code" placeholder="例: line_T1" />
        </div>
        <div class="field">
          <label>カレンダ名</label>
          <input v-model="newCalendar.name" placeholder="例: タンクライン勤務" />
        </div>
        <button class="btn primary" @click="createCalendar" :disabled="creatingCalendar">作成</button>
      </div>
    </div>

    <div class="section" v-if="showAssign">
      <div class="row compact">
        <div class="field">
          <label>ラインにカレンダ割当</label>
          <button class="btn primary" @click="assignCalendar" :disabled="!selectedLine || !selectedCalendar || savingAssign">
            ラインに割当
          </button>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="table-head">
        <div>
          <div class="card-title">カレンダ日一覧</div>
          <div class="hint">対象カレンダ: {{ currentCalendarLabel }}</div>
        </div>
        <button class="btn" @click="loadCalendarDays" :disabled="!selectedCalendar">再読込</button>
      </div>
      <div class="filter-row">
        <div class="field small">
          <label>開始</label>
          <input type="date" v-model="displayStart" />
        </div>
        <div class="field small">
          <label>終了</label>
          <input type="date" v-model="displayEnd" />
        </div>
      </div>
      <div class="table-wrap" v-if="visibleDays.length">
        <table>
          <thead>
            <tr>
              <th>日付</th>
              <th>曜</th>
              <th>稼働</th>
              <th>稼働分</th>
              <th>勤務パターン</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in visibleDays" :key="d.id">
              <td>{{ d.target_date }}</td>
              <td class="weekday">{{ formatWeekday(d.target_date) }}</td>
              <td>{{ d.is_working_day ? '○' : '×' }}</td>
              <td class="num">{{ d.work_minutes ?? '' }}</td>
              <td>{{ d.work_pattern_name ?? '' }}</td>
              <td class="actions-inline">
                <button class="btn tiny" @click="setHoliday(d)" :disabled="updatingDayId === d.id">
                  休日にする
                </button>
                <button class="btn tiny secondary" @click="setWorkingDay(d)" :disabled="updatingDayId === d.id">
                  稼働日にする
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty">データがありません。カレンダを選択してください。</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import api from '@/api/client'

const lines = ref([])
const calendars = ref([])
const calendarDays = ref([])
const workPatterns = ref([])
const showCreator = ref(false)
const showAssign = ref(false)

const selectedLine = ref('')
const selectedCalendar = ref('')

const savingAssign = ref(false)
const creatingCalendar = ref(false)
const applyingRange = ref(false)
const updatingDayId = ref(null)
const copyingCalendar = ref(false)

const copy = ref({
  srcId: '',
  dstId: '',
  start: '',
  end: '',
})

const newCalendar = ref({
  code: '',
  name: '',
})

const today = new Date()
const defaultEnd = new Date(today)
defaultEnd.setDate(defaultEnd.getDate() + 30)

const displayStart = ref(today.toISOString().slice(0, 10))
const displayEnd = ref(defaultEnd.toISOString().slice(0, 10))

const range = ref({
  start: '',
  end: '',
  workMinutes: 480,
  isWorkingDay: true,
  workPattern: '',
})

const formatMinutes = (minutes) => {
  if (!minutes && minutes !== 0) return '-'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h${mins}m`
}

// 勤務パターンから稼働分を計算
const calculateWorkMinutes = (pattern) => {
  if (!pattern || !pattern.start_time || !pattern.end_time) return 0

  // 時刻を分に変換
  const timeToMinutes = (timeStr) => {
    const [hours, minutes] = timeStr.split(':').map(Number)
    return hours * 60 + minutes
  }

  const startMinutes = timeToMinutes(pattern.start_time)
  let endMinutes = timeToMinutes(pattern.end_time)

  // 終了時刻が開始時刻より早い場合は翌日とみなす（二勤対応）
  if (endMinutes <= startMinutes) {
    endMinutes += 24 * 60
  }

  const totalMinutes = endMinutes - startMinutes

  // 休憩時間の合計を計算
  let breakMinutes = 0
  if (pattern.break_times && pattern.break_times.length > 0) {
    for (const bt of pattern.break_times) {
      const breakStart = timeToMinutes(bt.break_start)
      let breakEnd = timeToMinutes(bt.break_end)

      // 休憩終了が休憩開始より早い場合は翌日とみなす
      if (breakEnd <= breakStart) {
        breakEnd += 24 * 60
      }

      breakMinutes += breakEnd - breakStart
    }
  }

  return totalMinutes - breakMinutes
}

const currentCalendarLabel = computed(() => {
  const c = calendars.value.find((x) => x.id === selectedCalendar.value)
  return c ? `${c.calendar_code} - ${c.calendar_name}` : '未選択'
})

const visibleDays = computed(() => {
  if (!displayStart.value && !displayEnd.value) return calendarDays.value
  const s = displayStart.value ? new Date(displayStart.value) : null
  const e = displayEnd.value ? new Date(displayEnd.value) : null
  return calendarDays.value.filter((d) => {
    const dt = new Date(d.target_date)
    if (s && dt < s) return false
    if (e && dt > e) return false
    return true
  })
})

const formatWeekday = (dateStr) => {
  const w = new Date(dateStr).getDay()
  return ['日', '月', '火', '水', '木', '金', '土'][w] || ''
}

const loadLines = async () => {
  const res = await api.lines.getLines()
  lines.value = res.data.results || res.data || []
  const line = lines.value.find((l) => l.id === selectedLine.value)
  if (line && line.calendar) {
    selectedCalendar.value = line.calendar
  }
}

const loadCalendars = async () => {
  const res = await api.calendars.getCalendars()
  calendars.value = res.data.results || res.data || []
}

const loadWorkPatterns = async () => {
  const res = await api.workPatterns.getWorkPatterns()
  workPatterns.value = res.data.results || res.data || []
}

const onPatternChange = () => {
  const pattern = workPatterns.value.find((p) => p.id === range.value.workPattern)
  if (pattern) {
    range.value.workMinutes = calculateWorkMinutes(pattern)
  }
}

const onLineChange = () => {
  const line = lines.value.find((l) => l.id === selectedLine.value)
  if (line && line.calendar) {
    selectedCalendar.value = line.calendar
  } else {
    selectedCalendar.value = ''
  }
  loadCalendarDays()
}

const loadCalendarDays = async () => {
  if (!selectedCalendar.value) {
    calendarDays.value = []
    return
  }
  const res = await api.calendars.getCalendarDays(selectedCalendar.value)
  const rows = res.data.results || res.data || []
  calendarDays.value = rows.sort((a, b) => a.target_date.localeCompare(b.target_date))
}

const assignCalendar = async () => {
  if (!selectedLine.value || !selectedCalendar.value) return
  savingAssign.value = true
  try {
    await api.lines.patchLine(selectedLine.value, { calendar: selectedCalendar.value })
    alert('ラインに割り当てました。')
  } catch (e) {
    console.error('ラインカレンダ割当エラー', e)
    alert('割当に失敗しました。')
  } finally {
    savingAssign.value = false
  }
}

const createCalendar = async () => {
  if (!newCalendar.value.code || !newCalendar.value.name) {
    alert('コードと名称を入力してください。')
    return
  }
  creatingCalendar.value = true
  try {
    const res = await api.calendars.createCalendar({
      calendar_code: newCalendar.value.code,
      calendar_name: newCalendar.value.name,
    })
    const item = res.data
    calendars.value.push(item)
    selectedCalendar.value = item.id
    newCalendar.value = { code: '', name: '' }
    alert('カレンダを作成しました。')
  } catch (e) {
    console.error('カレンダ作成エラー', e)
    alert('作成に失敗しました。')
  } finally {
    creatingCalendar.value = false
  }
}

const applyRange = async () => {
  if (!selectedCalendar.value || !range.value.start || !range.value.end) {
    alert('開始日/終了日/カレンダを入力してください。')
    return
  }
  applyingRange.value = true
  try {
    const start = new Date(range.value.start)
    const end = new Date(range.value.end)
    const existing = new Map()
    calendarDays.value.forEach((d) => existing.set(d.target_date, d))

    const ops = []
    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      const key = d.toISOString().slice(0, 10)
      const payload = {
        calendar: selectedCalendar.value,
        target_date: key,
        is_working_day: !!range.value.isWorkingDay,
        work_minutes: range.value.workMinutes,
        work_pattern: range.value.workPattern || null,
      }
      if (existing.has(key)) {
        ops.push(api.calendars.updateCalendarDay(existing.get(key).id, payload))
      } else {
        ops.push(api.calendars.createCalendarDay(payload))
      }
    }
    await Promise.all(ops)
    await loadCalendarDays()
    alert('勤務時間を登録しました。')
  } catch (e) {
    console.error('勤務時間登録エラー', e)
    alert('登録に失敗しました。')
  } finally {
    applyingRange.value = false
  }
}

const copyCalendar = async () => {
  if (!copy.value.srcId || !copy.value.dstId || !copy.value.start || !copy.value.end) {
    alert('コピー元・コピー先・開始日・終了日をすべて入力してください。')
    return
  }
  if (copy.value.srcId === copy.value.dstId) {
    alert('コピー元とコピー先が同じカレンダーです。')
    return
  }
  const srcName = calendars.value.find((c) => c.id === copy.value.srcId)?.calendar_name ?? ''
  const dstName = calendars.value.find((c) => c.id === copy.value.dstId)?.calendar_name ?? ''
  if (!confirm(`「${srcName}」の ${copy.value.start}〜${copy.value.end} を「${dstName}」にコピーします。\n同期間のコピー先データは上書きされます。よいですか？`)) return

  copyingCalendar.value = true
  try {
    const res = await api.calendars.copyCalendar(copy.value.srcId, {
      target_calendar_id: copy.value.dstId,
      start_date: copy.value.start,
      end_date: copy.value.end,
    })
    alert(`${res.data.copied} 件コピーしました。`)
    if (selectedCalendar.value === copy.value.dstId) await loadCalendarDays()
  } catch (e) {
    console.error('カレンダコピーエラー', e)
    alert('コピーに失敗しました。')
  } finally {
    copyingCalendar.value = false
  }
}

const setHoliday = async (day) => {
  if (!day?.id) return
  updatingDayId.value = day.id
  try {
    await api.calendars.updateCalendarDay(day.id, {
      calendar: day.calendar,
      target_date: day.target_date,
      is_working_day: false,
      work_minutes: 0,
      work_pattern: null,
    })
    await loadCalendarDays()
  } catch (e) {
    console.error('休日設定エラー', e)
    alert('休日設定に失敗しました。')
  } finally {
    updatingDayId.value = null
  }
}

const setWorkingDay = async (day) => {
  if (!day?.id) return
  updatingDayId.value = day.id
  try {
    await api.calendars.updateCalendarDay(day.id, {
      calendar: day.calendar,
      target_date: day.target_date,
      is_working_day: true,
      work_minutes: (day.work_minutes ?? range.value.workMinutes ?? 480),
      work_pattern: (day.work_pattern ?? range.value.workPattern) || null,
    })
    await loadCalendarDays()
  } catch (e) {
    console.error('稼働日設定エラー', e)
    alert('稼働日設定に失敗しました。')
  } finally {
    updatingDayId.value = null
  }
}

onMounted(async () => {
  await Promise.all([loadLines(), loadCalendars(), loadWorkPatterns()])
})
</script>

<style scoped>
.page {
  padding: 12px;
}
.page-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.section {
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  background: #fff;
}
.btn.toggle {
  background: #0f172a;
  color: #fff;
  border-color: #0f172a;
}
.row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field input,
.field select {
  min-width: 220px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.field.checkbox {
  flex-direction: row;
  align-items: center;
}
.actions {
  display: flex;
  gap: 8px;
}
.two-col {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
}
.card {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px;
  background: #f8fafc;
  display: grid;
  gap: 8px;
}
.card-title {
  font-weight: 700;
}
.btn {
  padding: 6px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.btn.primary {
  background: #2563eb;
  color: #fff;
  border-color: #1d4ed8;
}
.btn.secondary {
  background: #f8fafc;
  border-color: #cbd5e1;
}
.table-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.table-wrap {
  max-height: 360px;
  overflow: auto;
  margin-top: 8px;
}
.actions-inline {
  display: flex;
  gap: 6px;
}
.btn.tiny {
  padding: 4px 8px;
  font-size: 12px;
}
.filter-row {
  display: flex;
  gap: 10px;
  margin: 6px 0;
}
.field.small input {
  min-width: 140px;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  border: 1px solid #e2e8f0;
  padding: 6px 8px;
  font-size: 13px;
}
th {
  background: #f1f5f9;
}
.num {
  text-align: right;
}
.hint {
  font-size: 12px;
  color: #6b7280;
}
.row.compact .btn {
  min-width: 140px;
}
.empty {
  padding: 8px;
  color: #94a3b8;
}
</style>
