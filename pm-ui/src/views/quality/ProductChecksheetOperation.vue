<template>
  <div class="page-container checksheet-operation" v-if="canView">
    <div class="page-header">
      <h2 class="page-title">チェック実施</h2>
      <div class="page-actions">
        <button class="btn-secondary" @click="refreshBatches" :disabled="loadingBatches">更新</button>
      </div>
    </div>

    <section class="panel filter-panel">
      <label>
        ライン
        <select v-model="selectedLine" :disabled="loadingBatches">
          <option value="">選択してください</option>
          <option v-for="l in lineOptions" :key="l.id" :value="l.id">{{ l.line_code }} - {{ l.line_name }}</option>
        </select>
      </label>
      <label>
        工程
        <select v-model="selectedProcess" :disabled="!selectedLine || loadingBatches">
          <option value="">{{ selectedLine ? '選択してください' : 'ラインを先に選択' }}</option>
          <option v-for="p in filteredProcesses" :key="p.id" :value="p.id">{{ p.process_code }} - {{ p.process_name }}</option>
        </select>
      </label>
      <label>
        製品
        <select v-model="selectedProduct" :disabled="!selectedLine || !selectedProcess || loadingProducts">
          <option value="">{{ loadingProducts ? '読込中...' : (productOptions.length ? '選択してください' : 'テンプレートなし') }}</option>
          <option v-for="p in productOptions" :key="p.id" :value="p.id">{{ p.product_code }} - {{ p.product_name }}</option>
        </select>
      </label>
      <div class="template-status">
        <span v-if="checkingTemplate" class="status-note">テンプレート確認中...</span>
        <span v-else-if="activeTemplate" class="status-chip ok">
          テンプレート: {{ activeTemplate.document_title || activeTemplate.name }} v{{ activeTemplate.version }}
        </span>
        <span v-else-if="selectedLine && selectedProcess && selectedProduct" class="status-chip danger">
          承認済みテンプレートがありません
        </span>
      </div>
    </section>

    <section v-if="activeTemplate" class="panel prepare-panel">
      <h3 class="panel-title">新規バッチ作成</h3>
      <div class="prepare-form">
        <label>
          数量 <span class="required-mark">*</span>
          <input type="number" v-model.number="newBatch.quantity" min="1" />
        </label>
        <label>
          ロットNo
          <input type="text" v-model.trim="newBatch.lot_no" placeholder="任意" />
        </label>
        <label>
          作業者名
          <input type="text" v-model.trim="newBatch.operator_name" />
        </label>
        <button class="btn-primary" @click="prepareBatch" :disabled="preparing || !newBatch.quantity">
          {{ preparing ? '作成中...' : 'バッチ作成・入力開始' }}
        </button>
      </div>
    </section>

    <section class="panel">
      <div class="batch-header">
        <h3 class="panel-title">既存バッチ一覧</h3>
        <select v-model="batchStatusFilter" class="batch-status-filter">
          <option value="">すべて</option>
          <option value="OPEN">実施中</option>
          <option value="COMPLETED">完了</option>
        </select>
      </div>
      <div v-if="loadingBatches" class="no-data">読込中...</div>
      <div v-else-if="!batches.length" class="no-data">該当するバッチはありません</div>
      <div v-else class="table-wrap">
        <table class="data-table compact">
          <thead>
            <tr>
              <th>ID</th>
              <th>計画日</th>
              <th>製品</th>
              <th>工程</th>
              <th>ロットNo</th>
              <th>数量</th>
              <th>進捗</th>
              <th>状態</th>
              <th>作成日時</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in batches" :key="b.id">
              <td>{{ b.id }}</td>
              <td>{{ b.plan_date || '-' }}</td>
              <td>{{ b.product_code || '-' }}</td>
              <td>{{ b.process_code || '-' }}</td>
              <td>{{ b.lot_no || '-' }}</td>
              <td>{{ b.quantity }}</td>
              <td>{{ b.completed_count ?? 0 }} / {{ b.quantity }}</td>
              <td>
                <span class="status-chip" :class="b.status === 'COMPLETED' ? 'ok' : 'draft'">
                  {{ b.status === 'COMPLETED' ? '完了' : '実施中' }}
                </span>
              </td>
              <td>{{ formatDateTime(b.created_at) }}</td>
              <td class="action-cell">
                <button class="btn-secondary btn-sm" @click="goToInput(b.id)">入力</button>
                <button
                  v-if="canDeleteBatch"
                  class="btn-danger btn-sm"
                  @click="deleteBatch(b)"
                  :disabled="(b.completed_count ?? 0) > 0"
                  :title="(b.completed_count ?? 0) > 0 ? '入力済みレコードがあるため削除不可' : 'バッチを削除'"
                >削除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>

  <div class="page-container" v-else>
    <h2 class="page-title">チェック実施</h2>
    <p class="no-data">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const router = useRouter()

