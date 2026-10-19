<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2>進度監視</h2>
        <p>お気に入りのグループに所属するラインについて、登録製品の進度を工程別に表示します。</p>
      </div>
      <div class="actions">
        <fieldset class="unit-checkboxes">
          <legend>グループ（複数選択可）</legend>
          <label v-for="unit in units" :key="unit.id" class="unit-checkbox">
            <input type="checkbox" :value="String(unit.id)" v-model="selectedUnitIds" @change="loadSnapshot" />{{ unit.name }}
          </label>
        </fieldset>
        <label>開始日 <input v-model="startDate" type="date" @change="loadSnapshot" /></label>
        <label>期間
          <select v-model.number="horizon" @change="loadSnapshot">
            <option :value="30">30日</option><option :value="60">60日</option>
            <option :value="90">90日</option><option :value="120">120日</option>
          </select>
        </label>
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">お気に入り選択</option>
          <option v-for="favorite in favorites" :key="favorite.id" :value="String(favorite.id)">{{ favorite.name }}</option>
        </select>
        <input v-model.trim="favoriteName" type="text" placeholder="お気に入り名" />
        <button class="favorite" type="button" title="お気に入り保存" @click="saveFavorite">★</button>
        <button type="button" @click="viewMode = viewMode === 'compact' ? 'full' : 'compact'">{{ viewMode === 'compact' ? '詳細表示' : '簡易表示' }}</button>
        <button type="button" :disabled="loading || !selectedUnitIds.length" @click="loadSnapshot">更新</button>
        <button v-if="canEdit" type="button" :disabled="loading || recalculating || !snapshot?.rows?.length" @click="recalculateVisibleProducts">表示品番だけ再計算</button>
        <button v-if="canEdit" type="button" :disabled="!selectedUnitIds.length" @click="openAdd">監視対象追加</button>
        <button v-if="canEdit" type="button" :disabled="!snapshot" @click="showManagement = !showManagement">対象管理</button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading" class="message">読込中...</p>
    <div v-else-if="snapshot">
      <div class="summary">グループ: {{ snapshot.units.map((unit) => unit.name).join('、') }} ／ 期間: {{ snapshot.start_date }} ～ {{ snapshot.end_date }} ／ {{ snapshot.rows.length }}カード</div>
      <div v-if="canEdit && showManagement" class="management-panel">
        <h3>監視対象管理</h3>
        <table class="management-table">
          <thead><tr><th>モード</th><th>ライン</th><th>品番</th><th>品名</th><th>表示順</th><th>メモ</th><th>状態</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="target in snapshot.targets" :key="target.target_id" :class="{ inactive: !target.is_active }">
              <td>{{ monitorTypeLabels[target.monitor_type] || '進度' }}</td>
              <td>{{ target.line_code }} {{ target.line_name }}</td><td>{{ target.product_code }}</td><td>{{ target.product_name }}</td>
              <td class="number">{{ target.display_order }}</td><td>{{ target.memo }}</td><td>{{ target.is_active ? '有効' : '無効' }}</td>
              <td><button type="button" @click="openEdit(target)">{{ target.is_active ? '編集' : '再有効化・編集' }}</button></td>
            </tr>
            <tr v-if="!snapshot.targets?.length"><td colspan="8" class="empty">登録済みの監視対象がありません。</td></tr>
          </tbody>
        </table>
      </div>

      <div v-if="snapshot.rows.length" class="card-scroll">
        <div class="card-list">
        <div v-for="row in snapshot.rows" :key="`${row.target_id}-${row.process_id ?? 'none'}`" class="progress-card">
          <div class="info-block">
            <div class="info-row"><span class="info-label">モード</span><span>{{ monitorTypeLabels[row.monitor_type] || '進度' }}</span></div>
            <div class="info-row"><span class="info-label">ライン</span><span>{{ formatLine(row) }}</span></div>
            <div class="info-row"><span class="info-label">工程</span><span>{{ formatProcess(row) }}</span></div>
            <div class="info-row"><span class="info-label">品番</span><span>{{ row.product_code }}</span></div>
            <div class="info-row"><span class="info-label">品名</span><span>{{ row.product_name || '-' }}</span></div>
            <div class="info-row memo-row"><span class="info-label">メモ</span><span>{{ row.memo || '-' }}</span></div>
          </div>
          <div class="matrix-wrap">
            <table class="matrix-table">
              <thead><tr><th class="label-col">項目</th><th v-for="day in snapshot.dates" :key="day">{{ formatDay(day) }}</th></tr></thead>
              <tbody>
                <tr v-for="definition in rowDefinitionsFor(row)" :key="definition.key">
                  <th class="label-col">{{ definition.label }}</th>
                  <td v-for="day in snapshot.dates" :key="`${definition.key}-${day}`" class="number" :class="cellClass(row, day, definition.key)">
                    {{ displayCell(row, day, definition) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        </div>
      </div>
      <div v-else class="empty">監視対象がありません。</div>
    </div>

    <div v-if="editorOpen" class="modal-backdrop" @click.self="closeEditor">
      <form class="modal" @submit.prevent="saveTarget">
        <h3>{{ editingId ? '監視対象編集' : '監視対象追加' }}</h3>
        <label>監視モード<select v-model="form.monitor_type" required><option value="progress">進度</option><option value="inventory">在庫</option></select></label>
        <label>対象グループ
          <select v-model="targetUnitId" @change="form.line = ''">
            <option v-for="unitId in selectedUnitIds" :key="unitId" :value="unitId">{{ unitNameById(unitId) }}</option>
          </select>
        </label>
        <label>ライン<select v-model="form.line" required><option value="">選択してください</option><option v-for="line in modalLines" :key="line.id" :value="String(line.id)">{{ line.line_code }} {{ line.line_name }}</option></select></label>
        <label>製品検索<input v-model.trim="productSearch" type="text" placeholder="品番・品名" @input="searchProducts" /></label>
        <label>製品<select v-model="form.product" required :disabled="Boolean(editingId)"><option value="">選択してください</option><option v-for="product in products" :key="product.id" :value="String(product.id)">{{ product.product_code }} {{ product.product_name }}</option></select></label>
        <label>表示順<input v-model.number="form.display_order" type="number" /></label>
        <label>メモ<input v-model="form.memo" type="text" maxlength="500" /></label>
        <label class="checkbox"><input v-model="form.is_active" type="checkbox" /> 有効</label>
        <p v-if="editorError" class="error">{{ editorError }}</p>
        <div class="modal-actions"><button type="button" @click="closeEditor">閉じる</button><button v-if="editingId && form.is_active" type="button" class="danger" @click="deactivateTarget">無効化</button><button type="submit" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button></div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const FAVORITE_SCREEN_KEY = 'production.progress_monitor'
const units = ref([])
const linesByUnit = ref({})
const selectedUnitIds = ref([])
const targetUnitId = ref('')
const startDate = ref(initialMonthStart())
const horizon = ref(30)
const favorites = ref([])
const selectedFavoriteId = ref('')
const favoriteName = ref('')
const snapshot = ref(null)
const products = ref([])
const productSearch = ref('')
const loading = ref(false)
const recalculating = ref(false)
const saving = ref(false)
const error = ref('')
const editorError = ref('')
const editorOpen = ref(false)
const editingId = ref(null)
const showManagement = ref(false)
let searchTimer = null

// 計進・進度・計庫・在庫はモードを問わず常に表示する共通項目
const COMMON_ROWS = [
  { key: 'planned_progress', label: '計進', showZero: true },
  { key: 'progress', label: '進度', showZero: true },
  { key: 'planned_stock', label: '計庫', showZero: true },
  { key: 'stock', label: '在庫', showZero: true },
]
const EXTRA_ROWS_BY_TYPE = {
  progress: [
    { key: 'forecast', label: '内示' }, { key: 'firm', label: '確定' },
    { key: 'plan', label: '計画' }, { key: 'actual', label: '実績' },
    { key: 'adjust', label: '調整' },
  ],
  inventory: [
    { key: 'forecast', label: '計需' }, { key: 'firm', label: '実需' },
    { key: 'plan', label: '計画' }, { key: 'actual', label: '実績' },
    { key: 'adjust', label: '調整' }, { key: 'scrap', label: '仕損' },
  ],
}
const monitorTypeLabels = { progress: '進度', inventory: '在庫' }
const viewMode = ref('compact') // 'compact': 共通4項目のみ / 'full': モード別項目も表示
function rowDefinitionsFor(row) {
  const extraRows = EXTRA_ROWS_BY_TYPE[row.monitor_type] || EXTRA_ROWS_BY_TYPE.progress
  if (viewMode.value === 'full') return [...extraRows, ...COMMON_ROWS]
  return COMMON_ROWS
}
const form = reactive({ monitor_type: 'progress', product: '', line: '', display_order: 0, memo: '', is_active: true })

function localDateString(value) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
function initialMonthStart() { const value = new Date(); value.setDate(1); return localDateString(value) }

const canEdit = computed(() => hasPermission(authState.user, 'production.progress_monitor', 'edit'))
const modalLines = computed(() => linesByUnit.value[String(targetUnitId.value)] || [])
function unitNameById(unitId) {
  const unit = units.value.find((item) => String(item.id) === String(unitId))
  return unit ? unit.name : ''
}

function formatDay(value) { const [, month, day] = String(value).split('-'); return `${Number(month)}/${Number(day)}` }
function formatLine(row) { return [row.line_code, row.line_name].filter(Boolean).join(' ') || '-' }
function formatProcess(row) { return [row.process_code, row.process_name].filter(Boolean).join(' ') || 'データなし' }
function displayCell(row, day, definition) {
  const cell = row.cells?.[day]
  if (!cell) return ''
  const value = Number(cell[definition.key] ?? 0)
  if (value === 0 && !definition.showZero) return ''
  return value.toLocaleString('ja-JP')
}
function cellClass(row, day, key) {
  const value = Number(row.cells?.[day]?.[key] ?? 0)
  if (key === 'adjust' && value < 0) return 'negative'
  if (['planned_progress', 'progress', 'stock', 'planned_stock'].includes(key) && value < 0) return 'negative-strong'
  return ''
}

async function loadOptions() {
  const response = await api.progressMonitor.getOptions()
  units.value = response.data.units || []
  linesByUnit.value = response.data.lines_by_unit || {}
  if (!selectedUnitIds.value.length && units.value.length === 1) selectedUnitIds.value = [String(units.value[0].id)]
}
async function loadFavorites() {
  const response = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY })
  favorites.value = Array.isArray(response.data) ? response.data : response.data?.results || []
}
async function loadSnapshot() {
  if (!selectedUnitIds.value.length || !startDate.value) { snapshot.value = null; return }
  loading.value = true
  error.value = ''
  try {
    const response = await api.progressMonitor.getSnapshot({ unit_ids: selectedUnitIds.value, start_date: startDate.value, horizon: horizon.value })
    snapshot.value = response.data
  } catch (e) { error.value = e?.response?.data?.detail || e?.message || '進度の取得に失敗しました。' }
  finally { loading.value = false }
}
function getDisplayedLineTargets() {
  const map = new Map()
  for (const row of snapshot.value?.rows || []) {
    if (!row.line_id || !row.product_id) continue
    if (!map.has(row.line_id)) {
      map.set(row.line_id, { line_id: row.line_id, product_ids: new Set(), product_codes: new Set() })
    }
    const entry = map.get(row.line_id)
    entry.product_ids.add(row.product_id)
    if (row.product_code) entry.product_codes.add(row.product_code)
  }
  return Array.from(map.values()).map((entry) => ({
    line_id: entry.line_id,
    product_ids: Array.from(entry.product_ids).sort((a, b) => a - b),
    product_codes: Array.from(entry.product_codes).sort(),
  }))
}
function buildVisibleProductConfirmMessage(targets) {
  const allCodes = targets.flatMap((target) => target.product_codes)
  const preview = allCodes.slice(0, 10).join(', ')
  const suffix = allCodes.length > 10 ? ` ほか${allCodes.length - 10}件` : ''
  return `表示中の${allCodes.length}件を再計算しますか？\n${preview}${suffix}`
}
async function recalculateVisibleProducts() {
  if (!canEdit.value) return
  const targets = getDisplayedLineTargets()
  if (!targets.length) { window.alert('再計算対象の品番がありません。'); return }
  if (!window.confirm(buildVisibleProductConfirmMessage(targets))) return
  recalculating.value = true
  error.value = ''
  try {
    const start = snapshot.value.start_date
    const end = snapshot.value.end_date
    await Promise.all(
      targets.map((target) =>
        api.lineBacklogs.pickupForProducts({ line_id: target.line_id, start_date: start, end_date: end, product_ids: target.product_ids })
      )
    )
    await Promise.all(
      targets.map((target) =>
        api.lineBacklogs.recalculateScrapForProducts({ line_id: target.line_id, start_date: start, end_date: end, product_ids: target.product_ids })
      )
    )
    await Promise.all(
      targets.map((target) =>
        api.lineBacklogs.recalculateInventoryForProducts({ line_id: target.line_id, start_date: start, end_date: end, product_ids: target.product_ids })
      )
    )
    await loadSnapshot()
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || '表示品番の再計算に失敗しました。'
  } finally {
    recalculating.value = false
  }
}
function applyFavorite() {
  const favorite = favorites.value.find((item) => String(item.id) === selectedFavoriteId.value)
  if (!favorite) return
  favoriteName.value = favorite.name || ''
  selectedUnitIds.value = (favorite.payload?.unit_ids || []).map(String)
  loadSnapshot()
}
async function saveFavorite() {
  if (!favoriteName.value || !selectedUnitIds.value.length) { window.alert('グループとお気に入り名を入力してください。'); return }
  const payload = { screen_key: FAVORITE_SCREEN_KEY, name: favoriteName.value, payload: { unit_ids: selectedUnitIds.value.map(Number) } }
  try {
    if (selectedFavoriteId.value) await api.accounts.updateFavorite(selectedFavoriteId.value, payload)
    else await api.accounts.createFavorite(payload)
    await loadFavorites()
    const saved = favorites.value.find((item) => item.name === favoriteName.value)
    selectedFavoriteId.value = saved ? String(saved.id) : ''
    window.alert('お気に入りを保存しました。')
  } catch (e) { window.alert(e?.response?.data?.detail || 'お気に入りの保存に失敗しました。') }
}
async function fetchProducts() { const response = await api.progressMonitor.getProductCandidates({ search: productSearch.value }); products.value = response.data || [] }
function searchProducts() { window.clearTimeout(searchTimer); searchTimer = window.setTimeout(fetchProducts, 250) }
function resetForm() {
  Object.assign(form, { monitor_type: 'progress', product: '', line: modalLines.value[0] ? String(modalLines.value[0].id) : '', display_order: 0, memo: '', is_active: true })
  editingId.value = null; editorError.value = ''; productSearch.value = ''
}
async function openAdd() {
  targetUnitId.value = selectedUnitIds.value[0] || ''
  resetForm(); await fetchProducts(); editorOpen.value = true
}
function openEdit(target) {
  editingId.value = target.target_id
  targetUnitId.value = selectedUnitIds.value.find(
    (unitId) => (linesByUnit.value[unitId] || []).some((line) => line.id === target.line_id),
  ) || selectedUnitIds.value[0] || ''
  Object.assign(form, { monitor_type: target.monitor_type || 'progress', product: String(target.product_id), line: String(target.line_id), display_order: target.display_order, memo: target.memo || '', is_active: target.is_active })
  productSearch.value = target.product_code
  products.value = [{ id: target.product_id, product_code: target.product_code, product_name: target.product_name }]
  editorError.value = ''; editorOpen.value = true
}
function closeEditor() { editorOpen.value = false }
async function saveTarget() {
  if (!canEdit.value) return
  saving.value = true; editorError.value = ''
  const payload = { monitor_type: form.monitor_type, product: Number(form.product), line: Number(form.line), display_order: Number(form.display_order || 0), memo: form.memo || '', is_active: Boolean(form.is_active) }
  try {
    if (editingId.value) await api.progressMonitor.updateTarget(editingId.value, payload)
    else await api.progressMonitor.createTarget(payload)
    closeEditor(); await loadSnapshot()
  } catch (e) {
    const data = e?.response?.data
    editorError.value = data?.detail || data?.non_field_errors?.[0] || '保存に失敗しました。同じライン・製品が登録済みでないか確認してください。'
  } finally { saving.value = false }
}
async function deactivateTarget() { if (!window.confirm('この監視対象を無効にしますか？')) return; form.is_active = false; await saveTarget() }

