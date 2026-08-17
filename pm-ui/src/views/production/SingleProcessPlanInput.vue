<template>
  <div class="single-process-plan">
    <div class="header-bar">
      <label>参照ライン</label>
      <select v-model="selectedLineId" @change="onLineChange">
        <option value="">ライン選択</option>
        <option v-for="line in lines" :key="line.id" :value="line.id">
          {{ line.line_code }} - {{ line.line_name }}
        </option>
      </select>
      <label>参照工程</label>
      <select v-model="selectedRefProcessId">
        <option value="">工程選択</option>
        <option v-for="proc in lineProcesses" :key="proc.id" :value="proc.id">
          {{ proc.process_code }} - {{ proc.process_name }}
        </option>
      </select>
      <label>サブ工程</label>
      <select v-model="selectedSubProcessId">
        <option value="">工程選択</option>
        <option v-for="proc in allProcesses" :key="proc.id" :value="proc.id">
          {{ proc.process_code }} - {{ proc.process_name }}
        </option>
      </select>
      <label>期間</label>
      <input type="date" v-model="startDate" />
      <span>〜</span>
      <input type="date" v-model="endDate" />
      <button class="btn btn-primary" @click="loadData" :disabled="loading">読込</button>
      <button class="btn btn-save" @click="saveSubProcessPlan" :disabled="saving || !canSaveSubProcessPlan">保存</button>
      <label class="header-toggle"><input type="checkbox" v-model="hideWeekends" />土日非表示</label>
      <span class="header-sep">|</span>
      <select v-model="selectedFavoriteId" @change="applyFavorite" class="fav-select">
        <option value="">-- 選択 --</option>
        <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">
          {{ fav.name }}
        </option>
      </select>
      <input v-model.trim="favoriteName" type="text" placeholder="お気に入り名" class="fav-name-input" />
      <button class="btn favorite-star-btn" title="お気に入り登録" :disabled="!canSaveFavorite" @click="saveFavorite">★</button>
      <button class="btn btn-danger btn-sm" title="お気に入り削除" :disabled="!selectedFavoriteId" @click="deleteFavorite">✕</button>
      <DataSourceDialog title="単独計画" :sources="dsSources" />
    </div>

    <div v-if="selectedSubProcessId" class="candidate-card">
      <div class="candidate-header" @click="candidateEditorOpen = !candidateEditorOpen">
        <span class="candidate-arrow">{{ candidateEditorOpen ? '▼' : '▶' }}</span>
        候補製品編集
        <span class="candidate-meta">
          {{ selectedSubProcessCode || '-' }} / {{ subProcessProducts.length }}件表示
          <template v-if="selectedSubProcessCandidateRule"> / 個別設定中</template>
        </span>
      </div>
      <div v-show="candidateEditorOpen" class="candidate-body">
        <div class="candidate-help">
          未設定なら関連製品候補を全表示します。設定保存すると、選択した品番だけをこの画面の候補に表示します。
        </div>
        <div class="candidate-actions">
          <button class="btn" type="button" @click="selectAllEditableProducts" :disabled="candidateSaving || !candidateEditableProducts.length">全選択</button>
          <button class="btn" type="button" @click="deselectAllEditableProducts" :disabled="candidateSaving">個別設定解除</button>
          <button class="btn btn-primary" type="button" @click="saveCandidateRule" :disabled="candidateSaving || !selectedSubProcessCode">
            {{ candidateSaving ? '保存中...' : '候補保存' }}
          </button>
        </div>
        <div v-if="candidateSaveMsg" class="candidate-save-msg" :class="{ error: candidateSaveError }">
          {{ candidateSaveMsg }}
        </div>
        <div v-if="candidateEditableProducts.length" class="candidate-list">
          <label v-for="prod in candidateEditableProducts" :key="`cand-${prod.id}`" class="candidate-item">
            <input
              type="checkbox"
              :checked="candidateDraftProductCodes.includes(normalizeProductCode(prod.product_code))"
              @change="toggleCandidateCode(prod.product_code, $event.target.checked)"
            />
            <span>{{ prod.product_code }} - {{ prod.product_name || '' }}</span>
            <small :class="{ 'coproduct-child-label': prod.relation_type === 'coproduct_child' }">{{ relationTypeLabel(prod.relation_type) }}</small>
          </label>
        </div>
        <div v-else class="candidate-help">この工程の加工品候補がありません。</div>
      </div>
    </div>

    <div v-if="selectedSubProcessId && selectedRefProcessId" class="candidate-card mapping-card">
      <div class="candidate-header" @click="mappingEditorOpen = !mappingEditorOpen">
        <span class="candidate-arrow">{{ mappingEditorOpen ? '▼' : '▶' }}</span>
        チェックシート用製品マッピング
        <span class="candidate-meta">
          サブ品→完成品
          <template v-if="selectedChecksheetMapping"> / {{ selectedChecksheetMapping.mappings.length }}件設定中</template>
        </span>
      </div>
      <div v-show="mappingEditorOpen" class="candidate-body">
        <div class="candidate-help">
          サブ工程の品番と参照工程（完成品）の品番の対応を設定します。チェックシート発行時に完成品の品番が使われます。
        </div>
        <div v-if="mappingSaveMsg" class="candidate-save-msg" :class="{ error: mappingSaveError }">
          {{ mappingSaveMsg }}
        </div>
        <div v-if="subProcessProducts.length" class="mapping-table">
          <div v-for="subProd in subProcessProducts" :key="`map-${subProd.id}`" class="mapping-row">
            <div class="mapping-sub-label">{{ subProd.product_code }}</div>
            <div class="mapping-arrow">→</div>
            <div class="mapping-finished-list">
              <span
                v-for="fin in (getMappingDraftForSub(subProd.product_code)?.finished || [])"
                :key="`fin-${fin}`"
                class="mapping-tag"
              >
                {{ fin }}
                <button type="button" class="mapping-tag-remove" @click="removeFinishedFromMapping(subProd.product_code, fin)">✕</button>
              </span>
              <select
                class="mapping-add-select"
                @change="addFinishedToMapping(subProd.product_code, $event.target.value); $event.target.value = ''"
              >
                <option value="">＋完成品追加</option>
                <option
                  v-for="refProd in refProcessProducts.filter((rp) => !(getMappingDraftForSub(subProd.product_code)?.finished || []).includes(normalizeProductCode(rp.product_code)))"
                  :key="refProd.id"
                  :value="refProd.product_code"
                >{{ refProd.product_code }} {{ refProd.product_name || '' }}</option>
              </select>
            </div>
          </div>
        </div>
        <div v-else class="candidate-help">サブ工程の候補製品がありません。</div>
        <div class="candidate-actions" style="margin-top: 8px;">
          <button class="btn" type="button" @click="resetChecksheetMapping" :disabled="mappingSaving">マッピング解除</button>
          <button class="btn btn-primary" type="button" @click="saveChecksheetMapping" :disabled="mappingSaving || !selectedSubProcessCode">
            {{ mappingSaving ? '保存中...' : 'マッピング保存' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-msg">読み込み中...</div>
    <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>

    <div v-if="dateColumns.length && (maxRefSeq > 0 || selectedSubProcessId)" class="grid-scroll">
      <table class="grid-table">
        <colgroup>
          <col class="col-seq" />
          <template v-for="d in dateColumns" :key="`cg-${d.dateStr}`">
            <col class="col-product" />
            <col class="col-qty" />
          </template>
        </colgroup>

        <thead v-if="maxRefSeq > 0">
          <tr>
            <th class="sticky-col section-label" :colspan="1 + dateColumns.length * 2">{{ refProcessLabel }} ガントプラン（参照）</th>
          </tr>
          <tr>
            <th class="sticky-col seq-header" rowspan="2">順</th>
            <th v-for="d in dateColumns" :key="d.dateStr" colspan="2" :class="dateHeaderClass(d)">
              {{ d.label }}<span class="dow">{{ d.dow }}</span>
            </th>
          </tr>
          <tr>
            <template v-for="d in dateColumns" :key="`sub-${d.dateStr}`">
              <th class="sub-header" :class="dateHeaderClass(d)">製品</th>
              <th class="sub-header" :class="dateHeaderClass(d)">数量</th>
            </template>
          </tr>
        </thead>
        <tbody v-if="maxRefSeq > 0">
          <tr v-for="seq in maxRefSeq" :key="`ref-${seq}`">
            <td class="sticky-col seq-cell">{{ seq }}</td>
            <template v-for="d in dateColumns" :key="`${d.dateStr}-${seq}`">
              <td class="product-cell" :class="dateCellClass(d)">{{ getRefCell(d.dateStr, seq)?.productCode || '' }}</td>
              <td class="num qty-cell" :class="dateCellClass(d)">{{ getRefCell(d.dateStr, seq)?.qty || '' }}</td>
            </template>
          </tr>
          <tr class="total-row">
            <td class="sticky-col"><strong>計</strong></td>
            <template v-for="d in dateColumns" :key="`reftot-${d.dateStr}`">
              <td :class="dateCellClass(d)"></td>
              <td class="num" :class="dateCellClass(d)"><strong>{{ getRefDateTotal(d.dateStr) || '' }}</strong></td>
            </template>
          </tr>
        </tbody>

        <thead v-if="selectedSubProcessId">
          <tr>
            <th class="sticky-col section-label" :colspan="1 + dateColumns.length * 2">{{ subProcessLabel }} 計画入力</th>
          </tr>
          <tr>
            <th class="sticky-col seq-header" rowspan="2">順</th>
            <th v-for="d in dateColumns" :key="`h2-${d.dateStr}`" colspan="2" :class="dateHeaderClass(d)">
              {{ d.label }}<span class="dow">{{ d.dow }}</span>
              <button
                v-if="selectedChecksheetMapping"
                type="button"
                class="btn-day-plus"
                :disabled="saving"
                @click="createChecksheetForDay(d.dateStr)"
                title="この日の計画から工程一体チェックシートを作成"
              >＋</button>
            </th>
          </tr>
          <tr>
            <template v-for="d in dateColumns" :key="`sub2-${d.dateStr}`">
              <th class="sub-header" :class="dateHeaderClass(d)">製品</th>
              <th class="sub-header" :class="dateHeaderClass(d)">数量</th>
            </template>
          </tr>
        </thead>
        <tbody v-if="selectedSubProcessId">
          <tr v-for="seq in subInputRowCount" :key="`sub-${seq}`">
            <td class="sticky-col seq-cell">{{ seq }}</td>
            <template v-for="d in dateColumns" :key="`${d.dateStr}-sub-${seq}`">
              <td class="input-cell" :class="dateCellClass(d)">
                <select
                  :value="getSubCell(d.dateStr, seq)?.productId || ''"
                  @change="setSubProduct(d.dateStr, seq, $event.target.value)"
                  class="prod-select"
                  :class="{ 'plan-batch-missing': isSubProductBatchMissing(d.dateStr, seq) }"
                >
                  <option value=""></option>
                  <option v-for="prod in subGridDropdownProducts" :key="prod.id" :value="prod.id">
                    {{ prod.product_code }}
                  </option>
                </select>
              </td>
              <td class="input-cell" :class="dateCellClass(d)">
                <input
                  type="number"
                  min="0"
                  step="1"
                  :value="getSubCell(d.dateStr, seq)?.qty || ''"
                  @change="setSubQty(d.dateStr, seq, $event.target.value)"
                  @keydown="onQtyKeydown"
                  class="qty-input"
                  :class="{ 'plan-batch-qty-mismatch': isSubQtyBatchMismatch(d.dateStr, seq) }"
                />
              </td>
            </template>
          </tr>
          <tr class="total-row">
            <td class="sticky-col"><strong>計</strong></td>
            <template v-for="d in dateColumns" :key="`subtot-${d.dateStr}`">
              <td :class="dateCellClass(d)"></td>
              <td class="num" :class="dateCellClass(d)"><strong>{{ getSubDateTotal(d.dateStr) || '' }}</strong></td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="selectedSubProcessId && dateColumns.length" class="gantt-section">
      <div class="gantt-header">
        <div class="gantt-title">
          工程ガント（{{ subProcessLabel }}）
          <span class="gantt-meta">ライン {{ selectedLineId || '' }} / 期間 {{ startDate }} 〜 {{ endDate }}</span>
        </div>
        <div class="gantt-actions">
          <label class="gantt-toggle">
            <input type="checkbox" v-model="showGanttAddAnchors" />
            ＋表示
          </label>
          <label class="gantt-toggle">
            <input type="checkbox" v-model="hideEmptyGanttRows" />
            空行非表示
          </label>
          <label class="gantt-toggle">
            <input type="checkbox" v-model="ganttHideWeekends" />
            土日非表示
          </label>
          <button
            class="btn gantt-save-btn"
            :class="{ 'gantt-save-dirty': ganttEditDirty }"
            @click="saveGanttEditChanges"
            :disabled="!selectedLineId || !ganttEditDirty"
          >
            時間数量保存
          </button>
          <button
            class="btn gantt-save-btn"
            :class="{ 'gantt-save-dirty': ganttStructureDirty }"
            @click="saveGanttStructureChanges"
            :disabled="!selectedLineId || !ganttStructureDirty"
          >
            追加削除保存
          </button>
        </div>
      </div>
      <ProcessGanttView
        :key="ganttReloadKey"
        ref="ganttRef"
        :embedded="true"
        :preset-line="selectedLineId"
        :preset-base-date="startDate"
        :preset-start-date="startDate"
        :preset-end-date="endDate"
        :filter-process-id="selectedSubProcessId"
        :auto-generate-if-empty="false"
        :show-add-anchors="showGanttAddAnchors"
        :hide-empty-rows="hideEmptyGanttRows"
        @dirty-change="onGanttDirtyChange"
        @mode-change="onGanttModeChange"
        @edit-dirty-change="onGanttEditDirtyChange"
        @structure-dirty-change="onGanttStructureDirtyChange"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import ProcessGanttView from './ProcessGanttView.vue'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '取得', table: 't_line_backlog', desc: '参照工程読込・サブ工程計画保存先読込' },
  { op: '取得', table: 't_line_gantt_plan', desc: 'サブ工程ガントプラン読込・完成品エントリ読込' },
  { op: '保存', table: 't_line_backlog', desc: 'サブ工程計画保存（seq>0の行を削除→再作成）' },
  { op: '保存', table: 't_line_gantt_plan', desc: 'サブ工程計画保存（SINGLEPROC_プレフィクス行を削除→再作成）' },
  { op: '取得', table: 't_line / t_process', desc: 'ライン・工程マスタ' },
  { op: '取得', table: 't_product / t_routing_step / t_bom_item', desc: '関連製品候補の解決' },
  { op: '取得/保存', table: 'production_plan_line_setting', desc: '候補製品の個別設定（special_rules）' },
  { op: '取得/保存', table: 'user_favorite', desc: 'お気に入りフィルタ条件' },
]

