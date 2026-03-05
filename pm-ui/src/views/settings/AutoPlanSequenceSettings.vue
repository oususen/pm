<template>
  <div class="settings-container">
    <h2 class="page-title">自動計画設定</h2>
    <div v-if="!canView" class="card no-permission">
      この画面を開く権限がありません。
    </div>
    <div v-else class="two-col">
      <div class="col">
        <div class="card">
          <div class="field">
            <label>ライン別設定（社内生産ライン）</label>
          </div>

          <div class="table-wrapper" v-if="prodConfigsByLine.length">
            <table class="line-table">
              <thead>
                <tr>
                  <th>ライン</th>
                  <th>対象月</th>
                  <th>有効</th>
                  <th>失敗時通知先</th>
                  <th>個別実行</th>
                  <th>最終実行情報</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cfg in prodConfigsByLine" :key="cfg.id">
                  <td>{{ cfg.line_code }} {{ cfg.line_name }}</td>
                  <td>
                    <div class="period-cell">
                      <label class="checkbox-label"><input type="checkbox" v-model="cfg.include_current_month" :disabled="!canEdit" />今月</label>
                      <label class="checkbox-label"><input type="checkbox" v-model="cfg.include_next_month" :disabled="!canEdit" />翌月</label>
                      <label class="checkbox-label"><input type="checkbox" v-model="cfg.include_second_month" :disabled="!canEdit" />翌々月</label>
                      <label class="checkbox-label"><input type="checkbox" v-model="cfg.include_third_month" :disabled="!canEdit" />翌々翌月</label>
                    </div>
                  </td>
                  <td><label class="checkbox-label"><input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEdit" />有効</label></td>
                  <td class="notify-cell">
                    <div class="notify-search">
                      <input
                        v-model="cfg.searchCode"
                        :disabled="!canEdit"
                        class="notify-search-input"
                        placeholder="社員コード/氏名/ユーザー名で検索して追加"
                        @keyup.enter.prevent="addFirstCandidate(cfg)"
                      />
                    </div>
                    <div v-if="candidateList(cfg).length" class="candidate-list">
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
                    <div class="selected-list" v-if="cfg.notify_user_codes?.length">
                      <span class="chip" v-for="code in cfg.notify_user_codes" :key="code">
                        <span class="chip-code">{{ code }}</span>
                        <span class="chip-name">{{ chipName(cfg, code) }}</span>
                        <button
                          type="button"
                          class="chip-remove"
                          :disabled="!canEdit"
                          @click="removeCode(cfg, code)"
                        >
                          ×
                        </button>
                      </span>
                    </div>
                  </td>
                  <td><button class="btn mini" :disabled="!canEdit || runningOne === cfg.id" @click="runNowOne(cfg)">{{ runningOne === cfg.id ? '実行中...' : '今すぐ実行' }}</button></td>
                  <td class="last-cell">
                    <div class="last-row"><span class="last-label">日時</span><span>{{ formatDateTime(cfg.last_run_at) }}</span></div>
                    <div class="last-row"><span class="last-label">結果</span><span :class="statusClass(cfg)">{{ cfg.last_run_status_display || '-' }}</span></div>
                    <div class="message-cell">{{ cfg.last_run_message || '-' }}</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="helper">社内生産ラインの設定データがありません。</p>
        </div>

        <div class="card">
          <div class="field">
            <label>実行タイミング・順序設定（社内生産ライン）</label>
            <div class="input-row">
              <input v-model.number="scheduledDomProd" type="number" min="1" max="31" :disabled="!canEdit" class="time-input" />
              <span class="suffix">日</span>
              <input v-model.number="scheduledHourProd" type="number" min="0" max="23" :disabled="!canEdit" class="time-input" />
              <span class="suffix">時</span>
              <input v-model.number="scheduledMinuteProd" type="number" min="0" max="59" :disabled="!canEdit" class="time-input" />
              <span class="suffix">分</span>
            </div>
          </div>
          <div class="field">
            <label>ライン追加（社内）</label>
            <div class="input-row">
              <select v-model="lineToAddProd" :disabled="!canEdit" class="line-select">
                <option value="">ラインを選択</option>
                <option v-for="line in addableProdLines" :key="line.line" :value="line.line">{{ line.line_code }} {{ line.line_name }}</option>
              </select>
              <button class="btn" :disabled="!canEdit || !lineToAddProd" @click="addLineProd">追加</button>
            </div>
          </div>
          <div class="field">
            <label>実行順（社内・上から順に実行）</label>
            <div class="order-list">
              <div v-for="(cfg, idx) in selectedProdConfigs" :key="cfg.id" class="order-item">
                <div class="order-label">{{ idx + 1 }}. {{ cfg.line_code }} {{ cfg.line_name }}</div>
                <div class="order-actions">
                  <button class="btn mini" :disabled="!canEdit || idx === 0" @click="moveUpProd(idx)">↑</button>
                  <button class="btn mini" :disabled="!canEdit || idx === selectedProdConfigs.length - 1" @click="moveDownProd(idx)">↓</button>
                  <button class="btn mini danger" :disabled="!canEdit" @click="removeLine(cfg.line)">削除</button>
                </div>
              </div>
              <p v-if="!selectedProdConfigs.length" class="helper">社内ラインが未設定です。</p>
            </div>
          </div>
        </div>
      </div>

      <div class="col">
        <div class="card">
          <div class="field">
            <label>ライン別設定（外作・購入品ライン）</label>
          </div>

          <div class="table-wrapper" v-if="extConfigsByLine.length">
            <table class="line-table">
              <thead>
                <tr>
                  <th>ライン</th>
                  <th>区分</th>
                  <th>対象月</th>
                  <th>有効</th>
                  <th>失敗時通知先</th>
                  <th>個別実行</th>
                  <th>最終実行情報</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cfg in extConfigsByLine" :key="cfg.id">
                  <td>{{ cfg.line_code }} {{ cfg.line_name }}</td>
                  <td>{{ lineTypeLabel(cfg.line_type) }}</td>
                  <td>
                    <div class="period-cell">
                      <label class="checkbox-label"><input type="checkbox" v-model="cfg.include_current_month" :disabled="!canEdit" />今月</label>
                      <label class="checkbox-label"><input type="checkbox" v-model="cfg.include_next_month" :disabled="!canEdit" />翌月</label>
                      <label class="checkbox-label"><input type="checkbox" v-model="cfg.include_second_month" :disabled="!canEdit" />翌々月</label>
                      <label class="checkbox-label"><input type="checkbox" v-model="cfg.include_third_month" :disabled="!canEdit" />翌々翌月</label>
                    </div>
                  </td>
                  <td><label class="checkbox-label"><input type="checkbox" v-model="cfg.is_enabled" :disabled="!canEdit" />有効</label></td>
                  <td class="notify-cell">
                    <div class="notify-search">
                      <input
                        v-model="cfg.searchCode"
                        :disabled="!canEdit"
                        class="notify-search-input"
                        placeholder="社員コード/氏名/ユーザー名で検索して追加"
                        @keyup.enter.prevent="addFirstCandidate(cfg)"
                      />
                    </div>
                    <div v-if="candidateList(cfg).length" class="candidate-list">
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
                    <div class="selected-list" v-if="cfg.notify_user_codes?.length">
                      <span class="chip" v-for="code in cfg.notify_user_codes" :key="code">
                        <span class="chip-code">{{ code }}</span>
                        <span class="chip-name">{{ chipName(cfg, code) }}</span>
                        <button
                          type="button"
                          class="chip-remove"
                          :disabled="!canEdit"
                          @click="removeCode(cfg, code)"
                        >
                          ×
                        </button>
                      </span>
                    </div>
                  </td>
                  <td><button class="btn mini" :disabled="!canEdit || runningOne === cfg.id" @click="runNowOne(cfg)">{{ runningOne === cfg.id ? '実行中...' : '今すぐ実行' }}</button></td>
                  <td class="last-cell">
                    <div class="last-row"><span class="last-label">日時</span><span>{{ formatDateTime(cfg.last_run_at) }}</span></div>
                    <div class="last-row"><span class="last-label">結果</span><span :class="statusClass(cfg)">{{ cfg.last_run_status_display || '-' }}</span></div>
                    <div class="message-cell">{{ cfg.last_run_message || '-' }}</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="helper">外作・購入品ラインの設定データがありません。</p>
        </div>

        <div class="card">
          <div class="field">
            <label>実行タイミング・順序設定（外作・購入品ライン）</label>
            <div class="input-row">
              <input v-model.number="scheduledDomExt" type="number" min="1" max="31" :disabled="!canEdit" class="time-input" />
              <span class="suffix">日</span>
              <input v-model.number="scheduledHourExt" type="number" min="0" max="23" :disabled="!canEdit" class="time-input" />
              <span class="suffix">時</span>
              <input v-model.number="scheduledMinuteExt" type="number" min="0" max="59" :disabled="!canEdit" class="time-input" />
              <span class="suffix">分</span>
            </div>
          </div>
          <div class="field">
            <label>ライン追加（外作・購入）</label>
            <div class="input-row">
              <select v-model="lineToAddExt" :disabled="!canEdit" class="line-select">
                <option value="">ラインを選択</option>
                <option v-for="line in addableExtLines" :key="line.line" :value="line.line">{{ line.line_code }} {{ line.line_name }}</option>
              </select>
              <button class="btn" :disabled="!canEdit || !lineToAddExt" @click="addLineExt">追加</button>
            </div>
          </div>
          <div class="field">
            <label>実行順（外作・購入・上から順に実行）</label>
            <div class="order-list">
              <div v-for="(cfg, idx) in selectedExtConfigs" :key="cfg.id" class="order-item">
                <div class="order-label">{{ idx + 1 }}. {{ cfg.line_code }} {{ cfg.line_name }}</div>
                <div class="order-actions">
                  <button class="btn mini" :disabled="!canEdit || idx === 0" @click="moveUpExt(idx)">↑</button>
                  <button class="btn mini" :disabled="!canEdit || idx === selectedExtConfigs.length - 1" @click="moveDownExt(idx)">↓</button>
                  <button class="btn mini danger" :disabled="!canEdit" @click="removeLine(cfg.line)">削除</button>
                </div>
              </div>
              <p v-if="!selectedExtConfigs.length" class="helper">外作・購入ラインが未設定です。</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="field">
        <div class="actions">
          <button class="btn primary" :disabled="!canEdit || saving" @click="saveAll">
            {{ saving ? '保存中...' : '保存' }}
          </button>
          <button class="btn" :disabled="!canEdit || runningProd" @click="runNowByGroup('prod')">
            {{ runningProd ? '社内実行中...' : '社内 今すぐ実行' }}
          </button>
          <button class="btn" :disabled="!canEdit || runningExt" @click="runNowByGroup('ext')">
            {{ runningExt ? '外作/購入実行中...' : '外作/購入 今すぐ実行' }}
          </button>
          <button class="btn" :disabled="!canEdit || running" @click="runNowAll">
            {{ running ? '全体実行中...' : '全体 今すぐ実行' }}
          </button>
        </div>
        <p class="helper">保存すると、ライン別設定（対象月/有効）と社内/外作購入の各実行タイミング・順序を一括で反映します。</p>
      </div>
    </div>
  </div>
 </template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const configs = ref([])
