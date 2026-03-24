<template>
  <div class="laser-pattern-editor">
    <div class="header-row">
      <div class="search-block">
        <label>パターン検索</label>
        <input v-model.trim="searchKeyword" type="text" placeholder="パターン番号で検索" />
      </div>
      <div class="filter-block">
        <select v-model="filterEquipment" class="filter-select">
          <option value="">設備: すべて</option>
          <option v-for="eq in equipmentOptions" :key="eq.id" :value="eq.equipment_code">
            {{ eq.equipment_code }} - {{ eq.equipment_name }}
          </option>
        </select>
        <select v-model="filterMaterial" class="filter-select">
          <option value="">材料: すべて</option>
          <option v-for="code in uniqueMaterialCodes" :key="code" :value="code">{{ code }}</option>
        </select>
        <input
          v-model="filterProcessTimeMin"
          type="number"
          step="0.1"
          min="0"
          class="filter-input"
          placeholder="加工時間: 以上"
        />
        <input
          v-model="filterProcessTimeMax"
          type="number"
          step="0.1"
          min="0"
          class="filter-input"
          placeholder="加工時間: 以下"
        />
      </div>
      <div class="action-block">
        <button class="btn" type="button" @click="createNewPattern">新規</button>
        <button class="btn primary" type="button" @click="savePattern" :disabled="saving">保存</button>
        <button class="btn" type="button" @click="copyPattern" :disabled="!form.id || saving">コピー</button>
        <button class="btn warn" type="button" @click="deactivatePattern" :disabled="!form.id || saving">無効化</button>
        <button class="btn danger" type="button" @click="deletePattern" :disabled="!form.id || saving">削除</button>
      </div>
    </div>

    <div class="content-grid">
      <div class="pattern-list-panel">
        <table class="list-table">
          <thead>
            <tr>
              <th class="col-pattern-no">Ｐ№</th>
              <th>材料</th>
              <th>設備</th>
              <th class="col-time">時間(分/回)</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="pattern in filteredPatterns"
              :key="pattern.id"
              :class="{ active: form.id === pattern.id }"
              @click="selectPattern(pattern)"
            >
              <td class="col-pattern-no">{{ pattern.pattern_no }}</td>
              <td>{{ pattern.material_code }}</td>
              <td>{{ pattern.equipment_code }}</td>
              <td class="num col-time">{{ formatNumber(pattern.process_time_min) }}</td>
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
            <input v-model="form.process_time_min" type="number" step="0.1" min="0" />
          </div>
          <div class="field field-full">
            <label>材料予算用</label>
            <label class="budget-toggle">
              <input v-model="form.is_budget_target" type="checkbox" />
              <span>材料予算計算に使用する</span>
            </label>
            <div class="budget-help" :class="{ on: form.is_budget_target, off: !form.is_budget_target }">
              <template v-if="form.is_budget_target">
                ON: 材料予算計算に使用します。完成品情報を1件以上入力してください。
              </template>
              <template v-else>
                OFF: 一時パターン用です。材料予算計算には使用しません。完成品情報は入力しないでください。
              </template>
            </div>
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
                <th class="col-no">No</th>
                <th>構成部品</th>
                <th>取り数</th>
                <th class="remove-col"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in form.component_items" :key="`comp-${idx}`">
                <td class="col-no">{{ idx + 1 }}</td>
                <td>
                  <LookupSelectInput
                    v-model="item.component_product"
                    :options="allProductLookupOptions"
                    :code-only="true"
                    placeholder="部番/品名を入力"
                  />
                </td>
                <td>
                  <input v-model="item.take_qty" type="number" step="1" min="1" />
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
                <th class="col-no">No</th>
                <th>完成品番号</th>
                <th>完成品取り数</th>
                <th class="remove-col"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in form.finished_items" :key="`fin-${idx}`">
                <td class="col-no">{{ idx + 1 }}</td>
                <td>
                  <LookupSelectInput
                    v-model="item.finished_product"
                    :options="finishedProductLookupOptions"
                    placeholder="完成品番/品名を入力"
                  />
                </td>
                <td>
                  <input v-model="item.units_per_shot" type="number" step="0.1" min="0.1" />
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
const filterEquipment = ref('')
const filterMaterial = ref('')
const filterProcessTimeMin = ref('')
const filterProcessTimeMax = ref('')
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
  is_budget_target: false,
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
  return num.toFixed(1)
}

const formatIntegerInput = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return `${value ?? ''}`
  return `${Math.trunc(num)}`
}

const formatOneDecimalInput = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return `${value ?? ''}`
  return num.toFixed(1)
}

const isOneDecimal = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return false
  return Math.abs(num * 10 - Math.round(num * 10)) < 1e-9
}

const uniqueMaterialCodes = computed(() => {
  const codes = patterns.value.map((p) => String(p.material_code || '').trim()).filter(Boolean)
  return [...new Set(codes)].sort()
})

const filteredPatterns = computed(() => {
  return patterns.value.filter((item) => {
    if (searchKeyword.value) {
      const q = searchKeyword.value.toLowerCase()
      if (!String(item.pattern_no || '').toLowerCase().includes(q)) return false
    }
    if (filterEquipment.value && item.equipment_code !== filterEquipment.value) return false
    if (filterMaterial.value && item.material_code !== filterMaterial.value) return false
    const processTime = Number(item.process_time_min ?? 0)
    const minTime = Number(filterProcessTimeMin.value)
    const maxTime = Number(filterProcessTimeMax.value)
    if (filterProcessTimeMin.value !== '' && Number.isFinite(minTime) && processTime < minTime) return false
    if (filterProcessTimeMax.value !== '' && Number.isFinite(maxTime) && processTime > maxTime) return false
    return true
  })
})

