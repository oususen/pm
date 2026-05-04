<template>
  <div class="page-container ics-operation" v-if="canView">
    <!-- ページヘッダー -->
    <div class="page-header">
      <h2 class="page-title">{{ pageTitleText }}</h2>
      <div class="page-actions">
        <button
          v-if="showBackToProcessInput"
          class="btn-secondary"
          @click="backToProcessInput"
        >工程作業入力へ戻る</button>
        <button
          v-if="isReviewMode"
          class="btn-secondary"
          @click="openNewBatchSection"
        >新規バッチ</button>
        <button class="btn-secondary" @click="refreshAll" :disabled="loading">更新</button>
      </div>
    </div>

    <!-- フィルタパネル -->
    <section class="panel filter-panel">
      <div class="prepare-form filter-form">
        <label>
          <span class="field-label">ライン</span>
          <select v-model="selectedLine" :disabled="loading || isLineLockedFromRoute">
            <option value="">全ライン</option>
            <option v-for="l in lineOptions" :key="l.id" :value="l.id">{{ l.line_code }} - {{ l.line_name }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">製品</span>
          <select v-model="selectedProduct" :disabled="loading">
            <option value="">全製品</option>
            <option v-for="p in filteredProductOptions" :key="p.id" :value="p.id">{{ p.product_code }} - {{ p.product_name }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">ステータス</span>
          <select v-model="batchStatusFilter">
            <option value="">すべて</option>
            <option value="OPEN">実施中</option>
            <option value="COMPLETED">完了</option>
            <option value="LEADER_CONFIRMED">リーダ確認済</option>
            <option value="SUPERVISOR_CONFIRMED">班長確認済</option>
          </select>
        </label>
      </div>
    </section>

    <!-- 新規バッチ作成 -->
    <section v-if="isReviewMode" class="panel" ref="newBatchSectionRef">
      <div class="panel-title-row">
        <h3 class="panel-title">新規バッチ作成</h3>
        <button class="btn-secondary btn-sm" @click="showNewBatchSection = !showNewBatchSection">
          {{ showNewBatchSection ? '隠す' : '表示' }}
        </button>
      </div>
      <div v-if="showNewBatchSection" class="prepare-form">
        <label>
          <span class="field-label">ライン <span class="required-mark">*</span></span>
          <select v-model="newBatch.line">
            <option value="">選択</option>
            <option v-for="l in lineOptions" :key="'nb-'+l.id" :value="l.id">{{ l.line_code }} - {{ l.line_name }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">製品 <span class="required-mark">*</span></span>
          <select v-model="newBatch.product">
            <option value="">選択</option>
            <option v-for="p in newBatchProductOptions" :key="'nb-'+p.id" :value="p.id">{{ p.product_code }} - {{ p.product_name }}</option>
          </select>
        </label>
        <label>
          <span class="field-label">台数 <span class="required-mark">*</span></span>
          <input type="number" v-model.number="newBatch.quantity" min="1" style="width:80px" />
        </label>
        <label>
          <span class="field-label">最終工程計画日 <span class="required-mark">*</span></span>
          <input type="date" v-model="newBatch.plan_date" style="width:140px" />
        </label>
        <label>
          <span class="field-label">ロットNo</span>
          <input type="text" v-model.trim="newBatch.lot_no" placeholder="任意" style="width:120px" />
        </label>
        <button class="btn-primary" @click="prepareBatch" :disabled="preparing || !newBatch.product || !newBatch.line || !newBatch.quantity || !newBatch.plan_date || !canEdit">
          {{ preparing ? '作成中...' : 'バッチ作成' }}
        </button>
      </div>
    </section>

    <!-- バッチ一覧 -->
    <section class="panel">
      <h3 class="panel-title">バッチ一覧</h3>
      <div v-if="loadingBatches" class="no-data">読込中...</div>
      <div v-else-if="!batches.length" class="no-data">該当するバッチはありません</div>
      <div v-else class="table-wrap">
        <table class="data-table compact">
          <thead>
            <tr>
              <th>ID</th>
              <th>最終工程計画日</th>
              <th>ライン</th>
              <th>製品</th>
              <th>ロットNo</th>
              <th>台数</th>
              <th>進捗</th>
              <th>工程別進捗</th>
              <th>状態</th>
              <th>作成日時</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in batches" :key="b.id" :class="{ 'row-selected': activeBatchId === b.id }">
              <td>{{ b.id }}</td>
              <td>{{ b.plan_date || '-' }}</td>
              <td>{{ b.line_code || '-' }}</td>
              <td>{{ b.product_code || '-' }}</td>
              <td>{{ b.lot_no || '-' }}</td>
              <td>{{ b.quantity }}</td>
              <td>{{ b.completed_count ?? 0 }} / {{ b.quantity }}</td>
              <td>
                <div class="process-progress-list">
                  <span
                    v-for="chip in processProgressChips(b.process_progress)"
                    :key="chip.key"
                    class="process-progress-chip"
                    :class="{ done: chip.done }"
                  >
                    {{ chip.label }}
                  </span>
                </div>
              </td>
              <td>
                <span class="status-chip" :class="statusClass(b.status)">{{ statusLabel(b.status) }}</span>
              </td>
              <td>{{ formatDateTime(b.created_at) }}</td>
              <td class="action-cell">
                <button class="btn-primary btn-sm" @click="openBatchDetail(b)">詳細</button>
                <button
                  v-if="isReviewMode && canLeaderConfirm(b)"
                  class="btn-secondary btn-sm"
                  :disabled="actionLoading"
                  @click="leaderConfirm(b)"
                >リーダ確認</button>
                <button
                  v-if="isReviewMode && canShowSupervisorConfirm(b)"
                  class="btn-secondary btn-sm"
                  :disabled="actionLoading || !isSupervisorUser"
                  @click="supervisorConfirm(b)"
                >班長確認</button>
                <span v-if="b.status === 'SUPERVISOR_CONFIRMED'" class="status-chip ok">確認済</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- バッチ詳細（マトリクス） -->
    <section v-if="activeBatch" class="panel matrix-panel">
      <div class="matrix-header">
        <h3 class="panel-title">
          {{ activeBatch.product_code }} {{ activeBatch.product_name }}
          <span class="batch-meta">| ロット: {{ activeBatch.lot_no || '-' }} | 最終工程計画日: {{ activeBatch.plan_date || '-' }}</span>
          <span v-if="isReviewMode && reviewRoleLabel" class="batch-meta">| 確認: {{ reviewRoleLabel }}</span>
        </h3>
        <button class="btn-secondary btn-sm" @click="closeBatchDetail">閉じる</button>
      </div>

      <div v-if="loadingUnits" class="no-data">読込中...</div>
      <div v-else-if="!units.length" class="no-data">台目データがありません</div>
      <div v-else class="matrix-scroll">
        <table class="data-table matrix-table">
          <thead>
            <tr>
              <th class="th-process">工程</th>
              <th class="th-item">チェック項目</th>
              <th class="th-type">種別</th>
              <th
                v-for="u in units"
                :key="'h-'+u.id"
                class="th-unit"
                :class="{ clickable: true }"
                  @click="canEdit ? openUnitModal(u) : null"
              >
                <div class="unit-header">
                  <span>{{ u.sequence_no }}</span>
                  <span class="status-chip mini" :class="statusClass(u.status)">{{ statusShort(u.status) }}</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="block in templateBlocks" :key="'blk-'+block.id">
              <!-- 工程ヘッダー行 -->
              <tr class="block-header-row">
                <td :colspan="3" class="block-header-cell">
                  <div class="block-header-inner">
                    <span class="block-title-left">
                      {{ block.process_code }} {{ block.process_name }}
                      <span v-if="block.sketch_image_url" class="sketch-badge">略図あり</span>
                    </span>
                    <span class="block-title-right">確認者</span>
                  </div>
                </td>
              <td
                v-for="u in units"
                :key="'bh-'+block.id+'-'+u.id"
                class="block-checker-cell"
                :class="{ 'cell-disabled-by-process': isBlockedByPreferredProcess(block) }"
                @click="canEdit && !isBlockedByPreferredProcess(block) ? openUnitModal(u, block.id) : null"
              >
                {{ getBlockCheckerName(u, block.id) || '-' }}
              </td>
              </tr>
              <!-- 各チェック項目行 -->
              <tr v-for="item in block.items" :key="'item-'+item.id">
                <td class="td-process">{{ block.process_code }}</td>
                <td class="td-item">
                  {{ item.item_name }}
                  <span v-if="item.standard" class="item-standard">{{ item.standard }}</span>
                </td>
                <td class="td-type">
                  <span class="type-tag" :class="'type-' + item.record_type">{{ recordTypeLabel(item.record_type) }}</span>
                </td>
                <td
                  v-for="u in units"
                  :key="'c-'+item.id+'-'+u.id"
                  class="td-cell"
                  :class="cellClass(u, block, item)"
                  @click="canEdit && !isBlockedByPreferredProcess(block) ? openUnitModal(u, block.id) : null"
                >
                  <template v-if="isBlockLocked(u, block)">
                    <span class="lock-icon">&#128274;</span>
                  </template>
                  <template v-else>
                    {{ cellDisplay(u, item) }}
                  </template>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 台目入力モーダル -->
    <div v-if="modalUnit" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>チェック入力</h3>
          <div class="modal-header-actions">
            <button class="btn-secondary btn-sm" @click="closeModal">閉じる</button>
            <button class="btn-close" @click="closeModal">&times;</button>
          </div>
        </div>
        <div class="modal-body">
          <div
            v-for="block in modalVisibleBlocks"
            :key="'mb-'+block.id"
            class="process-section"
            :class="{ 'ratio-4-1': block.sketch_image_url && !isBlockLockedForModal(block) && block.items?.length }"
          >
            <div class="process-section-header" :class="{ locked: isBlockLockedForModal(block) }">
              <strong>{{ block.process_code }} {{ block.process_name }}</strong>
              <span v-if="getBlockProgress(block)" class="progress-text">
                {{ getBlockProgress(block).done }} / {{ getBlockProgress(block).total }}
              </span>
              <span v-if="isBlockLockedForModal(block)" class="lock-label">前工程未完了のためロック中</span>
            </div>

            <!-- 略図プレースホルダー -->
            <div v-if="block.sketch_image_url && !isBlockLockedForModal(block)" class="sketch-placeholder">
              <img :src="block.sketch_image_url" alt="略図" class="sketch-img" />
              <div class="sketch-overlay"><span>手書き入力は後日実装予定</span></div>
            </div>

            <!-- チェック項目 -->
            <div v-if="!isBlockLockedForModal(block)" class="items-list">
              <div v-for="item in block.items" :key="'mi-'+item.id" class="item-row">
                <div class="item-label-area">
                  <span class="item-name">{{ item.item_name }}</span>
                  <span v-if="item.is_required" class="required-mark">*</span>
                  <span v-if="item.standard" class="item-hint">{{ item.standard }}</span>
                  <span v-if="item.unit" class="item-hint">[{{ item.unit }}]</span>
                </div>
                <div class="item-input-area">
                  <!-- CHECK -->
                  <template v-if="item.record_type === 'CHECK'">
                    <button
                      class="judge-btn ok"
                      :class="{ active: modalResponses[item.id]?.judgement === 'OK' }"
                      @click="setJudgement(item.id, 'OK')"
                      :disabled="!canEdit"
                    >OK</button>
                    <button
                      class="judge-btn ng"
                      :class="{ active: modalResponses[item.id]?.judgement === 'NG' }"
                      @click="setJudgement(item.id, 'NG')"
                      :disabled="!canEdit"
                    >NG</button>
                  </template>
                  <!-- NUMERIC -->
                  <template v-else-if="item.record_type === 'NUMERIC'">
                    <input
                      type="number"
                      step="any"
                      class="numeric-input"
                      :value="modalResponses[item.id]?.numeric_value ?? ''"
                      @input="setNumeric(item.id, $event.target.value)"
                      :disabled="!canEdit"
                      :placeholder="item.criteria || '数値'"
                    />
                    <span v-if="item.unit" class="unit-label">{{ item.unit }}</span>
                  </template>
                  <!-- TEXT -->
                  <template v-else>
                    <input
                      type="text"
                      class="text-input"
                      :value="modalResponses[item.id]?.text_value ?? ''"
                      @input="setText(item.id, $event.target.value)"
                      :disabled="!canEdit"
                      :placeholder="item.criteria || 'テキスト'"
                    />
                  </template>
                </div>
              </div>
            </div>

            <!-- ロック中表示 -->
            <div v-else class="locked-message">
              前工程の必須項目を全て完了してください
            </div>

          </div>
          <div class="modal-save-bar">
            <div class="modal-save-bar-main">
              <span class="modal-unit-label">台目 #{{ modalUnit.sequence_no }} 入力</span>
              <button
                class="btn-secondary btn-sm"
                @click="moveModalUnit(-1)"
                :disabled="!canMovePrevUnit"
              >前の一台</button>
              <button
                class="btn-secondary btn-sm"
                @click="moveModalUnit(1)"
                :disabled="!canMoveNextUnit"
              >次の一台</button>
              <span class="status-chip" :class="statusClass(modalHeaderStatusCode)">{{ modalHeaderStatusLabel }}</span>
              <button
                v-if="modalVisibleBlocks.length === 1 && !isBlockLockedForModal(modalVisibleBlocks[0]) && modalVisibleBlocks[0].items?.length"
                class="btn-primary btn-sm"
                @click="saveBlockChecks(modalVisibleBlocks[0])"
                :disabled="savingBlock === modalVisibleBlocks[0].id || !canEdit"
              >
                {{ savingBlock === modalVisibleBlocks[0].id ? '保存中...' : 'この工程を保存' }}
              </button>
              <button class="btn-secondary btn-sm" @click="closeModal">閉じる</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="page-container" v-else>
    <h2 class="page-title">{{ pageTitleText }}</h2>
    <p class="no-data">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
const route = useRoute()
const router = useRouter()

// --- 権限 ---
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
const isReviewMode = computed(() => route.name === 'IntegratedChecksheetReview')
const pageTitleText = computed(() => (
  isReviewMode.value ? '製品チェックシート結果確認' : '製品チェックシート実施'
))
const isSupervisorUser = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  return (user.profile?.role || '') === 'supervisor'
})
const canView = computed(() =>
  canAccessQuality(
    isReviewMode.value ? 'quality.integrated_checksheet_review' : 'quality.integrated_checksheet_operation',
    'view',
    [
      'quality.integrated_checksheet_operation',
      'quality.product_checksheet_input',
      'quality.product_checksheet_review',
      'quality.integrated_checksheet',
      'quality',
    ]
  )
)
const canEdit = computed(() =>
  canAccessQuality(
    isReviewMode.value ? 'quality.integrated_checksheet_review' : 'quality.integrated_checksheet_operation',
    'edit',
    [
      'quality.integrated_checksheet_operation',
      'quality.product_checksheet_input',
      'quality.integrated_checksheet',
      'quality',
    ]
  )
)

// --- マスタ ---
const allLines = ref([])
const allProducts = ref([])
const lineOptions = computed(() => allLines.value)
const lineFinalProductsByLine = ref({})
const lineFinalProductIdSet = computed(() => new Set(allProducts.value.map((p) => Number(p.id))))
const uniqById = (list) => {
  const map = new Map()
  list.forEach((item) => {
    if (!item || item.id == null) return
    map.set(Number(item.id), item)
  })
  return [...map.values()]
}
const parseLineFinalCandidates = (responseData) => {
  const rows = Array.isArray(responseData) ? responseData : []
  if (!rows.length) return []
  const raw = Array.isArray(rows[0]?.products)
    ? rows.flatMap((row) => row.products || [])
    : rows
  return uniqById(raw).filter((p) => lineFinalProductIdSet.value.has(Number(p.id)))
}
const filteredProductOptions = computed(() => {
  if (!selectedLine.value) return allProducts.value
  return lineFinalProductsByLine.value[String(selectedLine.value)] || []
})
const newBatchProductOptions = computed(() => {
  if (!newBatch.line) return allProducts.value
  return lineFinalProductsByLine.value[String(newBatch.line)] || []
})

// --- フィルタ ---
const selectedLine = ref('')
const selectedProduct = ref('')
const batchStatusFilter = ref('OPEN')

// --- バッチ一覧 ---
const batches = ref([])
const loadingBatches = ref(false)
const loading = computed(() => loadingBatches.value)

// --- 新規バッチ ---
const newBatch = reactive({ product: '', line: '', quantity: 1, plan_date: '', lot_no: '' })
const preparing = ref(false)
const showNewBatchSection = ref(true)
const newBatchSectionRef = ref(null)

// --- バッチ詳細 ---
const activeBatchId = ref(null)
const activeBatch = ref(null)
const reviewRole = ref('')
const units = ref([])
const loadingUnits = ref(false)
const actionLoading = ref(false)
const templateBlocks = ref([])
const preferredProcessId = ref('')
const lockedLineIdFromRoute = ref('')
const isLineLockedFromRoute = computed(() => Boolean(lockedLineIdFromRoute.value))

const processIdFromBlock = (block) => {
  if (!block) return ''
  return String(
    block.process_id
    ?? block.process
    ?? block.production_process
    ?? block.production_process_id
    ?? block.process_master
    ?? block.process_master_id
    ?? ''
  )
}

const isBlockedByPreferredProcess = (block) => {
  const preferred = String(preferredProcessId.value || '')
  if (!preferred) return false
  const blockProcessId = processIdFromBlock(block)
  if (!blockProcessId) return false
  return blockProcessId !== preferred
}

// --- モーダル ---
const modalUnit = ref(null)
const modalResponses = ref({})
const modalSelectedBlockId = ref(null)
const savingBlock = ref(null)

// --- ヘルパー ---
const formatDateTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('ja-JP')
}

