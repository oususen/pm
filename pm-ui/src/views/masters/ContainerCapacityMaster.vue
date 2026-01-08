<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">容器マスタ</h1>
      <div class="page-actions">
        <button @click="fetchContainers" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>容器名</th>
            <th>容器コード</th>
            <th>入り数</th>
            <th>サイズ</th>
            <th>最大重量</th>
            <th>混載</th>
            <th>積み重ね</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="container in containers" :key="container.id">
            <td>{{ container.name }}</td>
            <td>{{ container.container_code || '-' }}</td>
            <td>{{ container.capacity ?? '-' }}</td>
            <td>{{ formatSize(container) }}</td>
            <td>{{ container.max_weight ?? '-' }}</td>
            <td>{{ container.can_mix ? '可' : '不可' }}</td>
            <td>{{ container.stackable ? '可' : '不可' }}</td>
            <td>
              <button @click="editContainer(container)" class="btn-sm">編集</button>
              <button @click="deleteContainer(container.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="containers.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '容器編集' : '容器新規作成' }}</h2>
        <form @submit.prevent="saveContainer">
          <div class="form-group">
            <label>容器名 *</label>
            <input v-model="formData.name" required />
          </div>
          <div class="form-group">
            <label>容器コード</label>
            <input v-model="formData.container_code" />
          </div>
          <div class="form-group">
            <label>入り数</label>
            <input v-model.number="formData.capacity" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>幅</label>
            <input v-model.number="formData.width" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>奥行</label>
            <input v-model.number="formData.depth" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>高さ</label>
            <input v-model.number="formData.height" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>最大重量</label>
            <input v-model.number="formData.max_weight" type="number" min="0" />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.can_mix" />
              混載可能
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.stackable" />
              積み重ね可能
            </label>
          </div>
          <div class="form-group">
            <label>最大積み重ね段数</label>
            <input v-model.number="formData.max_stack" type="number" min="0" />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const containers = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  name: '',
  container_code: '',
  width: null,
  depth: null,
  height: null,
  max_weight: 0,
  can_mix: true,
  stackable: true,
  max_stack: 1,
  capacity: null,
})

const fetchContainers = async () => {
  try {
    const response = await api.containerCapacities.getContainerCapacities()
    containers.value = response.data.results || response.data
  } catch (error) {
    console.error('容器取得エラー:', error)
    alert('容器データの取得に失敗しました')
  }
}

const showNewDialog = () => {
  isEdit.value = false
  formData.value = {
    name: '',
    container_code: '',
    width: null,
    depth: null,
    height: null,
    max_weight: 0,
    can_mix: true,
    stackable: true,
    max_stack: 1,
    capacity: null,
  }
  showDialog.value = true
}

const editContainer = (container) => {
  isEdit.value = true
  formData.value = {
    ...container,
    container_code: container.container_code || '',
    can_mix: container.can_mix ?? true,
    stackable: container.stackable ?? true,
    max_stack: container.max_stack ?? 1,
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const normalizeNumber = (value) => {
  if (value === '' || value === null || Number.isNaN(value)) return null
  return value
}

const saveContainer = async () => {
  try {
    const payload = {
      ...formData.value,
      container_code: formData.value.container_code || null,
      width: normalizeNumber(formData.value.width),
      depth: normalizeNumber(formData.value.depth),
      height: normalizeNumber(formData.value.height),
      max_weight: normalizeNumber(formData.value.max_weight),
      max_stack: normalizeNumber(formData.value.max_stack),
      capacity: normalizeNumber(formData.value.capacity),
    }
    if (isEdit.value) {
      await api.containerCapacities.updateContainerCapacity(payload.id, payload)
      alert('更新しました')
    } else {
      await api.containerCapacities.createContainerCapacity(payload)
      alert('作成しました')
    }
    await fetchContainers()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteContainer = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.containerCapacities.deleteContainerCapacity(id)
    await fetchContainers()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

const formatSize = (container) => {
  const parts = [container.width, container.depth, container.height].filter((v) => v)
  if (!parts.length) return '-'
  return parts.join(' × ')
}

onMounted(() => {
  fetchContainers()
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
.form-group input[type="number"] {
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
</style>
