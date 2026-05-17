<template>
  <div class="page-container">
    <h2 class="page-title">FB外作マスタ管理</h2>

    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >{{ tab.label }}</button>
    </div>

    <!-- 外作先マスタ -->
    <div v-if="activeTab === 'subcontractor'" class="tab-content">
      <div class="form-row">
        <input v-model="subForm.name" placeholder="外作先名" class="input" />
        <input v-model.number="subForm.daily_capacity" placeholder="日キャパ" type="number" class="input input-sm" />
        <input v-model.number="subForm.transport_lt_supply" placeholder="支給運送LT" type="number" class="input input-md" />
        <input v-model.number="subForm.transport_lt_delivery" placeholder="完成品運送LT" type="number" class="input input-md" />
        <button class="btn-primary" @click="saveSub">{{ subForm.id ? '更新' : '追加' }}</button>
        <button v-if="subForm.id" class="btn-cancel" @click="resetSubForm">取消</button>
      </div>
      <table class="data-table">
        <thead><tr><th>外作先名</th><th>日キャパ</th><th>支給運送LT</th><th>完成品運送LT</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="s in subcontractors" :key="s.id">
            <td>{{ s.name }}</td>
            <td>{{ s.daily_capacity ?? '-' }}</td>
            <td>{{ s.transport_lt_supply }}日</td>
            <td>{{ s.transport_lt_delivery }}日</td>
            <td><button class="btn-edit" @click="editSub(s)">編集</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 品目マスタ -->
    <div v-if="activeTab === 'item'" class="tab-content">
      <div class="form-row">
        <input v-model="itemForm.item_code" placeholder="品目コード" class="input" />
        <input v-model="itemForm.item_name" placeholder="品目名称" class="input input-lg" />
        <select v-model.number="itemForm.subcontractor" class="input">
          <option value="">外作先選択</option>
          <option v-for="s in subcontractors" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
        <label class="field-label">納入LT</label>
        <input v-model.number="itemForm.customer_delivery_lt" placeholder="日数" type="number" class="input input-sm" />
        <button class="btn-primary" @click="saveItem">{{ itemForm.id ? '更新' : '追加' }}</button>
        <button v-if="itemForm.id" class="btn-cancel" @click="resetItemForm">取消</button>
      </div>
      <table class="data-table">
        <thead><tr><th>品目コード</th><th>品番</th><th>品名</th><th>外作先</th><th>顧客納入LT</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="it in items" :key="it.id">
            <td>{{ it.item_code }}</td>
            <td>{{ it.product_number }}</td>
            <td>{{ it.item_name }}</td>
            <td>{{ it.subcontractor_name }}</td>
            <td>{{ it.customer_delivery_lt }}日</td>
            <td><button class="btn-edit" @click="editItem(it)">編集</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 構成品マスタ -->
    <div v-if="activeTab === 'component'" class="tab-content">
      <div class="form-row">
        <input v-model="compFilterSearch" @input="fetchComponents" placeholder="コード検索" class="input" />
        <select v-model="compFilterSupplier" @change="fetchComponents" class="input">
          <option value="">全調達先</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.supplier_name }}</option>
        </select>
        <span class="badge badge-total" v-if="componentMaterials.length">{{ componentMaterials.length }}件</span>
      </div>
      <div class="form-row">
        <input v-model="compForm.material_code" placeholder="材料コード" class="input" />
        <input v-model="compForm.material_name" placeholder="材料名称" class="input input-lg" />
        <select v-model="compForm.supplier" class="input">
          <option :value="null">調達先選択</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.supplier_name }}</option>
        </select>
        <label class="field-label">調達LT</label>
        <input v-model.number="compForm.procurement_lt" placeholder="日数" type="number" class="input input-sm" />
        <button class="btn-primary" @click="saveComp">{{ compForm.id ? '更新' : '追加' }}</button>
        <button v-if="compForm.id" class="btn-cancel" @click="resetCompForm">取消</button>
      </div>
      <table v-if="componentMaterials.length" class="data-table">
        <thead><tr><th>材料コード</th><th>材料名称</th><th>調達先</th><th>調達LT</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="c in componentMaterials" :key="c.id">
            <td>{{ c.material_code }}</td>
            <td>{{ c.material_name }}</td>
            <td>{{ c.supplier_display || c.supplier_name || '-' }}</td>
            <td>{{ c.procurement_lt }}日</td>
            <td>
              <button class="btn-edit" @click="editComp(c)">編集</button>
              <button class="btn-del" @click="deleteComp(c.id)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- BOM -->
    <div v-if="activeTab === 'bom'" class="tab-content">
      <div class="form-row">
        <select v-model.number="bomFilter" @change="fetchBOM" class="input">
          <option value="">品目選択</option>
          <option v-for="it in items" :key="it.id" :value="it.id">{{ it.item_code }} {{ it.item_name }}</option>
        </select>
      </div>
      <div v-if="bomFilter" class="form-row">
        <select v-model.number="bomForm.material" class="input">
          <option :value="null">構成品選択</option>
          <option v-for="c in componentMaterials" :key="c.id" :value="c.id">{{ c.material_code }} {{ c.material_name }}</option>
        </select>
        <label class="field-label">員数</label>
        <input v-model.number="bomForm.quantity_per" placeholder="員数" type="number" step="0.0001" class="input input-sm" />
        <button class="btn-primary" @click="saveBOM">{{ bomForm.id ? '更新' : '追加' }}</button>
        <button v-if="bomForm.id" class="btn-cancel" @click="resetBOMForm">取消</button>
      </div>
      <table v-if="bomLines.length" class="data-table">
        <thead><tr><th>材料コード</th><th>材料名称</th><th>員数</th><th>調達先</th><th>調達LT</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="b in bomLines" :key="b.id">
            <td>{{ b.material_code }}</td>
            <td>{{ b.material_name }}</td>
            <td>{{ formatQty(b.quantity_per) }}</td>
            <td>{{ b.supplier_display || b.supplier_name }}</td>
            <td>{{ b.procurement_lt }}日</td>
            <td>
              <button class="btn-edit" @click="editBOM(b)">編集</button>
              <button class="btn-del" @click="deleteBOM(b.id)">削除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/client'