const lineToAddProd = ref('')
const lineToAddExt = ref('')
const saving = ref(false)
const running = ref(false)
const runningProd = ref(false)
const runningExt = ref(false)
const runningOne = ref(null)
const userList = ref([])
const scheduledDomProd = ref(1)
const scheduledHourProd = ref(3)
const scheduledMinuteProd = ref(0)
const scheduledDomExt = ref(1)
const scheduledHourExt = ref(3)
const scheduledMinuteExt = ref(0)

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

const canView = computed(() => canAccessByResource('settings.scheduled_tasks', 'view'))
const canEdit = computed(() => canAccessByResource('settings.scheduled_tasks', 'edit'))

const autoPlanConfigs = computed(() =>
  configs.value
    .filter((cfg) => cfg.task_name === 'AUTO_PLAN')
    .sort((a, b) => (a.execution_order || 9999) - (b.execution_order || 9999) || (a.line_code || '').localeCompare(b.line_code || ''))
)
const autoPlanConfigsByLine = computed(() =>
  configs.value
    .filter((cfg) => cfg.task_name === 'AUTO_PLAN')
    .sort((a, b) => (a.line_code || '').localeCompare(b.line_code || ''))
)
const isExternalType = (cfg) => ['OUTSOURCE', 'PURCHASE'].includes(String(cfg?.line_type || '').toUpperCase())
const isRightBucket = (cfg) => Number(cfg?.execution_order || 0) >= 1000
const prodConfigsByLine = computed(() => autoPlanConfigsByLine.value.filter((cfg) => !isExternalType(cfg)))
const extConfigsByLine = computed(() => autoPlanConfigsByLine.value.filter((cfg) => isExternalType(cfg)))