const reviewRoleLabel = computed(() => {
  if (reviewRole.value === 'leader') return 'リーダ'
  if (reviewRole.value === 'supervisor') return '班長'
  return ''
})

const processProgressChips = (progressList) => {
  if (!Array.isArray(progressList) || !progressList.length) return [{ key: 'none', label: '-', done: false }]
  return progressList.map((p, idx) => {
    const doneUnits = Number(p.done_units ?? 0)
    const totalUnits = Number(p.total_units ?? 0)
    return {
      key: `${p.process_block_id || idx}`,
      label: `${p.process_code || p.process_name || '-'}:${doneUnits}/${totalUnits}`,
      done: totalUnits > 0 && doneUnits >= totalUnits,
    }
  })
}

const getBlockCheckerName = (unit, blockId) => {
  if (!unit?.checks || !Array.isArray(unit.checks)) return ''
  const checks = unit.checks
    .filter((c) => Number(c.process_block_id) === Number(blockId) && c.checked_by_name)
    .sort((a, b) => {
      const ta = a?.checked_at ? new Date(a.checked_at).getTime() : 0
      const tb = b?.checked_at ? new Date(b.checked_at).getTime() : 0
      return tb - ta
    })
  return checks[0]?.checked_by_name || ''
}


const statusClass = (st) => {
  switch (st) {
    case 'PENDING': return 'pending'
    case 'IN_PROGRESS': return 'in-progress'
    case 'COMPLETED': return 'completed'
    case 'APPROVED': return 'approved'
    case 'OPEN': return 'in-progress'
    case 'LEADER_CONFIRMED': return 'completed'
    case 'SUPERVISOR_CONFIRMED': return 'approved'
    default: return 'pending'
  }
}