const DAY_BOUNDARY_HOUR = 8
const DOW_LABELS = ['日', '月', '火', '水', '木', '金', '土']
const FAVORITE_SCREEN_KEY = 'production.sub_process_plan'

const toDateStr = (d) => {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const normalizeProcessCode = (value) => String(value || '').trim().toUpperCase()
const normalizeProductCode = (value) => String(value || '').trim().toUpperCase()

const normalizeSubProcessCandidateRules = (rows) => {
  const source = Array.isArray(rows) ? rows : []
  const normalized = []
  const seen = new Set()
  source.forEach((row) => {
    const processCode = normalizeProcessCode(row?.processCode)
    const productCodes = Array.isArray(row?.productCodes)
      ? Array.from(new Set(row.productCodes.map((code) => normalizeProductCode(code)).filter(Boolean)))
      : []
    if (!processCode || !productCodes.length || seen.has(processCode)) return
    seen.add(processCode)
    normalized.push({ processCode, productCodes })
  })
  return normalized
}

const normalizeChecksheetProductMapping = (rows) => {
  const source = Array.isArray(rows) ? rows : []
  const normalized = []
  const seen = new Set()
  source.forEach((row) => {
    const processCode = normalizeProcessCode(row?.processCode)
    if (!processCode || seen.has(processCode)) return
    const mappings = Array.isArray(row?.mappings) ? row.mappings : []
    const normalizedMappings = []
    const subSeen = new Set()
    mappings.forEach((m) => {
      const sub = normalizeProductCode(m?.sub)
      const finished = Array.isArray(m?.finished)
        ? Array.from(new Set(m.finished.map((c) => normalizeProductCode(c)).filter(Boolean)))
        : []
      if (!sub || !finished.length || subSeen.has(sub)) return
      subSeen.add(sub)
      normalizedMappings.push({ sub, finished })
    })
    if (!normalizedMappings.length) return
    seen.add(processCode)
    normalized.push({ processCode, mappings: normalizedMappings })
  })
  return normalized
}

const relationTypeLabel = (relationType) => {
  switch (relationType) {
    case 'coproduct_parent':
      return '連産親'
    case 'coproduct_child':
      return '連産子'
    case 'output_product':
      return '出力品'
    case 'bom_process_item':
      return 'BOM工程品'
    case 'intermediate':
      return '社内製作品'
    case 'purchased':
      return '購入品'
    default:
      return relationType || ''
  }
}

const lines = ref([])
const allProcesses = ref([])
const lineProcesses = computed(() => {
  if (!selectedLineId.value) return allProcesses.value
  return allProcesses.value.filter((p) => p.line_id != null && String(p.line_id) === String(selectedLineId.value))
})

const selectedLineId = ref('')
const selectedRefProcessId = ref('')
const selectedSubProcessId = ref('')

const now = new Date()
if (now.getHours() < DAY_BOUNDARY_HOUR) now.setDate(now.getDate() - 1)
const todayStr = toDateStr(now)
const tomorrow = new Date(now)
tomorrow.setDate(tomorrow.getDate() + 1)
const tomorrowStr = toDateStr(tomorrow)
const defaultEnd = new Date(now)
defaultEnd.setDate(defaultEnd.getDate() + 13)

const startDate = ref(todayStr)
const endDate = ref(toDateStr(defaultEnd))

const HIDE_WEEKENDS_KEY = 'subProcessPlan.hideWeekends'
const hideWeekends = ref(localStorage.getItem(HIDE_WEEKENDS_KEY) === '1')

const loading = ref(false)
const errorMsg = ref('')

const refGrid = ref({})
const subGrid = ref({})
const checksheetBatchTotals = ref({})
const loadedGridProducts = ref([])
const lastLoadedSubEntryCount = ref(0)
const lastLoadedPlanCount = ref(0)

const subProcessAutoProducts = ref([])
const subProcessCandidateRules = ref([])
const candidateEditorOpen = ref(false)
const candidateDraftProductCodes = ref([])
const candidateSaving = ref(false)
const candidateSaveMsg = ref('')
const candidateSaveError = ref(false)

const checksheetProductMapping = ref([])
const mappingEditorOpen = ref(false)
const mappingDraft = ref([])
const mappingSaving = ref(false)
const mappingSaveMsg = ref('')
const mappingSaveError = ref(false)
const refProcessProducts = ref([])

const favorites = ref([])
const selectedFavoriteId = ref('')
const favoriteName = ref('')

const selectedSubProcess = computed(() => allProcesses.value.find((p) => String(p.id) === String(selectedSubProcessId.value)) || null)
const selectedSubProcessCode = computed(() => normalizeProcessCode(selectedSubProcess.value?.process_code))
const selectedSubProcessCandidateRule = computed(() => (
  subProcessCandidateRules.value.find((rule) => rule.processCode === selectedSubProcessCode.value) || null
))

const selectedChecksheetMapping = computed(() => (
  checksheetProductMapping.value.find((rule) => rule.processCode === selectedSubProcessCode.value) || null
))

const finishedToSubMap = computed(() => {
  const map = new Map()
  const rule = selectedChecksheetMapping.value
  if (!rule) return map
  rule.mappings.forEach((m) => {
    m.finished.forEach((finCode) => {
      map.set(finCode, m.sub)
    })
  })
  return map
})

const mergedSubProcessProducts = computed(() => {
  const map = new Map()
  subProcessAutoProducts.value.forEach((product) => {
    map.set(String(product.id), product)
  })
  loadedGridProducts.value.forEach((product) => {
    if (!map.has(String(product.id))) {
      map.set(String(product.id), product)
    }
  })
  return Array.from(map.values()).sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
})

const candidateEditableProducts = computed(() => {
  const allowedRelationTypes = new Set(['output_product', 'coproduct_child', 'coproduct_parent', 'bom_process_item'])
  const map = new Map()
  subProcessAutoProducts.value.forEach((product) => {
    if (!allowedRelationTypes.has(product.relation_type)) return
    map.set(String(product.id), product)
  })
  loadedGridProducts.value.forEach((product) => {
    if (!map.has(String(product.id))) {
      map.set(String(product.id), product)
    }
  })
  return Array.from(map.values()).sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
})

const subProcessProducts = computed(() => {
  const allCandidates = mergedSubProcessProducts.value
  const rule = selectedSubProcessCandidateRule.value
  if (!rule) return allCandidates
  const allowedCodes = new Set(rule.productCodes)
  const filtered = allCandidates.filter((product) => allowedCodes.has(normalizeProductCode(product.product_code)))
  return filtered.length ? filtered : allCandidates
})

const subGridDropdownProducts = computed(() => {
  const mapping = selectedChecksheetMapping.value
  if (!mapping) return subProcessProducts.value
  const mappedSubCodes = new Set(mapping.mappings.map((m) => m.sub))
  const result = subProcessProducts.value.filter((p) => !mappedSubCodes.has(normalizeProductCode(p.product_code)))
  const refMap = new Map(refProcessProducts.value.map((p) => [normalizeProductCode(p.product_code), p]))
  mapping.mappings.forEach((m) => {
    const subInCandidates = subProcessProducts.value.some((p) => normalizeProductCode(p.product_code) === m.sub)
    if (!subInCandidates) return
    m.finished.forEach((finCode) => {
      const refProd = refMap.get(finCode)
      if (refProd) result.push(refProd)
    })
  })
  return result.sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
})

const refProcessLabel = computed(() => {
  const proc = allProcesses.value.find((p) => String(p.id) === String(selectedRefProcessId.value))
  return proc ? `${proc.process_code} ${proc.process_name}` : '参照工程'
})
const subProcessLabel = computed(() => {
  return selectedSubProcess.value
    ? `${selectedSubProcess.value.process_code} ${selectedSubProcess.value.process_name}`
    : 'サブ工程'
})

const dateColumns = computed(() => {
  if (!startDate.value || !endDate.value) return []
  const cols = []
  const s = new Date(`${startDate.value}T00:00:00`)
  const e = new Date(`${endDate.value}T00:00:00`)
  for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)) {
    const day = d.getDay()
    if (hideWeekends.value && (day === 0 || day === 6)) continue
    const dateStr = toDateStr(d)
    cols.push({
      dateStr,
      label: `${d.getMonth() + 1}/${d.getDate()}`,
      dow: DOW_LABELS[day],
      isToday: dateStr === todayStr,
      isTomorrow: dateStr === tomorrowStr,
    })
  }
  return cols
})

