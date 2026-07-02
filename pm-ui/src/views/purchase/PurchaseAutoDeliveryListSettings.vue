<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">自動納入リスト送信</h1>
      <div class="page-actions">
        <button class="btn-primary" @click="openNew">新規追加</button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="loading" class="no-data">読み込み中...</div>

      <table v-else-if="configs.length" class="data-table">
        <thead>
          <tr>
            <th>仕入先</th>
            <th>実行時刻</th>
            <th>納入日</th>
            <th>有効</th>
            <th>CC送信先</th>
            <th>最終実行</th>
            <th>ステータス</th>
            <th>メッセージ</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in configs" :key="c.id">
            <td>{{ c.supplier_code }} {{ c.supplier_name }}</td>
            <td>{{ String(c.scheduled_hour).padStart(2, '0') }}:{{ String(c.scheduled_minute).padStart(2, '0') }}</td>
            <td>{{ c.lead_time_days }}営業日後</td>
            <td><span :class="['badge', c.is_enabled ? 'badge-on' : 'badge-off']">{{ c.is_enabled ? '有効' : '無効' }}</span></td>
            <td class="td-cc">{{ formatCcEmails(c.cc_emails) }}</td>
            <td>{{ c.last_run_at || '-' }}</td>
            <td><span v-if="c.last_run_status" :class="['badge', `badge-${c.last_run_status.toLowerCase()}`]">{{ c.last_run_status }}</span></td>
            <td class="td-msg">{{ c.last_run_message || '' }}</td>
            <td class="td-actions">
              <button class="btn-sm" @click="openEdit(c)">編集</button>
              <button class="btn-sm btn-run" :disabled="running.has(c.id)" @click="runNow(c)">{{ running.has(c.id) ? '実行中...' : '今すぐ実行' }}</button>
              <button class="btn-sm btn-danger" @click="remove(c)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="no-data">自動送信設定がありません。「新規追加」から設定してください。</div>
    </div>

    <!-- 編集モーダル -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <h2 class="modal-title">{{ isEdit ? '設定編集' : '新規設定' }}</h2>

        <div class="form-group">
          <label>仕入先 <span class="required">*</span></label>
          <select v-model="form.supplier_id" :disabled="isEdit">
            <option value="">-- 選択 --</option>
            <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.supplier_code }} {{ s.supplier_name }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>実行時刻 <span class="required">*</span></label>
          <div class="time-row">
            <input type="number" min="0" max="23" v-model.number="form.scheduled_hour" class="time-input" required />
            <span class="suffix">時</span>
            <input type="number" min="0" max="59" v-model.number="form.scheduled_minute" class="time-input" required />
            <span class="suffix">分</span>
          </div>
        </div>

        <div class="form-group">
          <label>納入日（実行日から何営業日後） <span class="required">*</span></label>
          <div class="time-row">
            <input type="number" min="1" max="30" v-model.number="form.lead_time_days" class="time-input" required />
            <span class="suffix">営業日後</span>
          </div>
        </div>

        <div class="form-group">
          <label>進度表期間 <span class="required">*</span></label>
          <div class="time-row">
            <input type="number" min="1" max="90" v-model.number="form.progress_days_back" class="time-input" required />
            <span class="suffix">営業日前 ～</span>
            <input type="number" min="1" max="120" v-model.number="form.progress_days_forward" class="time-input" required />
            <span class="suffix">日後</span>
          </div>
        </div>

        <div class="form-group">
          <label class="checkbox-label"><input type="checkbox" v-model="form.is_enabled" /> 有効</label>
        </div>

        <div class="form-group">
          <label>送信ファイル選択</label>
          <div class="file-toggle-grid">
            <label class="checkbox-label"><input type="checkbox" v-model="form.send_delivery_list_excel" /> 納品リスト Excel</label>
            <label class="checkbox-label"><input type="checkbox" v-model="form.send_progress_excel" /> 進度表 Excel</label>
            <label class="checkbox-label"><input type="checkbox" v-model="form.send_progress_pdf" /> 進度表 PDF</label>
            <label class="checkbox-label"><input type="checkbox" v-model="form.send_delivery_note_pdf" /> 外作納品書 PDF</label>
          </div>
        </div>

        <div class="form-group">
          <label>返信先メールアドレス（Reply-To） <span class="required">*</span></label>
          <input type="email" v-model="form.reply_to_email" class="input-full" placeholder="reply@example.com" required />
        </div>

        <div class="form-group">
          <label>業務員CC送信先メール（改行区切り、後追加可能） <span class="required">*</span></label>
          <textarea v-model="form.cc_emails" rows="3" class="input-full" placeholder="user1@example.com&#10;user2@example.com" required></textarea>
        </div>

        <div class="form-group">
          <label>失敗時の通知先 <span class="required">*</span></label>
          <UserChipSelect :userList="userList" v-model="form.notify_on_failure_user_ids" />
        </div>

        <div class="form-group">
          <label>納入日でないときの通知先 <span class="required">*</span></label>
          <UserChipSelect :userList="userList" v-model="form.notify_on_non_delivery_user_ids" />
        </div>

        <div class="form-actions">
          <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? '保存中...' : '保存' }}</button>
          <button class="btn-secondary" @click="closeModal">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'
