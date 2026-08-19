<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">プロフィール編集</h2>
    </div>

    <div class="page-content">
      <div v-if="!canView" class="alert alert-danger">この画面を開く権限がありません。</div>
      <template v-else>
        <div v-if="errorMessage" class="alert alert-danger">
          {{ errorMessage }}
        </div>
        <div v-if="successMessage" class="alert alert-success">
          {{ successMessage }}
        </div>

        <form class="form-grid" @submit.prevent="saveProfile">
          <div class="form-row">
            <label>ユーザー名</label>
            <input v-model="form.username" type="text" required :disabled="!canEdit" />
          </div>
          <div class="form-row">
            <label>メールアドレス</label>
            <input v-model="form.email" type="email" :disabled="!canEdit" />
          </div>
          <div class="form-row">
            <label>姓</label>
            <input v-model="form.last_name" type="text" :disabled="!canEdit" />
          </div>
          <div class="form-row">
            <label>名</label>
            <input v-model="form.first_name" type="text" :disabled="!canEdit" />
          </div>
          <div class="form-row">
            <label>パスワード変更</label>
            <input
              v-model="form.password"
              type="password"
              placeholder="変更する場合のみ入力"
              :disabled="!canEdit"
            />
          </div>
          <div class="form-row">
            <label>パスワード確認</label>
            <input
              v-model="form.password_confirm"
              type="password"
              placeholder="パスワード確認"
              :disabled="!canEdit"
            />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn primary" :disabled="loading || !canEdit">
              {{ loading ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>

        <div v-if="canViewAndroidApp" class="link-section">
          <h3 class="section-title">アプリ</h3>
          <router-link to="/settings/android-app" class="link-item">📱 Androidアプリ ダウンロード</router-link>
        </div>

        <div class="favorites-section">
          <h3 class="section-title">お気に入り管理</h3>
          <p class="section-note">各画面で登録したお気に入りを削除できます。</p>
          <div v-if="favoriteLoading" class="favorites-loading">読込中...</div>
          <div v-else-if="!favorites.length" class="favorites-empty">登録されたお気に入りはありません。</div>
          <table v-else class="favorites-table">
            <thead>
              <tr>
                <th>画面</th>
                <th>名前</th>
                <th>更新日時</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in favorites" :key="item.id">
                <td>{{ item.screen_key }}</td>
                <td>{{ item.name }}</td>
                <td>{{ formatDateTime(item.updated_at) }}</td>
                <td>
                  <button type="button" class="btn danger" @click="deleteFavorite(item)" :disabled="favoriteLoading">
                    削除
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { authState } from '../../auth'
import { hasPermission } from '@/router'
import api from '../../api/client'

const form = ref({
  username: '',
  email: '',
  last_name: '',
  first_name: '',
  password: '',
  password_confirm: ''
})

const loading = ref(false)
const favoriteLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const favorites = ref([])

const canAccessByResource = (resource, level = 'view') => {
  const user = authState.user
  if (!user || !resource) return false
  if (user.is_staff || user.is_superuser) return true

  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) {
    return hasPermission(user, resource, level)
  }
  return hasPermission(user, 'settings', level)
}

const canView = computed(() => canAccessByResource('settings.profile', 'view'))
const canEdit = computed(() => canAccessByResource('settings.profile', 'edit'))
const canViewAndroidApp = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  const role = user.profile?.role || ''
  const leaderRoles = ['leader', 'supervisor', 'chief', 'manager', 'admin']
  return leaderRoles.includes(role)
})

const loadProfile = async () => {
  if (!canView.value) return
  try {
    const response = await api.accounts.getUser('me')
    const user = response.data
    form.value = {
      username: user.username || '',
      email: user.email || '',
      last_name: user.last_name || '',
      first_name: user.first_name || '',
      password: '',
      password_confirm: ''
    }
  } catch (error) {
    errorMessage.value = 'プロフィールの読み込みに失敗しました。'
    console.error('Profile load error:', error)
  }
}

const loadFavorites = async () => {
  if (!canView.value) return
  favoriteLoading.value = true
  try {
    const response = await api.accounts.getFavorites({ page_size: 500 })
    favorites.value = Array.isArray(response.data) ? response.data : response.data?.results || []
  } catch (error) {
    console.error('Favorite load error:', error)
  } finally {
    favoriteLoading.value = false
  }
}

const deleteFavorite = async (item) => {
  if (!item?.id) return
  const ok = window.confirm(`お気に入り「${item.name}」を削除しますか？`)
  if (!ok) return

  favoriteLoading.value = true
  try {
    await api.accounts.deleteFavorite(item.id)
    await loadFavorites()
    successMessage.value = 'お気に入りを削除しました。'
  } catch (error) {
    console.error('Favorite delete error:', error)
    errorMessage.value = 'お気に入りの削除に失敗しました。'
  } finally {
    favoriteLoading.value = false
  }
}

const formatDateTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${hh}:${mm}`
}

const saveProfile = async () => {
  if (!canEdit.value) return
  if (form.value.password && form.value.password !== form.value.password_confirm) {
    errorMessage.value = 'パスワードが一致しません。'
    return
  }

  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const updateData = {
      username: form.value.username,
      email: form.value.email,
      last_name: form.value.last_name,
      first_name: form.value.first_name
    }

    if (form.value.password) {
      updateData.password = form.value.password
    }

    await api.accounts.updateUserPartial('me', updateData)
    successMessage.value = 'プロフィールを更新しました。'
    form.value.password = ''
    form.value.password_confirm = ''
  } catch (error) {
    errorMessage.value = 'プロフィールの更新に失敗しました。'
    console.error('Profile save error:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (canView.value) {
    loadProfile()
    loadFavorites()
  }
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  color: #333;
}

.page-content {
  max-width: 600px;
}

.form-grid {
  display: grid;
  gap: 16px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-row label {
  font-weight: bold;
  color: #555;
}

.form-row input,
.form-row select {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-row input:disabled {
  background-color: #f5f5f5;
  color: #999;
}

.form-actions {
  margin-top: 20px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn.primary {
  background-color: #52b788;
  color: white;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.alert {
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
}

.alert-danger {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.alert-success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}
.link-section {
  margin-top: 28px;
}
.link-item {
  display: inline-block;
  padding: 10px 16px;
  background: #f0f0f0;
  border-radius: 6px;
  color: #333;
  text-decoration: none;
  font-size: 14px;
}
.link-item:hover {
  background: #e0e0e0;
}
.favorites-section {
  margin-top: 28px;
}
.section-title {
  margin: 0 0 8px 0;
  font-size: 16px;
}
.section-note {
  margin: 0 0 10px 0;
  color: #666;
  font-size: 13px;
}
.favorites-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.favorites-table th,
.favorites-table td {
  border: 1px solid #ddd;
  padding: 8px 10px;
  text-align: left;
}
.favorites-table th {
  background: #f8f8f8;
}
.favorites-empty,
.favorites-loading {
  color: #777;
  font-size: 13px;
}
.btn.danger {
  background: #dc3545;
  color: #fff;
  padding: 6px 10px;
}
</style>
