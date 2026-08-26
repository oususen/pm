<template>
  <div class="page-container">
    <h2 class="page-title">FB受注取込 <DataSourceDialog title="FB受注取込" :sources="dsSources" /></h2>

    <div class="import-section">
      <div class="file-input-row">
        <label class="file-label">
          CSV/XLSXファイル選択
          <input type="file" accept=".csv,.xlsx,.xls" @change="onFileSelect" ref="fileInput" />
        </label>
        <select v-if="isCsvFile" v-model="encoding" class="encoding-select">
          <option value="utf-8">UTF-8</option>
          <option value="shift_jis">Shift_JIS</option>
        </select>
        <button class="btn-primary" :disabled="!file || importing" @click="doImport">
          {{ importing ? '取込中...' : '取込実行' }}
        </button>
      </div>

      <div v-if="result" class="result-section">
        <h3>取込結果</h3>
        <div class="result-summary">
          <span class="badge badge-success">作成: {{ result.created_count }}件</span>
          <span class="badge badge-warning">スキップ: {{ result.skipped_count }}件</span>
          <span class="badge badge-error">エラー: {{ result.error_count }}件</span>
        </div>

        <div v-if="result.first_article_candidates?.length" class="candidate-list">
          <h4>お久しぶり製品候補</h4>
          <div class="candidate-summary">
            {{ result.first_article_candidates.length }}件あります。初物検査連絡が必要な場合は送信してください。
          </div>
          <div v-for="(item, i) in result.first_article_candidates" :key="`candidate-${i}`" class="candidate-item">
            品番: {{ item.product_number }} / 品名: {{ item.item_name }} / 塗装日: {{ item.painting_date }} / 数量: {{ item.order_qty }} / 案件番号: {{ item.case_no }}
          </div>
        </div>

        <div
          v-if="sendMessage"
          :class="[
            'notification-item',
            sendMessage.variant === 'success' ? 'success' : 'warning',
          ]"
        >
          {{ sendMessage.message }}
        </div>

        <div v-if="result.errors.length" class="error-list">
          <h4>エラー詳細</h4>
          <div v-for="(err, i) in result.errors" :key="i" class="error-item">
            行{{ err.row }}: {{ err.message }}
          </div>
        </div>

        <div v-if="result.skipped.length" class="skip-list">
          <h4>スキップ（登録済み）</h4>
          <div v-for="(s, i) in result.skipped" :key="i" class="skip-item">
            {{ s.case_no }}: {{ s.message }}
          </div>
        </div>
      </div>

      <div v-if="preview.length" class="preview-section">
        <h3>プレビュー（{{ preview.length }}件）</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>品目コード</th>
              <th>品目名称</th>
              <th>塗装名</th>
              <th>塗装日</th>
              <th>数量</th>
              <th>案件番号</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in preview" :key="i">
              <td>{{ row.item_code }}</td>
              <td>{{ row.item_name }}</td>
              <td>{{ row.painting_name }}</td>
              <td>{{ row.painting_date }}</td>
              <td class="text-right">{{ row.qty }}</td>
              <td class="case-no">{{ row.case_no }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="showFirstArticleDialog" class="modal-overlay" @click.self="closeFirstArticleDialog">
      <div class="modal-content email-modal">
        <h2>お久しぶり製品メール送信</h2>
        <p class="dialog-message">お久しぶり製品が {{ firstArticleCandidates.length }} 件あります。送信しますか。</p>

        <div v-if="contactLoading" class="email-loading">連絡先を読み込み中...</div>

        <div v-if="!contactLoading && firstArticleContacts.length === 0" class="email-warning">
          連絡先マスタに種別「FB初物検査」または「初物検査」が登録されていません。追加宛先を入力してください。
        </div>

        <div class="email-field">
          <label>送信先</label>
          <select v-model="firstArticleTo" class="email-select" multiple>
            <option v-for="contact in firstArticleContacts" :key="contact.id" :value="contact.email">
              {{ contact.display_name }} &lt;{{ contact.email }}&gt;
            </option>
          </select>
          <div class="email-hint">Ctrl/Command を押しながら複数選択できます。</div>
        </div>

        <div class="email-field">
          <label>送信先（追加）</label>
          <input
            v-model.trim="firstArticleToManual"
            type="text"
            placeholder="example1@example.com, example2@example.com"
          />
        </div>

        <div class="email-field">
          <label>件名</label>
          <input v-model="firstArticleSubject" type="text" />
        </div>

        <div class="email-field">
          <label>本文</label>
          <textarea v-model="firstArticleBody" rows="12"></textarea>
        </div>

        <div class="email-field">
          <label>対象一覧</label>
          <div class="candidate-item" v-for="(item, i) in firstArticleCandidates" :key="`dialog-candidate-${i}`">
            品番: {{ item.product_number }} / 品名: {{ item.item_name }} / 塗装日: {{ item.painting_date }} / 数量: {{ item.order_qty }} / 案件番号: {{ item.case_no }}
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-primary email-send-btn" :disabled="sendingFirstArticleEmail" @click="sendFirstArticleNotice">
            {{ sendingFirstArticleEmail ? '送信中...' : '送信' }}
          </button>
          <button class="btn-secondary" :disabled="sendingFirstArticleEmail" @click="closeFirstArticleDialog">
            キャンセル
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_outsource_order / t_outsource_order_line', desc: 'CSV/XLSX取込による受注データ作成' },
]

