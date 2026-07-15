<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">容器マスタ <DataSourceDialog title="容器マスタ" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button @click="fetchContainers" class="btn-primary">更新</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規</button>
        <button v-if="canEdit" @click="triggerImport" class="btn-secondary">荷姿設定Excel取込</button>
        <input ref="fileInput" type="file" accept=".xlsx,.xls" style="display:none" @change="handleImport" />
      </div>
    </div>

    <div v-if="importResult" class="import-result">
      <div class="import-result-header">
        <strong>反映結果</strong>
        <button class="btn-sm" @click="importResult = null">閉じる</button>
      </div>
      <p>
        反映件数: {{ importResult.updated_count }}件
        （新規作成した容器: {{ importResult.created_containers.length }}件 /
        既存容器を更新: {{ importResult.updated_containers.length }}件 /
        反映した写真: {{ importResult.image_applied_count }}枚）
      </p>
    </div>

    <div class="filter-bar">
      <label>容器名:</label>
      <input
        v-model="nameFilter"
        type="text"
        placeholder="容器名で検索"
        @keydown.enter="fetchContainers"
        class="filter-input"
      />
      <label>製品:</label>
      <input
        v-model="productFilter"
        type="text"
        placeholder="品番・品名で検索"
        @keydown.enter="fetchContainers"
        class="filter-input"
      />
      <button @click="fetchContainers" class="btn-sm">検索</button>
      <button v-if="productFilter || nameFilter" @click="productFilter = ''; nameFilter = ''; fetchContainers()" class="btn-sm btn-secondary">クリア</button>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>写真</th>
            <th>容器名</th>
            <th>容器コード</th>
            <th>入り数</th>
            <th>サイズ</th>
            <th>最大重量</th>
            <th>混載</th>
            <th>積み重ね</th>
            <th>使用製品</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="container in containers" :key="container.id">
            <td>
              <img v-if="container.image_url" :src="container.image_url" alt="容器写真" class="thumb" />
              <span v-else>-</span>
            </td>
            <td>{{ container.name }}</td>
            <td>{{ container.container_code || '-' }}</td>
            <td>{{ container.capacity ?? '-' }}</td>
            <td>{{ formatSize(container) }}</td>
            <td>{{ container.max_weight ?? '-' }}</td>
            <td>{{ container.can_mix ? '可' : '不可' }}</td>
            <td>{{ container.stackable ? '可' : '不可' }}</td>
            <td class="products-cell">
              <template v-if="container.products && container.products.length">
                <span v-for="p in container.products" :key="p.id" class="product-tag">
                  {{ p.product_code }} ({{ p.capacity }})
                </span>
              </template>
              <span v-else>-</span>
            </td>
            <td>
              <button v-if="canEdit" @click="editContainer(container)" class="btn-sm">編集</button>
              <button v-if="canEdit" @click="deleteContainer(container.id)" class="btn-sm btn-danger">削除</button>
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
            <input v-model="formData.name" required :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>写真（複数登録可）</label>
            <div class="image-upload-row">
              <input type="file" ref="imageFileInput" @change="onImageFileSelected" accept="image/*" multiple style="display:none" />
              <button type="button" class="btn-secondary" @click="triggerImageFileInput" :disabled="!canEdit || !isEdit">
                画像を選択（複数可）
              </button>
              <span v-if="!isEdit" class="import-result-warn">先に保存してからアップロードしてください</span>
            </div>
            <div class="image-gallery" v-if="formData.images && formData.images.length">
              <div class="image-gallery-item" v-for="img in formData.images" :key="img.id">
                <img :src="img.image_url" alt="容器写真" />
                <button type="button" class="btn-sm btn-danger" @click="removeImage(img.id)" :disabled="!canEdit">削除</button>
              </div>
            </div>
          </div>
          <div class="form-group">
            <label>容器コード</label>
            <input v-model="formData.container_code" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>入り数（容器デフォルト）</label>
            <input v-model.number="formData.capacity" type="number" min="0" :disabled="!canEdit" />
          </div>
          <div v-if="isEdit" class="form-group">
            <label>使用製品</label>
            <table class="pc-table" v-if="formData.product_containers && formData.product_containers.length">
              <thead><tr><th>品番</th><th>品名</th><th>入数</th></tr></thead>
              <tbody>
                <tr v-for="pc in formData.product_containers" :key="pc.id">
                  <td>{{ pc.product_code }}</td>
                  <td>{{ pc.product_name }}</td>
                  <td>{{ pc.capacity }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="helper-text">紐づく製品はありません</p>
            <p class="helper-text">※ 編集は製品マスタから行ってください</p>
          </div>
          <div class="form-group">
            <label>幅</label>
            <input v-model.number="formData.width" type="number" min="0" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>奥行</label>
            <input v-model.number="formData.depth" type="number" min="0" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>高さ</label>
            <input v-model.number="formData.height" type="number" min="0" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>最大重量</label>
            <input v-model.number="formData.max_weight" type="number" min="0" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.can_mix" :disabled="!canEdit" />
              混載可能
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.stackable" :disabled="!canEdit" />
              積み重ね可能
            </label>
          </div>
          <div class="form-group">
            <label>最大積み重ね段数</label>
            <input v-model.number="formData.max_stack" type="number" min="0" :disabled="!canEdit" />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="!canEdit">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="importPreview" class="modal-overlay">
      <div class="modal-content import-review-content">
        <h2>荷姿設定Excel取込 - 内容確認</h2>
        <p class="import-review-hint">
          各行の「容器コード」は手入力、「紐付け先」で新規作成か既存容器の更新かを選び、採用する写真にチェックを入れてから「反映する」を押してください。
        </p>

        <table class="data-table import-review-table">
          <thead>
            <tr>
              <th>品番/品名</th>
              <th>荷姿名称</th>
              <th>入数</th>
              <th>容器コード</th>
              <th>紐付け先</th>
              <th>写真</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="card in importPreview.cards" :key="card.card_key">
              <td>{{ card.product_code }}<br /><span class="sub-text">{{ card.product_name }}</span></td>
              <td>
                <input
                  v-model="importDecisions[card.card_key].container_name"
                  :disabled="!!importDecisions[card.card_key].existing_container_id"
                />
              </td>
              <td>{{ card.qty }}</td>
              <td>
                <input v-model="importDecisions[card.card_key].container_code" placeholder="任意" />
              </td>
              <td>
                <select v-model="importDecisions[card.card_key].existing_container_id" @change="onExistingContainerChange(card.card_key)">
                  <option :value="null">新規作成</option>
                  <option v-for="c in containers" :key="c.id" :value="c.id">
                    {{ c.name }}（{{ c.container_code || '-' }}）
                  </option>
                </select>
              </td>
              <td>
                <div class="import-review-images">
                  <label v-for="(img, idx) in card.images" :key="idx" class="import-review-image-item">
                    <input
                      type="checkbox"
                      :value="idx"
                      v-model="importDecisions[card.card_key].keep_image_indices"
                    />
                    <img :src="img" alt="候補写真" />
                  </label>
                  <span v-if="!card.images.length" class="sub-text">写真なし</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="importPreview.not_found.length" class="import-result-block">
          <p class="import-result-warn">品番がマスタに未登録のためスキップ（{{ importPreview.not_found.length }}件）:</p>
          <ul>
            <li v-for="item in importPreview.not_found" :key="item.product_code">
              {{ item.product_code }}（{{ item.product_name }}）
            </li>
          </ul>
        </div>
        <div v-if="importPreview.skipped_undetermined.length" class="import-result-block">
          <p class="import-result-warn">荷姿・入数が未定のためスキップ（{{ importPreview.skipped_undetermined.length }}件）:</p>
          <ul>
            <li v-for="item in importPreview.skipped_undetermined" :key="item.product_code">
              {{ item.product_code }}（{{ item.product_name }}）
            </li>
          </ul>
        </div>

        <div class="form-actions">
          <button type="button" class="btn-primary" @click="commitImport" :disabled="importCommitting">
            {{ importCommitting ? '反映中...' : '反映する' }}
          </button>
          <button type="button" class="btn-secondary" @click="cancelImportPreview" :disabled="importCommitting">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { canAccessMasterResource } from '@/utils/masterPermissions'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'm_container_capacity', desc: '容器マスタ' },
]

