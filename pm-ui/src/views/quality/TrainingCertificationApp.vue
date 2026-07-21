<template>
  <div class="training-page">
    <h2 class="page-title">
      教育・テスト・認定
      <DataSourceDialog title="教育・テスト・認定" :sources="dsSources" :note="dsNote" />
    </h2>

    <div class="control-card">
      <div class="field">
        <label>受講者</label>
        <select v-model="form.traineeUser">
          <option value="">受講者を選択</option>
          <option v-for="user in userOptions" :key="user.id" :value="String(user.id)">
            {{ user.label }}
          </option>
        </select>
      </div>
      <div class="field">
        <label>試験官</label>
        <select v-model="form.supervisorUser">
          <option value="">試験官を選択</option>
          <option v-for="user in userOptions" :key="`sup-${user.id}`" :value="String(user.id)">
            {{ user.label }}
          </option>
        </select>
      </div>
      <div class="field">
        <label>実施日時</label>
        <input v-model="form.performedAt" type="datetime-local" />
      </div>
      <div class="field">
        <label>実施場所</label>
        <input v-model="form.location" type="text" placeholder="会議室 / 現場 など" />
      </div>
      <label class="check-field">
        <input v-model="form.formalExam" type="checkbox" />
        <span>推進判定対象として記録</span>
      </label>
    </div>

    <div v-if="message.text" class="message" :class="message.type">{{ message.text }}</div>
    <div v-if="loading" class="info-box">読み込み中...</div>
    <div v-else-if="loadError" class="message error">{{ loadError }}</div>

    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'books' }" @click="activeTab = 'books'">教材・試験</button>
      <button class="tab-btn" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">受験履歴</button>
      <button class="tab-btn" :class="{ active: activeTab === 'progress' }" @click="activeTab = 'progress'">個人進捗</button>
    </div>

    <section v-if="activeTab === 'books'" class="tab-panel">
      <div class="book-grid">
        <article v-for="book in books" :key="book.id" class="book-card">
          <div class="book-head">
            <div>
              <div class="book-title">{{ book.title }}</div>
              <div class="book-meta">
                <span>{{ book.question_count }}問</span>
                <span v-if="passedBookMap[book.id]" class="good">合格済み</span>
                <span v-else>未合格</span>
              </div>
            </div>
          </div>
          <div class="book-submeta">
            <span v-if="book.source_file">元: {{ book.source_file }}</span>
            <span v-if="book.material_url">
              <a :href="book.material_url" target="_blank" rel="noopener noreferrer">教材を開く</a>
            </span>
          </div>
          <div class="exam-list">
            <button
              v-for="exam in book.exams"
              :key="exam.id"
              class="exam-btn"
              :disabled="startingSession || submittingAttempt"
              @click="startExam(book, exam)"
            >
              {{ exam.name }}
            </button>
          </div>
        </article>
      </div>

      <div v-if="activeSession" class="exam-card">
        <div class="exam-header">
          <div>
            <h3>{{ activeSession.book.title }} / {{ activeSession.exam.name }}</h3>
            <p>
              受講者: {{ activeSession.trainee.name }} |
              試験官: {{ activeSession.supervisor?.name || '未設定' }} |
              合格基準: 100%
            </p>
          </div>
          <button class="btn-secondary" @click="closeSession" :disabled="submittingAttempt">閉じる</button>
        </div>

        <div class="question-progress">
          回答 {{ answeredCount }} / {{ activeSession.questions.length }}
        </div>

        <div class="question-list">
          <article v-for="(question, index) in activeSession.questions" :key="question.id" class="question-card">
            <div class="question-no">Q{{ index + 1 }} {{ question.question_code }}</div>
            <div class="question-text">{{ question.question }}</div>
            <div class="choice-list">
              <label v-for="choice in question.choices" :key="`${question.id}-${choice.value}`" class="choice-item">
                <input v-model="answers[question.id]" type="radio" :name="`q-${question.id}`" :value="choice.value" />
                <span>{{ choice.value }}. {{ choice.text }}</span>
              </label>
            </div>
          </article>
        </div>

        <div class="submit-row">
          <button class="btn-primary" :disabled="submittingAttempt || !canSubmitAttempt" @click="submitAttempt">
            {{ submittingAttempt ? '採点中...' : '採点して保存' }}
          </button>
        </div>

        <div v-if="lastAttempt" class="result-box" :class="{ good: lastAttempt.result === 'PASS', bad: lastAttempt.result !== 'PASS' }">
          <div class="result-title">{{ lastAttempt.result_label }}</div>
          <div>{{ lastAttempt.score }} / {{ lastAttempt.total }}（{{ lastAttempt.rate }}%）</div>
        </div>
      </div>
    </section>

    <section v-if="activeTab === 'history'" class="tab-panel">
      <div class="section-head">
        <h3>受験履歴</h3>
        <button class="btn-secondary" @click="loadAttempts" :disabled="historyLoading">再読込</button>
      </div>
      <div v-if="historyLoading" class="info-box">受験履歴を読み込み中...</div>
      <div v-else-if="!attempts.length" class="info-box">受験履歴はありません。</div>
      <div v-else class="history-list">
        <article v-for="attempt in attempts" :key="attempt.id" class="history-card">
          <div class="history-title">{{ attempt.book_title }} / {{ attempt.exam_name }}</div>
          <div class="history-meta">
            {{ attempt.trainee_name }} / {{ formatDateTime(attempt.performed_at) }} / {{ attempt.location || '場所未設定' }}
          </div>
          <div class="history-meta">
            試験官: {{ attempt.supervisor_name || '未設定' }} / 組織:
            {{ formatOrg(attempt.trainee_division, attempt.trainee_team, attempt.trainee_unit) }}
          </div>
          <div class="badge-row">
            <span class="badge" :class="attempt.result === 'PASS' ? 'good' : 'bad'">{{ attempt.result_label }}</span>
            <span class="badge">{{ attempt.score }}/{{ attempt.total }}</span>
            <span class="badge">{{ attempt.rate }}%</span>
            <span class="badge">{{ attempt.formal_exam ? '推進判定対象' : '練習' }}</span>
          </div>
        </article>
      </div>
    </section>

    <section v-if="activeTab === 'progress'" class="tab-panel">
      <div class="section-head">
        <h3>個人進捗</h3>
        <button class="btn-secondary" @click="loadProgress" :disabled="progressLoading || !form.traineeUser">再読込</button>
      </div>
      <div v-if="progressLoading" class="info-box">個人進捗を読み込み中...</div>
      <div v-else-if="!progressSummary" class="info-box">受講者を選択してください。</div>
      <template v-else>
        <div class="summary-banner">
          <span>受講者: {{ progressSummary.trainee.name }}</span>
          <span>組織: {{ formatOrgName(progressSummary.trainee) }}</span>
        </div>
        <div class="table-wrap">
          <table class="progress-table">
            <thead>
              <tr>
                <th>No.</th>
                <th>教育項目</th>
                <th>教育</th>
                <th>テスト</th>
                <th>認定</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in progressSummary.rows" :key="row.track_id">
                <td>{{ row.no }}</td>
                <td>{{ row.title }}</td>
                <td>
                  <div v-if="row.education">
                    <div>〇 {{ formatDateTime(row.education.performed_at) }}</div>
                    <div class="cell-sub">{{ row.education.supervisor_name || '試験官未設定' }}</div>
                  </div>
                  <button v-else class="mini-btn" :disabled="stepSaving" @click="recordStep(row, 'EDUCATION')">教育完了</button>
                </td>
                <td>
                  <div v-if="row.has_test && row.test">
                    <div>〇 {{ row.test.exam_name }}</div>
                    <div class="cell-sub">{{ row.test.score }}/{{ row.test.total }} | {{ formatDateTime(row.test.performed_at) }}</div>
                  </div>
                  <button v-else-if="row.has_test" class="mini-btn" :disabled="!row.book_id" @click="openTrackBook(row)">テストへ</button>
                  <div v-else class="cell-sub">対象外</div>
                </td>
                <td>
                  <div v-if="row.certification">
                    <div>〇 {{ formatDateTime(row.certification.performed_at) }}</div>
                    <div class="cell-sub">{{ row.certification.supervisor_name || '試験官未設定' }}</div>
                  </div>
                  <button v-else class="mini-btn" :disabled="stepSaving || !row.can_certify" @click="recordStep(row, 'CERTIFICATION')">認定完了</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { section: '教育・試験マスタ' },
  { op: '読み取り', table: 'quality_training_book', desc: '教材一覧、教材コード、教材URL、取込元ファイルの表示' },
  { op: '読み取り', table: 'quality_training_question', desc: '問題文、選択肢、正答、解説、根拠情報の取得' },
  { op: '読み取り', table: 'quality_training_exam_definition', desc: '試験名、ランダム出題設定、問題数の取得' },
  { op: '読み取り', table: 'quality_training_exam_question', desc: '固定試験の出題問題定義の取得' },
  { op: '読み取り', table: 'quality_training_track', desc: '個人進捗に表示する教育項目の取得' },
  { section: '実施・進捗実績' },
  { op: '書き込み', table: 'quality_training_exam_session', desc: '試験開始時の受講者、試験官、実施情報、出題問題を保存' },
  { op: '読み書き', table: 'quality_training_exam_attempt', desc: '採点結果、回答内容、合否、履歴表示、個人進捗判定に使用' },
  { op: '読み書き', table: 'quality_training_step_record', desc: '教育完了・認定完了の手動実績保存と個人進捗表示に使用' },
  { section: 'ユーザー・組織マスタ' },
  { op: '読み取り', table: 'auth_user', desc: '受講者・試験官ユーザーの基本情報取得' },
  { op: '読み取り', table: 'accounts_userprofile', desc: '社員コード、所属部署、事業部、係、班、グループの取得' },
  { op: '読み取り', table: 'accounts_department', desc: '組織名の表示と、受講時点組織スナップショットの名称解決に使用' },
]

