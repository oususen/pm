<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">得意先マスタ</h1>
      <div class="page-actions">
        <button @click="fetchCustomers" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>得意先コード</th>
            <th>得意先名</th>
            <th>略称</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="customer in customers" :key="customer.id">
            <td>{{ customer.customer_code }}</td>
            <td>{{ customer.customer_name }}</td>
            <td>{{ customer.short_name }}</td>
            <td>{{ customer.is_active ? '有効' : '無効' }}</td>
            <td>
              <button @click="editCustomer(customer)" class="btn-sm">編集</button>
              <button @click="deleteCustomer(customer.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="customers.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '得意先編集' : '得意先新規作成' }}</h2>
        <form @submit.prevent="saveCustomer">
          <div class="form-group">
            <label>得意先コード *</label>
            <input v-model="formData.customer_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>得意先名 *</label>
            <input v-model="formData.customer_name" required />
          </div>
          <div class="form-group">
            <label>略称</label>
            <input v-model="formData.short_name" />
          </div>
          <div class="form-group">
            <label>カレンダ</label>
            <select v-model="formData.calendar_id">
              <option :value="null">選択なし</option>
              <option v-for="cal in calendars" :key="cal.id" :value="cal.id">
                {{ cal.calendar_name }}
              </option>
            </select>
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
import api from '@/api/client'

const customers = ref([])
const calendars = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  customer_code: '',
  customer_name: '',
  short_name: '',
  calendar_id: null,
  is_active: true
})

const fetchCustomers = async () => {
  try {
    const response = await api.customers.getCustomers()
    // ページネーションレスポンスの場合はresultsを使用
    customers.value = response.data.results || response.data
  } catch (error) {
    console.error('得意先取得エラー:', error)
    alert('得意先データの取得に失敗しました')
  }
}

const fetchCalendars = async () => {
  try {
    const response = await api.calendars.getCalendars()
    calendars.value = response.data.results || response.data
  } catch (error) {
    console.error('カレンダ取得エラー:', error)
  }
}

const showNewDialog = () => {
  isEdit.value = false
  formData.value = {
    customer_code: '',
    customer_name: '',
    short_name: '',
    calendar_id: null,
    is_active: true
  }
  showDialog.value = true
}

const editCustomer = (customer) => {
  isEdit.value = true
  formData.value = { ...customer }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveCustomer = async () => {
  try {
    // データの前処理：空文字列をnullに変換
    const dataToSend = {
      ...formData.value,
      short_name: formData.value.short_name || null,
      calendar_id: formData.value.calendar_id || null
    }

    if (isEdit.value) {
      await api.customers.updateCustomer(dataToSend.id, dataToSend)
      alert('更新しました')
    } else {
      await api.customers.createCustomer(dataToSend)
      alert('作成しました')
    }
    await fetchCustomers()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    console.error('エラー詳細:', error.response?.data)
    const errorMessage = error.response?.data?.detail
      || JSON.stringify(error.response?.data)
      || error.message
      || '保存に失敗しました'
    alert('保存に失敗しました\n\n' + errorMessage)
  }
}

const deleteCustomer = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.customers.deleteCustomer(id)
    await fetchCustomers()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchCustomers()
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
.form-group select {
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