const dateHeaderClass = (d) => ({ 'col-today': d.isToday, 'col-tomorrow': d.isTomorrow })
const dateCellClass = (d) => ({ 'col-today': d.isToday, 'col-tomorrow': d.isTomorrow })
const createPlanBatchCompareKey = (dateStr, productId) => `${String(dateStr || '')}|${String(productId || '')}`

const maxRefSeq = computed(() => {
  let max = 0
  Object.keys(refGrid.value).forEach((key) => {
    const seq = parseInt(key.split('|')[1], 10)
    if (seq > max) max = seq
  })
  return max
})

const getRefCell = (dateStr, seq) => refGrid.value[`${dateStr}|${seq}`] || null
const getRefDateTotal = (dateStr) => {
  let total = 0
  Object.keys(refGrid.value).forEach((key) => {
    if (key.startsWith(`${dateStr}|`)) total += refGrid.value[key].qty
  })
  return total
}

const subInputRowCount = computed(() => {
  let maxUsed = 0
  Object.keys(subGrid.value).forEach((key) => {
    const seq = parseInt(key.split('|')[1], 10)
    if (seq > maxUsed) maxUsed = seq
  })
  return Math.max(maxUsed + 2, maxRefSeq.value, 5)
})

const getSubCell = (dateStr, seq) => subGrid.value[`${dateStr}|${seq}`] || null

