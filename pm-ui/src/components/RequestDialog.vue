<template>
  <div v-if="requestDialogOpen" class="req-overlay" @click.self="close">
    <form class="req-dialog" aria-label="システム管理者へのリクエスト" @submit.prevent="submit" @paste="onPaste">
      <header>
        <strong>システム管理者へリクエスト</strong>
        <button type="button" title="閉じる" :disabled="sending" @click="close">×</button>
      </header>
      <div class="row">
        <label>種別</label>
        <select v-model="requestType" :disabled="sending">
          <option v-for="(label, key) in typeOptions" :key="key" :value="key">{{ label }}</option>
        </select>
      </div>
      <div class="row">
        <label>件名</label>
        <input v-model="subject" type="text" maxlength="100" :disabled="sending" />
      </div>
      <div class="row top">
        <label>内容</label>
        <textarea v-model="body" rows="7" maxlength="5000" placeholder="スクリーンショットは Ctrl+V で貼り付けできます" :disabled="sending"></textarea>
      </div>
      <div class="row top">
        <label>添付</label>
        <div class="files">
          <div v-if="attachments.length" class="thumbs">
            <div v-for="(item, i) in attachments" :key="item.id" class="thumb" :class="{ doc: !item.url }">
              <img v-if="item.url" :src="item.url" alt="添付画像" />
              <span v-else class="doc-name" :title="item.file.name">{{ item.file.name }}<small>{{ sizeLabel(item.file.size) }}</small></span>
              <button type="button" title="外す" :disabled="sending" @click="removeAttachment(i)">×</button>
            </div>
          </div>
          <button type="button" class="add" :disabled="sending || attachments.length >= MAX_FILES" @click="fileInput?.click()">ファイルを選択</button>
          <span class="count">{{ attachments.length }}/{{ MAX_FILES }}個（1ファイル{{ MAX_MB }}MB・合計{{ MAX_TOTAL_MB }}MBまで）</span>
          <span class="hint">画像・Excel・Word・PDF・CSV・テキスト</span>
          <input ref="fileInput" type="file" :accept="ACCEPT" multiple hidden @change="onFiles" />
        </div>
      </div>
      <p v-if="errorMessage" class="msg error">{{ errorMessage }}</p>
      <p v-if="successMessage" class="msg ok">{{ successMessage }}</p>
      <footer>
        <button type="submit" class="primary" :disabled="sending || !canSubmit">{{ sending ? '送信中...' : '送信' }}</button>
        <button type="button" :disabled="sending" @click="close">閉じる</button>
      </footer>
    </form>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'
import { requestDialogOpen, closeRequestDialog } from '@/composables/requestDialog'

const MAX_FILES = 5
const MAX_MB = 10
const MAX_TOTAL_MB = 20
const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp']
const DOCUMENT_EXTENSIONS = ['xlsx', 'xlsm', 'xls', 'docx', 'doc', 'pdf', 'csv', 'txt']
const ACCEPT = [...IMAGE_EXTENSIONS, ...DOCUMENT_EXTENSIONS].map((ext) => `.${ext}`).join(',')
const typeOptions = { request: '要望', bug: '不具合', question: '問い合わせ', other: 'その他' }

const route = useRoute()
const requestType = ref('request')
const subject = ref('')
const body = ref('')
// { id, file, url }  url は画像のサムネイル用（書類は空）
const attachments = ref([])
const fileInput = ref(null)
const sending = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
let nextId = 1

const canSubmit = computed(() => subject.value.trim() && body.value.trim())

