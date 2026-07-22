<template>
  <div class="training-page">
    <h2 class="page-title">
      教育・テスト・認定
      <DataSourceDialog title="教育・テスト・認定" :sources="dsSources" :note="dsNote" />
    </h2>

    <div v-if="message.text" class="message" :class="message.type">{{ message.text }}</div>
    <div v-if="loading" class="info-box">読み込み中...</div>
    <div v-else-if="loadError" class="message error">{{ loadError }}</div>
    <template v-else>
      <div class="mode-grid">
        <button
          class="mode-tile"
          :class="{ active: activeMode === 'edit', disabled: !canViewBookEditor }"
          :disabled="!canViewBookEditor"
          @click="selectMode('edit')"
        >
          <div class="mode-head"><span class="mode-icon">編</span><span class="mode-title">問題集編集</span></div>
          <div class="mode-desc">教材・問題数・試験定義・進捗項目を管理者向けに確認します。</div>
          <div class="mode-foot">{{ canViewBookEditor ? '権限あり' : '権限が必要です' }}</div>
        </button>
        <button
          class="mode-tile"
          :class="{ active: activeMode === 'practice' }"
          @click="selectMode('practice')"
        >
          <div class="mode-head"><span class="mode-icon">練</span><span class="mode-title">練習</span></div>
          <div class="mode-desc">誰でも受講できる練習モードです。推進判定には使いません。</div>
          <div class="mode-foot">全ユーザー利用可</div>
        </button>
        <button
          class="mode-tile"
          :class="{ active: activeMode === 'test', disabled: !canViewTest }"
          :disabled="!canViewTest"
          @click="selectMode('test')"
        >
          <div class="mode-head"><span class="mode-icon">試</span><span class="mode-title">テスト</span></div>
          <div class="mode-desc">正式テスト、受験履歴、個人進捗を権限者向けに扱います。結果は推進判定対象として記録し、進捗へ反映します。</div>
          <div class="mode-foot">{{ canViewTest ? '権限あり' : '権限が必要です' }}</div>
        </button>
      </div>


      <section v-if="activeMode === 'edit'" class="tab-panel">
        <div class="summary-grid">
          <article class="summary-card">
            <div class="summary-label">教材数</div>
            <div class="summary-value">{{ trainingSummary.books }}</div>
          </article>
          <article class="summary-card">
            <div class="summary-label">問題数</div>
            <div class="summary-value">{{ trainingSummary.questions }}</div>
          </article>
          <article class="summary-card">
            <div class="summary-label">試験定義</div>
            <div class="summary-value">{{ trainingSummary.exams }}</div>
          </article>
          <article class="summary-card">
            <div class="summary-label">進捗項目</div>
            <div class="summary-value">{{ trainingSummary.tracks }}</div>
          </article>
        </div>

        <div class="info-box">
          現時点の画面は問題集マスタの確認用です。問題文・選択肢・試験定義の更新は Django 管理画面または別途更新手順で運用します。
        </div>

        <div class="book-grid">
          <article v-for="book in books" :key="book.id" class="book-card">
            <div class="book-head">
              <div>
                <div class="book-title">{{ book.title }}</div>
                <div class="book-meta">
                  <span>教材コード: {{ book.book_code }}</span>
                  <span>{{ book.question_count }}問</span>
                </div>
              </div>
            </div>
            <div class="book-submeta">
              <span v-if="book.source_file">元ファイル: {{ book.source_file }}</span>
              <span v-if="book.source_sheet">元シート: {{ book.source_sheet }}</span>
            </div>
            <div class="badge-row">
              <span v-for="exam in book.exams || []" :key="exam.id" class="badge">
                {{ exam.name }}
              </span>
            </div>
          </article>
        </div>

        <div class="table-wrap">
          <table class="progress-table">
            <thead>
              <tr>
                <th>No.</th>
                <th>進捗項目</th>
                <th>教材</th>
                <th>テスト有無</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="track in tracks" :key="track.id">
                <td>{{ track.track_no }}</td>
                <td>{{ track.title }}</td>
                <td>{{ track.book_title || '-' }}</td>
                <td>{{ track.has_test ? 'あり' : 'なし' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <template v-else-if="activeMode === 'practice'">
        <div class="info-box">
          練習モードでは受講者・試験官・実施日時・実施場所の入力は不要です。採点結果は画面上だけで確認し、DBには保存しません。
        </div>

        <section class="tab-panel">
          <div class="section-head">
            <h3>練習問題</h3>
          </div>
          <div class="book-grid">
            <article v-for="book in practiceBooks" :key="book.id" class="book-card">
              <div class="book-head">
                <div>
                  <div class="book-title">{{ book.title }}</div>
                  <div class="book-meta">
                    <span>{{ book.question_count }}問</span>
                    <span>練習用</span>
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
                  v-for="exam in getPracticeExams(book)"
                  :key="exam.id"
                  class="exam-btn"
                  :disabled="startingSession || submittingAttempt"
                  @click="startExam(book, exam, 'practice')"
                >
                  {{ exam.name }}
                </button>
              </div>
            </article>
          </div>

          <div v-if="!practiceBooks.length" class="info-box">練習用の試験が登録されていません。</div>
          <div v-if="activeSession && activeSessionMode === 'practice'" class="exam-card">
            <div class="exam-header">
              <div>
                <h3>{{ activeSession.book.title }} / {{ activeSession.exam.name }}</h3>
                <p>練習モード | 採点結果は保存しません</p>
              </div>
              <button class="btn-secondary" @click="closeSession" :disabled="submittingAttempt">閉じる</button>
            </div>

            <div class="question-progress">回答 {{ answeredCount }} / {{ activeSession.questions.length }}</div>

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
                {{ submittingAttempt ? '採点中...' : '採点する' }}
              </button>
            </div>

            <div v-if="lastAttempt" class="result-box" :class="{ good: lastAttempt.result === 'PASS', bad: lastAttempt.result !== 'PASS' }">
              <div class="result-title">{{ lastAttempt.result_label }}</div>
              <div>{{ lastAttempt.score }} / {{ lastAttempt.total }}（{{ lastAttempt.rate }}%）</div>
            </div>
          </div>
        </section>
      </template>

      <template v-else>
        <div class="control-card">
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
            <label>受講者</label>
            <select v-if="orgFilterOptions.length > 1" v-model="orgFilter" class="org-filter-select">
              <option value="">全組織</option>
              <option v-for="org in orgFilterOptions" :key="org.value" :value="org.value">{{ org.label }}</option>
            </select>
            <select v-model="form.traineeUser">
              <option value="">受講者を選択</option>
              <option v-for="user in filteredTraineeOptions" :key="user.id" :value="String(user.id)">
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
        </div>

        <section v-if="activeMode === 'test'" class="tab-panel">
          <div class="tab-bar">
            <button class="tab-btn" :class="{ active: testTab === 'exam' }" @click="testTab = 'exam'">テスト</button>
            <button class="tab-btn" :class="{ active: testTab === 'history' }" @click="testTab = 'history'">受験履歴</button>
            <button class="tab-btn" :class="{ active: testTab === 'progress' }" @click="testTab = 'progress'">個人進捗</button>
          </div>

          <section v-if="testTab === 'exam'" class="tab-panel">
            <div class="book-grid">
              <article v-for="book in testBooks" :key="book.id" class="book-card">
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
                    v-for="exam in getTestExams(book)"
                    :key="exam.id"
                    class="exam-btn"
                    :disabled="startingSession || submittingAttempt"
                    @click="startExam(book, exam, 'test')"
                  >
                    {{ exam.name }}
                  </button>
                </div>
              </article>
            </div>

            <div v-if="!testBooks.length" class="info-box">テスト用の試験が登録されていません。</div>
            <div v-if="activeSession && activeSessionMode === 'test'" class="exam-card">
              <div class="exam-header">
                <div>
                  <h3>{{ activeSession.book.title }} / {{ activeSession.exam.name }}</h3>
                  <p>
                    テスト |
                    受講者: {{ activeSession.trainee.name }} |
                    試験官: {{ activeSession.supervisor?.name || '未設定' }} |
                    合格基準: 100%
                  </p>
                </div>
                <button class="btn-secondary" @click="closeSession" :disabled="submittingAttempt">閉じる</button>
              </div>

              <div class="question-progress">回答 {{ answeredCount }} / {{ activeSession.questions.length }}</div>

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

          <section v-if="testTab === 'history'" class="tab-panel">
            <div class="section-head">
              <h3>受験履歴</h3>
              <button class="btn-secondary" @click="loadAttempts" :disabled="historyLoading">再読込</button>
            </div>
            <div v-if="historyLoading" class="info-box">受験履歴を読み込み中...</div>
            <div v-else-if="!formalAttempts.length" class="info-box">正式テストの受験履歴はありません。</div>
            <div v-else class="history-list">
              <article v-for="attempt in formalAttempts" :key="attempt.id" class="history-card">
                <div class="history-title">{{ attempt.book_title }} / {{ attempt.exam_name }}</div>
                <div class="history-meta">
                  {{ attempt.trainee_name }} / {{ formatDateTime(attempt.performed_at) }} / {{ attempt.location || '場所未設定' }}
                </div>
                <div class="history-meta">
                  試験官: {{ attempt.supervisor_name || '未設定' }} / 組織:
                  {{ formatOrg(attempt.trainee_division, attempt.trainee_group, attempt.trainee_team, attempt.trainee_unit) }}
                </div>
                <div class="badge-row">
                  <span class="badge" :class="attempt.result === 'PASS' ? 'good' : 'bad'">{{ attempt.result_label }}</span>
                  <span class="badge">{{ attempt.score }}/{{ attempt.total }}</span>
                  <span class="badge">{{ attempt.rate }}%</span>
                  <span class="badge">推進判定対象</span>
                </div>
              </article>
            </div>
          </section>

          <section v-if="testTab === 'progress'" class="tab-panel">
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
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import { hasPermission } from '@/router'

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
const activeSessionMode = ref('')
const lastAttempt = ref(null)
const activeMode = ref('practice')
const testTab = ref('exam')
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
})
const orgFilter = ref('')

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

