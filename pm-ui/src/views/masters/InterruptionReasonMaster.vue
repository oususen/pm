<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">中断理由マスタ</h1>
      <div class="page-actions">
        <button @click="fetchReasons" class="btn-primary">更新</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規追加</button>
      </div>
    </div>

    <div class="filter-bar">
      <label>有効/無効:</label>
      <select v-model="isActiveFilter" @change="fetchReasons" class="filter-input filter-select">
        <option value="">すべて</option>
        <option value="true">有効のみ</option>
        <option value="false">無効のみ</option>
      </select>
      <label>ライン種別:</label>
      <select v-model="lineCategoryFilter" @change="fetchReasons" class="filter-input filter-select">
        <option value="">すべて</option>
        <option v-for="c in LINE_CATEGORY_CHOICES" :key="c.value" :value="c.value">{{ c.label }}</option>
      </select>
      <label>類別:</label>
      <select v-model="categoryFilter" @change="fetchReasons" class="filter-input filter-select">
        <option value="">すべて</option>
        <option v-for="c in CATEGORY_CHOICES" :key="c.value" :value="c.value">{{ c.label }}</option>
      </select>
      <label>操作:</label>
      <select v-model="operationFilter" @change="fetchReasons" class="filter-input filter-select">
        <option value="">すべて</option>
        <option v-for="c in OPERATION_CHOICES" :key="c.value" :value="c.value">{{ c.label }}</option>
      </select>
      <label>検索（コード・表示名）:</label>
      <input
        v-model="searchText"
        type="text"
        placeholder="コードまたは表示名で検索"
        @keydown.enter="fetchReasons"
        class="filter-input"
      />
      <button @click="fetchReasons" class="btn-sm">検索</button>
      <button
        v-if="isActiveFilter || lineCategoryFilter || categoryFilter || operationFilter || searchText"
        @click="clearFilters"
        class="btn-sm btn-secondary"
      >クリア</button>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>ライン種別</th>
            <th>類別</th>
            <th>コード</th>
            <th>表示名</th>
            <th>操作</th>
            <th>表示順</th>
            <th>有効/無効</th>
            <th>編集</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="reason in reasons" :key="reason.id">
            <td>{{ lineCategoryLabel(reason.line_category) }}</td>
            <td>{{ categoryLabel(reason.category) }}</td>
            <td>{{ reason.code }}</td>
            <td>{{ reason.display_name }}</td>
            <td>{{ operationLabel(reason.operation) }}</td>
            <td>{{ reason.display_order }}</td>
            <td>{{ reason.is_active ? '有効' : '無効' }}</td>
            <td>
              <button v-if="canEdit" @click="editReason(reason)" class="btn-sm">編集</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="reasons.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '中断理由編集' : '中断理由新規作成' }}</h2>
        <form @submit.prevent="saveReason">
          <div class="form-group">
            <label>ライン種別 *</label>
            <select v-model="formData.line_category" :disabled="isEdit" required>
              <option v-for="c in LINE_CATEGORY_CHOICES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>類別 *</label>
            <select v-model="formData.category" :disabled="isEdit" required>
              <option v-for="c in CATEGORY_CHOICES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>コード（3・4桁目、0〜99） *</label>
            <input
              v-model.number="formData.codeTail"
              type="number"
              min="0"
              max="99"
              :disabled="isEdit"
              required
            />
            <p class="helper-text">コード全体: {{ composedCode }}（ライン種別・類別の桁 + 3・4桁目を結合）</p>
          </div>
          <div class="form-group">
            <label>表示名 *</label>
            <input v-model="formData.display_name" required />
          </div>
          <div class="form-group">
            <label>操作 *</label>
            <select v-model="formData.operation" :disabled="isEdit" required>
              <option v-for="c in OPERATION_CHOICES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>表示順 *</label>
            <input v-model.number="formData.display_order" type="number" required />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" />
              有効
            </label>
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
import { computed, ref, onMounted } from 'vue'
import api from '@/api/client'
import { canAccessMasterResource } from '@/utils/masterPermissions'

// モデルのchoicesと同じ内容（pm_backend/apps/masters/models.py InterruptionReason）
const LINE_CATEGORY_CHOICES = [
  { value: '1', label: '1: レーザー（予約）' },
  { value: '2', label: '2: ブレーキ・板金スポット' },
  { value: '3', label: '3: その他の一般の工程' },
]
const CATEGORY_CHOICES = [
  { value: '1', label: '1: 設備' },
  { value: '2', label: '2: 治具' },
  { value: '3', label: '3: 品質' },
  { value: '4', label: '4: 活動' },
  { value: '9', label: '9: 一般' },
]
const OPERATION_CHOICES = [
  { value: 'PAUSE', label: '中断' },
  { value: 'TEMP_END', label: '強制終了' },
]

