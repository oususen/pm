<template>
  <div class="settings-container">
    <h2 class="page-title">定時タスク設定</h2>

    <div class="card" v-if="showAutoPlanSection">
      <div class="card-header">
        <div>
          <div class="card-title">生産計画自動生成（需要→計画上書き）</div>
          <p class="helper">
            毎月指定日・時刻に需要取り込みのみ実行し、指定月の計画を需要で上書きします。対象月（今月／翌月／翌々月／翌々翌月）をラインごとに選択できます。
          </p>
          <p v-if="autoPlanLocked" class="helper warning">
            順序運用モードのため、この画面の自動計画設定は読み取り専用です。編集は「自動計画」画面で行ってください。
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
              <th style="width: 200px">失敗時通知先</th>
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
                    :disabled="!canEditAutoPlan"
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
                    :disabled="!canEditAutoPlan"
                    class="time-input"
                  />
                  <span class="suffix">時</span>
                  <input
                    type="number"
                    min="0"
                    max="59"
                    v-model.number="cfg.scheduled_minute"
                    :disabled="!canEditAutoPlan"
                    class="time-input"
                  />
                  <span class="suffix">分</span>
                </div>
              </td>
              <td class="period-cell">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_current_month" :disabled="!canEditAutoPlan" />
                  今月
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_next_month" :disabled="!canEditAutoPlan" />
                  翌月
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_second_month" :disabled="!canEditAutoPlan" />
                  翌々月
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.include_third_month" :disabled="!canEditAutoPlan" />
                  翌々翌月
                </label>
              </td>
              <td>
                <label class="checkbox-label">
                  <input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEditAutoPlan" />
                  有効
                </label>
              </td>
              <td class="notify-cell">
                <div class="notify-search">
                  <input
                    v-model="cfg.searchCode"
                    :disabled="!canEditAutoPlan"
                    class="notify-search-input"
                    placeholder="社員コード/氏名/ユーザー名で検索して追加"
                    @keyup.enter.prevent="addFirstCandidate(cfg)"
                  />
                </div>
                <div
                  v-if="candidateList(cfg).length"
                  class="candidate-list"
                >
                  <div
                    v-for="u in candidateList(cfg)"
                    :key="u.id"
                    class="candidate-item"
                    @click="addUser(cfg, u)"
                  >
                    <span class="candidate-code">{{ codeLabel(u) }}</span>
                    <span class="candidate-name">{{ nameLabel(u) }}</span>
                  </div>
                </div>
                <div class="selected-list" v-if="cfg.notify_user_codes.length">
                  <span
                    class="chip"
                    v-for="code in cfg.notify_user_codes"
                    :key="code"
                  >
                    <span class="chip-code">{{ code }}</span>
                    <span class="chip-name">{{ chipName(cfg, code) }}</span>
                    <button
                      type="button"
                      class="chip-remove"
                      :disabled="!canEditAutoPlan"
                      @click="removeCode(cfg, code)"
                    >
                      ×
                    </button>
                  </span>
                </div>
              </td>
              <td class="actions-cell">
                <button
                  class="btn primary"
                  @click="saveConfig(cfg)"
                  :disabled="saving.has(configKey(cfg)) || !canEditAutoPlan"
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

    <template v-if="showInventorySection">
    <div class="card" v-for="cfg in inventoryTaskConfigs" :key="configKey(cfg)">
      <div class="field">
        <label>{{ inventoryTaskLabel(cfg.task_name) }} - 実行時刻</label>
        <div class="input-row">
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
        <p class="helper">{{ inventoryTaskHelp(cfg.task_name) }}</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label>{{ showRangeBaseDay(cfg.task_name) ? '計算期間' : '対象期間' }}</label>
        <div class="input-row">
          <template v-if="showRangeBaseDay(cfg.task_name)">
            <select v-model="cfg.range_base_day" :disabled="!canEdit" class="date-input">
              <option value="TODAY">今日</option>
              <option value="YESTERDAY">昨日</option>
              <option value="TWO_DAYS_AGO">一昨日</option>
            </select>
            <span class="suffix">から</span>
          </template>
          <template v-else>
            <span class="suffix">今日から</span>
          </template>
          <input
            type="number"
            min="0"
            max="365"
            v-model.number="cfg.range_days_after"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">日後</span>
        </div>
        <p class="helper">例: 今日から45日後まで。業務日付は8時境界です。</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="actions">
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
          style="margin-left: 8px"
        >
          {{ running.has(configKey(cfg)) ? '実行中...' : '今すぐ実行' }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="cfg.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(cfg.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass(cfg)">{{ cfg.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ cfg.last_run_duration_seconds != null ? cfg.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ cfg.last_run_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    </template>

    <template v-if="showSafetyStockSection">
    <div class="card" v-for="cfg in safetyStockConfigs" :key="configKey(cfg)">
      <div class="field">
        <label>{{ safetyStockTaskLabel(cfg.task_name) }} - 実行日・時刻</label>
        <div class="input-row">
          <input
            type="number"
            min="1"
            max="31"
            v-model.number="cfg.scheduled_dom"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">日</span>
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
      </div>

      <div class="field" style="margin-top: 12px">
        <label>実行日から何日間の平均日あたりを計算</label>
        <div class="input-row">
          <input
            type="number"
            min="1"
            max="365"
            v-model.number="cfg.average_days_window"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">日</span>
        </div>
      </div>

      <div class="field" style="margin-top: 12px">
        <label>上記の日当たりの何日分を安全在庫とする</label>
        <div class="input-row">
          <input
            type="number"
            min="1"
            max="365"
            v-model.number="cfg.safety_days"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">日分</span>
        </div>
        <p class="helper">算出式: （実行日からの平均日あたり）×（安全在庫日数）で最小在庫数を更新します。</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="actions">
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
          style="margin-left: 8px"
        >
          {{ running.has(configKey(cfg)) ? '実行中...' : '今すぐ実行' }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="cfg.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(cfg.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass(cfg)">{{ cfg.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ cfg.last_run_duration_seconds != null ? cfg.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ cfg.last_run_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    </template>

    <div class="card" v-if="orderExpansionConfig && showOrderExpansionSection">
      <div class="field">
        <label>自動受注展開 - 実行時刻</label>
        <div class="input-row">
          <input
            type="number"
            min="0"
            max="23"
            v-model.number="orderExpansionConfig.scheduled_hour"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">時</span>
          <input
            type="number"
            min="0"
            max="59"
            v-model.number="orderExpansionConfig.scheduled_minute"
            :disabled="!canEdit"
            class="time-input"
          />
          <span class="suffix">分</span>
        </div>
        <p class="helper">毎日指定した時刻にOPEN受注をLineDemandへ自動展開します。</p>
      </div>

      <div class="field" style="margin-top: 12px">
        <label class="checkbox-label">
          <input type="checkbox" v-model="orderExpansionConfig.is_enabled" :disabled="!canEdit" />
          有効
        </label>
      </div>

      <div class="actions">
        <button
          class="btn primary"
          @click="saveConfig(orderExpansionConfig)"
          :disabled="saving.has(configKey(orderExpansionConfig)) || !canEdit"
        >
          {{ saving.has(configKey(orderExpansionConfig)) ? '保存中...' : '保存' }}
        </button>
        <button
          class="btn"
          @click="runNow(orderExpansionConfig)"
          :disabled="running.has(configKey(orderExpansionConfig)) || !canEdit"
          style="margin-left: 8px"
        >
          {{ running.has(configKey(orderExpansionConfig)) ? '実行中...' : '今すぐ実行' }}
        </button>
      </div>

      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>

      <div v-if="orderExpansionConfig.last_run_at" class="last-run">
        <h3 class="section-title">最終実行情報</h3>
        <table class="info-table">
          <tbody>
            <tr>
              <th>実行日時</th>
              <td>{{ formatDateTime(orderExpansionConfig.last_run_at) }}</td>
            </tr>
            <tr>
              <th>結果</th>
              <td>
                <span :class="statusClass(orderExpansionConfig)">{{ orderExpansionConfig.last_run_status_display || '-' }}</span>
              </td>
            </tr>
            <tr>
              <th>実行時間</th>
              <td>{{ orderExpansionConfig.last_run_duration_seconds != null ? orderExpansionConfig.last_run_duration_seconds + '秒' : '-' }}</td>
            </tr>
            <tr>
              <th>詳細</th>
              <td class="message-cell">{{ orderExpansionConfig.last_run_message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const route = useRoute()
const configs = ref([])
const saving = reactive(new Set())
const running = reactive(new Set())
const canEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true

  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : []
  if (permissions.some((item) => item.resource === 'settings.scheduled_tasks')) {
    return hasPermission(user, 'settings.scheduled_tasks', 'edit')
  }
  return hasPermission(user, 'settings', 'edit')
})
const userList = ref([])

const autoPlanConfigs = computed(() =>
  configs.value
    .filter((cfg) => cfg.task_name === 'AUTO_PLAN')
    .sort((a, b) => (a.line_code || '').localeCompare(b.line_code || ''))
)
const inventoryTaskOrder = ['INVENTORY_RECALC', 'PICKUP_ONLY', 'INVENTORY_ONLY', 'PROGRESS_ONLY']
const inventoryTaskConfigs = computed(() =>
  configs.value
    .filter((cfg) => inventoryTaskOrder.includes(cfg.task_name))
    .sort((a, b) => inventoryTaskOrder.indexOf(a.task_name) - inventoryTaskOrder.indexOf(b.task_name))
)
const safetyStockTaskOrder = ['AUTO_SAFETY_STOCK_INTERNAL', 'AUTO_SAFETY_STOCK_PURCHASE']
const safetyStockConfigs = computed(() =>
  configs.value
    .filter((cfg) => safetyStockTaskOrder.includes(cfg.task_name))
    .sort((a, b) => safetyStockTaskOrder.indexOf(a.task_name) - safetyStockTaskOrder.indexOf(b.task_name))
)
const orderExpansionConfig = computed(() => configs.value.find((cfg) => cfg.task_name === 'ORDER_EXPANSION'))
const showAutoPlanSection = computed(() => {
  const mode = String(route.query?.mode || '').toLowerCase()
  return mode !== 'inventory' && mode !== 'order-expansion' && mode !== 'safety-stock'
})
const showInventorySection = computed(() => {
  const mode = String(route.query?.mode || '').toLowerCase()
  return mode === '' || mode === 'inventory'
})
const showSafetyStockSection = computed(() => {
  const mode = String(route.query?.mode || '').toLowerCase()
  return mode === '' || mode === 'safety-stock'
})
const showOrderExpansionSection = computed(() => {
  const mode = String(route.query?.mode || '').toLowerCase()
  return mode === '' || mode === 'order-expansion'
})
const autoPlanLocked = computed(() =>
  autoPlanConfigs.value.some((cfg) => cfg.auto_plan_sequence_locked)
)
const canEditAutoPlan = computed(() => canEdit.value && !autoPlanLocked.value)

const statusClass = (cfg) => ({
  'status-success': cfg.last_run_status === 'SUCCESS',
  'status-failed': cfg.last_run_status === 'FAILED',
  'status-running': cfg.last_run_status === 'RUNNING',
})

const inventoryTaskLabel = (taskName) => {
  if (taskName === 'PICKUP_ONLY') return '取り込みのみ'
  if (taskName === 'INVENTORY_ONLY') return '在庫計算のみ'
  if (taskName === 'PROGRESS_ONLY') return '進度計算のみ'
  return '取り込み＋在庫再計算'
}

const inventoryTaskHelp = (taskName) => {
  if (taskName === 'PICKUP_ONLY') return '毎日指定した時刻に需要取り込み（pickup / pickup_purchase）のみを実行します。'
  if (taskName === 'INVENTORY_ONLY') return '毎日指定した時刻に在庫・計画在庫の再計算のみを実行します（必要に応じて過去営業日まで遡って再計算、進度は更新しません）。'
  if (taskName === 'PROGRESS_ONLY') return '毎日指定した時刻に進度のみを再計算します（必要に応じてLT+1営業日前まで遡って再計算します）。'
  return '毎日指定した時刻に需要取り込み（pickup）→ 在庫・計画在庫・進度の自動再計算を実行します。'
}
const isSafetyStockTask = (taskName) => safetyStockTaskOrder.includes(taskName)
const safetyStockTaskLabel = (taskName) => {
  if (taskName === 'AUTO_SAFETY_STOCK_PURCHASE') return '自動安全在庫（購入品）'
  return '自動安全在庫（社内）'
}

const showRangeBaseDay = (taskName) => taskName === 'INVENTORY_RECALC' || taskName === 'PICKUP_ONLY'

const configKey = (cfg) => `${cfg.task_name}-${cfg.line || 'none'}-${cfg.id || 'new'}`

const loadConfig = async () => {
  try {
    const res = await api.scheduleConfig.getConfigs()
    const data = Array.isArray(res.data) ? res.data : [res.data]
    configs.value = data.map((cfg) => ({
      ...cfg,
      average_days_window: Number.isFinite(Number(cfg.average_days_window)) ? Number(cfg.average_days_window) : 60,
      safety_days: Number.isFinite(Number(cfg.safety_days)) ? Number(cfg.safety_days) : 1,
      notify_users: cfg.notify_users || [],
      notify_user_codes: cfg.notify_user_codes || [],
      notify_user_names: cfg.notify_user_names || {},
      searchCode: '',
    }))
  } catch (e) {
    console.error('スケジュール設定の取得に失敗', e)
  }
}

const loadUsers = async () => {
  try {
    const res = await api.accounts.getUsers({ is_active: true })
    userList.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('ユーザー一覧の取得に失敗', e)
  }
}

const saveConfig = async (cfg) => {
  if (!canEdit.value) return
  if (cfg.task_name === 'AUTO_PLAN' && autoPlanLocked.value) {
    alert('順序運用モード中のため、この画面では自動計画設定を編集できません。')
    return
  }
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
      range_start_date: null,
      range_end_date: null,
      range_base_day: showRangeBaseDay(cfg.task_name) ? (cfg.range_base_day || 'TODAY') : 'TODAY',
      range_days_after: Number.isFinite(Number(cfg.range_days_after)) ? Number(cfg.range_days_after) : 45,
      average_days_window: Number.isFinite(Number(cfg.average_days_window)) ? Number(cfg.average_days_window) : 60,
      safety_days: Number.isFinite(Number(cfg.safety_days)) ? Number(cfg.safety_days) : 1,
      is_enabled: cfg.is_enabled,
      include_current_month: cfg.include_current_month,
      include_next_month: cfg.include_next_month,
      include_second_month: cfg.include_second_month,
      include_third_month: cfg.include_third_month,
      notify_user_codes: cfg.notify_user_codes,
    })
    alert('保存しました。設定は5分以内にスケジューラに反映されます。')
    await loadConfig()
  } catch (e) {
    alert('保存に失敗しました。')
  } finally {
    saving.delete(key)
  }
}

const pollTimer = ref(null)

const stopPolling = () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

const runNow = async (cfg) => {
  if (!canEdit.value) return
  const key = configKey(cfg)
  const targetName =
    cfg.task_name === 'AUTO_PLAN'
      ? `生産計画自動生成（${cfg.line_name || cfg.line_code || 'ライン未設定'}）`
      : cfg.task_name === 'ORDER_EXPANSION'
        ? '自動受注展開'
        : isSafetyStockTask(cfg.task_name)
          ? safetyStockTaskLabel(cfg.task_name)
        : inventoryTaskLabel(cfg.task_name)
  const msg =
    cfg.task_name === 'AUTO_PLAN'
      ? `${targetName}を今すぐ実行しますか？`
      : cfg.task_name === 'ORDER_EXPANSION'
        ? '自動受注展開を今すぐ実行しますか？'
        : isSafetyStockTask(cfg.task_name)
          ? `${safetyStockTaskLabel(cfg.task_name)}を今すぐ実行しますか？\nバックグラウンドで実行されます。`
        : `${inventoryTaskLabel(cfg.task_name)}を今すぐ実行しますか？\nバックグラウンドで実行されます。`
  if (!confirm(msg)) return

  running.add(key)
  try {
    const res = await api.scheduleConfig.runNow({ task_name: cfg.task_name, config_id: cfg.id, line: cfg.line })
    // 非同期実行の場合はポーリングで完了を待つ
    if (res.data?.async) {
      await loadConfig()
      stopPolling()
      const pollStart = Date.now()
      const POLL_TIMEOUT = 10 * 60 * 1000 // 10分
      pollTimer.value = setInterval(async () => {
        // タイムアウト: 10分でポーリング停止
        if (Date.now() - pollStart > POLL_TIMEOUT) {
          stopPolling()
          running.delete(key)
          alert('タイムアウト：10分経過しても完了しませんでした。\n画面をリロードして最新状態を確認してください。')
          return
        }
        await loadConfig()
        const updated = configs.value.find((c) => c.task_name === cfg.task_name && c.line === cfg.line)
        if (updated && updated.last_run_status !== 'RUNNING') {
          stopPolling()
          running.delete(key)
          const statusLabel = updated.last_run_status === 'SUCCESS' ? '成功' : '失敗'
          alert(`${targetName}が完了しました（${statusLabel}）\n${updated.last_run_message || ''}`)
        }
      }, 5000)
    } else {
      alert(`完了しました。\n${res.data?.detail || ''}`)
      await loadConfig()
      running.delete(key)
    }
  } catch (e) {
    running.delete(key)
    if (e.response?.status === 409) {
      alert(e.response.data?.detail || '既に実行中です。')
    } else {
      alert('実行に失敗しました。')
    }
  }
}

const formatDateTime = (dt) => {
  if (!dt) return '-'
  const d = new Date(dt)
  return d.toLocaleString('ja-JP')
}

const codeLabel = (u) => u?.profile?.employee_code || u.username || u.email || `ID:${u.id}`

const nameLabel = (u) => {
  const name = `${u.last_name || ''}${u.first_name || ''}`.trim()
  return name || u.username || u.email || `ID:${u.id}`
}

const candidateList = (cfg) => {
  const kw = (cfg.searchCode || '').trim().toLowerCase()
  if (!kw) return []
  return userList.value
    .filter((u) => {
      const code = codeLabel(u).toLowerCase()
      const name = nameLabel(u).toLowerCase()
      return code.includes(kw) || name.includes(kw)
    })
    .slice(0, 10)
}

const chipName = (cfg, code) => {
  if (cfg.notify_user_names && cfg.notify_user_names[code]) return cfg.notify_user_names[code]
  const user = userList.value.find((u) => codeLabel(u) === code)
  return user ? nameLabel(user) : ''
}

const addUser = (cfg, user) => {
  const code = codeLabel(user)
  if (!cfg.notify_user_codes.includes(code)) {
    cfg.notify_user_codes = [...cfg.notify_user_codes, code]
    cfg.notify_user_names = {
      ...(cfg.notify_user_names || {}),
      [code]: nameLabel(user),
    }
  }
  cfg.searchCode = ''
}

const addFirstCandidate = (cfg) => {
  const first = candidateList(cfg)[0]
  if (first) addUser(cfg, first)
}

const removeCode = (cfg, code) => {
  cfg.notify_user_codes = cfg.notify_user_codes.filter((c) => c !== code)
  if (cfg.notify_user_names) {
    const names = { ...cfg.notify_user_names }
    delete names[code]
    cfg.notify_user_names = names
  }
}

const startPollingIfRunning = () => {
  const pollTargets = [...inventoryTaskConfigs.value, ...safetyStockConfigs.value]
  const runningTask = pollTargets.find((cfg) => cfg.last_run_status === 'RUNNING')
  if (!runningTask) return
  if (runningTask.last_run_at) {
    const elapsed = Date.now() - new Date(runningTask.last_run_at).getTime()
    if (elapsed > 10 * 60 * 1000) return
  }
  const key = configKey(runningTask)
  running.add(key)
  stopPolling()
  const pollStart = Date.now()
  const POLL_TIMEOUT = 10 * 60 * 1000
  pollTimer.value = setInterval(async () => {
    if (Date.now() - pollStart > POLL_TIMEOUT) {
      stopPolling()
      running.delete(key)
      return
    }
    await loadConfig()
    const updated = [...inventoryTaskConfigs.value, ...safetyStockConfigs.value].find((cfg) => configKey(cfg) === key)
    if (updated && updated.last_run_status !== 'RUNNING') {
      stopPolling()
      running.delete(key)
    }
  }, 5000)
}

onMounted(async () => {
  await loadConfig()
  loadUsers()
  startPollingIfRunning()
})

onUnmounted(() => {
  stopPolling()
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
.date-input {
  width: 160px;
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
.notify-select {
  width: 100%;
  min-height: 60px;
  font-size: 12px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.notify-cell {
  min-width: 200px;
}
.notify-search-input {
  width: 100%;
  padding: 6px 8px;
  font-size: 12px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.candidate-list {
  border: 1px solid #e5e9ef;
  border-radius: 4px;
  margin-top: 6px;
  max-height: 160px;
  overflow: auto;
  background: #fff;
}
.candidate-item {
  padding: 6px 8px;
  display: flex;
  gap: 8px;
  align-items: center;
  cursor: pointer;
}
.candidate-item:hover {
  background: #f3f6fb;
}
.candidate-code {
  font-weight: 700;
  color: #1f2a44;
  min-width: 80px;
}
.candidate-name {
  color: #444;
  font-size: 12px;
}
.selected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.chip {
  background: #eef2f6;
  border: 1px solid #cfd6e1;
  border-radius: 14px;
  padding: 4px 8px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.chip-code {
  font-weight: 700;
}
.chip-name {
  color: #4b5563;
}
.chip-remove {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  padding: 0 2px;
  color: #6b7280;
}
.chip-remove:disabled {
  cursor: not-allowed;
  color: #9ca3af;
}
.notify-input {
  width: 100%;
  min-height: 60px;
  font-size: 12px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
  padding: 6px 8px;
  resize: vertical;
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