const canAccessTraining = (resource, level = 'view', aliases = [], fallbackToQuality = true) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const candidates = [resource, ...aliases]
  const hasSpecific = permissions.some((item) => candidates.includes(item.resource))
  if (hasSpecific) {
    return candidates.some((candidate) => hasPermission(user, candidate, level))
  }
  return fallbackToQuality ? hasPermission(user, 'quality', level) : false
}

const canViewBookEditor = computed(() => canAccessTraining('quality.training_certification_editor', 'view'))
const canViewTest = computed(() => canAccessTraining('quality.training_certification_test', 'view'))

const ROLE_RANK = { staff: 0, office_staff: 0, leader: 1, supervisor: 2, chief: 3, manager: 4 }

const userOptions = computed(() =>
  [...users.value].sort((a, b) => a.label.localeCompare(b.label, 'ja'))
)

const traineeOptions = computed(() => {
  if (!form.supervisorUser) return []
  const sup = users.value.find((u) => String(u.id) === form.supervisorUser)
  if (!sup) return []
  if (sup.is_superuser) return userOptions.value.filter((u) => String(u.id) !== form.supervisorUser)

  const sp = sup.profile || {}
  const supRole = sp.role || 'staff'
  const supRank = ROLE_RANK[supRole] ?? 0

  return users.value
    .filter((u) => {
      if (String(u.id) === form.supervisorUser) return false
      const p = u.profile || {}
      const rank = ROLE_RANK[p.role] ?? 0
      if (rank >= supRank) return false

      if (supRole === 'manager') {
        return sp.division && p.division === sp.division
      } else if (supRole === 'chief') {
        return sp.group && p.group === sp.group
      } else if (supRole === 'supervisor') {
        const teamIds = new Set()
        if (sp.team) teamIds.add(sp.team)
        for (const t of sp.supervisor_teams || []) teamIds.add(t)
        return teamIds.size > 0 && teamIds.has(p.team)
      } else if (supRole === 'leader') {
        const unitIds = new Set()
        if (sp.unit) unitIds.add(sp.unit)
        for (const uid of sp.leader_units || []) unitIds.add(uid)
        return unitIds.size > 0 && unitIds.has(p.unit)
      }
      return false
    })
    .sort((a, b) => a.label.localeCompare(b.label, 'ja'))
})

