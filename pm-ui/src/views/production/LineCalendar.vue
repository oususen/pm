<template>
  <div class="page">
    <div v-if="!canView" class="empty">
      この画面を閲覧する権限がありません。
    </div>

    <template v-else>
    <div class="header-row">
      <div class="title-wrap">
        <h2 class="page-title">ライン勤務カレンダ</h2>
        <p class="hint">勤務時間の編集は常に表示、新規カレンダ作成は必要時のみ開きます。</p>
      </div>
      <button class="btn toggle" @click="showCreator = !showCreator" :disabled="!canEdit">
        {{ showCreator ? '作成を閉じる' : 'カレンダ作成' }}
      </button>
    </div>

    <div class="main-layout">
      <div class="left-column">
    <div class="section">
      <div class="row">
        <div class="field">
          <label>ライン</label>
          <select v-model.number="selectedLine" @change="onLineChange">
            <option value="">未選択</option>
            <option v-for="l in prodLines" :key="l.id" :value="l.id">
              {{ l.line_code }} - {{ l.line_name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label>割当カレンダ</label>
          <select v-model.number="selectedCalendar">
            <option value="">未選択</option>
            <option v-for="c in assignableCalendars" :key="c.id" :value="c.id">
              {{ c.calendar_code }} - {{ c.calendar_name }}
            </option>
          </select>
        </div>
        <div class="actions">
          <button class="btn primary" @click="assignCalendar" :disabled="!selectedLine || !selectedCalendar || savingAssign || !canEdit || isReadOnlyLine">
            ラインに割当
          </button>
          <button class="btn" @click="loadCalendars">再読込</button>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="card inline-card one-container">
        <div class="one-container-grid">
          <div class="one-pane">
          <div class="card-title">勤務日一括登録</div>
          <div class="row inline">
            <div class="field">
              <label>開始日</label>
              <input type="date" v-model="range.start" :disabled="!canEdit || isReadOnlyLine" />
            </div>
            <div class="field">
              <label>終了日</label>
              <input type="date" v-model="range.end" :disabled="!canEdit || isReadOnlyLine" />
            </div>
            <div class="field">
              <label>勤務パターン</label>
              <select v-model.number="range.workPattern" @change="onPatternChange" :disabled="!canEdit || isReadOnlyLine">
                <option value="">選択なし</option>
                <option v-for="p in workPatterns" :key="p.id" :value="p.id">
                  {{ p.pattern_name }} ({{ p.start_time }}〜{{ p.end_time }} / {{ formatMinutes(calculateWorkMinutes(p)) }})
                </option>
              </select>
            </div>
            <div class="field small">
              <label>稼働分</label>
              <input type="number" v-model.number="range.workMinutes" min="0" :disabled="!canEdit || isReadOnlyLine" />
            </div>
            <div class="field action-field">
              <label>&nbsp;</label>
              <button class="btn primary" @click="applyRange" :disabled="!selectedCalendar || applyingRange || !canEdit || isReadOnlyLine">
                登録 / 更新
              </button>
            </div>
          </div>
          </div>

          <div class="one-pane">
          <div class="card-title">カレンダコピー</div>
          <div class="row inline">
            <div class="field">
              <label>コピー元</label>
              <select v-model.number="copy.srcId" :disabled="!canEdit || isReadOnlyLine">
                <option value="">選択</option>
                <option v-for="c in calendars" :key="c.id" :value="c.id">
                  {{ c.calendar_code }} - {{ c.calendar_name }}
                </option>
              </select>
            </div>
            <div class="field">
              <label>コピー先</label>
              <select v-model.number="copy.dstId" :disabled="!canEdit || isReadOnlyLine">
                <option value="">選択</option>
                <option v-for="c in assignableCalendars" :key="c.id" :value="c.id">
                  {{ c.calendar_code }} - {{ c.calendar_name }}
                </option>
              </select>
            </div>
            <div class="field">
              <label>開始日</label>
              <input type="date" v-model="copy.start" :disabled="!canEdit || isReadOnlyLine" />
            </div>
            <div class="field">
              <label>終了日</label>
              <input type="date" v-model="copy.end" :disabled="!canEdit || isReadOnlyLine" />
            </div>
            <div class="field action-field">
              <label>&nbsp;</label>
              <button class="btn primary" @click="copyCalendar" :disabled="copyingCalendar || !canEdit || isReadOnlyLine">
                コピー実行
              </button>
            </div>
          </div>
        </div>
      </div>
      </div>

      <div class="card" v-if="showCreator">
        <div class="card-title">新規カレンダ</div>
        <div class="field">
          <label>カレンダコード</label>
          <input v-model="newCalendar.code" placeholder="例: line_T1" :disabled="!canEdit || isReadOnlyLine" />
        </div>
        <div class="field">
          <label>カレンダ名</label>
          <input v-model="newCalendar.name" placeholder="例: タンクライン勤務" :disabled="!canEdit || isReadOnlyLine" />
        </div>
        <button class="btn primary" @click="createCalendar" :disabled="creatingCalendar || !canEdit || isReadOnlyLine">作成</button>
      </div>
    </div>

      </div>

      <div class="right-column">
    <div class="section">
      <div class="table-head">
        <div>
          <div class="card-title">カレンダ日一覧</div>
          <div class="hint">対象カレンダ: {{ currentCalendarLabel }}</div>
        </div>
        <div class="table-head-actions">
          <div class="month-head">
          <button class="btn" @click="moveMonth(-1)" :disabled="!selectedCalendar">前月へ</button>
          <div class="month-title">{{ monthTitle }}</div>
          <button class="btn" @click="moveMonth(1)" :disabled="!selectedCalendar">次月へ</button>
        </div>
          <button class="btn" @click="loadCalendarDays" :disabled="!selectedCalendar">再読込</button>
        </div>
      </div>

      <div v-if="!selectedCalendar" class="empty">
        カレンダを選択してください。
      </div>

      <table v-else class="calendar-table">
        <thead>
          <tr>
            <th v-for="(name, idx) in weekdayNames" :key="name">
              <span>{{ name }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(week, idx) in monthWeeks" :key="idx">
            <td v-for="day in week" :key="day.key" :class="cellClass(day)">
              <div class="day-cell-btn">
                <div class="day-main">
                  <div v-if="day.inMonth" class="day-meta">
                    <div class="day-left">
                      <div class="day-num">{{ day.day }}</div>
                      <label
                        class="day-check"
                        :class="{ holiday: !day.is_working_day }"
                      >
                        <input
                          type="checkbox"
                          :checked="day.is_working_day"
                          :disabled="savingDateKey === day.date || !canEdit || isReadOnlyLine"
                          @change="toggleDay(day)"
                        />
                        {{ day.is_working_day ? '出' : '休み' }}
                      </label>
                    </div>
                    <div class="day-right">
                      <div class="day-pattern">{{ getDayPatternName(day) }}</div>
                      <div class="day-time">{{ getDayPatternTime(day) }}</div>
                    </div>
                  </div>
                  <div v-else class="day-num">{{ day.day }}</div>
                </div>
                <div class="day-memo">
                  <textarea
                    v-if="day.inMonth"
                    class="note-input"
                    :value="day.record?.note || ''"
                    placeholder="メモ"
                    :disabled="savingDateKey === day.date || savingNoteDateKey === day.date || !canEdit || isReadOnlyLine"
                    @blur="saveDayNote(day, $event)"
                  ></textarea>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const canAccessLineCalendars = (level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === 'production.line_calendars')) {
    return hasPermission(user, 'production.line_calendars', level)
  }
  return hasPermission(user, 'production', level)
}

const canView = computed(() => canAccessLineCalendars('view'))
const canEdit = computed(() => canAccessLineCalendars('edit'))

const lines = ref([])
const calendars = ref([])
const calendarDays = ref([])
const workPatterns = ref([])
const daisoCalendarId = ref('')
const daisoCalendarDays = ref([])
const showCreator = ref(false)

const selectedLine = ref('')
const selectedCalendar = ref('')

const savingAssign = ref(false)
const creatingCalendar = ref(false)
const applyingRange = ref(false)
const applyingWeekday = ref(false)
const copyingCalendar = ref(false)
const savingDateKey = ref('')
const savingNoteDateKey = ref('')

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

const range = ref({
  start: '',
  end: '',
  workMinutes: 480,
  workPattern: '',
})

const weekdayNames = ['日', '月', '火', '水', '木', '金', '土']
const weekdayChecks = ref([false, false, false, false, false, false, false])
const currentMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))

