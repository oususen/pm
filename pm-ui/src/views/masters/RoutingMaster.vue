<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">ルーティングマスタ <DataSourceDialog title="ルーティングマスタ" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button
          v-if="canEdit"
          class="btn-success"
          @click="toggleCreateRow"
          :disabled="creatingRouting || loadingProducts"
        >
          {{ showCreateRow ? '新規入力を閉じる' : '新規' }}
        </button>
        <select v-model="migrationLineId" class="line-select" :disabled="loadingLines">
          <option value="">ライン選択（在庫移行用）</option>
          <option v-for="line in lines" :key="line.id" :value="line.id">
            {{ line.line_code }} - {{ line.line_name }}
          </option>
        </select>
        <button
          class="btn-warning"
          @click="openMigrationDialog"
          :disabled="!migrationLineId || checkingMigration"
        >
          {{ checkingMigration ? '確認中...' : 'ルーティング変更後の在庫移行' }}
        </button>
        <button class="btn-primary" @click="refreshAll" :disabled="loadingRoutings || loadingSteps">
          更新
        </button>
      </div>
    </div>

    <div class="filter-row">
      <input
        v-model.trim="searchText"
        class="search-input"
        placeholder="品番コードで検索"
      />
      <select v-model="filterFinalLineId" class="line-select line-select--filter" :disabled="loadingLines || loadingRoutingFinalLineMap">
        <option value="">最終工程ライン: すべて</option>
        <option v-for="line in lines" :key="`flt-line-${line.id}`" :value="String(line.id)">
          {{ line.line_code }} - {{ line.line_name }}
        </option>
      </select>
      <input
        v-model.trim="filterProductName"
        class="search-input search-input--narrow"
        placeholder="品名（部分一致）"
      />
      <select v-model="filterCustomerCode" class="line-select line-select--filter" :disabled="loadingCustomers || loadingCustomerProductSet">
        <option value="">得意先: すべて</option>
        <option v-for="customer in customerOptions" :key="`flt-customer-${customer.id}`" :value="customer.customer_code">
          {{ customer.customer_code }} - {{ customer.customer_name }}
        </option>
      </select>
      <label class="checkbox-inline">
        <input v-model="onlyActive" type="checkbox" />
        有効のみ
      </label>
      <span class="count-text">表示件数: {{ filteredRoutings.length }}</span>
      <span v-if="!canEdit" class="readonly-note">閲覧のみ（編集権限なし）</span>
    </div>
    <div v-if="canEdit && showCreateRow" class="create-row">
      <div class="create-step-field" style="position:relative;">
        <input
          v-model="newRoutingProductSearch"
          type="text"
          class="create-select"
          placeholder="品番/品名で検索"
          :disabled="creatingRouting || loadingProducts"
          @focus="newRoutingProductDropOpen = true"
          @input="newRoutingProductDropOpen = true; newRoutingDraft.product = ''"
          @blur="newRoutingProductDropOpen = false"
        />
        <ul v-if="newRoutingProductDropOpen && filteredNewRoutingProducts.length" class="autocomplete-list">
          <li
            v-for="product in filteredNewRoutingProducts"
            :key="product.id"
            @mousedown.prevent="selectNewRoutingProduct(product)"
            class="autocomplete-item"
          >
            {{ product.product_code }} - {{ product.product_name }}
          </li>
        </ul>
      </div>
      <input
        v-model.trim="newRoutingDraft.routing_code"
        class="create-input"
        type="text"
        maxlength="30"
        placeholder="ルーティングコード"
        :disabled="creatingRouting"
      />
      <input
        v-model.trim="newRoutingDraft.description"
        class="create-input create-input--wide"
        type="text"
        placeholder="説明（任意）"
        :disabled="creatingRouting"
      />
      <label class="checkbox-inline">
        <input v-model="newRoutingDraft.is_default" type="checkbox" :disabled="creatingRouting" />
        既定
      </label>
      <label class="checkbox-inline">
        <input v-model="newRoutingDraft.is_active" type="checkbox" :disabled="creatingRouting" />
        有効
      </label>
      <button class="btn-primary" @click="createRouting" :disabled="isCreateDisabled">
        {{ creatingRouting ? '作成中...' : '作成' }}
      </button>
    </div>

    <div class="split-layout" :class="{ 'split-layout--single': !showRoutingList }">
      <section v-show="showRoutingList" class="panel routing-panel">
        <h2 class="panel-title">ルーティング一覧</h2>
        <div class="table-wrap">
          <table class="data-table compact">
            <thead>
              <tr>
                <th>品番</th>
                <th>品名</th>
                <th>既定</th>
                <th>有効</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="routing in filteredRoutings"
                :key="routing.id"
                :class="{ selected: selectedRoutingId === routing.id }"
                @click="selectRouting(routing.id)"
              >
                <td>{{ productCode(routing) }}</td>
                <td>{{ productName(routing) }}</td>
                <td>{{ routing.is_default ? '○' : '' }}</td>
                <td>{{ routing.is_active ? '有効' : '無効' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="!loadingRoutings && filteredRoutings.length === 0" class="empty-state">
            該当データがありません
          </div>
        </div>
      </section>

      <section class="panel step-panel">
        <div v-if="loadingSteps" class="step-panel-overlay">
          <div class="step-panel-overlay__content">
            <span class="loading-spinner loading-spinner--lg"></span>
            <div>代表部品判定をダウンロード中...</div>
          </div>
        </div>
        <h2 class="panel-title">
          工程一覧
          <span v-if="selectedRouting" class="panel-subtitle">
            {{ productCode(selectedRouting) }} / {{ selectedRouting.routing_code }}
          </span>
          <button class="btn-secondary btn-small panel-toggle-btn" @click="showRoutingList = !showRoutingList">
            {{ showRoutingList ? '一覧を隠す' : '一覧を表示' }}
          </button>
        </h2>

        <div v-if="!selectedRouting" class="empty-state">
          左の一覧からルーティングを選択してください
        </div>

        <div v-else>
          <div class="routing-header-form">
            <div class="routing-header-grid">
              <label class="routing-header-field routing-header-field--check">
                <span>既定</span>
                <input v-model="routingHeaderDraft.is_default" type="checkbox" :disabled="!canEdit || savingRoutingHeader" />
              </label>
              <label class="routing-header-field routing-header-field--check">
                <span>有効</span>
                <input v-model="routingHeaderDraft.is_active" type="checkbox" :disabled="!canEdit || savingRoutingHeader" />
              </label>
              <label class="routing-header-field">
                <span>有効開始日時</span>
                <input
                  v-model="routingHeaderDraft.valid_from_datetime"
                  type="datetime-local"
                  :disabled="!canEdit || savingRoutingHeader"
                />
              </label>
              <label class="routing-header-field">
                <span>有効終了日時</span>
                <input
                  v-model="routingHeaderDraft.valid_to_datetime"
                  type="datetime-local"
                  :disabled="!canEdit || savingRoutingHeader"
                />
              </label>
            </div>
            <div class="routing-header-actions">
              <button
                class="btn-primary"
                @click="saveRoutingHeader"
                :disabled="!canEdit || !selectedRouting || !isRoutingHeaderDirty || savingRoutingHeader"
              >
                {{ savingRoutingHeader ? '保存中...' : 'ヘッダ保存' }}
              </button>
            </div>
          </div>
          <div v-if="canEdit && showCreateStepRow" class="create-step-row">
            <div class="create-step-field">
              <label class="create-step-label">工程番号</label>
              <input v-model.number="newStepDraft.step_no" type="number" min="1" step="1" class="duration-input" :disabled="creatingStep" />
            </div>
            <div class="create-step-field">
              <label class="create-step-label">階層</label>
              <input v-model.trim="newStepDraft.hierarchy_path" type="text" class="hierarchy-input" placeholder="必須" :disabled="creatingStep" />
            </div>
            <div class="create-step-field">
              <label class="create-step-label">並列G</label>
              <input v-model.number="newStepDraft.parallel_group" type="number" min="1" step="1" class="duration-input" :disabled="creatingStep" />
            </div>
            <div class="create-step-field" style="position:relative;">
              <label class="create-step-label">加工後品目</label>
              <input
                v-model="outputProductSearch"
                type="text"
                class="step-select"
                placeholder="品番/品名で検索"
                :disabled="creatingStep || loadingProducts"
                @focus="outputProductDropOpen = true"
                @input="outputProductDropOpen = true; newStepDraft.output_product = ''"
                @blur="outputProductDropOpen = false"
              />
              <ul v-if="outputProductDropOpen && filteredOutputProducts.length" class="autocomplete-list">
                <li
                  v-for="product in filteredOutputProducts"
                  :key="product.id"
                  @mousedown.prevent="selectOutputProduct(product)"
                  class="autocomplete-item"
                >
                  {{ product.product_code }} - {{ product.product_name }}
                </li>
              </ul>
            </div>
            <div class="create-step-field" style="position:relative;">
              <label class="create-step-label">親製品</label>
              <input
                v-model="remarkProductSearch"
                type="text"
                class="create-input"
                placeholder="品番で検索"
                :disabled="creatingStep || loadingProducts"
                @focus="remarkProductDropOpen = true"
                @input="remarkProductDropOpen = true"
                @blur="remarkProductDropOpen = false"
              />
              <ul v-if="remarkProductDropOpen && filteredRemarkProducts.length" class="autocomplete-list">
                <li
                  v-for="product in filteredRemarkProducts"
                  :key="product.id"
                  @mousedown.prevent="selectRemarkProduct(product)"
                  class="autocomplete-item"
                >
                  {{ product.product_code }} - {{ product.product_name }}
                </li>
              </ul>
            </div>
            <div class="create-step-field">
              <label class="create-step-label">使用個数</label>
              <input v-model.number="newStepDraft.usage_quantity" type="number" min="0" step="1" class="duration-input" :disabled="creatingStep" />
            </div>
            <div class="create-step-field">
              <label class="create-step-label">調達区分</label>
              <select v-model="newStepDraft.sourcing_type" class="step-select step-select--small" :disabled="creatingStep">
                <option value="MAKE">自社製造</option>
                <option value="BUY">購買</option>
                <option value="SUBCON">外作</option>
              </select>
            </div>
            <div class="create-step-field">
              <label class="create-step-label">外作先{{ newStepDraft.sourcing_type !== 'MAKE' ? ' *' : '' }}</label>
              <select v-model="newStepDraft.supplier" class="step-select"
                :disabled="creatingStep || loadingSuppliers || newStepDraft.sourcing_type === 'MAKE'">
                <option value="">未設定</option>
                <option v-for="supplier in supplierOptions" :key="supplier.id" :value="supplier.id">
                  {{ supplier.supplier_code }} - {{ supplier.supplier_name }}
                </option>
              </select>
            </div>
            <div class="create-step-field">
              <label class="create-step-label">工程{{ newStepDraft.sourcing_type === 'MAKE' ? ' *' : '' }}</label>
              <select v-model="newStepDraft.process" class="step-select"
                :disabled="creatingStep || loadingProcesses || newStepDraft.sourcing_type === 'BUY' || newStepDraft.sourcing_type === 'SUBCON'">
                <option value="">{{ loadingProcesses ? '読込中...' : '選択' }}</option>
                <option v-for="proc in processOptions" :key="proc.id" :value="proc.id">
                  {{ proc.process_code }} - {{ proc.process_name }}
                </option>
              </select>
            </div>
            <div class="create-step-field">
              <label class="create-step-label">ライン{{ newStepDraft.sourcing_type === 'MAKE' ? ' *' : '' }}</label>
              <select v-model="newStepDraft.line" class="step-select"
                :disabled="creatingStep || loadingLines || newStepDraft.sourcing_type === 'BUY' || newStepDraft.sourcing_type === 'SUBCON'">
                <option value="">未設定</option>
                <option v-for="line in lines" :key="line.id" :value="line.id">
                  {{ line.line_code }} - {{ line.line_name }}
                </option>
              </select>
            </div>
            <div class="create-step-field">
              <label class="create-step-label">時間単位{{ newStepDraft.sourcing_type === 'MAKE' ? ' *' : '' }}</label>
              <select v-model="newStepDraft.time_unit" class="step-select step-select--small"
                :disabled="creatingStep || newStepDraft.sourcing_type === 'BUY'">
                <option value="DAY">日</option>
                <option value="MINUTE">分</option>
              </select>
            </div>
            <div class="create-step-field">
              <label class="create-step-label">LT(日){{ newStepDraft.sourcing_type !== 'MAKE' ? ' *' : '' }}</label>
              <input
                v-model.number="newStepDraft.lead_time_days"
                type="number" min="0" step="1" class="duration-input" :disabled="creatingStep"
              />
            </div>
            <div class="create-step-field">
              <label class="create-step-label">所要時間(分){{ newStepDraft.time_unit === 'MINUTE' && newStepDraft.sourcing_type !== 'BUY' ? ' *' : '' }}</label>
              <input
                v-model.number="newStepDraft.duration_min"
                type="number" min="1" step="1" class="duration-input"
                :disabled="creatingStep || newStepDraft.time_unit === 'DAY' || newStepDraft.sourcing_type === 'BUY'"
              />
            </div>
            <div class="create-step-field" style="align-self:flex-end;">
              <button class="btn-primary" :disabled="isCreateStepDisabled" @click="createStep">
                {{ creatingStep ? '追加中...' : '工程追加保存' }}
              </button>
            </div>
            <div v-if="isSameParentChild" class="create-step-warning">
              親製品と加工後品目が同じです（中間工程）。BOM明細は作成されません。
            </div>
            <div v-if="autoFillProcessWarning" class="create-step-warning" style="color:#dc2626;">
              {{ autoFillProcessWarning }}
            </div>
          </div>
          <div class="step-filter-row">
            <label>工程</label>
            <select v-model="processFilter">
              <option value="">すべて</option>
              <option v-for="proc in processFilterOptions" :key="proc.value" :value="proc.value">
                {{ proc.label }}
              </option>
            </select>
            <button v-if="canEdit" class="btn-success btn-small" @click="toggleCreateStepRow" :disabled="creatingStep">
              {{ showCreateStepRow ? '工程追加を閉じる' : '工程追加' }}
            </button>
          </div>
          <div class="table-wrap">
            <table class="data-table compact">
              <thead>
                <tr>
                  <th>階層</th>
                  <th>工程番号</th>
                  <th>並列G</th>
                  <th>工程</th>
                  <th>ライン</th>
                  <th>外作先</th>
                  <th>加工後品目</th>
                  <th>代表部品</th>
                  <th>時間単位</th>
                  <th>LT(日)</th>
                  <th>所要時間(分)</th>
                  <th>使用個数</th>
                  <th>親製品</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="step in filteredSteps" :key="step.id">
                  <td>
                    <div class="duration-editor">
                      <input
                        v-model.trim="hierarchyPathDraftByStepId[step.id]"
                        type="text"
                        class="hierarchy-input"
                        placeholder="必須"
                        :disabled="!canEdit || savingHierarchyPathStepId === step.id"
                        @keydown.enter.prevent="saveHierarchyPath(step)"
                      />
                      <button
                        class="duration-save-btn"
                        :class="{ 'duration-save-btn--active': isHierarchyPathDirty(step) }"
                        :disabled="!canEdit || !isHierarchyPathDirty(step) || savingHierarchyPathStepId === step.id"
                        @click="saveHierarchyPath(step)"
                      >
                        {{ savingHierarchyPathStepId === step.id ? '保存中' : '保存' }}
                      </button>
                    </div>
                  </td>
                  <td>{{ step.step_no }}</td>
                  <td>{{ step.parallel_group }}</td>
                  <td>{{ step.process_name || step.process || '-' }}</td>
                  <td>{{ step.line_name || step.line || '-' }}</td>
                  <td>{{ step.supplier_name || '-' }}</td>
                  <td>
                    <div class="duration-editor">
                      <input
                        v-model.trim="outputProductDraftByStepId[step.id]"
                        type="text"
                        class="step-code-input"
                        placeholder="品番コード"
                        :disabled="!canEdit || savingOutputProductStepId === step.id"
                        @keydown.enter.prevent="saveOutputProduct(step)"
                      />
                      <button
                        class="duration-save-btn"
                        :class="{ 'duration-save-btn--active': isOutputProductDirty(step) }"
                        :disabled="!canEdit || !isOutputProductDirty(step) || savingOutputProductStepId === step.id"
                        @click="saveOutputProduct(step)"
                      >
                        {{ savingOutputProductStepId === step.id ? '保存中' : '保存' }}
                      </button>
                    </div>
                  </td>
                  <td>{{ isRepresentativePart(step) ? '○' : '' }}</td>
                  <td>{{ displayTimeUnit(step.time_unit) }}</td>
                  <td>
                    <div class="duration-editor">
                      <input
                        v-model.number="leadTimeDraftByStepId[step.id]"
                        type="number"
                        min="0"
                        step="1"
                        class="duration-input"
                        :disabled="!canEdit || savingLeadTimeStepId === step.id"
                        @keydown.enter.prevent="saveLeadTime(step)"
                      />
                      <button
                        class="duration-save-btn"
                        :class="{ 'duration-save-btn--active': isLeadTimeDirty(step) }"
                        :disabled="!canEdit || !isLeadTimeDirty(step) || savingLeadTimeStepId === step.id"
                        @click="saveLeadTime(step)"
                      >
                        {{ savingLeadTimeStepId === step.id ? '保存中' : '保存' }}
                      </button>
                    </div>
                  </td>
                  <td>
                    <div class="duration-editor">
                      <template v-if="isMinuteStep(step)">
                        <input
                          v-model.number="durationDraftByStepId[step.id]"
                          type="number"
                          min="1"
                          step="1"
                          class="duration-input"
                          :disabled="!canEdit || savingDurationStepId === step.id"
                          @keydown.enter.prevent="saveDuration(step)"
                        />
                        <button
                          class="duration-save-btn"
                          :class="{ 'duration-save-btn--active': isDurationDirty(step) }"
                          :disabled="!canEdit || !isDurationDirty(step) || savingDurationStepId === step.id"
                          @click="saveDuration(step)"
                        >
                          {{ savingDurationStepId === step.id ? '保存中' : '保存' }}
                        </button>
                      </template>
                      <span v-else>{{ step.duration_min ?? '' }}</span>
                    </div>
                  </td>
                  <td>
                    <div class="duration-editor">
                      <input
                        v-model.number="usageQuantityDraftByStepId[step.id]"
                        type="number"
                        min="0"
                        step="1"
                        class="duration-input"
                        :disabled="!canEdit || savingUsageQuantityStepId === step.id"
                        @keydown.enter.prevent="saveUsageQuantity(step)"
                      />
                      <button
                        class="duration-save-btn"
                        :class="{ 'duration-save-btn--active': isUsageQuantityDirty(step) }"
                        :disabled="!canEdit || !isUsageQuantityDirty(step) || savingUsageQuantityStepId === step.id"
                        @click="saveUsageQuantity(step)"
                      >
                        {{ savingUsageQuantityStepId === step.id ? '保存中' : '保存' }}
                      </button>
                    </div>
                  </td>
                  <td>
                    <div class="duration-editor">
                      <input
                        v-model.trim="parentProductDraftByStepId[step.id]"
                        type="text"
                        class="step-code-input"
                        placeholder="親製品コード"
                        :disabled="!canEdit || savingParentProductStepId === step.id"
                        @keydown.enter.prevent="saveParentProduct(step)"
                      />
                      <button
                        class="duration-save-btn"
                        :class="{ 'duration-save-btn--active': isParentProductDirty(step) }"
                        :disabled="!canEdit || !isParentProductDirty(step) || savingParentProductStepId === step.id"
                        @click="saveParentProduct(step)"
                      >
                        {{ savingParentProductStepId === step.id ? '保存中' : '保存' }}
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-if="!loadingSteps && filteredSteps.length === 0" class="empty-state">
              工程がありません
            </div>
          </div>
        </div>
      </section>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <!-- ルーティング変更在庫移行ダイアログ -->
    <div v-if="migrationDialogVisible" class="migration-overlay">
      <div class="migration-dialog">
        <h3 class="migration-title">⚠ ルーティング変更による在庫移行の確認</h3>
        <p class="migration-desc">
          以下の品番でルーティング変更が検出されました。<br>
          旧ラインの在庫を新ラインへ移行しますか？
        </p>
        <div class="migration-date-row">
          <label>移行基準日</label>
          <input type="date" v-model="migrationDate" class="migration-date-input" />
        </div>
        <table class="migration-table">
          <thead>
            <tr>
              <th>移行</th>
              <th>品番</th>
              <th>品名</th>
              <th>旧ライン / 旧工程</th>
              <th>新ライン / 新工程</th>
              <th>現在在庫</th>
              <th>移行数量</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in migrationCandidates" :key="item.product_id">
              <td><input type="checkbox" v-model="item.checked" /></td>
              <td>{{ item.product_code }}</td>
              <td>{{ item.product_name }}</td>
              <td>{{ item.old_line_code }} / {{ item.old_process_code }}</td>
              <td>{{ item.new_line_code }} / {{ item.new_process_code }}</td>
              <td class="qty-cell">{{ item.stock_qty }}</td>
              <td>
                <input
                  v-if="item.checked"
                  type="number"
                  v-model.number="item.migrate_qty"
                  :max="item.stock_qty >= 0 ? item.stock_qty : 0"
                  :min="item.stock_qty < 0 ? item.stock_qty : 0"
                  class="migrate-qty-input"
                />
                <span v-else>-</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p class="migration-note">
          ※ 実績(actual_qty)は旧ラインに残ります<br>
          ※ 移行はadjust_qtyへの加減算で行われます（在庫再計算後に反映）<br>
          <span class="migration-warning">※ 移行実行後、在庫/残量一覧画面で「過去から再計算」を必ず実行してください</span>
        </p>
        <div class="migration-actions">
          <button class="btn-secondary" @click="migrationDialogVisible = false">キャンセル</button>
          <button
            class="btn-primary"
            @click="executeMigration"
            :disabled="executingMigration"
          >{{ executingMigration ? '移行中...' : '移行実行' }}</button>
        </div>
      </div>
    </div>

    <!-- 孤立在庫なし通知 -->
    <div v-if="noMigrationMessage" class="migration-overlay" @click="noMigrationMessage = false">
      <div class="migration-dialog migration-dialog--small">
        <h3 class="migration-title" style="color: #15803d">✓ 移行対象なし</h3>
        <p class="migration-desc">ルーティング変更による孤立在庫は見つかりませんでした。</p>
        <div class="migration-actions">
          <button class="btn-primary" @click="noMigrationMessage = false">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'm_routing', desc: 'ルーティングヘッダ' },
  { op: '読み書き', table: 'm_routing_step', desc: 'ルーティングステップ' },
  { op: '読み取り', table: 'm_product', desc: '製品（選択肢）' },
  { op: '読み取り', table: 'm_process', desc: '工程（選択肢）' },
  { op: '読み取り', table: 'm_line', desc: 'ライン（選択肢）' },
  { op: '読み取り', table: 'm_supplier', desc: '仕入先（選択肢）' },
  { op: '読み取り', table: 'm_customer', desc: '得意先（フィルタ）' },
]

