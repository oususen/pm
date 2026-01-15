<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">プロフィール編集</h2>
    </div>

    <div class="page-content">
      <div v-if="errorMessage" class="alert alert-danger">
        {{ errorMessage }}
      </div>
      <div v-if="successMessage" class="alert alert-success">
        {{ successMessage }}
      </div>

      <form class="form-grid" @submit.prevent="saveProfile">
        <div class="form-row">
          <label>ユーザー名</label>
          <input v-model="form.username" type="text" required />
        </div>
        <div class="form-row">
          <label>メールアドレス</label>
          <input v-model="form.email" type="email" />
        </div>
        <div class="form-row">
          <label>姓</label>
          <input v-model="form.last_name" type="text" />
        </div>
        <div class="form-row">
          <label>名</label>
          <input v-model="form.first_name" type="text" />
        </div>
        <div class="form-row">
          <label>パスワード変更</label>
          <input v-model="form.password" type="password" placeholder="変更する場合のみ入力" />
        </div>
        <div class="form-row">
          <label>パスワード確認</label>
          <input v-model="form.password_confirm" type="password" placeholder="パスワード確認" />
        </div>
        <div class="form-actions">
          <button type="submit" class="btn primary" :disabled="loading">
            {{ loading ? '保存中...' : '保存' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { authState } from '../../auth'
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
const errorMessage = ref('')
const successMessage = ref('')

const loadProfile = async () => {
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

const saveProfile = async () => {
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
  loadProfile()
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
</style>
