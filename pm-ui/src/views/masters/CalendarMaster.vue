<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">カレンダマスタ</h1>
      <div class="page-actions">
        <button class="btn" @click="fetchCalendars">更新</button>
        <button class="btn btn-primary" @click="showNewDialog">新規</button>
      </div>
    </div>

    <div class="main-layout">
      <div class="left-column section">
        <div class="card-title">カレンダ一覧</div>
        <table class="data-table">
          <thead>
            <tr>
              <th>コード</th>
              <th>名称</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="calendar in calendars"
              :key="calendar.id"
              :class="{ selected: detailCalendar && detailCalendar.id === calendar.id }"
              @click="openDetail(calendar)"
            >
              <td>{{ calendar.calendar_code }}</td>
              <td>{{ calendar.calendar_name }}</td>
              <td class="actions-inline">
                <button class="btn-sm" @click.stop="editCalendar(calendar)">編集</button>
                <button class="btn-sm btn-danger" @click.stop="deleteCalendar(calendar.id)">削除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!calendars.length" class="empty">データがありません</div>
      </div>

      <div class="right-column section">
        <div class="table-head">
          <div>
            <div class="card-title">カレンダ日一覧</div>
            <div class="hint">対象: {{ currentCalendarLabel }}</div>
          </div>
          <div class="table-head-actions">
            <button class="btn" @click="moveMonth(-1)" :disabled="!detailCalendar">前月へ</button>
            <div class="month-title">{{ monthTitle }}</div>
            <button class="btn" @click="moveMonth(1)" :disabled="!detailCalendar">次月へ</button>
            <button class="btn" @click="reloadCurrent" :disabled="!detailCalendar || detailLoading">再読込</button>
          </div>
        </div>

        <div v-if="!detailCalendar" class="empty">左の一覧からカレンダを選択してください。</div>
        <div v-else-if="detailLoading" class="empty">読込中...</div>
        <table v-else class="calendar-table">
          <thead>
            <tr>
              <th v-for="name in weekdayNames" :key="name">{{ name }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(week, idx) in monthWeeks" :key="idx">
              <td v-for="day in week" :key="day.key" :class="cellClass(day)">
                <div class="day-wrap">
                  <div v-if="day.inMonth" class="day-main">
                    <div class="day-num">{{ day.day }}</div>
                    <label class="day-check" :class="{ holiday: !day.is_working_day }">
                      <input
                        type="checkbox"
                        :checked="day.is_working_day"
                        :disabled="savingDateKey === day.date"
                        @change="toggleDay(day)"
                      />
                      {{ day.is_working_day ? '出' : '休み' }}
                    </label>
                    <div class="day-pattern">{{ getDayPatternName(day) }}</div>
                    <div class="day-time">{{ getDayPatternTime(day) }}</div>
                    <textarea
                      class="note-input"
                      :value="day.record?.note || ''"
                      placeholder="メモ"
                      :disabled="savingNoteDateKey === day.date"
                      @blur="saveDayNote(day, $event)"
                    ></textarea>
                  </div>
                  <div v-else class="day-out">{{ day.day }}</div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? 'カレンダ編集' : 'カレンダ新規作成' }}</h2>
        <form @submit.prevent="saveCalendar">
          <div class="form-group">
            <label>カレンダコード *</label>
            <input v-model="formData.calendar_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>カレンダ名 *</label>
            <input v-model="formData.calendar_name" required />
          </div>
          <div class="form-group">
            <label>説明</label>
            <textarea v-model="formData.description" rows="3"></textarea>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">保存</button>
            <button type="button" class="btn" @click="closeDialog">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'

const calendars = ref([])
const calendarDays = ref([])
const workPatterns = ref([])
const detailCalendar = ref(null)
const detailLoading = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const savingDateKey = ref('')
const savingNoteDateKey = ref('')
const currentMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))

const formData = ref({
  calendar_code: '',
  calendar_name: '',
  description: ''
})

const weekdayNames = ['日', '月', '火', '水', '木', '金', '土']