const planGridTotals = computed(() => {
  const totals = {}
  Object.entries(subGrid.value || {}).forEach(([key, cell]) => {
    const [dateStr] = key.split('|')
    const productId = String(cell?.productId || '')
    const qty = Number(cell?.qty || 0)
    if (!dateStr || !productId || qty <= 0) return
    const compareKey = createPlanBatchCompareKey(dateStr, productId)
    totals[compareKey] = (totals[compareKey] || 0) + qty
  })
  return totals
})

const planBatchComparisonMap = computed(() => {
  if (!selectedChecksheetMapping.value) return {}
  const result = {}
  Object.entries(planGridTotals.value).forEach(([key, planQty]) => {
    const hasBatch = Object.prototype.hasOwnProperty.call(checksheetBatchTotals.value, key)
    const batchQty = Number(checksheetBatchTotals.value[key] || 0)
    result[key] = {
      missing: !hasBatch,
      qtyMismatch: hasBatch && batchQty !== Number(planQty || 0),
    }
  })
  return result
})

const getSubCellBatchComparison = (dateStr, seq) => {
  const cell = getSubCell(dateStr, seq)
  const productId = String(cell?.productId || '')
  const qty = Number(cell?.qty || 0)
  if (!selectedChecksheetMapping.value || !productId || qty <= 0) return null
  return planBatchComparisonMap.value[createPlanBatchCompareKey(dateStr, productId)] || null
}

const isSubProductBatchMissing = (dateStr, seq) => !!getSubCellBatchComparison(dateStr, seq)?.missing
const isSubQtyBatchMismatch = (dateStr, seq) => !!getSubCellBatchComparison(dateStr, seq)?.qtyMismatch

const getProductInfo = (productId) => {
  const pid = String(productId)
  const product = mergedSubProcessProducts.value.find((item) => String(item.id) === pid)
    || refProcessProducts.value.find((item) => String(item.id) === pid)
  return {
    productCode: product?.product_code || '',
    productName: product?.product_name || '',
  }
}

const setSubProduct = (dateStr, seq, productId) => {
  const key = `${dateStr}|${seq}`
  if (!productId) {
    if (subGrid.value[key]) {
      delete subGrid.value[key]
      subGrid.value = { ...subGrid.value }
    }
    return
  }
  const info = getProductInfo(productId)
  const existing = subGrid.value[key]
  subGrid.value = {
    ...subGrid.value,
    [key]: {
      productId,
      productCode: info.productCode,
      productName: info.productName,
      qty: existing?.qty || 0,
    },
  }
}

const setSubQty = (dateStr, seq, val) => {
  const key = `${dateStr}|${seq}`
  const qty = parseInt(val, 10)
  const existing = subGrid.value[key]
  if (!existing?.productId && (!qty || qty <= 0)) return
  const productId = existing?.productId || ''
  const info = getProductInfo(productId)
  subGrid.value = {
    ...subGrid.value,
    [key]: {
      productId,
      productCode: existing?.productCode || info.productCode,
      productName: existing?.productName || info.productName,
      qty: qty > 0 ? qty : 0,
    },
  }
}

const getSubDateTotal = (dateStr) => {
  let total = 0
  Object.keys(subGrid.value).forEach((key) => {
    if (key.startsWith(`${dateStr}|`)) total += (subGrid.value[key].qty || 0)
  })
  return total
}

const saving = ref(false)
const GANTT_HIDE_WEEKENDS_KEY = 'processGanttView.hideWeekends'
const ganttHideWeekends = ref(localStorage.getItem(GANTT_HIDE_WEEKENDS_KEY) === '1')
const hideEmptyGanttRows = ref(false)
const showGanttAddAnchors = ref(false)
const ganttReloadKey = ref(0)
const ganttRef = ref(null)
const ganttDirty = ref(false)
const ganttEditDirty = ref(false)
const ganttStructureDirty = ref(false)

const hasSubEntries = computed(() => Object.values(subGrid.value).some((cell) => cell.productId && cell.qty > 0))
const canSaveSubProcessPlan = computed(() => hasSubEntries.value || lastLoadedSubEntryCount.value > 0)

const onGanttDirtyChange = (isDirty) => {
  ganttDirty.value = !!isDirty
}

const onGanttModeChange = () => {}

const onGanttEditDirtyChange = (isDirty) => {
  ganttEditDirty.value = !!isDirty
}

const onGanttStructureDirtyChange = (isDirty) => {
  ganttStructureDirty.value = !!isDirty
}

const saveGanttEditChanges = async () => {
  const gantt = ganttRef.value
  if (!gantt || typeof gantt.saveEditChanges !== 'function') {
    window.alert('工程ガントが未読込です。')
    return
  }
  await gantt.saveEditChanges()
}

const saveGanttStructureChanges = async () => {
  const gantt = ganttRef.value
  if (!gantt || typeof gantt.saveStructureChanges !== 'function') {
    window.alert('工程ガントが未読込です。')
    return
  }
  await gantt.saveStructureChanges()
}

const buildCandidateDraftFromRule = () => {
  const rule = selectedSubProcessCandidateRule.value
  if (rule) {
    candidateDraftProductCodes.value = [...rule.productCodes]
    return
  }
  candidateDraftProductCodes.value = candidateEditableProducts.value.map((product) => normalizeProductCode(product.product_code))
}

const toggleCandidateCode = (productCode, checked) => {
  const normalizedCode = normalizeProductCode(productCode)
  const next = new Set(candidateDraftProductCodes.value)
  if (checked) next.add(normalizedCode)
  else next.delete(normalizedCode)
  candidateDraftProductCodes.value = Array.from(next)
}