const file = ref(null)
const encoding = ref('utf-8')
const importing = ref(false)
const preview = ref([])
const result = ref(null)
const fileInput = ref(null)
const isCsvFile = ref(true)
const showFirstArticleDialog = ref(false)
const sendingFirstArticleEmail = ref(false)
const contactLoading = ref(false)
const firstArticleCandidates = ref([])
const firstArticleContacts = ref([])
const firstArticleTo = ref([])
const firstArticleToManual = ref('')
const firstArticleSubject = ref('')
const firstArticleBody = ref('')
const sendMessage = ref(null)
const lookbackDays = ref(90)

function onFileSelect(e) {
  const f = e.target.files[0]
  if (!f) return
  file.value = f
  isCsvFile.value = !/\.(xlsx|xls)$/i.test(f.name || '')
  result.value = null
  parsePreview(f)
}

function parsePreview(f) {
  if (/\.(xlsx|xls)$/i.test(f.name || '')) {
    parseExcelPreview(f)
    return
  }
  parseCsvPreview(f)
}

function parseCsvPreview(f) {
  const parseCsvLine = (line) => {
    const cols = []
    let cur = ''
    let inQuotes = false
    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i]
      if (ch === '"') {
        if (inQuotes && line[i + 1] === '"') {
          cur += '"'
          i += 1
        } else {
          inQuotes = !inQuotes
        }
      } else if (ch === ',' && !inQuotes) {
        cols.push(cur.trim())
        cur = ''
      } else {
        cur += ch
      }
    }
    cols.push(cur.trim())
    return cols
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target.result
    const lines = text.split(/\r?\n/).filter(l => l.trim())
    if (lines.length < 2) return

    preview.value = lines.slice(1).map(line => {
      const cols = parseCsvLine(line)
      const item_code = cols[0]?.trim() || ''
      const painting_date = cols[3]?.trim() || ''
      const datePart = painting_date.replace(/\//g, '')
      return {
        item_code,
        item_name: cols[1]?.trim() || '',
        painting_name: cols[2]?.trim() || '',
        painting_date,
        qty: cols[4]?.trim() || '',
        case_no: `${datePart}-${item_code}`,
      }
    })
  }
  reader.readAsText(f, encoding.value === 'shift_jis' ? 'Shift_JIS' : 'UTF-8')
}

function parseExcelPreview(f) {
  const reader = new FileReader()
  reader.onload = (e) => {
    const workbook = XLSX.read(e.target.result, { type: 'array' })
    const sheet = workbook.Sheets[workbook.SheetNames[0]]
    const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false })
    let lastDenpyoKubun = ''
    let lastDenpyoType = ''

    preview.value = rows.slice(1).filter(cols => cols?.length).map((cols) => {
      const denpyoKubun = String(cols[0] || '').trim() || lastDenpyoKubun
      const denpyoType = String(cols[1] || '').trim() || lastDenpyoType
      if (denpyoKubun) lastDenpyoKubun = denpyoKubun
      if (denpyoType) lastDenpyoType = denpyoType

      const item_code = String(cols[2] || '').trim()
      const painting_date = normalizeExcelDate(cols[5])
      const datePart = painting_date.replace(/\D/g, '')
      const painting_name = [denpyoType, denpyoKubun].filter(Boolean).join(' / ')

      return {
        item_code,
        item_name: String(cols[3] || '').trim(),
        painting_name,
        painting_date,
        qty: String(cols[4] || '').trim(),
        case_no: item_code && datePart ? `${datePart}-${item_code}` : '',
      }
    }).filter(row => row.item_code || row.item_name || row.qty)
  }
  reader.readAsArrayBuffer(f)
}