const reasons = ref([])
const isActiveFilter = ref('')
const lineCategoryFilter = ref('')
const categoryFilter = ref('')
const operationFilter = ref('')
const searchText = ref('')

const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref(emptyFormData())

const canEdit = computed(() => canAccessMasterResource('masters.interruption_reason', 'edit'))

function emptyFormData() {
  return {
    id: null,
    line_category: '2',
    category: '1',
    codeTail: null,
    display_name: '',
    operation: 'PAUSE',
    display_order: 0,
    is_active: true,
  }
}

const composedCode = computed(() => {
  const tail = formData.value.codeTail
  if (tail === null || tail === undefined || tail === '') return `${formData.value.line_category}${formData.value.category}--`
  const tailStr = String(tail).padStart(2, '0')
  return `${formData.value.line_category}${formData.value.category}${tailStr}`
})

const lineCategoryLabel = (value) => LINE_CATEGORY_CHOICES.find((c) => c.value === value)?.label || value
const categoryLabel = (value) => CATEGORY_CHOICES.find((c) => c.value === value)?.label || value
const operationLabel = (value) => OPERATION_CHOICES.find((c) => c.value === value)?.label || value

const fetchReasons = async () => {
  try {
    const params = {}
    if (isActiveFilter.value !== '') params.is_active = isActiveFilter.value
    if (lineCategoryFilter.value) params.line_category = lineCategoryFilter.value
    if (categoryFilter.value) params.category = categoryFilter.value
    if (operationFilter.value) params.operation = operationFilter.value
    if (searchText.value) params.search = searchText.value
    const response = await api.interruptionReasons.getInterruptionReasons(params)
    reasons.value = response.data.results || response.data
  } catch (error) {
    console.error('中断理由取得エラー:', error)
    alert('中断理由データの取得に失敗しました')
  }
}

const clearFilters = () => {
  isActiveFilter.value = ''
  lineCategoryFilter.value = ''
  categoryFilter.value = ''
  operationFilter.value = ''
  searchText.value = ''
  fetchReasons()
}

const showNewDialog = () => {
  if (!canEdit.value) return
  isEdit.value = false
  formData.value = emptyFormData()
  showDialog.value = true
}

const editReason = (reason) => {
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = {
    id: reason.id,
    line_category: reason.line_category,
    category: reason.category,
    codeTail: Number(reason.code.slice(2, 4)),
    display_name: reason.display_name,
    operation: reason.operation,
    display_order: reason.display_order,
    is_active: reason.is_active,
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveReason = async () => {
  if (!canEdit.value) return
  try {
    if (isEdit.value) {
      // 作成後不変の項目（code/line_category/category/operation）は送らず、変更可能な項目のみ送る
      await api.interruptionReasons.updateInterruptionReason(formData.value.id, {
        display_name: formData.value.display_name,
        display_order: formData.value.display_order,
        is_active: formData.value.is_active,
      })
      alert('更新しました')
    } else {
      if (formData.value.codeTail === null || formData.value.codeTail === '' || formData.value.codeTail < 0 || formData.value.codeTail > 99) {
        alert('コード（3・4桁目）は0〜99の範囲で入力してください')
        return
      }
      const tailStr = String(formData.value.codeTail).padStart(2, '0')
      const code = `${formData.value.line_category}${formData.value.category}${tailStr}`
      await api.interruptionReasons.createInterruptionReason({
        code,
        display_name: formData.value.display_name,
        operation: formData.value.operation,
        display_order: formData.value.display_order,
        is_active: formData.value.is_active,
      })
      alert('作成しました')
    }
    await fetchReasons()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    const detail = error?.response?.data
    alert(typeof detail === 'object' ? JSON.stringify(detail) : '保存に失敗しました')
  }
}

onMounted(() => {
  fetchReasons()
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-bar label {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.filter-input {
  padding: 4px 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 13px;
}

.filter-select {
  min-width: 140px;
}

.btn-primary {
  background: #4a7ae5;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 4px 10px;
  cursor: pointer;
}

.btn-success {
  background: #2e9e5b;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 4px 10px;
  cursor: pointer;
}

.btn-sm {
  padding: 3px 8px;
  border: 1px solid #ccc;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
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
  min-width: 460px;
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
.form-group input[type="number"],
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

.helper-text {
  color: #888;
  font-size: 12px;
  margin: 4px 0 0;
}
</style>
