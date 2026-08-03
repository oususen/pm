<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">注文書自動送信設定</h1>
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
            <th>進度表期間</th>
            <th>数量方式</th>
            <th>有効</th>
            <th>最終実行</th>
            <th>ステータス</th>
            <th>メッセージ</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="config in configs" :key="config.id">
            <td>{{ config.supplier_code }} {{ config.supplier_name }}</td>
            <td>{{ String(config.scheduled_hour).padStart(2, '0') }}:{{ String(config.scheduled_minute).padStart(2, '0') }}</td>
            <td>{{ config.lead_time_days }}営業日後</td>
            <td>{{ config.progress_days_back }}営業日前 ～ {{ config.progress_days_forward }}日後</td>
            <td>{{ calcModeLabel(config.calc_mode) }}</td>
            <td><span :class="['badge', config.is_enabled ? 'badge-on' : 'badge-off']">{{ config.is_enabled ? '有効' : '無効' }}</span></td>
            <td>{{ config.last_run_at || '-' }}</td>
            <td><span v-if="config.last_run_status" :class="['badge', `badge-${config.last_run_status.toLowerCase()}`]">{{ config.last_run_status }}</span></td>
            <td class="td-msg">{{ config.last_run_message || '' }}</td>
            <td class="td-actions">
              <button class="btn-sm" @click="openEdit(config)">編集</button>
              <button class="btn-sm btn-run" :disabled="running.has(config.id)" @click="runNow(config)">{{ running.has(config.id) ? '実行中...' : '今すぐ実行' }}</button>
              <button class="btn-sm btn-danger" @click="remove(config)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="no-data">注文書自動送信設定がありません。</div>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <h2 class="modal-title">{{ isEdit ? '設定編集' : '新規設定' }}</h2>

        <div class="form-group">
          <label>仕入先 <span class="required">*</span></label>
          <select v-model="form.supplier_id" :disabled="isEdit">
            <option value="">-- 選択 --</option>
            <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">{{ supplier.supplier_code }} {{ supplier.supplier_name }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>実行時刻 <span class="required">*</span></label>
          <div class="time-row">
            <input v-model.number="form.scheduled_hour" type="number" min="0" max="23" class="time-input" />
            <span class="suffix">時</span>
            <input v-model.number="form.scheduled_minute" type="number" min="0" max="59" class="time-input" />
            <span class="suffix">分</span>
          </div>
        </div>

        <div class="form-group">
          <label>納入日（実行日から何営業日後） <span class="required">*</span></label>
          <div class="time-row">
            <input v-model.number="form.lead_time_days" type="number" min="1" max="30" class="time-input" />
            <span class="suffix">営業日後</span>
          </div>
        </div>

        <div class="form-group">
          <label>進度表期間 <span class="required">*</span></label>
          <div class="time-row">
            <input v-model.number="form.progress_days_back" type="number" min="1" max="90" class="time-input" />
            <span class="suffix">営業日前 ～</span>
            <input v-model.number="form.progress_days_forward" type="number" min="1" max="120" class="time-input" />
            <span class="suffix">日後（発行日基準）</span>
          </div>
        </div>

        <div class="form-group">
          <label>数量算出方式 <span class="required">*</span></label>
          <select v-model="form.calc_mode">
            <option value="DEMAND">需要そのまま</option>
            <option value="LOT_ROUNDED">ロット丸め</option>
          </select>
        </div>

        <div class="form-group">
          <label class="checkbox-label"><input v-model="form.is_enabled" type="checkbox" /> 有効</label>
        </div>

        <div class="form-group">
          <label class="checkbox-label"><input v-model="form.send_order_excel" type="checkbox" /> 注文書Excel送信</label>
        </div>

        <div class="form-group">
          <div class="label-row">
            <label>メール本文（空欄なら自動生成）</label>
          </div>
          <textarea v-model="form.email_body_custom" rows="8" class="input-full" />
        </div>

        <div class="form-group">
          <label>返信先メールアドレス <span class="required">*</span></label>
          <ContactEmailSelect
            v-model="form.reply_to_email"
            :contacts="contactList"
            :supplier-keywords="selectedSupplierKeywords"
            placeholder="連絡先マスタから返信先を検索して追加"
          />
        </div>

        <div class="form-group">
          <label>業務員CC送信先メール <span class="required">*</span></label>
          <ContactEmailSelect
            v-model="ccEmailList"
            :contacts="contactList"
            :supplier-keywords="selectedSupplierKeywords"
            multiple
            placeholder="連絡先マスタからCC送信先を検索して追加"
          />
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
import ContactEmailSelect from './ContactEmailSelect.vue'

