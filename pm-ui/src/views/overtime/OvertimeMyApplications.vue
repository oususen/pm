<template>
  <div class="ot-list-page">
    <div class="page-header">
      <h1 class="page-title">自分の申請一覧 <DataSourceDialog title="自分の申請一覧" :sources="dsSources" /></h1>
      <RouterLink to="/overtime/apply" class="btn btn-primary">新規申請</RouterLink>
    </div>

    <div class="filters">
      <input type="date" v-model="filters.dateFrom" class="filter-input" />
      <span>〜</span>
      <input type="date" v-model="filters.dateTo" class="filter-input" />
      <select v-model="filters.status" class="filter-select">
        <option value="">全ステータス</option>
        <option value="draft">下書き</option>
        <option value="submitted">提出済</option>
        <option value="approved_supervisor">係長承認済</option>
        <option value="approved_chief">課長承認済</option>
        <option value="approved_manager">部長承認済</option>
        <option value="rejected">差戻し</option>
      </select>
      <button class="btn btn-secondary" @click="fetchList">検索</button>
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else-if="!applications.length && hasSearched" class="empty">申請データがありません</div>
    <template v-else-if="applications.length">
      <div class="table-wrap">
        <table class="ot-table">
          <thead>
            <tr>
              <th>実施日</th>
              <th>種別</th>
              <th>勤務時間</th>
              <th>残業時間帯</th>
              <th>時間</th>
              <th>理由</th>
              <th>ステータス</th>
              <th>提出日時</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="app in filteredApplications" :key="app.id">
              <td>{{ app.work_date }}</td>
              <td>{{ app.type_display }}</td>
              <td class="nowrap">{{ app.work_start_time || '-' }}{{ app.work_start_time ? ' 〜 ' + (app.scheduled_end_time || '-') : '' }}</td>
              <td class="nowrap">{{ app.start_time }} 〜 {{ app.end_time }}</td>
              <td class="num">
                {{ totalAppHours(app) }}H
                <span v-if="app.midnight_hours > 0" class="midnight-tag">深夜{{ app.midnight_hours }}H</span>
              </td>
              <td class="reason-cell">{{ app.reason || '-' }}</td>
              <td>
                <span class="status-badge" :class="'status-' + app.status">{{ app.status_display }}</span>
              </td>
              <td class="nowrap">{{ formatDateTime(app.submitted_at) }}</td>
              <td class="actions">
                <RouterLink v-if="app.can_edit" :to="`/overtime/apply/${app.id}`" class="btn btn-sm btn-secondary">編集</RouterLink>
                <button v-if="app.can_edit" class="btn btn-sm btn-danger" @click="deleteApp(app)">
                  {{ app.status === 'submitted' ? '取消' : '削除' }}
                </button>
                <button class="btn btn-sm btn-ghost" @click="detailApp = app">詳細</button>
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="total-row">
              <td colspan="4" class="total-label">合計 {{ filteredApplications.length }}件</td>
              <td class="num">
                <span class="total-hours">{{ totalHours }}H</span>
                <span v-if="totalMidnight > 0" class="midnight-tag">深夜{{ totalMidnight }}H</span>
              </td>
              <td colspan="4"></td>
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
              <tr v-if="detailApp.work_start_time || detailApp.scheduled_end_time">
                <th>勤務時間</th>
                <td>{{ detailApp.work_start_time || '-' }} 〜 {{ detailApp.scheduled_end_time || '-' }}</td>
              </tr>
              <tr><th>残業時間帯</th><td>{{ detailApp.start_time }} 〜 {{ detailApp.end_time }}</td></tr>
              <tr>
                <th>時間</th>
                <td>{{ totalAppHours(detailApp) }}H（深夜: {{ detailApp.midnight_hours }}H）</td>
              </tr>
              <tr><th>理由</th><td>{{ detailApp.reason || '-' }}</td></tr>
              <tr><th>ステータス</th><td>
                <span class="status-badge" :class="'status-' + detailApp.status">{{ detailApp.status_display }}</span>
              </td></tr>
              <tr v-if="detailApp.rejection_reason">
                <th>差戻し理由</th><td class="rejection">{{ detailApp.rejection_reason }}</td>
              </tr>
              <tr v-if="detailApp.signature">
                <th>署名</th><td><img :src="detailApp.signature" alt="signature" class="sign-img" /></td>
              </tr>
            </tbody>
          </table>
          <div class="approval-log-section">
            <h3>承認履歴</h3>
            <div v-if="!detailApp.approval_logs?.length" class="empty-log">承認履歴はありません</div>
            <table v-else class="log-table">
              <thead><tr><th>役割</th><th>承認者</th><th>結果</th><th>コメント</th><th>日時</th></tr></thead>
              <tbody>
                <tr v-for="log in detailApp.approval_logs" :key="log.id">
                  <td>{{ log.role_display }}</td>
                  <td>{{ log.approver_name || '-' }}</td>
                  <td><span class="log-status" :class="'log-' + log.status">{{ log.status_display }}</span></td>
                  <td>{{ log.comment || '-' }}</td>
                  <td>{{ formatDateTime(log.acted_at) }}</td>
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
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_overtime_application', desc: '本人または自分が登録した申請の取得・取消・削除' },
  { op: '読み取り', table: 't_overtime_approval_log', desc: '申請詳細の承認履歴表示' },
  { op: '読み取り', table: 'auth_user / accounts_userprofile', desc: '本人・承認者の表示' },
]

