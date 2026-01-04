<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">カレンダマスタ</h1>
      <div class="page-actions">
        <button @click="fetchCalendars" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>カレンダコード</th>
            <th>カレンダ名</th>
            <th>説明</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="calendar in calendars"
            :key="calendar.id"
            class="calendar-row"
            :class="{ selected: detailCalendar && detailCalendar.id === calendar.id }"
            @click="openDetail(calendar)"
          >
            <td>{{ calendar.calendar_code }}</td>
            <td>{{ calendar.calendar_name }}</td>
            <td>{{ calendar.description }}</td>
            <td>
              <button @click.stop="editCalendar(calendar)" class="btn-sm">編集</button>
              <button @click.stop="deleteCalendar(calendar.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="calendars.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <div v-if="detailCalendar" class="detail-panel">
      <div class="detail-header">
        <div>
          <h2 class="detail-title">カレンダ詳細</h2>
          <div class="detail-hint">
            対象: {{ detailCalendar.calendar_code }} - {{ detailCalendar.calendar_name }}
          </div>
        </div>
        <div class="detail-actions">
          <button class="btn-sm" @click="fetchCalendarDays(detailCalendar.id)">再読込</button>
          <button class="btn-sm btn-secondary" @click="closeDetail">閉じる</button>
        </div>
      </div>
      <div class="detail-filters">
        <label>開始</label>
        <input type="date" v-model="detailStart" />
        <label>終了</label>
        <input type="date" v-model="detailEnd" />
      </div>
      <div v-if="detailLoading" class="detail-loading">読込中...</div>
      <div v-else-if="visibleDetailDays.length" class="detail-table-wrap">
        <table class="data-table">
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
            <tr v-for="day in visibleDetailDays" :key="day.id">
              <td>{{ day.target_date }}</td>
              <td>{{ formatWeekday(day.target_date) }}</td>
              <td>{{ day.is_working_day ? '○' : '×' }}</td>
              <td class="num">{{ day.work_minutes ?? '' }}</td>
              <td>{{ day.work_pattern_name ?? '' }}</td>
              <td class="actions-inline">
                <button class="btn-sm" @click="setHoliday(day)" :disabled="updatingDayId === day.id">
                  休日にする
                </button>
                <button class="btn-sm btn-secondary" @click="setWorkingDay(day)" :disabled="updatingDayId === day.id">
                  稼働日にする
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="no-data">カレンダ日データがありません</div>
    </div>

    <!-- 新規/編集ダイアログ -->
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
            <button type="submit" class="btn-primary">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/api/client'

const calendars = ref([])
const calendarDays = ref([])
const detailCalendar = ref(null)
const detailLoading = ref(false)
const updatingDayId = ref(null)
const detailStart = ref('')
const detailEnd = ref('')
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  calendar_code: '',
  calendar_name: '',
  description: ''
})

const visibleDetailDays = computed(() => {
  if (!detailStart.value && !detailEnd.value) return calendarDays.value
  const start = detailStart.value ? new Date(detailStart.value) : null
  const end = detailEnd.value ? new Date(detailEnd.value) : null
  return calendarDays.value.filter((d) => {
    const dt = new Date(d.target_date)
    if (start && dt < start) return false
    if (end && dt > end) return false
    return true
  })
})

const formatWeekday = (dateStr) => {
  const w = new Date(dateStr).getDay()
  return ['日', '月', '火', '水', '木', '金', '土'][w] || ''
}

const fetchCalendars = async () => {
  try {
    const response = await api.calendars.getCalendars()
    calendars.value = response.data.results || response.data
  } catch (error) {
    console.error('カレンダ取得エラー:', error)
    alert('カレンダデータの取得に失敗しました')
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

const openDetail = async (calendar) => {
  detailCalendar.value = calendar
  calendarDays.value = []
  detailStart.value = ''
  detailEnd.value = ''
  await fetchCalendarDays(calendar.id)
}

const closeDetail = () => {
  detailCalendar.value = null
  calendarDays.value = []
  detailStart.value = ''
  detailEnd.value = ''
}

const fetchCalendarDays = async (calendarId) => {
  if (!calendarId) {
    calendarDays.value = []
    return
  }
  detailLoading.value = true
  try {
    const response = await api.calendars.getCalendarDays(calendarId)
    const rows = response.data.results || response.data || []
    calendarDays.value = rows.sort((a, b) => a.target_date.localeCompare(b.target_date))
  } catch (error) {
    console.error('カレンダ日取得エラー:', error)
    alert('カレンダ日データの取得に失敗しました')
  } finally {
    detailLoading.value = false
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
    await fetchCalendarDays(detailCalendar.value?.id)
  } catch (error) {
    console.error('休日設定エラー:', error)
    alert('休日設定に失敗しました')
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
      work_minutes: (day.work_minutes ?? 480),
      work_pattern: day.work_pattern ?? null,
    })
    await fetchCalendarDays(detailCalendar.value?.id)
  } catch (error) {
    console.error('稼働日設定エラー:', error)
    alert('稼働日設定に失敗しました')
  } finally {
    updatingDayId.value = null
  }
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
    await fetchCalendars()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchCalendars()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  min-width: 500px;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
}

.calendar-row {
  cursor: pointer;
}

.calendar-row:hover {
  background-color: #f5f7ff;
}

.calendar-row.selected {
  background-color: #eef2ff;
}

.detail-panel {
  margin-top: 16px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.detail-title {
  margin: 0 0 4px;
  font-size: 16px;
}

.detail-hint {
  color: #6b7280;
  font-size: 12px;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.detail-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
  flex-wrap: wrap;
}

.detail-filters input[type="date"] {
  padding: 4px 6px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.detail-loading {
  padding: 8px 0;
  color: #6b7280;
}

.detail-table-wrap {
  max-height: 360px;
  overflow: auto;
}

.num {
  text-align: right;
}

.actions-inline {
  display: flex;
  gap: 6px;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

.form-group input[type="text"],
.form-group textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  font-family: inherit;
}

.form-actions {
  margin-top: 1.5rem;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background-color: white;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover {
  background-color: #f5f5f5;
}
</style>
