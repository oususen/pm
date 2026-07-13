<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">構成マスタ（BOM） <DataSourceDialog title="構成マスタ（BOM）" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button @click="fetchBOMs" class="btn-primary">更新</button>
        <button v-if="canEdit" @click="downloadBomImportTemplateXlsx" class="btn-secondary">取込テンプレートExcel</button>
        <button v-if="canEdit" @click="downloadBomImportTemplate" class="btn-secondary">取込テンプレートCSV</button>
        <button v-if="canEdit" @click="openBomImportDialog" class="btn-secondary">CSV取込</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規</button>
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
          <button @click="fetchBOMs(1)" class="btn-primary">検索</button>
          <button @click="resetFilters" class="btn-secondary">リセット</button>
        </div>
      </div>

      <div class="bom-list-area" v-if="hasSearched && boms.length > 0">
        <table class="data-table bom-list-table">
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
                <button @click="downloadBOMExcel(bom)" class="btn-sm btn-excel">Excel出力</button>
                <button @click="openDetailsInNewTab(bom)" class="btn-sm">別タブ</button>
                <button @click="viewTreeOnly(bom)" class="btn-sm">階層図</button>
                <button v-if="canEdit" @click="editBOM(bom)" class="btn-sm">編集</button>
                <button v-if="canEdit" @click="deleteBOM(bom.id)" class="btn-sm btn-danger">削除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination-controls" v-if="totalPages > 0">
        <button
          class="btn-secondary"
          :disabled="currentPage === 1"
          @click="changePage(currentPage - 1)"
        >
          前へ
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }} ページ (全 {{ totalCount }} 件)</span>
        <button
          class="btn-secondary"
          :disabled="currentPage === totalPages"
          @click="changePage(currentPage + 1)"
        >
          次へ
        </button>
      </div>

      <div v-if="!hasSearched" class="no-data">
        検索条件を入力して「検索」ボタンを押してください
      </div>
      <div v-else-if="boms.length === 0" class="no-data">
        該当するBOMがありません
      </div>
    </div>

    <div v-if="showBomImportDialog" class="modal-overlay" @click.self="closeBomImportDialog">
      <div class="modal-content">
        <h2>BOM取込（CSV / Excel）</h2>
        <div class="csv-format-note">
          <strong>必須列:</strong> 親品番, 子品番, 数量, 調達区分
          <br><small>区分別チェック実装済み: 自社製造は工程/ライン/時間単位/所要時間(分)必須、購入は仕入先/時間単位必須かつ工程不可、外作は仕入先/時間単位必須（工程空欄時はG自動補完）。</small>
        </div>
        <div class="form-group">
          <label>取込ファイル *</label>
          <input type="file" accept=".csv,.xlsx" @change="onBomCsvSelected" />
        </div>
        <div class="form-group">
          <label>版 *</label>
          <input v-model="bomImportForm.version" />
        </div>
        <div class="form-group">
          <label>完成品（画面入力） *</label>
          <input v-model="bomImportForm.completed_product_code" placeholder="例: YD60000441" />
        </div>
        <div class="form-group">
          <label>有効開始日 *</label>
          <input type="date" v-model="bomImportForm.valid_from" />
        </div>
        <div class="form-group">
          <label>有効終了日</label>
          <input type="date" v-model="bomImportForm.valid_to" />
        </div>
        <div class="form-group">
          <label>備考（全明細共通）</label>
          <input v-model="bomImportForm.remark" />
        </div>
        <div class="form-group">
          <label><input type="checkbox" v-model="bomImportForm.is_active" /> 有効</label>
        </div>
        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="executeBomImportCheck" :disabled="bomImporting || bomChecking">
            {{ bomChecking ? 'チェック中...' : '取込前チェック' }}
          </button>
          <button type="button" class="btn-primary" @click="executeBomCsvImport" :disabled="bomImporting">
            {{ bomImporting ? '取込中...' : '取込実行' }}
          </button>
          <button type="button" class="btn-secondary" @click="closeBomImportDialog">閉じる</button>
        </div>
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
            <button type="submit" class="btn-primary" :disabled="!canEdit">保存</button>
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
          <div class="summary-item">
            <button v-if="canEdit" type="button" class="btn-secondary" @click="editBOM(selectedBOM)">基本情報を編集</button>
            <button v-if="canEdit" type="button" class="btn-primary" @click="openCopyDialog">BOMをコピー</button>
          </div>
        </div>
        <p v-if="isPhantom(selectedBOM.parent_product)" class="phantom-info">
          この親製品は見なし組立です。リードタイム計算や展開ロジックの扱いに注意してください。
        </p>
        <div v-if="treeExcelRows.length" class="tree-section">
          <h3>階層表示</h3>
          <div class="tree-grid-container">
            <table class="tree-grid">
              <thead>
                <tr>
                  <th>BOM ID</th>
                  <th>親製品</th>
                  <th>部番表示</th>
                  <th>製品名</th>
                  <th class="level-col">階層</th>
                  <th class="qty-col">数量</th>
                  <th class="lt-col">LT(日)</th>
                  <th class="lt-col">積LT</th>
                  <th class="duration-col">所要(分)</th>
                  <th>工程</th>
                  <th>ライン</th>
                  <th>仕入先</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in treeExcelRows" :key="`${row.bom_id}-${idx}`">
                  <td>{{ row.bom_id }}</td>
                  <td>{{ row.parent_product }}</td>
                  <td>{{ row.part_display }}</td>
                  <td>{{ row.product_name }}</td>
                  <td class="level-col">{{ row.level }}</td>
                  <td class="qty-col">{{ row.quantity }}</td>
                  <td class="lt-col">{{ row.lead_time_days }}</td>
                  <td class="lt-col">{{ row.cumulative_lt }}</td>
                  <td class="duration-col">{{ row.duration_min }}</td>
                  <td>{{ row.process }}</td>
                  <td>{{ row.line }}</td>
                  <td>{{ row.supplier }}</td>
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
              <input
                type="number"
                step="1"
                min="1"
                v-model.number="itemForm.quantity"
                required
                class="tall-number-input narrow-field"
              />
            </div>
            <div class="form-group">
              <label>ロス率</label>
              <input
                type="number"
                step="0.001"
                min="0"
                v-model="itemForm.loss_rate"
                class="narrow-field"
              />
            </div>
            <div class="form-group">
              <label>調達区分 *</label>
              <select v-model="itemForm.sourcing_type" required>
                <option v-for="option in sourcingTypeOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>仕入先{{ itemForm.sourcing_type === 'BUY' || itemForm.sourcing_type === 'SUBCON' ? ' *' : '' }}</label>
              <select v-model="itemForm.supplier" :disabled="itemForm.sourcing_type === 'MAKE'" :required="itemForm.sourcing_type === 'BUY' || itemForm.sourcing_type === 'SUBCON'">
                <option value="">選択しない</option>
                <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.id">
                  {{ supplier.supplier_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>工程{{ itemForm.sourcing_type === 'MAKE' ? ' *' : '' }}</label>
              <select v-model="itemForm.process" :required="itemForm.sourcing_type === 'MAKE'" :disabled="itemForm.sourcing_type === 'BUY' || itemForm.sourcing_type === 'SUBCON'">
                <option value="">選択してください</option>
                <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                  {{ proc.process_code }} - {{ proc.process_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>ライン{{ itemForm.sourcing_type === 'MAKE' ? ' *' : '' }}</label>
              <select
                v-model="itemForm.line"
                :disabled="itemForm.sourcing_type === 'BUY' || itemForm.sourcing_type === 'SUBCON'"
                :required="itemForm.sourcing_type === 'MAKE'"
              >
                <option value="">選択しない</option>
                <option v-for="line in filteredLines" :key="line.id" :value="line.id">
                  {{ line.line_code }} - {{ line.line_name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>時間単位{{ itemForm.sourcing_type === 'MAKE' ? ' *' : '' }}</label>
              <select
                v-model="itemForm.time_unit"
                :disabled="itemForm.sourcing_type === 'BUY'"
                :required="itemForm.sourcing_type === 'MAKE'"
                class="narrow-field"
              >
                <option value="MINUTE">分</option>
                <option value="DAY">日</option>
              </select>
            </div>
            <div class="form-group">
              <label>リードタイム(日){{ itemForm.sourcing_type === 'BUY' || itemForm.sourcing_type === 'SUBCON' ? ' *' : '' }}</label>
              <input
                type="number"
                min="0"
                v-model.number="itemForm.lead_time_days"
                :required="itemForm.sourcing_type === 'BUY' || itemForm.sourcing_type === 'SUBCON'"
                class="tall-number-input narrow-field"
              />
            </div>
            <div class="form-group">
              <label>所要時間(分){{ itemForm.time_unit === 'MINUTE' && itemForm.sourcing_type !== 'BUY' ? ' *' : '' }}</label>
              <input
                type="number"
                min="1"
                v-model.number="itemForm.duration_min"
                :disabled="itemForm.time_unit === 'DAY' || itemForm.sourcing_type === 'BUY'"
                :required="itemForm.time_unit === 'MINUTE' && itemForm.sourcing_type !== 'BUY'"
                class="tall-number-input narrow-field"
              />
            </div>
            <div class="form-group" v-if="selectedBomIsCoproduct">
              <label>連産品代表品</label>
              <input
                type="checkbox"
                v-model="itemForm.is_coproduct_driver"
                class="checkbox-input"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group full-width">
              <label>備考</label>
              <input type="text" v-model="itemForm.remark" />
            </div>
          </div>
          <div class="form-actions">
            <label v-if="!editingItemId" class="checkbox-label" style="margin-right:12px;">
              <input type="checkbox" v-model="itemForm.add_to_routing" class="checkbox-input" />
              ルーティングにもステップ追加
            </label>
            <button type="button" class="btn-primary" @click="saveBOMItem" :disabled="!canEdit">
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
              <th>LT</th>
              <th>時間</th>
              <th v-if="selectedBomIsCoproduct">代表</th>
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
              <td>{{ item.lead_time_days ?? 0 }}</td>
              <td>
                <span v-if="item.time_unit === 'MINUTE'">分 {{ item.duration_min || '-' }}</span>
                <span v-else>日</span>
              </td>
              <td v-if="selectedBomIsCoproduct">{{ item.is_coproduct_driver ? '✓' : '' }}</td>
              <td>
                <button v-if="canEdit" type="button" class="btn-sm" @click="startEditItem(item)">編集</button>
                <button v-if="canEdit" type="button" class="btn-sm btn-danger" @click="deleteBOMItem(item.id)">削除</button>
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
              <select
                v-model="routingGenForm.final_line_id"
                :disabled="isFinalLineFixedByProcess"
              >
                <option value="">指定しない</option>
                <option v-for="line in filteredFinalLines" :key="line.id" :value="line.id">
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
                class="tall-number-input"
              />
            </div>
            <div class="form-group">
              <label>所要時間(分)</label>
              <input
                type="number"
                min="1"
                v-model.number="routingGenForm.final_duration_min"
                :disabled="routingGenForm.final_time_unit === 'DAY'"
                class="tall-number-input"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>有効開始日時</label>
              <input
                type="datetime-local"
                v-model="routingGenForm.valid_from_datetime"
              />
            </div>
            <div class="form-group">
              <label>ルーティングコード</label>
              <input type="text" v-model="routingGenForm.routing_code" placeholder="未指定なら自動採番" />
            </div>
            <div class="form-group full-width">
              <label>説明</label>
              <input type="text" v-model="routingGenForm.description" placeholder="bomから自動生成した" />
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
          <div v-if="treeExcelRows.length" class="tree-grid-container">
            <table class="tree-grid">
              <thead>
                <tr>
                  <th>BOM ID</th>
                  <th>親製品</th>
                  <th>部番表示</th>
                  <th>製品名</th>
                  <th class="level-col">階層</th>
                  <th class="qty-col">数量</th>
                  <th class="lt-col">LT(日)</th>
                  <th class="lt-col">積LT</th>
                  <th class="duration-col">所要(分)</th>
                  <th>工程</th>
                  <th>ライン</th>
                  <th>仕入先</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in treeExcelRows" :key="`${row.bom_id}-${idx}`">
                  <td>{{ row.bom_id }}</td>
                  <td>{{ row.parent_product }}</td>
                  <td>{{ row.part_display }}</td>
                  <td>{{ row.product_name }}</td>
                  <td class="level-col">{{ row.level }}</td>
                  <td class="qty-col">{{ row.quantity }}</td>
                  <td class="lt-col">{{ row.lead_time_days }}</td>
                  <td class="lt-col">{{ row.cumulative_lt }}</td>
                  <td class="duration-col">{{ row.duration_min }}</td>
                  <td>{{ row.process }}</td>
                  <td>{{ row.line }}</td>
                  <td>{{ row.supplier }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else>データがありません</div>
        </div>
        <div v-else>読み込み中...</div>
        <div class="form-actions">
          <button type="button" @click="downloadTreeExcel" class="btn-primary" :disabled="!treeSourceBom?.id">Excel出力</button>
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
                <th>加工先</th>
                <th>加工工程</th>
                <th>自LT</th>
                <th>最終品</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="whereUsedSelfRow" class="self-row">
                <td>★ {{ whereUsedSelfRow.parent_product_code }} - {{ whereUsedSelfRow.parent_product_name }}（検索品）</td>
                <td>{{ getCategoryLabel(whereUsedSelfRow.category) }}</td>
                <td>{{ whereUsedSelfRow.quantity }}</td>
                <td>{{ getSourcingTypeLabel(whereUsedSelfRow.sourcing_type) }}</td>
                <td>{{ formatWhereUsedDestination(whereUsedSelfRow) }}</td>
                <td>{{ formatWhereUsedProcess(whereUsedSelfRow) }}</td>
                <td>{{ formatWhereUsedSelfLt(whereUsedSelfRow) }}</td>
                <td>{{ whereUsedSelfRow.is_final_product ? '最終品' : '' }}</td>
              </tr>
              <template v-for="item in whereUsedResults" :key="item.parent_product_id">
                <tr :style="getItemFinalColor(item) ? { background: getItemFinalColor(item) } : {}">
                  <td>{{ item.parent_product_code }} - {{ item.parent_product_name }}</td>
                  <td>{{ getCategoryLabel(item.category) }}</td>
                  <td>{{ item.quantity }}</td>
                  <td>{{ getSourcingTypeLabel(getWhereUsedDisplaySourcingType(item)) }}</td>
                  <td>{{ formatWhereUsedDestination(item) }}</td>
                  <td>{{ formatWhereUsedProcess(item) }}</td>
                  <td>{{ formatWhereUsedSelfLt(item) }}</td>
                  <td>
                    <span v-if="item.is_final_product" class="final-badge" :style="{ background: getFinalProductColor(item.parent_product_code) }">最終品</span>
                  </td>
                </tr>
                <!-- 再帰結果の子要素（インデント表示） -->
                <template v-if="whereUsedRecursive && item.parents && item.parents.length > 0">
                  <tr v-for="(child, idx) in flattenParents(item.parents, 1)" :key="`${item.parent_product_id}-${idx}`" class="nested-row" :style="child.final_product_code ? { background: getFinalProductColor(child.final_product_code) } : {}">
                    <td :style="{ paddingLeft: (child.level * 20 + 8) + 'px' }">
                      └ {{ child.parent_product_code }} - {{ child.parent_product_name }}
                    </td>
                    <td>{{ getCategoryLabel(child.category) }}</td>
                    <td>{{ child.quantity }}</td>
                    <td>{{ getSourcingTypeLabel(getWhereUsedDisplaySourcingType(child)) }}</td>
                    <td>{{ formatWhereUsedDestination(child) }}</td>
                    <td>{{ formatWhereUsedProcess(child) }}</td>
                    <td>{{ formatWhereUsedSelfLt(child) }}</td>
                    <td>
                      <span v-if="child.is_final_product" class="final-badge" :style="{ background: getFinalProductColor(child.parent_product_code) }">最終品</span>
                    </td>
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
          <button type="button" @click="exportWhereUsedCsv" class="btn-info" :disabled="!whereUsedResults.length">Excel出力</button>
          <button type="button" @click="closeWhereUsedDialog" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>

    <!-- BOMコピーダイアログ -->
    <div v-if="showCopyDialog" class="modal-overlay" @click.self="closeCopyDialog">
      <div class="modal-content">
        <h2>BOMをコピー</h2>
        <p>コピー元: {{ getProductName(selectedBOM.parent_product) }}</p>
        <div class="form-group">
          <label>新しい親製品 *</label>
          <input
            type="text"
            v-model="copyProductFilter"
            placeholder="品番/品名で絞り込み"
            class="filter-input"
          />
          <select v-model="copyNewParentProductId" required>
            <option value="">選択してください</option>
            <option v-for="product in filteredCopyProducts" :key="product.id" :value="product.id">
              {{ product.product_code }} - {{ product.product_name }}
            </option>
          </select>
        </div>
        <div class="form-actions">
          <button type="button" class="btn-primary" @click="doCopyBOM" :disabled="!copyNewParentProductId">コピー実行</button>
          <button type="button" class="btn-secondary" @click="closeCopyDialog">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { ref, onMounted, computed, h, defineComponent, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { canAccessMasterResource } from '@/utils/masterPermissions'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'm_bom', desc: 'BOMヘッダ' },
  { op: '読み書き', table: 'm_bom_item', desc: 'BOM明細' },
  { op: '読み取り', table: 'm_product', desc: '製品（選択肢）' },
  { op: '読み取り', table: 'm_supplier', desc: '仕入先（選択肢）' },
  { op: '読み取り', table: 'm_process', desc: '工程（選択肢）' },
  { op: '読み取り', table: 'm_line', desc: 'ライン（選択肢）' },
  { op: '読み書き', table: 'm_routing', desc: 'ルーティング（自動生成）' },
]

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
  is_active: true,
  is_coproduct: false,
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

const currentPage = ref(1)
const totalCount = ref(0)
const totalPages = ref(0)
const pageSize = ref(20)
const hasSearched = ref(false)

const showDetailsDialog = ref(false)
const selectedBOM = ref({})
const bomItems = ref([])
const bomTree = ref(null)
const treeExcelRows = ref([])
const showTreeDialog = ref(false)
const treeLoading = ref(false)
const expandedNodes = ref(new Set())
const treeSourceBom = ref(null)

// 逆展開用
const showWhereUsedDialog = ref(false)
const whereUsedProductId = ref('')
const whereUsedProductFilter = ref('')
const whereUsedRecursive = ref(false)
const whereUsedResults = ref([])
const whereUsedSelfInfo = ref(null)
const whereUsedLoading = ref(false)

// BOMコピー用
const showCopyDialog = ref(false)
const copyNewParentProductId = ref('')
const copyProductFilter = ref('')
const canEdit = computed(() => canAccessMasterResource('masters.bom', 'edit'))
const showBomImportDialog = ref(false)
const bomImporting = ref(false)
const bomChecking = ref(false)
const bomImportUseExistingDuplicates = ref(false)
const bomImportFile = ref(null)
const bomImportForm = ref({
  version: 'v1',
  completed_product_code: '',
  valid_from: formatISODate(new Date()),
  valid_to: '',
  remark: '',
  is_active: true,
})

const pad2 = (value) => String(value).padStart(2, '0')
const buildDefaultRoutingValidFromLocal = () => {
  const date = new Date()
  date.setDate(date.getDate() + 2)
  date.setHours(8, 0, 0, 0)
  return [
    date.getFullYear(),
    pad2(date.getMonth() + 1),
    pad2(date.getDate()),
  ].join('-') + `T${pad2(date.getHours())}:${pad2(date.getMinutes())}`
}
const normalizeDatetimeLocal = (value) => {
  const raw = String(value || '').trim()
  if (!raw) return null
  return raw.length === 16 ? `${raw}:00` : raw
}

const routingGenForm = ref({
  valid_from_datetime: buildDefaultRoutingValidFromLocal(),
  routing_code: '',
  description: 'bomから自動生成した',
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
  is_coproduct_driver: false,
  remark: '',
  add_to_routing: false,
})
const editingItemId = ref(null)
const originalSourcingType = ref('')
const bomItemsRequestToken = ref(0)
const childProductFilter = ref('')
const parentProductFilter = ref('')

const selectedProcess = computed(() =>
  processes.value.find((p) => `${p.id}` === `${itemForm.value.process}`)
)
const filteredLines = computed(() => {
  const proc = selectedProcess.value
  if (itemForm.value.sourcing_type === 'SUBCON') {
    if (itemForm.value.line) {
      const selectedLine = lines.value.filter((l) => `${l.id}` === `${itemForm.value.line}`)
      return selectedLine.length ? selectedLine : lines.value
    }
    return lines.value
  }
  if (proc?.line) {
    return lines.value.filter((l) => `${l.id}` === `${proc.line}`)
  }
  return lines.value
})

const selectedFinalProcess = computed(() =>
  processes.value.find((p) => `${p.id}` === `${routingGenForm.value.final_process_id}`)
)
const isFinalLineFixedByProcess = computed(() => Boolean(selectedFinalProcess.value?.line))
const filteredFinalLines = computed(() => {
  const proc = selectedFinalProcess.value
  if (proc?.line) {
    return lines.value.filter((l) => `${l.id}` === `${proc.line}`)
  }
  return lines.value
})

const sourcingTypeMap = {
  'MAKE': '自社製造',
  'BUY': '購買',
  'SUBCON': '外作品'
}
const sourcingTypeOptions = [
  { value: 'MAKE', label: '自社製造' },
  { value: 'BUY', label: '購買' },
  { value: 'SUBCON', label: '外作品' }
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
  boms.value = []
  totalCount.value = 0
  totalPages.value = 0
  currentPage.value = 1
  hasSearched.value = false
}

const fetchBOMs = async (page = 1) => {
  hasSearched.value = true
  const targetPage = typeof page === 'number' ? page : 1
  try {
    const params = {
      page: targetPage,
      page_size: pageSize.value
    }

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
    if (response.data.results) {
      boms.value = response.data.results
      totalCount.value = response.data.count
      totalPages.value = Math.ceil(response.data.count / pageSize.value)
    } else {
      boms.value = response.data
      totalCount.value = response.data.length || 0
      totalPages.value = 1
    }
    currentPage.value = targetPage
  } catch (error) {
    console.error('BOM取得エラー:', error)
    alert('BOMデータの取得に失敗しました')
  }
}

const downloadBomImportTemplate = async () => {
  try {
    const response = await api.boms.downloadImportTemplateCsv()
    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8-sig;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'bom_import_template.csv'
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (error) {
    console.error('BOMテンプレート取得エラー:', error)
    alert('テンプレートCSVの取得に失敗しました')
  }
}

const downloadBomImportTemplateXlsx = async () => {
  try {
    const response = await api.boms.downloadImportTemplateXlsx()
    const blob = new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'bom_import_template.xlsx'
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (error) {
    console.error('BOMテンプレートExcel取得エラー:', error)
    alert('テンプレートExcelの取得に失敗しました')
  }
}

const openBomImportDialog = () => {
  bomImportFile.value = null
  bomImportUseExistingDuplicates.value = false
  showBomImportDialog.value = true
}

const closeBomImportDialog = () => {
  showBomImportDialog.value = false
}

const onBomCsvSelected = (event) => {
  bomImportFile.value = event.target.files?.[0] || null
}

const executeBomCsvImport = async () => {
  if (!bomImportFile.value) {
    alert('取込ファイル（CSV/Excel）を選択してください')
    return
  }
  if (!bomImportForm.value.valid_from) {
    alert('有効開始日を入力してください')
    return
  }
  if (!String(bomImportForm.value.completed_product_code || '').trim()) {
    alert('完成品（画面入力）を入力してください')
    return
  }
  bomImporting.value = true
  try {
    const buildImportFormData = (useExistingDuplicates) => {
      const fd = new FormData()
      fd.append('file', bomImportFile.value)
      fd.append('version', bomImportForm.value.version || 'v1')
      fd.append('completed_product_code', bomImportForm.value.completed_product_code || '')
      fd.append('valid_from', bomImportForm.value.valid_from)
      fd.append('valid_to', bomImportForm.value.valid_to || '')
      fd.append('remark', bomImportForm.value.remark || '')
      fd.append('is_active', String(!!bomImportForm.value.is_active))
      fd.append('use_existing_duplicates', String(!!useExistingDuplicates))
      return fd
    }

    let res
    try {
      res = await api.boms.importBOMCsv(buildImportFormData(bomImportUseExistingDuplicates.value))
    } catch (error) {
      const duplicateBoms = error?.response?.data?.duplicate_boms || []
      if (Array.isArray(duplicateBoms) && duplicateBoms.length > 0) {
        const preview = duplicateBoms.slice(0, 10).join('\n')
        const useExisting = window.confirm(
          `既存BOM重複があります。\n${preview}\n\n既存BOMを再利用して取込しますか？`
        )
        if (!useExisting) {
          throw error
        }
        bomImportUseExistingDuplicates.value = true
        res = await api.boms.importBOMCsv(buildImportFormData(true))
      } else {
        throw error
      }
    }

    const reused = res?.data?.reused_boms || 0
    alert(`${res.data.message}\nBOM: ${res.data.created_boms}件 / 明細: ${res.data.created_items}件 / 再利用: ${reused}件`)
    showBomImportDialog.value = false
    fetchBOMs(1)
  } catch (error) {
    console.error('BOM取込エラー:', error)
    const errors = error?.response?.data?.errors
    const detail = error?.response?.data?.detail || '取込に失敗しました'
    if (Array.isArray(errors) && errors.length) {
      alert(`${detail}\n${errors.slice(0, 10).join('\n')}`)
    } else {
      alert(detail)
    }
  } finally {
    bomImporting.value = false
  }
}

const executeBomImportCheck = async () => {
  if (!bomImportFile.value) {
    alert('取込ファイル（CSV/Excel）を選択してください')
    return
  }
  if (!String(bomImportForm.value.completed_product_code || '').trim()) {
    alert('完成品（画面入力）を入力してください')
    return
  }
  bomChecking.value = true
  try {
    const fd = new FormData()
    fd.append('file', bomImportFile.value)
    fd.append('completed_product_code', bomImportForm.value.completed_product_code || '')
    fd.append('version', bomImportForm.value.version || 'v1')
    fd.append('valid_from', bomImportForm.value.valid_from || '')
    const res = await api.boms.importBOMCheck(fd)
    const duplicateBoms = res?.data?.duplicate_boms || []
    if (duplicateBoms.length) {
      const preview = duplicateBoms.slice(0, 10).join('\n')
      const useExisting = window.confirm(
        `既存BOM重複があります。\n${preview}\n\n既存BOMを再利用して取込しますか？`
      )
      bomImportUseExistingDuplicates.value = useExisting
      alert(`チェック件数: ${res.data.checked_rows}件\n重複: ${duplicateBoms.length}件\n再利用設定: ${useExisting ? 'する' : 'しない'}`)
    } else {
      bomImportUseExistingDuplicates.value = false
      alert(`${res.data.message}\nチェック件数: ${res.data.checked_rows}件`)
    }
  } catch (error) {
    console.error('BOM取込チェックエラー:', error)
    const errors = error?.response?.data?.errors
    const detail = error?.response?.data?.detail || 'チェックに失敗しました'
    if (Array.isArray(errors) && errors.length) {
      alert(`${detail}\n${errors.slice(0, 15).join('\n')}`)
    } else {
      alert(detail)
    }
  } finally {
    bomChecking.value = false
  }
}

const changePage = (newPage) => {
  if (newPage >= 1 && newPage <= totalPages.value) {
    fetchBOMs(newPage)
  }
}

const fetchProducts = async () => {
  try {
    // 全ページ取得（現状フィルタなし）
    products.value = (await api.products.getAllProducts({ page_size: 10000 })).sort((a, b) =>
      (b.product_code || '').localeCompare(a.product_code || '')
    )
  } catch (error) {
    console.error('製品取得エラー:', error)
  }
}

const fetchSuppliers = async () => {
  try {
    const response = await api.suppliers.getSuppliers({ page_size: 1000 })
    suppliers.value = response.data.results || response.data
  } catch (error) {
    console.error('仕入先取得エラー:', error)
  }
}

const fetchProcesses = async () => {
  try {
    const response = await api.processes.getProcesses({ page_size: 1000 })
    processes.value = response.data.results || response.data
    if (itemForm.value.sourcing_type === 'SUBCON') {
      applySourcingSideEffects()
    }
  } catch (error) {
    console.error('工程取得エラー:', error)
  }
}

const fetchLines = async () => {
  try {
    const response = await api.lines.getLines({ page_size: 1000 })
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
    is_coproduct_driver: false,
    remark: '',
    add_to_routing: false,
  }
  editingItemId.value = null
  originalSourcingType.value = ''
  childProductFilter.value = ''
}

const getOutsourceProcessId = () => {
  const outsourceProcessByName = processes.value.find((p) =>
    String(p.process_name || '').includes('外作工程') ||
    String(p.process_code || '').includes('外作工程') ||
    String(p.process_name || '').includes('外作') ||
    String(p.process_code || '').includes('外作')
  )
  if (outsourceProcessByName) return outsourceProcessByName.id
  const outsourceProcessByFlag = processes.value.find((p) => p.is_outsource)
  return outsourceProcessByFlag ? outsourceProcessByFlag.id : ''
}

const applySourcingSideEffects = () => {
  if (itemForm.value.sourcing_type === 'MAKE') {
    itemForm.value.supplier = ''
    if (!itemForm.value.time_unit) itemForm.value.time_unit = 'MINUTE'
  }
  if (itemForm.value.sourcing_type === 'SUBCON') {
    itemForm.value.time_unit = 'DAY'
    const outsourceProcessId = getOutsourceProcessId()
    if (outsourceProcessId) itemForm.value.process = outsourceProcessId
    if (
      itemForm.value.lead_time_days === null ||
      itemForm.value.lead_time_days === undefined ||
      itemForm.value.lead_time_days === '' ||
      Number(itemForm.value.lead_time_days) === 0
    ) {
      itemForm.value.lead_time_days = 1
    }
    if (itemForm.value.supplier) {
      const supplier = suppliers.value.find((s) => `${s.id}` === `${itemForm.value.supplier}`)
      const matchingLine = supplier && lines.value.find(
        (l) => l.line_code === supplier.supplier_code && l.line_type === 'PURCHASE'
      )
      if (matchingLine) {
        itemForm.value.line = matchingLine.id
      }
    }
  }
  if (itemForm.value.sourcing_type === 'BUY') {
    itemForm.value.process = ''
    itemForm.value.line = ''
    itemForm.value.time_unit = 'DAY'
    itemForm.value.duration_min = null
    if (itemForm.value.lead_time_days === null || itemForm.value.lead_time_days === undefined || itemForm.value.lead_time_days === '') {
      itemForm.value.lead_time_days = 1
    }
  }
}

const resetRoutingGenForm = () => {
  routingGenForm.value = {
    valid_from_datetime: buildDefaultRoutingValidFromLocal(),
    routing_code: '',
    description: 'bomから自動生成した',
    final_process_id: '',
    final_line_id: '',
    final_time_unit: 'MINUTE',
    final_lead_time_days: 0,
    final_duration_min: 60,
  }
}

const fetchBOMItems = async (bomId, token = bomItemsRequestToken.value) => {
  const response = await api.boms.getBOMItems({ bom: bomId, page_size: 1000 })
  if (token !== bomItemsRequestToken.value) return
  const items = response.data.results || response.data || []
  // 追加した最新の明細が上に来るように逆順表示（APIデフォルトは昇順）
  bomItems.value = items.slice().reverse()
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

const fetchBOMTreeExcelRows = async (bomId) => {
  try {
    const response = await api.boms.getBOMTreeExcelRows(bomId)
    const payload = response.data || {}
    treeExcelRows.value = payload.rows || []
  } catch (error) {
    console.error('BOM階層図（Excel列）取得エラー:', error)
    treeExcelRows.value = []
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

const isCoproductBom = (bom) => {
  if (!bom) return false
  if (bom.is_coproduct) return true
  const parentProductId = typeof bom.parent_product === 'object'
    ? bom.parent_product?.id
    : bom.parent_product
  const parentProduct = products.value.find((p) => `${p.id}` === `${parentProductId}`)
  return Boolean(parentProduct?.is_virtual_set)
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

const whereUsedSelfRow = computed(() => {
  const src = whereUsedSelfInfo.value
  const selectedProduct = findProductById(whereUsedProductId.value)
  if (!src?.product_id && !selectedProduct) return null

  if (src?.product_id) {
    return {
      parent_product_id: src.product_id,
      parent_product_code: src.product_code,
      parent_product_name: src.product_name,
      category: src.category,
      quantity: 1,
      sourcing_type: src.sourcing_type || 'MAKE',
      is_final_product: Boolean(src.is_final_product),
      parent_line_id: src.line_id,
      parent_line_code: src.line_code,
      parent_line_name: src.line_name,
      parent_line_type: src.line_type,
      parent_process_id: src.process_id,
      parent_process_code: src.process_code,
      parent_process_name: src.process_name,
      parent_self_lt_days: src.self_lt_days,
    }
  }

  const lineObj = findLineById(selectedProduct?.line)
  const processObj = findProcessById(selectedProduct?.process)
  const lineType = lineObj?.line_type || ''
  let sourcingType = 'MAKE'
  if (lineType === 'PURCHASE' || selectedProduct?.category === 'PURCHASED') {
    sourcingType = 'BUY'
  } else if (lineType === 'OUTSOURCE') {
    sourcingType = 'SUBCON'
  }

  return {
    parent_product_id: selectedProduct.id,
    parent_product_code: selectedProduct.product_code,
    parent_product_name: selectedProduct.product_name,
    category: selectedProduct.category,
    quantity: 1,
    sourcing_type: sourcingType,
    is_final_product: Boolean(selectedProduct.is_final_product),
    parent_line_id: selectedProduct.line ?? null,
    parent_line_code: lineObj?.line_code || null,
    parent_line_name: lineObj?.line_name || null,
    parent_line_type: lineType || null,
    parent_process_id: selectedProduct.process ?? null,
    parent_process_code: processObj?.process_code || null,
    parent_process_name: processObj?.process_name || null,
    parent_self_lt_days: selectedProduct.self_lt_days,
  }
})

const filteredCopyProducts = computed(() => {
  const keyword = copyProductFilter.value.trim().toLowerCase()
  let pool = products.value
  // 連産品BOMの場合は仮想セット品番のみ
  if (isCoproductBom(selectedBOM.value)) {
    pool = pool.filter(p => p.is_virtual_set)
  }
  if (!keyword) return pool
  return pool.filter((p) =>
    `${p.product_code} ${p.product_name}`.toLowerCase().includes(keyword)
  )
})

const selectedBomIsCoproduct = computed(() => isCoproductBom(selectedBOM.value))

const categoryMap = {
  'ASSEMBLY': '組立品',
  'SINGLE': '単品',
  'MATERIAL': '材料',
  'PURCHASED': '購入品',
  'OUTSOURCED': '外作品',
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

const getLineType = (lineId) => {
  if (!lineId) return ''
  const line = lines.value.find(l => `${l.id}` === `${lineId}`)
  return line?.line_type || ''
}

const getSourcingTypeLabel = (value) => sourcingTypeMap[value] || value

const formatCodeName = (code, name) => {
  if (code && name) return `${code} ${name}`
  return code || name || ''
}

const findProductById = (productId) => {
  if (!productId) return null
  return products.value.find((product) => `${product.id}` === `${productId}`) || null
}

const findLineById = (lineId) => {
  if (!lineId) return null
  return lines.value.find((line) => `${line.id}` === `${lineId}`) || null
}

const findProcessById = (processId) => {
  if (!processId) return null
  return processes.value.find((process) => `${process.id}` === `${processId}`) || null
}

const getWhereUsedDisplaySourcingType = (item) => {
  if (!item) return ''
  const lineType = item.parent_line_type || item.line_type || ''
  if (lineType === 'PURCHASE') return 'BUY'
  if (lineType === 'OUTSOURCE') return 'SUBCON'
  if (lineType) return 'MAKE'
  return item.sourcing_type
}

const formatWhereUsedDestination = (item) => {
  if (!item) return ''
  const sourcingType = getWhereUsedDisplaySourcingType(item)
  const parentProduct = findProductById(item.parent_product_id)
  const parentLineId = item.parent_line_id || parentProduct?.line || null
  const parentLineObj = findLineById(parentLineId)
  const parentLineLabel = formatCodeName(item.parent_line_code || parentLineObj?.line_code, item.parent_line_name || parentLineObj?.line_name)
  const supplierLabel = formatCodeName(item.supplier_code, item.supplier_name)
  const lineType = item.parent_line_type || parentLineObj?.line_type || item.line_type || getLineType(item.line_id)

  if (lineType === 'OUTSOURCE') {
    return supplierLabel || parentLineLabel || '-'
  }

  switch (sourcingType) {
    case 'BUY':
      return supplierLabel || parentLineLabel || '-'
    case 'SUBCON':
      return parentLineLabel || supplierLabel || '-'
    default:
      return parentLineLabel || supplierLabel || '-'
  }
}

const formatWhereUsedProcess = (item) => {
  if (!item) return '-'
  const parentProduct = findProductById(item.parent_product_id)
  const parentProcessId = item.parent_process_id || parentProduct?.process || null
  const parentProcessObj = findProcessById(parentProcessId)
  const parentProcessLabel = formatCodeName(item.parent_process_code || parentProcessObj?.process_code, item.parent_process_name || parentProcessObj?.process_name)
  return parentProcessLabel || '-'
}

const formatWhereUsedSelfLt = (item) => {
  if (!item) return '-'
  const parentProduct = findProductById(item.parent_product_id)
  const selfLt = item.parent_self_lt_days ?? parentProduct?.self_lt_days
  if (selfLt === null || selfLt === undefined || selfLt === '') return '-'
  return selfLt
}

const goToDetailPage = (bom) => {
  if (!bom?.id) return
  router.push({ name: 'BOMMaster', query: { bomId: bom.id, detail: 'full' } })
}

const showNewDialog = () => {
  if (!canEdit.value) return
  closeDetailsDialog()
  isEdit.value = false
  parentProductFilter.value = ''
  const today = formatISODate(new Date())
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
    parent_product: bom.parent_product,
    valid_to: bom.valid_to || '',
    is_coproduct: bom.is_coproduct ?? false,
  }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
  parentProductFilter.value = ''
}

const saveBOM = async () => {
  if (!canEdit.value) return
  try {
    const selectedParentProduct = products.value.find((p) => `${p.id}` === `${formData.value.parent_product}`)
    const isVirtualSetParent = Boolean(selectedParentProduct?.is_virtual_set)
    const dataToSend = {
      parent_product: formData.value.parent_product,
      version: formData.value.version,
      valid_from: formData.value.valid_from,
      valid_to: formData.value.valid_to || null,
      is_active: formData.value.is_active,
      is_coproduct: formData.value.is_coproduct || isVirtualSetParent,
    }

    if (isEdit.value) {
      await api.boms.updateBOM(formData.value.id, dataToSend)
      alert('更新しました')
    } else {
      await api.boms.createBOM(dataToSend)
      alert('作成しました')
    }
    await fetchBOMs(currentPage.value)
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
  if (!canEdit.value) return
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.boms.deleteBOM(id)
    await fetchBOMs(currentPage.value)
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
    valid_from_datetime: normalizeDatetimeLocal(routingGenForm.value.valid_from_datetime),
    description: routingGenForm.value.description || undefined,
    routing_code: routingGenForm.value.routing_code || undefined,
    is_default: true,
  }

  // 最終工程のオプション指定がある場合だけ付与
  if (routingGenForm.value.final_process_id) {
    payload.final_process_id = routingGenForm.value.final_process_id
    const finalLineId = selectedFinalProcess.value?.line || routingGenForm.value.final_line_id
    if (finalLineId) {
      payload.final_line_id = finalLineId
    }
    payload.final_time_unit = routingGenForm.value.final_time_unit
    if (routingGenForm.value.final_lead_time_days === null || routingGenForm.value.final_lead_time_days === undefined || routingGenForm.value.final_lead_time_days < 0) {
      alert('最終工程のリードタイム(日)を0以上で入力してください')
      return
    }
    payload.final_lead_time_days = routingGenForm.value.final_lead_time_days
    if (routingGenForm.value.final_time_unit === 'MINUTE') {
      if (!routingGenForm.value.final_duration_min || routingGenForm.value.final_duration_min <= 0) {
        alert('最終工程の所要時間(分)を1以上で入力してください')
        return
      }
      payload.final_duration_min = routingGenForm.value.final_duration_min
    } else {
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
  selectedBOM.value = {
    ...bom,
    is_coproduct: isCoproductBom(bom),
  }
  resetItemForm()
  resetRoutingGenForm()
  childProductFilter.value = ''
  bomItems.value = []
  bomTree.value = null
  treeExcelRows.value = []
  const token = ++bomItemsRequestToken.value
  showDetailsDialog.value = openDialog && !isStandaloneDetail.value
  try {
    await fetchBOMItems(bom.id, token)
    await Promise.all([
      fetchBOMTree(bom.id),
      fetchBOMTreeExcelRows(bom.id),
    ])
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
  treeExcelRows.value = []
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
  treeSourceBom.value = bom
  showTreeDialog.value = true
  treeLoading.value = true
  bomTree.value = null
  treeExcelRows.value = []
  expandedNodes.value = new Set()
  try {
    await Promise.all([
      fetchBOMTree(bom.id),
      fetchBOMTreeExcelRows(bom.id),
    ])
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
  treeExcelRows.value = []
  treeSourceBom.value = null
  expandedNodes.value = new Set()
}

// 逆展開関連
const openWhereUsedDialog = () => {
  showWhereUsedDialog.value = true
  whereUsedProductId.value = ''
  whereUsedProductFilter.value = ''
  whereUsedRecursive.value = false
  whereUsedResults.value = []
  whereUsedSelfInfo.value = null
}

const closeWhereUsedDialog = () => {
  showWhereUsedDialog.value = false
  whereUsedProductId.value = ''
  whereUsedProductFilter.value = ''
  whereUsedRecursive.value = false
  whereUsedResults.value = []
  whereUsedSelfInfo.value = null
}

// BOMコピー
const openCopyDialog = () => {
  if (!canEdit.value) return
  copyNewParentProductId.value = ''
  copyProductFilter.value = ''
  showCopyDialog.value = true
}

const closeCopyDialog = () => {
  showCopyDialog.value = false
  copyNewParentProductId.value = ''
  copyProductFilter.value = ''
}

const doCopyBOM = async () => {
  if (!canEdit.value) return
  if (!selectedBOM.value?.id || !copyNewParentProductId.value) return
  let newBomId = null
  try {
    const response = await api.boms.copyBOM(selectedBOM.value.id, copyNewParentProductId.value)
    newBomId = response.data.new_bom_id
  } catch (error) {
    console.error('BOMコピーAPIエラー:', error)
    alert('BOMのコピーに失敗しました')
    return
  }

  alert(`BOMをコピーしました（新しいBOM ID: ${newBomId}）`)
  closeCopyDialog()
  closeDetailsDialog()

  try {
    await fetchBOMs(currentPage.value)
    // 新しいBOMを開く
    const newBom = boms.value.find(b => b.id === newBomId)
    if (newBom) {
      await viewDetails(newBom)
    }
  } catch (error) {
    console.error('BOMコピー後の画面更新エラー:', error)
  }
}

const fetchWhereUsed = async () => {
  if (!whereUsedProductId.value) {
    whereUsedResults.value = []
    whereUsedSelfInfo.value = null
    return
  }
  whereUsedLoading.value = true
  try {
    const response = await api.products.getWhereUsed(
      whereUsedProductId.value,
      whereUsedRecursive.value
    )
    if (response.data?.self_info) {
      whereUsedSelfInfo.value = response.data.self_info
    } else {
      const selectedProduct = findProductById(whereUsedProductId.value)
      const lineObj = findLineById(selectedProduct?.line)
      const processObj = findProcessById(selectedProduct?.process)
      const lineType = lineObj?.line_type || ''
      let sourcingType = 'MAKE'
      if (lineType === 'PURCHASE' || selectedProduct?.category === 'PURCHASED') {
        sourcingType = 'BUY'
      } else if (lineType === 'OUTSOURCE') {
        sourcingType = 'SUBCON'
      }
      whereUsedSelfInfo.value = {
        product_id: response.data?.product_id || selectedProduct?.id || null,
        product_code: response.data?.product_code || selectedProduct?.product_code || '',
        product_name: response.data?.product_name || selectedProduct?.product_name || '',
        category: selectedProduct?.category || '',
        is_final_product: Boolean(selectedProduct?.is_final_product),
        sourcing_type: sourcingType,
        line_id: selectedProduct?.line || null,
        line_code: lineObj?.line_code || null,
        line_name: lineObj?.line_name || null,
        line_type: lineType || null,
        process_id: selectedProduct?.process || null,
        process_code: processObj?.process_code || null,
        process_name: processObj?.process_name || null,
        self_lt_days: selectedProduct?.self_lt_days ?? null,
      }
    }
    whereUsedResults.value = response.data.parents || []
  } catch (error) {
    console.error('逆展開取得エラー:', error)
    alert('逆展開データの取得に失敗しました')
    whereUsedResults.value = []
    whereUsedSelfInfo.value = null
  } finally {
    whereUsedLoading.value = false
  }
}

const findFinalProductCodes = (node) => {
  const codes = []
  if (node.is_final_product) codes.push(node.parent_product_code)
  if (node.parents && node.parents.length > 0) {
    for (const p of node.parents) {
      codes.push(...findFinalProductCodes(p))
    }
  }
  return [...new Set(codes)]
}

const FINAL_PRODUCT_COLORS = [
  '#e3f2fd', '#fce4ec', '#e8f5e9', '#fff3e0', '#f3e5f5',
  '#e0f7fa', '#fff9c4', '#fbe9e7', '#e8eaf6', '#f1f8e9',
]

const allFinalProductCodes = computed(() => {
  const codes = new Set()
  for (const item of whereUsedResults.value) {
    findFinalProductCodes(item).forEach(c => codes.add(c))
  }
  return Array.from(codes)
})

const getFinalProductColor = (code) => {
  if (!code) return ''
  const idx = allFinalProductCodes.value.indexOf(code)
  if (idx < 0) return ''
  return FINAL_PRODUCT_COLORS[idx % FINAL_PRODUCT_COLORS.length]
}

const getItemFinalColor = (item) => {
  const codes = findFinalProductCodes(item)
  return getFinalProductColor(codes[0] || null)
}

const flattenParents = (parents, level) => {
  const result = []
  for (const p of parents) {
    const finalCode = p.is_final_product
      ? p.parent_product_code
      : (findFinalProductCodes(p)[0] || null)
    result.push({ ...p, level, final_product_code: finalCode })
    if (p.parents && p.parents.length > 0) {
      result.push(...flattenParents(p.parents, level + 1))
    }
  }
  return result
}

const escCsv = (val) => {
  if (val === null || val === undefined) return ''
  const str = String(val)
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return '"' + str.replace(/"/g, '""') + '"'
  }
  return str
}

const exportWhereUsedCsv = () => {
  if (!whereUsedResults.value.length) return
  const selectedProduct = findProductById(whereUsedProductId.value)
  const searchCode = selectedProduct?.product_code || ''
  const searchName = selectedProduct?.product_name || ''

  const bom = '﻿'
  const lines = []
  lines.push(['逆展開（Where Used）'].map(escCsv).join(','))
  lines.push(['検索品', `${searchCode} - ${searchName}`].map(escCsv).join(','))
  lines.push('')

  const header = ['親製品', 'カテゴリ', '数量', '調達区分', '加工先', '加工工程', '自LT', '最終品']
  lines.push(header.map(escCsv).join(','))

  const pushRow = (item, prefix) => {
    lines.push([
      escCsv(`${prefix}${item.parent_product_code} - ${item.parent_product_name}`),
      escCsv(getCategoryLabel(item.category)),
      escCsv(item.quantity),
      escCsv(getSourcingTypeLabel(getWhereUsedDisplaySourcingType(item))),
      escCsv(formatWhereUsedDestination(item)),
      escCsv(formatWhereUsedProcess(item)),
      escCsv(formatWhereUsedSelfLt(item)),
      escCsv(item.is_final_product ? '最終品' : ''),
    ].join(','))
  }

  if (whereUsedSelfRow.value) {
    pushRow(whereUsedSelfRow.value, '★ ')
  }
  for (const item of whereUsedResults.value) {
    pushRow(item, '')
    if (whereUsedRecursive.value && item.parents && item.parents.length > 0) {
      for (const child of flattenParents(item.parents, 1)) {
        const indent = '　'.repeat(child.level - 1) + '└ '
        pushRow(child, indent)
      }
    }
  }

  const csvContent = bom + lines.join('\r\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `逆展開_${searchCode}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

const downloadBOMExcel = async (bom) => {
  try {
    const response = await api.boms.exportBOMExcel(bom.id)
    const productCode = getParentProductCode(bom)
    const filename = `${productCode}_BOM_TREE.xlsx`
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Excel出力エラー:', error)
    alert('Excel出力に失敗しました')
  }
}

const downloadTreeExcel = async () => {
  if (!treeSourceBom.value?.id) return
  await downloadBOMExcel(treeSourceBom.value)
}

const startEditItem = (item) => {
  if (!canEdit.value) return
  editingItemId.value = item.id
  originalSourcingType.value = item.sourcing_type || ''
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
    is_coproduct_driver: item.is_coproduct_driver ?? false,
    remark: item.remark ?? ''
  }
  applySourcingSideEffects()
}

const saveBOMItem = async () => {
  if (!canEdit.value) return
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
    if (itemForm.value.sourcing_type === 'MAKE' && !itemForm.value.line) {
      alert('自社製造の場合、ラインは必須です')
      return
    }
    if (itemForm.value.time_unit === 'MINUTE' && (!itemForm.value.duration_min || itemForm.value.duration_min <= 0)) {
      alert('時間単位=分のときは所要時間(分)を1以上で入力してください')
      return
    }
    if (itemForm.value.time_unit === 'DAY' && itemForm.value.lead_time_days < 0) {
      alert('時間単位=日 のときはリードタイム(日)を0以上で入力してください')
      return
    }
  } else if (itemForm.value.sourcing_type === 'BUY') {
    if (!itemForm.value.supplier) {
      alert('購買の場合、仕入先は必須です')
      return
    }
    if (itemForm.value.lead_time_days === null || itemForm.value.lead_time_days === undefined || itemForm.value.lead_time_days < 0) {
      alert('購買の場合、リードタイム(日)を0以上で入力してください')
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
    is_coproduct_driver: selectedBomIsCoproduct.value ? itemForm.value.is_coproduct_driver : false,
    remark: itemForm.value.remark || '',
    ...((!editingItemId.value && itemForm.value.add_to_routing) ? { add_to_routing: true } : {}),
  }

  if (payload.add_to_routing) {
    if (!window.confirm('この親製品をoutput_productとする全アクティブルーティングにステップが追加されます。続行しますか？')) return
  }

  try {
    if (editingItemId.value) {
      const sourcingTypeChanged = !!originalSourcingType.value && originalSourcingType.value !== itemForm.value.sourcing_type
      if (sourcingTypeChanged) {
        const ok = window.confirm('加工区分は変更でいいですか？')
        if (!ok) return
      }
      await api.boms.updateBOMItem(editingItemId.value, payload)
      alert('明細を更新しました')
      if (sourcingTypeChanged) {
        alert('ルーティングを手動で直してください')
      }
    } else {
      const res = await api.boms.createBOMItem(payload)
      const stepsCreated = res.data?.routing_steps_created
      if (stepsCreated != null && stepsCreated > 0) {
        alert(`明細を追加しました（${stepsCreated}件のステップ追加）`)
      } else if (payload.add_to_routing) {
        alert('明細を追加しました（対象ルーティングなし）')
      } else {
        alert('明細を追加しました')
      }
    }
    await fetchBOMItems(selectedBOM.value.id)
    await fetchBOMTree(selectedBOM.value.id)
    expandAllNodes()
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
  if (!canEdit.value) return
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

watch(
  () => itemForm.value.process,
  (newProcess) => {
    const proc = processes.value.find((p) => `${p.id}` === `${newProcess}`)
    if (proc?.line) {
      // SUBCON+仕入先設定済みなら仕入先のPURCHASEラインを優先
      if (itemForm.value.sourcing_type === 'SUBCON' && itemForm.value.supplier) {
        const supplier = suppliers.value.find((s) => `${s.id}` === `${itemForm.value.supplier}`)
        const matchingLine = supplier && lines.value.find(
          (l) => l.line_code === supplier.supplier_code && l.line_type === 'PURCHASE'
        )
        itemForm.value.line = matchingLine ? matchingLine.id : proc.line
      } else {
        itemForm.value.line = proc.line
      }
    } else if (itemForm.value.line && !lines.value.find((l) => l.id === itemForm.value.line)) {
      itemForm.value.line = ''
    }
  }
)

watch(
  () => itemForm.value.sourcing_type,
  () => {
    applySourcingSideEffects()
  }
)

watch(
  () => routingGenForm.value.final_process_id,
  (newProcess) => {
    const proc = processes.value.find((p) => `${p.id}` === `${newProcess}`)
    if (proc?.line) {
      routingGenForm.value.final_line_id = proc.line
    } else if (
      routingGenForm.value.final_line_id &&
      !lines.value.find((l) => `${l.id}` === `${routingGenForm.value.final_line_id}`)
    ) {
      routingGenForm.value.final_line_id = ''
    }
  }
)

watch(
  () => itemForm.value.supplier,
  (supplierId) => {
    if (!supplierId) return
    if (itemForm.value.sourcing_type !== 'SUBCON') return
    const supplier = suppliers.value.find((s) => `${s.id}` === `${supplierId}`)
    if (!supplier) return
    const matchingLine = lines.value.find(
      (l) => l.line_code === supplier.supplier_code && l.line_type === 'PURCHASE'
    )
    if (matchingLine) {
      itemForm.value.line = matchingLine.id
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

.bom-list-area {
  max-height: min(65vh, 640px);
  overflow: auto;
}

.bom-list-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #eef1ff;
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
  width: min(96vw, 1600px);
  min-width: 1100px;
  max-width: 1600px;
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
  width: max-content;
  min-width: 1400px;
  border-collapse: collapse;
  font-size: 0.95rem;
}

.tree-grid th,
.tree-grid td {
  border: 1px solid #d6dce6;
  padding: 6px 8px;
  white-space: nowrap;
  vertical-align: top;
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
  width: 40px;
  text-align: center;
}

.qty-col {
  width: 36px;
  text-align: right;
}

.lt-col {
  width: 50px;
  text-align: right;
}

.duration-col {
  width: 60px;
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
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.5rem 0.75rem;
}

/* 構成品目フォームをぎゅっと詰める */
.item-form .form-row {
  grid-template-columns: repeat(auto-fit, minmax(120px, auto));
  gap: 0.25rem 0.5rem;
  justify-content: flex-start;
}

.item-form .form-group {
  width: auto;
}

.item-form .form-group .narrow-field {
  width: 110px;
  min-width: 90px;
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

.tall-number-input {
  width: 100%;
  padding: 0.55rem 0.7rem;
  min-height: 38px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  box-sizing: border-box;
}

.narrow-field {
  width: 25%;
  min-width: 80px;
  box-sizing: border-box;
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
.final-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  color: #1a1a1a;
  border: 1px solid rgba(0, 0, 0, 0.15);
}

.loading-text {
  padding: 1rem;
  text-align: center;
  color: #666;
}

.btn-excel {
  background-color: #217346;
  color: white;
  border-color: #1a5c38;
}

.btn-excel:hover {
  background-color: #1a5c38;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
}

.page-info {
  font-size: 14px;
  color: #555;
}
</style>
