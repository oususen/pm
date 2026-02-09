<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">構成部品在庫一覧</h2>
        <p class="subtitle">親製品のBOMを展開し、全ての子部品の在庫・計画在庫を表示します。</p>
      </div>
      <div class="page-actions">
        <input
          type="text"
          v-model="productSearch"
          placeholder="品番/品名で検索"
          @keyup.enter="onSearchEnter"
        />
        <button @click="searchProducts" :disabled="loading">検索</button>
      </div>
    </div>

    <!-- フィルター行 -->
    <div class="filter-row">
      <div class="filter-item">
        <label>開始日</label>
        <input type="date" v-model="startDate" />
      </div>
      <div class="filter-item">
        <label>期間</label>
        <select v-model.number="horizon">
          <option :value="7">7日</option>
          <option :value="15">15日</option>
          <option :value="30">30日</option>
          <option :value="60">60日</option>
        </select>
      </div>
      <div class="filter-item">
        <label>区分</label>
        <select v-model="sourcingFilter">
          <option value="">すべて</option>
          <option value="MAKE">製造</option>
          <option value="BUY">購買</option>
          <option value="SUBCON">外注</option>
        </select>
      </div>
      <div class="filter-item filter-negative">
        <label>
          <input type="checkbox" v-model="negativeOnly" />
          マイナスのみ
        </label>
        <input
          v-if="negativeOnly"
          type="date"
          v-model="negativeFromDate"
          placeholder="いつから"
          class="negative-date"
        />
      </div>
      <button @click="loadComponentInventory" :disabled="loading || !selectedProduct">更新</button>
    </div>

    <!-- 製品選択ドロップダウン -->
    <div v-if="searchResults.length > 0" class="search-results">
      <div class="search-result-header">検索結果 ({{ searchResults.length }}件)</div>
      <div
        v-for="p in searchResults"
        :key="p.id"
        class="search-result-item"
        :class="{ selected: selectedProduct?.id === p.id }"
        @click="selectProduct(p)"
      >
        <span class="product-code">{{ p.product_code }}</span>
        <span class="product-name">{{ p.product_name }}</span>
      </div>
    </div>

    <!-- 選択された親製品 -->
    <div v-if="selectedProduct" class="selected-product">
      <strong>親製品:</strong>
      {{ selectedProduct.product_code }} - {{ selectedProduct.product_name }}
    </div>

    <div v-if="loading" class="loading">読込中...</div>
    <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
    <div v-else-if="!selectedProduct" class="no-data">
      品番を検索して親製品を選択してください
    </div>
    <div v-else-if="bomTree.length === 0 && dataLoaded" class="no-data">
      BOMが登録されていません
    </div>
    <div v-else-if="filteredBomTree.length === 0 && bomTree.length > 0" class="no-data">
      条件に一致する部品がありません
    </div>
    <div v-else-if="filteredBomTree.length > 0" class="table-section">
      <div class="result-count">{{ filteredBomTree.length }}件 / {{ bomTree.length }}件</div>
      <div class="grid-wrapper">
        <table class="inventory-grid" :style="{ minWidth: tableMinWidth + 'px' }">
          <thead>
            <tr>
              <th class="tree-col">階層</th>
              <th class="code-col">品番</th>
              <th class="name-col">品名</th>
              <th class="type-col">区分</th>
              <th class="dest-col">加工先</th>
              <th class="qty-col">BOM数量</th>
              <th class="rowtype-col">項目</th>
              <th v-for="d in columns" :key="d" class="date-col">{{ formatDateShort(d) }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(item, idx) in filteredBomTree" :key="idx">
              <!-- 在庫行 -->
              <tr class="row-stock">
                <td class="tree-col">{{ item.treePrefix }}</td>
                <td class="code-col">{{ item.product_code }}</td>
                <td class="name-col">{{ item.product_name }}</td>
                <td class="type-col">{{ formatSourcingType(item.sourcing_type) }}</td>
                <td class="dest-col">{{ formatDestination(item) }}</td>
                <td class="qty-col">{{ item.quantity }}</td>
                <td class="rowtype-col">在庫</td>
                <td
                  v-for="d in columns"
                  :key="`stock-${d}`"
                  class="date-col"
                  :class="{ negative: getStockValue(item, d, 'stock') < 0 }"
                >
                  {{ fmt(getStockValue(item, d, 'stock')) }}
                </td>
              </tr>
              <!-- 計画在庫行 -->
              <tr class="row-planned">
                <td class="tree-col"></td>
                <td class="code-col"></td>
                <td class="name-col"></td>
                <td class="type-col"></td>
                <td class="dest-col"></td>
                <td class="qty-col"></td>
                <td class="rowtype-col">計画在庫</td>
                <td
                  v-for="d in columns"
                  :key="`planned-${d}`"
                  class="date-col"
                  :class="{ negative: getStockValue(item, d, 'planned') < 0 }"
                >
                  {{ fmt(getStockValue(item, d, 'planned')) }}
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import api from "@/api/client";
import { addDays, formatISODate } from "@/utils/dateUtil";

const productSearch = ref("");
const searchResults = ref([]);
const selectedProduct = ref(null);
const horizon = ref(15);
const startDate = ref(formatISODate(new Date()));
const sourcingFilter = ref("");
const negativeOnly = ref(false);
const negativeFromDate = ref("");
const loading = ref(false);
const error = ref("");
const bomTree = ref([]);
const inventoryData = ref({});
const dataLoaded = ref(false);

// 列幅定義
const W_TREE = 80;
const W_CODE = 120;
const W_NAME = 150;
const W_TYPE = 60;
const W_DEST = 150;
const W_QTY = 60;
const W_ROWTYPE = 70;
const W_DATE = 70;

const columns = computed(() => {
  const start = startDate.value ? new Date(startDate.value) : new Date();
  const cols = [];
  for (let i = 0; i < horizon.value; i++) {
    cols.push(formatISODate(addDays(start, i)));
  }
  return cols;
});

const tableMinWidth = computed(() => {
  const fixedColsWidth = W_TREE + W_CODE + W_NAME + W_TYPE + W_DEST + W_QTY + W_ROWTYPE;
  return fixedColsWidth + columns.value.length * W_DATE;
});

const hasNegativeStock = (item) => {
  const checkFromDate = negativeFromDate.value || columns.value[0];
  for (const d of columns.value) {
    if (d < checkFromDate) continue;
    const key = `${item.product_id}_${d}`;
    const data = inventoryData.value[key];
    if (data) {
      if (data.stock < 0 || data.planned < 0) return true;
    }
  }
  return false;
};

const filteredBomTree = computed(() => {
  let items = bomTree.value;
  if (sourcingFilter.value) {
    items = items.filter((item) => item.sourcing_type === sourcingFilter.value);
  }
  if (negativeOnly.value) {
    items = items.filter((item) => hasNegativeStock(item));
  }
  return items;
});

const searchProducts = async () => {
  if (!productSearch.value.trim()) {
    searchResults.value = [];
    return;
  }
  try {
    const res = await api.products.getProducts({ search: productSearch.value.trim() });
    searchResults.value = res.data?.results || res.data || [];
  } catch (e) {
    console.error("製品検索エラー:", e);
    searchResults.value = [];
  }
};

// 品番入力でEnter押下時に検索を実行（検索ボタンと同等）
const onSearchEnter = () => {
  if (loading.value) return;
  searchProducts();
};

const selectProduct = async (product) => {
  selectedProduct.value = product;
  searchResults.value = [];
  productSearch.value = "";
  bomTree.value = [];
  inventoryData.value = {};
  dataLoaded.value = false;
  await loadComponentInventory();
};

const loadComponentInventory = async () => {
  if (!selectedProduct.value) return;

  loading.value = true;
  error.value = "";
  bomTree.value = [];
  inventoryData.value = {};
  dataLoaded.value = false;

  try {
    const treeRes = await api.bomService.getBomTree(selectedProduct.value.id);
    const tree = treeRes.data;

    if (!tree || !tree.children || tree.children.length === 0) {
      dataLoaded.value = true;
      return;
    }

    const flatItems = flattenBomTree(tree.children, 0, "");
    const productIds = [...new Set(flatItems.map((item) => item.product_id))];

    const startDateVal = columns.value[0];
    const endDateVal = columns.value[columns.value.length - 1];

    const invRes = await api.lineBacklogs.getLineBacklogs({
      product__in: productIds.join(","),
      plan_date__gte: startDateVal,
      plan_date__lte: endDateVal,
    });
    const invData = invRes.data || [];

    const invMap = {};
    for (const d of invData) {
      const key = `${d.product}_${d.plan_date}`;
      if (!invMap[key]) {
        invMap[key] = { stock: 0, planned: 0 };
      }
      invMap[key].stock += Number(d.stock_qty || 0);
      invMap[key].planned += Number(d.planned_stock_qty || 0);
    }
    inventoryData.value = invMap;

    bomTree.value = flatItems;
    dataLoaded.value = true;
  } catch (e) {
    console.error("データ取得エラー:", e);
    error.value = e?.message || "データの取得に失敗しました";
  } finally {
    loading.value = false;
  }
};

const flattenBomTree = (children, level, parentPrefix) => {
  const result = [];
  children.forEach((child, idx) => {
    const isLast = idx === children.length - 1;
    const prefix = level === 0
      ? (isLast ? "└─" : "├─")
      : parentPrefix + (isLast ? "└─" : "├─");
    const childPrefix = level === 0
      ? (isLast ? "  " : "│ ")
      : parentPrefix + (isLast ? "  " : "│ ");

    result.push({
      product_id: child.product_id,
      product_code: child.product_code,
      product_name: child.product_name,
      sourcing_type: child.sourcing_type,
      quantity: child.quantity,
      level: level,
      treePrefix: prefix,
      line_id: child.line_id,
      line_code: child.line_code,
      line_name: child.line_name,
      process_id: child.process_id,
      process_code: child.process_code,
      process_name: child.process_name,
      supplier_id: child.supplier_id,
      supplier_code: child.supplier_code,
      supplier_name: child.supplier_name,
    });

    if (child.children && child.children.length > 0) {
      result.push(...flattenBomTree(child.children, level + 1, childPrefix));
    }
  });
  return result;
};

const getStockValue = (item, date, type) => {
  const key = `${item.product_id}_${date}`;
  const data = inventoryData.value[key];
  if (!data) return 0;
  return type === "stock" ? data.stock : data.planned;
};

const fmt = (n) => {
  if (n === null || n === undefined) return "";
  const num = Number(n);
  if (Number.isNaN(num)) return "";
  if (num === 0) return "";
  return num.toLocaleString();
};

const formatDateShort = (dateStr) => {
  if (!dateStr) return "";
  const parts = dateStr.split("-");
  if (parts.length < 3) return dateStr;
  return `${parseInt(parts[1])}/${parseInt(parts[2])}`;
};

const formatSourcingType = (type) => {
  const map = {
    MAKE: "製造",
    BUY: "購買",
    SUBCON: "外注",
  };
  return map[type] || type || "-";
};

const formatDestination = (item) => {
  if (!item) return "";
  const lineLabel = item.line_name || item.line_code
    ? `${item.line_code || ""}${item.line_code && item.line_name ? " " : ""}${item.line_name || ""}`.trim()
    : "";
  const supplierLabel = item.supplier_name || item.supplier_code
    ? `${item.supplier_code || ""}${item.supplier_code && item.supplier_name ? " " : ""}${item.supplier_name || ""}`.trim()
    : "";
  const processLabel = item.process_name || item.process_code
    ? `${item.process_code || ""}${item.process_code && item.process_name ? " " : ""}${item.process_name || ""}`.trim()
    : "";

  switch (item.sourcing_type) {
    case "BUY":
      return supplierLabel || lineLabel || processLabel;
    case "SUBCON":
      return lineLabel || supplierLabel || processLabel;
    default:
      return lineLabel || processLabel || supplierLabel;
  }
};
</script>

<style scoped>
.page-container {
  padding: 6px 8px 10px;
  background: #eef2f6;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}
.page-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.page-actions input,
.page-actions select {
  padding: 6px 8px;
}
.page-actions button {
  padding: 6px 12px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.subtitle {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.filter-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: #e1e8f4;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  margin-top: 6px;
}
.filter-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.filter-item label {
  font-size: 12px;
  color: #444;
}
.filter-item input[type="date"],
.filter-item select {
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.filter-negative {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}
.filter-negative label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  cursor: pointer;
}
.filter-negative input[type="checkbox"] {
  width: 16px;
  height: 16px;
}
.negative-date {
  width: 130px;
}
.filter-row button {
  padding: 6px 12px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #4a7ae5;
  color: #fff;
  cursor: pointer;
}
.filter-row button:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.search-results {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  max-height: 200px;
  overflow-y: auto;
  background: #fff;
  margin-top: 6px;
}
.search-result-header {
  padding: 8px 12px;
  background: #f3f4f6;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 1px solid #e5e7eb;
}
.search-result-item {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  gap: 12px;
  border-bottom: 1px solid #f3f4f6;
}
.search-result-item:hover {
  background: #f0f9ff;
}
.search-result-item.selected {
  background: #dbeafe;
}
.product-code {
  font-weight: 600;
  min-width: 120px;
}
.product-name {
  color: #4b5563;
}

.selected-product {
  padding: 10px 14px;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 6px;
  font-size: 14px;
  margin-top: 6px;
}

.table-section {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  margin-top: 6px;
}
.result-count {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 4px;
}

/* グリッドラッパー（plan-inputと同じパターン） */
.grid-wrapper {
  flex: 1;
  min-height: 200px;
  overflow: auto;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
}

/* テーブル本体 */
.inventory-grid {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.inventory-grid th,
.inventory-grid td {
  border: 1px solid #d7dfe8;
  padding: 4px 6px;
  white-space: nowrap;
  font-size: 13px;
}

/* ヘッダー行: 上に固定 */
.inventory-grid thead th {
  position: sticky;
  top: 0;
  z-index: 4;
  background: #cfd8ec;
  font-weight: 700;
}

/* 各列の幅とleft位置 - 個別にstickyを設定 */
.tree-col {
  position: sticky;
  left: 0;
  z-index: 3;
  width: 80px;
  min-width: 80px;
  max-width: 80px;
  font-family: monospace;
  color: #6b7280;
  background: #f8fafc;
}
.code-col {
  position: sticky;
  left: 80px;
  z-index: 3;
  width: 120px;
  min-width: 120px;
  max-width: 120px;
  font-weight: 600;
  background: #f8fafc;
}
.name-col {
  position: sticky;
  left: 200px;
  z-index: 3;
  width: 150px;
  min-width: 150px;
  max-width: 150px;
  background: #f8fafc;
}
.type-col {
  position: sticky;
  left: 350px;
  z-index: 3;
  width: 60px;
  min-width: 60px;
  max-width: 60px;
  text-align: center;
  background: #f8fafc;
}
.dest-col {
  position: sticky;
  left: 410px;
  z-index: 3;
  width: 150px;
  min-width: 150px;
  max-width: 150px;
  background: #f8fafc;
}
.qty-col {
  position: sticky;
  left: 560px;
  z-index: 3;
  width: 60px;
  min-width: 60px;
  max-width: 60px;
  text-align: right;
  background: #f8fafc;
}
.rowtype-col {
  position: sticky;
  left: 620px;
  z-index: 3;
  width: 70px;
  min-width: 70px;
  max-width: 70px;
  font-weight: 500;
  background: #f8fafc;
  border-right: 2px solid #b5c1d2 !important;
}

/* ヘッダーの左固定列は最優先 */
.inventory-grid thead .tree-col,
.inventory-grid thead .code-col,
.inventory-grid thead .name-col,
.inventory-grid thead .type-col,
.inventory-grid thead .dest-col,
.inventory-grid thead .qty-col,
.inventory-grid thead .rowtype-col {
  z-index: 8;
  background: #cfd8ec;
}

/* 日付列 */
.date-col {
  width: 70px;
  min-width: 70px;
  text-align: right;
  z-index: 1;
  background: #fff;
}
thead .date-col {
  background: #cfd8ec;
}

/* 在庫行 */
.row-stock {
  background: #fff;
}
.row-stock .tree-col,
.row-stock .code-col,
.row-stock .name-col,
.row-stock .type-col,
.row-stock .dest-col,
.row-stock .qty-col {
  background: #fff;
}
.row-stock .rowtype-col {
  background: #f9fafb;
}

/* 計画在庫行 */
.row-planned {
  background: #fefce8;
}
.row-planned .tree-col,
.row-planned .code-col,
.row-planned .name-col,
.row-planned .type-col,
.row-planned .dest-col,
.row-planned .qty-col,
.row-planned .rowtype-col,
.row-planned .date-col {
  background: #fefce8;
}

/* マイナス値 */
.negative {
  background: #fee2e2 !important;
  color: #dc2626;
  font-weight: bold;
}

.no-data,
.loading {
  padding: 24px;
  text-align: center;
  color: #6b7280;
  margin-top: 6px;
}
</style>
