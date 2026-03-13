<template>
  <div class="laser-pattern-editor">
    <div class="header-row">
      <div class="search-block">
        <label>パターン検索</label>
        <input v-model.trim="searchKeyword" type="text" placeholder="パターン番号で検索" />
      </div>
      <div class="action-block">
        <button class="btn" type="button" @click="createNewPattern">新規</button>
        <button class="btn primary" type="button" @click="savePattern" :disabled="saving">保存</button>
        <button class="btn" type="button" @click="copyPattern" :disabled="!form.id || saving">コピー</button>
        <button class="btn danger" type="button" @click="deletePattern" :disabled="!form.id || saving">削除</button>
      </div>
    </div>

    <div class="content-grid">
      <div class="pattern-list-panel">
        <table class="list-table">
          <thead>
            <tr>
              <th>パターン番号</th>
              <th>材料</th>
              <th>設備</th>
              <th>時間(分/回)</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="pattern in filteredPatterns"
              :key="pattern.id"
              :class="{ active: form.id === pattern.id }"
              @click="selectPattern(pattern)"
            >
              <td>{{ pattern.pattern_no }}</td>
              <td>{{ pattern.material_code }}</td>
              <td>{{ pattern.equipment_code }}</td>
              <td class="num">{{ formatNumber(pattern.process_time_min) }}</td>
            </tr>
            <tr v-if="!filteredPatterns.length">
              <td colspan="4" class="empty">データがありません</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="edit-panel">
        <div class="field-grid">
          <div class="field">
            <label>パターン番号</label>
            <input v-model.trim="form.pattern_no" type="text" />
          </div>
          <div class="field">
            <label>使用材料</label>
            <LookupSelectInput
              v-model="form.material"
              :options="materialLookupOptions"
              placeholder="品番/品名を入力"
            />
          </div>
          <div class="field">
            <label>使用設備</label>
            <LookupSelectInput
              v-model="form.equipment"
              :options="equipmentLookupOptions"
              placeholder="設備コード/設備名を入力"
            />
          </div>
          <div class="field">
            <label>加工時間(分/回)</label>
            <input v-model="form.process_time_min" type="number" step="0.01" min="0" />
          </div>
        </div>

        <div class="child-section">
          <div class="section-head">
            <h4>構成部品</h4>
            <button class="btn small" type="button" @click="addComponentRow">行追加</button>
          </div>
          <table class="child-table">
            <thead>
              <tr>
                <th>構成部品</th>
                <th>取り数</th>
                <th class="remove-col"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in form.component_items" :key="`comp-${idx}`">
                <td>
                  <LookupSelectInput
                    v-model="item.component_product"
                    :options="allProductLookupOptions"
                    placeholder="部番/品名を入力"
                  />
                </td>
                <td>
                  <input v-model="item.take_qty" type="number" step="0.001" min="0" />
                </td>
                <td class="remove-col">
                  <button class="btn danger small" type="button" @click="removeComponentRow(idx)">削除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="child-section">
          <div class="section-head">
            <h4>完成品情報</h4>
            <button class="btn small" type="button" @click="addFinishedRow">行追加</button>
          </div>
          <table class="child-table">
            <thead>
              <tr>
                <th>完成品番号</th>
                <th>完成品取り数</th>
                <th class="remove-col"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in form.finished_items" :key="`fin-${idx}`">
                <td>
                  <LookupSelectInput
                    v-model="item.finished_product"
                    :options="allProductLookupOptions"
                    placeholder="完成品番/品名を入力"
                  />
                </td>
                <td>
                  <input v-model="item.units_per_shot" type="number" step="0.001" min="0" />
                </td>
                <td class="remove-col">
                  <button class="btn danger small" type="button" @click="removeFinishedRow(idx)">削除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-overlay">読込中...</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import LookupSelectInput from '@/components/LookupSelectInput.vue'

const loading = ref(false)
const saving = ref(false)
const searchKeyword = ref('')
const patterns = ref([])
const allProductOptions = ref([])
const materialProductOptions = ref([])
const equipmentOptions = ref([])

const createEmptyForm = () => ({
  id: null,
  pattern_no: '',
  material: null,
  equipment: null,
  process_time_min: '0',
  component_items: [{ component_product: null, take_qty: '0' }],
  finished_items: [{ finished_product: null, units_per_shot: '0' }],
})