const extensionOf = (name) => (String(name || '').split('.').pop() || '').toLowerCase()
const sizeLabel = (bytes) => (bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)}MB` : `${Math.max(1, Math.round(bytes / 1024))}KB`)

const revokeAll = () => {
  attachments.value.forEach((item) => item.url && URL.revokeObjectURL(item.url))
  attachments.value = []
}

const reset = () => {
  requestType.value = 'request'
  subject.value = ''
  body.value = ''
  errorMessage.value = ''
  revokeAll()
}

const addFiles = (files) => {
  errorMessage.value = ''
  for (const file of files) {
    const ext = extensionOf(file.name)
    const isImage = IMAGE_EXTENSIONS.includes(ext)
    if (!isImage && !DOCUMENT_EXTENSIONS.includes(ext)) {
      errorMessage.value = `${file.name}: 対応していない形式です（画像・Excel・Word・PDF・CSV・テキストのみ）。`
      continue
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      errorMessage.value = `${file.name}: 1ファイル${MAX_MB}MBまでです。`
      continue
    }
    if (attachments.value.length >= MAX_FILES) {
      errorMessage.value = `添付は最大${MAX_FILES}個までです。`
      break
    }
    const total = attachments.value.reduce((sum, item) => sum + item.file.size, 0) + file.size
    if (total > MAX_TOTAL_MB * 1024 * 1024) {
      errorMessage.value = `添付の合計は${MAX_TOTAL_MB}MBまでです。`
      continue
    }
    attachments.value.push({ id: nextId++, file, url: isImage ? URL.createObjectURL(file) : '' })
  }
}

const onFiles = (event) => {
  addFiles(Array.from(event.target.files || []))
  event.target.value = ''
}

// クリップボードの画像（スクリーンショット）を貼り付け。貼り付け画像は名前がないため、連番の名前を付ける。
const onPaste = (event) => {
  const files = Array.from(event.clipboardData?.items || [])
    .filter((item) => item.kind === 'file' && item.type.startsWith('image/'))
    .map((item) => item.getAsFile())
    .filter(Boolean)
    .map((file, index) => {
      const ext = (file.type.split('/')[1] || 'png').replace('jpeg', 'jpg')
      return new File([file], `screenshot${nextId + index}.${ext}`, { type: file.type })
    })
  if (!files.length) return
  event.preventDefault()
  addFiles(files)
}

const removeAttachment = (index) => {
  const [removed] = attachments.value.splice(index, 1)
  if (removed?.url) URL.revokeObjectURL(removed.url)
}

const close = () => {
  if (sending.value) return
  closeRequestDialog()
}

const submit = async () => {
  if (!canSubmit.value || sending.value) return
  sending.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const formData = new FormData()
    formData.append('request_type', requestType.value)
    formData.append('subject', subject.value.trim())
    formData.append('body', body.value.trim())
    formData.append('page_url', `${window.location.origin}${route.fullPath}`)
    attachments.value.forEach((item) => formData.append('files', item.file, item.file.name))
    const { data } = await api.userRequests.send(formData)
    reset()
    successMessage.value = data?.detail || '送信しました。'
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || '送信に失敗しました。'
  } finally {
    sending.value = false
  }
}

watch(requestDialogOpen, (open) => {
  if (open) {
    errorMessage.value = ''
    successMessage.value = ''
  }
})

onBeforeUnmount(revokeAll)
</script>

<style scoped>
.req-overlay{position:fixed;inset:0;z-index:1200;background:rgba(0,0,0,.35);display:grid;place-items:center;padding:12px}
.req-dialog{width:min(560px,100%);max-height:100%;overflow:auto;background:#fff;border-radius:8px;box-shadow:0 10px 30px rgba(0,0,0,.25);padding:10px 12px;display:flex;flex-direction:column;gap:6px;font-size:13px}
header,footer{display:flex;align-items:center;gap:8px}
header{justify-content:space-between}
header button{border:0;background:none;font-size:18px;cursor:pointer}
.row{display:flex;gap:8px;align-items:center}
.row.top{align-items:flex-start}
.row>label{flex:0 0 40px;font-weight:600}
.row input[type=text],.row select,.row textarea{flex:1;min-width:0;padding:4px 6px;border:1px solid #c8ccd0;border-radius:4px;font:inherit}
.row textarea{resize:vertical}
.files{flex:1;display:flex;flex-wrap:wrap;align-items:center;gap:6px}
.thumbs{display:flex;flex-wrap:wrap;gap:6px;width:100%}
.thumb{position:relative}
.thumb img{height:56px;border:1px solid #c8ccd0;border-radius:4px;display:block}
.thumb.doc .doc-name{display:flex;flex-direction:column;justify-content:center;max-width:150px;height:56px;padding:0 8px;border:1px solid #c8ccd0;border-radius:4px;background:#f5f6f7;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.thumb.doc .doc-name small{color:#666;font-size:11px}
.thumb button{position:absolute;top:-6px;right:-6px;width:18px;height:18px;border:0;border-radius:50%;background:#444;color:#fff;font-size:12px;line-height:1;cursor:pointer}
.add,footer button{padding:4px 12px;border:1px solid #c8ccd0;border-radius:4px;background:#f5f6f7;cursor:pointer}
footer .primary{background:#087b6e;color:#fff;border-color:#087b6e}
footer button:disabled,.add:disabled{opacity:.5;cursor:default}
.count,.hint{color:#666;font-size:12px}
.hint{width:100%}
.msg{margin:0;font-weight:600}
.msg.error{color:#c0392b}
.msg.ok{color:#087b6e}
</style>
