<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ pageTitle }} <DataSourceDialog title="朝礼作成/編集" :sources="dsSources" /></h1>
    </div>

    <div class="page-content form-card">
      <div v-if="sourceMeetingSummary" class="source-banner">
        <strong>複製元:</strong> {{ sourceMeetingSummary }}
      </div>

      <div class="form-grid">
        <div class="form-field">
          <label>朝礼日</label>
          <input v-model="form.meeting_date" type="date" />
          <div v-if="form.is_template" class="selection-meta">テンプレート作成時は未入力でも保存できます</div>
        </div>
        <div class="form-field">
          <label>状態</label>
          <select v-model="form.status">
            <option value="DRAFT">下書き</option>
            <option value="READY">準備完了</option>
          </select>
        </div>
        <div class="form-field wide">
          <label>タイトル</label>
          <input v-model.trim="form.title" type="text" maxlength="200" />
        </div>
        <div class="form-field wide template-toggle">
          <label class="checkbox-line">
            <input v-model="form.is_template" type="checkbox" />
            <span>テンプレートとして保存する</span>
          </label>
          <div class="selection-meta">テンプレートは一覧の「表示区分」で切り替えて利用します</div>
        </div>

        <div class="form-field wide selection-field">
          <div class="selection-header">
            <label>対象部署</label>
            <div class="selection-meta">選択中 {{ form.department_ids.length }} 件</div>
          </div>
          <div class="selection-chip-list">
            <span v-for="dept in selectedDepartments" :key="dept.id" class="selection-chip">
              {{ dept.name }}（{{ levelLabel(dept.level) }}）
            </span>
            <span v-if="!selectedDepartments.length" class="selection-empty">未選択</span>
          </div>
          <div class="selection-list">
            <label v-for="dept in departments" :key="dept.id" class="selection-item">
              <input
                :checked="form.department_ids.includes(Number(dept.id))"
                type="checkbox"
                @change="toggleSelection('department_ids', dept.id, $event.target.checked)"
              />
              <span>{{ dept.name }}（{{ levelLabel(dept.level) }}）</span>
            </label>
          </div>
        </div>

        <div class="form-field wide selection-field">
          <div class="selection-header">
            <label>対象ライン</label>
            <div class="selection-meta">選択中 {{ form.line_ids.length }} 件</div>
          </div>
          <div class="selection-chip-list">
            <span v-for="line in selectedLines" :key="line.id" class="selection-chip">
              {{ line.line_code }} {{ line.line_name }}
            </span>
            <span v-if="!selectedLines.length" class="selection-empty">未選択</span>
          </div>
          <div class="selection-list" :class="{ disabled: !hasDepartmentSelection }">
            <label v-for="line in filteredLines" :key="line.id" class="selection-item">
              <input
                :checked="form.line_ids.includes(Number(line.id))"
                type="checkbox"
                :disabled="!hasDepartmentSelection"
                @change="toggleSelection('line_ids', line.id, $event.target.checked)"
              />
              <span>{{ line.line_code }} {{ line.line_name }}</span>
            </label>
            <div v-if="!hasDepartmentSelection" class="selection-empty">先に対象部署を選択してください</div>
            <div v-else-if="!filteredLines.length" class="selection-empty">選択部署に紐づく社内ラインがありません</div>
          </div>
        </div>

        <div class="form-field wide">
          <label>司会者</label>
          <select v-model="form.facilitator">
            <option value="">未選択</option>
            <option v-for="user in users" :key="user.id" :value="String(user.id)">
              {{ userLabel(user) }}
            </option>
          </select>
        </div>
        <div class="form-field wide">
          <label>議題</label>
          <textarea v-model="form.agenda" rows="4"></textarea>
        </div>
        <div class="form-field wide">
          <label>連絡事項</label>
          <textarea v-model="form.notices" rows="4"></textarea>
        </div>
        <div class="form-field wide">
          <label>注意事項</label>
          <textarea v-model="form.cautions" rows="4"></textarea>
        </div>
      </div>

      <div class="attachments-card">
        <div class="section-header">
          <h2>資料添付</h2>
          <div class="section-meta">PDF / 写真 / Excel を複数添付できます</div>
        </div>
        <input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp,.webp,.xlsx,.xls,.xlsm" @change="handleFileChange" />

        <div v-if="newAttachmentFiles.length" class="attachment-block">
          <div class="attachment-subtitle">新規追加予定</div>
          <div class="attachment-list">
            <div v-for="(file, index) in newAttachmentFiles" :key="`${file.name}-${index}`" class="attachment-item">
              <span>{{ file.name }}</span>
              <button class="btn-text danger-text" type="button" @click="removeNewAttachment(index)">除外</button>
            </div>
          </div>
        </div>

        <div v-if="activeExistingAttachments.length" class="attachment-block">
          <div class="attachment-subtitle">既存資料</div>
          <div class="attachment-list">
            <div v-for="attachment in activeExistingAttachments" :key="attachment.id" class="attachment-item">
              <button class="btn-text attachment-name" type="button" @click="openAttachmentPreview(attachment)">
                {{ attachment.original_name }}
              </button>
              <span class="attachment-type">{{ attachment.file_type_label }}</span>
              <button class="btn-text" type="button" @click="openAttachmentPreview(attachment)">プレビュー</button>
              <button class="btn-text danger-text" type="button" @click="markAttachmentForDelete(attachment.id)">削除</button>
            </div>
          </div>
        </div>

        <div v-if="removedAttachments.length" class="attachment-block">
          <div class="attachment-subtitle">削除予定</div>
          <div class="attachment-list">
            <div v-for="attachment in removedAttachments" :key="attachment.id" class="attachment-item removed">
              <span>{{ attachment.original_name }}</span>
              <button class="btn-text" type="button" @click="restoreAttachment(attachment.id)">戻す</button>
            </div>
          </div>
        </div>
      </div>

      <div class="participants-card">
        <div class="participants-header">
          <h2>参加者</h2>
          <div class="participants-actions">
            <button class="btn-secondary" type="button" @click="applyDepartmentMembers">部署メンバー反映</button>
            <button class="btn-secondary" type="button" @click="toggleAllFiltered(true)">表示中を全選択</button>
            <button class="btn-secondary" type="button" @click="toggleAllFiltered(false)">表示中を解除</button>
          </div>
        </div>
        <div class="participants-summary">選択中 {{ form.participant_user_ids.length }} 人</div>
        <div class="participants-list">
          <label v-for="user in filteredUsers" :key="user.id" class="participant-item">
            <input :checked="isSelected(user.id)" type="checkbox" @change="toggleParticipant(user.id, $event.target.checked)" />
            <span>{{ userLabel(user) }}</span>
          </label>
          <div v-if="!filteredUsers.length" class="empty-participants">対象ユーザーがいません</div>
        </div>
      </div>

      <div v-if="errorMessage" class="error-box">{{ errorMessage }}</div>

      <div class="form-actions">
        <button class="btn-primary" type="button" @click="save" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <RouterLink class="btn-secondary" to="/production/morning-meetings">一覧へ戻る</RouterLink>
      </div>
    </div>

    <div v-if="previewDialog.visible" class="modal-overlay" @click.self="closeAttachmentPreview">
      <div class="preview-dialog">
        <div class="preview-dialog-header">
          <strong>{{ previewDialog.name }}</strong>
          <button class="btn-secondary" type="button" @click="closeAttachmentPreview">閉じる</button>
        </div>
        <div v-if="previewDialog.type === 'IMAGE'" class="preview-body image-preview">
          <img :src="previewDialog.url" :alt="previewDialog.name" />
        </div>
        <div v-else-if="previewDialog.type === 'PDF'" class="preview-body">
          <iframe :src="previewDialog.url" title="PDFプレビュー"></iframe>
        </div>
        <div v-else class="preview-body preview-note">
          <p>Excel は画面内プレビュー非対応です。</p>
          <a :href="previewDialog.url" target="_blank" rel="noopener noreferrer">ファイルを開く</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import { getBusinessISODate } from '@/utils/dateUtil'

