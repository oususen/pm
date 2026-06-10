<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">製品グループマスタ <DataSourceDialog title="製品グループマスタ" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button @click="fetchProductGroups" class="btn-primary">更新</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>グループコード</th>
            <th>グループ名</th>
            <th>説明</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="group in productGroups" :key="group.id">
            <td>{{ group.group_code }}</td>
            <td>{{ group.group_name }}</td>
            <td>{{ group.description || '-' }}</td>
            <td>{{ group.is_active ? '有効' : '無効' }}</td>
            <td>
              <button v-if="canEdit" @click="editProductGroup(group)" class="btn-sm">編集</button>
              <button v-if="canEdit" @click="deleteProductGroup(group.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="productGroups.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '製品グループ編集' : '製品グループ新規作成' }}</h2>
        <form @submit.prevent="saveProductGroup">
          <div class="form-group">
            <label>グループコード *</label>
            <input v-model="formData.group_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>グループ名 *</label>
            <input v-model="formData.group_name" required :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>説明</label>
            <textarea v-model="formData.description" rows="3" :disabled="!canEdit" />
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
import { computed, ref, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { canAccessMasterResource } from '@/utils/masterPermissions'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'm_product_group', desc: '製品グループマスタ' },
]

const productGroups = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  group_code: '',
  group_name: '',
  description: '',
  is_active: true,
})
const canEdit = computed(() => canAccessMasterResource('masters.product_group', 'edit'))

const fetchProductGroups = async () => {
  try {
    const response = await api.productGroups.getProductGroups()
    productGroups.value = response.data.results || response.data
  } catch (error) {
    console.error('製品グループ取得エラー:', error)
    alert('製品グループデータの取得に失敗しました')
  }
}

const showNewDialog = () => {
  if (!canEdit.value) return
  isEdit.value = false
  formData.value = {
    group_code: '',
    group_name: '',
    description: '',
    is_active: true,
  }
  showDialog.value = true
}

const editProductGroup = (group) => {
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = { ...group }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveProductGroup = async () => {
  if (!canEdit.value) return
  try {
    const payload = {
      ...formData.value,
      description: formData.value.description || null,
    }
    if (isEdit.value) {
      await api.productGroups.updateProductGroup(payload.id, payload)
      alert('更新しました')
    } else {
      await api.productGroups.createProductGroup(payload)
      alert('作成しました')
    }
    await fetchProductGroups()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteProductGroup = async (id) => {
  if (!canEdit.value) return
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.productGroups.deleteProductGroup(id)
    await fetchProductGroups()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchProductGroups()
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
.form-group textarea {
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

