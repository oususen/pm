<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">クボタ堺 確定取り込み通知設定</h1>
    </div>

    <div v-if="!canViewPage" class="page-content">
      <div class="loading">この画面を開く権限がありません。</div>
    </div>
    <div v-else class="page-content">
      <div class="settings-card">
        <p class="description">
          クボタ堺の確定CSVを取り込んだ際に、内示と数量が異なる品番があった場合、
          以下のユーザーに通知を送信します。
        </p>

        <div v-if="loading" class="loading">読み込み中...</div>

        <template v-else>
          <div class="section">
            <h3>通知先ユーザー</h3>
            <div class="user-list">
              <label
                v-for="user in allUsers"
                :key="user.id"
                class="user-row"
              >
                <input
                  type="checkbox"
                  :value="user.id"
                  v-model="selectedUserIds"
                  :disabled="!canEditPage"
                />
                <span>{{ user.full_name }}</span>
              </label>
            </div>
          </div>

          <div class="form-actions">
            <button @click="save" :disabled="saving || !canEditPage" class="btn-primary">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>

          <div v-if="saveMessage" class="save-message" :class="saveError ? 'error' : 'success'">
            {{ saveMessage }}
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import axios from 'axios'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const loading = ref(true)
const saving = ref(false)
const allUsers = ref([])
const selectedUserIds = ref([])
const saveMessage = ref('')
const saveError = ref(false)

const canViewPage = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return hasPermission(user, 'settings', 'view')
})

const canEditPage = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return hasPermission(user, 'settings', 'edit')
})

const fetchConfig = async () => {
  if (!canViewPage.value) return
  try {
    const res = await axios.get(`${API_BASE_URL}/kubota-sakai-import-config/`)
    allUsers.value = res.data.all_users
    selectedUserIds.value = res.data.notify_users.map(u => u.id)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const save = async () => {
  if (!canEditPage.value) return
  saving.value = true
  saveMessage.value = ''
  try {
    await axios.patch(`${API_BASE_URL}/kubota-sakai-import-config/`, {
      notify_user_ids: selectedUserIds.value,
    })
    saveMessage.value = '保存しました'
    saveError.value = false
  } catch (e) {
    saveMessage.value = '保存に失敗しました'
    saveError.value = true
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (!canViewPage.value) return
  fetchConfig()
})
</script>

<style scoped>
.settings-card {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.description {
  color: #555;
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

.section h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: #333;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.5rem;
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 360px;
  overflow-y: auto;
  padding: 4px;
}

.user-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.user-row:hover {
  background: #f5f7ff;
}

.user-row input[type="checkbox"] {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.form-actions {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
}

.save-message {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 4px;
  font-size: 0.9rem;
}

.save-message.success {
  background: #d4edda;
  color: #155724;
}

.save-message.error {
  background: #fee;
  color: #c00;
}

.loading {
  color: #999;
  text-align: center;
  padding: 2rem;
}
</style>