const routings = ref([])
const selectedRoutingId = ref(null)
const steps = ref([])
const materialsByStepId = ref({})
const bomQuantityByChildId = ref({})
const searchText = ref('')
const onlyActive = ref(true)
const loadingRoutings = ref(false)
const loadingSteps = ref(false)
const errorMessage = ref('')
const stepLoadToken = ref(0)
const durationDraftByStepId = ref({})
const savingDurationStepId = ref(null)
const leadTimeDraftByStepId = ref({})
const savingLeadTimeStepId = ref(null)
const usageQuantityDraftByStepId = ref({})
const savingUsageQuantityStepId = ref(null)
const outputProductDraftByStepId = ref({})
const savingOutputProductStepId = ref(null)
const parentProductDraftByStepId = ref({})
const savingParentProductStepId = ref(null)
const hierarchyPathDraftByStepId = ref({})
const savingHierarchyPathStepId = ref(null)
const routingHeaderDraft = ref({
  is_default: false,
  is_active: true,
  valid_from_datetime: '',
  valid_to_datetime: '',
})
const savingRoutingHeader = ref(false)
const processFilter = ref('')
const representativeChildProductIds = ref(new Set())
const products = ref([])
const loadingProducts = ref(false)
const processes = ref([])
const suppliers = ref([])
const customers = ref([])
const loadingProcesses = ref(false)
const loadingSuppliers = ref(false)
const loadingCustomers = ref(false)
const filterFinalLineId = ref('')
const filterProductName = ref('')
const filterCustomerCode = ref('')
const loadingRoutingFinalLineMap = ref(false)
const routingFinalLineIdByRoutingId = ref({})
const routingFinalLineMapLoaded = ref(false)
const loadingCustomerProductSet = ref(false)
const customerProductCodeSet = ref(new Set())
const coproductDriverChildProductIds = ref(new Set())
const showCreateRow = ref(false)
const creatingRouting = ref(false)
const newRoutingDraft = ref({
  product: '',
  routing_code: '',
  description: '',
  is_default: false,
  is_active: true,
})
const newRoutingProductSearch = ref('')
const newRoutingProductDropOpen = ref(false)
const filteredNewRoutingProducts = computed(() => {
  const kw = (newRoutingProductSearch.value || '').trim().toLowerCase()
  if (!kw) return sortedProducts.value.slice(0, 30)
  return sortedProducts.value.filter((p) => {
    const code = (p.product_code || '').toLowerCase()
    const name = (p.product_name || '').toLowerCase()
    return code.includes(kw) || name.includes(kw)
  }).slice(0, 30)
})
const selectNewRoutingProduct = (product) => {
  newRoutingDraft.value.product = product.id
  newRoutingProductSearch.value = `${product.product_code} - ${product.product_name}`
  newRoutingProductDropOpen.value = false
}
const showCreateStepRow = ref(false)
const showRoutingList = ref(true)
const creatingStep = ref(false)
const newStepDraft = ref({
  step_no: '',
  hierarchy_path: '',
  parallel_group: 1,
  process: '',
  line: '',
  supplier: '',
  sourcing_type: 'MAKE',
  output_product: '',
  time_unit: 'DAY',
  lead_time_days: 0,
  duration_min: '',
  usage_quantity: '',
  remark: '',
})

