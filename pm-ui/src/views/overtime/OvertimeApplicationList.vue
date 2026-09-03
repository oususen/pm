<template>
  <div class="ot-list-page">
    <div class="page-header">
      <h1 class="page-title">{{ t('overtimeList.pageTitle') }} <DataSourceDialog title="残業申請一覧" :sources="dsSources" /></h1>
      <RouterLink to="/overtime/apply" class="btn btn-primary">{{ t('overtimeList.newApplication') }}</RouterLink>
    </div>

    <!-- フィルター -->
    <div class="filters">
      <input type="date" v-model="filters.work_date__gte" class="filter-input" />
      <span>〜</span>
      <input type="date" v-model="filters.work_date__lte" class="filter-input" />
      <select v-model="filters.status" class="filter-select">
        <option value="">{{ t('overtimeList.allStatus') }}</option>
        <option value="draft">{{ t('overtimeList.status.draft') }}</option>
        <option value="submitted">{{ t('overtimeList.status.submitted') }}</option>
        <option value="approved_supervisor">{{ t('overtimeList.status.approvedSupervisor') }}</option>
        <option value="approved_chief">{{ t('overtimeList.status.approvedChief') }}</option>
        <option value="approved_manager">{{ t('overtimeList.status.approvedManager') }}</option>
        <option value="rejected">{{ t('overtimeList.status.rejected') }}</option>
      </select>
      <select v-if="canFilterOrganization" v-model="filterSection" class="filter-select">
        <option value="">全係</option>
        <option v-for="section in sectionOptions" :key="section" :value="section">{{ section }}</option>
      </select>
      <select v-if="canFilterOrganization" v-model="filterTeam" class="filter-select">
        <option value="">{{ t('overtimeList.allTeams') }}</option>
        <option v-for="tm in teamOptions" :key="tm" :value="tm">{{ tm }}</option>
      </select>
      <select v-if="canFilterOrganization" v-model="filterGroup" class="filter-select">
        <option value="">{{ t('overtimeList.allGroups') }}</option>
        <option v-for="g in groupOptions" :key="g" :value="g">{{ g }}</option>
      </select>
      <button class="btn btn-secondary" @click="fetchList">{{ t('overtimeList.search') }}</button>
      <button class="btn btn-pdf" @click="downloadPdf">{{ t('overtimeList.pdfExport') }}</button>
      <label class="type-check-label">
        <input type="checkbox" v-model="excludeRejected" />
        {{ t('overtimeList.excludeRejected') }}
      </label>
    </div>
    <div class="filters" v-if="applications.length">
      <span class="type-checkboxes">
        <label v-for="tp in typeOptions" :key="tp.value" class="type-check-label">
          <input type="checkbox" :value="tp.value" v-model="filterTypes" />
          {{ tp.label }}
        </label>
      </span>
      <select v-model="filterName" class="filter-select">
        <option value="">{{ t('overtimeList.allMembers') }}</option>
        <option v-for="n in nameOptions" :key="n" :value="n">{{ n }}</option>
      </select>
      <select v-model="filterDate" class="filter-select">
        <option value="">{{ t('overtimeList.allDates') }}</option>
        <option v-for="d in dateOptions" :key="d" :value="d">{{ d }}</option>
      </select>
    </div>

    <div v-if="hasSearched && loading" class="loading">{{ t('overtimeList.loading') }}</div>
    <div v-else-if="hasSearched && !applications.length" class="empty">{{ t('overtimeList.empty') }}</div>
    <div v-else-if="hasSearched && !filteredApplications.length" class="empty">{{ t('overtimeList.emptyFilter') }}</div>
    <template v-else>
      <div class="table-wrap">
      <table class="ot-table">
        <thead>
          <tr>
            <th>{{ t('overtimeList.col.workDate') }}</th>
            <th>{{ t('overtimeList.col.team') }}</th>
            <th>{{ t('overtimeList.col.group') }}</th>
            <th>{{ t('overtimeList.col.type') }}</th>
            <th>{{ t('overtimeList.col.applicant') }}</th>
            <th>{{ t('overtimeList.col.workTime') }}</th>
            <th>{{ t('overtimeList.col.overtimeRange') }}</th>
            <th>{{ t('overtimeList.col.hours') }}</th>
            <th>{{ t('overtimeList.col.reason') }}</th>
            <th>{{ t('overtimeList.col.status') }}</th>
            <th>{{ t('overtimeList.col.submittedAt') }}</th>
            <th>{{ t('overtimeList.col.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="app in pagedApplications" :key="app.id">
            <td>{{ app.work_date }}</td>
            <td>{{ app.team_name || '-' }}</td>
            <td>{{ app.group_name || '-' }}</td>
            <td>{{ app.type_display }}</td>
            <td>
              <div>{{ app.applicant_name }}</div>
              <div v-if="app.is_proxy_application" class="proxy-note">{{ t('overtimeList.proxyNote', { name: app.created_by_name }) }}</div>
            </td>
            <td class="nowrap">{{ app.work_start_time || '-' }}{{ app.work_start_time ? ' 〜 ' + (app.scheduled_end_time || '-') : '' }}</td>
            <td class="nowrap">{{ app.start_time }} 〜 {{ app.end_time }}</td>
            <td class="num">
              {{ (Math.round((parseFloat(app.hours) + parseFloat(app.midnight_hours)) * 10) / 10) }}H
              <span v-if="app.midnight_hours > 0" class="midnight-tag">{{ t('overtimeList.midnight', { hours: app.midnight_hours }) }}</span>
            </td>
            <td class="reason-cell">{{ app.reason || '-' }}</td>
            <td>
              <span class="status-badge" :class="'status-' + app.status">
                {{ app.status_display }}
              </span>
            </td>
            <td class="nowrap">{{ app.submitted_at ? formatDateTime(app.submitted_at) : '-' }}</td>
            <td class="actions">
              <RouterLink
                v-if="app.can_edit"
                :to="`/overtime/apply/${app.id}`"
                class="btn btn-sm btn-secondary"
              >{{ t('overtimeList.edit') }}</RouterLink>
              <button
                v-if="app.can_edit"
                class="btn btn-sm btn-danger"
                @click="deleteApp(app)"
              >{{ app.status === 'submitted' ? t('overtimeList.cancel') : t('overtimeList.delete') }}</button>
              <button
                class="btn btn-sm btn-ghost"
                @click="openDetail(app)"
              >{{ t('overtimeList.detail') }}</button>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="total-row">
            <td colspan="7" class="total-label">{{ t('overtimeList.total', { count: filteredApplications.length }) }}</td>
            <td class="num">
              <span class="total-hours">{{ totalHours }}H</span>
              <span v-if="totalMidnight > 0" class="midnight-tag">{{ t('overtimeList.midnight', { hours: totalMidnight }) }}</span>
            </td>
            <td colspan="3"></td>
          </tr>
        </tfoot>
      </table>
      </div>
      <!-- ページネーション -->
      <div v-if="totalPages > 1" class="pagination">
        <button class="page-btn" :disabled="currentPage <= 1" @click="currentPage = 1">«</button>
        <button class="page-btn" :disabled="currentPage <= 1" @click="currentPage--">‹</button>
        <template v-for="p in totalPages" :key="p">
          <button
            v-if="p === 1 || p === totalPages || (p >= currentPage - 2 && p <= currentPage + 2)"
            class="page-btn" :class="{ active: p === currentPage }"
            @click="currentPage = p"
          >{{ p }}</button>
          <span v-else-if="p === currentPage - 3 || p === currentPage + 3" class="page-dots">…</span>
        </template>
        <button class="page-btn" :disabled="currentPage >= totalPages" @click="currentPage++">›</button>
        <button class="page-btn" :disabled="currentPage >= totalPages" @click="currentPage = totalPages">»</button>
        <span class="page-info">{{ t('overtimeList.pageInfo', { total: filteredApplications.length, from: (currentPage-1)*pageSize+1, to: Math.min(currentPage*pageSize, filteredApplications.length) }) }}</span>
      </div>
    </template>

    <!-- 詳細モーダル -->
    <div v-if="detailApp" class="modal-overlay" @click.self="detailApp = null">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ t('overtimeList.modal.title') }}</h2>
          <button class="modal-close" @click="detailApp = null">×</button>
        </div>
        <div class="modal-body">
          <table class="detail-table">
            <tbody>
              <tr><th>{{ t('overtimeList.modal.workDate') }}</th><td>{{ detailApp.work_date }}</td></tr>
              <tr><th>{{ t('overtimeList.modal.type') }}</th><td>{{ detailApp.type_display }}</td></tr>
              <tr v-if="detailApp.is_proxy_application"><th>{{ t('overtimeList.modal.proxyApplicant') }}</th><td>{{ detailApp.created_by_name }}</td></tr>
              <tr v-if="detailApp.work_start_time || detailApp.scheduled_end_time">
                <th>{{ t('overtimeList.modal.workTime') }}</th>
                <td>{{ detailApp.work_start_time || '-' }} 〜 {{ detailApp.scheduled_end_time || '-' }}（{{ t('overtimeList.modal.scheduled') }}）</td>
              </tr>
              <tr><th>{{ t('overtimeList.modal.overtimeRange') }}</th><td>{{ detailApp.start_time }} 〜 {{ detailApp.end_time }}</td></tr>
              <tr>
                <th>{{ t('overtimeList.modal.hours') }}</th>
                <td>{{ Math.round((parseFloat(detailApp.hours) + parseFloat(detailApp.midnight_hours)) * 10) / 10 }}H（{{ t('overtimeList.modal.midnightHours') }}: {{ detailApp.midnight_hours }}H）</td>
              </tr>
              <tr><th>{{ t('overtimeList.modal.reason') }}</th><td>{{ detailApp.reason || '-' }}</td></tr>
              <tr><th>{{ t('overtimeList.modal.status') }}</th><td>
                <span class="status-badge" :class="'status-' + detailApp.status">
                  {{ detailApp.status_display }}
                </span>
              </td></tr>
              <tr v-if="detailApp.rejection_reason">
                <th>{{ t('overtimeList.modal.rejectionReason') }}</th>
                <td class="rejection">{{ detailApp.rejection_reason }}</td>
              </tr>
              <tr v-if="detailApp.signature">
                <th>{{ t('overtimeList.modal.sign') }}</th>
                <td><img :src="detailApp.signature" alt="signature" class="sign-img" /></td>
              </tr>
            </tbody>
          </table>

          <div class="approval-log-section">
            <h3>{{ t('overtimeList.modal.approvalLog') }}</h3>
            <div v-if="!detailApp.approval_logs.length" class="empty-log">{{ t('overtimeList.modal.noLog') }}</div>
            <table v-else class="log-table">
              <thead><tr>
                <th>{{ t('overtimeList.modal.logCol.role') }}</th>
                <th>{{ t('overtimeList.modal.logCol.approver') }}</th>
                <th>{{ t('overtimeList.modal.logCol.status') }}</th>
                <th>{{ t('overtimeList.modal.logCol.comment') }}</th>
                <th>{{ t('overtimeList.modal.logCol.actedAt') }}</th>
              </tr></thead>
              <tbody>
                <tr v-for="log in detailApp.approval_logs" :key="log.id">
                  <td>{{ log.role_display }}</td>
                  <td>{{ log.approver_name || '-' }}</td>
                  <td>
                    <span class="log-status" :class="'log-' + log.status">{{ log.status_display }}</span>
                  </td>
                  <td>{{ log.comment || '-' }}</td>
                  <td>{{ log.acted_at ? formatDateTime(log.acted_at) : '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="detailApp.can_cancel_supervisor_approval" class="modal-actions">
            <button
              class="btn btn-warning"
              :disabled="supervisorCanceling"
              @click="cancelSupervisorApproval"
            >
              {{ supervisorCanceling ? '取消中...' : '班長承認取消' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '@/api/client'
import { t } from '@/i18n'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_overtime_application', desc: '残業申請の取得・削除・PDF出力' },
]

const applications = ref([])
const loading = ref(false)
const hasSearched = ref(false)
const detailApp = ref(null)
const supervisorCanceling = ref(false)
const currentPage = ref(1)
const pageSize = 30

const organizationSections = ref([])
const organizationTeams = ref([])
const organizationUnits = ref([])
const filterSection = ref('')
const filterTeam = ref('')
const filterGroup = ref('')
const filterTypes = ref([])
const filterName = ref('')
const filterDate = ref('')
const excludeRejected = ref(false)

const TYPE_KEYS = [
  { value: 'overtime', key: 'overtime.type.overtime' },
  { value: 'holiday', key: 'overtime.type.holiday' },
  { value: 'half_day_am', key: 'overtime.type.halfDayAm' },
  { value: 'half_day_pm', key: 'overtime.type.halfDayPm' },
  { value: 'paid_leave', key: 'overtime.type.paidLeave' },
  { value: 'paid_leave_consec', key: 'overtime.type.paidLeaveConsec' },
]

const typeOptions = computed(() =>
  TYPE_KEYS.map(tk => ({ value: tk.value, label: t(tk.key) }))
)
const canFilterOrganization = computed(() =>
  ['leader', 'supervisor', 'chief', 'manager'].includes(authState.user?.profile?.role)
)

const sectionOptions = computed(() =>
  organizationSections.value.map(section => section.name)
)
const teamOptions = computed(() =>
  organizationTeams.value
    .filter((team) => {
      if (!filterSection.value) return true
      const section = organizationSections.value.find(item => Number(item.id) === Number(team.parent))
      return section?.name === filterSection.value
    })
    .map(team => team.name)
)
const groupOptions = computed(() => {
  const targetTeam = organizationTeams.value.find(team => team.name === filterTeam.value)
  const filteredUnits = targetTeam
    ? organizationUnits.value.filter(unit => Number(unit.parent) === Number(targetTeam.id))
    : organizationUnits.value.filter((unit) => {
        if (!filterSection.value) return true
        const team = organizationTeams.value.find(item => Number(item.id) === Number(unit.parent))
        if (!team) return false
        const section = organizationSections.value.find(item => Number(item.id) === Number(team.parent))
        return section?.name === filterSection.value
      })
  return filteredUnits.map(unit => unit.name)
})
const nameOptions = computed(() =>
  [...new Set(applications.value.map(a => a.applicant_name).filter(Boolean))].sort()
)
const dateOptions = computed(() =>
  [...new Set(applications.value.map(a => a.work_date).filter(Boolean))].sort().reverse()
)
const filteredApplications = computed(() =>
  applications.value.filter(a =>
    (!filters.value.status || a.status === filters.value.status) &&
    (!filters.value.work_date__gte || a.work_date >= filters.value.work_date__gte) &&
    (!filters.value.work_date__lte || a.work_date <= filters.value.work_date__lte) &&
    (!filterSection.value || (() => {
      const team = organizationTeams.value.find(item => item.name === a.team_name)
      if (!team) return false
      const section = organizationSections.value.find(item => Number(item.id) === Number(team.parent))
      return section?.name === filterSection.value
    })()) &&
    (!filterTeam.value || a.team_name === filterTeam.value) &&
    (!filterGroup.value || a.group_name === filterGroup.value) &&
    (!filterTypes.value.length || filterTypes.value.includes(a.application_type)) &&
    (!filterName.value || a.applicant_name === filterName.value) &&
    (!filterDate.value || a.work_date === filterDate.value) &&
    (!excludeRejected.value || a.status !== 'rejected')
  ).sort((a, b) => {
    const da = a.status === 'draft' ? 0 : 1
    const db = b.status === 'draft' ? 0 : 1
    return da - db
  })
)
const totalPages = computed(() => Math.ceil(filteredApplications.value.length / pageSize) || 1)
const pagedApplications = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredApplications.value.slice(start, start + pageSize)
})
const totalHours = computed(() =>
  Math.round(filteredApplications.value.reduce((sum, a) =>
    sum + parseFloat(a.hours) + parseFloat(a.midnight_hours), 0
  ) * 10) / 10
)
const totalMidnight = computed(() =>
  Math.round(filteredApplications.value.reduce((sum, a) =>
    sum + parseFloat(a.midnight_hours), 0
  ) * 10) / 10
)

function formatDateInput(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function getDefaultFromDate() {
  const date = new Date()
  date.setDate(date.getDate() - 10)
  return formatDateInput(date)
}

const filters = ref({
  work_date__gte: getDefaultFromDate(),
  work_date__lte: '',
  status: '',
})

watch([filterSection, filterTeam, filterGroup, filterTypes, filterName, filterDate, excludeRejected, filters], () => {
  currentPage.value = 1
}, { deep: true })

watch(filterSection, () => {
  filterTeam.value = ''
  filterGroup.value = ''
})

watch(groupOptions, (options) => {
  if (filterGroup.value && !options.includes(filterGroup.value)) {
    filterGroup.value = ''
  }
})

watch(filterTeam, () => {
  filterGroup.value = ''
})

function formatDateTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function fetchList() {
  loading.value = true
  hasSearched.value = true
  try {
    const res = await api.overtime.getApplications(buildQueryParams())
    applications.value = res.data?.results || res.data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function openDetail(app) {
  detailApp.value = app
}

async function cancelSupervisorApproval() {
  if (!detailApp.value) return
  if (!confirm(`${detailApp.value.work_date} の班長承認を取り消しますか？`)) return
  supervisorCanceling.value = true
  try {
    const res = await api.overtime.cancelSupervisorApproval(detailApp.value.id)
    const updated = res.data
    applications.value = applications.value.map((app) => (
      app.id === updated.id ? updated : app
    ))
    detailApp.value = updated
  } catch (e) {
    alert('班長承認取消に失敗しました: ' + (e.response?.data?.detail || e.message))
  } finally {
    supervisorCanceling.value = false
  }
}

async function deleteApp(app) {
  const msg = app.status === 'submitted'
    ? t('overtimeList.confirm.cancel', { date: app.work_date })
    : t('overtimeList.confirm.delete', { date: app.work_date })
  if (!confirm(msg)) return
  try {
    await api.overtime.deleteApplication(app.id)
    await fetchList()
  } catch (e) {
    alert(t('overtimeList.error.deleteFailed') + (e.response?.data?.detail || e.message))
  }
}

async function downloadPdf() {
  try {
    const ids = filteredApplications.value.map(a => a.id).join(',')
    if (!ids) { alert(t('overtimeList.error.pdfEmpty')); return }
    const params = {
      ...buildQueryParams(),
      ids,
      team_name: filterTeam.value || t('overtimeList.allTeams'),
      group_name: filterGroup.value || t('overtimeList.allGroups'),
    }

    const res = await api.overtime.exportPdf(params)

    let filename = '残業申請書.pdf'
    const disposition = res.headers?.['content-disposition'] || ''
    const utf8Match = disposition.match(/filename\*=UTF-8''(.+)/)
    if (utf8Match) {
      filename = decodeURIComponent(utf8Match[1])
    } else {
      const plainMatch = disposition.match(/filename="?([^";\s]+)"?/)
      if (plainMatch) filename = plainMatch[1]
    }

    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    alert(t('overtimeList.error.pdfFailed') + (e.response?.data?.detail || e.message))
  }
}

function buildQueryParams() {
  const params = {}
  if (filters.value.work_date__gte) params.work_date__gte = filters.value.work_date__gte
  if (filters.value.work_date__lte) params.work_date__lte = filters.value.work_date__lte
  if (filters.value.status) params.status = filters.value.status
  if (filterSection.value) params.section_name = filterSection.value
  if (filterTeam.value) params.team_name = filterTeam.value
  if (filterGroup.value) params.group_name = filterGroup.value
  return params
}

async function loadOrganizationFilters() {
  if (!canFilterOrganization.value) {
    organizationTeams.value = []
    organizationUnits.value = []
    return
  }
  try {
    const [sectionsRes, teamsRes, unitsRes] = await Promise.all([
      api.accounts.getGroups(),
      api.accounts.getTeams(),
      api.accounts.getUnits(),
    ])
    organizationSections.value = Array.isArray(sectionsRes.data) ? sectionsRes.data : []
    organizationTeams.value = Array.isArray(teamsRes.data) ? teamsRes.data : []
    organizationUnits.value = Array.isArray(unitsRes.data) ? unitsRes.data : []
  } catch (e) {
    console.error(e)
    organizationSections.value = []
    organizationTeams.value = []
    organizationUnits.value = []
  }
}

onMounted(loadOrganizationFilters)
</script>

<style scoped>
.ot-list-page {
  padding: 24px;
  max-width: 100%;
  margin: 0 auto;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1f2a44;
}
.filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.total-row td {
  background: #f0fdf4;
  border-top: 2px solid #40916c;
  padding: 8px 12px;
  font-weight: 600;
}
.total-label { font-size: 13px; color: #374151; }
.total-hours { font-size: 15px; color: #40916c; }
.filter-input, .filter-select {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
}
.type-checkboxes {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.type-check-label {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.loading, .empty {
  text-align: center;
  color: #6b7280;
  padding: 40px;
}
.table-wrap {
  overflow-x: auto;
}
.ot-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}
.ot-table th {
  background: #f9fafb;
  padding: 6px 8px;
  text-align: center;
  font-weight: 600;
  color: #374151;
  border: 1px solid #d1d5db;
  white-space: nowrap;
}
.ot-table td {
  padding: 6px 8px;
  border: 1px solid #e5e7eb;
  vertical-align: middle;
  white-space: nowrap;
  text-align: center;
}
.ot-table tr:last-child td {
  border-bottom: none;
}
.num { text-align: right; }
.nowrap { white-space: nowrap; }
.reason-cell {
  max-width: 60px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.proxy-note {
  font-size: 11px;
  color: #6b7280;
}
.midnight-tag {
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  background: #f5f3ff;
  color: #7c3aed;
  padding: 1px 5px;
  border-radius: 3px;
}
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.status-draft { background: #f3f4f6; color: #6b7280; }
.status-submitted { background: #dbeafe; color: #1d4ed8; }
.status-approved_supervisor { background: #d1fae5; color: #065f46; }
.status-approved_chief { background: #a7f3d0; color: #065f46; }
.status-approved_manager { background: #6ee7b7; color: #065f46; font-weight: 700; }
.status-rejected { background: #fee2e2; color: #dc2626; }
.actions {
  display: flex;
  gap: 4px;
  white-space: nowrap;
}
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
.btn-sm { padding: 3px 8px; font-size: 12px; }
.btn-primary { background: #40916c; color: white; }
.btn-secondary { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
.btn-danger { background: #fee2e2; color: #dc2626; }
.btn-ghost { background: transparent; color: #6b7280; }
.btn-pdf { background: #7c3aed; color: white; }
.btn-pdf:hover { background: #6d28d9; }
/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 12px;
  flex-wrap: wrap;
}
.page-btn {
  min-width: 32px;
  height: 32px;
  padding: 0 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  font-size: 13px;
  cursor: pointer;
  color: #374151;
}
.page-btn:hover:not(:disabled):not(.active) { background: #f3f4f6; }
.page-btn.active { background: #40916c; color: white; border-color: #40916c; font-weight: 600; }
.page-btn:disabled { opacity: 0.4; cursor: default; }
.page-dots { color: #9ca3af; font-size: 13px; padding: 0 2px; }
.page-info { margin-left: 12px; font-size: 12px; color: #6b7280; }
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
  width: 640px;
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
.modal-close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #6b7280;
}
.modal-body { padding: 20px; }
.detail-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px; }
.detail-table th {
  width: 100px;
  padding: 8px 10px;
  text-align: left;
  font-weight: 600;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}
.detail-table td { padding: 8px 10px; border-bottom: 1px solid #f3f4f6; }
.rejection { color: #dc2626; }
.sign-img { max-width: 240px; border: 1px solid #e5e7eb; border-radius: 4px; }
.approval-log-section h3 { font-size: 14px; font-weight: 700; margin-bottom: 10px; }
.empty-log { color: #6b7280; font-size: 13px; }
.log-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.log-table th {
  background: #f9fafb;
  padding: 6px 8px;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}
.log-table td { padding: 6px 8px; border-bottom: 1px solid #f3f4f6; }
.log-status { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; }
.log-pending { background: #dbeafe; color: #1d4ed8; }
.log-approved { background: #d1fae5; color: #065f46; }
.log-rejected { background: #fee2e2; color: #dc2626; }
.modal-actions { margin-top: 14px; display: flex; justify-content: flex-end; }
.btn-warning { background: #b45309; color: white; }
</style>