const containers = ref([])
const nameFilter = ref('')
const productFilter = ref('')
const showDialog = ref(false)
const isEdit = ref(false)
const fileInput = ref(null)
const imageFileInput = ref(null)
const importResult = ref(null)
const importPreview = ref(null)
const importDecisions = reactive({})
const importCommitting = ref(false)
const formData = ref({
  name: '',
  container_code: '',
  image_url: '',
  width: null,
  depth: null,
  height: null,
  max_weight: 0,
  can_mix: true,
  stackable: true,
  max_stack: 1,
  capacity: null,
})
const canEdit = computed(() => canAccessMasterResource('masters.container_capacity', 'edit'))
const newProductCode = ref('')
const newProductCapacity = ref(1)

const fetchContainers = async () => {
  try {
    const params = {}
    if (nameFilter.value) params.search = nameFilter.value
    if (productFilter.value) params.product = productFilter.value
    const response = await api.containerCapacities.getContainerCapacities(params)
    containers.value = response.data.results || response.data
  } catch (error) {
    console.error('容器取得エラー:', error)
    alert('容器データの取得に失敗しました')
  }
}

const showNewDialog = () => {
  if (!canEdit.value) return
  isEdit.value = false
  formData.value = {
    name: '',
    container_code: '',
    image_url: '',
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
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = {
    ...container,
    container_code: container.container_code || '',
    can_mix: container.can_mix ?? true,
    stackable: container.stackable ?? true,
    max_stack: container.max_stack ?? 1,
    product_containers: (container.products || []).map((p) => ({ ...p })),
  }
  newProductCode.value = ''
  newProductCapacity.value = 1
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
  if (!canEdit.value) return
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
  if (!canEdit.value) return
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

const triggerImport = () => {
  if (!canEdit.value) return
  fileInput.value?.click()
}

const triggerImageFileInput = () => {
  if (!canEdit.value || !isEdit.value) return
  imageFileInput.value?.click()
}

const onImageFileSelected = async (e) => {
  if (!canEdit.value || !isEdit.value) return
  const files = e.target.files
  if (!files || !files.length) return
  try {
    const fd = new FormData()
    for (const file of files) fd.append('files', file)
    const res = await api.containerCapacities.uploadImages(formData.value.id, fd)
    formData.value.image_url = res.data.image_url || ''
    formData.value.images = res.data.images || []
    alert('画像をアップロードしました')
  } catch (error) {
    console.error('画像アップロードエラー:', error)
    alert('画像のアップロードに失敗しました')
  } finally {
    if (imageFileInput.value) imageFileInput.value.value = ''
  }
}

const removeImage = async (imageId) => {
  if (!canEdit.value) return
  if (!confirm('この写真を削除しますか？')) return
  try {
    const res = await api.containerCapacities.deleteImage(formData.value.id, imageId)
    formData.value.image_url = res.data.image_url || ''
    formData.value.images = res.data.images || []
  } catch (error) {
    console.error('画像削除エラー:', error)
    alert('画像の削除に失敗しました')
  }
}

const handleImport = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await api.containerCapacities.importExcelPreview(fd)
    importPreview.value = res.data
    Object.keys(importDecisions).forEach((key) => delete importDecisions[key])
    for (const card of res.data.cards) {
      const exactMatch = containers.value.find((c) => c.name === card.suggested_container_name)
      importDecisions[card.card_key] = {
        container_name: card.suggested_container_name,
        container_code: exactMatch ? (exactMatch.container_code || '') : '',
        existing_container_id: exactMatch ? exactMatch.id : null,
        keep_image_indices: card.images.map((_, idx) => idx),
      }
    }
  } catch (error) {
    console.error('インポートプレビューエラー:', error)
    alert('インポートに失敗しました')
  }
  e.target.value = ''
}