const props = defineProps({
  id: { type: [String, Number], default: null },
})

const dsSources = [
  { op: '読み書き', table: 't_morning_meeting', desc: '朝礼の作成・更新' },
  { op: '読み書き', table: 't_morning_meeting_participant', desc: '参加者設定の保存' },
  { op: '読み書き', table: 't_morning_meeting_attachment', desc: '資料添付の登録・削除' },
  { op: '読み取り', table: 'accounts_department / auth_user / t_line', desc: '部署・参加者・ライン候補の取得' },
]

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => Boolean(props.id))
const isTemplateMode = computed(() => route.query.template === '1')
const sourceMeetingId = computed(() => {
  const raw = route.query.source_id
  return raw ? Number(raw) : null
})
const pageTitle = computed(() => {
  if (isEdit.value) return '朝礼編集'
  return form.value.is_template || isTemplateMode.value ? '朝礼テンプレート作成' : '朝礼作成'
})
const saving = ref(false)
const errorMessage = ref('')
const departments = ref([])
const lines = ref([])
const unitLineMappings = ref([])
const users = ref([])
const existingAttachments = ref([])
const newAttachmentFiles = ref([])
const sourceMeetingSummary = ref('')
const previewDialog = ref({
  visible: false,
  type: '',
  name: '',
  url: '',
})
const form = ref({
  meeting_date: getBusinessISODate(),
  title: '',
  is_template: false,
  department_ids: [],
  line_ids: [],
  facilitator: String(authState.user?.id || ''),
  agenda: '',
  notices: '',
  cautions: '',
  status: 'DRAFT',
  participant_user_ids: [],
  deleted_attachment_ids: [],
})

