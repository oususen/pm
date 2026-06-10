<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">品番変換マスタ <DataSourceDialog title="品番変換マスタ" :sources="dsSources" /></h2>
      <div class="page-actions">
        <button class="btn" @click="loadMappings" :disabled="loading">更新</button>
      </div>
    </div>

    <div class="card">
      <div class="form-row">
        <label>変換元品番</label>
        <input v-model.trim="form.source_product_code" type="text" placeholder="例: YD40006696" />
      </div>
      <div class="form-row">
        <label>変換先品番</label>
        <input v-model.trim="form.target_product_code" type="text" placeholder="例: YD40006696_TATA" />
      </div>
      <div class="form-row">
        <label>備考</label>
        <input v-model.trim="form.note" type="text" placeholder="任意" />
      </div>
      <div class="form-row checkbox-row">
        <label><input v-model="form.is_active" type="checkbox" /> 有効</label>
      </div>
      <div class="form-actions">
        <button class="btn primary" @click="saveMapping" :disabled="saving">
          {{ editingId ? '更新' : '追加' }}
        </button>
        <button class="btn" @click="resetForm" :disabled="saving">クリア</button>
      </div>
      <p v-if="message" class="helper success">{{ message }}</p>
      <p v-if="error" class="helper error">{{ error }}</p>
    </div>

    <div class="card">
      <table class="table">
        <thead>
          <tr>
            <th>変換元品番</th>
            <th>変換先品番</th>
            <th>有効</th>
            <th>備考</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ row.source_product_code }}</td>
            <td>{{ row.target_product_code }}</td>
            <td>{{ row.is_active ? '有効' : '無効' }}</td>
            <td>{{ row.note || '-' }}</td>
            <td class="actions">
              <button class="btn small" @click="startEdit(row)">編集</button>
              <button class="btn small danger" @click="removeRow(row)" :disabled="saving">削除</button>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td colspan="5" class="empty">データがありません。</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_product_code_mapping', desc: '品番変換マスタ' },
]

const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const editingId = ref(null)
const message = ref('')
const error = ref('')

const form = ref({
  source_product_code: '',
  target_product_code: '',
  is_active: true,
  note: '',
})

const resetForm = () => {
  editingId.value = null
  form.value = {
    source_product_code: '',
    target_product_code: '',
    is_active: true,
    note: '',
  }
}

const normalizeRows = (data) => (Array.isArray(data) ? data : (data?.results || []))

const loadMappings = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await api.productCodeMappings.list({ page_size: 1000 })
    rows.value = normalizeRows(res.data)
  } catch (e) {
    error.value = e?.response?.data?.detail || '一覧取得に失敗しました。'
  } finally {
    loading.value = false
  }
}

const validateForm = () => {
  if (!form.value.source_product_code) return '変換元品番を入力してください。'
  if (!form.value.target_product_code) return '変換先品番を入力してください。'
  return ''
}

const saveMapping = async () => {
  message.value = ''
  error.value = ''
  const validationError = validateForm()
  if (validationError) {
    error.value = validationError
    return
  }
  saving.value = true
  try {
    const payload = {
      source_product_code: form.value.source_product_code,
      target_product_code: form.value.target_product_code,
      is_active: Boolean(form.value.is_active),
      note: form.value.note || '',
    }
    if (editingId.value) {
      await api.productCodeMappings.update(editingId.value, payload)
      message.value = '更新しました。'
    } else {
      await api.productCodeMappings.create(payload)
      message.value = '追加しました。'
    }
    resetForm()
    await loadMappings()
  } catch (e) {
    error.value = e?.response?.data?.detail || '保存に失敗しました。'
  } finally {
    saving.value = false
  }
}

const startEdit = (row) => {
  editingId.value = row.id
  form.value = {
    source_product_code: row.source_product_code || '',
    target_product_code: row.target_product_code || '',
    is_active: Boolean(row.is_active),
    note: row.note || '',
  }
}

const removeRow = async (row) => {
  message.value = ''
  error.value = ''
  if (!window.confirm(`削除しますか？\n${row.source_product_code} -> ${row.target_product_code}`)) return
  saving.value = true
  try {
    await api.productCodeMappings.remove(row.id)
    message.value = '削除しました。'
    if (editingId.value === row.id) resetForm()
    await loadMappings()
  } catch (e) {
    error.value = e?.response?.data?.detail || '削除に失敗しました。'
  } finally {
    saving.value = false
  }
}

onMounted(loadMappings)
</script>

<style scoped>
.card {
  background: #fff;
  border: 1px solid #dbe2ea;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}
.form-row {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.checkbox-row {
  grid-template-columns: 1fr;
}
.form-row input[type='text'] {
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
}
.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.btn {
  border: 1px solid #94a3b8;
  background: #fff;
  border-radius: 6px;
  padding: 6px 10px;
  cursor: pointer;
}
.btn.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.btn.small {
  padding: 3px 8px;
}
.btn.danger {
  color: #b91c1c;
  border-color: #ef9a9a;
}
.helper {
  margin-top: 8px;
  font-size: 12px;
}
.helper.success {
  color: #166534;
}
.helper.error {
  color: #b91c1c;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.table th,
.table td {
  border: 1px solid #dbe2ea;
  padding: 6px 8px;
}
.table th {
  background: #f8fafc;
}
.actions {
  white-space: nowrap;
}
.empty {
  text-align: center;
  color: #64748b;
}
</style>

