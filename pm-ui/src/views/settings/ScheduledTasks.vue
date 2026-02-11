<template>
  <div class="settings-container">
    <h2 class="page-title">定時タスク設定</h2>

    <div class="card">
      <div class="card-header">
        <div>
          <div class="card-title">生産計画自動生成（需要→計画上書き）</div>
          <p class="helper">
            毎月指定日・時刻に需要取り込みのみ実行し、指定月の計画を需要で上書きします。対象月（翌月／翌々月／翌々翌月）をラインごとに選択できます。
          </p>
        </div>
      </div>

      <div class="table-wrapper" v-if="autoPlanConfigs.length">
        <table class="config-table">
          <thead>
            <tr>
              <th style="width: 150px">ライン</th>
              <th style="width: 170px">実行タイミング</th>
              <th style="width: 180px">対象期間</th>
              <th style="width: 80px">有効</th>
              <th style="width: 180px">操作</th>
              <th>最終実行情報</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cfg in autoPlanConfigs" :key="configKey(cfg)">
              <td>
                <div class="line-name">{{ cfg.line_name || 'ライン未設定' }}</div>
                <div v-if="cfg.line_code" class="line-code">({{ cfg.line_code }})</div>
              </td>
              <td>
                <div class="time-row">
                  <input
                    type="number"
                    min="1"
                    max="31"
                    v-model.number="cfg.scheduled_dom"
                    :disabled="!canEdit"
                    class="time-input"
                  />
                  <span class="suffix">日</span>
                </div>
                <div class="time-row">
                  <input
                    type="number"
                    min="0"
                    max="23"
                    v-model.number="cfg.scheduled_hour"
                    :disabled="!canEdit"
                    class="time-input"
                  />
                  <span class="suffix">時</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    v-model.number="cfg.scheduled_minute"
                    :disabled="!canEdit"
                    class="time-input"
                  />
                  <span class="suffix">分</span>
                </div>
              </td>
              <td class="period-cell">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_next_month" :disabled="!canEdit" />
                  翌月
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_second_month" :disabled="!canEdit" />
                  翌々月
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_third_month" :disabled="!canEdit" />
                  翌々翌月
                </label>
              </td>
              <td>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEdit" />
                  有効
                </label>
              </td>
              <td class="actions-cell">
                <button
                  class="btn primary"
                  @click="saveConfig(cfg)"
                  :disabled="saving.has(configKey(cfg)) || !canEdit"
                >
                  {{ saving.has(configKey(cfg)) ? '保存中...' : '保存' }}
                </button>
                <button
                  class="btn"
                  @click="runNow(cfg)"
                  :disabled="running.has(configKey(cfg)) || !canEdit"
                >
                  {{ running.has(configKey(cfg)) ? '実行中...' : '今すぐ実行' }}
                </button>
              </td>
              <td class="last-cell">
                <div class="last-row">
                  <span class="last-label">日時</span>
                  <span>{{ formatDateTime(cfg.last_run_at) }}</span>
                </div>
                <div class="last-row">
                  <span class="last-label">結果</span>
                  <span :class="statusClass(cfg)">{{ cfg.last_run_status_display || '-' }}</span>
                </div>
                <div class="message-cell">{{ cfg.last_run_message || '-' }}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="helper warning">生産ラインの設定が見つかりません。</p>
    </div>

    <div class="card" v-if="inventoryConfig">
      <div class="field">
        <label>取り込み＋在庫再計算 - 実行時刻</label>
        <div class="input-row">
          <input
            type="number"
            min="0"
            max="23"
            v-model.number="inventoryConfig.scheduled_hour"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">時</span>
          <input
            type="number"
            min="0"
            max="59"
            v-model.number="inventoryConfig.scheduled_minute"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">分</span>
        </div>
        <p class="helper">毎日指定した時刻に需要取り込み（pickup）→ 在庫・計画在庫・進度の自動再計算を実行します。</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="inventoryConfig.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="actions">
        <button
          class="btn primary"
          @click="saveConfig(inventoryConfig)"
          :disabled="saving.has(configKey(inventoryConfig)) || !canEdit"
        >
          {{ saving.has(configKey(inventoryConfig)) ? '保存中...' : '保存' }}
        </button>
        <button
          class="btn"
          @click="runNow(inventoryConfig)"
          :disabled="running.has(configKey(inventoryConfig)) || !canEdit"
          style="margin-left: 8px"
        >
          {{ running.has(configKey(inventoryConfig)) ? '実行中...' : '今すぐ実行' }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="inventoryConfig.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(inventoryConfig.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass(inventoryConfig)">{{ inventoryConfig.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ inventoryConfig.last_run_duration_seconds != null ? inventoryConfig.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ inventoryConfig.last_run_message || '-' }}</td>
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

const configs = ref([])
const saving = reactive(new Set())
const running = reactive(new Set())
const canEdit = computed(() => hasPermission(authState.user, 'settings', 'edit'))

const autoPlanConfigs = computed(() =>
  configs.value
    .filter((cfg) => cfg.task_name === 'AUTO_PLAN')
    .sort((a, b) => (a.line_code || '').localeCompare(b.line_code || ''))
)
const inventoryConfig = computed(() => configs.value.find((cfg) => cfg.task_name === 'INVENTORY_RECALC'))

const statusClass = (cfg) => ({
  'status-success': cfg.last_run_status === 'SUCCESS',
  'status-failed': cfg.last_run_status === 'FAILED',
  'status-running': cfg.last_run_status === 'RUNNING',
})

const configKey = (cfg) => `${cfg.task_name}-${cfg.line || 'none'}-${cfg.id || 'new'}`

const loadConfig = async () => {
  try {
    const res = await api.scheduleConfig.getConfigs()
    const data = Array.isArray(res.data) ? res.data : [res.data]
    configs.value = data
  } catch (e) {
    console.error('スケジュール設定の取得に失敗', e)
  }
}

const saveConfig = async (cfg) => {
  if (!canEdit.value) return
  const key = configKey(cfg)
  saving.add(key)
  try {
    await api.scheduleConfig.saveConfig({
      id: cfg.id,
      task_name: cfg.task_name,
      line: cfg.line,
      scheduled_hour: cfg.scheduled_hour,
      scheduled_minute: cfg.scheduled_minute,
      scheduled_dom: cfg.scheduled_dom,
      is_enabled: cfg.is_enabled,
      include_next_month: cfg.include_next_month,
      include_second_month: cfg.include_second_month,
      include_third_month: cfg.include_third_month,
    })
    alert('保存しました。設定は5分以内にスケジューラに反映されます。')
    await loadConfig()
  } catch (e) {
    alert('保存に失敗しました。')
  } finally {
    saving.delete(key)
  }
}

const runNow = async (cfg) => {
  if (!canEdit.value) return
  const key = configKey(cfg)
  const targetName =
    cfg.task_name === 'AUTO_PLAN'
      ? `生産計画自動生成（${cfg.line_name || cfg.line_code || 'ライン未設定'}）`
      : '取り込み＋在庫再計算'
  const msg =
    cfg.task_name === 'AUTO_PLAN'
      ? `${targetName}を今すぐ実行しますか？`
      : '取り込み＋在庫再計算を今すぐ実行しますか？\n処理に数分かかる場合があります。'
  if (!confirm(msg)) return

  running.add(key)
  try {
    const res = await api.scheduleConfig.runNow({ task_name: cfg.task_name, config_id: cfg.id, line: cfg.line })
    alert(`完了しました。\n${res.data?.detail || ''}`)
    await loadConfig()
  } catch (e) {
    alert('実行に失敗しました。')
  } finally {
    running.delete(key)
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
  max-width: 100%;
  margin-bottom: 12px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.card-title {
  font-size: 14px;
  font-weight: 700;
  margin: 0 0 4px;
}
.table-wrapper {
  overflow-x: auto;
}
.config-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.config-table th {
  text-align: left;
  padding: 6px 6px;
  color: #444;
  border-bottom: 1px solid #e5e9ef;
  white-space: nowrap;
}
.config-table td {
  padding: 8px 6px;
  border-bottom: 1px solid #e5e9ef;
  vertical-align: top;
}
.line-name {
  font-weight: 700;
  color: #1f2a44;
}
.line-code {
  font-size: 11px;
  color: #6b7280;
}
.time-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.time-row:last-child {
  margin-bottom: 0;
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
  font-size: 12px;
}
.period-cell .checkbox-label {
  margin-bottom: 4px;
}
.period-cell .checkbox-label:last-child {
  margin-bottom: 0;
}
.actions-cell {
  display: flex;
  gap: 8px;
}
.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
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
.last-cell {
  font-size: 12px;
  color: #374151;
}
.last-row {
  display: flex;
  gap: 6px;
  margin-bottom: 4px;
  align-items: center;
}
.last-label {
  color: #6b7280;
  min-width: 32px;
}
.message-cell {
  white-space: pre-wrap;
  word-break: break-all;
  color: #111827;
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
