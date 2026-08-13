<template>
  <div class="page">
    <h1 class="page-title">クボタ堺便計画設定 <DataSourceDialog title="クボタ堺便計画設定" :sources="dsSources" /></h1>
    <div class="card">
      <div class="row">
        <label>未割付期限（日）</label>
        <input v-model.number="deadlineDays" type="number" min="0" />
      </div>
      <p class="help">調整後納期の何営業日前までに便割付を完了すべきかを設定します。</p>
      <div class="row">
        <label>検知時刻</label>
        <div class="time-row">
          <input v-model.number="scheduledHour" type="number" min="0" max="23" />
          <span>時</span>
          <input v-model.number="scheduledMinute" type="number" min="0" max="59" />
          <span>分</span>
        </div>
      </div>
      <p class="help">1日1回、この時刻に未割付期限超過を検知して通知します。</p>
      <div class="notify-field">
        <label>通知先</label>
        <UserChipSelect
          v-model="notifyUserIds"
          :userList="allUsers"
        />
      </div>
      <p class="help">未割付期限を超過した明細がある日に、ここで選んだユーザーへ1日1回だけ通知します。</p>
      <div class="actions">
        <button class="btn" :disabled="loading || saving" @click="load">再読込</button>
        <button class="btn primary" :disabled="loading || saving" @click="save">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import UserChipSelect from '@/views/purchase/UserChipSelect.vue'

const dsSources = [
  { op: '読み書き', table: 'system_setting', desc: 'クボタ堺便計画設定' },
]

const KEY = 'kubota_sakai.assignment_deadline_days'
const NOTIFY_USERS_KEY = 'kubota_sakai.overdue_notify_user_ids'
const TASK_NAME = 'KUBOTA_SAKAI_DUE_SYNC'
const loading = ref(false)
const saving = ref(false)
const deadlineDays = ref(3)
const allUsers = ref([])
const notifyUserIds = ref([])
const scheduleConfigId = ref(null)
const scheduledHour = ref(7)
const scheduledMinute = ref(45)

const parseNotifyUserIds = (value) => {
  if (!value) return []
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed.map((item) => Number(item)).filter((item) => Number.isFinite(item)) : []
  } catch (error) {
    return []
  }
}

const load = async () => {
  loading.value = true
  try {
    const [settingsRes, usersRes, scheduleRes] = await Promise.all([
      api.systemSettings.getAll(),
      api.accounts.getUsers({ is_active: true, ordering: 'username', page_size: 9999 }),
      api.scheduleConfig.getConfigs(),
    ])
    const value = settingsRes.data?.[KEY]?.value
    const parsed = Number(value)
    deadlineDays.value = Number.isFinite(parsed) ? parsed : 3
    notifyUserIds.value = parseNotifyUserIds(settingsRes.data?.[NOTIFY_USERS_KEY]?.value)
    allUsers.value = usersRes.data?.results || usersRes.data || []
    const scheduleConfigs = Array.isArray(scheduleRes.data) ? scheduleRes.data : []
    const targetConfig = scheduleConfigs.find((item) => item.task_name === TASK_NAME && !item.line && !item.process)
    scheduleConfigId.value = targetConfig?.id || null
    scheduledHour.value = Number.isFinite(Number(targetConfig?.scheduled_hour)) ? Number(targetConfig.scheduled_hour) : 7
    scheduledMinute.value = Number.isFinite(Number(targetConfig?.scheduled_minute)) ? Number(targetConfig.scheduled_minute) : 45
  } catch (error) {
    const message = error?.response?.data?.detail || '設定取得に失敗しました。'
    alert(message)
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  try {
    const normalizedHour = Math.max(0, Math.min(23, Number(scheduledHour.value || 0)))
    const normalizedMinute = Math.max(0, Math.min(59, Number(scheduledMinute.value || 0)))
    await Promise.all([
      api.systemSettings.updateByKey({
        [KEY]: Number(deadlineDays.value || 0),
        [NOTIFY_USERS_KEY]: JSON.stringify(notifyUserIds.value || []),
      }),
      api.scheduleConfig.saveConfig({
        id: scheduleConfigId.value,
        task_name: TASK_NAME,
        scheduled_hour: normalizedHour,
        scheduled_minute: normalizedMinute,
        is_enabled: true,
      }),
    ])
    alert('保存しました。')
    await load()
  } catch (error) {
    const message = error?.response?.data?.detail || '設定保存に失敗しました。'
    alert(message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding: 16px; }
.page-title { margin: 0 0 12px 0; font-size: 20px; }
.card {
  max-width: 560px;
  background: #fff;
  border: 1px solid #d7dfe8;
  border-radius: 8px;
  padding: 16px;
}
.row { display: flex; gap: 12px; align-items: center; }
.row label { width: 160px; font-weight: 700; }
.row input { width: 120px; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 4px; }
.time-row { display: flex; align-items: center; gap: 8px; }
.time-row input { width: 72px; }
.notify-field { margin-top: 16px; }
.notify-field label { display: block; margin-bottom: 6px; font-weight: 700; }
.help { color: #64748b; font-size: 12px; margin: 10px 0 16px; }
.actions { display: flex; gap: 8px; }
.btn { padding: 6px 12px; border: 1px solid #b5c1d2; background: #fff; border-radius: 4px; cursor: pointer; }
.btn.primary { background: #dff3e6; border-color: #8fc8a1; }
</style>
