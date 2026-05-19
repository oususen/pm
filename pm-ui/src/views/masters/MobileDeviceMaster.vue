<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">携帯端末管理</h1>
      <div class="page-actions">
        <template v-if="activeTab === 'list'">
          <button @click="fetchDevices" class="btn-primary" :disabled="loading">更新</button>
          <button @click="showNewDialog" class="btn-success">新規</button>
          <button @click="exportTepraCSV" class="btn-secondary">テプラCSV出力</button>
          <button @click="printChecklist" class="btn-secondary">棚卸チェックシート</button>
          <button @click="triggerImport" class="btn-secondary">Excelインポート</button>
          <button @click="exportExcel" class="btn-secondary">Excelエクスポート</button>
          <input ref="fileInput" type="file" accept=".xlsx,.xls" style="display:none" @change="handleImport" />
        </template>
        <template v-else>
          <button v-if="!docEditing" class="btn-primary" @click="startEditDoc">編集</button>
          <template v-if="docEditing">
            <button class="btn-success" @click="saveDoc" :disabled="docSaving">{{ docSaving ? '保存中...' : '保存' }}</button>
            <button class="btn-secondary" @click="cancelEditDoc">キャンセル</button>
          </template>
        </template>
      </div>
    </div>

    <!-- タブ -->
    <div class="tab-bar">
      <button :class="['tab-btn', { active: activeTab === 'list' }]" @click="activeTab = 'list'">台帳</button>
      <button :class="['tab-btn', { active: activeTab === 'regulation' }]" @click="switchDoc('regulation')">管理規定</button>
      <button :class="['tab-btn', { active: activeTab === 'inventory' }]" @click="switchDoc('inventory')">棚卸規定</button>
    </div>

    <!-- 台帳タブ -->
    <div v-show="activeTab === 'list'" class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>検索</label>
          <input v-model="filters.search" @keyup.enter="fetchDevices" placeholder="管理No./製造元/型番/場所" />
        </div>
        <div class="filter-field">
          <label>状態</label>
          <select v-model="filters.status" @change="fetchDevices">
            <option value="">すべて</option>
            <option value="ACTIVE">使用中</option>
            <option value="IDLE">遊休</option>
            <option value="DISPOSED">廃却</option>
          </select>
        </div>
        <div class="filter-field">
          <label>種別</label>
          <select v-model="filters.device_type" @change="fetchDevices">
            <option value="">すべて</option>
            <option value="T">タブレット</option>
            <option value="S">スマートフォン</option>
          </select>
        </div>
        <div class="filter-actions">
          <button @click="fetchDevices" class="btn-primary">検索</button>
          <button @click="resetFilters" class="btn-secondary">リセット</button>
        </div>
      </div>

      <div class="table-summary">
        {{ devices.length }}件
        <span v-if="selectedIds.length">（{{ selectedIds.length }}件選択中）</span>
      </div>

      <div v-if="loading" class="loading-message">読み込み中...</div>
      <template v-else>
        <table class="data-table compact">
          <thead>
            <tr>
              <th style="width:30px"><input type="checkbox" @change="toggleAll" :checked="allSelected" /></th>
              <th>管理No.</th>
              <th>種別</th>
              <th>製造元</th>
              <th>型番</th>
              <th>S/N</th>
              <th>導入年月</th>
              <th>配置場所</th>
              <th>管理責任者</th>
              <th>状態</th>
              <th>備考</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in devices" :key="d.id" :class="rowClass(d)">
              <td><input type="checkbox" :value="d.id" v-model="selectedIds" /></td>
              <td class="mono">{{ d.management_no }}</td>
              <td>{{ d.device_type === 'T' ? 'タブレット' : 'スマホ' }}</td>
              <td>{{ d.manufacturer }}</td>
              <td>{{ d.model_number }}</td>
              <td class="mono" style="font-size:0.8em">{{ d.serial_number || '-' }}</td>
              <td>{{ d.purchase_date || '-' }}</td>
              <td>{{ d.location }}</td>
              <td>{{ d.manager_name }}</td>
              <td><span class="status-chip" :class="statusClass(d.status)">{{ statusLabel(d.status) }}</span></td>
              <td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ d.note || '-' }}</td>
              <td class="action-cell">
                <button class="btn-primary btn-sm" @click="editDevice(d)">編集</button>
                <button class="btn-sm btn-delete-batch" @click="deleteDevice(d)">削除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>

    <!-- 規定タブ（閲覧・編集） -->
    <div v-show="activeTab !== 'list'" class="page-content doc-content">
      <div v-if="docLoading" class="loading-message">読み込み中...</div>
      <template v-else>
        <div v-if="docEditing" class="doc-editor-wrap">
          <textarea v-model="docEditText" class="doc-editor"></textarea>
        </div>
        <article v-else class="doc-body" v-html="renderedDoc"></article>
      </template>
    </div>

    <!-- 新規・編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content" style="max-width:500px">
        <h3>{{ editingDevice ? '端末編集' : '新規端末登録' }}</h3>
        <div class="form-grid">
          <label>
            <span>管理No. <span class="required-mark">*</span></span>
            <input v-model="form.management_no" placeholder="例: 26-10T" />
          </label>
          <label>
            <span>種別 <span class="required-mark">*</span></span>
            <select v-model="form.device_type">
              <option value="T">タブレット</option>
              <option value="S">スマートフォン</option>
            </select>
          </label>
          <label>
            <span>製造元 <span class="required-mark">*</span></span>
            <input v-model="form.manufacturer" />
          </label>
          <label>
            <span>型番 <span class="required-mark">*</span></span>
            <input v-model="form.model_number" />
          </label>
          <label>
            <span>S/N</span>
            <input v-model="form.serial_number" />
          </label>
          <label>
            <span>導入年月</span>
            <input v-model="form.purchase_date" placeholder="例: 26.4.16" />
          </label>
          <label>
            <span>配置場所 <span class="required-mark">*</span></span>
            <input v-model="form.location" />
          </label>
          <label>
            <span>管理責任者 <span class="required-mark">*</span></span>
            <input v-model="form.manager_name" />
          </label>
          <label>
            <span>状態</span>
            <select v-model="form.status">
              <option value="ACTIVE">使用中</option>
              <option value="IDLE">遊休</option>
              <option value="DISPOSED">廃却</option>
            </select>
          </label>
          <label>
            <span>備考</span>
            <input v-model="form.note" />
          </label>
        </div>
        <div class="modal-actions">
          <button class="btn-primary" @click="saveDevice" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
          <button class="btn-secondary" @click="closeDialog">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import api from '@/api/client'

