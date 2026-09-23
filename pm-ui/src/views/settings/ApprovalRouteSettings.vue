<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">承認設定 <DataSourceDialog title="" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button class="btn-primary" @click="fetchAll" :disabled="loading || !canViewPage">
          {{ loading ? '更新中...' : '更新' }}
        </button>
        <button class="btn-success" @click="save" :disabled="saving || !canEditPage">
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <div v-if="!canViewPage" class="page-content">
      <div class="no-data">この画面を開く権限がありません。</div>
    </div>
    <div v-else class="page-content">
      <div v-if="errorMessage" class="alert alert-danger">{{ errorMessage }}</div>
      <div v-if="successMessage" class="alert alert-success">{{ successMessage }}</div>

      <div class="approval-layout">
        <aside class="business-panel">
          <h2 class="panel-title">承認対象業務一覧</h2>
          <table class="business-table">
            <thead>
              <tr>
                <th>業務</th>
                <th>状態</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="business in businessRows"
                :key="business.key"
                :class="{ selected: business.key === selectedBusinessKey }"
                @click="openBusinessRoute(business.key)"
              >
                <td>{{ business.label }}</td>
                <td>
                  <span class="status-badge" :class="business.statusClass">{{ business.statusLabel }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </aside>

        <section class="edit-panel">
          <div v-if="!selectedRoute" class="no-data">左の一覧から承認対象業務を選択してください。</div>
          <section v-else class="route-section" :id="`route-${selectedRoute.local_key}`">
          <div class="route-head">
            <div class="route-main-fields">
              <label>
                承認項目名
                <input :value="businessLabel(selectedRoute)" disabled />
              </label>
              <label class="active-check">
                <input v-model="selectedRoute.is_active" type="checkbox" :disabled="!canEditPage" />
                有効
              </label>
            </div>
            <button class="btn-danger" type="button" @click="removeRoute(selectedRouteIndex)" :disabled="!canEditPage || selectedRouteIndex < 0">
              削除
            </button>
          </div>

          <div class="stage-grid">
            <div v-for="stage in stages" :key="stage.key" class="stage-card">
              <div class="stage-title-row">
                <div class="stage-title">{{ stage.label }}</div>
                <label v-if="stage.optional" class="option-check">
                  <input v-model="selectedRoute[`${stage.key}_enabled`]" type="checkbox" :disabled="!canEditPage" />
                  使用
                </label>
              </div>
              <label class="field-label">
                基本役割
                <select v-model="selectedRoute[`${stage.key}_role`]" :disabled="!canEditPage || isStageDisabled(selectedRoute, stage)">
                  <option v-for="role in roleOptions" :key="role.value" :value="role.value">
                    {{ role.label }}
                  </option>
                </select>
              </label>
              <label class="field-label">
                部署
                <select v-model="selectedRoute[`${stage.key}_department`]" :disabled="!canEditPage || isStageDisabled(selectedRoute, stage)">
                  <option :value="null">指定なし</option>
                  <option v-for="dept in departmentOptions" :key="dept.value" :value="dept.value">
                    {{ dept.label }}
                  </option>
                </select>
              </label>
              <div class="stage-options">
                <label class="option-check">
                  <input v-model="selectedRoute[`${stage.key}_task_enabled`]" type="checkbox" :disabled="!canEditPage || isStageDisabled(selectedRoute, stage)" />
                  次段階タスク
                </label>
                <label class="option-check">
                  <input v-model="selectedRoute[`${stage.key}_app_notification_enabled`]" type="checkbox" :disabled="!canEditPage || isStageDisabled(selectedRoute, stage)" />
                  アプリ通知
                </label>
                <label class="option-check">
                  <input v-model="selectedRoute[`${stage.key}_email_notification_enabled`]" type="checkbox" :disabled="!canEditPage || isStageDisabled(selectedRoute, stage)" />
                  メール通知
                </label>
              </div>
              <UserPicker
                :row="selectedRoute"
                :stage="stage.key"
                type="allowed"
                title="限定ユーザー"
                empty-text="未設定時は基本役割から判定"
                :users="users"
                :disabled="!canEditPage || isStageDisabled(selectedRoute, stage)"
              />
              <UserPicker
                v-if="stage.key === 'creator' && ['laser_material_order', 'purchase_order_proposal'].includes(selectedRoute.item_key)"
                :row="selectedRoute"
                :stage="stage.key"
                type="authorized"
                title="作成可能ユーザー"
                empty-text="基本役割・部署に加えて作成を許可するユーザー"
                :users="users"
                :disabled="!canEditPage"
              />
              <UserPicker
                :row="selectedRoute"
                :stage="stage.key"
                type="proxy"
                title="代理ユーザー"
                empty-text="代理なし"
                :users="users"
                :disabled="!canEditPage || isStageDisabled(selectedRoute, stage)"
              />
            </div>
          </div>

          <div class="result-options">
            <div class="result-title">結果通知（全段階の担当者へ）</div>
            <label class="option-check">
              <input v-model="selectedRoute.approved_result_app_notification_enabled" type="checkbox" :disabled="!canEditPage" />
              承認時アプリ通知
            </label>
            <label class="option-check">
              <input v-model="selectedRoute.approved_result_email_notification_enabled" type="checkbox" :disabled="!canEditPage" />
              承認時メール通知
            </label>
            <label class="option-check">
              <input v-model="selectedRoute.rejected_result_app_notification_enabled" type="checkbox" :disabled="!canEditPage" />
              却下時アプリ通知
            </label>
            <label class="option-check">
              <input v-model="selectedRoute.rejected_result_email_notification_enabled" type="checkbox" :disabled="!canEditPage" />
              却下時メール通知
            </label>
          </div>

          <label class="note-field">
            備考
            <input v-model.trim="selectedRoute.note" :disabled="!canEditPage" />
          </label>
        </section>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, nextTick, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '承認設定 読み書き', table: 'accounts_approval_route_config', desc: '承認項目ごとの役割・限定ユーザー・代理ユーザー設定' },
  { op: 'ユーザー 読み取り', table: 'auth_user / accounts_userprofile', desc: '限定ユーザー・代理ユーザーの候補' },
]

