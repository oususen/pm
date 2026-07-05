<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isCompleted ? '朝礼詳細' : '朝礼実行' }} <DataSourceDialog title="朝礼実行" :sources="dsSources" /></h1>
      <div class="page-actions">
        <RouterLink v-if="canEditMeetingActions" class="btn-secondary" :to="`/production/morning-meetings/${id}/edit`">編集</RouterLink>
        <RouterLink class="btn-secondary" to="/production/morning-meetings">一覧</RouterLink>
      </div>
    </div>

    <div v-if="meeting" class="page-content run-layout">
      <section class="summary-card">
        <div class="summary-grid">
          <div><strong>朝礼日:</strong> {{ meeting.meeting_date }}</div>
          <div><strong>状態:</strong> {{ meeting.status_display }}</div>
          <div><strong>対象部署:</strong> {{ joinNames(meeting.target_department_names) }}</div>
          <div><strong>対象ライン:</strong> {{ joinNames(meeting.target_line_names) }}</div>
          <div><strong>司会者:</strong> {{ meeting.facilitator_name || '-' }}</div>
          <div><strong>参加者:</strong> {{ meeting.participant_count }} 人</div>
        </div>
        <h2 class="summary-title">{{ meeting.title }}</h2>
        <div class="summary-block"><strong>議題</strong><p>{{ meeting.agenda || '未入力' }}</p></div>
        <div class="summary-block"><strong>連絡事項</strong><p>{{ meeting.notices || '未入力' }}</p></div>
        <div class="summary-block"><strong>注意事項</strong><p>{{ meeting.cautions || '未入力' }}</p></div>
        <div class="summary-block">
          <strong>資料</strong>
          <div v-if="meeting.attachments?.length" class="attachment-list">
            <a
              v-for="attachment in meeting.attachments"
              :key="attachment.id"
              class="attachment-link"
              :href="attachment.file_url"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span>{{ attachment.original_name }}</span>
              <span class="attachment-type">{{ attachment.file_type_label }}</span>
            </a>
          </div>
          <p v-else>未添付</p>
        </div>
        <div class="summary-block">
          <strong>実行メモ</strong>
          <textarea v-model="executionNote" rows="4" :readonly="!canEditMeetingActions"></textarea>
        </div>
        <div v-if="!isCompleted" class="run-actions">
          <button
            class="btn-primary"
            type="button"
            @click="startMeeting"
            :disabled="saving || !canEditMeetingActions"
          >
            開始
          </button>
          <button class="btn-secondary" type="button" @click="saveExecution" :disabled="saving || !canSaveParticipantChanges">
            参加者保存
          </button>
          <button class="btn-primary complete-btn" type="button" @click="completeMeeting" :disabled="saving || !canEditMeeting">
            完了
          </button>
        </div>
      </section>

      <section class="participants-card">
        <div class="participants-head">
          <h2>参加者確認</h2>
          <div class="participant-stats">
            出席 {{ presentCount }} / 欠席・遅刻 {{ absentCount }} / 未確認 {{ pendingCount }}
          </div>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>参加者</th>
              <th>所属</th>
              <th>状態</th>
              <th>備考</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in participants" :key="row.id">
              <td>{{ row.user_name }}</td>
              <td>{{ departmentPath(row) }}</td>
              <td>
                <select v-model="row.attendance_status" :disabled="!canEditParticipant(row)">
                  <option value="PENDING">未確認</option>
                  <option value="PRESENT">出席</option>
                  <option value="ABSENT">欠席</option>
                  <option value="LATE">遅刻</option>
                </select>
              </td>
              <td>
                <input v-model="row.remark" type="text" maxlength="255" :readonly="!canEditParticipant(row)" />
              </td>
            </tr>
            <tr v-if="!participants.length">
              <td colspan="4" class="empty-row">参加者が登録されていません</td>
            </tr>
          </tbody>
        </table>
      </section>

      <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import { hasPermission } from '@/router'

const props = defineProps({
  id: { type: [String, Number], required: true },
})

const dsSources = [
  { op: '読み書き', table: 't_morning_meeting', desc: '朝礼の開始・実行メモ・完了' },
  { op: '読み書き', table: 't_morning_meeting_participant', desc: '参加者確認状態の更新' },
]