const outputProductSearch = ref('')
const outputProductDropOpen = ref(false)
const filteredOutputProducts = computed(() => {
  const kw = (outputProductSearch.value || '').trim().toLowerCase()
  if (!kw) return sortedProducts.value.slice(0, 30)
  return sortedProducts.value.filter((p) => {
    const code = (p.product_code || '').toLowerCase()
    const name = (p.product_name || '').toLowerCase()
    return code.includes(kw) || name.includes(kw)
  }).slice(0, 30)
})
const selectOutputProduct = (product) => {
  newStepDraft.value.output_product = product.id
  outputProductSearch.value = `${product.product_code} - ${product.product_name}`
  outputProductDropOpen.value = false
}

const remarkProductSearch = ref('')
const remarkProductDropOpen = ref(false)
const filteredRemarkProducts = computed(() => {
  const kw = (remarkProductSearch.value || '').trim().toLowerCase()
  if (!kw) return sortedProducts.value.slice(0, 30)
  return sortedProducts.value.filter((p) => {
    const code = (p.product_code || '').toLowerCase()
    const name = (p.product_name || '').toLowerCase()
    return code.includes(kw) || name.includes(kw)
  }).slice(0, 30)
})
const selectRemarkProduct = (product) => {
  newStepDraft.value.remark = product.product_code
  remarkProductSearch.value = `${product.product_code} - ${product.product_name}`
  remarkProductDropOpen.value = false
}

