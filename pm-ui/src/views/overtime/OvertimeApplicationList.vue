<template>
  <div class="ot-list-page">
    <div class="page-header">
      <h1 class="page-title">残業申請 一覧</h1>
      <RouterLink to="/overtime/apply" class="btn btn-primary">＋ 新規申請</RouterLink>
    </div>

    <!-- フィルター -->
    <div class="filters">
      <input type="date" v-model="filters.work_date__gte" class="filter-input" />
      <span>〜</span>
      <input type="date" v-model="filters.work_date__lte" class="filter-input" />
      <select v-model="filters.status" class="filter-select">
        <option value="">全ステータス</option>
        <option value="draft">下書き</option>
        <option value="submitted">申請中</option>
        <option value="approved_supervisor">班長承認済み</option>
        <option value="approved_chief">係長承認済み</option>
        <option value="approved_manager">最終承認済み</option>
        <option value="rejected">却下</option>
      </select>
      <button class="btn btn-secondary" @click="fetchList">検索</button>
      <button class="btn btn-pdf" @click="downloadPdf">PDF出力</button>
    </div>
    <div class="filters" v-if="applications.length">
      <select v-model="filterTeam" class="filter-select">
        <option value="">全班</option>
        <option v-for="t in teamOptions" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filterGroup" class="filter-select">
        <option value="">全グループ</option>
        <option v-for="g in groupOptions" :key="g" :value="g">{{ g }}</option>
      </select>
      <select v-model="filterName" class="filter-select">
        <option value="">全員</option>
        <option v-for="n in nameOptions" :key="n" :value="n">{{ n }}</option>
      </select>
      <select v-model="filterDate" class="filter-select">
        <option value="">全日付</option>
        <option v-for="d in dateOptions" :key="d" :value="d">{{ d }}</option>
      </select>
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else-if="!applications.length" class="empty">申請がありません</div>
    <div v-else-if="!filteredApplications.length" class="empty">条件に一致する申請はありません</div>
    <template v-else>
      <div class="table-wrap">
      <table class="ot-table">
        <thead>
          <tr>
            <th>実施日</th>
            <th>班</th>
            <th>グループ</th>
            <th>種別</th>
            <th>申請者</th>
            <th>勤務時間</th>
            <th>残業時間帯</th>
            <th>時間数</th>
            <th>理由</th>
            <th>ステータス</th>
            <th>申請日時</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="app in filteredApplications" :key="app.id">
            <td>{{ app.work_date }}</td>
            <td>{{ app.team_name || '-' }}</td>
            <td>{{ app.group_name || '-' }}</td>
            <td>{{ app.type_display }}</td>
            <td>
              <div>{{ app.applicant_name }}</div>
              <div v-if="app.is_proxy_application" class="proxy-note">管理登録: {{ app.created_by_name }}</div>
            </td>
            <td class="nowrap">{{ app.work_start_time || '-' }}{{ app.work_start_time ? ' 〜 ' + (app.scheduled_end_time || '-') : '' }}</td>
            <td class="nowrap">{{ app.start_time }} 〜 {{ app.end_time }}</td>
            <td class="num">
              {{ (Math.round((parseFloat(app.hours) + parseFloat(app.midnight_hours)) * 10) / 10) }}H
              <span v-if="app.midnight_hours > 0" class="midnight-tag">深夜{{ app.midnight_hours }}H</span>
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
              >編集</RouterLink>
              <button
                v-if="app.can_edit"
                class="btn btn-sm btn-danger"
                @click="deleteApp(app)"
              >{{ app.status === 'submitted' ? 'キャンセル' : '削除' }}</button>
              <button
                class="btn btn-sm btn-ghost"
                @click="openDetail(app)"
              >詳細</button>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="total-row">
            <td colspan="7" class="total-label">合計（{{ filteredApplications.length }}件）</td>
            <td class="num">
              <span class="total-hours">{{ totalHours }}H</span>
              <span v-if="totalMidnight > 0" class="midnight-tag">深夜{{ totalMidnight }}H</span>
            </td>
            <td colspan="3"></td>
          </tr>
        </tfoot>
      </table>
      </div>
    </template>

    <!-- 詳細モーダル -->
    <div v-if="detailApp" class="modal-overlay" @click.self="detailApp = null">
      <div class="modal">
        <div class="modal-header">
          <h2>申請詳細</h2>
          <button class="modal-close" @click="detailApp = null">×</button>
        </div>
        <div class="modal-body">
          <table class="detail-table">
            <tbody>
              <tr><th>実施日</th><td>{{ detailApp.work_date }}</td></tr>
              <tr><th>種別</th><td>{{ detailApp.type_display }}</td></tr>
              <tr v-if="detailApp.is_proxy_application"><th>管理登録者</th><td>{{ detailApp.created_by_name }}</td></tr>
              <tr v-if="detailApp.work_start_time || detailApp.scheduled_end_time">
                <th>勤務時間</th>
                <td>{{ detailApp.work_start_time || '-' }} 〜 {{ detailApp.scheduled_end_time || '-' }}（定時）</td>
              </tr>
              <tr><th>残業時間帯</th><td>{{ detailApp.start_time }} 〜 {{ detailApp.end_time }}</td></tr>
              <tr>
                <th>時間数</th>
                <td>{{ Math.round((parseFloat(detailApp.hours) + parseFloat(detailApp.midnight_hours)) * 10) / 10 }}H（深夜: {{ detailApp.midnight_hours }}H）</td>
              </tr>
              <tr><th>理由</th><td>{{ detailApp.reason || '-' }}</td></tr>
              <tr><th>ステータス</th><td>
                <span class="status-badge" :class="'status-' + detailApp.status">
                  {{ detailApp.status_display }}
                </span>
              </td></tr>
              <tr v-if="detailApp.rejection_reason">
                <th>却下理由</th>
                <td class="rejection">{{ detailApp.rejection_reason }}</td>
              </tr>
              <tr v-if="detailApp.signature">
                <th>サイン</th>
                <td><img :src="detailApp.signature" alt="サイン" class="sign-img" /></td>
              </tr>
            </tbody>
          </table>

          <div class="approval-log-section">
            <h3>承認履歴</h3>
            <div v-if="!detailApp.approval_logs.length" class="empty-log">まだ承認アクションはありません</div>
            <table v-else class="log-table">
              <thead><tr><th>役割</th><th>承認者</th><th>状態</th><th>コメント</th><th>対応日時</th></tr></thead>
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
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'

