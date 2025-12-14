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
          <tr v-for="calendar in calendars" :key="calendar.id">
            <td>{{ calendar.calendar_code }}</td>
            <td>{{ calendar.calendar_name }}</td>
            <td>{{ calendar.description }}</td>
            <td>
              <button @click="editCalendar(calendar)" class="btn-sm">編集</button>
              <button @click="deleteCalendar(calendar.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="calendars.length === 0" class="no-data">
        データがありません
      </div>
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
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const calendars = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  calendar_code: '',
  calendar_name: '',
  description: ''
})

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
