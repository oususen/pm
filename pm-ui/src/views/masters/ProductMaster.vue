<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">製品マスタ <DataSourceDialog title="製品マスタ" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button v-if="canEdit" @click="openLineFinalDialog" class="btn-secondary">ライン最終品 一括設定</button>
        <button v-if="canEdit" @click="downloadUpdateImportTemplateXlsx" class="btn-secondary">取込テンプレートExcel</button>
        <button v-if="canEdit" @click="openUpdateImport" class="btn-secondary">統合取込</button>
        <button @click="openExportTab" class="btn-secondary">製品出力</button>
        <button @click="fetchProducts(1)" class="btn-primary">更新</button>
        <button @click="openProcessTab('create')" class="btn-success" :disabled="!canEdit">処理</button>
      </div>
    </div>

    <div class="master-tab-bar">
      <button type="button" class="master-tab-btn" :class="{ active: activeTab === 'list' }" @click="activeTab = 'list'">一覧</button>
      <button type="button" class="master-tab-btn" :class="{ active: activeTab === 'process' }" @click="activeTab = 'process'">処理</button>
      <button type="button" class="master-tab-btn" :class="{ active: activeTab === 'export' }" @click="openExportTab">製品出力</button>
    </div>

    <div v-if="activeTab === 'list'" class="page-content">
      <div class="filter-bar">
        <div class="filter-field">
          <label>品番/品名</label>
          <input
            v-model="filters.search"
            @keyup.enter="fetchProducts(1)"
            placeholder="品番・品名で検索"
          />
        </div>
        <div class="filter-field">
          <label>カテゴリ</label>
          <select v-model="filters.category">
            <option value="">すべて</option>
            <option v-for="cat in categoryOptions" :key="cat.value" :value="cat.value">
              {{ cat.label }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>製品群</label>
          <select v-model="filters.product_group">
            <option value="">すべて</option>
            <option v-for="group in productGroups" :key="group.id" :value="group.id">
              {{ group.group_code }} - {{ group.group_name }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>最終品</label>
          <select v-model="filters.is_final_product">
            <option value="">すべて</option>
            <option value="true">はい</option>
            <option value="false">いいえ</option>
          </select>
        </div>
        <div class="filter-field" v-if="showCustomerFilter">
          <label>客先</label>
          <select v-model="filters.customer_code">
            <option value="">すべて</option>
            <option v-for="customer in customers" :key="customer.id" :value="customer.customer_code">
              {{ customer.customer_code }} - {{ customer.customer_name }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>ライン最終品</label>
          <select v-model="filters.is_line_final_product">
            <option value="">すべて</option>
            <option value="true">はい</option>
            <option value="false">いいえ</option>
          </select>
        </div>
        <div class="filter-field">
          <label>BOM持ち</label>
          <select v-model="filters.has_bom">
            <option value="">すべて</option>
            <option value="true">あり</option>
            <option value="false">なし</option>
          </select>
        </div>
        <div class="filter-field">
          <label>有効</label>
          <select v-model="filters.is_active">
            <option value="">すべて</option>
            <option value="true">有効</option>
            <option value="false">無効</option>
          </select>
        </div>
        <div class="filter-field">
          <label>工程</label>
          <select v-model="filters.process">
            <option value="">すべて</option>
            <option v-for="proc in processes" :key="proc.id" :value="proc.id">
              {{ proc.process_code }} - {{ proc.process_name }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>加工先(将来用)</label>
          <select v-model="filters.processing_area">
            <option value="">すべて</option>
            <option v-for="area in processingAreaOptions" :key="area.value" :value="area.value">
              {{ area.label }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>保管場所</label>
          <input v-model="filters.stock_location" placeholder="場所で検索" />
        </div>
        <div class="filter-field">
          <label>後工程</label>
          <select v-model="filters.next_process">
            <option value="">すべて</option>
            <option value="__none__">未設定</option>
            <option v-for="proc in processes" :key="proc.id" :value="proc.id">
              {{ proc.process_code }} - {{ proc.process_name }}
            </option>
          </select>
        </div>
        <div class="filter-field">
          <label>作成日 From</label>
          <input type="date" v-model="filters.created_from" />
        </div>
        <div class="filter-field">
          <label>作成日 To</label>
          <input type="date" v-model="filters.created_to" />
        </div>
        <div class="filter-actions">
          <button @click="fetchProducts(1)" class="btn-primary">検索</button>
          <button @click="resetFilters" class="btn-secondary">リセット</button>
        </div>
      </div>

      <div class="list-area">
        <table class="data-table">
          <thead>
            <tr>
              <th>品番コード</th>
              <th>品名</th>
              <th>カテゴリ</th>
              <th>単位</th>
              <th>単価</th>
              <th>標準LT(日)</th>
              <th>最小発注数</th>
              <th>発注倍数（ロット）</th>
              <th>機種名</th>
              <th>識別記号</th>
              <th>加工先(将来用)</th>
              <th>保管場所</th>
              <th>グループ</th>
              <th>容器</th>
              <th>容器入り数</th>
              <th>移動先</th>
              <th>最終品</th>
              <th>ライン最終品</th>
              <th>みなし組立</th>
              <th>仮想セット</th>
              <th>有効</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="product in products" :key="product.id">
              <td>{{ product.product_code }}</td>
              <td>{{ product.product_name }}</td>
              <td>{{ getCategoryLabel(product.category) }}</td>
              <td>{{ product.unit }}</td>
              <td>{{ product.unit_price ?? '-' }}</td>
              <td>{{ product.standard_lt_days }}</td>
              <td>{{ product.order_lot_min ?? '-' }}</td>
              <td>{{ product.order_lot_multiple ?? 1 }}</td>
              <td>{{ product.model_name || '-' }}</td>
              <td>{{ product.identification_code || '-' }}</td>
              <td>{{ getProcessingAreaLabel(product.processing_area) }}</td>
              <td>{{ formatStockLocations(product) }}</td>
              <td>{{ getProductGroupLabel(product.product_group) }}</td>
              <td>{{ getContainerLabel(product.used_container) }}</td>
              <td>{{ product.capacity ?? '-' }}</td>
              <td>{{ getTransferDestLabel(product.transfer_destination) }}</td>
              <td>{{ product.is_final_product ? '最終' : '' }}</td>
              <td>{{ product.is_line_final_product ? 'はい' : '' }}</td>
              <td>{{ product.is_phantom ? 'はい' : 'いいえ' }}</td>
              <td>{{ product.is_virtual_set ? 'はい' : 'いいえ' }}</td>
              <td>{{ product.is_active ? '有効' : '無効' }}</td>
              <td>
                <button v-if="canEdit" @click="editProduct(product)" class="btn-sm">編集</button>
                <button v-if="canEdit" @click="copyProduct(product)" class="btn-sm">コピー</button>
                <button @click="viewProduct(product)" class="btn-sm">照会</button>
                <button v-if="canEdit" @click="deleteProduct(product.id)" class="btn-sm btn-danger">削除</button>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="pagination-area">
          <div class="pagination" v-if="totalPages > 1">
            <button class="pagination-btn" :disabled="currentPage === 1" @click="changePage(1)">
              最初
            </button>
            <button class="pagination-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">
              前へ
            </button>
            <button
              v-for="page in visiblePages"
              :key="page"
              class="pagination-btn"
              :class="{ 'is-active': page === currentPage }"
              @click="changePage(page)"
            >
              {{ page }}
            </button>
            <button class="pagination-btn" :disabled="currentPage >= totalPages" @click="changePage(currentPage + 1)">
              次へ
            </button>
            <button class="pagination-btn" :disabled="currentPage >= totalPages" @click="changePage(totalPages)">
              最後
            </button>
          </div>
          <div class="pagination-info">{{ pageRangeLabel }}</div>
        </div>

        <div v-if="products.length === 0" class="no-data">
          データがありません
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'process'" class="page-content process-page-content">
      <div class="process-mode-panel">
        <div class="process-mode-row">
          <span class="process-mode-label">処理区分</span>
          <label class="mode-option">
            <input type="radio" name="process-mode" value="create" :checked="processMode === 'create'" @change="changeProcessMode('create')" />
            新規
          </label>
          <label class="mode-option">
            <input type="radio" name="process-mode" value="edit" :checked="processMode === 'edit'" @change="changeProcessMode('edit')" />
            変更
          </label>
          <label class="mode-option">
            <input type="radio" name="process-mode" value="view" :checked="processMode === 'view'" @change="changeProcessMode('view')" />
            照会
          </label>
        </div>
        <div v-if="processMode !== 'create'" class="process-target-row">
          <label>対象品番</label>
          <select v-model="processTargetId" @change="loadProcessTarget">
            <option :value="null">一覧から選択してください</option>
            <option v-for="product in products" :key="product.id" :value="product.id">
              {{ product.product_code }} - {{ product.product_name }}
            </option>
          </select>
          <button type="button" class="btn-secondary" @click="activeTab = 'list'">一覧で選択</button>
        </div>
        <div v-if="processMode === 'create' && copySourceProduct" class="process-target-row">
          <label>コピー元</label>
          <div>{{ copySourceProduct.product_code }} - {{ copySourceProduct.product_name }}</div>
        </div>
      </div>

      <div class="process-form-card">
        <h2>{{ processModeTitle }}</h2>
        <form @submit.prevent="saveProduct">
          <fieldset class="form-fieldset process-form-fieldset" :disabled="!canEdit || isViewMode">
            <div class="process-section section-basic-info">
              <h3 class="process-section-title">基本情報</h3>
              <div class="process-form-layout">
                <div class="process-subsection subsection-product-basic">
                  <div class="process-subsection-title">製品基本</div>
                  <div class="process-section-grid process-section-grid-4">
                    <div class="form-group">
                      <label>品番コード *</label>
                      <input v-model="formData.product_code" required :disabled="processMode !== 'create'" />
                    </div>
                    <div class="form-group">
                      <label>品名 *</label>
                      <input v-model="formData.product_name" required />
                    </div>
                    <div class="form-group">
                      <label>カテゴリ *</label>
                      <select v-model="formData.category" required>
                        <option value="">選択してください</option>
                        <option v-for="cat in categoryOptions" :key="cat.value" :value="cat.value">
                          {{ cat.label }}
                        </option>
                      </select>
                    </div>
                    <div class="form-group">
                      <label>単位</label>
                      <input v-model="formData.unit" placeholder="個" />
                    </div>
                    <div class="form-group">
                      <label>単価</label>
                      <input v-model.number="formData.unit_price" type="number" min="0" step="0.01" />
                    </div>
                    <div class="form-group">
                      <label>機種名</label>
                      <input v-model="formData.model_name" placeholder="例: 17U" />
                    </div>
                    <div class="form-group">
                      <label>識別記号</label>
                      <input v-model="formData.identification_code" placeholder="例: 7a" />
                    </div>
                  </div>
                </div>

                <div class="process-subsection subsection-procurement">
                  <div class="process-subsection-title">調達・在庫</div>
                  <div class="process-section-grid process-section-grid-4">
                    <div class="form-group process-group-span-2">
                      <label>標準LT(日)</label>
                      <input v-model.number="formData.standard_lt_days" type="number" min="0" />
                      <small class="field-note">
                        ※ 枚方集荷・運送など特殊運用専用。生産計画・在庫・進度・購買などの本命LTには使用しません（本命LTは RoutingStep.lead_time_days を参照）。
                      </small>
                    </div>
                    <div class="form-group">
                      <label>最小発注数</label>
                      <input v-model.number="formData.order_lot_min" type="number" min="0" />
                    </div>
                    <div class="form-group">
                      <label>発注倍数（ロット）</label>
                      <input v-model.number="formData.order_lot_multiple" type="number" min="1" />
                    </div>
                    <div class="form-group">
                      <label>加工先(将来用)</label>
                      <select v-model="formData.processing_area">
                        <option :value="null">未設定</option>
                        <option v-for="area in processingAreaOptions" :key="area.value" :value="area.value">
                          {{ area.label }}
                        </option>
                      </select>
                    </div>
                    <div class="form-group">
                      <label>製品グループ</label>
                      <select v-model="formData.product_group">
                        <option :value="null">未設定</option>
                        <option v-for="group in productGroups" :key="group.id" :value="group.id">
                          {{ group.group_code }} - {{ group.group_name }}
                        </option>
                      </select>
                    </div>
                    <div class="form-group">
                      <label>移動先</label>
                      <select v-model="formData.transfer_destination">
                        <option :value="null">未設定</option>
                        <option v-for="td in transferDestOptions" :key="td.value" :value="td.value">
                          {{ td.label }}
                        </option>
                      </select>
                    </div>
                    <div class="form-group process-group-span-2">
                      <label>保管場所</label>
                      <div class="stock-locations-edit">
                        <div v-for="(loc, idx) in formData.stock_locations_edit" :key="idx" class="stock-loc-row">
                          <input v-model="formData.stock_locations_edit[idx]" placeholder="例: レーザ横A棚" />
                          <button type="button" class="btn-sm btn-danger" @click="removeStockLocation(idx)">×</button>
                        </div>
                        <button type="button" class="btn-sm stock-location-add-btn" @click="addStockLocation">+ 置き場追加</button>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="process-subsection subsection-container-setting">
                  <div class="process-subsection-title">容器設定</div>
                  <div class="process-section-grid process-section-grid-2">
                    <div class="product-container-box product-container-box-standard">
                      <div class="product-container-box-title">標準容器</div>
                      <div class="container-setting-guide container-setting-guide-inline">
                        <div class="container-setting-guide-item">
                          <strong>標準容器:</strong> 通常使う容器と標準の容器入り数を設定します。
                        </div>
                        <div class="container-setting-guide-item">
                          <strong>臨時容器:</strong> 標準容器とは別に使う容器を、容器ごとの入数付きで登録します。
                        </div>
                      </div>
                      <div class="process-section-grid process-section-grid-2">
                        <div class="form-group">
                          <label>使用容器</label>
                          <select v-model="formData.used_container">
                            <option :value="null">未設定</option>
                            <option v-for="container in containers" :key="container.id" :value="container.id">
                              {{ formatContainerOption(container) }}
                            </option>
                          </select>
                        </div>
                        <div class="form-group">
                          <label>容器入り数</label>
                          <input v-model.number="formData.capacity" type="number" min="0" />
                        </div>
                      </div>
                    </div>
                    <div v-if="processMode !== 'create'" class="product-container-box product-container-box-temporary">
                      <div class="product-container-box-title">
                        臨時容器
                        <span class="product-container-box-note">標準容器とは別に使う臨時容器を登録します。既存の容器を選ぶと入数を更新し、新しい容器を選ぶと追加します。</span>
                      </div>
                      <div class="product-container-panel">
                        <div class="product-container-box product-container-box-nested product-container-box-current">
                          <div class="product-container-box-title">現在の登録</div>
                          <div v-if="productContainers.length" class="stock-locations-edit">
                            <div v-for="pc in productContainers" :key="pc.id" class="stock-loc-row product-container-readonly-row">
                              <span class="pc-container-label">{{ pc.container_name }}</span>
                              <span class="product-container-readonly-value">{{ pc.capacity }}</span>
                              <button
                                v-if="!isViewMode"
                                type="button"
                                class="btn-sm btn-danger"
                                @click="removeProductContainer(pc)"
                              >
                                削除
                              </button>
                            </div>
                          </div>
                          <div v-else class="product-container-empty">未設定です</div>
                        </div>
                        <div v-if="!isViewMode" class="product-container-box product-container-box-nested product-container-box-edit">
                          <div class="product-container-box-title">追加・変更</div>
                          <div class="stock-locations-edit">
                            <div class="stock-loc-row product-container-editor-row">
                              <select v-model="newContainerId" class="pc-add-select">
                                <option :value="null">容器を選択</option>
                                <option v-for="c in availableContainersForAdd" :key="c.id" :value="c.id">
                                  {{ formatProductContainerSelectOption(c) }}
                                </option>
                              </select>
                              <input v-model.number="newContainerCapacity" type="number" min="1" placeholder="入数" class="pc-capacity-input" />
                              <button type="button" class="btn-sm btn-primary" @click="addProductContainer">{{ productContainerActionLabel }}</button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="process-subsection subsection-material-info">
                  <div class="process-subsection-title">材料情報</div>
                  <div class="form-group-section">レーザ材料情報（重量 = 比重×縦×横×厚さ / 1,000,000 kg）</div>
                  <small v-if="!isMaterialCategory" class="field-note material-lock-note">カテゴリが「材料」の場合のみ編集できます。</small>
                  <fieldset class="form-fieldset material-info-fieldset" :disabled="!isMaterialCategory">
                    <div class="process-section-grid process-section-grid-5">
                      <div class="form-group">
                        <label>比重 (g/cm³)</label>
                        <input v-model.number="formData.specific_gravity" type="number" step="0.0001" min="0" placeholder="例: 7.85" />
                      </div>
                      <div class="form-group">
                        <label>縦 (mm)</label>
                        <input v-model.number="formData.size_length" type="number" step="0.01" min="0" placeholder="例: 1219" />
                      </div>
                      <div class="form-group">
                        <label>横 (mm)</label>
                        <input v-model.number="formData.size_width" type="number" step="0.01" min="0" placeholder="例: 2438" />
                      </div>
                      <div class="form-group">
                        <label>厚さ (mm)</label>
                        <input v-model.number="formData.size_thickness" type="number" step="0.001" min="0" placeholder="例: 4.5" />
                      </div>
                      <div v-if="computedUnitWeight != null" class="form-group">
                        <label>重量/枚 (kg) ※自動計算</label>
                        <div class="computed-value">{{ computedUnitWeight.toFixed(3) }} kg</div>
                      </div>
                    </div>
                  </fieldset>
                </div>
              </div>
            </div>

            <div class="process-section section-process-info">
              <h3 class="process-section-title">工程情報</h3>
              <div class="process-section-grid process-section-grid-4">
                <div class="form-group">
                  <label>工程情報</label>
                  <select v-model="formData.process">
                    <option :value="null">未設定</option>
                    <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                      {{ proc.process_code }} - {{ proc.process_name }}
                    </option>
                  </select>
                </div>
                <div class="form-group">
                  <label>ライン情報</label>
                  <select v-model="formData.line">
                    <option :value="null">未設定</option>
                    <option v-for="line in lines" :key="line.id" :value="line.id">
                      {{ line.line_code }} - {{ line.line_name }}
                    </option>
                  </select>
                </div>
                <div class="form-group">
                  <label>後工程</label>
                  <select v-model="formData.next_process">
                    <option :value="null">未設定</option>
                    <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                      {{ proc.process_code }} - {{ proc.process_name }}
                    </option>
                  </select>
                </div>
                <div class="form-group">
                  <label>管理区分（日/分）</label>
                  <select v-model="formData.management_unit">
                    <option :value="null">未設定</option>
                    <option value="DAY">日</option>
                    <option value="MINUTE">分</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="process-section section-status-info">
              <h3 class="process-section-title">状態</h3>
              <div class="process-check-grid">
                <label>
                  <input type="checkbox" v-model="formData.is_final_product" />
                  最終品（完成品として出荷される品目）
                </label>
                <label>
                  <input type="checkbox" v-model="formData.is_line_final_product" />
                  ライン最終品（ラインで最後に出力される品目）
                </label>
                <label>
                  <input type="checkbox" v-model="formData.is_virtual_set" />
                  仮想セット品番（連産品用、在庫を持たない親品番）
                </label>
                <label>
                  <input type="checkbox" v-model="formData.is_active" />
                  有効
                </label>
              </div>
            </div>

            <div class="process-section section-image-info">
              <h3 class="process-section-title">図面情報（写真など）</h3>
              <div class="process-section-grid">
                <div class="form-group process-group-full">
                  <label>画像URL</label>
                  <input v-model="formData.image_url" placeholder="/media/products/..." />
                  <div class="upload-row">
                    <input type="file" ref="fileInput" @change="onFileSelected" accept="image/*" />
                    <button type="button" class="btn-secondary" @click="triggerFileInput" :disabled="isViewMode || (processMode === 'create' && !formData.id)">
                      画像をアップロード
                    </button>
                    <span class="hint-small" v-if="processMode === 'create' && !formData.id">保存後にアップロードできます</span>
                  </div>
                </div>
                <div class="form-group process-group-full image-preview" v-if="formData.image_url">
                  <img :src="formData.image_url" alt="Product image" />
                </div>
              </div>
            </div>

            <div class="form-actions">
              <button v-if="!isViewMode" type="submit" class="btn-primary" :disabled="!canEdit">
                {{ processMode === 'edit' ? '更新' : '作成' }}
              </button>
              <button type="button" @click="resetProcessForm" class="btn-secondary">入力クリア</button>
              <button type="button" @click="activeTab = 'list'" class="btn-secondary">一覧へ戻る</button>
            </div>
          </fieldset>
        </form>
      </div>
    </div>
    <!-- CSVインポートダイアログ -->
    <div v-if="showCsvImportDialog" class="modal-overlay" @click.self="closeCsvImport">
      <div class="modal-content csv-import-modal">
        <h2>製品マスタ 取込（CSV / Excel）</h2>

        <div class="csv-format-note">
          <strong>CSVフォーマット（1行目はヘッダー）:</strong><br>
          品名規格, 構成品番, 品番区分名, ライン情報, 工程情報, 後工程, 管理区分, 最終品, ライン最終品<br>
          <small>品番区分名: 集合部品 / 単体部品 / 材料 / 購入品 / 外作品</small>
        </div>

        <div class="form-group">
          <label>取込ファイル</label>
          <input type="file" accept=".csv,.xlsx" @change="onCsvSelected" />
        </div>

        <div v-if="csvPreviewRows.length > 0" class="csv-preview-area">
          <div class="csv-preview-header">
            プレビュー: {{ csvPreviewRows.length }}件（重複除外済み）
          </div>
          <table class="data-table csv-preview-table">
            <thead>
              <tr>
                <th>品番コード</th>
                <th>品名規格</th>
                <th>品番区分名</th>
                <th>ライン情報</th>
                <th>工程情報</th>
                <th>後工程</th>
                <th>管理区分</th>
                <th>最終品</th>
                <th>ライン最終品</th>
                <th>登録カテゴリ</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in csvPreviewRows" :key="i">
                <td>{{ row.product_code }}</td>
                <td>{{ row.product_name }}</td>
                <td>{{ row.category_raw }}</td>
                <td>{{ row.line_code }}</td>
                <td>{{ row.process_code }}</td>
                <td>{{ row.next_process_code }}</td>
                <td>{{ row.management_unit_raw }}</td>
                <td>{{ row.is_final_product_raw }}</td>
                <td>{{ row.is_line_final_product_raw }}</td>
                <td>{{ getCategoryLabel(csvCategoryMap[row.category_raw] || 'UNKNOWN') }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="csvImportResult" class="csv-result-area">
          <span class="result-created">登録: {{ csvImportResult.created }}件</span>
          <span class="result-skipped">スキップ(既存): {{ csvImportResult.skipped }}件</span>
          <div v-if="csvImportResult.skipped_codes.length > 0" class="skipped-codes">
            {{ csvImportResult.skipped_codes.join(', ') }}
          </div>
        </div>

        <div class="form-actions">
          <button
            v-if="csvPreviewRows.length > 0 && !csvImportResult"
            @click="executeCsvImport"
            class="btn-primary"
            :disabled="csvImporting"
          >
            {{ csvImporting ? 'インポート中...' : `${csvPreviewRows.length}件 登録実行` }}
          </button>
          <button @click="closeCsvImport" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>

    <!-- 統合取込ダイアログ -->
    <div v-if="showUpdateImportDialog" class="modal-overlay" @click.self="showUpdateImportDialog = false">
      <div class="modal-content csv-import-modal">
        <h2>製品マスタ 統合取込（CSV / Excel）</h2>

        <div class="csv-format-note">
          <strong>品番コードで照合し、既存は更新・未登録は新規登録します。</strong><br>
          <small>空欄の列はスキップ（元の値を維持）します。</small><br>
          <small>対応列: 構成品番(必須), 品名規格, 品番区分名, 単位, 単価, 標準LT, 自工程LT, ライン情報, 工程情報, 後工程, 管理区分, 最終品, ライン最終品, 機種名, 識別記号, 製品グループ, 移動先, 比重, 縦, 横, 厚さ, 発注倍数, 最小発注数, 容器入り数</small>
        </div>

        <div class="form-group" style="display: flex; gap: 16px; align-items: center;">
          <div>
            <label>取込ファイル</label>
            <input type="file" accept=".csv,.xlsx,.xlsm" @change="onUpdateFileSelected" ref="updateFileInput" />
          </div>
          <label style="white-space: nowrap; cursor: pointer; user-select: none;">
            <input type="checkbox" v-model="appendGOnImport" /> 品番末尾にGを追加
          </label>
        </div>

        <div v-if="updateImportPreview" class="csv-result-area">
          <span class="result-created" style="color: #dc3545;" v-if="updateImportPreview.created">未登録（新規）: {{ updateImportPreview.created }}件</span>
          <span class="result-created">DB一致（更新）: {{ updateImportPreview.updated || 0 }}件</span>
          <span class="result-skipped">変更なし: {{ updateImportPreview.skipped || 0 }}件</span>
          <div v-if="updateImportPreview.created_codes && updateImportPreview.created_codes.length > 0" class="skipped-codes" style="color: #dc3545;">
            未登録: {{ updateImportPreview.created_codes.join(', ') }}
          </div>
          <div v-if="updateImportPreview.updated_codes && updateImportPreview.updated_codes.length > 0" class="skipped-codes">
            DB一致: {{ updateImportPreview.updated_codes.join(', ') }}
          </div>
        </div>

        <div v-if="updateImportDone" class="csv-result-area" style="border-color: #28a745; background: #d4edda;">
          <strong>取込完了</strong>
        </div>

        <div class="form-actions">
          <button v-if="updateImportPreview && !updateImportDone" @click="executeUpdateImport" :disabled="updateImporting" class="btn-primary">
            {{ updateImporting ? '取込中...' : '取り込みしますか？' }}
          </button>
          <button @click="closeUpdateImport" class="btn-secondary">閉じる</button>
        </div>
      </div>
    </div>

    <!-- ライン最終品 一括設定ダイアログ -->
    <div v-if="showLineFinalDialog" class="modal-overlay" @click.self="showLineFinalDialog = false">
      <div class="modal-content line-final-modal">
        <h2>ライン最終品 一括設定</h2>

        <div class="lf-filter-bar">
          <div class="filter-field">
            <label>ライン</label>
            <select v-model="lfSelectedLine" @change="fetchLineFinalCandidates">
              <option value="">すべて</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
          </div>
        </div>

        <div class="lf-lines-area">
          <div v-for="lineGroup in lfLineGroups" :key="lineGroup.line_id" class="lf-line-group">
            <h3 class="lf-line-header">{{ lineGroup.line_code }} - {{ lineGroup.line_name }}</h3>
            <table class="data-table lf-table">
              <thead>
                <tr>
                  <th style="width: 60px;">ライン最終品</th>
                  <th>品番コード</th>
                  <th>品名</th>
                  <th>カテゴリ</th>
                  <th>最終品</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="product in lineGroup.products" :key="product.id">
                  <td style="text-align: center;">
                    <input
                      type="checkbox"
                      v-model="lfChanges[product.id]"
                      :disabled="!canEdit"
                    />
                  </td>
                  <td>{{ product.product_code }}</td>
                  <td>{{ product.product_name }}</td>
                  <td>{{ getCategoryLabel(product.category) }}</td>
                  <td>{{ product.is_final_product ? '最終' : '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="lfLineGroups.length === 0" class="no-data">
            ルーティングに紐づく製品がありません
          </div>
        </div>

        <div class="form-actions">
          <button @click="saveLineFinal" class="btn-primary" :disabled="lfSaving || !canEdit">
            {{ lfSaving ? '保存中...' : '保存' }}
          </button>
          <button @click="showLineFinalDialog = false" class="btn-secondary">キャンセル</button>
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'export'" class="page-content export-page-content">
      <div class="process-form-card export-card">
        <h2>製品出力</h2>
        <div class="export-filter-grid">
          <div class="form-group">
            <label>ライン</label>
            <select v-model="exportFilters.line">
              <option value="">すべて</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>工程</label>
            <select v-model="exportFilters.process">
              <option value="">すべて</option>
              <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                {{ proc.process_code }} - {{ proc.process_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>仕入先</label>
            <select v-model="exportFilters.supplier_code">
              <option value="">すべて</option>
              <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.supplier_code">
                {{ supplier.supplier_code }} - {{ supplier.supplier_name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>移動先</label>
            <select v-model="exportFilters.transfer_destination">
              <option value="">すべて</option>
              <option v-for="td in transferDestOptions" :key="td.value" :value="td.value">
                {{ td.label }}
              </option>
            </select>
          </div>
        </div>

        <div class="form-actions export-actions">
          <button type="button" class="btn-secondary" @click="previewProductExport" :disabled="exportLoading">
            {{ exportLoading ? '抽出中...' : '件数確認' }}
          </button>
          <button type="button" class="btn-primary" @click="exportProductsToExcel" :disabled="exporting">
            {{ exporting ? '出力中...' : 'Excel出力' }}
          </button>
          <button type="button" class="btn-secondary" @click="resetExportFilters" :disabled="exportLoading || exporting">リセット</button>
        </div>

        <div class="export-summary">
          <span>抽出件数: {{ exportResultCount }}件</span>
          <span v-if="exportPreviewRows.length">プレビュー: 先頭 {{ exportPreviewRows.length }}件</span>
        </div>

        <div v-if="exportPreviewRows.length" class="list-area export-preview-area">
          <table class="data-table">
            <thead>
              <tr>
                <th>構成品番</th>
                <th>品名規格</th>
                <th>品番区分名</th>
                <th>ライン情報</th>
                <th>工程情報</th>
                <th>後工程</th>
                <th>移動先</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in exportPreviewRows" :key="row.export_key || row.id">
                <td>{{ row.product_code }}</td>
                <td>{{ row.product_name }}</td>
                <td>{{ toTemplateCategoryLabel(row.category) }}</td>
                <td>{{ row.line_code || '' }}</td>
                <td>{{ row.process_code || '' }}</td>
                <td>{{ row.next_process_code || '' }}</td>
                <td>{{ getTransferDestLabel(row.transfer_destination) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'
import { authState } from '@/auth'
import { canAccessMasterResource } from '@/utils/masterPermissions'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'm_product', desc: '製品マスタ' },
  { op: '読み取り', table: 'm_line', desc: 'ライン（選択肢）' },
  { op: '読み取り', table: 'm_process', desc: '工程（選択肢）' },
  { op: '読み取り', table: 'm_product_group', desc: '製品グループ（選択肢）' },
  { op: '読み取り', table: 'm_container_capacity', desc: '容器（選択肢）' },
  { op: '読み取り', table: 'm_customer', desc: '得意先（選択肢）' },
  { op: '読み取り', table: 'm_supplier', desc: '仕入先（製品出力条件）' },
]

// カテゴリマッピング (DB英語 ⇔ UI日本語)
const categoryMap = {
  'ASSEMBLY': '集合',
  'SINGLE': '単品',
  'MATERIAL': '材料',
  'PURCHASED': '購入品',
  'OUTSOURCED': '外作品',
  'UNKNOWN': '未定',
  '–¢’è': '未定', // 文字化けして保存された既存値も未定扱い
}

const categoryOptions = [
  { value: 'ASSEMBLY', label: '集合' },
  { value: 'SINGLE', label: '単品' },
  { value: 'MATERIAL', label: '材料' },
  { value: 'PURCHASED', label: '購入品' },
  { value: 'OUTSOURCED', label: '外作品' },
  { value: 'UNKNOWN', label: '未定' },
]

const templateCategoryMap = {
  ASSEMBLY: '集合部品',
  SINGLE: '単体部品',
  MATERIAL: '材料',
  PURCHASED: '購入品',
  OUTSOURCED: '外作品',
  UNKNOWN: '未定',
  '–¢’è': '未定',
}

const getCategoryLabel = (value) => categoryMap[value] || value

const transferDestOptions = [
  { value: 'INLINE', label: '社内ライン' },
  { value: 'INPAINT', label: '社内塗装' },
  { value: 'CWL', label: 'CWL' },
  { value: 'KOWA', label: '興和' },
  { value: 'DIRECT', label: '直納' },
  { value: 'OTHER', label: 'その他' },
]
const processingAreaOptions = [
  { value: 'LASER', label: 'レーザ' },
  { value: 'BRAKE', label: 'ブレーキ' },
  { value: 'NUT', label: 'ナット' },
  { value: 'WELD', label: '溶接' },
  { value: 'SPOT', label: 'スポット' },
  { value: 'ASSY', label: '組立' },
  { value: 'OTHER', label: 'その他' },
]

const transferDestMap = Object.fromEntries(transferDestOptions.map(o => [o.value, o.label]))
const processingAreaMap = Object.fromEntries(processingAreaOptions.map(o => [o.value, o.label]))
const getTransferDestLabel = (value) => transferDestMap[value] || value || '-'
const getProcessingAreaLabel = (value) => processingAreaMap[value] || value || '-'

const createEmptyFormData = () => ({
  product_code: '',
  product_name: '',
  model_name: '',
  identification_code: '',
  category: '',
  unit: '個',
  unit_price: null,
  standard_lt_days: 0,
  order_lot_min: null,
  order_lot_multiple: 1,
  specific_gravity: 7.85,
  size_length: null,
  size_width: null,
  size_thickness: null,
  product_group: null,
  used_container: null,
  capacity: null,
  transfer_destination: null,
  processing_area: null,
  stock_location: '',
  stock_locations_edit: [''],
  line: null,
  process: null,
  next_process: null,
  management_unit: null,
  is_active: true,
  is_line_final_product: false,
  is_final_product: false,
  is_virtual_set: false,
  image_url: '',
})

const mapProductToFormData = (product, options = {}) => {
  const source = product || {}
  const asCopy = options.asCopy === true
  return {
    ...createEmptyFormData(),
    ...source,
    id: asCopy ? undefined : source.id,
    product_code: asCopy ? '' : (source.product_code ?? ''),
    model_name: source.model_name ?? '',
    identification_code: source.identification_code ?? '',
    order_lot_min: source.order_lot_min ?? null,
    order_lot_multiple: source.order_lot_multiple ?? 1,
    line: source.line ?? null,
    process: source.process ?? null,
    next_process: source.next_process ?? null,
    management_unit: source.management_unit ?? null,
    specific_gravity: source.specific_gravity ?? 7.85,
    size_length: source.size_length ?? null,
    size_width: source.size_width ?? null,
    size_thickness: source.size_thickness ?? null,
    product_group: source.product_group ?? null,
    used_container: source.used_container ?? null,
    capacity: source.capacity ?? null,
    transfer_destination: source.transfer_destination ?? null,
    processing_area: source.processing_area ?? null,
    stock_location: source.stock_location ?? '',
    stock_locations_edit: source.stock_locations_list && source.stock_locations_list.length
      ? source.stock_locations_list.map(sl => sl.location_name)
      : (source.stock_location ? [source.stock_location] : ['']),
    image_url: asCopy ? '' : (source.image_url || ''),
  }
}

// データ
const products = ref([])
const lines = ref([])
const processes = ref([])
const suppliers = ref([])
const productGroups = ref([])
const containers = ref([])
const customers = ref([])
const productContainers = ref([])
const activeTab = ref('list')
const processMode = ref('create')
const processTargetId = ref(null)
const copySourceProduct = ref(null)
const currentPage = ref(1)
const pageSize = ref(50)
const totalCount = ref(0)
const filters = ref({
  search: '',
  category: '',
  product_group: '',
  is_final_product: '',
  is_line_final_product: '',
  has_bom: '',
  customer_code: '',
  is_active: '',
  process: '',
  processing_area: '',
  stock_location: '',
  created_from: '',
  created_to: ''
})
const formData = ref(createEmptyFormData())
const fileInput = ref(null)
const exportFilters = ref({
  line: '',
  process: '',
  supplier_code: '',
  transfer_destination: '',
})
const exportPreviewRows = ref([])
const exportResultCount = ref(0)
const exportLoading = ref(false)
const exporting = ref(false)
const canEdit = computed(() => canAccessMasterResource('masters.product', 'edit'))
const isViewMode = computed(() => processMode.value === 'view')
const isMaterialCategory = computed(() => formData.value.category === 'MATERIAL')
const processModeTitle = computed(() => {
  if (processMode.value === 'edit') return '製品変更'
  if (processMode.value === 'view') return '製品照会'
  return '製品新規作成'
})

const addStockLocation = () => {
  formData.value.stock_locations_edit.push('')
}
const removeStockLocation = (idx) => {
  formData.value.stock_locations_edit.splice(idx, 1)
  if (formData.value.stock_locations_edit.length === 0) formData.value.stock_locations_edit.push('')
}
const formatStockLocations = (product) => {
  if (product.stock_locations_list && product.stock_locations_list.length) {
    return product.stock_locations_list.map(sl => sl.location_name).join(', ')
  }
  return product.stock_location || '-'
}

const toTemplateCategoryLabel = (value) => templateCategoryMap[value] || value || ''
const yesNoLabel = (value) => (value ? 'はい' : 'いいえ')
const findLine = (lineId) => lines.value.find((line) => `${line.id}` === `${lineId}`)
const findProcess = (processId) => processes.value.find((process) => `${process.id}` === `${processId}`)
const findLineCode = (lineId) => findLine(lineId)?.line_code || ''
const findLineName = (lineId) => findLine(lineId)?.line_name || ''
const findProcessCode = (processId) => findProcess(processId)?.process_code || ''
const findProcessName = (processId) => findProcess(processId)?.process_name || ''
const findProductGroup = (groupId) => productGroups.value.find((group) => `${group.id}` === `${groupId}`)
const findContainer = (containerId) => containers.value.find((container) => `${container.id}` === `${containerId}`)
const getProductGroupCode = (groupId) => findProductGroup(groupId)?.group_code || ''
const getContainerCode = (containerId) => findContainer(containerId)?.container_code || ''
const getStockLocationByIndex = (product, index) => product?.stock_locations_list?.[index]?.location_name || ''

// CSVインポート
const showCsvImportDialog = ref(false)
const csvPreviewRows = ref([])
const csvImportResult = ref(null)
const csvImporting = ref(false)
const csvCategoryMap = {
  '集合部品': 'ASSEMBLY',
  '単体部品': 'SINGLE',
  '材料': 'MATERIAL',
  '購入品': 'PURCHASED',
  '外作品': 'OUTSOURCED',
}

const openCsvImport = () => {
  csvPreviewRows.value = []
  csvImportResult.value = null
  showCsvImportDialog.value = true
}

const downloadProductImportTemplateXlsx = async () => {
  try {
    const res = await api.products.downloadImportTemplateXlsx()
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'product_import_template.xlsx'
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('製品テンプレートExcel取得エラー:', error)
    alert('テンプレートExcelの取得に失敗しました')
  }
}

const closeCsvImport = () => {
  showCsvImportDialog.value = false
  if (csvImportResult.value?.created > 0) {
    fetchProducts(1)
  }
}

const onCsvSelected = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  const lowerName = String(file.name || '').toLowerCase()
  if (lowerName.endsWith('.xlsx') || lowerName.endsWith('.xlsm')) {
    executeFileImport(file)
    return
  }
  const reader = new FileReader()
  reader.onload = (ev) => {
    const text = ev.target.result
    parseCsv(text)
  }
  reader.readAsText(file, 'Shift_JIS')
}

const parseCsv = (text) => {
  const lines = text.split(/\r?\n/).filter(l => l.trim())
  if (lines.length < 2) return

  const headerCols = lines[0].split(',').map(h => h.trim())
  const headerIndex = {}
  headerCols.forEach((name, idx) => {
    headerIndex[name] = idx
  })

  const getValue = (cols, name, fallbackIndex = -1) => {
    const idx = Object.prototype.hasOwnProperty.call(headerIndex, name) ? headerIndex[name] : fallbackIndex
    if (idx < 0) return ''
    return String(cols[idx] || '').trim()
  }

  const rows = lines.slice(1)
  const seen = new Set()
  const result = []

  for (const line of rows) {
    const cols = line.split(',')
    const productName = getValue(cols, '品名規格', 0)
    const productCode = getValue(cols, '構成品番', 1)
    const categoryRaw = getValue(cols, '品番区分名', 2)
    const lineCode = getValue(cols, 'ライン情報', 3)
    const processCode = getValue(cols, '工程情報', 4)
    const nextProcessCode = getValue(cols, '後工程', 5)
    const managementUnitRaw = getValue(cols, '管理区分', 6)
    const isFinalProductRaw = getValue(cols, '最終品', 7)
    const isLineFinalProductRaw = getValue(cols, 'ライン最終品', 8)
    if (!productCode) continue
    if (seen.has(productCode)) continue
    seen.add(productCode)
    result.push({
      product_code: productCode,
      product_name: productName,
      category_raw: categoryRaw,
      line_code: lineCode,
      process_code: processCode,
      next_process_code: nextProcessCode,
      management_unit_raw: managementUnitRaw,
      is_final_product_raw: isFinalProductRaw,
      is_line_final_product_raw: isLineFinalProductRaw,
    })
  }
  csvPreviewRows.value = result
  csvImportResult.value = null
}

const executeCsvImport = async () => {
  if (csvImporting.value) return
  csvImporting.value = true
  try {
    const items = csvPreviewRows.value.map(row => ({
      product_code: row.product_code,
      product_name: row.product_name,
      category: row.category_raw,
      line_code: row.line_code,
      process_code: row.process_code,
      next_process_code: row.next_process_code,
      management_unit: row.management_unit_raw,
      is_final_product: row.is_final_product_raw,
      is_line_final_product: row.is_line_final_product_raw,
    }))
    const res = await api.products.bulkImport(items)
    csvImportResult.value = res.data
  } catch (error) {
    console.error('CSVインポートエラー:', error)
    alert('インポートに失敗しました')
  } finally {
    csvImporting.value = false
  }
}

const executeFileImport = async (file) => {
  if (csvImporting.value) return
  csvImporting.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await api.products.importFile(fd)
    csvImportResult.value = res.data
    csvPreviewRows.value = []
  } catch (error) {
    console.error('Excelインポートエラー:', error)
    const detail = error?.response?.data?.detail || 'インポートに失敗しました'
    alert(detail)
  } finally {
    csvImporting.value = false
  }
}

// 統合取込
const showUpdateImportDialog = ref(false)
const updateImportPreview = ref(null)
const updateImportDone = ref(false)
const updateImporting = ref(false)
const updateImportFile = ref(null)
const appendGOnImport = ref(false)

const downloadUpdateImportTemplateXlsx = async () => {
  try {
    const res = await api.products.downloadUpdateImportTemplateXlsx()
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'product_update_template.xlsx'
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('統合テンプレートExcel取得エラー:', error)
    alert('テンプレートExcelの取得に失敗しました')
  }
}

const openUpdateImport = () => {
  updateImportPreview.value = null
  updateImportDone.value = false
  updateImportFile.value = null
  appendGOnImport.value = false
  showUpdateImportDialog.value = true
}

const closeUpdateImport = () => {
  showUpdateImportDialog.value = false
  if (updateImportDone.value) {
    fetchProducts(1)
  }
}

const onUpdateFileSelected = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  if (updateImporting.value) return
  updateImporting.value = true
  updateImportPreview.value = null
  updateImportDone.value = false
  updateImportFile.value = file
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await api.products.bulkUpdateImport(fd, { dryRun: true, appendG: appendGOnImport.value })
    updateImportPreview.value = res.data
  } catch (error) {
    console.error('統合取込プレビューエラー:', error)
    const detail = error?.response?.data?.detail || '統合取込のプレビューに失敗しました'
    alert(detail)
    updateImportFile.value = null
  } finally {
    updateImporting.value = false
    if (e?.target) e.target.value = ''
  }
}

const executeUpdateImport = async () => {
  if (updateImporting.value || !updateImportFile.value) return
  updateImporting.value = true
  try {
    const fd = new FormData()
    fd.append('file', updateImportFile.value)
    const res = await api.products.bulkUpdateImport(fd, { appendG: appendGOnImport.value })
    updateImportPreview.value = res.data
    updateImportDone.value = true
    updateImportFile.value = null
  } catch (error) {
    console.error('統合取込エラー:', error)
    const detail = error?.response?.data?.detail || '統合取込に失敗しました'
    alert(detail)
  } finally {
    updateImporting.value = false
  }
}

// ライン最終品一括設定
const showLineFinalDialog = ref(false)
const lfSelectedLine = ref('')
const lfLineGroups = ref([])
const lfChanges = ref({})  // product_id -> boolean
const lfSaving = ref(false)

const computedUnitWeight = computed(() => {
  const sg = formData.value.specific_gravity
  const sl = formData.value.size_length
  const sw = formData.value.size_width
  const st = formData.value.size_thickness
  if (sg && sl && sw && st) {
    return (sg * sl * sw * st) / 1_000_000
  }
  return null
})

// 品名から T{厚さ}X{縦}X{横} を解析して自動入力
const parseSizeFromName = (name) => {
  if (!name) return
  // T4.5X1219X2550 形式、または SPHC-P 1.6X1219X1219 のようなスペース区切り形式に対応
  const match = String(name).match(/(?:T|[ ])(\d+(?:\.\d+)?)X(\d+(?:\.\d+)?)X(\d+(?:\.\d+)?)/i)
  if (match) {
    formData.value.size_thickness = parseFloat(match[1])
    formData.value.size_length = parseFloat(match[2])
    formData.value.size_width = parseFloat(match[3])
  }
}

watch(() => formData.value.product_name, (newVal) => {
  // 未入力のときのみ自動補完（手動入力を上書きしない）
  if (!formData.value.size_thickness && !formData.value.size_length && !formData.value.size_width) {
    parseSizeFromName(newVal)
  }
})

const totalPages = computed(() => {
  if (totalCount.value === 0) return 1
  return Math.ceil(totalCount.value / pageSize.value)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const windowSize = 2
  const start = Math.max(1, current - windowSize)
  const end = Math.min(total, current + windowSize)
  const pages = []
  for (let i = start; i <= end; i += 1) {
    pages.push(i)
  }
  return pages
})

const pageRangeLabel = computed(() => {
  if (totalCount.value === 0) return '0件'
  const start = (currentPage.value - 1) * pageSize.value + 1
  const end = Math.min(currentPage.value * pageSize.value, totalCount.value)
  return `${totalCount.value}件中 ${start}-${end}件`
})

const showCustomerFilter = computed(() => filters.value.is_final_product === 'true')

const productGroupMap = computed(() => {
  const map = new Map()
  for (const group of productGroups.value) {
    map.set(group.id, group)
  }
  return map
})

const containerMap = computed(() => {
  const map = new Map()
  for (const container of containers.value) {
    map.set(container.id, container)
  }
  return map
})

const getProductGroupLabel = (groupId) => {
  if (!groupId) return '-'
  const group = productGroupMap.value.get(groupId)
  return group ? `${group.group_code} - ${group.group_name}` : '-'
}

const getContainerLabel = (containerId) => {
  if (!containerId) return '-'
  const container = containerMap.value.get(containerId)
  return container ? formatContainerOption(container) : '-'
}

const formatContainerOption = (container) => {
  if (!container) return ''
  if (container.capacity) {
    return `${container.name} (${container.capacity})`
  }
  return container.name
}

const formatProductContainerSelectOption = (container) => {
  if (!container) return ''
  const existing = productContainers.value.find((pc) => pc.container_id === container.id)
  if (existing) {
    return `${container.name}（現在: ${existing.capacity}）`
  }
  return container.name
}

const newContainerId = ref(null)
const newContainerCapacity = ref(1)

const selectedProductContainer = computed(() => (
  productContainers.value.find((pc) => pc.container_id === Number(newContainerId.value))
))

const productContainerActionLabel = computed(() => (
  selectedProductContainer.value ? '更新' : '+ 追加'
))

const addProductContainer = async () => {
  if (!newContainerId.value || !processTargetId.value) return
  try {
    const res = await api.products.addContainer(processTargetId.value, {
      container_id: newContainerId.value,
      capacity: newContainerCapacity.value || 1,
    })
    const existing = productContainers.value.find((pc) => pc.container_id === res.data.container_id)
    if (existing) {
      Object.assign(existing, res.data)
    } else {
      productContainers.value.push(res.data)
    }
    newContainerId.value = null
    newContainerCapacity.value = 1
  } catch (error) {
    alert(error?.response?.data?.detail || '容器追加に失敗しました')
  }
}

const removeProductContainer = async (pc) => {
  if (!processTargetId.value) return
  if (!confirm(`${pc.container_name} を削除しますか？`)) return
  try {
    await api.products.removeContainer(processTargetId.value, pc.id)
    productContainers.value = productContainers.value.filter((p) => p.id !== pc.id)
  } catch (error) {
    alert(error?.response?.data?.detail || '容器削除に失敗しました')
  }
}

const availableContainersForAdd = computed(() => {
  return containers.value
})

// クエリパラメータを組み立て
const buildQueryParams = () => {
  const params = {}
  if (filters.value.search.trim()) {
    params.search = filters.value.search.trim()
  }
  if (filters.value.category) {
    params.category = filters.value.category
  }
  if (filters.value.product_group) {
    params.product_group = filters.value.product_group
  }
  if (filters.value.is_final_product !== '') {
    params.is_final_product = filters.value.is_final_product === 'true'
  }
  if (filters.value.is_final_product === 'true' && filters.value.customer_code) {
    params.customer_code = filters.value.customer_code
  }
  if (filters.value.is_line_final_product !== '') {
    params.is_line_final_product = filters.value.is_line_final_product === 'true'
  }
  if (filters.value.has_bom !== '') {
    params.has_bom = filters.value.has_bom === 'true'
  }
  if (filters.value.is_active !== '') {
    params.is_active = filters.value.is_active === 'true'
  }
  if (filters.value.process) {
    params.process = filters.value.process
  }
  if (filters.value.processing_area) {
    params.processing_area = filters.value.processing_area
  }
  if (filters.value.stock_location.trim()) {
    params.stock_location = filters.value.stock_location.trim()
  }
  if (filters.value.next_process === '__none__') {
    params.next_process_unset = true
  } else if (filters.value.next_process) {
    params.next_process = filters.value.next_process
  }
  if (filters.value.created_from) {
    params.created_from = filters.value.created_from
  }
  if (filters.value.created_to) {
    params.created_to = filters.value.created_to
  }
  return params
}

// 製品取得
const fetchProducts = async (page = 1) => {
  try {
    const params = buildQueryParams()
    params.page = page
    params.page_size = pageSize.value
    const response = await api.products.getProducts(params)
    const data = response.data
    if (data?.results) {
      products.value = data.results
      totalCount.value = data.count ?? data.results.length
    } else {
      products.value = Array.isArray(data) ? data : []
      totalCount.value = products.value.length
    }
    currentPage.value = page
  } catch (error) {
    console.error('製品取得エラー:', error)
    alert('製品データの取得に失敗しました')
  }
}

const fetchLines = async () => {
  try {
    const response = await api.lines.getLines({ page_size: 500 })
    lines.value = response.data.results || response.data
  } catch (error) {
    console.error('ライン取得エラー:', error)
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

const fetchProductGroups = async () => {
  try {
    const response = await api.productGroups.getProductGroups()
    productGroups.value = response.data.results || response.data
  } catch (error) {
    console.error('製品グループ取得エラー:', error)
  }
}

const fetchSuppliers = async () => {
  try {
    const response = await api.suppliers.getSuppliers({ page_size: 1000, ordering: 'supplier_code' })
    suppliers.value = response.data.results || response.data
  } catch (error) {
    console.error('仕入先取得エラー:', error)
  }
}

const fetchContainers = async () => {
  try {
    const response = await api.containerCapacities.getContainerCapacities()
    containers.value = response.data.results || response.data
  } catch (error) {
    console.error('容器取得エラー:', error)
  }
}

const fetchCustomers = async () => {
  try {
    const response = await api.customers.getCustomers()
    customers.value = response.data.results || response.data
  } catch (error) {
    console.error('得意先取得エラー:', error)
  }
}

const openProcessTab = (mode = 'create', product = null) => {
  if (mode !== 'view' && !canEdit.value) return
  activeTab.value = 'process'
  processMode.value = mode
  if (mode === 'create') {
    processTargetId.value = null
    copySourceProduct.value = product
    formData.value = product ? mapProductToFormData(product, { asCopy: true }) : createEmptyFormData()
    return
  }
  copySourceProduct.value = null
  processTargetId.value = product?.id ?? null
  formData.value = product ? mapProductToFormData(product) : createEmptyFormData()
  productContainers.value = []
  if (product?.id) {
    api.products.listContainers(product.id).then((res) => {
      productContainers.value = Array.isArray(res.data) ? res.data : []
    }).catch(() => {})
  }
}

const openExportTab = () => {
  activeTab.value = 'export'
}

const changeProcessMode = (mode) => {
  if (mode !== 'view' && !canEdit.value) return
  processMode.value = mode
  copySourceProduct.value = null
  if (mode === 'create') {
    processTargetId.value = null
    formData.value = createEmptyFormData()
    productContainers.value = []
    return
  }
  if (!processTargetId.value) {
    formData.value = createEmptyFormData()
  }
}

const loadProcessTarget = async () => {
  const targetId = Number(processTargetId.value || 0)
  if (!targetId) {
    formData.value = createEmptyFormData()
    return
  }
  try {
    const [response, pcRes] = await Promise.all([
      api.products.getProduct(targetId),
      api.products.listContainers(targetId),
    ])
    processTargetId.value = targetId
    formData.value = mapProductToFormData(response.data)
    productContainers.value = Array.isArray(pcRes.data) ? pcRes.data : []
  } catch (error) {
    console.error('製品詳細取得エラー:', error)
    alert('製品データの取得に失敗しました')
  }
}

const resetProcessForm = () => {
  if (processMode.value === 'create') {
    formData.value = createEmptyFormData()
    return
  }
  if (processTargetId.value) {
    void loadProcessTarget()
  } else {
    formData.value = createEmptyFormData()
  }
}

// コピーして新規作成タブを表示
const copyProduct = (product) => {
  if (!canEdit.value) return
  openProcessTab('create', product)
}

// 変更タブ表示
const editProduct = (product) => {
  if (!canEdit.value) return
  openProcessTab('edit', product)
}

// 照会タブ表示
const viewProduct = (product) => {
  openProcessTab('view', product)
}

// フィルタリセット
const resetFilters = async () => {
  filters.value = {
    search: '',
    category: '',
    product_group: '',
    is_final_product: '',
    is_line_final_product: '',
    has_bom: '',
    customer_code: '',
    is_active: '',
    process: '',
    processing_area: '',
    stock_location: '',
    next_process: '',
    created_from: '',
    created_to: ''
  }
  await fetchProducts(1)
}

const buildExportQueryParams = () => {
  const params = {}
  if (exportFilters.value.line) {
    params.line = exportFilters.value.line
  }
  if (exportFilters.value.process) {
    params.process = exportFilters.value.process
  }
  if (exportFilters.value.supplier_code) {
    params.supplier_code = exportFilters.value.supplier_code
  }
  if (exportFilters.value.transfer_destination) {
    params.transfer_destination = exportFilters.value.transfer_destination
  }
  return params
}

const mapProductToExportRow = (product) => ({
  構成品番: product.product_code || '',
  品名規格: product.product_name || '',
  品番区分名: toTemplateCategoryLabel(product.category),
  単位: product.unit || '',
  単価: product.unit_price ?? '',
  標準LT: product.standard_lt_days ?? '',
  自工程LT: product.self_lt_days ?? '',
  ライン情報: product.line_code || '',
  ライン名: product.line_name || '',
  工程情報: product.process_code || '',
  工程名: product.process_name || '',
  後工程: product.next_process_code || '',
  後工程名: product.next_process_name || '',
  管理区分: product.management_unit === 'DAY' ? '日' : product.management_unit === 'MINUTE' ? '分' : '',
  最終品: yesNoLabel(product.is_final_product),
  ライン最終品: yesNoLabel(product.is_line_final_product),
  機種名: product.model_name || '',
  識別記号: product.identification_code || '',
  製品グループ: getProductGroupCode(product.product_group),
  移動先: getTransferDestLabel(product.transfer_destination) === '-' ? '' : getTransferDestLabel(product.transfer_destination),
  比重: product.specific_gravity ?? '',
  縦: product.size_length ?? '',
  横: product.size_width ?? '',
  厚さ: product.size_thickness ?? '',
  発注倍数: product.order_lot_multiple ?? '',
  最小発注数: product.order_lot_min ?? '',
  容器入り数: product.capacity ?? '',
  使用容器: getContainerCode(product.used_container),
  置き場1: getStockLocationByIndex(product, 0),
  置き場2: getStockLocationByIndex(product, 1),
  置き場3: getStockLocationByIndex(product, 2),
  置き場4: getStockLocationByIndex(product, 3),
})

const loadExportProducts = async () => {
  const params = buildExportQueryParams()
  const response = await api.products.getExportPreview(params)
  return Array.isArray(response.data) ? response.data : []
}

const previewProductExport = async () => {
  exportLoading.value = true
  try {
    const rows = await loadExportProducts()
    exportResultCount.value = rows.length
    exportPreviewRows.value = rows.slice(0, 20)
  } catch (error) {
    console.error('製品出力プレビューエラー:', error)
    alert('製品出力データの取得に失敗しました')
  } finally {
    exportLoading.value = false
  }
}

const exportProductsToExcel = async () => {
  exporting.value = true
  try {
    const rows = await loadExportProducts()
    exportResultCount.value = rows.length
    exportPreviewRows.value = rows.slice(0, 20)
    if (!rows.length) {
      alert('出力対象がありません')
      return
    }
    const worksheet = XLSX.utils.json_to_sheet(rows.map(mapProductToExportRow))
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '製品')

    const processSheet = XLSX.utils.json_to_sheet(
      processes.value.map((process) => ({
        工程コード: process.process_code || '',
        工程名: process.process_name || '',
      }))
    )
    XLSX.utils.book_append_sheet(workbook, processSheet, '工程')

    const lineSheet = XLSX.utils.json_to_sheet(
      lines.value.map((line) => ({
        ラインコード: line.line_code || '',
        ライン名: line.line_name || '',
      }))
    )
    XLSX.utils.book_append_sheet(workbook, lineSheet, 'ライン')

    const productGroupSheet = XLSX.utils.json_to_sheet(
      productGroups.value.map((group) => ({
        グループコード: group.group_code || '',
        グループ名: group.group_name || '',
      }))
    )
    XLSX.utils.book_append_sheet(workbook, productGroupSheet, '製品グループ')

    const containerSheet = XLSX.utils.json_to_sheet(
      containers.value.map((container) => ({
        容器コード: container.container_code || '',
        容器名: container.name || '',
      }))
    )
    XLSX.utils.book_append_sheet(workbook, containerSheet, '容器')

    XLSX.writeFile(workbook, 'product_export.xlsx')
  } catch (error) {
    console.error('製品Excel出力エラー:', error)
    alert('Excel出力に失敗しました')
  } finally {
    exporting.value = false
  }
}

const resetExportFilters = () => {
  exportFilters.value = {
    line: '',
    process: '',
    supplier_code: '',
    transfer_destination: '',
  }
  exportPreviewRows.value = []
  exportResultCount.value = 0
}

const normalizeNumber = (value) => {
  if (value === '' || value === null || Number.isNaN(value)) return null
  return value
}

// 保存
const saveProduct = async () => {
  if (!canEdit.value || isViewMode.value) return
  if (processMode.value !== 'create' && !formData.value.id) {
    alert('対象品番を選択してください')
    return
  }
  try {
    const payload = {
      ...formData.value,
      model_name: formData.value.model_name || null,
      product_group: formData.value.product_group || null,
      used_container: formData.value.used_container || null,
      transfer_destination: formData.value.transfer_destination || null,
      processing_area: formData.value.processing_area || null,
      stock_location: (formData.value.stock_locations_edit.find(s => s.trim()) || '').trim(),
      standard_lt_days: normalizeNumber(formData.value.standard_lt_days),
      order_lot_min: normalizeNumber(formData.value.order_lot_min),
      order_lot_multiple: Math.max(1, Number(formData.value.order_lot_multiple || 1)),
      self_lt_days: normalizeNumber(formData.value.self_lt_days),
      capacity: normalizeNumber(formData.value.capacity),
      specific_gravity: normalizeNumber(formData.value.specific_gravity),
      size_length: normalizeNumber(formData.value.size_length),
      size_width: normalizeNumber(formData.value.size_width),
      size_thickness: normalizeNumber(formData.value.size_thickness),
      unit_price: normalizeNumber(formData.value.unit_price),
    }
    delete payload.stock_locations_edit
    delete payload.stock_locations_list
    const locationsPayload = formData.value.stock_locations_edit.filter(s => s.trim()).map(s => ({ location_name: s.trim() }))
    if (processMode.value === 'edit') {
      await api.products.updateProduct(payload.id, payload)
      await api.products.setStockLocations(payload.id, locationsPayload)
      alert('更新しました')
    } else {
      const response = await api.products.createProduct(payload)
      const created = response?.data
      if (created?.id) {
        await api.products.setStockLocations(created.id, locationsPayload)
        processMode.value = 'edit'
        processTargetId.value = created.id
        formData.value = mapProductToFormData(created)
      }
      alert('作成しました')
    }
    await fetchProducts(currentPage.value)
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const triggerFileInput = () => {
  if (!canEdit.value || isViewMode.value) return
  if (fileInput.value) {
    fileInput.value.click()
  }
}

const onFileSelected = async (e) => {
  if (!canEdit.value || isViewMode.value) return
  const file = e.target.files && e.target.files[0]
  if (!file) return
  if (!formData.value.id) {
    alert('先に保存してからアップロードしてください。')
    return
  }
  try {
    const fd = new FormData()
    fd.append('file', file)
    const res = await api.products.uploadProductImage(formData.value.id, fd)
    formData.value.image_url = res.data.image_url || ''
    alert('画像をアップロードしました')
  } catch (error) {
    console.error('画像アップロードエラー:', error)
    alert('画像のアップロードに失敗しました')
  } finally {
    if (fileInput.value) fileInput.value.value = ''
  }
}

// 削除
const deleteProduct = async (id) => {
  if (!canEdit.value) return
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.products.deleteProduct(id)
    await fetchProducts()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

const changePage = async (page) => {
  const target = Math.min(Math.max(page, 1), totalPages.value)
  if (target === currentPage.value) return
  await fetchProducts(target)
}

// ライン最終品一括設定
const openLineFinalDialog = async () => {
  if (!canEdit.value) return
  lfSelectedLine.value = ''
  showLineFinalDialog.value = true
  await fetchLineFinalCandidates()
}

const fetchLineFinalCandidates = async () => {
  try {
    const lineId = lfSelectedLine.value || null
    const response = await api.products.getLineFinalCandidates(lineId)
    lfLineGroups.value = response.data
    // 現在の値でチェックボックス初期化
    const changes = {}
    for (const group of response.data) {
      for (const product of group.products) {
        changes[product.id] = product.is_line_final_product
      }
    }
    lfChanges.value = changes
  } catch (error) {
    console.error('ライン最終品候補取得エラー:', error)
    alert('データの取得に失敗しました')
  }
}

const saveLineFinal = async () => {
  if (!canEdit.value) return
  lfSaving.value = true
  try {
    const updates = Object.entries(lfChanges.value).map(([id, val]) => ({
      id: Number(id),
      is_line_final_product: val,
    }))
    const response = await api.products.bulkUpdateLineFinal(updates)
    alert(`${response.data.updated}件 更新しました`)
    showLineFinalDialog.value = false
    await fetchProducts(currentPage.value)
  } catch (error) {
    console.error('一括更新エラー:', error)
    alert('保存に失敗しました')
  } finally {
    lfSaving.value = false
  }
}

onMounted(() => {
  fetchProducts(1)
  fetchLines()
  fetchProcesses()
  fetchSuppliers()
  fetchProductGroups()
  fetchContainers()
  fetchCustomers()
})

watch(
  () => formData.value.process,
  (processId) => {
    const selectedProcess = processes.value.find((proc) => `${proc.id}` === `${processId}`)
    if (!selectedProcess) return
    if (selectedProcess.line != null && selectedProcess.line !== '') {
      formData.value.line = selectedProcess.line
    }
  }
)

watch(
  () => filters.value.is_final_product,
  (value) => {
    if (value !== 'true') {
      filters.value.customer_code = ''
    }
  }
)
</script>

<style scoped>
.page-container {
  height: 100%;
}

.master-tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.master-tab-btn {
  padding: 6px 14px;
  border: 1px solid #cbd5e1;
  border-bottom: 2px solid #94a3b8;
  border-radius: 6px 6px 0 0;
  background: #f8fafc;
  color: #334155;
  cursor: pointer;
}

.master-tab-btn.active {
  background: #ffffff;
  color: #0f172a;
  border-bottom-color: #2563eb;
  font-weight: 700;
}

.page-content {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.process-page-content {
  overflow: auto;
  gap: 12px;
}

.export-page-content {
  overflow: auto;
}

.export-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.export-filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px 12px;
  align-items: end;
}

.export-actions {
  margin-top: 0;
}

.export-summary {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  font-size: 13px;
  color: #475569;
}

.export-preview-area {
  max-height: 520px;
}

.process-mode-panel {
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 12px;
}

.process-mode-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.process-mode-label {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.mode-option {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #1f2937;
}

.process-target-row {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.process-target-row label {
  font-size: 12px;
  color: #555;
}

.process-target-row select {
  min-width: 360px;
  max-width: 520px;
  height: 34px;
  box-sizing: border-box;
  padding: 0.35rem 0.45rem;
  font-size: 0.9rem;
}

.process-target-row .btn-secondary {
  height: 34px;
  padding: 0 12px;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
}

.process-form-card {
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px;
}

.process-form-card h2 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #111827;
}

.process-form-fieldset {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.process-section {
  border: 1px solid #dbe3ec;
  border-left-width: 6px;
  border-radius: 6px;
  padding: 8px;
  background: #fbfdff;
}

.section-basic-info {
  background: #fcfdf7;
  border-color: #d9e7c1;
  border-left-color: #7aa341;
}

.section-process-info {
  background: #f7fbff;
  border-color: #cfe0f3;
  border-left-color: #4b86c5;
}

.section-status-info {
  background: #fffaf3;
  border-color: #f0dcc0;
  border-left-color: #d28b2d;
}

.section-image-info {
  background: #faf7ff;
  border-color: #ddd1f4;
  border-left-color: #8b63c7;
}

.process-section-title {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
}

.process-section-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px 12px;
  align-items: end;
}

.process-section-grid-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.process-section-grid-4 {
  grid-template-columns: repeat(8, minmax(0, 1fr));
}

.process-section-grid-5 {
  grid-template-columns: repeat(8, minmax(0, 1fr));
}

.process-form-layout {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.process-subsection {
  border: 1px solid #e5e7eb;
  border-left-width: 6px;
  border-radius: 6px;
  padding: 8px;
  background: #ffffff;
}

.subsection-product-basic {
  background: #fffdf2;
  border-color: #eadf9d;
  border-left-color: #c4a62a;
}

.subsection-procurement {
  background: #f7fcf7;
  border-color: #cae6cc;
  border-left-color: #4ea463;
}

.subsection-container-setting {
  background: #f7fbff;
  border-color: #cfe0f3;
  border-left-color: #4c8fd1;
}

.subsection-material-info {
  background: #f6fcfb;
  border-color: #c9e7df;
  border-left-color: #2c9a89;
}

.process-subsection-title {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.container-setting-guide {
  margin-bottom: 8px;
  padding: 8px 10px;
  border: 1px solid #dbe3ec;
  border-radius: 6px;
  background: #f8fafc;
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
}

.container-setting-guide-item + .container-setting-guide-item {
  margin-top: 4px;
}

.container-setting-guide-inline {
  min-height: 92px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.process-group-full {
  grid-column: 1 / -1;
}

.process-group-span-2 {
  grid-column: span 2;
}

.process-form-card .form-group {
  margin-bottom: 0;
}

.process-check-grid {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 8px 10px;
  align-items: start;
  padding: 2px 0;
}

.process-check-grid label {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 13px;
  line-height: 1.5;
  padding: 5px 7px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #ffffff;
}

.process-form-card .form-group label {
  margin-bottom: 0.25rem;
  line-height: 1.2;
}

.process-form-card .form-group > input:not([type="checkbox"]):not([type="file"]),
.process-form-card .form-group > select {
  width: 100%;
  box-sizing: border-box;
  height: 34px;
  padding: 0.35rem 0.45rem;
  font-size: 0.9rem;
}

.process-form-card .form-group input[type="checkbox"] {
  margin-right: 0.35rem;
}

.process-form-card .form-actions {
  margin-top: 4px;
}

.form-fieldset {
  border: 0;
  margin: 0;
  padding: 0;
  min-width: 0;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
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
  margin-bottom: 2px;
}

.filter-bar .filter-field > input,
.filter-bar .filter-field > select {
  width: 100%;
  box-sizing: border-box;
  height: 34px;
  padding: 0.35rem 0.45rem;
  font-size: 0.9rem;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.filter-actions button {
  height: 34px;
  padding: 0 12px;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
}

.list-area {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.data-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
}

.pagination-area {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pagination {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pagination-btn {
  padding: 4px 10px;
  border: 1px solid #d1d5db;
  background-color: #fff;
  color: #374151;
  border-radius: 4px;
  cursor: pointer;
}

.pagination-btn.is-active {
  background-color: #1f2937;
  border-color: #1f2937;
  color: #fff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 12px;
  color: #6b7280;
}
.stock-locations-edit { display: flex; flex-direction: column; gap: 6px; }
.stock-loc-row { display: flex; gap: 6px; align-items: center; }
.stock-loc-row input { flex: 1; }
.pc-container-label { min-width: 60px; font-size: 12px; }
.pc-capacity-input { width: 72px; text-align: right; }
.pc-add-select { flex: 1; min-width: 0; max-width: none; }
.product-container-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.product-container-box {
  border: 1px solid #dbe3ec;
  border-left-width: 6px;
  border-radius: 6px;
  background: #f8fafc;
  padding: 8px;
}

.product-container-box-standard {
  background: #f9f8ff;
  border-color: #d8cff8;
  border-left-color: #7b5dc9;
}

.product-container-box-temporary {
  background: #fff8f1;
  border-color: #efd5bb;
  border-left-color: #d18a3c;
}

.product-container-box-nested {
  background: #ffffff;
  padding: 8px;
}

.product-container-box-current {
  background: #f8fbff;
  border-color: #d8e5f3;
  border-left-color: #5d95c9;
}

.product-container-box-edit {
  background: #fffef7;
  border-color: #eee0b0;
  border-left-color: #c7a72c;
}
.product-container-box-title {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #334155;
}

.product-container-box-note {
  margin-left: 8px;
  font-size: 11px;
  font-weight: 400;
  color: #64748b;
}
.product-container-editor-row {
  align-items: stretch;
}
.product-container-editor-row .btn-sm {
  white-space: nowrap;
}
.product-container-readonly-row {
  justify-content: space-between;
  padding: 4px 6px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #f8fafc;
}
.product-container-readonly-value {
  min-width: 40px;
  text-align: right;
  font-weight: 700;
  color: #0f172a;
}
.product-container-empty {
  padding: 8px 6px;
  color: #64748b;
  font-size: 12px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 4px;
}

.stock-location-add-btn {
  align-self: flex-start;
}

@media (max-width: 1200px) {
  .process-section-grid-4,
  .process-section-grid-5 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .process-check-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .process-section-grid,
  .process-section-grid-2,
  .process-section-grid-4,
  .process-section-grid-5 {
    grid-template-columns: 1fr;
  }

  .process-group-span-2 {
    grid-column: auto;
  }

  .product-container-editor-row {
    flex-direction: column;
  }

  .pc-capacity-input,
  .product-container-editor-row .btn-sm {
    width: 100%;
  }
}
</style>

<style scoped>
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

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
}

.form-group {
  margin-bottom: 1rem;
}
.form-group .field-note {
  display: block;
  margin-top: 4px;
  color: #888;
  font-size: 11px;
  line-height: 1.4;
}
.material-lock-note {
  margin-bottom: 8px;
}
.material-info-fieldset:disabled {
  opacity: 0.75;
}
.form-group-section {
  font-size: 12px;
  font-weight: 700;
  color: #0f766e;
  background: #f0fdf4;
  border-left: 3px solid #0f766e;
  padding: 4px 8px;
  margin-bottom: 8px;
}
.computed-value {
  padding: 6px 8px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}
.upload-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hint-small {
  font-size: 12px;
  color: #64748b;
}
.image-preview img {
  max-height: 120px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  margin-top: 6px;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

.form-group input[type="text"],
.form-group input[type="number"],
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

/* ライン最終品一括設定モーダル */
.line-final-modal {
  min-width: 700px;
  max-width: 900px;
}

.lf-filter-bar {
  margin-bottom: 16px;
}

.lf-lines-area {
  max-height: 60vh;
  overflow-y: auto;
}

.lf-line-group {
  margin-bottom: 20px;
}

.lf-line-header {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  background-color: #f3f4f6;
  padding: 6px 10px;
  border-radius: 4px;
  margin: 0 0 4px 0;
}

.lf-table {
  font-size: 13px;
}

.lf-table td,
.lf-table th {
  padding: 4px 8px;
}

/* CSVインポートモーダル */
.csv-import-modal {
  min-width: 700px;
  max-width: 900px;
}

.csv-format-note {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 4px;
  padding: 8px 12px;
  font-size: 12px;
  color: #0369a1;
  margin-bottom: 16px;
  line-height: 1.6;
}

.csv-preview-area {
  margin: 12px 0;
  max-height: 50vh;
  overflow-y: auto;
}

.csv-preview-header {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 6px;
}

.csv-preview-table {
  font-size: 12px;
}

.csv-preview-table td,
.csv-preview-table th {
  padding: 3px 8px;
}

.csv-result-area {
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 4px;
  padding: 8px 12px;
  margin: 12px 0;
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  align-items: center;
}

.result-created {
  font-weight: 700;
  color: #166534;
}

.result-skipped {
  color: #6b7280;
}

.skipped-codes {
  width: 100%;
  font-size: 11px;
  color: #9ca3af;
  word-break: break-all;
}
</style>