const orgFilterLevel = computed(() => {
  const sup = users.value.find((u) => String(u.id) === form.supervisorUser)
  const role = sup?.profile?.role || 'staff'
  if (role === 'manager') return 'team'
  if (role === 'chief') return 'team'
  if (role === 'supervisor') return 'unit'
  if (sup?.is_superuser) return 'team'
  return ''
})

const orgFilterOptions = computed(() => {
  const level = orgFilterLevel.value
  if (!level) return []
  const map = new Map()
  for (const u of traineeOptions.value) {
    const p = u.profile || {}
    const key = p[level] || 0
    const label = p[`${level}_name`] || '未設定'
    if (key && !map.has(key)) map.set(key, label)
  }
  return [...map.entries()]
    .map(([value, label]) => ({ value: String(value), label }))
    .sort((a, b) => a.label.localeCompare(b.label, 'ja'))
})

const filteredTraineeOptions = computed(() => {
  if (!orgFilter.value) return traineeOptions.value
  const level = orgFilterLevel.value
  const filterKey = Number(orgFilter.value)
  return traineeOptions.value.filter((u) => (u.profile || {})[level] === filterKey)
})

const practiceBooks = computed(() => books.value.filter((book) => getPracticeExams(book).length > 0))
const testBooks = computed(() => books.value.filter((book) => getTestExams(book).length > 0))
const formalAttempts = computed(() => attempts.value.filter((attempt) => attempt.formal_exam))

