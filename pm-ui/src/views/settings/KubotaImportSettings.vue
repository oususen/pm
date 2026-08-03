<template>
  <div class="settings-container">
    <h2 class="page-title">クボタ堺 確定取り込み通知設定</h2>
    <div v-if="!canView" class="card no-permission">この画面を開く権限がありません。</div>
    <div v-else class="card">
      <div v-if="loading" class="loading">読み込み中...</div>
      <template v-else>
        <p class="description">
          クボタ堺の確定CSVを取り込んだ際に、内示と数量が異なる品番があった場合、
          以下のユーザーにアプリ内通知を送信します。メール通知を有効にすると、同じ宛先にメールも送信します。
        </p>

        <div class="field">
          <label>通知先</label>
          <UserChipSelect
            :userList="allUsers"
            v-model="notifyUserIds"
          />
          <p class="helper">社員を検索して通知先に追加します。</p>
        </div>

        <div class="field">
          <label>メール通知</label>
          <div class="toggle-row">
            <label class="toggle-label">
              <input type="checkbox" v-model="emailEnabled" :disabled="!canEdit" />
              <span>差分検知時にメールも送信する</span>
            </label>
          </div>
          <p class="helper">有効にすると、上記通知先ユーザーのメールアドレス宛にメールを送信します。</p>
        </div>

        <div class="actions">
          <button class="btn primary" @click="save" :disabled="saving || !canEdit">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>

        <div v-if="saveMessage" class="save-message" :class="saveError ? 'error' : 'success'">
          {{ saveMessage }}
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import UserChipSelect from '@/views/purchase/UserChipSelect.vue'

const loading = ref(true)
const saving = ref(false)
const allUsers = ref([])
const notifyUserIds = ref([])
const emailEnabled = ref(false)
const saveMessage = ref('')
const saveError = ref(false)

const canAccess = (level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return hasPermission(user, 'settings', level)
}

const canView = computed(() => canAccess('view'))
const canEdit = computed(() => canAccess('edit'))

const fetchConfig = async () => {
  if (!canView.value) return
  try {
    const res = await api.orders.getKubotaSakaiImportConfig()
    allUsers.value = res.data.all_users || []
    notifyUserIds.value = res.data.notify_user_ids || []
    emailEnabled.value = !!res.data.email_enabled
  } catch (e) {
    console.error('設定取得エラー', e)
  } finally {
    loading.value = false
  }
}

const save = async () => {
  if (!canEdit.value) return
  saving.value = true
  saveMessage.value = ''
  try {
    const res = await api.orders.saveKubotaSakaiImportConfig({
      notify_user_ids: notifyUserIds.value,
      email_enabled: emailEnabled.value,
    })
    notifyUserIds.value = res.data.notify_user_ids || notifyUserIds.value
    emailEnabled.value = !!res.data.email_enabled
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
  fetchConfig()
})
</script>

<style scoped>
.settings-container {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
  color: #1f2a44;
  font-family: 'Segoe UI', 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
}
.page-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
}
.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 12px;
  max-width: 720px;
}
.no-permission {
  color: #b91c1c;
  font-weight: 600;
}
.description {
  color: #555;
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.6;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}
.field > label {
  font-size: 12px;
  color: #444;
}
.helper {
  margin: 0;
  font-size: 12px;
  color: #666;
}
.toggle-row {
  display: flex;
  align-items: center;
}
.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
}
.toggle-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.actions {
  margin-top: 12px;
}
.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
.save-message {
  margin-top: 10px;
  padding: 8px;
  border-radius: 4px;
  font-size: 13px;
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