const selectAllEditableProducts = () => {
  candidateDraftProductCodes.value = candidateEditableProducts.value.map((product) => normalizeProductCode(product.product_code))
}

const deselectAllEditableProducts = () => {
  candidateDraftProductCodes.value = []
}

const saveSubProcessCandidateRulesPayload = async (rules) => {
  const payload = {
    special_rules: {
      sub_process_candidate_rules: normalizeSubProcessCandidateRules(rules),
    },
  }
  const res = await api.productionPlanLineSettings.saveSettings(payload)
  const savedRules = normalizeSubProcessCandidateRules(res?.data?.special_rules?.sub_process_candidate_rules)
  subProcessCandidateRules.value = savedRules
}

const saveCandidateRule = async () => {
  if (!selectedSubProcessCode.value) return
  candidateSaving.value = true
  candidateSaveMsg.value = ''
  candidateSaveError.value = false
  try {
    const nextRules = subProcessCandidateRules.value.filter((rule) => rule.processCode !== selectedSubProcessCode.value)
    if (candidateDraftProductCodes.value.length) {
      nextRules.push({
        processCode: selectedSubProcessCode.value,
        productCodes: Array.from(new Set(candidateDraftProductCodes.value.map((code) => normalizeProductCode(code)).filter(Boolean))),
      })
    }
    await saveSubProcessCandidateRulesPayload(nextRules)
    buildCandidateDraftFromRule()
    candidateSaveMsg.value = '候補製品設定を保存しました。'
  } catch (e) {
    console.warn('候補製品設定保存失敗', e)
    candidateSaveError.value = true
    candidateSaveMsg.value = e?.response?.data?.detail || '候補製品設定の保存に失敗しました。'
  } finally {
    candidateSaving.value = false
  }
}

const resetCandidateRule = async () => {
  if (!selectedSubProcessCode.value) return
  candidateSaving.value = true
  candidateSaveMsg.value = ''
  candidateSaveError.value = false
  try {
    const nextRules = subProcessCandidateRules.value.filter((rule) => rule.processCode !== selectedSubProcessCode.value)
    await saveSubProcessCandidateRulesPayload(nextRules)
    buildCandidateDraftFromRule()
    candidateSaveMsg.value = '候補製品の個別設定を解除しました。'
  } catch (e) {
    console.warn('候補製品設定解除失敗', e)
    candidateSaveError.value = true
    candidateSaveMsg.value = e?.response?.data?.detail || '候補製品設定の解除に失敗しました。'
  } finally {
    candidateSaving.value = false
  }
}

const loadRefProcessProducts = async () => {
  if (!selectedRefProcessId.value) {
    refProcessProducts.value = []
    return
  }
  try {
    const res = await api.processes.getRelatedProducts(selectedRefProcessId.value)
    const products = Array.isArray(res?.data) ? res.data : []
    refProcessProducts.value = products
      .filter((p) => ['output_product', 'coproduct_child', 'coproduct_parent', 'bom_process_item'].includes(p.relation_type))
      .map((p) => ({ id: p.id, product_code: p.product_code, product_name: p.product_name }))
      .sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
  } catch (e) {
    console.warn('参照工程製品取得失敗', e)
    refProcessProducts.value = []
  }
}

const buildMappingDraft = () => {
  const rule = selectedChecksheetMapping.value
  if (rule) {
    mappingDraft.value = rule.mappings.map((m) => ({ sub: m.sub, finished: [...m.finished] }))
  } else {
    mappingDraft.value = []
  }
}

const getMappingDraftForSub = (subCode) => {
  const norm = normalizeProductCode(subCode)
  return mappingDraft.value.find((m) => m.sub === norm) || null
}

const addFinishedToMapping = (subCode, finishedCode) => {
  const normSub = normalizeProductCode(subCode)
  const normFin = normalizeProductCode(finishedCode)
  if (!normSub || !normFin) return
  let entry = mappingDraft.value.find((m) => m.sub === normSub)
  if (!entry) {
    entry = { sub: normSub, finished: [] }
    mappingDraft.value.push(entry)
  }
  if (!entry.finished.includes(normFin)) {
    entry.finished.push(normFin)
  }
}

const removeFinishedFromMapping = (subCode, finishedCode) => {
  const normSub = normalizeProductCode(subCode)
  const normFin = normalizeProductCode(finishedCode)
  const entry = mappingDraft.value.find((m) => m.sub === normSub)
  if (!entry) return
  entry.finished = entry.finished.filter((f) => f !== normFin)
  if (!entry.finished.length) {
    mappingDraft.value = mappingDraft.value.filter((m) => m.sub !== normSub)
  }
}

const saveChecksheetMapping = async () => {
  if (!selectedSubProcessCode.value) return
  mappingSaving.value = true
  mappingSaveMsg.value = ''
  mappingSaveError.value = false
  try {
    const nextRules = checksheetProductMapping.value.filter((r) => r.processCode !== selectedSubProcessCode.value)
    const validMappings = mappingDraft.value.filter((m) => m.sub && m.finished.length)
    if (validMappings.length) {
      nextRules.push({ processCode: selectedSubProcessCode.value, mappings: validMappings })
    }
    const payload = { special_rules: { checksheet_product_mapping: nextRules } }
    const res = await api.productionPlanLineSettings.saveSettings(payload)
    checksheetProductMapping.value = normalizeChecksheetProductMapping(res?.data?.special_rules?.checksheet_product_mapping)
    buildMappingDraft()
    mappingSaveMsg.value = 'マッピングを保存しました。'
  } catch (e) {
    console.warn('マッピング保存失敗', e)
    mappingSaveError.value = true
    mappingSaveMsg.value = e?.response?.data?.detail || 'マッピングの保存に失敗しました。'
  } finally {
    mappingSaving.value = false
  }
}

const resetChecksheetMapping = async () => {
  if (!selectedSubProcessCode.value) return
  mappingSaving.value = true
  mappingSaveMsg.value = ''
  mappingSaveError.value = false
  try {
    const nextRules = checksheetProductMapping.value.filter((r) => r.processCode !== selectedSubProcessCode.value)
    const payload = { special_rules: { checksheet_product_mapping: nextRules } }
    const res = await api.productionPlanLineSettings.saveSettings(payload)
    checksheetProductMapping.value = normalizeChecksheetProductMapping(res?.data?.special_rules?.checksheet_product_mapping)
    buildMappingDraft()
    mappingSaveMsg.value = 'マッピングを解除しました。'
  } catch (e) {
    console.warn('マッピング解除失敗', e)
    mappingSaveError.value = true
    mappingSaveMsg.value = e?.response?.data?.detail || 'マッピングの解除に失敗しました。'
  } finally {
    mappingSaving.value = false
  }
}

const resolveSubProductId = (productId) => {
  const info = getProductInfo(productId)
  const normCode = normalizeProductCode(info.productCode)
  const subCode = finishedToSubMap.value.get(normCode)
  if (!subCode) return productId
  const subProd = mergedSubProcessProducts.value.find((p) => normalizeProductCode(p.product_code) === subCode)
  return subProd ? String(subProd.id) : productId
}