const allLines = ref([])
const allProcesses = ref([])
const selectedLine = ref('')
const selectedProcess = ref('')
const selectedProduct = ref('')

const userUnitLines = computed(() => {
  const unitLines = authState.user?.profile?.unit_lines
  return Array.isArray(unitLines) ? unitLines : []
})
const userAllowedLineIds = computed(() =>
  new Set(userUnitLines.value.map((item) => String(item?.line_id || '').trim()).filter(Boolean))
)
const preferredLineId = computed(() => {
  const mappings = userUnitLines.value
  if (!mappings.length) return ''
  const def = mappings.find((item) => item?.is_default)
  const target = def || mappings[0]
  return target?.line_id ? String(target.line_id) : ''
})
const lineOptions = computed(() => {
  if (!userAllowedLineIds.value.size) return allLines.value
  return allLines.value.filter((line) => userAllowedLineIds.value.has(String(line.id)))
})
const filteredProcesses = computed(() => {
  if (!selectedLine.value) return allProcesses.value
  return allProcesses.value.filter((p) => String(p.line) === String(selectedLine.value))
})

const productOptions = ref([])
const loadingProducts = ref(false)

const activeTemplate = ref(null)
const checkingTemplate = ref(false)

const batches = ref([])
const loadingBatches = ref(false)
const batchStatusFilter = ref('OPEN')

const preparing = ref(false)
const defaultOperatorName = computed(() => {
  const u = authState.user
  if (!u) return ''
  return `${u.last_name || ''} ${u.first_name || ''}`.trim() || u.username || ''
})
const newBatch = ref({ quantity: 1, lot_no: '', operator_name: '' })

const canAccessQuality = (resource, level = 'view', aliases = []) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const candidates = [resource, ...aliases]
  const hasSpecific = permissions.some((item) => candidates.includes(item.resource))
  if (hasSpecific) return candidates.some((c) => hasPermission(user, c, level))
  return hasPermission(user, 'quality', level)
}

const canView = computed(() => canAccessQuality('quality.product_checksheet_input', 'view', [
  'quality.product_checksheet_operation',
  'quality.product_checksheet_template',
  'quality',
]))

const canDeleteBatch = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  return hasPermission(user, 'quality.product_checksheet_batch_delete', 'edit')
})

const formatDateTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('ja-JP')
}

const loadProductOptions = async () => {
  if (!selectedLine.value || !selectedProcess.value) {
    productOptions.value = []
    selectedProduct.value = ''
    return
  }
  loadingProducts.value = true
  try {
    const res = await api.productChecksheets.listTemplates({
      line: selectedLine.value,
      process: selectedProcess.value,
      status: 'APPROVED',
      is_active: true,
      page_size: 500,
    })
    const templates = res.data?.results || res.data || []
    const seen = new Set()
    productOptions.value = templates
      .filter((t) => t.product && !seen.has(t.product) && seen.add(t.product))
      .map((t) => ({ id: t.product, product_code: t.product_code, product_name: t.product_name }))
    if (!productOptions.value.some((p) => p.id === selectedProduct.value)) {
      selectedProduct.value = ''
    }
  } catch {
    productOptions.value = []
  } finally {
    loadingProducts.value = false
  }
}

const checkActiveTemplate = async () => {
  if (!selectedLine.value || !selectedProcess.value || !selectedProduct.value) {
    activeTemplate.value = null
    return
  }
  checkingTemplate.value = true
  try {
    const res = await api.productChecksheets.activeForTarget({
      line: selectedLine.value,
      process: selectedProcess.value,
      product: selectedProduct.value,
    })
    activeTemplate.value = res.data?.required ? res.data.template : null
  } catch {
    activeTemplate.value = null
  } finally {
    checkingTemplate.value = false
  }
}

const loadBatches = async () => {
  loadingBatches.value = true
  try {
    const params = {}
    if (selectedLine.value) params.line = selectedLine.value
    if (selectedProcess.value) params.process = selectedProcess.value
    if (selectedProduct.value) params.product = selectedProduct.value
    if (batchStatusFilter.value) params.status = batchStatusFilter.value
    const res = await api.productChecksheets.listBatches(params)
    batches.value = res.data?.results || res.data || []
  } catch {
    batches.value = []
  } finally {
    loadingBatches.value = false
  }
}

const refreshBatches = () => {
  checkActiveTemplate()
  loadBatches()
}

const prepareBatch = async () => {
  if (!activeTemplate.value || !newBatch.value.quantity) return
  preparing.value = true
  try {
    const res = await api.productChecksheets.prepareBatch({
      line: selectedLine.value,
      process: selectedProcess.value,
      product: selectedProduct.value,
      quantity: newBatch.value.quantity,
      lot_no: newBatch.value.lot_no,
      operator_name: newBatch.value.operator_name,
    })
    const batchId = res.data?.id
    if (batchId) {
      router.push(`/quality/product-checksheet/input/${batchId}`)
    } else {
      await loadBatches()
    }
  } catch (error) {
    alert(`バッチ作成に失敗しました: ${error.response?.data?.detail || error.message}`)
  } finally {
    preparing.value = false
  }
}

