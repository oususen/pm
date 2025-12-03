<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">ラインマスタ</h1>
      <div class="page-actions">
        <button @click="fetchLines" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>ラインコード</th>
            <th>ライン名</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="line in lines" :key="line.id">
            <td>{{ line.line_code }}</td>
            <td>{{ line.line_name }}</td>
            <td>{{ line.is_active ? '有効' : '無効' }}</td>
            <td>
              <button @click="editLine(line)" class="btn-sm">編集</button>
              <button @click="deleteLine(line.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="lines.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? 'ライン編集' : 'ライン新規作成' }}</h2>
        <form @submit.prevent="saveLine">
          <div class="form-group">
            <label>ラインコード *</label>
            <input v-model="formData.line_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>ライン名 *</label>
            <input v-model="formData.line_name" required />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" />
              有効
            </label>
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
import api from '../api/client'

const lines = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  line_code: '',
  line_name: '',
  is_active: true
})

const fetchLines = async () => {
  try {
    const response = await api.lines.getLines()
    lines.value = response.data.results || response.data
  } catch (error) {
    console.error('ライン取得エラー:', error)
    alert('ラインデータの取得に失敗しました')
  }
}

const showNewDialog = () => {
  isEdit.value = false
  formData.value = {
    line_code: '',
    line_name: '',
    is_active: true
  }
  showDialog.value = true
}

const editLine = (line) => {
  isEdit.value = true
  formData.value = { ...line }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveLine = async () => {
  try {
    if (isEdit.value) {
      await api.lines.updateLine(formData.value.id, formData.value)
      alert('更新しました')
    } else {
      await api.lines.createLine(formData.value)
      alert('作成しました')
    }
    await fetchLines()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteLine = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.lines.deleteLine(id)
    await fetchLines()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchLines()
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

.form-group input[type="text"] {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input[type="checkbox"] {
  margin-right: 0.5rem;
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