const onExistingContainerChange = (cardKey) => {
  const decision = importDecisions[cardKey]
  const existing = containers.value.find((c) => c.id === decision.existing_container_id)
  if (existing) {
    decision.container_name = existing.name
    decision.container_code = existing.container_code || ''
  }
}

const cancelImportPreview = () => {
  importPreview.value = null
  Object.keys(importDecisions).forEach((key) => delete importDecisions[key])
}

const commitImport = async () => {
  if (!importPreview.value) return
  importCommitting.value = true
  try {
    const decisions = importPreview.value.cards.map((card) => {
      const d = importDecisions[card.card_key]
      return {
        card_key: card.card_key,
        mode: d.existing_container_id ? 'update' : 'create',
        existing_container_id: d.existing_container_id,
        container_name: d.container_name,
        container_code: d.container_code,
        keep_image_indices: d.keep_image_indices,
      }
    })
    const res = await api.containerCapacities.importExcelCommit({
      import_token: importPreview.value.import_token,
      decisions,
    })
    importResult.value = res.data
    cancelImportPreview()
    await fetchContainers()
  } catch (error) {
    console.error('インポート反映エラー:', error)
    alert('反映に失敗しました')
  } finally {
    importCommitting.value = false
  }
}

const addProductContainer = async () => {
  if (!canEdit.value || !formData.value.id) return
  const code = newProductCode.value.trim()
  if (!code) return
  try {
    const res = await api.containerCapacities.addProduct(formData.value.id, {
      product_code: code, capacity: newProductCapacity.value || 1,
    })
    const existing = formData.value.product_containers.find((p) => p.product_id === res.data.product_id)
    if (existing) {
      Object.assign(existing, res.data)
    } else {
      formData.value.product_containers.push(res.data)
    }
    newProductCode.value = ''
    newProductCapacity.value = 1
    await fetchContainers()
  } catch (e) {
    alert(e?.response?.data?.detail || '追加に失敗しました')
  }
}