const statusLabel = (st) => {
  switch (st) {
    case 'PENDING': return '未着手'
    case 'IN_PROGRESS': return '入力中'
    case 'COMPLETED': return '完了'
    case 'APPROVED': return '承認済'
    case 'OPEN': return '実施中'
    case 'LEADER_CONFIRMED': return 'リーダ確認済'
    case 'SUPERVISOR_CONFIRMED': return '班長確認済'
    default: return st
  }
}

const statusShort = (st) => {
  switch (st) {
    case 'PENDING': return '-'
    case 'IN_PROGRESS': return '中'
    case 'COMPLETED': return '済'
    case 'APPROVED': return '認'
    default: return '-'
  }
}

const recordTypeLabel = (rt) => {
  switch (rt) {
    case 'CHECK': return 'C'
    case 'NUMERIC': return 'N'
    case 'TEXT': return 'T'
    default: return rt
  }
}

// --- 工程ロック判定 ---
const getUnitProcessProgress = (unit) => {
  return unit.process_progress || []
}

const isBlockLocked = (unit, block) => {
  const progress = getUnitProcessProgress(unit)
  for (const pp of progress) {
    if (pp.process_block_id === block.id) return false
    // この工程ブロックより前の工程で、必須項目が未完了ならロック
    if (!pp.complete && pp.total > 0) return true
  }
  return false
}

