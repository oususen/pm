<template>
  <div class="ot-form-page">
    <h1 class="page-title">{{ isEdit ? t('overtime.pageTitleEdit') : t('overtime.pageTitle') }}</h1>
    <p class="company-note-top">{{ t('overtime.companyNote') }}</p>

    <form class="ot-form" @submit.prevent="handleSubmit">
      <div class="form-section">
        <div class="form-row">
          <label class="form-label required">{{ t('overtime.type') }}</label>
          <div class="radio-group">
            <label class="radio-item">
              <input type="radio" v-model="form.application_type" value="overtime" />
              {{ t('overtime.type.overtime') }}
            </label>
            <label class="radio-item">
              <input type="radio" v-model="form.application_type" value="holiday" />
              {{ t('overtime.type.holiday') }}
            </label>
            <label class="radio-item">
              <input type="radio" v-model="form.application_type" value="half_day_am" />
              {{ t('overtime.type.halfDayAm') }}
            </label>
            <label class="radio-item">
              <input type="radio" v-model="form.application_type" value="half_day_pm" />
              {{ t('overtime.type.halfDayPm') }}
            </label>
            <label class="radio-item">
              <input type="radio" v-model="form.application_type" value="paid_leave" />
              {{ t('overtime.type.paidLeave') }}
            </label>
            <label class="radio-item">
              <input type="radio" v-model="form.application_type" value="paid_leave_consec" />
              {{ t('overtime.type.paidLeaveConsec') }}
            </label>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label required">対象者</label>
          <div class="applicant-field">
            <select
              v-if="canSelectApplicant"
              v-model="form.applicant"
              class="form-input form-select"
            >
              <option v-for="user in applicantOptions" :key="user.id" :value="user.id">
                {{ user.label }}
              </option>
            </select>
            <div v-else class="applicant-fixed">{{ currentUserName }}</div>
            <p v-if="canSelectApplicant" class="applicant-note">
              午前半休・午後半休・有給・連続有給は、リーダーまたは班長が管理目的で登録できます。
            </p>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label required">{{ isConsecutive ? t('overtime.startDate') : t('overtime.workDate') }}</label>
          <input type="date" v-model="form.work_date" class="form-input" required />
        </div>

        <div v-if="isConsecutive" class="form-row">
          <label class="form-label required">{{ t('overtime.endDate') }}</label>
          <input type="date" v-model="form.end_date" class="form-input" required />
        </div>

        <!-- 休日出勤: 勤務パターン選択 -->
        <div v-if="form.application_type === 'holiday'" class="form-row">
          <label class="form-label">勤務パターン</label>
          <select v-model="form.work_pattern" class="form-input form-select">
            <option :value="null">-- 選択してください（未選択=通常8H）--</option>
            <option v-for="wp in holidayWorkPatterns" :key="wp.id" :value="wp.id">
              {{ wp.pattern_name }}（{{ wp.start_time }} 〜 {{ wp.end_time }}）
            </option>
          </select>
        </div>

        <p v-if="form.application_type === 'half_day_am'" class="half-day-note">
          {{ t('overtime.halfDayNote') }}
        </p>

        <!-- 時間外・午前半休: 勤務時間 + 残業時間（両方必須） -->
        <template v-if="needsTimeInput && form.application_type !== 'holiday'">
          <div class="form-row">
            <label class="form-label required">{{ t('overtime.workTime') }}</label>
            <div class="time-range">
              <input type="text" v-model="form.work_start_time" class="form-input time-input" placeholder="08:00" maxlength="5" @blur="onWorkStartBlur" />
              <span class="tilde">〜</span>
              <input type="text" v-model="form.scheduled_end_time" class="form-input time-input" placeholder="17:05" maxlength="5" @blur="formatTime('scheduled_end_time')" />
              <span class="time-note">（{{ t('overtime.scheduled') }}）</span>
            </div>
          </div>

          <div class="form-row">
            <label class="form-label required">{{ t('overtime.overtimeTime') }}</label>
            <div class="time-range">
              <input type="text" v-model="form.start_time" class="form-input time-input" placeholder="17:15" maxlength="5" @blur="formatTime('start_time')" required />
              <span class="tilde">〜</span>
              <input type="text" v-model="form.end_time" class="form-input time-input" placeholder="19:00" maxlength="5" @blur="formatTime('end_time')" required />
            </div>
          </div>
        </template>

        <!-- 休日出勤: 勤務時間帯（任意） -->
        <div v-if="form.application_type === 'holiday'" class="form-row">
          <label class="form-label">勤務時間帯</label>
          <div class="time-range">
            <input type="text" v-model="form.start_time" class="form-input time-input" placeholder="08:00" maxlength="5" @blur="onHolidayStartBlur" />
            <span class="tilde">〜</span>
            <input type="text" v-model="form.end_time" class="form-input time-input" placeholder="15:00" maxlength="5" @blur="formatTime('end_time')" />
          </div>
        </div>

        <div v-if="!needsApproval" class="form-row">
          <label class="form-label"></label>
          <span class="record-only-badge">{{ t('overtime.recordOnly') }}</span>
        </div>

        <div v-if="needsTimeInput && previewHours !== null" class="form-row">
          <label class="form-label">{{ t('overtime.hoursPreview') }}</label>
          <div class="hours-preview">
            <span class="hours-val">{{ previewHours.total }}H</span>
            <span v-if="previewHours.midnight > 0" class="hours-midnight">
              {{ t('overtime.midnight') }} {{ previewHours.midnight }}H
            </span>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label" :class="{ required: needsApproval }">{{ t('overtime.reason') }}</label>
          <textarea
            v-model="form.reason"
            class="form-textarea"
            rows="5"
            :placeholder="needsApproval ? t('overtime.reasonPlaceholder') : t('overtime.remarkPlaceholder')"
            :required="needsApproval"
          ></textarea>
        </div>

        <div v-if="needsApproval" class="form-row sign-row">
          <label class="form-label required">{{ t('overtime.sign') }}</label>
          <div class="sign-wrap">
            <canvas ref="signCanvas" class="sign-canvas" width="420" height="200"></canvas>
            <button type="button" class="btn-clear-sign" @click="clearSign">{{ t('overtime.signClear') }}</button>
          </div>
        </div>
      </div>

      <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

      <div class="form-actions">
        <button type="button" class="btn btn-secondary" @click="saveDraft" :disabled="saving">
          {{ t('overtime.saveDraft') }}
        </button>
        <button type="submit" class="btn btn-primary" :disabled="saving">
          {{ isEdit ? t('overtime.submitEdit') : t('overtime.submit') }}
        </button>
        <RouterLink to="/overtime/list" class="btn btn-ghost">{{ t('overtime.cancel') }}</RouterLink>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import SignaturePad from 'signature_pad'