const stages = [
  { key: 'creator', label: '作成者' },
  { key: 'reviewer1', label: '確認①' },
  { key: 'reviewer2', label: '確認②', optional: true },
  { key: 'approver', label: '承認者' },
]

const roleOptions = [
  { value: 'leader', label: 'リーダー' },
  { value: 'supervisor', label: '班長' },
  { value: 'chief', label: '係長' },
  { value: 'manager', label: '事業部長・課長' },
  { value: 'office_staff', label: '事務員' },
  { value: 'staff', label: '一般' },
]

const businessOptions = [
  { key: 'laser_material_order', label: 'レーザー材料発注' },
  { key: 'purchase_order_proposal', label: '外作・購入品注文' },
]

const departments = ref([])

const levelLabels = {
  division: '事業部',
  group: '係',
  team: '班',
  unit: 'グループ',
}

const levelIndent = {
  division: '',
  group: '　',
  team: '　　',
  unit: '　　　',
}

const buildDepartmentTree = (depts) => {
  const levelOrder = ['division', 'group', 'team', 'unit']
  const byParent = {}
  for (const dept of depts) {
    const pid = dept.parent || null
    if (!byParent[pid]) byParent[pid] = []
    byParent[pid].push(dept)
  }
  for (const key of Object.keys(byParent)) {
    byParent[key].sort((a, b) => {
      const li = levelOrder.indexOf(a.level) - levelOrder.indexOf(b.level)
      if (li !== 0) return li
      return (a.name || '').localeCompare(b.name || '')
    })
  }
  const result = []
  const walk = (parentId) => {
    for (const dept of (byParent[parentId] || [])) {
      const indent = levelIndent[dept.level] || ''
      result.push({
        value: dept.id,
        label: `${indent}${dept.name} (${levelLabels[dept.level] || dept.level})`,
      })
      walk(dept.id)
    }
  }
  walk(null)
  return result
}

const departmentOptions = computed(() => buildDepartmentTree(departments.value))

const userLabel = (user) => {
  const code = user?.profile?.employee_code || user?.username || user?.email || `ID:${user?.id}`
  const name = `${user?.last_name || ''} ${user?.first_name || ''}`.trim() || user?.username || ''
  return name ? `${code} ${name}` : code
}