const isBlockLockedForModal = (block) => {
  if (!modalUnit.value) return false
  return isBlockLocked(modalUnit.value, block)
}

const getBlockProgress = (block) => {
  if (!modalUnit.value) return null
  const progress = getUnitProcessProgress(modalUnit.value)
  return progress.find((pp) => pp.process_block_id === block.id) || null
}

// --- マトリクスセル表示 ---
const getCheckForItem = (unit, item) => {
  if (!unit.checks) return null
  return unit.checks.find((c) => c.item === item.id)
}

const cellDisplay = (unit, item) => {
  const check = getCheckForItem(unit, item)
  if (!check) return ''
  if (item.record_type === 'CHECK') {
    if (check.judgement === 'OK') return '✓'
    if (check.judgement === 'NG') return '✗'
    return ''
  }
  if (item.record_type === 'NUMERIC') {
    return check.numeric_value != null ? check.numeric_value : ''
  }
  return check.text_value || ''
}

const cellClass = (unit, block, item) => {
  if (isBlockedByPreferredProcess(block)) return 'cell-disabled-by-process'
  if (isBlockLocked(unit, block)) return 'cell-locked'
  const check = getCheckForItem(unit, item)
  if (!check) return 'cell-empty'
  if (item.record_type === 'CHECK') {
    if (check.judgement === 'OK') return 'cell-ok'
    if (check.judgement === 'NG') return 'cell-ng'
  }
  if (check.numeric_value != null || check.text_value) return 'cell-filled'
  return 'cell-empty'
}

// --- データ取得 ---
const loadMasters = async () => {
  try {
    const [lineRes, productRes] = await Promise.all([
      api.lines.getLines({ line_type: 'PROD', page_size: 1000 }),
      api.products.getProducts({ is_active: true, is_line_final_product: true, page_size: 1000 }),
    ])
    allLines.value = lineRes.data?.results || lineRes.data || []
    allProducts.value = productRes.data?.results || productRes.data || []
  } catch (error) {
    console.error('マスタ取得に失敗:', error)
  }
}

