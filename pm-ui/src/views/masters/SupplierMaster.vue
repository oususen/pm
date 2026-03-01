<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">仕入先マスタ</h1>
      <div class="page-actions">
        <button @click="fetchSuppliers" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>仕入先コード</th>
            <th>仕入先名</th>
            <th>送信メールアドレス</th>
            <th>専用カレンダー</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="supplier in suppliers" :key="supplier.id">
            <td>{{ supplier.supplier_code }}</td>
            <td>{{ supplier.supplier_name }}</td>
            <td>{{ supplier.order_email || '-' }}</td>
            <td>{{ getCalendarLabelBySupplier(supplier) }}</td>
            <td>
              <button @click="editSupplier(supplier)" class="btn-sm">編集</button>
              <button @click="deleteSupplier(supplier.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="suppliers.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '仕入先編集' : '仕入先新規作成' }}</h2>
        <form @submit.prevent="saveSupplier">
          <div class="form-group">
            <label>仕入先コード *</label>
            <input v-model="formData.supplier_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>仕入先名 *</label>
            <input v-model="formData.supplier_name" required />
          </div>
          <div class="form-group">
            <label>送信メールアドレス</label>
            <input v-model="formData.order_email" type="email" placeholder="example@company.co.jp" />
          </div>
          <div class="form-group">
            <label>専用カレンダー</label>
            <select v-model="formData.calendar">
              <option :value="null">未設定</option>
              <option v-for="calendar in calendars" :key="calendar.id" :value="calendar.id">
                {{ calendar.calendar_code }} - {{ calendar.calendar_name }}
              </option>
            </select>
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

const suppliers = ref([])
const calendars = ref([])
const purchaseLines = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  supplier_code: '',
  supplier_name: '',
  order_email: '',
  calendar: null,
})

const fetchSuppliers = async () => {
  try {
    const response = await api.suppliers.getSuppliers()
    suppliers.value = response.data.results || response.data
  } catch (error) {
    console.error('仕入先取得エラー:', error)
    alert('仕入先データの取得に失敗しました')
  }
}

const fetchCalendars = async () => {
  try {
    const response = await api.calendars.getCalendars()
    calendars.value = response.data.results || response.data || []
  } catch (error) {
    console.error('カレンダー取得エラー:', error)
  }
}

const fetchPurchaseLines = async () => {
  try {
    const response = await api.lines.getLines()
    const lines = response.data.results || response.data || []
    purchaseLines.value = lines.filter((row) => row.line_type === 'PURCHASE')
  } catch (error) {
    console.error('購買ライン取得エラー:', error)
  }
}

const getCalendarLabel = (calendarId) => {
  if (!calendarId) return '-'
  const found = calendars.value.find((item) => item.id === calendarId)
  if (!found) return '-'
  return `${found.calendar_code} - ${found.calendar_name}`
}

const getCalendarLabelBySupplier = (supplier) => {
  const purchaseLine = purchaseLines.value.find((line) => line.line_code === supplier.supplier_code)
  const calendarId = purchaseLine?.calendar || null
  return getCalendarLabel(calendarId)
}

const showNewDialog = () => {
  isEdit.value = false
  formData.value = {
    supplier_code: '',
    supplier_name: '',
    order_email: '',
    calendar: null,
  }
  showDialog.value = true
}

const editSupplier = (supplier) => {
  isEdit.value = true
  formData.value = { ...supplier }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveSupplier = async () => {
  try {
    const payload = {
      ...formData.value,
      order_email: (formData.value.order_email || '').trim(),
      calendar: formData.value.calendar || null,
    }
    if (isEdit.value) {
      await api.suppliers.updateSupplier(formData.value.id, payload)
      alert('更新しました')
    } else {
      await api.suppliers.createSupplier(payload)
      alert('作成しました')
    }
    await fetchSuppliers()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteSupplier = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.suppliers.deleteSupplier(id)
    await fetchSuppliers()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchSuppliers()
  fetchCalendars()
  fetchPurchaseLines()
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

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
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