const loading = ref(true)
const saving = ref(false)
const configs = ref([])
const suppliers = ref([])
const userList = ref([])
const contactList = ref([])
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
  calc_mode: 'DEMAND',
  send_order_excel: true,
  email_body_custom: '',
  reply_to_email: '',
  cc_emails: '',
  notify_on_failure_user_ids: [],
  notify_on_non_delivery_user_ids: [],
})

const splitEmailLines = (text) => {
  return String(text || '')
    .split('\n')
    .map((email) => email.trim())
    .filter(Boolean)
}

const ccEmailList = computed({
  get: () => splitEmailLines(form.cc_emails),
  set: (emails) => {
    form.cc_emails = (emails || []).join('\n')
  },
})

const selectedSupplier = computed(() => suppliers.value.find((supplier) => String(supplier.id) === String(form.supplier_id)) || null)
const selectedSupplierKeywords = computed(() => {
  if (!selectedSupplier.value) return []
  return [selectedSupplier.value.supplier_code, selectedSupplier.value.supplier_name]
})

const calcModeLabel = (mode) => {
  if (mode === 'LOT_ROUNDED') return 'ロット丸め'
  return '需要そのまま'
}

const loadConfigs = async () => {
  loading.value = true
  try {
    const res = await api.purchaseAutoOrderSend.getConfigs()
    configs.value = res.data || []
  } finally {
    loading.value = false
  }
}

const loadSuppliers = async () => {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = (res.data.results || res.data || []).sort((a, b) => (a.supplier_code || '').localeCompare(b.supplier_code || ''))
}

const loadUsers = async () => {
  const res = await api.accounts.getUsers({ is_active: true, page_size: 9999 })
  userList.value = res.data?.results || res.data || []
}

const loadContacts = async () => {
  const res = await api.contacts.getContacts({ is_active: true, page_size: 9999 })
  contactList.value = (res.data?.results || res.data || []).filter((contact) => contact.email)
}

const resetForm = () => {
  form.supplier_id = ''
  form.is_enabled = true
  form.scheduled_hour = 7
  form.scheduled_minute = 0
  form.lead_time_days = 2
  form.progress_days_back = 7
  form.progress_days_forward = 30
  form.calc_mode = 'DEMAND'
  form.send_order_excel = true
  form.email_body_custom = ''
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

const openEdit = (config) => {
  isEdit.value = true
  editId.value = config.id
  form.supplier_id = config.supplier_id
  form.is_enabled = config.is_enabled
  form.scheduled_hour = config.scheduled_hour
  form.scheduled_minute = config.scheduled_minute
  form.lead_time_days = config.lead_time_days
  form.progress_days_back = config.progress_days_back ?? 7
  form.progress_days_forward = config.progress_days_forward ?? 30
  form.calc_mode = config.calc_mode
  form.send_order_excel = config.send_order_excel
  form.email_body_custom = config.email_body_custom || ''
  form.reply_to_email = config.reply_to_email || ''
  form.cc_emails = config.cc_emails || ''
  form.notify_on_failure_user_ids = [...(config.notify_on_failure_user_ids || [])]
  form.notify_on_non_delivery_user_ids = [...(config.notify_on_non_delivery_user_ids || [])]
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
}

const validate = () => {
  const errors = []
  if (!form.supplier_id) errors.push('仕入先')
  if (!form.lead_time_days) errors.push('納入日（営業日後）')
  if (!form.progress_days_back) errors.push('進度表（営業日前）')
  if (!form.progress_days_forward) errors.push('進度表（日後・発行日基準）')
  if (!form.reply_to_email?.trim()) errors.push('返信先メールアドレス')
  if (!form.cc_emails?.trim()) errors.push('業務員CC送信先メール')
  if (!form.notify_on_failure_user_ids.length) errors.push('失敗時の通知先')
  if (!form.notify_on_non_delivery_user_ids.length) errors.push('納入日でないときの通知先')
  if (errors.length) {
    alert(`以下の項目は必須です:\n${errors.join('\n')}`)
    return false
  }
  return true
}

const buildPayload = () => ({
  supplier_id: form.supplier_id,
  is_enabled: form.is_enabled,
  scheduled_hour: form.scheduled_hour,
  scheduled_minute: form.scheduled_minute,
  lead_time_days: form.lead_time_days,
  progress_days_back: form.progress_days_back,
  progress_days_forward: form.progress_days_forward,
  calc_mode: form.calc_mode,
  send_order_excel: form.send_order_excel,
  email_body_custom: form.email_body_custom,
  reply_to_email: form.reply_to_email,
  cc_emails: form.cc_emails,
  notify_on_failure_user_ids: form.notify_on_failure_user_ids,
  notify_on_non_delivery_user_ids: form.notify_on_non_delivery_user_ids,
})

const save = async () => {
  if (!validate()) return
  saving.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      await api.purchaseAutoOrderSend.updateConfig(editId.value, payload)
    } else {
      await api.purchaseAutoOrderSend.createConfig(payload)
    }
    closeModal()
    await loadConfigs()
  } catch (error) {
    const detail = error?.response?.data?.detail
    alert(`保存に失敗しました。${detail ? `\n${detail}` : ''}`)
  } finally {
    saving.value = false
  }
}