const selectedConfigs = computed(() =>
  autoPlanConfigs.value.filter((cfg) => cfg.is_enabled)
)
const selectedProdConfigs = computed(() =>
  selectedConfigs.value
    .filter((cfg) => !isRightBucket(cfg))
    .sort((a, b) => (a.execution_order || 0) - (b.execution_order || 0))
)
const selectedExtConfigs = computed(() =>
  selectedConfigs.value
    .filter((cfg) => isRightBucket(cfg))
    .sort((a, b) => (a.execution_order || 0) - (b.execution_order || 0))
)

const addableProdLines = computed(() => autoPlanConfigs.value.filter((cfg) => !cfg.is_enabled))
const addableExtLines = computed(() => autoPlanConfigs.value.filter((cfg) => !cfg.is_enabled))

const loadConfigs = async () => {
  if (!canView.value) return
  const res = await api.scheduleConfig.getConfigs()
  const rows = Array.isArray(res.data) ? res.data : []
  configs.value = rows.map((r) => ({
    ...r,
    notify_user_codes: Array.isArray(r.notify_user_codes) ? r.notify_user_codes : [],
    notify_user_names: r.notify_user_names || {},
    searchCode: '',
  }))
  const autoRows = rows.filter((r) => r.task_name === 'AUTO_PLAN')
  const prodBase = autoRows.find((r) => !isExternalType(r) && r.is_enabled) || autoRows.find((r) => !isExternalType(r))
  const extBase = autoRows.find((r) => isExternalType(r) && r.is_enabled) || autoRows.find((r) => isExternalType(r))
  if (prodBase) {
    scheduledDomProd.value = prodBase.scheduled_dom || 1
    scheduledHourProd.value = prodBase.scheduled_hour ?? 3
    scheduledMinuteProd.value = prodBase.scheduled_minute ?? 0
  }
  if (extBase) {
    scheduledDomExt.value = extBase.scheduled_dom || 1
    scheduledHourExt.value = extBase.scheduled_hour ?? 3
    scheduledMinuteExt.value = extBase.scheduled_minute ?? 0
  }

  // 旧データ（連番のみ）から左右バケットへ補正
  const enabled = configs.value.filter((c) => c.task_name === 'AUTO_PLAN' && c.is_enabled)
  const hasRightBucket = enabled.some((c) => isRightBucket(c))
  if (!hasRightBucket) {
    let leftNo = 1
    let rightNo = 1000
    const sorted = [...enabled].sort((a, b) => (a.execution_order || 9999) - (b.execution_order || 9999))
    for (const cfg of sorted) {
      if (isExternalType(cfg)) {
        cfg.execution_order = rightNo++
      } else {
        cfg.execution_order = leftNo++
      }
    }
  }
}