const levelLabel = (level) => {
  const map = {
    division: '事業部',
    group: '係',
    team: '班',
    unit: 'グループ',
  }
  return map[level] || level
}

const userLabel = (user) => {
  const name = `${user.last_name || ''} ${user.first_name || ''}`.trim() || user.username || `ID:${user.id}`
  const team = user.profile?.team_name || ''
  const unit = user.profile?.unit_name || ''
  const org = [team, unit].filter(Boolean).join(' / ')
  return org ? `${name}（${org}）` : name
}

const isSelected = (userId) => form.value.participant_user_ids.includes(Number(userId))
const hasDepartmentSelection = computed(() => form.value.department_ids.length > 0)

const departmentChildrenMap = computed(() => {
  const childrenMap = new Map()
  departments.value.forEach((department) => {
    const parentId = Number(department.parent || 0)
    if (!childrenMap.has(parentId)) {
      childrenMap.set(parentId, [])
    }
    childrenMap.get(parentId).push(department)
  })
  return childrenMap
})

const selectedDepartments = computed(() => {
  const selectedIds = new Set(form.value.department_ids.map(Number))
  return departments.value.filter((department) => selectedIds.has(Number(department.id)))
})

const selectedLines = computed(() => {
  const selectedIds = new Set(form.value.line_ids.map(Number))
  return lines.value.filter((line) => selectedIds.has(Number(line.id)))
})

const activeExistingAttachments = computed(() => {
  const removedIds = new Set(form.value.deleted_attachment_ids.map(Number))
  return existingAttachments.value.filter((attachment) => !removedIds.has(Number(attachment.id)))
})

const removedAttachments = computed(() => {
  const removedIds = new Set(form.value.deleted_attachment_ids.map(Number))
  return existingAttachments.value.filter((attachment) => removedIds.has(Number(attachment.id)))
})

const collectDescendantUnitIds = (departmentIds) => {
  const startDepartments = departments.value.filter((item) => departmentIds.includes(Number(item.id)))
  if (!startDepartments.length) return []

  const unitIds = new Set()
  const queue = [...startDepartments]
  while (queue.length) {
    const current = queue.shift()
    if (!current) continue
    if (current.level === 'unit') {
      unitIds.add(Number(current.id))
      continue
    }
    const children = departmentChildrenMap.value.get(Number(current.id)) || []
    queue.push(...children)
  }
  return [...unitIds]
}

