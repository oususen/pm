<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">消耗品マスタ <DataSourceDialog title="消耗品マスタ" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button class="btn-primary" :disabled="loading" @click="reload">更新</button>
        <template v-if="canEdit">
          <button class="btn-success" @click="openNew">新規</button>
          <button class="btn-secondary" @click="csvInput.click()">CSV取込</button>
          <input ref="csvInput" type="file" accept=".csv" style="display:none" @change="importCsv" />
        </template>
      </div>
    </div>

    <div class="tab-bar">
      <button :class="['tab-btn', { active: activeTab === 'items' }]" @click="switchTab('items')">消耗品</button>
      <button :class="['tab-btn', { active: activeTab === 'suppliers' }]" @click="switchTab('suppliers')">購入先</button>
    </div>

    <!-- 消耗品タブ -->
    <div v-show="activeTab === 'items'">
      <div class="filter-bar">
        <label>検索: <input v-model="itemFilters.search" placeholder="コード/発注コード/品名" @keyup.enter="fetchItems" /></label>
        <label>購入先:
          <select v-model="itemFilters.supplier" @change="fetchItems">
            <option value="">すべて</option>
            <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </label>
        <label>有効:
          <select v-model="itemFilters.is_active" @change="fetchItems">
            <option value="">すべて</option>
            <option value="true">有効</option>
            <option value="false">無効</option>
          </select>
        </label>
        <button class="btn-primary" @click="fetchItems">検索</button>
        <span class="summary">{{ items.length }}件</span>
      </div>
      <div v-if="loading" class="loading-message">読み込み中...</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>画像</th><th>コード</th><th>発注コード</th><th>品名</th><th>カテゴリ</th><th>保管場所</th>
            <th>在庫数</th><th>安全在庫</th><th>発注単位</th><th>単価</th><th>購入先</th><th>有効</th>
            <th v-if="canEdit">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id" :class="{ inactive: !item.is_active }">
            <td class="img-cell"><img v-if="item.image_url" :src="item.image_url" alt="" /></td>
            <td class="mono">{{ item.code }}</td>
            <td class="mono">{{ item.order_code }}</td>
            <td>{{ item.name }}</td>
            <td>{{ item.category }}</td>
            <td>{{ item.storage_location }}</td>
            <td class="num" :class="{ shortage: item.is_shortage }">{{ item.stock_quantity }} {{ item.unit }}</td>
            <td class="num">{{ item.safety_stock }}</td>
            <td class="num">{{ item.order_unit }}</td>
            <td class="num">{{ formatPrice(item.unit_price) }}</td>
            <td>{{ item.supplier_name }}</td>
            <td>{{ item.is_active ? '有効' : '無効' }}</td>
            <td v-if="canEdit" class="action-cell">
              <button class="btn-primary btn-sm" @click="openEdit(item)">編集</button>
              <button class="btn-delete btn-sm" @click="removeItem(item)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 購入先タブ -->
    <div v-show="activeTab === 'suppliers'">
      <div class="filter-bar"><span class="summary">{{ suppliers.length }}件</span></div>
      <table class="data-table">
        <thead>
          <tr>
            <th>購入先名</th><th>担当者</th><th>電話番号</th><th>メールアドレス</th><th>住所</th><th>備考</th><th>有効</th>
            <th v-if="canEdit">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in suppliers" :key="s.id" :class="{ inactive: !s.is_active }">
            <td>{{ s.name }}</td>
            <td>{{ s.contact_person }}</td>
            <td>{{ s.phone }}</td>
            <td>{{ s.email }}</td>
            <td>{{ s.address }}</td>
            <td>{{ s.note }}</td>
            <td>{{ s.is_active ? '有効' : '無効' }}</td>
            <td v-if="canEdit" class="action-cell">
              <button class="btn-primary btn-sm" @click="openEdit(s)">編集</button>
              <button class="btn-delete btn-sm" @click="removeSupplier(s)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 消耗品 編集ダイアログ -->
    <div v-if="dialog === 'items'" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h3>{{ form.id ? '消耗品編集' : '消耗品登録' }}</h3>
        <div class="form-grid">
          <label>コード <span class="req">*</span><input v-model="form.code" /></label>
          <label>発注コード<input v-model="form.order_code" /></label>
          <label class="wide">品名 <span class="req">*</span><input v-model="form.name" /></label>
          <label>カテゴリ<input v-model="form.category" list="category-options" /></label>
          <label>単位<input v-model="form.unit" /></label>
          <label>保管場所<input v-model="form.storage_location" list="location-options" /></label>
          <label>購入先
            <select v-model="form.supplier">
              <option :value="null">（なし）</option>
              <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </label>
          <label>在庫数
            <input v-model.number="form.stock_quantity" type="number" :disabled="!!form.id" />
            <small v-if="form.id">在庫数は入庫・出庫で変更します</small>
          </label>
          <label>安全在庫<input v-model.number="form.safety_stock" type="number" min="0" /></label>
          <label>発注単位<input v-model.number="form.order_unit" type="number" min="1" /></label>
          <label>単価<input v-model="form.unit_price" type="number" min="0" step="0.01" /></label>
          <label class="wide">備考<textarea v-model="form.note" rows="2" /></label>
          <label>有効<input v-model="form.is_active" type="checkbox" /></label>
          <label v-if="form.id">画像
            <input type="file" accept="image/*" @change="(e) => (imageFile = e.target.files[0] || null)" />
          </label>
        </div>
        <datalist id="category-options"><option v-for="c in filterOptions.categories" :key="c" :value="c" /></datalist>
        <datalist id="location-options"><option v-for="l in filterOptions.storage_locations" :key="l" :value="l" /></datalist>
        <p v-if="formError" class="error-text">{{ formError }}</p>
        <div class="modal-actions">
          <button class="btn-success" :disabled="saving" @click="saveItem">{{ saving ? '保存中...' : '保存' }}</button>
          <button class="btn-secondary" @click="closeDialog">キャンセル</button>
        </div>
      </div>
    </div>

    <!-- 購入先 編集ダイアログ -->
    <div v-if="dialog === 'suppliers'" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h3>{{ form.id ? '購入先編集' : '購入先登録' }}</h3>
        <div class="form-grid">
          <label class="wide">購入先名 <span class="req">*</span><input v-model="form.name" /></label>
          <label>担当者<input v-model="form.contact_person" /></label>
          <label>電話番号<input v-model="form.phone" /></label>
          <label class="wide">メールアドレス（注文書送信先）<input v-model="form.email" type="email" /></label>
          <label class="wide">住所<input v-model="form.address" /></label>
          <label class="wide">備考<textarea v-model="form.note" rows="2" /></label>
          <label>有効<input v-model="form.is_active" type="checkbox" /></label>
        </div>
        <p v-if="formError" class="error-text">{{ formError }}</p>
        <div class="modal-actions">
          <button class="btn-success" :disabled="saving" @click="saveSupplier">{{ saving ? '保存中...' : '保存' }}</button>
          <button class="btn-secondary" @click="closeDialog">キャンセル</button>
        </div>
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
import { errorMessage, formatPrice, rowsOf } from './consumableUtils'