const applications = ref([])
const loading = ref(false)
const hasSearched = ref(false)
const detailApp = ref(null)

function formatDateInput(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

const filters = ref({
  dateFrom: formatDateInput((() => { const d = new Date(); d.setDate(d.getDate() - 30); return d })()),
  dateTo: '',
  status: '',
})

const filteredApplications = computed(() =>
  applications.value.filter(a =>
    (!filters.value.dateFrom || a.work_date >= filters.value.dateFrom) &&
    (!filters.value.dateTo || a.work_date <= filters.value.dateTo) &&
    (!filters.value.status || a.status === filters.value.status)
  )
)

function totalAppHours(app) {
  return Math.round((parseFloat(app.hours) + parseFloat(app.midnight_hours)) * 10) / 10
}

const totalHours = computed(() =>
  Math.round(filteredApplications.value.reduce((s, a) => s + parseFloat(a.hours) + parseFloat(a.midnight_hours), 0) * 10) / 10
)
const totalMidnight = computed(() =>
  Math.round(filteredApplications.value.reduce((s, a) => s + parseFloat(a.midnight_hours), 0) * 10) / 10
)

function formatDateTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function fetchList() {
  loading.value = true
  hasSearched.value = true
  try {
    const userId = authState.user?.id
    const res = await api.overtime.getApplications({ applicant: userId })
    applications.value = res.data?.results || res.data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function deleteApp(app) {
  const msg = app.status === 'submitted'
    ? `${app.work_date}の申請を取り消しますか？`
    : `${app.work_date}の申請を削除しますか？`
  if (!confirm(msg)) return
  try {
    await api.overtime.deleteApplication(app.id)
    await fetchList()
  } catch (e) {
    alert('削除に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(fetchList)
</script>

<style scoped>
.ot-list-page { padding: 24px; max-width: 100%; margin: 0 auto; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: #1f2a44; }
.filters { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.filter-input, .filter-select { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px; font-size: 13px; }
.loading, .empty { text-align: center; color: #6b7280; padding: 40px; }
.table-wrap { overflow-x: auto; }
.ot-table { width: max-content; min-width: 100%; border-collapse: collapse; font-size: 12px; background: white; border-radius: 8px; border: 1px solid #e5e7eb; }
.ot-table th { background: #f9fafb; padding: 6px 8px; text-align: center; font-weight: 600; color: #374151; border: 1px solid #d1d5db; white-space: nowrap; }
.ot-table td { padding: 6px 8px; border: 1px solid #e5e7eb; vertical-align: middle; white-space: nowrap; text-align: center; }
.num { text-align: right; }
.nowrap { white-space: nowrap; }
.reason-cell { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.midnight-tag { display: inline-block; margin-left: 4px; font-size: 11px; background: #f5f3ff; color: #7c3aed; padding: 1px 5px; border-radius: 3px; }
.status-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.status-draft { background: #f3f4f6; color: #6b7280; }
.status-submitted { background: #dbeafe; color: #1d4ed8; }
.status-approved_supervisor { background: #d1fae5; color: #065f46; }
.status-approved_chief { background: #a7f3d0; color: #065f46; }
.status-approved_manager { background: #6ee7b7; color: #065f46; font-weight: 700; }
.status-rejected { background: #fee2e2; color: #dc2626; }
.total-row td { background: #f0fdf4; border-top: 2px solid #40916c; padding: 8px 12px; font-weight: 600; }
.total-label { font-size: 13px; color: #374151; }
.total-hours { font-size: 15px; color: #40916c; }
.actions { display: flex; gap: 4px; white-space: nowrap; }
.btn { display: inline-flex; align-items: center; padding: 7px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; text-decoration: none; }
.btn-sm { padding: 3px 8px; font-size: 12px; }
.btn-primary { background: #40916c; color: white; }
.btn-secondary { background: #f3f4f6; color: #374151; border: 1px solid #d1d5db; }
.btn-danger { background: #fee2e2; color: #dc2626; }
.btn-ghost { background: transparent; color: #6b7280; }
/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: white; border-radius: 12px; width: 640px; max-width: 95vw; max-height: 80vh; overflow-y: auto; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #e5e7eb; }
.modal-header h2 { font-size: 16px; font-weight: 700; }
.modal-close { background: none; border: none; font-size: 20px; cursor: pointer; color: #6b7280; }
.modal-body { padding: 20px; }
.detail-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 20px; }
.detail-table th { width: 100px; padding: 8px 10px; text-align: left; font-weight: 600; background: #f9fafb; border-bottom: 1px solid #e5e7eb; }
.detail-table td { padding: 8px 10px; border-bottom: 1px solid #f3f4f6; }
.rejection { color: #dc2626; }
.sign-img { max-width: 240px; border: 1px solid #e5e7eb; border-radius: 4px; }
.approval-log-section h3 { font-size: 14px; font-weight: 700; margin-bottom: 10px; }
.empty-log { color: #6b7280; font-size: 13px; }
.log-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.log-table th { background: #f9fafb; padding: 6px 8px; text-align: left; border-bottom: 1px solid #e5e7eb; }
.log-table td { padding: 6px 8px; border-bottom: 1px solid #f3f4f6; }
.log-status { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; }
.log-pending { background: #dbeafe; color: #1d4ed8; }
.log-approved { background: #d1fae5; color: #065f46; }
.log-rejected { background: #fee2e2; color: #dc2626; }
</style>