const createChecksheetForDay = async (dateStr) => {
  if (!selectedSubProcessId.value || !selectedLineId.value) {
    alert('ラインとサブ工程を選択してください。')
    return
  }
  if (!dateStr) return
  const mapping = selectedChecksheetMapping.value
  if (!mapping) {
    alert('チェックシート用マッピングが設定されていません。')
    return
  }
  const ok = window.confirm('チェックシート作成しますか？')
  if (!ok) return

  const targets = []
  Object.keys(subGrid.value).forEach((key) => {
    if (!key.startsWith(`${dateStr}|`)) return
    const cell = subGrid.value[key]
    if (!cell.productId || !cell.qty || cell.qty <= 0) return
    targets.push({ productId: cell.productId, productCode: normalizeProductCode(cell.productCode), qty: cell.qty })
  })

  if (!targets.length) {
    alert('この日の計画数量がありません。')
    return
  }

  saving.value = true
  try {
    let created = 0
    const errors = []
    for (const target of targets) {
      try {
        await api.integratedChecksheets.prepareBatch({
          product: target.productId,
          line: selectedLineId.value,
          quantity: target.qty,
          plan_date: dateStr,
          lot_no: '',
        })
        created += 1
      } catch (e) {
        const msg = e?.response?.data?.detail || e?.message || '作成失敗'
        errors.push(`${target.productCode}: ${msg}`)
      }
    }
    if (errors.length) {
      alert(`チェックシート作成: ${created}件成功 / ${errors.length}件失敗\n${errors.join('\n')}`)
    } else {
      alert(`チェックシートを ${created} 件作成しました。`)
    }
    await loadChecksheetBatchTotals()
  } finally {
    saving.value = false
  }
}

const loadChecksheetBatchTotals = async () => {
  if (!selectedLineId.value || !startDate.value || !endDate.value || !selectedChecksheetMapping.value) {
    checksheetBatchTotals.value = {}
    return
  }
  try {
    const res = await api.integratedChecksheets.listBatches({
      line: selectedLineId.value,
      plan_date__gte: startDate.value,
      plan_date__lte: endDate.value,
      page_size: 1000,
    })
    const rows = Array.isArray(res?.data) ? res.data : (Array.isArray(res?.data?.results) ? res.data.results : [])
    const totals = {}
    rows.forEach((row) => {
      const dateStr = String(row?.plan_date || '')
      const productId = String(row?.product || '')
      const qty = Number(row?.quantity || 0)
      if (!dateStr || !productId || qty <= 0) return
      const key = createPlanBatchCompareKey(dateStr, productId)
      totals[key] = (totals[key] || 0) + qty
    })
    checksheetBatchTotals.value = totals
  } catch (e) {
    console.warn('チェックシートバッチ集計取得失敗', e)
    checksheetBatchTotals.value = {}
  }
}

const saveSubProcessPlan = async () => {
  if (!selectedSubProcessId.value || !selectedLineId.value) return
  saving.value = true

  const entries = []
  Object.keys(subGrid.value).forEach((key) => {
    const cell = subGrid.value[key]
    if (!cell.productId || !cell.qty || cell.qty <= 0) return
    const [planDate, seqStr] = key.split('|')
    entries.push({
      product_id: resolveSubProductId(cell.productId),
      plan_date: planDate,
      plan_qty: cell.qty,
      sequence_no: parseInt(seqStr, 10),
    })
  })

  const allDates = []
  if (startDate.value && endDate.value) {
    const s = new Date(`${startDate.value}T00:00:00`)
    const e = new Date(`${endDate.value}T00:00:00`)
    for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)) {
      allDates.push(toDateStr(d))
    }
  }

  const finishedEntries = []
  if (selectedChecksheetMapping.value) {
    Object.keys(subGrid.value).forEach((key) => {
      const cell = subGrid.value[key]
      if (!cell.productId || !cell.qty || cell.qty <= 0) return
      const [planDate, seqStr] = key.split('|')
      finishedEntries.push({
        product_id: cell.productId,
        plan_date: planDate,
        quantity: cell.qty,
        sequence_no: parseInt(seqStr, 10),
      })
    })
  }

  try {
    const payload = {
      line_id: selectedLineId.value,
      process_id: selectedSubProcessId.value,
      entries,
      target_dates: allDates,
    }
    if (finishedEntries.length) {
      payload.finished_entries = finishedEntries
    }
    const res = await api.lineGanttPlans.subProcessSave(payload)
    const data = res?.data || {}
    await loadData()
    ganttReloadKey.value += 1
    alert(`保存完了（Backlog: 削除${data.deleted_backlog || 0} → 作成${data.created_backlog || 0}件、ガント: 削除${data.deleted_gantt || 0} → 作成${data.created_gantt || 0}件）`)
  } catch (e) {
    console.error('保存エラー', e)
    alert(e?.response?.data?.detail || '保存に失敗しました')
  } finally {
    saving.value = false
  }
}

const toFavoritePayload = () => ({
  lineId: String(selectedLineId.value || ''),
  refProcessId: String(selectedRefProcessId.value || ''),
  subProcessId: String(selectedSubProcessId.value || ''),
})

const applyFavoritePayload = (payload) => {
  selectedLineId.value = String(payload?.lineId || '')
  selectedRefProcessId.value = String(payload?.refProcessId || '')
  selectedSubProcessId.value = String(payload?.subProcessId || '')
}

const loadFavorites = async () => {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 })
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error('お気に入り取得失敗:', e)
  }
}

const applyFavorite = () => {
  const id = Number(selectedFavoriteId.value || 0)
  if (!id) return
  const target = favorites.value.find((item) => Number(item.id) === id)
  if (!target) return
  favoriteName.value = target.name || ''
  applyFavoritePayload(target.payload || {})
}

const canSaveFavorite = computed(() => favoriteName.value && selectedLineId.value)

const saveFavorite = async () => {
  const name = String(favoriteName.value || '').trim()
  if (!name) {
    window.alert('お気に入り名を入力してください。')
    return
  }
  const payload = {
    screen_key: FAVORITE_SCREEN_KEY,
    name,
    payload: toFavoritePayload(),
  }
  try {
    const id = Number(selectedFavoriteId.value || 0)
    if (id) await api.accounts.updateFavorite(id, payload)
    else await api.accounts.createFavorite(payload)
    await loadFavorites()
    const found = favorites.value.find((item) => item.name === name)
    selectedFavoriteId.value = found ? String(found.id) : ''
    window.alert('お気に入りを保存しました。')
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || '保存に失敗しました。'
    window.alert(`お気に入り保存エラー: ${detail}`)
  }
}

const deleteFavorite = async () => {
  const id = Number(selectedFavoriteId.value || 0)
  if (!id) return
  const target = favorites.value.find((item) => Number(item.id) === id)
  if (!window.confirm(`「${target?.name || ''}」を削除しますか？`)) return
  try {
    await api.accounts.deleteFavorite(id)
    selectedFavoriteId.value = ''
    favoriteName.value = ''
    await loadFavorites()
  } catch (e) {
    window.alert('削除に失敗しました。')
  }
}

const onQtyKeydown = (e) => {
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault()
  }
  if (e.key === 'Enter' || e.key === 'ArrowDown') {
    e.preventDefault()
    const td = e.target.closest('td')
    if (!td) return
    const colIdx = Array.from(td.parentElement.children).indexOf(td)
    const nextRow = td.parentElement.nextElementSibling
    if (nextRow && nextRow.children[colIdx]) {
      const nextInput = nextRow.children[colIdx].querySelector('input')
      if (nextInput) nextInput.focus()
    }
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    const td = e.target.closest('td')
    if (!td) return
    const colIdx = Array.from(td.parentElement.children).indexOf(td)
    const prevRow = td.parentElement.previousElementSibling
    if (prevRow && prevRow.children[colIdx]) {
      const prevInput = prevRow.children[colIdx].querySelector('input')
      if (prevInput) prevInput.focus()
    }
  }
}

