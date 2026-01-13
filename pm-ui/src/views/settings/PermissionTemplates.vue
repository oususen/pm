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
        <div v-if="templateSuccess" class="alert alert-success">
          {{ templateSuccess }}
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
              <td>{{ getPermissionLabel(perm.resource) }}</td>
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
          <button type="button" class="btn primary" @click="saveTemplate" :disabled="templateSaving">
            {{ templateSaving ? '保存中...' : '保存' }}
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

const permissionResources = [
  { value: 'dashboard', label: 'ダッシュボード' },
  { value: 'orders', label: '受注' },
  { value: 'production', label: '生産' },
  { value: 'purchase', label: '仕入' },
  { value: 'shipping', label: '出荷' },
  { value: 'inventory', label: '在庫' },
  { value: 'quality', label: '品質' },
  { value: 'masters', label: 'マスタ' },
  { value: 'settings', label: '設定' },
  { value: 'users', label: 'ユーザー管理' },
  { value: 'manual', label: 'マニュアル' },
]

const levelLabels = {
  division: '事業部',
  group: '係',
  team: '班',
}

const isAdminUser = computed(() => {
  return Boolean(authState.user?.is_staff || authState.user?.is_superuser)
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
  try {
    await loadDepartments()
    await loadPositions()
    await loadTemplate()
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

.permission-table th {
  background: #f4f6ff;
  font-weight: 600;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
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