function normalizeExcelDate(value) {
  const text = String(value || '').trim()
  if (/^\d{8}$/.test(text)) {
    return `${text.slice(0, 4)}/${Number(text.slice(4, 6))}/${Number(text.slice(6, 8))}`
  }
  return text
}

async function doImport() {
  if (!file.value) return
  importing.value = true
  result.value = null
  sendMessage.value = null

  try {
    const formData = new FormData()
    formData.append('file', file.value)
    formData.append('encoding', encoding.value)

    const res = await api.outsource.importCSV(formData)
    result.value = res.data
    if (res.data?.lookback_days) lookbackDays.value = res.data.lookback_days
    const emailEnabled = res.data?.email_enabled !== false
    const candidates = Array.isArray(res.data?.first_article_candidates) ? res.data.first_article_candidates : []
    if (candidates.length && emailEnabled) {
      await openFirstArticleDialog(candidates)
    } else if (candidates.length) {
      sendMessage.value = {
        variant: 'warning',
        message: 'お久しぶり製品候補がありますが、通知設定がOFFのためメール送信は停止しています。',
      }
    }
  } catch (err) {
    result.value = {
      created_count: 0,
      skipped_count: 0,
      error_count: 1,
      created: [],
      skipped: [],
      errors: [{ row: 0, message: err.response?.data?.error || err.message }],
      first_article_candidates: [],
    }
  } finally {
    importing.value = false
  }
}

function buildFirstArticleBody(items) {
  const days = lookbackDays.value
  const lines = [
    `FB外作受注取込で、${days}日以上受注のなかった品番が検出されました。`,
    '初物検査の要否を確認してください。',
    '',
    `判定条件: 塗装日から${days}日遡った期間に同一品番の受注がないこと`,
    '',
    '対象一覧:',
  ]
  items.forEach((item) => {
    lines.push(
      `- 品番: ${item.product_number} / 品名: ${item.item_name} / 塗装日: ${item.painting_date} / 数量: ${item.order_qty} / 案件番号: ${item.case_no}`
    )
  })
  const user = authState.user
  const name = user ? `${user.last_name || ''} ${user.first_name || ''}`.trim() || user.username : ''
  if (name) {
    lines.push('', `取込者: ${name}`)
  }
  lines.push('', '以上')
  return lines.join('\n')
}

function collectFirstArticleRecipients() {
  const recipients = []
  const seen = new Set()
  const addRecipient = (value) => {
    const email = String(value || '').trim()
    if (!email) return
    const key = email.toLowerCase()
    if (seen.has(key)) return
    seen.add(key)
    recipients.push(email)
  }

  firstArticleTo.value.forEach(addRecipient)
  if (firstArticleToManual.value) {
    firstArticleToManual.value.split(/[,;、\s]+/).forEach(addRecipient)
  }
  return recipients
}

async function openFirstArticleDialog(candidates) {
  firstArticleCandidates.value = candidates
  showFirstArticleDialog.value = true
  contactLoading.value = true
  sendMessage.value = null
  let settingUserEmails = []
  try {
    const res = await api.outsource.getFirstArticleContacts()
    firstArticleContacts.value = Array.isArray(res.data?.contacts) ? res.data.contacts : []
    settingUserEmails = Array.isArray(res.data?.setting_user_emails) ? res.data.setting_user_emails : []
    if (res.data?.lookback_days) lookbackDays.value = res.data.lookback_days
  } catch {
    firstArticleContacts.value = []
  } finally {
    contactLoading.value = false
  }

  firstArticleTo.value = firstArticleContacts.value.map((contact) => contact.email)
  const contactSet = new Set(firstArticleTo.value.map(e => e.toLowerCase()))
  const extraEmails = settingUserEmails.filter(e => !contactSet.has(e.toLowerCase()))
  firstArticleToManual.value = extraEmails.join(', ')
  firstArticleSubject.value = `【FB外作】初物検査対象のお久しぶり製品通知 ${new Date().toLocaleString('ja-JP', { hour12: false })}`
  firstArticleBody.value = buildFirstArticleBody(candidates)
}

