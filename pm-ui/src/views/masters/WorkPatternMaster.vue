<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">勤務パターンマスタ</h1>
      <div class="page-actions">
        <button @click="fetchPatterns" class="btn-primary">更新</button>
        <button v-if="canEdit" @click="toggleForm" class="btn-success">{{ showForm ? 'フォームを閉じる' : '新規作成' }}</button>
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
            <label>終了時刻 *</label>
            <input type="time" v-model="formData.end_time" required class="form-input" />
            <small class="help-text">例: 開始08:00、終了26:10（翌日02:10）の場合は02:10と入力</small>
          </div>
        </div>

        <!-- 休憩時間設定 -->
        <div class="break-section">
          <div class="break-header">
            <h3>休憩時間設定</h3>
            <button type="button" @click="addBreak" class="btn-secondary btn-sm" :disabled="!canEdit">休憩追加</button>
          </div>
          <div v-if="formData.break_times.length === 0" class="no-breaks">
            休憩時間が設定されていません
          </div>
          <div v-for="(breakTime, index) in formData.break_times" :key="index" class="break-item">
            <div class="break-row">
              <div class="form-group">
                <label>休憩開始 *</label>
                <input type="time" v-model="breakTime.break_start" required class="form-input" :disabled="!canEdit" />
              </div>
              <div class="form-group">
                <label>休憩終了 *</label>
                <input type="time" v-model="breakTime.break_end" required class="form-input" :disabled="!canEdit" />
              </div>
              <button type="button" @click="removeBreak(index)" class="btn-danger btn-sm" :disabled="!canEdit">削除</button>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>説明</label>
          <textarea v-model="formData.description" rows="3" class="form-input" :disabled="!canEdit"></textarea>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn-primary" :disabled="!canEdit">保存</button>
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
            <th>終了時刻</th>
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
            <td>{{ pattern.end_time }}</td>
            <td>{{ formatBreakTimes(pattern.break_times) }}</td>
            <td>{{ pattern.description }}</td>
            <td>
              <button v-if="canEdit" @click="editPattern(pattern)" class="btn-sm">編集</button>
              <button v-if="canEdit" @click="deletePattern(pattern.id)" class="btn-sm btn-danger">削除</button>
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
import { computed, ref, onMounted } from 'vue'
import api from '@/api/client'
import { canAccessMasterResource } from '@/utils/masterPermissions'

const patterns = ref([])
const showForm = ref(false)
const isEdit = ref(false)
const formData = ref({
  pattern_code: '',
  pattern_name: '',
  start_time: '',
  end_time: '',
  description: '',
  break_times: []
})
const canEdit = computed(() => canAccessMasterResource('masters.work_pattern', 'edit'))

const formatBreakTimes = (breakTimes) => {
  if (!breakTimes || breakTimes.length === 0) return 'なし'
  return breakTimes.map(bt => `${bt.break_start}〜${bt.break_end}`).join(', ')
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
  if (!canEdit.value) return
  if (showForm.value) {
    showForm.value = false
    isEdit.value = false
  } else {
    isEdit.value = false
    formData.value = {
      pattern_code: '',
      pattern_name: '',
      start_time: '',
      end_time: '',
      description: '',
      break_times: []
    }
    showForm.value = true
  }
}

const addBreak = () => {
  if (!canEdit.value) return
  formData.value.break_times.push({
    break_start: '',
    break_end: '',
    order: formData.value.break_times.length + 1
  })
}

const removeBreak = (index) => {
  if (!canEdit.value) return
  formData.value.break_times.splice(index, 1)
  // 順序を再調整
  formData.value.break_times.forEach((bt, idx) => {
    bt.order = idx + 1
  })
}

const editPattern = async (pattern) => {
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = {
    ...pattern,
    break_times: pattern.break_times ? [...pattern.break_times] : []
  }
  showForm.value = true
}

const cancelEdit = () => {
  showForm.value = false
  isEdit.value = false
}

const savePattern = async () => {
  if (!canEdit.value) return
  try {
    let patternId

    if (isEdit.value) {
      // パターン更新
      await api.workPatterns.updateWorkPattern(formData.value.id, {
        pattern_code: formData.value.pattern_code,
        pattern_name: formData.value.pattern_name,
        start_time: formData.value.start_time,
        end_time: formData.value.end_time,
        description: formData.value.description
      })
      patternId = formData.value.id

      // サーバーから既存の休憩時間をすべて取得して削除
      const existingBreaksResponse = await api.workPatterns.getBreakTimes(patternId)
      const existingBreaks = existingBreaksResponse.data.results || existingBreaksResponse.data || []
      for (const bt of existingBreaks) {
        await api.workPatterns.deleteBreakTime(bt.id)
      }
    } else {
      // パターン作成
      const res = await api.workPatterns.createWorkPattern({
        pattern_code: formData.value.pattern_code,
        pattern_name: formData.value.pattern_name,
        start_time: formData.value.start_time,
        end_time: formData.value.end_time,
        description: formData.value.description
      })
      patternId = res.data.id
    }

    // 休憩時間を作成
    for (const bt of formData.value.break_times) {
      await api.workPatterns.createBreakTime({
        work_pattern: patternId,
        break_start: bt.break_start,
        break_end: bt.break_end,
        order: bt.order
      })
    }

    alert(isEdit.value ? '更新しました' : '作成しました')
    await fetchPatterns()
    showForm.value = false
    isEdit.value = false
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deletePattern = async (id) => {
  if (!canEdit.value) return
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
  gap: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
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

.break-section {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 1rem;
  background: white;
}

.break-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.break-header h3 {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.no-breaks {
  padding: 1rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.875rem;
}

.break-item {
  margin-bottom: 0.75rem;
  padding: 0.75rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
}

.break-row {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
}

.break-row .form-group {
  flex: 1;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: white;
  cursor: pointer;
  white-space: nowrap;
}

.btn-sm:hover {
  background: #f8fafc;
}

.btn-danger {
  background: #dc2626;
  color: white;
  border-color: #dc2626;
}

.btn-danger:hover {
  background: #b91c1c;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}
</style>

