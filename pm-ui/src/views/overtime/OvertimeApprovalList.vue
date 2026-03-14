<template>
  <div class="ot-approval-page">
    <h1 class="page-title">承認待ち一覧</h1>

    <div v-if="loading" class="loading">読み込み中...</div>
    <div v-else-if="!applications.length" class="empty">承認待ちの申請はありません</div>
    <template v-else>
      <table class="ot-table">
        <thead>
          <tr>
            <th>実施日</th>
            <th>申請者</th>
            <th>種別</th>
            <th>時間帯</th>
            <th>時間数</th>
            <th>理由</th>
            <th>申請日時</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="app in applications" :key="app.id">
            <td class="nowrap">{{ app.work_date }}</td>
            <td>{{ app.applicant_name }}</td>
            <td>{{ app.type_display }}</td>
            <td class="nowrap">{{ app.start_time }} 〜 {{ app.end_time }}</td>
            <td class="num">
              {{ app.hours }}H
              <span v-if="app.midnight_hours > 0" class="midnight-tag">深夜{{ app.midnight_hours }}H</span>
            </td>
            <td class="reason-cell">{{ app.reason || '-' }}</td>
            <td class="nowrap">{{ app.submitted_at ? formatDateTime(app.submitted_at) : '-' }}</td>
            <td class="actions">
              <button class="btn btn-sm btn-detail" @click="openApprove(app)">確認・承認</button>
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <!-- 承認モーダル -->
    <div v-if="targetApp" class="modal-overlay" @click.self="targetApp = null">
      <div class="modal">
        <div class="modal-header">
          <h2>承認確認</h2>
          <button class="modal-close" @click="targetApp = null">×</button>
        </div>
        <div class="modal-body">
          <table class="detail-table">
            <tr><th>申請者</th><td>{{ targetApp.applicant_name }}</td></tr>
            <tr><th>実施日</th><td>{{ targetApp.work_date }}</td></tr>
            <tr><th>種別</th><td>{{ targetApp.type_display }}</td></tr>
            <tr v-if="targetApp.work_start_time || targetApp.scheduled_end_time">
              <th>勤務時間</th>
              <td>{{ targetApp.work_start_time || '-' }} 〜 {{ targetApp.scheduled_end_time || '-' }}（定時）</td>
            </tr>
            <tr><th>残業時間帯</th><td>{{ targetApp.start_time }} 〜 {{ targetApp.end_time }}</td></tr>
            <tr>
              <th>時間数</th>
              <td>{{ targetApp.hours }}H（深夜: {{ targetApp.midnight_hours }}H）</td>
            </tr>
            <tr><th>理由</th><td>{{ targetApp.reason || '-' }}</td></tr>
          </table>

          <div class="comment-section">
            <label class="comment-label">コメント（任意）</label>
            <textarea v-model="actionComment" class="comment-input" rows="2" placeholder="承認・却下のコメントを入力（省略可）"></textarea>
          </div>

          <div v-if="actionMode === 'reject'" class="reject-section">
            <label class="comment-label required">却下理由</label>
            <textarea v-model="rejectReason" class="comment-input" rows="2" placeholder="却下理由を入力してください" required></textarea>
          </div>

          <div v-if="actionError" class="error-msg">{{ actionError }}</div>

          <div class="modal-actions">
            <template v-if="actionMode === 'confirm'">
              <button class="btn btn-primary" @click="doApprove" :disabled="acting">承認する</button>
              <button class="btn btn-danger" @click="actionMode = 'reject'">却下する</button>
              <button class="btn btn-ghost" @click="targetApp = null">キャンセル</button>
            </template>
            <template v-else>
              <button class="btn btn-danger" @click="doReject" :disabled="acting || !rejectReason">却下する</button>
              <button class="btn btn-ghost" @click="actionMode = 'confirm'">戻る</button>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const applications = ref([])
const loading = ref(false)
const targetApp = ref(null)
const actionMode = ref('confirm')  // 'confirm' | 'reject'
const actionComment = ref('')
const rejectReason = ref('')
const actionError = ref('')
const acting = ref(false)

function formatDateTime(val) {
  if (!val) return '-'
  const d = new Date(val)
  return `${d.getFullYear()}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function fetchList() {
  loading.value = true
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

async function doApprove() {
  acting.value = true
  actionError.value = ''
  try {
    await api.overtime.approveApplication(targetApp.value.id, { comment: actionComment.value })
    targetApp.value = null
    await fetchList()
  } catch (e) {
    actionError.value = '承認に失敗しました: ' + (e.response?.data?.detail || e.message)
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
    actionError.value = '却下に失敗しました: ' + (e.response?.data?.detail || e.message)
  } finally {
    acting.value = false
  }
}

onMounted(fetchList)
</script>

<style scoped>
.ot-approval-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1f2a44;
  margin-bottom: 20px;
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
.num { text-align: right; }
.nowrap { white-space: nowrap; }
.reason-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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