const router = useRouter()
const meeting = ref(null)
const participants = ref([])
const executionNote = ref('')
const saving = ref(false)
const errorMessage = ref('')
const currentUserId = computed(() => Number(authState.user?.id || 0))
const isFacilitator = computed(() => Number(meeting.value?.facilitator || 0) === currentUserId.value)
const morningMeetingResource = 'production.morning_meeting'
const isCompleted = computed(() => meeting.value?.status === 'COMPLETED')

const pendingCount = computed(() => participants.value.filter((row) => row.attendance_status === 'PENDING').length)
const presentCount = computed(() => participants.value.filter((row) => row.attendance_status === 'PRESENT').length)
const absentCount = computed(() => participants.value.filter((row) => ['ABSENT', 'LATE'].includes(row.attendance_status)).length)
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
const canEditMeetingActions = computed(() => canEditMeeting.value && !isCompleted.value)
const canSaveParticipantChanges = computed(() => {
  if (isCompleted.value) return false
  if (isFacilitator.value) return true
  return participants.value.some((row) => Number(row.user) === currentUserId.value)
})

const departmentPath = (row) => {
  return [row.division_name, row.group_name, row.team_name, row.unit_name].filter(Boolean).join(' / ') || row.department_name || '-'
}

const joinNames = (values) => {
  if (!Array.isArray(values) || !values.length) return '-'
  return values.join(' / ')
}

const canEditParticipant = (row) => {
  if (isCompleted.value) return false
  if (isFacilitator.value) return true
  return Number(row.user) === currentUserId.value
}

const payload = () => ({
  execution_note: executionNote.value,
  participants: participants.value.map((row) => ({
    id: row.id,
    attendance_status: row.attendance_status,
    remark: row.remark || '',
  })),
})

const loadMeeting = async () => {
  const res = await api.morningMeetings.get(props.id)
  meeting.value = res.data
  participants.value = Array.isArray(res.data.participants)
    ? res.data.participants.map((row) => ({ ...row }))
    : []
  executionNote.value = res.data.execution_note || ''
}

const startMeeting = async () => {
  if (!canEditMeetingActions.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    await api.morningMeetings.start(props.id)
    await loadMeeting()
  } catch (error) {
    console.error('朝礼の開始に失敗しました:', error)
    errorMessage.value = error.response?.data?.detail || '朝礼の開始に失敗しました。'
  } finally {
    saving.value = false
  }
}

const saveExecution = async () => {
  saving.value = true
  errorMessage.value = ''
  try {
    await api.morningMeetings.saveExecution(props.id, payload())
    await loadMeeting()
  } catch (error) {
    console.error('朝礼実行内容の保存に失敗しました:', error)
    errorMessage.value = error.response?.data?.detail || '朝礼実行内容の保存に失敗しました。'
  } finally {
    saving.value = false
  }
}

const completeMeeting = async () => {
  if (!canEditMeetingActions.value) return
  if (!window.confirm('この朝礼を完了にします。よろしいですか？')) return
  saving.value = true
  errorMessage.value = ''
  try {
    await api.morningMeetings.complete(props.id, payload())
    await loadMeeting()
    window.alert('朝礼を完了しました。')
    router.push('/production/morning-meetings')
  } catch (error) {
    console.error('朝礼の完了に失敗しました:', error)
    errorMessage.value = error.response?.data?.detail || '朝礼の完了に失敗しました。'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadMeeting()
  } catch (error) {
    console.error('朝礼の取得に失敗しました:', error)
    errorMessage.value = '朝礼の取得に失敗しました。'
  }
})
</script>

<style scoped>
.run-layout {
  display: grid;
  gap: 16px;
}

.summary-card,
.participants-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px 12px;
  color: #334155;
}

.summary-title {
  margin: 14px 0 8px;
}

.summary-block {
  margin-top: 12px;
}

.summary-block p {
  margin: 6px 0 0;
  white-space: pre-wrap;
}

.attachment-list {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.attachment-link {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  border: 1px solid #dbeafe;
  background: #f8fbff;
  border-radius: 8px;
  padding: 8px 10px;
  color: #1d4ed8;
  text-decoration: none;
}

.attachment-type {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #dbeafe;
  color: #0f172a;
  padding: 4px 10px;
  font-size: 12px;
}

.summary-block textarea,
.participants-card input,
.participants-card select {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
}

.run-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.complete-btn {
  background: #15803d;
}

.participants-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.participants-head h2 {
  margin: 0;
}

.participant-stats {
  color: #475569;
}

.empty-row {
  text-align: center;
  color: #64748b;
  padding: 16px;
}

.error-box {
  color: #b91c1c;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .participants-head,
  .run-actions {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