const toProductLookupOption = (product) => ({
  value: product.id,
  code: product.product_code || '',
  name: product.product_name || '',
  label: `${product.product_code || ''} - ${product.product_name || ''}`,
})

const compareByCode = (a, b) => {
  const aCode = String(a?.product_code || '')
  const bCode = String(b?.product_code || '')
  return aCode.localeCompare(bCode, 'ja', { numeric: true, sensitivity: 'base' })
}

const materialLookupOptions = computed(() => materialProductOptions.value.map(toProductLookupOption))
const allProductLookupOptions = computed(() =>
  [...allProductOptions.value]
    .sort(compareByCode)
    .map(toProductLookupOption),
)
const finishedProductLookupOptions = computed(() =>
  allProductOptions.value
    .filter((item) => Boolean(item?.is_final_product) && Boolean(item?.is_active))
    .map(toProductLookupOption),
)
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
  // レーザラインの設備のみ（line_name に「レーザ」を含む）
  const allEquipments = normalizeList(equipmentsRes?.data)
  equipmentOptions.value = allEquipments.filter((eq) =>
    String(eq.line_name || '').includes('レーザ'),
  )
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
  process_time_min: formatOneDecimalInput(pattern.process_time_min ?? 0),
  is_budget_target: Boolean(pattern.is_budget_target),
  component_items: [...(pattern.component_items || [])]
    .sort((a, b) =>
      String(a?.component_product_code || '')
        .localeCompare(String(b?.component_product_code || ''), 'ja', { numeric: true, sensitivity: 'base' }),
    )
    .map((item) => ({
      component_product: item.component_product ?? null,
      take_qty: formatIntegerInput(item.take_qty ?? 0),
    })),
  finished_items: (pattern.finished_items || []).map((item) => ({
    finished_product: item.finished_product ?? null,
    units_per_shot: formatOneDecimalInput(item.units_per_shot ?? 0),
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
  if (!form.value.finished_items.length && form.value.is_budget_target) addFinishedRow()
}

const buildPayload = () => ({
  pattern_no: form.value.pattern_no,
  material: form.value.material,
  equipment: form.value.equipment,
  process_time_min: Number(Number(form.value.process_time_min).toFixed(1)),
  is_budget_target: Boolean(form.value.is_budget_target),
  component_items: form.value.component_items.map((item) => ({
    component_product: item.component_product,
    take_qty: Number.parseInt(`${item.take_qty}`, 10),
  })),
  finished_items: form.value.finished_items.map((item) => ({
    finished_product: item.finished_product,
    units_per_shot: Number(Number(item.units_per_shot).toFixed(1)),
  })),
})

const validateForm = () => {
  if (!form.value.pattern_no) return 'パターン番号を入力してください。'
  if (!form.value.material) return '使用材料を選択してください。'
  if (!form.value.equipment) return '使用設備を選択してください。'
  if (Number(form.value.process_time_min) < 0 || !isOneDecimal(form.value.process_time_min)) {
    return '加工時間は0以上の小数1桁で入力してください。'
  }

  const invalidComp = form.value.component_items.some(
    (item) => !item.component_product || Number(item.take_qty) <= 0 || !Number.isInteger(Number(item.take_qty)),
  )
  if (invalidComp) return '構成部品の部番と取り数(1以上の整数)を入力してください。'

  const hasFinishedInput = form.value.finished_items.some(
    (item) => item.finished_product || Number(item.units_per_shot) > 0,
  )
  if (form.value.is_budget_target) {
    const invalidFinished = form.value.finished_items.some(
      (item) =>
        !item.finished_product ||
        Number(item.units_per_shot) <= 0 ||
        !isOneDecimal(item.units_per_shot),
    )
    if (invalidFinished) return '材料予算用パターンは完成品情報の品番と取り数(0より大きい小数1桁)を入力してください。'
  } else if (hasFinishedInput) {
    return '材料予算用にしないパターンは完成品情報を入力できません。'
  }
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
    const resData = error?.response?.data || {}
    const firstFieldKey = Object.keys(resData).find((k) => k !== 'detail')
    const fieldMessage = firstFieldKey
      ? (Array.isArray(resData[firstFieldKey]) ? resData[firstFieldKey][0] : resData[firstFieldKey])
      : ''
    const detail = error?.response?.data?.detail || fieldMessage || '保存に失敗しました。'
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

const deactivatePattern = async () => {
  if (!form.value.id) return
  const ok = window.confirm(`パターン ${form.value.pattern_no} を無効化します。一覧から非表示になります。よろしいですか？`)
  if (!ok) return
  saving.value = true
  try {
    await api.laserPatterns.deactivateLaserPattern(form.value.id)
    await loadPatterns()
    createNewPattern()
    window.alert('無効化しました。')
  } catch (error) {
    const detail = error?.response?.data?.detail || '無効化に失敗しました。'
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
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
}
.search-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 280px;
}
.filter-block {
  display: flex;
  gap: 6px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.filter-select {
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
  font-size: 13px;
  background: #fff;
}
.filter-input {
  width: 132px;
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
  font-size: 13px;
  background: #fff;
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
.btn.warn {
  border-color: #b45309;
  color: #b45309;
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
.list-table .col-pattern-no {
  width: 56px;
  min-width: 56px;
  white-space: nowrap;
}
.list-table .col-time {
  width: 72px;
  min-width: 72px;
  white-space: nowrap;
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
.field-full {
  grid-column: 1 / -1;
}
.field input,
.field select {
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
}
.budget-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.budget-help {
  margin-top: 4px;
  font-size: 12px;
}
.budget-help.on {
  color: #065f46;
}
.budget-help.off {
  color: #334155;
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
.col-no {
  width: 36px;
  min-width: 36px;
  text-align: center;
  color: #6b7280;
  font-size: 11px;
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