onMounted(async () => {
  try { await Promise.all([loadOptions(), loadFavorites()]); if (selectedUnitIds.value.length) await loadSnapshot() }
  catch (e) { error.value = e?.response?.data?.detail || e?.message || '初期データの取得に失敗しました。' }
})
</script>

<style scoped>
.page-container { padding: 10px; }
.page-header { display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; }
h2 { margin: 0 0 3px; font-size: 20px; } p { margin: 0; }
.actions { display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; align-items: end; }
label { display: flex; gap: 4px; align-items: center; font-weight: 600; }
.unit-checkboxes { display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: center; border: 1px solid #ccc; border-radius: 3px; padding: 2px 8px; margin: 0; }
.unit-checkboxes legend { font-size: 11px; font-weight: 600; padding: 0 2px; }
.unit-checkbox { display: flex; gap: 3px; align-items: center; font-weight: normal; font-size: 13px; }
input, select, button { min-height: 30px; font-size: 13px; } button { cursor: pointer; }
.favorite { background: #ffc800; border: 1px solid #d7a900; border-radius: 3px; }
.summary { margin: 8px 0 5px; font-weight: 600; }
.management-panel { margin: 6px 0 10px; padding: 8px; border: 1px solid #aaa; background: #fffdf0; overflow: auto; }
.management-panel h3 { margin: 0 0 6px; font-size: 15px; }
.management-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.management-table th, .management-table td { border: 1px solid #aaa; padding: 5px 7px; white-space: nowrap; }
.management-table th { background: #e8ebf8; } .inactive { color: #777; background: #eee; }
.card-scroll { overflow-x: auto; }
.card-list { display: grid; gap: 10px; width: max-content; min-width: 100%; }
.progress-card { display: grid; grid-template-columns: 260px 1fr; width: max-content; min-width: 100%; border: 1px solid #aaa; background: #fff; }
.info-block { position: sticky; left: 0; z-index: 4; padding: 7px; background: #f7f8fc; border-right: 1px solid #aaa; }
.info-row { display: grid; grid-template-columns: 55px minmax(0, 1fr); gap: 6px; padding: 4px 2px; border-bottom: 1px solid #ddd; font-size: 13px; }
.info-label { font-weight: 700; } .memo-row span:last-child { white-space: normal; overflow-wrap: anywhere; }
.matrix-wrap { overflow: visible; }
.matrix-table { border-collapse: collapse; width: max-content; min-width: 100%; font-size: 12px; }
.matrix-table th, .matrix-table td { min-width: 64px; height: 27px; padding: 3px 6px; border: 1px solid #d2d2d2; white-space: nowrap; }
.matrix-table thead th { background: #e8ebf8; text-align: center; }
.matrix-table .label-col { position: sticky; left: 0; z-index: 2; min-width: 52px; background: #f4f5f8; text-align: left; }
.matrix-table thead .label-col { z-index: 3; background: #e8ebf8; }
.number { text-align: right; } .negative { color: #c53030; background: #fff2f2; font-weight: 700; }
.negative-strong { color: #b91c1c; background: #ffe4e6; font-weight: 700; }
.empty, .message { text-align: center; padding: 20px; } .error { color: #c40000; margin: 8px 0; }
.modal-backdrop { position: fixed; inset: 0; background: #0008; display: grid; place-items: center; z-index: 1000; }
.modal { width: min(520px, calc(100vw - 24px)); background: white; padding: 16px; border-radius: 6px; display: grid; gap: 10px; }
.modal h3 { margin: 0; } .modal label { display: grid; grid-template-columns: 95px 1fr; }
.checkbox { display: flex !important; } .modal-actions { display: flex; justify-content: flex-end; gap: 6px; } .danger { color: #b00000; }
@media (max-width: 900px) { .page-header { flex-direction: column; } .actions { justify-content: flex-start; } .progress-card { grid-template-columns: 210px minmax(0, 1fr); } }
</style>
