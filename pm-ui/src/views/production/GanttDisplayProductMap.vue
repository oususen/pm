<template>
  <div class="settings-container">
    <h2 class="page-title">ガントチャート生成表示品マップ 一覧</h2>
    <p class="helper-text">
      ガントチャート生成時に探索する表示品マップを管理します。新規登録や既存データ編集、同一最終品への工程追加ができます。
    </p>

    <div class="card">
      <div class="card-header">
        <div class="summary">
          <span>件数: {{ filteredRows.length }} / {{ rows.length }}</span>
          <span v-if="!canEdit" class="warn-text">閲覧モード（編集不可）</span>
        </div>
        <div class="filters">
          <label>ライン</label>
          <select v-model="lineFilter" :disabled="loading">
            <option value="">すべて</option>
            <option v-for="line in lineOptions" :key="line.id" :value="String(line.id)">
              {{ line.line_code }} - {{ line.line_name }}
            </option>
          </select>
          <input
            v-model.trim="keyword"
            type="text"
            placeholder="最終品/工程/表示品で検索"
            :disabled="loading"
          />
        </div>
        <div class="actions">
          <button class="btn" @click="reloadAll" :disabled="loading">再読込</button>
          <button class="btn primary" @click="goNew" :disabled="!canEdit || loading">新規</button>
        </div>
      </div>

      <div class="table-wrap">
        <table class="setting-table">
          <thead>
            <tr>
              <th class="col-line">ライン</th>
              <th class="col-final">ライン最終品</th>
              <th class="col-process">工程</th>
              <th class="col-display">表示品（主に連産品）</th>
              <th class="col-updated">更新</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredRows" :key="row.id" :style="{ backgroundColor: finalProductColor(row.final_product) }">
              <td>{{ formatLine(row) }}</td>
              <td>{{ formatProduct(row.final_product_code, row.final_product_name) }}</td>
              <td>{{ formatProcess(row.process_code, row.process_name) }}</td>
              <td>{{ formatProduct(row.display_product_code, row.display_product_name) }}</td>
              <td>{{ formatDateTime(row.updated_at) }}</td>
              <td class="actions-cell">
                <button class="btn small" @click="goAddProcess(row)" :disabled="!canEdit || loading">工程追加</button>
                <button class="btn small primary" @click="goEdit(row.id)" :disabled="!canEdit || loading">編集</button>
                <button class="btn small danger" @click="deleteRow(row)" :disabled="!canEdit || loading || deletingId === row.id">
                  削除
                </button>
              </td>
            </tr>
            <tr v-if="!filteredRows.length">
              <td colspan="6" class="no-data">データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const router = useRouter()

const rows = ref([])
const lineOptions = ref([])
const lineFilter = ref('')
const keyword = ref('')
const loading = ref(false)
const deletingId = ref(null)

const canEdit = computed(() => hasPermission(authState.user, 'production.plan_input', 'edit'))

// ライン最終品ごとの色分け用パレット（淡い背景色）
const FINAL_PRODUCT_COLORS = [
  '#e8f5e9', '#e3f2fd', '#fff3e0', '#f3e5f5', '#e0f7fa',
  '#fce4ec', '#f1f8e9', '#ede7f6', '#fff8e1', '#e1f5fe',
  '#fbe9e7', '#e8eaf6', '#f9fbe7', '#efebe9', '#e0f2f1',
  '#fffde7', '#f5f5f5', '#fafafa', '#eceff1', '#fff9c4',
]
const finalProductColorMap = computed(() => {
  const map = {}
  let colorIndex = 0
  // rows順に走査してユニークなfinal_productにカラーを割り当て
  for (const row of rows.value) {
    const key = row.final_product
    if (key != null && !(key in map)) {
      map[key] = FINAL_PRODUCT_COLORS[colorIndex % FINAL_PRODUCT_COLORS.length]
      colorIndex++
    }
  }
  return map
})
const finalProductColor = (finalProduct) => {
  return finalProductColorMap.value[finalProduct] || 'transparent'
}

