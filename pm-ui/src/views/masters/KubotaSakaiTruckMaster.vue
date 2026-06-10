<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">クボタ堺便マスタ <DataSourceDialog title="クボタ堺便マスタ" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button @click="fetchTrucks" class="btn-primary" :disabled="loading">更新</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>便名</th>
            <th>俗称</th>
            <th>荷台幅(mm)</th>
            <th>荷台奥行(mm)</th>
            <th>荷台高さ(mm)</th>
            <th>最大積載(kg)</th>
            <th>出発時刻</th>
            <th>到着時刻</th>
            <th>到着日</th>
            <th>常用</th>
            <th>表示順</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="truck in trucks" :key="truck.id">
            <td>{{ truck.name }}</td>
            <td>{{ truck.alias_name || '' }}</td>
            <td>{{ truck.width }}</td>
            <td>{{ truck.depth }}</td>
            <td>{{ truck.height }}</td>
            <td>{{ truck.max_weight }}</td>
            <td>{{ formatTime(truck.departure_time) }}</td>
            <td>{{ formatTime(truck.arrival_time) }}</td>
            <td>{{ truck.arrival_day_offset === 0 ? '当日' : `翌${truck.arrival_day_offset}日` }}</td>
            <td>{{ truck.default_use ? '○' : '' }}</td>
            <td>{{ truck.display_order }}</td>
            <td>{{ truck.is_active ? '有効' : '無効' }}</td>
            <td>
              <button v-if="canEdit" @click="editTruck(truck)" class="btn-sm">編集</button>
              <button v-if="canEdit" @click="deleteTruck(truck.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!loading && trucks.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '便編集' : '便新規作成' }}</h2>
        <form @submit.prevent="saveTruck">
          <div class="form-group">
            <label>便名 *</label>
            <input v-model.trim="formData.name" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>俗称</label>
            <input v-model.trim="formData.alias_name" :disabled="!canEdit" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>荷台幅(mm) *</label>
              <input type="number" min="0" v-model.number="formData.width" required :disabled="!canEdit" />
            </div>
            <div class="form-group">
              <label>荷台奥行(mm) *</label>
              <input type="number" min="0" v-model.number="formData.depth" required :disabled="!canEdit" />
            </div>
            <div class="form-group">
              <label>荷台高さ(mm) *</label>
              <input type="number" min="0" v-model.number="formData.height" required :disabled="!canEdit" />
            </div>
          </div>
          <div class="form-group">
            <label>最大積載重量(kg) *</label>
            <input type="number" min="0" v-model.number="formData.max_weight" required :disabled="!canEdit" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>出発時刻 *</label>
              <input type="time" v-model="formData.departure_time" required :disabled="!canEdit" />
            </div>
            <div class="form-group">
              <label>到着時刻 *</label>
              <input type="time" v-model="formData.arrival_time" required :disabled="!canEdit" />
            </div>
            <div class="form-group">
              <label>到着日オフセット</label>
              <select v-model.number="formData.arrival_day_offset" :disabled="!canEdit">
                <option :value="0">当日着</option>
                <option :value="1">翌日着</option>
                <option :value="2">翌々日着</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>表示順</label>
            <input type="number" min="0" v-model.number="formData.display_order" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>備考</label>
            <textarea v-model.trim="formData.notes" rows="3" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.default_use" :disabled="!canEdit" />
              常用便
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" :disabled="!canEdit" />
              有効
            </label>
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
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { canAccessMasterResource } from '@/utils/masterPermissions'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'm_kubota_sakai_truck', desc: 'クボタ堺便マスタ' },
]

const trucks = ref([])
const loading = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const canEdit = computed(() => canAccessMasterResource('masters.kubota_sakai_truck', 'edit'))

const createEmptyForm = () => ({
  id: null,
  name: '',
  alias_name: '',
  width: 2400,
  depth: 9000,
  height: 2400,
  max_weight: 10000,
  departure_time: '09:00',
  arrival_time: '15:00',
  arrival_day_offset: 0,
  default_use: true,
  is_active: true,
  display_order: 0,
  notes: '',
})

const formData = ref(createEmptyForm())

const formatTime = (t) => {
  if (!t) return ''
  return String(t).slice(0, 5)
}

const getErrorMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  return fallback
}

const fetchTrucks = async () => {
  loading.value = true
  try {
    const response = await api.kubotaSakaiTrucks.getKubotaSakaiTrucks({ ordering: 'display_order,name' })
    trucks.value = response.data.results || response.data
  } catch (error) {
    console.error('便マスタ取得エラー:', error)
    alert(getErrorMessage(error, '便マスタの取得に失敗しました'))
  } finally {
    loading.value = false
  }
}

const showNewDialog = () => {
  if (!canEdit.value) return
  isEdit.value = false
  formData.value = createEmptyForm()
  showDialog.value = true
}

const editTruck = (truck) => {
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = {
    ...truck,
    departure_time: formatTime(truck.departure_time),
    arrival_time: formatTime(truck.arrival_time),
    notes: truck.notes || '',
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveTruck = async () => {
  if (!canEdit.value) return
  const payload = {
    ...formData.value,
    width: Number(formData.value.width || 0),
    depth: Number(formData.value.depth || 0),
    height: Number(formData.value.height || 0),
    max_weight: Number(formData.value.max_weight || 0),
    arrival_day_offset: Number(formData.value.arrival_day_offset || 0),
    display_order: Number(formData.value.display_order || 0),
    notes: formData.value.notes || null,
    alias_name: formData.value.alias_name || null,
  }

  try {
    if (isEdit.value) {
      await api.kubotaSakaiTrucks.updateKubotaSakaiTruck(payload.id, payload)
      alert('更新しました')
    } else {
      await api.kubotaSakaiTrucks.createKubotaSakaiTruck(payload)
      alert('作成しました')
    }
    await fetchTrucks()
    closeDialog()
  } catch (error) {
    console.error('便マスタ保存エラー:', error)
    alert(getErrorMessage(error, '保存に失敗しました'))
  }
}

const deleteTruck = async (id) => {
  if (!canEdit.value) return
  if (!confirm('本当に削除しますか？')) return
  try {
    await api.kubotaSakaiTrucks.deleteKubotaSakaiTruck(id)
    await fetchTrucks()
    alert('削除しました')
  } catch (error) {
    console.error('便マスタ削除エラー:', error)
    alert(getErrorMessage(error, '削除に失敗しました'))
  }
}

onMounted(async () => {
  await fetchTrucks()
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
  min-width: 600px;
  max-width: 800px;
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
  flex: 1;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="time"],
.form-group textarea,
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
</style>