const ensureLineFinalProducts = async (lineId) => {
  if (!lineId) return allProducts.value
  const key = String(lineId)
  if (Object.prototype.hasOwnProperty.call(lineFinalProductsByLine.value, key)) {
    return lineFinalProductsByLine.value[key]
  }
  try {
    const res = await api.products.getLineFinalCandidates(lineId)
    const products = parseLineFinalCandidates(res?.data)
    lineFinalProductsByLine.value = {
      ...lineFinalProductsByLine.value,
      [key]: products,
    }
    return products
  } catch (error) {
    console.error('ライン最終品候補の取得に失敗:', error)
    lineFinalProductsByLine.value = {
      ...lineFinalProductsByLine.value,
      [key]: [],
    }
    return []
  }
}

const loadBatches = async () => {
  loadingBatches.value = true
  try {
    const params = {}
    const effectiveLineId = lockedLineIdFromRoute.value || selectedLine.value
    if (effectiveLineId) params.line = effectiveLineId
    if (selectedProduct.value) params.product = selectedProduct.value
    if (batchStatusFilter.value) params.status = batchStatusFilter.value
    const res = await api.integratedChecksheets.listBatches(params)
    batches.value = res.data?.results || res.data || []
  } catch {
    batches.value = []
  } finally {
    loadingBatches.value = false
  }
}

const loadBatchUnits = async (batchId) => {
  loadingUnits.value = true
  try {
    const [unitsRes, batchRes] = await Promise.all([
      api.integratedChecksheets.getBatchUnits(batchId),
      api.integratedChecksheets.getBatch(batchId),
    ])
    units.value = unitsRes.data || []
    const batchData = batchRes.data
    // テンプレートの工程ブロック情報を取得
    if (batchData.template) {
      const tmplRes = await api.integratedChecksheets.getTemplate(batchData.template)
      templateBlocks.value = tmplRes.data?.process_blocks || []
    }
  } catch (error) {
    console.error('台目取得に失敗:', error)
    units.value = []
    templateBlocks.value = []
  } finally {
    loadingUnits.value = false
  }
}

const openBatchDetail = async (batch) => {
  activeBatchId.value = batch.id
  activeBatch.value = batch
  await loadBatchUnits(batch.id)
}

const canLeaderConfirm = (b) => ['OPEN', 'COMPLETED'].includes(b.status)
const canShowSupervisorConfirm = (b) => b.status === 'LEADER_CONFIRMED'