const toArray = (res) => {
  const data = res?.data
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

const sortByCode = (a, b, codeKey, nameKey) => {
  const codeA = String(a?.[codeKey] || '')
  const codeB = String(b?.[codeKey] || '')
  if (codeA !== codeB) return codeA.localeCompare(codeB)
  return String(a?.[nameKey] || '').localeCompare(String(b?.[nameKey] || ''))
}

const formatLine = (row) => {
  const code = String(row?.line_code || '').trim()
  const name = String(row?.line_name || '').trim()
  if (code && name) return `${code} - ${name}`
  return code || name || ''
}

const formatProduct = (code, name) => {
  const codeText = String(code || '').trim()
  const nameText = String(name || '').trim()
  if (codeText && nameText) return `${codeText} - ${nameText}`
  return codeText || nameText || ''
}

const formatProcess = (code, name) => {
  const codeText = String(code || '').trim()
  const nameText = String(name || '').trim()
  if (codeText && nameText) return `${codeText} - ${nameText}`
  return codeText || nameText || ''
}

const formatDateTime = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const loadLines = async () => {
  const res = await api.lines.getLines({ is_active: true, page_size: 5000 })
  lineOptions.value = toArray(res).sort((a, b) => sortByCode(a, b, 'line_code', 'line_name'))
}

const loadRows = async () => {
  const res = await api.ganttDisplayProductMaps.getGanttDisplayProductMaps()
  rows.value = toArray(res)
}

const reloadAll = async () => {
  loading.value = true
  try {
    await Promise.all([loadLines(), loadRows()])
  } catch (error) {
    console.error('ガント表示品マップ一覧の読込に失敗しました', error)
    alert('ガント表示品マップ一覧の読込に失敗しました。')
  } finally {
    loading.value = false
  }
}

const filteredRows = computed(() => {
  const lineId = Number(lineFilter.value || 0)
  const key = String(keyword.value || '').trim().toLowerCase()

  return rows.value.filter((row) => {
    if (lineId && Number(row.line) !== lineId) return false
    if (!key) return true

    const haystack = [
      row.line_code,
      row.line_name,
      row.final_product_code,
      row.final_product_name,
      row.process_code,
      row.process_name,
      row.display_product_code,
      row.display_product_name,
    ].map((v) => String(v || '').toLowerCase())

    return haystack.some((text) => text.includes(key))
  })
})

const goNew = () => {
  router.push({ name: 'GanttDisplayProductMapCreate' })
}

const goAddProcess = (row) => {
  router.push({
    name: 'GanttDisplayProductMapCreate',
    query: {
      line: String(row.line),
      final_product: String(row.final_product),
    },
  })
}

const goEdit = (id) => {
  router.push({ name: 'GanttDisplayProductMapEdit', params: { id: String(id) } })
}

const deleteRow = async (row) => {
  if (!row?.id) return
  if (!confirm('このデータを削除しますか？')) return

  deletingId.value = row.id
  try {
    await api.ganttDisplayProductMaps.deleteGanttDisplayProductMap(row.id)
    await loadRows()
  } catch (error) {
    console.error('ガント表示品マップの削除に失敗しました', error)
    alert('削除に失敗しました。')
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped>
.settings-container {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
  color: #1f2a44;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
.page-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
}
.helper-text {
  margin: 0 0 10px;
  color: #475569;
  font-size: 12px;
}
.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.summary {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #334155;
}
.warn-text {
  color: #b45309;
}
.filters {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.filters select,
.filters input {
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
  min-width: 200px;
}
.actions {
  display: flex;
  gap: 8px;
}
.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.btn.small {
  padding: 4px 8px;
  font-size: 12px;
}
.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
.btn.danger {
  background: #fff5f5;
  color: #b91c1c;
  border-color: #fecaca;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.table-wrap {
  overflow-x: auto;
}
.setting-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.setting-table th,
.setting-table td {
  border: 1px solid #d7dfe8;
  padding: 6px 8px;
  font-size: 12px;
  color: #111;
  vertical-align: middle;
}
.setting-table thead th {
  background: #e7edf7;
}
.col-line {
  width: 220px;
}
.col-final {
  width: 300px;
}
.col-process {
  width: 220px;
}
.col-display {
  width: 300px;
}
.col-updated {
  width: 150px;
}
.col-actions {
  width: 240px;
}
.actions-cell {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.no-data {
  text-align: center;
  color: #6b7280;
  padding: 10px 0;
}
@media (max-width: 1024px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .summary {
    flex-direction: column;
    gap: 4px;
  }
}
</style>