const applications = ref([])
const loading = ref(false)
const detailApp = ref(null)

const filterTeam = ref('')
const filterGroup = ref('')
const filterName = ref('')
const filterDate = ref('')

const teamOptions = computed(() =>
  [...new Set(applications.value.map(a => a.team_name).filter(Boolean))].sort()
)
const groupOptions = computed(() =>
  [...new Set(applications.value.map(a => a.group_name).filter(Boolean))].sort()
)
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
    (!filterTeam.value || a.team_name === filterTeam.value) &&
    (!filterGroup.value || a.group_name === filterGroup.value) &&
    (!filterName.value || a.applicant_name === filterName.value) &&
    (!filterDate.value || a.work_date === filterDate.value)
  )
)
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

const filters = ref({
  work_date__gte: '',
  work_date__lte: '',
  status: '',
})

function formatDateTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function fetchList() {
  loading.value = true
  try {
    const res = await api.overtime.getApplications()
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

async function deleteApp(app) {
  const msg = app.status === 'submitted'
    ? `${app.work_date} の申請を取り消しますか？（承認依頼も取り消されます）`
    : `${app.work_date} の申請を削除しますか？`
  if (!confirm(msg)) return
  try {
    await api.overtime.deleteApplication(app.id)
    await fetchList()
  } catch (e) {
    alert('削除に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

async function downloadPdf() {
  try {
    const ids = filteredApplications.value.map(a => a.id).join(',')
    if (!ids) { alert('出力する申請がありません'); return }
    const params = {
      ids,
      team_name: filterTeam.value || '全班',
      group_name: filterGroup.value || '全グループ',
    }

    const res = await api.overtime.exportPdf(params)

    // Content-Disposition からファイル名を取得
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
    alert('PDF出力に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(fetchList)
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
</style>
