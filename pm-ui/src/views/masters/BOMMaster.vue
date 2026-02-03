<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">構成マスタ（BOM）</h1>
      <div class="page-actions">
        <button @click="fetchBOMs" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
        <button @click="openWhereUsedDialog" class="btn-info">逆展開</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>親製品（品番/品名）</label>
          <input
            v-model="filters.search"
            @keyup.enter="fetchBOMs"
            placeholder="品番・品名で検索"
          />
        </div>
        <div class="filter-field">
          <label>最終品</label>
          <select v-model="filters.is_final">
            <option value="">すべて</option>
            <option value="true">最終</option>
            <option value="false">それ以外</option>
          </select>
        </div>
        <div class="filter-field">
          <label>ライン最終品</label>
          <select v-model="filters.is_line_final">
            <option value="">すべて</option>
            <option value="true">はい</option>
            <option value="false">いいえ</option>
          </select>
        </div>
        <div class="filter-field">
          <label>連産品</label>
          <select v-model="filters.is_coproduct">
            <option value="">すべて</option>
            <option value="true">はい</option>
            <option value="false">いいえ</option>
          </select>
        </div>
        <div class="filter-field">
          <label>版</label>
          <input
            v-model="filters.version"
            @keyup.enter="fetchBOMs"
            placeholder="版で検索"
          />
        </div>
        <div class="filter-field">
          <label>作成日 From</label>
          <input type="date" v-model="filters.created_from" />
        </div>
        <div class="filter-field">
          <label>作成日 To</label>
          <input type="date" v-model="filters.created_to" />
        </div>
        <div class="filter-field">
          <label>有効</label>
          <select v-model="filters.is_active">
            <option value="">すべて</option>
            <option value="true">有効</option>
            <option value="false">無効</option>
          </select>
        </div>
        <div class="filter-actions">
          <button @click="fetchBOMs" class="btn-primary">検索</button>
          <button @click="resetFilters" class="btn-secondary">リセット</button>
        </div>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>親製品</th>
            <th>最終品</th>
            <th>ライン最終品</th>
            <th>版</th>
            <th>連産品</th>
            <th>有効開始日</th>
            <th>有効終了日</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="bom in boms" :key="bom.id">
            <td>{{ bom.id }}</td>
            <td>{{ getParentProductCode(bom) }}</td>
            <td>{{ bom.parent_is_final ? '最終' : '' }}</td>
            <td>{{ bom.parent_is_line_final ? 'はい' : '' }}</td>
            <td>{{ bom.version }}</td>
            <td>{{ bom.is_coproduct ? 'はい' : '' }}</td>
            <td>{{ bom.valid_from }}</td>
            <td>{{ bom.valid_to || '-' }}</td>
            <td>{{ bom.is_active ? '有効' : '無効' }}</td>
            <td>
              <button @click="viewDetails(bom)" class="btn-sm">詳細</button>
              <button @click="openDetailsInNewTab(bom)" class="btn-sm">別タブ</button>
              <button @click="viewTreeOnly(bom)" class="btn-sm">階層図</button>
              <button @click="editBOM(bom)" class="btn-sm">編集</button>
              <button @click="deleteBOM(bom.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="boms.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? 'BOM編集' : 'BOM新規作成' }}</h2>
        <form @submit.prevent="saveBOM">
          <div class="form-group">
            <label>親製品 *</label>
            <input
              class="filter-input"
              type="text"
              v-model="parentProductFilter"
              placeholder="品番/品名で絞り込み"
              :disabled="isEdit"
            />
            <select v-model="formData.parent_product" required :disabled="isEdit">
              <option value="">選択してください</option>
              <option v-for="product in filteredParentProducts" :key="product.id" :value="product.id">
                {{ product.product_code }} - {{ product.product_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_coproduct" :disabled="isEdit" />
              連産品BOM（仮想セット品番を親にして複数製品を同時生産）
            </label>
            <p v-if="formData.is_coproduct" class="helper-text">
              親製品は仮想セット品番（製品マスタで「仮想セット」をオン）から選択してください。
            </p>
          </div>
          <div class="form-group">
            <label>版 *</label>
            <input v-model="formData.version" required />
          </div>
          <div class="form-group">
            <label>有効開始日 *</label>
            <input type="date" v-model="formData.valid_from" required />
          </div>
          <div class="form-group">
            <label>有効終了日</label>
            <input type="date" v-model="formData.valid_to" />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" />
              有効
            </label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 詳細ダイアログ -->
    <div
      v-if="showDetailsDialog || isStandaloneDetail"
      :class="['modal-overlay', { 'as-page': isStandaloneDetail }]"
      @click.self="handleDetailsBackdropClick"
    >
      <div :class="['modal-content', 'modal-large', { 'detail-page-card': isStandaloneDetail }]">
        <h2>BOM詳細</h2>
        <div class="details-section summary-grid">
          <div class="summary-item">
            <span class="summary-label">BOM ID</span>
            <span class="summary-value">{{ selectedBOM.id }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">親製品</span>
            <span class="summary-value">{{ getProductName(selectedBOM.parent_product) }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">版</span>
            <span class="summary-value">{{ selectedBOM.version }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">有効期間</span>
            <span class="summary-value">{{ selectedBOM.valid_from }} ～ {{ selectedBOM.valid_to || '無期限' }}</span>
          </div>
        </div>
        <p v-if="isPhantom(selectedBOM.parent_product)" class="phantom-info">
          この親製品は見なし組立です。リードタイム計算や展開ロジックの扱いに注意してください。
        </p>
        <div v-if="bomTree" class="tree-section">
          <h3>階層表示</h3>
          <div class="tree-controls">
            <button type="button" class="btn-sm" @click="expandAllNodes">全展開</button>
            <button type="button" class="btn-sm" @click="collapseAllNodes">全折りたたみ</button>
          </div>
          <div class="tree-grid-container">
            <table class="tree-grid">
              <thead>
                <tr>
                  <th>部番</th>
                  <th class="level-col">階層</th>
                  <th class="qty-col">数量</th>
                  <th class="phantom-col">みなし組立</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in treeRows" :key="row.key">
                  <td>
                    <span class="tree-line">{{ row.prefix }}</span>
                    <button
                      v-if="row.hasChildren"
                      @click="toggleNode(row.key)"
                      class="expand-btn"
                    >
                      {{ row.isExpanded ? '－' : '＋' }}
                    </button>
                    <span v-else class="expand-placeholder"></span>
                    {{ row.product }}
                  </td>
                  <td class="level-col">{{ row.level }}</td>
                  <td class="qty-col">{{ row.quantity }}</td>
                  <td class="phantom-col">{{ row.isPhantom ? '1' : '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <h3>構成品目</h3>
        <div class="item-form">
          <div class="form-row">
            <div class="form-group">
              <label>子製品 *</label>
              <input
                class="filter-input"
                type="text"
                v-model="childProductFilter"
                placeholder="品番/品名で絞り込み"
              />
              <select v-model="itemForm.child_product" required>
                <option value="">選択してください</option>
                <option v-for="product in filteredChildProducts" :key="product.id" :value="product.id">
                  {{ product.product_code }} - {{ product.product_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>数量 *</label>
              <input type="number" step="1" min="1" v-model.number="itemForm.quantity" required />
            </div>
            <div class="form-group">
              <label>ロス率</label>
              <input type="number" step="0.001" min="0" v-model="itemForm.loss_rate" />
            </div>
            <div class="form-group">
              <label>調達区分</label>
              <select v-model="itemForm.sourcing_type">
                <option v-for="option in sourcingTypeOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>仕入先</label>
              <select v-model="itemForm.supplier" :disabled="itemForm.sourcing_type === 'MAKE'">
                <option value="">選択しない</option>
                <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
                  {{ supplier.supplier_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>工程 *</label>
              <select v-model="itemForm.process" :required="itemForm.sourcing_type === 'MAKE' || itemForm.sourcing_type === 'SUBCON'" :disabled="itemForm.sourcing_type === 'BUY'">
                <option value="">選択してください</option>
                <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                  {{ proc.process_code }} - {{ proc.process_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>ライン</label>
              <select v-model="itemForm.line" :disabled="itemForm.sourcing_type === 'BUY'">
                <option value="">選択しない</option>
                <option v-for="line in lines" :key="line.id" :value="line.id">
                  {{ line.line_code }} - {{ line.line_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>時間単位</label>
              <select v-model="itemForm.time_unit" :disabled="itemForm.sourcing_type === 'BUY'">
                <option value="MINUTE">分</option>
                <option value="DAY">日</option>
              </select>
            </div>
            <div class="form-group">
              <label>リードタイム(日)</label>
              <input
                type="number"
                min="0"
                v-model.number="itemForm.lead_time_days"
              />
            </div>
            <div class="form-group">
              <label>所要時間(分)</label>
              <input type="number" min="1" v-model.number="itemForm.duration_min" :disabled="itemForm.time_unit === 'DAY' || itemForm.sourcing_type === 'BUY'" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group full-width">
              <label>備考</label>
              <input type="text" v-model="itemForm.remark" />
            </div>
          </div>
          <div class="form-actions">
            <button type="button" class="btn-primary" @click="saveBOMItem">
              {{ editingItemId ? '明細を更新' : '明細を追加' }}
            </button>
            <button type="button" class="btn-secondary" @click="resetItemForm" :disabled="!editingItemId">
              キャンセル
            </button>
          </div>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th>子製品</th>
              <th>数量</th>
              <th>ロス率</th>
              <th>調達区分</th>
              <th>仕入先</th>
              <th>工程</th>
              <th>ライン</th>
              <th>時間</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in bomItems" :key="item.id">
              <td>{{ getChildProductCode(item) }}</td>
              <td>{{ formatQuantity(item.quantity) }}</td>
              <td>{{ item.loss_rate || '-' }}</td>
              <td>{{ getSourcingTypeLabel(item.sourcing_type) }}</td>
              <td>{{ getSupplierName(item.supplier) }}</td>
              <td>{{ getProcessName(item.process) }}</td>
              <td>{{ getLineName(item.line) }}</td>
              <td>
                <span v-if="item.time_unit === 'MINUTE'">分 {{ item.duration_min || '-' }}</span>
                <span v-else>日 {{ item.lead_time_days }}</span>
              </td>
              <td>
                <button type="button" class="btn-sm" @click="startEditItem(item)">編集</button>
                <button type="button" class="btn-sm btn-danger" @click="deleteBOMItem(item.id)">削除</button>
              </td>
            </tr>
          </tbody>
        </table>
        <h3 class="mt-16">ルーティング自動生成</h3>
        <div class="routing-gen">
          <p class="section-label">最終工程（任意）</p>
          <div class="form-row">
            <div class="form-group">
              <label>工程</label>
              <select v-model="routingGenForm.final_process_id">
                <option value="">指定しない</option>
                <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                  {{ proc.process_code }} - {{ proc.process_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>ライン</label>
              <select v-model="routingGenForm.final_line_id">
                <option value="">指定しない</option>
                <option v-for="line in lines" :key="line.id" :value="line.id">
                  {{ line.line_code }} - {{ line.line_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>時間単位</label>
              <select v-model="routingGenForm.final_time_unit">
                <option value="MINUTE">分</option>
                <option value="DAY">日</option>
              </select>
            </div>
            <div class="form-group">
              <label>リードタイム(日)</label>
              <input
                type="number"
                min="0"
                v-model.number="routingGenForm.final_lead_time_days"
                :disabled="routingGenForm.final_time_unit === 'MINUTE'"
              />
            </div>
            <div class="form-group">
              <label>所要時間(分)</label>
              <input
                type="number"
                min="1"
                v-model.number="routingGenForm.final_duration_min"
                :disabled="routingGenForm.final_time_unit === 'DAY'"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>ルーティングコード</label>
              <input type="text" v-model="routingGenForm.routing_code" placeholder="未指定なら自動採番" />
            </div>
            <div class="form-group full-width">
              <label>説明</label>
              <input type="text" v-model="routingGenForm.description" placeholder="BOMから自動生成 のように記入" />
            </div>
          </div>
          <div class="form-actions">
            <button type="button" class="btn-primary" @click="generateRoutingFromBom" :disabled="!selectedBOM.id">
              BOMからルーティング生成
            </button>
            <button type="button" class="btn-secondary" @click="resetRoutingGenForm">リセット</button>
          </div>
          <p class="hint-text">
            MAKEの明細に登録された工程/ライン/時間をそのまま順番にステップ化します。必要なら最後に「最終工程」を追加できます（任意）。
          </p>
        </div>
        <div class="form-actions">
          <button type="button" @click="closeDetailsDialog" class="btn-secondary">
            {{ isStandaloneDetail ? '一覧に戻る' : '閉じる' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 階層図のみダイアログ -->
    <div v-if="showTreeDialog" class="modal-overlay" @click.self="closeTreeDialog">
      <div class="modal-content modal-large">
        <h2>BOM階層図</h2>
        <div class="tree-section" v-if="!treeLoading">
          <div v-if="bomTree" class="tree-grid-container">
            <table class="tree-grid">
              <thead>
                <tr>
                  <th>部番</th>
                  <th class="level-col">階層</th>
                  <th class="qty-col">数量</th>
                  <th class="phantom-col">みなし組立</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in treeRows" :key="row.key">
                  <td>
                    <span class="tree-line">{{ row.prefix }}</span>
                    <button
                      v-if="row.hasChildren"
                      @click="toggleNode(row.key)"
                      class="expand-btn"
                    >
                      {{ row.isExpanded ? '－' : '＋' }}
                    </button>
                    <span v-else class="expand-placeholder"></span>
                    {{ row.product }}
                  </td>
                  <td class="level-col">{{ row.level }}</td>
                  <td class="qty-col">{{ row.quantity }}</td>
                  <td class="phantom-col">{{ row.isPhantom ? '1' : '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else>データがありません</div>
        </div>
        <div v-else>読み込み中...</div>
        <div class="form-actions">
          <button type="button" @click="exportToExcel" class="btn-primary" :disabled="!bomTree">Excel出力</button>
          <button type="button" @click="closeTreeDialog" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>

    <!-- 逆展開ダイアログ -->
    <div v-if="showWhereUsedDialog" class="modal-overlay" @click.self="closeWhereUsedDialog">
      <div class="modal-content modal-large">
        <h2>逆展開（Where Used）</h2>
        <p class="hint-text">指定した製品がどの親製品で使われているかを確認します。</p>

        <div class="form-group">
          <label>製品を選択</label>
          <input
            class="filter-input"
            type="text"
            v-model="whereUsedProductFilter"
            placeholder="品番/品名で絞り込み"
          />
          <select v-model="whereUsedProductId" @change="fetchWhereUsed">
            <option value="">選択してください</option>
            <option v-for="product in filteredWhereUsedProducts" :key="product.id" :value="product.id">
              {{ product.product_code }} - {{ product.product_name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>
            <input type="checkbox" v-model="whereUsedRecursive" @change="fetchWhereUsed" />
            再帰的に最終製品まで辿る
          </label>
        </div>

        <div v-if="whereUsedLoading" class="loading-text">読み込み中...</div>

        <div v-else-if="whereUsedResults && whereUsedResults.length > 0" class="where-used-results">
          <h3>この製品を使用している親製品（{{ whereUsedResults.length }}件）</h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>親製品</th>
                <th>カテゴリ</th>
                <th>数量</th>
                <th>調達区分</th>
                <th>最終品</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="item in whereUsedResults" :key="item.parent_product_id">
                <tr>
                  <td>{{ item.parent_product_code }} - {{ item.parent_product_name }}</td>
                  <td>{{ getCategoryLabel(item.category) }}</td>
                  <td>{{ item.quantity }}</td>
                  <td>{{ getSourcingTypeLabel(item.sourcing_type) }}</td>
                  <td>{{ item.is_final_product ? '最終品' : '' }}</td>
                </tr>
                <!-- 再帰結果の子要素（インデント表示） -->
                <template v-if="whereUsedRecursive && item.parents && item.parents.length > 0">
                  <tr v-for="(child, idx) in flattenParents(item.parents, 1)" :key="`${item.parent_product_id}-${idx}`" class="nested-row">
                    <td :style="{ paddingLeft: (child.level * 20 + 8) + 'px' }">
                      └ {{ child.parent_product_code }} - {{ child.parent_product_name }}
                    </td>
                    <td>{{ getCategoryLabel(child.category) }}</td>
                    <td>{{ child.quantity }}</td>
                    <td>{{ getSourcingTypeLabel(child.sourcing_type) }}</td>
                    <td>{{ child.is_final_product ? '最終品' : '' }}</td>
                  </tr>
                </template>
              </template>
            </tbody>
          </table>
        </div>

        <div v-else-if="whereUsedProductId && !whereUsedLoading" class="no-data">
          この製品を使用している親製品はありません
        </div>

        <div class="form-actions">
          <button type="button" @click="closeWhereUsedDialog" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, h, defineComponent, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'

const route = useRoute()
const router = useRouter()

const boms = ref([])
const products = ref([])
const suppliers = ref([])
const processes = ref([])
const lines = ref([])
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  parent_product: '',
  version: 'v1',
  valid_from: '',
  valid_to: '',
  is_active: true
})

const filters = ref({
  search: '',
  is_final: '',
  is_line_final: '',
  is_coproduct: '',
  version: '',
  created_from: '',
  created_to: '',
  is_active: ''
})

const showDetailsDialog = ref(false)
const selectedBOM = ref({})
const bomItems = ref([])
const bomTree = ref(null)
const showTreeDialog = ref(false)
const treeLoading = ref(false)
const expandedNodes = ref(new Set())

// 逆展開用
const showWhereUsedDialog = ref(false)
const whereUsedProductId = ref('')
const whereUsedProductFilter = ref('')
const whereUsedRecursive = ref(false)
const whereUsedResults = ref([])
const whereUsedLoading = ref(false)

const routingGenForm = ref({
  routing_code: '',
  description: '',
  final_process_id: '',
  final_line_id: '',
  final_time_unit: 'MINUTE',
  final_lead_time_days: 0,
  final_duration_min: 60,
})

const routeBomId = computed(() => {
  const raw = route.query.bomId
  if (raw === undefined || raw === null || raw === '') return null
  const parsed = Number(raw)
  return Number.isNaN(parsed) ? raw : parsed
})

const isStandaloneDetail = computed(() => route.query.detail === 'full' && !!routeBomId.value)

const treeRows = computed(() => {
  if (!bomTree.value) return []
  const rows = []
  const rootKey = `root-${bomTree.value.id}`

  rows.push({
    key: rootKey,
    product: formatProductCode(bomTree.value.parent_product),
    quantity: '',
    level: 0,
    prefix: '',
    hasChildren: bomTree.value.items && bomTree.value.items.length > 0,
    isExpanded: expandedNodes.value.has(rootKey),
    parentKey: null,
    isPhantom: isPhantom(bomTree.value.parent_product?.id),
  })

  const walk = (items, level, parentPrefix = '', parentKey = null, parentExpanded = true) => {
    if (!items || !parentExpanded) return
    items.forEach((item, index) => {
      const isLast = index === items.length - 1
      const connector = isLast ? '└─ ' : '├─ '
      const currentPrefix = parentPrefix + connector
      const itemKey = `item-${item.id}`
      const hasChildren = item.child_bom && item.child_bom.items && item.child_bom.items.length > 0

      rows.push({
        key: itemKey,
        product: formatProductCode(item.child_product),
        quantity: formatQuantity(item.quantity),
        level,
        prefix: currentPrefix,
        hasChildren,
        isExpanded: expandedNodes.value.has(itemKey),
        parentKey,
        isPhantom: isPhantom(item.child_product?.id || item.child_product),
      })

      if (hasChildren) {
        const childPrefix = parentPrefix + (isLast ? '   ' : '│  ')
        const isExpanded = expandedNodes.value.has(itemKey)
        walk(item.child_bom.items, level + 1, childPrefix, itemKey, isExpanded)
      }
    })
  }

  const rootExpanded = expandedNodes.value.has(rootKey)
  walk(bomTree.value.items, 1, '', rootKey, rootExpanded)
  return rows
})

const toggleNode = (key) => {
  if (expandedNodes.value.has(key)) {
    expandedNodes.value.delete(key)
  } else {
    expandedNodes.value.add(key)
  }
}
const itemForm = ref({
  child_product: '',
  quantity: 1,
  loss_rate: '',
  sourcing_type: 'MAKE',
  supplier: '',
  process: '',
  line: '',
  time_unit: 'MINUTE',
  lead_time_days: 0,
  duration_min: 60,
  remark: ''
})
const editingItemId = ref(null)
const bomItemsRequestToken = ref(0)
const childProductFilter = ref('')
const parentProductFilter = ref('')

const sourcingTypeMap = {
  'MAKE': '自社製造',
  'BUY': '購買',
  'SUBCON': '外注'
}
const sourcingTypeOptions = [
  { value: 'MAKE', label: '自社製造' },
  { value: 'BUY', label: '購買' },
  { value: 'SUBCON', label: '外注' }
]

const resetFilters = () => {
  filters.value = {
    search: '',
    is_final: '',
    is_line_final: '',
    is_coproduct: '',
    version: '',
    created_from: '',
    created_to: '',
    is_active: ''
  }
  fetchBOMs()
}

const fetchBOMs = async () => {
  try {
    const params = {}

    if (filters.value.search) {
      params.search = filters.value.search
    }
    if (filters.value.is_final !== '') {
      params.parent_is_final = filters.value.is_final
    }
    if (filters.value.is_line_final !== '') {
      params.parent_is_line_final = filters.value.is_line_final
    }
    if (filters.value.is_coproduct !== '') {
      params.is_coproduct = filters.value.is_coproduct
    }
    if (filters.value.version) {
      params.version = filters.value.version
    }
    if (filters.value.created_from) {
      params.created_from = filters.value.created_from
    }
    if (filters.value.created_to) {
      params.created_to = filters.value.created_to
    }
    if (filters.value.is_active !== '') {
      params.is_active = filters.value.is_active
    }

    const response = await api.boms.getBOMs(params)
    boms.value = response.data.results || response.data
  } catch (error) {
    console.error('BOM取得エラー:', error)
    alert('BOMデータの取得に失敗しました')
  }
}

const fetchProducts = async () => {
  try {
    // 全ページ取得（現状フィルタなし）
    products.value = (await api.products.getAllProducts()).sort((a, b) =>
      (b.product_code || '').localeCompare(a.product_code || '')
    )
  } catch (error) {
    console.error('製品取得エラー:', error)
  }
}

const fetchSuppliers = async () => {
  try {
    const response = await api.suppliers.getSuppliers()
    suppliers.value = response.data.results || response.data
  } catch (error) {
    console.error('仕入先取得エラー:', error)
  }
}

const fetchProcesses = async () => {
  try {
    const response = await api.processes.getProcesses()
    processes.value = response.data.results || response.data
  } catch (error) {
    console.error('工程取得エラー:', error)
  }
}

const fetchLines = async () => {
  try {
    const response = await api.lines.getLines()
    lines.value = response.data.results || response.data
  } catch (error) {
    console.error('ライン取得エラー:', error)
  }
}

const findBomById = (bomId) => boms.value.find((b) => `${b.id}` === `${bomId}`)

const ensureBomLoaded = async (bomId) => {
  const existing = findBomById(bomId)
  if (existing) return existing
  try {
    const response = await api.boms.getBOM(bomId)
    const bom = response.data
    if (bom && !findBomById(bom.id)) {
      boms.value.push(bom)
    }
    return bom
  } catch (error) {
    console.error('BOM取得エラー(単体):', error)
    return null
  }
}

const resetItemForm = () => {
  itemForm.value = {
    child_product: '',
    quantity: 1,
    loss_rate: '',
    sourcing_type: 'MAKE',
    supplier: '',
    process: '',
    line: '',
    time_unit: 'MINUTE',
    lead_time_days: 0,
    duration_min: 60,
    remark: ''
  }
  editingItemId.value = null
}

const applySourcingSideEffects = () => {
  if (itemForm.value.sourcing_type === 'MAKE') {
    itemForm.value.supplier = ''
    if (!itemForm.value.time_unit) itemForm.value.time_unit = 'MINUTE'
  }
  if (itemForm.value.sourcing_type === 'SUBCON') {
    if (!itemForm.value.time_unit) itemForm.value.time_unit = 'DAY'
  }
  if (itemForm.value.sourcing_type === 'BUY') {
    itemForm.value.process = ''
    itemForm.value.line = ''
    itemForm.value.time_unit = 'DAY'
    itemForm.value.duration_min = null
    if (!itemForm.value.lead_time_days || itemForm.value.lead_time_days === 0) {
      itemForm.value.lead_time_days = 1
    }
  }
}

const resetRoutingGenForm = () => {
  routingGenForm.value = {
    routing_code: '',
    description: '',
    final_process_id: '',
    final_line_id: '',
    final_time_unit: 'MINUTE',
    final_lead_time_days: 0,
    final_duration_min: 60,
  }
}

const fetchBOMItems = async (bomId, token = bomItemsRequestToken.value) => {
  const response = await api.boms.getBOMItems({ bom: bomId })
  if (token !== bomItemsRequestToken.value) return
  const items = response.data.results || response.data || []
  // API側で絞られている前提でそのまま表示（過剰フィルタで消えないようにする）
  bomItems.value = items
}

const fetchBOMTree = async (bomId) => {
  try {
    const response = await api.boms.getBOMTree(bomId)
    bomTree.value = response.data
  } catch (error) {
    console.error('BOMツリー取得エラー:', error)
    bomTree.value = null
  }
}

const getProductName = (productId) => {
  const product = products.value.find(p => p.id === productId)
  return product ? `${product.product_code} - ${product.product_name}` : productId
}

const getChildProductCode = (item) => {
  if (!item) return ''
  if (item.child_product_code) return item.child_product_code
  if (item.child_product && typeof item.child_product === 'object') {
    return item.child_product.product_code || item.child_product.code || ''
  }
  return getProductCodeOnly(item.child_product)
}

const getParentProductCode = (bom) => {
  if (!bom) return ''
  if (bom.parent_product_code) return bom.parent_product_code
  if (bom.parent_product && typeof bom.parent_product === 'object') {
    return bom.parent_product.product_code || bom.parent_product.code || ''
  }
  return getProductCodeOnly(bom.parent_product)
}

const getProductCodeOnly = (productId) => {
  const product = products.value.find(p => p.id === productId)
  return product ? product.product_code : productId
}

// Backward compatibility: some template renders may still call getProductCode
const getProductCode = (productId) => getProductCodeOnly(productId)

const formatProductCode = (productObj) => {
  if (!productObj) return ''
  return productObj.code || productObj.product_code || ''
}

const formatQuantity = (quantity) => {
  if (quantity === null || quantity === undefined) return ''
  const num = parseFloat(quantity)
  if (Number.isNaN(num)) return quantity
  return Math.trunc(num).toString()
}

const normalizeQuantityValue = (value) => {
  const num = Math.trunc(Number(value))
  return Number.isFinite(num) && num > 0 ? num : null
}

const requiresRoutingDetails = (sourcingType) => sourcingType === 'MAKE' || sourcingType === 'SUBCON'

const isPhantom = (productId) => {
  const product = products.value.find(p => p.id === productId)
  return Boolean(product?.is_phantom)
}

const filteredChildProducts = computed(() => {
  const keyword = childProductFilter.value.trim().toLowerCase()
  if (!keyword) return products.value
  return products.value.filter((p) =>
    `${p.product_code} ${p.product_name}`.toLowerCase().includes(keyword)
  )
})

const filteredParentProducts = computed(() => {
  const keyword = parentProductFilter.value.trim().toLowerCase()
  let pool = products.value
  if (formData.value.is_coproduct) {
    pool = pool.filter(p => p.is_virtual_set)
  }
  if (!keyword) return pool
  return pool.filter((p) =>
    `${p.product_code} ${p.product_name}`.toLowerCase().includes(keyword)
  )
})

const filteredWhereUsedProducts = computed(() => {
  const keyword = whereUsedProductFilter.value.trim().toLowerCase()
  if (!keyword) return products.value
  return products.value.filter((p) =>
    `${p.product_code} ${p.product_name}`.toLowerCase().includes(keyword)
  )
})

const categoryMap = {
  'ASSEMBLY': '組立品',
  'SINGLE': '単品',
  'MATERIAL': '材料',
  'PURCHASED': '購入品',
  'UNKNOWN': '未定',
}

const getCategoryLabel = (value) => categoryMap[value] || value || '-'

const getSupplierName = (supplierId) => {
  if (!supplierId) return '-'
  const supplier = suppliers.value.find(s => s.id === supplierId)
  return supplier ? supplier.supplier_name : supplierId
}

const getProcessName = (processId) => {
  if (!processId) return '-'
  const proc = processes.value.find(p => p.id === processId)
  return proc ? `${proc.process_code} - ${proc.process_name}` : processId
}

const getLineName = (lineId) => {
  if (!lineId) return '-'
  const line = lines.value.find(l => l.id === lineId)
  return line ? `${line.line_code} - ${line.line_name}` : lineId
}

const getSourcingTypeLabel = (value) => sourcingTypeMap[value] || value

const showNewDialog = () => {
  isEdit.value = false
  parentProductFilter.value = ''
  const today = new Date().toISOString().split('T')[0]
  formData.value = {
    parent_product: '',
    version: 'v1',
    valid_from: today,
    valid_to: '',
    is_active: true,
    is_coproduct: false,
  }
  showDialog.value = true
}

const editBOM = (bom) => {
  isEdit.value = true
  parentProductFilter.value = ''
  formData.value = {
    ...bom,
    parent_product: bom.parent_product
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
  parentProductFilter.value = ''
}

const saveBOM = async () => {
  try {
    const dataToSend = {
      parent_product: formData.value.parent_product,
      version: formData.value.version,
      valid_from: formData.value.valid_from,
      valid_to: formData.value.valid_to || null,
      is_active: formData.value.is_active,
      is_coproduct: formData.value.is_coproduct,
    }

    if (isEdit.value) {
      await api.boms.updateBOM(formData.value.id, dataToSend)
      alert('更新しました')
    } else {
      await api.boms.createBOM(dataToSend)
      alert('作成しました')
    }
    await fetchBOMs()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    console.error('エラー詳細:', error.response?.data)
    const errorMessage = error.response?.data?.detail
      || JSON.stringify(error.response?.data)
      || error.message
      || '保存に失敗しました'
    alert('保存に失敗しました\n\n' + errorMessage)
  }
}

const deleteBOM = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.boms.deleteBOM(id)
    await fetchBOMs()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

const generateRoutingFromBom = async () => {
  if (!selectedBOM.value?.id) {
    alert('BOMを開いてから実行してください')
    return
  }

  const payload = {
    description: routingGenForm.value.description || undefined,
    routing_code: routingGenForm.value.routing_code || undefined,
    is_default: true,
  }

  // 最終工程のオプション指定がある場合だけ付与
  if (routingGenForm.value.final_process_id) {
    payload.final_process_id = routingGenForm.value.final_process_id
    if (routingGenForm.value.final_line_id) {
      payload.final_line_id = routingGenForm.value.final_line_id
    }
    payload.final_time_unit = routingGenForm.value.final_time_unit
    if (routingGenForm.value.final_time_unit === 'MINUTE') {
      if (!routingGenForm.value.final_duration_min || routingGenForm.value.final_duration_min <= 0) {
        alert('最終工程の所要時間(分)を1以上で入力してください')
        return
      }
      payload.final_duration_min = routingGenForm.value.final_duration_min
      payload.final_lead_time_days = 0
    } else {
      if (!routingGenForm.value.final_lead_time_days || routingGenForm.value.final_lead_time_days <= 0) {
        alert('最終工程のリードタイム(日)を1以上で入力してください')
        return
      }
      payload.final_lead_time_days = routingGenForm.value.final_lead_time_days
      payload.final_duration_min = null
    }
  }

  try {
    const res = await api.boms.generateRouting(selectedBOM.value.id, payload)
    const steps = res.data?.generated_steps ?? '-'
    alert(`ルーティングを生成しました（ステップ: ${steps}）`)
  } catch (error) {
    console.error('ルーティング生成エラー:', error)
    const errorMessage = error.response?.data?.detail
      || JSON.stringify(error.response?.data)
      || error.message
      || 'ルーティング生成に失敗しました'
    alert('ルーティング生成に失敗しました\n\n' + errorMessage)
  }
}

const openDetailsInNewTab = (bom) => {
  const target = router.resolve({
    name: 'BOMMaster',
    query: { bomId: bom.id, detail: 'full' }
  })
  window.open(target.href, '_blank', 'noopener')
}

const viewDetails = async (bom, { openDialog = true } = {}) => {
  selectedBOM.value = bom
  resetItemForm()
  resetRoutingGenForm()
  childProductFilter.value = ''
  bomItems.value = []
  bomTree.value = null
  const token = ++bomItemsRequestToken.value
  showDetailsDialog.value = openDialog && !isStandaloneDetail.value
  try {
    await fetchBOMItems(bom.id, token)
    await fetchBOMTree(bom.id)
    collapseAllNodes()
  } catch (error) {
    console.error('BOM明細取得エラー:', error)
    alert('BOM明細の取得に失敗しました')
    bomItems.value = []
  }
}

const openDetailFromRoute = async () => {
  if (!routeBomId.value || !isStandaloneDetail.value) return
  const bom = await ensureBomLoaded(routeBomId.value)
  if (bom) {
    await viewDetails(bom, { openDialog: false })
  } else {
    alert('指定のBOMが見つかりませんでした')
  }
}

const closeDetailsDialog = () => {
  if (isStandaloneDetail.value) {
    router.replace({ name: 'BOMMaster' })
  }
  showDetailsDialog.value = false
  selectedBOM.value = {}
  bomItems.value = []
  bomTree.value = null
  bomItemsRequestToken.value += 1
  resetItemForm()
  childProductFilter.value = ''
}

const handleDetailsBackdropClick = () => {
  if (!isStandaloneDetail.value) {
    closeDetailsDialog()
  }
}

const viewTreeOnly = async (bom) => {
  showTreeDialog.value = true
  treeLoading.value = true
  bomTree.value = null
  expandedNodes.value = new Set()
  try {
    await fetchBOMTree(bom.id)
    // 初期状態：全て展開
    expandAllNodes()
  } catch (error) {
    alert('階層図の取得に失敗しました')
  } finally {
    treeLoading.value = false
  }
}

const expandAllNodes = () => {
  if (!bomTree.value) return
  const allKeys = new Set()
  const rootKey = `root-${bomTree.value.id}`
  allKeys.add(rootKey)

  const collectKeys = (items) => {
    if (!items) return
    items.forEach((item) => {
      const itemKey = `item-${item.id}`
      allKeys.add(itemKey)
      if (item.child_bom && item.child_bom.items && item.child_bom.items.length) {
        collectKeys(item.child_bom.items)
      }
    })
  }
  collectKeys(bomTree.value.items)
  expandedNodes.value = allKeys
}

const collapseAllNodes = () => {
  if (!bomTree.value) {
    expandedNodes.value = new Set()
    return
  }
  const rootKey = `root-${bomTree.value.id}`
  expandedNodes.value = new Set([rootKey])
}

const closeTreeDialog = () => {
  showTreeDialog.value = false
  bomTree.value = null
  expandedNodes.value = new Set()
}

// 逆展開関連
const openWhereUsedDialog = () => {
  showWhereUsedDialog.value = true
  whereUsedProductId.value = ''
  whereUsedProductFilter.value = ''
  whereUsedRecursive.value = false
  whereUsedResults.value = []
}

const closeWhereUsedDialog = () => {
  showWhereUsedDialog.value = false
  whereUsedProductId.value = ''
  whereUsedProductFilter.value = ''
  whereUsedRecursive.value = false
  whereUsedResults.value = []
}

const fetchWhereUsed = async () => {
  if (!whereUsedProductId.value) {
    whereUsedResults.value = []
    return
  }
  whereUsedLoading.value = true
  try {
    const response = await api.products.getWhereUsed(
      whereUsedProductId.value,
      whereUsedRecursive.value
    )
    whereUsedResults.value = response.data.parents || []
  } catch (error) {
    console.error('逆展開取得エラー:', error)
    alert('逆展開データの取得に失敗しました')
    whereUsedResults.value = []
  } finally {
    whereUsedLoading.value = false
  }
}

const flattenParents = (parents, level) => {
  const result = []
  for (const p of parents) {
    result.push({ ...p, level })
    if (p.parents && p.parents.length > 0) {
      result.push(...flattenParents(p.parents, level + 1))
    }
  }
  return result
}

const exportToExcel = () => {
  if (!bomTree.value) return

  // CSVヘッダー
  const headers = ['部番', '階層', '数量', 'みなし組立']
  const rows = [headers]

  // データ行を追加
  treeRows.value.forEach((row) => {
    // 罫線とボタン部分を含めた部番表示
    const productDisplay = row.prefix + row.product
    rows.push([
      productDisplay,
      row.level.toString(),
      row.quantity || '',
      row.isPhantom ? '1' : ''
    ])
  })

  // CSV形式に変換
  const csvContent = rows.map(row =>
    row.map(cell => {
      // セル内にカンマや改行、ダブルクォートがある場合はエスケープ
      const cellStr = String(cell)
      if (cellStr.includes(',') || cellStr.includes('\n') || cellStr.includes('"')) {
        return '"' + cellStr.replace(/"/g, '""') + '"'
      }
      return cellStr
    }).join(',')
  ).join('\n')

  // BOM UTF-8付きでダウンロード（Excelで正しく開けるように）
  const bom = '\uFEFF'
  const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)

  // ファイル名を生成
  const parentProduct = formatProductCode(bomTree.value.parent_product)
  const timestamp = new Date().toISOString().slice(0, 10)
  const filename = `BOM階層図_${parentProduct}_${timestamp}.csv`

  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

const startEditItem = (item) => {
  editingItemId.value = item.id
  itemForm.value = {
    child_product: item.child_product,
    quantity: normalizeQuantityValue(item.quantity) ?? 1,
    loss_rate: item.loss_rate ?? '',
    sourcing_type: item.sourcing_type,
    supplier: item.supplier ?? '',
    process: item.process ?? '',
    line: item.line ?? '',
    time_unit: item.time_unit || 'MINUTE',
    lead_time_days: item.lead_time_days ?? 0,
    duration_min: item.duration_min ?? 60,
    remark: item.remark ?? ''
  }
  applySourcingSideEffects()
}

const saveBOMItem = async () => {
  if (!selectedBOM.value?.id) return
  if (!itemForm.value.child_product) {
    alert('子製品は必須です')
    return
  }

  const normalizedQuantity = normalizeQuantityValue(itemForm.value.quantity)
  if (!normalizedQuantity) {
    alert('数量は1以上の整数で入力してください')
    return
  }
  applySourcingSideEffects()
  if (requiresRoutingDetails(itemForm.value.sourcing_type)) {
    if (!itemForm.value.process) {
      alert('工程は必須です（自社製造/外注）')
      return
    }
    if (itemForm.value.time_unit === 'MINUTE' && (!itemForm.value.duration_min || itemForm.value.duration_min <= 0)) {
      alert('時間単位=分のときは所要時間(分)を1以上で入力してください')
      return
    }
    if (itemForm.value.time_unit === 'DAY' && itemForm.value.lead_time_days <= 0) {
      alert('時間単位=日 のときはリードタイム(日)を1以上で入力してください')
      return
    }
  } else if (itemForm.value.sourcing_type === 'BUY') {
    if (!itemForm.value.lead_time_days || itemForm.value.lead_time_days <= 0) {
      alert('購買の場合、リードタイム(日)を1以上で入力してください')
      return
    }
  }

  const payload = {
    bom: selectedBOM.value.id,
    child_product: itemForm.value.child_product,
    quantity: normalizedQuantity,
    loss_rate: itemForm.value.loss_rate === '' ? null : itemForm.value.loss_rate,
    sourcing_type: itemForm.value.sourcing_type,
    supplier: itemForm.value.sourcing_type === 'MAKE' ? null : (itemForm.value.supplier || null),
    process: requiresRoutingDetails(itemForm.value.sourcing_type) ? (itemForm.value.process || null) : null,
    line: requiresRoutingDetails(itemForm.value.sourcing_type) ? (itemForm.value.line || null) : null,
    time_unit: requiresRoutingDetails(itemForm.value.sourcing_type) ? itemForm.value.time_unit : 'DAY',
    lead_time_days: itemForm.value.lead_time_days,
    duration_min: requiresRoutingDetails(itemForm.value.sourcing_type) && itemForm.value.time_unit === 'MINUTE'
      ? itemForm.value.duration_min
      : null,
    remark: itemForm.value.remark || ''
  }

  try {
    if (editingItemId.value) {
      await api.boms.updateBOMItem(editingItemId.value, payload)
      alert('明細を更新しました')
    } else {
      await api.boms.createBOMItem(payload)
      alert('明細を追加しました')
    }
    await fetchBOMItems(selectedBOM.value.id)
    resetItemForm()
  } catch (error) {
    console.error('明細保存エラー:', error)
    console.error('エラー詳細:', error.response?.data)
    const errorMessage = error.response?.data?.detail
      || JSON.stringify(error.response?.data)
      || error.message
      || '明細の保存に失敗しました'
    alert('明細の保存に失敗しました\n\n' + errorMessage)
  }
}

const deleteBOMItem = async (id) => {
  if (!confirm('この明細を削除しますか？')) return
  try {
    await api.boms.deleteBOMItem(id)
    await fetchBOMItems(selectedBOM.value.id)
  } catch (error) {
    console.error('明細削除エラー:', error)
    alert('明細の削除に失敗しました')
  }
}

onMounted(async () => {
  await Promise.all([
    fetchProducts(),
    fetchSuppliers(),
    fetchProcesses(),
    fetchLines(),
  ])
  await fetchBOMs()
  if (isStandaloneDetail.value && routeBomId.value) {
    await openDetailFromRoute()
  }
})

watch(
  () => [route.query.bomId, route.query.detail],
  () => {
    if (isStandaloneDetail.value) {
      openDetailFromRoute()
    } else if (showDetailsDialog.value) {
      closeDetailsDialog()
    }
  }
)

const TreeBranch = defineComponent({
  name: 'TreeBranch',
  props: {
    items: {
      type: Array,
      required: true,
    },
  },
  setup(props) {
    return () =>
      h(
        'ul',
        { class: 'tree-children' },
        props.items.map((item) =>
          h('li', { key: item.id }, [
            h('div', { class: 'tree-node' }, [
              h('span', { class: 'tree-product' }, formatProductCode(item.child_product)),
              h(
                'span',
                { class: 'tree-meta' },
                `数量: ${formatQuantity(item.quantity)}`
              ),
            ]),
            item.child_bom && item.child_bom.items && item.child_bom.items.length
              ? h(TreeBranch, { items: item.child_bom.items })
              : null,
          ])
        )
      )
  },
})
</script>

<style scoped>
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  margin-bottom: 16px;
}

.filter-field {
  display: flex;
  flex-direction: column;
  min-width: 180px;
}

.filter-field label {
  font-size: 12px;
  color: #555;
  margin-bottom: 4px;
}

.filter-field input,
.filter-field select {
  padding: 6px 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-overlay.as-page {
  position: static;
  background-color: transparent;
  justify-content: flex-start;
  align-items: flex-start;
  padding: 0;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  min-width: 500px;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-large {
  min-width: 800px;
  max-width: 900px;
}

.detail-page-card {
  max-width: none;
  width: 100%;
  max-height: none;
  box-shadow: none;
  border: 1px solid #e5e7eb;
  min-width: 0;
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
}

.modal-content h3 {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  color: #555;
}

.details-section {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.details-section p {
  margin: 0.5rem 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem 1rem;
  align-items: center;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

@media (min-width: 640px) {
  .summary-item {
    flex-direction: row;
    align-items: center;
  }
}

.summary-label {
  font-weight: 600;
  color: #444;
  min-width: 90px;
}

.summary-value {
  color: #111;
}

.tree-section {
  margin-bottom: 1.5rem;
}

.tree-grid-container {
  background: #f9fbff;
  border: 1px solid #e1e8f5;
  border-radius: 8px;
  padding: 1rem;
  overflow-x: auto;
}

.tree-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.tree-grid {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}

.tree-grid th,
.tree-grid td {
  border: 1px solid #d6dce6;
  padding: 6px 8px;
}

.phantom-col {
  width: 90px;
  text-align: center;
}

.tree-grid th {
  background: #eef5ff;
  text-align: left;
}

.level-col {
  width: 60px;
  text-align: center;
}

.qty-col {
  width: 90px;
  text-align: right;
}

.tree-line {
  font-family: 'Courier New', Consolas, monospace;
  color: #888;
  user-select: none;
  white-space: pre;
}

.expand-btn {
  display: inline-block;
  width: 20px;
  height: 20px;
  padding: 0;
  margin: 0 4px;
  border: 1px solid #ccc;
  background: #fff;
  color: #333;
  font-size: 14px;
  line-height: 18px;
  text-align: center;
  cursor: pointer;
  border-radius: 3px;
  vertical-align: middle;
}

.expand-btn:hover {
  background: #f0f0f0;
  border-color: #999;
}

.expand-placeholder {
  display: inline-block;
  width: 20px;
  margin: 0 4px;
}

.filter-input {
  width: 100%;
  margin-bottom: 0.5rem;
  padding: 0.4rem 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.phantom-info {
  margin-top: 0.5rem;
  color: #b15e00;
  font-size: 0.9rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

.form-group input[type="text"],
.form-group input[type="date"],
.form-group select {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input[type="checkbox"] {
  margin-right: 0.5rem;
}

.form-actions {
  margin-top: 1.5rem;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background-color: white;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover {
  background-color: #f5f5f5;
}

.routing-gen {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #e1e8f5;
  border-radius: 8px;
  background: #f8fbff;
}

.section-label {
  font-weight: 600;
  margin: 0 0 8px;
  color: #444;
}

.routing-gen .form-row {
  gap: 12px;
}

.routing-gen .form-group {
  min-width: 160px;
}

.mt-16 {
  margin-top: 16px;
}

.hint-text {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

.btn-info {
  padding: 0.5rem 1rem;
  background-color: #17a2b8;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-info:hover {
  background-color: #138496;
}

.where-used-results {
  margin-top: 1rem;
}

.where-used-results h3 {
  margin-bottom: 0.5rem;
}

.nested-row {
  background-color: #f9f9f9;
}

.nested-row td:first-child {
  color: #666;
}

.loading-text {
  padding: 1rem;
  text-align: center;
  color: #666;
}
</style>