const loadUsers = async () => {
  if (!canView.value) return
  try {
    const res = await api.accounts.getUsers({ is_active: true })
    userList.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('ユーザー一覧の取得に失敗', e)
  }
}

const findConfig = (lineId) => configs.value.find((cfg) => String(cfg.line) === String(lineId) && cfg.task_name === 'AUTO_PLAN')

const addLineProd = () => {
  const cfg = findConfig(lineToAddProd.value)
  if (!cfg) return
  cfg.is_enabled = true
  cfg.execution_order = selectedProdConfigs.value.length + 1
  lineToAddProd.value = ''
  normalizeOrder()
}

const addLineExt = () => {
  const cfg = findConfig(lineToAddExt.value)
  if (!cfg) return
  cfg.is_enabled = true
  cfg.execution_order = 1000 + selectedExtConfigs.value.length
  lineToAddExt.value = ''
  normalizeOrder()
}

const removeLine = (lineId) => {
  const cfg = findConfig(lineId)
  if (!cfg) return
  cfg.is_enabled = false
  cfg.execution_order = 9999
  normalizeOrder()
}

const normalizeOrder = () => {
  // 実行順は左ブロック(1〜)→右ブロック(1000〜)で固定
  selectedProdConfigs.value.forEach((cfg, idx) => {
    cfg.execution_order = idx + 1
  })
  selectedExtConfigs.value.forEach((cfg, idx) => {
    cfg.execution_order = 1000 + idx
  })
}

