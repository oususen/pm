<template>
  <div class="ot-form-page">
    <h1 class="page-title">{{ isEdit ? '残業申請 編集' : '残業申請' }}</h1>

    <form class="ot-form" @submit.prevent="handleSubmit">
      <div class="form-section">
        <div class="form-row">
          <label class="form-label required">申請種別</label>
          <div class="radio-group">
            <label class="radio-item">
              <input type="radio" v-model="form.application_type" value="overtime" />
              時間外
            </label>
            <label class="radio-item">
              <input type="radio" v-model="form.application_type" value="holiday" />
              休日出勤
            </label>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label required">実施日</label>
          <input type="date" v-model="form.work_date" class="form-input" required />
        </div>

        <div class="form-row">
          <label class="form-label">勤務時間</label>
          <div class="time-range">
            <input type="text" v-model="form.work_start_time" class="form-input time-input" placeholder="08:00" maxlength="5" @blur="formatTime('work_start_time')" />
            <span class="tilde">〜</span>
            <input type="text" v-model="form.scheduled_end_time" class="form-input time-input" placeholder="17:15" maxlength="5" @blur="formatTime('scheduled_end_time')" />
            <span class="time-note">（定時）</span>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label required">残業時間</label>
          <div class="time-range">
            <input type="text" v-model="form.start_time" class="form-input time-input" placeholder="17:15" maxlength="5" @blur="formatTime('start_time')" required />
            <span class="tilde">〜</span>
            <input type="text" v-model="form.end_time" class="form-input time-input" placeholder="19:00" maxlength="5" @blur="formatTime('end_time')" required />
          </div>
        </div>

        <div v-if="previewHours !== null" class="form-row">
          <label class="form-label">時間数（自動計算）</label>
          <div class="hours-preview">
            <span class="hours-val">{{ previewHours.regular }}H</span>
            <span v-if="previewHours.midnight > 0" class="hours-midnight">
              うち深夜 {{ previewHours.midnight }}H
            </span>
          </div>
        </div>

        <div class="form-row">
          <label class="form-label">発生理由</label>
          <textarea
            v-model="form.reason"
            class="form-textarea"
            rows="3"
            placeholder="残業・休日出勤が発生した理由を入力してください"
          ></textarea>
        </div>
      </div>

      <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

      <div class="form-actions">
        <button type="button" class="btn btn-secondary" @click="saveDraft" :disabled="saving">
          下書き保存
        </button>
        <button type="submit" class="btn btn-primary" :disabled="saving">
          {{ isEdit ? '更新して申請する' : '申請する' }}
        </button>
        <RouterLink to="/overtime/list" class="btn btn-ghost">キャンセル</RouterLink>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'

// "800" "0800" "8:00" "08:00" → "08:00"、変換不能なら元の値を返す
function toHHMM(val) {
  if (!val) return val
  const s = String(val).trim().replace('：', ':')
  // すでに HH:MM 形式
  if (/^\d{1,2}:\d{2}$/.test(s)) {
    const [h, m] = s.split(':').map(Number)
    if (h >= 0 && h <= 29 && m >= 0 && m <= 59) {
      return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
    }
  }
  // 3〜4桁の数字 "800" "1715"
  if (/^\d{3,4}$/.test(s)) {
    const h = s.length === 3 ? Number(s[0]) : Number(s.slice(0, 2))
    const m = Number(s.slice(-2))
    if (h >= 0 && h <= 29 && m >= 0 && m <= 59) {
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

const props = defineProps({
  id: { type: [String, Number], default: null },
})

const isEdit = computed(() => !!props.id)
const saving = ref(false)
const errorMsg = ref('')

const form = ref({
  application_type: 'overtime',
  work_date: '',
  work_start_time: '',
  scheduled_end_time: '',
  start_time: '',
  end_time: '',
  reason: '',
})

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

  const totalMin = endMin - startMin

  // 深夜帯: 22:00(1320)〜29:00(1740=翌05:00)
  const midnightStart = 22 * 60
  const midnightEnd = 29 * 60
  const mStart = Math.max(startMin, midnightStart)
  const mEnd = Math.min(endMin, midnightEnd)
  const midnightMin = Math.max(0, mEnd - mStart)
  const regularMin = totalMin - midnightMin

  return {
    regular: Math.round(regularMin / 60 * 10) / 10,
    midnight: Math.round(midnightMin / 60 * 10) / 10,
  }
})

// フォーカスが外れたとき自動整形
function formatTime(field) {
  form.value[field] = toHHMM(form.value[field])
}
function formatDate() {
  form.value.work_date = toYYYYMMDD(form.value.work_date)
}

// 送信前に全フィールドを正規化した payload を返す
function normalizedPayload() {
  return {
    ...form.value,
    work_date: toYYYYMMDD(form.value.work_date),
    work_start_time: toHHMM(form.value.work_start_time) || null,
    scheduled_end_time: toHHMM(form.value.scheduled_end_time) || null,
    start_time: toHHMM(form.value.start_time),
    end_time: toHHMM(form.value.end_time),
  }
}

onMounted(async () => {
  if (isEdit.value) {
    try {
      const res = await api.overtime.getApplication(props.id)
      const d = res.data
      form.value = {
        application_type: d.application_type,
        work_date: d.work_date,
        work_start_time: d.work_start_time || '',
        scheduled_end_time: d.scheduled_end_time || '',
        start_time: d.start_time,
        end_time: d.end_time,
        reason: d.reason,
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
    form.value.work_date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  }
})

async function saveDraft() {
  saving.value = true
  errorMsg.value = ''
  try {
    const payload = normalizedPayload()
    if (isEdit.value) {
      await api.overtime.updateApplication(props.id, payload)
    } else {
      await api.overtime.createApplication(payload)
    }
    router.push('/overtime/list')
  } catch (e) {
    errorMsg.value = '保存に失敗しました: ' + (e.response?.data?.detail || e.message)
  } finally {
    saving.value = false
  }
}

async function handleSubmit() {
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
    // 申請提出
    await api.overtime.submitApplication(appId)
    router.push('/overtime/list')
  } catch (e) {
    errorMsg.value = '申請に失敗しました: ' + (e.response?.data?.detail || e.message)
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