const form = ref(createEmptyForm())

const normalizeList = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

const formatNumber = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return ''
  return Number.isInteger(num) ? `${num}` : `${num.toFixed(2)}`
}

const filteredPatterns = computed(() => {
  if (!searchKeyword.value) return patterns.value
  const q = searchKeyword.value.toLowerCase()
  return patterns.value.filter((item) => String(item.pattern_no || '').toLowerCase().includes(q))
})

const toProductLookupOption = (product) => ({
  value: product.id,
  code: product.product_code || '',
  name: product.product_name || '',
  label: `${product.product_code || ''} - ${product.product_name || ''}`,
})

const materialLookupOptions = computed(() => materialProductOptions.value.map(toProductLookupOption))
const allProductLookupOptions = computed(() => allProductOptions.value.map(toProductLookupOption))
const equipmentLookupOptions = computed(() =>
  equipmentOptions.value.map((equipment) => ({
    value: equipment.id,
    code: equipment.equipment_code || '',
    name: equipment.equipment_name || '',
    label: `${equipment.equipment_code || ''} - ${equipment.equipment_name || ''}`,
  })),
)

const loadMasterOptions = async () => {
  const [productsRes, equipmentsRes] = await Promise.all([
    api.products.getAllProducts(),
    api.equipments.getEquipments({ page_size: 1000, is_active: true }),
  ])
  const products = normalizeList(productsRes?.data ?? productsRes)
  allProductOptions.value = products
  materialProductOptions.value = products.filter(
    (item) => item?.category === 'MATERIAL' && Boolean(item?.is_active),
  )
  equipmentOptions.value = normalizeList(equipmentsRes?.data)
}

const loadPatterns = async () => {
  const res = await api.laserPatterns.getLaserPatterns({ page_size: 500 })
  patterns.value = normalizeList(res.data)
}

const hydrateForm = (pattern) => ({
  id: pattern.id,
  pattern_no: pattern.pattern_no || '',
  material: pattern.material ?? null,
  equipment: pattern.equipment ?? null,
  process_time_min: `${pattern.process_time_min ?? 0}`,
  component_items: (pattern.component_items || []).map((item) => ({
    component_product: item.component_product ?? null,
    take_qty: `${item.take_qty ?? 0}`,
  })),
  finished_items: (pattern.finished_items || []).map((item) => ({
    finished_product: item.finished_product ?? null,
    units_per_shot: `${item.units_per_shot ?? 0}`,
  })),
})

const selectPattern = (pattern) => {
  form.value = hydrateForm(pattern)
}

const createNewPattern = () => {
  form.value = createEmptyForm()
}

const addComponentRow = () => {
  form.value.component_items.push({ component_product: null, take_qty: '0' })
}

const removeComponentRow = (idx) => {
  form.value.component_items.splice(idx, 1)
  if (!form.value.component_items.length) addComponentRow()
}

const addFinishedRow = () => {
  form.value.finished_items.push({ finished_product: null, units_per_shot: '0' })
}

const removeFinishedRow = (idx) => {
  form.value.finished_items.splice(idx, 1)
  if (!form.value.finished_items.length) addFinishedRow()
}

const buildPayload = () => ({
  pattern_no: form.value.pattern_no,
  material: form.value.material,
  equipment: form.value.equipment,
  process_time_min: form.value.process_time_min,
  component_items: form.value.component_items.map((item) => ({
    component_product: item.component_product,
    take_qty: item.take_qty,
  })),
  finished_items: form.value.finished_items.map((item) => ({
    finished_product: item.finished_product,
    units_per_shot: item.units_per_shot,
  })),
})

const validateForm = () => {
  if (!form.value.pattern_no) return 'パターン番号を入力してください。'
  if (!form.value.material) return '使用材料を選択してください。'
  if (!form.value.equipment) return '使用設備を選択してください。'
  if (Number(form.value.process_time_min) < 0) return '加工時間は0以上で入力してください。'

  const invalidComp = form.value.component_items.some(
    (item) => !item.component_product || Number(item.take_qty) <= 0,
  )
  if (invalidComp) return '構成部品の部番と取り数(0より大きい値)を入力してください。'

  const invalidFinished = form.value.finished_items.some(
    (item) => !item.finished_product || Number(item.units_per_shot) <= 0,
  )
  if (invalidFinished) return '完成品情報の品番と取り数(0より大きい値)を入力してください。'
  return ''
}

