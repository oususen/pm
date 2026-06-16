<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">仕入先マスタ <DataSourceDialog title="仕入先マスタ" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button @click="fetchSuppliers" class="btn-primary">更新</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <label>検索:
          <input v-model="filterText" class="filter-input" placeholder="コード・名前" />
        </label>
        <div class="btn-group">
          <span class="filter-label">区分:</span>
          <button :class="['btn-filter', { active: filterType === '' }]" @click="filterType = ''">全</button>
          <button :class="['btn-filter', { active: filterType === 'outsource' }]" @click="filterType = 'outsource'">外作</button>
          <button :class="['btn-filter', { active: filterType === 'purchase' }]" @click="filterType = 'purchase'">購入</button>
          <button :class="['btn-filter', { active: filterType === 'both' }]" @click="filterType = 'both'">両方</button>
        </div>
        <span class="filter-count">{{ filteredSuppliers.length }} / {{ suppliers.length }}件</span>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>仕入先コード</th>
            <th>仕入先名</th>
            <th>区分</th>
            <th>送信メールアドレス</th>
            <th>専用カレンダー</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="supplier in filteredSuppliers" :key="supplier.id">
            <td>{{ supplier.supplier_code }}</td>
            <td>{{ supplier.supplier_name }}</td>
            <td>{{ supplierTypeLabel(supplier.supplier_type) }}</td>
            <td>{{ supplier.order_email || '-' }}</td>
            <td>{{ getCalendarLabelBySupplier(supplier) }}</td>
            <td>
              <button v-if="canEdit" @click="editSupplier(supplier)" class="btn-sm">編集</button>
              <button v-if="canEdit" @click="deleteSupplier(supplier.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="filteredSuppliers.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '仕入先編集' : '仕入先新規作成' }}</h2>
        <form @submit.prevent="saveSupplier">
          <div class="form-group">
            <label>仕入先コード *</label>
            <input v-model="formData.supplier_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>仕入先名 *</label>
            <input v-model="formData.supplier_name" required :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>仕入先区分</label>
            <select v-model="formData.supplier_type" :disabled="!canEdit">
              <option value="outsource">外作</option>
              <option value="purchase">購入</option>
              <option value="both">両方</option>
            </select>
          </div>
          <div class="form-group">
            <label>送信メールアドレス</label>
            <input v-model="formData.order_email" type="email" placeholder="example@company.co.jp" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>専用カレンダー</label>
            <select v-model="formData.calendar" :disabled="!canEdit">
              <option :value="null">未設定</option>
              <option v-for="calendar in calendars" :key="calendar.id" :value="calendar.id">
                {{ calendar.calendar_code }} - {{ calendar.calendar_name }}
              </option>
            </select>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="!canEdit">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { canAccessMasterResource } from '@/utils/masterPermissions'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'm_supplier', desc: '仕入先マスタ' },
  { op: '読み取り', table: 'm_calendar', desc: 'カレンダ（選択肢）' },
  { op: '読み取り', table: 'm_line', desc: 'ライン（購買ライン参照）' },
]

const suppliers = ref([])
const calendars = ref([])
const purchaseLines = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  supplier_code: '',
  supplier_name: '',
  order_email: '',
  calendar: null,
})
const canEdit = computed(() => canAccessMasterResource('masters.supplier', 'edit'))
const filterText = ref('')
const filterType = ref('')

const SUPPLIER_TYPE_MAP = { outsource: '外作', purchase: '購入', both: '両方' }
const supplierTypeLabel = (type) => SUPPLIER_TYPE_MAP[type] || '両方'
const normalizeSupplierCode = (value) => {
  const text = String(value || '').trim()
  if (!/^\d+$/.test(text)) return text
  return text.padStart(6, '0')
}

const filteredSuppliers = computed(() => {
  return suppliers.value.filter((s) => {
    if (filterType.value && s.supplier_type !== filterType.value) return false
    if (filterText.value) {
      const q = filterText.value.toUpperCase()
      if (!s.supplier_code.toUpperCase().includes(q) && !s.supplier_name.toUpperCase().includes(q)) return false
    }
    return true
  })
})

const fetchSuppliers = async () => {
  try {
    const response = await api.suppliers.getSuppliers()
    suppliers.value = response.data.results || response.data
  } catch (error) {
    console.error('仕入先取得エラー:', error)
    alert('仕入先データの取得に失敗しました')
  }
}

const fetchCalendars = async () => {
  try {
    const response = await api.calendars.getCalendars()
    calendars.value = response.data.results || response.data || []
  } catch (error) {
    console.error('カレンダー取得エラー:', error)
  }
}

const fetchPurchaseLines = async () => {
  try {
    const response = await api.lines.getLines({ page_size: 500 })
    const lines = response.data.results || response.data || []
    purchaseLines.value = lines.filter((row) => row.line_type === 'PURCHASE')
  } catch (error) {
    console.error('購買ライン取得エラー:', error)
  }
}

const getCalendarLabel = (calendarId) => {
  if (!calendarId) return '-'
  const found = calendars.value.find((item) => item.id === calendarId)
  if (!found) return '-'
  return `${found.calendar_code} - ${found.calendar_name}`
}

const getCalendarLabelBySupplier = (supplier) => {
  const purchaseLine = purchaseLines.value.find((line) => line.line_code === supplier.supplier_code)
  const calendarId = purchaseLine?.calendar || null
  return getCalendarLabel(calendarId)
}

const showNewDialog = () => {
  if (!canEdit.value) return
  isEdit.value = false
  formData.value = {
    supplier_code: '',
    supplier_name: '',
    supplier_type: 'both',
    order_email: '',
    calendar: null,
  }
  showDialog.value = true
}

const editSupplier = (supplier) => {
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = { ...supplier }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveSupplier = async () => {
  if (!canEdit.value) return
  try {
    const normalizedSupplierCode = normalizeSupplierCode(formData.value.supplier_code)
    formData.value.supplier_code = normalizedSupplierCode
    const payload = {
      ...formData.value,
      supplier_code: normalizedSupplierCode,
      order_email: (formData.value.order_email || '').trim(),
      calendar: formData.value.calendar || null,
    }
    if (isEdit.value) {
      await api.suppliers.updateSupplier(formData.value.id, payload)
      alert('更新しました')
    } else {
      await api.suppliers.createSupplier(payload)
      alert('作成しました')
    }
    await fetchSuppliers()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteSupplier = async (id) => {
  if (!canEdit.value) return
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.suppliers.deleteSupplier(id)
    await fetchSuppliers()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchSuppliers()
  fetchCalendars()
  fetchPurchaseLines()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 13px;
}
.filter-bar label { display: flex; align-items: center; gap: 4px; color: #475569; font-weight: 600; }
.filter-input { padding: 2px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; width: 140px; }
.btn-group { display: flex; align-items: center; gap: 2px; }
.filter-label { color: #475569; font-weight: 600; margin-right: 2px; }
.btn-filter {
  padding: 2px 8px;
  font-size: 12px;
  border: 1px solid #d1d5db;
  background: #fff;
  color: #64748b;
  cursor: pointer;
  border-radius: 3px;
}
.btn-filter.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
.filter-count { color: #94a3b8; margin-left: auto; }
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  min-width: 500px;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-actions {
  margin-top: 1.5rem;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background-color: white;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover {
  background-color: #f5f5f5;
}
</style>