const updateProductCapacity = async (pc) => {
  if (!canEdit.value || !formData.value.id) return
  try {
    await api.containerCapacities.updateProduct(formData.value.id, pc.id, { capacity: pc.capacity })
    await fetchContainers()
  } catch (e) {
    alert(e?.response?.data?.detail || '更新に失敗しました')
  }
}

const removeProductContainer = async (pc) => {
  if (!canEdit.value || !formData.value.id) return
  if (!confirm(`${pc.product_code} の紐付けを削除しますか？`)) return
  try {
    await api.containerCapacities.removeProduct(formData.value.id, pc.id)
    formData.value.product_containers = formData.value.product_containers.filter((p) => p.id !== pc.id)
    await fetchContainers()
  } catch (e) {
    alert(e?.response?.data?.detail || '削除に失敗しました')
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

.import-result {
  margin: 0 1rem 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background-color: #f9f9f9;
}

.import-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.import-result-block {
  margin-top: 0.5rem;
}

.import-result-warn {
  color: #b45309;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.import-result ul {
  margin: 0;
  padding-left: 1.25rem;
  max-height: 160px;
  overflow-y: auto;
}

.thumb {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.image-upload-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.image-preview {
  margin-top: 0.5rem;
}

.image-preview img {
  max-width: 200px;
  max-height: 200px;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.image-gallery {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.image-gallery-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.image-gallery-item img {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.import-review-content {
  min-width: 900px;
  max-width: 95vw;
}

.import-review-hint {
  color: #666;
  margin-bottom: 1rem;
}

.import-review-table th,
.import-review-table td {
  vertical-align: top;
  padding: 0.5rem;
}

.import-review-table input,
.import-review-table select {
  width: 100%;
  padding: 0.4rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.import-review-images {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  max-width: 260px;
}

.import-review-image-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  cursor: pointer;
}

.import-review-image-item img {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.sub-text {
  color: #888;
  font-size: 0.85em;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 1rem 8px;
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
  width: 220px;
  font-size: 13px;
}

.products-cell {
  max-width: 200px;
}

.product-tag {
  display: inline-block;
  background: #e8f0fe;
  color: #1a56db;
  border-radius: 3px;
  padding: 1px 5px;
  margin: 1px 2px;
  font-size: 11px;
  white-space: nowrap;
}

.pc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.pc-table th, .pc-table td {
  padding: 4px 6px;
  border: 1px solid #ddd;
  text-align: left;
}

.pc-table th {
  background: #f5f5f5;
  font-weight: 600;
}

.pc-capacity-input {
  width: 70px;
  padding: 3px 6px;
  border: 1px solid #ccc;
  border-radius: 3px;
}

.pc-add-row {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-top: 6px;
}

.pc-add-input {
  width: 160px;
  padding: 4px 8px;
  border: 1px solid #ccc;
  border-radius: 3px;
  font-size: 13px;
}

.btn-primary {
  background: #4a7ae5;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 4px 10px;
  cursor: pointer;
}

.helper-text {
  color: #888;
  font-size: 12px;
  margin: 4px 0;
}
</style>