const normalizeUserIds = (list) => {
  if (!Array.isArray(list)) return []
  const ids = list.map((id) => Number(id)).filter((id) => Number.isFinite(id))
  return [...new Set(ids)]
}

const emptyRoute = () => ({
  id: null,
  local_key: `new-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  item_key: '',
  item_name: '',
  creator_role: 'leader',
  creator_department: null,
  creator_task_enabled: true,
  creator_app_notification_enabled: true,
  creator_email_notification_enabled: false,
  creator_allowed_users: [],
  creator_authorized_users: [],
  creator_proxy_users: [],
  reviewer1_role: 'supervisor',
  reviewer1_department: null,
  reviewer1_task_enabled: true,
  reviewer1_app_notification_enabled: true,
  reviewer1_email_notification_enabled: false,
  reviewer1_allowed_users: [],
  reviewer1_proxy_users: [],
  reviewer2_role: 'chief',
  reviewer2_department: null,
  reviewer2_enabled: true,
  reviewer2_task_enabled: true,
  reviewer2_app_notification_enabled: true,
  reviewer2_email_notification_enabled: false,
  reviewer2_allowed_users: [],
  reviewer2_proxy_users: [],
  approver_role: 'manager',
  approver_department: null,
  approver_task_enabled: true,
  approver_app_notification_enabled: true,
  approver_email_notification_enabled: false,
  approver_allowed_users: [],
  approver_proxy_users: [],
  approved_result_app_notification_enabled: true,
  approved_result_email_notification_enabled: false,
  rejected_result_app_notification_enabled: true,
  rejected_result_email_notification_enabled: false,
  is_active: true,
  note: '',
})

const normalizeRoute = (route) => ({
  ...emptyRoute(),
  ...route,
  local_key: route.id ? `saved-${route.id}` : `new-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  creator_allowed_users: normalizeUserIds(route.creator_allowed_users),
  creator_authorized_users: normalizeUserIds(route.creator_authorized_users),
  creator_proxy_users: normalizeUserIds(route.creator_proxy_users),
  reviewer1_allowed_users: normalizeUserIds(route.reviewer1_allowed_users),
  reviewer1_proxy_users: normalizeUserIds(route.reviewer1_proxy_users),
  reviewer2_allowed_users: normalizeUserIds(route.reviewer2_allowed_users),
  reviewer2_proxy_users: normalizeUserIds(route.reviewer2_proxy_users),
  approver_allowed_users: normalizeUserIds(route.approver_allowed_users),
  approver_proxy_users: normalizeUserIds(route.approver_proxy_users),
})

const UserPicker = defineComponent({
  props: {
    row: { type: Object, required: true },
    stage: { type: String, required: true },
    type: { type: String, required: true },
    title: { type: String, required: true },
    emptyText: { type: String, required: true },
    users: { type: Array, required: true },
    disabled: { type: Boolean, default: false },
  },
  setup(props) {
    const search = ref('')
    const fieldKey = computed(() => `${props.stage}_${props.type}_users`)
    const selectedUsers = computed(() => {
      const ids = new Set((props.row[fieldKey.value] || []).map((id) => Number(id)))
      return props.users.filter((user) => ids.has(Number(user.id)))
    })
    const candidates = computed(() => {
      const keyword = search.value.trim().toLowerCase()
      if (!keyword) return []
      const selectedIds = new Set((props.row[fieldKey.value] || []).map((id) => Number(id)))
      return props.users
        .filter((user) => {
          if (selectedIds.has(Number(user.id))) return false
          return userLabel(user).toLowerCase().includes(keyword)
        })
        .slice(0, 8)
    })
    const addUser = (user) => {
      if (props.disabled) return
      const userId = Number(user.id)
      props.row[fieldKey.value] = [...(props.row[fieldKey.value] || []), userId]
      search.value = ''
    }
    const removeUser = (userId) => {
      if (props.disabled) return
      props.row[fieldKey.value] = (props.row[fieldKey.value] || []).filter((id) => Number(id) !== Number(userId))
    }
    return () => h('div', { class: 'user-picker' }, [
      h('div', { class: 'picker-title' }, props.title),
      h('input', {
        value: search.value,
        class: 'picker-search-input',
        disabled: props.disabled,
        placeholder: '社員コード/氏名/ユーザー名で検索',
        onInput: (event) => { search.value = event.target.value },
        onKeyup: (event) => {
          if (event.key === 'Enter' && candidates.value[0]) {
            event.preventDefault()
            addUser(candidates.value[0])
          }
        },
      }),
      candidates.value.length
        ? h('div', { class: 'candidate-list' }, candidates.value.map((user) =>
            h('button', {
              key: user.id,
              type: 'button',
              class: 'candidate-item',
              onClick: () => addUser(user),
            }, userLabel(user))
          ))
        : null,
      selectedUsers.value.length
        ? h('div', { class: 'selected-list' }, selectedUsers.value.map((user) =>
            h('span', { key: user.id, class: 'chip' }, [
              h('span', userLabel(user)),
              h('button', {
                type: 'button',
                class: 'chip-remove',
                disabled: props.disabled,
                onClick: () => removeUser(user.id),
              }, '×'),
            ])
          ))
        : h('div', { class: 'picker-empty' }, props.emptyText),
    ])
  },
})