const isSameParentChild = computed(() => {
  const outputId = newStepDraft.value.output_product
  const remarkCode = String(newStepDraft.value.remark || '').trim()
  if (!outputId || !remarkCode) return false
  const p = sortedProducts.value.find(item => item.id === Number(outputId))
  return p && p.product_code === remarkCode
})

// 在庫移行機能
const lines = ref([])
const loadingLines = ref(false)
const migrationLineId = ref('')
const _nowJst = new Date(Date.now() + 9 * 60 * 60 * 1000)
const migrationDate = ref(formatISODate(_nowJst))
const migrationDialogVisible = ref(false)
const migrationCandidates = ref([])
const checkingMigration = ref(false)
const executingMigration = ref(false)
const noMigrationMessage = ref(false)

const normalizeList = (payload) => payload?.results || payload || []

const toPathNumbers = (path) => {
  if (!path) return []
  return String(path)
    .split('.')
    .map((part) => Number(part))
    .filter((num) => Number.isFinite(num))
}

const compareSteps = (a, b) => {
  const left = toPathNumbers(a.hierarchy_path)
  const right = toPathNumbers(b.hierarchy_path)
  const maxLen = Math.max(left.length, right.length)
  for (let i = 0; i < maxLen; i += 1) {
    const lv = left[i] ?? -1
    const rv = right[i] ?? -1
    if (lv !== rv) return lv - rv
  }
  if ((a.step_no ?? 0) !== (b.step_no ?? 0)) return (a.step_no ?? 0) - (b.step_no ?? 0)
  return (a.parallel_group ?? 0) - (b.parallel_group ?? 0)
}

const productCode = (routing) => routing?.product_code || ''
const productName = (routing) => routing?.product_name || ''
const productSearchLabel = (product) => {
  if (!product) return ''
  const code = String(product.product_code || '').trim()
  const name = String(product.product_name || '').trim()
  if (code && name) return `${code} - ${name}`
  return code || name
}
const extractProductCode = (value) => String(value || '').trim().split(' - ')[0].trim()
const findProductByInput = (value) => {
  const raw = String(value || '').trim()
  if (!raw) return null
  const code = extractProductCode(raw).toLowerCase()
  if (!code) return null
  return sortedProducts.value.find((product) => String(product.product_code || '').trim().toLowerCase() === code) || null
}

const selectedRouting = computed(() => routings.value.find((r) => r.id === selectedRoutingId.value) || null)
const pad2 = (value) => String(value).padStart(2, '0')
const formatDatetimeLocal = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16)
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
const resetRoutingHeaderDraft = (routing) => {
  routingHeaderDraft.value = {
    is_default: Boolean(routing?.is_default),
    is_active: routing?.is_active !== false,
    valid_from_datetime: formatDatetimeLocal(routing?.valid_from_datetime),
    valid_to_datetime: formatDatetimeLocal(routing?.valid_to_datetime),
  }
}
const canEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === 'masters.routing')) {
    return hasPermission(user, 'masters.routing', 'edit')
  }
  return hasPermission(user, 'masters', 'edit')
})
const isRoutingHeaderDirty = computed(() => {
  const routing = selectedRouting.value
  if (!routing) return false
  return (
    Boolean(routingHeaderDraft.value.is_default) !== Boolean(routing.is_default) ||
    Boolean(routingHeaderDraft.value.is_active) !== Boolean(routing.is_active) ||
    normalizeDatetimeLocal(routingHeaderDraft.value.valid_from_datetime) !== normalizeDatetimeLocal(formatDatetimeLocal(routing.valid_from_datetime)) ||
    normalizeDatetimeLocal(routingHeaderDraft.value.valid_to_datetime) !== normalizeDatetimeLocal(formatDatetimeLocal(routing.valid_to_datetime))
  )
})

const filteredRoutings = computed(() => {
  const q = searchText.value.toLowerCase()
  const productNameQ = filterProductName.value.toLowerCase()
  const selectedFinalLineId = String(filterFinalLineId.value || '')
  const selectedCustomerCode = String(filterCustomerCode.value || '')
  return routings.value.filter((routing) => {
    if (onlyActive.value && !routing.is_active) return false
    if (selectedFinalLineId) {
      const finalLineId = String(routingFinalLineIdByRoutingId.value[routing.id] || '')
      if (finalLineId !== selectedFinalLineId) return false
    }
    if (productNameQ) {
      const pname = String(productName(routing) || '').toLowerCase()
      if (!pname.includes(productNameQ)) return false
    }
    if (selectedCustomerCode && !customerProductCodeSet.value.has(String(productCode(routing) || ''))) return false
    if (!q) return true
    const code = String(productCode(routing) || '').toLowerCase()
    return code.includes(q)
  })
})
const sortedProducts = computed(() => {
  return [...products.value].sort((a, b) => {
    const left = `${a?.product_code || ''} ${a?.product_name || ''}`
    const right = `${b?.product_code || ''} ${b?.product_name || ''}`
    return left.localeCompare(right, 'ja')
  })
})
const isCreateDisabled = computed(() => {
  if (!canEdit.value) return true
  if (creatingRouting.value || loadingProducts.value) return true
  if (!newRoutingDraft.value.product) return true
  if (!String(newRoutingDraft.value.routing_code || '').trim()) return true
  return false
})
const processOptions = computed(() => {
  return [...processes.value].sort((a, b) => {
    const left = `${a?.process_code || ''} ${a?.process_name || ''}`
    const right = `${b?.process_code || ''} ${b?.process_name || ''}`
    return left.localeCompare(right, 'ja')
  })
})
const supplierOptions = computed(() => {
  return [...suppliers.value].sort((a, b) => {
    const left = `${a?.supplier_code || ''} ${a?.supplier_name || ''}`
    const right = `${b?.supplier_code || ''} ${b?.supplier_name || ''}`
    return left.localeCompare(right, 'ja')
  })
})
const customerOptions = computed(() => {
  return [...customers.value]
    .filter((c) => c?.is_active !== false)
    .sort((a, b) => {
      const left = `${a?.customer_code || ''} ${a?.customer_name || ''}`
      const right = `${b?.customer_code || ''} ${b?.customer_name || ''}`
      return left.localeCompare(right, 'ja')
    })
})
const isCreateStepDisabled = computed(() => {
  if (!canEdit.value) return true
  if (!selectedRoutingId.value || creatingStep.value) return true
  if (!newStepDraft.value.process && newStepDraft.value.sourcing_type !== 'BUY') return true
  if (!String(newStepDraft.value.hierarchy_path || '').trim()) return true
  if (!newStepDraft.value.output_product) return true
  if (!String(newStepDraft.value.remark || '').trim()) return true
  const stepNo = Number(newStepDraft.value.step_no)
  const parallelGroup = Number(newStepDraft.value.parallel_group)
  if (!Number.isInteger(stepNo) || stepNo <= 0) return true
  if (!Number.isInteger(parallelGroup) || parallelGroup <= 0) return true
  if (newStepDraft.value.time_unit === 'MINUTE') {
    const durationMin = Number(newStepDraft.value.duration_min)
    return !Number.isInteger(durationMin) || durationMin <= 0
  }
  const leadTimeDays = Number(newStepDraft.value.lead_time_days)
  return !Number.isInteger(leadTimeDays) || leadTimeDays < 0
})

const sortedSteps = computed(() => {
  return [...steps.value].sort((a, b) => {
    const stepDiff = Number(a.step_no ?? 0) - Number(b.step_no ?? 0)
    if (stepDiff !== 0) return stepDiff
    const groupDiff = Number(a.parallel_group ?? 0) - Number(b.parallel_group ?? 0)
    if (groupDiff !== 0) return groupDiff
    return Number(a.id ?? 0) - Number(b.id ?? 0)
  })
})

const processFilterOptions = computed(() => {
  const map = new Map()
  sortedSteps.value.forEach((step) => {
    if (!step?.process) return
    if (!map.has(String(step.process))) {
      map.set(String(step.process), step.process_name || String(step.process))
    }
  })
  return Array.from(map.entries())
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label, 'ja'))
})

