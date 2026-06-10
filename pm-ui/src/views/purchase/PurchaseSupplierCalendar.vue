<template>
  <div class="page">
    <div class="header-row">
      <div class="title-wrap">
        <h2 class="page-title">仕入れ先カレンダ <DataSourceDialog title="" :sources="dsSources" /></h2>
        <div class="title-note">注意事項：未設定日はダイソウカレンダの稼働日を既定値として表示します</div>
      </div>
      <button class="btn primary" @click="showCreate = !showCreate" :disabled="!canEdit">
        {{ showCreate ? '新規作成を閉じる' : '新規作成' }}
      </button>
    </div>

    <div class="section">
      <div class="toolbar">
        <div class="field inline-field">
          <label>仕入れ先</label>
          <select v-model.number="selectedSupplierId" @change="onSupplierChange">
            <option value="">未選択</option>
            <option v-for="s in suppliers" :key="s.id" :value="s.id">
              {{ s.supplier_code }} - {{ s.supplier_name }}
            </option>
          </select>
        </div>
        <div class="field inline-field">
          <label>カレンダ</label>
          <select v-model.number="selectedCalendarId" :disabled="!selectedSupplierId" @change="onCalendarChange">
            <option value="">未割当</option>
            <option v-for="c in supplierAssignableCalendars" :key="c.id" :value="c.id">
              {{ c.calendar_code }} - {{ c.calendar_name }}
            </option>
          </select>
          <button
            class="btn primary"
            @click="assignCalendar"
            :disabled="!selectedSupplierId || !selectedCalendarId || assigning || !canEdit"
          >
            割当
          </button>
          <button
            class="btn"
            @click="unassignCalendar"
            :disabled="!selectedSupplierId || !currentLineCalendarId || assigning || !canEdit"
          >
            割当解除
          </button>
        </div>
        <div class="field inline-field">
          <label>コピー</label>
          <select v-model.number="copySourceCalendarId" :disabled="!selectedCalendarId || copying || !canEdit">
            <option value="">コピー元を選択</option>
            <option
              v-for="c in copySourceCandidates"
              :key="c.id"
              :value="c.id"
            >
              {{ c.calendar_code }} - {{ c.calendar_name }}
            </option>
          </select>
          <input type="date" v-model="copyStartDate" :disabled="!selectedCalendarId || copying || !canEdit" />
          <span>〜</span>
          <input type="date" v-model="copyEndDate" :disabled="!selectedCalendarId || copying || !canEdit" />
          <button
            class="btn"
            @click="copyCalendarDays"
            :disabled="!selectedCalendarId || !copySourceCalendarId || !copyStartDate || !copyEndDate || copying || !canEdit"
          >
            {{ copying ? 'コピー中...' : 'コピー実行' }}
          </button>
        </div>
      </div>
    </div>

    <div class="section" v-if="showCreate">
      <div class="create-grid">
        <div class="field">
          <label>カレンダコード</label>
          <input v-model.trim="newCalendar.code" placeholder="例: sup_A001" />
        </div>
        <div class="field">
          <label>カレンダ名</label>
          <input v-model.trim="newCalendar.name" placeholder="例: A社カレンダ" />
        </div>
        <div class="field action-field">
          <label>&nbsp;</label>
          <button class="btn primary" @click="createAndAssignCalendar" :disabled="creating || !canEdit">
            作成して割当
          </button>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="calendar-controls">
        <div></div>
        <div class="month-head">
          <button class="btn" @click="moveMonth(-1)" :disabled="!selectedCalendarId">前月へ</button>
          <div class="month-title">{{ monthTitle }}</div>
          <button class="btn" @click="moveMonth(1)" :disabled="!selectedCalendarId">次月へ</button>
        </div>
        <div class="weekday-bulk"></div>
      </div>

      <div v-if="!selectedCalendarId" class="empty">
        仕入れ先を選択してください。
      </div>

      <table v-else class="calendar-table">
        <thead>
          <tr>
            <th v-for="(name, idx) in weekdayNames" :key="name">
              <label class="weekday-check">
                <span>{{ name }}</span>
                <input
                  type="checkbox"
                  v-model="weekdayChecks[idx]"
                  :disabled="!selectedCalendarId || applyingWeekday || !canEdit"
                  @change="toggleWeekday(idx, $event.target.checked)"
                />
              </label>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(week, idx) in monthWeeks" :key="idx">
            <td v-for="day in week" :key="day.key" :class="cellClass(day)">
              <div class="day-cell-btn">
                <div class="day-main">
                  <div class="day-num">{{ day.day }}</div>
                  <label
                    v-if="day.inMonth"
                    class="day-check"
                    :class="{ holiday: !day.is_working_day }"
                  >
                    <input
                      type="checkbox"
                      :checked="day.is_working_day"
                      :disabled="savingDateKey === day.date || !canEdit"
                      @change="toggleDay(day)"
                    />
                    {{ day.is_working_day ? '稼働中' : '休み' }}
                  </label>
                </div>
                <div class="day-memo">
                  <textarea
                    v-if="day.inMonth"
                    class="note-input"
                    :value="day.record?.note || ''"
                    placeholder="メモ"
                    :disabled="savingDateKey === day.date || savingNoteDateKey === day.date || !canEdit"
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
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: 'カレンダー 読み書き', table: 'm_calendar', desc: 'カレンダーマスタ（新規作成・一覧）' },
  { op: 'カレンダー日 読み書き', table: 'm_calendar_day', desc: '日別の稼働/休日設定・メモ' },
  { op: 'ライン 読み書き', table: 'm_line', desc: '購買ライン（カレンダー割当先）' },
  { op: '仕入先 読み取り', table: 'm_supplier', desc: '仕入先マスタ' },
]

const canEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const entry = permissions.find((item) => item.resource === 'purchase.supplier_calendar')
  if (entry) return Boolean(entry.can_edit)
  return hasPermission(user, 'purchase', 'edit')
})

const suppliers = ref([])
const lines = ref([])
const calendars = ref([])
const calendarDays = ref([])
const daisoCalendarId = ref('')
const daisoCalendarDays = ref([])

const selectedSupplierId = ref('')
const selectedCalendarId = ref('')
const showCreate = ref(false)
const creating = ref(false)
const assigning = ref(false)
const currentLineCalendarId = ref('')
const savingDateKey = ref('')
const applyingWeekday = ref(false)
const savingNoteDateKey = ref('')
const copySourceCalendarId = ref('')
const copyStartDate = ref('')
const copyEndDate = ref('')
const copying = ref(false)
const weekdayNames = ['日', '月', '火', '水', '木', '金', '土']
const weekdayChecks = ref([false, false, false, false, false, false, false])

const currentMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))

const newCalendar = ref({
  code: '',
  name: '',
})

const ymd = (dateObj) => {
  const y = dateObj.getFullYear()
  const m = String(dateObj.getMonth() + 1).padStart(2, '0')
  const d = String(dateObj.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const formatMonth = (dateObj) => {
  const y = dateObj.getFullYear()
  const m = String(dateObj.getMonth() + 1)
  return `${y}年${m}月`
}

const monthTitle = computed(() => formatMonth(currentMonth.value))

const monthRange = computed(() => {
  const start = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth(), 1)
  const end = new Date(currentMonth.value.getFullYear(), currentMonth.value.getMonth() + 1, 0)
  return { start, end }
})

const dayMap = computed(() => {
  const map = new Map()
  for (const row of calendarDays.value) {
    map.set(row.target_date, row)
  }
  return map
})

const copySourceCandidates = computed(() => calendars.value)
const supplierAssignableCalendars = computed(() =>
  calendars.value.filter((c) => c?.is_supplier_assignable !== false),
)

const daisoDayMap = computed(() => {
  const map = new Map()
  for (const row of daisoCalendarDays.value) {
    map.set(row.target_date, row)
  }
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

const loadSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = res.data.results || res.data || []
}

const loadLines = async () => {
  const res = await api.lines.getLines({ page_size: 500 })
  lines.value = (res.data.results || res.data || []).filter((x) => x.line_type === 'PURCHASE')
}

const loadCalendars = async () => {
  const res = await api.calendars.getCalendars({ page_size: 500 })
  calendars.value = res.data.results || res.data || []
}

const supplierToLine = (supplierId) => {
  const supplier = suppliers.value.find((x) => x.id === supplierId)
  if (!supplier) return null
  return lines.value.find((l) => l.line_code === supplier.supplier_code) || null
}

const onCalendarChange = async () => {
  copySourceCalendarId.value = ''
  await loadCalendarDays()
}

const onSupplierChange = async () => {
  const line = supplierToLine(selectedSupplierId.value)
  const nextCalendarId = line?.calendar || ''
  selectedCalendarId.value = supplierAssignableCalendars.value.some((c) => c.id === nextCalendarId) ? nextCalendarId : ''
  currentLineCalendarId.value = line?.calendar || ''
  await Promise.all([loadCalendarDays(), loadDaisoCalendarDays()])
}

const loadCalendarDays = async () => {
  if (!selectedCalendarId.value) {
    calendarDays.value = []
    return
  }
  const { start, end } = monthRange.value
  const res = await api.calendars.getCalendarDays(selectedCalendarId.value, {
    page_size: 500,
    target_date__gte: ymd(start),
    target_date__lte: ymd(end),
  })
  calendarDays.value = res.data.results || res.data || []
}

const loadDaisoCalendarDays = async () => {
  const { start, end } = monthRange.value
  if (!daisoCalendarId.value) {
    const res = await api.calendars.getCalendars({ search: 'daiso', page_size: 200 })
    const rows = res.data.results || res.data || []
    const found = rows.find((row) => String(row.calendar_code || '').toLowerCase() === 'daiso')
    daisoCalendarId.value = found?.id || ''
  }
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
  const { start, end } = monthRange.value
  copyStartDate.value = ymd(start)
  copyEndDate.value = ymd(end)
  await Promise.all([loadCalendarDays(), loadDaisoCalendarDays()])
}

const copyCalendarDays = async () => {
  if (!canEdit.value) return
  if (!selectedCalendarId.value || !copySourceCalendarId.value || !copyStartDate.value || !copyEndDate.value) return
  if (copyStartDate.value > copyEndDate.value) {
    alert('コピー期間の開始日と終了日を確認してください。')
    return
  }
  if (String(copySourceCalendarId.value) === String(selectedCalendarId.value)) {
    alert('同じカレンダ同士はコピーできません。')
    return
  }

  const src = calendars.value.find((c) => String(c.id) === String(copySourceCalendarId.value))
  const dst = calendars.value.find((c) => String(c.id) === String(selectedCalendarId.value))
  const srcLabel = src ? `${src.calendar_code} - ${src.calendar_name}` : `ID:${copySourceCalendarId.value}`
  const dstLabel = dst ? `${dst.calendar_code} - ${dst.calendar_name}` : `ID:${selectedCalendarId.value}`
  if (!confirm(`「${srcLabel}」から「${dstLabel}」へ ${copyStartDate.value}〜${copyEndDate.value} をコピーします。実行しますか？`)) return

  copying.value = true
  try {
    const res = await api.calendars.copyCalendar(copySourceCalendarId.value, {
      target_calendar_id: selectedCalendarId.value,
      start_date: copyStartDate.value,
      end_date: copyEndDate.value,
    })
    await loadCalendarDays()
    alert(`コピーが完了しました。（${res.data?.copied ?? 0}件）`)
  } catch (e) {
    console.error('カレンダコピーエラー', e)
    alert('コピーに失敗しました。')
  } finally {
    copying.value = false
  }
}

const toggleWeekday = async (weekday, checked) => {
  if (!canEdit.value) return
  if (!selectedCalendarId.value) return
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
            calendar: selectedCalendarId.value,
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
            calendar: selectedCalendarId.value,
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

const createAndAssignCalendar = async () => {
  if (!canEdit.value) return
  if (!selectedSupplierId.value) {
    alert('先に仕入れ先を選択してください。')
    return
  }
  if (!newCalendar.value.code || !newCalendar.value.name) {
    alert('カレンダコードとカレンダ名を入力してください。')
    return
  }
  const line = supplierToLine(selectedSupplierId.value)
  if (!line) {
    alert('仕入れ先に対応する購買ラインが見つかりません。')
    return
  }

  creating.value = true
  try {
    const calRes = await api.calendars.createCalendar({
      calendar_code: newCalendar.value.code,
      calendar_name: newCalendar.value.name,
      calendar_type: 'SUPPLIER',
    })
    const calendar = calRes.data
    await api.lines.patchLine(line.id, { calendar: calendar.id })

    await loadCalendars()
    await loadLines()
    selectedCalendarId.value = calendar.id
    currentLineCalendarId.value = calendar.id
    newCalendar.value = { code: '', name: '' }
    showCreate.value = false
    await loadCalendarDays()
    alert('カレンダを作成し、仕入れ先へ割当しました。')
  } catch (e) {
    console.error('仕入れ先カレンダ作成エラー', e)
    alert('作成または割当に失敗しました。')
  } finally {
    creating.value = false
  }
}

const assignCalendar = async () => {
  if (!canEdit.value) return
  if (!selectedSupplierId.value || !selectedCalendarId.value) return
  const line = supplierToLine(selectedSupplierId.value)
  if (!line) {
    alert('仕入れ先に対応する購買ラインが見つかりません。')
    return
  }
  if (line.calendar === selectedCalendarId.value) {
    alert('既に同じカレンダが割当されています。')
    return
  }
  const cal = calendars.value.find((c) => c.id === selectedCalendarId.value)
  const calLabel = cal ? `${cal.calendar_code} - ${cal.calendar_name}` : ''
  if (!confirm(`「${calLabel}」をこの仕入れ先に割り当てますか？`)) return

  assigning.value = true
  try {
    await api.lines.patchLine(line.id, { calendar: selectedCalendarId.value })
    await loadLines()
    currentLineCalendarId.value = selectedCalendarId.value
    await loadCalendarDays()
    alert('カレンダを割り当てました。')
  } catch (e) {
    console.error('カレンダ割当エラー', e)
    alert('割当に失敗しました。')
  } finally {
    assigning.value = false
  }
}

const unassignCalendar = async () => {
  if (!canEdit.value) return
  if (!selectedSupplierId.value) return
  const line = supplierToLine(selectedSupplierId.value)
  if (!line) return
  if (!confirm('カレンダの割当を解除しますか？ダイソウカレンダが既定値として使用されます。')) return

  assigning.value = true
  try {
    await api.lines.patchLine(line.id, { calendar: null })
    await loadLines()
    selectedCalendarId.value = ''
    currentLineCalendarId.value = ''
    calendarDays.value = []
    alert('割当を解除しました。')
  } catch (e) {
    console.error('カレンダ割当解除エラー', e)
    alert('割当解除に失敗しました。')
  } finally {
    assigning.value = false
  }
}

const toggleDay = async (day) => {
  if (!canEdit.value) return
  if (!day?.inMonth || !selectedCalendarId.value) return
  savingDateKey.value = day.date
  try {
    const nextWorking = !day.is_working_day
    if (day.record?.id) {
      await api.calendars.updateCalendarDay(day.record.id, {
        calendar: selectedCalendarId.value,
        target_date: day.date,
        is_working_day: nextWorking,
        work_minutes: nextWorking ? (day.record.work_minutes ?? 480) : 0,
        work_pattern: day.record.work_pattern || null,
      })
    } else {
      await api.calendars.createCalendarDay({
        calendar: selectedCalendarId.value,
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
  if (!day?.inMonth || !selectedCalendarId.value) return
  const inputNote = String(event?.target?.value || '').trim()
  const currentNote = String(day.record?.note || '').trim()
  if (inputNote === currentNote) return

  savingNoteDateKey.value = day.date
  try {
    if (day.record?.id) {
      await api.calendars.updateCalendarDay(day.record.id, {
        calendar: selectedCalendarId.value,
        target_date: day.date,
        is_working_day: day.is_working_day,
        work_minutes: day.is_working_day ? (day.record.work_minutes ?? 480) : 0,
        work_pattern: day.record.work_pattern || null,
        note: inputNote || null,
      })
    } else {
      await api.calendars.createCalendarDay({
        calendar: selectedCalendarId.value,
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
  await Promise.all([loadSuppliers(), loadLines(), loadCalendars()])
  const { start, end } = monthRange.value
  copyStartDate.value = ymd(start)
  copyEndDate.value = ymd(end)
  await loadDaisoCalendarDays()
})
</script>

<style scoped>
.page {
  padding: 12px;
}
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.title-wrap {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.page-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.title-note {
  font-size: 13px;
  color: #b91c1c;
  font-weight: 700;
}
.section {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  background: #fff;
  margin-bottom: 12px;
}
.toolbar {
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
.inline-field {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}
.field input,
.field select {
  min-width: 280px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.create-grid {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.action-field .btn {
  min-width: 140px;
}
.calendar-label {
  font-size: 13px;
  color: #334155;
}
.calendar-controls {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.month-head {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.weekday-bulk {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}
.month-title {
  font-size: 16px;
  font-weight: 700;
  min-width: 140px;
  text-align: center;
}
.calendar-table {
  width: 100%;
  max-width: 1500px;
  margin: 0 auto;
  border-collapse: collapse;
}
.calendar-table th,
.calendar-table td {
  border: 1px solid #e2e8f0;
  width: calc(100% / 7);
  vertical-align: top;
  padding: 0;
}
.calendar-table th {
  background: #f8fafc;
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
  min-height: 130px;
  cursor: default;
  padding: 6px;
  display: grid;
  grid-template-columns: 1fr 3fr;
  gap: 8px;
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
  font-size: 12px;
}
.day-check.holiday {
  color: #ff0000;
  font-weight: 700;
}
.day-num {
  font-size: 24px;
  font-weight: 700;
  line-height: 1;
}
.day-memo {
  display: flex;
  align-items: stretch;
}
.note-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 6px 8px;
  height: 100%;
  min-height: 118px;
  font-size: 12px;
  line-height: 1.2;
  resize: vertical;
}
td.work .day-cell-btn {
  background: #ecfdf5;
}
td.holiday .day-cell-btn {
  background: #fef2f2;
}
td.out .day-cell-btn {
  background: #f8fafc;
  color: #94a3b8;
  cursor: default;
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
}
.empty {
  color: #94a3b8;
  padding: 10px;
}
</style>
