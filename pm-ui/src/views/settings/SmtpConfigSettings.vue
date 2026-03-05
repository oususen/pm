<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">SMTP設定管理</h1>
      <div class="page-actions">
        <button @click="fetchConfigs" class="btn-primary" :disabled="loading || !canViewPage">更新</button>
        <button @click="showNewDialog" class="btn-success" :disabled="!canEditPage">新規</button>
      </div>
    </div>

    <div v-if="!canViewPage" class="page-content">
      <div class="no-data">この画面を開く権限がありません。</div>
    </div>
    <div v-else class="page-content">
      <div v-if="loading" class="loading-message">読み込み中...</div>
      <template v-else>
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>ユーザー名</th>
              <th>SMTPホスト</th>
              <th>ポート</th>
              <th>SMTPユーザー</th>
              <th>デフォルト</th>
              <th>有効</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="config in configs" :key="config.id">
              <td>{{ config.id }}</td>
              <td>{{ config.username }}</td>
              <td>{{ config.smtp_host }}</td>
              <td>{{ config.smtp_port || 587 }}</td>
              <td>{{ config.smtp_user }}</td>
              <td>{{ config.is_admin ? '✓' : '' }}</td>
              <td>{{ config.is_active ? '有効' : '無効' }}</td>
              <td>
                <button @click="editConfig(config)" class="btn-sm" :disabled="!canEditPage">編集</button>
                <button @click="deleteConfig(config.id)" class="btn-sm btn-danger" :disabled="!canEditPage">削除</button>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="configs.length === 0" class="no-data">
          データがありません
        </div>
      </template>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? 'SMTP設定編集' : 'SMTP設定新規作成' }}</h2>
        <form @submit.prevent="saveConfig">
          <div class="form-group">
            <label>ユーザー *</label>
            <select v-model="formData.user" required :disabled="isEdit || !canEditPage">
              <option value="">選択してください</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                {{ user.username }} ({{ user.email }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>SMTPホスト *</label>
            <input v-model="formData.smtp_host" required placeholder="例: smtp.gmail.com" :disabled="!canEditPage" />
          </div>
          <div class="form-group">
            <label>SMTPポート</label>
            <input type="number" v-model.number="formData.smtp_port" placeholder="587" :disabled="!canEditPage" />
            <small>デフォルト: 587</small>
          </div>
          <div class="form-group">
            <label>SMTPユーザー *</label>
            <input v-model="formData.smtp_user" required placeholder="メールアドレス" :disabled="!canEditPage" />
          </div>
          <div class="form-group">
            <label>SMTPパスワード *</label>
            <input type="password" v-model="formData.smtp_password" :required="!isEdit"
              placeholder="パスワード" :disabled="!canEditPage" />
            <small v-if="isEdit">※ 変更する場合のみ入力してください</small>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_admin" :disabled="!canEditPage" />
              デフォルト設定（全ユーザーで使用可能）
            </label>
            <small>※ チェックを入れると、SMTP設定を持たないユーザーがこの設定を使用します</small>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" :disabled="!canEditPage" />
              有効
            </label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="!canEditPage">保存</button>
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
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const configs = ref([])
const users = ref([])
const loading = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  user: '',
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  is_admin: false,
  is_active: true
})

const canAccessByResource = (resource, level = 'view') => {
  const user = authState.user
  if (!user || !resource) return false
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) {
    return hasPermission(user, resource, level)
  }
  return hasPermission(user, 'settings', level)
}

const canViewPage = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return canAccessByResource('settings.smtp', 'view')
})

const canEditPage = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return canAccessByResource('settings.smtp', 'edit')
})

const fetchConfigs = async () => {
  if (!canViewPage.value) return
  loading.value = true
  try {
    const response = await api.smtpConfigs.getSmtpConfigs()
    configs.value = response.data.results || response.data
  } catch (error) {
    console.error('SMTP設定取得エラー:', error)
    alert('SMTP設定の取得に失敗しました')
  } finally {
    loading.value = false
  }
}

const fetchUsers = async () => {
  if (!canViewPage.value) return
  try {
    // 全ユーザー（管理者含む）を大量に取得
    const response = await api.accounts.getUsers({
      page_size: 1000,  // ページサイズを大きくして全ユーザー取得
      ordering: 'username'
    })
    users.value = response.data.results || response.data

    // デバッグ: ユーザー一覧を確認
    console.log('取得したユーザー数:', users.value.length)

    // adminユーザーが含まれているか確認
    const adminUser = users.value.find(u => u.username === 'admin')
    console.log('adminユーザー:', adminUser ? 'あり' : 'なし')
  } catch (error) {
    console.error('ユーザー取得エラー:', error)
  }
}

const showNewDialog = () => {
  if (!canEditPage.value) return
  isEdit.value = false
  formData.value = {
    user: '',
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    is_admin: false,
    is_active: true
  }
  showDialog.value = true
}

const editConfig = (config) => {
  if (!canEditPage.value) return
  isEdit.value = true
  formData.value = {
    ...config,
    smtp_password: '' // パスワードは空にする
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveConfig = async () => {
  if (!canEditPage.value) return
  try {
    const dataToSend = { ...formData.value }

    // パスワードが空の場合は送信しない（編集時）
    if (isEdit.value && !dataToSend.smtp_password) {
      delete dataToSend.smtp_password
    }

    if (isEdit.value) {
      await api.smtpConfigs.updateSmtpConfig(formData.value.id, dataToSend)
      alert('更新しました')
    } else {
      await api.smtpConfigs.createSmtpConfig(dataToSend)
      alert('作成しました')
    }
    await fetchConfigs()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteConfig = async (id) => {
  if (!canEditPage.value) return
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.smtpConfigs.deleteSmtpConfig(id)
    await fetchConfigs()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(async () => {
  if (!canViewPage.value) return
  await Promise.all([fetchConfigs(), fetchUsers()])
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
.form-group input[type="password"],
.form-group input[type="number"],
.form-group select {
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
.form-group small {
  display: block;
  margin-top: 0.25rem;
  color: #666;
  font-size: 0.875rem;
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
