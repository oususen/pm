<template>
  <div class="ot-approval-page">
    <div class="page-header">
      <h1 class="page-title">{{ t('approvalList.pageTitle') }}</h1>
      <button
        v-if="selectedIds.length > 0"
        class="btn btn-bulk"
        @click="openBulk"
      >
        {{ t('approvalList.bulkBtn', { count: selectedIds.length }) }}
      </button>
    </div>

    <!-- フィルター -->
    <div v-if="applications.length" class="filters">
      <select v-model="filterTeam" class="filter-select">
        <option value="">{{ t('approvalList.allTeams') }}</option>
        <option v-for="tm in teamOptions" :key="tm" :value="tm">{{ tm }}</option>
      </select>
      <select v-model="filterGroup" class="filter-select">
        <option value="">{{ t('approvalList.allGroups') }}</option>
        <option v-for="g in groupOptions" :key="g" :value="g">{{ g }}</option>
      </select>
      <select v-model="filterDate" class="filter-select">
        <option value="">全日付</option>
        <option v-for="d in dateOptions" :key="d" :value="d">{{ d }}</option>
      </select>
    </div>

    <div v-if="loading" class="loading">{{ t('approvalList.loading') }}</div>
    <div v-else-if="!applications.length" class="empty">{{ t('approvalList.empty') }}</div>
    <div v-else-if="!filteredApplications.length" class="empty">{{ t('approvalList.emptyFilter') }}</div>
    <template v-else>
      <table class="ot-table">
        <thead>
          <tr>
            <th class="check-col">
              <input type="checkbox" :checked="allSelected" @change="toggleAll" />
            </th>
            <th>{{ t('approvalList.col.date') }}</th>
            <th>{{ t('approvalList.col.team') }}</th>
            <th>{{ t('approvalList.col.group') }}</th>
            <th class="name-col">{{ t('approvalList.col.applicant') }}</th>
            <th>{{ t('approvalList.col.type') }}</th>
            <th>勤務時間</th>
            <th>{{ t('approvalList.col.timeRange') }}</th>
            <th>{{ t('approvalList.col.hours') }}</th>
            <th>{{ t('approvalList.col.reason') }}</th>
            <th>{{ t('approvalList.col.submittedAt') }}</th>
            <th>状態</th>
            <th>{{ t('approvalList.col.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="app in filteredApplications" :key="app.id" :class="{ selected: selectedIds.includes(app.id) }">
            <td class="check-col">
              <input type="checkbox" :value="app.id" v-model="selectedIds" />
            </td>
            <td class="nowrap">{{ app.work_date }}</td>
            <td>{{ app.team_name || '-' }}</td>
            <td>{{ app.group_name || '-' }}</td>
            <td class="name-col">{{ app.applicant_name }}</td>
            <td>{{ app.type_display }}</td>
            <td class="nowrap time-cell">{{ app.work_start_time || '-' }}{{ app.work_start_time ? ' 〜 ' + (app.scheduled_end_time || '-') : '' }}</td>
            <td class="nowrap time-cell">{{ app.start_time }} 〜 {{ app.end_time }}</td>
            <td class="num">
              {{ Math.round((parseFloat(app.hours) + parseFloat(app.midnight_hours)) * 10) / 10 }}H
              <span v-if="app.midnight_hours > 0" class="midnight-tag">{{ t('approvalList.midnight') }}{{ app.midnight_hours }}H</span>
            </td>
            <td class="reason-cell">{{ app.reason || '-' }}</td>
            <td class="nowrap">{{ app.submitted_at ? formatDateTime(app.submitted_at) : '-' }}</td>
            <td class="nowrap">
              <span class="status-badge" :style="{ color: statusMeta(app.status).color }">
                {{ statusMeta(app.status).label }}
              </span>
            </td>
            <td class="actions">
              <button class="btn btn-sm btn-detail" @click="openApprove(app)">{{ t('approvalList.btnDetail') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <!-- 個別承認モーダル -->
    <div v-if="targetApp" class="modal-overlay" @click.self="targetApp = null">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ t('approvalList.modal.title') }}</h2>
          <button class="modal-close" @click="targetApp = null">×</button>
        </div>
        <div class="modal-body">
          <table class="detail-table">
            <tbody>
              <tr><th>{{ t('approvalList.col.applicant') }}</th><td>{{ targetApp.applicant_name }}</td></tr>
              <tr><th>{{ t('approvalList.col.date') }}</th><td>{{ targetApp.work_date }}</td></tr>
              <tr><th>{{ t('approvalList.col.type') }}</th><td>{{ targetApp.type_display }}</td></tr>
              <tr v-if="targetApp.work_start_time || targetApp.scheduled_end_time">
                <th>{{ t('approvalList.modal.workTime') }}</th>
                <td>{{ targetApp.work_start_time || '-' }} 〜 {{ targetApp.scheduled_end_time || '-' }}（{{ t('approvalList.modal.scheduled') }}）</td>
              </tr>
              <tr><th>{{ t('approvalList.modal.overtimeRange') }}</th><td>{{ targetApp.start_time }} 〜 {{ targetApp.end_time }}</td></tr>
              <tr>
                <th>{{ t('approvalList.modal.hours') }}</th>
                <td>{{ Math.round((parseFloat(targetApp.hours) + parseFloat(targetApp.midnight_hours)) * 10) / 10 }}H（{{ t('approvalList.modal.midnight') }}: {{ targetApp.midnight_hours }}H）</td>
              </tr>
              <tr><th>{{ t('approvalList.col.reason') }}</th><td>{{ targetApp.reason || '-' }}</td></tr>
              <tr v-if="targetApp.signature">
                <th>サイン</th>
                <td><img :src="targetApp.signature" alt="申請者サイン" class="sign-img" /></td>
              </tr>
            </tbody>
          </table>

          <div class="comment-section">
            <label class="comment-label">{{ t('approvalList.modal.comment') }}</label>
            <textarea v-model="actionComment" class="comment-input" rows="2" :placeholder="t('approvalList.modal.commentPlaceholder')"></textarea>
          </div>

          <div v-if="actionMode === 'reject'" class="reject-section">
            <label class="comment-label required">{{ t('approvalList.modal.rejectReason') }}</label>
            <textarea v-model="rejectReason" class="comment-input" rows="2" :placeholder="t('approvalList.modal.rejectPlaceholder')" required></textarea>
          </div>

          <div v-if="actionError" class="error-msg">{{ actionError }}</div>

          <div class="modal-actions">
            <template v-if="actionMode === 'confirm'">
              <button class="btn btn-primary" @click="doApprove" :disabled="acting">{{ t('approvalList.modal.approve') }}</button>
              <button class="btn btn-danger" @click="actionMode = 'reject'">{{ t('approvalList.modal.reject') }}</button>
              <button class="btn btn-ghost" @click="targetApp = null">{{ t('approvalList.modal.cancel') }}</button>
            </template>
            <template v-else>
              <button class="btn btn-danger" @click="doReject" :disabled="acting || !rejectReason">{{ t('approvalList.modal.reject') }}</button>
              <button class="btn btn-ghost" @click="actionMode = 'confirm'">{{ t('approvalList.modal.back') }}</button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- 一括確認依頼モーダル -->
    <div v-if="showBulkModal" class="modal-overlay" @click.self="showBulkModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ t('approvalList.bulk.title') }}</h2>
          <button class="modal-close" @click="showBulkModal = false">×</button>
        </div>
        <div class="modal-body">
          <p class="bulk-desc" v-html="t('approvalList.bulk.desc', { count: `<strong>${selectedIds.length}</strong>`, role: nextRoleLabel })"></p>
          <table class="bulk-list-table">
            <thead><tr><th>{{ t('approvalList.col.date') }}</th><th>{{ t('approvalList.col.applicant') }}</th><th>{{ t('approvalList.col.timeRange') }}</th></tr></thead>
            <tbody>
              <tr v-for="app in selectedApps" :key="app.id">
                <td>{{ app.work_date }}</td>
                <td>{{ app.applicant_name }}</td>
                <td class="nowrap">{{ app.start_time }} 〜 {{ app.end_time }}</td>
              </tr>
            </tbody>
          </table>

          <div class="comment-section">
            <label class="comment-label">{{ t('approvalList.modal.comment') }}</label>
            <textarea v-model="bulkComment" class="comment-input" rows="2" :placeholder="t('approvalList.bulk.commentPlaceholder', { role: nextRoleLabel })"></textarea>
          </div>

          <div v-if="bulkError" class="error-msg">{{ bulkError }}</div>

          <div class="modal-actions">
            <button class="btn btn-bulk" @click="doBulkApprove" :disabled="bulkActing">
              {{ bulkActing ? t('approvalList.bulk.sending') : t('approvalList.bulk.btn', { count: selectedIds.length, role: nextRoleLabel }) }}
            </button>
            <button class="btn btn-ghost" @click="showBulkModal = false">{{ t('approvalList.bulk.cancel') }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { t } from '@/i18n'

// ステータス表示ラベル・色
const STATUS_META = {
  submitted:          { label: '提出済み',        color: '#6b7280' },
  approved_leader:    { label: 'リーダー確認済み', color: '#2563eb' },
  approved_supervisor:{ label: '班長確認済み',     color: '#0891b2' },
  approved_chief:     { label: '係長確認済み',     color: '#059669' },
  approved_manager:   { label: '承認完了',         color: '#16a34a' },
  rejected:           { label: '却下',             color: '#dc2626' },
}
function statusMeta(status) {
  return STATUS_META[status] || { label: status, color: '#6b7280' }
}

// ロール別の次承認者ラベル
const myRole = computed(() => authState.user?.profile?.role || 'supervisor')
const nextRoleLabel = computed(() => {
  const map = { leader: 'supervisor', supervisor: 'chief', chief: 'manager' }
  const key = map[myRole.value]
  return key ? t(`approvalList.role.${key}`) : t('approvalList.role.default')
})

const applications = ref([])
const loading = ref(false)
const filterTeam = ref('')
const filterGroup = ref('')
const filterDate = ref('')

const teamOptions = computed(() =>
  [...new Set(applications.value.map(a => a.team_name).filter(Boolean))].sort()
)
const groupOptions = computed(() =>
  [...new Set(applications.value.map(a => a.group_name).filter(Boolean))].sort()
)
const dateOptions = computed(() =>
  [...new Set(applications.value.map(a => a.work_date).filter(Boolean))].sort().reverse()
)
const filteredApplications = computed(() =>
  applications.value.filter(a =>
    (!filterTeam.value || a.team_name === filterTeam.value) &&
    (!filterGroup.value || a.group_name === filterGroup.value) &&
    (!filterDate.value || a.work_date === filterDate.value)
  )
)
const targetApp = ref(null)
const actionMode = ref('confirm')  // 'confirm' | 'reject'
const actionComment = ref('')
const rejectReason = ref('')
const actionError = ref('')
const acting = ref(false)

// チェックボックス
const selectedIds = ref([])

const allSelected = computed(() =>
  filteredApplications.value.length > 0 &&
  filteredApplications.value.every(a => selectedIds.value.includes(a.id))
)

function toggleAll(e) {
  if (e.target.checked) {
    const filteredIds = filteredApplications.value.map(a => a.id)
    selectedIds.value = [...new Set([...selectedIds.value, ...filteredIds])]
  } else {
    const filteredIds = new Set(filteredApplications.value.map(a => a.id))
    selectedIds.value = selectedIds.value.filter(id => !filteredIds.has(id))
  }
}

const selectedApps = computed(() =>
  applications.value.filter(a => selectedIds.value.includes(a.id))
)

// 一括モーダル
const showBulkModal = ref(false)
const bulkComment = ref('')
const bulkError = ref('')
const bulkActing = ref(false)

function formatDateTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function fetchList() {
  loading.value = true
  selectedIds.value = []
  try {
    const res = await api.overtime.getPendingApprovals()
    applications.value = res.data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function openApprove(app) {
  targetApp.value = app
  actionMode.value = 'confirm'
  actionComment.value = ''
  rejectReason.value = ''
  actionError.value = ''
}

function openBulk() {
  bulkComment.value = ''
  bulkError.value = ''
  showBulkModal.value = true
}

async function doApprove() {
  acting.value = true
  actionError.value = ''
  try {
    await api.overtime.approveApplication(targetApp.value.id, { comment: actionComment.value })
    targetApp.value = null
    await fetchList()
  } catch (e) {
    actionError.value = t('approvalList.error.approve') + (e.response?.data?.detail || e.message)
  } finally {
    acting.value = false
  }
}

async function doReject() {
  if (!rejectReason.value.trim()) return
  acting.value = true
  actionError.value = ''
  try {
    await api.overtime.rejectApplication(targetApp.value.id, {
      reason: rejectReason.value,
      comment: actionComment.value,
    })
    targetApp.value = null
    await fetchList()
  } catch (e) {
    actionError.value = t('approvalList.error.reject') + (e.response?.data?.detail || e.message)
  } finally {
    acting.value = false
  }
}

async function doBulkApprove() {
  bulkActing.value = true
  bulkError.value = ''
  try {
    await api.overtime.bulkApproveApplications({
      ids: selectedIds.value,
      comment: bulkComment.value,
    })
    showBulkModal.value = false
    await fetchList()
  } catch (e) {
    bulkError.value = t('approvalList.error.bulk') + (e.response?.data?.detail || e.message)
  } finally {
    bulkActing.value = false
  }
}

onMounted(fetchList)
</script>

<style scoped>
.ot-approval-page {
  padding: 24px;
  max-width: 1600px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1f2a44;
}
.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.filter-select {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
}
.loading, .empty {
  text-align: center;
  color: #6b7280;
  padding: 40px;
}
.ot-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
}
.ot-table th {
  background: #f9fafb;
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
}
.ot-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}
.ot-table tr:last-child td { border-bottom: none; }
.ot-table tr.selected td { background: #f0fdf4; }
.check-col { width: 36px; text-align: center; }
.name-col { min-width: 240px; }
.num { text-align: right; }
.nowrap { white-space: nowrap; }
.time-cell { color: #1f2a44; }
.reason-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status-badge { font-size: 12px; font-weight: 600; white-space: nowrap; }
.midnight-tag {
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  background: #f5f3ff;
  color: #7c3aed;
  padding: 1px 5px;
  border-radius: 3px;
}
.actions { white-space: nowrap; }
.btn {
  display: inline-flex;
  align-items: center;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  text-decoration: none;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-primary { background: #40916c; color: white; }
.btn-primary:hover:not(:disabled) { background: #2d6a4f; }
.btn-danger { background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5; }
.btn-danger:hover:not(:disabled) { background: #fecaca; }
.btn-detail { background: #dbeafe; color: #1d4ed8; }
.btn-bulk { background: #f59e0b; color: white; }
.btn-bulk:hover:not(:disabled) { background: #d97706; }
.btn-ghost { background: transparent; color: #6b7280; }
/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: white;
  border-radius: 12px;
  width: 560px;
  max-width: 95vw;
  max-height: 80vh;
  overflow-y: auto;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
}
.modal-header h2 { font-size: 16px; font-weight: 700; }
.modal-close { background: none; border: none; font-size: 20px; cursor: pointer; color: #6b7280; }
.modal-body { padding: 20px; }
.detail-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 16px; }
.detail-table th {
  width: 90px;
  padding: 7px 10px;
  text-align: left;
  font-weight: 600;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}
.detail-table td { padding: 7px 10px; border-bottom: 1px solid #f3f4f6; }
.sign-img { max-width: 100%; max-height: 120px; border: 1px solid #e5e7eb; border-radius: 4px; background: #fff; display: block; }
.bulk-desc { font-size: 14px; color: #374151; margin-bottom: 14px; }
.bulk-list-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-bottom: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}
.bulk-list-table th {
  background: #f9fafb;
  padding: 7px 10px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid #e5e7eb;
}
.bulk-list-table td { padding: 7px 10px; border-bottom: 1px solid #f3f4f6; }
.bulk-list-table tr:last-child td { border-bottom: none; }
.comment-section, .reject-section { margin-bottom: 14px; }
.comment-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #374151;
}
.comment-label.required::after { content: ' *'; color: #ef4444; }
.comment-input {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
  resize: vertical;
  box-sizing: border-box;
}
.error-msg {
  margin-bottom: 12px;
  color: #ef4444;
  font-size: 13px;
  padding: 8px 12px;
  background: #fef2f2;
  border-radius: 6px;
}
.modal-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
</style>