const routes = ref([])
const users = ref([])
const selectedBusinessKey = ref('')
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const deletedRouteIds = ref([])

const canViewPage = computed(() => {
  const user = authState.user
  if (!user) return false
  return Boolean(user.is_staff || user.is_superuser)
})

const canEditPage = computed(() => {
  const user = authState.user
  if (!user) return false
  return Boolean(user.is_staff || user.is_superuser)
})

const normalizeList = (payload) => Array.isArray(payload) ? payload : payload?.results || []

const fetchUsers = async () => {
  const response = await api.accounts.getUsers({ page_size: 1000, is_active: true })
  users.value = normalizeList(response.data)
}

const fetchDepartments = async () => {
  const response = await api.accounts.getDepartments({ page_size: 20000 })
  const data = response.data
  departments.value = Array.isArray(data) ? data : data.results || []
}

const fetchRoutes = async () => {
  const response = await api.accounts.getApprovalRoutes({ page_size: 1000 })
  routes.value = normalizeList(response.data).map((route) => normalizeRoute(route))
  deletedRouteIds.value = []
}

const fetchAll = async () => {
  if (!canViewPage.value) return
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await Promise.all([fetchUsers(), fetchRoutes(), fetchDepartments()])
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || '承認設定の取得に失敗しました。'
  } finally {
    loading.value = false
  }
}

const hasRouteForBusiness = (itemKey) => routes.value.some((route) => route.item_key === itemKey)

const businessLabel = (route) => {
  const business = businessOptions.find((option) => option.key === route.item_key)
  return business?.label || route.item_name
}

const businessRows = computed(() => businessOptions.map((business) => {
  const route = routes.value.find((item) => item.item_key === business.key)
  if (!route) {
    return {
      ...business,
      statusLabel: '未設定',
      statusClass: 'draft',
    }
  }
  return {
    ...business,
    statusLabel: route.is_active ? '有効' : '無効',
    statusClass: route.is_active ? 'active' : 'inactive',
  }
}))

const selectedRouteIndex = computed(() => routes.value.findIndex((route) => route.item_key === selectedBusinessKey.value))
const selectedRoute = computed(() => selectedRouteIndex.value >= 0 ? routes.value[selectedRouteIndex.value] : null)

