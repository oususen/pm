<template>
  <div class="page">
    <h2 class="page-title">納入実績編集</h2>
    <div class="filters">
      <label>開始日 <input v-model="startDate" type="date" /></label>
      <label>終了日 <input v-model="endDate" type="date" /></label>
      <label>品番 <input v-model.trim="productCode" type="text" /></label>
      <button class="btn" :disabled="loading" @click="load">検索</button>
    </div>

    <div class="table-wrap">
      <table class="list-table">
        <thead>
          <tr>
            <th>納入日</th>
            <th>品番</th>
            <th>品名</th>
            <th>購入先</th>
            <th class="num">数量</th>
            <th>入力者</th>
            <th class="num">ID</th>
            <th class="center">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ formatDate(row.delivery_date) }}</td>
            <td>{{ row.product_code }}</td>
            <td>{{ row.product_name }}</td>
            <td>{{ row.supplier }}</td>
            <td class="num">{{ formatNum(row.qty) }}</td>
            <td>{{ row.operator_name }}</td>
            <td class="num">{{ row.id }}</td>
            <td class="actions">
              <button class="btn btn-sm" :disabled="loading || !canEdit" @click="startEdit(row)">編集</button>
              <button class="btn btn-sm danger" :disabled="loading || !canEdit" @click="removeRow(row)">削除</button>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="8" class="no-data">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="editingId != null" class="edit-panel">
      <div class="edit-title">納入実績更新 (ID: {{ editingId }})</div>
      <div class="edit-grid">
        <label>納入日 <input v-model="form.arrivalDate" type="date" /></label>
        <label>品番 <input :value="form.productCode" type="text" readonly /></label>
        <label>品名 <input :value="form.productName" type="text" readonly /></label>
        <label>購入先 <input :value="form.supplierLabel" type="text" readonly /></label>
        <label>数量 <input v-model.number="form.qty" type="number" min="1" step="1" /></label>
        <label>入力者 <input v-model.trim="form.operatorName" type="text" /></label>
        <label class="span-2">備考 <input v-model.trim="form.remarks" type="text" /></label>
      </div>
      <div class="edit-actions">
        <button class="btn primary" :disabled="saving || loading || !canEdit" @click="saveEdit">更新</button>
        <button class="btn" :disabled="saving || loading" @click="cancelEdit">キャンセル</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const today = formatISODate(new Date())
const startDate = ref(today)
const endDate = ref(today)
const productCode = ref('')

const editingId = ref(null)
const form = reactive({
  arrivalDate: '',
  productCode: '',
  productName: '',
  supplierLabel: '',
  supplierId: null,
  lineId: null,
  qty: null,
  operatorName: '',
  remarks: '',
})

const canEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const entry = permissions.find((item) => item.resource === 'purchase.actual_input')
    || permissions.find((item) => item.resource === 'purchase')
  if (entry) return Boolean(entry.can_edit)
  return hasPermission(user, 'purchase', 'edit')
})

const formatDate = (value) => String(value || '').replace(/-/g, '/')
const formatNum = (value) => Number(value || 0).toLocaleString()
const normalizeDateInput = (value) => {
  const text = String(value || '').trim().replace(/\//g, '-')
  if (!text) return ''
  return text.slice(0, 10)
}

const load = async () => {
  loading.value = true
  try {
    const res = await api.purchaseActuals.getInquiry({
      start_date: startDate.value,
      end_date: endDate.value,
      product_code: productCode.value || undefined,
    })
    rows.value = Array.isArray(res.data) ? res.data : []
    if (editingId.value != null) {
      const current = rows.value.find((row) => row.id === editingId.value)
      if (!current) cancelEdit()
    }
  } catch (e) {
    rows.value = []
    alert('納入実績の取得に失敗しました。')
  } finally {
    loading.value = false
  }
}

const startEdit = (row) => {
  editingId.value = row.id
  form.arrivalDate = normalizeDateInput(row.arrival_date || row.delivery_date)
  form.productCode = row.product_code || ''
  form.productName = row.product_name || ''
  form.supplierLabel = row.supplier || ''
  form.supplierId = row.supplier_id ?? null
  form.lineId = row.line_id ?? null
  form.qty = Number(row.qty || 0)
  form.operatorName = row.operator_name || ''
  form.remarks = row.remarks || ''
}

const cancelEdit = () => {
  editingId.value = null
  form.arrivalDate = ''
  form.productCode = ''
  form.productName = ''
  form.supplierLabel = ''
  form.supplierId = null
  form.lineId = null
  form.qty = null
  form.operatorName = ''
  form.remarks = ''
}

const saveEdit = async () => {
  if (editingId.value == null) return
  if (!form.arrivalDate) {
    alert('納入日を入力してください。')
    return
  }
  if (!form.qty || Number(form.qty) <= 0) {
    alert('数量は1以上で入力してください。')
    return
  }

  saving.value = true
  try {
    await api.purchaseActuals.update(editingId.value, {
      arrival_date: form.arrivalDate,
      supplier_id: form.supplierId,
      line_id: form.lineId,
      qty: Number(form.qty),
      operator_name: form.operatorName || '',
      remarks: form.remarks || '',
    })
    alert('更新しました。')
    await load()
    cancelEdit()
  } catch (e) {
    alert('更新に失敗しました。')
  } finally {
    saving.value = false
  }
}

const removeRow = async (row) => {
  if (!canEdit.value) return
  if (!window.confirm('この納入実績を削除しますか？')) return

  saving.value = true
  try {
    await api.purchaseActuals.remove(row.id)
    alert('削除しました。')
    if (editingId.value === row.id) cancelEdit()
    await load()
  } catch (e) {
    alert('削除に失敗しました。')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding: 16px; }
.page-title { margin: 0 0 12px; font-size: 22px; }
.filters { display: flex; gap: 10px; align-items: end; margin-bottom: 10px; flex-wrap: wrap; }
.filters label { display: grid; gap: 4px; font-size: 13px; font-weight: 700; }
.filters input { border: 1px solid #9ca3af; padding: 6px; min-width: 140px; }
.btn { border: 1px solid #6d7478; background: #e5e5e5; padding: 6px 12px; font-weight: 700; }
.btn:disabled { opacity: 0.5; cursor: default; }
.btn.primary { background: #d7f0ff; }
.btn-sm { padding: 3px 8px; font-size: 12px; }
.btn-sm.danger { background: #f8d7da; }
.table-wrap { border: 1px solid #8d9498; overflow: auto; background: #fff; }
.list-table { width: 100%; border-collapse: collapse; min-width: 1000px; }
.list-table th, .list-table td { border: 1px solid #ccd2d8; padding: 6px 8px; font-size: 13px; }
.list-table th { background: #4f6f82; color: #fff; text-align: left; position: sticky; top: 0; }
.num { text-align: right; }
.center { text-align: center; }
.actions { display: flex; gap: 6px; justify-content: center; }
.no-data { text-align: center; color: #64748b; }

.edit-panel { margin-top: 10px; border: 1px solid #8d9498; background: #f5f7f8; padding: 10px; }
.edit-title { background: #4f6f82; color: #fff; padding: 5px 8px; font-weight: 700; margin: -10px -10px 10px; }
.edit-grid { display: grid; gap: 8px; grid-template-columns: repeat(2, minmax(220px, 1fr)); }
.edit-grid label { display: grid; gap: 4px; font-size: 13px; font-weight: 700; }
.edit-grid input { border: 1px solid #9ca3af; padding: 6px; background: #fff; }
.edit-grid input[readonly] { background: #ececec; }
.span-2 { grid-column: span 2; }
.edit-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 10px; }
</style>




