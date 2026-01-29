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
          @keydown.enter="searchProducts"
        />
        <button @click="searchProducts" :disabled="loading">検索</button>
        <select v-model.number="horizon">
          <option :value="7">7日</option>
          <option :value="15">15日</option>
          <option :value="30">30日</option>
          <option :value="60">60日</option>
        </select>
        <button @click="loadComponentInventory" :disabled="loading || !selectedProduct">更新</button>
      </div>
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
    <div v-else-if="bomTree.length > 0">
      <div class="inventory-table-wrapper">
        <table class="inventory-table">
          <thead>
            <tr>
              <th class="col-tree">階層</th>
              <th class="col-code">品番</th>
              <th class="col-name">品名</th>
              <th class="col-type">区分</th>
              <th class="col-qty">BOM数量</th>
              <th class="col-row-type">項目</th>
              <th v-for="d in columns" :key="d" class="col-date">{{ formatDateShort(d) }}</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(item, idx) in bomTree" :key="idx">
              <!-- 在庫行 -->
              <tr class="row-stock">
                <td class="col-tree">{{ item.treePrefix }}</td>
                <td class="col-code">{{ item.product_code }}</td>
                <td class="col-name">{{ item.product_name }}</td>
                <td class="col-type">{{ formatSourcingType(item.sourcing_type) }}</td>
                <td class="col-qty">{{ item.quantity }}</td>
                <td class="col-row-type">在庫</td>
                <td
                  v-for="d in columns"
                  :key="`stock-${d}`"
                  class="col-date"
                  :class="{ negative: getStockValue(item, d, 'stock') < 0 }"
                >
                  {{ fmt(getStockValue(item, d, 'stock')) }}
                </td>
              </tr>
              <!-- 計画在庫行 -->
              <tr class="row-planned">
                <td class="col-tree"></td>
                <td class="col-code"></td>
                <td class="col-name"></td>
                <td class="col-type"></td>
                <td class="col-qty"></td>
                <td class="col-row-type">計画在庫</td>
                <td
                  v-for="d in columns"
                  :key="`planned-${d}`"
                  class="col-date"
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
const loading = ref(false);
const error = ref("");
const bomTree = ref([]);
const inventoryData = ref({});
const dataLoaded = ref(false);

// 今日から始まる日付列
const columns = computed(() => {
  const today = new Date();
  const cols = [];
  for (let i = 0; i < horizon.value; i++) {
    cols.push(formatISODate(addDays(today, i)));
  }
  return cols;
});

// 製品検索
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

// 製品選択
const selectProduct = (product) => {
  selectedProduct.value = product;
  searchResults.value = [];
  bomTree.value = [];
  inventoryData.value = {};
  dataLoaded.value = false;
};

// BOMツリー展開 + 在庫取得
const loadComponentInventory = async () => {
  if (!selectedProduct.value) return;

  loading.value = true;
  error.value = "";
  bomTree.value = [];
  inventoryData.value = {};
  dataLoaded.value = false;

  try {
    // 1. BOMツリーを取得
    const treeRes = await api.bomService.getBomTree(selectedProduct.value.id);
    const tree = treeRes.data;

    if (!tree || !tree.children || tree.children.length === 0) {
      dataLoaded.value = true;
      return;
    }

    // 2. ツリーをフラット化
    const flatItems = flattenBomTree(tree.children, 0, "");

    // 3. 子部品のproduct_idリストを取得
    const productIds = [...new Set(flatItems.map((item) => item.product_id))];

    // 4. 在庫データを取得
    const startDate = columns.value[0];
    const endDate = columns.value[columns.value.length - 1];

    // 複数製品の在庫をまとめて取得
    const invRes = await api.lineBacklogs.getLineBacklogs({
      product__in: productIds.join(","),
      plan_date__gte: startDate,
      plan_date__lte: endDate,
    });
    const invData = invRes.data || [];

    // 5. 製品ID・日付ごとに在庫を集計
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

    // 6. BOMツリーに在庫情報をマージ
    bomTree.value = flatItems;
    dataLoaded.value = true;
  } catch (e) {
    console.error("データ取得エラー:", e);
    error.value = e?.message || "データの取得に失敗しました";
  } finally {
    loading.value = false;
  }
};

// BOMツリーをフラット化（再帰）
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
    });

    if (child.children && child.children.length > 0) {
      result.push(...flattenBomTree(child.children, level + 1, childPrefix));
    }
  });
  return result;
};

// 在庫値取得
const getStockValue = (item, date, type) => {
  const key = `${item.product_id}_${date}`;
  const data = inventoryData.value[key];
  if (!data) return 0;
  return type === "stock" ? data.stock : data.planned;
};

// フォーマット
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
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
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
.subtitle {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.search-results {
  border: 1px solid #d1d5db;
  border-radius: 6px;
  max-height: 200px;
  overflow-y: auto;
  background: #fff;
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
}

.inventory-table-wrapper {
  overflow-x: auto;
}
.inventory-table {
  border-collapse: collapse;
  min-width: 100%;
  font-size: 13px;
}
.inventory-table th,
.inventory-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  text-align: left;
  white-space: nowrap;
}
.inventory-table thead th {
  background: #f4f6fb;
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}
.col-tree {
  font-family: monospace;
  color: #6b7280;
  min-width: 80px;
}
.col-code {
  min-width: 120px;
  font-weight: 600;
}
.col-name {
  min-width: 150px;
}
.col-type {
  min-width: 60px;
  text-align: center;
}
.col-qty {
  min-width: 60px;
  text-align: right;
}
.col-row-type {
  min-width: 70px;
  background: #f9fafb;
  font-weight: 500;
}
.col-date {
  min-width: 60px;
  text-align: right;
}
.row-stock {
  background: #fff;
}
.row-planned {
  background: #fefce8;
}
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
}
</style>