const filteredSteps = computed(() => {
  if (!processFilter.value) return sortedSteps.value
  return sortedSteps.value.filter((step) => String(step.process) === String(processFilter.value))
})

const displayTimeUnit = (timeUnit) => {
  if (timeUnit === 'MINUTE') return '分'
  if (timeUnit === 'DAY') return '日'
  return timeUnit || ''
}

const formatQuantity = (value) => {
  if (value === null || value === undefined || value === '') return ''
  const num = Number(value)
  if (!Number.isFinite(num)) return String(value)
  return Number.isInteger(num) ? String(num) : String(num)
}

const usageQuantity = (step) => {
  if (!step?.output_product) return ''
  if (step.usage_quantity !== undefined && step.usage_quantity !== null && step.usage_quantity !== '') {
    return formatQuantity(step.usage_quantity)
  }

  if (step.hierarchy_path && step.hierarchy_path.includes('.')) {
    const parentPath = step.hierarchy_path.split('.').slice(0, -1).join('.')
    const parentStep = steps.value.find((item) => item.hierarchy_path === parentPath)
    if (parentStep) {
      const parentMaterials = materialsByStepId.value[parentStep.id] || []
      const material = parentMaterials.find((item) => item.component === step.output_product)
      if (material) return formatQuantity(material.quantity)
    }
  }

  if (step.remark) {
    const fallbackParent = steps.value.find((item) => item.output_product_code === step.remark)
    if (fallbackParent) {
      const parentMaterials = materialsByStepId.value[fallbackParent.id] || []
      const material = parentMaterials.find((item) => item.component === step.output_product)
      if (material) return formatQuantity(material.quantity)
    }
  }

  return formatQuantity(bomQuantityByChildId.value[step.output_product])
}

const isRepresentativePart = (step) => {
  if (!step?.output_product) return false
  return representativeChildProductIds.value.has(Number(step.output_product))
}

const fetchCoproductDriverChildProductIds = async () => {
  try {
    const res = await api.routings.getCoproductDriverChildProducts()
    const ids = Array.isArray(res?.data?.child_product_ids) ? res.data.child_product_ids : []
    coproductDriverChildProductIds.value = new Set(
      ids.map((id) => Number(id)).filter((id) => Number.isFinite(id) && id > 0)
    )
  } catch (e) {
    console.warn('連産品driver品番取得エラー:', e)
    coproductDriverChildProductIds.value = new Set()
  }
}

const resetDurationDrafts = (stepList) => {
  const draftMap = {}
  stepList.forEach((step) => {
    draftMap[step.id] = step.duration_min ?? ''
  })
  durationDraftByStepId.value = draftMap
}

const resetLeadTimeDrafts = (stepList) => {
  const draftMap = {}
  stepList.forEach((step) => {
    draftMap[step.id] = step.lead_time_days ?? 0
  })
  leadTimeDraftByStepId.value = draftMap
}

const resetUsageQuantityDrafts = (stepList) => {
  const draftMap = {}
  stepList.forEach((step) => {
    draftMap[step.id] = usageQuantity(step)
  })
  usageQuantityDraftByStepId.value = draftMap
}

const resetOutputProductDrafts = (stepList) => {
  const draftMap = {}
  stepList.forEach((step) => {
    draftMap[step.id] = step.output_product_code || ''
  })
  outputProductDraftByStepId.value = draftMap
}

const resetParentProductDrafts = (stepList) => {
  const draftMap = {}
  stepList.forEach((step) => {
    draftMap[step.id] = step.remark || ''
  })
  parentProductDraftByStepId.value = draftMap
}

const resetHierarchyPathDrafts = (stepList) => {
  const draftMap = {}
  stepList.forEach((step) => {
    draftMap[step.id] = step.hierarchy_path || ''
  })
  hierarchyPathDraftByStepId.value = draftMap
}

const isMinuteStep = (step) => step?.time_unit === 'MINUTE'

const parseDuration = (value) => {
  if (value === '' || value === null || value === undefined) return null
  const num = Number(value)
  if (!Number.isFinite(num) || !Number.isInteger(num)) return null
  if (num <= 0) return null
  return num
}

const parseLeadTime = (value) => {
  if (value === '' || value === null || value === undefined) return null
  const num = Number(value)
  if (!Number.isFinite(num) || !Number.isInteger(num)) return null
  if (num < 0) return null
  return num
}

const isLeadTimeDirty = (step) => {
  const draft = leadTimeDraftByStepId.value[step.id]
  const current = step.lead_time_days
  if (draft === '' || draft === null || draft === undefined) {
    return !(current === '' || current === null || current === undefined)
  }
  return String(draft) !== String(current ?? '')
}

const isDurationDirty = (step) => {
  const draft = durationDraftByStepId.value[step.id]
  const current = step.duration_min
  if (draft === '' || draft === null || draft === undefined) {
    return !(current === '' || current === null || current === undefined)
  }
  return String(draft) !== String(current ?? '')
}

const parseUsageQuantity = (value) => {
  if (value === '' || value === null || value === undefined) return null
  const num = Number(value)
  if (!Number.isFinite(num) || !Number.isInteger(num)) return null
  if (num < 0) return null
  return num
}

const isUsageQuantityDirty = (step) => {
  const draft = usageQuantityDraftByStepId.value[step.id]
  const current = step.usage_quantity
  if (draft === '' || draft === null || draft === undefined) {
    return !(current === '' || current === null || current === undefined)
  }
  return String(draft) !== String(current ?? '')
}

const isOutputProductDirty = (step) => {
  const draftProduct = findProductByInput(outputProductDraftByStepId.value[step.id])
  const draftCode = draftProduct?.product_code || extractProductCode(outputProductDraftByStepId.value[step.id])
  const currentCode = String(step?.output_product_code || '').trim()
  return String(draftCode || '') !== currentCode
}

const isHierarchyPathDirty = (step) => {
  const draft = String(hierarchyPathDraftByStepId.value[step.id] || '').trim()
  const current = String(step?.hierarchy_path || '').trim()
  return draft !== current
}

const isParentProductDirty = (step) => {
  const draftProduct = findProductByInput(parentProductDraftByStepId.value[step.id])
  const draftCode = draftProduct?.product_code || extractProductCode(parentProductDraftByStepId.value[step.id])
  const currentCode = String(step?.remark || '').trim()
  return String(draftCode || '') !== currentCode
}

const saveLeadTime = async (step) => {
  if (!canEdit.value || !step?.id) return
  if (!isLeadTimeDirty(step)) return

  const leadTime = parseLeadTime(leadTimeDraftByStepId.value[step.id])
  if (leadTime === null) {
    alert('LT(日)は0以上の整数で入力してください。')
    return
  }

  savingLeadTimeStepId.value = step.id
  errorMessage.value = ''
  try {
    await api.routings.patchRoutingStep(step.id, { lead_time_days: leadTime })
    step.lead_time_days = leadTime
    leadTimeDraftByStepId.value[step.id] = leadTime
  } catch (error) {
    console.error('LT更新エラー:', error)
    const detail = error?.response?.data?.detail || 'LT(日)の更新に失敗しました'
    alert(detail)
  } finally {
    if (savingLeadTimeStepId.value === step.id) {
      savingLeadTimeStepId.value = null
    }
  }
}

const saveDuration = async (step) => {
  if (!canEdit.value || !isMinuteStep(step) || !step?.id) return
  if (!isDurationDirty(step)) return

  const duration = parseDuration(durationDraftByStepId.value[step.id])
  if (duration === null) {
    alert('所要時間(分)は1以上の整数で入力してください。')
    return
  }

  savingDurationStepId.value = step.id
  errorMessage.value = ''
  try {
    await api.routings.patchRoutingStep(step.id, { duration_min: duration })
    step.duration_min = duration
    durationDraftByStepId.value[step.id] = duration
  } catch (error) {
    console.error('所要時間更新エラー:', error)
    const detail = error?.response?.data?.detail || '所要時間の更新に失敗しました'
    alert(detail)
  } finally {
    if (savingDurationStepId.value === step.id) {
      savingDurationStepId.value = null
    }
  }
}

const saveUsageQuantity = async (step) => {
  if (!canEdit.value || !step?.id) return
  if (!isUsageQuantityDirty(step)) return

  const usageQuantity = parseUsageQuantity(usageQuantityDraftByStepId.value[step.id])
  if (usageQuantity === null) {
    alert('使用個数は0以上の整数で入力してください。')
    return
  }

  savingUsageQuantityStepId.value = step.id
  errorMessage.value = ''
  try {
    await api.routings.patchRoutingStep(step.id, { usage_quantity: usageQuantity })
    step.usage_quantity = usageQuantity
    usageQuantityDraftByStepId.value[step.id] = usageQuantity
  } catch (error) {
    console.error('使用個数更新エラー:', error)
    const detail = error?.response?.data?.detail || '使用個数の更新に失敗しました'
    alert(detail)
  } finally {
    if (savingUsageQuantityStepId.value === step.id) {
      savingUsageQuantityStepId.value = null
    }
  }
}

