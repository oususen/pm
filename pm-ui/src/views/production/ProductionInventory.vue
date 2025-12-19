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
                  >
                    {{ fmt(getValue(g, d, row.key)) }}
                  </td>
                </tr>
              </tbody>
            </table>
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
const productFilter = ref("");
const startDate = ref(formatISODate(new Date()));
const horizon = ref(14);
const loading = ref(false);
const error = ref("");
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
    const lineText = `${d.line_name || ""}${d.line || ""}`.toLowerCase();
    const prodText = `${d.product_code || ""}${d.product_name || ""}`.toLowerCase();
    const okLine =
      !lineFilter.value ||
      lineText.includes(lineFilter.value.trim().toLowerCase());
    const okProd =
      !productFilter.value ||
      prodText.includes(productFilter.value.trim().toLowerCase());
    return within && okLine && okProd;
  });

  const map = new Map();
  for (const d of filtered) {
    const key = `${d.line || d.line_name || ""}__${d.product_code || ""}`;
    if (!map.has(key)) {
      map.set(key, {
        key,
        line_code: d.line_code,
        line_name: d.line_name,
        product_code: d.product_code,
        product_name: d.product_name,
        process_code: d.process_code || d.routing_step || d.process || "",
        process_name: d.process_name || "",
        cells: {},
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
    c.forecast += Number(d.forecast_qty || 0);
    c.firm += Number(d.firm_qty || 0);
    c.plan += Number(d.plan_qty || 0);
    c.adjust += 0; // 調整は現状データ無しのため0
    c.scrap += 0; // 仕損は在庫計算側で集計予定のため0表示
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

const load = async () => {
  loading.value = true;
  error.value = "";
  try {
    const res = await api.lineDemands.list({ page_size: 5000 });
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
  } catch (e) {
    error.value = e?.message || "読み込みに失敗しました";
  } finally {
    loading.value = false;
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
  background: #fff;
}
.no-data,
.loading {
  padding: 24px;
  text-align: center;
  color: #6b7280;
}
</style>
