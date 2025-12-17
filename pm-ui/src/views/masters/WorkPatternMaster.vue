<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">勤務パターンマスタ</h1>
      <div class="page-actions">
        <button @click="fetchPatterns" class="btn-primary">更新</button>
        <button @click="toggleForm" class="btn-success">{{ showForm ? 'フォームを閉じる' : '新規作成' }}</button>
      </div>
    </div>

    <!-- 新規/編集フォーム -->
    <div v-if="showForm" class="form-section">
      <h2 class="form-title">{{ isEdit ? '勤務パターン編集' : '勤務パターン新規作成' }}</h2>
      <form @submit.prevent="savePattern" class="pattern-form">
        <div class="form-row">
          <div class="form-group">
            <label>パターンコード *</label>
            <input v-model="formData.pattern_code" required :disabled="isEdit" class="form-input" />
          </div>
          <div class="form-group">
            <label>パターン名 *</label>
            <input v-model="formData.pattern_name" required class="form-input" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>開始時刻 *</label>
            <input type="time" v-model="formData.start_time" required class="form-input" />
          </div>
          <div class="form-group">
            <label>勤務時間（分） *</label>
            <input type="number" v-model.number="formData.work_minutes" required min="0" class="form-input" />
            <small class="help-text">例: 1090分 = 18時間10分（8:00〜翌2:10）</small>
          </div>
          <div class="form-group">
            <label>休憩時間（分）</label>
            <input type="number" v-model.number="formData.break_minutes" min="0" class="form-input" />
          </div>
        </div>
        <div class="form-group">
          <label>説明</label>
          <textarea v-model="formData.description" rows="3" class="form-input"></textarea>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn-primary">保存</button>
          <button type="button" @click="cancelEdit" class="btn-secondary">キャンセル</button>
        </div>
      </form>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>パターンコード</th>
            <th>パターン名</th>
            <th>開始時刻</th>
            <th>勤務時間</th>
            <th>休憩時間</th>
            <th>説明</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pattern in patterns" :key="pattern.id">
            <td>{{ pattern.pattern_code }}</td>
            <td>{{ pattern.pattern_name }}</td>
            <td>{{ pattern.start_time }}</td>
            <td>{{ formatMinutes(pattern.work_minutes) }}</td>
            <td>{{ formatMinutes(pattern.break_minutes) }}</td>
            <td>{{ pattern.description }}</td>
            <td>
              <button @click="editPattern(pattern)" class="btn-sm">編集</button>
              <button @click="deletePattern(pattern.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="patterns.length === 0" class="no-data">
        データがありません
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const patterns = ref([])
const showForm = ref(false)
const isEdit = ref(false)
const formData = ref({
  pattern_code: '',
  pattern_name: '',
  start_time: '',
  work_minutes: 0,
  break_minutes: 0,
  description: ''
})

const formatMinutes = (minutes) => {
  if (!minutes && minutes !== 0) return '-'
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours}時間${mins}分 (${minutes}分)`
}

const fetchPatterns = async () => {
  try {
    const response = await api.workPatterns.getWorkPatterns()
    patterns.value = response.data.results || response.data
  } catch (error) {
    console.error('勤務パターン取得エラー:', error)
    alert('勤務パターンデータの取得に失敗しました')
  }
}

const toggleForm = () => {
  if (showForm.value) {
    showForm.value = false
    isEdit.value = false
  } else {
    isEdit.value = false
    formData.value = {
      pattern_code: '',
      pattern_name: '',
      start_time: '',
      work_minutes: 0,
      break_minutes: 0,
      description: ''
    }
    showForm.value = true
  }
}

const editPattern = (pattern) => {
  isEdit.value = true
  formData.value = { ...pattern }
  showForm.value = true
}

const cancelEdit = () => {
  showForm.value = false
  isEdit.value = false
}

const savePattern = async () => {
  try {
    if (isEdit.value) {
      await api.workPatterns.updateWorkPattern(formData.value.id, formData.value)
      alert('更新しました')
    } else {
      await api.workPatterns.createWorkPattern(formData.value)
      alert('作成しました')
    }
    await fetchPatterns()
    showForm.value = false
    isEdit.value = false
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deletePattern = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.workPatterns.deleteWorkPattern(id)
    await fetchPatterns()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchPatterns()
})
</script>

<style scoped>
.form-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.form-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: #1e293b;
}

.pattern-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #475569;
}

.form-input {
  padding: 0.5rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 0.875rem;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-input:disabled {
  background: #f1f5f9;
  color: #94a3b8;
  cursor: not-allowed;
}

.help-text {
  display: block;
  color: #64748b;
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}
</style>
