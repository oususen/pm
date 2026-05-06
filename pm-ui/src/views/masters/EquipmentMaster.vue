<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">設備マスタ</h1>
      <div class="page-actions">
        <button @click="fetchEquipments" class="btn-primary" :disabled="loading">更新</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>設備コード</th>
            <th>設備名</th>
            <th>ライン</th>
            <th>工程</th>
            <th>表示順</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="equipment in equipments" :key="equipment.id">
            <td>{{ equipment.equipment_code }}</td>
            <td>{{ equipment.equipment_name }}</td>
            <td>{{ lineLabel(equipment) }}</td>
            <td>{{ processLabel(equipment) }}</td>
            <td>{{ equipment.display_order }}</td>
            <td>{{ equipment.is_active ? '有効' : '無効' }}</td>
            <td>
              <button v-if="canEdit" @click="editEquipment(equipment)" class="btn-sm">編集</button>
              <button v-if="canEdit" @click="deleteEquipment(equipment.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!loading && equipments.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '設備編集' : '設備新規作成' }}</h2>
        <form @submit.prevent="saveEquipment">
          <div class="form-group">
            <label>設備コード *</label>
            <input v-model.trim="formData.equipment_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>設備名 *</label>
            <input v-model.trim="formData.equipment_name" required :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>ライン</label>
            <select v-model="formData.line" class="select-line" :disabled="!canEdit">
              <option :value="null">未設定</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>工程</label>
            <select v-model="formData.process" class="select-line" :disabled="!canEdit">
              <option :value="null">未設定</option>
              <option v-for="process in filteredProcesses" :key="process.id" :value="process.id">
                {{ process.process_code }} - {{ process.process_name }}
              </option>
            </select>
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
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { canAccessMasterResource } from '@/utils/masterPermissions'

const equipments = ref([])
const lines = ref([])
const processes = ref([])
const loading = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const canEdit = computed(() => canAccessMasterResource('masters.equipment', 'edit'))

const createEmptyForm = () => ({
  id: null,
  equipment_code: '',
  equipment_name: '',
  line: null,
  process: null,
  display_order: 0,
  is_active: true,
  notes: '',
})

const formData = ref(createEmptyForm())

const filteredProcesses = computed(() => {
  const selectedLineId = Number(formData.value.line || 0)
  if (!selectedLineId) return processes.value
  return processes.value.filter((process) => Number(process.line || 0) === selectedLineId)
})

watch(
  () => formData.value.line,
  () => {
    const currentProcessId = Number(formData.value.process || 0)
    if (!currentProcessId) return
    const isProcessInOptions = filteredProcesses.value.some(
      (process) => Number(process.id) === currentProcessId
    )
    if (!isProcessInOptions) {
      formData.value.process = null
    }
  }
)

const getErrorMessage = (error, fallback) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail) return detail
  return fallback
}

const fetchEquipments = async () => {
  loading.value = true
  try {
    const response = await api.equipments.getEquipments({ ordering: 'display_order,equipment_code' })
    equipments.value = response.data.results || response.data
  } catch (error) {
    console.error('設備取得エラー:', error)
    alert(getErrorMessage(error, '設備データの取得に失敗しました'))
  } finally {
    loading.value = false
  }
}

const fetchLines = async () => {
  try {
    const response = await api.lines.getLines({ ordering: 'line_code' })
    lines.value = response.data.results || response.data
  } catch (error) {
    console.error('ライン取得エラー:', error)
  }
}

const fetchProcesses = async () => {
  try {
    const response = await api.processes.getProcesses({ ordering: 'process_code' })
    processes.value = response.data.results || response.data
  } catch (error) {
    console.error('工程取得エラー:', error)
  }
}

const showNewDialog = () => {
  if (!canEdit.value) return
  isEdit.value = false
  formData.value = createEmptyForm()
  showDialog.value = true
}

const editEquipment = (equipment) => {
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = {
    ...equipment,
    line: equipment.line ?? null,
    process: equipment.process ?? null,
    notes: equipment.notes || '',
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveEquipment = async () => {
  if (!canEdit.value) return
  const payload = {
    ...formData.value,
    line: formData.value.line || null,
    process: formData.value.process || null,
    display_order: Number(formData.value.display_order || 0),
    notes: formData.value.notes || null,
  }

  try {
    if (isEdit.value) {
      await api.equipments.updateEquipment(payload.id, payload)
      alert('更新しました')
    } else {
      await api.equipments.createEquipment(payload)
      alert('作成しました')
    }
    await fetchEquipments()
    closeDialog()
  } catch (error) {
    console.error('設備保存エラー:', error)
    alert(getErrorMessage(error, '保存に失敗しました'))
  }
}

const deleteEquipment = async (id) => {
  if (!canEdit.value) return
  if (!confirm('本当に削除しますか？')) return
  try {
    await api.equipments.deleteEquipment(id)
    await fetchEquipments()
    alert('削除しました')
  } catch (error) {
    console.error('設備削除エラー:', error)
    alert(getErrorMessage(error, '削除に失敗しました'))
  }
}

const lineLabel = (equipment) => {
  if (!equipment.line) return '-'
  const line = lines.value.find((item) => Number(item.id) === Number(equipment.line))
  if (line) return `${line.line_code} - ${line.line_name}`
  return equipment.line_name || '-'
}

const processLabel = (equipment) => {
  if (!equipment.process) return '-'
  const process = processes.value.find((item) => Number(item.id) === Number(equipment.process))
  if (process) return `${process.process_code} - ${process.process_name}`
  return equipment.process_name || '-'
}

onMounted(async () => {
  await Promise.all([fetchLines(), fetchProcesses(), fetchEquipments()])
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
  max-width: 640px;
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
.form-group textarea,
.select-line {
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