const dsNote = '初期の教材・問題・試験定義は、試作HTMLのデータを移行用マイグレーションで quality_training_* テーブルへ投入しています。'

const loading = ref(false)
const loadError = ref('')
const historyLoading = ref(false)
const progressLoading = ref(false)
const startingSession = ref(false)
const submittingAttempt = ref(false)
const stepSaving = ref(false)
const books = ref([])
const tracks = ref([])
const users = ref([])
const attempts = ref([])
const progressSummary = ref(null)
const activeSession = ref(null)
const lastAttempt = ref(null)
const activeTab = ref('books')
const message = reactive({ text: '', type: 'info' })
const answers = reactive({})

function pad2(value) {
  return String(value).padStart(2, '0')
}

function nowLocalValue() {
  const now = new Date()
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}T${pad2(now.getHours())}:${pad2(now.getMinutes())}`
}

const form = reactive({
  traineeUser: '',
  supervisorUser: '',
  performedAt: nowLocalValue(),
  location: '',
  formalExam: true,
})

const normalizeList = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

function setMessage(text, type = 'info') {
  message.text = text
  message.type = type
}

function clearMessage() {
  message.text = ''
  message.type = 'info'
}

const userOptions = computed(() =>
  [...users.value].sort((a, b) => a.label.localeCompare(b.label, 'ja'))
)

const answeredCount = computed(() => {
  if (!activeSession.value) return 0
  return activeSession.value.questions.filter((question) => answers[question.id]).length
})

const canSubmitAttempt = computed(() => {
  if (!activeSession.value) return false
  return answeredCount.value === activeSession.value.questions.length
})

const passedBookMap = computed(() => {
  const map = {}
  for (const attempt of attempts.value) {
    if (attempt.formal_exam && attempt.result === 'PASS' && !map[attempt.book]) {
      map[attempt.book] = attempt
    }
  }
  return map
})

async function loadUsers() {
  const response = await api.accounts.getUsers({ page_size: 1000, is_active: true })
  users.value = normalizeList(response.data).map((user) => ({
    id: user.id,
    label: buildUserLabel(user),
    first_name: user.first_name,
    last_name: user.last_name,
    username: user.username,
    profile: user.profile || {},
  }))
}

function buildUserLabel(user) {
  const fullName = `${user.last_name || ''} ${user.first_name || ''}`.trim() || user.username
  const code = user.profile?.employee_code ? ` [${user.profile.employee_code}]` : ''
  const org = [user.profile?.division_name, user.profile?.team_name, user.profile?.unit_name].filter(Boolean).join(' / ')
  return org ? `${fullName}${code} - ${org}` : `${fullName}${code}`
}

async function loadMasterData() {
  const [booksResponse, tracksResponse] = await Promise.all([
    api.trainingCertification.listBooks(),
    api.trainingCertification.listTracks(),
  ])
  books.value = normalizeList(booksResponse.data)
  tracks.value = normalizeList(tracksResponse.data)
}

async function loadAttempts() {
  if (!form.traineeUser) {
    attempts.value = []
    return
  }
  historyLoading.value = true
  try {
    const response = await api.trainingCertification.listAttempts({ trainee: form.traineeUser })
    attempts.value = normalizeList(response.data)
  } finally {
    historyLoading.value = false
  }
}

async function loadProgress() {
  if (!form.traineeUser) {
    progressSummary.value = null
    return
  }
  progressLoading.value = true
  try {
    const response = await api.trainingCertification.getProgressSummary({ trainee: form.traineeUser })
    progressSummary.value = response.data
  } finally {
    progressLoading.value = false
  }
}

async function refreshTraineeData() {
  await Promise.all([loadAttempts(), loadProgress()])
}

function validateExecutionForm() {
  if (!form.traineeUser || !form.supervisorUser || !form.performedAt || !form.location) {
    setMessage('受講者・試験官・実施日時・実施場所を入力してください。', 'error')
    return false
  }
  return true
}

async function startExam(book, exam) {
  clearMessage()
  if (!validateExecutionForm()) return
  startingSession.value = true
  try {
    const response = await api.trainingCertification.startSession({
      exam_id: exam.id,
      trainee_user: Number(form.traineeUser),
      supervisor_user: Number(form.supervisorUser),
      performed_at: form.performedAt,
      location: form.location,
      formal_exam: form.formalExam,
    })
    activeSession.value = response.data
    lastAttempt.value = null
    Object.keys(answers).forEach((key) => delete answers[key])
    activeTab.value = 'books'
  } catch (error) {
    setMessage(error.response?.data?.detail || '試験開始に失敗しました。', 'error')
  } finally {
    startingSession.value = false
  }
}

async function submitAttempt() {
  if (!activeSession.value) return
  clearMessage()
  submittingAttempt.value = true
  try {
    const response = await api.trainingCertification.submitAttempt({
      session_id: activeSession.value.session_id,
      answers,
    })
    lastAttempt.value = response.data
    setMessage(`採点結果を保存しました: ${response.data.result_label}`, response.data.result === 'PASS' ? 'success' : 'warn')
    await refreshTraineeData()
  } catch (error) {
    setMessage(error.response?.data?.detail || '採点保存に失敗しました。', 'error')
  } finally {
    submittingAttempt.value = false
  }
}

function closeSession() {
  activeSession.value = null
  lastAttempt.value = null
  Object.keys(answers).forEach((key) => delete answers[key])
}

async function recordStep(row, stepType) {
  clearMessage()
  if (!validateExecutionForm()) return
  stepSaving.value = true
  try {
    await api.trainingCertification.createStepRecord({
      trainee: Number(form.traineeUser),
      supervisor: Number(form.supervisorUser),
      track: row.track_id,
      step_type: stepType,
      performed_at: form.performedAt,
      location: form.location,
    })
    setMessage(`${stepType === 'EDUCATION' ? '教育' : '認定'}実績を保存しました。`, 'success')
    await loadProgress()
  } catch (error) {
    setMessage(error.response?.data?.detail || '進捗保存に失敗しました。', 'error')
  } finally {
    stepSaving.value = false
  }
}

function openTrackBook(row) {
  const book = books.value.find((item) => item.id === row.book_id)
  if (!book) {
    setMessage('紐付く教材が見つかりません。', 'error')
    return
  }
  const exam = book.exams?.find((item) => !item.bank_all) || book.exams?.[0]
  if (!exam) {
    setMessage('開始できる試験がありません。', 'error')
    return
  }
  startExam(book, exam)
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}/${pad2(date.getMonth() + 1)}/${pad2(date.getDate())} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`
}