const dsSources = [
  { op: '読み書き', table: 't_consumable', desc: '消耗品マスタ（在庫数を保持）' },
  { op: '読み書き', table: 't_consumable_supplier', desc: '消耗品購入先' },
  { op: '読み', table: 't_consumable_request', desc: '注文状態の導出（未完了の依頼）' },
]

const canEdit = computed(() => hasPermission(authState.user, 'consumables.masters', 'edit'))

const activeTab = ref('items')
const items = ref([])
const suppliers = ref([])
const filterOptions = ref({ categories: [], storage_locations: [] })
const itemFilters = ref({ search: '', supplier: '', is_active: 'true' })
const loading = ref(false)
const saving = ref(false)
const dialog = ref('')
const form = ref({})
const formError = ref('')
const imageFile = ref(null)
const csvInput = ref(null)


async function fetchItems() {
  loading.value = true
  try {
    const params = { page_size: 0, search: itemFilters.value.search || undefined }
    if (itemFilters.value.supplier) params.supplier = itemFilters.value.supplier
    if (itemFilters.value.is_active) params.is_active = itemFilters.value.is_active
    items.value = rowsOf(await api.consumables.listItems(params))
  } finally {
    loading.value = false
  }
}

async function fetchSuppliers() {
  suppliers.value = rowsOf(await api.consumables.listSuppliers({ page_size: 0 }))
}

async function fetchFilterOptions() {
  filterOptions.value = (await api.consumables.getFilterOptions()).data
}

function reload() {
  fetchSuppliers()
  fetchItems()
  fetchFilterOptions()
}

function switchTab(tab) {
  activeTab.value = tab
}

function openNew() {
  formError.value = ''
  imageFile.value = null
  dialog.value = activeTab.value
  form.value = activeTab.value === 'items'
    ? { code: '', order_code: '', name: '', category: '', unit: '', storage_location: '', supplier: null,
        stock_quantity: 0, safety_stock: 0, order_unit: 1, unit_price: 0, note: '', is_active: true }
    : { name: '', contact_person: '', phone: '', email: '', address: '', note: '', is_active: true }
}

