<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">朝礼一覧 <DataSourceDialog title="朝礼一覧" :sources="dsSources" /></h1>
      <div class="page-actions">
        <RouterLink v-if="canEditMeeting" class="btn-primary" to="/production/morning-meetings/new">新規作成</RouterLink>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>開始日</label>
          <input v-model="filters.meeting_date_from" type="date" />
        </div>
        <div class="filter-field">
          <label>終了日</label>
          <input v-model="filters.meeting_date_to" type="date" />
        </div>
        <div class="filter-field">
          <label>状態</label>
          <select v-model="filters.status">
            <option value="">すべて</option>
            <option v-for="option in statusOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>対象部署</label>
          <select v-model="filters.department">
            <option value="">すべて</option>
            <option v-for="dept in departments" :key="dept.id" :value="String(dept.id)">
              {{ dept.name }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>キーワード</label>
          <input v-model.trim="filters.search" type="text" placeholder="タイトル・議題" />
        </div>
        <div class="filter-actions">
          <button class="btn-primary" type="button" @click="loadMeetings" :disabled="loading">
            {{ loading ? '読込中...' : '検索' }}
          </button>
          <button class="btn-secondary" type="button" @click="resetFilters">リセット</button>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>日付</th>
            <th>タイトル</th>
            <th>対象部署</th>
            <th>ライン</th>
            <th>司会者</th>
            <th>状態</th>
            <th>参加者</th>
            <th>確認済</th>
            <th>資料</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in meetings" :key="row.id">
            <td>{{ row.meeting_date }}</td>
            <td>{{ row.title }}</td>
            <td>{{ joinNames(row.target_department_names) }}</td>
            <td>{{ joinNames(row.target_line_names) }}</td>
            <td>{{ row.facilitator_name || '-' }}</td>
            <td>{{ row.status_display }}</td>
            <td>{{ row.participant_count }}</td>
            <td>{{ row.checked_count }}</td>
            <td>{{ row.attachment_count || 0 }}</td>
            <td class="actions-cell">
              <template v-if="row.status === 'COMPLETED'">
                <RouterLink class="btn-sm secondary" :to="`/production/morning-meetings/${row.id}/run`">詳細</RouterLink>
              </template>
              <template v-else>
                <RouterLink class="btn-sm" :to="`/production/morning-meetings/${row.id}/run`">実行</RouterLink>
                <RouterLink v-if="canEditMeeting" class="btn-sm secondary" :to="`/production/morning-meetings/${row.id}/edit`">編集</RouterLink>
                <button
                  v-if="canEditMeeting"
                  class="btn-sm danger"
                  type="button"
                  @click="handleDelete(row)"
                  :disabled="loading"
                >
                  削除
                </button>
              </template>
            </td>
          </tr>
          <tr v-if="!meetings.length && !loading">
            <td colspan="10" class="empty-row">朝礼はありません</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import { hasPermission } from '@/router'
import { addDays, getBusinessISODate } from '@/utils/dateUtil'

const dsSources = [
  { op: '読み書き', table: 't_morning_meeting', desc: '朝礼一覧・作成・更新・開始・完了' },
  { op: '読み書き', table: 't_morning_meeting_participant', desc: '参加者確認状況の保存' },
  { op: '読み取り', table: 'accounts_department / auth_user', desc: '対象部署・司会者・参加者の取得' },
]

const statusOptions = [
  { value: 'DRAFT', label: '下書き' },
  { value: 'READY', label: '準備完了' },
  { value: 'IN_PROGRESS', label: '実行中' },
  { value: 'COMPLETED', label: '完了' },
]

const loading = ref(false)
const meetings = ref([])
const departments = ref([])
const filters = ref({
  meeting_date_from: getBusinessISODate(addDays(new Date(), -7)),
  meeting_date_to: getBusinessISODate(),
  status: '',
  department: '',
  search: '',
})
const morningMeetingResource = 'production.morning_meeting'

const hasMorningMeetingPermission = (level) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true

  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : []
  const entry = permissions.find((item) => item.resource === morningMeetingResource)
  if (entry) {
    return level === 'edit'
      ? Boolean(entry.can_edit)
      : Boolean(entry.can_view || entry.can_edit)
  }

  return hasPermission(user, 'production', level)
}

const canEditMeeting = computed(() => hasMorningMeetingPermission('edit'))

const buildParams = () => {
  const params = {}
  Object.entries(filters.value).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) {
      params[key] = value
    }
  })
  return params
}

const joinNames = (values) => {
  if (!Array.isArray(values) || !values.length) return '-'
  return values.join(' / ')
}

const loadMeetings = async () => {
  loading.value = true
  try {
    const res = await api.morningMeetings.list(buildParams())
    meetings.value = Array.isArray(res.data) ? res.data : []
  } catch (error) {
    console.error('朝礼一覧の取得に失敗しました:', error)
    meetings.value = []
  } finally {
    loading.value = false
  }
}

const loadDepartments = async () => {
  try {
    const res = await api.accounts.getDepartments({ ordering: 'display_id,name', page_size: 20000 })
    const data = res.data
    departments.value = Array.isArray(data) ? data : data?.results || []
  } catch (error) {
    console.error('部署一覧の取得に失敗しました:', error)
    departments.value = []
  }
}

const resetFilters = async () => {
  filters.value = {
    meeting_date_from: getBusinessISODate(addDays(new Date(), -7)),
    meeting_date_to: getBusinessISODate(),
    status: '',
    department: '',
    search: '',
  }
  await loadMeetings()
}

const handleDelete = async (row) => {
  if (!window.confirm(`朝礼「${row.title}」を削除します。よろしいですか？`)) return
  try {
    await api.morningMeetings.delete(row.id)
    await loadMeetings()
  } catch (error) {
    console.error('朝礼の削除に失敗しました:', error)
    window.alert('朝礼の削除に失敗しました。')
  }
}

onMounted(async () => {
  await Promise.all([loadDepartments(), loadMeetings()])
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.filter-field {
  display: flex;
  flex-direction: column;
  min-width: 160px;
}

.filter-field input,
.filter-field select {
  min-height: 34px;
}

.filter-actions {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.actions-cell {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.btn-sm.secondary {
  background: #e2e8f0;
  color: #1e293b;
}

.btn-sm.danger {
  background: #dc2626;
  color: #fff;
}

.empty-row {
  text-align: center;
  color: #64748b;
  padding: 16px;
}
</style>