const saveOutputProduct = async (step) => {
  if (!canEdit.value || !step?.id) return
  if (!isOutputProductDirty(step)) return

  const product = findProductByInput(outputProductDraftByStepId.value[step.id])
  if (!product) {
    alert('加工後品目は既存の品番コードで入力してください。')
    return
  }

  savingOutputProductStepId.value = step.id
  errorMessage.value = ''
  try {
    await api.routings.patchRoutingStep(step.id, { output_product: Number(product.id) })
    await fetchStepsAndMaterials(selectedRoutingId.value)
  } catch (error) {
    console.error('加工後品目更新エラー:', error)
    const detail = error?.response?.data?.detail || error?.response?.data?.non_field_errors?.[0] || '加工後品目の更新に失敗しました'
    alert(detail)
  } finally {
    if (savingOutputProductStepId.value === step.id) {
      savingOutputProductStepId.value = null
    }
  }
}

const saveHierarchyPath = async (step) => {
  if (!canEdit.value || !step?.id) return
  if (!isHierarchyPathDirty(step)) return
  const newPath = String(hierarchyPathDraftByStepId.value[step.id] || '').trim()
  savingHierarchyPathStepId.value = step.id
  errorMessage.value = ''
  try {
    await api.routings.patchRoutingStep(step.id, { hierarchy_path: newPath })
    await fetchStepsAndMaterials(selectedRoutingId.value)
  } catch (error) {
    console.error('階層更新エラー:', error)
    const detail = error?.response?.data?.hierarchy_path?.[0] || error?.response?.data?.detail || '階層の更新に失敗しました'
    alert(detail)
  } finally {
    if (savingHierarchyPathStepId.value === step.id) {
      savingHierarchyPathStepId.value = null
    }
  }
}

const saveParentProduct = async (step) => {
  if (!canEdit.value || !step?.id) return
  if (!isParentProductDirty(step)) return

  const product = findProductByInput(parentProductDraftByStepId.value[step.id])
  if (!product) {
    alert('親製品は既存の品番コードで入力してください。')
    return
  }

  savingParentProductStepId.value = step.id
  errorMessage.value = ''
  try {
    await api.routings.patchRoutingStep(step.id, { remark: product.product_code })
    await fetchStepsAndMaterials(selectedRoutingId.value)
  } catch (error) {
    console.error('親製品更新エラー:', error)
    const detail = error?.response?.data?.detail || error?.response?.data?.non_field_errors?.[0] || '親製品の更新に失敗しました'
    alert(detail)
  } finally {
    if (savingParentProductStepId.value === step.id) {
      savingParentProductStepId.value = null
    }
  }
}

const saveRoutingHeader = async () => {
  const routing = selectedRouting.value
  if (!canEdit.value || !routing?.id || !isRoutingHeaderDirty.value) return

  savingRoutingHeader.value = true
  errorMessage.value = ''
  try {
    await api.routings.patchRouting(routing.id, {
      is_default: Boolean(routingHeaderDraft.value.is_default),
      is_active: Boolean(routingHeaderDraft.value.is_active),
      valid_from_datetime: normalizeDatetimeLocal(routingHeaderDraft.value.valid_from_datetime),
      valid_to_datetime: normalizeDatetimeLocal(routingHeaderDraft.value.valid_to_datetime),
    })
    await refreshAll()
    resetRoutingHeaderDraft(selectedRouting.value)
  } catch (error) {
    console.error('ルーティングヘッダ更新エラー:', error)
    const detail = error?.response?.data?.detail || error?.response?.data?.non_field_errors?.[0] || 'ルーティングヘッダの更新に失敗しました'
    alert(detail)
  } finally {
    savingRoutingHeader.value = false
  }
}

const fetchRoutings = async () => {
  loadingRoutings.value = true
  try {
    const params = {
    }
    if (onlyActive.value) {
      params.is_active = true
    }
    const list = await api.routings.getAllRoutings(params)
    routings.value = list
  } finally {
    loadingRoutings.value = false
  }
}

const fetchRoutingFinalLineMap = async () => {
  if (routingFinalLineMapLoaded.value) return
  loadingRoutingFinalLineMap.value = true
  try {
    const perPage = 500
    let page = 1
    const all = []
    while (true) {
      const res = await api.routings.getRoutingSteps({ page, page_size: perPage })
      const data = res?.data
      if (Array.isArray(data)) {
        all.push(...data)
        break
      }
      const rows = normalizeList(data)
      all.push(...rows)
      if (!data?.next) break
      page += 1
    }
    const byRouting = new Map()
    for (const step of all) {
      const routingId = Number(step?.routing)
      if (!Number.isFinite(routingId) || !step?.line) continue
      const current = byRouting.get(routingId)
      if (!current) {
        byRouting.set(routingId, step)
        continue
      }
      const stepNo = Number(step?.step_no ?? 0)
      const curStepNo = Number(current?.step_no ?? 0)
      if (stepNo > curStepNo) {
        byRouting.set(routingId, step)
        continue
      }
      if (stepNo === curStepNo) {
        const pg = Number(step?.parallel_group ?? 0)
        const curPg = Number(current?.parallel_group ?? 0)
        if (pg > curPg) byRouting.set(routingId, step)
      }
    }
    const map = {}
    byRouting.forEach((step, routingId) => {
      map[routingId] = Number(step.line)
    })
    routingFinalLineIdByRoutingId.value = map
    routingFinalLineMapLoaded.value = true
  } catch (error) {
    console.error('ルーティング最終工程ライン集計エラー:', error)
  } finally {
    loadingRoutingFinalLineMap.value = false
  }
}

const fetchBomQuantityMap = async (routing) => {
  if (!routing?.product) return {}
  const bomRes = await api.boms.getBOMs({
    parent_product: routing.product,
    is_active: true,
    page_size: 200,
  })
  const bomList = normalizeList(bomRes.data)
  if (bomList.length === 0) return {}

  const latestBom = [...bomList].sort((a, b) => {
    const av = `${a.valid_from || ''}#${a.id || 0}`
    const bv = `${b.valid_from || ''}#${b.id || 0}`
    return av < bv ? 1 : -1
  })[0]
  if (!latestBom?.id) return {}

  const itemRes = await api.boms.getBOMItems({ bom: latestBom.id })
  const items = normalizeList(itemRes.data)
  const map = {}
  items.forEach((item) => {
    map[item.child_product] = item.quantity
  })
  return map
}

const fetchStepsAndMaterials = async (routingId) => {
  const token = Date.now()
  stepLoadToken.value = token
  loadingSteps.value = true
  errorMessage.value = ''
  processFilter.value = ''
  representativeChildProductIds.value = new Set()

  try {
    const stepRes = await api.routings.getRoutingSteps({ routing: routingId, page_size: 5000 })
    const routingIdNum = Number(routingId)
    const stepList = normalizeList(stepRes.data).filter(
      (step) => Number(step.routing) === routingIdNum
    )
    if (stepLoadToken.value !== token) return
    steps.value = stepList
    resetDurationDrafts(stepList)
    resetLeadTimeDrafts(stepList)
    resetUsageQuantityDrafts(stepList)
    resetOutputProductDrafts(stepList)
    resetParentProductDrafts(stepList)
    resetHierarchyPathDrafts(stepList)

    // ルーティングID一括取得（ステップ数分のN+1リクエストを回避）
    // routing 指定時はサーバー側でページネーション無効化のため page_size 不要
    const routing = routings.value.find((item) => item.id === routingId)
    const matRes = await api.routings.getRoutingStepMaterials({ routing: routingId })
    if (stepLoadToken.value !== token) return

    const allMaterials = normalizeList(matRes.data)
    const materialMap = {}
    allMaterials.forEach((mat) => {
      const sid = mat.routing_step
      if (!materialMap[sid]) materialMap[sid] = []
      materialMap[sid].push(mat)
    })
    materialsByStepId.value = materialMap
    representativeChildProductIds.value = new Set(
      stepList
        .map((step) => Number(step?.output_product))
        .filter((id) => Number.isFinite(id) && coproductDriverChildProductIds.value.has(id))
    )
    bomQuantityByChildId.value = {}
    fetchBomQuantityMap(routing)
      .then((bomQuantityMap) => {
        if (stepLoadToken.value !== token) return
        bomQuantityByChildId.value = bomQuantityMap
      })
      .catch((error) => {
        console.warn('BOM使用数量取得エラー:', error)
      })
  } catch (error) {
    console.error('ルーティング工程取得エラー:', error)
    errorMessage.value = 'ルーティング工程の取得に失敗しました'
  } finally {
    if (stepLoadToken.value === token) {
      loadingSteps.value = false
    }
  }
}

const selectRouting = async (routingId) => {
  if (!routingId) return
  if (selectedRoutingId.value === routingId) {
    await fetchStepsAndMaterials(routingId)
    return
  }
  selectedRoutingId.value = routingId
}

const refreshAll = async () => {
  errorMessage.value = ''
  try {
    await fetchRoutings()
  } catch (error) {
    console.error('ルーティングマスタ更新エラー:', error)
    errorMessage.value = 'データ更新に失敗しました'
  }
}