const openBusinessRoute = async (itemKey) => {
  const business = businessOptions.find((option) => option.key === itemKey)
  if (!business) return
  selectedBusinessKey.value = business.key

  let route = routes.value.find((item) => item.item_key === business.key)
  if (!route) {
    if (!canEditPage.value) return
    route = {
      ...emptyRoute(),
      item_key: business.key,
      item_name: business.label,
    }
    routes.value.push(route)
  }
  await nextTick()
  document.getElementById(`route-${route.local_key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const removeRoute = (index) => {
  if (!canEditPage.value) return
  const route = routes.value[index]
  if (route?.id) {
    deletedRouteIds.value = [...new Set([...deletedRouteIds.value, Number(route.id)])]
  }
  routes.value.splice(index, 1)
}

const buildPayload = () => routes.value.map((route) => ({
  id: route.id || undefined,
  item_key: route.item_key,
  item_name: route.item_name,
  creator_role: route.creator_role,
  creator_department: route.creator_department || null,
  creator_task_enabled: Boolean(route.creator_task_enabled),
  creator_app_notification_enabled: Boolean(route.creator_app_notification_enabled),
  creator_email_notification_enabled: Boolean(route.creator_email_notification_enabled),
  creator_allowed_users: route.creator_allowed_users || [],
  creator_authorized_users: route.creator_authorized_users || [],
  creator_proxy_users: route.creator_proxy_users || [],
  reviewer1_role: route.reviewer1_role,
  reviewer1_department: route.reviewer1_department || null,
  reviewer1_task_enabled: Boolean(route.reviewer1_task_enabled),
  reviewer1_app_notification_enabled: Boolean(route.reviewer1_app_notification_enabled),
  reviewer1_email_notification_enabled: Boolean(route.reviewer1_email_notification_enabled),
  reviewer1_allowed_users: route.reviewer1_allowed_users || [],
  reviewer1_proxy_users: route.reviewer1_proxy_users || [],
  reviewer2_role: route.reviewer2_role,
  reviewer2_department: route.reviewer2_department || null,
  reviewer2_enabled: Boolean(route.reviewer2_enabled),
  reviewer2_task_enabled: Boolean(route.reviewer2_task_enabled),
  reviewer2_app_notification_enabled: Boolean(route.reviewer2_app_notification_enabled),
  reviewer2_email_notification_enabled: Boolean(route.reviewer2_email_notification_enabled),
  reviewer2_allowed_users: route.reviewer2_allowed_users || [],
  reviewer2_proxy_users: route.reviewer2_proxy_users || [],
  approver_role: route.approver_role,
  approver_department: route.approver_department || null,
  approver_task_enabled: Boolean(route.approver_task_enabled),
  approver_app_notification_enabled: Boolean(route.approver_app_notification_enabled),
  approver_email_notification_enabled: Boolean(route.approver_email_notification_enabled),
  approver_allowed_users: route.approver_allowed_users || [],
  approver_proxy_users: route.approver_proxy_users || [],
  approved_result_app_notification_enabled: Boolean(route.approved_result_app_notification_enabled),
  approved_result_email_notification_enabled: Boolean(route.approved_result_email_notification_enabled),
  rejected_result_app_notification_enabled: Boolean(route.rejected_result_app_notification_enabled),
  rejected_result_email_notification_enabled: Boolean(route.rejected_result_email_notification_enabled),
  is_active: Boolean(route.is_active),
  note: route.note || '',
}))

const validateRoutes = () => {
  const seen = new Set()
  const supportedKeys = new Set(businessOptions.map((option) => option.key))
  for (const route of routes.value) {
    if (!route.item_name) {
      return '承認項目名を入力してください。'
    }
    const itemKey = String(route.item_key || '').trim()
    if (!itemKey) {
      return '対象業務を選択してください。'
    }
    if (!route.id && !supportedKeys.has(itemKey)) {
      return `対象業務にない承認項目は追加できません: ${route.item_name}`
    }
    if (seen.has(itemKey)) {
      return `対象業務が重複しています: ${businessLabel(route)}`
    }
    seen.add(itemKey)
  }
  return ''
}

const isStageDisabled = (route, stage) => Boolean(stage.optional && !route[`${stage.key}_enabled`])

const save = async () => {
  if (!canEditPage.value) return
  errorMessage.value = ''
  successMessage.value = ''
  const validationError = validateRoutes()
  if (validationError) {
    errorMessage.value = validationError
    return
  }
  saving.value = true
  try {
    const response = await api.accounts.saveApprovalRoutes(buildPayload(), deletedRouteIds.value)
    routes.value = normalizeList(response.data).map((route) => normalizeRoute(route))
    deletedRouteIds.value = []
    successMessage.value = '承認設定を保存しました。'
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || '保存に失敗しました。'
  } finally {
    saving.value = false
  }
}

onMounted(fetchAll)
</script>

<style scoped>
.approval-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 12px;
}

.business-panel,
.edit-panel {
  min-width: 0;
}

.panel-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
  color: #1f2a44;
}

.business-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border: 1px solid #cfd6e1;
  font-size: 12px;
}

.business-table th,
.business-table td {
  border: 1px solid #cfd6e1;
  padding: 7px 8px;
  text-align: left;
}

.business-table th {
  background: #e9eef8;
  color: #1f2a44;
}

.business-table tbody tr {
  cursor: pointer;
}

.business-table tbody tr:hover,
.business-table tbody tr.selected {
  background: #e8f1ff;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  border-radius: 12px;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 700;
}

.status-badge.active {
  color: #047857;
  border: 1px solid #86efac;
  background: #dcfce7;
}

.status-badge.inactive {
  color: #6b7280;
  border: 1px solid #d1d5db;
  background: #f3f4f6;
}

.status-badge.draft {
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
}

.route-section {
  border: 1px solid #d6dce8;
  border-radius: 6px;
  background: #fff;
  padding: 12px;
  scroll-margin-top: 120px;
}

.route-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 10px;
}

.route-main-fields {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto;
  gap: 10px;
  align-items: end;
  flex: 1;
}

.route-main-fields label,
.field-label,
.note-field {
  display: grid;
  gap: 4px;
  font-size: 12px;
  font-weight: 700;
  color: #26364f;
}

.route-main-fields input,
.field-label select,
.note-field input {
  border: 1px solid #cfd6e1;
  border-radius: 4px;
  padding: 5px 8px;
  font-size: 12px;
  font-weight: 400;
}

.active-check {
  display: flex !important;
  align-items: center;
  gap: 6px;
  padding-bottom: 5px;
  white-space: nowrap;
}

.stage-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(220px, 1fr));
  gap: 10px;
}

.stage-card {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px;
  background: #f8fafc;
  display: grid;
  gap: 8px;
}

.stage-title {
  font-size: 13px;
  font-weight: 700;
  color: #1f2a44;
}

.stage-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.stage-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px 6px;
}

.option-check {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
  color: #26364f;
  white-space: nowrap;
}

.result-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  align-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #f8fafc;
  margin-top: 10px;
  padding: 8px 10px;
}

.result-title {
  font-size: 12px;
  font-weight: 700;
  color: #1f2a44;
  margin-right: 4px;
}

:deep(.user-picker) {
  display: grid;
  gap: 5px;
}

:deep(.picker-title) {
  font-size: 12px;
  font-weight: 700;
  color: #26364f;
}

:deep(.picker-search-input) {
  width: 100%;
  padding: 5px 8px;
  font-size: 12px;
  border: 1px solid #cfd6e1;
  border-radius: 4px;
}

:deep(.candidate-list) {
  display: grid;
  gap: 2px;
  border: 1px solid #e5e9ef;
  border-radius: 4px;
  background: #fff;
  max-height: 150px;
  overflow: auto;
}

:deep(.candidate-item) {
  border: none;
  background: transparent;
  text-align: left;
  padding: 5px 8px;
  cursor: pointer;
  font-size: 12px;
}

:deep(.candidate-item:hover) {
  background: #eef3ff;
}

:deep(.selected-list) {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

:deep(.chip) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #cfd6e1;
  border-radius: 12px;
  background: #fff;
  padding: 3px 7px;
  font-size: 11px;
}

:deep(.chip-remove) {
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  padding: 0 2px;
}

:deep(.picker-empty) {
  font-size: 11px;
  color: #6b7280;
}

.note-field {
  margin-top: 10px;
}

.btn-danger {
  background: #ef4444;
  border: 1px solid #ef4444;
  color: #fff;
  border-radius: 4px;
  padding: 5px 10px;
  cursor: pointer;
  font-size: 12px;
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.alert {
  padding: 6px 8px;
  border-radius: 4px;
  margin-bottom: 8px;
  font-size: 12px;
}

.alert-danger {
  background: #ffe5e5;
  color: #b42318;
  border: 1px solid #f5b7b1;
}

.alert-success {
  background: #e7f6e9;
  color: #1a7f37;
  border: 1px solid #b7dfb9;
}

@media (max-width: 1400px) {
  .stage-grid {
    grid-template-columns: repeat(2, minmax(260px, 1fr));
  }
}

@media (max-width: 760px) {
  .approval-layout {
    grid-template-columns: 1fr;
  }

  .route-head {
    flex-direction: column;
  }

  .route-main-fields {
    grid-template-columns: 1fr;
  }

  .stage-grid {
    grid-template-columns: 1fr;
  }
}
</style>