const deleteBatch = async (batch) => {
  if ((batch.completed_count ?? 0) > 0) {
    alert('入力済みレコードがあるため削除できません。')
    return
  }
  if (!confirm(`バッチ ID:${batch.id}（${batch.product_code} / ${batch.process_code}）を削除しますか？`)) return
  try {
    await api.productChecksheets.deleteBatch(batch.id)
    await loadBatches()
  } catch (error) {
    alert(`削除に失敗しました: ${error.response?.data?.detail || error.message}`)
  }
}

const goToInput = (batchId) => {
  router.push(`/quality/product-checksheet/input/${batchId}`)
}

const loadMasters = async () => {
  try {
    const [lineRes, processRes] = await Promise.all([
      api.lines.getLines({ page_size: 1000 }),
      api.processes.getProcesses({ is_active: true, page_size: 1000 }),
    ])
    allLines.value = lineRes.data?.results || lineRes.data || []
    allProcesses.value = processRes.data?.results || processRes.data || []
  } catch (error) {
    console.error('マスタ取得に失敗:', error)
  }
}

watch(() => selectedLine.value, () => {
  selectedProcess.value = ''
})

watch([() => selectedLine.value, () => selectedProcess.value], () => {
  loadProductOptions()
  activeTemplate.value = null
  loadBatches()
})

watch(() => selectedProduct.value, () => {
  checkActiveTemplate()
  loadBatches()
})

watch(() => batchStatusFilter.value, () => {
  loadBatches()
})

onMounted(async () => {
  if (!canView.value) return
  newBatch.value.operator_name = defaultOperatorName.value
  await loadMasters()
  if (preferredLineId.value) {
    selectedLine.value = preferredLineId.value
  } else if (lineOptions.value.length === 1) {
    selectedLine.value = String(lineOptions.value[0].id)
  }
  await loadBatches()
})
</script>

<style scoped>
.checksheet-operation {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: #111827;
  font-family: 'Meiryo', 'Yu Gothic UI', 'Yu Gothic', sans-serif;
  font-size: 14px;
}
.page-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.page-title { margin: 0; font-size: 20px; font-weight: 700; color: #0f172a; }
.page-actions { display: flex; gap: 8px; }
.panel {
  background: #fff;
  border: 1px solid #d5d8dc;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.panel-title { margin: 0; font-size: 16px; font-weight: 700; color: #0f172a; }
.filter-panel {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  align-items: end;
}
.filter-panel label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  color: #334155;
}
.filter-panel select,
.filter-panel input {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}
.template-status { display: flex; align-items: center; }
.status-note { font-size: 13px; color: #6b7280; }
.prepare-panel .prepare-form {
  display: flex;
  gap: 10px;
  align-items: end;
  flex-wrap: wrap;
}
.prepare-form label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  color: #334155;
}
.prepare-form input {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  width: 120px;
}
.required-mark { color: #dc2626; font-size: 12px; margin-left: 2px; }
.table-wrap {
  overflow: auto;
  border: 1px solid #dde2ea;
  border-radius: 4px;
}
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 6px 8px; border-bottom: 1px solid #edf1f5; text-align: left; }
.data-table th { background: #f7f9fb; font-size: 13px; font-weight: 700; }
.data-table.compact th, .data-table.compact td { padding: 4px 6px; font-size: 14px; }
.status-chip {
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
  display: inline-block;
}
.status-chip.ok { background: #e9f7ef; border-color: #9fd9b4; color: #166534; }
.status-chip.draft { background: #eef2ff; border-color: #c7d2fe; color: #3730a3; }
.status-chip.danger { background: #fdecec; border-color: #f7b1b1; color: #991b1b; }
.batch-header { display: flex; justify-content: space-between; align-items: center; }
.batch-status-filter { padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px; }
.no-data { color: #6b7280; padding: 8px 0; font-size: 13px; }
.btn-primary, .btn-secondary, .btn-sm {
  border-radius: 6px;
  padding: 7px 14px;
  cursor: pointer;
  border: 1px solid transparent;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-primary { background: #2563eb; color: #fff; border-color: #2563eb; }
.btn-primary:disabled { background: #93c5fd; border-color: #93c5fd; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #2563eb; border-color: #2563eb; }
.btn-danger { background: #dc2626; color: #fff; border-color: #dc2626; }
.btn-danger:disabled { background: #fca5a5; border-color: #fca5a5; cursor: not-allowed; }
.action-cell { display: flex; gap: 4px; }
</style>