const onLineChange = () => {
  selectedRefProcessId.value = ''
}

const formatTime = (dt) => {
  if (!dt) return ''
  const dateObj = new Date(dt)
  return `${String(dateObj.getHours()).padStart(2, '0')}:${String(dateObj.getMinutes()).padStart(2, '0')}`
}

const loadSubProcessProducts = async () => {
  if (!selectedSubProcessId.value) {
    subProcessAutoProducts.value = []
    buildCandidateDraftFromRule()
    return
  }
  try {
    const relatedRes = await api.processes.getRelatedProducts(selectedSubProcessId.value)
    const products = Array.isArray(relatedRes?.data) ? relatedRes.data : []
    subProcessAutoProducts.value = products
      .map((product) => ({
        id: product.id,
        product_code: product.product_code,
        product_name: product.product_name,
        relation_type: product.relation_type,
      }))
      .sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
  } catch (e) {
    console.warn('サブ工程製品取得失敗', e)
    subProcessAutoProducts.value = []
  } finally {
    buildCandidateDraftFromRule()
  }
}

const loadPlanSettings = async () => {
  try {
    const res = await api.productionPlanLineSettings.getSettings()
    subProcessCandidateRules.value = normalizeSubProcessCandidateRules(res?.data?.special_rules?.sub_process_candidate_rules)
    checksheetProductMapping.value = normalizeChecksheetProductMapping(res?.data?.special_rules?.checksheet_product_mapping)
  } catch (e) {
    console.warn('サブ工程候補製品設定取得失敗', e)
    subProcessCandidateRules.value = []
    checksheetProductMapping.value = []
  } finally {
    buildCandidateDraftFromRule()
    buildMappingDraft()
  }
}

const loadData = async () => {
  if (!selectedLineId.value) {
    errorMsg.value = 'ラインを選択してください'
    return
  }
  loading.value = true
  errorMsg.value = ''
  refGrid.value = {}
  subGrid.value = {}
  checksheetBatchTotals.value = {}
  loadedGridProducts.value = []
  lastLoadedSubEntryCount.value = 0
  lastLoadedPlanCount.value = 0

  try {
    const [backlogRes, ganttRes] = await Promise.all([
      api.lineBacklogs.getLineBacklogs({
        line: selectedLineId.value,
        plan_date__gte: startDate.value,
        plan_date__lte: endDate.value,
      }),
      api.lineGanttPlans.getLineGanttPlans({
        line: selectedLineId.value,
        plan_date__gte: startDate.value,
        plan_date__lte: endDate.value,
      }),
    ])
    const backlogs = backlogRes?.data?.results || backlogRes?.data || []
    const plans = ganttRes?.data?.results || ganttRes?.data || []
    lastLoadedPlanCount.value = Array.isArray(plans) ? plans.length : 0

    const refProcessId = Number(selectedRefProcessId.value || 0)
    const subProcessId = Number(selectedSubProcessId.value || 0)
    const subProcessPrefix = `SINGLEPROC_${selectedLineId.value}_${selectedSubProcessId.value}_`

    const nextRefGrid = {}
    const subEntries = {}
    const loadedProductsMap = new Map()

    if (refProcessId) {
      backlogs.forEach((row) => {
        if (Number(row.process) !== refProcessId) return
        const seq = Number(row.sequence_no || 0)
        const dateStr = String(row.plan_date || '')
        if (!dateStr || seq <= 0) return
        nextRefGrid[`${dateStr}|${seq}`] = {
          productCode: row.product_code || '',
          qty: Math.round(Number(row.plan_qty || 0)),
        }
      })
    }

    plans.forEach((plan) => {
      const processes = Array.isArray(plan.processes_plan) ? plan.processes_plan : []
      if (!subProcessId || !String(plan.plan_id || '').startsWith(subProcessPrefix)) return
      const subProc = processes.find((proc) => Number(proc.process_id) === subProcessId)
      if (!subProc) return
      const seq = Number(plan.sequence_no || 0)
      if (!seq) return
      const dateStr = String(plan.plan_date || '')
      const productId = Number(subProc.output_product_id || plan.product || 0)
      if (!dateStr || !productId) return
      const qty = Number(subProc.quantity || plan.plan_qty || 0)
      subEntries[`${dateStr}|${seq}`] = {
        productId: String(productId),
        productCode: subProc.output_product_code || plan.product_code || '',
        productName: subProc.output_product_name || plan.product_name || '',
        qty: qty > 0 ? Math.round(qty) : 0,
      }
      loadedProductsMap.set(String(productId), {
        id: productId,
        product_code: subProc.output_product_code || plan.product_code || '',
        product_name: subProc.output_product_name || plan.product_name || '',
      })
    })
    refGrid.value = nextRefGrid

    if (selectedSubProcessId.value) {
      await loadSubProcessProducts()
    }

    let finalSubEntries = subEntries
    if (selectedChecksheetMapping.value && selectedSubProcessId.value) {
      try {
        const feRes = await api.lineGanttPlans.getSingleprocFinishedEntries({
          line: selectedLineId.value,
          process: selectedSubProcessId.value,
          plan_date__gte: startDate.value,
          plan_date__lte: endDate.value,
        })
        const feData = Array.isArray(feRes?.data) ? feRes.data : []
        if (feData.length) {
          finalSubEntries = {}
          feData.forEach((fe) => {
            const key = `${fe.plan_date}|${fe.sequence_no}`
            finalSubEntries[key] = {
              productId: String(fe.product_id),
              productCode: fe.product_code || '',
              productName: fe.product_name || '',
              qty: fe.quantity > 0 ? fe.quantity : 0,
            }
          })
        }
      } catch (e) {
        console.warn('完成品エントリ取得失敗、ガントデータで代替', e)
      }
    }

    subGrid.value = finalSubEntries
    await loadChecksheetBatchTotals()
    loadedGridProducts.value = Array.from(loadedProductsMap.values()).sort((a, b) => (a.product_code || '').localeCompare(b.product_code || ''))
    lastLoadedSubEntryCount.value = Object.keys(finalSubEntries).length
  } catch (e) {
    console.error('読込エラー', e)
    errorMsg.value = 'データ読み込みに失敗しました'
  } finally {
    loading.value = false
  }
}

watch(selectedSubProcessId, async () => {
  candidateSaveMsg.value = ''
  candidateSaveError.value = false
  mappingSaveMsg.value = ''
  mappingSaveError.value = false
  loadedGridProducts.value = []
  if (selectedSubProcessId.value) {
    await loadSubProcessProducts()
  } else {
    subProcessAutoProducts.value = []
    candidateDraftProductCodes.value = []
  }
  buildMappingDraft()
})

watch(selectedRefProcessId, () => {
  loadRefProcessProducts()
})

watch(hideWeekends, (v) => {
  localStorage.setItem(HIDE_WEEKENDS_KEY, v ? '1' : '0')
})

watch(ganttHideWeekends, (v) => {
  localStorage.setItem(GANTT_HIDE_WEEKENDS_KEY, v ? '1' : '0')
  const gantt = ganttRef.value
  if (gantt) {
    gantt.hideWeekends = v
  }
})

watch([selectedLineId, startDate, endDate], () => {
  ganttReloadKey.value += 1
})

