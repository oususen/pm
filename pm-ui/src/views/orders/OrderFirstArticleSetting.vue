<template>
  <div class="settings-container">
    <h2 class="page-title">受注お久しぶり製品通知設定</h2>
    <div v-if="!canView" class="card no-permission">この画面を開く権限がありません。</div>
    <div v-else class="card">
      <div class="field">
        <label>お久しぶり判定日数</label>
        <div class="input-row">
          <input v-model.number="days" type="number" min="1" :disabled="loading || !canEdit" />
          <span class="suffix">日</span>
        </div>
        <p class="helper">受注取込後、各明細の納期から指定日数さかのぼって同一品番の受注がなければ通知対象にします。</p>
      </div>

      <div class="field">
        <label>送信宛先</label>
        <UserChipSelect
          :userList="userList"
          v-model="recipientUserIds"
        />
        <p class="helper">社員を検索して送信先に追加します。</p>
        <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>
      </div>

      <div class="actions">
        <button class="btn primary" @click="saveSetting" :disabled="loading || saving || !canEdit">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import UserChipSelect from '@/views/purchase/UserChipSelect.vue'

const days = ref(90)
const recipientUserIds = ref([])
const userList = ref([])
const loading = ref(false)
const saving = ref(false)

const canAccessOrders = (level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  if (hasPermission(user, 'orders.first_article', level)) return true
  return hasPermission(user, 'orders', level)
}

const canView = computed(() => canAccessOrders('view'))
const canEdit = computed(() => canAccessOrders('edit'))

const loadSetting = async () => {
  if (!canView.value) return
  loading.value = true
  try {
    const res = await api.orders.getFirstArticleSetting()
    days.value = Number(res.data?.days ?? 90)
    recipientUserIds.value = Array.isArray(res.data?.recipient_user_ids) ? res.data.recipient_user_ids : []
    userList.value = Array.isArray(res.data?.all_users) ? res.data.all_users : []
  } catch (error) {
    console.error('受注お久しぶり製品通知設定の取得に失敗しました', error)
    alert('設定の取得に失敗しました。')
  } finally {
    loading.value = false
  }
}

const saveSetting = async () => {
  if (!canEdit.value) return
  if (!Number.isInteger(days.value) || days.value < 1) {
    alert('判定日数は1以上の整数で入力してください。')
    return
  }

  saving.value = true
  try {
    const res = await api.orders.saveFirstArticleSetting({
      days: days.value,
      recipient_user_ids: recipientUserIds.value,
    })
    days.value = Number(res.data?.days ?? days.value)
    recipientUserIds.value = Array.isArray(res.data?.recipient_user_ids) ? res.data.recipient_user_ids : []
    alert('保存しました。')
  } catch (error) {
    console.error('受注お久しぶり製品通知設定の保存に失敗しました', error)
    alert(error?.response?.data?.detail || '保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSetting()
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
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}
.field label {
  font-size: 12px;
  color: #444;
}
.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.input-row input {
  width: 120px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.suffix {
  font-size: 12px;
  color: #333;
}
.helper {
  margin: 0;
  font-size: 12px;
  color: #666;
}
.helper.warning {
  color: #b45309;
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
</style>