const remove = async (config) => {
  if (!confirm(`${config.supplier_code} ${config.supplier_name} の設定を削除しますか？`)) return
  try {
    await api.purchaseAutoOrderSend.deleteConfig(config.id)
    await loadConfigs()
  } catch {
    alert('削除に失敗しました。')
  }
}

const runNow = async (config) => {
  if (!confirm(`${config.supplier_code} ${config.supplier_name} の注文書自動送信を今すぐ実行しますか？`)) return
  running.add(config.id)
  try {
    await api.purchaseAutoOrderSend.runNow(config.id)
    const start = Date.now()
    const timer = setInterval(async () => {
      if (Date.now() - start > 5 * 60 * 1000) {
        clearInterval(timer)
        running.delete(config.id)
        alert('5分経過しても完了しませんでした。')
        return
      }
      await loadConfigs()
      const updated = configs.value.find((item) => item.id === config.id)
      if (updated && updated.last_run_status !== 'RUNNING') {
        clearInterval(timer)
        running.delete(config.id)
        alert(`完了: ${updated.last_run_status}\n${updated.last_run_message || ''}`)
      }
    }, 3000)
  } catch {
    running.delete(config.id)
    alert('実行に失敗しました。')
  }
}

onMounted(async () => {
  await Promise.all([loadConfigs(), loadSuppliers(), loadUsers(), loadContacts()])
})
</script>

<style scoped>
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 6px 8px; border-bottom: 2px solid #e5e9ef; font-weight: 700; color: #374151; background: #f8fafc; white-space: nowrap; }
.data-table td { padding: 8px; border-bottom: 1px solid #e5e9ef; }
.td-msg { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #64748b; }
.td-actions { white-space: nowrap; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-on { background: #dcfce7; color: #166534; }
.badge-off { background: #f1f5f9; color: #64748b; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-failed { background: #fee2e2; color: #991b1b; }
.badge-running { background: #dbeafe; color: #1e40af; }
.badge-skipped { background: #fef3c7; color: #92400e; }
.btn-sm { padding: 3px 10px; font-size: 12px; border: 1px solid #d1d5db; border-radius: 4px; background: #fff; cursor: pointer; }
.btn-run { border-color: #3b82f6; color: #2563eb; }
.btn-danger { border-color: #fca5a5; color: #dc2626; }
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
.label-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.required { color: #dc2626; }
.form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.btn-primary { padding: 6px 16px; background: #2563eb; color: #fff; border: none; border-radius: 4px; font-weight: 600; cursor: pointer; }
.btn-secondary { padding: 6px 16px; background: #fff; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }
</style>
