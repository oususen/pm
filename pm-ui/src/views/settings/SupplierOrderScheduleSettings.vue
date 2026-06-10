<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">仕入れ先スケジュール設定 <DataSourceDialog title="仕入れ先スケジュール設定" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button class="btn-primary" @click="fetchSchedules" :disabled="!canViewPage">更新</button>
        <button class="btn-success" @click="openNew" :disabled="!canEditPage">新規</button>
      </div>
    </div>

    <div v-if="!canViewPage" class="page-content">
      <div class="no-data">この画面を開く権限がありません。</div>
    </div>
    <div v-else class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>仕入先</th>
            <th>パターン</th>
            <th>LT(日)</th>
            <th>有効</th>
            <th>備考</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ row.supplier_code }} - {{ row.supplier_name }}</td>
            <td>{{ row.pattern_code }} - {{ row.pattern_name }}</td>
            <td>{{ row.lead_time_days }}</td>
            <td>{{ row.is_enabled ? '有効' : '無効' }}</td>
            <td>{{ row.note }}</td>
            <td>
              <button class="btn-sm" @click="openEdit(row)" :disabled="!canEditPage">編集</button>
              <button class="btn-sm btn-danger" @click="remove(row.id)" :disabled="!canEditPage">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="rows.length === 0" class="no-data">データがありません</div>
    </div>

    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '仕入れ先スケジュール編集' : '仕入れ先スケジュール新規作成' }}</h2>
        <form @submit.prevent="save">
          <div class="form-group">
            <label>仕入先 *</label>
            <select v-model="form.supplier" required :disabled="!canEditPage">
              <option value="">選択してください</option>
              <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
                {{ supplier.supplier_code }} - {{ supplier.supplier_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>パターン *</label>
            <select v-model="form.pattern" required :disabled="!canEditPage">
              <option value="">選択してください</option>
              <option v-for="p in patterns" :key="p.id" :value="p.id">
                {{ p.pattern_code }} - {{ p.pattern_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>リードタイム(日)</label>
            <input v-model.number="form.lead_time_days" type="number" min="0" :disabled="!canEditPage" />
          </div>
          <div class="form-group">
            <label>
              <input v-model="form.is_enabled" type="checkbox" :disabled="!canEditPage" />
              有効
            </label>
          </div>
          <div class="form-group">
            <label>備考</label>
            <input v-model="form.note" :disabled="!canEditPage" />
          </div>
          <div class="form-actions">
            <button class="btn-primary" type="submit" :disabled="!canEditPage">保存</button>
            <button class="btn-secondary" type="button" @click="closeDialog">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_supplier_order_schedule', desc: '仕入れ先スケジュール設定' },
]

const rows = ref([])
const suppliers = ref([])
const patterns = ref([])
const showDialog = ref(false)
const isEdit = ref(false)

const form = ref({
  id: null,
  supplier: '',
  pattern: '',
  lead_time_days: 0,
  is_enabled: true,
  note: '',
})

const canAccessByResource = (resource, level = 'view') => {
  const user = authState.user
  if (!user || !resource) return false
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) {
    return hasPermission(user, resource, level)
  }
  return hasPermission(user, 'settings', level)
}

const canViewPage = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return canAccessByResource('settings.supplier_order_schedule', 'view')
})

const canEditPage = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return canAccessByResource('settings.supplier_order_schedule', 'edit')
})

const fetchSuppliers = async () => {
  if (!canViewPage.value) return
  const response = await api.suppliers.getSuppliers()
  suppliers.value = response.data.results || response.data || []
}

const fetchPatterns = async () => {
  if (!canViewPage.value) return
  const response = await api.supplierOrderPatterns.list({ is_active: true })
  patterns.value = response.data || []
}

const fetchSchedules = async () => {
  if (!canViewPage.value) return
  const response = await api.supplierOrderSchedules.list()
  rows.value = response.data || []
}

const openNew = () => {
  if (!canEditPage.value) return
  isEdit.value = false
  form.value = {
    id: null,
    supplier: '',
    pattern: '',
    lead_time_days: 0,
    is_enabled: true,
    note: '',
  }
  showDialog.value = true
}

const openEdit = (row) => {
  if (!canEditPage.value) return
  isEdit.value = true
  form.value = { ...row }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const save = async () => {
  if (!canEditPage.value) return
  const payload = {
    supplier: form.value.supplier,
    pattern: form.value.pattern,
    lead_time_days: Number(form.value.lead_time_days || 0),
    is_enabled: Boolean(form.value.is_enabled),
    note: form.value.note || '',
  }
  if (isEdit.value) {
    await api.supplierOrderSchedules.update(form.value.id, payload)
  } else {
    await api.supplierOrderSchedules.create(payload)
  }
  showDialog.value = false
  await fetchSchedules()
}

const remove = async (id) => {
  if (!canEditPage.value) return
  if (!confirm('削除しますか？')) return
  await api.supplierOrderSchedules.delete(id)
  await fetchSchedules()
}

onMounted(async () => {
  if (!canViewPage.value) return
  await Promise.all([fetchSuppliers(), fetchPatterns(), fetchSchedules()])
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
  padding: 24px;
  border-radius: 8px;
  min-width: 500px;
}
.form-group {
  margin-bottom: 10px;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