const trainingSummary = computed(() => ({
  books: books.value.length,
  questions: books.value.reduce((sum, book) => sum + Number(book.question_count || 0), 0),
  exams: books.value.reduce((sum, book) => sum + Number(book.exams?.length || 0), 0),
  tracks: tracks.value.length,
}))

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
  for (const attempt of formalAttempts.value) {
    if (attempt.result === 'PASS' && !map[attempt.book]) {
      map[attempt.book] = attempt
    }
  }
  return map
})

function getPracticeExams(book) {
  const exams = Array.isArray(book?.exams) ? book.exams : []
  return exams.filter((exam) => exam.bank_all || exam.is_random)
}

function getTestExams(book) {
  const exams = Array.isArray(book?.exams) ? book.exams : []
  return exams.filter((exam) => !exam.bank_all)
}

function selectMode(mode) {
  if (mode === 'edit' && !canViewBookEditor.value) return
  if (mode === 'test' && !canViewTest.value) return
  if (activeSession.value && activeSessionMode.value !== mode) {
    closeSession()
  }
  activeMode.value = mode
  if (mode === 'test') {
    testTab.value = 'exam'
  }
}

async function loadUsers() {
  const response = await api.accounts.getUsers({ page_size: 1000, is_active: true })
  users.value = normalizeList(response.data).map((user) => ({
    id: user.id,
    label: buildUserLabel(user),
    first_name: user.first_name,
    last_name: user.last_name,
    username: user.username,
    is_superuser: user.is_superuser || false,
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

function validateExecutionForm(mode = 'practice') {
  if (mode === 'practice') {
    return true
  }
  if (!form.traineeUser || !form.performedAt || !form.location) {
    setMessage('受講者・実施日時・実施場所を入力してください。', 'error')
    return false
  }
  if (!form.supervisorUser) {
    setMessage('テストでは試験官を入力してください。', 'error')
    return false
  }
  return true
}

async function startExam(book, exam, mode) {
  clearMessage()
  if (!validateExecutionForm(mode)) return
  startingSession.value = true
  try {
    const response = mode === 'practice'
      ? await api.trainingCertification.startPractice({
          exam_id: exam.id,
        })
      : await api.trainingCertification.startSession({
          exam_id: exam.id,
          trainee_user: Number(form.traineeUser),
          supervisor_user: form.supervisorUser ? Number(form.supervisorUser) : null,
          performed_at: form.performedAt,
          location: form.location,
          formal_exam: true,
        })
    activeSession.value = response.data
    activeSessionMode.value = mode
    lastAttempt.value = null
    Object.keys(answers).forEach((key) => delete answers[key])
    if (mode === 'practice') {
      activeMode.value = 'practice'
    } else {
      activeMode.value = 'test'
      testTab.value = 'exam'
    }
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
    const response = activeSessionMode.value === 'practice'
      ? await api.trainingCertification.gradePractice({
          exam_id: activeSession.value.exam.id,
          question_ids: activeSession.value.questions.map((question) => question.id),
          answers,
        })
      : await api.trainingCertification.submitAttempt({
          session_id: activeSession.value.session_id,
          answers,
        })
    lastAttempt.value = response.data
    if (activeSessionMode.value === 'practice') {
      setMessage(
        `練習を採点しました: ${response.data.result_label}`,
        response.data.result === 'PASS' ? 'success' : 'warn'
      )
    } else {
      setMessage(
        `採点結果を保存しました: ${response.data.result_label}`,
        response.data.result === 'PASS' ? 'success' : 'warn'
      )
      await refreshTraineeData()
    }
  } catch (error) {
    setMessage(error.response?.data?.detail || '採点保存に失敗しました。', 'error')
  } finally {
    submittingAttempt.value = false
  }
}

function closeSession() {
  activeSession.value = null
  activeSessionMode.value = ''
  lastAttempt.value = null
  Object.keys(answers).forEach((key) => delete answers[key])
}

async function recordStep(row, stepType) {
  clearMessage()
  if (!validateExecutionForm('test')) return
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
  const exam = getTestExams(book)[0]
  if (!exam) {
    setMessage('開始できる試験がありません。', 'error')
    return
  }
  startExam(book, exam, 'test')
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}/${pad2(date.getMonth() + 1)}/${pad2(date.getDate())} ${pad2(date.getHours())}:${pad2(date.getMinutes())}`
}

function formatOrg(...departmentIds) {
  const parts = departmentIds.map((departmentId) => lookupDepartmentName(departmentId)).filter(Boolean)
  return parts.join(' / ') || '未設定'
}

function lookupDepartmentName(departmentId) {
  if (!departmentId) return ''
  const divisionUser = users.value.find((item) => Number(item.profile?.division) === Number(departmentId))
  if (divisionUser?.profile?.division_name) return divisionUser.profile.division_name
  const groupUser = users.value.find((item) => Number(item.profile?.group) === Number(departmentId))
  if (groupUser?.profile?.group_name) return groupUser.profile.group_name
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
  () => form.supervisorUser,
  () => {
    form.traineeUser = ''
    orgFilter.value = ''
  }
)

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

watch(
  [canViewBookEditor, canViewTest],
  ([canEditBooks, canTest]) => {
    if (activeMode.value === 'edit' && !canEditBooks) {
      activeMode.value = 'practice'
    }
    if (activeMode.value === 'test' && !canTest) {
      activeMode.value = canEditBooks ? 'edit' : 'practice'
    }
  },
  { immediate: true }
)

onMounted(async () => {
  loading.value = true
  loadError.value = ''
  try {
    await Promise.all([loadUsers(), loadMasterData()])
    if (authState.user?.id) {
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

.mode-grid,
.summary-grid,
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.mode-tile,
.summary-card,
.book-card,
.exam-card,
.history-card {
  background: #fff;
  border: 1px solid #d8e0e8;
  border-radius: 14px;
  padding: 14px;
}

.mode-tile {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}

.mode-tile:not(:disabled):hover {
  transform: translateY(-1px);
  border-color: #7bb7aa;
  box-shadow: 0 8px 18px rgba(26, 61, 76, 0.08);
}

.mode-tile.active {
  border-color: #1f7a66;
  background: #eef7f4;
}

.mode-tile.disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.mode-head {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mode-icon {
  width: 24px;
  height: 24px;
  font-size: 12px;
  border-radius: 6px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  background: #e7f3ef;
  color: #1f7a66;
  font-weight: 700;
}

.mode-title,
.book-title,
.history-title,
.summary-value {
  font-weight: 700;
  color: #1f3045;
}

.mode-desc,
.mode-foot,
.book-meta,
.book-submeta,
.history-meta,
.cell-sub,
.summary-label,
.mode-hint,
.mode-summary-text {
  font-size: 12px;
  color: #5e7084;
}

.mode-foot {
  font-weight: 600;
}

.summary-card {
  display: grid;
  gap: 6px;
}

.summary-value {
  font-size: 24px;
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
  min-width: 0;
}

.field label,
.check-field {
  font-size: 13px;
  color: #415164;
}

.field input,
.field select {
  width: 100%;
  box-sizing: border-box;
  min-height: 38px;
  padding: 6px 10px;
  border: 1px solid #c8d2dc;
  border-radius: 8px;
}

.org-filter-select {
  font-size: 12px;
  min-height: 30px;
  padding: 2px 8px;
  border: 1px solid #c8d2dc;
  border-radius: 6px;
  background: #f8fafb;
}

.mode-summary {
  padding: 10px 12px;
  border-radius: 10px;
  background: #f3f7fa;
}

.mode-summary-title {
  font-size: 13px;
  font-weight: 700;
  color: #1f3045;
}

.message,
.info-box,
.summary-banner,
.mode-hint {
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

.mode-hint {
  background: #f7f7eb;
  border: 1px solid #e6dfbd;
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

@media (max-width: 1100px) {
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
    grid-column: auto;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
