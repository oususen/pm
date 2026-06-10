<template>
  <div class="settings-container">
    <h2 class="page-title">生産計画ロック設定 <DataSourceDialog title="生産計画ロック設定" :sources="dsSources" /></h2>
    <div v-if="!canView" class="card no-permission">この画面を開く権限がありません。</div>
    <div v-else class="card">
      <div class="field">
        <label>計画入力を読み取りにする日数</label>
        <div class="input-row">
          <input type="number" min="0" v-model.number="lockDays" :disabled="!canEdit" />
          <span class="suffix">日</span>
        </div>
        <p class="helper">今日を含めて指定日数までの計画日を編集不可にします。</p>
        <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>
      </div>
      <div class="actions">
        <button class="btn primary" @click="saveSetting" :disabled="saving || !canEdit">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: '*_lock_setting', desc: '生産計画ロック日数' },
]

const lockDays = ref(0)
const saving = ref(false)
const canAccessByResource = (resource, level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true

  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : []
  if (permissions.some((item) => item.resource === resource)) {
    return hasPermission(user, resource, level)
  }
  return hasPermission(user, 'settings', level)
}

const canView = computed(() => canAccessByResource('settings.production_plan_lock', 'view'))
const canEdit = computed(() => canAccessByResource('settings.production_plan_lock', 'edit'))

const loadSetting = async () => {
  if (!canView.value) return
  try {
    const res = await api.productionPlanLockSetting.getSetting()
    lockDays.value = Number(res.data?.lock_days ?? 0)
  } catch (e) {
    console.error('生産計画ロック設定の取得に失敗しました', e)
    lockDays.value = 0
  }
}

const saveSetting = async () => {
  if (!canEdit.value) return
  saving.value = true
  try {
    const res = await api.productionPlanLockSetting.saveSetting({ lock_days: lockDays.value })
    lockDays.value = Number(res.data?.lock_days ?? 0)
    alert('保存しました。')
  } catch (e) {
    console.error('生産計画ロック設定の保存に失敗しました', e)
    alert('保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  if (!canView.value) return
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
  max-width: 560px;
}
.no-permission {
  color: #b91c1c;
  font-weight: 600;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
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