const userMatchesDepartment = (user, departmentId) => {
  const department = departments.value.find((item) => Number(item.id) === Number(departmentId))
  if (!department) return false
  const profile = user.profile || {}
  if (department.level === 'division') return Number(profile.division) === Number(department.id)
  if (department.level === 'group') return Number(profile.group) === Number(department.id)
  if (department.level === 'team') {
    const teams = Array.isArray(profile.supervisor_teams) ? profile.supervisor_teams.map(Number) : []
    return Number(profile.team) === Number(department.id) || teams.includes(Number(department.id))
  }
  if (department.level === 'unit') {
    const units = Array.isArray(profile.leader_units) ? profile.leader_units.map(Number) : []
    return Number(profile.unit) === Number(department.id) || units.includes(Number(department.id))
  }
  return Number(profile.department) === Number(department.id)
}

const filteredUsers = computed(() => {
  if (!form.value.department_ids.length) return users.value
  return users.value.filter((user) => form.value.department_ids.some((departmentId) => userMatchesDepartment(user, departmentId)))
})

const filteredLines = computed(() => {
  if (!form.value.department_ids.length) return []
  const unitIds = new Set(collectDescendantUnitIds(form.value.department_ids.map(Number)))
  if (!unitIds.size) return []

  const lineIds = new Set(
    unitLineMappings.value
      .filter((mapping) => unitIds.has(Number(mapping.unit)))
      .map((mapping) => Number(mapping.line))
  )
  return lines.value.filter((line) => lineIds.has(Number(line.id)))
})

const loadMasterData = async () => {
  const [departmentsRes, linesRes, usersRes, unitLineMappingsRes] = await Promise.all([
    api.accounts.getDepartments({ ordering: 'display_id,name', page_size: 20000 }),
    api.lines.getLines({ is_active: true, line_type: 'PROD', page_size: 1000 }),
    api.accounts.getUsers({ is_active: true, page_size: 1000 }),
    api.accounts.getUnitLineMappings({ page_size: 20000 }),
  ])
  const departmentData = departmentsRes.data
  const unitLineMappingData = unitLineMappingsRes.data
  departments.value = Array.isArray(departmentData) ? departmentData : departmentData?.results || []
  lines.value = Array.isArray(linesRes.data?.results) ? linesRes.data.results : (Array.isArray(linesRes.data) ? linesRes.data : [])
  unitLineMappings.value = Array.isArray(unitLineMappingData) ? unitLineMappingData : unitLineMappingData?.results || []
  users.value = Array.isArray(usersRes.data?.results) ? usersRes.data.results : (Array.isArray(usersRes.data) ? usersRes.data : [])
}

const loadMeeting = async () => {
  if (!isEdit.value) return
  const res = await api.morningMeetings.get(props.id)
  const row = res.data
  if (row.status === 'COMPLETED') {
    window.alert('完了した朝礼は編集できません。詳細画面を表示します。')
    router.replace(`/production/morning-meetings/${row.id}/run`)
    return
  }
  form.value = {
    meeting_date: row.meeting_date || getBusinessISODate(),
    title: row.title || '',
    is_template: Boolean(row.is_template),
    department_ids: Array.isArray(row.target_departments) ? row.target_departments.map((item) => Number(item.id)) : [],
    line_ids: Array.isArray(row.target_lines) ? row.target_lines.map((item) => Number(item.id)) : [],
    facilitator: row.facilitator ? String(row.facilitator) : '',
    agenda: row.agenda || '',
    notices: row.notices || '',
    cautions: row.cautions || '',
    status: row.status === 'READY' ? 'READY' : 'DRAFT',
    participant_user_ids: Array.isArray(row.participants) ? row.participants.map((item) => Number(item.user)) : [],
    deleted_attachment_ids: [],
  }
  existingAttachments.value = Array.isArray(row.attachments) ? row.attachments : []
  sourceMeetingSummary.value = ''
}