function closeFirstArticleDialog() {
  showFirstArticleDialog.value = false
}

async function sendFirstArticleNotice() {
  const recipients = collectFirstArticleRecipients()
  if (!recipients.length) {
    alert('送信先を1件以上指定してください。')
    return
  }
  if (!firstArticleSubject.value.trim()) {
    alert('件名を入力してください。')
    return
  }
  if (!firstArticleBody.value.trim()) {
    alert('本文を入力してください。')
    return
  }

  sendingFirstArticleEmail.value = true
  try {
    const res = await api.outsource.sendFirstArticleNotice({
      to_emails: recipients,
      subject: firstArticleSubject.value,
      body: firstArticleBody.value,
      items: firstArticleCandidates.value,
    })
    sendMessage.value = {
      variant: 'success',
      message: res.data?.message || 'メールを送信しました。',
    }
    showFirstArticleDialog.value = false
  } catch (error) {
    const message = error?.response?.data?.detail || 'メール送信に失敗しました。'
    sendMessage.value = { success: false, message }
    alert(message)
  } finally {
    sendingFirstArticleEmail.value = false
  }
}
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { margin-bottom: 16px; font-size: 18px; }

.file-input-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.file-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.encoding-select {
  padding: 4px 8px;
  font-size: 13px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.btn-primary {
  padding: 6px 16px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  padding: 6px 16px;
  background: #fff;
  color: #333;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.preview-section, .result-section { margin-top: 16px; }
.preview-section h3, .result-section h3 { font-size: 14px; margin-bottom: 8px; }

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.data-table th, .data-table td {
  border: 1px solid #ddd;
  padding: 4px 8px;
  text-align: left;
}
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.case-no { font-family: monospace; font-size: 11px; color: #666; }

.result-summary {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}
.badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.badge-success { background: #e8f5e9; color: #2e7d32; }
.badge-warning { background: #fff3e0; color: #e65100; }
.badge-error { background: #fbe9e7; color: #c62828; }

.error-list, .skip-list { margin-top: 8px; }
.candidate-list { margin-top: 8px; }
.error-list h4, .skip-list h4, .candidate-list h4 { font-size: 13px; margin-bottom: 4px; }
.error-item { color: #c62828; font-size: 12px; padding: 2px 0; }
.skip-item { color: #e65100; font-size: 12px; padding: 2px 0; }
.candidate-summary {
  font-size: 12px;
  color: #333;
  margin-bottom: 4px;
}
.candidate-item {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  margin-bottom: 4px;
  background: #f5f5f5;
  color: #333;
}
.notification-item { font-size: 12px; padding: 4px 8px; border-radius: 4px; margin-bottom: 4px; }
.notification-item.success { color: #2e7d32; background: #e8f5e9; }
.notification-item.warning { color: #e65100; background: #fff3e0; }
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal-content {
  width: 420px;
  max-width: calc(100vw - 24px);
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.25);
  padding: 16px;
}
.modal-content h2 {
  margin: 0 0 10px;
  font-size: 16px;
}
.modal-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.dialog-message {
  margin: 0 0 12px;
  font-size: 13px;
  color: #333;
}
.email-modal {
  width: 720px;
  max-height: 90vh;
  overflow-y: auto;
}
.email-field {
  margin-bottom: 14px;
}
.email-field > label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 4px;
}
.email-field input[type="text"],
.email-field textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 8px;
  font-size: 14px;
  box-sizing: border-box;
}
.email-field textarea {
  resize: vertical;
}
.email-select {
  width: 100%;
  padding: 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 14px;
}
.email-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}
.email-loading {
  text-align: center;
  padding: 12px;
  color: #6b7280;
}
.email-warning {
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #92400e;
}
.email-send-btn {
  min-width: 100px;
}
</style>
