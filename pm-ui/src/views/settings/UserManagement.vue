<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">ユーザー管理</h2>
      <div class="page-actions">
        <input
          v-model="searchKeyword"
          class="search-input"
          type="text"
          placeholder="ユーザー名/氏名/メールで検索"
          @keyup.enter="loadUsers"
        />
        <button class="btn" @click="loadUsers" :disabled="loading">
          更新
        </button>
        <button class="btn primary" @click="startCreate">
          新規ユーザー
        </button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="!isAdminUser" class="helper-text">
        この画面を開く権限がありません。
      </div>
      <div v-else class="user-grid">
        <section class="user-list">
          <h3 class="section-title">ユーザー一覧</h3>
          <div v-if="loading" class="helper-text">読み込み中...</div>
          <div v-else-if="users.length === 0" class="helper-text">ユーザーがありません。</div>
          <table v-else class="data-table">
            <thead>
              <tr>
                <th>ユーザー名</th>
                <th>氏名</th>
                <th>部署</th>
                <th>役割</th>
                <th>状態</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="user in users"
                :key="user.id"
                :class="{ active: user.id === selectedUserId }"
                @click="selectUser(user)"
              >
                <td>{{ user.username }}</td>
                <td>{{ getUserDisplayName(user) }}</td>
                <td>{{ user.profile?.department_name || '-' }}</td>
                <td>{{ roleLabels[user.profile?.role] || '-' }}</td>
                <td>
                  <span :class="user.is_active ? 'status active' : 'status inactive'">
                    {{ user.is_active ? '有効' : '無効' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="user-editor">
          <div class="editor-header">
            <h3 class="section-title" :class="{ 'creating-mode': isCreating, 'editing-mode': !isCreating && selectedUserId }">
              <span v-if="isCreating" class="mode-badge create">新規作成</span>
              <span v-else-if="selectedUserId" class="mode-badge edit">編集中</span>
              <span v-else class="mode-badge empty">未選択</span>
              {{ isCreating ? '新規ユーザー作成' : selectedUserId ? `ユーザー詳細 - ${form.username}` : 'ユーザーを選択してください' }}
            </h3>
          </div>

          <div v-if="errorMessage" class="alert alert-danger">
            {{ errorMessage }}
          </div>
          <div v-if="successMessage" class="alert alert-success">
            {{ successMessage }}
          </div>

          <div v-if="!isCreating && !selectedUserId" class="empty-state">
            <p>左側のリストからユーザーを選択して編集するか、「新規ユーザー」ボタンをクリックして新しいユーザーを作成してください。</p>
          </div>

          <form v-else class="form-grid" @submit.prevent="saveUser">
            <div class="form-row">
              <label>ユーザー名</label>
              <input v-model="form.username" type="text" required />
            </div>
            <div class="form-row">
              <label>メールアドレス</label>
              <input v-model="form.email" type="email" />
            </div>
            <div class="form-row">
              <label>姓</label>
              <input v-model="form.last_name" type="text" />
            </div>
            <div class="form-row">
              <label>名</label>
              <input v-model="form.first_name" type="text" />
            </div>

            <div class="form-row">
              <label>社員コード</label>
              <input v-model="form.profile.employee_code" type="text" />
            </div>
            <div class="form-row">
              <label>役職</label>
              <input v-model="form.profile.position" type="text" />
            </div>
            <div class="form-row">
              <label>役割</label>
              <select v-model="form.profile.role">
                <option v-for="option in roleOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>雇用形態</label>
              <select v-model="form.profile.employment_type">
                <option v-for="option in employmentOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <div class="form-row full">
              <label>部署</label>
              <select v-model="form.profile.department">
                <option :value="null">未設定</option>
                <option v-for="dept in departmentOptions" :key="dept.value" :value="dept.value">
                  {{ dept.label }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>事業部</label>
              <input v-model="form.profile.division" type="text" />
            </div>
            <div class="form-row">
              <label>係</label>
              <input v-model="form.profile.group" type="text" />
            </div>
            <div class="form-row">
              <label>班</label>
              <input v-model="form.profile.team" type="text" />
            </div>
            <div class="form-row">
              <label>入社日</label>
              <input v-model="form.profile.joined_on" type="date" />
            </div>

            <div class="form-row">
              <label>パスワード</label>
              <input v-model="form.password" type="password" :placeholder="passwordHint" />
            </div>
            <div class="form-row">
              <label>パスワード確認</label>
              <input v-model="passwordConfirm" type="password" :placeholder="passwordHint" />
            </div>

            <div class="form-row inline">
              <label>有効</label>
              <input v-model="form.is_active" type="checkbox" />
            </div>
            <div class="form-row inline">
              <label>スタッフ</label>
              <input v-model="form.is_staff" type="checkbox" />
            </div>
            <div class="form-row inline">
              <label>管理者</label>
              <input v-model="form.is_superuser" type="checkbox" />
            </div>

            <div class="form-actions">
              <button type="submit" class="btn primary" :disabled="saving">
                {{ saving ? '保存中...' : '保存' }}
              </button>
              <button type="button" class="btn" @click="resetForm">
                リセット
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'

const users = ref([])
const departments = ref([])
const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const searchKeyword = ref('')
const selectedUserId = ref(null)
const isCreating = ref(false)
const passwordConfirm = ref('')

const roleOptions = [
  { value: 'staff', label: '一般' },
  { value: 'supervisor', label: '班長' },
  { value: 'chief', label: '係長' },
  { value: 'manager', label: '事業部長' },
]

const employmentOptions = [
  { value: 'regular', label: '正社員' },
  { value: 'skilled', label: '特定技能実習生' },
  { value: 'intern', label: '実習生' },
  { value: 'temporary', label: '人材派遣' },
]

const roleLabels = roleOptions.reduce((acc, option) => {
  acc[option.value] = option.label
  return acc
}, {})

const levelLabels = {
  division: '事業部',
  group: '係',
  team: '班',
}

const emptyProfile = () => ({
  employee_code: '',
  position: '',
  role: 'staff',
  employment_type: 'regular',
  department: null,
  division: '',
  group: '',
  team: '',
  joined_on: '',
})

const form = reactive({
  id: null,
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  is_active: true,
  is_staff: false,
  is_superuser: false,
  password: '',
  profile: emptyProfile(),
})

const passwordHint = computed(() => (isCreating.value ? '必須' : '変更時のみ入力'))

const isAdminUser = computed(() => {
  return Boolean(authState.user?.is_staff || authState.user?.is_superuser)
})

const departmentOptions = computed(() =>
  departments.value.map((dept) => ({
    value: dept.id,
    label: `${dept.name} (${levelLabels[dept.level] || dept.level})`,
  }))
)

const getUserDisplayName = (user) => {
  const fullName = `${user.last_name || ''} ${user.first_name || ''}`.trim()
  return fullName || user.username || user.email || '-'
}

const loadDepartments = async () => {
  if (!isAdminUser.value) return
  const response = await api.accounts.getDepartments({ page_size: 500 })
  const data = response.data
  departments.value = Array.isArray(data) ? data : data.results || []
}

const loadUsers = async () => {
  if (!isAdminUser.value) {
    errorMessage.value = 'この画面を開く権限がありません。'
    return
  }
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await api.accounts.getUsers({
      search: searchKeyword.value || undefined,
      page_size: 200,
    })
    const data = response.data
    users.value = Array.isArray(data) ? data : data.results || []
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || 'ユーザー一覧の取得に失敗しました。'
  } finally {
    loading.value = false
  }
}

const selectUser = (user) => {
  isCreating.value = false
  selectedUserId.value = user.id
  form.id = user.id
  form.username = user.username || ''
  form.email = user.email || ''
  form.first_name = user.first_name || ''
  form.last_name = user.last_name || ''
  form.is_active = Boolean(user.is_active)
  form.is_staff = Boolean(user.is_staff)
  form.is_superuser = Boolean(user.is_superuser)
  form.password = ''
  passwordConfirm.value = ''
  form.profile = {
    ...emptyProfile(),
    ...(user.profile || {}),
  }
  if (form.profile.department === undefined) {
    form.profile.department = user.profile?.department_id || null
  }
}

const resetForm = () => {
  if (isCreating.value) {
    form.id = null
    form.username = ''
    form.email = ''
    form.first_name = ''
    form.last_name = ''
    form.is_active = true
    form.is_staff = false
    form.is_superuser = false
    form.password = ''
    passwordConfirm.value = ''
    form.profile = emptyProfile()
    return
  }

  const current = users.value.find((item) => item.id === selectedUserId.value)
  if (current) {
    selectUser(current)
  }
}

const startCreate = () => {
  isCreating.value = true
  selectedUserId.value = null
  resetForm()
}

const buildPayload = () => {
  const profile = {
    ...form.profile,
    department: form.profile.department || null,
    joined_on: form.profile.joined_on || null,
  }

  const payload = {
    username: form.username.trim(),
    email: form.email.trim(),
    first_name: form.first_name.trim(),
    last_name: form.last_name.trim(),
    is_active: form.is_active,
    is_staff: form.is_staff,
    is_superuser: form.is_superuser,
    profile,
  }

  if (form.password) {
    payload.password = form.password
  }

  return payload
}

const saveUser = async () => {
  errorMessage.value = ''
  successMessage.value = ''

  if (form.password && form.password !== passwordConfirm.value) {
    errorMessage.value = 'パスワードが一致しません。'
    return
  }

  saving.value = true
  try {
    const payload = buildPayload()
    if (isCreating.value) {
      const response = await api.accounts.createUser(payload)
      successMessage.value = 'ユーザーを作成しました。'
      isCreating.value = false
      await loadUsers()
      selectUser(response.data)
    } else if (form.id) {
      const response = await api.accounts.updateUser(form.id, payload)
      successMessage.value = 'ユーザー情報を更新しました。'
      await loadUsers()
      selectUser(response.data)
    }
  } catch (error) {
    const detail = error?.response?.data
    errorMessage.value = extractErrorMessage(detail) || '保存に失敗しました。'
  } finally {
    saving.value = false
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
  if (!isAdminUser.value) {
    errorMessage.value = 'この画面を開く権限がありません。'
    return
  }
  await Promise.all([loadDepartments(), loadUsers()])
})
</script>

<style scoped>
.user-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 12px;
}

.editor-header {
  margin-bottom: 12px;
}

.section-title {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.mode-badge.create {
  background: #e7f6e9;
  color: #1a7f37;
  border: 1px solid #b7dfb9;
}

.mode-badge.edit {
  background: #e8f4ff;
  color: #0969da;
  border: 1px solid #b6d9f7;
}

.mode-badge.empty {
  background: #f6f8fa;
  color: #656d76;
  border: 1px solid #d0d7de;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #656d76;
  font-size: 13px;
  background: #f6f8fa;
  border-radius: 6px;
  border: 2px dashed #d0d7de;
}

.search-input {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  min-width: 220px;
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

.data-table tbody tr.active {
  background: #dfe9ff;
}

.user-editor {
  border-left: 1px solid #e0e0e0;
  padding-left: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(140px, 1fr));
  gap: 10px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.form-row.full {
  grid-column: span 2;
}

.form-row.inline {
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.form-row label {
  font-weight: 600;
}

.form-row input,
.form-row select {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
}

.form-actions {
  grid-column: span 2;
  display: flex;
  gap: 8px;
  margin-top: 6px;
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

.status {
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}

.status.active {
  background: #e7f6e9;
  color: #1a7f37;
}

.status.inactive {
  background: #ffeaea;
  color: #b42318;
}

@media (max-width: 1024px) {
  .user-grid {
    grid-template-columns: 1fr;
  }

  .user-editor {
    border-left: none;
    padding-left: 0;
    border-top: 1px solid #e0e0e0;
    padding-top: 12px;
  }
}
</style>