const savePattern = async () => {
  const error = validateForm()
  if (error) {
    window.alert(error)
    return
  }
  saving.value = true
  try {
    const payload = buildPayload()
    if (form.value.id) {
      await api.laserPatterns.updateLaserPattern(form.value.id, payload)
    } else {
      await api.laserPatterns.createLaserPattern(payload)
    }
    await loadPatterns()
    const target = patterns.value.find((item) => item.pattern_no === form.value.pattern_no)
    if (target) selectPattern(target)
    window.alert('保存しました。')
  } catch (error) {
    const detail = error?.response?.data?.detail || '保存に失敗しました。'
    window.alert(detail)
  } finally {
    saving.value = false
  }
}

const copyPattern = async () => {
  if (!form.value.id) return
  const patternNo = window.prompt('コピー先のパターン番号を入力してください。')
  if (!patternNo) return
  saving.value = true
  try {
    await api.laserPatterns.copyLaserPattern(form.value.id, patternNo.trim())
    await loadPatterns()
    const copied = patterns.value.find((item) => item.pattern_no === patternNo.trim())
    if (copied) selectPattern(copied)
    window.alert('コピーしました。')
  } catch (error) {
    const detail = error?.response?.data?.detail || 'コピーに失敗しました。'
    window.alert(detail)
  } finally {
    saving.value = false
  }
}

const deletePattern = async () => {
  if (!form.value.id) return
  const ok = window.confirm(`パターン ${form.value.pattern_no} を削除します。よろしいですか？`)
  if (!ok) return
  saving.value = true
  try {
    await api.laserPatterns.deleteLaserPattern(form.value.id)
    await loadPatterns()
    createNewPattern()
    window.alert('削除しました。')
  } catch (error) {
    const detail = error?.response?.data?.detail || '削除に失敗しました。'
    window.alert(detail)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadMasterOptions(), loadPatterns()])
    if (patterns.value.length) {
      selectPattern(patterns.value[0])
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.laser-pattern-editor {
  position: relative;
  padding: 8px;
  border: 1px solid #d7dfe8;
  border-radius: 8px;
  background: #fff;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 12px;
  margin-bottom: 8px;
}
.search-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 280px;
}
.search-block input {
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
}
.action-block {
  display: flex;
  gap: 6px;
}
.btn {
  border: 1px solid #9ca3af;
  background: #fff;
  border-radius: 6px;
  height: 30px;
  padding: 0 10px;
  cursor: pointer;
}
.btn.primary {
  background: #0f766e;
  border-color: #0f766e;
  color: #fff;
}
.btn.danger {
  border-color: #b91c1c;
  color: #b91c1c;
}
.btn.small {
  height: 28px;
  font-size: 12px;
}
.content-grid {
  display: grid;
  grid-template-columns: 38% 62%;
  gap: 10px;
  min-height: 420px;
}
.pattern-list-panel {
  border: 1px solid #d7dfe8;
  border-radius: 6px;
  overflow: auto;
}
.list-table {
  width: 100%;
  border-collapse: collapse;
}
.list-table th,
.list-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 6px 8px;
  font-size: 12px;
}
.list-table th {
  position: sticky;
  top: 0;
  background: #e7edf7;
}
.list-table tr {
  cursor: pointer;
}
.list-table tr.active {
  background: #e0f2fe;
}
.list-table .num {
  text-align: right;
}
.list-table .empty {
  text-align: center;
  color: #6b7280;
}
.edit-panel {
  border: 1px solid #d7dfe8;
  border-radius: 6px;
  padding: 8px;
  overflow: auto;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field input,
.field select {
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
}
.field :deep(.lookup-select-input input) {
  height: 32px;
}
.child-section {
  margin-top: 12px;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.section-head h4 {
  margin: 0;
  font-size: 13px;
}
.child-table {
  width: 100%;
  border-collapse: collapse;
}
.child-table th,
.child-table td {
  border: 1px solid #d7dfe8;
  padding: 4px;
  font-size: 12px;
}
.child-table select,
.child-table input {
  width: 100%;
  height: 30px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0 6px;
}
.child-table :deep(.lookup-select-input input) {
  height: 30px;
  border-radius: 4px;
  padding: 0 6px;
}
.remove-col {
  width: 64px;
}
.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: 600;
}
@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