onMounted(async () => {
  try {
    const [lineRes, procRes] = await Promise.all([
      api.lines.getLines({ is_active: true }),
      api.processes.getProcesses({ page_size: 5000 }),
      loadFavorites(),
      loadPlanSettings(),
    ])
    lines.value = (lineRes?.data?.results || lineRes?.data || [])
      .filter((l) => l.line_type === 'PROD')
      .sort((a, b) => (a.line_code || '').localeCompare(b.line_code || ''))
    allProcesses.value = (procRes?.data?.results || procRes?.data || [])
      .map((proc) => ({
        id: proc.id,
        process_code: String(proc.process_code || '').trim(),
        process_name: String(proc.process_name || '').trim(),
        line_id: proc.line ?? null,
      }))
      .filter((proc) => proc.process_code)
      .sort((a, b) => a.process_code.localeCompare(b.process_code))
  } catch (e) {
    console.error('初期データ取得失敗', e)
  }
})
</script>

<style scoped>
.single-process-plan { padding: 8px; }
.header-bar { background: #f5f5f5; padding: 6px 8px; border-radius: 4px; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.header-bar label { font-weight: bold; font-size: 12px; white-space: nowrap; }
.header-bar select, .header-bar input { font-size: 12px; padding: 2px 3px; }
.header-bar select { max-width: 160px; }
.header-bar input[type="date"] { width: 110px; }
.header-sep { color: #bbb; font-size: 14px; margin: 0 2px; }
.header-toggle { display: inline-flex; align-items: center; gap: 2px; font-size: 11px; white-space: nowrap; cursor: pointer; }
.fav-select { max-width: 120px !important; }
.fav-name-input { width: 100px; }
.btn { font-size: 11px; padding: 2px 4px; cursor: pointer; border: 1px solid #ccc; border-radius: 3px; background: #fff; }
.btn:hover { background: #eee; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #4a90d9; color: #fff; border-color: #4a90d9; }
.btn-primary:hover { background: #3a7bc0; }
.btn-danger { background: #d9534f; color: #fff; border-color: #d9534f; }
.btn-sm { font-size: 11px; padding: 2px 6px; }
.favorite-star-btn { background: #fff8e1; border-color: #f9a825; color: #f57f17; font-size: 14px; padding: 2px 8px; }
.favorite-star-btn:hover { background: #fff3c4; }
.candidate-card { border: 1px solid #d7dfeb; border-radius: 4px; background: #fbfcff; margin-bottom: 8px; }
.candidate-header { padding: 6px 8px; font-size: 12px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 6px; }
.candidate-arrow { color: #4a90d9; }
.candidate-meta { margin-left: auto; color: #666; font-weight: normal; }
.candidate-body { border-top: 1px solid #d7dfeb; padding: 8px; }
.candidate-help { font-size: 12px; color: #555; margin-bottom: 8px; }
.candidate-actions { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.candidate-save-msg { font-size: 12px; color: #2e7d32; margin-bottom: 8px; }
.candidate-save-msg.error { color: #d32f2f; }
.candidate-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 6px 10px; }
.candidate-item { display: flex; align-items: center; gap: 6px; font-size: 12px; border: 1px solid #edf1f6; border-radius: 4px; padding: 4px 6px; background: #fff; }
.candidate-item small { margin-left: auto; color: #666; }
.candidate-item small.coproduct-child-label { color: #d32f2f; font-weight: bold; }
.grid-scroll { overflow-x: auto; margin-bottom: 8px; }
.grid-table { border-collapse: collapse; font-size: 11px; white-space: nowrap; table-layout: fixed; }
.col-seq { width: 28px; }
.col-product { width: 100px; }
.col-qty { width: 38px; }
.section-label { text-align: left !important; font-size: 13px; background: #e0e0e0 !important; padding: 4px 6px !important; }
.grid-table th, .grid-table td { border: 1px solid #ccc; padding: 2px 4px; text-align: center; }
.grid-table th { background: #f0f0f0; font-weight: bold; }
.sub-header { font-size: 10px; font-weight: normal !important; }
.sticky-col { position: sticky; left: 0; background: #f0f0f0; z-index: 2; min-width: 28px; }
.seq-header { width: 28px; }
.seq-cell { font-weight: bold; color: #666; }
.product-cell { text-align: left !important; font-size: 10px; min-width: 90px; max-width: 110px; overflow: hidden; text-overflow: ellipsis; }
.qty-cell { min-width: 32px; }
.num { text-align: right !important; }
.total-row td { background: #f5f5f5; }
.col-today { background: #fff8e1 !important; }
.col-tomorrow { background: #e8f5e9 !important; }
.dow { font-size: 9px; color: #888; margin-left: 2px; }
.input-cell { padding: 1px !important; }
.prod-select { width: 100px; font-size: 10px; border: 1px solid #ddd; padding: 1px; background: transparent; }
.prod-select:focus { outline: 2px solid #4a90d9; }
.qty-input { width: 38px; border: 1px solid #ddd; text-align: right; font-size: 11px; padding: 1px 2px; background: transparent; }
.qty-input:focus { outline: 2px solid #4a90d9; background: #fff; }
.prod-select.plan-batch-missing { color: #c62828; border-color: #ef9a9a; background: #fff5f5; font-weight: bold; }
.qty-input.plan-batch-qty-mismatch { color: #c62828; border-color: #ef9a9a; background: #fff5f5; font-weight: bold; }
.qty-input::-webkit-inner-spin-button, .qty-input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.qty-input { -moz-appearance: textfield; }
.save-bar { padding: 8px 0; display: flex; align-items: center; gap: 10px; }
.btn-save { background: #2e7d32; color: #fff; border-color: #2e7d32; font-size: 11px; padding: 2px 6px; font-weight: bold; }
.btn-save:hover { background: #1b5e20; }
.loading-msg { padding: 12px; color: #666; }
.error-msg { padding: 6px; color: #d32f2f; background: #ffebee; border-radius: 3px; margin-bottom: 8px; }
.gantt-section { margin-top: 8px; padding: 8px; border: 1px solid #d7dfeb; border-radius: 6px; background: #fff; }
.gantt-header { display: flex; justify-content: space-between; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.gantt-title { font-size: 14px; font-weight: bold; color: #1f2937; }
.gantt-meta { margin-left: 8px; font-size: 12px; font-weight: normal; color: #6b7280; }
.gantt-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.gantt-toggle { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: #111827; }
.gantt-save-btn { font-weight: bold; }
.gantt-save-btn.gantt-save-dirty { background: #dc2626; color: #fff; border-color: #b91c1c; }
.mapping-card { border-color: #c8d6e5; background: #f8faff; }
.mapping-table { display: flex; flex-direction: column; gap: 6px; }
.mapping-row { display: flex; align-items: center; gap: 6px; padding: 4px 6px; border: 1px solid #edf1f6; border-radius: 4px; background: #fff; }
.mapping-sub-label { font-size: 12px; font-weight: bold; min-width: 120px; white-space: nowrap; }
.mapping-arrow { font-size: 14px; color: #888; }
.mapping-finished-list { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
.mapping-tag { display: inline-flex; align-items: center; gap: 2px; font-size: 11px; background: #e3f2fd; border: 1px solid #90caf9; border-radius: 3px; padding: 2px 6px; }
.mapping-tag-remove { background: none; border: none; color: #d32f2f; font-size: 11px; cursor: pointer; padding: 0 2px; line-height: 1; }
.mapping-add-select { font-size: 11px; padding: 2px 4px; border: 1px solid #ddd; border-radius: 3px; max-width: 200px; }
.btn-day-plus { display: inline-block; margin-left: 2px; padding: 0 3px; font-size: 10px; line-height: 14px; border: 1px solid #4caf50; border-radius: 2px; background: #e8f5e9; color: #2e7d32; cursor: pointer; vertical-align: middle; }
.btn-day-plus:hover { background: #c8e6c9; }
.btn-day-plus:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