const leaderConfirm = async (batch) => {
  if (!window.confirm('リーダ確認を実行します。全台目の必須項目が完了している必要があります。よろしいですか？')) return
  actionLoading.value = true
  try {
    await api.integratedChecksheets.leaderConfirm(batch.id)
    await loadBatches()
    alert('リーダ確認しました。')
  } catch (e) {
    alert(`リーダ確認に失敗しました: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const supervisorConfirm = async (batch) => {
  if (!isSupervisorUser.value) {
    alert('班長のみ班長確認を実行できます。')
    return
  }
  if (!window.confirm('班長確認を実行します。よろしいですか？')) return
  actionLoading.value = true
  try {
    await api.integratedChecksheets.supervisorConfirm(batch.id)
    await loadBatches()
    alert('班長確認しました。')
  } catch (e) {
    alert(`班長確認に失敗しました: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const openReviewByRole = async (batch, role) => {
  reviewRole.value = role || ''
  await openBatchDetail(batch)
}

const closeBatchDetail = () => {
  activeBatchId.value = null
  activeBatch.value = null
  reviewRole.value = ''
  units.value = []
  templateBlocks.value = []
}

const refreshAll = () => {
  loadBatches()
  if (activeBatchId.value) {
    loadBatchUnits(activeBatchId.value)
  }
}

const openNewBatchSection = () => {
  showNewBatchSection.value = true
  newBatchSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const showBackToProcessInput = computed(() =>
  String(route.query?.source || '') === 'mobile_process_input'
)

const backToProcessInput = () => {
  const lineId = selectedLine.value || ''
  const processId = preferredProcessId.value || ''
  router.push({
    path: '/production/mobile-process-input',
    query: {
      ...(lineId ? { line_id: String(lineId) } : {}),
      ...(processId ? { process_id: String(processId) } : {}),
    },
  })
}

const applyInitialFiltersFromQuery = async () => {
  preferredProcessId.value = route.query?.process_id ? String(route.query.process_id) : ''
  const lineIdFromQuery = route.query?.line_id ? String(route.query.line_id) : ''
  lockedLineIdFromRoute.value = lineIdFromQuery || ''
  if (!lineIdFromQuery) return
  const exists = allLines.value.some((l) => String(l.id) === lineIdFromQuery)
  if (!exists) return
  selectedLine.value = lineIdFromQuery
  await ensureLineFinalProducts(lineIdFromQuery)
}

// --- バッチ作成 ---
const prepareBatch = async () => {
  if (!canEdit.value) return
  if (!newBatch.product || !newBatch.line || !newBatch.quantity || !newBatch.plan_date) return
  preparing.value = true
  try {
    const res = await api.integratedChecksheets.prepareBatch({
      product: newBatch.product,
      line: newBatch.line,
      quantity: newBatch.quantity,
      plan_date: newBatch.plan_date,
      lot_no: newBatch.lot_no,
    })
    const created = res.data
    await loadBatches()
    if (created?.id) {
      await openBatchDetail(created)
    }
    // フォーム初期化
    newBatch.quantity = 1
    newBatch.lot_no = ''
    newBatch.plan_date = ''
  } catch (error) {
    alert(`バッチ作成に失敗しました: ${error.response?.data?.detail || error.message}`)
  } finally {
    preparing.value = false
  }
}

// --- モーダル ---
const modalVisibleBlocks = computed(() => {
  if (!modalSelectedBlockId.value) return templateBlocks.value
  return templateBlocks.value.filter((b) => b.id === modalSelectedBlockId.value)
})
const modalCurrentBlock = computed(() => {
  if (modalVisibleBlocks.value.length !== 1) return null
  return modalVisibleBlocks.value[0]
})
const modalHeaderStatusCode = computed(() => {
  const block = modalCurrentBlock.value
  if (!block) return modalUnit.value?.status || 'PENDING'
  if (isBlockLockedForModal(block)) return 'PENDING'
  const p = getBlockProgress(block)
  if (!p || Number(p.total || 0) <= 0) return 'PENDING'
  const done = Number(p.done || 0)
  const total = Number(p.total || 0)
  if (done <= 0) return 'PENDING'
  if (done >= total) return 'COMPLETED'
  return 'IN_PROGRESS'
})
const modalHeaderStatusLabel = computed(() => {
  const block = modalCurrentBlock.value
  if (!block) return statusLabel(modalUnit.value?.status)
  if (isBlockLockedForModal(block)) return 'ロック中'
  return statusLabel(modalHeaderStatusCode.value)
})
const currentModalUnitIndex = computed(() => {
  if (!modalUnit.value) return -1
  return units.value.findIndex((u) => u.id === modalUnit.value.id)
})
const canMovePrevUnit = computed(() => currentModalUnitIndex.value > 0)
const canMoveNextUnit = computed(() => {
  const idx = currentModalUnitIndex.value
  return idx >= 0 && idx < units.value.length - 1
})

const openUnitModal = (unit, blockId = null) => {
  if (!canView.value) return
  let resolvedBlockId = blockId || null
  if (!resolvedBlockId && preferredProcessId.value) {
    const matched = templateBlocks.value.find((b) => !isBlockedByPreferredProcess(b))
    if (matched?.id) resolvedBlockId = matched.id
  }
  if (resolvedBlockId) {
    const targetBlock = templateBlocks.value.find((b) => Number(b.id) === Number(resolvedBlockId))
    if (targetBlock && isBlockedByPreferredProcess(targetBlock)) return
  }
  modalUnit.value = unit
  modalSelectedBlockId.value = resolvedBlockId
  // 既存チェック結果を modalResponses にマッピング
  const resp = {}
  if (unit.checks) {
    for (const c of unit.checks) {
      resp[c.item] = {
        judgement: c.judgement || '',
        numeric_value: c.numeric_value,
        text_value: c.text_value || '',
      }
    }
  }
  // テンプレートの全項目について空エントリを用意
  for (const block of templateBlocks.value) {
    for (const item of block.items) {
      if (!resp[item.id]) {
        resp[item.id] = { judgement: '', numeric_value: null, text_value: '' }
      }
    }
  }
  modalResponses.value = resp
}

const moveModalUnit = (delta) => {
  if (!modalUnit.value) return
  const currentIdx = currentModalUnitIndex.value
  if (currentIdx < 0) return
  const nextIdx = currentIdx + delta
  if (nextIdx < 0 || nextIdx >= units.value.length) return
  const nextUnit = units.value[nextIdx]
  if (!nextUnit) return
  openUnitModal(nextUnit, modalSelectedBlockId.value)
}

const closeModal = () => {
  modalUnit.value = null
  modalResponses.value = {}
  modalSelectedBlockId.value = null
}

const setJudgement = (itemId, val) => {
  if (!canEdit.value) return
  if (!modalResponses.value[itemId]) {
    modalResponses.value[itemId] = { judgement: '', numeric_value: null, text_value: '' }
  }
  // トグル: 同じ値をクリックしたらクリア
  modalResponses.value[itemId].judgement = modalResponses.value[itemId].judgement === val ? '' : val
}

const setNumeric = (itemId, val) => {
  if (!canEdit.value) return
  if (!modalResponses.value[itemId]) {
    modalResponses.value[itemId] = { judgement: '', numeric_value: null, text_value: '' }
  }
  modalResponses.value[itemId].numeric_value = val !== '' ? parseFloat(val) : null
}

const setText = (itemId, val) => {
  if (!canEdit.value) return
  if (!modalResponses.value[itemId]) {
    modalResponses.value[itemId] = { judgement: '', numeric_value: null, text_value: '' }
  }
  modalResponses.value[itemId].text_value = val
}

// 工程ブロック単位で保存
const saveBlockChecks = async (block) => {
  if (!canEdit.value) return
  if (!modalUnit.value) return
  const savedUnitId = modalUnit.value.id
  savingBlock.value = block.id
  try {
    const checks = []
    for (const item of block.items) {
      const r = modalResponses.value[item.id]
      if (!r) continue
      const entry = { item: item.id }
      if (item.record_type === 'CHECK') {
        entry.judgement = r.judgement || ''
      } else if (item.record_type === 'NUMERIC') {
        entry.numeric_value = r.numeric_value
      } else {
        entry.text_value = r.text_value || ''
      }
      checks.push(entry)
    }
    const res = await api.integratedChecksheets.saveChecks(modalUnit.value.id, {
      process_block_id: block.id,
      checks,
    })
    // モーダルのunitを更新
    const updatedUnit = res.data
    updateUnitInList(updatedUnit)
    modalUnit.value = updatedUnit
    // バッチ一覧も更新
    loadBatches()

    // 保存成功後、自動で次の一台へ移動（末尾はそのまま）
    const currentIdx = units.value.findIndex((u) => u.id === savedUnitId)
    if (currentIdx >= 0 && currentIdx + 1 < units.value.length) {
      const nextUnit = units.value[currentIdx + 1]
      if (nextUnit) openUnitModal(nextUnit, modalSelectedBlockId.value)
    }
  } catch (error) {
    alert(`保存に失敗しました: ${error.response?.data?.detail || error.message}`)
  } finally {
    savingBlock.value = null
  }
}

const updateUnitInList = (updatedUnit) => {
  const idx = units.value.findIndex((u) => u.id === updatedUnit.id)
  if (idx >= 0) {
    units.value[idx] = updatedUnit
  }
}

// --- ウォッチ ---
watch([() => selectedLine.value, () => selectedProduct.value, () => batchStatusFilter.value], () => {
  loadBatches()
})

watch(() => selectedLine.value, async () => {
  await ensureLineFinalProducts(selectedLine.value)
  if (!filteredProductOptions.value.some((p) => String(p.id) === String(selectedProduct.value))) {
    selectedProduct.value = ''
  }
  if (!selectedProduct.value && filteredProductOptions.value.length === 1) {
    selectedProduct.value = filteredProductOptions.value[0].id
  }
})

watch(() => newBatch.line, async () => {
  await ensureLineFinalProducts(newBatch.line)
  if (!newBatchProductOptions.value.some((p) => String(p.id) === String(newBatch.product))) {
    newBatch.product = ''
  }
  if (!newBatch.product && newBatchProductOptions.value.length === 1) {
    newBatch.product = newBatchProductOptions.value[0].id
  }
})

// --- マウント ---
onMounted(async () => {
  if (!canView.value) return
  await loadMasters()
  await applyInitialFiltersFromQuery()
  await loadBatches()
})
</script>

<style scoped>
.ics-operation {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: #111827;
  font-family: 'Meiryo', 'Yu Gothic UI', 'Yu Gothic', sans-serif;
  font-size: 14px;
}
.page-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.page-title { margin: 0; font-size: 20px; font-weight: 700; color: #0f172a; }
.page-actions { display: flex; gap: 8px; }

/* パネル */
.panel {
  background: #fff;
  border: 1px solid #d5d8dc;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.panel-title { margin: 0; font-size: 15px; font-weight: 700; color: #0f172a; }
.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.batch-meta { font-size: 13px; font-weight: 400; color: #6b7280; }

/* フィルタ */
.filter-panel {
  display: block;
}
.filter-form {
  justify-content: flex-start;
}
.filter-form label {
  margin: 0;
  width: auto;
  flex: 0 0 auto;
}
.filter-panel label,
.prepare-form label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #334155;
}
.field-label {
  white-space: nowrap;
  min-width: 56px;
}
.filter-panel select,
.filter-panel input,
.prepare-form select,
.prepare-form input {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}
.prepare-form {
  display: flex;
  gap: 8px;
  align-items: end;
  flex-wrap: wrap;
}

.process-progress-list {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.process-progress-chip {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 1.4;
  background: #eef2f7;
  color: #334155;
  border: 1px solid #d7dee8;
}
.process-progress-chip.done {
  background: #16a34a;
  border-color: #15803d;
  color: #ffffff;
}
.required-mark { color: #dc2626; font-size: 12px; margin-left: 2px; }

/* テーブル */
.table-wrap {
  overflow: auto;
  border: 1px solid #dde2ea;
  border-radius: 4px;
}
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 5px 7px; border-bottom: 1px solid #edf1f5; text-align: left; }
.data-table th { background: #f7f9fb; font-size: 12px; font-weight: 700; white-space: nowrap; }
.data-table.compact th, .data-table.compact td { padding: 4px 6px; font-size: 13px; }
.row-selected { background: #eff6ff; }
.action-cell { display: flex; gap: 4px; }

/* ステータスチップ */
.status-chip {
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid transparent;
  display: inline-block;
  white-space: nowrap;
}
.status-chip.mini { padding: 1px 5px; font-size: 10px; }
.status-chip.pending { background: #f3f4f6; border-color: #d1d5db; color: #6b7280; }
.status-chip.in-progress { background: #dbeafe; border-color: #93c5fd; color: #1d4ed8; }
.status-chip.completed { background: #d1fae5; border-color: #6ee7b7; color: #065f46; }
.status-chip.approved { background: #d1fae5; border-color: #34d399; color: #065f46; font-weight: 800; }

/* ボタン */
.btn-primary, .btn-secondary, .btn-sm {
  border-radius: 6px;
  padding: 6px 12px;
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
.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { background: #93c5fd; border-color: #93c5fd; cursor: not-allowed; }
.btn-secondary { background: #fff; color: #2563eb; border-color: #2563eb; }
.btn-secondary:hover { background: #eff6ff; }
.btn-close { background: none; border: none; font-size: 22px; cursor: pointer; color: #6b7280; padding: 0 4px; line-height: 1; }
.no-data { color: #6b7280; padding: 8px 0; font-size: 13px; }

/* マトリクス */
.matrix-panel { overflow: hidden; }
.matrix-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.matrix-scroll { overflow: auto; max-height: calc(100vh - 420px); border: 1px solid #dde2ea; border-radius: 4px; }
.matrix-table { border-collapse: collapse; }
.matrix-table th, .matrix-table td { padding: 3px 6px; border: 1px solid #e5e7eb; font-size: 12px; white-space: nowrap; }
.th-process { min-width: 60px; position: sticky; left: 0; z-index: 2; background: #f7f9fb; }
.th-item { min-width: 140px; position: sticky; left: 60px; z-index: 2; background: #f7f9fb; }
.th-type { min-width: 28px; position: sticky; left: 200px; z-index: 2; background: #f7f9fb; text-align: center; }
.th-unit { min-width: 52px; text-align: center; cursor: pointer; }
.th-unit:hover { background: #dbeafe; }
.unit-header { display: flex; flex-direction: column; align-items: center; gap: 2px; }

.td-process { position: sticky; left: 0; z-index: 1; background: #fff; font-size: 11px; color: #6b7280; }
.td-item { position: sticky; left: 60px; z-index: 1; background: #fff; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
.td-type { position: sticky; left: 200px; z-index: 1; background: #fff; text-align: center; }
.td-cell { text-align: center; cursor: pointer; min-width: 52px; }
.td-cell:hover { background: #f0f4ff; }
.td-cell.cell-disabled-by-process {
  cursor: not-allowed;
  background: #f3f4f6;
  color: #9ca3af;
}
.td-cell.cell-disabled-by-process:hover { background: #f3f4f6; }

.item-standard { font-size: 10px; color: #9ca3af; display: block; }

.type-tag { font-size: 10px; font-weight: 700; padding: 1px 4px; border-radius: 3px; }
.type-tag.type-CHECK { background: #dbeafe; color: #1d4ed8; }
.type-tag.type-NUMERIC { background: #fef3c7; color: #92400e; }
.type-tag.type-TEXT { background: #e0e7ff; color: #3730a3; }

/* マトリクス工程ヘッダー */
.block-header-row td { background: #1e293b; color: #fff; font-weight: 700; font-size: 13px; padding: 4px 8px; }
.block-header-cell {
  position: sticky;
  left: 0;
}
.block-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.block-title-left { display: inline-flex; align-items: center; gap: 6px; }
.block-title-right { font-size: 11px; color: #cbd5e1; font-weight: 600; }
.block-checker-cell {
  background: #1e293b;
  color: #cbd5e1;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  min-width: 52px;
  cursor: pointer;
}
.block-checker-cell:hover { background: #334155; color: #ffffff; }
.block-checker-cell.cell-disabled-by-process {
  cursor: not-allowed;
  background: #334155;
  color: #94a3b8;
}
.block-checker-cell.cell-disabled-by-process:hover {
  background: #334155;
  color: #94a3b8;
}
.sketch-badge { font-size: 10px; background: #fbbf24; color: #78350f; padding: 1px 6px; border-radius: 3px; margin-left: 6px; font-weight: 400; }

/* セル状態 */
.cell-locked { background: #f3f4f6; color: #d1d5db; }
.cell-empty { color: #d1d5db; }
.cell-ok { background: #ecfdf5; color: #059669; font-weight: 700; }
.cell-ng { background: #fef2f2; color: #dc2626; font-weight: 700; }
.cell-filled { background: #f0fdf4; color: #166534; }
.lock-icon { font-size: 12px; }

/* モーダル */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 8px;
  overflow-y: auto;
}
.modal-content {
  background: #fff;
  border-radius: 8px;
  width: calc(100vw - 16px);
  max-width: none;
  height: calc(100vh - 16px);
  height: calc(100dvh - 16px);
  max-height: calc(100vh - 16px);
  max-height: calc(100dvh - 16px);
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 30px rgba(0,0,0,0.2);
}
.modal-header {
  position: relative;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
}
.modal-header h3 {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  margin: 0;
  font-size: 16px;
  white-space: nowrap;
}
.modal-header-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.modal-body { flex: 1; overflow-y: auto; padding: 12px 16px; }
.modal-save-bar {
  position: sticky;
  bottom: 0;
  background: linear-gradient(to bottom, rgba(248, 250, 252, 0.75), #f8fafc 35%);
  padding: 10px 0 4px;
  margin-top: 8px;
}
.modal-save-bar-main {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
.modal-unit-label {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  font-weight: 700;
  color: #0f172a;
  pointer-events: none;
}

@media (max-width: 1200px) {
  .modal-overlay { padding: 4px; }
  .modal-content {
    width: calc(100vw - 8px);
    height: calc(100vh - 8px);
    height: calc(100dvh - 8px);
    max-height: calc(100vh - 8px);
    max-height: calc(100dvh - 8px);
    border-radius: 6px;
  }
}

/* 工程セクション */
.process-section {
  margin-bottom: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}
.process-section.ratio-4-1 {
  display: grid;
  grid-template-rows: auto 4fr 1fr;
  min-height: min(72dvh, 820px);
}
.process-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #1e293b;
  color: #fff;
  font-size: 14px;
}
.process-section-header.locked { background: #9ca3af; }
.progress-text { font-size: 12px; font-weight: 400; color: #94a3b8; }
.lock-label { font-size: 11px; color: #fbbf24; margin-left: auto; }

/* 略図 */
.sketch-placeholder {
  position: relative;
  border-bottom: 1px solid #e5e7eb;
  max-height: 340px;
  overflow: hidden;
}
.process-section.ratio-4-1 .sketch-placeholder {
  max-height: none;
  height: 100%;
}
.sketch-img { width: 100%; object-fit: contain; max-height: 340px; }
.process-section.ratio-4-1 .sketch-img {
  max-height: none;
  height: 100%;
}
.sketch-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.35);
  font-size: 44px;
  color: #1f2937;
  font-weight: 800;
  letter-spacing: 0.02em;
  text-align: center;
  line-height: 1.2;
  z-index: 1;
}
.sketch-overlay::before {
  content: '';
  position: absolute;
  width: min(92%, 720px);
  height: 112px;
  background: rgba(255, 255, 255, 0.88);
  border: 2px solid rgba(107, 114, 128, 0.35);
  border-radius: 999px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
.sketch-overlay span {
  position: relative;
  z-index: 2;
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.75);
}

/* チェック項目リスト */
.items-list { padding: 6px 10px; }
.process-section.ratio-4-1 .items-list {
  height: 100%;
  overflow: auto;
}
.item-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 1px solid #f3f4f6;
}
.item-row:last-child { border-bottom: none; }
.item-label-area { flex: 1; min-width: 0; }
.item-name { font-size: 13px; font-weight: 500; }
.item-hint { font-size: 11px; color: #9ca3af; margin-left: 4px; }
.item-input-area { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

/* OK/NGボタン */
.judge-btn {
  padding: 4px 14px;
  border-radius: 4px;
  border: 2px solid #d1d5db;
  background: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.judge-btn.ok { color: #059669; border-color: #a7f3d0; }
.judge-btn.ok.active { background: #059669; color: #fff; border-color: #059669; }
.judge-btn.ng { color: #dc2626; border-color: #fca5a5; }
.judge-btn.ng.active { background: #dc2626; color: #fff; border-color: #dc2626; }

/* 数値・テキスト入力 */
.numeric-input, .text-input {
  padding: 4px 6px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  width: 100px;
}
.text-input { width: 140px; }
.unit-label { font-size: 12px; color: #6b7280; }

/* ロック中メッセージ */
.locked-message {
  padding: 12px;
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  background: #f9fafb;
}

</style>
