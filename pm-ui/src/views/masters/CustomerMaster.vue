<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">得意先マスタ <DataSourceDialog title="得意先マスタ" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button @click="fetchCustomers" class="btn-primary">更新</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>得意先コード</th>
            <th>得意先名</th>
            <th>略称</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="customer in customers" :key="customer.id">
            <td>{{ customer.customer_code }}</td>
            <td>{{ customer.customer_name }}</td>
            <td>{{ customer.short_name }}</td>
            <td>{{ customer.is_active ? '有効' : '無効' }}</td>
            <td>
              <button v-if="canEdit" @click="editCustomer(customer)" class="btn-sm">編集</button>
              <button v-if="canEdit" @click="deleteCustomer(customer.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="customers.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '得意先編集' : '得意先新規作成' }}</h2>
        <form @submit.prevent="saveCustomer">
          <div class="form-group">
            <label>得意先コード *</label>
            <input v-model="formData.customer_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>得意先名 *</label>
            <input v-model="formData.customer_name" required :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>略称</label>
            <input v-model="formData.short_name" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>カレンダ</label>
            <select v-model="formData.calendar" :disabled="!canEdit">
              <option :value="null">選択なし</option>
              <option v-for="cal in calendars" :key="cal.id" :value="cal.id">
                {{ cal.calendar_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" :disabled="!canEdit" />
              有効
            </label>
          </div>

          <!-- 納入地別カレンダ（編集時のみ表示） -->
          <div v-if="isEdit" class="ship-to-section">
            <h3>納入地別カレンダ</h3>
            <table v-if="shipToRows.length" class="ship-to-table">
              <thead>
                <tr>
                  <th>納入先コード</th>
                  <th>納入地名</th>
                  <th class="num">加算日数</th>
                  <th>カレンダ</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in shipToRows" :key="row.id || row.ship_to_code" :class="{ 'new-row': row._isNew }">
                  <td>{{ row.ship_to_code }}</td>
                  <td><input v-model="row.ship_to_name" class="inline-input" placeholder="納入地名" /></td>
                  <td class="num"><input v-if="row._isNew" type="number" v-model.number="row.additional_days" min="0" class="inline-input num" style="width:60px" /><template v-else>{{ row.additional_days }}</template></td>
                  <td>
                    <select v-model="row.calendar" :disabled="!canEdit" class="cal-select">
                      <option :value="null">(顧客と同じ)</option>
                      <option v-for="cal in calendars" :key="cal.id" :value="cal.id">
                        {{ cal.calendar_name }}
                      </option>
                    </select>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="no-ship-to">納入地の登録なし（出荷 → 納入地別出荷加算日数で追加）</div>
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
  { op: '読み書き', table: 'm_customer', desc: '得意先マスタ' },
  { op: '読み取り', table: 'm_calendar', desc: 'カレンダ（選択肢）' },
]

const customers = ref([])
const calendars = ref([])
const shipToRows = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  customer_code: '',
  customer_name: '',
  short_name: '',
  calendar: null,
  is_active: true
})
const canEdit = computed(() => canAccessMasterResource('masters.customer', 'edit'))

const fetchCustomers = async () => {
  try {
    const response = await api.customers.getCustomers()
    // ページネーションレスポンスの場合はresultsを使用
    customers.value = response.data.results || response.data
  } catch (error) {
    console.error('得意先取得エラー:', error)
    alert('得意先データの取得に失敗しました')
  }
}

const fetchCalendars = async () => {
  try {
    const response = await api.calendars.getCalendars()
    calendars.value = response.data.results || response.data
  } catch (error) {
    console.error('カレンダ取得エラー:', error)
  }
}

const showNewDialog = () => {
  if (!canEdit.value) return
  isEdit.value = false
  formData.value = {
    customer_code: '',
    customer_name: '',
    short_name: '',
    calendar: null,
    is_active: true
  }
  shipToRows.value = []
  showDialog.value = true
}

const fetchShipToRows = async (customerId) => {
  try {
    const [existingRes, codesRes] = await Promise.all([
      api.shipToLeadTimes.getAll({ customer: customerId }),
      api.shipToLeadTimes.getShipToCodes(customerId),
    ])
    const existing = (existingRes.data.results || existingRes.data || []).map(r => ({ ...r, _isNew: false }))
    const existingCodes = new Set(existing.map(r => r.ship_to_code))
    const orderCodes = codesRes.data || []
    const newRows = orderCodes
      .filter(code => !existingCodes.has(code))
      .map(code => ({
        _isNew: true,
        customer: customerId,
        ship_to_code: code,
        ship_to_name: '',
        additional_days: 0,
        calendar: null,
        is_active: true,
      }))
    shipToRows.value = [...existing, ...newRows]
  } catch (e) {
    console.error('納入地取得エラー:', e)
    shipToRows.value = []
  }
}

const editCustomer = async (customer) => {
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = { ...customer }
  shipToRows.value = []
  showDialog.value = true
  await fetchShipToRows(customer.id)
}

const closeDialog = () => {
  showDialog.value = false
}

const saveCustomer = async () => {
  if (!canEdit.value) return
  try {
    // データの前処理：空文字列をnullに変換
    const dataToSend = {
      ...formData.value,
      short_name: formData.value.short_name || null,
      calendar: formData.value.calendar || null
    }

    if (isEdit.value) {
      await api.customers.updateCustomer(dataToSend.id, dataToSend)
      for (const row of shipToRows.value) {
        const payload = {
          customer: row.customer,
          ship_to_code: row.ship_to_code,
          ship_to_name: row.ship_to_name,
          additional_days: row.additional_days,
          calendar: row.calendar || null,
          is_active: row.is_active,
        }
        if (row._isNew) {
          if (row.calendar) {
            await api.shipToLeadTimes.create(payload)
          }
        } else {
          await api.shipToLeadTimes.update(row.id, payload)
        }
      }
      alert('更新しました')
    } else {
      await api.customers.createCustomer(dataToSend)
      alert('作成しました')
    }
    await fetchCustomers()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    console.error('エラー詳細:', error.response?.data)
    const errorMessage = error.response?.data?.detail
      || JSON.stringify(error.response?.data)
      || error.message
      || '保存に失敗しました'
    alert('保存に失敗しました\n\n' + errorMessage)
  }
}

const deleteCustomer = async (id) => {
  if (!canEdit.value) return
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.customers.deleteCustomer(id)
    await fetchCustomers()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchCustomers()
  fetchCalendars()
})
</script>

<style scoped>
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

.form-group input[type="text"],
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input[type="checkbox"] {
  margin-right: 0.5rem;
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

.ship-to-section {
  margin-top: 1.2rem;
  border-top: 1px solid #e2e8f0;
  padding-top: 1rem;
}

.ship-to-section h3 {
  margin: 0 0 0.5rem;
  font-size: 0.9rem;
  color: #475569;
}

.ship-to-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.ship-to-table th,
.ship-to-table td {
  padding: 4px 8px;
  border: 1px solid #e2e8f0;
  text-align: left;
}

.ship-to-table th {
  background: #f8fafc;
  font-weight: 600;
  color: #475569;
}

.ship-to-table .num {
  text-align: right;
}

.cal-select {
  width: 100%;
  padding: 2px 4px;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  font-size: 0.85rem;
}

.no-ship-to {
  color: #94a3b8;
  font-size: 0.85rem;
  padding: 4px 0;
}

.new-row {
  background: #fffbeb;
}

.inline-input {
  padding: 2px 4px;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  font-size: 0.85rem;
  width: 100%;
}

.inline-input.num {
  text-align: right;
}
</style>
