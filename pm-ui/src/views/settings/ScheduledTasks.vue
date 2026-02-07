<template>
  <div class="settings-container">
    <h2 class="page-title">定時タスク設定</h2>
    <div class="card">
      <div class="field">
        <label>取り込み＋在庫再計算 - 実行時刻</label>
        <div class="input-row">
          <input
            type="number"
            min="0"
            max="23"
            v-model.number="config.scheduled_hour"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">時</span>
          <input
            type="number"
            min="0"
            max="59"
            v-model.number="config.scheduled_minute"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">分</span>
        </div>
        <p class="helper">毎日指定した時刻に需要取り込み（pickup）→ 在庫・計画在庫・進度の自動再計算を実行します。</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="config.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="actions">
        <button class="btn primary" @click="saveConfig" :disabled="saving || !canEdit">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button
          class="btn"
          @click="runNow"
          :disabled="running || !canEdit"
          style="margin-left: 8px"
        >
          {{ running ? '実行中...' : '今すぐ実行' }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="config.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(config.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass">{{ config.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ config.last_run_duration_seconds != null ? config.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ config.last_run_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const config = reactive({
  task_name: 'INVENTORY_RECALC',
  is_enabled: true,
  scheduled_hour: 7,
  scheduled_minute: 0,
  last_run_at: null,
  last_run_status: null,
  last_run_status_display: '',
  last_run_message: '',
  last_run_duration_seconds: null,
})
const saving = ref(false)
const running = ref(false)
const canEdit = computed(() => hasPermission(authState.user, 'settings', 'edit'))

const statusClass = computed(() => ({
  'status-success': config.last_run_status === 'SUCCESS',
  'status-failed': config.last_run_status === 'FAILED',
  'status-running': config.last_run_status === 'RUNNING',
}))

const loadConfig = async () => {
  try {
    const res = await api.scheduleConfig.getConfigs()
    const data = Array.isArray(res.data) ? res.data : [res.data]
    const inv = data.find(d => d.task_name === 'INVENTORY_RECALC')
    if (inv) Object.assign(config, inv)
  } catch (e) {
    console.error('スケジュール設定の取得に失敗', e)
  }
}

const saveConfig = async () => {
  if (!canEdit.value) return
  saving.value = true
  try {
    await api.scheduleConfig.saveConfig({
      task_name: config.task_name,
      scheduled_hour: config.scheduled_hour,
      scheduled_minute: config.scheduled_minute,
      is_enabled: config.is_enabled,
    })
    alert('保存しました。設定は5分以内にスケジューラに反映されます。')
    await loadConfig()
  } catch (e) {
    alert('保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

const runNow = async () => {
  if (!canEdit.value) return
  if (!confirm('取り込み＋在庫再計算を今すぐ実行しますか？\n処理に数分かかる場合があります。')) return
  running.value = true
  try {
    const res = await api.scheduleConfig.runNow()
    alert(`完了しました。\n${res.data?.detail || ''}`)
    await loadConfig()
  } catch (e) {
    alert('実行に失敗しました。')
  } finally {
    running.value = false
  }
}

const formatDateTime = (dt) => {
  if (!dt) return '-'
  const d = new Date(dt)
  return d.toLocaleString('ja-JP')
}

onMounted(loadConfig)
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
.time-input {
  width: 60px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.suffix {
  font-size: 12px;
  color: #333;
}
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
.helper {
  margin: 0;
  font-size: 12px;
  color: #666;
}
.helper.warning {
  color: #b45309;
  margin-top: 8px;
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
  font-size: 13px;
}
.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.last-run {
  margin-top: 16px;
  border-top: 1px solid #e5e9ef;
  padding-top: 12px;
}
.section-title {
  font-size: 13px;
  margin: 0 0 6px;
  font-weight: 600;
}
.info-table {
  font-size: 12px;
  border-collapse: collapse;
  width: 100%;
}
.info-table th {
  text-align: left;
  padding: 4px 8px 4px 0;
  color: #666;
  white-space: nowrap;
  width: 80px;
  vertical-align: top;
}
.info-table td {
  padding: 4px 0;
}
.message-cell {
  white-space: pre-wrap;
  word-break: break-all;
}
.status-success {
  color: #16a34a;
  font-weight: 600;
}
.status-failed {
  color: #dc2626;
  font-weight: 600;
}
.status-running {
  color: #2563eb;
  font-weight: 600;
}
</style>