function openEdit(row) {
  formError.value = ''
  imageFile.value = null
  dialog.value = activeTab.value
  form.value = { ...row }
}

function closeDialog() {
  dialog.value = ''
}

async function saveItem() {
  saving.value = true
  formError.value = ''
  try {
    const payload = { ...form.value }
    delete payload.image
    const res = form.value.id
      ? await api.consumables.updateItem(form.value.id, payload)
      : await api.consumables.createItem(payload)
    if (imageFile.value) {
      const fd = new FormData()
      fd.append('image', imageFile.value)
      await api.consumables.uploadItemImage(res.data.id, fd)
    }
    closeDialog()
    fetchItems()
    fetchFilterOptions()
  } catch (err) {
    formError.value = errorMessage(err)
  } finally {
    saving.value = false
  }
}

async function saveSupplier() {
  saving.value = true
  formError.value = ''
  try {
    if (form.value.id) await api.consumables.updateSupplier(form.value.id, form.value)
    else await api.consumables.createSupplier(form.value)
    closeDialog()
    fetchSuppliers()
  } catch (err) {
    formError.value = errorMessage(err)
  } finally {
    saving.value = false
  }
}

async function removeItem(item) {
  if (!confirm(`消耗品「${item.code} ${item.name}」を削除しますか？`)) return
  try {
    await api.consumables.deleteItem(item.id)
    fetchItems()
  } catch (err) {
    alert(errorMessage(err))
  }
}

async function removeSupplier(supplier) {
  if (!confirm(`購入先「${supplier.name}」を削除しますか？`)) return
  try {
    await api.consumables.deleteSupplier(supplier.id)
    fetchSuppliers()
  } catch (err) {
    alert(errorMessage(err))
  }
}

async function importCsv(event) {
  const file = event.target.files[0]
  event.target.value = ''
  if (!file) return
  const target = activeTab.value === 'items' ? '消耗品' : '購入先'
  if (!confirm(`${target}CSV「${file.name}」を取り込みますか？\n（一致するデータは更新、ないものは追加します）`)) return
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = activeTab.value === 'items'
      ? await api.consumables.importItemsCsv(fd)
      : await api.consumables.importSuppliersCsv(fd)
    const { created, updated, errors } = res.data
    let message = `追加: ${created}件 / 更新: ${updated}件`
    if (errors.length) message += `\nエラー: ${errors.length}件\n${errors.slice(0, 20).join('\n')}`
    alert(message)
    reload()
  } catch (err) {
    alert(errorMessage(err))
  }
}

onMounted(reload)
</script>

<style scoped>
.page-container { padding: 12px; }
.page-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 6px; }
.page-title { font-size: 1.2em; margin: 0; }
.page-actions { display: flex; gap: 6px; }
.tab-bar { display: flex; gap: 4px; border-bottom: 2px solid #1565c0; margin-bottom: 6px; }
.tab-btn { padding: 4px 14px; border: 1px solid #ccc; border-bottom: none; background: #f5f5f5; cursor: pointer; border-radius: 4px 4px 0 0; }
.tab-btn.active { background: #1565c0; color: #fff; border-color: #1565c0; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 6px; font-size: 0.85em; }
.summary { color: #555; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
.data-table th, .data-table td { padding: 3px 6px; border: 1px solid #ddd; text-align: left; }
.data-table th { background: #f5f5f5; white-space: nowrap; }
.data-table .num { text-align: right; white-space: nowrap; }
.data-table .mono { font-family: monospace; }
.data-table tr.inactive { color: #999; background: #fafafa; }
.shortage { color: #c62828; font-weight: bold; }
.img-cell img { width: 36px; height: 36px; object-fit: cover; }
.action-cell { white-space: nowrap; display: flex; gap: 4px; }
.loading-message { padding: 12px; color: #666; }
.btn-primary { background: #1565c0; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-success { background: #2e7d32; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-secondary { background: #f5f5f5; border: 1px solid #ccc; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-delete { background: #e53935; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.btn-sm { padding: 2px 8px; font-size: 0.8em; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; border-radius: 8px; padding: 16px; width: 90%; max-width: 640px; max-height: 90vh; overflow-y: auto; }
.modal-content h3 { margin: 0 0 10px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 12px; font-size: 0.85em; }
.form-grid label { display: flex; flex-direction: column; gap: 2px; }
.form-grid label.wide { grid-column: 1 / -1; }
.form-grid small { color: #888; }
.req { color: #c62828; }
.error-text { color: #c62828; white-space: pre-wrap; font-size: 0.85em; }
.modal-actions { margin-top: 10px; display: flex; gap: 8px; justify-content: flex-end; }
</style>
