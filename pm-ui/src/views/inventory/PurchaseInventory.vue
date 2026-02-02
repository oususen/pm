<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">仕入れ在庫 / 残量一覧</h2>
        <p class="subtitle">購入品を対象に、日付別の数量を右に並べて表示します。</p>
      </div>
      <div class="page-actions">
        <select v-model.number="selectedSupplier" @change="onSupplierChange">
          <option value="">-- 仕入先を選択 --</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">
            {{ s.supplier_code }} - {{ s.supplier_name }}
          </option>
        </select>
        <input
          type="text"
          v-model="productFilter"
          placeholder="品番/品名で絞り込み"
        />
        <input type="date" v-model="startDate" @change="onStartChange" />
        <select v-model.number="horizon">
          <option :value="30">30日</option>
          <option :value="60">60日</option>
          <option :value="90">90日</option>
          <option :value="120">120日</option>
        </select>
        <button @click="load" :disabled="loading || !selectedSupplier">更新</button>
        <button
          @click="recalculateInventory"
          :disabled="loading || recalculating || !purchaseLineId"
        >
          在庫再計算
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">読込中...</div>
    <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
    <div v-else-if="!selectedSupplier" class="no-data">
      仕入先を選択してください
    </div>
    <div v-else>
      <div v-if="groups.length" class="group-list">
        <div v-for="g in groups" :key="g.key" class="group-card">
          <div class="info-block">
            <div class="info-row">
              <span class="info-label">品番</span>
              <span class="info-value">{{ g.product_code || '-' }}</span>
              <button @click="toggleChildren(g)" class="expand-btn">
                {{ g.showChildren ? '▼' : '▶' }} BOM展開
              </button>
            </div>
            <div class="info-row">
              <span class="info-label">品名</span>
              <span class="info-value">{{ g.product_name || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">仕入先</span>
              <span class="info-value">{{ g.line_name || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">仕入先コード</span>
              <span class="info-value">{{ g.line_code || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">翌月</span>
              <span class="info-value"></span>
            </div>
            <div class="info-row">
              <span class="info-label">翌々月</span>
              <span class="info-value"></span>
            </div>
            <div class="info-row">
              <span class="info-label">完成品向けLT</span>
              <span class="info-value">{{ fmt(g.total_lt_days) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">自LT</span>
              <span class="info-value">{{ fmt(g.self_lt_days) }}</span>
            </div>
          </div>

          <div class="matrix-block">
            <table class="matrix-table">
              <thead>
                <tr>
                  <th class="label-col">項目</th>
                  <th v-for="d in columns" :key="d" class="day-col">{{ d }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in rowDefs" :key="row.key">
                  <th class="label-col">{{ row.label }}</th>
                  <td
                    v-for="d in columns"
                    :key="`${row.key}-${d}`"
                    class="cell"
                    :class="getCellClass(g, d, row.key)"
                  >
                    {{ fmt(getValue(g, d, row.key)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="g.showChildren" class="children-list">
            <div v-if="g.children.length === 0" class="no-children">BOM子製品がありません</div>
            <div v-for="(child, idx) in g.children" :key="idx" class="child-card">
              <div class="child-info">
                <div class="child-row">
                  <span class="child-label">品番</span>
                  <span class="child-value">{{ child.product_code }}</span>
                </div>
                <div class="child-row">
                  <span class="child-label">品名</span>
                  <span class="child-value">{{ child.product_name }}</span>
                </div>
                <div class="child-row">
                  <span class="child-label">工程</span>
                  <span class="child-value">{{ child.process_code }}</span>
                </div>
                <div class="child-row">
                  <span class="child-label">BOM数量</span>
                  <span class="child-value">{{ child.bom_quantity }}</span>
                </div>
              </div>
              <div class="child-matrix">
                <table class="matrix-table">
                  <thead>
                    <tr>
                      <th class="label-col">項目</th>
                      <th v-for="d in columns" :key="d" class="day-col">{{ d }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in rowDefs" :key="row.key">
                      <th class="label-col">{{ row.label }}</th>
                      <td
                        v-for="d in columns"
                        :key="`${row.key}-${d}`"
                        class="cell"
                        :class="getCellClass(child, d, row.key)"
                      >
                        {{ fmt(getValue(child, d, row.key)) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="no-data">データがありません</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "@/api/client";
import { addDays, formatISODate, parseISODate } from "@/utils/dateUtil";

const selectedSupplier = ref("");
const productFilter = ref("");
const defaultStart = new Date();
defaultStart.setDate(1);
const startDate = ref(formatISODate(defaultStart));
const horizon = ref(30);
const loading = ref(false);
const error = ref("");
const recalculating = ref(false);
const demands = ref([]);
const suppliers = ref([]);
const products = ref([]);
const purchaseLineId = ref("");
const adjustInputs = ref({});
const adjustSaving = ref({});
let userSetStart = false;

const onStartChange = () => {
  userSetStart = true;
};

const columns = computed(() => {
  const start = parseISODate(startDate.value);
  const cols = [];
  for (let i = 0; i < horizon.value; i++) {
    cols.push(formatISODate(addDays(start, i)));
  }
  return cols;
});

const rowDefs = [
  { key: "forecast", label: "計需" },
  { key: "firm", label: "実需" },
  { key: "plan", label: "計画" },
  { key: "actual", label: "実績" },
  { key: "adjust", label: "調整" },
  { key: "scrap", label: "仕損" },
  { key: "stock", label: "在庫" },
  { key: "planned_stock", label: "計画在庫" },
  { key: "progress", label: "進度" },
];

const applyDemands = (payload) => {
  const list = Array.isArray(payload) ? payload : payload.results || [];
  demands.value = list;
  if (!userSetStart && !startDate.value && demands.value.length) {
    const minDate = demands.value.map((d) => d.plan_date).sort()[0];
    if (minDate) {
      startDate.value = minDate;
    }
  }
};

const groups = computed(() => {
  if (!demands.value.length) return [];
  const filtered = demands.value.filter((d) => {
    const within =
      d.plan_date >= columns.value[0] &&
      d.plan_date <= columns.value[columns.value.length - 1];
    const prodText = `${d.product_code || ""}${d.product_name || ""}`.toLowerCase();
    const okProd =
      !productFilter.value ||
      prodText.includes(productFilter.value.trim().toLowerCase());
    return within && okProd;
  });

  const map = new Map();
  for (const d of filtered) {
    const key = `${d.line || d.line_name || ""}__${d.process_code || d.process || ""}__${d.product_code || ""}`;
    if (!map.has(key)) {
        map.set(key, {
          key,
          line_code: d.line_code,
          line_name: d.line_name,
          product_code: d.product_code,
          product_name: d.product_name,
          product_id: d.product,
          line_id: d.line,
          process_id: d.process,
          process_code: d.process_code || d.process || "",
          process_name: d.process_name || "",
          total_lt_days: null,
          self_lt_days: null,
          cells: {},
          children: [],
          showChildren: false,
          isChild: false,
        });
      }
      const g = map.get(key);
      if (g.total_lt_days === null && d.total_lt_days !== null && d.total_lt_days !== undefined) {
        g.total_lt_days = Number(d.total_lt_days);
      }
      if (g.self_lt_days === null && d.self_lt_days !== null && d.self_lt_days !== undefined) {
        g.self_lt_days = Number(d.self_lt_days);
      }
    if (!g.cells[d.plan_date]) {
      g.cells[d.plan_date] = {
        forecast: 0,
        firm: 0,
        plan: 0,
        actual: 0,
        adjust: 0,
        scrap: 0,
        stock: 0,
        planned_stock: 0,
        progress: 0,
      };
    }
    const c = g.cells[d.plan_date];
    const hasForecastSplit = d.forecast_order_qty !== null && d.forecast_order_qty !== undefined;
    c.forecast += Number((hasForecastSplit ? d.forecast_order_qty : d.order_qty) || 0);
    const hasFirmSplit = d.firm_order_qty !== null && d.firm_order_qty !== undefined;
    c.firm += Number((hasFirmSplit ? d.firm_order_qty : d.actual_shipment_qty) || 0);
    c.plan += Number(d.plan_qty || 0);
    c.actual += Number(d.actual_qty || 0);
    c.adjust += Number(d.adjust_qty || 0);
    c.scrap += Number(d.scrap_qty || 0);
    c.stock += Number(d.stock_qty || 0);
    c.planned_stock += Number(d.planned_stock_qty || 0);
    // 進度はバックエンドで計算された値を使用
    c.progress += Number(d.progress_qty || 0);
  }

  // 進度が日付抜けで途切れないよう、日付順に直近値をキャリーする
  const carryForwardProgress = (group) => {
    let last = null;
    columns.value.forEach((date) => {
      const cell = group.cells[date];
      const val = cell ? cell.progress : undefined;
      if (val !== null && val !== undefined) {
        last = val;
      } else if (last !== null && last !== undefined) {
        if (!group.cells[date]) group.cells[date] = {};
        group.cells[date].progress = last;
      }
    });
    if (group.children && group.children.length) {
      group.children.forEach(carryForwardProgress);
    }
  };

  const result = Array.from(map.values());
  result.forEach(carryForwardProgress);
  return result;
});

const fmt = (n) => {
  if (n === null || n === undefined) return "";
  const num = Number(n);
  if (Number.isNaN(num)) return "";
  if (num === 0) return "";
  return num.toLocaleString();
};

const getValue = (group, date, key) => {
  return group.cells?.[date]?.[key] ?? "";
};

const getCellClass = (group, date, rowKey) => {
  if (rowKey === "stock" || rowKey === "planned_stock" || rowKey === "progress") {
    const value = getValue(group, date, rowKey);
    if (value !== null && value !== undefined && Number(value) < 0) {
      return "negative";
    }
  }
  return "";
};

const adjustKey = (group, date) => `${group.key}__${date}`;

const getAdjustInputValue = (group, date) => {
  const key = adjustKey(group, date);
  if (Object.prototype.hasOwnProperty.call(adjustInputs.value, key)) {
    return adjustInputs.value[key];
  }
  const current = getValue(group, date, "adjust");
  if (current === null || current === undefined) return "";
  const num = Number(current);
  if (Number.isNaN(num) || num === 0) return "";
  return String(num);
};

const onAdjustInput = (group, date, event) => {
  adjustInputs.value[adjustKey(group, date)] = event.target.value;
};

const onAdjustEnter = (event) => {
  event.target.blur();
};

const isAdjustSaving = (group, date) => {
  return Boolean(adjustSaving.value[adjustKey(group, date)]);
};

const updateAdjustDemand = (group, date, adjustQty) => {
  const idx = demands.value.findIndex(
    (d) =>
      d.line === group.line_id &&
      d.process === group.process_id &&
      d.product === group.product_id &&
      d.plan_date === date
  );
  if (idx >= 0) {
    demands.value[idx].adjust_qty = adjustQty;
    return;
  }
  demands.value.push({
    line: group.line_id,
    line_code: group.line_code,
    line_name: group.line_name,
    process: group.process_id,
    process_code: group.process_code,
    process_name: group.process_name,
    product: group.product_id,
    product_code: group.product_code,
    product_name: group.product_name,
    plan_date: date,
    order_qty: 0,
    actual_qty: 0,
    plan_qty: 0,
    adjust_qty: adjustQty,
    scrap_qty: 0,
    stock_qty: 0,
    planned_stock_qty: 0,
    progress_qty: 0,
  });
};

const saveAdjust = async (group, date) => {
  if (group.isChild) return;
  if (!group.line_id || !group.process_id || !group.product_id) {
    alert("調整の保存に必要な情報が不足しています。");
    return;
  }
  const key = adjustKey(group, date);
  if (adjustSaving.value[key]) return;
  const raw = adjustInputs.value[key];
  let adjustQty = 0;
  if (raw !== "" && raw !== null && raw !== undefined) {
    const parsed = Number(raw);
    if (Number.isNaN(parsed) || !Number.isFinite(parsed)) {
      alert("調整数は数値で入力してください。");
      return;
    }
    if (!Number.isInteger(parsed)) {
      alert("調整数は整数で入力してください。");
      return;
    }
    adjustQty = parsed;
  }
  const current = Number(getValue(group, date, "adjust") || 0);
  if (adjustQty === current) {
    delete adjustInputs.value[key];
    return;
  }

  adjustSaving.value[key] = true;
  try {
    await api.lineBacklogs.save({
      line_id: group.line_id,
      items: [
        {
          product_id: group.product_id,
          process_id: group.process_id,
          plan_date: date,
          adjust_qty: adjustQty,
        },
      ],
    });
    updateAdjustDemand(group, date, adjustQty);
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];
    await api.lineBacklogs.recalculateInventory({
      line_id: group.line_id,
      start_date: start,
      end_date: end,
    });
    await reloadDemands();
    delete adjustInputs.value[key];
  } catch (e) {
    console.error("調整の保存に失敗:", e);
    alert("調整の保存に失敗しました。");
  } finally {
    delete adjustSaving.value[key];
  }
};

const loadBOMChildren = async (group) => {
  if (!group.product_id) return;

  try {
    const bomRes = await api.boms.getBOMs({ parent_product: group.product_id });
    const boms = bomRes.data || [];

    if (!boms.length) {
      group.children = [];
      return;
    }

    const activeBoms = boms.filter((b) => b.is_active);
    if (!activeBoms.length) {
      group.children = [];
      return;
    }

    const bom = activeBoms[0];
    const itemsRes = await api.bomItems.getBOMItems({ bom: bom.id });
    const items = itemsRes.data || [];

    const children = [];
    for (const item of items) {
      const childDemands = demands.value.filter(
        (d) =>
          d.product === item.child_product &&
          d.plan_date >= columns.value[0] &&
          d.plan_date <= columns.value[columns.value.length - 1]
      );

      if (childDemands.length > 0) {
        const childCells = {};
        for (const d of childDemands) {
          if (!childCells[d.plan_date]) {
            childCells[d.plan_date] = {
              forecast: 0,
              firm: 0,
              plan: 0,
              actual: 0,
              adjust: 0,
              scrap: 0,
              stock: 0,
              planned_stock: 0,
              progress: 0,
            };
          }
          const c = childCells[d.plan_date];
          const hasForecastSplit = d.forecast_order_qty !== null && d.forecast_order_qty !== undefined;
          c.forecast += Number((hasForecastSplit ? d.forecast_order_qty : d.order_qty) || 0);
          const hasFirmSplit = d.firm_order_qty !== null && d.firm_order_qty !== undefined;
          c.firm += Number((hasFirmSplit ? d.firm_order_qty : d.actual_shipment_qty) || 0);
          c.plan += Number(d.plan_qty || 0);
          c.actual += Number(d.actual_qty || 0);
          c.adjust += Number(d.adjust_qty || 0);
          c.scrap += Number(d.scrap_qty || 0);
          c.stock += Number(d.stock_qty || 0);
          c.planned_stock += Number(d.planned_stock_qty || 0);
          // 進度はバックエンドで計算された値を使用
          c.progress += Number(d.progress_qty || 0);
        }

        const childDemand = childDemands[0];
        children.push({
          product_code: childDemand.product_code,
          product_name: childDemand.product_name,
          product_id: childDemand.product,
          process_code: childDemand.process_code,
          process_name: childDemand.process_name,
          process_id: childDemand.process,
          line_code: childDemand.line_code,
          line_name: childDemand.line_name,
          line_id: childDemand.line,
          bom_quantity: item.quantity,
          cells: childCells,
          isChild: true,
        });
      }
    }

    group.children = children;
  } catch (e) {
    console.error("BOM子製品の読み込みに失敗:", e);
    group.children = [];
  }
};

const toggleChildren = async (group) => {
  group.showChildren = !group.showChildren;
  if (group.showChildren && group.children.length === 0) {
    await loadBOMChildren(group);
  }
};

const reloadDemands = async () => {
  if (!purchaseLineId.value) return;
  const res = await api.lineBacklogs.getLineBacklogs(getBacklogParams());
  const payload = res.data || [];
  applyDemands(payload);
};

const getBacklogParams = () => {
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  const productIds = products.value.map((p) => p.id);
  return {
    line: purchaseLineId.value,
    product__in: productIds.join(","),
    plan_date__gte: start,
    plan_date__lte: end,
    include_order_split: true,
  };
};

const fetchSuppliers = async () => {
  const res = await api.suppliers.getSuppliers();
  suppliers.value = res.data.results || res.data || [];
};

const fetchProducts = async (supplierId = null) => {
  try {
    let bomItems = [];
    if (supplierId) {
      const baseParams = { supplier: supplierId };
      const [buyRes, subconRes] = await Promise.all([
        api.bomItems.getBOMItems({ ...baseParams, sourcing_type: "BUY" }),
        api.bomItems.getBOMItems({ ...baseParams, sourcing_type: "SUBCON" }),
      ]);
      const buyItems = buyRes.data.results || buyRes.data || [];
      const subconItems = subconRes.data.results || subconRes.data || [];
      bomItems = [...buyItems, ...subconItems];
    } else {
      const params = { sourcing_type: "BUY" };
      const bomItemsRes = await api.bomItems.getBOMItems(params);
      bomItems = bomItemsRes.data.results || bomItemsRes.data || [];
    }

    const targetProductIds = new Set(bomItems.map((item) => item.child_product));
    const allProducts = await api.products.getAllProducts();
    const filtered =
      supplierId && targetProductIds.size
        ? allProducts.filter((p) => !p.is_phantom && targetProductIds.has(p.id))
        : allProducts.filter((p) => !p.is_phantom);

    products.value = filtered.sort((a, b) =>
      (a.product_code || "").localeCompare(b.product_code || "")
    );
  } catch (e) {
    console.error("購入品の取得エラー", e);
    products.value = [];
  }
};

const refreshPurchaseDemand = async () => {
  if (!selectedSupplier.value) return false;
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  const pickupRes = await api.lineBacklogs.pickupPurchase({
    supplier_id: selectedSupplier.value,
    start_date: start,
    end_date: end,
  });
  purchaseLineId.value = pickupRes?.data?.line_id || "";
  return Boolean(purchaseLineId.value);
};

const refreshScrapQty = async () => {
  if (!purchaseLineId.value) return false;
  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  try {
    await api.lineBacklogs.recalculateScrap({
      line_id: purchaseLineId.value,
      start_date: start,
      end_date: end,
    });
    return true;
  } catch (e) {
    console.error("仕損再計算に失敗:", e);
    return false;
  }
};

const onSupplierChange = async () => {
  demands.value = [];
  purchaseLineId.value = "";
  if (selectedSupplier.value) {
    await fetchProducts(selectedSupplier.value);
    await load();
  }
};

const load = async () => {
  if (!selectedSupplier.value) return;
  loading.value = true;
  error.value = "";
  try {
    await fetchProducts(selectedSupplier.value);
    const productIds = products.value.map((p) => p.id);
    if (!productIds.length) {
      demands.value = [];
      return;
    }
    const refreshed = await refreshPurchaseDemand();
    if (!refreshed) {
      throw new Error("仕入れラインの解決に失敗しました");
    }
    await refreshScrapQty();
    // 在庫・計画在庫・進度を再計算
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];
    await api.lineBacklogs.recalculateInventory({
      line_id: purchaseLineId.value,
      start_date: start,
      end_date: end,
    });
    const res = await api.lineBacklogs.getLineBacklogs(getBacklogParams());
    const payload = res.data || [];
    applyDemands(payload);
  } catch (e) {
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
};

const recalculateInventory = async () => {
  if (!purchaseLineId.value) return;
  if (!confirm("在庫と計画在庫を再計算しますか？")) {
    return;
  }
  recalculating.value = true;
  error.value = "";
  try {
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];
    await api.lineBacklogs.recalculateInventory({
      line_id: purchaseLineId.value,
      start_date: start,
      end_date: end,
    });
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || "在庫再計算に失敗しました";
    alert("エラー: " + error.value);
  } finally {
    recalculating.value = false;
  }
};

onMounted(async () => {
  await fetchSuppliers();
});
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
.group-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.group-card {
  display: grid;
  grid-template-columns: 260px 1fr;
  border: 1px solid #dce3ef;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}
.info-block {
  padding: 10px;
  border-right: 1px solid #e5e7eb;
  background: #f8fafc;
}
.info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 4px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 13px;
}
.info-label {
  font-weight: 700;
  color: #374151;
}
.info-value {
  color: #111827;
  margin-left: 8px;
}
.matrix-block {
  overflow: auto;
}
.matrix-table {
  border-collapse: collapse;
  min-width: 960px;
  width: 100%;
}
.matrix-table th,
.matrix-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  text-align: right;
  min-width: 80px;
}
.matrix-table thead th {
  position: sticky;
  top: 0;
  background: #f4f6fb;
  z-index: 1;
  text-align: center;
}
.label-col {
  position: sticky;
  left: 0;
  background: #f9fafb;
  z-index: 2;
  text-align: left;
  min-width: 100px;
}
.cell {
  &.negative {
    background: #fee;
    color: #c00;
    font-weight: bold;
  }
  background: #fff;
}
.cell-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 4px 6px;
  text-align: right;
  font-size: 12px;
  background: #fff;
}
.cell-input:disabled {
  background: #f3f4f6;
  color: #9ca3af;
}
.no-data,
.loading {
  padding: 24px;
  text-align: center;
  color: #6b7280;
}
.expand-btn {
  margin-left: 8px;
  padding: 4px 8px;
  font-size: 12px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.expand-btn:hover {
  background: #2563eb;
}
.children-list {
  padding: 12px;
  background: #f1f5f9;
  border-top: 2px solid #cbd5e1;
}
.no-children {
  padding: 12px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}
.child-card {
  display: grid;
  grid-template-columns: 200px 1fr;
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
}
.child-card:last-child {
  margin-bottom: 0;
}
.child-info {
  padding: 8px;
  background: #fefce8;
  border-right: 1px solid #e5e7eb;
}
.child-row {
  display: flex;
  justify-content: space-between;
  padding: 4px;
  font-size: 12px;
  border-bottom: 1px solid #fde68a;
}
.child-row:last-child {
  border-bottom: none;
}
.child-label {
  font-weight: 600;
  color: #92400e;
}
.child-value {
  color: #451a03;
}
.child-matrix {
  overflow: auto;
}
</style>
