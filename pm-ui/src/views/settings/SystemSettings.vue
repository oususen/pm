<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">システム設定</h1>
      <div class="page-actions">
        <button @click="fetchSettings" class="btn-primary" :disabled="loading">更新</button>
        <button @click="showNewDialog = true" class="btn-secondary" :disabled="!canEdit">新規</button>
        <button @click="saveAll" class="btn-success" :disabled="loading || !canEdit || !hasChanges">保存</button>
      </div>
    </div>

    <div v-if="!canView" class="page-content">
      <div class="no-data">この画面を開く権限がありません。</div>
    </div>
    <div v-else class="page-content">
      <div v-if="loading" class="loading-message">読み込み中...</div>
      <template v-else>
        <div v-if="saveError" class="error-message">{{ saveError }}</div>
        <div v-if="saveSuccess" class="success-message">保存しました。</div>

        <table class="data-table">
          <thead>
            <tr>
              <th>キー</th>
              <th>説明</th>
              <th>値</th>
              <th>最終更新</th>
              <th>更新者</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in settings" :key="item.key">
              <td class="key-cell">{{ item.key }}</td>
              <td>{{ item.description }}</td>
              <td>
                <input
                  v-if="canEdit"
                  type="text"
                  v-model="editValues[item.key]"
                  class="value-input"
                />
                <span v-else>{{ item.value }}</span>
              </td>
              <td>{{ formatDate(item.updated_at) }}</td>
              <td>{{ item.updated_by || '-' }}</td>
            </tr>
          </tbody>
        </table>

        <div v-if="settings.length === 0" class="no-data">データがありません</div>

        <div v-if="canEdit" class="pw-section">
          <h3 class="section-title">計画数編集用パスワード</h3>
          <div class="pw-form">
            <input v-model="planQtyPassword" type="password" class="form-input pw-input" placeholder="新しいパスワード" />
            <button class="btn-primary" :disabled="!planQtyPassword" @click="savePlanQtyPassword">設定</button>
          </div>
          <div v-if="planQtyPwMsg" :class="planQtyPwError ? 'error-message' : 'success-message'">{{ planQtyPwMsg }}</div>
        </div>
      </template>
    </div>

    <!-- 新規作成ダイアログ -->
    <div v-if="showNewDialog" class="modal-overlay" @click.self="closeNewDialog">
      <div class="modal-content">
        <h2>新規設定</h2>
        <div v-if="createError" class="error-message">{{ createError }}</div>
        <form @submit.prevent="createSetting">
          <div class="form-group">
            <label>キー <span class="required">*</span></label>
            <input v-model="newForm.key" type="text" class="form-input" placeholder="例: some_setting_key" required />
          </div>
          <div class="form-group">
            <label>説明</label>
            <input v-model="newForm.description" type="text" class="form-input" placeholder="例: ○○の設定（単位）" />
          </div>
          <div class="form-group">
            <label>値 <span class="required">*</span></label>
            <input v-model="newForm.value" type="text" class="form-input" required />
          </div>
          <div class="form-actions">
            <button type="button" @click="closeNewDialog" class="btn-secondary">キャンセル</button>
            <button type="submit" class="btn-success" :disabled="loading">作成</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'

const loading = ref(false)
const settings = ref([])
const editValues = ref({})
const saveError = ref('')
const saveSuccess = ref(false)
const showNewDialog = ref(false)
const newForm = ref({ key: '', value: '', description: '' })
const createError = ref('')

const canView = computed(() => Boolean(authState.user))
const canEdit = computed(() => authState.user?.is_superuser || authState.user?.is_staff)

const hasChanges = computed(() => {
  return settings.value.some((item) => editValues.value[item.key] !== item.value)
})

const fetchSettings = async () => {
  loading.value = true
  saveError.value = ''
  saveSuccess.value = false
  try {
    const res = await api.systemSettings.list()
    settings.value = res.data
    editValues.value = {}
    res.data.forEach((item) => {
      editValues.value[item.key] = item.value
    })
  } catch (e) {
    console.error('システム設定の取得に失敗しました', e)
  } finally {
    loading.value = false
  }
}

const saveAll = async () => {
  const payload = {}
  settings.value.forEach((item) => {
    if (editValues.value[item.key] !== item.value) {
      payload[item.key] = editValues.value[item.key]
    }
  })
  if (Object.keys(payload).length === 0) return

  loading.value = true
  saveError.value = ''
  saveSuccess.value = false
  try {
    await api.systemSettings.updateByKey(payload)
    saveSuccess.value = true
    await fetchSettings()
  } catch (e) {
    saveError.value = '保存に失敗しました。'
    console.error(e)
  } finally {
    loading.value = false
  }
}

const closeNewDialog = () => {
  showNewDialog.value = false
  newForm.value = { key: '', value: '', description: '' }
  createError.value = ''
}

const createSetting = async () => {
  loading.value = true
  createError.value = ''
  try {
    await api.systemSettings.create(newForm.value)
    closeNewDialog()
    await fetchSettings()
  } catch (e) {
    const msg = e.response?.data?.key || e.response?.data?.detail || '作成に失敗しました。'
    createError.value = msg
  } finally {
    loading.value = false
  }
}

const planQtyPassword = ref('')
const planQtyPwMsg = ref('')
const planQtyPwError = ref(false)

const savePlanQtyPassword = async () => {
  if (!planQtyPassword.value) return
  planQtyPwMsg.value = ''
  planQtyPwError.value = false
  try {
    await api.systemSettings.setPlanQtyPassword({ password: planQtyPassword.value })
    planQtyPwMsg.value = '計画数編集用パスワードを設定しました。'
    planQtyPassword.value = ''
  } catch (e) {
    planQtyPwError.value = true
    planQtyPwMsg.value = e?.response?.data?.detail || '設定に失敗しました。'
  }
}

const formatDate = (val) => {
  if (!val) return '-'
  return new Date(val).toLocaleString('ja-JP')
}

onMounted(fetchSettings)
</script>

<style scoped>
.page-container {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.page-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.page-actions {
  display: flex;
  gap: 8px;
}
.page-content {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 12px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th,
.data-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}
.data-table th {
  background: #f1f5f9;
  font-weight: 600;
  color: #374151;
}
.key-cell {
  font-family: monospace;
  color: #1e40af;
}
.value-input {
  width: 120px;
  padding: 4px 6px;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  font-size: 13px;
}
.loading-message {
  color: #6b7280;
  padding: 12px 0;
}
.no-data {
  color: #6b7280;
  padding: 20px 0;
  text-align: center;
}
.error-message {
  color: #dc2626;
  margin-bottom: 8px;
  font-size: 13px;
}
.success-message {
  color: #16a34a;
  margin-bottom: 8px;
  font-size: 13px;
}
.btn-primary {
  padding: 6px 14px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-success {
  padding: 6px 14px;
  background: #16a34a;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-success:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-secondary {
  padding: 6px 14px;
  background: #fff;
  color: #374151;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-content {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  width: 420px;
  max-width: 90vw;
}
.modal-content h2 {
  margin: 0 0 16px;
  font-size: 15px;
  font-weight: 700;
}
.form-group {
  margin-bottom: 14px;
}
.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 4px;
}
.required {
  color: #dc2626;
}
.form-input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  font-size: 13px;
  box-sizing: border-box;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
.pw-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}
.section-title {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}
.pw-form {
  display: flex;
  gap: 8px;
  align-items: center;
}
.pw-input {
  width: 200px;
}
</style>