import api from '@/api/client'
import { authState, ensureAuth } from '@/auth'
import { t } from '@/i18n'

// "800" "0800" "8:00" "08:00" → "08:00"、変換不能なら元の値を返す
function toHHMM(val) {
  if (!val) return val
  const s = String(val).trim().replace('：', ':')
  // すでに HH:MM 形式
  if (/^\d{1,2}:\d{2}$/.test(s)) {
    const [h, m] = s.split(':').map(Number)
    if (h >= 0 && h <= 47 && m >= 0 && m <= 59) {
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
    }
  }
  // 3〜4桁の数字 "800" "1715" "3111"
  if (/^\d{3,4}$/.test(s)) {
    const h = s.length === 3 ? Number(s[0]) : Number(s.slice(0, 2))
    const m = Number(s.slice(-2))
    if (h >= 0 && h <= 47 && m >= 0 && m <= 59) {
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
    }
  }
  return val
}

// "20260314" "2026/03/14" "2026-03-14" → "2026-03-14"
function toYYYYMMDD(val) {
  if (!val) return val
  const s = String(val).trim().replace(/\//g, '-')
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s
  if (/^\d{8}$/.test(s)) return `${s.slice(0,4)}-${s.slice(4,6)}-${s.slice(6,8)}`
  return val
}

const router = useRouter()
const currentUserId = computed(() => Number(authState.user?.id || 0))
const currentUserName = computed(() => {
  const user = authState.user
  if (!user) return ''
  return `${user.last_name || ''} ${user.first_name || ''}`.trim() || user.username || ''
})
const canProxyRole = computed(() => ['leader', 'supervisor'].includes(authState.user?.profile?.role || ''))

// サインパッド
const signCanvas = ref(null)
let signaturePad = null

function clearSign() {
  signaturePad?.clear()
}

async function uploadSignIfNeeded(appId) {
  if (!signaturePad || signaturePad.isEmpty()) return
  try {
    const dataURL = signaturePad.toDataURL('image/png')
    const res = await fetch(dataURL)
    const blob = await res.blob()
    await api.overtime.uploadSignature(appId, blob)
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || 'サイン画像の保存に失敗しました。'
    throw new Error(detail)
  }
}

const props = defineProps({
  id: { type: [String, Number], default: null },
})

const isEdit = computed(() => !!props.id)

// 種別に関するcomputed
const NEEDS_APPROVAL_TYPES = new Set(['overtime', 'holiday', 'half_day_am'])
const SELF_ONLY_TYPES = new Set(['overtime', 'holiday'])
const needsApproval = computed(() => NEEDS_APPROVAL_TYPES.has(form.value.application_type))
const needsTimeInput = computed(() => NEEDS_APPROVAL_TYPES.has(form.value.application_type))
const isConsecutive = computed(() => form.value.application_type === 'paid_leave_consec')
const canSelectApplicant = computed(() => canProxyRole.value && !SELF_ONLY_TYPES.has(form.value.application_type))
const saving = ref(false)
const errorMsg = ref('')
const applicantOptions = ref([])

const form = ref({
  applicant: null,
  application_type: 'overtime',
  work_date: '',
  end_date: '',
  work_start_time: '',
  scheduled_end_time: '',
  start_time: '',
  end_time: '',
  reason: '',
  work_pattern: null,
})

const workPatterns = ref([])
// 休日出勤パターンのみ: コードがk***または名称に「休日」を含む
const holidayWorkPatterns = computed(() =>
  workPatterns.value.filter(wp =>
    /^k/i.test(wp.pattern_code) || wp.pattern_name.includes('休日')
  )
)
const selectedPatternBreaks = ref([])  // 選択中パターンの休憩時間リスト

function buildApplicantLabel(user) {
  const fullName = `${user.last_name || ''} ${user.first_name || ''}`.trim() || user.username || `ID:${user.id}`
  const teamName = user.profile?.team_name || ''
  const unitName = user.profile?.unit_name || ''
  const org = [teamName, unitName].filter(Boolean).join(' / ')
  return org ? `${fullName}（${org}）` : fullName
}

async function loadApplicantOptions() {
  if (!canProxyRole.value) {
    applicantOptions.value = currentUserId.value
      ? [{ id: currentUserId.value, label: currentUserName.value }]
      : []
    return
  }

  try {
    const res = await api.accounts.getUsers({ page_size: 1000, is_active: true })
    const users = res.data?.results ?? res.data ?? []
    const myProfile = authState.user?.profile || {}
    const teamIds = new Set(
      [myProfile.team_id, ...(Array.isArray(myProfile.supervisor_teams) ? myProfile.supervisor_teams : [])]
        .filter(Boolean)
        .map(Number)
    )
    const unitIds = new Set(
      [myProfile.unit_id, ...(Array.isArray(myProfile.leader_units) ? myProfile.leader_units : [])]
        .filter(Boolean)
        .map(Number)
    )

    const filtered = users.filter((user) => {
      if (Number(user.id) === currentUserId.value) return true
      if ((authState.user?.profile?.role || '') === 'supervisor') {
        return teamIds.has(Number(user.profile?.team))
      }
      if ((authState.user?.profile?.role || '') === 'leader') {
        return unitIds.has(Number(user.profile?.unit))
      }
      return false
    })

    applicantOptions.value = filtered
      .map((user) => ({ id: Number(user.id), label: buildApplicantLabel(user) }))
      .sort((a, b) => a.label.localeCompare(b.label, 'ja'))
  } catch (e) {
    applicantOptions.value = currentUserId.value
      ? [{ id: currentUserId.value, label: currentUserName.value }]
      : []
  }
}

function ensureApplicantOption(userId, label) {
  const numericId = Number(userId || 0)
  if (!numericId || applicantOptions.value.some((user) => user.id === numericId)) return
  applicantOptions.value.push({ id: numericId, label: label || `ID:${numericId}` })
  applicantOptions.value.sort((a, b) => a.label.localeCompare(b.label, 'ja'))
}

// 勤務パターン変更時に休憩時間を取得
watch(() => form.value.work_pattern, async (newVal) => {
  if (!newVal) { selectedPatternBreaks.value = []; return }
  try {
    const res = await api.workPatterns.getBreakTimes(newVal)
    selectedPatternBreaks.value = res.data?.results ?? res.data ?? []
  } catch (e) {
    selectedPatternBreaks.value = []
  }
})

watch(
  () => form.value.application_type,
  (newType) => {
    if (SELF_ONLY_TYPES.has(newType)) {
      form.value.applicant = currentUserId.value || null
    } else if (!form.value.applicant) {
      form.value.applicant = currentUserId.value || null
    }
  }
)

// 2時間ごとに10分休憩を控除（130分サイクル）
function applyBreaks(wallMinutes) {
  const CYCLE = 130 // 2h work(120) + 10min break
  const fullCycles = Math.floor(wallMinutes / CYCLE)
  const remainder = wallMinutes % CYCLE
  return fullCycles * 120 + Math.min(remainder, 120)
}

// 勤務パターンの実休憩時間を使った控除（分）
function calcBreakMinutesFromPattern(startMin, endMin, breaks) {
  let total = 0
  const crossesMidnight = endMin > 24 * 60
  for (const brk of breaks) {
    const [bsh, bsm] = brk.break_start.split(':').map(Number)
    const [beh, bem] = brk.break_end.split(':').map(Number)
    let bs = bsh * 60 + bsm
    let be = beh * 60 + bem
    if (be <= bs) be += 24 * 60
    // 日をまたぐシフトで深夜後の早朝休憩（00:00台など）を翌日扱いに補正
    if (crossesMidnight && bs < 12 * 60 && bs < startMin) {
      bs += 24 * 60
      be += 24 * 60
    }
    const overlapS = Math.max(startMin, bs)
    const overlapE = Math.min(endMin, be)
    if (overlapE > overlapS) total += overlapE - overlapS
  }
  return total
}

// 時間数プレビュー（フロントエンドで計算）
const previewHours = computed(() => {
  const startRaw = toHHMM(form.value.start_time)
  const endRaw = toHHMM(form.value.end_time)
  if (!startRaw || !startRaw.includes(':') || !endRaw || !endRaw.includes(':')) return null
  const [sh, sm] = startRaw.split(':').map(Number)
  const [eh, em] = endRaw.split(':').map(Number)
  let startMin = sh * 60 + sm
  let endMin = eh * 60 + em
  if (endMin <= startMin) endMin += 24 * 60

  const wallMin = endMin - startMin

  // 深夜帯: 22:00(1320)〜29:00(1740=翌05:00)
  const midnightStart = 22 * 60
  const midnightEnd = 29 * 60
  const midnightWall = Math.max(0, Math.min(endMin, midnightEnd) - Math.max(startMin, midnightStart))

  // 休憩控除: 休日出勤かつパターン選択あり → 実休憩時間、それ以外 → 汎用計算
  let workMin
  if (form.value.application_type === 'holiday' && selectedPatternBreaks.value.length > 0) {
    const breakMin = calcBreakMinutesFromPattern(startMin, endMin, selectedPatternBreaks.value)
    workMin = Math.floor((wallMin - breakMin) / 30) * 30
  } else {
    workMin = Math.floor(applyBreaks(wallMin) / 30) * 30
  }

  // 深夜も30分単位で切り捨て、通常 = 合計 - 深夜
  const ratio = wallMin > 0 ? workMin / wallMin : 1
  const midnightMin = Math.floor(midnightWall * ratio / 30) * 30
  const regularMin = workMin - midnightMin

  const regularH = regularMin / 60
  const midnightH = midnightMin / 60
  return {
    total: Math.round((regularH + midnightH) * 10) / 10,
    midnight: Math.round(midnightH * 10) / 10,
  }
})

// HH:MM に分を加算して HH:MM を返す
function addMinutes(hhmm, minutes) {
  const fmt = toHHMM(hhmm)
  if (!fmt || !fmt.includes(':')) return ''
  const [h, m] = fmt.split(':').map(Number)
  const total = h * 60 + m + minutes
  const nh = Math.floor(total / 60)
  const nm = total % 60
  return `${String(nh).padStart(2, '0')}:${String(nm).padStart(2, '0')}`
}

// フォーカスが外れたとき自動整形
function formatTime(field) {
  form.value[field] = toHHMM(form.value[field])
}

// 休日出勤の勤務時間帯開始blur: 整形 + パターン開始時間より早ければ補正
function onHolidayStartBlur() {
  formatTime('start_time')
  const selected = workPatterns.value.find(wp => wp.id === form.value.work_pattern)
  if (!selected || !selected.start_time) return
  const patternStart = toHHMM(selected.start_time)
  if (!patternStart) return
  const [ph, pm] = patternStart.split(':').map(Number)
  const patternMin = ph * 60 + pm
  const entered = toHHMM(form.value.start_time)
  if (!entered || !entered.includes(':')) return
  const [eh, em] = entered.split(':').map(Number)
  const enteredMin = eh * 60 + em
  if (enteredMin < patternMin) {
    form.value.start_time = patternStart
  }
}

// 勤務開始時間のblur: 整形 + 定時終了・残業開始を自動セット
function onWorkStartBlur() {
  formatTime('work_start_time')
  const base = form.value.work_start_time
  if (!base) return
  form.value.scheduled_end_time = addMinutes(base, 9 * 60 + 5)   // +9h5m
  form.value.start_time = addMinutes(base, 9 * 60 + 15)           // +9h15m
}
function formatDate() {
  form.value.work_date = toYYYYMMDD(form.value.work_date)
}

// 24時間を超える時刻を % 24 で巻き戻す（27:20 → 03:20）
function wrapTime(hhmm) {
  if (!hhmm || !hhmm.includes(':')) return hhmm
  const [h, m] = hhmm.split(':').map(Number)
  if (h < 24) return hhmm
  return `${String(h % 24).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

// 送信前に全フィールドを正規化した payload を返す
function normalizedPayload() {
  const type = form.value.application_type
  const hasTime = NEEDS_APPROVAL_TYPES.has(type)
  const isHoliday = type === 'holiday'
  return {
    ...form.value,
    applicant: Number(form.value.applicant || currentUserId.value || 0) || null,
    work_date: toYYYYMMDD(form.value.work_date),
    end_date: form.value.end_date ? toYYYYMMDD(form.value.end_date) : null,
    // 休日出勤は標準勤務時間なし（勤務パターンで管理）
    work_start_time: (hasTime && !isHoliday) ? (toHHMM(form.value.work_start_time) || null) : null,
    scheduled_end_time: (hasTime && !isHoliday) ? (wrapTime(toHHMM(form.value.scheduled_end_time)) || null) : null,
    // 休日出勤は任意、他の承認種別は必須
    start_time: hasTime ? (wrapTime(toHHMM(form.value.start_time)) || null) : null,
    end_time: hasTime ? (wrapTime(toHHMM(form.value.end_time)) || null) : null,
  }
}

onMounted(async () => {
  await ensureAuth()

  // サインパッド初期化
  if (signCanvas.value) {
    signaturePad = new SignaturePad(signCanvas.value, { penColor: '#1f2a44' })
  }

  // 勤務パターン取得
  try {
    const res = await api.workPatterns.getWorkPatterns()
    workPatterns.value = res.data?.results ?? res.data ?? []
  } catch (e) {
    console.warn('勤務パターン取得失敗:', e)
  }

  await loadApplicantOptions()

  if (isEdit.value) {
    try {
      const res = await api.overtime.getApplication(props.id)
      const d = res.data
      ensureApplicantOption(d.applicant, d.applicant_name)
      form.value = {
        applicant: d.applicant || currentUserId.value || null,
        application_type: d.application_type,
        work_date: d.work_date,
        end_date: d.end_date || '',
        work_start_time: d.work_start_time || '',
        scheduled_end_time: d.scheduled_end_time || '',
        start_time: d.start_time || '',
        end_time: d.end_time || '',
        reason: d.reason,
        work_pattern: d.work_pattern || null,
      }
    } catch (e) {
      errorMsg.value = '申請データの取得に失敗しました。'
    }
  } else {
    // デフォルト: 10時日替わり（10時未満は前日扱い）
    const now = new Date()
    if (now.getHours() < 10) {
      now.setDate(now.getDate() - 1)
    }
    form.value.applicant = currentUserId.value || null
    form.value.work_date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  }
})

async function saveDraft() {
  if (needsApproval.value && !form.value.reason.trim()) {
    errorMsg.value = '発生理由を入力してください'
    return
  }
  saving.value = true
  errorMsg.value = ''
  try {
    const payload = normalizedPayload()
    let appId = props.id
    if (isEdit.value) {
      await api.overtime.updateApplication(props.id, payload)
    } else {
      const res = await api.overtime.createApplication(payload)
      appId = res.data.id
    }
    await uploadSignIfNeeded(appId)
    router.push('/overtime/list')
  } catch (e) {
    const data = e.response?.data
    const apiMsg = data?.detail || data?.non_field_errors?.[0] || e.message
    errorMsg.value = t('overtime.error.saveFailed') + apiMsg
  } finally {
    saving.value = false
  }
}

async function handleSubmit() {
  if (needsApproval.value && !form.value.reason.trim()) {
    errorMsg.value = '発生理由を入力してください'
    return
  }
  if (needsApproval.value && (!signaturePad || signaturePad.isEmpty())) {
    errorMsg.value = t('overtime.error.signRequired')
    return
  }
  saving.value = true
  errorMsg.value = ''
  try {
    const payload = normalizedPayload()
    let appId = props.id
    if (isEdit.value) {
      await api.overtime.updateApplication(props.id, payload)
    } else {
      const res = await api.overtime.createApplication(payload)
      appId = res.data.id
    }
    await uploadSignIfNeeded(appId)
    // 申請提出
    await api.overtime.submitApplication(appId)
    router.push('/overtime/list')
  } catch (e) {
    const data = e.response?.data
    const apiMsg = data?.detail || data?.non_field_errors?.[0] || e.message
    errorMsg.value = t('overtime.error.submitFailed') + apiMsg
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.ot-form-page {
  padding: 24px;
  max-width: 640px;
  margin: 0 auto;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  color: #1f2a44;
  margin-bottom: 24px;
}
.ot-form {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px;
}
.form-section {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.form-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.form-label {
  width: 120px;
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  padding-top: 6px;
}
.form-label.required::after {
  content: ' *';
  color: #ef4444;
}
.form-input {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 14px;
  outline: none;
}
.form-input:focus {
  border-color: #40916c;
}
.applicant-field {
  flex: 1;
}
.applicant-fixed {
  min-height: 36px;
  display: flex;
  align-items: center;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #f9fafb;
  color: #374151;
  font-size: 14px;
}
.applicant-note {
  margin: 6px 0 0;
  font-size: 12px;
  color: #6b7280;
}
.time-range {
  display: flex;
  align-items: center;
  gap: 8px;
}
.time-input {
  width: 110px;
}
.tilde {
  font-size: 16px;
  color: #6b7280;
}
.time-note {
  font-size: 12px;
  color: #9ca3af;
}
.form-textarea {
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 14px;
  resize: vertical;
  outline: none;
}
.form-textarea:focus {
  border-color: #40916c;
}
.radio-group {
  display: flex;
  gap: 20px;
  padding-top: 6px;
}
.radio-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  cursor: pointer;
}
.hours-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 6px;
}
.hours-val {
  font-size: 18px;
  font-weight: 700;
  color: #40916c;
}
.hours-midnight {
  font-size: 13px;
  color: #7c3aed;
  background: #f5f3ff;
  padding: 2px 8px;
  border-radius: 4px;
}
.error-msg {
  margin-top: 16px;
  color: #ef4444;
  font-size: 13px;
  padding: 10px 12px;
  background: #fef2f2;
  border-radius: 6px;
}
.half-day-note {
  margin: 0 0 4px;
  font-size: 12px;
  color: #1e40af;
  background: #eff6ff;
  border: 1px solid #93c5fd;
  border-radius: 6px;
  padding: 8px 12px;
  line-height: 1.6;
}
.company-note-top {
  margin: 0 0 16px;
  font-size: 12px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fcd34d;
  border-radius: 6px;
  padding: 8px 12px;
  line-height: 1.6;
}
.record-only-badge {
  display: inline-block;
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #86efac;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
}
.sign-row { align-items: flex-start; }
.sign-wrap { display: flex; flex-direction: column; gap: 6px; }
.sign-canvas {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  touch-action: none;
  cursor: crosshair;
  display: block;
}
.btn-clear-sign {
  align-self: flex-end;
  background: none;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 12px;
  color: #6b7280;
  cursor: pointer;
}
.btn-clear-sign:hover { background: #f3f4f6; }
.form-actions {
  margin-top: 24px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary {
  background: #40916c;
  color: white;
}
.btn-primary:hover:not(:disabled) {
  background: #2d6a4f;
}
.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}
.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}
.btn-ghost {
  background: transparent;
  color: #6b7280;
}
.btn-ghost:hover {
  color: #374151;
}
</style>