function formatOrg(divisionId, teamId, unitId) {
  const parts = [lookupDepartmentName(divisionId), lookupDepartmentName(teamId), lookupDepartmentName(unitId)].filter(Boolean)
  return parts.join(' / ') || '未設定'
}

function lookupDepartmentName(departmentId) {
  if (!departmentId) return ''
  const user = users.value.find((item) => Number(item.profile?.division) === Number(departmentId))
  if (user?.profile?.division_name) return user.profile.division_name
  const teamUser = users.value.find((item) => Number(item.profile?.team) === Number(departmentId))
  if (teamUser?.profile?.team_name) return teamUser.profile.team_name
  const unitUser = users.value.find((item) => Number(item.profile?.unit) === Number(departmentId))
  if (unitUser?.profile?.unit_name) return unitUser.profile.unit_name
  return ''
}

function formatOrgName(trainee) {
  return [trainee.division_name, trainee.team_name, trainee.unit_name].filter(Boolean).join(' / ') || '未設定'
}

watch(
  () => form.traineeUser,
  async (value) => {
    closeSession()
    if (!value) {
      attempts.value = []
      progressSummary.value = null
      return
    }
    await refreshTraineeData()
  }
)

onMounted(async () => {
  loading.value = true
  loadError.value = ''
  try {
    await Promise.all([loadUsers(), loadMasterData()])
    if (authState.user?.id) {
      form.traineeUser = String(authState.user.id)
      form.supervisorUser = String(authState.user.id)
    }
    await refreshTraineeData()
  } catch (error) {
    loadError.value = error.response?.data?.detail || error.message || '初期化に失敗しました。'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.training-page {
  padding: 16px;
  display: grid;
  gap: 14px;
}

.control-card {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  padding: 12px;
  background: #fff;
  border: 1px solid #d8e0e8;
  border-radius: 14px;
}

.field {
  display: grid;
  gap: 4px;
}

.field label,
.check-field {
  font-size: 13px;
  color: #415164;
}

.field input,
.field select {
  min-height: 38px;
  padding: 6px 10px;
  border: 1px solid #c8d2dc;
  border-radius: 8px;
}

.check-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message,
.info-box,
.summary-banner {
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13px;
}

.message.info,
.info-box {
  background: #eef5fb;
  color: #32506c;
}

.message.success {
  background: #e8f7ee;
  color: #1d6a3d;
}

.message.warn {
  background: #fff4d8;
  color: #7a5912;
}

.message.error {
  background: #fdecec;
  color: #a22a2a;
}

.tab-bar {
  display: flex;
  gap: 8px;
}

.tab-btn {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid #c8d2dc;
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
}

.tab-btn.active {
  background: #1f7a66;
  color: #fff;
  border-color: #1f7a66;
}

.tab-panel {
  display: grid;
  gap: 12px;
}

.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.book-card,
.exam-card,
.history-card {
  background: #fff;
  border: 1px solid #d8e0e8;
  border-radius: 14px;
  padding: 12px;
}

.book-title,
.history-title {
  font-weight: 700;
  color: #1f3045;
}

.book-meta,
.book-submeta,
.history-meta,
.cell-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #5e7084;
}

.exam-list,
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.exam-btn,
.btn-primary,
.btn-secondary,
.mini-btn {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid #c8d2dc;
  cursor: pointer;
  background: #fff;
}

.btn-primary {
  background: #1f7a66;
  color: #fff;
  border-color: #1f7a66;
}

.mini-btn {
  min-height: 30px;
  font-size: 12px;
}

.exam-header,
.section-head,
.submit-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.question-progress {
  font-size: 13px;
  color: #415164;
}

.question-list {
  display: grid;
  gap: 10px;
}

.question-card {
  border: 1px solid #e1e8ef;
  border-radius: 12px;
  padding: 12px;
}

.question-no {
  font-size: 12px;
  color: #1f7a66;
  font-weight: 700;
}

.question-text {
  margin-top: 6px;
  color: #1f3045;
  font-weight: 600;
}

.choice-list {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.choice-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 13px;
}

.result-box {
  padding: 12px;
  border-radius: 12px;
  font-weight: 700;
}

.result-box.good {
  background: #e8f7ee;
  color: #1d6a3d;
}

.result-box.bad {
  background: #fff4d8;
  color: #7a5912;
}

.history-list {
  display: grid;
  gap: 10px;
}

.badge {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: #edf2f7;
  font-size: 12px;
}

.badge.good,
.good {
  color: #1d6a3d;
}

.badge.bad {
  color: #a22a2a;
}

.table-wrap {
  overflow-x: auto;
}

.progress-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
  background: #fff;
}

.progress-table th,
.progress-table td {
  border: 1px solid #d8e0e8;
  padding: 8px 10px;
  vertical-align: top;
  font-size: 13px;
}

.progress-table th {
  background: #f3f7fa;
}

@media (max-width: 980px) {
  .control-card {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .training-page {
    padding: 12px;
  }

  .control-card {
    grid-template-columns: 1fr;
  }

  .exam-header,
  .section-head,
  .submit-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