const ymd = (dateObj) => {
  const y = dateObj.getFullYear()
  const m = String(dateObj.getMonth() + 1).padStart(2, '0')
  const d = String(dateObj.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const formatMonth = (dateObj) => `${dateObj.getFullYear()}年${dateObj.getMonth() + 1}月`

const formatMinutes = (minutes) => {
  if (!minutes && minutes !== 0) return '-'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}h${mins}m`
}

const getWorkPatternById = (patternId) => {
  if (!patternId) return null
  return workPatterns.value.find((p) => p.id === patternId) || null
}

const getDayPatternName = (day) => {
  const pattern = getWorkPatternById(day?.record?.work_pattern)
  if (!pattern) return '-'
  const minutes = Number(day?.record?.work_minutes)
  if (Number.isFinite(minutes)) {
    return `${pattern.pattern_name}（${minutes.toLocaleString()}分）`
  }
  return pattern.pattern_name
}

const getDayPatternTime = (day) => {
  const pattern = getWorkPatternById(day?.record?.work_pattern)
  if (!pattern?.start_time || !pattern?.end_time) return '-'
  return `${pattern.start_time} - ${pattern.end_time}`
}

const calculateWorkMinutes = (pattern) => {
  if (!pattern || !pattern.start_time || !pattern.end_time) return 0
  const toMinutes = (timeStr) => {
    const [hours, minutes] = timeStr.split(':').map(Number)
    return hours * 60 + minutes
  }
  const startMinutes = toMinutes(pattern.start_time)
  let endMinutes = toMinutes(pattern.end_time)
  if (endMinutes <= startMinutes) endMinutes += 24 * 60

  let breakMinutes = 0
  if (pattern.break_times && pattern.break_times.length > 0) {
    for (const bt of pattern.break_times) {
      const breakStart = toMinutes(bt.break_start)
      let breakEnd = toMinutes(bt.break_end)
      if (breakEnd <= breakStart) breakEnd += 24 * 60
      breakMinutes += breakEnd - breakStart
    }
  }
  return endMinutes - startMinutes - breakMinutes
}

const currentCalendarLabel = computed(() => {
  const c = calendars.value.find((x) => x.id === selectedCalendar.value)
  return c ? `${c.calendar_code} - ${c.calendar_name}` : '未選択'
})

const selectedLineObj = computed(() => lines.value.find((l) => l.id === selectedLine.value) || null)
const isReadOnlyLine = computed(() => String(selectedLineObj.value?.line_type || '').toUpperCase() === 'PURCHASE')
const prodLines = computed(() => lines.value.filter((line) => String(line?.line_type || '').toUpperCase() === 'PROD'))
const assignableCalendars = computed(() => calendars.value.filter((calendar) => calendar?.is_line_assignable !== false))

const monthTitle = computed(() => formatMonth(currentMonth.value))

const monthRange = computed(() => {
  const start = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth(), 1)
  const end = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth() + 1, 0)
  return { start, end }
})

const dayMap = computed(() => {
  const map = new Map()
  for (const row of calendarDays.value) map.set(row.target_date, row)
  return map
})

const daisoDayMap = computed(() => {
  const map = new Map()
  for (const row of daisoCalendarDays.value) map.set(row.target_date, row)
  return map
})

const monthWeeks = computed(() => {
  const { start, end } = monthRange.value
  const firstDay = new Date(start)
  firstDay.setDate(firstDay.getDate() - firstDay.getDay())
  const lastDay = new Date(end)
  lastDay.setDate(lastDay.getDate() + (6 - lastDay.getDay()))

  const rows = []
  let cursor = new Date(firstDay)
  while (cursor <= lastDay) {
    const week = []
    for (let i = 0; i < 7; i += 1) {
      const dateStr = ymd(cursor)
      const inMonth = cursor.getMonth() === currentMonth.value.getMonth()
      const existing = dayMap.value.get(dateStr)
      const daiso = daisoDayMap.value.get(dateStr)
      const fallbackWorking = daiso ? !!daiso.is_working_day : cursor.getDay() !== 0 && cursor.getDay() !== 6
      week.push({
        key: `${dateStr}-${i}`,
        date: dateStr,
        day: cursor.getDate(),
        inMonth,
        record: existing || null,
        is_working_day: existing ? !!existing.is_working_day : fallbackWorking,
      })
      cursor.setDate(cursor.getDate() + 1)
    }
    rows.push(week)
  }
  return rows
})

const cellClass = (day) => ({
  out: !day.inMonth,
  work: day.inMonth && day.is_working_day,
  holiday: day.inMonth && !day.is_working_day,
})

const loadLines = async () => {
  const res = await api.lines.getLines()
  const rows = res.data.results || res.data || []
  lines.value = [...rows].sort((a, b) => {
    const aCode = String(a?.line_code || '')
    const bCode = String(b?.line_code || '')
    return aCode.localeCompare(bCode, 'ja')
  })
  if (selectedLine.value && !prodLines.value.some((line) => line.id === selectedLine.value)) {
    selectedLine.value = ''
  }
  const line = lines.value.find((l) => l.id === selectedLine.value)
  if (line?.calendar) selectedCalendar.value = line.calendar
}

const loadCalendars = async () => {
  const res = await api.calendars.getCalendars()
  calendars.value = res.data.results || res.data || []
  if (selectedCalendar.value && !assignableCalendars.value.some((calendar) => calendar.id === selectedCalendar.value)) {
    selectedCalendar.value = ''
  }
}

const loadWorkPatterns = async () => {
  const res = await api.workPatterns.getWorkPatterns()
  workPatterns.value = res.data.results || res.data || []
}

const onPatternChange = () => {
  const pattern = workPatterns.value.find((p) => p.id === range.value.workPattern)
  if (pattern) range.value.workMinutes = calculateWorkMinutes(pattern)
}

const onLineChange = async () => {
  const line = lines.value.find((l) => l.id === selectedLine.value)
  const nextCalendar = line?.calendar || ''
  selectedCalendar.value = assignableCalendars.value.some((calendar) => calendar.id === nextCalendar) ? nextCalendar : ''
  await loadCalendarDays()
}

const loadCalendarDays = async () => {
  if (!selectedCalendar.value) {
    calendarDays.value = []
    return
  }
  const { start, end } = monthRange.value
  const res = await fetchCalendarDaysByRange(ymd(start), ymd(end))
  calendarDays.value = res
}

const fetchCalendarDaysByRange = async (startDate, endDate) => {
  if (!selectedCalendar.value) return []
  const res = await api.calendars.getCalendarDays(selectedCalendar.value, {
    page_size: 500,
    target_date__gte: startDate,
    target_date__lte: endDate,
  })
  return res.data.results || res.data || []
}

const ensureDaisoCalendarId = async () => {
  if (daisoCalendarId.value) return daisoCalendarId.value
  const res = await api.calendars.getCalendars({ search: 'daiso', page_size: 200 })
  const rows = res.data.results || res.data || []
  const found = rows.find((row) => String(row.calendar_code || '').toLowerCase() === 'daiso')
  daisoCalendarId.value = found?.id || ''
  return daisoCalendarId.value
}

const loadDaisoCalendarDays = async () => {
  const { start, end } = monthRange.value
  await ensureDaisoCalendarId()
  if (!daisoCalendarId.value) {
    daisoCalendarDays.value = []
    return
  }
  const res = await api.calendars.getCalendarDays(daisoCalendarId.value, {
    page_size: 500,
    target_date__gte: ymd(start),
    target_date__lte: ymd(end),
  })
  daisoCalendarDays.value = res.data.results || res.data || []
}

const moveMonth = async (delta) => {
  currentMonth.value = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth() + delta, 1)
  await Promise.all([loadCalendarDays(), loadDaisoCalendarDays()])
}

const toggleWeekday = async (weekday, checked) => {
  if (!canEdit.value) return
  if (!selectedCalendar.value) return
  applyingWeekday.value = true
  try {
    const { start, end } = monthRange.value
    const existing = new Map()
    calendarDays.value.forEach((d) => existing.set(d.target_date, d))
    const ops = []

    for (let day = new Date(start); day <= end; day.setDate(day.getDate() + 1)) {
      if (day.getDay() !== weekday) continue
      const dateStr = ymd(day)
      const row = existing.get(dateStr)
      if (row?.id) {
        ops.push(
          api.calendars.updateCalendarDay(row.id, {
            calendar: selectedCalendar.value,
            target_date: dateStr,
            is_working_day: checked,
            work_minutes: checked ? (row.work_minutes ?? 480) : 0,
            work_pattern: row.work_pattern || null,
            note: row.note || null,
          }),
        )
      } else {
        ops.push(
          api.calendars.createCalendarDay({
            calendar: selectedCalendar.value,
            target_date: dateStr,
            is_working_day: checked,
            work_minutes: checked ? 480 : 0,
            work_pattern: null,
            note: null,
          }),
        )
      }
    }

    if (ops.length) {
      await Promise.all(ops)
      await loadCalendarDays()
    }
  } catch (e) {
    console.error('曜日反映エラー', e)
    alert('曜日の反映に失敗しました。')
    weekdayChecks.value[weekday] = !checked
  } finally {
    applyingWeekday.value = false
  }
}

const assignCalendar = async () => {
  if (!canEdit.value) return
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
  if (!canEdit.value) return
  if (!newCalendar.value.code || !newCalendar.value.name) {
    alert('コードと名称を入力してください。')
    return
  }
  creatingCalendar.value = true
  try {
    const res = await api.calendars.createCalendar({
      calendar_code: newCalendar.value.code,
      calendar_name: newCalendar.value.name,
      calendar_type: 'INTERNAL',
      is_supplier_assignable: false,
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
  if (!canEdit.value) return
  if (isReadOnlyLine.value) return
  if (!selectedCalendar.value || !range.value.start || !range.value.end) {
    alert('開始日/終了日/カレンダを入力してください。')
    return
  }
  applyingRange.value = true
  try {
    const existingRows = await fetchCalendarDaysByRange(range.value.start, range.value.end)
    const workingRows = existingRows.filter((row) => !!row.is_working_day)

    if (!workingRows.length) {
      alert('対象期間に出勤日がありません。先に出勤日を設定してください。')
      return
    }

    const ops = []
    for (const row of workingRows) {
      ops.push(api.calendars.updateCalendarDay(row.id, {
        calendar: selectedCalendar.value,
        target_date: row.target_date,
        is_working_day: true,
        work_minutes: range.value.workMinutes,
        work_pattern: range.value.workPattern || null,
      }))
    }

    await Promise.all(ops)
    await loadCalendarDays()
    alert(`出勤日 ${workingRows.length} 件に勤務パターンを適用しました。`)
  } catch (e) {
    console.error('勤務時間登録エラー', e)
    alert('登録に失敗しました。')
  } finally {
    applyingRange.value = false
  }
}

const copyCalendar = async () => {
  if (!canEdit.value) return
  if (isReadOnlyLine.value) return
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

const toggleDay = async (day) => {
  if (!canEdit.value) return
  if (isReadOnlyLine.value) return
  if (!day?.inMonth || !selectedCalendar.value) return
  savingDateKey.value = day.date
  try {
    const nextWorking = !day.is_working_day
    if (day.record?.id) {
      await api.calendars.updateCalendarDay(day.record.id, {
        calendar: selectedCalendar.value,
        target_date: day.date,
        is_working_day: nextWorking,
        work_minutes: nextWorking ? (day.record.work_minutes ?? 480) : 0,
        work_pattern: day.record.work_pattern || null,
      })
    } else {
      await api.calendars.createCalendarDay({
        calendar: selectedCalendar.value,
        target_date: day.date,
        is_working_day: nextWorking,
        work_minutes: nextWorking ? 480 : 0,
        work_pattern: null,
      })
    }
    await loadCalendarDays()
  } catch (e) {
    console.error('カレンダ日更新エラー', e)
    alert('日付の更新に失敗しました。')
  } finally {
    savingDateKey.value = ''
  }
}

const saveDayNote = async (day, event) => {
  if (!canEdit.value) return
  if (isReadOnlyLine.value) return
  if (!day?.inMonth || !selectedCalendar.value) return
  const inputNote = String(event?.target?.value || '').trim()
  const currentNote = String(day.record?.note || '').trim()
  if (inputNote === currentNote) return

  savingNoteDateKey.value = day.date
  try {
    if (day.record?.id) {
      await api.calendars.updateCalendarDay(day.record.id, {
        calendar: selectedCalendar.value,
        target_date: day.date,
        is_working_day: day.is_working_day,
        work_minutes: day.is_working_day ? (day.record.work_minutes ?? 480) : 0,
        work_pattern: day.record.work_pattern || null,
        note: inputNote || null,
      })
    } else {
      await api.calendars.createCalendarDay({
        calendar: selectedCalendar.value,
        target_date: day.date,
        is_working_day: day.is_working_day,
        work_minutes: day.is_working_day ? 480 : 0,
        work_pattern: null,
        note: inputNote || null,
      })
    }
    await loadCalendarDays()
  } catch (e) {
    console.error('メモ保存エラー', e)
    alert('メモ保存に失敗しました。')
  } finally {
    savingNoteDateKey.value = ''
  }
}

onMounted(async () => {
  if (!canView.value) return
  await Promise.all([loadLines(), loadCalendars(), loadWorkPatterns()])
  await loadDaisoCalendarDays()
})
</script>

<style scoped>
.page {
  padding: 12px;
  font-size: 16px;
}
.page-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  padding: 2px 0;
}
.title-wrap {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.section {
  margin-bottom: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  background: #fff;
}
.main-layout {
  display: grid;
  grid-template-columns: 1fr 2.3fr;
  gap: 12px;
  align-items: start;
}
.left-column,
.right-column {
  min-width: 0;
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
  min-width: 0;
}
.field input,
.field select {
  min-width: 0;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  font-size: 16px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.field select {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.field.checkbox {
  flex-direction: row;
  align-items: center;
}
.actions {
  display: flex;
  gap: 8px;
}
.card {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px;
  background: #f8fafc;
  display: grid;
  gap: 8px;
}
.one-container-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}
.one-pane {
  padding: 4px;
}
.one-pane + .one-pane {
  border-top: 2px solid #cbd5e1;
  margin-top: 6px;
  padding-top: 10px;
}
.card-title {
  font-size: 18px;
  font-weight: 700;
}
.btn {
  padding: 6px 10px;
  font-size: 15px;
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
.table-head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.hint {
  font-size: 15px;
  color: #6b7280;
  margin: 0;
  line-height: 1.2;
}
.row.compact .btn {
  min-width: 140px;
}
.empty {
  color: #94a3b8;
  padding: 10px;
}
.month-head {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.month-title {
  font-size: 20px;
  font-weight: 700;
  min-width: 140px;
  text-align: center;
}
.calendar-table {
  width: 100%;
  max-width: 1800px;
  margin: 0 auto;
  border-collapse: collapse;
}
.calendar-table th,
.calendar-table td {
  border: 2px solid #cbd5e1;
  width: calc(100% / 7);
  vertical-align: top;
  padding: 0;
}
.calendar-table th {
  background: #f8fafc;
  font-size: 16px;
  font-weight: 700;
  text-align: center;
  padding: 6px 0;
}
.weekday-check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.day-cell-btn {
  width: 100%;
  min-height: 0;
  cursor: default;
  padding: 6px;
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: auto auto;
  gap: 6px;
  align-items: stretch;
}
.day-main {
  text-align: left;
}
.day-check {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 15px;
  padding: 0;
}
.day-check.holiday {
  color: #ff0000;
  font-weight: 700;
}
.day-meta {
  display: grid;
  grid-template-columns: 2fr 3fr;
  gap: 6px;
  align-items: center;
  height: 100%;
}
.day-left {
  display: grid;
  gap: 4px;
}
.day-right {
  display: flex;
  flex-direction: column;
  gap: 2px;
  text-align: right;
  font-size: 15px;
  color: #334155;
}
.day-pattern {
  font-weight: 600;
  padding: 0;
  display: block;
  line-height: 1.2;
  white-space: nowrap;
}
.day-time {
  padding: 0;
  display: block;
  line-height: 1.2;
  white-space: nowrap;
}
.day-num {
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
  padding: 0;
}
.day-memo {
  display: flex;
  align-items: stretch;
  min-height: auto;
}
.note-input {
  width: 100%;
  box-sizing: border-box;
  border: 0;
  border-radius: 0;
  padding: 0;
  height: 100%;
  min-height: 0;
  font-size: 15px;
  line-height: 1.2;
  resize: none;
  background: transparent !important;
}
@media (max-width: 1280px) {
  .main-layout {
    grid-template-columns: 1fr;
  }
  .one-container-grid {
    grid-template-columns: 1fr;
  }
}
td.work {
  background: #ecfdf5;
}
td.holiday {
  background: #fef2f2;
}
td.out {
  background: #f8fafc;
  color: #94a3b8;
}
</style>

