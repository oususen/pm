<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h2 class="page-title">在庫 / 残量一覧</h2>
        <p class="subtitle">製品情報を左に、日付別の数量を右に並べて表示します。</p>
      </div>
      <div class="page-actions">
        <input
          type="text"
          v-model="lineFilter"
          placeholder="ラインコード/名称で絞り込み"
        />
        <input
          type="text"
          v-model="processFilter"
          placeholder="工程コード/名称で絞り込み"
        />
        <input
          type="text"
          v-model="productFilter"
          placeholder="品番/品名で絞り込み"
        />
        <input type="date" v-model="startDate" @change="onStartChange" />
        <select v-model.number="horizon">
          <option :value="7">7日</option>
          <option :value="14">14日</option>
          <option :value="21">21日</option>
          <option :value="30">30日</option>
        </select>
        <button @click="load" :disabled="loading">更新</button>
        <button @click="recalculateInventory" :disabled="loading || recalculating">在庫再計算</button>
      </div>
    </div>

    <div v-if="loading" class="loading">読込中...</div>
    <div v-else-if="error" class="no-data">エラー: {{ error }}</div>
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
              <span class="info-label">工程名</span>
              <span class="info-value">{{ g.process_name || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">工程コード</span>
              <span class="info-value">{{ g.process_code || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">予定</span>
              <span class="info-value"></span>
            </div>
            <div class="info-row">
              <span class="info-label">確定</span>
              <span class="info-value"></span>
            </div>
            <div class="info-row">
              <span class="info-label">翌月</span>
              <span class="info-value"></span>
            </div>
            <div class="info-row">
              <span class="info-label">翌々月</span>
              <span class="info-value"></span>
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
                  <td v-for="d in columns"
                    :key="`${row.key}-${d}`"
                    class="cell" :class="getCellClass(g, d, row.key)"
                  >
                    {{ fmt(getValue(g, d, row.key)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- BOM子製品表示 -->
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
                      <td v-for="d in columns"
                        :key="`${row.key}-${d}`"
                        class="cell" :class="getCellClass(child, d, row.key)"
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

const lineFilter = ref("");
const processFilter = ref("");
const productFilter = ref("");
const startDate = ref(formatISODate(new Date()));
const horizon = ref(14);
const loading = ref(false);
const error = ref("");
const recalculating = ref(false);
const demands = ref([]);
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
  { key: "forecast", label: "内示" },
  { key: "firm", label: "確定" },
  { key: "plan", label: "計画" },
  { key: "adjust", label: "調整" },
  { key: "scrap", label: "仕損" },
  { key: "stock", label: "在庫" },
  { key: "planned_stock", label: "計画在庫" },
];

const groups = computed(() => {
  if (!demands.value.length) return [];
  const filtered = demands.value.filter((d) => {
    const within =
      d.plan_date >= columns.value[0] &&
      d.plan_date <= columns.value[columns.value.length - 1];
    const lineText = `${d.line_code || ""}${d.line_name || ""}`.toLowerCase();
    const processText = `${d.process_code || ""}${d.process_name || ""}`.toLowerCase();
    const prodText = `${d.product_code || ""}${d.product_name || ""}`.toLowerCase();
    const okLine =
      !lineFilter.value ||
      lineText.includes(lineFilter.value.trim().toLowerCase());
    const okProcess =
      !processFilter.value ||
      processText.includes(processFilter.value.trim().toLowerCase());
    const okProd =
      !productFilter.value ||
      prodText.includes(productFilter.value.trim().toLowerCase());
    return within && okLine && okProcess && okProd;
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
        process_code: d.process_code || d.process || "",
        process_name: d.process_name || "",
        cells: {},
        children: [],
        showChildren: false,
      });
    }
    const g = map.get(key);
    if (!g.cells[d.plan_date]) {
      g.cells[d.plan_date] = {
        forecast: 0,
        firm: 0,
        plan: 0,
        adjust: 0,
        scrap: 0,
        stock: 0,
        planned_stock: 0,
      };
    }
    const c = g.cells[d.plan_date];
    // 内示: この製品を加工するラインの直後ラインの計画数の合計
    // → 在庫側では line_backlog.order_qty を利用
    c.forecast += Number(d.order_qty || 0);
    // 確定: 直後ラインの実績の合計に相当する値として
    // このラインの実績数量(actual_qty)を集計
    c.firm += Number(d.actual_qty || 0);
    // 計画・在庫・計画在庫は line_backlog から取得
    c.plan += Number(d.plan_qty || 0);
    c.adjust += Number(d.adjust_qty || 0); // 調整数
    c.scrap += Number(d.scrap_qty || 0); // 仕損数
    c.stock += Number(d.stock_qty || 0);
    c.planned_stock += Number(d.planned_stock_qty || 0);
  }
  return Array.from(map.values());
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
  // 在庫・計画在庫がマイナスの場合は赤色表示
  if (rowKey === 'stock' || rowKey === 'planned_stock') {
    const value = getValue(group, date, rowKey);
    if (value !== null && value !== undefined && Number(value) < 0) {
      return 'negative';
    }
  }
  return '';
};

const loadBOMChildren = async (group) => {
  if (!group.product_id) return;

  try {
    // この製品を親とするBOMを取得
    const bomRes = await api.boms.getBOMs({ parent_product: group.product_id });
    const boms = bomRes.data || [];

    if (!boms.length) {
      group.children = [];
      return;
    }

    // 最新のアクティブなBOMを使用
    const activeBoms = boms.filter(b => b.is_active);
    if (!activeBoms.length) {
      group.children = [];
      return;
    }

    const bom = activeBoms[0];

    // BOM明細を取得
    const itemsRes = await api.bomItems.getBOMItems({ bom: bom.id });
    const items = itemsRes.data || [];

    // 各子製品の在庫データを取得
    const children = [];
    for (const item of items) {
      // この子製品の在庫データを取得（日付範囲は親と同じ）
      const childDemands = demands.value.filter(d =>
        d.product === item.child_product &&
        d.plan_date >= columns.value[0] &&
        d.plan_date <= columns.value[columns.value.length - 1]
      );

      if (childDemands.length > 0) {
        // 子製品のセルデータを作成
        const childCells = {};
        for (const d of childDemands) {
          if (!childCells[d.plan_date]) {
            childCells[d.plan_date] = {
              forecast: 0,
              firm: 0,
              plan: 0,
              adjust: 0,
              scrap: 0,
              stock: 0,
              planned_stock: 0,
            };
          }
          const c = childCells[d.plan_date];
          c.forecast += Number(d.order_qty || 0);
          c.firm += Number(d.actual_qty || 0);
          c.plan += Number(d.plan_qty || 0);
          c.adjust += Number(d.adjust_qty || 0);
          c.scrap += Number(d.scrap_qty || 0);
          c.stock += Number(d.stock_qty || 0);
          c.planned_stock += Number(d.planned_stock_qty || 0);
        }

        // 子製品情報を追加
        const childDemand = childDemands[0];
        children.push({
          product_code: childDemand.product_code,
          product_name: childDemand.product_name,
          process_code: childDemand.process_code,
          process_name: childDemand.process_name,
          line_code: childDemand.line_code,
          line_name: childDemand.line_name,
          bom_quantity: item.quantity,
          cells: childCells,
        });
      }
    }

    group.children = children;
  } catch (e) {
    console.error('BOM子製品の読み込みに失敗:', e);
    group.children = [];
  }
};

const toggleChildren = async (group) => {
  group.showChildren = !group.showChildren;
  if (group.showChildren && group.children.length === 0) {
    await loadBOMChildren(group);
  }
};

const refreshOrderQty = async () => {
  const lineIds = [...new Set(demands.value.map((d) => d.line).filter(Boolean))];
  if (!lineIds.length) return false;

  const start = columns.value[0];
  const end = columns.value[columns.value.length - 1];
  let updated = false;
  for (const lineId of lineIds) {
    try {
      await api.lineBacklogs.pickup({
        line_id: lineId,
        start_date: start,
        end_date: end,
      });
      updated = true;
    } catch (e) {
      console.error('内示再計算に失敗:', e);
    }
  }
  return updated;
};

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    // 在庫/残量は line_backlog ベースで集計する
    const res = await api.lineBacklogs.getLineBacklogs();
    const payload = res.data || [];
    demands.value = Array.isArray(payload) ? payload : payload.results || [];
    if (!userSetStart && demands.value.length) {
      const minDate = demands.value
        .map((d) => d.plan_date)
        .sort()[0];
      if (minDate) {
        startDate.value = minDate;
      }
    }
    const refreshed = await refreshOrderQty();
    if (refreshed) {
      const refreshRes = await api.lineBacklogs.getLineBacklogs();
      const refreshPayload = refreshRes.data || [];
      demands.value = Array.isArray(refreshPayload)
        ? refreshPayload
        : refreshPayload.results || [];
    }
  } catch (e) {
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
  }
};

const recalculateInventory = async () => {
  if (!confirm('在庫と計画在庫を再計算しますか？\n※全ラインの在庫データが更新されます。')) {
    return;
  }
  
  recalculating.value = true;
  error.value = "";
  try {
    // 現在表示中の期間で再計算
    const start = columns.value[0];
    const end = columns.value[columns.value.length - 1];
    
    // 表示中の全ラインを取得
    const lines = [...new Set(demands.value.map(d => d.line).filter(Boolean))];
    
    if (lines.length === 0) {
      alert('再計算対象のラインがありません');
      return;
    }
    
    // 各ラインごとに再計算
    for (const lineId of lines) {
      await api.lineBacklogs.recalculateInventory({
        line_id: lineId,
        start_date: start,
        end_date: end
      });
    }
    
    alert('在庫再計算が完了しました');
    
    // データを再読み込み
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || "在庫再計算に失敗しました";
    alert('エラー: ' + error.value);
  } finally {
    recalculating.value = false;
  }
};

onMounted(load);
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
