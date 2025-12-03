<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">工程マスタ</h1>
      <div class="page-actions">
        <button @click="fetchProcesses" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>工程コード</th>
            <th>工程名</th>
            <th>外注工程</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="process in processes" :key="process.id">
            <td>{{ process.process_code }}</td>
            <td>{{ process.process_name }}</td>
            <td>{{ process.is_outsource ? '外注' : '社内' }}</td>
            <td>{{ process.is_active ? '有効' : '無効' }}</td>
            <td>
              <button @click="editProcess(process)" class="btn-sm">編集</button>
              <button @click="deleteProcess(process.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="processes.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '工程編集' : '工程新規作成' }}</h2>
        <form @submit.prevent="saveProcess">
          <div class="form-group">
            <label>工程コード *</label>
            <input v-model="formData.process_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>工程名 *</label>
            <input v-model="formData.process_name" required />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_outsource" />
              外注工程
            </label>
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

const processes = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  process_code: '',
  process_name: '',
  is_outsource: false,
  is_active: true
})

const fetchProcesses = async () => {
  try {
    const response = await api.getProcesses()
    processes.value = response.data.results || response.data
  } catch (error) {
    console.error('工程取得エラー:', error)
    alert('工程データの取得に失敗しました')
  }
}

const showNewDialog = () => {
  isEdit.value = false
  formData.value = {
    process_code: '',
    process_name: '',
    is_outsource: false,
    is_active: true
  }
  showDialog.value = true
}

const editProcess = (process) => {
  isEdit.value = true
  formData.value = { ...process }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveProcess = async () => {
  try {
    if (isEdit.value) {
      await api.updateProcess(formData.value.id, formData.value)
      alert('更新しました')
    } else {
      await api.createProcess(formData.value)
      alert('作成しました')
    }
    await fetchProcesses()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteProcess = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.deleteProcess(id)
    await fetchProcesses()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchProcesses()
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
