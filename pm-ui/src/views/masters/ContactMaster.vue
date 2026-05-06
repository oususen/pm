<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">連絡先マスタ</h1>
      <div class="page-actions">
        <button @click="fetchContacts" class="btn-primary" :disabled="loading">更新</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>検索（会社名/担当者）</label>
          <input
            v-model="filters.search"
            @keyup.enter="fetchContacts"
            placeholder="キーワード検索"
          />
        </div>
        <div class="filter-field">
          <label>種別</label>
          <input
            v-model="filters.contact_type"
            @keyup.enter="fetchContacts"
            placeholder="種別で検索"
          />
        </div>
        <div class="filter-field">
          <label>有効</label>
          <select v-model="filters.is_active">
            <option value="">すべて</option>
            <option value="true">有効</option>
            <option value="false">無効</option>
          </select>
        </div>
        <div class="filter-actions">
          <button @click="fetchContacts" class="btn-primary">検索</button>
          <button @click="resetFilters" class="btn-secondary">リセット</button>
        </div>
      </div>

      <div v-if="loading" class="loading-message">読み込み中...</div>
      <template v-else>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>種別</th>
            <th>会社名</th>
            <th>部署</th>
            <th>担当者</th>
            <th>Email</th>
            <th>電話番号</th>
            <th>表示順</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="contact in contacts" :key="contact.id">
            <td>{{ contact.id }}</td>
            <td>{{ contact.contact_type }}</td>
            <td>{{ contact.company_name }}</td>
            <td>{{ contact.department || '-' }}</td>
            <td>{{ contact.contact_person || '-' }}</td>
            <td>{{ contact.email }}</td>
            <td>{{ contact.phone || '-' }}</td>
            <td>{{ contact.display_order }}</td>
            <td>{{ contact.is_active ? '有効' : '無効' }}</td>
            <td>
              <button v-if="canEdit" @click="editContact(contact)" class="btn-sm">編集</button>
              <button v-if="canEdit" @click="deleteContact(contact.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="contacts.length === 0" class="no-data">
        データがありません
      </div>
      </template>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '連絡先編集' : '連絡先新規作成' }}</h2>
        <form @submit.prevent="saveContact">
          <div class="form-group">
            <label>種別 *</label>
            <input v-model="formData.contact_type" required placeholder="例: 枚方集荷依頼" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>会社名 *</label>
            <input v-model="formData.company_name" required :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>部署名</label>
            <input v-model="formData.department" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>担当者名</label>
            <input v-model="formData.contact_person" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>Email *</label>
            <input type="email" v-model="formData.email" required :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>電話番号</label>
            <input v-model="formData.phone" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>表示順</label>
            <input type="number" v-model.number="formData.display_order" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>備考</label>
            <textarea v-model="formData.note" rows="3" :disabled="!canEdit"></textarea>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" :disabled="!canEdit" />
              有効
            </label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="!canEdit">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import api from '@/api/client'
import { canAccessMasterResource } from '@/utils/masterPermissions'

const contacts = ref([])
const loading = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  contact_type: '',
  company_name: '',
  department: '',
  contact_person: '',
  email: '',
  phone: '',
  display_order: 0,
  note: '',
  is_active: true
})
const canEdit = computed(() => canAccessMasterResource('masters.contact', 'edit'))

const filters = ref({
  search: '',
  contact_type: '',
  is_active: ''
})

const resetFilters = () => {
  filters.value = {
    search: '',
    contact_type: '',
    is_active: ''
  }
  fetchContacts()
}

const fetchContacts = async () => {
  loading.value = true
  try {
    if (!api.contacts) {
      alert('API設定エラー: src/api/client.js に contacts の定義がありません。')
      loading.value = false
      return
    }
    const params = {}
    if (filters.value.search) params.search = filters.value.search
    if (filters.value.contact_type) params.contact_type = filters.value.contact_type
    if (filters.value.is_active !== '') params.is_active = filters.value.is_active

    const response = await api.contacts.getContacts(params)
    contacts.value = response.data.results || response.data
  } catch (error) {
    console.error('連絡先取得エラー:', error)
  } finally {
    loading.value = false
  }
}

const showNewDialog = () => {
  if (!canEdit.value) return
  isEdit.value = false
  formData.value = {
    contact_type: '',
    company_name: '',
    department: '',
    contact_person: '',
    email: '',
    phone: '',
    display_order: 0,
    note: '',
    is_active: true
  }
  showDialog.value = true
}

const editContact = (contact) => {
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = { ...contact }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveContact = async () => {
  if (!canEdit.value) return
  try {
    if (isEdit.value) {
      await api.contacts.updateContact(formData.value.id, formData.value)
      alert('更新しました')
    } else {
      await api.contacts.createContact(formData.value)
      alert('作成しました')
    }
    await fetchContacts()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteContact = async (id) => {
  if (!canEdit.value) return
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.contacts.deleteContact(id)
    await fetchContacts()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchContacts()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-title {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}
.page-actions {
  display: flex;
  gap: 10px;
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 16px;
  background-color: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
}
.filter-field {
  display: flex;
  flex-direction: column;
  min-width: 180px;
}
.filter-field label {
  font-size: 12px;
  color: #555;
  margin-bottom: 4px;
}
.filter-field input,
.filter-field select {
  padding: 6px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}
.filter-actions {
  display: flex;
  gap: 8px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}
.data-table th,
.data-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}
.data-table th {
  background-color: #f2f2f2;
  font-weight: bold;
}
.btn-primary {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}
.btn-primary:hover {
  background-color: #0056b3;
}
.btn-success {
  background-color: #28a745;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}
.btn-success:hover {
  background-color: #218838;
}
.btn-secondary {
  background-color: #6c757d;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}
.btn-secondary:hover {
  background-color: #5a6268;
}
.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 3px;
  border: 1px solid #ccc;
  background-color: #fff;
  cursor: pointer;
  margin-right: 4px;
}
.btn-danger {
  background-color: #dc3545;
  color: white;
  border: none;
}
.btn-danger:hover {
  background-color: #c82333;
}
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
.form-group input[type="email"],
.form-group input[type="number"],
.form-group textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
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
.no-data {
  padding: 20px;
  text-align: center;
  color: #888;
}
.loading-message {
  padding: 20px;
  text-align: center;
  color: #666;
}
</style>

