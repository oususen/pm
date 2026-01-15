<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="brand">DAISO 管理システム</div>
        <h1>ログイン</h1>
        <p>ユーザー名とパスワードを入力してください。</p>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label for="username">ユーザー名</label>
          <input
            id="username"
            v-model="username"
            type="text"
            autocomplete="username"
            placeholder="社員番号を入力（６桁全部入力してください）"
            :disabled="loading"
            required
          />
        </div>

        <div class="form-field">
          <label for="password">パスワード</label>
          <input
            id="password"
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="パスワード"
            :disabled="loading"
            required
          />
        </div>

        <div v-if="errorMessage" class="form-error">
          {{ errorMessage }}
        </div>

        <button type="submit" class="login-button" :disabled="loading">
          {{ loading ? 'ログイン中...' : 'ログイン' }}
        </button>
      </form>

      <div class="login-footer">
        <span class="hint-label">ヒント:</span>
        初期パスワード：123456。
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ensureAuth, login } from '../../auth'

const route = useRoute()
const router = useRouter()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

const redirectAfterLogin = () => {
  const nextPath = typeof route.query.next === 'string' ? route.query.next : '/'
  router.replace(nextPath)
}

const handleSubmit = async () => {
  errorMessage.value = ''
  loading.value = true
  try {
    const user = await login(username.value.trim(), password.value)
    if (!user) {
      errorMessage.value = 'ログインに失敗しました。'
      return
    }
    redirectAfterLogin()
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.error || 'ログインに失敗しました。'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  const user = await ensureAuth()
  if (user) {
    redirectAfterLogin()
  }
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap');

.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
  background: radial-gradient(circle at top left, #e8f7ed, #f8fafc 55%) fixed;
  font-family: 'Zen Kaku Gothic New', 'Hiragino Kaku Gothic ProN', sans-serif;
}

.login-card {
  width: min(420px, 100%);
  background: #ffffff;
  border-radius: 20px;
  padding: 32px 28px;
  box-shadow: 0 24px 60px rgba(16, 24, 40, 0.12);
  border: 1px solid rgba(229, 231, 235, 0.9);
  animation: fadeUp 0.5s ease both;
}

.login-header {
  margin-bottom: 24px;
}

.brand {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: #4b5563;
  margin-bottom: 8px;
}

.login-header h1 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}

.login-header p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field label {
  font-size: 12px;
  font-weight: 500;
  color: #374151;
}

.form-field input {
  border-radius: 10px;
  border: 1px solid #d1d5db;
  padding: 12px 14px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-field input:focus {
  outline: none;
  border-color: #16a34a;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.15);
}

.form-error {
  background: #fff1f2;
  color: #be123c;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
}

.login-button {
  margin-top: 4px;
  padding: 12px 14px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: white;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.login-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  box-shadow: none;
}

.login-button:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(34, 197, 94, 0.25);
}

.login-footer {
  margin-top: 20px;
  font-size: 12px;
  color: #6b7280;
}

.hint-label {
  font-weight: 600;
  color: #374151;
  margin-right: 6px;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