const tabs = [
  { id: 'subcontractor', label: '外作先' },
  { id: 'item', label: '品目' },
  { id: 'component', label: '構成品' },
  { id: 'bom', label: 'BOM' },
]
const activeTab = ref('subcontractor')

function formatQty(val) {
  const n = parseFloat(val)
  return Number.isInteger(n) ? n : n.toFixed(2)
}

// 外作先
const subcontractors = ref([])
const subForm = ref({ name: '', daily_capacity: null, transport_lt_supply: null, transport_lt_delivery: null })

function resetSubForm() { subForm.value = { name: '', daily_capacity: null, transport_lt_supply: null, transport_lt_delivery: null } }
function editSub(s) { subForm.value = { ...s } }

async function fetchSubs() {
  const res = await api.outsource.getSubcontractors()
  subcontractors.value = res.data.results || res.data
}
async function saveSub() {
  const data = { ...subForm.value }
  if (data.daily_capacity === '' || data.daily_capacity === undefined) data.daily_capacity = null
  if (data.id) {
    await api.outsource.updateSubcontractor(data.id, data)
  } else {
    await api.outsource.createSubcontractor(data)
  }
  resetSubForm()
  await fetchSubs()
}

// 品目
const items = ref([])
const itemForm = ref({ item_code: '', item_name: '', subcontractor: '', customer_delivery_lt: 2 })

function resetItemForm() { itemForm.value = { item_code: '', item_name: '', subcontractor: '', customer_delivery_lt: 2 } }
function editItem(it) { itemForm.value = { ...it } }