const resetCreateDraft = () => {
  newRoutingDraft.value = {
    product: '',
    routing_code: '',
    description: '',
    is_default: false,
    is_active: true,
  }
  newRoutingProductSearch.value = ''
  newRoutingProductDropOpen.value = false
}

const toggleCreateRow = () => {
  showCreateRow.value = !showCreateRow.value
  if (!showCreateRow.value) {
    resetCreateDraft()
  }
}

const fetchProducts = async () => {
  loadingProducts.value = true
  try {
    products.value = await api.products.getAllProducts({ is_active: true })
  } catch (error) {
    console.error('品番一覧取得エラー:', error)
    alert('品番一覧の取得に失敗しました。')
  } finally {
    loadingProducts.value = false
  }
}

const fetchProcesses = async () => {
  loadingProcesses.value = true
  try {
    const res = await api.processes.getProcesses({ page_size: 500 })
    processes.value = normalizeList(res?.data)
  } catch (error) {
    console.error('工程一覧取得エラー:', error)
    alert('工程一覧の取得に失敗しました。')
  } finally {
    loadingProcesses.value = false
  }
}

const syncLineFromProcess = (processId) => {
  const selectedProcess = processes.value.find((proc) => String(proc.id) === String(processId))
  newStepDraft.value.line = selectedProcess?.line ? Number(selectedProcess.line) : ''
}

const fetchSuppliers = async () => {
  loadingSuppliers.value = true
  try {
    const res = await api.suppliers.getSuppliers({ page_size: 500 })
    suppliers.value = normalizeList(res?.data)
  } catch (error) {
    console.error('外作先一覧取得エラー:', error)
    alert('外作先一覧の取得に失敗しました。')
  } finally {
    loadingSuppliers.value = false
  }
}

const fetchCustomers = async () => {
  loadingCustomers.value = true
  try {
    const res = await api.customers.getCustomers()
    customers.value = normalizeList(res?.data)
  } catch (error) {
    console.error('得意先一覧取得エラー:', error)
    alert('得意先一覧の取得に失敗しました。')
  } finally {
    loadingCustomers.value = false
  }
}

const fetchCustomerProductCodeSet = async (customerCode) => {
  if (!customerCode) {
    customerProductCodeSet.value = new Set()
    return
  }
  loadingCustomerProductSet.value = true
  try {
    const res = await api.orders.getCustomerProductCodes(customerCode)
    const rows = Array.isArray(res?.data?.product_codes) ? res.data.product_codes : []
    const set = new Set(
      rows
        .map((code) => String(code || '').trim())
        .filter((code) => Boolean(code))
    )
    customerProductCodeSet.value = set
  } catch (error) {
    console.error('得意先別品番取得エラー:', error)
    customerProductCodeSet.value = new Set()
    alert('得意先別品番の取得に失敗しました。')
  } finally {
    loadingCustomerProductSet.value = false
  }
}

const resetCreateStepDraft = () => {
  newStepDraft.value = {
    step_no: '',
    hierarchy_path: '',
    parallel_group: 1,
    process: '',
    line: '',
    supplier: '',
    sourcing_type: 'MAKE',
    output_product: '',
    time_unit: 'DAY',
    lead_time_days: 0,
    duration_min: '',
    usage_quantity: '',
    remark: '',
  }
  outputProductSearch.value = ''
  outputProductDropOpen.value = false
  remarkProductSearch.value = ''
  remarkProductDropOpen.value = false
  autoFillProcessWarning.value = ''
}

const toggleCreateStepRow = () => {
  showCreateStepRow.value = !showCreateStepRow.value
  if (showCreateStepRow.value) {
    resetCreateStepDraft()
  }
}

const createStep = async () => {
  if (isCreateStepDisabled.value || !selectedRoutingId.value) return
  creatingStep.value = true
  errorMessage.value = ''
  try {
    const hierarchyPath = String(newStepDraft.value.hierarchy_path || '').trim()
    const payload = {
      routing: Number(selectedRoutingId.value),
      step_no: Number(newStepDraft.value.step_no),
      parallel_group: Number(newStepDraft.value.parallel_group || 1),
      process: newStepDraft.value.process ? Number(newStepDraft.value.process) : null,
      line: newStepDraft.value.line ? Number(newStepDraft.value.line) : null,
      supplier: newStepDraft.value.supplier ? Number(newStepDraft.value.supplier) : null,
      output_product: newStepDraft.value.output_product ? Number(newStepDraft.value.output_product) : null,
      time_unit: newStepDraft.value.time_unit === 'MINUTE' ? 'MINUTE' : 'DAY',
      lead_time_days: newStepDraft.value.time_unit === 'DAY' ? Number(newStepDraft.value.lead_time_days || 0) : 0,
      duration_min: newStepDraft.value.time_unit === 'MINUTE' ? Number(newStepDraft.value.duration_min) : null,
      sourcing_type: newStepDraft.value.sourcing_type || 'MAKE',
      usage_quantity: newStepDraft.value.usage_quantity !== '' && newStepDraft.value.usage_quantity != null ? Number(newStepDraft.value.usage_quantity) : null,
      remark: String(newStepDraft.value.remark || '').trim() || null,
    }
    payload.hierarchy_path = hierarchyPath
    await api.routings.createRoutingStep(payload)
    resetCreateStepDraft()
    try {
      await fetchStepsAndMaterials(selectedRoutingId.value)
    } catch (refreshError) {
      console.error('工程追加後の再読込エラー:', refreshError)
      errorMessage.value = '工程は追加済みですが、一覧の再読込に失敗しました。更新してください。'
    }
  } catch (error) {
    console.error('工程追加エラー:', error)
    const data = error?.response?.data || {}
    const detail =
      data.hierarchy_path?.[0] ||
      data.process?.[0] ||
      data.detail ||
      data.non_field_errors?.[0] ||
      '工程の追加に失敗しました'
    alert(detail)
  } finally {
    creatingStep.value = false
  }
}

const createRouting = async () => {
  if (isCreateDisabled.value) return
  creatingRouting.value = true
  errorMessage.value = ''
  try {
    const payload = {
      product: Number(newRoutingDraft.value.product),
      routing_code: String(newRoutingDraft.value.routing_code || '').trim(),
      description: String(newRoutingDraft.value.description || '').trim() || null,
      is_default: Boolean(newRoutingDraft.value.is_default),
      is_active: Boolean(newRoutingDraft.value.is_active),
    }
    const res = await api.routings.createRouting(payload)
    const newRoutingId = res?.data?.id
    resetCreateDraft()
    showCreateRow.value = false
    await refreshAll()
    if (newRoutingId) {
      selectedRoutingId.value = Number(newRoutingId)
    }
  } catch (error) {
    console.error('ルーティング新規作成エラー:', error)
    const detail =
      error?.response?.data?.detail ||
      error?.response?.data?.non_field_errors?.[0] ||
      'ルーティング新規作成に失敗しました'
    alert(detail)
  } finally {
    creatingRouting.value = false
  }
}

watch(selectedRoutingId, async (routingId) => {
  if (!routingId) {
    steps.value = []
    materialsByStepId.value = {}
    bomQuantityByChildId.value = {}
    representativeChildProductIds.value = new Set()
    durationDraftByStepId.value = {}
    leadTimeDraftByStepId.value = {}
    usageQuantityDraftByStepId.value = {}
    outputProductDraftByStepId.value = {}
    parentProductDraftByStepId.value = {}
    processFilter.value = ''
    return
  }
  await fetchStepsAndMaterials(routingId)
})

watch(() => newStepDraft.value.process, (processId) => {
  if (!processId) {
    newStepDraft.value.line = ''
    return
  }
  syncLineFromProcess(processId)
})

const autoFillProcessWarning = ref('')

const autoFillSupplierLineAndProcess = () => {
  autoFillProcessWarning.value = ''
  const st = newStepDraft.value.sourcing_type
  if (st === 'MAKE') {
    newStepDraft.value.supplier = ''
    return
  }
  if (st === 'SUBCON') {
    const proc = processOptions.value.find(p => p.process_code === 'G')
    if (proc) {
      newStepDraft.value.process = proc.id
    } else {
      newStepDraft.value.process = ''
      autoFillProcessWarning.value = `工程マスタに「外注(G)」が未登録です。先に工程マスタで作成してください。`
    }
  } else {
    newStepDraft.value.process = ''
  }

  const supplierId = Number(newStepDraft.value.supplier)
  if (!supplierId) return
  const supplier = supplierOptions.value.find(s => s.id === supplierId)
  if (!supplier) return
  const matchLine = lines.value.find(l => l.line_code === supplier.supplier_code)
  if (matchLine) newStepDraft.value.line = matchLine.id
}

watch(() => newStepDraft.value.sourcing_type, () => {
  autoFillSupplierLineAndProcess()
})

watch(() => newStepDraft.value.supplier, () => {
  if (newStepDraft.value.sourcing_type !== 'MAKE') {
    autoFillSupplierLineAndProcess()
  }
})

watch(selectedRouting, (routing) => {
  resetRoutingHeaderDraft(routing)
  if (showCreateStepRow.value) {
    resetCreateStepDraft()
  }
}, { immediate: true })

