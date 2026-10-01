<template>
  <div v-if="task" class="urt-overlay" @click.self="close">
    <div class="urt-dialog" role="dialog" aria-label="システム管理者リクエスト">
      <header>
        <strong>システム管理者リクエスト</strong>
        <button type="button" title="閉じる" :disabled="saving" @click="close">×</button>
      </header>
      <div class="meta">
        <span>種類: {{ task.request_type_label }}</span>
        <span>依頼者: {{ task.requester_name || '-' }}</span>
        <span>メール: {{ task.requester_email || '-' }}</span>
        <span>送信: {{ formatDateTime(task.created_at) }}</span>
      </div>
      <div class="field">
        <label>件名</label>
        <div class="value">{{ task.subject }}</div>
      </div>
      <div class="field">
        <label>内容</label>
        <div class="value body">{{ task.body }}</div>
      </div>
      <p class="hint">添付ファイルは、システム管理者宛に届いたメールで確認してください。</p>
      <div class="field">
        <label>状況</label>
        <select v-model="status" :disabled="saving">
          <option v-for="option in STATUS_OPTIONS" :key="option.value" :value="option.value">{{ option.label }}</option>
        </select>
        <span v-if="task.handled_by_name" class="handled">最終対応: {{ task.handled_by_name }}（{{ formatDateTime(task.handled_at) }}）</span>
      </div>
      <div v-if="status === 'REJECTED'" class="field top">
        <label>却下理由<span class="req" title="必須">*</span></label>
        <div class="reason">
          <textarea v-model="rejectReason" rows="3" maxlength="1000" placeholder="依頼者へ返信メールで伝える理由を入力" :disabled="saving"></textarea>
          <small v-if="task.status !== 'REJECTED'">保存すると、依頼者へ返信メールを送ります。</small>
        </div>
      </div>
      <p v-if="errorMessage" class="msg error">{{ errorMessage }}</p>
      <p v-if="warningMessage" class="msg warn">{{ warningMessage }}</p>
      <footer>
        <button type="button" class="primary" :disabled="saving || !canSave" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
        <button type="button" class="danger" :disabled="saving" @click="remove">削除</button>
        <button type="button" :disabled="saving" @click="close">閉じる</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import api from '@/api/client'

const props = defineProps({
  task: { type: Object, default: null },
})
const emit = defineEmits(['close', 'changed'])

const STATUS_OPTIONS = [
  { value: 'PENDING', label: '未対応' },
  { value: 'IN_PROGRESS', label: '対応中' },
  { value: 'DONE', label: '完了' },
  { value: 'REJECTED', label: '却下' },
]

const status = ref('PENDING')
const rejectReason = ref('')
const saving = ref(false)
const errorMessage = ref('')
const warningMessage = ref('')

watch(() => props.task, (task) => {
  status.value = task?.status || 'PENDING'
  rejectReason.value = task?.reject_reason || ''
  errorMessage.value = ''
  warningMessage.value = ''
}, { immediate: true })

const canSave = computed(() => {
  if (!props.task) return false
  if (status.value === 'REJECTED' && !rejectReason.value.trim()) return false
  return status.value !== props.task.status || (status.value === 'REJECTED' && rejectReason.value.trim() !== props.task.reject_reason)
})

const formatDateTime = (value) => {
  if (!value) return '-'
  const dt = new Date(value)
  return Number.isNaN(dt.getTime()) ? value : dt.toLocaleString('ja-JP')
}

const close = () => {
  if (!saving.value) emit('close')
}

const save = async () => {
  if (!canSave.value || saving.value) return
  saving.value = true
  errorMessage.value = ''
  warningMessage.value = ''
  try {
    const { data } = await api.userRequests.updateTask(props.task.id, {
      status: status.value,
      reject_reason: status.value === 'REJECTED' ? rejectReason.value.trim() : '',
    })
    emit('changed')
    if (data?.warning) {
      warningMessage.value = data.warning
    } else {
      emit('close')
    }
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || '保存に失敗しました。'
  } finally {
    saving.value = false
  }
}

const remove = async () => {
  if (saving.value) return
  if (!window.confirm('このリクエストを削除します。元に戻せません。よろしいですか？')) return
  saving.value = true
  errorMessage.value = ''
  try {
    await api.userRequests.deleteTask(props.task.id)
    emit('changed')
    emit('close')
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || '削除に失敗しました。'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.urt-overlay{position:fixed;inset:0;z-index:1200;background:rgba(0,0,0,.35);display:grid;place-items:center;padding:12px}
.urt-dialog{width:min(600px,100%);max-height:100%;overflow:auto;background:#fff;border-radius:8px;box-shadow:0 10px 30px rgba(0,0,0,.25);padding:10px 12px;display:flex;flex-direction:column;gap:6px;font-size:13px}
header,footer{display:flex;align-items:center;gap:8px}
header{justify-content:space-between}
header button{border:0;background:none;font-size:18px;cursor:pointer}
.meta{display:flex;flex-wrap:wrap;gap:4px 14px;color:#444}
.field{display:flex;gap:8px;align-items:center}
.field.top{align-items:flex-start}
.field>label{flex:0 0 56px;font-weight:600}
.field .value{flex:1;min-width:0;padding:4px 6px;border:1px solid #e1e4e8;border-radius:4px;background:#f8f9fa;word-break:break-word}
.field .value.body{white-space:pre-wrap;max-height:240px;overflow:auto}
.field select,.field textarea{padding:4px 6px;border:1px solid #c8ccd0;border-radius:4px;font:inherit}
.reason{flex:1;display:flex;flex-direction:column;gap:2px}
.reason textarea{width:100%;resize:vertical}
.reason small,.handled,.hint{color:#666;font-size:12px}
.hint{margin:0}
.req{margin-left:2px;color:#c0392b}
footer button{padding:4px 12px;border:1px solid #c8ccd0;border-radius:4px;background:#f5f6f7;cursor:pointer}
footer .primary{background:#087b6e;color:#fff;border-color:#087b6e}
footer .danger{margin-left:auto;color:#c0392b;border-color:#e0b4ae}
footer button:disabled{opacity:.5;cursor:default}
.msg{margin:0;font-weight:600}
.msg.error{color:#c0392b}
.msg.warn{color:#b9770e}
</style>