const applyMeetingToForm = (row) => {
  form.value = {
    meeting_date: row.meeting_date || getBusinessISODate(),
    title: row.title || '',
    is_template: isTemplateMode.value,
    department_ids: Array.isArray(row.target_departments) ? row.target_departments.map((item) => Number(item.id)) : [],
    line_ids: Array.isArray(row.target_lines) ? row.target_lines.map((item) => Number(item.id)) : [],
    facilitator: row.facilitator ? String(row.facilitator) : String(authState.user?.id || ''),
    agenda: row.agenda || '',
    notices: row.notices || '',
    cautions: row.cautions || '',
    status: 'DRAFT',
    participant_user_ids: Array.isArray(row.participants) ? row.participants.map((item) => Number(item.user)) : [],
    deleted_attachment_ids: [],
  }
  existingAttachments.value = Array.isArray(row.attachments) ? row.attachments : []
  sourceMeetingSummary.value = `${row.meeting_date} ${row.title}`
}

const loadSourceMeeting = async () => {
  if (isEdit.value || !sourceMeetingId.value) return
  const res = await api.morningMeetings.get(sourceMeetingId.value)
  applyMeetingToForm(res.data)
}

const toggleSelection = (fieldName, value, checked) => {
  const id = Number(value)
  const next = new Set(form.value[fieldName])
  if (checked) next.add(id)
  else next.delete(id)
  form.value[fieldName] = [...next]
}

const toggleParticipant = (userId, checked) => {
  const id = Number(userId)
  const next = new Set(form.value.participant_user_ids)
  if (checked) next.add(id)
  else next.delete(id)
  form.value.participant_user_ids = [...next]
}

const toggleAllFiltered = (checked) => {
  const next = new Set(form.value.participant_user_ids)
  filteredUsers.value.forEach((user) => {
    if (checked) next.add(Number(user.id))
    else next.delete(Number(user.id))
  })
  form.value.participant_user_ids = [...next]
}

const applyDepartmentMembers = () => {
  form.value.participant_user_ids = [...new Set(filteredUsers.value.map((user) => Number(user.id)))]
}

const handleFileChange = (event) => {
  const files = Array.from(event.target.files || [])
  newAttachmentFiles.value = [...newAttachmentFiles.value, ...files]
  event.target.value = ''
}

const removeNewAttachment = (index) => {
  newAttachmentFiles.value.splice(index, 1)
}

const markAttachmentForDelete = (attachmentId) => {
  const next = new Set(form.value.deleted_attachment_ids)
  next.add(Number(attachmentId))
  form.value.deleted_attachment_ids = [...next]
}

const restoreAttachment = (attachmentId) => {
  form.value.deleted_attachment_ids = form.value.deleted_attachment_ids.filter((id) => Number(id) !== Number(attachmentId))
}

const openAttachmentPreview = (attachment) => {
  previewDialog.value = {
    visible: true,
    type: attachment.attachment_type || '',
    name: attachment.original_name || '添付資料',
    url: attachment.file_url || '',
  }
}

const closeAttachmentPreview = () => {
  previewDialog.value = {
    visible: false,
    type: '',
    name: '',
    url: '',
  }
}

const formatApiError = (payload) => {
  if (!payload) return '朝礼の保存に失敗しました。'
  if (typeof payload === 'string') return payload
  if (payload.detail) return payload.detail
  if (payload.attachments) {
    return Array.isArray(payload.attachments) ? payload.attachments.join(' ') : String(payload.attachments)
  }
  const messages = Object.entries(payload).flatMap(([key, value]) => {
    if (Array.isArray(value)) return [`${key}: ${value.join(' ')}`]
    if (value && typeof value === 'object') return [`${key}: ${JSON.stringify(value)}`]
    return [`${key}: ${String(value)}`]
  })
  return messages.join(' / ') || '朝礼の保存に失敗しました。'
}

watch(
  [() => form.value.department_ids.slice(), filteredLines],
  () => {
    const validLineIds = new Set(filteredLines.value.map((line) => Number(line.id)))
    form.value.line_ids = form.value.line_ids.filter((lineId) => validLineIds.has(Number(lineId)))
  },
  { immediate: true }
)