import UserChipSelect from './UserChipSelect.vue'

const loading = ref(true)
const saving = ref(false)
const configs = ref([])
const suppliers = ref([])
const userList = ref([])
const showModal = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const running = reactive(new Set())

const form = reactive({
  supplier_id: '',
  is_enabled: true,
  scheduled_hour: 7,
  scheduled_minute: 0,
  lead_time_days: 2,
  progress_days_back: 7,
  progress_days_forward: 30,
  send_delivery_list_excel: true,
  send_progress_excel: true,
  send_progress_pdf: true,
  send_delivery_note_pdf: true,
  reply_to_email: '',
  cc_emails: '',
  notify_on_failure_user_ids: [],
  notify_on_non_delivery_user_ids: [],
})

const formatCcEmails = (text) => {
  if (!text) return '-'
  const list = text.split('\n').map(e => e.trim()).filter(Boolean)
  return list.length ? list.join(', ') : '-'
}

const loadConfigs = async () => {
  loading.value = true
  try {
    const res = await api.purchaseAutoDeliveryList.getConfigs()
    configs.value = res.data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const loadSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = (res.data.results || res.data || []).sort((a, b) =>
    (a.supplier_code || '').localeCompare(b.supplier_code || '')
  )
}

const loadUsers = async () => {
  const res = await api.accounts.getUsers({ is_active: true, page_size: 9999 })
  userList.value = res.data?.results || res.data || []
}

const resetForm = () => {
  form.supplier_id = ''
  form.is_enabled = true
  form.scheduled_hour = 7
  form.scheduled_minute = 0
  form.lead_time_days = 2
  form.progress_days_back = 7
  form.progress_days_forward = 30
  form.send_delivery_list_excel = true
  form.send_progress_excel = true
  form.send_progress_pdf = true
  form.send_delivery_note_pdf = true
  form.reply_to_email = ''
  form.cc_emails = ''
  form.notify_on_failure_user_ids = []
  form.notify_on_non_delivery_user_ids = []
}

const openNew = () => {
  resetForm()
  isEdit.value = false
  editId.value = null
  showModal.value = true
}

const openEdit = (c) => {
  isEdit.value = true
  editId.value = c.id
  form.supplier_id = c.supplier_id
  form.is_enabled = c.is_enabled
  form.scheduled_hour = c.scheduled_hour
  form.scheduled_minute = c.scheduled_minute
  form.lead_time_days = c.lead_time_days ?? 2
  form.progress_days_back = c.progress_days_back ?? 7
  form.progress_days_forward = c.progress_days_forward ?? 30
  form.send_delivery_list_excel = c.send_delivery_list_excel ?? true
  form.send_progress_excel = c.send_progress_excel ?? true
  form.send_progress_pdf = c.send_progress_pdf ?? true
  form.send_delivery_note_pdf = c.send_delivery_note_pdf ?? true
  form.reply_to_email = c.reply_to_email || ''
  form.cc_emails = c.cc_emails || ''
  form.notify_on_failure_user_ids = [...(c.notify_on_failure_user_ids || [])]
  form.notify_on_non_delivery_user_ids = [...(c.notify_on_non_delivery_user_ids || [])]
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}

const save = async () => {
  const errors = []
  if (!form.supplier_id) errors.push('仕入先')
  if (form.scheduled_hour === null || form.scheduled_hour === '') errors.push('実行時刻（時）')
  if (form.scheduled_minute === null || form.scheduled_minute === '') errors.push('実行時刻（分）')
  if (!form.lead_time_days) errors.push('納入日（営業日後）')
  if (!form.progress_days_back) errors.push('進度表（営業日前）')
  if (!form.progress_days_forward) errors.push('進度表（日後）')
  if (!form.reply_to_email?.trim()) errors.push('返信先メールアドレス')
  if (!form.cc_emails?.trim()) errors.push('業務員CC送信先メール')
  if (!form.notify_on_failure_user_ids.length) errors.push('失敗時の通知先')
  if (!form.notify_on_non_delivery_user_ids.length) errors.push('納入日でないときの通知先')
  if (errors.length) {
    alert(`以下の項目は必須です:\n${errors.join('\n')}`)
    return
  }
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const badEmails = []
  if (form.reply_to_email && !emailRe.test(form.reply_to_email.trim())) {
    badEmails.push(`返信先: ${form.reply_to_email.trim()}`)
  }
  for (const line of (form.cc_emails || '').split('\n')) {
    const addr = line.trim()
    if (addr && !emailRe.test(addr)) badEmails.push(`CC: ${addr}`)
  }
  if (badEmails.length) {
    alert(`メールアドレスの形式が不正です:\n${badEmails.join('\n')}`)
    return
  }
  saving.value = true
  try {
    const payload = {
      supplier_id: form.supplier_id,
      is_enabled: form.is_enabled,
      scheduled_hour: form.scheduled_hour,
      scheduled_minute: form.scheduled_minute,
      lead_time_days: form.lead_time_days,
      progress_days_back: form.progress_days_back,
      progress_days_forward: form.progress_days_forward,
      send_delivery_list_excel: form.send_delivery_list_excel,
      send_progress_excel: form.send_progress_excel,
      send_progress_pdf: form.send_progress_pdf,
      send_delivery_note_pdf: form.send_delivery_note_pdf,
      reply_to_email: form.reply_to_email,
      cc_emails: form.cc_emails,
      notify_on_failure_user_ids: form.notify_on_failure_user_ids,
      notify_on_non_delivery_user_ids: form.notify_on_non_delivery_user_ids,
    }
    if (isEdit.value) {
      await api.purchaseAutoDeliveryList.updateConfig(editId.value, payload)
    } else {
      await api.purchaseAutoDeliveryList.createConfig(payload)
    }
    closeModal()
    await loadConfigs()
  } catch (e) {
    const detail = e?.response?.data?.detail
    alert(`保存に失敗しました。${detail ? `\n${detail}` : ''}`)
  } finally {
    saving.value = false
  }
}

const remove = async (c) => {
  if (!confirm(`${c.supplier_code} ${c.supplier_name} の設定を削除しますか？`)) return
  try {
    await api.purchaseAutoDeliveryList.deleteConfig(c.id)
    await loadConfigs()
  } catch (e) {
    alert('削除に失敗しました。')
  }
}

const runNow = async (c) => {
  if (!confirm(`${c.supplier_code} ${c.supplier_name} の自動送信を今すぐ実行しますか？`)) return
  running.add(c.id)
  try {
    await api.purchaseAutoDeliveryList.runNow(c.id)
    const pollStart = Date.now()
    const timer = setInterval(async () => {
      if (Date.now() - pollStart > 5 * 60 * 1000) {
        clearInterval(timer)
        running.delete(c.id)
        alert('5分経過しても完了しませんでした。')
        return
      }
      await loadConfigs()
      const updated = configs.value.find(x => x.id === c.id)
      if (updated && updated.last_run_status !== 'RUNNING') {
        clearInterval(timer)
        running.delete(c.id)
        alert(`完了: ${updated.last_run_status}\n${updated.last_run_message || ''}`)
      }
    }, 3000)
  } catch (e) {
    running.delete(c.id)
    alert('実行に失敗しました。')
  }
}

onMounted(async () => {
  await Promise.all([loadConfigs(), loadSuppliers(), loadUsers()])
})
</script>

<style scoped>
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 6px 8px; border-bottom: 2px solid #e5e9ef; font-weight: 700; color: #374151; background: #f8fafc; white-space: nowrap; }
.data-table td { padding: 8px; border-bottom: 1px solid #e5e9ef; }
.td-cc { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-msg { max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #64748b; }
.td-actions { white-space: nowrap; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-on { background: #dcfce7; color: #166534; }
.badge-off { background: #f1f5f9; color: #64748b; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-failed { background: #fee2e2; color: #991b1b; }
.badge-running { background: #dbeafe; color: #1e40af; }
.badge-skipped { background: #fef3c7; color: #92400e; }
.btn-sm { padding: 3px 10px; font-size: 12px; border: 1px solid #d1d5db; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-sm:hover { background: #f1f5f9; }
.btn-run { border-color: #3b82f6; color: #2563eb; }
.btn-run:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger { border-color: #fca5a5; color: #dc2626; }
.btn-danger:hover { background: #fef2f2; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 9999; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 8px; padding: 24px; width: 520px; max-height: 85vh; overflow-y: auto; box-shadow: 0 4px 24px rgba(0,0,0,0.2); }
.modal-title { margin: 0 0 16px; font-size: 16px; }
.form-group { margin-bottom: 14px; }
.form-group > label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 4px; }
.form-group select, .input-full { width: 100%; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; }
.time-row { display: flex; align-items: center; gap: 4px; }
.time-input { width: 60px; text-align: center; padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; }
.suffix { font-size: 13px; color: #475569; }
.checkbox-label { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.file-toggle-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px; }
.required { color: #dc2626; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.btn-primary { padding: 6px 16px; background: #2563eb; color: #fff; border: none; border-radius: 4px; font-weight: 600; cursor: pointer; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { padding: 6px 16px; background: #fff; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }
</style>