watch(filteredRoutings, (list) => {
  if (!list.length) {
    selectedRoutingId.value = null
    return
  }
  if (!list.some((item) => item.id === selectedRoutingId.value)) {
    selectedRoutingId.value = null
  }
})

watch(onlyActive, async () => {
  await fetchRoutings()
})
watch(filterFinalLineId, async (lineId) => {
  if (!lineId) return
  await fetchRoutingFinalLineMap()
})
watch(filterCustomerCode, async (code) => {
  await fetchCustomerProductCodeSet(code)
})

const fetchLines = async () => {
  loadingLines.value = true
  try {
    const res = await api.lines.getLines({ page_size: 500 })
    lines.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('ライン一覧取得エラー', e)
  } finally {
    loadingLines.value = false
  }
}

const openMigrationDialog = async () => {
  if (!migrationLineId.value) return
  checkingMigration.value = true
  try {
    const res = await api.lineBacklogs.detectStockMigration({ line_id: migrationLineId.value })
    const candidates = res.data || []
    if (candidates.length === 0) {
      noMigrationMessage.value = true
      return
    }
    migrationCandidates.value = candidates.map((c) => ({ ...c, migrate_qty: c.stock_qty, checked: true }))
    migrationDialogVisible.value = true
  } catch (e) {
    console.error('在庫移行検出エラー', e)
    alert('孤立在庫の検出に失敗しました。')
  } finally {
    checkingMigration.value = false
  }
}

const executeMigration = async () => {
  executingMigration.value = true
  try {
    const items = migrationCandidates.value
      .filter((c) => c.checked && c.migrate_qty !== 0)
      .map((c) => ({
        product_id: c.product_id,
        old_line_id: c.old_line_id,
        old_process_id: c.old_process_id,
        new_line_id: c.new_line_id,
        new_process_id: c.new_process_id,
        migrate_qty: c.migrate_qty,
      }))
    if (items.length === 0) {
      migrationDialogVisible.value = false
      return
    }
    const res = await api.lineBacklogs.executeStockMigration({ migration_date: migrationDate.value, items })
    migrationDialogVisible.value = false
    const count = res.data?.count ?? items.length
    alert(`在庫移行が完了しました。${count}件`)
  } catch (e) {
    const detail = e?.response?.data?.detail || '在庫移行に失敗しました。'
    console.error('在庫移行実行エラー', e)
    alert(`エラー: ${detail}`)
  } finally {
    executingMigration.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    refreshAll(),
    fetchLines(),
    fetchProducts(),
    fetchProcesses(),
    fetchSuppliers(),
    fetchCustomers(),
    fetchCoproductDriverChildProductIds(),
  ])
})
</script>

<style scoped>
.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.create-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid #dcdfe5;
  border-radius: 8px;
  background: #fff;
  flex-wrap: wrap;
}

.create-step-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid #eceff5;
  background: #f7fafc;
  flex-wrap: wrap;
}
.create-step-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.create-step-label {
  font-size: 10px;
  color: #6b7280;
  font-weight: 600;
  white-space: nowrap;
}
.autocomplete-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 200px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid #d5d7dd;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,.15);
  z-index: 100;
  margin: 0;
  padding: 0;
  list-style: none;
}
.autocomplete-item {
  padding: 5px 8px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.autocomplete-item:hover {
  background: #e0edff;
}

.create-select {
  min-width: 320px;
  max-width: 460px;
  padding: 7px 10px;
  border: 1px solid #d5d7dd;
  border-radius: 6px;
  font-size: 13px;
}

.create-input {
  min-width: 180px;
  padding: 7px 10px;
  border: 1px solid #d5d7dd;
  border-radius: 6px;
  font-size: 13px;
}

.create-input--wide {
  min-width: 260px;
}

.step-select {
  min-width: 170px;
  max-width: 260px;
  padding: 5px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}

.step-select--small {
  min-width: 90px;
  max-width: 110px;
}

.search-input {
  width: 420px;
  max-width: 100%;
  padding: 8px 10px;
  border: 1px solid #d5d7dd;
  border-radius: 6px;
}

.search-input--narrow {
  width: 240px;
}

.checkbox-inline {
  display: flex;
  align-items: center;
  gap: 6px;
}

.count-text {
  color: #666;
  font-size: 13px;
}

.readonly-note {
  color: #b45309;
  font-size: 12px;
}

.split-layout {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 12px;
}

.split-layout--single {
  grid-template-columns: 1fr;
}

.panel {
  border: 1px solid #dcdfe5;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}

.panel-title {
  margin: 0;
  padding: 10px 12px;
  border-bottom: 1px solid #eceff5;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-subtitle {
  margin-left: 8px;
  color: #556;
  font-size: 13px;
  font-weight: 400;
}

.table-wrap {
  max-height: 72vh;
  overflow: auto;
}

.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #d1d5db;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: routing-loading-spin 0.8s linear infinite;
}

.loading-spinner--lg {
  width: 28px;
  height: 28px;
  border-width: 3px;
}

@keyframes routing-loading-spin {
  to {
    transform: rotate(360deg);
  }
}

.step-panel {
  position: relative;
}

.step-panel-overlay {
  position: absolute;
  inset: 0;
  z-index: 40;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(1px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-panel-overlay__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #1f2937;
  font-weight: 600;
}

.routing-header-form {
  padding: 10px 12px;
  border-bottom: 1px solid #eceff5;
  background: #f8fafc;
}

.routing-header-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(140px, 1fr));
  gap: 10px;
}

.routing-header-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #374151;
}

.routing-header-field input[type='datetime-local'] {
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}

.routing-header-field--check {
  justify-content: center;
}

.routing-header-field--check input[type='checkbox'] {
  width: 16px;
  height: 16px;
}

.routing-header-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

.step-filter-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid #eceff5;
  background: #fafbfc;
}

.btn-small {
  padding: 4px 10px;
  font-size: 12px;
}

.panel-toggle-btn {
  margin-left: auto;
}

.step-filter-row label {
  font-size: 13px;
  color: #374151;
}

.step-filter-row select {
  min-width: 180px;
  padding: 5px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}

.step-panel .data-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #d7dce8;
}

.compact th,
.compact td {
  padding: 6px 8px;
  font-size: 13px;
  white-space: nowrap;
}

.duration-editor {
  display: flex;
  align-items: center;
  gap: 6px;
}

.duration-input {
  width: 80px;
  padding: 2px 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
  text-align: right;
}

.create-step-warning {
  width: 100%;
  padding: 4px 8px;
  margin-top: 2px;
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffc107;
  border-radius: 4px;
  font-size: 12px;
}
.hierarchy-input {
  width: 60px;
  padding: 2px 4px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
  text-align: center;
}
.step-code-input {
  width: 150px;
  padding: 2px 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
}

.duration-save-btn {
  padding: 2px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #f9fafb;
  color: #374151;
  font-size: 12px;
  cursor: pointer;
}

.duration-save-btn--active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.duration-save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.routing-panel .compact tbody tr {
  cursor: pointer;
}

.routing-panel .compact tbody tr.selected {
  background: #eaf2ff;
}

.empty-state {
  padding: 16px;
  color: #666;
}

.error-text {
  margin-top: 8px;
  color: #b42318;
}

.line-select {
  padding: 6px 10px;
  border: 1px solid #d5d7dd;
  border-radius: 6px;
  font-size: 13px;
  min-width: 220px;
}

.line-select--filter {
  min-width: 260px;
}

.btn-warning {
  padding: 6px 14px;
  background: #d97706;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}
.btn-warning:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 6px 14px;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

/* 在庫移行ダイアログ */
.migration-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2100;
}
.migration-dialog {
  background: #fff;
  border-radius: 10px;
  padding: 24px 28px;
  max-width: 820px;
  width: 95%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  max-height: 80vh;
  overflow-y: auto;
}
.migration-dialog--small {
  max-width: 400px;
}
.migration-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
  color: #b45309;
}
.migration-desc {
  font-size: 13px;
  color: #374151;
  margin: 0 0 12px;
  line-height: 1.6;
}
.migration-date-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  font-size: 13px;
}
.migration-date-input {
  padding: 4px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
}
.migration-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin-bottom: 12px;
}
.migration-table th {
  background: #f3f4f6;
  padding: 6px 8px;
  text-align: left;
  border-bottom: 1px solid #d1d5db;
  white-space: nowrap;
}
.migration-table td {
  padding: 5px 8px;
  border-bottom: 1px solid #e5e7eb;
  vertical-align: middle;
}
.qty-cell {
  text-align: right;
  font-weight: 600;
}
.migrate-qty-input {
  width: 70px;
  padding: 2px 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  text-align: right;
  font-size: 12px;
}
.migration-note {
  font-size: 11px;
  color: #6b7280;
  margin: 0 0 16px;
  line-height: 1.6;
}
.migration-warning {
  color: #dc2626;
  font-size: 14px;
  font-weight: bold;
}
.migration-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

@media (max-width: 1400px) {
  .split-layout {
    grid-template-columns: 1fr;
  }
}
</style>