const buildPayload = () => {
  const formData = new FormData()
  if (form.value.meeting_date) {
    formData.append('meeting_date', form.value.meeting_date)
  }
  formData.append('title', form.value.title)
  formData.append('is_template', form.value.is_template ? 'true' : 'false')
  formData.append('department_ids', JSON.stringify(form.value.department_ids))
  formData.append('line_ids', JSON.stringify(form.value.line_ids))
  if (form.value.facilitator) {
    formData.append('facilitator', form.value.facilitator)
  }
  formData.append('agenda', form.value.agenda)
  formData.append('notices', form.value.notices)
  formData.append('cautions', form.value.cautions)
  formData.append('status', form.value.status)
  formData.append('participant_user_ids', JSON.stringify(form.value.participant_user_ids))
  formData.append('deleted_attachment_ids', JSON.stringify(form.value.deleted_attachment_ids))
  newAttachmentFiles.value.forEach((file) => {
    formData.append('new_attachments', file)
  })
  return formData
}

const save = async () => {
  if (!form.value.title.trim()) {
    errorMessage.value = 'タイトルを入力してください。'
    return
  }
  if (!form.value.is_template && !form.value.meeting_date) {
    errorMessage.value = '通常朝礼では朝礼日を入力してください。'
    return
  }
  saving.value = true
  errorMessage.value = ''
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await api.morningMeetings.update(props.id, payload)
    } else {
      await api.morningMeetings.create(payload)
    }
    router.push('/production/morning-meetings')
  } catch (error) {
    console.error('朝礼の保存に失敗しました:', error)
    errorMessage.value = formatApiError(error.response?.data)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await loadMasterData()
    if (isEdit.value) {
      await loadMeeting()
    } else {
      form.value.is_template = isTemplateMode.value
      await loadSourceMeeting()
    }
  } catch (error) {
    console.error('初期データの取得に失敗しました:', error)
    errorMessage.value = '初期データの取得に失敗しました。'
  }
})
</script>

<style scoped>
.form-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
}

.source-banner {
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid #c7d2fe;
  background: #eef2ff;
  border-radius: 10px;
  color: #312e81;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field.wide {
  grid-column: 1 / -1;
}

.form-field input,
.form-field select,
.form-field textarea {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
}

.selection-field {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
}

.selection-header,
.section-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.selection-meta,
.section-meta,
.participants-summary {
  color: #475569;
}

.selection-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selection-chip,
.attachment-type {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0f172a;
  padding: 4px 10px;
  font-size: 12px;
}

.selection-list,
.attachment-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
}

.selection-list.disabled {
  opacity: 0.7;
}

.selection-item,
.attachment-item {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
}

.selection-empty,
.empty-participants {
  color: #64748b;
}

.template-toggle {
  gap: 4px;
}

.checkbox-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.attachments-card,
.participants-card {
  margin-top: 16px;
  border-top: 1px solid #e2e8f0;
  padding-top: 16px;
}

.attachment-block {
  margin-top: 12px;
}

.attachment-subtitle {
  margin-bottom: 6px;
  font-weight: 600;
}

.attachment-item.removed {
  background: #f8fafc;
  color: #64748b;
}

.participants-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.participants-header h2,
.section-header h2 {
  margin: 0;
  font-size: 16px;
}

.participants-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.participants-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
  max-height: 320px;
  overflow: auto;
  padding-right: 4px;
}

.participant-item {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
}

.btn-text {
  border: none;
  background: transparent;
  color: #2563eb;
  cursor: pointer;
}

.attachment-name {
  padding: 0;
  text-align: left;
  flex: 1;
}

.danger-text {
  color: #dc2626;
}

.error-box {
  margin-top: 12px;
  color: #b91c1c;
}

.form-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.52);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 1000;
}

.preview-dialog {
  width: min(1000px, 100%);
  max-height: 90vh;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #cbd5e1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-bottom: 1px solid #e2e8f0;
}

.preview-body {
  padding: 12px;
  min-height: 320px;
}

.preview-body iframe {
  width: 100%;
  height: 70vh;
  border: none;
}

.image-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  background: #0f172a;
}

.image-preview img {
  max-width: 100%;
  max-height: 72vh;
  object-fit: contain;
}

.preview-note {
  display: grid;
  gap: 8px;
  align-content: center;
  justify-items: start;
}

@media (max-width: 900px) {
  .form-grid,
  .selection-list,
  .attachment-list,
  .participants-list {
    grid-template-columns: 1fr;
  }

  .selection-header,
  .section-header,
  .participants-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