const moveUpProd = (idx) => {
  const list = selectedProdConfigs.value
  if (idx <= 0) return
  const a = list[idx - 1].execution_order
  list[idx - 1].execution_order = list[idx].execution_order
  list[idx].execution_order = a
  normalizeOrder()
}

const moveDownProd = (idx) => {
  const list = selectedProdConfigs.value
  if (idx >= list.length - 1) return
  const a = list[idx + 1].execution_order
  list[idx + 1].execution_order = list[idx].execution_order
  list[idx].execution_order = a
  normalizeOrder()
}

const moveUpExt = (idx) => {
  const list = selectedExtConfigs.value
  if (idx <= 0) return
  const a = list[idx - 1].execution_order
  list[idx - 1].execution_order = list[idx].execution_order
  list[idx].execution_order = a
  normalizeOrder()
}

const moveDownExt = (idx) => {
  const list = selectedExtConfigs.value
  if (idx >= list.length - 1) return
  const a = list[idx + 1].execution_order
  list[idx + 1].execution_order = list[idx].execution_order
  list[idx].execution_order = a
  normalizeOrder()
}

const saveAll = async () => {
  if (!canEdit.value) return
  saving.value = true
  try {
    normalizeOrder()
    const targets = autoPlanConfigs.value
    for (const cfg of targets) {
      const isRight = isRightBucket(cfg)
      await api.scheduleConfig.saveConfig({
        id: cfg.id,
        task_name: cfg.task_name,
        line: cfg.line,
        scheduled_hour: isRight ? scheduledHourExt.value : scheduledHourProd.value,
        scheduled_minute: isRight ? scheduledMinuteExt.value : scheduledMinuteProd.value,
        scheduled_dom: isRight ? scheduledDomExt.value : scheduledDomProd.value,
        execution_order: cfg.is_enabled ? cfg.execution_order : 9999,
        from_sequence_ui: true,
        range_base_day: cfg.range_base_day || 'TODAY',
        range_days_after: Number.isFinite(Number(cfg.range_days_after)) ? Number(cfg.range_days_after) : 45,
        is_enabled: cfg.is_enabled,
        include_current_month: cfg.include_current_month,
        include_next_month: cfg.include_next_month,
        include_second_month: cfg.include_second_month,
        include_third_month: cfg.include_third_month,
        notify_user_codes: cfg.notify_user_codes || [],
      })
    }
    alert('保存しました。')
    await loadConfigs()
  } catch (e) {
    console.error(e)
    alert('保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

const runNowAll = async () => {
  if (!canEdit.value) return
  if (!confirm('自動計画を設定順で今すぐ実行しますか？')) return
  running.value = true
  try {
    const res = await api.scheduleConfig.runNow({ task_name: 'AUTO_PLAN' })
    const executed = Number(res?.data?.executed || 0)
    const success = res?.data?.success
    if (success === false) {
      alert(`実行完了（一部失敗の可能性あり）\n実行件数: ${executed}`)
    } else {
      alert(`実行完了\n実行件数: ${executed}`)
    }
    await loadConfigs()
  } catch (e) {
    console.error(e)
    alert('実行に失敗しました。')
  } finally {
    running.value = false
  }
}

const runNowByGroup = async (group) => {
  if (!canEdit.value) return
  const isProd = group === 'prod'
  const targets = isProd ? selectedProdConfigs.value : selectedExtConfigs.value
  if (!targets.length) {
    alert(isProd ? '社内ラインの実行対象がありません。' : '外作・購入ラインの実行対象がありません。')
    return
  }
  const label = isProd ? '社内ライン' : '外作・購入ライン'
  if (!confirm(`${label}を順番に今すぐ実行しますか？`)) return

  if (isProd) runningProd.value = true
  else runningExt.value = true

  let executed = 0
  let failed = 0
  try {
    for (const cfg of targets) {
      try {
        await api.scheduleConfig.runNow({ task_name: 'AUTO_PLAN', config_id: cfg.id, line: cfg.line })
        executed += 1
      } catch (e) {
        failed += 1
      }
    }
    if (failed > 0) {
      alert(`${label}の実行完了（一部失敗あり）\n成功: ${executed} / 失敗: ${failed}`)
    } else {
      alert(`${label}の実行完了\n実行件数: ${executed}`)
    }
    await loadConfigs()
  } finally {
    if (isProd) runningProd.value = false
    else runningExt.value = false
  }
}

const runNowOne = async (cfg) => {
  if (!canEdit.value) return
  if (!confirm(`${cfg.line_code || ''} ${cfg.line_name || ''} を今すぐ実行しますか？`)) return
  runningOne.value = cfg.id
  try {
    await api.scheduleConfig.runNow({ task_name: 'AUTO_PLAN', config_id: cfg.id, line: cfg.line })
    alert('実行しました。')
    await loadConfigs()
  } catch (e) {
    console.error(e)
    alert('実行に失敗しました。')
  } finally {
    runningOne.value = null
  }
}

const formatDateTime = (dt) => {
  if (!dt) return '-'
  const d = new Date(dt)
  return d.toLocaleString('ja-JP')
}

const statusClass = (cfg) => ({
  'status-success': cfg.last_run_status === 'SUCCESS',
  'status-failed': cfg.last_run_status === 'FAILED',
  'status-running': cfg.last_run_status === 'RUNNING',
})

const lineTypeLabel = (lineType) => {
  const t = String(lineType || '').toUpperCase()
  if (t === 'PROD') return '社内'
  if (t === 'OUTSOURCE') return '外作'
  if (t === 'PURCHASE') return '購入'
  return '-'
}

const codeLabel = (u) => u?.profile?.employee_code || u.username || u.email || `ID:${u.id}`

const nameLabel = (u) => {
  const name = `${u.last_name || ''}${u.first_name || ''}`.trim()
  return name || u.username || u.email || `ID:${u.id}`
}

const candidateList = (cfg) => {
  const kw = String(cfg.searchCode || '').trim().toLowerCase()
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

onMounted(async () => {
  if (!canView.value) return
  await loadConfigs()
  await loadUsers()
})
</script>

<style scoped>
.settings-container {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
}
.page-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.col {
  min-width: 0;
}
.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 12px;
}
.no-permission {
  color: #b91c1c;
  font-weight: 600;
}
.field {
  margin-bottom: 12px;
}
.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.time-input {
  width: 72px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.line-select {
  min-width: 320px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.suffix {
  font-size: 12px;
}
.order-list {
  border: 1px solid #e5e9ef;
  border-radius: 4px;
  padding: 8px;
}
.order-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 4px;
  border-bottom: 1px solid #eef2f6;
}
.order-item:last-child {
  border-bottom: none;
}
.order-label {
  font-size: 13px;
}
.order-actions {
  display: flex;
  gap: 6px;
}
.actions {
  margin-top: 12px;
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
.btn.mini {
  padding: 4px 8px;
}
.btn.danger {
  color: #b91c1c;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.helper {
  margin: 8px 0 0;
  font-size: 12px;
  color: #666;
}
.table-wrapper {
  overflow-x: auto;
}
.line-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.line-table th,
.line-table td {
  border-bottom: 1px solid #e5e9ef;
  padding: 8px 6px;
  text-align: left;
  vertical-align: top;
}
.notify-cell {
  min-width: 220px;
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
.period-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.last-cell {
  min-width: 280px;
  font-size: 12px;
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
@media (max-width: 1200px) {
  .two-col {
    grid-template-columns: 1fr;
  }
}
</style>
