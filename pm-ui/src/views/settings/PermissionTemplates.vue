<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">権限テンプレート</h2>
      <div class="page-actions">
        <button class="btn" @click="refreshAll" :disabled="loading">
          更新
        </button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="!isAdminUser" class="helper-text">
        この画面を開く権限がありません。
      </div>
      <div v-else class="template-card">
        <div class="template-header">
          <h3 class="section-title">部署・役職 権限テンプレート</h3>
        </div>

        <div class="template-controls">
          <div class="template-select">
            <label>部署選択</label>
            <select v-model="selectedDepartmentId" @change="onDepartmentChange">
              <option :value="null">選択してください</option>
              <option v-for="dept in departmentOptions" :key="dept.value" :value="dept.value">
                {{ dept.label }}
              </option>
            </select>
          </div>
          <div class="template-select">
            <label>役職選択</label>
            <div class="position-row">
              <select
                v-model="selectedPositionName"
                :disabled="!selectedDepartmentId"
                @change="loadTemplate"
              >
                <option value="">選択してください</option>
                <option v-for="name in positions" :key="name" :value="name">
                  {{ name }}
                </option>
              </select>
              <input
                v-model="newPositionName"
                type="text"
                placeholder="新しい役職名"
                :disabled="!selectedDepartmentId"
              />
              <button type="button" class="btn" @click="addPosition" :disabled="!selectedDepartmentId">
                追加
              </button>
            </div>
          </div>
        </div>

        <div v-if="templateError" class="alert alert-danger">
          {{ templateError }}
        </div>

        <div v-if="templateLoading" class="helper-text">読み込み中...</div>

        <table v-else class="permission-table">
          <thead>
            <tr>
              <th>機能</th>
              <th>閲覧</th>
              <th>編集</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="perm in templatePermissions" :key="perm.resource">
              <td :class="getPermissionCellClass(perm)">{{ getPermissionLabel(perm.resource) }}</td>
              <td>
                <input
                  type="checkbox"
                  v-model="perm.can_view"
                  @change="onPermissionChange(perm, 'can_view')"
                  :disabled="!selectedPositionName"
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  v-model="perm.can_edit"
                  @change="onPermissionChange(perm, 'can_edit')"
                  :disabled="!selectedPositionName"
                />
              </td>
            </tr>
          </tbody>
        </table>

        <div class="form-actions">
          <div v-if="templateSuccess" class="save-message success">
            {{ templateSuccess }}
          </div>
          <button type="button" class="btn primary" @click="saveTemplate" :disabled="templateSaving">
            {{ templateSaving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>

      <div class="template-card">
        <div class="template-header">
          <h3 class="section-title">部署 権限テンプレート</h3>
        </div>

        <div class="template-controls">
          <div class="template-select">
            <label>部署選択</label>
            <select v-model="selectedDepartmentOnlyId" @change="loadDepartmentTemplate">
              <option :value="null">選択してください</option>
              <option v-for="dept in departmentOptions" :key="dept.value" :value="dept.value">
                {{ dept.label }}
              </option>
            </select>
          </div>
        </div>

        <div v-if="departmentTemplateError" class="alert alert-danger">
          {{ departmentTemplateError }}
        </div>

        <div v-if="departmentTemplateLoading" class="helper-text">読み込み中...</div>

        <table v-else class="permission-table">
          <thead>
            <tr>
              <th>機能</th>
              <th>閲覧</th>
              <th>編集</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="perm in departmentTemplatePermissions" :key="perm.resource">
              <td :class="getPermissionCellClass(perm)">{{ getPermissionLabel(perm.resource) }}</td>
              <td>
                <input
                  type="checkbox"
                  v-model="perm.can_view"
                  @change="onDepartmentPermissionChange(perm, 'can_view')"
                  :disabled="!selectedDepartmentOnlyId"
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  v-model="perm.can_edit"
                  @change="onDepartmentPermissionChange(perm, 'can_edit')"
                  :disabled="!selectedDepartmentOnlyId"
                />
              </td>
            </tr>
          </tbody>
        </table>

        <div class="form-actions">
          <div v-if="departmentTemplateSuccess" class="save-message success">
            {{ departmentTemplateSuccess }}
          </div>
          <button type="button" class="btn primary" @click="saveDepartmentTemplate" :disabled="departmentTemplateSaving">
            {{ departmentTemplateSaving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>

      <div class="template-card">
        <div class="template-header">
          <h3 class="section-title">役職 権限テンプレート</h3>
        </div>

        <div class="template-controls">
          <div class="template-select">
            <label>役職選択</label>
            <div class="position-row">
              <select v-model="selectedPositionOnlyName" @change="loadPositionTemplate">
                <option value="">選択してください</option>
                <option v-for="name in allPositions" :key="name" :value="name">
                  {{ name }}
                </option>
              </select>
              <input
                v-model="newPositionOnlyName"
                type="text"
                placeholder="新しい役職名"
              />
              <button type="button" class="btn" @click="addPositionOnly">
                追加
              </button>
            </div>
          </div>
        </div>

        <div v-if="positionTemplateError" class="alert alert-danger">
          {{ positionTemplateError }}
        </div>

        <div v-if="positionTemplateLoading" class="helper-text">読み込み中...</div>

        <table v-else class="permission-table">
          <thead>
            <tr>
              <th>機能</th>
              <th>閲覧</th>
              <th>編集</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="perm in positionTemplatePermissions" :key="perm.resource">
              <td :class="getPermissionCellClass(perm)">{{ getPermissionLabel(perm.resource) }}</td>
              <td>
                <input
                  type="checkbox"
                  v-model="perm.can_view"
                  @change="onPositionPermissionChange(perm, 'can_view')"
                  :disabled="!selectedPositionOnlyName"
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  v-model="perm.can_edit"
                  @change="onPositionPermissionChange(perm, 'can_edit')"
                  :disabled="!selectedPositionOnlyName"
                />
              </td>
            </tr>
          </tbody>
        </table>

        <div class="form-actions">
          <div v-if="positionTemplateSuccess" class="save-message success">
            {{ positionTemplateSuccess }}
          </div>
          <button type="button" class="btn primary" @click="savePositionTemplate" :disabled="positionTemplateSaving">
            {{ positionTemplateSaving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const loading = ref(false)
const templateLoading = ref(false)
const templateSaving = ref(false)
const templateError = ref('')
const templateSuccess = ref('')

const departments = ref([])
const positions = ref([])
const selectedDepartmentId = ref(null)
const selectedPositionName = ref('')
const newPositionName = ref('')
const templatePermissions = ref([])

const positionTemplateLoading = ref(false)
const positionTemplateSaving = ref(false)
const positionTemplateError = ref('')
const positionTemplateSuccess = ref('')
const allPositions = ref([])
const selectedPositionOnlyName = ref('')
const newPositionOnlyName = ref('')
const positionTemplatePermissions = ref([])

const departmentTemplateLoading = ref(false)
const departmentTemplateSaving = ref(false)
const departmentTemplateError = ref('')
const departmentTemplateSuccess = ref('')
const selectedDepartmentOnlyId = ref(null)
const departmentTemplatePermissions = ref([])

  const permissionResources = [
    { value: 'dashboard', label: 'ダッシュボード' },
    { value: 'orders', label: '受注' },
    { value: 'production', label: '生産' },
  { value: 'production.process_input', label: '生産: 工程作業入力' },
  { value: 'production.record_edit', label: '生産: 実績変更' },
  { value: 'production.scrap_record', label: '生産: 仕損品記録' },
  { value: 'production.plan_input', label: '生産: 生産計画入力' },
  { value: 'production.inventory', label: '生産: 在庫/残量一覧' },
  { value: 'production.scrap_history', label: '生産: 仕損履歴' },
  { value: 'production.progress', label: '生産: 進捗管理' },
  { value: 'production.line_demands', label: '生産: ライン需要一覧' },
  { value: 'production.line_calendars', label: '生産: ライン勤務カレンダ' },
  { value: 'production.stock_allocations', label: '生産: 在庫引当' },
  { value: 'production.orders', label: '生産: 製造指示' },
  { value: 'production.sequence_board', label: '生産: ミックス順序ボード' },
  { value: 'production.line_monitor', label: '生産: ライン稼働監視' },
  { value: 'production.mobile_input', label: '生産: モバイル作業入力（ライン）' },
  { value: 'purchase', label: '仕入' },
  { value: 'purchase.plan_input', label: '仕入: 仕入れ計画' },
  { value: 'purchase.inventory', label: '仕入: 在庫/残量' },
  { value: 'purchase.progress', label: '仕入: 仕入れ進度' },
  { value: 'purchase.actual_input', label: '仕入: 仕入れ実績入力' },
  { value: 'purchase.actual_inquiry', label: '仕入: 納入実績照会' },
  { value: 'purchase.supplier_calendar', label: '仕入: 仕入れ先カレンダ' },
  { value: 'purchase.order_proposals', label: '仕入: 発注提案' },
  { value: 'shipping', label: '出荷' },
    { value: 'inventory', label: '在庫' },
    { value: 'quality', label: '品質' },
    { value: 'notifications', label: '通知' },
    { value: 'engineering_change', label: '設変' },
    { value: 'masters', label: 'マスタ' },
    { value: 'settings', label: '設定' },
  { value: 'settings.profile', label: '設定: プロフィール編集' },
  { value: 'settings.users', label: '設定: ユーザー管理' },
  { value: 'settings.user_permissions', label: '設定: ユーザー権限編集' },
  { value: 'settings.permission_templates', label: '設定: 権限テンプレート' },
  { value: 'settings.smtp', label: '設定: SMTP設定' },
  { value: 'settings.purchase_plan_lock', label: '設定: 仕入計画ロック設定' },
  { value: 'settings.production_plan_lock', label: '設定: 生産計画ロック設定' },
  { value: 'settings.scheduled_tasks', label: '設定: 定時タスク設定' },
  { value: 'settings.supplier_order_schedule', label: '設定: 発注スケジュール設定' },
  { value: 'settings.purchase_order_approval', label: '設定: 発注承認者設定' },
  { value: 'settings.stocktake_init', label: '設定: 棚卸初期化' },
  { value: 'manual', label: 'マニュアル' },
]

const levelLabels = {
  division: '事業部',
  group: '係',
  team: '班',
}

const isAdminUser = computed(() => {
  // is_staff/is_superuser または権限テンプレート編集権限があるユーザー
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  // 新リソース優先、未設定時は従来の settings 編集権限にフォールバック
  const hasSpecificEntry = Array.isArray(user.effective_permissions)
    && user.effective_permissions.some((item) => item.resource === 'settings.permission_templates')
  if (hasSpecificEntry) {
    return hasPermission(user, 'settings.permission_templates', 'edit')
  }
  return hasPermission(user, 'settings', 'edit')
})

const departmentOptions = computed(() =>
  departments.value
    .filter((dept) => dept.level === 'division')
    .map((dept) => ({
      value: dept.id,
      label: `${dept.name} (${levelLabels[dept.level] || dept.level})`,
    }))
)

const getPermissionLabel = (resource) => {
  const found = permissionResources.find((item) => item.value === resource)
  return found ? found.label : resource
}

const getPermissionCellClass = (perm) => {
  if (perm.can_edit) return 'permission-cell-edit'
  if (perm.can_view) return 'permission-cell-view'
  return ''
}

const emptyPermissions = () =>
  permissionResources.map((resource) => ({
    resource: resource.value,
    can_view: false,
    can_edit: false,
  }))

const buildPermissions = (permissions) => {
  const list = Array.isArray(permissions) ? permissions : []
  return permissionResources.map((resource) => {
    const existing = list.find((perm) => perm.resource === resource.value)
    return {
      resource: resource.value,
      can_view: Boolean(existing?.can_view),
      can_edit: Boolean(existing?.can_edit),
    }
  })
}

const serializePermissions = () =>
  templatePermissions.value
    .filter((perm) => perm.can_view || perm.can_edit)
    .map((perm) => ({
      resource: perm.resource,
      can_view: Boolean(perm.can_view),
      can_edit: Boolean(perm.can_edit),
    }))

const onPermissionChange = (perm, field) => {
  if (field === 'can_edit' && perm.can_edit) {
    perm.can_view = true
  }
  if (field === 'can_view' && !perm.can_view) {
    perm.can_edit = false
  }
}

const onPositionPermissionChange = (perm, field) => {
  if (field === 'can_edit' && perm.can_edit) {
    perm.can_view = true
  }
  if (field === 'can_view' && !perm.can_view) {
    perm.can_edit = false
  }
}

const loadDepartments = async () => {
  if (!isAdminUser.value) return
  const response = await api.accounts.getDepartments({ page_size: 500 })
  const data = response.data
  departments.value = Array.isArray(data) ? data : data.results || []
}

const loadPositions = async () => {
  if (!isAdminUser.value || !selectedDepartmentId.value) {
    positions.value = []
    return
  }
  try {
    const response = await api.accounts.getDepartmentPositions({
      department: selectedDepartmentId.value,
    })
    const data = response.data
    positions.value = Array.isArray(data) ? data : []
  } catch (error) {
    positions.value = []
    templateError.value =
      error?.response?.data?.detail || '役職一覧の取得に失敗しました。'
  }
}

const loadAllPositions = async () => {
  if (!isAdminUser.value) {
    allPositions.value = []
    return
  }
  try {
    const response = await api.accounts.getPositions()
    const data = response.data
    allPositions.value = Array.isArray(data) ? data : []
  } catch (error) {
    allPositions.value = []
  }
}
const loadDepartmentTemplate = async () => {
  departmentTemplateError.value = ''
  departmentTemplateSuccess.value = ''
  if (!selectedDepartmentOnlyId.value) {
    departmentTemplatePermissions.value = emptyPermissions()
    return
  }

  departmentTemplateLoading.value = true
  try {
    const response = await api.accounts.getDepartmentPermissions({
      department: selectedDepartmentOnlyId.value,
    })
    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    departmentTemplatePermissions.value = buildPermissions(list)
  } catch (error) {
    departmentTemplateError.value =
      error?.response?.data?.detail || '権限テンプレートの取得に失敗しました。'
  } finally {
    departmentTemplateLoading.value = false
  }
}

const saveDepartmentTemplate = async () => {
  departmentTemplateError.value = ''
  departmentTemplateSuccess.value = ''
  if (!selectedDepartmentOnlyId.value) {
    departmentTemplateError.value = '部署を選択してください。'
    return
  }

  departmentTemplateSaving.value = true
  try {
    const permissions = departmentTemplatePermissions.value
      .filter((perm) => perm.can_view || perm.can_edit)
      .map((perm) => ({
        resource: perm.resource,
        can_view: Boolean(perm.can_view),
        can_edit: Boolean(perm.can_edit),
      }))

    const response = await api.accounts.setDepartmentPermissions({
      department: selectedDepartmentOnlyId.value,
      permissions: permissions,
    })

    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    departmentTemplatePermissions.value = buildPermissions(list)
    departmentTemplateSuccess.value = '権限テンプレートを保存しました。'
  } catch (error) {
    departmentTemplateError.value = extractErrorMessage(error?.response?.data) || '保存に失敗しました。'
  } finally {
    departmentTemplateSaving.value = false
  }
}

const onDepartmentPermissionChange = (perm, field) => {
  // 編集権限がある場合、閲覧権限も自動で付与
  if (field === 'can_edit' && perm.can_edit) {
    perm.can_view = true
  }
  // 閲覧権限を外す場合、編集権限も自動で外す
  if (field === 'can_view' && !perm.can_view) {
    perm.can_edit = false
  }
}
const loadPositionTemplate = async () => {
  positionTemplateError.value = ''
  positionTemplateSuccess.value = ''
  if (!selectedPositionOnlyName.value) {
    positionTemplatePermissions.value = emptyPermissions()
    return
  }

  positionTemplateLoading.value = true
  try {
    const response = await api.accounts.getPositionPermissions({
      position_name: selectedPositionOnlyName.value,
    })
    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    positionTemplatePermissions.value = buildPermissions(list)
  } catch (error) {
    positionTemplateError.value =
      error?.response?.data?.detail || '権限テンプレートの取得に失敗しました。'
  } finally {
    positionTemplateLoading.value = false
  }
}

const savePositionTemplate = async () => {
  positionTemplateError.value = ''
  positionTemplateSuccess.value = ''
  if (!selectedPositionOnlyName.value) {
    positionTemplateError.value = '役職を選択してください。'
    return
  }

  positionTemplateSaving.value = true
  try {
    const permissions = positionTemplatePermissions.value
      .filter((perm) => perm.can_view || perm.can_edit)
      .map((perm) => ({
        resource: perm.resource,
        can_view: Boolean(perm.can_view),
        can_edit: Boolean(perm.can_edit),
      }))

    const response = await api.accounts.setPositionPermissions({
      position_name: selectedPositionOnlyName.value,
      permissions: permissions,
    })

    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    positionTemplatePermissions.value = buildPermissions(list)
    positionTemplateSuccess.value = '権限テンプレートを保存しました。'
  } catch (error) {
    positionTemplateError.value = extractErrorMessage(error?.response?.data) || '保存に失敗しました。'
  } finally {
    positionTemplateSaving.value = false
  }
}

const addPositionOnly = async () => {
  const name = newPositionOnlyName.value.trim()
  if (!name) {
    positionTemplateError.value = '役職名を入力してください。'
    return
  }
  positionTemplateError.value = ''
  if (!allPositions.value.includes(name)) {
    allPositions.value = [...allPositions.value, name].sort()
  }
  selectedPositionOnlyName.value = name
  newPositionOnlyName.value = ''
  await loadPositionTemplate()
}

const loadTemplate = async () => {
  templateError.value = ''
  templateSuccess.value = ''
  if (!selectedDepartmentId.value || !selectedPositionName.value) {
    templatePermissions.value = emptyPermissions()
    return
  }

  templateLoading.value = true
  try {
    const response = await api.accounts.getDepartmentPositionPermissions({
      department: selectedDepartmentId.value,
      position_name: selectedPositionName.value,
    })
    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    templatePermissions.value = buildPermissions(list)
  } catch (error) {
    templateError.value =
      error?.response?.data?.detail || '権限テンプレートの取得に失敗しました。'
  } finally {
    templateLoading.value = false
  }
}

const addPosition = async () => {
  const name = newPositionName.value.trim()
  if (!name) {
    templateError.value = '役職名を入力してください。'
    return
  }
  templateError.value = ''
  if (!positions.value.includes(name)) {
    positions.value = [...positions.value, name].sort()
  }
  selectedPositionName.value = name
  newPositionName.value = ''
  await loadTemplate()
}

const saveTemplate = async () => {
  templateError.value = ''
  templateSuccess.value = ''
  if (!selectedDepartmentId.value || !selectedPositionName.value) {
    templateError.value = '部署と役職を選択してください。'
    return
  }

  templateSaving.value = true
  try {
    const response = await api.accounts.setDepartmentPositionPermissions({
      department: selectedDepartmentId.value,
      position_name: selectedPositionName.value,
      permissions: serializePermissions(),
    })

    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    templatePermissions.value = buildPermissions(list)
    templateSuccess.value = '権限テンプレートを保存しました。'
  } catch (error) {
    templateError.value = extractErrorMessage(error?.response?.data) || '保存に失敗しました。'
  } finally {
    templateSaving.value = false
  }
}

const onDepartmentChange = async () => {
  selectedPositionName.value = ''
  newPositionName.value = ''
  templatePermissions.value = emptyPermissions()
  await loadPositions()
}

const refreshAll = async () => {
  loading.value = true
  templateError.value = ''
  templateSuccess.value = ''
  positionTemplateError.value = ''
  positionTemplateSuccess.value = ''
  try {
    await loadDepartments()
    await loadAllPositions()
    await loadPositions()
    await loadTemplate()
    await loadPositionTemplate()
  } finally {
    loading.value = false
  }
}

const extractErrorMessage = (detail) => {
  if (!detail) return ''
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.join(' ')
  if (typeof detail !== 'object') return ''

  const messages = []
  Object.entries(detail).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      messages.push(`${key}: ${value.join(' ')}`)
    } else if (typeof value === 'object' && value !== null) {
      Object.entries(value).forEach(([childKey, childValue]) => {
        if (Array.isArray(childValue)) {
          messages.push(`${key}.${childKey}: ${childValue.join(' ')}`)
        } else if (childValue) {
          messages.push(`${key}.${childKey}: ${childValue}`)
        }
      })
    } else if (value) {
      messages.push(`${key}: ${value}`)
    }
  })
  return messages.join(' / ')
}

onMounted(async () => {
  if (!isAdminUser.value) return
  templatePermissions.value = emptyPermissions()
  positionTemplatePermissions.value = emptyPermissions()
  await refreshAll()
})
</script>

<style scoped>
.template-card {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 12px;
  background: #fff;
}

.template-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
}

.template-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 12px 0;
}

.template-select {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 240px;
  font-size: 12px;
}

.template-select select,
.template-select input {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
}

.position-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.permission-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.permission-table th,
.permission-table td {
  border: 1px solid #d6d6d6;
  padding: 4px 6px;
  text-align: center;
}

.permission-table th:first-child,
.permission-table td:first-child {
  text-align: right;
}

.permission-table td.permission-cell-edit {
  background: #9ed7a5;
}

.permission-table td.permission-cell-view {
  background: #9fbcf7;
}

.permission-table th {
  background: #f4f6ff;
  font-weight: 600;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.save-message {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
}

.save-message.success {
  background: #e7f6e9;
  color: #1a7f37;
  border: 1px solid #b7dfb9;
}

.btn {
  border: 1px solid #888;
  background: #f3f3f3;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.btn.primary {
  background: #2f6fed;
  border-color: #2f6fed;
  color: #fff;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.helper-text {
  color: #666;
  font-size: 12px;
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
</style>