const ymd = (dateObj) => {
  const y = dateObj.getFullYear()
  const m = String(dateObj.getMonth() + 1).padStart(2, '0')
  const d = String(dateObj.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const currentCalendarLabel = computed(() => {
  if (!detailCalendar.value) return '未選択'
  return `${detailCalendar.value.calendar_code} - ${detailCalendar.value.calendar_name}`
})

const monthTitle = computed(() => `${currentMonth.value.getFullYear()}年${currentMonth.value.getMonth() + 1}月`)

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

const getWorkPatternById = (patternId) => {
  if (!patternId) return null
  return workPatterns.value.find((p) => p.id === patternId) || null
}

const getDayPatternName = (day) => {
  const pattern = getWorkPatternById(day?.record?.work_pattern)
  if (!pattern) return '-'
  const minutes = Number(day?.record?.work_minutes)
  if (Number.isFinite(minutes)) return `${pattern.pattern_name}（${minutes}分）`
  return pattern.pattern_name
}

const getDayPatternTime = (day) => {
  const pattern = getWorkPatternById(day?.record?.work_pattern)
  if (!pattern?.start_time || !pattern?.end_time) return '-'
  return `${pattern.start_time} - ${pattern.end_time}`
}

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
      const fallbackWorking = cursor.getDay() !== 0 && cursor.getDay() !== 6
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

const fetchCalendars = async () => {
  try {
    const response = await api.calendars.getCalendars()
    calendars.value = response.data.results || response.data || []
    if (detailCalendar.value) {
      const found = calendars.value.find((c) => c.id === detailCalendar.value.id)
      if (found) detailCalendar.value = found
    }
  } catch (error) {
    console.error('カレンダ取得エラー:', error)
    alert('カレンダデータの取得に失敗しました')
  }
}

const fetchWorkPatterns = async () => {
  try {
    const response = await api.workPatterns.getWorkPatterns()
    workPatterns.value = response.data.results || response.data || []
  } catch (error) {
    console.error('勤務パターン取得エラー:', error)
    workPatterns.value = []
  }
}

const openDetail = async (calendar) => {
  detailCalendar.value = calendar
  await fetchCalendarDays(calendar.id)
}

const fetchCalendarDays = async (calendarId) => {
  if (!calendarId) {
    calendarDays.value = []
    return
  }
  detailLoading.value = true
  try {
    const { start, end } = monthRange.value
    const response = await api.calendars.getCalendarDays(calendarId, {
      page_size: 500,
      target_date__gte: ymd(start),
      target_date__lte: ymd(end),
    })
    const rows = response.data.results || response.data || []
    calendarDays.value = rows.sort((a, b) => a.target_date.localeCompare(b.target_date))
  } catch (error) {
    console.error('カレンダ日取得エラー:', error)
    alert('カレンダ日データの取得に失敗しました')
  } finally {
    detailLoading.value = false
  }
}

const reloadCurrent = async () => {
  if (!detailCalendar.value) return
  await fetchCalendarDays(detailCalendar.value.id)
}

const moveMonth = async (delta) => {
  currentMonth.value = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth() + delta, 1)
  await reloadCurrent()
}

const toggleDay = async (day) => {
  if (!day?.inMonth || !detailCalendar.value) return
  savingDateKey.value = day.date
  try {
    const nextWorking = !day.is_working_day
    if (day.record?.id) {
      await api.calendars.updateCalendarDay(day.record.id, {
        calendar: detailCalendar.value.id,
        target_date: day.date,
        is_working_day: nextWorking,
        work_minutes: nextWorking ? (day.record.work_minutes ?? 480) : 0,
        work_pattern: day.record.work_pattern || null,
        note: day.record.note || null,
      })
    } else {
      await api.calendars.createCalendarDay({
        calendar: detailCalendar.value.id,
        target_date: day.date,
        is_working_day: nextWorking,
        work_minutes: nextWorking ? 480 : 0,
        work_pattern: null,
        note: null,
      })
    }
    await reloadCurrent()
  } catch (error) {
    console.error('カレンダ日更新エラー:', error)
    alert('日付の更新に失敗しました')
  } finally {
    savingDateKey.value = ''
  }
}

const saveDayNote = async (day, event) => {
  if (!day?.inMonth || !detailCalendar.value) return
  const note = String(event?.target?.value || '').trim()
  const current = String(day.record?.note || '').trim()
  if (note === current) return

  savingNoteDateKey.value = day.date
  try {
    if (day.record?.id) {
      await api.calendars.updateCalendarDay(day.record.id, {
        calendar: detailCalendar.value.id,
        target_date: day.date,
        is_working_day: day.is_working_day,
        work_minutes: day.is_working_day ? (day.record.work_minutes ?? 480) : 0,
        work_pattern: day.record.work_pattern || null,
        note: note || null,
      })
    } else {
      await api.calendars.createCalendarDay({
        calendar: detailCalendar.value.id,
        target_date: day.date,
        is_working_day: day.is_working_day,
        work_minutes: day.is_working_day ? 480 : 0,
        work_pattern: null,
        note: note || null,
      })
    }
    await reloadCurrent()
  } catch (error) {
    console.error('メモ保存エラー:', error)
    alert('メモ保存に失敗しました')
  } finally {
    savingNoteDateKey.value = ''
  }
}

const showNewDialog = () => {
  isEdit.value = false
  formData.value = {
    calendar_code: '',
    calendar_name: '',
    description: ''
  }
  showDialog.value = true
}

const editCalendar = (calendar) => {
  isEdit.value = true
  formData.value = { ...calendar }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveCalendar = async () => {
  try {
    if (isEdit.value) {
      await api.calendars.updateCalendar(formData.value.id, formData.value)
      alert('更新しました')
    } else {
      await api.calendars.createCalendar(formData.value)
      alert('作成しました')
    }
    await fetchCalendars()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteCalendar = async (id) => {
  if (!confirm('本当に削除しますか？')) return
  try {
    await api.calendars.deleteCalendar(id)
    if (detailCalendar.value?.id === id) {
      detailCalendar.value = null
      calendarDays.value = []
    }
    await fetchCalendars()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(async () => {
  await Promise.all([fetchCalendars(), fetchWorkPatterns()])
})
</script>

<style scoped>
.page {
  padding: 12px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.page-title {
  margin: 0;
  font-size: 24px;
}

.page-actions {
  display: flex;
  gap: 8px;
}

.main-layout {
  display: grid;
  grid-template-columns: 460px 1fr;
  gap: 12px;
  align-items: start;
}

.section {
  border: 1px solid #d7dce7;
  border-radius: 8px;
  padding: 10px;
  background: #fff;
}

.card-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 8px;
}

.hint {
  font-size: 13px;
  color: #64748b;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  border: 1px solid #d7dce7;
  padding: 6px;
}

.data-table tbody tr {
  cursor: pointer;
}

.data-table tbody tr.selected {
  background: #e8eefc;
}

.actions-inline {
  display: flex;
  gap: 6px;
}

.table-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
}

.table-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.month-title {
  min-width: 130px;
  text-align: center;
  font-weight: 700;
  font-size: 26px;
}

.calendar-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.calendar-table th,
.calendar-table td {
  border: 1px solid #c7d0e0;
  vertical-align: top;
}

.calendar-table th {
  background: #eef2f8;
  padding: 4px;
  text-align: center;
}

.day-wrap {
  min-height: 110px;
  padding: 4px;
}

.day-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.day-num {
  font-size: 38px;
  font-weight: 700;
  line-height: 1;
}

.day-check {
  font-weight: 700;
  color: #1e3a8a;
}

.day-check.holiday {
  color: #dc2626;
}

.day-pattern {
  color: #1e3a8a;
  font-weight: 600;
}

.day-time {
  color: #334155;
  font-size: 14px;
}

.note-input {
  width: 100%;
  min-height: 28px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 12px;
  padding: 3px;
  box-sizing: border-box;
}

.day-out {
  color: #94a3b8;
  font-size: 38px;
  font-weight: 700;
}

td.work {
  background: #eaf6f2;
}

td.holiday {
  background: #f8ecec;
}

td.out {
  background: #f1f5f9;
}

.empty {
  padding: 10px;
  color: #64748b;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  width: min(640px, 90vw);
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  box-sizing: border-box;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn,
.btn-sm {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
}

.btn {
  padding: 6px 10px;
}

.btn-sm {
  padding: 4px 8px;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.btn-danger {
  background: #dc2626;
  color: #fff;
  border-color: #dc2626;
}

@media (max-width: 1200px) {
  .main-layout {
    grid-template-columns: 1fr;
  }
}
</style>
