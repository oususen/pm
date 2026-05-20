<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">納入地別出荷加算日数</h1>
      <div class="page-actions">
        <button @click="fetchData" class="btn-secondary" :disabled="loading">更新</button>
        <button @click="openCreateDialog" class="btn-success">追加</button>
      </div>
    </div>

    <table v-if="rows.length" class="data-table">
      <thead>
        <tr>
          <th>顧客コード</th>
          <th>顧客名</th>
          <th>納入先コード</th>
          <th>納入地名</th>
          <th class="num">出荷加算日数</th>
          <th>有効</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.id">
          <td>{{ row.customer_code }}</td>
          <td>{{ row.customer_name }}</td>
          <td>{{ row.ship_to_code }}</td>
          <td>{{ row.ship_to_name }}</td>
          <td class="num">{{ row.additional_days }}</td>
          <td>{{ row.is_active ? 'はい' : 'いいえ' }}</td>
          <td>
            <button class="btn-secondary btn-sm" @click="openEditDialog(row)">編集</button>
            <button class="btn-danger btn-sm" @click="deleteRow(row)">削除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else-if="!loading" class="no-data">データがありません</div>

    <div v-if="showDialog" class="modal-overlay" @click.self="showDialog = false">
      <div class="modal-content" style="max-width: 480px;">
        <h2>{{ editingId ? '編集' : '新規追加' }}</h2>
        <div class="form-group">
          <label>顧客</label>
          <select v-model="form.customer" :disabled="!!editingId">
            <option value="">選択してください</option>
            <option v-for="c in customers" :key="c.id" :value="c.id">
              {{ c.customer_code }} - {{ c.customer_name }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>納入先コード</label>
          <input v-model="form.ship_to_code" :disabled="!!editingId" />
        </div>
        <div class="form-group">
          <label>納入地名</label>
          <input v-model="form.ship_to_name" placeholder="例: 神立, つくば, 滋賀" />
        </div>
        <div class="form-group">
          <label>出荷加算日数</label>
          <input type="number" v-model.number="form.additional_days" min="0" />
        </div>
        <div class="form-group">
          <label>
            <input type="checkbox" v-model="form.is_active" /> 有効
          </label>
        </div>
        <div class="form-actions">
          <button @click="saveForm" class="btn-primary" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
          <button @click="showDialog = false" class="btn-secondary">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAPI } from '@/api/client'

const api = useAPI()
const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const customers = ref([])
const showDialog = ref(false)
const editingId = ref(null)
const form = ref({ customer: '', ship_to_code: '', ship_to_name: '', additional_days: 0, is_active: true })

const fetchData = async () => {
  loading.value = true
  try {
    const res = await api.shipToLeadTimes.getAll()
    rows.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error('取得エラー:', e)
  } finally {
    loading.value = false
  }
}

const fetchCustomers = async () => {
  try {
    const res = await api.customers.getCustomers({ page_size: 500 })
    customers.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error('顧客取得エラー:', e)
  }
}

const openCreateDialog = () => {
  editingId.value = null
  form.value = { customer: '', ship_to_code: '', ship_to_name: '', additional_days: 0, is_active: true }
  showDialog.value = true
}

const openEditDialog = (row) => {
  editingId.value = row.id
  form.value = {
    customer: row.customer,
    ship_to_code: row.ship_to_code,
    ship_to_name: row.ship_to_name,
    additional_days: row.additional_days,
    is_active: row.is_active,
  }
  showDialog.value = true
}

const saveForm = async () => {
  if (!form.value.customer || !form.value.ship_to_code) {
    alert('顧客と納入先コードは必須です')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await api.shipToLeadTimes.update(editingId.value, form.value)
    } else {
      await api.shipToLeadTimes.create(form.value)
    }
    showDialog.value = false
    await fetchData()
  } catch (e) {
    console.error('保存エラー:', e)
    const detail = e?.response?.data?.detail || e?.response?.data?.ship_to_code?.[0] || '保存に失敗しました'
    alert(detail)
  } finally {
    saving.value = false
  }
}

const deleteRow = async (row) => {
  if (!confirm(`${row.customer_code} ${row.ship_to_code}(${row.ship_to_name}) を削除しますか？`)) return
  try {
    await api.shipToLeadTimes.delete(row.id)
    await fetchData()
  } catch (e) {
    console.error('削除エラー:', e)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchData()
  fetchCustomers()
})
</script>

<style scoped>
.num { text-align: right; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-weight: 600; margin-bottom: 4px; font-size: 13px; }
.form-group input, .form-group select { width: 100%; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 14px; }
.form-group input[type="number"] { width: 120px; }
.form-group input[type="checkbox"] { width: auto; margin-right: 6px; }
.form-actions { display: flex; gap: 8px; margin-top: 16px; }
.no-data { padding: 32px; text-align: center; color: #64748b; }
</style>