async function fetchItems() {
  const res = await api.outsource.getItems()
  items.value = res.data.results || res.data
}
async function saveItem() {
  if (itemForm.value.id) {
    await api.outsource.updateItem(itemForm.value.id, itemForm.value)
  } else {
    await api.outsource.createItem(itemForm.value)
  }
  resetItemForm()
  await fetchItems()
}

// 仕入れ先マスタ（既存）
const suppliers = ref([])
async function fetchSuppliers() {
  const res = await api.suppliers.getSuppliers()
  suppliers.value = res.data.results || res.data
}

// 構成品
const componentMaterials = ref([])
const compFilterSearch = ref('')
const compFilterSupplier = ref('')
const compForm = ref({ material_code: '', material_name: '', supplier: null, procurement_lt: 7 })

function resetCompForm() { compForm.value = { material_code: '', material_name: '', supplier: null, procurement_lt: 7 } }
function editComp(c) { compForm.value = { ...c } }

async function fetchComponents() {
  const params = {}
  if (compFilterSearch.value) params.search = compFilterSearch.value
  if (compFilterSupplier.value) params.supplier = compFilterSupplier.value
  const res = await api.outsource.getComponentMaterials(params)
  componentMaterials.value = res.data.results || res.data
}
async function saveComp() {
  if (compForm.value.id) {
    await api.outsource.updateComponentMaterial(compForm.value.id, compForm.value)
  } else {
    await api.outsource.createComponentMaterial(compForm.value)
  }
  resetCompForm()
  await fetchComponents()
}
async function deleteComp(id) {
  if (!confirm('削除しますか？')) return
  await api.outsource.deleteComponentMaterial(id)
  await fetchComponents()
}

// BOM
const bomFilter = ref('')
const bomLines = ref([])
const bomForm = ref({ material: null, quantity_per: 1 })

function resetBOMForm() { bomForm.value = { material: null, quantity_per: 1 } }
function editBOM(b) { bomForm.value = { ...b } }

async function fetchBOM() {
  if (!bomFilter.value) { bomLines.value = []; return }
  const res = await api.outsource.getBOMLines({ item: bomFilter.value })
  bomLines.value = res.data.results || res.data
}
async function saveBOM() {
  const data = { ...bomForm.value, item: bomFilter.value }
  if (bomForm.value.id) {
    await api.outsource.updateBOMLine(bomForm.value.id, data)
  } else {
    await api.outsource.createBOMLine(data)
  }
  resetBOMForm()
  await fetchBOM()
}
async function deleteBOM(id) {
  if (!confirm('削除しますか？')) return
  await api.outsource.deleteBOMLine(id)
  await fetchBOM()
}

onMounted(async () => {
  await Promise.all([fetchSubs(), fetchItems(), fetchSuppliers(), fetchComponents()])
})
</script>

<style scoped>
.page-container { padding: 16px; }
.page-title { font-size: 18px; margin-bottom: 12px; }

.tab-bar { display: flex; gap: 4px; margin-bottom: 12px; border-bottom: 2px solid #eee; }
.tab-btn {
  padding: 6px 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
.tab-btn.active { border-bottom-color: #1976d2; color: #1976d2; font-weight: 600; }

.form-row { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.input { padding: 4px 8px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.input-sm { width: 80px; }
.input-md { width: 120px; }
.field-label { font-size: 12px; color: #555; }
.input-lg { width: 200px; }

.btn-primary { padding: 4px 12px; background: #1976d2; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
.btn-cancel { padding: 4px 12px; background: #eee; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }
.btn-edit { padding: 2px 8px; background: #fff3e0; border: 1px solid #ffb74d; border-radius: 4px; cursor: pointer; font-size: 11px; }
.btn-del { padding: 2px 8px; background: #fbe9e7; border: 1px solid #ef9a9a; border-radius: 4px; cursor: pointer; font-size: 11px; margin-left: 4px; }

.badge { padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge-total { background: #e3f2fd; color: #1565c0; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; }
.data-table th { background: #f5f5f5; }
</style>