const devices = ref([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const editingDevice = ref(null)
const selectedIds = ref([])
const fileInput = ref(null)
const activeTab = ref('list')

const filters = ref({ search: '', status: '', device_type: '' })
const form = ref(emptyForm())

function emptyForm() {
  return {
    management_no: '', device_type: 'T', manufacturer: '', model_number: '',
    serial_number: '', purchase_date: '', location: '', manager_name: '',
    status: 'ACTIVE', note: '',
  }
}

// --- 規定ドキュメント ---
const DOC_PATHS = {
  regulation: '端末管理/携帯端末管理規定.md',
  inventory: '端末管理/携帯端末棚卸規定.md',
}
const docRawText = ref('')
const docEditText = ref('')
const docLoading = ref(false)
const docEditing = ref(false)
const docSaving = ref(false)

const renderedDoc = computed(() => {
  if (!docRawText.value) return ''
  return DOMPurify.sanitize(marked.parse(docRawText.value))
})

async function loadDoc(tabKey) {
  const path = DOC_PATHS[tabKey]
  if (!path) return
  docLoading.value = true
  docEditing.value = false
  try {
    const res = await api.mobileDevices.readManualDoc(path)
    docRawText.value = res.data.content
  } catch {
    docRawText.value = '読み込みに失敗しました。'
  } finally {
    docLoading.value = false
  }
}

function switchDoc(tabKey) {
  activeTab.value = tabKey
  loadDoc(tabKey)
}

function startEditDoc() {
  docEditText.value = docRawText.value
  docEditing.value = true
}

function cancelEditDoc() {
  docEditing.value = false
}

async function saveDoc() {
  const path = DOC_PATHS[activeTab.value]
  if (!path) return
  docSaving.value = true
  try {
    await api.mobileDevices.writeManualDoc(path, docEditText.value)
    docRawText.value = docEditText.value
    docEditing.value = false
  } catch {
    alert('保存に失敗しました')
  } finally {
    docSaving.value = false
  }
}

// --- 台帳 ---
const allSelected = computed(() => devices.value.length > 0 && selectedIds.value.length === devices.value.length)

function toggleAll(e) {
  selectedIds.value = e.target.checked ? devices.value.map(d => d.id) : []
}

async function fetchDevices() {
  loading.value = true
  try {
    const params = {}
    if (filters.value.search) params.search = filters.value.search
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.device_type) params.device_type = filters.value.device_type
    const res = await api.mobileDevices.list(params)
    devices.value = res.data?.results || res.data || []
  } catch {
    devices.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.value = { search: '', status: '', device_type: '' }
  fetchDevices()
}

function showNewDialog() {
  editingDevice.value = null
  form.value = emptyForm()
  showDialog.value = true
}

function editDevice(d) {
  editingDevice.value = d
  form.value = { ...d }
  showDialog.value = true
}

function closeDialog() {
  showDialog.value = false
  editingDevice.value = null
}

async function saveDevice() {
  saving.value = true
  try {
    if (editingDevice.value) {
      await api.mobileDevices.update(editingDevice.value.id, form.value)
    } else {
      await api.mobileDevices.create(form.value)
    }
    closeDialog()
    await fetchDevices()
  } catch (e) {
    alert('保存に失敗しました: ' + (e.response?.data?.detail || JSON.stringify(e.response?.data) || e.message))
  } finally {
    saving.value = false
  }
}

async function deleteDevice(d) {
  if (!confirm(`${d.management_no} を削除しますか？`)) return
  try {
    await api.mobileDevices.delete(d.id)
    await fetchDevices()
  } catch {
    alert('削除に失敗しました')
  }
}

function exportTepraCSV() {
  const ids = selectedIds.value
  window.location.href = api.mobileDevices.printLabelsUrl(ids)
}

function printChecklist() {
  window.open(api.mobileDevices.inventoryChecklistUrl(), '_blank')
}

function triggerImport() {
  fileInput.value?.click()
}

async function handleImport(e) {
  const file = e.target.files[0]
  if (!file) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await api.mobileDevices.importExcel(fd)
    alert(`インポート完了: 新規${res.data.created}件, 更新${res.data.updated}件`)
    await fetchDevices()
  } catch {
    alert('インポートに失敗しました')
  }
  e.target.value = ''
}

function exportExcel() {
  window.open(api.mobileDevices.exportExcelUrl(), '_blank')
}

function statusLabel(st) {
  return { ACTIVE: '使用中', IDLE: '遊休', DISPOSED: '廃却' }[st] || st
}

function statusClass(st) {
  return { ACTIVE: 'ok', IDLE: 'warn', DISPOSED: 'ng' }[st] || ''
}

function rowClass(d) {
  if (d.status === 'DISPOSED') return 'row-disposed'
  if (d.status === 'IDLE') return 'row-idle'
  return ''
}

onMounted(fetchDevices)
</script>

<style scoped>
.page-container { padding: 16px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.page-title { font-size: 1.3em; font-weight: bold; }
.page-actions { display: flex; gap: 6px; }
.tab-bar { display: flex; gap: 0; margin-bottom: 0; border-bottom: 2px solid #1565c0; }
.tab-btn { padding: 6px 18px; border: 1px solid #ccc; border-bottom: none; background: #f5f5f5; cursor: pointer; font-size: 0.9em; border-radius: 4px 4px 0 0; margin-right: 2px; }
.tab-btn.active { background: #1565c0; color: #fff; border-color: #1565c0; font-weight: 600; }
.page-content { background: #fff; border-radius: 0 6px 6px 6px; padding: 12px; border: 1px solid #ddd; border-top: none; }
.filter-bar { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; margin-bottom: 10px; }
.filter-field { display: flex; flex-direction: column; gap: 2px; }
.filter-field label { font-size: 0.8em; color: #666; }
.filter-field input, .filter-field select { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 0.9em; }
.filter-actions { display: flex; gap: 4px; }
.table-summary { font-size: 0.85em; color: #666; margin-bottom: 6px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
.data-table th, .data-table td { padding: 4px 8px; border: 1px solid #ddd; text-align: left; }
.data-table th { background: #f5f5f5; font-weight: 600; white-space: nowrap; }
.data-table.compact td { padding: 3px 6px; }
.mono { font-family: monospace; }
.action-cell { white-space: nowrap; }
.btn-primary { background: #1565c0; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-success { background: #2e7d32; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-secondary { background: #f5f5f5; border: 1px solid #ccc; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-sm { padding: 2px 8px; font-size: 0.8em; }
.btn-delete-batch { background: #e53935; color: #fff; border: none; padding: 2px 8px; border-radius: 4px; cursor: pointer; font-size: 0.8em; }
.status-chip { padding: 1px 8px; border-radius: 10px; font-size: 0.8em; font-weight: 600; }
.status-chip.ok { background: #e8f5e9; color: #2e7d32; }
.status-chip.warn { background: #fff3e0; color: #e65100; }
.status-chip.ng { background: #fbe9e7; color: #c62828; }
.row-disposed { opacity: 0.5; }
.row-idle { background: #fffde7; }
.loading-message { padding: 20px; text-align: center; color: #999; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; border-radius: 8px; padding: 20px; width: 90%; }
.modal-content h3 { margin: 0 0 12px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.form-grid label { display: flex; flex-direction: column; gap: 2px; font-size: 0.85em; }
.form-grid input, .form-grid select { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }
.required-mark { color: #e53935; }
.modal-actions { margin-top: 12px; display: flex; gap: 8px; justify-content: flex-end; }
.doc-content { min-height: 400px; }
.doc-body { line-height: 1.7; font-size: 0.95em; }
.doc-body :deep(h1) { font-size: 1.4em; border-bottom: 2px solid #1565c0; padding-bottom: 4px; margin: 16px 0 10px; }
.doc-body :deep(h2) { font-size: 1.15em; border-bottom: 1px solid #ddd; padding-bottom: 3px; margin: 14px 0 8px; }
.doc-body :deep(h3) { font-size: 1.05em; margin: 10px 0 6px; }
.doc-body :deep(table) { border-collapse: collapse; margin: 8px 0; font-size: 0.9em; }
.doc-body :deep(th), .doc-body :deep(td) { border: 1px solid #ddd; padding: 4px 10px; }
.doc-body :deep(th) { background: #f5f5f5; }
.doc-body :deep(code) { background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 0.9em; }
.doc-body :deep(pre) { background: #f8f8f8; padding: 10px; border-radius: 4px; overflow-x: auto; }
.doc-body :deep(ul), .doc-body :deep(ol) { padding-left: 24px; }
.doc-editor-wrap { width: 100%; }
.doc-editor { width: 100%; min-height: 500px; font-family: monospace; font-size: 0.9em; padding: 10px; border: 1px solid #ccc; border-radius: 4px; resize: vertical; line-height: 1.6; }
</style>
